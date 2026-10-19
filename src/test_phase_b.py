
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

def _type_errors(source):
    return [d for d in check_program(parse_source(source)) if d.severity == "error"]

def test_checker_annotations_and_widening():
    assert _type_errors('let age: int = "five"\n')
    assert not _type_errors("let price: dec = 5\n")

def test_checker_function_calls():
    source = "fn add(a: int, b: int): int { ret a + b }\nprint add(1, 2)\n"
    assert not _type_errors(source)
    assert _type_errors('fn add(a: int, b: int): int { ret a + b }\nadd("1", 2)\n')
    errors = _type_errors("fn add(a: int, b: int): int { ret a + b }\nadd(1)\nadd(1, 2, 3)\n")
    assert len(errors) == 2

def test_checker_return_types():
    assert _type_errors('fn count(): int { ret "many" }\n')
    assert not _type_errors("fn count(): int { ret 3 }\n")

def test_checker_assignment_mutability_and_types():
    errors = _type_errors('var count: int = 0\ncount = "many"\n')
    assert any("assignment to 'count'" in d.message for d in errors)
    inferred = _type_errors('var count = 0\ncount = "many"\n')
    assert any("assignment to 'count'" in d.message for d in inferred)
    errors = _type_errors("let fixed: int = 1\nfixed = 2\n")
    assert any("immutable" in d.message for d in errors)

def test_checker_block_scopes():
    source = 'if true { let value: int = 1 }\nif true { let value: str = "one" }\n'
    assert not _type_errors(source)

def test_checker_index_types():
    errors = _type_errors('let names = ["a"]\nprint names["0"]\n')
    assert any("list index" in d.message for d in errors)

def test_checker_strict_name_resolution():
    errors = [d for d in check_program(parse_source("print missing_name\n"), strict=True) if d.severity == "error"]
    assert any("Unknown name 'missing_name'" in d.message for d in errors)
    errors = [d for d in check_program(parse_source("missing_function()\n"), strict=True) if d.severity == "error"]
    assert any("Unknown function 'missing_function'" in d.message for d in errors)
    imported = check_program(parse_source("use toolkit\nprint imported_name\n"), strict=True)
    assert not any(d.severity == "error" for d in imported)

def test_checker_parameters_are_immutable():
    errors = _type_errors("fn change(n: int): int { n = 2\nret n }\n")
    assert any("immutable" in d.message for d in errors)

def run_all():
    """Run Phase B checks and return standard test-runner results."""
    tests = [
        ("phase_b_versions", test_versions),
        ("phase_b_resolve", test_resolve),
        ("phase_b_checker", test_checker),
        ("phase_b_checker_annotations", test_checker_annotations_and_widening),
        ("phase_b_checker_calls", test_checker_function_calls),
        ("phase_b_checker_returns", test_checker_return_types),
        ("phase_b_checker_assignments", test_checker_assignment_mutability_and_types),
        ("phase_b_checker_scopes", test_checker_block_scopes),
        ("phase_b_checker_indexes", test_checker_index_types),
        ("phase_b_checker_strict_names", test_checker_strict_name_resolution),
        ("phase_b_checker_param_mutability", test_checker_parameters_are_immutable),
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
