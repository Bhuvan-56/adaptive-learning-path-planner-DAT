# Architecture Decision Record: ADR-009

## Decision ID & Date
ADR-009 | 2026-10-10

## Title
Cold-Start Prior and CAT Ability-to-Mastery Mapping for Learner Initialization

## Status
Accepted

## Old / Current Approach
Initial learner profiles were manually parameterized with ad-hoc initial states in `config/profiles.yaml` and heuristic cold-start values in `ConceptState.cold_start()` ($A=1.0, B=1.0, \kappa=2.0$). The connection between adaptive diagnostic ability estimates $\hat{\theta}$ and concept-level BKT initial mastery $p_{c,0}$ was designed in ADR-002 but lacked an explicit mathematical mapping function, formal prior definition, and rules for unprobed concepts.

## Evidence
- Computerized Adaptive Testing (CAT / IRT) produces a standardized latent ability scale $\hat{\theta} \in (-\infty, \infty)$ centered at $0$.
- Bayesian Knowledge Tracing requires prior mastery probabilities $p_{c,0} \in (0, 1)$.
- Unprobed concepts must not be artificially promoted to `Mastered`, `Developing`, or `Weak` without direct assessment evidence, as premature classification causes prerequisite gating violations or inappropriate remediation.

## Alternatives Considered
1. **Uniform Initialization across all concepts ($p_{c,0} = \text{const}$):** Fails to leverage diagnostic test results and treats experienced learners identically to novices.
2. **Linear Mapping $\hat{\theta} \mapsto p_{c,0}$:** Unbounded $\hat{\theta}$ requires arbitrary heuristic truncation and distorts probability densities at extreme ability levels.
3. **Logistic Transformation with Uninformative Prior:** Maps $\hat{\theta}$ to $(0, 1)$ via the canonical logistic link function $p_{c,0} = \frac{1}{1 + e^{-\hat{\theta}}}$, clamped to $[0.01, 0.99]$. Concepts without direct diagnostic assessment retain an uninformative $\operatorname{Beta}(1, 1)$ prior with $n=0$ interactions, strictly classifying as `Uncertain`.

## Selected Approach + Rationale
**Selected Approach:** Adopt the logistic ability-to-mastery mapping with an uninformative $\operatorname{Beta}(1, 1)$ prior for unprobed concepts and a strict $p < 0.40$ boundary for Weak classification.

1. **Unprobed Cold-Start Prior:**
   Unprobed concepts are initialized with $\operatorname{Beta}(A=1.0, B=1.0)$, yielding pseudo-count $\kappa = A + B = 2.0$, mean mastery $p = 0.5$, heuristic variance $\sigma^2 = \frac{p(1-p)}{\kappa+1} = \frac{0.25}{3} \approx 0.0833$, and interaction count $n = 0$.
   Because $\sigma^2 > 0.05$ and $n < 3$, every unprobed concept strictly classifies as `Uncertain` (top precedence).

2. **CAT Ability-to-Mastery Mapping:**
   When a learner completes the bounded CAT diagnostic (terminating when $\operatorname{Var}(\theta) \le 0.15$ or 10 questions are answered), the resulting ability estimate $\hat{\theta}$ initializes probed concepts via:
   \[
   p_{c,0} = \frac{1}{1 + e^{-\hat{\theta}}}
   \]
   clamped to $[0.01, 0.99]$. Concentration is set to $\kappa = 2.0$ ($A = 2 p_{c,0}, B = 2(1 - p_{c,0})$).

3. **No Invented Observations:**
   Concepts without direct diagnostic items keep observation count $n = 0$, $\kappa = 2.0$, and stay `Uncertain`. No pseudo-observations or synthetic counts are added.

4. **Weak Boundary Settled:**
   The classification boundary for `Weak` mastery is settled strictly at $p < 0.40$ (with $\sigma^2 \le 0.05$, $n \ge 3$, and $\ge 3/4$ incorrect answers in the sliding window).

## Impact on Milestones
- **M1 (Curriculum Graph & Learner State Models):** Formalizes initial state parameters for `ConceptState` and preserves strict precedence classification.
- **M2 (Adaptive Diagnostic Policy):** Defines the mathematical contract between CAT stopping outputs and downstream BKT concept initialization.
- **M7 (Explainability Framework):** Explains why diagnostic and unprobed nodes route to initial assessment rather than prerequisite bypass.

## Week 8 Amendment (2026-11-13): diagnostic answers count as evidence

**Problem (LIMITATIONS B10).** Rule 2 gave every probed concept $n = 0$, and rule 1 makes $n < 3$ `Uncertain`. So the CAT result set $p$ but never the class the planner reads, and `ablation_no_diagnostic` equalled `adaptive_full` on every curriculum.

**Change.** A concept with $k$ administered items that load on it (Q-matrix) is initialised by `ConceptState.init_from_diagnostic`:
- $p_{c,0}$ is the same logistic mapping of $\hat{\theta}$ as above, clamped to $[0.01, 0.99]$.
- $n = k$ and $\kappa = 2 + k$: the cold-start pseudo-count plus one per observation, the same increment `ConceptState.update` applies. $\sigma^2 = p(1-p)/(\kappa+1)$ is unchanged, and $k \ge 3$ gives $\kappa \ge 5$, so $\sigma^2 \le 0.05$ (ADR-005).
- `history` holds the concept's last $W$ answers, so the conflict gate (ADR-007) applies to diagnostic evidence as it does to practice.
- A concept with $k = 0$, and every concept without items, stays exactly as in rules 1 and 3 ($n = 0$, `Uncertain`). Rule 3 ("no invented observations") still holds: only answered items are counted.

**Scope.**
- The baseline arms (`static_prerequisite_order`, `non_adaptive_greedy`, `non_adaptive_greedy_best_singleton`) keep the pre-amendment states (`DiagnosticResult.prior_only_states`), so their behaviour is unchanged.
- The harness's independent prerequisite recount accepts a prerequisite that was evidence-`Mastered` in the arm's initial states, the same rule the planner and the greedy baseline use.
- The diagnostic record (`diagnostic_record.json`, `initial_priors`) now shows `n` and `items_answered` per concept.

**Observed consequence.** Because one $\hat{\theta}$ sets $p$ for all probed concepts, `Mastered` needs $\hat{\theta} \ge 1.73$, and an all-correct 10-item diagnostic on the synthetic bank stops at $\hat{\theta} \approx 1.13$. In practice the diagnostic mostly yields `Developing` or `Weak`. On 20 learners (seed 42, `experiments/w8_final.yaml`), 19 adaptive_full rows changed and mean mastered went from 2.30 to 2.25, so there is no gain on that sample (`evaluation/results/w8_evidence/after_fix3_diagnostic_prior.txt`). Tests: `tests/test_w8_diagnostic_prior.py`.
