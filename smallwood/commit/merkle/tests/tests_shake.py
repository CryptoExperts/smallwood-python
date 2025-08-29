import unittest

def random_bytes(nb_bytes):
    import random
    return bytes([random.randint(0, 255) for _ in range(nb_bytes)])

class TestMerkleWithShake(unittest.TestCase):
    def test_one(self):
        from smallwood.commit.merkle.shake import MerkleTreeFactoryWithShake

        for truncated in [None, 1]:
            nb_leaves = 16
            tree_factory = MerkleTreeFactoryWithShake(
                security_level = 128,
                nb_leaves = nb_leaves,
                arity = (4, 4),
                truncated = truncated,
            )

            leaves = []
            for _ in range(nb_leaves):
                leaves.append(random_bytes(32))
            
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
