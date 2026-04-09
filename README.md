<div align="center">

[![Python](https://img.shields.io/badge/Python-%E2%89%A53.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qiskit](https://img.shields.io/badge/Qiskit-%E2%89%A52.3-6929C4?logo=qiskit&logoColor=white)](https://qiskit.org/)
[![Stars](https://img.shields.io/github/stars/a1exxd0/mos-quantum-learning)](https://github.com/a1exxd0/mos-quantum-learning/stargazers)
[![Last commit](https://img.shields.io/github/last-commit/a1exxd0/mos-quantum-learning)](https://github.com/a1exxd0/mos-quantum-learning/commits)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# Mixture-of-Superpositions Quantum Learning

**A faithful implementation of the MoS protocol for classically verifiable quantum learning**

Alex Do · Supervised by Dr. Matthias Caro · University of Warwick

</div>

---

### Abstract

We present the first faithful implementation and systematic empirical evaluation of the Mixture-of-Superpositions (MoS) protocol for classically verifiable quantum learning, due to Caro, Hinsche, Ioannou, Nietner, and Sweke. The protocol enables a classical client to delegate a distribution-agnostic Boolean-function learning task to an untrusted quantum server and verify the result using only classical samples. Our implementation comprises two Python packages: a state-level simulator that prepares MoS quantum examples and performs Fourier sampling via postselected Hadamard measurement, and a protocol-level layer that realises the four-step interactive proof between a quantum prover and a classical verifier. We design seven experiments, spanning over 30,000 trials, that probe the protocol along four empirical axes: completeness, soundness, robustness, and sensitivity. Beyond preconditions, we identify two failure modes: a vanishing-margin acceptance ceiling for adversarial mixed-coefficient strategies and a sharp prover-side breakdown under per-gate depolarising noise, the latter lying outside the scope of current theoretical analyses. We discuss limitations including sub-analytic sample budgets, exponential simulation cost, and the absence of real hardware execution, and outline directions for future work.

---

This repository provides two Python packages implementing the interactive proof protocol from [Caro et al. (ITCS 2024)](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITCS.2024.24) for classical verification of quantum learning:

- **`mos/`** - Mixture-of-Superpositions state preparation, Quantum Fourier Sampling, and Fourier analysis
- **`ql/`** - Interactive proof protocol: quantum prover and classical verifier

The accompanying report is available at [**a1exxd0/cs310-final-report**](https://github.com/a1exxd0/cs310-final-report).

## Quickstart

Requires [UV](https://docs.astral.sh/uv/):

```sh
uv sync
```

## Usage

### `mos` — State Simulation and Quantum Fourier Sampling

```python
import numpy as np
from mos import MoSState
from mos.sampler import QuantumFourierSampler

# Encode a Boolean function as label probabilities over {0,1}^3
# Here phi(x) = x_0 (least significant bit parity)
phi = np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
state = MoSState(n=3, phi=phi, noise_rate=0.1, seed=42)

# Draw classical samples (x, y) from the distribution (Lemma 1)
x, y = state.sample_classical()

# Run Quantum Fourier Sampling (Theorem 5)
sampler = QuantumFourierSampler(state, seed=42)
result = sampler.sample(shots=1000, mode="statevector")
print(result.empirical_distribution())

# Inspect the Fourier spectrum
spectrum = state.fourier_spectrum(effective=True)
heavy = {s: c for s, c in enumerate(spectrum) if abs(c) > 0.1}
print(f"Heavy coefficients: {heavy}")
```

### `ql` — Interactive Proof Protocol

```python
import numpy as np
from mos import MoSState
from ql.prover import MoSProver
from ql.verifier import MoSVerifier

# Set up the MoS state
phi = np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
mos_state = MoSState(n=3, phi=phi, seed=42)

# Prover: QFS -> heavy coefficient extraction -> estimates
prover = MoSProver(mos_state, seed=123)
msg = prover.run_protocol(epsilon=0.3, delta=0.1, qfs_shots=2000)
print(f"Candidate heavy set L = {msg.L}")

# Verifier: independent classical verification
verifier = MoSVerifier(mos_state, seed=456)
result = verifier.verify_parity(msg, epsilon=0.3, delta=0.1)

if result.accepted:
    print(f"ACCEPT — learned parity s = {result.hypothesis.s}")
    print(f"h(5) = {result.hypothesis.evaluate(5)}")
else:
    print(f"REJECT — {result.outcome.value}")
```

## Running Tests

```sh
uv run pytest -n auto
```

## Running Experiments

The experiment harness covers completeness, soundness, robustness, and sensitivity:

```sh
uv run python -m experiments.harness {scaling,bent,noise,soundness,soundness_multi,average_case,gate_noise,k_sparse,theta_sensitivity,ab_regime,all} \
  --workers $(nproc 2>/dev/null || sysctl -n hw.ncpu)
```

### Decoding Results

```sh
uv run python -m experiments.decode results/scaling_4_10_20.pb
uv run python -m experiments.decode results/scaling_4_10_20.pb -o results/scaling_4_10_20.json
uv run python -m experiments.decode results/*.pb
```

### SLURM Cluster Submission

```sh
bash experiments/slurm/submit.sh <experiment> <n_min> <n_max> <trials> <num_shards> [partition] [seed]

# Example: 8 shards on the tiger partition (default)
bash experiments/slurm/submit.sh scaling 4 16 24 8
```

## Documentation

```sh
uv run sphinx-build docs docs/_build/html
open docs/_build/html/index.html
```

## References

- [Caro et al. "Classical Verification of Quantum Learning" (ITCS 2024)](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITCS.2024.24)
