"""Week 7 deadlock fix: compare the fixed run with the W7 improvement run.

Same method as scripts/w7_pooled_s0.py: the five per_learner_seed_<s>.csv files
concatenated in seed order 42, 101, 2024, 777, 999; compute_paired_bootstrap_ci
with B = 1000, seed 42; paired rows sorted by the per-learner seed column.

Prints
  1. identity check for arms the fix must not change (all columns but runtime_ms)
  2. per-arm pooled figures for the fixed run
  3. paired mastered differences: each replan arm fixed minus before, and
     adaptive_full (fixed) minus static_prerequisite_order / non_adaptive_greedy

Usage:
  python scripts/w7_deadlock_fix_compare.py <before_dir> <after_dir>
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.evaluation.compare import compute_paired_bootstrap_ci  # noqa: E402

SEEDS = [42, 101, 2024, 777, 999]
UNCHANGED = ["static_prerequisite_order", "non_adaptive_greedy",
             "non_adaptive_greedy_best_singleton", "ablation_no_replan"]
REPLAN_ARMS = ["adaptive_full", "ablation_no_diagnostic", "ablation_no_difficulty_step",
               "ablation_no_review", "ablation_no_remediation"]


def load(d):
    return pd.concat([pd.read_csv(os.path.join(d, f"per_learner_seed_{s}.csv")) for s in SEEDS],
                     ignore_index=True)


def arm_rows(df, arm):
    return df[df.arm == arm].sort_values("seed", kind="mergesort").reset_index(drop=True)


def paired(ga, gb, label):
    assert len(ga) == len(gb)
    assert (ga[["seed", "learner_id"]].values == gb[["seed", "learner_id"]].values).all()
    d = (ga.mastered_concepts - gb.mastered_concepts).values
    m, lo, hi = compute_paired_bootstrap_ci(d, 1000, 0.95, 42)
    claim = "better" if lo > 0 else ("worse" if hi < 0 else "no difference shown")
    print(f"{label}: {m:+.4f} [{lo:.4f}, {hi:.4f}] changed {(d != 0).sum()} "
          f"(+{(d > 0).sum()} / -{(d < 0).sum()}) -> {claim}")


def main(before_dir, after_dir):
    before, after = load(before_dir), load(after_dir)
    print(f"rows before {len(before)} after {len(after)}")

    print("\n1. identity of unchanged arms (all columns except runtime_ms)")
    cols = [c for c in before.columns if c != "runtime_ms"]
    for arm in UNCHANGED:
        a, b = arm_rows(after, arm)[cols], arm_rows(before, arm)[cols]
        same = a.equals(b)
        print(f"  {arm}: {'identical' if same else 'DIFFERS'}")
        assert same, arm

    print("\n2. fixed run, pooled per arm")
    for arm, g in after.groupby("arm", sort=False):
        m, lo, hi = compute_paired_bootstrap_ci(g.mastered_concepts.values, 1000, 0.95, 42)
        print(f"  {arm}: n={len(g)} mastered {m:.4f} [{lo:.4f}, {hi:.4f}] "
              f"no_plan {g.no_plan_days.sum()}/{len(g) * 5} prereq {g.prereq_violations.sum()} "
              f"budget {g.budget_violations.sum()} runtime_p50 {g.runtime_ms.median():.4f} "
              f"runtime_p95 {g.runtime_ms.quantile(0.95):.4f}")
        b = before[before.arm == arm]
        print(f"  {'':{len(arm)}}  before: no_plan {b.no_plan_days.sum()}/{len(b) * 5}")

    print("\n3. paired mastered differences")
    for arm in REPLAN_ARMS:
        paired(arm_rows(after, arm), arm_rows(before, arm), f"  {arm} fixed - before")
    for other in ("static_prerequisite_order", "non_adaptive_greedy"):
        paired(arm_rows(after, "adaptive_full"), arm_rows(after, other), f"  adaptive_full (fixed) - {other}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
