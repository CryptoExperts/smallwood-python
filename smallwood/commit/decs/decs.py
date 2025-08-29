from utils import MultiDimArray, PolynomialUtils, LPolynomialUtils, Buffer
from utils.log.section import LogSection
from utils.challenges import RLCChallengeType, derive_rlc_challenge, get_rlc_bit_security

class DECS:
    def __init__(self, **kwargs):
        self._field = kwargs.pop('field')
        self._nb_polys = kwargs.pop('nb_polys')
        self._degree = kwargs.pop('degree')
        self._tree_factory = kwargs.pop('tree_factory')
        self._nb_queries = kwargs.pop('nb_queries')

        self._eta = kwargs.pop('eta')
        self._pow_opening = kwargs.pop('pow_opening', 0)
        self._format_challenge = kwargs.pop('format_challenge', RLCChallengeType.POWERS)
        assert self._nb_queries <= self._degree

        assert len(kwargs) == 0, kwargs

    @property
    def field(self):
        return self._field

    @property
    def nb_polys(self):
        return self._nb_polys

    @property
    def degree(self):
        return self._degree

    @property
    def nb_evals(self):
        return self.tree_factory.get_nb_leaves()

    @property
    def nb_queries(self):
        return self._nb_queries

    @property
    def eta(self):
        return self._eta

    @property
    def format_challenge(self):
        return self._format_challenge

    @property
    def pow_opening(self):
        return self._pow_opening

    @property
    def tree_factory(self):
        return self._tree_factory

    def get_security(self):
        from math import log2
        from scipy.special import comb as binom
        sec_dec = get_rlc_bit_security(self.field, self.eta, self.nb_polys, self.format_challenge)
        sec_dec -= log2(binom(self.nb_evals, self.degree+2))
        return sec_dec, {'decs_check': sec_dec}

    def get_opening_security(self):
        from math import log2
        from scipy.special import comb as binom
        N = self.nb_evals
        sec_opening = log2(binom(N, self.nb_queries)) - log2(binom(self.degree, self.nb_queries)) + self.pow_opening
        return sec_opening
    
    def get_auth_size(self):
        return self.tree_factory.get_authentication_path_max_size(self.nb_queries)

    def get_variable_auth_size(self):
        if self.tree_factory.has_variable_auth_size():
            raise NotImplementedError()
        return self.get_auth_size()

    def has_variable_proof_size(self):
        return self.tree_factory.has_variable_auth_size()

    def get_proof_size(self, with_details=False):
        proof_size_d = {}
        proof_size_d['trunc_eps + opening_dec_masks'] = self.get_partial_proof_size()
        proof_size_d['auth'] = self.get_auth_size()

        proof_size = sum(proof_size_d.values())
        return (proof_size, proof_size_d) if with_details else proof_size

    def get_averaged_proof_size(self, with_details=False):
        vec = self.get_serializer().get_serialized_size

        proof_size_d = {}
        proof_size_d['opening_dec_masks'] = self.nb_queries * vec(self.eta)
        proof_size_d['trunc_eps'] = self.eta * vec(self.degree+1-self.nb_queries)
        proof_size_d['auth'] = self.get_variable_auth_size()

        proof_size = sum(proof_size_d.values())
        return (proof_size, proof_size_d) if with_details else proof_size

    def get_opening_aux_size(self):
        raise NotImplementedError()

    ###########################################
    ###        DECS ROUTINES

    def commit(self, salt, polynomials):
        nb_polys = self.nb_polys
        degree = self.degree
        nb_evals = self.nb_evals
        eta = self.eta
        field = self.field

        ## Sanity check on input polynomials
        assert len(polynomials) == nb_polys
        for poly in polynomials:
            assert poly.degree() <= degree
            assert poly.base_ring() == field
        R = polynomials[0].parent()

        # Sample random masking polynomials
        mask_polys = [
            R.random_element(degree=degree)
            for _ in range(eta)
        ]

        # Compute polynomial evaluations
        input_shares = MultiDimArray((nb_evals, nb_polys+eta))
        for i in range(nb_evals):
            eval_point = self.get_evaluation_point(i)
            for k in range(nb_polys):
                input_shares[i][k] = polynomials[k](eval_point)
            for k in range(eta):
                input_shares[i][nb_polys+k] = mask_polys[k](eval_point)

        # Hash polynomial evaluations
        coms = MultiDimArray((nb_evals,))
        for i in range(nb_evals):
            coms[i] = self.hash_leaf(i, salt, input_shares[i])
        tree, root = self.commit_leaves(coms)
        hash_mt = self.hash_merkle_root(salt, root)

        # Run the degree-enforcing test
        gamma = self.derive_decs_challenge(hash_mt)
        eps = MultiDimArray((eta,), R(0))
        for j in range(eta):
            for k in range(nb_polys):
                eps[j] += gamma[j][k] * polynomials[k]
            eps[j] += mask_polys[j]
            eps[j] = PolynomialUtils.to_list(eps[j], degree)

        # Build commitment digest
        commitment = self.build_commitment_digest(hash_mt, eps)
        state = (input_shares, tree, eps)
        return (commitment, state)

    def open(self, state, iop_queries):
        (input_shares, tree, eps) = state
        eta = self.eta
        degree = self.degree
        nb_dec_queries = self.nb_queries

        opened_values = MultiDimArray((nb_dec_queries,))
        opening_dec_masks = MultiDimArray((nb_dec_queries,))
        open_columns = MultiDimArray((nb_dec_queries,))

        for j in range(nb_dec_queries):
            open_columns[j] = self.get_num_leaf(iop_queries[j])
            opened_values[j] = input_shares[open_columns[j]][:-eta]
            opening_dec_masks[j] = input_shares[open_columns[j]][-eta:]
        auth = self.open_leaves(tree, open_columns)

        proof = self.build_partial_proof(opening_dec_masks, eps)
        proof += auth
        return (opened_values, proof)

    def recompute_commitment(self, salt, iop_queries, opened_values, proof, is_standalone_proof=True):
        eta = self.eta
        degree = self.degree
        nb_dec_queries = self.nb_queries
        F = self.field

        open_columns = MultiDimArray((nb_dec_queries,))
        for j in range(nb_dec_queries):
            open_columns[j] = self.get_num_leaf(iop_queries[j])
        
        (opening_dec_masks, hint_eps), proof = self.parse_partial_proof(proof)

        with LogSection('Leave Hash'):
            open_leaves = MultiDimArray((nb_dec_queries,))
            for j in range(nb_dec_queries):
                share = opened_values[j] + opening_dec_masks[j]
                open_leaves[j] = self.hash_leaf(open_columns[j], salt, share)

        with LogSection('Merkle Tree'):
            root, proof = self.recompute_root(proof, [
                (open_columns[j], open_leaves[j])
                for j in range(nb_dec_queries)
            ])

        with LogSection('Recompute Com Share'):
            hash_mt = self.hash_merkle_root(salt, root)

        # To decrease the dec randomness, we can take {x^i}_i for a random x
        with LogSection('Derive DEC Challenge'):
            gamma = self.derive_decs_challenge(hash_mt)

        is_ok = True
        with LogSection('Run DEC test'):
            eps = MultiDimArray((eta,))
            for j in range(eta):
                eps_values = []
                for i in range(nb_dec_queries):

                    share = opened_values[i] + opening_dec_masks[i]
                    v = F(0)
                    for k in range(self.nb_polys):
                        v += gamma[j][k] * share[k]
                    v += share[self.nb_polys+j]
                    eps_values.append(v)
                eps[j] = self.recover_polynomial(
                    hint_eps[j], degree,
                    iop_queries, eps_values
                )
                if eps[j] is None:
                    is_ok = False

        commitment = self.build_commitment_digest(hash_mt, eps) if is_ok else None
        if is_standalone_proof:
            assert len(proof) == 0, (len(proof), proof)
            return commitment
        else:
            return commitment, proof

    def verify(self, salt, commitment, iop_queries, opened_values, proof):
        commitment_ = self.recompute_commitment(salt, iop_queries, opened_values, proof)
        return commitment == commitment_

    def get_random_opening(self, binding=[]):
        counter = 0
        open_columns = None
        aux = None
        while True:
            aux = self.counter_to_aux(counter)
            open_columns = self.xof_decs_opening(aux, binding)
            if open_columns is not None:
                break
            counter += 1

        iop_queries = MultiDimArray((self.nb_queries,))
        for j in range(self.nb_queries):
            iop_queries[j] = self.get_evaluation_point(open_columns[j])
        return (iop_queries, aux)

    def recompute_random_opening(self, aux, binding=[]):
        open_columns = self.xof_decs_opening(aux, binding)
        if open_columns is None:
            return None

        iop_queries = MultiDimArray((self.nb_queries,))
        for j in range(self.nb_queries):
            iop_queries[j] = self.get_evaluation_point(open_columns[j])
        return iop_queries

    ###########################################
    ###        SUB-ROUTINES

    def get_evaluation_point(self, num_leaf):
        field = self.field
        return field(num_leaf) + field(1)
    
    def get_num_leaf(self, query):
        field = self.field
        return int(query - field(1))

    def get_serializer(self):
        raise NotImplementedError()

    def hash_leaf(self, num_leaf, salt, leaf_data):
        raise NotImplementedError()

    def commit_leaves(self, coms):
        tree_factory = self.tree_factory
        tree = tree_factory(coms)
        root = tree.get_root()
        return tree, root
    
    def hash_merkle_root(self, salt, root):
        raise NotImplementedError()

    def xof_decs_challenge(self, hash_mt, gamma_size):
        raise NotImplementedError()
    
    def xof_decs_opening(self, counter, binding):
        raise NotImplementedError()

    def derive_decs_challenge(self, hash_mt):
        return derive_rlc_challenge(
            self.field, self.eta, self.nb_polys,
            lambda x: self.xof_decs_challenge(hash_mt, x),
            self.format_challenge
        )
    
    def build_commitment_digest(self, hash_mt, eps):
        eta = self.eta
        serializer = self.get_serializer()

        digest = hash_mt
        for j in range(eta):
            digest += serializer.serialize(eps[j])
        return digest

    def build_partial_proof(self, opening_dec_masks, eps):
        eta = self.eta
        degree = self.degree
        nb_dec_queries = self.nb_queries
        serializer = self.get_serializer()

        proof  = serializer.dumps(opening_dec_masks, (nb_dec_queries, eta))
        high_eps = MultiDimArray((eta,))
        for k in range(eta):
            high_eps[k] = eps[k][nb_dec_queries:] # keep `degree+1-nb_dec_queries` coefficients
        proof += serializer.dumps(high_eps, (eta, degree+1-nb_dec_queries))
        return proof
    
    def get_partial_proof_size(self):
        vec = self.get_serializer().get_serialized_size
        return self.nb_queries * vec(self.eta) + self.eta * vec(self.degree+1-self.nb_queries)
    
    def parse_partial_proof(self, proof):
        eta = self.eta
        degree = self.degree
        nb_dec_queries = self.nb_queries
        serializer = self.get_serializer()

        opening_dec_masks, proof = serializer.reads(proof, (nb_dec_queries, eta))
        high_eps, proof = serializer.reads(proof, (eta, degree+1-nb_dec_queries))
        return (opening_dec_masks, high_eps), proof

    def open_leaves(self, tree, open_columns):
        if tree.require_sorted_indexes():
            open_columns = sorted(open_columns)
        auth = tree.get_authentication_path(open_columns)
        return auth

    def recompute_root(self, proof, opened_leaves):
        tree_factory = self.tree_factory
        if tree_factory.require_sorted_indexes():
            opened_leaves = sorted(opened_leaves, key=lambda x: x[0])
        auth_size = tree_factory.get_authentication_path_size([
            idx for (idx, _) in opened_leaves
        ])
        auth, proof = Buffer.reads(proof, auth_size)
        return tree_factory.get_root_from_authentication_path(
            opened_leaves, auth
        ), proof
    
    def recover_polynomial(self, high, degree, iop_queries, evals):
        return LPolynomialUtils.restore(high, degree, [
            (eval_point, evals[i]) for i, eval_point in enumerate(iop_queries)
        ])
