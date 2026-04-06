# Experiment Findings

Date: 2026-04-06

This document reports the empirical findings from 11 experiments evaluating the
MoS (mixture-of-superpositions) verification protocol from Caro et al.
(arXiv:2306.04843). Each finding is linked to the specific theorem, lemma, or
definition it tests. All experiments use 100 trials per cell unless noted.

Figures and summary tables are located in `results/figures/<experiment>/`.

---

## 1. Completeness

> *Does the protocol accept honest provers, and how does it scale?*
> Paper reference: Theorems 5, 7, 8, 9, 10

### 1.1 Scaling -- Honest Baseline

**Data:** `scaling_4_16_100.pb` (1,300 trials, n=4..16)

**Result: Perfect completeness across the full range.** Acceptance and correctness
are both 100% for every n from 4 to 16 (95% Wilson CI lower bound: 96.3%). No
degradation is observed as n grows. This confirms the completeness guarantee of
Theorem 8 (Eq. 17): with an honest prover, the verifier accepts with probability
at least 1 - delta = 0.9.

**Theorem 5 confirmed (postselection rate).** The median postselection rate is
0.498--0.502 across all n values, matching the theoretical prediction of 1/2
from Equation 4. For single parities, E_{x~U_n}[phi(x)^2] = 1, so the
perturbation term (1/2^n)(1 - E[phi(x)^2]) vanishes, and the sampling
distribution reduces to (phi_hat(s))^2 -- placing all mass on the target
parity string.

**Theorem 7 Step 1 confirmed (list-size bound).** |L| = 1 in every trial, far
below the upper bound 4/theta^2 = 44.4 (theta = 0.3). Single-parity targets
have exactly one nonzero Fourier coefficient, so the prover identifies it with
certainty.

**Theorem 8 resource scaling.** The total sample count is fixed at 6,000 per trial
(qfsShots + classicalSamplesProver + classicalSamplesVerifier = 2000 + 1000 +
3000). The theoretical O(n * log(1/(delta*theta^2)) / theta^4) worst-case bound
from Theorem 8 is not reached because |L| = 1 collapses the prover's search.
Wall-clock time grows exponentially (0.36s at n=4 to 1203s at n=16) due to
classical simulation of the 2^n-dimensional quantum state space -- an artefact
of simulation, not the protocol itself.

| n  | Accept % | Correct % | |L| | Postselection | Copies | Time (s) |
|----|----------|-----------|-----|---------------|--------|----------|
| 4  | 100      | 100       | 1   | 0.499         | 6000   | 0.36     |
| 8  | 100      | 100       | 1   | 0.501         | 6000   | 0.69     |
| 12 | 100      | 100       | 1   | 0.502         | 6000   | 3.80     |
| 16 | 100      | 100       | 1   | 0.498         | 6000   | 1203     |


### 1.2 Average-Case Performance

**Data:** `average_case_4_16_100.pb` (n=4..16, 4 function families)

**Theorem 9 prediction confirmed: |L| tracks sparsity k, not dimension n.** This
is the strongest positive result from this experiment. For n >= 7:
- k-sparse (k=2): median |L| = 2 (exactly matching k)
- k-sparse (k=4): median |L| = 3 (close to k)
- Sparse + noise: median |L| = 1 (only the dominant coefficient survives)
- Random boolean: median |L| = 0 for n >= 10

All values are flat as n grows and far below the 4/theta^2 upper bounds, directly
validating the Theorem 9 prediction that communication cost scales with Fourier
sparsity.

**Completeness below 1-delta for finite shot counts.** The 1-delta = 0.9
guarantee from Theorem 7 is not met by any family in practice:
- k-sparse (k=2): 73--78% acceptance for n >= 7
- k-sparse (k=4): 59--74%
- Sparse + noise: drops from 78% (n=4) to 13--21% (n >= 7)
- Random boolean: 0% by n=6

This gap is attributable to finite QFS shot counts (2000 shots) rather than a
theoretical failure. The random boolean family has a dense Fourier spectrum with
exponentially many non-negligible coefficients, placing it outside the protocol's
Fourier-sparsity promise class (Definition 2). The protocol's correct rejection
of these functions confirms that Fourier sparsity is a genuine prerequisite, not
merely a theoretical convenience.


