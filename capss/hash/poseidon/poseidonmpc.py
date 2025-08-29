from sign.mpc_mul import MPCProtocolFromMultiplications
from math import ceil
from sage.all import *

class PoseidonMPCProtocol(MPCProtocolFromMultiplications):
    def __init__(self, config, *args, **kwargs):
        self.hash_oneway = config.hash_one_way
        self.perm = self.hash_oneway.get_permutation()
        self.nb_sboxes = (self.perm.t*self.perm.R_F + self.perm.R_P)
        super().__init__(config, *args, **kwargs)

    def get_witness_packed_size(self):
        pack_size = self.config.s
        return 2*ceil(self.nb_sboxes/pack_size)

    def get_nb_polynomial_constraints(self):
        pack_size = self.config.s
        return ceil(self.nb_sboxes/pack_size)

    def get_nb_linear_constraints(self):
        # Nb of gate inputs with are not the witness, plus the outputs
        return self.nb_sboxes-self.hash_oneway.capacity

    def get_polynomial_constraints(self, input_share, party_point, powers=None):
        pack_size = self.config.s
        half = ceil(self.nb_sboxes/pack_size)
        all_values = []
        for i in range(half):
            all_values.append(input_share[i]**self.perm.alpha - input_share[half+i])
        return all_values

    def get_linear_matrix(self, pk):
        pack_size = self.config.s
        t = self.perm.t
        nb_linear_constraints = self.get_nb_linear_constraints()
        F = self.F
        R_f = self.perm.R_f
        R_P = self.perm.R_P
        A = zero_matrix(F, nb_linear_constraints, 2*pack_size*ceil(self.nb_sboxes/pack_size))

        half = pack_size*ceil(self.nb_sboxes/pack_size)
        sectorA_x = t
        sectorA_y = 0
        sectorB_x = t + (R_f-1)*t
        sectorB_y = 0 + (R_f-1)*t
        sectorC_x = t + (R_f-1)*t + R_P
        sectorC_y = 0 + (R_f-1)*t + R_P
        sectorD_x = half + 0
        sectorD_y = 0
        sectorE_x = half + 0 + (R_f-1)*t
        sectorE_y = 0 + (R_f-1)*t
        sectorF_x = half + 0 + R_f*t + R_P
        sectorF_y = 0 + (R_f-1)*t + R_P + t

        #### WARNING: I changed the definition of Poseidon! In the partial rounds, the sbox is now
        ### applied over the last state coordinate, instead of the first one!

        # Set coefficients for inputs
        for i in range(R_f-1):
            A[sectorA_y+i*t:sectorA_y+(i+1)*t,sectorA_x+i*t:sectorA_x+(i+1)*t] = -identity_matrix(F, t)
        for i in range(R_P):
            A[sectorB_y+i,sectorB_x+i] = -F(1)
        for i in range(R_f):
            A[sectorC_y+i*t:sectorC_y+(i+1)*t,sectorC_x+i*t:sectorC_x+(i+1)*t] = -identity_matrix(F, t)
        # Set coefficients for outputs
        for i in range(R_f):
            A[sectorD_y+i*t:sectorD_y+(i+1)*t,sectorD_x+i*t:sectorD_x+(i+1)*t] = self.perm.MDS_matrix
        for i in range(R_f-1):
            A[sectorF_y+i*t:sectorF_y+(i+1)*t,sectorF_x+i*t:sectorF_x+(i+1)*t] = self.perm.MDS_matrix
        A[sectorF_y+(R_f-1)*t:sectorF_y+(R_f)*t,sectorF_x+(R_f-1)*t:sectorF_x+(R_f)*t] = self.perm.MDS_matrix[self.hash_oneway.capacity:,:]

        a = self.perm.MDS_matrix[0,0]
        b = self.perm.MDS_matrix[0,1:]
        b_ = self.perm.MDS_matrix[1:,0]
        M_ = self.perm.MDS_matrix[1:,1:]
        PM = self.perm.MDS_matrix[:,:]
        for i in range(t):
            PM[i,0] = 0
        def vector_v(i):
            return ((PM**i) * self.perm.MDS_matrix)[0,:]
        def vector_v_bar(i):
            return (PM**(R_P-i-1)) * self.perm.MDS_matrix[:,0]
        def matrix_V():
            return ((PM**(R_P)) * self.perm.MDS_matrix)
        def gamma(i,j):
            return ((PM**(i-j)) * self.perm.MDS_matrix[:,0])[0,0]
        def rcum(i,complete=False):
            v = zero_vector(F, t)
            for j in range(i+1):
                r = vector(self.perm.round_constants[(R_f+j)*t:(R_f+j+1)*t])
                v += (PM**(i-j)) * r
            return v if complete else v[0]
        
        for i in range(R_P):
            A[sectorE_y+i:sectorE_y+(i+1),sectorE_x:sectorE_x+t] = vector_v(i)
        A[sectorE_y+R_P:sectorE_y+R_P+t,sectorE_x:sectorE_x+t] = matrix_V()
        for i in range(R_P):
            A[sectorE_y+R_P:sectorE_y+R_P+t,sectorE_x+t+i:sectorE_x+t+(i+1)] = vector_v_bar(i)
        for i in range(1, R_P):
            for j in range(1, i+1):
                A[sectorE_y+1+i-1,sectorE_x+t+j-1] = gamma(i,j)
        
        #vt = zero_vector(F, nb_linear_constraints)
        vt = [F(0)]*nb_linear_constraints
        for i in range(1,R_f):
            for j in range(t):
                vt[(i-1)*t + j] = -self.perm.round_constants[i*t+j]
        #vt[(R_f-1)*t+0] = -self.perm.round_constants[(R_f)*t+0]
        for i in range(R_P):
            vt[(R_f-1)*t+i] = -rcum(i)
        vt[(R_f-1)*t+R_P:(R_f-1)*t+R_P+t] = -rcum(R_P, complete=True)
        for i in range(1,R_f):
            for j in range(t):
                vt[(R_f-1)*t + R_P + i*t + j] = -self.perm.round_constants[t*(R_f+R_P+i)+j]
        vt[(R_f-1)*t + R_P + R_f*t: (R_f-1)*t + R_P + R_f*t+t-+self.hash_oneway.capacity]=pk
        return A, vt

    def extend_witness(self, wit):
        F = self.config.hash_one_way.get_field()
        pk=self.config.hash_one_way(wit, self.config.hash_one_way.rate)
        inter=self.config.hash_one_way.perm.get_last_input_output_sboxes()
        n = (len(inter) % self.config.s)
        n = self.config.s-n if n else 0
        col1 = [v for v, _ in inter] + [F(0)]*n
        col2 = [v for _, v in inter] + [F(0)]*n
        return col1+col2, pk
