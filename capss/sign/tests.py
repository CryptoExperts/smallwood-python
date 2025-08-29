import unittest

class TestCAPSSSignature(unittest.TestCase):
    def test_sig_griffin(self):
        from .instances import get_scheme
        scheme = get_scheme('euG3.default')

        field = scheme.get_field()
        msg = [field.random_element()]

        pk, sk = scheme.keygen()
        sig = scheme.sign(sk, msg)
        assert not scheme.has_variable_signature_size()
        assert len(sig) == scheme.get_signature_size()
        assert scheme.verify(pk, msg, sig)

    def test_sig_griffin_r1cs(self):
        from .instances import get_scheme
        scheme = get_scheme('euG3.default')
        field = scheme.get_field()
        message_size = 1

        from r1cs.r1cs import R1CS
        r1cs = R1CS(field)

        ### Build Verification R1CS Constraints
        assert not scheme.has_variable_signature_size()

        msg = r1cs.new_registers(message_size, 'msg')
        pk  = r1cs.new_registers(scheme.get_public_key_size(), 'pk')
        sig = r1cs.new_registers(scheme.get_signature_size(), 'sig')
        assert scheme.verify(pk, msg, sig)

        print(r1cs.get_info())
        print('nb_linear', r1cs.nb_linear_equations())
        print('nb_vars_used_only_once', r1cs.nb_variables_used_only_once())
        print('nb_useless_equations', r1cs.nb_usedless_equations())

        dependencies = r1cs.get_dependencies()
        print(f'nb_dep={len(dependencies)}')

        ### Testing
        msg = [field.random_element() for _ in range(message_size)]
        pk, sk = scheme.keygen()
        sig = scheme.sign(sk, msg)
        assert scheme.verify(pk, msg, sig)

        aux = {
            'msg': msg,
            'pk': pk,
            'sig': sig,
        }
        data = r1cs.resolve(aux)

        nb_false = 0
        nb_true = 0
        for num_eq, eq in enumerate(r1cs.equations):
            if eq.evaluate(data):
                nb_true += 1
            else:
                nb_false += 1
        print(f'nb_true={nb_true}')
        print(f'nb_false={nb_false}')
        self.assertTrue(nb_false == 0)
