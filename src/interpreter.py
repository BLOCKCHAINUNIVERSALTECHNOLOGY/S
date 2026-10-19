"""S Language Tree-walk Interpreter — M2"""

import sys
from typing import Any, Dict, List, Optional
from .ast import *
from .errors import RuntimeError_ as RuntimeError


class ReturnValue(Exception):
    """Used for returning from functions"""
    def __init__(self, value):
        self.value = value


class GuardSignal(Exception):
    pass

class BreakSignal(Exception):
    pass


class NextSignal(Exception):
    pass


class Environment:
    def __init__(self, parent: "Environment" = None):
        self.parent = parent
        self.values: Dict[str, Any] = {}
        self.mutables: Dict[str, bool] = {}

    def define(self, name: str, value: Any, mutable: bool = False):
        self.values[name] = value
        self.mutables[name] = mutable

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        # Collect known names for friendly hint
        known = set()
        env = self
        while env:
            known.update(env.values.keys())
            env = env.parent
        hint = ""
        if known:
            import difflib
            close = difflib.get_close_matches(name, list(known), n=1, cutoff=0.6)
            if close:
                hint = f" (did you mean '{close[0]}'?)"
        raise RuntimeError(f"Unknown name '{name}'{hint}. Define it with let/var/fn first.")

    def assign(self, name: str, value: Any):
        if name in self.values:
            if not self.mutables.get(name, False):
                raise RuntimeError(f"Cannot assign to immutable variable '{name}'")
            self.values[name] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        raise RuntimeError(f"Undefined variable '{name}'")


class Function:
    def __init__(self, decl: FnDecl, closure: Environment, bound_this=None):
        self.decl = decl
        self.closure = closure
        self.bound_this = bound_this  # for methods
        self.is_async = getattr(decl, "is_async", False)

    def __repr__(self):
        return f"<{'async ' if self.is_async else ''}fn {self.decl.name}>"


class Future:
    def __init__(self, fn, args, interpreter, node):
        self.fn = fn
        self.args = args
        self.interpreter = interpreter
        self.node = node
        self._result = None
        self._done = False

    def result(self):
        if not self._done:
            self._result = self.interpreter.call_function(self.fn, self.args, self.node)
            self._done = True
        return self._result

    def __repr__(self):
        return "<future>"


class Class:
    def __init__(self, name: str, methods: dict):
        self.name = name
        self.methods = methods  # name -> FnDecl

    def __repr__(self):
        return f"<class {self.name}>"


class Instance:
    def __init__(self, klass: Class):
        self.klass = klass
        self.fields = {}

    def get(self, name: str):
        if name in self.fields:
            return self.fields[name]
        if name in self.klass.methods:
            # bind this
            return Function(self.klass.methods[name], None, bound_this=self)
        raise RuntimeError(f"Undefined property '{name}' on {self.klass.name}")

    def set(self, name: str, value):
        self.fields[name] = value

    def __repr__(self):
        return f"<{self.klass.name} instance>"


