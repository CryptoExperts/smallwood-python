from smallwood.pacs import AbstractPACS

class PACS(AbstractPACS):
    def __init__(self, nb_rows, nb_cols, para_constraints, aggr_constraints):
        self._nb_rows = nb_rows
        self._nb_cols = nb_cols
        self._para_constraints = para_constraints
        self._aggr_constraints = aggr_constraints
        self._degree = 0
        for constr in para_constraints + aggr_constraints:
            deg = constr.degree()
            if deg > self._degree:
                self._degree = deg

    def get_nb_wit_rows(self):
        return self._nb_rows
    
    def get_nb_wit_cols(self):
        return self._nb_cols
    
    def get_constraint_degree(self):
        raise self._degree

    def get_nb_parallel_constraints(self):
        return len(self._para_constraints)
        
    def get_nb_aggregated_constraints(self):
        return len(self._aggr_constraints)
    
        
    def get_theta(self):
        return [
            [None]*self.get_nb_wit_cols()
            for _ in range(self.get_nb_parallel_constraints())
        ]

    def evaluate_parallel_constraints(self, wit_evals, theta):
        values = []
        data = {
            i: wit_evals[j]
            for i in self.get_nb_wit_rows()
        }
        for j, constraint in enumerate(self._para_constraints):
            assert theta[j] is None
            values.append(
                constraint.evaluate(data)
            )
        return values
        
    def get_theta_(self):
        theta_ = []
        nb_rows = self.get_nb_wit_rows()
        nb_cols = self.get_nb_wit_cols()

        for j, constraint in enumerate(self._aggr_constraints):
            assert constraint.degree() == 1
            lst = constraint._lst
            offset = constraint._offset

            values = [[None]*(nb_rows+1) for _ in range(nb_cols)]
            for [mono], scalar in lst:
                x, y = mono
                values[y][x] = scalar
            values[0][-1] = offset

            theta_.append(values)
        return theta_

    def evaluate_aggregated_constraints(self, wit_evals, theta_k):
        nb_constraints = self.get_nb_wit_cols()
        values = [None]*nb_constraints
        nb_rows = self.get_nb_wit_rows()
        for j, constraint in enumerate(self._aggr_constraints):
            assert constraint.degree() == 1
            val = 0

            ind = 0
            for i in range(nb_rows):
                if theta_k[j][ind] is not None:
                    val +=  wit_evals[i]*theta_k[j][ind]
                ind += 1
            
            if theta_k[j][-1] is not None:
                val += theta_k[j][-1]
            values.append(val)
        return values
