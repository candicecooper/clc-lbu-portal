from theme import apply_clc_theme
import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime, timedelta
import calendar

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="CLC Calendar", page_icon="📅", layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()

from staff_auth import require_staff_auth, staff_logout_button
require_staff_auth("CLC Calendar", "📅")
staff_logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)


# ─── SUPABASE ───────────────────────────────────────────────────────────────────
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_supabase()

# ─── EVENT TYPES ────────────────────────────────────────────────────────────────
EVENT_TYPES = {
    "Staff Meeting":         {"color": "#1a2e4a", "bg": "#e8edf3", "emoji": "👥"},
    "PAC Meeting":           {"color": "#6d28d9", "bg": "#ede9fe", "emoji": "🏛️"},
    "PD / Professional Dev": {"color": "#065f46", "bg": "#d1fae5", "emoji": "📚"},
    "Team Meeting":          {"color": "#1d4ed8", "bg": "#dbeafe", "emoji": "🤝"},
    "Excursion / Event":     {"color": "#92400e", "bg": "#fef3c7", "emoji": "🎒"},
    "Planned Staff Absence": {"color": "#b91c1c", "bg": "#fee2e2", "emoji": "🏠"},
    "Staff Birthday":        {"color": "#be185d", "bg": "#fce7f3", "emoji": "🎂"},
    "Entry Meeting":         {"color": "#0e7490", "bg": "#cffafe", "emoji": "🚪"},
    "Review Meeting":        {"color": "#c2410c", "bg": "#ffedd5", "emoji": "🔍"},
    "Transition Meeting":    {"color": "#7c3aed", "bg": "#ede9fe", "emoji": "🔄"},
    "TAC Meeting":           {"color": "#b45309", "bg": "#fef3c7", "emoji": "📎"},
    "Student Placement":     {"color": "#374151", "bg": "#f3f4f6", "emoji": "📋"},
    "Other":                 {"color": "#374151", "bg": "#f3f4f6", "emoji": "📌"},
}

# Student meeting types — appear in BOTH normal calendar AND student placement view
STUDENT_MEETING_TYPES = ["Entry Meeting", "Review Meeting", "Transition Meeting", "TAC Meeting"]
# All student-related types
STUDENT_EVENT_TYPES   = STUDENT_MEETING_TYPES + ["Student Placement"]

# Program colour coding
PROGRAM_COLORS = {
    "JP": {"color": "#1d4ed8", "bg": "#dbeafe", "label": "Junior Primary"},
    "PY": {"color": "#15803d", "bg": "#dcfce7", "label": "Primary Years"},
    "SY": {"color": "#a16207", "bg": "#fef9c3", "label": "Senior Years"},
}

# ─── STYLES ─────────────────────────────────────────────────────────────────────

# ─── ADMIN PASSWORD ──────────────────────────────────────────────────────────────
try:
    CAL_ADMIN_PW = st.secrets["CAL_ADMIN_PASSWORD"]
except Exception:
    CAL_ADMIN_PW = "CLC2026"

# ─── SESSION STATE ───────────────────────────────────────────────────────────────
# Use Adelaide timezone for today's date
from datetime import timezone
import zoneinfo
try:
    _adelaide = zoneinfo.ZoneInfo("Australia/Adelaide")
    from datetime import datetime as _dt
    today = _dt.now(_adelaide).date()
except Exception:
    today = date.today()
