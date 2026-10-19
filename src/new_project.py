"""s new — create a complete, runnable S project."""

from pathlib import Path

HELLO = """// {name} — S project
// Simple · Safe · Supreme

fn greet(who: str): str {{
  ret "Hello, " + who + "!"
}}

print greet("{name}")
print "Ready. Run: s check main.s"
print json_stringify({{ "project": "{name}", "ok": true }})
"""

README = """# {name}

Made with **S** — Simple · Safe · Supreme

```bash
python3 s run main.s
python3 s check main.s
python3 s build .
```
"""

PROJECT_SE = """# S project identity
name: {name}
version: 0.1.0
entry: main.s
strict_let_collections: false
"""

NOTES = """# {name} notes

Design notes (.sd).
"""


def create(name: str, dest: str) -> Path:
    root = Path(dest) / name if dest else Path(name)
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.s").write_text(HELLO.format(name=name), encoding="utf-8")
    (root / "project.se").write_text(PROJECT_SE.format(name=name), encoding="utf-8")
    (root / "README.sd").write_text(NOTES.format(name=name), encoding="utf-8")
    (root / "README.md").write_text(README.format(name=name), encoding="utf-8")
    (root / "s_modules").mkdir(exist_ok=True)
    return root
