# ADR-005: Uncertainty Representation as Heuristic Evidence-Count Proxy

## Status

Accepted

## Context

Standard Bayesian Knowledge Tracing (BKT) continuously updates a scalar point estimate of mastery probability $p_{c,t}$, but does not directly output a posterior variance or parameter uncertainty metric. The path planning engine requires an explicit uncertainty metric to gate prerequisite advancement and trigger diagnostic assessments.

## Decision

The system maintains a Beta-distributed belief proxy $\operatorname{Beta}(A_{c,t}, B_{c,t})$ matched to the current BKT mastery estimate $p_{c,t} = \frac{A_{c,t}}{A_{c,t} + B_{c,t}}$.

The associated variance is defined as:

\[
\sigma_{c,t}^2 = \frac{p_{c,t}(1 - p_{c,t})}{\kappa_{c,t} + 1}, \qquad \kappa_{c,t} = A_{c,t} + B_{c,t}.
\]

This representation is explicitly treated as a **heuristic evidence-count confidence proxy**, not a calibrated posterior distribution.

Because $\kappa \ge 4$ mathematically guarantees $\sigma^2 \le 0.05$ for all values of $p$, the observation count constraint ($n \ge 3$) serves as the primary evidence gate for state classification.

## Consequences

- Resolves cold-start and unprobed high-ability edge cases by forcing unprobed concepts ($n=0$) to classify as `Uncertain`.
- Ensures mathematical bounds $0 \le \sigma^2 \le p(1-p)$ hold across all updates.
- Prevents misinterpreting heuristic evidence growth as empirical posterior calibration.
