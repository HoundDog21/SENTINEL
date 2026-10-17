#!/usr/bin/env python3
"""SENTINEL case pipeline: build a case from raw logs, check it, publish it to the campaign.

    ./sentinel case new 02-echoes --title "Echoes in the Scheduler" --data ~/dfir-data/x.evtx [more files…]
    ./sentinel case add-data 02-echoes more.zip
    ./sentinel case survey 02-echoes          # rewrite private/author-notes.md
    ./sentinel case check 02-echoes           # what's missing or broken
    ./sentinel case publish 02-echoes --chapter 2
    ./sentinel case list

Accepted inputs (each is converted to the one JSONL shape the app reads):
  .evtx                       Windows event log (converted with chainsaw)
  .jsonl / .json              chainsaw dump output, OTRF Security-Datasets / nxlog flat JSON,
                              or Winlogbeat/Elastic JSON (one per line, or a JSON array)
  .xml                        Windows event XML (wevtutil qe /f:xml, Splunk XmlWinEventLog)
  .zip                        any of the above inside a ZIP (e.g. OTRF downloads)

Nothing here runs, opens or follows anything found in the evidence. Standard library only
(plus chainsaw for .evtx). The app needs no code changes for a new case: event labels and
field types live in app/eventids.json.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import server  # noqa: E402  (reuse the app's own loader so "check" sees exactly what the app sees)

CASES, TEMPLATES, CAMPAIGN = server.CASES, server.TEMPLATES, server.CAMPAIGN   # paths are defined once, in app/server.py
CASE_ID = re.compile(r"^\d{2}-[a-z0-9][a-z0-9-]*$")
GRADES = [[90, "S"], [75, "A"], [60, "B"], [40, "C"], [0, "D"]]
MAX_MEMBER = 300_000_000
AUTHORED = ["brief.md", "story.md", "hints.md", "private/answer-key.md", "private/rubric.json", "private/debrief.json"]


class Fail(Exception):
    pass


# =====================================================================
# input formats → canonical record {"Event": {"System": {...}, "EventData"|"UserData": {...}}}
# (the shape `chainsaw dump --jsonl` produces, which app/server.py reads)
# =====================================================================

# Envelope fields in flat (OTRF / nxlog) records. Everything else is event data.
FLAT_ENVELOPE = {
    "SourceName", "ProviderName", "ProviderGuid", "EventID", "Version", "Level", "Task", "Opcode", "OpcodeValue",
    "Keywords", "Channel", "Hostname", "Computer", "host", "port", "tags", "@timestamp", "@version", "TimeCreated",
    "EventTime", "EventReceivedTime", "RecordNumber", "EventRecordID", "ProcessID", "ThreadID", "ExecutionProcessID",
    "ExecutionThreadID", "Category", "Domain", "AccountName", "UserID", "AccountType", "SourceModuleName",
    "SourceModuleType", "Severity", "SeverityValue", "ActivityID", "RelatedActivityID", "Message", "log", "agent", "ecs",
}
NXLOG_EVENTTYPES = {"INFO", "AUDIT_SUCCESS", "AUDIT_FAILURE", "WARNING", "ERROR", "VERBOSE", "CRITICAL"}


def as_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return v


def iso_z(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_time(s):
    """Parse the timestamp styles these datasets use. Returns (datetime, had_zone)."""
    if s is None:
        return None, False
    t = str(s).strip().replace(" ", "T", 1)
    zone = t.endswith("Z") or bool(re.search(r"[+-]\d\d:?\d\d$", t))
    t = t[:-1] + "+00:00" if t.endswith("Z") else t
    m = re.match(r"^(.*T\d\d:\d\d:\d\d)(\.\d+)?(.*)$", t)
    if m and m.group(2) and len(m.group(2)) > 7:            # trim >6 fractional digits for fromisoformat
        t = m.group(1) + m.group(2)[:7] + m.group(3)
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None, False
    return (dt if zone else dt.replace(tzinfo=timezone.utc)), zone


def system_block(eid, channel, computer, record, time_iso, provider=None, provider_guid=None, extra=None):
    sysd = {"Provider_attributes": {k: v for k, v in (("Name", provider), ("Guid", provider_guid)) if v},
            "EventID": as_int(eid), "Channel": channel, "Computer": computer}
    if time_iso:
        sysd["TimeCreated_attributes"] = {"SystemTime": time_iso}
    if record not in (None, ""):
        sysd["EventRecordID"] = as_int(record)
    sysd.update(extra or {})
    return sysd


def from_flat(r, offset):
    """OTRF Security-Datasets / nxlog style: every field at the top level."""
    ts = r.get("@timestamp")
    when, zoned = parse_time(ts) if ts else parse_time(r.get("EventTime") or r.get("TimeCreated"))
    if when is not None and not (ts or zoned):
        when = when - offset                                   # local wall clock → UTC
    extra = {}
    for k_out, k_in in (("Version", "Version"), ("Level", "Level"), ("Task", "Task"), ("Keywords", "Keywords")):
        if r.get(k_in) is not None:
            extra[k_out] = r[k_in]
    pid, tid = r.get("ExecutionProcessID", r.get("ProcessID")), r.get("ExecutionThreadID", r.get("ThreadID"))
    if pid is not None or tid is not None:
        extra["Execution_attributes"] = {k: as_int(v) for k, v in (("ProcessID", pid), ("ThreadID", tid)) if v is not None}
    host = r.get("Hostname") or r.get("Computer") or (r.get("host") if isinstance(r.get("host"), str) else None)
    sysd = system_block(r.get("EventID"), r.get("Channel"), host, r.get("RecordNumber", r.get("EventRecordID")),
                        iso_z(when) if when else None, r.get("SourceName") or r.get("ProviderName"), r.get("ProviderGuid"), extra)
    data = {k: v for k, v in r.items() if k not in FLAT_ENVELOPE
            and not (k == "EventType" and str(v).upper() in NXLOG_EVENTTYPES)}
    ev = {"System": sysd, "EventData": data}
    if r.get("Message"):
        ev["RenderingInfo"] = {"Message": r["Message"]}
    return {"Event": ev}


def from_winlogbeat(r):
    w = r["winlog"]
    when, _ = parse_time(r.get("@timestamp"))
    extra = {}
    pr = w.get("process") or {}
    if pr:
        extra["Execution_attributes"] = {"ProcessID": (pr.get("pid")), "ThreadID": (pr.get("thread") or {}).get("id")}
    sysd = system_block(w.get("event_id"), w.get("channel"), w.get("computer_name"), w.get("record_id"),
                        iso_z(when) if when else None, w.get("provider_name"), w.get("provider_guid"), extra)
    ev = {"System": sysd}
    if w.get("event_data"):
        ev["EventData"] = w["event_data"]
    elif w.get("user_data"):
        ev["UserData"] = w["user_data"]
    else:
        ev["EventData"] = {}
    if (r.get("message")):
        ev["RenderingInfo"] = {"Message": r["message"]}
    return {"Event": ev}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def xml_tree(el):
    """UserData-style nesting as dicts, attributes under <name>_attributes like chainsaw."""
    kids = list(el)
    if not kids:
        return (el.text or "").strip()
    out = {}
    for k in kids:
        name = local(k.tag)
        if k.attrib:
            out[name + "_attributes"] = {local(a): v for a, v in k.attrib.items()}
        out[name] = xml_tree(k)
    return out


def from_xml_event(el):
    sysd, ev = {}, {}
    sys_el = next((c for c in el if local(c.tag) == "System"), None)
    for c in (sys_el if sys_el is not None else []):
        name = local(c.tag)
        if c.attrib:
            sysd[name + "_attributes"] = {local(a): v for a, v in c.attrib.items()}
        text = (c.text or "").strip()
        sysd[name] = as_int(text) if name in ("EventID", "EventRecordID", "Version", "Level", "Task", "Opcode") else (text or None)
    for c in el:
        name = local(c.tag)
        if name == "EventData":
            data, unnamed = {}, []
            for d in c:
                if "Name" in d.attrib:
                    data[d.attrib["Name"]] = (d.text or "")
                else:
                    unnamed.append(d.text or "")
            if unnamed:
                data["Data"] = unnamed if len(unnamed) > 1 else unnamed[0]
            ev["EventData"] = data
        elif name == "UserData":
            ev["UserData"] = xml_tree(c)
        elif name == "RenderingInfo":
            ev["RenderingInfo"] = xml_tree(c)
    return {"Event": {"System": sysd, **ev}}


def kind_of(r):
    if isinstance(r, dict) and isinstance(r.get("Event"), dict) and isinstance(r["Event"].get("System"), dict):
        return "chainsaw"
    if isinstance(r, dict) and isinstance(r.get("winlog"), dict):
        return "winlogbeat"
    if isinstance(r, dict) and "EventID" in r and ("Channel" in r or "SourceName" in r):
        return "flat"
    return None


def infer_offset(records):
    """Flat datasets often stamp TimeCreated in the collector's local time. Learn the offset from
    Sysmon records that carry both TimeCreated and a true UtcTime. Returns (timedelta, note)."""
    deltas = Counter()
    for r in records:
        if r.get("@timestamp") or not r.get("UtcTime"):
            continue
        local_t, zl = parse_time(r.get("EventTime") or r.get("TimeCreated"))
        utc_t, _ = parse_time(r["UtcTime"])
        if local_t and utc_t and not zl:
            minutes = round((local_t - utc_t).total_seconds() / 900) * 15     # nearest 15 min
            deltas[minutes] += 1
    if not deltas:
        return timedelta(0), None
    minutes, n = deltas.most_common(1)[0]
    if minutes == 0:
        return timedelta(0), None
    sign = "+" if minutes > 0 else "-"
    note = (f"TimeCreated in this file is local time, UTC{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d} "
            f"(learned from {n} Sysmon record(s) with UtcTime). System times were converted to UTC.")
    if len(deltas) > 1:
        note += f" Offsets disagreed across records ({dict(deltas)} minutes); the most common was used."
    return timedelta(minutes=minutes), note


def records_from_json(text, name):
    text = text.lstrip("\ufeff")
    try:
        whole = json.loads(text)
        items = whole if isinstance(whole, list) else [whole]
    except json.JSONDecodeError:
        items = []
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise Fail(f"{name} line {n}: not JSON ({e})")
    return items


def convert_json_items(items, name, tz_hours):
    kinds = Counter(kind_of(r) for r in items)
    if None in kinds:
        bad = next(i for i, r in enumerate(items, 1) if kind_of(r) is None)
        raise Fail(f"{name}: record {bad} isn't a format I recognize (chainsaw, OTRF/nxlog flat JSON or Winlogbeat)")
    notes = []
    flat = [r for r in items if kind_of(r) == "flat"]
    offset = timedelta(0)
    if flat:
        if tz_hours is not None:
            offset = timedelta(hours=tz_hours)
            notes.append(f"TimeCreated treated as UTC{tz_hours:+g} (from --tz-offset) and converted to UTC.")
        else:
            offset, note = infer_offset(flat)
            if note:
                notes.append(note)
            elif not any(r.get("@timestamp") for r in flat):
                notes.append("No @timestamp and no way to learn a time zone: TimeCreated was assumed to be UTC. "
                             "Pass --tz-offset if you know better. Sysmon UtcTime fields are unaffected.")
    out = []
    for r in items:
        k = kind_of(r)
        out.append(r if k == "chainsaw" else from_winlogbeat(r) if k == "winlogbeat" else from_flat(r, offset))
    fmt = "+".join(sorted(kinds)) if len(kinds) > 1 else next(iter(kinds))
    return out, {"chainsaw": "chainsaw JSONL", "flat": "OTRF/nxlog flat JSON", "winlogbeat": "Winlogbeat JSON"}.get(fmt, fmt), notes


def convert_xml(data, name):
    head = data[:4096].decode("utf-8", "replace")
    if "<!DOCTYPE" in head or "<!ENTITY" in head:
        raise Fail(f"{name}: XML with a DOCTYPE/ENTITY declaration refused")
    text = data.decode("utf-8-sig", "replace").strip()
    # wevtutil emits bare <Event> elements one after another with no root: wrap them.
    text = re.sub(r"^<\?xml[^>]*\?>", "", text).strip()
    root = ET.fromstring(f"<Events>{text}</Events>")
    events = [el for el in root.iter() if local(el.tag) == "Event"]
    if not events:
        raise Fail(f"{name}: no <Event> elements found")
    return [from_xml_event(e) for e in events], "Windows event XML", []


def convert_evtx(path, name):
    exe = shutil.which("chainsaw")
    if not exe:
        raise Fail(f"{name}: converting .evtx needs chainsaw (brew install chainsaw), or convert it yourself and pass the .jsonl")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.jsonl"
        r = subprocess.run([exe, "dump", str(path), "--jsonl", "-o", str(out), "-q"], capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            raise Fail(f"{name}: chainsaw failed: {r.stderr.strip()[:300]}")
        items = records_from_json(out.read_text(encoding="utf-8", errors="replace"), name)
    return items, "EVTX (chainsaw dump)", []


def safe_stem(name):
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(name).stem).strip("-.") or "data"
    return stem[:80]


def ingest(path, tz_hours=None):
    """Yield (stem, original_name, original_bytes_or_path, records, format, notes) for one input path."""
    path = Path(path).expanduser()
    if not path.is_file():
        raise Fail(f"{path}: no such file")
    suffix = path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            members = [m for m in z.infolist() if not m.is_dir() and Path(m.filename).suffix.lower() in (".json", ".jsonl", ".evtx", ".xml")
                       and not Path(m.filename).name.startswith(".") and "__MACOSX" not in m.filename]
            if not members:
                raise Fail(f"{path.name}: no .json/.jsonl/.evtx/.xml files inside")
            for m in members:
                if m.file_size > MAX_MEMBER:
                    raise Fail(f"{path.name}: {m.filename} is larger than {MAX_MEMBER // 1_000_000} MB")
                data = z.read(m)                          # read into memory: never extract paths from the archive
                inner = Path(m.filename).name
                yield from ingest_bytes(inner, data, tz_hours, via=path.name)
        return
    yield from ingest_bytes(path.name, path.read_bytes(), tz_hours, via=None, src_path=path)


def ingest_bytes(name, data, tz_hours, via=None, src_path=None):
    suffix = Path(name).suffix.lower()
    if suffix == ".evtx":
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "in.evtx"
            tmp.write_bytes(data)
            recs, fmt, notes = convert_evtx(tmp, name)
    elif suffix in (".json", ".jsonl"):
        recs, fmt, notes = convert_json_items(records_from_json(data.decode("utf-8", "replace"), name), name, tz_hours)
    elif suffix == ".xml":
        recs, fmt, notes = convert_xml(data, name)
    else:
        raise Fail(f"{name}: unsupported file type (use .evtx, .json, .jsonl, .xml or .zip)")
    yield {"stem": safe_stem(name), "name": name, "via": via, "data": data, "records": recs, "format": fmt, "notes": notes,
           "sha256": hashlib.sha256(data).hexdigest()}


# =====================================================================
# writing a case
# =====================================================================

def case_path(cid, must_exist=True):
    if not CASE_ID.match(cid):
        raise Fail(f"case id '{cid}' should look like 02-echoes-in-the-scheduler (two digits, dash, lowercase words)")
    d = CASES / cid
    if must_exist and not d.is_dir():
        raise Fail(f"no case folder {d.relative_to(ROOT)}")
    return d


def meta_of(d):
    return server.read_json(d / "private" / "case.json", {"sources": []})


def add_data(d, paths, tz_hours=None):
    """Convert inputs into d/data/<stem>.jsonl, keep originals, verify every event loads in the app."""
    (d / "data" / "source").mkdir(parents=True, exist_ok=True)
    meta = meta_of(d)
    added = []
    cols = server.catalog().get("columns", {})
    for p in paths:
        for item in ingest(p, tz_hours):
            stem = item["stem"]
            n = 2
            while (d / "data" / f"{stem}.jsonl").exists():
                stem = f"{item['stem']}-{n}"
                n += 1
            out = d / "data" / f"{stem}.jsonl"
            lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in item["records"]]
            for i, line in enumerate(lines, 1):     # exactly what the app will do when it loads the case
                try:
                    server.normalize(json.loads(line), out.name, i, cols)
                except ValueError as e:
                    raise Fail(f"{item['name']} record {i}: the app couldn't read the converted event ({e})")
            out.write_text("\n".join(lines) + "\n", encoding="utf-8")
            if Path(item["name"]).suffix.lower() == ".evtx":
                orig = d / "data" / f"{stem}.evtx"            # app treats data/*.evtx as the original (gitignored)
            else:
                orig = d / "data" / "source" / (stem + Path(item["name"]).suffix.lower())
            orig.write_bytes(item["data"])
            src = {"file": f"data/{out.name}", "original": str(orig.relative_to(d)), "from": item["name"],
                   "via": item["via"], "sha256": item["sha256"], "format": item["format"], "events": len(lines),
                   "notes": item["notes"], "added": server.now()}
            meta["sources"].append(src)
            added.append(src)
            print(f"  + {src['file']}: {len(lines)} events from {item['name']}" + (f" (in {item['via']})" if item["via"] else "")
                  + f" [{item['format']}]")
            for note in item["notes"]:
                print(f"    note: {note}")
    server.write_json(d / "private" / "case.json", meta)
    return added


def load(d):
    events, errors = server.load_events(d)
    return events, errors


def label(e, cat):
    ch = str(e.get("channel") or "").lower()
    for c in cat.get("channels", []):
        if (c.get("exact") and ch == c["exact"].lower()) or (c.get("contains") and c["contains"].lower() in ch):
            lab = (c.get("ids") or {}).get(str(e.get("eid")))
            return c.get("name"), lab
    return None, None


def data_summary(events, cat):
    groups = defaultdict(set)
    for e in events:
        name, _ = label(e, cat)
        groups[name or e.get("channel") or "Unknown"].add(e.get("eid"))
    return " + ".join(f"{g} (Event ID{'s' if len(ids) > 1 else ''} {', '.join(str(i) for i in sorted(ids, key=lambda x: (0, x, "") if isinstance(x, int) else (1, 0, str(x))))})"
                      for g, ids in groups.items())


def survey_md(d, cid=None):
    """Author-only notes (private/): mechanical facts about the data to help write the brief and key."""
    events, errors = load(d)
    cat = server.catalog()
    meta = meta_of(d)
    L = [f"# Author notes: {cid or d.name}", "",
         "Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.", "",
         f"Generated {server.now()} by `tools/case.py survey`.", "", "## Sources", "",
         "| Case file | From | Format | Events | SHA-256 |", "|---|---|---|---|---|"]
    for s in meta.get("sources", []):
        L.append(f"| `{s['file']}` | {s['from']}{' in ' + s['via'] if s.get('via') else ''} | {s['format']} | {s['events']} | `{s['sha256'][:12]}…` |")
    for s in meta.get("sources", []):
        for n in s.get("notes", []):
            L.append(f"\n> **{s['file']}:** {n}")
    if errors:
        L += ["", "## Load problems", ""] + [f"- {x}" for x in errors]
    L += ["", "## Counts", "", "| Channel | Event ID | Label | Count |", "|---|---|---|---|"]
    counts = Counter((e.get("channel"), e.get("eid")) for e in events)
    unlabeled = []
    num_key = lambda v: (0, v, "") if isinstance(v, int) else (1, 0, str(v))
    for (ch, eid), n in sorted(counts.items(), key=lambda x: (str(x[0][0]), num_key(x[0][1]))):
        name, lab = label({"channel": ch, "eid": eid}, cat)
        if not lab:
            unlabeled.append((ch, eid))
        L.append(f"| {ch} | {eid} | {lab or '**no label**'} | {n} |")
    hosts = Counter(e.get("host") for e in events)
    users = Counter(e.get("user") for e in events if e.get("user"))
    L += ["", f"- **Events:** {len(events)}", f"- **Hosts:** {', '.join(f'`{h}` ({n})' for h, n in hosts.most_common())}",
          f"- **Users:** {', '.join(f'`{u}` ({n})' for u, n in users.most_common(10)) or 'none in the data'}"]
    by_ch = defaultdict(list)
    for e in events:
        by_ch[e.get("channel")].append(e)
    L += ["", "## Time and record IDs per channel", "", "| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |", "|---|---|---|---|---|"]
    for ch, evs in by_ch.items():
        times = sorted(e["time"] for e in evs if e.get("time"))
        recs = sorted({r for r in (as_int(e.get("record")) for e in evs) if isinstance(r, int)})
        if recs:
            missing = sorted(set(range(recs[0], recs[-1] + 1)) - set(recs))
            miss = (", ".join(map(str, missing[:20])) + (f" … ({len(missing)} total)" if len(missing) > 20 else "")) if missing else "none"
            rng = f"{recs[0]}–{recs[-1]}"
        else:
            rng, miss = "**none: cite by file:line**", "n/a"
        L.append(f"| {ch} | {times[0] if times else '?'} | {times[-1] if times else '?'} | {rng} | {miss} |")
    order = [e for e in events if e.get("time")]
    order.sort(key=lambda e: e["time"])
    recs_in_time = [(e.get("channel"), as_int(e.get("record"))) for e in order]
    swaps = sum(1 for ch in by_ch for a, b in zip([r for c, r in recs_in_time if c == ch and isinstance(r, int)],
                                                  [r for c, r in recs_in_time if c == ch and isinstance(r, int)][1:]) if b < a)
    L.append(f"\nRecord order vs time order: {swaps} place(s) where a later event has a lower record ID within its channel.")
    pcs = [e for e in order if e.get("guid") and e.get("pguid") and e.get("image")]
    if pcs:
        L += ["", "## Process-create style events (time order)", "", "| Time | Ref | Image | ProcessGuid | ParentProcessGuid | Parent image | Command line |", "|---|---|---|---|---|---|---|"]
        guids = {e["guid"] for e in pcs}
        for e in pcs[:200]:
            ref = f"rec {e['record']}" if e.get("record") not in (None, "") else f"{e['source']}:{e['line']}"
            cmd = (e.get("cmd") or "").replace("|", "\\|")
            L.append(f"| {e['time']} | {ref} | `{e['image']}` | `{e['guid']}` | `{e['pguid']}`{'' if e['pguid'] in guids else ' (no process-create event)'} | `{e.get('pimage') or ''}` | `{cmd[:160]}` |")
    if unlabeled:
        L += ["", "## Missing labels", "", "These channel/Event ID pairs have no label in `app/eventids.json`. Add them there (no code changes needed):", ""]
        L += [f"- `{ch}` · {eid}" for ch, eid in unlabeled]
    (d / "private" / "author-notes.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return events, unlabeled


def write_skeleton(d, cid, title, severity, difficulty, budget):
    events, _ = load(d)
    cat = server.catalog()
    meta = meta_of(d)
    num = cid[:2]
    first = min((e["time"] for e in events if e.get("time")), default="TODO")
    norec = any(e.get("record") in (None, "") for e in events)
    ev_rows = []
    for s in meta["sources"]:
        orig = s["original"]
        ev_rows.append(f"| `{orig}` | Original {s['format']} file (SHA-256 `{s['sha256'][:8]}…{s['sha256'][-6:]}`) |")
        ev_rows.append(f"| `{s['file']}` | Same {s['events']} events, one per line, in the format the app reads |")
    files = {
        "brief.md": f"""# Case {num}: {title}

