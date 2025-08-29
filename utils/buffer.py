from .serializer import PLAIN_SERIALIZER

class Buffer:
    @classmethod
    def reads_multiple(cls, buffer, *sizes, serializer=PLAIN_SERIALIZER):
        
        def aux(buffer, size):
            if len(size) == 1:
                if len(buffer) < size[0]:
                    raise BufferError()
                serialized_size = serializer.get_serialized_size(size[0])
                return serializer.deserialize(
                    buffer[:serialized_size], size[0]
                ), buffer[serialized_size:]
            data = []
            for _ in range(size[0]):
                d, buffer = aux(buffer, size[1:])
                data.append(d)
            return data, buffer

        data = []
        for size in sizes:
            if type(size) not in [list, tuple]:
                size = (size,)
            d, buffer = aux(buffer, size)
            data.append(d)
        return data, buffer
        
    @classmethod
    def reads(cls, buffer, size, serializer=PLAIN_SERIALIZER):
        data, buffer = cls.reads_multiple(buffer, size, serializer=serializer)
        return data[0], buffer

    @classmethod
    def parses_multiples(cls, buffer, *sizes, serializer=PLAIN_SERIALIZER):
        data, buffer = cls.reads_multiple(buffer, *sizes, serializer=serializer)
        assert len(buffer) == 0
        return data

    @classmethod
    def parses(cls, buffer, size, serializer=PLAIN_SERIALIZER):
        data = cls.parses_multiples(buffer, size, serializer=serializer)
        return data[0]

    # @classmethod
    # def dumps(cls, *args):

    #     def aux(dat):
    #         if type(dat) not in [list, tuple]:
    #             return [dat]
            
    #         buffer = []
    #         for d in dat:
    #             buffer += aux(d)
    #         return buffer
    #     buffer = []
    #     for data in args:
    #         if type(data) not in [list, tuple]:
    #             buffer += [data]
    #         else:
    #             buffer += aux(data)
    #     return buffer


    @classmethod
    def dumps_multiple(cls, data, *sizes, serializer=PLAIN_SERIALIZER):

        def aux(data, size):
            assert len(size) > 0
            assert len(data) == size[0]
            assert size[0] > 0

            if len(size) == 1:
                return serializer.serialize(data)
            else:                
                buffer = aux(data[0], size[1:])
                for i in range(1, size[0]):
                    buffer += aux(data[i], size[1:])
                return buffer

        assert len(sizes) > 0
        assert len(data) == len(sizes)
        buffer = aux(data[0], sizes[0])
        for i in range(1, len(sizes)):
            buffer += aux(data[i], sizes[i])
        return buffer

    @classmethod
    def dumps(cls, data, size, serializer=PLAIN_SERIALIZER):
        return cls.dumps_multiple([data], size, serializer=serializer)
