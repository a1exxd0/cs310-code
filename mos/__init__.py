r"""
Mixture-of-Superpositions (MoS) State - Definition 8 of Caro et al.

Represents the mixed quantum example state:

.. math::

    \rho_D = \mathbb{E}_{f \sim F_D}
    \bigl[|\psi_{U_n, f}\rangle\langle\psi_{U_n, f}|\bigr]

where :math:`F_D` is the distribution over Boolean functions induced by
independently sampling :math:`f(x) \sim \text{Bernoulli}(\phi(x))` for each
:math:`x \in \{0,1\}^n`, and

.. math::

    |\psi_{U_n, f}\rangle = \frac{1}{\sqrt{2^n}} \sum_x |x, f(x)\rangle

This class handles ONLY state-level concerns:

- Storing the distribution :math:`D = (U_n, \phi)`
- Sampling :math:`f \sim F_D`
- Preparing :math:`|\psi_f\rangle` as a Statevector or QuantumCircuit
- Approximating :math:`\rho_D` via Monte Carlo
- Recovering classical samples via computational basis measurement (Lemma 1)

It does NOT handle Hadamard measurement, post-selection, Fourier sampling,
heavy coefficient extraction, or anything verification-related.

Conventions:

- :math:`\phi(x) = \Pr[y{=}1 \mid x] \in [0, 1]` — the {0,1}-valued label expectation
- :math:`\tilde\phi(x) = 1 - 2\phi(x) \in [-1, 1]` — the {-1,1}-valued label expectation
- Qiskit little-endian: integer :math:`x = \sum_i x_i \cdot 2^i`
- Qubits 0..n-1 hold x, qubit n holds the label bit b
"""

import numpy as np
from typing import Callable, Union, Optional, Tuple
from numpy.random import Generator, default_rng

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector, DensityMatrix


