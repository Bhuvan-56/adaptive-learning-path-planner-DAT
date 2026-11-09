# Ownership & Architecture Guide: Evaluation, Planning & Retention Engine (Module Pack B)

This document provides a self-contained guide to explaining, testing, and modifying the path planner and evaluation harness without agent dependency.

---

## 1. The Data-to-Plan Path (End-to-End Workflow)

The data pipeline progresses through 9 strictly isolated stages from curriculum graph parsing to deferred retention assessment:

1. **Curriculum Graph Loading:**
   - **File:** `src/curriculum/graph.py`
   - **Function:** `load_graph(path: str) -> nx.DiGraph`
   - **Role:** Loads curriculum nodes, difficulty values, prerequisites, and edge dependencies into a Directed Acyclic Graph (DAG).

2. **Diagnostic Prior Initialization:**
   - **File:** `src/state/learner_state.py` / `src/diagnostic/cat.py`
   - **Function:** `ConceptState(p: float, kappa: float, sigma2: float, n: int, class_name: str)`
   - **Role:** Instantiates prior belief for each concept (e.g., $A=1.0, B=1.0 \implies p=0.50$ for cold start, or CAT-derived priors).

3. **Observable Response Simulation (Evaluation Only):**
   - **File:** `src/simulation/simulator.py`
   - **Function:** `SimulatedLearner.generate_response(concept_id: str, difficulty: float) -> Tuple[bool, float]`
   - **Role:** Generates synthetic response $(y \in \{0, 1\}, \text{latency})$ using latent mastery $L \in \{0, 1\}$ and noise parameters ($p_G, p_S$). Planners never observe $L$.

4. **Cognitive State Belief Updating:**
   - **File:** `src/state/bkt_adapter.py`
   - **Function:** `bkt_update(state: ConceptState, correct: bool, p_G: float = 0.2, p_S: float = 0.1, p_T: float = 0.1) -> ConceptState`
   - **Role:** Updates posterior belief $p$ and evidence counter $n$ via standard Bayesian Knowledge Tracing.

5. **Candidate Universe Discovery:**
   - **File:** `src/trace/universe.py`
   - **Function:** `get_candidate_universe(graph: nx.DiGraph, completed_nodes: Set[str], current_day: int, target_nodes: Optional[Set[str]] = None) -> Set[str]`
   - **Role:** Determines all curriculum nodes that the planner is legally eligible to consider on `current_day`.

6. **Admissibility & Prerequisite Filtering:**
   - **File:** `src/planning/admissibility.py`
   - **Function:** `filter_admissible(graph: nx.DiGraph, completed_nodes: Set[str], learner_states: Dict[str, ConceptState], current_day: int, remaining_budget: int) -> Tuple[List[str], List[Dict[str, Any]]]`
   - **Role:** Prunes candidates failing prerequisites or budget constraints, generating structured filter entries with `ReasonCode`.

7. **Knapsack Optimization & Path Replanning:**
   - **File:** `src/planning/replan.py` / `src/planning/service.py`
   - **Function:** `plan_request(graph: nx.DiGraph, learner_id: str, current_day: int, budget: int, horizon: int, states: Dict[str, ConceptState], ...) -> Dict[str, Any]`
   - **Role:** Solves daily score-density bounded knapsack selection, choosing activities that maximize utility under daily time budgets.

8. **Audit Trace Schema Verification:**
   - **File:** `src/trace/checker.py`
   - **Function:** `check_trace(universe: Set[str], trace: List[Dict[str, Any]], num_days: int, budget: Optional[int] = None) -> bool`
   - **Function:** `check_no_plan_trace(trace: Dict[str, Any]) -> bool`
   - **Role:** Strictly validates that all candidate nodes across all days are accounted for with valid decisions, reason codes, and non-empty state snapshots.

9. **Deferred Retention Quiz Administration:**
   - **File:** `src/evaluation/retention.py`
   - **Function:** `administer_retention_quiz(learner: SimulatedLearner, studied_concepts: List[str], n_items: Optional[int] = None, delay_days: Optional[int] = None, difficulty: Optional[float] = None, config_source: Optional[Union[str, Dict[str, Any]]] = None) -> Dict[str, Any]`
   - **Role:** Simulates a post-horizon quiz after $D = 7$ days delay with $N = 5$ items per concept to evaluate recall retention under forgetting.

---

## 2. BKT Probability vs. Uncertainty Proxy

