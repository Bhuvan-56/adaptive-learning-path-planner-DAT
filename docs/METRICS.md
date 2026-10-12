# Initial Metrics

The initial metrics are explicitly defined to evaluate both the strict correctness
constraints and the adaptive performance of the planning engine, diagnostic, and
mastery models.

- **Prerequisite-Violation Count:** A strict correctness requirement, rather than a mere
  performance metric. It counts the number of times a scheduled activity violates the
  rule that a downstream target is only unlocked when all mandatory prerequisites are
  Mastered ($p \ge 0.85$, $\sigma^2 \le 0.05$, and at least 3 scored observations) and
  not classified as Uncertain.

- **Daily-Budget Violations:** Another absolute correctness requirement tracking any
  instance where the total scheduled activity duration for a given day exceeds the
  learner's specified daily time budget (B).

- **Plan Feasibility Rate:** Evaluates whether generated paths pass capacity feasibility ($W_{req} \le D \cdot B$) and scheduling feasibility (block indivisibility). The system categorizes every planning outcome into one of three distinct statuses:
  1. `FEASIBLE`: Path successfully packed into daily time budget blocks.
  2. `INFEASIBLE_PROVED`: Mathematically proved impossible (e.g. single block duration > budget or total work $W_{req} > D \cdot B$) with machine-readable minimum fixes.
  3. `HEURISTIC_NO_PLAN`: Work capacity $W_{req} \le D \cdot B$, but heuristic packer failed to place all activities within deadline $D$.

- **Explanation Coverage:** Assessed via the Trace Completeness automated test. This metric verifies that 100% of candidate activities in the candidate universe (the target node plus ALL ancestor nodes in the DAG, not merely the frontier) are successfully documented in the JSON audit trace for every planning day — either marked as `SELECTED` alongside their policy scores, or marked as `FILTERED` alongside a valid machine-readable reason code.

- **Variance Threshold Disambiguation:**
  The system uses two strictly distinct variance parameters that must not be conflated:
  1. *CAT Diagnostic Stopping Variance Threshold ($\operatorname{Var}(\theta) \le 0.15$):* In Computerized Adaptive Testing (TC-2.2), calibration terminates immediately once the posterior latent ability estimation variance $\operatorname{Var}(\theta) \le 0.15$ (or at exactly 10 questions, whichever comes first).
  2. *Mastered Heuristic Variance Ceiling ($\sigma^2 \le 0.05$):* In BKT mastery state classification (TC-1.1), a concept is classified as Mastered only when its Beta-distributed evidence confidence proxy $\sigma^2 = \frac{p(1-p)}{\kappa+1} \le 0.05$ (alongside $p \ge 0.85$, $n \ge 3$, and window quorum), guaranteeing sufficient interaction certainty before dependent material unlocks.

### TC-3.2 — Greedy-to-Optimal Planning Ratio

The greedy score-per-minute scheduler is evaluated against an exact exhaustive search oracle on a declared benchmark set of 250 instances (5 random seeds × 50 instances).

The benchmark uses the same:
- prerequisite constraints,
- indivisible activity blocks,
- eligible activity set,
- daily time budget, and
- planning objective

for both the greedy scheduler and the exact oracle.

The benchmark includes the following discrete knapsack counterexample:

- Budget: 10 minutes
- Item 1: 6 minutes, score 12
- Item 2: 5 minutes, score 9
- Item 3: 5 minutes, score 9

Greedy score-per-minute selection chooses Item 1 because

\[
12/6 = 2.0 > 9/5 = 1.8.
\]

It therefore obtains a score of 12. The exact optimum selects the two 5-minute items and obtains a score of 18:

\[
\rho = \frac{12}{18}=0.667.
\]

Therefore, the project does not claim a universal or per-instance approximation bound.

Instead, TC-3.2 is structured as a distribution-level empirical report across the declared 250-instance benchmark set, reporting:
- mean greedy-to-optimal ratio ($\bar{\rho}$),
- 5th-percentile ratio ($\rho_{0.05}$),
- worst-case minimum ratio ($\rho_{\min}$), with the 12/18 counterexample ($\rho = 0.667$) and empirical benchmark minimum ($\rho = 0.2143$) explicitly cited, and
- mean runtimes for both the greedy scheduler and exact exhaustive oracle.

The exact oracle and greedy scheduler must receive identical constraints and inputs.

> Note: when reported in the final evaluation, Plan Feasibility Rate and Simulated Final
> Mastery should be explicitly compared against the Static Prerequisite Order and
> Non-Adaptive Greedy baselines defined in `docs/LITERATURE_REVIEW.md` / the evaluation
> configuration, per the course's requirement to report predeclared metrics against
> baselines.
