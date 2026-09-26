# Architecture Decision Record: ADR-001

## Decision ID & Date
ADR-001 | 2026-09-25

## Title
Bayesian Knowledge Tracing (BKT) vs. Deep Knowledge Tracing (DKT) for Mastery Estimation

## Status
Reaffirmed (Decided at proposal time)

## Old / Current Approach
N/A — First decision.

## Evidence
- Empirical studies (Badrinath et al., 2021; Piech et al., 2015) show Deep Knowledge Tracing (DKT) achieves high predictive accuracy ($AUC$) on large learner response benchmarks.
- However, DKT encodes knowledge state into hidden recurrent neural network vectors ($h_t \in \mathbb{R}^d$), rendering latent mastery uninterpretable and preventing direct extraction of concept-level posterior variance $\sigma^2_{c,t}$.
- BKT provides closed-form Bayesian probability updates ($p_{c,t}$) and explicit Beta belief representations $\text{Beta}(A_{c,t}, B_{c,t})$ with quantifiable uncertainty $\sigma^2_{c,t}$.

## Alternatives Considered
1. **Deep Knowledge Tracing (DKT):** High predictive capability, but uninterpretable black-box hidden state space. Cannot natively emit explicit uncertainty thresholds ($\sigma^2 \le 0.05$) or justify prerequisite readiness in structured audit traces.
2. **Performance Factor Analysis (PFA):** Logistic regression over success/failure counts per skill. Useful baseline, but lacks dynamic posterior updates and explicit belief variance tracking.
3. **Bayesian Knowledge Tracing (BKT) via pyBKT:** Classical 4-parameter Hidden Markov Model per concept ($p_L, p_T, p_S, p_G$). Fully interpretable, fast CPU fitting, and direct integration with prerequisite DAG gating.

## Selected Approach + Rationale
**Selected Approach:** Adopt Bayesian Knowledge Tracing (BKT) leveraging `pyBKT` as the core online mastery estimation model.

**Rationale:**
The engine requires explicit, mathematically transparent triggers for planning decisions (e.g., classifying state into Uncertain, Mastered, Weak, or Developing). BKT provides exact posterior probabilities $p_{c,t}$ and matches posterior mean to a Beta distribution to track belief variance $\sigma^2_{c,t}$. This native transparency is mandatory to satisfy the system's machine-readable JSON explainability requirement (M7) and zero-prerequisite-violation constraint (M1).

## Impact on Milestones
- **M1 (Curriculum Graph & Learner State Models):** Establishes explicit state fields $S_{c,t} = (p_{c,t}, \sigma^2_{c,t}, d_{c,t}, R_{c,t})$ and state classification rules.
- **M7 (Explainability Framework):** Provides probabilistic mastery and uncertainty values included in every daily JSON audit trace.

## Revised Plan / Risks
None yet. standard 4-parameter BKT will be fitted via student-level splits on Junyi Academy and ASSISTments logs. Performance will be benchmarked against DKT baseline models during the mandatory 09 October decision review.
