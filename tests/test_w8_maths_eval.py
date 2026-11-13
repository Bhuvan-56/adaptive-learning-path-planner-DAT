"""W8 addendum 2 (docs/w8/preregistration_maths.md): the integrated harness on
the maths curriculum and under the mismatched PFA simulator (S3)."""
import math
import os

import pandas as pd
import pytest
import yaml

from src.evaluation import integrated

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _cfg(name, tmp_path, **override):
    with open(os.path.join(ROOT, "experiments", name), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["seeds"] = [42]
    cfg.update(override)
    p = tmp_path / name
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")  # keep arm order
    return str(p)


def test_maths_s0_run_uses_the_maths_curriculum(tmp_path):
    res = integrated.run_integrated_evaluation(config_path=_cfg("w8_maths_s0.yaml", tmp_path),
                                               output_dir=str(tmp_path / "out"), override_learners=3,
                                               override_resamples=20)
    df = pd.read_csv(res["csv_path"])
    assert len(df) == 3 * 9
    assert df.mastered_concepts.max() > 4  # 16-concept curriculum
    for r in res["arm_results"].values():
        assert r.total_prereq_violations == 0 and r.total_budget_violations == 0
        assert r.trace_coverage == 100.0


def test_s3_generator_uses_per_learner_intercepts():
    diffs = {"A": -0.2, "B": 0.5}
    gen, _ = integrated.make_learner_generator("S3", theta=0.3, concept_difficulties=diffs)
    assert gen.name == "MismatchedPFAOrLogisticGenerator"
    logit = math.log(0.75 / 0.25)
    assert gen.concept_intercepts["A"] == pytest.approx(0.3 + 0.2 + logit)
    assert gen.concept_intercepts["B"] == pytest.approx(0.3 - 0.5 + logit)
    # initial PFA mastery (no practice) equals the S0 truth rule theta >= b
    for c, b in diffs.items():
        p_ref = 1 / (1 + math.exp(-gen.concept_intercepts[c]))
        assert (p_ref >= gen.mastered_p) == (0.3 >= b)
    assert (gen.gamma, gen.rho, gen.difficulty_weight, gen.p_F) == (0.40, 0.10, 1.0, 0.0)


def test_toy_s3_run_completes_with_hard_constraints(tmp_path):
    res = integrated.run_integrated_evaluation(config_path=_cfg("w8_toy_s3.yaml", tmp_path),
                                               output_dir=str(tmp_path / "out"), override_learners=4,
                                               override_resamples=20)
    for r in res["arm_results"].values():
        assert r.total_prereq_violations == 0 and r.total_budget_violations == 0
        assert r.trace_coverage == 100.0


def test_toy_s0_unchanged_against_committed_run(tmp_path):
    """Guard: the first 8 learners of seed 42 equal the committed W8 S0 run.

    W8 fix 3 (diagnostic evidence, LIMITATIONS B10) changes the arms that use the
    diagnostic's states by design, so the guard covers the arms that must stay
    identical: the three baselines (pre-fix n = 0 priors) and ablation_no_diagnostic
    (cold start). W8 task 4 appends calibration columns; the committed run's columns
    are compared."""
    res = integrated.run_integrated_evaluation(config_path=_cfg("w8_final.yaml", tmp_path),
                                               output_dir=str(tmp_path / "out"), override_learners=8,
                                               override_resamples=20)
    unchanged = ["static_prerequisite_order", "non_adaptive_greedy",
                 "non_adaptive_greedy_best_singleton", "ablation_no_diagnostic"]
    new = pd.read_csv(res["csv_path"]).drop(columns="runtime_ms")
    old = pd.read_csv(os.path.join(ROOT, "evaluation/results/w8/final/integrated_s0/per_learner_seed_42.csv"))
    old = old[old.learner_id.isin(new.learner_id.unique())].drop(columns="runtime_ms")
    assert list(new.columns[:len(old.columns)]) == list(old.columns)  # existing order kept
    new = new[list(old.columns)]
    new = new[new.arm.isin(unchanged)].reset_index(drop=True)
    old = old[old.arm.isin(unchanged)].reset_index(drop=True)
    assert len(new) == 8 * len(unchanged)
    pd.testing.assert_frame_equal(new, old, check_dtype=False)
