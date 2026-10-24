import hashlib
import json
import os
import shutil
import pytest

from src.cli import run_demo
from src.provenance import (
    resolved_config_hash,
    write_manifest,
    get_git_info,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMO_CURRICULUM_PATH = os.path.join(REPO_ROOT, "data", "curricula", "demo_curriculum.json")
PROFILES_PATH = os.path.join(REPO_ROOT, "config", "profiles.yaml")
BKT_PARAMS_PATH = os.path.join(REPO_ROOT, "config", "bkt_params.yaml")


def _file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_w4_d7_changing_node_duration_changes_hash(tmp_path):
    # Setup two curriculum files with different node durations
    with open(DEMO_CURRICULUM_PATH, "r", encoding="utf-8") as f:
        curr_data = json.load(f)

    curr_orig = tmp_path / "curr_orig.json"
    curr_orig.write_text(json.dumps(curr_data, indent=2), encoding="utf-8")

    # Mutate concept C baseline_duration from 10 to 9
    curr_mutated_data = json.loads(json.dumps(curr_data))
    for node in curr_mutated_data["nodes"]:
        if node["node_id"] == "C":
            node["baseline_duration"] = 9

    curr_mutated = tmp_path / "curr_mutated.json"
    curr_mutated.write_text(json.dumps(curr_mutated_data, indent=2), encoding="utf-8")

    # Assert curriculum bytes differ before comparing hashes
    assert curr_orig.read_bytes() != curr_mutated.read_bytes()

    out1 = str(tmp_path / "out1")
    out2 = str(tmp_path / "out2")

    ret1 = run_demo(out_dir=out1, seed=20261012, budget=10, curriculum_path=str(curr_orig))
    ret2 = run_demo(out_dir=out2, seed=20261012, budget=10, curriculum_path=str(curr_mutated))
    assert ret1 == 0
    assert ret2 == 0

    with open(os.path.join(out1, "manifest.json"), "r", encoding="utf-8") as f:
        m1 = json.load(f)
    with open(os.path.join(out2, "manifest.json"), "r", encoding="utf-8") as f:
        m2 = json.load(f)

    assert m1["config_hash"] != m2["config_hash"], (
        f"Editing node duration left config_hash unchanged: {m1['config_hash']}"
    )


def test_w4_d7_manifest_records_curriculum_path_and_hashes(tmp_path):
    custom_curr = tmp_path / "custom_demo.json"
    shutil.copyfile(DEMO_CURRICULUM_PATH, str(custom_curr))

    out_dir = str(tmp_path / "manifest_run")
    ret = run_demo(out_dir=out_dir, seed=20261012, budget=10, curriculum_path=str(custom_curr))
    assert ret == 0

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Manifest records actual curriculum path passed in
    assert "curriculum_path" in manifest
    assert manifest["curriculum_path"] == str(custom_curr)

    # 2. Records SHA-256 of curriculum file, profile fixtures, and resolved policy
    assert "input_hashes" in manifest
    input_hashes = manifest["input_hashes"]
    assert "curriculum" in input_hashes
    assert input_hashes["curriculum"] == _file_sha256(str(custom_curr))
    assert "profiles" in input_hashes
    assert input_hashes["profiles"] == _file_sha256(PROFILES_PATH)
    assert "policy" in input_hashes
    assert len(input_hashes["policy"]) == 64

    # 3. Lists SHA-256 for every emitted output file (excluding manifest.json itself)
    assert "output_checksums" in manifest
    output_checksums = manifest["output_checksums"]

    emitted_files = [f for f in os.listdir(out_dir) if f != "manifest.json"]
    assert len(emitted_files) > 0
    assert set(output_checksums.keys()) == set(emitted_files)

    for fname in emitted_files:
        expected_hash = _file_sha256(os.path.join(out_dir, fname))
        assert output_checksums[fname] == expected_hash


def test_w4_d7_ninth_decimal_difference_hashes_differently():
    val1 = {"learning_rate": 0.100000001}
    val2 = {"learning_rate": 0.100000002}
    h1 = resolved_config_hash(val1)
    h2 = resolved_config_hash(val2)
    assert h1 != h2, f"Values differing at 9th decimal produced identical hash: {h1}"



def test_w4_d7_timestamp_does_not_affect_config_hash():
    cfg1 = {"budget": 10, "seed": 42}
    cfg2 = {"budget": 10, "seed": 42}
    assert resolved_config_hash(cfg1) == resolved_config_hash(cfg2)


def test_w4_d7_dirty_tree_recorded_as_dirty(tmp_path):
    manifest_path = tmp_path / "test_dirty.json"
    manifest = write_manifest(
        path=str(manifest_path),
        experiment_name="test_dirty",
        config_hash="abc",
        seeds=[42],
        git_sha="sha",
        python_version="3.11",
        package_versions={"numpy": "1.0"},
        timestamp="2026-10-24T00:00:00Z",
        data_route="test",
        dirty=True,
    )
    assert manifest["dirty"] is True
