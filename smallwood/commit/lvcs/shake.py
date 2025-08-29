from .lvcs import LVCS
from .layoutlvcs import LayoutLVCS

class LVCSWithShake(LVCS):
    def __init__(self, security_level, **kwargs):
        self._security_level = security_level
        super().__init__(**kwargs)
        
        from math import ceil
        self._security_level_in_bytes = ceil(security_level/8)
        self._digest_bytesize = 2*self._security_level_in_bytes

    def get_decs_class(self):
        from smallwood.commit.decs.shake import DECSWithShake
        return lambda **kwargs: DECSWithShake(security_level=self._security_level, **kwargs)

    def hash_challenge_opening_decs(self, binding, iop_responses, associated_rnd):
        import hashlib
        h = hashlib.shake_128()
        serializer = self.get_serializer()
        if binding:
            h.update(binding)
        for iop_response in iop_responses:
            h.update(serializer.serialize(iop_response))
        for rnd in associated_rnd:
            h.update(serializer.serialize(rnd))
        return h.digest(self._digest_bytesize)

    def xof_lvcs_opening(self, binding):
        import hashlib
        h = hashlib.shake_128()
        h.update(binding)
        serializer = self.get_serializer()
        return serializer.sample_from_xof(h, self.nb_queries*self.nb_rows)
    
class LayoutLVCSWithShake(LayoutLVCS):
    def __init__(self, security_level, **kwargs):
        self._security_level = security_level
        super().__init__(**kwargs)

    def get_lvcs_class(self):
        return lambda *args, **kwargs: LVCSWithShake(security_level=self._security_level, **kwargs)

    def xof_layout_lvcs_opening_flat(self, binding):
        import hashlib
        h = hashlib.shake_128()
        h.update(binding)
        serializer = self.get_serializer()
        return serializer.sample_from_xof(h, self.layout.get_iop_query_tot_size())
