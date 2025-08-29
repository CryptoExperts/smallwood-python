class Serializer:
    def __init__(self, field):
        self._field = field

    @property
    def field(self):
        return self._field

    def get_serialized_size(self, vec_size):
        raise NotImplementedError()

    def serialize(self, vector):
        raise NotImplementedError()

    def deserialize(self, ser_vector, vec_size):
        raise NotImplementedError()

    def dumps(self, *args, **kwargs):
        from utils import Buffer
        return Buffer.dumps(
            *args, **kwargs, 
            serializer=self,
        )

    def reads(self, *args, **kwargs):
        from utils import Buffer
        return Buffer.reads(
            *args, **kwargs, 
            serializer=self,
        )
