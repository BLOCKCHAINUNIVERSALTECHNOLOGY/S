#!/usr/bin/env python3
"""S Language Server — offline powerful: diagnostics, complete, goto-def, rename, refs"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

KEYWORDS = [
    "let", "var", "fn", "ret", "if", "else", "loop", "for", "in",
    "break", "next", "class", "new", "this", "safe", "rescue",
    "use", "assert", "true", "false", "nil", "and", "or", "not",
    "print", "guard", "defer", "async", "await", "spawn", "repeat",
    "when", "enum",
]
TYPES = ["int", "dec", "str", "bool", "list", "map", "opt"]
BUILTINS = [
    "print", "len", "map", "filter", "each", "some", "none", "valueOr",
    "ok", "err", "isOk", "isErr", "unwrap", "freeze", "type", "input",
    "sort", "unique", "reverse", "push", "pop", "split", "join",
    "upper", "lower", "trim", "replace", "contains", "sum", "any", "all",
]


def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line or line in (b"\r\n", b"\n"):
            break
        k, v = line.decode().split(":", 1)
        headers[k.strip()] = v.strip()
    length = int(headers.get("Content-Length", 0))
    if length == 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode())


def send(msg):
    body = json.dumps(msg).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode())
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def send_result(id, result):
    send({"jsonrpc": "2.0", "id": id, "result": result})


def send_notify(method, params):
    send({"jsonrpc": "2.0", "method": method, "params": params})


docs = {}  # uri -> text
indexes = {}  # uri -> SymbolIndexer


def word_at(text: str, line: int, character: int) -> str:
    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return ""
    row = lines[line]
    if character > len(row):
        character = len(row)
    i = character
    while i > 0 and (row[i - 1].isalnum() or row[i - 1] == "_"):
        i -= 1
    j = character
    while j < len(row) and (row[j].isalnum() or row[j] == "_"):
        j += 1
    return row[i:j]


def reindex(uri, text):
    try:
        from src.parser import parse_source
        from src.symbols import SymbolIndexer
        from src.errors import SError
        try:
            program = parse_source(text, uri)
            idx = SymbolIndexer().index(program)
            indexes[uri] = idx
            return program, None
        except SError as e:
            indexes[uri] = SymbolIndexer()
            return None, e
    except Exception:
        indexes[uri] = SymbolIndexer()
        return None, None


def diagnose(uri, text):
    diags = []
    program, parse_err = reindex(uri, text)
    if parse_err is not None:
        line = max(0, getattr(getattr(parse_err, "location", None), "line", 1) - 1)
        col = max(0, getattr(getattr(parse_err, "location", None), "col", 1) - 1)
        diags.append({
            "range": {"start": {"line": line, "character": col},
                      "end": {"line": line, "character": col + 1}},
            "severity": 1,
            "source": "s-lsp",
            "message": str(parse_err),
        })
    elif program is not None:
        try:
            from src.checker import check_program
            for d in check_program(program):
                line = 0
                col = 0
                if d.span is not None:
                    line = max(0, getattr(d.span, "line", 1) - 1)
                    col = max(0, getattr(d.span, "col", 1) - 1)
                sev = {"error": 1, "warning": 2, "info": 3}.get(d.severity, 2)
                diags.append({
                    "range": {"start": {"line": line, "character": col},
                              "end": {"line": line, "character": col + 1}},
                    "severity": sev,
                    "source": "s-lsp",
                    "message": d.message,
                })
        except Exception:
            pass
    send_notify("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": diags})


def completion():
    items = []
    for k in KEYWORDS:
        items.append({"label": k, "kind": 14, "detail": "keyword"})
    for t in TYPES:
        items.append({"label": t, "kind": 25, "detail": "type"})
    for f in BUILTINS:
        items.append({"label": f, "kind": 3, "detail": "builtin"})
    return items


def definition(uri, line, character):
    text = docs.get(uri, "")
    name = word_at(text, line, character)
    idx = indexes.get(uri)
    if not idx or not name or name not in idx.defs:
        return None
    sym = idx.defs[name]
    return {
        "uri": uri,
        "range": {
            "start": {"line": max(0, sym.line - 1), "character": max(0, sym.col - 1)},
            "end": {"line": max(0, sym.line - 1), "character": max(0, sym.col - 1) + len(name)},
        },
    }


def references(uri, line, character):
    text = docs.get(uri, "")
    name = word_at(text, line, character)
    idx = indexes.get(uri)
    if not idx or not name:
        return []
    locs = []
    if name in idx.defs:
        sym = idx.defs[name]
        locs.append({
            "uri": uri,
            "range": {
                "start": {"line": max(0, sym.line - 1), "character": max(0, sym.col - 1)},
                "end": {"line": max(0, sym.line - 1), "character": max(0, sym.col - 1) + len(name)},
            },
        })
    for r in idx.refs:
        if r.name == name:
            locs.append({
                "uri": uri,
                "range": {
                    "start": {"line": max(0, r.line - 1), "character": max(0, r.col - 1)},
                    "end": {"line": max(0, r.line - 1), "character": max(0, r.col - 1) + len(name)},
                },
            })
    return locs


def rename(uri, line, character, new_name):
    text = docs.get(uri, "")
    old = word_at(text, line, character)
    idx = indexes.get(uri)
    if not idx or not old or old not in idx.defs:
        return None
    from src.symbols import rename_in_text
    new_text = rename_in_text(text, old, new_name, idx)
    return {
        "documentChanges": [{
            "textDocument": {"uri": uri, "version": None},
            "edits": [{
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": len(text.splitlines()), "character": 0},
                },
                "newText": new_text,
            }],
        }]
    }


def hover(uri, line, character):
    text = docs.get(uri, "")
    name = word_at(text, line, character)
    idx = indexes.get(uri)
    if idx and name in idx.defs:
        sym = idx.defs[name]
        return {
            "contents": {
                "kind": "markdown",
                "value": f"**{sym.kind}** `{sym.name}`  \nDefined at line {sym.line}",
            }
        }
    if name in KEYWORDS:
        return {"contents": {"kind": "markdown", "value": f"**keyword** `{name}`"}}
    if name in BUILTINS:
        return {"contents": {"kind": "markdown", "value": f"**builtin** `{name}`"}}
    return {
        "contents": {
            "kind": "markdown",
            "value": "**S** · Simple · Safe · Supreme",
        }
    }


def main():
    while True:
        msg = read_message()
        if msg is None:
            break
        method = msg.get("method")
        id = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            send_result(id, {
                "capabilities": {
                    "textDocumentSync": 1,
                    "completionProvider": {"triggerCharacters": [".", "?"]},
                    "hoverProvider": True,
                    "definitionProvider": True,
                    "referencesProvider": True,
                    "renameProvider": True,
                },
                "serverInfo": {"name": "s-lsp", "version": "2.0.0-rc2"},
            })
        elif method == "initialized":
            pass
        elif method == "shutdown":
            send_result(id, None)
        elif method == "exit":
            break
        elif method == "textDocument/didOpen":
            doc = params["textDocument"]
            docs[doc["uri"]] = doc["text"]
            diagnose(doc["uri"], doc["text"])
        elif method == "textDocument/didChange":
            uri = params["textDocument"]["uri"]
            text = params["contentChanges"][0]["text"]
            docs[uri] = text
            diagnose(uri, text)
        elif method == "textDocument/completion":
            # also add user symbols
            uri = params.get("textDocument", {}).get("uri", "")
            items = completion()
            idx = indexes.get(uri)
            if idx:
                for name, sym in idx.defs.items():
                    kind = {"fn": 3, "class": 7, "var": 6, "param": 6, "enum": 10}.get(sym.kind, 6)
                    items.append({"label": name, "kind": kind, "detail": sym.kind})
            send_result(id, {"isIncomplete": False, "items": items})
        elif method == "textDocument/hover":
            pos = params["position"]
            uri = params["textDocument"]["uri"]
            send_result(id, hover(uri, pos["line"], pos["character"]))
        elif method == "textDocument/definition":
            pos = params["position"]
            uri = params["textDocument"]["uri"]
            send_result(id, definition(uri, pos["line"], pos["character"]))
        elif method == "textDocument/references":
            pos = params["position"]
            uri = params["textDocument"]["uri"]
            send_result(id, references(uri, pos["line"], pos["character"]))
        elif method == "textDocument/rename":
            pos = params["position"]
            uri = params["textDocument"]["uri"]
            send_result(id, rename(uri, pos["line"], pos["character"], params["newName"]))
        elif id is not None:
            send_result(id, None)


if __name__ == "__main__":
    main()
