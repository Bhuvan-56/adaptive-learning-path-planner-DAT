# Week 5 Integrated Evaluation Summary: Closed-Loop Path Planning

## 1. Evaluation Setup & Input Provenance

- **Benchmark Name:** `w5_integrated`
- **Evaluated Cohort:** 200 synthetic learners (paired random seeds)
- **Planning Horizon:** 5 days
- **Daily Study Budget:** 10 minutes
- **Bootstrap Resamples (B):** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `MatchedBKTGenerator` (BKT response dynamics)
- **Runtime Note:** Planning runtimes reported from one machine and one run.

### Arm Configuration Matrix

| Arm | Diagnostic Inputs | Planner Algorithm | Difficulty Stepping | Dynamic Replanning | Spaced Review | Prerequisite Remediation |
|---|---|---|---|---|---|---|
| **adaptive_full** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On (HLR decay baseline) | On (k=2 failures) |
| **static_prerequisite_order** | Initial priors (IRT CAT) | Static Topological Sort (`generate_static_plan`) | Static base | Off | Off | Off |
| **non_adaptive_greedy** | Mastered set ($n < \text{min\_obs} \implies \emptyset$) | Score/duration frontier packing | Static base | Off | Off | Off |
| **non_adaptive_greedy_best_singleton** | Same as non_adaptive_greedy | Frontier packing, then best-singleton fallback (`src.planning.greedy_fallback`) | Static base | Off | Off | Off |
| **ablation_no_diagnostic** | Cold-start priors (p=0.5) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On | On |
| **ablation_no_replan** | Initial priors (IRT CAT) | Static Topological Sort (`generate_static_plan`) | 2-Up / 1-Down staircase | Off | Off | Off |
| **ablation_no_difficulty_step** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | Static base | On | On | On |
| **ablation_no_review** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | Off | On |
| **ablation_no_remediation** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On | Off |

## 2. Primary Arm Performance Results

| Arm | Concepts Mastered [95% CI] | Prereq Violations | Budget Violations | Trace Coverage (%) | No-Plan Results | Runtime p50 (ms) | Runtime p95 (ms) |
|---|---|---|---|---|---|---|---|
| **adaptive_full** | 1.4500 [1.2699, 1.6300] | 0 | 0 | 100.0% | 133 (SCHEDULING_CONSTRAINTS_UNMET:59, CAPACITY_EXCEEDED:74) | 13.868 | 28.652 |
| **static_prerequisite_order** | 1.4300 [1.2550, 1.6150] | 0 | 0 | 100.0% | 0 | 0.543 | 1.267 |
| **non_adaptive_greedy** | 1.4450 [1.2550, 1.6350] | 0 | 0 | 100.0% | 0 | 0.016 | 0.037 |
| **non_adaptive_greedy_best_singleton** | 1.4500 [1.2600, 1.6450] | 0 | 0 | 100.0% | 0 | 0.035 | 0.057 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0200 | [-0.0300, 0.0650] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0050 | [-0.0800, 0.0850] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0150 | [-0.0601, 0.0950] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0050 | [-0.0250, 0.0350] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 1.5450 [1.3700, 1.7201] | -0.0950 [-0.1850, -0.0100] | ablation_no_diagnostic improves on adaptive_full [0.0100, 0.1850] |
| **ablation_no_replan** | 1.4200 [1.2400, 1.6051] | 0.0300 [-0.0150, 0.0700] | no difference shown |
| **ablation_no_difficulty_step** | 1.4500 [1.2699, 1.6300] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.4750 [1.2950, 1.6551] | -0.0250 [-0.0550, 0.0001] | no difference shown |
| **ablation_no_remediation** | 1.4500 [1.2699, 1.6300] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1965 [0.1801, 0.2144] | 0.1931 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1874 [0.1723, 0.2025] | 0.1681 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1965 [0.1801, 0.2144] | 0.1931 | 800 |
| ablation_no_review | 0.1872 [0.1717, 0.2033] | 0.1841 | 800 |
| ablation_no_remediation | 0.1965 [0.1801, 0.2144] | 0.1931 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 137 | 0.1435 | 0.0511 |
| 0.2–0.3 | 99 | 0.2202 | 0.0909 |
| 0.3–0.4 | 34 | 0.3621 | 0.2647 |
| 0.4–0.5 | 45 | 0.4389 | 0.2000 |
| 0.5–0.6 | 79 | 0.5093 | 0.0759 |
| 0.6–0.7 | 29 | 0.6431 | 0.3448 |
| 0.7–0.8 | 64 | 0.7466 | 0.5156 |
| 0.8–0.9 | 181 | 0.8295 | 0.6188 |
| 0.9–1.0 | 122 | 0.9297 | 0.7787 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 176 | 0.1332 | 0.1080 |
| 0.2–0.3 | 36 | 0.2195 | 0.1944 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 61 | 0.4165 | 0.1967 |
| 0.5–0.6 | 228 | 0.5042 | 0.2061 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 58 | 0.7324 | 0.4483 |
| 0.8–0.9 | 34 | 0.8247 | 0.6471 |
| 0.9–1.0 | 207 | 0.9723 | 0.8502 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 137 | 0.1435 | 0.0511 |
| 0.2–0.3 | 99 | 0.2202 | 0.0909 |
| 0.3–0.4 | 34 | 0.3621 | 0.2647 |
| 0.4–0.5 | 45 | 0.4389 | 0.2000 |
| 0.5–0.6 | 79 | 0.5093 | 0.0759 |
| 0.6–0.7 | 29 | 0.6431 | 0.3448 |
| 0.7–0.8 | 64 | 0.7466 | 0.5156 |
| 0.8–0.9 | 181 | 0.8295 | 0.6188 |
| 0.9–1.0 | 122 | 0.9297 | 0.7787 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 137 | 0.1435 | 0.0511 |
| 0.2–0.3 | 99 | 0.2202 | 0.1111 |
| 0.3–0.4 | 34 | 0.3621 | 0.2647 |
| 0.4–0.5 | 47 | 0.4413 | 0.1915 |
| 0.5–0.6 | 85 | 0.5128 | 0.0941 |
| 0.6–0.7 | 41 | 0.6485 | 0.3415 |
| 0.7–0.8 | 67 | 0.7476 | 0.5075 |
| 0.8–0.9 | 164 | 0.8251 | 0.6159 |
| 0.9–1.0 | 116 | 0.9610 | 0.8793 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 137 | 0.1435 | 0.0511 |
| 0.2–0.3 | 99 | 0.2202 | 0.0909 |
| 0.3–0.4 | 34 | 0.3621 | 0.2647 |
| 0.4–0.5 | 45 | 0.4389 | 0.2000 |
| 0.5–0.6 | 79 | 0.5093 | 0.0759 |
| 0.6–0.7 | 29 | 0.6431 | 0.3448 |
| 0.7–0.8 | 64 | 0.7466 | 0.5156 |
| 0.8–0.9 | 181 | 0.8295 | 0.6188 |
| 0.9–1.0 | 122 | 0.9297 | 0.7787 |
