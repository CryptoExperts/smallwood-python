import unittest

class TestLVCSWithAOHash(unittest.TestCase):
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

    def _test_running(self, lvcs):
        F = lvcs.field

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
        fullrank_cols = list(range(lvcs.nb_queries))
        opened_values, proof = lvcs.open(state, iop_queries, fullrank_cols)
        if lvcs.has_variable_proof_size():
            assert len(proof) <= lvcs.get_proof_size()
        else:
            assert len(proof) == lvcs.get_proof_size()

        # Check that the open values are correct
        for i, iop_query in enumerate(iop_queries):
            for j in range(lvcs.row_length):
                res = sum(rows[k][j]*iop_query[k] for k in range(lvcs.nb_rows))
                self.assertTrue(opened_values[i][j] == res)

        # Verify
        iop_queries_ = lvcs.recompute_random_opening(aux, binding=challenge_rnd)
        com_ = lvcs.recompute_commitment(salt, iop_queries_, fullrank_cols, opened_values, proof)
        self.assertTrue(com == com_)

    def _test_aohash_running(self, setup):
        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        from smallwood.commit.lvcs.aohash import LVCSWithAOHash
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup
        nb_rows = 10
        row_length = 30
        nb_dec_queries = 10
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = False,
        )

        lvcs = LVCSWithAOHash(
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
        self._test_running(lvcs)

    def test_aohash_running_large_field(self):
        setup = self._test_setup_large_field()
        self._test_aohash_running(setup)

    def test_aohash_running_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_aohash_running(setup)
        
    def _test_aohash_expanded_running(self, setup):
        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        from smallwood.commit.lvcs.aohash import LVCSWithAOHash
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup
        nb_rows = 10
        row_length = 30
        nb_dec_queries = 10
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )

        lvcs = LVCSWithAOHash(
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
        self._test_running(lvcs)

    def test_aohash_expanded_running_large_field(self):
        setup = self._test_setup_large_field()
        self._test_aohash_expanded_running(setup)

    def test_aohash_expanded_running_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_aohash_expanded_running(setup)
