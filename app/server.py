#!/usr/bin/env python3
"""SENTINEL lab server.

Standard library only. Serves the GUI and a small JSON API over content/cases/.
Binds to 127.0.0.1 only. Never executes anything found in evidence.
"""
import json
import re
import shutil
import subprocess
import sys
import threading
import traceback
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

APP = Path(__file__).resolve().parent
ROOT = APP.parent
# Everything authored (cases, campaign, tutorial, templates) lives under content/.
CONTENT = ROOT / "content"
CASES = CONTENT / "cases"
CAMPAIGN = CONTENT / "campaign.json"
LIBRARY = CONTENT / "library.json"      # standalone cases you can pick in any order
TEMPLATES = CONTENT / "templates"
# Tutorial: a read-only practice template, copied into a throwaway workspace.
# It is never a campaign chapter, so it can't change XP, rank or real cases.
TUTORIAL_ID = "tutorial"
TUTORIAL_TEMPLATE = CONTENT / "tutorial" / "practice"
TUTORIAL_WORK = CONTENT / "tutorial" / "workspace"
STATIC = APP / "static"
CATALOG = APP / "eventids.json"   # event labels, IOC field types, column fields: edit to support new log sources
DEFAULT_COLUMNS = {"user": ["User"], "image": ["Image"], "cmd": ["CommandLine"], "target": ["TargetFilename"],
                   "guid": ["ProcessGuid"], "pguid": ["ParentProcessGuid"], "pimage": ["ParentImage"]}
HOST, PORT = "127.0.0.1", 8765

CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
EDITABLE = {"worksheet.md", "report.md"}
DOCS = {"bookmarks", "iocs", "tree"}          # JSON lists the GUI may replace wholesale
STATUSES = ["New", "Triage", "Investigating", "Containment", "Resolved"]
ACTIVITY_TYPES = {"comment", "status", "evidence", "ioc", "tree", "playbook", "hint", "file", "case"}
MAX_BODY = 2_000_000
MAX_EVENTS_FILE = 200_000_000
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
}
_lock = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ---------- case helpers ----------

def reset_tutorial():
    """Recreate the practice workspace from the template (fresh start)."""
    if TUTORIAL_WORK.parent != TUTORIAL_TEMPLATE.parent or TUTORIAL_WORK.name != "workspace":
        raise RuntimeError("unexpected tutorial workspace path")
    if TUTORIAL_WORK.exists():
        shutil.rmtree(TUTORIAL_WORK)
    shutil.copytree(TUTORIAL_TEMPLATE, TUTORIAL_WORK)
    # The tour introduces the briefing itself, so don't pop it up on open.
    write_json(TUTORIAL_WORK / "state.json", {"story_seen": True})


def case_dir(cid):
    if cid == TUTORIAL_ID:
        if not (TUTORIAL_WORK / "brief.md").is_file() and (TUTORIAL_TEMPLATE / "brief.md").is_file():
            reset_tutorial()
        return TUTORIAL_WORK if (TUTORIAL_WORK / "brief.md").is_file() else None
    if not CASE_ID_RE.match(cid):
        return None
    d = CASES / cid
    return d if (d / "brief.md").is_file() else None


def read_text(path, default=""):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def title_of(md, fallback):
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def meta_of(md):
    for line in md.splitlines():
        if line.startswith("**Difficulty:**"):
            return line.replace("**", "").strip()
    return ""


def field_of(md, name):
    m = re.search(rf"\*\*{name}:\*\*\s*([^·\n]+)", md)
    return m.group(1).strip() if m else None


def steps_of(md):
    """Numbered items under '## Guided steps' (first line of each item only)."""
    steps, inside = [], False
    for line in md.splitlines():
        if line.startswith("## "):
            inside = line.strip().lower() == "## guided steps"
            continue
        if inside:
            m = re.match(r"^\d+\.\s+(.*)", line)
            if m:
                steps.append(m.group(1))
    return steps


def state_of(d):
    st = {"submitted": False, "steps": [], "hints": [], "status": "New", "opened_at": None,
          "story_seen": False, "rubric": [], "score": None, "grade": None}
    st.update(read_json(d / "state.json", {}))
    return st


def log_activity(d, kind, text):
    entry = {"t": now(), "type": kind, "text": text}
    acts = read_json(d / "activity.json", [])
    acts.append(entry)
    write_json(d / "activity.json", acts)
    return entry


