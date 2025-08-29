from smallwood.pacs import AbstractPACS

class PermPreimagePACS(AbstractPACS):
    def __init__(self, perm, iv, y):
        self._perm = perm
        self._iv = iv
        self._y = y

    def get_field(self):
        return self._perm.get_field()

    @classmethod
    def random(cls, perm, iv_size, y_size, *args, **kwargs):
        F = perm.get_field()
        state_size = perm.get_state_size()

        iv = [
            F.random_element()
            for _ in range(iv_size)
        ]
        x = [
            F.random_element()
            for _ in range(state_size-iv_size)
        ]
        perm_output = perm(iv + x)
        y = perm_output[:y_size]
        return cls(perm, iv, y, *args, **kwargs), x

    @classmethod
    def blank(cls, perm, iv_size, y_size, *args, **kwargs):
        F = perm.get_field()
        iv = [F(0)]*iv_size
        y = [F(0)]*y_size
        return cls(perm, iv, y, *args, **kwargs)

    def get_secret_size(self):
        state_size = self._perm.get_state_size()
        iv_size = len(self._iv)
        return state_size-iv_size

    def secret_to_witness(self, secret):
        raise NotImplementedError()

    def serialize(self, fnc):
        data = self._iv + self._y
        return fnc(data)
    
    @classmethod
    def deserialize(cls, ser_data, fnc, perm, iv_size, y_size, *args, **kwargs):
        data = fnc(ser_data)
        iv, y = data[:iv_size], data[iv_size:]
        assert len(y) == y_size
        return cls(perm, iv, y, *args, **kwargs)
