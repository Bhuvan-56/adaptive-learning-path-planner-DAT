"""
Evaluation and benchmark comparison package.

CRITICAL ARCHITECTURAL BOUNDARY:
--------------------------------
Modules in this package evaluate simulator behavior, diagnostic efficacy,
and planning policies. They may import from `src.simulation`, `src.diagnostic`,
and `src.planning`.
However, modules under `src.planning` and `src.state` MUST NEVER import from
`src.evaluation`.
"""

from src.evaluation.compare import (
    load_comparison_config,
    run_diagnostic_comparison,
    run_planner_comparison,
    run_all_comparisons,
)

__all__ = [
    "load_comparison_config",
    "run_diagnostic_comparison",
    "run_planner_comparison",
    "run_all_comparisons",
]
