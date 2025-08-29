from .pacs_perm import PermPreimagePACS
from capss.hash.permutation import SboxesPermutation
from math import ceil
from utils import MultiDimArray

class SBoxesHashPACS(PermPreimagePACS):
    def __init__(self, perm, iv, y, nb_wit_cols):
        assert isinstance(perm, SboxesPermutation)
        super().__init__(perm, iv, y)
        self._nb_wit_cols = nb_wit_cols
        nb_sboxes = perm.get_number_sboxes()
        nb_add_vars = perm.get_sbox_witness_size()
        state_size = perm.get_state_size()

        # Compute Wiring
        self._wiring_internal, self._wiring_outputs = perm.get_wiring()

        # Compute Nb Wit Rows
        self._nb_groups_of_sboxes = ceil((nb_sboxes+state_size)/nb_wit_cols)
        self._nb_wit_rows = (2+nb_add_vars)*self._nb_groups_of_sboxes

        # Compute Nb Parallel Constraints
        self._nb_para_constraints = (1+nb_add_vars)*self._nb_groups_of_sboxes

        # Compute Nb Aggregated Constraints
        iv_size = len(iv)
        y_size = len(y)
        self._nb_aggr_constraints = len(self._wiring_internal) + iv_size + y_size

    def get_nb_wit_rows(self):
        return self._nb_wit_rows

    def get_nb_wit_cols(self):
        return self._nb_wit_cols
    
    def get_constraint_degree(self):
        return self._perm.get_degree_of_sbox_verification_function()

    def get_nb_parallel_constraints(self):
        return self._nb_para_constraints

    def get_nb_aggregated_constraints(self):
        return self._nb_aggr_constraints

    def get_theta(self):
        nb_para_constraints = self.get_nb_parallel_constraints()
        return [[] for _ in range(nb_para_constraints)]

    def evaluate_parallel_constraints(self, wit_evals, theta):
        nb_groups_of_sboxes = self._nb_groups_of_sboxes
        nb_add_vars = self._perm.get_sbox_witness_size()

        all_values = []
        for num_group in range(nb_groups_of_sboxes):
            sbox_in = wit_evals[num_group*(2+nb_add_vars)+0]
            sbox_out = wit_evals[num_group*(2+nb_add_vars)+1]
            sbox_wit = wit_evals[num_group*(2+nb_add_vars)+2:num_group*(2+nb_add_vars)+2+nb_add_vars]
            all_values += self._perm.run_sbox_verification_function(sbox_in, sbox_out, sbox_wit)
        return all_values

    def get_theta_(self):
        nb_groups_of_sboxes = self._nb_groups_of_sboxes
        nb_wit_cols = self.get_nb_wit_cols()
        state_size = self._perm.get_state_size()
        F = self.get_field()

        theta_ = []
        for num_wire, wire in enumerate(self._wiring_internal):
            num_col = (state_size + num_wire) % nb_wit_cols
            subtheta = MultiDimArray((nb_groups_of_sboxes+2,nb_wit_cols), F(0))
            subtheta[-2][num_col] = F(1) # Selector
            subtheta[-1][0] = wire._offset # Offset
            for var, factor in wire._lst:
                num = var.id if var.is_input() else state_size + var.id
                subtheta[num//nb_wit_cols][num%nb_wit_cols] = factor            
            theta_.append(subtheta)
        
        # IV
        iv_size = len(self._iv)
        for j in range(iv_size):
            pos = j % nb_wit_cols
            theta_.append([
                [F(0)]*pos + [F(1)] + [F(0)]*(nb_wit_cols-1-pos),
                [self._iv[j]] + [F(0)]*(nb_wit_cols-1),
            ])

        # y
        y_size = len(self._y)
        for j in range(y_size):
            wire = self._wiring_outputs[j]
            subtheta = MultiDimArray((nb_groups_of_sboxes+1,nb_wit_cols), F(0))
            subtheta[-1][0] = self._y[j] - wire._offset
            for var, factor in wire._lst:
                num = var.id if var.is_input() else state_size + var.id
                subtheta[num//nb_wit_cols][num%nb_wit_cols] = factor            
            theta_.append(subtheta)

        return theta_
    
    def evaluate_aggregated_constraints(self, wit_evals, theta):
        nb_wit_cols = self.get_nb_wit_cols()
        state_size = self._perm.get_state_size()
        nb_add_vars = self._perm.get_sbox_witness_size()
        nb_groups_of_sboxes = self._nb_groups_of_sboxes

        values = []
        num_constraints = 0

        # Wiring
        for num_wire in range(len(self._wiring_internal)):
            
            num_row = ((state_size + num_wire) // nb_wit_cols)*(2+nb_add_vars)
            val = theta[num_constraints][-1] - wit_evals[num_row]*theta[num_constraints][-2]

            for i in range(nb_groups_of_sboxes):
                val += wit_evals[i*(2+nb_add_vars)+1]*theta[num_constraints][i]

            values.append(val)
            num_constraints += 1

        # IV
        iv_size = len(self._iv)
        for j in range(iv_size):
            pos_row = (j // nb_wit_cols)*(2+nb_add_vars) + 1
            val = wit_evals[pos_row]*theta[num_constraints][0] - theta[num_constraints][1]
            values.append(val)
            num_constraints += 1

        # y
        y_size = len(self._y)
        for j in range(y_size):
            val = 0
            for i in range(nb_groups_of_sboxes):
                val += wit_evals[i*(2+nb_add_vars)+1]*theta[num_constraints][i]
            val -= theta[num_constraints][-1]
            values.append(val)
            num_constraints += 1
        
        return values

    def secret_to_witness(self, secret):
        nb_wit_rows = self.get_nb_wit_rows()
        nb_wit_cols = self.get_nb_wit_cols()
        nb_add_vars = self._perm.get_sbox_witness_size()
        nb_sboxes = self._perm.get_number_sboxes()

        perm_inputs = self._iv + secret
        sboxes_inputs = [None]*nb_sboxes
        sboxes_outputs = [None]*nb_sboxes
        sboxes_witnesses = [None]*nb_sboxes
        for num_sbox in range(nb_sboxes):
            sboxes_inputs[num_sbox] = self._wiring_internal[num_sbox].evaluate(perm_inputs, sboxes_outputs)
            sboxes_outputs[num_sbox], sboxes_witnesses[num_sbox] = self._perm.compute_sbox_with_witness(sboxes_inputs[num_sbox])

        sboxes_data = []
        for inp in perm_inputs:
            sbox_out = inp
            sbox_in = self._perm.compute_sbox_inv(sbox_out)
            _, sbox_wit = self._perm.compute_sbox_with_witness(sbox_in)
            sboxes_data.append((sbox_in, sbox_out, sbox_wit))
        for num_sbox in range(nb_sboxes):
            sboxes_data.append((sboxes_inputs[num_sbox], sboxes_outputs[num_sbox], sboxes_witnesses[num_sbox]))
        # padding with zero can prevent to verify the poly constraint
        # we pad using the values of the last sbox
        while len(sboxes_data) % nb_wit_cols:
            sboxes_data.append(sboxes_data[-1])

        witness = MultiDimArray((nb_wit_rows, nb_wit_cols))
        for num in range(len(sboxes_data)):
            num_col = num % nb_wit_cols
            offset_row = (num // nb_wit_cols)*(2+nb_add_vars)
            witness[offset_row+0][num_col] = sboxes_data[num][0]
            witness[offset_row+1][num_col] = sboxes_data[num][1]
            for i in range(nb_add_vars):
                witness[offset_row+2+i][num_col] = sboxes_data[num][2][i]

        import numpy as np
        witness = list(np.array(witness).reshape((nb_wit_rows*nb_wit_cols,)))
        return witness