**Difficulty:** {difficulty} · **Severity:** {severity} · **Data:** {data_summary(events, cat)} · **Time budget:** {budget}

## The alert

> **Client:** TODO: client name (and what kind of business)
>
> **{first[:16]} UTC**: TODO: which product raised what alert, on which host.
> **"TODO: alert name"**
>
> TODO: what the client believes, and what you've been handed.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
{chr(10).join(ev_rows)}
{chr(10) + "This dataset has **no EventRecordIDs**. Cite events by `file:line`, which the app shows for every event." + chr(10) if norec else ""}
## What you'll practice

- TODO

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with a reference for each one.

1. **Survey.** How many events are there? Which Event IDs and channels? What time range? Which host(s) and user(s)?
2. TODO: next step
3. **Assess.** Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown.
4. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an event reference behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
""",
        "story.md": f"""**From:** Priya Nandakumar, SOC Team Lead · Ironlantern Security
**To:** Cody
**Subject:** TODO: subject line

Cody,

TODO: the briefing. Set the scene, name the client and host, quote what the client claims (a claim, not evidence), and say what you want back. The story must never add evidence.

— Priya
""",
        "hints.md": f"""# Case {num}: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

TODO: a nudge, not the answer.
</details>
""",
        "private/answer-key.md": f"""# Case {num}: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** {"; ".join(f"`{s['from']}`" + (f" in `{s['via']}`" if s.get("via") else "") for s in meta["sources"])}. TODO: dataset name, author, and whether it's a lab recording.

