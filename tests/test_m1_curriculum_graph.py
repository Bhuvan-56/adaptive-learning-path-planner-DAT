import os
import pytest
from src.curriculum.graph import load_graph, validate_graph
from src.curriculum.errors import GraphErrorCode

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "graphs")


def test_tc_1_2_valid_branching_graph_passes():
    """TC-1.2: Valid branching graph passes all 5 graph validation checks."""
    path = os.path.join(FIXTURES_DIR, "valid_branching.json")
    g = load_graph(path)
    errors = validate_graph(g)
    assert errors == []


@pytest.mark.parametrize(
    "filename, expected_error",
    [
        ("missing_node.json", GraphErrorCode.MISSING_NODE),
        ("nonpositive_duration.json", GraphErrorCode.NONPOSITIVE_DURATION),
        ("difficulty_out_of_range.json", GraphErrorCode.DIFFICULTY_OUT_OF_RANGE),
        ("self_loop.json", GraphErrorCode.SELF_LOOP),
        ("cycle_detected.json", GraphErrorCode.CYCLE_DETECTED),
    ],
)
def test_tc_1_2_rejects_malformed_graph_files(filename, expected_error):
    """TC-1.2: Malformed graph fixtures yield ONLY their specific error code."""
    path = os.path.join(FIXTURES_DIR, filename)
    g = load_graph(path)
    errors = validate_graph(g)
    assert errors == [expected_error]
