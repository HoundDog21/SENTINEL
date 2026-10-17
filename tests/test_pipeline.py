"""tools/case.py: every input format, the time-zone fix, refusals, and the new → check → publish flow."""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import R_CAMPAIGN, R_CASES, ROOT, SKIP, casetool, server

FX = Path(__file__).parent / "fixtures"


def convert(path, tz=None):
    return list(casetool.ingest(path, tz))


def first_ev(items, i=0):
    return items[0]["records"][i]["Event"]


class Formats(unittest.TestCase):
    def assertLoads(self, items):
        """Whatever came in, the app's own loader must read every converted record."""
        for it in items:
            for n, r in enumerate(it["records"], 1):
                server.normalize(json.loads(json.dumps(r)), "x.jsonl", n)

    def test_chainsaw_passthrough(self):
        items = convert(FX / "chainsaw.jsonl")
        self.assertEqual(items[0]["format"], "chainsaw JSONL")
        self.assertEqual(items[0]["records"], [json.loads(l) for l in (FX / "chainsaw.jsonl").read_text().splitlines()])
        self.assertLoads(items)

    def test_otrf_flat_json(self):
        items = convert(FX / "otrf.json")
        it = items[0]
        self.assertEqual(it["format"], "OTRF/nxlog flat JSON")
        self.assertTrue(any("UTC-16:00" in n for n in it["notes"]), it["notes"])
        ev = it["records"][0]["Event"]
        self.assertEqual(ev["System"]["EventID"], 1)
        self.assertEqual(ev["System"]["Computer"], "WORKSTATION5")
        self.assertNotIn("EventRecordID", ev["System"], "no record IDs may be invented")
        self.assertEqual(ev["EventData"]["Image"], "C:\\Windows\\System32\\reg.exe")
        for env in ("Hostname", "Channel", "TimeCreated", "Message", "SourceName"):
            self.assertNotIn(env, ev["EventData"], f"envelope field {env} leaked into EventData")
        self.assertEqual(ev["RenderingInfo"]["Message"], "Process Create: ...")
        # Sysmon EventType is data; nxlog's AUDIT_SUCCESS EventType is envelope
        self.assertEqual(it["records"][1]["Event"]["EventData"]["EventType"], "SetValue")
        sec = it["records"][2]["Event"]
        self.assertNotIn("EventType", sec["EventData"])
        self.assertEqual(sec["System"]["Execution_attributes"], {"ProcessID": 4, "ThreadID": 99})
        # local 10:47:08.745 (UTC-16) → 2020-10-20 02:47:08.745 UTC, matching the Sysmon UtcTime
        self.assertEqual(sec["System"]["TimeCreated_attributes"]["SystemTime"], "2020-10-20T02:47:08.745000Z")
        self.assertLoads(items)

    def test_tz_offset_override(self):
        sec = convert(FX / "otrf.json", tz=-5)[0]["records"][2]["Event"]
        self.assertEqual(sec["System"]["TimeCreated_attributes"]["SystemTime"], "2020-10-19T15:47:08.745000Z")

    def test_winlogbeat_array(self):
        items = convert(FX / "winlogbeat.json")
        self.assertEqual(items[0]["format"], "Winlogbeat JSON")
        ev = first_ev(items)
        self.assertEqual((ev["System"]["EventID"], ev["System"]["EventRecordID"], ev["System"]["Computer"]), (1, 120, "FS01.corp.local"))
        self.assertEqual(ev["System"]["TimeCreated_attributes"]["SystemTime"], "2024-03-02T10:20:01.500000Z")
        self.assertEqual(ev["EventData"]["CommandLine"], "sc.exe query UpdaterSvc")
        self.assertLoads(items)

    def test_windows_xml(self):
        items = convert(FX / "events.xml")
        self.assertEqual(items[0]["format"], "Windows event XML")
        svc, pca = (r["Event"] for r in items[0]["records"])
        self.assertEqual((svc["System"]["EventID"], svc["System"]["EventRecordID"], svc["System"]["Channel"]), (7045, 881, "System"))
        self.assertEqual(svc["System"]["Provider_attributes"]["Name"], "Service Control Manager")
        self.assertEqual(svc["EventData"]["ImagePath"], "C:\\ProgramData\\upd\\svc.exe")
        self.assertEqual(pca["UserData"]["ResolverFiredEvent"]["ExePath"], "C:\\ProgramData\\upd\\svc.exe")
        self.assertLoads(items)
        n = server.normalize(items[0]["records"][1], "x.jsonl", 2)
        self.assertEqual(n["target"], "C:\\ProgramData\\upd\\svc.exe", "UserData fields feed the table columns")

    def test_refusals(self):
        with self.assertRaisesRegex(casetool.Fail, "isn't a format I recognize"):
            convert(FX / "unknown.json")
        with self.assertRaisesRegex(casetool.Fail, "DOCTYPE"):
            convert(FX / "doctype.xml")
        with self.assertRaisesRegex(casetool.Fail, "unsupported file type"):
            convert(FX / "README.md")
        with self.assertRaisesRegex(casetool.Fail, "no such file"):
            convert(FX / "nope.json")

    def test_zip_is_read_in_memory_with_safe_names(self):
        with tempfile.TemporaryDirectory() as td:
            z = Path(td) / "bundle.zip"
            with zipfile.ZipFile(z, "w") as zf:
                zf.write(FX / "otrf.json", "../../escape/otrf.json")      # path traversal attempt
                zf.write(FX / "events.xml", "nested/dir/events.xml")
                zf.writestr("__MACOSX/._junk.json", "x")
                zf.writestr("notes.txt", "ignored")
            items = convert(z)
            self.assertEqual(sorted(i["stem"] for i in items), ["events", "otrf"])
            self.assertTrue(all(i["via"] == "bundle.zip" for i in items))
            self.assertFalse((Path(td).parent / "escape").exists())
            empty = Path(td) / "empty.zip"
            with zipfile.ZipFile(empty, "w") as zf:
                zf.writestr("readme.txt", "nothing")
            with self.assertRaisesRegex(casetool.Fail, "no .json"):
                convert(empty)

    @unittest.skipUnless(shutil.which("chainsaw"), "chainsaw not installed")
    def test_evtx(self):
        evtx = next(iter(sorted(server.CASES.glob("*/data/*.evtx"))), None)
        if not evtx:
            self.skipTest("no .evtx in any case (they're gitignored)")
        items = convert(evtx)
        self.assertEqual(items[0]["format"], "EVTX (chainsaw dump)")
        self.assertEqual(items[0]["records"], [json.loads(l) for l in evtx.with_suffix(".jsonl").read_text().splitlines()])


