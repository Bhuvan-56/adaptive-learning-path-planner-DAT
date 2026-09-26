# Formal Curriculum and Learner-State Models

## Formal Learner-State Model

The system continuously tracks and updates the learner's cognitive state for each
concept $c$ at time $t$ using the mathematical representation
$S_{c,t} = (p_{c,t}, \sigma^2_{c,t}, d_{c,t}, R_{c,t})$.

### Entities and Fields

- **Mastery Probability ($p_{c,t}$):** The estimated likelihood (from 0 to 1) that the
  learner understands the concept, updated continuously via Bayesian Knowledge Tracing
  (BKT).

- **Uncertainty ($\sigma^2_{c,t}$):** Because standard BKT does not output posterior
  variance, the system separately maintains a Beta belief, $\text{Beta}(A_{c,t},
  B_{c,t})$, matched to the mastery estimate. The evidence concentration $\kappa$ grows
  by 1 for each scored concept-level observation.

- **Current Difficulty ($d_{c,t}$):** The normalized challenge level of the exercises
  currently being presented to the learner, bounded within $[0.05, 0.95]$.

- **Predicted Recall ($R_{c,t}$):** The probability that the learner retains the
  information, calculated using Half-Life Regression (HLR) to determine when spaced
  reviews are required.

### Learner-State Constraints & Thresholds

Concepts are strictly classified into distinct states based on specific combinations of
these fields, evaluated in the following precedence order:

- **Uncertain:** $\sigma^2_{c,t} > 0.05$. This state strictly overrides all others for
  planning and assessment decisions.
- **Mastered:** $\sigma^2_{c,t} \le 0.05$, $p_{c,t} \ge 0.85$, and at least 3 scored
  observations have been recorded. A concept cannot be marked as Mastered solely due to
  low variance.
- **Weak:** $\sigma^2_{c,t} \le 0.05$, $p_{c,t} \le 0.40$, and at least 3 scored
  observations.
- **Developing:** All remaining field combinations that do not satisfy the above rules.

## Formal Curriculum Model

The curriculum is structurally architected as a queryable Directed Acyclic Graph (DAG),
mathematically denoted as $G = (V, E)$.

### Entities and Fields

- **Node Schema ($v$):** Each node represents a specific learning concept and must
  contain the fields $\{Node\_ID, Concept\_Name, Baseline\_Duration, Exercises,
  Base\_Difficulty\}$.
  - `Baseline_Duration` is measured in minutes.
  - `Base_Difficulty` is a normalized continuous value bounded within $[0.05, 0.95]$.

- **Edge Schema ($e$):** Each directed edge represents a mandatory prerequisite
  relationship and must contain the fields $\{Source\_Node\_ID, Target\_Node\_ID,
  Importance\}$. The source node must be Mastered (and not Uncertain) before the target
  node unlocks.

### Graph Validation Constraints

Before any planning engine operations occur, the curriculum administrator's DAG must
pass five specific hard constraints:

1. Every prerequisite node referenced by an edge must explicitly exist in the node list.
2. Every baseline duration must be a positive, non-null value.
3. Every normalized difficulty value must be strictly bounded within $[0.05, 0.95]$.
4. No node is permitted to contain a self-loop.
5. Tarjan's strongly connected components algorithm must detect zero cyclic prerequisite
   components.

### Sample Curriculum Graph (Branching Prerequisites)

Below is an illustrative curriculum DAG demonstrating branching prerequisite logic
(where one foundational concept unlocks multiple independent paths, which later
converge into a single advanced target), built using the system's exact schema.
Exercise IDs shown are illustrative placeholders, not yet drawn from the real
Junyi/ASSISTments datasets.

**Nodes (V):**

```
v1 = {Node_ID: "A", Concept_Name: "Addition", Baseline_Duration: 5, Exercises: ["ex_a1", "ex_a2"], Base_Difficulty: 0.20}
v2 = {Node_ID: "B", Concept_Name: "Subtraction", Baseline_Duration: 5, Exercises: ["ex_b1"], Base_Difficulty: 0.25}
v3 = {Node_ID: "C", Concept_Name: "Multiplication", Baseline_Duration: 10, Exercises: ["ex_c1", "ex_c2"], Base_Difficulty: 0.40}
v4 = {Node_ID: "D", Concept_Name: "Division", Baseline_Duration: 10, Exercises: ["ex_d1"], Base_Difficulty: 0.50}
```

**Edges (E) demonstrating branching:**

```
e1 = {Source_Node_ID: "A", Target_Node_ID: "B", Importance: 1.0}  (Addition required for Subtraction)
e2 = {Source_Node_ID: "A", Target_Node_ID: "C", Importance: 1.0}  (Addition also required for Multiplication - branch)
e3 = {Source_Node_ID: "B", Target_Node_ID: "D", Importance: 0.8}  (Subtraction required for Division)
e4 = {Source_Node_ID: "C", Target_Node_ID: "D", Importance: 0.9}  (Multiplication required for Division - branch converges)
```

Under the system's planning constraints, the target node D (Division) will only be
placed on the planner's frontier when both B (Subtraction) and C (Multiplication)
simultaneously satisfy the condition $p \ge 0.85$, $\sigma^2 \le 0.05$, and $n \ge 3$.
