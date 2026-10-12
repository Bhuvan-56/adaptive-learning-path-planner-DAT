from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any


class ReasonCode(str, Enum):
    SELECTED = "SELECTED"
    PREREQUISITE_UNMET = "PREREQUISITE_UNMET"
    ALREADY_MASTERED = "ALREADY_MASTERED"
    ALREADY_SCHEDULED = "ALREADY_SCHEDULED"
    COMPLETED = "COMPLETED"
    BLOCK_EXCEEDS_DAILY_BUDGET = "BLOCK_EXCEEDS_DAILY_BUDGET"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    UNCERTAIN_NEEDS_ASSESSMENT = "UNCERTAIN_NEEDS_ASSESSMENT"


@dataclass
class TraceEntry:
    """
    Structured trace entry representing a single planning decision for one candidate node on one day.

    Note: score_terms is empty `{}` for the static baseline planner. This is intentional until the scored policy planner exists in Week 3+.
    """
    node_id: str
    day: int
    concept_state: Dict[str, Any]
    constraints: Dict[str, Any]
    score_terms: Dict[str, Any]
    decision: str  # "SELECTED" or "FILTERED"
    reason_code: str
    policy_version: str = "static_baseline_v0"


    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if isinstance(self.reason_code, Enum):
            data["reason_code"] = self.reason_code.value
        return data
