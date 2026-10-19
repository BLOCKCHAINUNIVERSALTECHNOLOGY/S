"""S Language Module Loader — M5 / V0.0.5

Resolution rules (simple & predictable):
  use math          →  <dir>/math.s
  use utils.helper  →  <dir>/utils/helper.s
  use utils.helper  →  <dir>/utils/helper/init.s   (fallback)

Cycle detection via DFS.
"""

from pathlib import Path
from typing import Dict, Set, List, Optional
from .parser import parse_source
from .errors import SError, ParseError, RuntimeError_


class ModuleError(SError):
    pass


class ModuleLoader:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.loaded: Dict[str, object] = {}       # module_key → Program
        self.loading: Set[str] = set()            # currently being loaded (cycle detect)
        self.load_order: List[str] = []
        # Built-in Slib path
        self.slib_dir = Path(__file__).resolve().parent / "slib"

    def resolve_path(self, path_parts: List[str]) -> Path:
        """Convert use path to filesystem path.

        Lookup order:
          1. Project-local: <root>/<parts>.s  or  <root>/<parts>/init.s
          2. Built-in Slib:  if first part is 's', look in slib/
        """
        # 1. Project local
        candidate = self.root_dir.joinpath(*path_parts).with_suffix(".s")
        if candidate.exists():
            return candidate
        candidate2 = self.root_dir.joinpath(*path_parts) / "init.s"
        if candidate2.exists():
            return candidate2

        # 2. Built-in Slib / SDX / SAI
        #    s.math      → slib/math.s
        #    sdx.ui      → slib/sdx/ui.s
        #    sai.chat    → slib/sai/chat.s
        if path_parts:
            # s.xxx
            if path_parts[0] == "s" and len(path_parts) >= 2:
                slib_candidate = self.slib_dir.joinpath(*path_parts[1:]).with_suffix(".s")
                if slib_candidate.exists():
                    return slib_candidate
                if path_parts[1] == "list":
                    alt = self.slib_dir / "listutil.s"
                    if alt.exists():
                        return alt
            # sdx.xxx / sai.xxx
            if path_parts[0] in ("sdx", "sai") and len(path_parts) >= 2:
                candidate = self.slib_dir.joinpath(*path_parts).with_suffix(".s")
                if candidate.exists():
                    return candidate

        raise ModuleError(
            f"Module not found: {'.'.join(path_parts)} "
            f"(looked in project and Slib/SDX/SAI)"
        )

    def module_key(self, path_parts: List[str]) -> str:
        return ".".join(path_parts)

    def load(self, path_parts: List[str], from_span=None) -> object:
        key = self.module_key(path_parts)

        if key in self.loaded:
            return self.loaded[key]

        if key in self.loading:
            chain = " → ".join(self.load_order + [key])
            raise ModuleError(f"Circular module dependency: {chain}", from_span)

        file_path = self.resolve_path(path_parts)
        self.loading.add(key)
        self.load_order.append(key)

        try:
            source = file_path.read_text(encoding="utf-8")
            program = parse_source(source, str(file_path))
            # Pre-scan for use declarations and load them first (DFS)
            from .ast import UseDecl
            for stmt in program.statements:
                if isinstance(stmt, UseDecl):
                    self.load(stmt.path, from_span=stmt.span)
            self.loaded[key] = program
            return program
        except ParseError as e:
            raise ParseError(f"in module '{key}': {e.message}", e.location)
        finally:
            self.loading.discard(key)
            if self.load_order and self.load_order[-1] == key:
                self.load_order.pop()
