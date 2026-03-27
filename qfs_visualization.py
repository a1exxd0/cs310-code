"""
Visualization of Approximate Quantum Fourier Sampling (QFS)

This script compares the true squared Fourier coefficients of a boolean function phi
against the empirical probability distribution obtained by simulating the
Hadamard+measure circuit on the Mixture-of-Superpositions (MoS) state.
"""

import numpy as np
import matplotlib.pyplot as plt
from mos.mos_simulator import MoSSimulator


def make_target_phi(n: int, target_s: int, eta: float) -> np.ndarray:
    """Create a noisy parity distribution."""
    phi = np.zeros(2**n)
    for x in range(2**n):
        parity = bin(target_s & x).count('1') % 2
        phi[x] = (1 - eta) * parity + eta * (1 - parity)
    return phi


def main():
    n = 5
    target_s = 0b1011
    eta = 0.15
    shots = 50000

    print(f"Creating MoS simulator for n={n} qubits...")
    phi_true = make_target_phi(n, target_s, eta)
    sim = MoSSimulator(n=n, phi=phi_true, seed=42)

    print("Computing true Fourier coefficients...")
    true_probs = np.zeros(2**n)
    for s in range(2**n):
        # The true MoS probability of measuring s is |hat{phi}(s)|^2
        coeff = sim.fourier_coefficient(s)
        true_probs[s] = coeff**2

    print(f"Running QFS circuit simulation with {shots} shots...")
    rng = np.random.default_rng(42)
    counts = sim.sample_hadamard_measure(shots=shots, mode="batched", batch_size=1000, use_oracle=True, rng=rng)
    
    # Analyze the raw counts to extract conditional probabilities Pr[s | last=1]
    analysis = sim.analyze_counts(counts)

    # Convert counts to empirical probabilities
    empirical_probs = np.zeros(2**n)
    for s, p in analysis['s_distribution'].items():
        empirical_probs[s] = p

    # Prepare data for plotting
    x = np.arange(2**n)
    labels = [format(s, f"0{n}b") for s in x]
    
    # Sort by true probability for better visualization
    sort_idx = np.argsort(true_probs)[::-1]
    x_sorted = np.arange(2**n)
    
    true_sorted = true_probs[sort_idx]
    empirical_sorted = empirical_probs[sort_idx]
    labels_sorted = [labels[i] for i in sort_idx]

    # Display only top 8 if n > 3 to keep it readable, but here we just show all 16
    print("Generating plot...")
    plt.figure(figsize=(12, 6))
    width = 0.35

    plt.bar(x_sorted - width/2, true_sorted, width, label='True $|\\hat{\\phi}(s)|^2$', color='#1f77b4', edgecolor='black')
    plt.bar(x_sorted + width/2, empirical_sorted, width, label=f'Empirical (Shots={shots})', color='#ff7f0e', edgecolor='black', alpha=0.8)

    plt.title(f"Quantum Fourier Sampling Distribution (n={n}, Noisy Parity s*={format(target_s, f'0{n}b')})", fontsize=14)
    plt.xlabel('Fourier basis state $s$', fontsize=12)
    plt.ylabel('Probability', fontsize=12)
    plt.xticks(x_sorted, labels_sorted, rotation=45)
    plt.legend(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    output_file = "qfs_histogram.png"
    plt.savefig(output_file, dpi=300)
    print(f"✅ Plot saved successfully to {output_file}")


if __name__ == "__main__":
    main()
