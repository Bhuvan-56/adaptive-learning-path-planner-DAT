"""W8 task 4 (M8 calibration): end-of-horizon calibration of the engine's mastery
estimate p against the simulator's latent mastery, read only in the evaluation step."""
import ast
import glob
import math
import os

import pandas as pd
import pytest
import yaml

from src.evaluation import integrated

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _cal():
    from src.evaluation import calibration
    return calibration


def test_brier_hand_example():
    cal = _cal()
    # (0.9-1)^2 + (0.2-0)^2 + (0.5-1)^2 = 0.01 + 0.04 + 0.25 = 0.30 -> mean 0.10
    assert cal.brier_score([0.9, 0.2, 0.5], [1, 0, 1]) == pytest.approx(0.10)
    assert cal.brier_score([1.0, 0.0], [1, 0]) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        cal.brier_score([0.5], [1, 0])


def test_reliability_and_ece_hand_example():
    cal = _cal()
    p = [0.05, 0.15, 0.15, 0.95, 1.0]
    y = [0, 1, 0, 1, 1]
    table = cal.reliability_table(p, y, n_bins=10)
    assert len(table) == 10
    assert [b["count"] for b in table] == [1, 2, 0, 0, 0, 0, 0, 0, 0, 2]  # p = 1.0 falls in the last bin
    assert table[1]["mean_p"] == pytest.approx(0.15) and table[1]["frac_mastered"] == pytest.approx(0.5)
    assert table[2]["mean_p"] is None and table[2]["frac_mastered"] is None
    assert table[9]["mean_p"] == pytest.approx(0.975) and table[9]["frac_mastered"] == pytest.approx(1.0)
    # ECE = (1*0.05 + 2*0.35 + 2*0.025) / 5 = 0.80 / 5 = 0.16
    assert cal.expected_calibration_error(p, y, n_bins=10) == pytest.approx(0.16)
    assert cal.expected_calibration_error([0.3, 0.3], [0, 1]) == pytest.approx(0.2)  # |0.3 - 0.5|
    assert math.isnan(cal.expected_calibration_error([], []))


def test_pairs_round_trip():
    cal = _cal()
    pairs = [("A", 0.123456789012, 1), ("B", 0.5, 0)]
    s = cal.encode_pairs(pairs)
    back = cal.decode_pairs(s)
    assert [c for c, _, _ in back] == ["A", "B"]
    assert back[0][1] == pytest.approx(0.123456789012, abs=1e-12) and back[0][2] == 1
    assert cal.decode_pairs("") == [] and cal.decode_pairs(float("nan")) == []


def test_latent_state_stays_behind_the_evaluator_boundary():
    """The existing boundary tests still hold, and the new calibration code is not
    reachable from the planner, state or diagnostic packages."""
    from tests.test_simulation import test_planner_and_state_modules_contain_no_import_of_evaluator_view
    from tests.test_w5_b1_integrated import test_w5_b1_latent_state_invisibility_boundary
    test_planner_and_state_modules_contain_no_import_of_evaluator_view()
    test_w5_b1_latent_state_invisibility_boundary()
    for pkg in ("planning", "state", "diagnostic"):
        for py in glob.glob(os.path.join(ROOT, "src", pkg, "**", "*.py"), recursive=True):
            tree = ast.parse(open(py, encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    assert "calibration" not in (node.module or ""), py
                    assert all("calibration" not in a.name for a in node.names), py
    # calibration.py itself takes plain numbers; it does not import the simulator
    tree = ast.parse(open(os.path.join(ROOT, "src", "evaluation", "calibration.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [getattr(node, "module", None) or ""] + [a.name for a in node.names]
            assert not any("simulation" in n or "EvaluatorView" in n for n in names)


def test_small_run_has_calibration_columns_and_summary(tmp_path):
    cal = _cal()
    with open(os.path.join(ROOT, "experiments", "w8_final.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["seeds"] = [42]
    p = tmp_path / "w8_final.yaml"
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    res = integrated.run_integrated_evaluation(config_path=str(p), output_dir=str(tmp_path / "out"),
                                               override_learners=4, override_resamples=20)
    df = pd.read_csv(res["csv_path"])
    old_cols = list(pd.read_csv(os.path.join(
        ROOT, "evaluation/results/w8/final/integrated_s0/per_learner_seed_42.csv"), nrows=1).columns)
    assert list(df.columns) == old_cols + ["mastery_brier", "mastery_pairs"]

    na_arms = {"static_prerequisite_order", "non_adaptive_greedy",
               "non_adaptive_greedy_best_singleton", "ablation_no_replan"}
    for arm, g in df.groupby("arm"):
        if arm in na_arms:
            assert (g.mastery_brier == "not applicable").all(), arm
            assert (g.mastery_pairs == "not applicable").all(), arm
        else:
            for _, r in g.iterrows():
                pairs = cal.decode_pairs(r.mastery_pairs)
                assert [c for c, _, _ in pairs] == ["A", "B", "C", "D"]
                assert float(r.mastery_brier) == pytest.approx(
                    cal.brier_score([q for _, q, _ in pairs], [y for _, _, y in pairs]), abs=1e-9)
                # latent flags agree with the evaluator's mastered count
                assert sum(y for _, _, y in pairs) == r.mastered_concepts

    md = open(res["md_path"], encoding="utf-8").read()
    assert "Mastery calibration" in md and "ECE" in md
    for arm in na_arms:
        assert f"| {arm} | not applicable" in md
    assert md.count("| 0.9–1.0 |") >= 1  # a 10-bin reliability table
