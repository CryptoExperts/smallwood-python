import unittest

class TestTensorBasedPCSWithAOHash_R1CS(unittest.TestCase):
    def _test_setup_large_field(self):
        from sage.all import FiniteField

        # Get Hash Function
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1

        from capss.hash.griffin import Griffin
        from capss.hash import SpongeHashFunction, TruncationCompressionFunction
        perm = Griffin.get(p, alpha, 4, capacity, 128)
        hash_leaves = SpongeHashFunction(perm, capacity=capacity)
        hash_merkle = {4: TruncationCompressionFunction(perm)}

        # Configure DEC Scheme
        F = FiniteField(p)
        decs_opening_challenge_size = 1
        return F, (hash_leaves, hash_merkle), decs_opening_challenge_size
    
    def _test_setup_goldilocks(self):
        from sage.all import FiniteField

        # Get Hash Function
        p = 0xffffffff00000001
        alpha = 7
        capacity = 4

        from capss.hash.griffin import Griffin
        from capss.hash import SpongeHashFunction, TruncationCompressionFunction
        perm = Griffin.get(p, alpha, 16, capacity, 128)
        hash_leaves = SpongeHashFunction(perm, capacity=capacity)
        hash_merkle = {4: TruncationCompressionFunction(perm)}

        # Configure DEC Scheme
        F = FiniteField(p)
        decs_opening_challenge_size = 2
        return F, (hash_leaves, hash_merkle), decs_opening_challenge_size
    
    def _test_r1cs(self, setup):
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup

        from sage.all import PolynomialRing
        R = PolynomialRing(F, name='X')
        X = R.gen()

        from r1cs.r1cs import R1CS
        r1cs = R1CS(F)

        degree = 13
        nb_polys = 4
        nb_queries = 2
        poly_col_size = 3
        beta = 3

        from r1cs.commit.merkle import MerkleTreeFactoryWithAOHash_R1CS
        tree_factory = MerkleTreeFactoryWithAOHash_R1CS(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )
        nb_dec_queries = 10
        decs_eta = 2

        from r1cs.commit.pcs import UnivariateTensorBasedPCSWithAOHash_R1CS
        pcs = UnivariateTensorBasedPCSWithAOHash_R1CS(
            degree = degree,
            poly_col_size = poly_col_size,
            nb_polys = nb_polys,
            nb_queries = nb_queries,
            beta = beta,

            commitment_size = hash_leaves.get_capacity(),
            hash_xof = hash_leaves,

            field = F,
            tree_factory = tree_factory,
            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            decs_hash_leaves = hash_leaves,
            decs_opening_challenge_size = decs_opening_challenge_size
        )

        ### Build Verification R1CS Constraints
        salt = r1cs.new_registers(1, 'salt')
        iop_queries_ = r1cs.new_registers(nb_queries, 'iop_queries_')
        opened_values = r1cs.new_registers((nb_queries, nb_polys), f'opened_values')
        proof = r1cs.new_registers(pcs.get_proof_size(), 'proof')
        com = pcs.recompute_commitment(salt, iop_queries_, opened_values, proof)

        print(r1cs.get_info())
        print('nb_linear', r1cs.nb_linear_equations())
        print('nb_vars_used_only_once', r1cs.nb_variables_used_only_once())
        print('nb_useless_equations', r1cs.nb_usedless_equations())

        dependencies = r1cs.get_dependencies()
        print(f'nb_dep={len(dependencies)}')

        ### Testing
        # Data
        polynomials = []
        for _ in range(nb_polys):
            polynomials.append(
                R.random_element(degree=degree)
            )

        # Commit
        salt = [F.random_element()]
        com, state = pcs.commit(salt, polynomials)

        # Open
        challenge_rnd = [F.random_element()]
        iop_queries, aux = pcs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = pcs.open(state, iop_queries)

        for num_poly in range(nb_polys):
            for num_query in range(nb_queries):
                self.assertEqual(
                    polynomials[num_poly](iop_queries[num_query]), opened_values[num_query][num_poly],
                    f'Invalid opened polynomial evaluations ({num_poly})'
                )

        # Verify
        iop_queries_ = pcs.recompute_random_opening(aux, binding=challenge_rnd)

        data = r1cs.resolve({
            'salt': salt,
            'iop_queries_': iop_queries_,
            'opened_values': opened_values,
            'proof': proof,
        })
        nb_false = 0
        nb_true = 0
        for num_eq, eq in enumerate(r1cs.equations):
            if eq.evaluate(data):
                nb_true += 1
            else:
                nb_false += 1
        print(f'nb_true={nb_true}')
        print(f'nb_false={nb_false}')
        self.assertTrue(nb_false == 0)

    def test_r1cs_large_field(self):
        setup = self._test_setup_large_field()
        self._test_r1cs(setup)

    def test_r1cs_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_r1cs(setup)
