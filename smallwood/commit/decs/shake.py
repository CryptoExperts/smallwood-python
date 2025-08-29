from .decs import DECS

class DECSWithShake(DECS):
    def __init__(self, security_level, **kwargs):
        super().__init__(**kwargs)
        from utils.serializer import SerializerToBytes
        self._serializer = SerializerToBytes(self.field)
        from math import ceil
        self._security_level_in_bytes = ceil(security_level/8)
        self._digest_bytesize = 2*self._security_level_in_bytes

    def get_opening_aux_size(self):
        return 4
    
    def counter_to_aux(self, counter):
        nonce = b''
        for _ in range(4):
            (counter, r) = (counter // 256, counter % 256)
            nonce += bytes([r])
        return nonce

    def get_serializer(self):
        return self._serializer

    def hash_leaf(self, num_leaf, salt, leaf_data):
        serializer = self.get_serializer()
        import hashlib
        h = hashlib.shake_128()
        h.update(salt)
        h.update(bytes([num_leaf % 256, (num_leaf // 256)%256])) # over 2 bytes
        h.update(serializer.serialize(leaf_data))
        return h.digest(self._digest_bytesize)
    
    def hash_merkle_root(self, salt, root):
        import hashlib
        h = hashlib.shake_128()
        h.update(bytes([1]))
        h.update(root)
        return h.digest(self._digest_bytesize)
    
    def xof_decs_challenge(self, hash_mt, gamma_size):
        serializer = self.get_serializer()
        import hashlib
        h = hashlib.shake_128()
        h.update(hash_mt)
        return serializer.sample_from_xof(h, gamma_size)
    
    def xof_decs_opening(self, nonce, binding):
        import hashlib
        h = hashlib.shake_128()
        h.update(nonce)
        h.update(binding)
        
        from math import log2, ceil
        log2N = ceil(log2(self.nb_evals))
        assert self.nb_evals == 2**log2N
        data = h.digest(4*self.nb_queries+4)
        vpow = data[4*self.nb_queries:]
        vpow = vpow[0] + 256*vpow[1] + 256**2*vpow[2] + 256**3*vpow[3]
        vpow = vpow % (2**self.pow_opening)
        open_columns = [None]*self.nb_queries
        for i in range(self.nb_queries):
            open_columns[i] = data[4*i:4*(i+1)]
            open_columns[i] = open_columns[i][0] + 256*open_columns[i][1] + 256**2*open_columns[i][2] + 256**3*open_columns[i][3]
            open_columns[i] = open_columns[i] % self.nb_evals
    
        if vpow != 0:
            return None
        
        for i in range(self.nb_queries):
            for j in range(i+1, self.nb_queries):
                if open_columns[i] == open_columns[j]:
                    return None

        return open_columns
