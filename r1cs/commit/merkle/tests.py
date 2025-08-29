

import unittest

class TestMerkleWithAOHash_R1CS(unittest.TestCase):
    def test_one(self):
        from r1cs.commit.merkle import MerkleTreeFactoryWithAOHash_R1CS
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

        for truncated in [1, None]:
            nb_leaves = 9
            tree_factory = MerkleTreeFactoryWithAOHash_R1CS(
                nb_leaves = nb_leaves,
                arity = (3, 3),
                compression_method=hash_merkle,
                output_size = capacity,
                truncated = truncated,
                is_expanded = True,
            )

            from r1cs.r1cs import R1CS
            r1cs = R1CS(F)

            nb_opened = 1

            assert not tree_factory.has_variable_auth_size()
            auth = r1cs.new_registers(tree_factory.get_authentication_path_max_size(nb_opened), 'auth')
            opened_indexes = r1cs.new_registers(nb_opened, 'opened_indexes')
            opened_leaves = r1cs.new_registers((nb_opened,1), 'opened_leaves')
            root = tree_factory.get_root_from_authentication_path([
                (opened_indexes[num], opened_leaves[num])
                for num in range(nb_opened)
            ], auth)

            print(r1cs.get_info())
            print('nb_linear', r1cs.nb_linear_equations())
            print('nb_vars_used_only_once', r1cs.nb_variables_used_only_once())
            print('nb_useless_equations', r1cs.nb_usedless_equations())

            dependencies = r1cs.get_dependencies()
            print(f'nb_dep={len(dependencies)}')

            ### Testing
            leaves = []
            for _ in range(nb_leaves):
                leaves.append([F.random_element()])

            tree = tree_factory(leaves)
            root = tree.get_root()

            opened_indexes = [i for i in range(nb_opened)]
            auth = tree.get_authentication_path(opened_indexes)
            assert len(auth) == tree.get_authentication_path_size(opened_indexes)
            root_ = tree_factory.get_root_from_authentication_path([
                (idx, leaves[idx])
                for idx in opened_indexes
            ], auth)
            self.assertTrue(root == root_)

            aux = {
                'auth': auth,
                'opened_indexes': [F(idx) for idx in opened_indexes],
                'opened_leaves': [leaves[idx] for idx in opened_indexes]
            }
            data = r1cs.resolve(aux)

            nb_false = 0
            nb_true = 0
            for num_eq, eq in enumerate(r1cs.equations):
                if eq.evaluate(data):
                    nb_true += 1
                else:
                    nb_false += 1
            print(f'nb_true={nb_true}')
            print(f'nb_false={nb_false}')
            self.assertTrue(nb_false == 0)
