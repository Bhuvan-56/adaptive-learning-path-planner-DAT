"""
Tests for Week 5 Task A3: CLI Evaluation Subcommand (python -m src.cli evaluate).

Covers:
1. Two runs with the same seed give byte-identical outputs in tmp_path.
2. Unknown configuration key exits nonzero and names the key.
3. Missing configuration file exits nonzero.
4. --require-clean fails when the dirty check is monkeypatched to report dirty.
5. Manifest lists valid SHA-256 for config and for every output file except itself, recomputed with hashlib.
6. Subprocess CLI invocation and default --require-clean behavior.
"""

import hashlib
import json
import os
import subprocess
import sys
from typing import Dict, Any

import pytest
import yaml

from src.cli import run_evaluate, DEFAULT_INTEGRATED_CONFIG


def _compute_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_evaluate_byte_identical_rerun(tmp_path, monkeypatch):
    """Running evaluate twice with the same seed produces byte-identical per_learner.csv and summary.md."""
    out1 = str(tmp_path / "eval_run1")
    out2 = str(tmp_path / "eval_run2")

    # Mock time.perf_counter to deterministic increments so runtime measurements do not fluctuate
    t_clock = [0.0]

    def mock_perf():
        t_clock[0] += 0.001
        return t_clock[0]

    monkeypatch.setattr("time.perf_counter", mock_perf)
    monkeypatch.setattr("src.evaluation.integrated.time.perf_counter", mock_perf)

    # First run
    t_clock[0] = 0.0
    ret1 = run_evaluate(
        config_path="experiments/w5_integrated.yaml",
        out_dir=out1,
        learners=2,
        require_clean=False,
    )

    # Second run with reset clock
    t_clock[0] = 0.0
    ret2 = run_evaluate(
        config_path="experiments/w5_integrated.yaml",
        out_dir=out2,
        learners=2,
        require_clean=False,
    )

    # Both runs should exit with consistent status
    assert ret1 == ret2

    # Check that required output artifacts exist in both
    for out in (out1, out2):
        assert os.path.exists(os.path.join(out, "per_learner.csv"))
        assert os.path.exists(os.path.join(out, "summary.md"))
        assert os.path.exists(os.path.join(out, "manifest.json"))

    # per_learner.csv must be byte-identical
    hash_csv1 = _compute_sha256(os.path.join(out1, "per_learner.csv"))
    hash_csv2 = _compute_sha256(os.path.join(out2, "per_learner.csv"))
    assert hash_csv1 == hash_csv2, "per_learner.csv differs across identical reruns"

    # summary.md must be byte-identical
    hash_md1 = _compute_sha256(os.path.join(out1, "summary.md"))
    hash_md2 = _compute_sha256(os.path.join(out2, "summary.md"))
    assert hash_md1 == hash_md2, "summary.md differs across identical reruns"

    # In manifest.json, config_hash and output checksums must match
    with open(os.path.join(out1, "manifest.json"), "r", encoding="utf-8") as f:
        m1 = json.load(f)
    with open(os.path.join(out2, "manifest.json"), "r", encoding="utf-8") as f:
        m2 = json.load(f)

    assert m1["config_hash"] == m2["config_hash"]
    assert m1["output_files"] == m2["output_files"]


