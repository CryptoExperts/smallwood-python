### ISIS Selection

instances = [
    'A256-3', 'A256-5', # Anemoi
    'G256-3', 'G256-5', # Griffin
    'P256-3', 'P256-5', # Poseidon
    'R256-3', 'R256-5', # RescuePrime
]
MESSAGE_SIZE = 1

DIRPATH = '.'
FILENAME_FIELD_PARAMETERS = f'{DIRPATH}/r1cs-field.txt'
FILENAME_R1CS_CONSTRAINTS = f'{DIRPATH}/r1cs-constraints.txt'
FILENAME_R1CS_PRIMARY_INPUTS = f'{DIRPATH}/r1cs-primary-inputs.txt'
FILENAME_R1CS_AUX_INPUTS = f'{DIRPATH}/r1cs-auxiliary-inputs.txt'

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('label', choices=instances, help='Instance label')
parser.add_argument('tradeoff', choices=['short', 'default', 'fast'], help='Trade-off')
arguments = parser.parse_args()
label = arguments.label
tradeoff = arguments.tradeoff

## Get the signature scheme
from capss.sign.instances import get_scheme
scheme = get_scheme(f'{label}.{tradeoff}.extended')
scheme_c = get_scheme(f'{label}.{tradeoff}.compressed')
from math import log2, ceil
bytes_per_felt = ceil(log2(scheme_c.get_field().order())/8)

print(f'Signature Scheme: {label}.{tradeoff}')
print(f'Security: {scheme.get_security()[0]:.1f} bits')
print(f'Size: {scheme.get_signature_size()} felt / {scheme_c.get_signature_size()*bytes_per_felt} bytes')
print()

### Build R1CS Constraints
from r1cs.r1cs import R1CS
r1cs = R1CS(scheme.get_field())
from utils.log import Log
Log.set_r1cs(r1cs)
Log.set_verbose(False)

print(f'Building R1CS system of the verification algorithm...')
from capss.sign.r1cs import build_r1cs_for_verification
build_r1cs_for_verification(scheme, MESSAGE_SIZE, r1cs=r1cs)
print(f'Nb R1CS variables: {r1cs.get_nb_variables()}')
print(f'Nb R1CS equations: {r1cs.get_nb_equations()}')
print()

print('Generating a signature...')
field = scheme.get_field()
msg = [field.random_element() for _ in range(MESSAGE_SIZE)]
pk, sk = scheme.keygen()
sig = scheme.sign(sk, msg)
assert scheme.verify(pk, msg, sig)
from capss.sign.r1cs import build_inputs
inputs = build_inputs(scheme, pk, msg, sig)

print('Deducing the R1CS variable assigment')
variables = r1cs.resolve(inputs, verbose=True)

print('Exporting data')
from capss.libiop.export_r1cs import export_field_params, export_r1cs
export_field_params(scheme.get_field().order(), FILENAME_FIELD_PARAMETERS, verbose=False)
export_r1cs(r1cs, FILENAME_R1CS_CONSTRAINTS)

from capss.libiop.export_r1cs import export_variables
export_variables(r1cs, [inputs],
    FILENAME_R1CS_PRIMARY_INPUTS, FILENAME_R1CS_AUX_INPUTS,
    precomputed_variables=[variables]
)
