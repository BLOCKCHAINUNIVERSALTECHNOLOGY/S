"""S Static Checker — Phase B1 opt / safety rules (V1.9)

Not a full type system — focused rules that catch real mistakes early.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set
from .ast import *


@dataclass
class Diagnostic:
    severity: str  # "error" | "warning" | "info"
    message: str
    span: Optional[object] = None

    def format(self, filename: str = "<check>") -> str:
        loc = ""
        if self.span is not None and hasattr(self.span, "line"):
            loc = f"{filename}:{self.span.line}:{self.span.col}: "
        elif self.span is not None and hasattr(self.span, "start_line"):
            loc = f"{filename}:{self.span.start_line}:{getattr(self.span, 'start_col', 1)}: "
        return f"{loc}{self.severity}: {self.message}"


class OptChecker:
    """Walk AST and emit diagnostics."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.diags: List[Diagnostic] = []
        self.opt_names: Set[str] = set()
        self.result_names: Set[str] = set()
        self.defined: Set[str] = set()
        self.types: dict = {}  # name -> "int"|"str"|"bool"|"dec"|"list"|"map"|"opt"|"unknown"
        self.builtins = {
            "print", "len", "map", "filter", "each", "some", "none", "valueOr",
            "ok", "err", "isOk", "isErr", "unwrap", "freeze", "type", "input",
            "sort", "unique", "reverse", "push", "pop", "split", "join",
            "upper", "lower", "trim", "replace", "contains", "sum", "any", "all",
            "json_parse", "json_stringify", "http_get", "http_post",
            "read_file", "write_file", "sleep", "range_of",
            "true", "false", "nil",
        }

    def check(self, program: Program) -> List[Diagnostic]:
        self.diags = []
        self.opt_names = set()
        self.result_names = set()
        for stmt in program.statements:
            self.stmt(stmt)
        return self.diags

    def error(self, msg, span=None):
        self.diags.append(Diagnostic("error", msg, span))

    def warn(self, msg, span=None):
        self.diags.append(Diagnostic("warning", msg, span))

    def stmt(self, s):
        if isinstance(s, LetDecl):
            self.expr(s.value)
            self.defined.add(s.name)
            if self._is_opt_expr(s.value):
                self.opt_names.add(s.name)
            if self._is_result_expr(s.value):
                self.result_names.add(s.name)
            # Light static: annotation vs literal
            ann = getattr(s, "type_ann", None)
            inferred = self._infer(s.value)
            if isinstance(ann, str) and ann:
                self.types[s.name] = ann
                from .ast import IntLit, StrLit, BoolLit
                v = s.value
                if ann == "int" and isinstance(v, StrLit):
                    self.error(f"Type: '{s.name}' annotated int but string literal given", getattr(s, "span", None))
                elif ann == "str" and isinstance(v, IntLit):
                    self.error(f"Type: '{s.name}' annotated str but number literal given", getattr(s, "span", None))
                elif ann == "bool" and isinstance(v, (IntLit, StrLit)):
                    self.error(f"Type: '{s.name}' annotated bool but non-bool literal", getattr(s, "span", None))
                elif self.strict and inferred and inferred != "unknown" and ann != inferred and not (
                    ann in ("dec", "int") and inferred in ("dec", "int")
                ):
                    self.error(f"Type: '{s.name}' annotated {ann} but value is {inferred}", getattr(s, "span", None))
            else:
                self.types[s.name] = inferred or "unknown"
        elif isinstance(s, Assign):
            self.expr(s.value)
            self.defined.add(s.name)
            if self._is_opt_expr(s.value):
                self.opt_names.add(s.name)
            else:
                self.opt_names.discard(s.name)
            if self._is_result_expr(s.value):
                self.result_names.add(s.name)
            else:
                self.result_names.discard(s.name)
        elif isinstance(s, PrintStmt):
            for a in s.args:
                self.expr(a)
        elif isinstance(s, ExprStmt):
            self.expr(s.expr)
        elif isinstance(s, Block):
            for x in s.stmts:
                self.stmt(x)
        elif isinstance(s, IfStmt):
            self.expr(s.condition)
            self.stmt(s.then_branch)
            if s.else_branch:
                self.stmt(s.else_branch)
        elif isinstance(s, FnDecl):
            self.defined.add(s.name)
            saved_o, saved_r, saved_d = set(self.opt_names), set(self.result_names), set(self.defined)
            for p in s.params:
                pname = p[0] if isinstance(p, (tuple, list)) else getattr(p, "name", p)
                self.defined.add(pname)
            for st in s.body.stmts:
                self.stmt(st)
            self.opt_names, self.result_names, self.defined = saved_o, saved_r, saved_d
        elif isinstance(s, RetStmt):
            if s.value:
                self.expr(s.value)
        elif isinstance(s, GuardStmt):
            self.expr(s.condition)
        elif isinstance(s, LoopStmt) or isinstance(s, RepeatStmt):
            body = s.body if hasattr(s, "body") else None
            if body:
                self.stmt(body)
        elif isinstance(s, ForStmt):
            self.expr(s.iterable)
            self.stmt(s.body)
        elif isinstance(s, SafeStmt):
            self.stmt(s.body)
            self.stmt(s.rescue_body)
        elif isinstance(s, ClassDecl):
            self.defined.add(s.name)
            for m in s.methods:
                self.stmt(m)
        elif isinstance(s, AssertStmt):
            self.expr(s.condition)
        # others ignored

    def expr(self, e):
        if e is None:
            return
        if isinstance(e, Call):
            self._check_call(e)
            self.expr(e.callee)
            for a in e.args:
                self.expr(a)
        elif isinstance(e, Binary):
            self._check_binary(e)
            self.expr(e.left)
            self.expr(e.right)
        elif isinstance(e, Unary):
            self.expr(e.expr)
        elif isinstance(e, Group):
            self.expr(e.expr)
        elif isinstance(e, Index):
            self.expr(e.object)
            self.expr(e.index)
        elif isinstance(e, Slice):
            self.expr(e.object)
        elif isinstance(e, Member) or isinstance(e, SafeNav):
            self.expr(e.object)
        elif isinstance(e, Pipe):
            self.expr(e.left)
            self.expr(e.right)
        elif isinstance(e, Coalesce):
            self.expr(e.left)
            self.expr(e.right)
        elif isinstance(e, Ternary):
            self.expr(e.cond)
            self.expr(e.then_expr)
            self.expr(e.else_expr)
        elif isinstance(e, Ident):
            if (
                e.name not in self.defined
                and e.name not in self.builtins
                and not e.name.startswith("S_")
            ):
                # warning only (modules / use can define later)
                pass  # modules/use define later; opt rules remain primary
        elif isinstance(e, Lambda):
            if hasattr(e, "body"):
                self.expr(e.body)
        elif isinstance(e, ListLit):
            for el in e.elements:
                self.expr(el)
        elif isinstance(e, MapLit):
            for k, v in e.entries:
                self.expr(k)
                self.expr(v)
        elif isinstance(e, WhenExpr):
            if e.subject:
                self.expr(e.subject)

    def _is_opt_expr(self, e) -> bool:
        if isinstance(e, Call) and isinstance(e.callee, Ident):
            return e.callee.name in ("some", "none")
        if isinstance(e, Ident) and e.name in self.opt_names:
            return True
        if isinstance(e, SafeNav):
            return True
        if isinstance(e, Coalesce):
            return False  # coalesce yields value
        return False

    def _is_result_expr(self, e) -> bool:
        if isinstance(e, Call) and isinstance(e.callee, Ident):
            return e.callee.name in ("ok", "err")
        if isinstance(e, Ident) and e.name in self.result_names:
            return True
        return False

    def _check_call(self, e: Call):
        if not isinstance(e.callee, Ident):
            return
        name = e.callee.name
        # unwrap without isOk / isSome nearby — heuristic on arg
        if name == "unwrap" and e.args:
            arg = e.args[0]
            if isinstance(arg, Ident) and arg.name in self.result_names:
                self.warn(
                    f"unwrap('{arg.name}') without visible isOk() check — prefer guard isOk({arg.name})",
                    getattr(e, "span", None),
                )
            if isinstance(arg, Ident) and arg.name in self.opt_names:
                self.warn(
                    f"unwrap on opt-like '{arg.name}' — use valueOr() or isSome()",
                    getattr(e, "span", None),
                )
            if isinstance(arg, Call) and isinstance(arg.callee, Ident) and arg.callee.name in ("none", "err"):
                self.error("unwrap(none/err) is always unsafe", getattr(e, "span", None))
        if name in ("+",) and False:
            pass

    def _check_binary(self, e: Binary):
        if e.op in ("+", "-", "*", "/", "%", "<", ">", "<=", ">="):
            for side, label in ((e.left, "left"), (e.right, "right")):
                if isinstance(side, Ident) and side.name in self.opt_names:
                    self.error(
                        f"Arithmetic/compare with opt value '{side.name}' — use valueOr({side.name}, default) or unwrap after isSome",
                        getattr(e, "span", None),
                    )
                if isinstance(side, Call) and isinstance(side.callee, Ident) and side.callee.name in ("some", "none"):
                    self.error(
                        f"Arithmetic/compare with raw opt call — unwrap or valueOr first",
                        getattr(e, "span", None),
                    )
                if isinstance(side, Ident) and side.name in self.result_names:
                    self.error(
                        f"Arithmetic with result '{side.name}' — use unwrap() after isOk()",
                        getattr(e, "span", None),
                    )


    def _infer(self, e) -> str:
        from .ast import IntLit, StrLit, BoolLit, DecLit, ListLit, MapLit, Binary, Ident, Call
        if isinstance(e, IntLit):
            return "int"
        if isinstance(e, DecLit):
            return "dec"
        if isinstance(e, StrLit):
            return "str"
        if isinstance(e, BoolLit):
            return "bool"
        if isinstance(e, ListLit):
            return "list"
        if isinstance(e, MapLit):
            return "map"
        if isinstance(e, Ident):
            return self.types.get(e.name, "unknown")
        if isinstance(e, Binary) and e.op in ("+", "-", "*", "/", "%"):
            lt, rt = self._infer(e.left), self._infer(e.right)
            if self.strict and lt == "str" and e.op != "+":
                self.error(f"Type: cannot use '{e.op}' on str", getattr(e, "span", None))
            if lt == "str" or rt == "str":
                return "str"
            if lt in ("dec", "int") and rt in ("dec", "int"):
                return "dec" if "dec" in (lt, rt) else "int"
        if isinstance(e, Call) and isinstance(e.callee, Ident):
            n = e.callee.name
            if n in ("len", "floor", "ceil", "abs"):
                return "int"
            if n in ("json_stringify", "html_escape", "upper", "lower", "trim"):
                return "str"
        return "unknown"


def check_program(program: Program, strict: bool = False) -> List[Diagnostic]:
    return OptChecker(strict=strict).check(program)
