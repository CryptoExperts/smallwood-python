from smallwood.commit.merkle import MerkleTreeFactoryWithAOHash
from r1cs.r1cs import R1CS
from sage.all import flatten

class BitDecomposition_R1CS:
    def decompose_value(value_to_decompose, arity, subdecomp):
        depth = len(arity)

        r1cs = R1CS.detect(value_to_decompose)
        if r1cs is None:
            def normal_decompose(v):
                v = int(v)
                decomposition = [None]*depth
                for d in range(depth-1, -1, -1):
                    value, v = v%arity[d], v//arity[d]
                    if subdecomp[d]:
                        decomposition[d] = [
                            (1 if value == j else 0)
                            for j in range(arity[d])
                        ]
                    else:
                        decomposition[d] = value
                return decomposition
            return normal_decompose(value_to_decompose)

        F = r1cs.field

        def aux_decompose(v):
            v = int(v)
            decomposition_open_index = [
                [None]*(a-1) if subdecomp[d] else None
                for d, a in enumerate(arity)
            ]
            for d in range(depth-1, -1, -1):
                value, v = v%arity[d], v//arity[d]
                # The first term of the decomposition (when value=0) can be deduced
                #   from the the others terms.
                if subdecomp[d]:
                    for j in range(1, arity[d]):
                        decomposition_open_index[d][j-1] = (F(1) if value == j else F(0))
                else:
                    decomposition_open_index[d] = value
            return flatten(decomposition_open_index)[:-1]

        size_decomposition_oindex = sum(((a-1) if subdecomp[d] else 1) for d, a in enumerate(arity))-1
        vectorialized_decomposition_ocolumn = r1cs.new_registers(
            size_decomposition_oindex,
            hint_inputs=[value_to_decompose],
            hint=aux_decompose
        )
        partial_decomposition = [None]*depth
        ind = 0
        for d in range(depth):
            if d < depth-1:
                if subdecomp[d]:
                    partial_decomposition[d] = [None] + vectorialized_decomposition_ocolumn[ind:ind+arity[d]-1]
                    ind += arity[d]-1
                    assert len(partial_decomposition[d]) == arity[d]
                else:
                    partial_decomposition[d] = vectorialized_decomposition_ocolumn[ind:ind+1]
                    ind += 1
            else:
                if subdecomp[d]:
                    partial_decomposition[d] = [None] + vectorialized_decomposition_ocolumn[ind:ind+arity[d]-2] + [None]
                    ind += arity[d]-2
                    assert len(partial_decomposition[d]) == arity[d]
                else:
                    partial_decomposition[d] = None
        assert len(vectorialized_decomposition_ocolumn[ind:]) == 0

        decomposition = [None]*depth
        value = F(0)
        # All the loop iterations
        for d in range(depth):
            if subdecomp[d]:
                local_value = F(0)
                decomposition[d] = [F(0)]*arity[d]
                for j in range(1, arity[d]):
                    if (d == depth-1) and (j == arity[d]-1):
                        b = (value_to_decompose - ((value*arity[d]) + local_value))*(1/F(j))
                    else:
                        b = partial_decomposition[d][j]
                    b.force_binary()
                    decomposition[d][j] = b
                    local_value += F(j)*b
                ## j=0, the bit b can be deduced from the other terms
                b = F(1) + (-1)*sum(decomposition[d])
                #local_value += F(0)*b
                b.force_binary()
                decomposition[d][0] = b
            else:
                if d == depth-1:
                    local_value = value_to_decompose - value*arity[d]
                else:
                    local_value = partial_decomposition[d]
                decomposition[d] = local_value
            value *= arity[d]
            value += local_value
        return decomposition


