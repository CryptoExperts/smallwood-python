class MerkleTree:
    def __init__(self, factory, tree):
        self._factory = factory
        self._tree = tree

    def get_root(self):
        return self._factory.get_root(self._tree)

    def get_nodes_at_depth(self, depth):
        return self._factory.get_nodes_at_depth(self._tree, depth)
    
    def require_sorted_indexes(self):
        return self._factory.require_sorted_indexes()

    def get_authentication_path(self, opened_indexes):
        return self._factory.get_authentication_path(self._tree, opened_indexes)

    def get_authentication_path_size(self, opened_indexes):
        return self._factory.get_authentication_path_size(opened_indexes)

    def get_authentication_path_max_size(self, nb_queries):
        return self._factory.get_authentication_path_max_size(nb_queries)

    def has_variable_auth_size(self):
        return self._factory.has_variable_auth_size()
    