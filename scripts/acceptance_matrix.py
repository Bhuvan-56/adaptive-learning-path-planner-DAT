"""
Acceptance Matrix Generator for M1-M8 Acceptance Groups.

Verdict rules, declared in the script's docstring:
PASS only if at least one test is collected, all pass, none is skipped, and the group has no MISSING_CITATION.
PARTIAL if any test is skipped or the document says partial.
FAIL if any test fails.
UNCOVERED if no node ID maps to the group.

This script executes pytest across all acceptance groups, collects empirical execution
metrics, parses docs/ACCEPTANCE_GROUPS.md, evaluates verdicts against formal rules,
and writes structured markdown and CSV reports with git and document provenance metadata.
"""

import argparse
import csv
import datetime
import hashlib
import io
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# pyrefly: ignore[missing-import]
import pytest
import sys
import yaml


class PytestResultCollector:
    """Pytest plugin to capture exact test outcome counts without cacheprovider."""

    def __init__(self) -> None:
        self.collected = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.xfailed = 0

    def pytest_collection_modifyitems(self, items: List[Any]) -> None:
        self.collected = len(items)

    def pytest_runtest_logreport(self, report: Any) -> None:
        if report.when == "call":
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1
            elif report.skipped:
                if hasattr(report, "wasxfail"):
                    self.xfailed += 1
                else:
                    self.skipped += 1
        elif report.when in ("setup", "teardown"):
            if report.failed:
                self.failed += 1
            elif report.skipped and not getattr(report, "wasxfail", None):
                self.skipped += 1


