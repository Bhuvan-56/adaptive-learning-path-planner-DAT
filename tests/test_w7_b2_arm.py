"""W7 B2: the opt-in non_adaptive_greedy_best_singleton arm leaves every existing arm unchanged."""
import os

import pandas as pd
import yaml

from src.evaluation import integrated

ROOT = os.path.join(os.path.dirname(__file__), "..")
W5_FINAL = os.path.join(ROOT, "experiments", "w5_final.yaml")
W7_IMPROVEMENT = os.path.join(ROOT, "experiments", "w7_improvement.yaml")
NEW_ARM = "non_adaptive_greedy_best_singleton"


def _one_seed_config(src_path, tmp_path, name):
    with open(src_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["seeds"] = [42]
    path = tmp_path / name
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return str(path)


def test_w7_config_only_adds_the_new_arm():
    with open(W5_FINAL, "r", encoding="utf-8") as f:
        base = yaml.safe_load(f)
    with open(W7_IMPROVEMENT, "r", encoding="utf-8") as f:
        new = yaml.safe_load(f)
    assert new["arms"]["primary"] == base["arms"]["primary"] + [NEW_ARM]
    new["arms"]["primary"] = base["arms"]["primary"]
    assert new == base


def test_existing_arms_identical_under_both_configs(tmp_path):
    base_cfg = _one_seed_config(W5_FINAL, tmp_path, "base.yaml")
    new_cfg = _one_seed_config(W7_IMPROVEMENT, tmp_path, "new.yaml")
    base = integrated.run_integrated_evaluation(base_cfg, str(tmp_path / "base"), override_learners=5)
    new = integrated.run_integrated_evaluation(new_cfg, str(tmp_path / "new"), override_learners=5)

    df_base = pd.read_csv(base["csv_path"])
    df_new = pd.read_csv(new["csv_path"])
    assert NEW_ARM not in set(df_base["arm"])
    assert (df_new["arm"] == NEW_ARM).sum() == 5

    cols = [c for c in df_base.columns if c != "runtime_ms"]
    kept = df_new[df_new["arm"] != NEW_ARM].reset_index(drop=True)
    pd.testing.assert_frame_equal(df_base[cols], kept[cols])

    new_rows = df_new[df_new["arm"] == NEW_ARM]
    assert new_rows["prereq_violations"].sum() == 0
    assert new_rows["budget_violations"].sum() == 0

    summary = open(new["md_path"], encoding="utf-8").read()
    assert f"{NEW_ARM} - non_adaptive_greedy" in summary
    assert f"{NEW_ARM} - non_adaptive_greedy" not in open(base["md_path"], encoding="utf-8").read()
