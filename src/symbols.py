"""Symbol table for LSP: definitions + references (Phase C offline)."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from .ast import *


@dataclass
class Symbol:
    name: str
    kind: str  # fn, var, class, enum, param
    line: int
    col: int
    end_line: int = 0
    end_col: int = 0


@dataclass
class Ref:
    name: str
    line: int
    col: int


def _span_pos(span) -> tuple:
    if span is None:
        return 1, 1
    line = getattr(span, "line", None) or getattr(span, "start_line", 1) or 1
    col = getattr(span, "col", None) or getattr(span, "start_col", 1) or 1
    return int(line), int(col)


class SymbolIndexer:
    def __init__(self):
        self.defs: Dict[str, Symbol] = {}
        self.refs: List[Ref] = []
        self._scope_stack: List[set] = [set()]

    def index(self, program: Program):
        self.defs.clear()
        self.refs.clear()
        self._scope_stack = [set()]
        for s in program.statements:
            self._stmt(s)
        return self

    def _define(self, name: str, kind: str, span):
        line, col = _span_pos(span)
        self.defs[name] = Symbol(name=name, kind=kind, line=line, col=col)
        self._scope_stack[-1].add(name)

    def _ref(self, name: str, span):
        line, col = _span_pos(span)
        self.refs.append(Ref(name=name, line=line, col=col))

    def _stmt(self, s):
        if isinstance(s, LetDecl):
            self._expr(s.value)
            self._define(s.name, "var", s.span)
        elif isinstance(s, Assign):
            self._ref(s.name, s.span)
            self._expr(s.value)
        elif isinstance(s, FnDecl):
            self._define(s.name, "fn", s.span)
            self._scope_stack.append(set())
            for p in s.params:
                pname = p[0] if isinstance(p, (tuple, list)) else p
                self._define(pname, "param", s.span)
            for st in s.body.stmts:
                self._stmt(st)
            self._scope_stack.pop()
        elif isinstance(s, ClassDecl):
            self._define(s.name, "class", s.span)
            for m in s.methods:
                self._stmt(m)
        elif isinstance(s, EnumDecl):
            self._define(s.name, "enum", s.span)
        elif isinstance(s, PrintStmt):
            for a in s.args:
                self._expr(a)
        elif isinstance(s, ExprStmt):
            self._expr(s.expr)
        elif isinstance(s, Block):
            for st in s.stmts:
                self._stmt(st)
        elif isinstance(s, IfStmt):
            self._expr(s.condition)
            self._stmt(s.then_branch)
            if s.else_branch:
                self._stmt(s.else_branch)
        elif isinstance(s, RetStmt) and s.value:
            self._expr(s.value)
        elif isinstance(s, ForStmt):
            self._expr(s.iterable)
            self._define(s.var, "var", s.span)
            self._stmt(s.body)
        elif isinstance(s, LoopStmt):
            self._stmt(s.body)
        elif isinstance(s, RepeatStmt):
            self._expr(s.count)
            self._stmt(s.body)
        elif isinstance(s, GuardStmt):
            self._expr(s.condition)
        elif isinstance(s, SafeStmt):
            self._stmt(s.body)
            self._stmt(s.rescue_body)
        elif isinstance(s, AssertStmt):
            self._expr(s.condition)

    def _expr(self, e):
        if e is None:
            return
        if isinstance(e, Ident):
            self._ref(e.name, e.span)
        elif isinstance(e, Call):
            self._expr(e.callee)
            for a in e.args:
                self._expr(a)
        elif isinstance(e, Binary):
            self._expr(e.left)
            self._expr(e.right)
        elif isinstance(e, Unary):
            self._expr(e.expr)
        elif isinstance(e, Group):
            self._expr(e.expr)
        elif isinstance(e, Index):
            self._expr(e.object)
            self._expr(e.index)
        elif isinstance(e, Member):
            self._expr(e.object)
        elif isinstance(e, SafeNav):
            self._expr(e.object)
        elif isinstance(e, Pipe):
            self._expr(e.left)
            self._expr(e.right)
        elif isinstance(e, Coalesce):
            self._expr(e.left)
            self._expr(e.right)
        elif isinstance(e, Ternary):
            self._expr(e.cond)
            self._expr(e.then_expr)
            self._expr(e.else_expr)
        elif isinstance(e, Lambda):
            self._expr(e.body)
        elif isinstance(e, ListLit):
            for x in e.elements:
                self._expr(x)
        elif isinstance(e, NewExpr):
            self._ref(e.class_name, e.span)
            for a in e.args:
                self._expr(a)


def rename_in_text(text: str, old: str, new: str, indexer: SymbolIndexer) -> str:
    """Rename identifier occurrences that match symbol refs/defs (word-boundary)."""
    import re
    # Only rename if defined
    if old not in indexer.defs:
        return text
    pattern = re.compile(r"\b" + re.escape(old) + r"\b")
    return pattern.sub(new, text)
