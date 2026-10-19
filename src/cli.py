#!/usr/bin/env python3
"""S Language CLI — M2

Usage:
  s new     <name>       Create a complete S project (joy path)
  s run     <file.s>     Run an S program
  s check   <file.s>     Parse + basic checks only
  s tokens  <file.s>     Show tokens
  s ast     <file.s>     Show AST
  s test                 Run the test suite
  s doctor               Health check of the toolchain
  s version              Show version
  s lib                  List built-in Slib modules
  s emit kotlin <file.s> Emit Kotlin-style code
  s vm <file.s>          Run via SVM bytecode VM
  s hub                  List/search/install/publish packages
  s fmt <file.s>         Minimal format (trim + newline)
  s sai [status|help]    AI engine status
  s sbridge init <dir>   Android SBridge scaffold
  s bench                LOC benchmarks vs Kotlin-style
  s symbols <file.s>     List definitions (goto-def data)
  s rename <file> <old> <new>  Rename symbol in file
  s protect <file.s>     Encrypt to .sbx (S Shield)
  s unbox <file.sbx>     Decrypt .sbx (developer + key)
  s seal-append <sbx> <file.s>  Join file into sealed pack
  s build [dir]          Release pack → dist/*.sbx
  s release [dir]        Full gate: test + check + build
  s log                  Local event / crash log (last 50)
  s html build <file.s>  Static site from S (W-WEB-1)
  s serve [dir] [--go]   HTTP serve (Python or Go native)
  s check file.s [--strict]  Type/safety checks
  s hub search <q>        Search Hub
  s hub install <name>    Install package
  s hub publish <n> <f>   Publish local package
  s repl                 Interactive REPL
"""

import sys
import json
import os
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lexer import Lexer, TokenKind
from src.parser import parse_source
from src.interpreter import Interpreter
from src.errors import SError, ParseError, RuntimeError_
from src.ast import *


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def report_error(e: Exception):
    """Always print clean S errors — never raw Python tracebacks for user code."""
    if isinstance(e, SError):
        print(f"error: {e}", file=sys.stderr)
    else:
        # Unexpected internal error
        print(f"internal error: {e}", file=sys.stderr)
    sys.exit(1)


def cmd_tokens(path: str):
    source = read_file(path)
    lexer = Lexer(source, path)
    tokens = lexer.tokenize()
    for t in tokens:
        if t.kind == TokenKind.NEWLINE:
            print(f"{t.span}: NEWLINE")
        elif t.kind == TokenKind.EOF:
            print(f"{t.span}: EOF")
        else:
            print(f"{t.span}: {t.kind.name:12} {t.text!r}")


def cmd_ast(path: str):
    try:
        program = parse_source(read_file(path), path)
        print_ast(program)
    except SError as e:
        try:
            from src.monitor import report_crash
            report_crash(str(e), where=path if "path" in dir() else "")
        except Exception:
            pass
        report_error(e)