for k, v in [("cal_year", today.year), ("cal_month", today.month),
              ("cal_week_start", today - timedelta(days=today.weekday())),
              ("selected_date", today), ("is_admin", True), ("edit_event_id", None),
              ("selected_event_id", None), ("quick_add_open", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# Only set defaults if not already in session state (don't override navigation)
if "selected_date" not in st.session_state:
    st.session_state.selected_date = today
if "cal_week_start" not in st.session_state:
    st.session_state.cal_week_start = today - timedelta(days=today.weekday())
if "cal_year" not in st.session_state:
    st.session_state.cal_year = today.year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = today.month

# ─── DB HELPERS ─────────────────────────────────────────────────────────────────
def db_events(start_date=None, end_date=None):
    q = supabase.table("clc_events").select("*").order("event_date").order("start_time")
    if start_date: q = q.gte("event_date", str(start_date))
    if end_date:   q = q.lte("event_date", str(end_date))
    return q.execute().data

def db_events_all():
    return supabase.table("clc_events").select("*").order("event_date").execute().data

def db_pac():
    try: return supabase.table("pac_meetings").select("*").order("meeting_date").execute().data
    except: return []

def pac_events(pac_list, d_from=None, d_to=None):
    out = []
    for p in pac_list:
        if not p.get("meeting_date"): continue
        d = str(p["meeting_date"])[:10]
        if d_from and d < str(d_from): continue
        if d_to   and d > str(d_to):   continue
        out.append({"title": f"{p.get('meeting_type','Ordinary')} PAC Meeting",
                    "event_type": "PAC Meeting", "event_date": p["meeting_date"],
                    "start_time": p.get("start_time"), "location": p.get("location",""),
                    "added_by": "PAC System", "notes": f"Chair: {p.get('chair','—')}",
                    "id": f"pac_{p['id']}"})
    return out

_DAY_NAME_TO_INT = {"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}
_PROG_LABEL = {"JP":"Junior Primary","PY":"Primary Years","SY":"Senior Years","STAFF":"All Staff","ADMIN":"Admin"}

def schedule_events(d_from=None, d_to=None):
    """Generate synthetic calendar events from tm_schedules flagged show_in_calendar."""
    try:
        res = supabase.table("tm_schedules").select("*").eq("show_in_calendar", True).execute()
        schedules = res.data or []
    except Exception:
        return []
    if not schedules or not d_from or not d_to:
        return []
    out = []
    cur = d_from
    while cur <= d_to:
        for s in schedules:
            dow = s.get("day_of_week", "")
            target = _DAY_NAME_TO_INT.get(dow, -1)
            if target == cur.weekday():
                prog = s.get("program", "")
                out.append({
                    "id": f"sched_{s['id']}_{cur}",
                    "title": s.get("schedule_name", "Team Meeting"),
                    "event_type": "Team Meeting",
                    "event_date": str(cur),
                    "end_date": None,
                    "start_time": s.get("meeting_time") or None,
                    "end_time": None,
                    "location": "",
                    "added_by": _PROG_LABEL.get(prog, prog),
                    "notes": s.get("notes",""),
                    "program": prog,
                    "student_initials": "",
                    "_from_schedule": True,
                })
        cur += timedelta(days=1)
    return out

def ev_index(events):
    idx = {}
    for ev in events:
        idx.setdefault(str(ev.get("event_date",""))[:10], []).append(ev)
    return idx

def fmt_date(d):
    try: return datetime.strptime(str(d)[:10], "%Y-%m-%d").strftime("%-d %B %Y")
    except: return str(d)[:10]

def fmt_time(t):
    if not t: return ""
    try: return datetime.strptime(str(t)[:5], "%H:%M").strftime("%-I:%M %p")
    except: return str(t)[:5]

def select_day(d):
    st.session_state.selected_date = d
    st.session_state.edit_event_id = None

def save_event(d):
    try:
        supabase.table("clc_events").insert({
            "title": d["title"].strip(), "event_type": d["etype"],
            "event_date": str(d["ev_date"]),
            "end_date": str(d["end_date"]) if d["end_date"] and d["end_date"] != d["ev_date"] else None,
            "start_time": str(d["start_t"]) if d["start_t"] else None,
            "end_time": str(d["end_t"]) if d["end_t"] else None,
            "location": d["location"].strip(), "added_by": d["who"].strip(), "notes": d["notes"].strip(),
            "program": d.get("program",""), "student_initials": d.get("student_initials",""),
        }).execute()
        st.success(f"✅ Event saved for {d['ev_date'].strftime('%-d %B %Y')}!")
    except Exception as e:
        st.error(f"❌ Could not save event: {e}")

def upd_event(ev_id, d):
    supabase.table("clc_events").update({
        "title": d["title"].strip(), "event_type": d["etype"],
        "event_date": str(d["ev_date"]),
        "end_date": str(d["end_date"]) if d["end_date"] and d["end_date"] != d["ev_date"] else None,
        "start_time": str(d["start_t"]) if d["start_t"] else None,
        "end_time": str(d["end_t"]) if d["end_t"] else None,
        "location": d["location"].strip(), "added_by": d["who"].strip(), "notes": d["notes"].strip(),
        "program": d.get("program",""), "student_initials": d.get("student_initials",""),
    }).eq("id", ev_id).execute()

def del_event(ev_id):
    try:
        result = supabase.table("clc_events").delete().eq("id", str(ev_id)).execute()
        return True
    except Exception as e:
        st.error(f"Could not delete event: {e}")
        return False

# ─── EVENT FORM ──────────────────────────────────────────────────────────────────
def event_form(key, default_date=None, existing=None, label="📅 Save Event"):
    ev = existing or {}
    d0 = default_date or today
    is_student = ev.get("event_type") in STUDENT_EVENT_TYPES

    with st.form(key, clear_on_submit=(existing is None)):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Event title *", value=ev.get("title",""),
                                  placeholder="e.g. Staff meeting, J.S. Entry Meeting")
            etype = st.selectbox("Type", list(EVENT_TYPES.keys()),
                                 index=list(EVENT_TYPES.keys()).index(ev.get("event_type","Other"))
                                 if ev.get("event_type") in EVENT_TYPES else len(EVENT_TYPES)-1)
            _staff_default = ev.get("added_by","") or ""
            who = st.text_input("Added by *", value=_staff_default, placeholder="Your name")
        with c2:
            ev_date  = st.date_input("Date *",
                                     value=datetime.strptime(str(ev.get("event_date",d0))[:10],"%Y-%m-%d").date()
                                     if ev.get("event_date") else d0)
            end_date = st.date_input("End date (leave same for single day)", value=ev_date)
            location = st.text_input("Location", value=ev.get("location",""))

        # Student-specific fields — shown when student event type selected
        st.markdown("**Student details** *(fill in for Entry/Review/Transition/Placement events)*")
        sc1, sc2 = st.columns(2)
        with sc1:
            student_initials = st.text_input("Student initials (privacy)",
                                             value=ev.get("student_initials",""),
                                             placeholder="e.g. J.S.")
        with sc2:
            prog_opts = ["", "JP", "PY", "SY"]
            prog_val  = ev.get("program","") or ""
            program   = st.selectbox("Program", prog_opts,
                                     index=prog_opts.index(prog_val) if prog_val in prog_opts else 0)

        c3, c4 = st.columns(2)
        with c3: start_t = st.time_input("Start time (optional)", value=None)
        with c4: end_t   = st.time_input("End time (optional)",   value=None)
        notes = st.text_area("Notes", value=ev.get("notes",""), height=64)
        ok = st.form_submit_button(label, type="primary", use_container_width=True)
        if ok:
            if not title.strip() or not who.strip():
                st.warning("Event title and 'Added by' are required.")
                return False, {}
            return True, dict(title=title, etype=etype, ev_date=ev_date, end_date=end_date,
                              start_t=start_t, end_t=end_t, location=location, who=who,
                              notes=notes, program=program, student_initials=student_initials)
    return False, {}

# ─── EVENT DETAIL PANEL ─────────────────────────────────────────────────────────
def event_detail_panel():
    """Show a floating detail card for the selected event."""
    eid = st.session_state.selected_event_id
    if not eid:
        return
    # Load event
    pac = str(eid).startswith("pac_")
    if pac:
        all_pac = db_pac()
        ev = next((e for e in pac_events(all_pac, date(2000,1,1), date(2099,12,31)) if e.get("id")==eid), None)
    else:
        try:
            res = supabase.table("clc_events").select("*").eq("id", eid).execute()
            ev  = res.data[0] if res.data else None
        except:
            ev = None
    if not ev:
        st.session_state.selected_event_id = None
        return

    cfg   = EVENT_TYPES.get(ev.get("event_type","Other"), EVENT_TYPES["Other"])
    prog  = ev.get("program","")
    if prog and ev.get("event_type") in STUDENT_EVENT_TYPES:
        pc  = PROGRAM_COLORS.get(prog, {})
        color = pc.get("color", cfg["color"]); bg = pc.get("bg", cfg["bg"])
    else:
        color = cfg["color"]; bg = cfg["bg"]

    tr = fmt_time(ev.get("start_time",""))
    if ev.get("end_time"): tr += f" – {fmt_time(ev['end_time'])}"
    edate = fmt_date(ev.get("event_date",""))
    if ev.get("end_date") and ev["end_date"] != ev.get("event_date"):
        edate += f" → {fmt_date(ev['end_date'])}"


# ─── MAIN PAGE ────────────────────────────────────────────────────────────────
yr = st.session_state.cal_year
mo = st.session_state.cal_month

ph_col1, ph_col2, ph_col3, ph_col4 = st.columns([1,3,1,1])
with ph_col1:
    if st.button("◀ Prev", use_container_width=True, key="m_prev"):
        new_mo = mo - 1 if mo > 1 else 12
        new_yr = yr - 1 if mo == 1 else yr
        st.session_state.cal_month = new_mo
        st.session_state.cal_year  = new_yr
        st.session_state.selected_date = date(new_yr, new_mo, 1)
        st.session_state.m_jump_last = date(new_yr, new_mo, 1)
        st.rerun()
with ph_col2:
    import calendar as _cal
    st.markdown(f"<h2 style='text-align:center;margin:0;color:#1a2e44;'>{_cal.month_name[mo]} {yr}</h2>", unsafe_allow_html=True)
with ph_col3:
    if st.button("▶ Next", use_container_width=True, key="m_next"):
        new_mo = mo + 1 if mo < 12 else 1
        new_yr = yr + 1 if mo == 12 else yr
        st.session_state.cal_month = new_mo
        st.session_state.cal_year  = new_yr
        st.session_state.selected_date = date(new_yr, new_mo, 1)
        st.session_state.m_jump_last = date(new_yr, new_mo, 1)
        st.rerun()
with ph_col4:
    if st.button("Today", use_container_width=True, key="m_today"):
        st.session_state.cal_year=today.year; st.session_state.cal_month=today.month
        select_day(today); st.rerun()

tab_month, tab_week, tab_list, tab_students = st.tabs(["📅 Month", "📆 Week", "📋 List", "👤 Students"])

with tab_month:
    ts = str(today)
    ss = str(st.session_state.selected_date)
    _mo_start = date(yr, mo, 1)
    _mo_end = date(yr, mo, 28) + timedelta(days=4)
    idx = ev_index(db_events(_mo_start, _mo_end) + schedule_events(_mo_start, _mo_end))
    day_headers = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    hcols = st.columns(7)
    for i, dn in enumerate(day_headers):
        with hcols[i]:
            st.markdown(f"<div style='text-align:center;font-weight:700;font-size:0.78rem;"
                        f"color:#1a2e4a;padding:0.3rem 0;border-bottom:2px solid #e5e7eb;"
                        f"margin-bottom:0.4rem;'>{dn}</div>", unsafe_allow_html=True)

    for week in calendar.monthcalendar(yr, mo):
        wcols = st.columns(7)
        for i, day in enumerate(week):
            with wcols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)
                    continue
                d = date(yr, mo, day); ds = str(d)
                is_today = ds == ts; is_sel = ds == ss
                day_evs  = idx.get(ds, [])

                border = "3px solid #d4af37" if is_today else ("3px solid #1a2e4a" if is_sel else "1px solid #e5e7eb")
                bg     = "#fffef5" if is_today else ("#e8edf3" if is_sel else "white")
                num_col= "#d4af37" if is_today else ("#1a2e4a" if is_sel else "#374151")
                badge  = (f"<span style='background:#d4af37;color:white;border-radius:50%;"
                          f"width:22px;height:22px;display:inline-flex;align-items:center;"
                          f"justify-content:center;font-size:0.72rem;font-weight:800;'>{day}</span>"
                          if is_today else
                          f"<span style='color:{num_col};font-weight:700;font-size:0.82rem;'>{day}</span>")

                chips_html = ""
                for ev in day_evs[:2]:
                    etype = ev.get("event_type","Other"); prog = ev.get("program","")
                    if prog and etype in STUDENT_EVENT_TYPES:
                        pc=PROGRAM_COLORS.get(prog,{}); cbg=pc.get("bg","#f3f4f6"); ccol=pc.get("color","#374151")
                        emoji=EVENT_TYPES.get(etype,EVENT_TYPES["Other"])["emoji"]
                    else:
                        cfg=EVENT_TYPES.get(etype,EVENT_TYPES["Other"]); cbg=cfg["bg"]; ccol=cfg["color"]; emoji=cfg["emoji"]
                    lbl = ev.get("student_initials","") or ev.get("title","")
                    lbl = lbl[:10]+"…" if len(lbl)>10 else lbl
                    chips_html += (f"<div style='background:{cbg};color:{ccol};border-radius:4px;"
                                   f"padding:0.1rem 0.3rem;font-size:0.62rem;font-weight:600;"
                                   f"margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;"
                                   f"white-space:nowrap;'>{emoji} {lbl}</div>")
                if len(day_evs) > 2:
                    chips_html += f"<div style='font-size:0.6rem;color:#888;'>+{len(day_evs)-2} more</div>"

                st.markdown(
                    f"<div style='border:{border};border-radius:8px;background:{bg};"
                    f"padding:0.4rem;min-height:80px;'>"
                    f"<div style='margin-bottom:4px;'>{badge}</div>{chips_html}</div>",
                    unsafe_allow_html=True)
                # Hidden click button
                if st.button(" ", key=f"mday_{yr}_{mo}_{day}", use_container_width=True):
                    select_day(d)
                    st.session_state.cal_year  = yr
                    st.session_state.cal_month = mo
                    st.session_state.quick_add_open = len(day_evs) == 0
                    st.session_state.selected_event_id = None
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Jump to date — use a separate tracking key so the widget doesn't fight with Prev/Next nav
    if "m_jump_last" not in st.session_state:
        st.session_state.m_jump_last = st.session_state.selected_date
    jumped = st.date_input("Jump to date:", value=st.session_state.selected_date, key="m_jump", label_visibility="collapsed")
    if jumped != st.session_state.m_jump_last:
        st.session_state.m_jump_last = jumped
        select_day(jumped); st.session_state.cal_year=jumped.year; st.session_state.cal_month=jumped.month; st.rerun()

    st.markdown("---")

    # ── Day panel ──
    sel = st.session_state.selected_date
    d_evs = db_events(sel, sel) + schedule_events(sel, sel) + pac_events(db_pac(), sel, sel)
    d_evs.sort(key=lambda x: str(x.get("start_time","")))
    st.markdown(f"### {'📍 ' if sel==today else ''}📅 {sel.strftime('%A %-d %B %Y')}")

    if not d_evs:
        st.markdown('<div class="add-prompt">📭 No events on this day — click ➕ below to add one</div>', unsafe_allow_html=True)

    for ev in d_evs:
        eid    = ev.get("id","")
        pac    = str(eid).startswith("pac_")
        cfg_ev = EVENT_TYPES.get(ev.get("event_type","Other"), EVENT_TYPES["Other"])
        prog   = ev.get("program","")
        ecol   = (PROGRAM_COLORS.get(prog,{}).get("color", cfg_ev["color"])
                  if prog and ev.get("event_type") in STUDENT_EVENT_TYPES else cfg_ev["color"])
        ebg    = (PROGRAM_COLORS.get(prog,{}).get("bg", cfg_ev["bg"])
                  if prog and ev.get("event_type") in STUDENT_EVENT_TYPES else cfg_ev["bg"])
        tr_ev  = fmt_time(ev.get("start_time",""))
        if ev.get("end_time"): tr_ev += f" – {fmt_time(ev['end_time'])}"
        can_edit = (st.session_state.is_admin or ev.get("event_type") in STUDENT_EVENT_TYPES) and not pac and not ev.get("_from_schedule")
        is_expanded = st.session_state.selected_event_id == eid

        # Event row
        ev_cols = st.columns([7, 1, 1, 1])
        with ev_cols[0]:
            st.markdown(
                f'<div class="ev-card" style="background:{ebg};border-left-color:{ecol};">'
                f'<h4 style="color:{ecol};margin:0 0 0.2rem;">{cfg_ev["emoji"]} {ev.get("title","")}'
                f'{(" · "+ev.get("student_initials","")) if ev.get("student_initials") else ""}</h4>'
                f'<div class="meta">'
                f'{(" ⏰ "+tr_ev) if tr_ev else ""}'
                f'{(" 📍 "+ev.get("location","")) if ev.get("location") else ""}'
                f'{(" 👤 "+ev.get("added_by","")) if ev.get("added_by") else ""}'
                f'</div></div>', unsafe_allow_html=True)
        with ev_cols[1]:
            st.write("")
            lbl = "✖" if is_expanded else "🔍"
            if st.button(lbl, key=f"mdet_{eid}", help="View details" if not is_expanded else "Close"):
                st.session_state.selected_event_id = None if is_expanded else eid
                st.rerun()
        with ev_cols[2]:
            if can_edit:
                st.write("")
                if st.button("✏️", key=f"med_{eid}", help="Edit"):
                    st.session_state.edit_event_id = eid if st.session_state.edit_event_id != eid else None
                    st.rerun()
        with ev_cols[3]:
            if st.session_state.is_admin and not pac:
                st.write("")
                confirm_key = f"confirm_del_{eid}"
                if st.session_state.get(confirm_key):
                    if st.button("✅ Yes", key=f"mdel_yes_{eid}", help="Confirm delete", type="primary"):
                        del_event(eid)
                        st.session_state[confirm_key] = False
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"mdel_{eid}", help="Delete event"):
                        st.session_state[confirm_key] = True
                        st.rerun()

        # ── Inline detail panel — expands directly under the event ──
        if is_expanded:
            edate = fmt_date(ev.get("event_date",""))
            if ev.get("end_date") and ev["end_date"] != ev.get("event_date"):
                edate += f" → {fmt_date(ev['end_date'])}"
            prog_badge = ""
            if prog:
                pc = PROGRAM_COLORS.get(prog,{})
                prog_badge = (f'<span style="background:{pc.get("bg","#f3f4f6")};color:{pc.get("color","#374151")};'
                              f'font-size:0.7rem;font-weight:700;padding:0.15rem 0.5rem;border-radius:20px;margin-left:6px;">{prog}</span>')
            st.markdown(
                f'<div style="background:{ebg};border:2px solid {ecol};border-radius:12px;'
                f'padding:1rem 1.25rem;margin:0.25rem 0 0.75rem;'
                f'box-shadow:0 3px 12px rgba(0,0,0,0.1);">'
                f'<div style="font-weight:800;color:{ecol};font-size:1rem;margin-bottom:0.6rem;">'
                f'{cfg_ev["emoji"]} {ev.get("title","")}'
                f'<span style="background:{ecol};color:white;font-size:0.68rem;font-weight:700;'
                f'padding:0.15rem 0.5rem;border-radius:20px;margin-left:8px;">{ev.get("event_type","")}</span>'
                f'{prog_badge}</div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;font-size:0.84rem;color:#374151;">'
                f'<div>📅 <b>Date:</b> {edate}</div>'
                f'{f"<div>⏰ <b>Time:</b> {tr_ev}</div>" if tr_ev else "<div></div>"}'
                f'{f"<div>📍 <b>Location:</b> {ev.get(chr(108)+chr(111)+chr(99)+chr(97)+chr(116)+chr(105)+chr(111)+chr(110))}</div>" if ev.get("location") else "<div></div>"}'
                f'{f"<div>👤 <b>Added by:</b> {ev.get(chr(97)+chr(100)+chr(100)+chr(101)+chr(100)+chr(95)+chr(98)+chr(121))}</div>" if ev.get("added_by") else "<div></div>"}'
                f'</div>'
                f'{f'<div style="margin-top:0.5rem;font-size:0.84rem;color:#555;border-top:1px solid rgba(0,0,0,0.08);padding-top:0.4rem;">{ev.get("notes")}</div>' if ev.get("notes") else ""}'
                f'</div>', unsafe_allow_html=True)

        # Edit form inline
        if st.session_state.edit_event_id == eid and can_edit:
            st.markdown("**✏️ Edit event:**")
            ok, data = event_form(f"mef_{eid}", existing=ev, label="💾 Save Changes")
            if ok:
                upd_event(eid, data); st.session_state.edit_event_id=None
                st.success("Updated!"); st.rerun()

    st.markdown(f"#### ➕ Add event on {sel.strftime('%-d %B %Y')}")
    ok, data = event_form(f"madd_{sel.year}_{sel.month}_{sel.day}", default_date=sel)
    if ok:
        save_event(data)
        st.session_state.cal_year  = data['ev_date'].year
        st.session_state.cal_month = data['ev_date'].month
        st.session_state.selected_date = data['ev_date']
        st.rerun()

