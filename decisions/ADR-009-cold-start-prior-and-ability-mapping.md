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
