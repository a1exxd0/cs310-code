"""
Dishonest Prover Experiments for the MoS Verification Protocol.

Two failure modes:
  1. Oracle mismatch  — prover performs correct computation on wrong data.
  2. Noisy prover     — oracle-level noise attenuates Fourier coefficients.

Run:
    cd /path/to/cs310-code && uv run python dishonest_prover_experiments.py
"""

import numpy as np
from mos.mos_simulator import MoSSimulator
from ql.verifier import MoSProtocol

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_noisy_parity_phi(n: int, target_s: int, eta: float) -> np.ndarray:
    """
    Build phi for a noisy parity distribution.

    phi(x) = (1-eta) * parity(s,x)  +  eta * (1 - parity(s,x))
           = eta + (1 - 2*eta) * parity(s,x)

    where parity(s,x) = <s,x> mod 2.
    """
    phi = np.zeros(2**n)
    for x in range(2**n):
        parity = bin(target_s & x).count('1') % 2
        phi[x] = (1 - eta) * parity + eta * (1 - parity)
    return phi


def print_header(title: str):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_protocol_and_report(
    label: str,
    phi_true: np.ndarray,
    n: int,
    prover_simulator=None,
    prover_copies: int = 60_000,
    verifier_samples_per_coeff: int = 20_000,
    seed: int = 42,
):
    """Run the protocol and print a structured report."""
    sim_true = MoSSimulator(n=n, phi=phi_true, seed=seed)
    protocol = MoSProtocol(
        simulator=sim_true,
        phi=phi_true,
        seed=seed,
        prover_simulator=prover_simulator,
    )
    transcript = protocol.run(
        epsilon=0.1,
        delta=0.05,
        prover_copies=prover_copies,
        verifier_samples_per_coeff=verifier_samples_per_coeff,
    )
    vr = transcript.verifier_result

    print(f"\n--- {label} ---")
    print(f"  Prover's list L = {[format(s, f'0{n}b') for s in transcript.prover_list]}")
    print(f"  Prover's weight estimates: "
          + ", ".join(f"|φ̂({s})|²≈{w:.4f}" for s, w in transcript.prover_weights.items()))
    print(f"  Decision:  {vr.decision.value}")
    print(f"  Reason:    {vr.reason}")
    print(f"  Estimated list weight: {vr.estimated_list_weight:.6f}")
    print(f"  Expected interval:     [{protocol.weight_interval[0]:.6f}, "
          f"{protocol.weight_interval[1]:.6f}]")
    return transcript


# ---------------------------------------------------------------------------
# Experiment 1: Oracle Mismatch
# ---------------------------------------------------------------------------

def experiment_oracle_mismatch():
    print_header("EXPERIMENT 1: Oracle Mismatch  (O_V ≠ O_P)")
    print("""
    The prover performs correct quantum computation but on the WRONG data.
    Verifier has phi with target parity s* = 1011.
    Prover uses a mismatched target parity string.
    """)

    n = 4
    eta = 0.15  # noise rate for noisy parity
    target_true = 0b1011  # s* that verifier knows about

    # Mismatched targets for the prover to use
    mismatched_targets = [
        (0b1010, "1010  (1-bit flip)"),
        (0b0011, "0011  (1-bit flip)"),
        (0b0101, "0101  (2-bit flip)"),
        (0b0000, "0000  (trivial)"),
    ]

    phi_true = make_noisy_parity_phi(n, target_true, eta)

    # First, run the honest case as baseline
    print("\n[Baseline: honest prover with correct oracle]")
    run_protocol_and_report("Honest (s*=1011)", phi_true, n)

    # Now run mismatched cases
    for mismatch_s, label in mismatched_targets:
        phi_prover = make_noisy_parity_phi(n, mismatch_s, eta)
        sim_prover = MoSSimulator(n=n, phi=phi_prover, seed=42)
        run_protocol_and_report(
            f"Mismatch: prover uses s*={label}",
            phi_true, n,
            prover_simulator=sim_prover,
        )


# ---------------------------------------------------------------------------
# Experiment 2: Noisy Prover
# ---------------------------------------------------------------------------

