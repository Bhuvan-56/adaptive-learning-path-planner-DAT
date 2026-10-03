from typing import Set
import networkx as nx


def get_candidate_universe(g: nx.DiGraph, target_node: str) -> Set[str]:
    """
    Extracts the full candidate universe for a given target concept node.

    The candidate universe contains the target node plus all of its ancestor nodes in the DAG
    (every node with a path leading to the target node). Blocked and skipped (already-mastered)
    nodes remain strictly visible in the universe.
    """
    if target_node not in g:
        return set()

    ancestors = nx.ancestors(g, target_node)
    return set(ancestors) | {target_node}
