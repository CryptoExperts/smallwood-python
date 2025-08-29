def MultiDimArray(dims, init=None):
    if len(dims) == 1:
        return [init]*dims[0]
    return [MultiDimArray(dims[1:], init) for _ in range(dims[0])]

