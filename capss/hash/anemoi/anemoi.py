from capss.hash import RegularIteratedPermutation, check_perm_exponent
import numpy as np
from r1cs.math import root

class Anemoi(RegularIteratedPermutation):
    def __init__(self, F, alpha, t, security_level, R, round_constants, MDS_matrix):
        super().__init__(F, t, R)
        print('Alert, the current code does not implement the final Amenoi\'s linear layer yet.')
        assert F.order() % 2 == 1, 'For the moment, the current implementation only support prime field.'
        assert t % 2 == 0

        self.alpha = alpha
        self.security_level = security_level
        self.C, self.D = round_constants
        self.MDS_matrix = MDS_matrix
        self.mat = MDS_matrix

        self.g = F.multiplicative_generator()
        self.beta = self.g
        self.delta = self.g**(-1)
        self.QUAD = 2

        if not check_perm_exponent(F, alpha):
            raise ValueError('Error to compute the root, is the field order compatible with the permutation degree?')

    @classmethod
    def get(cls, p, alpha, t, capacity, security_level, nb_add_rounds=0):
        from .anemoibuilder import AnemoiBuilder
        return AnemoiBuilder.get(p, alpha, t, capacity, security_level, nb_add_rounds)

    def _evaluate_sbox(self, _x, _y):
        """Applies an open Flystel to the full state. """
        # Warning, there is a divergence between the article and https://github.com/anemoi-hash/anemoi-hash/blob/3e86ff0cafa54839709b2fa2de0e75d7dd2db464/anemoi.sage#L300, the "+ self.delta" is at the first operation, not at the last.
        x, y = _x, _y
        x -= self.beta * y**self.QUAD + self.delta
        y -= root(x, self.alpha)
        x += self.beta * y**self.QUAD
        return x, y

    def _linear_layer(self, x, y):
        x = self.mat*x
        shifted_y = np.empty_like(y)
        shifted_y[:-1,:] = y[1:,:]
        shifted_y[-1,:] = y[0,:]
        y = self.mat*shifted_y

        # Pseudo-Hadamard transform on each (x,y) pair
        y += x
        x += y
        return x, y

    def get_nb_constants_per_round(self):
        return self.get_state_size()

    def get_round_constants(self, num_round):
        n_cols = self.get_state_size() // 2
        round_constants = []
        for i in range(0, n_cols):
            round_constants.append(self.C[num_round][i])
            round_constants.append(self.D[num_round][i])
        return round_constants

    def run_round_permutation(self, state, round_constants):
        state = np.matrix(state[:]).T

        n_cols = self.get_state_size() // 2
        nb_rounds = self.get_number_rounds()

        x, y = state[:n_cols,:], state[n_cols:,:]
        for i in range(0, n_cols):
            x[i,0] += round_constants[2*i+0]
            y[i,0] += round_constants[2*i+1]

        x, y = self._linear_layer(x, y)

        for i in range(0, n_cols):
           x[i,0], y[i,0] = self._evaluate_sbox(x[i,0], y[i,0])

        #if num_round == nb_rounds-1:
        #    x, y = self._linear_layer(x, y)

        state[:n_cols,:], state[n_cols:,:] = x, y
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

        n_cols = state_size // 2

        x, y = state_in[:n_cols], state_in[n_cols:]
        u, v = state_out[:n_cols], state_out[n_cols:]

        # Constants addition
        for i in range(0, n_cols):
            x[i] += round_constants[2*i+0]
            y[i] += round_constants[2*i+1]
        
        def prod_mat(mat, inp, size):
            outp = [F(0)]*size
            for k in range(size):
                for j in range(size):
                    outp[k] += mat[k,j] * inp[j]
            return outp

        x = prod_mat(self.mat, x, n_cols)
        y = prod_mat(self.mat, list(y[1:]) + [y[0]], n_cols)
        for i in range(0, n_cols):
            y[i] += x[i]
            x[i] += y[i]

        alpha = self.alpha
        beta = self.beta
        delta = self.delta
        QUAD = self.QUAD

        values = []
        for i in range(0, n_cols):
            t = x[i] - (beta * y[i]**QUAD + delta)
            val1 = (y[i] - v[i])**alpha - t
            val2 = (u[i] - beta * v[i]**QUAD) - t
            values += [val1, val2]
        return values
