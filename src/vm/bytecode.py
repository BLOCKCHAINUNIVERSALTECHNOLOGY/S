"""S Bytecode + SVM — with classes, modules, safe/rescue"""

from enum import IntEnum, auto
from dataclasses import dataclass, field
from typing import List, Any, Dict


class Op(IntEnum):
    LOAD_CONST      = auto()
    LOAD_NAME       = auto()
    STORE_NAME      = auto()
    BINARY_ADD      = auto()
    BINARY_SUB      = auto()
    BINARY_MUL      = auto()
    BINARY_DIV      = auto()
    BINARY_MOD      = auto()
    COMPARE         = auto()
    BINARY_AND      = auto()
    BINARY_OR       = auto()
    UNARY_NOT       = auto()
    UNARY_NEG       = auto()
    JUMP            = auto()
    JUMP_IF_FALSE   = auto()
    JUMP_IF_TRUE    = auto()
    PRINT           = auto()
    POP             = auto()
    BUILD_LIST      = auto()
    BUILD_MAP       = auto()
    GET_ITEM        = auto()
    MAKE_FUNC       = auto()
    CALL            = auto()
    RETURN          = auto()
    MAKE_CLASS      = auto()
    NEW_INSTANCE    = auto()
    GET_PROP        = auto()
    SET_PROP        = auto()
    SETUP_SAFE      = auto()  # arg = rescue IP; err name pushed as const before
    BIND_ERR        = auto()  # arg = name index for error variable
    END_SAFE        = auto()  # arg = IP after rescue block
    HALT            = auto()


@dataclass
class FunctionObject:
    name: str
    arity: int
    chunk: "Chunk"
    param_names: List[str] = field(default_factory=list)
    bound_this: Any = None


@dataclass
class ClassObject:
    name: str
    methods: Dict[str, FunctionObject] = field(default_factory=dict)


@dataclass
class Instance:
    klass: ClassObject
    fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    code: List[int] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)
    names: List[str] = field(default_factory=list)

    def add_const(self, value) -> int:
        for i, v in enumerate(self.constants):
            if v == value and type(v) == type(value):
                return i
        self.constants.append(value)
        return len(self.constants) - 1

    def add_name(self, name: str) -> int:
        if name in self.names:
            return self.names.index(name)
        self.names.append(name)
        return len(self.names) - 1

    def emit(self, op: Op, arg: int = 0) -> int:
        pos = len(self.code)
        self.code.append(int(op))
        self.code.append(arg)
        return pos

    def patch(self, pos: int, arg: int):
        self.code[pos + 1] = arg

    def __len__(self):
        return len(self.code)


class CallFrame:
    def __init__(self, chunk: Chunk, ip: int = 0):
        self.chunk = chunk
        self.ip = ip
        self.locals: Dict[str, Any] = {}


