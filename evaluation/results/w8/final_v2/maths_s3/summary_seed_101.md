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
| **adaptive_full** | 7.3900 [6.6950, 8.1151] | 0 | 0 | 100.0% | 1116 (SCHEDULING_CONSTRAINTS_UNMET:490, CAPACITY_EXCEEDED:626) | 74.704 | 96.671 |
| **static_prerequisite_order** | 6.7600 [5.9948, 7.6151] | 0 | 0 | 100.0% | 0 | 2.802 | 6.047 |
| **non_adaptive_greedy** | 6.9600 [6.1948, 7.7901] | 0 | 0 | 100.0% | 0 | 0.064 | 0.141 |
| **non_adaptive_greedy_best_singleton** | 7.0500 [6.2698, 7.8951] | 0 | 0 | 100.0% | 0 | 0.107 | 0.241 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.6300 | [0.4350, 0.8301] | **adaptive_full improves on static_prerequisite_order** [0.4350, 0.8301] |
| **adaptive_full - non_adaptive_greedy** | 0.4300 | [0.2250, 0.6450] | **adaptive_full improves on non_adaptive_greedy** [0.2250, 0.6450] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.2000 | [0.0650, 0.3251] | **non_adaptive_greedy improves on static_prerequisite_order** [0.0650, 0.3251] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0900 | [0.0400, 0.1400] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0400, 0.1400] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 7.5550 [6.8849, 8.2751] | -0.1650 [-0.2851, -0.0550] | ablation_no_diagnostic improves on adaptive_full [0.0550, 0.2851] |
| **ablation_no_replan** | 6.7650 [5.9949, 7.6200] | 0.6250 [0.4250, 0.8250] | adaptive_full improves on ablation_no_replan [0.4250, 0.8250] |
| **ablation_no_difficulty_step** | 7.4000 [6.7148, 8.1251] | -0.0100 [-0.0400, 0.0150] | no difference shown |
| **ablation_no_review** | 7.4000 [6.7000, 8.1201] | -0.0100 [-0.0250, 0.0000] | no difference shown |
| **ablation_no_remediation** | 7.3900 [6.6950, 8.1151] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1959 [0.1880, 0.2043] | 0.1557 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1956 [0.1865, 0.2041] | 0.1520 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1946 [0.1867, 0.2029] | 0.1537 | 3200 |
| ablation_no_review | 0.1957 [0.1875, 0.2040] | 0.1556 | 3200 |
| ablation_no_remediation | 0.1959 [0.1880, 0.2043] | 0.1557 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 145 | 0.1398 | 0.1241 |
| 0.2–0.3 | 90 | 0.2221 | 0.3556 |
| 0.3–0.4 | 14 | 0.3582 | 0.5714 |
| 0.4–0.5 | 124 | 0.4236 | 0.2742 |
| 0.5–0.6 | 1673 | 0.5014 | 0.2504 |
| 0.6–0.7 | 51 | 0.6530 | 0.5882 |
| 0.7–0.8 | 245 | 0.7399 | 0.6612 |
| 0.8–0.9 | 278 | 0.8347 | 0.8058 |
| 0.9–1.0 | 580 | 0.9709 | 0.9500 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 101 | 0.1382 | 0.1287 |
| 0.2–0.3 | 184 | 0.2106 | 0.2500 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 63 | 0.4149 | 0.2222 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2562 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 205 | 0.7367 | 0.6829 |
| 0.8–0.9 | 453 | 0.8121 | 0.6909 |
| 0.9–1.0 | 594 | 0.9851 | 0.9680 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 152 | 0.1397 | 0.1250 |
| 0.2–0.3 | 95 | 0.2218 | 0.3474 |
| 0.3–0.4 | 15 | 0.3604 | 0.6000 |
| 0.4–0.5 | 121 | 0.4228 | 0.2810 |
| 0.5–0.6 | 1673 | 0.5013 | 0.2504 |
| 0.6–0.7 | 51 | 0.6530 | 0.5882 |
| 0.7–0.8 | 238 | 0.7402 | 0.6681 |
| 0.8–0.9 | 269 | 0.8351 | 0.8216 |
| 0.9–1.0 | 586 | 0.9710 | 0.9488 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 145 | 0.1394 | 0.1310 |
| 0.2–0.3 | 89 | 0.2223 | 0.3371 |
| 0.3–0.4 | 14 | 0.3582 | 0.5714 |
| 0.4–0.5 | 123 | 0.4237 | 0.2764 |
| 0.5–0.6 | 1675 | 0.5014 | 0.2513 |
| 0.6–0.7 | 53 | 0.6512 | 0.6038 |
| 0.7–0.8 | 249 | 0.7399 | 0.6707 |
| 0.8–0.9 | 259 | 0.8315 | 0.7915 |
| 0.9–1.0 | 593 | 0.9788 | 0.9511 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 145 | 0.1398 | 0.1241 |
| 0.2–0.3 | 90 | 0.2221 | 0.3556 |
| 0.3–0.4 | 14 | 0.3582 | 0.5714 |
| 0.4–0.5 | 124 | 0.4236 | 0.2742 |
| 0.5–0.6 | 1673 | 0.5014 | 0.2504 |
| 0.6–0.7 | 51 | 0.6530 | 0.5882 |
| 0.7–0.8 | 245 | 0.7399 | 0.6612 |
| 0.8–0.9 | 278 | 0.8347 | 0.8058 |
| 0.9–1.0 | 580 | 0.9709 | 0.9500 |
