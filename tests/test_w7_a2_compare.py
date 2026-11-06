"""W7 A2: scheduling policy comparison on a tiny config written to tmp_path."""
import csv
import json

import yaml

from src.planning.benchmark import load_benchmark_config, run_benchmark
from src.planning.compare_policies import run_policy_comparison


def _tiny_config(tmp_path):
    cfg = load_benchmark_config()
    cfg["seeds"] = [7, 47]
    cfg["instances_per_seed"] = 6
    path = tmp_path / "tiny.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return str(path)


def test_greedy_column_matches_run_benchmark_and_new_never_lower(tmp_path):
    cfg_path = _tiny_config(tmp_path)
    bench = run_benchmark(output_dir=str(tmp_path / "bench"), config_path=cfg_path)
    comp = run_policy_comparison(output_dir=str(tmp_path / "comp"), config_path=cfg_path, n_boot=200)

    with open(bench["csv_path"], newline="", encoding="utf-8") as f:
        bench_rows = list(csv.DictReader(f))
    with open(comp["csv_path"], newline="", encoding="utf-8") as f:
        comp_rows = [r for r in csv.DictReader(f) if r["is_fixture"] == "False"]

    assert len(comp_rows) == len(bench_rows) == 12
    assert comp["config_hash"] == bench["config_hash"]
    for b, c in zip(bench_rows, comp_rows):
        assert (b["seed"], b["instance_id"], b["budget"]) == (c["seed"], c["instance_id"], c["budget"])
        assert b["greedy_score"] == c["greedy_score"]
        assert b["oracle_score"] == c["oracle_score"]
        assert b["ratio"] == c["greedy_ratio"]

    for r in comp["rows"] + comp["fixture_rows"]:
        assert r["greedy_best_singleton_ratio"] >= r["greedy_ratio"]

    fixtures = {r["case_id"]: r for r in comp["fixture_rows"]}
    assert set(fixtures) == {"counterexample_12_18", "benchmark_seed47_instance215"}
    assert fixtures["counterexample_12_18"]["greedy_best_singleton_score"] == 12

    manifest = json.loads((tmp_path / "comp" / "manifest.json").read_text(encoding="utf-8"))
    for key in ("config_hash", "git_sha", "dirty"):
        assert key in manifest
    assert (tmp_path / "comp" / "summary.md").exists()
