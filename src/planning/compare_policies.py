"""Week 7 scheduling comparison: greedy vs greedy + best-singleton fallback.

Same 250 instances as src/planning/benchmark.py (its own generator and config),
exact oracle once per instance, and the two saved bad cases flagged as fixtures.
Specified in docs/w7/preregistration.md.
"""
import csv
import datetime
import json
import os
import platform
import random
import time
from typing import Any, Dict, List, Optional

import numpy as np

from src.evaluation.compare import compute_paired_bootstrap_ci
from src.planning.benchmark import generate_benchmark_instance, load_benchmark_config
from src.planning.greedy import run_greedy_scheduler
from src.planning.greedy_fallback import run_greedy_best_singleton
from src.planning.oracle import run_exhaustive_oracle
from src.provenance import get_git_info, get_package_versions, resolved_config_hash, write_manifest

DEFAULT_BAD_CASES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "tests", "fixtures", "w7", "bad_cases.json"
)

POLICIES = ("greedy", "greedy_best_singleton")


def _ratio(score: float, oracle: float) -> float:
    return 1.0 if oracle == 0 else (score / oracle)


def _evaluate(items: List[Dict[str, Any]], budget: int) -> Dict[str, Any]:
    t0 = time.perf_counter()
    greedy_score = run_greedy_scheduler(items, budget)
    t_greedy = time.perf_counter() - t0

    t0 = time.perf_counter()
    new_score = run_greedy_best_singleton(items, budget)
    t_new = time.perf_counter() - t0

    oracle_score = run_exhaustive_oracle(items, budget)
    return {
        "num_activities": len(items),
        "budget": budget,
        "oracle_score": oracle_score,
        "greedy_score": greedy_score,
        "greedy_ratio": _ratio(greedy_score, oracle_score),
        "greedy_ms": t_greedy * 1000.0,
        "greedy_best_singleton_score": new_score,
        "greedy_best_singleton_ratio": _ratio(new_score, oracle_score),
        "greedy_best_singleton_ms": t_new * 1000.0,
    }


def _policy_stats(rows: List[Dict[str, Any]], policy: str) -> Dict[str, float]:
    ratios = np.array([r[f"{policy}_ratio"] for r in rows], dtype=float)
    ms = np.array([r[f"{policy}_ms"] for r in rows], dtype=float)
    return {
        "mean_ratio": float(np.mean(ratios)),
        "p5_ratio": float(np.percentile(ratios, 5)),
        "min_ratio": float(np.min(ratios)),
        "below_95_count": int(np.sum(ratios < 0.95)),
        "runtime_p50_ms": float(np.percentile(ms, 50)),
        "runtime_p95_ms": float(np.percentile(ms, 95)),
    }


