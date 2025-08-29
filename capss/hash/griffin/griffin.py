from capss.hash import RegularIteratedPermutation, check_perm_exponent
import numpy as np
from r1cs.math import root

class Griffin(RegularIteratedPermutation):
    def __init__(self, F, alpha, t, security_level, R, round_constants, MDS_matrix, alphas, betas):
        super().__init__(F, t, R)

        self.alpha = alpha
        self.security_level = security_level
        self.round_constants = round_constants
        self.MDS_matrix = MDS_matrix
        self.alphas = alphas
        self.betas = betas

        if not check_perm_exponent(F, alpha):
            raise ValueError('Error to compute the root, is the field order compatible with the permutation degree?')
        
        # For round verification function
        self.matrix_inv = MDS_matrix.inverse()

    @classmethod
    def get(cls, p, alpha, t, capacity, security_level, nb_add_rounds=0):
        from .griffinbuilder import GriffinBuilder
        return GriffinBuilder.get(p, alpha, t, capacity, security_level, nb_add_rounds)

    def get_nb_constants_per_round(self):
        return self.get_state_size()

    def get_round_constants(self, num_round):
        t = self.get_state_size()
        R = self.get_number_rounds()
        if num_round < R-1:
            return self.round_constants[num_round*t:(num_round+1)*t]
        else:
            F = self.get_field()
            return [F(0)]*t

    def run_round_permutation(self, state, round_constants):
        state = np.matrix(state[:]).T

        new_state = state.copy()
        F = self.get_field()
        t = self.get_state_size()
        R = self.get_number_rounds()

        ### Non Linear Layer
        new_state[0,0] = root(state[0,0], self.alpha)
        new_state[1,0] = state[1,0]**self.alpha

        def Li(z0, z1, z2, i): return (F(i-1) * z0 + z1 + z2)
        l = Li(new_state[0,0], new_state[1,0], 0, 2)
        new_state[2,0] = state[2,0] * (l ** 2 + self.alphas[0] * l + self.betas[0])

        for i in range(3, t):
            l = Li(new_state[0,0], new_state[1,0], state[i-1,0], i)
            new_state[i,0] = state[i,0] * (l ** 2 + self.alphas[i-2] * l + self.betas[i-2])

        ### Linear Layer
        new_state = self.MDS_matrix * new_state

        ### Additive Constant Layer
        for j in range(t):
            new_state[j,0] += round_constants[j]

        return list(new_state[:,0].flat)

    def get_round_witness_size(self):
        return 0

    def run_round_permutation_with_witness(self, state, round_constants):
        state = self.run_round_permutation(state, round_constants)
        return (state, [])

    def get_degree_of_round_verification_function(self):
        return self.alpha

    def run_round_verification_function(self, state_in, state_out, witness, round_constants):
        F = self.get_field()
        state_size = self.get_state_size()
        assert len(witness) == 0

        def Lj(z0, z1, z2, i): return (F(i-1) * z0 + z1 + z2)
        sbox_out = [None]*state_size
        for k in range(state_size):
            sbox_out[k] = F(0)
            for j in range(state_size):
                sbox_out[k] += self.matrix_inv[k,j] * (state_out[j] - round_constants[j])
        
        values = []
        for type_sbox in range(state_size):
            if type_sbox == 0:
                # y[0]**d == x[0]
                v = sbox_out[0]**self.alpha - state_in[0]
            elif type_sbox == 1:
                # y[1] == x[1]**d
                v = sbox_out[1] - state_in[1]**self.alpha
            elif type_sbox == 2:
                # y[2] == x[2]*(l**2 + a_2*l + b_2) with l=L_i(y[0],y[1],0)
                l = Lj(sbox_out[0], sbox_out[1], 0, 2)
                v = sbox_out[2] - state_in[2]*(l ** 2 + self.alphas[0] * l + self.betas[0])
            else:
                # y[j] == x[j]*(l**2 + a_j*l + b_j) with l=L_j(y[0],y[1],x[j-1])
                j = type_sbox
                l = Lj(sbox_out[0], sbox_out[1], state_in[j-1], j)
                v = sbox_out[j] - state_in[j]*(l ** 2 + self.alphas[j-2] * l + self.betas[j-2])
            values.append(v)
        return values

    def get_number_r1cs_constraints(self, is_constant=None):
        from math import log2, floor
        hw = lambda x: sum(map(int, bin(x)[2:]))
        # Page 28 of https://eprint.iacr.org/2022/403.pdf
        total = (2*floor(log2(self.alpha)) + 2*hw(self.alpha) - 6 + 2*self.t)*(self.R-1)
        if is_constant is None:
            is_constant = [False]*self.t
        assert len(is_constant) == self.t
        for b in is_constant[:2]:
            if not b:
                total += floor(log2(self.alpha)) + hw(self.alpha) - 1
        for i in range(2, self.t):
            has_r1cs_square = (not is_constant[0]) or (not is_constant[1])
            if i > 2:
                has_r1cs_square = has_r1cs_square or (not is_constant[i-1])
            if has_r1cs_square:
                total += 1
                if not is_constant[i]:
                    total += 1
        return total

