from capss.hash import RegularIteratedPermutation, check_perm_exponent
import numpy as np
from r1cs.math import root

class RescuePrime(RegularIteratedPermutation):
    def __init__(self, F, alpha, t, security_level, R, round_constants, MDS_matrix):
        super().__init__(F, t, R)

        self.alpha = alpha
        self.security_level = security_level
        self.round_constants = round_constants
        self.MDS_matrix = MDS_matrix

        if not check_perm_exponent(F, alpha):
            raise ValueError('Error to compute the root, is the field order compatible with the permutation degree?')

        # For round verification function
        self.matrix_inv = self.MDS_matrix.inverse()

    @classmethod
    def get(cls, p, alpha, t, capacity, security_level, nb_add_rounds=0):
        from .rescuebuilder import RescueBuilder
        return RescueBuilder.get(p, alpha, t, capacity, security_level, nb_add_rounds)

    def get_nb_constants_per_round(self):
        return 2*self.get_state_size()

    def get_round_constants(self, num_round):
        t = self.get_state_size()
        round_constants = []
        for j in range(t):
            round_constants.append(self.round_constants[num_round*2*t + j])
        for j in range(t):
            round_constants.append(self.round_constants[num_round*2*t + t + j])
        return round_constants
        
    def run_round_permutation(self, state, round_constants):
        state = np.matrix(state[:]).T

        t = self.get_state_size()
        MDS_matrix = self.MDS_matrix

        # S-box
        for j in range(t):
            state[j,0] = state[j,0]**self.alpha

        # MDS
        state = MDS_matrix * state

        # constants
        for j in range(t):
            state[j,0] += round_constants[j]

        # inverse S-box
        for j in range(t):
            state[j,0] = root(state[j,0], self.alpha)

        # MDS
        state = MDS_matrix * state

        # constants
        for j in range(t):
            state[j,0] += round_constants[t + j]

        return list(state[:,0].flat)

    def get_round_witness_size(self):
        return 0
    
    def run_round_permutation_with_witness(self, state, round_constants):
        state = self.run_round_permutation(state, round_constants)
        return (state, [])

    def get_degree_of_round_verification_function(self):
        return self.alpha
    
    def run_round_verification_function(self, state_in, state_out, witness, round_constants):
        state_size = self.get_state_size()
        F = self.get_field()
        assert len(witness) == 0

        # Left approach
        for j in range(state_size):
            state_in[j] = state_in[j]**self.alpha

        inter = [None]*state_size
        for k in range(state_size):
            inter[k] = round_constants[k]
            for j in range(state_size):
                inter[k] += self.MDS_matrix[k,j] * state_in[j]
        
        # Right approach
        inter2 = [None]*state_size
        for k in range(state_size):
            inter2[k] = F(0)
            for j in range(state_size):
                inter2[k] += self.matrix_inv[k,j] * (state_out[j] - round_constants[state_size+j])

        for j in range(state_size):
            inter2[j] = inter2[j]**self.alpha

        # Equations
        return [
            (inter2[j] - inter[j]) for j in range(state_size)
        ]
