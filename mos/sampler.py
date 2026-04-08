r"""
Quantum Fourier Sampling from MoS states — Theorem 5 of Caro et al.

Implements the QFS procedure: given a copy of the MoS state
:math:`\rho_D`, apply :math:`H^{\otimes(n+1)}`, measure all qubits in
the computational basis, and post-select on the label qubit being 1.

**Theorem 5** (Distributional agnostic approximate quantum Fourier sampling).
Conditioned on observing outcome 1 for the last qubit (which occurs with
probability 1/2), the first :math:`n` qubits output :math:`s \in \{0,1\}^n`
with probability

.. math::

    \Pr[s \mid b{=}1]
    = \frac{1}{2^n}
      \bigl(1 - \mathbb{E}_{x \sim U_n}[(\tilde\phi_{\text{eff}}(x))^2]\bigr)
    + \bigl(\hat{\tilde\phi}_{\text{eff}}(s)\bigr)^2

This module provides two simulation strategies:

- **statevector** (default): For each sampled :math:`f \sim F_D`, constructs
  :math:`|\psi_f\rangle` as a Statevector, applies :math:`H^{\otimes(n+1)}`,
  and samples from the resulting probability distribution.  Exact (no
  shot noise beyond finite sampling).  Cost: :math:`O(2^n)` per copy.
  Practical for :math:`n \leq 20`.

- **circuit**: Builds a Qiskit circuit (Hadamard layer + oracle) for each
  :math:`f` and executes it via ``StatevectorSampler``.  Produces identical
  distributions to statevector mode but uses the Qiskit primitives pipeline,
  validating circuit construction.  Practical for :math:`n \leq 12` due
  to multi-controlled gate overhead.

Both modes return raw measurement counts (before post-selection) so that
the caller can verify the 1/2 label-qubit marginal and inspect rejection
rates.

References:

- Caro et al., "Classical Verification of Quantum Learning", ITCS 2024.
  Theorem 5 (Section 5.1), Lemma 2 (Section 4.1), Corollary 5 (Section 5.1).
- Bernstein & Vazirani (1997) for the original QFS idea.
"""

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.random import Generator, default_rng

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

# ---------------------------------------------------------------------------
# Import MoSState — assumes mos_state.py is importable
# ---------------------------------------------------------------------------
from mos import MoSState


# ===================================================================
# Result container
# ===================================================================


@dataclass(frozen=True)
class QFSResult:
    r"""
    Container for raw and post-selected QFS measurement outcomes.

    Attributes
    ----------
    raw_counts : dict[str, int]
        Full :math:`(n+1)`-bit measurement counts (bitstrings in Qiskit
        little-endian convention:  rightmost character = qubit 0).
    postselected_counts : dict[str, int]
        :math:`n`-bit frequency counts for the input register, conditioned
        on the label qubit being 1.
    total_shots : int
        Number of MoS copies consumed (= circuits executed).
    postselected_shots : int
        Number of shots surviving post-selection (label qubit = 1).
    n : int
        Number of input qubits.
    mode : str
        Simulation mode used (``"statevector"`` or ``"circuit"``).
    """

    raw_counts: dict[str, int]
    postselected_counts: dict[str, int]
    total_shots: int
    postselected_shots: int
    n: int
    mode: str

    # ---- derived quantities ----

    @property
    def postselection_rate(self) -> float:
        r"""
        Fraction of shots surviving post-selection.

        By Theorem 5(i) this should concentrate around 1/2.
        """
        if self.total_shots == 0:
            return 0.0
        return self.postselected_shots / self.total_shots

    def empirical_distribution(self) -> np.ndarray:
        r"""
        Normalised empirical distribution over :math:`\{0,1\}^n` from
        the post-selected counts.

        Returns
        -------
        dist : np.ndarray of shape :math:`(2^n,)`
            ``dist[s]`` is the empirical probability of frequency s.
            Zero everywhere if no shots survived post-selection.
        """
        dim = 2**self.n
        dist = np.zeros(dim, dtype=np.float64)
        if self.postselected_shots == 0:
            return dist
        for bitstring, count in self.postselected_counts.items():
            s = int(bitstring, 2)
            dist[s] += count
        dist /= self.postselected_shots
        return dist


# ===================================================================
# Main class
# ===================================================================