# ═══════════════ WEEK VIEW ═════════════════════════════════════════════════════
with tab_week:
    # Hide the transparent overlay buttons on day tabs
    ws = st.session_state.cal_week_start
    we = ws + timedelta(days=6)
    wp, wt, wn, wtod = st.columns([1,3,1,1])
    with wp:
        if st.button("◀ Prev", use_container_width=True, key="w_prev"):
            st.session_state.cal_week_start -= timedelta(weeks=1); st.rerun()
    with wt:
        st.markdown(f"<h3 style='text-align:center;margin:0;color:#1a2e4a;'>{fmt_date(ws)} – {fmt_date(we)}</h3>", unsafe_allow_html=True)
    with wn:
        if st.button("Next ▶", use_container_width=True, key="w_next"):
            st.session_state.cal_week_start += timedelta(weeks=1); st.rerun()
    with wtod:
        if st.button("Today", use_container_width=True, key="w_today"):
            st.session_state.cal_week_start = today-timedelta(days=today.weekday()); select_day(today); st.rerun()

    wevs  = db_events(ws, we) + schedule_events(ws, we) + pac_events(db_pac(), ws, we)
    widx  = ev_index(wevs)
    ts    = str(today)
    ss    = str(st.session_state.selected_date)
    dnames= ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    wcols = st.columns(7)
    for i, wc in enumerate(wcols):
        d    = ws + timedelta(days=i); ds = str(d)
        itod = ds==ts; isel = ds==ss
        top  = "#d4af37" if itod else ("#1a2e4a" if isel else "#e0e0e0")
        bg   = "#fffef5" if itod else ("f0f4ff" if isel else "white")
        with wc:
            # Day header - clicking selects the day
            num_col = "#d4af37" if itod else ("#1a2e4a" if isel else "#374151")
            badge = (f"<span style='background:#d4af37;color:white;border-radius:50%;"
                     f"width:22px;height:22px;display:inline-flex;align-items:center;"
                     f"justify-content:center;font-size:0.72rem;font-weight:800;'>{d.day}</span>"
                     if itod else
                     f"<span style='font-weight:700;color:{num_col};'>{d.day}</span>")
            st.markdown(
                f"<div style='border-top:3px solid {top};background:{bg};border-radius:8px;"
                f"padding:0.4rem;min-height:90px;'>"
                f"<div style='font-size:0.7rem;font-weight:700;color:#888;text-transform:uppercase;"
                f"letter-spacing:0.05em;'>{dnames[i]}</div>"
                f"<div style='margin:2px 0 6px;'>{badge}</div>",
                unsafe_allow_html=True)
            for ev in widx.get(ds, []):
                etype = ev.get("event_type","Other"); prog = ev.get("program","")
                if prog and etype in STUDENT_EVENT_TYPES:
                    pc=PROGRAM_COLORS.get(prog,{}); cbg=pc.get("bg","#f3f4f6"); ccol=pc.get("color","#374151")
                    emoji=EVENT_TYPES.get(etype,EVENT_TYPES["Other"])["emoji"]
                else:
                    cfg=EVENT_TYPES.get(etype,EVENT_TYPES["Other"]); cbg=cfg["bg"]; ccol=cfg["color"]; emoji=cfg["emoji"]
                t     = fmt_time(ev.get("start_time",""))
                title = ev.get("student_initials","") or ev.get("title","")
                short = title[:9]+"…" if len(title)>9 else title
                st.markdown(
                    f"<div style='background:{cbg};border-left:3px solid {ccol};border-radius:4px;"
                    f"padding:0.15rem 0.3rem;margin-bottom:3px;font-size:0.68rem;'>"
                    f"<span style='font-weight:600;color:{ccol};'>{emoji} {short}</span>"
                    f"{f'<br><span style=chr(34)color:#777;font-size:0.62rem;{chr(34)}>{t}</span>' if t else ''}"
                    f"</div>", unsafe_allow_html=True)
            if not widx.get(ds,[]):
                st.markdown("<div style='color:#ddd;font-size:0.72rem;text-align:center;padding:0.3rem 0;'>—</div>",
                            unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            # Coloured button directly — label carries the colour info via CSS keyed on index
            n_evs = len(widx.get(ds,[]))
            if isel:
                tab_bg = "#1a2e44"; tab_col = "white"
                tab_lbl = "✅ Selected"
            elif itod:
                tab_bg = "#d4af37"; tab_col = "white"
                tab_lbl = (f"📍 {n_evs} event{'s' if n_evs!=1 else ''}") if n_evs else "📍 Today"
            elif n_evs:
                tab_bg = "#2d4a6e"; tab_col = "white"
                tab_lbl = f"👁 {n_evs} event{'s' if n_evs!=1 else ''}"
            else:
                tab_bg = "#6b7280"; tab_col = "white"
                tab_lbl = "➕ Add"
            # Inject CSS targeting this specific column button
            st.markdown(
                f"<style>div[data-testid='column']:nth-child({i+1}) "
                f"button[data-testid='baseButton-secondary'] {{"
                f" background-color:{tab_bg} !important;"
                f" color:{tab_col} !important;"
                f" border:none !important;"
                f" font-size:0.68rem !important;"
                f" font-weight:700 !important;"
                f" padding:0.3rem 0.1rem !important;"
                f" border-radius:6px !important; }}</style>",
                unsafe_allow_html=True)
            if st.button(tab_lbl, key=f"wsel_{i}", use_container_width=True):
                select_day(d)
                st.session_state.selected_event_id = None
                st.rerun()

    st.markdown("---")

    # ── Day panel — same inline detail expansion as month view ──
    sel   = st.session_state.selected_date
    d_evs = db_events(sel, sel) + schedule_events(sel, sel) + pac_events(db_pac(), sel, sel)
    d_evs.sort(key=lambda x: str(x.get("start_time","")))
    st.markdown(f"### {'📍 ' if sel==today else ''}📅 {sel.strftime('%A %-d %B %Y')}")

    if not d_evs:
        st.markdown('<div class="add-prompt">📭 No events on this day — click a day above or use ➕ below</div>',
                    unsafe_allow_html=True)

    for ev in d_evs:
        eid    = ev.get("id","")
        pac    = str(eid).startswith("pac_")
        cfg_ev = EVENT_TYPES.get(ev.get("event_type","Other"), EVENT_TYPES["Other"])
        prog   = ev.get("program","")
        ecol   = (PROGRAM_COLORS.get(prog,{}).get("color", cfg_ev["color"])
                  if prog and ev.get("event_type") in STUDENT_EVENT_TYPES else cfg_ev["color"])
        ebg    = (PROGRAM_COLORS.get(prog,{}).get("bg", cfg_ev["bg"])
                  if prog and ev.get("event_type") in STUDENT_EVENT_TYPES else cfg_ev["bg"])
        tr_ev  = fmt_time(ev.get("start_time",""))
        if ev.get("end_time"): tr_ev += f" – {fmt_time(ev['end_time'])}"
        can_edit  = (st.session_state.is_admin or ev.get("event_type") in STUDENT_EVENT_TYPES) and not pac
        is_expanded = st.session_state.selected_event_id == eid

        ev_cols = st.columns([7, 1, 1, 1])
        with ev_cols[0]:
            st.markdown(
                f'<div class="ev-card" style="background:{ebg};border-left-color:{ecol};">'
                f'<h4 style="color:{ecol};margin:0 0 0.2rem;">{cfg_ev["emoji"]} {ev.get("title","")}'
                f'{(" · "+ev.get("student_initials","")) if ev.get("student_initials") else ""}</h4>'
                f'<div class="meta">'
                f'{(" ⏰ "+tr_ev) if tr_ev else ""}'
                f'{(" 📍 "+ev.get("location","")) if ev.get("location") else ""}'
                f'{(" 👤 "+ev.get("added_by","")) if ev.get("added_by") else ""}'
                f'</div></div>', unsafe_allow_html=True)
        with ev_cols[1]:
            st.write("")
            if st.button("✖" if is_expanded else "🔍", key=f"wdet2_{eid}",
                         help="Close" if is_expanded else "View details"):
                st.session_state.selected_event_id = None if is_expanded else eid
                st.rerun()
        with ev_cols[2]:
            if can_edit:
                st.write("")
                if st.button("✏️", key=f"wed_{eid}", help="Edit"):
                    st.session_state.edit_event_id = eid if st.session_state.edit_event_id != eid else None
                    st.rerun()
        with ev_cols[3]:
            if st.session_state.is_admin and not pac:
                st.write("")
                confirm_key = f"confirm_del_{eid}"
                if st.session_state.get(confirm_key):
                    if st.button("✅ Yes", key=f"wdel_yes_{eid}", help="Confirm delete", type="primary"):
                        del_event(eid)
                        st.session_state[confirm_key] = False
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"wdel_{eid}", help="Delete event"):
                        st.session_state[confirm_key] = True
                        st.rerun()

        if is_expanded:
            edate = fmt_date(ev.get("event_date",""))
            if ev.get("end_date") and ev["end_date"] != ev.get("event_date"):
                edate += f" → {fmt_date(ev['end_date'])}"
            prog_badge = ""
            if prog:
                pc = PROGRAM_COLORS.get(prog,{})
                prog_badge = (f'<span style="background:{pc.get("bg","#f3f4f6")};color:{pc.get("color","#374151")};'
                              f'font-size:0.7rem;font-weight:700;padding:0.15rem 0.5rem;border-radius:20px;margin-left:6px;">{prog}</span>')
            st.markdown(
                f'<div style="background:{ebg};border:2px solid {ecol};border-radius:12px;'
                f'padding:1rem 1.25rem;margin:0.25rem 0 0.75rem;box-shadow:0 3px 12px rgba(0,0,0,0.1);">'
                f'<div style="font-weight:800;color:{ecol};font-size:1rem;margin-bottom:0.6rem;">'
                f'{cfg_ev["emoji"]} {ev.get("title","")}'
                f'<span style="background:{ecol};color:white;font-size:0.68rem;font-weight:700;'
                f'padding:0.15rem 0.5rem;border-radius:20px;margin-left:8px;">{ev.get("event_type","")}</span>'
                f'{prog_badge}</div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;font-size:0.84rem;color:#374151;">'
                f'<div>📅 <b>Date:</b> {edate}</div>'
                f'{f"<div>⏰ <b>Time:</b> {tr_ev}</div>" if tr_ev else "<div></div>"}'
                f'{f"<div>📍 <b>Location:</b> {ev.get('location','')}</div>" if ev.get("location") else "<div></div>"}'
                f'{f"<div>👤 <b>Added by:</b> {ev.get('added_by','')}</div>" if ev.get("added_by") else "<div></div>"}'
                f'</div>'
                f'{f'<div style="margin-top:0.5rem;font-size:0.84rem;color:#555;border-top:1px solid rgba(0,0,0,0.08);padding-top:0.4rem;">{ev.get("notes")}</div>' if ev.get("notes") else ""}'
                f'</div>', unsafe_allow_html=True)

        if st.session_state.edit_event_id == eid and can_edit:
            st.markdown("**✏️ Edit event:**")
            ok, data = event_form(f"wef_{eid}", existing=ev, label="💾 Save Changes")
            if ok:
                upd_event(eid, data); st.session_state.edit_event_id=None
                st.success("Updated!"); st.rerun()

    with st.expander(f"➕ Add event on {sel.strftime('%-d %B')}", expanded=(not d_evs and sel != today)):
        ok, data = event_form(f"wadd_{str(sel)}", default_date=sel)
        if ok: save_event(data); st.success(f"✅ '{data['title']}' added!"); st.rerun()

