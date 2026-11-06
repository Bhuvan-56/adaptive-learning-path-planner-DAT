"""Week 7: pooled five-seed S0 figures from per_learner_seed_<s>.csv files.

per_learner.csv and the "Arm" table in summary.md hold seed 42 only, so the
five-seed figures are computed here from the five per-seed CSVs, concatenated
in seed order, with compute_paired_bootstrap_ci (B = 1000, seed 42).
Paired differences use rows sorted by the per-learner seed column.

Usage:
  python scripts/w7_pooled_s0.py <results_dir> [arm_a:arm_b ...]
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.evaluation.compare import compute_paired_bootstrap_ci  # noqa: E402

SEEDS = [42, 101, 2024, 777, 999]


def main(results_dir, pairs):
    df = pd.concat(
        [pd.read_csv(os.path.join(results_dir, f"per_learner_seed_{s}.csv")) for s in SEEDS],
        ignore_index=True,
    )
    print(f"rows {len(df)}")
    for arm, g in df.groupby("arm", sort=False):
        m, lo, hi = compute_paired_bootstrap_ci(g.mastered_concepts.values, 1000, 0.95, 42)
        print(
            f"{arm}: n={len(g)} mastered {m:.4f} [{lo:.4f}, {hi:.4f}] "
            f"no_plan {g.no_plan_days.sum()}/{len(g) * 5} prereq {g.prereq_violations.sum()} "
            f"budget {g.budget_violations.sum()} runtime_p50 {g.runtime_ms.median():.4f} "
            f"runtime_p95 {g.runtime_ms.quantile(0.95):.4f}"
        )
    for pair in pairs:
        a, b = pair.split(":")
        # Rows sorted by the per-learner seed (unique), as in BASELINE.md; the
        # bootstrap resamples by position, so this order fixes the reported CI.
        ga = df[df.arm == a].sort_values("seed", kind="mergesort").reset_index(drop=True)
        gb = df[df.arm == b].sort_values("seed", kind="mergesort").reset_index(drop=True)
        if len(ga) == 0 or len(gb) == 0:
            print(f"{a} - {b}: arm missing in {results_dir}")
            continue
        assert len(ga) == len(gb)
        assert (ga[["seed", "learner_id"]].values == gb[["seed", "learner_id"]].values).all()
        d = (ga.mastered_concepts - gb.mastered_concepts).values
        m, lo, hi = compute_paired_bootstrap_ci(d, 1000, 0.95, 42)
        print(
            f"{a} - {b}: {m:.4f} [{lo:.4f}, {hi:.4f}] "
            f"changed {(d != 0).sum()} (+{(d > 0).sum()} / -{(d < 0).sum()})"
        )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
