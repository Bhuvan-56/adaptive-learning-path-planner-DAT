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

### Beta Confidence Representation

For each concept \(c\), the system maintains a Beta-distributed confidence proxy:

\[
p_{c,t}^{\mathrm{conf}}
\sim
\operatorname{Beta}(A_{c,t},B_{c,t}).
\]

Its mean is matched to the BKT mastery estimate:

\[
p_{c,t}
=
\frac{A_{c,t}}
{A_{c,t}+B_{c,t}}.
\]

The corresponding variance is

\[
\sigma_{c,t}^{2}
=
\frac{A_{c,t}B_{c,t}}
{(A_{c,t}+B_{c,t})^2(A_{c,t}+B_{c,t}+1)}.
\]

Equivalently,

\[
\sigma_{c,t}^{2}
=
\frac{p_{c,t}(1-p_{c,t})}
{\kappa_{c,t}+1},
\qquad
\kappa_{c,t}=A_{c,t}+B_{c,t}.
\]

Therefore,

\[
0\leq\sigma_{c,t}^{2}
\leq p_{c,t}(1-p_{c,t}).
\]

The Beta representation is treated as a confidence proxy unless empirical calibration establishes a stronger probabilistic interpretation.

### Mathematical Notation & Symbol Disambiguation

To prevent symbol collision across formal specifications:
- **Variance ($\sigma^2_{c,t}$):** $\sigma$ and $\sigma^2$ are strictly reserved for variance and standard deviation of belief proxies.
- **Sigmoid Function ($\operatorname{sigm}(z)$):** Logistic functions are denoted exclusively as $\operatorname{sigm}(z) = \frac{1}{1 + e^{-z}}$. The symbol $\sigma$ is never used for sigmoid functions.
- **Discrimination Slope ($a_c$):** Item Response Theory (IRT) concept-level discrimination parameters are denoted as $a_c$.
- **Duration Multiplier ($w_L$):** Objective scoring duration weight multipliers are denoted as $w_L$.

### Learner-State Constraints & Thresholds

Concepts are strictly classified into distinct states based on specific combinations of
these fields and a **Conflict-Sensitive Evidence Window Gate** ($W=4$), evaluated in the following strict precedence order:

- **Uncertain:** $\sigma^2_{c,t} > 0.05$ OR $n_{c,t} < 3$. This state strictly overrides all others for
  planning and assessment decisions, ensuring unprobed concepts ($n=0$) cannot be misclassified as Mastered or Developing.
- **Mastered:** $p_{c,t} \ge 0.85$, $\sigma^2_{c,t} \le 0.05$, $n_{c,t} \ge 3$, AND the observation window is full ($|W| \ge 4$) with at least 3 out of 4 correct outcomes ($\ge 75\%$).
- **Weak:** $p_{c,t} < 0.40$ (STRICT), $\sigma^2_{c,t} \le 0.05$, $n_{c,t} \ge 3$, AND the observation window is full ($|W| \ge 4$) with at least 3 out of 4 incorrect outcomes ($\le 25\%$ correct). (Note: $p_{c,t} = 0.40$ is Developing; $p_{c,t} < 0.40$ is Weak).
- **Developing:** All remaining field combinations that do not satisfy the above rules, including cases where mastery or weakness thresholds are met by BKT point estimates but the observation window gate fails due to contradictory evidence.

*Implementation Note:* The earlier $p_T = 0.0$ learning-rate workaround used to prevent drift during alternating sequences was a non-realistic parameter setting that has been completely removed. Default BKT parameters ($p_S=0.10, p_G=0.25, p_T=0.10$) are loaded from `config/bkt_params.yaml`, and contradictory evidence protection is handled structurally by the conflict-sensitive window gate.



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
