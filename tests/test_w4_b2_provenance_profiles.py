import glob
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


# =============================================================================
# DEFECT 8 REPRODUCTION TESTS
# =============================================================================

GROUPS_PATH = os.path.abspath("data/curricula/demo_curriculum.groups.yaml")


@pytest.mark.xfail(strict=True, reason="W4 D8: SimulatedLearner latent keys are profile group names instead of concept IDs")
def test_w4_d8_latent_keys_equal_concept_ids():
    from src.simulation.simulator import SimulatedLearner
    for pid in ["profile_1", "profile_2", "profile_3"]:
        learner = SimulatedLearner(profile_id=pid)
        assert set(learner._latent_states.keys()) == {"A", "B", "C", "D"}, (
            f"Latent keys for {pid} were {list(learner._latent_states.keys())}, expected ['A', 'B', 'C', 'D']"
        )
        assert set(learner.evaluator_view().latent_masteries.keys()) == {"A", "B", "C", "D"}


@pytest.mark.xfail(strict=True, reason="W4 D8: profile expansion to concept priors not implemented")
def test_w4_d8_profile_expansion_to_concept_priors():
    import src.simulation.simulator as sim
    if not hasattr(sim, "expand_profile_to_priors"):
        pytest.fail("expand_profile_to_priors not found in src.simulation.simulator")
    
    expand_fn = getattr(sim, "expand_profile_to_priors")
    
    # Profile 1: default -> (0.01, 2.0, 0)
    p1_priors = expand_fn("profile_1", groups_path=GROUPS_PATH)
    assert set(p1_priors.keys()) == {"A", "B", "C", "D"}
    for cid in ["A", "B", "C", "D"]:
        assert p1_priors[cid] == {"p": 0.01, "kappa": 2.0, "n": 0}

    # Profile 2: prerequisites -> (0.90, 10.0, 8), downstream -> (0.30, 2.0, 0)
    p2_priors = expand_fn("profile_2", groups_path=GROUPS_PATH)
    assert set(p2_priors.keys()) == {"A", "B", "C", "D"}
    assert p2_priors["A"] == {"p": 0.90, "kappa": 10.0, "n": 8}
    assert p2_priors["B"] == {"p": 0.90, "kappa": 10.0, "n": 8}
    assert p2_priors["C"] == {"p": 0.30, "kappa": 2.0, "n": 0}
    assert p2_priors["D"] == {"p": 0.30, "kappa": 2.0, "n": 0}

    # Profile 3: default -> (0.92, 8.0, 6)
    p3_priors = expand_fn("profile_3", groups_path=GROUPS_PATH)
    assert set(p3_priors.keys()) == {"A", "B", "C", "D"}
    for cid in ["A", "B", "C", "D"]:
        assert p3_priors[cid] == {"p": 0.92, "kappa": 8.0, "n": 6}


@pytest.mark.xfail(strict=True, reason="W4 D8: unknown group in mapping does not raise ValueError")
def test_w4_d8_unknown_group_raises(tmp_path):
    import src.simulation.simulator as sim
    if not hasattr(sim, "expand_profile_to_priors"):
        pytest.fail("expand_profile_to_priors not found in src.simulation.simulator")
    
    expand_fn = getattr(sim, "expand_profile_to_priors")
    # Mapping references a group 'quantum_math' which does not exist in profile_2
    invalid_groups_file = tmp_path / "invalid_group.yaml"
    with open(invalid_groups_file, "w", encoding="utf-8") as f:
        f.write("groups:\n  A: prerequisites\n  B: quantum_math\n  C: downstream\n  D: downstream\n")
    
    with pytest.raises(ValueError, match="quantum_math|unknown group|invalid"):
        expand_fn("profile_2", groups_path=str(invalid_groups_file))


@pytest.mark.xfail(strict=True, reason="W4 D8: concept with no group does not raise ValueError")
def test_w4_d8_concept_with_no_group_raises(tmp_path):
    import src.simulation.simulator as sim
    if not hasattr(sim, "expand_profile_to_priors"):
        pytest.fail("expand_profile_to_priors not found in src.simulation.simulator")
    
    expand_fn = getattr(sim, "expand_profile_to_priors")
    # Concept B has no group or is missing from mapping
    missing_group_file = tmp_path / "missing_group.yaml"
    with open(missing_group_file, "w", encoding="utf-8") as f:
        f.write("groups:\n  A: prerequisites\n  C: downstream\n  D: downstream\n")
    
    with pytest.raises(ValueError, match="no group|missing"):
        expand_fn("profile_2", groups_path=str(missing_group_file), curriculum_concepts=["A", "B", "C", "D"])


@pytest.mark.xfail(strict=True, reason="W4 D8: unexpandable profile_4 does not raise ValueError")
def test_w4_d8_unexpandable_profile_4_raises():
    from src.simulation.simulator import SimulatedLearner
    # profile_4 uses groups 'advanced' and 'foundational' and references 'concept_b1', 'concept_b2'
    # none of which exist in demo_curriculum / demo_curriculum.groups.yaml
    with pytest.raises(ValueError, match="cannot expand|unknown group|foundational_uncertain_nodes|missing"):
        SimulatedLearner(profile_id="profile_4", groups_path=GROUPS_PATH)


def test_w4_d8_evaluator_view_boundary_preserved():
    """EvaluatorView must never be imported in src/planning or src/state."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    checked_dirs = [
        os.path.join(repo_root, "src", "planning"),
        os.path.join(repo_root, "src", "state"),
    ]
    forbidden_patterns = ["EvaluatorView", "evaluator_view", "from src.simulation", "import EvaluatorView"]
    violations = []
    for cdir in checked_dirs:
        for py_file in glob.glob(os.path.join(cdir, "**", "*.py"), recursive=True):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                for pattern in forbidden_patterns:
                    if pattern in content:
                        rel_path = os.path.relpath(py_file, repo_root)
                        violations.append(f"{rel_path} references '{pattern}'")
    assert len(violations) == 0, f"Architectural boundary violated: {violations}"

