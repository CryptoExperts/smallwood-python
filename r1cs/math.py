from sage.all import xgcd

def root(x, r):
    try:
        # R1CS
        return x.__root__(r)
    except AttributeError as e:
        p = x.parent().order()
        _, r_inv, _ = xgcd(r, p-1)
        r_inv = r_inv % (p-1)
        return x**r_inv

