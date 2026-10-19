# S Language v1.0.0 "Supreme" — Release Checklist

## Acceptance Criteria

- [x] Lexer + Parser + Interpreter working
- [x] let / var / functions / classes
- [x] list + map collections
- [x] Modules (use) + cycle detection
- [x] Slib standard library
- [x] SDX + SAI API stubs
- [x] Kotlin emit backend
- [x] assert + safe/rescue
- [x] Test suite passing
- [x] s doctor healthy
- [x] Version file present
- [x] CHANGELOG present
- [x] README present
- [x] Examples present

## CLI Commands

| Command | Purpose |
|---------|---------|
| s run <file> | Execute S program |
| s check <file> | Parse only |
| s test | Run test suite |
| s doctor | Health check |
| s lib | List modules |
| s emit kotlin <file> | Emit Kotlin |
| s version | Show version |
| s repl | Interactive REPL |
| s tokens / s ast | Debug tools |

## Install (developer)

```bash
cd project-s
python3 s version
python3 s doctor
python3 s test
python3 s run examples/hello.s
```

Requires: Python 3.10+

## Known Limits (v1.0)

- SDX/SAI are stubs (no real Android/AI runtime yet)
- Kotlin emit is demonstration, not full compile
- No LSP / IDE plugin yet
- Single-threaded interpreter
- No package registry (S Hub) yet

## Next after v1.0

- Real Android bridge (SBridge)
- Real AI provider integration
- LSP for S Studio
- spack package manager
- Native / WASM backends
