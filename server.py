#!/usr/bin/env python3
"""Mini Maya Studio server: serves the app and stores scenes on disk. Standard library only."""
import argparse
import json
import os
import re
import sys
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "dev"
DATA = Path(os.environ.get("MINIMAYA_DATA", ROOT / "data"))
SCENES = DATA / "scenes"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_BODY = 20 * 1024 * 1024


class Handler(SimpleHTTPRequestHandler):
    server_version = "MiniMaya/" + VERSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stdout.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), fmt % args))
        sys.stdout.flush()

    def end_headers(self):
        path = urlparse(self.path).path
        if path.startswith("/api/") or path in ("/", "/index.html"):
            self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def scene_path(self, name):
        if not NAME_RE.match(name):
            return None
        return SCENES / (name + ".json")

    def route(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            return None, None
        parts = [unquote(p) for p in path[len("/api/"):].split("/") if p]
        return parts, path

    def do_GET(self):
        parts, _ = self.route()
        if parts is None:
            blocked = ("/data", "/logs", "/.git", "/server.py", "/install.sh", "/run.sh", "/uninstall.sh")
            if any(urlparse(self.path).path.startswith(b) for b in blocked):
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return super().do_GET()
        if parts == ["health"]:
            return self.send_json(HTTPStatus.OK, {"ok": True, "app": "minimaya", "version": VERSION})
        if parts == ["scenes"]:
            items = []
            for f in SCENES.glob("*.json"):
                st = f.stat()
                items.append({"name": f.stem, "modified": st.st_mtime, "size": st.st_size})
            items.sort(key=lambda x: x["modified"], reverse=True)
            return self.send_json(HTTPStatus.OK, {"scenes": items})
        if len(parts) == 2 and parts[0] == "scenes":
            p = self.scene_path(parts[1])
            if not p or not p.exists():
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "No scene with that name"})
            body = p.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})

    def do_PUT(self):
        parts, _ = self.route()
        if not parts or len(parts) != 2 or parts[0] != "scenes":
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
        p = self.scene_path(parts[1])
        if not p:
            return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Use letters, numbers, dashes and underscores, up to 64"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Scene is empty or larger than 20 MB"})
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
            assert isinstance(data, dict) and isinstance(data.get("objects"), list)
        except Exception:
            return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Body is not a Mini Maya scene"})
        SCENES.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(raw)
        os.replace(tmp, p)
        return self.send_json(HTTPStatus.OK, {"ok": True, "name": parts[1], "path": str(p)})

    def do_DELETE(self):
        parts, _ = self.route()
        if not parts or len(parts) != 2 or parts[0] != "scenes":
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
        p = self.scene_path(parts[1])
        if not p or not p.exists():
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "No scene with that name"})
        p.unlink()
        return self.send_json(HTTPStatus.OK, {"ok": True})


def main():
    ap = argparse.ArgumentParser(description="Mini Maya Studio server")
    ap.add_argument("--host", default=os.environ.get("MINIMAYA_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MINIMAYA_PORT", "48713")))
    a = ap.parse_args()
    SCENES.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((a.host, a.port), Handler)
    print("Mini Maya Studio %s on http://%s:%d  (data: %s)" % (VERSION, a.host, a.port, DATA), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
