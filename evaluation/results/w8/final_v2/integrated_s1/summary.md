# Week 5 Integrated Evaluation Summary: Multi-Seed Benchmark

## 1. Multi-Seed Benchmark Setup

- **Benchmark Name:** `w5_integrated_multiseed`
- **Evaluated Seeds (5):** `[42, 101, 2024, 777, 999]`
- **Synthetic Learners per Seed:** 200
- **Total Synthetic Learners Evaluated:** 1000
- **Planning Horizon:** 5 days
- **Daily Study Budget:** 10 minutes
- **Bootstrap Resamples per Seed:** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `MatchedBKTGenerator` (BKT response dynamics)

## 2. Per-Seed Performance Table (Primary Arms)

| Seed | adaptive_full [95% CI] | static_prerequisite_order [95% CI] | non_adaptive_greedy [95% CI] | adaptive minus static [95% CI] | Claim Assessment | No-Plan Days (adaptive) |
|---|---|---|---|---|---|---|
| **42** | 1.6350 [1.4349, 1.8301] | 1.6000 [1.3949, 1.8000] | 1.6550 [1.4399, 1.8700] | 0.0350 [0.0050, 0.0700] | adaptive_full improves on static_prerequisite_order [0.0050, 0.0700] | 120 |
| **101** | 1.5700 [1.3948, 1.7550] | 1.4800 [1.2950, 1.6700] | 1.4800 [1.2900, 1.6601] | 0.0900 [0.0350, 0.1450] | adaptive_full improves on static_prerequisite_order [0.0350, 0.1450] | 135 |
| **2024** | 1.6750 [1.4900, 1.8451] | 1.6150 [1.4249, 1.8050] | 1.5800 [1.4050, 1.7550] | 0.0600 [0.0150, 0.1050] | adaptive_full improves on static_prerequisite_order [0.0150, 0.1050] | 127 |
| **777** | 1.4500 [1.2699, 1.6300] | 1.4300 [1.2550, 1.6150] | 1.4450 [1.2550, 1.6350] | 0.0200 [-0.0300, 0.0650] | no difference shown | 133 |
| **999** | 1.8300 [1.6450, 2.0300] | 1.8100 [1.6250, 2.0150] | 1.8100 [1.6150, 2.0150] | 0.0200 [-0.0300, 0.0700] | no difference shown | 105 |

