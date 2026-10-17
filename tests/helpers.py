"""Shared test helpers. Every test runs against a throwaway copy of the project, so your real
case files, progress and XP are never touched."""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))
import server  # noqa: E402
import case as casetool  # noqa: E402

CASE_ID = casetool.CASE_ID
# Project-relative paths, from the one place they're defined (app/server.py), so a sandbox copy
# can find the same files: sandbox.root / R_CASES etc.
R_CONTENT = server.CONTENT.relative_to(ROOT)
R_CASES = server.CASES.relative_to(ROOT)
R_CAMPAIGN = server.CAMPAIGN.relative_to(ROOT)
R_TEMPLATES = server.TEMPLATES.relative_to(ROOT)
R_TUTORIAL = server.TUTORIAL_TEMPLATE.relative_to(ROOT)
R_WORKSPACE = server.TUTORIAL_WORK.relative_to(ROOT)
SKIP = shutil.ignore_patterns(".git", ".venv", "__pycache__", "workspace", ".DS_Store")
# Per-user progress files that a real copy may contain; tests start every case fresh.
PROGRESS = ("state.json", "activity.json", "bookmarks.json", "iocs.json", "tree.json")


def case_dirs(only=None):
    """Every case folder in content/cases/ (plus the tutorial template), optionally just one id."""
    only = only or os.environ.get("SENTINEL_TEST_CASE") or None
    dirs = [p for p in sorted(server.CASES.iterdir()) if p.is_dir() and CASE_ID.match(p.name)]
    tut = server.TUTORIAL_TEMPLATE
    if tut.is_dir():
        dirs.append(tut)
    if only:
        dirs = [d for d in dirs if d.name == only or (only == "tutorial" and d == tut)]
    return dirs


def case_id(d):
    return "tutorial" if d == server.TUTORIAL_TEMPLATE or d == server.TUTORIAL_WORK else d.name


def campaign():
    return server.read_json(server.CAMPAIGN, {"chapters": []})


def published_ids():
    return {c["case"] for c in campaign().get("chapters", []) if c.get("case")}


def is_draft(d):
    """Unpublished cases may still have TODOs. `case publish` sets SENTINEL_STRICT to hold the case
    it's publishing to the full standard."""
    if os.environ.get("SENTINEL_STRICT"):
        return False
    return case_id(d) != "tutorial" and d.name not in published_ids()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Sandbox:
    """A copy of the project with its own server on a free port.

    unlock_all=True empties the campaign in the copy so every case is playable (a case that isn't a
    chapter is unlocked), which lets each case be tested on its own."""

    def __init__(self, unlock_all=True, fresh=True):
        self.unlock_all, self.fresh = unlock_all, fresh

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sentinel-test-"))
        self.root = self.tmp / "Sentinel"
        shutil.copytree(ROOT, self.root, ignore=SKIP)
        if self.fresh:
            for f in (self.root / R_CASES).glob("*/*"):
                if f.name in PROGRESS:
                    f.unlink()
            for t in ("worksheet.md", "report.md"):
                for d in (self.root / R_CASES).iterdir():
                    if (d / t).is_file():
                        shutil.copyfile(self.root / R_TEMPLATES / t, d / t)
        if self.unlock_all:
            camp = json.loads((self.root / R_CAMPAIGN).read_text())
            camp["chapters"] = []
            (self.root / R_CAMPAIGN).write_text(json.dumps(camp))
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.log = open(self.tmp / "server.log", "w")
        self.proc = subprocess.Popen([sys.executable, "app/server.py", "--port", str(self.port), "--no-browser"],
                                     cwd=self.root, stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                urllib.request.urlopen(self.url + "/api/profile", timeout=1)
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.05)
        else:
            raise RuntimeError("test server didn't start: " + (self.tmp / "server.log").read_text())
        return self

    def __exit__(self, *exc):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- tiny HTTP client ---
    def call(self, method, path, body=None, origin=None):
        data = None if body is None else (body if isinstance(body, (bytes, str)) else json.dumps(body))
        if isinstance(data, str):
            data = data.encode()
        req = urllib.request.Request(self.url + path, data=data, method=method)
        if origin:
            req.add_header("Origin", origin)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if r.headers.get_content_type() == "application/json" else raw)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw

    def get(self, path):
        return self.call("GET", path)

    def post(self, path, body=None, **kw):
        return self.call("POST", path, body if body is not None else "", **kw)

    def put(self, path, body, **kw):
        return self.call("PUT", path, body, **kw)


def fingerprint(root):
    """SHA-1 of every authored file under content/ (not the tutorial's throwaway workspace), for 'nothing changed' checks."""
    import hashlib
    out = {}
    work = Path(root) / R_WORKSPACE
    for f in sorted((Path(root) / R_CONTENT).rglob("*")):
        if f.is_file() and ".DS_Store" not in f.name and work not in f.parents:
            out[str(f.relative_to(root))] = hashlib.sha1(f.read_bytes()).hexdigest()
    return out


REC_REF = re.compile(r"\brec(?:ord)?s?\.?\s+#?(\d{1,12})\b", re.I)
LINE_REF = re.compile(r"\b([\w.-]+\.jsonl):(\d+)\b")
