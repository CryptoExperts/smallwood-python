from .serializer import Serializer

class PlainSerializer(Serializer):
    def __init__(self, field=None):
        super().__init__(field)

    def get_serialized_size(self, vec_size):
        return vec_size
    
    def serialize(self, vector):
        return vector

    def deserialize(self, ser_vector, vec_size):
        assert len(ser_vector) == vec_size
        return ser_vector

PLAIN_SERIALIZER = PlainSerializer()

