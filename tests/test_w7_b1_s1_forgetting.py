"""W7 B1: under S1 the integrated daily learning loop should apply daily forgetting.

The spy counts SimulatedLearner.advance_day calls made directly from
src/evaluation/integrated.py. Calls made by the retention quiz
(src/evaluation/retention.py) are not counted.
"""
import inspect
import os

import pytest
import yaml

from src.evaluation import integrated
from src.simulation.simulator import SimulatedLearner

W5_FINAL = os.path.join(os.path.dirname(__file__), "..", "experiments", "w5_final.yaml")


def test_s1_daily_loop_calls_advance_day(tmp_path, monkeypatch):
    with open(W5_FINAL, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["scenario"] = "S1"
    cfg["seeds"] = [42]
    cfg_path = tmp_path / "w7_s1.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    assert integrated.resolve_scenario_name(cfg) == "S1"

    integrated_file = os.path.normcase(os.path.abspath(integrated.__file__))
    calls = {"daily_loop": 0, "other": 0}
    original = SimulatedLearner.advance_day

    def spy(self, *args, **kwargs):
        caller = inspect.stack()[1].filename
        if os.path.normcase(os.path.abspath(caller)) == integrated_file:
            calls["daily_loop"] += 1
        else:
            calls["other"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SimulatedLearner, "advance_day", spy)

    integrated.run_integrated_evaluation(
        config_path=str(cfg_path),
        output_dir=str(tmp_path / "out"),
        override_learners=5,
    )

    # The retention quiz does run under S1, so the spy is wired correctly.
    assert calls["other"] > 0
    assert calls["daily_loop"] > 0, f"advance_day calls from integrated.py: {calls}"
