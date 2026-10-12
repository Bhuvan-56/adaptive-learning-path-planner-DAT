import csv
import datetime
import os
import platform
import random
import time
from typing import List, Dict, Any, Optional
import numpy as np
import yaml

from src.planning.greedy import run_greedy_scheduler
from src.planning.oracle import run_exhaustive_oracle
from src.provenance import (
    resolved_config_hash,
    write_manifest,
    get_git_info,
    get_package_versions
)

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "experiments", "w2_scheduling_benchmark.yaml"
)


def load_benchmark_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads benchmark configuration from experiments/w2_scheduling_benchmark.yaml."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Benchmark experiment config not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Benchmark config must be a YAML mapping, got {type(data)}")

    return data


def generate_benchmark_instance(
    instance_id: int,
    rng: random.Random,
    gen_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generates a single valid benchmark instance using configured generator parameters."""
    params = gen_params or {}
    min_act = params.get("min_activities", 4)
    max_act = params.get("max_activities", 12)
    budgets = params.get("budgets", [5, 10, 15, 30])
    prereq_prob = params.get("prereq_probability", 0.35)
    min_dur = params.get("min_duration", 1)
    max_dur = params.get("max_duration", 10)
    min_sc = params.get("min_score", 1)
    max_sc = params.get("max_score", 20)

    num_activities = rng.randint(min_act, max_act)
    budget = rng.choice(budgets)

    node_ids = [f"item_{i+1}" for i in range(num_activities)]
    prereq_map = {nid: [] for nid in node_ids}
    for i in range(1, num_activities):
        if rng.random() < prereq_prob:
            num_prereqs = rng.randint(1, max(1, i))
            possible_prereqs = node_ids[:i]
            selected_prereqs = rng.sample(possible_prereqs, min(num_prereqs, len(possible_prereqs)))
            prereq_map[node_ids[i]] = selected_prereqs

    items = []
    for i in range(num_activities):
        nid = node_ids[i]
        dur = rng.randint(min_dur, max_dur)
        score = rng.randint(min_sc, max_sc)
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


def run_benchmark(
    output_dir: str = "evaluation/results/w3",
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs the optimality benchmark across configured seeds and writes outputs:
    - CSV and Summary MD with config hash embedded
    - manifest.json and config_hash.txt in output_dir
    """
    os.makedirs(output_dir, exist_ok=True)
    config = load_benchmark_config(config_path)

    seeds = config.get("seeds", [7, 17, 27, 37, 47])
    instances_per_seed = config.get("instances_per_seed", 50)
    gen_params = config.get("generator_params", {})
    experiment_name = config.get("experiment_name", "w2_scheduling_benchmark")

    cfg_hash = resolved_config_hash(config)

    results = []
    instance_counter = 1
    for seed in seeds:
        rng = random.Random(seed)
        for _ in range(instances_per_seed):
            inst = generate_benchmark_instance(instance_counter, rng, gen_params)
            budget = inst["budget"]
            items = inst["items"]

            t0 = time.perf_counter()
            greedy_score = run_greedy_scheduler(items, budget)
            t_greedy = time.perf_counter() - t0

            t0 = time.perf_counter()
            oracle_score = run_exhaustive_oracle(items, budget)
            t_oracle = time.perf_counter() - t0

            ratio = 1.0 if oracle_score == 0 else (greedy_score / oracle_score)

            results.append({
                "config_hash": cfg_hash,
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

    # Save CSV with config hash
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

- **Config Hash:** `{cfg_hash}`
- **Total Benchmark Instances:** {total_count} ({len(seeds)} seeds × {instances_per_seed} instances)
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

    # Save config hash text file
    hash_path = os.path.join(output_dir, "config_hash.txt")
    with open(hash_path, "w", encoding="utf-8") as f:
        f.write(cfg_hash + "\n")

    # Save manifest.json
    git_sha, dirty = get_git_info()
    manifest_path = os.path.join(output_dir, "manifest.json")
    manifest = write_manifest(
        path=manifest_path,
        experiment_name=experiment_name,
        config_hash=cfg_hash,
        seeds=seeds,
        git_sha=git_sha,
        python_version=platform.python_version(),
        package_versions=get_package_versions(),
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        data_route="synthetic_dag_generator",
        dataset_provenance=None,
        dirty=dirty
    )

    return {
        "config_hash": cfg_hash,
        "mean_ratio": mean_ratio,
        "p5_ratio": p5_ratio,
        "min_ratio": min_ratio,
        "below_95_count": below_95_count,
        "total_count": total_count,
        "csv_path": csv_path,
        "summary_path": summary_path,
        "hash_path": hash_path,
        "manifest_path": manifest_path,
        "manifest": manifest
    }


if __name__ == "__main__":
    run_benchmark()
