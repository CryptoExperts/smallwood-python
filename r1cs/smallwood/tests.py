import unittest

class TestSmallWoodCAPSS_R1CS(unittest.TestCase):
    def test_example_smallwood_aohash(self):
        from sage.all import FiniteField

        # Get Hash Function
        p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
        alpha = 3
        capacity = 1

        from capss.hash.griffin import Griffin
        from capss.hash import SpongeHashFunction, TruncationCompressionFunction
        perm = Griffin.get(p, alpha, 4, capacity, 128)
        hash_xof = SpongeHashFunction(perm, capacity=capacity)
        hash_merkle = {4: TruncationCompressionFunction(perm)}

        # Configure DEC Scheme
        F = FiniteField(p)
        decs_opening_challenge_size = 1
    
        iv_size = 1
        y_size = 1
        perm3 = Griffin.get(p, alpha, 3, capacity, 128)
        from capss.pacs.pacs_reg_rounds import RegRoundsHashPACS
        pacs, secret = RegRoundsHashPACS.random(perm3, iv_size, y_size, batching_factor=3)
        witness = pacs.secret_to_witness(secret)
        assert pacs.test_witness(witness) is True

        nb_dec_queries = 10
        decs_eta = 2

        digest_size = 1

        from .smallwood import SmallWoodWithAOHash_R1CS
        sw = SmallWoodWithAOHash_R1CS(
            pacs = pacs,

            salt_size = 1,
            digest_size = digest_size,
            hash_xof = hash_xof,

            tree_nb_leaves = 16,
            tree_arity = (4,4),
            tree_truncated = None,
            tree_compression_method = hash_merkle,
            tree_is_expanded = True,

            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            decs_opening_challenge_size = decs_opening_challenge_size,
            layout_beta = 2,

            piop_nb_queries = 1,
            piop_rho = 2,
        )

        from r1cs.r1cs import R1CS
        r1cs = R1CS(F)

        ### Build Verification R1CS Constraints
        assert not sw.has_variable_proof_size()
        proof = r1cs.new_registers(sw.get_proof_size(), 'proof')
        assert sw.verify(proof)

        print(r1cs.get_info())
        print('nb_linear', r1cs.nb_linear_equations())
        print('nb_vars_used_only_once', r1cs.nb_variables_used_only_once())
        print('nb_useless_equations', r1cs.nb_usedless_equations())

        dependencies = r1cs.get_dependencies()
        print(f'nb_dep={len(dependencies)}')

        ### Testing
        proof = sw.prove(witness)
        assert sw.verify(proof)
        
        aux = {
            'proof': proof,
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
