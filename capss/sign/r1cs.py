from r1cs.r1cs import R1CS

def build_r1cs_for_verification(scheme, message_size=1, r1cs=None):
    assert not scheme.has_variable_signature_size()
    r1cs = r1cs or R1CS(scheme.get_field())
    msg = r1cs.new_registers(message_size, 'msg', is_primary=True)
    pk  = r1cs.new_registers(scheme.get_public_key_size(), 'pk', is_primary=True)
    sig = r1cs.new_registers(scheme.get_signature_size(), 'sig')
    _ = scheme.verify(pk, msg, sig) # Build R1CS constraints
    return r1cs

def build_primary_inputs(scheme, pk, message):
    assert (scheme is None) or (len(pk) == scheme.get_public_key_size())
    return {'pk': pk, 'msg': message}

def build_auxiliary_inputs(scheme, signature):
    assert (scheme is None) or (len(signature) == scheme.get_signature_size())
    return {'sig': signature}

def build_inputs(scheme, pk, message, signature):
    assert (scheme is None) or (len(pk) == scheme.get_public_key_size())
    assert (scheme is None) or (len(signature) == scheme.get_signature_size())
    return {'pk': pk, 'msg': message, 'sig': signature}
