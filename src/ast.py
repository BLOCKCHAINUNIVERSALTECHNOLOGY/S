"""S Language AST nodes — M1 vertical slice"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union


@dataclass
class SourceSpan:
    file: str
    start: int
    end: int
    line: int
    col: int

    def __str__(self):
        return f"{self.file}:{self.line}:{self.col}"


# ── Expressions ──────────────────────────────────────────────

@dataclass
class IntLit:
    value: int
    span: Optional[SourceSpan] = None

@dataclass
class DecLit:
    value: float
    span: Optional[SourceSpan] = None

@dataclass
class StrLit:
    value: str
    span: Optional[SourceSpan] = None

@dataclass
class BoolLit:
    value: bool
    span: Optional[SourceSpan] = None

@dataclass
class NilLit:
    span: Optional[SourceSpan] = None

@dataclass
class Ident:
    name: str
    span: Optional[SourceSpan] = None

@dataclass
class Binary:
    op: str
    left: "Expr"
    right: "Expr"
    span: Optional[SourceSpan] = None

@dataclass
class Unary:
    op: str
    expr: "Expr"
    span: Optional[SourceSpan] = None

@dataclass
class Call:
    callee: "Expr"
    args: List["Expr"]
    span: Optional[SourceSpan] = None

@dataclass
class Group:
    expr: "Expr"
    span: Optional[SourceSpan] = None

@dataclass
class Range:
    start: "Expr"
    end: "Expr"
    span: Optional[SourceSpan] = None

@dataclass
class ListLit:
    elements: List["Expr"]
    span: Optional[SourceSpan] = None

@dataclass
class MapLit:
    entries: List[tuple]          # list of (key_expr, value_expr)
    span: Optional[SourceSpan] = None

@dataclass
class Index:
    object: "Expr"
    index: "Expr"
    span: Optional[SourceSpan] = None


@dataclass
class NewExpr:
    class_name: str
    args: List["Expr"]
    span: Optional[SourceSpan] = None

@dataclass
class Member:
    object: "Expr"
    name: str
    span: Optional[SourceSpan] = None

@dataclass
class ThisLit:
    span: Optional[SourceSpan] = None

@dataclass
class IndexAssign:
    object: "Expr"
    index: "Expr"
    value: "Expr"
    span: Optional[SourceSpan] = None

@dataclass
class SetMember:
    object: "Expr"
    name: str
    value: "Expr"
    span: Optional[SourceSpan] = None


@dataclass
class WhenBranch:
    pattern: object  # Expr or special "else"
    body: object     # Expr or Block
    is_else: bool = False

@dataclass
class WhenExpr:
    subject: object  # Expr or None for when without subject
    branches: list
    span: Optional[SourceSpan] = None

@dataclass
class EnumDecl:
    name: str
    variants: list  # list of str
    span: Optional[SourceSpan] = None

@dataclass
class InterpStr:
    parts: list  # alternating str and Expr
    span: Optional[SourceSpan] = None


@dataclass
class Lambda:
    params: list  # list of names (str)
    body: object  # Expr or Block
    span: Optional[SourceSpan] = None

@dataclass
class Pipe:
    left: object
    right: object  # usually Call or Ident
    span: Optional[SourceSpan] = None

@dataclass
class Coalesce:
    left: object
    right: object
    span: Optional[SourceSpan] = None

@dataclass
class DeferStmt:
    body: object  # statement or block
    span: Optional[SourceSpan] = None


@dataclass
class AwaitExpr:
    expr: object
    span: Optional[SourceSpan] = None

@dataclass
class SpawnStmt:
    expr: object
    span: Optional[SourceSpan] = None


@dataclass
class Slice:
    object: "Expr"
    start: Optional[object]  # Expr or None
    end: Optional[object]
    span: Optional[SourceSpan] = None

@dataclass
class Ternary:
    cond: object
    then_expr: object
    else_expr: object
    span: Optional[SourceSpan] = None

@dataclass
class GuardStmt:
    condition: object
    span: Optional[SourceSpan] = None

@dataclass
class RepeatStmt:
    count: object  # Expr
    body: object   # Block
    span: Optional[SourceSpan] = None


@dataclass
class SafeNav:
    object: object
    name: str
    span: Optional[SourceSpan] = None

Expr = Union[IntLit, DecLit, StrLit, BoolLit, NilLit, Ident, Binary, Unary, Call, Group, Range, ListLit, MapLit, Index, NewExpr, Member, ThisLit, WhenExpr, InterpStr, Lambda, Pipe, Coalesce, AwaitExpr, Slice, Ternary, SafeNav]


# ── Statements ───────────────────────────────────────────────

@dataclass
class LetDecl:
    name: str
    type_ann: Optional[str]
    value: Expr
    mutable: bool = False          # False = let, True = var
    span: Optional[SourceSpan] = None

@dataclass
class Assign:
    name: str
    value: Expr
    span: Optional[SourceSpan] = None

@dataclass
class ExprStmt:
    expr: Expr
    span: Optional[SourceSpan] = None

@dataclass
class PrintStmt:
    args: List[Expr]
    span: Optional[SourceSpan] = None

@dataclass
class Block:
    stmts: List["Stmt"]
    span: Optional[SourceSpan] = None

@dataclass
class IfStmt:
    condition: Expr
    then_branch: Block
    else_branch: Optional[Union[Block, "IfStmt"]] = None
    span: Optional[SourceSpan] = None

@dataclass
class WhileStmt:
    condition: object
    body: object
    span: Optional[SourceSpan] = None

@dataclass
class LoopStmt:
    body: Block
    span: Optional[SourceSpan] = None

@dataclass
class ForStmt:
    var: str
    iterable: Expr
    body: Block
    span: Optional[SourceSpan] = None

@dataclass
class BreakStmt:
    span: Optional[SourceSpan] = None

@dataclass
class NextStmt:
    span: Optional[SourceSpan] = None

@dataclass
class RetStmt:
    value: Optional[Expr] = None
    span: Optional[SourceSpan] = None

@dataclass
class FnDecl:
    name: str
    params: List[tuple]            # list of (name, type)
    return_type: str
    body: Block
    is_async: bool = False
    span: Optional[SourceSpan] = None

@dataclass
class UseDecl:
    path: List[str]                # e.g. ["math"] or ["utils", "helper"]
    alias: Optional[str] = None    # use math as m
    span: Optional[SourceSpan] = None

@dataclass
class AssertStmt:
    condition: "Expr"
    message: Optional["Expr"] = None
    span: Optional[SourceSpan] = None

@dataclass
class ClassDecl:
    name: str
    methods: List[FnDecl]
    span: Optional[SourceSpan] = None

@dataclass
class SafeStmt:
    body: Block
    rescue_name: str
    rescue_body: Block
    span: Optional[SourceSpan] = None






Stmt = Union[
    LetDecl, Assign, ExprStmt, PrintStmt, Block,
    IfStmt, LoopStmt, ForStmt, BreakStmt, NextStmt, RetStmt, FnDecl, UseDecl, AssertStmt,
    ClassDecl, SafeStmt, SetMember, EnumDecl, DeferStmt, SpawnStmt, IndexAssign, RepeatStmt, GuardStmt, WhileStmt
]


@dataclass
class Program:
    statements: List[Stmt] = field(default_factory=list)
    span: Optional[SourceSpan] = None
