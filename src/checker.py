"""S static checker for basic type and safety diagnostics.

The checker intentionally supports the types and syntax represented by the
current parser. Unknown/dynamic values remain permissive so module imports,
reflection-like member access, and existing gradual-typing programs keep
working while known mismatches are caught before execution.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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


@dataclass
class FunctionSig:
    name: str
    params: List[Tuple[str, str, object]]
    return_type: str
    is_async: bool = False

    @property
    def min_args(self) -> int:
        # Positional arguments still have to reach the last required parameter.
        return max((i + 1 for i, (_, _, default) in enumerate(self.params) if default is None), default=0)


@dataclass
class Symbol:
    type_name: str = "any"
    mutable: bool = False
    signature: Optional[FunctionSig] = None
    kind: str = "value"


class OptChecker:
    """Scope-aware checker for the current S AST (kept under its legacy name)."""

    BUILTINS = {
        "print", "len", "map", "filter", "each", "some", "none", "valueOr",
        "ok", "err", "isOk", "isErr", "isSome", "unwrap", "freeze", "type",
        "input", "sort", "unique", "reverse", "push", "pop", "split", "join",
        "upper", "lower", "trim", "replace", "contains", "sum", "any", "all",
        "json_parse", "json_stringify", "http_get", "http_post", "read_file",
        "write_file", "sleep", "range_of", "env_get", "path_join", "regex_match",
        "csv_split", "date_fmt", "exit", "starts_with", "ends_with", "clock", "now",
        "hash", "min", "max", "abs", "pad", "require", "keys", "values",
        "floor", "ceil", "round", "clamp", "take", "drop", "find", "zip",
        "html_escape", "html_tag", "html_page", "true", "false", "nil",
        "__sai_ask", "__sai_generate",
    }
    NUMERIC = {"int", "dec"}
    BUILTIN_RETURNS = {
        "len": "int", "floor": "int", "ceil": "int", "abs": "int",
        "isOk": "bool", "isErr": "bool", "isSome": "bool", "any": "bool",
        "all": "bool", "contains": "bool", "json_stringify": "str",
        "html_escape": "str", "html_tag": "str", "html_page": "str",
        "upper": "str", "lower": "str", "trim": "str",
        "replace": "str", "split": "list", "read_file": "str", "write_file": "str",
        "path_join": "str", "env_get": "str", "regex_match": "list",
        "csv_split": "list", "date_fmt": "str", "clock": "dec", "now": "dec",
        "hash": "str", "input": "str", "keys": "list", "values": "list",
        "range_of": "list", "reverse": "list", "sort": "list", "unique": "list",
        "map": "list", "filter": "list", "push": "list", "join": "str",
        "json_parse": "any", "http_get": "str", "http_post": "str",
        "sleep": "nil", "exit": "nil", "print": "nil", "each": "nil",
        "require": "nil", "some": "opt", "none": "opt", "ok": "result",
        "err": "result", "unwrap": "any", "valueOr": "any", "sum": "any",
        "min": "any", "max": "any", "pop": "any", "freeze": "list",
        "type": "str", "pad": "str", "__sai_ask": "str", "__sai_generate": "str",
    }

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.diags: List[Diagnostic] = []
        self.scopes: List[Dict[str, Symbol]] = [{}]
        self.class_methods: Dict[str, Dict[str, FunctionSig]] = {}
        self.class_names = set()
        self.return_types: List[str] = []
        self.loop_depth = 0
        self.function_depth = 0
        self.future_globals = set()
        self.permissive_names = False

    def check(self, program: Program) -> List[Diagnostic]:
        self.diags = []
        self.scopes = [{}]
        self.class_methods = {}
        self.class_names = set()
        self.return_types = []
        self.loop_depth = 0
        self.function_depth = 0
        self.future_globals = {s.name for s in program.statements if isinstance(s, LetDecl)}
        # Unaliased imports inject unknown names into the current runtime scope;
        # without loading modules here, strict name resolution must defer them.
        self.permissive_names = any(isinstance(s, UseDecl) and not s.alias for s in program.statements)

        # Register top-level nominal types and function signatures first so
        # recursion and calls to later declarations get checked consistently.
        for stmt in program.statements:
            if isinstance(stmt, ClassDecl):
                self.class_names.add(stmt.name)
                methods = {m.name: self._signature(m) for m in stmt.methods}
                self.class_methods[stmt.name] = methods
                self._define(stmt.name, Symbol(stmt.name, kind="class"))
            elif isinstance(stmt, EnumDecl):
                self._define(stmt.name, Symbol(stmt.name, kind="enum"))
            elif isinstance(stmt, FnDecl):
                sig = self._signature(stmt)
                self._define(stmt.name, Symbol("fn", signature=sig, kind="function"))

        for stmt in program.statements:
            self.stmt(stmt)
        return self.diags

    def error(self, message: str, node=None):
        self.diags.append(Diagnostic("error", message, getattr(node, "span", None)))

    def warn(self, message: str, node=None):
        self.diags.append(Diagnostic("warning", message, getattr(node, "span", None)))

    def _signature(self, fn: FnDecl) -> FunctionSig:
        params = []
        for param in fn.params:
            if isinstance(param, (tuple, list)):
                name = param[0]
                type_name = param[1] if len(param) > 1 and param[1] else "any"
                default = param[2] if len(param) > 2 else None
            else:
                name = getattr(param, "name", str(param))
                type_name = getattr(param, "type_name", "any") or "any"
                default = getattr(param, "default", None)
            params.append((name, self._normalize(type_name), default))
        return FunctionSig(fn.name, params, self._normalize(fn.return_type or "any"), getattr(fn, "is_async", False))

    @staticmethod
    def _normalize(type_name: Optional[str]) -> str:
        if not type_name:
            return "any"
        aliases = {"string": "str", "float": "dec", "double": "dec", "void": "nil", "unit": "nil"}
        return aliases.get(type_name, type_name)

    def _define(self, name: str, symbol: Symbol):
        self.scopes[-1][name] = symbol

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _push_scope(self):
        self.scopes.append({})

    def _pop_scope(self):
        self.scopes.pop()

    def _compatible(self, actual: str, expected: str) -> bool:
        actual, expected = self._normalize(actual), self._normalize(expected)
        if actual in ("any", "unknown") or expected in ("any", "unknown"):
            return True
        if actual == expected:
            return True
        # Integer values can be widened to decimals without changing meaning.
        if actual == "int" and expected == "dec":
            return True
        if actual == "nil" and expected in ("opt", "result"):
            return True
        return False

    def _expect_type(self, actual: str, expected: str, node, context: str):
        if not self._compatible(actual, expected):
            self.error(f"Type mismatch in {context}: expected {expected}, got {actual}", node)

    def _join_types(self, left: str, right: str) -> str:
        if left == right:
            return left
        if self._compatible(left, right):
            return right
        if self._compatible(right, left):
            return left
        if left in self.NUMERIC and right in self.NUMERIC:
            return "dec"
        return "any"

    def _predeclare_functions(self, statements):
        for stmt in statements:
            if isinstance(stmt, FnDecl) and stmt.name not in self.scopes[-1]:
                self._define(stmt.name, Symbol("fn", signature=self._signature(stmt), kind="function"))

    def _check_block(self, block: Block, *, new_scope: bool = True):
        if block is None:
            return
        if new_scope:
            self._push_scope()
        try:
            self._predeclare_functions(block.stmts)
            for statement in block.stmts:
                self.stmt(statement)
        finally:
            if new_scope:
                self._pop_scope()

    def _check_block_value(self, block: Block) -> str:
        """Check an expression-valued block once and return its final type."""
        if block is None:
            return "nil"
        self._push_scope()
        result_type = "nil"
        try:
            self._predeclare_functions(block.stmts)
            for statement in block.stmts:
                if isinstance(statement, ExprStmt):
                    result_type = self.expr(statement.expr)
                else:
                    self.stmt(statement)
                    result_type = "nil"
        finally:
            self._pop_scope()
        return result_type

    def _check_function(self, fn: FnDecl, class_name: Optional[str] = None):
        signature = self._signature(fn)
        self._push_scope()
        old_loop_depth = self.loop_depth
        self.loop_depth = 0
        self.function_depth += 1
        self.return_types.append(signature.return_type)
        try:
            if class_name:
                self._define("this", Symbol(class_name, kind="value"))
            for name, type_name, default in signature.params:
                if default is not None:
                    default_type = self.expr(default)
                    self._expect_type(default_type, type_name, default, f"default value for parameter '{name}'")
                self._define(name, Symbol(type_name, mutable=False))
            self._check_block(fn.body)
        finally:
            self.return_types.pop()
            self.function_depth -= 1
            self.loop_depth = old_loop_depth
            self._pop_scope()

    def _check_call_args(self, signature: FunctionSig, arg_types: List[str], node):
        if len(arg_types) < signature.min_args:
            self.error(
                f"Function '{signature.name}' expects at least {signature.min_args} argument(s), got {len(arg_types)}",
                node,
            )
        if len(arg_types) > len(signature.params):
            self.error(
                f"Function '{signature.name}' expects at most {len(signature.params)} argument(s), got {len(arg_types)}",
                node,
            )
        for index, actual in enumerate(arg_types[:len(signature.params)]):
            pname, expected, _ = signature.params[index]
            self._expect_type(actual, expected, node, f"argument '{pname}' of {signature.name}()")

    def _check_builtin_arity(self, name: str, count: int, node):
        exact = {"len": 1, "upper": 1, "lower": 1, "trim": 1, "type": 1,
                 "isOk": 1, "isErr": 1, "isSome": 1, "unwrap": 1, "freeze": 1,
                 "pop": 1, "sort": 1, "unique": 1, "reverse": 1, "sum": 1,
                 "any": 1, "all": 1, "contains": 2, "replace": 3,
                 "push": 2, "valueOr": 2, "map": 2, "filter": 2, "each": 2,
                 "range_of": 2, "starts_with": 2, "ends_with": 2}
        if name in exact and count != exact[name]:
            self.error(f"Built-in '{name}' expects {exact[name]} argument(s), got {count}", node)
        elif name in ("some", "ok", "err") and count > 1:
            self.error(f"Built-in '{name}' expects at most 1 argument(s), got {count}", node)
        elif name == "none" and count != 0:
            self.error(f"Built-in 'none' expects 0 argument(s), got {count}", node)

    def stmt(self, statement):
        if isinstance(statement, LetDecl):
            value_type = self.expr(statement.value)
            annotation = self._normalize(statement.type_ann)
            if statement.type_ann:
                self._expect_type(value_type, annotation, statement, f"initializer for '{statement.name}'")
                stored_type = annotation
            else:
                stored_type = value_type
            self._define(statement.name, Symbol(stored_type, mutable=statement.mutable))
            return

        if isinstance(statement, Assign):
            value_type = self.expr(statement.value)
            symbol = self._lookup(statement.name)
            if symbol is None:
                # Unqualified names can come from `use` modules; leave name
                # resolution to the runtime/module loader for now.
                if self.strict and not self.permissive_names:
                    known_later_in_function = self.function_depth > 0 and statement.name in self.future_globals
                    if not known_later_in_function:
                        self.error(f"Undefined variable '{statement.name}'", statement)
                return
            if symbol.kind == "function" or not symbol.mutable:
                self.error(f"Cannot assign to immutable name '{statement.name}'", statement)
                return
            self._expect_type(value_type, symbol.type_name, statement, f"assignment to '{statement.name}'")
            return

        if isinstance(statement, PrintStmt):
            for arg in statement.args:
                self.expr(arg)
        elif isinstance(statement, ExprStmt):
            self.expr(statement.expr)
        elif isinstance(statement, Block):
            self._check_block(statement)
        elif isinstance(statement, IfStmt):
            self.expr(statement.condition)  # conditions use S truthiness semantics
            self._check_block(statement.then_branch)
            if isinstance(statement.else_branch, Block):
                self._check_block(statement.else_branch)
            elif statement.else_branch:
                self.stmt(statement.else_branch)
        elif isinstance(statement, WhileStmt):
            self.expr(statement.condition)
            self.loop_depth += 1
            try:
                self._check_block(statement.body)
            finally:
                self.loop_depth -= 1
        elif isinstance(statement, (LoopStmt, RepeatStmt)):
            if isinstance(statement, RepeatStmt):
                self._expect_type(self.expr(statement.count), "int", statement.count, "repeat count")
            self.loop_depth += 1
            try:
                self._check_block(statement.body)
            finally:
                self.loop_depth -= 1
        elif isinstance(statement, ForStmt):
            iterable_type = self.expr(statement.iterable)
            if iterable_type not in ("any", "unknown", "list", "range"):
                self.error(f"Cannot iterate over value of type {iterable_type}; expected list or range", statement.iterable)
            self.loop_depth += 1
            self._push_scope()
            self._define(statement.var, Symbol("int" if iterable_type == "range" else "any", mutable=False))
            try:
                self._check_block(statement.body)
            finally:
                self._pop_scope()
                self.loop_depth -= 1
        elif isinstance(statement, BreakStmt):
            if self.loop_depth == 0:
                self.error("break outside of loop", statement)
        elif isinstance(statement, NextStmt):
            if self.loop_depth == 0:
                self.error("next outside of loop", statement)
        elif isinstance(statement, RetStmt):
            if not self.return_types:
                self.error("return outside of function", statement)
                if statement.value is not None:
                    self.expr(statement.value)
                return
            actual = self.expr(statement.value) if statement.value is not None else "nil"
            self._expect_type(actual, self.return_types[-1], statement, "return value")
        elif isinstance(statement, FnDecl):
            self._check_function(statement)
        elif isinstance(statement, UseDecl):
            module_name = statement.alias or (statement.path[-1] if statement.path else "")
            if module_name:
                self._define(module_name, Symbol("module", kind="module"))
        elif isinstance(statement, AssertStmt):
            self.expr(statement.condition)
            if statement.message is not None:
                self.expr(statement.message)
        elif isinstance(statement, ClassDecl):
            for method in statement.methods:
                self._check_function(method, class_name=statement.name)
        elif isinstance(statement, SafeStmt):
            self._check_block(statement.body)
            self._push_scope()
            self._define(statement.rescue_name, Symbol("str", mutable=False))
            try:
                self._check_block(statement.rescue_body)
            finally:
                self._pop_scope()
        elif isinstance(statement, SetMember):
            self.expr(statement.object)
            self.expr(statement.value)
        elif isinstance(statement, IndexAssign):
            obj_type = self.expr(statement.object)
            index_type = self.expr(statement.index)
            self.expr(statement.value)
            if obj_type == "list":
                self._expect_type(index_type, "int", statement.index, "list index")
            elif obj_type == "map":
                self._expect_type(index_type, "str", statement.index, "map key")
            elif obj_type not in ("any", "unknown"):
                self.error(f"Cannot assign through index on type {obj_type}", statement)
        elif isinstance(statement, EnumDecl):
            self._define(statement.name, Symbol(statement.name, kind="enum"))
        elif isinstance(statement, GuardStmt):
            self.expr(statement.condition)
        elif isinstance(statement, DeferStmt):
            if isinstance(statement.body, Block):
                self._check_block(statement.body)
            elif statement.body is not None:
                self.stmt(statement.body)
        elif isinstance(statement, SpawnStmt):
            self.expr(statement.expr)

    def expr(self, expression) -> str:
        if expression is None:
            return "nil"
        if isinstance(expression, IntLit):
            return "int"
        if isinstance(expression, DecLit):
            return "dec"
        if isinstance(expression, StrLit):
            return "str"
        if isinstance(expression, BoolLit):
            return "bool"
        if isinstance(expression, NilLit):
            return "nil"
        if isinstance(expression, Ident):
            symbol = self._lookup(expression.name)
            if symbol is not None:
                return symbol.type_name
            known_later_in_function = self.function_depth > 0 and expression.name in self.future_globals
            if self.strict and not self.permissive_names and expression.name not in self.BUILTINS and not known_later_in_function:
                self.error(f"Unknown name '{expression.name}'", expression)
            return "any"
        if isinstance(expression, Group):
            return self.expr(expression.expr)
        if isinstance(expression, Range):
            self._expect_type(self.expr(expression.start), "int", expression.start, "range start")
            self._expect_type(self.expr(expression.end), "int", expression.end, "range end")
            return "range"
        if isinstance(expression, ListLit):
            for item in expression.elements:
                self.expr(item)
            return "list"
        if isinstance(expression, MapLit):
            for key, value in expression.entries:
                key_type = self.expr(key)
                self._expect_type(key_type, "str", key, "map key")
                self.expr(value)
            return "map"
        if isinstance(expression, Index):
            object_type = self.expr(expression.object)
            index_type = self.expr(expression.index)
            if object_type == "list":
                self._expect_type(index_type, "int", expression.index, "list index")
                return "any"
            if object_type == "map":
                self._expect_type(index_type, "str", expression.index, "map key")
                return "any"
            if object_type == "str":
                self._expect_type(index_type, "int", expression.index, "string index")
                return "str"
            if object_type not in ("any", "unknown"):
                self.error(f"Cannot index value of type {object_type}", expression)
            return "any"
        if isinstance(expression, NewExpr):
            init = self.class_methods.get(expression.class_name, {}).get("init")
            argument_types = [self.expr(arg) for arg in expression.args]
            if init is not None:
                self._check_call_args(init, argument_types, expression)
            elif expression.args and expression.class_name in self.class_names:
                self.error(f"Class '{expression.class_name}' has no init method but got {len(expression.args)} argument(s)", expression)
            elif expression.class_name not in self.class_names and self.strict and not self.permissive_names:
                self.error(f"Unknown class '{expression.class_name}'", expression)
            return expression.class_name if expression.class_name in self.class_names else "any"
        if isinstance(expression, ThisLit):
            symbol = self._lookup("this")
            if symbol is None:
                if self.strict:
                    self.error("'this' used outside of a method", expression)
                return "any"
            return symbol.type_name
        if isinstance(expression, Member):
            object_type = self.expr(expression.object)
            if object_type in self.class_methods and expression.name in self.class_methods[object_type]:
                return "fn"
            return "any"
        if isinstance(expression, SafeNav):
            self.expr(expression.object)
            return "opt"
        if isinstance(expression, InterpStr):
            for part in expression.parts:
                if not isinstance(part, str):
                    self.expr(part)
            return "str"
        if isinstance(expression, Unary):
            operand = self.expr(expression.expr)
            if expression.op == "-":
                self._expect_numeric(operand, expression, "unary '-'")
                return operand if operand in self.NUMERIC else "any"
            if expression.op == "not":
                return "bool"
            return "any"
        if isinstance(expression, Binary):
            left = self.expr(expression.left)
            right = self.expr(expression.right)
            return self._binary_type(expression.op, left, right, expression)
        if isinstance(expression, Call):
            arg_types = [self.expr(arg) for arg in expression.args]
            signature = self._callee_signature(expression.callee)
            if signature is not None:
                self._check_call_args(signature, arg_types, expression)
                result_type = signature.return_type
                return f"future[{result_type}]" if signature.is_async else result_type
            if isinstance(expression.callee, Ident):
                name = expression.callee.name
                if name in self.BUILTINS:
                    self._check_builtin_arity(name, len(arg_types), expression)
                    if name == "len" and arg_types:
                        arg_type = arg_types[0]
                        if arg_type not in ("str", "list", "map", "range", "any", "unknown"):
                            self.error(f"len() does not accept values of type {arg_type}", expression)
                    if name in ("upper", "lower", "trim") and arg_types:
                        self._expect_type(arg_types[0], "str", expression.args[0], f"argument of {name}()")
                    if name == "replace" and len(arg_types) == 3:
                        for arg_type, arg_node in zip(arg_types, expression.args):
                            self._expect_type(arg_type, "str", arg_node, "argument of replace()")
                    if name == "push" and arg_types:
                        self._expect_type(arg_types[0], "list", expression.args[0], "first argument of push()")
                    if name == "valueOr" and len(arg_types) == 2:
                        return arg_types[1]
                    if name == "unwrap" and expression.args:
                        arg_type = arg_types[0]
                        if arg_type in ("opt", "result") and isinstance(expression.args[0], Ident):
                            self.warn(f"unwrap('{expression.args[0].name}') may fail; guard it or use valueOr()", expression)
                        if isinstance(expression.args[0], Call) and isinstance(expression.args[0].callee, Ident) and expression.args[0].callee.name in ("none", "err"):
                            self.error("unwrap(none/err) is always unsafe", expression)
                    return self.BUILTIN_RETURNS.get(name, "any")
                if self.strict and not self.permissive_names and self._lookup(name) is None:
                    self.error(f"Unknown function '{name}'", expression)
            return "any"
        if isinstance(expression, Pipe):
            left_type = self.expr(expression.left)
            if isinstance(expression.right, Call):
                arg_nodes = [expression.left] + expression.right.args
                arg_types = [left_type] + [self.expr(arg) for arg in expression.right.args]
                signature = self._callee_signature(expression.right.callee)
                if signature is not None:
                    self._check_call_args(signature, arg_types, expression)
                    return signature.return_type
                return "any"
            if isinstance(expression.right, Ident):
                signature = self._callee_signature(expression.right)
                if signature is not None:
                    self._check_call_args(signature, [left_type], expression)
                    return signature.return_type
                return "any"
            if isinstance(expression.right, Lambda):
                self.expr(expression.right)
            else:
                self.expr(expression.right)
            return "any"
        if isinstance(expression, Coalesce):
            left = self.expr(expression.left)
            right = self.expr(expression.right)
            if left in ("opt", "nil"):
                return right
            return self._join_types(left, right)
        if isinstance(expression, Ternary):
            self.expr(expression.cond)
            return self._join_types(self.expr(expression.then_expr), self.expr(expression.else_expr))
        if isinstance(expression, AwaitExpr):
            value_type = self.expr(expression.expr)
            if value_type.startswith("future[") and value_type.endswith("]"):
                return value_type[7:-1]
            return value_type
        if isinstance(expression, Lambda):
            self._push_scope()
            try:
                for name in expression.params:
                    self._define(name, Symbol("any", mutable=False))
                if isinstance(expression.body, Block):
                    self._check_block(expression.body)
                else:
                    self.expr(expression.body)
            finally:
                self._pop_scope()
            return "fn"
        if isinstance(expression, WhenExpr):
            if expression.subject is not None:
                self.expr(expression.subject)
            branch_types = []
            for branch in expression.branches:
                if not branch.is_else:
                    self.expr(branch.pattern)
                if isinstance(branch.body, Block):
                    branch_types.append(self._check_block_value(branch.body))
                else:
                    branch_types.append(self.expr(branch.body))
            if not branch_types:
                return "nil"
            result = branch_types[0]
            for branch_type in branch_types[1:]:
                result = self._join_types(result, branch_type)
            return result
        return "any"

    def _callee_signature(self, callee) -> Optional[FunctionSig]:
        if isinstance(callee, Ident):
            symbol = self._lookup(callee.name)
            return symbol.signature if symbol is not None else None
        if isinstance(callee, Member):
            object_type = self.expr(callee.object)
            return self.class_methods.get(object_type, {}).get(callee.name)
        return None

    def _expect_numeric(self, type_name: str, node, context: str):
        if type_name not in self.NUMERIC and type_name not in ("any", "unknown"):
            self.error(f"Type mismatch in {context}: expected a number, got {type_name}", node)

    def _binary_type(self, op: str, left: str, right: str, node) -> str:
        if op in ("==", "!="):
            return "bool"
        if op in ("<", ">", "<=", ">="):
            self._expect_numeric(left, node, f"operator '{op}'")
            self._expect_numeric(right, node, f"operator '{op}'")
            return "bool"
        if op in ("-", "*", "/", "%"):
            self._expect_numeric(left, node, f"operator '{op}'")
            self._expect_numeric(right, node, f"operator '{op}'")
            if left not in self.NUMERIC or right not in self.NUMERIC:
                return "any"
            return "dec" if op == "/" or "dec" in (left, right) else "int"
        if op == "+":
            if left == "str" or right == "str":
                # S deliberately stringifies either side for concatenation.
                return "str"
            if left == right == "list":
                return "list"
            if left in self.NUMERIC and right in self.NUMERIC:
                return "dec" if "dec" in (left, right) else "int"
            if left in ("any", "unknown") or right in ("any", "unknown"):
                return "any"
            self.error(f"Operator '+' is not defined for {left} and {right}", node)
            return "any"
        if op == "in":
            if right not in ("list", "map", "str", "range", "any", "unknown"):
                self.error(f"Right operand of 'in' must be a list, map, string, or range, got {right}", node)
            return "bool"
        if op in ("and", "or"):
            return self._join_types(left, right)
        return "any"

    # Compatibility helpers used by a few existing integrations/tests.
    def _is_opt_expr(self, expression) -> bool:
        return self.expr(expression) == "opt"

    def _is_result_expr(self, expression) -> bool:
        return self.expr(expression) == "result"


def check_program(program: Program, strict: bool = False) -> List[Diagnostic]:
    return OptChecker(strict=strict).check(program)
