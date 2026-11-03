# Module Ownership Pack: Path Planning & Learner Cognitive State (Track A)

This ownership pack provides the complete technical and operational documentation required to explain, test, and modify the planning, state, and diagnostic subsystems without assistant guidance.

---

## 1. End-to-End Data-to-Plan Pipeline

The execution path from curriculum and diagnostic inputs to an explainable daily schedule follows six sequential stages:

```
Curriculum JSON ──> Graph Validation ──> Adaptive Diagnostic (CAT) ──> ConceptState Priors ──> Feasibility Check ──> Plan Generation (Static / Replan) ──> Trace Verification
```

### Step 1: Curriculum Ingestion and Graph Validation
- **File:** `src/curriculum/graph.py`
- **Functions:**
  - `load_graph(path: str) -> nx.DiGraph`
    Reads curriculum JSON and constructs a NetworkX directed graph with node attributes (`baseline_duration`, `base_difficulty`, `exercises`) and edge attributes (`importance`).
  - `validate_graph(g: nx.DiGraph) -> List[GraphErrorCode]`
    Validates structural invariants: checks for DAG acyclicity via Tarjan's SCC algorithm, positive baseline durations, valid base difficulties in $[0.05, 0.95]$, and finite weights.

### Step 2: Adaptive Diagnostic Assessment & Prior Calibration
- **File:** `src/diagnostic/diagnostic.py`
- **Functions:**
  - `load_item_bank_and_qmatrix(bank_source, qmatrix_source, curriculum_source) -> Tuple[List[str], np.ndarray, Dict[str, str], List[str]]`
    Loads the 24-item synthetic bank and item-to-concept Q-matrix.
  - `run_adaptive_diagnostic(respond: Callable[[str], int], bank_source: Any, qmatrix_source: Any, curriculum_source: Any, stopping_variance: Optional[float] = None, max_questions: Optional[int] = None) -> DiagnosticResult`
    Executes Computerized Adaptive Testing (CAT) using maximum Fisher information item selection and numerical maximum likelihood ability estimation ($\hat\theta$).
  - `ability_to_prior(theta: float, difficulty: float) -> float`
    Maps estimated scalar ability $\hat\theta$ to initial concept mastery probability $p_0 = \sigma(\hat\theta - b)$ via logistic sigmoid.

### Step 3: Cognitive State Representation & Policy Configuration
- **File:** `src/state/policy.py`
  - `PolicyConfig(p_S: float = 0.10, p_G: float = 0.25, p_T: float = 0.10, window_size: int = 4, mastered_p: float = 0.85, weak_p: float = 0.40, sigma2_max: float = 0.05, min_obs: int = 3, kappa0: float = 2.0)`
    Defines classification thresholds and evidence parameters.
  - `default_policy() -> DefaultPolicyResult`
- **File:** `src/state/learner_state.py`
  - `ConceptState(A: float = 1.0, B: float = 1.0, n: int = 0, history: List[int] = field(default_factory=list))`
    Maintains Beta-distributed cognitive state proxy where $p = A / (A + B)$, $\kappa = A + B$, and observation count $n$.
  - `update(correct: Union[bool, int], policy: Optional[PolicyConfig] = None) -> ConceptState`
    Applies BKT Bayesian observation likelihood update followed by transition probability $p_T$. Increments $\kappa$ and $n$, appending outcome to history window.
  - `classify(policy: Optional[PolicyConfig] = None) -> str`
    Enforces mutually exclusive 4-way classification with strict precedence: `Uncertain` ($n < \text{min\_obs} \lor \sigma^2 > \sigma^2_{\max}$), `Mastered` ($p \ge 0.85 \land \sigma^2 \le 0.05 \land n \ge 3 \land \text{quorum}$), `Weak` ($p < 0.40 \land \sigma^2 \le 0.05 \land n \ge 3 \land \text{quorum}$), else `Developing`.

### Step 4: Feasibility Pre-Checks & Candidate Universe Extraction
- **File:** `src/trace/universe.py`
  - `get_candidate_universe(g: nx.DiGraph, target_node: str) -> Set[str]`
    Extracts all topological ancestors of `target_node` plus the target node itself.
- **File:** `src/planning/feasibility.py`
  - `check_feasibility(g: nx.DiGraph, required_nodes: Set[str], budget: int, deadline_days: int) -> Tuple[FeasibilityStatus, Dict[str, Any]]`
    Performs block indivisibility check ($\max \text{dur} \le \text{budget}$) and aggregate capacity check ($\sum \text{dur} \le \text{deadline} \times \text{budget}$).

