"""Tests every case folder automatically: add a case to content/cases/ and it's covered.

Published cases (and the tutorial) must be complete. Unpublished drafts may still have TODOs, but
everything else (data, references, structure) must already hold.

Run one case: ./sentinel test --case 01-unpaid-invoice
"""
import hashlib
import json
import re
import unittest

from helpers import (LINE_REF, R_CASES, R_WORKSPACE, REC_REF, ROOT, Sandbox, case_dirs, case_id, campaign, casetool, is_draft,
                     published_ids, server)


def events_of(d):
    events, errors = server.load_events(d)
    return events, errors


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def valid_records(events):
    """Record IDs present in the data, plus the gaps inside each channel's range (so an answer key
    may say 'record 4862 is missing')."""
    present, gaps = set(), set()
    by_ch = {}
    for e in events:
        r = as_int(e.get("record"))
        if r is not None:
            present.add(r)
            by_ch.setdefault(e.get("channel"), set()).add(r)
    for recs in by_ch.values():
        gaps |= set(range(min(recs), max(recs) + 1)) - recs
    return present, gaps


def per_case(test):
    """Run a test once per case folder, each in its own subTest: one failing case doesn't stop the
    others from being checked, and each failure is reported once, under its case."""
    def run(self):
        dirs = case_dirs()
        if not dirs:
            self.skipTest("no cases")
        for d in dirs:
            with self.subTest(case=case_id(d)):
                test(self, d)
    run.__name__, run.__doc__ = test.__name__, test.__doc__
    return run


