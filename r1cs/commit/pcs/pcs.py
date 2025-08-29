from r1cs.commit.lvcs import LayoutLVCSWithAOHash_R1CS
from smallwood.commit.pcs.layouts import UnivariateLayout, MultilinearLayout

class UnivariateTensorBasedPCSWithAOHash_R1CS(LayoutLVCSWithAOHash_R1CS):
    def __init__(self, **kwargs):
        super().__init__(
            layout = UnivariateLayout(
                degree = kwargs.pop('degree'),
                poly_col_size = kwargs.pop('poly_col_size'),
                nb_polys = kwargs.pop('nb_polys'),
                nb_queries = kwargs.pop('nb_queries'),
                beta = kwargs.pop('beta', 1),
            ),
            **kwargs
        )

class MultilinearTensorBasedPCSWithAOHash_R1CS(LayoutLVCSWithAOHash_R1CS):
    def __init__(self, **kwargs):
        super().__init__(
            layout = MultilinearLayout(
                nb_variables = kwargs.pop('nb_variables'),
                nb_common_vars = kwargs.pop('nb_common_vars'),
                nb_multilinears = kwargs.pop('nb_multilinears'),
            ),
            **kwargs
        )
