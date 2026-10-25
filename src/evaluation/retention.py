"""
Delayed Retention Quiz Evaluation Module (Task W5-B2).

ARCHITECTURAL PRINCIPLE:
------------------------
This module is strictly evaluator-only. It evaluates operational retained recall
at a delayed observation point (D days post-intervention) by querying the simulator.
Planning algorithms (src/planning), cognitive state models (src/state), and
diagnostic testing (src/diagnostic) must NEVER import from src/evaluation or src/simulation.

PROTOCOL CITATIONS (docs/EVALUATION_PROTOCOL.md lines 63-73):
-------------------------------------------------------------
- N = 5 items per studied concept [PROPOSED] (docs/EVALUATION_PROTOCOL.md line 63)
- D = 7 days delay post-horizon [PROPOSED] (docs/EVALUATION_PROTOCOL.md line 65)
- Reference test difficulty d_0 = 0.50

SCORING MECHANISM:
-------------------
1. Advance the simulated learner by D days under the active generator's forgetting dynamics.
2. Administer N fresh simulated items per concept the learner studied.
3. Compute the retention rate as the overall share of items answered correctly:
   retention_share = (total_correct_items) / (total_items_administered)
"""

import os
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import yaml

from src.simulation.simulator import SimulatedLearner

DEFAULT_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "w5_integrated.yaml")
)

# Operational retention parameters [PROPOSED]
DEFAULT_RETENTION_N = 5  # items per concept (docs/EVALUATION_PROTOCOL.md line 63)
DEFAULT_RETENTION_D = 7  # delay days post-horizon (docs/EVALUATION_PROTOCOL.md line 65)
DEFAULT_REFERENCE_DIFFICULTY = 0.50


def load_retention_parameters(
    config_source: Optional[Union[str, Dict[str, Any]]] = None
) -> Tuple[int, int, float]:
    """
    Loads (N, D, reference_difficulty) retention parameters from YAML config or dictionary.
    Falls back to PROPOSED protocol defaults if not specified.
    """
    if config_source is None:
        c_path = DEFAULT_CONFIG_PATH
        if os.path.exists(c_path):
            with open(c_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            data = {}
    elif isinstance(config_source, str):
        if not os.path.exists(config_source):
            raise FileNotFoundError(f"Configuration file not found: {config_source}")
        with open(config_source, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif isinstance(config_source, dict):
        data = config_source
    else:
        raise ValueError(f"Invalid config_source type: {type(config_source)}")

    ret_block = data.get("retention", {})
    # Check planner_controls fallback for D
    controls_block = data.get("planner_controls", {})

    n = int(ret_block.get("items_per_concept_N", DEFAULT_RETENTION_N))
    d = int(ret_block.get("delay_days_D", controls_block.get("retention_delay_days", DEFAULT_RETENTION_D)))
    diff = float(ret_block.get("reference_difficulty", DEFAULT_REFERENCE_DIFFICULTY))

    return n, d, diff


def administer_retention_quiz(
    learner: SimulatedLearner,
    studied_concepts: List[str],
    n_items: Optional[int] = None,
    delay_days: Optional[int] = None,
    difficulty: Optional[float] = None,
    config_source: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Administers a delayed retention quiz to an individual simulated learner.

    Parameters:
        learner: SimulatedLearner instance holding the latent state at the end of planning horizon.
        studied_concepts: List of concept IDs that were scheduled/studied during the horizon.
        n_items: Number of items per concept to administer (overrides config if provided).
        delay_days: Number of days to advance under forgetting variant (overrides config if provided).
        difficulty: Reference item difficulty for evaluation queries (default 0.50).
        config_source: Optional path or dict to read retention parameters from.

    Returns:
        Dictionary containing retention summary, scores, per-concept breakdowns,
        and latent mastery snapshot via EvaluatorView.
    """
    cfg_n, cfg_d, cfg_diff = load_retention_parameters(config_source)
    n = cfg_n if n_items is None else int(n_items)
    d = cfg_d if delay_days is None else int(delay_days)
    diff = cfg_diff if difficulty is None else float(difficulty)

    if n <= 0:
        raise ValueError(f"n_items must be strictly positive, got {n}")
    if d < 0:
        raise ValueError(f"delay_days must be non-negative, got {d}")

    # 1. Advance simulation environment by D days (decaying mastered concepts if p_F > 0)
    learner.advance_day(num_days=d)

    # 2. Administer N items per studied concept
    per_concept_scores: Dict[str, List[int]] = {}
    total_items = 0
    total_correct = 0

    for concept in studied_concepts:
        scores = [
            learner.respond(concept=concept, difficulty=diff)
            for _ in range(n)
        ]
        per_concept_scores[concept] = scores
        total_items += len(scores)
        total_correct += sum(scores)

    retention_share = (total_correct / total_items) if total_items > 0 else 0.0
    eval_view = learner.evaluator_view()

    return {
        "delay_days_D": d,
        "items_per_concept_N": n,
        "reference_difficulty": diff,
        "studied_concepts": list(studied_concepts),
        "total_items": total_items,
        "total_correct": total_correct,
        "retention_share": retention_share,
        "per_concept_scores": per_concept_scores,
        "per_concept_share": {
            c: (sum(scores) / len(scores)) if scores else 0.0
            for c, scores in per_concept_scores.items()
        },
        "latent_mastery_snapshot": eval_view.latent_masteries,
    }


def evaluate_cohort_retention(
    learner_cohort: List[Tuple[SimulatedLearner, List[str]]],
    n_items: Optional[int] = None,
    delay_days: Optional[int] = None,
    difficulty: Optional[float] = None,
    config_source: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Administers delayed retention quizzes across a cohort of simulated learners.

    Parameters:
        learner_cohort: List of (SimulatedLearner, studied_concepts) pairs.

    Returns:
        Aggregated summary including mean retention share and individual results.
    """
    individual_results = []
    shares = []

    for learner, concepts in learner_cohort:
        res = administer_retention_quiz(
            learner=learner,
            studied_concepts=concepts,
            n_items=n_items,
            delay_days=delay_days,
            difficulty=difficulty,
            config_source=config_source,
        )
        individual_results.append(res)
        shares.append(res["retention_share"])

    mean_share = float(np.mean(shares)) if shares else 0.0

    return {
        "num_learners": len(learner_cohort),
        "mean_retention_share": mean_share,
        "individual_results": individual_results,
    }
