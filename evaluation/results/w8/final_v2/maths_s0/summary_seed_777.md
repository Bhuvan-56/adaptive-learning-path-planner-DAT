# Week 5 Integrated Evaluation Summary: Closed-Loop Path Planning

## 1. Evaluation Setup & Input Provenance

- **Benchmark Name:** `w5_integrated`
- **Evaluated Cohort:** 200 synthetic learners (paired random seeds)
- **Planning Horizon:** 10 days
- **Daily Study Budget:** 30 minutes
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
| **adaptive_full** | 5.9550 [5.2398, 6.6752] | 0 | 0 | 100.0% | 1165 (SCHEDULING_CONSTRAINTS_UNMET:479, CAPACITY_EXCEEDED:686) | 75.212 | 142.245 |
| **static_prerequisite_order** | 5.7250 [4.9849, 6.4750] | 0 | 0 | 100.0% | 0 | 2.879 | 5.914 |
| **non_adaptive_greedy** | 5.8150 [5.0899, 6.5600] | 0 | 0 | 100.0% | 0 | 0.060 | 0.134 |
| **non_adaptive_greedy_best_singleton** | 5.9200 [5.1950, 6.6501] | 0 | 0 | 100.0% | 0 | 0.100 | 0.233 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.2300 | [0.1200, 0.3500] | **adaptive_full improves on static_prerequisite_order** [0.1200, 0.3500] |
| **adaptive_full - non_adaptive_greedy** | 0.1400 | [0.0400, 0.2450] | **adaptive_full improves on non_adaptive_greedy** [0.0400, 0.2450] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0900 | [0.0150, 0.1650] | **non_adaptive_greedy improves on static_prerequisite_order** [0.0150, 0.1650] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.1050 | [0.0600, 0.1550] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0600, 0.1550] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 5.9900 [5.2599, 6.6901] | -0.0350 [-0.1350, 0.0650] | no difference shown |
| **ablation_no_replan** | 5.7250 [4.9849, 6.4750] | 0.2300 [0.1200, 0.3500] | adaptive_full improves on ablation_no_replan [0.1200, 0.3500] |
| **ablation_no_difficulty_step** | 5.9550 [5.2398, 6.6752] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 5.9450 [5.2300, 6.6600] | 0.0100 [0.0000, 0.0250] | no difference shown |
| **ablation_no_remediation** | 5.9550 [5.2398, 6.6752] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1915 [0.1852, 0.1984] | 0.1871 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1892 [0.1828, 0.1962] | 0.1629 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1915 [0.1852, 0.1984] | 0.1871 | 3200 |
| ablation_no_review | 0.1911 [0.1847, 0.1979] | 0.1846 | 3200 |
| ablation_no_remediation | 0.1915 [0.1852, 0.1984] | 0.1871 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0711 | 0.0000 |
| 0.1–0.2 | 339 | 0.1366 | 0.1534 |
| 0.2–0.3 | 108 | 0.2268 | 0.1759 |
| 0.3–0.4 | 31 | 0.3669 | 0.4839 |
| 0.4–0.5 | 138 | 0.4248 | 0.3623 |
| 0.5–0.6 | 1766 | 0.5006 | 0.1925 |
| 0.6–0.7 | 22 | 0.6484 | 0.5000 |
| 0.7–0.8 | 190 | 0.7414 | 0.7000 |
| 0.8–0.9 | 205 | 0.8364 | 0.8878 |
| 0.9–1.0 | 393 | 0.9664 | 0.9898 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 316 | 0.1319 | 0.1456 |
| 0.2–0.3 | 302 | 0.2107 | 0.1556 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 131 | 0.4149 | 0.3435 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2100 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 127 | 0.7372 | 0.6220 |
| 0.8–0.9 | 323 | 0.8118 | 0.7895 |
| 0.9–1.0 | 401 | 0.9851 | 0.9726 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0711 | 0.0000 |
| 0.1–0.2 | 339 | 0.1366 | 0.1534 |
| 0.2–0.3 | 108 | 0.2268 | 0.1759 |
| 0.3–0.4 | 31 | 0.3669 | 0.4839 |
| 0.4–0.5 | 138 | 0.4248 | 0.3623 |
| 0.5–0.6 | 1766 | 0.5006 | 0.1925 |
| 0.6–0.7 | 22 | 0.6484 | 0.5000 |
| 0.7–0.8 | 190 | 0.7414 | 0.7000 |
| 0.8–0.9 | 205 | 0.8364 | 0.8878 |
| 0.9–1.0 | 393 | 0.9664 | 0.9898 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0711 | 0.0000 |
| 0.1–0.2 | 342 | 0.1366 | 0.1491 |
| 0.2–0.3 | 108 | 0.2268 | 0.1759 |
| 0.3–0.4 | 31 | 0.3669 | 0.4839 |
| 0.4–0.5 | 138 | 0.4248 | 0.3623 |
| 0.5–0.6 | 1773 | 0.5007 | 0.1951 |
| 0.6–0.7 | 28 | 0.6496 | 0.6071 |
| 0.7–0.8 | 190 | 0.7417 | 0.7000 |
| 0.8–0.9 | 190 | 0.8344 | 0.8947 |
| 0.9–1.0 | 392 | 0.9753 | 0.9898 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0711 | 0.0000 |
| 0.1–0.2 | 339 | 0.1366 | 0.1534 |
| 0.2–0.3 | 108 | 0.2268 | 0.1759 |
| 0.3–0.4 | 31 | 0.3669 | 0.4839 |
| 0.4–0.5 | 138 | 0.4248 | 0.3623 |
| 0.5–0.6 | 1766 | 0.5006 | 0.1925 |
| 0.6–0.7 | 22 | 0.6484 | 0.5000 |
| 0.7–0.8 | 190 | 0.7414 | 0.7000 |
| 0.8–0.9 | 205 | 0.8364 | 0.8878 |
| 0.9–1.0 | 393 | 0.9664 | 0.9898 |
