# ADR-007: Conflict-Sensitive Evidence Window Gate for Learner State Classification

## Status

Accepted

## Context

Standard Bayesian Knowledge Tracing (BKT) updates mastery probability $p_{c,t}$ on each observation. During audit testing under realistic default BKT parameters ($p_S=0.10, p_G=0.25, p_T=0.10$), an alternating sequence of correct/incorrect observations caused belief variance $\sigma^2$ to drop below $0.05$ at observation $n=4$, while $p$ dropped below $0.40$, incorrectly triggering a `Weak` state classification despite mixed, contradictory evidence.

An earlier workaround set default learning rate $p_T = 0.0$ to prevent state transitions during alternating sequences. However, this workaround was rejected because setting learning to zero disables BKT mastery progression under realistic student practice and hides state model drift.

## Decision

The system retains realistic default BKT parameters ($p_S=0.10, p_G=0.25, p_T=0.10$) loaded from `config/bkt_params.yaml` and introduces a **Conflict-Sensitive Evidence Window Gate** to `ConceptState`:

1. Maintain a bounded window of the last $W=4$ observation outcomes ($W$ configured in `config/bkt_params.yaml`).
2. Classification into `Mastered` requires: $\sigma^2 \le 0.05$, $n \ge 3$, $p \ge 0.85$, AND the window is full ($|W| \ge 4$) with at least $3/4$ correct outcomes.
3. Classification into `Weak` requires: $\sigma^2 \le 0.05$, $n \ge 3$, strict $p < 0.40$, AND the window is full ($|W| \ge 4$) with at least $3/4$ incorrect outcomes ($\le 1/4$ correct).
4. If $p$ meets the `Mastered` or `Weak` threshold but the window gate fails due to conflicting evidence, the concept classifies as `Developing`.
5. `Uncertain` ($\sigma^2 > 0.05$ or $n < 3$) maintains top precedence.

## Limitations

- The evidence window gate is an uncalibrated heuristic guard designed to prevent premature classification under contradictory evidence.
- The window size ($W=4$) is a heuristic constant and has not yet been fitted against empirical student logs.