def parse_acceptance_groups(doc_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Parses acceptance groups table from markdown document.
    Extracts group ID, name, criterion text, claimed status, and citations.
    """
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"Document not found: {doc_path}")

    groups: Dict[str, Dict[str, Any]] = {}
    with open(doc_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines):
        line_s = line.strip()
        if not line_s.startswith("| **M"):
            continue

        raw_parts = [p.strip() for p in line_s.split("|")]
        if len(raw_parts) < 6:
            continue

        parts = raw_parts[1:-1]
        gid = parts[0].replace("*", "").strip()
        status = parts[-3].replace("`", "").strip()
        owner = parts[-2].strip()
        tests_cell = parts[-4].strip()
        crit_full = "|".join(parts[1:-4]).strip()

        # Parse name and criterion
        m = re.match(r"^\s*\*\*([^*]+)\*\*\s*:\s*(.*)", crit_full, re.DOTALL)
        if m:
            name = m.group(1).strip()
            criterion = m.group(2).strip()
        else:
            m2 = re.match(r"^\s*\*\*([^*:]+):\*\*\s*(.*)", crit_full, re.DOTALL)
            if m2:
                name = m2.group(1).strip()
                criterion = m2.group(2).strip()
            else:
                name = crit_full
                criterion = crit_full

        # Citations in backticks
        citations = re.findall(r"`([^`]+)`", tests_cell)

        groups[gid] = {
            "group_id": gid,
            "name": name,
            "criterion": criterion,
            "status": status,
            "owner": owner,
            "citations": [c.strip() for c in citations],
            "line_number": idx + 1,
        }

    return groups


def load_acceptance_map(map_path: str) -> Dict[str, Dict[str, Any]]:
    """Loads experiments acceptance map YAML."""
    if not os.path.exists(map_path):
        raise FileNotFoundError(f"Mapping file not found: {map_path}")

    with open(map_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected dictionary in mapping file, got {type(data)}")

    return data


def get_collected_test_node_ids() -> List[str]:
    """Runs pytest --collect-only -q to get authoritative list of test node IDs."""
    class NodeCollector:
        def __init__(self) -> None:
            self.nodes: List[str] = []

        def pytest_collection_modifyitems(self, items: List[Any]) -> None:
            self.nodes = [item.nodeid for item in items]

    col = NodeCollector()
    with tempfile.TemporaryDirectory() as tmpdir:
        pytest.main(["--collect-only", "-q", "-p", "no:cacheprovider", f"--basetemp={tmpdir}"], plugins=[col])

    return col.nodes


def find_missing_citations(cited_items: List[str], collected_nodes: List[str]) -> List[str]:
    """
    Finds test citations in document that are not present in collected pytest nodes.
    A citation is checked if it looks like a test function or test node.
    """
    collected_names = set()
    for node in collected_nodes:
        func = node.split("::")[-1].split("[")[0]
        collected_names.add(node)
        collected_names.add(func)

    missing = []
    for c in cited_items:
        # Check if item refers to a specific test function or node
        if "::" in c:
            test_name = c.split("::")[-1].split("[")[0]
            if c not in collected_names and test_name not in collected_names:
                missing.append(c)
        elif c.startswith("test_"):
            if c not in collected_names:
                missing.append(c)
    return missing


def run_group_tests(node_ids: List[str], temp_dir: Optional[str] = None) -> Dict[str, int]:
    """
    Runs pytest for a list of node IDs with -p no:cacheprovider and output captured.
    Returns counts of collected, passed, failed, skipped, xfailed.
    """
    if not node_ids:
        return {"collected": 0, "passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}

    collector = PytestResultCollector()
    out_capture = io.StringIO()
    err_capture = io.StringIO()

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    basetemp_dir = os.path.join(temp_dir, "pytest_run") if temp_dir else tempfile.mkdtemp()
    os.makedirs(basetemp_dir, exist_ok=True)

    args = list(node_ids) + ["-p", "no:cacheprovider", "-q", f"--basetemp={basetemp_dir}"]

    try:
        sys.stdout = out_capture
        sys.stderr = err_capture
        pytest.main(args, plugins=[collector])
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    # If log folder provided, save output
    if temp_dir:
        log_file = os.path.join(temp_dir, "pytest_output.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"--- Pytest run for: {node_ids} ---\n")
            f.write(out_capture.getvalue())
            f.write(err_capture.getvalue())
            f.write("\n")

    return {
        "collected": collector.collected,
        "passed": collector.passed,
        "failed": collector.failed,
        "skipped": collector.skipped,
        "xfailed": collector.xfailed,
    }


def compute_verdict(
    node_ids: List[str],
    counts: Dict[str, int],
    doc_status: str,
    missing_citations: List[str],
) -> Tuple[str, str]:
    """
    Computes acceptance verdict based on formal specification rules:
    - PASS only if at least one test is collected, all pass, none is skipped, and no MISSING_CITATION.
    - PARTIAL if any test is skipped or the document says partial or has MISSING_CITATION.
    - FAIL if any test fails.
    - UNCOVERED if no node ID maps to the group.

    Returns (verdict, reason).
    """
    collected = counts.get("collected", 0)
    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0)
    skipped = counts.get("skipped", 0)
    xfailed = counts.get("xfailed", 0)

    if len(node_ids) == 0:
        return "UNCOVERED", "No node IDs mapped to group"

    if failed > 0:
        return "FAIL", f"{failed} test(s) failed"

    # Check partial conditions
    reasons: List[str] = []
    if doc_status.lower() == "partial":
        reasons.append("Document marks status as partial")
    if skipped > 0:
        reasons.append(f"{skipped} test(s) skipped")
    if len(missing_citations) > 0:
        reasons.append(f"Missing cited test: {', '.join(missing_citations)}")

    if reasons:
        return "PARTIAL", "; ".join(reasons)

    if collected > 0 and passed == collected and skipped == 0 and len(missing_citations) == 0:
        return "PASS", "All collected tests passed"

    return "PARTIAL", "Incomplete verification or unclassified state"


def get_git_info() -> Tuple[str, bool]:
    """Returns (git_sha, is_dirty)."""
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        sha = "UNKNOWN_SHA"

    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        is_dirty = len(status) > 0
    except Exception:
        is_dirty = False

    return sha, is_dirty


def compute_file_sha256(path: str) -> str:
    """Computes SHA-256 hash of a file."""
    if not os.path.exists(path):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def evaluate_acceptance_matrix(
    doc_path: str = "docs/ACCEPTANCE_GROUPS.md",
    map_path: str = "experiments/w5_acceptance_map.yaml",
    temp_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Evaluates all groups in the acceptance matrix and returns row records."""
    doc_groups = parse_acceptance_groups(doc_path)
    map_groups = load_acceptance_map(map_path)

    # Union of group IDs from doc and map
    all_gids = sorted(list(set(doc_groups.keys()) | set(map_groups.keys())))

    rows: List[Dict[str, Any]] = []
    for gid in all_gids:
        doc_entry = doc_groups.get(gid, {})
        map_entry = map_groups.get(gid, {})

        name = map_entry.get("name") or doc_entry.get("name") or gid
        doc_status = doc_entry.get("status") or map_entry.get("doc_status") or "unknown"
        node_ids = map_entry.get("node_ids") or map_entry.get("tests") or []
        asserts_criterion = map_entry.get("asserts_criterion") or "NONE FOUND"

        # Explicit missing citations in map or calculated from doc citations
        explicit_missing = map_entry.get("missing_citations") or map_entry.get("MISSING_CITATION") or []
        if isinstance(explicit_missing, str):
            explicit_missing = [explicit_missing]

        missing_citations = list(explicit_missing)

        # Run pytest on group's node IDs
        counts = run_group_tests(node_ids, temp_dir=temp_dir)
        verdict, reason = compute_verdict(node_ids, counts, doc_status, missing_citations)

        rows.append({
            "group_id": gid,
            "name": name,
            "doc_status": doc_status,
            "test_count": len(node_ids),
            "passed": counts["passed"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "xfailed": counts["xfailed"],
            "verdict": verdict,
            "reason": reason,
            "missing_citations": missing_citations,
            "asserts_criterion": asserts_criterion,
            "node_ids": node_ids,
        })

    return rows


def generate_matrix_reports(
    rows: List[Dict[str, Any]],
    git_sha: str,
    is_dirty: bool,
    doc_sha: str,
) -> Tuple[str, str]:
    """Generates markdown and CSV report strings."""
    # Build markdown
    md_lines: List[str] = []
    if is_dirty:
        md_lines.append("DIRTY")
        md_lines.append("")

    md_lines.append("# Acceptance Matrix (Week 5 Snapshot)")
    md_lines.append("")
    md_lines.append(f"- **Git SHA:** `{git_sha}`")
    md_lines.append(f"- **Tracked Tree Dirty:** `{str(is_dirty).lower()}`")
    md_lines.append(f"- **docs/ACCEPTANCE_GROUPS.md SHA-256:** `{doc_sha}`")
    md_lines.append(f"- **Generated:** `{datetime.datetime.now(datetime.timezone.utc).isoformat()}`")
    md_lines.append("")
    md_lines.append("## Acceptance Groups Status Matrix (M1–M8)")
    md_lines.append("")
    md_lines.append("| Group ID | Name | Doc Status | Tests | Passed | Failed | Skipped | XFailed | Verdict | Missing Citations | ASSERTS_CRITERION |")
    md_lines.append("|---|---|---|---|---|---|---|---|---|---|---|")

    for r in rows:
        missing_str = ", ".join(r["missing_citations"]) if r["missing_citations"] else "None"
        md_lines.append(
            f"| **{r['group_id']}** | {r['name']} | `{r['doc_status']}` | {r['test_count']} | "
            f"{r['passed']} | {r['failed']} | {r['skipped']} | {r['xfailed']} | "
            f"**{r['verdict']}** | {missing_str} | `{r['asserts_criterion']}` |"
        )

    md_lines.append("")
    md_lines.append("## Non-PASS Summary")
    md_lines.append("")
    non_pass = [r for r in rows if r["verdict"] != "PASS"]
    if not non_pass:
        md_lines.append("All groups achieved PASS.")
    else:
        for r in non_pass:
            md_lines.append(f"- **{r['group_id']} ({r['name']}):** {r['verdict']} — {r['reason']}")

    md_lines.append("")
    md_content = "\n".join(md_lines) + "\n"

    # Build CSV
    csv_buffer = io.StringIO()
    if is_dirty:
        csv_buffer.write("DIRTY\n")

    writer = csv.writer(csv_buffer)
    writer.writerow([
        "GROUP_ID",
        "NAME",
        "DOC_STATUS",
        "TESTS_COUNT",
        "PASSED",
        "FAILED",
        "SKIPPED",
        "XFAILED",
        "VERDICT",
        "REASON",
        "MISSING_CITATIONS",
        "ASSERTS_CRITERION",
    ])
    for r in rows:
        missing_str = "; ".join(r["missing_citations"]) if r["missing_citations"] else "NONE"
        writer.writerow([
            r["group_id"],
            r["name"],
            r["doc_status"],
            r["test_count"],
            r["passed"],
            r["failed"],
            r["skipped"],
            r["xfailed"],
            r["verdict"],
            r["reason"],
            missing_str,
            r["asserts_criterion"],
        ])

    csv_content = csv_buffer.getvalue()
    return md_content, csv_content


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Week 5 Acceptance Matrix.")
    parser.add_argument(
        "--out",
        type=str,
        default="evaluation/results/w5",
        help="Output directory for matrix reports (default: evaluation/results/w5)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="acceptance_matrix_r1",
        help="Base filename prefix for output reports (default: acceptance_matrix_r1)",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow generation when tracked tree is dirty (refuses otherwise)",
    )
    parser.add_argument(
        "--map",
        type=str,
        default="experiments/w5_acceptance_map.yaml",
        help="Path to acceptance map YAML",
    )
    parser.add_argument(
        "--doc",
        type=str,
        default="docs/ACCEPTANCE_GROUPS.md",
        help="Path to ACCEPTANCE_GROUPS.md",
    )

    args = parser.parse_args()

    git_sha, is_dirty = get_git_info()
    if is_dirty and not args.allow_dirty:
        sys.stderr.write("ERROR: Working tree is dirty. Clean tree or pass --allow-dirty.\n")
        return 1

    doc_sha = compute_file_sha256(args.doc)

    with tempfile.TemporaryDirectory() as temp_dir:
        rows = evaluate_acceptance_matrix(
            doc_path=args.doc,
            map_path=args.map,
            temp_dir=temp_dir,
        )

        md_content, csv_content = generate_matrix_reports(
            rows=rows,
            git_sha=git_sha,
            is_dirty=is_dirty,
            doc_sha=doc_sha,
        )

    os.makedirs(args.out, exist_ok=True)
    md_path = os.path.join(args.out, f"{args.prefix}.md")
    csv_path = os.path.join(args.out, f"{args.prefix}.csv")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    # Print to stdout
    print(md_content)
    print(f"Matrix reports written to:\n  - {md_path}\n  - {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
