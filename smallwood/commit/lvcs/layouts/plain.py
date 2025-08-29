from .layout import AbstractLayout

class PlainLayout(AbstractLayout):
    def __init__(self, row_length, nb_rows, nb_queries, fullrank_cols):
        self._nb_queries = nb_queries
        self._fullrank_cols = fullrank_cols
        super().__init__(row_length, nb_rows)

    @property
    def nb_queries(self):
        return self._nb_queries
    
    @property
    def fullrank_cols(self):
        return self._fullrank_cols

    def to_rows(self, rows):
        assert len(rows) == self.nb_rows
        for row in rows:
            assert len(row) == self.row_length
        return rows
    
    def get_iop_query_tot_size(self):
        return self.nb_queries * self.nb_rows
    
    def fieldstr_to_iop_query(self, v):
        assert len(v) == self.get_iop_query_tot_size()
        queries = []
        for layout in self.layouts:
            size = layout.get_iop_query_tot_size()
            data, v = v[:size], v[size:]
            queries.append(layout.fieldstr_to_iop_query(data))
        return [
            v[i*self.nb_rows:(i+1)*self.nb_rows]
            for i in range(self.nb_queries)
        ]
    
    def get_nb_lvcs_queries(self):
        return self.nb_queries
    
    def check_iop_queries(self, iop_query):
        pass

    def to_lvcs_queries(self, iop_query):
        return iop_query

    def get_partial_evals_size(self):
        return 0

    def to_iop_responses(self, iop_query, lvcs_responses):
        return lvcs_responses, []

    def to_lvcs_responses(self, iop_query, iop_responses, partial_evals):
        assert len(partial_evals) == 0
        return iop_responses

