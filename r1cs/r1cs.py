from .variable import ElementaryVariable, Variable
from .hint import HintRegister

class Equation:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c
    
    def __str__(self):
        return f'({str(self.a)})*({str(self.b)}) = {str(self.c)}'

    def evaluate(self, data):
        value_a = self.a.evaluate(data)
        value_b = self.b.evaluate(data)
        value_c = self.c.evaluate(data)
        return value_a*value_b == value_c

class R1CS:
    def __init__(self, field):
        self._field = field
        self.equations = []
        self.evars = []
        self.counter = 0
        self.hint_register = HintRegister()
        self._nb_primary_inputs = 0

    @property
    def field(self):
        return self._field

    def register_equation(self, a, b, c):
        assert isinstance(a, Variable)
        assert isinstance(b, Variable)
        assert isinstance(c, Variable)
        if False:
            # DEBUG
            import traceback
            mode = 'w' if len(self.equations) == 0 else 'a'
            with open('r1cs-constraints.log', mode) as _file:
                _file.write(f'\n\n==== CONSTRAINT {len(self.equations)} ====\n')
                _file.write('\n'.join(traceback.format_stack()[:-1]))
        #assert len(self.equations) != 567, self.equations[-1]
        self.equations.append(Equation(a,b,c))

    def new_register(self, label=None, hint_inputs=None, hint=None, is_primary=False):
        v = ElementaryVariable(self.field, id=self.counter, label=label, is_primary=is_primary)
        self.evars.append(v)
        self.counter += 1
        if is_primary:
            self._nb_primary_inputs += 1
        if hint is not None:
            assert hint_inputs is not None
            hint_ = lambda *args, **kwargs: [hint(*args, **kwargs)]
            self.hint_register.new_hint([v], hint_inputs, hint_)
        return Variable(self, v)

    def new_registers(self, nb_registers, label=None, hint_inputs=None, hint=None, is_primary=False):
        registers = []
        if type(nb_registers) not in [tuple, list]:
            nb_registers = (nb_registers,)

        def create_registers(nb_registers, label):
            if len(nb_registers) == 0:
                reg = ElementaryVariable(
                    self.field, id=self.counter, label=label, is_primary=is_primary
                )
                self.evars.append(reg)
                self.counter += 1
                if is_primary:
                    self._nb_primary_inputs += 1
                return reg
            
            regs = []
            for num in range(nb_registers[0]):
                label_reg = None
                if label is not None:
                    if type(label) in [tuple, list]:
                        label_reg = label[num]
                    else:
                        label_reg = label + f'_v{num}'
                regs.append(
                    create_registers(nb_registers[1:], label_reg)
                )
            return regs
        registers = create_registers(nb_registers, label)
        if hint is not None:
            assert hint_inputs is not None
            self.hint_register.new_hint(registers, hint_inputs, hint)

        from .hint import browse_data
        return browse_data(lambda v: Variable(self, v), registers)

    def __str__(self):
        print(f'NB VAR: {self.counter}')
        print(f'NB EQU: {len(self.equations)}')
        txt = ''
        for eq in self.equations:
            txt += f'{str(eq)}\n'
        return txt

    def get_nb_equations(self):
        return len(self.equations)

    def get_nb_variables(self):
        return self.counter
    
    def get_nb_primary_inputs(self):
        return self._nb_primary_inputs

    def get_info(self):
        return {
            'nb-variables': self.counter,
            'nb-equations': len(self.equations),
        }

    def nb_linear_equations(self):
        count = 0
        for eq in self.equations:
            if eq.a.is_constant():
                count += 1
            elif eq.b.is_constant():
                count += 1
        return count

    def nb_variables_used_only_once(self):
        count = {}
        for eq in self.equations:
            for idx in eq.a.terms:
                count[idx] = count.get(idx, 0) + 1
            for idx in eq.b.terms:
                count[idx] = count.get(idx, 0) + 1
            for idx in eq.c.terms:
                count[idx] = count.get(idx, 0) + 1    

        nb_vars_used_only_once = 0
        for key, counter in count.items():
            if counter == 1:
                nb_vars_used_only_once += 1
        return nb_vars_used_only_once

    def nb_usedless_equations(self):
        count = {}
        for i, eq in enumerate(self.equations):
            for idx in eq.a.terms:
                count[idx] = count.get(idx, 0) + 1
            for idx in eq.b.terms:
                count[idx] = count.get(idx, 0) + 1
            for idx in eq.c.terms:
                count[idx] = count.get(idx, 0) + 1    

        nb_useless_eqs = 0
        for i, eq in enumerate(self.equations):
            indexes = list(eq.c.terms.keys())
            if None in indexes:
                indexes.remove(None)
            if (len(indexes) == 1) and (count[indexes[0]] == 1):
                nb_useless_eqs += 1
                #print('USELESS', i, eq, indexes[0])
        return nb_useless_eqs

    def get_dependencies(self):
        flags = {i: False for i in range(self.counter)}
        for eq in self.equations:
            for var in [eq.a, eq.b, eq.c]:
                for evar in var.get_dependencies():
                    flags[evar.id] = True
        return [self.evars[evar_id] for evar_id, flag in flags.items() if flag]

    def resolve(self, labels, verbose=False):
        expanded_labels = {}
        def expand_label(key, value):
            expanded = {}
            if type(value) in [list, tuple]:
                for num, v in enumerate(value):
                    expanded = {**expanded, **expand_label(key + f'_v{num}', v)}
            else:
                expanded[key] = value
            return expanded
        for key, value in labels.items():
            expanded_labels = {**expanded_labels, **expand_label(key, value)}
        dependencies = self.get_dependencies()
        data = {}
        def resolve(evar):
            if evar.id in data:
                return
            elif evar.label in expanded_labels:
                data[evar.id] = expanded_labels[evar.label]
                if verbose:
                    print(f'{len(data)}/{self.counter}', end='\r')
                    import sys
                    sys.stdout.flush()
            else:
                num_hint = self.hint_register.get_num_hint(evar)
                if num_hint is None:
                    raise Exception(f'Impossible to resolve variable "{evar}": neither hint, nor label.')
                deps = self.hint_register.get_dependencies(num_hint)
                for dep in deps:
                    resolve(dep)
                hint_outputs, out_values = self.hint_register.evaluate_hint(num_hint, data)
                def assign(key, value):
                    if type(key) in [list, tuple]:
                        assert len(value) == len(key), (len(value), len(key))
                        for i in range(len(key)):
                            assign(key[i], value[i])
                    else:
                        data[key.id] = value
                        if verbose:
                            print(f'{len(data)}/{self.counter}', end='\r')
                            import sys
                            sys.stdout.flush()
                assign(hint_outputs, out_values)
        for dep in dependencies:
            resolve(dep)
        return data

    def evaluate(self, data, output_nb_true=False):
        nb_true = 0
        for eq in self.equations:
            if eq.evaluate(data) == False:
                if not output_nb_true:
                    return False
            else:
                nb_true += 1
        return nb_true if output_nb_true else True

    @classmethod
    def detect(cls, *args):
        r1cs = None
        for arg in args:
            if type(arg) in [list, tuple]:
                r1cs = cls.detect(*arg)
                if r1cs is not None:
                    return r1cs
            else:
                if isinstance(arg, Variable):
                    return arg.r1cs
        return None