def render_event_card(ev, key_prefix="e"):
    """Render a single event as a styled card with optional edit/delete."""
    eid    = ev.get("id","")
    pac    = str(eid).startswith("pac_")
    sched  = ev.get("_from_schedule", False)
    cfg_ev = EVENT_TYPES.get(ev.get("event_type","Other"), EVENT_TYPES["Other"])
    prog   = ev.get("program","")
    ecol   = (PROGRAM_COLORS.get(prog,{}).get("color", cfg_ev["color"])
              if prog and ev.get("event_type") in STUDENT_EVENT_TYPES else cfg_ev["color"])
    ebg    = (PROGRAM_COLORS.get(prog,{}).get("bg", cfg_ev["bg"])
              if prog and ev.get("event_type") in STUDENT_EVENT_TYPES else cfg_ev["bg"])
    tr_ev  = fmt_time(ev.get("start_time",""))
    if ev.get("end_time"): tr_ev += f" – {fmt_time(ev['end_time'])}"
    can_edit = st.session_state.is_admin and not pac and not sched

    edate_str = ""
    if ev.get("end_date") and ev["end_date"] != ev.get("event_date"):
        edate_str = f" → {fmt_date(ev['end_date'])}"

    notes_html = (f'<div style="font-size:0.8rem;color:#555;border-top:1px solid rgba(0,0,0,0.08);'
                  f'padding-top:0.3rem;margin-top:0.3rem;">{ev["notes"]}</div>'
                  if ev.get("notes") else "")
    sched_badge = (' <span style="font-size:0.65rem;background:#e8f0fe;color:#1a4d8c;'
                   'border-radius:8px;padding:1px 6px;">🔁 Recurring</span>' if sched else "")

    st.markdown(
        f'<div style="background:{ebg};border-left:4px solid {ecol};border-radius:8px;'
        f'padding:0.55rem 0.85rem;margin-bottom:0.4rem;">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">'
        f'<span style="font-size:0.82rem;font-weight:700;color:{ecol};">'
        f'{cfg_ev["emoji"]} {ev.get("event_type","")}</span>'
        f'{sched_badge}'
        f'<span style="font-size:0.82rem;font-weight:600;color:#1a2e44;">{ev.get("title","")}</span>'
        f'{"<span style=\"font-size:0.75rem;color:#666;\"> · " + tr_ev + "</span>" if tr_ev else ""}'
        f'{"<span style=\"font-size:0.75rem;color:#666;\"> · 📍 " + ev["location"] + "</span>" if ev.get("location") else ""}'
        f'{"<span style=\"font-size:0.75rem;color:#888;\"> · " + ev.get("notes","") + "</span>" if ev.get("notes") and not notes_html else ""}'
        f'</div>{notes_html}</div>',
        unsafe_allow_html=True
    )
    if can_edit:
        ec1, ec2 = st.columns([1,1])
        with ec1:
            if st.button("✏️ Edit", key=f"edit_{key_prefix}_{eid}", use_container_width=True):
                st.session_state.edit_event_id = (None if st.session_state.edit_event_id==eid else eid)
                st.rerun()
        with ec2:
            if st.button("🗑️ Delete", key=f"del_{key_prefix}_{eid}", use_container_width=True):
                del_event(eid); st.rerun()
        if st.session_state.get("edit_event_id") == eid:
            ok, data = event_form(f"ef_{key_prefix}_{eid}", existing=ev, label="💾 Save Changes")
            if ok:
                upd_event(eid, data)
                st.session_state.edit_event_id = None
                st.success("Updated!"); st.rerun()


