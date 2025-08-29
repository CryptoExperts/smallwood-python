
from .sign import CAPSSSignature, PermutationSelector

# def get_signature_griffin_3_256bits():
#     from sage.all import FiniteField

#     # Get Hash Function
#     p = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f00000a7
#     alpha = 3
#     capacity = 1

#     from capss.hash.griffin import Griffin

#     # Configure DEC Scheme
#     decs_opening_challenge_size = 1

#     iv_size = 1
#     y_size = 1
#     from capss.pacs.pacs_reg_rounds import RegRoundsHashPACS

#     nb_dec_queries = 10
#     decs_eta = 2

#     perm_selector = PermutationSelector(
#         Griffin.get, state_size_key='t',
#         alpha = alpha, p=p,
#         capacity = capacity,
#         security_level = 128,
#     )
#     pacs_params = {
#         'state_size': 3,
#         'iv_size': iv_size,
#         'y_size': y_size,
#         'batching_factor': 4,
#     }
#     sw_params = {
#         'hash_xof_state_size': 4,
#         'hash_xof_capacity': 1,

#         'piop_nb_queries': 1,
#         'piop_rho': 1,

#         'tree_arity': [4]*6,
#         'tree_truncated': None,
#         'tree_is_expanded': True,

#         'decs_nb_queries': nb_dec_queries,
#         'decs_eta': decs_eta,
#         'decs_opening_challenge_size': decs_opening_challenge_size,
#     }

#     sig_scheme = CAPSSSignature(
#         perm_selector = perm_selector,
#         pacs_cls = RegRoundsHashPACS,
#         pacs_params = pacs_params,
#         sw_params = sw_params
#     )
#     return sig_scheme

class SchemeParsing:
    def __init__(self, label, data):
        self._label = label
        self._parameters = {}

        perm_selector = self.build_permutation_selector(data)
        (pacs_cls, pacs_params) = self.parse_pacs(data)
        sw_params = self.parse_smallwood_parameters(data)

        self._sig_scheme = CAPSSSignature(
            perm_selector = perm_selector,
            pacs_cls = pacs_cls,
            pacs_params = pacs_params,
            sw_params = sw_params
        )

    @property
    def label(self):
        return self._label
    
    @property
    def sig_scheme(self):
        return self._sig_scheme

    def check_fields(self, data, fields):
        for entry in fields:
            assert entry in data, f'{self.label} does not have the entry "{entry}"'

    def build_permutation_selector(self, data):
        self.check_fields(data, [
            'field', 'alpha', 'capacity', 'permutation_module', 'permutation'
        ])
        try:
            param_field = int(data['field'])
        except ValueError:
            param_field = int(data['field'], base=16)
        param_alpha = int(data['alpha'])
        param_capacity = int(data['capacity'])
        permutation_module_str = data['permutation_module']
        permutation_str = data['permutation']
        import importlib
        perm_mod = importlib.import_module(permutation_module_str)
        permutation_cls = getattr(perm_mod, permutation_str)
        class MyPermutationSelector(PermutationSelector):
            def __init__(self, perm_cls, alpha, field_order, capacity, security_level):
                self._perm_cls = perm_cls
                self._alpha = alpha
                self._field_order = field_order
                self._capacity = capacity
                self._security_level = security_level

            def get_permutation(self, state_size):
                return self._perm_cls.get(
                    self._field_order, self._alpha,
                    state_size, self._capacity,
                    self._security_level
                )
        perm_selector = MyPermutationSelector(
            permutation_cls,
            alpha = param_alpha, field_order = param_field,
            capacity = param_capacity,
            security_level = 128,
        )
        return perm_selector

    def parse_pacs(self, data):
        self.check_fields(data, ['pacs_module', 'pacs'])
        # Statement
        import importlib
        pacs_module_str = data['pacs_module']
        pacs_str = data['pacs']
        pacs_mod = importlib.import_module(pacs_module_str)
        pacs_cls = getattr(pacs_mod,  pacs_str)
        pacs_params = {key[11:]: eval(value) for key, value in data.items() if key[:11] == 'pacs_param_'}
        return pacs_cls, pacs_params

    def parse_smallwood_parameters(self, data):
        sw_keys = [
            'xof_state_size', 'piop_nb_queries', 'piop_rho',
            'tree_arity', 'tree_truncated', 'tree_is_expanded',
            'decs_nb_queries', 'decs_eta', 'decs_opening_challenge_size',
            'decs_pow_opening', 'capacity'
        ]
        self.check_fields(data, sw_keys)
        sw_params = {key: eval(data[key]) for key in sw_keys}
        sw_params['xof_capacity'] = sw_params.pop('capacity')
        if 'decs_format_challenge' in data:
            sw_params['decs_format_challenge'] = eval(data['decs_format_challenge'])
        if 'piop_format_challenge' in data:
            sw_params['piop_format_challenge'] = eval(data['piop_format_challenge'])
        return sw_params
    

def get_schemes(labels=None, filenames=None):
    if filenames is None:
        import os
        scheme_dirpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemes')
        filenames = [
            os.path.join(scheme_dirpath, filename)
            for filename in os.listdir(scheme_dirpath)
            if filename[-4:] == '.ini'
        ]

    if type(filenames) not in [tuple, list]:
        filenames = (filenames,)

    all_schemes = {}
    import configparser
    for filename in filenames:
        configfile = configparser.ConfigParser()
        configfile.read(filename)
        if labels is not None:
            if type(labels) not in [tuple, list]:
                labels = (labels,)

        sections = sorted(configfile.sections())

        all_data = {}
        for sec in sections:
            subdata = {}
            subsec = sec.split('.')
            for i in range(1, len(subsec)):
                sublabel = '.'.join(subsec[:i])
                if sublabel in all_data:
                    for key, value in all_data[sublabel].items():
                        subdata[key] = value
            for key, value in configfile[sec].items():
                subdata[key] = value
            all_data[sec] = subdata

        all_data = {
            key: value
            for key, value in all_data.items()
            if ('active' in value) and (value['active'] == 'yes')
        }

        for key, data in all_data.items():
            if labels is not None:
                if key not in labels:
                    continue
            parsing = SchemeParsing(key, data)
            all_schemes[key] = parsing.sig_scheme

    return all_schemes

def get_scheme(label, filenames=None):
    all_schemes = get_schemes(label, filenames)
    if len(all_schemes) == 0:
        raise ValueError(f'No scheme found for: {label}')
    elif len(all_schemes) > 1:
        raise ValueError(f'Multiple schemes found for: {label}')
    return list(all_schemes.values())[0]
