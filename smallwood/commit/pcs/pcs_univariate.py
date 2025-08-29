from smallwood.commit.lvcs.shake import LayoutLVCSWithShake
from smallwood.commit.lvcs.aohash import LayoutLVCSWithAOHash
from .layouts.univariate import UnivariateLayout

class UnivariateTensorBasedPCSWithShake(LayoutLVCSWithShake):
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

class UnivariateTensorBasedPCSWithAOHash(LayoutLVCSWithAOHash):
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