class BitSelection_R1CS:
    @staticmethod
    def assert_selection(selector, inputs, output):
        data_size = len(output)

        r1cs = R1CS.detect(selector, inputs, output)
        if r1cs is None:
            ### WITHOUT R1CS
            for k in range(len(selector)):
                for pos in range(data_size):
                    assert (inputs[k][pos]-output[pos])*selector[k] == 0
            return
            
        ### WITH R1CS
        F = r1cs.field
        lin_combination = [F(0)]*data_size
        for k in range(len(selector)):
            if k < len(selector)-1:
                for pos in range(data_size):
                    lin_combination[pos] += inputs[k][pos]*selector[k]
            else:
                for pos in range(data_size):
                    output[pos] -= lin_combination[pos]
                    r1cs.register_equation(inputs[k][pos], selector[k], output[pos])


class MerkleTreeFactoryWithAOHash_R1CS(MerkleTreeFactoryWithAOHash):
    def __init__(self, nb_leaves, arity, compression_method, output_size, truncated=None, is_expanded=False):
        super().__init__(nb_leaves, arity, compression_method, output_size, truncated, is_expanded)
        self._record = None

    def run_compression(self, children):
        if self._record is not None:
            self._record.append(flatten(children))
        return super().run_compression(children)

    def get_root_from_authentication_path(self, opened_leaves, auth):
        r1cs = R1CS.detect(opened_leaves, auth)
        if r1cs is None:
            return super().get_root_from_authentication_path(opened_leaves, auth)

        if (self.is_expanded is False) and (len(opened_leaves) == 1):
            open_index, open_leaf = opened_leaves[0]

            depth = self.get_depth()
            arity = self.get_arity()
            output_size = self.output_size

            decomposition = BitDecomposition_R1CS.decompose_value(open_index, arity, subdecomp=[True]*depth)

            ### Get Intermediary States of the Authentication Paths Checkings
            def compute_merkle_intermediary_nodes(opened_leaves, auth):
                self._record = []
                _ = self.get_root_from_authentication_path(opened_leaves, auth)
                merkle_intermediary_nodes = self._record
                self._record = None
                return flatten(merkle_intermediary_nodes)

            ### Check Intermediary States of the Authentication Paths Checkings
            size_vec_states = output_size*sum(arity[depth-1-j] for j in range(depth))
            vec_states = r1cs.new_registers(
                size_vec_states,
                hint_inputs=[opened_leaves, auth],
                hint=compute_merkle_intermediary_nodes
            )
            states = [None]*depth
            ind_state = 0
            for j in range(depth):
                states[j] = [
                    vec_states[ind_state+i*output_size:ind_state+(i+1)*output_size]
                    for i in range(arity[depth-1-j])
                ]
                ind_state += arity[depth-1-j]*output_size

            outputs = [None]*depth
            for j in range(depth):
                BitSelection_R1CS.assert_selection(decomposition[depth-1-j], states[j], (open_leaf if j == 0 else outputs[j-1]))
                outputs[j] = self.compression_function[arity[depth-1-j]](flatten(states[j]), output_size=output_size)
            root = outputs[depth-1]

            return root
        
        assert self.is_expanded is True
        return super().get_root_from_authentication_path(opened_leaves, auth)

    def check_subtree(self, root_preimages, open_index, open_leaf, auth):
        nb_root_preimages = len(root_preimages)
        nb_subtree_leaves = self.subtree_factory.get_nb_leaves()
        output_size = self.output_size

        if len(root_preimages) > 1:
            preimage_selector, sub_open_index = BitDecomposition_R1CS.decompose_value(open_index, [nb_root_preimages, nb_subtree_leaves], subdecomp=[True, False])
            preimage = self.subtree_factory.get_root_from_authentication_path([(sub_open_index, open_leaf)], auth)
            BitSelection_R1CS.assert_selection(preimage_selector, root_preimages, preimage)
        else:
            root_ = self.subtree_factory.get_root_from_authentication_path([(open_index, open_leaf)], auth)
            for pos in range(output_size):
                assert root_[pos] == root_preimages[0][pos]
        
        return True
