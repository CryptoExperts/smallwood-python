from .smallwood import SmallWood
from utils.challenges import RLCChallengeType

class SmallWoodWithShake(SmallWood):
    def __init__(self, security_level, **kwargs):
        self._security_level = security_level
        self._tree_nb_leaves = kwargs.pop('tree_nb_leaves')
        self._tree_arity = kwargs.pop('tree_arity')
        self._tree_truncated = kwargs.pop('tree_truncated')
        self._decs_nb_queries = kwargs.pop('decs_nb_queries')
        self._decs_eta = kwargs.pop('decs_eta')
        self._decs_pow_opening = kwargs.pop('decs_pow_opening', 0)
        self._decs_format_challenge = kwargs.pop('decs_format_challenge', RLCChallengeType.POWERS)

        super().__init__(**kwargs)

        from math import ceil
        self._security_level_in_bytes = ceil(security_level/8)
        self._digest_bytesize = 2*self._security_level_in_bytes

    def get_tree_factory_class(self):
        from smallwood.commit.merkle import MerkleTreeFactoryWithShake
        return MerkleTreeFactoryWithShake

    def get_layout_lvcs_class(self):
        from smallwood.commit.lvcs import LayoutLVCSWithShake
        return LayoutLVCSWithShake
    
    def get_layout_lvcs(self, layout):
        from smallwood.commit.merkle import MerkleTreeFactoryWithShake
        tree_factory = MerkleTreeFactoryWithShake(
            security_level = self._security_level,
            nb_leaves = self._tree_nb_leaves,
            arity = self._tree_arity,
            truncated = self._tree_truncated,
        )

        from smallwood.commit.lvcs import LayoutLVCSWithShake
        return LayoutLVCSWithShake(
            layout = layout,
            security_level = self._security_level,
            tree_factory = tree_factory,
            decs_nb_queries = self._decs_nb_queries,
            decs_eta =self._decs_eta,
            decs_pow_opening = self._decs_pow_opening,
            decs_format_challenge = self._decs_format_challenge,
            field = self.field,
        )
    
    def get_salt_size(self):
        return 16

    def sample_salt(self):
        import random
        return bytes([random.randint(0, 255) for _ in range(self.get_salt_size())])

    def xof_fpp_challenge(self, binding, gamma_size):
        import hashlib
        h = hashlib.shake_128()
        h.update(binding)
        serializer = self.get_serializer()
        return serializer.sample_from_xof(h, gamma_size)
    
    def hash_poly_commitment(self, binding):
        import hashlib
        h = hashlib.shake_128()
        serializer = self.get_serializer()
        h.update(serializer.serialize(binding))
        return h.digest(self._digest_bytesize)
    
    def hash_piop_transcript(self, h_polys, piop_polys):
        import hashlib
        h = hashlib.shake_128()
        h.update(h_polys)
        serializer = self.get_serializer()
        for poly in piop_polys:
            h.update(serializer.serialize(poly))
        return h.digest(self._digest_bytesize)
    
    def xof_piop_opening(self, h_piop):
        import hashlib
        h = hashlib.shake_128()
        h.update(h_piop)
        serializer = self.get_serializer()
        return serializer.sample_from_xof(h, self.nb_queries)

    def get_hash_digest_size(self):
        return self._digest_bytesize
