from smallwood.commit.decs import DECSWithAOHash

class DECSWithAOHash_R1CS(DECSWithAOHash):
    def recover_polynomial(self, high, degree, iop_queries, evals):
        from r1cs.utils.polynomial import LPolynomialUtils_R1CS
        return LPolynomialUtils_R1CS.restore(high, degree, [
            (eval_point, evals[i]) for i, eval_point in enumerate(iop_queries)
        ])

    def parse_challenge(self, challenge):
        nb_evals = self.nb_evals
        nb_queries = self.nb_queries
        opening_challenge_size = self.opening_challenge_size
        assert len(challenge) == opening_challenge_size

        def parse_challenge(challenge):
            open_columns = []
            for i, chal_value in enumerate(challenge):
                chal_value = int(chal_value)
                chal_value = chal_value % self.maxi_useful_per_chal_value[i]
                for _ in range(self.nb_queries_per_chal_value[i]):
                    v, chal_value = chal_value % nb_evals, chal_value // nb_evals
                    open_columns.append(v)
            assert len(open_columns) == nb_queries
            return open_columns

        from r1cs.r1cs import R1CS
        r1cs = R1CS.detect(challenge)
        if r1cs is None:
            return super().parse_challenge(challenge)

        ### WITH R1CS
        F = self.field

        ### Get Open Columns
        open_columns = r1cs.new_registers(
            (nb_queries,),
            hint_inputs=[challenge],
            hint=parse_challenge
        )

        ## Get additional bits
        def compute_additional_bits(x, ind):
            factor = int(x) // self.maxi_useful_per_chal_value[ind]
            bin_str = bin(factor)[2:].rjust(self.nb_additional_bits_per_chal_value[ind], '0')
            return list(map(F, map(int, bin_str[::-1])))
        additional_bits = []
        for ind in range(opening_challenge_size):
            additional_bits.append(r1cs.new_registers(
                self.nb_additional_bits_per_chal_value[ind],
                hint_inputs=[challenge[ind], ind],
                hint=compute_additional_bits
            ))

        # Test Unicity
        for i in range(nb_queries):
            for j in range(i+1, nb_queries):
                assert open_columns[i] != open_columns[j]

        ## Check Open Columns
        recomposed_number = [ F(0) for ind in range(opening_challenge_size) ]
        acc = [ F(1) for ind in range(self.opening_challenge_size) ]
        ind = 0
        current_nb_query = 0
        for i in range(nb_queries):
            recomposed_number[ind] += open_columns[i]*acc[ind]
            acc[ind] *= nb_evals
            current_nb_query += 1
            if current_nb_query == self.nb_queries_per_chal_value[ind]:
                ind += 1
                current_nb_query = 0

        for ind in range(opening_challenge_size):
            term = F(0)
            for i in range(self.nb_additional_bits_per_chal_value[ind]):
                additional_bits[ind][i].force_binary()
                term += additional_bits[ind][i] * (F(2)**i)
            assert term*acc[ind] + recomposed_number[ind] == challenge[ind]

        return open_columns
