from .decs import DECS

class DECSWithAOHash(DECS):
    def __init__(self, **kwargs):
        commitment_size = kwargs.pop('commitment_size')
        hash_leaves = kwargs.pop('hash_leaves')
        hash_xof = kwargs.pop('hash_xof')
        assert hash_leaves.get_capacity() == commitment_size
        opening_challenge_size = kwargs.pop('opening_challenge_size', 1)

        super().__init__(**kwargs)

        self._commitment_size = commitment_size
        self._hash_leaves = hash_leaves
        self._hash_xof = hash_xof

        self._opening_challenge_size = opening_challenge_size

        # Parsing Opening challenge
        nb_evals = self.nb_evals
        nb_queries = self.nb_queries

        from math import floor, ceil, log2
        max_nb_queries_per_chal_value = ceil(nb_queries/opening_challenge_size)
        min_nb_queries_per_chal_value = floor(nb_queries/opening_challenge_size)
        assert nb_evals**max_nb_queries_per_chal_value <= self.field.order(), '"opening_challenge_size" seems too small.'
        nb_at_max = nb_queries % opening_challenge_size
        nb_queries_per_chal_value = [max_nb_queries_per_chal_value]*nb_at_max + [min_nb_queries_per_chal_value]*(opening_challenge_size-nb_at_max)
        assert sum(nb_queries_per_chal_value) == nb_queries
        
        nb_additional_bits_per_chal_value = [
            log2(self.field.order()) - nb_queries_per_chal_value[i]*log2(nb_evals)
            for i in range(opening_challenge_size)
        ]
        current_w = 0
        for i in range(opening_challenge_size):
            current_w += (nb_additional_bits_per_chal_value[i] - floor(nb_additional_bits_per_chal_value[i]))
            nb_additional_bits_per_chal_value[i] = floor(nb_additional_bits_per_chal_value[i])

        ind = 0
        while current_w < self.pow_opening:
            add_w = min(self.pow_opening-floor(current_w), nb_additional_bits_per_chal_value[ind])
            current_w += add_w
            nb_additional_bits_per_chal_value[ind] -= add_w
            ind += 1
            assert (current_w >= self.pow_opening) or (ind < opening_challenge_size), '"opening_challenge_size" seems too small.'
        self._concrete_pow_opening = current_w

        self._nb_queries_per_chal_value = nb_queries_per_chal_value
        self._nb_additional_bits_per_chal_value = nb_additional_bits_per_chal_value
        self._maxi_useful_per_chal_value = [
            nb_evals**nb_queries_per_chal_value[i]
            for i in range(opening_challenge_size)
        ]
        self._maxi_to_keep_per_chal_value = [
            self.maxi_useful_per_chal_value[i] * 2**nb_additional_bits_per_chal_value[i]
            for i in range(opening_challenge_size)
        ]

    @property
    def commitment_size(self):
        return self._commitment_size

    @property
    def hash_leaves(self):
        return self._hash_leaves

    @property
    def hash_merkle(self):
        return self._hash_merkle

    @property
    def hash_xof(self):
        return self._hash_xof

    @property
    def nb_queries_per_chal_value(self):
        return self._nb_queries_per_chal_value

    @property
    def nb_additional_bits_per_chal_value(self):
        return self._nb_additional_bits_per_chal_value

    @property
    def maxi_useful_per_chal_value(self):
        return self._maxi_useful_per_chal_value

    @property
    def maxi_to_keep_per_chal_value(self):
        return self._maxi_to_keep_per_chal_value

    @property
    def concrete_pow_opening(self):
        return self._concrete_pow_opening

    @property
    def opening_challenge_size(self):
        return self._opening_challenge_size

    def get_opening_aux_size(self):
        return 1
    
    def counter_to_aux(self, counter):
        return [counter]

    def get_evaluation_point(self, num_leaf):
        field = self.field
        return num_leaf + field(1)
    
    def get_num_leaf(self, query):
        field = self.field
        return query - field(1)
    
    def get_serializer(self):
        from utils.serializer import PLAIN_SERIALIZER
        return PLAIN_SERIALIZER

    def hash_leaf(self, num_leaf, salt, leaf_data):
        domain_separator = salt[:]
        domain_separator[-1] += num_leaf
        return self.hash_leaves(domain_separator + leaf_data, output_size=self.commitment_size)

    def hash_merkle_root(self, salt, root):
        return self.hash_xof(salt + root, output_size=self.commitment_size)

    def xof_decs_challenge(self, hash_mt, gamma_size):
        return self.hash_xof(hash_mt, output_size=gamma_size)

    def xof_decs_opening(self, nonce, binding):
        domain_separator = []
        chal = self.hash_xof(domain_separator + nonce + binding, output_size=self.opening_challenge_size, label='View Challenge')
        return self.parse_challenge(chal)
        
    def parse_challenge(self, challenge):
        nb_evals = self.nb_evals
        nb_queries = self.nb_queries
        opening_challenge_size = self.opening_challenge_size
        assert len(challenge) == opening_challenge_size

        def parse_challenge(challenge):
            open_columns = []
            for i, chal_value in enumerate(challenge):
                chal_value = int(chal_value)
                chal_value = chal_value % self.maxi_useful_per_chal_value[i]
                for _ in range(self.nb_queries_per_chal_value[i]):
                    v, chal_value = chal_value % nb_evals, chal_value // nb_evals
                    open_columns.append(v)
            assert len(open_columns) == nb_queries
            return open_columns

        for i in range(opening_challenge_size):
            if int(challenge[i]) >= self.maxi_to_keep_per_chal_value[i]:
                return None

        open_columns = parse_challenge(challenge)
        for i in range(nb_queries):
            for j in range(i+1, nb_queries):
                if open_columns[i] == open_columns[j]:
                    return None

        return open_columns