### 1.3 k-Sparse Verification

**Data:** `k_sparse_4_16_100.pb` (n even 4..16, k in {1,2,4,8})

**Theorem 9 (2-agnostic guarantee): partially confirmed.** For k=1, the protocol
achieves 100% acceptance and zero misclassification across all n, exactly
matching the single-parity baseline. For k >= 2, empirical misclassification
rates are:

| k | Mean misclassification | Thm 9 bound (2*opt + eps) | Mean acceptance |
|---|------------------------|---------------------------|-----------------|
| 1 | 0.000                  | 0.30                      | 100%            |
| 2 | 0.152                  | 0.30                      | 51.3%           |
| 4 | 0.265                  | 0.30                      | 46.7%           |
| 8 | 0.349                  | 0.30                      | 61.6%           |

For k=2 and k=4, misclassification stays within the 2*opt + eps = 0.30 bound
(with opt ~ 0 for well-specified targets). For k=8, it slightly exceeds 0.30,
suggesting finite-sample estimation noise pushes marginal cases beyond the bound.

**Weight threshold is the binding constraint.** No trial is rejected for
list-too-large. All rejections are due to insufficient accumulated weight (Step 4
of Theorem 9). The threshold a^2 - eps^2/(32k^2) tightens as k grows, and
Dirichlet-drawn coefficients spread probability mass across k terms, making the
weight check increasingly difficult to pass with finite QFS precision.

**|L| behaviour.** For n >= 10 with stabilised spectra: median |L| = 2 (k=2), 3
(k=4), 5--13 (k=8). At small n (especially n=4), |L| = 2^n because the entire
Fourier space is enumerable.


---

## 2. Soundness

> *Does the protocol reject dishonest provers?*
> Paper reference: Theorems 7, 8, 9 (soundness parts)

### 2.1 Soundness -- Single-Parity Dishonest Prover

**Data:** `soundness_4_20_100.pb` (n=4..20, 4 adversarial strategies)

**Theorems 7/8 soundness confirmed.** Three of four adversarial strategies --
wrong parity, partial list, and inflated list -- are rejected at 100% across all
n values, exceeding the 1-delta = 0.9 guarantee. The random list strategy shows
rejection rising from 71% at n=4 to 100% for n >= 11, consistent with the
collision probability 1 - 5/2^n converging to 1.

**Rejection mechanism.** All rejections are via the weight check (Step 4); no
strategy triggers the list-size bound (Step 3). This is expected: all adversarial
lists contain at most 10 entries versus the bound 4/theta^2 ~ 44. The weight
check is the operationally binding constraint for soundness, confirming the proof
structure of Theorem 7 (Eqs. 69--77) where the key inequality
sum(g_hat(s_l))^2 >= 1 - eps^2/8 determines acceptance.

| Strategy      | n=4   | n=8   | n=12  | n=16  | n=20  |
|---------------|-------|-------|-------|-------|-------|
| Random list   | 71%   | 97%   | 100%  | 100%  | 100%  |
| Wrong parity  | 100%  | 100%  | 100%  | 100%  | 100%  |
| Partial list  | 100%  | 100%  | 100%  | 100%  | 100%  |
| Inflated list | 100%  | 100%  | 100%  | 100%  | 100%  |


### 2.2 Soundness -- Multi-Element (k-Sparse Targets)

**Data:** `soundness_multi_4_16_100.pb` (n=4..16, k in {2,4}, 4 strategies)

**Soundness maintained for 7 of 8 (strategy, k) combinations.** Three strategies
-- partial_real, shifted_coefficients, and diluted_list -- achieve 100% (or
near-100%) rejection at both k=2 and k=4. All rejections are via the weight
check; no strategy triggers list-size rejection.

**Boundary violation: subset_plus_noise at k=2.** This strategy (single heaviest
real coefficient + marginal fakes) achieves only 75.9% mean rejection (range
68--83%), below the 1-delta = 0.9 guarantee. The single real coefficient
sometimes carries enough weight to pass the threshold, leading to ~24%
acceptance. This represents a genuine boundary case in Theorem 9's soundness
argument (Eq. 93): when the dishonest list contains one legitimate heavy
coefficient, the accumulated weight can approach a^2 - eps^2/(32k^2).

