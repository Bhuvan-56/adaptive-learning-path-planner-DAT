# Acceptance Groups Register (M1–M8)

This register defines the formal binary pass/fail acceptance groups across modules M1 through M8. It copies and sharpens the acceptance groups from the mid-review report and requirements traceability register (`TRACEABILITY.md`), establishing explicit test bindings, current implementation status, and module ownership.

---

## Hard Correctness Requirements
The system enforces four non-negotiable correctness invariants that take strict precedence over empirical performance:
1. **Zero Prerequisite Violations (Group M1-d):** No target concept may ever be unlocked or scheduled until all mandatory prerequisite nodes are strictly in the `Mastered` state ($p \ge 0.85, \sigma^2 \le 0.05, n \ge 3$, window quorum satisfied).
2. **Zero Budget Violations (Group M3-a):** Total scheduled duration on any planning day must never exceed the configured daily budget $B \in \{5, 10, 15, 30\}$ minutes; lesson activity blocks are indivisible.
3. **Trace Explanation Coverage 1.0 (Group M7-a):** Exactly 100% of candidate activities in the candidate universe (target node plus all ancestor nodes in the DAG) must appear in the JSON audit trace for every planning day with valid schema fields and machine-readable reason codes.
4. **Single Runnable End-to-End Command (Group M8-b):** The entire verification and execution suite must be runnable via a single terminal command returning exit code 0.

---

## Acceptance Groups Matrix

### Module M1: Curriculum Graph & Learner State Models
*Primary Owner: Bhuvan | Secondary Owner: Abdur*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M1-a** | **Graph Topology & Schema Validation:** Curriculum graph loaded from YAML must pass 5 automated checks: existing node references, positive durations, difficulty $\in [0.05, 0.95]$, zero self-loops, and zero directed cycles via Tarjan's SCC. | `tests/test_m1_curriculum_graph.py`<br>`test_tc_1_2_rejects_malformed_graph_files` | `passing` | Bhuvan | Testable as written. |
| **M1-b** | **BKT Numerical Parity with pyBKT:** Exact closed-form BKT posterior updates in `src/state/learner_state.py` match `pyBKT 1.4.3` predictions within absolute error tolerance $10^{-4}$ across arbitrary binary observation sequences. | `tests/test_m1_bkt_parity.py`<br>`test_bkt_pybkt_numeric_parity_across_sequences` | `passing` | Abdur | Testable as written. |
| **M1-c** | **State Classification Precedence & Window Gating:** Learner state prioritizes `Uncertain` if $n < 3$ or $\sigma^2 > 0.05$; requires full window $|W| \ge 4$ with $\ge 75\%$ correct for `Mastered` ($p \ge 0.85$) and $\ge 75\%$ incorrect for `Weak` (strict $p < 0.40$); conflicting evidence defaults to `Developing`. | `tests/test_m1_learner_state.py`<br>`test_boundary_variance_0_05`<br>`test_boundary_p_0_40`<br>`test_boundary_n_3` | `passing` | Bhuvan | Testable as written. |
| **M1-d** | **Zero Prerequisite Violations (Hard Correctness):** Unmastered, uncertain, or merely scheduled prerequisites prevent unlocking of dependent targets under all conditions. | `tests/test_m3_states_feasibility.py`<br>`test_scheduled_only_prerequisite_does_not_unlock_dependent_unconditionally` | `passing` | Both | Testable as written. |

---

### Module M2: Adaptive Diagnostic Policy (CAT / IRT)
*Primary Owner: Abdur | Secondary Owner: Bhuvan*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M2-a** | **CAT Item Selection & Stopping Rule:** Diagnostic dynamically selects items via Maximum Fisher Information $I(\hat{\theta})$; terminates immediately when $\operatorname{Var}(\theta) \le 0.15$ or exactly 10 questions are answered. | `tests/test_m2_adaptive_diagnostic.py`<br>`test_tc_2_1_incorrect_response_lowers_mastery_and_selects_max_fisher_item`<br>`test_tc_2_2_diagnostic_terminates_on_variance_or_question_limit`<br>`tests/test_w4_b3_diagnostic.py` | `passing` | Abdur | Testable and verified in Week 4 against synthetic item bank. |
| **M2-b** | **CAT Ability-to-Skill Mapping:** Diagnostic ability estimate $\hat{\theta}$ initializes probed concepts via logistic link $p_{c,0} = \operatorname{sigm}(\hat{\theta})$ clamped to $[0.01, 0.99]$; unprobed concepts retain uninformative prior $\operatorname{Beta}(1, 1)$ ($n=0$, `Uncertain`). | `tests/test_m2_adaptive_diagnostic.py`<br>`test_cat_theta_to_bkt_mapping`<br>`tests/test_w4_b3_diagnostic.py` | `passing` | Abdur | Testable and verified. Synthetic item bank (`data/processed/item_bank_synthetic.csv`) and Q-matrix (`data/processed/q_matrix_synthetic.csv`) declared and integrated. |

