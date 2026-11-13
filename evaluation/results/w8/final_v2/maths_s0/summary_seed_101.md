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
| **adaptive_full** | 6.5350 [5.8099, 7.2700] | 0 | 0 | 100.0% | 1161 (SCHEDULING_CONSTRAINTS_UNMET:469, CAPACITY_EXCEEDED:692) | 77.614 | 101.280 |
| **static_prerequisite_order** | 6.5100 [5.7849, 7.2701] | 0 | 0 | 100.0% | 0 | 3.010 | 6.378 |
| **non_adaptive_greedy** | 6.4950 [5.7698, 7.2350] | 0 | 0 | 100.0% | 0 | 0.063 | 0.139 |
| **non_adaptive_greedy_best_singleton** | 6.5950 [5.8900, 7.3450] | 0 | 0 | 100.0% | 0 | 0.105 | 0.213 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0250 | [-0.0950, 0.1351] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0400 | [-0.0651, 0.1400] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | -0.0150 | [-0.1000, 0.0650] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.1000 | [0.0500, 0.1550] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0500, 0.1550] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 6.6500 [5.9550, 7.3601] | -0.1150 [-0.2201, -0.0100] | ablation_no_diagnostic improves on adaptive_full [0.0100, 0.2201] |
| **ablation_no_replan** | 6.5000 [5.7798, 7.2602] | 0.0350 [-0.0850, 0.1450] | no difference shown |
| **ablation_no_difficulty_step** | 6.5350 [5.8099, 7.2700] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 6.5300 [5.8098, 7.2650] | 0.0050 [-0.0100, 0.0250] | no difference shown |
| **ablation_no_remediation** | 6.5350 [5.8099, 7.2700] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1898 [0.1831, 0.1966] | 0.1565 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1945 [0.1879, 0.2011] | 0.1375 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1898 [0.1831, 0.1966] | 0.1565 | 3200 |
| ablation_no_review | 0.1911 [0.1843, 0.1979] | 0.1551 | 3200 |
| ablation_no_remediation | 0.1898 [0.1831, 0.1966] | 0.1565 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 316 | 0.1363 | 0.1361 |
| 0.2–0.3 | 103 | 0.2228 | 0.2524 |
| 0.3–0.4 | 26 | 0.3609 | 0.3846 |
| 0.4–0.5 | 117 | 0.4312 | 0.3675 |
| 0.5–0.6 | 1777 | 0.5008 | 0.2375 |
| 0.6–0.7 | 24 | 0.6532 | 0.4167 |
| 0.7–0.8 | 177 | 0.7387 | 0.7627 |
| 0.8–0.9 | 216 | 0.8366 | 0.8565 |
| 0.9–1.0 | 440 | 0.9682 | 0.9841 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 311 | 0.1316 | 0.1672 |
| 0.2–0.3 | 251 | 0.2098 | 0.2271 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 134 | 0.4149 | 0.3507 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2562 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 160 | 0.7331 | 0.6438 |
| 0.8–0.9 | 348 | 0.8117 | 0.7816 |
| 0.9–1.0 | 396 | 0.9851 | 0.9823 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 316 | 0.1363 | 0.1361 |
| 0.2–0.3 | 103 | 0.2228 | 0.2524 |
| 0.3–0.4 | 26 | 0.3609 | 0.3846 |
| 0.4–0.5 | 117 | 0.4312 | 0.3675 |
| 0.5–0.6 | 1777 | 0.5008 | 0.2375 |
| 0.6–0.7 | 24 | 0.6532 | 0.4167 |
| 0.7–0.8 | 177 | 0.7387 | 0.7627 |
| 0.8–0.9 | 216 | 0.8366 | 0.8565 |
| 0.9–1.0 | 440 | 0.9682 | 0.9841 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 317 | 0.1363 | 0.1356 |
| 0.2–0.3 | 106 | 0.2225 | 0.2830 |
| 0.3–0.4 | 26 | 0.3609 | 0.3846 |
| 0.4–0.5 | 119 | 0.4316 | 0.3782 |
| 0.5–0.6 | 1779 | 0.5009 | 0.2383 |
| 0.6–0.7 | 26 | 0.6499 | 0.4615 |
| 0.7–0.8 | 186 | 0.7387 | 0.7688 |
| 0.8–0.9 | 201 | 0.8346 | 0.8507 |
| 0.9–1.0 | 436 | 0.9779 | 0.9817 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 316 | 0.1363 | 0.1361 |
| 0.2–0.3 | 103 | 0.2228 | 0.2524 |
| 0.3–0.4 | 26 | 0.3609 | 0.3846 |
| 0.4–0.5 | 117 | 0.4312 | 0.3675 |
| 0.5–0.6 | 1777 | 0.5008 | 0.2375 |
| 0.6–0.7 | 24 | 0.6532 | 0.4167 |
| 0.7–0.8 | 177 | 0.7387 | 0.7627 |
| 0.8–0.9 | 216 | 0.8366 | 0.8565 |
| 0.9–1.0 | 440 | 0.9682 | 0.9841 |