## Mastery calibration, pooled over seeds [42, 101, 2024, 777, 999] (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1955 [0.1873, 0.2033] | 0.1625 | 4000 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1890 [0.1817, 0.1959] | 0.1453 | 4000 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1955 [0.1873, 0.2033] | 0.1625 | 4000 |
| ablation_no_review | 0.1889 [0.1812, 0.1961] | 0.1569 | 4000 |
| ablation_no_remediation | 0.1955 [0.1873, 0.2033] | 0.1625 | 4000 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 558 | 0.1442 | 0.0824 |
| 0.2–0.3 | 577 | 0.2192 | 0.1213 |
| 0.3–0.4 | 179 | 0.3600 | 0.2514 |
| 0.4–0.5 | 237 | 0.4454 | 0.3080 |
| 0.5–0.6 | 368 | 0.5103 | 0.0897 |
| 0.6–0.7 | 125 | 0.6494 | 0.4080 |
| 0.7–0.8 | 312 | 0.7489 | 0.5513 |
| 0.8–0.9 | 966 | 0.8328 | 0.6718 |
| 0.9–1.0 | 638 | 0.9325 | 0.7727 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 800 | 0.1341 | 0.1187 |
| 0.2–0.3 | 123 | 0.2195 | 0.1707 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 303 | 0.4164 | 0.2937 |
| 0.5–0.6 | 1170 | 0.5050 | 0.2496 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 307 | 0.7335 | 0.5537 |
| 0.8–0.9 | 178 | 0.8247 | 0.6236 |
| 0.9–1.0 | 1119 | 0.9724 | 0.8508 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 558 | 0.1442 | 0.0824 |
| 0.2–0.3 | 577 | 0.2192 | 0.1213 |
| 0.3–0.4 | 179 | 0.3600 | 0.2514 |
| 0.4–0.5 | 237 | 0.4454 | 0.3080 |
| 0.5–0.6 | 368 | 0.5103 | 0.0897 |
| 0.6–0.7 | 125 | 0.6494 | 0.4080 |
| 0.7–0.8 | 312 | 0.7489 | 0.5513 |
| 0.8–0.9 | 966 | 0.8328 | 0.6718 |
| 0.9–1.0 | 638 | 0.9325 | 0.7727 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 558 | 0.1442 | 0.0824 |
| 0.2–0.3 | 577 | 0.2192 | 0.1248 |
| 0.3–0.4 | 179 | 0.3600 | 0.2570 |
| 0.4–0.5 | 245 | 0.4471 | 0.3184 |
| 0.5–0.6 | 401 | 0.5138 | 0.1097 |
| 0.6–0.7 | 166 | 0.6504 | 0.4096 |
| 0.7–0.8 | 334 | 0.7497 | 0.5419 |
| 0.8–0.9 | 852 | 0.8271 | 0.6678 |
| 0.9–1.0 | 648 | 0.9626 | 0.8410 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 558 | 0.1442 | 0.0824 |
| 0.2–0.3 | 577 | 0.2192 | 0.1213 |
| 0.3–0.4 | 179 | 0.3600 | 0.2514 |
| 0.4–0.5 | 237 | 0.4454 | 0.3080 |
| 0.5–0.6 | 368 | 0.5103 | 0.0897 |
| 0.6–0.7 | 125 | 0.6494 | 0.4080 |
| 0.7–0.8 | 312 | 0.7489 | 0.5513 |
| 0.8–0.9 | 966 | 0.8328 | 0.6718 |
| 0.9–1.0 | 638 | 0.9325 | 0.7727 |

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
| **adaptive_full** | 1.6350 [1.4349, 1.8301] | 0 | 0 | 100.0% | 120 (SCHEDULING_CONSTRAINTS_UNMET:55, CAPACITY_EXCEEDED:65) | 12.731 | 26.178 |
| **static_prerequisite_order** | 1.6000 [1.3949, 1.8000] | 0 | 0 | 100.0% | 0 | 0.536 | 0.879 |
| **non_adaptive_greedy** | 1.6550 [1.4399, 1.8700] | 0 | 0 | 100.0% | 0 | 0.016 | 0.022 |
| **non_adaptive_greedy_best_singleton** | 1.6600 [1.4400, 1.8750] | 0 | 0 | 100.0% | 0 | 0.034 | 0.057 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0350 | [0.0050, 0.0700] | **adaptive_full improves on static_prerequisite_order** [0.0050, 0.0700] |
| **adaptive_full - non_adaptive_greedy** | -0.0200 | [-0.1050, 0.0651] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0550 | [-0.0250, 0.1351] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0050 | [-0.0350, 0.0550] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 1.7550 [1.5749, 1.9400] | -0.1200 [-0.2050, -0.0399] | ablation_no_diagnostic improves on adaptive_full [0.0399, 0.2050] |
| **ablation_no_replan** | 1.5950 [1.3899, 1.7950] | 0.0400 [0.0100, 0.0750] | adaptive_full improves on ablation_no_replan [0.0100, 0.0750] |
| **ablation_no_difficulty_step** | 1.6350 [1.4349, 1.8301] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.6400 [1.4399, 1.8350] | -0.0050 [-0.0401, 0.0300] | no difference shown |
| **ablation_no_remediation** | 1.6350 [1.4349, 1.8301] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1864 [0.1676, 0.2043] | 0.1581 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1813 [0.1665, 0.1959] | 0.1352 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1864 [0.1676, 0.2043] | 0.1581 | 800 |
| ablation_no_review | 0.1847 [0.1658, 0.2019] | 0.1546 | 800 |
| ablation_no_remediation | 0.1864 [0.1676, 0.2043] | 0.1581 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 110 | 0.1427 | 0.0909 |
| 0.2–0.3 | 136 | 0.2194 | 0.1397 |
| 0.3–0.4 | 35 | 0.3459 | 0.1714 |
| 0.4–0.5 | 38 | 0.4433 | 0.2105 |
| 0.5–0.6 | 66 | 0.5068 | 0.0152 |
| 0.6–0.7 | 20 | 0.6465 | 0.4500 |
| 0.7–0.8 | 62 | 0.7494 | 0.5806 |
| 0.8–0.9 | 212 | 0.8345 | 0.6462 |
| 0.9–1.0 | 117 | 0.9311 | 0.8632 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 171 | 0.1340 | 0.1228 |
| 0.2–0.3 | 24 | 0.2195 | 0.1667 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 53 | 0.4167 | 0.3208 |
| 0.5–0.6 | 237 | 0.5054 | 0.2489 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 56 | 0.7334 | 0.5893 |
| 0.8–0.9 | 27 | 0.8247 | 0.5185 |
| 0.9–1.0 | 232 | 0.9734 | 0.8750 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 110 | 0.1427 | 0.0909 |
| 0.2–0.3 | 136 | 0.2194 | 0.1397 |
| 0.3–0.4 | 35 | 0.3459 | 0.1714 |
| 0.4–0.5 | 38 | 0.4433 | 0.2105 |
| 0.5–0.6 | 66 | 0.5068 | 0.0152 |
| 0.6–0.7 | 20 | 0.6465 | 0.4500 |
| 0.7–0.8 | 62 | 0.7494 | 0.5806 |
| 0.8–0.9 | 212 | 0.8345 | 0.6462 |
| 0.9–1.0 | 117 | 0.9311 | 0.8632 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 110 | 0.1427 | 0.0909 |
| 0.2–0.3 | 136 | 0.2194 | 0.1471 |
| 0.3–0.4 | 35 | 0.3459 | 0.2000 |
| 0.4–0.5 | 41 | 0.4472 | 0.2439 |
| 0.5–0.6 | 75 | 0.5120 | 0.0533 |
| 0.6–0.7 | 26 | 0.6448 | 0.4231 |
| 0.7–0.8 | 65 | 0.7489 | 0.5692 |
| 0.8–0.9 | 187 | 0.8296 | 0.6524 |
| 0.9–1.0 | 121 | 0.9624 | 0.8843 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 110 | 0.1427 | 0.0909 |
| 0.2–0.3 | 136 | 0.2194 | 0.1397 |
| 0.3–0.4 | 35 | 0.3459 | 0.1714 |
| 0.4–0.5 | 38 | 0.4433 | 0.2105 |
| 0.5–0.6 | 66 | 0.5068 | 0.0152 |
| 0.6–0.7 | 20 | 0.6465 | 0.4500 |
| 0.7–0.8 | 62 | 0.7494 | 0.5806 |
| 0.8–0.9 | 212 | 0.8345 | 0.6462 |
| 0.9–1.0 | 117 | 0.9311 | 0.8632 |
