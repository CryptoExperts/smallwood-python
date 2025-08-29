class Quantity:
    def __init__(self, lst, offset):
        self._lst = lst
        self._offset = offset

    def degree(self):
        return max(
            len(mono)
            for mono, x in self._lst
        )

    def __add__(self, other):
        if isinstance(other, Quantity):
            result = []
            lst1 = self._lst
            lst2 = other._lst
            i, j = 0, 0

            while i < len(lst1) and j < len(lst2):
                if lst1[i][0] < lst2[j][0]:
                    result.append(lst1[i])
                    i += 1
                elif lst1[i] > lst2[j]:
                    result.append(lst2[j])
                    j += 1
                else:
                    i += 1
                    j += 1
                    mono, x = lst1[i]
                    _, y = lst2[j]
                    result.append((mono, x+y))

            result.extend(lst1[i:])
            result.extend(lst2[j:])
            return Quantity(result, self._offset+other._offset)
        else:
            return Quantity(self._lst, self._offset+other)
    
    def __mul__(self, other):
        if isinstance(other, Quantity):
            result = []
            lst1 = self._lst
            lst2 = other._lst

            def verify(x):
                col_ = x[0][1]
                for _, col in x[1:]:
                    if col != col_:
                        return False
                return True

            for mono1, x1 in lst1:
                for mono2, x2 in lst2:
                    mono = sorted(mono1+mono2)
                    assert verify(mono)
                    result.append((mono, x1*x2))

            offset1 = self._offset
            offset2 = other._offset
            for mono2, x2 in lst2:
                result.append((mono2, offset1*x2))
            for mono1, x1 in lst1:
                result.append((mono1, x1*offset2))
            result.sort(key=lambda x: x[0])
            offset = offset1*offset2
            return Quantity(result, offset)
        else:
            return Quantity([
                (mono, x*other)
                for mono, x in self._lst
            ], self._offset*other)
        
    def __eq__(self, value):
        return Constraint(self-value)

class Variable(Quantity):
    def __init__(self, label):
        super().__init__([label], offset=0)

class Constraint:
    def __init__(self, qu):
        assert isinstance(qu, Quantity)
        self._qu = qu

    def degree(self):
        return self._qu.degree()
    