def print_ast(node, indent=0):
    prefix = "  " * indent
    if isinstance(node, Program):
        print(f"{prefix}Program")
        for s in node.statements:
            print_ast(s, indent + 1)
    elif isinstance(node, LetDecl):
        kind = "var" if node.mutable else "let"
        print(f"{prefix}{kind} {node.name}" + (f": {node.type_ann}" if node.type_ann else ""))
        print_ast(node.value, indent + 1)
    elif isinstance(node, Assign):
        print(f"{prefix}Assign {node.name} =")
        print_ast(node.value, indent + 1)
    elif isinstance(node, PrintStmt):
        print(f"{prefix}print")
        for a in node.args:
            print_ast(a, indent + 1)
    elif isinstance(node, ExprStmt):
        print(f"{prefix}ExprStmt")
        print_ast(node.expr, indent + 1)
    elif isinstance(node, IfStmt):
        print(f"{prefix}if")
        print_ast(node.condition, indent + 1)
        print(f"{prefix}then")
        print_ast(node.then_branch, indent + 1)
        if node.else_branch:
            print(f"{prefix}else")
            print_ast(node.else_branch, indent + 1)
    elif isinstance(node, LoopStmt):
        print(f"{prefix}loop")
        print_ast(node.body, indent + 1)
    elif isinstance(node, ForStmt):
        print(f"{prefix}for {node.var} in")
        print_ast(node.iterable, indent + 1)
        print_ast(node.body, indent + 1)
    elif isinstance(node, Block):
        print(f"{prefix}{{")
        for s in node.stmts:
            print_ast(s, indent + 1)
        print(f"{prefix}}}")
    elif isinstance(node, FnDecl):
        params = ", ".join(f"{n}: {t}" for n, t in node.params)
        print(f"{prefix}fn {node.name}({params}): {node.return_type}")
        print_ast(node.body, indent + 1)
    elif isinstance(node, RetStmt):
        print(f"{prefix}ret")
        if node.value:
            print_ast(node.value, indent + 1)
    elif isinstance(node, BreakStmt):
        print(f"{prefix}break")
    elif isinstance(node, NextStmt):
        print(f"{prefix}next")
    elif isinstance(node, IntLit):
        print(f"{prefix}Int({node.value})")
    elif isinstance(node, DecLit):
        print(f"{prefix}Dec({node.value})")
    elif isinstance(node, StrLit):
        print(f"{prefix}Str({node.value!r})")
    elif isinstance(node, BoolLit):
        print(f"{prefix}Bool({node.value})")
    elif isinstance(node, NilLit):
        print(f"{prefix}nil")
    elif isinstance(node, Ident):
        print(f"{prefix}Ident({node.name})")
    elif isinstance(node, Binary):
        print(f"{prefix}Binary({node.op})")
        print_ast(node.left, indent + 1)
        print_ast(node.right, indent + 1)
    elif isinstance(node, Unary):
        print(f"{prefix}Unary({node.op})")
        print_ast(node.expr, indent + 1)
    elif isinstance(node, Call):
        print(f"{prefix}Call")
        print_ast(node.callee, indent + 1)
        for a in node.args:
            print_ast(a, indent + 1)
    elif isinstance(node, Group):
        print(f"{prefix}Group")
        print_ast(node.expr, indent + 1)
    else:
        print(f"{prefix}{type(node).__name__}")


def cmd_check(path: str):
    try:
        program = parse_source(read_file(path), path)
        from src.checker import check_program
        strict = "--strict" in sys.argv
        diags = check_program(program, strict=strict)
        errors = [d for d in diags if d.severity == "error"]
        warnings = [d for d in diags if d.severity == "warning"]
        for d in diags:
            print(d.format(path))
        if errors:
            print(f"check failed: {len(errors)} error(s), {len(warnings)} warning(s)")
            sys.exit(1)
        if warnings:
            print(f"OK with warnings: {path} ({len(warnings)} warning(s), {len(program.statements)} statements)")
        else:
            print(f"OK: {path} ({len(program.statements)} statements)")
    except SError as e:
        report_error(e)


def cmd_run(path: str):
    try:
        if str(path).endswith(".sbx"):
            cmd_run_sbx_or_s(path)
            return
        from src.modules import ModuleLoader
        from src.project_config import load_project_se
        root = str(Path(path).resolve().parent)
        loader = ModuleLoader(root_dir=root)
        program = parse_source(read_file(path), path)
        interp = Interpreter(module_loader=loader)
        cfg = load_project_se(root)
        if cfg.get("strict_let_collections"):
            interp.strict_let_collections = True
        interp.run(program)
    except SError as e:
        report_error(e)
    except ValueError as e:
        print(f"S Shield: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_repl():
    print("S Language REPL v1.0.0 Supreme — type 'exit' or Ctrl-D to quit")
    interp = Interpreter()
    while True:
        try:
            line = input("s> ")
        except EOFError:
            print()
            break
        if line.strip() in ("exit", "quit"):
            break
        if not line.strip():
            continue
        try:
            program = parse_source(line + "\n", "<repl>")
            result = interp.run(program)
            if result is not None:
                print(interp.stringify(result))
        except SError as e:
            print(f"error: {e}")


def cmd_test():
    """Run the built-in test suite."""
    test_dir = Path(__file__).parent.parent / "tests"
    if not test_dir.exists():
        print("No tests directory found.")
        return

    passed = 0
    failed = 0
    files = sorted(test_dir.glob("*.s")) + sorted(test_dir.glob("test_*.py"))

    # Also run the simple assertion tests defined below
    from src import test_runner
    results = test_runner.run_all()
    for name, ok, msg in results:
        if ok:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}: {msg}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


