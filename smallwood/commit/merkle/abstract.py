class AbstractMerkleTreeFactory:
    def get_nb_leaves(self):
        raise NotImplementedError()
    
    def get_depth(self):
        raise NotImplementedError()

    def expand_tree(self, leaves):
        raise NotImplementedError()
    
    def get_root(self, tree):
        raise NotImplementedError()
    
    def get_nodes_at_depth(self, tree, depth):
        raise NotImplementedError()
    
    def require_sorted_indexes(self):
        raise NotImplementedError()

    def get_authentication_path(self, tree, opened_indexes):
        raise NotImplementedError()

    def get_authentication_path_size(self, opened_indexes):
        raise NotImplementedError()

    def get_authentication_path_max_size(self, nb_queries):
        raise NotImplementedError()
    
    def has_variable_auth_size(self):
        raise NotImplementedError()

    def get_root_from_authentication_path(self, opened_leaves, auth):
        raise NotImplementedError()