### Code Locations
- Posterior probability and uncertainty proxy formulas: [`src/state/learner_state.py:25-30`](../../src/state/learner_state.py#L25-L30)
- BKT belief updates: [`src/state/bkt_adapter.py:35-85`](../../src/state/bkt_adapter.py#L35-L85)

### Mathematical Distinction
- **$p$ (Posterior Mastery Probability):**
  $$p = \frac{A}{A + B}$$
  Represents the point belief that the learner has mastered the latent concept. Used for threshold classification:
  - $p \ge 0.85 \implies \text{Mastered}$
  - $0.40 < p < 0.85 \implies \text{Developing} / \text{Uncertain}$
  - $p \le 0.40 \implies \text{Novice}$
- **$\sigma^2$ (Uncertainty Proxy):**
  $$\sigma^2 = \frac{p(1 - p)}{\kappa + 1} = \frac{A \cdot B}{(A + B)^2 (A + B + 1)}$$
  Derived from the variance of a $\text{Beta}(A, B)$ distribution with pseudo-counts $\kappa = A + B$.
  **Critical Caveat:** $\sigma^2$ is an *uncalibrated heuristic proxy* of epistemic variance, not a calibrated Bayesian credible interval or frequentist confidence interval.

### Computed Numeric Example
1. **Cold Start (Uniform Prior $A=1.0, B=1.0$):**
   - $p_0 = \frac{1.0}{1.0 + 1.0} = 0.50$
   - $\kappa_0 = 1.0 + 1.0 = 2.0$
   - $\sigma^2_0 = \frac{0.50 \times (1 - 0.50)}{2.0 + 1.0} = \frac{0.25}{3.0} \approx 0.08333$
2. **Observation 1 (Correct, $A \leftarrow 2.0, B \leftarrow 1.0$):**
   - $p_1 = \frac{2.0}{2.0 + 1.0} = \frac{2}{3} \approx 0.6667$
   - $\kappa_1 = 2.0 + 1.0 = 3.0$
   - $\sigma^2_1 = \frac{(2/3) \times (1/3)}{3.0 + 1.0} = \frac{2/9}{4.0} = \frac{1}{18} \approx 0.05556$
3. **Observation 2 (Correct, $A \leftarrow 3.0, B \leftarrow 1.0$):**
   - $p_2 = \frac{3.0}{3.0 + 1.0} = 0.75$
   - $\kappa_2 = 3.0 + 1.0 = 4.0$
   - $\sigma^2_2 = \frac{0.75 \times 0.25}{4.0 + 1.0} = \frac{0.1875}{5.0} = 0.03750$

---

## 3. Reproducing Counterexamples

### A. Knapsack Suboptimality Oracle Counterexample (12 vs. 18)
- **Reproduction Command:**
  ```powershell
  .venv_w2\Scripts\python.exe -m pytest tests/test_benchmark_invariance.py -k "test_counterexample_12_18" -v
  ```
- **Scenario:**
  - Budget = 10 minutes.
  - Items:
    - Item 1: Duration = 6 min, Score = 12 (Density = 2.0 score/min)
    - Item 2: Duration = 5 min, Score = 9  (Density = 1.8 score/min)
    - Item 3: Duration = 5 min, Score = 9  (Density = 1.8 score/min)
- **Outcome:**
  - Greedy selects Item 1 first (score 12), leaving 4 min remaining (neither Item 2 nor Item 3 fits). Greedy total = 12.
  - Oracle selects Item 2 + Item 3 (duration 5 + 5 = 10 min). Oracle total = 18.
  - Ratio: $\rho = \frac{12}{18} = 0.6667$, disproving any claim of a universal 95% greedy approximation ratio.
- **Terminal Output:**
  ```text
  tests/test_benchmark_invariance.py::test_counterexample_12_18 PASSED [100%]
  ```

### B. Trace Contract Validation Counterexample
- **Reproduction Command:**
  ```powershell
  .venv_w2\Scripts\python.exe -m pytest tests/test_m7_trace_contract.py -k "test_check_trace_missing_whole_day_2_of_2 or test_check_trace_mastered_reason_with_uncertain_state" -v
  ```
- **Scenario:**
  1. Multi-day schedule (2 days) omitting day 2 entries entirely.
  2. Candidate recorded with `reason_code="ALREADY_MASTERED"` but concept state classified as `Uncertain`.
- **Outcome:**
  `check_trace` strictly raises `ValueError`:
  - `ValueError: Trace does not contain entries for day 2 of 2`
  - `ValueError: Trace entry for node A on day 1 has ALREADY_MASTERED reason but concept class is Uncertain (must be Mastered)`
- **Terminal Output:**
  ```text
  tests/test_m7_trace_contract.py::test_check_trace_missing_whole_day_2_of_2 PASSED [ 50%]
  tests/test_m7_trace_contract.py::test_check_trace_mastered_reason_with_uncertain_state PASSED [100%]
  ```

---

## 4. Source Files to Read in Order

To understand or extend the evaluation and planning systems, read files in this exact sequence:
1. `src/curriculum/graph.py`: DAG representation and prerequisite topology.
2. `src/state/learner_state.py` and `src/state/bkt_adapter.py`: Belief representations and Bayesian Knowledge Tracing formulas.
3. `src/trace/schema.py` and `src/trace/checker.py`: Contract schema, decision reason codes, and validation invariants.
4. `src/planning/admissibility.py` and `src/planning/replan.py`: Candidate pruning and score-density knapsack scheduling.
5. `src/simulation/simulator.py`: Synthetic learner dynamics, noise parameters, and scenario generators.
6. `src/evaluation/retention.py` and `src/evaluation/integrated.py`: Retention quiz administration and the multi-seed closed-loop evaluation harness.

---

## 5. Six Common Architectural Questions & Answers

### Q1: Why does `SimulatedLearner` never import from `src/planning` or `src/state`?
**A:** Architectural decoupling: true latent mastery ($L \in \{0, 1\}$) must never leak into planning algorithms. Planners only observe noisy binary exercise responses.
*Code:* [`src/evaluation/integrated.py:4-12`](../../src/evaluation/integrated.py#L4-L12).

### Q2: Why did all 5 ablations produce identical mastery outcomes under Scenario S0?
**A:** Under default scenario S0, `MatchedBKTGenerator` has forgetting rate $p_F = 0.0$ and difficulty sensitivity $d_{sens} = 0.0$. Thus, spaced review and difficulty-stepping ablations do not alter latent transition probabilities in simulator behavior.
*Code:* [`src/simulation/simulator.py:180-220`](../../src/simulation/simulator.py#L180-L220).

### Q3: What guarantees that an infeasible schedule emits a structured trace instead of failing silently?
**A:** When remaining budget is strictly less than the minimal activity block, the planner emits a no-plan trace with status `INFEASIBLE_PROVED` and reason code `BLOCK_EXCEEDS_DAILY_BUDGET`, validated by `check_no_plan_trace`.
*Code:* [`src/trace/checker.py:65-90`](../../src/trace/checker.py#L65-L90).

### Q4: How does the retention quiz avoid data leakage from the simulation?
**A:** Retention administration reads `studied_concepts` and evaluates post-horizon responses on a cloned learner state without feeding any feedback or state updates back into the planner.
*Code:* [`src/evaluation/retention.py:100-145`](../../src/evaluation/retention.py#L100-L145).

### Q5: Why is $\sigma^2$ considered an uncalibrated proxy rather than a Bayesian credible interval?
**A:** $\sigma^2$ is purely the variance of an idealized Beta distribution with arbitrary prior pseudo-counts $\kappa = A+B$. It has not been calibrated or empirically validated against real-world posterior predictive intervals.
*Code:* [`src/state/learner_state.py:29-30`](../../src/state/learner_state.py#L29-L30).

### Q6: How does multi-seed evaluation prevent cohort contamination across arms?
**A:** Each seed constructs an independent cohort of `SimulatedLearner` instances. For each arm, identical clones of that cohort are simulated independently, ensuring arms are paired across learners within each seed.
*Code:* [`src/evaluation/integrated.py:530-580`](../../src/evaluation/integrated.py#L530-L580).

---

## 6. Live Code Change & Expected Diff

### Change Description
Add range validation for reference `difficulty` ($0.0 \le \text{difficulty} \le 1.0$) in `src/evaluation/retention.py::administer_retention_quiz`.

### Expected Diff:
```diff
--- a/src/evaluation/retention.py
+++ b/src/evaluation/retention.py
@@ -107,6 +107,8 @@ def administer_retention_quiz(
     if d < 0:
         raise ValueError(f"delay_days must be non-negative, got {d}")
+    if not (0.0 <= diff <= 1.0):
+        raise ValueError(f"difficulty must be between 0.0 and 1.0, got {diff}")
 
     # 1. Advance simulation environment by D days (decaying mastered concepts if p_F > 0)
```

### Verification Test:
```python
def test_administer_retention_quiz_invalid_difficulty_raises():
    learner = SimulatedLearner(learner_id="test_diff", initial_mastery={})
    with pytest.raises(ValueError, match="difficulty must be between 0.0 and 1.0"):
        administer_retention_quiz(learner, studied_concepts=["A"], difficulty=1.5)
```

---

## 7. Practice Change Task & Expected Diff

### Task Description
Add non-negative delay validation (`delay_days_D >= 0`) in `src/evaluation/retention.py::load_retention_parameters`.

### Expected Diff:
```diff
--- a/src/evaluation/retention.py
+++ b/src/evaluation/retention.py
@@ -73,6 +73,8 @@ def load_retention_parameters(
     d = int(ret_block.get("delay_days_D", controls_block.get("retention_delay_days", DEFAULT_RETENTION_D)))
     diff = float(ret_block.get("reference_difficulty", DEFAULT_REFERENCE_DIFFICULTY))
 
+    if d < 0:
+        raise ValueError(f"Config delay_days must be non-negative, got {d}")
     return n, d, diff
```

### Verification Test:
```python
def test_load_retention_parameters_negative_delay_raises():
    cfg = {"retention": {"delay_days_D": -5}}
    with pytest.raises(ValueError, match="Config delay_days must be non-negative"):
        load_retention_parameters(cfg)
```
