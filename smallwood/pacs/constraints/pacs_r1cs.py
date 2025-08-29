from smallwood.pacs import AbstractPACS
from math import ceil

class PACSFromR1CS(AbstractPACS):
    def __init__(self, r1cs, nb_batched, mapping):
        self._r1cs = r1cs
        self._mapping = mapping
        nb_vars = r1cs.get_nb_variables()
        nb_muls = r1cs.get_nb_equations()
        self._nb_cols = nb_batched
        self._nb_batched_muls = ceil(nb_muls/nb_batched)
        self._nb_rows_muls = 3*self._nb_batched_muls
        self._nb_rows_wit = ceil(nb_vars/nb_batched)
        self._nb_rows = self._nb_rows_muls + self._nb_rows_wit

    def get_nb_wit_rows(self):
        return self._nb_rows
    
    def get_nb_wit_cols(self):
        return self._nb_cols
    
    def get_constraint_degree(self):
        raise 2

    def get_nb_parallel_constraints(self):
        return self._nb_batched_muls
        
    def get_nb_aggregated_constraints(self):
        nb_primary = self._r1cs.get_nb_primary_inputs()
        return 3*self._r1cs.get_nb_equations() + nb_primary
    
    def get_theta(self):
        return [
            [None]*self.get_nb_wit_cols()
            for _ in range(self.get_nb_parallel_constraints())
        ]

    def evaluate_parallel_constraints(self, wit_evals, theta):
        values = []
        for j in range(self.get_nb_parallel_constraints()):
            assert theta[j] is None
            values.append(
                wit_evals[3*j+0]*wit_evals[3*j+1] - wit_evals[3*j+2]
            )
        return values

    def get_theta_(self):
        theta_ = []
        nb_wit_cols = self.get_nb_wit_cols()
        F = self._r1cs.get_field()

        for j in range(self._r1cs.get_nb_equations()):
            eq = self._r1cs.equations[j]

            for terms in [eq.a.terms, eq.b.terms, eq.c.terms]:
                values = [[F(0)]*(nb_wit_cols) for _ in range(self._nb_rows_wit+1+1)]
                for elt_id, factor in terms.items():
                    if elt_id is not None:
                        num_row = (elt_id // nb_wit_cols)
                        num_col = (elt_id % nb_wit_cols)
                        values[num_row][num_col] = factor
                    else:
                        values[-2][0] = factor
                num_col = j % nb_wit_cols
                values[-1][num_col] = F(1)
                theta_.append(values)

        # Primary Inputs
        nb_primary = self._r1cs.get_nb_primary_inputs()
        for var_id in range(nb_primary):
            pos = var_id % nb_wit_cols
            value = self._mapping[elt_id]
            theta_.append([
                [0]*pos + [1] + [0]*(nb_wit_cols-1-pos),
                [value] + [0]*(nb_wit_cols-1),
            ])

        return theta_
    
    def evaluate_aggregated_constraints(self, wit_evals, theta):
        nb_wit_cols = self.get_nb_wit_cols()

        values = []
        num_constraints = 0

        for j in range(self._r1cs.get_nb_equations()):
            num_mul_row = (j // nb_wit_cols)
            # A
            val = theta[num_constraints][-2]
            for i, theta_value in enumerate(theta[num_constraints][:-2]):
                val += wit_evals[self._nb_rows_muls+i]*theta_value
            val -= wit_evals[3*num_mul_row+0]*theta[num_constraints][-1]
            values.append(val)
            num_constraints += 1

            # B
            val = theta[num_constraints][-2]
            for i, theta_value in enumerate(theta[num_constraints][:-2]):
                val += wit_evals[self._nb_rows_muls+i]*theta_value
            val -= wit_evals[3*num_mul_row+1]*theta[num_constraints][-1]
            values.append(val)
            num_constraints += 1

            # C
            val = theta[num_constraints][-2]
            for i, theta_value in enumerate(theta[num_constraints][:-2]):
                val += wit_evals[self._nb_rows_muls+i]*theta_value
            val -= wit_evals[3*num_mul_row+2]*theta[num_constraints][-1]
            values.append(val)
            num_constraints += 1

        nb_primary = self._r1cs.get_nb_primary_inputs()
        for var_id in range(nb_primary):
            num_wit_row = var_id // nb_wit_cols
            val = wit_evals[self._nb_rows_muls+num_wit_row]*theta[num_constraints][0] - theta[num_constraints][1]
            values.append(val)
            num_constraints += 1

        return values
