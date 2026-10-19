"""S Shield v2 — stronger key stretch + anti-tamper fail-closed

Own rules. Stdlib only.
On integrity failure: refuse to run (app 'crashes' / hard exit).
Does NOT attack the analyst's machine — only stops the protected app.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import struct
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

MAGIC = b"SBX2"  # v2 format
VERSION = 2
PBKDF2_ITERS = 200_000


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERS, dklen=32)


def _xor_stream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    out = bytearray(len(data))
    counter = 0
    ks = b""
    ki = 0
    block = key + nonce
    for i in range(len(data)):
        if ki >= len(ks):
            ks = hashlib.sha256(block + struct.pack(">Q", counter)).digest()
            counter += 1
            ki = 0
        out[i] = data[i] ^ ks[ki]
        ki += 1
    return bytes(out)


def _replace_idents(text: str, mapping: dict) -> str:
    import re as _re
    if not mapping:
        return text
    parts = []
    i = 0
    while i < len(text):
        if text[i] == '"':
            j = i + 1
            while j < len(text):
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            parts.append(text[i:j])
            i = j
        else:
            j = i
            while j < len(text) and text[j] != '"':
                j += 1
            chunk = text[i:j]
            for old in sorted(mapping.keys(), key=len, reverse=True):
                chunk = _re.sub(r"\b" + _re.escape(old) + r"\b", mapping[old], chunk)
            parts.append(chunk)
            i = j
    return "".join(parts)


def _strip_comments(source: str) -> str:
    lines = []
    for line in source.splitlines():
        if "//" in line:
            in_str = False
            out = []
            i = 0
            while i < len(line):
                ch = line[i]
                if ch == '"':
                    in_str = not in_str
                    out.append(ch)
                    i += 1
                    continue
                if not in_str and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break
                out.append(ch)
                i += 1
            line = "".join(out).rstrip()
        if line.strip():
            lines.append(line)
    return "\n".join(lines) + "\n"


def _strip_source(source: str) -> Tuple[str, Dict[str, str]]:
    mapping: Dict[str, str] = {}
    try:
        from .parser import parse_source
        from .symbols import SymbolIndexer
        program = parse_source(source)
        idx = SymbolIndexer().index(program)
        reserved = {
            "print", "len", "map", "filter", "some", "none", "valueOr",
            "ok", "err", "unwrap", "freeze", "type", "true", "false", "nil",
        }
        n = 0
        for name, sym in sorted(idx.defs.items(), key=lambda x: x[1].line):
            if name in reserved or name.startswith("S_"):
                continue
            if sym.kind in ("fn", "var", "class", "enum"):
                mapping[name] = f"S_{n}"
                n += 1
        source = _replace_idents(source, mapping)
    except Exception:
        mapping = {}
    return _strip_comments(source), mapping


def _seal(plain: bytes, passphrase: str) -> bytes:
    salt = os.urandom(16)
    nonce = os.urandom(16)
    key = _derive_key(passphrase, salt)
    cipher = _xor_stream(plain, key, nonce)
    # dual tags — both must match (anti-partial-tamper)
    tag1 = hmac.new(key, MAGIC + salt + nonce + cipher, hashlib.sha256).digest()
    tag2 = hmac.new(key, cipher + nonce + salt + MAGIC, hashlib.sha256).digest()
    return MAGIC + bytes([VERSION]) + salt + nonce + tag1 + tag2 + cipher


def _open(blob: bytes, passphrase: str) -> bytes:
    if len(blob) < 4 + 1 + 16 + 16 + 32 + 32:
        _die("SBX corrupt: too short")
    if blob[:4] != MAGIC:
        # accept legacy SBX1 for old packs
        if blob[:4] == b"SBX1":
            return _open_legacy(blob, passphrase)
        _die("SBX corrupt: bad magic")
    ver = blob[4]
    if ver != VERSION:
        _die(f"SBX unsupported version: {ver}")
    salt = blob[5:21]
    nonce = blob[21:37]
    tag1 = blob[37:69]
    tag2 = blob[69:101]
    cipher = blob[101:]
    key = _derive_key(passphrase, salt)
    e1 = hmac.new(key, MAGIC + salt + nonce + cipher, hashlib.sha256).digest()
    e2 = hmac.new(key, cipher + nonce + salt + MAGIC, hashlib.sha256).digest()
    if not (hmac.compare_digest(tag1, e1) and hmac.compare_digest(tag2, e2)):
        _die("TAMPER DETECTED — integrity fail. App halted.", decoy=True, seed=salt + nonce + tag1[:16])
    return _xor_stream(cipher, key, nonce)


def _open_legacy(blob: bytes, passphrase: str) -> bytes:
    """SBX1 reader for compatibility."""
    salt = blob[5:21]
    nonce = blob[21:37]
    tag = blob[37:69]
    cipher = blob[69:]
    # old key stretch
    key = passphrase.encode("utf-8")
    for i in range(120_000):
        key = hashlib.sha256(salt + key + struct.pack(">I", i % 1024)).digest()
    expect = hmac.new(key, b"SBX1" + salt + nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expect):
        _die("TAMPER DETECTED — integrity fail. App halted.", decoy=True, seed=blob[:64] if "blob" in dir() else os.urandom(32))
    return _xor_stream(cipher, key, nonce)


def _decoy_flood(seed: bytes, lines: int = 50000) -> None:
    """On forced/wrong open: dump huge garbage so casual RE gets unusable noise."""
    import hashlib as _h
    state = seed
    # ~50k lines of pseudo-random noise (bounded — not infinite)
    out = []
    for i in range(lines):
        state = _h.sha256(state + struct.pack(">I", i)).digest()
        out.append(state.hex() + state[::-1].hex())
        if i % 500 == 0:
            out.append("/* S_SEAL_NOISE block %d — not source */" % i)
    sys.stdout.write("\n".join(out))
    sys.stdout.write("\n[S SHIELD] decoy complete — real source not available\n")
    sys.stdout.flush()


def _die(msg: str, decoy: bool = True, seed: bytes = b"") -> None:
    """Fail-closed. Optional huge decoy instead of useful error detail."""
    print(f"[S SHIELD] {msg}", file=sys.stderr)
    if decoy:
        _decoy_flood(seed or os.urandom(32), lines=40000)
    sys.exit(2)


def pack(source: str, passphrase: str, meta: Dict[str, Any] | None = None) -> bytes:
    cleaned, mapping = _strip_source(source)
    payload = {"v": VERSION, "kind": "file", "src": cleaned, "meta": meta or {}, "map": mapping}
    plain = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _seal(plain, passphrase)


def unpack(blob: bytes, passphrase: str) -> Dict[str, Any]:
    plain = _open(blob, passphrase)
    try:
        return json.loads(plain.decode("utf-8"))
    except Exception:
        _die("SBX decrypt failed — halted.")


def pack_file(src_path: Path, out_path: Path, passphrase: str, meta: Dict[str, Any] | None = None) -> Path:
    text = src_path.read_text(encoding="utf-8")
    blob = pack(text, passphrase, meta=meta or {"entry": src_path.name})
    out_path.write_bytes(blob)
    return out_path


def unpack_file(sbx_path: Path, passphrase: str) -> Dict[str, Any]:
    return unpack(sbx_path.read_bytes(), passphrase)


def pack_project(root: Path, passphrase: str, entry: str = "main.s") -> bytes:
    import re as _re
    root = Path(root)
    raw_files = {}
    for p in sorted(root.rglob("*.s")):
        rel = str(p.relative_to(root)).replace("\\", "/")
        raw_files[rel] = p.read_text(encoding="utf-8")

    reserved = {
        "print", "len", "map", "filter", "each", "some", "none", "valueOr",
        "ok", "err", "isOk", "isErr", "unwrap", "freeze", "type", "input",
        "true", "false", "nil",
    }
    mapping = {}
    n = 0
    try:
        from .parser import parse_source
        from .symbols import SymbolIndexer
        for rel, text in raw_files.items():
            try:
                prog = parse_source(text)
                idx = SymbolIndexer().index(prog)
                for name, sym in sorted(idx.defs.items(), key=lambda x: x[1].line):
                    if name in reserved or name in mapping or name.startswith("S_"):
                        continue
                    if sym.kind in ("fn", "var", "class", "enum"):
                        mapping[name] = f"S_{n}"
                        n += 1
            except Exception:
                pass
    except Exception:
        mapping = {}

    files = {}
    for rel, text in raw_files.items():
        text = _replace_idents(text, mapping)
        files[rel] = {"src": _strip_comments(text), "map": mapping}

    meta = {"entry": entry, "files": list(files.keys()), "mapping": mapping}
    se = root / "project.se"
    if se.exists():
        meta["project_se"] = se.read_text(encoding="utf-8")
    payload = {"v": VERSION, "kind": "project", "files": files, "meta": meta}
    plain = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _seal(plain, passphrase)


def seal_append(blob: bytes, passphrase: str, rel_path: str, source: str) -> bytes:
    """Join/add a file into existing project SBX (needs key). Cannot read others without key."""
    data = unpack(blob, passphrase)
    if data.get("kind") != "project" and "files" not in data:
        # upgrade single file to project
        entry_src = data.get("src", "")
        data = {
            "v": VERSION,
            "kind": "project",
            "files": {"main.s": {"src": entry_src, "map": {}}},
            "meta": data.get("meta") or {"entry": "main.s"},
        }
    cleaned, mapping = _strip_source(source)
    data["files"][rel_path] = {"src": cleaned, "map": mapping}
    data.setdefault("meta", {})["files"] = list(data["files"].keys())
    plain = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return _seal(plain, passphrase)
