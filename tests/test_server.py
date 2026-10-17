"""app/server.py through HTTP: static files, safety rules, chapter locking, XP, tutorial isolation."""
import json
import re
import shutil
import socket
import unittest

from helpers import R_CAMPAIGN, R_CASES, R_LIBRARY, R_TUTORIAL, R_WORKSPACE, ROOT, Sandbox, fingerprint, server

IOC_TYPES = set(re.search(r'const IOC_TYPES = \[([^\]]+)\]', (ROOT / "app/static/app.js").read_text()).group(1).replace('"', "").replace(" ", "").split(","))


def first_case():
    camp = server.read_json(server.CAMPAIGN, {})
    return next(c["case"] for c in camp["chapters"] if c.get("case"))


class Static(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sb = Sandbox().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.sb.__exit__(None, None, None)

    def test_pages_and_assets(self):
        for path in ("/", "/static/app.js", "/static/tutorial.js", "/static/style.css", "/static/vendor/gridstack-all.js", "/static/vendor/marked.min.js"):
            code, _ = self.sb.get(path)
            self.assertEqual(code, 200, path)

    def test_no_path_traversal(self):
        for path in ("/static/../server.py", "/static/%2e%2e/server.py", "/static/..%2fserver.py", "/static/../../cases",
                     "/static/../eventids.json", "/api/cases/..%2fcampaign.json/answer"):
            code, _ = self.sb.get(path)
            self.assertIn(code, (403, 404), path)

    def test_catalog_is_well_formed(self):
        code, cat = self.sb.get("/api/catalog")
        self.assertEqual(code, 200)
        for c in cat["channels"]:
            self.assertTrue(bool(c.get("exact")) != bool(c.get("contains")), f"{c.get('name')}: needs exactly one of exact/contains")
            self.assertTrue(c.get("name") and c.get("fallback"), c)
            for k, v in c.get("ids", {}).items():
                self.assertTrue(k.isdigit() and v, f"{c['name']}: bad id {k!r}")
        for field, t in cat["ioc_types"].items():
            self.assertIn(t, IOC_TYPES, f"ioc_types.{field} = {t!r} isn't an IOC type the app knows")
        for col in ("user", "image", "cmd", "target", "guid", "pguid", "pimage"):
            self.assertTrue(cat["columns"].get(col), f"columns.{col} missing")


class Safety(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox().__enter__()
        self.cid = first_case()
        self.api = f"/api/cases/{self.cid}"

    def tearDown(self):
        self.sb.__exit__(None, None, None)

    def test_cross_origin_writes_refused(self):
        evil = "http://evil.example"
        for method, path, body in (("PUT", "/file/report.md", "x"), ("PUT", "/doc/iocs", "[]"), ("PUT", "/state", "{}"),
                                   ("POST", "/submit", ""), ("POST", "/activity", '{"type":"comment","text":"x"}')):
            code, _ = self.sb.call(method, self.api + path, body, origin=evil)
            self.assertEqual(code, 403, f"{method} {path}")
        self.assertEqual(self.sb.post("/api/tutorial/reset", origin=evil)[0], 403)
        self.assertEqual(self.sb.get(self.api + "/answer")[0], 403)

    def test_only_editable_files_can_be_written(self):
        for name in ("brief.md", "story.md", "../brief.md", "private%2Fanswer-key.md", "state.json"):
            code, _ = self.sb.put(self.api + "/file/" + name, "overwritten")
            self.assertEqual(code, 404, name)
        self.assertEqual(self.sb.put(self.api + "/file/worksheet.md", "my notes")[0], 200)
        self.assertEqual((self.sb.root / R_CASES / self.cid / "worksheet.md").read_text(), "my notes")
        self.assertEqual(self.sb.put(self.api + "/doc/iocs", '{"not": "a list"}')[0], 400)
        self.assertEqual(self.sb.put(self.api + "/doc/secrets", "[]")[0], 404)
        self.assertEqual(self.sb.put(self.api + "/doc/iocs", "not json")[0], 400)

    def test_bad_ids_and_activity(self):
        self.assertEqual(self.sb.get("/api/cases/nope")[0], 404)
        self.assertEqual(self.sb.get("/api/cases/..")[0], 404)
        self.assertEqual(self.sb.post(self.api + "/activity", {"type": "evil", "text": "x"})[0], 400)
        self.assertEqual(self.sb.post(self.api + "/activity", {"type": "comment", "text": "  "})[0], 400)
        code, st = self.sb.put(self.api + "/state", {"status": "Triage"})
        self.assertEqual(st["state"]["status"], "Triage")
        self.assertTrue(any("Triage" in a["text"] for a in st["activity"]))
        code, st = self.sb.put(self.api + "/state", {"status": "Pwned"})
        self.assertEqual(st["state"]["status"], "Triage")

    def test_malformed_requests_get_a_clear_error(self):
        """Wrong JSON shapes and a bad Content-Length get a 400, not a dropped connection or a stuck thread."""
        for method, path, body in (("PUT", "/state", "[]"), ("PUT", "/state", '"x"'), ("POST", "/activity", "[1]")):
            self.assertEqual(self.sb.call(method, self.api + path, body)[0], 400, f"{method} {path} {body}")
        self.sb.post(self.api + "/submit")
        self.assertEqual(self.sb.post(self.api + "/score", '"x"')[0], 400)
        with socket.create_connection(("127.0.0.1", self.sb.port), timeout=5) as s:
            s.sendall(f"PUT {self.api}/file/worksheet.md HTTP/1.1\r\nHost: 127.0.0.1:{self.sb.port}\r\nContent-Length: -1\r\n\r\n".encode())
            self.assertIn(b" 400 ", s.recv(100))

    def test_foreign_host_header_refused(self):
        """DNS rebinding: a website whose domain resolves to 127.0.0.1 can't read or write the API."""
        bad = {"Host": f"evil.example:{self.sb.port}"}
        self.assertEqual(self.sb.call("GET", "/api/profile", headers=bad)[0], 403)
        self.assertEqual(self.sb.call("GET", self.api, headers=bad)[0], 403)
        self.assertEqual(self.sb.call("PUT", self.api + "/file/report.md", "x", headers=bad)[0], 403)
        self.assertEqual(self.sb.call("GET", "/api/profile", headers={"Host": f"localhost:{self.sb.port}"})[0], 200)

    def test_progress_lists_hold_only_real_items(self):
        """Hints, steps and rubric items can't be counted twice, out of range, or as true/false."""
        code, st = self.sb.put(self.api + "/state", {"hints": [True, 0, 0, 999], "steps": [0, 0, -1, 999, False]})
        self.assertEqual((code, st["state"]["hints"], st["state"]["steps"]), (200, [0], [0]))
        self.sb.post(self.api + "/submit")
        rb = self.sb.get(self.api + "/rubric")[1]
        code, sc = self.sb.post(self.api + "/score", {"rubric": [True, 0, 0]})
        self.assertEqual((code, sc["earned"]), (200, rb["items"][0]["points"]))

    def test_unexpected_errors_answer_with_json(self):
        (self.sb.root / R_CASES / self.cid / "private" / "rubric.json").write_text(json.dumps({"items": [{"points": 5, "text": "x"}]}))
        self.sb.post(self.api + "/submit")
        code, body = self.sb.post(self.api + "/score", {"rubric": [0]})
        self.assertEqual(code, 500)
        self.assertIn("error", body)


class Campaign(unittest.TestCase):
    """Locking and XP with the real campaign plus an extra test chapter."""

    def setUp(self):
        self.sb = Sandbox(unlock_all=False).__enter__()
        self.c1 = first_case()
        root = self.sb.root
        shutil.copytree(root / R_CASES / self.c1, root / R_CASES / "99-lock-test")
        camp = json.loads((root / R_CAMPAIGN).read_text())
        for ch in camp["chapters"]:
            ch["case"] = None
        camp["chapters"][0]["case"] = self.c1
        camp["chapters"][1]["case"] = "99-lock-test"
        (root / R_CAMPAIGN).write_text(json.dumps(camp))

    def tearDown(self):
        self.sb.__exit__(None, None, None)

    def test_chapters_unlock_in_order_and_xp_adds_up(self):
        sb = self.sb
        code, pf = sb.get("/api/profile")
        self.assertEqual([c["status"] for c in pf["chapters"][:3]], ["available", "locked", "coming-soon"])
        self.assertEqual(pf["xp"], 0)
        self.assertEqual(sb.get("/api/cases/99-lock-test")[0], 403)
        self.assertEqual(sb.get("/api/cases/99-lock-test/events")[0], 403)
        self.assertEqual(sb.put("/api/cases/99-lock-test/file/report.md", "x")[0], 403)
        api = f"/api/cases/{self.c1}"
        sb.get(api)
        sb.post(api + "/submit")
        rb = sb.get(api + "/rubric")[1]
        sc = sb.post(api + "/score", {"rubric": [0]})[1]
        self.assertEqual(sc["xp_after"], rb["items"][0]["points"])
        code, pf = sb.get("/api/profile")
        self.assertEqual((pf["xp"], pf["closed"]), (rb["items"][0]["points"], 1))
        self.assertEqual(pf["chapters"][1]["status"], "available")
        self.assertEqual(sb.get("/api/cases/99-lock-test")[0], 200)
        sb.post(api + "/reset")
        self.assertEqual(sb.get("/api/profile")[1]["xp"], 0, "reset removes the XP")


class Library(unittest.TestCase):
    """The Case library with a test entry: listing, no locks, XP, nothing private leaked."""

    def setUp(self):
        self.sb = Sandbox(unlock_all=False).__enter__()
        root = self.sb.root
        shutil.copytree(root / R_CASES / first_case(), root / R_CASES / "98-library-test")
        (root / R_LIBRARY).write_text(json.dumps({"cases": [{"case": "98-library-test", "teaser": "A test ticket from the queue, for the test suite."}]}))

    def tearDown(self):
        self.sb.__exit__(None, None, None)

    def test_listing_unlocked_and_scored(self):
        sb = self.sb
        code, lib = sb.get("/api/library")
        self.assertEqual(code, 200)
        self.assertEqual([c["case"] for c in lib], ["98-library-test"])
        c = lib[0]
        self.assertEqual((c["status"], c["score"], c["teaser"]), ("new", None, "A test ticket from the queue, for the test suite."))
        for k in ("title", "difficulty", "severity", "budget", "data"):
            self.assertTrue(c[k], k)
        self.assertFalse(c["title"].startswith("Case "), "title shown without the 'Case NN:' prefix")
        answer = (sb.root / R_CASES / "98-library-test" / "private" / "answer-key.md").read_text()
        self.assertNotIn(answer[200:260], json.dumps(lib), "listing leaked the answer key")
        api = "/api/cases/98-library-test"
        self.assertEqual(sb.get(api)[0], 200, "library cases are never locked")
        self.assertEqual(sb.get("/api/library")[1][0]["status"], "in-progress")
        sb.post(api + "/submit")
        sc = sb.post(api + "/score", {"rubric": [0]})[1]
        pts = sb.get(api + "/rubric")[1]["items"][0]["points"]
        self.assertEqual(sc["xp_after"] - sc["xp_before"], pts, "library scores earn XP")
        pf = sb.get("/api/profile")[1]
        self.assertEqual((pf["xp"], pf["closed"]), (pts, 1))
        self.assertEqual(sb.get("/api/library")[1][0]["status"], "completed")

    def test_a_duplicate_entry_counts_once(self):
        entry = {"case": "98-library-test", "teaser": "A test ticket from the queue, for the test suite."}
        (self.sb.root / R_LIBRARY).write_text(json.dumps({"cases": [entry, entry]}))
        self.assertEqual(len(self.sb.get("/api/library")[1]), 1)
        api = "/api/cases/98-library-test"
        self.sb.post(api + "/submit")
        sc = self.sb.post(api + "/score", {"rubric": [0]})[1]
        self.assertEqual(self.sb.get("/api/profile")[1]["xp"], sc["score"], "a duplicate library entry must not double the XP")

    def test_a_chapter_case_is_not_listed(self):
        (self.sb.root / R_LIBRARY).write_text(json.dumps({"cases": [{"case": first_case(), "teaser": "x" * 30}, {"case": "no-such", "teaser": "y" * 30}]}))
        self.assertEqual(self.sb.get("/api/library")[1], [])


class Tutorial(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox(unlock_all=False).__enter__()

    def tearDown(self):
        self.sb.__exit__(None, None, None)

    def test_tutorial_never_touches_real_cases_xp_or_template(self):
        sb, root = self.sb, self.sb.root
        before = fingerprint(root)
        template = {str(p.relative_to(root)): p.read_bytes() for p in (root / R_TUTORIAL).rglob("*") if p.is_file()}
        xp = sb.get("/api/profile")[1]
        self.assertEqual(sb.post("/api/tutorial/reset")[0], 200)
        api = "/api/cases/tutorial"
        code, data = sb.get(api)
        self.assertEqual((code, data["id"], data["tutorial"], data["chapter"]), (200, "tutorial", True, None))
        ev = sb.get(api + "/events")[1]["events"]
        sb.put(api + "/doc/bookmarks", [{"key": ev[0]["key"], "note": "x"}])
        sb.put(api + "/doc/iocs", [{"type": "file", "value": "x"}])
        sb.put(api + "/doc/tree", [{"id": "a", "key": ev[0]["key"], "name": "n", "parent": None}])
        sb.put(api + "/file/report.md", "practice report")
        sb.put(api + "/state", {"status": "Triage", "hints": [0], "steps": [0]})
        sb.post(api + "/activity", {"type": "comment", "text": "hi"})
        sb.post(api + "/submit")
        rb = sb.get(api + "/rubric")[1]
        sc = sb.post(api + "/score", {"rubric": list(range(len(rb["items"])))})[1]
        self.assertEqual(sc["xp_before"], sc["xp_after"], "tutorial scoring must not change XP")
        self.assertEqual(sb.get("/api/profile")[1], xp)
        self.assertEqual(fingerprint(root), before, "tutorial changed authored files under content/")
        self.assertEqual({str(p.relative_to(root)): p.read_bytes() for p in (root / R_TUTORIAL).rglob("*") if p.is_file()},
                         template, "tutorial changed its own template")
        work = root / R_WORKSPACE
        self.assertEqual((work / "report.md").read_text(), "practice report")
        # replay: a fresh workspace
        sb.post("/api/tutorial/reset")
        self.assertFalse((work / "bookmarks.json").exists())
        self.assertEqual(sb.get(api)[1]["state"]["submitted"], False)
        self.assertNotIn("tutorial", [c.get("case") for c in sb.get("/api/profile")[1]["chapters"]])


if __name__ == "__main__":
    unittest.main()
