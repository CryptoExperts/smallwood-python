

from math import ceil
from .permutation import Permutation

class CompressionFunction:
    def __init__(self, perm):
        assert isinstance(perm, Permutation)
        self.perm = perm

    def get_permutation(self):
        return self.perm

    def get_field(self):
        return self.perm.get_field()

    def get_input_size(self):
        return self.perm.get_state_size()

    def get_number_r1cs_constraints(self, input_size, output_size):
        assert input_size == self.perm.get_state_size()
        return self.perm.get_number_r1cs_constraints()

    def __call__(self, inputs, output_size):
        raise NotImplementedError()


class TruncationCompressionFunction(CompressionFunction):
    def __call__(self, inputs, output_size):
        assert len(inputs) == self.perm.get_state_size()
        #if len(inputs) < self.perm.get_state_size():
        #    inputs += [self.perm.F(0)]*(self.perm.get_state_size()-len(inputs))
        assert output_size < len(inputs)
        perm_output = self.perm(inputs)
        output_with_feedforward = [
            perm_output[i] + inputs[i] # Feed-forward operation
            for i in range(self.perm.get_state_size())
        ]
        truncated_output = output_with_feedforward[:output_size]
        return truncated_output


class JiveCompressionFunction(CompressionFunction):
    def __call__(self, inputs, output_size):
        assert len(inputs) == self.perm.get_state_size()
        assert output_size < len(inputs)
        assert len(inputs) % output_size == 0
        arity = len(inputs) // output_size
        perm_output = self.perm(inputs)
        output_with_feedforward = [
            perm_output[i] + inputs[i] # Feed-forward operation
            for i in range(self.perm.get_state_size())
        ]
        compressed_output = output_with_feedforward[:output_size]
        for i in range(1, arity):
            for j in range(output_size):
                compressed_output[j] += output_with_feedforward[i*output_size+j]
        return compressed_output
    