---

### Module M3: Path Planning Optimization (Greedy & Exact Oracle)
*Primary Owner: Bhuvan | Secondary Owner: Abdur*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M3-a** | **Zero Daily Budget Violations (Hard Correctness):** Total scheduled duration for any day never exceeds daily budget $B \in \{5, 10, 15, 30\}$ minutes; block indivisibility strictly preserved. | `tests/test_m3_path_planning.py`<br>`test_tc_3_1_budget_never_exceeds_configured_budget` | `passing` | Bhuvan | Testable as written. |
| **M3-b** | **Greedy Benchmark Approximation Distribution:** Greedy score-per-minute scheduler evaluated against exact exhaustive oracle over 250 instances across 5 seeds achieves mean ratio $\bar{\rho} \ge 0.95$ and reproduces the 12/18 counterexample ($\rho = 0.6667$). | `tests/test_m3_path_planning.py`<br>`test_tc_3_2_benchmark_runs_and_reports` | `passing` | Bhuvan | Testable as written. |
| **M3-c** | **Oracle Precedence & Order Invariance:** Benchmark oracle enumerates all precedence-closed subsets independently of candidate input ordering, enforces $N \le 20$ hard cap (`ValueError`), and 2.0 s timeout (`TimeoutError`). | `tests/test_m3_oracle_order.py`<br>`test_oracle_order_independence`<br>`tests/test_m3_oracle_bruteforce.py`<br>`test_oracle_hard_cap_raises_value_error` | `passing` | Bhuvan | Testable as written. |

---

### Module M4: Difficulty Adaptation & Feasibility Analysis
*Primary Owner: Abdur (Adaptation) / Bhuvan (Feasibility)*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M4-a** | **Infeasibility Detection & Repair Guidance:** System partitions planning requests into `FEASIBLE`, `INFEASIBLE_PROVED` with actionable repair suggestions (single block $> B$ or total work $> DB$), and `HEURISTIC_NO_PLAN`. | `tests/test_m3_path_planning.py`<br>`test_infeasible_block_10min_under_5min_cap`<br>`tests/test_m3_states_feasibility.py`<br>`test_defect_4_three_six_minute_tasks_heuristic_no_plan_consistent_nested_status` | `partial` | Bhuvan | Partial per mentor guidance. Strict mathematical infeasibility proves single-block ($> B$) and aggregate capacity ($> DB$) violations with actionable repairs; heuristic packing failures without capacity overruns return `HEURISTIC_NO_PLAN` without dynamic constraint relaxation. |
| **M4-b** | **2-Up / 1-Down Dynamic Exercise Adaptation:** Single incorrect exercise decreases concept difficulty by 0.10 (floored at 0.05); two consecutive correct exercises increase difficulty by 0.10 (capped at 0.95). | `tests/test_m4_difficulty_adaptation.py`<br>`test_tc_4_1_single_failure_decreases_difficulty_floored_at_0_05`<br>`test_tc_4_2_two_consecutive_successes_increase_difficulty_capped_at_0_95`<br>`tests/test_w4_a3_difficulty_gate.py` | `passing` | Abdur | Testable and verified in Week 4 against `config/adaptive.yaml` step size. |

---

