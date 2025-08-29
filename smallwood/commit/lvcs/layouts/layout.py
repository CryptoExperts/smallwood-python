class AbstractLayout:
    def __init__(self, row_length, nb_rows):
        self._row_length = row_length
        self._nb_rows = nb_rows

    ### Getters
    @property
    def row_length(self):
        return self._row_length

    @property
    def nb_rows(self):
        return self._nb_rows

    ### Methods
    def to_rows(self, *args, **kwargs):
        raise NotImplementedError()

    def get_iop_query_tot_size(self):
        raise NotImplementedError()
    
    def fieldstr_to_iop_query(self, v):
        raise NotImplementedError()

    def get_nb_lvcs_queries(self, *args, **kwargs):
        raise NotImplementedError()

    def check_iop_queries(self, *args, **kwargs):
        raise NotImplementedError()

    def to_lvcs_queries(self, *args, **kwargs):
        raise NotImplementedError()

    def get_partial_evals_size(self):
        raise NotImplementedError()
        
    def to_iop_responses(self, *args, **kwargs):
        raise NotImplementedError()

    def to_lvcs_responses(self, *args, **kwargs):
        raise NotImplementedError()

