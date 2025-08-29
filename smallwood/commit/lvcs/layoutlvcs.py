

from utils import MultiDimArray, Buffer
from smallwood.commit.lvcs import LVCS
from utils.log.section import LogSection
from utils.challenges import RLCChallengeType

class LayoutLVCS:
    def __init__(self, **kwargs):
        self._field = kwargs.pop('field')
        self._layout = kwargs.pop('layout')

        row_length = self._layout.row_length
        nb_rows = self._layout.nb_rows
        nb_queries = self._layout.get_nb_lvcs_queries()

        tree_factory = kwargs.pop('tree_factory')
        decs_nb_queries = kwargs.pop('decs_nb_queries')
        decs_eta = kwargs.pop('decs_eta')
        decs_pow_opening = kwargs.pop('decs_pow_opening', 0)
        decs_format_challenge = kwargs.pop('decs_format_challenge', RLCChallengeType.POWERS)

        lvcs_class = self.get_lvcs_class()
        self._lvcs = lvcs_class(
            field = self.field,
            row_length = row_length,
            nb_rows = nb_rows,
            nb_queries = nb_queries,
            tree_factory = tree_factory,
            decs_nb_queries = decs_nb_queries,
            decs_eta = decs_eta,
            decs_pow_opening = decs_pow_opening,
            decs_format_challenge = decs_format_challenge,
            **kwargs
        )

    def get_lvcs_class(self):
        from smallwood.commit.lvcs import LVCS
        return LVCS

    @property
    def field(self):
        return self._field
    
    @property
    def layout(self):
        return self._layout
    
    @property
    def lvcs(self):
        return self._lvcs
    
    def get_security(self):
        return self.lvcs.get_security()
    
    def has_variable_proof_size(self):
        return self.lvcs.has_variable_proof_size()
    
    def get_proof_size(self, with_details=False):
        vec = self.get_serializer().get_serialized_size

        proof_size_d = {}
        lvcs_proof_size, lvcs_proof_size_d = self.lvcs.get_proof_size(with_details=True)
        proof_size_d['partial_evals'] = vec(self.layout.get_partial_evals_size())

        proof_size = sum(proof_size_d.values()) + lvcs_proof_size
        if with_details:
            proof_size_d['lvcs_proof'] = lvcs_proof_size_d
            return proof_size, proof_size_d
        else:
            return proof_size

    def get_averaged_proof_size(self, with_details=False):
        vec = self.get_serializer().get_serialized_size

        proof_size_d = {}
        lvcs_proof_size, lvcs_proof_size_d = self.lvcs.get_averaged_proof_size(with_details=True)
        proof_size_d['partial_evals'] = vec(self.layout.get_partial_evals_size())

        proof_size = sum(proof_size_d.values()) + lvcs_proof_size
        if with_details:
            proof_size_d['lvcs_proof'] = lvcs_proof_size_d
            return proof_size, proof_size_d
        else:
            return proof_size

    def commit(self, salt, inputs):
        rows = self.layout.to_rows(inputs)
        return self.lvcs.commit(salt, rows)

    def open(self, state, iop_query, binding=[]):
        layout = self.layout
        lvcs_iop_queries, fullrank_cols = layout.to_lvcs_queries(iop_query)
        (lvcs_iop_responses, lvcs_proof) = self.lvcs.open(state, lvcs_iop_queries, fullrank_cols, binding=binding)
        iop_responses, partial_evals = layout.to_iop_responses(iop_query, lvcs_iop_responses)

        proof  = self.build_partial_proof(partial_evals)
        proof += lvcs_proof
        return (iop_responses, proof)

    def recompute_commitment(self, salt, iop_query, iop_responses, proof, binding=[], is_standalone_proof=True):
        layout = self.layout

        with LogSection('Derive LVCS data'):
            lvcs_iop_queries, fullrank_cols = layout.to_lvcs_queries(iop_query)
            partial_evals, proof = self.parses_partial_proof(proof)
            lvcs_iop_responses = layout.to_lvcs_responses(iop_query, iop_responses, partial_evals)

        with LogSection('Recompute LVCS Commitment'):
            lvcs_proof = proof
            com, proof = self.lvcs.recompute_commitment(
                salt, lvcs_iop_queries, fullrank_cols, lvcs_iop_responses, lvcs_proof, binding=binding,
                is_standalone_proof=False,
            )
            if is_standalone_proof:
                assert len(proof) == 0
                return com
            else:
                return com, proof

    def verify(self, salt, commitment, iop_queries, iop_responses, proof, binding=[]):
        commitment_ = self.recompute_commitment(salt, iop_queries, iop_responses, proof, binding=binding)
        return commitment == commitment_

    def get_random_opening(self, binding=[]):
        digest = self.xof_layout_lvcs_opening_flat(binding)
        iop_query = self.layout.fieldstr_to_iop_query(digest)
        return (iop_query, [])

    def get_serializer(self):
        return self._lvcs.get_serializer()
    
    def recompute_random_opening(self, aux, binding=[]):
        assert len(aux) == 0
        return self.get_random_opening(binding=binding)[0]
    
    def build_partial_proof(self, partial_evals):
        serializer = self.get_serializer()
        return serializer.dumps(partial_evals, (self.layout.get_partial_evals_size(),))
    
    def parses_partial_proof(self, proof):
        serializer = self.get_serializer()
        partial_evals, proof = serializer.reads(proof, (self.layout.get_partial_evals_size(),))
        return partial_evals, proof
