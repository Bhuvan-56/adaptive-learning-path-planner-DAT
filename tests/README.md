# Test Suite Overview

This directory contains the acceptance test suite for the Adaptive Learning and Path-Planning Engine. Tests are mapped 1:1 to the Requirement Traceability Matrix defined in [`TRACEABILITY.md`](../TRACEABILITY.md).

## Test Mapping Structure

| Test File | Milestone | Test Cases | Description |
| --------- | --------- | ---------- | ----------- |
| [`test_m1_curriculum_graph.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m1_curriculum_graph.py) | M1: Curriculum Graph & State | `test_tc_1_1`, `test_tc_1_2` | Prerequisite gating and 5 DAG validation checks (Tarjan's SCC, bounds, durations) |
| [`test_m2_adaptive_diagnostic.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m2_adaptive_diagnostic.py) | M2: Adaptive Diagnostic Policy | `test_tc_2_1`, `test_tc_2_2` | IRT Fisher information updates and CAT termination rules ($\text{Var}(\theta) \le 0.15$ or 10 items) |
| [`test_m3_path_planning.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m3_path_planning.py) | M3: Path Planning Optimization | `test_tc_3_1`, `test_tc_3_2` | Daily budget adherence and greedy scheduler $\ge 95\%$ DP-optimality benchmark |
| [`test_m4_difficulty_adaptation.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m4_difficulty_adaptation.py) | M4: Difficulty Adaptation | `test_tc_4_1`, `test_tc_4_2` | Stepwise difficulty decreases ($-0.10$, floor $0.05$) and increases ($+0.10$, cap $0.95$) |
| [`test_m5_spaced_review_remediation.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m5_spaced_review_remediation.py) | M5: Spaced Review & Remediation | `test_tc_5_1`, `test_tc_5_2` | Prerequisite remediation insertion and HLR recall decay review triggers ($R_c < 0.85$) |
| [`test_m6_dynamic_replanning.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m6_dynamic_replanning.py) | M6: Dynamic Replanning | `test_tc_6_1`, `test_tc_6_2` | Missed day schedule replanning and capacity infeasibility alternative trace output |
| [`test_m7_explainability.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m7_explainability.py) | M7: Explainability Framework | `test_tc_7_1`, `test_tc_7_2`, `test_tc_7_3` | Structured JSON trace generation, skipped material audit logs, and trace completeness checks |
| [`test_m8_evaluation.py`](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_m8_evaluation.py) | M8: Comparative Evaluation | `test_tc_8_1` | Differential path planning validation across distinct synthetic learner profiles |

## Running Tests

Once dependencies are installed, tests can be executed using `pytest`:

```bash
pytest tests/
```
