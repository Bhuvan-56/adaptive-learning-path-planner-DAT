"""Week 8 public-data extension: toy S0 (final_v2) against toy S4 (ASSISTments-calibrated learners).

Both runs use the same config apart from the scenario (experiments/w8_final.yaml vs
experiments/w8_s4_assistments.yaml): 5 seeds x 200 learners, 5 days, 10-minute budget, target D.
Pooling, pairing and bootstrap are as in scripts/w8_final_v2_compare.py (B = 1000, seed 42).

S0 and S4 learners differ (S4 draws per learner-concept slip/guess/learn from real-student fits),
so absolute levels are not paired across the two columns; only within-run differences are.
Runtimes are not compared (different machine load).

Usage:
  python scripts/w8_s4_compare.py      (prints the Markdown tables)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from w8_final_v2_compare import calib, coverage, paired, pooled  # noqa: E402

S0 = "evaluation/results/w8/final_v2/integrated_s0"
S4 = "evaluation/results/w8/final_v2/integrated_s4"
HORIZON = 5
ARMS = ["adaptive_full", "static_prerequisite_order", "non_adaptive_greedy",
        "non_adaptive_greedy_best_singleton", "ablation_no_diagnostic", "ablation_no_review"]
PAIRS = [("adaptive_full", "static_prerequisite_order"), ("adaptive_full", "non_adaptive_greedy"),
         ("non_adaptive_greedy_best_singleton", "non_adaptive_greedy"),
         ("adaptive_full", "ablation_no_diagnostic"), ("adaptive_full", "ablation_no_review")]


def main():
    s0, s4 = pooled(S0), pooled(S4)
    c0, c4 = coverage(S0), coverage(S4)
    out = [f"S0: `{S0}`; S4: `{S4}`; {len(s4) // 9} learners per arm in each.", "",
           "| Arm | Mastered S0 → S4 | Retained recall S0 → S4 | No-plan days S0 → S4 | Prereq / budget violations S0 → S4 | Trace coverage % S0 → S4 | Mastery Brier [95% CI] / ECE, S0 → S4 |",
           "|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        g0, g4 = s0[s0.arm == arm], s4[s4.arm == arm]
        days = len(g4) * HORIZON
        cov = f"{c0.get(arm, '–')} → {c4.get(arm, '–')}" if arm in c4 else "not written for ablations"
        out.append(
            f"| {arm} | {g0.mastered_concepts.mean():.4f} → {g4.mastered_concepts.mean():.4f} | "
            f"{g0.retained_recall.mean():.4f} → {g4.retained_recall.mean():.4f} | "
            f"{int(g0.no_plan_days.sum())} → {int(g4.no_plan_days.sum())} / {days} | "
            f"{int(g0.prereq_violations.sum())}/{int(g0.budget_violations.sum())} → "
            f"{int(g4.prereq_violations.sum())}/{int(g4.budget_violations.sum())} | {cov} | "
            f"{calib(g0)} → {calib(g4)} |")
    t0 = (int(s0.prereq_violations.sum()), int(s0.budget_violations.sum()))
    t4 = (int(s4.prereq_violations.sum()), int(s4.budget_violations.sum()))
    out += ["", f"All 9 arms, prereq/budget violations: S0 {t0[0]}/{t0[1]}, S4 {t4[0]}/{t4[1]}.", "",
            "| Paired difference (within run) | Metric | S0 [95% CI] | S4 [95% CI] | Claim S0 → S4 |",
            "|---|---|---|---|---|"]
    for a, b in PAIRS:
        for col, label in (("mastered_concepts", "mastered"), ("retained_recall", "retained recall")):
            m0, l0, h0, cl0 = paired(s0, a, b, col)
            m4, l4, h4, cl4 = paired(s4, a, b, col)
            flag = "" if cl0 == cl4 else " **(changed)**"
            out.append(f"| {a} − {b} | {label} | {m0:+.4f} [{l0:+.4f}, {h0:+.4f}] | "
                       f"{m4:+.4f} [{l4:+.4f}, {h4:+.4f}] | {cl0} → {cl4}{flag} |")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
