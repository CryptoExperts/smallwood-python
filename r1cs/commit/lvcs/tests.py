import unittest

class TestLVCSWithAOHash_R1CS(unittest.TestCase):
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

    def _test_r1cs(self, lvcs):
        F = lvcs.field

        from r1cs.r1cs import R1CS
        r1cs = R1CS(F)

        fullrank_cols = list(range(lvcs.nb_queries))

        ### Build Verification R1CS Constraints
        salt = r1cs.new_registers(1, 'salt')
        iop_queries_ = [
            r1cs.new_registers(lvcs.nb_rows, f'iop_queries_v{j}')
            for j in range(lvcs.nb_queries)
        ]
        opened_values = [
            r1cs.new_registers(lvcs.row_length, f'opened_values_v{j}')
            for j in range(lvcs.nb_queries)
        ]
        assert not lvcs.has_variable_proof_size()
        proof = r1cs.new_registers(lvcs.get_proof_size(), 'proof')
        com = lvcs.recompute_commitment(salt, iop_queries_, fullrank_cols, opened_values, proof)

        print(r1cs.get_info())
        print('nb_linear', r1cs.nb_linear_equations())
        print('nb_vars_used_only_once', r1cs.nb_variables_used_only_once())
        print('nb_useless_equations', r1cs.nb_usedless_equations())

        dependencies = r1cs.get_dependencies()
        print(f'nb_dep={len(dependencies)}')

        ### Testing
        # Data
        rows = []
        for _ in range(lvcs.nb_rows):
            rows.append(
                [F.random_element() for _ in range(lvcs.row_length)]
            )

        # Commit
        salt = [F.random_element()]
        com, state = lvcs.commit(salt, rows)

        # Open
        challenge_rnd = [F.random_element()]
        iop_queries, aux = lvcs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = lvcs.open(state, iop_queries, fullrank_cols)

        # Check that the open values are correct
        for i, iop_query in enumerate(iop_queries):
            for j in range(lvcs.row_length):
                res = sum(rows[k][j]*iop_query[k] for k in range(lvcs.nb_rows))
                self.assertTrue(opened_values[i][j] == res)

        # Verify
        iop_queries_ = lvcs.recompute_random_opening(aux, binding=challenge_rnd)
        com_ = lvcs.recompute_commitment(salt, iop_queries_, fullrank_cols, opened_values, proof)
        self.assertTrue(com == com_)

        aux = {
            'salt': salt,
            'proof': proof,
        }
        for j in range(lvcs.nb_queries):
            aux[f'iop_queries_v{j}'] = iop_queries_[j]
        for j in range(lvcs.nb_queries):
            aux[f'opened_values_v{j}'] = opened_values[j]
        data = r1cs.resolve(aux)

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

    def _test_aohash_expanded_r1cs(self, setup):
        from r1cs.commit.merkle import MerkleTreeFactoryWithAOHash_R1CS
        from r1cs.commit.lvcs import LVCSWithAOHash_R1CS
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup
        nb_rows = 10
        row_length = 30
        nb_dec_queries = 10
        tree_factory = MerkleTreeFactoryWithAOHash_R1CS(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )

        lvcs = LVCSWithAOHash_R1CS(
            field = F,
            row_length = row_length,
            nb_rows = nb_rows,
            nb_queries = 3,

            commitment_size = hash_leaves.get_capacity(),
            hash_xof = hash_leaves,

            tree_factory = tree_factory,
            decs_nb_queries = nb_dec_queries,
            decs_eta = 2,
            decs_hash_leaves = hash_leaves,
            decs_opening_challenge_size = decs_opening_challenge_size
        )
        self._test_r1cs(lvcs)

    def test_aohash_expanded_r1cs_large_field(self):
        setup = self._test_setup_large_field()
        self._test_aohash_expanded_r1cs(setup)

    def test_aohash_expanded_r1cs_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_aohash_expanded_r1cs(setup)
