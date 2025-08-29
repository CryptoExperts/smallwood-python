from sage.all import FiniteField, Matrix, binomial, ZZ
from math import floor, ceil, log
from .griffin import Griffin

class GriffinBuilder:
    @classmethod
    def get_matrix(cls, p, t):
        # Source: https://github.com/Nashtare/griffin-hash/blob/main/griffin.sage
        # TODO: the decomposition below is overly complicated. It
        # would probably be simpler to rely on numpy.
        Fp = FiniteField(p)
        if t == 3:
            return Matrix.circulant([2, 1, 1]).change_ring(Fp)
        if t == 4:
            return Matrix([[5, 7, 1, 3], [4, 6, 1, 1], [1, 3, 5, 7], [1, 1, 4, 6]]).change_ring(Fp)

        # for larger cases, we split the matrix M as M' x M''
        # with M' a diagonal matrix and M'' a circulant one.
        # this requires t to be a multiple of 4
        assert t % 4 == 0
        tp = t // 4

        Mt = Matrix([[5, 7, 1, 3], [4, 6, 1, 1], [1, 3, 5, 7], [1, 1, 4, 6]]).change_ring(Fp)
        M1 = Matrix.zero(t, t)
        # put Mt on the diagonal of the larger matrix M1
        for i in range(tp):
            for row in range(4):
                for col in range(4):
                    M1[4*i + row, 4*i + col] = Mt[row, col]

        M2 = Matrix.diagonal([1 for i in range(t)])
        # we fill up the missing non-zero coefficients so
        # that M2 looks like = circ(2I_4, I_4, ..., I_4).
        # we proceed to do so in two phases as the matrix is
        # symmetric.
        for col in range(1, tp):
            for row in range(0, col):
                for diag in range(4):
                    M2[4*row + diag, 4*col + diag] = 1
        # now M2 is upper-triangular, we can transpose and add
        # it to obtain the desired matrix
        M2 = M2 + M2.transpose()

        M = M1 * M2

        return M.change_ring(Fp)

    @classmethod
    def get_number_of_rounds(cls, p, t, security_level, alpha):
        # Source: https://github.com/Nashtare/griffin-hash/blob/main/griffin.sage
        #assert security_level <= min(256, floor(log(p, 2) * t/3.0))
        # get number of rounds for Groebner basis attack
        target = 2 ** (security_level // 2)
        for rgb in range(1, 25):
            left = binomial(rgb * (alpha + t) + 1, 1 + t * rgb)
            right = binomial(alpha**rgb + 1 + rgb, 1 + rgb)
            if min(left, right) >= target:
                break

        v = ceil(2.5*security_level/(log(p,2)-log(alpha-1,2)))

        # set a minimum value for sanity and add 20%
        R = ceil(1.2 * max(6, v, 1 + rgb))
        if t == 3 and alpha == 5:
            #print('[!] Warning: R=12 when t=3 and alpha=5, but it does not correspond to the article (R=14)')
            assert R == 12
            return 14 # To follow the article
        if t == 4 and alpha == 3:
            #print('[!] Warning: R=14 when t=4 and alpha=3, but it does not correspond to the article (R=15)')
            assert R == 14
            return 15 # To follow the article
        return R

    @classmethod
    def get_round_constants(cls, p, t, security_level, N):
        # Source: https://github.com/Nashtare/griffin-hash/blob/main/griffin.sage
        # generate pseudorandom bytes
        bytes_per_int = ceil(len(bin(p)[2:]) / 8) + 1
        # 1 value for alpha_2
        # 1 value for beta_2
        # t * (N-1) values for ARK
        num_elems = (t * (N - 1) + 2)
        num_bytes = bytes_per_int * num_elems
        seed_string = "Griffin(%i,%i,%i,%i)" % (p, t, 1, security_level)
        import hashlib
        byte_string = hashlib.shake_256(bytes(seed_string, "ascii")).digest(num_bytes)

        # process byte string in chunks
        round_constants = []
        alphas = []
        betas = []
        Fp = FiniteField(p)

        # generate alpha_2 and deduce the other ones
        chunk = byte_string[0: bytes_per_int]
        alpha = Fp(sum(256 ** j * ZZ(chunk[j]) for j in range(len(chunk))))
        alphas.append(alpha)
        for i in range(3, t):
            alphas.append(Fp(i - 1) * alpha)

        # generate beta_2 and deduce the other ones
        chunk = byte_string[bytes_per_int: bytes_per_int*2]
        beta = Fp(sum(256 ** j * ZZ(chunk[j]) for j in range(len(chunk))))
        betas.append(beta)
        for i in range(3, t):
            betas.append(Fp(i - 1)**2 * beta)

        for i in range(2, num_elems):
            chunk = byte_string[bytes_per_int*i: bytes_per_int*(i+1)]
            c = Fp(sum(256 ** j * ZZ(chunk[j]) for j in range(len(chunk))))
            round_constants.append(c)

        return alphas, betas, round_constants

    @classmethod
    def get(cls, p, alpha, t, capacity, security_level, nb_additional_rounds=0):
        MDS_matrix = cls.get_matrix(p, t)
        R = cls.get_number_of_rounds(p, t, security_level, alpha)
        R += nb_additional_rounds
        alphas, betas, round_constants = cls.get_round_constants(p, t, security_level, R)
        F = FiniteField(p)
        return Griffin(F, alpha, t, security_level, R, round_constants, MDS_matrix, alphas, betas)

