<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Admin Duties Checklist</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
  :root {
    --ground: #F2F4F1;
    --surface: #FFFFFF;
    --surface-2: #E7ECE8;
    --ink: #1A2420;
    --ink-muted: #5C6B64;
    --accent: #2F6F5E;
    --accent-ink: #FFFFFF;
    --accent-soft: #DCEAE4;
    --warn: #A24A2C;
    --warn-soft: #F3E1D8;
    --border: #D8DED9;
    --shadow: 0 1px 2px rgba(20, 30, 25, 0.04), 0 4px 16px rgba(20, 30, 25, 0.05);
  }

  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --ground: #101513;
      --surface: #1A211E;
      --surface-2: #222B27;
      --ink: #ECF1EE;
      --ink-muted: #9BAAA2;
      --accent: #59BC9E;
      --accent-ink: #0C1512;
      --accent-soft: rgba(89, 188, 158, 0.16);
      --warn: #E3936B;
      --warn-soft: rgba(227, 147, 107, 0.14);
      --border: #2B3733;
      --shadow: 0 1px 2px rgba(0, 0, 0, 0.2), 0 8px 24px rgba(0, 0, 0, 0.25);
    }
  }

  :root[data-theme="dark"] {
    --ground: #101513;
    --surface: #1A211E;
    --surface-2: #222B27;
    --ink: #ECF1EE;
    --ink-muted: #9BAAA2;
    --accent: #59BC9E;
    --accent-ink: #0C1512;
    --accent-soft: rgba(89, 188, 158, 0.16);
    --warn: #E3936B;
    --warn-soft: rgba(227, 147, 107, 0.14);
    --border: #2B3733;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.2), 0 8px 24px rgba(0, 0, 0, 0.25);
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }

  [hidden] { display: none !important; }

  body {
    background: var(--ground);
    color: var(--ink);
    font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
  }

  @media (prefers-reduced-motion: reduce) {
    * { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; }
  }

  .page { max-width: 720px; margin: 0 auto; padding: 48px 24px 96px; }
  header.top { margin-bottom: 28px; }

  .eyebrow {
    font-size: 12px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--accent); margin: 0 0 10px;
  }

  h1 {
    font-family: "Fraunces", Georgia, serif; font-weight: 600; font-size: clamp(28px, 5vw, 38px);
    line-height: 1.12; letter-spacing: -0.01em; margin: 0 0 10px; text-wrap: balance; color: var(--ink);
  }

  .lede { font-size: 15px; line-height: 1.55; color: var(--ink-muted); margin: 0 0 18px; max-width: 58ch; }

  .identity-bar {
    display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
    font-size: 12.5px; color: var(--ink-muted); margin-bottom: 18px;
  }
  .identity-bar strong { color: var(--ink); }
  .identity-sep { color: var(--border); }

  .link-btn {
    font: inherit; font-weight: 600; color: var(--accent); background: none; border: none;
    padding: 0; cursor: pointer; text-decoration: underline; text-decoration-color: transparent;
  }
  .link-btn:hover { text-decoration-color: currentColor; }
  .link-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .tabs { display: inline-flex; background: var(--surface-2); border-radius: 11px; padding: 3px; gap: 2px; }

  button.tab-btn {
    font: inherit; font-size: 13.5px; font-weight: 600; color: var(--ink-muted);
    background: transparent; border: none; border-radius: 8px; padding: 8px 16px; cursor: pointer;
  }
  button.tab-btn.is-active { background: var(--surface); color: var(--ink); box-shadow: var(--shadow); }
  button.tab-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .progress-row { display: flex; align-items: center; gap: 14px; margin-bottom: 6px; }
  .progress-track {
    flex: 1; height: 8px; border-radius: 999px; background: var(--surface-2);
    overflow: hidden; border: 1px solid var(--border);
  }
  .progress-fill { height: 100%; background: var(--accent); border-radius: 999px; transition: width 240ms ease; width: 0%; }
  .progress-label { font-variant-numeric: tabular-nums; font-size: 13px; font-weight: 600; color: var(--ink-muted); white-space: nowrap; }

  .toolbar {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    margin-top: 18px; margin-bottom: 22px; flex-wrap: wrap;
  }

  .status { font-size: 12.5px; color: var(--ink-muted); display: flex; align-items: center; gap: 6px; }
  .status .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
  .status.is-busy .dot { background: #C9A227; }
  .status.is-error .dot { background: var(--warn); }

  button.reset {
    font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--ink-muted);
    background: transparent; border: 1px solid var(--border); border-radius: 7px; padding: 7px 12px; cursor: pointer;
  }
  button.reset:hover { border-color: var(--ink-muted); color: var(--ink); }
  button.reset:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .toolbar-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

  button.toggle-sso {
    font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--accent);
    background: var(--accent-soft); border: 1px solid transparent; border-radius: 7px; padding: 7px 12px; cursor: pointer;
  }
  button.toggle-sso:hover { filter: brightness(0.96); }
  button.toggle-sso:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  button.toggle-sso[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); }

  .legend { font-size: 12.5px; color: var(--ink-muted); margin: 0 0 4px; }
  .legend .badge-sso { margin: 0 2px; }

  .categories { display: flex; flex-direction: column; gap: 14px; }

  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow); overflow: hidden; }
  .card.is-safety { border-left: 3px solid var(--warn); }
  .card:not(.is-safety) { border-left: 3px solid var(--accent); }

  .card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 16px 18px 12px; }
  .card-title { font-family: "Fraunces", Georgia, serif; font-weight: 600; font-size: 17px; margin: 0; color: var(--ink); }
  .card-count {
    font-variant-numeric: tabular-nums; font-size: 12.5px; font-weight: 600; color: var(--ink-muted);
    background: var(--surface-2); border-radius: 999px; padding: 3px 9px; white-space: nowrap;
  }
  .card.is-complete .card-count { color: var(--accent); background: var(--accent-soft); }

  ul.tasks { list-style: none; margin: 0; padding: 2px 10px 12px; }
  li.task { display: flex; align-items: flex-start; gap: 11px; padding: 9px 8px; border-radius: 9px; }
  li.task:hover { background: var(--surface-2); }

  li.task input[type="checkbox"] {
    appearance: none; -webkit-appearance: none; width: 19px; height: 19px; border-radius: 6px;
    border: 1.5px solid var(--border); background: var(--surface); flex-shrink: 0; margin-top: 1px;
    cursor: pointer; display: grid; place-content: center;
  }
  li.task input[type="checkbox"]:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  li.task input[type="checkbox"]::after {
    content: ""; width: 10px; height: 10px; transform: scale(0); transition: transform 120ms ease;
    box-shadow: inset 1em 1em var(--accent-ink);
    clip-path: polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 45% 62%);
  }
  li.task input[type="checkbox"]:checked { background: var(--accent); border-color: var(--accent); }
  li.task input[type="checkbox"]:checked::after { transform: scale(1); }

  .task-body { display: flex; flex-wrap: wrap; align-items: center; gap: 5px 9px; flex: 1; padding-top: 1px; }
  li.task label { font-size: 14.5px; line-height: 1.45; color: var(--ink); cursor: pointer; }
  li.task.is-done label { color: var(--ink-muted); text-decoration: line-through; text-decoration-color: var(--border); }

  .badge-sso, .badge-freq {
    font-size: 10.5px; font-weight: 600; letter-spacing: 0.02em; border-radius: 999px; padding: 2px 8px; white-space: nowrap;
  }
  .badge-sso { color: var(--accent); background: var(--accent-soft); }
  .badge-freq { color: var(--ink-muted); background: var(--surface-2); }
  li.task.is-done .badge-sso, li.task.is-done .badge-freq { opacity: 0.55; }

  select.assignee-select {
    font: inherit; font-size: 11.5px; font-weight: 600; color: var(--ink-muted); background: var(--surface);
    border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; cursor: pointer; max-width: 140px;
  }
  select.assignee-select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .done-meta { font-size: 11px; color: var(--ink-muted); width: 100%; padding-left: 1px; }

  footer.note { margin-top: 36px; font-size: 12.5px; line-height: 1.6; color: var(--ink-muted); border-top: 1px solid var(--border); padding-top: 18px; }

  .overlay {
    position: fixed; inset: 0; background: rgba(10, 14, 12, 0.55);
    display: flex; align-items: center; justify-content: center; padding: 20px; z-index: 50;
  }
  .overlay-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 26px; max-width: 400px; width: 100%; box-shadow: var(--shadow); }
  .overlay-title { font-family: "Fraunces", Georgia, serif; font-weight: 600; font-size: 21px; margin: 0 0 6px; color: var(--ink); }
  .overlay-sub { font-size: 13px; line-height: 1.5; color: var(--ink-muted); margin: 0 0 18px; }
  .panel-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 4px; }

  .name-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  button.name-chip {
    font: inherit; padding: 9px 14px; border-radius: 9px; border: 1px solid var(--border);
    background: var(--surface-2); font-weight: 600; font-size: 13.5px; cursor: pointer; color: var(--ink);
  }
  button.name-chip:hover { border-color: var(--accent); color: var(--accent); }
  button.name-chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .add-name-row { display: flex; gap: 8px; }
  .add-name-row input {
    flex: 1; min-width: 0; border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px;
    font: inherit; font-size: 13.5px; background: var(--surface); color: var(--ink);
  }
  .add-name-row input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  button.btn-primary {
    background: var(--accent); color: var(--accent-ink); border: none; border-radius: 8px; padding: 8px 14px;
    font: inherit; font-weight: 600; font-size: 13.5px; cursor: pointer; white-space: nowrap;
  }
  button.btn-primary:hover { filter: brightness(1.05); }
  button.btn-primary:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }

  .skip-row { margin-top: 14px; text-align: center; }
  .skip-row .link-btn { color: var(--ink-muted); font-weight: 500; }

  ul.staff-list { list-style: none; margin: 0 0 14px; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .staff-row {
    display: flex; align-items: center; justify-content: space-between; padding: 7px 6px 7px 12px;
    border-radius: 8px; background: var(--surface-2); font-size: 13.5px; font-weight: 600; color: var(--ink);
  }
  button.staff-remove { background: none; border: none; color: var(--ink-muted); cursor: pointer; font-size: 16px; line-height: 1; padding: 4px 8px; }
  button.staff-remove:hover { color: var(--warn); }

  .week-nav { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
  .week-nav button.nav-arrow {
    font: inherit; font-size: 13px; font-weight: 600; color: var(--ink-muted); background: var(--surface);
    border: 1px solid var(--border); border-radius: 7px; padding: 6px 11px; cursor: pointer;
  }
  .week-nav button.nav-arrow:hover { border-color: var(--ink-muted); color: var(--ink); }
  .week-nav button.nav-arrow:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .week-range { font-family: "Fraunces", Georgia, serif; font-weight: 600; font-size: 16px; margin: 0; flex: 1; min-width: 160px; }

  .table-scroll { overflow-x: auto; border: 1px solid var(--border); border-radius: 14px; background: var(--surface); box-shadow: var(--shadow); margin-bottom: 20px; }
  table.week-grid { border-collapse: collapse; width: 100%; min-width: 680px; }
  table.week-grid th, table.week-grid td { padding: 9px 12px; text-align: center; border-bottom: 1px solid var(--border); font-size: 13px; }
  table.week-grid thead th {
    font-weight: 600; font-size: 11.5px; color: var(--ink-muted); text-transform: uppercase;
    letter-spacing: 0.03em; background: var(--surface-2); white-space: nowrap;
  }
  table.week-grid th.col-task, table.week-grid td.col-task { text-align: left; width: 46%; }
  table.week-grid th.is-today, table.week-grid td.is-today-col { background: var(--accent-soft); }
  table.week-grid thead th.is-today { color: var(--accent); }

  tr.cat-row td {
    text-align: left; background: var(--surface-2); font-weight: 600; font-size: 12px; color: var(--ink-muted);
    text-transform: uppercase; letter-spacing: 0.03em; padding: 7px 12px;
  }
  tr.cat-row:first-child td { border-top: none; }

  td.task-cell { line-height: 1.4; }
  .task-cell-title { color: var(--ink); }
  .task-cell-badges { display: flex; flex-wrap: wrap; gap: 4px 6px; margin-top: 4px; }

  .badge-assignee {
    font-size: 10.5px; font-weight: 600; color: var(--ink-muted); background: var(--surface-2);
    border: 1px solid var(--border); border-radius: 999px; padding: 1px 7px; white-space: nowrap;
  }

  td.day-cell input[type="checkbox"] {
    appearance: none; -webkit-appearance: none; width: 18px; height: 18px; border-radius: 5px;
    border: 1.5px solid var(--border); background: var(--surface); cursor: pointer; display: grid; place-content: center;
  }
  td.day-cell input[type="checkbox"]:checked { background: var(--accent); border-color: var(--accent); }
  td.day-cell input[type="checkbox"]:checked::after {
    content: ""; width: 9px; height: 9px; box-shadow: inset 1em 1em var(--accent-ink);
    clip-path: polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 45% 62%);
  }
  td.day-cell input[type="checkbox"]:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  td.day-off { color: var(--border); }

  .week-extra { margin-top: 4px; }
  .week-extra .card { margin-bottom: 14px; }
</style>
</head>
<body>

<div id="app-shell">
  <div class="page">
    <header class="top">
      <p class="eyebrow">Daily Operations</p>
      <h1>Admin Duties Checklist</h1>
      <p class="lede">The full run-down of admin jobs, saved to your team's Supabase project. Pick your name to start ticking things off, hand a job to a teammate, and use "This Week" to see what's daily versus weekly, with real dates.</p>
      <div class="identity-bar">
        <span id="identity-current">Signed in as <strong id="identity-name">—</strong></span>
        <button class="link-btn" id="switch-user-btn" type="button">Switch</button>
        <span class="identity-sep">·</span>
        <button class="link-btn" id="manage-staff-btn" type="button">Manage staff</button>
      </div>
      <div class="tabs" role="tablist">
        <button class="tab-btn is-active" id="tab-btn-checklist" role="tab" aria-selected="true" aria-controls="panel-checklist" type="button">Checklist</button>
        <button class="tab-btn" id="tab-btn-week" role="tab" aria-selected="false" aria-controls="panel-week" type="button">This Week</button>
      </div>
    </header>

    <section class="tab-panel" id="panel-checklist" role="tabpanel">
      <div class="progress-row">
        <div class="progress-track"><div class="progress-fill" id="progress-fill"></div></div>
        <span class="progress-label" id="progress-label">0/0</span>
      </div>
      <p class="legend"><span class="badge-sso">8–9am</span><span class="badge-sso">2:45–4pm</span> badges mark tasks that fit an SSO's admin hours. <span class="badge-freq">Daily</span><span class="badge-freq">Weekly</span> show how often a job comes around.</p>
      <div class="toolbar">
        <span class="status" id="status"><span class="dot"></span><span id="status-text">Loading…</span></span>
        <div class="toolbar-actions">
          <button class="toggle-sso" id="sso-toggle" type="button" aria-pressed="false">SSO hours only</button>
          <button class="reset" id="reset-btn" type="button">Clear today's ticks</button>
        </div>
      </div>
      <main class="categories" id="categories"></main>
    </section>

    <section class="tab-panel" id="panel-week" role="tabpanel" hidden>
      <div class="week-nav">
        <button class="nav-arrow" id="week-prev" type="button">‹ Prev</button>
        <h2 class="week-range" id="week-range">Week of —</h2>
        <button class="nav-arrow" id="week-today-btn" type="button">This week</button>
        <button class="nav-arrow" id="week-next" type="button">Next ›</button>
      </div>
      <div class="table-scroll">
        <table class="week-grid">
          <thead><tr id="week-head-row"><th class="col-task">Task</th></tr></thead>
          <tbody id="week-body"></tbody>
        </table>
      </div>
      <div class="week-extra" id="week-extra"></div>
    </section>

    <footer class="note">
      Ticks and assignments save straight to Supabase and update live for anyone else with this page open. "Clear today's ticks" only clears the current day/week — past history stays on the This Week tab.
    </footer>
  </div>

  <div class="overlay" id="signin-overlay" hidden>
    <div class="overlay-card">
      <p class="eyebrow">Before you start</p>
      <h2 class="overlay-title">Who's ticking things off?</h2>
      <p class="overlay-sub">This labels your ticks and job assignments so the team can see who did what — it isn't a password, so please pick your real name.</p>
      <div class="name-grid" id="signin-name-grid"></div>
      <div class="add-name-row">
        <input type="text" id="signin-new-name" placeholder="Not on the list? Add your name" />
        <button type="button" id="signin-add-btn" class="btn-primary">Add &amp; continue</button>
      </div>
      <div class="skip-row"><button class="link-btn" id="signin-skip-btn" type="button">Just browsing — skip for now</button></div>
    </div>
  </div>

  <div class="overlay" id="staff-panel" hidden>
    <div class="overlay-card">
      <div class="panel-head">
        <h2 class="overlay-title">Manage staff</h2>
        <button class="link-btn" id="staff-panel-close" type="button">Close</button>
      </div>
      <p class="overlay-sub">Anyone with this page can edit this list — there's no password behind it, so it's really just a shared roster to keep names consistent.</p>
      <ul class="staff-list" id="staff-list"></ul>
      <div class="add-name-row">
        <input type="text" id="staff-new-name" placeholder="Add a name" />
        <button type="button" id="staff-add-btn" class="btn-primary">Add</button>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
(function () {
  "use strict";

  // ------------------------------------------------------------------
  // Supabase project — the anon/publishable key is safe to ship in the
  // page; Row Level Security policies on the tables (see supabase_schema.sql)
  // control what it can actually read or write.
  // ------------------------------------------------------------------
  var SUPABASE_URL = "https://cmqyrfekxgjdtuloseri.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_KbEHgtFyQ-rCoct7d71blQ_ZP_pfPGG";

  var sb = null;
  if (window.supabase && typeof window.supabase.createClient === "function") {
    sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  }

  // task.sso: "am" (8-9am), "pm" (2:45-4pm), "both", or null.
  // task.frequency: "daily" or "weekly". task.weekday: "Mon".."Fri" or null.
  // task.assignee / task.completions are populated at runtime from Supabase
  // (checklist_assignments / checklist_completions) — see loadRemoteState().
  var DEFAULT_STATE = {
    staff: ["Candice", "Vinnie", "Annette", "Bonnie", "Naomi"],
    categories: [
      {
        id: "email", title: "Email Monitoring", safety: false,
        tasks: [
          { id: "email-1", text: "Check emails as they come through", sso: null, frequency: "daily", weekday: null },
          { id: "email-2", text: "Forward emails on to the correct people", sso: null, frequency: "daily", weekday: null },
          { id: "email-3", text: "Respond to the admin email inbox", sso: null, frequency: "daily", weekday: null }
        ]
      },
      {
        id: "allocation", title: "Allocation Process", safety: false,
        tasks: [
          { id: "alloc-1", text: "Print referrals that come through via email no later than 9am Wednesday", sso: "am", frequency: "weekly", weekday: "Wed" },
          { id: "alloc-2", text: "Give a copy to the manager and the transition coordinator", sso: "am", frequency: "weekly", weekday: "Wed" },
          { id: "alloc-3", text: "Receive the transition coordinator's email with allocation outcomes", sso: null, frequency: "weekly", weekday: "Wed" },
          { id: "alloc-6", text: "Send communication to referring schools, BSE and TC (using the script) before 4:00pm Wednesday", sso: "pm", frequency: "weekly", weekday: "Wed" },
          { id: "alloc-7", text: "Send a separate email to the allocated teacher with the student's details (not documents)", sso: "pm", frequency: "weekly", weekday: "Wed" },
          { id: "alloc-5", text: "Create a OneDrive file for the student", sso: null, frequency: "weekly", weekday: "Wed" },
          { id: "alloc-4", text: "Upload the student's files to OneDrive", sso: null, frequency: "weekly", weekday: "Wed" },
          { id: "alloc-8", text: "Email LBU admin the student's information for the referrals database", sso: null, frequency: "weekly", weekday: "Wed" }
        ]
      },
      {
        id: "entry-meeting", title: "Entry Meeting Follow-Up", safety: false,
        tasks: [
          { id: "entry-1", text: "Scan and upload entry meeting documents to OneDrive", sso: null, frequency: "daily", weekday: null },
          { id: "entry-4", text: "Place the original documents in the student's box", sso: null, frequency: "daily", weekday: null },
          { id: "entry-5", text: "Distribute documents to the teacher", sso: null, frequency: "daily", weekday: null },
          { id: "entry-2", text: "Enrol the student through the EMS", sso: null, frequency: "daily", weekday: null },
          { id: "entry-3", text: "Send taxi forms to LBU admin email for signing", sso: null, frequency: "daily", weekday: null }
        ]
      },
      {
        id: "phone", title: "Phone Management", safety: false,
        tasks: [
          { id: "phone-1", text: "Transfer the phone over to mobile when not at the desk", sso: null, frequency: "daily", weekday: null },
          { id: "phone-2", text: "Switch the day/night switch each morning and afternoon", sso: "both", frequency: "daily", weekday: null },
          { id: "phone-3", text: "Check the message bank and action any messages left", sso: "both", frequency: "daily", weekday: null }
        ]
      },
      {
        id: "taxi", title: "Taxi Bookings", safety: false,
        tasks: [
          { id: "taxi-1", text: "Update and confirm bookings through the 131 Cabs app", sso: "am", frequency: "daily", weekday: null },
          { id: "taxi-2", text: "Upload each day's transport details to the bulletin", sso: "am", frequency: "daily", weekday: null },
          { id: "taxi-3", text: "Log pickups and the process for each student in OneNote", sso: null, frequency: "daily", weekday: null },
          { id: "taxi-4", text: "Monitor the app for student arrivals and departures, and update as required", sso: "both", frequency: "daily", weekday: null }
        ]
      },
      {
        id: "trt", title: "TRT Payroll", safety: false,
        tasks: [
          { id: "trt-1", text: "Email Naomi with the day's on-site TRTs so they're added to payroll", sso: "pm", frequency: "daily", weekday: null }
        ]
      },
      {
        id: "medication", title: "Medication", safety: false,
        tasks: [
          { id: "med-2", text: "Ensure medication documents (e.g. medication agreement form) are signed and filed with the medicine", sso: null, frequency: "daily", weekday: null },
          { id: "med-1", text: "Distribute medication to students who require it, at the correct times — set alarms as a reminder", sso: null, frequency: "daily", weekday: null }
        ]
      },
      {
        id: "bulletin", title: "Daily Bulletin Screen", safety: false,
        tasks: [
          { id: "bull-1", text: "Update the planning room screen so staff can read the daily bulletin", sso: "am", frequency: "daily", weekday: null }
        ]
      },
      {
        id: "foodbank", title: "Food Bank & Kickstart", safety: false,
        tasks: [
          { id: "food-1", text: "Work out what needs ordering for the week", sso: null, frequency: "weekly", weekday: null },
          { id: "food-2", text: "Place the weekly order", sso: null, frequency: "weekly", weekday: null }
        ]
      },
      {
        id: "hazards", title: "Hazard Management", safety: true,
        tasks: [
          { id: "haz-1", text: "Check for hazards reported via email", sso: null, frequency: "daily", weekday: null },
          { id: "haz-2", text: "Action and follow up on reported hazards", sso: null, frequency: "daily", weekday: null }
        ]
      },
      {
        id: "ventia", title: "Ventia", safety: false,
        tasks: [
          { id: "vent-1", text: "Handle communication with Ventia as required", sso: null, frequency: "daily", weekday: null },
          { id: "vent-2", text: "Sign off completed jobs in the Ventia portal", sso: null, frequency: "daily", weekday: null }
        ]
      }
    ]
  };

  // give every task a fresh assignee/completions slot
  function freshState() {
    var s = JSON.parse(JSON.stringify(DEFAULT_STATE));
    s.categories.forEach(function (cat) {
      cat.tasks.forEach(function (t) { t.assignee = null; t.completions = {}; });
    });
    return s;
  }

  var state = freshState();

  // ---------- date helpers ----------
  var WEEKDAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var WEEKDAY_COLS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

  function pad2(n) { return n < 10 ? "0" + n : "" + n; }
  function isoDate(d) { return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate()); }
  function dateOnly(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  function addDays(d, n) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
  function mondayOf(d) { var day = d.getDay(); var diff = day === 0 ? -6 : 1 - day; return addDays(dateOnly(d), diff); }
  function weekStartISO(d) { return isoDate(mondayOf(d)); }
  function todayDate() { return dateOnly(new Date()); }
  function formatDayLabel(d) { return WEEKDAY_SHORT[d.getDay()] + " " + d.getDate() + " " + MONTH_SHORT[d.getMonth()]; }
  function formatTime(ts) {
    var d = new Date(ts);
    var h = d.getHours(), m = d.getMinutes();
    var ampm = h >= 12 ? "pm" : "am";
    h = h % 12; if (h === 0) h = 12;
    return h + ":" + pad2(m) + ampm;
  }

  function periodKeyFor(task, refDate) { return task.frequency === "weekly" ? weekStartISO(refDate) : isoDate(refDate); }
  function isDoneOn(task, refDate) { var c = task.completions && task.completions[periodKeyFor(task, refDate)]; return !!(c && c.done); }
  function completionOn(task, refDate) { return (task.completions && task.completions[periodKeyFor(task, refDate)]) || null; }

  var currentUser = null;
  try { currentUser = window.localStorage.getItem("admin-checklist-user") || null; } catch (e) { /* ignore */ }

  var filterSso = false;
  var activeTab = "checklist";
  var weekOffset = 0;

  var SSO_BADGE_LABEL = { am: "8–9am", pm: "2:45–4pm", both: "8–9am · 2:45–4pm" };

  // ---------- DOM refs ----------
  var elCategories = document.getElementById("categories");
  var elFill = document.getElementById("progress-fill");
  var elLabel = document.getElementById("progress-label");
  var elStatus = document.getElementById("status");
  var elStatusText = document.getElementById("status-text");
  var elResetBtn = document.getElementById("reset-btn");
  var elSsoToggle = document.getElementById("sso-toggle");

  var elIdentityName = document.getElementById("identity-name");
  var elSwitchUserBtn = document.getElementById("switch-user-btn");
  var elManageStaffBtn = document.getElementById("manage-staff-btn");
  var elSigninOverlay = document.getElementById("signin-overlay");
  var elSigninNameGrid = document.getElementById("signin-name-grid");
  var elSigninNewName = document.getElementById("signin-new-name");
  var elSigninAddBtn = document.getElementById("signin-add-btn");
  var elSigninSkipBtn = document.getElementById("signin-skip-btn");

  var elStaffPanel = document.getElementById("staff-panel");
  var elStaffPanelClose = document.getElementById("staff-panel-close");
  var elStaffList = document.getElementById("staff-list");
  var elStaffNewName = document.getElementById("staff-new-name");
  var elStaffAddBtn = document.getElementById("staff-add-btn");

  var elTabBtnChecklist = document.getElementById("tab-btn-checklist");
  var elTabBtnWeek = document.getElementById("tab-btn-week");
  var elPanelChecklist = document.getElementById("panel-checklist");
  var elPanelWeek = document.getElementById("panel-week");

  var elWeekPrev = document.getElementById("week-prev");
  var elWeekNext = document.getElementById("week-next");
  var elWeekTodayBtn = document.getElementById("week-today-btn");
  var elWeekRange = document.getElementById("week-range");
  var elWeekHeadRow = document.getElementById("week-head-row");
  var elWeekBody = document.getElementById("week-body");
  var elWeekExtra = document.getElementById("week-extra");

  function setStatus(kind, text) {
    elStatus.className = "status" + (kind ? " is-" + kind : "");
    elStatusText.textContent = text;
  }

  function isSelectOrButton(el) { return !!(el.closest && el.closest("select, button, input, a")); }

  // ---------- identity ----------
  function updateIdentityBar() { elIdentityName.textContent = currentUser || "no one yet"; }

  function renderSigninNames() {
    elSigninNameGrid.innerHTML = "";
    state.staff.forEach(function (name) {
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "name-chip"; btn.textContent = name;
      btn.addEventListener("click", function () { chooseUser(name); });
      elSigninNameGrid.appendChild(btn);
    });
  }

  function chooseUser(name) {
    currentUser = name;
    try { window.localStorage.setItem("admin-checklist-user", name); } catch (e) { /* ignore */ }
    elSigninOverlay.hidden = true;
    updateIdentityBar();
    render();
  }

  elSwitchUserBtn.addEventListener("click", function () { renderSigninNames(); elSigninOverlay.hidden = false; });

  elSigninAddBtn.addEventListener("click", function () {
    var name = elSigninNewName.value.trim();
    if (!name) return;
    addStaffName(name);
    elSigninNewName.value = "";
    chooseUser(name);
  });
  elSigninNewName.addEventListener("keydown", function (e) { if (e.key === "Enter") elSigninAddBtn.click(); });
  elSigninSkipBtn.addEventListener("click", function () { elSigninOverlay.hidden = true; });

  // ---------- staff management (Supabase-backed) ----------
  async function addStaffName(name) {
    var exists = state.staff.some(function (n) { return n.toLowerCase() === name.toLowerCase(); });
    if (exists) return;
    state.staff.push(name);
    render();
    if (!sb) return;
    try {
      var res = await sb.from("checklist_staff").insert({ name: name });
      if (res.error) throw res.error;
    } catch (e) { setStatus("error", "Couldn't save the new name"); }
  }

  async function removeStaffName(name) {
    state.staff = state.staff.filter(function (n) { return n !== name; });
    state.categories.forEach(function (cat) {
      cat.tasks.forEach(function (t) { if (t.assignee === name) t.assignee = null; });
    });
    if (currentUser === name) {
      currentUser = null;
      try { window.localStorage.removeItem("admin-checklist-user"); } catch (e2) { /* ignore */ }
      updateIdentityBar();
    }
    renderStaffList();
    render();
    if (!sb) return;
    try {
      await sb.from("checklist_assignments").delete().eq("assignee", name);
      var res = await sb.from("checklist_staff").delete().eq("name", name);
      if (res.error) throw res.error;
    } catch (e) { setStatus("error", "Couldn't remove that name"); }
  }

  function renderStaffList() {
    elStaffList.innerHTML = "";
    state.staff.forEach(function (name) {
      var li = document.createElement("li");
      li.className = "staff-row";
      var span = document.createElement("span");
      span.textContent = name;
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "staff-remove";
      btn.setAttribute("aria-label", "Remove " + name);
      btn.textContent = "×";
      btn.addEventListener("click", function () { removeStaffName(name); });
      li.appendChild(span); li.appendChild(btn);
      elStaffList.appendChild(li);
    });
  }

  elManageStaffBtn.addEventListener("click", function () { renderStaffList(); elStaffPanel.hidden = false; });
  elStaffPanelClose.addEventListener("click", function () { elStaffPanel.hidden = true; });

  elStaffAddBtn.addEventListener("click", function () {
    var name = elStaffNewName.value.trim();
    if (!name) return;
    addStaffName(name);
    elStaffNewName.value = "";
    renderStaffList();
  });
  elStaffNewName.addEventListener("keydown", function (e) { if (e.key === "Enter") elStaffAddBtn.click(); });

  // ---------- tabs ----------
  function setTab(tab) {
    activeTab = tab;
    elTabBtnChecklist.classList.toggle("is-active", tab === "checklist");
    elTabBtnWeek.classList.toggle("is-active", tab === "week");
    elTabBtnChecklist.setAttribute("aria-selected", String(tab === "checklist"));
    elTabBtnWeek.setAttribute("aria-selected", String(tab === "week"));
    elPanelChecklist.hidden = tab !== "checklist";
    elPanelWeek.hidden = tab !== "week";
    render();
  }
  elTabBtnChecklist.addEventListener("click", function () { setTab("checklist"); });
  elTabBtnWeek.addEventListener("click", function () { setTab("week"); });

  // ---------- writes (Supabase-backed completions / assignments) ----------
  async function setDoneOn(task, refDate, done) {
    var key = periodKeyFor(task, refDate);
    if (done) task.completions[key] = { done: true, by: currentUser || "Unknown", at: Date.now() };
    else delete task.completions[key];
    render();
    if (!sb) return;
    setStatus("busy", "Saving…");
    try {
      var res;
      if (done) {
        res = await sb.from("checklist_completions").upsert(
          { task_id: task.id, period_key: key, done_by: currentUser || "Unknown", done_at: new Date().toISOString() },
          { onConflict: "task_id,period_key" }
        );
      } else {
        res = await sb.from("checklist_completions").delete().eq("task_id", task.id).eq("period_key", key);
      }
      if (res.error) throw res.error;
      setStatus("", "Saved");
    } catch (e) {
      setStatus("error", "Couldn't save — check your connection");
    }
  }

  async function setAssignee(task, name) {
    task.assignee = name || null;
    render();
    if (!sb) return;
    setStatus("busy", "Saving…");
    try {
      var res;
      if (name) {
        res = await sb.from("checklist_assignments").upsert(
          { task_id: task.id, assignee: name, updated_at: new Date().toISOString() },
          { onConflict: "task_id" }
        );
      } else {
        res = await sb.from("checklist_assignments").delete().eq("task_id", task.id);
      }
      if (res.error) throw res.error;
      setStatus("", "Saved");
    } catch (e) {
      setStatus("error", "Couldn't save — check your connection");
    }
  }

  function buildAssigneeSelect(task) {
    var sel = document.createElement("select");
    sel.className = "assignee-select";
    sel.setAttribute("aria-label", "Assigned to");
    var optNone = document.createElement("option");
    optNone.value = ""; optNone.textContent = "Unassigned";
    sel.appendChild(optNone);
    state.staff.forEach(function (name) {
      var opt = document.createElement("option");
      opt.value = name; opt.textContent = name;
      if (task.assignee === name) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener("click", function (e) { e.stopPropagation(); });
    sel.addEventListener("change", function () { setAssignee(task, sel.value || null); });
    return sel;
  }

  function freqBadgeText(task) {
    if (task.frequency === "weekly") return task.weekday ? "Weekly · " + task.weekday : "Weekly";
    return "Daily";
  }

  function totals() {
    var done = 0, total = 0;
    var today = todayDate();
    state.categories.forEach(function (cat) {
      cat.tasks.forEach(function (t) { total++; if (isDoneOn(t, today)) done++; });
    });
    return { done: done, total: total };
  }

  // ---------- render: checklist tab ----------
  function renderChecklist() {
    var today = todayDate();
    elCategories.innerHTML = "";
    state.categories.forEach(function (cat) {
      var visibleTasks = filterSso ? cat.tasks.filter(function (t) { return !!t.sso; }) : cat.tasks;
      if (filterSso && visibleTasks.length === 0) return;

      var catDone = visibleTasks.filter(function (t) { return isDoneOn(t, today); }).length;
      var card = document.createElement("section");
      card.className = "card" + (cat.safety ? " is-safety" : "") + (visibleTasks.length && catDone === visibleTasks.length ? " is-complete" : "");

      var head = document.createElement("div");
      head.className = "card-head";
      var title = document.createElement("h2");
      title.className = "card-title"; title.textContent = cat.title;
      var count = document.createElement("span");
      count.className = "card-count"; count.textContent = catDone + "/" + visibleTasks.length;
      head.appendChild(title); head.appendChild(count);
      card.appendChild(head);

      var list = document.createElement("ul");
      list.className = "tasks";

      visibleTasks.forEach(function (task) {
        var done = isDoneOn(task, today);
        var li = document.createElement("li");
        li.className = "task" + (done ? " is-done" : "");

        var checkboxId = "cb-" + task.id;
        var checkbox = document.createElement("input");
        checkbox.type = "checkbox"; checkbox.id = checkboxId; checkbox.checked = done;

        var body = document.createElement("div");
        body.className = "task-body";

        var label = document.createElement("label");
        label.setAttribute("for", checkboxId); label.textContent = task.text;
        body.appendChild(label);

        var freqBadge = document.createElement("span");
        freqBadge.className = "badge-freq"; freqBadge.textContent = freqBadgeText(task);
        body.appendChild(freqBadge);

        if (task.sso) {
          var badge = document.createElement("span");
          badge.className = "badge-sso"; badge.textContent = SSO_BADGE_LABEL[task.sso] || task.sso;
          body.appendChild(badge);
        }

        body.appendChild(buildAssigneeSelect(task));

        if (done) {
          var c = completionOn(task, today);
          if (c) {
            var meta = document.createElement("span");
            meta.className = "done-meta";
            meta.textContent = "Done by " + c.by + " · " + formatTime(c.at);
            body.appendChild(meta);
          }
        }

        function toggle() { setDoneOn(task, today, !isDoneOn(task, today)); }
        checkbox.addEventListener("change", toggle);
        li.addEventListener("click", function (e) { if (e.target === checkbox || isSelectOrButton(e.target)) return; toggle(); });

        li.appendChild(checkbox); li.appendChild(body); list.appendChild(li);
      });

      card.appendChild(list);
      elCategories.appendChild(card);
    });
  }

  // ---------- render: week tab ----------
  function currentWeekMonday() { return addDays(mondayOf(todayDate()), weekOffset * 7); }

  function renderWeekHead(dates, todayIso) {
    elWeekHeadRow.innerHTML = "";
    var th0 = document.createElement("th");
    th0.className = "col-task"; th0.textContent = "Task";
    elWeekHeadRow.appendChild(th0);
    dates.forEach(function (d) {
      var th = document.createElement("th");
      if (isoDate(d) === todayIso) th.className = "is-today";
      th.textContent = formatDayLabel(d);
      elWeekHeadRow.appendChild(th);
    });
  }

  function renderWeek() {
    var monday = currentWeekMonday();
    var dates = [];
    for (var i = 0; i < 5; i++) dates.push(addDays(monday, i));
    var friday = dates[4];
    var todayIso = isoDate(todayDate());

    elWeekRange.textContent = "Week of " + formatDayLabel(monday) + " – " + formatDayLabel(friday);
    renderWeekHead(dates, todayIso);

    elWeekBody.innerHTML = "";
    elWeekExtra.innerHTML = "";
    var extraCard = null, extraList = null;

    state.categories.forEach(function (cat) {
      var pinned = cat.tasks.filter(function (t) { return t.frequency === "daily" || (t.frequency === "weekly" && t.weekday); });
      var anyDay = cat.tasks.filter(function (t) { return t.frequency === "weekly" && !t.weekday; });

      if (pinned.length) {
        var catRow = document.createElement("tr");
        catRow.className = "cat-row";
        var catCell = document.createElement("td");
        catCell.colSpan = 6; catCell.textContent = cat.title;
        catRow.appendChild(catCell);
        elWeekBody.appendChild(catRow);

        pinned.forEach(function (task) {
          var row = document.createElement("tr");
          row.className = "task-row";

          var taskCell = document.createElement("td");
          taskCell.className = "task-cell col-task";
          var titleSpan = document.createElement("div");
          titleSpan.className = "task-cell-title"; titleSpan.textContent = task.text;
          taskCell.appendChild(titleSpan);

          var badges = document.createElement("div");
          badges.className = "task-cell-badges";
          var fb = document.createElement("span");
          fb.className = "badge-freq"; fb.textContent = freqBadgeText(task);
          badges.appendChild(fb);
          if (task.sso) {
            var sb2 = document.createElement("span");
            sb2.className = "badge-sso"; sb2.textContent = SSO_BADGE_LABEL[task.sso] || task.sso;
            badges.appendChild(sb2);
          }
          if (task.assignee) {
            var ab = document.createElement("span");
            ab.className = "badge-assignee"; ab.textContent = task.assignee;
            badges.appendChild(ab);
          }
          taskCell.appendChild(badges);
          row.appendChild(taskCell);

          dates.forEach(function (d) {
            var td = document.createElement("td");
            var iso = isoDate(d);
            var colShort = WEEKDAY_COLS[d.getDay() === 0 ? 6 : d.getDay() - 1];
            var applies = task.frequency === "daily" || task.weekday === colShort;
            if (iso === todayIso) td.classList.add("is-today-col");
            if (!applies) {
              td.className += " day-off"; td.textContent = "—";
            } else {
              td.className += " day-cell";
              var cb = document.createElement("input");
              cb.type = "checkbox"; cb.checked = isDoneOn(task, d);
              var c = completionOn(task, d);
              if (c) cb.title = "Done by " + c.by + " · " + formatTime(c.at);
              cb.setAttribute("aria-label", task.text + " — " + formatDayLabel(d));
              cb.addEventListener("change", function () { setDoneOn(task, d, !isDoneOn(task, d)); });
              td.appendChild(cb);
            }
            row.appendChild(td);
          });

          elWeekBody.appendChild(row);
        });
      }

      if (anyDay.length) {
        if (!extraCard) {
          extraCard = document.createElement("section");
          extraCard.className = "card";
          var xhead = document.createElement("div");
          xhead.className = "card-head";
          var xtitle = document.createElement("h2");
          xtitle.className = "card-title"; xtitle.textContent = "Weekly (any day this week)";
          xhead.appendChild(xtitle);
          extraCard.appendChild(xhead);
          extraList = document.createElement("ul");
          extraList.className = "tasks";
          extraCard.appendChild(extraList);
          elWeekExtra.appendChild(extraCard);
        }
        anyDay.forEach(function (task) {
          var done = isDoneOn(task, monday);
          var li = document.createElement("li");
          li.className = "task" + (done ? " is-done" : "");

          var cb = document.createElement("input");
          cb.type = "checkbox";
          var cbId = "wk-" + task.id;
          cb.id = cbId; cb.checked = done;

          var body = document.createElement("div");
          body.className = "task-body";
          var label = document.createElement("label");
          label.setAttribute("for", cbId); label.textContent = cat.title + " — " + task.text;
          body.appendChild(label);

          var fb2 = document.createElement("span");
          fb2.className = "badge-freq"; fb2.textContent = "Weekly";
          body.appendChild(fb2);

          if (task.assignee) {
            var ab2 = document.createElement("span");
            ab2.className = "badge-assignee"; ab2.textContent = task.assignee;
            body.appendChild(ab2);
          }

          function toggle() { setDoneOn(task, monday, !isDoneOn(task, monday)); }
          cb.addEventListener("change", toggle);
          li.addEventListener("click", function (e) { if (e.target === cb || isSelectOrButton(e.target)) return; toggle(); });

          li.appendChild(cb); li.appendChild(body); extraList.appendChild(li);
        });
      }
    });
  }

  elWeekPrev.addEventListener("click", function () { weekOffset--; render(); });
  elWeekNext.addEventListener("click", function () { weekOffset++; render(); });
  elWeekTodayBtn.addEventListener("click", function () { weekOffset = 0; render(); });

  // ---------- top-level render ----------
  function render() {
    var t = totals();
    elFill.style.width = (t.total ? (100 * t.done / t.total) : 0) + "%";
    elLabel.textContent = t.done + "/" + t.total;
    updateIdentityBar();
    if (activeTab === "checklist") renderChecklist(); else renderWeek();
  }

  elResetBtn.addEventListener("click", async function () {
    var today = todayDate();
    var toClear = [];
    state.categories.forEach(function (cat) {
      cat.tasks.forEach(function (t) {
        var key = periodKeyFor(t, today);
        if (t.completions && t.completions[key]) { delete t.completions[key]; toClear.push({ task_id: t.id, period_key: key }); }
      });
    });
    render();
    if (!sb || !toClear.length) return;
    setStatus("busy", "Clearing…");
    try {
      await Promise.all(toClear.map(function (c) {
        return sb.from("checklist_completions").delete().eq("task_id", c.task_id).eq("period_key", c.period_key);
      }));
      setStatus("", "Saved");
    } catch (e) {
      setStatus("error", "Couldn't clear — check your connection");
    }
  });

  elSsoToggle.addEventListener("click", function () {
    filterSso = !filterSso;
    elSsoToggle.setAttribute("aria-pressed", String(filterSso));
    render();
  });

  // ---------- load + live sync from Supabase ----------
  function applyRemoteRows(staffRows, assignRows, compRows) {
    if (staffRows && staffRows.length) state.staff = staffRows.map(function (r) { return r.name; });

    var assignMap = {};
    (assignRows || []).forEach(function (r) { assignMap[r.task_id] = r.assignee; });

    var compMap = {};
    (compRows || []).forEach(function (r) {
      if (!compMap[r.task_id]) compMap[r.task_id] = {};
      compMap[r.task_id][r.period_key] = {
        done: true,
        by: r.done_by || "Unknown",
        at: r.done_at ? new Date(r.done_at).getTime() : Date.now()
      };
    });

    state.categories.forEach(function (cat) {
      cat.tasks.forEach(function (t) {
        t.assignee = Object.prototype.hasOwnProperty.call(assignMap, t.id) ? assignMap[t.id] : null;
        t.completions = compMap[t.id] || {};
      });
    });
  }

  async function loadRemoteState() {
    if (!sb) return false;
    try {
      var results = await Promise.all([
        sb.from("checklist_staff").select("name").order("name"),
        sb.from("checklist_assignments").select("task_id, assignee"),
        sb.from("checklist_completions").select("task_id, period_key, done_by, done_at")
      ]);
      if (results[0].error) throw results[0].error;
      if (results[1].error) throw results[1].error;
      if (results[2].error) throw results[2].error;
      applyRemoteRows(results[0].data, results[1].data, results[2].data);
      return true;
    } catch (e) {
      return false;
    }
  }

  var refreshTimer = null;
  function scheduleRemoteRefresh() {
    if (refreshTimer) clearTimeout(refreshTimer);
    refreshTimer = setTimeout(async function () {
      var ok = await loadRemoteState();
      if (ok) render();
    }, 350);
  }

  function subscribeRealtime() {
    if (!sb || typeof sb.channel !== "function") return;
    sb.channel("checklist-live")
      .on("postgres_changes", { event: "*", schema: "public", table: "checklist_completions" }, scheduleRemoteRefresh)
      .on("postgres_changes", { event: "*", schema: "public", table: "checklist_assignments" }, scheduleRemoteRefresh)
      .on("postgres_changes", { event: "*", schema: "public", table: "checklist_staff" }, scheduleRemoteRefresh)
      .subscribe();
  }

  (async function init() {
    updateIdentityBar();
    render();

    if (!sb) {
      setStatus("error", "Supabase didn't load — working offline, nothing will save");
    } else {
      setStatus("busy", "Loading…");
      var ok = await loadRemoteState();
      render();
      setStatus(ok ? "" : "error", ok ? "Connected" : "Couldn't reach Supabase — working offline");
      if (ok) subscribeRealtime();
    }

    if (!currentUser) {
      renderSigninNames();
      elSigninOverlay.hidden = false;
    }
  })();
})();
</script>
</body>
</html>