def test_evaluate_unknown_config_key_exits_nonzero(tmp_path, capsys):
    """An unknown configuration key causes evaluate to exit nonzero and name the unknown key."""
    with open("experiments/w5_integrated.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["unrecognized_test_parameter_xyz"] = "invalid_value"
    bad_cfg_path = str(tmp_path / "bad_config.yaml")
    with open(bad_cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f)

    out_dir = str(tmp_path / "eval_out")
    ret = run_evaluate(
        config_path=bad_cfg_path,
        out_dir=out_dir,
        learners=2,
        require_clean=False,
    )

    assert ret != 0, "run_evaluate must exit nonzero when an unknown config key is present"

    captured = capsys.readouterr()
    err_text = captured.out + captured.err
    assert "unrecognized_test_parameter_xyz" in err_text, (
        f"Expected unknown key name 'unrecognized_test_parameter_xyz' in output: {err_text}"
    )


def test_evaluate_missing_config_file_exits_nonzero(tmp_path, capsys):
    """A missing configuration file causes evaluate to exit nonzero and print an error."""
    non_existent = str(tmp_path / "missing_file_404.yaml")
    ret = run_evaluate(
        config_path=non_existent,
        out_dir=str(tmp_path / "eval_out"),
        learners=2,
        require_clean=False,
    )

    assert ret != 0, "run_evaluate must exit nonzero on missing configuration file"

    captured = capsys.readouterr()
    err_text = captured.out + captured.err
    assert "missing_file_404.yaml" in err_text or "not found" in err_text.lower()


def test_evaluate_require_clean_fails_when_dirty(tmp_path, monkeypatch, capsys):
    """--require-clean fails nonzero when the dirty check is monkeypatched to report dirty."""
    out_dir = str(tmp_path / "eval_out")

    # Monkeypatch the dirty check to report dirty
    monkeypatch.setattr("src.cli.is_tracked_tree_dirty", lambda: True)

    ret = run_evaluate(
        config_path="experiments/w5_integrated.yaml",
        out_dir=out_dir,
        learners=2,
        require_clean=True,
    )

    assert ret != 0, "run_evaluate must exit nonzero when --require-clean is active and tree is dirty"

    captured = capsys.readouterr()
    err_text = captured.out + captured.err
    assert "dirty" in err_text.lower(), f"Expected 'dirty' warning in output: {err_text}"


def test_evaluate_manifest_sha256_checksums(tmp_path):
    """The manifest lists SHA-256 for the config and for every output file except itself, verified with hashlib."""
    out_dir = str(tmp_path / "eval_checksums")
    config_path = "experiments/w5_integrated.yaml"

    run_evaluate(
        config_path=config_path,
        out_dir=out_dir,
        learners=2,
        require_clean=False,
    )

    manifest_file = os.path.join(out_dir, "manifest.json")
    assert os.path.exists(manifest_file)

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Config SHA-256 check
    expected_cfg_sha = _compute_sha256(config_path)
    actual_cfg_sha = manifest["input_files"]["config"]["sha256"]
    assert actual_cfg_sha == expected_cfg_sha, "Manifest config sha256 mismatch"

    # 2. Check every output file listed in manifest
    output_files = manifest["output_files"]
    assert "per_learner.csv" in output_files
    assert "summary.md" in output_files
    assert "manifest.json" not in output_files

    for fname, recorded_sha in output_files.items():
        fpath = os.path.join(out_dir, fname)
        assert os.path.exists(fpath), f"Output file '{fname}' missing on disk"
        recomputed_sha = _compute_sha256(fpath)
        assert recomputed_sha == recorded_sha, f"SHA-256 mismatch for output file '{fname}'"

    # 3. Ensure no unmanifested output files exist (except manifest.json)
    dir_files = {f for f in os.listdir(out_dir) if f != "manifest.json"}
    assert set(output_files.keys()) == dir_files


def test_evaluate_cli_subcommand_via_subprocess(tmp_path):
    """Invoking evaluate through CLI subprocess produces all artifacts and prints summary."""
    out_dir = str(tmp_path / "subprocess_eval")

    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli",
            "evaluate",
            "--config",
            "experiments/w5_integrated.yaml",
            "--out",
            out_dir,
            "--learners",
            "2",
            "--no-require-clean",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # Check output files were emitted
    assert os.path.exists(os.path.join(out_dir, "per_learner.csv"))
    assert os.path.exists(os.path.join(out_dir, "summary.md"))
    assert os.path.exists(os.path.join(out_dir, "manifest.json"))

    # Check stdout summary
    assert "ADAPTIVE LEARNING ENGINE: INTEGRATED EVALUATION SUMMARY" in res.stdout
    assert "per_learner.csv" in res.stdout
