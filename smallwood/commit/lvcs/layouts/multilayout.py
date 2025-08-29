from .layout import AbstractLayout

def pad(v, total, before=0):
    assert len(v)+before <= total
    assert len(v) > 0, 'Should be not empty to know the field'
    F = v[0].base_ring()
    padding_prefix = [F(0)]*before
    padding_suffix = [F(0)]*(total-before-len(v))
    return padding_prefix + v + padding_suffix

class MultiLayout(AbstractLayout):
    def __init__(self, layouts):
        self._layouts = layouts
        assert len(layouts) > 0

        row_length = layouts[0].row_length
        nb_rows = layouts[0].nb_rows
        for layout in layouts[1:]:
            row_length = max(row_length, layout.row_length)
            nb_rows += layout.nb_rows

        super().__init__(row_length, nb_rows)

    ### Getters
    @property
    def layouts(self):
        return self._layouts

    ### Methods
    def to_rows(self, layout_inputs):
        assert len(layout_inputs) == len(self.layouts)

        rows = []
        for num, layout in enumerate(self.layouts):
            layout_rows = layout.to_rows(layout_inputs[num])
            for row in layout_rows:
                rows.append(pad(row, self.row_length))

        return rows
    
    def get_iop_query_tot_size(self):
        return sum(layout.get_iop_query_tot_size() for layout in self.layouts)
    
    def fieldstr_to_iop_query(self, v):
        assert len(v) == self.get_iop_query_tot_size()
        queries = []
        for layout in self.layouts:
            size = layout.get_iop_query_tot_size()
            data, v = v[:size], v[size:]
            queries.append(layout.fieldstr_to_iop_query(data))
        return queries
    
    def get_nb_lvcs_queries(self):
        return sum(layout.get_nb_lvcs_queries() for layout in self.layouts)

    def _pad_lvcs_queries(self, num_layout, lvcs_queries):
        nb_prior_rows = sum(layout.nb_rows for layout in self.layouts[:num_layout])
        padded_lvcs_queries = []
        for query in lvcs_queries:
            padded_lvcs_query = pad(query, self.nb_rows, before=nb_prior_rows)
            assert len(padded_lvcs_query) == self.nb_rows
            padded_lvcs_queries.append(padded_lvcs_query)
        return padded_lvcs_queries
    
    def check_iop_queries(self, iop_query):
        for num, layout in enumerate(self.layouts):
            layout.check_iop_queries(iop_query[num])

    def to_lvcs_queries(self, iop_query):
        lvcs_iop_queries = []
        fullrank_cols = []
        offset = 0
        for num, layout in enumerate(self.layouts):
            layout_lvcs_queries, layout_fullrank_cols = layout.to_lvcs_queries(iop_query[num])
            padded_layout_lvcs_queries = self._pad_lvcs_queries(num, layout_lvcs_queries)
            lvcs_iop_queries += padded_layout_lvcs_queries
            fullrank_cols += [offset+col for col in layout_fullrank_cols]
            offset += layout.nb_rows

        return lvcs_iop_queries, fullrank_cols

    def get_partial_evals_size(self):
        return sum(layout.get_partial_evals_size() for layout in self.layouts)

    def to_iop_responses(self, iop_query, padded_lvcs_iop_responses):
        F = padded_lvcs_iop_responses[0][0].base_ring()

        # Formatting
        lvcs_iop_responses_by_layout = [[] for _ in self.layouts]
        for num, layout in enumerate(self.layouts):
            nb_lvcs_responses = layout.get_nb_lvcs_queries()
            layout_padded_lvcs_iop_responses, padded_lvcs_iop_responses = padded_lvcs_iop_responses[:nb_lvcs_responses], padded_lvcs_iop_responses[nb_lvcs_responses:]
            for resp in layout_padded_lvcs_iop_responses:
                for i in range(layout.row_length, self.row_length):
                    assert resp[i] == F(0)
                lvcs_iop_responses_by_layout[num].append(resp[:layout.row_length])

        iop_responses = []
        partial_evals = []
        for num, layout in enumerate(self.layouts):
            layout_iop_response, layout_partial_evals = layout.to_iop_responses(iop_query[num], lvcs_iop_responses_by_layout[num])
            iop_responses.append(layout_iop_response)
            partial_evals += layout_partial_evals

        return iop_responses, partial_evals

    def to_lvcs_responses(self, iop_query, iop_responses, partial_evals):

        padded_lvcs_iop_responses = []
        for num, layout in enumerate(self.layouts):
            layout_partial_evals, partial_evals = partial_evals[:layout.get_partial_evals_size()], partial_evals[layout.get_partial_evals_size():]
            for resp in layout.to_lvcs_responses(iop_query[num], iop_responses[num], layout_partial_evals):
                padded_lvcs_iop_responses.append(pad(resp, self.row_length))
        
        return padded_lvcs_iop_responses
