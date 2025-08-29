import unittest
import random

class TestLVCSWithShake(unittest.TestCase):
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

    def _test_running(self, lvcs):
        F = lvcs.field

        # Data
        rows = []
        for _ in range(lvcs.nb_rows):
            rows.append(
                [F.random_element() for _ in range(lvcs.row_length)]
            )

        # Commit
        salt = bytes([random.randint(0, 255) for _ in range(16)])
        com, state = lvcs.commit(salt, rows)

        # Open
        opening_binding = bytes([random.randint(0, 255) for _ in range(32)])
        iop_queries, aux = lvcs.get_random_opening(binding=opening_binding)
        fullrank_cols = list(range(lvcs.nb_queries))
        opened_values, proof = lvcs.open(state, iop_queries, fullrank_cols)

        # Check that the open values are correct
        for i, iop_query in enumerate(iop_queries):
            for j in range(lvcs.row_length):
                res = sum(rows[k][j]*iop_query[k] for k in range(lvcs.nb_rows))
                self.assertTrue(opened_values[i][j] == res)

        # Verify
        iop_queries_ = lvcs.recompute_random_opening(aux, binding=opening_binding)
        com_ = lvcs.recompute_commitment(salt, iop_queries_, fullrank_cols, opened_values, proof)
        self.assertTrue(com == com_)

    def _test_shake_running(self, setup):
        from smallwood.commit.merkle.shake import MerkleTreeFactoryWithShake
        from smallwood.commit.lvcs.shake import LVCSWithShake
        F = setup
        nb_rows = 10
        row_length = 30
        nb_dec_queries = 10
        tree_factory = MerkleTreeFactoryWithShake(
            security_level = 128,
            nb_leaves = 16,
            arity = (4, 4),
            truncated = None,
        )

        lvcs = LVCSWithShake(
            security_level=128,
            field = F,
            row_length = row_length,
            nb_rows = nb_rows,
            nb_queries = 3,

            tree_factory = tree_factory,
            decs_nb_queries = nb_dec_queries,
            decs_eta = 2,
        )
        self._test_running(lvcs)

    def test_shake_running_large_field(self):
        setup = self._test_setup_large_field()
        self._test_shake_running(setup)

    def test_shake_running_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_shake_running(setup)
    