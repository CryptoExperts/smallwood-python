


class Quantity:
    def is_parallel(self):
        raise NotImplementedError()
    
    def degree(self):
        raise NotImplementedError()
    
    def evaluate(self, data):
        raise NotImplementedError()
    
    def __add__(self, other):
        if isinstance(other, Quantity):
            return AdditionGate(self, other)
        else:
            return ScalarAdditionGate(self, other)
    __radd__ = __add__
    
    def __mul__(self, other):
        if isinstance(other, Quantity):
            return MultiplicationGate(self, other)
        else:
            return ScalarMultiplicationGate(self, other)
    __rmul__ = __mul__

    def __eq__(self, value):
        return Constraint(self-value)

class AdditionGate(Quantity):
    def __init__(self, a, b):
        assert a.is_parallel() == b.is_parallel()
        self._a = a
        self._b = b

    def is_parallel(self):
        return self._a.is_parallel()
    
    def degree(self):
        return max(self._a.degree(), self._b.degree())

    def evaluate(self, data):
        return self._a.evaluate(data) + self._b.evaluate(data)
    
class ScalarAdditionGate(Quantity):
    def __init__(self, a, sc):
        self._a = a
        self._sc = sc

    def is_parallel(self):
        return self._a.is_parallel()
    
    def degree(self):
        return self._a.degree()

    def evaluate(self, data):
        return self._a.evaluate(data) + self._sc

class MultiplicationGate(Quantity):
    def __init__(self, a, b):
        assert a.is_parallel() == b.is_parallel()
        self._a = a
        self._b = b

    def is_parallel(self):
        return self._a.is_parallel()

    def degree(self):
        return self._a.degree() + self._b.degree()

    def evaluate(self, data):
        return self._a.evaluate(data) * self._b.evaluate(data)

class ScalarMultiplicationGate(Quantity):
    def __init__(self, a, sc):
        self._a = a
        self._sc = sc

    def is_parallel(self):
        return self._a.is_parallel()

    def degree(self):
        return self._a.degree()

    def evaluate(self, data):
        return self._a.evaluate(data) * self._sc

class Variable(Quantity):
    def __init__(self, num_row, num_col=None):
        self._num_row = num_row
        self._num_col = num_col

    def is_parallel(self):
        return (self._num_col == None)

    def degree(self):
        return 1

    def evaluate(self, data):
        return data[(self._num_row,self._num_col)]

class Constraint:
    def __init__(self, qu):
        assert isinstance(qu, Quantity)
        self._qu = qu

    def degree(self):
        return self._qu.degree()
    
    def evaluate(self, data):
        return self._qu.evaluate(data)