## Survey

TODO (see `private/author-notes.md` for counts, time ranges and record gaps)

## Process tree

```text
TODO
```

## What happened (interpretation)

1. TODO

## Verdict

TODO

## IOCs

- TODO

## What you can't conclude from this data

- TODO

## Good next steps (for your recommendations)

- TODO

*Score yourself with the rubric panel above the answer key in SENTINEL.*
""",
    }
    for rel, text in files.items():
        (d / rel).write_text(text, encoding="utf-8")
    server.write_json(d / "private" / "rubric.json", {"hint_penalty": 3, "grades": GRADES,
                                                      "items": [{"points": 100, "text": "TODO: one checkable item per finding; points should total 100"}]})
    server.write_json(d / "private" / "debrief.json", {"from": "Priya Nandakumar, SOC Team Lead", "common": "TODO: what happened after the report landed",
                                                       "by_grade": {g: "TODO" for _, g in GRADES}, "next": "TODO: hook for the next chapter"})
    for t in ("worksheet.md", "report.md"):
        shutil.copyfile(TEMPLATES / t, d / t)


# =====================================================================
# checking
# =====================================================================

def check(d, quiet=False):
    errors, warns = [], []
    for rel in AUTHORED + ["worksheet.md", "report.md"]:
        if not (d / rel).is_file():
            errors.append(f"missing {rel}")
    brief = server.read_text(d / "brief.md")
    if brief:
        if not brief.lstrip().startswith("# "):
            errors.append("brief.md should start with a '# Case NN: Title' heading")
        if not server.steps_of(brief):
            errors.append("brief.md has no numbered list under '## Guided steps' (the Playbook is built from it)")
        if not server.field_of(brief, "Severity"):
            warns.append("brief.md has no **Severity:** field (the case bar will show Medium)")
    for rel in AUTHORED:
        text = server.read_text(d / rel)
        for n, line in enumerate(text.splitlines(), 1):
            if "TODO" in line:
                errors.append(f"{rel}:{n} still has a TODO")
                break
    if not server.read_text(d / "story.md").strip():
        warns.append("story.md is empty (no briefing message)")
    hints = server.read_text(d / "hints.md")
    if hints and "<details" not in hints:
        warns.append("hints.md has no <details> blocks, so hints can't be opened one at a time or counted")
    rb = server.read_json(d / "private" / "rubric.json", None)
    if (d / "private" / "rubric.json").is_file():
        if not isinstance(rb, dict):
            errors.append("private/rubric.json isn't valid JSON")
        else:
            items = rb.get("items")
            if not isinstance(items, list) or not items:
                errors.append("rubric.json needs a non-empty 'items' list")
            elif any(not isinstance(i, dict) or not isinstance(i.get("points"), int) or i["points"] <= 0 or not str(i.get("text", "")).strip() for i in items):
                errors.append("every rubric item needs positive integer 'points' and a 'text'")
            else:
                total = sum(i["points"] for i in items)
                if total != 100:
                    warns.append(f"rubric points total {total}, not 100")
            g = rb.get("grades")
            if not (isinstance(g, list) and g and all(isinstance(x, list) and len(x) == 2 for x in g)
                    and [x[0] for x in g] == sorted([x[0] for x in g], reverse=True) and g[-1][0] == 0):
                errors.append("rubric 'grades' must be [[floor, letter], …] from highest floor down to 0")
            if not isinstance(rb.get("hint_penalty", 0), int):
                errors.append("rubric 'hint_penalty' must be an integer")
    db = server.read_json(d / "private" / "debrief.json", None)
    if (d / "private" / "debrief.json").is_file():
        if not isinstance(db, dict):
            errors.append("private/debrief.json isn't valid JSON")
        else:
            letters = [x[1] for x in (rb or {}).get("grades", GRADES)] if isinstance(rb, dict) else []
            missing = [l for l in letters if not (db.get("by_grade") or {}).get(l)]
            if not db.get("common"):
                errors.append("debrief.json needs 'common' text")
            if missing:
                errors.append(f"debrief.json 'by_grade' has no text for grade(s) {', '.join(missing)}")
    if not list((d / "data").glob("*.jsonl")) and not list((d / "data").glob("*.evtx")):
        errors.append("no data: add some with `case add-data`")
    events, load_errors = load(d)
    errors += [f"data: {x}" for x in load_errors]
    if not events and not load_errors:
        errors.append("data loads but contains no events")
    cat = server.catalog()
    unl = sorted({(e.get("channel"), e.get("eid")) for e in events if not label(e, cat)[1]}, key=str)
    if unl:
        warns.append("no label in app/eventids.json for: " + ", ".join(f"{c} · {i}" for c, i in unl))
    notime = sum(1 for e in events if not e.get("time"))
    if notime:
        warns.append(f"{notime} event(s) have no timestamp")
    if not quiet:
        print(f"{d.name}: {len(events)} events, {len(errors)} error(s), {len(warns)} warning(s)")
        for x in errors:
            print(f"  ✗ {x}")
        for x in warns:
            print(f"  ! {x}")
        if not errors:
            print("  ✓ ready to publish")
    return errors, warns


# =====================================================================
# campaign
# =====================================================================

def run_case_tests(cid):
    """The publish gate: the case must pass its full test suite (content, API, and, when Playwright
    is installed, a browser playthrough), held to published standards."""
    if os.environ.get("SENTINEL_SKIP_PUBLISH_TESTS"):      # set only by the pipeline's own tests
        return
    print(f"Running the tests for {cid} (./sentinel test --case {cid} --strict)…")
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "run.py"), "--case", cid, "--strict", "--quiet"], cwd=ROOT)
    if r.returncode != 0:
        raise Fail(f"{cid} failed its tests (output above). Fix them, then publish again.")


def publish(d, chapter, title, teaser, difficulty, replace):
    errors, _ = check(d)
    if errors:
        raise Fail("fix the errors above before publishing")
    run_case_tests(d.name)
    camp = server.read_json(CAMPAIGN, None)
    if not isinstance(camp, dict):
        raise Fail(f"{CAMPAIGN.relative_to(ROOT)} is missing or invalid")
    chapters = camp.setdefault("chapters", [])
    for ch in chapters:
        if ch.get("case") == d.name and ch.get("n") != chapter:
            raise Fail(f"{d.name} is already Chapter {ch['n']}")
    ch = next((c for c in chapters if c.get("n") == chapter), None)
    if ch is None:
        nxt = max((c.get("n", 0) for c in chapters), default=0) + 1
        if chapter != nxt:
            raise Fail(f"there's no Chapter {chapter}; the next new chapter number is {nxt}")
        if not (title and teaser and difficulty):
            raise Fail("a new chapter needs --title, --teaser and --difficulty")
        ch = {"n": chapter, "case": None, "title": title, "teaser": teaser, "difficulty": difficulty}
        chapters.append(ch)
    old = ch.get("case")
    if old and old != d.name and not replace:
        raise Fail(f"Chapter {chapter} already plays {old}. Pass --replace to swap it (the old folder is left untouched).")
    ch["case"] = d.name
    for k, v in (("title", title), ("teaser", teaser), ("difficulty", difficulty)):
        if v:
            ch[k] = v
    server.write_json(CAMPAIGN, camp)
    print(f"Chapter {chapter}: \"{ch['title']}\" now plays {d.name}" + (f" (was {old})" if old and old != d.name else "")
          + ". Reload the app to see it.")


# =====================================================================
# CLI
# =====================================================================

def cmd_new(a):
    d = case_path(a.id, must_exist=False)
    if d.exists():
        raise Fail(f"{d.relative_to(ROOT)} already exists (use add-data to add files)")
    if not a.data:
        raise Fail("give at least one --data file")
    staging = Path(tempfile.mkdtemp(prefix=f".{a.id}-", dir=CASES))   # build aside, move into place only if it all worked
    try:
        (staging / "private").mkdir()
        print(f"Building {a.id}…")
        add_data(staging, a.data, a.tz_offset)
        write_skeleton(staging, a.id, a.title, a.severity, a.difficulty, a.budget)
        survey_md(staging, a.id)
        staging.rename(d)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    rel = d.relative_to(ROOT)
    print(f"""
