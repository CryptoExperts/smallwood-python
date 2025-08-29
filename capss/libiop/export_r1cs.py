from .field_params_generator import export_field_params

def get_permutation(r1cs):
    nb_variables = r1cs.get_nb_variables()
    nb_primary_inputs = r1cs.get_nb_primary_inputs()

    evars = sorted(r1cs.evars, key=lambda x:x.id)
    assert len(evars) == nb_variables, (len(evars), nb_variables)

    perm = {}
    inv_perm = {}
    primary_input_size = 0
    auxiliary_input_size = 0
    for evar in evars:
        if evar.is_primary:
            perm[evar.id] = primary_input_size
            inv_perm[primary_input_size] = evar.id
            primary_input_size += 1
        else:
            perm[evar.id] = nb_primary_inputs + auxiliary_input_size
            inv_perm[nb_primary_inputs + auxiliary_input_size] = evar.id
            auxiliary_input_size += 1
    assert primary_input_size == nb_primary_inputs
    return perm, inv_perm

def export_r1cs(r1cs, filename):
    nb_variables = r1cs.get_nb_variables()
    nb_primary_inputs = r1cs.get_nb_primary_inputs()
    equations = r1cs.equations

    perm, _ = get_permutation(r1cs)

    with open(filename, 'w') as _file:
        _file.write(f'{nb_primary_inputs} {nb_variables} {len(equations)} ')
        for _, eqn in enumerate(equations):
            (a, b, c) = (eqn.a, eqn.b, eqn.c)

            # A
            terms_a = [(elt_id, factor) for (elt_id, factor) in a.terms.items() if factor] 
            _file.write(f'{len(terms_a)} ')
            for (elt_id, factor) in terms_a:
                _file.write(f'{perm[elt_id]+1} ' if elt_id is not None else '0 ')
                _file.write(f'{factor} ')
            # B
            terms_b = [(elt_id, factor) for (elt_id, factor) in b.terms.items() if factor] 
            _file.write(f'{len(terms_b)} ')
            for (elt_id, factor) in terms_b:
                _file.write(f'{perm[elt_id]+1} ' if elt_id is not None else '0 ')
                _file.write(f'{factor} ')
            # A
            terms_c = [(elt_id, factor) for (elt_id, factor) in c.terms.items() if factor] 
            _file.write(f'{len(terms_c)} ')
            for (elt_id, factor) in terms_c:
                _file.write(f'{perm[elt_id]+1} ' if elt_id is not None else '0 ')
                _file.write(f'{factor} ')

def export_variables(r1cs, inputs, filename_primary, filename_aux, precomputed_variables=None):
    nb_batched = len(inputs)
    nb_variables = r1cs.get_nb_variables()
    nb_primary_inputs = r1cs.get_nb_primary_inputs()

    variables = []
    for num in range(nb_batched):
        if (precomputed_variables is None) or (precomputed_variables[num] is None):
            variables.append(r1cs.resolve(inputs[num], verbose=True))
        else:
            variables.append(precomputed_variables[num])
        assert r1cs.evaluate(variables[num])

    evars = sorted(r1cs.evars, key=lambda x:x.id)
    assert len(evars) == nb_variables, (len(evars), nb_variables)

    _, inv_perm = get_permutation(r1cs)

    with open(filename_primary, 'w') as _file:
        _file.write(f'{nb_batched} {nb_primary_inputs} ')
        for j in range(nb_batched):
            for i in range(nb_primary_inputs):
                idx = inv_perm[i]
                _file.write(f'{variables[j][idx]} ')
    with open(filename_aux, 'w') as _file:
        _file.write(f'{nb_batched} {nb_variables-nb_primary_inputs} ')
        for j in range(nb_batched):
            for i in range(nb_primary_inputs, nb_variables):
                idx = inv_perm[i]
                _file.write(f'{variables[j][idx]} ')
