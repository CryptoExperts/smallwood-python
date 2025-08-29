
def check_perm_exponent(F, alpha):
    # Test that alpha is compatible with the field
    from r1cs.math import root
    r = root(F(2), alpha)
    b = r**alpha
    return b == F(2)

class Permutation:
    def __init__(self, field, state_size):
        self._field = field
        self._state_size = state_size
        self._nb_calls = 0

    def get_field(self):
        return self._field

    def get_state_size(self):
        return self._state_size
    
    def get_nb_calls(self):
        return self._nb_calls

    def _perm(self, input_state):
        raise NotImplementedError()

    def get_number_r1cs_constraints(self):
        raise NotImplementedError()

    def __call__(self, inputs):
        assert len(inputs) == self._state_size, 'The input has not the right size'
        self._nb_calls += 1
        return self._perm(inputs)