def cmd_doctor():
    """Basic toolchain health check."""
    print("S Language Doctor — 4.1.0")
    print("=" * 40)
    checks = []

    # Version
    ver_path = Path(__file__).parent.parent / "VERSION"
    ver = ver_path.read_text().strip() if ver_path.exists() else "unknown"
    checks.append(("Version", ver, True))

    # Core modules importable
    try:
        from src.lexer import Lexer
        from src.parser import parse_source
        from src.interpreter import Interpreter
        from src.modules import ModuleLoader
        checks.append(("Core modules", "OK", True))
    except Exception as e:
        checks.append(("Core modules", str(e), False))

    # Test suite
    try:
        from src import test_runner
        results = test_runner.run_all()
        passed = sum(1 for _, ok, _ in results if ok)
        total = len(results)
        ok = passed == total
        checks.append(("Test suite", f"{passed}/{total} passed", ok))
    except Exception as e:
        checks.append(("Test suite", str(e), False))

    # Examples exist
    ex_dir = Path(__file__).parent.parent / "examples"
    ex_count = len(list(ex_dir.glob("*.s"))) if ex_dir.exists() else 0
    checks.append(("Examples", f"{ex_count} files", ex_count > 0))
    try:
        from src.checker import OptChecker
        checks.append(("Opt checker (B1)", "OK", True))
    except Exception as e:
        checks.append(("Opt checker (B1)", str(e), False))
    try:
        from src.hub_lock import version_satisfies
        assert version_satisfies("1.0.0", ">=0.9.0")
        checks.append(("Hub versions (B4)", "OK", True))
    except Exception as e:
        checks.append(("Hub versions (B4)", str(e), False))
    lock = Path(__file__).parent.parent / "s.lock"
    if not lock.exists():
        lock = Path.cwd() / "s.lock"
    checks.append(("s.lock present", "yes" if lock.exists() else "no (optional)", True))
    try:
        from src.vm.compiler import Compiler
        from src.parser import parse_source as ps
        from src.vm.bytecode import VM
        VM(Compiler().compile(ps("let x = 1\n"))).run()
        checks.append(("SVM lambda path (B3)", "OK", True))
    except Exception as e:
        checks.append(("SVM (B3)", str(e)[:40], False))
    try:
        from src.sai_config import status
        st = status()
        checks.append(("SAI (C)", st["mode"], True))
    except Exception as e:
        checks.append(("SAI (C)", str(e)[:40], False))
    bench = Path(__file__).parent.parent / "benchmarks"
    n = len(list(bench.glob("*.s"))) if bench.exists() else 0
    checks.append(("Benchmarks (C)", f"{n} tasks", n > 0))
    try:
        from src.symbols import SymbolIndexer
        checks.append(("LSP symbols", "goto-def+rename", True))
    except Exception as e:
        checks.append(("LSP symbols", str(e)[:40], False))
    try:
        from src.shield import pack
        b = pack("print 1\n", "doctor-key")
        assert b[:4] in (b"SBX1", b"SBX2")
        checks.append(("Build/Shield (W2)", "SBX pack OK", True))
    except Exception as e:
        checks.append(("Build/Shield (W2)", str(e)[:40], False))
    import shutil as _shutil
    _nf = Path(__file__).resolve().parents[1] / "bin" / "s_fast"
    _ok = _nf.exists() or bool(_shutil.which("s_fast"))
    checks.append(("Native s_fast (Rust)", "present" if _ok else "optional missing", True))
    _gs = Path(__file__).resolve().parents[1] / "native" / "s_serve" / "s_serve"
    checks.append(("Native s_serve (Go)", "present" if _gs.exists() else "optional missing", True))

    for name, detail, ok in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status:4}] {name}: {detail}")

    all_ok = all(c[2] for c in checks)
    print("=" * 40)
    print("Healthy" if all_ok else "Issues found")
    if not all_ok:
        sys.exit(1)


def cmd_version():
    ver_path = Path(__file__).parent.parent / "VERSION"
    ver = ver_path.read_text().strip() if ver_path.exists() else "0.0.0"
    print(f"S Language {ver}")

def cmd_lib():
    """List built-in Slib / SDX / SAI modules."""
    slib = Path(__file__).parent / "slib"
    print("S Modules — Slib + SDX + SAI (4.1.0)")
    print("=" * 50)
    if not slib.exists():
        print("  (no slib directory)")
        return
    count = 0
    # top-level s.* modules
    for m in sorted(slib.glob("*.s")):
        name = m.stem
        display = f"s.{name}" if name != "listutil" else "s.list"
        text = m.read_text()
        fns = [line.strip() for line in text.splitlines() if line.strip().startswith("fn ")]
        print(f"  {display:20} ({len(fns)} functions)")
        count += 1
    # sdx / sai subdirs
    for sub in ("sdx", "sai"):
        subdir = slib / sub
        if subdir.exists():
            print(f"  --- {sub.upper()} ---")
            for m in sorted(subdir.glob("*.s")):
                display = f"{sub}.{m.stem}"
                text = m.read_text()
                fns = [line.strip() for line in text.splitlines() if line.strip().startswith("fn ")]
                print(f"  {display:20} ({len(fns)} functions)")
                count += 1
    print("=" * 50)
    print(f"{count} modules available")