class QuantumFourierSampler:
    r"""
    Approximate quantum Fourier sampling from MoS states (Theorem 5).

    Consumes copies of :math:`\rho_D`, applies :math:`H^{\otimes(n+1)}`,
    measures all :math:`n+1` qubits in the computational basis, and
    post-selects on the label qubit (qubit :math:`n`) being 1.

    **Protocol** (one copy):

    1. Sample :math:`f \sim F_D` using :math:`\phi_{\text{eff}}`.
    2. Prepare :math:`|\psi_{U_n,f}\rangle = 2^{-n/2}\sum_x |x,f(x)\rangle`.
    3. Apply :math:`H^{\otimes(n+1)}`.
    4. Measure all qubits → outcome :math:`(s, b) \in \{0,1\}^n \times \{0,1\}`.
    5. If :math:`b = 1`, record :math:`s`.

    By Theorem 5, the conditional distribution is

    .. math::

        \Pr[s \mid b{=}1]
        = \frac{1 - \mathbb{E}_x[\tilde\phi_{\text{eff}}(x)^2]}{2^n}
        + \hat{\tilde\phi}_{\text{eff}}(s)^2

    Parameters
    ----------
    mos_state : MoSState
        The MoS state to sample from.  Defines :math:`n`, :math:`\phi`,
        and the noise model.
    seed : int, optional
        Random seed for reproducibility.
    """

    # valid mode names
    _MODES = {"statevector", "circuit"}

    def __init__(
        self,
        mos_state: MoSState,
        seed: Optional[int] = None,
        noise_model: Optional[object] = None,
    ):
        self.state = mos_state
        self.n = mos_state.n
        self._seed = seed
        self._rng: Generator = default_rng(seed)
        self._noise_model = noise_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sample(
        self,
        shots: int,
        mode: str = "statevector",
    ) -> QFSResult:
        r"""
        Execute the QFS protocol and return raw + post-selected counts.

        Each shot consumes one independent copy of :math:`\rho_D`.  The
        label qubit marginal should be close to 1/2 (Theorem 5(i)); any
        significant deviation indicates a bug.

        Parameters
        ----------
        shots : int
            Number of MoS copies to consume (:math:`\geq 1`).
        mode : str
            Simulation strategy:

            - ``"statevector"`` — direct Statevector computation per copy.
            - ``"circuit"`` — Qiskit circuit + ``StatevectorSampler`` per copy.

        Returns
        -------
        QFSResult
            Raw and post-selected measurement counts.

        Raises
        ------
        ValueError
            If *shots* < 1 or *mode* is unrecognised.
        """
        if shots < 1:
            raise ValueError(f"shots must be >= 1, got {shots}")
        if mode not in self._MODES:
            raise ValueError(
                f"Unknown mode {mode!r}; expected one of {sorted(self._MODES)}"
            )

        dispatch = {
            "statevector": self._sample_statevector,
            "circuit": self._sample_circuit,
        }
        raw_counts = dispatch[mode](shots)
        ps_counts, ps_shots = self._postselect(raw_counts)

        return QFSResult(
            raw_counts=raw_counts,
            postselected_counts=ps_counts,
            total_shots=shots,
            postselected_shots=ps_shots,
            n=self.n,
            mode=mode,
        )

    # ------------------------------------------------------------------
    # Theoretical reference quantities (delegated to MoSState)
    # ------------------------------------------------------------------

    def theoretical_distribution(self) -> np.ndarray:
        r"""
        Exact :math:`\Pr[s \mid b{=}1]` from Theorem 5.

        .. math::

            \Pr[s \mid b{=}1]
            = \frac{1 - \mathbb{E}_x[\tilde\phi_{\text{eff}}(x)^2]}{2^n}
            + \hat{\tilde\phi}_{\text{eff}}(s)^2

        Always uses the effective (noise-adjusted) spectrum, since this is
        what the physical QFS circuit produces.

        Returns
        -------
        dist : np.ndarray of shape :math:`(2^n,)`
        """
        return self.state.qfs_distribution()

    def fourier_coefficient(
        self,
        s: int,
        effective: bool = True,
    ) -> float:
        r"""
        Exact Fourier coefficient for validation.

        Parameters
        ----------
        s : int
            Frequency index in :math:`\{0, \ldots, 2^n - 1\}`.
        effective : bool
            If True (default), return
            :math:`\hat{\tilde\phi}_{\text{eff}}(s) = (1-2\eta)\hat{\tilde\phi}(s)`.
            If False, return the noiseless :math:`\hat{\tilde\phi}(s)`.

        Returns
        -------
        float
        """
        return self.state.fourier_coefficient(s, effective=effective)

    # ------------------------------------------------------------------
    # Private: simulation backends
    # ------------------------------------------------------------------

    def _sample_statevector(self, shots: int) -> dict[str, int]:
        r"""
        Statevector mode: for each copy, build
        :math:`H^{\otimes(n+1)}|\psi_f\rangle` and sample.

        For every sampled :math:`f`, the Hadamard-transformed statevector
        has closed-form amplitudes (proof of Lemma 2):

        .. math::

            H^{\otimes(n+1)}|\psi_f\rangle
            = \frac{1}{\sqrt{2}}|0\rangle^{\otimes(n+1)}
            + \frac{1}{\sqrt{2}}\sum_s \hat{g}_f(s)\,|s,1\rangle

        where :math:`g_f = (-1)^f`.  Rather than recomputing this
        symbolically, we apply the Hadamard via
        :meth:`Statevector.evolve` and use
        :meth:`Statevector.sample_counts`.
        """
        n = self.n
        dim_total = self.state.dim_total
        counts: dict[str, int] = {}

        # Build the (n+1)-qubit Hadamard circuit once
        h_circuit = QuantumCircuit(n + 1, name="H_all")
        for q in range(n + 1):
            h_circuit.h(q)

        for _ in range(shots):
            f = self.state.sample_f(rng=self._rng)
            psi_f = self.state.statevector_f(f)
            psi_h = psi_f.evolve(h_circuit)

            # Draw one measurement outcome using the internal RNG
            probs = psi_h.probabilities()
            idx = self._rng.choice(dim_total, p=probs)
            bitstring = format(idx, f"0{n + 1}b")
            counts[bitstring] = counts.get(bitstring, 0) + 1

        return counts

    def _sample_circuit(self, shots: int) -> dict[str, int]:
        r"""
        Circuit mode: build a full Qiskit circuit per copy and execute
        via ``StatevectorSampler``.

        Each circuit is:

        .. math::

            |0\rangle^{\otimes(n+1)}
            \;\xrightarrow{H^{\otimes n}\otimes I}\;
            |{+}\rangle^{\otimes n}|0\rangle
            \;\xrightarrow{U_f}\;
            |\psi_f\rangle
            \;\xrightarrow{H^{\otimes(n+1)}}\;
            \text{measure}

        This validates the circuit-construction pipeline (oracle gates,
        Hadamard layer, measurement) against the statevector mode.
        Practical for :math:`n \leq 12` due to multi-controlled gate
        overhead in :meth:`MoSState._circuit_oracle_f`.
        """
        if self.n > 12:
            warnings.warn(
                f"Circuit mode with n={self.n} will be very slow "
                f"(up to 2^n multi-controlled gates per copy).",
                stacklevel=3,
            )

        n = self.n
        counts: dict[str, int] = {}

        # Build all circuits up front
        circuits = []
        for _ in range(shots):
            f = self.state.sample_f(rng=self._rng)
            qc = self.state.circuit_prepare_f(f)
            for q in range(n + 1):
                qc.h(q)
            qc.measure_all()
            circuits.append(qc)

        if self._noise_model is not None:
            # Gate-level noise: use AerSimulator with the noise model.
            # The circuit is transpiled so that MCX gates decompose
            # into basis gates (CX, H, X, etc.) to which the noise
            # model's depolarising channels apply.
            from qiskit_aer import AerSimulator
            from qiskit import transpile

            backend = AerSimulator(noise_model=self._noise_model)
            for qc in circuits:
                child_seed = int(self._rng.integers(0, 2**31))
                qc_t = transpile(qc, backend)
                result = backend.run(
                    qc_t, shots=1, seed_simulator=child_seed
                ).result()
                for bitstring, cnt in result.get_counts().items():
                    # AerSimulator may include spaces in bitstrings;
                    # strip them for consistency.
                    bs = bitstring.replace(" ", "")
                    counts[bs] = counts.get(bs, 0) + cnt
        else:
            # Batch all circuits in a single sampler.run() call.
            # Pass a Generator *object* (not an int) so the sampler
            # holds a mutable reference whose state advances between
            # PUBs — otherwise identical circuits get identical draws
            # (Qiskit bug #13047).
            child_rng = default_rng(int(self._rng.integers(0, 2**31)))
            sampler = StatevectorSampler(seed=child_rng)
            job = sampler.run(circuits, shots=1)
            for pub_result in job.result():
                for bitstring, cnt in pub_result.data.meas.get_counts().items():
                    counts[bitstring] = counts.get(bitstring, 0) + cnt

        return counts

    # ------------------------------------------------------------------
    # Private: post-selection
    # ------------------------------------------------------------------

    def _postselect(
        self,
        raw_counts: dict[str, int],
    ) -> tuple[dict[str, int], int]:
        r"""
        Extract the :math:`n`-bit frequency distribution conditioned on
        the label qubit :math:`b = 1`.

        In the raw bitstrings (Qiskit convention: highest qubit index on
        the left), the label qubit (qubit :math:`n`) is the **leftmost**
        character.  We keep only bitstrings where this character is
        ``'1'``, then strip it to obtain the :math:`n`-bit frequency
        string.

        Parameters
        ----------
        raw_counts : dict[str, int]
            Full :math:`(n+1)`-bit counts from measurement.

        Returns
        -------
        ps_counts : dict[str, int]
            :math:`n`-bit post-selected counts.
        ps_total : int
            Total shots surviving post-selection.
        """
        ps_counts: dict[str, int] = {}
        ps_total = 0
        for bitstring, count in raw_counts.items():
            # bitstring[0] = highest qubit = qubit n = label qubit
            if bitstring[0] == "1":
                s_bits = bitstring[1:]  # remaining n bits
                ps_counts[s_bits] = ps_counts.get(s_bits, 0) + count
                ps_total += count
        return ps_counts, ps_total
