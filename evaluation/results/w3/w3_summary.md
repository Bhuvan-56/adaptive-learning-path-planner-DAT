# Benchmark Summary: Greedy vs. Exact DP Oracle (W3 Rerun)

- **Config Hash:** `70e78c7e7ff24d27fd25808a266ceda28c1ac04ad0e7737720cd11e5649c6505`
- **Total Benchmark Instances:** 250 (5 seeds × 50 instances)
- **Mean Greedy-to-Optimal Ratio (All):** 0.9737
- **Mean Ratio (Excluding Zero-Oracle):** 0.9730
- **5th Percentile Ratio:** 0.8270
- **Worst-Case Ratio (Minimum):** 0.2143
- **Instances with Ratio < 0.95:** 35 / 250 (14.0%)
- **Zero-Oracle Score Instances:** 6 / 250 (2.4%)
- **12/18 Counterexample:** Greedy=12, Oracle=18, Ratio=0.6667 (2/3)
- **Mean Greedy Scheduler Runtime:** 0.0914 ms
- **Mean Exact DP Oracle Runtime:** 0.2375 ms

## Performance Distribution Note
The greedy score-per-minute heuristic achieves strong empirical performance across random DAG instances, but does not possess a universal 95% approximation guarantee due to known indivisible block knapsack counterexamples.
