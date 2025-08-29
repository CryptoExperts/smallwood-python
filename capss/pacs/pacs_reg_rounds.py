from .pacs_perm import PermPreimagePACS
from capss.hash.permutation import RegularIteratedPermutation
from math import ceil
from utils import MultiDimArray

class RegRoundsHashPACS(PermPreimagePACS):
    def __init__(self, perm, iv, y, batching_factor=1):
        assert isinstance(perm, RegularIteratedPermutation)
        super().__init__(perm, iv, y)
        self._batching_factor = batching_factor

        nb_rounds = self._perm.get_number_rounds()
        state_size = self._perm.get_state_size()
        nb_add_vars = self._perm.get_round_witness_size()

        # Compute Nb Wit Cols
        nb_wit_cols = ceil(nb_rounds/batching_factor)
        self._nb_wit_cols = nb_wit_cols

        # Compute Nb Wit Rows
        self._nb_wit_rows = (batching_factor+1)*state_size + nb_add_vars*batching_factor

        # Compute Nb Parallel Constraints
        self._nb_para_constraints = batching_factor*(state_size+nb_add_vars)

        # Compute Nb Aggregated Constraints
        iv_size = len(iv)
        y_size = len(y)
        self._nb_aggr_constraints = (nb_wit_cols-1)*state_size+iv_size+y_size

    def get_batching_factor(self):
        return self._batching_factor

    def get_nb_wit_rows(self):
        return self._nb_wit_rows
    
    def get_nb_wit_cols(self):
        return self._nb_wit_cols
    
    def get_constraint_degree(self):
        return self._perm.get_degree_of_round_verification_function()
        
    def get_nb_parallel_constraints(self):
        return self._nb_para_constraints
    
    def get_nb_aggregated_constraints(self):
        return self._nb_aggr_constraints
    
    def get_theta(self):
        state_size = self._perm.get_state_size()
        nb_add_vars = self._perm.get_round_witness_size()
        batching_factor = self.get_batching_factor()
        nb_wit_cols = self.get_nb_wit_cols()
        nb_rounds = self._perm.get_number_rounds()

        nb_constants_per_round = self._perm.get_nb_constants_per_round()

        round_constants = []
        for num_round in range(nb_rounds):
            cnst = self._perm.get_round_constants(num_round)
            assert len(cnst) == nb_constants_per_round
            round_constants.append(cnst)
        for _ in range(batching_factor*nb_wit_cols - nb_rounds):
            round_constants.append([0]*nb_constants_per_round)

        theta_per_pack = [
            [
                [
                    round_constants[k*batching_factor + i][j]
                    for k in range(nb_wit_cols)
                ]
                for j in range(nb_constants_per_round)
            ]
            for i in range(batching_factor)
        ]
        return [
            (theta_per_pack[i//(state_size+nb_add_vars)] if i % (state_size+nb_add_vars) == 0 else [])
            for i in range(self.get_nb_parallel_constraints())
        ]

    def evaluate_parallel_constraints(self, wit_evals, theta):
        state_size = self._perm.get_state_size()
        batching_factor = self.get_batching_factor()
        nb_add_vars = self._perm.get_round_witness_size()

        state = []
        add_vars = []
        wit_evals = list(wit_evals) # To copy, such that modifying "wit_evals" does not impact the given argument, even when it is a Numpy array

        # Parse Wit Evals
        for i in range(batching_factor+1):
            cur_state, wit_evals = wit_evals[:state_size], wit_evals[state_size:]
            state.append(cur_state)
        for i in range(batching_factor):
            vars, wit_evals = wit_evals[:nb_add_vars], wit_evals[nb_add_vars:]
            add_vars.append(vars)

        # Evaluate Verification Function
        all_values = []
        for i in range(batching_factor):
            cst = theta[i*(state_size+nb_add_vars)]
            all_values += self._perm.run_round_verification_function(state[i], state[i+1], add_vars[i], cst)

        return all_values

    def get_theta_(self):
        nb_wit_cols = self.get_nb_wit_cols()
        state_size = self._perm.get_state_size()

        theta_ = []
        for j in range(nb_wit_cols-1):
            for _ in range(state_size):
                theta_.append([
                    [0]*j + [1,0] + [0]*(nb_wit_cols-j-2),
                    [0]*j + [0,1] + [0]*(nb_wit_cols-j-2),
                ])
        
        # IV
        iv_size = len(self._iv)
        for j in range(iv_size):
            theta_.append([
                [1]           + [0]*(nb_wit_cols-1),
                [self._iv[j]] + [0]*(nb_wit_cols-1),
            ])

        # y
        y_size = len(self._y)
        for j in range(y_size):
            theta_.append([
                [0]*(nb_wit_cols-1) + [1],
                [0]*(nb_wit_cols-1) + [self._y[j]],
            ])

        return theta_
    
    def evaluate_aggregated_constraints(self, wit_evals, theta):
        nb_wit_cols = self.get_nb_wit_cols()
        state_size = self._perm.get_state_size()
        nb_rounds = self._perm.get_number_rounds()
        batching_factor = self.get_batching_factor()

        values = []
        num_constraints = 0

        # Wiring
        for j in range(nb_wit_cols-1):
            for i in range(state_size):
                val = wit_evals[batching_factor*state_size+i]*theta[num_constraints][0] - wit_evals[i]*theta[num_constraints][1]
                values.append(val)
                num_constraints += 1

        # IV
        iv_size = len(self._iv)
        for j in range(iv_size):
            val = wit_evals[j]*theta[num_constraints][0] - theta[num_constraints][1]
            values.append(val)
            num_constraints += 1

        # y
        y_size = len(self._y)
        pos_y = (batching_factor - (batching_factor*nb_wit_cols - nb_rounds))*state_size
        for j in range(y_size):
            val = wit_evals[pos_y+j]*theta[num_constraints][0] - theta[num_constraints][1]
            values.append(val)
            num_constraints += 1
        
        return values
        
    def secret_to_witness(self, secret):
        nb_wit_rows = self.get_nb_wit_rows()
        nb_wit_cols = self.get_nb_wit_cols()
        state_size = self._perm.get_state_size()
        nb_rounds = self._perm.get_number_rounds()
        batching_factor = self.get_batching_factor()
        nb_add_vars = self._perm.get_round_witness_size()
        nb_constants_per_round = self._perm.get_nb_constants_per_round()

        F = self.get_field()

        intermediary_states = []
        round_wits = []

        state = self._iv + secret
        intermediary_states.append(state)

        for r in range(0, batching_factor*nb_wit_cols):
            round_constants = [F(0)]*nb_constants_per_round
            if r < nb_rounds:
                round_constants = self._perm.get_round_constants(r)
            state, round_wit = self._perm.run_round_permutation_with_witness(state, round_constants)

            assert len(round_wit) == nb_add_vars
            assert len(state) == state_size
            intermediary_states.append(state)
            round_wits.append(round_wit)

        witness = MultiDimArray((nb_wit_rows, nb_wit_cols))
        for i in range(nb_wit_cols):
            for k in range(batching_factor+1):
                for j in range(state_size):
                    witness[k*state_size+j][i] = intermediary_states[i*batching_factor+k][j]
            for k in range(batching_factor):
                for j in range(nb_add_vars):
                    witness[(batching_factor+1)*state_size+k*nb_add_vars+j][i] = round_wits[i*batching_factor+k][j]

        import numpy as np
        witness = list(np.array(witness).reshape((nb_wit_rows*nb_wit_cols,)))
        return witness