class CaseContent(unittest.TestCase):
    """Static checks on each case's files and data. No server needed."""

    @per_case
    def test_case_check_is_clean(self, d):
        errors, warns = casetool.check(d, quiet=True)
        if is_draft(d):
            errors = [e for e in errors if "still has a TODO" not in e]
        self.assertEqual(errors, [], f"`./sentinel case check {case_id(d)}` reports errors")
        unlabeled = [w for w in warns if "no label" in w]
        self.assertEqual(unlabeled, [], "add labels for these to app/eventids.json")

    @per_case
    def test_data_loads_and_every_event_has_a_time(self, d):
        events, errors = events_of(d)
        self.assertEqual(errors, [])
        self.assertTrue(events, "no events")
        self.assertEqual([e["key"] for e in events if not e.get("time")], [], "events without a timestamp")
        keys = [e["key"] for e in events]
        self.assertEqual(len(keys), len(set(keys)), "duplicate event keys")

    @per_case
    def test_answer_key_cites_real_records(self, d):
        """Every 'rec N' / 'record N' in the private files and hints exists in the data, or is a
        gap inside a channel's range (a record the answer key says is missing)."""
        events, _ = events_of(d)
        present, gaps = valid_records(events)
        for rel in ("private/answer-key.md", "private/rubric.json", "private/debrief.json", "hints.md"):
            text = server.read_text(d / rel)
            for m in REC_REF.finditer(text):
                line = text[: m.start()].count("\n") + 1
                for n in map(int, re.findall(r"\d+", m.group(1))):     # every number in a list or range
                    self.assertTrue(n in present or n in gaps,
                                    f"{rel}:{line} cites record {n}, which isn't in the data (or in a gap)")

    @per_case
    def test_file_line_references_exist(self, d):
        lines = {f.name: sum(1 for l in f.read_text(encoding="utf-8").splitlines() if l.strip()) for f in (d / "data").glob("*.jsonl")}
        for rel in ("private/answer-key.md", "hints.md", "brief.md"):
            text = server.read_text(d / rel)
            for m in LINE_REF.finditer(text):
                name, n = m.group(1), int(m.group(2))
                self.assertIn(name, lines, f"{rel} cites {name}:{n}, but there's no data/{name}")
                self.assertTrue(1 <= n <= lines[name], f"{rel} cites {name}:{n}, but the file has {lines[name]} events")

    @per_case
    def test_brief_lists_every_data_file(self, d):
        brief = server.read_text(d / "brief.md")
        for f in (d / "data").glob("*.jsonl"):
            self.assertIn(f.name, brief, f"brief.md's Evidence table doesn't mention data/{f.name}")

    @per_case
    def test_brief_hashes_match_files(self, d):
        """'SHA-256 `3a343508…3c3550`' next to a file name must match that file (skipped when the
        file isn't present, e.g. a gitignored .evtx on a fresh clone)."""
        for line in server.read_text(d / "brief.md").splitlines():
            m = re.search(r"`(data/[^`]+)`.*SHA-256 `([0-9a-f]{6,})…([0-9a-f]{4,})`", line)
            if not m or not (d / m.group(1)).is_file():
                continue
            h = hashlib.sha256((d / m.group(1)).read_bytes()).hexdigest()
            self.assertTrue(h.startswith(m.group(2)) and h.endswith(m.group(3)), f"brief.md hash for {m.group(1)} is wrong: real {h}")

    @per_case
    def test_brief_data_field_matches_event_ids(self, d):
        field = server.field_of(server.read_text(d / "brief.md"), "Data") or ""
        claimed = {int(n) for n in re.findall(r"\b(\d{1,5})\b", field)}
        events, _ = events_of(d)
        actual = {as_int(e.get("eid")) for e in events}
        self.assertEqual(claimed - actual, set(), f"brief.md **Data:** names Event IDs not in the data: {sorted(claimed - actual)}")
        if not is_draft(d):
            self.assertEqual(actual - claimed, set(), f"brief.md **Data:** doesn't mention Event IDs {sorted(actual - claimed)}")

    @per_case
    def test_hints_match_playbook_steps(self, d):
        steps = server.steps_of(server.read_text(d / "brief.md"))
        self.assertTrue(steps, "no ## Guided steps")
        hints = server.read_text(d / "hints.md")
        self.assertGreaterEqual(hints.count("<details"), 1, "no hints")
        self.assertEqual(hints.count("<details"), hints.count("</details>"), "unbalanced <details> blocks")
        self.assertEqual(hints.count("<details"), hints.count("<summary>"), "every hint needs a <summary>")
        for n in re.findall(r"^###\s+Step\s+(\d+)", hints, re.M):
            self.assertLessEqual(int(n), len(steps), f"hints.md has a 'Step {n}' section but the playbook has {len(steps)} steps")

    @per_case
    def test_rubric_and_debrief_fit_together(self, d):
        rb = json.loads((d / "private" / "rubric.json").read_text())
        db = json.loads((d / "private" / "debrief.json").read_text())
        if not is_draft(d):
            self.assertEqual(sum(i["points"] for i in rb["items"]), 100, "rubric points should total 100")
        for _, letter in rb["grades"]:
            self.assertTrue(db.get("by_grade", {}).get(letter), f"debrief has no text for grade {letter}")
        texts = [i["text"] for i in rb["items"]]
        self.assertEqual(len(texts), len(set(texts)), "duplicate rubric items")


