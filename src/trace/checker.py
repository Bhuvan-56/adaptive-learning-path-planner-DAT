from typing import Set, List, Dict, Any
from src.trace.schema import ReasonCode

VALID_REASON_CODES = {code.value for code in ReasonCode}


def check_trace(candidate_universe: Set[str], trace: List[Dict[str, Any]], num_days: int = 1) -> bool:
    """
    Validates automated trace completeness (TC-7.3).

    Trace check FAILS if:
    1. Any candidate in candidate_universe is missing from trace for a day.
    2. Any candidate is duplicated for a given day in trace.
    3. Any entry has decision FILTERED without a valid machine-readable reason code.

    Returns True if valid; raises ValueError if invalid.
    """
    if not trace and candidate_universe:
        raise ValueError("Trace is empty while candidate universe is non-empty.")

    # Group entries by day
    entries_by_day: Dict[int, List[Dict[str, Any]]] = {}
    for entry in trace:
        day = entry.get("day", 1)
        entries_by_day.setdefault(day, []).append(entry)

    for day, entries in entries_by_day.items():
        seen_nodes = set()
        for entry in entries:
            node_id = entry.get("node_id")
            if not node_id:
                raise ValueError(f"Trace entry missing node_id on day {day}.")

            if node_id in seen_nodes:
                raise ValueError(f"Duplicate trace entry detected for node '{node_id}' on day {day}.")
            seen_nodes.add(node_id)

            decision = entry.get("decision")
            reason_code = entry.get("reason_code")

            if decision == "FILTERED":
                if not reason_code or reason_code not in VALID_REASON_CODES:
                    raise ValueError(
                        f"Entry for node '{node_id}' on day {day} filtered with invalid reason code '{reason_code}'."
                    )

        missing = candidate_universe - seen_nodes
        if missing:
            raise ValueError(f"Trace missing candidate nodes on day {day}: {sorted(list(missing))}")

    return True
