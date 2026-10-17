"""Plays every case in a real browser the way a learner would. A new case is covered automatically."""
import json
import unittest

from helpers import R_CAMPAIGN, R_CASES, R_LIBRARY, Sandbox, case_dirs, case_id, server
from browser.common import Page, needs_browser


def show(pg, *titles):
    """Show widgets through the Widgets ▾ menu, like a user."""
    pg.click("#widgets-btn")
    for t in titles:
        box = pg.locator("#widgets-pop label.check", has_text=t).locator("input")
        if not box.is_checked():
            box.check()
    pg.click("#widgets-btn")
    pg.wait_for_timeout(250)


@needs_browser
class PlayEveryCase(unittest.TestCase):
    def test_every_case(self):
        dirs = [d for d in case_dirs() if case_id(d) != "tutorial"]
        if not dirs:
            self.skipTest("no cases")
        for d in dirs:
            with self.subTest(case=d.name):
                self.play(d)

    def play(self, d):
        cid = d.name
        rb = json.loads((d / "private" / "rubric.json").read_text())
        has_story = bool(server.read_text(d / "story.md").strip())
        with Sandbox(unlock_all=True) as sb, Page() as P:
            pg = P.page
            n_events = len(sb.get(f"/api/cases/{cid}/events")[1]["events"])
            pg.goto(f"{sb.url}/#/case/{cid}")
            if has_story:
                pg.wait_for_selector("#dialog[open]")
                self.assertEqual(pg.locator("#dialog-ok").inner_text(), "Accept case")
                pg.click("#dialog-ok")
            pg.wait_for_selector("tr.row")
            pg.wait_for_timeout(300)
            sev = server.field_of(server.read_text(d / "brief.md"), "Severity") or "Medium"
            self.assertIn(sev.upper(), pg.locator("#casebar").inner_text().upper())
            self.assertEqual(pg.locator("tr.row").count(), n_events, "every event is listed")
            self.assertEqual(pg.locator(".pb-task:not(.final)").count(), len(server.steps_of(server.read_text(d / "brief.md"))))
            # every event opens cleanly in Event detail
            for i, row in enumerate(pg.locator("tr.row").all()[:80]):
                row.click()
                body = pg.locator('[data-w="detail"] .w-body').inner_text()
                self.assertIn("Raw record".upper(), body.upper(), f"event {i} didn't render")
                head = body.upper().split("RAW RECORD")[0]
                self.assertNotIn("UNDEFINED", head, f"event {i}: 'undefined' in detail")
                self.assertNotRegex(head, r"\bNULL\b", f"event {i}: stray 'null' in detail")
            show(pg, "Hints", "Process tree", "Evidence", "Worksheet", "Report")
            # evidence + note
            pg.locator("tr.row").first.click()
            pg.click('[data-w="detail"] button:has-text("Add to evidence")')
            pg.fill('[data-w="detail"] textarea', "test note")
            pg.wait_for_timeout(800)
            self.assertEqual(pg.locator('[data-w="evidence"] .bm').count(), 1)
            # processes into the tree (up to three events with a ProcessGuid), and a not-in-evidence node
            keys = pg.evaluate("(S.events.filter(e => e.guid).length ? S.events.filter(e => e.guid) : S.events).slice(0, 3).map(e => e.key)")
            for key in keys:
                pg.locator(f'tr.row[data-key="{key}"]').click()
                pg.click('[data-w="detail"] button:has-text("Add to tree")')
                pg.wait_for_timeout(250)
            pg.fill('[data-w="tree"] input[placeholder^="Process seen only"]', "parent.exe")
            pg.click('[data-w="tree"] button:has-text("Not-in-evidence")')
            pg.wait_for_timeout(300)
            self.assertEqual(pg.evaluate("S.tree.length"), len(keys) + 1)
            self.assertEqual(pg.evaluate("S.tree.map(n => n.parent)"), [None] * (len(keys) + 1), "the app must never pick a parent")
            if len(keys) >= 2:   # but you can pick one yourself
                child = pg.evaluate("S.tree[1].key")
                pg.locator(f'[data-w="tree"] .node[data-key="{child}"] select').select_option(pg.evaluate("S.tree[0].id"))
                pg.wait_for_timeout(300)
                self.assertEqual(pg.evaluate("S.tree[1].parent"), pg.evaluate("S.tree[0].id"))
            # flag an IOC from a field
            row = pg.locator('[data-w="detail"] .kv tr').filter(has=pg.locator("button", has_text="IOC")).first
            row.hover(); row.locator("button", has_text="IOC").click()
            pg.wait_for_timeout(300)
            self.assertEqual(pg.evaluate("S.iocs.length"), 1)
            # playbook, hint, war room
            pg.locator(".pb-task:not(.final)").first.click()
            pg.locator('[data-w="hints"] details summary').first.click()
            pg.fill('[data-w="warroom"] .wr-input input', "war room note"); pg.keyboard.press("Enter")
            pg.wait_for_timeout(500)
            self.assertEqual(pg.evaluate("[S.state.steps.length, S.state.hints.length]"), [1, 1])
            wr = pg.locator('[data-w="warroom"] .wr-log').inner_text()
            for bad in ("rec null", "rec undefined", "undefined"):
                self.assertNotIn(bad, wr)
            # worksheet + report, saved to disk
            for name in ("worksheet", "report"):
                ta = pg.locator(f'[data-w="{name}"] textarea')
                ta.click(); ta.press("End"); ta.type(f"\n{name} line")
                pg.click(f'[data-w="{name}"] button:has-text("Save")')
            pg.click('[data-w="report"] button:has-text("+ Evidence")')
            pg.click('[data-w="report"] button:has-text("+ Tree")')
            pg.click('[data-w="report"] button:has-text("Save")')
            pg.wait_for_timeout(400)
            report = (sb.root / R_CASES / cid / "report.md").read_text()
            self.assertIn("report line", report)
            self.assertIn("test note", report, "+ Evidence inserts your evidence table")
            # submit, score, debrief
            pg.click('#casebar button:has-text("Submit report")')
            pg.wait_for_selector("#dialog[open]"); pg.click("#dialog-ok")
            pg.wait_for_selector(".rub-item")
            self.assertEqual(pg.locator(".rub-item").count(), len(rb["items"]))
            for cb in pg.locator(".rub-item input").all():
                cb.check()
            pg.click('button:has-text("Finalize score")')
            pg.wait_for_selector("#dialog[open]")
            expect = max(0, sum(i["points"] for i in rb["items"]) - rb["hint_penalty"])
            self.assertIn(f"{expect} points", pg.locator("#dialog").inner_text())
            pg.click("#dialog-ok")
            pg.wait_for_selector("#home:not(.hidden)")
            self.assertEqual(P.errors, [], "browser errors")


