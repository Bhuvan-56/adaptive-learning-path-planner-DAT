import csv
import os
import random
import time
from typing import List, Dict, Any
import numpy as np

from src.planning.greedy import run_greedy_scheduler
from src.planning.oracle import run_exhaustive_oracle

SEEDS = [7, 17, 27, 37, 47]
INSTANCES_PER_SEED = 50  # 250 total benchmark instances


def generate_benchmark_instance(instance_id: int, rng: random.Random) -> Dict[str, Any]:
    """Generates a single valid benchmark instance with 4-12 nodes, integer durations/scores, and DAG edges."""
    num_activities = rng.randint(4, 12)
    budget = rng.choice([5, 10, 15, 30])

    items = []
    node_ids = [f"item_{i+1}" for i in range(num_activities)]

    # Generate random DAG edges
    prereq_map = {nid: [] for nid in node_ids}
    for i in range(1, num_activities):
        # 30% chance of having a prerequisite from earlier nodes
        if rng.random() < 0.35:
            num_prereqs = rng.randint(1, max(1, i))
            possible_prereqs = node_ids[:i]
            selected_prereqs = rng.sample(possible_prereqs, min(num_prereqs, len(possible_prereqs)))
            prereq_map[node_ids[i]] = selected_prereqs

    for i in range(num_activities):
        nid = node_ids[i]
        dur = rng.randint(1, 10)
        score = rng.randint(1, 20)
        items.append({
            "node_id": nid,
            "duration": dur,
            "score": score,
            "prerequisites": prereq_map[nid]
        })

    return {
        "instance_id": instance_id,
        "budget": budget,
        "items": items
    }


def run_benchmark(output_dir: str = "evaluation/results") -> Dict[str, Any]:
    """Runs the 250-instance optimality benchmark across 5 seeds and saves results CSV and summary MD."""
    os.makedirs(output_dir, exist_ok=True)
    results = []

    instance_counter = 1
    for seed in SEEDS:
        rng = random.Random(seed)
        for _ in range(INSTANCES_PER_SEED):
            inst = generate_benchmark_instance(instance_counter, rng)
            budget = inst["budget"]
            items = inst["items"]

            t0 = time.perf_counter()
            greedy_score = run_greedy_scheduler(items, budget)
            t_greedy = time.perf_counter() - t0

            t0 = time.perf_counter()
            oracle_score = run_exhaustive_oracle(items, budget)
            t_oracle = time.perf_counter() - t0

            if oracle_score == 0:
                ratio = 1.0
            else:
                ratio = greedy_score / oracle_score

            results.append({
                "seed": seed,
                "instance_id": instance_counter,
                "num_activities": len(items),
                "budget": budget,
                "greedy_score": greedy_score,
                "oracle_score": oracle_score,
                "ratio": ratio,
                "greedy_runtime_sec": t_greedy,
                "oracle_runtime_sec": t_oracle
            })
            instance_counter += 1

    # Save CSV
    csv_path = os.path.join(output_dir, "w2_greedy_vs_oracle.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # Compute Summary Statistics
    ratios = np.array([r["ratio"] for r in results])
    greedy_times = np.array([r["greedy_runtime_sec"] for r in results])
    oracle_times = np.array([r["oracle_runtime_sec"] for r in results])

    mean_ratio = float(np.mean(ratios))
    p5_ratio = float(np.percentile(ratios, 5))
    min_ratio = float(np.min(ratios))
    below_95_count = int(np.sum(ratios < 0.95))
    total_count = len(results)

    mean_greedy_time_ms = float(np.mean(greedy_times)) * 1000.0
    mean_oracle_time_ms = float(np.mean(oracle_times)) * 1000.0

    summary_md = f"""# Benchmark Summary: Greedy vs. Exact DP Oracle

- **Total Benchmark Instances:** {total_count} (5 seeds × 50 instances)
- **Mean Greedy-to-Optimal Ratio:** {mean_ratio:.4f}
- **5th Percentile Ratio:** {p5_ratio:.4f}
- **Worst-Case Ratio (Minimum):** {min_ratio:.4f}
- **Instances with Ratio < 0.95:** {below_95_count} / {total_count} ({below_95_count / total_count * 100.0:.1f}%)
- **Mean Greedy Scheduler Runtime:** {mean_greedy_time_ms:.4f} ms
- **Mean Exact DP Oracle Runtime:** {mean_oracle_time_ms:.4f} ms

## Performance Distribution Note
The greedy score-per-minute heuristic achieves strong empirical performance across random DAG instances, but does not possess a universal 95% approximation guarantee due to known indivisible block knapsack counterexamples.
"""

    summary_path = os.path.join(output_dir, "w2_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    return {
        "mean_ratio": mean_ratio,
        "p5_ratio": p5_ratio,
        "min_ratio": min_ratio,
        "below_95_count": below_95_count,
        "total_count": total_count,
        "csv_path": csv_path,
        "summary_path": summary_path
    }


if __name__ == "__main__":
    run_benchmark()