Created {rel}/ with skeleton files. Next:
  1. Read {rel}/private/author-notes.md (data facts for you, never shown in the app)
  2. Fill in every TODO: brief.md, story.md, hints.md and private/answer-key.md, rubric.json, debrief.json
  3. ./sentinel case check {a.id}
  4. ./sentinel case publish {a.id} --chapter N""")


def cmd_add(a):
    d = case_path(a.id)
    add_data(d, a.files, a.tz_offset)
    survey_md(d)
    print(f"Updated private/author-notes.md. The brief's Evidence table isn't rewritten: add the new files to it yourself.")


def cmd_survey(a):
    d = case_path(a.id)
    events, unl = survey_md(d)
    print(f"Wrote {(d / 'private' / 'author-notes.md').relative_to(ROOT)} ({len(events)} events"
          + (f", {len(unl)} unlabeled Event ID(s)" if unl else "") + ")")


def cmd_check(a):
    ids = [a.id] if a.id else [p.name for p in sorted(CASES.iterdir()) if p.is_dir() and CASE_ID.match(p.name)]
    bad = 0
    for cid in ids:
        errors, _ = check(case_path(cid))
        bad += bool(errors)
    return 1 if bad else 0


def cmd_publish(a):
    publish(case_path(a.id), a.chapter, a.title, a.teaser, a.difficulty, a.replace)


def cmd_list(a):
    camp = server.read_json(CAMPAIGN, {"chapters": []})
    by_case = {c.get("case"): c for c in camp.get("chapters", []) if c.get("case")}
    print(f"{'Case':32} {'Chapter':28} Status")
    for p in sorted(CASES.iterdir()):
        if not (p.is_dir() and CASE_ID.match(p.name)):
            continue
        errors, warns = check(p, quiet=True)
        ch = by_case.get(p.name)
        chap = f"{ch['n']}: {ch['title']}" if ch else "draft (not published)"
        status = f"{len(errors)} error(s)" if errors else ("ready" if not ch else "live") + (f", {len(warns)} warning(s)" if warns else "")
        print(f"{p.name:32} {chap[:28]:28} {status}")
    for c in camp.get("chapters", []):
        if not c.get("case"):
            print(f"{'(no case yet)':32} {str(c['n']) + ': ' + c['title']:28.28} coming soon")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sentinel case", description="Build, check and publish SENTINEL cases.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="create a case from log files")
    n.add_argument("id", help="folder name, e.g. 02-echoes-in-the-scheduler")
    n.add_argument("--title", required=True)
    n.add_argument("--data", nargs="+", required=True, metavar="FILE", help=".evtx, .json(l), .xml or .zip")
    n.add_argument("--severity", default="Medium", choices=["Low", "Medium", "High", "Critical"])
    n.add_argument("--difficulty", default="Beginner")
    n.add_argument("--budget", default="1–2 hours", help="time budget shown in the brief")
    n.add_argument("--tz-offset", type=float, help="hours from UTC for local TimeCreated values in flat JSON (default: learn it)")
    n.set_defaults(fn=cmd_new)
    ad = sub.add_parser("add-data", help="add more log files to a case")
    ad.add_argument("id"); ad.add_argument("files", nargs="+")
    ad.add_argument("--tz-offset", type=float)
    ad.set_defaults(fn=cmd_add)
    sv = sub.add_parser("survey", help="rewrite private/author-notes.md")
    sv.add_argument("id"); sv.set_defaults(fn=cmd_survey)
    ck = sub.add_parser("check", help="list what's missing or broken (all cases if no id)")
    ck.add_argument("id", nargs="?"); ck.set_defaults(fn=cmd_check)
    pb = sub.add_parser("publish", help="put a checked case into the campaign")
    pb.add_argument("id"); pb.add_argument("--chapter", type=int, required=True)
    pb.add_argument("--title"); pb.add_argument("--teaser"); pb.add_argument("--difficulty")
    pb.add_argument("--replace", action="store_true", help="swap out the case a chapter already plays")
    pb.set_defaults(fn=cmd_publish)
    ls = sub.add_parser("list", help="show every case and its status")
    ls.set_defaults(fn=cmd_list)
    a = ap.parse_args(argv)
    try:
        return a.fn(a) or 0
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