def run_policy_comparison(
    output_dir: str,
    config_path: Optional[str] = None,
    n_boot: int = 1000,
    bad_cases_path: Optional[str] = None,
) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    config = load_benchmark_config(config_path)
    seeds = config.get("seeds", [7, 17, 27, 37, 47])
    instances_per_seed = config.get("instances_per_seed", 50)
    gen_params = config.get("generator_params", {})
    cfg_hash = resolved_config_hash(config)

    rows: List[Dict[str, Any]] = []
    instance_counter = 1
    for seed in seeds:
        rng = random.Random(seed)
        for _ in range(instances_per_seed):
            inst = generate_benchmark_instance(instance_counter, rng, gen_params)
            row = {"case_id": f"seed{seed}_instance{instance_counter}", "is_fixture": False,
                   "seed": seed, "instance_id": instance_counter}
            row.update(_evaluate(inst["items"], inst["budget"]))
            rows.append(row)
            instance_counter += 1

    with open(bad_cases_path or DEFAULT_BAD_CASES_PATH, "r", encoding="utf-8") as f:
        bad_cases = json.load(f)["cases"]
    fixture_rows: List[Dict[str, Any]] = []
    for case in bad_cases:
        row = {"case_id": case["id"], "is_fixture": True, "seed": "", "instance_id": ""}
        row.update(_evaluate(case["items"], case["budget"]))
        fixture_rows.append(row)

    csv_path = os.path.join(output_dir, "per_instance.csv")
    fieldnames = ["config_hash"] + list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows + fixture_rows:
            writer.writerow({"config_hash": cfg_hash, **r})

    stats = {p: _policy_stats(rows, p) for p in POLICIES}
    diffs = [r["greedy_best_singleton_ratio"] - r["greedy_ratio"] for r in rows]
    d_mean, d_low, d_high = compute_paired_bootstrap_ci(diffs, b_resamples=n_boot, seed=42)
    if d_low > 0.0:
        claim = "greedy_best_singleton better (higher ratio)"
    elif d_high < 0.0:
        claim = "greedy_best_singleton worse (lower ratio): loss"
    else:
        claim = "no difference shown"
    changed = [r for r in rows if r["greedy_best_singleton_score"] != r["greedy_score"]]

    lines = [
        "# Week 7 Scheduling Comparison: greedy vs greedy + best-singleton fallback",
        "",
        f"- Config hash: `{cfg_hash}`",
        f"- Instances: {len(rows)} ({len(seeds)} seeds x {instances_per_seed}), plus {len(fixture_rows)} fixture bad cases (not in the statistics)",
        f"- Paired bootstrap resamples: {n_boot} (compute_paired_bootstrap_ci, seed 42)",
        "- Ratio = policy score / exact oracle score (1.0 when the oracle scores 0). Simulator-free synthetic instances.",
        "",
        "| Policy | Mean ratio | 5th pct | Min | Count < 0.95 | Runtime p50 (ms) | Runtime p95 (ms) |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in POLICIES:
        s = stats[p]
        lines.append(
            f"| {p} | {s['mean_ratio']:.4f} | {s['p5_ratio']:.4f} | {s['min_ratio']:.4f} | "
            f"{s['below_95_count']} / {len(rows)} | {s['runtime_p50_ms']:.4f} | {s['runtime_p95_ms']:.4f} |"
        )
    lines += [
        "",
        f"Paired ratio difference (greedy_best_singleton minus greedy): {d_mean:.4f} [{d_low:.4f}, {d_high:.4f}]. Claim: {claim}.",
        f"Instances where the score changed: {len(changed)} / {len(rows)}.",
        "",
        "## Fixture bad cases",
        "",
        "| Case | Budget | Items | Oracle | Greedy | Greedy ratio | Best-singleton | Best-singleton ratio |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in fixture_rows:
        lines.append(
            f"| {r['case_id']} | {r['budget']} | {r['num_activities']} | {r['oracle_score']} | {r['greedy_score']} | "
            f"{r['greedy_ratio']:.4f} | {r['greedy_best_singleton_score']:g} | {r['greedy_best_singleton_ratio']:.4f} |"
        )
    lines.append("")
    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    git_sha, dirty = get_git_info()
    manifest = write_manifest(
        path=os.path.join(output_dir, "manifest.json"),
        experiment_name="w7_scheduling_policy_comparison",
        config_hash=cfg_hash,
        seeds=seeds,
        git_sha=git_sha,
        python_version=platform.python_version(),
        package_versions=get_package_versions(),
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        data_route="synthetic_dag_generator",
        dirty=dirty,
    )

    return {
        "config_hash": cfg_hash,
        "rows": rows,
        "fixture_rows": fixture_rows,
        "stats": stats,
        "paired_diff": (d_mean, d_low, d_high),
        "claim": claim,
        "changed_count": len(changed),
        "csv_path": csv_path,
        "summary_path": summary_path,
        "manifest": manifest,
    }


if __name__ == "__main__":
    import sys
    run_policy_comparison(sys.argv[1] if len(sys.argv) > 1 else "evaluation/results/w7/improvement/scheduling")
