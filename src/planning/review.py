"""
Review and remediation planning module for Module M5.

This module implements:
1. ReviewLog: Per-learner history mapping concept to a list of (time_in_days, correct) records.
   Time is simulated days since plan start, tracked as a float (declared in this docstring).
   ConceptState carries NO timestamp field and is completely unmodified.
2. DECAY_BASELINE: Recall decay baseline estimating R(dt) = 2 ** (-dt / H), where H is
   fixed at the declared half_life_prior_days (14.0) loaded from experiments/m8_learner_eval.yaml.
   NOTE: This baseline model is named DECAY_BASELINE in code and comments. It is NOT Half-Life
   Regression (HLR) and H is NOT learned or fitted on data. No HLR model was fitted or integrated.
3. Review eligibility: A concept is review-eligible when its state is evidence Mastered
   and its estimated recall R(dt) is strictly below review_eligibility_recall_threshold (0.85).
4. Prerequisite remediation: When a concept has k consecutive failed assessments (k loaded from
   config/adaptive.yaml under remediation block), returns its not-Mastered ancestors in
   topological order to be scheduled first inside the same daily budget.
"""

from dataclasses import dataclass, field
import math
import os
from typing import Dict, List, Set, Optional, Tuple, NamedTuple, Any
import networkx as nx
import yaml

from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig
from src.planning.difficulty import load_remediation_config, DEFAULT_CONFIG_PATH


DEFAULT_EVAL_CONFIG_PATH = "experiments/m8_learner_eval.yaml"
DECAY_BASELINE = "DECAY_BASELINE"


def load_review_eval_config(path: Optional[str] = None) -> Dict[str, float]:
    """
    Loads review evaluation baseline parameters from experiments/m8_learner_eval.yaml.

    Reads:
    - half_life_prior_days (fixed H = 14.0)
    - review_eligibility_recall_threshold (0.85)

    Enforces strict validation on config structure.
    """
    cfg_path = path if path is not None else DEFAULT_EVAL_CONFIG_PATH
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"Learner eval config not found: {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Eval config at {cfg_path} must be a dictionary.")

    hyperparams = data.get("model_hyperparameters")
    if not isinstance(hyperparams, dict):
        raise KeyError("Missing 'model_hyperparameters' in eval config.")

    hlr_block = hyperparams.get("hlr")
    if not isinstance(hlr_block, dict):
        raise KeyError("Missing 'hlr' block under 'model_hyperparameters' in eval config.")

    if "half_life_prior_days" not in hlr_block:
        raise KeyError("Missing 'half_life_prior_days' in hlr block.")
    if "review_eligibility_recall_threshold" not in hlr_block:
        raise KeyError("Missing 'review_eligibility_recall_threshold' in hlr block.")

    h_raw = hlr_block["half_life_prior_days"]
    thresh_raw = hlr_block["review_eligibility_recall_threshold"]

    if isinstance(h_raw, bool) or not isinstance(h_raw, (int, float)) or not math.isfinite(h_raw) or h_raw <= 0:
        raise ValueError(f"half_life_prior_days must be a positive finite number, got {h_raw!r}")

    if isinstance(thresh_raw, bool) or not isinstance(thresh_raw, (int, float)) or not math.isfinite(thresh_raw) or not (0.0 < thresh_raw <= 1.0):
        raise ValueError(f"review_eligibility_recall_threshold must be in (0, 1], got {thresh_raw!r}")

    return {
        "half_life_prior_days": float(h_raw),
        "review_eligibility_recall_threshold": float(thresh_raw),
    }


def calculate_recall_decay(dt: float, half_life_days: float = 14.0) -> float:
    """
    Computes recall estimate R(dt) = 2 ** (-dt / H) under DECAY_BASELINE.

    Named DECAY_BASELINE in code and comments.
    NOTE: H is fixed at half_life_prior_days (14.0 days). This is NOT Half-Life
    Regression (HLR) and H is NOT learned or fitted.
    """
    if dt <= 0:
        return 1.0
    return 2.0 ** (-float(dt) / float(half_life_days))


