# SmallWood Proof System & CAPSS Framework

This repository contains a prototype implementation (in Python) of the **SmallWood** proof system and the **CAPSS** framework.

- **SmallWood** is a hash-based proof system targeting small-to-medium statements.
- **CAPSS** is a framework for constructing SNARK-friendly, post-quantum signature schemes from arithmetization-oriented permutations.


📄 The accompanying papers introducing SmallWood and CAPSS are available on the IACR ePrint archive: [https://eprint.iacr.org/2025/1085](https://eprint.iacr.org/2025/1085) and [https://eprint.iacr.org/2025/061](https://eprint.iacr.org/2025/061).

⚠️ **Warning**: This is a prototype implementation. It has not been audited and may contain bugs or security vulnerabilities. It is **not** intended for production use.

## 🚦 Dependencies

The Python implementation relies on SageMath.

## 📚 Documentation

### Project Structure

  - The folder `smallwood` implements the SmallWood proof systems:
    - The sub-folder `commit` implements Merkle trees (`merkle`), the degree-enforcing commitment scheme (`decs`), the SmallWood-LVCS (`lvcs`) and the SmallWood polynomial commitment scheme (`pcs`).
    - The sub-folder `pacs` implements the logic of the parallel and aggregated constraint systems (PACS), which is the input constrain system format of the proof system SmallWood.
    - The file `smallwood.py` implements the SmallWood proof system, independently of the used hash functions. The file `shake.py` and `aohash.py` are then respectively instantiations of the proof systems using respectively SHAKE and arithmetization-oriented hash functions.
  - The folder `utils` implements from helpers to deal with arrays, buffer, polynomials, logs, etc.
  - The folder `r1cs` implements a R1CS compiler, namely a tool that derive on-the-fly a R1CS constraints of a Python code.
  - The folder `capss` implements the CAPSS framework from the SmallWood proof systems based on arithmetization-oriented hash functions.
    - The sub-folder `hash` contains implementations of AO permutations. At the time of writing, there are Anemoi (`anemoi`), Griffin (`griffin`), Poseidon (`poseidon`), and RescuePrime (`rescue`).
    - The sub-folder `pacs` implements the PACS arithemization for verifying an execution of an AO permutation, including the Regular-Permutation arithmetization and the Sbox-centrix arithmetization.
    - The sub-folder `sign` implements the CAPSS signature scheme.

### Testing

Run the script
```python3
sage --python3 test.py G256-3 default
```
It gives the signature size and the parameters of the R1CS constraints encoding the verification algorithm for the CAPSS signature scheme based on Griffin-3 over a 256-bit field, with trade-off "default".

## 📄 License

This project is licensed under the terms of Apache License (version 2.0).
