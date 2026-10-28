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
Workflow: new timetables are DRAFTS (save as often as needed, share with
colleagues). PUBLISH makes it live (This Week / Bulletin), emails the program
teacher(s) + Admin + Leadership, and files an initials-only Word copy in the
student's Document Archive folder. Edits after publishing stay unpublished
until published again ("UPDATED" email).
Email settings view is behind the confidential password.
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
            "year_level": "", "recommencement_date": None, "status": "draft", "notes": "", "weeks": [],
            "published_version": None}


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


def parsed_to_record(parsed: dict) -> dict:
    """Turn a parsed Word timetable into an editor record (initials only)."""
    sens = parsed["sensitive"]
    full = sens.get("full_name", "")
    ini = tu.initials_from_name(full)
    reg = [r for r in load_register() if not r["archived"]]
    parts = [p for p in full.replace(".", " ").split() if p]
    two = "".join(p[0].upper() for p in parts[:2])
    match = next((r for r in reg if r["initials"] in (ini, two)), None)
    rec = dict(parsed["header"])
    rec["student_initials"] = match["initials"] if match else ini
    rec["weeks"] = parsed["weeks"]
    rec["program"] = "PY"
    if match:
        rec["register_id"] = match["id"] or None
        rec["program"] = match["program"] if match["program"] in PROGRAMS else "PY"
        rec["year_level"] = rec.get("year_level") or match["year"]
    rec["_on_register"] = bool(match)
    return rec


def weeks_preview_html(weeks: list[dict], short: str) -> str:
    head = "".join(f"<th>{d}</th>" for d in tu.DAY_NAMES)
    body = ""
    for w in tu.sort_weeks(weeks):
        mon = tu.week_monday(w["year"], w["term"], w["week"])
        cells = "".join(cell_html(w["days"][i], short) for i in range(5))
        body += (f'<tr><td class="stu">T{w["term"]} W{w["week"]}<br>'
                 f'<small>{mon.strftime("%d/%m")}–{(mon + timedelta(days=4)).strftime("%d/%m")}</small></td>{cells}</tr>')
    return f'<table class="tt-grid"><tr><th>Week</th>{head}</tr>{body}</table>'


def do_publish(row: dict, by: str, note: str) -> str:
    """Publish + build the message shown after rerun."""
    with st.spinner("Publishing — emailing staff and filing in the Document Archive…"):
        res = tu.publish_timetable(client, row, by, note)
    ini = row.get("student_initials")
    msg = f"🚀 Published {ini} (v{row.get('version')}). It now shows in This Week and the Bulletin lines."
    msg += (f"  📧 {res['email_msg']}" if res["email_ok"]
            else f"  ⚠️ {res['email_msg']} Use **Resend email** in Timetables once fixed.")
    msg += (f"  🗄️ Filed in {ini}'s Document Archive folder." if res["archive_ok"]
            else "  ⚠️ Couldn't file it in the Document Archive — please check the archive.")
    return msg


