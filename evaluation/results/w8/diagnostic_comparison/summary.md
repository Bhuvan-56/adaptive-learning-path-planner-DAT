# Diagnostic Comparison, Pooled Paired Differences (Week 8)

All results are simulator behaviour on synthetic learners (2PL responses, latent mastery `theta* >= b_concept`). No real learner data.

- Config: `experiments/w4_comparison.yaml`; seeds [42, 101, 2024, 777, 999]; 200 learners per seed; 1000 paired learners per arm.
- Item cap 10; stopping variance 0.15.
- Bootstrap: B = 1000, 95% percentile CI, resampling seed 42; rows pooled in seed order and paired by (cohort seed, learner seed).
- Lower is better for every metric. A difference adaptive − X below zero favours adaptive.
- Claim rule: "X improves on Y" only if the paired 95% CI excludes zero; otherwise "no difference shown".
- `adaptive` is maximum-information selection run to the item cap. The concept Brier score uses p = sigmoid(θ̂) for probed concepts (0.5 for unprobed D), so the Week 8 diagnostic-prior change (n, κ, history) does not enter these metrics.

## Arms (pooled mean [95% CI])

| Arm | n | Items used | \|θ̂ − θ*\| error | Concept Brier | Held-out log loss |
|---|---|---|---|---|---|
| adaptive | 1000 | 10.00 | 0.4275 [0.4071, 0.4461] | 0.1642 [0.1596, 0.1689] | 0.5439 [0.5334, 0.5541] |
| adaptive_early_stop | 1000 | 10.00 | 0.4275 [0.4071, 0.4461] | 0.1642 [0.1596, 0.1689] | 0.5439 [0.5334, 0.5541] |
| fixed | 1000 | 10.00 | 0.4917 [0.4684, 0.5157] | 0.1672 [0.1620, 0.1726] | 0.5529 [0.5413, 0.5648] |
| random | 1000 | 10.00 | 0.5098 [0.4877, 0.5350] | 0.1699 [0.1647, 0.1755] | 0.5594 [0.5471, 0.5718] |

## Paired differences (adaptive − X)

| Comparison | Metric | Mean difference | 95% CI | Learners lower (adaptive / X / tie) | Claim |
|---|---|---|---|---|---|
| adaptive − fixed | \|θ̂ − θ*\| error | -0.0643 | [-0.0921, -0.0375] | 549 / 440 / 11 | adaptive improves on fixed [0.0375, 0.0921] |
| adaptive − fixed | concept Brier score | -0.0030 | [-0.0067, +0.0008] | 501 / 488 / 11 | no difference shown |
| adaptive − fixed | held-out log loss | -0.0090 | [-0.0158, -0.0026] | 518 / 471 / 11 | adaptive improves on fixed [0.0026, 0.0158] |
| adaptive − random | \|θ̂ − θ*\| error | -0.0823 | [-0.1103, -0.0560] | 562 / 420 / 18 | adaptive improves on random [0.0560, 0.1103] |
| adaptive − random | concept Brier score | -0.0057 | [-0.0096, -0.0017] | 518 / 464 / 18 | adaptive improves on random [0.0017, 0.0096] |
| adaptive − random | held-out log loss | -0.0155 | [-0.0237, -0.0082] | 543 / 439 / 18 | adaptive improves on random [0.0082, 0.0237] |
