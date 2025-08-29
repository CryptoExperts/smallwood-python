import unittest

class TestPACSRegRound(unittest.TestCase):
    def test_griffin(self):
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1
        iv_size = 1
        y_size = 1

        from capss.hash.griffin import Griffin
        perm = Griffin.get(p, alpha, 3, capacity, 128)

        from capss.pacs.pacs_reg_rounds import RegRoundsHashPACS
        pacs, secret = RegRoundsHashPACS.random(perm, iv_size, y_size, batching_factor=3)
        witness = pacs.secret_to_witness(secret)
        assert pacs.test_witness(witness) is True

    def test_anemoi(self):
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1
        iv_size = 1
        y_size = 1

        from capss.hash.anemoi import Anemoi
        perm = Anemoi.get(p, alpha, 2, capacity, 128)

        from capss.pacs.pacs_reg_rounds import RegRoundsHashPACS
        pacs, secret = RegRoundsHashPACS.random(perm, iv_size, y_size, batching_factor=3)
        witness = pacs.secret_to_witness(secret)
        assert pacs.test_witness(witness) is True

    def test_rescue(self):
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1
        iv_size = 1
        y_size = 1

        from capss.hash.rescue import RescuePrime
        perm = RescuePrime.get(p, alpha, 3, capacity, 128)

        from capss.pacs.pacs_reg_rounds import RegRoundsHashPACS
        pacs, secret = RegRoundsHashPACS.random(perm, iv_size, y_size, batching_factor=4)
        witness = pacs.secret_to_witness(secret)
        assert pacs.test_witness(witness) is True