### Step 5: Planning Engine & Closed-Loop Replanning
- **File:** `src/planning/service.py`
  - `plan_request(graph: nx.DiGraph, learner_states: Dict[str, ConceptState], budget: int, deadline_days: int, targets: Union[str, List[str]], policy: Optional[PolicyConfig] = None) -> PlanResult`
    Validates input parameters and invokes `generate_static_plan`.
- **File:** `src/planning/static_baseline.py`
  - `generate_static_plan(g: nx.DiGraph, learner_states: Dict[str, ConceptState], budget: int, deadline_days: int, target_node: str, ...) -> Dict[str, Any]`
    Partitions candidate universe into `evidence_mastered` and `required_nodes`, topologically sorts required nodes, and packs them into daily budgets.
- **File:** `src/planning/replan.py`
  - `replan(state: ReplanState, event: Optional[ReplanEvent] = None) -> Dict[str, Any]`
    Closed-loop dynamic replanner executing 4 priority phases per day:
    1. Remediation queue for failed prerequisites (`Weak` concepts).
    2. Planned curriculum progress toward target (gated by prerequisite mastery).
    3. Due spaced reviews ordered by lowest Half-Life Regression recall.
    4. Residual candidate trace recording.

### Step 6: Audit Trace Completeness & Explainability Verification
- **File:** `src/trace/checker.py`
  - `check_trace(candidate_universe: Set[str], trace: List[Dict[str, Any]], num_days: int, budget: Optional[int] = None) -> bool`
    Validates that every candidate node is evaluated exactly once per day with a valid decision, reason code, and state.
  - `check_no_plan_trace(trace: Dict[str, Any]) -> bool`
    Validates infeasibility traces for capacity-exceeded or constraint-unmet plans.

---

## 2. Mastery Probability ($p$) vs. Uncertainty Proxy ($\sigma^2$)

### Mathematical Definitions & Code Locations
In `src/state/learner_state.py`:
- **Posterior Mastery Probability $p$ (line 70):**
  $$p = \frac{A}{A + B} = \frac{A}{\kappa}$$
  Represents the model's Bayesian point estimate of whether the learner has acquired latent mastery of the concept. Updated dynamically via BKT update equations on each practice attempt (lines 142–150).
- **Uncertainty Confidence Proxy $\sigma^2$ (line 78):**
  $$\sigma^2 = \frac{p(1 - p)}{\kappa + 1}$$
  Represents the variance of the Beta belief distribution proxy. It is an uncalibrated heuristic measure of statistical dispersion. As more observations accumulate, $\kappa$ increments ($\kappa \gets \kappa + 1$), causing $\sigma^2 \to 0$ even if $p$ remains intermediate.

### Concrete Numeric Example (Computed by Code)
Starting from cold-start state ($A=1.0, B=1.0, n=0$) under default BKT parameters ($p_S=0.10, p_G=0.25, p_T=0.10$):

```python
from src.state.learner_state import ConceptState
from src.state.policy import default_policy

policy, _ = default_policy()
state = ConceptState.cold_start()
# Initial state:
# p = 0.500000, kappa = 2.0, sigma2 = 0.083333, n = 0 -> Classification: 'Uncertain' (sigma2 > 0.05 and n < 3)

state.update(correct=1, policy=policy)
# After 1 correct attempt:
# p = 0.804348, kappa = 3.0, sigma2 = 0.039343, n = 1 -> Classification: 'Uncertain' (n < 3)
```

**Observation:** Notice that after 1 correct attempt, $p$ jumped to **$0.8043$** and variance dropped to **$0.0393 \le 0.05$**. Despite high estimated mastery and low variance, the state remains classified as **`Uncertain`** because $n = 1 < \text{min\_obs} (3)$.

---

## 3. Reproducible Counterexamples & Commands

### Counterexample 1: Greedy Score-per-Minute Suboptimality (12/18)
The greedy score-per-minute heuristic is susceptible to knapsack suboptimality when discrete block durations cannot be packed efficiently.

**Command:**
```pwsh
$env:PYTHONPATH='.'; .venv\Scripts\python.exe -c "from src.planning.greedy import run_greedy_scheduler; from src.planning.oracle import run_exhaustive_oracle; items = [{'node_id': 'A', 'duration': 6, 'score': 12, 'prerequisites': set()}, {'node_id': 'B', 'duration': 5, 'score': 9, 'prerequisites': set()}, {'node_id': 'C', 'duration': 5, 'score': 9, 'prerequisites': set()}]; budget = 10; g_score = run_greedy_scheduler(items, budget); o_score = run_exhaustive_oracle(items, budget); print(f'Greedy score: {g_score}, Oracle score: {o_score}, Ratio: {g_score/o_score:.4f}')"
```
**Output:**
```text
Greedy score: 12, Oracle score: 18, Ratio: 0.6667
```

