import streamlit as st
from datetime import date, timedelta, datetime
import database as db
import json

st.set_page_config(
    page_title="CLC Daily Bulletin",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from auth import require_auth, logout_button, get_staff_name
require_auth("Daily Bulletin", "📰")
logout_button("sidebar")

# ── DESIGN SYSTEM ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
  background: #f0f4f0 !important;
  font-family: 'DM Sans', sans-serif;
}
[data-testid="stAppViewContainer"] { padding: 0; }
[data-testid="stHeader"] { display: none; }
[data-testid="stSidebar"] { display: none; }
#MainMenu, footer, .stDeployButton { display: none; }

/* ── Main container ── */
.main .block-container {
  padding: 0 !important;
  max-width: 100% !important;
}

/* ── TOP NAV BAR ── */
.top-nav {
  background: #1a2e44;
  padding: 0 2rem;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}
.top-nav-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.top-nav-logo {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, #6BBF4E, #4a8f33);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; color: white; font-size: 0.85rem;
}
.top-nav-title {
  font-family: 'DM Sans', sans-serif;
  font-weight: 700;
  font-size: 0.95rem;
  color: white;
  letter-spacing: 0.02em;
}
.top-nav-sub {
  font-size: 0.72rem;
  color: rgba(255,255,255,0.5);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.top-nav-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.nav-badge {
  background: rgba(107,191,78,0.2);
  border: 1px solid rgba(107,191,78,0.4);
  color: #6BBF4E;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  letter-spacing: 0.05em;
}
.nav-badge.edit { background: rgba(232,161,37,0.2); border-color: rgba(232,161,37,0.4); color: #e8a125; }

/* ── BULLETIN HEADER ── */
.bulletin-hero {
  background: linear-gradient(135deg, #3d7a28 0%, #6BBF4E 60%, #8fd468 100%);
  padding: 1.75rem 2rem 1.5rem;
  position: relative;
  overflow: hidden;
}
.bulletin-hero::before {
  content: '';
  position: absolute;
  top: -40px; right: -40px;
  width: 200px; height: 200px;
  background: rgba(255,255,255,0.06);
  border-radius: 50%;
}
.bulletin-hero::after {
  content: '';
  position: absolute;
  bottom: -60px; right: 100px;
  width: 160px; height: 160px;
  background: rgba(255,255,255,0.04);
  border-radius: 50%;
}
.bulletin-hero-inner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  position: relative;
  z-index: 1;
}
.bulletin-date-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  color: rgba(255,255,255,0.7);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 0.3rem;
}
.bulletin-date-main {
  font-family: 'Playfair Display', serif;
  font-size: 2rem;
  color: white;
  font-weight: 700;
  line-height: 1.1;
}
.bulletin-date-sub {
  font-size: 0.85rem;
  color: rgba(255,255,255,0.75);
  margin-top: 0.25rem;
  font-weight: 400;
}
.fun-fact-pill {
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  padding: 0.65rem 1rem;
  max-width: 420px;
}
.fun-fact-label {
  font-size: 0.65rem;
  color: rgba(255,255,255,0.6);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 0.2rem;
}
.fun-fact-text {
  font-size: 0.85rem;
  color: white;
  font-weight: 500;
  line-height: 1.4;
}

/* ── DAY NAV ── */
.day-nav-bar {
  background: white;
  border-bottom: 2px solid #e8f0e3;
  padding: 0 2rem;
  display: flex;
  align-items: center;
  gap: 0;
  overflow-x: auto;
}
.day-pill {
  padding: 0.75rem 1.25rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: #5a6e5a;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  text-decoration: none;
}
.day-pill:hover { color: #4a8f33; }
.day-pill.active { color: #4a8f33; border-bottom-color: #6BBF4E; }
.day-pill.today { color: #1a2e44; font-weight: 700; }

/* ── CONTENT AREA ── */
.content-area {
  padding: 1.5rem 2rem 3rem;
  max-width: 1600px;
  margin: 0 auto;
}

/* ── SECTION CARDS ── */
.section-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  overflow: hidden;
  margin-bottom: 1.25rem;
}
.section-card-header {
  padding: 0.6rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.section-card-header.green  { background: #6BBF4E; }
.section-card-header.navy   { background: #1a2e44; }
.section-card-header.brown  { background: #A67C6A; }
.section-card-header.amber  { background: #e8a125; }
.section-card-header.blue   { background: #4a7fb5; }
.section-card-header.purple { background: #7a5bb5; }
.section-card-header.slate  { background: #6a7f8a; }
.section-card-header h3 {
  font-size: 0.72rem;
  font-weight: 700;
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0;
}
.section-card-header.amber h3 { color: #1a2e44; }
.section-card-body { padding: 0.75rem; }

/* ── DATA TABLES ── */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}
.data-table th {
  background: #f4f8f2;
  color: #4a6640;
  font-weight: 600;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.4rem 0.6rem;
  text-align: left;
  border-bottom: 2px solid #d8ead2;
}
.data-table td {
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid #f0f4ee;
  color: #2a3a2a;
  vertical-align: top;
}
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafcf9; }
.data-table td.empty { color: #bbb; font-style: italic; font-size: 0.72rem; }

/* Kitchen highlight */
.kitchen-row td { background: #fff8e6 !important; font-weight: 600; }
.kitchen-badge {
  background: #e8a125;
  color: #1a2e44;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Vehicle time grid */
.vehicle-time { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #888; }
.vehicle-booking { 
  background: #e8f5e1; 
  color: #2d6b1a; 
  padding: 0.1rem 0.4rem; 
  border-radius: 4px; 
  font-size: 0.75rem;
  font-weight: 500;
}

/* Program changes scroll */
.pc-scroll { overflow-x: auto; }
.pc-table { min-width: 1400px; }
.pc-table th { background: #1a2e44; color: rgba(255,255,255,0.8); }
.pc-table td.timeslot { background: #f9fbf8; text-align: center; font-family: 'DM Mono', monospace; font-size: 0.7rem; }
.pc-table td.timeslot.filled { background: #e8f5e1; color: #2d6b1a; font-weight: 600; }

/* ── TABS ── */
[data-baseweb="tab-list"] {
  background: transparent !important;
  gap: 0.25rem !important;
  border-bottom: 2px solid #e0e8dc !important;
  padding: 0 !important;
}
[data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 8px 8px 0 0 !important;
  padding: 0.5rem 1rem !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  color: #7a907a !important;
  border: none !important;
}
[aria-selected="true"][data-baseweb="tab"] {
  background: white !important;
  color: #4a8f33 !important;
  border-bottom: 2px solid #6BBF4E !important;
}
[data-baseweb="tab-panel"] { padding: 1rem 0 0 !important; }

/* ── STREAMLIT FORM OVERRIDES ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
  border: 1.5px solid #d8e8d4 !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.82rem !important;
  background: white !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: #6BBF4E !important;
  box-shadow: 0 0 0 3px rgba(107,191,78,0.15) !important;
}
label[data-testid="stWidgetLabel"] p {
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  color: #5a7a5a !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
}
.stButton button {
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
}
.stButton button[kind="primary"] {
  background: #4a8f33 !important;
  border: none !important;
}
.stButton button[kind="primary"]:hover { background: #3d7a28 !important; }

/* ── DATA EDITOR ── */
[data-testid="stDataEditor"] {
  border: 1.5px solid #d8e8d4 !important;
  border-radius: 10px !important;
  overflow: hidden;
}

/* ── ARCHIVE CARD ── */
.arch-card {
  background: white;
  border: 1.5px solid #e0e8dc;
  border-left: 4px solid #6BBF4E;
  border-radius: 10px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.6rem;
  transition: box-shadow 0.15s;
}
.arch-card:hover { box-shadow: 0 4px 16px rgba(107,191,78,0.15); }
.arch-card-date { font-weight: 700; font-size: 0.9rem; color: #1a2e44; }
.arch-card-fact { font-size: 0.78rem; color: #7a907a; margin-top: 0.2rem; }

/* ── EMPTY STATE ── */
.empty-state {
  text-align: center;
  padding: 2rem;
  color: #9ab09a;
  font-size: 0.85rem;
}
.empty-state .icon { font-size: 2rem; margin-bottom: 0.5rem; }

/* ── AUTH GATE ── */
.auth-gate {
  max-width: 400px;
  margin: 4rem auto;
  background: white;
  border-radius: 16px;
  padding: 2.5rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  text-align: center;
}
.auth-gate h2 { font-family: 'Playfair Display', serif; color: #1a2e44; margin-bottom: 0.5rem; }
.auth-gate p { color: #7a907a; font-size: 0.85rem; margin-bottom: 1.5rem; }

/* ── NOTIFICATIONS ── */
.stSuccess, .stError, .stInfo {
  border-radius: 10px !important;
  font-size: 0.85rem !important;
}

/* Responsive */
@media (max-width: 768px) {
  .bulletin-date-main { font-size: 1.4rem; }
  .content-area { padding: 1rem; }
  .fun-fact-pill { max-width: 100%; }
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────
def _default_date():
    """Return today's date, but skip weekends — Sat → Fri, Sun → Mon."""
    d = date.today()
    if d.weekday() == 5:   # Saturday → Friday
        return d - timedelta(days=1)
    if d.weekday() == 6:   # Sunday → Monday
        return d + timedelta(days=1)
    return d

def init_state():
    defaults = {
        "authenticated": False,
        "edit_mode": False,
        "selected_date": _default_date(),
        "page": "bulletin",
        "show_login": False,
        "show_inline_login": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "clcstaff2026")

# ── HELPERS ───────────────────────────────────────────────────
def week_dates(d: date):
    monday = d - timedelta(days=d.weekday())
    return [monday + timedelta(days=i) for i in range(5)]

def term_label(d: date):
    y = d.year
    terms = {1:(date(y,1,28),date(y,4,11)), 2:(date(y,4,28),date(y,7,4)),
              3:(date(y,7,21),date(y,9,26)), 4:(date(y,10,13),date(y,12,12))}
    for t,(s,e) in terms.items():
        if s <= d <= e: return f"Term {t} · {y}"
    return str(y)

def default_bulletin():
    return {
        "fun_fact": "",
        "staff_absent": [{"Staff Absence":"","TRT":"","Student Absence":"","Program":"","Reason":""} for _ in range(4)],
        "excursions": [{"Program":"","Staff Member":"","Time Departing":"","Time Returning":"","Location":""} for _ in range(4)],
        "staff_meetings": [{"Type":"","Staff Member":"","Location":"","Time Departing":"","Time Returning":"","Student":""} for _ in range(4)],
        "entry_meetings": [{"Time":"","Program":"","Student":""} for _ in range(4)],
        "additional_messages": [{"Staff Member":"","Visitor":"","Reason":"","Arriving/Departing":""} for _ in range(4)],
        "travel_jp": [{"Student":"","Transport To":"","Transport From":"","Times":""} for _ in range(5)],
        "travel_py": [{"Student":"","Transport To":"","Transport From":"","Times":""} for _ in range(5)],
        "travel_sy": [{"Student":"","Transport To":"","Transport From":"","Times":""} for _ in range(5)],
        "vehicle_bookings": [],
        "staff_responsibilities": {"kitchen_duties":"","meeting_pd_focus":"","chair":"","minutes":""},
        "nit_booking": "",
        "program_changes": [_empty_pc() for _ in range(3)]
    }

def load_bulletin(d: date):
    data = db.get_bulletin(d)
    defaults = default_bulletin()
    if not data:
        data = defaults.copy()
    else:
        for k, v in defaults.items():
            if k not in data:
                data[k] = v

    # ── Backward compat — old vehicle_bookings format (dict → list) ────────
    vb = data.get("vehicle_bookings", [])
    if isinstance(vb, dict):
        # Old format: {time: {van, kia}} — convert to list of booking dicts
        converted = []
        for t, v in vb.items():
            if v.get("van",""):
                converted.append({"vehicle":"Van","booker":v["van"],"whole_day":True,"start_time":"","end_time":""})
            if v.get("kia",""):
                converted.append({"vehicle":"Kia","booker":v["kia"],"whole_day":True,"start_time":"","end_time":""})
        data["vehicle_bookings"] = converted

    # ── Backward compat — old program_changes format (list of old-key dicts) ─
    pc = data.get("program_changes", [])
    if pc and isinstance(pc[0], dict) and "change_reason" not in pc[0]:
        data["program_changes"] = [_empty_pc() for _ in range(3)]

    # ── Weekly carry-forward for staff responsibilities ──────────────
    # If today's responsibilities are blank, inherit from Monday of the
    # same week so staff only need to enter them once per week.
    sr = data.get("staff_responsibilities", {})
    resp_keys = ["kitchen_duties", "meeting_pd_focus", "chair", "minutes"]
    is_empty = not any(sr.get(k, "").strip() for k in resp_keys)

    monday = d - timedelta(days=d.weekday())
    if is_empty and d != monday:
        monday_data = db.get_bulletin(monday)
        if monday_data:
            monday_sr = monday_data.get("staff_responsibilities", {})
            if any(monday_sr.get(k, "").strip() for k in resp_keys):
                data["staff_responsibilities"] = monday_sr

    # ── Auto-fill fun fact if empty — always override blank saved values ──
    if not data.get("fun_fact", "").strip():
        data["fun_fact"] = daily_fun_fact(d)
    # Also ensure display mode always gets a fact
    if not data.get("fun_fact", "").strip():
        data["fun_fact"] = daily_fun_fact(d)

    return data


# ── QUICK NOTICE HELPERS ──────────────────────────────────────
NOTICE_CATS = {
    "General":      {"color": "#4a8f33", "bg": "#e8f5e1", "emoji": "📢"},
    "Reminder":     {"color": "#c97b1a", "bg": "#fff3e0", "emoji": "⏰"},
    "Urgent":       {"color": "#b91c1c", "bg": "#fee2e2", "emoji": "🚨"},
    "Student Info": {"color": "#1d4ed8", "bg": "#dbeafe", "emoji": "👨‍🎓"},
    "Facilities":   {"color": "#6d28d9", "bg": "#ede9fe", "emoji": "🏫"},
    "Wellbeing":    {"color": "#0e7490", "bg": "#cffafe", "emoji": "💚"},
}

# ── CLC STAFF LIST (edit this list to match your actual staff) ──────────────
CLC_STAFF = [
    "— Select staff member —",
    "Admin",
    "Teacher A",
    "Teacher B",
    "Teacher C",
    "SSO 1",
    "SSO 2",
    "SSO 3",
]

# ── PROGRAM CHANGES — 15-min time slots & options ───────────────────────────
PC_TIME_SLOTS = [
    "9:00","9:15","9:30","9:45",
    "10:00","10:15","10:30","10:45",
    "11:00","11:15","11:30","11:45",
    "12:00","12:15","12:30","12:45",
    "1:00","1:15","1:30","1:45",
    "2:00","2:15","2:30","2:45",
]
PC_SLOT_OPTIONS     = ["", "JP", "PY", "SY", "Lunch Cover", "Lunch Break", "NIT", "Other"]
PC_SLOT_OPTIONS_EXT = ["", "JP Cover", "PY Cover", "SY Cover", "Lunch Cover", "Lunch Break", "Other"]

# Colour map for slot values (used in both edit indicators and HTML rendering)
def _slot_color(val, dark=False):
    _lc = ("#fff3cd", "#4a3200")
    _lb = ("#cce5ff", "#002a4a")
    _nd = ("#f0f0f0", "#2a2a2a")
    _ok = ("#e8f5e1", "#1e3d1e")
    _ot = ("#fce8ff", "#2a003a")
    d = 1 if dark else 0
    if val in ("Lunch Cover",):               return _lc[d]
    if val in ("Lunch Break",):               return _lb[d]
    if val in ("Normal Duties",):             return _nd[d]
    if val in ("JP","PY","SY","NIT",
               "JP Cover","PY Cover","SY Cover"): return _ok[d]
    if val in ("Other",):                     return _ot[d]
    return "transparent"

def _slot_emoji(val):
    m = {"JP":"🟦","PY":"🟣","SY":"🟫","JP Cover":"🟦","PY Cover":"🟣","SY Cover":"🟫",
         "Lunch Cover":"🟡","Lunch Break":"🔵","NIT":"⬛","Normal Duties":"⬜","Other":"🔷"}
    return m.get(val, "")

def _empty_pc():
    return {
        "change_reason": "",      # "Staff Absence" | "Site Need"
        "staff_absent": "",
        "trt": False,
        "trt_name": "",
        "covering": "",           # "Program" | "NIT"  (TRT path)
        "program": "",            # "JP" | "PY" | "SY" (TRT/Program path)
        "time_slots": {},         # TRT path timetable
        "staff_allocations": [],  # No-TRT path: [{name, normal_prog, time_slots}]
        "staff_member": "",       # Site Need no-TRT
        "release_type": "",
    }

def _empty_alloc():
    return {"name": "", "normal_prog": "", "time_slots": {}}

def _pc_row_html(label, normal_prog, ts, dark=False):
    """Render ONE staff row as a coloured timetable strip."""
    text  = ("#1a2e44" if not dark else "#c8d8c8")
    hdr   = ("#4a6640" if not dark else "#6BBF4E")
    th_bg = ("#f4f8f2" if not dark else "#111e11")
    fs    = "0.56rem" if dark else "0.66rem"
    lbl_c = ("#1a2e44" if not dark else "#6BBF4E")

    # Time header row
    th_cells = "".join([
        f'<th style="background:{th_bg};color:{hdr};font-size:0.52rem;padding:1px 3px;'
        f'text-align:center;white-space:nowrap;border-right:1px solid {"#e0e8dc" if not dark else "#2a3d2a"};">'
        f'{s}</th>'
        for s in PC_TIME_SLOTS
    ])

    # Data cells
    td_cells = ""
    for slot in PC_TIME_SLOTS:
        raw    = ts.get(slot, {})
        val    = raw.get("value","")  if isinstance(raw,dict) else str(raw)
        person = raw.get("person","") if isinstance(raw,dict) else ""
        bg     = _slot_color(val, dark)
        border = f'border-right:1px solid {"#e0e8dc" if not dark else "#2a3d2a"};'
        disp   = val if val else ("·" if not dark else "")
        inner  = f'<span style="font-weight:700;">{disp}</span>'
        if person:
            if val == "Lunch Cover":
                _plbl = f"→ {person}"   # "releasing" arrow
            elif val == "Lunch Break":
                _plbl = f"↩ {person}"   # "covered by" arrow
            else:
                _plbl = person
            inner += f'<br><span style="font-size:0.85em;opacity:0.7;">{_plbl}</span>'
        td_cells += (
            f'<td style="background:{bg};color:{text};text-align:center;'
            f'padding:2px 2px;font-size:{fs};min-width:34px;vertical-align:top;{border}">'
            f'{inner}</td>'
        )

    # Row label column
    lbl_html = (
        f'<td style="white-space:nowrap;padding:3px 8px 3px 4px;color:{lbl_c};'
        f'font-weight:700;font-size:{fs};vertical-align:middle;'
        f'border-right:2px solid {"#6BBF4E" if not dark else "#4a8f33"};">'
        f'{label}'
        f'{"<br>" if normal_prog else ""}'
        f'<span style="font-weight:400;opacity:0.7;font-size:0.9em;">{normal_prog}</span>'
        f'</td>'
    )

    return (
        f'<tr>'
        f'{lbl_html}'
        f'{td_cells}'
        f'</tr>'
    )

def _pc_timetable_html(entry, dark=False):
    """
    Render an entire program change entry as an HTML table.
    Handles both TRT (single row) and multi-staff-allocation scenarios.
    """
    th_bg = ("#f4f8f2" if not dark else "#111e11")
    hdr   = ("#4a6640" if not dark else "#6BBF4E")

    th_cells = (
        '<th style="white-space:nowrap;padding:3px 8px 3px 4px;'
        f'background:{th_bg};color:{hdr};font-size:0.52rem;'
        f'border-right:2px solid {"#6BBF4E" if not dark else "#4a8f33"};">Staff / Role</th>'
        + "".join([
            f'<th style="background:{th_bg};color:{hdr};font-size:0.52rem;padding:1px 3px;'
            f'text-align:center;white-space:nowrap;border-right:1px solid {"#e0e8dc" if not dark else "#2a3d2a"};">'
            f'{s}</th>'
            for s in PC_TIME_SLOTS
        ])
    )

    rows_html = ""

    # TRT path — single timetable
    ts = entry.get("time_slots", {})
    trt_name = entry.get("trt_name","")
    covering = entry.get("covering","")
    program  = entry.get("program","")
    if ts and any((v.get("value","") if isinstance(v,dict) else v) for v in ts.values()):
        lbl = trt_name if trt_name else "TRT"
        norm = f"{covering} · {program}" if program else covering
        rows_html += _pc_row_html(lbl, norm, ts, dark)

    # No-TRT allocations — one row per allocated staff member
    for alloc in entry.get("staff_allocations", []):
        a_ts = alloc.get("time_slots", {})
        if not a_ts or not any((v.get("value","") if isinstance(v,dict) else v) for v in a_ts.values()):
            continue
        rows_html += _pc_row_html(
            alloc.get("name","(Staff)"),
            alloc.get("normal_prog",""),
            a_ts, dark
        )

    if not rows_html:
        return ""

    return (
        f'<div style="overflow-x:auto;margin-top:4px;">'
        f'<table style="border-collapse:collapse;width:auto;">'
        f'<thead><tr>{th_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )

# ── AUSTRALIAN FUN FACTS — one per day, deterministic by date ────────────────
_AUS_FACTS = [
    "Australia is the only continent that is also a single country — and somehow still can't decide where to put its capital.",
    "Kangaroos can't walk backwards, which is why they're on the Australian coat of arms — always moving forward, mate.",
    "Australia has more kangaroos than people. The roos are winning.",
    "The Box Jellyfish has 24 eyes. It still can't see why Australians swim anywhere near it.",
    "A group of kangaroos is called a mob. Very on-brand for Australia.",
    "Wombats produce cube-shaped poo — the only animal in the world that does. Science still hasn't fully explained why.",
    "Australia has 10 of the world's 15 most venomous snakes. They're very proud of this.",
    "The Great Barrier Reef is the largest living structure on Earth — visible from space, yet invisible to politicians.",
    "Australian Rules Football was invented to keep cricketers fit during winter. Cricket: unintentionally very useful.",
    "The platypus is venomous, lays eggs, and has a bill like a duck. It looks like Australia designed it after a big night.",
    "Australians consume more than 1.9 billion Tim Tams per year — roughly 80 per person. This tracks.",
    "The Sydney Funnel-web Spider is considered the world's most dangerous spider. Sydney has strong opinions about everything.",
    "Australia once fought a war against emus. The emus won. This is true. Look it up.",
    "The Dingo Fence is 5,614 km long — built to keep dingoes out of southern Australia. The dingoes are biding their time.",
    "Eucalyptus leaves are mildly toxic to most animals. Koalas eat almost nothing else and sleep 22 hours a day. Icon behaviour.",
    "Australia has the longest straight stretch of railway in the world — 478 km of perfectly straight track through the Nullarbor.",
    "The word 'kangaroo' may come from a Guugu Yimithirr phrase meaning 'I don't understand you' — said to the first Europeans who pointed at one.",
    "Australia has pink lakes. Lake Hillier on Middle Island is bubblegum pink year-round, and scientists are still arguing about exactly why.",
    "Canberra was purpose-built as the capital because Sydney and Melbourne couldn't agree on which city deserved it. Classic.",
    "The Thorny Devil lizard can drink through its feet by standing in water. Useful at a BBQ.",
    "Australia's first police force was made up of the most well-behaved convicts. Starting as you mean to go on.",
    "The world's largest cattle station — Anna Creek — is bigger than the entire country of Israel.",
    "Australians invented WiFi. Also the black box flight recorder. And the bionic ear. But mostly WiFi.",
    "Drop bears are not real. Probably.",
    "The laughing kookaburra's call sounds exactly like a human laughing manically. Nobody finds this unsettling.",
    "Vegemite was invented in Australia in 1922 as a way to use leftover brewer's yeast. You're welcome, or sorry, depending on your position.",
    "The Murray-Darling river system is so important that an entire government department was created just to argue about it.",
    "Australians use the word 'reckon' as a sophisticated intellectual agreement mechanism. Fully reckon this is true.",
    "A baby kangaroo (joey) is about the size of a jellybean when born. It then spends six months in a pouch. Living the dream.",
    "The Australian dollar is made from polymer plastic, making it waterproof. Essential for a country surrounded by water.",
    "Australia has the world's largest population of wild camels — over a million. They arrived in the 1800s and clearly decided to stay.",
    "The Melbourne Cup is a public holiday in Victoria. Only Australians would make a horse race a legitimate reason to stop work.",
    "Australians call thongs something you wear on your feet. Other countries find this confusing at every BBQ invitation.",
    "The Australian pelican has the longest bill of any bird in the world. Big bill energy.",
    "Quokkas are considered the happiest animal on Earth. They live on Rottnest Island. No predators, good weather — honestly same.",
    "Australian magpies remember human faces and will swoop people they dislike. They hold grudges. Do not underestimate them.",
    "The Tasmanian Devil's scientific name is Sarcophilus harrisii, meaning 'Harris's meat-lover'. A very honest name.",
    "Australia's coat of arms features a kangaroo and an emu because neither can walk backwards. Chosen on purpose.",
    "The first cricket Test match ever played was Australia vs England in 1877. Australia won. England has been processing this since.",
    "Australians say 'arvo' for afternoon, 'servo' for service station, and 'bottle-o' for bottle shop. The nation abbreviates by default.",
    "There are more than 10,000 beaches in Australia. Visiting a new one every day would take 27 years. Start planning.",
    "The bunyip is a mythical creature from Aboriginal folklore said to lurk in swamps. No one has found one. Not ruling it out.",
    "A mob of emus will methodically destroy a fence to get to crops on the other side. They have a system. They are organised.",
    "Australia is the driest inhabited continent on Earth, yet Australians insist on planting lawns everywhere. Optimism.",
    "The Royal Flying Doctor Service covers 7.69 million square kilometres — essentially the world's largest GP practice.",
    "Uluru extends 2.5 km underground — what you see is only a fraction of the full rock. Like an iceberg, but red and in a desert.",
    "The cassowary is considered the world's most dangerous bird. It lives in Far North Queensland. Of course it does.",
    "Australians invented the Hills Hoist rotary clothesline. A genuine contribution to civilisation.",
    "The Australian Alps receive more snowfall than Switzerland in a good year. Nobody ever believes this.",
    "A group of wombats is called a wisdom. A group of platypuses is called a paddle. Australian fauna naming is an art.",
    "South Australia was the first place in the world to give women the right to stand for parliament, back in 1894.",
    "The echidna and platypus are the only two mammals in the world that lay eggs. Both live in Australia, naturally.",
    "Australia has more species of lizard than any other country in the world. Over 860. All of them confident.",
    "Neighbours has been running since 1985, making it one of the longest-running dramas in the world. Erinsborough is eternal.",
    "The phrase 'no worries' appears in Australian conversation more than any other expression. It is both a greeting and a worldview.",
    "Tim Tams were named after a horse that won the 1958 Kentucky Derby. An American horse named an Australian biscuit. Culture is weird.",
    "Australia has a national feral camel management programme. This is a real government job.",
    "The ACT (Canberra) is the only place in Australia where you can legally own a Segway. Make of that what you will.",
    "Australia has been ranked one of the world's most liveable countries for decades — largely because we refuse to leave.",
]

def daily_fun_fact(d):
    import hashlib
    seed = int(hashlib.md5(str(d).encode()).hexdigest(), 16)
    return _AUS_FACTS[seed % len(_AUS_FACTS)]


def _get_sb():
    return db.get_supabase()

def load_notices(for_date=None):
    try:
        q = _get_sb().table("bulletin_notices").select("*").order("created_at", desc=False)
        if for_date:
            q = q.eq("notice_date", str(for_date))
        result = q.execute()
        return result.data or []
    except Exception as e:
        st.warning(f"⚠️ Could not load notices: {e}")
        return []

def save_notice(row):
    try:
        _get_sb().table("bulletin_notices").insert(row).execute()
    except Exception as e:
        st.error(f"Could not save notice: {e}")

def load_scheduled_meetings(for_date=None):
    """Load team meetings from tm_schedules that are flagged show_in_bulletin,
       filtered to the given date's day of week."""
    _DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    try:
        d = for_date or date.today()
        day_name = _DAY_NAMES[d.weekday()]
        res = _get_sb().table("tm_schedules").select("*").eq("show_in_bulletin", True).execute()
        rows = res.data or []
        meetings = []
        for r in rows:
            if r.get("day_of_week","").strip().lower() == day_name.lower():
                prog = r.get("program","")
                prog_label = {"JP":"Junior Primary","PY":"Primary Years","SY":"Senior Years",
                              "STAFF":"All Staff","ADMIN":"Admin"}.get(prog, prog)
                meetings.append({
                    "Type": r.get("schedule_name","Team Meeting"),
                    "Staff Member": prog_label,
                    "Location": "",
                    "Time Departing": r.get("meeting_time",""),
                    "Time Returning": "",
                    "Student": "",
                })
        return meetings
    except Exception:
        return []

def delete_notice(nid):
    try:
        _get_sb().table("bulletin_notices").delete().eq("id", nid).execute()
    except Exception as e:
        st.error(f"Could not delete notice: {e}")



# ══════════════════════════════════════════════════════════════
# DISPLAY MODE — Staff Room Full-Screen View
# Access via: your-app-url/?display=true
# ══════════════════════════════════════════════════════════════

# Check URL params for display mode
params = st.query_params
if params.get("display") == "true":

    # Always show today — reset to today on every fresh load
    # If manually navigated, honour that; midnight will naturally flip to new day
    import time
    if "display_date" not in st.session_state:
        st.session_state.display_date = date.today()

    # Midnight rollover — if the stored date is in the past, snap back to today
    if st.session_state.display_date < date.today():
        st.session_state.display_date = date.today()

    today = st.session_state.display_date
    d_data = load_bulletin(today)

    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: #f4f8f2 !important; }
    .main .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stHeader"] { display: none; }
    #MainMenu, footer, .stDeployButton { display: none; }
    [data-baseweb="tab-list"] { display: none !important; }
    [data-baseweb="tab-panel"] { padding: 0 !important; }
    /* hide the normal tabs rendered above */
    section[data-testid="stVerticalBlock"] > div:first-child { display: none; }
    </style>
    """, unsafe_allow_html=True)

    # Auto-refresh every 60 seconds — keeps data current and rolls over at midnight
    if "display_last_refresh" not in st.session_state:
        st.session_state.display_last_refresh = time.time()
    if time.time() - st.session_state.display_last_refresh > 60:
        st.session_state.display_last_refresh = time.time()
        # Snap to today on each refresh cycle
        st.session_state.display_date = date.today()
        st.rerun()

    # Google fonts
    st.markdown("""<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">""", unsafe_allow_html=True)

    # ── Header banner ──
    sr = d_data.get("staff_responsibilities", {})
    fun = d_data.get("fun_fact", "")

    st.markdown(f"""
    <style>
    .display-header {{
      background: linear-gradient(135deg, #1a4d8c 0%, #2d7d4f 100%);
      padding: 0.6rem 1.5rem;
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 3px solid #6BBF4E;
    }}
    .display-header-title {{ font-family: 'Playfair Display', serif; font-size: 1.1rem; color: white; font-weight: 700; letter-spacing: 0.05em; }}
    .display-header-date {{ font-family: 'DM Mono', monospace; font-size: 1rem; color: #6BBF4E; font-weight: 600; letter-spacing: 0.08em; }}
    .display-header-time {{ font-family: 'DM Mono', monospace; font-size: 1.4rem; color: #e8a125; font-weight: 700; }}
    .dp {{ background: #ffffff; border: 1px solid #d8ead8; border-radius: 8px; overflow: hidden; margin-bottom: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
    .dp-header {{ padding: 0.3rem 0.6rem; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: white; }}
    .dp-header.green  {{ background: #4a8f33; }}
    .dp-header.navy   {{ background: #1a2e44; }}
    .dp-header.brown  {{ background: #7a5c4a; }}
    .dp-header.amber  {{ background: #c97b1a; color: #1a2e44; }}
    .dp-header.blue   {{ background: #3a6a9a; }}
    .dp-header.purple {{ background: #6a4a9a; }}
    .dp-header.slate  {{ background: #4a5a6a; }}
    .dp-body {{ padding: 0.4rem 0.5rem; }}
    .dt {{ width: 100%; border-collapse: collapse; font-size: 0.62rem; color: #1e3a1e; font-family: 'DM Sans', sans-serif; }}
    .dt th {{ color: #6BBF4E; font-weight: 600; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.06em; padding: 0.2rem 0.3rem; border-bottom: 1px solid #2a3d2a; }}
    .dt td {{ padding: 0.18rem 0.3rem; border-bottom: 1px solid #e8f0e8; vertical-align: top; line-height: 1.3; }}
    .dt tr:last-child td {{ border-bottom: none; }}
    .dt-em {{ color: #9aaa9a; font-style: italic; font-size: 0.55rem; }}
    .dp-empty {{ color: #9aaa9a; font-size: 0.6rem; padding: 0.3rem; font-style: italic; font-family: 'DM Sans', sans-serif; }}
    .vb-time {{ font-family: 'DM Mono', monospace; font-size: 0.58rem; color: #5a7a5a; }}
    .vb-tag {{ background: #e8f5e1; color: #2d6b1a; padding: 0.05rem 0.35rem; border-radius: 3px; font-size: 0.6rem; font-weight: 600; }}
    .kitchen-val {{ background: #c97b1a; border-radius: 4px; padding: 0.1rem 0.4rem; color: #1a2e44; font-weight: 800; font-size: 0.65rem; display: inline-block; }}
    .resp-label {{ font-size: 0.58rem; color: #6BBF4E; font-weight: 600; }}
    .resp-val {{ font-size: 0.62rem; color: #2d3d2d; }}
    .fact-bar {{ background: #f0f8ee; border-top: 2px solid #c8e0c8; padding: 0.4rem 1.5rem; font-size: 0.72rem; color: #3a5a3a; display: flex; align-items: center; gap: 0.75rem; font-family: 'DM Sans', sans-serif; }}
    .fact-label {{ color: #e8a125; font-weight: 700; font-size: 0.65rem; letter-spacing: 0.08em; text-transform: uppercase; white-space: nowrap; }}
    .pc-wrap {{ overflow-x: auto; }}
    .pc-table {{ min-width: 900px; }}
    .slot {{ text-align: center; font-family: 'DM Mono', monospace; font-size: 0.55rem; }}
    .slot.filled {{ background: #e8f5e1; color: #2d6b1a; font-weight: 600; }}
    </style>

    <div class="display-header">
      <div>
        <div class="display-header-title">Cowandilla Learning Centre &mdash; Daily Bulletin</div>
        <div class="display-header-date">{today.strftime("%A %-d %B %Y").upper()}</div>
      </div>
      <div style="display:flex;align-items:center;gap:1.5rem;">
        <div class="display-header-time" id="live-clock">--:-- --</div>
        <a href="/?quickadd=true" style="background:rgba(107,191,78,0.2);border:1px solid rgba(107,191,78,0.5);color:#6BBF4E;font-family:'DM Sans',sans-serif;font-size:0.68rem;font-weight:600;padding:0.3rem 0.85rem;border-radius:6px;text-decoration:none;letter-spacing:0.05em;">📝 Quick Add</a><a href="/?from_display=true" style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.18);color:rgba(255,255,255,0.55);font-family:'DM Sans',sans-serif;font-size:0.68rem;font-weight:600;padding:0.3rem 0.85rem;border-radius:6px;text-decoration:none;letter-spacing:0.05em;">✏️ Staff Access</a>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Day navigation (display mode) ──
    prev_day = today - timedelta(days=1)
    next_day = today + timedelta(days=1)
    dn_prev, dn_label, dn_next, dn_today = st.columns([1, 4, 1, 1])
    with dn_prev:
        if st.button(f"← {prev_day.strftime('%a %-d %b')}", key="dn_prev", use_container_width=True):
            st.session_state.display_date = prev_day
            st.rerun()
    with dn_label:
        st.markdown(
            f'<div style="text-align:center;color:#2d7d4f;font-size:0.75rem;font-weight:700;'
            f'font-family:DM Mono,monospace;letter-spacing:0.08em;padding:0.45rem 0;">'
            f'VIEWING: {today.strftime("%A %-d %B %Y").upper()}</div>',
            unsafe_allow_html=True)
    with dn_next:
        if st.button(f"{next_day.strftime('%a %-d %b')} →", key="dn_next", use_container_width=True):
            st.session_state.display_date = next_day
            st.rerun()
    with dn_today:
        if st.button("Today", key="dn_today", use_container_width=True):
            st.session_state.display_date = date.today()
            st.rerun()

    # ── Helper for table rows ──
    def tbl_rows(rows, keys):
        filtered = [r for r in rows if any(r.get(k,"") for k in keys)]
        if not filtered:
            return '<tr><td colspan="20" class="dt-em">None today</td></tr>'
        return "".join(["<tr>" + "".join([f"<td>{r.get(k,'')}</td>" for k in keys]) + "</tr>" for r in filtered])

    # ── Staff Notices — FIRST on display ──
    d_notices = load_notices(for_date=today)
    if d_notices:
        n_parts = []
        for n in d_notices:
            cat = n.get("category","General")
            nc  = NOTICE_CATS.get(cat, NOTICE_CATS["General"])
            n_parts.append(
                f'<span style="background:{nc["bg"]};color:{nc["color"]};font-size:0.58rem;'
                f'font-weight:700;text-transform:uppercase;letter-spacing:0.06em;'
                f'padding:0.1rem 0.4rem;border-radius:10px;">{cat}</span> '
                f'<strong style="color:#1a2e44;font-size:0.65rem;">{n.get("title","")}</strong>'
                f'<span style="color:#4a6a4a;font-size:0.62rem;"> — {n.get("body","")}</span>'
                f'<span style="color:#7a9a7a;font-size:0.58rem;"> · {n.get("submitted_by","")}</span>'
            )
        n_html = "<br>".join(n_parts)
        st.markdown(
            f'<div class="dp"><div class="dp-header green">📝 Staff Notices</div>'
            f'<div class="dp-body"><div style="font-family:DM Sans,sans-serif;line-height:1.8;">{n_html}</div></div></div>',
            unsafe_allow_html=True)

    # ── ROW 1: 5 columns ──
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([2,2,2.5,1.5,2])

    with r1c1:
        st.markdown(f"""
        <div class="dp"><div class="dp-header green">🙅 Staff & Student Absent</div><div class="dp-body">
        <table class="dt"><tr><th>Staff</th><th>TRT</th><th>Student</th><th>Program</th><th>Reason</th></tr>
        {tbl_rows(d_data.get("staff_absent",[]), ["Staff Absence","TRT","Student Absence","Program","Reason"])}
        </table></div></div>
        """, unsafe_allow_html=True)

    with r1c2:
        st.markdown(f"""
        <div class="dp"><div class="dp-header blue">🚌 Excursions</div><div class="dp-body">
        <table class="dt"><tr><th>Program</th><th>Staff</th><th>Depart</th><th>Return</th><th>Location</th></tr>
        {tbl_rows(d_data.get("excursions",[]), ["Program","Staff Member","Time Departing","Time Returning","Location"])}
        </table></div></div>
        """, unsafe_allow_html=True)

    with r1c3:
        _sched_mtgs = load_scheduled_meetings(today)
        _all_mtgs = list(d_data.get("staff_meetings") or []) + _sched_mtgs
        st.markdown(f"""
        <div class="dp"><div class="dp-header navy">🤝 Staff Meetings</div><div class="dp-body">
        <table class="dt"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>
        {tbl_rows(_all_mtgs, ["Type","Staff Member","Location","Time Departing","Time Returning","Student"])}
        </table></div></div>
        """, unsafe_allow_html=True)

    with r1c4:
        st.markdown(f"""
        <div class="dp"><div class="dp-header brown">📥 Entry Meetings</div><div class="dp-body">
        <table class="dt"><tr><th>Time</th><th>Program</th><th>Student</th></tr>
        {tbl_rows(d_data.get("entry_meetings",[]), ["Time","Program","Student"])}
        </table></div></div>
        """, unsafe_allow_html=True)

    with r1c5:
        # Staff Responsibilities
        kitchen = sr.get("kitchen_duties","") or "—"
        pd_focus = sr.get("meeting_pd_focus","") or "—"
        chair = sr.get("chair","") or "—"
        minutes = sr.get("minutes","") or "—"
        st.markdown(f"""
        <div class="dp"><div class="dp-header amber">⭐ Staff Responsibilities</div><div class="dp-body">
        <div style="margin-bottom:0.35rem;"><span class="kitchen-val">🍳 Kitchen: {kitchen}</span></div>
        <div style="margin-bottom:0.2rem;"><span class="resp-label">📌 PD Focus</span><br><span class="resp-val">{pd_focus}</span></div>
        <div style="margin-bottom:0.2rem;"><span class="resp-label">🪑 Chair</span><br><span class="resp-val">{chair}</span></div>
        <div><span class="resp-label">📝 Minutes</span><br><span class="resp-val">{minutes}</span></div>
        </div></div>
        """, unsafe_allow_html=True)

    # ── ROW 2: Travel + Vehicle + NIT ──
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns([2,2,2,1.5,1])

    with r2c1:
        st.markdown(f"""
        <div class="dp"><div class="dp-header blue">🟦 JP – Travel</div><div class="dp-body">
        <table class="dt"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>
        {tbl_rows(d_data.get("travel_jp",[]), ["Student","Transport To","Transport From","Times"])}
        </table></div></div>
        """, unsafe_allow_html=True)

    with r2c2:
        st.markdown(f"""
        <div class="dp"><div class="dp-header purple">🟣 PY – Travel</div><div class="dp-body">
        <table class="dt"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>
        {tbl_rows(d_data.get("travel_py",[]), ["Student","Transport To","Transport From","Times"])}
        </table></div></div>
        """, unsafe_allow_html=True)

    with r2c3:
        st.markdown(f"""
        <div class="dp"><div class="dp-header slate">🟫 SY – Travel</div><div class="dp-body">
        <table class="dt"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>
        {tbl_rows(d_data.get("travel_sy",[]), ["Student","Transport To","Transport From","Times"])}
        </table></div></div>
        """, unsafe_allow_html=True)

    with r2c4:
        vb_list = d_data.get("vehicle_bookings", [])
        # Backward compat: old dict format
        if isinstance(vb_list, dict):
            _conv = []
            for _t, _v in vb_list.items():
                if _v.get("van",""): _conv.append({"vehicle":"Van","booker":_v["van"],"whole_day":True,"start_time":"","end_time":""})
                if _v.get("kia",""): _conv.append({"vehicle":"Kia","booker":_v["kia"],"whole_day":True,"start_time":"","end_time":""})
            vb_list = _conv
        if vb_list:
            def _dm_vb_time(b):
                if b.get("whole_day", True):
                    return "All day"
                return f"{b.get('start_time','?')} – {b.get('end_time','?')}"
            vb_rows_html = "".join([
                f'<tr><td class="vb-time">{"🚐 Van" if b.get("vehicle","")=="Van" else "🚙 Kia"}</td>'
                f'<td><span class="vb-tag">{b.get("booker","")}</span></td>'
                f'<td style="font-size:0.58rem;color:#6BBF4E;">{_dm_vb_time(b)}</td></tr>'
                for b in vb_list if b.get("booker","")
            ])
        else:
            vb_rows_html = '<tr><td colspan="3" class="dt-em">No bookings today</td></tr>'
        st.markdown(f"""
        <div class="dp"><div class="dp-header navy">🚗 Vehicles</div><div class="dp-body">
        <table class="dt"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>{vb_rows_html}</table>
        </div></div>
        """, unsafe_allow_html=True)

    with r2c5:
        nit = d_data.get("nit_booking","") or '<span class="dp-empty">None today</span>'
        msgs = d_data.get("additional_messages",[])
        msg_rows = tbl_rows(msgs, ["Staff Member","Visitor","Reason","Arriving/Departing"])
        st.markdown(f"""
        <div class="dp"><div class="dp-header green">📋 NIT Booking</div><div class="dp-body">
        <p style="font-size:0.62rem;color:#c8d8c8;margin:0;line-height:1.4;">{nit}</p>
        </div></div>
        <div class="dp"><div class="dp-header slate">💬 Messages</div><div class="dp-body">
        <table class="dt"><tr><th>Staff</th><th>Visitor</th><th>Reason</th><th>Arr/Dep</th></tr>{msg_rows}</table>
        </div></div>
        """, unsafe_allow_html=True)

    # ── ROW 3: Program Changes (full width) ──
    pc_rows = d_data.get("program_changes", [])
    pc_active = [r for r in pc_rows if isinstance(r,dict) and r.get("change_reason","")]
    if pc_active:
        pc_html_parts = []
        for pc in pc_active:
            reason   = pc.get("change_reason","")
            absent   = pc.get("staff_absent","")
            trt      = pc.get("trt", False)
            trt_nm   = pc.get("trt_name","")
            smember  = pc.get("staff_member","")
            rel      = pc.get("release_type","")

            meta_parts = []
            if reason:  meta_parts.append(f"<strong style='color:#6BBF4E;'>{reason}</strong>")
            if absent:  meta_parts.append(f"Absent: <strong>{absent}</strong>")
            if trt and trt_nm: meta_parts.append(f"TRT: {trt_nm}")
            if smember: meta_parts.append(f"Staff: {smember}")
            if rel:     meta_parts.append(f"Role: {rel}")

            tt_html = _pc_timetable_html(pc, dark=True)
            pc_html_parts.append(
                f'<div style="margin-bottom:8px;">'
                f'<div style="font-size:0.6rem;margin-bottom:4px;color:#a8c8a8;">{" · ".join(meta_parts)}</div>'
                f'{tt_html if tt_html else "<span style=\'color:#3a5a3a;font-size:0.6rem;\'>No timetable entered</span>"}'
                f'</div>'
            )
        st.markdown(
            f'<div class="dp"><div class="dp-header green">📊 Program Changes</div>'
            f'<div class="dp-body">{"".join(pc_html_parts)}</div></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="dp"><div class="dp-header green">📊 Program Changes</div>'
            '<div class="dp-body"><span class="dt-em">No program changes today</span></div></div>',
            unsafe_allow_html=True)

    # ── Live clock JS (Adelaide time) — must use components to run JS ──
    import streamlit.components.v1 as components
    components.html("""
    <script>
    (function() {
      function updateClock() {
        var opts = { timeZone: 'Australia/Adelaide', hour: 'numeric', minute: '2-digit', hour12: true };
        var timeStr = new Date().toLocaleTimeString('en-AU', opts).toUpperCase();
        // Walk up to parent frames to find the element
        var el = window.parent.document.getElementById('live-clock');
        if (el) el.textContent = timeStr;
      }
      updateClock();
      setInterval(updateClock, 1000);
    })();
    </script>
    """, height=0)

    # ── Fun fact footer ──
    st.markdown(f"""
    <div class="fact-bar">
      <span class="fact-label">💡 Fun Fact</span>
      <span>{fun if fun else "No fun fact entered for today"}</span>
    </div>
    """, unsafe_allow_html=True)

    st.stop()


# ══════════════════════════════════════════════════════════════
# QUICK ADD MODE — Standalone form (no tabs, no login needed)
# Access via: your-app-url/?quickadd=true
# ══════════════════════════════════════════════════════════════
if params.get("quickadd") == "true":
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: #f0f7eb !important; }
    .main .block-container { padding: 2rem 2rem 3rem !important; max-width: 620px !important; margin: 0 auto !important; }
    [data-testid="stHeader"] { display: none; }
    #MainMenu, footer, .stDeployButton { display: none; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;
    padding:1.5rem 2rem;margin-bottom:1.5rem;text-align:center;color:white;">
      <div style="font-size:2rem;margin-bottom:0.3rem;">📝</div>
      <div style="font-size:1.3rem;font-weight:700;margin-bottom:0.25rem;">Staff Quick Notice</div>
      <div style="font-size:0.85rem;opacity:0.85;">Cowandilla Learning Centre · Daily Bulletin</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("qa_standalone_form", clear_on_submit=True):
        qa_name  = st.text_input("Your name *", placeholder="e.g. Sarah")
        qa_cat   = st.selectbox("Category *", list(NOTICE_CATS.keys()),
                                format_func=lambda x: f"{NOTICE_CATS[x]['emoji']} {x}")
        qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3")
        qa_body  = st.text_area("Details (optional)", placeholder="Any extra info staff need to know…", height=110)
        qa_date  = st.date_input("For which day?", value=date.today())
        qa_ok    = st.form_submit_button("📢 Post Notice to Bulletin", type="primary", use_container_width=True)

        if qa_ok:
            if not qa_name.strip():
                st.warning("Please enter your name.")
            elif not qa_title.strip():
                st.warning("Please enter a title.")
            else:
                save_notice({
                    "submitted_by": qa_name.strip(),
                    "category":     qa_cat,
                    "title":        qa_title.strip(),
                    "body":         qa_body.strip(),
                    "notice_date":  str(qa_date),
                })
                st.success(f"✅ Notice posted for {qa_date.strftime('%-d %B')}! It's now live on the bulletin.")
                st.balloons()

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;">'
        '<a href="/" style="font-size:0.82rem;color:#4a8f33;font-weight:600;text-decoration:none;">← Back to full bulletin</a>'
        '&nbsp;&nbsp;|&nbsp;&nbsp;'
        '<a href="/?display=true" style="font-size:0.82rem;color:#4a8f33;font-weight:600;text-decoration:none;">Staff room display →</a>'
        '</div>',
        unsafe_allow_html=True)

    # Show today's notices below form
    qa_today = load_notices(for_date=date.today())
    if qa_today:
        st.markdown(f"**Posted today ({date.today().strftime('%-d %B')}):**")
        for n in qa_today:
            cat = n.get("category","General")
            nc  = NOTICE_CATS.get(cat, NOTICE_CATS["General"])
            st.markdown(
                f'<div style="background:white;border-radius:10px;border-left:4px solid {nc["color"]};'
                f'padding:0.7rem 1rem;margin-bottom:0.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
                f'<span style="background:{nc["bg"]};color:{nc["color"]};font-size:0.65rem;font-weight:700;'
                f'text-transform:uppercase;padding:0.15rem 0.5rem;border-radius:20px;">{nc["emoji"]} {cat}</span>'
                f'<span style="font-size:0.7rem;color:#9ab09a;margin-left:0.5rem;">from {n.get("submitted_by","")}</span>'
                f'<div style="font-size:0.9rem;font-weight:700;color:#1a2e44;margin:0.3rem 0 0.15rem;">{n.get("title","")}</div>'
                f'<div style="font-size:0.82rem;color:#3a4a3a;">{n.get("body","") or ""}</div>'
                f'</div>',
                unsafe_allow_html=True)

    st.stop()


# ── TOP NAV ───────────────────────────────────────────────────
edit = st.session_state.edit_mode and st.session_state.authenticated

auth_badge = ""
if st.session_state.authenticated:
    if edit:
        auth_badge = '<span class="nav-badge edit">✏️ Edit Mode</span>'
    else:
        auth_badge = '<span class="nav-badge">✅ Staff</span>'
else:
    auth_badge = ''

st.markdown(f"""
<div class="top-nav">
  <div class="top-nav-left">
    <div class="top-nav-logo">CLC</div>
    <div>
      <div class="top-nav-title">Daily Bulletin</div>
      <div class="top-nav-sub">Cowandilla Learning Centre</div>
    </div>
  </div>
  <div class="top-nav-right">
    {auth_badge}
  </div>
</div>
""", unsafe_allow_html=True)

# ── CURRENT DATE + DATA ────────────────────────────────────────
current_date = st.session_state.selected_date
bulletin_data = load_bulletin(current_date)

# ── PAGE ROUTING ───────────────────────────────────────────────
# Top-level tabs
page_tab, quickadd_tab, archive_tab, login_tab = st.tabs(["📋 Bulletin", "📝 Quick Add", "🗂️ Archive", "🔐 Staff"])

# ══════════════════════════════════════════════════════════════
# TAB: BULLETIN
# ══════════════════════════════════════════════════════════════
with page_tab:

    # ── From display: show quick login banner ──
    if st.query_params.get("from_display") == "true" and not st.session_state.authenticated:
        st.markdown("""
        <div style="background:#1a2e44;border-left:4px solid #6BBF4E;padding:0.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:1rem;display:flex;align-items:center;gap:1rem;">
          <span style="font-size:1.2rem;">🔐</span>
          <span style="color:white;font-size:0.85rem;">Enter your staff password below to edit today's bulletin, then save to return to the display screen.</span>
        </div>
        """, unsafe_allow_html=True)
        pw_col, btn_col, back_col = st.columns([2,1,1])
        with pw_col:
            quick_pw = st.text_input("Staff Password", type="password", key="quick_pw", label_visibility="collapsed", placeholder="Enter staff password...")
        with btn_col:
            if st.button("🔓 Login", type="primary", use_container_width=True):
                if quick_pw == ADMIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.edit_mode = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
        with back_col:
            st.markdown('<a href="/?display=true" style="display:block;text-align:center;background:#eef1f4;color:#1a2e44;font-weight:600;font-size:0.85rem;padding:0.5rem;border-radius:8px;text-decoration:none;">↩️ Back to Display</a>', unsafe_allow_html=True)
        st.markdown("---")

    # ── Hero header ──
    week = week_dates(current_date)
    day_pills = ""
    for d in week:
        active = "active" if d == current_date else ""
        today_cls = "today" if d == date.today() else ""
        day_pills += f'<span class="day-pill {active} {today_cls}" data-date="{d}">{d.strftime("%a %-d %b")}</span>'

    fun_fact_html = ""
    import html as _html
    fact = bulletin_data.get("fun_fact","")
    # Strip any accidentally stored HTML tags and re-escape for safe display
    import re as _re
    fact_clean = _html.escape(_re.sub(r'<[^>]+>', '', fact)).strip()
    if fact_clean:
        fun_fact_html = (
            '<div style="background:rgba(255,255,255,0.15);backdrop-filter:blur(8px);'
            'border:1px solid rgba(255,255,255,0.2);border-radius:12px;'
            'padding:0.65rem 1rem;max-width:480px;">'
            '<div style="font-size:0.65rem;color:rgba(255,255,255,0.6);'
            'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.2rem;">💡 Fun Fact</div>'
            f'<div style="font-size:0.85rem;color:white;font-weight:500;line-height:1.4;">{fact_clean}</div>'
            '</div>'
        )

    st.markdown(f"""
    <div class="bulletin-hero">
      <div class="bulletin-hero-inner">
        <div>
          <div class="bulletin-date-label">{term_label(current_date)}</div>
          <div class="bulletin-date-main">{current_date.strftime("%A %-d %B")}</div>
          <div class="bulletin-date-sub">{current_date.strftime("%Y")}</div>
        </div>
        {fun_fact_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Week day selector with week navigation ──
    st.markdown('<div style="background:white;border-bottom:2px solid #e8f0e3;padding:0.4rem 1rem 0;">', unsafe_allow_html=True)

    # Week navigation row
    nav_left, nav_mid, nav_right = st.columns([1, 4, 1])
    with nav_left:
        prev_monday = week[0] - timedelta(days=7)
        if st.button("← Prev Week", key="prev_week", use_container_width=True):
            st.session_state.selected_date = prev_monday
            st.rerun()
    with nav_mid:
        week_label_str = f"Week of {week[0].strftime('%-d %b')} – {week[-1].strftime('%-d %b %Y')}"
        is_this_week = date.today() in week
        if is_this_week:
            week_label_str += " · This Week"
        st.markdown(
            f'<div style="text-align:center;padding:0.45rem 0;font-size:0.78rem;font-weight:600;'
            f'color:{"#4a8f33" if is_this_week else "#5a6e5a"};">{week_label_str}</div>',
            unsafe_allow_html=True,
        )
    with nav_right:
        next_monday = week[0] + timedelta(days=7)
        if st.button("Next Week →", key="next_week", use_container_width=True):
            st.session_state.selected_date = next_monday
            st.rerun()

    # Day buttons
    day_cols = st.columns(5)
    for i, d in enumerate(week):
        with day_cols[i]:
            is_current = d == current_date
            is_today   = d == date.today()
            label = d.strftime("%a %-d %b") + (" ◉" if is_today else "")
            btn_type = "primary" if is_current else "secondary"
            if st.button(label, key=f"day_{d}", use_container_width=True, type=btn_type):
                st.session_state.selected_date = d
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Edit controls ──
    ctrl_cols = st.columns([1, 1, 1, 3, 1])
    if st.session_state.authenticated:
        with ctrl_cols[0]:
            if st.button("✏️ Edit" if not edit else "👁️ View", type="primary" if not edit else "secondary", use_container_width=True):
                st.session_state.edit_mode = not st.session_state.edit_mode
                st.session_state.show_inline_login = False
                st.rerun()
        with ctrl_cols[1]:
            if edit:
                if st.button("💾 Save", type="primary", use_container_width=True):
                    st.session_state["_pending_save"] = True
        with ctrl_cols[2]:
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.edit_mode = False
                st.rerun()
    else:
        with ctrl_cols[0]:
            if st.button("🔐 Staff Login", type="secondary", use_container_width=True):
                st.session_state.show_inline_login = not st.session_state.get("show_inline_login", False)
                st.rerun()

    with ctrl_cols[4]:
        st.markdown(
            '<a href="/?display=true" target="_blank" style="display:block;text-align:center;'
            'background:#1a2e44;color:white;font-weight:600;font-size:0.8rem;'
            'padding:0.45rem 0.75rem;border-radius:8px;text-decoration:none;white-space:nowrap;">'
            '📺 Staff Room View</a>',
            unsafe_allow_html=True
        )

    # ── Inline login panel ──
    if not st.session_state.authenticated and st.session_state.get("show_inline_login", False):
        with st.container():
            st.markdown('<div style="background:#f0f7eb;border:1.5px solid #6BBF4E;border-radius:10px;padding:1rem 1.25rem;margin:0.5rem 0 0.75rem;">', unsafe_allow_html=True)
            lc1, lc2, lc3 = st.columns([3, 1, 1])
            with lc1:
                quick_pw = st.text_input("Staff password", type="password", key="inline_pw", label_visibility="collapsed", placeholder="Enter staff password…")
            with lc2:
                if st.button("🔓 Login", type="primary", use_container_width=True, key="inline_login_btn"):
                    if quick_pw == ADMIN_PASSWORD:
                        st.session_state.authenticated = True
                        st.session_state.edit_mode = True
                        st.session_state.show_inline_login = False
                        st.rerun()
                    else:
                        st.error("Incorrect password")
            with lc3:
                if st.button("Cancel", type="secondary", use_container_width=True, key="inline_cancel"):
                    st.session_state.show_inline_login = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="content-area">', unsafe_allow_html=True)

    # ══ STAFF NOTICES — shown first on admin page ═══════════════════════════
    _admin_notices = load_notices(for_date=current_date)
    if _admin_notices or edit:
        st.markdown('<div class="section-card"><div class="section-card-header green"><h3>📝 Staff Notices</h3></div><div class="section-card-body">', unsafe_allow_html=True)
        if _admin_notices:
            for _n in _admin_notices:
                _cat = _n.get("category","General")
                _nc  = NOTICE_CATS.get(_cat, NOTICE_CATS["General"])
                _nid = _n.get("id","")
                _nc1, _nc2 = st.columns([9,1])
                with _nc1:
                    st.markdown(
                        f'<div style="background:white;border-radius:10px;border-left:4px solid {_nc["color"]};'
                        f'padding:0.75rem 1rem;margin-bottom:0.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
                        f'<div style="margin-bottom:0.2rem;">'
                        f'<span style="background:{_nc["bg"]};color:{_nc["color"]};font-size:0.65rem;font-weight:700;'
                        f'text-transform:uppercase;letter-spacing:0.08em;padding:0.15rem 0.5rem;border-radius:20px;">'
                        f'{_nc["emoji"]} {_cat}</span>'
                        f'<span style="font-size:0.7rem;color:#9ab09a;margin-left:0.5rem;">from {_n.get("submitted_by","")}</span>'
                        f'</div>'
                        f'<div style="font-size:0.9rem;font-weight:700;color:#1a2e44;margin:0.3rem 0 0.2rem;">{_n.get("title","")}</div>'
                        f'<div style="font-size:0.82rem;color:#3a4a3a;line-height:1.5;">{_n.get("body","")}</div>'
                        f'</div>',
                        unsafe_allow_html=True)
                with _nc2:
                    if edit:
                        st.write("")
                        if st.button("🗑️", key=f"top_del_n_{_nid}", help="Delete notice"):
                            delete_notice(_nid); st.rerun()
        else:
            st.markdown('<div style="text-align:center;padding:1rem;color:#9ab09a;font-size:0.85rem;">No notices today — staff can add via the 📝 Quick Add tab</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # SECTION TABS
    # ═══════════════════════════════════════════════════════
    s1, s2, s3, s4 = st.tabs(["👥 Staff & Meetings", "🚌 Travel & Vehicles", "📌 Responsibilities & NIT", "📊 Program Changes"])

    # ─────────────────────────────────────────────────────
    # TAB S1: Staff & Meetings
    # ─────────────────────────────────────────────────────
    with s1:
        if edit:
            auto_fact = daily_fun_fact(current_date)
            current_fact = bulletin_data.get("fun_fact", "").strip()
            fc1, fc2 = st.columns([5, 1])
            with fc1:
                new_fact = st.text_input(
                    "💡 Fun Fact of the Day",
                    value=current_fact if current_fact else auto_fact,
                    placeholder="Auto-filled with today's Australian fun fact…",
                )
            with fc2:
                st.markdown("<div style='padding-top:1.85rem;'>", unsafe_allow_html=True)
                if st.button("🎲 New", key="new_fact", help="Replace with today's auto fact", use_container_width=True):
                    bulletin_data["fun_fact"] = auto_fact
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            bulletin_data["fun_fact"] = new_fact

        col_left, col_right = st.columns(2)

        with col_left:
            # Staff & Student Absent
            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>🙅 Staff & Student Absent</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                import pandas as pd
                df = pd.DataFrame(bulletin_data["staff_absent"])
                edited = st.data_editor(df, key="sa_editor", hide_index=True, use_container_width=True, num_rows="dynamic",
                    column_config={c: st.column_config.TextColumn(c) for c in df.columns})
                bulletin_data["staff_absent"] = edited.to_dict("records")
            else:
                rows = bulletin_data["staff_absent"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Staff Absence</th><th>TRT</th><th>Student</th><th>Program</th><th>Reason</th></tr>' +
                        "".join([f"<tr><td>{r.get('Staff Absence','')}</td><td>{r.get('TRT','')}</td><td>{r.get('Student Absence','')}</td><td>{r.get('Program','')}</td><td>{r.get('Reason','')}</td></tr>"
                        for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">✅</div>No absences today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            # Excursions
            st.markdown('<div class="section-card"><div class="section-card-header blue"><h3>🚌 Excursions</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["excursions"])
                edited = st.data_editor(df, key="ex_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["excursions"] = edited.to_dict("records")
            else:
                rows = bulletin_data["excursions"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Program</th><th>Staff</th><th>Departing</th><th>Returning</th><th>Location</th></tr>' +
                        "".join([f"<tr><td>{r.get('Program','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Location','')}</td></tr>"
                        for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">🗺️</div>No excursions today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            # Entry Meetings
            st.markdown('<div class="section-card"><div class="section-card-header brown"><h3>📥 Entry Meetings – Annette</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["entry_meetings"])
                edited = st.data_editor(df, key="em_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["entry_meetings"] = edited.to_dict("records")
            else:
                rows = bulletin_data["entry_meetings"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Time</th><th>Program</th><th>Student</th></tr>' +
                        "".join([f"<tr><td>{r.get('Time','')}</td><td>{r.get('Program','')}</td><td>{r.get('Student','')}</td></tr>"
                        for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">📭</div>No entry meetings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

        with col_right:
            # Staff Meetings
            st.markdown('<div class="section-card"><div class="section-card-header navy"><h3>🤝 Staff Meetings</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["staff_meetings"])
                edited = st.data_editor(df, key="sm_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["staff_meetings"] = edited.to_dict("records")
            else:
                rows = bulletin_data["staff_meetings"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>' +
                        "".join([f"<tr><td>{r.get('Type','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Location','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Student','')}</td></tr>"
                        for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">📅</div>No staff meetings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            # Additional Staff Messages
            st.markdown('<div class="section-card"><div class="section-card-header slate"><h3>💬 Additional Staff Messages</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["additional_messages"])
                edited = st.data_editor(df, key="msg_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["additional_messages"] = edited.to_dict("records")
            else:
                rows = bulletin_data["additional_messages"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Staff</th><th>Visitor</th><th>Reason</th><th>Arriving/Departing</th></tr>' +
                        "".join([f"<tr><td>{r.get('Staff Member','')}</td><td>{r.get('Visitor','')}</td><td>{r.get('Reason','')}</td><td>{r.get('Arriving/Departing','')}</td></tr>"
                        for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">💭</div>No additional messages</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────
    # TAB S2: Travel & Vehicles
    # ─────────────────────────────────────────────────────
    with s2:
        import pandas as pd
        jp_col, py_col, sy_col = st.columns(3)

        def render_travel_card(col, key, label, color):
            with col:
                st.markdown(f'<div class="section-card"><div class="section-card-header" style="background:{color};"><h3>{label}</h3></div><div class="section-card-body">', unsafe_allow_html=True)
                rows = bulletin_data[key]
                if edit:
                    df = pd.DataFrame(rows)
                    edited = st.data_editor(df, key=f"{key}_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                    bulletin_data[key] = edited.to_dict("records")
                else:
                    has_data = any(any(v for v in r.values()) for r in rows)
                    if has_data:
                        st.markdown('<table class="data-table"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>' +
                            "".join([f"<tr><td>{r.get('Student','')}</td><td>{r.get('Transport To','')}</td><td>{r.get('Transport From','')}</td><td>{r.get('Times','')}</td></tr>"
                            for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="empty-state"><div class="icon">🚐</div>No travel today</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)

        render_travel_card(jp_col, "travel_jp", "🟦 Junior Primary – Travel", "#4a7fb5")
        render_travel_card(py_col, "travel_py", "🟣 Primary Years – Travel", "#7a5bb5")
        render_travel_card(sy_col, "travel_sy", "🟫 Senior Years – Travel", "#8c6a4f")

        # Vehicle bookings
        st.markdown('<div class="section-card"><div class="section-card-header navy"><h3>🚗 Vehicle Bookings — Van & Kia</h3></div><div class="section-card-body">', unsafe_allow_html=True)
        vb_list = bulletin_data.get("vehicle_bookings", [])
        if isinstance(vb_list, dict):
            vb_list = []  # discard old format silently

        if edit:
            # ── Show existing bookings ──────────────────────────────
            if vb_list:
                st.markdown("**Current bookings:**")
                for _bi, _bk in enumerate(vb_list):
                    _bc1, _bc2, _bc3, _bc4 = st.columns([1,2,2,1])
                    with _bc1:
                        st.markdown(f"**{'🚐 Van' if _bk.get('vehicle','')=='Van' else '🚙 Kia'}**")
                    with _bc2:
                        st.markdown(f"**{_bk.get('booker','—')}**")
                    with _bc3:
                        if _bk.get("whole_day", True):
                            st.markdown("🕐 Whole day")
                        else:
                            st.markdown(f"🕐 {_bk.get('start_time','?')} – {_bk.get('end_time','?')}")
                    with _bc4:
                        if st.button("🗑️", key=f"vb_del_{_bi}", help="Remove booking"):
                            vb_list.pop(_bi)
                            bulletin_data["vehicle_bookings"] = vb_list
                            st.rerun()
                st.markdown("---")

            # ── Add a new booking ───────────────────────────────────
            st.markdown("**Add a booking:**")
            _av1, _av2, _av3 = st.columns([1,2,2])
            with _av1:
                _new_vehicle = st.selectbox("Vehicle", ["Van", "Kia"], key="vb_new_vehicle")
            with _av2:
                _new_booker = st.text_input("Booked by (name)", key="vb_new_booker", placeholder="e.g. Sarah")
            with _av3:
                _new_whole = st.checkbox("Whole day", value=True, key="vb_new_whole")
            if not _new_whole:
                _at1, _at2 = st.columns(2)
                with _at1:
                    _new_start = st.text_input("Start time", key="vb_new_start", placeholder="e.g. 9:30")
                with _at2:
                    _new_end = st.text_input("End time", key="vb_new_end", placeholder="e.g. 12:00")
            else:
                _new_start = ""
                _new_end = ""

            if st.button("➕ Add Booking", type="primary", key="vb_add_btn"):
                if _new_booker.strip():
                    vb_list.append({
                        "vehicle": _new_vehicle,
                        "booker": _new_booker.strip(),
                        "whole_day": _new_whole,
                        "start_time": _new_start.strip(),
                        "end_time": _new_end.strip(),
                    })
                    bulletin_data["vehicle_bookings"] = vb_list
                    st.rerun()
                else:
                    st.warning("Please enter a name for this booking.")

        else:
            # ── View mode ───────────────────────────────────────────
            if vb_list and any(b.get("booker","") for b in vb_list):
                def _vb_time(b):
                    if b.get("whole_day", True):
                        return "Whole day"
                    return f"{b.get('start_time','?')} – {b.get('end_time','?')}"
                rows_html = "".join([
                    f'<tr>'
                    f'<td>{"🚐 Van" if b.get("vehicle","")=="Van" else "🚙 Kia"}</td>'
                    f'<td><span class="vehicle-booking">{b.get("booker","")}</span></td>'
                    f'<td class="vehicle-time">{_vb_time(b)}</td>'
                    f'</tr>'
                    for b in vb_list if b.get("booker","")
                ])
                st.markdown(f'<table class="data-table"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>{rows_html}</table>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty-state"><div class="icon">🚗</div>No vehicle bookings today</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────
    # TAB S3: Responsibilities & NIT
    # ─────────────────────────────────────────────────────
    with s3:
        resp_col, nit_col = st.columns([1, 1])

        with resp_col:
            st.markdown('<div class="section-card"><div class="section-card-header amber"><h3>⭐ Staff Responsibilities</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            sr = bulletin_data["staff_responsibilities"]
            if edit:
                bulletin_data["staff_responsibilities"] = {
                    "kitchen_duties": st.text_input("🍳 Kitchen Duties", sr.get("kitchen_duties",""), key="sr_k"),
                    "meeting_pd_focus": st.text_input("📌 Staff Meeting PD Focus", sr.get("meeting_pd_focus",""), key="sr_pd"),
                    "chair": st.text_input("🪑 Meeting Chair", sr.get("chair",""), key="sr_c"),
                    "minutes": st.text_input("📝 Meeting Minutes", sr.get("minutes",""), key="sr_m"),
                }
            else:
                kitchen = sr.get("kitchen_duties","")
                st.markdown(f"""
                <table class="data-table">
                  <tr class="kitchen-row">
                    <td><span class="kitchen-badge">🍳 Kitchen</span></td>
                    <td><strong>{kitchen if kitchen else "—"}</strong></td>
                  </tr>
                  <tr><td>📌 PD Focus</td><td>{sr.get("meeting_pd_focus","") or "—"}</td></tr>
                  <tr><td>🪑 Chair</td><td>{sr.get("chair","") or "—"}</td></tr>
                  <tr><td>📝 Minutes</td><td>{sr.get("minutes","") or "—"}</td></tr>
                </table>""", unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

        with nit_col:
            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>📋 Additional NIT Booking</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                bulletin_data["nit_booking"] = st.text_area("NIT Booking Details", value=bulletin_data.get("nit_booking",""), height=120, label_visibility="collapsed")
            else:
                nit = bulletin_data.get("nit_booking","")
                if nit:
                    st.markdown(f'<p style="font-size:0.85rem;color:#2a3a2a;line-height:1.6;">{nit}</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">📋</div>No NIT bookings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────
    # TAB S4: Program Changes
    # ─────────────────────────────────────────────────────
    with s4:
        # ── Helper functions ────────────────────────────────────────────────
        ROLE_OPTIONS = ["", "JP", "PY", "SY", "NIT", "Lunch Cover", "Lunch Break", "Release", "Planning", "Other"]
        ROLE_COLORS  = {
            "JP": "#dbeafe", "PY": "#ede9fe", "SY": "#fef3c7",
            "NIT": "#f1f5f9", "Lunch Cover": "#fef9c3", "Lunch Break": "#cffafe",
            "Release": "#dcfce7", "Planning": "#fce7f3", "Other": "#f3f4f6",
        }

        def _load_changes(d):
            try:
                res = _get_sb().table("bulletin_changes").select("*").eq("bulletin_date", str(d)).order("created_at").execute()
                return res.data or []
            except Exception:
                return []

        def _save_change(d, entry):
            try:
                import json as _json
                data = {
                    "bulletin_date": str(d),
                    "reason": entry.get("reason", ""),
                    "staff_absent": entry.get("staff_absent", ""),
                    "has_trt": entry.get("has_trt", False),
                    "trt_name": entry.get("trt_name", ""),
                    "staff_rows": _json.dumps(entry.get("staff_rows", [])),
                }
                if entry.get("id"):
                    res = _get_sb().table("bulletin_changes").update(data).eq("id", entry["id"]).execute()
                else:
                    res = _get_sb().table("bulletin_changes").insert(data).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                st.error(f"Could not save change: {e}")
                return None

        def _delete_change(cid):
            try:
                _get_sb().table("bulletin_changes").delete().eq("id", cid).execute()
                return True
            except Exception as e:
                st.error(f"Delete failed: {e}")
                return False

        def _render_change_card(ch, ci):
            import json as _json
            reason = ch.get("reason", "")
            absent = ch.get("staff_absent", "")
            has_trt = ch.get("has_trt", False)
            trt_name = ch.get("trt_name", "")
            rows_raw = ch.get("staff_rows", [])
            rows = _json.loads(rows_raw) if isinstance(rows_raw, str) else (rows_raw or [])

            header = f"{'🙅 ' if reason == 'Staff Absence' else '📌 '}{reason}"
            if absent: header += f" — **{absent}**"
            if has_trt and trt_name: header += f" (TRT: {trt_name})"

            with st.container():
                st.markdown(f"""<div style="background:white;border:1.5px solid #e0e8dc;
                    border-left:4px solid #6BBF4E;border-radius:10px;
                    padding:0.75rem 1rem;margin-bottom:0.75rem;">
                    <div style="font-weight:700;color:#1a2e44;margin-bottom:0.5rem;">{header}</div>""",
                    unsafe_allow_html=True)
                for row in rows:
                    name = row.get("name", "")
                    blocks = row.get("blocks", [])
                    if blocks:
                        block_html = " &nbsp;·&nbsp; ".join([
                            f'<span style="background:{ROLE_COLORS.get(b.get("role",""), "#f3f4f6")};'
                            f'padding:1px 7px;border-radius:8px;font-size:0.72rem;font-weight:600;">'
                            f'{b.get("start","")}–{b.get("end","")} {b.get("role","")}'
                            f'{(" → " + b["person"]) if b.get("person") else ""}</span>'
                            for b in blocks if b.get("role") or b.get("start")
                        ])
                        if block_html:
                            st.markdown(f'<div style="margin:2px 0;font-size:0.82rem;color:#1a2e44;">'
                                       f'<b>{name}:</b> {block_html}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                if edit:
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("✏️ Edit", key=f"ch_edit_{ch['id']}_{ci}", use_container_width=True):
                            st.session_state["_pc_editing"] = dict(ch)
                            st.session_state["_pc_adding"] = False
                            st.rerun()
                    with dc2:
                        if st.button("🗑️ Delete", key=f"ch_del_{ch['id']}_{ci}", use_container_width=True):
                            _delete_change(ch["id"])
                            st.rerun()

        def _render_change_form(d, existing=None):
            import json as _json
            is_edit = existing is not None
            pfx = "_pcf"
            rows_key = f"{pfx}_rows"
            existing_rows = []
            if existing:
                rr = existing.get("staff_rows", [])
                existing_rows = _json.loads(rr) if isinstance(rr, str) else (rr or [])

            if rows_key not in st.session_state:
                st.session_state[rows_key] = existing_rows if existing_rows else [{"name": "", "blocks": []}]

            st.markdown(f"#### {'✏️ Edit' if is_edit else '➕ Add'} Program Change")
            st.markdown('<div style="background:#f8fdf6;border:1.5px solid #c8e0c8;border-radius:12px;padding:1rem 1.25rem;">', unsafe_allow_html=True)

            reason_opts = ["Staff Absence", "Site Need / Other"]
            r_idx = 1 if (existing or {}).get("reason","") == "Site Need / Other" else 0
            reason = st.radio("Reason", reason_opts, index=r_idx, key=f"{pfx}_reason", horizontal=True)

            staff_absent = ""
            has_trt = False
            trt_name = ""
            if reason == "Staff Absence":
                c1, c2 = st.columns(2)
                with c1:
                    staff_absent = st.text_input("Absent staff member *",
                        value=(existing or {}).get("staff_absent", ""), key=f"{pfx}_absent")
                with c2:
                    has_trt = st.checkbox("TRT coming in?",
                        value=bool((existing or {}).get("has_trt", False)), key=f"{pfx}_trt")
                if has_trt:
                    trt_name = st.text_input("TRT name",
                        value=(existing or {}).get("trt_name", ""), key=f"{pfx}_trt_name")

            st.markdown("---")
            st.markdown("**Timetable rows** — add each person whose day is affected:")
            rows = st.session_state[rows_key]

            for ri, row in enumerate(rows):
                st.markdown(f'<div style="background:white;border:1px solid #d8ead2;border-radius:8px;padding:0.75rem;margin-bottom:0.5rem;">', unsafe_allow_html=True)
                rc1, rc2, rc3 = st.columns([3, 2, 1])
                with rc1:
                    row["name"] = st.text_input("Staff / SSO name", value=row.get("name",""),
                        placeholder="e.g. Sarah Jones", key=f"{pfx}_r{ri}_name")
                with rc2:
                    autofill = st.selectbox("Autofill all time blocks with",
                        ROLE_OPTIONS, key=f"{pfx}_r{ri}_af")
                with rc3:
                    st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                    if st.button("▶ Fill", key=f"{pfx}_r{ri}_fill"):
                        if autofill:
                            for b in row["blocks"]: b["role"] = autofill
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                for bi, block in enumerate(row.get("blocks", [])):
                    bc1, bc2, bc3, bc4, bc5 = st.columns([2, 2, 2, 2, 1])
                    with bc1: block["start"] = st.text_input("Start", value=block.get("start",""), placeholder="9:00", key=f"{pfx}_r{ri}_b{bi}_s")
                    with bc2: block["end"]   = st.text_input("End",   value=block.get("end",""),   placeholder="10:30", key=f"{pfx}_r{ri}_b{bi}_e")
                    with bc3:
                        try: ridx = ROLE_OPTIONS.index(block.get("role",""))
                        except: ridx = 0
                        block["role"] = st.selectbox("Role", ROLE_OPTIONS, index=ridx, key=f"{pfx}_r{ri}_b{bi}_r")
                    with bc4: block["person"] = st.text_input("Detail (optional)", value=block.get("person",""), key=f"{pfx}_r{ri}_b{bi}_p")
                    with bc5:
                        st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                        if st.button("✕", key=f"{pfx}_r{ri}_b{bi}_del"):
                            row["blocks"].pop(bi); st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                ba1, ba2 = st.columns([2, 4])
                with ba1:
                    if st.button("➕ Add time block", key=f"{pfx}_r{ri}_ab"):
                        row["blocks"].append({"start":"","end":"","role":"","person":""}); st.rerun()
                with ba2:
                    if len(rows) > 1:
                        if st.button(f"🗑️ Remove row", key=f"{pfx}_r{ri}_dr"):
                            rows.pop(ri); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            if st.button("➕ Add another staff member", key=f"{pfx}_ar"):
                rows.append({"name":"","blocks":[]}); st.rerun()

            st.markdown("---")
            sa1, sa2 = st.columns(2)
            with sa1:
                if st.button("💾 Save Change", type="primary", key=f"{pfx}_save", use_container_width=True):
                    if reason == "Staff Absence" and not staff_absent.strip():
                        st.warning("Please enter the absent staff member's name.")
                    else:
                        entry = {
                            "id": (existing or {}).get("id"),
                            "reason": reason,
                            "staff_absent": staff_absent.strip(),
                            "has_trt": has_trt,
                            "trt_name": trt_name.strip() if has_trt else "",
                            "staff_rows": [r for r in rows if r.get("name") or r.get("blocks")],
                        }
                        saved = _save_change(d, entry)
                        if saved:
                            st.success("✅ Saved!")
                            for k in [k for k in st.session_state if k.startswith(pfx)]:
                                del st.session_state[k]
                            st.session_state["_pc_editing"] = None
                            st.session_state["_pc_adding"] = False
                            st.rerun()
            with sa2:
                if st.button("Cancel", key=f"{pfx}_cancel", use_container_width=True):
                    for k in [k for k in st.session_state if k.startswith(pfx)]:
                        del st.session_state[k]
                    st.session_state["_pc_editing"] = None
                    st.session_state["_pc_adding"] = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Main s4 content ─────────────────────────────────────────────────
        if "program_changes" in bulletin_data:
            # Migrate old format to new on first view
            old_pcs = bulletin_data.get("program_changes", [])
            if old_pcs and any(isinstance(e, dict) and e.get("change_reason") for e in old_pcs):
                st.info("📋 Old-format program changes exist in the bulletin data for this date. They are shown below for reference but new changes use the improved system.")
                for _old in old_pcs:
                    if isinstance(_old, dict) and _old.get("change_reason"):
                        st.markdown(f"- **{_old.get('change_reason','')}** — {_old.get('staff_absent','')}")

        _changes = _load_changes(current_date)

        if not _changes:
            st.markdown('<div style="text-align:center;padding:1.5rem;color:#9ab09a;font-size:0.85rem;background:#f8fdf6;border-radius:10px;">📭 No program changes recorded for this day.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(_changes)} change(s) recorded:**")
            for _ci, _ch in enumerate(_changes):
                _render_change_card(_ch, _ci)

        if edit:
            st.markdown("---")
            _editing = st.session_state.get("_pc_editing")
            _adding  = st.session_state.get("_pc_adding", False)
            if not _editing and not _adding:
                if st.button("➕ Add Program Change", type="primary", key="pc_add_new", use_container_width=True):
                    st.session_state["_pc_adding"] = True
                    st.session_state["_pc_editing"] = None
                    st.rerun()
            if _adding and not _editing:
                _render_change_form(current_date, existing=None)
            elif _editing:
                _render_change_form(current_date, existing=_editing)
    st.markdown('</div>', unsafe_allow_html=True)  # end content-area

    # ── BOTTOM SAVE BUTTONS ──────────────────────────────────────────────
    if edit:
        st.markdown('<div style="background:white;border-top:2px solid #e8f0e3;padding:1rem 2rem;position:sticky;bottom:0;z-index:100;display:flex;gap:1rem;align-items:center;">', unsafe_allow_html=True)
        bsv1, bsv2, bsv3 = st.columns([2, 2, 6])
        with bsv1:
            if st.button("💾 Save Bulletin", type="primary", use_container_width=True, key="bottom_save"):
                st.session_state["_pending_save"] = True
        with bsv2:
            if st.button("🚪 Discard & Exit", type="secondary", use_container_width=True, key="bottom_discard"):
                st.session_state.edit_mode = False
                st.rerun()
        with bsv3:
            st.markdown('<span style="font-size:0.78rem;color:#9ab09a;">💡 Changes are saved to the database and appear on the staff room display immediately.</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── PROGRAM CHANGES EXPORT / SHARE ──────────────────────────────────
    _export_pc = bulletin_data.get("program_changes", [])
    _export_active = [e for e in _export_pc if isinstance(e,dict) and e.get("change_reason","")]

    if _export_active:
        st.markdown("---")
        st.markdown(
            '<div style="background:white;border-radius:12px;border:1.5px solid #d8e8d4;'
            'padding:1.25rem 1.5rem;margin-bottom:1rem;">'
            '<div style="font-size:1rem;font-weight:700;color:#1a2e44;margin-bottom:0.25rem;">📤 Share Program Changes</div>'
            '<div style="font-size:0.8rem;color:#7a907a;">Copy as plain text for SMS · download as printable sheet for email or TRT</div>'
            '</div>',
            unsafe_allow_html=True)

        def _build_plain_text(entries, for_date):
            """Build a clean plain-text summary suitable for SMS or email body."""
            lines = []
            lines.append(f"CLC PROGRAM CHANGES — {for_date.strftime('%A %-d %B %Y').upper()}")
            lines.append("=" * 52)
            for idx, e in enumerate(entries, 1):
                reason  = e.get("change_reason","")
                absent  = e.get("staff_absent","")
                trt     = e.get("trt", False)
                trt_nm  = e.get("trt_name","")
                covering = e.get("covering","")
                program  = e.get("program","")
                smember  = e.get("staff_member","")
                rel      = e.get("release_type","")

                lines.append(f"\n[{idx}] {reason.upper()}")
                if absent:  lines.append(f"    Absent: {absent}")
                if trt:     lines.append(f"    TRT: {trt_nm or '(name not entered)'}")
                if covering: lines.append(f"    Covering: {covering}{' — ' + program if program else ''}")
                if smember: lines.append(f"    Staff: {smember} ({rel})")

                # TRT timetable
                ts = e.get("time_slots", {})
                if ts and any((v.get("value","") if isinstance(v,dict) else v) for v in ts.values()):
                    lines.append(f"    Timetable ({trt_nm or 'TRT'}):")
                    for slot in PC_TIME_SLOTS:
                        raw = ts.get(slot, {})
                        val = raw.get("value","") if isinstance(raw,dict) else str(raw)
                        person = raw.get("person","") if isinstance(raw,dict) else ""
                        if val:
                            person_str = ""
                            if val == "Lunch Cover" and person: person_str = f" → releasing {person}"
                            elif val == "Lunch Break" and person: person_str = f" ↩ covered by {person}"
                            elif person: person_str = f" ({person})"
                            lines.append(f"      {slot:>7}  {val}{person_str}")

                # Staff allocations
                for alloc in e.get("staff_allocations", []):
                    a_name = alloc.get("name","(Staff)")
                    a_norm = alloc.get("normal_prog","")
                    a_ts   = alloc.get("time_slots", {})
                    if not a_ts or not any((v.get("value","") if isinstance(v,dict) else v) for v in a_ts.values()):
                        continue
                    norm_str = f" [normally: {a_norm}]" if a_norm else ""
                    lines.append(f"    {a_name}{norm_str}:")
                    for slot in PC_TIME_SLOTS:
                        raw = a_ts.get(slot, {})
                        val = raw.get("value","") if isinstance(raw,dict) else str(raw)
                        person = raw.get("person","") if isinstance(raw,dict) else ""
                        if val:
                            person_str = ""
                            if val == "Lunch Cover" and person: person_str = f" → releasing {person}"
                            elif val == "Lunch Break" and person: person_str = f" ↩ covered by {person}"
                            elif person: person_str = f" ({person})"
                            lines.append(f"      {slot:>7}  {val}{person_str}")

            lines.append("\n" + "=" * 52)
            lines.append("Cowandilla Learning Centre · clcdailybulletin.streamlit.app")
            return "\n".join(lines)

        def _build_html_sheet(entries, for_date):
            """Build a self-contained printable HTML page."""
            COLORS = {
                "JP Cover":    ("#1d4ed8","#dbeafe"),
                "PY Cover":    ("#6d28d9","#ede9fe"),
                "SY Cover":    ("#92400e","#fef3c7"),
                "JP":          ("#1d4ed8","#dbeafe"),
                "PY":          ("#6d28d9","#ede9fe"),
                "SY":          ("#92400e","#fef3c7"),
                "Lunch Cover": ("#856404","#fff3cd"),
                "Lunch Break": ("#004085","#cce5ff"),
                "NIT":         ("#374151","#f3f4f6"),
                "Other":       ("#5b21b6","#f5f3ff"),
            }

            def slot_td(val, person, size="0.48rem"):
                c, bg = COLORS.get(val, ("#374151","#f9fafb")) if val else ("#ccc","#fff")
                disp = val if val else ""
                person_html = ""
                if person:
                    if val == "Lunch Cover":   person_html = f'<br><small style="font-size:0.85em;opacity:0.8;">→ {person}</small>'
                    elif val == "Lunch Break": person_html = f'<br><small style="font-size:0.85em;opacity:0.8;">↩ {person}</small>'
                    else:                      person_html = f'<br><small style="font-size:0.85em;opacity:0.8;">{person}</small>'
                return (f'<td style="background:{bg};color:{c};text-align:center;padding:2px 1px;'
                        f'font-size:{size};font-weight:600;border:1px solid #e5e7eb;word-break:break-word;overflow:hidden;">'
                        f'{disp}{person_html}</td>')

            def tt_table(name, normal_prog, ts):
                norm_str = f' <span style="font-weight:400;color:#6b7280;font-size:0.75em;">({normal_prog})</span>' if normal_prog else ""
                header = "".join([
                    f'<th style="background:#1a2e44;color:rgba(255,255,255,0.85);font-size:0.42rem;'
                    f'padding:2px 1px;text-align:center;border:1px solid #374151;word-break:break-all;">{s}</th>'
                    for s in PC_TIME_SLOTS])
                cells = "".join([slot_td(
                    (ts.get(s,{}).get("value","")  if isinstance(ts.get(s,{}),dict) else ts.get(s,"")),
                    (ts.get(s,{}).get("person","") if isinstance(ts.get(s,{}),dict) else ""),
                    size="0.48rem"
                ) for s in PC_TIME_SLOTS])
                return (
                    f'<div style="margin:6px 0 10px;">'
                    f'<div style="font-weight:700;font-size:0.8rem;color:#1a2e44;margin-bottom:3px;">👤 {name}{norm_str}</div>'
                    f'<table style="border-collapse:collapse;width:100%;table-layout:fixed;">'
                    f'<tr>{header}</tr><tr>{cells}</tr>'
                    f'</table></div>'
                )

            entries_html = ""
            for idx, e in enumerate(entries, 1):
                reason  = e.get("change_reason","")
                absent  = e.get("staff_absent","")
                trt     = e.get("trt", False)
                trt_nm  = e.get("trt_name","")
                covering = e.get("covering","")
                program  = e.get("program","")
                smember  = e.get("staff_member","")
                rel      = e.get("release_type","")

                meta_bits = []
                if absent:   meta_bits.append(f"<strong>Absent:</strong> {absent}")
                if trt:      meta_bits.append(f"<strong>TRT:</strong> {trt_nm or '(name TBC)'}")
                else:        meta_bits.append("<strong>No TRT</strong>")
                if covering: meta_bits.append(f"<strong>Covering:</strong> {covering}{' — '+program if program else ''}")
                if smember:  meta_bits.append(f"<strong>Staff:</strong> {smember} ({rel})")
                meta_html = " &nbsp;·&nbsp; ".join(meta_bits)

                timetables_html = ""
                ts = e.get("time_slots", {})
                if ts and any((v.get("value","") if isinstance(v,dict) else v) for v in ts.values()):
                    timetables_html += tt_table(trt_nm or "TRT", covering + (" — "+program if program else ""), ts)
                for alloc in e.get("staff_allocations", []):
                    a_ts = alloc.get("time_slots", {})
                    if a_ts and any((v.get("value","") if isinstance(v,dict) else v) for v in a_ts.values()):
                        timetables_html += tt_table(alloc.get("name","Staff"), alloc.get("normal_prog",""), a_ts)

                color = "#dc2626" if reason == "Staff Absence" else "#0e7490"
                entries_html += (
                    f'<div style="background:white;border:1.5px solid #e5e7eb;border-left:5px solid {color};'
                    f'border-radius:8px;padding:12px 14px;margin-bottom:14px;page-break-inside:avoid;">'
                    f'<div style="font-size:0.85rem;font-weight:800;color:{color};margin-bottom:4px;">'
                    f'Change {idx} — {reason}</div>'
                    f'<div style="font-size:0.78rem;color:#374151;margin-bottom:8px;">{meta_html}</div>'
                    f'{timetables_html}'
                    f'</div>'
                )

            legend_items = "".join([
                f'<span style="background:{bg};color:{c};padding:2px 8px;border-radius:10px;font-size:0.65rem;font-weight:600;">{label}</span>'
                for label, c, bg in [
                    ("JP/PY/SY Cover", "#1d4ed8", "#dbeafe"),
                    ("Lunch Cover",    "#856404", "#fff3cd"),
                    ("Lunch Break",    "#004085", "#cce5ff"),
                    ("Blank = no change", "#374151", "#f9fafb"),
                ]
            ])

            return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>CLC Program Changes — {for_date.strftime('%A %-d %B %Y')}</title>
<style>
  @page {{ size: A4 landscape; margin: 12mm 14mm; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f9fafb; margin: 0; padding: 16px; color: #1a2e44; }}
  @media print {{
    body {{ background: white; padding: 0; }}
    .no-print {{ display: none !important; }}
    .page {{ box-shadow: none; margin: 0; padding: 0; }}
  }}
  .page {{ width: 100%; max-width: 100%; background: white; border-radius: 8px;
           box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 20px 24px; box-sizing: border-box; }}
  h1 {{ font-size: 1rem; color: #1a2e44; margin: 0 0 2px; }}
  .subtitle {{ font-size: 0.75rem; color: #6b7280; margin-bottom: 12px; }}
  .legend {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }}
  table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
  th, td {{ overflow: hidden; word-break: break-word; }}
</style>
</head><body>
<div class="page">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;border-bottom:2px solid #e5e7eb;padding-bottom:12px;">
    <div>
      <h1>📊 Program Changes</h1>
      <div class="subtitle">Cowandilla Learning Centre &nbsp;·&nbsp; {for_date.strftime('%A %-d %B %Y')}</div>
    </div>
    <button class="no-print" onclick="window.print()" style="background:#1a2e44;color:white;border:none;padding:8px 16px;border-radius:6px;font-size:0.8rem;cursor:pointer;">🖨️ Print</button>
  </div>
  <div class="legend">{legend_items}</div>
  {entries_html}
  <div style="font-size:0.65rem;color:#9ca3af;margin-top:20px;text-align:center;border-top:1px solid #f3f4f6;padding-top:10px;">
    Generated from CLC Daily Bulletin · clcdailybulletin.streamlit.app
  </div>
</div>
</body></html>"""

        _plain = _build_plain_text(_export_active, current_date)
        _html  = _build_html_sheet(_export_active, current_date)

        _ex1, _ex2, _ex3 = st.columns([1,1,2])
        with _ex1:
            st.download_button(
                "📱 Download as Text (SMS/Email)",
                data=_plain,
                file_name=f"CLC_ProgramChanges_{current_date.strftime('%Y-%m-%d')}.txt",
                mime="text/plain",
                use_container_width=True,
                type="secondary",
            )
        with _ex2:
            st.download_button(
                "🖨️ Download Printable Sheet",
                data=_html,
                file_name=f"CLC_ProgramChanges_{current_date.strftime('%Y-%m-%d')}.html",
                mime="text/html",
                use_container_width=True,
                type="secondary",
            )
        with _ex3:
            st.markdown(
                '<div style="font-size:0.75rem;color:#7a907a;padding-top:0.5rem;">'
                '💡 <strong>Text file</strong> — paste into SMS or email body &nbsp;·&nbsp; '
                '<strong>Printable sheet</strong> — open in browser, then Print or Save as PDF to email/share'
                '</div>',
                unsafe_allow_html=True)

        # Preview
        with st.expander("👁️ Preview plain text (for SMS / email body)", expanded=False):
            st.code(_plain, language=None)

    # ── SAVE EXECUTION — runs here so all data_editors above have already
    # updated bulletin_data before we write to the database ──────────────
    if st.session_state.get("_pending_save"):
        st.session_state["_pending_save"] = False
        save_data = {k: v for k, v in bulletin_data.items() if k != "id"}
        db.save_bulletin(current_date, save_data)
        st.session_state.edit_mode = False
        st.success("✅ Bulletin saved!")
        if st.query_params.get("from_display") == "true":
            st.markdown('<meta http-equiv="refresh" content="2;url=/?display=true">', unsafe_allow_html=True)
            st.info("↩️ Returning to staff room display in 2 seconds...")
        st.rerun()



# ══════════════════════════════════════════════════════════════
# TAB: QUICK ADD
# ══════════════════════════════════════════════════════════════
with quickadd_tab:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;
    padding:1.5rem 2rem;margin-bottom:1.5rem;color:white;">
      <div style="font-size:1.3rem;font-weight:700;margin-bottom:0.3rem;">📝 Add a Staff Notice</div>
      <div style="font-size:0.85rem;opacity:0.85;">No password needed. Your notice will appear on today's bulletin
      and the staff room display screen straight away.</div>
    </div>
    """, unsafe_allow_html=True)

    qa_col, preview_col = st.columns([1, 1])

    with qa_col:
        with st.form("quick_add_form", clear_on_submit=True):
            qa_name = st.text_input("Your name *", placeholder="e.g. Sarah")
            qa_cat  = st.selectbox("Category *", list(NOTICE_CATS.keys()))
            qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3")
            qa_body  = st.text_area("Details", placeholder="Any additional info… (optional)", height=120)
            qa_date  = st.date_input("For which day?", value=date.today())
            qa_ok    = st.form_submit_button("📢 Post Notice", type="primary", use_container_width=True)
            if qa_ok:
                if not qa_name.strip():
                    st.warning("Please enter your name.")
                elif not qa_title.strip():
                    st.warning("Please enter a title.")
                else:
                    save_notice({
                        "submitted_by": qa_name.strip(),
                        "category":     qa_cat,
                        "title":        qa_title.strip(),
                        "body":         qa_body.strip(),
                        "notice_date":  str(qa_date),
                    })
                    st.success(f"✅ Notice posted for {qa_date.strftime('%-d %B')}! It's now live on the bulletin.")
                    st.balloons()

    with preview_col:
        st.markdown("**Category guide:**")
        for cat, cfg in NOTICE_CATS.items():
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">'
                f'<span style="background:{cfg["bg"]};color:{cfg["color"]};font-size:0.72rem;'
                f'font-weight:700;padding:0.2rem 0.6rem;border-radius:20px;min-width:90px;'
                f'text-align:center;">{cfg["emoji"]} {cat}</span>'
                f'</div>',
                unsafe_allow_html=True)

    # ── Today's notices listed below ──
    st.markdown("---")
    st.markdown(f"**Notices posted for {date.today().strftime('%A %-d %B')}:**")
    listed = load_notices(for_date=date.today())
    if not listed:
        st.markdown('<div style="text-align:center;padding:2rem;color:#9ab09a;font-size:0.85rem;">No notices yet today — be the first!</div>', unsafe_allow_html=True)
    else:
        for n in listed:
            cat = n.get("category","General")
            nc  = NOTICE_CATS.get(cat, NOTICE_CATS["General"])
            nid = n.get("id","")
            nl1, nl2 = st.columns([9,1])
            with nl1:
                st.markdown(
                    f'<div style="background:white;border-radius:10px;border-left:4px solid {nc["color"]};'
                    f'padding:0.75rem 1rem;margin-bottom:0.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
                    f'<div style="margin-bottom:0.2rem;">'
                    f'<span style="background:{nc["bg"]};color:{nc["color"]};font-size:0.65rem;'
                    f'font-weight:700;text-transform:uppercase;letter-spacing:0.08em;'
                    f'padding:0.15rem 0.5rem;border-radius:20px;">{nc["emoji"]} {cat}</span>'
                    f'<span style="font-size:0.7rem;color:#9ab09a;margin-left:0.5rem;">from {n.get("submitted_by","")}</span>'
                    f'</div>'
                    f'<div style="font-size:0.9rem;font-weight:700;color:#1a2e44;margin:0.3rem 0 0.2rem;">{n.get("title","")}</div>'
                    f'<div style="font-size:0.82rem;color:#3a4a3a;line-height:1.5;">{n.get("body","") or ""}</div>'
                    f'</div>',
                    unsafe_allow_html=True)
            with nl2:
                st.write("")
                if st.session_state.authenticated:
                    if st.button("🗑️", key=f"qa_del_{nid}", help="Delete"):
                        delete_notice(nid); st.rerun()

# ══════════════════════════════════════════════════════════════
# TAB: ARCHIVE
# ══════════════════════════════════════════════════════════════
with archive_tab:
    st.markdown("### 🗂️ Bulletin Archive")
    a1, a2 = st.tabs(["Browse by Week / Term", "Search"])

    with a1:
        c1, c2 = st.columns(2)
        with c1:
            browse_date = st.date_input("Select a date", value=date.today(), key="archive_date")
        with c2:
            browse_mode = st.selectbox("Browse by", ["Week", "Term"])

        y = browse_date.year
        terms_map = {1:(date(y,1,28),date(y,4,11)), 2:(date(y,4,28),date(y,7,4)),
                     3:(date(y,7,21),date(y,9,26)), 4:(date(y,10,13),date(y,12,12))}

        if browse_mode == "Week":
            wk = week_dates(browse_date)
            results = db.get_bulletins_range(wk[0], wk[-1])
            st.markdown(f"**Week of {wk[0].strftime('%-d %b %Y')}**")
        else:
            t_start = t_end = None
            for t,(s,e) in terms_map.items():
                if s <= browse_date <= e:
                    t_start, t_end = s, e
                    st.markdown(f"**Term {t}, {y}**")
                    break
            results = db.get_bulletins_range(t_start, t_end) if t_start else []
            if not t_start:
                st.info("Date is outside term dates.")

        if results:
            for row in results:
                d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                label = d.strftime("%A %-d %B %Y")
                fact = row.get("fun_fact","")
                st.markdown(f'<div class="arch-card"><div class="arch-card-date">{label}</div><div class="arch-card-fact">💡 {fact if fact else "No fun fact recorded"}</div></div>', unsafe_allow_html=True)
                if st.button(f"Open →", key=f"arch_{row['date']}"):
                    st.session_state.selected_date = d
                    st.rerun()
        else:
            st.markdown('<div class="empty-state"><div class="icon">📭</div>No bulletins found for this period</div>', unsafe_allow_html=True)

    with a2:
        keyword = st.text_input("🔍 Search all bulletins", placeholder="Enter staff name, student, excursion, note...")
        if keyword and len(keyword) >= 2:
            results = db.search_bulletins(keyword)
            if results:
                st.markdown(f"**{len(results)} result(s) found for '{keyword}'**")
                for row in results:
                    d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                    label = d.strftime("%A %-d %B %Y")
                    st.markdown(f'<div class="arch-card"><div class="arch-card-date">{label}</div></div>', unsafe_allow_html=True)
                    if st.button(f"Open →", key=f"search_{row['date']}"):
                        st.session_state.selected_date = d
                        st.rerun()
            else:
                st.markdown(f'<div class="empty-state"><div class="icon">🔍</div>No results for "{keyword}"</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB: STAFF LOGIN
# ══════════════════════════════════════════════════════════════
with login_tab:
    if st.session_state.authenticated:
        st.success("✅ You are logged in as Staff")
        st.markdown(f"You can now edit bulletins — head to the **📋 Bulletin** tab and click **✏️ Edit**.")
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.authenticated = False
            st.session_state.edit_mode = False
            st.rerun()
    else:
        st.markdown('<div class="auth-gate">', unsafe_allow_html=True)
        st.markdown("### 🔐 Staff Login")
        st.markdown("Login to create and edit daily bulletins.")
        pw = st.text_input("Password", type="password", placeholder="Enter staff password")
        if st.button("Login", type="primary", use_container_width=True):
            if pw == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.success("✅ Logged in! Go to the Bulletin tab to start editing.")
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.markdown('</div>', unsafe_allow_html=True)