class Interpreter:
    MAX_RECURSION = 200

    def __init__(self, module_loader=None):
        self.global_env = Environment()
        self.env = self.global_env
        self.call_depth = 0
        self.loop_depth = 0
        self.module_loader = module_loader
        self._imported: set = set()
        self._defer_stack = [[]]  # stack of frames of deferred stmts
        self.strict_let_collections = False
        # Allow deeper S recursion than default Python limit
        if sys.getrecursionlimit() < 3000:
            sys.setrecursionlimit(3000)

    def run(self, program: Program) -> Any:
        result = None
        self._defer_stack = [[]]
        try:
            for stmt in program.statements:
                result = self.exec(stmt)
        finally:
            if hasattr(self, "_spawn_queue"):
                for fut in self._spawn_queue:
                    try:
                        fut.result()
                    except Exception as e:
                        print(f"[spawn error] {e}")
                self._spawn_queue = []
            self._run_defers()
        return result

    def _run_defers(self):
        while self._defer_stack and self._defer_stack[-1]:
            body = self._defer_stack[-1].pop()
            try:
                self.exec(body)
            except Exception:
                pass

    # ── Statements ───────────────────────────────────────────

    def exec(self, stmt: Stmt) -> Any:
        if isinstance(stmt, LetDecl):
            value = self.eval(stmt.value)
            if (
                getattr(self, "strict_let_collections", False)
                and not stmt.mutable
                and isinstance(value, list)
            ):
                value = ("__frozen__", list(value))
            self.env.define(stmt.name, value, mutable=stmt.mutable)
            return None

        if isinstance(stmt, Assign):
            value = self.eval(stmt.value)
            self.env.assign(stmt.name, value)
            return None

        if isinstance(stmt, PrintStmt):
            values = [self.eval(a) for a in stmt.args]
            print(*[self.stringify(v) for v in values])
            return None

        if isinstance(stmt, ExprStmt):
            return self.eval(stmt.expr)

        if isinstance(stmt, Block):
            return self.exec_block(stmt.stmts, Environment(self.env))

        if isinstance(stmt, IfStmt):
            cond = self.eval(stmt.condition)
            if self.is_truthy(cond):
                return self.exec(stmt.then_branch)
            elif stmt.else_branch:
                return self.exec(stmt.else_branch)
            return None

        if isinstance(stmt, WhileStmt):
            self.loop_depth += 1
            try:
                while self.is_truthy(self.eval(stmt.condition)):
                    try:
                        self.exec(stmt.body)
                    except BreakSignal:
                        break
                    except NextSignal:
                        continue
            finally:
                self.loop_depth -= 1
            return None

        if isinstance(stmt, LoopStmt):
            self.loop_depth += 1
            try:
                while True:
                    try:
                        self.exec(stmt.body)
                    except BreakSignal:
                        break
                    except NextSignal:
                        continue
            finally:
                self.loop_depth -= 1
            return None

        if isinstance(stmt, ForStmt):
            iterable = self.eval(stmt.iterable)
            if isinstance(iterable, tuple) and iterable[0] == "__frozen__":
                iterable = iterable[1]
            if not isinstance(iterable, (list, range)):
                raise RuntimeError(f"Cannot iterate over {type(iterable).__name__}", stmt)

            items = list(iterable) if not isinstance(iterable, list) else iterable

            self.loop_depth += 1
            try:
                for item in items:
                    loop_env = Environment(self.env)
                    loop_env.define(stmt.var, item, mutable=False)
                    prev = self.env
                    self.env = loop_env
                    try:
                        self.exec(stmt.body)
                    except BreakSignal:
                        self.env = prev
                        break
                    except NextSignal:
                        self.env = prev
                        continue
                    finally:
                        self.env = prev
            finally:
                self.loop_depth -= 1
            return None

        if isinstance(stmt, BreakStmt):
            if self.loop_depth == 0:
                raise RuntimeError("break outside of loop", stmt)
            raise BreakSignal()

        if isinstance(stmt, NextStmt):
            if self.loop_depth == 0:
                raise RuntimeError("next outside of loop", stmt)
            raise NextSignal()

        if isinstance(stmt, RetStmt):
            value = self.eval(stmt.value) if stmt.value else None
            raise ReturnValue(value)

        if isinstance(stmt, FnDecl):
            fn = Function(stmt, self.env)
            self.env.define(stmt.name, fn, mutable=False)
            return None

        if isinstance(stmt, UseDecl):
            return self.exec_use(stmt)

        if isinstance(stmt, AssertStmt):
            cond = self.eval(stmt.condition)
            if not self.is_truthy(cond):
                msg = "Assertion failed"
                if stmt.message:
                    msg = self.stringify(self.eval(stmt.message))
                raise RuntimeError(msg, stmt)
            return None

        if isinstance(stmt, ClassDecl):
            methods = {m.name: m for m in stmt.methods}
            klass = Class(stmt.name, methods)
            self.env.define(stmt.name, klass, mutable=False)
            return None

        if isinstance(stmt, SafeStmt):
            try:
                return self.exec(stmt.body)
            except RuntimeError as e:
                rescue_env = Environment(self.env)
                rescue_env.define(stmt.rescue_name, e.message, mutable=False)
                prev = self.env
                self.env = rescue_env
                try:
                    return self.exec(stmt.rescue_body)
                finally:
                    self.env = prev

        if isinstance(stmt, SetMember):
            obj = self.eval(stmt.object)
            val = self.eval(stmt.value)
            if isinstance(obj, Instance):
                obj.set(stmt.name, val)
                return None
            raise RuntimeError(f"Cannot set member on {type(obj).__name__}", stmt)

        if isinstance(stmt, GuardStmt):
            if not self.is_truthy(self.eval(stmt.condition)):
                raise GuardSignal()
            return None

        if isinstance(stmt, RepeatStmt):
            n = self.eval(stmt.count)
            if not isinstance(n, int) or n < 0:
                raise RuntimeError("repeat count must be non-negative int", stmt)
            self.loop_depth += 1
            try:
                for _ in range(n):
                    try:
                        self.exec(stmt.body)
                    except BreakSignal:
                        break
                    except NextSignal:
                        continue
            finally:
                self.loop_depth -= 1
            return None

        if isinstance(stmt, SpawnStmt):
            # Cooperative spawn: queue futures, run after current flow
            val = self.eval(stmt.expr)
            if not hasattr(self, "_spawn_queue"):
                self._spawn_queue = []
            if isinstance(val, Future):
                self._spawn_queue.append(val)
            return None

        if isinstance(stmt, IndexAssign):
            obj = self.eval(stmt.object)
            idx = self.eval(stmt.index)
            val = self.eval(stmt.value)
            if isinstance(obj, tuple) and len(obj) == 2 and obj[0] == "__frozen__":
                raise RuntimeError("Cannot modify frozen list", stmt)
            if isinstance(obj, list):
                if not isinstance(idx, int) or idx < 0 or idx >= len(obj):
                    raise RuntimeError(f"List index out of bounds: {idx}", stmt)
                obj[idx] = val
                return None
            if isinstance(obj, dict):
                obj[idx] = val
                return None
            raise RuntimeError(f"Cannot index-assign on {type(obj).__name__}", stmt)

        if isinstance(stmt, DeferStmt):
            self._defer_stack[-1].append(stmt.body)
            return None

        if isinstance(stmt, EnumDecl):
            # Create a simple namespace object with variants as string constants
            class EnumNS:
                def __init__(self, name, variants):
                    self._name = name
                    for v in variants:
                        setattr(self, v, f"{name}.{v}")
                def __repr__(self):
                    return f"<enum {self._name}>"
            ns = EnumNS(stmt.name, stmt.variants)
            self.env.define(stmt.name, ns, mutable=False)
            return None

        raise RuntimeError(f"Unknown statement type: {type(stmt).__name__}", stmt)

    def exec_block(self, stmts: List[Stmt], env: Environment) -> Any:
        prev = self.env
        self.env = env
        result = None
        try:
            for s in stmts:
                result = self.exec(s)
        finally:
            self.env = prev
        return result

    # ── Expressions ──────────────────────────────────────────

    def eval(self, expr: Expr) -> Any:
        if isinstance(expr, IntLit):
            return expr.value
        if isinstance(expr, DecLit):
            return expr.value
        if isinstance(expr, StrLit):
            return expr.value
        if isinstance(expr, BoolLit):
            return expr.value
        if isinstance(expr, NilLit):
            return None
        if isinstance(expr, Ident):
            return self.env.get(expr.name)
        if isinstance(expr, Group):
            return self.eval(expr.expr)

        if isinstance(expr, Range):
            start = self.eval(expr.start)
            end = self.eval(expr.end)
            if not isinstance(start, int) or not isinstance(end, int):
                raise RuntimeError("Range bounds must be integers", expr)
            # end-exclusive ascending range (like Python)
            if start >= end:
                return range(0)  # empty
            return range(start, end)

        if isinstance(expr, ListLit):
            return [self.eval(e) for e in expr.elements]

        if isinstance(expr, MapLit):
            result = {}
            for key_expr, val_expr in expr.entries:
                key = self.eval(key_expr)
                if not isinstance(key, str):
                    raise RuntimeError("Map keys must be strings", expr)
                if key in result:
                    raise RuntimeError(f"Duplicate map key: {key!r}", expr)
                result[key] = self.eval(val_expr)
            return result

        if isinstance(expr, Index):
            obj = self.eval(expr.object)
            idx = self.eval(expr.index)
            if isinstance(obj, tuple) and len(obj) == 2 and obj[0] == "__frozen__":
                obj = obj[1]
            if isinstance(obj, list):
                if not isinstance(idx, int):
                    raise RuntimeError("List index must be an integer", expr)
                if idx < 0 or idx >= len(obj):
                    raise RuntimeError(f"List index out of bounds: {idx}", expr)
                return obj[idx]
            if isinstance(obj, dict):
                if not isinstance(idx, str):
                    raise RuntimeError("Map key must be a string", expr)
                if idx not in obj:
                    raise RuntimeError(f"Map key not found: {idx!r}", expr)
                return obj[idx]
            if isinstance(obj, str):
                if not isinstance(idx, int):
                    raise RuntimeError("String index must be an integer", expr)
                if idx < 0 or idx >= len(obj):
                    raise RuntimeError(f"String index out of bounds: {idx}", expr)
                return obj[idx]
            raise RuntimeError(f"Cannot index type {type(obj).__name__}", expr)

        if isinstance(expr, ThisLit):
            try:
                return self.env.get("this")
            except RuntimeError:
                raise RuntimeError("'this' used outside of method", expr)

        if isinstance(expr, NewExpr):
            klass = self.env.get(expr.class_name)
            if not isinstance(klass, Class):
                raise RuntimeError(f"'{expr.class_name}' is not a class", expr)
            instance = Instance(klass)
            # call init method if present
            if "init" in klass.methods:
                init_fn = Function(klass.methods["init"], self.env, bound_this=instance)
                args = [self.eval(a) for a in expr.args]
                self.call_function(init_fn, args, expr)
            elif expr.args:
                raise RuntimeError(f"Class '{klass.name}' has no init method but got arguments", expr)
            return instance

        if isinstance(expr, Member):
            obj = self.eval(expr.object)
            if isinstance(obj, Instance):
                return obj.get(expr.name)
            # enum variants
            if hasattr(obj, expr.name):
                return getattr(obj, expr.name)
            raise RuntimeError(f"Cannot access member '{expr.name}' on {type(obj).__name__}", expr)

        if isinstance(expr, InterpStr):
            out = []
            for part in expr.parts:
                if isinstance(part, str):
                    out.append(part)
                else:
                    out.append(self.stringify(self.eval(part)))
            return "".join(out)

        if isinstance(expr, SafeNav):
            obj = self.eval(expr.object)
            if obj is None:
                return ("__opt__", None)
            if isinstance(obj, tuple) and obj[0] == "__opt__":
                if obj[1] is None:
                    return ("__opt__", None)
                obj = obj[1]
            if isinstance(obj, Instance):
                try:
                    return obj.get(expr.name)
                except Exception:
                    return ("__opt__", None)
            if hasattr(obj, expr.name):
                return getattr(obj, expr.name)
            return ("__opt__", None)

        if isinstance(expr, Slice):
            obj = self.eval(expr.object)
            if isinstance(obj, tuple) and obj[0] == "__frozen__":
                obj = obj[1]
            start = self.eval(expr.start) if expr.start is not None else None
            end = self.eval(expr.end) if expr.end is not None else None
            if isinstance(obj, (list, str)):
                return obj[start:end]
            raise RuntimeError(f"Cannot slice {type(obj).__name__}", expr)

        if isinstance(expr, Ternary):
            if self.is_truthy(self.eval(expr.cond)):
                return self.eval(expr.then_expr)
            return self.eval(expr.else_expr)

        if isinstance(expr, AwaitExpr):
            v = self.eval(expr.expr)
            if isinstance(v, Future):
                return v.result()
            return v

        if isinstance(expr, Lambda):
            # Create a synthetic FnDecl-like Function
            from .ast import FnDecl, Block, RetStmt
            params = [(p, "any", None) for p in expr.params]
            body = Block(stmts=[RetStmt(value=expr.body)])
            decl = FnDecl(name="<lambda>", params=params, return_type="any", body=body)
            return Function(decl, self.env)

        if isinstance(expr, Pipe):
            # left |> right  =>  if right is Call, inject left as first arg
            # if right is Ident/Lambda, call with left
            left_val = self.eval(expr.left)
            right = expr.right
            if isinstance(right, Call):
                # prepend left as first argument
                args = [left_val] + [self.eval(a) for a in right.args]
                callee = self.eval(right.callee)
                if isinstance(callee, Function):
                    return self.call_function(callee, args, expr)
                raise RuntimeError("Pipe target must be function", expr)
            if isinstance(right, Ident):
                fn = self.env.get(right.name)
                if isinstance(fn, Function):
                    return self.call_function(fn, [left_val], expr)
                raise RuntimeError(f"Cannot pipe into '{right.name}'", expr)
            if isinstance(right, Lambda):
                fn = self.eval(right)
                return self.call_function(fn, [left_val], expr)
            # bare expression after pipe: treat as call if Function
            fn = self.eval(right)
            if isinstance(fn, Function):
                return self.call_function(fn, [left_val], expr)
            raise RuntimeError("Invalid pipe target", expr)

        if isinstance(expr, Coalesce):
            left = self.eval(expr.left)
            # treat none/nil/opt-none as empty
            empty = left is None
            if isinstance(left, tuple) and left[0] == "__opt__" and left[1] is None:
                empty = True
            if empty:
                return self.eval(expr.right)
            if isinstance(left, tuple) and left[0] == "__opt__":
                return left[1]
            return left

        if isinstance(expr, WhenExpr):
            subject = self.eval(expr.subject) if expr.subject is not None else None
            for br in expr.branches:
                is_block = type(br.body).__name__ == "Block"
                if br.is_else:
                    if is_block:
                        return self.exec(br.body)
                    return self.eval(br.body)
                if expr.subject is not None:
                    if self.eval(br.pattern) == subject:
                        if is_block:
                            return self.exec(br.body)
                        return self.eval(br.body)
                else:
                    if self.is_truthy(self.eval(br.pattern)):
                        if is_block:
                            return self.exec(br.body)
                        return self.eval(br.body)
            return None

        if isinstance(expr, Unary):
            right = self.eval(expr.expr)
            if expr.op == "-":
                self.check_number(right, expr)
                return -right
            if expr.op == "not":
                return not self.is_truthy(right)
            raise RuntimeError(f"Unknown unary operator '{expr.op}'", expr)

        if isinstance(expr, Binary):
            # short-circuit for and/or
            if expr.op == "and":
                left = self.eval(expr.left)
                if not self.is_truthy(left):
                    return left
                return self.eval(expr.right)
            if expr.op == "or":
                left = self.eval(expr.left)
                if self.is_truthy(left):
                    return left
                return self.eval(expr.right)

            left = self.eval(expr.left)
            right = self.eval(expr.right)

            if expr.op == "+":
                if isinstance(left, list) and isinstance(right, list):
                    return left + right
                if isinstance(left, str) or isinstance(right, str):
                    return self.stringify(left) + self.stringify(right)
                self.check_number(left, expr)
                self.check_number(right, expr)
                return left + right
            if expr.op == "-":
                self.check_number(left, expr)
                self.check_number(right, expr)
                return left - right
            if expr.op == "*":
                self.check_number(left, expr)
                self.check_number(right, expr)
                return left * right
            if expr.op == "/":
                self.check_number(left, expr)
                self.check_number(right, expr)
                if right == 0:
                    raise RuntimeError("Division by zero", expr)
                return left / right
            if expr.op == "%":
                self.check_number(left, expr)
                self.check_number(right, expr)
                if right == 0:
                    raise RuntimeError("Modulo by zero", expr)
                return left % right
            if expr.op == "in":
                if isinstance(right, (list, str)):
                    return left in right
                if isinstance(right, dict):
                    return left in right
                if isinstance(right, tuple) and right[0] == "__frozen__":
                    return left in right[1]
                raise RuntimeError(f"'in' not supported for {type(right).__name__}", expr)
            if expr.op == "==":
                return left == right
            if expr.op == "!=":
                return left != right
            if expr.op == "<":
                self.check_number(left, expr)
                self.check_number(right, expr)
                return left < right
            if expr.op == ">":
                self.check_number(left, expr)
                self.check_number(right, expr)
                return left > right
            if expr.op == "<=":
                self.check_number(left, expr)
                self.check_number(right, expr)
                return left <= right
            if expr.op == ">=":
                self.check_number(left, expr)
                self.check_number(right, expr)
                return left >= right

            raise RuntimeError(f"Unknown binary operator '{expr.op}'", expr)

        if isinstance(expr, Call):
            # Built-in: __sai_ask / __sai_generate (real SAI when env set)
            if isinstance(expr.callee, Ident) and expr.callee.name in ("__sai_ask", "__sai_generate"):
                args = [self.eval(a) for a in expr.args]
                try:
                    from .sai_runtime import ask, generate
                    if expr.callee.name == "__sai_ask":
                        return ask(str(args[0]) if args else "")
                    return generate(str(args[0]) if args else "")
                except Exception as e:
                    return f"[SAI error] {e}"
            # Built-in: len()
            if isinstance(expr.callee, Ident) and expr.callee.name == "len":
                if len(expr.args) != 1:
                    raise RuntimeError("len() takes exactly 1 argument", expr)
                arg = self.eval(expr.args[0])
                if isinstance(arg, tuple) and arg[0] == "__frozen__":
                    return len(arg[1])
                if isinstance(arg, (list, dict, str, range)):
                    return len(arg)
                raise RuntimeError(f"len() not supported for {type(arg).__name__}", expr)

            # Power builtins: map, filter, each, some, none, isSome, valueOr
            if isinstance(expr.callee, Ident) and expr.callee.name in (
                "map", "filter", "each", "some", "none", "isSome", "valueOr",
                "ok", "err", "isOk", "isErr", "unwrap", "sum", "any", "all", "range_of", "sleep",
                "type", "input", "freeze", "push", "pop", "contains", "split", "join", "upper", "lower",
                "replace", "trim", "starts_with", "ends_with", "read_file", "write_file",
                "reverse", "sort", "unique",
                "json_parse", "json_stringify", "http_get", "http_post", "clock", "hash", "now", "min", "max", "abs", "pad", "require",
                "keys", "values", "floor", "ceil", "round", "clamp", "zip", "take", "drop", "find",
                "html_escape", "html_tag", "html_page",
                "env_get", "path_join", "regex_match", "csv_split", "date_fmt", "exit"
            ):
                return self._power_builtin(expr.callee.name, expr.args, expr)

            callee = self.eval(expr.callee)
            args = [self.eval(a) for a in expr.args]

            if isinstance(callee, Function):
                if getattr(callee, "is_async", False):
                    return Future(callee, args, self, expr)
                return self.call_function(callee, args, expr)

            raise RuntimeError(f"Can only call functions, got {type(callee).__name__}", expr)

        raise RuntimeError(f"Unknown expression type: {type(expr).__name__}", expr)


    def exec_use(self, stmt):
        if self.module_loader is None:
            raise RuntimeError("Module loading not available (no loader)", stmt)
        key = ".".join(stmt.path)
        alias = getattr(stmt, "alias", None)
        if key in self._imported and not alias:
            return None
        program = self.module_loader.load(stmt.path, from_span=stmt.span)
        self._imported.add(key)
        if alias:
            # Run module in isolated env, bind as namespace
            mod_env = Environment(self.global_env)
            prev = self.env
            self.env = mod_env
            try:
                for s in program.statements:
                    if isinstance(s, UseDecl):
                        self.exec_use(s)
                    else:
                        self.exec(s)
            finally:
                self.env = prev
            class ModuleNS:
                pass
            ns = ModuleNS()
            for name, val in mod_env.values.items():
                setattr(ns, name, val)
            self.env.define(alias, ns, mutable=False)
        else:
            for s in program.statements:
                if isinstance(s, UseDecl):
                    self.exec_use(s)
                else:
                    self.exec(s)
        return None

    def call_function(self, fn: Function, args: List[Any], call_node) -> Any:
        min_args = sum(1 for p in fn.decl.params if len(p) < 3 or p[2] is None)
        if len(args) < min_args or len(args) > len(fn.decl.params):
            raise RuntimeError(
                f"Function '{fn.decl.name}' expects {min_args}-{len(fn.decl.params)} arguments, got {len(args)}",
                call_node
            )
        if self.call_depth >= self.MAX_RECURSION:
            raise RuntimeError(f"Maximum recursion depth ({self.MAX_RECURSION}) exceeded", call_node)

        parent = fn.closure if fn.closure is not None else self.env
        env = Environment(parent)
        for i, param in enumerate(fn.decl.params):
            pname = param[0]
            if i < len(args):
                env.define(pname, args[i], mutable=False)
            elif len(param) >= 3 and param[2] is not None:
                default_node = param[2]
                # default is AST expr
                from .ast import IntLit, StrLit, BoolLit, NilLit
                if hasattr(default_node, "value") and type(default_node).__name__ in ("IntLit", "StrLit", "BoolLit"):
                    env.define(pname, default_node.value, mutable=False)
                elif type(default_node).__name__ == "NilLit":
                    env.define(pname, None, mutable=False)
                else:
                    env.define(pname, self.eval(default_node), mutable=False)
            else:
                raise RuntimeError(f"Missing argument for '{pname}'", call_node)
        if fn.bound_this is not None:
            env.define("this", fn.bound_this, mutable=False)

        self.call_depth += 1
        try:
            self.exec_block(fn.decl.body.stmts, env)
        except ReturnValue as ret:
            return ret.value
        except GuardSignal:
            return None
        finally:
            self.call_depth -= 1
        return None  # implicit nil return

    # ── Helpers ──────────────────────────────────────────────


    def _repr_in_collection(self, value: Any) -> str:
        if isinstance(value, str):
            return repr(value)
        return self.stringify(value)


    def _power_builtin(self, name, args, node):
        if name == "some":
            if len(args) != 1:
                raise RuntimeError("some(x) takes 1 argument", node)
            return ("__opt__", self.eval(args[0]))
        if name == "none":
            return ("__opt__", None)
        if name == "isSome":
            v = self.eval(args[0])
            return isinstance(v, tuple) and len(v) == 2 and v[0] == "__opt__" and v[1] is not None
        if name == "valueOr":
            if len(args) != 2:
                raise RuntimeError("valueOr(opt, default) takes 2 arguments", node)
            v = self.eval(args[0])
            default = self.eval(args[1])
            if isinstance(v, tuple) and v[0] == "__opt__":
                return default if v[1] is None else v[1]
            return v if v is not None else default
        if name in ("map", "filter", "each"):
            if len(args) != 2:
                raise RuntimeError(f"{name}(list, fn) takes 2 arguments", node)
            lst = self.eval(args[0])
            fn = self.eval(args[1])
            if not isinstance(lst, list):
                raise RuntimeError(f"{name} requires a list", node)
            if not isinstance(fn, Function):
                raise RuntimeError(f"{name} requires a function", node)
            if name == "map":
                return [self.call_function(fn, [item], node) for item in lst]
            if name == "filter":
                return [item for item in lst if self.is_truthy(self.call_function(fn, [item], node))]
            if name == "each":
                for item in lst:
                    self.call_function(fn, [item], node)
                return None
        if name == "ok":
            return ("__result__", "ok", self.eval(args[0]) if args else None)
        if name == "err":
            return ("__result__", "err", self.eval(args[0]) if args else "error")
        if name == "isOk":
            v = self.eval(args[0])
            return isinstance(v, tuple) and len(v) >= 2 and v[0] == "__result__" and v[1] == "ok"
        if name == "isErr":
            v = self.eval(args[0])
            return isinstance(v, tuple) and len(v) >= 2 and v[0] == "__result__" and v[1] == "err"
        if name == "unwrap":
            v = self.eval(args[0])
            if isinstance(v, tuple) and v[0] == "__result__":
                if v[1] == "ok":
                    return v[2]
                raise RuntimeError(f"unwrap on err: {v[2]}", node)
            return v
        if name == "sum":
            return sum(self.eval(args[0]))
        if name == "any":
            return any(self.eval(args[0]))
        if name == "all":
            return all(self.eval(args[0]))
        if name == "range_of":
            a, b = self.eval(args[0]), self.eval(args[1])
            return list(range(int(a), int(b)))
        if name == "sleep":
            import time
            ms = self.eval(args[0]) if args else 0
            time.sleep(float(ms) / 1000.0)
            return None
        if name == "type":
            v = self.eval(args[0])
            if v is None: return "nil"
            if isinstance(v, bool): return "bool"
            if isinstance(v, int): return "int"
            if isinstance(v, float): return "dec"
            if isinstance(v, str): return "str"
            if isinstance(v, list): return "list"
            if isinstance(v, dict): return "map"
            if isinstance(v, tuple) and v[0] == "__opt__": return "opt"
            if isinstance(v, tuple) and v[0] == "__result__": return "result"
            if isinstance(v, tuple) and v[0] == "__frozen__": return "list"
            if isinstance(v, Function): return "fn"
            return type(v).__name__
        if name == "input":
            prompt = self.stringify(self.eval(args[0])) if args else ""
            try:
                return input(prompt)
            except EOFError:
                return ""
        if name == "freeze":
            v = self.eval(args[0])
            if isinstance(v, list):
                return ("__frozen__", list(v))  # shallow copy freeze
            raise RuntimeError("freeze() only for lists", node)
        if name == "push":
            lst = self.eval(args[0])
            if isinstance(lst, tuple) and lst[0] == "__frozen__":
                raise RuntimeError("Cannot push to frozen list", node)
            val = self.eval(args[1])
            lst.append(val)
            return lst
        if name == "pop":
            lst = self.eval(args[0])
            if isinstance(lst, tuple) and lst[0] == "__frozen__":
                raise RuntimeError("Cannot pop frozen list", node)
            if not lst:
                raise RuntimeError("pop from empty list", node)
            return lst.pop()
        if name == "contains":
            container = self.eval(args[0])
            item = self.eval(args[1])
            return item in container
        if name == "split":
            s = self.eval(args[0])
            sep = self.eval(args[1]) if len(args) > 1 else " "
            return s.split(sep)
        if name == "join":
            lst = self.eval(args[0])
            sep = self.eval(args[1]) if len(args) > 1 else ""
            return sep.join(str(x) for x in lst)
        if name == "upper":
            return self.eval(args[0]).upper()
        if name == "lower":
            return self.eval(args[0]).lower()
        if name == "replace":
            s = self.eval(args[0])
            return s.replace(self.eval(args[1]), self.eval(args[2]))
        if name == "trim":
            return self.eval(args[0]).strip()
        if name == "starts_with":
            return self.eval(args[0]).startswith(self.eval(args[1]))
        if name == "ends_with":
            return self.eval(args[0]).endswith(self.eval(args[1]))
        if name == "read_file":
            path = self.eval(args[0])
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        if name == "write_file":
            path = self.eval(args[0])
            data = self.stringify(self.eval(args[1]))
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            return path
        if name == "reverse":
            lst = list(self.eval(args[0]))
            lst.reverse()
            return lst
        if name == "sort":
            return sorted(self.eval(args[0]))
        if name == "unique":
            seen = set()
            out = []
            for x in self.eval(args[0]):
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out
        if name == "json_parse":
            import json as _json
            s = self.eval(args[0])
            return _json.loads(str(s))
        if name == "json_stringify":
            import json as _json
            v = self.eval(args[0])
            return _json.dumps(v, ensure_ascii=False)
        if name == "http_get":
            import urllib.request
            url = str(self.eval(args[0]))
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                raise RuntimeError(f"http_get failed: {e}", node)
        if name == "http_post":
            import urllib.request
            url = str(self.eval(args[0]))
            body = str(self.eval(args[1])) if len(args) > 1 else ""
            data = body.encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST",
                headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                raise RuntimeError(f"http_post failed: {e}", node)
        if name == "clock" or name == "now":
            import time
            return time.time()
        if name == "hash":
            import hashlib
            s = str(self.eval(args[0]))
            algo = str(self.eval(args[1])) if len(args) > 1 else "sha256"
            h = hashlib.new(algo if algo in hashlib.algorithms_available else "sha256")
            h.update(s.encode("utf-8"))
            return h.hexdigest()
        if name == "min":
            vals = [self.eval(a) for a in args]
            if len(vals) == 1 and isinstance(vals[0], list):
                return min(vals[0])
            return min(vals)
        if name == "max":
            vals = [self.eval(a) for a in args]
            if len(vals) == 1 and isinstance(vals[0], list):
                return max(vals[0])
            return max(vals)
        if name == "abs":
            v = self.eval(args[0])
            return abs(v)
        if name == "pad":
            s = str(self.eval(args[0]))
            width = int(self.eval(args[1])) if len(args) > 1 else 0
            ch = str(self.eval(args[2])) if len(args) > 2 else " "
            return s.ljust(width, ch[0] if ch else " ")
        if name == "require":
            cond = self.eval(args[0])
            msg = self.stringify(self.eval(args[1])) if len(args) > 1 else "require failed"
            if not self.is_truthy(cond):
                raise RuntimeError(msg, node)
            return None
        if name == "keys":
            m = self.eval(args[0])
            if not isinstance(m, dict):
                raise RuntimeError("keys() needs a map", node)
            return list(m.keys())
        if name == "values":
            m = self.eval(args[0])
            if not isinstance(m, dict):
                raise RuntimeError("values() needs a map", node)
            return list(m.values())
        if name == "floor":
            import math
            return int(math.floor(float(self.eval(args[0]))))
        if name == "ceil":
            import math
            return int(math.ceil(float(self.eval(args[0]))))
        if name == "round":
            v = float(self.eval(args[0]))
            n = int(self.eval(args[1])) if len(args) > 1 else 0
            return round(v, n)
        if name == "clamp":
            v = self.eval(args[0])
            lo = self.eval(args[1])
            hi = self.eval(args[2])
            if v < lo: return lo
            if v > hi: return hi
            return v
        if name == "zip":
            a = self.eval(args[0])
            b = self.eval(args[1])
            return [[x, y] for x, y in zip(a, b)]
        if name == "take":
            xs = self.eval(args[0])
            n = int(self.eval(args[1]))
            return list(xs)[:n]
        if name == "drop":
            xs = self.eval(args[0])
            n = int(self.eval(args[1]))
            return list(xs)[n:]
        if name == "find":
            xs = self.eval(args[0])
            pred = self.eval(args[1])
            for item in xs:
                if self.is_truthy(self.call_function(pred, [item], node)):
                    return item
            return None
        if name == "html_escape":
            s = self.stringify(self.eval(args[0]))
            # Polyglot: optional Rust s_fast accelerator
            import os, shutil, subprocess
            from pathlib import Path
            native = os.environ.get("S_FAST") or shutil.which("s_fast")
            if not native:
                root = Path(__file__).resolve().parents[1]
                for cand in (
                    root / "bin" / "s_fast",
                    root / "native" / "s_fast" / "target" / "release" / "s_fast",
                    Path("/tmp/s_fast"),
                ):
                    if cand.exists():
                        native = str(cand)
                        break
            if native and os.environ.get("S_NATIVE", "1") != "0":
                try:
                    r = subprocess.run(
                        [native, "html_escape", s],
                        capture_output=True, text=True, timeout=5,
                    )
                    if r.returncode == 0 and r.stdout != "":
                        return r.stdout
                except Exception:
                    pass
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
            )
        if name == "html_tag":
            # html_tag(name, body, [attrs_map])
            tag = self.stringify(self.eval(args[0]))
            body = self.stringify(self.eval(args[1])) if len(args) > 1 else ""
            attrs = self.eval(args[2]) if len(args) > 2 else {}
            attr_s = ""
            if isinstance(attrs, dict):
                parts = []
                for k, v in attrs.items():
                    parts.append(f'{k}="{self.stringify(v).replace(chr(34), "&quot;")}"')
                if parts:
                    attr_s = " " + " ".join(parts)
            return f"<{tag}{attr_s}>{body}</{tag}>"
        if name == "html_page":
            # html_page(title, body_html)
            title = self.stringify(self.eval(args[0]))
            body = self.stringify(self.eval(args[1])) if len(args) > 1 else ""
            return (
                "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
                f"<meta charset=\"utf-8\"/>\n<title>{title}</title>\n"
                "</head>\n<body>\n"
                f"{body}\n"
                "</body>\n</html>\n"
            )

        if name == "env_get":
            import os
            key = self.stringify(self.eval(args[0]))
            default = self.stringify(self.eval(args[1])) if len(args) > 1 else ""
            return os.environ.get(key, default)
        if name == "path_join":
            from pathlib import Path
            parts = [self.stringify(self.eval(a)) for a in args]
            return str(Path(*parts)) if parts else ""
        if name == "regex_match":
            import re
            pat = self.stringify(self.eval(args[0]))
            text = self.stringify(self.eval(args[1]))
            m = re.search(pat, text)
            if not m:
                return None
            return list(m.groups()) if m.groups() else m.group(0)
        if name == "csv_split":
            line = self.stringify(self.eval(args[0]))
            sep = self.stringify(self.eval(args[1])) if len(args) > 1 else ","
            return line.split(sep)
        if name == "date_fmt":
            import time
            fmt = self.stringify(self.eval(args[0])) if args else "%Y-%m-%d %H:%M:%S"
            return time.strftime(fmt)
        if name == "exit":
            code = int(self.eval(args[0])) if args else 0
            raise SystemExit(code)
        raise RuntimeError(f"Unknown builtin {name}", node)

    def is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return True

    def check_number(self, value: Any, node):
        if not isinstance(value, (int, float)):
            raise RuntimeError(f"Operand must be a number, got {type(value).__name__}", node)

    def stringify(self, value: Any) -> str:
        if value is None:
            return "nil"
        if isinstance(value, tuple) and len(value) == 2 and value[0] == "__opt__":
            return "none" if value[1] is None else f"some({self.stringify(value[1])})"
        if isinstance(value, tuple) and len(value) == 3 and value[0] == "__result__":
            return f"{value[1]}({self.stringify(value[2])})"
        if isinstance(value, tuple) and len(value) == 2 and value[0] == "__frozen__":
            items = ", ".join(self._repr_in_collection(v) for v in value[1])
            return f"[{items}]"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            if value == int(value):
                return str(int(value))
            return str(value)
        if isinstance(value, list):
            items = ", ".join(self._repr_in_collection(v) for v in value)
            return f"[{items}]"
        if isinstance(value, dict):
            items = ", ".join(f"{k!r}: {self._repr_in_collection(v)}" for k, v in value.items())
            return f"{{{items}}}"
        if isinstance(value, range):
            return f"range({value.start}..{value.stop})"
        return str(value)