class ReviewRecord(NamedTuple):
    """
    A single practice or assessment record for a concept.

    time_in_days: Simulated days since plan start (float >= 0.0).
    correct: Boolean indicating whether the response was correct.
    """
    time_in_days: float
    correct: bool


@dataclass
class ReviewLog:
    """
    Per-learner review log mapping concept_id to a list of (time_in_days, correct) records.
    Time is simulated days since plan start, tracked as a float.

    ConceptState carries NO timestamp field and is completely unmodified.
    """
    records: Dict[str, List[ReviewRecord]] = field(default_factory=dict)

    def record_attempt(self, concept_id: str, time_in_days: float, correct: bool) -> None:
        """Appends a new attempt record (time_in_days, correct) for concept_id."""
        if concept_id not in self.records:
            self.records[concept_id] = []
        self.records[concept_id].append(
            ReviewRecord(time_in_days=float(time_in_days), correct=bool(correct))
        )

    def get_records(self, concept_id: str) -> List[ReviewRecord]:
        """Returns all records for concept_id as a list of (time_in_days, correct) namedtuples."""
        return list(self.records.get(concept_id, []))

    def get_last_review_time(self, concept_id: str) -> Optional[float]:
        """Returns the most recent time_in_days for concept_id, or None if no records exist."""
        recs = self.records.get(concept_id, [])
        if not recs:
            return None
        return recs[-1].time_in_days

    def get_consecutive_failures(self, concept_id: str) -> int:
        """Returns the number of trailing consecutive incorrect attempts for concept_id."""
        recs = self.records.get(concept_id, [])
        count = 0
        for rec in reversed(recs):
            if not rec.correct:
                count += 1
            else:
                break
        return count


def is_review_eligible(
    concept_id: str,
    concept_state: ConceptState,
    review_log: Optional[ReviewLog],
    current_day: float,
    policy: Optional[PolicyConfig] = None,
    half_life_days: float = 14.0,
    threshold: float = 0.85,
) -> Tuple[bool, float]:
    """
    Evaluates whether a concept is review-eligible on current_day under DECAY_BASELINE.

    A concept is review-eligible when:
    1. Its state is evidence Mastered (concept_state.classify(policy) == 'Mastered').
    2. Estimated recall R(dt) < threshold (0.85).

    dt is computed as (current_day - last_review_time). If no record exists in review_log,
    elapsed time defaults to current_day (relative to plan start at day 0.0).

    Returns:
    (is_eligible: bool, recall_estimate: float)
    """
    classification = concept_state.classify(policy)
    if classification != "Mastered":
        return False, 1.0

    last_time = None
    if review_log is not None:
        last_time = review_log.get_last_review_time(concept_id)

    dt = (current_day - last_time) if last_time is not None else float(current_day)
    r = calculate_recall_decay(dt, half_life_days=half_life_days)
    is_eligible = (r < threshold)
    return is_eligible, r


def get_remediation_ancestors(
    g: nx.DiGraph,
    failed_node: str,
    learner_states: Dict[str, ConceptState],
    policy: Optional[PolicyConfig] = None,
    completed_nodes: Optional[Set[str]] = None,
) -> List[str]:
    """
    Returns the not-Mastered ancestors of failed_node in deterministic topological order.

    When a concept has k consecutive failed assessments, replan returns a remediation
    plan: the not-Mastered ancestors of that concept in topological order, scheduled
    first inside the same daily budget.
    """
    if g is None or failed_node not in g:
        return []

    ancestors = nx.ancestors(g, failed_node)
    completed = completed_nodes or set()

    unmastered = []
    for anc in ancestors:
        if anc in completed:
            continue
        st = learner_states.get(anc, ConceptState.cold_start())
        if st.classify(policy) != "Mastered":
            unmastered.append(anc)

    if not unmastered:
        return []

    subgraph = g.subgraph(unmastered)
    return list(nx.lexicographical_topological_sort(subgraph))