def first_case_id():
    camp = server.read_json(server.CAMPAIGN, {"chapters": []})
    lib = server.read_json(server.LIBRARY, {"cases": []}).get("cases", [])
    return next((c["case"] for c in camp["chapters"] if c.get("case")), None) or (lib[0]["case"] if lib else None)


@needs_browser
class Regressions(unittest.TestCase):
    """Bugs that were fixed once and must stay fixed."""

    def open_case(self, sb, pg, cid):
        pg.goto(f"{sb.url}/#/case/{cid}")
        if server.read_text(server.CASES / cid / "story.md").strip():
            pg.wait_for_selector("#dialog[open]")
            pg.click("#dialog-ok")           # accepting the briefing leaves the dialog's returnValue at "ok"
        pg.wait_for_selector("tr.row")

    def test_backing_out_of_submit_does_not_submit(self):
        cid = first_case_id()
        if not cid:
            self.skipTest("no published case")
        with Sandbox(unlock_all=True) as sb, Page() as P:
            pg = P.page
            self.open_case(sb, pg, cid)
            for how in ("close()", "Escape"):
                pg.evaluate("document.querySelector('#dialog').returnValue = 'ok'")   # as if the last dialog was OK'd
                pg.click('#casebar button:has-text("Submit report")')
                pg.wait_for_selector("#dialog[open]")
                if how == "Escape":
                    pg.keyboard.press("Escape")
                else:                            # how the spec says Esc closes a dialog: no new returnValue
                    pg.evaluate("document.querySelector('#dialog').close()")
                pg.wait_for_timeout(400)
                self.assertFalse(pg.evaluate("S.state.submitted"), f"closing the submit dialog with {how} submitted the report")
            self.assertFalse(sb.get(f"/api/cases/{cid}")[1]["state"]["submitted"])
            self.assertEqual(P.errors, [])

    def test_a_note_is_saved_even_if_you_leave_straight_away(self):
        cid = first_case_id()
        if not cid:
            self.skipTest("no published case")
        with Sandbox(unlock_all=True) as sb, Page() as P:
            pg = P.page
            self.open_case(sb, pg, cid)
            pg.locator("tr.row").first.click()
            pg.click('[data-w="detail"] button:has-text("Add to evidence")')
            pg.fill('[data-w="detail"] textarea', "typed just before leaving")
            pg.evaluate("location.hash = ''")    # leave before the note's save timer fires
            pg.wait_for_selector("#home:not(.hidden)")
            pg.wait_for_timeout(1000)
            saved = json.loads((sb.root / R_CASES / cid / "bookmarks.json").read_text())
            self.assertEqual(saved[0]["note"], "typed just before leaving")
            self.assertEqual(P.errors, [])


@needs_browser
class HQ(unittest.TestCase):
    def test_hq_shows_the_campaign(self):
        with Sandbox(unlock_all=False) as sb, Page() as P:
            pg = P.page
            pg.goto(sb.url)
            pg.wait_for_selector(".chapter")
            camp = json.loads((sb.root / R_CAMPAIGN).read_text())
            self.assertEqual(pg.locator(".chapters .chapter").count(), len(camp["chapters"]))
            for ch in camp["chapters"]:
                self.assertIn(ch["title"], pg.locator("#home").inner_text())
            self.assertEqual(pg.locator("#tutorial-btn").count(), 1)
            lib = json.loads((sb.root / R_LIBRARY).read_text())["cases"]
            self.assertEqual(pg.locator(".lib-card").count(), len(lib), "every library case has a card")
            for e in lib:
                self.assertIn(e["teaser"], pg.locator("#home").inner_text())
            if lib:
                pg.fill(".lib-filters input[type=search]", "zzzz-no-such-case")
                self.assertEqual(pg.locator(".lib-card").count(), 0, "search filters the cards")
                self.assertIn("No cases match", pg.locator(".lib-grid").inner_text())
                pg.fill(".lib-filters input[type=search]", "")
                pg.click('.lib-filters button:has-text("Completed")')
                self.assertEqual(pg.locator(".lib-card").count(), 0, "status filter: nothing is completed yet")
                pg.click('.lib-filters button:has-text("Any status")')
                pg.locator(".lib-card").first.click()
                pg.wait_for_selector("#console:not(.hidden)")
                self.assertIn(f"#/case/{lib[0]['case']}", pg.url)
            self.assertEqual(P.errors, [])
