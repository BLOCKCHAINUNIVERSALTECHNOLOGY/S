"""S HTTP server — W-WEB-2 static + health + simple JSON API hooks."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import urlparse, parse_qs


def make_handler(root: Path, routes: Dict[str, Callable]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[s serve] {self.address_string()} {fmt % args}")

        def _send(self, code: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Powered-By", "S-Language")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            if path in routes:
                try:
                    result = routes[path](parsed)
                    if isinstance(result, tuple):
                        code, body, ctype = result
                    else:
                        code, body, ctype = 200, result, "application/json; charset=utf-8"
                    if isinstance(body, str):
                        body = body.encode("utf-8")
                    self._send(code, body, ctype)
                except Exception as e:
                    self._send(500, f'{{"error":"{e}"}}'.encode(), "application/json")
                return
            # static
            rel = path.lstrip("/") or "index.html"
            if ".." in rel:
                self._send(400, b"bad path")
                return
            file_path = (root / rel).resolve()
            if not str(file_path).startswith(str(root.resolve())):
                self._send(403, b"forbidden")
                return
            if file_path.is_dir():
                file_path = file_path / "index.html"
            if not file_path.is_file():
                self._send(404, b"not found")
                return
            data = file_path.read_bytes()
            ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            self._send(200, data, ctype)

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            if path in routes:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b""
                try:
                    result = routes[path](parsed, raw)
                    if isinstance(result, tuple):
                        code, body, ctype = result
                    else:
                        code, body, ctype = 200, result, "application/json; charset=utf-8"
                    if isinstance(body, str):
                        body = body.encode("utf-8")
                    self._send(code, body, ctype)
                except Exception as e:
                    self._send(500, f'{{"error":"{e}"}}'.encode(), "application/json")
                return
            self._send(404, b"not found")

    return Handler


def run_server(root: str, host: str = "127.0.0.1", port: int = 8080):
    root_p = Path(root).resolve()
    if not root_p.exists():
        root_p.mkdir(parents=True)

    def health(parsed, raw=None):
        return 200, json.dumps({"ok": True, "engine": "S", "root": str(root_p)}), "application/json; charset=utf-8"

    def api_hello(parsed, raw=None):
        return 200, json.dumps({"message": "Hello from S serve", "path": parsed.path}), "application/json; charset=utf-8"

    def api_echo(parsed, raw=None):
        body = (raw or b"").decode("utf-8", errors="replace")
        qs = parse_qs(parsed.query)
        return 200, json.dumps({"query": qs, "body": body, "ok": True}), "application/json; charset=utf-8"

    def api_form(parsed, raw=None):
        # application/x-www-form-urlencoded simple parse
        body = (raw or b"").decode("utf-8", errors="replace")
        data = parse_qs(body, keep_blank_values=True)
        flat = {k: (v[0] if len(v) == 1 else v) for k, v in data.items()}
        return 200, json.dumps({"form": flat, "ok": True}), "application/json; charset=utf-8"

    routes = {
        "/health": health,
        "/api/hello": api_hello,
        "/api/echo": api_echo,
        "/api/form": api_form,
    }
    handler = make_handler(root_p, routes)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"S serve http://{host}:{port}/  root={root_p}")
    print("  GET /health  GET /api/hello  + static files")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
        httpd.server_close()
