import unittest

class TestPACSSBoxes(unittest.TestCase):
    def test_poseidon(self):
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1
        iv_size = 1
        y_size = 1

        from capss.hash.poseidon import Poseidon
        perm = Poseidon.get(p, alpha, 3, capacity, 128)

        from capss.pacs.pacs_sboxes import SBoxesHashPACS
        pacs, secret = SBoxesHashPACS.random(perm, iv_size, y_size, nb_wit_cols=5)
        witness = pacs.secret_to_witness(secret)
        assert pacs.test_witness(witness) is True
