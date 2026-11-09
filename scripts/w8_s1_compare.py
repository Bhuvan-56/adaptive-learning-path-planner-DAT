"""Week 8: S1 before vs after the daily-forgetting fix, same learners.

Same method as scripts/w7_pooled_s0.py: per_learner_seed_<s>.csv for seeds
42, 101, 2024, 777, 999 concatenated; compute_paired_bootstrap_ci with
B = 1000, seed 42; paired rows sorted by the per-learner seed column.

Prints, for every arm, the paired after-minus-before difference of
mastered_concepts and of retained_recall.

Usage:
  python scripts/w8_s1_compare.py <before_dir> <after_dir>
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.evaluation.compare import compute_paired_bootstrap_ci  # noqa: E402

SEEDS = [42, 101, 2024, 777, 999]


def _load(d):
    return pd.concat([pd.read_csv(os.path.join(d, f"per_learner_seed_{s}.csv")) for s in SEEDS],
                     ignore_index=True)


def main(before_dir, after_dir):
    before, after = _load(before_dir), _load(after_dir)
    print(f"rows before {len(before)} after {len(after)}")
    for arm in after.arm.drop_duplicates():
        b = before[before.arm == arm].sort_values("seed", kind="mergesort").reset_index(drop=True)
        a = after[after.arm == arm].sort_values("seed", kind="mergesort").reset_index(drop=True)
        assert list(a.seed) == list(b.seed), arm
        out = [arm]
        for col in ("mastered_concepts", "retained_recall"):
            diff = (a[col] - b[col]).values
            m, lo, hi = compute_paired_bootstrap_ci(diff, 1000, 0.95, 42)
            out.append(f"{col} {b[col].mean():.4f} -> {a[col].mean():.4f} diff {m:.4f} [{lo:.4f}, {hi:.4f}]")
        print(" | ".join(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
