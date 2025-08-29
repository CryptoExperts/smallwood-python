from .factory import MerkleTreeFactory
import hashlib

class MerkleTreeFactoryWithShake(MerkleTreeFactory):
    def __init__(self, security_level, nb_leaves, arity, truncated=None):
        super().__init__(nb_leaves, arity, truncated)
        from math import ceil
        self._security_level_in_bytes = ceil(security_level/8)
        self._digest_bytesize = 2*self._security_level_in_bytes

    def check_leaf(self, leaf):
        super().check_leaf(leaf)
        assert type(leaf) is bytes
        assert len(leaf) == self._digest_bytesize

    def get_digest_size(self):
        return self._digest_bytesize
    
    def get_null_digest(self):
        return b'\x00'*(self._digest_bytesize)
    
    def run_compression(self, children):
        h = hashlib.shake_128() if self._security_level_in_bytes <= 16 else hashlib.shake_256()
        for child in children:
            h.update(child)
        return h.digest(self._digest_bytesize)

    def get_null_auth(self):
        return b''
