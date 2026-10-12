import dataclasses
import hashlib
import json
import os
import platform
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def _normalize_obj(obj: Any) -> Any:
    """Recursively converts dataclasses, dicts, lists, sets, and primitives into canonical JSON-serializable types."""
    if dataclasses.is_dataclass(obj):
        return _normalize_obj(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _normalize_obj(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [_normalize_obj(v) for v in obj]
    if isinstance(obj, set):
        return [_normalize_obj(v) for v in sorted(list(obj))]
    if isinstance(obj, float):
        if obj.is_integer():
            return int(obj)
        return round(obj, 8)
    return obj


def resolved_config_hash(obj: Any) -> str:
    """
    Computes a deterministic SHA-256 hash of the canonical sorted JSON representation
    of a resolved configuration object (including dataclasses, seeds, and dictionaries).
    """
    normalized = _normalize_obj(obj)
    canonical_json = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def get_git_info() -> Tuple[str, bool]:
    """Retrieves current git commit SHA and dirty working tree status."""
    git_sha = "unknown"
    dirty = False
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0:
            git_sha = res.stdout.strip()
    except Exception:
        pass

    try:
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False
        )
        if res_status.returncode == 0:
            dirty = bool(res_status.stdout.strip())
    except Exception:
        pass

    return git_sha, dirty


def get_package_versions() -> Dict[str, str]:
    """Retrieves pinned runtime package versions."""
    versions = {}
    for pkg in ("numpy", "networkx", "pytest", "yaml"):
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[pkg] = "not_installed"
    return versions


def write_manifest(
    path: str,
    experiment_name: str,
    config_hash: str,
    seeds: List[int],
    git_sha: str,
    python_version: str,
    package_versions: Dict[str, str],
    timestamp: str,
    data_route: str,
    dataset_provenance: Optional[Dict[str, Any]] = None,
    dirty: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Writes a structured execution provenance manifest to path.
    Records experiment metadata, configuration hash, seeds, environment, and git state.
    """
    if dirty is None:
        _, is_dirty = get_git_info()
        dirty = is_dirty

    manifest: Dict[str, Any] = {
        "experiment_name": experiment_name,
        "config_hash": config_hash,
        "seeds": list(seeds),
        "git_sha": git_sha,
        "dirty": bool(dirty),
        "python_version": python_version,
        "package_versions": package_versions,
        "timestamp": timestamp,
        "data_route": data_route,
    }

    if dataset_provenance is not None:
        manifest["dataset_provenance"] = dataset_provenance

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    return manifest
