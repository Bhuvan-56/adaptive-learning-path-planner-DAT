# Benchmark Summary: Greedy vs. Exact DP Oracle

- **Config Hash:** `70e78c7e7ff24d27fd25808a266ceda28c1ac04ad0e7737720cd11e5649c6505`
- **Total Benchmark Instances:** 250 (5 seeds × 50 instances)
- **Mean Greedy-to-Optimal Ratio:** 0.9737
- **5th Percentile Ratio:** 0.8270
- **Worst-Case Ratio (Minimum):** 0.2143
- **Instances with Ratio < 0.95:** 35 / 250 (14.0%)
- **Mean Greedy Scheduler Runtime:** 0.0223 ms
- **Mean Exact DP Oracle Runtime:** 0.0548 ms

## Performance Distribution Note
The greedy score-per-minute heuristic achieves strong empirical performance across random DAG instances, but does not possess a universal 95% approximation guarantee due to known indivisible block knapsack counterexamples.
