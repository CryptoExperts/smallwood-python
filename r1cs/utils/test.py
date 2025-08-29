from utils import LPolynomialUtils, PolynomialUtils
from .polynomial import LPolynomialUtils_R1CS
import unittest

class TestR1CS(unittest.TestCase):

    def test_one(self):
        from sage.all import FiniteField, PolynomialRing
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        F = FiniteField(p)
        R = PolynomialRing(F, 'X')

        degree = 4
        relations = [
            (F(5), [F(0)]),
            (F(1), [F(2), F(5)]),
            (F(6), [F(1), F(0)]),
        ]
        high_coeffs = [F(9), F(8)]
        poly = PolynomialUtils.restore_from_relations(R, relations, high_coeffs, degree)
        
        for i, v in enumerate(high_coeffs):
            self.assertTrue(poly[degree-len(high_coeffs)+1+i] == v)

        for alpha, vs in relations:
            tot = F(0)
            for v in vs:
                tot += poly(v)
            self.assertTrue(tot == alpha)

    def test_r1cs(self):
        from sage.all import FiniteField, PolynomialRing
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        F = FiniteField(p)

        from r1cs.r1cs import R1CS
        r1cs = R1CS(F)

        degree = 4
        relations = [
            (F(5), [F(0)]),
            (r1cs.new_register('a'), [F(2), F(5)]),
            (F(6), [F(1), r1cs.new_register('b')]),
        ]
        high_coeffs = r1cs.new_registers(2, 'high_coeffs')
        poly = LPolynomialUtils_R1CS.restore_from_relations(relations, high_coeffs, degree)

        print(r1cs.get_info())
        print('nb_linear', r1cs.nb_linear_equations())
        print('nb_vars_used_only_once', r1cs.nb_variables_used_only_once())
        print('nb_useless_equations', r1cs.nb_usedless_equations())

        dependencies = r1cs.get_dependencies()
        print(f'nb_dep={len(dependencies)}')

        aux = {
            'a': F(1),
            'b': F(2),
            'high_coeffs': [F(8), F(9)],
        }
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
