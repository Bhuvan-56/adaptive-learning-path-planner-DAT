import glob
import json
import os
import random
import pytest
import yaml

from src.provenance import (
    resolved_config_hash,
    write_manifest,
    get_git_info,
    get_package_versions
)
from src.planning.benchmark import (
    load_benchmark_config,
    generate_benchmark_instance
)


def test_defect_10_no_conflicting_bkt_keys_across_configs():
    """Defect 10: Scanning config/ and evaluation/config/ must not find conflicting BKT parameters."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_dirs = [
        os.path.join(repo_root, "config"),
        os.path.join(repo_root, "evaluation", "config"),
    ]

    bkt_params_found = {}

    def extract_bkt(data, filepath):
        if not isinstance(data, dict):
            return
        slip = data.get("p_S")
        guess = data.get("p_G")
        transit = data.get("p_T")

        if isinstance(data.get("bkt"), dict):
            slip = slip or data["bkt"].get("slip_p_S")
            guess = guess or data["bkt"].get("guess_p_G")
            transit = transit or data["bkt"].get("transit_p_T")

        if isinstance(data.get("model_hyperparameters"), dict):
            m = data["model_hyperparameters"]
            if isinstance(m.get("bkt"), dict):
                slip = slip or m["bkt"].get("slip_p_S")
                guess = guess or m["bkt"].get("guess_p_G")
                transit = transit or m["bkt"].get("transit_p_T")

        extracted = {}
        if slip is not None:
            extracted["slip"] = slip
        if guess is not None:
            extracted["guess"] = guess
        if transit is not None:
            extracted["transit"] = transit

        if extracted:
            bkt_params_found[filepath] = extracted

    for cdir in config_dirs:
        if os.path.exists(cdir):
            for ypath in glob.glob(os.path.join(cdir, "*.yaml")) + glob.glob(os.path.join(cdir, "*.yml")):
                with open(ypath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    extract_bkt(data, ypath)

    conflicts = []
    files = list(bkt_params_found.keys())
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            f1, f2 = files[i], files[j]
            p1, p2 = bkt_params_found[f1], bkt_params_found[f2]
            for k in set(p1.keys()).intersection(set(p2.keys())):
                if p1[k] != p2[k]:
                    conflicts.append(
                        f"Conflict on {k}: {os.path.basename(f1)} ({p1[k]}) vs {os.path.basename(f2)} ({p2[k]})"
                    )

    assert len(conflicts) == 0, f"Found BKT config conflicts: {conflicts}"


def test_same_experiment_run_twice_gives_same_hash_and_identical_outputs():
    """Verifies that hashing the same experiment configuration twice produces identical hash and outputs."""
    config1 = load_benchmark_config()
    config2 = load_benchmark_config()

    hash1 = resolved_config_hash(config1)
    hash2 = resolved_config_hash(config2)
    assert hash1 == hash2

    rng1 = random.Random(config1["seeds"][0])
    rng2 = random.Random(config2["seeds"][0])
    inst1 = generate_benchmark_instance(1, rng1, config1.get("generator_params"))
    inst2 = generate_benchmark_instance(1, rng2, config2.get("generator_params"))
    assert inst1 == inst2


def test_changing_one_parameter_changes_hash():
    """Verifies that mutating a single config parameter produces a distinct SHA-256 hash."""
    config = load_benchmark_config()
    orig_hash = resolved_config_hash(config)

    # Mutate one parameter
    mutated = dict(config)
    gen_params = dict(config.get("generator_params", {}))
    gen_params["prereq_probability"] = 0.99
    mutated["generator_params"] = gen_params

    new_hash = resolved_config_hash(mutated)
    assert orig_hash != new_hash


def test_manifest_contains_every_listed_field(tmp_path):
    """Verifies that write_manifest produces all required fields including git_sha and dirty flag."""
    manifest_path = tmp_path / "test_manifest.json"
    manifest = write_manifest(
        path=str(manifest_path),
        experiment_name="test_experiment",
        config_hash="abc123hash",
        seeds=[1, 2, 3],
        git_sha="test_git_sha",
        python_version="3.11.4",
        package_versions={"numpy": "1.24.3"},
        timestamp="2026-10-12T00:00:00Z",
        data_route="synthetic_test",
        dataset_provenance={"dataset": "none"},
        dirty=False
    )

    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    required_fields = [
        "experiment_name",
        "config_hash",
        "seeds",
        "git_sha",
        "dirty",
        "python_version",
        "package_versions",
        "timestamp",
        "data_route",
    ]
    for field_name in required_fields:
        assert field_name in loaded
        assert loaded[field_name] == manifest[field_name]
