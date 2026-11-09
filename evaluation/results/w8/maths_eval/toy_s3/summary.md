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
| **42** | 2.7050 [2.5400, 2.8600] | 2.3450 [2.0900, 2.5800] | 2.3450 [2.0900, 2.5800] | 0.3600 [0.2250, 0.4951] | adaptive_full improves on static_prerequisite_order [0.2250, 0.4951] | 200 |
| **101** | 2.6300 [2.4550, 2.8200] | 2.2100 [1.9898, 2.4450] | 2.2100 [1.9898, 2.4450] | 0.4200 [0.3049, 0.5400] | adaptive_full improves on static_prerequisite_order [0.3049, 0.5400] | 200 |
| **2024** | 2.6950 [2.5248, 2.8601] | 2.4100 [2.1849, 2.6250] | 2.4100 [2.1849, 2.6250] | 0.2850 [0.1650, 0.4150] | adaptive_full improves on static_prerequisite_order [0.1650, 0.4150] | 200 |
| **777** | 2.5450 [2.3650, 2.7200] | 2.1650 [1.9250, 2.4001] | 2.1650 [1.9250, 2.4001] | 0.3800 [0.2499, 0.5050] | adaptive_full improves on static_prerequisite_order [0.2499, 0.5050] | 200 |
| **999** | 2.8650 [2.7000, 3.0151] | 2.5400 [2.3000, 2.7800] | 2.5400 [2.3000, 2.7800] | 0.3250 [0.1950, 0.4600] | adaptive_full improves on static_prerequisite_order [0.1950, 0.4600] | 200 |

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
| **adaptive_full** | 2.7050 [2.5400, 2.8600] | 0 | 0 | 100.0% | 200 (SCHEDULING_CONSTRAINTS_UNMET:200) | 26.818 | 37.384 |
| **static_prerequisite_order** | 2.3450 [2.0900, 2.5800] | 0 | 0 | 100.0% | 0 | 0.772 | 0.969 |
| **non_adaptive_greedy** | 2.3450 [2.0900, 2.5800] | 0 | 0 | 100.0% | 0 | 0.020 | 0.028 |
| **non_adaptive_greedy_best_singleton** | 2.3400 [2.0850, 2.5800] | 0 | 0 | 100.0% | 0 | 0.042 | 0.050 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.3600 | [0.2250, 0.4951] | **adaptive_full improves on static_prerequisite_order** [0.2250, 0.4951] |
| **adaptive_full - non_adaptive_greedy** | 0.3600 | [0.2250, 0.4951] | **adaptive_full improves on non_adaptive_greedy** [0.2250, 0.4951] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0050 | [-0.0500, 0.0350] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.7050 [2.5400, 2.8600] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_replan** | 2.3450 [2.0900, 2.5800] | 0.3600 [0.2250, 0.4951] | adaptive_full improves on ablation_no_replan [0.2250, 0.4951] |
| **ablation_no_difficulty_step** | 2.7000 [2.5350, 2.8600] | 0.0050 [0.0000, 0.0150] | no difference shown |
| **ablation_no_review** | 2.7050 [2.5400, 2.8600] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.7050 [2.5400, 2.8600] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.
