# Week 2 Independent Audit Report

**Auditor:** Independent Auditor  
**Date:** 03 October 2026  
**Repository:** Adaptive Learning and Path-Planning Engine (Project ID 3)  
**Target Increment:** Week 2 Deliverables (M1, M3, M7 foundation)

---

## 1. Milestone & Acceptance Test Audit Matrix

| Milestone / Test ID | Target Week | Verdict | Evidence (File/Line or Command) | Gaps / Notes |
|---|---|---|---|---|
| **M1 / TC-1.1** (Prerequisite Gating) | W2 | **PASS** | `src/planning/static_baseline.py:100-104`, `tests/test_m3_path_planning.py:91-105` | Prerequisite gating enforced during topological packing and admissibility check. |
| **M1 / TC-1.2** (Graph Loader & Validator) | W2 | **PASS** | `src/curriculum/graph.py:12-98`, `tests/test_m1_curriculum_graph.py:10-33` | All 5 automated checks pass on valid graph; 5 malformed fixtures yield ONLY their specific `GraphErrorCode`. Null duration & difficulty bounds [0.05, 0.95] verified via shell execution. |
| **M1 / Learner State** (Beta Belief & Classification) | W2 | **PARTIAL** | `src/state/learner_state.py:9-97`, `tests/test_m1_learner_state.py:10-92` | State class, Beta variance $\sigma^2 = \frac{p(1-p)}{\kappa+1}$, and classification precedence implemented. **Gap:** Default BKT parameters ($p_S=0.20, p_G=0.20, p_T=0.0$) were manually tuned to force `test_conflicting_evidence_no_unsupported_confidence` to pass. |
| **M2 / TC-2.1, TC-2.2** (Adaptive Diagnostic CAT/IRT) | W3+ | **NOT IMPLEMENTED** | `tests/test_m2_adaptive_diagnostic.py:4-11` | Clean stub marked `pytest.skip("NOT_IMPLEMENTED")`. Expected for W2. |
| **M3 / TC-3.1** (Static Baseline & Time Budget) | W2 | **PASS** | `src/planning/static_baseline.py:17-175`, `tests/test_m3_path_planning.py:12-34` | Daily budget constraint enforced across 5, 10, 15, 30 min budgets. Block indivisibility preserved (no block splitting). |
| **M3 / Infeasibility Engine** (Per-block & Capacity) | W2 | **PASS** | `src/planning/feasibility.py:17-76`, `tests/test_m3_path_planning.py:37-51` | Block duration $> B$ returns `INFEASIBLE_PROVED` with `BLOCK_EXCEEDS_DAILY_BUDGET` at all deadlines $D$. Aggregate $W_{req} > D \cdot B$ returns `CAPACITY_EXCEEDED` with necessary-not-sufficient fixes. $W_{req} \le D \cdot B$ packing failure returns `HEURISTIC_NO_PLAN`. |
| **M3 / TC-3.2** (Greedy vs. Exact DP Oracle) | W2 | **PASS** | `src/planning/greedy.py:10-53`, `src/planning/oracle.py:10-54`, `src/planning/benchmark.py:17-133` | 10-min counterexample yields score 12 vs 18 ($\rho = 0.6667$). Benchmark across 5 seeds (250 instances) produces mean ratio 0.9737, 5th percentile 0.8270, worst-case 0.2143 (instance 215, verified valid). Reports saved to `w2_greedy_vs_oracle.csv` and `w2_summary.md`. |
| **M4 / TC-4.1, TC-4.2** (Difficulty Adaptation) | W3+ | **NOT IMPLEMENTED** | `tests/test_m4_difficulty_adaptation.py:4-11` | Clean stub marked `pytest.skip("NOT_IMPLEMENTED")`. Expected for W2. |
| **M5 / TC-5.1, TC-5.2** (Spaced Review & Remediation) | W3+ | **NOT IMPLEMENTED** | `tests/test_m5_spaced_review_remediation.py:4-11` | Clean stub marked `pytest.skip("NOT_IMPLEMENTED")`. Expected for W2. |
| **M6 / TC-6.1, TC-6.2** (Dynamic Replanning) | W3+ | **NOT IMPLEMENTED** | `tests/test_m6_dynamic_replanning.py:4-11` | Clean stub marked `pytest.skip("NOT_IMPLEMENTED")`. Expected for W2. |
| **M7 / TC-7.1, TC-7.2, TC-7.3** (Audit Trace & Checker) | W2 | **PARTIAL** | `src/trace/schema.py:6-30`, `src/trace/universe.py:5-15`, `src/trace/checker.py:6-52`, `tests/test_m7_explainability.py:12-78` | Candidate universe (target + all ancestors) extracted. Trace completeness checker verifies 1 entry per candidate per day and fails on missing, duplicate, or invalid codes. **Gap:** `score_terms` dictionary is empty `{}` for static baseline, and multi-policy explainability is W3+. |
| **M8 / TC-8.1** (Evaluation Suite & Multi-Policy Comparison) | W3+ | **NOT IMPLEMENTED** | `tests/test_m8_evaluation.py:4-7` | Clean stub marked `pytest.skip("NOT_IMPLEMENTED")`. Expected for W2. |
| **Optional Bandit Agent** (ADR-005) | W3+ | **NOT IMPLEMENTED** | `docs/adr/ADR-005-bounded-self-learning-policy.md` | Documented as optional extension in ADR-005; no implementation code written. Expected for W2. |

