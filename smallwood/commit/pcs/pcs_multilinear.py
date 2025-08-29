from smallwood.commit.lvcs.shake import LayoutLVCSWithShake
from smallwood.commit.lvcs.aohash import LayoutLVCSWithAOHash
from .layouts import MultilinearLayout

class MultilinearTensorBasedPCSWithShake(LayoutLVCSWithShake):
    def __init__(self, **kwargs):
        super().__init__(
            layout = MultilinearLayout(
                nb_variables = kwargs.pop('nb_variables'),
                nb_common_vars = kwargs.pop('nb_common_vars'),
                nb_multilinears = kwargs.pop('nb_multilinears'),
            ),
            **kwargs
        )

class MultilinearTensorBasedPCSWithAOHash(LayoutLVCSWithAOHash):
    def __init__(self, **kwargs):
        super().__init__(
            layout = MultilinearLayout(
                nb_variables = kwargs.pop('nb_variables'),
                nb_common_vars = kwargs.pop('nb_common_vars'),
                nb_multilinears = kwargs.pop('nb_multilinears'),
            ),
            **kwargs
        )

