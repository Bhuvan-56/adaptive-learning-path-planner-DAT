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
| **adaptive_full** | 2.3500 [2.1250, 2.5651] | 0 | 0 | 100.0% | 61 (SCHEDULING_CONSTRAINTS_UNMET:28, CAPACITY_EXCEEDED:33) | 14.062 | 58.587 |
| **static_prerequisite_order** | 2.2100 [1.9898, 2.4450] | 0 | 0 | 100.0% | 0 | 0.545 | 1.306 |
| **non_adaptive_greedy** | 2.2100 [1.9898, 2.4450] | 0 | 0 | 100.0% | 0 | 0.017 | 0.041 |
| **non_adaptive_greedy_best_singleton** | 2.1900 [1.9550, 2.4300] | 0 | 0 | 100.0% | 0 | 0.035 | 0.082 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.1400 | [0.0900, 0.1900] | **adaptive_full improves on static_prerequisite_order** [0.0900, 0.1900] |
| **adaptive_full - non_adaptive_greedy** | 0.1400 | [0.0900, 0.1900] | **adaptive_full improves on non_adaptive_greedy** [0.0900, 0.1900] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0200 | [-0.0550, 0.0150] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.6300 [2.4550, 2.8200] | -0.2800 [-0.3900, -0.1800] | ablation_no_diagnostic improves on adaptive_full [0.1800, 0.3900] |
| **ablation_no_replan** | 2.2100 [1.9898, 2.4450] | 0.1400 [0.0900, 0.1900] | adaptive_full improves on ablation_no_replan [0.0900, 0.1900] |
| **ablation_no_difficulty_step** | 2.3500 [2.1250, 2.5651] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.3600 [2.1350, 2.5800] | -0.0100 [-0.0250, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.3500 [2.1250, 2.5651] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1757 [0.1579, 0.1951] | 0.1066 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1455 [0.1308, 0.1611] | 0.0694 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1751 [0.1573, 0.1949] | 0.1054 | 800 |
| ablation_no_review | 0.1740 [0.1559, 0.1936] | 0.0999 | 800 |
| ablation_no_remediation | 0.1757 [0.1579, 0.1951] | 0.1066 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 1 | 0.0664 | 0.0000 |
| 0.1–0.2 | 62 | 0.1426 | 0.1129 |
| 0.2–0.3 | 99 | 0.2159 | 0.3333 |
| 0.3–0.4 | 14 | 0.3690 | 0.5000 |
| 0.4–0.5 | 56 | 0.4411 | 0.3393 |
| 0.5–0.6 | 66 | 0.5291 | 0.2424 |
| 0.6–0.7 | 44 | 0.6557 | 0.5000 |
| 0.7–0.8 | 77 | 0.7461 | 0.6104 |
| 0.8–0.9 | 233 | 0.8284 | 0.7425 |
| 0.9–1.0 | 148 | 0.9329 | 0.9865 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 38 | 0.1335 | 0.1316 |
| 0.2–0.3 | 15 | 0.2195 | 0.3333 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 48 | 0.4172 | 0.3542 |
| 0.5–0.6 | 231 | 0.5046 | 0.3420 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 63 | 0.7371 | 0.7460 |
| 0.8–0.9 | 53 | 0.8247 | 0.7547 |
| 0.9–1.0 | 352 | 0.9713 | 0.9460 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 1 | 0.0664 | 0.0000 |
| 0.1–0.2 | 62 | 0.1425 | 0.1129 |
| 0.2–0.3 | 100 | 0.2159 | 0.3300 |
| 0.3–0.4 | 14 | 0.3690 | 0.5000 |
| 0.4–0.5 | 56 | 0.4411 | 0.3393 |
| 0.5–0.6 | 66 | 0.5291 | 0.2424 |
| 0.6–0.7 | 44 | 0.6557 | 0.5000 |
| 0.7–0.8 | 76 | 0.7464 | 0.6184 |
| 0.8–0.9 | 233 | 0.8284 | 0.7425 |
| 0.9–1.0 | 148 | 0.9329 | 0.9865 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 1 | 0.0664 | 0.0000 |
| 0.1–0.2 | 62 | 0.1426 | 0.1129 |
| 0.2–0.3 | 99 | 0.2159 | 0.3333 |
| 0.3–0.4 | 14 | 0.3690 | 0.5000 |
| 0.4–0.5 | 56 | 0.4411 | 0.3393 |
| 0.5–0.6 | 69 | 0.5301 | 0.2754 |
| 0.6–0.7 | 46 | 0.6563 | 0.5217 |
| 0.7–0.8 | 78 | 0.7463 | 0.6154 |
| 0.8–0.9 | 209 | 0.8231 | 0.7225 |
| 0.9–1.0 | 166 | 0.9646 | 0.9880 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 1 | 0.0664 | 0.0000 |
| 0.1–0.2 | 62 | 0.1426 | 0.1129 |
| 0.2–0.3 | 99 | 0.2159 | 0.3333 |
| 0.3–0.4 | 14 | 0.3690 | 0.5000 |
| 0.4–0.5 | 56 | 0.4411 | 0.3393 |
| 0.5–0.6 | 66 | 0.5291 | 0.2424 |
| 0.6–0.7 | 44 | 0.6557 | 0.5000 |
| 0.7–0.8 | 77 | 0.7461 | 0.6104 |
| 0.8–0.9 | 233 | 0.8284 | 0.7425 |
| 0.9–1.0 | 148 | 0.9329 | 0.9865 |
