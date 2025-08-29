from capss.hash import SboxesPermutation
import numpy as np
from r1cs.math import root

class Poseidon(SboxesPermutation):
    def __init__(self, F, alpha, t, security_level, R_F, R_P, round_constants, MDS_matrix):
        """
        :param F: The finite field
        :param t: The size of Poseidon's inner state

        :param security_level: The security level in bits. Denote `M`in in the Poseidon paper
        :param alpha: The power of S-box
        :param int 
        """
        super().__init__(F, t)

        self.F = F
        self.alpha = alpha
        self.t = t
        self.security_level = security_level
        self.R_F = R_F
        self.R_f = int(self.R_F / 2)
        self.R_P = R_P
        self.round_constants = round_constants
        self.MDS_matrix = MDS_matrix

        self.counter = 0

    @classmethod
    def get(cls, p, alpha, t, capacity, security_level, nb_additional_rounds=0):
        from .poseidonbuilder import PoseidonBuilder
        return PoseidonBuilder.get(p, alpha, t, capacity, security_level, nb_additional_rounds)

    def get_number_sboxes(self):
        return self.t*self.R_F + self.R_P

    def _sbox(self, v_in):
        return v_in**self.alpha

    def _sbox_inv(self, v_out):
        return root(v_out, self.alpha)

    def _perm(self, input_state):
        #print('CNT', self.counter)
        self.counter += 1
        assert len(input_state) == self.t, 'The input has not the right size'
        self._last_input_output_sboxes = []
        state_words = np.matrix(input_state[:]).T
        round_constants_counter = 0

        # First full rounds
        for r in range(0, self.R_f):
            # Round constants, nonlinear layer, matrix multiplication
            for i in range(0, self.t):
                state_words[i,0] = state_words[i,0] + self.round_constants[round_constants_counter]
                round_constants_counter += 1
            for i in range(0, self.t):
                state_words[i,0] = self.compute_sbox(state_words[i,0])
            state_words = self.MDS_matrix * state_words

        # Middle partial rounds
        for r in range(0, self.R_P):
            # Round constants, nonlinear layer, matrix multiplication
            for i in range(0, self.t):
                state_words[i,0] = state_words[i,0] + self.round_constants[round_constants_counter]
                round_constants_counter += 1
            state_words[self.t-1,0] = self.compute_sbox(state_words[self.t-1,0])
            state_words = self.MDS_matrix * state_words

        # Last full rounds
        for r in range(0, self.R_f):
            # Round constants, nonlinear layer, matrix multiplication
            for i in range(0, self.t):
                state_words[i,0] = state_words[i,0] + self.round_constants[round_constants_counter]
                round_constants_counter += 1
            for i in range(0, self.t):
                state_words[i,0] = self.compute_sbox(state_words[i,0])
            state_words = self.MDS_matrix * state_words
        
        return list(state_words[:,0].flat)

    def get_sbox_witness_size(self):
        return 0

    def compute_sbox_with_witness(self, sbox_in):
        sbox_out = self._sbox(sbox_in)
        return (sbox_out, [])
    
    def get_degree_of_sbox_verification_function(self):
        return self.alpha

    def run_sbox_verification_function(self, sbox_in, sbox_out, sbox_wit):
        assert len(sbox_wit) == 0
        return [sbox_in**self.alpha - sbox_out]
    
    # def get_wiring(self):
    #     F = self.hash_oneway.get_field()
    #     state_size = self.hash_oneway.perm.get_state_size()
    #     R_f = self.hash_oneway.perm.R_f
    #     R_P = self.hash_oneway.perm.R_P
    #     M = self.hash_oneway.perm.MDS_matrix

    #     a = self.hash_oneway.perm.MDS_matrix[0,0]
    #     b = self.hash_oneway.perm.MDS_matrix[0,1:]
    #     b_ = self.hash_oneway.perm.MDS_matrix[1:,0]
    #     M_ = self.hash_oneway.perm.MDS_matrix[1:,1:]
    #     PM = self.hash_oneway.perm.MDS_matrix[:,:]
    #     for i in range(state_size):
    #         PM[i,0] = 0
    #     def vector_v(i):
    #         return ((PM**i) * self.hash_oneway.perm.MDS_matrix)[0,:]
    #     def vector_v_bar(i):
    #         return (PM**(R_P-i-1)) * self.hash_oneway.perm.MDS_matrix[:,0]
    #     def matrix_V():
    #         return ((PM**(R_P)) * self.hash_oneway.perm.MDS_matrix)
    #     def gamma(i,j):
    #         return ((PM**(i-j)) * self.hash_oneway.perm.MDS_matrix[:,0])[0,0]
    #     def rcum(i,complete=False):
    #         v = zero_vector(F, state_size)
    #         for j in range(i+1):
    #             r = vector(self.hash_oneway.perm.round_constants[(R_f+j)*state_size:(R_f+j+1)*state_size])
    #             v += (PM**(i-j)) * r
    #         return v if complete else v[0]

    #     wires = []

    #     ### Between rounds
    #     num_sbox = state_size
    #     for i in range(1, R_f):
    #         for j in range(state_size):
    #             wire_data = []
    #             wire_data.append((num_sbox, False, F(-1))) # Input
    #             for k in range(state_size):
    #                 wire_data.append((num_sbox-j-state_size+k, True, M[j,k]))
    #             wires.append((wire_data, -self.hash_oneway.perm.round_constants[i*state_size+j]))
    #             num_sbox += 1

    #     first_partial_sbox = num_sbox
    #     for i in range(R_P):
    #         wire_data = []
    #         wire_data.append((num_sbox, False, F(-1))) # Input

    #         v = vector_v(i)
    #         for k in range(state_size):
    #             wire_data.append((num_sbox-i-state_size+k, True, v[0,k]))
    #         for j in range(1, i+1):
    #             wire_data.append((num_sbox-i+j-1, True, gamma(i,j)))
            
    #         wires.append((wire_data, -rcum(i)))
    #         num_sbox += 1

    #     V = matrix_V()
    #     v_bar = [vector_v_bar(i) for i in range(R_P)]
    #     rcum_final = rcum(R_P, complete=True)
    #     for j in range(state_size):
    #         wire_data = []
    #         wire_data.append((num_sbox, False, F(-1))) # Input

    #         for k in range(state_size):
    #             wire_data.append((first_partial_sbox-state_size+k, True, V[j,k]))
    #         for i in range(R_P):
    #             wire_data.append((first_partial_sbox+i, True, v_bar[i][j,0]))

    #         wires.append((wire_data, -rcum_final[j]))
    #         num_sbox += 1

    #     for i in range(1, R_f):
    #         for j in range(state_size):
    #             wire_data = []
    #             wire_data.append((num_sbox, False, F(-1))) # Input
    #             for k in range(state_size):
    #                 wire_data.append((num_sbox-j-state_size+k, True, M[j,k]))
    #             wires.append((wire_data, -self.hash_oneway.perm.round_constants[(R_f+R_P+i)*state_size+j]))
    #             num_sbox += 1

    #     # Input
    #     # TODO

    #     # Output
    #     rate = state_size - self.hash_oneway.capacity
    #     for i in range(rate):
    #         wire_data = []
    #         wire_data.append(((2*state_size*R_f+R_P)-rate+i, True, pk[i])) # Input

    #     return wires
    