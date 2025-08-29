from enum import Enum
from utils import MultiDimArray

class RLCChallengeType(Enum):
    POWERS = 0
    UNIFORM = 1
    HYBRID = 2

def derive_rlc_challenge(field, nb_combinations, nb_coefficients, random_felt_fnc, format_challenge):
    rlc_chall = MultiDimArray((nb_combinations,nb_coefficients))

    if format_challenge == RLCChallengeType.POWERS:
        gamma = random_felt_fnc(nb_combinations)
        for k in range(nb_combinations):
            alea = gamma[k]
            aleas = [alea]
            for _ in range(1, nb_coefficients):
                aleas.append(aleas[-1]*alea)
            rlc_chall[k] = aleas

    elif format_challenge == RLCChallengeType.UNIFORM:
        gamma = random_felt_fnc(nb_combinations*nb_coefficients)
        for i in range(nb_combinations):
            rlc_chall[i] = gamma[i*nb_coefficients:(i+1)*nb_coefficients]

    elif format_challenge == RLCChallengeType.HYBRID:
        gamma = random_felt_fnc((nb_combinations+1)+(nb_combinations+1)*nb_combinations)
        mat_rnd = MultiDimArray((nb_combinations, nb_combinations+1))
        mat_powers = MultiDimArray((nb_combinations+1, nb_coefficients))
        for k in range(nb_combinations):
            for j in range(nb_combinations+1):
                mat_rnd[k][j] = gamma[k*(nb_combinations+1)+j]
        for k in range(nb_combinations+1):
            alea = gamma[nb_combinations*(nb_combinations+1)+k]
            mat_powers[k][0] = [field(1)]
            for j in range(1, nb_coefficients):
                mat_powers[k][j] = mat_powers[k][j-1]*alea
        for k in range(nb_combinations):
            for i in range(nb_coefficients):
                rlc_chall[k][i] = sum(mat_rnd[k][j]*mat_powers[j][i] for j in range(nb_combinations+1))

    else:
        raise ValueError(f'Unknown format: {format_challenge}')
    
    return rlc_chall

def get_rlc_bit_security(field, nb_combinations, nb_coefficients, format_challenge):
    from math import log2
    field_order =  field.order()

    if format_challenge == RLCChallengeType.POWERS:
        return nb_combinations*log2(field_order/nb_coefficients)

    elif format_challenge == RLCChallengeType.UNIFORM:
        return nb_combinations*log2(field_order)

    elif format_challenge == RLCChallengeType.HYBRID:
        return nb_combinations*log2(field_order) - log2(1+nb_coefficients**(nb_combinations+1)/field_order)

    else:
        raise ValueError(f'Unknown format: {format_challenge}')
    
