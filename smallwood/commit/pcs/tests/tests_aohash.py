import unittest

class TestTensorBasedPCSWithAOHash(unittest.TestCase):
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
        decs_opening_challenge_size = 1
        return F, (hash_leaves, hash_merkle), decs_opening_challenge_size
    
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
        decs_opening_challenge_size = 2
        return F, (hash_leaves, hash_merkle), decs_opening_challenge_size
    
    def _test_one(self, setup):
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup

        from sage.all import PolynomialRing
        R = PolynomialRing(F, name='X')
        X = R.gen()

        degree = 13
        nb_polys = 4
        nb_queries = 2
        poly_col_size = 3
        beta = 3

        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )
        nb_dec_queries = 10
        decs_eta = 2

        from smallwood.commit.pcs.pcs_univariate import UnivariateTensorBasedPCSWithAOHash
        pcs = UnivariateTensorBasedPCSWithAOHash(
            degree = degree,
            poly_col_size = poly_col_size,
            nb_polys = nb_polys,
            nb_queries = nb_queries,
            beta = beta,

            commitment_size = hash_leaves.get_capacity(),
            hash_xof = hash_leaves,

            field = F,
            tree_factory = tree_factory,
            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            decs_hash_leaves = hash_leaves,
            decs_opening_challenge_size = decs_opening_challenge_size
        )

        # Data
        polynomials = []
        for _ in range(nb_polys):
            polynomials.append(
                R.random_element(degree=degree)
            )

        # Commit
        salt = [F.random_element()]
        com, state = pcs.commit(salt, polynomials)

        # Open
        challenge_rnd = [F.random_element()]
        iop_queries, aux = pcs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = pcs.open(state, iop_queries)

        for num_poly in range(nb_polys):
            for num_query in range(nb_queries):
                self.assertEqual(
                    polynomials[num_poly](iop_queries[num_query]), opened_values[num_query][num_poly],
                    f'Invalid opened polynomial evaluations ({num_poly})'
                )

        # Verify
        iop_query_ = pcs.recompute_random_opening(aux, binding=challenge_rnd)
        com_ = pcs.recompute_commitment(salt, iop_query_, opened_values, proof)
        self.assertTrue(com == com_)

    def _test_two(self, setup):
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup

        from sage.all import PolynomialRing
        nb_variables = 5
        R = PolynomialRing(F, [f'X{i}' for i in range(nb_variables)])
        Xs = R.gens()

        nb_common_vars = 3
        nb_multilinears = 3

        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )
        nb_dec_queries = 10
        decs_eta = 2

        from smallwood.commit.pcs.pcs_multilinear import MultilinearTensorBasedPCSWithAOHash
        pcs = MultilinearTensorBasedPCSWithAOHash(
            nb_variables = nb_variables,
            nb_common_vars = nb_common_vars,
            nb_multilinears = nb_multilinears,

            commitment_size = hash_leaves.get_capacity(),
            hash_xof = hash_leaves,

            field = F,
            tree_factory = tree_factory,
            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            decs_hash_leaves = hash_leaves,
            decs_opening_challenge_size = decs_opening_challenge_size
        )

        # Data
        from utils import MultilinearUtils
        tprod_mono = MultilinearUtils.tensor_product(F, Xs)
        multilinears = []
        for _ in range(nb_multilinears):
            multilinears.append(
                sum([F.random_element()*mono for mono in tprod_mono])
            )

        # Commit
        salt = [F.random_element()]
        com, state = pcs.commit(salt, multilinears)

        # Open
        challenge_rnd = [F.random_element()]
        iop_query, aux = pcs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = pcs.open(state, iop_query)

        for num_multilinear in range(nb_multilinears):
            self.assertEqual(
                multilinears[num_multilinear](*iop_query), opened_values[num_multilinear],
                f'Invalid opened multilinear evaluations ({num_multilinear})'
            )

        # Verify
        iop_query_ = pcs.recompute_random_opening(aux, binding=challenge_rnd)
        com_ = pcs.recompute_commitment(salt, iop_query_, opened_values, proof)
        self.assertTrue(com == com_)

    def _test_three(self, setup):
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup

        # Configure DEC Scheme
        from sage.all import PolynomialRing
        nb_variables = 5
        R = PolynomialRing(F, [f'X{i}' for i in range(nb_variables)])
        Xs = R.gens()

        nb_common_vars = 3
        nb_multilinears = 3
        uni_degree = 3
        nb_uni_queries = 2

        poly_col_size = uni_degree + 1 - nb_uni_queries
        beta = 2

        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )
        nb_dec_queries = 10
        decs_eta = 2

        from smallwood.commit.lvcs.layouts import MultiLayout
        from smallwood.commit.pcs.layouts import MultilinearLayout, MonoUnivariateLayout
        layout = MultiLayout([
            MultilinearLayout(
                nb_variables = nb_variables,
                nb_common_vars = nb_common_vars,
                nb_multilinears = nb_multilinears,
            ),
            MultiLayout([ 
                MonoUnivariateLayout(
                    degree = uni_degree,
                    poly_col_size = poly_col_size,
                    nb_queries = nb_uni_queries,
                    beta = beta,
                ) for _ in range(nb_variables)
            ])
        ])
        from smallwood.commit.lvcs.aohash import LayoutLVCSWithAOHash
        pcs = LayoutLVCSWithAOHash(
            layout = layout,

            commitment_size = hash_leaves.get_capacity(),
            hash_xof = hash_leaves,

            field = F,
            tree_factory = tree_factory,
            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            decs_hash_leaves = hash_leaves,
            decs_opening_challenge_size = decs_opening_challenge_size
        )

        # Data
        from utils import MultilinearUtils
        tprod_mono = MultilinearUtils.tensor_product(F, Xs)
        multilinears = []
        univariates = []
        for _ in range(nb_multilinears):
            multilinears.append(
                sum([F.random_element()*mono for mono in tprod_mono])
            )
        for num in range(nb_variables):
            univariates.append(
                PolynomialRing(R.base_ring(), R.gen(num)).random_element(degree=uni_degree)
            )

        # Commit
        salt = [F.random_element()]
        com, state = pcs.commit(salt, [multilinears, univariates])

        # Open
        challenge_rnd = [F.random_element()]
        iop_queries, aux = pcs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = pcs.open(state, iop_queries)

        for num_multilinear in range(nb_multilinears):
            self.assertEqual(
                multilinears[num_multilinear](*iop_queries[0]), opened_values[0][num_multilinear],
                f'Invalid opened multilinear evaluations ({num_multilinear})'
            )
        for num_univariate in range(nb_variables):
            for num_query in range(nb_uni_queries):
                self.assertEqual(
                    univariates[num_univariate](iop_queries[1][num_univariate][num_query]), opened_values[1][num_univariate][num_query],
                    f'Invalid opened univariate evaluations ({num_univariate}, {num_query})'
                )

        # Verify
        iop_query_ = pcs.recompute_random_opening(aux, binding=challenge_rnd)
        com_ = pcs.recompute_commitment(salt, iop_query_, opened_values, proof)
        self.assertTrue(com == com_)

    def _test_four(self, setup):
        F, (hash_leaves, hash_merkle), decs_opening_challenge_size = setup

        from sage.all import PolynomialRing
        nb_variables = 5
        R = PolynomialRing(F, [f'X{i}' for i in range(nb_variables)])
        Xs = R.gens()

        nb_common_vars = 2
        nb_multilinears = 1
        uni_degree = 3

        ignored_rows = [2]
        ignored_cols = [1, 5]
        from smallwood.commit.pcs.layouts import EvalMultilinearLayout
        layout = EvalMultilinearLayout(
            nb_variables = nb_variables,
            nb_common_vars = nb_common_vars,
            nb_multilinears = nb_multilinears,
            ignore_rows = ignored_rows,
            ignore_cols = ignored_cols,
        )

        from smallwood.commit.merkle.aohash import MerkleTreeFactoryWithAOHash
        tree_factory = MerkleTreeFactoryWithAOHash(
            nb_leaves = 16,
            arity = (4, 4),
            compression_method=hash_merkle,
            output_size = hash_leaves.get_capacity(),
            truncated = None,
            is_expanded = True,
        )
        nb_dec_queries = 10
        decs_eta = 2

        from smallwood.commit.lvcs.aohash import LayoutLVCSWithAOHash
        pcs = LayoutLVCSWithAOHash(
            layout = layout,

            commitment_size = hash_leaves.get_capacity(),
            hash_xof = hash_leaves,

            field = F,
            tree_factory = tree_factory,
            decs_nb_queries = nb_dec_queries,
            decs_eta = decs_eta,
            decs_hash_leaves = hash_leaves,
            decs_opening_challenge_size = decs_opening_challenge_size
        )

        # Data
        from utils import MultilinearUtils
        tprod_mono = MultilinearUtils.tensor_product(F, Xs)
        multilinears = []
        for _ in range(nb_multilinears):
            #multilinears.append(
            #    sum([F.random_element()*mono for mono in tprod_mono])
            #)
            hyp_evals = [F.random_element() for _ in range(2**nb_variables)]
            for i in ignored_rows:
                for j in range(2**(nb_variables-nb_common_vars)):
                    hyp_evals[i*2**(nb_variables-nb_common_vars)+j] = F(0)
            for i in range(2**nb_common_vars):
                for j in ignored_cols:
                    hyp_evals[i*2**(nb_variables-nb_common_vars)+j] = F(0)
            multilinears.append(
                MultilinearUtils.get_mle(R, nb_variables, hyp_evals)
            )

        # Commit
        salt = [F.random_element()]
        com, state = pcs.commit(salt, multilinears)

        # Open
        challenge_rnd = [F.random_element()]
        iop_query, aux = pcs.get_random_opening(binding=challenge_rnd)
        opened_values, proof = pcs.open(state, iop_query)

        for num_multilinear in range(nb_multilinears):
            self.assertEqual(
                multilinears[num_multilinear](*iop_query), opened_values[num_multilinear],
                f'Invalid opened multilinear evaluations ({num_multilinear})'
            )

        # Verify
        iop_query_ = pcs.recompute_random_opening(aux, binding=challenge_rnd)
        com_ = pcs.recompute_commitment(salt, iop_query_, opened_values, proof)
        self.assertTrue(com == com_)

    ################################################################################################

    def test_one_large_field(self):
        setup = self._test_setup_large_field()
        self._test_one(setup)

    def test_two_large_field(self):
        setup = self._test_setup_large_field()
        self._test_two(setup)

    def test_three_large_field(self):
        setup = self._test_setup_large_field()
        self._test_three(setup)

    def test_four_large_field(self):
        setup = self._test_setup_large_field()
        self._test_four(setup)

    ####

    def test_one_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_one(setup)

    def test_two_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_two(setup)

    def test_three_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_three(setup)

    def test_four_goldilocks(self):
        setup = self._test_setup_goldilocks()
        self._test_four(setup)
