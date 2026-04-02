# Dissertation Chapter 5: Experiment Results Presentation Plan

## Context

The dissertation implements and evaluates the MoS verification protocol from Caro et al. (arXiv:2306.04843). Chapter 5 needs to present results from 7 experiments + baseline in a way that is clear, visually compelling, and ties empirical findings back to the paper's theoretical predictions. Currently there is no plotting code — only ASCII summary tables.

This plan covers: (1) how to structure the chapter narrative, (2) what figure/table to produce for each experiment, (3) what additional experiment runs would strengthen the results, and (4) a concrete implementation path for the plotting code.

---

## Chapter Narrative Structure

The results should tell a story in four acts:

1. **"The protocol works"** — Honest baseline + Scaling sweep (Exps 4, baseline)
2. **"It rejects cheaters"** — Soundness / oracle mismatch (Exp 1)
3. **"It degrades gracefully under noise"** — Noise sweep (Exp 2), and optionally gate-level noise (Exp 3)
4. **"Practical limits and edge cases"** — Bent functions (Exp 5), verifier truncation (Exp 6), average-case (Exp 7)

---

## Per-Experiment Presentation

### 0. Honest Baseline (Section 5.2)

**Data source:** Extract eta=0.0 rows from `noise_sweep_4_13_24.pb` and select n from `scaling_4_16_24.pb`.

| Visualisation | Type | What it shows |
|---|---|---|
| **Table 5.1** | Summary table | n in {4, 8, 12, 16}: acceptance rate, hypothesis correctness, median \|L\|, postselection rate, median wall-clock time |
| **Figure 5.1** | Bar chart (small, 4 bars) | Postselection rate vs n — compare to theoretical 1/2 (Theorem 5, Eq. 4) |

**Key claim to support:** Postselection rate ~ 0.5, acceptance ~ 100%, correctness ~ 100% for honest single-parity targets.

---

### 1. Oracle Mismatch — Soundness (Exp 1, Section 5.3)

**Data source:** `soundness_4_16_50.pb`

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.2** | Grouped bar chart | Rejection rate (y) by dishonest strategy (x-groups), with bars for each n in {4, 8, 12, 16}. Four strategy clusters: `random_list`, `wrong_parity`, `partial_list`, `inflated_list`. |
| **Table 5.2** | Compact table | Per-strategy, per-n rejection rate with 95% CI (Wilson interval over 50 trials) |

**Key claim:** Verifier rejects all four dishonest strategies with probability >= 1-delta, confirming the soundness property of Theorems 7-8. The `random_list` and `wrong_parity` strategies should be rejected ~100%; `partial_list` and `inflated_list` test the weight-check step (Step 4 in the protocol).

---

### 2. Noisy Prover — Oracle Noise Sweep (Exp 2, Section 5.3)

**Data source:** `noise_sweep_4_13_24.pb`

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.3** | Heatmap (n x eta) | Acceptance rate as colour intensity. Rows = n in {4,6,8,10,12,13}, columns = eta in {0.0, 0.05, ..., 0.4}. |
| **Figure 5.4** | Line plot with theoretical overlay | Two panels (n=4, n=12): acceptance rate (solid) and correctness (dashed) vs eta. Overlay vertical line at Ma-Su-Deng threshold eta <= 1/(10*theta). Shade the "theoretically safe" region green. |
| **Table 5.3** | Small table | Empirical breakdown point (eta at which acceptance drops below 50%) vs theoretical threshold, for each n. |

**Key claim:** Protocol remains robust up to moderate noise, degrading smoothly. Empirical breakdown roughly matches the Ma-Su-Deng threshold. At high eta, the attenuated Fourier weight (1-2*eta)^2 causes the weight check to fail, exactly as Theorem 11/12 predicts.

**Suggested additional run:** Currently n goes up to 13. Running at n=16 (matching scaling sweep) would provide a consistent comparison point. ~24 trials at n=14,16 per eta level.

---

### 3. Gate-Level Noise (Exp 3) — NOT YET IMPLEMENTED

**What's needed for the chapter:**
- Even a small pilot (n=4, n=6) with depolarising error rates p in {0.001, 0.005, 0.01, 0.02, 0.05} would be valuable.
- This is *novel* — Caro et al. only analyse label-flip noise. The result is inherently empirical.

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.5** | Line plot | Acceptance rate vs depolarising error rate p, for n=4 and n=6. Compare with the label-flip curve from Exp 2 at equivalent effective noise. |
| **Table 5.4** | Comparison table | Side-by-side: gate-noise breakdown point vs label-flip breakdown point. |

**Recommendation:** This experiment is medium effort but high dissertation value (original contribution). Prioritise implementing it, even at small n.

---

### 4. Scaling Sweep (Exp 4, Section 5.4)

**Data source:** `scaling_4_16_24.pb`

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.6** | Dual-axis line plot | Primary y-axis: acceptance rate and correctness vs n. Secondary y-axis (log scale): median wall-clock time vs n. x-axis: n in {4,6,8,10,12,14,16}. |
| **Figure 5.7** | Line plot (log-linear) | Median \|L\| (list size) vs n. Overlay theoretical upper bound \|L\| <= 4/theta^2 from Theorem 7. For single parities, \|L\| should be O(1). |
| **Figure 5.8** | Line plot (log scale y) | Total QFS copies used vs n. Compare to theoretical O(n * log(1/delta*theta^2) / theta^4) from Theorem 8. Fit a curve to assess empirical scaling exponent. |
| **Table 5.5** | Summary table | Per-n: acceptance %, correctness %, median \|L\|, median copies, median time. |

