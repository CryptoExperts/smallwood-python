import unittest


def decs_get_random_inputs(decs):
    field = decs.field
    nb_polys = decs.nb_polys
    degree = decs.degree

    from sage.all import PolynomialRing
    R = PolynomialRing(field, name='X')

    from utils import MultiDimArray
    salt = [field.random_element()]
    polys = MultiDimArray((nb_polys,))
    for i in range(nb_polys):
        polys[i] = R.random_element(degree=degree)
    
    challenge_rnd = [field.random_element()]

    return salt, polys, challenge_rnd


class TestDECSWithAOHash(unittest.TestCase):
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
        dec_opening_challenge_size = 1
        return F, (hash_leaves, hash_merkle), dec_opening_challenge_size
    
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
        dec_opening_challenge_size = 2
        return F, (hash_leaves, hash_merkle), dec_opening_challenge_size


    def _test_running(self, decs):
        from sage.all import PolynomialRing
        field = decs.field
        nb_polys = decs.nb_polys
        degree = decs.degree
        
        R = PolynomialRing(field, name='X')
        from utils import MultiDimArray

        # Commit
        salt = [field.random_element()]
        polys = MultiDimArray((nb_polys,))
        for i in range(nb_polys):
            polys[i] = R.random_element(degree=degree)
        com, state = decs.commit(salt, polys)

        # Open
        challenge_rnd = [field.random_element()]
        iop_queries, aux = decs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = decs.open(state, iop_queries)
        if decs.has_variable_proof_size():
            assert len(proof) <= decs.get_proof_size()
        else:
            assert len(proof) == decs.get_proof_size()

        # Verify
        iop_queries_ = decs.recompute_random_opening(aux, binding=challenge_rnd)
        com_ = decs.recompute_commitment(salt, iop_queries_, opened_values, proof)
        self.assertTrue(com == com_)

    def _test_aohash_running(self, setup):
        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        from smallwood.commit.decs.aohash import DECSWithAOHash
        F, (hash_leaves, hash_merkle), dec_opening_challenge_size = setup
        nb_polys = 11
        degree = 30
        nb_queries = 5
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = False,
        )
        
        decs = DECSWithAOHash(
            field = F,
            nb_polys = nb_polys,
            degree = degree,
            tree_factory = tree_factory,
            nb_queries = nb_queries,
            eta = 2,

            commitment_size = hash_leaves.get_capacity(),
            hash_leaves = hash_leaves,
            hash_xof = hash_leaves,
            opening_challenge_size = dec_opening_challenge_size,
        )
        self._test_running(decs)

    def test_aohash_running_large_field(self):
        setup = self._test_setup_large_field()
        self._test_aohash_running(setup)

    def test_aohash_running_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_aohash_running(setup)

    def _test_aohash_expanded_running(self, setup):
        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        from smallwood.commit.decs.aohash import DECSWithAOHash
        F, (hash_leaves, hash_merkle), dec_opening_challenge_size = setup
        nb_polys = 11
        degree = 30
        nb_queries = 5
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )

        decs = DECSWithAOHash(
            field = F,
            nb_polys = nb_polys,
            degree = degree,
            tree_factory = tree_factory,
            nb_queries = nb_queries,
            eta = 2,

            commitment_size = hash_leaves.get_capacity(),
            hash_leaves = hash_leaves,
            hash_xof = hash_leaves,
            opening_challenge_size = dec_opening_challenge_size,
        )
        self._test_running(decs)

    def test_aohash_expanded_running_large_field(self):
        setup = self._test_setup_large_field()
        self._test_aohash_expanded_running(setup)

    def test_aohash_expanded_running_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_aohash_expanded_running(setup)
