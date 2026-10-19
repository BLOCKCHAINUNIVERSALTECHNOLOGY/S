"""S Hub lockfile + version constraints — Phase B4

s.lock format (JSON content, S-owned filename):
{
  "lock_version": 1,
  "packages": {
    "mathx": { "version": "0.1.0", "entry": "mathx.s" }
  }
}

Version strings: exact "0.1.0" or ">=0.1.0"
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import json
import re


def parse_version(v: str) -> Tuple[int, int, int]:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", v.strip())
    if not m:
        raise ValueError(f"Invalid version: {v}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def version_satisfies(have: str, constraint: str) -> bool:
    constraint = constraint.strip()
    if constraint.startswith(">="):
        return parse_version(have) >= parse_version(constraint[2:].strip())
    if constraint.startswith(">"):
        return parse_version(have) > parse_version(constraint[1:].strip())
    if constraint.startswith("<="):
        return parse_version(have) <= parse_version(constraint[2:].strip())
    if constraint.startswith("<"):
        return parse_version(have) < parse_version(constraint[1:].strip())
    if constraint.startswith("=="):
        return have == constraint[2:].strip()
    # exact
    return have == constraint


def parse_pkg_spec(spec: str) -> Tuple[str, Optional[str]]:
    """mathx or mathx@0.1.0 or mathx@>=0.1.0"""
    if "@" in spec:
        name, ver = spec.split("@", 1)
        return name.strip(), ver.strip()
    return spec.strip(), None


def load_lock(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"lock_version": 1, "packages": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_lock(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def resolve_package(registry: dict, name: str, constraint: Optional[str]) -> dict:
    packages = registry.get("packages", {})
    if name not in packages:
        raise KeyError(f"Package not found: {name}")
    info = packages[name]
    # support single version or versions list
    if "versions" in info:
        candidates = info["versions"]
    else:
        candidates = [{"version": info["version"], "entry": info.get("entry", f"{name}.s")}]
    if constraint is None:
        # latest by tuple
        best = max(candidates, key=lambda c: parse_version(c["version"]))
        return {**info, **best, "name": name}
    matched = [c for c in candidates if version_satisfies(c["version"], constraint)]
    if not matched:
        raise KeyError(f"No version of {name} satisfies {constraint}")
    best = max(matched, key=lambda c: parse_version(c["version"]))
    return {**info, **best, "name": name}
