"""B14 fix: before/after for every integrated run (W8, 2026-11-20).

Before = evaluation/results/w8/final_v2/<run> (pre-fix); after = evaluation/results/w8/final_v3/<run>
(same configs and seeds, after commit 03fd8ce). For each run prints, per arm, mastered concepts and
retained recall before and after, and paired 95% bootstrap CIs (B = 1000, seed 42) for
  after - before (adaptive_full), adaptive_full - static_prerequisite_order,
  adaptive_full - ablation_no_review.

  python scripts/w8_b14_compare.py > evaluation/results/w8/final_v3/b14_before_after.txt
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.evaluation.compare import compute_paired_bootstrap_ci  # noqa: E402

SEEDS = (42, 101, 2024, 777, 999)
RUNS = ["integrated_s0", "integrated_s1", "toy_s3", "maths_s0", "maths_s3", "integrated_s4"]
BEFORE = os.path.join(ROOT, "evaluation/results/w8/final_v2")
AFTER = os.path.join(ROOT, "evaluation/results/w8/final_v3")


def pooled(d):
    return pd.concat([pd.read_csv(os.path.join(d, f"per_learner_seed_{s}.csv")) for s in SEEDS], ignore_index=True)


def paired(a, b, col):
    a = a.sort_values(["seed", "learner_id"], kind="mergesort").reset_index(drop=True)
    b = b.sort_values(["seed", "learner_id"], kind="mergesort").reset_index(drop=True)
    assert (a[["seed", "learner_id"]].values == b[["seed", "learner_id"]].values).all()
    m, lo, hi = compute_paired_bootstrap_ci((a[col] - b[col]).values, 1000, 0.95, 42)
    return f"{m:+.4f} [{lo:+.4f}, {hi:+.4f}]"


def main():
    for run in RUNS:
        bd, ad = os.path.join(BEFORE, run), os.path.join(AFTER, run)
        if not os.path.isdir(ad):
            print(f"## {run}: no after run in {ad}\n")
            continue
        b, a = pooled(bd), pooled(ad)
        assert len(a) == len(b), run
        print(f"## {run}  (before {os.path.relpath(bd, ROOT)}, after {os.path.relpath(ad, ROOT)})")
        print("arm | mastered before | mastered after | retained before | retained after | prereq/budget violations after")
        for arm in a.arm.unique():
            ga, gb = a[a.arm == arm], b[b.arm == arm]
            print(f"{arm} | {gb.mastered_concepts.mean():.4f} | {ga.mastered_concepts.mean():.4f} | "
                  f"{gb.retained_recall.mean():.4f} | {ga.retained_recall.mean():.4f} | "
                  f"{int(ga.prereq_violations.sum())}/{int(ga.budget_violations.sum())}")
        A = lambda df, arm: df[df.arm == arm]  # noqa: E731
        for col in ("mastered_concepts", "retained_recall"):
            print(f"{col}: adaptive_full after - before        {paired(A(a, 'adaptive_full'), A(b, 'adaptive_full'), col)}")
            for other in ("static_prerequisite_order", "ablation_no_review"):
                print(f"{col}: adaptive_full - {other:<26} before {paired(A(b, 'adaptive_full'), A(b, other), col)}"
                      f"  after {paired(A(a, 'adaptive_full'), A(a, other), col)}")
        print()


if __name__ == "__main__":
    main()
