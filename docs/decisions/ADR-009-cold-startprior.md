# ADR-009: Cold-Start Prior and Configuration Provenance Resolution

## Context
During initial development, contradictory references existed across configurations and documentation regarding the initial learner state prior:
1. `config/bkt_params.yaml` and the engine's `ConceptState.cold_start()` implemented an uninformative prior of $A=1.0, B=1.0 \implies p=0.5, \kappa_0=2.0, n=0$.
2. The historical `evaluation/config/seeds.yaml` file declared an ad-hoc hyperparameter `prior_p_L: 0.10` alongside `transit_p_T: 0.15, slip_p_S: 0.10, guess_p_G: 0.20`, conflicting with the engine's runtime parameterization.
3. The Week 2 Evidence and Report tables evaluated unprobed initial states under $p=0.5, \kappa=2.0, \sigma^2=\frac{1}{12} \approx 0.0833 \to \text{Uncertain}$.

## Decision
1. **Canonical Engine Prior:** The runtime cold-start prior for the adaptive learning engine is strictly fixed at:
   $$\text{Beta}(\alpha=1.0, \beta=1.0) \implies p_0 = 0.5, \quad \kappa_0 = 2.0, \quad n = 0$$
   yielding heuristic belief variance:
   $$\sigma^2 = \frac{p_0(1 - p_0)}{\kappa_0 + 1} = \frac{0.25}{3} = \frac{1}{12} \approx 0.0833$$
   This guarantees that an unprobed concept starts with high variance ($\sigma^2 > 0.05$) and $n < 3$, strictly classifying as `Uncertain`.

2. **Resolution of Legacy Values:** The historical `prior_p_L: 0.10` in legacy `seeds.yaml` is recognized as a parameter intended for future synthetic student simulators (Milestone M8 evaluation generator), not the engine's cognitive mastery tracking model.

3. **Configuration Provenance:** Runtime engine parameters reside solely in `config/bkt_params.yaml` and `config/profiles.yaml`. Experiment and simulation configurations reside under `experiments/`.
