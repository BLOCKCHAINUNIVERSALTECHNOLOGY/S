"""Load project.se — S project manifest"""
from pathlib import Path
from typing import Dict, Any

def load_project_se(start: str = ".") -> Dict[str, Any]:
    p = Path(start)
    for _ in range(5):
        cand = p / "project.se"
        if cand.exists():
            return _parse(cand.read_text(encoding="utf-8"))
        if p.parent == p:
            break
        p = p.parent
    return {}

def _parse(text: str) -> Dict[str, Any]:
    cfg = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if v.lower() in ("true", "yes", "on"):
                cfg[k] = True
            elif v.lower() in ("false", "no", "off"):
                cfg[k] = False
            else:
                cfg[k] = v
    return cfg
