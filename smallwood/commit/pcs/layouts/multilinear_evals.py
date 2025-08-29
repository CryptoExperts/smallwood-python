from smallwood.commit.lvcs.layouts import AbstractLayout
from utils import MultiDimArray
from utils.multivariate import MultilinearUtils

class EvalMultilinearLayout(AbstractLayout):
    def __init__(self, nb_variables, nb_common_vars, nb_multilinears, ignore_rows=[], ignore_cols=[]):
        assert nb_common_vars <= nb_variables
        self._nb_variables = nb_variables
        self._nb_common_vars = nb_common_vars
        self._nb_multilinears = nb_multilinears

        self._ignored_rows = sorted(set(ignore_rows))
        assert len(self._ignored_rows) == len(ignore_rows), 'Duplicated ignored rows'
        self._ignored_cols = sorted(set(ignore_cols))
        assert len(self._ignored_cols) == len(ignore_cols), 'Duplicated ignored columns'
        for ignored_row in self._ignored_rows:
            assert 0 <= ignored_row and ignored_row < 2**nb_common_vars, f'Invalid ignored row: {ignored_row}'
        for ignored_col in self._ignored_cols:
            assert 0 <= ignored_col and ignored_col < 2**(nb_variables - nb_common_vars), f'Invalid ignored column: {ignored_col}'
        self._remaining_rows = [i for i in range(2**nb_common_vars) if i not in self._ignored_rows]
        self._remaining_cols = [i for i in range(2**(nb_variables-nb_common_vars)) if i not in self._ignored_cols]

        row_length = nb_multilinears * len(self.remaining_cols)
        nb_rows = len(self.remaining_rows)
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

    @property
    def ignored_rows(self):
        return self._ignored_rows

    @property
    def ignored_cols(self):
        return self._ignored_cols

    @property
    def remaining_rows(self):
        return self._remaining_rows

    @property
    def remaining_cols(self):
        return self._remaining_cols

    ### Methods
    def to_rows(self, multilinears):
        assert len(multilinears) == self.nb_multilinears
        R = multilinears[0].parent()
        F = R.base_ring()
        Xs = R.gens()

        multilinear_height = len(self.remaining_rows)
        multilinear_width = len(self.remaining_cols)

        rows = MultiDimArray((self.nb_rows, self.row_length))
        from sage.all import Integer
        for k, multilinear in enumerate(multilinears):
            for i in range(2**self.nb_common_vars):
                for j in range(2**(self.nb_variables-self.nb_common_vars)):
                    b_rows = Integer(i).digits(2, None, self.nb_common_vars)[::-1]
                    b_cols = Integer(j).digits(2, None, self.nb_variables-self.nb_common_vars)[::-1]
                    b = b_rows + b_cols
                    if (i in self.remaining_rows) and (j in self.remaining_cols):
                        idx_row = self.remaining_rows.index(i)
                        idx_col = self.remaining_cols.index(j)
                        rows[idx_row][k*multilinear_width+idx_col] = multilinear(*b)
                    else:
                        assert multilinear(*b) == 0, 'Ignored layout case while it is not zero'

        #print('rows[0][0]', rows[0][0])
        #print('rows[0][1]', rows[0][1])
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
        tprod_rows = MultilinearUtils.tensor_product_lagrange(F, iop_query[:self.nb_common_vars])
        remaining_tprod_rows = [tprod_rows[i] for i in self.remaining_rows]
        fullrank_cols = [0] #TBC
        assert remaining_tprod_rows[0] != 0
        return [remaining_tprod_rows], fullrank_cols

    def get_partial_evals_size(self):
        multilinear_width = len(self.remaining_cols)
        return self.nb_multilinears*(multilinear_width-1)

    def to_iop_responses(self, iop_query, lvcs_responses):
        F = iop_query[0].base_ring()
        assert len(iop_query) == self.nb_variables
        multilinear_width = len(self.remaining_cols)
        tprod_cols = MultilinearUtils.tensor_product_lagrange(F, iop_query[self.nb_common_vars:])
        assert len(lvcs_responses) == 1
        lvcs_response = lvcs_responses[0]

        if False:
            # Choose the pivot
            #  Rmk: tprod_cols has always at least one non-zero value
            non_zero_pos = None
            for idx_col, k in enumerate(self.remaining_cols):
                if tprod_cols[k] != 0:
                    non_zero_pos = idx_col
            assert non_zero_pos is not None, 'Impossible to find a pivot'
        else:
            # Using R1CS Constraint does not allow to have dynamic pivot
            non_zero_pos = 0
            assert tprod_cols[self.remaining_cols[non_zero_pos]] != 0, 'Invalid pivot'

        partial_evals = []
        iop_response = []
        for j in range(self.nb_multilinears):
            multilinear_eval = F(0)
            for idx_col, k in enumerate(self.remaining_cols):
                multilinear_eval += lvcs_response[j*multilinear_width+idx_col] * tprod_cols[k]
            iop_response.append(multilinear_eval)
            partial_evals += lvcs_response[j*multilinear_width:j*multilinear_width+non_zero_pos]
            partial_evals += lvcs_response[j*multilinear_width+(non_zero_pos+1):(j+1)*multilinear_width]

        return iop_response, partial_evals

    def to_lvcs_responses(self, iop_query, iop_response, partial_evals):
        F = iop_query[0].base_ring()
        assert len(iop_query) == self.nb_variables
        multilinear_width = len(self.remaining_cols)
        tprod_cols = MultilinearUtils.tensor_product_lagrange(F, iop_query[self.nb_common_vars:])

        if False:
            non_zero_pos = None
            for idx_col, k in enumerate(self.remaining_cols):
                if tprod_cols[k] != 0:
                    non_zero_pos = idx_col
            assert non_zero_pos is not None, 'Impossible to find a pivot'
        else:
            # Using R1CS Constraint does not allow to have dynamic pivot
            non_zero_pos = 0

        lvcs_iop_response = []
        for j in range(self.nb_multilinears):
            value = iop_response[j]
            partial_eval = partial_evals[j*(multilinear_width-1):(j+1)*(multilinear_width-1)]
            assert len(partial_eval) == multilinear_width-1
            partial_eval_before_pivot = partial_eval[:non_zero_pos]
            partial_eval_after_pivot = partial_eval[non_zero_pos:]
            for idx, k in enumerate(self.remaining_cols[:non_zero_pos]):
                value -= partial_eval_before_pivot[idx] * tprod_cols[k]
            for idx, k in enumerate(self.remaining_cols[non_zero_pos+1:]):
                value -= partial_eval_after_pivot[idx] * tprod_cols[k]
            value /= tprod_cols[self.remaining_cols[non_zero_pos]]
            
            lvcs_iop_response += partial_eval_before_pivot
            lvcs_iop_response += [value]
            lvcs_iop_response += partial_eval_after_pivot
        
        return [lvcs_iop_response]
