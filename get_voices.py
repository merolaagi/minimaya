#!/usr/bin/env python3
"""Download Piper voices listed in voices.txt into a folder. Lines are full voice names (ne_NP-google-medium) or language codes (ne_NP)."""
import json
import subprocess
import sys
from pathlib import Path

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
here = Path(__file__).resolve().parent
dest = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "data" / "voices"
dest.mkdir(parents=True, exist_ok=True)
wanted = [l.strip() for l in (here / "voices.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]


def fetch(url, path):
    tmp = path.with_name(path.name + ".part")
    r = subprocess.run(["curl", "-fsSL", "--retry", "2", "-o", str(tmp), url])
    if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
        tmp.replace(path)
        return True
    tmp.unlink(missing_ok=True)
    return False


catalog = {}
cat_file = dest / "voices.json"
if fetch(BASE + "voices.json?download=true", cat_file):
    try:
        catalog = json.loads(cat_file.read_text())
    except Exception:
        catalog = {}

names = []
for w in wanted:
    if "-" in w:
        names.append(w)
    else:
        found = sorted((k for k, v in catalog.items() if v.get("language", {}).get("code") == w),
                       key=lambda k: {"medium": 0, "high": 1, "low": 2, "x_low": 3}.get(catalog[k].get("quality"), 4))
        if not found:
            print("  no Piper voice found for %s" % w)
        names += found[:2]

ok = 0
for name in dict.fromkeys(names):
    if (dest / (name + ".onnx")).exists():
        ok += 1
        continue
    meta = catalog.get(name)
    if meta:
        files = [f for f in meta.get("files", {}) if f.endswith(".onnx") or f.endswith(".onnx.json")]
        urls = {Path(f).name: BASE + f + "?download=true" for f in files}
    else:
        lang = name.split("-")[0]
        fam = lang.split("_")[0]
        _, vname, q = name.split("-", 2) if name.count("-") >= 2 else (None, None, None)
        if not vname:
            print("  skipped %s (unknown name)" % name)
            continue
        p = "%s/%s/%s/%s/%s" % (fam, lang, vname, q, name)
        urls = {name + ".onnx": BASE + p + ".onnx?download=true", name + ".onnx.json": BASE + p + ".onnx.json?download=true"}
    if all(fetch(u, dest / fn) for fn, u in sorted(urls.items(), key=lambda x: x[0].endswith(".onnx"))):
        print("  voice %s" % name)
        ok += 1
    else:
        print("  could not download %s" % name)
        for fn in urls:
            (dest / fn).unlink(missing_ok=True)
print("%d Piper voice(s) ready in %s" % (ok, dest))
