"""Real SAI backend — uses HTTP API when S_AI_KEY / S_AI_URL set, else stub.

Environment:
  S_AI_URL   — chat completions endpoint (OpenAI-compatible)
  S_AI_KEY   — API key
  S_AI_MODEL — model name (default: grok-beta or gpt-4o-mini)
"""

import os
import json
import urllib.request
import urllib.error


def ask(prompt: str) -> str:
    url = os.environ.get("S_AI_URL", "")
    key = os.environ.get("S_AI_KEY", "")
    model = os.environ.get("S_AI_MODEL", "gpt-4o-mini")

    if not url or not key:
        return f"[SAI stub] No S_AI_KEY/S_AI_URL set. Prompt was: {prompt}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
            return body["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[SAI error] {e}"


def generate(prompt: str) -> str:
    return ask(f"Generate content for: {prompt}")
