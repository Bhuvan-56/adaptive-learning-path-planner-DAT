import os
import pytest
import networkx as nx

from src.curriculum.graph import MIN_DIFFICULTY, MAX_DIFFICULTY
from src.planning.difficulty import (
    DifficultyState,
    step_difficulty,
    load_adaptive_config,
    get_step_size
)
from src.state.learner_state import ConceptState
from src.planning.replan import replan, assessment_result


def test_tc_4_1_single_failure_decreases_difficulty_floored_at_0_05():
    """TC-4.1: A single failure decreases difficulty by step (0.10), floored at 0.05."""
    s0 = DifficultyState(difficulty=0.20, consecutive_successes=0)
    s1 = step_difficulty(s0, correct=False)
    assert s1.difficulty == pytest.approx(0.10)
    assert s1.consecutive_successes == 0

    s2 = step_difficulty(s1, correct=False)
    assert s2.difficulty == pytest.approx(0.05)
    assert s2.consecutive_successes == 0

    # Below floor: remains floored at 0.05
    s3 = step_difficulty(s2, correct=False)
    assert s3.difficulty == pytest.approx(MIN_DIFFICULTY)
    assert s3.consecutive_successes == 0


def test_tc_4_2_two_consecutive_successes_increase_difficulty_capped_at_0_95():
    """TC-4.2: Two consecutive successes increase difficulty by step (0.10), capped at 0.95."""
    s0 = DifficultyState(difficulty=0.85, consecutive_successes=0)

    # First success increments streak without increasing difficulty
    s1 = step_difficulty(s0, correct=True)
    assert s1.difficulty == pytest.approx(0.85)
    assert s1.consecutive_successes == 1

    # Second consecutive success triggers difficulty increase and resets streak
    s2 = step_difficulty(s1, correct=True)
    assert s2.difficulty == pytest.approx(0.95)
    assert s2.consecutive_successes == 0

    # At cap: two more successes stay capped at 0.95
    s3 = step_difficulty(s2, correct=True)
    assert s3.consecutive_successes == 1
    s4 = step_difficulty(s3, correct=True)
    assert s4.difficulty == pytest.approx(MAX_DIFFICULTY)
    assert s4.consecutive_successes == 0


def test_difficulty_floor():
    """Repeated failures clamp strictly at MIN_DIFFICULTY."""
    s = DifficultyState(difficulty=MIN_DIFFICULTY, consecutive_successes=0)
    for _ in range(5):
        s = step_difficulty(s, correct=0)
    assert s.difficulty == pytest.approx(MIN_DIFFICULTY)
    assert s.consecutive_successes == 0


def test_difficulty_cap():
    """Repeated successes clamp strictly at MAX_DIFFICULTY."""
    s = DifficultyState(difficulty=MAX_DIFFICULTY, consecutive_successes=0)
    for _ in range(6):
        s = step_difficulty(s, correct=1)
    assert s.difficulty == pytest.approx(MAX_DIFFICULTY)


def test_reset_of_success_counter_after_failure():
    """A failure resets the consecutive successes counter."""
    s0 = DifficultyState(difficulty=0.50, consecutive_successes=0)

    # 1 success -> streak = 1
    s1 = step_difficulty(s0, correct=1)
    assert s1.consecutive_successes == 1
    assert s1.difficulty == pytest.approx(0.50)

    # 1 failure -> streak resets to 0, difficulty drops by 0.10
    s2 = step_difficulty(s1, correct=0)
    assert s2.consecutive_successes == 0
    assert s2.difficulty == pytest.approx(0.40)

    # 1 success -> streak = 1, difficulty does NOT step up yet
    s3 = step_difficulty(s2, correct=1)
    assert s3.consecutive_successes == 1
    assert s3.difficulty == pytest.approx(0.40)

    # 2nd success -> streak resets to 0, difficulty steps up to 0.50
    s4 = step_difficulty(s3, correct=1)
    assert s4.consecutive_successes == 0
    assert s4.difficulty == pytest.approx(0.50)


def test_response_driven_change_appearing_in_trace():
    """A response-driven difficulty change appears in the trace entry score_terms as exercise_difficulty."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5, base_difficulty=0.50)

    states = {"A": ConceptState.cold_start()}
    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 1,
        "target_node": "A",
        "current_day": 1
    }

    # Failure response drops difficulty from 0.50 to 0.40
    res1 = replan(state, assessment_result("A", [0]))
    trace1 = [e for e in res1["trace"] if e["node_id"] == "A"]
    assert len(trace1) > 0
    assert "exercise_difficulty" in trace1[0]["score_terms"]
    assert trace1[0]["score_terms"]["exercise_difficulty"] == pytest.approx(0.40)

    # Two consecutive successes step difficulty up from 0.40 to 0.50
    state2 = {
        "graph": g,
        "learner_states": res1["learner_states"],
        "difficulty_states": res1["difficulty_states"],
        "budget": 10,
        "deadline_days": 1,
        "target_node": "A",
        "current_day": 1
    }
    res2 = replan(state2, assessment_result("A", [1, 1]))
    trace2 = [e for e in res2["trace"] if e["node_id"] == "A"]
    assert len(trace2) > 0
    assert trace2[0]["score_terms"]["exercise_difficulty"] == pytest.approx(0.50)


def test_adaptive_yaml_strict_loader_missing_or_misspelled_key_raises(tmp_path):
    """Adaptive config loader strictly enforces schema and raises on missing, misspelled, or extra keys."""
    # 1. Missing key 'step'
    bad_cfg1 = tmp_path / "bad1.yaml"
    bad_cfg1.write_text("learning_rate: 0.1\n", encoding="utf-8")
    with pytest.raises((KeyError, ValueError)):
        load_adaptive_config(str(bad_cfg1))

    # 2. Misspelled key 'step_size'
    bad_cfg2 = tmp_path / "bad2.yaml"
    bad_cfg2.write_text("step_size: 0.1\n", encoding="utf-8")
    with pytest.raises((KeyError, ValueError)):
        load_adaptive_config(str(bad_cfg2))

    # 3. Unknown extra key
    bad_cfg3 = tmp_path / "bad3.yaml"
    bad_cfg3.write_text("step: 0.1\nextra_param: 42\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown key"):
        load_adaptive_config(str(bad_cfg3))

    # 4. Non-finite or invalid range
    bad_cfg4 = tmp_path / "bad4.yaml"
    bad_cfg4.write_text("step: .nan\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_adaptive_config(str(bad_cfg4))

    bad_cfg5 = tmp_path / "bad5.yaml"
    bad_cfg5.write_text("step: 0.0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_adaptive_config(str(bad_cfg5))

    bad_cfg6 = tmp_path / "bad6.yaml"
    bad_cfg6.write_text("step: 0.95\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_adaptive_config(str(bad_cfg6))