def ensure_jsonl(d):
    """Convert any .evtx without a matching .jsonl, using chainsaw if installed."""
    notes = []
    for evtx in sorted((d / "data").glob("*.evtx")):
        out = evtx.with_suffix(".jsonl")
        if out.exists():
            continue
        if not shutil.which("chainsaw"):
            notes.append(f"{evtx.name}: chainsaw not installed, cannot convert")
            continue
        r = subprocess.run(["chainsaw", "dump", str(evtx), "--jsonl", "-o", str(out), "-q"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            notes.append(f"{evtx.name}: conversion failed: {r.stderr.strip()[:300]}")
    return notes


def first(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "-"):
            return v
    return None


def scalar(v):
    if isinstance(v, dict):
        return v.get("#text", v.get("value"))
    return v


def flat_userdata(ud, out=None):
    """Leaf fields of a UserData block (skipping XML *_attributes), for the derived columns only."""
    out = {} if out is None else out
    for k, v in ud.items():
        if k.endswith("_attributes"):
            continue
        if isinstance(v, dict):
            flat_userdata(v, out)
        else:
            out.setdefault(k, v)
    return out


def catalog():
    return read_json(CATALOG, {"channels": [], "ioc_types": {}, "columns": DEFAULT_COLUMNS})


def normalize(raw, source, line_no, columns=None):
    """Derive display fields. Raw record is always kept unchanged alongside."""
    ev = raw.get("Event") if isinstance(raw, dict) else None
    if not isinstance(ev, dict):
        raise ValueError("no 'Event' object (expected chainsaw/EVTX JSON)")
    sysd = ev.get("System") or {}
    ed = ev.get("EventData") or {}
    if not isinstance(ed, dict):
        ed = {}
    if not ed and isinstance(ev.get("UserData"), dict):
        ed = flat_userdata(ev["UserData"])   # e.g. Program-Compatibility-Assistant events

    time, time_src = ed.get("UtcTime"), "EventData.UtcTime"
    if not time:
        time = (sysd.get("TimeCreated_attributes") or {}).get("SystemTime")
        time_src = "System.TimeCreated.SystemTime"
    if time:
        time = str(time).replace("T", " ").rstrip("Z")

    return {
        "key": f"{source}:{line_no}",
        "source": source,
        "line": line_no,
        "record": scalar(sysd.get("EventRecordID")),
        "eid": scalar(sysd.get("EventID")),
        "channel": sysd.get("Channel"),
        "provider": (sysd.get("Provider_attributes") or {}).get("Name"),
        "host": sysd.get("Computer"),
        "time": time,
        "time_src": time_src if time else None,
        **{col: first(ed, *keys) for col, keys in {**DEFAULT_COLUMNS, **(columns or catalog().get("columns", {}))}.items()},
        "raw": raw,
    }


def load_events(d):
    notes = ensure_jsonl(d)
    events, errors = [], []
    columns = catalog().get("columns", {})
    for f in sorted((d / "data").glob("*.jsonl")):
        if f.stat().st_size > MAX_EVENTS_FILE:
            errors.append(f"{f.name}: larger than {MAX_EVENTS_FILE // 1_000_000} MB, skipped")
            continue
        with f.open(encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    events.append(normalize(json.loads(line), f.name, n, columns))
                except (json.JSONDecodeError, ValueError) as e:
                    errors.append(f"{f.name} line {n}: {e}")
    return events, notes + errors


# ---------- campaign ----------

def campaign():
    return read_json(CAMPAIGN, {"company": "", "analyst": "Analyst", "ranks": [{"xp": 0, "title": "Analyst"}], "chapters": []})


def library():
    """Library entries whose case folder exists and that aren't also campaign chapters (each case once)."""
    chapters = {c.get("case") for c in campaign().get("chapters", [])}
    out, seen = [], set()
    for entry in read_json(LIBRARY, {"cases": []}).get("cases", []):
        cid = entry.get("case") if isinstance(entry, dict) else None
        d = case_dir(cid) if isinstance(cid, str) else None
        if d and cid not in chapters and cid not in seen:   # a duplicate entry would count its XP twice
            seen.add(cid)
            out.append((entry, d))
    return out


def library_listing():
    """What the Case library shows: title and description, never anything from private/."""
    items = []
    for entry, d in library():
        brief = read_text(d / "brief.md")
        st = state_of(d)
        status = "completed" if st["submitted"] else ("in-progress" if st["opened_at"] else "new")
        items.append({
            "case": d.name, "title": re.sub(r"^Case\s+\d+:\s*", "", title_of(brief, d.name)),
            "teaser": entry.get("teaser", ""), "difficulty": field_of(brief, "Difficulty") or "",
            "severity": field_of(brief, "Severity") or "Medium", "budget": field_of(brief, "Time budget") or "",
            "data": field_of(brief, "Data") or "", "status": status, "case_status": st["status"],
            "score": st["score"], "grade": st["grade"],
        })
    return items


def rank_for(xp, ranks):
    cur = ranks[0]
    nxt = None
    for r in ranks:
        if xp >= r["xp"]:
            cur = r
        elif nxt is None:
            nxt = r
    return cur, nxt


def profile():
    camp = campaign()
    chapters, xp, prev_done = [], 0, True
    for ch in camp["chapters"]:
        d = case_dir(ch["case"]) if ch.get("case") else None
        st = state_of(d) if d else None
        done = bool(st and st["submitted"])
        if st and st["score"] is not None:
            xp += st["score"]
        status = "coming-soon" if not d else ("completed" if done else ("available" if prev_done else "locked"))
        chapters.append({**ch, "status": status, "score": st["score"] if st else None,
                         "grade": st["grade"] if st else None, "case_status": st["status"] if st else None})
        prev_done = done
    closed = sum(1 for c in chapters if c["status"] == "completed")
    for _, d in library():                  # library cases earn XP too
        st = state_of(d)
        xp += st["score"] or 0
        closed += bool(st["submitted"])
    cur, nxt = rank_for(xp, camp["ranks"])
    return {"company": camp["company"], "tagline": camp.get("tagline", ""), "analyst": camp["analyst"],
            "xp": xp, "rank": cur, "next_rank": nxt, "chapters": chapters, "closed": closed}


def chapter_of(cid):
    return next((c for c in profile()["chapters"] if c.get("case") == cid), None)


def unlocked(cid):
    ch = chapter_of(cid)
    return ch is None or ch["status"] in ("available", "completed")


def grade_for(score, grades):
    return next((g for floor, g in grades if score >= floor), grades[-1][1])


def indices(value, limit):
    """A client-sent list of item numbers, kept only if each is a real index below limit (no bools,
    no duplicates), so a hint or rubric item can't be counted twice or out of range."""
    if not isinstance(value, list):
        return None
    return sorted({i for i in value if type(i) is int and 0 <= i < limit})


def json_object(body):
    data = json.loads(body or "{}")
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def debrief_text(d, grade):
    db = read_json(d / "private" / "debrief.json", None)
    if not db:
        return ""
    return "\n\n".join(x for x in (db.get("common", ""), db.get("by_grade", {}).get(grade, ""), db.get("next", "")) if x)


def case_summary(d):
    brief = read_text(d / "brief.md")
    st = state_of(d)
    return {"id": TUTORIAL_ID if d == TUTORIAL_WORK else d.name, "title": title_of(brief, d.name), "meta": meta_of(brief),
            "severity": field_of(brief, "Severity") or "Medium",
            "status": st["status"], "submitted": st["submitted"]}


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "Sentinel/0.2"

    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if not isinstance(body, (bytes, str)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def error(self, code, msg):
        self.send(code, {"error": msg})

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n < 0:
            raise ValueError("bad Content-Length")       # read(-1) would block until the client hangs up
        if n > MAX_BODY:
            raise ValueError("request too large")
        return self.rfile.read(n).decode("utf-8")

    def same_origin(self):
        # Reject writes from other websites open in the browser.
        origin = self.headers.get("Origin")
        return origin in (None, f"http://{HOST}:{PORT}", f"http://localhost:{PORT}")

    def local_host(self):
        # A website that re-points its own domain at 127.0.0.1 (DNS rebinding) could otherwise read the API.
        host = self.headers.get("Host")
        return host in (None, f"{HOST}:{PORT}", f"localhost:{PORT}")

    def route(self):
        return [unquote(p) for p in urlparse(self.path).path.strip("/").split("/") if p]

    def guarded(self, fn, *args):
        """Run a handler; an unexpected error becomes a JSON 500 (with the traceback in the terminal),
        not a dropped connection the browser can't explain."""
        try:
            return fn(*args)
        except (BrokenPipeError, ConnectionResetError):
            return                                        # the browser went away mid-reply: nobody to tell
        except Exception:
            traceback.print_exc()
            return self.error(500, "internal error: see the terminal running SENTINEL")

    # -- GET --
    def do_GET(self):
        self.guarded(self.get)

    def get(self):
        if not self.local_host():
            return self.error(403, "unexpected Host header")
        p = self.route()
        if not p or p[0] != "api":
            return self.static(p)
        if p == ["api", "catalog"]:
            return self.send(200, catalog())
        if p == ["api", "library"]:
            return self.send(200, library_listing())
        if p == ["api", "profile"]:
            return self.send(200, profile())
        if p == ["api", "cases"]:
            dirs = sorted(CASES.iterdir()) if CASES.is_dir() else []
            return self.send(200, [case_summary(d) for d in dirs if case_dir(d.name)])
        if len(p) >= 3 and p[1] == "cases":
            d = case_dir(p[2])
            if not d:
                return self.error(404, "no such case")
            sub = p[3] if len(p) > 3 else None
            if not unlocked(d.name):
                return self.error(403, "this chapter is locked: finish the previous one first")
            if sub is None:
                with _lock:
                    st = state_of(d)
                    if not st["opened_at"]:
                        st["opened_at"] = now()
                        write_json(d / "state.json", st)
                        log_activity(d, "case", "Case opened")
                brief = read_text(d / "brief.md")
                return self.send(200, {
                    **case_summary(d), "brief": brief, "steps": steps_of(brief),
                    "hints": read_text(d / "hints.md"),
                    "worksheet": read_text(d / "worksheet.md"), "report": read_text(d / "report.md"),
                    "template_report": read_text(TEMPLATES / "report.md"),
                    "state": st, "statuses": STATUSES,
                    "bookmarks": read_json(d / "bookmarks.json", []),
                    "iocs": read_json(d / "iocs.json", []),
                    "tree": read_json(d / "tree.json", []),
                    "activity": read_json(d / "activity.json", []),
                    "has_answer_key": (d / "private" / "answer-key.md").is_file(),
                    "story": read_text(d / "story.md"),
                    "chapter": chapter_of(d.name), "profile": profile(),
                    "tutorial": d == TUTORIAL_WORK,
                })
            if sub == "events":
                events, errors = load_events(d)
                return self.send(200, {"events": events, "errors": errors})
            if sub == "answer":
                if not state_of(d)["submitted"]:
                    return self.error(403, "submit your report first")
                return self.send(200, {"answer": read_text(d / "private" / "answer-key.md")})
            if sub == "rubric":
                st = state_of(d)
                if not st["submitted"]:
                    return self.error(403, "submit your report first")
                rb = read_json(d / "private" / "rubric.json", {"items": [], "hint_penalty": 0, "grades": [[0, "-"]]})
                return self.send(200, {**rb, "checked": st["rubric"], "hints_used": len(st["hints"]),
                                       "score": st["score"], "grade": st["grade"]})
            if sub == "debrief":
                st = state_of(d)
                if st["score"] is None:
                    return self.error(403, "score your report first")
                return self.send(200, {"debrief": debrief_text(d, st["grade"]), "score": st["score"], "grade": st["grade"]})
        return self.error(404, "not found")

    def static(self, parts):
        rel = "/".join(parts[1:]) if parts and parts[0] == "static" else "index.html"
        f = (STATIC / rel).resolve()
        if STATIC not in f.parents or not f.is_file():
            return self.error(404, "not found")
        self.send(200, f.read_bytes(), MIME.get(f.suffix, "application/octet-stream"))

    # -- PUT / POST --
    def do_PUT(self):
        self.guarded(self.write, "PUT")

    def do_POST(self):
        self.guarded(self.write, "POST")

    def write(self, method):
        if not self.local_host():
            return self.error(403, "unexpected Host header")
        if not self.same_origin():
            return self.error(403, "cross-origin write refused")
        p = self.route()
        if method == "POST" and p == ["api", "tutorial", "reset"]:
            with _lock:
                reset_tutorial()
            return self.send(200, {"ok": True})
        if len(p) < 4 or p[:2] != ["api", "cases"]:
            return self.error(404, "not found")
        d = case_dir(p[2])
        if not d:
            return self.error(404, "no such case")
        if not unlocked(d.name):
            return self.error(403, "this chapter is locked")
        try:
            body = self.body()
            with _lock:
                return self.write_case(method, d, p[3:], body)
        except ValueError as e:  # includes JSONDecodeError
            return self.error(400, str(e))

    def write_case(self, method, d, p, body):
        sub = p[0]
        if method == "PUT" and sub == "file" and len(p) == 2 and p[1] in EDITABLE:
            (d / p[1]).write_text(body, encoding="utf-8")
            return self.send(200, {"ok": True})
        if method == "PUT" and sub == "doc" and len(p) == 2 and p[1] in DOCS:
            data = json.loads(body or "[]")
            if not isinstance(data, list):
                return self.error(400, "expected a list")
            write_json(d / f"{p[1]}.json", data)
            return self.send(200, {"ok": True})
        if method == "PUT" and sub == "state":
            incoming = json_object(body)
            st = state_of(d)
            # 'submitted' can only be set through /submit, never via state updates.
            limits = {"steps": len(steps_of(read_text(d / "brief.md"))), "hints": read_text(d / "hints.md").count("<details")}
            for k, limit in limits.items():
                ok = indices(incoming.get(k), limit)
                if ok is not None:
                    st[k] = ok
            if incoming.get("story_seen") is True:
                st["story_seen"] = True
            if incoming.get("status") in STATUSES and incoming["status"] != st["status"]:
                log_activity(d, "status", f"Status: {st['status']} → {incoming['status']}")
                st["status"] = incoming["status"]
            write_json(d / "state.json", st)
            return self.send(200, {"state": st, "activity": read_json(d / "activity.json", [])})
        if method == "POST" and sub == "activity":
            incoming = json_object(body)
            kind, text = incoming.get("type"), str(incoming.get("text") or "").strip()[:4000]
            if kind not in ACTIVITY_TYPES or not text:
                return self.error(400, "bad activity entry")
            return self.send(200, log_activity(d, kind, text))
        if method == "POST" and sub == "submit":
            st = state_of(d)
            st["submitted"] = True
            write_json(d / "state.json", st)
            log_activity(d, "case", "Report submitted, answer key unlocked")
            return self.send(200, {"answer": read_text(d / "private" / "answer-key.md"),
                                   "activity": read_json(d / "activity.json", [])})
        if method == "POST" and sub == "score":
            st = state_of(d)
            if not st["submitted"]:
                return self.error(403, "submit your report first")
            rb = read_json(d / "private" / "rubric.json", None)
            if not rb:
                return self.error(404, "this case has no rubric")
            incoming = json_object(body)
            checked = indices(incoming.get("rubric", []), len(rb["items"])) or []
            before = profile()
            earned = sum(rb["items"][i]["points"] for i in checked)
            penalty = len(st["hints"]) * rb.get("hint_penalty", 0)
            score = max(0, earned - penalty)
            first_time = st["score"] is None
            st.update({"rubric": checked, "score": score, "grade": grade_for(score, rb["grades"])})
            write_json(d / "state.json", st)
            after = profile()
            log_activity(d, "case", f"{'Scored' if first_time else 'Re-scored'}: {score} pts, grade {st['grade']}"
                         + (f" · Promoted to {after['rank']['title']}" if after["rank"] != before["rank"] else ""))
            return self.send(200, {"score": score, "grade": st["grade"], "earned": earned, "penalty": penalty,
                                   "xp_before": before["xp"], "xp_after": after["xp"],
                                   "rank_before": before["rank"], "rank_after": after["rank"], "next_rank": after["next_rank"],
                                   "debrief": debrief_text(d, st["grade"]),
                                   "activity": read_json(d / "activity.json", [])})
        if method == "POST" and sub == "reset":
            st = state_of(d)
            st.update({"submitted": False, "steps": [], "hints": [], "rubric": [], "score": None, "grade": None})
            write_json(d / "state.json", st)
            log_activity(d, "case", "Progress reset, answer key hidden")
            return self.send(200, {"state": st, "activity": read_json(d / "activity.json", [])})
        return self.error(404, "not found")


def main():
    global PORT
    if "--port" in sys.argv:
        PORT = int(sys.argv[sys.argv.index("--port") + 1])
    try:
        srv = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        print(f"Port {PORT} is busy. SENTINEL may already be running: http://{HOST}:{PORT}")
        if "--no-browser" not in sys.argv:
            webbrowser.open(f"http://{HOST}:{PORT}")
        return
    url = f"http://{HOST}:{PORT}"
    print(f"SENTINEL running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
