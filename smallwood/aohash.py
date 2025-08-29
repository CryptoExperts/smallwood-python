from .smallwood import SmallWood
from utils.challenges import RLCChallengeType

class SmallWoodWithAOHash(SmallWood):
    def __init__(self, **kwargs):
        self._salt_size = kwargs.pop('salt_size')
        self._digest_size = kwargs.pop('digest_size')

        self._tree_nb_leaves = kwargs.pop('tree_nb_leaves')
        self._tree_arity = kwargs.pop('tree_arity')
        self._tree_truncated = kwargs.pop('tree_truncated')
        self._tree_compression_method = kwargs.pop('tree_compression_method')
        self._tree_is_expanded = kwargs.pop('tree_is_expanded', False)
        self._decs_nb_queries = kwargs.pop('decs_nb_queries')
        self._decs_eta = kwargs.pop('decs_eta')
        self._decs_pow_opening = kwargs.pop('decs_pow_opening', 0)
        self._decs_format_challenge = kwargs.pop('decs_format_challenge', RLCChallengeType.POWERS)
        self._decs_opening_challenge_size = kwargs.pop('decs_opening_challenge_size')


        self._hash_xof = kwargs.pop('hash_xof')
        assert self._hash_xof.get_capacity() == self._digest_size
        super().__init__(**kwargs)

    def get_layout_lvcs(self, layout):
        from smallwood.commit.merkle import MerkleTreeFactoryWithAOHash
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = self._tree_nb_leaves,
            arity = self._tree_arity,
            truncated = self._tree_truncated,
            compression_method = self._tree_compression_method,
            is_expanded = self._tree_is_expanded,
            output_size = self._digest_size,
        )
        from smallwood.commit.lvcs import LayoutLVCSWithAOHash
        return LayoutLVCSWithAOHash(
            layout = layout,
            tree_factory = tree_factory,
            decs_nb_queries = self._decs_nb_queries,
            decs_eta =self._decs_eta,
            decs_pow_opening = self._decs_pow_opening,
            decs_format_challenge = self._decs_format_challenge,
            field = self.field,
            decs_opening_challenge_size = self._decs_opening_challenge_size,
            commitment_size = self._digest_size,
            hash_xof = self._hash_xof,
            decs_hash_leaves = self._hash_xof,
        )
    
    def get_salt_size(self):
        return self._salt_size

    def sample_salt(self):
        field = self.field
        return [field.random_element() for _ in range(self.get_salt_size())]

    def xof_fpp_challenge(self, binding, gamma_size):
        return self._hash_xof(binding, output_size=gamma_size, label='XOF IOP')
    
    def hash_poly_commitment(self, binding):
        return self._hash_xof(binding, output_size=self._digest_size)
    
    def hash_piop_transcript(self, h_polys, piop_polys):
        transcript_piop = h_polys
        for poly in piop_polys:
            transcript_piop += poly
        return self._hash_xof(transcript_piop, output_size=self._digest_size)
    
    def xof_piop_opening(self, h_piop):
        return self._hash_xof(h_piop, output_size=self.nb_queries, label='XOF IOP')
    
    def get_hash_digest_size(self):
        return self._digest_size
