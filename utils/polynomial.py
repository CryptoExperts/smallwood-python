class LPolynomialUtils:
    @staticmethod
    def eval(coeffs, point):
        return sum(coeff * point**i for i, coeff in enumerate(coeffs))

    @staticmethod
    def get_high_coeffs(coeffs, degree, nb):
        assert len(coeffs) == degree+1
        assert nb <= degree+1
        return coeffs[-nb:]

    @classmethod
    def restore(cls, high_coeffs, degree, evals):
        return cls.restore_from_relations(
            [(value, [eval_point]) for (eval_point, value) in evals],
            high_coeffs,
            degree,
        )

    @staticmethod
    def restore_only_from_relation(relations, degree):
        """ It takes some relations and return the coefficients
            of the polynomials satisfying them.
        """
        from sage.all import matrix
        alphas = [alpha for alpha, _ in relations]
        assert degree+1 == len(relations)
        eq_systems = [
            [
                sum(v**i for v in vs)
                for i in range(degree+1)
            ]
            for _, vs in relations
        ]
        # We use numpy, because it enables us to
        #   support a vector of objects.
        import numpy as np
        coeffs = list(np.array(matrix(eq_systems).inverse()).dot(np.array(alphas)))
        return coeffs

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
        degree_L = degree - (len(high_coeffs)-1)-1
        assert len(relations) == degree_L+1
        low_coeffs = cls.restore_only_from_relation([
            (alpha - sum(v**(degree_L+1) * cls.eval(high_coeffs, v) for v in vs), vs)
            for alpha, vs in relations
        ], degree_L)
        coeffs = low_coeffs + high_coeffs
        return coeffs


class PolynomialUtils:
    @staticmethod
    def to_list(poly, degree):
        F = poly.base_ring()
        coeffs = list(poly)
        assert len(coeffs) <= degree+1, f'The polynomial {poly} is supposed to have degree at most {degree}'
        coeffs += [F(0)]*(degree+1-len(coeffs))
        return coeffs

    @classmethod
    def get_high_coeffs(cls, poly, degree, nb):
        assert nb <= degree+1
        return cls.to_list(poly, degree)[-nb:]

    @staticmethod
    def restore(R, high_coeffs, degree, evals):
        X = R.gen()
        d = degree - (len(high_coeffs)-1)
        poly_D = X**d * R(high_coeffs)
        assert len(evals) == d
        poly_L = R.lagrange_polynomial([
            (eval_point, value-poly_D(eval_point))
            for eval_point, value in evals
        ])
        return poly_D + poly_L

    @classmethod
    def restore_only_from_relation(cls, R, relations, degree):
        """ It takes some relations and return the coefficients
            of the polynomials satisfying them.
        """
        return R(LPolynomialUtils.restore_only_from_relation(
            relations, degree
        ))

    @classmethod
    def restore_from_relations(cls, R, relations, high_coeffs, degree):
        """
            relation = [
                (alpha_1, [v_11, v12, ...]),
                (alpha_2, [v_21, v22, ...]),
                ...
            ]
            implies that the output polynomial R will satisfy, for all i, 
               sum_{v in [vi1, vi2, ...]} R(v) = alpha_i
        """
        return R(LPolynomialUtils.restore_from_relations(
            relations, high_coeffs, degree
        ))

