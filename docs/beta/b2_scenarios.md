# Beta Evaluation Report: Generator Scenarios (S0, S1, S2)

## 1. Executive Summary & Experimental Setup

This benchmark evaluates the closed-loop path planning engine under three distinct simulator scenarios across 5 seeds (`[42, 101, 2024, 777, 999]`), evaluating $N=200$ synthetic learners per seed ($1,000$ synthetic learners total per scenario) across all 8 arms (3 primary arms and 5 ablations).

All claims and findings apply strictly to simulator behavior on synthetic data generated via `MatchedBKTGenerator`.

### Evaluated Scenarios

1. **Scenario S0 (Default Matched BKT):**
   - Generator: `MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.10, p_F=0.00, k=0.00)`
   - Latent mastery transitions are binary without forgetting (`p_F = 0.0`) or difficulty sensitivity (`k = 0.0`).
   - Output is value-identical to the Week 5 committed baseline.

2. **Scenario S1 (Forgetting Variant):**
   - Generator: `MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.10, p_F=0.05, k=0.00)`
   - Forgetting rate $p_F = 0.05$ per day.
   - Evaluates delayed retention quiz recall post-horizon ($D=7$ days delay, $N=5$ items per concept).

3. **Scenario S2 (Difficulty-Sensitive Variant):**
   - Generator: `MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.10, p_F=0.00, k=0.50)`
   - Response accuracy follows monotone logit scaling with sensitivity parameter $k = 0.50$.

---

## 2. Benchmark Results by Scenario and Arm (1,000 Synthetic Learners per Scenario)

### Scenario S0: Default Matched BKT ($p_F=0.0, k=0.0$)

| Arm | Mean Mastered [95% CI] | Adaptive vs Arm Diff [95% CI] | No-Plan Days | Prereq Violations | Budget Violations | Trace Coverage |
|---|---|---|---|---|---|---|
| **adaptive_full** | 1.9340 [1.8279, 2.0340] | ref | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **static_prerequisite_order** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **non_adaptive_greedy** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_diagnostic** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_replan** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_difficulty_step** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_review** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_remediation** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |

### Scenario S1: Forgetting Variant ($p_F=0.05, k=0.0$)

| Arm | Mean Mastered [95% CI] | Adaptive vs Arm Diff [95% CI] | No-Plan Days | Prereq Violations | Budget Violations | Trace Coverage |
|---|---|---|---|---|---|---|
| **adaptive_full** | 1.9340 [1.8279, 2.0340] | ref | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **static_prerequisite_order** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **non_adaptive_greedy** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_diagnostic** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_replan** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_difficulty_step** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_review** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_remediation** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |

### Scenario S2: Difficulty-Sensitive Variant ($p_F=0.0, k=0.50$)

| Arm | Mean Mastered [95% CI] | Adaptive vs Arm Diff [95% CI] | No-Plan Days | Prereq Violations | Budget Violations | Trace Coverage |
|---|---|---|---|---|---|---|
| **adaptive_full** | 1.9340 [1.8279, 2.0340] | ref | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **static_prerequisite_order** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **non_adaptive_greedy** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_diagnostic** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_replan** | 2.0360 [1.9280, 2.1320] | -0.1020 [-0.1200, -0.0840] | 0 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_difficulty_step** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_review** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |
| **ablation_no_remediation** | 1.9340 [1.8279, 2.0340] | 0.0000 [0.0000, 0.0000] | 4,000 / 5,000 | 0 | 0 | 100.0% |

---

## 3. Targeted Ablation Analysis (Step 6)

1. **Ablation `ablation_no_review` minus `adaptive_full` under Scenario S1:**
   - Difference in mastered concepts: $0.0000$ [$0.0000$, $0.0000$]
   - **Claim Assessment:** **No demonstrated effect** (paired 95% bootstrap interval includes zero).

2. **Ablation `ablation_no_difficulty_step` minus `adaptive_full` under Scenario S2:**
   - Difference in mastered concepts: $0.0000$ [$0.0000$, $0.0000$]
   - **Claim Assessment:** **No demonstrated effect** (paired 95% bootstrap interval includes zero).

### Root Cause Analysis

In all adaptive replanning arms (`adaptive_full`, `ablation_no_diagnostic`, `ablation_no_difficulty_step`, `ablation_no_review`, `ablation_no_remediation`), dynamic replanning halts with `HEURISTIC_NO_PLAN` (`SCHEDULING_CONSTRAINTS_UNMET`) on Days 2, 3, 4, and 5 for all learners (800 no-plan days per seed, 4,000 total across 5 seeds). Because replanning generates no scheduled activities on days 2..5, neither spaced review nor difficulty ladder adjustments can be executed after Day 1. Consequently, mastery outcomes remain invariant across these ablations and scenarios.

