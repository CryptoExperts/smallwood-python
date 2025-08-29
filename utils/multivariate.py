class MultilinearUtils:
    @classmethod
    def get_mle(cls, R, dim, hyp_evals, partial_eval_points=[]):
        if R is not None:
            F = R.base_ring()
            dim_R = len(R.gens())
        else:
            F = partial_eval_points[0].base_ring()
            dim_R = 0
        dim_add = len(partial_eval_points)
        assert dim_R + dim_add == dim
        # Source: https://risencrypto.github.io/Sumcheck/

        # Lagrange Basis
        Lw = []
        from sage.all import Integer
        for i in range(2**dim):
            b=Integer(i).digits(2, None, dim) # pad(ZZ(i).binary(),v)
            g = F(1)

            for j in range(dim):
                xi = R.gen(j) if j < dim_R else partial_eval_points[j-dim_R]
                wi = b[dim-1-j]
                g = g* (xi * wi + (1-xi)*(1-wi))

            Lw.append(g)

        # MLE
        f = F(0)
        for i in range(2**dim):
            v = hyp_evals(i) if callable(hyp_evals) else hyp_evals[i]
            f = f + v*Lw[i]

        return f
    
    @classmethod
    def eval_hyp(cls, mle, eval_point):
        # Get MLE Dimension
        dim_mle = 0
        try:
            dim_mle = len(mle.degrees())
        except AttributeError:
            pass
        # GET Eval Point
        try:
            int(eval_point)
            from sage.all import Integer
            eval_point = Integer(eval_point).digits(2, None, dim_mle)[::-1] # pad(ZZ(i).binary(),v)
        except TypeError:
            pass

        return mle(*eval_point)
    
    @classmethod
    def tensor_product(cls, F, data):
        if len(data) == 0:
            return [F(1)]
        else:
            subdata = cls.tensor_product(F, data[1:])
            tprod = []
            for s in subdata:
                tprod.append(s)
                tprod.append(s*data[0])
            return tprod

    @classmethod
    def tensor_product_lagrange(cls, F, data):
        if len(data) == 0:
            return [F(1)]
        else:
            subdata = cls.tensor_product_lagrange(F, data[1:])
            tprod_2 = [s*data[0] for s in subdata] # s*data[0]
            tprod_1 = [s-tprod_2[i] for i, s in enumerate(subdata)] # s*(1-data[0])
            return tprod_1 + tprod_2


class MultivariatePolynomialUtils:
    @classmethod
    def to_univariate(cls, Runi, multi):
        if multi.degree() < 0:
            return Runi(0)
        assert multi.is_univariate()
        index = None
        for i, deg in enumerate(multi.degrees()):
            if deg > 0:
                index = i
                break
        if index is None:
            index = 0
        uni = Runi(0)
        pos = [0]*len(multi.parent().gens())
        for i in range(multi.degree()+1):
            pos[index] = i
            uni += multi[pos] * Runi.gen()**i
        return uni
