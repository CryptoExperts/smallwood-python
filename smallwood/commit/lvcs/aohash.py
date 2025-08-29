from .lvcs import LVCS
from .layoutlvcs import LayoutLVCS
from sage.all import flatten
from utils import MultiDimArray

class LVCSWithAOHash(LVCS):
    def __init__(self, **kwargs):
        self.commitment_size = kwargs.pop('commitment_size')
        self.hash_xof = kwargs.pop('hash_xof')
        assert self.hash_xof.get_capacity() == self.commitment_size
        self.decs_hash_leaves = kwargs.pop('decs_hash_leaves')
        self.decs_opening_challenge_size = kwargs.pop('decs_opening_challenge_size', 1)
        super().__init__(**kwargs)

    def get_decs_class(self):
        from smallwood.commit.decs.aohash import DECSWithAOHash
        return lambda **kwargs: DECSWithAOHash(
            commitment_size = self.commitment_size,
            hash_leaves = self.decs_hash_leaves,
            hash_xof = self.hash_xof,
            opening_challenge_size = self.decs_opening_challenge_size,
            **kwargs
        )
    
    def hash_challenge_opening_decs(self, binding, iop_responses, associated_rnd):
        field = self.field
        domain_separator = []
        return self.hash_xof(
            domain_separator + binding + flatten(iop_responses, max_level=2) + flatten(associated_rnd, max_level=2),
            output_size=self.commitment_size,
            label = 'Com IOP Response',
        )

    def xof_lvcs_opening(self, binding):
        return self.hash_xof(binding, output_size=self.nb_queries*self.nb_rows)
    

class LayoutLVCSWithAOHash(LayoutLVCS):
    def __init__(self, **kwargs):
        self.commitment_size = kwargs.pop('commitment_size')
        self.hash_xof = kwargs.pop('hash_xof')
        assert self.hash_xof.get_capacity() == self.commitment_size
        self.decs_hash_leaves = kwargs.pop('decs_hash_leaves')
        self.decs_opening_challenge_size = kwargs.pop('decs_opening_challenge_size', 1)
        super().__init__(**kwargs)

    def get_lvcs_class(self):
        return lambda **kwargs: LVCSWithAOHash(
            commitment_size=self.commitment_size,
            hash_xof=self.hash_xof,
            decs_hash_leaves=self.decs_hash_leaves,
            decs_opening_challenge_size=self.decs_opening_challenge_size,
            **kwargs
        )

    def xof_layout_lvcs_opening_flat(self, binding):
        return self.hash_xof(binding, output_size=self.layout.get_iop_query_tot_size())
