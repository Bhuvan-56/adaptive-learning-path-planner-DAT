"""Week 8 final_v2: before/after table for the runs re-made after fixes B10, B11 and M8 calibration.

For each run, the committed Week 8 directory (before) and evaluation/results/w8/final_v2/<run>
(after) are pooled over the five seeds from per_learner_seed_<s>.csv, as in
scripts/w7_pooled_s0.py (concatenated in seed order; paired rows sorted by the per-learner seed;
compute_paired_bootstrap_ci with B = 1000, seed 42).

Per arm: mastered concepts, retained recall, no-plan days, prerequisite and budget violations,
trace coverage (primary arms only: the harness writes it to summary_seed_<s>.md for those),
and mastery Brier / ECE (after only; the before runs predate the calibration columns).
Paired: adaptive_full minus static_prerequisite_order, non_adaptive_greedy and
ablation_no_diagnostic, on mastered concepts and retained recall, before and after, with the
claim and a flag when a claim changes.

Usage:
  python scripts/w8_final_v2_compare.py            (prints the Markdown tables)
"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.evaluation.calibration import NOT_APPLICABLE, decode_pairs, expected_calibration_error  # noqa: E402
from src.evaluation.compare import compute_paired_bootstrap_ci  # noqa: E402

SEEDS = [42, 101, 2024, 777, 999]
RUNS = [  # name, before dir, after dir, horizon days
    ("toy S0", "evaluation/results/w8/final/integrated_s0", "evaluation/results/w8/final_v2/integrated_s0", 5),
    ("toy S1", "evaluation/results/w8/final/integrated_s1", "evaluation/results/w8/final_v2/integrated_s1", 5),
    ("toy S3", "evaluation/results/w8/maths_eval/toy_s3", "evaluation/results/w8/final_v2/toy_s3", 5),
    ("maths S0", "evaluation/results/w8/maths_eval/maths_s0", "evaluation/results/w8/final_v2/maths_s0", 10),
    ("maths S3", "evaluation/results/w8/maths_eval/maths_s3", "evaluation/results/w8/final_v2/maths_s3", 10),
]
ARMS_SHOWN = ["adaptive_full", "static_prerequisite_order", "non_adaptive_greedy", "ablation_no_diagnostic"]
PAIRS = [("adaptive_full", "static_prerequisite_order"), ("adaptive_full", "non_adaptive_greedy"),
         ("adaptive_full", "ablation_no_diagnostic")]


def pooled(d):
    return pd.concat([pd.read_csv(os.path.join(d, f"per_learner_seed_{s}.csv")) for s in SEEDS], ignore_index=True)


def coverage(d):
    """Trace coverage (%) per primary arm, minimum over the five per-seed summaries."""
    cov = {}
    for s in SEEDS:
        for line in open(os.path.join(d, f"summary_seed_{s}.md"), encoding="utf-8"):
            m = re.match(r"\| \*\*(\w+)\*\* \| [^|]+ \| \d+ \| \d+ \| ([\d.]+)% \|", line)
            if m:
                cov[m.group(1)] = min(cov.get(m.group(1), 100.0), float(m.group(2)))
    return cov


def paired(df, a, b, col):
    ga = df[df.arm == a].sort_values("seed", kind="mergesort").reset_index(drop=True)
    gb = df[df.arm == b].sort_values("seed", kind="mergesort").reset_index(drop=True)
    assert (ga[["seed", "learner_id"]].values == gb[["seed", "learner_id"]].values).all()
    m, lo, hi = compute_paired_bootstrap_ci((ga[col] - gb[col]).values, 1000, 0.95, 42)
    claim = f"{a} better" if lo > 0 else (f"{b} better" if hi < 0 else "no difference shown")
    return m, lo, hi, claim


def calib(g):
    if "mastery_brier" not in g.columns:
        return "not measured"
    if (g.mastery_brier.astype(str) == NOT_APPLICABLE).all():
        return "n/a"
    m, lo, hi = compute_paired_bootstrap_ci(g.mastery_brier.astype(float).values, 1000, 0.95, 42)
    pr = [x for s in g.mastery_pairs for x in decode_pairs(s)]
    ece = expected_calibration_error([q for _, q, _ in pr], [y for _, _, y in pr])
    return f"{m:.4f} [{lo:.4f}, {hi:.4f}] / {ece:.4f}"


def main():
    out = []
    for name, bdir, adir, horizon in RUNS:
        before, after = pooled(bdir), pooled(adir)
        cb, ca = coverage(bdir), coverage(adir)
        out += [f"### {name}", "", f"Before: `{bdir}`; after: `{adir}`; {len(after) // 9} learners per arm.", "",
                "| Arm | Mastered (before → after) | Retained recall | No-plan days | Prereq / budget violations (before → after) | Trace coverage % (before → after) | Mastery Brier [95% CI] / ECE (after) |",
                "|---|---|---|---|---|---|---|"]
        for arm in ARMS_SHOWN:
            gb, ga = before[before.arm == arm], after[after.arm == arm]
            days = len(ga) * horizon
            cov = f"{cb.get(arm, '–')} → {ca.get(arm, '–')}" if arm in ca else "not written for ablations"
            out.append(
                f"| {arm} | {gb.mastered_concepts.mean():.4f} → {ga.mastered_concepts.mean():.4f} | "
                f"{gb.retained_recall.mean():.4f} → {ga.retained_recall.mean():.4f} | "
                f"{int(gb.no_plan_days.sum())} → {int(ga.no_plan_days.sum())} / {days} | "
                f"{int(gb.prereq_violations.sum())}/{int(gb.budget_violations.sum())} → "
                f"{int(ga.prereq_violations.sum())}/{int(ga.budget_violations.sum())} | {cov} | {calib(ga)} |")
        tot_b = (int(before.prereq_violations.sum()), int(before.budget_violations.sum()))
        tot_a = (int(after.prereq_violations.sum()), int(after.budget_violations.sum()))
        out += ["", f"All 9 arms, prereq/budget violations: before {tot_b[0]}/{tot_b[1]}, after {tot_a[0]}/{tot_a[1]}.", "",
                "| Paired difference | Metric | Before [95% CI] | After [95% CI] | Claim before → after |",
                "|---|---|---|---|---|"]
        for a, b in PAIRS:
            for col, label in (("mastered_concepts", "mastered"), ("retained_recall", "retained recall")):
                mb, lb, hb, clb = paired(before, a, b, col)
                ma, la, ha, cla = paired(after, a, b, col)
                flag = "" if clb == cla else " **(changed)**"
                out.append(f"| {a} − {b} | {label} | {mb:+.4f} [{lb:+.4f}, {hb:+.4f}] | "
                           f"{ma:+.4f} [{la:+.4f}, {ha:+.4f}] | {clb} → {cla}{flag} |")
        out.append("")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
