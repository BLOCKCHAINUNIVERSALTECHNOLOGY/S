"""SAI configuration helpers — Phase C"""

import os


def status() -> dict:
    url = os.environ.get("S_AI_URL", "")
    key = os.environ.get("S_AI_KEY", "")
    model = os.environ.get("S_AI_MODEL", "gpt-4o-mini")
    mode = "live" if (url and key) else "stub"
    return {
        "mode": mode,
        "url": url or "(not set)",
        "model": model,
        "key_set": bool(key),
    }


def help_text() -> str:
    return """SAI — S AI Engine
Modes:
  stub  — no network (default). Built-in placeholder replies.
  live  — set S_AI_URL + S_AI_KEY (+ optional S_AI_MODEL)

Example:
  export S_AI_URL="https://api.openai.com/v1/chat/completions"
  export S_AI_KEY="sk-..."
  export S_AI_MODEL="gpt-4o-mini"
  python3 s run examples/android_ai_demo.s
"""
