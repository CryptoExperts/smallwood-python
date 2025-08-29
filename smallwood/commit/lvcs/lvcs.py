from sage.all import PolynomialRing
from utils.log.section import LogSection
from utils import Buffer, MultiDimArray, LPolynomialUtils
from utils.challenges import RLCChallengeType

class LVCS:
    def __init__(self, **kwargs):
        self._field = kwargs.pop('field')
        self._row_length = kwargs.pop('row_length')
        self._nb_rows = kwargs.pop('nb_rows')
        self._nb_queries = kwargs.pop('nb_queries')

        tree_factory = kwargs.pop('tree_factory')
        decs_nb_queries = kwargs.pop('decs_nb_queries')
        decs_eta = kwargs.pop('decs_eta')
        decs_pow_opening = kwargs.pop('decs_pow_opening', 0)
        decs_format_challenge = kwargs.pop('decs_format_challenge', RLCChallengeType.POWERS)

        # Initialize DECS
        nb_polys = self._nb_rows
        degree = self._row_length + decs_nb_queries - 1

        decs_class = self.get_decs_class()
        self._decs = decs_class(
            field=self.field,
            nb_polys=nb_polys,
            degree=degree,
            tree_factory=tree_factory,
            nb_queries=decs_nb_queries,
            eta=decs_eta,
            pow_opening=decs_pow_opening,
            format_challenge=decs_format_challenge,
            **kwargs
        )

    def get_decs_class(self):
        from smallwood.commit.decs import DECS
        return DECS

    @property
    def field(self):
        return self._field
    
    @property
    def row_length(self):
        return self._row_length

    @property
    def nb_rows(self):
        return self._nb_rows
    
    @property
    def nb_queries(self):
        return self._nb_queries
    
    @property
    def decs(self):
        return self._decs

    def get_interpolation_points(self):
        nb_eval_points = self.row_length+self.decs.nb_queries
        field = self.field
        return [field(-i) for i in range(nb_eval_points)]

    def get_security(self):
        sec_dec, _ = self.decs.get_security()
        sec_opening = self.decs.get_opening_security()

        return min(sec_dec, sec_opening), {
            'decs_check': sec_dec,
            'decs_opening': sec_opening,
        }

    def has_variable_proof_size(self):
        return self.decs.has_variable_proof_size()

    def get_proof_size(self, with_details=False):
        vec = self.get_serializer().get_serialized_size

        proof_size_d = {}
        proof_size_d['associated_rnd + dec_opened_values_sub'] = self.get_partial_proof_size()
        proof_size_d['dec_aux'] = self.decs.get_opening_aux_size()
        dec_proof_size, dec_proof_size_d = self.decs.get_proof_size(with_details=True)

        proof_size = sum(proof_size_d.values()) + dec_proof_size
        if with_details:
            proof_size_d['dec_proof'] = dec_proof_size_d
            return proof_size, proof_size_d
        else:
            return proof_size

    def get_averaged_proof_size(self, with_details=False):
        vec = self.get_serializer().get_serialized_size

        proof_size_d = {}
        proof_size_d['associated_rnd'] = self.nb_queries * vec(self.decs.nb_queries)
        proof_size_d['dec_opened_values'] = self.decs.nb_queries * vec(self.nb_rows-self.nb_queries)
        proof_size_d['dec_aux'] = self.decs.get_opening_aux_size()
        dec_proof_size, dec_proof_size_d = self.decs.get_averaged_proof_size(with_details=True)

        proof_size = sum(proof_size_d.values()) + dec_proof_size
        if with_details:
            proof_size_d['dec_proof'] = dec_proof_size_d
            return proof_size, proof_size_d
        else:
            return proof_size

    def commit(self, salt, rows):
        F = self.field
        R = PolynomialRing(F, name='X')

        extended_rows = []
        assert len(rows) == self.nb_rows
        for row in rows:
            assert len(row) == self.row_length
            extended_rows.append(
                row + [F.random_element() for _ in range(self.decs.nb_queries)]
            )

        interpolation_points = self.get_interpolation_points()
        dec_polynomials = [
            R.lagrange_polynomial([
                (interpolation_points[i], value)
                for i, value in enumerate(erow)
            ])
            for erow in extended_rows
        ]

        (commitment, state_dec) = self.decs.commit(salt, dec_polynomials)
        state = (state_dec, extended_rows, dec_polynomials) 
        return (commitment, state)

    def open(self, state, iop_queries, fullrank_cols, binding=[]):
        (state_dec, extended_rows, dec_polynomials) = state
        F = self.field

        iop_responses = []
        associated_rnd = []

        import numpy as np
        assert len(iop_queries) == self.nb_queries
        for iop_query in iop_queries:
            assert len(iop_query) == len(dec_polynomials)
            extended_iop_response = np.array([F(0)]*len(extended_rows[0]))
            for i, coeff in enumerate(iop_query):
                extended_iop_response += coeff * np.array(extended_rows[i])
            extended_iop_response = list(extended_iop_response)
            iop_responses.append(
                extended_iop_response[:self.row_length]
            )
            associated_rnd.append(
                extended_iop_response[self.row_length:]
            )
        
        com_iop_responses = self.hash_challenge_opening_decs(binding, iop_responses, associated_rnd)

        (dec_queries, dec_aux) = self.decs.get_random_opening(binding=com_iop_responses)
        dec_opened_values, dec_proof = self.decs.open(state_dec, dec_queries)

        proof = self.build_partial_proof(associated_rnd, dec_opened_values, fullrank_cols)
        proof += dec_aux + dec_proof
        return (iop_responses, proof)

    def recompute_commitment(self, salt, iop_queries, fullrank_cols, iop_responses, proof, binding=[], is_standalone_proof=True):
        F = self.field

        (associated_rnd, hint_dec_opened_values), proof = self.parses_partial_proof(proof)
        dec_aux, proof = Buffer.reads(proof, (self.decs.get_opening_aux_size(),))

        with LogSection('Derive Com IOP Response'):
            com_iop_responses = self.hash_challenge_opening_decs(binding, iop_responses, associated_rnd)

        with LogSection('DEC Random Opening'):
            dec_queries = self.decs.recompute_random_opening(dec_aux, binding=com_iop_responses)

        with LogSection('Interpolate Combi Polys'):
            polys_Q = MultiDimArray((self.nb_queries,))
            interpolation_points = self.get_interpolation_points()
            for k in range(self.nb_queries):
                polys_Q[k] =LPolynomialUtils.restore(
                    [], self.decs.nb_queries+self.row_length-1,
                    [
                        (interpolation_points[i], value)
                        for i, value in enumerate(iop_responses[k] + associated_rnd[k])
                    ]
                )
            v_ = MultiDimArray((self.decs.nb_queries,self.nb_queries))
            for j, dec_query in enumerate(dec_queries):
                for k, poly_Q in enumerate(polys_Q):
                    v_[j][k] = LPolynomialUtils.eval(poly_Q, dec_query)

        with LogSection('Recompute Associated Rnd'):
            dec_opened_values = self.restore_dec_opened_values(v_, hint_dec_opened_values, iop_queries, fullrank_cols)

        with LogSection('DEC Recompute Commitment'):
            com, proof = self.decs.recompute_commitment(
                salt, dec_queries, dec_opened_values, proof,
                is_standalone_proof=False,
            )
            if is_standalone_proof:
                assert len(proof) == 0
                return com
            else:
                return com, proof

    def verify(self, salt, commitment, iop_queries, fullrank_cols, iop_responses, proof, binding=[]):
        commitment_ = self.recompute_commitment(salt, iop_queries, fullrank_cols, iop_responses, proof, binding=binding)
        return commitment == commitment_

    def get_random_opening(self, binding=[]):
        iop_queries = self.xof_lvcs_opening(binding)
        iop_queries = [
            iop_queries[i*self.nb_rows:(i+1)*self.nb_rows]
            for i in range(self.nb_queries)
        ]
        return (iop_queries, [])

    def recompute_random_opening(self, aux, binding=[]):
        assert len(aux) == 0
        return self.get_random_opening(binding=binding)[0]

    def hash_challenge_opening_decs(self, binding, iop_responses, associated_rnd):
        raise NotImplementedError()

    def xof_lvcs_opening(self, binding):
        raise NotImplementedError()

    def get_serializer(self):
        return self._decs.get_serializer()
    
    def build_partial_proof(self, associated_rnd, dec_opened_values, fullrank_cols):
        serializer = self.get_serializer()
        proof  = serializer.dumps(
            associated_rnd, (self.nb_queries, self.decs.nb_queries),
        )
        sub_dec_opened_value = MultiDimArray((self.decs.nb_queries, self.nb_rows-self.nb_queries))
        for j in range(self.decs.nb_queries):
            sub_dec_opened_value[j] = []
            ind = 0
            for k in range(self.nb_rows):
                if ind < self.nb_queries and fullrank_cols[ind] == k:
                    ind += 1
                else:
                    sub_dec_opened_value[j].append(
                        dec_opened_values[j][k]
                    )
        proof += serializer.dumps(
            sub_dec_opened_value, (self.decs.nb_queries, self.nb_rows-self.nb_queries),
        )
        return proof
    
    def get_partial_proof_size(self):
        vec = self.get_serializer().get_serialized_size
        return self.nb_queries * vec(self.decs.nb_queries) + self.decs.nb_queries * vec(self.nb_rows-self.nb_queries)

    def parses_partial_proof(self, proof):
        serializer = self.get_serializer()
        associated_rnd, proof = serializer.reads(proof, (self.nb_queries, self.decs.nb_queries))
        sub_dec_opened_values, proof = serializer.reads(proof, (self.decs.nb_queries, self.nb_rows-self.nb_queries))
        return (associated_rnd, sub_dec_opened_values), proof

    def restore_dec_opened_values(self, v_, sub_dec_opened_values, iop_queries, fullrank_cols):
        coeffs_part1 = MultiDimArray((self.nb_queries, self.nb_queries))
        coeffs_part2 = MultiDimArray((self.nb_queries, self.nb_rows-self.nb_queries))
        for j in range(self.nb_queries):
            ind = 0
            for k in range(self.nb_rows):
                if ind < self.nb_queries and fullrank_cols[ind] == k:
                    coeffs_part1[j][ind] = iop_queries[j][k]
                    ind += 1
                else:
                    coeffs_part2[j][k-ind] = iop_queries[j][k]

        from sage.all import matrix
        import numpy as np
        coeffs_part1_inv = np.array(matrix(coeffs_part1).inverse())
        coeffs_part2 = np.array(coeffs_part2)

        dec_opened_values = MultiDimArray((self.decs.nb_queries, self.nb_rows))
        for j in range(self.decs.nb_queries):
            res = list(coeffs_part1_inv.dot((np.array(v_[j]) - coeffs_part2.dot(np.array(sub_dec_opened_values[j])))))
            ind = 0
            for k in range(self.nb_rows):
                if ind < self.nb_queries and fullrank_cols[ind] == k:
                    dec_opened_values[j][k] = res[ind]
                    ind += 1
                else:
                    dec_opened_values[j][k] = sub_dec_opened_values[j][k-ind]

        return dec_opened_values
