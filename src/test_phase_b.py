
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
    print("OK versions")

def test_resolve():
    reg = json.loads((Path(__file__).parent.parent / "hub/registry.json").read_text())
    r = resolve_package(reg, "mathx", ">=0.2.0")
    assert r["version"] == "0.2.0"
    print("OK resolve")

def test_checker():
    diags = check_program(parse_source("let x = none()\nprint x + 1\n"))
    assert any(d.severity == "error" for d in diags)
    diags2 = check_program(parse_source("print 1 + 2\n"))
    assert not any(d.severity == "error" for d in diags2)
    print("OK checker")

if __name__ == "__main__":
    test_versions()
    test_resolve()
    test_checker()
    print("Phase B unit checks passed")
