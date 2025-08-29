import unittest

class TestPACS(unittest.TestCase):
    def test_example_pacs(self):
        from sage.all import FiniteField
        F = FiniteField(13)
        from .examplepacs import ExamplePACS
        pacs, witness = ExamplePACS.random_instance(F)
        assert pacs.test_witness(witness) is True

    # def test_factory_pacs(self):
    #     from smallwood.pacs.constraints import LUT, PACSFactory
    #     from sage.all import flatten

    #     nb_rows = 10
    #     nb_cols = 6

    #     from sage.all import FiniteField, matrix
    #     F = FiniteField(3329)


    #     factory = PACSFactory(nb_rows, nb_cols)
    #     wit = factory.get_witness()
    #     pvar = factory.get_pvar()
    #     lut = LUT([F(0), F(1)])

    #     for i in range(nb_rows):
    #         factory.register(pvar(i) in lut)

    #     xsecret = matrix(F, flatten(wit))
    #     secret = matrix(F, [F.random_element() for _ in range(nb_rows*nb_cols)])
    #     mat = matrix(F, [
    #         [F.random_element() for _ in range(nb_rows*nb_cols)]
    #         for _ in range(nb_rows*nb_cols)
    #     ])
    #     solution = mat*secret
    #     xsolution = mat*xsecret
    #     factory.register(xsolution == solution)

    #     secret = ...
    #     mat = ...
    #     offset = mat*secret
        
    #     xsecret = None
    #     xoffset = mat*xsecret
    #     xoffset == offset

    #     CheckIn()