class VM:
    def __init__(self, chunk: Chunk):
        self.frames: List[CallFrame] = [CallFrame(chunk)]
        self.stack: List[Any] = []
        self.globals: Dict[str, Any] = {
            "len": ("__native__", "len"),
            "none": ("__native__", "none"),
            "some": ("__native__", "some"),
            "valueOr": ("__native__", "valueOr"),
        }
        self.handlers: List[dict] = []
        self._pending_instances: List[Instance] = []

    @property
    def frame(self) -> CallFrame:
        return self.frames[-1]

    def _lookup(self, name: str):
        if name in self.frame.locals:
            return self.frame.locals[name]
        if name in self.globals:
            return self.globals[name]
        raise RuntimeError(f"Undefined variable '{name}'")

    def _store(self, name: str, value):
        if name in self.frame.locals or len(self.frames) > 1:
            self.frame.locals[name] = value
        else:
            self.globals[name] = value

    def _handle_error(self, e: RuntimeError) -> bool:
        """Return True if handled by safe/rescue."""
        if not self.handlers:
            return False
        h = self.handlers.pop()
        while len(self.frames) - 1 > h["frame_idx"]:
            self.frames.pop()
        frame = self.frame
        err_name = h["err_name"]
        frame.locals[err_name] = str(e)
        self.globals[err_name] = str(e)
        frame.ip = h["rescue_ip"]
        return True

    def run(self):
        while self.frames:
            frame = self.frame
            code = frame.chunk.code
            if frame.ip >= len(code):
                self.frames.pop()
                continue

            op = Op(code[frame.ip])
            arg = code[frame.ip + 1]
            frame.ip += 2

            try:
                result = self._step(op, arg, frame)
                if result is not None or op == Op.HALT:
                    if op == Op.HALT:
                        return self.stack[-1] if self.stack else None
                    if op == Op.RETURN and not self.frames:
                        return result
            except RuntimeError as e:
                if not self._handle_error(e):
                    raise
        return None

    def _step(self, op, arg, frame):
        if op == Op.LOAD_CONST:
            self.stack.append(frame.chunk.constants[arg])
        elif op == Op.LOAD_NAME:
            self.stack.append(self._lookup(frame.chunk.names[arg]))
        elif op == Op.STORE_NAME:
            self._store(frame.chunk.names[arg], self.stack.pop())
        elif op == Op.BINARY_ADD:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a + b)
        elif op == Op.BINARY_SUB:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a - b)
        elif op == Op.BINARY_MUL:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a * b)
        elif op == Op.BINARY_DIV:
            b, a = self.stack.pop(), self.stack.pop()
            if b == 0:
                raise RuntimeError("Division by zero")
            self.stack.append(a / b)
        elif op == Op.BINARY_MOD:
            b, a = self.stack.pop(), self.stack.pop()
            if b == 0:
                raise RuntimeError("Modulo by zero")
            self.stack.append(a % b)
        elif op == Op.COMPARE:
            b, a = self.stack.pop(), self.stack.pop()
            ops = ["==", "!=", "<", ">", "<=", ">="]
            self.stack.append({
                "==": a == b, "!=": a != b,
                "<": a < b, ">": a > b,
                "<=": a <= b, ">=": a >= b,
            }[ops[arg]])
        elif op == Op.BINARY_AND:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(bool(a) and bool(b))
        elif op == Op.BINARY_OR:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(bool(a) or bool(b))
        elif op == Op.UNARY_NOT:
            self.stack.append(not self.stack.pop())
        elif op == Op.UNARY_NEG:
            self.stack.append(-self.stack.pop())
        elif op == Op.JUMP:
            frame.ip = arg
        elif op == Op.JUMP_IF_FALSE:
            if not self.stack.pop():
                frame.ip = arg
        elif op == Op.JUMP_IF_TRUE:
            if self.stack.pop():
                frame.ip = arg
        elif op == Op.PRINT:
            vals = [self.stack.pop() for _ in range(arg)][::-1]
            def fmt(v):
                if v is None: return "nil"
                if isinstance(v, bool): return "true" if v else "false"
                return str(v)
            print(*[fmt(v) for v in vals])
        elif op == Op.POP:
            if self.stack:
                self.stack.pop()
        elif op == Op.BUILD_LIST:
            self.stack.append([self.stack.pop() for _ in range(arg)][::-1])
        elif op == Op.BUILD_MAP:
            m = {}
            for _ in range(arg):
                val = self.stack.pop()
                key = self.stack.pop()
                m[key] = val
            self.stack.append(m)
        elif op == Op.GET_ITEM:
            idx = self.stack.pop()
            obj = self.stack.pop()
            self.stack.append(obj[idx])
        elif op == Op.MAKE_FUNC:
            self.stack.append(frame.chunk.constants[arg])
        elif op == Op.CALL:
            arity = arg
            args = [self.stack.pop() for _ in range(arity)][::-1]
            callee = self.stack.pop()
            if isinstance(callee, tuple) and callee[0] == "__native__":
                if callee[1] == "len":
                    if arity != 1:
                        raise RuntimeError("len() takes 1 argument")
                    obj = args[0]
                    if isinstance(obj, tuple) and len(obj) == 2 and obj[0] == "__opt__":
                        self.stack.append(0 if obj[1] is None else 1)
                    else:
                        self.stack.append(len(obj))
                elif callee[1] == "none":
                    self.stack.append(None)  # treat as nil for ?? 
                elif callee[1] == "some":
                    self.stack.append(args[0] if args else None)
                elif callee[1] == "valueOr":
                    v, d = args[0], args[1]
                    self.stack.append(d if v is None else v)
                else:
                    raise RuntimeError(f"Unknown native: {callee[1]}")
            elif isinstance(callee, FunctionObject):
                if arity != callee.arity:
                    raise RuntimeError(
                        f"Function '{callee.name}' expects {callee.arity} args, got {arity}"
                    )
                new_frame = CallFrame(callee.chunk)
                for name, val in zip(callee.param_names, args):
                    new_frame.locals[name] = val
                if callee.bound_this is not None:
                    new_frame.locals["this"] = callee.bound_this
                self.frames.append(new_frame)
            else:
                raise RuntimeError(f"Can only call functions, got {type(callee).__name__}")
        elif op == Op.MAKE_CLASS:
            self.stack.append(frame.chunk.constants[arg])
        elif op == Op.NEW_INSTANCE:
            arity = arg
            args = [self.stack.pop() for _ in range(arity)][::-1]
            klass = self.stack.pop()
            if not isinstance(klass, ClassObject):
                raise RuntimeError(f"Not a class: {type(klass).__name__}")
            inst = Instance(klass)
            if "init" in klass.methods:
                init_fn = klass.methods["init"]
                if arity != init_fn.arity:
                    raise RuntimeError(f"init expects {init_fn.arity} args, got {arity}")
                new_frame = CallFrame(init_fn.chunk)
                for name, val in zip(init_fn.param_names, args):
                    new_frame.locals[name] = val
                new_frame.locals["this"] = inst
                self._pending_instances.append(inst)
                self.frames.append(new_frame)
            else:
                if arity != 0:
                    raise RuntimeError(f"Class '{klass.name}' has no init")
                self.stack.append(inst)
        elif op == Op.GET_PROP:
            name = frame.chunk.names[arg]
            obj = self.stack.pop()
            if not isinstance(obj, Instance):
                raise RuntimeError(f"Cannot get property on {type(obj).__name__}")
            if name in obj.fields:
                self.stack.append(obj.fields[name])
            elif name in obj.klass.methods:
                m = obj.klass.methods[name]
                self.stack.append(FunctionObject(
                    m.name, m.arity, m.chunk, m.param_names, bound_this=obj
                ))
            else:
                raise RuntimeError(f"Undefined property '{name}'")
        elif op == Op.SET_PROP:
            name = frame.chunk.names[arg]
            val = self.stack.pop()
            obj = self.stack.pop()
            if not isinstance(obj, Instance):
                raise RuntimeError(f"Cannot set property on {type(obj).__name__}")
            obj.fields[name] = val
        elif op == Op.RETURN:
            result = self.stack.pop() if self.stack else None
            self.frames.pop()
            if self._pending_instances and self.frames:
                self.stack.append(self._pending_instances.pop())
            elif self.frames:
                self.stack.append(result)
            return result
        elif op == Op.SETUP_SAFE:
            # arg = rescue IP; err_name index is on stack as const? 
            # Convention: err_name index stored in arg high bits? 
            # We use BIND_ERR right after SETUP in compiler, but handler needs name at setup.
            # arg encodes rescue_ip; err name set by BIND_ERR which updates last handler
            self.handlers.append({
                "frame_idx": len(self.frames) - 1,
                "rescue_ip": arg,
                "err_name": "err",
            })
        elif op == Op.BIND_ERR:
            if self.handlers:
                self.handlers[-1]["err_name"] = frame.chunk.names[arg]
        elif op == Op.END_SAFE:
            if self.handlers:
                self.handlers.pop()
            frame.ip = arg
        elif op == Op.HALT:
            return "HALT"
        else:
            raise RuntimeError(f"Unknown opcode: {op}")
        return None