class Campaign(unittest.TestCase):
    def test_chapters_are_consistent(self):
        camp = campaign()
        chs = camp["chapters"]
        self.assertEqual([c["n"] for c in chs], list(range(1, len(chs) + 1)), "chapters must be numbered 1, 2, 3…")
        cases = [c["case"] for c in chs if c.get("case")]
        self.assertEqual(len(cases), len(set(cases)), "a case is in two chapters")
        for c in chs:
            for k in ("title", "teaser", "difficulty"):
                self.assertTrue(c.get(k), f"chapter {c['n']} has no {k}")
            if c.get("case"):
                self.assertTrue((server.CASES / c["case"] / "brief.md").is_file(), f"chapter {c['n']} points at missing case {c['case']}")
        playable = [c["n"] for c in chs if c.get("case")]
        self.assertEqual(playable, list(range(1, len(playable) + 1)), "playable chapters must come first, with no gaps")

    def test_library_is_consistent(self):
        entries = server.read_json(server.LIBRARY, {"cases": []}).get("cases", [])
        ids = [e.get("case") for e in entries]
        self.assertEqual(len(ids), len(set(ids)), "a case is listed twice in the library")
        chapters = {c.get("case") for c in campaign()["chapters"]}
        for e in entries:
            with self.subTest(case=e.get("case")):
                self.assertTrue((server.CASES / e["case"] / "brief.md").is_file(), "library lists a missing case")
                self.assertNotIn(e["case"], chapters, "a case can't be both a chapter and in the library")
                self.assertTrue(len(e.get("teaser", "").strip()) >= 20, "library cases need a real teaser")
                self.assertIsNone(casetool.SPOILER.search(e["teaser"]), "the teaser names a file, which gives the case away")
                title = server.title_of(server.read_text(server.CASES / e["case"] / "brief.md"), "")
                self.assertRegex(title, r"^Case \d+: \S", "brief.md title should be '# Case NN: Title'")
                self.assertTrue(e["case"].startswith(title.split()[1].rstrip(":")), "case number in the title should match the folder")

    def test_ranks(self):
        ranks = campaign()["ranks"]
        xp = [r["xp"] for r in ranks]
        self.assertEqual(xp[0], 0)
        self.assertEqual(xp, sorted(set(xp)), "rank XP must increase")


class CaseApi(unittest.TestCase):
    """Each case through a real (throwaway) server: loading, locking of private files, scoring."""

    @classmethod
    def setUpClass(cls):
        cls.sb = Sandbox(unlock_all=True).__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.sb.__exit__(None, None, None)

    def test_each_case_plays_through(self):
        sb = self.sb
        for d in case_dirs():
            cid = case_id(d)
            with self.subTest(case=cid):
                if cid == "tutorial":
                    self.assertEqual(sb.post("/api/tutorial/reset")[0], 200)
                    d = sb.root / R_WORKSPACE
                else:
                    d = sb.root / R_CASES / cid
                api = f"/api/cases/{cid}"
                code, data = sb.get(api)
                self.assertEqual(code, 200, data)
                self.assertEqual(data["steps"], server.steps_of((d / "brief.md").read_text()))
                code, ev = sb.get(api + "/events")
                self.assertEqual((code, ev["errors"]), (200, []))
                self.assertEqual(len(ev["events"]), len(server.load_events(d)[0]))
                # private files stay locked until submit, and 'submitted' can't be forced
                for sub in ("/answer", "/rubric", "/debrief"):
                    self.assertEqual(sb.get(api + sub)[0], 403, f"{sub} served before submit")
                sb.put(api + "/state", {"submitted": True})
                self.assertEqual(sb.get(api + "/answer")[0], 403, "PUT state must not unlock the answer key")
                # open one hint, submit, score everything
                self.assertEqual(sb.put(api + "/state", {"hints": [0]})[0], 200)
                code, sub = sb.post(api + "/submit")
                self.assertEqual(code, 200)
                self.assertEqual(sub["answer"], (d / "private" / "answer-key.md").read_text())
                code, rb = sb.get(api + "/rubric")
                self.assertEqual((code, rb["hints_used"]), (200, 1))
                code, sc = sb.post(api + "/score", {"rubric": list(range(len(rb["items"])))})
                total = sum(i["points"] for i in rb["items"])
                self.assertEqual(code, 200)
                self.assertEqual(sc["score"], max(0, total - rb["hint_penalty"]))
                expect_grade = next(g for floor, g in rb["grades"] if sc["score"] >= floor)
                self.assertEqual(sc["grade"], expect_grade)
                db = json.loads((d / "private" / "debrief.json").read_text())
                self.assertIn(db["common"][:40], sc["debrief"])
                self.assertIn(db["by_grade"][expect_grade][:40], sc["debrief"])
                # reset hides it again
                self.assertEqual(sb.post(api + "/reset")[0], 200)
                self.assertEqual(sb.get(api + "/answer")[0], 403)


if __name__ == "__main__":
    unittest.main()