def cmd_emit(path: str, backend: str = "kotlin"):
    try:
        program = parse_source(read_file(path), path)
        if backend == "kotlin":
            from src.emit_kotlin import KotlinEmitter
            code = KotlinEmitter().generate(program)
            print(code)
        else:
            print(f"Unknown backend: {backend}", file=sys.stderr)
            sys.exit(1)
    except SError as e:
        report_error(e)

def cmd_vm(path: str):
    """Compile to bytecode and run on SVM."""
    try:
        from src.vm.compiler import Compiler
        from src.vm.bytecode import VM
        from src.modules import ModuleLoader
        root = str(Path(path).resolve().parent)
        loader = ModuleLoader(root_dir=root)
        program = parse_source(read_file(path), path)
        chunk = Compiler(module_loader=loader, root_dir=root).compile(program)
        vm = VM(chunk)
        vm.run()
    except SError as e:
        report_error(e)
    except Exception as e:
        print(f"VM error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_hub(args: list):
    """S Hub — list / search / install / publish / lock (Phase B4)."""
    import json
    from src.hub_lock import (
        parse_pkg_spec, resolve_package, load_lock, save_lock, version_satisfies
    )
    hub_dir = Path(__file__).parent.parent / "hub"
    reg_path = hub_dir / "registry.json"
    lock_path = Path.cwd() / "s.lock"
    if not reg_path.exists():
        print("S Hub registry not found")
        return
    reg = json.loads(reg_path.read_text())
    packages = reg.get("packages", {})

    def show_list():
        print(f"S Hub — {reg.get('name')} (v{reg.get('version')})")
        print("=" * 50)
        for name, info in packages.items():
            vers = info.get("versions")
            if vers:
                vs = ", ".join(v["version"] for v in vers)
            else:
                vs = info.get("version", "?")
            print(f"  {name:16} [{vs}]  {info.get('description', '')}")
        print("=" * 50)
        if lock_path.exists():
            lock = load_lock(lock_path)
            print(f"s.lock: {len(lock.get('packages', {}))} locked package(s)")
        print("Usage: s hub [list|search <q>|install <name[@ver]>|publish <n> <f>|lock]")

    if not args or args[0] == "list":
        show_list()
        return

    if args[0] == "search" and len(args) >= 2:
        q = args[1].lower()
        print(f"Search: {q}")
        found = False
        for name, info in packages.items():
            blob = f"{name} {info.get('description','')} {' '.join(info.get('tags',[]))}".lower()
            if q in blob:
                vers = info.get("versions") or [{"version": info.get("version")}]
                vs = ", ".join(v.get("version", "?") for v in vers)
                print(f"  {name} [{vs}] — {info.get('description','')}")
                found = True
        if not found:
            print("  (no matches)")
        return

    if args[0] == "install" and len(args) >= 2:
        name, constraint = parse_pkg_spec(args[1])
        lock = load_lock(lock_path)
        # prefer lock if no explicit constraint
        if constraint is None and name in lock.get("packages", {}):
            constraint = lock["packages"][name]["version"]
            print(f"(from s.lock) {name}@{constraint}")
        try:
            resolved = resolve_package(reg, name, constraint)
        except KeyError as e:
            print(str(e))
            sys.exit(1)
        src = hub_dir / "packages" / resolved["entry"]
        if not src.exists():
            print(f"Package file missing: {src}")
            sys.exit(1)
        dest_dir = Path.cwd() / "s_modules"
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / f"{name}.s"
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        # update lock entry
        lock.setdefault("packages", {})[name] = {
            "version": resolved["version"],
            "entry": resolved["entry"],
        }
        lock["lock_version"] = 1
        save_lock(lock_path, lock)
        print(f"Installed {name} v{resolved['version']} → {dest}")
        print(f"Updated {lock_path.name}")
        return

    if args[0] == "lock":
        # freeze currently installed s_modules into s.lock using registry versions
        dest_dir = Path.cwd() / "s_modules"
        lock = {"lock_version": 1, "packages": {}}
        if dest_dir.exists():
            for f in dest_dir.glob("*.s"):
                name = f.stem
                if name in packages:
                    try:
                        resolved = resolve_package(reg, name, None)
                        lock["packages"][name] = {
                            "version": resolved["version"],
                            "entry": resolved["entry"],
                        }
                    except KeyError:
                        lock["packages"][name] = {"version": "0.0.0", "entry": f.name}
        save_lock(lock_path, lock)
        print(f"Wrote {lock_path} ({len(lock['packages'])} packages)")
        return

    if args[0] == "publish" and len(args) >= 3:
        name, path = args[1], args[2]
        if not Path(path).exists():
            print(f"File not found: {path}")
            sys.exit(1)
        dest = hub_dir / "packages" / f"{name}.s"
        dest.write_text(Path(path).read_text(encoding="utf-8"), encoding="utf-8")
        info = packages.get(name, {"description": f"Published {name}", "tags": ["local"], "versions": []})
        versions = info.get("versions") or []
        versions.append({"version": "0.1.0", "entry": f"{name}.s"})
        info["versions"] = versions
        packages[name] = info
        reg["packages"] = packages
        reg_path.write_text(json.dumps(reg, indent=2))
        print(f"Published {name} → hub/packages/{name}.s")
        return

    show_list()




def cmd_fmt(path: str):
    """Minimal formatter: trim trailing spaces, ensure newline at EOF."""
    try:
        text = read_file(path)
        lines = [ln.rstrip() for ln in text.splitlines()]
        out = "\n".join(lines) + "\n"
        Path(path).write_text(out, encoding="utf-8")
        print(f"Formatted {path}")
    except Exception as e:
        print(f"fmt error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_sai(args: list):
    from src.sai_config import status, help_text
    if not args or args[0] in ("status", "info"):
        st = status()
        print("SAI status")
        print(f"  mode:    {st['mode']}")
        print(f"  url:     {st['url']}")
        print(f"  model:   {st['model']}")
        print(f"  key_set: {st['key_set']}")
        return
    if args[0] == "help":
        print(help_text())
        return
    print("Usage: s sai [status|help]")


def cmd_sbridge(args: list):
    if not args or args[0] != "init":
        print("Usage: s sbridge init <dir> [AppName] [package]")
        return
    dest = args[1] if len(args) > 1 else "s-android-app"
    app = args[2] if len(args) > 2 else "SApp"
    pkg = args[3] if len(args) > 3 else "com.slang.app"
    from sbridge.init import init_project
    root = init_project(dest, app, pkg)
    print(f"SBridge scaffold → {root}")
    print("  assets/main.s + MainActivity.kt + project.se")


def cmd_bench():
    bdir = Path(__file__).parent.parent / "benchmarks"
    print("S Benchmarks (Phase C)")
    print("=" * 40)
    if not bdir.exists():
        print("No benchmarks/")
        return
    for f in sorted(bdir.glob("*.s")):
        lines = [ln for ln in f.read_text().splitlines() if ln.strip() and not ln.strip().startswith("//")]
        print(f"  {f.name:20} {len(lines)} LOC")
    results = bdir / "RESULTS.sd"
    if results.exists():
        print("-" * 40)
        print(results.read_text())

def cmd_symbols(path: str):
    """List definitions in a .s file (offline IDE helper)."""
    from src.symbols import SymbolIndexer
    program = parse_source(read_file(path), path)
    idx = SymbolIndexer().index(program)
    print(f"Symbols in {path}")
    print("=" * 40)
    for name, sym in sorted(idx.defs.items(), key=lambda x: x[1].line):
        print(f"  {sym.kind:8} {name:20} line {sym.line}")
    print("=" * 40)
    print(f"{len(idx.defs)} definitions, {len(idx.refs)} references")


def cmd_rename(path: str, old: str, new: str):
    """Rename symbol across file (offline)."""
    from src.symbols import SymbolIndexer, rename_in_text
    text = read_file(path)
    program = parse_source(text, path)
    idx = SymbolIndexer().index(program)
    if old not in idx.defs:
        print(f"Symbol not defined: {old}")
        sys.exit(1)
    out = rename_in_text(text, old, new, idx)
    Path(path).write_text(out, encoding="utf-8")
    print(f"Renamed {old} → {new} in {path}")

def cmd_new(args: list):
    """Create a complete runnable S project."""
    from src.new_project import create
    if not args:
        print("Usage: s new <name> [parent_dir]")
        print("Example: s new myapp")
        sys.exit(1)
    name = args[0]
    dest = args[1] if len(args) > 1 else "."
    root = create(name, dest)
    print()
    print("  S project ready — Simple · Safe · Supreme")
    print(f"  → {root.resolve()}")
    print()
    print("  Files (S symbols):")
    print("    main.s       your program")
    print("    project.se   project identity")
    print("    README.sd    design notes")
    print()
    print("  Next:")
    print(f"    python3 s run {root}/main.s")
    print(f"    python3 s check {root}/main.s")
    print()


def cmd_protect(args: list):
    """Encrypt .s or project folder → .sbx (S Shield)."""
    from src.shield import pack_file, pack_project, _strip_source
    if len(args) < 1:
        print("Usage: s protect <file.s|project_dir> [out.sbx] [--key=secret]")
        print("  Default key: env S_SHIELD_KEY or 's-dev-key'")
        sys.exit(1)
    src = Path(args[0])
    if not src.exists():
        print(f"Not found: {src}")
        sys.exit(1)
    key = os.environ.get("S_SHIELD_KEY", "s-dev-key")
    for a in args:
        if a.startswith("--key="):
            key = a[6:]
    out_arg = [a for a in args[1:] if not a.startswith("--")]
    if src.is_dir():
        out = Path(out_arg[0]) if out_arg else Path(src.name + ".sbx")
        # entry from project.se
        entry = "main.s"
        se = src / "project.se"
        if se.exists():
            for line in se.read_text().splitlines():
                if line.strip().startswith("entry:"):
                    entry = line.split(":", 1)[1].strip()
        blob = pack_project(src, key, entry=entry)
        out.write_bytes(blob)
        print(f"S Shield project packed → {out}")
        print(f"  entry: {entry}")
        print("  Release: ship only .sbx (no .s folder)")
    else:
        out = Path(out_arg[0]) if out_arg else src.with_suffix(".sbx")
        pack_file(src, out, key, meta={"source": src.name})
        _, mapping = _strip_source(src.read_text(encoding="utf-8"))
        map_path = out.with_suffix(".sbx.map")
        map_path.write_text(
            json.dumps({"mapping": mapping, "note": "DEVELOPER ONLY — do not ship"}, indent=2),
            encoding="utf-8",
        )
        print(f"S Shield packed → {out}")
        print(f"Developer map  → {map_path} (keep private)")
    print("Tip: S_SHIELD_KEY=... python3 s run app.sbx")


def cmd_unbox(args: list):
    """Decrypt .sbx for developer recovery (needs key)."""
    from src.shield import unpack_file
    if len(args) < 1:
        print("Usage: s unbox <file.sbx> [--key=secret]")
        sys.exit(1)
    key = os.environ.get("S_SHIELD_KEY", "s-dev-key")
    for a in args:
        if a.startswith("--key="):
            key = a[6:]
    data = unpack_file(Path(args[0]), key)
    print(data.get("src", ""))


def cmd_run_sbx_or_s(path: str):
    """Run .sbx — single file or full project pack."""
    p = Path(path)
    from src.shield import unpack_file
    key = os.environ.get("S_SHIELD_KEY", "s-dev-key")
    data = unpack_file(p, key)
    from src.modules import ModuleLoader
    root = str(p.resolve().parent)
    loader = ModuleLoader(root_dir=root)
    interp = Interpreter(module_loader=loader)

    if data.get("kind") == "project" or "files" in data:
        files = data["files"]
        meta = data.get("meta") or {}
        entry = meta.get("entry", "main.s")
        if entry not in files:
            # try first file
            entry = next(iter(files.keys()))
        # materialize virtual sources for module loader via temp dir
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="s_sbx_"))
        try:
            for rel, info in files.items():
                dest = tmp / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(info["src"] if isinstance(info, dict) else info, encoding="utf-8")
            if meta.get("project_se"):
                (tmp / "project.se").write_text(meta["project_se"], encoding="utf-8")
            loader = ModuleLoader(root_dir=str(tmp))
            interp = Interpreter(module_loader=loader)
            entry_src = (tmp / entry).read_text(encoding="utf-8")
            program = parse_source(entry_src, entry)
            interp.run(program)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        return True

    src = data.get("src")
    if not src:
        raise ValueError("SBX has no source")
    program = parse_source(src, str(p))
    interp.run(program)
    return True

