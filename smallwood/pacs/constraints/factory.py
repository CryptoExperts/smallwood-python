class LUT:
    def __init__(self, lut):
        self._lut = lut

    def __contains__(self, item):
        value = 0
        for v in self._lut:
            value *= (v-item)
        return (value == 0)

class PACSFactory:
    def __init__(self, nb_rows, nb_cols):
        self._nb_rows = nb_rows
        self._nb_cols = nb_cols
        self._para_constraints = []
        self._aggr_constraints = []

    def get_witness(self):
        from .constraints_aggr import Variable
        import numpy as np
        return np.array([
            [
                Variable((num_row, num_col))
                for num_col in range(self._nb_cols)
            ]
            for num_row in range(self._nb_rows)
        ])
    
    def get_pvar(self):
        from .constraints_para import Variable
        def pvar(i):
            assert i<self._nb_rows
            return Variable(num_row=i)
        return pvar
    
    def register(self, constraints):
        from .constraints_aggr import Constraint as AggrConstraint
        from .constraints_para import Constraint as ParaConstraint
        for constraint in constraints:
            if isinstance(constraint, ParaConstraint):
                self._para_constraints.append(constraint)
            elif isinstance(constraint, AggrConstraint):
                self._aggr_constraints.append(constraints)
    
    def get_pacs_instance():
        raise NotImplementedError()
