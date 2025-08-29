import unittest
import random

class TestDECSWithShake(unittest.TestCase):
    def _test_setup_large_field(self):
        from sage.all import FiniteField
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        F = FiniteField(p)
        return F
    
    def _test_setup_goldilocks(self):
        from sage.all import FiniteField
        p = 0xffffffff00000001
        F = FiniteField(p)
        return F

    def _test_running(self, decs):
        field = decs.field
        nb_polys = decs.nb_polys
        degree = decs.degree

        from sage.all import PolynomialRing

        R = PolynomialRing(field, name='X')
        from utils import MultiDimArray

        # Commit
        salt = bytes([random.randint(0, 255) for _ in range(16)])
        polys = MultiDimArray((nb_polys,))
        for i in range(nb_polys):
            polys[i] = R.random_element(degree=degree)
        com, state = decs.commit(salt, polys)

        # Open
        opening_binding = bytes([random.randint(0, 255) for _ in range(32)])
        iop_queries, aux = decs.get_random_opening(binding=opening_binding)
        opened_values, proof = decs.open(state, iop_queries)
        if decs.has_variable_proof_size():
            assert len(proof) <= decs.get_proof_size()
        else:
            assert len(proof) == decs.get_proof_size()

        # Verify
        iop_queries_ = decs.recompute_random_opening(aux, binding=opening_binding)
        com_ = decs.recompute_commitment(salt, iop_queries_, opened_values, proof)
        self.assertTrue(com == com_)

    def _test_shake_running(self, setup):
        from smallwood.commit.merkle.shake import MerkleTreeFactoryWithShake
        from smallwood.commit.decs.shake import DECSWithShake
        F = setup
        nb_polys = 11
        degree = 30
        nb_queries = 5
        tree_factory = MerkleTreeFactoryWithShake(
            security_level = 128,
            nb_leaves = 16,
            arity = (4, 4),
            truncated = None,
        )

        decs = DECSWithShake(
            security_level = 128,
            field = F,
            nb_polys = nb_polys,
            degree = degree,
            tree_factory = tree_factory,
            nb_queries = nb_queries,
            eta = 2,
            pow_opening = 0,
            format_challenge = 0,
        )
        self._test_running(decs)

    def test_shake_running_large_field(self):
        setup = self._test_setup_large_field()
        self._test_shake_running(setup)

    def test_shake_running_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_shake_running(setup)
