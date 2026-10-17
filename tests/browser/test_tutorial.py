"""The guided tutorial, end to end: HQ button → all tour steps with their practice tasks →
Back/Skip/resume/replay → isolation from your real prefs, XP and case files."""
import json
import os
import unittest
import urllib.request
from pathlib import Path

from helpers import Sandbox, fingerprint
from browser.common import Page, needs_browser

SHOTS = Path(os.environ.get("SENTINEL_SHOTS") or ".")   # set SENTINEL_SHOTS=dir to save screenshots
REAL_PREFS = {"accent": "#a78bfa", "density": "compact", "locked": True, "layoutChoice": "investigate", "custom": None,
              "columns": ["time", "eid", "type", "process", "detail"]}


@needs_browser
class Tutorial(unittest.TestCase):
    def test_tour(self):
        log, problems = [], []

        def check(c, m):
            log.append(("PASS " if c else "FAIL ") + m)
            if not c:
                problems.append(m)

        with Sandbox(unlock_all=False) as sb, Page() as P:
            URL, pg = sb.url, P.page
            snap = (lambda path: pg.screenshot(path=path)) if os.environ.get("SENTINEL_SHOTS") else (lambda path: None)

            def profile():
                return json.load(urllib.request.urlopen(URL + "/api/profile"))

            files_before = fingerprint(sb.root)
            pg.goto(URL)
            pg.evaluate("p => localStorage.setItem('sentinel.prefs.v1', JSON.stringify(p))", REAL_PREFS)
            pg.reload()
            xp_before = profile()

            # ---- HQ button ----
            pg.wait_for_selector("#tutorial-btn")
            snap(SHOTS / "00-hq.png")
            pg.click("#tutorial-btn")
            pg.wait_for_selector(".tour-card")
            pg.wait_for_timeout(700)
            check(pg.url.endswith("#/tutorial"), "Tutorial button opens #/tutorial")
            check(pg.locator("#crumb").inner_text().startswith("/ TUTORIAL"), "crumb says TUTORIAL")
            check(pg.locator(".pill.practice").count() == 1, "PRACTICE pill in case bar")
            check(pg.locator("#dialog[open]").count() == 0, "no briefing popup over the tour")
            shown = pg.evaluate("Object.values(W).filter(w => w.shown).map(w => w.id)")
            check(len(shown) == 11, f"practice board shows all 11 pre-submit widgets: {shown}")
            check(pg.evaluate("prefs.locked") is False, "practice layout starts unlocked even though real prefs are locked")

            def step():
                return pg.locator(".tour-step").inner_text()
            def title():
                return pg.locator(".tour-card .tour-head b").inner_text()
            def nxt():
                pg.locator(".tour-nav button", has_text="→").click(); pg.wait_for_timeout(450)
            def tasks_ok():
                return pg.locator(".tour-task.ok").count(), pg.locator(".tour-task").count()
            def all_done(label):
                pg.wait_for_timeout(400)
                ok, n = tasks_ok()
                check(ok == n and n > 0, f"[{title()}] {label}: {ok}/{n} tasks ticked")
                check("Next" in pg.locator(".tour-nav button", has_text="→").inner_text(), f"[{title()}] button turns into Next")
            def shot(n):
                snap(SHOTS / f"{n:02d}-{title().split(':')[0].replace(' ', '-').replace('&','and').lower()}.png")
            def ring_over(sel):
                """The primary highlight ring surrounds the element."""
                r = pg.locator(".tour-ring.primary").bounding_box(); e = pg.locator(sel).first.bounding_box()
                return r and e and r["x"] <= e["x"] + 1 and r["y"] <= max(e["y"], 0) + 1 and r["x"] + r["width"] >= e["x"] + e["width"] - 1
            def card_clear_of(sel):
                c = pg.locator(".tour-card").bounding_box(); e = pg.locator(sel).first.bounding_box()
                return c["x"] >= e["x"] + e["width"] or c["x"] + c["width"] <= e["x"] or c["y"] >= e["y"] + e["height"] or c["y"] + c["height"] <= e["y"]

            total = int(step().split("/")[1])
            check(step() == f"1 / {total}" and title() == "Welcome to the console", "starts at Welcome")
            shot(1)
            nxt()

            # 2 case bar: status
            check(title() == "Case bar", "step 2 Case bar"); shot(2)
            pg.select_option(".status-select", "Triage"); all_done("status set")
            nxt()
            # 3 alert
            check(title() == "Alert & brief" and ring_over('[data-w="alert"]'), "Alert highlighted"); shot(3)
            check(card_clear_of('.grid-stack-item[gs-id="alert"]'), "card doesn't cover the Alert widget")
            nxt()
            # 4 playbook
            check(title() == "Playbook" and ring_over('[data-w="playbook"]'), "Playbook highlighted"); shot(4)
            pg.locator(".pb-task").first.click(); all_done("ticked a step")
            nxt()
            # 5 hints
            check(title() == "Hints", "step Hints")
            pg.locator('[data-w="hints"] details summary').first.click(); all_done("opened a hint"); shot(5)
            nxt()
            # 6 events
            check(title() == "Events" and ring_over('[data-w="events"]'), "Events highlighted")
            pg.fill('[data-w="events"] input[type=search]', "notepad")
            pg.locator('[data-w="events"] .chip').first.click()
            pg.locator('[data-w="events"] .chip').first.click()
            pg.fill('[data-w="events"] input[type=search]', "")
            pg.locator('[data-w="events"] input[type=search]').dispatch_event("input")
            pg.locator("tr.row", has_text="notepad.exe").first.click()
            all_done("search, chip, row"); shot(6)
            nxt()
            # 7 detail: pivot
            check(title() == "Event detail", "step Event detail")
            row = pg.locator('[data-w="detail"] .kv tr', has_text="ProcessGuid").first
            row.hover(); row.locator("button", has_text="pivot").click()
            pg.wait_for_timeout(300)
            all_done("pivot"); shot(7)
            nxt()
            # 8 evidence: add + note (file-create event)
            check(title() == "Evidence", "step Evidence")
            pg.click('[data-w="events"] button:has-text("Clear")')
            pg.locator("tr.row", has_text="shopping-list.txt").first.click()
            pg.click('[data-w="detail"] button:has-text("Add to evidence")')
            pg.wait_for_timeout(300)
            pg.fill('[data-w="detail"] textarea', "Notepad saved shopping-list.txt to Documents.")
            pg.wait_for_timeout(900)
            all_done("evidence + note"); shot(8)
            check(pg.locator('[data-w="evidence"] .bm').count() == 1, "evidence item listed")
            nxt()
            # 9 tree add: notepad then explorer (found via ParentProcessGuid search)
            check(title() == "Process tree: add processes", "step tree add")
            pg.locator("tr.row", has_text="Process create").filter(has_text="notepad.exe").first.click()
            pg.click('[data-w="detail"] button:has-text("Add to tree")'); pg.wait_for_timeout(300)
            pguid = pg.evaluate("S.byKey.get(S.selected).pguid")
            pg.fill('[data-w="events"] input[type=search]', pguid)
            pg.locator('[data-w="events"] input[type=search]').dispatch_event("input")
            pg.locator("tr.row", has_text="explorer.exe").first.click()
            pg.click('[data-w="detail"] button:has-text("Add to tree")'); pg.wait_for_timeout(300)
            all_done("two processes in tree"); shot(9)
            nxt()
            # 10 tree link
            check(title() == "Process tree: link them", "step tree link")
            nodes = pg.evaluate("S.tree.map(n => [n.id, n.name])")
            notepad_sel = pg.locator('[data-w="tree"] .node', has=pg.locator('input[value="notepad.exe"]')).locator("select")
            exp_id = [i for i, n in nodes if n == "explorer.exe"][0]
            notepad_sel.select_option(exp_id); pg.wait_for_timeout(300)
            pg.fill('[data-w="tree"] input[placeholder^="Process seen only"]', "userinit.exe")
            pg.click('[data-w="tree"] button:has-text("Not-in-evidence")'); pg.wait_for_timeout(300)
            all_done("parent set + placeholder"); shot(10)
            nxt()
            # 11 IOCs via ◇ IOC
            check(title() == "IOCs", "step IOCs")
            pg.click('[data-w="events"] button:has-text("Clear")')
            pg.locator("tr.row", has_text="shopping-list.txt").first.click()
            r = pg.locator('[data-w="detail"] .kv tr', has_text="TargetFilename").first
            r.hover(); r.locator("button", has_text="IOC").click(); pg.wait_for_timeout(300)
            all_done("IOC flagged"); shot(11)
            nxt()
            # 12 war room
            check(title() == "War room", "step War room")
            pg.fill('[data-w="warroom"] .wr-input input', "Looks like normal Notepad use.")
            pg.keyboard.press("Enter"); all_done("note posted"); shot(12)
            nxt()
            # 13 worksheet
            check(title() == "Worksheet", "step Worksheet")
            ws = pg.locator('[data-w="worksheet"] textarea'); ws.click(); ws.press("End"); ws.type("\nPractice note.")
            pg.click('[data-w="worksheet"] button:has-text("Save")'); all_done("worksheet saved"); shot(13)
            nxt()
            # 14 report
            check(title() == "Report", "step Report")
            pg.click('[data-w="report"] button:has-text("+ Evidence")')
            pg.click('[data-w="report"] button:has-text("+ Tree")')
            pg.click('[data-w="report"] button:has-text("Save")'); all_done("report built + saved"); shot(14)
            nxt()
            # 15 submit
            check(title() == "Submit a practice report" and ring_over("#casebar .btn.primary"), "Submit button highlighted"); shot(15)
            pg.click('#casebar button:has-text("Submit report")'); pg.wait_for_selector("#dialog[open]")
            snap(SHOTS / "15b-submit-dialog.png")
            pg.click("#dialog-ok"); pg.wait_for_timeout(800)
            all_done("submitted")
            nxt()
            # 16 answer key: score
            check(title() == "Answer key" and pg.locator(".grid-stack-item.max[gs-id=answer]").count() == 1, "answer key maximized & highlighted")
            shot(16)
            for cb in pg.locator(".rub-item input").all()[:3]: cb.check()
            pg.click('button:has-text("Finalize score")'); pg.wait_for_selector("#dialog[open]")
            dtext = pg.locator("#dialog").inner_text()
            check("Practice score" in dtext and "no XP" in dtext, "debrief says practice / no XP")
            snap(SHOTS / "16b-debrief.png")
            pg.click("#dialog-ok"); pg.wait_for_timeout(600)
            check(pg.url.endswith("#/tutorial"), "stays in tutorial after scoring (no jump to HQ)")
            check("practice" in pg.locator("#casebar .ch-result").inner_text() and "XP" not in pg.locator("#casebar .ch-result").inner_text(), "case bar shows practice pts, not XP")
            all_done("scored")
            nxt()
            # 17 layout
            check(title() == "Layout presets" and pg.locator(".grid-stack-item.max").count() == 0, "layout step, answer un-maximized")
            pg.select_option("#layout-select", "investigate"); pg.wait_for_timeout(500)
            all_done("preset picked"); shot(17)
            nxt()
            # 18 widgets
            check(title() == "Widgets menu", "step Widgets")
            pg.click("#widgets-btn"); pg.wait_for_timeout(200)
            shot(18)
            pg.locator("#widgets-pop label.check", has_text="War room").locator("input").click()
            all_done("toggled a widget")
            nxt()
            # 19 drag/resize/max
            check(title() == "Drag, resize & snap", "step drag/resize"); 
            tgt = pg.evaluate("['hints','playbook','alert','warroom','events'].find(id => W[id].shown)")
            head = pg.locator(f'[data-w="{tgt}"] .w-head'); hb = head.bounding_box()
            sx, sy = hb["x"] + hb["width"] * 0.55, hb["y"] + hb["height"] / 2
            pg.mouse.move(sx, sy); pg.mouse.down(); pg.mouse.move(sx + 80, sy + 200, steps=12)
            check(pg.locator("#grid.snapping").count() == 1, "snap grid visible while dragging")
            shot(19)
            pg.mouse.up(); pg.wait_for_timeout(600)
            item = pg.locator(f'.grid-stack-item[gs-id="{tgt}"]'); item.hover(); pg.wait_for_timeout(200)
            hbx = item.locator(".ui-resizable-se").bounding_box()
            pg.mouse.move(hbx["x"] + 4, hbx["y"] + 4); pg.mouse.down(); pg.mouse.move(hbx["x"] + 120, hbx["y"] + 90, steps=10); pg.mouse.up()
            pg.wait_for_timeout(500)
            pg.locator(f'[data-w="{tgt}"] .w-actions button').first.click(); pg.wait_for_timeout(300)
            snap(SHOTS / "19b-maximized.png")
            pg.keyboard.press("Escape"); all_done("drag + resize + max")
            nxt()
            # 20 lock
            check(title() == "Lock", "step Lock")
            pg.click("#lock-btn"); pg.wait_for_timeout(200); shot(20); pg.click("#lock-btn")
            all_done("lock + unlock")
            nxt()
            # 21 settings
            check(title() == "Settings", "step Settings")
            pg.click("#settings-btn"); pg.locator("#settings-pop .swatch").nth(2).click(); pg.wait_for_timeout(200)
            shot(21); all_done("accent changed")
            nxt()
            # 22 finish
            check(title() == "You're ready" and step() == f"{total} / {total}", "finish step"); shot(22)

            # ---- Back / Skip / resume ----
            pg.get_by_role("button", name="Back", exact=True).click(); pg.wait_for_timeout(300)
            check(title() == "Settings", "Back goes to previous step")
            pg.locator(".tour-nav button", has_text="Skip tour").click(); pg.wait_for_timeout(300)
            check(pg.locator("#tour.hidden").count() == 1, "Skip tour hides it")
            pg.click("#tour-btn"); pg.wait_for_timeout(400)
            check(title() == "Settings", "🎓 Tour resumes at the same step")
            pg.reload(); pg.wait_for_selector(".tour-card"); pg.wait_for_timeout(600)
            check(title() == "Settings", "reload resumes tour at saved step")
            pg.locator(".tour-nav button", has_text="→").click(); pg.wait_for_timeout(300)

            # Replay
            pg.click('.tour-nav button:has-text("Replay tour")'); pg.wait_for_timeout(400)
            check(step() == f"1 / {total}", "Replay goes to step 1")
            check(pg.evaluate("S.bookmarks.length") == 1, "Replay keeps practice work")
            for _ in range(total - 1): pg.locator(".tour-nav button", has_text="→").click(); pg.wait_for_timeout(120)
            check(title() == "You're ready", "Next/Skip-step walks through every step")

            # Back to HQ: real prefs restored
            pg.click('.tour-nav button:has-text("Back to HQ")'); pg.wait_for_selector("#tutorial-btn")
            pg.wait_for_timeout(300)
            stored = pg.evaluate("JSON.parse(localStorage.getItem('sentinel.prefs.v1'))")
            check(stored == REAL_PREFS, f"saved prefs untouched by tutorial: {stored}")
            check(pg.evaluate("prefs.accent") == REAL_PREFS["accent"] and pg.evaluate("prefs.locked") is True, "real prefs active again at HQ")
            check(pg.locator("#tour.hidden").count() == 1, "tour hidden at HQ")
            xp_after = profile()
            check(xp_after["xp"] == xp_before["xp"] and xp_after["chapters"] == xp_before["chapters"], f"XP/chapters unchanged ({xp_before['xp']} -> {xp_after['xp']})")

            # real case still opens with real layout
            pg.click("button.chapter.available"); pg.wait_for_timeout(800)
            if pg.locator("#dialog[open]").count(): pg.click("#dialog-ok"); pg.wait_for_timeout(300)
            check(pg.evaluate("prefs.layoutChoice") == "investigate" and pg.evaluate("S.tutorial") is False, "real case uses real layout")
            check(pg.locator(".pill.practice").count() == 0 and pg.locator("#tour-btn").count() == 0, "no practice UI in real case")
            snap(SHOTS / "23-real-case.png")
            pg.goto(URL + "/#"); pg.wait_for_selector("#tutorial-btn")

            # Start again from HQ: fresh workspace
            pg.click("#tutorial-btn"); pg.wait_for_selector(".tour-card"); pg.wait_for_timeout(600)
            fresh = pg.evaluate("[S.bookmarks.length, S.iocs.length, S.tree.length, S.state.submitted, S.state.status]")
            check(fresh == [0, 0, 0, False, "New"], f"Tutorial button gives a fresh workspace: {fresh}")
            check(step() == f"1 / {total}", "fresh tutorial starts at step 1")

            # narrow viewport sanity
            pg.set_viewport_size({"width": 1100, "height": 760}); pg.wait_for_timeout(400)
            c = pg.locator(".tour-card").bounding_box()
            check(c["x"] >= 0 and c["y"] >= 0 and c["x"] + c["width"] <= 1100 and c["y"] + c["height"] <= 760, "card stays on screen at 1100x760")
            pg.locator(".tour-nav button", has_text="→").click(); pg.wait_for_timeout(400)
            snap(SHOTS / "24-small.png")
            check("null" not in pg.locator(".tour-card").inner_text(), "no stray 'null' in the tour card")
            pg.locator("tr.row").first.click(); pg.wait_for_timeout(200)
            check("null" not in pg.locator('[data-w="detail"] .w-body').inner_text().upper().split("RAW RECORD")[0].lower(), "no stray 'null' in Event detail")

            # the tutorial run (and opening the real chapter) must not change real case content
            changed = {k for k, v in fingerprint(sb.root).items() if files_before.get(k) != v}
            changed = {k for k in changed if not any(k.endswith(x) for x in ("state.json", "activity.json"))}
            check(not changed, f"authored content files unchanged by the tutorial: {sorted(changed)}")
            problems += P.errors
        self.assertEqual(problems, [], "\n".join(log))
