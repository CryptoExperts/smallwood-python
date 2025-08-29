from .factory import MerkleTreeFactory

class MerkleTreeFactoryWithAOHash(MerkleTreeFactory):

    def __init__(self, nb_leaves, arity, compression_method, output_size, truncated=None, is_expanded=False):
        depth = len(arity)
        for dp in range(depth):
            assert arity[dp] in compression_method, f'key error {arity[dp]}'
            assert compression_method[arity[dp]].get_input_size() >= arity[dp]*output_size
        
        self.output_size = output_size
        self.compression_function = compression_method
        self.F = list(self.compression_function.values())[0].get_field()
        self.is_expanded = is_expanded

        super().__init__(nb_leaves, arity, truncated)

        if is_expanded:
            depth_width = self.get_depth_width()
            assert self.get_nb_leaves() == depth_width[-1] # Perfect tree
            truncated = truncated or 0
            nb_root_preimages = depth_width[truncated]
            nb_subtree_leaves = depth_width[-1] // nb_root_preimages
            self.subtree_factory = self.duplicate_with(
                nb_leaves=nb_subtree_leaves,
                arity=arity[truncated:],
                truncated=None,
                is_expanded=False,
            )

    def check_leaf(self, leaf):
        super().check_leaf(leaf)
        assert len(leaf) == self.output_size

    def get_digest_size(self):
        return self.output_size

    def get_null_digest(self):
        return [self.F(0)]*self.output_size
    
    def run_compression(self, children):
        arity = len(children)
        compr_fnc = self.compression_function[arity]
        from sage.all import flatten
        return compr_fnc(flatten(children), output_size=self.output_size)

    def get_null_auth(self):
        return []

    def require_sorted_indexes(self):
        return not self.is_expanded
    
    def get_authentication_path(self, tree, opened_indexes):
        if not self.is_expanded:
            return super().get_authentication_path(tree, opened_indexes)
        else:
            truncated = self.get_truncated_factor() or 0
            output_size = self.output_size
            from sage.all import flatten
            auth = flatten(self.get_nodes_at_depth(tree, truncated))
            for open_idx in opened_indexes:
                auth_j = super().get_authentication_path(tree, [open_idx])
                auth_j = auth_j[:self.subtree_factory.get_authentication_path_max_size(1)]
                auth += auth_j
            return auth
        
    def get_authentication_path_size(self, opened_indexes):
        if not self.is_expanded:
            return super().get_authentication_path_size(opened_indexes)
        else:
            return self.get_authentication_path_max_size(len(opened_indexes))
        
    def get_authentication_path_max_size(self, nb_queries):
        if not self.is_expanded:
            return super().get_authentication_path_max_size(nb_queries)
        else:
            digest_size = self.get_digest_size()
            depth_width = self.get_depth_width()
            truncated = self.get_truncated_factor() or 0
            
            auth_path_size = self.subtree_factory.get_authentication_path_max_size(1)
            return depth_width[truncated]*digest_size + nb_queries*auth_path_size
        
    def has_variable_auth_size(self):
        return not self.is_expanded

    def get_root_from_authentication_path(self, opened_leaves, auth):
        if not self.is_expanded:
            return super().get_root_from_authentication_path(opened_leaves, auth)
        
        else:
            depth_width = self.get_depth_width()
            truncated = self.get_truncated_factor() or 0
            nb_root_preimages = depth_width[truncated]

            # Check Root Preimages
            output_size = self.output_size
            root_preimages, auth = auth[:nb_root_preimages*output_size], auth[nb_root_preimages*output_size:]
            root_preimages = [root_preimages[i*output_size:(i+1)*output_size] for i in range(nb_root_preimages)]
            root = self.expand_tree_from_depth(truncated, root_preimages).get_root()

            # Check paths between leaves and root preimages
            auth_size = self.subtree_factory.get_authentication_path_max_size(1)
            for open_index, open_leaf in opened_leaves:
                cur_auth, auth = auth[:auth_size], auth[auth_size:]
                is_valid = self.check_subtree(root_preimages, open_index, open_leaf, cur_auth)
                if not is_valid:
                    return None
            
            assert len(auth) == 0
            return root
        
    def check_subtree(self, root_preimages, open_index, open_leaf, auth):
        nb_subtree_leaves = self.subtree_factory.get_nb_leaves()
        output_size = self.output_size
        open_index = int(open_index)
        (preimage_selector, sub_open_index) = (open_index // nb_subtree_leaves, open_index % nb_subtree_leaves)
        preimage = self.subtree_factory.get_root_from_authentication_path([(sub_open_index, open_leaf)], auth)
        for pos in range(output_size):
            if preimage[pos] != root_preimages[preimage_selector][pos]:
                return False
        return True

    def duplicate_with(self, nb_leaves, arity, truncated=None, is_expanded=False):
        return type(self)(
            nb_leaves = nb_leaves,
            arity = arity,
            compression_method = self.compression_function,
            output_size = self.output_size,
            truncated = truncated,
            is_expanded = is_expanded,
        )
