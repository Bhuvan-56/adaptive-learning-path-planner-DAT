# Acceptance Matrix (Week 5 Snapshot)

- **Git SHA:** `a209f13e02705c9a7b11311f339384f20c556ad6`
- **Tracked Tree Dirty:** `false`
- **docs/ACCEPTANCE_GROUPS.md SHA-256:** `1c0d8ddc124378c629dd84061e88d54ea85bd6fae1d6b38ef291bd8ad2a3f9f5`
- **Generated:** `2026-10-25T16:58:15.899432+00:00`

## Acceptance Groups Status Matrix (M1–M8)

| Group ID | Name | Doc Status | Tests | Passed | Failed | Skipped | XFailed | Verdict | Missing Citations | ASSERTS_CRITERION |
|---|---|---|---|---|---|---|---|---|---|---|
| **M1-a** | Graph Topology & Schema Validation | `passing` | 7 | 7 | 0 | 0 | 0 | **PASS** | None | `tests/test_m1_curriculum_graph.py:33` |
| **M1-b** | BKT Numerical Parity with pyBKT | `passing` | 3 | 3 | 0 | 0 | 0 | **PARTIAL** | test_bkt_pybkt_numeric_parity_across_sequences | `tests/test_m1_bkt_parity.py:125` |
| **M1-c** | State Classification Precedence & Window Gating | `passing` | 9 | 9 | 0 | 0 | 0 | **PASS** | None | `tests/test_m1_learner_state.py:108` |
| **M1-d** | Zero Prerequisite Violations (Hard Correctness) | `passing` | 6 | 6 | 0 | 0 | 0 | **PASS** | None | `tests/test_m3_states_feasibility.py:67` |
| **M2-a** | CAT Item Selection & Stopping Rule | `passing` | 6 | 6 | 0 | 0 | 0 | **PASS** | None | `tests/test_m2_adaptive_diagnostic.py:125` |
| **M2-b** | CAT Ability-to-Skill Mapping | `passing` | 1 | 1 | 0 | 0 | 0 | **PARTIAL** | test_cat_theta_to_bkt_mapping | `tests/test_w4_b3_diagnostic.py:263` |
| **M3-a** | Zero Daily Budget Violations (Hard Correctness) | `passing` | 4 | 4 | 0 | 0 | 0 | **PASS** | None | `tests/test_m3_path_planning.py:36` |
| **M3-b** | Greedy Benchmark Approximation Distribution | `passing` | 4 | 4 | 0 | 0 | 0 | **PASS** | None | `tests/test_m3_path_planning.py:77` |
| **M3-c** | Oracle Precedence & Order Invariance | `passing` | 3 | 3 | 0 | 0 | 0 | **PASS** | None | `tests/test_m3_oracle_bruteforce.py:136` |
| **M4-a** | Infeasibility Detection & Repair Guidance | `partial` | 2 | 2 | 0 | 0 | 0 | **PARTIAL** | None | `tests/test_m3_path_planning.py:53` |
| **M4-b** | 2-Up / 1-Down Dynamic Exercise Adaptation | `passing` | 4 | 4 | 0 | 0 | 0 | **PASS** | None | `tests/test_m4_difficulty_adaptation.py:20` |
| **M5-a** | Remediation Trigger on Repeated Assessment Failure | `passing` | 3 | 3 | 0 | 0 | 0 | **PASS** | None | `tests/test_m5_spaced_review_remediation.py:66` |
| **M5-b** | HLR Spaced Review Scheduling | `passing` | 4 | 4 | 0 | 0 | 0 | **PASS** | None | `tests/test_w4_a4_review_remediation.py:83` |
| **M6-a** | Dynamic Event Replanning | `passing` | 4 | 4 | 0 | 0 | 0 | **PASS** | None | `tests/test_m6_replanning_events.py:163` |
| **M6-b** | Plan Compression on Resource Reductions | `passing` | 1 | 1 | 0 | 0 | 0 | **PASS** | None | `tests/test_m6_dynamic_replanning.py:131` |
| **M7-a** | Trace Coverage 1.0 & Schema Contract (Hard Correctness) | `passing` | 4 | 4 | 0 | 0 | 0 | **PASS** | None | `tests/test_m7_explainability.py:25` |
| **M7-b** | Prerequisite & Skip Explainability Justification | `passing` | 3 | 3 | 0 | 0 | 0 | **PASS** | None | `tests/test_m7_explainability.py:40` |
| **M8-a** | Learner Profile Plan Differentiation | `partial` | 3 | 2 | 0 | 1 | 0 | **PARTIAL** | None | `NONE FOUND` |
| **M8-b** | Single Runnable End-to-End Command (Hard Correctness) | `passing` | 4 | 4 | 0 | 0 | 0 | **PASS** | None | `tests/test_cli_demo.py:32` |
| **M8-c** | Latent Mastery Simulator Invisibility Invariant | `passing` | 3 | 3 | 0 | 0 | 0 | **PASS** | None | `tests/test_simulation.py:69` |
| **M8-d** | Independent Retained-Recall Outcome Evaluation | `partial` | 5 | 5 | 0 | 0 | 0 | **PARTIAL** | test_independent_retention_outcome | `NONE FOUND` |

## Non-PASS Summary

- **M1-b (BKT Numerical Parity with pyBKT):** PARTIAL — Missing cited test: test_bkt_pybkt_numeric_parity_across_sequences
- **M2-b (CAT Ability-to-Skill Mapping):** PARTIAL — Missing cited test: test_cat_theta_to_bkt_mapping
- **M4-a (Infeasibility Detection & Repair Guidance):** PARTIAL — Document marks status as partial
- **M8-a (Learner Profile Plan Differentiation):** PARTIAL — Document marks status as partial; 1 test(s) skipped
- **M8-d (Independent Retained-Recall Outcome Evaluation):** PARTIAL — Document marks status as partial; Missing cited test: test_independent_retention_outcome