def cmd_seal_append(args: list):
    """Add a .s file into existing .sbx project pack (join only, with key)."""
    from src.shield import seal_append
    if len(args) < 2:
        print("Usage: s seal-append <pack.sbx> <file.s> [as_name.s] [--key=]")
        sys.exit(1)
    pack_path = Path(args[0])
    src_path = Path(args[1])
    as_name = args[2] if len(args) > 2 and not args[2].startswith("--") else src_path.name
    key = os.environ.get("S_SHIELD_KEY", "s-dev-key")
    for a in args:
        if a.startswith("--key="):
            key = a[6:]
    blob = pack_path.read_bytes()
    new_blob = seal_append(blob, key, as_name, src_path.read_text(encoding="utf-8"))
    pack_path.write_bytes(new_blob)
    print(f"Joined {as_name} into {pack_path} (sealed pack updated)")

def cmd_build(args: list):
    """Professional release: project → dist/*.sbx"""
    from src.shield import pack_project, pack_file
    root = Path(args[0]) if args else Path(".")
    if not root.exists():
        print(f"Not found: {root}")
        sys.exit(1)
    key = os.environ.get("S_SHIELD_KEY", "s-dev-key")
    for a in args:
        if a.startswith("--key="):
            key = a[6:]
    dist = (root / "dist") if root.is_dir() else (root.parent / "dist")
    dist.mkdir(exist_ok=True)
    if root.is_dir():
        entry = "main.s"
        se = root / "project.se"
        if se.exists():
            for line in se.read_text().splitlines():
                if line.strip().startswith("entry:"):
                    entry = line.split(":", 1)[1].strip()
        out = dist / (root.name + ".sbx")
        out.write_bytes(pack_project(root, key, entry=entry))
        print(f"Build OK → {out}")
        (dist / "run.sh").write_text(
            "#!/bin/sh\n"
            "export S_SHIELD_KEY=\"${S_SHIELD_KEY:-s-dev-key}\"\n"
            f"exec python3 s run {out.resolve()}\n",
            encoding="utf-8",
        )
    else:
        out = dist / (root.stem + ".sbx")
        pack_file(root, out, key)
        print(f"Build OK → {out}")
    print("Run: S_SHIELD_KEY=... python3 s run", out)



