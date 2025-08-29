from .permutation import Permutation

class RegularIteratedPermutation(Permutation):
    def __init__(self, field, state_size, nb_rounds):
        self._nb_rounds = nb_rounds
        super().__init__(field, state_size)

        # Intermediary State of the Last Permutation
        self._last_internal_states = None

    def get_number_rounds(self):
        return self._nb_rounds

    def get_nb_constants_per_round(self):
        raise NotImplementedError()

    def get_round_constants(self, num_round):
        raise NotImplementedError()

    def run_round_permutation(self, state, round_constants):
        raise NotImplementedError()
    
    def get_round_witness_size(self):
        raise NotImplementedError()
    
    def run_round_permutation_with_witness(self, state, round_constants):
        raise NotImplementedError()
    
    def get_degree_of_round_verification_function(self):
        raise NotImplementedError()

    def run_round_verification_function(self, previous_state, new_state, witness, round_constants):
        raise NotImplementedError()

    def _perm(self, input_state):
        state = input_state

        for r in range(0, self.get_number_rounds()):
            round_constants = self.get_round_constants(r)
            state = self.run_round_permutation(state, round_constants)

        return state
