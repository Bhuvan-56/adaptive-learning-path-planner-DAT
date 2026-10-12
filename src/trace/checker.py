from typing import Set, List, Dict, Any
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


def check_trace(candidate_universe: Set[str], trace: List[Dict[str, Any]], num_days: int = 1) -> bool:
    """
    Validates automated trace completeness (TC-7.3).

    Trace check FAILS if:
    1. Trace is empty while candidate_universe is non-empty.
    2. Any day in 1..num_days has no entries.
    3. Any duplicate node appears on a given day.
    4. Any candidate in candidate_universe is missing or extra on a given day.
    5. Any decision is not in {"SELECTED", "FILTERED"}.
    6. Any reason code is not in ReasonCode.
    7. Decision and reason code mismatch (SELECTED must have SELECTED, FILTERED must have filtering reason).
    8. Any of the 8 schema fields is missing from an entry.
    9. Reason ALREADY_MASTERED contradicts concept_state (concept_state must be Mastered).

    Returns True if valid; raises ValueError if invalid.
    """
    if not trace and candidate_universe:
        raise ValueError("Trace is empty while candidate universe is non-empty.")

    if not isinstance(trace, list):
        raise ValueError("Trace must be a list of trace entry dictionaries.")

    # Group entries by day
    entries_by_day: Dict[int, List[Dict[str, Any]]] = {}
    for entry in trace:
        day = entry.get("day")
        if day is None:
            raise ValueError("Trace entry missing schema field: 'day'.")
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
