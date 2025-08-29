from utils import LPolynomialUtils
from r1cs.variable import Variable
from r1cs.r1cs import R1CS

class LPolynomialUtils_R1CS:
    @staticmethod
    def eval(coeffs, point):
        return sum(coeff * point**i for i, coeff in enumerate(coeffs))

    @staticmethod
    def get_high_coeffs(coeffs, degree, nb):
        return LPolynomialUtils.get_high_coeffs(coeffs, degree, nb)

    @classmethod
    def restore(cls, high_coeffs, degree, evals):
        return cls.restore_from_relations(
            [(value, [eval_point]) for (eval_point, value) in evals],
            high_coeffs,
            degree,
        )

    @classmethod
    def restore_only_from_relation(cls, relations, degree):
        return cls.restore_from_relations(relations, [], degree)

    @classmethod
    def restore_from_relations(cls, relations, high_coeffs, degree):
        """
            relation = [
                (alpha_1, [v_11, v12, ...]),
                (alpha_2, [v_21, v22, ...]),
                ...
            ]
            implies that the output polynomial R will satisfy, for all i, 
               sum_{v in [vi1, vi2, ...]} R(v) = alpha_i
        """
        assert degree == len(relations) + len(high_coeffs) - 1

        r1cs = R1CS.detect(relations, high_coeffs)
        if r1cs is None:
            return LPolynomialUtils.restore_from_relations(relations, high_coeffs, degree)

        r1cs_linear_constraints = []
        r1cs_non_linear_constraints = []
        for alpha, vs in relations:
            is_r1cs_linear = True
            clean_vs = []
            for v in vs:
                if Variable(r1cs, v).is_constant():
                    clean_vs.append(Variable(r1cs, v).get_constant())
                else:
                    clean_vs.append(v)
                    is_r1cs_linear = False
            if is_r1cs_linear:
                r1cs_linear_constraints.append((alpha, clean_vs))
            else:
                r1cs_non_linear_constraints.append((alpha, clean_vs))

        nb_middle_coeffs = (degree+1)-len(high_coeffs)-len(r1cs_linear_constraints)
        assert len(r1cs_non_linear_constraints) == nb_middle_coeffs
        def hint_for_middle_coeffs(relations, high_coeffs):
            coeffs = LPolynomialUtils.restore_from_relations(relations, high_coeffs, degree)
            begin = len(r1cs_linear_constraints)
            end = begin + nb_middle_coeffs
            return coeffs[begin:end]
        middle_coeffs = r1cs.new_registers(
            nb_middle_coeffs,
            hint_inputs=[relations, high_coeffs],
            hint=hint_for_middle_coeffs,
        )

        low_coeffs = LPolynomialUtils.restore_only_from_relation([
            (alpha - sum(v**len(r1cs_linear_constraints) * cls.eval(middle_coeffs + high_coeffs, v) for v in vs), vs)
            for alpha, vs in r1cs_linear_constraints
        ], len(r1cs_linear_constraints)-1)
        
        coeffs = low_coeffs + middle_coeffs + high_coeffs
        for alpha, vs in r1cs_non_linear_constraints:
            tot = sum(cls.eval(coeffs, v) for v in vs)
            assert tot == alpha
        
        return coeffs
