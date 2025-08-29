from .serializer import Serializer

class SerializerToBytes(Serializer):
    def __init__(self, field):
        self._field = field
        from math import log2, ceil
        self._bitsize_per_value = ceil(log2(field.order()))

    def get_serialized_size(self, vec_size):
        from math import ceil
        return ceil((vec_size*self._bitsize_per_value)/8)

    def serialize(self, vector):
        bits = []
        for v in vector:
            v = int(v)
            for _ in range(self._bitsize_per_value):
                v, r = (v // 2, v % 2)
                bits.append(r)
        pad_bitsize = (8-(len(bits) % 8))%8
        bits += [0]*pad_bitsize
        bytesize = len(bits) // 8
        def to_int_le(x):
            if len(x) == 1:
                return x[0]
            return x[0] + 2*to_int_le(x[1:])
        bytestr = bytes([to_int_le(bits[8*i:8*(i+1)]) for i in range(bytesize)])
        return bytestr
    
    def deserialize(self, bytestr, vec_size):
        bits = []
        for v in bytestr:
            for _ in range(8):
                v, r = (v // 2, v % 2)
                bits.append(r)
        def to_int_le(x):
            if len(x) == 1:
                return x[0]
            return x[0] + 2*to_int_le(x[1:])
        assert len(bits) >= self._bitsize_per_value*vec_size
        vector = [to_int_le(bits[self._bitsize_per_value*i:self._bitsize_per_value*(i+1)]) for i in range(vec_size)]
        for v in vector:
            assert v < self._field.order()
        vector = [self._field(v) for v in vector]
        return vector
    
    def sample_from_xof(self, state, vec_size):
        felt_bitsize = self._bitsize_per_value
        squeeze_size = vec_size*felt_bitsize
        while True:
            squeeze_size += vec_size*felt_bitsize
            from math import ceil
            bytestr = state.digest(ceil(squeeze_size//8))
            bits = []
            for v in bytestr:
                for _ in range(8):
                    v, r = (v // 2, v % 2)
                    bits.append(r)
            def to_int_le(x):
                if len(x) == 1:
                    return x[0]
                return x[0] + 2*to_int_le(x[1:])
            raw_vector = [to_int_le(bits[self._bitsize_per_value*i:self._bitsize_per_value*(i+1)]) for i in range(len(bits)//felt_bitsize)]
            vector = []
            for v in raw_vector:
                if v < self._field.order():
                    vector.append(self._field(v))
            if len(vector) >= vec_size:
                return vector[:vec_size]