---

## 2. Post-Failure Edits Analysis

During implementation of Week 2 work, three source files were edited to resolve test execution failures. Each edit was audited to determine root cause and whether test assertions were loosened or model parameters were tuned:

### 1. `src/curriculum/graph.py`
- **Trigger:** Initial test run of `test_tc_1_2_rejects_malformed_graph_files` on `missing_node.json` failed with `AssertionError: [<NONPOSITIVE_DURATION>, <DIFFICULTY_OUT_OF_RANGE>, <MISSING_NODE>] != [<MISSING_NODE>]`.
- **Root Cause:** Calling NetworkX's `g.add_edge(source, target)` when `target` was not in `declared_nodes` caused NetworkX to automatically insert node `"NON_EXISTENT_NODE"` into `g.nodes` with default `{}` attributes (causing `baseline_duration=None` and `base_difficulty=None`).
- **Change Made:** Modified `load_graph()` to check `if source in declared_nodes and target in declared_nodes` before calling `g.add_edge()` (lines 26–33).
- **Assessment:** **Legitimate Bug Fix.** No test assertions were loosened or removed.

### 2. `src/state/learner_state.py`
- **Trigger:** Test `test_conflicting_evidence_no_unsupported_confidence` failed during initial test execution with `AssertionError: 'Weak' not in ['Mastered', 'Weak']` (and subsequently `'Mastered' not in ['Mastered', 'Weak']`).
- **Root Cause:** Under default initial BKT update parameters ($p_S=0.10, p_G=0.25, p_T=0.10$), an alternating sequence of 4 correct/incorrect outcomes reduced $p$ to $0.3566 < 0.40$ with $\sigma^2 = 0.0327 \le 0.05$ at $n=4$, triggering a `"Weak"` classification.
- **Change Made:** Default BKT parameters in `ConceptState.update()` were tuned from $(p_S=0.10, p_G=0.25, p_T=0.10)$ to $(p_S=0.20, p_G=0.20, p_T=0.0)$ (lines 55–57).
- **Assessment:** **Parameter Tuning to Pass Test.** The test assertion itself (`assert state.classify() not in ["Mastered", "Weak"]`) was not modified, but default BKT parameters were specifically set to zero learning rate ($p_T=0.0$) and symmetric slip/guess ($p_S=p_G=0.20$) to prevent state transitions into `Mastered` or `Weak` during alternating observation sequences.

### 3. `src/planning/static_baseline.py`
- **Trigger:** Test `test_trace_has_one_entry_per_candidate` failed with `ValueError: Trace missing candidate nodes on day 2: ['A', 'B']`.
- **Root Cause:** Nodes scheduled on Day 1 were removed from `remaining_nodes` (`remaining_nodes.remove(node_id)`). On Day 2, `static_baseline` only iterated over `remaining_nodes` and `mastered_nodes` (nodes mastered before Day 1), omitting nodes scheduled on Day 1 from Day 2's trace.
- **Change Made:** Updated `static_baseline.py` to iterate over the entire `candidate_universe` on every planning day, emitting a trace entry with `decision="FILTERED"` and `reason_code=ALREADY_MASTERED` for nodes completed on prior days (lines 115–137).
- **Assessment:** **Legitimate Bug Fix.** Ensures 100% trace candidate completeness per planning day without loosening test criteria.

---

## 3. Defects Found (Ranked by Severity)

### 1. **Medium Severity: Parameter Sensitivity in Learner State BKT Update**
- **Location:** `src/state/learner_state.py:55-57`
- **Description:** `ConceptState.update()` relies on hardcoded default BKT parameters ($p_S=0.20, p_G=0.20, p_T=0.0$). If non-zero learning rates (e.g. $p_T=0.05$) or asymmetric slip/guess parameters are passed, an alternating sequence of 20 outcomes can cause belief drift into `Mastered` or `Weak` states despite inconsistent evidence.
- **Impact:** Evidence confidence tracking is sensitive to BKT parameter selection.
- **Recommendation:** Document parameter constraints or separate evidence probing from skill acquisition transitions in future BKT fitting.

