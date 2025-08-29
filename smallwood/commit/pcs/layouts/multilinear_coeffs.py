from smallwood.commit.lvcs.layouts import AbstractLayout
from utils import MultiDimArray, MultilinearUtils

class MultilinearLayout(AbstractLayout):
    def __init__(self, nb_variables, nb_common_vars, nb_multilinears):
        assert nb_common_vars <= nb_variables
        self._nb_variables = nb_variables
        self._nb_common_vars = nb_common_vars
        self._nb_multilinears = nb_multilinears

        row_length = nb_multilinears * 2**(nb_variables - nb_common_vars)
        nb_rows = 2**nb_common_vars
        super().__init__(row_length, nb_rows)

    ### Getters
    @property
    def nb_variables(self):
        return self._nb_variables

    @property
    def nb_common_vars(self):
        return self._nb_common_vars

    @property
    def nb_multilinears(self):
        return self._nb_multilinears

    ### Methods
    def to_rows(self, multilinears):
        assert len(multilinears) == self.nb_multilinears
        R = multilinears[0].parent()
        F = R.base_ring()
        Xs = R.gens()

        tprod_rows = MultilinearUtils.tensor_product(F, Xs[:self.nb_common_vars])
        tprod_cols = MultilinearUtils.tensor_product(F, Xs[self.nb_common_vars:])
        multilinear_height = 2**self.nb_common_vars
        multilinear_width = 2**(self.nb_variables-self.nb_common_vars)

        rows = MultiDimArray((self.nb_rows, self.row_length))
        for k, multilinear in enumerate(multilinears):
            coeffs = list(multilinear)
            for i in range(len(tprod_rows)):
                for j in range(len(tprod_cols)):
                    index = None
                    for pos, (_, mono) in enumerate(coeffs):
                        if mono == tprod_rows[i]*tprod_cols[j]:
                            index = pos
                    assert index is not None
                    rows[i][k*multilinear_width+j] = coeffs[index][0]

        return rows

    def get_iop_query_tot_size(self):
        return self.nb_variables
    
    def fieldstr_to_iop_query(self, v):
        assert len(v) == self.get_iop_query_tot_size()
        return v

    def get_nb_lvcs_queries(self):
        return 1

    def check_iop_queries(self, iop_query):
        pass

    def to_lvcs_queries(self, iop_query):
        F = iop_query[0].base_ring()
        assert len(iop_query) == self.nb_variables
        multilinear_height = 2**self.nb_common_vars
        tprod_rows = MultilinearUtils.tensor_product(F, iop_query[:self.nb_common_vars])
        assert len(tprod_rows) == multilinear_height
        assert tprod_rows[0] == F(1)

        fullrank_cols = [0]
        return [tprod_rows], fullrank_cols

    def get_partial_evals_size(self):
        multilinear_width = 2**(self.nb_variables-self.nb_common_vars)
        return self.nb_multilinears*(multilinear_width-1)

    def to_iop_responses(self, iop_query, lvcs_responses):
        F = iop_query[0].base_ring()
        assert len(iop_query) == self.nb_variables
        multilinear_width = 2**(self.nb_variables-self.nb_common_vars)
        tprod_cols = MultilinearUtils.tensor_product(F, iop_query[self.nb_common_vars:])
        assert len(tprod_cols) == multilinear_width
        assert tprod_cols[0] == F(1)
        assert len(lvcs_responses) == 1
        lvcs_response = lvcs_responses[0]

        partial_evals = []
        iop_response = []
        for j in range(self.nb_multilinears):
            multilinear_eval = F(0)
            for k in range(multilinear_width):
                multilinear_eval += lvcs_response[j*multilinear_width+k] * tprod_cols[k]
            iop_response.append(multilinear_eval)
            partial_evals += lvcs_response[j*multilinear_width+1:(j+1)*multilinear_width]

        return iop_response, partial_evals

    def to_lvcs_responses(self, iop_query, iop_response, partial_evals):
        F = iop_query[0].base_ring()
        assert len(iop_query) == self.nb_variables
        multilinear_width = 2**(self.nb_variables-self.nb_common_vars)
        tprod_cols = MultilinearUtils.tensor_product(F, iop_query[self.nb_common_vars:])
        assert len(tprod_cols) == multilinear_width
        assert tprod_cols[0] == F(1)

        lvcs_iop_response = []
        for j in range(self.nb_multilinears):
            value = iop_response[j]
            partial_eval = partial_evals[j*(multilinear_width-1):(j+1)*(multilinear_width-1)]
            for k in range(1, multilinear_width):
                value -= partial_eval[k-1] * tprod_cols[k]
            
            lvcs_iop_response += [value]
            lvcs_iop_response += partial_eval
        
        return [lvcs_iop_response]