def cmd_release(args: list):
    """Week 4 gate: check → test → build (fail closed)."""
    target = Path(args[0]) if args else Path(".")
    key = os.environ.get("S_SHIELD_KEY", "s-dev-key")
    for a in args:
        if a.startswith("--key="):
            key = a[6:]
    print("=== S RELEASE GATE ===")
    # 1 tests
    print("[1/3] tests...")
    cmd_test()
    # 2 check entry if project
    entry = target / "main.s" if target.is_dir() else target
    if entry.exists() and str(entry).endswith(".s"):
        print("[2/3] check...", entry)
        try:
            program = parse_source(read_file(str(entry)), str(entry))
            from src.checker import check_program
            diags = check_program(program)
            errs = [d for d in diags if d.severity == "error"]
            for d in diags:
                print(" ", d.format(str(entry)))
            if errs:
                print("RELEASE FAILED: check errors")
                sys.exit(1)
        except SError as e:
            report_error(e)
            sys.exit(1)
    else:
        print("[2/3] check skipped (no main.s)")
    # 3 build
    print("[3/3] build...")
    cmd_build(([str(target)] if target.is_dir() or target.suffix == ".s" else []) + [f"--key={key}"])
    print("=== RELEASE OK ===")

def cmd_log(args: list):
    """Show local S event log (monitoring)."""
    from src.monitor import log_path
    p = log_path()
    if not p.exists():
        print("No events yet:", p)
        return
    lines = p.read_text(encoding="utf-8").strip().splitlines()[-50:]
    for ln in lines:
        print(ln)