### Module M5: Spaced Review & Remediation
*Primary Owner: Abdur | Secondary Owner: Bhuvan*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M5-a** | **Remediation Trigger on Repeated Assessment Failure:** Failing two mastery assessments for the same concept within an episode schedules the lowest-mastery unmet prerequisite for remediation before dependent material unlocks. | `tests/test_m5_spaced_review_remediation.py`<br>`test_tc_5_1_failed_assessments_trigger_prerequisite_remediation`<br>`tests/test_w4_a4_review_remediation.py` | `passing` | Abdur | Testable and verified in Week 4 against simulated failure sequences. |
| **M5-b** | **HLR Spaced Review Scheduling:** When HLR-predicted recall $R_c = 2^{-\Delta t / H_c}$ drops below 0.85, a review activity is scheduled competing within daily budget $B$. | `tests/test_m5_spaced_review_remediation.py`<br>`test_tc_5_2_decayed_hlr_recall_schedules_spaced_review`<br>`tests/test_w4_a4_review_remediation.py` | `passing` | Abdur | Testable and verified. Calendar tracking and attempt logging implemented via `ReviewLog` with half-life decay prior ($H_{\text{prior}}=14.0$ d) and review threshold $R_c < 0.85$. |

---

### Module M6: Dynamic Replanning & Event Handling
*Primary Owner: Bhuvan | Secondary Owner: Abdur*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M6-a** | **Dynamic Event Replanning:** External events (`assessment_result`, `missed_day`, `budget_change`, `deadline_change`) dynamically replan remaining schedule without deleting or overwriting completed progress. | `tests/test_m6_replanning_events.py`<br>`test_event_missed_day_keeps_completed_work`<br>`test_event_budget_reduced_gives_valid_plan_or_structured_infeasibility` | `passing` | Bhuvan | Testable as written. |
| **M6-b** | **Plan Compression on Resource Reductions:** Mid-plan budget reduction produces either a valid compressed plan or an explicit capacity-infeasibility trace with actionable alternatives (extend deadline by $X$ days, raise budget by $Y$ min). | `tests/test_m6_dynamic_replanning.py`<br>`test_tc_6_2_reduced_budget_outputs_valid_plan_or_infeasibility_trace_with_alternatives` | `passing` | Bhuvan | Testable and verified in Week 4 dynamic replanning suite. |

---

### Module M7: Explainability Framework & Audit Trace
*Primary Owner: Bhuvan | Secondary Owner: Abdur*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M7-a** | **Trace Coverage 1.0 & Schema Contract (Hard Correctness):** Candidate universe (target + all DAG ancestors) is 100% documented per planning day. Validates all 8 schema fields, valid ReasonCodes, and non-empty score terms for scoring policies. | `tests/test_m7_explainability.py`<br>`test_trace_has_one_entry_per_candidate`<br>`tests/test_m7_trace_contract.py`<br>`test_check_trace_missing_whole_day_2_of_2` | `passing` | Bhuvan | Testable as written. |
| **M7-b** | **Prerequisite & Skip Explainability Justification:** Unmet prerequisites are explicitly traced with `PREREQUISITE_UNMET`; already mastered nodes with `ALREADY_MASTERED`; uncertain nodes with `UNCERTAIN_NEEDS_ASSESSMENT`. | `tests/test_m7_explainability.py`<br>`test_blocked_and_skipped_nodes_visible`<br>`tests/test_m3_states_feasibility.py`<br>`test_uncertain_prerequisite_routes_to_uncertain_needs_assessment` | `passing` | Bhuvan | Testable as written. |

---

### Module M8: Comparative Evaluation & End-to-End Pipeline
*Primary Owner: Both (Bhuvan & Abdur)*

| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |
|---|---|---|---|---|---|
| **M8-a** | **Learner Profile Plan Differentiation:** Synthetic learners with distinctly different initial prior mastery profiles (Novice, Intermediate, Refresher, Mixed) receive structurally and mathematically distinct learning paths. | `tests/test_m8_evaluation.py`<br>`test_tc_8_1_different_mastery_profiles_produce_distinct_plans`<br>`tests/test_w4_b2_provenance_profiles.py`<br>`tests/test_w4_t2_slice.py` | `partial` | Both | Partial per mentor guidance. Multi-profile group expansion and distinct plan generation are tested and passing in W4 test suites (`test_w4_b2_provenance_profiles.py`, `test_w4_t2_slice.py`), while stub `test_m8_evaluation.py::test_tc_8_1` remains skipped. |
| **M8-b** | **Single Runnable End-to-End Command (Hard Correctness):** A single runnable command executes the full verification and evaluation suite, verifying graph validation, state tracking, multi-day planning, simulation, and trace validation with exit code 0. | Standalone CLI execution:<br>`python -m src.cli demo`<br>`python -m src.cli plan`<br>`python -m src.cli slice`<br>Audit script: `scripts/clean_run.ps1` | `passing` | Both | Verified. Standalone CLI exists now in `src/cli.py` supporting `demo`, `plan`, and `slice` subcommands. `scripts/clean_run.ps1` executes clean clone verification with exit code 0. |
| **M8-c** | **Latent Mastery Simulator Invisibility Invariant:** Modules under `src/planning/` and `src/state/` contain zero imports or references to `EvaluatorView`; latent mastery state is strictly invisible to the planning engine. | `tests/test_simulation.py`<br>`test_planner_and_state_modules_contain_no_import_of_evaluator_view` | `passing` | Abdur | Testable as written. |
| **M8-d** | **Independent Retained-Recall Outcome Evaluation:** Delayed quiz of $N$ items at $D$ days post-intervention scored strictly from latent state by evaluator, reporting paired bootstrap 95% CIs against Static and Greedy baselines across matched and mismatched simulators. | `src/evaluation/compare.py`<br>`tests/test_w4_b4_comparison.py`<br>`tests/test_m8_evaluation.py::test_independent_retention_outcome` | `partial` | Both | Partial per mentor guidance. Multi-arm comparative evaluation across diagnostic arms (Random, Static, CAT) and planner arms (Static, Greedy, Adaptive) is executed via `src/evaluation/compare.py` (`experiments/w4_comparison.yaml`), while delayed retention quiz with `MismatchedPFAOrLogisticGenerator` remains stubbed (`NotImplementedError`). |

---

## Summary of Partial and Resolved Groups (Week 4 Reconciliation)

1. **M2-b (CAT Ability-to-Skill Mapping):** **RESOLVED (Passing).**
   - Item bank (`data/processed/item_bank_synthetic.csv`) and Q-matrix (`data/processed/q_matrix_synthetic.csv`) were declared and synthesized in Week 4. Probed concepts map via ADR-009 logistic link $p_{c,0} = \operatorname{sigm}(\hat{\theta})$, and unprobed concepts cold-start as uninformative prior $\operatorname{Beta}(1, 1)$ (`Uncertain`).
2. **M4-a (Infeasibility Detection & Repair Guidance):** **PARTIAL (Mentor Confirmed).**
   - Partitioning into `FEASIBLE`, `INFEASIBLE_PROVED`, and `HEURISTIC_NO_PLAN` is implemented and passing. Actionable repairs are computed for block exceedances ($> B$) and capacity overruns ($> DB$). Heuristic packing dead-ends return `HEURISTIC_NO_PLAN` with consistent nested explanations without dynamic repair synthesis.
3. **M5-b (HLR Spaced Review Scheduling):** **RESOLVED (Passing).**
   - Timestamped attempt logging is implemented via `ReviewLog`. Elapsed time $\Delta t$ and exponential memory decay ($R_c = 2^{-\Delta t / 14}$) trigger review scheduling inside leftover daily budget with reason `REVIEW_DUE`.
4. **M8-a (Learner Profile Plan Differentiation):** **PARTIAL (Mentor Confirmed).**
   - Plan divergence between profiles (e.g. `profile_1` vs `profile_2`) is verified across dynamic assessment scenarios in `test_w4_b2_provenance_profiles.py` and `test_w4_t2_slice.py`. The legacy stub `test_m8_evaluation.py::test_tc_8_1` remains skipped.
5. **M8-b (Single Runnable End-to-End Command):** **RESOLVED (Passing).**
   - The CLI exists now. Dedicated subcommands `demo`, `plan`, and `slice` in `src/cli.py` run full planning and trace generation from the terminal, and `scripts/clean_run.ps1` executes fresh-clone verification with exit code 0.
6. **M8-d (Independent Retained-Recall Outcome Evaluation):** **PARTIAL (Mentor Confirmed).**
   - Comparative evaluation across 4 diagnostic arms and 3 planner arms is implemented in `src/evaluation/compare.py` with results in `evaluation/results/w4/`. Delayed post-intervention retention testing under `MismatchedPFAOrLogisticGenerator` remains deferred.
