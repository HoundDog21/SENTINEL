"use strict";

// =====================================================================
// Guided tour for the tutorial workspace.
//
// Highlights one part of the console at a time and explains it. "Try it" tasks
// tick themselves off when you do the action; the tour never does it for you
// and never checks whether your analysis is right (the practice answer key does
// that after you submit). Loaded after app.js and uses its globals.
// =====================================================================

const Tour = (() => {
  const KEY = "sentinel.tour.step";
  const ever = new Set();          // listeners the tour adds itself (layout preset, widgets menu)
  let i = 0, on = false, timer = null, manualPos = null, lastSig = "", startLook = null;
  let root, card, rings = [], backdrop;

  // ---------- small helpers ----------
  const wEl = (id) => (W[id]?.shown ? $(".grid-stack-item-content", W[id].item) : null);
  const imageOf = (key) => base(S.byKey.get(key)?.image).toLowerCase();
  const orig = { worksheet: null, report: null };
  const changed = (name) => orig[name] != null && S.data && S.data[name] !== orig[name];
  const submitBtn = () => $$("#casebar .btn").find((b) => /submit report|score your report|answer key/i.test(b.textContent));
  const visible = (el) => el && !el.classList.contains("hidden") ? el : null;

  function ensureShown(id) {
    if (id === "answer" && !S.state?.submitted) return;
    if (!W[id].shown) { showWidget(id); saveLayout(); }
  }

  function scrollTo(el) {
    if (!el) return;
    const sc = $(".grid-scroll");
    if (!sc.contains(el)) return;
    const r = el.getBoundingClientRect(), box = sc.getBoundingClientRect();
    if (r.top >= box.top && r.bottom <= box.bottom) return;
    sc.scrollBy({ top: r.top - box.top - Math.max(12, (box.height - r.height) / 2), behavior: "smooth" });
  }

  // ---------- the steps ----------
  const STEPS = [
    {
      title: "Welcome to the console",
      html: `<p>This is a <b>practice workspace</b>. It holds six harmless events from a training PC: someone logged on, opened Notepad and saved a file.</p>
        <p>Nothing here touches your real cases, XP, rank or saved layout. Every start from HQ gives you a fresh copy.</p>
        <p>Use <b>Next</b> and <b>Back</b> to move around. <b>Try it</b> tasks tick themselves off when you do them, and you can skip any of them. Drag this card by its title bar if it's in the way.</p>`,
    },
    {
      title: "Case bar",
      target: () => $("#casebar"),
      html: `<p>The strip across the top shows the case ID, severity, case <b>Status</b>, when you opened it, the time you've spent, and live counts of events, evidence, IOCs and playbook steps.</p>
        <p><b>Submit report</b> on the right unlocks the answer key. You'll use it near the end.</p>`,
      tasks: [{ text: "Change the Status from New to Triage", done: () => S.state.status !== "New" }],
    },
    {
      title: "Alert & brief",
      widget: "alert",
      html: `<p>What you're told up front: the alert, the evidence files and the guided steps. <b>📨 Re-read briefing message</b> reopens the message from Priya.</p>
        <p>The alert is a claim, not evidence. Only the logs are evidence.</p>`,
    },
    {
      title: "Playbook",
      widget: "playbook",
      html: `<p>The brief's guided steps as a checklist. Click a step to tick it off (or untick it). Each tick is logged in the War room.</p>
        <p>The ⚑ item at the bottom is a shortcut to Submit report.</p>`,
      tasks: [{ text: "Tick any step (you can untick it again)", done: () => S.state.steps.length > 0 }],
    },
    {
      title: "Hints",
      widget: "hints",
      html: `<p>Hints are grouped by playbook step. Open them one at a time, only when you're stuck.</p>
        <p>In real cases every hint you open costs points (3 each in Chapter 1), and an opened hint stays counted. <b>Practice hints are free.</b></p>`,
      tasks: [{ text: "Open a hint", done: () => S.state.hints.length > 0 }],
    },
    {
      title: "Events",
      widget: "events",
      html: `<p>Every record in the case data. The search box matches <b>any field</b>, including raw values like paths and GUIDs. The Event ID chips filter by type and show counts.</p>
        <p><b>Columns ▾</b> picks table columns. The sort menu switches between time order and record-ID order, which aren't always the same. A ★ marks events in your evidence.</p>`,
      tasks: [
        { text: "Type something in the search box", done: () => tourSaw.has("filter") },
        { text: "Click an Event ID chip to filter by type", done: () => tourSaw.has("chip") },
        { text: "Click a row to open it in Event detail", done: () => tourSaw.has("selected") },
      ],
    },
    {
      title: "Event detail",
      widget: "detail",
      html: `<p>The selected event in full: System fields, every EventData field and the raw JSON record. Nothing is hidden or summarized.</p>
        <p>Hover a field row to get two buttons. <b>⌕ pivot</b> searches all events for that value. <b>◇ IOC</b> adds it to your IOC list.</p>`,
      tasks: [{ text: "Hover a field and click ⌕ pivot", done: () => tourSaw.has("pivot") }],
    },
    {
      title: "Evidence",
      target: () => [wEl("evidence"), wEl("detail")],
      widget: "evidence",
      also: ["detail"],
      html: `<p>Your bookmarked events, always in time order. This becomes your timeline.</p>
        <p>In Event detail, press <b>☆ Add to evidence</b>. A <b>Your note</b> box appears. Write what the event shows and why it matters. Click an evidence item to reopen its event.</p>`,
      tasks: [
        { text: "Add an event to your evidence", done: () => S.bookmarks.length > 0 },
        { text: "Write a note on it", done: () => S.bookmarks.some((b) => (b.note || "").trim()) },
      ],
    },
    {
      title: "Process tree: add processes",
      target: () => [wEl("tree"), wEl("detail")],
      widget: "tree",
      also: ["detail"],
      html: `<p>The tree starts empty and you build it. Open a <b>process-create</b> event (Event ID 1) and press <b>⑂ Add to tree</b> in Event detail.</p>
        <p>To find a process's parent, take its <code>ParentProcessGuid</code> and search for it. The event whose <code>ProcessGuid</code> matches is the parent.</p>`,
      tasks: [
        { text: "Add notepad.exe's process-create event to the tree", done: () => S.tree.some((n) => n.key && imageOf(n.key) === "notepad.exe") },
        { text: "Find the event for its parent and add that too", done: () => S.tree.filter((n) => n.key).length >= 2 },
      ],
    },
    {
      title: "Process tree: link them",
      widget: "tree",
      html: `<p>Each node has a <b>Parent</b> menu. You choose the parent from the evidence. The app never guesses.</p>
        <p>Some parents never appear as their own process-create event. Type the name from <code>ParentImage</code> into the box at the top and press <b>+ Not-in-evidence node</b>, so the tree shows the gap instead of hiding it.</p>`,
      tasks: [
        { text: "Set a parent with a Parent menu", done: () => S.tree.some((n) => n.parent) },
        { text: "Add a not-in-evidence node", done: () => S.tree.some((n) => !n.key) },
      ],
    },
    {
      title: "IOCs",
      target: () => [wEl("indicators"), wEl("detail")],
      widget: "indicators",
      also: ["detail"],
      html: `<p>Indicators you've decided matter. Nothing is pre-filled. Flag a field with <b>◇ IOC</b> in Event detail, or paste a value here, pick its type and press <b>Add</b>.</p>
        <p>Click a value to pivot on it. Use the menu to fix its type and <b>×</b> to remove it. On harmless data like this, a real report's IOC list would be empty.</p>`,
      tasks: [{ text: "Add an IOC (any value, for practice)", done: () => S.iocs.length > 0 }],
    },
    {
      title: "War room",
      widget: "warroom",
      html: `<p>The case log. Every action you take lands here with a UTC timestamp: status changes, evidence, tree edits, hints and saves.</p>
        <p>Post your own notes too, such as a hunch, a question or a dead end. It keeps a record of how you reached your conclusion.</p>`,
      tasks: [{ text: "Post a note in the war room", done: () => S.activity.some((a) => a.type === "comment") }],
    },
    {
      title: "Worksheet",
      widget: "worksheet",
      html: `<p>Your working notes in Markdown, saved to <code>worksheet.md</code> in the case folder (here, the practice folder). Use it while you investigate. It's never graded.</p>
        <p><b>Preview</b> renders it. <b>Save</b> or ⌘S writes it to disk. An <b>● unsaved</b> marker shows when you have changes.</p>`,
      tasks: [{ text: "Type a line and save it", done: () => changed("worksheet") }],
    },
    {
      title: "Report",
      widget: "report",
      html: `<p>Your final incident report, saved to <code>report.md</code>. <b>+ Evidence</b>, <b>+ IOCs</b> and <b>+ Tree</b> insert what you've built as tables or text, at the cursor if you've clicked into the report and at the end otherwise.</p>
        <p>For practice, a few lines is enough: what happened, what classification you'd give it, and one thing the logs can't tell you.</p>`,
      tasks: [
        { text: "Insert your evidence or tree with a + button", done: () => tourSaw.has("report.md dirty") },
        { text: "Save the report", done: () => changed("report") },
      ],
    },
    {
      title: "Submit a practice report",
      target: () => submitBtn(),
      html: `<p><b>Submit report</b> unlocks the answer key. In a real case, treat your submission as final: you can keep editing, but score yourself against what you submitted.</p>
        <p>Save your report first. The dialog warns you if it's unsaved or still blank.</p>`,
      tasks: [{ text: "Submit your practice report", done: () => S.state.submitted }],
    },
    {
      title: "Answer key",
      target: () => wEl("answer") || submitBtn(),
      widget: "answer",
      keepMax: true,
      enter: () => { if (S.state.submitted && maxed !== "answer") showAnswer(); },
      html: `<p>After you submit, the answer key opens. At the top is the <b>rubric</b>. Honestly tick only what your report actually contained, with evidence behind it. Opened hints are subtracted.</p>
        <p>Your score becomes XP and a grade, and Priya sends a debrief. <b>This practice score doesn't count.</b> <b>Hide & reset progress</b> lets you replay a case cold.</p>
        <p class="tour-note">Haven't submitted? Go Back one step, or skip this one.</p>`,
      tasks: [{ text: "Tick the rubric items you earned and finalize your practice score", done: () => S.state.score != null }],
    },
    {
      title: "Layout presets",
      target: () => $("#layout-select").closest(".ctl"),
      html: `<p><b>Layout ▾</b> switches between <b>Triage</b>, <b>Investigate</b> and <b>Report</b> presets. As soon as you move or resize anything, the result is saved as <b>My layout</b>.</p>
        <p>In this tutorial, "My layout" is the practice board. Your real layout is untouched.</p>`,
      tasks: [{ text: "Pick a preset from Layout ▾", done: () => ever.has("layout") }],
    },
    {
      title: "Widgets menu",
      target: () => [$("#widgets-btn"), visible($("#widgets-pop"))],
      html: `<p><b>Widgets ▾</b> shows or hides any widget. A widget you close with <b>×</b> comes back from here.</p>
        <p><b>Tidy up</b> slides every widget up to close the gaps.</p>`,
      tasks: [{ text: "Open Widgets ▾ and hide or show a widget", done: () => ever.has("widgets") }],
    },
    {
      title: "Drag, resize & snap",
      target: () => wEl(["hints", "playbook", "alert", "warroom", "events"].find((id) => W[id].shown) || "events"),
      enter: () => { if (prefs.locked) setLocked(false); },
      html: `<p><b>Move</b> a widget by dragging its ⠿ grip or title. <b>Resize</b> from any edge or corner. The handles appear when you hover.</p>
        <p>While you drag, a snap grid appears and widgets stay exactly where you drop them. <b>⤢</b> maximizes a widget (Esc restores it) and <b>×</b> closes it.</p>`,
      tasks: [
        { text: "Drag a widget to a new spot", done: () => tourSaw.has("dragstop") },
        { text: "Resize a widget from an edge or corner", done: () => tourSaw.has("resizestop") },
        { text: "Maximize a widget with ⤢, then press Esc", done: () => tourSaw.has("max") && !maxed },
      ],
    },
    {
      title: "Lock",
      target: () => $("#lock-btn"),
      html: `<p><b>Lock</b> freezes the layout so a stray drag can't move anything. The grips fade and the resize handles disappear. Click it again to unlock.</p>`,
      tasks: [
        { text: "Lock the layout", done: () => tourSaw.has("lock") },
        { text: "Unlock it again", done: () => tourSaw.has("lock") && tourSaw.has("unlock") && !prefs.locked },
      ],
    },
    {
      title: "Settings",
      target: () => [$("#settings-btn"), visible($("#settings-pop"))],
      html: `<p><b>⚙</b> sets the accent color and density, and <b>Reset my layout</b> returns to the Triage preset.</p>
        <p>Changes you make here last only for this tutorial. Outside it, they're remembered in your browser.</p>`,
      tasks: [{ text: "Change the accent color or density", done: () => startLook && (prefs.accent !== startLook.accent || prefs.density !== startLook.density) }],
    },
    {
      title: "You're ready",
      finish: true,
      html: `<p>That's the whole loop: read the brief, explore events, collect evidence, build the tree, flag IOCs, write the report, submit and score it.</p>
        <p>Replay this any time from the <b>Tutorial</b> button on the HQ screen, or with <b>🎓 Tour</b> in the case bar while you're here. Chapter 1 is waiting in the Campaign list.</p>`,
    },
  ];

  // ---------- rendering ----------
  function build() {
    if (root) return;
    backdrop = h("div", { class: "tour-backdrop hidden" });
    card = h("div", { class: "tour-card", role: "dialog", "aria-live": "polite" });
    root = h("div", { class: "tour", id: "tour" }, backdrop, card);
    document.body.append(root);
    $("#layout-select").addEventListener("change", () => ever.add("layout"));
    $("#widgets-pop").addEventListener("change", () => ever.add("widgets"));
    window.addEventListener("resize", () => on && place());
  }

  function taskSig() {
    return (STEPS[i].tasks || []).map((t) => (safe(t.done) ? 1 : 0)).join("");
  }
  const safe = (fn) => { try { return !!fn(); } catch { return false; } };

  function renderCard() {
    const st = STEPS[i];
    const tasks = st.tasks || [];
    const allDone = tasks.length && tasks.every((t) => safe(t.done));
    const head = h("div", { class: "tour-head", title: "Drag to move this card" },
      h("span", { class: "tour-step" }, `${i + 1} / ${STEPS.length}`),
      h("b", {}, st.title),
      h("button", { class: "tour-x", title: "Hide the tour (reopen it with 🎓 Tour)", onclick: stop }, "×"));
    const body = h("div", { class: "tour-body" });
    body.innerHTML = st.html;  // authored text in this file, never case data
    const list = tasks.length ? h("div", { class: "tour-tasks" },
      h("div", { class: "tour-tasks-h" }, allDone ? "✓ Done" : "Try it"),
      tasks.map((t) => {
        const ok = safe(t.done);
        return h("div", { class: "tour-task" + (ok ? " ok" : "") }, h("span", { class: "tour-box" }, ok ? "✓" : ""), t.text);
      })) : null;
    const nav = st.finish
      ? h("div", { class: "tour-nav" },
          h("button", { class: "btn small", onclick: () => go(i - 1) }, "Back"),
          h("span", { class: "spacer" }),
          h("button", { class: "btn small", title: "Run the tour again on your current practice work", onclick: () => go(0) }, "Replay tour"),
          h("button", { class: "btn small", title: "Throw away this practice work and start over", onclick: launchTutorial }, "Start fresh"),
          h("button", { class: "btn small primary", onclick: () => (location.hash = "") }, "Back to HQ"))
      : h("div", { class: "tour-nav" },
          h("button", { class: "btn small", disabled: i === 0, onclick: () => go(i - 1) }, "Back"),
          h("button", { class: "btn small ghost", title: "Hide the tour. Reopen it with 🎓 Tour in the case bar.", onclick: stop }, "Skip tour"),
          h("span", { class: "spacer" }),
          h("button", { class: "btn small" + (!tasks.length || allDone ? " primary" : ""), onclick: () => go(i + 1) },
            tasks.length && !allDone ? "Skip step →" : "Next →"));
    card.replaceChildren(...[head, body, list, nav].filter(Boolean));
    dragCard(head);
    lastSig = taskSig();
  }

  function dragCard(handle) {
    handle.addEventListener("pointerdown", (e) => {
      if (e.target.closest("button")) return;
      const r = card.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
      handle.setPointerCapture(e.pointerId);
      const move = (ev) => {
        manualPos = { left: ev.clientX - dx, top: ev.clientY - dy };
        place();
      };
      const up = () => { handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", up); };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", up);
    });
  }

  function targets() {
    const st = STEPS[i];
    const t = st.target ? st.target() : st.widget ? wEl(st.widget) : null;
    return [t].flat().filter((el) => el && el.isConnected && el.getClientRects().length);
  }

  function place() {
    if (!on) return;
    const els = targets();
    const vw = innerWidth, vh = innerHeight, pad = 5;
    while (rings.length > els.length) rings.pop().remove();
    while (rings.length < els.length) { const r = h("div", { class: "tour-ring" }); root.insertBefore(r, card); rings.push(r); }
    let u = null;
    els.forEach((el, k) => {
      const r = el.getBoundingClientRect();
      const top = Math.max(r.top, 0), bottom = Math.min(r.bottom, vh);
      Object.assign(rings[k].style, { left: r.left - pad + "px", top: top - pad + "px", width: r.width + pad * 2 + "px", height: Math.max(0, bottom - top) + pad * 2 + "px" });
      rings[k].classList.toggle("primary", k === 0);
      rings[k].classList.toggle("dim", els.length === 1);
      u = u ? { left: Math.min(u.left, r.left), top: Math.min(u.top, top), right: Math.max(u.right, r.right), bottom: Math.max(u.bottom, bottom) }
            : { left: r.left, top, right: r.right, bottom };
    });
    backdrop.classList.toggle("hidden", !!els.length);

    const cw = card.offsetWidth, ch = card.offsetHeight, gap = 14, m = 10;
    let left, top;
    if (manualPos) ({ left, top } = manualPos);
    else if (!u) { left = (vw - cw) / 2; top = (vh - ch) / 2; }
    else if (vw - u.right >= cw + gap + m) { left = u.right + gap; top = u.top; }
    else if (u.left >= cw + gap + m) { left = u.left - gap - cw; top = u.top; }
    else if (vh - u.bottom >= ch + gap + m) { left = u.left; top = u.bottom + gap; }
    else if (u.top >= ch + gap + m) { left = u.left; top = u.top - gap - ch; }
    else { left = vw - cw - 18; top = vh - ch - 18; }   // target fills the screen: tuck into a corner
    card.style.left = Math.round(Math.max(m, Math.min(left, vw - cw - m))) + "px";
    card.style.top = Math.round(Math.max(m, Math.min(top, vh - ch - m))) + "px";
  }

  function tick() {
    if (!on || !S.tutorial) return;
    if (taskSig() !== lastSig) renderCard();
    place();
  }

  function go(n) {
    i = Math.max(0, Math.min(STEPS.length - 1, n));
    save(i);
    manualPos = null;
    const st = STEPS[i];
    closePopovers();
    if (maxed && !(st.keepMax && maxed === st.widget)) toggleMax(maxed);
    for (const id of [st.widget, ...(st.also || [])].filter(Boolean)) ensureShown(id);
    st.enter?.();
    renderCard();
    // Wait a frame for new widgets to lay out, then bring the target into view.
    requestAnimationFrame(() => { scrollTo(targets()[0]); place(); });
  }

  function start(n = 0) {
    build();
    tourSaw.clear(); ever.clear();
    orig.worksheet = S.data.worksheet; orig.report = S.data.report;
    startLook = { accent: prefs.accent, density: prefs.density };
    on = true;
    root.classList.remove("hidden");
    clearInterval(timer);
    timer = setInterval(tick, 250);
    go(n);
  }

  // Reopen where you left off (from 🎓 Tour), without resetting what you've done.
  function resume() {
    if (on) return go(i);
    build();
    on = true;
    root.classList.remove("hidden");
    clearInterval(timer);
    timer = setInterval(tick, 250);
    go(i);
  }

  function stop() {
    on = false;
    clearInterval(timer);
    root?.classList.add("hidden");
  }

  function save(n) { store.set(KEY, n); }
  function saved() { const n = store.get(KEY, 0); return Number.isInteger(n) && n >= 0 && n < STEPS.length ? n : 0; }

  return { start, resume, stop, save, saved, get steps() { return STEPS; }, get index() { return i; }, get running() { return on; } };
})();
