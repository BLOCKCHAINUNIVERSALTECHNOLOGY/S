"""S Language Lexer — M1 vertical slice"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
from .ast import SourceSpan


class TokenKind(Enum):
    # Literals
    INT     = auto()
    DEC     = auto()
    STR     = auto()
    BOOL    = auto()
    NIL     = auto()

    # Identifiers & keywords
    IDENT   = auto()
    LET     = auto()
    VAR     = auto()
    FN      = auto()
    RET     = auto()
    IF      = auto()
    ELSE    = auto()
    ELIF    = auto()
    LOOP    = auto()
    WHILE   = auto()
    FOR     = auto()
    IN      = auto()
    BREAK   = auto()
    NEXT    = auto()
    TRUE    = auto()
    FALSE   = auto()
    NIL_KW  = auto()
    AND     = auto()
    OR      = auto()
    NOT     = auto()
    USE     = auto()
    CLASS   = auto()
    NEW     = auto()
    THIS    = auto()
    SAFE    = auto()
    RESCUE  = auto()
    PRINT   = auto()
    ASSERT  = auto()
    WHEN    = auto()
    ENUM    = auto()
    ARROW   = auto()   # ->
    PIPE    = auto()   # |>
    COALESCE = auto()  # ??
    PLUS_EQ = auto()
    MINUS_EQ = auto()
    STAR_EQ = auto()
    SLASH_EQ = auto()
    DEFER   = auto()
    ASYNC   = auto()
    AWAIT   = auto()
    SPAWN   = auto()
    REPEAT  = auto()
    QUESTION = auto()  # ? for ternary
    AS      = auto()
    GUARD   = auto()
    QUESTION_DOT = auto()  # ?.

    # Operators
    PLUS    = auto()
    MINUS   = auto()
    STAR    = auto()
    SLASH   = auto()
    PERCENT = auto()
    EQ      = auto()          # ==
    NEQ     = auto()          # !=
    LT      = auto()
    GT      = auto()
    LTE     = auto()
    GTE     = auto()
    ASSIGN  = auto()          # =
    DOT     = auto()
    DOTDOT  = auto()          # ..

    # Delimiters
    LPAREN  = auto()
    RPAREN  = auto()
    LBRACE  = auto()
    RBRACE  = auto()
    LBRACK  = auto()
    RBRACK  = auto()
    COMMA   = auto()
    COLON   = auto()
    SEMI    = auto()          # optional, we use newline as END

    # Special
    NEWLINE = auto()
    EOF     = auto()
    ERROR   = auto()


KEYWORDS = {
    "let":    TokenKind.LET,
    "var":    TokenKind.VAR,
    "fn":     TokenKind.FN,
    "ret":    TokenKind.RET,
    "if":     TokenKind.IF,
    "else":   TokenKind.ELSE,
    "elif":   TokenKind.ELIF,
    "loop":   TokenKind.LOOP,
    "while":  TokenKind.WHILE,
    "for":    TokenKind.FOR,
    "in":     TokenKind.IN,
    "break":  TokenKind.BREAK,
    "next":   TokenKind.NEXT,
    "true":   TokenKind.TRUE,
    "false":  TokenKind.FALSE,
    "nil":    TokenKind.NIL_KW,
    "and":    TokenKind.AND,
    "or":     TokenKind.OR,
    "not":    TokenKind.NOT,
    "use":    TokenKind.USE,
    "class":  TokenKind.CLASS,
    "new":    TokenKind.NEW,
    "this":   TokenKind.THIS,
    "safe":   TokenKind.SAFE,
    "rescue": TokenKind.RESCUE,
    "print":  TokenKind.PRINT,
    "assert": TokenKind.ASSERT,
    "when":   TokenKind.WHEN,
    "enum":   TokenKind.ENUM,
    "defer":  TokenKind.DEFER,
    "async":  TokenKind.ASYNC,
    "await":  TokenKind.AWAIT,
    "spawn":  TokenKind.SPAWN,
    "repeat": TokenKind.REPEAT,
    "as":     TokenKind.AS,
    "guard":  TokenKind.GUARD,
}


@dataclass
class Token:
    kind: TokenKind
    text: str
    value: any = None
    span: Optional[SourceSpan] = None

    def __repr__(self):
        if self.value is not None:
            return f"Token({self.kind.name}, {self.value!r})"
        return f"Token({self.kind.name}, {self.text!r})"


class Lexer:
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def error(self, msg: str) -> Token:
        span = SourceSpan(self.filename, self.pos, self.pos, self.line, self.col)
        return Token(TokenKind.ERROR, msg, span=span)

    def peek(self, n=0) -> str:
        i = self.pos + n
        return self.source[i] if i < len(self.source) else "\0"

    def advance(self) -> str:
        ch = self.peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.peek() == expected:
            self.advance()
            return True
        return False

    def make_token(self, kind: TokenKind, text: str, value=None, start_pos=None, start_line=None, start_col=None) -> Token:
        start = start_pos if start_pos is not None else self.pos - len(text)
        line = start_line if start_line is not None else self.line
        col = start_col if start_col is not None else self.col - len(text)
        span = SourceSpan(self.filename, start, self.pos, line, col)
        return Token(kind, text, value, span)

    def skip_whitespace_and_comments(self):
        while True:
            ch = self.peek()
            if ch in " \t\r":
                self.advance()
            elif ch == "/" and self.peek(1) == "/":
                # line comment
                while self.peek() not in "\n\0":
                    self.advance()
            elif ch == "/" and self.peek(1) == "*":
                # block comment
                self.advance()  # /
                self.advance()  # *
                while True:
                    if self.peek() == "\0":
                        break
                    if self.peek() == "*" and self.peek(1) == "/":
                        self.advance()
                        self.advance()
                        break
                    self.advance()
            else:
                break

    def read_string(self) -> Token:
        start_pos = self.pos
        start_line = self.line
        start_col = self.col
        triple = (self.peek(0) == '"' and self.peek(1) == '"' and self.peek(2) == '"')
        if triple:
            self.advance(); self.advance(); self.advance()
        else:
            self.advance()
        value = []
        while True:
            ch = self.peek()
            if ch is None or ch == "\0" or (isinstance(ch, str) and len(ch)==0):
                # check end of source
                if self.pos >= len(self.source):
                    return self.error("Unterminated string")
            if self.pos >= len(self.source):
                return self.error("Unterminated string")
            ch = self.source[self.pos]
            if triple:
                if ch == '"' and self.pos+2 < len(self.source) and self.source[self.pos+1] == '"' and self.source[self.pos+2] == '"':
                    self.advance(); self.advance(); self.advance()
                    break
                if ch == "\\":
                    self.advance()
                    if self.pos >= len(self.source):
                        return self.error("Unterminated string")
                    esc = self.advance()
                    mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
                    value.append(mapping.get(esc, esc))
                else:
                    value.append(self.advance())
            else:
                if ch == '"':
                    self.advance()
                    break
                if ch == "\n":
                    return self.error("Newline in string (use \"\"\" for multiline)")
                if ch == "\\":
                    self.advance()
                    if self.pos >= len(self.source):
                        return self.error("Unterminated string")
                    esc = self.advance()
                    mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
                    value.append(mapping.get(esc, esc))
                else:
                    value.append(self.advance())
        text = "".join(value)
        return self.make_token(TokenKind.STR, text, value=text,
                               start_pos=start_pos, start_line=start_line, start_col=start_col)


    def read_number(self) -> Token:
        start_pos = self.pos
        start_line = self.line
        start_col = self.col
        while self.peek().isdigit():
            self.advance()
        if self.peek() == "." and self.peek(1).isdigit():
            self.advance()  # .
            while self.peek().isdigit():
                self.advance()
            text = self.source[start_pos:self.pos]
            return self.make_token(TokenKind.DEC, text, float(text), start_pos, start_line, start_col)
        text = self.source[start_pos:self.pos]
        return self.make_token(TokenKind.INT, text, int(text), start_pos, start_line, start_col)

    def read_ident(self) -> Token:
        start_pos = self.pos
        start_line = self.line
        start_col = self.col
        while self.peek().isalnum() or self.peek() == "_":
            self.advance()
        text = self.source[start_pos:self.pos]
        kind = KEYWORDS.get(text, TokenKind.IDENT)
        value = None
        if kind == TokenKind.TRUE:
            value = True
        elif kind == TokenKind.FALSE:
            value = False
        elif kind == TokenKind.NIL_KW:
            value = None
        return self.make_token(kind, text, value, start_pos, start_line, start_col)

    def tokenize(self) -> List[Token]:
        while True:
            self.skip_whitespace_and_comments()
            ch = self.peek()
            if ch == "\0":
                self.tokens.append(self.make_token(TokenKind.EOF, ""))
                break

            start_pos = self.pos
            start_line = self.line
            start_col = self.col

            if ch == "\n":
                self.advance()
                self.tokens.append(self.make_token(TokenKind.NEWLINE, "\n", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue

            # two-character operators
            if ch == "=" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.EQ, "==", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "!" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.NEQ, "!=", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "<" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.LTE, "<=", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == ">" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.GTE, ">=", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "." and self.peek(1) == ".":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.DOTDOT, "..", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "-" and self.peek(1) == ">":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.ARROW, "->", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "|" and self.peek(1) == ">":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.PIPE, "|>", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "?" and self.peek(1) == "?":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.COALESCE, "??", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "?" and self.peek(1) == ".":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.QUESTION_DOT, "?.", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "+" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.PLUS_EQ, "+=", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "-" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.MINUS_EQ, "-=", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "*" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.STAR_EQ, "*=", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue
            if ch == "/" and self.peek(1) == "=":
                self.advance(); self.advance()
                self.tokens.append(self.make_token(TokenKind.SLASH_EQ, "/=", start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue

            # single character
            single = {
                "+": TokenKind.PLUS,
                "-": TokenKind.MINUS,
                "*": TokenKind.STAR,
                "/": TokenKind.SLASH,
                "%": TokenKind.PERCENT,
                "=": TokenKind.ASSIGN,
                "<": TokenKind.LT,
                ">": TokenKind.GT,
                "(": TokenKind.LPAREN,
                ")": TokenKind.RPAREN,
                "{": TokenKind.LBRACE,
                "}": TokenKind.RBRACE,
                "[": TokenKind.LBRACK,
                "]": TokenKind.RBRACK,
                ",": TokenKind.COMMA,
                ":": TokenKind.COLON,
                ".": TokenKind.DOT,
                ";": TokenKind.SEMI,
                "?": TokenKind.QUESTION,
            }
            if ch in single:
                self.advance()
                self.tokens.append(self.make_token(single[ch], ch, start_pos=start_pos, start_line=start_line, start_col=start_col))
                continue

            if ch == '"':
                self.tokens.append(self.read_string())
                continue

            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            if ch.isalpha() or ch == "_":
                self.tokens.append(self.read_ident())
                continue

            # unknown
            self.advance()
            self.tokens.append(self.error(f"Unexpected character: {ch!r}"))

        return self.tokens
