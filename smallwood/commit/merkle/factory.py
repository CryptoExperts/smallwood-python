from .abstract import AbstractMerkleTreeFactory

def get_parent(child, arity):
    return (child-1)//arity

def get_first_sibling(node, arity):
    return node - ((node-1) % arity)


class MerkleTreeFactory(AbstractMerkleTreeFactory):
    def __init__(self, nb_leaves, arity, truncated=None):

        depth = len(arity)
        depth_width = [1]
        nb_maxi_leaves = 1
        for dp in range(depth):
            assert arity[dp]
            nb_maxi_leaves *= arity[dp]
            depth_width.append(nb_maxi_leaves)
        assert nb_leaves <= nb_maxi_leaves

        self._nb_leaves = nb_leaves
        self._arity = arity
        self._depth = depth
        self._depth_width = depth_width

        assert (truncated is None) or (truncated <= depth)
        self._truncated = truncated

    ###########################################
    ###        GETTERS

    def get_nb_leaves(self):
        return self._nb_leaves
    
    def get_depth(self):
        return self._depth
    
    def get_arity(self):
        return self._arity

    def get_truncated_factor(self):
        return self._truncated
    
    def get_depth_width(self):
        return self._depth_width

    ###########################################
    ###        SUB-ROUTINES

    def check_leaf(self, leaf):
        pass

    def get_digest_size(self):
        raise NotImplementedError()

    def get_null_digest(self):
        raise NotImplementedError()

    def run_compression(self, children):
        raise NotImplementedError()
    
    def get_null_auth(self):
        raise NotImplementedError()

    def extract_digest(self, auth):
        digest_size = self.get_digest_size()
        assert len(auth) >= digest_size
        return (auth[:digest_size], auth[digest_size:])
    
    ###########################################
    ###        MAIN ROUTINES

    def _expand_tree_generic(self, depth, leaves):
        depth_width = self.get_depth_width()
        assert len(leaves) <= depth_width[depth]
        null_digest = self.get_null_digest()
        arity = self.get_arity()

        tree = [None]*(depth+1)
        tree[depth] = [null_digest]*depth_width[depth]
        for i, leaf in enumerate(leaves):
            self.check_leaf(leaf)
            tree[depth][i] = leaf

        for dp in range(depth-1, -1, -1):
            tree[dp] = [None]*depth_width[dp]
            for num in range(depth_width[dp]):
                first_child_idx = num*arity[dp]
                children = tree[dp+1][first_child_idx:first_child_idx+arity[dp]]
                tree[dp][num] = self.run_compression(children)
        
        from .instance import MerkleTree
        return MerkleTree(self, tree)
    
    def expand_tree(self, leaves):
        depth = self.get_depth()
        return self._expand_tree_generic(depth, leaves)
    
    def expand_tree_from_depth(self, depth, nodes):
        depth_width = self.get_depth_width()
        assert len(nodes) == depth_width[depth]
        return self._expand_tree_generic(depth, nodes)

    __call__ = expand_tree

    def get_root(self, tree):
        return tree[0][0]

    def get_nodes_at_depth(self, tree, depth):
        return tree[depth]

    def require_sorted_indexes(self):
        return True

    def get_authentication_path(self, tree, opened_indexes):
        assert len(opened_indexes), 'The list of opened indexes should not be empty.'
        depth = self.get_depth()
        arity = self.get_arity()
        depth_width = self.get_depth_width()
        truncated = self.get_truncated_factor()
        auth = self.get_null_auth()

        # Check that it is sorted
        assert all(opened_indexes[i] <= opened_indexes[i+1] for i in range(len(opened_indexes) - 1))

        queue = [(depth, int(idx)) for idx in opened_indexes]
        # While the queue head does not corresponds to the root of the Merkle tree
        while (queue[0][0] != truncated) and (queue[0][0] != 0):
            # Get the first node in the queue
            dp, index = queue.pop(0)

            # Get the siblings and parent
            first_sibling = index - (index % arity[dp-1])
            next_first_sibling = first_sibling + arity[dp-1]
            parent = index // arity[dp-1]

            # Complete the authentication path
            for i in range(first_sibling, next_first_sibling):
                if i < index:
                    auth += tree[dp][i]
                elif len(queue) > 0 and (queue[0][0] == dp and index < queue[0][1] and queue[0][1] < next_first_sibling):
                    _, index = queue.pop(0)
                else:
                    index = next_first_sibling

            queue.append((dp-1, parent))

        if (truncated is not None) and (truncated > 0):
            nb_nodes_of_last_floor = depth_width[truncated]
            for num_final_node in range(nb_nodes_of_last_floor):
                if len(queue) > 0 and queue[0][1] == num_final_node:
                    queue.pop(0)
                else:
                    auth += tree[truncated][num_final_node]
            assert len(queue) == 0

        return auth


    def get_authentication_path_size(self, opened_indexes):
        depth = self.get_depth()
        arity = self.get_arity()
        depth_width = self.get_depth_width()
        truncated = self.get_truncated_factor()
        digest_size = self.get_digest_size()

        # Check that it is sorted
        assert all(opened_indexes[i] <= opened_indexes[i+1] for i in range(len(opened_indexes) - 1))

        auth_size = 0
        queue = [(depth, int(idx)) for idx in opened_indexes]
        # While the queue head does not corresponds to the root of the Merkle tree
        while (queue[0][0] != truncated) and (queue[0][0] != 0):
            # Get the first node in the queue
            dp, index = queue.pop(0)

            # Get the siblings and parent
            first_sibling = index - (index % arity[dp-1])
            next_first_sibling = first_sibling + arity[dp-1]
            parent = index // arity[dp-1]

            # Complete the authentication path
            for i in range(first_sibling, next_first_sibling):
                if i < index:
                    auth_size += digest_size
                elif len(queue) > 0 and (queue[0][0] == dp and index < queue[0][1] and queue[0][1] < next_first_sibling):
                    _, index = queue.pop(0)
                else:
                    index = next_first_sibling

            queue.append((dp-1, parent))

        if truncated is not None:
            nb_nodes_of_last_floor = depth_width[truncated]
            auth_size += (nb_nodes_of_last_floor - len(queue))*digest_size

        return auth_size
    
    def get_authentication_path_max_size(self, nb_queries):
        digest_size = self.get_digest_size()
        arity = self.get_arity()
        depth_width = self.get_depth_width()
        truncated = self.get_truncated_factor() or 0

        auth_path_size = 0
        for a in arity[truncated:]:
            auth_path_size += (a-1)*digest_size
        return (depth_width[truncated]-1)*digest_size + nb_queries*auth_path_size
    
    def has_variable_auth_size(self):
        return True

    def get_root_from_authentication_path(self, opened_leaves, auth):
        """ opened_leaves is a list of couple
                    (open_index, open_leaf)
        """
        depth = self.get_depth()
        arity = self.get_arity()
        depth_width = self.get_depth_width()
        truncated = self.get_truncated_factor()

        # Check that it is sorted
        assert all(opened_leaves[i][0] <= opened_leaves[i+1][0] for i in range(len(opened_leaves) - 1))

        queue = [(depth, int(idx), value[:]) for (idx,value) in opened_leaves]
        # While the queue head does not corresponds to the root of the Merkle tree
        while (queue[0][0] != truncated) and (queue[0][0] != 0):
            # Get the first node in the queue
            dp, index, value = queue.pop(0)

            # Get the siblings and parent
            first_sibling = index - (index % arity[dp-1])
            next_first_sibling = first_sibling + arity[dp-1]
            parent = index // arity[dp-1]

            # Complete the authentication path
            children = [None]*arity[dp-1]
            for i in range(first_sibling, next_first_sibling):
                if i < index:
                    children[i-first_sibling], auth = self.extract_digest(auth)
                elif len(queue) > 0 and (queue[0][0] == dp and index < queue[0][1] and queue[0][1] < next_first_sibling):
                    children[i-first_sibling] = value
                    _, index, value = queue.pop(0)
                else:
                    children[i-first_sibling] = value
                    index = next_first_sibling

            value_parent = self.run_compression(children)
            queue.append((dp-1, parent, value_parent))

        if (truncated is not None) and (truncated > 0):
            # Truncated
            nb_nodes_of_last_floor = depth_width[truncated]

            last_nodes = [None]*nb_nodes_of_last_floor
            for num_final_node in range(nb_nodes_of_last_floor):
                if len(queue) > 0 and queue[0][1] == num_final_node:
                    _, _, last_nodes[num_final_node] = queue.pop(0)
                else:
                    last_nodes[num_final_node], auth = self.extract_digest(auth)
            assert len(queue) == 0
            assert len(auth) == 0
            return self.expand_tree_from_depth(truncated, last_nodes).get_root()
        else:
            # Standard
            assert len(queue) == 1
            assert len(auth) == 0
            return queue[0][2]
