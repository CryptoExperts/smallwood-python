from math import ceil, log2
from .permutation import Permutation

class SpongeHashFunction:
    def __init__(self, perm, rate=None, capacity=None, lda=128, label=None, using_tweak_hir18=True, capacity_last=True):
        assert isinstance(perm, Permutation)
        self.perm = perm
        self.lda = lda
        self.label = label
        self.using_tweak_hir18 = using_tweak_hir18
        self.capacity_last = capacity_last
        if (rate is None) and (capacity is None):
            q = self.perm.get_field().order()
            self.capacity = ceil(2*lda / log2(q))
            self.rate = self.perm.get_state_size() - self.capacity
        elif (rate is not None) and (capacity is None):
            self.rate = rate
            self.capacity = self.perm.get_state_size() - rate
        elif (capacity is not None) and (rate is None):
            self.capacity = capacity
            self.rate = self.perm.get_state_size() - capacity
        else:
            assert capacity + rate == self.perm.get_state_size()
            self.capacity = capacity
            self.rate = rate

    def get_permutation(self):
        return self.perm

    def get_field(self):
        return self.perm.get_field()

    def get_rate(self):
        return self.rate

    def get_capacity(self):
        return self.capacity

    def get_number_r1cs_constraints(self, input_size, output_size):
        nb_input_blocks = ceil(input_size/self.rate)
        nb_output_blocks = ceil(output_size/self.rate)
        nb_perms = nb_input_blocks + nb_output_blocks - 1

        first_perm_input_size = input_size if (input_size <= self.rate) else self.rate
        block = [True]*self.capacity + [False]*first_perm_input_size + [True]*(self.rate-first_perm_input_size)

        total = (nb_perms-1)*self.perm.get_number_r1cs_constraints() + self.perm.get_number_r1cs_constraints(block)
        return total

    def __call__(self, inputs, output_size, label=None):
        assert len(inputs) > 0, 'Cannot hash the empty string'
        F = self.get_field()

        if (not self.using_tweak_hir18) or (len(inputs) % self.rate != 0): # Padding
            inputs = inputs + [1] + [0]*(self.rate-(len(inputs)%self.rate)-1)
            offset_capacity = F(0)
        else:
            offset_capacity = F(1)
        n = len(inputs)
        nb_input_blocks = ceil(n/self.rate)
        nb_output_blocks = ceil(output_size/self.rate)

        # Absorbing phase
        state = [F(0) for _ in range(self.rate + self.capacity)]
        for num_block in range(nb_input_blocks):
            block = inputs[num_block*self.rate:(num_block+1)*self.rate]
            assert len(block) == self.rate
            for i in range(self.rate):
                if self.capacity_last:
                    state[i] += block[i]
                else:
                    state[self.capacity + i] += block[i]
            if num_block == nb_input_blocks - 1: # Last Iteration
                if self.capacity_last:
                    state[-1] += offset_capacity
                else:
                    state[0] += offset_capacity
            state = self.perm(state)

        # Squeezing phase
        outputs = []
        filtered_state = state[:-self.capacity] if self.capacity_last else state[self.capacity:]
        outputs += filtered_state[:output_size-len(outputs)]
        for num_block in range(nb_output_blocks-1):
            state = self.perm(state)
            filtered_state = state[:-self.capacity] if self.capacity_last else state[self.capacity:]
            outputs += filtered_state[:output_size-len(outputs)]

        return outputs

class MultipleSpongeHashFunction:
    def __init__(self, perms, selector=None):
        assert len(perms) > 0
        for num, (key, perm) in enumerate(perms.items()):
            assert type(key) is int
            assert isinstance(perm, SpongeHashFunction)
            if num == 0:
                self._field = perm.get_field()
                self._capacity = perm.get_capacity()
            else:
                assert perm.get_field() == self._field
                assert perm.get_capacity() == self._capacity

        self._perms = perms
        assert (selector is None) or callable(selector)

        all_perm_keys = sorted(perms.keys())
        def default_selector(input_size, output_size):
            size = max(input_size, output_size) + self._capacity
            for key in all_perm_keys:
                if size <= key:
                    return key
            return all_perm_keys[-1]
        self._selector = selector or default_selector

    def get_permutations(self):
        return self._perms

    def get_field(self):
        return self._field

    def get_capacity(self):
        return self._capacity

    def get_number_r1cs_constraints(self, input_size, output_size):
        perm = self._perms[self._selector(input_size, output_size)]
        return perm.get_number_r1cs_constraints(input_size, output_size)

    def __call__(self, inputs, output_size, label=None):
        perm = self._perms[self._selector(len(inputs), output_size)]
        return perm(inputs, output_size, label=label)