def confidential_gate() -> bool:
    """Admin & Leadership only — uses the portal's shared confidential_auth.py."""
    try:
        import confidential_auth as ca
        for fn_name in ("require_confidential_auth", "require_confidential", "confidential_gate",
                        "check_confidential_password", "check_password"):
            fn = getattr(ca, fn_name, None)
            if callable(fn):
                return fn() is not False
    except Exception:
        pass
    if ss.get("tt_conf_ok"):
        return True
    pw_secret = tu._secret("CONFIDENTIAL_PASSWORD", "confidential_password", "ADMIN_PASSWORD")
    pw = st.text_input("Admin / Leadership password", type="password", key="tt_conf_pw")
    if pw and pw_secret and pw == pw_secret:
        ss.tt_conf_ok = True
        st.rerun()
    elif pw:
        st.error("Incorrect password.")
    return False


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
VIEWS = ["📅 This Week", "🗂️ Timetables", "📥 Upload Word", "✏️ Create / Edit", "⚙️ Email settings"]
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

    all_open = load_all(include_complete=False)
    tts = [v for v in (tu.live_view(t) for t in all_open) if v]   # published versions only
    n_drafts = sum(1 for t in all_open if t.get("status") == tu.DRAFT)
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
        st.caption("Yellow = at home school. Green = at CLC. Published timetables only.")
    if n_drafts:
        st.caption(f"📝 {n_drafts} draft timetable(s) not shown — they appear here once published.")

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
        tts = [t for t in tts if t.get("status") != tu.COMPLETE]
    order = {tu.DRAFT: 0, tu.PUBLISHED: 1, "active": 1, tu.COMPLETE: 2}
    tts.sort(key=lambda t: (order.get(t.get("status"), 1), t.get("program", ""), t.get("student_initials", "")))
    if search:
        s = search.lower()
        tts = [t for t in tts if s in (t.get("student_initials", "") + " " + t.get("home_school", "")).lower()]

    if not tts:
        st.info("No timetables yet. Use **New timetable**, or upload an existing Word timetable in Create / Edit.")

    for tt in tts:
        wk = tt.get("weeks") or []
        lc = tu.last_clc_day(wk)
        title = (f"{tu.status_label(tt)} · {tt.get('student_initials')} · {tt.get('program')} — {tt.get('home_school') or 'home school?'}"
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
                f"**Version {tt.get('version', 1)}** · updated by {tt.get('updated_by') or tt.get('created_by') or '—'}"
                + (f"  \n**Published:** v{tt.get('published_version')} by {tt.get('published_by') or '—'} "
                   f"on {str(tt.get('published_at') or '')[:10]}"
                   + ("" if tt.get("publish_email_ok", True) else " · ⚠️ email not sent")
                   if tt.get("published_version") else ""))
            if tt.get("status") == tu.DRAFT:
                a.info("📝 Draft — not yet sent to anyone. Check it with colleagues, then **Publish**.")
            elif tu.has_unpublished_changes(tt):
                a.warning(f"🟠 Saved changes (v{tt.get('version')}) aren't live yet — v{tt.get('published_version')} "
                          "is what staff see. **Publish** to send the update.")
            if tt.get("notes"):
                a.caption(tt["notes"])
            with b:
                stepdown_chart(wk, height=200)
                sent = stepdown_sentence(wk)
                if sent:
                    st.markdown(sent)

            bc = st.columns(5)
            if bc[0].button("✏️ Edit / export", key=f"ed_{tt['id']}"):
                load_into_editor(tt, flash=f"Loaded {tt.get('student_initials')}. Add full name/EDID/DOB in the export box if you need the Word file.")
                st.rerun()
            stt = tt.get("status")
            if stt == tu.DRAFT or tu.has_unpublished_changes(tt) or stt == "active":
                with bc[1].popover("🚀 Publish" if stt == tu.DRAFT else "🚀 Publish changes"):
                    st.caption("Emails the " + (tt.get("program") or "program") + " teacher(s), Admin and Leadership, "
                               "and files a copy in the Document Archive.")
                    if f"pbn_{tt['id']}" not in ss:
                        ss[f"pbn_{tt['id']}"] = ss.get("tt_name", "")
                    pb = st.text_input("Your name", key=f"pbn_{tt['id']}")
                    pn = st.text_input("What changed? (optional)", key=f"pbc_{tt['id']}")
                    if st.button("Publish now", type="primary", key=f"pb_{tt['id']}"):
                        if not pb.strip():
                            st.error("Add your name.")
                        else:
                            ss.tt_name = pb.strip()
                            ss.tt_flash = do_publish(tt, pb.strip(), pn.strip())
                            st.rerun()
            elif stt == tu.PUBLISHED:
                if bc[1].button("✅ Mark complete", key=f"cp_{tt['id']}"):
                    tu.set_status(client, tt["id"], tu.COMPLETE); st.rerun()
            elif stt == tu.COMPLETE:
                if bc[1].button("↩️ Reactivate", key=f"ra_{tt['id']}"):
                    tu.set_status(client, tt["id"], tu.PUBLISHED if tt.get("published_version") else tu.DRAFT)
                    st.rerun()
            if tu.is_live(tt) and tt.get("publish_email_ok") is False:
                if bc[2].button("📧 Resend email", key=f"re_{tt['id']}"):
                    live = tu.live_view(tt)
                    ok, msg = tu.send_email(tu.recipients_for(client, live.get("program") or ""),
                                            f"Transition timetable — {live.get('student_initials')} ({live.get('program')})",
                                            tu.timetable_email_html(live, bool(tt.get("published_version")),
                                                                    tt.get("published_by") or "—", "",
                                                                    tu.portal_page_url()))
                    if ok:
                        client.table(tu.TABLE_TIMETABLES).update({"publish_email_ok": True}).eq("id", tt["id"]).execute()
                    ss.tt_flash = ("📧 " if ok else "⚠️ ") + msg
                    st.rerun()
            show_hist = bc[3].toggle("History", key=f"hi_{tt['id']}")
            with bc[4].popover("🗑️ Delete"):
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
# 📥 UPLOAD WORD TIMETABLES
# ══════════════════════════════════════════════════════════════════════════
elif view == VIEWS[2]:
    st.subheader("📥 Convert Word timetables")
    st.caption("Upload one or more transition timetables written in Word (the usual CLC layout). Each one is "
               "converted into a portal timetable you can check, then save as a **Draft**. Once it's published, "
               "it connects to This Week, the Bulletin lines, the Document Archive and the email alerts.")
    st.caption("🔒 The Word files aren't stored. Only initials are saved. The full name, EDID and DOB in the file are "
               "kept for this session only, so you can re-export the Word version from the editor.")
    ss.setdefault("tt_up_nonce", 0)
    ss.setdefault("tt_up_done", {})
    files = st.file_uploader("Word timetables (.docx)", type=["docx"], accept_multiple_files=True,
                             key=f"tt_up_files_{ss.tt_up_nonce}")
    if not files:
        st.info("Drag Word timetables here, or click **Browse files**. You can select several at once.")
    else:
        uc = st.columns([2, 3])
        up_by = uc[0].text_input("Your name (for saving)", key="tt_up_by", value=ss.get("tt_name", ""))
        if up_by.strip():
            ss.tt_name = up_by.strip()
        open_initials = {t.get("student_initials") for t in load_all(include_complete=False)}

        converted = []
        for fi, f in enumerate(files):
            fkey = f"{f.name}:{f.size}"
            with st.container(border=True):
                st.markdown(f"**📄 {html.escape(f.name)}**")
                if fkey in ss.tt_up_done:
                    st.success(ss.tt_up_done[fkey])
                    continue
                try:
                    parsed = tu.parse_timetable_docx(f.getvalue())
                except Exception as e:
                    st.error(f"Couldn't read this file: {e}. Is it a Word (.docx) timetable?")
                    continue
                if not parsed["weeks"]:
                    st.error("No weeks found. This doesn't look like the CLC transition timetable layout — "
                             "use **Create / Edit** to enter it by hand.")
                    continue
                rec = parsed_to_record(parsed)
                cc = st.columns([1, 1, 2, 2])
                rec["student_initials"] = cc[0].text_input("Initials", value=rec["student_initials"],
                                                           key=f"up_ini_{fi}_{fkey}", max_chars=4).strip().upper()
                rec["program"] = cc[1].selectbox("Program", PROGRAMS, index=PROGRAMS.index(rec["program"]),
                                                 key=f"up_prog_{fi}_{fkey}")
                cc[2].markdown(f"**Home school:** {html.escape(rec.get('home_school') or '—')}  \n"
                               f"**Contact:** {html.escape(rec.get('home_school_contact') or '—')} · "
                               f"**BSC:** {html.escape(rec.get('bsc') or '—')}")
                rd = rec.get("recommencement_date")
                cc[3].markdown(f"**Recommencement:** {tu.recommencement_text(date.fromisoformat(rd)) if rd else '—'}  \n"
                               + (stepdown_sentence(rec["weeks"]) or f"{len(rec['weeks'])} week(s)"))
                if not rec.pop("_on_register"):
                    st.caption(f"ℹ️ {rec['student_initials'] or 'This student'} isn't on the Student Register — "
                               "check the initials and program.")
                if rec["student_initials"] in open_initials:
                    st.warning(f"{rec['student_initials']} already has an open timetable in the portal. "
                               "Saving this creates a second one — open the existing one from Timetables if "
                               "this is an update.")
                for w_ in parsed["warnings"]:
                    st.warning(w_)
                short = rec.get("home_school_short") or tu.school_short_name(rec.get("home_school", ""))
                st.markdown(weeks_preview_html(rec["weeks"], short), unsafe_allow_html=True)

                bc_ = st.columns([1, 1, 3])
                if bc_[0].button("✏️ Check in editor", key=f"up_ed_{fi}_{fkey}"):
                    ss.tt_up_done[fkey] = f"Opened {rec['student_initials']} in the editor (not saved yet)."
                    load_into_editor(rec, sensitive=parsed["sensitive"],
                                     flash=f"Converted {f.name}. Check the grid, then **Save draft**.")
                    st.rerun()
                if bc_[1].button("💾 Save as draft", key=f"up_sv_{fi}_{fkey}"):
                    if not up_by.strip():
                        st.error("Add your name above first.")
                    elif not rec["student_initials"]:
                        st.error("Add the student's initials.")
                    else:
                        row = tu.save_timetable(client, rec, up_by.strip(), f"Converted from Word: {f.name}")
                        ss.tt_up_done[fkey] = (f"💾 Saved as draft {row.get('student_initials')} · {row.get('program')}. "
                                               "Find it in **Timetables** to check and publish.")
                        st.rerun()
                converted.append((fkey, rec))

        if len(converted) > 1:
            st.divider()
            if st.button(f"💾 Save all {len(converted)} as drafts", type="primary"):
                if not up_by.strip():
                    st.error("Add your name above first.")
                elif any(not r["student_initials"] for _, r in converted):
                    st.error("Every timetable needs initials before saving.")
                else:
                    for fkey, rec in converted:
                        row = tu.save_timetable(client, rec, up_by.strip(), "Converted from Word")
                        ss.tt_up_done[fkey] = (f"💾 Saved as draft {row.get('student_initials')} · {row.get('program')}. "
                                               "Find it in **Timetables** to check and publish.")
                    st.rerun()
        if ss.tt_up_done and st.button("🧹 Clear and upload more"):
            ss.tt_up_done = {}
            ss.tt_up_nonce += 1
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# ✏️ CREATE / EDIT
# ══════════════════════════════════════════════════════════════════════════
elif view == VIEWS[3]:
    dr = ss.tt_draft
    top = st.columns([3, 1])
    top[0].subheader(("Editing " + dr["student_initials"] + f" (v{dr['version']})") if dr.get("id") else "New transition timetable")
    top[1].button("➕ Start a new one", on_click=cb_new)
    if not dr.get("id"):
        st.caption("📝 New timetables are saved as a **Draft**. Nothing is sent until you **Publish**.")
    elif dr.get("status") == tu.DRAFT:
        st.info("📝 **Draft** — only visible here. Save as often as you like; Publish when it's checked.")
    elif dr.get("status") == tu.COMPLETE:
        st.info("✅ This transition is marked complete.")
    elif dr.get("published_version") and int(dr.get("version") or 0) > int(dr["published_version"]):
        st.warning(f"🟠 Published v{dr['published_version']} is live. Your saved changes (v{dr['version']}) "
                   "aren't live until you publish them.")
    else:
        st.success(f"🟢 Published (v{dr.get('published_version') or dr.get('version')}). "
                   "Edits you save stay as unpublished changes until you publish again.")

    # ── Upload an existing Word timetable
    with st.expander("📥 Start from an existing Word timetable", expanded=not dr.get("id") and not dr["weeks"]):
        st.caption("Tip: the **📥 Upload Word** section (top of the page) converts several at once. "
                   "Upload a timetable in the usual CLC layout. The grid fills in for you to check. "
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
                rec = parsed_to_record(parsed)
                ini = rec["student_initials"]
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

    # ── Save / publish
    st.markdown("#### Save & publish")
    sc = st.columns([2, 3])
    if "tt_saved_by" not in ss:
        ss.tt_saved_by = ss.get("tt_name", "")
    saved_by = sc[0].text_input("Your name", key="tt_saved_by")
    ss.tt_name = saved_by
    note = sc[1].text_input("What changed? (optional)", key=k("note"),
                            placeholder="e.g. Added Week 3, Thursday now full day at home school")
    is_draft = (not dr.get("id")) or dr.get("status") == tu.DRAFT
    bc_ = st.columns([1, 1, 2])
    save_clicked = bc_[0].button("💾 Save draft" if is_draft else "💾 Save changes", key=k("save"))
    pub_clicked = bc_[1].button("🚀 Save & publish", type="primary", key=k("pub"),
                                disabled=dr.get("status") == tu.COMPLETE)
    bc_[2].caption(f"Publish emails the {dr.get('program') or 'program'} teacher(s), Admin and Leadership, "
                   "and files a copy in the student's Document Archive folder.")
    if save_clicked or pub_clicked:
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
                    st.warning(f"{dr['student_initials']} already has an open timetable. "
                               "Edit that one from Timetables, or press the button again to create a second.")
                    st.stop()
            try:
                row = tu.save_timetable(client, dr, saved_by.strip(), note)
                row.setdefault("published_version", dr.get("published_version"))
            except Exception as e:
                st.error(f"Save failed: {e}")
            else:
                if pub_clicked:
                    msg = do_publish(row, saved_by.strip(), note)
                    row.update(status=tu.PUBLISHED, published_version=row.get("version"))
                elif row.get("status") == tu.DRAFT:
                    msg = (f"📝 Saved draft {row.get('student_initials')} (v{row.get('version')}). "
                           "Nothing has been sent — Publish when it's ready.")
                else:
                    msg = (f"💾 Saved v{row.get('version')}. These changes aren't live yet — "
                           "press **Save & publish** to send the update.")
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


# ══════════════════════════════════════════════════════════════════════════
# ⚙️ EMAIL SETTINGS (Admin & Leadership)
# ══════════════════════════════════════════════════════════════════════════
else:
    st.subheader("📧 Who gets published timetables")
    st.caption("When a timetable is published, it goes to everyone active under that student's program "
               "(JP, PY or SY), plus everyone under Admin and Leadership.")
    if confidential_gate():
        try:
            recips = tu.load_recipients(client, active_only=False)
        except Exception as e:
            recips = []
            st.error(f"Couldn't load recipients — has the SQL been run? ({e})")
        for role in tu.RECIPIENT_ROLES:
            group = [r for r in recips if r.get("role") == role]
            st.markdown(f"**{role}**" + ("" if group else "  — _nobody yet_"))
            for rc in group:
                c1, c2, c3, c4 = st.columns([3, 4, 1, 1])
                c1.write(rc.get("name") or "")
                c2.write(rc.get("email") or "")
                act = c3.checkbox("Active", value=bool(rc.get("active")), key=f"rca_{rc['id']}")
                if act != bool(rc.get("active")):
                    client.table(tu.TABLE_RECIPIENTS).update({"active": act}).eq("id", rc["id"]).execute()
                    st.rerun()
                if c4.button("Remove", key=f"rcd_{rc['id']}"):
                    client.table(tu.TABLE_RECIPIENTS).delete().eq("id", rc["id"]).execute()
                    st.rerun()

        with st.form("tt_add_recipient", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 4, 2])
            rn = c1.text_input("Name")
            re_ = c2.text_input("Email")
            rr = c3.selectbox("Group", tu.RECIPIENT_ROLES)
            if st.form_submit_button("Add recipient"):
                if rn.strip() and "@" in re_:
                    client.table(tu.TABLE_RECIPIENTS).insert(
                        {"name": rn.strip(), "email": re_.strip(), "role": rr, "active": True}).execute()
                    st.rerun()
                else:
                    st.error("Enter a name and a valid email.")

        cc = st.columns(2)
        if cc[0].button("Copy Admin & Leadership from Hazard Report"):
            try:
                hz = client.table("hazard_recipients").select("*").eq("active", True).execute().data or []
            except Exception:
                hz = []
            have = {(r.get("email", "").lower(), r.get("role")) for r in recips}
            new = [{"name": h.get("name"), "email": h.get("email"), "role": h.get("role"), "active": True}
                   for h in hz if h.get("role") in ("Admin", "Leadership")
                   and (str(h.get("email", "")).lower(), h.get("role")) not in have]
            if new:
                client.table(tu.TABLE_RECIPIENTS).insert(new).execute()
                ss.tt_flash = f"Copied {len(new)} recipient(s) from the Hazard Report."
                st.rerun()
            else:
                st.info("Nothing new to copy (or the Hazard Report list isn't in this database).")
        if recips and cc[1].button("Send a test email to all active recipients"):
            ok, msg = tu.send_email([r["email"] for r in recips if r.get("active")],
                                    "TEST — Transition Timetables email",
                                    "<p>This is a test from the CLC portal's Transition Timetables tool. "
                                    "Published timetables will arrive like this.</p>")
            (st.success if ok else st.error)(msg)