### 2. **Low Severity: Uncommitted Working Tree State**
- **Location:** Repository root
- **Description:** All Week 2 implementation files (`src/`, `config/`, `tests/test_m1_learner_state.py`, `evaluation/results/`, `requirements.txt`, `.github/workflows/ci.yml`) remain uncommitted in the git working tree. `git log` contains only the initial commit `002eb51`.
- **Impact:** No version-controlled release tag exists for Week 2.
- **Recommendation:** Stage and commit Week 2 deliverables with proper commit message tags (e.g. `TC-1.2`, `TC-3.1`, `TC-3.2`, `TC-7.1`).

### 3. **Low Severity: Empty `score_terms` in Static Baseline Trace**
- **Location:** `src/planning/static_baseline.py:127`
- **Description:** Trace entries emitted by the static baseline planner populate `score_terms` as an empty dictionary `{}`.
- **Impact:** Multi-objective policy score explanations are not exercised until Week 3+ scoring planners are implemented.

---

## 4. Unsupported Claims in Implementer Summary

| Claim in Implementer Summary | Audit Finding & Empirical Evidence |
|---|---|
| *"0 failures, no deviations, all verified"* | **Misleading.** While 29 active tests pass, 9 tests are skipped (`NOT_IMPLEMENTED`), BKT default parameters were tuned to make `test_conflicting_evidence_no_unsupported_confidence` pass, all Week 2 files remain uncommitted, and dataset provenance tables are empty placeholders. |
| *"Full test suite clean execution"* | **Partially True.** 29 tests pass and 9 tests skip. However, running `python -m src.planning.benchmark` using standard system Python fails with `ModuleNotFoundError: No module named 'networkx'` because dependencies are installed under Anaconda Python 3.11 (`C:\Users\bhuva\anaconda3\python.exe`). |
| *"Acceptance criteria fully met for Week 2"* | **Partially True.** Core W2 code and tests exist and pass locally, but repository housekeeping (commit, tagging, `weekly/W2.md`, dataset provenance documentation) is incomplete. |

---

## 5. Summary of Claims Guidelines

### Safe to Claim in W2 Report
- Implemented and validated graph loader and 5-check graph validator (`src/curriculum/graph.py`) passing all 6 tests in `test_m1_curriculum_graph.py`.
- Implemented `ConceptState` model (`src/state/learner_state.py`) with Beta evidence variance $\sigma^2 = \frac{p(1-p)}{\kappa+1}$, strict precedence classification (`Uncertain` if $\sigma^2 > 0.05$ or $n < 3$), and valid profile loading across budgets (5, 10, 15, 30 min).
- Implemented static baseline planner (`src/planning/static_baseline.py`) with block indivisibility preservation and deterministic topological packing.
- Implemented infeasibility detection engine (`src/planning/feasibility.py`) returning `INFEASIBLE_PROVED` with `BLOCK_EXCEEDS_DAILY_BUDGET` and minimum budget fixes, `CAPACITY_EXCEEDED` for $W_{req} > D \cdot B$, and `HEURISTIC_NO_PLAN` for packing failures.
- Implemented score-per-minute greedy scheduler (`src/planning/greedy.py`) and exact DP oracle (`src/planning/oracle.py`) with 20-item cap and timeout protection.
- Executed 250-instance benchmark across 5 seeds (`{7, 17, 27, 37, 47}`), establishing mean greedy-to-optimal ratio of `0.9737`, 5th percentile `0.8270`, and minimum ratio `0.2143` (verified valid knapsack instance 215).
- Implemented decision trace schema (`src/trace/schema.py`), candidate universe extractor (`src/trace/universe.py`), and automated trace completeness checker (`src/trace/checker.py`) verifying 1 entry per candidate per day.
- Created `requirements.txt` with pinned versions and `.github/workflows/ci.yml`.

### Do NOT Claim
- Do NOT claim universal 95% optimality for the greedy scheduler (the 10-minute counterexample $\rho = 0.6667$ and minimum benchmark ratio $\rho = 0.2143$ disprove universal per-instance guarantees).
- Do NOT claim Beta belief variance $\sigma^2$ is an empirically calibrated posterior (it is a heuristic evidence-count proxy).
- Do NOT claim dynamic replanning, CAT/IRT diagnostics, HLR review decay, or multi-policy evaluation are implemented (these are skipped W3+ stubs).
- Do NOT claim real Junyi/ASSISTments datasets are downloaded or preprocessed (`data/raw/` and `data/processed/` remain empty).
- Do NOT claim Week 2 work is committed or tagged in Git (`git status` shows all files uncommitted).
