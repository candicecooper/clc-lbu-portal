"""
71_Transition_Timetables.py — CLC-LBU Transition Timetables
===========================================================

Class teachers build a student's transition timetable (CLC ↔ home school)
week by week, or upload an existing Word timetable to pre-fill it.

  • This Week    – who is where each day (initials only) + upcoming last days
  • Timetables   – every saved timetable, step-down chart, history, status
  • Create / Edit – week grid editor, Word upload, Word export in CLC layout

Privacy: Supabase stores INITIALS only. Full name / EDID / DOB are typed
(or read from an uploaded Word file) at export time, kept in this browser
session only, and never saved.

Access: open to all staff (no password).
Archive: every save files an initials-only Word copy in the student's
Document Archive folder via archive_utils.archive_document (supersede=True).
Needs: transition_utils.py at repo root, SQL in sql/transition_timetables_schema.sql
"""

from __future__ import annotations

import html
from datetime import date, timedelta

import pandas as pd
import streamlit as st

try:
    st.set_page_config(page_title="Transition Timetables", page_icon="🔁", layout="wide")
except Exception:
    pass

import transition_utils as tu

# ──────────────────────────────────────────────────────────────────────────
# Styling
# ──────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.tt-grid {border-collapse: collapse; width: 100%; font-size: 0.88rem;}
.tt-grid th {background:#C5E0B3; color:#1f3d17; padding:6px 8px; border:1px solid #cfd8c8; text-align:center;}
.tt-grid td {padding:6px 8px; border:1px solid #dde3d8; text-align:center; vertical-align:middle;}
.tt-grid td.stu {text-align:left; font-weight:600; white-space:nowrap;}
.tt-clc {background:#eef6ea; color:#2d5a22;}
.tt-home {background:#fff59d; color:#4a3b00; font-weight:600;}
.tt-other {background:#eceff1; color:#37474f;}
.tt-none {color:#9aa3a8;}
.tt-label {display:block; font-size:0.75rem; font-weight:700; color:#b3261e;}
.tt-today {outline: 2px solid #2d5a22; outline-offset:-2px;}
</style>
""", unsafe_allow_html=True)

st.title("🔁 Transition Timetables")
st.caption("Build and share a student's CLC ↔ home school transition timetable. "
           "Stored with initials only — full name, EDID and DOB are added at export and never saved.")

client = tu.get_students_client()
if client is None:
    st.error("Supabase (students project) isn't configured — SUPABASE_URL_STUDENTS / key not found.")
    st.stop()

PROGRAMS = ["JP", "PY", "SY"]
PRESETS = [
    f"CLC {tu.CLC_START}–{tu.CLC_END}",
    f"Home school {tu.HOME_AM_START}–{tu.HOME_AM_END}",
    "Home school full day",
    "CLC – custom times",
    "Home school – custom times",
    "Other / not attending",
]
CUSTOM_PRESETS = {3, 4}
OTHER_PRESET = 5


# ──────────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_register() -> list[dict]:
    """Students from the Student Register (initials only)."""
    try:
        import archive_utils as au
        rows = au.fetch_register(None)
        if rows:
            out = [{"id": str(r.get("id") or ""), "initials": str(r.get("initials") or "").strip().upper(),
                    "program": str(r.get("program") or "").upper(), "year": str(r.get("year_level") or ""),
                    "archived": r.get("status") == "archived"} for r in rows if r.get("initials")]
            return sorted(out, key=lambda x: (x["archived"], x["program"], x["initials"]))
    except Exception:
        pass
    for table in ("student_register", "students_register", "student_registry", "register_students"):
        try:
            rows = client.table(table).select("*").execute().data or []
        except Exception:
            continue
        out = []
        for r in rows:
            ini = r.get("initials") or r.get("student_initials") or r.get("student_code") or ""
            if not ini:
                continue
            status = str(r.get("status") or "").lower()
            archived = bool(r.get("archived") or r.get("is_archived")) or status in ("archived", "exited", "inactive")
            out.append({
                "id": str(r.get("id") or ""),
                "initials": str(ini).strip().upper(),
                "program": str(r.get("program") or r.get("programme") or "").upper(),
                "year": str(r.get("year_level") or r.get("year") or ""),
                "archived": archived,
            })
        return sorted(out, key=lambda x: (x["archived"], x["program"], x["initials"]))
    return []


def load_all(include_complete=True):
    try:
        return tu.load_timetables(client, include_complete=include_complete)
    except Exception as e:
        st.error(f"Couldn't load timetables — has the SQL been run? ({e})")
        return []


# ──────────────────────────────────────────────────────────────────────────
# Draft (editor) state
# ──────────────────────────────────────────────────────────────────────────
HEADER_FIELDS = ["student_initials", "program", "home_school", "home_school_short",
                 "home_school_contact", "bsc", "year_level", "notes"]


def blank_draft() -> dict:
    return {"id": None, "version": 0, "register_id": None, "student_initials": "", "program": "PY",
            "home_school": "", "home_school_short": "", "home_school_contact": "", "bsc": "",
            "year_level": "", "recommencement_date": None, "status": "active", "notes": "", "weeks": []}


ss = st.session_state
ss.setdefault("tt_draft", blank_draft())
ss.setdefault("tt_sensitive", {"full_name": "", "preferred_name": "", "edid": "", "dob": ""})
ss.setdefault("tt_nonce", 0)
ss.setdefault("tt_view", "📅 This Week")
ss.setdefault("tt_flash", "")


def k(name: str) -> str:
    """Widget key tied to the current draft load."""
    return f"tt{ss.tt_nonce}_{name}"


def day_to_preset(d: dict) -> int:
    if d["loc"] == tu.LOC_CLC:
        return 0 if (d.get("start"), d.get("end")) == (tu.CLC_START, tu.CLC_END) and not d.get("full_day") else 3
    if d["loc"] == tu.LOC_HOME:
        if d.get("full_day"):
            return 2
        return 1 if (d.get("start"), d.get("end")) == (tu.HOME_AM_START, tu.HOME_AM_END) else 4
    return OTHER_PRESET


def preset_to_day(p: int, iso: str, start: str, end: str, label: str, other: str) -> dict:
    base = {"date": iso, "label": (label or "").strip(), "other": "", "full_day": False}
    if p == 0:
        base.update(loc=tu.LOC_CLC, start=tu.CLC_START, end=tu.CLC_END)
    elif p == 1:
        base.update(loc=tu.LOC_HOME, start=tu.HOME_AM_START, end=tu.HOME_AM_END)
    elif p == 2:
        base.update(loc=tu.LOC_HOME, start="", end="", full_day=True)
    elif p == 3:
        base.update(loc=tu.LOC_CLC, start=start.strip(), end=end.strip())
    elif p == 4:
        base.update(loc=tu.LOC_HOME, start=start.strip(), end=end.strip())
    else:
        base.update(loc=tu.LOC_OTHER, start=start.strip(), end=end.strip(), other=(other or "").strip())
    return base


def sync_from_widgets():
    """Copy current widget values into the draft (used by callbacks)."""
    dr = ss.tt_draft
    for f in HEADER_FIELDS:
        if k(f) in ss:
            dr[f] = ss[k(f)]
    if k("rec") in ss:
        v = ss[k("rec")]
        dr["recommencement_date"] = v.isoformat() if v else None
    for wi, w in enumerate(dr["weeks"]):
        for di, day in enumerate(w["days"]):
            pk = k(f"w{wi}d{di}_p")
            if pk not in ss:
                continue
            w["days"][di] = preset_to_day(
                PRESETS.index(ss[pk]), day["date"],
                ss.get(k(f"w{wi}d{di}_s"), day.get("start", "")),
                ss.get(k(f"w{wi}d{di}_e"), day.get("end", "")),
                ss.get(k(f"w{wi}d{di}_l"), day.get("label", "")),
                ss.get(k(f"w{wi}d{di}_o"), day.get("other", "")))


def load_into_editor(record: dict | None, sensitive: dict | None = None, flash: str = ""):
    dr = blank_draft()
    if record:
        dr.update({key: record.get(key, dr.get(key)) for key in dr})
        dr["weeks"] = tu.sort_weeks(record.get("weeks") or [])
    ss.tt_draft = dr
    ss.tt_sensitive = sensitive or {"full_name": "", "preferred_name": "", "edid": "", "dob": ""}
    ss.tt_nonce += 1
    seed_header()
    ss.tt_goto = "✏️ Create / Edit"
    ss.tt_flash = flash


def seed_header():
    """Put the draft's header values into the (new) widget keys before widgets render."""
    dr = ss.tt_draft
    for f in HEADER_FIELDS:
        ss[k(f)] = dr.get(f) or ("PY" if f == "program" else "")
    if ss[k("program")] not in PROGRAMS:
        ss[k("program")] = "PY"
    ss[k("rec")] = date.fromisoformat(dr["recommencement_date"]) if dr.get("recommencement_date") else None


# Callbacks ---------------------------------------------------------------
def cb_add_week(copy_last: bool):
    sync_from_widgets()
    y, t, w = ss[k("add_y")], int(ss[k("add_t")]), int(ss[k("add_w")])
    if w > tu.weeks_in_term(y, t):
        ss.tt_flash = f"Term {t} {y} only has {tu.weeks_in_term(y, t)} weeks."
        return
    if any((x["year"], x["term"], x["week"]) == (y, t, w) for x in ss.tt_draft["weeks"]):
        ss.tt_flash = f"Term {t} Week {w} is already in this timetable."
        return
    pattern = None
    if copy_last and ss.tt_draft["weeks"]:
        pattern = tu.sort_weeks(ss.tt_draft["weeks"])[-1]["days"]
    ss.tt_draft["weeks"] = tu.sort_weeks(ss.tt_draft["weeks"] + [tu.make_week(y, t, w, pattern)])
    ss.tt_nonce += 1
    seed_header()


def cb_remove_week(wi: int):
    sync_from_widgets()
    ss.tt_draft["weeks"].pop(wi)
    ss.tt_nonce += 1
    seed_header()


def cb_new():
    load_into_editor(None)


# ──────────────────────────────────────────────────────────────────────────
# Shared renderers
# ──────────────────────────────────────────────────────────────────────────
def cell_html(day: dict | None, home_short: str, is_today=False) -> str:
    if not day:
        return f'<td class="tt-none{" tt-today" if is_today else ""}">—</td>'
    cls = {"CLC": "tt-clc", "HOME": "tt-home"}.get(day["loc"], "tt-other")
    place = {"CLC": "CLC", "HOME": home_short or "Home school"}.get(day["loc"], day.get("other") or "Other")
    tr = tu.fmt_time_range(day)
    lab = f'<span class="tt-label">{html.escape(day["label"].upper())}</span>' if day.get("label") else ""
    return (f'<td class="{cls}{" tt-today" if is_today else ""}">{html.escape(place)}'
            f'<br><small>{html.escape(tr)}</small>{lab}</td>')


def stepdown_chart(weeks: list[dict], height=220):
    import altair as alt
    rows = []
    order = ["At CLC", "Home school – part day", "Home school – full day", "Other"]
    for i, w in enumerate(tu.sort_weeks(weeks)):
        lab = f"T{w['term']} W{w['week']}" + (f" '{str(w['year'])[2:]}" if w["year"] != date.today().year else "")
        for cat, n in tu.week_summary(w).items():
            if n:
                rows.append({"Week": lab, "i": i, "Where": cat, "Days": n, "o": order.index(cat)})
    if not rows:
        return
    df = pd.DataFrame(rows)
    chart = alt.Chart(df).mark_bar(size=26).encode(
        x=alt.X("Week:N", sort=alt.SortField("i"), title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("sum(Days):Q", title="Days", scale=alt.Scale(domain=[0, 5]), axis=alt.Axis(tickCount=5)),
        color=alt.Color("Where:N", sort=order, title=None,
                        scale=alt.Scale(domain=order, range=["#4a8f3c", "#f5d76e", "#d4a106", "#b0bec5"]),
                        legend=alt.Legend(orient="bottom")),
        order=alt.Order("o:Q"),
        tooltip=["Week", "Where", "Days"],
    ).properties(height=height)
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:
        st.altair_chart(chart)


def stepdown_sentence(weeks: list[dict]) -> str:
    ws = tu.sort_weeks(weeks)
    if len(ws) < 2:
        return ""
    a, b = tu.week_summary(ws[0])["At CLC"], tu.week_summary(ws[-1])["At CLC"]
    fa = f"T{ws[0]['term']} W{ws[0]['week']}"
    fb = f"T{ws[-1]['term']} W{ws[-1]['week']}"
    return f"CLC days per week: **{a}** ({fa}) → **{b}** ({fb})"


# ──────────────────────────────────────────────────────────────────────────
# Navigation
# ──────────────────────────────────────────────────────────────────────────
VIEWS = ["📅 This Week", "🗂️ Timetables", "✏️ Create / Edit"]
if "tt_goto" in ss:
    ss.tt_view = ss.pop("tt_goto")
if k("program") not in ss:
    seed_header()
st.radio("View", VIEWS, horizontal=True, key="tt_view", label_visibility="collapsed")
if ss.tt_flash:
    st.info(ss.tt_flash)
    ss.tt_flash = ""
view = ss.tt_view


# ══════════════════════════════════════════════════════════════════════════
# 📅 THIS WEEK
# ══════════════════════════════════════════════════════════════════════════
if view == VIEWS[0]:
    today = date.today()
    default = today if today.weekday() < 5 else today + timedelta(days=7 - today.weekday())
    pick = st.date_input("Week of", value=default, format="DD/MM/YYYY", key="tt_week_pick")
    mon = pick - timedelta(days=pick.weekday())
    tw = tu.term_week_for(mon)
    st.subheader(f"Week of {mon.strftime('%d/%m/%Y')}" + (f" — Term {tw[1]} Week {tw[2]}" if tw else " — school holidays"))

    tts = [t for t in load_all(include_complete=False)]
    rows = []
    for tt in tts:
        wk = tt.get("weeks") or []
        if any(tu.day_for(wk, mon + timedelta(days=i)) for i in range(5)):
            rows.append(tt)
    rows.sort(key=lambda t: (t.get("program", ""), t.get("student_initials", "")))

    if not rows:
        st.info("No students have transition days scheduled this week.")
    else:
        head = "".join(f"<th>{d}<br><small>{(mon + timedelta(days=i)).strftime('%d/%m')}</small></th>"
                       for i, d in enumerate(tu.DAY_NAMES))
        body = ""
        for tt in rows:
            short = tt.get("home_school_short") or tu.school_short_name(tt.get("home_school", ""))
            cells = "".join(cell_html(tu.day_for(tt["weeks"], mon + timedelta(days=i)), short,
                                      is_today=(mon + timedelta(days=i) == today)) for i in range(5))
            body += (f'<tr><td class="stu">{html.escape(tt.get("student_initials", ""))} · '
                     f'{html.escape(tt.get("program", ""))}<br><small>{html.escape(short)}</small></td>{cells}</tr>')
        st.markdown(f'<table class="tt-grid"><tr><th>Student</th>{head}</tr>{body}</table>',
                    unsafe_allow_html=True)
        st.caption("Yellow = at home school. Green = at CLC.")

    # Daily Bulletin preview
    with st.expander("📰 Daily Bulletin lines for a day", expanded=False):
        bday = st.date_input("Day", value=default, format="DD/MM/YYYY", key="tt_bday")
        lines = []
        for e in tu.where_is_everyone(tts, bday):
            d = e["day"]
            if d["loc"] == tu.LOC_CLC and not d.get("label"):
                continue
            lines.append(f"{e['initials']} · {e['program']} — {tu.short_day_text(d, 'Home school')}")
        st.write("\n".join(f"- {l}" for l in lines) if lines else "_Nothing to flag — everyone on a transition is at CLC._")
        st.caption("Initials only. The Bulletin can pull these with `transition_utils.bulletin_lines_for()`.")

    # Coming up
    st.markdown("#### ⏰ Coming up (next 14 days)")
    soon = []
    for tt in tts:
        lc = tu.last_clc_day(tt.get("weeks") or [])
        rec = date.fromisoformat(tt["recommencement_date"]) if tt.get("recommencement_date") else None
        who = f"**{tt.get('student_initials')} · {tt.get('program')}**"
        if lc and today <= lc <= today + timedelta(days=14):
            soon.append((lc, f"{who} — last day at CLC **{lc.strftime('%a %d/%m')}**"))
        if rec and today <= rec <= today + timedelta(days=14):
            soon.append((rec, f"{who} — back at home school full time **{rec.strftime('%a %d/%m')}** "
                              f"→ Admin: start exit process (archive folder, comms log export)."))
    if soon:
        for _, txt in sorted(soon):
            st.markdown(f"- {txt}")
    else:
        st.caption("No last days or recommencements in the next fortnight.")


# ══════════════════════════════════════════════════════════════════════════
# 🗂️ TIMETABLES
# ══════════════════════════════════════════════════════════════════════════
elif view == VIEWS[1]:
    c1, c2, c3 = st.columns([2, 1, 1])
    show_done = c2.toggle("Show completed", value=False, key="tt_show_done")
    c3.button("➕ New timetable", on_click=cb_new)
    search = c1.text_input("Search initials or school", key="tt_search", placeholder="e.g. AW or Bellevue")

    tts = load_all(include_complete=True)
    if not show_done:
        tts = [t for t in tts if t.get("status") == "active"]
    if search:
        s = search.lower()
        tts = [t for t in tts if s in (t.get("student_initials", "") + " " + t.get("home_school", "")).lower()]

    if not tts:
        st.info("No timetables yet. Use **New timetable**, or upload an existing Word timetable in Create / Edit.")

    for tt in tts:
        wk = tt.get("weeks") or []
        lc = tu.last_clc_day(wk)
        badge = "🟢" if tt.get("status") == "active" else "✅"
        title = (f"{badge} {tt.get('student_initials')} · {tt.get('program')} — {tt.get('home_school') or 'home school?'}"
                 + (f"  ·  last CLC day {lc.strftime('%d/%m')}" if lc else ""))
        with st.expander(title):
            a, b = st.columns([1, 1])
            rec = tt.get("recommencement_date")
            a.markdown(
                f"**Home school:** {tt.get('home_school') or '—'}  \n"
                f"**Contact:** {tt.get('home_school_contact') or '—'}  \n"
                f"**BSC:** {tt.get('bsc') or '—'}  \n"
                f"**Year level:** {tt.get('year_level') or '—'}  \n"
                f"**Recommencement:** {tu.recommencement_text(date.fromisoformat(rec)) if rec else '—'}  \n"
                f"**Version {tt.get('version', 1)}** · updated by {tt.get('updated_by') or tt.get('created_by') or '—'}")
            if tt.get("notes"):
                a.caption(tt["notes"])
            with b:
                stepdown_chart(wk, height=200)
                sent = stepdown_sentence(wk)
                if sent:
                    st.markdown(sent)

            bc = st.columns(4)
            if bc[0].button("✏️ Edit / export", key=f"ed_{tt['id']}"):
                load_into_editor(tt, flash=f"Loaded {tt.get('student_initials')}. Add full name/EDID/DOB in the export box if you need the Word file.")
                st.rerun()
            if tt.get("status") == "active":
                if bc[1].button("✅ Mark complete", key=f"cp_{tt['id']}"):
                    tu.set_status(client, tt["id"], "complete"); st.rerun()
            else:
                if bc[1].button("↩️ Reactivate", key=f"ra_{tt['id']}"):
                    tu.set_status(client, tt["id"], "active"); st.rerun()
            show_hist = bc[2].toggle("History", key=f"hi_{tt['id']}")
            with bc[3].popover("🗑️ Delete"):
                st.warning("Deletes this timetable and all its saved versions. This can't be undone. "
                           "Use **Mark complete** instead if the transition has simply finished.")
                if st.checkbox("I understand", key=f"dc_{tt['id']}") and st.button("Delete permanently", key=f"dl_{tt['id']}"):
                    tu.delete_timetable(client, tt["id"]); st.rerun()

            if show_hist:
                try:
                    hist = tu.load_history(client, tt["id"])
                except Exception:
                    hist = []
                if not hist:
                    st.caption("No earlier versions saved.")
                for h in hist:
                    snap = h.get("snapshot") or {}
                    hc = st.columns([3, 1])
                    hc[0].markdown(f"**v{h.get('version')}** — {str(h.get('saved_at', ''))[:16].replace('T', ' ')} "
                                   f"by {h.get('saved_by') or '—'}" + (f" — _{h['change_note']}_" if h.get("change_note") else "")
                                   + f"  ·  {stepdown_sentence(snap.get('weeks') or []) or ''}")
                    if hc[1].button("Open this version", key=f"hv_{h.get('id')}"):
                        rec_ = dict(tt); rec_.update(snap); rec_["id"] = tt["id"]; rec_["version"] = tt.get("version")
                        load_into_editor(rec_, flash=f"Opened v{h.get('version')} — saving will make it the current version.")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# ✏️ CREATE / EDIT
# ══════════════════════════════════════════════════════════════════════════
else:
    dr = ss.tt_draft
    top = st.columns([3, 1])
    top[0].subheader(("Editing " + dr["student_initials"] + f" (v{dr['version']})") if dr.get("id") else "New transition timetable")
    top[1].button("➕ Start a new one", on_click=cb_new)

    # ── Upload an existing Word timetable
    with st.expander("📥 Start from an existing Word timetable", expanded=not dr.get("id") and not dr["weeks"]):
        st.caption("Upload a timetable in the usual CLC layout. The grid fills in for you to check. "
                   "The Word file itself isn't stored, and the full name / EDID / DOB in it are only kept "
                   "in this session for the export.")
        up = st.file_uploader("Word timetable (.docx)", type=["docx"], key=k("upload"))
        if up is not None and st.button("Read timetable", type="primary", key=k("read")):
            try:
                parsed = tu.parse_timetable_docx(up.getvalue())
            except Exception as e:
                st.error(f"Couldn't read that file: {e}")
            else:
                sens = parsed["sensitive"]
                ini = tu.initials_from_name(sens.get("full_name", ""))
                rec = dict(parsed["header"])
                rec["student_initials"] = ini
                rec["weeks"] = parsed["weeks"]
                match = next((r for r in load_register() if r["initials"] == ini and not r["archived"]), None)
                if match:
                    rec["register_id"] = match["id"] or None
                    rec["program"] = match["program"] or "PY"
                    rec["year_level"] = rec.get("year_level") or match["year"]
                msg = f"Read {len(parsed['weeks'])} week(s) for {ini or 'the student'}. Check the grid, then save."
                if parsed["warnings"]:
                    msg += "  ⚠️ " + "  ⚠️ ".join(parsed["warnings"])
                load_into_editor(rec, sensitive=sens, flash=msg)
                st.rerun()

    # ── Student + header
    st.markdown("#### Student & home school")
    reg = [r for r in load_register() if not r["archived"]]
    h1, h2, h3 = st.columns([2, 1, 1])
    if reg:
        labels = ["— type initials —"] + [f"{r['initials']} · {r['program']}" + (f" · Yr {r['year']}" if r["year"] else "") for r in reg]
        cur = next((i + 1 for i, r in enumerate(reg) if r["initials"] == dr["student_initials"]), 0)
        sel = h1.selectbox("Student (from Student Register)", labels, index=cur, key=k("reg"))
        if sel != labels[0]:
            r = reg[labels.index(sel) - 1]
            if ss.get(k("student_initials")) != r["initials"]:
                dr["register_id"] = r["id"] or None
                if r["program"] in PROGRAMS:
                    ss[k("program")] = r["program"]
                if r["year"] and not ss.get(k("year_level")):
                    ss[k("year_level")] = r["year"]
            ss[k("student_initials")] = r["initials"]
        picked = sel != labels[0]
    else:
        picked = False
        h1.caption("Student Register not found — type initials.")
    h2.text_input("Initials", key=k("student_initials"), max_chars=4, disabled=picked)
    h3.selectbox("Program", PROGRAMS, key=k("program"))

    h4, h5, h6 = st.columns([2, 1, 1])
    h4.text_input("Home school", key=k("home_school"),
                  placeholder="e.g. Bellevue Heights Primary School")
    h5.text_input("Short name used in timetable",
                  key=k("home_school_short"), placeholder="e.g. Bellevue",
                  help="Used in the Word export: 'Abi will attend Bellevue.'")
    h6.text_input("Year level", key=k("year_level"))

    h7, h8, h9 = st.columns([2, 1, 1])
    h7.text_input("Home school contact person", key=k("home_school_contact"))
    h8.text_input("BSC", key=k("bsc"))
    h9.date_input("Recommencement at home school", format="DD/MM/YYYY", key=k("rec"))
    st.text_area("Notes (optional — no full names)", key=k("notes"), height=68)

    # write header back
    for f in HEADER_FIELDS:
        if k(f) in ss:
            dr[f] = ss[k(f)]
    dr["student_initials"] = (dr["student_initials"] or "").strip().upper()
    dr["recommencement_date"] = ss[k("rec")].isoformat() if ss.get(k("rec")) else None
    if not dr["home_school_short"] and dr["home_school"]:
        dr["home_school_short"] = tu.school_short_name(dr["home_school"])

    # ── Weeks
    st.markdown("#### Weeks")
    if not dr["weeks"]:
        st.caption("No weeks yet — add the first week below.")

    for wi, w in enumerate(dr["weeks"]):
        mon = tu.week_monday(w["year"], w["term"], w["week"])
        with st.container(border=True):
            hc = st.columns([5, 1])
            hc[0].markdown(f"**Term {w['term']} · Week {w['week']}** "
                           f"<span style='color:#666'>({mon.strftime('%d/%m')} – {(mon + timedelta(days=4)).strftime('%d/%m/%Y')})</span>",
                           unsafe_allow_html=True)
            hc[1].button("Remove week", key=k(f"rm{wi}"), on_click=cb_remove_week, args=(wi,))
            cols = st.columns(5)
            for di in range(5):
                day = w["days"][di]
                with cols[di]:
                    st.markdown(f"**{tu.DAY_NAMES[di]}** {(mon + timedelta(days=di)).strftime('%d/%m')}")
                    p = st.selectbox("Where", PRESETS, index=day_to_preset(day), key=k(f"w{wi}d{di}_p"),
                                     label_visibility="collapsed")
                    pi = PRESETS.index(p)
                    s_, e_, o_ = day.get("start", ""), day.get("end", ""), day.get("other", "")
                    if pi == OTHER_PRESET:
                        o_ = st.text_input("Where / why", value=o_, key=k(f"w{wi}d{di}_o"),
                                           placeholder="e.g. Not attending, excursion")
                    if pi in CUSTOM_PRESETS or pi == OTHER_PRESET:
                        tc = st.columns(2)
                        s_ = tc[0].text_input("From", value=s_, key=k(f"w{wi}d{di}_s"), placeholder="9:00")
                        e_ = tc[1].text_input("To", value=e_, key=k(f"w{wi}d{di}_e"), placeholder="12:00")
                    l_ = st.text_input("Flag", value=day.get("label", ""), key=k(f"w{wi}d{di}_l"),
                                       placeholder="Flag (optional) e.g. LAST DAY", label_visibility="collapsed")
                    w["days"][di] = preset_to_day(pi, day["date"], s_, e_, l_, o_)

    # ── Add week controls
    with st.container(border=True):
        if dr["weeks"]:
            last = tu.sort_weeks(dr["weeks"])[-1]
            ny, nt, nw = tu.next_term_week(last["year"], last["term"], last["week"])
        else:
            ny, nt, nw = tu.current_or_next_term_week()
        years = sorted(tu.TERM_DATES)
        ac = st.columns([1, 1, 1, 2, 2])
        ac[0].selectbox("Year", years, index=years.index(ny), key=k("add_y"))
        ac[1].selectbox("Term", [1, 2, 3, 4], index=nt - 1, key=k("add_t"))
        ac[2].number_input("Week", 1, 11, value=nw, key=k("add_w"))
        ac[3].button("➕ Add week (all CLC)", on_click=cb_add_week, args=(False,))
        ac[4].button("📋 Add week — copy last week's pattern", on_click=cb_add_week, args=(True,), disabled=not dr["weeks"])

    # ── Preview
    if dr["weeks"]:
        st.markdown("#### Step-down")
        pc = st.columns([2, 1])
        with pc[0]:
            stepdown_chart(dr["weeks"])
        sent = stepdown_sentence(dr["weeks"])
        pc[1].markdown(sent or "Add more weeks to see the step-down.")
        lc = tu.last_clc_day(dr["weeks"])
        if lc:
            pc[1].markdown(f"Last scheduled CLC day: **{lc.strftime('%a %d/%m/%Y')}**")

    # ── Save
    st.markdown("#### Save")
    sc = st.columns([2, 3, 1])
    saved_by = sc[0].text_input("Your name", key="tt_saved_by")
    note = sc[1].text_input("What changed? (optional)", key=k("note"),
                            placeholder="e.g. Added Week 3, Thursday now full day at home school")
    sc[2].markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
    if sc[2].button("💾 Save", type="primary", key=k("save")):
        problems = []
        if not dr["student_initials"]:
            problems.append("student initials")
        if not dr["weeks"]:
            problems.append("at least one week")
        if not saved_by.strip():
            problems.append("your name")
        if problems:
            st.error("Please add: " + ", ".join(problems) + ".")
        else:
            if not dr.get("id"):
                dup = [t for t in load_all(include_complete=False) if t.get("student_initials") == dr["student_initials"]]
                if dup and not ss.get(k("dup_ok")):
                    ss[k("dup_ok")] = True
                    st.warning(f"{dr['student_initials']} already has an active timetable. "
                               "Edit that one from Timetables, or press Save again to create a second.")
                    st.stop()
            try:
                row = tu.save_timetable(client, dr, saved_by.strip(), note)
            except Exception as e:
                st.error(f"Save failed: {e}")
            else:
                msg = f"Saved {row.get('student_initials')} — version {row.get('version')}."
                with st.spinner("Filing in Document Archive…"):
                    arc = tu.archive_timetable(row, saved_by.strip(), note)
                if arc:
                    msg += f" 🗄️ Filed in {row.get('student_initials')}'s Document Archive folder (replaces the previous copy)."
                else:
                    msg += (" ⚠️ Couldn't file it in the Document Archive — the timetable is saved here, "
                            "but check the archive and let Candice know.")
                load_into_editor(row, sensitive=ss.tt_sensitive, flash=msg)
                st.rerun()

    # ── Word export
    if dr["weeks"]:
        with st.expander("📄 Word export (CLC layout)", expanded=bool(ss.tt_sensitive.get("full_name"))):
            st.caption("🔒 These details go into the Word file only. They are not saved anywhere and clear "
                       "when you close the page.")
            sens = ss.tt_sensitive
            ec = st.columns(4)
            sens["full_name"] = ec[0].text_input("Student's full name", value=sens.get("full_name", ""), key=k("x_full"))
            sens["preferred_name"] = ec[1].text_input("Name used in timetable", value=sens.get("preferred_name", ""),
                                                      key=k("x_pref"), placeholder="e.g. Abi")
            sens["edid"] = ec[2].text_input("EDID", value=sens.get("edid", ""), key=k("x_edid"))
            sens["dob"] = ec[3].text_input("DOB", value=sens.get("dob", ""), key=k("x_dob"), placeholder="dd/mm/yyyy")
            try:
                data = tu.build_timetable_docx(dr, dr["weeks"], sens)
                st.download_button("⬇️ Download Word timetable", data=data,
                                   file_name=tu.export_filename(sens, dr["student_initials"]),
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   type="primary", key=k("dl"))
            except Exception as e:
                st.error(f"Couldn't build the Word file: {e}")
