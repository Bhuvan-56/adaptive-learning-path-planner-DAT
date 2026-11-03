# Beta Evaluation: Retained Recall Analysis (Task B3)

## 1. Overview and Evaluation Setup
This evaluation integrates the deferred retention quiz evaluator (`src/evaluation/retention.py`) into the closed-loop evaluation harness (`src/evaluation/integrated.py`). Latent mastery and recall retention are evaluated across all 8 evaluation arms over 5 random seeds (`[42, 101, 2024, 777, 999]`), totaling 1,000 simulated learners per arm (200 learners per seed).

### Retention Quiz Parameters
- **Delay:** $D = 7$ days post-instruction.
- **Items per Concept:** $N = 5$ items.
- **Reference Difficulty:** $d_0 = 0.50$.
- **Evaluated Concepts:** All completed/scheduled concepts (`studied_concepts`) for each learner.

### Scenarios
- **Scenario S0 (Control):** Default simulator dynamics with zero forgetting ($p_F = 0.0$).
- **Scenario S1 (Forgetting Treatment):** Simulator dynamics with forgetting rate $p_F = 0.05$ per day.

---

## 2. Retained Recall Results by Arm

Across all seeds and arms, retention was successfully computed for 100% of simulated learners (1,000/1,000 per arm). No arm failed to yield retention metrics because all arms schedule or complete eligible concepts within Day 1.

### Scenario S0 (Control: $p_F = 0.0$)
| Arm | Mean Retained Recall | Std Dev | Learners (N) |
| :--- | :--- | :--- | :--- |
| `adaptive_full` | **0.6903** | 0.2828 | 1000 |
| `static_prerequisite_order` | **0.6362** | 0.2406 | 1000 |
| `non_adaptive_greedy` | **0.6362** | 0.2406 | 1000 |
| `ablation_no_diagnostic` | **0.6903** | 0.2828 | 1000 |
| `ablation_no_replan` | **0.6362** | 0.2406 | 1000 |
| `ablation_no_difficulty_step`| **0.6903** | 0.2828 | 1000 |
| `ablation_no_review` | **0.6903** | 0.2828 | 1000 |
| `ablation_no_remediation` | **0.6903** | 0.2828 | 1000 |

### Scenario S1 (Forgetting Treatment: $p_F = 0.05$)
| Arm | Mean Retained Recall | Std Dev | Learners (N) |
| :--- | :--- | :--- | :--- |
| `adaptive_full` | **0.5877** | 0.2624 | 1000 |
| `static_prerequisite_order` | **0.5566** | 0.2084 | 1000 |
| `non_adaptive_greedy` | **0.5566** | 0.2084 | 1000 |
| `ablation_no_diagnostic` | **0.5877** | 0.2624 | 1000 |
| `ablation_no_replan` | **0.5566** | 0.2084 | 1000 |
| `ablation_no_difficulty_step`| **0.5877** | 0.2624 | 1000 |
| `ablation_no_review` | **0.5877** | 0.2624 | 1000 |
| `ablation_no_remediation` | **0.5877** | 0.2624 | 1000 |

---

## 3. Paired Differences and Interval Decision Rule

Paired differences are computed per learner ($N = 1,000$ pairs) using 1,000 bootstrap resamples for the 95% confidence interval:

### Scenario S0:
- **Adaptive Full vs. Static Prerequisite Order:**
  - Mean Difference: $+0.0541$
  - 95% Bootstrap CI: `[+0.0445, +0.0648]`
  - Claim under Interval Rule: **Favourable** (95% CI strictly excludes 0 in the positive direction).
- **Adaptive Full vs. Non-Adaptive Greedy:**
  - Mean Difference: $+0.0541$
  - 95% Bootstrap CI: `[+0.0445, +0.0648]`
  - Claim under Interval Rule: **Favourable** (95% CI strictly excludes 0 in the positive direction).

### Scenario S1:
- **Adaptive Full vs. Static Prerequisite Order:**
  - Mean Difference: $+0.0311$
  - 95% Bootstrap CI: `[+0.0194, +0.0431]`
  - Claim under Interval Rule: **Favourable** (95% CI strictly excludes 0 in the positive direction).
- **Adaptive Full vs. Non-Adaptive Greedy:**
  - Mean Difference: $+0.0311$
  - 95% Bootstrap CI: `[+0.0194, +0.0431]`
  - Claim under Interval Rule: **Favourable** (95% CI strictly excludes 0 in the positive direction).

---

## 4. Simulator Limitations and Scope
All reported figures and statistical intervals are generated from synthetic simulation environments (`SimulatedLearner` and `MatchedBKTGenerator`).
- No claims of calibration or fitting to real human learner data are made.
- Under S0, decay is absent ($p_F = 0$), so differences reflect item score response distributions across studied concepts.
- Under S1, decay is present ($p_F = 0.05$), and adaptive paths demonstrate higher retained recall than fixed topological or greedy paths under simulator assumptions.
