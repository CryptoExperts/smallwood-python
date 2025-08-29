from smallwood.pacs import AbstractPACS

# I know x such that x^{2^4} = y for a public y
class ExamplePACS(AbstractPACS):
    def __init__(self, field, y):
        self._field = field
        self.y = y

    def get_field(self):
        return self._field

    def get_nb_wit_rows(self):
        return 3

    def get_nb_wit_cols(self):
        return 2
    
    def get_constraint_degree(self):
        return 2
    
    def get_nb_parallel_constraints(self):
        return self.get_nb_wit_rows() - 1
    
    def get_nb_aggregated_constraints(self):
        return self.get_nb_wit_cols()
    
    def get_theta(self):
        return [
            [] for _ in range(self.get_nb_parallel_constraints())
        ]

    def evaluate_parallel_constraints(self, wit_evals, theta):
        n = len(wit_evals)-1
        values = [None]*n
        for j in range(n):
            assert len(theta[j]) == 0
            values[j] = wit_evals[j]**2 - wit_evals[j+1]
        return values

    def get_theta_(self):
        nb_wit_cols = self.get_nb_wit_cols()

        theta_ = []
        for j in range(nb_wit_cols-1):
            theta_.append([
                [0]*j + [1,0] + [0]*(nb_wit_cols-j-2),
                [0]*j + [0,1] + [0]*(nb_wit_cols-j-2),
            ])
        
        theta_.append([
            [0]*(nb_wit_cols-1) + [1],
            [0]*(nb_wit_cols-1) + [self.y],
        ])
        return theta_

    def evaluate_aggregated_constraints(self, wit_evals, theta_k):
        nb_wit_cols = self.get_nb_wit_cols()

        values = []
        for j in range(nb_wit_cols-1):
            val = wit_evals[2]*theta_k[j][0] - wit_evals[0]*theta_k[j][1]
            values.append(val)

        val = wit_evals[2]*theta_k[nb_wit_cols-1][0] - theta_k[nb_wit_cols-1][1]
        values.append(val)
        return values

    @classmethod
    def random_instance(cls, field):
        x = field.random_element()
        y = x**(2**4)
        witness = [
            [x,     x**4],
            [x**2,  x**8],
            [x**4, x**16]
        ]
        import numpy as np
        witness = list(np.array(witness).reshape((6,)))
        return cls(field, y), witness









