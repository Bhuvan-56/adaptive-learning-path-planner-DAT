import pytest
from src.evaluation.compare import run_planner_comparison
from src.simulation.simulator import SimulatedLearner


def test_w5_f1_planner_controls_executes_activities(tmp_path):
    """
    Verifies that run_planner_comparison executes scheduled activities for static and adaptive arms.
    In the unfixed code, lines 727 and 829 query .get('lessons', []) which evaluates to [] because
    generate_static_plan and replan emit 'activities', causing 0 activities to be executed.
    """
    out_dir = str(tmp_path / "f1_test")
    call_counts = []
    orig_respond = SimulatedLearner.respond

    def wrapped_respond(self, concept, difficulty=0.5):
        call_counts.append(concept)
        return orig_respond(self, concept=concept, difficulty=difficulty)

    SimulatedLearner.respond = wrapped_respond
    try:
        run_planner_comparison(
            output_dir=out_dir,
            override_learners=2,
            override_resamples=10,
        )
    finally:
        SimulatedLearner.respond = orig_respond

    # Unfixed code only executes non_adaptive_greedy (8 calls for 2 learners: A, B, C, D each)
    # Fixed code executes static_prerequisite_order and adaptive_replan activities as well.
    assert len(call_counts) > 8, (
        f"Only greedy executed activities ({len(call_counts)} calls); static and adaptive executed 0."
    )
