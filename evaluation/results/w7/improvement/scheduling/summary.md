# Week 7 Scheduling Comparison: greedy vs greedy + best-singleton fallback

- Config hash: `70e78c7e7ff24d27fd25808a266ceda28c1ac04ad0e7737720cd11e5649c6505`
- Instances: 250 (5 seeds x 50), plus 2 fixture bad cases (not in the statistics)
- Paired bootstrap resamples: 1000 (compute_paired_bootstrap_ci, seed 42)
- Ratio = policy score / exact oracle score (1.0 when the oracle scores 0). Simulator-free synthetic instances.

| Policy | Mean ratio | 5th pct | Min | Count < 0.95 | Runtime p50 (ms) | Runtime p95 (ms) |
|---|---|---|---|---|---|---|
| greedy | 0.9737 | 0.8270 | 0.2143 | 35 / 250 | 0.0219 | 0.0657 |
| greedy_best_singleton | 0.9814 | 0.8548 | 0.5000 | 25 / 250 | 0.0266 | 0.0730 |

Paired ratio difference (greedy_best_singleton minus greedy): 0.0077 [0.0018, 0.0159]. Claim: greedy_best_singleton better (higher ratio).
Instances where the score changed: 10 / 250.

## Fixture bad cases

| Case | Budget | Items | Oracle | Greedy | Greedy ratio | Best-singleton | Best-singleton ratio |
|---|---|---|---|---|---|---|---|
| counterexample_12_18 | 10 | 3 | 18 | 12 | 0.6667 | 12 | 0.6667 |
| benchmark_seed47_instance215 | 5 | 11 | 14 | 3 | 0.2143 | 14 | 1.0000 |
