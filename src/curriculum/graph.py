import json
from typing import List
import networkx as nx

from src.curriculum.errors import GraphErrorCode

MIN_DIFFICULTY: float = 0.05
MAX_DIFFICULTY: float = 0.95


def load_graph(path: str) -> nx.DiGraph:
    """Loads a JSON curriculum graph definition into a networkx DiGraph."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    g = nx.DiGraph()

    for node in data.get("nodes", []):
        node_id = node.get("node_id")
        if node_id is not None:
            g.add_node(
                node_id,
                concept_name=node.get("concept_name"),
                baseline_duration=node.get("baseline_duration"),
                exercises=node.get("exercises", []),
                base_difficulty=node.get("base_difficulty"),
            )

    declared_nodes = set(g.nodes)

    # Store raw edges even if nodes might be missing for validator to inspect
    raw_edges = []
    for edge in data.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        importance = edge.get("importance", 1.0)
        raw_edges.append((source, target, importance))
        if source in declared_nodes and target in declared_nodes:
            g.add_edge(source, target, importance=importance)

    g.graph["raw_edges"] = raw_edges
    return g



def validate_graph(g: nx.DiGraph) -> List[GraphErrorCode]:
    """
    Validates a curriculum graph against six strict graph integrity checks:
    1. MISSING_NODE: Edge references non-existent node.
    2. NONPOSITIVE_DURATION: Baseline duration <= 0 or null.
    3. DIFFICULTY_OUT_OF_RANGE: Base difficulty outside [MIN_DIFFICULTY, MAX_DIFFICULTY].
    4. SELF_LOOP: Node has edge pointing to itself.
    5. CYCLE_DETECTED: Graph contains cyclic components (SCC size > 1).
    6. NON_FINITE_VALUE: Baseline duration or base difficulty is NaN or infinite.

    Returns a list of GraphErrorCode entries. Never raises on bad data.
    """
    import math
    errors: List[GraphErrorCode] = []

    # 1. Missing node check
    declared_nodes = set(g.nodes)
    has_missing_node = False
    raw_edges = g.graph.get("raw_edges", [])
    for src, tgt, _ in raw_edges:
        if src not in declared_nodes or tgt not in declared_nodes:
            has_missing_node = True
            break
    if has_missing_node:
        errors.append(GraphErrorCode.MISSING_NODE)

    # 2. Duration check: non-finite or non-positive
    has_non_finite_dur = False
    has_bad_duration = False
    for _, attrs in g.nodes(data=True):
        dur = attrs.get("baseline_duration")
        if dur is not None and (not isinstance(dur, (int, float)) or not math.isfinite(dur)):
            has_non_finite_dur = True
            break
        elif dur is None or dur <= 0:
            has_bad_duration = True
            break

    # 3. Difficulty check: non-finite or out of range [MIN_DIFFICULTY, MAX_DIFFICULTY]
    has_non_finite_diff = False
    has_bad_difficulty = False
    for _, attrs in g.nodes(data=True):
        diff = attrs.get("base_difficulty")
        if diff is not None and (not isinstance(diff, (int, float)) or not math.isfinite(diff)):
            has_non_finite_diff = True
            break
        elif diff is None or diff < MIN_DIFFICULTY or diff > MAX_DIFFICULTY:
            has_bad_difficulty = True
            break

    # Edge importance check: non-finite
    has_non_finite_edge_imp = False
    for edge in raw_edges:
        if len(edge) >= 3:
            imp = edge[2]
            if imp is not None and (not isinstance(imp, (int, float)) or not math.isfinite(imp)):
                has_non_finite_edge_imp = True
                break

    if not has_non_finite_edge_imp:
        for _, _, attrs in g.edges(data=True):
            imp = attrs.get("importance")
            if imp is not None and (not isinstance(imp, (int, float)) or not math.isfinite(imp)):
                has_non_finite_edge_imp = True
                break

    if has_non_finite_dur or has_non_finite_diff or has_non_finite_edge_imp:
        errors.append(GraphErrorCode.NON_FINITE_VALUE)
    if has_bad_duration:
        errors.append(GraphErrorCode.NONPOSITIVE_DURATION)
    if has_bad_difficulty:
        errors.append(GraphErrorCode.DIFFICULTY_OUT_OF_RANGE)


    # 4. Self loop check
    has_self_loop = len(list(nx.nodes_with_selfloops(g))) > 0
    if has_self_loop:
        errors.append(GraphErrorCode.SELF_LOOP)

    # 5. Cycle check (SCC size > 1)
    sccs = list(nx.strongly_connected_components(g))
    has_cycle = any(len(scc) > 1 for scc in sccs)
    if has_cycle:
        errors.append(GraphErrorCode.CYCLE_DETECTED)

    return errors
