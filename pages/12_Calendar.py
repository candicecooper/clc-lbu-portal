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

from auth import require_auth, logout_button, get_staff_name
require_auth("CLC Calendar", "📅")
logout_button("sidebar")

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

DAYS    = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
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
    ("is_admin",          True),
    ("edit_event_id",     None),
    ("selected_event_id", None),
    ("quick_add_open",    False),
]:
    if k not in st.session_state:
        st.session_state[k] = v

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

# ── Student placements table ──────────────────────────────────────────────────
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
        st.success(f"✅ Event saved for {d['ev_date'].strftime('%-d %B %Y')}!")
        return True
    except Exception as e:
        st.error(f"❌ Could not save event: {e}"); return False

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
            try:    date_val = datetime.strptime(str(ev.get("event_date", d0))[:10], "%Y-%m-%d").date()
            except: date_val = d0
            ev_date  = st.date_input("Date *", value=date_val)
            end_date = st.date_input("End date (same for single day)", value=ev_date)
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
        with c3: start_t = st.time_input("Start time (optional)", value=None)
        with c4: end_t   = st.time_input("End time (optional)",   value=None)
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
    """Return (color, bg, cfg) for an event."""
    cfg  = EVENT_TYPES.get(ev.get("event_type","Other"), EVENT_TYPES["Other"])
    prog = ev.get("program","")
    if prog and ev.get("event_type") in STUDENT_EVENT_TYPES:
        pc   = PROGRAM_COLORS.get(prog, {})
        col  = pc.get("color", cfg["color"]); bg = pc.get("bg", cfg["bg"])
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
    """Render event card + expand / edit / delete controls."""
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
                st.session_state.edit_event_id = eid if st.session_state.edit_event_id != eid else None
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
        ok, data = event_form(f"{key_prefix}_ef_{eid}", existing=ev, label="💾 Save Changes")
        if ok:
            upd_event(eid, data)
            st.session_state.edit_event_id = None
            st.success("✅ Updated!")
            st.rerun()

# ─── DAY CELL HTML (month + week) ────────────────────────────────────────────────
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
        # FIX: update selected_date so day panel matches navigated month
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

tab_month, tab_week, tab_list, tab_students = st.tabs(["📅 Month", "📆 Week", "📋 List", "👤 Students"])

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

    # ── Day panel ──
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
    ok, data = event_form(f"madd_{sel.year}_{sel.month}_{sel.day}", default_date=sel)
    if ok:
        if save_event(data):
            st.session_state.cal_year  = sel.year
            st.session_state.cal_month = sel.month
            st.rerun()

# ═══════════════ WEEK VIEW ═════════════════════════════════════════════════════
with tab_week:
    ws = st.session_state.cal_week_start
    we = ws + timedelta(days=6)
    wp, wt, wn, wtod = st.columns([1, 3, 1, 1])
    with wp:
        if st.button("◀ Prev", use_container_width=True, key="w_prev"):
            st.session_state.cal_week_start -= timedelta(weeks=1)
            # FIX: move selected_date to Monday of new week
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
            if isel:    lbl = "✅ Selected"; bg_b = "#1a2e44"; col_b = "white"
            elif itod:  lbl = f"📍 {n} event{'s' if n!=1 else ''}" if n else "📍 Today"; bg_b = "#d4af37"; col_b = "white"
            elif n:     lbl = f"👁 {n} event{'s' if n!=1 else ''}"; bg_b = "#2d4a6e"; col_b = "white"
            else:       lbl = "➕ Add"; bg_b = "#6b7280"; col_b = "white"
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
    with st.expander(f"➕ Add event on {sel.strftime('%-d %B')}", expanded=(not d_evs and sel != today)):
        ok, data = event_form(f"wadd_{str(sel)}", default_date=sel)
        if ok: save_event(data); st.rerun()

# ═══════════════ LIST / AGENDA VIEW ═══════════════════════════════════════════
with tab_list:
    lc1, lc2, lc3 = st.columns(3)
    with lc1: ls = st.date_input("From", value=today, key="ls")
    with lc2: le = st.date_input("To",   value=today+timedelta(weeks=8), key="le")
    with lc3: tf = st.multiselect("Filter type", list(EVENT_TYPES.keys()), default=list(EVENT_TYPES.keys()), key="tf")

    with st.expander("➕ Add New Event"):
        ok, data = event_form("ladd")
        if ok: save_event(data); st.rerun()

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