def cmd_html(args: list):
    """W-WEB-1: build static HTML from a .s generator script.
    Usage: s html build <generator.s> [--out=dir]
    The .s script should print HTML (or write_file). We also capture print output to index.html if out set.
    """
    if not args or args[0] != "build" or len(args) < 2:
        print("Usage: s html build <site.s> [--out=dir]")
        sys.exit(1)
    src = Path(args[1])
    out_dir = Path("site_out")
    for a in args[2:]:
        if a.startswith("--out="):
            out_dir = Path(a[6:])
    if not src.exists():
        print(f"Not found: {src}")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Run and capture stdout prints by intercepting — simple: exec and expect write_file in script
    # Also support scripts that only print one page → index.html
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    try:
        from src.modules import ModuleLoader
        root = str(src.resolve().parent)
        loader = ModuleLoader(root_dir=root)
        program = parse_source(read_file(str(src)), str(src))
        interp = Interpreter(module_loader=loader)
        with redirect_stdout(buf):
            interp.run(program)
    except SError as e:
        report_error(e)
        sys.exit(1)
    text = buf.getvalue()
    if text.strip():
        index = out_dir / "index.html"
        index.write_text(text, encoding="utf-8")
        print(f"Wrote {index}")
    print(f"HTML build done → {out_dir.resolve()}")

