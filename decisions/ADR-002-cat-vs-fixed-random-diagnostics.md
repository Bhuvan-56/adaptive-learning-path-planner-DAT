# Architecture Decision Record: ADR-002

## Decision ID & Date
ADR-002 | 2026-09-25

## Title
Computerized Adaptive Testing (CAT) vs. Fixed-Order / Random-Item Diagnostics for Cold-Start Assessment

## Status
Reaffirmed (Decided at proposal time)

## Old / Current Approach
N/A — First decision.

## Evidence
- Item Response Theory (IRT) and Computerized Adaptive Testing (CAT) literature (Eggen, 2018; van der Linden, 2005) demonstrates that selecting items via Maximum Fisher Information maximizes per-question measurement efficiency.
- Adaptive item selection reduces question count by up to 50% while achieving identical or lower measurement error $\text{Var}(\theta)$ compared to static linear tests.

## Alternatives Considered
1. **Fixed-Order Diagnostic:** Evaluates questions in a predetermined topological order. Simple to administer, but inflexible and inefficient when testing learners with non-uniform prior knowledge.
2. **Random-Item Diagnostic:** Selects items uniformly at random from the item bank. Provides poor ability estimation calibration and high variance per item.
3. **CAT with 2-Parameter Logistic (2PL) IRT Model:** Dynamically selects the item maximizing Fisher Information $I_i(\hat{\theta})$ after each response, terminating when $\text{Var}(\theta) \le 0.15$ or 10 items are answered.

## Selected Approach + Rationale
**Selected Approach:** Implement Computerized Adaptive Testing (CAT) driven by a 2PL IRT item bank with Maximum Fisher Information item selection.

**Rationale:**
CAT rapidly cold-starts learner profiles without requiring lengthy placement tests. By enforcing strict termination criteria ($\text{Var}(\theta) \le 0.15$ or max 10 questions), the system minimizes diagnostic friction for the learner. The resulting latent ability parameter $\hat{\theta}$ is cleanly mapped to concept-level initial BKT mastery ($p_{c,0}$), satisfying acceptance criteria TC-2.1 and TC-2.2.

## Impact on Milestones
- **M2 (Adaptive Diagnostic Policy):** Governs the design of the diagnostic module (`/diagnostic`), IRT item selection algorithm, stopping rule, and baseline diagnostic comparators.

## Revised Plan / Risks
None yet. IRT parameters $(\alpha_i, \beta_i)$ will be calibrated on the Junyi Academy training split. Fixed-order and random diagnostics will be implemented as baseline controls for evaluation. Re-assessment scheduled for 09 October.