class CaseTool(unittest.TestCase):
    """The CLI end to end, in a throwaway copy of the project."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sentinel-cli-"))
        self.root = self.tmp / "Sentinel"
        shutil.copytree(ROOT, self.root, ignore=SKIP)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args):
        r = subprocess.run([sys.executable, "tools/case.py", *map(str, args)], cwd=self.root, capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "SENTINEL_SKIP_PUBLISH_TESTS": "1"})
        return r.returncode, r.stdout + r.stderr

    def fill_todos(self, cid):
        d = self.root / R_CASES / cid
        for rel in casetool.AUTHORED:
            p = d / rel
            p.write_text(p.read_text().replace("TODO", "written"))

    def test_new_check_publish(self):
        code, out = self.run_cli("new", "07-cli-test", "--title", "CLI Test", "--severity", "High", "--data", FX / "otrf.json", FX / "events.xml")
        self.assertEqual(code, 0, out)
        d = self.root / R_CASES / "07-cli-test"
        for rel in casetool.AUTHORED + ["worksheet.md", "report.md", "private/author-notes.md", "private/case.json",
                                        "data/otrf.jsonl", "data/events.jsonl", "data/source/otrf.json", "data/source/events.xml"]:
            self.assertTrue((d / rel).is_file(), rel)
        self.assertTrue((d / "brief.md").read_text().startswith("# Case 07: CLI Test"))
        notes = (d / "private" / "author-notes.md").read_text()
        self.assertIn("# Author notes: 07-cli-test", notes)
        self.assertIn("cite by file:line", notes)
        code, out = self.run_cli("check", "07-cli-test")
        self.assertEqual(code, 1)
        self.assertIn("still has a TODO", out)
        code, out = self.run_cli("publish", "07-cli-test", "--chapter", "2")
        self.assertNotEqual(code, 0, "publish must refuse a case with TODOs")
        self.fill_todos("07-cli-test")
        code, out = self.run_cli("check", "07-cli-test")
        self.assertEqual(code, 0, out)
        code, out = self.run_cli("publish", "07-cli-test", "--chapter", "1")
        self.assertNotEqual(code, 0)
        self.assertIn("already plays", out)
        code, out = self.run_cli("publish", "07-cli-test", "--chapter", "9")
        self.assertIn("next new chapter number", out)
        code, out = self.run_cli("publish", "07-cli-test", "--chapter", "2")
        self.assertEqual(code, 0, out)
        camp = json.loads((self.root / R_CAMPAIGN).read_text())
        self.assertEqual(next(c for c in camp["chapters"] if c["n"] == 2)["case"], "07-cli-test")
        code, out = self.run_cli("publish", "07-cli-test", "--chapter", "3")
        self.assertIn("already Chapter 2", out)
        code, out = self.run_cli("list")
        self.assertIn("07-cli-test", out)
        self.assertIn("live", out)

    def test_failed_new_leaves_nothing_behind(self):
        before = sorted(p.name for p in (self.root / R_CASES).iterdir())
        code, out = self.run_cli("new", "08-bad", "--title", "Bad", "--data", FX / "otrf.json", FX / "unknown.json")
        self.assertEqual(code, 2, out)
        self.assertEqual(sorted(p.name for p in (self.root / R_CASES).iterdir()), before)

    def test_bad_ids_and_duplicates(self):
        code, out = self.run_cli("new", "Bad_Name", "--title", "x", "--data", FX / "otrf.json")
        self.assertIn("should look like", out)
        existing = next(p.name for p in sorted((self.root / R_CASES).iterdir()) if casetool.CASE_ID.match(p.name))
        code, out = self.run_cli("new", existing, "--title", "x", "--data", FX / "otrf.json")
        self.assertIn("already exists", out)

    def test_add_data_and_survey(self):
        self.assertEqual(self.run_cli("new", "07-cli-test", "--title", "T", "--data", FX / "otrf.json")[0], 0)
        code, out = self.run_cli("add-data", "07-cli-test", FX / "otrf.json")
        self.assertEqual(code, 0, out)
        d = self.root / R_CASES / "07-cli-test"
        self.assertTrue((d / "data" / "otrf-2.jsonl").is_file(), "a second file with the same name gets a new stem")
        meta = json.loads((d / "private" / "case.json").read_text())
        self.assertEqual(len(meta["sources"]), 2)
        self.assertEqual(self.run_cli("survey", "07-cli-test")[0], 0)
        self.assertIn("otrf-2.jsonl", (d / "private" / "author-notes.md").read_text())


if __name__ == "__main__":
    unittest.main()
