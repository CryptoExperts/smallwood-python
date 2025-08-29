from sage.all import *
from .anemoi import Anemoi
import itertools

# Source: https://github.com/anemoi-hash/anemoi-hash/blob/main/anemoi.sage

class AnemoiBuilder:
    @classmethod
    def is_mds(cls, m):
        # Uses the Laplace expansion of the determinant to calculate the (m+1)x(m+1) minors in terms of the mxm minors.
        # Taken from https://github.com/mir-protocol/hash-constants/blob/master/mds_search.sage.

        # 1-minors are just the elements themselves
        if any(any(r == 0 for r in row) for row in m):
            return False

        N = m.nrows()
        assert m.is_square() and N >= 2

        det_cache = m

        # Calculate all the nxn minors of m:
        for n in range(2, N+1):
            new_det_cache = dict()
            for rows in itertools.combinations(range(N), n):
                for cols in itertools.combinations(range(N), n):
                    i, *rs = rows

                    # Laplace expansion along row i
                    det = 0
                    for j in range(n):
                        # pick out c = column j; the remaining columns are in cs
                        c = cols[j]
                        cs = cols[:j] + cols[j+1:]

                        # Look up the determinant from the previous iteration
                        # and multiply by -1 if j is odd
                        cofactor = det_cache[(*rs, *cs)]
                        if j % 2 == 1:
                            cofactor = -cofactor

                        # update the determinant with the j-th term
                        det += m[i, c] * cofactor

                    if det == 0:
                        return False
                    new_det_cache[(*rows, *cols)] = det
            det_cache = new_det_cache
        return True

    @classmethod
    def M_2(cls, x_input, b):
        """Fast matrix-vector multiplication algorithm for Anemoi MDS layer with \ell = 1,2."""

        x = x_input[:]
        x[0] += b*x[1]
        x[1] += b*x[0]
        return x

    @classmethod
    def M_3(cls, x_input, b):
        """Fast matrix-vector multiplication algorithm for Anemoi MDS layer with \ell = 3.

        From Figure 6 of [DL18](https://tosc.iacr.org/index.php/ToSC/article/view/888)."""

        x = x_input[:]
        t = x[0] + b*x[2]
        x[2] += x[1]
        x[2] += b*x[0]
        x[0] = t + x[2]
        x[1] += t
        return x

    @classmethod
    def M_4(cls, x_input, b):
        """Fast matrix-vector multiplication algorithm for Anemoi MDS layer with \ell = 4.

        Figure 8 of [DL18](https://tosc.iacr.org/index.php/ToSC/article/view/888)."""

        x = x_input[:]
        x[0] += x[1]
        x[2] += x[3]
        x[3] += b*x[0]
        x[1]  = b*(x[1] + x[2])
        x[0] += x[1]
        x[2] += b*x[3]
        x[1] += x[2]
        x[3] += x[0]
        return x

    @classmethod
    def circulant_mds_matrix(cls, field, l, coeff_upper_limit=None):
        if coeff_upper_limit == None:
            coeff_upper_limit = l+1
        assert(coeff_upper_limit > l)
        for v in itertools.combinations_with_replacement(range(1,coeff_upper_limit), l):
            mat = matrix.circulant(list(v)).change_ring(field)
            if cls.is_mds(mat):
                return(mat)
        # In some cases, the method won't return any valid matrix,
        # hence the need to increase the limit further.
        return cls.circulant_mds_matrix(field, l, coeff_upper_limit+1)

    @classmethod
    def get_matrix(cls, p, l):
        field = FiniteField(p)
        if l == 1:
            return identity_matrix(field, 1)
        if l <= 4: # low addition case
            a = field.multiplicative_generator()
            b = field.one()
            t = 0
            while True:
                # we construct the matrix
                mat = []
                b = b*a
                t += 1
                for i in range(0, l):
                    x_i = [field.one() * (j == i) for j in range(0, l)]
                    if l == 2:
                        mat.append(cls.M_2(x_i, b))
                    elif l == 3:
                        mat.append(cls.M_3(x_i, b))
                    elif l == 4:
                        mat.append(cls.M_4(x_i, b))
                mat = Matrix(field, l, l, mat).transpose()
                if cls.is_mds(mat):
                    return mat
        else: # circulant matrix case
            return cls.circulant_mds_matrix(field, l)

    @classmethod
    def get_number_of_rounds(cls, p, l, security_level, alpha):
        """Returns the number of rounds needed in Anemoi (based on the
        complexity of algebraic attacks).

        """
        r = 0
        complexity = 0
        kappa = {3:1, 5:2, 7:4, 9:7, 11:9}
        assert alpha in kappa
        while complexity < 2**security_level:
            r += 1
            complexity = binomial(
                4*l*r + kappa[alpha],
                2*l*r
            )**2
        r += 2 # considering the second model
        r += min(5,l+1) # security margin
        
        return max(8, r)

    PI_0 = 1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679
    PI_1 = 8214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196


    @classmethod
    def get_round_constants(cls, p, l, N, alpha):
        F = FiniteField(p)
        g = F.multiplicative_generator()
        beta = g
        delta = g**(-1)
        alpha_inv = inverse_mod(alpha, p-1)
        
        C = []
        D = []
        pi_F_0 = F(cls.PI_0 % p)
        pi_F_1 = F(cls.PI_1 % p)
        for r in range(0, N):
            pi_0_r = pi_F_0**r
            C.append([])
            D.append([])
            for i in range(0, l):
                pi_1_i = pi_F_1**i
                pow_alpha = (pi_0_r + pi_1_i)**alpha
                C[r].append(g * (pi_0_r)**2 + pow_alpha)
                D[r].append(g * (pi_1_i)**2 + pow_alpha + delta)
        return (C, D)

    @classmethod
    def get_alphas(cls, p):
        for alpha in range(3, p):
            if gcd(alpha, p-1) == 1:
                break
        g, alphainv, garbage = xgcd(alpha, p-1)
        return (alpha, (alphainv % (p-1)))

    @classmethod
    def get(cls, p, alpha, m, capacity, security_level, nb_additional_rounds=0):
        assert m % 2 == 0
        l = m // 2
        MDS_matrix = cls.get_matrix(p, l)
        N = cls.get_number_of_rounds(p, l, security_level, alpha)
        N += nb_additional_rounds
        round_constants = cls.get_round_constants(p, l, N, alpha)
        F = FiniteField(p)
        return Anemoi(F, alpha, m, security_level, N, round_constants, MDS_matrix)
