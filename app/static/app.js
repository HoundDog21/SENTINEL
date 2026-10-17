"use strict";

// =====================================================================
// helpers
// =====================================================================

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// Build DOM safely: evidence text always goes in via textContent, never innerHTML.
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

// Markdown from case files (authored content) and the user's own notes.
const md = (text) => marked.parse(text || "");

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
const put = (path, body) => api(path, { method: "PUT", body: typeof body === "string" ? body : JSON.stringify(body) });
const post = (path, body) => api(path, { method: "POST", body: body == null ? "" : JSON.stringify(body) });
const caseApi = (sub = "") => `/api/cases/${encodeURIComponent(S.cid)}${sub}`;

function flash(msg, ok = true) {
  const s = $("#status");
  s.textContent = msg;
  s.className = "status" + (ok ? " ok" : "");
  clearTimeout(flash.t);
  flash.t = setTimeout(() => (s.textContent = ""), 2500);
}

function confirmDialog(title, bodyNodes, okLabel = "OK", opts = {}) {
  const d = $("#dialog");
  d.classList.toggle("wide", !!opts.wide);
  $("#dialog-cancel").classList.toggle("hidden", opts.cancel === false);
  $("#dialog-title").textContent = title;
  $("#dialog-body").replaceChildren(...bodyNodes.filter(Boolean));
  $("#dialog-ok").textContent = okLabel;
  d.showModal();
  // Autofocus lands on the button at the bottom; start long messages at the top.
  requestAnimationFrame(() => (d.scrollTop = 0));
  return new Promise((resolve) => d.addEventListener("close", () => resolve(d.returnValue === "ok"), { once: true }));
}

