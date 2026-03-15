from theme import apply_clc_theme
from auth import require_auth, logout_button
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

apply_clc_theme()
require_auth("Daily Bulletin", "📰")
logout_button("sidebar")

# ── BULLETIN DESIGN SYSTEM ────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
.main .block-container { padding: 0 !important; max-width: 100% !important; }
.bulletin-hero { background: linear-gradient(135deg, #3d7a28 0%, #6BBF4E 60%, #8fd468 100%); padding: 1.75rem 2rem 1.5rem; position: relative; overflow: hidden; }
.bulletin-hero-inner { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 1rem; position: relative; z-index: 1; }
.bulletin-date-label { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: rgba(255,255,255,0.7); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.3rem; }
.bulletin-date-main { font-family: 'Playfair Display', serif; font-size: 2rem; color: white; font-weight: 700; line-height: 1.1; }
.bulletin-date-sub { font-size: 0.85rem; color: rgba(255,255,255,0.75); margin-top: 0.25rem; font-weight: 400; }
.section-card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; margin-bottom: 1.25rem; }
.section-card-header { padding: 0.6rem 1rem; display: flex; align-items: center; gap: 0.5rem; }
.section-card-header.green { background: #6BBF4E; } .section-card-header.navy { background: #1a2e44; }
.section-card-header.brown { background: #A67C6A; } .section-card-header.amber { background: #e8a125; }
.section-card-header.blue { background: #4a7fb5; } .section-card-header.purple { background: #7a5bb5; }
.section-card-header.slate { background: #6a7f8a; }
.section-card-header h3 { font-size: 0.72rem; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.1em; margin: 0; }
.section-card-header.amber h3 { color: #1a2e44; }
.section-card-body { padding: 0.75rem; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
.data-table th { background: #f4f8f2; color: #4a6640; font-weight: 600; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; padding: 0.4rem 0.6rem; text-align: left; border-bottom: 2px solid #d8ead2; }
.data-table td { padding: 0.4rem 0.6rem; border-bottom: 1px solid #f0f4ee; color: #2a3a2a; vertical-align: top; }
.data-table tr:last-child td { border-bottom: none; }
.kitchen-row td { background: #fff8e6 !important; font-weight: 600; }
.kitchen-badge { background: #e8a125; color: #1a2e44; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
.vehicle-time { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #888; }
.vehicle-booking { background: #e8f5e1; color: #2d6b1a; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
.content-area { padding: 1.5rem 2rem 3rem; max-width: 1600px; margin: 0 auto; }
.arch-card { background: white; border: 1.5px solid #e0e8dc; border-left: 4px solid #6BBF4E; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.6rem; }
.arch-card-date { font-weight: 700; font-size: 0.9rem; color: #1a2e44; }
.arch-card-fact { font-size: 0.78rem; color: #7a907a; margin-top: 0.2rem; }
.empty-state { text-align: center; padding: 2rem; color: #9ab09a; font-size: 0.85rem; }
.empty-state .icon { font-size: 2rem; margin-bottom: 0.5rem; }
.auth-gate { max-width: 400px; margin: 4rem auto; background: white; border-radius: 16px; padding: 2.5rem; box-shadow: 0 8px 32px rgba(0,0,0,0.1); text-align: center; }
.dp { background: #ffffff; border: 1px solid #d8ead8; border-radius: 8px; overflow: hidden; margin-bottom: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.dp-header { padding: 0.3rem 0.6rem; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: white; }
.dp-header.green { background: #4a8f33; } .dp-header.navy { background: #1a2e44; }
.dp-header.brown { background: #7a5c4a; } .dp-header.amber { background: #c97b1a; color: #1a2e44; }
.dp-header.blue { background: #3a6a9a; } .dp-header.purple { background: #6a4a9a; }
.dp-header.slate { background: #4a5a6a; }
.dp-body { padding: 0.4rem 0.5rem; }
.dt { width: 100%; border-collapse: collapse; font-size: 0.62rem; color: #1e3a1e; font-family: 'DM Sans', sans-serif; }
.dt th { color: #6BBF4E; font-weight: 600; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.06em; padding: 0.2rem 0.3rem; border-bottom: 1px solid #2a3d2a; }
.dt td { padding: 0.18rem 0.3rem; border-bottom: 1px solid #e8f0e8; vertical-align: top; line-height: 1.3; }
.dt-em { color: #9aaa9a; font-style: italic; font-size: 0.55rem; }
.nav-badge { background: rgba(107,191,78,0.2); border: 1px solid rgba(107,191,78,0.4); color: #6BBF4E; font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 20px; letter-spacing: 0.05em; }
.nav-badge.edit { background: rgba(232,161,37,0.2); border-color: rgba(232,161,37,0.4); color: #e8a125; }
.top-nav { background: #1a2e44; padding: 0 2rem; height: 56px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 12px rgba(0,0,0,0.2); }
.top-nav-left { display: flex; align-items: center; gap: 0.75rem; }
.top-nav-logo { width: 32px; height: 32px; background: linear-gradient(135deg, #6BBF4E, #4a8f33); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: white; font-size: 0.85rem; }
.top-nav-title { font-family: 'DM Sans', sans-serif; font-weight: 700; font-size: 0.95rem; color: white; letter-spacing: 0.02em; }
.top-nav-sub { font-size: 0.72rem; color: rgba(255,255,255,0.5); letter-spacing: 0.06em; text-transform: uppercase; }
.fact-bar { background: #f0f8ee; border-top: 2px solid #c8e0c8; padding: 0.4rem 1.5rem; font-size: 0.72rem; color: #3a5a3a; display: flex; align-items: center; gap: 0.75rem; font-family: 'DM Sans', sans-serif; }
.fact-label { color: #e8a125; font-weight: 700; font-size: 0.65rem; letter-spacing: 0.08em; text-transform: uppercase; white-space: nowrap; }
.vb-time { font-family: 'DM Mono', monospace; font-size: 0.58rem; color: #5a7a5a; }
.vb-tag { background: #e8f5e1; color: #2d6b1a; padding: 0.05rem 0.35rem; border-radius: 3px; font-size: 0.6rem; font-weight: 600; }
.kitchen-val { background: #c97b1a; border-radius: 4px; padding: 0.1rem 0.4rem; color: #1a2e44; font-weight: 800; font-size: 0.65rem; display: inline-block; }
.resp-label { font-size: 0.58rem; color: #6BBF4E; font-weight: 600; }
.resp-val { font-size: 0.62rem; color: #2d3d2d; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────
def _default_date():
    d = date.today()
    if d.weekday() == 5: return d - timedelta(days=1)
    if d.weekday() == 6: return d + timedelta(days=1)
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
    vb = data.get("vehicle_bookings", [])
    if isinstance(vb, dict):
        converted = []
        for t, v in vb.items():
            if v.get("van",""): converted.append({"vehicle":"Van","booker":v["van"],"whole_day":True,"start_time":"","end_time":""})
            if v.get("kia",""): converted.append({"vehicle":"Kia","booker":v["kia"],"whole_day":True,"start_time":"","end_time":""})
        data["vehicle_bookings"] = converted
    pc = data.get("program_changes", [])
    if pc and isinstance(pc[0], dict) and "change_reason" not in pc[0]:
        data["program_changes"] = [_empty_pc() for _ in range(3)]
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
    if not data.get("fun_fact", "").strip():
        data["fun_fact"] = daily_fun_fact(d)
    return data

NOTICE_CATS = {
    "General":      {"color": "#4a8f33", "bg": "#e8f5e1", "emoji": "📢"},
    "Reminder":     {"color": "#c97b1a", "bg": "#fff3e0", "emoji": "⏰"},
    "Urgent":       {"color": "#b91c1c", "bg": "#fee2e2", "emoji": "🚨"},
    "Student Info": {"color": "#1d4ed8", "bg": "#dbeafe", "emoji": "👨‍🎓"},
    "Facilities":   {"color": "#6d28d9", "bg": "#ede9fe", "emoji": "🏫"},
    "Wellbeing":    {"color": "#0e7490", "bg": "#cffafe", "emoji": "💚"},
}

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

def _slot_color(val, dark=False):
    _lc = ("#fff3cd", "#4a3200")
    _lb = ("#cce5ff", "#002a4a")
    _nd = ("#f0f0f0", "#2a2a2a")
    _ok = ("#e8f5e1", "#1e3d1e")
    _ot = ("#fce8ff", "#2a003a")
    d = 1 if dark else 0
    if val in ("Lunch Cover",): return _lc[d]
    if val in ("Lunch Break",): return _lb[d]
    if val in ("Normal Duties",): return _nd[d]
    if val in ("JP","PY","SY","NIT","JP Cover","PY Cover","SY Cover"): return _ok[d]
    if val in ("Other",): return _ot[d]
    return "transparent"

def _slot_emoji(val):
    m = {"JP":"🟦","PY":"🟣","SY":"🟫","JP Cover":"🟦","PY Cover":"🟣","SY Cover":"🟫",
         "Lunch Cover":"🟡","Lunch Break":"🔵","NIT":"⬛","Normal Duties":"⬜","Other":"🔷"}
    return m.get(val, "")

def _empty_pc():
    return {
        "change_reason": "",
        "staff_absent": "",
        "trt": False,
        "trt_name": "",
        "covering": "",
        "program": "",
        "time_slots": {},
        "staff_allocations": [],
        "staff_member": "",
        "release_type": "",
    }

def _empty_alloc():
    return {"name": "", "normal_prog": "", "time_slots": {}}

def _pc_row_html(label, normal_prog, ts, dark=False):
    text  = ("#1a2e44" if not dark else "#c8d8c8")
    hdr   = ("#4a6640" if not dark else "#6BBF4E")
    th_bg = ("#f4f8f2" if not dark else "#111e11")
    fs    = "0.56rem" if dark else "0.66rem"
    lbl_c = ("#1a2e44" if not dark else "#6BBF4E")
    th_cells = "".join([
        f'<th style="background:{th_bg};color:{hdr};font-size:0.52rem;padding:1px 3px;'
        f'text-align:center;white-space:nowrap;border-right:1px solid {"#e0e8dc" if not dark else "#2a3d2a"};">'
        f'{s}</th>'
        for s in PC_TIME_SLOTS
    ])
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
            if val == "Lunch Cover": _plbl = f"→ {person}"
            elif val == "Lunch Break": _plbl = f"↩ {person}"
            else: _plbl = person
            inner += f'<br><span style="font-size:0.85em;opacity:0.7;">{_plbl}</span>'
        td_cells += (
            f'<td style="background:{bg};color:{text};text-align:center;'
            f'padding:2px 2px;font-size:{fs};min-width:34px;vertical-align:top;{border}">'
            f'{inner}</td>'
        )
    lbl_html = (
        f'<td style="white-space:nowrap;padding:3px 8px 3px 4px;color:{lbl_c};'
        f'font-weight:700;font-size:{fs};vertical-align:middle;'
        f'border-right:2px solid {"#6BBF4E" if not dark else "#4a8f33"};">'
        f'{label}'
        f'{"<br>" if normal_prog else ""}'
        f'<span style="font-weight:400;opacity:0.7;font-size:0.9em;">{normal_prog}</span>'
        f'</td>'
    )
    return f'<tr>{lbl_html}{td_cells}</tr>'

def _pc_timetable_html(entry, dark=False):
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
    ts = entry.get("time_slots", {})
    trt_name = entry.get("trt_name","")
    covering = entry.get("covering","")
    program  = entry.get("program","")
    if ts and any((v.get("value","") if isinstance(v,dict) else v) for v in ts.values()):
        lbl = trt_name if trt_name else "TRT"
        norm = f"{covering} · {program}" if program else covering
        rows_html += _pc_row_html(lbl, norm, ts, dark)
    for alloc in entry.get("staff_allocations", []):
        a_ts = alloc.get("time_slots", {})
        if not a_ts or not any((v.get("value","") if isinstance(v,dict) else v) for v in a_ts.values()):
            continue
        rows_html += _pc_row_html(alloc.get("name","(Staff)"), alloc.get("normal_prog",""), a_ts, dark)
    if not rows_html:
        return ""
    return (
        f'<div style="overflow-x:auto;margin-top:4px;">'
        f'<table style="border-collapse:collapse;width:auto;">'
        f'<thead><tr>{th_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )

_AUS_FACTS = [
    "Australia is the only continent that is also a single country — and somehow still can't decide where to put its capital.",
    "Kangaroos can't walk backwards, which is why they're on the Australian coat of arms — always moving forward, mate.",
    "Australia has more kangaroos than people. The roos are winning.",
    "Wombats produce cube-shaped poo — the only animal in the world that does. Science still hasn't fully explained why.",
    "Australia has 10 of the world's 15 most venomous snakes. They're very proud of this.",
    "The Great Barrier Reef is the largest living structure on Earth — visible from space, yet invisible to politicians.",
    "The platypus is venomous, lays eggs, and has a bill like a duck. It looks like Australia designed it after a big night.",
    "Australia once fought a war against emus. The emus won. This is true. Look it up.",
    "Eucalyptus leaves are mildly toxic to most animals. Koalas eat almost nothing else and sleep 22 hours a day. Icon behaviour.",
    "Australians invented WiFi. Also the black box flight recorder. And the bionic ear. But mostly WiFi.",
    "Drop bears are not real. Probably.",
    "Quokkas are considered the happiest animal on Earth. They live on Rottnest Island. No predators, good weather — honestly same.",
    "South Australia was the first place in the world to give women the right to stand for parliament, back in 1894.",
    "The phrase 'no worries' appears in Australian conversation more than any other expression. It is both a greeting and a worldview.",
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

def delete_notice(nid):
    try:
        _get_sb().table("bulletin_notices").delete().eq("id", nid).execute()
    except Exception as e:
        st.error(f"Could not delete notice: {e}")

# ══════════════════════════════════════════════════════════════
# DISPLAY MODE
# ══════════════════════════════════════════════════════════════
params = st.query_params
if params.get("display") == "true":
    import time
    if "display_date" not in st.session_state:
        st.session_state.display_date = date.today()
    if st.session_state.display_date < date.today():
        st.session_state.display_date = date.today()
    today = st.session_state.display_date
    d_data = load_bulletin(today)
    if "display_last_refresh" not in st.session_state:
        st.session_state.display_last_refresh = time.time()
    if time.time() - st.session_state.display_last_refresh > 60:
        st.session_state.display_last_refresh = time.time()
        st.session_state.display_date = date.today()
        st.rerun()
    sr = d_data.get("staff_responsibilities", {})
    fun = d_data.get("fun_fact", "")
    st.markdown(f"""
    <style>
    .display-header {{ background: linear-gradient(135deg, #1a4d8c 0%, #2d7d4f 100%); padding: 0.6rem 1.5rem; display: flex; align-items: center; justify-content: space-between; border-bottom: 3px solid #6BBF4E; }}
    .display-header-title {{ font-family: 'Playfair Display', serif; font-size: 1.1rem; color: white; font-weight: 700; }}
    .display-header-date {{ font-family: 'DM Mono', monospace; font-size: 1rem; color: #6BBF4E; font-weight: 600; }}
    .display-header-time {{ font-family: 'DM Mono', monospace; font-size: 1.4rem; color: #e8a125; font-weight: 700; }}
    </style>
    <div class="display-header">
      <div>
        <div class="display-header-title">Cowandilla Learning Centre &mdash; Daily Bulletin</div>
        <div class="display-header-date">{today.strftime("%A %-d %B %Y").upper()}</div>
      </div>
      <div style="display:flex;align-items:center;gap:1.5rem;">
        <div class="display-header-time" id="live-clock">--:-- --</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    prev_day = today - timedelta(days=1)
    next_day = today + timedelta(days=1)
    dn_prev, dn_label, dn_next, dn_today = st.columns([1, 4, 1, 1])
    with dn_prev:
        if st.button(f"← {prev_day.strftime('%a %-d %b')}", key="dn_prev", use_container_width=True):
            st.session_state.display_date = prev_day; st.rerun()
    with dn_label:
        st.markdown(f'<div style="text-align:center;color:#2d7d4f;font-size:0.75rem;font-weight:700;padding:0.45rem 0;">VIEWING: {today.strftime("%A %-d %B %Y").upper()}</div>', unsafe_allow_html=True)
    with dn_next:
        if st.button(f"{next_day.strftime('%a %-d %b')} →", key="dn_next", use_container_width=True):
            st.session_state.display_date = next_day; st.rerun()
    with dn_today:
        if st.button("Today", key="dn_today", use_container_width=True):
            st.session_state.display_date = date.today(); st.rerun()

    def tbl_rows(rows, keys):
        filtered = [r for r in rows if any(r.get(k,"") for k in keys)]
        if not filtered:
            return '<tr><td colspan="20" class="dt-em">None today</td></tr>'
        return "".join(["<tr>" + "".join([f"<td>{r.get(k,'')}</td>" for k in keys]) + "</tr>" for r in filtered])

    d_notices = load_notices(for_date=today)
    if d_notices:
        n_parts = []
        for n in d_notices:
            cat = n.get("category","General")
            nc  = NOTICE_CATS.get(cat, NOTICE_CATS["General"])
            n_parts.append(f'<span style="background:{nc["bg"]};color:{nc["color"]};font-size:0.58rem;font-weight:700;text-transform:uppercase;padding:0.1rem 0.4rem;border-radius:10px;">{cat}</span> <strong style="color:#1a2e44;font-size:0.65rem;">{n.get("title","")}</strong><span style="color:#4a6a4a;font-size:0.62rem;"> — {n.get("body","")}</span><span style="color:#7a9a7a;font-size:0.58rem;"> · {n.get("submitted_by","")}</span>')
        st.markdown(f'<div class="dp"><div class="dp-header green">📝 Staff Notices</div><div class="dp-body"><div style="line-height:1.8;">{"<br>".join(n_parts)}</div></div></div>', unsafe_allow_html=True)

    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([2,2,2.5,1.5,2])
    with r1c1:
        st.markdown(f'<div class="dp"><div class="dp-header green">🙅 Staff & Student Absent</div><div class="dp-body"><table class="dt"><tr><th>Staff</th><th>TRT</th><th>Student</th><th>Program</th><th>Reason</th></tr>{tbl_rows(d_data.get("staff_absent",[]), ["Staff Absence","TRT","Student Absence","Program","Reason"])}</table></div></div>', unsafe_allow_html=True)
    with r1c2:
        st.markdown(f'<div class="dp"><div class="dp-header blue">🚌 Excursions</div><div class="dp-body"><table class="dt"><tr><th>Program</th><th>Staff</th><th>Depart</th><th>Return</th><th>Location</th></tr>{tbl_rows(d_data.get("excursions",[]), ["Program","Staff Member","Time Departing","Time Returning","Location"])}</table></div></div>', unsafe_allow_html=True)
    with r1c3:
        st.markdown(f'<div class="dp"><div class="dp-header navy">🤝 Staff Meetings</div><div class="dp-body"><table class="dt"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>{tbl_rows(d_data.get("staff_meetings",[]), ["Type","Staff Member","Location","Time Departing","Time Returning","Student"])}</table></div></div>', unsafe_allow_html=True)
    with r1c4:
        st.markdown(f'<div class="dp"><div class="dp-header brown">📥 Entry Meetings</div><div class="dp-body"><table class="dt"><tr><th>Time</th><th>Program</th><th>Student</th></tr>{tbl_rows(d_data.get("entry_meetings",[]), ["Time","Program","Student"])}</table></div></div>', unsafe_allow_html=True)
    with r1c5:
        kitchen = sr.get("kitchen_duties","") or "—"
        pd_focus = sr.get("meeting_pd_focus","") or "—"
        chair = sr.get("chair","") or "—"
        minutes = sr.get("minutes","") or "—"
        st.markdown(f'<div class="dp"><div class="dp-header amber">⭐ Staff Responsibilities</div><div class="dp-body"><div style="margin-bottom:0.35rem;"><span class="kitchen-val">🍳 Kitchen: {kitchen}</span></div><div style="margin-bottom:0.2rem;"><span class="resp-label">📌 PD Focus</span><br><span class="resp-val">{pd_focus}</span></div><div style="margin-bottom:0.2rem;"><span class="resp-label">🪑 Chair</span><br><span class="resp-val">{chair}</span></div><div><span class="resp-label">📝 Minutes</span><br><span class="resp-val">{minutes}</span></div></div></div>', unsafe_allow_html=True)

    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns([2,2,2,1.5,1])
    with r2c1:
        st.markdown(f'<div class="dp"><div class="dp-header blue">🟦 JP – Travel</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>{tbl_rows(d_data.get("travel_jp",[]), ["Student","Transport To","Transport From","Times"])}</table></div></div>', unsafe_allow_html=True)
    with r2c2:
        st.markdown(f'<div class="dp"><div class="dp-header purple">🟣 PY – Travel</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>{tbl_rows(d_data.get("travel_py",[]), ["Student","Transport To","Transport From","Times"])}</table></div></div>', unsafe_allow_html=True)
    with r2c3:
        st.markdown(f'<div class="dp"><div class="dp-header slate">🟫 SY – Travel</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>{tbl_rows(d_data.get("travel_sy",[]), ["Student","Transport To","Transport From","Times"])}</table></div></div>', unsafe_allow_html=True)
    with r2c4:
        vb_list = d_data.get("vehicle_bookings", [])
        if isinstance(vb_list, dict): vb_list = []
        if vb_list:
            def _dm_vb_time(b):
                return "All day" if b.get("whole_day", True) else f"{b.get('start_time','?')} – {b.get('end_time','?')}"
            vb_rows_html = "".join([f'<tr><td class="vb-time">{"🚐 Van" if b.get("vehicle","")=="Van" else "🚙 Kia"}</td><td><span class="vb-tag">{b.get("booker","")}</span></td><td style="font-size:0.58rem;color:#6BBF4E;">{_dm_vb_time(b)}</td></tr>' for b in vb_list if b.get("booker","")])
        else:
            vb_rows_html = '<tr><td colspan="3" class="dt-em">No bookings today</td></tr>'
        st.markdown(f'<div class="dp"><div class="dp-header navy">🚗 Vehicles</div><div class="dp-body"><table class="dt"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>{vb_rows_html}</table></div></div>', unsafe_allow_html=True)
    with r2c5:
        nit = d_data.get("nit_booking","") or '<span style="color:#9aaa9a;font-style:italic;font-size:0.6rem;">None today</span>'
        msgs = d_data.get("additional_messages",[])
        msg_rows = tbl_rows(msgs, ["Staff Member","Visitor","Reason","Arriving/Departing"])
        st.markdown(f'<div class="dp"><div class="dp-header green">📋 NIT Booking</div><div class="dp-body"><p style="font-size:0.62rem;color:#c8d8c8;margin:0;line-height:1.4;">{nit}</p></div></div><div class="dp"><div class="dp-header slate">💬 Messages</div><div class="dp-body"><table class="dt"><tr><th>Staff</th><th>Visitor</th><th>Reason</th><th>Arr/Dep</th></tr>{msg_rows}</table></div></div>', unsafe_allow_html=True)

    pc_rows = d_data.get("program_changes", [])
    pc_active = [r for r in pc_rows if isinstance(r,dict) and r.get("change_reason","")]
    if pc_active:
        pc_html_parts = []
        for pc in pc_active:
            meta_parts = []
            if pc.get("change_reason"): meta_parts.append(f"<strong style='color:#6BBF4E;'>{pc['change_reason']}</strong>")
            if pc.get("staff_absent"): meta_parts.append(f"Absent: <strong>{pc['staff_absent']}</strong>")
            if pc.get("trt") and pc.get("trt_name"): meta_parts.append(f"TRT: {pc['trt_name']}")
            tt_html = _pc_timetable_html(pc, dark=True)
            pc_html_parts.append(f'<div style="margin-bottom:8px;"><div style="font-size:0.6rem;margin-bottom:4px;color:#a8c8a8;">{" · ".join(meta_parts)}</div>{tt_html if tt_html else "<span style=\'color:#3a5a3a;font-size:0.6rem;\'>No timetable entered</span>"}</div>')
        st.markdown(f'<div class="dp"><div class="dp-header green">📊 Program Changes</div><div class="dp-body">{"".join(pc_html_parts)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="dp"><div class="dp-header green">📊 Program Changes</div><div class="dp-body"><span class="dt-em">No program changes today</span></div></div>', unsafe_allow_html=True)

    import streamlit.components.v1 as components
    components.html("""<script>(function(){function u(){var o={timeZone:'Australia/Adelaide',hour:'numeric',minute:'2-digit',hour12:true};var t=new Date().toLocaleTimeString('en-AU',o).toUpperCase();var e=window.parent.document.getElementById('live-clock');if(e)e.textContent=t;}u();setInterval(u,1000);})();</script>""", height=0)
    st.markdown(f'<div class="fact-bar"><span class="fact-label">💡 Fun Fact</span><span>{fun if fun else "No fun fact entered for today"}</span></div>', unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════
# QUICK ADD MODE
# ══════════════════════════════════════════════════════════════
if params.get("quickadd") == "true":
    st.markdown("""<div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;padding:1.5rem 2rem;margin-bottom:1.5rem;text-align:center;color:white;"><div style="font-size:2rem;margin-bottom:0.3rem;">📝</div><div style="font-size:1.3rem;font-weight:700;margin-bottom:0.25rem;">Staff Quick Notice</div><div style="font-size:0.85rem;opacity:0.85;">Cowandilla Learning Centre · Daily Bulletin</div></div>""", unsafe_allow_html=True)
    with st.form("qa_standalone_form", clear_on_submit=True):
        qa_name  = st.text_input("Your name *", placeholder="e.g. Sarah")
        qa_cat   = st.selectbox("Category *", list(NOTICE_CATS.keys()), format_func=lambda x: f"{NOTICE_CATS[x]['emoji']} {x}")
        qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3")
        qa_body  = st.text_area("Details (optional)", placeholder="Any extra info staff need to know…", height=110)
        qa_date  = st.date_input("For which day?", value=date.today())
        qa_ok    = st.form_submit_button("📢 Post Notice to Bulletin", type="primary", use_container_width=True)
        if qa_ok:
            if not qa_name.strip(): st.warning("Please enter your name.")
            elif not qa_title.strip(): st.warning("Please enter a title.")
            else:
                save_notice({"submitted_by": qa_name.strip(), "category": qa_cat, "title": qa_title.strip(), "body": qa_body.strip(), "notice_date": str(qa_date)})
                st.success(f"✅ Notice posted for {qa_date.strftime('%-d %B')}!")
                st.balloons()
    st.stop()


# ── TOP NAV ───────────────────────────────────────────────────
edit = st.session_state.edit_mode and st.session_state.authenticated
auth_badge = ""
if st.session_state.authenticated:
    auth_badge = '<span class="nav-badge edit">✏️ Edit Mode</span>' if edit else '<span class="nav-badge">✅ Staff</span>'

st.markdown(f"""<div class="top-nav"><div class="top-nav-left"><div class="top-nav-logo">CLC</div><div><div class="top-nav-title">Daily Bulletin</div><div class="top-nav-sub">Cowandilla Learning Centre</div></div></div><div style="display:flex;align-items:center;gap:1rem;">{auth_badge}</div></div>""", unsafe_allow_html=True)

current_date = st.session_state.selected_date
bulletin_data = load_bulletin(current_date)

# ── PAGE TABS ─────────────────────────────────────────────────
page_tab, quickadd_tab, archive_tab, login_tab = st.tabs(["📋 Bulletin", "📝 Quick Add", "🗂️ Archive", "🔐 Staff"])

# ══════════════════════════════════════════════════════════════
# TAB: BULLETIN
# ══════════════════════════════════════════════════════════════
with page_tab:
    if st.query_params.get("from_display") == "true" and not st.session_state.authenticated:
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

    week = week_dates(current_date)
    import html as _html, re as _re
    fact = bulletin_data.get("fun_fact","")
    fact_clean = _html.escape(_re.sub(r'<[^>]+>', '', fact)).strip()
    fun_fact_html = ""
    if fact_clean:
        fun_fact_html = f'<div style="background:rgba(255,255,255,0.15);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.2);border-radius:12px;padding:0.65rem 1rem;max-width:480px;"><div style="font-size:0.65rem;color:rgba(255,255,255,0.6);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.2rem;">💡 Fun Fact</div><div style="font-size:0.85rem;color:white;font-weight:500;line-height:1.4;">{fact_clean}</div></div>'

    st.markdown(f"""<div class="bulletin-hero"><div class="bulletin-hero-inner"><div><div class="bulletin-date-label">{term_label(current_date)}</div><div class="bulletin-date-main">{current_date.strftime("%A %-d %B")}</div><div class="bulletin-date-sub">{current_date.strftime("%Y")}</div></div>{fun_fact_html}</div></div>""", unsafe_allow_html=True)

    st.markdown('<div style="background:white;border-bottom:2px solid #e8f0e3;padding:0.4rem 1rem 0;">', unsafe_allow_html=True)
    nav_left, nav_mid, nav_right = st.columns([1, 4, 1])
    with nav_left:
        if st.button("← Prev Week", key="prev_week", use_container_width=True):
            st.session_state.selected_date = week[0] - timedelta(days=7); st.rerun()
    with nav_mid:
        week_label_str = f"Week of {week[0].strftime('%-d %b')} – {week[-1].strftime('%-d %b %Y')}"
        is_this_week = date.today() in week
        if is_this_week: week_label_str += " · This Week"
        st.markdown(f'<div style="text-align:center;padding:0.45rem 0;font-size:0.78rem;font-weight:600;color:{"#4a8f33" if is_this_week else "#5a6e5a"};">{week_label_str}</div>', unsafe_allow_html=True)
    with nav_right:
        if st.button("Next Week →", key="next_week", use_container_width=True):
            st.session_state.selected_date = week[0] + timedelta(days=7); st.rerun()
    day_cols = st.columns(5)
    for i, d in enumerate(week):
        with day_cols[i]:
            is_current = d == current_date
            label = d.strftime("%a %-d %b") + (" ◉" if d == date.today() else "")
            if st.button(label, key=f"day_{d}", use_container_width=True, type="primary" if is_current else "secondary"):
                st.session_state.selected_date = d; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    ctrl_cols = st.columns([1, 1, 1, 3, 1])
    if st.session_state.authenticated:
        with ctrl_cols[0]:
            if st.button("✏️ Edit" if not edit else "👁️ View", type="primary" if not edit else "secondary", use_container_width=True):
                st.session_state.edit_mode = not st.session_state.edit_mode; st.rerun()
        with ctrl_cols[1]:
            if edit:
                if st.button("💾 Save", type="primary", use_container_width=True):
                    st.session_state["_pending_save"] = True
        with ctrl_cols[2]:
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                st.session_state.authenticated = False; st.session_state.edit_mode = False; st.rerun()
    else:
        with ctrl_cols[0]:
            if st.button("🔐 Staff Login", type="secondary", use_container_width=True):
                st.session_state.show_inline_login = not st.session_state.get("show_inline_login", False); st.rerun()
    with ctrl_cols[4]:
        st.markdown('<a href="/?display=true" target="_blank" style="display:block;text-align:center;background:#1a2e44;color:white;font-weight:600;font-size:0.8rem;padding:0.45rem 0.75rem;border-radius:8px;text-decoration:none;white-space:nowrap;">📺 Staff Room View</a>', unsafe_allow_html=True)

    if not st.session_state.authenticated and st.session_state.get("show_inline_login", False):
        lc1, lc2, lc3 = st.columns([3, 1, 1])
        with lc1:
            quick_pw = st.text_input("Staff password", type="password", key="inline_pw", label_visibility="collapsed", placeholder="Enter staff password…")
        with lc2:
            if st.button("🔓 Login", type="primary", use_container_width=True, key="inline_login_btn"):
                if quick_pw == ADMIN_PASSWORD:
                    st.session_state.authenticated = True; st.session_state.edit_mode = True; st.session_state.show_inline_login = False; st.rerun()
                else:
                    st.error("Incorrect password")
        with lc3:
            if st.button("Cancel", type="secondary", use_container_width=True, key="inline_cancel"):
                st.session_state.show_inline_login = False; st.rerun()

    st.markdown('<div class="content-area">', unsafe_allow_html=True)

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
                    st.markdown(f'<div style="background:white;border-radius:10px;border-left:4px solid {_nc["color"]};padding:0.75rem 1rem;margin-bottom:0.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);"><div style="margin-bottom:0.2rem;"><span style="background:{_nc["bg"]};color:{_nc["color"]};font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;padding:0.15rem 0.5rem;border-radius:20px;">{_nc["emoji"]} {_cat}</span><span style="font-size:0.7rem;color:#9ab09a;margin-left:0.5rem;">from {_n.get("submitted_by","")}</span></div><div style="font-size:0.9rem;font-weight:700;color:#1a2e44;margin:0.3rem 0 0.2rem;">{_n.get("title","")}</div><div style="font-size:0.82rem;color:#3a4a3a;line-height:1.5;">{_n.get("body","")}</div></div>', unsafe_allow_html=True)
                with _nc2:
                    if edit:
                        st.write("")
                        if st.button("🗑️", key=f"top_del_n_{_nid}", help="Delete notice"):
                            delete_notice(_nid); st.rerun()
        else:
            st.markdown('<div style="text-align:center;padding:1rem;color:#9ab09a;font-size:0.85rem;">No notices today — staff can add via the 📝 Quick Add tab</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    s1, s2, s3, s4 = st.tabs(["👥 Staff & Meetings", "🚌 Travel & Vehicles", "📌 Responsibilities & NIT", "📊 Program Changes"])

    with s1:
        if edit:
            auto_fact = daily_fun_fact(current_date)
            current_fact = bulletin_data.get("fun_fact", "").strip()
            fc1, fc2 = st.columns([5, 1])
            with fc1:
                new_fact = st.text_input("💡 Fun Fact of the Day", value=current_fact if current_fact else auto_fact, placeholder="Auto-filled with today's Australian fun fact…")
            with fc2:
                st.markdown("<div style='padding-top:1.85rem;'>", unsafe_allow_html=True)
                if st.button("🎲 New", key="new_fact", use_container_width=True):
                    bulletin_data["fun_fact"] = auto_fact; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            bulletin_data["fun_fact"] = new_fact

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>🙅 Staff & Student Absent</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                import pandas as pd
                df = pd.DataFrame(bulletin_data["staff_absent"])
                edited = st.data_editor(df, key="sa_editor", hide_index=True, use_container_width=True, num_rows="dynamic", column_config={c: st.column_config.TextColumn(c) for c in df.columns})
                bulletin_data["staff_absent"] = edited.to_dict("records")
            else:
                rows = bulletin_data["staff_absent"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Staff Absence</th><th>TRT</th><th>Student</th><th>Program</th><th>Reason</th></tr>' + "".join([f"<tr><td>{r.get('Staff Absence','')}</td><td>{r.get('TRT','')}</td><td>{r.get('Student Absence','')}</td><td>{r.get('Program','')}</td><td>{r.get('Reason','')}</td></tr>" for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">✅</div>No absences today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header blue"><h3>🚌 Excursions</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["excursions"])
                edited = st.data_editor(df, key="ex_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["excursions"] = edited.to_dict("records")
            else:
                rows = bulletin_data["excursions"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Program</th><th>Staff</th><th>Departing</th><th>Returning</th><th>Location</th></tr>' + "".join([f"<tr><td>{r.get('Program','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Location','')}</td></tr>" for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">🗺️</div>No excursions today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header brown"><h3>📥 Entry Meetings – Annette</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["entry_meetings"])
                edited = st.data_editor(df, key="em_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["entry_meetings"] = edited.to_dict("records")
            else:
                rows = bulletin_data["entry_meetings"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Time</th><th>Program</th><th>Student</th></tr>' + "".join([f"<tr><td>{r.get('Time','')}</td><td>{r.get('Program','')}</td><td>{r.get('Student','')}</td></tr>" for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">📭</div>No entry meetings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

        with col_right:
            st.markdown('<div class="section-card"><div class="section-card-header navy"><h3>🤝 Staff Meetings</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["staff_meetings"])
                edited = st.data_editor(df, key="sm_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["staff_meetings"] = edited.to_dict("records")
            else:
                rows = bulletin_data["staff_meetings"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>' + "".join([f"<tr><td>{r.get('Type','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Location','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Student','')}</td></tr>" for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">📅</div>No staff meetings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header slate"><h3>💬 Additional Staff Messages</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["additional_messages"])
                edited = st.data_editor(df, key="msg_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["additional_messages"] = edited.to_dict("records")
            else:
                rows = bulletin_data["additional_messages"]
                has_data = any(any(v for v in r.values()) for r in rows)
                if has_data:
                    st.markdown('<table class="data-table"><tr><th>Staff</th><th>Visitor</th><th>Reason</th><th>Arriving/Departing</th></tr>' + "".join([f"<tr><td>{r.get('Staff Member','')}</td><td>{r.get('Visitor','')}</td><td>{r.get('Reason','')}</td><td>{r.get('Arriving/Departing','')}</td></tr>" for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="empty-state"><div class="icon">💭</div>No additional messages</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

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
                        st.markdown('<table class="data-table"><tr><th>Student</th><th>To</th><th>From</th><th>Times</th></tr>' + "".join([f"<tr><td>{r.get('Student','')}</td><td>{r.get('Transport To','')}</td><td>{r.get('Transport From','')}</td><td>{r.get('Times','')}</td></tr>" for r in rows if any(v for v in r.values())]) + "</table>", unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="empty-state"><div class="icon">🚐</div>No travel today</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)

        render_travel_card(jp_col, "travel_jp", "🟦 Junior Primary – Travel", "#4a7fb5")
        render_travel_card(py_col, "travel_py", "🟣 Primary Years – Travel", "#7a5bb5")
        render_travel_card(sy_col, "travel_sy", "🟫 Senior Years – Travel", "#8c6a4f")

        st.markdown('<div class="section-card"><div class="section-card-header navy"><h3>🚗 Vehicle Bookings — Van & Kia</h3></div><div class="section-card-body">', unsafe_allow_html=True)
        vb_list = bulletin_data.get("vehicle_bookings", [])
        if isinstance(vb_list, dict): vb_list = []
        if edit:
            if vb_list:
                st.markdown("**Current bookings:**")
                for _bi, _bk in enumerate(vb_list):
                    _bc1, _bc2, _bc3, _bc4 = st.columns([1,2,2,1])
                    with _bc1: st.markdown(f"**{'🚐 Van' if _bk.get('vehicle','')=='Van' else '🚙 Kia'}**")
                    with _bc2: st.markdown(f"**{_bk.get('booker','—')}**")
                    with _bc3: st.markdown("🕐 Whole day" if _bk.get("whole_day", True) else f"🕐 {_bk.get('start_time','?')} – {_bk.get('end_time','?')}")
                    with _bc4:
                        if st.button("🗑️", key=f"vb_del_{_bi}", help="Remove"):
                            vb_list.pop(_bi); bulletin_data["vehicle_bookings"] = vb_list; st.rerun()
                st.markdown("---")
            st.markdown("**Add a booking:**")
            _av1, _av2, _av3 = st.columns([1,2,2])
            with _av1: _new_vehicle = st.selectbox("Vehicle", ["Van", "Kia"], key="vb_new_vehicle")
            with _av2: _new_booker = st.text_input("Booked by (name)", key="vb_new_booker", placeholder="e.g. Sarah")
            with _av3: _new_whole = st.checkbox("Whole day", value=True, key="vb_new_whole")
            if not _new_whole:
                _at1, _at2 = st.columns(2)
                with _at1: _new_start = st.text_input("Start time", key="vb_new_start", placeholder="e.g. 9:30")
                with _at2: _new_end = st.text_input("End time", key="vb_new_end", placeholder="e.g. 12:00")
            else:
                _new_start = ""; _new_end = ""
            if st.button("➕ Add Booking", type="primary", key="vb_add_btn"):
                if _new_booker.strip():
                    vb_list.append({"vehicle": _new_vehicle, "booker": _new_booker.strip(), "whole_day": _new_whole, "start_time": _new_start.strip(), "end_time": _new_end.strip()})
                    bulletin_data["vehicle_bookings"] = vb_list; st.rerun()
                else:
                    st.warning("Please enter a name for this booking.")
        else:
            if vb_list and any(b.get("booker","") for b in vb_list):
                def _vb_time(b): return "Whole day" if b.get("whole_day", True) else f"{b.get('start_time','?')} – {b.get('end_time','?')}"
                rows_html = "".join([f'<tr><td>{"🚐 Van" if b.get("vehicle","")=="Van" else "🚙 Kia"}</td><td><span class="vehicle-booking">{b.get("booker","")}</span></td><td class="vehicle-time">{_vb_time(b)}</td></tr>' for b in vb_list if b.get("booker","")])
                st.markdown(f'<table class="data-table"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>{rows_html}</table>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty-state"><div class="icon">🚗</div>No vehicle bookings today</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

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
                st.markdown(f'<table class="data-table"><tr class="kitchen-row"><td><span class="kitchen-badge">🍳 Kitchen</span></td><td><strong>{kitchen if kitchen else "—"}</strong></td></tr><tr><td>📌 PD Focus</td><td>{sr.get("meeting_pd_focus","") or "—"}</td></tr><tr><td>🪑 Chair</td><td>{sr.get("chair","") or "—"}</td></tr><tr><td>📝 Minutes</td><td>{sr.get("minutes","") or "—"}</td></tr></table>', unsafe_allow_html=True)
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

    with s4:
        _pc_state_key = f"pc_n_{current_date}"
        if edit:
            if _pc_state_key not in st.session_state:
                _loaded_pc = bulletin_data.get("program_changes", [])
                _n_loaded  = len([e for e in _loaded_pc if isinstance(e,dict) and "change_reason" in e])
                st.session_state[_pc_state_key] = max(1, _n_loaded)
        else:
            st.session_state.pop(_pc_state_key, None)
        _n_entries = st.session_state.get(_pc_state_key, 1)
        _loaded_pc = bulletin_data.get("program_changes", [])

        def _render_timetable_edit(key_prefix, covering_mode, entry_slots, prog_default=""):
            opts = PC_SLOT_OPTIONS if covering_mode != "allocation" else PC_SLOT_OPTIONS_EXT
            st.markdown('<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;"><span style="background:#f0f4f0;color:#5a6e5a;font-size:0.68rem;padding:2px 8px;border-radius:12px;font-weight:600;">⬜ Blank = no change</span><span style="background:#e8f5e1;color:#2d6b1a;font-size:0.68rem;padding:2px 8px;border-radius:12px;font-weight:600;">🟩 Program cover</span><span style="background:#fff3cd;color:#856404;font-size:0.68rem;padding:2px 8px;border-radius:12px;font-weight:600;">🟡 Lunch Cover</span><span style="background:#cce5ff;color:#004085;font-size:0.68rem;padding:2px 8px;border-radius:12px;font-weight:600;">🔵 Lunch Break</span></div>', unsafe_allow_html=True)
            strip_cells = ""
            for _s in PC_TIME_SLOTS:
                _v = st.session_state.get(f"{key_prefix}_{_s}", "")
                if not _v and prog_default and covering_mode == "program": _v = prog_default
                _bg = _slot_color(_v)
                _em = _slot_emoji(_v) if _v else ""
                strip_cells += f'<td style="background:{_bg};text-align:center;padding:4px 2px;min-width:36px;font-size:0.55rem;border-right:1px solid #e0e8dc;" title="{_s}: {_v}">{_em}</td>'
            st.markdown(f'<div style="overflow-x:auto;margin-bottom:8px;"><table style="border-collapse:collapse;width:auto;"><tr>{"".join([f"<th style=background:#f4f8f2;color:#4a6640;font-size:0.5rem;text-align:center;padding:1px 2px;min-width:36px;border-right:1px solid #e0e8dc;>{s}</th>" for s in PC_TIME_SLOTS])}</tr><tr>{strip_cells}</tr></table></div>', unsafe_allow_html=True)
            HOUR_GROUPS = [("9:00 – 10:00", PC_TIME_SLOTS[0:4]), ("10:00 – 11:00", PC_TIME_SLOTS[4:8]), ("11:00 – 12:00", PC_TIME_SLOTS[8:12]), ("12:00 – 1:00", PC_TIME_SLOTS[12:16]), ("1:00 – 2:00", PC_TIME_SLOTS[16:20]), ("2:00 – 2:45", PC_TIME_SLOTS[20:24])]
            for grp_label, slots in HOUR_GROUPS:
                st.markdown(f'<div style="font-size:0.65rem;font-weight:700;color:#1a2e44;margin:6px 0 2px;padding:2px 6px;background:#e8f0e3;border-radius:4px;display:inline-block;">{grp_label}</div>', unsafe_allow_html=True)
                gcols = st.columns(len(slots))
                for j, slot in enumerate(slots):
                    with gcols[j]:
                        stored = entry_slots.get(slot, {})
                        stored_val  = stored.get("value","")  if isinstance(stored,dict) else str(stored)
                        stored_pers = stored.get("person","") if isinstance(stored,dict) else ""
                        default_val = stored_val if stored_val else (prog_default if covering_mode == "program" else "")
                        try: _def_idx = opts.index(default_val)
                        except: _def_idx = 0
                        chosen = st.selectbox(slot, opts, index=_def_idx, key=f"{key_prefix}_{slot}")
                        _sw = _slot_color(chosen)
                        if _sw != "transparent":
                            st.markdown(f'<div style="background:{_sw};height:5px;border-radius:0 0 3px 3px;margin-top:-4px;"></div>', unsafe_allow_html=True)
                        _show_person = covering_mode in ("nit", "allocation") or chosen in ("Lunch Cover", "Lunch Break")
                        if _show_person:
                            if chosen == "Lunch Cover": _ph, _lbl = "Teacher being released for lunch…", "👤 Releasing:"
                            elif chosen == "Lunch Break": _ph, _lbl = "Who is covering / releasing them…", "👤 Covered by:"
                            else: _ph, _lbl = "Name…", "Name"
                            st.markdown(f'<div style="font-size:0.6rem;color:#5a7a5a;font-weight:600;margin-top:2px;">{_lbl}</div>', unsafe_allow_html=True)
                            st.text_input(_lbl, value=stored_pers, key=f"{key_prefix}_p_{slot}", placeholder=_ph, label_visibility="collapsed")

        def _collect_ts(key_prefix, covering_mode):
            ts = {}
            for slot in PC_TIME_SLOTS:
                v = st.session_state.get(f"{key_prefix}_{slot}", "")
                p = st.session_state.get(f"{key_prefix}_p_{slot}", "")
                if v or p: ts[slot] = {"value": v, "person": p}
            return ts

        def _view_pc_entry(entry):
            if not entry.get("change_reason",""):
                st.markdown('<div class="empty-state"><div class="icon">📊</div>No change entered</div>', unsafe_allow_html=True)
                return
            reason = entry.get("change_reason","")
            absent = entry.get("staff_absent","")
            trt    = entry.get("trt", False)
            trt_nm = entry.get("trt_name","")
            smember = entry.get("staff_member","")
            rel    = entry.get("release_type","")
            meta = []
            if absent: meta.append(f"**Absent:** {absent}")
            if trt: meta.append(f"**TRT:** {trt_nm or '(name not entered)'}")
            else: meta.append("**No TRT**")
            if smember: meta.append(f"**Staff:** {smember} — {rel}")
            st.markdown(f"**{reason}** · " + " · ".join(meta))
            _tt = _pc_timetable_html(entry, dark=False)
            if _tt: st.markdown(_tt, unsafe_allow_html=True)

        for _i in range(_n_entries):
            _db_entry = _loaded_pc[_i] if _i < len(_loaded_pc) else _empty_pc()
            if not isinstance(_db_entry, dict) or "change_reason" not in _db_entry: _db_entry = _empty_pc()
            _db_ts    = _db_entry.get("time_slots", {})
            _db_allocs = _db_entry.get("staff_allocations", [])
            _exp_title = f"📋 Program Change #{_i+1}"
            reason_now = st.session_state.get(f"pc_reason_{_i}", _db_entry.get("change_reason",""))
            sa_now     = st.session_state.get(f"pc_sa_{_i}", _db_entry.get("staff_absent",""))
            if sa_now: _exp_title = f"📋 #{_i+1} — {reason_now}: {sa_now}"
            with st.expander(_exp_title, expanded=(_i == 0 or bool(reason_now))):
                if not edit:
                    _view_pc_entry(_db_entry)
                    continue
                _clc, _ = st.columns([1,5])
                with _clc:
                    if st.button("🗑️ Clear", key=f"pc_clr_{_i}", help="Clear this entry"):
                        _keys_to_del = [f"pc_reason_{_i}", f"pc_sa_{_i}", f"pc_trt_{_i}", f"pc_trt_name_{_i}", f"pc_covering_{_i}", f"pc_prog_{_i}", f"pc_smember_{_i}", f"pc_release_{_i}", f"pc_alloc_n_{_i}"]
                        _n_a = st.session_state.get(f"pc_alloc_n_{_i}", len(_db_allocs) or 1)
                        for _aj in range(_n_a):
                            _keys_to_del += [f"pc_alloc_name_{_i}_{_aj}", f"pc_alloc_norm_{_i}_{_aj}"]
                            for _sl in PC_TIME_SLOTS: _keys_to_del += [f"pc_alloc_{_i}_{_aj}_{_sl}", f"pc_alloc_{_i}_{_aj}_p_{_sl}"]
                        for _tsl in PC_TIME_SLOTS: _keys_to_del += [f"pc_trt_{_i}_{_tsl}", f"pc_trt_{_i}_p_{_tsl}"]
                        for _k in _keys_to_del: st.session_state.pop(_k, None)
                        st.rerun()
                st.markdown("---")
                st.markdown('<div style="background:#1a2e44;color:white;font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:6px;">Step 1 — Reason for change</div>', unsafe_allow_html=True)
                _reason_opts = ["— Select —", "Staff Absence", "Site Need"]
                try: _r_idx = _reason_opts.index(_db_entry.get("change_reason",""))
                except: _r_idx = 0
                _reason = st.radio("Change reason", _reason_opts, index=_r_idx, key=f"pc_reason_{_i}", horizontal=True, label_visibility="collapsed")
                if _reason not in ("Staff Absence", "Site Need"): continue
                st.markdown("---")
                if _reason == "Staff Absence":
                    st.markdown('<div style="background:#4a7fb5;color:white;font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:6px;">Step 2 — Who is absent?</div>', unsafe_allow_html=True)
                    st.text_input("Absent staff member", value=_db_entry.get("staff_absent",""), key=f"pc_sa_{_i}", placeholder="e.g. John Smith", label_visibility="collapsed")
                    st.markdown("---")
                _step_n = 3 if _reason == "Staff Absence" else 2
                st.markdown(f'<div style="background:#6a4a9a;color:white;font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:6px;">Step {_step_n} — Is a TRT covering?</div>', unsafe_allow_html=True)
                _trt = st.checkbox("Yes — a TRT is coming in", value=bool(_db_entry.get("trt", False)), key=f"pc_trt_{_i}")
                if _trt:
                    st.text_input("TRT name", value=_db_entry.get("trt_name",""), key=f"pc_trt_name_{_i}", placeholder="e.g. Ms Jones")
                    st.markdown("---")
                    st.markdown(f'<div style="background:#4a8f33;color:white;font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:6px;">Step {_step_n+1} — What is the TRT covering?</div>', unsafe_allow_html=True)
                    _cov_opts = ["Program", "NIT"]
                    try: _cov_idx = _cov_opts.index(_db_entry.get("covering","Program"))
                    except: _cov_idx = 0
                    _covering = st.radio("TRT covering", _cov_opts, index=_cov_idx, key=f"pc_covering_{_i}", horizontal=True, label_visibility="collapsed")
                    if _covering == "Program":
                        st.markdown("---")
                        _prog_opts = ["JP", "PY", "SY"]
                        try: _prog_idx = _prog_opts.index(_db_entry.get("program","JP"))
                        except: _prog_idx = 0
                        _prog = st.radio("Program", _prog_opts, index=_prog_idx, key=f"pc_prog_{_i}", horizontal=True, label_visibility="collapsed")
                        st.markdown("---")
                        _render_timetable_edit(f"pc_trt_{_i}", "program", _db_ts, prog_default=_prog)
                    else:
                        st.markdown("---")
                        _render_timetable_edit(f"pc_trt_{_i}", "nit", _db_ts)
                else:
                    if _reason == "Staff Absence":
                        st.markdown("---")
                        st.markdown('<div style="background:#b91c1c;color:white;font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:6px;">Step 4 — No TRT: allocate existing staff to cover the day</div>', unsafe_allow_html=True)
                        _alloc_key = f"pc_alloc_n_{_i}"
                        if _alloc_key not in st.session_state: st.session_state[_alloc_key] = max(1, len(_db_allocs))
                        _n_allocs = st.session_state[_alloc_key]
                        for _j in range(_n_allocs):
                            _db_alloc = _db_allocs[_j] if _j < len(_db_allocs) else _empty_alloc()
                            _alloc_ts = _db_alloc.get("time_slots", {})
                            st.markdown(f'<div style="background:#f0f4f0;border:1.5px solid #c8dcc0;border-left:4px solid #6BBF4E;border-radius:8px;padding:10px 12px;margin:8px 0 4px;"><div style="font-size:0.72rem;font-weight:700;color:#1a2e44;margin-bottom:6px;">👤 Staff Member #{_j+1}</div>', unsafe_allow_html=True)
                            _an1, _an2, _an3 = st.columns([2,2,1])
                            with _an1: st.text_input("Staff member name", value=_db_alloc.get("name",""), key=f"pc_alloc_name_{_i}_{_j}", placeholder="e.g. Sarah")
                            with _an2:
                                _norm_opts = ["","JP","PY","SY","NIT","Other"]
                                try: _norm_idx = _norm_opts.index(_db_alloc.get("normal_prog",""))
                                except: _norm_idx = 0
                                st.selectbox("Their normal program/role", _norm_opts, index=_norm_idx, key=f"pc_alloc_norm_{_i}_{_j}")
                            with _an3:
                                st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                                if st.button("🗑️", key=f"pc_alloc_del_{_i}_{_j}", help="Remove this allocation"):
                                    for _sl in PC_TIME_SLOTS:
                                        st.session_state.pop(f"pc_alloc_{_i}_{_j}_{_sl}", None)
                                        st.session_state.pop(f"pc_alloc_{_i}_{_j}_p_{_sl}", None)
                                    st.session_state.pop(f"pc_alloc_name_{_i}_{_j}", None)
                                    st.session_state.pop(f"pc_alloc_norm_{_i}_{_j}", None)
                                    st.session_state[_alloc_key] = max(1, _n_allocs - 1)
                                    st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                            _render_timetable_edit(f"pc_alloc_{_i}_{_j}", "allocation", _alloc_ts)
                        if st.button(f"➕ Add another staff member", key=f"pc_alloc_add_{_i}"):
                            st.session_state[_alloc_key] = _n_allocs + 1; st.rerun()
                    else:
                        st.markdown("---")
                        st.text_input("Staff member name", value=_db_entry.get("staff_member",""), key=f"pc_smember_{_i}", placeholder="e.g. Sarah", label_visibility="collapsed")
                        _rel_opts = ["— Select —", "Receiving release time", "Covering release time for staff member", "Covering Lunch cover"]
                        try: _rel_idx = _rel_opts.index(_db_entry.get("release_type",""))
                        except: _rel_idx = 0
                        st.radio("Role", _rel_opts, index=_rel_idx, key=f"pc_release_{_i}", horizontal=False, label_visibility="collapsed")

        if edit:
            if st.button("➕ Add another program change", key="pc_add_entry", type="secondary"):
                st.session_state[_pc_state_key] = _n_entries + 1; st.rerun()
        if edit:
            _collected_pc = []
            for _i in range(_n_entries):
                _reason_val = st.session_state.get(f"pc_reason_{_i}", "")
                _trt_val    = st.session_state.get(f"pc_trt_{_i}", False)
                _trt_ts     = _collect_ts(f"pc_trt_{_i}", st.session_state.get(f"pc_covering_{_i}", ""))
                _alloc_n    = st.session_state.get(f"pc_alloc_n_{_i}", len(_loaded_pc[_i].get("staff_allocations",[]) if _i < len(_loaded_pc) else []))
                _allocs     = []
                for _j in range(max(_alloc_n, 0)):
                    _a_ts = _collect_ts(f"pc_alloc_{_i}_{_j}", "allocation")
                    _allocs.append({"name": st.session_state.get(f"pc_alloc_name_{_i}_{_j}", ""), "normal_prog": st.session_state.get(f"pc_alloc_norm_{_i}_{_j}", ""), "time_slots": _a_ts})
                _collected_pc.append({"change_reason": _reason_val, "staff_absent": st.session_state.get(f"pc_sa_{_i}", ""), "trt": _trt_val, "trt_name": st.session_state.get(f"pc_trt_name_{_i}", ""), "covering": st.session_state.get(f"pc_covering_{_i}", ""), "program": st.session_state.get(f"pc_prog_{_i}", ""), "time_slots": _trt_ts, "staff_allocations": _allocs, "staff_member": st.session_state.get(f"pc_smember_{_i}", ""), "release_type": st.session_state.get(f"pc_release_{_i}", "")})
            bulletin_data["program_changes"] = _collected_pc

    st.markdown('</div>', unsafe_allow_html=True)

    if edit:
        bsv1, bsv2, bsv3 = st.columns([2, 2, 6])
        with bsv1:
            if st.button("💾 Save Bulletin", type="primary", use_container_width=True, key="bottom_save"):
                st.session_state["_pending_save"] = True
        with bsv2:
            if st.button("🚪 Discard & Exit", type="secondary", use_container_width=True, key="bottom_discard"):
                st.session_state.edit_mode = False; st.rerun()

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
    st.markdown("""<div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;padding:1.5rem 2rem;margin-bottom:1.5rem;color:white;"><div style="font-size:1.3rem;font-weight:700;margin-bottom:0.3rem;">📝 Add a Staff Notice</div><div style="font-size:0.85rem;opacity:0.85;">No password needed. Your notice will appear on today's bulletin and the staff room display screen straight away.</div></div>""", unsafe_allow_html=True)
    qa_col, preview_col = st.columns([1, 1])
    with qa_col:
        with st.form("quick_add_form", clear_on_submit=True):
            qa_name  = st.text_input("Your name *", placeholder="e.g. Sarah")
            qa_cat   = st.selectbox("Category *", list(NOTICE_CATS.keys()))
            qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3")
            qa_body  = st.text_area("Details", placeholder="Any additional info… (optional)", height=120)
            qa_date  = st.date_input("For which day?", value=date.today())
            qa_ok    = st.form_submit_button("📢 Post Notice", type="primary", use_container_width=True)
            if qa_ok:
                if not qa_name.strip(): st.warning("Please enter your name.")
                elif not qa_title.strip(): st.warning("Please enter a title.")
                else:
                    save_notice({"submitted_by": qa_name.strip(), "category": qa_cat, "title": qa_title.strip(), "body": qa_body.strip(), "notice_date": str(qa_date)})
                    st.success(f"✅ Notice posted for {qa_date.strftime('%-d %B')}! It's now live on the bulletin.")
                    st.balloons()
    with preview_col:
        st.markdown("**Category guide:**")
        for cat, cfg in NOTICE_CATS.items():
            st.markdown(f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;"><span style="background:{cfg["bg"]};color:{cfg["color"]};font-size:0.72rem;font-weight:700;padding:0.2rem 0.6rem;border-radius:20px;min-width:90px;text-align:center;">{cfg["emoji"]} {cat}</span></div>', unsafe_allow_html=True)
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
                st.markdown(f'<div style="background:white;border-radius:10px;border-left:4px solid {nc["color"]};padding:0.75rem 1rem;margin-bottom:0.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);"><div style="margin-bottom:0.2rem;"><span style="background:{nc["bg"]};color:{nc["color"]};font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;padding:0.15rem 0.5rem;border-radius:20px;">{nc["emoji"]} {cat}</span><span style="font-size:0.7rem;color:#9ab09a;margin-left:0.5rem;">from {n.get("submitted_by","")}</span></div><div style="font-size:0.9rem;font-weight:700;color:#1a2e44;margin:0.3rem 0 0.2rem;">{n.get("title","")}</div><div style="font-size:0.82rem;color:#3a4a3a;line-height:1.5;">{n.get("body","") or ""}</div></div>', unsafe_allow_html=True)
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
        terms_map = {1:(date(y,1,28),date(y,4,11)), 2:(date(y,4,28),date(y,7,4)), 3:(date(y,7,21),date(y,9,26)), 4:(date(y,10,13),date(y,12,12))}
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
            if not t_start: st.info("Date is outside term dates.")
        if results:
            for row in results:
                d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                label = d.strftime("%A %-d %B %Y")
                fact = row.get("fun_fact","")
                st.markdown(f'<div class="arch-card"><div class="arch-card-date">{label}</div><div class="arch-card-fact">💡 {fact if fact else "No fun fact recorded"}</div></div>', unsafe_allow_html=True)
                if st.button(f"Open →", key=f"arch_{row['date']}"):
                    st.session_state.selected_date = d; st.rerun()
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
                        st.session_state.selected_date = d; st.rerun()
            else:
                st.markdown(f'<div class="empty-state"><div class="icon">🔍</div>No results for "{keyword}"</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB: STAFF LOGIN
# ══════════════════════════════════════════════════════════════
with login_tab:
    if st.session_state.authenticated:
        st.success("✅ You are logged in as Staff")
        st.markdown("You can now edit bulletins — head to the **📋 Bulletin** tab and click **✏️ Edit**.")
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