def experiment_noisy_prover():
    print_header("EXPERIMENT 2: Noisy Prover  (data-access noise)")
    print("""
    The prover uses the correct target parity but with oracle-level noise η.
    phi_noisy(x) = (1-2η)*phi(x) + η  →  Fourier coefficients scale by (1-2η).
    We sweep η and observe the accept→reject transition.

    Theoretical attenuation:
      |φ̂_noisy(s)|² = (1-2η)² |φ̂(s)|²
      At η=0.15 (base noise), effective combined noise is higher.
    """)

    n = 4
    base_eta = 0.15
    target_s = 0b1011
    phi_true = make_noisy_parity_phi(n, target_s, base_eta)

    # True Fourier weight for reference
    sim_ref = MoSSimulator(n=n, phi=phi_true, seed=42)
    true_fc = sim_ref.fourier_coefficient(target_s)
    print(f"  True φ̂({target_s:04b}) = {true_fc:+.4f},  |φ̂|² = {true_fc**2:.4f}")

    # Sweep additional oracle-level noise applied ON TOP of the base distribution
    noise_rates = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]

    print(f"\n{'η_oracle':>10}  {'(1-2η)²':>8}  {'expect |φ̂|²':>14}  {'decision':>10}")
    print("-" * 55)

    for extra_eta in noise_rates:
        # Create a noisy simulator: the prover's MoS sampling uses
        # phi_effective = (1-2*extra_eta) * phi_true + extra_eta
        sim_noisy = MoSSimulator(n=n, phi=phi_true, seed=42, noise_rate=extra_eta)

        # Theoretical expected attenuation
        attenuation = (1 - 2 * extra_eta) ** 2
        expected_weight = attenuation * true_fc**2

        sim_true = MoSSimulator(n=n, phi=phi_true, seed=42)
        protocol = MoSProtocol(
            simulator=sim_true,
            phi=phi_true,
            seed=42,
            prover_simulator=sim_noisy,
        )
        transcript = protocol.run(
            epsilon=0.1,
            delta=0.05,
            prover_copies=60_000,
            verifier_samples_per_coeff=20_000,
        )

        decision = transcript.verifier_result.decision.value
        print(f"  {extra_eta:>8.2f}  {attenuation:>8.4f}  {expected_weight:>14.6f}  {decision:>10}")

        if extra_eta in (0.0, 0.20, 0.50):
            vr = transcript.verifier_result
            print(f"           ↳ Prover list: {[format(s, f'0{n}b') for s in transcript.prover_list]}")
            print(f"           ↳ Est. weight: {vr.estimated_list_weight:.6f}  "
                  f"interval: [{protocol.weight_interval[0]:.4f}, {protocol.weight_interval[1]:.4f}]")
            print(f"           ↳ Reason: {vr.reason}")


# ---------------------------------------------------------------------------
# Experiment 3: Gate-Level Noise
# ---------------------------------------------------------------------------

def experiment_gate_noise():
    print_header("EXPERIMENT 3: Gate-Level Noise (Qiskit NoiseModel)")
    print("""
    The prover operates on the correct data but hardware noise degrades the
    quantum Fourier sampling measurements.
    We apply depolarizing error to single-qubit (h, x) and two-qubit (cx) gates.
    The prover uses mode='batched' (circuit execution) to support noise models.
    """)

    n = 4
    base_eta = 0.15
    target_s = 0b1011
    phi_true = make_noisy_parity_phi(n, target_s, base_eta)
    
    error_rates = [0.0, 0.01, 0.03, 0.05, 0.10]
    
    # We use a smaller number of copies to keep circuit simulation fast
    prover_copies = 20_000
    verifier_samples = 20_000
    
    print(f"\n{'p_error':>8}  {'decision':>10}")
    print("-" * 35)
    
    for p in error_rates:
        # Build noise model
        nm = NoiseModel()
        if p > 0:
            nm.add_all_qubit_quantum_error(depolarizing_error(p, 1), ['h', 'x', 'id'])
            nm.add_all_qubit_quantum_error(depolarizing_error(p * 1.5, 2), ['cx'])
            
        noisy_backend = AerSimulator(noise_model=nm)
        
        sim_true = MoSSimulator(n=n, phi=phi_true, seed=42)
        
        protocol = MoSProtocol(
            simulator=sim_true,
            phi=phi_true,
            seed=42,
        )
        
        transcript = protocol.run(
            epsilon=0.1,
            delta=0.05,
            prover_copies=prover_copies,
            verifier_samples_per_coeff=verifier_samples,
            prover_mode="batched",
            batch_size=200,          # Kwarg passed to _run_fourier_sampling
            backend=noisy_backend    # Kwarg passed to sample_hadamard_measure
        )

        decision = transcript.verifier_result.decision.value
        print(f"  {p:>8.3f}  {decision:>10}")
        
        if p in (0.0, 0.05, 0.10):
            vr = transcript.verifier_result
            print(f"           ↳ Prover list: {[format(s, f'0{n}b') for s in transcript.prover_list]}")
            print(f"           ↳ Est. weight: {vr.estimated_list_weight:.6f}  interval: [{protocol.weight_interval[0]:.4f}, {protocol.weight_interval[1]:.4f}]")
            print(f"           ↳ Reason: {vr.reason[:100]}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║       Dishonest Prover Experiments — MoS Protocol              ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    experiment_oracle_mismatch()
    experiment_noisy_prover()
    experiment_gate_noise()

    print("\n\nDone.")
