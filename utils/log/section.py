
DATA = []
STATS = {
    'r1cs': {}
}
LOG_OPTIONS = {
    'verbose_section': True,
    'r1cs': None
}

class LogSection:
    def __init__(self, label):
        self._label = label

    def __enter__(self):
        if LOG_OPTIONS['verbose_section']:
            print('   '*len(DATA)+self._label)
        DATA.append({
            'label': self._label,
            'start_nb_equations': LOG_OPTIONS['r1cs'].get_nb_equations() if LOG_OPTIONS['r1cs'] is not None else None,
        })

    def __exit__(self, *args):
        abs_label = ''
        for d in DATA:
            abs_label += '/' + d['label']
        cur = DATA.pop()
        assert cur['label'] == self._label
        end_nb_equations = LOG_OPTIONS['r1cs'].get_nb_equations() if LOG_OPTIONS['r1cs'] is not None else None
        if LOG_OPTIONS['r1cs'] is not None:
            STATS['r1cs'][abs_label] = end_nb_equations - cur['start_nb_equations']

class Log:
    @staticmethod
    def reset():
        STATS['r1cs'] = {}

    @staticmethod
    def set_r1cs(r1cs):
        LOG_OPTIONS['r1cs'] = r1cs

    @staticmethod
    def unset_r1cs():
        LOG_OPTIONS['r1cs'] = None

    @staticmethod
    def get_statistics():
        return STATS

    @staticmethod
    def set_verbose(value):
        LOG_OPTIONS['verbose_section'] = value
