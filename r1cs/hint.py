from .variable import ElementaryVariable, Variable

def browse_data(fnc, input_data):
    output_data = []
    for data in input_data:
        out = browse_data(fnc, data) if type(data) in [list, tuple] else fnc(data)
        output_data.append(out)
    return output_data

class Hint:
    def __init__(self, hint_outputs, hint_inputs, hint_fnc):
        self._hint_fnc = hint_fnc
        self._var_outputs = []
        self._dependencies = []

        # Check that the hint outputs are elementary variables
        def validator_hint_output(out):
            assert isinstance(out, ElementaryVariable)
            self._var_outputs.append(out)
            return out
        self._hint_outputs = browse_data(validator_hint_output, hint_outputs)

        # Compute dependencies
        already_includes = []
        def accumulate_dependencies(inp):
            if isinstance(inp, Variable):
                for evar in inp.get_dependencies():
                    if evar.id not in already_includes:
                        self._dependencies.append(evar)
                        already_includes.append(evar.id)
                return Variable(inp.r1cs, inp)
            return inp
        self._hint_inputs = browse_data(accumulate_dependencies, hint_inputs)
        
    @property
    def hint_outputs(self):
        return self._hint_outputs
    
    @property
    def hint_inputs(self):
        return self._hint_inputs
    
    @property
    def hint_fnc(self):
        return self._hint_fnc
    
    @property
    def var_outputs(self):
        return self._var_outputs

    @property
    def dependencies(self):
        return self._dependencies
    

class HintRegister:
    def __init__(self):
        self._hints = []
        self._by_evar = {}

    def new_hint(self, hint_outputs, hint_inputs, hint_fnc):
        num_hint = len(self._hints)
        #assert num_hint != 1256
        hint = Hint(hint_outputs, hint_inputs, hint_fnc)
        for evar in hint.var_outputs:
            assert evar.id not in self._by_evar
        self._hints.append(hint)
        for evar in hint.var_outputs:
            self._by_evar[evar.id] = num_hint

    def get_num_hint(self, evar):
        return self._by_evar.get(evar.id, None)

    def get_dependencies(self, num_hint):
        return self._hints[num_hint].dependencies

    def evaluate_hint(self, num_hint, data):
        hint = self._hints[num_hint]
        def evaluate_input(inputs_var):
            # We test if it is a variable, because it can
            #   be directly a field elements
            if isinstance(inputs_var, Variable):
                return inputs_var.evaluate(data)
            else:
                return inputs_var
        inputs = browse_data(evaluate_input, hint.hint_inputs)
        return hint.hint_outputs, hint.hint_fnc(*inputs)