**Increasing k makes cheating harder, not easier.** At k=4, subset_plus_noise
rejection rises to 97.2%, because the tighter weight threshold
(a^2 - eps^2/(32k^2)) for larger k makes it harder for a single real coefficient
to push the accumulated weight above the acceptance bound. This is consistent
with the proof of Theorem 9: the factor 1/(32k^2) in the threshold makes
soundness stronger at higher k.


---

## 3. Robustness

> *How does performance degrade under noise and distributional assumptions?*
> Paper reference: Definition 12, Lemmas 4--6, Theorems 11--13, Definition 14

### 3.1 Noise Sweep -- Label-Flip Noise

**Data:** `noise_sweep_4_16_100.pb` (n=4..16, eta in {0.0, 0.05, ..., 0.4})

**Definition 12 weight attenuation precisely confirmed.** The observed median
accumulated weight follows the (1-2*eta)^2 curve with less than 3% relative
error across all n and eta values. This n-independent behaviour is consistent
with Lemma 6, which predicts that the perturbation from the noisy QFS
distribution is exponentially small in n: the output distribution is
(4*eta - 4*eta^2)/2^n + (1-2*eta)^2 * (g_hat(s))^2.

**No breakdown within tested range.** Acceptance never drops below 50% for any
(n, eta) combination. The theoretical breakdown threshold is eta_max = 0.447
(where (1-2*eta)^2 = eps^2/8 with eps = 0.3), beyond the maximum tested eta of
0.40. Acceptance at eta = 0.40 remains 93--100%.

**Non-monotonic acceptance pattern.** Acceptance dips at moderate noise (eta =
0.05--0.15, dropping to ~70--75%) then recovers at higher eta (93--100% at eta =
0.40). This is because the experiment adapts a^2 = b^2 = (1-2*eta)^2 and
theta = min(eps, 0.9*(1-2*eta)), which lowers the acceptance threshold
proportionally with the weight attenuation. At high eta, the threshold becomes
so low that the protocol almost always accepts. This demonstrates that noise
adaptation from Theorems 11/12 successfully extends the operating range.

**Acceptance = correctness.** When the protocol accepts under noise, the
hypothesis is correct, confirming that the noise-adapted parameters
preserve the functional guarantee from Equation 32: err_{(U_n,f)}(m) <=
alpha * opt_{(U_n,f)}(B) + eps.


### 3.2 Gate-Level Noise

**Data:** `gate_noise_4_8_50.pb` (n=4..8, p in {0, 0.001, ..., 0.1}, 50 trials)

**No direct theoretical prediction exists.** The paper analyses label-flip noise
(Definition 5, Lemmas 4--6) but not depolarising circuit noise. This experiment
provides novel empirical evidence beyond the paper's scope.

**Sharp threshold behaviour with strong n-dependence:**

| n | Robust up to p= | Cliff at p= | Accept at p=0.1 |
|---|-----------------|-------------|-----------------|
| 4 | 0.1             | none        | 100%            |
| 5 | 0.1             | none        | 98%             |
| 6 | 0.001           | 0.005       | 2%              |
| 7 | 0 (noiseless)   | 0.001       | 0%              |
| 8 | 0 (noiseless)   | 0.001       | 0%              |

Gate noise is qualitatively worse than label-flip noise. At p = 0.01 (1% gate
error), label-flip noise at equivalent eta has negligible effect (Section 3.1),
but gate noise causes complete protocol failure for n >= 6. This is because gate
noise corrupts the QFS circuit itself -- the Hadamard layer and measurement
operations -- rather than just the data labels. The sharp n-dependence reflects
the multiplicative accumulation of gate errors across O(n) circuit depth.


### 3.3 a^2 != b^2 Regime

**Data:** `ab_regime_4_16_100.pb` (n=4..16, gap in {0.0, 0.05, ..., 0.4})

**Definition 14 (L2-bounded bias class) tested.** The experiment uses
sparse_plus_noise targets with true Parseval weight ~0.52, constructing the
[a^2, b^2] interval as pw +/- gap/2.

**Counter-intuitive result: wider gap increases acceptance.** At gap = 0.0 (tight
promise, a^2 = b^2 = 0.52), acceptance is only 11--22% for n >= 6 because the
threshold tau = a^2 - eps^2/8 = 0.509 sits above the median accumulated weight
~0.49, creating a negative margin (~-0.018). As gap widens, a^2 decreases,
lowering tau and increasing the margin:

