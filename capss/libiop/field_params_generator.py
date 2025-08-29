# Adapted from https://github.com/scipr-lab/libff/blob/9769030a06b7ab933d6c064db120019decd359f1/libff/algebra/curves/params_generator.sage

from sage.all import *

def export_field_params(prime, filename, verbose=False):
    cprint = print if verbose else lambda *args: None

    with open(filename, 'w') as file:
        num_bits = ceil(log(prime, 2))
        cprint('num_bits = {}'.format(num_bits))
        file.write(f'{num_bits}\n')

        modulus = prime
        cprint('modulus = {}'.format(modulus))
        file.write(f'{modulus}\n')

        euler = (prime-1)/2
        cprint('euler = {}'.format(euler))
        file.write(f'{euler}\n')

        factorization = factor(prime-1)
        t = 0
        term_2 = factorization[0]
        counter = 0
        if term_2[0] != 2:
            raise BaseException("The prime decomposition doesn't have any factor 2."
            "The 'high 2-adicity' requirement isn't respected")
        while not(is_odd(t)):
            s = term_2[1] - counter
            t = (prime-1)/(2**s)
            counter = counter + 1
        cprint('s = {}'.format(s))
        file.write(f'{s}\n')
        assert is_odd(t)
        cprint('t = {}'.format(t))
        file.write(f'{t}\n')

        t_minus_1_over_2 = (t-1)/2
        cprint('t_minus_1_over_2 = {}'.format(t_minus_1_over_2))
        file.write(f'{t_minus_1_over_2}\n')

        multiplicative_generator = primitive_root(prime)
        cprint('multiplicative_generator = {}'.format(multiplicative_generator))
        file.write(f'{multiplicative_generator}\n')

        root_of_unity = pow(multiplicative_generator, t, prime)
        cprint('root_of_unity = {}'.format(root_of_unity))
        file.write(f'{root_of_unity}\n')

        nqr = least_quadratic_nonresidue(prime)
        cprint('nqr = {}'.format(nqr))
        file.write(f'{nqr}\n')

        nqr_to_t = pow(nqr, t, prime)
        cprint('nqr_to_t = {}'.format(nqr_to_t))
        file.write(f'{nqr_to_t}\n')

        word_len_64_bits = 64
        W_64_bits = 2**(word_len_64_bits)
        k_64_bits = ceil(num_bits/word_len_64_bits)
        cprint('k_64_bits (nb limbs) = {}'.format(k_64_bits))
        R_64_bits = mod(W_64_bits**k_64_bits, prime); R_64_bits
        Rsquared_64_bits = R_64_bits**2
        cprint('Rsquared_64_bits = {}'.format(Rsquared_64_bits))
        file.write(f'{Rsquared_64_bits}\n')
        Rcubed_64_bits = R_64_bits**3
        cprint('Rcubed_64_bits = {}'.format(Rcubed_64_bits))
        file.write(f'{Rcubed_64_bits}\n')
        inv_64_bits = hex(int(mod((1/-prime), W_64_bits)))
        cprint('inv_64_bits = {}'.format(inv_64_bits))
        file.write(f'{int(inv_64_bits, base=16)}\n')

        word_len_32_bits = 32
        W_32_bits = 2**(32)
        k_32_bits = ceil(num_bits/word_len_32_bits)
        cprint('k_32_bits (nb limbs) = {}'.format(k_32_bits))
        R_32_bits = mod(W_32_bits**k_32_bits, prime); R_32_bits
        Rsquared_32_bits = R_32_bits**2
        cprint('Rsquared_32_bits = {}'.format(Rsquared_32_bits))
        file.write(f'{Rsquared_32_bits}\n')
        Rcubed_32_bits = R_32_bits**3
        cprint('Rcubed_32_bits = {}'.format(Rcubed_32_bits))
        file.write(f'{Rcubed_32_bits}\n')
        inv_32_bits = hex(int(mod(1/-prime, W_32_bits)))
        cprint('inv_32_bits = {}'.format(inv_32_bits))
        file.write(f'{int(inv_32_bits, base=16)}\n')
