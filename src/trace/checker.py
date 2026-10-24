import math
from typing import Set, List, Dict, Any, Optional
from src.trace.schema import ReasonCode

VALID_REASON_CODES = {code.value for code in ReasonCode}
VALID_DECISIONS = {"SELECTED", "FILTERED"}
REQUIRED_SCHEMA_FIELDS = (
    "node_id",
    "day",
    "concept_state",
    "constraints",
    "score_terms",
    "decision",
    "reason_code",
    "policy_version",
)


def check_trace(
    candidate_universe: Set[str],
    trace: List[Dict[str, Any]],
    num_days: int = 1,
    budget: Optional[float] = None,
) -> bool:
    """
    Validates automated trace completeness (TC-7.3).

    Trace check FAILS if:
    1. Trace is empty while candidate_universe is non-empty.
    2. Trace is not a list or contains non-dict entries.
    3. Any day is outside 1..num_days or any day in 1..num_days has no entries.
    4. Any duplicate node appears on a given day.
    5. Any candidate in candidate_universe is missing or extra on a given day.
    6. Any decision is not in {"SELECTED", "FILTERED"}.
    7. Any reason code is not in ReasonCode.
    8. Decision and reason code mismatch (SELECTED must have SELECTED, FILTERED must have filtering reason).
    9. Any of the 8 schema fields is missing from an entry.
    10. Container types are invalid (concept_state, constraints, score_terms must be dicts).
    11. Values in containers are non-finite, out of bounds (p in [0,1], n >= 0, remaining_budget in [0, budget]).
    12. Reason ALREADY_MASTERED contradicts concept_state (concept_state must be Mastered).

    Returns True if valid; raises ValueError if invalid.
    """
    if not trace and candidate_universe:
        raise ValueError("Trace is empty while candidate universe is non-empty.")

    if not isinstance(trace, list):
        raise ValueError("Trace must be a list of trace entry dictionaries.")

    for idx, entry in enumerate(trace):
        if not isinstance(entry, dict):
            raise ValueError(f"Trace entry at index {idx} must be a dictionary.")

    # Group entries by day
    entries_by_day: Dict[int, List[Dict[str, Any]]] = {}
    for entry in trace:
        day = entry.get("day")
        if day is None:
            raise ValueError("Trace entry missing schema field: 'day'.")
        if not isinstance(day, int) or isinstance(day, bool):
            raise ValueError(f"Trace entry day must be an integer, got {day!r}.")
        if day < 1 or day > num_days:
            raise ValueError(f"Trace entry day {day} is outside valid range 1..{num_days}.")
        entries_by_day.setdefault(day, []).append(entry)

    # 1. Any day in 1..num_days with no entries
    for d in range(1, num_days + 1):
        if d not in entries_by_day or not entries_by_day[d]:
            raise ValueError(f"Trace missing all entries for day {d} of {num_days}.")

    for day in sorted(entries_by_day.keys()):
        entries = entries_by_day[day]
        seen_nodes = set()

        # Check duplicates on this day
        for entry in entries:
            node_id = entry.get("node_id")
            if not node_id:
                raise ValueError(f"Trace entry missing node_id on day {day}.")
            if node_id in seen_nodes:
                raise ValueError(f"Duplicate trace entry detected for node '{node_id}' on day {day}.")
            seen_nodes.add(node_id)

        # Check missing candidate nodes
        missing = candidate_universe - seen_nodes
        if missing:
            raise ValueError(f"Trace missing candidate nodes on day {day}: {sorted(list(missing))}")

        # Check extra candidate nodes
        extra = seen_nodes - candidate_universe
        if extra:
            raise ValueError(f"Trace contains unexpected candidate nodes on day {day}: {sorted(list(extra))}")

        # Validate entries on this day
        for entry in entries:
            node_id = entry["node_id"]
            decision = entry.get("decision")
            reason_code = entry.get("reason_code")

            if decision not in VALID_DECISIONS:
                raise ValueError(
                    f"Entry for node '{node_id}' on day {day} has invalid decision '{decision}'. Must be 'SELECTED' or 'FILTERED'."
                )

            if reason_code not in VALID_REASON_CODES:
                raise ValueError(
                    f"Entry for node '{node_id}' on day {day} filtered with invalid reason code '{reason_code}'."
                )

            if decision == "SELECTED" and reason_code != ReasonCode.SELECTED.value:
                raise ValueError(
                    f"Selected entry for node '{node_id}' on day {day} must carry reason SELECTED, got '{reason_code}'."
                )

            if decision == "FILTERED" and reason_code == ReasonCode.SELECTED.value:
                raise ValueError(
                    f"Filtered entry for node '{node_id}' on day {day} cannot carry reason SELECTED."
                )

            for field in REQUIRED_SCHEMA_FIELDS:
                if field not in entry:
                    raise ValueError(f"Trace entry for node '{node_id}' on day {day} missing schema field: '{field}'.")

            concept_state = entry["concept_state"]
            if not isinstance(concept_state, dict):
                raise ValueError(f"Trace entry for node '{node_id}' on day {day} has invalid concept_state (must be a dictionary).")

            for k, v in concept_state.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if not math.isfinite(v):
                        raise ValueError(f"Entry for node '{node_id}' on day {day} concept_state['{k}'] has non-finite value: {v}.")

            if "p" in concept_state:
                p = concept_state["p"]
                if not isinstance(p, (int, float)) or isinstance(p, bool) or not math.isfinite(p) or not (0.0 <= p <= 1.0):
                    raise ValueError(f"Entry for node '{node_id}' on day {day} has concept_state p outside [0, 1]: {p}.")

            if "n" in concept_state:
                n = concept_state["n"]
                if not isinstance(n, int) or isinstance(n, bool) or n < 0:
                    raise ValueError(f"Entry for node '{node_id}' on day {day} has negative concept_state n: {n}.")

            if "kappa" in concept_state:
                k = concept_state["kappa"]
                if not isinstance(k, (int, float)) or isinstance(k, bool) or not math.isfinite(k) or k <= 0:
                    raise ValueError(f"Entry for node '{node_id}' on day {day} has invalid concept_state kappa: {k}.")

            if "sigma2" in concept_state:
                s = concept_state["sigma2"]
                if not isinstance(s, (int, float)) or isinstance(s, bool) or not math.isfinite(s) or s < 0:
                    raise ValueError(f"Entry for node '{node_id}' on day {day} has invalid concept_state sigma2: {s}.")

            constraints = entry["constraints"]
            if not isinstance(constraints, dict):
                raise ValueError(f"Trace entry for node '{node_id}' on day {day} has invalid constraints (must be a dictionary).")

            for k, v in constraints.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if not math.isfinite(v):
                        raise ValueError(f"Entry for node '{node_id}' on day {day} constraints['{k}'] has non-finite value: {v}.")

            if "remaining_budget" in constraints:
                rem_budget = constraints["remaining_budget"]
                if not isinstance(rem_budget, (int, float)) or isinstance(rem_budget, bool) or not math.isfinite(rem_budget):
                    raise ValueError(f"Entry for node '{node_id}' on day {day} has non-finite remaining_budget: {rem_budget}.")
                if rem_budget < 0:
                    raise ValueError(f"Entry for node '{node_id}' on day {day} has negative remaining_budget: {rem_budget}.")
                if budget is not None and rem_budget > budget:
                    raise ValueError(f"Entry for node '{node_id}' on day {day} has remaining_budget {rem_budget} exceeding daily budget {budget}.")

            score_terms = entry["score_terms"]
            if not isinstance(score_terms, dict):
                raise ValueError(f"Trace entry for node '{node_id}' on day {day} has invalid score_terms (must be a dictionary).")

            for k, v in score_terms.items():
                if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
                    raise ValueError(f"Entry for node '{node_id}' on day {day} score_terms['{k}'] has non-finite value: {v}.")

            if reason_code == ReasonCode.ALREADY_MASTERED.value:
                concept_class = (
                    concept_state.get("class")
                    if isinstance(concept_state, dict)
                    else getattr(concept_state, "class", None)
                )
                if concept_class != "Mastered":
                    raise ValueError(
                        f"Entry for node '{node_id}' on day {day} has reason ALREADY_MASTERED but concept state '{concept_class}' (expected 'Mastered')."
                    )

    return True