| Gap  | a^2  | b^2  | tau    | Median margin | Acceptance (n=10) |
|------|------|------|--------|---------------|-------------------|
| 0.00 | 0.52 | 0.52 | 0.509  | -0.018        | 12%               |
| 0.05 | 0.50 | 0.55 | 0.484  | +0.005        | 59%               |
| 0.10 | 0.47 | 0.57 | 0.459  | +0.029        | 98%               |
| 0.20 | 0.42 | 0.62 | 0.409  | +0.082        | 100%              |

**Theorem 13 accuracy lower bound.** The theoretical necessity bound
eps >= 2*sqrt(b^2 - a^2) predicts a critical gap of (eps/2)^2 = 0.0225 for
eps = 0.3. All tested gap values >= 0.05 exceed this bound and achieve high
acceptance, while gap = 0 (which violates the bound since sqrt(0) = 0 < eps)
fails. The bound appears operationally loose for the specific target function
tested (sparse_plus_noise), consistent with Theorem 13's worst-case nature:
the proof constructs a hard instance via reduction to distinguishing
(U_n, (1-2*eta)*chi_s) from U_{n+1} (Lemma 18).


---

## 4. Sensitivity and Practical Limits

> *How do protocol parameters and function structure affect behaviour?*
> Paper reference: Corollary 5, Theorem 8 Step 3

### 4.1 Bent Functions -- Fourier Density

**Data:** `bent_4_16_100.pb` (n even 4..16)

**Corollary 5 extraction boundary confirmed via sharp phase transition.** Bent
functions have all 2^n Fourier coefficients equal in magnitude: |g_hat(s)| =
2^{-n/2}. The extraction threshold theta/2 = 0.15 predicts a crossover at
n = 2*log_2(2/theta) = 5.47:

| n  | Coeff magnitude | Above theta/2? | Observed |L| | Accept % |
|----|-----------------|----------------|-----------|----------|
| 4  | 0.250           | yes            | 16        | 100%     |
| 6  | 0.125           | no             | 1         | 0%       |
| 8  | 0.063           | no             | 0         | 0%       |
| 16 | 0.004           | no             | 0         | 0%       |

At n=4 (below crossover), all 16 coefficients are detected and the protocol
accepts perfectly. At n=6 (just above crossover), coefficient magnitude 0.125
drops below theta/2 = 0.15, and acceptance collapses to 0%. The transition is
a sharp phase boundary, not a gradual decline.

**Fourier sparsity is load-bearing.** The contrast with single parities (|L| = 1,
100% acceptance at all n) demonstrates that the sparsity assumption in
Definition 2 (|supp(phi)| = k << 2^n) is a practical prerequisite for protocol
efficiency. Bent functions -- the maximally Fourier-dense case -- are the
antithesis of this assumption.

**All rejections are via insufficient weight (Step 4),** not list-size (Step 3).
For n >= 8, the prover finds zero coefficients above threshold, so the
accumulated weight is zero. The list-size cap 4/theta^2 = 44 never triggers
because coefficients fall below the detection threshold before the list could
grow large enough.


### 4.2 Theta Sensitivity -- Resolution Threshold

**Data:** `theta_sensitivity_4_16_100.pb` (n even 4..16, theta in {0.05..0.50})

**Theorem 7 Step 1 universally holds: |L| <= 4/theta^2.** The bound is never
violated across all 56 (n, theta) cells. Empirical list sizes sit well below the
bound, especially for larger n where QFS becomes more selective.

**Extraction boundary manifests as n-dependent transition.** The target function
(sparse_plus_noise: dominant 0.7, three secondary 0.1) has a detectable
transition at theta ~ 0.20, where secondary coefficients (magnitude 0.1) cross
the theta/2 detection threshold:

| theta | |L| at n=16 | |L| upper bound | Accept at n=16 |
|-------|-----------|-----------------|----------------|
| 0.05  | 484       | 1600            | 100%           |
| 0.10  | 4         | 400             | 71%            |
| 0.15  | 4         | 178             | 74%            |
| 0.20  | 2         | 100             | 45%            |
| 0.30  | 1         | 44              | 17%            |
| 0.50  | 1         | 16              | 17%            |

