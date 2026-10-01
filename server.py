#!/usr/bin/env python3
"""Mini Maya Studio server: serves the app, stores scenes and media, and encodes movies with ffmpeg. Standard library only."""
import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
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
ASSETS = DATA / "assets"
RENDERS = DATA / "renders"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ASSET_RE = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")
JOB_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
ASSET_EXT = {".glb", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".png", ".jpg", ".jpeg"}
MAX_BODY = 20 * 1024 * 1024
MAX_ASSET = 300 * 1024 * 1024
MAX_FRAME = 60 * 1024 * 1024
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("audio/mp4", ".m4a")


def find_ffmpeg():
    for c in (os.environ.get("MINIMAYA_FFMPEG"), shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


class Handler(SimpleHTTPRequestHandler):
    server_version = "MiniMaya/" + VERSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        if "/api/render/" in (self.path or "") and " 200 " in (fmt % args):
            return
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
        return SCENES / (name + ".json") if NAME_RE.match(name) else None

    def asset_path(self, name):
        if not ASSET_RE.match(name) or name.startswith(".") or Path(name).suffix.lower() not in ASSET_EXT:
            return None
        return ASSETS / name

    def route(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            return None, path
        return [unquote(p) for p in path[len("/api/"):].split("/") if p], path

    def read_to_file(self, dest, limit):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > limit:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        left = length
        with open(tmp, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        if left:
            tmp.unlink(missing_ok=True)
            return False
        os.replace(tmp, dest)
        return True

    def send_media(self, base, name):
        p = (base / name).resolve()
        if base.resolve() not in p.parents or not p.is_file():
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        size = p.stat().st_size
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        start, end = 0, size - 1
        rng = self.headers.get("Range")
        m = re.match(r"bytes=(\d*)-(\d*)$", rng or "")
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            end = min(end, size - 1)
            if start > end:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.end_headers()
                return
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        else:
            self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(p, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_HEAD(self):
        _, path = self.route()
        if path.startswith("/media/"):
            return self.do_GET()
        return super().do_HEAD()

    def do_GET(self):
        parts, path = self.route()
        if parts is None:
            if path.startswith("/media/assets/"):
                return self.send_media(ASSETS, unquote(path[len("/media/assets/"):]))
            if path.startswith("/media/renders/"):
                return self.send_media(RENDERS, unquote(path[len("/media/renders/"):]))
            blocked = ("/data", "/logs", "/.git", "/server.py", "/install.sh", "/run.sh", "/uninstall.sh", "/ctl.sh", "/releases")
            if any(path.startswith(b) for b in blocked):
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return super().do_GET()
        if parts == ["health"]:
            return self.send_json(HTTPStatus.OK, {"ok": True, "app": "minimaya", "version": VERSION, "ffmpeg": bool(find_ffmpeg())})
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
        if parts == ["assets"]:
            items = [{"name": f.name, "size": f.stat().st_size} for f in sorted(ASSETS.glob("*")) if f.is_file() and not f.name.endswith(".part")]
            return self.send_json(HTTPStatus.OK, {"assets": items})
        if parts == ["renders"]:
            items = [{"name": f.name, "size": f.stat().st_size, "url": "media/renders/" + f.name, "modified": f.stat().st_mtime} for f in RENDERS.glob("*.mp4")]
            items.sort(key=lambda x: x["modified"], reverse=True)
            return self.send_json(HTTPStatus.OK, {"renders": items})
        return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})

    def do_PUT(self):
        parts, _ = self.route()
        if parts and len(parts) == 2 and parts[0] == "assets":
            p = self.asset_path(parts[1])
            if not p:
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Allowed files: glb, mp3, wav, m4a, aac, ogg, png, jpg"})
            if not self.read_to_file(p, MAX_ASSET):
                return self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "File is empty or larger than 300 MB"})
            return self.send_json(HTTPStatus.OK, {"ok": True, "name": p.name, "url": "media/assets/" + p.name})
        if parts and len(parts) == 3 and parts[0] == "render" and JOB_RE.match(parts[1]) and parts[2].isdigit():
            dest = RENDERS / parts[1] / "frames" / ("%05d.png" % int(parts[2]))
            if not self.read_to_file(dest, MAX_FRAME):
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Frame is empty or too large"})
            return self.send_json(HTTPStatus.OK, {"ok": True})
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

    def do_POST(self):
        parts, _ = self.route()
        if not parts or len(parts) != 3 or parts[0] != "render" or parts[2] != "finish" or not JOB_RE.match(parts[1]):
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
        ff = find_ffmpeg()
        if not ff:
            return self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "ffmpeg is not installed on the studio Mac (brew install ffmpeg)"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            opts = json.loads(self.rfile.read(length) or b"{}") if 0 < length < 65536 else {}
        except Exception:
            opts = {}
        jobdir = RENDERS / parts[1]
        frames = jobdir / "frames"
        n = len(list(frames.glob("*.png"))) if frames.exists() else 0
        if n == 0:
            return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "No frames were uploaded for this render"})
        fps = max(1, min(120, int(opts.get("fps") or 24)))
        name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(opts.get("name") or parts[1]))[:90] or parts[1]
        out = RENDERS / (name + ".mp4")
        cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames / "%05d.png")]
        audio = opts.get("audio")
        ap = self.asset_path(audio) if isinstance(audio, str) else None
        dur = n / fps
        if ap and ap.exists():
            start = float(opts.get("audioStart") or 0)
            vol = max(0.0, min(2.0, float(opts.get("volume") if opts.get("volume") is not None else 1)))
            if start < 0:
                cmd += ["-ss", "%.3f" % (-start)]
            cmd += ["-i", str(ap)]
            af = []
            if start > 0:
                ms = int(round(start * 1000))
                af.append("adelay=%d|%d" % (ms, ms))
            af += ["volume=%.3f" % vol, "apad"]
            cmd += ["-map", "0:v:0", "-map", "1:a:0", "-af", ",".join(af), "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-t", "%.3f" % dur, "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        except subprocess.TimeoutExpired:
            return self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "ffmpeg took longer than an hour"})
        if r.returncode != 0 or not out.exists():
            return self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "ffmpeg failed: " + (r.stderr or "").strip()[-400:]})
        shutil.rmtree(jobdir, ignore_errors=True)
        print("%s rendered %s (%d frames, %.1fs encode)" % (time.strftime("%Y-%m-%d %H:%M:%S"), out.name, n, time.time() - t0), flush=True)
        return self.send_json(HTTPStatus.OK, {"ok": True, "name": name, "url": "media/renders/" + out.name, "size": out.stat().st_size, "path": str(out), "frames": n})

    def do_DELETE(self):
        parts, _ = self.route()
        if parts and len(parts) == 2 and parts[0] == "render" and JOB_RE.match(parts[1]):
            shutil.rmtree(RENDERS / parts[1], ignore_errors=True)
            return self.send_json(HTTPStatus.OK, {"ok": True})
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
    for d in (SCENES, ASSETS, RENDERS):
        d.mkdir(parents=True, exist_ok=True)
    for stale in RENDERS.glob("job_*"):
        if stale.is_dir() and time.time() - stale.stat().st_mtime > 86400:
            shutil.rmtree(stale, ignore_errors=True)
    httpd = ThreadingHTTPServer((a.host, a.port), Handler)
    print("Mini Maya Studio %s on http://%s:%d  (data: %s, ffmpeg: %s)" % (VERSION, a.host, a.port, DATA, find_ffmpeg() or "not found"), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
