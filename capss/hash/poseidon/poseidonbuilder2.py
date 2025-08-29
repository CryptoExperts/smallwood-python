from sage.all import *
from .poseidon import Poseidon

def build_poseidon_hash(data):
    F = FiniteField(data['prime'])
    security_level = data['security_level']
    alpha = data['alpha']
    t = data['t']
    R_F = data['R_F']
    R_P = data['R_P']
    round_constants = [
        F(int(data['round_constants'][i], 16))
        for i in range(0, (R_F + R_P) * t)
    ]
    MDS_matrix = matrix(F, t, t)
    for i in range(0, t):
        for j in range(0, t):
            MDS_matrix[i, j] = F(int(data['MDS_matrix'][i][j], 16))
    return Poseidon(F, alpha, t, security_level, R_F, R_P, round_constants, MDS_matrix)
