

import unittest

class TestDECSWithAOHash_R1CS(unittest.TestCase):
    def _test_setup_large_field(self):
        from sage.all import FiniteField

        # Get Hash Function
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1

        from capss.hash.griffin import Griffin
        from capss.hash import SpongeHashFunction, TruncationCompressionFunction
        perm = Griffin.get(p, alpha, 4, capacity, 128)
        hash_leaves = SpongeHashFunction(perm, capacity=capacity)
        hash_merkle = {4: TruncationCompressionFunction(perm)}

        # Configure DEC Scheme
        F = FiniteField(p)
        dec_opening_challenge_size = 1
        return F, (hash_leaves, hash_merkle), dec_opening_challenge_size
    
    def _test_setup_goldilocks(self):
        from sage.all import FiniteField

        # Get Hash Function
        p = 0xffffffff00000001
        alpha = 7
        capacity = 4

        from capss.hash.griffin import Griffin
        from capss.hash import SpongeHashFunction, TruncationCompressionFunction
        perm = Griffin.get(p, alpha, 16, capacity, 128)
        hash_leaves = SpongeHashFunction(perm, capacity=capacity)
        hash_merkle = {4: TruncationCompressionFunction(perm)}

        # Configure DEC Scheme
        F = FiniteField(p)
        dec_opening_challenge_size = 2
        return F, (hash_leaves, hash_merkle), dec_opening_challenge_size

    def _test_r1cs(self, decs):
        from sage.all import PolynomialRing
        field = decs.field
        nb_polys = decs.nb_polys
        degree = decs.degree
        nb_queries = decs.nb_queries

        R = PolynomialRing(field, name='X')
        from utils import MultiDimArray

        from r1cs.r1cs import R1CS
        r1cs = R1CS(field)

        ### Build Verification R1CS Constraints
        salt = r1cs.new_registers(1, 'salt')
        iop_queries_ = r1cs.new_registers(nb_queries, f'iop_queries')
        opened_values = [
            r1cs.new_registers(nb_polys, f'opened_values_{j}')
            for j in range(nb_queries)
        ]
        assert not decs.has_variable_proof_size()
        proof = r1cs.new_registers(decs.get_proof_size(), 'proof')
        com = decs.recompute_commitment(salt, iop_queries_, opened_values, proof)

        print(r1cs.get_info())
        print('nb_linear', r1cs.nb_linear_equations())
        print('nb_vars_used_only_once', r1cs.nb_variables_used_only_once())
        print('nb_useless_equations', r1cs.nb_usedless_equations())

        dependencies = r1cs.get_dependencies()
        print(f'nb_dep={len(dependencies)}')

        ### Testing
        # Commit
        salt = [field.random_element()]
        polys = MultiDimArray((nb_polys,))
        for i in range(nb_polys):
            polys[i] = R.random_element(degree=degree)
        com, state = decs.commit(salt, polys)

        # Open
        challenge_rnd = [field.random_element()]
        iop_queries, aux = decs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = decs.open(state, iop_queries)

        # Verify
        iop_queries_ = decs.recompute_random_opening(aux, binding=challenge_rnd)
        
        aux = {
            'salt': salt,
            'proof': proof,
        }
        aux[f'iop_queries'] = iop_queries_
        for j in range(nb_queries):
            aux[f'opened_values_{j}'] = opened_values[j]
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

    def _test_aohash_expanded_r1cs(self, setup):
        from r1cs.commit.merkle import MerkleTreeFactoryWithAOHash_R1CS
        from r1cs.commit.decs import DECSWithAOHash_R1CS
        F, (hash_leaves, hash_merkle), dec_opening_challenge_size = setup
        nb_polys = 11
        degree = 30
        nb_queries = 5
        tree_factory = MerkleTreeFactoryWithAOHash_R1CS(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )

        decs = DECSWithAOHash_R1CS(
            field = F,
            nb_polys = nb_polys,
            degree = degree,
            tree_factory = tree_factory,
            nb_queries = nb_queries,
            eta = 2,

            commitment_size = hash_leaves.get_capacity(),
            hash_leaves = hash_leaves,
            hash_xof = hash_leaves,
            opening_challenge_size = dec_opening_challenge_size,
        )
        self._test_r1cs(decs)

    def test_aohash_expanded_r1cs_large_field(self):
        setup = self._test_setup_large_field()
        self._test_aohash_expanded_r1cs(setup)

    def test_aohash_expanded_r1cs_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_aohash_expanded_r1cs(setup)