### Counterexample 2: Trace Incompleteness Validation
The trace checker strictly validates complete candidate coverage for every day in the planning horizon. If any candidate node in `candidate_universe` is omitted, `check_trace` raises an immediate `ValueError`.

**Command:**
```pwsh
$env:PYTHONPATH='.'; .venv\Scripts\python.exe -c "from src.trace.checker import check_trace; universe = {'A', 'B'}; incomplete_trace = [{'node_id': 'A', 'day': 1, 'decision': 'SELECTED', 'reason_code': 'SELECTED', 'concept_state': {'p': 0.5, 'kappa': 2.0, 'sigma2': 0.083, 'n': 0, 'class': 'Uncertain'}, 'constraints': {'budget': 10, 'remaining_budget': 5, 'prerequisites': {}}, 'score_terms': {}, 'policy_version': 'v1'}]; check_trace(universe, incomplete_trace, num_days=1)"
```
**Output:**
```text
ValueError: Trace missing candidate nodes on day 1: ['B']
```

---

## 4. Reading Guide: Codebase Navigation Order

When onboarding to the planning and state architecture, read the files in the following order:

1. [src/curriculum/graph.py](file:///c:/Users/bhuva/Downloads/DAT11/src/curriculum/graph.py): Curriculum DAG parsing and validation rules.
2. [src/state/policy.py](file:///c:/Users/bhuva/Downloads/DAT11/src/state/policy.py): Hyperparameter schema (`PolicyConfig`) and threshold definitions.
3. [src/state/learner_state.py](file:///c:/Users/bhuva/Downloads/DAT11/src/state/learner_state.py): Cognitive state representation, BKT Bayesian updates, and classification gate logic.
4. [src/diagnostic/diagnostic.py](file:///c:/Users/bhuva/Downloads/DAT11/src/diagnostic/diagnostic.py): CAT adaptive test engine and ability-to-prior mapping.
5. [src/planning/feasibility.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/feasibility.py): Mathematical feasibility checks (block budget and horizon capacity).
6. [src/planning/static_baseline.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/static_baseline.py): Deterministic topological sort planner.
7. [src/planning/difficulty.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/difficulty.py): 2-Up / 1-Down staircase difficulty stepping.
8. [src/planning/review.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/review.py): Half-Life Regression memory decay and remediation ancestor selection.
9. [src/planning/replan.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/replan.py): Core closed-loop dynamic replanning engine.
10. [src/planning/service.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/service.py): Public service endpoint for plan requests.
11. [src/trace/checker.py](file:///c:/Users/bhuva/Downloads/DAT11/src/trace/checker.py): Rigorous validation harness for plan and trace contracts.

---

## 5. Six Likely Questions with Code Pointers

### Q1: How does a concept state transition from `Uncertain` to `Mastered`?
**Answer:** In [src/state/learner_state.py](file:///c:/Users/bhuva/Downloads/DAT11/src/state/learner_state.py#L178-L189) (`ConceptState.classify`), a concept must satisfy all of the following:
1. $n \ge \text{min\_obs}$ (default: 3)
2. $\sigma^2 \le \sigma^2_{\max}$ (default: 0.05)
3. $p \ge \text{mastered\_p}$ (default: 0.85)
4. History window must be full ($\ge \text{window\_size}$, default: 4) with at least $\text{quorum}$ (default: 3) correct outcomes.

### Q2: Why does dynamic replanning produce 0 activities when a prerequisite is Uncertain?
**Answer:** In [src/planning/replan.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/replan.py#L509-L520), line 509 specifies: `elif p in completed_nodes and p_class not in ("Weak", "Uncertain"):`. If a prerequisite is `Uncertain`, it falls through to `else:`, marking `prereqs_met = False` and filtering downstream nodes with `UNCERTAIN_NEEDS_ASSESSMENT`. Because completed nodes are omitted from `remaining_nodes` and `remed_queue`, no candidate can be scheduled.

### Q3: How does the static baseline planner avoid this deadlock?
**Answer:** In [src/planning/static_baseline.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/static_baseline.py#L44-L50), the static planner checks `state.classify() == "Mastered"`. Unmastered concepts are placed in `required_nodes` and scheduled in topological order. It assumes future scheduled execution clears prerequisites without re-checking intermediate runtime uncertainty.

### Q4: What is the architectural boundary between `src/simulation` and `src/planning`?
**Answer:** As specified in [src/evaluation/integrated.py](file:///c:/Users/bhuva/Downloads/DAT11/src/evaluation/integrated.py#L6-L12) and enforced by AST test in [tests/test_simulation.py](file:///c:/Users/bhuva/Downloads/DAT11/tests/test_simulation.py), code in `src/planning` and `src/state` must NEVER import `EvaluatorView` or read latent mastery. Planners receive only observable binary scored outcomes from `SimulatedLearner.respond()`.

### Q5: How are budget and deadline feasibility verified mathematically before scheduling?
**Answer:** In [src/planning/feasibility.py](file:///c:/Users/bhuva/Downloads/DAT11/src/planning/feasibility.py#L37-L85) (`check_feasibility`):
1. **Per-activity check:** If $\exists u \in \text{req}: \text{dur}(u) > \text{budget}$, returns `INFEASIBLE_PROVED` with `BLOCK_EXCEEDS_DAILY_BUDGET`.
2. **Aggregate capacity check:** If $\sum_{u \in \text{req}} \text{dur}(u) > \text{deadline\_days} \times \text{budget}$, returns `INFEASIBLE_PROVED` with `CAPACITY_EXCEEDED` and lower-bound fix recommendations.

### Q6: How does the trace checker enforce explainability?
**Answer:** In [src/trace/checker.py](file:///c:/Users/bhuva/Downloads/DAT11/src/trace/checker.py#L50-L120) (`check_trace`), every candidate node in `candidate_universe` must have an entry for each day in $1 \dots \text{num\_days}$, with valid `decision` in `{SELECTED, FILTERED}`, valid `reason_code` in `ReasonCode`, observable `concept_state`, and consistent remaining budget bounds.

---

## 6. Live Code Change & Practice Task Specifications

### Live Code Change (Applied on `practice/a-live`)
- **Target File:** `src/planning/feasibility.py`
- **Change:** Add helper function `calculate_minimum_capacity` to calculate total duration of required nodes:
  ```python
  def calculate_minimum_capacity(g: nx.DiGraph, required_nodes: Set[str]) -> int:
      """Calculates total required work duration across required curriculum nodes."""
      return sum(g.nodes[nid].get("baseline_duration", 0) for nid in required_nodes)
  ```
- **Test File:** `tests/test_practice_a_live.py`
- **Expected Diff:**
  ```diff
  diff --git a/src/planning/feasibility.py b/src/planning/feasibility.py
  index 8b1cb3b..b2e535e 100644
  --- a/src/planning/feasibility.py
  +++ b/src/planning/feasibility.py
  @@ -19,6 +19,11 @@ class InfeasibilityReason(str, Enum):
       SCHEDULING_CONSTRAINTS_UNMET = "SCHEDULING_CONSTRAINTS_UNMET"
   
   
  +def calculate_minimum_capacity(g: nx.DiGraph, required_nodes: Set[str]) -> int:
  +    """Calculates total required work duration across required curriculum nodes."""
  +    return sum(g.nodes[nid].get("baseline_duration", 0) for nid in required_nodes)
  +
  +
   def check_feasibility(
       g: nx.DiGraph,
       required_nodes: Set[str],
  ```

### Practice Task Change (Applied on `practice/a-task`)
- **Target File:** `src/planning/service.py`
- **Change:** Add helper function `is_plan_feasible` checking if a `PlanResult` yielded a valid feasible schedule:
  ```python
  def is_plan_feasible(plan_result: PlanResult) -> bool:
      """Returns True if plan_result is valid and generated a feasible schedule."""
      if not plan_result.is_valid or not plan_result.plan:
          return False
      return plan_result.plan.get("status") == FeasibilityStatus.FEASIBLE
  ```
- **Test File:** `tests/test_practice_a_task.py`
- **Expected Diff:**
  ```diff
  diff --git a/src/planning/service.py b/src/planning/service.py
  index c66657c..0b767eb 100644
  --- a/src/planning/service.py
  +++ b/src/planning/service.py
  @@ -7,6 +7,7 @@ import networkx as nx
   from src.curriculum.graph import validate_graph
   from src.curriculum.errors import GraphErrorCode
   from src.state.learner_state import ConceptState
  +from src.planning.feasibility import FeasibilityStatus
   from src.state.policy import PolicyConfig, default_policy
   from src.planning.static_baseline import generate_static_plan
   
  @@ -33,6 +34,13 @@ class PlanResult:
           except KeyError:
               return default
   
  +
  +def is_plan_feasible(plan_result: PlanResult) -> bool:
  +    """Returns True if plan_result is valid and generated a feasible schedule."""
  +    if not plan_result.is_valid or not plan_result.plan:
  +        return False
  +    return plan_result.plan.get("status") == FeasibilityStatus.FEASIBLE
  +
   
   def plan_request(
       graph: nx.DiGraph,
  ```
