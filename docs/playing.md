# Playing SENTINEL

## The campaign

You're **Cody**, a new night-shift hire at **Ironlantern Security**, a fictional managed detection & response company. Each case is a chapter of the story:

- A briefing message opens each case. Re-read it any time from **Alert & brief**.
- After you **Submit report**, score yourself on the rubric at the top of the answer key (honor system). Every hint you opened costs points.
- Your score becomes **XP**. XP earns promotions, from New Hire (Probation) up to IR Lead.
- The debrief changes with your grade and sets up the next chapter, which unlocks when you finish the current one.
- **Hide & reset progress** removes the score so you can replay a case cold.

The story never adds evidence. What characters tell you is a claim; only the logs are evidence.

## Tutorial

New to the console? Press **Tutorial** on the HQ screen. It opens a practice case, "A Quiet Morning": six harmless events from a training PC where someone opens Notepad and saves a file. A guided tour highlights each widget and control in turn, and **Try it** tasks let you practice adding evidence, building a process tree, flagging an IOC and submitting a report. Use **Next**, **Back** and **Skip tour**. **🎓 Tour** in the case bar brings it back.

The tutorial never touches your real cases, XP, rank or saved layout. The template lives in `content/tutorial/practice/`. Each press of **Tutorial** copies it into a fresh, gitignored `content/tutorial/workspace/`, so you can replay it as often as you like.

## Working a case

1. Pick a chapter from the **Campaign** list on the HQ screen and read **Alert & brief**.
2. Work the **Playbook** and tick off tasks. Open **Hints** one at a time if stuck (the app counts how many you used).
3. Explore **Events** and **Event detail**: every raw field is there. Hover a field to **pivot** (search all events for it) or add it to your IOCs. **Add to evidence** and write a note on each item.
4. **Process tree** and **IOCs** start empty, and you fill them in. Add processes with **⑂ Add to tree**, then pick each one's parent yourself by matching `ParentProcessGuid` to `ProcessGuid`. Add a "not in evidence" node for parents that aren't in the data. Add IOCs from Event detail or by pasting a value. The app never works out relationships or indicators for you.
5. Set the case **Status** as you go. Every action lands in the **War room** log with a UTC timestamp, and you can post your own notes there.
6. Fill in the **Worksheet** and **Report** (**+ Evidence**, **+ IOCs** and **+ Tree** insert what you've built), then **Submit report** to unlock the answer key.

## Customizing the console

- **Move** a widget by dragging its ⠿ grip or title. **Resize** from any edge or corner (handles appear on hover).
- **⤢** maximizes a widget (Esc restores). **×** closes it; bring it back from **Widgets ▾**.
- **Layout ▾**: Triage, Investigate and Report presets. Any change you make is saved as **My layout**.
- **Lock** stops accidental moves. **⚙** sets accent color and density. **Columns ▾** in Events picks table columns.

Layout and appearance are remembered in your browser. Case work is saved as plain files in the case's folder under `content/cases/` (`worksheet.md`, `report.md`, `bookmarks.json`, `iocs.json`, `tree.json`, `activity.json`).
