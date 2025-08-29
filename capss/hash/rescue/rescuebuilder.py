from sage.all import *
from .rescue import RescuePrime

# Source: https://github.com/KULeuven-COSIC/Marvellous/blob/master/rescue_prime.sage

class RescueBuilder:
    @classmethod
    def get_matrix(cls, p, m):
        # get a primitive element
        Fp = FiniteField(p)
        g = Fp(2)
        while g.multiplicative_order() != p-1:
            g = g + 1

        # get a systematic generator matrix for the code
        V = matrix([[g**(i*j) for j in range(0, 2*m)] for i in range(0, m)])
        V_ech = V.echelon_form()

        # the MDS matrix is the transpose of the right half of this matrix
        MDS = V_ech[:, m:].transpose()
        return MDS

    @classmethod
    def get_number_of_rounds(cls, p, m, capacity, security_level, alpha):
        # get number of rounds for Groebner basis attack
        rate = m - capacity
        dcon = lambda N : floor(0.5 * (alpha-1) * m * (N-1) + 2)
        v = lambda N : m*(N-1) + rate
        target = 2**security_level
        for l1 in range(1, 25):
            if binomial(v(l1) + dcon(l1), v(l1))**2 > target:
                break

        # set a minimum value for sanity and add 50%
        return ceil(1.5 * max(5, l1))

    @classmethod
    def get_round_constants(cls, p, m, capacity, security_level, N):
        # generate pseudorandom bytes
        bytes_per_int = ceil(len(bin(p)[2:]) / 8) + 1
        num_bytes = bytes_per_int * 2 * m * N
        seed_string = "Rescue-XLIX(%i,%i,%i,%i)" % (p, m, capacity, security_level)
        import hashlib
        byte_string = hashlib.shake_256(bytes(seed_string, "ascii")).digest(num_bytes)

        # process byte string in chunks
        round_constants = []
        Fp = FiniteField(p)
        for i in range(2*m*N):
            chunk = byte_string[bytes_per_int*i : bytes_per_int*(i+1)]
            integer = sum(256**j * ZZ(chunk[j]) for j in range(len(chunk)))
            round_constants.append(Fp(integer % p))

        return round_constants

    @classmethod
    def get_alphas(cls, p):
        for alpha in range(3, p):
            if gcd(alpha, p-1) == 1:
                break
        g, alphainv, garbage = xgcd(alpha, p-1)
        return (alpha, (alphainv % (p-1)))

    @classmethod
    def get(cls, p, alpha, m, capacity, security_level, nb_additional_rounds=0):
        MDS_matrix = cls.get_matrix(p, m)
        N = cls.get_number_of_rounds(p, m, capacity, security_level, alpha)
        N += nb_additional_rounds
        round_constants = cls.get_round_constants(p, m, capacity, security_level, N)
        F = FiniteField(p)
        return RescuePrime(F, alpha, m, security_level, N, round_constants, MDS_matrix)

    @classmethod
    def get_number_of_rounds1(cls, p, m, capacity, security_level, alpha):
        # get number of rounds for Groebner basis attack
        rate = m - capacity
        dcon = lambda N : floor(0.5 * (alpha-1) * m * (N-1) + 2)
        v = lambda N : m*(N-1) + rate
        target = 2**security_level
        for l1 in range(1, 25):
            if binomial(v(l1) + dcon(l1), v(l1))**2 > target:
                break

        # get number of rounds for differential attack
        l0 = 2*security_level / ( log(1.0*p**(m+1), 2.0) - log(1.0*(alpha - 1)**(m+1), 2.0) )

        # take minimum of numbers, sanity factor, and add 50%
        return ceil(1.5 * max(5, l0, l1))
