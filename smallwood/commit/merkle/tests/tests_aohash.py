import unittest

def random_bytes(nb_bytes):
    import random
    return bytes([random.randint(0, 255) for _ in range(nb_bytes)])

class TestMerkleWithAOHash(unittest.TestCase):
    def test_one(self):
        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        from sage.all import FiniteField

        # Get Hash Function
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1

        from capss.hash.griffin import Griffin
        from capss.hash import JiveCompressionFunction
        perm = Griffin.get(p, alpha, 3, capacity, 128)
        hash_merkle = {3: JiveCompressionFunction(perm)}
        F = FiniteField(p)

        for truncated in [None, 1]:
            for is_expanded in [False, True]:
                nb_leaves = 9
                tree_factory = MerkleTreeFactoryWithAOHash(
                    nb_leaves = nb_leaves,
                    arity = (3, 3),
                    compression_method = hash_merkle,
                    output_size=capacity,
                    truncated = truncated,
                    is_expanded = is_expanded,
                )

                leaves = []
                for _ in range(nb_leaves):
                    leaves.append([F.random_element()])
                
                tree = tree_factory(leaves)
                root = tree.get_root()

                opened_indexes = [0, 1, 2, 3, 4]
                auth = tree.get_authentication_path(opened_indexes)
                assert len(auth) == tree.get_authentication_path_size(opened_indexes), (len(auth), tree.get_authentication_path_size(opened_indexes))

                root_ = tree_factory.get_root_from_authentication_path([
                    (idx, leaves[idx])
                    for idx in opened_indexes
                ], auth)
                self.assertTrue(root == root_)