# ═══════════════ AGENDA VIEW ══════════════════════════════════════════════════
with tab_list:
    lc1, lc2, lc3 = st.columns(3)
    with lc1: ls = st.date_input("From", value=today, key="ls")
    with lc2: le = st.date_input("To",   value=today+timedelta(weeks=8), key="le")
    with lc3: tf = st.multiselect("Filter type", list(EVENT_TYPES.keys()), default=list(EVENT_TYPES.keys()), key="tf")

    with st.expander("➕ Add New Event"):
        ok, data = event_form("ladd")
        if ok: save_event(data); st.success(f"✅ '{data['title']}' added!"); st.rerun()

    st.markdown("---")
    levs  = db_events(ls, le) + schedule_events(ls, le) + pac_events(db_pac(), ls, le)
    levs  = [e for e in levs if e.get("event_type") in tf]
    levs.sort(key=lambda x: (str(x.get("event_date","")), str(x.get("start_time",""))))

    if not levs:
        st.markdown('<div class="info-box">No events in this date range.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(levs)} event{'s' if len(levs)!=1 else ''} found**")
        cur_d = None
        for ev in levs:
            eds = str(ev.get("event_date",""))[:10]
            if eds != cur_d:
                cur_d = eds
                try:
                    do = datetime.strptime(eds,"%Y-%m-%d").date()
                    lbl = f"📍 **TODAY — {do.strftime('%A %-d %B %Y')}**" if do==today else f"**{do.strftime('%A %-d %B %Y')}**"
                    st.markdown(lbl)
                except: st.markdown(f"**{eds}**")
            render_event_card(ev, "l")

# ═══════════════ STUDENTS VIEW ════════════════════════════════════════════════
with tab_students:
    st.markdown("### 👨‍🎓 Student Placements & Meetings")
    
    # ── Helpers for transition table ──
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    DAY_KEYS = ["mon", "tue", "wed", "thu", "fri"]

    def db_transitions(initials=None):
        try:
            q = supabase.table("student_transitions").select("*").order("week_start_date").order("student_initials")
            if initials:
                q = q.eq("student_initials", initials)
            return q.execute().data or []
        except Exception as e:
            st.error(f"Could not load transition data. Have you run the SQL migration? ({e})")
            return []

    def save_transition(d):
        supabase.table("student_transitions").insert(d).execute()

    def upd_transition(tid, d):
        supabase.table("student_transitions").update(d).eq("id", tid).execute()

    def del_transition(tid):
        supabase.table("student_transitions").delete().eq("id", tid).execute()

    def fmt_time_short(t):
        if not t: return ""
        try: return datetime.strptime(str(t)[:5], "%H:%M").strftime("%-I:%M%p").lower()
        except: return str(t)[:5]

    # ── Filters ──
    tr1, tr2, tr3 = st.columns(3)
    with tr1:
        tr_prog = st.multiselect("Program", ["JP","PY","SY"], default=["JP","PY","SY"], key="tr_prog")
    with tr2:
        # Get distinct students from transitions for filter
        all_trans = db_transitions()
        all_inits = sorted(set(t.get("student_initials","") for t in all_trans if t.get("student_initials")))
        tr_student = st.selectbox("Filter by student", ["All"] + all_inits, key="tr_student")
    with tr3:
        tr_term = st.selectbox("Filter by term", ["All", "Term 1", "Term 2", "Term 3", "Term 4"], key="tr_term")

    # ── Add new transition week ──
    with st.expander("➕ Add Transition Week"):
        with st.form("tr_add_form", clear_on_submit=True):
            tf1, tf2 = st.columns(2)
            with tf1:
                tr_initials  = st.text_input("Student initials *", placeholder="e.g. J.S.")
                tr_program_s = st.selectbox("Program *", ["", "JP", "PY", "SY"], key="tr_prog_add")
                tr_school    = st.text_input("Mainstream school name", placeholder="e.g. Cowandilla Primary")
                tr_added_by  = st.text_input("Added by *", placeholder="Your name")
            with tf2:
                tr_term_val  = st.selectbox("Term *", ["Term 1", "Term 2", "Term 3", "Term 4"], key="tr_term_add")
                tr_week_lbl  = st.text_input("Week label *", placeholder="e.g. Week 3")
                tr_week_date = st.date_input("Week start date (Monday) *", value=today - timedelta(days=today.weekday()), key="tr_week_date")
                tr_notes     = st.text_area("Notes (optional)", height=60)

            st.markdown("**Times at mainstream school** *(leave blank = at CLC all day)*")
            day_cols = st.columns(5)
            tr_times = {}
            for i, (day, dk) in enumerate(zip(DAYS, DAY_KEYS)):
                with day_cols[i]:
                    st.markdown(f"**{day[:3]}**")
                    tr_times[f"{dk}_start"] = st.time_input(f"From", value=None, key=f"tr_{dk}_s")
                    tr_times[f"{dk}_end"]   = st.time_input(f"To",   value=None, key=f"tr_{dk}_e")

            tr_ok = st.form_submit_button("✅ Save Transition Week", type="primary", use_container_width=True)
            if tr_ok:
                if not tr_initials.strip():
                    st.warning("Please enter student initials.")
                elif not tr_program_s:
                    st.warning("Please select a program.")
                elif not tr_added_by.strip():
                    st.warning("Please enter your name.")
                elif not tr_week_lbl.strip():
                    st.warning("Please enter a week label.")
                else:
                    row = {
                        "student_initials": tr_initials.strip(),
                        "program": tr_program_s,
                        "mainstream_school": tr_school.strip(),
                        "term": tr_term_val,
                        "week_label": tr_week_lbl.strip(),
                        "week_start_date": str(tr_week_date),
                        "notes": tr_notes.strip(),
                        "added_by": tr_added_by.strip(),
                    }
                    for dk in DAY_KEYS:
                        s = tr_times.get(f"{dk}_start")
                        e = tr_times.get(f"{dk}_end")
                        row[f"{dk}_start"] = str(s) if s else None
                        row[f"{dk}_end"]   = str(e) if e else None
                    save_transition(row)
                    st.success(f"✅ Transition week saved for {tr_initials.strip()}!")
                    st.rerun()

    st.markdown("---")

    # ── Fetch and filter ──
    disp_trans = db_transitions(initials=None if tr_student == "All" else tr_student)
    if tr_prog != ["JP","PY","SY"]:
        disp_trans = [t for t in disp_trans if t.get("program","") in tr_prog]
    if tr_term != "All":
        disp_trans = [t for t in disp_trans if t.get("term","") == tr_term]

    if not disp_trans:
        st.markdown('<div class="info-box">No transition schedules found. Add one above.</div>', unsafe_allow_html=True)
    else:
        # Group by student
        from collections import defaultdict
        by_student = defaultdict(list)
        for t in disp_trans:
            by_student[t.get("student_initials","?")].append(t)

        for init, weeks in by_student.items():
            prog = weeks[0].get("program","")
            pc   = PROGRAM_COLORS.get(prog, {"color":"#374151","bg":"#f3f4f6"})
            school = weeks[0].get("mainstream_school","")

            # Student header
            st.markdown(
                f'<div style="background:{pc["bg"]};border-left:4px solid {pc["color"]};border-radius:10px;'
                f'padding:0.6rem 1rem;margin:1rem 0 0.5rem;display:flex;align-items:center;gap:0.75rem;">'
                f'<span style="background:{pc["color"]};color:white;font-size:0.75rem;font-weight:700;'
                f'padding:0.2rem 0.55rem;border-radius:8px;">{prog}</span>'
                f'<strong style="font-size:1rem;color:{pc["color"]};">🔀 {init}</strong>'
                f'{"<span style=\"font-size:0.82rem;color:#666;\">→ "+school+"</span>" if school else ""}'
                f'</div>', unsafe_allow_html=True)

            # Build timetable HTML grid
            html = """
<style>
.tr-grid{border-collapse:collapse;width:100%;font-family:'Inter',sans-serif;margin-bottom:1rem;}
.tr-grid th{background:#4a7c59;color:white;padding:6px 10px;font-size:0.78rem;font-weight:600;text-align:center;border:1px solid #3a6347;}
.tr-grid th.row-h{background:#2d5a3d;text-align:left;min-width:90px;}
.tr-grid td{border:1px solid #d1d5db;padding:6px 8px;font-size:0.78rem;text-align:center;background:white;vertical-align:middle;}
.tr-grid td.label-cell{background:#f0f7f2;font-weight:600;color:#2d5a3d;text-align:left;white-space:nowrap;}
.tr-grid td.has-time{background:#d1fae5;color:#065f46;font-weight:600;}
.tr-grid td.no-time{background:#f9fafb;color:#9ca3af;font-size:0.72rem;}
.tr-grid tr.week-divider td{border-top:2px solid #6b9e7a;}
</style>
<table class="tr-grid">
<tr>
  <th class="row-h">Term / Week</th>
  <th>Monday</th><th>Tuesday</th><th>Wednesday</th><th>Thursday</th><th>Friday</th>
</tr>"""
            cur_term = None
            for idx_w, week in enumerate(weeks):
                trm  = week.get("term","")
                wlbl = week.get("week_label","")
                tid  = week.get("id","")
                # Week date labels row
                wdate = week.get("week_start_date","")
                try:
                    wmon = datetime.strptime(wdate[:10], "%Y-%m-%d").date()
                    date_cells = "".join([
                        f'<td style="font-size:0.7rem;color:#888;background:#fafafa;">{(wmon+timedelta(days=i)).strftime("%-d %b")}</td>'
                        for i in range(5)])
                except:
                    date_cells = "<td colspan='5'></td>"

                # Term header row
                if trm != cur_term:
                    cur_term = trm
                    html += f'<tr><td class="label-cell" colspan="6" style="background:#2d5a3d;color:white;font-size:0.8rem;letter-spacing:0.05em;text-transform:uppercase;">{trm}</td></tr>'

                # Week label + dates
                html += f'<tr class="{"week-divider" if idx_w>0 else ""}"><td class="label-cell" rowspan="2">{wlbl}</td>{date_cells}</tr>'

                # Time cells row
                html += "<tr>"
                for dk in DAY_KEYS:
                    s = fmt_time_short(week.get(f"{dk}_start"))
                    e = fmt_time_short(week.get(f"{dk}_end"))
                    if s and e:
                        html += f'<td class="has-time">{s}–{e}</td>'
                    elif s:
                        html += f'<td class="has-time">{s}</td>'
                    else:
                        html += '<td class="no-time">CLC</td>'
                html += "</tr>"

            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)

            # Notes
            if weeks[0].get("notes"):
                st.caption(f"📝 {weeks[0]['notes']}")

            # Edit / delete controls per week
            with st.expander(f"✏️ Edit / delete weeks for {init}"):
                for week in weeks:
                    tid   = week.get("id","")
                    wlbl  = week.get("week_label","")
                    wdate = week.get("week_start_date","")
                    ec1, ec2, ec3 = st.columns([4,1,1])
                    with ec1:
                        st.markdown(f"**{week.get('term','')} · {wlbl}** — {wdate}")
                    with ec2:
                        if st.button("✏️", key=f"tr_ed_{tid}"):
                            st.session_state.edit_event_id = tid if st.session_state.edit_event_id != tid else None
                            st.rerun()
                    with ec3:
                        if st.session_state.is_admin:
                            if st.button("🗑️", key=f"tr_del_{tid}"):
                                del_transition(tid); st.rerun()

                    if st.session_state.edit_event_id == tid:
                        with st.form(f"tr_ef_{tid}", clear_on_submit=False):
                            ef1, ef2 = st.columns(2)
                            with ef1:
                                e_init_tr   = st.text_input("Student initials *", value=week.get("student_initials",""))
                                prog_opts   = ["", "JP", "PY", "SY"]
                                e_prog_tr   = st.selectbox("Program *", prog_opts,
                                                           index=prog_opts.index(week.get("program","")) if week.get("program","") in prog_opts else 0)
                                e_school_tr = st.text_input("Mainstream school", value=week.get("mainstream_school",""))
                                e_by_tr     = st.text_input("Added by *", value=week.get("added_by",""))
                            with ef2:
                                e_term_tr   = st.selectbox("Term *", ["Term 1","Term 2","Term 3","Term 4"],
                                                           index=["Term 1","Term 2","Term 3","Term 4"].index(week.get("term","Term 1")) if week.get("term") in ["Term 1","Term 2","Term 3","Term 4"] else 0)
                                e_wlbl_tr   = st.text_input("Week label *", value=week.get("week_label",""))
                                try:
                                    e_wdate_tr = st.date_input("Week start date *",
                                                               value=datetime.strptime(week.get("week_start_date","")[:10],"%Y-%m-%d").date(),
                                                               key=f"tr_wd_{tid}")
                                except:
                                    e_wdate_tr = st.date_input("Week start date *", value=today, key=f"tr_wd_{tid}")
                                e_notes_tr  = st.text_area("Notes", value=week.get("notes",""), height=50)

                            st.markdown("**Times at mainstream**")
                            eday_cols = st.columns(5)
                            e_tr_times = {}
                            for i, (day, dk) in enumerate(zip(DAYS, DAY_KEYS)):
                                with eday_cols[i]:
                                    st.markdown(f"**{day[:3]}**")
                                    existing_s = week.get(f"{dk}_start")
                                    existing_e = week.get(f"{dk}_end")
                                    e_tr_times[f"{dk}_start"] = st.time_input(f"From", value=None, key=f"tr_e{dk}s_{tid}")
                                    e_tr_times[f"{dk}_end"]   = st.time_input(f"To",   value=None, key=f"tr_e{dk}e_{tid}")

                            if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                                upd_row = {
                                    "student_initials": e_init_tr.strip(),
                                    "program": e_prog_tr,
                                    "mainstream_school": e_school_tr.strip(),
                                    "term": e_term_tr,
                                    "week_label": e_wlbl_tr.strip(),
                                    "week_start_date": str(e_wdate_tr),
                                    "notes": e_notes_tr.strip(),
                                    "added_by": e_by_tr.strip(),
                                }
                                for dk in DAY_KEYS:
                                    s = e_tr_times.get(f"{dk}_start")
                                    e_val = e_tr_times.get(f"{dk}_end")
                                    upd_row[f"{dk}_start"] = str(s) if s else None
                                    upd_row[f"{dk}_end"]   = str(e_val) if e_val else None
                                upd_transition(tid, upd_row)
                                st.session_state.edit_event_id = None
                                st.success("Updated!"); st.rerun()

# ─── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;color:#aaa;font-size:0.76rem;">
Cowandilla Learning Centre · Communal Staff Calendar · Events auto-sync to Daily Bulletin
</div>""", unsafe_allow_html=True)
