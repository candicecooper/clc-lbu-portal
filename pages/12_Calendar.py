from theme import apply_clc_theme
import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime, timedelta
import calendar
from collections import defaultdict
import zoneinfo

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="CLC Calendar", page_icon="📅", layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()

# ── Inline staff auth (view is public; editing requires sign-in) ─────────────
def _cal_is_signed_in():
    return bool(st.session_state.get("_cal_staff_name", "").strip())

def _cal_staff_name():
    return st.session_state.get("_cal_staff_name", "").strip()

def get_staff_name():
    return _cal_staff_name()

st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.75rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Sidebar staff sign-in ─────────────────────────────────────────────────────
st.sidebar.markdown("---")
if _cal_is_signed_in():
    st.sidebar.success(f"✅ Signed in as **{_cal_staff_name()}**")
    st.sidebar.caption("You can add and edit calendar events.")
    if st.sidebar.button("🔓 Sign out", use_container_width=True):
        st.session_state["_cal_staff_name"] = ""
        st.rerun()
else:
    st.sidebar.markdown("### 🔐 Staff Sign In")
    st.sidebar.caption("Sign in to add or edit events. The calendar is viewable by everyone.")
    with st.sidebar.form("cal_signin_form", clear_on_submit=False):
        _sn_input = st.text_input("Your name", placeholder="e.g. Candice Cooper")
        _sn_pin   = st.text_input("Staff password", type="password", placeholder="Staff password")
        if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
            import os
            try:    _correct = st.secrets.get("APP_PASSWORD", "")
            except: _correct = os.environ.get("APP_PASSWORD", "")
            if not _correct:
                _correct = "clcstaff2026"
            if not _sn_input.strip():
                st.sidebar.warning("Please enter your name.")
            elif _sn_pin != _correct:
                st.sidebar.error("Incorrect password. Please try again.")
            else:
                st.session_state["_cal_staff_name"] = _sn_input.strip()
                st.rerun()
st.sidebar.markdown("---")

# ─── SUPABASE ───────────────────────────────────────────────────────────────────
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_supabase()

# ─── CONSTANTS ──────────────────────────────────────────────────────────────────
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

STUDENT_MEETING_TYPES = ["Entry Meeting", "Review Meeting", "Transition Meeting", "TAC Meeting"]
STUDENT_EVENT_TYPES   = STUDENT_MEETING_TYPES + ["Student Placement"]

PROGRAM_COLORS = {
    "JP": {"color": "#1d4ed8", "bg": "#dbeafe", "label": "Junior Primary"},
    "PY": {"color": "#15803d", "bg": "#dcfce7", "label": "Primary Years"},
    "SY": {"color": "#a16207", "bg": "#fef9c3", "label": "Senior Years"},
}

DAYS     = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri"]

PLACEMENT_TYPES = [
    "", "Mainstream Integration", "Community Placement", "Work Experience",
    "School-Based Apprenticeship", "Supported Transition", "Dual Enrolment",
    "Visiting Teacher Program", "Respite", "Other",
]
FUNDING_TYPES = ["", "NDIS", "DfE Support", "School Budget", "Program Budget", "Other"]

try:
    CAL_ADMIN_PW = st.secrets["CAL_ADMIN_PASSWORD"]
except Exception:
    CAL_ADMIN_PW = "CLC2026"

# ─── ADELAIDE TIME ───────────────────────────────────────────────────────────────
try:
    _adelaide = zoneinfo.ZoneInfo("Australia/Adelaide")
    today = datetime.now(_adelaide).date()
except Exception:
    today = date.today()