def cmd_serve(args: list):
    """Serve static + API. Use --go for native Go server."""
    root = "examples/static_site/out"
    host = "127.0.0.1"
    port = 8080
    use_go = False
    for a in args:
        if a.startswith("--port="):
            port = int(a[7:])
        elif a.startswith("--host="):
            host = a[7:]
        elif a in ("--go", "-g"):
            use_go = True
        elif not a.startswith("--"):
            root = a
    if use_go:
        import shutil, subprocess
        from pathlib import Path
        cand = [
            Path(__file__).resolve().parents[1] / "native" / "s_serve" / "s_serve",
            Path("/tmp/s_serve"),
            Path(shutil.which("s_serve") or ""),
        ]
        binary = next((str(c) for c in cand if c and c.exists()), None)
        if not binary:
            print("Go s_serve binary not found. Build: cd native/s_serve && go build -o s_serve .")
            sys.exit(1)
        addr = f"{host}:{port}"
        print(f"Starting Go serve: {binary} -root {root} -addr {addr}")
        os.execv(binary, [binary, "-root", root, "-addr", addr])
    from src.serve import run_server
    run_server(root, host, port)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "new":
        cmd_new(sys.argv[2:])
        return
    if cmd == "repl":
        cmd_repl()
        return
    if cmd == "test":
        cmd_test()
        return
    if cmd == "doctor":
        cmd_doctor()
        return
    if cmd == "version":
        cmd_version()
        return
    if cmd == "lib":
        cmd_lib()
        return
    if cmd == "emit":
        if len(sys.argv) < 4:
            print("Usage: s emit kotlin <file.s>")
            sys.exit(1)
        cmd_emit(sys.argv[3], backend=sys.argv[2])
        return
    if cmd == "vm":
        if len(sys.argv) < 3:
            print("Usage: s vm <file.s>")
            sys.exit(1)
        cmd_vm(sys.argv[2])
        return
    if cmd == "hub":
        cmd_hub(sys.argv[2:])
        return
    if cmd == "fmt":
        if len(sys.argv) < 3:
            print("Usage: s fmt <file.s>")
            sys.exit(1)
        cmd_fmt(sys.argv[2])
        return
    if cmd == "sai":
        cmd_sai(sys.argv[2:])
        return
    if cmd == "sbridge":
        cmd_sbridge(sys.argv[2:])
        return
    if cmd == "bench":
        cmd_bench()
        return
    if cmd == "symbols":
        if len(sys.argv) < 3:
            print("Usage: s symbols <file.s>")
            sys.exit(1)
        cmd_symbols(sys.argv[2])
        return
    if cmd == "rename":
        if len(sys.argv) < 5:
            print("Usage: s rename <file.s> <old> <new>")
            sys.exit(1)
        cmd_rename(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    if cmd == "protect":
        cmd_protect(sys.argv[2:])
        return
    if cmd == "unbox":
        cmd_unbox(sys.argv[2:])
        return
    if cmd == "seal-append":
        cmd_seal_append(sys.argv[2:])
        return
    if cmd == "build":
        cmd_build(sys.argv[2:])
        return
    if cmd == "release":
        cmd_release(sys.argv[2:])
        return
    if cmd == "log":
        cmd_log(sys.argv[2:])
        return
    if cmd == "html":
        cmd_html(sys.argv[2:])
        return
    if cmd == "serve":
        cmd_serve(sys.argv[2:])
        return

    if len(sys.argv) < 3:
        print(f"Usage: s {cmd} <file.s>")
        sys.exit(1)

    path = sys.argv[2]
    if not os.path.exists(path):
        print(f"error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    if cmd == "run":
        cmd_run(path)
    elif cmd == "check":
        cmd_check(path)
    elif cmd == "tokens":
        cmd_tokens(path)
    elif cmd == "ast":
        cmd_ast(path)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
