class ElementaryVariable:
    def __init__(self, field, id, label=None, is_primary=False):
        self._field = field
        self._label = label
        self._id = id
        self._is_primary = is_primary

    @property
    def field(self):
        return self._field

    @property
    def label(self):
        return self._label
    
    @property
    def id(self):
        return self._id
    
    @property
    def is_primary(self):
        return self._is_primary

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        if self.label:
            return self.label
        return f'<{self.id}>'

    def __repr__(self):
        return self.__str__()


class Variable:
    def __init__(self, r1cs, objs, terms=None, terms_obj=None):
        self.r1cs = r1cs
        self.terms = {None: self.r1cs.field(0)}
        self.terms_obj = {}
        if terms is None:
            assert terms_obj is None
            if type(objs) is not list:
                objs = [objs]
            for obj in objs:
                if isinstance(obj, Variable):
                    for elt_id, factor in obj.terms.items():
                        if elt_id is None:
                            self._update_add_term(None, factor)
                        else:
                            self._update_add_term(obj.terms_obj[elt_id], factor)
                elif isinstance(obj, ElementaryVariable):
                    self._update_add_term(obj, obj.field(1))
                else:
                    self._update_add_term(None, obj)
        else:
            assert terms_obj is not None
            self.terms = terms.copy()
            self.terms_obj = terms_obj.copy()

    @property
    def field(self):
        return self.r1cs.field

    def base_ring(self):
        """ To be compliant with SageMath's field element """
        return self.r1cs.field

    def _update_add_term(self, elt, factor):
        if elt is not None:
            if elt.id in self.terms:
                self.terms[elt.id] += factor
                if self.terms[elt.id] == self.r1cs.field(0):
                    del self.terms[elt.id]
                    del self.terms_obj[elt.id]
            else:
                self.terms[elt.id] = factor
                self.terms_obj[elt.id] = elt
        else:
            self.terms[None] += factor

    def is_constant(self):
        return len(self.terms) == 1

    def get_constant(self):
        return self.terms[None]

    def _scale(self, factor):
        if factor == self.r1cs.field(0):
            self.terms = {None: self.r1cs.field(0)}
            self.terms_obj = {}
        else:
            for key in self.terms:
                self.terms[key] *= factor

    def __mul__(self, other):
        if isinstance(other, Variable):
            if self.is_constant():
                return self.get_constant()*other
            elif other.is_constant():
                return self*other.get_constant()
            else:
                output = self.r1cs.new_register(
                    hint_inputs=[self, other],
                    hint=(lambda x,y: x*y),
                )
                self.r1cs.register_equation(
                    self, other, output
                )
                return output
        else:
            res = Variable(self.r1cs, None,
                terms=self.terms,
                terms_obj=self.terms_obj
            )
            res._scale(other)
            return res

    def __truediv__(self, other):
        if isinstance(other, Variable):
            if self.is_constant():
                return self.get_constant()/other
            elif other.is_constant():
                return self/other.get_constant()
            else:
                output = self.r1cs.new_register(
                    hint_inputs=[self, other],
                    hint=(lambda x,y: x/y),
                )
                self.r1cs.register_equation(
                    other, output, self
                )
                return output
        else:
            res = Variable(self.r1cs, None,
                terms=self.terms,
                terms_obj=self.terms_obj
            )
            res._scale(1/other)
            return res

    def __rtruediv__(self, other):
        if isinstance(other, Variable):
            if self.is_constant():
                return other/self.get_constant()
            elif other.is_constant():
                return other.get_constant()/self
            else:
                output = self.r1cs.new_register(
                    hint_inputs=[self, other],
                    hint=(lambda x,y: y/x),
                )
                self.r1cs.register_equation(
                    self, output, other
                )
                return output
        else:
            output = self.r1cs.new_register(
                hint_inputs=[self, Variable(self.r1cs, other)],
                hint=(lambda x,y: y/x),
            )
            self.r1cs.register_equation(
                self, output, Variable(self.r1cs, other)
            )
            return output

    __rmul__ = __mul__

    def __add__(self, eq):
        if not isinstance(eq, Variable):
            eq = Variable(self.r1cs, eq)

        return Variable(self.r1cs, [self, eq])
    
    __radd__ = __add__

    def __sub__(self, eq):
        return self + self.r1cs.field(-1)*eq

    def __rsub__(self, eq):
        return self.r1cs.field(-1)*self + eq

    # def __pow__(self, power):
    #     if power < 0:
    #         raise ValueError('R1CS Variable does not support negative exponent.')

    #     if power == 0:
    #         return Variable(self.r1cs, self.r1cs.field(1))

    #     binary_power = list(map(int, bin(power)[2:]))[::-1]
    #     n = len(binary_power)

    #     powers = [self]
    #     for i in range(1,n):
    #         powers.append(powers[i-1]*powers[i-1])
    #     state = powers[-1]

    #     for i, b in enumerate(binary_power[:-1]):
    #         if b:
    #             state = state*powers[i]
    #     return state
    
    def __pow__(self, power):
        if power < 0:
            raise ValueError('R1CS Variable does not support negative exponent.')

        if power == 0:
            return Variable(self.r1cs, self.r1cs.field(1))

        try:
            self._cache_powers
        except AttributeError:
            self._cache_powers = {0: self.field(1), 1: self}

        binary_power = list(map(int, bin(power)[2:]))[::-1]
        n = len(binary_power)

        powers = [self]
        for i in range(1,n):
            if (1 << i) in self._cache_powers:
                powers.append(self._cache_powers[1<<i])
            else:
                powers.append(powers[i-1]*powers[i-1])
                self._cache_powers[1<<i] = powers[-1]
        state = powers[-1]

        current_exp = 1<<(n-1)
        for i, b in enumerate(binary_power[:-1]):
            if b:
                current_exp += (1<<i)
                if current_exp in self._cache_powers:
                    state = self._cache_powers[current_exp]
                else:
                    state = state*powers[i]
                    self._cache_powers[current_exp] = state
        return state

    def __root__(self, root):
        if root <= 0:
            raise ValueError('R1CS Variable does not support negative root.')

        from r1cs.math import root as get_root
        binary_root = list(map(int, bin(root)[2:]))[::-1]
        n = len(binary_root)

        output = self.r1cs.new_register(
            hint_inputs=[self],
            hint=(lambda x: get_root(x, root)),
        )
        powers = [output]
        for i in range(1,n):
            powers.append(powers[i-1]*powers[i-1])
        state = powers[-1]

        indexes = [i for i in range(n-1) if binary_root[i]]
        for j in range(len(indexes)-1):
            state = state*powers[indexes[j]]
        #assert state*powers[indexes[len(indexes)-1]] == self
        self.r1cs.register_equation(state,powers[indexes[len(indexes)-1]], self)
        return output
    
    def __str__(self):
        txt = ''
        for elt, factor in self.terms.items():
            if txt:
                txt += ' + '
            if factor == self.r1cs.field(1):
                txt += f'{str(self.terms_obj[elt])}' if elt is not None else '1'
            else:
                txt += f'{factor}*{str(self.terms_obj[elt])}' if elt is not None else f'{factor}'
        return txt

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        self.r1cs.register_equation(
            self, Variable(self.r1cs, self.r1cs.field(1)), Variable(self.r1cs, other)
        )
        return True

    def __ne__(self, other):
        diff = self - other
        inv_diff = self.r1cs.new_register(
            hint_inputs=[diff],
            hint=(lambda x: 1/x if x else x),
        )
        self.r1cs.register_equation(
            diff, inv_diff, Variable(self.r1cs, self.r1cs.field(1))
        )
        return True

    def force_binary(self):
        zero = Variable(self.r1cs, self.r1cs.field(0))
        one = Variable(self.r1cs, self.r1cs.field(1))
        self.r1cs.register_equation(
            self, self - one, zero
        )

    def get_dependencies(self):
        dep = []
        for elt, _ in self.terms.items():
            if elt is not None:
                dep.append(self.terms_obj[elt])
        return dep

    def evaluate(self, data):
        value = self.r1cs.field(0)
        for elt, factor in self.terms.items():
            if elt is None:
                value += factor
            elif elt not in data:
                raise Exception(f'Can not evaluate variable, unknown {self.terms_obj[elt]}')
            else:
                value += data[elt]*factor
        return value
