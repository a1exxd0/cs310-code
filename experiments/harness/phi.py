r"""Phi generators for constructing label-bias functions.

Functions that build :math:`\varphi(x) = \Pr[y{=}1 \mid x]` vectors
for use as inputs to the MoS verification protocol experiments.
"""

import numpy as np


def make_single_parity(n: int, target_s: int) -> list[float]:
    r"""Construct :math:`\varphi` for a pure parity function.

    .. math::

        \varphi(x) = s^* \cdot x \bmod 2

    so that :math:`\tilde\phi = \chi_{s^*}` and the Fourier spectrum has
    a single nonzero coefficient :math:`\hat{\tilde\phi}(s^*) = 1`.

    Parameters
    ----------
    n : int
        Number of input bits.
    target_s : int
        Parity index :math:`s^* \in \{0, \ldots, 2^n - 1\}`.

    Returns
    -------
    list[float]
        :math:`\varphi(x)` for :math:`x = 0, \ldots, 2^n - 1`.
    """
    return [float(bin(target_s & x).count("1") % 2) for x in range(2**n)]


def make_random_parity(n: int, rng: np.random.Generator) -> tuple[list[float], int]:
    r"""Construct :math:`\varphi` for a uniformly random nonzero parity.

    Draws :math:`s^* \sim \mathrm{Uniform}(\{1, \ldots, 2^n - 1\})` and
    returns the corresponding :math:`\varphi` via :func:`make_single_parity`.

    Parameters
    ----------
    n : int
        Number of input bits.
    rng : numpy.random.Generator
        Random number generator.

    Returns
    -------
    phi : list[float]
        Label-bias function.
    target_s : int
        The sampled parity index.
    """
    s = int(rng.integers(1, 2**n))
    return make_single_parity(n, s), s


def make_bent_function(n: int) -> list[float]:
    r"""Construct :math:`\varphi` for a Maiorana--McFarland bent function.

    For even :math:`n`, defines :math:`f(x, y) = \langle x, y \rangle \bmod 2`
    where :math:`x, y \in \{0,1\}^{n/2}`.  The resulting
    :math:`g = (-1)^f` has all Fourier coefficients equal in magnitude:

    .. math::

        |\hat{g}(s)| = 2^{-n/2} \quad \forall\, s \in \{0,1\}^n

    This is the worst case for heavy coefficient extraction because no
    coefficient dominates: Parseval gives :math:`\sum_s \hat{g}(s)^2 = 1`
    spread uniformly over all :math:`2^n` frequencies.

    Parameters
    ----------
    n : int
        Number of input bits (must be even).

    Returns
    -------
    list[float]
        :math:`\varphi(x)` for :math:`x = 0, \ldots, 2^n - 1`.

    Raises
    ------
    ValueError
        If *n* is odd.
    """
    if n % 2 != 0:
        raise ValueError(f"Bent functions require even n, got {n}")
    half = n // 2
    phi = []
    for z in range(2**n):
        x_bits = z & ((1 << half) - 1)
        y_bits = (z >> half) & ((1 << half) - 1)
        phi.append(float(bin(x_bits & y_bits).count("1") % 2))
    return phi
