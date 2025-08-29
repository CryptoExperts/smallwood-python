from sage.all import FiniteField, matrix, vector, binomial, VectorSpace
from math import floor, ceil, log, log2, inf
from .poseidon import Poseidon

# Source: https://extgit.iaik.tugraz.at/krypto/hadeshash/-/blob/master/code/generate_params_poseidon.sage?ref_type=heads

class PoseidonBuilder:
    @classmethod
    def sat_inequiv_alpha(cls, p, t, R_F, R_P, alpha, M):
        FIELD_SIZE = ceil(log2(p))
        NUM_CELLS = t
        N = int(FIELD_SIZE * NUM_CELLS)

        if alpha > 0:
            R_F_1 = 6 if M <= ((floor(log(p, 2) - ((alpha-1)/2.0))) * (t + 1)) else 10 # Statistical
            R_F_2 = 1 + ceil(log(2, alpha) * min(M, FIELD_SIZE)) + ceil(log(t, alpha)) - R_P # Interpolation
            R_F_3 = (log(2, alpha) * min(M, log(p, 2))) - R_P # Groebner 1
            R_F_4 = t - 1 + log(2, alpha) * min(M / float(t + 1), log(p, 2) / float(2)) - R_P # Groebner 2
            R_F_5 = (t - 2 + (M / float(2 * log(alpha, 2))) - R_P) / float(t - 1) # Groebner 3
            R_F_max = max(ceil(R_F_1), ceil(R_F_2), ceil(R_F_3), ceil(R_F_4), ceil(R_F_5))
            
            # Addition due to https://eprint.iacr.org/2023/537.pdf
            r_temp = floor(t / 3.0)
            over = (R_F - 1) * t + R_P + r_temp + r_temp * (R_F / 2.0) + R_P + alpha
            under = r_temp * (R_F / 2.0) + R_P + alpha
            binom_log = log(binomial(over, under), 2)
            if binom_log == inf:
                binom_log = M + 1
            cost_gb4 = ceil(2 * binom_log) # Paper uses 2.3727, we are more conservative here

            return ((R_F >= R_F_max) and (cost_gb4 >= M))
        else:
            print("Invalid value for alpha!")
            exit(1)

    @classmethod
    def get_sbox_cost(cls, R_F, R_P, N, t):
        return int(t * R_F + R_P)

    @classmethod
    def get_size_cost(cls, R_F, R_P, N, t):
        n = ceil(float(N) / t)
        return int((N * R_F) + (n * R_P))

    @classmethod
    def find_FD_round_numbers(cls, p, t, alpha, M, cost_function, security_margin):
        FIELD_SIZE = ceil(log2(p))
        NUM_CELLS = t
        N = int(FIELD_SIZE * NUM_CELLS)

        sat_inequiv = cls.sat_inequiv_alpha
        
        R_P = 0
        R_F = 0
        min_cost = float("inf")
        max_cost_rf = 0
        # Brute-force approach
        for R_P_t in range(1, 500):
            for R_F_t in range(4, 100):
                if R_F_t % 2 == 0:
                    if (sat_inequiv(p, t, R_F_t, R_P_t, alpha, M) == True):
                        if security_margin == True:
                            R_F_t += 2
                            R_P_t = int(ceil(float(R_P_t) * 1.075))
                        cost = cost_function(R_F_t, R_P_t, N, t)
                        if (cost < min_cost) or ((cost == min_cost) and (R_F_t < max_cost_rf)):
                            R_P = ceil(R_P_t)
                            R_F = ceil(R_F_t)
                            min_cost = cost
                            max_cost_rf = R_F
        return (int(R_F), int(R_P))

    @classmethod
    def calc_final_numbers_fixed(cls, p, t, alpha, M, security_margin):
        FIELD_SIZE = ceil(log2(p))
        NUM_CELLS = t

        # [Min. S-boxes] Find best possible for t and N
        N = int(FIELD_SIZE * NUM_CELLS)
        cost_function = cls.get_sbox_cost
        ret_list = []
        (R_F, R_P) = cls.find_FD_round_numbers(p, t, alpha, M, cost_function, security_margin)
        min_sbox_cost = cost_function(R_F, R_P, N, t)
        ret_list.append(R_F)
        ret_list.append(R_P)
        ret_list.append(min_sbox_cost)

        # [Min. Size] Find best possible for t and N
        # Minimum number of S-boxes for fixed n results in minimum size also (round numbers are the same)!
        min_size_cost = cls.get_size_cost(R_F, R_P, N, t)
        ret_list.append(min_size_cost)

        return ret_list # [R_F, R_P, min_sbox_cost, min_size_cost]

    @classmethod
    def init_generator(cls, p, t, R_F, R_P):
        # Generate initial sequence based on parameters
        FIELD = 1
        SBOX = 0
        FIELD_SIZE = ceil(log2(p))
        NUM_CELLS = t

        bit_list_field = [_ for _ in (bin(FIELD)[2:].zfill(2))]
        bit_list_sbox = [_ for _ in (bin(SBOX)[2:].zfill(4))]
        bit_list_n = [_ for _ in (bin(FIELD_SIZE)[2:].zfill(12))]
        bit_list_t = [_ for _ in (bin(NUM_CELLS)[2:].zfill(12))]
        bit_list_R_F = [_ for _ in (bin(R_F)[2:].zfill(10))]
        bit_list_R_P = [_ for _ in (bin(R_P)[2:].zfill(10))]
        bit_list_1 = [1] * 30

        INIT_SEQUENCE = bit_list_field + bit_list_sbox + bit_list_n + bit_list_t + bit_list_R_F + bit_list_R_P + bit_list_1
        INIT_SEQUENCE = [int(_) for _ in INIT_SEQUENCE]

        def grain_sr_generator():
            bit_sequence = INIT_SEQUENCE
            for _ in range(0, 160):
                new_bit = bit_sequence[62] ^ bit_sequence[51] ^ bit_sequence[38] ^ bit_sequence[23] ^ bit_sequence[13] ^ bit_sequence[0]
                bit_sequence.pop(0)
                bit_sequence.append(new_bit)
                
            while True:
                new_bit = bit_sequence[62] ^ bit_sequence[51] ^ bit_sequence[38] ^ bit_sequence[23] ^ bit_sequence[13] ^ bit_sequence[0]
                bit_sequence.pop(0)
                bit_sequence.append(new_bit)
                while new_bit == 0:
                    new_bit = bit_sequence[62] ^ bit_sequence[51] ^ bit_sequence[38] ^ bit_sequence[23] ^ bit_sequence[13] ^ bit_sequence[0]
                    bit_sequence.pop(0)
                    bit_sequence.append(new_bit)
                    new_bit = bit_sequence[62] ^ bit_sequence[51] ^ bit_sequence[38] ^ bit_sequence[23] ^ bit_sequence[13] ^ bit_sequence[0]
                    bit_sequence.pop(0)
                    bit_sequence.append(new_bit)
                new_bit = bit_sequence[62] ^ bit_sequence[51] ^ bit_sequence[38] ^ bit_sequence[23] ^ bit_sequence[13] ^ bit_sequence[0]
                bit_sequence.pop(0)
                bit_sequence.append(new_bit)
                yield new_bit
        return grain_sr_generator()

    @classmethod
    def grain_random_bits(cls, grain_gen, num_bits):
        random_bits = [next(grain_gen) for i in range(0, num_bits)]
        # random_bits.reverse() ## Remove comment to start from least significant bit
        random_int = int("".join(str(i) for i in random_bits), 2)
        return random_int

    @classmethod
    def generate_constants(cls, p, t, R_F, R_P, grain_gen):
        n = ceil(log2(p))
        field = 1
        round_constants = []
        num_constants = (R_F + R_P) * t

        if field == 0:
            for i in range(0, num_constants):
                random_int = cls.grain_random_bits(grain_gen, n)
                round_constants.append(random_int)
        elif field == 1:
            for i in range(0, num_constants):
                random_int = cls.grain_random_bits(grain_gen, n)
                while random_int >= p:
                    # print("[Info] Round constant is not in prime field! Taking next one.")
                    random_int = cls.grain_random_bits(grain_gen, n)
                round_constants.append(random_int)
        return round_constants

    @classmethod
    def generate_vectorspace(cls, p, round_num, M, M_round, NUM_CELLS):
        F = FiniteField(p)
        t = NUM_CELLS
        s = 1
        V = VectorSpace(F, t)
        if round_num == 0:
            return V
        elif round_num == 1:
            return V.subspace(V.basis()[s:])
        else:
            mat_temp = matrix(F)
            for i in range(0, round_num-1):
                add_rows = []
                for j in range(0, s):
                    add_rows.append(M_round[i].rows()[j][s:])
                mat_temp = matrix(mat_temp.rows() + add_rows)
            r_k = mat_temp.right_kernel()
            extended_basis_vectors = []
            for vec in r_k.basis():
                extended_basis_vectors.append(vector([0]*s + list(vec)))
            S = V.subspace(extended_basis_vectors)

            return S

    @classmethod
    def subspace_times_matrix(cls, p, subspace, M, NUM_CELLS):
        F = FiniteField(p)
        t = NUM_CELLS
        V = VectorSpace(F, t)
        subspace_basis = subspace.basis()
        new_basis = []
        for vec in subspace_basis:
            new_basis.append(M * vec)
        new_subspace = V.subspace(new_basis)
        return new_subspace

    # Returns True if the matrix is considered secure, False otherwise
    @classmethod
    def algorithm_1(cls, p, M, NUM_CELLS):
        t = NUM_CELLS
        s = 1
        r = floor((t - s) / float(s))
        F = FiniteField(p)

        # Generate round matrices
        M_round = []
        for j in range(0, t+1):
            M_round.append(M**(j+1))

        for i in range(1, r+1):
            mat_test = M**i
            entry = mat_test[0, 0]
            mat_target = matrix.circulant(vector([entry] + ([F(0)] * (t-1))))

            if (mat_test - mat_target) == matrix.circulant(vector([F(0)] * (t))):
                return [False, 1]

            S = cls.generate_vectorspace(p, i, M, M_round, t)
            V = VectorSpace(F, t)

            basis_vectors= []
            for eigenspace in mat_test.eigenspaces_right(format='galois'):
                if (eigenspace[0] not in F):
                    continue
                vector_subspace = eigenspace[1]
                intersection = S.intersection(vector_subspace)
                basis_vectors += intersection.basis()
            IS = V.subspace(basis_vectors)

            if IS.dimension() >= 1 and IS != V:
                return [False, 2]
            for j in range(1, i+1):
                S_mat_mul = cls.subspace_times_matrix(p, S, M**j, t)
                if S == S_mat_mul:
                    print("S.basis():\n", S.basis())
                    return [False, 3]

        return [True, 0]

    # Returns True if the matrix is considered secure, False otherwise
    @classmethod
    def algorithm_2(cls, p, M, NUM_CELLS):
        t = NUM_CELLS
        s = 1
        F = FiniteField(p)

        V = VectorSpace(F, t)
        trail = [None, None]
        test_next = False
        I = range(0, s)
        import sage
        I_powerset = list(sage.misc.misc.powerset(I))[1:]
        for I_s in I_powerset:
            test_next = False
            new_basis = []
            for l in I_s:
                new_basis.append(V.basis()[l])
            IS = V.subspace(new_basis)
            for i in range(s, t):
                new_basis.append(V.basis()[i])
            full_iota_space = V.subspace(new_basis)
            for l in I_s:
                v = V.basis()[l]
                while True:
                    delta = IS.dimension()
                    v = M * v
                    IS = V.subspace(IS.basis() + [v])
                    if IS.dimension() == t or IS.intersection(full_iota_space) != IS:
                        test_next = True
                        break
                    if IS.dimension() <= delta:
                        break
                if test_next == True:
                    break
            if test_next == True:
                continue
            return [False, [IS, I_s]]

        return [True, None]

    # Returns True if the matrix is considered secure, False otherwise
    @classmethod
    def algorithm_3(cls, p, M, NUM_CELLS):
        t = NUM_CELLS
        s = 1
        F = FiniteField(p)

        V = VectorSpace(F, t)

        l = 4*t
        for r in range(2, l+1):
            next_r = False
            res_alg_2 = cls.algorithm_2(p, M**r, t)
            if res_alg_2[0] == False:
                return [False, None]

            # if res_alg_2[1] == None:
            #     continue
            # IS = res_alg_2[1][0]
            # I_s = res_alg_2[1][1]
            # for j in range(1, r):
            #     IS = subspace_times_matrix(IS, M, t)
            #     I_j = []
            #     for i in range(0, s):
            #         new_basis = []
            #         for k in range(0, t):
            #             if k != i:
            #                 new_basis.append(V.basis()[k])
            #         iota_space = V.subspace(new_basis)
            #         if IS.intersection(iota_space) != iota_space:
            #             single_iota_space = V.subspace([V.basis()[i]])
            #             if IS.intersection(single_iota_space) == single_iota_space:
            #                 I_j.append(i)
            #             else:
            #                 next_r = True
            #                 break
            #     if next_r == True:
            #         break
            # if next_r == True:
            #     continue
            # return [False, [IS, I_j, r]]
        
        return [True, None]

    @classmethod
    def create_mds_p(cls, p, t, grain_gen):
        n = ceil(log2(p))
        F = FiniteField(p)
        M = matrix(F, t, t)

        # Sample random distinct indices and assign to xs and ys
        while True:
            flag = True
            rand_list = [F(cls.grain_random_bits(grain_gen, n)) for _ in range(0, 2*t)]
            while len(rand_list) != len(set(rand_list)): # Check for duplicates
                rand_list = [F(cls.grain_random_bits(grain_gen, n)) for _ in range(0, 2*t)]
            xs = rand_list[:t]
            ys = rand_list[t:]
            # xs = [F(ele) for ele in range(0, t)]
            # ys = [F(ele) for ele in range(t, 2*t)]
            for i in range(0, t):
                for j in range(0, t):
                    if (flag == False) or ((xs[i] + ys[j]) == 0):
                        flag = False
                    else:
                        entry = (xs[i] + ys[j])**(-1)
                        M[i, j] = entry
            if flag == False:
                continue
            return M


    @classmethod
    def generate_matrix(cls, p, NUM_CELLS, grain_gen):
        FIELD = 1
        FIELD_SIZE = ceil(log2(p))
        if FIELD == 0:
            mds_matrix = cls.create_mds_gf2n(FIELD_SIZE, NUM_CELLS, grain_gen)
            result_1 = cls.algorithm_1(mds_matrix, NUM_CELLS)
            result_2 = cls.algorithm_2(mds_matrix, NUM_CELLS)
            result_3 = cls.algorithm_3(mds_matrix, NUM_CELLS)
            while result_1[0] == False or result_2[0] == False or result_3[0] == False:
                mds_matrix = cls.create_mds_gf2n(FIELD_SIZE, NUM_CELLS, grain_gen)
                result_1 = cls.algorithm_1(mds_matrix, NUM_CELLS)
                result_2 = cls.algorithm_2(mds_matrix, NUM_CELLS)
                result_3 = cls.algorithm_3(mds_matrix, NUM_CELLS)
            return mds_matrix
        elif FIELD == 1:
            mds_matrix = cls.create_mds_p(p, NUM_CELLS, grain_gen)
            result_1 = cls.algorithm_1(p, mds_matrix, NUM_CELLS)
            result_2 = cls.algorithm_2(p, mds_matrix, NUM_CELLS)
            result_3 = cls.algorithm_3(p, mds_matrix, NUM_CELLS)
            while result_1[0] == False or result_2[0] == False or result_3[0] == False:
                mds_matrix = cls.create_mds_p(p, NUM_CELLS, grain_gen)
                result_1 = cls.algorithm_1(p, mds_matrix, NUM_CELLS)
                result_2 = cls.algorithm_2(p, mds_matrix, NUM_CELLS)
                result_3 = cls.algorithm_3(p, mds_matrix, NUM_CELLS)
            return mds_matrix

    @classmethod
    def get(cls, p, alpha, t, capacity, security_level, nb_additional_rounds=0):
        round_numbers = cls.calc_final_numbers_fixed(p, t, alpha, security_level, True)
        R_F = round_numbers[0]
        R_P = round_numbers[1]+nb_additional_rounds

        grain_gen = cls.init_generator(p, t, R_F, R_P)
        round_constants = cls.generate_constants(p, t, R_F, R_P, grain_gen)
        linear_layer = cls.generate_matrix(p, t, grain_gen)

        F = FiniteField(p)
        return Poseidon(F, alpha, t, security_level, R_F, R_P, round_constants, linear_layer)

