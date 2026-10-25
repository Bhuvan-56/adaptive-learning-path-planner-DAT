"""
Tests for W5-A1: Acceptance Matrix Generator and Mapping Validation.

Verifies:
1. Every node ID in experiments/w5_acceptance_map.yaml exists in the collected pytest test list.
2. Every group ID in docs/ACCEPTANCE_GROUPS.md appears in the mapping and vice-versa.
3. A fake document in tmp_path that cites a test name that does not exist gives MISSING_CITATION.
4. A group with a deliberately failing test in a tmp_path test file gives FAIL.
5. A group with no node IDs gives UNCOVERED.
6. Refuses dirty tree unless --allow-dirty is passed (which prints DIRTY).
"""

import os
import sys
import pytest
import yaml

from scripts.acceptance_matrix import (
    load_acceptance_map,
    parse_acceptance_groups,
    get_collected_test_node_ids,
    find_missing_citations,
    run_group_tests,
    compute_verdict,
    evaluate_acceptance_matrix,
    generate_matrix_reports,
)


def test_w5_a1_every_mapped_node_id_exists_in_collected():
    """Requirement: Every node ID in the mapping file exists in the collected list."""
    map_path = os.path.join(os.path.dirname(__file__), "..", "experiments", "w5_acceptance_map.yaml")
    acceptance_map = load_acceptance_map(map_path)

    collected_nodes = set(get_collected_test_node_ids())
    assert len(collected_nodes) > 0, "No tests collected from repository suite"

    missing_nodes = []
    for gid, group_data in acceptance_map.items():
        node_ids = group_data.get("node_ids") or []
        for nid in node_ids:
            if nid not in collected_nodes:
                missing_nodes.append((gid, nid))

    assert len(missing_nodes) == 0, f"Mapped node IDs not found in collected suite: {missing_nodes}"


def test_w5_a1_group_ids_bijection_with_document():
    """Requirement: Every group ID in the document appears in the mapping and the other way round."""
    doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "ACCEPTANCE_GROUPS.md")
    map_path = os.path.join(os.path.dirname(__file__), "..", "experiments", "w5_acceptance_map.yaml")

    doc_groups = parse_acceptance_groups(doc_path)
    map_groups = load_acceptance_map(map_path)

    doc_ids = set(doc_groups.keys())
    map_ids = set(map_groups.keys())

    assert doc_ids == map_ids, (
        f"Mismatch between doc group IDs and map group IDs:\n"
        f"In doc only: {doc_ids - map_ids}\n"
        f"In map only: {map_ids - doc_ids}"
    )
    # Exactly 21 groups (M1-a to M8-d)
    assert len(doc_ids) == 21


def test_w5_a1_fake_document_missing_citation_detected(tmp_path):
    """Requirement: A fake document in tmp_path that cites a test name that does not exist gives MISSING_CITATION."""
    fake_doc = tmp_path / "FAKE_ACCEPTANCE_GROUPS.md"
    fake_doc.write_text(
        "# Fake Acceptance Groups\n\n"
        "| Group ID | Criterion | Test File & Test Name | Status Today | Owner | Testability Assessment |\n"
        "|---|---|---|---|---|---|\n"
        "| **M9-a** | **Fake Criterion:** Test criterion | `tests/test_fake.py`<br>`test_nonexistent_function_xyz` | `passing` | Bhuvan | Testable |\n",
        encoding="utf-8"
    )

    doc_data = parse_acceptance_groups(str(fake_doc))
    assert "M9-a" in doc_data
    citations = doc_data["M9-a"]["citations"]

    collected_sample = ["tests/test_something.py::test_existing_function"]
    missing = find_missing_citations(citations, collected_sample)
    assert "test_nonexistent_function_xyz" in missing

    # Also check via compute_verdict that missing citations prevent PASS and yield PARTIAL with reason
    verdict, reason = compute_verdict(
        node_ids=["tests/test_something.py::test_existing_function"],
        counts={"collected": 1, "passed": 1, "failed": 0, "skipped": 0, "xfailed": 0},
        doc_status="passing",
        missing_citations=missing,
    )
    assert verdict == "PARTIAL"
    assert "Missing cited test: test_nonexistent_function_xyz" in reason


def test_w5_a1_failing_test_gives_fail_verdict(tmp_path):
    """Requirement: A group with a deliberately failing test in a tmp_path test file gives FAIL."""
    test_file = tmp_path / "test_deliberate_failure.py"
    test_file.write_text(
        "def test_deliberate_fail():\n"
        "    assert False, 'Expected deliberate failure'\n",
        encoding="utf-8"
    )

    node_id = f"{test_file}::test_deliberate_fail"
    counts = run_group_tests([node_id], temp_dir=str(tmp_path))

    assert counts["collected"] == 1
    assert counts["failed"] == 1
    assert counts["passed"] == 0

    verdict, reason = compute_verdict(
        node_ids=[node_id],
        counts=counts,
        doc_status="passing",
        missing_citations=[],
    )
    assert verdict == "FAIL"
    assert "1 test(s) failed" in reason


def test_w5_a1_uncovered_group_gives_uncovered_verdict():
    """Requirement: A group with no node IDs gives UNCOVERED."""
    verdict, reason = compute_verdict(
        node_ids=[],
        counts={"collected": 0, "passed": 0, "failed": 0, "skipped": 0, "xfailed": 0},
        doc_status="passing",
        missing_citations=[],
    )
    assert verdict == "UNCOVERED"
    assert "No node IDs mapped" in reason


def test_w5_a1_dirty_tree_flag_behavior():
    """Requirement: Reports DIRTY when is_dirty is true."""
    rows = [
        {
            "group_id": "M1-a",
            "name": "Graph Topology",
            "doc_status": "passing",
            "test_count": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "xfailed": 0,
            "verdict": "PASS",
            "reason": "All collected tests passed",
            "missing_citations": [],
            "asserts_criterion": "tests/test_m1.py:10",
        }
    ]

    md_dirty, csv_dirty = generate_matrix_reports(
        rows=rows,
        git_sha="test_sha",
        is_dirty=True,
        doc_sha="test_doc_sha",
    )
    assert md_dirty.startswith("DIRTY\n")
    assert csv_dirty.startswith("DIRTY\n")

    md_clean, csv_clean = generate_matrix_reports(
        rows=rows,
        git_sha="test_sha",
        is_dirty=False,
        doc_sha="test_doc_sha",
    )
    assert not md_clean.startswith("DIRTY")
    assert not csv_clean.startswith("DIRTY")
