import unittest

class TestSmallWood(unittest.TestCase):
    def test_example_smallwood_shake(self):
        from sage.all import FiniteField
        F = FiniteField(101)
        from smallwood.pacs.tests.examplepacs import ExamplePACS
        pacs, witness = ExamplePACS.random_instance(F)
        assert pacs.test_witness(witness) is True

        nb_dec_queries = 10
        decs_eta = 2

        from smallwood.shake import SmallWoodWithShake
        sw = SmallWoodWithShake(
            pacs = pacs,

            security_level=128,

            tree_nb_leaves = 16,
            tree_arity = (4,4),
            tree_truncated = None,
            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            layout_beta = 2,

            piop_nb_queries = 1,
            piop_rho = 2,
        )

        proof = sw.prove(witness)
        assert sw.verify(proof)

    def test_example_smallwood_aohash(self):
        from sage.all import FiniteField

        # Get Hash Function
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1

        from capss.hash.griffin import Griffin
        from capss.hash import SpongeHashFunction, TruncationCompressionFunction
        perm = Griffin.get(p, alpha, 4, capacity, 128)
        hash_xof = SpongeHashFunction(perm, capacity=capacity)
        hash_merkle = {4: TruncationCompressionFunction(perm)}

        # Configure DEC Scheme
        F = FiniteField(p)
        decs_opening_challenge_size = 1
    
        from smallwood.pacs.tests.examplepacs import ExamplePACS
        pacs, witness = ExamplePACS.random_instance(F)
        assert pacs.test_witness(witness) is True

        nb_dec_queries = 10
        decs_eta = 2

        digest_size = 1

        from smallwood.aohash import SmallWoodWithAOHash
        sw = SmallWoodWithAOHash(
            pacs = pacs,

            salt_size = 1,
            digest_size = digest_size,
            hash_xof = hash_xof,

            tree_nb_leaves = 16,
            tree_arity = (4,4),
            tree_truncated = None,
            tree_compression_method = hash_merkle,
            tree_is_expanded = True,

            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            decs_opening_challenge_size = decs_opening_challenge_size,
            layout_beta = 2,

            piop_nb_queries = 1,
            piop_rho = 2,
        )

        proof = sw.prove(witness)
        assert sw.verify(proof)