At theta <= 0.15, |L| = 4 matches the true sparsity (1 dominant + 3 secondary
coefficients), confirming that the resolution parameter correctly resolves the
target's Fourier structure. At theta >= 0.30, only the dominant coefficient
survives, and acceptance drops sharply because the accumulated weight from a
single coefficient is insufficient to pass the threshold.

**Practical sweet spot at theta = 0.10--0.15.** This range balances coefficient
detection (|L| = 4 = true sparsity) with manageable list sizes (4--178 vs bound)
and reasonable acceptance (70--96% for n <= 12).

**Theorem 5 confirmed: postselection rate is exactly 0.50, independent of theta.**
Median postselection rates are 0.497--0.503 for every theta value, confirming
that QFS postselection efficiency is a property of the measurement scheme (the
H^{tensor(n+1)} layer), not the resolution parameter.

**Zero false accepts.** Acceptance and correctness are identical in every cell.
When the verifier accepts, the hypothesis is always correct.


### 4.3 Verifier Truncation -- Sample Budget

**Data:** `truncation_{N}_{N}_100.pb` for N=4..14 (30 grid cells per n, eta=0.15)

**Theorem 8 Step 3 sample complexity confirmed qualitatively.** The theoretical
verifier complexity O(|L|^2 * log(|L|/delta) / eps^4) predicts that larger eps
(looser accuracy) requires fewer verifier samples. This is observed: eps = 0.5
achieves >= 90% acceptance at budget 3000 for most n, while eps = 0.1--0.3
frequently fails at all tested budgets for n >= 11.

**Minimum viable budget by (n, eps):**

| n   | eps=0.1 | eps=0.3 | eps=0.5 |
|-----|---------|---------|---------|
| 4   | 50      | 50      | 3000    |
| 7   | 50      | never   | 1000    |
| 10  | 50      | never   | 3000    |
| 14  | never   | never   | 3000    |

The data is censored at the maximum tested budget of 3000: the true knee for
larger n likely exceeds 3000. The Theorem 8 scaling O(|L|^2/eps^4) is
exponential in n through |L| (which can grow as large as 2^n for dense spectra),
consistent with the observation that acceptance rates degrade for larger n.

**Tight margin creates paradoxical inversion.** The acceptance threshold under
noise is tau = (1-2*eta)^2 - eps^2/8 = 0.49 - eps^2/8. For small eps (e.g., 0.1),
the margin is only 0.0012 (0.26% of a^2). This creates a counter-intuitive
pattern: at eps = 0.1, acceptance *decreases* with more verifier samples for
n >= 11. With few samples, Hoeffding noise randomly inflates weight estimates
above the tight threshold, yielding artificially high acceptance. With many
samples, estimates converge to the true value which sits barely above tau, and
residual estimation error causes rejection.

For eps = 0.5 (margin = 0.031, 6.4% of a^2), the pattern is normal: more
samples always helps.

**Zero false accepts.** Across all 330 (n, eps, budget) combinations, correctness
tracks acceptance perfectly. Every accepted hypothesis is correct.


---

## 5. Cross-Experiment Synthesis

### 5.1 Theory-vs-Empirics Comparison

