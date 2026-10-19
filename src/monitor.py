"""Simple local crash / event log for S apps (Wave 4)."""

from __future__ import annotations
import json
import os
import time
from pathlib import Path


def log_path() -> Path:
    base = Path(os.environ.get("S_LOG_DIR", Path.home() / ".s-lang" / "logs"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "events.jsonl"


def emit(event: str, detail: dict | None = None) -> None:
    rec = {
        "ts": time.time(),
        "event": event,
        "detail": detail or {},
    }
    try:
        with log_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def report_crash(message: str, where: str = "") -> None:
    emit("crash", {"message": message, "where": where})
