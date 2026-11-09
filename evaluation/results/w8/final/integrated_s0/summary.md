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
| **42** | 2.1300 [1.9146, 2.3350] | 1.9700 [1.7299, 2.2050] | 1.9700 [1.7299, 2.2050] | 0.1600 [0.0900, 0.2350] | adaptive_full improves on static_prerequisite_order [0.0900, 0.2350] | 200 |
| **101** | 2.1600 [1.9500, 2.3650] | 1.9700 [1.7450, 2.2050] | 1.9700 [1.7450, 2.2050] | 0.1900 [0.1200, 0.2650] | adaptive_full improves on static_prerequisite_order [0.1200, 0.2650] | 200 |
| **2024** | 2.1850 [1.9800, 2.3850] | 2.1150 [1.8850, 2.3250] | 2.1150 [1.8850, 2.3250] | 0.0700 [0.0100, 0.1300] | adaptive_full improves on static_prerequisite_order [0.0100, 0.1300] | 200 |
| **777** | 2.0200 [1.8000, 2.2301] | 1.8700 [1.6400, 2.1050] | 1.8700 [1.6400, 2.1050] | 0.1500 [0.0800, 0.2200] | adaptive_full improves on static_prerequisite_order [0.0800, 0.2200] | 200 |
| **999** | 2.3850 [2.1898, 2.5951] | 2.2550 [2.0449, 2.4750] | 2.2550 [2.0449, 2.4750] | 0.1300 [0.0700, 0.1901] | adaptive_full improves on static_prerequisite_order [0.0700, 0.1901] | 200 |

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
| **adaptive_full** | 2.1300 [1.9146, 2.3350] | 0 | 0 | 100.0% | 200 (SCHEDULING_CONSTRAINTS_UNMET:200) | 28.498 | 33.070 |
| **static_prerequisite_order** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.845 | 0.909 |
| **non_adaptive_greedy** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.022 | 0.025 |
| **non_adaptive_greedy_best_singleton** | 1.9850 [1.7400, 2.2200] | 0 | 0 | 100.0% | 0 | 0.047 | 0.059 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.1600 | [0.0900, 0.2350] | **adaptive_full improves on static_prerequisite_order** [0.0900, 0.2350] |
| **adaptive_full - non_adaptive_greedy** | 0.1600 | [0.0900, 0.2350] | **adaptive_full improves on non_adaptive_greedy** [0.0900, 0.2350] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0150 | [0.0000, 0.0350] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.1300 [1.9146, 2.3350] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_replan** | 1.9700 [1.7299, 2.2050] | 0.1600 [0.0900, 0.2350] | adaptive_full improves on ablation_no_replan [0.0900, 0.2350] |
| **ablation_no_difficulty_step** | 2.1300 [1.9146, 2.3350] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.1300 [1.9146, 2.3350] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.1300 [1.9146, 2.3350] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.
