
"""Phase B unit checks — run via: python3 -m src.test_phase_b"""
from src.hub_lock import version_satisfies, parse_pkg_spec, resolve_package, parse_version
from src.checker import check_program
from src.parser import parse_source
import json
from pathlib import Path

def test_versions():
    assert version_satisfies("0.2.0", ">=0.1.0")
    assert version_satisfies("0.1.0", "0.1.0")
    assert not version_satisfies("0.1.0", ">=0.2.0")
    assert parse_pkg_spec("mathx@>=0.2.0") == ("mathx", ">=0.2.0")

def test_resolve():
    reg = json.loads((Path(__file__).parent.parent / "hub/registry.json").read_text())
    r = resolve_package(reg, "mathx", ">=0.2.0")
    assert r["version"] == "0.2.0"

def test_checker():
    diags = check_program(parse_source("let x = none()\nprint x + 1\n"))
    assert any(d.severity == "error" for d in diags)
    diags2 = check_program(parse_source("print 1 + 2\n"))
    assert not any(d.severity == "error" for d in diags2)
def run_all():
    """Run Phase B checks and return standard test-runner results."""
    tests = [
        ("phase_b_versions", test_versions),
        ("phase_b_resolve", test_resolve),
        ("phase_b_checker", test_checker),
    ]
    results = []
    for name, test in tests:
        try:
            test()
            results.append((name, True, ""))
        except Exception as exc:
            results.append((name, False, f"{type(exc).__name__}: {exc}"))
    return results

if __name__ == "__main__":
    results = run_all()
    for name, ok, message in results:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {message}" if message else ""))
    if not all(ok for _, ok, _ in results):
        raise SystemExit(1)
    print(f"Phase B unit checks passed ({len(results)} tests)")
