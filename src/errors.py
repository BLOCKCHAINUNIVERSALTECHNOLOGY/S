"""S Language unified error types — M2"""

from typing import Optional, Any


class SError(Exception):
    """Base class for all S language errors shown to the user."""
    def __init__(self, message: str, location: Any = None):
        self.message = message
        # location can be a string, a Token, or a node with .span
        if location is None:
            self.location = None
        elif isinstance(location, str):
            self.location = location
        elif hasattr(location, "span") and location.span is not None:
            self.location = str(location.span)
        elif hasattr(location, "__str__"):
            self.location = str(location)
        else:
            self.location = None
        super().__init__(self.format())

    def format(self) -> str:
        if self.location:
            return f"{self.location}: {self.message}"
        return self.message


class LexError(SError):
    """Lexer / tokenization error"""
    pass


class ParseError(SError):
    """Syntax / parse error"""
    pass


class TypeError_(SError):
    """Static type / semantic error"""
    pass


class RuntimeError_(SError):
    """Runtime error while executing"""
    pass