# ─── SESSION STATE ───────────────────────────────────────────────────────────────
for k, v in [
    ("cal_year",          today.year),
    ("cal_month",         today.month),
    ("cal_week_start",    today - timedelta(days=today.weekday())),
    ("selected_date",     today),
    ("is_admin",          False),
    ("edit_event_id",     None),
    ("selected_event_id", None),
    ("quick_add_open",    False),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# Update is_admin dynamically based on current sign-in state
st.session_state.is_admin = _cal_is_signed_in()

# ─── HOVER + CARD CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
.cal-day-cell { position: relative; cursor: pointer; }
.cal-tooltip {
    display: none;
    position: absolute;
    top: 92%;
    left: 0;
    z-index: 9999;
    background: #1a2e4a;
    color: white;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.75rem;
    min-width: 190px;
    max-width: 250px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    line-height: 1.75;
    pointer-events: none;
}
.cal-day-cell:hover .cal-tooltip { display: block; }
.ev-card {
    border-left: 4px solid #ccc;
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.4rem;
}
.ev-card h4 { font-size: 0.9rem; }
.meta { font-size: 0.78rem; color: #666; margin-top: 0.1rem; }
</style>
""", unsafe_allow_html=True)

# ─── DB HELPERS ─────────────────────────────────────────────────────────────────
def db_events(start_date=None, end_date=None):
    q = supabase.table("clc_events").select("*").order("event_date").order("start_time")
    if start_date: q = q.gte("event_date", str(start_date))
    if end_date:   q = q.lte("event_date", str(end_date))
    return q.execute().data or []

def db_pac():
    try: return supabase.table("pac_meetings").select("*").order("meeting_date").execute().data or []
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

_DAY_TO_INT  = {"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}
_PROG_LABEL  = {"JP":"Junior Primary","PY":"Primary Years","SY":"Senior Years","STAFF":"All Staff","ADMIN":"Admin"}

def schedule_events(d_from=None, d_to=None):
    try:
        schedules = supabase.table("tm_schedules").select("*").eq("show_in_calendar", True).execute().data or []
    except:
        return []
    if not schedules or not d_from or not d_to: return []
    out = []; cur = d_from
    while cur <= d_to:
        for s in schedules:
            if _DAY_TO_INT.get(s.get("day_of_week",""), -1) == cur.weekday():
                prog = s.get("program","")
                out.append({"id": f"sched_{s['id']}_{cur}", "title": s.get("schedule_name","Team Meeting"),
                            "event_type": "Team Meeting", "event_date": str(cur), "end_date": None,
                            "start_time": s.get("meeting_time") or None, "end_time": None,
                            "location": "", "added_by": _PROG_LABEL.get(prog, prog),
                            "notes": s.get("notes",""), "program": prog, "student_initials": "",
                            "_from_schedule": True})
        cur += timedelta(days=1)
    return out

# ── Student placements ────────────────────────────────────────────────────────
def db_placements(initials=None):
    try:
        q = supabase.table("student_placements").select("*").order("start_date")
        if initials: q = q.eq("student_initials", initials)
        return q.execute().data or []
    except:
        return []

def save_placement(d):
    supabase.table("student_placements").insert(d).execute()

def upd_placement(pid, d):
    supabase.table("student_placements").update(d).eq("id", pid).execute()

def del_placement(pid):
    supabase.table("student_placements").delete().eq("id", pid).execute()

# ── Transitions ──────────────────────────────────────────────────────────────
def db_transitions(initials=None):
    try:
        q = supabase.table("student_transitions").select("*").order("week_start_date").order("student_initials")
        if initials: q = q.eq("student_initials", initials)
        return q.execute().data or []
    except Exception as e:
        st.error(f"Could not load transition data: {e}"); return []

def save_transition(d): supabase.table("student_transitions").insert(d).execute()
def upd_transition(tid, d): supabase.table("student_transitions").update(d).eq("id", tid).execute()
def del_transition(tid): supabase.table("student_transitions").delete().eq("id", tid).execute()

# ── Utilities ────────────────────────────────────────────────────────────────
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

def fmt_time_short(t):
    if not t: return ""
    try: return datetime.strptime(str(t)[:5], "%H:%M").strftime("%-I:%M%p").lower()
    except: return str(t)[:5]

def select_day(d):
    st.session_state.selected_date = d
    st.session_state.edit_event_id = None

def _show_save_notification():
    """Display and clear any pending save success/error messages that survived rerun."""
    if "_cal_save_ok" in st.session_state:
        st.success(st.session_state.pop("_cal_save_ok"))
    if "_cal_save_err" in st.session_state:
        st.error(st.session_state.pop("_cal_save_err"))

# ─── SAVE / UPDATE / DELETE EVENTS ──────────────────────────────────────────────
def save_event(d):
    try:
        supabase.table("clc_events").insert({
            "title":            d["title"].strip(),
            "event_type":       d["etype"],
            "event_date":       str(d["ev_date"]),
            "end_date":         str(d["end_date"]) if d.get("end_date") and d["end_date"] != d["ev_date"] else None,
            "start_time":       str(d["start_t"]) if d.get("start_t") else None,
            "end_time":         str(d["end_t"])   if d.get("end_t")   else None,
            "location":         d.get("location","").strip(),
            "added_by":         d["who"].strip(),
            "notes":            d.get("notes","").strip(),
            "program":          d.get("program",""),
            "student_initials": d.get("student_initials",""),
        }).execute()
        # Store success message in session state so it survives st.rerun()
        try:
            date_label = d['ev_date'].strftime('%-d %B %Y')
        except Exception:
            date_label = str(d.get('ev_date', ''))
        st.session_state["_cal_save_ok"] = f"✅ '{d['title'].strip()}' saved for {date_label}!"
        return True
    except Exception as e:
        st.session_state["_cal_save_err"] = f"❌ Could not save event: {e}"
        return False

def upd_event(ev_id, d):
    supabase.table("clc_events").update({
        "title":            d["title"].strip(),
        "event_type":       d["etype"],
        "event_date":       str(d["ev_date"]),
        "end_date":         str(d["end_date"]) if d.get("end_date") and d["end_date"] != d["ev_date"] else None,
        "start_time":       str(d["start_t"]) if d.get("start_t") else None,
        "end_time":         str(d["end_t"])   if d.get("end_t")   else None,
        "location":         d.get("location","").strip(),
        "added_by":         d["who"].strip(),
        "notes":            d.get("notes","").strip(),
        "program":          d.get("program",""),
        "student_initials": d.get("student_initials",""),
    }).eq("id", ev_id).execute()

def del_event(ev_id):
    try:
        supabase.table("clc_events").delete().eq("id", str(ev_id)).execute()
        return True
    except Exception as e:
        st.error(f"Could not delete: {e}"); return False

# ─── EVENT FORM ──────────────────────────────────────────────────────────────────
def event_form(key, default_date=None, existing=None, label="📅 Save Event"):
    ev = existing or {}
    d0 = default_date or today

    with st.form(key, clear_on_submit=(existing is None)):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Event title *", value=ev.get("title",""), placeholder="e.g. Staff meeting, J.S. Entry Meeting")
            etype = st.selectbox("Type", list(EVENT_TYPES.keys()),
                                 index=list(EVENT_TYPES.keys()).index(ev.get("event_type","Other"))
                                 if ev.get("event_type") in EVENT_TYPES else len(EVENT_TYPES)-1)
            who   = st.text_input("Added by *", value=ev.get("added_by","") or get_staff_name())
        with c2:
            date_val = d0
            if existing and ev.get("event_date"):
                raw_date = ev["event_date"]
                if isinstance(raw_date, date):
                    date_val = raw_date
                else:
                    raw_date_str = str(raw_date)
                    for date_str in [raw_date_str[:10], raw_date_str.split('T')[0], raw_date_str]:
                        try:
                            date_val = datetime.strptime(date_str, "%Y-%m-%d").date(); break
                        except:
                            try:
                                date_val = datetime.fromisoformat(date_str).date(); break
                            except:
                                continue

            ev_date = st.date_input("Date *", value=date_val, key=f"{key}_evdate")

            end_date_val = ev_date
            if existing and ev.get("end_date"):
                raw_end = ev["end_date"]
                if isinstance(raw_end, date):
                    end_date_val = raw_end
                else:
                    raw_end_str = str(raw_end)
                    for date_str in [raw_end_str[:10], raw_end_str.split('T')[0], raw_end_str]:
                        try:
                            end_date_val = datetime.strptime(date_str, "%Y-%m-%d").date(); break
                        except:
                            try:
                                end_date_val = datetime.fromisoformat(date_str).date(); break
                            except:
                                continue

            end_date = st.date_input("End date (same for single day)", value=end_date_val, key=f"{key}_enddate")
            location = st.text_input("Location", value=ev.get("location",""))

        st.markdown("**Student details** *(for Entry / Review / Transition / Placement events)*")
        sc1, sc2 = st.columns(2)
        with sc1:
            student_initials = st.text_input("Student initials", value=ev.get("student_initials",""), placeholder="e.g. J.S.")
        with sc2:
            prog_opts = ["", "JP", "PY", "SY"]
            program   = st.selectbox("Program", prog_opts,
                                     index=prog_opts.index(ev.get("program","")) if ev.get("program","") in prog_opts else 0)

        c3, c4 = st.columns(2)
        with c3:
            start_t_val = None
            if existing and ev.get("start_time"):
                raw_time = str(ev["start_time"])
                for time_str in [raw_time[:8], raw_time[:5]]:
                    try:
                        start_t_val = datetime.strptime(time_str, "%H:%M:%S").time(); break
                    except:
                        try:
                            start_t_val = datetime.strptime(time_str, "%H:%M").time(); break
                        except:
                            continue
            start_t = st.time_input("Start time (optional)", value=start_t_val, key=f"{key}_startt")
        with c4:
            end_t_val = None
            if existing and ev.get("end_time"):
                raw_time = str(ev["end_time"])
                for time_str in [raw_time[:8], raw_time[:5]]:
                    try:
                        end_t_val = datetime.strptime(time_str, "%H:%M:%S").time(); break
                    except:
                        try:
                            end_t_val = datetime.strptime(time_str, "%H:%M").time(); break
                        except:
                            continue
            end_t = st.time_input("End time (optional)", value=end_t_val, key=f"{key}_endt")

        notes = st.text_area("Notes", value=ev.get("notes",""), height=64)
        ok = st.form_submit_button(label, type="primary", use_container_width=True)
        if ok:
            if not title.strip() or not who.strip():
                st.warning("Event title and 'Added by' are required."); return False, {}
            return True, dict(title=title, etype=etype, ev_date=ev_date, end_date=end_date,
                              start_t=start_t, end_t=end_t, location=location, who=who,
                              notes=notes, program=program, student_initials=student_initials)
    return False, {}

# ─── SHARED RENDER HELPERS ────────────────────────────────────────────────────────
def _ev_style(ev):
    cfg  = EVENT_TYPES.get(ev.get("event_type","Other"), EVENT_TYPES["Other"])
    prog = ev.get("program","")
    if prog and ev.get("event_type") in STUDENT_EVENT_TYPES:
        pc  = PROGRAM_COLORS.get(prog, {})
        col = pc.get("color", cfg["color"]); bg = pc.get("bg", cfg["bg"])
    else:
        col = cfg["color"]; bg = cfg["bg"]
    return col, bg, cfg

def render_detail_card(ev):
    col, bg, cfg = _ev_style(ev)
    prog = ev.get("program","")
    tr   = fmt_time(ev.get("start_time",""))
    if ev.get("end_time"): tr += f" – {fmt_time(ev['end_time'])}"
    edate = fmt_date(ev.get("event_date",""))
    if ev.get("end_date") and ev["end_date"] != ev.get("event_date"):
        edate += f" → {fmt_date(ev['end_date'])}"
    prog_badge = ""
    if prog:
        pc = PROGRAM_COLORS.get(prog,{})
        prog_badge = (f'<span style="background:{pc.get("bg","#f3f4f6")};color:{pc.get("color","#374151")};'
                      f'font-size:0.7rem;font-weight:700;padding:0.15rem 0.5rem;border-radius:20px;margin-left:6px;">{prog}</span>')
    loc_html  = f'<div>📍 <b>Location:</b> {ev["location"]}</div>'    if ev.get("location")  else "<div></div>"
    who_html  = f'<div>👤 <b>Added by:</b> {ev["added_by"]}</div>'    if ev.get("added_by")  else "<div></div>"
    time_html = f'<div>⏰ <b>Time:</b> {tr}</div>'                     if tr                  else "<div></div>"
    notes_html= (f'<div style="margin-top:0.5rem;font-size:0.84rem;color:#555;'
                 f'border-top:1px solid rgba(0,0,0,0.08);padding-top:0.4rem;">{ev["notes"]}</div>'
                 if ev.get("notes") else "")
    st.markdown(
        f'<div style="background:{bg};border:2px solid {col};border-radius:12px;'
        f'padding:1rem 1.25rem;margin:0.25rem 0 0.75rem;box-shadow:0 3px 12px rgba(0,0,0,0.1);">'
        f'<div style="font-weight:800;color:{col};font-size:1rem;margin-bottom:0.6rem;">'
        f'{cfg["emoji"]} {ev.get("title","")}'
        f'<span style="background:{col};color:white;font-size:0.68rem;font-weight:700;'
        f'padding:0.15rem 0.5rem;border-radius:20px;margin-left:8px;">{ev.get("event_type","")}</span>'
        f'{prog_badge}</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;font-size:0.84rem;color:#374151;">'
        f'<div>📅 <b>Date:</b> {edate}</div>{time_html}{loc_html}{who_html}'
        f'</div>{notes_html}</div>', unsafe_allow_html=True)

def render_event_row(ev, key_prefix="m"):
    eid   = ev.get("id","")
    pac   = str(eid).startswith("pac_")
    sched = ev.get("_from_schedule", False)
    col, bg, cfg = _ev_style(ev)
    tr    = fmt_time(ev.get("start_time",""))
    if ev.get("end_time"): tr += f" – {fmt_time(ev['end_time'])}"
    can_edit = (st.session_state.is_admin or ev.get("event_type") in STUDENT_EVENT_TYPES) and not pac and not sched
    can_del  = st.session_state.is_admin and not pac and not sched
    is_exp   = st.session_state.selected_event_id == eid

    ev_cols = st.columns([7, 1, 1, 1])
    with ev_cols[0]:
        st.markdown(
            f'<div class="ev-card" style="background:{bg};border-left-color:{col};">'
            f'<h4 style="color:{col};margin:0 0 0.2rem;">{cfg["emoji"]} {ev.get("title","")}'
            f'{(" · "+ev["student_initials"]) if ev.get("student_initials") else ""}</h4>'
            f'<div class="meta">'
            f'{(" ⏰ "+tr) if tr else ""}'
            f'{(" 📍 "+ev["location"]) if ev.get("location") else ""}'
            f'{(" 👤 "+ev["added_by"]) if ev.get("added_by") else ""}'
            f'</div></div>', unsafe_allow_html=True)
    with ev_cols[1]:
        st.write("")
        if st.button("✖" if is_exp else "🔍", key=f"{key_prefix}_det_{eid}",
                     help="Close" if is_exp else "View details"):
            st.session_state.selected_event_id = None if is_exp else eid
            st.rerun()
    with ev_cols[2]:
        if can_edit:
            st.write("")
            if st.button("✏️", key=f"{key_prefix}_ed_{eid}", help="Edit"):
                if st.session_state.edit_event_id != eid:
                    st.session_state.edit_event_id = eid
                    st.session_state[f"editing_event_{eid}"] = ev.copy()
                else:
                    st.session_state.edit_event_id = None
                    if f"editing_event_{eid}" in st.session_state:
                        del st.session_state[f"editing_event_{eid}"]
                st.rerun()
    with ev_cols[3]:
        if can_del:
            st.write("")
            ck = f"cdel_{key_prefix}_{eid}"
            if st.session_state.get(ck):
                if st.button("✅ Yes", key=f"{key_prefix}_delc_{eid}", type="primary"):
                    if del_event(eid):
                        st.session_state[ck] = False
                        st.session_state.selected_event_id = None
                    st.rerun()
            else:
                if st.button("🗑️", key=f"{key_prefix}_del_{eid}", help="Delete"):
                    st.session_state[ck] = True
                    st.rerun()

    if is_exp:
        render_detail_card(ev)

    if st.session_state.edit_event_id == eid and can_edit:
        st.markdown("**✏️ Edit event:**")
        event_to_edit = st.session_state.get(f"editing_event_{eid}", ev)
        ok, data = event_form(f"{key_prefix}_ef_{eid}", existing=event_to_edit, label="💾 Save Changes")
        if ok:
            upd_event(eid, data)
            st.session_state.edit_event_id = None
            if f"editing_event_{eid}" in st.session_state:
                del st.session_state[f"editing_event_{eid}"]
            st.success("✅ Updated!")
            st.rerun()

# ─── DAY CELL HTML ────────────────────────────────────────────────────────────────
def _chips(day_evs, max_chips=2):
    html = ""
    for ev in day_evs[:max_chips]:
        c, bg, cfg = _ev_style(ev)
        lbl = ev.get("student_initials","") or ev.get("title","")
        lbl = lbl[:10]+"…" if len(lbl) > 10 else lbl
        html += (f"<div style='background:{bg};color:{c};border-radius:4px;"
                 f"padding:0.1rem 0.3rem;font-size:0.62rem;font-weight:600;"
                 f"margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;"
                 f"white-space:nowrap;'>{cfg['emoji']} {lbl}</div>")
    if len(day_evs) > max_chips:
        html += f"<div style='font-size:0.6rem;color:#888;'>+{len(day_evs)-max_chips} more</div>"
    return html

def _tooltip(day_evs):
    if not day_evs: return ""
    lines = []
    for ev in day_evs:
        cfg = EVENT_TYPES.get(ev.get("event_type","Other"), EVENT_TYPES["Other"])
        t   = fmt_time(ev.get("start_time",""))
        lines.append(f"{cfg['emoji']} {ev.get('title','')}{' · '+t if t else ''}")
    return f"<div class='cal-tooltip'>{'<br>'.join(lines)}</div>"

def month_day_cell(d, day_evs, is_today, is_sel):
    border = "3px solid #d4af37" if is_today else ("3px solid #1a2e4a" if is_sel else "1px solid #e5e7eb")
    bg     = "#fffef5" if is_today else ("#e8edf3" if is_sel else "white")
    badge  = (f"<span style='background:#d4af37;color:white;border-radius:50%;width:22px;height:22px;"
              f"display:inline-flex;align-items:center;justify-content:center;font-size:0.72rem;font-weight:800;'>{d.day}</span>"
              if is_today else
              f"<span style='color:{'#d4af37' if is_today else '#1a2e4a' if is_sel else '#374151'};"
              f"font-weight:700;font-size:0.82rem;'>{d.day}</span>")
    return (f"<div class='cal-day-cell' style='border:{border};border-radius:8px;background:{bg};"
            f"padding:0.4rem;min-height:80px;'>"
            f"<div style='margin-bottom:4px;'>{badge}</div>"
            f"{_chips(day_evs)}{_tooltip(day_evs)}</div>")

def week_day_cell(d, day_evs, is_today, is_sel, day_name):
    top = "#d4af37" if is_today else ("#1a2e4a" if is_sel else "#e0e0e0")
    bg  = "#fffef5" if is_today else ("#f0f4ff" if is_sel else "white")
    badge = (f"<span style='background:#d4af37;color:white;border-radius:50%;width:22px;height:22px;"
             f"display:inline-flex;align-items:center;justify-content:center;font-size:0.72rem;font-weight:800;'>{d.day}</span>"
             if is_today else f"<span style='font-weight:700;color:{'#1a2e4a' if is_sel else '#374151'};'>{d.day}</span>")
    chips = ""
    for ev in day_evs[:3]:
        c, cbg, cfg = _ev_style(ev)
        t = fmt_time(ev.get("start_time",""))
        title = ev.get("student_initials","") or ev.get("title","")
        short = title[:9]+"…" if len(title) > 9 else title
        chips += (f"<div style='background:{cbg};border-left:3px solid {c};border-radius:4px;"
                  f"padding:0.15rem 0.3rem;margin-bottom:3px;font-size:0.68rem;'>"
                  f"<span style='font-weight:600;color:{c};'>{cfg['emoji']} {short}</span>"
                  f"{f'<br><span style=color:#777;font-size:0.62rem;>{t}</span>' if t else ''}"
                  f"</div>")
    if not day_evs:
        chips = "<div style='color:#ddd;font-size:0.72rem;text-align:center;padding:0.3rem 0;'>—</div>"
    return (f"<div class='cal-day-cell' style='border-top:3px solid {top};background:{bg};"
            f"border-radius:8px;padding:0.4rem;min-height:90px;'>"
            f"<div style='font-size:0.7rem;font-weight:700;color:#888;text-transform:uppercase;"
            f"letter-spacing:0.05em;'>{day_name}</div>"
            f"<div style='margin:2px 0 6px;'>{badge}</div>"
            f"{chips}{_tooltip(day_evs)}</div>")

# ═══════════════ MAIN HEADER ═══════════════════════════════════════════════════
yr = st.session_state.cal_year
mo = st.session_state.cal_month

ph1, ph2, ph3, ph4 = st.columns([1, 3, 1, 1])
with ph1:
    if st.button("◀ Prev", use_container_width=True, key="m_prev"):
        mo = mo-1 if mo > 1 else 12
        yr = yr if mo > 0 else yr-1
        if mo == 0: mo = 12
        if st.session_state.cal_month == 1: yr = st.session_state.cal_year - 1
        st.session_state.cal_month = mo
        st.session_state.cal_year  = yr
        try: st.session_state.selected_date = date(yr, mo, 1)
        except: pass
        st.rerun()
with ph2:
    import calendar as _cal
    st.markdown(f"<h2 style='text-align:center;margin:0;color:#1a2e44;'>{_cal.month_name[mo]} {yr}</h2>",
                unsafe_allow_html=True)
with ph3:
    if st.button("▶ Next", use_container_width=True, key="m_next"):
        mo = mo+1 if mo < 12 else 1
        yr = st.session_state.cal_year + (1 if st.session_state.cal_month == 12 else 0)
        st.session_state.cal_month = mo
        st.session_state.cal_year  = yr
        try: st.session_state.selected_date = date(yr, mo, 1)
        except: pass
        st.rerun()
with ph4:
    if st.button("Today", use_container_width=True, key="m_today"):
        st.session_state.cal_year = today.year; st.session_state.cal_month = today.month
        select_day(today); st.rerun()

tab_month, tab_week, tab_list, tab_students, tab_weekoverview = st.tabs(["📅 Month", "📆 Week", "📋 List", "👤 Students", "🖨️ Week Overview"])

# ═══════════════ MONTH VIEW ════════════════════════════════════════════════════
with tab_month:
    ts = str(today); ss = str(st.session_state.selected_date)
    _mo_start = date(yr, mo, 1); _mo_end = date(yr, mo, 28) + timedelta(days=4)
    idx = ev_index(db_events(_mo_start, _mo_end) + schedule_events(_mo_start, _mo_end))

    hcols = st.columns(7)
    for i, dn in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
        with hcols[i]:
            st.markdown(f"<div style='text-align:center;font-weight:700;font-size:0.78rem;color:#1a2e4a;"
                        f"padding:0.3rem 0;border-bottom:2px solid #e5e7eb;margin-bottom:0.4rem;'>{dn}</div>",
                        unsafe_allow_html=True)

    for week in calendar.monthcalendar(yr, mo):
        wcols = st.columns(7)
        for i, day in enumerate(week):
            with wcols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True); continue
                d = date(yr, mo, day); ds = str(d)
                day_evs = idx.get(ds, [])
                st.markdown(month_day_cell(d, day_evs, ds==ts, ds==ss), unsafe_allow_html=True)
                if st.button(" ", key=f"mday_{yr}_{mo}_{day}", use_container_width=True):
                    select_day(d)
                    st.session_state.cal_year  = yr
                    st.session_state.cal_month = mo
                    st.session_state.quick_add_open = len(day_evs) == 0
                    st.session_state.selected_event_id = None
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    jumped = st.date_input("Jump to date:", value=st.session_state.selected_date, key="m_jump", label_visibility="collapsed")
    if jumped != st.session_state.selected_date:
        select_day(jumped); st.session_state.cal_year=jumped.year; st.session_state.cal_month=jumped.month; st.rerun()

    st.markdown("---")

    sel   = st.session_state.selected_date
    d_evs = db_events(sel, sel) + schedule_events(sel, sel) + pac_events(db_pac(), sel, sel)
    d_evs.sort(key=lambda x: str(x.get("start_time","")))
    st.markdown(f"### {'📍 ' if sel==today else ''}📅 {sel.strftime('%A %-d %B %Y')}")
    if not d_evs:
        st.markdown('<p style="color:#888;font-size:0.9rem;">📭 No events on this day — use ➕ below to add one</p>',
                    unsafe_allow_html=True)
    for ev in d_evs:
        render_event_row(ev, "m")

    st.markdown(f"#### ➕ Add event on {sel.strftime('%-d %B %Y')}")
    if _cal_is_signed_in():
        _show_save_notification()
        ok, data = event_form(f"madd_{sel.year}_{sel.month}_{sel.day}", default_date=sel)
        if ok:
            if save_event(data):
                st.session_state.cal_year  = sel.year
                st.session_state.cal_month = sel.month
                st.rerun()
    else:
        st.info("🔐 **Sign in via the sidebar** to add or edit events.", icon="ℹ️")

# ═══════════════ WEEK VIEW ═════════════════════════════════════════════════════
with tab_week:
    ws = st.session_state.cal_week_start
    we = ws + timedelta(days=6)
    wp, wt, wn, wtod = st.columns([1, 3, 1, 1])
    with wp:
        if st.button("◀ Prev", use_container_width=True, key="w_prev"):
            st.session_state.cal_week_start -= timedelta(weeks=1)
            st.session_state.selected_date = st.session_state.cal_week_start
            st.rerun()
    with wt:
        st.markdown(f"<h3 style='text-align:center;margin:0;color:#1a2e4a;'>{fmt_date(ws)} – {fmt_date(we)}</h3>",
                    unsafe_allow_html=True)
    with wn:
        if st.button("Next ▶", use_container_width=True, key="w_next"):
            st.session_state.cal_week_start += timedelta(weeks=1)
            st.session_state.selected_date = st.session_state.cal_week_start
            st.rerun()
    with wtod:
        if st.button("Today", use_container_width=True, key="w_today"):
            st.session_state.cal_week_start = today - timedelta(days=today.weekday())
            select_day(today); st.rerun()

    wevs = db_events(ws, we) + schedule_events(ws, we) + pac_events(db_pac(), ws, we)
    widx = ev_index(wevs)
    ts   = str(today); ss = str(st.session_state.selected_date)
    dnames = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    wcols = st.columns(7)
    for i, wc in enumerate(wcols):
        d = ws + timedelta(days=i); ds = str(d)
        itod = ds==ts; isel = ds==ss
        day_evs = widx.get(ds, [])
        with wc:
            st.markdown(week_day_cell(d, day_evs, itod, isel, dnames[i]), unsafe_allow_html=True)
            n = len(day_evs)
            if isel:   lbl = "✅ Selected"; bg_b = "#1a2e44"; col_b = "white"
            elif itod: lbl = f"📍 {n} event{'s' if n!=1 else ''}" if n else "📍 Today"; bg_b = "#d4af37"; col_b = "white"
            elif n:    lbl = f"👁 {n} event{'s' if n!=1 else ''}"; bg_b = "#2d4a6e"; col_b = "white"
            else:      lbl = "➕ Add"; bg_b = "#6b7280"; col_b = "white"
            st.markdown(
                f"<style>div[data-testid='column']:nth-child({i+1}) "
                f"button[data-testid='baseButton-secondary'] {{"
                f" background-color:{bg_b}!important;color:{col_b}!important;"
                f" border:none!important;font-size:0.68rem!important;font-weight:700!important;"
                f" padding:0.3rem 0.1rem!important;border-radius:6px!important;}}</style>",
                unsafe_allow_html=True)
            if st.button(lbl, key=f"wsel_{i}", use_container_width=True):
                select_day(d); st.session_state.selected_event_id = None; st.rerun()

    st.markdown("---")

    sel   = st.session_state.selected_date
    d_evs = db_events(sel, sel) + schedule_events(sel, sel) + pac_events(db_pac(), sel, sel)
    d_evs.sort(key=lambda x: str(x.get("start_time","")))
    st.markdown(f"### {'📍 ' if sel==today else ''}📅 {sel.strftime('%A %-d %B %Y')}")
    if not d_evs:
        st.markdown('<p style="color:#888;font-size:0.9rem;">📭 No events — click a day above or use ➕ below</p>',
                    unsafe_allow_html=True)
    for ev in d_evs:
        render_event_row(ev, "w")
    if _cal_is_signed_in():
        with st.expander(f"➕ Add event on {sel.strftime('%-d %B')}", expanded=(not d_evs and sel != today)):
            _show_save_notification()
            ok, data = event_form(f"wadd_{str(sel)}", default_date=sel)
            if ok:
                if save_event(data):
                    st.rerun()
    else:
        st.info("🔐 **Sign in via the sidebar** to add or edit events.", icon="ℹ️")

# ═══════════════ LIST / AGENDA VIEW ═══════════════════════════════════════════
with tab_list:
    lc1, lc2, lc3 = st.columns(3)
    with lc1: ls = st.date_input("From", value=today, key="ls")
    with lc2: le = st.date_input("To",   value=today+timedelta(weeks=8), key="le")
    with lc3: tf = st.multiselect("Filter type", list(EVENT_TYPES.keys()), default=list(EVENT_TYPES.keys()), key="tf")

    if _cal_is_signed_in():
        with st.expander("➕ Add New Event"):
            _show_save_notification()
            ok, data = event_form("ladd")
            if ok:
                if save_event(data):
                    st.rerun()
    else:
        st.info("🔐 **Sign in via the sidebar** to add or edit events.", icon="ℹ️")

    st.markdown("---")
    levs = [e for e in (db_events(ls, le) + schedule_events(ls, le) + pac_events(db_pac(), ls, le))
            if e.get("event_type") in tf]
    levs.sort(key=lambda x: (str(x.get("event_date","")), str(x.get("start_time",""))))

    if not levs:
        st.markdown('<p style="color:#888;">No events in this date range.</p>', unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(levs)} event{'s' if len(levs)!=1 else ''} found**")
        cur_d = None
        for ev in levs:
            eds = str(ev.get("event_date",""))[:10]
            if eds != cur_d:
                cur_d = eds
                try:
                    do  = datetime.strptime(eds, "%Y-%m-%d").date()
                    lbl = f"📍 **TODAY — {do.strftime('%A %-d %B %Y')}**" if do==today else f"**{do.strftime('%A %-d %B %Y')}**"
                    st.markdown(lbl)
                except: st.markdown(f"**{eds}**")
            render_event_row(ev, f"l{eds}")

# ─── STUDENT TIMELINE RENDERER ───────────────────────────────────────────────────
MTG_COLORS = {
    "Entry Meeting":      "#0e7490",
    "Review Meeting":     "#c2410c",
    "Transition Meeting": "#7c3aed",
    "TAC Meeting":        "#b45309",
}
MTG_EMOJIS = {
    "Entry Meeting": "🚪", "Review Meeting": "🔍",
    "Transition Meeting": "🔄", "TAC Meeting": "📎",
}

def sa_terms(yr):
    if yr == 2026:
        return [
            {"name":"T1","full":"Term 1","start":date(2026,1,28),"end":date(2026,4,9), "color":"#e0f2fe"},
            {"name":"T2","full":"Term 2","start":date(2026,4,28),"end":date(2026,7,3), "color":"#dcfce7"},
            {"name":"T3","full":"Term 3","start":date(2026,7,20),"end":date(2026,9,25),"color":"#fef9c3"},
            {"name":"T4","full":"Term 4","start":date(2026,10,12),"end":date(2026,12,11),"color":"#fce7f3"},
        ]
    return [
        {"name":"T1","full":"Term 1","start":date(yr,2,1), "end":date(yr,4,10), "color":"#e0f2fe"},
        {"name":"T2","full":"Term 2","start":date(yr,5,1), "end":date(yr,7,5),  "color":"#dcfce7"},
        {"name":"T3","full":"Term 3","start":date(yr,7,20),"end":date(yr,9,26), "color":"#fef9c3"},
        {"name":"T4","full":"Term 4","start":date(yr,10,13),"end":date(yr,12,12),"color":"#fce7f3"},
    ]

def render_student_timeline(students_data, yr):
    year_start = date(yr, 1, 1)
    year_end   = date(yr, 12, 31)
    total_days = (year_end - year_start).days + 1
    terms      = sa_terms(yr)

    def pct(d):
        if not d: return -1.0
        if isinstance(d, str):
            try: d = datetime.strptime(d[:10], "%Y-%m-%d").date()
            except: return -1.0
        return max(0.0, min(100.0, (d - year_start).days / total_days * 100.0))

    today_pct = pct(today)

    css = """<style>
.tl-wrap{font-family:'Inter',sans-serif;margin:0.5rem 0 1.5rem;}
.tl-axis{position:relative;height:44px;margin:0 0 6px 160px;}
.tl-term-band{position:absolute;top:0;height:20px;border-radius:4px;border:1px solid rgba(0,0,0,0.08);}
.tl-term-label{position:absolute;top:2px;font-size:0.67rem;font-weight:700;color:#555;text-align:center;overflow:hidden;}
.tl-month-tick{position:absolute;top:20px;bottom:0;width:1px;background:#e5e7eb;}
.tl-month-lbl{position:absolute;top:24px;font-size:0.59rem;color:#aaa;transform:translateX(-50%);white-space:nowrap;}
.tl-today-marker{position:absolute;top:-6px;bottom:-6px;width:2px;background:#ef4444;border-radius:2px;z-index:20;}
.tl-today-marker::before{content:'▼';position:absolute;top:-12px;left:-4px;font-size:9px;color:#ef4444;}
.tl-student{position:relative;min-height:42px;margin-bottom:16px;}
.tl-student-label{position:absolute;left:0;top:50%;transform:translateY(-50%);width:155px;display:flex;align-items:center;gap:5px;overflow:hidden;}
.tl-prog-badge{flex-shrink:0;font-size:0.65rem;font-weight:800;padding:0.1rem 0.35rem;border-radius:5px;color:white;}
.tl-sname{font-size:0.8rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tl-school{font-size:0.67rem;color:#888;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tl-row-area{position:relative;margin-left:160px;height:40px;}
.tl-bg-track{position:absolute;top:11px;left:0;right:0;height:18px;background:#f3f4f6;border-radius:6px;}
.tl-term-shade{position:absolute;top:11px;height:18px;opacity:0.55;}
.tl-placement-bar{position:absolute;top:9px;height:22px;border-radius:6px;opacity:0.45;cursor:default;}
.tl-transition-bar{position:absolute;top:6px;height:28px;border-radius:5px;opacity:0.82;cursor:default;}
.tl-meeting-pin{position:absolute;top:0;transform:translateX(-50%);width:13px;height:13px;border-radius:50%;border:2.5px solid white;cursor:default;z-index:10;box-shadow:0 1px 4px rgba(0,0,0,0.25);}
.tl-legend{display:flex;flex-wrap:wrap;gap:14px;font-size:0.74rem;margin-top:16px;padding:10px 14px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;}
.tl-legend-item{display:flex;align-items:center;gap:5px;color:#374151;}
.tl-ls{width:18px;height:11px;border-radius:3px;flex-shrink:0;}
.tl-lc{width:11px;height:11px;border-radius:50%;flex-shrink:0;}
.tl-ll{width:2px;height:13px;border-radius:1px;flex-shrink:0;background:#ef4444;}
</style>"""

    axis = '<div class="tl-axis">'
    for t in terms:
        sp = pct(t["start"]); ep = pct(t["end"]); wp = max(0.0, ep-sp)
        axis += (f'<div class="tl-term-band" title="{t["full"]}" '
                 f'style="left:{sp:.2f}%;width:{wp:.2f}%;background:{t["color"]};"></div>'
                 f'<span class="tl-term-label" style="left:{sp:.2f}%;width:{wp:.2f}%;">{t["name"]}</span>')
    for m in range(1, 13):
        d = date(yr, m, 1); p = pct(d)
        axis += (f'<div class="tl-month-tick" style="left:{p:.2f}%;"></div>'
                 f'<span class="tl-month-lbl" style="left:{p:.2f}%;">{d.strftime("%b")}</span>')
    axis += '</div>'

    rows = ""
    for init, data in students_data.items():
        placements  = data.get("placements", [])
        transitions = data.get("transitions", [])
        meetings    = data.get("meetings", [])
        prog        = data.get("program", "")
        pc          = PROGRAM_COLORS.get(prog, {"color":"#374151","bg":"#f3f4f6"})
        school      = placements[0].get("placement_school","") if placements else ""

        rows += '<div class="tl-student">'
        rows += (f'<div class="tl-student-label">'
                 f'<span class="tl-prog-badge" style="background:{pc["color"]};">{prog or "—"}</span>'
                 f'<div><div class="tl-sname" style="color:{pc["color"]};">{init}</div>'
                 f'{"<div class=tl-school>"+school+"</div>" if school else ""}</div></div>')

        rows += '<div class="tl-row-area"><div class="tl-bg-track"></div>'

        for t in terms:
            sp = pct(t["start"]); ep = pct(t["end"]); wp = max(0.0, ep-sp)
            rows += f'<div class="tl-term-shade" style="left:{sp:.2f}%;width:{wp:.2f}%;background:{t["color"]};"></div>'

        rows += f'<div class="tl-today-marker" style="left:{today_pct:.2f}%;"></div>'

        for pl in placements:
            sp = pct(pl.get("start_date","")); ep = pct(pl.get("end_date",""))
            if sp < 0 or ep < 0: continue
            wp = max(0.4, ep-sp)
            tip = f"{pl.get('placement_type','Placement')} · {pl.get('placement_school','')} · {fmt_date(pl.get('start_date',''))} to {fmt_date(pl.get('end_date',''))}"
            rows += (f'<div class="tl-placement-bar" title="{tip}" '
                     f'style="left:{sp:.2f}%;width:{wp:.2f}%;background:{pc["color"]};"></div>')

        for tr in transitions:
            try: wmon = datetime.strptime(tr.get("week_start_date","")[:10], "%Y-%m-%d").date()
            except: continue
            if not (year_start <= wmon <= year_end): continue
            if not any(tr.get(f"{dk}_start") for dk in DAY_KEYS): continue
            sp = pct(wmon); ep = pct(wmon + timedelta(days=4)); wp = max(0.3, ep-sp)
            school_tr = tr.get("mainstream_school","mainstream")
            tip = f"{tr.get('week_label','')} at {school_tr} · {wmon.strftime('%-d %b')}"
            rows += (f'<div class="tl-transition-bar" title="{tip}" '
                     f'style="left:{sp:.2f}%;width:{wp:.2f}%;background:{pc["color"]};"></div>')

        for mtg in meetings:
            try: md = datetime.strptime(str(mtg.get("event_date",""))[:10], "%Y-%m-%d").date()
            except: continue
            if not (year_start <= md <= year_end): continue
            mp  = pct(md)
            mc  = MTG_COLORS.get(mtg.get("event_type",""), "#374151")
            em  = MTG_EMOJIS.get(mtg.get("event_type",""), "")
            tip = f"{em} {mtg.get('event_type','')} · {fmt_date(md)}"
            rows += (f'<div class="tl-meeting-pin" title="{tip}" '
                     f'style="left:{mp:.2f}%;background:{mc};"></div>')

        rows += '</div></div>'

    legend = ('<div class="tl-legend">'
              '<div class="tl-legend-item"><div class="tl-ls" style="background:#6b7280;opacity:0.45;"></div>Placement period</div>'
              '<div class="tl-legend-item"><div class="tl-ls" style="background:#6b7280;opacity:0.82;"></div>Transition weeks at mainstream</div>'
              '<div class="tl-legend-item"><div class="tl-lc" style="background:#0e7490;"></div>Entry Meeting</div>'
              '<div class="tl-legend-item"><div class="tl-lc" style="background:#c2410c;"></div>Review Meeting</div>'
              '<div class="tl-legend-item"><div class="tl-lc" style="background:#7c3aed;"></div>Transition Meeting</div>'
              '<div class="tl-legend-item"><div class="tl-lc" style="background:#b45309;"></div>TAC Meeting</div>'
              '<div class="tl-legend-item"><div class="tl-ll"></div>Today</div>'
              '</div>')

    return f'<div class="tl-wrap">{css}{axis}{rows}{legend}</div>'

# ═══════════════ STUDENTS VIEW ════════════════════════════════════════════════
with tab_students:
    st.markdown("### 👨‍🎓 Student Placements & Meetings")
    st_timeline, st_place, st_trans, st_mtg = st.tabs(["📊 Student Timeline", "📋 Placement Details", "🔄 Transition Schedule", "📅 Student Meetings"])

    # ════ STUDENT TIMELINE ═════════════════════════════════════════════════════
    with st_timeline:
        tl_c1, tl_c2, _ = st.columns([2, 2, 4])
        with tl_c1:
            tl_year = st.selectbox("Year", [2025, 2026, 2027], index=1, key="tl_year")
        with tl_c2:
            tl_prog_filter = st.multiselect("Program", ["JP","PY","SY"], default=["JP","PY","SY"], key="tl_prog")

        all_pl  = db_placements()
        all_tr  = db_transitions()
        all_mtg = [e for e in db_events(date(tl_year,1,1), date(tl_year,12,31)) if e.get("event_type") in STUDENT_MEETING_TYPES]

        students_map = defaultdict(lambda: {"placements":[], "transitions":[], "meetings":[], "program":""})
        for pl in all_pl:
            init = pl.get("student_initials","")
            if not init or pl.get("program","") not in tl_prog_filter: continue
            students_map[init]["placements"].append(pl)
            students_map[init]["program"] = pl.get("program","")
        for tr in all_tr:
            init = tr.get("student_initials","")
            if not init or tr.get("program","") not in tl_prog_filter: continue
            students_map[init]["transitions"].append(tr)
            if not students_map[init]["program"]: students_map[init]["program"] = tr.get("program","")
        for mtg in all_mtg:
            init = mtg.get("student_initials","")
            if not init or mtg.get("program","") not in tl_prog_filter: continue
            students_map[init]["meetings"].append(mtg)
            if not students_map[init]["program"]: students_map[init]["program"] = mtg.get("program","")

        prog_order = {"JP":0,"PY":1,"SY":2,"":3}
        sorted_students = dict(sorted(students_map.items(), key=lambda x: (prog_order.get(x[1]["program"],3), x[0])))

        if not sorted_students:
            st.markdown("<p style=color:#888;>No student data found. Add placements and log meetings in the other tabs to populate the timeline.</p>", unsafe_allow_html=True)
        else:
            count = len(sorted_students)
            st.markdown(f"<div style=background:#f0fdf4;border-left:4px solid #15803d;border-radius:8px;padding:0.6rem 1rem;font-size:0.82rem;color:#14532d;margin-bottom:1rem;><b>{count} student{chr(115) if count!=1 else ''}</b> shown. Hover bars and dots for details. <b>Faint bar</b> = placement period &nbsp;|&nbsp; <b>Solid bar</b> = transition weeks at mainstream &nbsp;|&nbsp; <b>Dots</b> = meetings.</div>", unsafe_allow_html=True)
            st.markdown(render_student_timeline(sorted_students, tl_year), unsafe_allow_html=True)

    # ════ PLACEMENT DETAILS ══════════════════════════════════════════════════════
    with st_place:
        st.markdown(
            '<div style="background:#f0f9ff;border-left:4px solid #0e7490;border-radius:8px;'
            'padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.84rem;color:#0e4a5e;">'
            '📋 Record full placement details here — school, support arrangements, funding, goals and contacts. '
            'Placements auto-appear in the Student Timeline above.</div>', unsafe_allow_html=True)

        if not _cal_is_signed_in():
            st.info("🔐 **Sign in via the sidebar** to add or edit student records.", icon="ℹ️")
        else:
         with st.expander("➕ Add New Placement", expanded=True):
            with st.form("place_add_form", clear_on_submit=True):
                pa1, pa2 = st.columns(2)
                with pa1:
                    pa_init   = st.text_input("Student initials *", placeholder="e.g. J.S.", key="pa_init")
                    pa_prog   = st.selectbox("Program *", ["", "JP", "PY", "SY"], key="pa_prog")
                    pa_type   = st.selectbox("Placement type", PLACEMENT_TYPES, key="pa_type")
                    pa_school = st.text_input("School / placement site *", placeholder="e.g. Findon Primary School", key="pa_school")
                    pa_fund   = st.selectbox("Funding type", FUNDING_TYPES, key="pa_fund")
                with pa2:
                    pa_start   = st.date_input("Start date *", value=today, key="pa_start")
                    pa_end     = st.date_input("End date *",   value=today + timedelta(weeks=10), key="pa_end")
                    pa_contact = st.text_input("Contact person", placeholder="e.g. Jane Smith (Principal)", key="pa_contact")
                    pa_phone   = st.text_input("Contact phone", placeholder="e.g. 08 8123 4567", key="pa_phone")
                    pa_email   = st.text_input("Contact email", placeholder="e.g. j.smith@schools.sa.edu.au", key="pa_email")

                pa_support = st.text_area("Support arrangements", height=64,
                                          placeholder="e.g. 1:1 SSO support Tues–Thurs, check-ins with class teacher, sensory breaks as needed",
                                          key="pa_support")
                pa_goals   = st.text_area("Placement goals", height=64,
                                          placeholder="e.g. Build peer relationships, participate in structured activities independently, develop self-regulation strategies",
                                          key="pa_goals")
                pa_notes   = st.text_area("Additional notes", height=48, key="pa_notes")

                if st.form_submit_button("✅ Save Placement", type="primary", use_container_width=True):
                    if not pa_init.strip():     st.warning("Student initials are required.")
                    elif not pa_prog:           st.warning("Please select a program.")
                    elif not pa_school.strip(): st.warning("School / placement site is required.")
                    elif pa_end < pa_start:     st.warning("End date must be on or after start date.")
                    else:
                        # Fold all extended fields into notes to avoid missing-column errors
                        contact_combined = pa_contact.strip()
                        if pa_email.strip():
                            contact_combined = f"{contact_combined} — {pa_email.strip()}" if contact_combined else pa_email.strip()
                        notes_parts = []
                        if pa_type:                  notes_parts.append(f"Type: {pa_type}")
                        if pa_fund:                  notes_parts.append(f"Funding: {pa_fund}")
                        if pa_phone.strip():         notes_parts.append(f"Phone: {pa_phone.strip()}")
                        if pa_support.strip():       notes_parts.append(f"Support: {pa_support.strip()}")
                        if pa_goals.strip():         notes_parts.append(f"Goals: {pa_goals.strip()}")
                        if pa_notes.strip():         notes_parts.append(pa_notes.strip())
                        save_placement({
                            "student_initials": pa_init.strip(),
                            "program":          pa_prog,
                            "placement_school": pa_school.strip(),
                            "start_date":       str(pa_start),
                            "end_date":         str(pa_end),
                            "contact_person":   contact_combined,
                            "notes":            "\n".join(notes_parts),
                        })
                        st.session_state["_cal_save_ok"] = f"✅ Placement saved for {pa_init.strip()} at {pa_school.strip()}!"
                        st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Existing Placements")

        pf1, pf2 = st.columns(2)
        with pf1: pf_prog = st.multiselect("Filter program", ["JP","PY","SY"], default=["JP","PY","SY"], key="pf_prog")
        with pf2: pf_init = st.text_input("Filter by initials", placeholder="Leave blank for all", key="pf_init")

        all_pls = db_placements(pf_init.strip() if pf_init.strip() else None)
        if pf_prog != ["JP","PY","SY"]:
            all_pls = [p for p in all_pls if p.get("program","") in pf_prog]

        if not all_pls:
            st.markdown('<p style="color:#888;">No placements found. Add one above.</p>', unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(all_pls)} placement{'s' if len(all_pls)!=1 else ''} found**")
            for pl in all_pls:
                pid   = pl.get("id","")
                prog  = pl.get("program","")
                pc    = PROGRAM_COLORS.get(prog, {"color":"#374151","bg":"#f3f4f6"})
                ptype = pl.get("placement_type","") or "Placement"
                dur   = f"{fmt_date(pl.get('start_date',''))} → {fmt_date(pl.get('end_date',''))}"

                with st.expander(f"[{prog}] {pl.get('student_initials','?')} · {ptype} · {pl.get('placement_school','')} · {dur}"):
                    badge_html = (f'<span style="background:{pc["bg"]};color:{pc["color"]};font-size:0.68rem;'
                                  f'font-weight:800;padding:0.12rem 0.4rem;border-radius:6px;">{prog}</span> '
                                  if prog else "")
                    st.markdown(
                        f'<div style="background:{pc["bg"]};border-left:4px solid {pc["color"]};'
                        f'border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.75rem;font-size:0.84rem;">'
                        f'{badge_html}<b style="color:{pc["color"]};">{pl.get("student_initials","")}</b>'
                        f' — {ptype} at <b>{pl.get("placement_school","")}</b><br>'
                        f'<span style="color:#555;">📅 {dur}</span>'
                        f'{("<br>👤 Contact: "+pl["contact_person"]) if pl.get("contact_person") else ""}'
                        f'</div>', unsafe_allow_html=True)
                    if pl.get("notes"):
                        st.markdown(pl['notes'])

                    ec1, ec2 = st.columns(2)
                    with ec1:
                        ek = f"pl_edit_{pid}"
                        if st.button("✏️ Edit", key=f"pl_ed_{pid}"):
                            st.session_state[ek] = not st.session_state.get(ek, False)
                            st.rerun()
                        if st.session_state.get(ek):
                            with st.form(f"pl_ef_{pid}", clear_on_submit=False):
                                e1, e2 = st.columns(2)
                                with e1:
                                    e_init   = st.text_input("Student initials", value=pl.get("student_initials",""))
                                    e_prog   = st.selectbox("Program", ["","JP","PY","SY"],
                                                            index=["","JP","PY","SY"].index(pl.get("program","")) if pl.get("program","") in ["","JP","PY","SY"] else 0)
                                    # Parse stored fields back out of notes
                                    _notes_raw = pl.get("notes","") or ""
                                    def _parse_note(prefix, text):
                                        for line in text.splitlines():
                                            if line.startswith(prefix+":"):
                                                return line[len(prefix)+1:].strip()
                                        return ""
                                    _stored_type    = _parse_note("Type",    _notes_raw)
                                    _stored_fund    = _parse_note("Funding", _notes_raw)
                                    _stored_phone   = _parse_note("Phone",   _notes_raw)
                                    _stored_support = _parse_note("Support", _notes_raw)
                                    _stored_goals   = _parse_note("Goals",   _notes_raw)
                                    _stored_notes   = "\n".join(l for l in _notes_raw.splitlines() if not any(l.startswith(p+":") for p in ["Type","Funding","Phone","Support","Goals"]))
                                    e_type   = st.selectbox("Placement type", PLACEMENT_TYPES,
                                                            index=PLACEMENT_TYPES.index(_stored_type) if _stored_type in PLACEMENT_TYPES else 0)
                                    e_school = st.text_input("School / site", value=pl.get("placement_school",""))
                                    e_fund   = st.selectbox("Funding", FUNDING_TYPES,
                                                            index=FUNDING_TYPES.index(_stored_fund) if _stored_fund in FUNDING_TYPES else 0)
                                with e2:
                                    try:    e_start = st.date_input("Start date", value=datetime.strptime(str(pl.get("start_date",""))[:10], "%Y-%m-%d").date())
                                    except: e_start = st.date_input("Start date", value=today)
                                    try:    e_end   = st.date_input("End date",   value=datetime.strptime(str(pl.get("end_date",""))[:10],   "%Y-%m-%d").date())
                                    except: e_end   = st.date_input("End date",   value=today)
                                    _cp_raw   = pl.get("contact_person","")
                                    _cp_name  = _cp_raw.split(" — ", 1)[0]
                                    e_contact = st.text_input("Contact person", value=_cp_name)
                                    e_phone   = st.text_input("Phone",          value=_stored_phone)
                                    _cp_parts = pl.get("contact_person","").split(" — ", 1)
                                    e_email   = st.text_input("Email", value=_cp_parts[1] if len(_cp_parts) > 1 else "")
                                e_support = st.text_area("Support arrangements", value=_stored_support, height=56)
                                e_goals   = st.text_area("Goals",               value=_stored_goals,   height=56)
                                e_notes   = st.text_area("Notes",               value=_stored_notes,   height=40)
                                if st.form_submit_button("💾 Save Changes", type="primary"):
                                    _upd_contact = e_contact.strip()
                                    if e_email.strip():
                                        _upd_contact = f"{_upd_contact} — {e_email.strip()}" if _upd_contact else e_email.strip()
                                    _upd_notes_parts = []
                                    if e_type:              _upd_notes_parts.append(f"Type: {e_type}")
                                    if e_fund:              _upd_notes_parts.append(f"Funding: {e_fund}")
                                    if e_phone.strip():     _upd_notes_parts.append(f"Phone: {e_phone.strip()}")
                                    if e_support.strip():   _upd_notes_parts.append(f"Support: {e_support.strip()}")
                                    if e_goals.strip():     _upd_notes_parts.append(f"Goals: {e_goals.strip()}")
                                    if e_notes.strip():     _upd_notes_parts.append(e_notes.strip())
                                    upd_placement(pid, {
                                        "student_initials": e_init.strip(),
                                        "program":          e_prog,
                                        "placement_school": e_school.strip(),
                                        "start_date":       str(e_start),
                                        "end_date":         str(e_end),
                                        "contact_person":   _upd_contact,
                                        "notes":            "\n".join(_upd_notes_parts),
                                    })
                                    st.session_state[ek] = False
                                    st.success("✅ Updated!")
                                    st.rerun()
                    with ec2:
                        dk = f"pl_del_{pid}"
                        if st.session_state.get(dk):
                            if st.button("✅ Confirm delete", key=f"pl_delc_{pid}", type="primary"):
                                del_placement(pid)
                                st.session_state[dk] = False
                                st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"pl_del_btn_{pid}"):
                                st.session_state[dk] = True
                                st.rerun()

    # ════ TRANSITION SCHEDULE ═══════════════════════════════════════════════════
    with st_trans:
        st.markdown(
            '<div style="background:#fefce8;border-left:4px solid #ca8a04;border-radius:8px;'
            'padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.84rem;color:#713f12;">'
            '🔄 Record each week a student attends their mainstream school during transition. '
            'Enter the days and times they are <b>at mainstream</b> — leave a day blank if they are at CLC all day. '
            'Transition weeks appear as solid bars on the Student Timeline.</div>', unsafe_allow_html=True)

        if not _cal_is_signed_in():
            st.info("🔐 **Sign in via the sidebar** to add or edit student records.", icon="ℹ️")
        else:
         with st.expander("➕ Add Transition Week", expanded=True):
            with st.form("trans_add_form", clear_on_submit=True):
                tr1, tr2, tr3 = st.columns(3)
                with tr1:
                    tr_init   = st.text_input("Student initials *", placeholder="e.g. J.S.", key="tr_init")
                    tr_prog   = st.selectbox("Program *", ["","JP","PY","SY"], key="tr_prog")
                with tr2:
                    tr_school = st.text_input("Mainstream school *", placeholder="e.g. Findon Primary", key="tr_school")
                    tr_label  = st.text_input("Week label", placeholder="e.g. Week 3 T2, Trial Week 1", key="tr_label")
                with tr3:
                    tr_wstart = st.date_input("Week starting (Monday) *",
                                              value=today - timedelta(days=today.weekday()), key="tr_wstart")
                    tr_notes  = st.text_input("Notes", placeholder="Optional", key="tr_notes_field")

                st.markdown("**Days at mainstream school** — enter the times for each day they attend:")
                th0, th1, th2, th3, th4, th5 = st.columns([1.5, 1, 1, 1, 1, 1])
                with th0: st.markdown("<div style='font-size:0.78rem;font-weight:700;padding-top:0.5rem;'>Day</div>", unsafe_allow_html=True)
                for h, day in zip([th1, th2, th3, th4, th5], DAYS):
                    with h: st.markdown(f"<div style='font-size:0.78rem;font-weight:700;text-align:center;padding-top:0.5rem;'>{day[:3]}</div>", unsafe_allow_html=True)

                times = {}
                for row_label, dkk in [("From", "start"), ("To", "end")]:
                    rc0, rc1, rc2, rc3, rc4, rc5 = st.columns([1.5, 1, 1, 1, 1, 1])
                    with rc0: st.markdown(f"<div style='font-size:0.78rem;padding-top:0.5rem;'>{row_label}</div>", unsafe_allow_html=True)
                    for col, dkey in zip([rc1, rc2, rc3, rc4, rc5], DAY_KEYS):
                        with col:
                            times[f"{dkey}_{dkk}"] = st.time_input(" ", value=None,
                                                                    key=f"tr_{dkey}_{dkk}",
                                                                    label_visibility="collapsed")

                if st.form_submit_button("✅ Save Transition Week", type="primary", use_container_width=True):
                    if not tr_init.strip():     st.warning("Student initials are required.")
                    elif not tr_prog:           st.warning("Please select a program.")
                    elif not tr_school.strip(): st.warning("Mainstream school is required.")
                    elif tr_wstart.weekday() != 0: st.warning("Week start date should be a Monday.")
                    else:
                        row = {
                            "student_initials":  tr_init.strip(),
                            "program":           tr_prog,
                            "mainstream_school": tr_school.strip(),
                            "week_label":        tr_label.strip(),
                            "week_start_date":   str(tr_wstart),
                            "notes":             tr_notes.strip(),
                        }
                        for dkey in DAY_KEYS:
                            row[f"{dkey}_start"] = str(times[f"{dkey}_start"]) if times.get(f"{dkey}_start") else None
                            row[f"{dkey}_end"]   = str(times[f"{dkey}_end"])   if times.get(f"{dkey}_end")   else None
                        save_transition(row)
                        st.success(f"✅ Transition week saved for {tr_init.strip()} — week of {fmt_date(tr_wstart)}!")
                        st.rerun()

        st.markdown("---")
        st.markdown("#### 🔄 Recorded Transition Weeks")

        tf1, tf2 = st.columns(2)
        with tf1: tf_prog = st.multiselect("Filter program", ["JP","PY","SY"], default=["JP","PY","SY"], key="tf_prog_trans")
        with tf2: tf_init = st.text_input("Filter by initials", placeholder="Leave blank for all", key="tf_init_trans")

        all_trs = db_transitions(tf_init.strip() if tf_init.strip() else None)
        if tf_prog != ["JP","PY","SY"]:
            all_trs = [t for t in all_trs if t.get("program","") in tf_prog]

        if not all_trs:
            st.markdown('<p style="color:#888;">No transition weeks found. Add one above.</p>', unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(all_trs)} transition week{'s' if len(all_trs)!=1 else ''} found**")

            by_student = defaultdict(list)
            for t in all_trs:
                by_student[t.get("student_initials","?")].append(t)

            for sinit, s_trs in by_student.items():
                prog = s_trs[0].get("program","")
                pc   = PROGRAM_COLORS.get(prog, {"color":"#374151","bg":"#f3f4f6"})
                st.markdown(
                    f'<div style="margin:0.75rem 0 0.25rem;">'
                    f'<span style="background:{pc["bg"]};color:{pc["color"]};font-size:0.7rem;font-weight:800;'
                    f'padding:0.12rem 0.4rem;border-radius:6px;margin-right:4px;">{prog}</span>'
                    f'<b style="color:{pc["color"]};font-size:0.9rem;">{sinit}</b> &nbsp;'
                    f'<span style="color:#888;font-size:0.8rem;">· {s_trs[0].get("mainstream_school","")} '
                    f'· {len(s_trs)} week{"s" if len(s_trs)!=1 else ""}</span></div>',
                    unsafe_allow_html=True)

                # Column header
                st.markdown(
                    "<div style='display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr;"
                    "gap:4px;font-size:0.72rem;font-weight:700;color:#555;"
                    "background:#f3f4f6;border-radius:6px;padding:0.35rem 0.5rem;margin-bottom:2px;'>"
                    "<div>Week</div><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div>"
                    "<div></div><div></div></div>",
                    unsafe_allow_html=True)

                for tr in s_trs:
                    tid = tr.get("id","")

                    def fmt_slot(dkey, _tr=tr):
                        s = _tr.get(f"{dkey}_start"); e = _tr.get(f"{dkey}_end")
                        if not s: return "<span style='color:#ccc;'>—</span>"
                        return f"<span style='font-size:0.68rem;'>{fmt_time_short(s)}<br>{fmt_time_short(e)}</span>"

                    wlbl = tr.get("week_label","") or fmt_date(tr.get("week_start_date",""))
                    st.markdown(
                        "<div style='display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr;"
                        "gap:4px;font-size:0.76rem;align-items:center;"
                        "border-bottom:1px solid #f0f0f0;padding:0.3rem 0.5rem;'>"
                        f"<div><b style='font-size:0.78rem;'>{wlbl}</b>"
                        f"{'<br><span style=color:#aaa;font-size:0.66rem;>'+tr.get('notes','')+'</span>' if tr.get('notes') else ''}"
                        f"</div>"
                        f"<div>{fmt_slot('mon')}</div><div>{fmt_slot('tue')}</div>"
                        f"<div>{fmt_slot('wed')}</div><div>{fmt_slot('thu')}</div>"
                        f"<div>{fmt_slot('fri')}</div>"
                        f"<div></div><div></div></div>",
                        unsafe_allow_html=True)

                    ek = f"tr_edit_{tid}"
                    bt1, bt2, bt3 = st.columns([1, 1, 8])
                    with bt1:
                        if st.button("✏️", key=f"tr_ed_{tid}", help="Edit this week"):
                            st.session_state[ek] = not st.session_state.get(ek, False)
                            st.rerun()
                    with bt2:
                        dk2 = f"tr_del_{tid}"
                        if st.session_state.get(dk2):
                            if st.button("✅", key=f"tr_delc_{tid}", help="Confirm delete", type="primary"):
                                del_transition(tid)
                                st.session_state[dk2] = False
                                st.rerun()
                        else:
                            if st.button("🗑️", key=f"tr_del_btn_{tid}", help="Delete"):
                                st.session_state[dk2] = True
                                st.rerun()

                    if st.session_state.get(ek):
                        with st.form(f"tr_ef_{tid}", clear_on_submit=False):
                            e1, e2, e3 = st.columns(3)
                            with e1:
                                ei = st.text_input("Student initials", value=tr.get("student_initials",""))
                                ep = st.selectbox("Program", ["","JP","PY","SY"],
                                                  index=["","JP","PY","SY"].index(tr.get("program",""))
                                                  if tr.get("program","") in ["","JP","PY","SY"] else 0)
                            with e2:
                                es  = st.text_input("Mainstream school", value=tr.get("mainstream_school",""))
                                el  = st.text_input("Week label", value=tr.get("week_label",""))
                            with e3:
                                try:    ews = st.date_input("Week start (Mon)", value=datetime.strptime(str(tr.get("week_start_date",""))[:10], "%Y-%m-%d").date())
                                except: ews = st.date_input("Week start (Mon)", value=today - timedelta(days=today.weekday()))
                                en  = st.text_input("Notes", value=tr.get("notes",""))

                            st.markdown("**Times at mainstream:**")
                            eth0, eth1, eth2, eth3, eth4, eth5 = st.columns([1.5, 1, 1, 1, 1, 1])
                            with eth0: st.markdown("<div style='font-size:0.76rem;font-weight:700;'>Day</div>", unsafe_allow_html=True)
                            for h, day in zip([eth1, eth2, eth3, eth4, eth5], DAYS):
                                with h: st.markdown(f"<div style='font-size:0.76rem;font-weight:700;text-align:center;'>{day[:3]}</div>", unsafe_allow_html=True)

                            etimes = {}
                            for row_label, dkk in [("From","start"),("To","end")]:
                                er0, er1, er2, er3, er4, er5 = st.columns([1.5, 1, 1, 1, 1, 1])
                                with er0: st.markdown(f"<div style='font-size:0.76rem;'>{row_label}</div>", unsafe_allow_html=True)
                                for col, dkey in zip([er1, er2, er3, er4, er5], DAY_KEYS):
                                    existing_time = None
                                    raw = tr.get(f"{dkey}_{dkk}")
                                    if raw:
                                        try: existing_time = datetime.strptime(str(raw)[:5], "%H:%M").time()
                                        except: pass
                                    with col:
                                        etimes[f"{dkey}_{dkk}"] = st.time_input(
                                            " ", value=existing_time,
                                            key=f"tref_{tid}_{dkey}_{dkk}",
                                            label_visibility="collapsed")

                            if st.form_submit_button("💾 Save Changes", type="primary"):
                                upd_row = {
                                    "student_initials":  ei.strip(),
                                    "program":           ep,
                                    "mainstream_school": es.strip(),
                                    "week_label":        el.strip(),
                                    "week_start_date":   str(ews),
                                    "notes":             en.strip(),
                                }
                                for dkey in DAY_KEYS:
                                    upd_row[f"{dkey}_start"] = str(etimes[f"{dkey}_start"]) if etimes.get(f"{dkey}_start") else None
                                    upd_row[f"{dkey}_end"]   = str(etimes[f"{dkey}_end"])   if etimes.get(f"{dkey}_end")   else None
                                upd_transition(tid, upd_row)
                                st.session_state[ek] = False
                                st.success("✅ Updated!")
                                st.rerun()

    # ════ STUDENT MEETINGS ══════════════════════════════════════════════════════
    with st_mtg:
        st.markdown(
            '<div style="background:#f0fdf4;border-left:4px solid #15803d;border-radius:8px;'
            'padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.84rem;color:#14532d;">'
            '📅 Meetings logged here <b>automatically appear in the main calendar</b> on the correct date. '
            'Use the calendar\'s Entry / Review / Transition / TAC filter to view them.'
            '</div>', unsafe_allow_html=True)

        if not _cal_is_signed_in():
            st.info("🔐 **Sign in via the sidebar** to add or edit student records.", icon="ℹ️")
        else:
         with st.expander("➕ Log a Student Meeting", expanded=True):
            _show_save_notification()
            with st.form("mtg_add_form", clear_on_submit=True):
                mg1, mg2 = st.columns(2)
                with mg1:
                    mtg_type  = st.selectbox("Meeting type *", STUDENT_MEETING_TYPES)
                    mtg_init  = st.text_input("Student initials *", placeholder="e.g. J.S.")
                    mtg_prog  = st.selectbox("Program *", ["","JP","PY","SY"], key="mtg_prog")
                    mtg_by    = st.text_input("Added by *", value=get_staff_name())
                with mg2:
                    mtg_date  = st.date_input("Meeting date *", value=today, key="mtg_date")
                    mtg_start = st.time_input("Start time", value=None, key="mtg_start")
                    mtg_end   = st.time_input("End time",   value=None, key="mtg_end")
                    mtg_loc   = st.text_input("Location", placeholder="e.g. CLC Meeting Room")
                mtg_attend = st.text_input("Attendees", placeholder="e.g. Teacher, Parent, Support Worker")
                mtg_notes  = st.text_area("Meeting notes / outcomes", height=80)

                if st.form_submit_button("✅ Save Meeting — auto-syncs to Calendar", type="primary", use_container_width=True):
                    if not mtg_init.strip():  st.warning("Please enter student initials.")
                    elif not mtg_prog:        st.warning("Please select a program.")
                    elif not mtg_by.strip():  st.warning("Please enter your name.")
                    else:
                        full_notes = "\n".join(filter(None, [
                            f"Attendees: {mtg_attend.strip()}" if mtg_attend.strip() else "",
                            mtg_notes.strip()
                        ]))
                        evt = dict(
                            title=f"{mtg_init.strip()} — {mtg_type}",
                            etype=mtg_type, ev_date=mtg_date, end_date=mtg_date,
                            start_t=mtg_start, end_t=mtg_end, location=mtg_loc.strip(),
                            who=mtg_by.strip(), notes=full_notes,
                            program=mtg_prog, student_initials=mtg_init.strip()
                        )
                        if save_event(evt):
                            # Override generic save message with a meeting-specific one
                            st.session_state["_cal_save_ok"] = f"✅ {mtg_type} logged for {mtg_init.strip()} on {fmt_date(mtg_date)} — now visible in calendar!"
                            st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Recent Student Meetings")

        mf1, mf2, mf3 = st.columns(3)
        with mf1: mf_prog = st.multiselect("Program", ["JP","PY","SY"], default=["JP","PY","SY"], key="mf_prog")
        with mf2: mf_type = st.multiselect("Meeting type", STUDENT_MEETING_TYPES, default=STUDENT_MEETING_TYPES, key="mf_type")
        with mf3: mf_from = st.date_input("From", value=today-timedelta(weeks=12), key="mf_from")

        all_mtgs = [e for e in db_events(mf_from, today+timedelta(weeks=52))
                    if e.get("event_type") in STUDENT_MEETING_TYPES]
        if mf_prog != ["JP","PY","SY"]:     all_mtgs = [e for e in all_mtgs if e.get("program","") in mf_prog]
        if mf_type != STUDENT_MEETING_TYPES: all_mtgs = [e for e in all_mtgs if e.get("event_type") in mf_type]
        all_mtgs.sort(key=lambda x: str(x.get("event_date","")), reverse=True)

        if not all_mtgs:
            st.markdown('<p style="color:#888;">No student meetings found. Log one above.</p>', unsafe_allow_html=True)
        else:
            mtgs_text = "meetings" if len(all_mtgs) != 1 else "meeting"
            st.markdown(f"**{len(all_mtgs)} {mtgs_text} found**")
            for ev in all_mtgs:
                render_event_row(ev, "stmtg")

# ═══════════════ WEEK OVERVIEW (PRINT) ════════════════════════════════════════
with tab_weekoverview:
    st.markdown("### 🖨️ Week Overview")

    # ── Week selector ──────────────────────────────────────────────────────────
    ov_col1, ov_col2, ov_col3 = st.columns([1, 2, 1])
    with ov_col1:
        if st.button("◀ Prev week", key="ov_prev", use_container_width=True):
            st.session_state["ov_week_start"] = st.session_state.get("ov_week_start", today - timedelta(days=today.weekday())) - timedelta(weeks=1)
            st.rerun()
    with ov_col3:
        if st.button("Next week ▶", key="ov_next", use_container_width=True):
            st.session_state["ov_week_start"] = st.session_state.get("ov_week_start", today - timedelta(days=today.weekday())) + timedelta(weeks=1)
            st.rerun()
    with ov_col2:
        if st.button("📅 This week", key="ov_this", use_container_width=True):
            st.session_state["ov_week_start"] = today - timedelta(days=today.weekday())
            st.rerun()

    ov_start = st.session_state.get("ov_week_start", today - timedelta(days=today.weekday()))
    ov_end   = ov_start + timedelta(days=4)   # Mon–Fri
    week_label = f"Week of {ov_start.strftime('%-d %B')} – {ov_end.strftime('%-d %B %Y')}"
    st.markdown(f"<h4 style='text-align:center;color:#1A7A7A;margin:0.25rem 0 1rem;'>{week_label}</h4>", unsafe_allow_html=True)

    # ── Fetch data for the week ────────────────────────────────────────────────
    ov_events    = db_events(ov_start, ov_end) + schedule_events(ov_start, ov_end)
    ov_index     = ev_index(ov_events)
    ov_days      = [ov_start + timedelta(days=i) for i in range(5)]

    # ── Build HTML for screen + print ─────────────────────────────────────────
    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    def ov_event_html(ev):
        et   = ev.get("event_type", "Other")
        cfg  = EVENT_TYPES.get(et, EVENT_TYPES["Other"])
        emoji = cfg["emoji"]
        color = cfg["color"]
        bg    = cfg["bg"]
        title = ev.get("title", et)
        loc   = ev.get("location", "")
        st_t  = ev.get("start_time", "")
        en_t  = ev.get("end_time", "")
        who   = ev.get("added_by", "")
        prog  = ev.get("program", "")
        time_str = ""
        if st_t:
            try:    time_str = datetime.strptime(str(st_t)[:5], "%H:%M").strftime("%-I:%M %p")
            except: time_str = str(st_t)[:5]
        if en_t:
            try:    time_str += f" – {datetime.strptime(str(en_t)[:5], '%H:%M').strftime('%-I:%M %p')}"
            except: pass
        meta_parts = [p for p in [time_str, loc, prog] if p]
        meta = " &nbsp;·&nbsp; ".join(meta_parts)
        return (
            f'<div style="background:{bg};border-left:3px solid {color};border-radius:5px;'
            f'padding:4px 8px;margin:3px 0;font-size:0.82rem;">'
            f'<span style="color:{color};font-weight:600;">{emoji} {title}</span>'
            + (f'<br><span style="color:#555;font-size:0.75rem;">{meta}</span>' if meta else '')
            + f'</div>'
        )

    # Build the HTML overview table
    html_rows = ""
    any_events = False
    for d, dname in zip(ov_days, DAY_NAMES):
        day_evs = ov_index.get(str(d), [])
        is_today = (d == today)
        bg_hdr = "#1A7A7A" if is_today else "#2d3748"
        event_html = "".join(ov_event_html(e) for e in day_evs) if day_evs else '<span style="color:#aaa;font-size:0.8rem;font-style:italic;">No events</span>'
        if day_evs:
            any_events = True
        html_rows += (
            f'<tr>'
            f'<td style="background:{bg_hdr};color:white;font-weight:700;font-size:0.85rem;'
            f'padding:8px 12px;vertical-align:top;white-space:nowrap;border-bottom:1px solid #e2e8f0;">'
            f'{dname}<br><span style="font-weight:400;font-size:0.75rem;opacity:0.85;">{d.strftime("%-d %b")}</span></td>'
            f'<td style="padding:6px 10px;vertical-align:top;border-bottom:1px solid #e2e8f0;">{event_html}</td>'
            f'</tr>'
        )

    overview_html = f"""
<style>
@media print {{
  body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .no-print {{ display: none !important; }}
  .print-container {{ font-family: Arial, sans-serif; }}
}}
</style>
<div class="print-container" id="weekOverviewBlock" style="font-family:Arial,sans-serif;max-width:860px;margin:0 auto;">
  <div style="text-align:center;padding:12px 0 8px;">
    <div style="font-size:1.1rem;font-weight:700;color:#1A7A7A;">Cowandilla Learning Centre</div>
    <div style="font-size:0.95rem;font-weight:600;color:#2d3748;">{week_label}</div>
    <div style="font-size:0.72rem;color:#888;margin-top:2px;">Generated {today.strftime('%-d %B %Y')}</div>
  </div>
  <table style="width:100%;border-collapse:collapse;border:1px solid #cbd5e0;border-radius:8px;overflow:hidden;">
    <thead>
      <tr style="background:#f7fafc;">
        <th style="width:120px;padding:8px 12px;text-align:left;font-size:0.8rem;color:#555;border-bottom:2px solid #1A7A7A;">Day</th>
        <th style="padding:8px 12px;text-align:left;font-size:0.8rem;color:#555;border-bottom:2px solid #1A7A7A;">Events &amp; Activities</th>
      </tr>
    </thead>
    <tbody>{html_rows}</tbody>
  </table>
  <div style="text-align:center;font-size:0.7rem;color:#aaa;padding:8px 0 4px;">
    CLC Staff Portal · Calendar · Printed {today.strftime('%-d %B %Y')}
  </div>
</div>
"""
    st.markdown(overview_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── Download button ────────────────────────────────────────────────────────
    printable_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CLC Week Overview – {week_label}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; padding: 24px; color: #1a202c; }}
  h1 {{ font-size: 1.2rem; color: #1A7A7A; text-align: center; margin-bottom: 2px; }}
  h2 {{ font-size: 1rem; text-align: center; color: #2d3748; margin-bottom: 4px; }}
  .meta {{ text-align: center; font-size: 0.72rem; color: #888; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; border: 1px solid #cbd5e0; }}
  thead th {{ background: #f7fafc; padding: 8px 12px; text-align: left; font-size: 0.8rem; color: #555; border-bottom: 2px solid #1A7A7A; }}
  td {{ padding: 6px 10px; vertical-align: top; border-bottom: 1px solid #e2e8f0; font-size: 0.82rem; }}
  td.day-col {{ background: #2d3748; color: white; font-weight: 700; font-size: 0.85rem; white-space: nowrap; width: 120px; }}
  td.day-col.today {{ background: #1A7A7A; }}
  td.day-col span {{ font-weight: 400; font-size: 0.75rem; opacity: 0.85; display: block; }}
  .ev {{ border-radius: 4px; padding: 3px 7px; margin: 2px 0; border-left: 3px solid; }}
  .ev-title {{ font-weight: 600; }}
  .ev-meta {{ font-size: 0.72rem; color: #555; }}
  .none {{ color: #aaa; font-style: italic; font-size: 0.78rem; }}
  footer {{ text-align: center; font-size: 0.68rem; color: #aaa; padding: 10px 0 0; }}
  @media print {{
    body {{ padding: 12px; }}
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
</style>
</head>
<body>
<h1>Cowandilla Learning Centre</h1>
<h2>{week_label}</h2>
<p class="meta">Generated {today.strftime('%-d %B %Y')}</p>
<table>
<thead><tr><th>Day</th><th>Events &amp; Activities</th></tr></thead>
<tbody>
"""
    for d, dname in zip(ov_days, DAY_NAMES):
        day_evs = ov_index.get(str(d), [])
        is_today_cls = " today" if d == today else ""
        rows_html = ""
        if day_evs:
            for ev in day_evs:
                et   = ev.get("event_type", "Other")
                cfg  = EVENT_TYPES.get(et, EVENT_TYPES["Other"])
                title = ev.get("title", et)
                loc   = ev.get("location", "")
                st_t  = ev.get("start_time", "")
                en_t  = ev.get("end_time", "")
                prog  = ev.get("program", "")
                time_str = ""
                if st_t:
                    try:    time_str = datetime.strptime(str(st_t)[:5], "%H:%M").strftime("%-I:%M %p")
                    except: time_str = str(st_t)[:5]
                if en_t:
                    try:    time_str += f" – {datetime.strptime(str(en_t)[:5], '%H:%M').strftime('%-I:%M %p')}"
                    except: pass
                meta_parts = [p for p in [time_str, loc, prog] if p]
                meta = " · ".join(meta_parts)
                rows_html += (
                    f'<div class="ev" style="background:{cfg["bg"]};border-color:{cfg["color"]};">'
                    f'<span class="ev-title" style="color:{cfg["color"]};">{cfg["emoji"]} {title}</span>'
                    + (f'<div class="ev-meta">{meta}</div>' if meta else '')
                    + '</div>'
                )
        else:
            rows_html = '<span class="none">No events</span>'
        printable_html += (
            f'<tr>'
            f'<td class="day-col{is_today_cls}">{dname}<span>{d.strftime("%-d %b")}</span></td>'
            f'<td>{rows_html}</td>'
            f'</tr>\n'
        )

    printable_html += f"""</tbody>
</table>
<footer>CLC Staff Portal · Calendar · {today.strftime('%-d %B %Y')}</footer>
</body>
</html>"""

    safe_label = week_label.replace(" ", "_").replace("–", "-")
    st.download_button(
        label="⬇️ Download printable HTML (open in browser → Print / Save as PDF)",
        data=printable_html.encode("utf-8"),
        file_name=f"CLC_Week_Overview_{safe_label}.html",
        mime="text/html",
        use_container_width=True,
        type="primary",
    )
    st.caption("💡 Tip: Open the downloaded file in Chrome or Edge, then use Ctrl+P (or ⌘P on Mac) → Save as PDF for a clean printout.")

# ─── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;color:#aaa;font-size:0.76rem;">
Cowandilla Learning Centre · Communal Staff Calendar · Student meetings auto-sync to calendar
</div>""", unsafe_allow_html=True)
