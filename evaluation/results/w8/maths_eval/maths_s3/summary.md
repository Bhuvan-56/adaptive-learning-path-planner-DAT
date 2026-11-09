# Week 5 Integrated Evaluation Summary: Multi-Seed Benchmark

## 1. Multi-Seed Benchmark Setup

- **Benchmark Name:** `w5_integrated_multiseed`
- **Evaluated Seeds (5):** `[42, 101, 2024, 777, 999]`
- **Synthetic Learners per Seed:** 200
- **Total Synthetic Learners Evaluated:** 1000
- **Planning Horizon:** 10 days
- **Daily Study Budget:** 30 minutes
- **Bootstrap Resamples per Seed:** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `MatchedBKTGenerator` (BKT response dynamics)

## 2. Per-Seed Performance Table (Primary Arms)

| Seed | adaptive_full [95% CI] | static_prerequisite_order [95% CI] | non_adaptive_greedy [95% CI] | adaptive minus static [95% CI] | Claim Assessment | No-Plan Days (adaptive) |
|---|---|---|---|---|---|---|
| **42** | 7.5350 [6.9149, 8.1950] | 6.5400 [5.7399, 7.3302] | 6.9600 [6.1299, 7.7850] | 0.9950 [0.7749, 1.2451] | adaptive_full improves on static_prerequisite_order [0.7749, 1.2451] | 1200 |
| **101** | 7.5550 [6.8849, 8.2751] | 6.7600 [5.9948, 7.6151] | 6.9600 [6.1948, 7.7901] | 0.7950 [0.5450, 1.0350] | adaptive_full improves on static_prerequisite_order [0.5450, 1.0350] | 1200 |
| **2024** | 7.7000 [7.0449, 8.3552] | 6.8950 [6.1195, 7.6701] | 7.2650 [6.4700, 8.0854] | 0.8050 [0.5849, 1.0300] | adaptive_full improves on static_prerequisite_order [0.5849, 1.0300] | 1200 |
| **777** | 7.0650 [6.4099, 7.7552] | 6.3000 [5.5143, 7.1202] | 6.6000 [5.8048, 7.4052] | 0.7650 [0.5050, 1.0101] | adaptive_full improves on static_prerequisite_order [0.5050, 1.0101] | 1200 |
| **999** | 8.0800 [7.4750, 8.7251] | 7.3850 [6.6250, 8.1902] | 7.7050 [6.9349, 8.5200] | 0.6950 [0.4496, 0.9501] | adaptive_full improves on static_prerequisite_order [0.4496, 0.9501] | 1200 |

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
| **adaptive_full** | 7.5350 [6.9149, 8.1950] | 0 | 0 | 100.0% | 1200 (SCHEDULING_CONSTRAINTS_UNMET:400, CAPACITY_EXCEEDED:800) | 114.391 | 234.492 |
| **static_prerequisite_order** | 6.5400 [5.7399, 7.3302] | 0 | 0 | 100.0% | 0 | 7.093 | 8.389 |
| **non_adaptive_greedy** | 6.9600 [6.1299, 7.7850] | 0 | 0 | 100.0% | 0 | 0.137 | 0.176 |
| **non_adaptive_greedy_best_singleton** | 7.0450 [6.2000, 7.8750] | 0 | 0 | 100.0% | 0 | 0.232 | 0.267 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.9950 | [0.7749, 1.2451] | **adaptive_full improves on static_prerequisite_order** [0.7749, 1.2451] |
| **adaptive_full - non_adaptive_greedy** | 0.5750 | [0.3099, 0.8651] | **adaptive_full improves on non_adaptive_greedy** [0.3099, 0.8651] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.4200 | [0.2999, 0.5550] | **non_adaptive_greedy improves on static_prerequisite_order** [0.2999, 0.5550] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0850 | [0.0350, 0.1350] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0350, 0.1350] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 7.5350 [6.9149, 8.1950] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_replan** | 6.5400 [5.7399, 7.3302] | 0.9950 [0.7749, 1.2451] | adaptive_full improves on ablation_no_replan [0.7749, 1.2451] |
| **ablation_no_difficulty_step** | 7.5400 [6.9149, 8.1951] | -0.0050 [-0.0150, 0.0000] | no difference shown |
| **ablation_no_review** | 7.5350 [6.9149, 8.1950] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 7.5350 [6.9149, 8.1950] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.
