"""W8 task 3 (M2 evidence): pooled five-seed diagnostic comparison with paired
per-learner differences (adaptive - fixed, adaptive - random) and 95% bootstrap CIs
on |theta_hat - theta*|, concept Brier and held-out log loss. Lower is better."""
import json
import os

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _mod():
    from src.evaluation import diagnostic_comparison
    return diagnostic_comparison


def test_paired_difference_hand_example():
    dc = _mod()
    a = [0.5, 0.2, 0.9, 0.4]
    b = [0.7, 0.2, 0.6, 0.9]  # a - b = [-0.2, 0.0, 0.3, -0.5], mean -0.1
    m, lo, hi = dc.paired_difference(a, b, b_resamples=0)
    assert (m, lo, hi) == pytest.approx((-0.1, -0.1, -0.1))
    m, lo, hi = dc.paired_difference(a, b, b_resamples=1000, seed=42)
    assert m == pytest.approx(-0.1)
    assert -0.5 <= lo <= m <= hi <= 0.3
    # same resampling as the repo's compute_paired_bootstrap_ci on the differences
    from src.evaluation.compare import compute_paired_bootstrap_ci
    assert (m, lo, hi) == pytest.approx(compute_paired_bootstrap_ci(np.subtract(a, b), 1000, 0.95, 42))
    assert dc.paired_difference([1.0, 2.0], [1.0, 2.0], b_resamples=200) == pytest.approx((0.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        dc.paired_difference([1.0, 2.0], [1.0], b_resamples=10)


def test_claim_rule_lower_is_better():
    dc = _mod()
    # adaptive - fixed below zero: adaptive has the lower (better) error
    assert dc.claim_lower_is_better("adaptive", "fixed", -0.10, -0.15, -0.05).startswith("adaptive improves on fixed")
    assert dc.claim_lower_is_better("adaptive", "fixed", 0.10, 0.05, 0.15).startswith("fixed improves on adaptive")
    assert dc.claim_lower_is_better("adaptive", "fixed", 0.01, -0.02, 0.04) == "no difference shown"
    assert dc.claim_lower_is_better("adaptive", "fixed", 0.0, 0.0, 0.0) == "no difference shown"


def _small_cfg(tmp_path):
    with open(os.path.join(ROOT, "experiments", "w4_comparison.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["seeds"] = [42, 101]
    p = tmp_path / "w4_comparison_small.yaml"
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return str(p)


def test_small_run_writes_outputs_with_all_six_comparisons(tmp_path):
    dc = _mod()
    out = tmp_path / "out"
    res = dc.run_pooled_diagnostic_comparison(config_path=_small_cfg(tmp_path), output_dir=str(out),
                                              override_learners=6, override_resamples=50)
    df = pd.read_csv(out / "per_learner.csv")
    arms = ["adaptive", "adaptive_early_stop", "fixed", "random"]
    assert sorted(df.arm.unique()) == sorted(arms)
    assert len(df) == 2 * 6 * len(arms)
    for c in ("cohort_seed", "learner_seed", "learner_id", "abs_theta_error", "brier", "log_loss"):
        assert c in df.columns
    # pairing: every arm sees the same learners in the same order
    keys = {a: df[df.arm == a][["cohort_seed", "learner_seed"]].values.tolist() for a in arms}
    assert all(keys[a] == keys["adaptive"] for a in arms)

    md = (out / "summary.md").read_text(encoding="utf-8")
    comps = res["comparisons"]
    assert len(comps) == 6
    for other in ("fixed", "random"):
        for metric in ("abs_theta_error", "brier", "log_loss"):
            row = [c for c in comps if c["arm_b"] == other and c["metric"] == metric]
            assert len(row) == 1
            r = row[0]
            assert r["arm_a"] == "adaptive" and r["n_pairs"] == 12
            d = (df[df.arm == "adaptive"][metric].values - df[df.arm == other][metric].values).mean()
            assert r["mean"] == pytest.approx(d)
            assert r["claim"] == dc.claim_lower_is_better("adaptive", other, r["mean"], r["ci_low"], r["ci_high"])
            assert f"| adaptive − {other} | {dc.METRIC_LABELS[metric]} |" in md
            assert r["claim"] in md
    assert md.count("| adaptive − ") == 6

    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["seeds"] == [42, 101]
    assert set(man["output_files"]) == {"per_learner.csv", "summary.md"}
    assert "config" in man["input_files"] and "git" in man
