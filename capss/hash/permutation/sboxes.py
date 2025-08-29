from .permutation import Permutation
import enum

class Variable:
    def __init__(self, field, type, id):
        self._field = field
        self._type = type
        self._id = id

    @property
    def field(self):
        return self._field

    @property
    def type(self):
        return self._type
    
    @property
    def id(self):
        return self._id
    
    def is_input(self):
        return self._type == 0
    
    def __eq__(self, other):
        return (self.type == other.type) and (self.id == other.id)
    
    def __str__(self):
        return f'{self.type}<{self.id}>'
    
class AffineExpression:
    def __init__(self, lst, offset=None):
        if isinstance(lst, Variable):
            var = lst
            lst = [(var, var.field(1))]
        self._lst = lst
        if len(lst) > 0:
            self._field = lst[0][0].field
            self._offset = offset or lst[0][0].field(0)
        else:
            assert offset is not None
            self._field = offset.base_ring()
            self._offset = offset

    @property
    def field(self):
        return self._field
    
    def __mul__(self, scalar):
        return type(self)(
            [(var, factor*scalar) for (var, factor) in self._lst],
            offset = self._offset*scalar
        )
    
    def __rmul__(self, scalar):
        return type(self)(
            [(var, factor*scalar) for (var, factor) in self._lst],
            offset = self._offset*scalar
        )
    
    def __add__(self, other):
        if isinstance(other, type(self)):
            pos_self = 0
            pos_other = 0
            lst = []
            while pos_self < len(self._lst) or pos_other < len(other._lst):
                if pos_self == len(self._lst):
                    lst += other._lst[pos_other:]
                    pos_other = len(other._lst)
                elif pos_other == len(other._lst):
                    lst += self._lst[pos_self:]
                    pos_self = len(self._lst)
                else:
                    val_self = self._lst[pos_self]
                    val_other = other._lst[pos_other]
                    if val_self[0].type == val_other[0].type and val_self[0].id == val_other[0].id:
                        lst.append((val_self[0], val_self[1]+val_other[1]))
                        pos_self += 1
                        pos_other += 1
                    else:
                        select_self = (val_self[0].type < val_other[0].type)
                        select_self = select_self or (val_self[0].type == val_other[0].type and val_self[0].id < val_other[0].id)
                        if select_self:
                            lst.append(val_self)
                            pos_self += 1
                        else:
                            lst.append(val_other)
                            pos_other += 1
            return type(self)(
                lst, offset = self._offset + other._offset
            )
        else:
            return type(self)(
                self._lst, offset = self._offset + other
            )

    def is_constant(self):
        return len(self._lst) == 0
    
    def evaluate(self, inputs, sbox_outputs):
        return sum(
            factor*(inputs[var.id] if var.is_input() else sbox_outputs[var.id])
            for (var, factor) in self._lst
        ) + self._offset

    def __sub__(self, eq):
        return self + self.field(-1)*eq

    def __rsub__(self, eq):
        return self.field(-1)*self + eq

    def __truediv__(self, other):
        return self*(self.field(1)/other)


class SboxesPermutation(Permutation):
    def __init__(self, field, state_size):
        super().__init__(field, state_size)

        # Intermediary State of the Last Permutation
        #self._last_input_output_sboxes = None

        self._compute_wiring = False

    def get_number_sboxes(self):
        raise NotImplementedError()

    def _sbox(self, v_in):
        raise NotImplementedError()
    
    def _sbox_inv(self, v_out):
        raise NotImplementedError()
    
    def compute_sbox(self, sbox_in):
        if self._compute_wiring:
            sbox_out = AffineExpression(Variable(sbox_in.field, 1, len(self._io_sboxes_for_wiring)))
            self._io_sboxes_for_wiring.append(sbox_in)
        else:
            sbox_out = self._sbox(sbox_in)
            #self._last_input_output_sboxes.append((sbox_in, sbox_out))
        return sbox_out

    def compute_sbox_inv(self, sbox_out):
        return self._sbox_inv(sbox_out)

    def get_sbox_witness_size(self):
        raise NotImplementedError()
    
    def compute_sbox_with_witness(self, sbox_in):
        raise NotImplementedError()

    def get_degree_of_sbox_verification_function(self):
        raise NotImplementedError()

    def run_sbox_verification_function(self, sbox_in, sbox_out, sbox_wit):
        raise NotImplementedError()

    #def get_io_sboxes_of_last_call(self):
    #    return self._last_input_output_sboxes

    def __call__(self, inputs):
        #self._last_input_output_sboxes = None
        return super().__call__(inputs)

    def get_wiring(self):
        state_size = self.get_state_size()
        field = self.get_field()

        self._compute_wiring = True
        self._io_sboxes_for_wiring = []
        inputs = [
            AffineExpression(Variable(field, 0, num))
            for num in range(state_size)
        ]
        outputs = self._perm(inputs)
        self._compute_wiring = False

        return self._io_sboxes_for_wiring, outputs