# ═══════════════ STUDENTS VIEW ════════════════════════════════════════════════
with tab_students:
    st.markdown("### 👨‍🎓 Student Placements & Meetings")
    st_place, st_trans, st_mtg = st.tabs(["📋 Placement Details", "🔄 Transition Schedule", "📅 Student Meetings"])

    # ════ PLACEMENT DETAILS ════════════════════════════════════════════════════
    with st_place:
        st.markdown(
            '<div style="background:#f0f9ff;border-left:4px solid #0e7490;border-radius:8px;'
            'padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.84rem;color:#0e4a5e;">'
            '📋 Record full placement details here — school, support arrangements, funding, goals and contacts. '
            'Student <b>meetings</b> are logged in the Student Meetings tab and auto-sync to the calendar.<br><br>'
            '<b>Run this SQL in Supabase if table doesn\'t exist yet:</b><br>'
            '<code style="font-size:0.72rem;">create table student_placements (id uuid primary key default gen_random_uuid(), '
            'student_initials text not null, program text not null, placement_type text, placement_school text, '
            'placement_location text, start_date date, end_date date, days_attending text, arrival_time time, '
            'departure_time time, support_worker text, funding_type text, contact_person text, contact_phone text, '
            'goals text, notes text, added_by text, created_at timestamptz default now()); '
            'alter table student_placements enable row level security; '
            'create policy "Allow all" on student_placements for all using (true) with check (true);</code>'
            '</div>', unsafe_allow_html=True)

        # Filters
        pf1, pf2 = st.columns(2)
        with pf1: pl_prog    = st.multiselect("Program", ["JP","PY","SY"], default=["JP","PY","SY"], key="pl_prog")
        with pf2:
            all_pl   = db_placements()
            pl_inits = sorted(set(p.get("student_initials","") for p in all_pl if p.get("student_initials")))
            pl_stu   = st.selectbox("Filter by student", ["All"] + pl_inits, key="pl_stu")

        with st.expander("➕ Add Placement Details"):
            with st.form("pl_add_form", clear_on_submit=True):
                pa1, pa2 = st.columns(2)
                with pa1:
                    pl_init    = st.text_input("Student initials *", placeholder="e.g. J.S.")
                    pl_prog_s  = st.selectbox("Program *", ["","JP","PY","SY"], key="pl_prog_sel")
                    pl_type    = st.selectbox("Placement type", PLACEMENT_TYPES)
                    pl_school  = st.text_input("Placement school / site", placeholder="e.g. Cowandilla Primary School")
                    pl_loc     = st.text_input("Suburb / address", placeholder="e.g. Cowandilla SA 5033")
                    pl_by      = st.text_input("Added by *", value=get_staff_name())
                with pa2:
                    pl_start   = st.date_input("Start date *", value=today, key="pl_start")
                    pl_end     = st.date_input("End date",     value=today+timedelta(weeks=10), key="pl_end")
                    pl_days    = st.multiselect("Days attending", DAYS, default=DAYS, key="pl_days")
                    pla1, pla2 = st.columns(2)
                    with pla1: pl_arrive = st.time_input("Arrival time",   value=None, key="pl_arr")
                    with pla2: pl_depart = st.time_input("Departure time", value=None, key="pl_dep")
                    pl_worker  = st.text_input("Support worker / LSO", placeholder="Name of support person")
                    pl_fund    = st.selectbox("Funding type", FUNDING_TYPES)
                    pl_contact = st.text_input("Site contact person", placeholder="e.g. Mrs Smith (Deputy)")
                    pl_phone   = st.text_input("Contact phone", placeholder="e.g. 08 8234 XXXX")

                pl_goals = st.text_area("Placement goals / objectives", height=80,
                                        placeholder="e.g. Build peer relationships, develop independence in reading tasks...")
                pl_notes = st.text_area("Additional notes / context", height=60)

                if st.form_submit_button("✅ Save Placement Details", type="primary", use_container_width=True):
                    if not pl_init.strip():   st.warning("Please enter student initials.")
                    elif not pl_prog_s:       st.warning("Please select a program.")
                    elif not pl_by.strip():   st.warning("Please enter your name.")
                    else:
                        try:
                            save_placement({
                                "student_initials": pl_init.strip(), "program": pl_prog_s,
                                "placement_type":   pl_type, "placement_school": pl_school.strip(),
                                "placement_location": pl_loc.strip(),
                                "start_date":       str(pl_start), "end_date": str(pl_end),
                                "days_attending":   ", ".join(pl_days),
                                "arrival_time":     str(pl_arrive) if pl_arrive else None,
                                "departure_time":   str(pl_depart) if pl_depart else None,
                                "support_worker":   pl_worker.strip(), "funding_type": pl_fund,
                                "contact_person":   pl_contact.strip(), "contact_phone": pl_phone.strip(),
                                "goals":            pl_goals.strip(), "notes": pl_notes.strip(),
                                "added_by":         pl_by.strip(),
                            })
                            st.success(f"✅ Placement saved for {pl_init.strip()}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Could not save: {e}")

        st.markdown("---")

        disp_pl = db_placements(initials=None if pl_stu == "All" else pl_stu)
        if pl_prog != ["JP","PY","SY"]:
            disp_pl = [p for p in disp_pl if p.get("program","") in pl_prog]

        if not disp_pl:
            st.markdown('<p style="color:#888;">No placement records found. Add one above.</p>', unsafe_allow_html=True)
        else:
            by_stu = defaultdict(list)
            for p in disp_pl: by_stu[p.get("student_initials","?")].append(p)

            for init, records in by_stu.items():
                prog = records[0].get("program","")
                pc   = PROGRAM_COLORS.get(prog, {"color":"#374151","bg":"#f3f4f6"})
                st.markdown(
                    f'<div style="background:{pc["bg"]};border-left:4px solid {pc["color"]};border-radius:10px;'
                    f'padding:0.6rem 1rem;margin:1rem 0 0.5rem;display:flex;align-items:center;gap:0.75rem;">'
                    f'<span style="background:{pc["color"]};color:white;font-size:0.75rem;font-weight:700;'
                    f'padding:0.2rem 0.55rem;border-radius:8px;">{prog}</span>'
                    f'<strong style="font-size:1rem;color:{pc["color"]};">📋 {init}</strong>'
                    f'</div>', unsafe_allow_html=True)

                for p in records:
                    pid      = p.get("id","")
                    time_str = ""
                    arr = fmt_time(p.get("arrival_time","")); dep = fmt_time(p.get("departure_time",""))
                    if arr and dep: time_str = f"{arr} – {dep}"
                    elif arr:       time_str = arr

                    st.markdown(
                        f'<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;'
                        f'padding:0.9rem 1.1rem;margin-bottom:0.75rem;">'
                        f'<div style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:center;margin-bottom:0.6rem;">'
                        f'<span style="background:#1a2e4a;color:white;font-size:0.75rem;font-weight:700;'
                        f'padding:0.2rem 0.6rem;border-radius:8px;">{p.get("placement_type","Placement")}</span>'
                        f'<strong style="color:#1a2e4a;font-size:0.95rem;">{p.get("placement_school","—")}</strong>'
                        f'{"<span style=color:#888;font-size:0.8rem;> · "+p["placement_location"]+"</span>" if p.get("placement_location") else ""}'
                        f'</div>'
                        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;font-size:0.82rem;color:#374151;">'
                        f'<div>📅 <b>Start:</b> {fmt_date(p.get("start_date",""))}</div>'
                        f'<div>📅 <b>End:</b> {fmt_date(p.get("end_date",""))}</div>'
                        f'<div>📆 <b>Days:</b> {p.get("days_attending","—")}</div>'
                        f'{"<div>⏰ <b>Times:</b> "+time_str+"</div>" if time_str else "<div></div>"}'
                        f'{"<div>🧑 <b>Support:</b> "+p["support_worker"]+"</div>" if p.get("support_worker") else "<div></div>"}'
                        f'{"<div>💰 <b>Funding:</b> "+p["funding_type"]+"</div>" if p.get("funding_type") else "<div></div>"}'
                        f'{"<div>📞 <b>Contact:</b> "+p["contact_person"]+(": "+p["contact_phone"] if p.get("contact_phone") else "")+"</div>" if p.get("contact_person") else "<div></div>"}'
                        f'</div>'
                        f'{"<div style=margin-top:0.5rem;font-size:0.82rem;color:#065f46;><b>🎯 Goals:</b> "+p["goals"]+"</div>" if p.get("goals") else ""}'
                        f'{"<div style=margin-top:0.4rem;font-size:0.8rem;color:#666;>📝 "+p["notes"]+"</div>" if p.get("notes") else ""}'
                        f'<div style="font-size:0.73rem;color:#aaa;margin-top:0.4rem;">Added by {p.get("added_by","")}</div>'
                        f'</div>', unsafe_allow_html=True)

                    if st.session_state.is_admin:
                        xc1, xc2 = st.columns([1,1])
                        with xc1:
                            if st.button("✏️ Edit", key=f"pl_ed_{pid}"):
                                st.session_state.edit_event_id = pid if st.session_state.edit_event_id != pid else None
                                st.rerun()
                        with xc2:
                            if st.button("🗑️ Delete", key=f"pl_del_{pid}"):
                                del_placement(pid); st.rerun()

                    # Edit form for placement
                    if st.session_state.edit_event_id == pid:
                        with st.form(f"pl_ef_{pid}", clear_on_submit=False):
                            ep1, ep2 = st.columns(2)
                            with ep1:
                                e_init   = st.text_input("Student initials *", value=p.get("student_initials",""))
                                po       = ["","JP","PY","SY"]
                                e_prog   = st.selectbox("Program *", po, index=po.index(p.get("program","")) if p.get("program","") in po else 0)
                                e_type   = st.selectbox("Placement type", PLACEMENT_TYPES,
                                                        index=PLACEMENT_TYPES.index(p.get("placement_type","")) if p.get("placement_type","") in PLACEMENT_TYPES else 0)
                                e_school = st.text_input("School / site", value=p.get("placement_school",""))
                                e_loc    = st.text_input("Location", value=p.get("placement_location",""))
                                e_by     = st.text_input("Added by *", value=p.get("added_by",""))
                            with ep2:
                                try:    e_start = st.date_input("Start date *", value=datetime.strptime(str(p.get("start_date",""))[:10],"%Y-%m-%d").date(), key=f"pl_es_{pid}")
                                except: e_start = st.date_input("Start date *", value=today, key=f"pl_es_{pid}")
                                try:    e_end   = st.date_input("End date",     value=datetime.strptime(str(p.get("end_date",""))[:10],"%Y-%m-%d").date(), key=f"pl_ee_{pid}")
                                except: e_end   = st.date_input("End date",     value=today+timedelta(weeks=10), key=f"pl_ee_{pid}")
                                e_days   = st.multiselect("Days", DAYS, default=[d for d in (p.get("days_attending","") or "").split(", ") if d in DAYS], key=f"pl_ed_{pid}")
                                ea1, ea2 = st.columns(2)
                                with ea1: e_arr = st.time_input("Arrival",   value=None, key=f"pl_ea_{pid}")
                                with ea2: e_dep = st.time_input("Departure", value=None, key=f"pl_edep_{pid}")
                                e_worker  = st.text_input("Support worker", value=p.get("support_worker",""))
                                e_fund    = st.selectbox("Funding", FUNDING_TYPES, index=FUNDING_TYPES.index(p.get("funding_type","")) if p.get("funding_type","") in FUNDING_TYPES else 0)
                                e_contact = st.text_input("Contact person", value=p.get("contact_person",""))
                                e_phone   = st.text_input("Contact phone",  value=p.get("contact_phone",""))
                            e_goals = st.text_area("Goals", value=p.get("goals",""), height=70)
                            e_notes = st.text_area("Notes", value=p.get("notes",""), height=50)
                            if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                                upd_placement(pid, {
                                    "student_initials": e_init.strip(), "program": e_prog,
                                    "placement_type":   e_type, "placement_school": e_school.strip(),
                                    "placement_location": e_loc.strip(),
                                    "start_date": str(e_start), "end_date": str(e_end),
                                    "days_attending": ", ".join(e_days),
                                    "arrival_time": str(e_arr) if e_arr else None,
                                    "departure_time": str(e_dep) if e_dep else None,
                                    "support_worker": e_worker.strip(), "funding_type": e_fund,
                                    "contact_person": e_contact.strip(), "contact_phone": e_phone.strip(),
                                    "goals": e_goals.strip(), "notes": e_notes.strip(),
                                    "added_by": e_by.strip(),
                                })
                                st.session_state.edit_event_id = None
                                st.success("✅ Updated!"); st.rerun()

    # ════ TRANSITION SCHEDULE ══════════════════════════════════════════════════
    with st_trans:
        tr1, tr2, tr3 = st.columns(3)
        with tr1: tr_prog = st.multiselect("Program", ["JP","PY","SY"], default=["JP","PY","SY"], key="tr_prog")
        with tr2:
            all_trans = db_transitions()
            all_inits = sorted(set(t.get("student_initials","") for t in all_trans if t.get("student_initials")))
            tr_student = st.selectbox("Filter by student", ["All"]+all_inits, key="tr_student")
        with tr3:
            tr_term = st.selectbox("Filter by term", ["All","Term 1","Term 2","Term 3","Term 4"], key="tr_term")

        with st.expander("➕ Add Transition Week"):
            with st.form("tr_add_form", clear_on_submit=True):
                tf1, tf2 = st.columns(2)
                with tf1:
                    tr_initials  = st.text_input("Student initials *", placeholder="e.g. J.S.")
                    tr_program_s = st.selectbox("Program *", ["","JP","PY","SY"], key="tr_prog_add")
                    tr_school    = st.text_input("Mainstream school", placeholder="e.g. Cowandilla Primary")
                    tr_added_by  = st.text_input("Added by *", placeholder="Your name")
                with tf2:
                    tr_term_val  = st.selectbox("Term *", ["Term 1","Term 2","Term 3","Term 4"], key="tr_term_add")
                    tr_week_lbl  = st.text_input("Week label *", placeholder="e.g. Week 3")
                    tr_week_date = st.date_input("Week start date (Monday) *", value=today-timedelta(days=today.weekday()), key="tr_week_date")
                    tr_notes     = st.text_area("Notes (optional)", height=60)
                st.markdown("**Times at mainstream school** *(leave blank = at CLC all day)*")
                day_cols = st.columns(5)
                tr_times = {}
                for i, (day, dk) in enumerate(zip(DAYS, DAY_KEYS)):
                    with day_cols[i]:
                        st.markdown(f"**{day[:3]}**")
                        tr_times[f"{dk}_start"] = st.time_input("From", value=None, key=f"tr_{dk}_s")
                        tr_times[f"{dk}_end"]   = st.time_input("To",   value=None, key=f"tr_{dk}_e")
                if st.form_submit_button("✅ Save Transition Week", type="primary", use_container_width=True):
                    if not tr_initials.strip():    st.warning("Please enter student initials.")
                    elif not tr_program_s:         st.warning("Please select a program.")
                    elif not tr_added_by.strip():  st.warning("Please enter your name.")
                    elif not tr_week_lbl.strip():  st.warning("Please enter a week label.")
                    else:
                        row = {"student_initials": tr_initials.strip(), "program": tr_program_s,
                               "mainstream_school": tr_school.strip(), "term": tr_term_val,
                               "week_label": tr_week_lbl.strip(), "week_start_date": str(tr_week_date),
                               "notes": tr_notes.strip(), "added_by": tr_added_by.strip()}
                        for dk in DAY_KEYS:
                            s = tr_times.get(f"{dk}_start"); e = tr_times.get(f"{dk}_end")
                            row[f"{dk}_start"] = str(s) if s else None
                            row[f"{dk}_end"]   = str(e) if e else None
                        save_transition(row)
                        st.success(f"✅ Transition week saved for {tr_initials.strip()}!"); st.rerun()

        st.markdown("---")
        disp_trans = db_transitions(initials=None if tr_student == "All" else tr_student)
        if tr_prog != ["JP","PY","SY"]: disp_trans = [t for t in disp_trans if t.get("program","") in tr_prog]
        if tr_term != "All":            disp_trans = [t for t in disp_trans if t.get("term","") == tr_term]

        if not disp_trans:
            st.markdown('<p style="color:#888;">No transition schedules found. Add one above.</p>', unsafe_allow_html=True)
        else:
            by_stu2 = defaultdict(list)
            for t in disp_trans: by_stu2[t.get("student_initials","?")].append(t)

            for init, weeks in by_stu2.items():
                prog   = weeks[0].get("program","")
                pc     = PROGRAM_COLORS.get(prog, {"color":"#374151","bg":"#f3f4f6"})
                school = weeks[0].get("mainstream_school","")
                st.markdown(
                    f'<div style="background:{pc["bg"]};border-left:4px solid {pc["color"]};border-radius:10px;'
                    f'padding:0.6rem 1rem;margin:1rem 0 0.5rem;display:flex;align-items:center;gap:0.75rem;">'
                    f'<span style="background:{pc["color"]};color:white;font-size:0.75rem;font-weight:700;'
                    f'padding:0.2rem 0.55rem;border-radius:8px;">{prog}</span>'
                    f'<strong style="font-size:1rem;color:{pc["color"]};">🔀 {init}</strong>'
                    f'{"<span style=color:#666;font-size:0.82rem;> → "+school+"</span>" if school else ""}'
                    f'</div>', unsafe_allow_html=True)

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
<tr><th class="row-h">Term / Week</th><th>Monday</th><th>Tuesday</th><th>Wednesday</th><th>Thursday</th><th>Friday</th></tr>"""
                cur_term = None
                for idx_w, week in enumerate(weeks):
                    trm = week.get("term",""); wlbl = week.get("week_label","")
                    wdate = week.get("week_start_date","")
                    try:
                        wmon = datetime.strptime(wdate[:10],"%Y-%m-%d").date()
                        date_cells = "".join([f'<td style="font-size:0.7rem;color:#888;background:#fafafa;">{(wmon+timedelta(days=di)).strftime("%-d %b")}</td>' for di in range(5)])
                    except: date_cells = "<td colspan='5'></td>"
                    if trm != cur_term:
                        cur_term = trm
                        html += f'<tr><td class="label-cell" colspan="6" style="background:#2d5a3d;color:white;font-size:0.8rem;text-transform:uppercase;">{trm}</td></tr>'
                    html += f'<tr class="{"week-divider" if idx_w>0 else ""}"><td class="label-cell" rowspan="2">{wlbl}</td>{date_cells}</tr><tr>'
                    for dk in DAY_KEYS:
                        s = fmt_time_short(week.get(f"{dk}_start")); e = fmt_time_short(week.get(f"{dk}_end"))
                        if s and e:   html += f'<td class="has-time">{s}–{e}</td>'
                        elif s:       html += f'<td class="has-time">{s}</td>'
                        else:         html += '<td class="no-time">CLC</td>'
                    html += "</tr>"
                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)
                if weeks[0].get("notes"): st.caption(f"📝 {weeks[0]['notes']}")

                with st.expander(f"✏️ Edit / delete weeks for {init}"):
                    for week in weeks:
                        tid = week.get("id",""); wlbl = week.get("week_label","")
                        ec1, ec2, ec3 = st.columns([4,1,1])
                        with ec1: st.markdown(f"**{week.get('term','')} · {wlbl}** — {week.get('week_start_date','')}")
                        with ec2:
                            if st.button("✏️", key=f"tr_ed_{tid}"):
                                st.session_state.edit_event_id = tid if st.session_state.edit_event_id != tid else None; st.rerun()
                        with ec3:
                            if st.session_state.is_admin:
                                if st.button("🗑️", key=f"tr_del_{tid}"):
                                    del_transition(tid); st.rerun()
                        if st.session_state.edit_event_id == tid:
                            with st.form(f"tr_ef_{tid}", clear_on_submit=False):
                                ef1, ef2 = st.columns(2)
                                with ef1:
                                    e_i   = st.text_input("Student initials *", value=week.get("student_initials",""))
                                    po    = ["","JP","PY","SY"]
                                    e_pr  = st.selectbox("Program *", po, index=po.index(week.get("program","")) if week.get("program","") in po else 0)
                                    e_sc  = st.text_input("Mainstream school", value=week.get("mainstream_school",""))
                                    e_by  = st.text_input("Added by *", value=week.get("added_by",""))
                                with ef2:
                                    e_tm  = st.selectbox("Term *", ["Term 1","Term 2","Term 3","Term 4"], index=["Term 1","Term 2","Term 3","Term 4"].index(week.get("term","Term 1")) if week.get("term") in ["Term 1","Term 2","Term 3","Term 4"] else 0)
                                    e_wl  = st.text_input("Week label *", value=week.get("week_label",""))
                                    try:   e_wd = st.date_input("Week start date *", value=datetime.strptime(week.get("week_start_date","")[:10],"%Y-%m-%d").date(), key=f"tr_wd_{tid}")
                                    except: e_wd = st.date_input("Week start date *", value=today, key=f"tr_wd_{tid}")
                                    e_nt  = st.text_area("Notes", value=week.get("notes",""), height=50)
                                st.markdown("**Times at mainstream**")
                                edc = st.columns(5)
                                e_tt = {}
                                for i, (dy, dk) in enumerate(zip(DAYS, DAY_KEYS)):
                                    with edc[i]:
                                        st.markdown(f"**{dy[:3]}**")
                                        e_tt[f"{dk}_start"] = st.time_input("From", value=None, key=f"tr_e{dk}s_{tid}")
                                        e_tt[f"{dk}_end"]   = st.time_input("To",   value=None, key=f"tr_e{dk}e_{tid}")
                                if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                                    upd_row = {"student_initials": e_i.strip(), "program": e_pr,
                                               "mainstream_school": e_sc.strip(), "term": e_tm,
                                               "week_label": e_wl.strip(), "week_start_date": str(e_wd),
                                               "notes": e_nt.strip(), "added_by": e_by.strip()}
                                    for dk in DAY_KEYS:
                                        s = e_tt.get(f"{dk}_start"); ev2 = e_tt.get(f"{dk}_end")
                                        upd_row[f"{dk}_start"] = str(s) if s else None
                                        upd_row[f"{dk}_end"]   = str(ev2) if ev2 else None
                                    upd_transition(tid, upd_row)
                                    st.session_state.edit_event_id = None
                                    st.success("✅ Updated!"); st.rerun()

    # ════ STUDENT MEETINGS ══════════════════════════════════════════════════════
    with st_mtg:
        st.markdown(
            '<div style="background:#f0fdf4;border-left:4px solid #15803d;border-radius:8px;'
            'padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.84rem;color:#14532d;">'
            '📅 Meetings logged here <b>automatically appear in the main calendar</b> on the correct date. '
            'Use the calendar\'s Entry / Review / Transition / TAC filter to view them.'
            '</div>', unsafe_allow_html=True)

        with st.expander("➕ Log a Student Meeting", expanded=True):
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
                            st.success(f"✅ {mtg_type} logged for {mtg_init.strip()} on {fmt_date(mtg_date)} — now visible in calendar!")
                            st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Recent Student Meetings")

        mf1, mf2, mf3 = st.columns(3)
        with mf1: mf_prog = st.multiselect("Program", ["JP","PY","SY"], default=["JP","PY","SY"], key="mf_prog")
        with mf2: mf_type = st.multiselect("Meeting type", STUDENT_MEETING_TYPES, default=STUDENT_MEETING_TYPES, key="mf_type")
        with mf3: mf_from = st.date_input("From", value=today-timedelta(weeks=12), key="mf_from")

        all_mtgs = [e for e in db_events(mf_from, today+timedelta(weeks=52))
                    if e.get("event_type") in STUDENT_MEETING_TYPES]
        if mf_prog != ["JP","PY","SY"]:         all_mtgs = [e for e in all_mtgs if e.get("program","") in mf_prog]
        if mf_type != STUDENT_MEETING_TYPES:     all_mtgs = [e for e in all_mtgs if e.get("event_type") in mf_type]
        all_mtgs.sort(key=lambda x: str(x.get("event_date","")), reverse=True)

        if not all_mtgs:
            st.markdown('<p style="color:#888;">No student meetings found. Log one above.</p>', unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(all_mtgs)} meeting{'s' if len(all_mtgs)!=1 else ''} found**")
            for ev in all_mtgs:
                render_event_row(ev, "stmtg")

# ─── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;color:#aaa;font-size:0.76rem;">
Cowandilla Learning Centre · Communal Staff Calendar · Student meetings auto-sync to calendar
</div>""", unsafe_allow_html=True)
