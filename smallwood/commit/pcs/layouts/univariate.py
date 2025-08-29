from smallwood.commit.lvcs.layouts import AbstractLayout
from math import ceil
from utils import MultiDimArray

class GenericUnivariateLayout(AbstractLayout):
    def __init__(self, degrees, poly_col_size, nb_queries, beta=1):
        self._degrees = degrees
        self._nb_polys = len(degrees)
        self._nb_queries = nb_queries
        self._poly_col_size = poly_col_size # mu
        self._beta = beta

        split_factors = [ # nu_j
            ceil((deg+1-nb_queries)/poly_col_size)
            for deg in degrees
        ]
        self._split_factors = split_factors

        self._unstacked_row_length = sum(split_factors)
        self._unstacked_nb_rows = poly_col_size + nb_queries

        row_length = ceil(self.unstacked_row_length/beta)
        nb_rows = beta*self.unstacked_nb_rows
        super().__init__(row_length, nb_rows)

    ### Getters
    @property
    def degrees(self):
        return self._degrees

    @property
    def nb_polys(self):
        return self._nb_polys

    @property
    def nb_queries(self):
        return self._nb_queries

    @property
    def poly_col_size(self):
        return self._poly_col_size

    @property
    def beta(self):
        return self._beta

    @property
    def split_factors(self):
        return self._split_factors

    @property
    def unstacked_row_length(self):
        return self._unstacked_row_length

    @property
    def unstacked_nb_rows(self):
        return self._unstacked_nb_rows
    
    ### Methods
    def to_rows(self, polynomials):
        assert len(polynomials) == self.nb_polys
        R = polynomials[0].parent()
        F = R.base_ring()
        X = R.gen()

        unit_polys = []
        for num, poly in enumerate(polynomials):
            assert poly.degree() <= self.degrees[num]
            previous_leading_coefficients = None
            for i in range(self.split_factors[num]):
                if i < self.split_factors[num] - 1:
                    unit_poly = poly % X**self.poly_col_size
                    poly = poly // X**self.poly_col_size
                    if previous_leading_coefficients is not None:
                        unit_poly -= previous_leading_coefficients
                    leading_coefficients = R.random_element(degree=self.nb_queries-1)
                    unit_poly += leading_coefficients * X**self.poly_col_size
                    previous_leading_coefficients = leading_coefficients
                else: # Last
                    last_degree = self.degrees[num] - (self.split_factors[num]-1)*self.poly_col_size
                    assert poly.degree() <= last_degree
                    unit_poly = poly
                    if previous_leading_coefficients is not None:
                        unit_poly -= previous_leading_coefficients
                    unit_poly *= X**(self.unstacked_nb_rows-1-last_degree)
                unit_polys.append(unit_poly)

        unstacked_rows = MultiDimArray((self.unstacked_nb_rows, self.unstacked_row_length))
        for num_col, unit_poly in enumerate(unit_polys):
            for num_row in range(self.unstacked_nb_rows):
                unstacked_rows[num_row][num_col] = unit_poly[num_row]

        rows = MultiDimArray((self.nb_rows, self.row_length), F(0))
        for num_unstacked_col in range(self.unstacked_row_length):
            for num_unstacked_row in range(self.unstacked_nb_rows):
                num_row = (num_unstacked_col//self.row_length)*self.unstacked_nb_rows + num_unstacked_row
                num_col = num_unstacked_col % self.row_length
                rows[num_row][num_col] = unstacked_rows[num_unstacked_row][num_unstacked_col]

        return rows

    def get_iop_query_tot_size(self):
        return self.nb_queries
    
    def fieldstr_to_iop_query(self, v):
        assert len(v) == self.get_iop_query_tot_size()
        return v

    def get_nb_lvcs_queries(self):
        return self.nb_queries*self.beta

    def check_iop_queries(self, iop_queries):
        for i in range(self.nb_queries):
            for j in range(i+1, self.nb_queries):
                assert iop_queries[i] != iop_queries[j]

    def to_lvcs_queries(self, iop_queries):
        F = iop_queries[0].base_ring()
        zero = F(0)
        lvcs_queries = []
        for j in range(self.nb_queries):
            powers = [iop_queries[j]**i for i in range(self.unstacked_nb_rows)]
            for k in range(self.beta):
                lvcs_query = [zero]*(k*self.unstacked_nb_rows) + powers + [zero]*((self.beta-1-k)*self.unstacked_nb_rows)
                assert len(lvcs_query) == self.nb_rows
                lvcs_queries.append(lvcs_query)

        fullrank_cols = []
        for k in range(self.beta):
            fullrank_cols += [k*self.unstacked_nb_rows+j for j in range(self.nb_queries)]

        return lvcs_queries, fullrank_cols

    def _get_exponents_to_rebuild_poly(self):
        exponents = [None]*self.nb_polys
        for num in range(self.nb_polys):
            exponents[num] = []
            for k in range(self.split_factors[num]):
                if k < self.split_factors[num] - 1:
                    exponents[num].append(k*self.poly_col_size)
                else:
                    last_degree = self.degrees[num] - (self.split_factors[num]-1)*self.poly_col_size
                    exponents[num].append((self.split_factors[num]-1)*self.poly_col_size-(self.unstacked_nb_rows-1-last_degree))
        return exponents

    def get_partial_evals_size(self):
        return sum(split_factor-1 for split_factor in self.split_factors)*self.nb_queries

    def to_iop_responses(self, iop_queries, lvcs_responses):
        exponents = self._get_exponents_to_rebuild_poly()
        F = iop_queries[0].base_ring()
        assert len(lvcs_responses) == self.nb_queries*self.beta

        unstacked_lvcs_responses = [[] for _ in range(self.nb_queries)]
        for num_query in range(self.nb_queries):
            for k in range(self.beta):
                unstacked_lvcs_responses[num_query] += lvcs_responses[k+num_query*self.beta]
            assert len(unstacked_lvcs_responses[num_query]) == self.row_length*self.beta
            for j in range(self.unstacked_row_length, self.row_length*self.beta):
                assert unstacked_lvcs_responses[num_query][j] == F(0)
            unstacked_lvcs_responses[num_query] = unstacked_lvcs_responses[num_query][:self.unstacked_row_length]

        iop_responses = []
        partial_evals = []
        for num, lvcs_response in enumerate(unstacked_lvcs_responses):
            iop_response = []
            for j in range(self.nb_polys):
                lvcs_response_for_j, lvcs_response = lvcs_response[:self.split_factors[j]], lvcs_response[self.split_factors[j]:]
                poly_eval = F(0)
                for k in range(self.split_factors[j]):
                    poly_eval += lvcs_response_for_j[k] * iop_queries[num]**exponents[j][k]
                iop_response.append(poly_eval)
                partial_evals += lvcs_response_for_j[1:]
            iop_responses.append(iop_response)

        return iop_responses, partial_evals

    def to_lvcs_responses(self, iop_queries, iop_responses, partial_evals):
        exponents = self._get_exponents_to_rebuild_poly()
        F = iop_queries[0].base_ring()
        assert len(iop_responses) == self.nb_queries

        unstacked_lvcs_responses = []
        for num, iop_response in enumerate(iop_responses):
            lvcs_iop_response = []
            for j in range(self.nb_polys):
                partial_evals_for_j, partial_evals = partial_evals[:self.split_factors[j]-1], partial_evals[self.split_factors[j]-1:]
                value = iop_response[j]
                for k in range(1, self.split_factors[j]):
                    value -= partial_evals_for_j[k-1] * iop_queries[num]**exponents[j][k]
                
                lvcs_iop_response += [value]
                lvcs_iop_response += partial_evals_for_j
            unstacked_lvcs_responses.append(lvcs_iop_response)
        assert len(partial_evals) == 0
        
        lvcs_responses = []
        for num_query in range(self.nb_queries):
            assert len(unstacked_lvcs_responses[num_query]) == self.unstacked_row_length
            unstacked_lvcs_responses[num_query] += [F(0)]*(self.row_length*self.beta-self.unstacked_row_length)
            for k in range(self.beta):
                lvcs_responses.append(unstacked_lvcs_responses[num_query][k*self.row_length:(k+1)*self.row_length])

        assert len(lvcs_responses) == self.nb_queries*self.beta
        return lvcs_responses

class UnivariateLayout(GenericUnivariateLayout):
    def __init__(self, degree, poly_col_size, nb_polys, nb_queries, beta=1):
        super().__init__(
            degrees = [degree]*nb_polys,
            poly_col_size = poly_col_size,
            nb_queries = nb_queries,
            beta = beta,
        )
        self._degree = degree

    @property
    def degree(self):
        return self._degree


class MonoUnivariateLayout(UnivariateLayout):
    def __init__(self, degree, poly_col_size, nb_queries, beta=1):
        super().__init__(degree, poly_col_size, nb_polys=1, nb_queries=nb_queries, beta=beta)

    def to_rows(self, polynomial):
        return super().to_rows([polynomial])
    
    def to_iop_responses(self, iop_query, lvcs_responses):
        iop_responses, partial_evals = super().to_iop_responses(iop_query, lvcs_responses)
        iop_responses = [iop_response for [iop_response] in iop_responses]
        return iop_responses, partial_evals

    def to_lvcs_responses(self, iop_query, iop_responses, partial_evals):
        iop_responses = [[iop_response] for iop_response in iop_responses]
        return super().to_lvcs_responses(iop_query, iop_responses, partial_evals)