def check_no_plan_trace(trace: Any) -> bool:
    """
    Validates a no-plan trace contract (for an infeasible or invalid-input outcome).

    A no-plan trace has no daily candidate entries, but must carry:
    - status
    - reason_code
    - constraints (containing at least 'budget')

    Returns True if valid; raises ValueError if invalid.
    """
    if isinstance(trace, list):
        if any(isinstance(item, dict) and "node_id" in item and "day" in item for item in trace):
            raise ValueError("No-plan trace must not contain daily candidate entries.")
        if len(trace) == 1 and isinstance(trace[0], dict):
            trace_dict = trace[0]
        else:
            raise ValueError("No-plan trace must carry status, reason code and constraints.")
    elif isinstance(trace, dict):
        if "node_id" in trace and "day" in trace:
            raise ValueError("No-plan trace must not contain daily candidate entries.")
        trace_dict = trace
    else:
        raise ValueError("No-plan trace must be a dictionary or list containing trace contract.")

    if not trace_dict.get("status"):
        raise ValueError("No-plan trace missing required field: 'status'.")

    if not trace_dict.get("reason_code"):
        raise ValueError("No-plan trace missing required field: 'reason_code'.")

    constraints = trace_dict.get("constraints")
    if not isinstance(constraints, dict) or "budget" not in constraints:
        raise ValueError("No-plan trace missing required constraints containing 'budget'.")

    return True