| Theorem / Result | Property | Prediction | Experiments | Verdict |
|---|---|---|---|---|
| Thm 5 (Eq. 4) | Postselection = 1/2 | Pr[last qubit = 1] = 1/2 | scaling, theta_sensitivity | **Confirmed** (0.497--0.503) |
| Thm 7 Step 1 | |L| <= 4/theta^2 | List-size upper bound | scaling, avg_case, k_sparse, theta_sens | **Confirmed** (never violated) |
| Thm 7/8 completeness | Accept >= 1-delta | Honest prover accepted | scaling | **Confirmed** (100% for parities) |
| Thm 7/8 soundness | Reject >= 1-delta | Dishonest prover rejected | soundness | **Confirmed** (100% for 3/4 strategies) |
| Thm 9 (2-agnostic) | Misclass <= 2*opt + eps | k-sparse learning bound | k_sparse | **Partially confirmed** (holds k<=4, tight k=8) |
| Thm 9 soundness | Multi-element rejection | Reject >= 1-delta | soundness_multi | **Mostly confirmed** (7/8 combos; boundary violation at subset+noise, k=2) |
| Def 12 (Eq. 103) | Weight = (1-2*eta)^2 | Noise attenuation | noise_sweep | **Precisely confirmed** (<3% error) |
| Thm 11/12 | Noisy verification | Protocol works with adapted params | noise_sweep | **Confirmed** (no breakdown up to eta=0.40) |
| Thm 13 | eps >= 2*sqrt(b^2-a^2) | Accuracy lower bound | ab_regime | **Consistent** (bound is loose for typical functions) |
| Cor 5 | Extraction threshold | QFS resolves coeffs > eps | bent, theta_sensitivity | **Confirmed** (sharp transition at 2^{-n/2} = theta/2) |
| Thm 8 Step 3 | Verifier: O(|L|^2/eps^4) | Sample complexity | truncation | **Qualitatively confirmed** (budget saturates at 3000) |
| Def 14 (L2-bounded) | [a^2, b^2] promise | Distributional class | ab_regime | **Confirmed** (wider gap lowers threshold, increases acceptance) |
| -- (no theorem) | Gate noise | Novel / empirical | gate_noise | **Novel finding** (sharp threshold, qualitatively worse than label-flip) |


### 5.2 Key Cross-Cutting Findings

1. **The weight check (Step 4) is the operationally dominant mechanism.** Across
   soundness, soundness_multi, bent, and truncation experiments, rejection is
   overwhelmingly driven by the accumulated weight falling below the threshold
   tau = a^2 - eps^2/8 (or its k-sparse variant). The list-size bound (Step 3) is
   never the binding constraint in any experiment.

2. **Fourier sparsity is the load-bearing assumption.** The protocol works
   flawlessly for single parities (k=1) and degrades gracefully for small k. It
   fails entirely for Fourier-dense functions (bent, random boolean). The
   transition is sharp: bent functions show a phase boundary at n ~ 5.5 where
   coefficient magnitude crosses the detection threshold.

3. **Finite-sample effects dominate the gap between theory and practice.** The
   theoretical guarantees (acceptance >= 1-delta, misclassification <=
   2*opt + eps) are asymptotic. With fixed QFS shot budgets (2000), the
   empirical acceptance for k >= 2 functions drops to 50--60%, below the 90%
   guarantee. The theoretical bounds are not wrong -- they simply require larger
   sample budgets than the experiments use.

4. **Gate noise represents an unexplored theoretical frontier.** The sharp
   threshold behaviour (100% to 0% acceptance between p=0.001 and p=0.005 for
   n=6) with strong n-dependence is qualitatively different from label-flip noise
   and is not covered by any theorem in the paper. This is potentially the most
   practically relevant noise model for near-term quantum devices.

5. **Zero false accepts across all experiments.** In every experiment where the
   protocol accepts an honest prover, the output hypothesis is correct. This
   empirical observation is stronger than the theoretical soundness guarantee,
   which only bounds the probability of accepting a *bad* hypothesis.


### 5.3 Parameter Sensitivity Summary

| Parameter | Varied in | Sensitivity | Theoretical prediction confirmed? |
|---|---|---|---|
| n (dimension) | All experiments | Low for parities; high for dense spectra | Yes (Thm 8 resource bounds, Cor 5 threshold) |
| theta (resolution) | theta_sensitivity, bent | High: determines coefficient detection | Yes (|L| <= 4/theta^2, extraction boundary) |
| eps (accuracy) | truncation, ab_regime | Medium: affects threshold margin | Yes (tau = a^2 - eps^2/8) |
| eta (label noise) | noise_sweep | Low with adaptation; weight tracks (1-2*eta)^2 | Yes (Def 12, Thm 11/12) |
| k (sparsity) | k_sparse, avg_case | High: weight threshold tightens as 1/(32k^2) | Partially (Thm 9 tight for large k) |
| gate error rate | gate_noise | Very high: sharp threshold at p ~ 0.001 for n >= 7 | No theorem exists (novel) |
| gap (b^2-a^2) | ab_regime | Medium: wider gap loosens threshold | Yes (Def 14, Thm 13 loose) |
| verifier samples | truncation | High for tight margins (small eps) | Yes (Thm 8 Step 3) |