**Key claim:** Protocol scales polynomially. Acceptance and correctness remain high as n grows. Empirical resource usage is well below theoretical worst-case bounds.

---

### 5. Fourier-Dense / Bent Functions (Exp 5, Section 5.4)

**Data source:** `bent_4_16_24.pb`

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.9** | Line plot (log scale y) | Median \|L\| vs n for bent functions. Overlay the theoretical prediction \|L\| = 2^(n/2) (since all \|g_hat(s)\| = 2^(-n/2) >= theta/2 when theta is small). Compare with the single-parity \|L\| from Exp 4 on the same axes. |
| **Figure 5.10** | Grouped bar chart | Acceptance rate: bent vs single-parity (from Exp 4) at each n. Shows worst-case degradation. |
| **Table 5.6** | Table | Per-n: \|L\|, acceptance rate, wall-clock time. Theoretical \|L\| vs observed \|L\|. |

**Key claim:** Bent functions represent the worst case for communication complexity (\|L\| grows exponentially). The protocol still functions but resource usage grows as predicted, demonstrating the Fourier-sparsity assumption is load-bearing.

---

### 6. Verifier Truncation (Exp 6, Section 5.4)

**Data source:** `truncation_6_6_24.pb`

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.11** | Heatmap | Acceptance rate over the 2D grid: epsilon (x) x verifier_samples (y). Colour scale from red (0%) to green (100%). |
| **Figure 5.12** | Heatmap | Hypothesis correctness over the same grid. |
| **Figure 5.13** | Line plot | Fix epsilon=0.3, plot acceptance rate and correctness vs verifier_samples. Identify the "knee" — the minimum sample budget for reliable verification. |

**Suggested additional runs (high priority):**
- Run at n=10 and n=12 to satisfy the plan's "at scaled n" requirement. This is critical — a single n=6 result is insufficient for a "scaling" claim.
- If feasible, also add a true list-truncation mode (verifier only processes a random subset of L) to match the plan description more precisely.

**Key claim:** There is a practical minimum verifier sample budget below which verification breaks down. This budget grows with n, quantifying the verifier's computational cost.

---

### 7. Average-Case Performance (Exp 7) — NOT YET IMPLEMENTED

**What's needed:**
- Random k-sparse functions (k=1,2,4) at n=4..12.
- Measures whether protocol performance degrades for multi-parity targets.

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.14** | Line plot with error bands | Acceptance rate vs n, one line per sparsity level k in {1,2,4}. Shaded 95% CI bands. |
| **Figure 5.15** | Line plot | Median \|L\| vs n, one line per k. Shows how list size grows with spectral complexity. |
| **Table 5.7** | Table | Per-(n,k): acceptance, correctness, \|L\|, time. |

**Recommendation:** Medium priority. If time is short, even k=1 vs k=2 at n=4..10 would add value. This connects to the 2-agnostic bound (Theorem 9) and the open question about whether the factor-of-2 loss materialises.

---

## Summary Figure

| Visualisation | Type | What it shows |
|---|---|---|
| **Figure 5.16** | Multi-panel overview (2x2 or 3x2) | A single "highlight reel" figure combining: (a) scaling acceptance rate, (b) soundness rejection rates, (c) noise heatmap, (d) bent vs parity \|L\| growth. This would be the figure referenced in the abstract/introduction. |

---

## Additional Experiments Recommended

| Priority | Experiment | Effort | Justification |
|---|---|---|---|
| **HIGH** | Truncation at n=10, n=12 | Low (re-run existing code) | Current n=6 only result is insufficient for "scaled regime" claim |
| **HIGH** | Gate-level noise pilot (n=4,6) | Medium (new module) | Novel contribution, distinguishes from pure theory replication |
| **MEDIUM** | Noise sweep at n=14,16 | Low (extend existing) | Consistent n range across experiments |
| **MEDIUM** | Average-case k-sparse (k=1,2,4) | Medium (new module) | Tests 2-agnostic bound, broadens function coverage |
| **LOW** | Honest baseline with GL diagnostics | Low (logging changes) | Plan explicitly requests GL tree depth, nodes explored |

---

## Implementation: Plotting Module

**File:** `experiments/plot.py` (new)

**Dependencies:** `matplotlib`, `seaborn`, `numpy` (add to pyproject.toml)

**Structure:**
```
experiments/plot.py
  load_results(path) -> ExperimentResult     # deserialise .pb
  plot_baseline_table(scaling_pb, noise_pb)   # Table 5.1, Fig 5.1
  plot_soundness(soundness_pb)                # Fig 5.2, Table 5.2
  plot_noise_sweep(noise_pb)                  # Fig 5.3, Fig 5.4, Table 5.3
  plot_scaling(scaling_pb)                    # Fig 5.6, 5.7, 5.8, Table 5.5
  plot_bent(bent_pb, scaling_pb)              # Fig 5.9, 5.10, Table 5.6
  plot_truncation(truncation_pb)              # Fig 5.11, 5.12, 5.13
  plot_summary(all_results)                   # Fig 5.16
  main()  # CLI: uv run python -m experiments.plot [all|scaling|noise|...]
```

**Style:**
- Use `seaborn` with `paper` context and `colorblind` palette for accessibility
- All figures exported as both PDF (for LaTeX) and PNG (for previewing)
- Figure size: single-column (3.5in) and double-column (7in) widths matching typical LaTeX templates
- Consistent axis labels using LaTeX math formatting (`$n$`, `$\eta$`, `$|L|$`)
- Error bars/bands: 95% confidence intervals via bootstrap or Wilson interval

**Output directory:** `results/figures/`