const store = {
  get(k, dflt) { try { const v = localStorage.getItem(k); return v == null ? dflt : JSON.parse(v); } catch { return dflt; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
};

// Labels and field types come from app/eventids.json (served at /api/catalog), so a new log
// source only needs a catalog entry, not code.
let CATALOG = { channels: [], ioc_types: {} };
const channelOf = (e) => {
  const ch = String(e.channel || "").toLowerCase();
  return CATALOG.channels.find((c) => (c.exact ? ch === c.exact.toLowerCase() : c.contains && ch.includes(c.contains.toLowerCase())));
};
function eidLabel(e) {
  const c = channelOf(e);
  return c?.ids?.[e.eid] || c?.fallback || e.channel || "Event";
}
// How to cite an event: its EventRecordID, or file:line when the dataset has no record IDs.
const hasRec = (e) => e.record != null && e.record !== "";
const refOf = (e) => (hasRec(e) ? `rec ${e.record}` : `${e.source}:${e.line}`);
const refLabel = (x) => x.ref || `rec ${x.record}`;          // saved evidence/tree items (older ones have no ref)
const iocRef = (r) => (r ? (/^\d+$/.test(r) ? `rec ${r}` : r) : "");
const base = (p) => (p ? String(p).split(/[\\/]/).pop() : "");
// Field names and values as plain text, so a pasted path like C:\Windows\x.exe matches.
const flatText = (v) => v == null ? "" : typeof v === "object"
  ? Object.entries(v).map(([k, x]) => k + "\n" + flatText(x)).join("\n") : String(v);
const caseCode = (id) => { const m = /^(\d+)/.exec(id); return m ? `CASE-${m[1]}` : id.toUpperCase(); };
const sevClass = (s) => "sev-" + String(s || "medium").toLowerCase();

// Which EventData fields count as which indicator type: CATALOG.ioc_types.

// =====================================================================
// state
// =====================================================================

const S = {
  cid: null, data: null, events: [], byKey: new Map(),
  bookmarks: [], iocs: [], activity: [], state: null, selected: null,
  filter: "", eids: new Set(), sort: "time", dirty: {}, tree: [], tutorial: false,
};

// =====================================================================
// preferences (accent, density, lock, layouts): per-browser conveniences
// =====================================================================

const ACCENTS = ["#38bdf8", "#a78bfa", "#34d399", "#f59e0b", "#f472b6"];
const COLS = [
  { id: "time", label: "Time (UTC)", cell: (e) => e.time || "?" },
  { id: "record", label: "Record", cell: (e) => e.record ?? "" },
  { id: "eid", label: "EID", cell: (e) => e.eid ?? "", cls: "eid" },
  { id: "type", label: "Type", cell: (e) => eidLabel(e) },
  { id: "host", label: "Host", cell: (e) => e.host || "" },
  { id: "user", label: "User", cell: (e) => e.user || "" },
  { id: "process", label: "Process", cell: (e) => base(e.image), title: (e) => e.image || "" },
  { id: "pid", label: "Process GUID", cell: (e) => e.guid || "" },
  { id: "detail", label: "Detail", cell: (e) => e.cmd || e.target || "", cls: "wrap" },
];
const PREF_DEFAULTS = { accent: ACCENTS[0], density: "comfortable", locked: false, layoutChoice: "triage", custom: null,
  columns: ["time", "record", "eid", "type", "user", "process", "detail"] };
// Swapped for a throwaway copy while the tutorial is open, so practice never changes your real layout.
let prefs = Object.assign(structuredClone(PREF_DEFAULTS), store.get("sentinel.prefs.v1", {}));
const savePrefs = () => { if (!S.tutorial) store.set("sentinel.prefs.v1", prefs); };
// Things you did that the tutorial's "Try it" tasks look for. Nothing else reads this.
const tourSaw = new Set();

function applyAppearance() {
  document.documentElement.style.setProperty("--accent", prefs.accent);
  document.documentElement.dataset.density = prefs.density;
  if (grid) grid.cellHeight(prefs.density === "compact" ? 38 : 44);
}

function renderSettings() {
  const pop = $("#settings-pop");
  pop.replaceChildren(
    h("h4", {}, "Accent"),
    h("div", { class: "swatches" }, ACCENTS.map((c) => h("button", {
      class: "swatch" + (prefs.accent === c ? " on" : ""), style: `background:${c}`, title: c,
      onclick: () => { prefs.accent = c; savePrefs(); applyAppearance(); renderSettings(); },
    }))),
    h("h4", {}, "Density"),
    h("div", { class: "seg" }, ["comfortable", "compact"].map((d) => h("button", {
      class: prefs.density === d ? "on" : "",
      onclick: () => { prefs.density = d; savePrefs(); applyAppearance(); renderSettings(); },
    }, d[0].toUpperCase() + d.slice(1)))),
    h("h4", {}, "Layout"),
    h("button", { class: "btn small", onclick: () => { prefs.custom = null; prefs.layoutChoice = "triage"; savePrefs(); if (S.cid) applyLayoutChoice(); flash("Layouts reset"); } }, "Reset my layout"),
  );
}

// popovers
function bindPopover(btnSel, popSel, render) {
  const btn = $(btnSel), pop = $(popSel);
  btn.addEventListener("click", (e) => { e.stopPropagation(); const open = pop.classList.contains("hidden"); closePopovers(); if (open) { render(); pop.classList.remove("hidden"); } });
  pop.addEventListener("click", (e) => e.stopPropagation());
}
const closePopovers = () => $$(".popover").forEach((p) => p.classList.add("hidden"));
document.addEventListener("click", closePopovers);
bindPopover("#settings-btn", "#settings-pop", renderSettings);
bindPopover("#widgets-btn", "#widgets-pop", renderWidgetsMenu);

// =====================================================================
// widgets
// =====================================================================

const ICONS = {
  alert: "M12 3l10 18H2z M12 10v5 M12 18h.01",
  playbook: "M6 3v12 M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M18 9a9 9 0 0 1-9 9",
  hints: "M9 18h6 M10 22h4 M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z",
  events: "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01",
  tree: "M3 3h6v6H3z M15 15h6v6h-6z M6 9v6a3 3 0 0 0 3 3h6",
  detail: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M21 21l-5-5",
  evidence: "M12 2l3 7 7 .6-5.3 4.6L18.4 22 12 18l-6.4 4 1.7-7.8L2 9.6 9 9z",
  indicators: "M12 2v4 M12 18v4 M2 12h4 M18 12h4 M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z",
  warroom: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  worksheet: "M9 3h6v3H9z M7 4H5v17h14V4h-2 M8 11h8 M8 15h5",
  report: "M14 2H6v20h12V8z M14 2v6h6 M9 13h6 M9 17h6",
  answer: "M5 11h14v10H5z M8 11V7a4 4 0 0 1 7.5-2",
};
const svgIcon = (name, cls = "w-icon") => {
  const s = h("span", { class: cls });
  s.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" width="100%" height="100%"><path d="${ICONS[name]}"/></svg>`;
  return s;
};
const GRIP = '<svg viewBox="0 0 10 16" fill="currentColor"><circle cx="2.5" cy="3" r="1.4"/><circle cx="7.5" cy="3" r="1.4"/><circle cx="2.5" cy="8" r="1.4"/><circle cx="7.5" cy="8" r="1.4"/><circle cx="2.5" cy="13" r="1.4"/><circle cx="7.5" cy="13" r="1.4"/></svg>';

const WDEF = {
  alert:      { title: "Alert & brief" },
  playbook:   { title: "Playbook" },
  hints:      { title: "Hints" },
  events:     { title: "Events", body: "col" },
  tree:       { title: "Process tree" },
  detail:     { title: "Event detail" },
  evidence:   { title: "Evidence" },
  indicators: { title: "IOCs" },
  warroom:    { title: "War room", body: "flush wr" },
  worksheet:  { title: "Worksheet" },
  report:     { title: "Report" },
  answer:     { title: "Answer key" },
};

const PRESETS = {
  triage: [
    { id: "alert", x: 0, y: 0, w: 3, h: 7 }, { id: "playbook", x: 0, y: 7, w: 3, h: 9 },
    { id: "events", x: 3, y: 0, w: 6, h: 9 }, { id: "indicators", x: 3, y: 9, w: 3, h: 7 },
    { id: "warroom", x: 6, y: 9, w: 3, h: 7 }, { id: "detail", x: 9, y: 0, w: 3, h: 16 },
  ],
  investigate: [
    { id: "events", x: 0, y: 0, w: 7, h: 8 }, { id: "tree", x: 0, y: 8, w: 4, h: 8 },
    { id: "evidence", x: 4, y: 8, w: 3, h: 8 }, { id: "detail", x: 7, y: 0, w: 5, h: 10 },
    { id: "hints", x: 7, y: 10, w: 5, h: 6 },
  ],
  report: [
    { id: "worksheet", x: 0, y: 0, w: 4, h: 16 }, { id: "report", x: 4, y: 0, w: 5, h: 16 },
    { id: "evidence", x: 9, y: 0, w: 3, h: 8 }, { id: "indicators", x: 9, y: 8, w: 3, h: 8 },
  ],
};

const W = {};
for (const [id, def] of Object.entries(WDEF)) {
  const count = h("span", { class: "w-count" });
  const body = h("div", { class: "w-body" + (def.body ? " " + def.body : "") });
  const grip = h("span", { class: "w-grip", title: "Drag to move" });
  grip.innerHTML = GRIP;
  const widget = h("div", { class: "widget", "data-w": id },
    h("div", { class: "w-head" },
      grip, svgIcon(id), h("span", { class: "w-title", title: "Drag to move" }, def.title), count,
      h("div", { class: "w-actions" },
        h("button", { title: "Maximize (Esc to restore)", onclick: () => toggleMax(id) }, "⤢"),
        h("button", { title: "Close. Re-open it from Widgets.", onclick: () => { hideWidget(id); saveLayout(); } }, "×"))),
    body);
  const item = h("div", { class: "grid-stack-item", "gs-id": id }, h("div", { class: "grid-stack-item-content" }, widget));
  W[id] = { id, item, body, count, shown: false };
}
const setCount = (id, text) => (W[id].count.textContent = text ?? "");

let grid = null, applying = false;

function initGrid() {
  if (grid) return;
  grid = GridStack.init({
    // float: widgets stay exactly where you drop them (snapped to the grid) instead of floating up.
    column: 12, cellHeight: prefs.density === "compact" ? 38 : 44, margin: 5, float: true, animate: true, minRow: 16,
    draggable: { handle: ".w-head" },  // gridstack ignores drags that start on buttons/inputs/selects
    resizable: { handles: "n,ne,e,se,s,sw,w,nw" },
    columnOpts: { breakpoints: [{ w: 760, c: 1 }] },
  }, "#grid");
  grid.on("change", () => saveLayout());
  // Show the snap grid while dragging or resizing.
  const gridEl = $("#grid");
  grid.on("dragstart resizestart", () => {
    gridEl.style.setProperty("--snap-w", gridEl.clientWidth / grid.getColumn() + "px");
    gridEl.style.setProperty("--snap-h", grid.getCellHeight(true) + "px");
    gridEl.classList.add("snapping");
  });
  grid.on("dragstop resizestop", (ev) => { gridEl.classList.remove("snapping"); tourSaw.add(ev?.type); });
  setLocked(prefs.locked);
}

function posFor(id) {
  const src = prefs.layoutChoice === "custom" && prefs.custom ? prefs.custom : PRESETS[prefs.layoutChoice] || PRESETS.triage;
  return src.find((p) => p.id === id) || Object.values(PRESETS).flat().find((p) => p.id === id) || { w: 4, h: 8 };
}

function showWidget(id, pos) {
  const w = W[id];
  if (w.shown) return;
  const p = pos || posFor(id);
  for (const k of ["gs-x", "gs-y", "gs-w", "gs-h", "gs-auto-position"]) w.item.removeAttribute(k);
  w.item.setAttribute("gs-w", p.w ?? 4);
  w.item.setAttribute("gs-h", p.h ?? 8);
  if (p.x != null && p.y != null) { w.item.setAttribute("gs-x", p.x); w.item.setAttribute("gs-y", p.y); }
  else w.item.setAttribute("gs-auto-position", "true");
  w.item.setAttribute("gs-min-w", 2);
  w.item.setAttribute("gs-min-h", 3);
  $("#grid").append(w.item);
  grid.makeWidget(w.item);
  w.shown = true;
}

function hideWidget(id) {
  const w = W[id];
  if (!w.shown) return;
  if (w.item.classList.contains("max")) toggleMax(id);
  grid.removeWidget(w.item, false);
  w.item.remove();
  w.shown = false;
}

function applyLayout(layout) {
  // Clear, then place top-to-bottom at exact positions. Moving widgets one by one
  // makes them collide and push each other around.
  applying = true;
  if (maxed) toggleMax(maxed);
  grid.batchUpdate();
  for (const id of Object.keys(W)) hideWidget(id);
  const order = [...layout].sort((a, b) => a.y - b.y || a.x - b.x);
  for (const p of order) {
    if (W[p.id] && (p.id !== "answer" || S.state?.submitted)) showWidget(p.id, p);
  }
  grid.batchUpdate(false);
  setTimeout(() => (applying = false), 0);
}

function applyLayoutChoice() {
  const c = prefs.layoutChoice;
  applyLayout(c === "custom" && prefs.custom ? prefs.custom : PRESETS[c] || PRESETS.triage);
  $("#layout-select").value = c === "custom" && !prefs.custom ? "triage" : c;
}

function saveLayout() {
  if (applying || !grid || grid.getColumn() !== 12) return;
  prefs.custom = grid.save(false).map(({ id, x, y, w, h: hh }) => ({ id, x, y, w, h: hh }));
  prefs.layoutChoice = "custom";
  savePrefs();
  $("#layout-select").value = "custom";
}

$("#layout-select").addEventListener("change", (e) => {
  const v = e.target.value;
  if (v === "custom" && !prefs.custom) { flash("No saved layout yet. Move a widget to create one.", false); e.target.value = prefs.layoutChoice; return; }
  prefs.layoutChoice = v;
  savePrefs();
  applyLayoutChoice();
});

function renderWidgetsMenu() {
  const pop = $("#widgets-pop");
  pop.replaceChildren(
    h("h4", {}, "Show widgets"),
    ...Object.entries(WDEF).filter(([id]) => id !== "answer" || S.state?.submitted).map(([id, def]) =>
      h("label", { class: "check" },
        h("input", { type: "checkbox", checked: W[id].shown, onchange: (e) => { e.target.checked ? showWidget(id) : hideWidget(id); saveLayout(); } }),
        svgIcon(id), def.title)),
    h("h4", { style: "margin-top:12px" }, "Arrange"),
    h("button", { class: "btn small", title: "Slide every widget up to close the gaps", onclick: () => { grid.compact(); saveLayout(); flash("Tidied up"); } }, "Tidy up (close gaps)"),
  );
}

function setLocked(on) {
  prefs.locked = on;
  savePrefs();
  grid?.setStatic(on);
  $("#console").classList.toggle("locked", on);
  $("#console").classList.toggle("editing", !on);
  const b = $("#lock-btn");
  b.textContent = on ? "🔒 Locked" : "Unlocked";
  b.classList.toggle("on", on);
}
$("#lock-btn").addEventListener("click", () => { setLocked(!prefs.locked); tourSaw.add(prefs.locked ? "lock" : "unlock"); });

let maxed = null;
function toggleMax(id) {
  const w = W[id];
  const on = !w.item.classList.contains("max");
  if (maxed && maxed !== id) toggleMax(maxed);
  w.item.classList.toggle("max", on);
  $(".max-backdrop")?.remove();
  if (on) {
    document.body.append(h("div", { class: "max-backdrop", onclick: () => toggleMax(id) }));
    grid.movable(w.item, false); grid.resizable(w.item, false);
  } else if (!prefs.locked) {
    grid.movable(w.item, true); grid.resizable(w.item, true);
  }
  maxed = on ? id : null;
  if (on) tourSaw.add("max");
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && maxed && !$("#dialog").open) toggleMax(maxed); });

