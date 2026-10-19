"""S Language Parser — M2"""

from typing import List, Optional
from .lexer import Token, TokenKind, Lexer
from .ast import *
from .errors import ParseError, LexError


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def peek(self, n=0) -> Token:
        i = self.pos + n
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def check(self, *kinds) -> bool:
        return self.current().kind in kinds

    def match(self, *kinds) -> bool:
        if self.check(*kinds):
            self.advance()
            return True
        return False

    def expect(self, kind: TokenKind, msg: str = None) -> Token:
        if self.check(kind):
            return self.advance()
        tok = self.current()
        raise ParseError(msg or f"Expected {kind.name}, got {tok.kind.name}", tok)

    def skip_newlines(self):
        while self.match(TokenKind.NEWLINE, TokenKind.SEMI):
            pass

    def synchronize(self):
        """Error recovery: skip until a statement boundary"""
        while not self.check(TokenKind.EOF):
            if self.check(TokenKind.NEWLINE, TokenKind.SEMI, TokenKind.RBRACE):
                self.advance()
                return
            if self.check(TokenKind.LET, TokenKind.VAR, TokenKind.FN, TokenKind.IF,
                          TokenKind.LOOP, TokenKind.FOR, TokenKind.RET, TokenKind.PRINT):
                return
            self.advance()

    # ── Entry ────────────────────────────────────────────────

    def parse(self) -> Program:
        stmts = []
        self.skip_newlines()
        while not self.check(TokenKind.EOF):
            try:
                stmt = self.statement()
                if stmt:
                    stmts.append(stmt)
            except ParseError as e:
                # For M1 we re-raise; later we can collect multiple errors
                raise
            self.skip_newlines()
        return Program(statements=stmts)

    # ── Statements ───────────────────────────────────────────

    def statement(self) -> Optional[Stmt]:
        if self.check(TokenKind.USE):
            return self.use_decl()
        if self.check(TokenKind.ASSERT):
            return self.assert_stmt()
        if self.check(TokenKind.CLASS):
            return self.class_decl()
        if self.check(TokenKind.ENUM):
            return self.enum_decl()
        if self.check(TokenKind.SAFE):
            return self.safe_stmt()
        if self.check(TokenKind.WHEN):
            return self.when_stmt()
        if self.check(TokenKind.DEFER):
            return self.defer_stmt()
        if self.check(TokenKind.LET, TokenKind.VAR):
            return self.var_decl()
        if self.check(TokenKind.PRINT):
            return self.print_stmt()
        if self.check(TokenKind.IF):
            return self.if_stmt()
        if self.check(TokenKind.LOOP):
            return self.loop_stmt()
        if self.check(TokenKind.WHILE):
            return self.while_stmt()
        if self.check(TokenKind.FOR):
            return self.for_stmt()
        if self.check(TokenKind.BREAK):
            self.advance()
            return BreakStmt(span=self.current().span)
        if self.check(TokenKind.NEXT):
            self.advance()
            return NextStmt(span=self.current().span)
        if self.check(TokenKind.RET):
            return self.ret_stmt()
        if self.check(TokenKind.ASYNC):
            self.advance()
            if not self.check(TokenKind.FN):
                raise ParseError("Expected fn after async", self.current())
            return self.fn_decl(is_async=True)
        if self.check(TokenKind.FN):
            return self.fn_decl()
        if self.check(TokenKind.SPAWN):
            return self.spawn_stmt()
        if self.check(TokenKind.REPEAT):
            return self.repeat_stmt()
        if self.check(TokenKind.GUARD):
            return self.guard_stmt()
        if self.check(TokenKind.LBRACE):
            return self.block()

        # expression statement or assignment
        expr = self.expression()
        if self.match(TokenKind.ASSIGN):
            value = self.expression()
            if isinstance(expr, Ident):
                return Assign(name=expr.name, value=value, span=expr.span)
            if isinstance(expr, Member):
                return SetMember(object=expr.object, name=expr.name, value=value, span=expr.span)
            if isinstance(expr, Index):
                return IndexAssign(object=expr.object, index=expr.index, value=value, span=expr.span)
            raise ParseError("Left side of assignment must be a name, member, or index", self.current())
        # compound assignment: x += 1
        for op_tok, op in [
            (TokenKind.PLUS_EQ, "+"), (TokenKind.MINUS_EQ, "-"),
            (TokenKind.STAR_EQ, "*"), (TokenKind.SLASH_EQ, "/"),
        ]:
            if self.match(op_tok):
                if not isinstance(expr, Ident):
                    raise ParseError("Compound assignment needs a variable name", self.current())
                rhs = self.expression()
                bin_e = Binary(op=op, left=Ident(name=expr.name, span=expr.span), right=rhs, span=expr.span)
                return Assign(name=expr.name, value=bin_e, span=expr.span)
        return ExprStmt(expr=expr, span=expr.span)

    def var_decl(self) -> LetDecl:
        mutable = self.current().kind == TokenKind.VAR
        start = self.advance()  # let or var
        name_tok = self.expect(TokenKind.IDENT, "Expected variable name")
        type_ann = None
        if self.match(TokenKind.COLON):
            type_tok = self.expect(TokenKind.IDENT, "Expected type name")
            type_ann = type_tok.text
        self.expect(TokenKind.ASSIGN, "Expected '=' after variable name")
        value = self.expression()
        return LetDecl(
            name=name_tok.text,
            type_ann=type_ann,
            value=value,
            mutable=mutable,
            span=start.span
        )





    def guard_stmt(self):
        start = self.advance()
        cond = self.expression()
        return GuardStmt(condition=cond, span=start.span)

    def repeat_stmt(self):

        start = self.advance()
        count = self.expression()
        body = self.block()
        return RepeatStmt(count=count, body=body, span=start.span)

    def spawn_stmt(self):

        start = self.advance()
        e = self.expression()
        return SpawnStmt(expr=e, span=start.span)

    def defer_stmt(self):

        start = self.advance()
        if self.check(TokenKind.LBRACE):
            body = self.block()
        else:
            body = self.statement()
        return DeferStmt(body=body, span=start.span)

    def enum_decl(self):

        start = self.advance()
        name = self.expect(TokenKind.IDENT, "Expected enum name").text
        self.expect(TokenKind.LBRACE)
        variants = []
        self.skip_newlines()
        while not self.check(TokenKind.RBRACE, TokenKind.EOF):
            variants.append(self.expect(TokenKind.IDENT).text)
            self.match(TokenKind.COMMA)
            self.skip_newlines()
        self.expect(TokenKind.RBRACE)
        return EnumDecl(name=name, variants=variants, span=start.span)

    def when_stmt(self):
        return ExprStmt(expr=self._when_expr(), span=None)

    def _when_expr(self):
        start = self.advance()  # when
        subject = None
        if not self.check(TokenKind.LBRACE):
            subject = self.expression()
        self.expect(TokenKind.LBRACE)
        branches = []
        self.skip_newlines()
        while not self.check(TokenKind.RBRACE, TokenKind.EOF):
            if self.match(TokenKind.ELSE):
                if self.check(TokenKind.LBRACE):
                    body = self.block()
                else:
                    # else -> expr
                    if self.match(TokenKind.ARROW):
                        pass
                    body_e = self.expression()
                    body = Block(stmts=[ExprStmt(expr=body_e)], span=start.span)
                branches.append(WhenBranch(pattern=None, body=body, is_else=True))
                self.skip_newlines()
                break
            pattern = self.expression()
            if self.match(TokenKind.ARROW):
                body_e = self.expression()
                body = Block(stmts=[ExprStmt(expr=body_e)], span=start.span)
            else:
                body = self.block()
            branches.append(WhenBranch(pattern=pattern, body=body, is_else=False))
            self.skip_newlines()
        self.expect(TokenKind.RBRACE)
        return WhenExpr(subject=subject, branches=branches, span=start.span)

    def class_decl(self) -> ClassDecl:
        start = self.advance()  # class
        name = self.expect(TokenKind.IDENT, "Expected class name").text
        self.expect(TokenKind.LBRACE)
        methods = []
        self.skip_newlines()
        while not self.check(TokenKind.RBRACE, TokenKind.EOF):
            if self.check(TokenKind.FN):
                methods.append(self.fn_decl())
            else:
                raise ParseError("Expected method (fn) inside class", self.current())
            self.skip_newlines()
        self.expect(TokenKind.RBRACE)
        return ClassDecl(name=name, methods=methods, span=start.span)

    def safe_stmt(self) -> SafeStmt:
        start = self.advance()  # safe
        body = self.block()
        self.expect(TokenKind.RESCUE, "Expected 'rescue' after safe block")
        rname = self.expect(TokenKind.IDENT, "Expected error variable name").text
        rbody = self.block()
        return SafeStmt(body=body, rescue_name=rname, rescue_body=rbody, span=start.span)

    def assert_stmt(self) -> AssertStmt:
        start = self.advance()  # assert
        cond = self.expression()
        message = None
        if self.match(TokenKind.COMMA):
            message = self.expression()
        return AssertStmt(condition=cond, message=message, span=start.span)

    def use_decl(self) -> UseDecl:
        start = self.advance()  # use
        path = []
        path.append(self.expect(TokenKind.IDENT, "Expected module name").text)
        while self.match(TokenKind.DOT):
            path.append(self.expect(TokenKind.IDENT, "Expected module name after '.'").text)
        alias = None
        if self.match(TokenKind.AS):
            alias = self.expect(TokenKind.IDENT, "Expected alias after as").text
        return UseDecl(path=path, alias=alias, span=start.span)

    def print_stmt(self) -> PrintStmt:
        start = self.advance()  # print
        args = []
        if self.match(TokenKind.LPAREN):
            if not self.check(TokenKind.RPAREN):
                args.append(self.expression())
                while self.match(TokenKind.COMMA):
                    args.append(self.expression())
            self.expect(TokenKind.RPAREN)
        else:
            # print without parens: print "hello", x, y
            args.append(self.expression())
            while self.match(TokenKind.COMMA):
                args.append(self.expression())
        return PrintStmt(args=args, span=start.span)

    def if_stmt(self) -> IfStmt:
        start = self.advance()  # if or elif treated via caller
        cond = self.expression()
        then = self.block()
        else_branch = None
        if self.match(TokenKind.ELIF):
            else_branch = self.if_stmt_after_elif()
        elif self.match(TokenKind.ELSE):
            if self.check(TokenKind.IF):
                else_branch = self.if_stmt()
            else:
                else_branch = self.block()
        return IfStmt(condition=cond, then_branch=then, else_branch=else_branch, span=start.span)

    def if_stmt_after_elif(self) -> IfStmt:
        """Parse starting at condition after ELIF token already consumed."""
        start = self.current()
        cond = self.expression()
        then = self.block()
        else_branch = None
        if self.match(TokenKind.ELIF):
            else_branch = self.if_stmt_after_elif()
        elif self.match(TokenKind.ELSE):
            if self.check(TokenKind.IF):
                else_branch = self.if_stmt()
            else:
                else_branch = self.block()
        return IfStmt(condition=cond, then_branch=then, else_branch=else_branch, span=getattr(start, "span", None))

    def loop_stmt(self) -> LoopStmt:
        start = self.advance()  # loop
        body = self.block()
        return LoopStmt(body=body, span=start.span)

    def while_stmt(self):
        start = self.advance()  # while
        cond = self.expression()
        body = self.block()
        return WhileStmt(condition=cond, body=body, span=start.span)

    def for_stmt(self) -> ForStmt:
        start = self.advance()  # for
        var = self.expect(TokenKind.IDENT, "Expected loop variable").text
        self.expect(TokenKind.IN, "Expected 'in'")
        iterable = self.expression()
        body = self.block()
        return ForStmt(var=var, iterable=iterable, body=body, span=start.span)

    def ret_stmt(self) -> RetStmt:
        start = self.advance()  # ret
        value = None
        if not self.check(TokenKind.NEWLINE, TokenKind.SEMI, TokenKind.RBRACE, TokenKind.EOF):
            value = self.expression()
        return RetStmt(value=value, span=start.span)

    def fn_decl(self, is_async: bool = False) -> FnDecl:
        start = self.advance()  # fn
        name = self.expect(TokenKind.IDENT, "Expected function name").text
        self.expect(TokenKind.LPAREN)
        params = []
        if not self.check(TokenKind.RPAREN):
            while True:
                pname = self.expect(TokenKind.IDENT).text
                ptype = "any"
                default = None
                if self.match(TokenKind.COLON):
                    ptype = self.expect(TokenKind.IDENT).text
                if self.match(TokenKind.ASSIGN):
                    default = self.expression()
                params.append((pname, ptype, default))
                if not self.match(TokenKind.COMMA):
                    break
        self.expect(TokenKind.RPAREN)
        self.expect(TokenKind.COLON)
        rtype = self.expect(TokenKind.IDENT).text
        body = self.block()
        return FnDecl(name=name, params=params, return_type=rtype, body=body, is_async=is_async, span=start.span)

    def block(self) -> Block:
        start = self.expect(TokenKind.LBRACE)
        stmts = []
        self.skip_newlines()
        while not self.check(TokenKind.RBRACE, TokenKind.EOF):
            stmt = self.statement()
            if stmt:
                stmts.append(stmt)
            self.skip_newlines()
        self.expect(TokenKind.RBRACE)
        return Block(stmts=stmts, span=start.span)

    # ── Expressions (Pratt / precedence climbing) ────────────

    def expression(self) -> Expr:
        return self.pipe_expr()

    def pipe_expr(self) -> Expr:
        left = self.coalesce_expr()
        while self.match(TokenKind.PIPE):
            right = self.coalesce_expr()
            left = Pipe(left=left, right=right, span=getattr(left, "span", None))
        return left

    def coalesce_expr(self) -> Expr:
        left = self.ternary_expr()
        while self.match(TokenKind.COALESCE):
            right = self.ternary_expr()
            left = Coalesce(left=left, right=right, span=getattr(left, "span", None))
        return left

    def ternary_expr(self) -> Expr:
        cond = self.or_expr()
        if self.match(TokenKind.QUESTION):
            then_e = self.expression()
            self.expect(TokenKind.COLON, "Expected ':' in ternary")
            else_e = self.ternary_expr()
            return Ternary(cond=cond, then_expr=then_e, else_expr=else_e, span=getattr(cond, "span", None))
        return cond

    def or_expr(self) -> Expr:
        left = self.and_expr()
        while self.match(TokenKind.OR):
            op = "or"
            right = self.and_expr()
            left = Binary(op=op, left=left, right=right, span=left.span)
        return left

    def and_expr(self) -> Expr:
        left = self.equality()
        while self.match(TokenKind.AND):
            op = "and"
            right = self.equality()
            left = Binary(op=op, left=left, right=right, span=left.span)
        return left

    def equality(self) -> Expr:
        left = self.comparison()
        while self.check(TokenKind.EQ, TokenKind.NEQ):
            op = self.advance().text
            right = self.comparison()
            left = Binary(op=op, left=left, right=right, span=left.span)
        return left

    def comparison(self) -> Expr:
        left = self.term()
        while self.check(TokenKind.LT, TokenKind.GT, TokenKind.LTE, TokenKind.GTE, TokenKind.IN):
            op = self.advance().text
            right = self.term()
            left = Binary(op=op, left=left, right=right, span=left.span)
        return left

    def term(self) -> Expr:
        left = self.factor()
        while self.check(TokenKind.PLUS, TokenKind.MINUS):
            op = self.advance().text
            right = self.factor()
            left = Binary(op=op, left=left, right=right, span=left.span)
        return left

    def factor(self) -> Expr:
        left = self.unary()
        while self.check(TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
            op = self.advance().text
            right = self.unary()
            left = Binary(op=op, left=left, right=right, span=left.span)
        return left

    def unary(self) -> Expr:
        if self.check(TokenKind.MINUS, TokenKind.NOT):
            op = self.advance().text
            expr = self.unary()
            return Unary(op=op, expr=expr, span=expr.span)
        if self.match(TokenKind.AWAIT):
            e = self.unary()
            return AwaitExpr(expr=e, span=e.span)
        return self.call()

    def call(self) -> Expr:
        expr = self.primary()
        while True:
            if self.match(TokenKind.LPAREN):
                args = []
                if not self.check(TokenKind.RPAREN):
                    args.append(self.expression())
                    while self.match(TokenKind.COMMA):
                        args.append(self.expression())
                self.expect(TokenKind.RPAREN)
                expr = Call(callee=expr, args=args, span=expr.span)
            elif self.match(TokenKind.LBRACK):
                # [idx] or [start:end] or [:end] or [start:]
                start_e = None
                end_e = None
                if self.check(TokenKind.COLON):
                    self.advance()
                    if not self.check(TokenKind.RBRACK):
                        end_e = self.expression()
                    self.expect(TokenKind.RBRACK)
                    expr = Slice(object=expr, start=None, end=end_e, span=expr.span)
                else:
                    first = self.expression()
                    if self.match(TokenKind.COLON):
                        start_e = first
                        if not self.check(TokenKind.RBRACK):
                            end_e = self.expression()
                        self.expect(TokenKind.RBRACK)
                        expr = Slice(object=expr, start=start_e, end=end_e, span=expr.span)
                    else:
                        self.expect(TokenKind.RBRACK)
                        expr = Index(object=expr, index=first, span=expr.span)
            elif self.match(TokenKind.DOT):
                name = self.expect(TokenKind.IDENT, "Expected member name").text
                expr = Member(object=expr, name=name, span=expr.span)
            elif self.match(TokenKind.QUESTION_DOT):
                name = self.expect(TokenKind.IDENT, "Expected member name after ?.").text
                expr = SafeNav(object=expr, name=name, span=expr.span)
            else:
                break
        # Range: expr .. expr
        if self.match(TokenKind.DOTDOT):
            end = self.call()
            return Range(start=expr, end=end, span=expr.span)
        return expr

    def primary(self) -> Expr:
        if self.check(TokenKind.WHEN):
            return self._when_expr()
        tok = self.current()

        if self.match(TokenKind.INT):
            return IntLit(value=tok.value, span=tok.span)
        if self.match(TokenKind.DEC):
            return DecLit(value=tok.value, span=tok.span)
        if self.match(TokenKind.STR):
            val = tok.value
            if "${" in val:
                return self._parse_interp(val, tok.span)
            return StrLit(value=val, span=tok.span)
        if self.match(TokenKind.TRUE):
            return BoolLit(value=True, span=tok.span)
        if self.match(TokenKind.FALSE):
            return BoolLit(value=False, span=tok.span)
        if self.match(TokenKind.NIL_KW):
            return NilLit(span=tok.span)
        if self.match(TokenKind.IDENT):
            return Ident(name=tok.text, span=tok.span)
        if self.match(TokenKind.THIS):
            return ThisLit(span=tok.span)
        if self.match(TokenKind.NEW):
            cname = self.expect(TokenKind.IDENT, "Expected class name after new").text
            self.expect(TokenKind.LPAREN)
            args = []
            if not self.check(TokenKind.RPAREN):
                args.append(self.expression())
                while self.match(TokenKind.COMMA):
                    args.append(self.expression())
            self.expect(TokenKind.RPAREN)
            return NewExpr(class_name=cname, args=args, span=tok.span)
        if self.match(TokenKind.LPAREN):
            expr = self.expression()
            self.expect(TokenKind.RPAREN)
            return Group(expr=expr, span=tok.span)

        # List literal: [1, 2, 3]
        if self.match(TokenKind.LBRACK):
            elements = []
            self.skip_newlines()
            if not self.check(TokenKind.RBRACK):
                elements.append(self.expression())
                while self.match(TokenKind.COMMA):
                    self.skip_newlines()
                    if self.check(TokenKind.RBRACK):
                        break
                    elements.append(self.expression())
            self.skip_newlines()
            self.expect(TokenKind.RBRACK)
            return ListLit(elements=elements, span=tok.span)

        # Lambda { x -> expr } / { x, y -> expr } OR map literal
        if self.match(TokenKind.LBRACE):
            self.skip_newlines()
            # Look ahead for lambda: IDENT (COMMA IDENT)* ARROW
            is_lambda = False
            if self.check(TokenKind.IDENT):
                # scan without consuming permanently — manual peek
                save = self.pos
                self.advance()
                while self.match(TokenKind.COMMA):
                    if not self.check(TokenKind.IDENT):
                        break
                    self.advance()
                if self.check(TokenKind.ARROW):
                    is_lambda = True
                self.pos = save
            if is_lambda:
                params = []
                params.append(self.expect(TokenKind.IDENT).text)
                while self.match(TokenKind.COMMA):
                    params.append(self.expect(TokenKind.IDENT).text)
                self.expect(TokenKind.ARROW)
                # body: expression or block-like statements until }
                # single expression body
                body_expr = self.expression()
                self.skip_newlines()
                self.expect(TokenKind.RBRACE)
                return Lambda(params=params, body=body_expr, span=tok.span)
            # Map literal
            entries = []
            if not self.check(TokenKind.RBRACE):
                while True:
                    key = self.expression()
                    self.expect(TokenKind.COLON, "Expected ':' in map entry")
                    val = self.expression()
                    entries.append((key, val))
                    self.skip_newlines()
                    if not self.match(TokenKind.COMMA):
                        break
                    self.skip_newlines()
                    if self.check(TokenKind.RBRACE):
                        break
            self.skip_newlines()
            self.expect(TokenKind.RBRACE)
            return MapLit(entries=entries, span=tok.span)

        raise ParseError(f"Unexpected token: {tok.kind.name} ({tok.text!r})", tok)


    def _parse_interp(self, val, span):
        """Split string with ${...} into InterpStr parts. Simple scan."""
        parts = []
        i = 0
        buf = ""
        while i < len(val):
            if val[i] == "$" and i + 1 < len(val) and val[i+1] == "{":
                if buf:
                    parts.append(buf)
                    buf = ""
                i += 2
                expr_src = ""
                depth = 1
                while i < len(val) and depth:
                    if val[i] == "{": depth += 1
                    elif val[i] == "}": depth -= 1
                    if depth:
                        expr_src += val[i]
                    i += 1
                # parse expr_src as expression
                from .lexer import Lexer
                sub_tokens = Lexer(expr_src + "\n", "<interp>").tokenize()
                sub = Parser(sub_tokens)
                parts.append(sub.expression())
            else:
                buf += val[i]
                i += 1
        if buf:
            parts.append(buf)
        return InterpStr(parts=parts, span=span)


def parse_source(source: str, filename: str = "<stdin>") -> Program:
    lexer = Lexer(source, filename)
    tokens = lexer.tokenize()
    # filter out ERROR tokens early
    errors = [t for t in tokens if t.kind == TokenKind.ERROR]
    if errors:
        raise ParseError(errors[0].text, errors[0])
    parser = Parser(tokens)
    return parser.parse()
