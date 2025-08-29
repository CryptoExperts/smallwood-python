from smallwood import SmallWoodWithAOHash

class SmallWoodWithAOHash_R1CS(SmallWoodWithAOHash):
    def recover_polynomial(self, high, degree, evals):
        from r1cs.utils.polynomial import LPolynomialUtils_R1CS
        field = self.field
        wit_support = self.get_witness_support()
        return LPolynomialUtils_R1CS.restore_from_relations(
            [(field(0), [wit_support[idx] for idx in range(self.pacs.get_nb_wit_cols())])] + evals,
            high, degree
        )
    
    def recover_polynomial2(self, high, degree, evals):
        from r1cs.utils.polynomial import LPolynomialUtils_R1CS
        return LPolynomialUtils_R1CS.restore(high, degree, evals)
    
    def get_layout_lvcs(self, layout):
        from r1cs.commit.merkle import MerkleTreeFactoryWithAOHash_R1CS
        tree_factory = MerkleTreeFactoryWithAOHash_R1CS(
            nb_leaves = self._tree_nb_leaves,
            arity = self._tree_arity,
            truncated = self._tree_truncated,
            compression_method = self._tree_compression_method,
            is_expanded = self._tree_is_expanded,
            output_size = self._digest_size,
        )

        from r1cs.commit.lvcs import LayoutLVCSWithAOHash_R1CS
        return LayoutLVCSWithAOHash_R1CS(
            layout = layout,
            tree_factory = tree_factory,
            decs_nb_queries = self._decs_nb_queries,
            decs_eta =self._decs_eta,
            decs_pow_opening = self._decs_pow_opening,
            decs_format_challenge = self._decs_format_challenge,
            field = self.field,
            decs_opening_challenge_size = self._decs_opening_challenge_size,
            commitment_size = self._digest_size,
            hash_xof = self._hash_xof,
            decs_hash_leaves = self._hash_xof,
        )
    