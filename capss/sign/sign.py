class PermutationSelector:
    def __init__(self, perm_cls, perm_state_size_key = 'state_size', **kwargs):
        self._perm_cls = perm_cls
        self._perm_state_size_key = perm_state_size_key
        self._perm_params = kwargs

    def get_permutation(self, state_size):
        return self._perm_cls({
            **{self._perm_state_size_key: state_size},
            **self._perm_params
        })

class CAPSSSignature:
    def __init__(self, **kwargs):
        # Permutation
        perm_selector = kwargs.pop('perm_selector')
        assert isinstance(perm_selector, PermutationSelector)
        self._perm_lst = {} # We keep the list of permutation for statistics

        def get_permutation(state_size):
            if state_size not in self._perm_lst:
                self._perm_lst[state_size] = perm_selector.get_permutation(state_size)
            return self._perm_lst[state_size]

        # PACS
        self._pacs_cls = kwargs.pop('pacs_cls')
        from capss.pacs import PermPreimagePACS
        assert issubclass(self._pacs_cls, PermPreimagePACS)
        pacs_params_raw = kwargs.pop('pacs_params')
        pacs_perm_state_size = pacs_params_raw.pop('state_size')
        self._pacs_params = {
            'perm': get_permutation(pacs_perm_state_size),
            **pacs_params_raw,
        }

        # 
        from capss.hash import TruncationCompressionFunction
        compression_fnc_cls = kwargs.pop('compression_fnc_cls', TruncationCompressionFunction)
        
        self._raw_sw_params = kwargs.pop('sw_params')
        self._raw_sw_params['layout_beta'] = self._raw_sw_params.get('layout_beta', 1)

        self._sw_params = {}
        from capss.hash import SpongeHashFunction, MultipleSpongeHashFunction
        xof_state_size = self._raw_sw_params.pop('xof_state_size')
        xof_capacity = self._raw_sw_params.pop('xof_capacity')
        if type(xof_state_size) in [list, tuple]:
            self._sw_params['hash_xof'] = MultipleSpongeHashFunction({
                state_size: SpongeHashFunction(get_permutation(state_size), capacity=xof_capacity)
                for state_size in xof_state_size
            })
        else:
            self._sw_params['hash_xof'] = SpongeHashFunction(get_permutation(xof_state_size), capacity=xof_capacity)
        self._sw_params['tree_compression_method'] = {
            arity: compression_fnc_cls(get_permutation(arity*xof_capacity))
            for arity in set(self._raw_sw_params['tree_arity'])
        }
        self._sw_params['tree_nb_leaves'] = 1
        for a in self._raw_sw_params['tree_arity']:
            self._sw_params['tree_nb_leaves'] *= a
        self._sw_params['digest_size'] = self._sw_params['hash_xof'].get_capacity()
        from math import ceil
        self._sw_params['salt_size'] = ceil(self._sw_params['hash_xof'].get_capacity()/2)
        for key, value in self._raw_sw_params.items():
            self._sw_params[key] = value

        try:
            # Test the given parameters
            self._blank_pacs = self._pacs_cls.blank(**self._pacs_params)
            sw_cls = self.get_smallwood_class()
            self._blank_sw = sw_cls(pacs=self._blank_pacs, **self._sw_params)
            self._public_key_size = len(self._blank_pacs.serialize(lambda x: x))
            self._secret_key_size = self._blank_pacs.get_secret_size()
        except Exception as error:
            raise ValueError('Invalid PACS params') from error

    @classmethod
    def get_smallwood_class(cls):
        #from smallwood import SmallWoodWithAOHash
        #return SmallWoodWithAOHash
        from r1cs.smallwood.smallwood import SmallWoodWithAOHash_R1CS
        return SmallWoodWithAOHash_R1CS
    
    def get_field(self):
        return self._blank_pacs.get_field()

    def get_public_key_size(self):
        return self._public_key_size
    
    def get_private_key_size(self):
        return self._secret_key_size
    
    def get_signature_size(self):
        return self._blank_sw.get_proof_size()
    
    def has_variable_signature_size(self):
        return self._blank_sw.has_variable_proof_size()

    def get_security(self):
        return self._blank_sw.get_security()

    def keygen(self):
        pacs, secret = self._pacs_cls.random(**self._pacs_params)
        public_key = pacs.serialize(lambda x: x)
        secret_key = public_key + secret
        return (public_key, secret_key)

    def sign(self, secret_key, message):
        public_key, secret = secret_key[:self._public_key_size], secret_key[self._public_key_size:]
        pacs = self._pacs_cls.deserialize(public_key, lambda x: x, **self._pacs_params)
        witness = pacs.secret_to_witness(secret)

        sw_cls = self.get_smallwood_class()
        sw = sw_cls(pacs=pacs, **self._sw_params)
        signature = sw.prove(witness, binding=message)
        return signature

    def verify(self, public_key, message, signature):
        pacs = self._pacs_cls.deserialize(public_key, lambda x: x, **self._pacs_params)
        sw_cls = self.get_smallwood_class()
        sw = sw_cls(pacs=pacs, **self._sw_params)
        return sw.verify(signature, binding=message)