class MoSState:
    r"""
    Mixture-of-Superpositions quantum example state (Definition 8).

    Parameters
    ----------
    n : int
        Number of input bits (dimension of :math:`X_n = \{0,1\}^n`).
    phi : callable or array-like
        The conditional probability function :math:`\phi(x) = \Pr[y{=}1 \mid x]`.
        If callable: ``phi(x: int) -> float`` in [0, 1].
        If array: ``phi[x]`` for x in 0..2^n - 1, values in [0, 1].
    noise_rate : float
        Label-flip noise rate :math:`\eta \in [0, 0.5]`. When :math:`\eta > 0`,
        each label is independently flipped with probability :math:`\eta` before
        state preparation. This corresponds to the MoS noisy functional setting,
        Definition 5(iii).
    seed : int, optional
        Random seed for reproducibility.
    """

    def __init__(
        self,
        n: int,
        phi: Union[Callable[[int], float], np.ndarray],
        noise_rate: float = 0.0,
        seed: Optional[int] = None,
    ):
        if n < 1:
            raise ValueError(f"n must be >= 1, got {n}")
        if not 0.0 <= noise_rate <= 0.5:
            raise ValueError(f"noise_rate must be in [0, 0.5], got {noise_rate}")

        self.n: int = n
        self.dim_x: int = 2**n
        self.dim_total: int = 2 ** (n + 1)
        self.noise_rate: float = noise_rate
        self._rng: Generator = default_rng(seed)

        # Store phi as array
        if callable(phi):
            self._phi = np.array([phi(x) for x in range(self.dim_x)], dtype=np.float64)
        else:
            self._phi = np.asarray(phi, dtype=np.float64).copy()
            if len(self._phi) != self.dim_x:
                raise ValueError(
                    f"phi must have length 2^n = {self.dim_x}, got {len(self._phi)}"
                )

        if not np.all((self._phi >= 0.0) & (self._phi <= 1.0)):
            raise ValueError("All phi values must be in [0, 1]")

        # Precompute effective phi under noise:
        #   phi_eff(x) = (1 - 2*eta) * phi(x) + eta
        # This is the effective Pr[y=1|x] after independent label flips.
        eta = self.noise_rate
        self._phi_effective: np.ndarray = (1 - 2 * eta) * self._phi + eta

    # ------------------------------------------------------------------
    # Properties: access phi in both {0,1} and {-1,1} conventions
    # ------------------------------------------------------------------

    @property
    def phi(self) -> np.ndarray:
        r""":math:`\phi(x) = \Pr[y{=}1 \mid x]` in [0, 1] for all x (noiseless)."""
        return self._phi

    @property
    def tilde_phi(self) -> np.ndarray:
        r""":math:`\tilde\phi(x) = 1 - 2\phi(x)` in [-1, 1] for all x (noiseless)."""
        return 1.0 - 2.0 * self._phi

    @property
    def phi_effective(self) -> np.ndarray:
        r"""Effective phi after noise. :math:`(1 - 2\eta)\phi(x) + \eta`."""
        return self._phi_effective

    @property
    def tilde_phi_effective(self) -> np.ndarray:
        r"""Effective tilde_phi after noise. :math:`(1 - 2\eta) \tilde\phi(x)`."""
        return 1.0 - 2.0 * self._phi_effective

    # ------------------------------------------------------------------
    # Sampling f ~ F_D (Definition 8)
    # ------------------------------------------------------------------

    def sample_f(self, rng: Optional[Generator] = None) -> np.ndarray:
        r"""
        Sample a random Boolean function :math:`f \sim F_D`.

        For each :math:`x \in \{0,1\}^n`, independently sample
        :math:`f(x) \sim \text{Bernoulli}(\phi_{\text{eff}}(x))`.
        When ``noise_rate > 0``, :math:`\phi_{\text{eff}}` incorporates
        the label-flip noise.

        Parameters
        ----------
        rng : Generator, optional
            NumPy random generator. Uses internal RNG if not provided.

        Returns
        -------
        f : np.ndarray of shape (2^n,), dtype=np.uint8
            ``f[x]`` is the value f(x) in {0, 1}.
        """
        if rng is None:
            rng = self._rng
        return (rng.random(self.dim_x) < self._phi_effective).astype(np.uint8)

    # ------------------------------------------------------------------
    # Pure state preparation: |psi_{U_n, f}>
    # ------------------------------------------------------------------

    def statevector_f(self, f: np.ndarray) -> Statevector:
        r"""
        Construct the Qiskit Statevector :math:`|\psi_{U_n, f}\rangle` for a
        fixed function f.

        .. math::

            |\psi_{U_n, f}\rangle
            = \frac{1}{\sqrt{2^n}} \sum_x |x,\, f(x)\rangle

        In Qiskit's little-endian convention, :math:`|x, b\rangle` maps to
        index :math:`x + b \cdot 2^n` since qubit n (the label) is the
        highest-index qubit.

        Parameters
        ----------
        f : np.ndarray of shape (2^n,), dtype=np.uint8
            Boolean function values.

        Returns
        -------
        sv : Statevector
            The (n+1)-qubit state :math:`|\psi_{U_n, f}\rangle`.
        """
        sv_data = np.zeros(self.dim_total, dtype=np.complex128)
        amp = 1.0 / np.sqrt(self.dim_x)

        for x in range(self.dim_x):
            idx = x + int(f[x]) * self.dim_x
            sv_data[idx] = amp

        return Statevector(sv_data)

    # ------------------------------------------------------------------
    # Circuit preparation of |psi_{U_n, f}>
    # ------------------------------------------------------------------

    def _circuit_oracle_f(self, f: np.ndarray) -> QuantumCircuit:
        r"""
        Build an oracle circuit :math:`U_f` mapping
        :math:`|x\rangle|0\rangle \to |x\rangle|f(x)\rangle`.

        For each x where f(x) = 1, applies a multi-controlled X gate on the
        label qubit, controlled on the input register being :math:`|x\rangle`.

        Parameters
        ----------
        f : np.ndarray
            Boolean function values.

        Returns
        -------
        qc : QuantumCircuit
            Oracle circuit on n+1 qubits.
        """
        qr = QuantumRegister(self.n + 1, "q")
        qc = QuantumCircuit(qr, name="oracle_f")

        for x in range(self.dim_x):
            if f[x] == 1:
                ctrl_state = format(x, f"0{self.n}b")
                if self.n == 1:
                    # Single-controlled X
                    qc.cx(0, 1, ctrl_state=ctrl_state)
                else:
                    qc.mcx(
                        control_qubits=list(range(self.n)),
                        target_qubit=self.n,
                        ctrl_state=ctrl_state,
                    )

        return qc

    def circuit_prepare_f(self, f: np.ndarray) -> QuantumCircuit:
        r"""
        Build a circuit preparing :math:`|\psi_{U_n, f}\rangle` via
        :math:`H^{\otimes n}` + oracle.

        .. math::

            |0\rangle^{\otimes(n+1)}
            \xrightarrow{H^{\otimes n} \otimes I}
            |{+}\rangle^{\otimes n}|0\rangle
            \xrightarrow{U_f}
            |\psi_{U_n, f}\rangle

        This is more hardware-friendly than arbitrary state initialisation.

        Parameters
        ----------
        f : np.ndarray
            Boolean function values.

        Returns
        -------
        qc : QuantumCircuit
            Circuit on n+1 qubits that prepares
            :math:`|\psi_{U_n, f}\rangle`.
        """
        qr = QuantumRegister(self.n + 1, "q")
        qc = QuantumCircuit(qr, name="prepare_psi_f")

        # Uniform superposition on the x-register
        for i in range(self.n):
            qc.h(qr[i])

        # Apply oracle to entangle label register
        oracle = self._circuit_oracle_f(f)
        qc.compose(oracle, inplace=True)

        return qc

    def circuit_prepare_f_initialize(self, f: np.ndarray) -> QuantumCircuit:
        r"""
        Build a circuit preparing :math:`|\psi_{U_n, f}\rangle` via Qiskit's
        Initialize.

        Exact but synthesises an arbitrary state preparation unitary —
        less portable to real hardware.

        Parameters
        ----------
        f : np.ndarray
            Boolean function values.

        Returns
        -------
        qc : QuantumCircuit
            Circuit on n+1 qubits.
        """
        sv = self.statevector_f(f)
        qr = QuantumRegister(self.n + 1, "q")
        qc = QuantumCircuit(qr, name="prepare_psi_f_init")
        qc.initialize(sv, qr)
        return qc

    # ------------------------------------------------------------------
    # Density matrix: rho_D = E_{f ~ F_D}[|psi_f><psi_f|]
    # ------------------------------------------------------------------

    def density_matrix(
        self,
        num_samples: int = 1000,
        rng: Optional[Generator] = None,
    ) -> DensityMatrix:
        r"""
        Approximate :math:`\rho_D` by Monte Carlo averaging over sampled f.

        .. math::

            \rho_D \approx \frac{1}{M}
            \sum_{m=1}^{M} |\psi_{f_m}\rangle\langle\psi_{f_m}|

        Parameters
        ----------
        num_samples : int
            Number of functions f to sample (M).
        rng : Generator, optional
            NumPy random generator.

        Returns
        -------
        rho : DensityMatrix
            Monte Carlo estimate of the MoS density matrix.
        """
        if rng is None:
            rng = self._rng

        rho_data = np.zeros((self.dim_total, self.dim_total), dtype=np.complex128)

        for _ in range(num_samples):
            f = self.sample_f(rng)
            sv = self.statevector_f(f)
            rho_data += np.outer(sv.data, sv.data.conj())

        rho_data /= num_samples
        return DensityMatrix(rho_data)

    # ------------------------------------------------------------------
    # Classical sampling: computational basis measurement (Lemma 1)
    # ------------------------------------------------------------------

    def sample_classical(
        self,
        rng: Optional[Generator] = None,
    ) -> Tuple[int, int]:
        r"""
        Draw a classical sample :math:`(x, y) \sim D` by measuring
        :math:`\rho_D` in the computational basis.

        By Lemma 1, this is equivalent to drawing :math:`(x, y) \sim D`
        directly:

        1. Sample :math:`f \sim F_D`
        2. Prepare :math:`|\psi_{U_n, f}\rangle`
        3. Measure in computational basis — yields :math:`(x, f(x))` with
           :math:`x \sim U_n`

        Equivalently (and more efficiently), we can just sample
        :math:`x \sim U_n` and :math:`y \sim \text{Bernoulli}(\phi_{\text{eff}}(x))`
        directly.

        Parameters
        ----------
        rng : Generator, optional
            NumPy random generator.

        Returns
        -------
        x : int
            Input in {0, ..., 2^n - 1}.
        y : int
            Label in {0, 1}.
        """
        if rng is None:
            rng = self._rng

        x = rng.integers(0, self.dim_x)
        y = int(rng.random() < self._phi_effective[x])
        return x, y

    def sample_classical_batch(
        self,
        num_samples: int,
        rng: Optional[Generator] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Draw a batch of classical samples :math:`(x_i, y_i) \\sim D`.

        Parameters
        ----------
        num_samples : int
            Number of samples.
        rng : Generator, optional
            NumPy random generator.

        Returns
        -------
        xs : np.ndarray of shape (num_samples,), dtype=int
            Input values.
        ys : np.ndarray of shape (num_samples,), dtype=int
            Label values.
        """
        if rng is None:
            rng = self._rng

        xs = rng.integers(0, self.dim_x, size=num_samples)
        ys = (rng.random(num_samples) < self._phi_effective[xs]).astype(np.uint8)
        return xs, ys

    # ------------------------------------------------------------------
    # Fourier analysis (for validation / ground truth)
    # ------------------------------------------------------------------

    def fourier_coefficient(self, s: int) -> float:
        r"""
        Compute the exact Fourier coefficient :math:`\hat{\tilde\phi}(s)`.

        .. math::

            \hat{\tilde\phi}(s)
            = \mathbb{E}_{x \sim U_n}[\tilde\phi(x) \cdot \chi_s(x)]

        where :math:`\chi_s(x) = (-1)^{s \cdot x}` and
        :math:`\tilde\phi = 1 - 2\phi` (noiseless).

        Parameters
        ----------
        s : int
            Frequency index in {0, ..., 2^n - 1}.

        Returns
        -------
        coeff : float
            The Fourier coefficient :math:`\hat{\tilde\phi}(s)`.
        """
        tphi = self.tilde_phi
        # Compute (-1)^{popcount(s & x)} for all x
        parities = np.array([bin(s & x).count("1") % 2 for x in range(self.dim_x)])
        chi_s = 1.0 - 2.0 * parities  # (-1)^{s·x}
        return float(np.mean(tphi * chi_s))

    def fourier_coefficient_effective(self, s: int) -> float:
        r"""
        Compute :math:`\hat{\tilde\phi}_{\text{eff}}(s)
        = (1 - 2\eta) \hat{\tilde\phi}(s)`.

        This is the Fourier coefficient of the noise-adjusted
        :math:`\tilde\phi`, which governs the actual sampling distribution
        from Theorem 5 when ``noise_rate > 0``.

        Parameters
        ----------
        s : int
            Frequency index in {0, ..., 2^n - 1}.

        Returns
        -------
        coeff : float
            The effective Fourier coefficient.
        """
        return (1.0 - 2.0 * self.noise_rate) * self.fourier_coefficient(s)

    def fourier_spectrum(self) -> np.ndarray:
        r"""
        Compute the full Fourier spectrum
        :math:`\{\hat{\tilde\phi}(s)\}` for all s.

        Returns
        -------
        spectrum : np.ndarray of shape (2^n,)
            ``spectrum[s]`` = :math:`\hat{\tilde\phi}(s)`.
        """
        return np.array([self.fourier_coefficient(s) for s in range(self.dim_x)])

    def parseval_check(self) -> Tuple[float, float]:
        r"""
        Verify Parseval's identity:
        :math:`\sum_s \hat{\tilde\phi}(s)^2 = \mathbb{E}[\tilde\phi(x)^2]`.

        Returns
        -------
        fourier_sum : float
            :math:`\sum_s \hat{\tilde\phi}(s)^2`
        expected_sq : float
            :math:`\mathbb{E}_{x \sim U_n}[\tilde\phi(x)^2]`
        """
        spectrum = self.fourier_spectrum()
        fourier_sum = float(np.sum(spectrum**2))
        expected_sq = float(np.mean(self.tilde_phi**2))
        return fourier_sum, expected_sq

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        noise_str = f", noise_rate={self.noise_rate}" if self.noise_rate > 0 else ""
        return f"MoSState(n={self.n}{noise_str})"

    def summary(self) -> str:
        """Human-readable summary of the MoS state."""
        tphi = self.tilde_phi
        fourier_sum, expected_sq = self.parseval_check()

        lines = [
            "MoS State (Definition 8)",
            f"  n = {self.n}, dim = 2^n = {self.dim_x}",
            f"  noise_rate = {self.noise_rate}",
            f"  E[tilde_phi^2] = {expected_sq:.6f}",
            f"  Parseval check: sum hat(s)^2 = {fourier_sum:.6f}",
            f"  phi range: [{self._phi.min():.4f}, {self._phi.max():.4f}]",
            f"  tilde_phi range: [{tphi.min():.4f}, {tphi.max():.4f}]",
        ]

        # Show nonzero Fourier coefficients if manageable
        if self.dim_x <= 64:
            spectrum = self.fourier_spectrum()
            nonzero = [
                (s, spectrum[s]) for s in range(self.dim_x) if abs(spectrum[s]) > 1e-10
            ]
            lines.append(f"  Nonzero Fourier coefficients: {len(nonzero)}")
            for s, coeff in sorted(nonzero, key=lambda t: abs(t[1]), reverse=True):
                bits = format(s, f"0{self.n}b")
                lines.append(f"    s={s} ({bits}): {coeff:+.6f}")

        return "\n".join(lines)
