
from math import ceil
from utils import MultiDimArray, PolynomialUtils, Buffer
from sage.all import flatten
from utils.polynomial import LPolynomialUtils
from utils.log.section import LogSection
from utils.challenges import RLCChallengeType, derive_rlc_challenge, get_rlc_bit_security

class SmallWood:
    def __init__(self, pacs, piop_nb_queries, piop_rho, layout_beta, piop_format_challenge=RLCChallengeType.POWERS):
        self._pacs = pacs
        self._nb_queries = piop_nb_queries
        self._rho = piop_rho
        self._layout_beta = layout_beta
        self._format_challenge = piop_format_challenge

        F = self.pacs.get_field()
        from sage.all import PolynomialRing
        self._polynomial_ring = PolynomialRing(F, 'X')

        self._pcs = self.get_pcs(
            degrees = [self.input_degree]*self.pacs.get_nb_wit_rows() + [self.deg_q]*self._rho,
        )
        assert self._pcs.field == F

    def has_variable_proof_size(self):
        return self._pcs.has_variable_proof_size()

    def get_proof_size(self, with_details=False):
        proof_size_d = {}
        proof_size_d['salt'] = self.get_salt_size()
        proof_size_d['h_piop'] = self.get_hash_digest_size()
        proof_size_d['piop_proof + piop_responses'] = self.get_partial_proof_size()
        dec_proof_size, dec_proof_size_d = self._pcs.get_proof_size(with_details=True)

        proof_size = sum(proof_size_d.values()) + dec_proof_size
        if with_details:
            proof_size_d['opening_proof'] = dec_proof_size_d
            return proof_size, proof_size_d
        else:
            return proof_size

    def get_averaged_proof_size(self, with_details=False):
        proof_size_d = {}
        proof_size_d['salt'] = self.get_salt_size()
        proof_size_d['h_piop'] = self.get_hash_digest_size()
        proof_size_d['piop_proof + piop_responses'] = self.get_partial_proof_size()
        dec_proof_size, dec_proof_size_d = self._pcs.get_averaged_proof_size(with_details=True)

        proof_size = sum(proof_size_d.values()) + dec_proof_size
        if with_details:
            proof_size_d['opening_proof'] = dec_proof_size_d
            return proof_size, proof_size_d
        else:
            return proof_size
    
    def get_layout_lvcs(self, layout):
        raise NotImplementedError()
        
    def get_pcs(self, degrees):
        from smallwood.commit.pcs.layouts import GenericUnivariateLayout
        layout = GenericUnivariateLayout(
            degrees = degrees,
            poly_col_size = degrees[0] - self.nb_queries + 1,
            nb_queries = self.nb_queries,
            beta = self.layout_beta,
        )
        return self.get_layout_lvcs(layout)

    @property
    def polynomial_ring(self):
        return self._polynomial_ring

    @property
    def field(self):
        return self.pacs.get_field()

    def get_witness_support(self):
        field = self.field
        nb_wit_cols = self.pacs.get_nb_wit_cols()
        return [
            field(i)
            for i in range(nb_wit_cols)
        ]

    @property
    def pacs(self):
        return self._pacs

    @property
    def nb_queries(self):
        return self._nb_queries

    @property
    def rho(self):
        return self._rho

    @property
    def format_challenge(self):
        return self._format_challenge

    @property
    def layout_beta(self):
        return self._layout_beta

    @property
    def pcs(self):
        return self._pcs

    @property
    def input_degree(self):
        return self.nb_queries + self.pacs.get_nb_wit_cols() - 1

    @property
    def deg_q(self):
        return self.pacs.get_constraint_degree()*self.input_degree + self.pacs.get_nb_wit_cols()

    def get_security(self):
        from math import log2
        p = self.field.order()
        m1 = self.pacs.get_nb_parallel_constraints()
        m2 = self.pacs.get_nb_aggregated_constraints()
        nb_wit_cols = self.pacs.get_nb_wit_cols()

        sec_fpp = get_rlc_bit_security(self.field, self.rho, m1*nb_wit_cols + m2, self.format_challenge)
        sec_query = self.nb_queries*log2(p/self.deg_q)
        sec_pcs, sec_pcs_d = self._pcs.get_security()
        return min(sec_fpp, sec_query, sec_pcs), {
            'iop_fpp': sec_fpp,
            'iop_query': sec_query,
            **sec_pcs_d,
        }

    def prove(self, witness, binding=None):
        field = self.field

        ### 1. Initialization
        with LogSection('Initialization'):
            # Sample a random salt
            salt = self.sample_salt()
            #self._compute_linear_encoding()
            import numpy as np
            witness = np.array(witness).reshape((self.pacs.get_nb_wit_rows(), self.pacs.get_nb_wit_cols()))
            witness = [
                [
                    witness[i,j]
                    for j in range(self.pacs.get_nb_wit_cols())
                ]
                for i in range(self.pacs.get_nb_wit_rows())
            ]

        ### 2. Polynomial Commitment
        with LogSection('Polynomial Commitment'):
            
            # Build witness polynomials
            wit_polys = []
            wit_support = self.get_witness_support()
            for row in witness:
                assert self.pacs.get_nb_wit_cols()
                poly = PolynomialUtils.restore_from_relations(
                    self.polynomial_ring,
                    [(row[i], [wit_support[i]]) for i in range(self.pacs.get_nb_wit_cols())],
                    [field.random_element() for _ in range(self.nb_queries)],
                    self.input_degree,
                )
                wit_polys.append(poly)
            
            # Build mask polynomials
            mask_polys = [
                PolynomialUtils.restore_from_relations(
                    self.polynomial_ring,
                    [(field(0), wit_support)],
                    [field.random_element() for _ in range(self.deg_q)],
                    self.deg_q,
                )
                for _ in range(self.rho)
            ]

            # Compute polynomial commitment
            commitment, commit_state = self.pcs.commit(salt, wit_polys + mask_polys)

        ### 3. Run Polynomial IOP
        with LogSection('Run the Polynomial IOP'):
            ### 3.1. IOP Verifier: send batching randomness
            commitment_with_binding = binding+commitment if binding else commitment
            h_polys = self.hash_poly_commitment(commitment_with_binding)
            batching_rnd = self.derive_fpp_challenge(h_polys)

            ### 3.2. IOP Prover: build PIOP polynomials
            (theta_polys, theta_prime_polys) = self.get_polys_theta()
            para_constraints = self.evaluate_parallel_constraints_over_polynomials(wit_polys, theta_polys)
            aggr_constraints = self.evaluate_aggregated_constraints_over_polynomials(wit_polys, theta_prime_polys)
            piop_polys = self.batch_polys(para_constraints, aggr_constraints, batching_rnd)
            piop_polys = self.add_masks(piop_polys, mask_polys)
            piop_polys = [
                PolynomialUtils.to_list(poly, self.deg_q)
                for poly in piop_polys
            ]
            piop_proof = flatten([poly[self.nb_queries+1:] for poly in piop_polys])

            ### 3.3. IOP Verifier: query
            h_piop = self.hash_piop_transcript(h_polys, piop_polys)
            piop_queries = self.xof_piop_opening(h_piop)

        ### 4. Open the commitment
        with LogSection('Open the commitment'):
                piop_responses, opening_proof = self.pcs.open(commit_state, piop_queries, binding=h_piop)

        ### 5. Build proof transcript
        with LogSection('Build proof transcript'):
            transcript = salt + h_piop
            assert len(salt) == self.get_salt_size()
            assert len(h_piop) == self.get_hash_digest_size()
            transcript += self.build_partial_proof(piop_proof, piop_responses)
            transcript += opening_proof
        return transcript

    def verify(self, transcript, binding=None):
        #self._compute_linear_encoding()
        salt, transcript = Buffer.reads(transcript, (self.get_salt_size(),))
        h_piop, transcript = Buffer.reads(transcript, (self.get_hash_digest_size(),))
        (piop_proof, piop_responses), transcript = self.parses_partial_proof(transcript)

        ### 1. Recompute Witness Commitment
        with LogSection('Recomputing Wit Commitment'):
            opening_proof = transcript
            piop_queries = self.xof_piop_opening(h_piop)
            commitment = self.pcs.recompute_commitment(salt, piop_queries, piop_responses, opening_proof, binding=h_piop)

        ### 2. Recompute IOP Output
        with LogSection('Recompute IOP Output'):
            nb_queries = self.nb_queries
            rho = self.rho

            ### 2.1. IOP Verifier: send batching randomness
            with LogSection('Derive IOP Verifier Challenge'):
                commitment_with_binding = binding+commitment if binding else commitment
                h_polys = self.hash_poly_commitment(commitment_with_binding)
                batching_rnd = self.derive_fpp_challenge(h_polys)

            ### 2.2. IOP Prover: build tested polynomials
            with LogSection('Compute Prover Response'):
                hint_piop_polys = MultiDimArray((rho,))
                for num in range(rho):
                    hint_piop_polys[num], piop_proof = piop_proof[:self.deg_q-nb_queries], piop_proof[self.deg_q-nb_queries:]
                assert len(piop_proof) == 0

                piop_polys = MultiDimArray((rho,))

                input_evals_all = [piop_responses[i][:-rho] for i in range(nb_queries)]
                mask_evals_all  = [piop_responses[i][-rho:] for i in range(nb_queries)]

                # Compute Evaluation
                piop_evals = MultiDimArray((nb_queries,))
                from .pacs.pacs import format_theta
                (theta_polys, theta_prime_polys) = self.get_polys_theta()
                for num_query in range(nb_queries):
                    input_evals = input_evals_all[num_query]
                    mask_evals = mask_evals_all[num_query]
                    theta_evals = format_theta(theta_polys, lambda x: LPolynomialUtils.eval(x, piop_queries[num_query]))
                    theta_prime_evals = format_theta(theta_prime_polys, lambda x: LPolynomialUtils.eval(x, piop_queries[num_query]))
                    para_constraints = self.evaluate_parallel_constraints(input_evals, theta_evals)
                    aggr_constraints = self.evaluate_aggregated_constraints(input_evals, theta_prime_evals)
                    piop_evals[num_query] = self.batch_polys(para_constraints, aggr_constraints, batching_rnd, eval_point=piop_queries[num_query])
                    piop_evals[num_query] = self.add_masks(piop_evals[num_query], mask_evals)

                # Interpolate
                for num in range(self.rho):
                    piop_polys[num] = self.recover_polynomial(
                        hint_piop_polys[num], self.deg_q,
                        [(piop_evals[num_query][num], [piop_queries[num_query]]) for num_query in range(nb_queries)]
                    )

            ### 2.3. IOP Verifier: query
            with LogSection('Derive PIOP Queries'):
                h_piop_ = self.hash_piop_transcript(h_polys, piop_polys)

            return h_piop_ == h_piop

    def get_serializer(self):
        return self._pcs.get_serializer()

    def hash_poly_commitment(self, binding):
        raise NotImplementedError()

    def xof_fpp_challenge(self, binding, gamma_size):
        raise NotImplementedError()

    def hash_piop_transcript(self, h_polys, piop_polys):
        raise NotImplementedError()
    
    def xof_piop_opening(self, h_piop):
        raise NotImplementedError()

    def derive_fpp_challenge(self, hash_mt):
        nb_wit_cols = self.pacs.get_nb_wit_cols()
        rho = self.rho

        m1 = self.pacs.get_nb_parallel_constraints()
        m2 = self.pacs.get_nb_aggregated_constraints()
        wit_support = self.get_witness_support()

        batching_rnd = derive_rlc_challenge(
            field = self.field,
            nb_combinations = rho,
            nb_coefficients = m1*nb_wit_cols + m2,
            format_challenge = self.format_challenge,
            random_felt_fnc = lambda x: self.xof_fpp_challenge(hash_mt, x)
        )

        poly_gamma = MultiDimArray((rho,m1))
        gamma_prime = MultiDimArray((rho,))
        for num in range(rho):
            for j in range(m1):
                #poly_gamma[num][j] = PolynomialUtils.restore_only_from_relation(
                #    self.polynomial_ring,
                #    [
                #        (batching_rnd[num][nb_wit_cols*j+i], [wit_support[i]])
                #        for i in range(nb_wit_cols)
                #    ],
                #    nb_wit_cols-1
                #)
                poly_gamma[num][j] = batching_rnd[num][nb_wit_cols*j:nb_wit_cols*(j+1)]
            gamma_prime[num] = batching_rnd[num][m1*nb_wit_cols:]

        return poly_gamma, gamma_prime

    def batch_polys(self, para_constraints, aggr_constraints, batch_rnd, eval_point=None):
        field = self.field
        rho = self.rho
        (poly_gamma, gamma_prime) = batch_rnd
        if eval_point:
            poly_gamma = [
                [LPolynomialUtils.eval(poly, eval_point) for poly in polys]
                for polys in poly_gamma
            ]
        else:
            poly_gamma = [
                [self._polynomial_ring(poly) for poly in polys]
                for polys in poly_gamma
            ]
        nb_parallel_constraints = self.pacs.get_nb_parallel_constraints()
        nb_aggregated_constraints = self.pacs.get_nb_aggregated_constraints()

        poly_out = [field(0) for _ in range(rho)]
        for num in range(rho):
            for j in range(nb_parallel_constraints):
                poly_out[num] += poly_gamma[num][j] * para_constraints[j]
            for j in range(nb_aggregated_constraints):
                poly_out[num] += gamma_prime[num][j] * aggr_constraints[j]
        return poly_out

    # def _compute_linear_encoding(self):
    #     R = self.polynomial_ring
    #     A, t = self.get_linear_matrix()
    #     A_encoding = [
    #         [
    #             R.lagrange_polynomial([
    #                 (self.config.wit_positions[idx], A[i,j*cfg.packing_size+idx]) for idx in range(cfg.packing_size)
    #             ])
    #             for j in range(A.dimensions()[1] // cfg.packing_size)
    #         ] for i in range(A.dimensions()[0])
    #     ]
    #     self.linear_matrix_encoding = (A_encoding, t)

    def get_polys_theta(self):
        nb_wit_cols = self.pacs.get_nb_wit_cols()
        wit_support = self.get_witness_support()

        theta = self.pacs.get_theta()
        from .pacs.pacs import format_theta
        theta_polys = format_theta(theta, fnc=lambda x: self.recover_polynomial2(
            [], nb_wit_cols-1, [(wit_support[i], x[i]) for i in range(nb_wit_cols)]
        ))

        theta_prime = self.pacs.get_theta_()
        from .pacs.pacs import format_theta
        wit_support = self.get_witness_support()
        theta_prime_polys = format_theta(theta_prime, fnc=lambda x: self.recover_polynomial2(
            [], nb_wit_cols-1, [(wit_support[i], x[i]) for i in range(nb_wit_cols)]
        ))

        return (theta_polys, theta_prime_polys)

    def evaluate_parallel_constraints_over_polynomials(self, input_polys, theta_polys):
        nb_wit_cols = self.pacs.get_nb_wit_cols()
        nb_parallel_constraints = self.pacs.get_nb_parallel_constraints()
        wit_support = self.get_witness_support()

        field = self.field
        eval_points = [field(i) for i in range(self.deg_q+1)]
        evals = []
        from .pacs.pacs import format_theta
        for eval_point in eval_points:
            wit_evals = [input_poly(eval_point) for input_poly in input_polys]
            theta_evals = format_theta(theta_polys, lambda x: LPolynomialUtils.eval(x, eval_point))
            evals.append(self.pacs.evaluate_parallel_constraints(wit_evals, theta_evals))
        poly_constraints = [
            PolynomialUtils.restore(
                self.polynomial_ring, [],
                self.deg_q, [(eval_point, evals[j][i]) for j, eval_point in enumerate(eval_points)]
            )
            for i in range(nb_parallel_constraints)
        ]
        for num, poly_constraint in enumerate(poly_constraints):
            for i in range(nb_wit_cols):
                assert poly_constraint(wit_support[i]) == field(0), f'A polynomial constraint is not satisfied (num={num}, eval={i}).'
        return poly_constraints

    def evaluate_parallel_constraints(self, input_evals, theta_evals):
        return self.pacs.evaluate_parallel_constraints(input_evals, theta_evals)

    def evaluate_aggregated_constraints_over_polynomials(self, input_polys, theta_prime_polys):
        nb_aggregated_constraints = self.pacs.get_nb_aggregated_constraints()
        nb_wit_cols = self.pacs.get_nb_wit_cols()
        wit_support = self.get_witness_support()

        field = self.field
        eval_points = [field(i) for i in range(self.deg_q+1)]
        evals = []
        from .pacs.pacs import format_theta
        for eval_point in eval_points:
            wit_evals = [input_poly(eval_point) for input_poly in input_polys]
            theta_evals = format_theta(theta_prime_polys, lambda x: LPolynomialUtils.eval(x, eval_point))
            evals.append(self.pacs.evaluate_aggregated_constraints(wit_evals, theta_evals))

        poly_constraints = [
            PolynomialUtils.restore(
                self.polynomial_ring, [],
                self.deg_q, [(eval_point, evals[j][i]) for j, eval_point in enumerate(eval_points)]
            )
            for i in range(nb_aggregated_constraints)
        ]

        for num in range(nb_aggregated_constraints):
            tot_sum = field(0)
            for i in range(nb_wit_cols):
                tot_sum += poly_constraints[num](wit_support[i])
            assert tot_sum == field(0), 'A linear constraint is not satisfied.'
        return poly_constraints

    def evaluate_aggregated_constraints(self, input_evals, theta_prime_evals):
        return self.pacs.evaluate_aggregated_constraints(input_evals, theta_prime_evals)

    def add_masks(self, poly_out, mask_polys):
        return [
            poly_out[num] + mask_polys[num]
            for num in range(self.rho)
        ]

    def recover_polynomial(self, high, degree, evals):
        field = self.field
        wit_support = self.get_witness_support()
        return LPolynomialUtils.restore_from_relations(
            [(field(0), [wit_support[idx] for idx in range(self.pacs.get_nb_wit_cols())])] + evals,
            high, degree
        )
    
    def recover_polynomial2(self, high, degree, evals):
        return LPolynomialUtils.restore(high, degree, evals)

    def get_salt_size(self):
        raise NotImplementedError()

    def sample_salt(self):
        raise NotImplementedError()

    def build_partial_proof(self, piop_proof, piop_responses):
        serializer = self.get_serializer()
        proof  = serializer.dumps(piop_proof, ((self.deg_q-self.nb_queries)*self.rho,))
        proof += serializer.dumps(piop_responses, ((self.nb_queries, self.pacs.get_nb_wit_rows()+self.rho)))
        return proof
    
    def get_partial_proof_size(self):
        vec = self.get_serializer().get_serialized_size
        return vec((self.deg_q-self.nb_queries)*self.rho) + self.nb_queries * vec(self.pacs.get_nb_wit_rows()+self.rho)

    def parses_partial_proof(self, proof):
        serializer = self.get_serializer()
        piop_proof, proof = serializer.reads(proof, ((self.deg_q-self.nb_queries)*self.rho,))
        piop_responses, proof = serializer.reads(proof, ((self.nb_queries, self.pacs.get_nb_wit_rows()+self.rho)))
        return (piop_proof, piop_responses), proof

    def get_hash_digest_size(self):
        raise NotImplementedError()
