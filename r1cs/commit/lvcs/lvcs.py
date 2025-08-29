from smallwood.commit.lvcs import LVCSWithAOHash, LayoutLVCSWithAOHash
from utils import MultiDimArray

class LVCSWithAOHash_R1CS(LVCSWithAOHash):
    def get_decs_class(self):
        from r1cs.commit.decs import DECSWithAOHash_R1CS
        return lambda **kwargs: DECSWithAOHash_R1CS(
            commitment_size = self.commitment_size,
            hash_leaves = self.decs_hash_leaves,
            hash_xof = self.hash_xof,
            opening_challenge_size = self.decs_opening_challenge_size,
            **kwargs
        )

    def restore_dec_opened_values(self, v_, sub_dec_opened_values, iop_queries, fullrank_cols):
        coeffs_part1 = MultiDimArray((self.nb_queries, self.nb_queries))
        coeffs_part2 = MultiDimArray((self.nb_queries, self.nb_rows-self.nb_queries))
        for j in range(self.nb_queries):
            ind = 0
            for k in range(self.nb_rows):
                if ind < self.nb_queries and fullrank_cols[ind] == k:
                    coeffs_part1[j][ind] = iop_queries[j][k]
                    ind += 1
                else:
                    coeffs_part2[j][k-ind] = iop_queries[j][k]

        from sage.all import matrix
        import numpy as np

        from r1cs.r1cs import R1CS
        r1cs = R1CS.detect(coeffs_part1)
        if r1cs is None:
            coeffs_part1_inv = np.array(matrix(coeffs_part1).inverse())
        else:
            field = self.field
            def aux_inverse(mat):
                mat_inv = np.array(matrix(mat).inverse())
                return [[mat_inv[i,j] for j in range(self.nb_queries)] for i in range(self.nb_queries)]
            coeffs_part1_inv = r1cs.new_registers(
                (self.nb_queries, self.nb_queries),
                hint_inputs=[coeffs_part1],
                hint=aux_inverse
            )
            id_mat = np.array(coeffs_part1_inv).dot(np.array(coeffs_part1))
            for i in range(self.nb_queries):
                for j in range(self.nb_queries):
                    if i == j:
                        assert id_mat[i,j] == field(1)
                    else:
                        assert id_mat[i,j] == field(0)
            coeffs_part1_inv = np.array(coeffs_part1_inv)
        
        coeffs_part2 = np.array(coeffs_part2)

        dec_opened_values = MultiDimArray((self.decs.nb_queries, self.nb_rows))
        for j in range(self.decs.nb_queries):
            res = list(coeffs_part1_inv.dot((np.array(v_[j]) - coeffs_part2.dot(np.array(sub_dec_opened_values[j])))))
            ind = 0
            for k in range(self.nb_rows):
                if ind < self.nb_queries and fullrank_cols[ind] == k:
                    dec_opened_values[j][k] = res[ind]
                    ind += 1
                else:
                    dec_opened_values[j][k] = sub_dec_opened_values[j][k-ind]

        return dec_opened_values
    
class LayoutLVCSWithAOHash_R1CS(LayoutLVCSWithAOHash):
    def get_lvcs_class(self):
        return lambda **kwargs: LVCSWithAOHash_R1CS(
            commitment_size=self.commitment_size,
            hash_xof=self.hash_xof,
            decs_hash_leaves=self.decs_hash_leaves,
            decs_opening_challenge_size=self.decs_opening_challenge_size,
            **kwargs
        )