function focusWidget(id) {
  if (!W[id].shown) { showWidget(id); saveLayout(); }
  W[id].item.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// =====================================================================
// routing & home
// =====================================================================

window.addEventListener("hashchange", route);
$("#go-home").onclick = () => (location.hash = "");

async function route() {
  const id = decodeURIComponent(location.hash.replace(/^#\/?case\//, ""));
  const tutorial = location.hash === "#/tutorial";
  const target = tutorial ? "tutorial" : location.hash.startsWith("#/case/") && id ? id : null;
  if (S.cid && target !== S.cid && Object.values(S.dirty).some(Boolean)) {
    if (!confirm("You have unsaved changes in your worksheet or report. Leave without saving?")) {
      history.replaceState(null, "", S.tutorial ? "#/tutorial" : "#/case/" + encodeURIComponent(S.cid));
      return;
    }
    S.dirty = {};
  }
  if (!tutorial) exitTutorial();
  if (tutorial) return openTutorial().catch((e) => { flash(e.message, false); location.hash = ""; });
  if (target) return openCase(id).catch((e) => { flash(e.message, false); location.hash = ""; });
  showHome();
}

let clock = null;

async function showHome() {
  S.cid = null;
  clearInterval(clock);
  if (maxed) toggleMax(maxed);
  $("#console").classList.add("hidden");
  $("#case-tools").classList.add("hidden");
  $("#home").classList.remove("hidden");
  $("#crumb").textContent = "";
  try {
    renderHQ(await api("/api/profile"));
  } catch (e) {
    $("#home").replaceChildren(h("p", { class: "alert" }, "Could not load your profile: " + e.message));
  }
}

function renderHQ(pf) {
  const nxt = pf.next_rank;
  const pct = nxt ? Math.round(((pf.xp - pf.rank.xp) / (nxt.xp - pf.rank.xp)) * 100) : 100;
  const stat = (n, label) => h("div", { class: "stat" }, h("b", {}, n), h("span", {}, label));
  const side = (ch) => {
    if (ch.status === "completed") return ch.grade
      ? h("span", { class: "ch-result" }, h("span", { class: "grade grade-" + ch.grade }, ch.grade), `${ch.score} XP`)
      : h("span", { class: "pill done plain" }, "Submitted · score it");
    if (ch.status === "available") return h("span", { class: "btn primary small" }, ch.case_status && ch.case_status !== "New" ? "Continue" : "Start");
    if (ch.status === "locked") return h("span", { class: "muted small" }, `Finish Chapter ${ch.n - 1} to unlock`);
    return h("span", { class: "muted small" }, "Coming soon");
  };
  const playable = (ch) => ch.status === "available" || ch.status === "completed";
  $("#home").replaceChildren(
    h("section", { class: "hq-card" },
      h("div", { class: "hq-company" }, h("span", { class: "brand-mark" }),
        h("div", {}, h("b", {}, pf.company), h("div", { class: "muted small" }, pf.tagline))),
      h("div", { class: "hq-analyst" },
        h("div", { class: "hq-avatar" }, (pf.analyst || "?")[0].toUpperCase()),
        h("div", {}, h("div", { class: "hq-name" }, pf.analyst), h("div", { class: "hq-rank" }, pf.rank.title))),
      h("div", { class: "hq-xp" },
        h("div", { class: "hq-xp-top" }, h("b", {}, `${pf.xp} XP`), h("span", { class: "muted small" }, nxt ? `${nxt.xp - pf.xp} XP to ${nxt.title}` : "Top rank reached")),
        h("div", { class: "pb-bar" }, h("div", { style: `width:${Math.max(0, Math.min(100, pct))}%` }))),
      h("div", { class: "stats" }, stat(pf.closed, "Cases closed"), stat(pf.chapters.length, "Chapters"))),
    h("h2", { class: "hq-h" }, "Training"),
    h("div", { class: "chapter tutorial-card" },
      h("div", { class: "ch-num" }, "🎓"),
      h("div", { class: "ch-main" },
        h("div", { class: "ch-kicker" }, "Practice · no XP"),
        h("div", { class: "ch-title" }, "Tutorial: A Quiet Morning"),
        h("div", { class: "ch-teaser" }, "A guided tour of every widget and control, on six harmless events from a training PC. It uses its own practice workspace and never touches your cases, XP or layout.")),
      h("div", { class: "ch-side" }, h("button", { class: "btn primary small", id: "tutorial-btn", onclick: launchTutorial }, "Tutorial"))),
    h("h2", { class: "hq-h" }, "Campaign"),
    h("div", { class: "chapters" }, pf.chapters.map((ch) => h(playable(ch) ? "button" : "div", {
      class: "chapter " + ch.status,
      onclick: playable(ch) ? () => (location.hash = "#/case/" + encodeURIComponent(ch.case)) : null,
    },
      h("div", { class: "ch-num" }, playable(ch) ? String(ch.n) : "🔒"),
      h("div", { class: "ch-main" },
        h("div", { class: "ch-kicker" }, `Chapter ${ch.n} · ${ch.difficulty}`),
        h("div", { class: "ch-title" }, ch.title),
        h("div", { class: "ch-teaser" }, ch.teaser)),
      h("div", { class: "ch-side" }, side(ch))))),
  );
}

// =====================================================================
// case// =====================================================================
// case
// =====================================================================

async function openCase(id) {
  const [data, ev] = await Promise.all([
    api(`/api/cases/${encodeURIComponent(id)}`), api(`/api/cases/${encodeURIComponent(id)}/events`),
  ]);
  Object.assign(S, {
    cid: id, data, events: ev.events, errors: ev.errors, bookmarks: data.bookmarks, iocs: data.iocs,
    activity: data.activity, tree: data.tree || [], state: data.state, selected: null, filter: "", eids: new Set(), dirty: {},
  });
  S.byKey = new Map(S.events.map((e) => [e.key, e]));
  for (const e of S.events) e._search = flatText(e.raw).toLowerCase();

  $("#home").classList.add("hidden");
  $("#console").classList.remove("hidden");
  $("#case-tools").classList.remove("hidden");
  $("#crumb").textContent = S.tutorial ? "/ TUTORIAL (practice)" : "/ " + caseCode(id);

  initGrid();
  applyLayoutChoice();

  const briefBox = h("div", { class: "md" });
  briefBox.innerHTML = md(data.brief);
  W.alert.body.replaceChildren(...[
    data.story ? h("button", { class: "btn small story-btn", onclick: () => showStory(false) }, "📨 Re-read briefing message") : null,
    briefBox].filter(Boolean));
  buildEventsWidget();
  renderCasebar();
  renderPlaybook();
  renderHints();
  renderEvents();
  renderTree();
  renderDetail();
  renderEvidence();
  renderIndicators();
  renderWarroom();
  renderEditor("worksheet", data.worksheet);
  renderEditor("report", data.report);
  renderAnswer();
  if (data.story && !data.state.story_seen) showStory(true);
}

async function showStory(first) {
  const box = h("div", { class: "md story" });
  box.innerHTML = md(S.data.story);
  await confirmDialog(`📨 Incoming · Chapter ${S.data.chapter?.n ?? ""}: ${S.data.chapter?.title ?? S.data.title}`, [box],
    first ? "Accept case" : "Close", { cancel: false, wide: true });
  if (first) {
    const r = await put(caseApi("/state"), { story_seen: true });
    S.state = r.state;
    logAct("case", `Accepted case: ${S.data.chapter?.title ?? S.data.title}`);
  }
}

// ---------- case bar ----------

function renderCasebar() {
  const st = S.state, d = S.data;
  const statusSel = h("select", { class: "status-select", title: "Case status", onchange: (e) => setStatus(e.target.value) },
    d.statuses.map((s) => h("option", { value: s, selected: s === st.status }, s)));
  const elapsed = h("span", { class: "cb-val", id: "elapsed" }, "-");
  const done = st.steps.length, total = d.steps.length;
  const field = (label, ...val) => h("div", { class: "cb-field" }, h("span", { class: "cb-label" }, label), ...val);
  const stat = (n, label) => h("div", { class: "stat" }, h("b", {}, n), h("span", {}, label));

  $("#casebar").replaceChildren(...[
    h("div", { class: "cb-field" }, h("span", { class: "case-id" }, caseCode(S.cid)), h("span", { class: "pill " + sevClass(d.severity) }, d.severity)),
    S.tutorial ? h("div", { class: "cb-field" }, h("span", { class: "pill practice plain" }, "PRACTICE · no XP"),
      h("button", { class: "btn small", id: "tour-btn", title: "Show the guided tour", onclick: () => Tour.resume() }, "🎓 Tour")) : null,
    h("div", { class: "cb-title" },
      h("b", { title: d.title }, d.chapter ? `Chapter ${d.chapter.n}: ${d.chapter.title}` : d.title),
      h("span", { class: "muted small" }, d.meta)),
    field("Status", statusSel),
    field("Analyst", h("span", { class: "cb-val" }, `${d.profile.analyst} · ${d.profile.rank.title}`)),
    field("Opened (UTC)", h("span", { class: "cb-val" }, (st.opened_at || "").replace("T", " ").replace("Z", ""))),
    field("Time on case", elapsed),
    h("div", { class: "stats" },
      stat(S.events.length, "Events"), stat(S.bookmarks.length, "Evidence"),
      stat(S.iocs.length, "IOCs"), stat(`${done}/${total}`, "Playbook")),
    h("span", { class: "spacer" }),
    st.grade ? h("span", { class: "ch-result", title: S.tutorial ? "Practice score: not added to your XP" : null },
      h("span", { class: "grade grade-" + st.grade }, st.grade), S.tutorial ? `${st.score} pts · practice` : `${st.score} XP`) : null,
    st.submitted
      ? h("button", { class: "btn" + (st.score == null ? " primary" : ""), onclick: () => showAnswer() }, st.score == null ? "Score your report" : "Answer key")
      : h("button", { class: "btn primary", onclick: submitFlow }, "Submit report"),
  ].filter(Boolean));
  clearInterval(clock);
  const tick = () => {
    if (!st.opened_at) return;
    const s = Math.max(0, Math.floor((Date.now() - Date.parse(st.opened_at)) / 1000));
    const dd = Math.floor(s / 86400), hh = Math.floor((s % 86400) / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60;
    elapsed.textContent = (dd ? `${dd}d ` : "") + `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  };
  tick();
  clock = setInterval(tick, 1000);
}

async function setStatus(status) {
  const r = await put(caseApi("/state"), { status });
  S.state = r.state; S.activity = r.activity;
  renderWarroom();
  flash("Status: " + status);
}

// ---------- war room (activity log) ----------

const ACT_ICON = { comment: "✎", status: "◐", evidence: "★", ioc: "◆", tree: "⑂", playbook: "✓", hint: "?", file: "▤", case: "●" };

async function logAct(type, text) {
  try {
    S.activity.push(await post(caseApi("/activity"), { type, text }));
    renderWarroom();
  } catch (e) { flash("Could not log activity: " + e.message, false); }
}

function renderWarroom() {
  const body = W.warroom.body;
  const log = h("div", { class: "wr-log" }, S.activity.length ? S.activity.map((a) =>
    h("div", { class: "wr-entry " + a.type },
      h("time", { title: a.t + " (UTC)" }, (a.t || "").slice(11, 19)),
      h("span", { class: "ic" }, ACT_ICON[a.type] || "·"),
      h("span", { class: "txt" }, a.text))) : h("p", { class: "empty" }, "No activity yet."));
  const input = h("input", { type: "text", placeholder: "Add a note to the war room… (Enter)", maxlength: 4000 });
  const send = () => { const v = input.value.trim(); if (!v) return; input.value = ""; logAct("comment", v); };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  body.replaceChildren(log, h("div", { class: "wr-input" }, input, h("button", { class: "btn small", onclick: send }, "Post")));
  log.scrollTop = log.scrollHeight;
  setCount("warroom", S.activity.length || "");
  $("#casebar") && updateStats();
}

function updateStats() {
  const stats = $$("#casebar .stat b");
  if (stats.length !== 4) return;
  stats[0].textContent = S.events.length;
  stats[1].textContent = S.bookmarks.length;
  stats[2].textContent = S.iocs.length;
  stats[3].textContent = `${S.state.steps.length}/${S.data.steps.length}`;
}

// ---------- playbook ----------

function renderPlaybook() {
  const body = W.playbook.body;
  const steps = S.data.steps;
  const done = new Set(S.state.steps);
  setCount("playbook", steps.length ? `${done.size}/${steps.length}` : "");
  if (!steps.length) return body.replaceChildren(h("p", { class: "muted" }, "This case has no playbook steps."));
  const pct = Math.round((done.size / steps.length) * 100);
  const task = (i, text, isDone) => {
    const card = h("div", { class: "pb-card md", title: "Click to toggle done" });
    card.innerHTML = marked.parseInline(text);
    return h("div", { class: "pb-task" + (isDone ? " done" : ""), onclick: () => toggleStep(i, !isDone) },
      h("div", { class: "pb-dot" }, isDone ? "✓" : String(i + 1)), card);
  };
  body.replaceChildren(
    h("div", { class: "playbook" },
      h("div", { class: "pb-progress" }, h("div", { class: "pb-bar" }, h("div", { style: `width:${pct}%` })), `${pct}%`),
      ...steps.map((t, i) => task(i, t, done.has(i))),
      h("div", { class: "pb-task final" + (S.state.submitted ? " done" : ""), onclick: () => (S.state.submitted ? showAnswer() : submitFlow()) },
        h("div", { class: "pb-dot" }, "⚑"),
        h("div", { class: "pb-card" }, S.state.submitted ? "Submitted. Answer key unlocked." : h("b", {}, "Submit report & compare with answer key"))),
      h("p", { class: "muted small" }, "Full instructions for each step are in the Alert & brief widget."),
    ),
  );
}

async function toggleStep(i, on) {
  const set = new Set(S.state.steps);
  on ? set.add(i) : set.delete(i);
  const r = await put(caseApi("/state"), { steps: [...set].sort((a, b) => a - b) });
  S.state = r.state;
  renderPlaybook();
  updateStats();
  logAct("playbook", `${on ? "Completed" : "Reopened"} step ${i + 1}: ${S.data.steps[i].replace(/\*\*/g, "").slice(0, 60)}`);
}

// ---------- hints ----------

function renderHints() {
  const body = W.hints.body;
  if (!S.data.hints.trim()) { setCount("hints", ""); return body.replaceChildren(h("p", { class: "muted" }, "No hints for this case.")); }
  const box = h("div", { class: "md" });
  box.innerHTML = md(S.data.hints);
  body.replaceChildren(box);
  const used = new Set(S.state.hints);
  $$("details", box).forEach((d, i) => {
    if (used.has(i)) d.classList.add("used");
    d.addEventListener("toggle", async () => {
      if (!d.open || used.has(i)) return;
      used.add(i);
      d.classList.add("used");
      const r = await put(caseApi("/state"), { hints: [...used].sort((a, b) => a - b) });
      S.state = r.state;
      setCount("hints", `${used.size} used`);
      // Name the hint by the nearest heading above it.
      const section = $$("h3", box).filter((x) => x.compareDocumentPosition(d) & Node.DOCUMENT_POSITION_FOLLOWING).pop()?.textContent || "";
      logAct("hint", `Opened a hint${section ? ` (${section})` : ""}`);
    });
  });
  setCount("hints", used.size ? `${used.size} used` : "");
}

// ---------- events ----------

const E = {};
function buildEventsWidget() {
  E.filter = h("input", { type: "search", placeholder: "Search all fields (e.g. cmd.exe, Temp, 0x779c2)", autocomplete: "off", spellcheck: "false" });
  E.filter.addEventListener("input", () => { S.filter = E.filter.value.trim().toLowerCase(); if (S.filter) tourSaw.add("filter"); renderEvents(); });
  E.sort = h("select", { title: "Sort order", onchange: (e) => { S.sort = e.target.value; renderEvents(); } },
    h("option", { value: "time" }, "Time (UTC)"), h("option", { value: "record" }, "Record ID"));
  E.chips = h("div", { class: "chips" });
  E.errors = h("div", { class: "alert" + (S.errors.length ? "" : " hidden") },
    S.errors.length ? `${S.errors.length} record(s) could not be loaded:\n` + S.errors.join("\n") : "");
  E.table = h("table", { class: "events" });
  const colPop = h("div", { class: "popover right hidden", onclick: (e) => e.stopPropagation() });
  const renderColPop = () => colPop.replaceChildren(h("h4", {}, "Columns"), ...COLS.map((c) =>
    h("label", { class: "check" }, h("input", {
      type: "checkbox", checked: prefs.columns.includes(c.id),
      onchange: (ev) => {
        prefs.columns = COLS.map((x) => x.id).filter((id) => (id === c.id ? ev.target.checked : prefs.columns.includes(id)));
        savePrefs(); renderEvents();
      },
    }), c.label)));
  const colBtn = h("button", { class: "btn small", title: "Choose table columns", onclick: (e) => {
    e.stopPropagation(); const open = colPop.classList.contains("hidden"); closePopovers(); if (open) { renderColPop(); colPop.classList.remove("hidden"); }
  } }, "Columns ▾");
  W.events.body.replaceChildren(
    h("div", { class: "toolbar" }, E.filter, h("button", { class: "btn small", onclick: () => pivot("") }, "Clear"), E.sort,
      h("div", { class: "pop-wrap" }, colBtn, colPop)),
    E.chips, E.errors, h("div", { class: "table-wrap" }, E.table));
}

function pivot(value) {
  E.filter.value = value;
  S.filter = value.toLowerCase();
  renderEvents();
  if (value) tourSaw.add("pivot");
  if (value) { focusWidget("events"); flash(`Pivot: ${value.length > 40 ? value.slice(0, 40) + "…" : value}`); }
}

function renderChips() {
  const counts = new Map();
  for (const e of S.events) counts.set(e.eid, (counts.get(e.eid) || 0) + 1);
  E.chips.replaceChildren(...[...counts].sort((a, b) => a[0] - b[0]).map(([eid, n]) => h("button", {
    class: "chip" + (S.eids.has(eid) ? " on" : ""), title: "Show only this Event ID (click again to clear)",
    onclick: () => { S.eids.has(eid) ? S.eids.delete(eid) : (S.eids.add(eid), tourSaw.add("chip")); renderEvents(); },
  }, `${eid} · ${eidLabel(S.events.find((e) => e.eid === eid))} (${n})`)));
}

function visibleEvents() {
  const list = S.events.filter((e) => (!S.eids.size || S.eids.has(e.eid)) && (!S.filter || e._search.includes(S.filter)));
  const byRec = (a, b) => (Number(a.record) || 0) - (Number(b.record) || 0);
  return list.sort(S.sort === "record" ? byRec : (a, b) => (a.time || "").localeCompare(b.time || "") || byRec(a, b));
}

function renderEvents() {
  renderChips();
  const list = visibleEvents();
  const starred = new Set(S.bookmarks.map((b) => b.key));
  const cols = COLS.filter((c) => prefs.columns.includes(c.id));
  const head = h("tr", {}, h("th", {}, ""), cols.map((c) => h("th", {}, c.label)));
  const rows = list.map((e) => h("tr", { class: "row" + (S.selected === e.key ? " sel" : ""), "data-key": e.key, onclick: () => select(e.key) },
    h("td", { class: "star" }, starred.has(e.key) ? "★" : ""),
    cols.map((c) => h("td", { class: c.cls, title: c.title?.(e) }, c.cell(e)))));
  E.table.replaceChildren(h("thead", {}, head), h("tbody", {}, rows.length ? rows : h("tr", {}, h("td", { colspan: cols.length + 1, class: "empty" }, "No events match."))));
  setCount("events", list.length === S.events.length ? list.length : `${list.length}/${S.events.length}`);
}

// ---------- selection & detail ----------

function select(key) {
  S.selected = key;
  tourSaw.add("selected");
  $$("tr.row", E.table).forEach((r) => r.classList.toggle("sel", r.dataset.key === key));
  $$(".node", W.tree.body).forEach((n) => n.classList.toggle("sel", n.dataset.key === key));
  if (!W.detail.shown) focusWidget("detail");
  renderDetail();
}

function renderDetail() {
  const box = W.detail.body;
  const e = S.byKey.get(S.selected);
  setCount("detail", e ? refOf(e) : "");
  if (!e) return box.replaceChildren(h("p", { class: "muted" }, "Select an event in Events or Evidence to inspect it."));
  const sys = e.raw.Event?.System || {};
  // Some channels keep their fields in UserData instead of EventData. Show its leaf fields as-is.
  const userData = !e.raw.Event?.EventData && e.raw.Event?.UserData;
  const leaves = (o, out = {}) => { for (const [k, v] of Object.entries(o || {})) {
    if (k.endsWith("_attributes")) continue;
    if (v && typeof v === "object" && !Array.isArray(v)) leaves(v, out); else if (!(k in out)) out[k] = v;
  } return out; };
  const data = userData ? leaves(userData) : e.raw.Event?.EventData || {};
  const bm = S.bookmarks.find((b) => b.key === e.key);

  const row = (k, v, type) => {
    const text = v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v);
    const acts = text ? h("span", { class: "acts" },
      h("button", { title: "Pivot: search all events for this value", onclick: () => pivot(text) }, "⌕ pivot"),
      type && type !== "hash" ? h("button", { title: "Add to your IOC list", onclick: () => toggleIoc(type, text, hasRec(e) ? e.record : `${e.source}:${e.line}`) }, isIoc(type, text) ? "◆ in IOCs" : "◇ IOC") : null) : null;
    return h("tr", {}, h("th", {}, k), h("td", {}, acts, text));
  };

  box.replaceChildren(...[
    h("div", { class: "detail-head" },
      h("div", {}, h("h3", {}, `${e.eid} · ${eidLabel(e)}`), h("div", { class: "muted small mono" }, `Record ${hasRec(e) ? e.record : "none"} · ${e.source}:${e.line}`)),
      h("div", { class: "toolbar" },
        h("button", { class: "btn small", title: "Add this process to your process tree", onclick: () => addToTree(e) }, treeNodeFor(e.key) ? "⑂ In tree" : "⑂ Add to tree"),
        h("button", { class: "btn small" + (bm ? "" : " primary"), onclick: () => toggleBookmark(e) }, bm ? "★ In evidence" : "☆ Add to evidence"))),
    bm ? h("div", {},
      h("div", { class: "section-label" }, "Your note"),
      h("textarea", { rows: 3, placeholder: "What does this event show? Why does it matter?", oninput: (ev) => saveNote(e.key, ev.target.value) }, bm.note || "")) : null,
    h("div", { class: "section-label" }, "System"),
    h("table", { class: "kv" }, h("tbody", {},
      row("Time (UTC)", e.time || "?"), row("Computer", sys.Computer, "host"), row("Channel", sys.Channel), row("EventRecordID", sys.EventRecordID))),
    h("div", { class: "derived" }, `Time taken from ${e.time_src || "nowhere (missing)"}. Hover a row to pivot or flag it.`),
    h("div", { class: "section-label" }, userData ? "User data" : "Event data"),
    Object.keys(data).length
      ? h("table", { class: "kv" }, h("tbody", {}, Object.entries(data).map(([k, v]) => row(k, v, CATALOG.ioc_types?.[k] || "other"))))
      : h("p", { class: "muted small" }, "No EventData fields."),
    h("div", { class: "section-label" }, "Raw record"),
    h("pre", { class: "raw" }, JSON.stringify(e.raw, null, 2)),
  ].filter(Boolean));
}

// ---------- evidence (bookmarks) ----------

const saveBookmarks = () => put(caseApi("/doc/bookmarks"), S.bookmarks);
const sortedBookmarks = () => [...S.bookmarks].sort((a, b) => (a.time || "").localeCompare(b.time || ""));

async function toggleBookmark(e) {
  const i = S.bookmarks.findIndex((b) => b.key === e.key);
  const summary = `${eidLabel(e)}: ${base(e.image)} ${e.cmd || e.target || ""}`.trim();
  if (i >= 0) S.bookmarks.splice(i, 1);
  else S.bookmarks.push({ key: e.key, record: e.record, ref: refOf(e), eid: e.eid, time: e.time, host: e.host, summary, note: "" });
  await saveBookmarks();
  renderEvents(); renderEvidence(); renderDetail(); updateStats();
  logAct("evidence", `${i >= 0 ? "Removed from" : "Added to"} evidence: ${refOf(e)} (${eidLabel(e)}, ${base(e.image)})`);
}

let noteTimer;
function saveNote(key, text) {
  const b = S.bookmarks.find((x) => x.key === key);
  if (!b) return;
  b.note = text;
  clearTimeout(noteTimer);
  noteTimer = setTimeout(async () => { await saveBookmarks(); renderEvidence(); flash("Note saved"); }, 500);
}

function renderEvidence() {
  const list = sortedBookmarks();
  setCount("evidence", list.length || "");
  W.evidence.body.replaceChildren(...(list.length ? [
    h("p", { class: "muted small", style: "margin-top:0" }, "In time order. This is your timeline."),
    ...list.map((b) => h("div", { class: "bm", onclick: () => select(b.key) },
      h("div", { class: "bm-top" }, h("span", {}, b.time), h("span", {}, refLabel(b)), h("span", { class: "eid" }, `EID ${b.eid}`), h("span", {}, b.host || "")),
      h("div", { class: "mono small" }, b.summary),
      h("div", { class: "bm-note" + (b.note ? "" : " none") }, b.note || "No note yet: select it and write why it matters."))),
  ] : [h("p", { class: "empty" }, "No evidence yet. Select an event and press ☆ Add to evidence.")]));
}

// ---------- IOCs (yours: nothing is pre-filled) ----------

const IOC_TYPES = ["file", "hash", "process", "command", "host", "user", "ip", "domain", "registry", "other"];
const isIoc = (type, value) => S.iocs.some((i) => i.type === type && i.value === value);
const saveIocs = () => put(caseApi("/doc/iocs"), S.iocs);

async function toggleIoc(type, value, ref = "") {
  const i = S.iocs.findIndex((x) => x.type === type && x.value === value);
  if (i >= 0) S.iocs.splice(i, 1);
  else S.iocs.push({ type, value, ref: String(ref ?? ""), flagged_at: new Date().toISOString().slice(0, 19) + "Z" });
  await saveIocs();
  renderIndicators(); renderDetail(); updateStats();
  logAct("ioc", `${i >= 0 ? "Removed" : "Added"} IOC [${type}] ${value.length > 80 ? value.slice(0, 80) + "…" : value}`);
}

function renderIndicators() {
  setCount("indicators", S.iocs.length || "");
  const type = h("select", { title: "Indicator type" }, IOC_TYPES.map((t) => h("option", { value: t }, t)));
  const value = h("input", { type: "text", placeholder: "Paste a value: path, hash, domain…", spellcheck: "false" });
  const ref = h("input", { type: "text", placeholder: "Record #", title: "EventRecordID where you found it", style: "width:84px" });
  const add = () => {
    const v = value.value.trim();
    if (!v) return;
    if (isIoc(type.value, v)) return flash("Already in your list", false);
    toggleIoc(type.value, v, ref.value.trim());
  };
  value.addEventListener("keydown", (e) => e.key === "Enter" && add());
  W.indicators.body.replaceChildren(
    h("p", { class: "muted small", style: "margin-top:0" }, "Indicators you've decided matter. Nothing is pre-filled. Add them here, or hover a field in Event detail and click ◇ IOC."),
    h("div", { class: "toolbar", style: "margin-bottom:10px" }, type, value, ref, h("button", { class: "btn small primary", onclick: add }, "Add")),
    S.iocs.length
      ? h("div", {}, S.iocs.map((ioc) => h("div", { class: "ioc-row" },
          h("select", { title: "Change type", onchange: async (e) => { ioc.type = e.target.value; await saveIocs(); } },
            IOC_TYPES.map((t) => h("option", { value: t, selected: t === ioc.type }, t))),
          h("span", { class: "val", title: "Pivot: search events for this", onclick: () => pivot(ioc.value) }, ioc.value),
          h("span", { class: "n" }, iocRef(ioc.ref)),
          h("button", { class: "x", title: "Remove", onclick: () => toggleIoc(ioc.type, ioc.value) }, "×"))))
      : h("p", { class: "empty" }, "No IOCs yet."),
  );
}

// ---------- process tree (yours: you decide every parent) ----------

const saveTree = () => put(caseApi("/doc/tree"), S.tree);
const treeNodeFor = (key) => S.tree.find((n) => n.key === key);
const newId = () => Math.random().toString(36).slice(2, 10);

async function addToTree(e) {
  if (treeNodeFor(e.key)) return focusWidget("tree");
  S.tree.push({ id: newId(), key: e.key, record: e.record, ref: refOf(e), name: base(e.image) || refOf(e), parent: null });
  await saveTree();
  renderTree(); renderDetail(); focusWidget("tree");
  logAct("tree", `Added ${refOf(e)} (${base(e.image)}) to process tree`);
}

function treeChildren() {
  const ids = new Set(S.tree.map((n) => n.id));
  const kids = new Map(), roots = [];
  const t = (n) => (n.key && S.byKey.get(n.key)?.time) || "";
  for (const n of S.tree) {
    if (n.parent && ids.has(n.parent)) {
      if (!kids.has(n.parent)) kids.set(n.parent, []);
      kids.get(n.parent).push(n);
    } else roots.push(n);
  }
  const byTime = (a, b) => t(a).localeCompare(t(b));
  roots.sort(byTime);
  for (const list of kids.values()) list.sort(byTime);
  return { kids, roots };
}

function descendants(id, kids, out = new Set()) {
  for (const c of kids.get(id) || []) { out.add(c.id); descendants(c.id, kids, out); }
  return out;
}

function treeText() {
  const { kids, roots } = treeChildren();
  const label = (n) => `${n.name}${n.key ? ` (${refLabel(n)})` : " [not in evidence]"}`;
  const lines = [];
  const walk = (n, prefix, last, root) => {
    lines.push(root ? label(n) : prefix + (last ? "└── " : "├── ") + label(n));
    const ch = kids.get(n.id) || [];
    const next = root ? "" : prefix + (last ? "    " : "│   ");
    ch.forEach((c, i) => walk(c, next, i === ch.length - 1, false));
  };
  roots.forEach((r) => walk(r, "", true, true));
  return "```text\n" + lines.join("\n") + "\n```";
}

function renderTree() {
  const { kids, roots } = treeChildren();
  setCount("tree", S.tree.length || "");
  const placeholder = h("input", { type: "text", placeholder: "Process seen only as a parent, e.g. cmd.exe", spellcheck: "false" });
  const addPlaceholder = async () => {
    const name = placeholder.value.trim();
    if (!name) return;
    S.tree.push({ id: newId(), key: null, record: null, name, parent: null });
    await saveTree();
    renderTree();
    logAct("tree", `Added "${name}" to process tree (not in evidence)`);
  };
  placeholder.addEventListener("keydown", (e) => e.key === "Enter" && addPlaceholder());

  const renderNode = (n) => {
    const banned = descendants(n.id, kids).add(n.id);
    const parentSel = h("select", {
      title: "Which process launched this one? Decide from the evidence.",
      onchange: async (e) => {
        n.parent = e.target.value || null;
        await saveTree(); renderTree();
        const p = S.tree.find((x) => x.id === n.parent);
        logAct("tree", `Set parent of ${n.name} → ${p ? p.name : "top level"}`);
      },
    }, h("option", { value: "" }, "— top level / not decided —"),
      S.tree.filter((x) => !banned.has(x.id)).map((x) => h("option", { value: x.id, selected: x.id === n.parent }, `${x.name}${x.key ? ` (${refLabel(x)})` : " [not in evidence]"}`)));
    const name = h("input", { class: "node-name", type: "text", value: n.name, title: "Rename", spellcheck: "false",
      onchange: async (e) => { n.name = e.target.value.trim() || n.name; await saveTree(); renderTree(); } });
    const box = h("div", { class: "node" + (n.key ? "" : " unknown") + (n.key && S.selected === n.key ? " sel" : ""), "data-key": n.key || "" },
      h("div", { class: "node-row" }, name,
        n.key ? h("button", { class: "btn small", title: "Show this event", onclick: () => select(n.key) }, refLabel(n))
          : h("span", { class: "meta" }, "not in evidence"),
        h("button", { class: "x", title: "Remove from tree", onclick: async () => {
          S.tree.forEach((x) => { if (x.parent === n.id) x.parent = n.parent || null; });
          S.tree = S.tree.filter((x) => x.id !== n.id);
          await saveTree(); renderTree(); renderDetail();
          logAct("tree", `Removed ${n.name} from process tree`);
        } }, "×")),
      h("div", { class: "node-row" }, h("span", { class: "meta" }, "Parent:"), parentSel));
    const ch = kids.get(n.id) || [];
    return h("li", {}, box, ch.length ? h("ul", {}, ch.map(renderNode)) : null);
  };

  W.tree.body.replaceChildren(
    h("p", { class: "muted small", style: "margin-top:0" },
      "Your tree. Nothing is pre-filled. Add processes with ⑂ Add to tree in Event detail, then set each one's parent from the evidence (match ParentProcessGuid to ProcessGuid). Use a not-in-evidence node for parents you can't find."),
    h("div", { class: "toolbar", style: "margin-bottom:10px" }, placeholder, h("button", { class: "btn small", onclick: addPlaceholder }, "+ Not-in-evidence node")),
    roots.length ? h("div", { class: "tree" }, h("ul", {}, roots.map(renderNode))) : h("p", { class: "empty" }, "Empty. Select a process-create event and press ⑂ Add to tree."),
  );
}

// ---------- editors (worksheet / report) ----------

function renderEditor(name, text) {
  const file = name + ".md";
  const ta = h("textarea", { spellcheck: "true" }, text);
  const preview = h("div", { class: "preview md hidden" });
  const dirty = h("span", { class: "dirty" });
  const markDirty = (v) => { S.dirty[file] = v; if (v) tourSaw.add(file + " dirty"); dirty.textContent = v ? "● unsaved" : ""; setCount(name, v ? "unsaved" : ""); };
  const save = async () => {
    await put(caseApi(`/file/${file}`), ta.value);
    S.data[name] = ta.value;
    markDirty(false);
    flash("Saved " + file);
    logAct("file", `Saved ${file}`);
  };
  const previewBtn = h("button", { class: "btn small" }, "Preview");
  previewBtn.onclick = () => {
    const editing = preview.classList.toggle("hidden");
    ta.classList.toggle("hidden", !editing);
    if (!editing) preview.innerHTML = md(ta.value);
    previewBtn.textContent = editing ? "Preview" : "Edit";
  };
  let touched = false;
  ta.addEventListener("focus", () => (touched = true));
  const insert = (snippet, what) => {
    // At the cursor if you've clicked into the text, otherwise at the end.
    const pos = touched ? ta.selectionStart : ta.value.length;
    ta.value = ta.value.slice(0, pos) + "\n" + snippet + "\n" + ta.value.slice(pos);
    markDirty(true);
    flash(`Inserted ${what}`);
  };
  const esc = (s) => String(s ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
  const insertEvidence = () => {
    const list = sortedBookmarks();
    if (!list.length) return flash("No evidence to insert", false);
    insert(["| # | Time (UTC) | Host | Ref | Observation | Note |", "|---|---|---|---|---|---|",
      ...list.map((b, i) => `| ${i + 1} | ${esc(b.time)} | ${esc(b.host)} | ${esc(refLabel(b))} (EID ${esc(b.eid)}) | ${esc(b.summary)} | ${esc(b.note)} |`)].join("\n"), "evidence");
  };
  const insertIocs = () => {
    if (!S.iocs.length) return flash("No IOCs to insert", false);
    insert(["| Type | Value | Found in |", "|---|---|---|",
      ...S.iocs.map((i) => `| ${esc(i.type)} | \`${esc(i.value)}\` | ${esc(iocRef(i.ref))} |`)].join("\n"), "IOCs");
  };
  const insertTree = () => {
    if (!S.tree.length) return flash("Your process tree is empty", false);
    insert(treeText(), "process tree");
  };
  ta.addEventListener("input", () => markDirty(true));
  ta.addEventListener("keydown", (ev) => { if ((ev.metaKey || ev.ctrlKey) && ev.key === "s") { ev.preventDefault(); save(); } });
  W[name].body.replaceChildren(h("div", { class: "editor" },
    h("div", { class: "toolbar" },
      h("button", { class: "btn small primary", onclick: save }, "Save"), previewBtn,
      h("button", { class: "btn small", title: "Insert your evidence as a table at the cursor", onclick: insertEvidence }, "+ Evidence"),
      h("button", { class: "btn small", title: "Insert your IOCs as a table at the cursor", onclick: insertIocs }, "+ IOCs"),
      h("button", { class: "btn small", title: "Insert your process tree as text at the cursor", onclick: insertTree }, "+ Tree"),
      dirty, h("span", { class: "spacer" }), h("span", { class: "muted small" }, "⌘S")),
    ta, preview));
  markDirty(false);
}

window.addEventListener("beforeunload", (ev) => { if (Object.values(S.dirty).some(Boolean)) { ev.preventDefault(); ev.returnValue = ""; } });

// ---------- submit & answer key ----------

async function submitFlow() {
  if (S.state.submitted) return showAnswer();
  if (!S.data.has_answer_key) return flash("This case has no answer key", false);
  const unchanged = S.data.report.trim() === S.data.template_report.trim();
  const unsaved = Object.values(S.dirty).some(Boolean);
  const ok = await confirmDialog("Submit your report?", [
    h("p", {}, "Submitting unlocks the answer key for this case. Treat your report as final. You can keep editing, but compare honestly against what you submitted."),
    unchanged ? h("p", { class: "alert" }, "Your report.md still matches the blank template. Write your report first!") : null,
    unsaved ? h("p", { class: "alert" }, "You have unsaved changes. Save them first so your submission is complete.") : null,
    h("p", { class: "muted small" }, `Hints used: ${S.state.hints.length} · Playbook: ${S.state.steps.length}/${S.data.steps.length} · Evidence: ${S.bookmarks.length} · IOCs: ${S.iocs.length}`),
  ], "Submit & reveal");
  if (!ok) return;
  const r = await post(caseApi("/submit"));
  S.state.submitted = true;
  S.activity = r.activity;
  renderCasebar(); renderPlaybook(); renderWarroom();
  renderAnswer(r.answer);
  showAnswer();
  flash("Submitted. Score yourself at the top of the answer key.");
}

async function renderAnswer(text) {
  const body = W.answer.body;
  if (!S.state.submitted) { body.replaceChildren(); if (W.answer.shown) hideWidget("answer"); return; }
  if (text == null) {
    try { text = (await api(caseApi("/answer"))).answer; } catch { return; }
  }
  const box = h("div", { class: "md" });
  box.innerHTML = md(text);
  const scoreBox = h("section", { class: "score-panel" });
  renderScorePanel(scoreBox);
  body.replaceChildren(
    scoreBox,
    h("div", { class: "toolbar", style: "margin-bottom:8px" },
      h("span", { class: "muted small" }, "Compare against your report. Every claim here should trace to an event; check them yourself."),
      h("span", { class: "spacer" }),
      h("button", { class: "btn small danger", onclick: resetCase }, "Hide & reset progress")),
    box);
}

function showAnswer() {
  if (!W.answer.shown) { showWidget("answer", { w: 8, h: 14 }); saveLayout(); }
  if (!W.answer.item.classList.contains("max")) toggleMax("answer");
}

async function renderScorePanel(box) {
  let rb;
  try { rb = await api(caseApi("/rubric")); } catch { return box.replaceChildren(); }
  if (!rb.items.length) return box.replaceChildren();
  const checked = new Set(rb.checked);
  const max = rb.items.reduce((a, it) => a + it.points, 0);
  const penalty = rb.hints_used * rb.hint_penalty;
  const out = h("div", { class: "score-total" });
  const update = () => {
    const earned = [...checked].reduce((a, i) => a + rb.items[i].points, 0);
    const score = Math.max(0, earned - penalty);
    const grade = (rb.grades.find(([floor]) => score >= floor) || rb.grades[rb.grades.length - 1])[1];
    out.replaceChildren(h("span", { class: "grade grade-" + grade }, grade),
      h("div", {}, h("b", {}, `${score} / ${max} pts`),
        h("div", { class: "muted small" }, `${earned} earned − ${penalty} for ${rb.hints_used} hint${rb.hints_used === 1 ? "" : "s"} opened`)));
  };
  box.replaceChildren(
    h("h3", {}, rb.score == null ? "Score your report" : "Your score"),
    h("p", { class: "muted small" }, "Honor system. Read the reference investigation below, then tick only what your submitted report actually contained, with evidence behind it. Partial credit doesn't count. That's the point."),
    h("div", { class: "rubric" }, rb.items.map((it, i) => h("label", { class: "rub-item" },
      h("input", { type: "checkbox", checked: checked.has(i), onchange: (e) => { e.target.checked ? checked.add(i) : checked.delete(i); update(); } }),
      h("span", { class: "rub-pts" }, `+${it.points}`), h("span", {}, it.text)))),
    h("div", { class: "score-foot" }, out, h("span", { class: "spacer" }),
      rb.score != null ? h("button", { class: "btn", onclick: rereadDebrief }, "Re-read debrief") : null,
      h("button", { class: "btn primary", onclick: () => finalizeScore([...checked], box) }, rb.score == null ? "Finalize score & get debrief" : "Update score")),
  );
  update();
}

async function finalizeScore(list, box) {
  const r = await post(caseApi("/score"), { rubric: list });
  Object.assign(S.state, { score: r.score, grade: r.grade, rubric: list });
  S.activity = r.activity;
  S.data.profile.rank = r.rank_after;
  renderCasebar(); renderWarroom(); renderScorePanel(box);
  await showDebrief(r);
  if (!S.tutorial) location.hash = "";  // back to HQ to see the XP land
}

function showDebrief(r) {
  const box = h("div", { class: "md story" });
  box.innerHTML = md(r.debrief || "");
  const delta = r.xp_after != null ? r.xp_after - r.xp_before : null;
  const promoted = r.rank_before && r.rank_after && r.rank_before.title !== r.rank_after.title;
  return confirmDialog("Debrief", [
    h("div", { class: "debrief-head" },
      h("span", { class: "grade big grade-" + r.grade }, r.grade),
      h("div", {},
        h("b", {}, `${r.score} points`),
        S.tutorial ? h("div", { class: "muted small" }, "Practice score · no XP awarded, rank unchanged")
          : delta != null ? h("div", { class: "muted small" }, `${delta >= 0 ? "+" : ""}${delta} XP · total ${r.xp_after} XP · ${r.rank_after.title}`) : null)),
    promoted && !S.tutorial ? h("div", { class: "promo" }, `🎖 Promoted: ${r.rank_before.title} → ${r.rank_after.title}`) : null,
    box,
  ], "Continue", { cancel: false, wide: true });
}

async function rereadDebrief() {
  const r = await api(caseApi("/debrief"));
  showDebrief(r);
}

async function resetCase() {
  const ok = await confirmDialog("Reset progress?", [h("p", {}, "This hides the answer key and clears playbook, hint tracking and your score (your XP from this case is removed). Your worksheet, report, evidence, IOCs and tree are kept.")], "Reset");
  if (!ok) return;
  const r = await post(caseApi("/reset"));
  S.state = r.state; S.activity = r.activity;
  renderAnswer(); renderCasebar(); renderPlaybook(); renderHints(); renderWarroom();
}

// =====================================================================
// tutorial: practice workspace (case id "tutorial") with its own throwaway prefs
// =====================================================================

// Every widget on one scrollable board, so the tour can point at each in turn.
const TOUR_LAYOUT = [
  { id: "alert", x: 0, y: 0, w: 3, h: 8 }, { id: "playbook", x: 3, y: 0, w: 3, h: 8 },
  { id: "hints", x: 6, y: 0, w: 3, h: 8 }, { id: "warroom", x: 9, y: 0, w: 3, h: 8 },
  { id: "events", x: 0, y: 8, w: 7, h: 9 }, { id: "detail", x: 7, y: 8, w: 5, h: 13 },
  { id: "evidence", x: 0, y: 17, w: 4, h: 8 }, { id: "tree", x: 4, y: 17, w: 3, h: 8 },
  { id: "indicators", x: 7, y: 21, w: 5, h: 8 },
  { id: "worksheet", x: 0, y: 25, w: 6, h: 10 }, { id: "report", x: 6, y: 29, w: 6, h: 10 },
];
let realPrefs = null;

function enterTutorialPrefs() {
  if (!S.tutorial) realPrefs = prefs;
  S.tutorial = true;
  prefs = Object.assign(structuredClone(PREF_DEFAULTS), {
    accent: realPrefs.accent, density: realPrefs.density, locked: false,
    layoutChoice: "custom", custom: structuredClone(TOUR_LAYOUT),
  });
  applyAppearance();
  if (grid) setLocked(false);
}

function exitTutorial() {
  if (!S.tutorial) return;
  Tour.stop();
  S.tutorial = false;
  prefs = realPrefs;
  applyAppearance();
  if (grid) setLocked(prefs.locked);
}

async function launchTutorial() {
  try { await post("/api/tutorial/reset"); } catch (e) { return flash("Could not start the tutorial: " + e.message, false); }
  Tour.save(0);
  if (location.hash === "#/tutorial") openTutorial();
  else location.hash = "#/tutorial";
}

async function openTutorial() {
  enterTutorialPrefs();
  await openCase("tutorial");
  Tour.start(Tour.saved());
}

// =====================================================================
// boot
// =====================================================================

applyAppearance();
api("/api/catalog").then((c) => (CATALOG = c)).catch(() => flash("Could not load app/eventids.json: event labels unavailable", false)).finally(route);
