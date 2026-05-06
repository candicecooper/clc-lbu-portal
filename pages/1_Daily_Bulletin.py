import streamlit as st
from datetime import date, timedelta, datetime
import database as db
import json
import time as _time

st.set_page_config(
    page_title="CLC Daily Bulletin",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from auth import logout_button, get_staff_name
logout_button("sidebar")

# ── DESIGN SYSTEM ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"]{background:#f0f4f0!important;font-family:'DM Sans',sans-serif}
[data-testid="stAppViewContainer"]{padding:0}
[data-testid="stHeader"]{display:none}
[data-testid="stSidebar"]{display:none}
#MainMenu,footer,.stDeployButton{display:none}
.main .block-container{padding:0!important;max-width:100%!important}
.top-nav{background:#1a2e44;padding:0 2rem;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:1000;box-shadow:0 2px 12px rgba(0,0,0,0.2)}
.top-nav-left{display:flex;align-items:center;gap:.75rem}
.top-nav-logo{width:32px;height:32px;background:linear-gradient(135deg,#6BBF4E,#4a8f33);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;color:white;font-size:.85rem}
.top-nav-title{font-family:'DM Sans',sans-serif;font-weight:700;font-size:.95rem;color:white;letter-spacing:.02em}
.top-nav-sub{font-size:.72rem;color:rgba(255,255,255,0.5);letter-spacing:.06em;text-transform:uppercase}
.nav-badge{background:rgba(107,191,78,0.2);border:1px solid rgba(107,191,78,0.4);color:#6BBF4E;font-size:.72rem;font-weight:600;padding:.2rem .6rem;border-radius:20px;letter-spacing:.05em}
.nav-badge.edit{background:rgba(232,161,37,0.2);border-color:rgba(232,161,37,0.4);color:#e8a125}
.bulletin-hero{background:linear-gradient(135deg,#3d7a28 0%,#6BBF4E 60%,#8fd468 100%);padding:1.75rem 2rem 1.5rem;position:relative;overflow:hidden}
.bulletin-hero::before{content:'';position:absolute;top:-40px;right:-40px;width:200px;height:200px;background:rgba(255,255,255,0.06);border-radius:50%}
.bulletin-hero-inner{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;position:relative;z-index:1}
.bulletin-date-label{font-family:'DM Mono',monospace;font-size:.7rem;color:rgba(255,255,255,0.7);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.3rem}
.bulletin-date-main{font-family:'Playfair Display',serif;font-size:2rem;color:white;font-weight:700;line-height:1.1}
.bulletin-date-sub{font-size:.85rem;color:rgba(255,255,255,0.75);margin-top:.25rem;font-weight:400}
.content-area{padding:1.5rem 2rem 3rem;max-width:1600px;margin:0 auto}
.section-card{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);overflow:hidden;margin-bottom:1.25rem}
.section-card-header{padding:.6rem 1rem;display:flex;align-items:center;gap:.5rem}
.section-card-header.green{background:#6BBF4E}
.section-card-header.navy{background:#1a2e44}
.section-card-header.brown{background:#A67C6A}
.section-card-header.amber{background:#e8a125}
.section-card-header.blue{background:#4a7fb5}
.section-card-header.purple{background:#7a5bb5}
.section-card-header.slate{background:#6a7f8a}
.section-card-header.red{background:#c0392b}
.section-card-header h3{font-size:.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.1em;margin:0}
.section-card-header.amber h3{color:#1a2e44}
.section-card-body{padding:.75rem}
.data-table{width:100%;border-collapse:collapse;font-size:.78rem}
.data-table th{background:#f4f8f2;color:#4a6640;font-weight:600;font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;padding:.4rem .6rem;text-align:left;border-bottom:2px solid #d8ead2}
.data-table td{padding:.4rem .6rem;border-bottom:1px solid #f0f4ee;color:#2a3a2a;vertical-align:top}
.data-table tr:last-child td{border-bottom:none}
.data-table tr:hover td{background:#fafcf9}
.change-badge{background:#fee2e2;color:#b91c1c;padding:.1rem .45rem;border-radius:4px;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.kitchen-row td{background:#fff8e6!important;font-weight:600}
.kitchen-badge{background:#e8a125;color:#1a2e44;padding:.15rem .5rem;border-radius:4px;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.vehicle-time{font-family:'DM Mono',monospace;font-size:.72rem;color:#888}
.vehicle-booking{background:#e8f5e1;color:#2d6b1a;padding:.1rem .4rem;border-radius:4px;font-size:.75rem;font-weight:500}
[data-baseweb="tab-list"]{background:transparent!important;gap:.25rem!important;border-bottom:2px solid #e0e8dc!important;padding:0!important}
[data-baseweb="tab"]{background:transparent!important;border-radius:8px 8px 0 0!important;padding:.5rem 1rem!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important;font-weight:600!important;color:#7a907a!important;border:none!important}
[aria-selected="true"][data-baseweb="tab"]{background:white!important;color:#4a8f33!important;border-bottom:2px solid #6BBF4E!important}
[data-baseweb="tab-panel"]{padding:1rem 0 0!important}
.stTextInput input,.stTextArea textarea,.stSelectbox select{border:1.5px solid #d8e8d4!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important;background:white!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:#6BBF4E!important;box-shadow:0 0 0 3px rgba(107,191,78,0.15)!important}
label[data-testid="stWidgetLabel"] p{font-size:.72rem!important;font-weight:600!important;color:#5a7a5a!important;text-transform:uppercase!important;letter-spacing:.06em!important}
.stButton button{border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-weight:600!important;font-size:.85rem!important}
.stButton button[kind="primary"]{background:#4a8f33!important;border:none!important}
.stButton button[kind="primary"]:hover{background:#3d7a28!important}
[data-testid="stDataEditor"]{border:1.5px solid #d8e8d4!important;border-radius:10px!important;overflow:hidden}
.arch-card{background:white;border:1.5px solid #e0e8dc;border-left:4px solid #6BBF4E;border-radius:10px;padding:.85rem 1rem;margin-bottom:.6rem}
.arch-card-date{font-weight:700;font-size:.9rem;color:#1a2e44}
.arch-card-fact{font-size:.78rem;color:#7a907a;margin-top:.2rem}
.empty-state{text-align:center;padding:2rem;color:#9ab09a;font-size:.85rem}
.empty-state .icon{font-size:2rem;margin-bottom:.5rem}
.auth-gate{max-width:400px;margin:4rem auto;background:white;border-radius:16px;padding:2.5rem;box-shadow:0 8px 32px rgba(0,0,0,0.1);text-align:center}
@media(max-width:768px){.bulletin-date-main{font-size:1.4rem}.content-area{padding:1rem}}
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
        "authenticated": False, "edit_mode": False,
        "selected_date": _default_date(), "page": "bulletin",
        "show_login": False, "show_inline_login": False,
        "_pc_form_id": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "clcstaff2026")

TRANSPORT_OPTIONS = ["Taxi","Parent/Carer","Other"]
CHANGE_TYPE_OPTIONS = ["Early Departure","Late Arrival","No Show","Alternative Pickup","Alternative Drop-off","Absent - not attending","Other"]
VISITOR_REASON_OPTIONS = ["Student Observation","Meeting with Leadership","Meeting with Teacher","TAC","Review/Transition Meeting","Support","Other"]

def _migrate_travel_rows(rows):
    migrated = []
    for r in rows:
        if "Transport To" in r or "Transport From" in r or "Times" in r:
            migrated.append({
                "Student": r.get("Student",""),
                "Arrival Time": r.get("Times",""),
                "Departure Time": "",
                "Transport": r.get("Transport To","") or r.get("Transport From",""),
            })
        else:
            migrated.append(r)
    return migrated

# ── HELPERS ───────────────────────────────────────────────────
def week_dates(d):
    monday = d - timedelta(days=d.weekday())
    return [monday + timedelta(days=i) for i in range(5)]

def term_label(d):
    y = d.year
    terms = {1:(date(y,1,28),date(y,4,11)), 2:(date(y,4,28),date(y,7,4)),
              3:(date(y,7,21),date(y,9,26)), 4:(date(y,10,13),date(y,12,12))}
    for t,(s,e) in terms.items():
        if s <= d <= e: return f"Term {t} \u00b7 {y}"
    return str(y)

def default_bulletin():
    return {
        "fun_fact": "",
        "staff_absent": [{"Staff Member":"","TRT":""} for _ in range(4)],
        "student_absent": [{"Student":"","Program":"","Reason":""} for _ in range(4)],
        "excursions": [{"Program":"","Staff Member":"","Time Departing":"","Time Returning":"","Location":""} for _ in range(4)],
        "staff_meetings": [{"Type":"","Staff Member":"","Location":"","Time Departing":"","Time Returning":"","Student":""} for _ in range(4)],
        "entry_meetings": [{"Time":"","Program":"","Student":""} for _ in range(4)],
        "additional_messages": [{"Staff Name":"","Details":""} for _ in range(4)],
        "visitors_on_site": [{"Visitor Name":"","Reason":"","Staff Responsible":"","Arriving":"","Departing":"","Location":""} for _ in range(4)],
        "travel_jp": [{"Student":"","Arrival Time":"","Departure Time":"","Transport":""} for _ in range(5)],
        "travel_py": [{"Student":"","Arrival Time":"","Departure Time":"","Transport":""} for _ in range(5)],
        "travel_sy": [{"Student":"","Arrival Time":"","Departure Time":"","Transport":""} for _ in range(5)],
        "travel_changes": [{"Student":"","Program":"","Change Type":"","Reason":"","Time":"","How Departed":""} for _ in range(3)],
        "vehicle_bookings": [],
        "staff_responsibilities": {"kitchen_duties":"","meeting_pd_focus":"","chair":"","minutes":""},
        "nit_booking": "",
        "program_changes": []
    }

def load_bulletin(d):
    data = db.get_bulletin(d)
    defaults = default_bulletin()
    if not data:
        data = defaults.copy()
    else:
        for k, v in defaults.items():
            if k not in data: data[k] = v
    vb = data.get("vehicle_bookings", [])
    if isinstance(vb, dict):
        converted = []
        for t, v in vb.items():
            if v.get("van",""): converted.append({"vehicle":"Van","booker":v["van"],"whole_day":True,"start_time":"","end_time":""})
            if v.get("kia",""): converted.append({"vehicle":"Kia","booker":v["kia"],"whole_day":True,"start_time":"","end_time":""})
        data["vehicle_bookings"] = converted
    for tk in ("travel_jp","travel_py","travel_sy"):
        data[tk] = _migrate_travel_rows(data.get(tk, []))
    # Migrate old combined staff_absent → separate staff_absent + student_absent
    old_sa = data.get("staff_absent", [])
    if old_sa and isinstance(old_sa[0], dict) and "Staff Absence" in old_sa[0]:
        data["staff_absent"]   = [{"Staff Member": r.get("Staff Absence",""), "TRT": r.get("TRT","")} for r in old_sa if (r.get("Staff Absence") or "").strip()]
        data["student_absent"] = [{"Student": r.get("Student Absence",""), "Program": r.get("Program",""), "Reason": r.get("Reason","")} for r in old_sa if (r.get("Student Absence") or "").strip()]
        if not data["staff_absent"]:   data["staff_absent"]   = [{"Staff Member":"","TRT":""} for _ in range(4)]
        if not data["student_absent"]: data["student_absent"] = [{"Student":"","Program":"","Reason":""} for _ in range(4)]
    sr = data.get("staff_responsibilities", {})
    resp_keys = ["kitchen_duties", "meeting_pd_focus", "chair", "minutes"]
    is_empty = not any((sr.get(k) or "").strip() for k in resp_keys)
    monday = d - timedelta(days=d.weekday())
    if is_empty and d != monday:
        monday_data = db.get_bulletin(monday)
        if monday_data:
            monday_sr = monday_data.get("staff_responsibilities", {})
            if any((monday_sr.get(k) or "").strip() for k in resp_keys):
                data["staff_responsibilities"] = monday_sr
    if not (data.get("fun_fact") or "").strip():
        data["fun_fact"] = daily_fun_fact(d)
    return data

# ── NOTICE HELPERS ────────────────────────────────────────────
NOTICE_CATS = {
    "General":      {"color":"#4a8f33","bg":"#e8f5e1","emoji":"\U0001f4e2"},
    "Reminder":     {"color":"#c97b1a","bg":"#fff3e0","emoji":"\u23f0"},
    "Urgent":       {"color":"#b91c1c","bg":"#fee2e2","emoji":"\U0001f6a8"},
    "Student Info": {"color":"#1d4ed8","bg":"#dbeafe","emoji":"\U0001f468\u200d\U0001f393"},
    "Facilities":   {"color":"#6d28d9","bg":"#ede9fe","emoji":"\U0001f3eb"},
    "Wellbeing":    {"color":"#0e7490","bg":"#cffafe","emoji":"\U0001f49a"},
}

# ── PROGRAM CHANGES ───────────────────────────────────────────
PC_TIME_SLOTS = [
    "9:00","9:15","9:30","9:45",
    "10:00","10:15","10:30","10:45",
    "11:00","11:15","11:30","11:45",
    "12:00","12:15","12:30","12:45",
    "1:00","1:15","1:30","1:45",
    "2:00","2:15","2:30","2:45",
]
PC_TIME_SLOTS_30 = [s for s in PC_TIME_SLOTS if s.endswith(":00") or s.endswith(":30")]

ROLE_OPTIONS = ["", "JP", "PY", "SY", "NIT", "Lunch Cover", "Lunch Break",
                "Release", "Planning", "Meeting", "Other"]

ROLE_COLORS = {
    "JP":"#dbeafe","PY":"#ede9fe","SY":"#fef3c7","NIT":"#f1f5f9",
    "Lunch Cover":"#fef9c3","Lunch Break":"#cffafe","Release":"#dcfce7",
    "Planning":"#fce7f3","Meeting":"#fef3c7","Other":"#f3f4f6",
}
ROLE_COLORS_DARK = {
    "JP":"#1d4ed8","PY":"#6d28d9","SY":"#92400e","NIT":"#374151",
    "Lunch Cover":"#856404","Lunch Break":"#004085","Release":"#166534",
    "Planning":"#9d174d","Meeting":"#78350f","Other":"#4b5563",
}

def _slot_color_bg(val): return ROLE_COLORS.get(val, "#f9fafb")
def _slot_color_fg(val): return ROLE_COLORS_DARK.get(val, "#374151")

def _t2m(ts):
    try:
        h, m = str(ts).strip().split(":")
        h, m = int(h), int(m)
        if h < 9: h += 12
        return h * 60 + m
    except Exception:
        return -1

def blocks_to_slots(blocks, slot_list=None):
    if slot_list is None: slot_list = PC_TIME_SLOTS
    result = {s: {"value":"","person":""} for s in slot_list}
    for slot in slot_list:
        sm = _t2m(slot)
        best = None; best_bs = -1
        for block in (blocks or []):
            bs = _t2m(block.get("start","")); be = _t2m(block.get("end",""))
            if bs >= 0 and be > bs and bs <= sm < be:
                result[slot] = {"value": block.get("role",""), "person": block.get("person","")}
                break
            if bs < 0 or be <= bs: continue
            if bs <= sm <= be and bs > best_bs: best = block; best_bs = bs
        if best: result[slot] = {"value": best.get("role",""), "person": best.get("person","")}
    return result

def _pc_row_html(label, normal_prog, ts, slot_list=None, dark=False):
    if slot_list is None: slot_list = PC_TIME_SLOTS
    text = "#1a2e44" if not dark else "#c8d8c8"
    fs = "0.56rem" if dark else "0.62rem"
    lbl_c = "#1a2e44" if not dark else "#6BBF4E"
    bdr = "#e0e8dc" if not dark else "#2a3d2a"
    td_cells = ""
    for slot in slot_list:
        raw = ts.get(slot, {})
        val = raw.get("value","") if isinstance(raw,dict) else str(raw)
        person = raw.get("person","") if isinstance(raw,dict) else ""
        bg = _slot_color_bg(val); fg = _slot_color_fg(val) if val else text
        disp = val if val else ("\u00b7" if not dark else "")
        inner = f'<span style="font-weight:700;font-size:{fs};">{disp}</span>'
        if person:
            arrow = "\u2192" if val == "Lunch Cover" else ("\u21a9" if val == "Lunch Break" else "")
            inner += f'<br><span style="font-size:0.85em;opacity:0.75;">{arrow} {person}</span>'
        td_cells += f'<td style="background:{bg};color:{fg};text-align:center;padding:2px 1px;min-width:30px;vertical-align:top;border-right:1px solid {bdr};">{inner}</td>'
    lbl_html = (f'<td style="white-space:nowrap;padding:3px 8px 3px 4px;color:{lbl_c};font-weight:700;font-size:{fs};vertical-align:middle;border-right:2px solid {"#6BBF4E" if not dark else "#4a8f33"};">'
                f'{label}' + (f'<br><span style="font-weight:400;opacity:0.65;font-size:0.9em;">{normal_prog}</span>' if normal_prog else "") + f'</td>')
    return f'<tr>{lbl_html}{td_cells}</tr>'

def _timetable_grid_html(staff_rows, slot_list=None, dark=False):
    if slot_list is None: slot_list = PC_TIME_SLOTS
    if not staff_rows: return ""
    th_bg = "#f4f8f2" if not dark else "#111e11"
    hdr = "#4a6640" if not dark else "#6BBF4E"
    bdr = "#e0e8dc" if not dark else "#2a3d2a"
    bdr2 = "#6BBF4E" if not dark else "#4a8f33"
    th_cells = (f'<th style="white-space:nowrap;padding:3px 8px 3px 4px;background:{th_bg};color:{hdr};font-size:0.5rem;border-right:2px solid {bdr2};">Staff / Role</th>'
                + "".join([f'<th style="background:{th_bg};color:{hdr};font-size:0.48rem;padding:1px 2px;text-align:center;white-space:nowrap;border-right:1px solid {bdr};">{s}</th>' for s in slot_list]))
    rows_html = ""
    for row in staff_rows:
        name = row.get("name",""); normal = row.get("normal_prog",""); blocks = row.get("blocks",[])
        ts = row.get("time_slots")
        if ts is None: ts = blocks_to_slots(blocks, slot_list)
        if any((v.get("value","") if isinstance(v,dict) else v) for v in ts.values()):
            rows_html += _pc_row_html(name, normal, ts, slot_list, dark)
    if not rows_html: return ""
    return (f'<div style="overflow-x:auto;margin-top:6px;"><table style="border-collapse:collapse;width:auto;">'
            f'<thead><tr>{th_cells}</tr></thead><tbody>{rows_html}</tbody></table></div>')

# ── SUPABASE / FACTS ──────────────────────────────────────────
_AUS_FACTS = [
    "Australia is the only continent that is also a single country \u2014 and somehow still can\u2019t decide where to put its capital.",
    "Kangaroos can\u2019t walk backwards, which is why they\u2019re on the Australian coat of arms \u2014 always moving forward, mate.",
    "Australia has more kangaroos than people. The roos are winning.",
    "The Box Jellyfish has 24 eyes. It still can\u2019t see why Australians swim anywhere near it.",
    "A group of kangaroos is called a mob. Very on-brand for Australia.",
    "Wombats produce cube-shaped poo \u2014 the only animal in the world that does. Science still hasn\u2019t fully explained why.",
    "Australia has 10 of the world\u2019s 15 most venomous snakes. They\u2019re very proud of this.",
    "The Great Barrier Reef is the largest living structure on Earth \u2014 visible from space, yet invisible to politicians.",
    "Australian Rules Football was invented to keep cricketers fit during winter. Cricket: unintentionally very useful.",
    "The platypus is venomous, lays eggs, and has a bill like a duck. It looks like Australia designed it after a big night.",
    "Australians consume more than 1.9 billion Tim Tams per year \u2014 roughly 80 per person. This tracks.",
    "The Sydney Funnel-web Spider is considered the world\u2019s most dangerous spider. Sydney has strong opinions about everything.",
    "Australia once fought a war against emus. The emus won. This is true. Look it up.",
    "The Dingo Fence is 5,614 km long \u2014 built to keep dingoes out of southern Australia. The dingoes are biding their time.",
    "Eucalyptus leaves are mildly toxic to most animals. Koalas eat almost nothing else and sleep 22 hours a day. Icon behaviour.",
    "Australia has the longest straight stretch of railway in the world \u2014 478 km of perfectly straight track through the Nullarbor.",
    "Canberra was purpose-built as the capital because Sydney and Melbourne couldn\u2019t agree on which city deserved it. Classic.",
    "Australia has pink lakes. Lake Hillier on Middle Island is bubblegum pink year-round, and scientists still argue about why.",
    "The Thorny Devil lizard can drink through its feet by standing in water. Useful at a BBQ.",
    "Australia\u2019s first police force was made up of the most well-behaved convicts. Starting as you mean to go on.",
    "Australians invented WiFi. Also the black box flight recorder. And the bionic ear. But mostly WiFi.",
    "Drop bears are not real. Probably.",
    "The laughing kookaburra\u2019s call sounds exactly like a human laughing manically. Nobody finds this unsettling.",
    "Vegemite was invented in 1922 as a way to use leftover brewer\u2019s yeast. You\u2019re welcome, or sorry, depending on your position.",
    "Australians use the word \u2018reckon\u2019 as a sophisticated intellectual agreement mechanism. Fully reckon this is true.",
    "A baby kangaroo (joey) is about the size of a jellybean when born. It then spends six months in a pouch.",
    "The Australian dollar is made from polymer plastic, making it waterproof. Essential for a country surrounded by water.",
    "The Melbourne Cup is a public holiday in Victoria. Only Australians would make a horse race a reason to stop work.",
    "Quokkas are considered the happiest animal on Earth. They live on Rottnest Island. No predators, good weather \u2014 honestly same.",
    "Australian magpies remember human faces and will swoop people they dislike. They hold grudges. Do not underestimate them.",
    "South Australia was the first place in the world to give women the right to stand for parliament, back in 1894.",
    "The echidna and platypus are the only two mammals in the world that lay eggs. Both live in Australia, naturally.",
    "Australians say \u2018arvo\u2019 for afternoon, \u2018servo\u2019 for service station, and \u2018bottle-o\u2019 for bottle shop.",
    "There are more than 10,000 beaches in Australia. Visiting a new one every day would take 27 years.",
    "A mob of emus will methodically destroy a fence to get to crops. They have a system. They are organised.",
    "The Royal Flying Doctor Service covers 7.69 million square kilometres \u2014 the world\u2019s largest GP practice.",
    "Uluru extends 2.5 km underground \u2014 what you see is only a fraction of the full rock.",
    "Australians invented the Hills Hoist rotary clothesline. A genuine contribution to civilisation.",
    "The Australian Alps receive more snowfall than Switzerland in a good year. Nobody ever believes this.",
]

def daily_fun_fact(d):
    import hashlib
    seed = int(hashlib.md5(str(d).encode()).hexdigest(), 16)
    return _AUS_FACTS[seed % len(_AUS_FACTS)]

def _get_sb(): return db.get_supabase()

def load_notices(for_date=None):
    try:
        q = _get_sb().table("daily_notices").select("*").order("created_at", desc=False)
        if for_date: q = q.eq("notice_date", str(for_date))
        return q.execute().data or []
    except Exception as e:
        st.warning(f"\u26a0\ufe0f Could not load notices: {e}"); return []

def save_notice(row):
    try: _get_sb().table("daily_notices").insert(row).execute()
    except Exception as e: st.error(f"Could not save notice: {e}")

def load_scheduled_meetings(for_date=None):
    _DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    try:
        d = for_date or date.today()
        day_name = _DAY_NAMES[d.weekday()]
        res = _get_sb().table("tm_schedules").select("*").eq("show_in_bulletin", True).execute()
        meetings = []
        for r in (res.data or []):
            if (r.get("day_of_week") or "").strip().lower() == day_name.lower():
                prog = r.get("program","")
                prog_label = {"JP":"Junior Primary","PY":"Primary Years","SY":"Senior Years","STAFF":"All Staff","ADMIN":"Admin"}.get(prog, prog)
                meetings.append({"Type": r.get("schedule_name","Team Meeting"),"Staff Member": prog_label,"Location": r.get("location",""),"Time Departing": r.get("meeting_time",""),"Time Returning": "","Student": ""})
        return meetings
    except Exception: return []

def delete_notice(nid):
    try: _get_sb().table("daily_notices").delete().eq("id", nid).execute()
    except Exception as e: st.error(f"Could not delete notice: {e}")

def load_bulletin_changes(d):
    try:
        res = _get_sb().table("daily_changes").select("*").eq("bulletin_date", str(d)).order("created_at").execute()
        rows = res.data or []; result = []
        for r in rows:
            sr = r.get("staff_rows", [])
            if isinstance(sr, str):
                try: sr = json.loads(sr)
                except: sr = []
            result.append({**r, "staff_rows": sr})
        return result
    except Exception: return []

def save_bulletin_change(d, entry):
    try:
        data = {"bulletin_date": str(d),"reason": entry.get("reason",""),"staff_absent": entry.get("staff_absent",""),"has_trt": entry.get("has_trt", False),"trt_name": entry.get("trt_name",""),"staff_rows": json.dumps(entry.get("staff_rows",[])),}
        if entry.get("id"): res = _get_sb().table("daily_changes").update(data).eq("id", entry["id"]).execute()
        else: res = _get_sb().table("daily_changes").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e: st.error(f"Could not save change: {e}"); return None

def delete_bulletin_change(cid):
    try: _get_sb().table("daily_changes").delete().eq("id", cid).execute(); return True
    except Exception as e: st.error(f"Delete failed: {e}"); return False

def _build_plain_text_bc(changes, for_date):
    lines = [f"CLC PROGRAM CHANGES \u2014 {for_date.strftime('%A %-d %B %Y').upper()}", "="*52]
    for idx, ch in enumerate(changes, 1):
        reason = ch.get("reason",""); absent = ch.get("staff_absent",""); has_trt = ch.get("has_trt", False); trt_name = ch.get("trt_name","")
        lines.append(f"\n[{idx}] {reason.upper()}")
        if absent: lines.append(f"    Absent staff: {absent}")
        if has_trt: lines.append(f"    TRT on site:  {trt_name or '(name not recorded)'}")
        else: lines.append(f"    No TRT \u2014 internal staff adjustment")
        for row in ch.get("staff_rows",[]):
            name = row.get("name",""); normal = row.get("normal_prog",""); blocks = row.get("blocks",[])
            if not blocks: continue
            norm_str = f" [normally: {normal}]" if normal else ""
            lines.append(f"\n    {name}{norm_str}:")
            for block in sorted(blocks, key=lambda b: b.get("start","")):
                role = block.get("role",""); start = block.get("start",""); end = block.get("end",""); person = block.get("person","")
                if not role: continue
                detail = ""
                if role == "Lunch Cover" and person: detail = f" (releasing {person})"
                elif role == "Lunch Break" and person: detail = f" (covered by {person})"
                elif person: detail = f" \u2014 {person}"
                lines.append(f"      {start} \u2013 {end}: {role}{detail}")
    lines += ["", "="*52, "Cowandilla Learning Centre \u00b7 LBU Daily Bulletin"]
    return "\n".join(lines)

def _build_html_sheet_bc(changes, for_date):
    slot_list = PC_TIME_SLOTS_30
    def slot_td(val, person):
        bg = _slot_color_bg(val); fg = _slot_color_fg(val) if val else "#9ca3af"; disp = val if val else ""; arrow = ""
        if val == "Lunch Cover" and person: arrow = f'<br><small style="font-size:0.75em;opacity:0.75;">\u2192{person}</small>'
        elif val == "Lunch Break" and person: arrow = f'<br><small style="font-size:0.75em;opacity:0.75;">\u21a9{person}</small>'
        elif person: arrow = f'<br><small style="font-size:0.75em;opacity:0.75;">{person}</small>'
        return (f'<td style="background:{bg};color:{fg};text-align:center;padding:2px 1px;font-size:0.5rem;font-weight:600;border:1px solid #e5e7eb;min-width:38px;">{disp}{arrow}</td>')
    def tt_block(staff_rows):
        if not staff_rows: return ""
        header = "".join([f'<th style="background:#1a2e44;color:rgba(255,255,255,0.85);font-size:0.42rem;padding:2px 1px;text-align:center;border:1px solid #374151;white-space:nowrap;">{s}</th>' for s in slot_list])
        rows_html = ""
        for row in staff_rows:
            name = row.get("name","(Staff)"); normal = row.get("normal_prog",""); blocks = row.get("blocks",[]); ts = blocks_to_slots(blocks, slot_list)
            if not any(v.get("value","") for v in ts.values()): continue
            norm_str = f'<span style="font-weight:400;color:#6b7280;font-size:0.75em;"> ({normal})</span>' if normal else ""
            cells = "".join([slot_td(ts[s].get("value",""), ts[s].get("person","")) for s in slot_list])
            rows_html += f'<tr><td style="white-space:nowrap;padding:3px 8px;color:#1a2e44;font-weight:700;font-size:0.6rem;border:1px solid #e5e7eb;border-right:2px solid #6BBF4E;">{name}{norm_str}</td>{cells}</tr>'
        if not rows_html: return ""
        return (f'<table style="border-collapse:collapse;width:100%;table-layout:fixed;margin-top:8px;"><thead><tr><th style="background:#1a2e44;color:rgba(255,255,255,0.85);font-size:0.42rem;padding:2px 8px;border:1px solid #374151;text-align:left;">Staff / Role</th>{header}</tr></thead><tbody>{rows_html}</tbody></table>')
    changes_html = ""
    for idx, ch in enumerate(changes, 1):
        reason = ch.get("reason",""); absent = ch.get("staff_absent",""); has_trt = ch.get("has_trt", False); trt_name = ch.get("trt_name",""); staff_rows = ch.get("staff_rows",[])
        color = "#dc2626" if reason == "Staff Absence" else "#0e7490"
        meta = []
        if absent: meta.append(f"<strong>Absent:</strong> {absent}")
        if has_trt: meta.append(f"<strong>TRT on site:</strong> {trt_name or 'Name TBC'}")
        else: meta.append("<strong>No TRT \u2014 internal adjustment</strong>")
        changes_html += (f'<div style="background:white;border:1.5px solid #e5e7eb;border-left:5px solid {color};border-radius:8px;padding:12px 14px;margin-bottom:14px;page-break-inside:avoid;"><div style="font-size:0.85rem;font-weight:800;color:{color};margin-bottom:4px;">Change {idx} \u2014 {reason}</div><div style="font-size:0.78rem;color:#374151;margin-bottom:6px;">{" &nbsp;\u00b7&nbsp; ".join(meta)}</div>{tt_block(staff_rows)}</div>')
    legend = "".join([f'<span style="background:{_slot_color_bg(v)};color:{_slot_color_fg(v)};padding:2px 8px;border-radius:10px;font-size:0.62rem;font-weight:600;">{v}</span>' for v in ["JP","PY","SY","NIT","Lunch Cover","Lunch Break","Release","Planning"]])
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>CLC Program Changes</title><style>@page{{size:A4 landscape;margin:10mm 12mm}}body{{font-family:'Segoe UI',Arial,sans-serif;background:#f9fafb;margin:0;padding:14px;color:#1a2e44}}@media print{{body{{background:white;padding:0}}.no-print{{display:none!important}}}}.page{{background:white;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.08);padding:18px 22px}}</style></head><body><div class="page"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;border-bottom:2px solid #e5e7eb;padding-bottom:10px;"><div><div style="font-size:1rem;font-weight:800;color:#1a2e44;">\U0001f4ca CLC Program Changes</div><div style="font-size:0.75rem;color:#6b7280;">{for_date.strftime('%A %-d %B %Y')} &nbsp;\u00b7&nbsp; Cowandilla Learning Centre LBU</div></div><button class="no-print" onclick="window.print()" style="background:#1a2e44;color:white;border:none;padding:7px 14px;border-radius:6px;font-size:0.78rem;cursor:pointer;">\U0001f5a8\ufe0f Print / Save PDF</button></div><div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:12px;">{legend}</div>{changes_html}<div style="font-size:0.6rem;color:#9ca3af;margin-top:16px;text-align:center;border-top:1px solid #f3f4f6;padding-top:8px;">Cowandilla Learning Centre \u00b7 LBU Daily Bulletin \u00b7 Printed {date.today().strftime('%-d %B %Y')}</div></div></body></html>"""


# ══════════════════════════════════════════════════════════════
# DISPLAY MODE
# ══════════════════════════════════════════════════════════════
params = st.query_params
if params.get("display") == "true":
    import time
    if "display_date" not in st.session_state: st.session_state.display_date = date.today()
    if st.session_state.display_date < date.today(): st.session_state.display_date = date.today()
    today = st.session_state.display_date
    d_data = load_bulletin(today)
    if "display_last_refresh" not in st.session_state: st.session_state.display_last_refresh = time.time()
    if time.time() - st.session_state.display_last_refresh > 60:
        st.session_state.display_last_refresh = time.time(); st.session_state.display_date = date.today(); st.rerun()

    st.markdown("""<style>[data-testid="stAppViewContainer"]{background:#f4f8f2!important}.main .block-container{padding:0!important;max-width:100%!important}[data-testid="stHeader"]{display:none}#MainMenu,footer,.stDeployButton{display:none}[data-baseweb="tab-list"]{display:none!important}</style>""", unsafe_allow_html=True)
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    sr = d_data.get("staff_responsibilities", {}); fun = d_data.get("fun_fact","")
    st.markdown(f"""<style>
    .dp{{background:#ffffff;border:1px solid #d8ead8;border-radius:8px;overflow:hidden;margin-bottom:5px;box-shadow:0 1px 4px rgba(0,0,0,0.06)}}
    .dp-header{{padding:.3rem .6rem;font-size:.6rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:white}}
    .dp-header.green{{background:#4a8f33}}.dp-header.navy{{background:#1a2e44}}.dp-header.brown{{background:#7a5c4a}}
    .dp-header.amber{{background:#c97b1a;color:#1a2e44}}.dp-header.blue{{background:#3a6a9a}}
    .dp-header.purple{{background:#6a4a9a}}.dp-header.slate{{background:#4a5a6a}}.dp-header.red{{background:#c0392b}}
    .dp-body{{padding:.35rem .5rem}}
    .dt{{width:100%;border-collapse:collapse;font-size:.62rem;color:#1e3a1e;font-family:'DM Sans',sans-serif}}
    .dt th{{color:#6BBF4E;font-weight:600;font-size:.55rem;text-transform:uppercase;letter-spacing:.06em;padding:.2rem .3rem;border-bottom:1px solid #2a3d2a}}
    .dt td{{padding:.18rem .3rem;border-bottom:1px solid #e8f0e8;vertical-align:top;line-height:1.3}}
    .dt tr:last-child td{{border-bottom:none}}
    .dt-em{{color:#9aaa9a;font-style:italic;font-size:.55rem}}
    .vb-tag{{background:#e8f5e1;color:#2d6b1a;padding:.05rem .35rem;border-radius:3px;font-size:.6rem;font-weight:600}}
    .kitchen-val{{background:#c97b1a;border-radius:4px;padding:.1rem .4rem;color:#1a2e44;font-weight:800;font-size:.65rem;display:inline-block}}
    .resp-label{{font-size:.58rem;color:#6BBF4E;font-weight:600}}.resp-val{{font-size:.62rem;color:#2d3d2d}}
    .fact-bar{{background:#f0f8ee;border-top:2px solid #c8e0c8;padding:.4rem 1.5rem;font-size:.72rem;color:#3a5a3a;display:flex;align-items:center;gap:.75rem;font-family:'DM Sans',sans-serif}}
    .fact-label{{color:#e8a125;font-weight:700;font-size:.65rem;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}}
    .tc-badge{{background:#fee2e2;color:#b91c1c;padding:.05rem .35rem;border-radius:3px;font-size:.6rem;font-weight:700}}
    </style>
    <div style="background:linear-gradient(135deg,#1a4d8c 0%,#2d7d4f 100%);padding:.6rem 1.5rem;display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #6BBF4E;">
      <div><div style="font-family:'Playfair Display',serif;font-size:1.1rem;color:white;font-weight:700;">Cowandilla Learning Centre &mdash; Daily Bulletin</div>
      <div style="font-family:'DM Mono',monospace;font-size:1rem;color:#6BBF4E;font-weight:600;letter-spacing:.08em;">{today.strftime("%A %-d %B %Y").upper()}</div></div>
      <div style="display:flex;align-items:center;gap:1.5rem;">
        <div style="font-family:'DM Mono',monospace;font-size:1.4rem;color:#e8a125;font-weight:700;" id="live-clock">--:-- --</div>
        <a href="/?quickadd=true" style="background:rgba(107,191,78,0.2);border:1px solid rgba(107,191,78,0.5);color:#6BBF4E;font-family:'DM Sans',sans-serif;font-size:.68rem;font-weight:600;padding:.3rem .85rem;border-radius:6px;text-decoration:none;">\U0001f4dd Quick Add</a>
        <a href="/?from_display=true" style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.18);color:rgba(255,255,255,0.55);font-family:'DM Sans',sans-serif;font-size:.68rem;font-weight:600;padding:.3rem .85rem;border-radius:6px;text-decoration:none;">\u270f\ufe0f Staff Access</a>
      </div></div>""", unsafe_allow_html=True)

    prev_day = today - timedelta(days=1); next_day = today + timedelta(days=1)
    dn1, dn2, dn3, dn4 = st.columns([1,4,1,1])
    with dn1:
        if st.button(f"\u2190 {prev_day.strftime('%a %-d %b')}", key="dn_prev", use_container_width=True): st.session_state.display_date = prev_day; st.rerun()
    with dn2:
        st.markdown(f'<div style="text-align:center;color:#2d7d4f;font-size:.75rem;font-weight:700;font-family:DM Mono,monospace;letter-spacing:.08em;padding:.45rem 0;">VIEWING: {today.strftime("%A %-d %B %Y").upper()}</div>', unsafe_allow_html=True)
    with dn3:
        if st.button(f"{next_day.strftime('%a %-d %b')} \u2192", key="dn_next", use_container_width=True): st.session_state.display_date = next_day; st.rerun()
    with dn4:
        if st.button("Today", key="dn_today", use_container_width=True): st.session_state.display_date = date.today(); st.rerun()

    def tbl_rows(rows, keys):
        filtered = [r for r in rows if any(r.get(k,"") for k in keys)]
        if not filtered: return '<tr><td colspan="20" class="dt-em">None today</td></tr>'
        return "".join(["<tr>"+"".join([f"<td>{r.get(k,'')}</td>" for k in keys])+"</tr>" for r in filtered])

    d_notices = load_notices(for_date=today)
    if d_notices:
        n_parts = []
        for n in d_notices:
            cat = n.get("category","General"); nc = NOTICE_CATS.get(cat, NOTICE_CATS["General"])
            n_parts.append(f'<span style="background:{nc["bg"]};color:{nc["color"]};font-size:.58rem;font-weight:700;text-transform:uppercase;padding:.1rem .4rem;border-radius:10px;">{cat}</span> <strong style="color:#1a2e44;font-size:.65rem;">{n.get("title","")}</strong><span style="color:#4a6a4a;font-size:.62rem;"> \u2014 {n.get("body","")}</span><span style="color:#7a9a7a;font-size:.58rem;"> \u00b7 {n.get("submitted_by","")}</span>')
        st.markdown(f'<div class="dp"><div class="dp-header green">\U0001f4dd Staff Notices</div><div class="dp-body"><div style="font-family:DM Sans,sans-serif;line-height:1.8;">{"<br>".join(n_parts)}</div></div></div>', unsafe_allow_html=True)

    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([2,2,2.5,1.5,2])
    with r1c1:
        _staff_rows   = [r for r in d_data.get("staff_absent",  []) if (r.get("Staff Member") or "").strip()]
        _student_rows = [r for r in d_data.get("student_absent", []) if (r.get("Student") or "").strip()]
        st.markdown(f'<div class="dp"><div class="dp-header green">\U0001f645 Staff Absent</div><div class="dp-body"><table class="dt"><tr><th>Staff</th><th>TRT</th></tr>{tbl_rows(_staff_rows, ["Staff Member","TRT"])}</table></div></div><div style="height:6px;"></div><div class="dp"><div class="dp-header blue">\U0001f392 Student Absent</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>Program</th><th>Reason</th></tr>{tbl_rows(_student_rows, ["Student","Program","Reason"])}</table></div></div>', unsafe_allow_html=True)
    with r1c2:
        st.markdown(f'<div class="dp"><div class="dp-header blue">\U0001f68c Excursions</div><div class="dp-body"><table class="dt"><tr><th>Program</th><th>Staff</th><th>Depart</th><th>Return</th><th>Location</th></tr>{tbl_rows(d_data.get("excursions",[]), ["Program","Staff Member","Time Departing","Time Returning","Location"])}</table></div></div>', unsafe_allow_html=True)
    with r1c3:
        _sched = load_scheduled_meetings(today); _all_mtgs = list(d_data.get("staff_meetings") or []) + _sched
        st.markdown(f'<div class="dp"><div class="dp-header navy">\U0001f91d Staff Meetings</div><div class="dp-body"><table class="dt"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>{tbl_rows(_all_mtgs, ["Type","Staff Member","Location","Time Departing","Time Returning","Student"])}</table></div></div>', unsafe_allow_html=True)
    with r1c4:
        st.markdown(f'<div class="dp"><div class="dp-header brown">\U0001f4e5 Entry Meetings</div><div class="dp-body"><table class="dt"><tr><th>Time</th><th>Program</th><th>Student</th></tr>{tbl_rows(d_data.get("entry_meetings",[]), ["Time","Program","Student"])}</table></div></div>', unsafe_allow_html=True)
    with r1c5:
        kitchen = sr.get("kitchen_duties","") or "\u2014"
        st.markdown(f'<div class="dp"><div class="dp-header amber">\u2b50 Staff Responsibilities</div><div class="dp-body"><div style="margin-bottom:.35rem;"><span class="kitchen-val">\U0001f373 Kitchen: {kitchen}</span></div><div style="margin-bottom:.2rem;"><span class="resp-label">\U0001f4cc PD Focus</span><br><span class="resp-val">{sr.get("meeting_pd_focus","") or "\u2014"}</span></div><div style="margin-bottom:.2rem;"><span class="resp-label">\U0001fa91 Chair</span><br><span class="resp-val">{sr.get("chair","") or "\u2014"}</span></div><div><span class="resp-label">\U0001f4dd Minutes</span><br><span class="resp-val">{sr.get("minutes","") or "\u2014"}</span></div></div></div>', unsafe_allow_html=True)

    _vis_rows = [r for r in d_data.get("visitors_on_site", []) if any(r.get(k,"") for k in ["Visitor Name","Reason","Staff Responsible"])]
    if _vis_rows:
        _vis_html = "".join([f'<tr><td><strong style="color:#1a2e44;">{r.get("Visitor Name","")}</strong></td><td style="font-size:.6rem;">{r.get("Reason","")}</td><td style="font-size:.6rem;">{r.get("Staff Responsible","")}</td><td style="font-size:.6rem;">{r.get("Arriving","")}</td><td style="font-size:.6rem;">{r.get("Departing","")}</td><td style="font-size:.6rem;">{r.get("Location","")}</td></tr>' for r in _vis_rows])
        st.markdown(f'<div class="dp"><div class="dp-header green">\U0001f465 Visitors on Site</div><div class="dp-body"><table class="dt"><tr><th>Visitor</th><th>Reason</th><th>Staff</th><th>Arriving</th><th>Departing</th><th>Location</th></tr>{_vis_html}</table></div></div>', unsafe_allow_html=True)

    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns([2,2,2,1.5,1])
    with r2c1:
        st.markdown(f'<div class="dp"><div class="dp-header blue">\U0001f7e6 JP \u2013 Travel</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>{tbl_rows(d_data.get("travel_jp",[]), ["Student","Arrival Time","Departure Time","Transport"])}</table></div></div>', unsafe_allow_html=True)
    with r2c2:
        st.markdown(f'<div class="dp"><div class="dp-header purple">\U0001f7e3 PY \u2013 Travel</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>{tbl_rows(d_data.get("travel_py",[]), ["Student","Arrival Time","Departure Time","Transport"])}</table></div></div>', unsafe_allow_html=True)
    with r2c3:
        st.markdown(f'<div class="dp"><div class="dp-header slate">\U0001f7eb SY \u2013 Travel</div><div class="dp-body"><table class="dt"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>{tbl_rows(d_data.get("travel_sy",[]), ["Student","Arrival Time","Departure Time","Transport"])}</table></div></div>', unsafe_allow_html=True)
    with r2c4:
        vb = d_data.get("vehicle_bookings",[]); 
        if isinstance(vb, dict): vb = []
        if vb:
            def _dm_vb_time_d(b): return "All day" if b.get("whole_day",True) else f"{b.get('start_time','?')}\u2013{b.get('end_time','?')}"
            vb_html = "".join([f'<tr><td style="font-size:.58rem;color:#5a7a5a;">{"🚐 Van" if b.get("vehicle")=="Van" else "🚙 Kia"}</td><td><span class="vb-tag">{b.get("booker","")}</span></td><td style="font-size:.58rem;color:#6BBF4E;">{_dm_vb_time_d(b)}</td></tr>' for b in vb if b.get("booker","")])
        else:
            vb_html = '<tr><td colspan="3" class="dt-em">No bookings today</td></tr>'
        st.markdown(f'<div class="dp"><div class="dp-header navy">\U0001f697 Vehicles</div><div class="dp-body"><table class="dt"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>{vb_html}</table></div></div>', unsafe_allow_html=True)
    with r2c5:
        nit = d_data.get("nit_booking","") or '<span class="dt-em">None today</span>'
        st.markdown(f'<div class="dp"><div class="dp-header green">\U0001f4cb NIT</div><div class="dp-body"><p style="font-size:.62rem;color:#2d3d2d;margin:0;line-height:1.4;">{nit}</p></div></div>', unsafe_allow_html=True)

    # Travel Changes — highlighted red if anything entered
    tc_today = d_data.get("travel_changes", [])
    tc_filtered = [r for r in tc_today if any(r.get(k,"") for k in ["Student","Change Type","Reason","Time","How Departed"])]
    if tc_filtered:
        tc_rows_html = "".join([
            f'<tr><td><strong style="color:#1a2e44;">{r.get("Student","")}</strong></td>'
            f'<td style="font-size:.6rem;">{r.get("Program","")}</td>'
            f'<td><span class="tc-badge">{r.get("Change Type","")}</span></td>'
            f'<td style="font-size:.6rem;color:#4a2a2a;">{r.get("Reason","")}</td>'
            f'<td style="font-family:DM Mono,monospace;font-size:.6rem;color:#c0392b;font-weight:700;">{r.get("Time","")}</td>'
            f'<td style="font-size:.6rem;">{r.get("How Departed","")}</td></tr>'
            for r in tc_filtered
        ])
        st.markdown(f'<div class="dp" style="border-left:4px solid #c0392b;"><div class="dp-header red">\U0001f504 Travel Plan Changes</div><div class="dp-body"><table class="dt"><tr><th style="color:#e87878;">Student</th><th style="color:#e87878;">Program</th><th style="color:#e87878;">Change</th><th style="color:#e87878;">Reason</th><th style="color:#e87878;">Time</th><th style="color:#e87878;">How Departed</th></tr>{tc_rows_html}</table></div></div>', unsafe_allow_html=True)

    bc_today = load_bulletin_changes(today)
    if bc_today:
        pc_parts = []
        for ch in bc_today:
            reason = ch.get("reason",""); absent = ch.get("staff_absent",""); has_trt = ch.get("has_trt",False); trt_name = ch.get("trt_name",""); staff_rows = ch.get("staff_rows",[])
            color = "#dc2626" if reason == "Staff Absence" else "#0e7490"
            meta = []
            if absent: meta.append(f"Absent: <strong>{absent}</strong>")
            if has_trt: meta.append(f"TRT: {trt_name or 'On site'}")
            tt_html = _timetable_grid_html(staff_rows, PC_TIME_SLOTS_30, dark=True)
            pc_parts.append(f'<div style="margin-bottom:10px;border-left:3px solid {color};padding-left:8px;"><div style="font-size:.6rem;color:#a8c8a8;margin-bottom:3px;font-weight:700;">{reason.upper()}{(" \u00b7 " + " \u00b7 ".join(meta)) if meta else ""}</div>{tt_html or "<span style=\'color:#3a5a3a;font-size:.6rem;\'>No timetable entered</span>"}</div>')
        st.markdown(f'<div class="dp"><div class="dp-header green">\U0001f4ca Program Changes</div><div class="dp-body">{"".join(pc_parts)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="dp"><div class="dp-header green">\U0001f4ca Program Changes</div><div class="dp-body"><span class="dt-em">No program changes today</span></div></div>', unsafe_allow_html=True)

    import streamlit.components.v1 as components
    components.html("""<script>(function(){function u(){var o={timeZone:'Australia/Adelaide',hour:'numeric',minute:'2-digit',hour12:true};var t=new Date().toLocaleTimeString('en-AU',o).toUpperCase();var e=window.parent.document.getElementById('live-clock');if(e)e.textContent=t}u();setInterval(u,1000)})();</script>""", height=0)
    st.markdown(f'<div class="fact-bar"><span class="fact-label">\U0001f4a1 Fun Fact</span><span>{fun or "No fun fact for today"}</span></div>', unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════
# QUICK ADD MODE
# ══════════════════════════════════════════════════════════════
if params.get("quickadd") == "true":
    st.markdown("""<style>[data-testid="stAppViewContainer"]{background:#f0f7eb!important}.main .block-container{padding:2rem 2rem 3rem!important;max-width:620px!important;margin:0 auto!important}[data-testid="stHeader"]{display:none}#MainMenu,footer,.stDeployButton{display:none}</style>""", unsafe_allow_html=True)
    st.markdown("""<div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;padding:1.5rem 2rem;margin-bottom:1.5rem;text-align:center;color:white;"><div style="font-size:2rem;margin-bottom:.3rem;">\U0001f4dd</div><div style="font-size:1.3rem;font-weight:700;margin-bottom:.25rem;">Staff Quick Notice</div><div style="font-size:.85rem;opacity:.85;">Cowandilla Learning Centre \u00b7 Daily Bulletin</div></div>""", unsafe_allow_html=True)
    with st.form("qa_standalone_form", clear_on_submit=True):
        qa_name = st.text_input("Your name *", placeholder="e.g. Sarah")
        qa_cat = st.selectbox("Category *", list(NOTICE_CATS.keys()), format_func=lambda x: f"{NOTICE_CATS[x]['emoji']} {x}")
        qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3")
        qa_body = st.text_area("Details (optional)", height=110)
        qa_date = st.date_input("For which day?", value=date.today())
        if st.form_submit_button("\U0001f4e2 Post Notice to Bulletin", type="primary", use_container_width=True):
            if not qa_name.strip(): st.warning("Please enter your name.")
            elif not qa_title.strip(): st.warning("Please enter a title.")
            else:
                save_notice({"submitted_by": qa_name.strip(), "category": qa_cat, "title": qa_title.strip(), "body": qa_body.strip(), "notice_date": str(qa_date)})
                st.success(f"\u2705 Notice posted for {qa_date.strftime('%-d %B')}!"); st.balloons()
    st.markdown('<div style="text-align:center;"><a href="/" style="font-size:.82rem;color:#4a8f33;font-weight:600;text-decoration:none;">\u2190 Back to full bulletin</a>&nbsp;&nbsp;|&nbsp;&nbsp;<a href="/?display=true" style="font-size:.82rem;color:#4a8f33;font-weight:600;text-decoration:none;">Staff room display \u2192</a></div>', unsafe_allow_html=True)
    st.stop()


# ── TOP NAV ───────────────────────────────────────────────────
edit = st.session_state.edit_mode and st.session_state.authenticated
auth_badge = ('<span class="nav-badge edit">\u270f\ufe0f Edit Mode</span>' if edit else '<span class="nav-badge">\u2705 Staff</span>') if st.session_state.authenticated else ''
st.markdown(f'<div class="top-nav"><div class="top-nav-left"><div class="top-nav-logo">CLC</div><div><div class="top-nav-title">Daily Bulletin</div><div class="top-nav-sub">Cowandilla Learning Centre</div></div></div><div class="top-nav-right">{auth_badge}</div></div>', unsafe_allow_html=True)

current_date = st.session_state.selected_date
bulletin_data = load_bulletin(current_date)

page_tab, quickadd_tab, archive_tab, login_tab = st.tabs(["\U0001f4cb Bulletin", "\U0001f4dd Quick Add", "\U0001f5c2\ufe0f Archive", "\U0001f510 Staff"])

with page_tab:
    if st.query_params.get("from_display") == "true" and not st.session_state.authenticated:
        st.markdown("""<div style="background:#1a2e44;border-left:4px solid #6BBF4E;padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:1rem;"><span style="color:white;font-size:.85rem;">\U0001f510 Enter your staff password to edit today's bulletin, then save to return to the display screen.</span></div>""", unsafe_allow_html=True)
        pw_col, btn_col, back_col = st.columns([2,1,1])
        with pw_col:
            quick_pw = st.text_input("Staff Password", type="password", key="quick_pw", label_visibility="collapsed", placeholder="Enter staff password...")
        with btn_col:
            if st.button("\U0001f513 Login", type="primary", use_container_width=True):
                if quick_pw == ADMIN_PASSWORD: st.session_state.authenticated = True; st.session_state.edit_mode = True; st.rerun()
                else: st.error("Incorrect password")
        with back_col:
            st.markdown('<a href="/?display=true" style="display:block;text-align:center;background:#eef1f4;color:#1a2e44;font-weight:600;font-size:.85rem;padding:.5rem;border-radius:8px;text-decoration:none;">\u21a9\ufe0f Back to Display</a>', unsafe_allow_html=True)
        st.markdown("---")

    week = week_dates(current_date)
    import html as _html, re as _re
    fact = bulletin_data.get("fun_fact","")
    fact_clean = _html.escape(_re.sub(r'<[^>]+>', '', fact)).strip()
    fun_fact_html = (f'<div style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.2);border-radius:12px;padding:.65rem 1rem;max-width:480px;"><div style="font-size:.65rem;color:rgba(255,255,255,0.6);letter-spacing:.1em;text-transform:uppercase;margin-bottom:.2rem;">\U0001f4a1 Fun Fact</div><div style="font-size:.85rem;color:white;font-weight:500;line-height:1.4;">{fact_clean}</div></div>') if fact_clean else ""
    st.markdown(f"""<div class="bulletin-hero"><div class="bulletin-hero-inner"><div><div class="bulletin-date-label">{term_label(current_date)}</div><div class="bulletin-date-main">{current_date.strftime("%A %-d %B")}</div><div class="bulletin-date-sub">{current_date.strftime("%Y")}</div></div>{fun_fact_html}</div></div>""", unsafe_allow_html=True)

    st.markdown('<div style="background:white;border-bottom:2px solid #e8f0e3;padding:.4rem 1rem 0;">', unsafe_allow_html=True)
    nav_l, nav_m, nav_r = st.columns([1,4,1])
    with nav_l:
        if st.button("\u2190 Prev Week", key="prev_week", use_container_width=True): st.session_state.selected_date = week[0] - timedelta(days=7); st.rerun()
    with nav_m:
        wls = f"Week of {week[0].strftime('%-d %b')} \u2013 {week[-1].strftime('%-d %b %Y')}"
        if date.today() in week: wls += " \u00b7 This Week"
        st.markdown(f'<div style="text-align:center;padding:.45rem 0;font-size:.78rem;font-weight:600;color:{"#4a8f33" if date.today() in week else "#5a6e5a"};">{wls}</div>', unsafe_allow_html=True)
    with nav_r:
        if st.button("Next Week \u2192", key="next_week", use_container_width=True): st.session_state.selected_date = week[0] + timedelta(days=7); st.rerun()
    day_cols = st.columns(5)
    for i, d in enumerate(week):
        with day_cols[i]:
            lbl = d.strftime("%a %-d %b") + (" \u25c9" if d == date.today() else "")
            if st.button(lbl, key=f"day_{d}", use_container_width=True, type="primary" if d==current_date else "secondary"): st.session_state.selected_date = d; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="background:#f8fdf6;border:1.5px solid #d8ead2;border-radius:10px;padding:.6rem 1rem;margin:.75rem 0;">', unsafe_allow_html=True)
    jump_col1, jump_col2, jump_col3 = st.columns([1,2,1])
    with jump_col1: st.markdown('<div style="font-size:.8rem;font-weight:600;color:#4a8f33;padding-top:.5rem;">\U0001f4c5 Jump to Date:</div>', unsafe_allow_html=True)
    with jump_col2: jump_date = st.date_input("Select date", value=current_date, key="jump_date_picker", label_visibility="collapsed")
    with jump_col3:
        if st.button("\u2192 Go", key="jump_to_date", use_container_width=True, type="primary"): st.session_state.selected_date = jump_date; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    ctrl_cols = st.columns([1,1,1,3,1])
    if st.session_state.authenticated:
        with ctrl_cols[0]:
            if st.button("\u270f\ufe0f Edit" if not edit else "\U0001f441\ufe0f View", type="primary" if not edit else "secondary", use_container_width=True): st.session_state.edit_mode = not st.session_state.edit_mode; st.rerun()
        with ctrl_cols[1]:
            if edit and st.button("\U0001f4be Save", type="primary", use_container_width=True): st.session_state["_pending_save"] = True
        with ctrl_cols[2]:
            if st.button("\U0001f6aa Logout", type="secondary", use_container_width=True): st.session_state.authenticated = False; st.session_state.edit_mode = False; st.rerun()
    else:
        with ctrl_cols[0]:
            if st.button("\U0001f510 Staff Login", type="secondary", use_container_width=True): st.session_state.show_inline_login = not st.session_state.get("show_inline_login", False); st.rerun()
    with ctrl_cols[4]:
        st.markdown('<a href="/?display=true" target="_blank" style="display:block;text-align:center;background:#1a2e44;color:white;font-weight:600;font-size:.8rem;padding:.45rem .75rem;border-radius:8px;text-decoration:none;white-space:nowrap;">\U0001f4fa Staff Room</a>', unsafe_allow_html=True)

    if not st.session_state.authenticated and st.session_state.get("show_inline_login", False):
        with st.container():
            st.markdown('<div style="background:#f0f7eb;border:1.5px solid #6BBF4E;border-radius:10px;padding:1rem 1.25rem;margin:.5rem 0 .75rem;">', unsafe_allow_html=True)
            lc1, lc2, lc3 = st.columns([3,1,1])
            with lc1: quick_pw = st.text_input("Staff password", type="password", key="inline_pw", label_visibility="collapsed", placeholder="Enter staff password\u2026")
            with lc2:
                if st.button("\U0001f513 Login", type="primary", use_container_width=True, key="inline_login_btn"):
                    if quick_pw == ADMIN_PASSWORD: st.session_state.authenticated = True; st.session_state.edit_mode = True; st.session_state.show_inline_login = False; st.rerun()
                    else: st.error("Incorrect password")
            with lc3:
                if st.button("Cancel", type="secondary", use_container_width=True, key="inline_cancel"): st.session_state.show_inline_login = False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="content-area">', unsafe_allow_html=True)

    _admin_notices = load_notices(for_date=current_date)
    if _admin_notices or edit:
        st.markdown('<div class="section-card"><div class="section-card-header green"><h3>\U0001f4dd Staff Notices</h3></div><div class="section-card-body">', unsafe_allow_html=True)
        if _admin_notices:
            for _n in _admin_notices:
                _cat = _n.get("category","General"); _nc = NOTICE_CATS.get(_cat, NOTICE_CATS["General"]); _nid = _n.get("id","")
                _nc1, _nc2 = st.columns([9,1])
                with _nc1:
                    st.markdown(f'<div style="background:white;border-radius:10px;border-left:4px solid {_nc["color"]};padding:.75rem 1rem;margin-bottom:.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);"><div style="margin-bottom:.2rem;"><span style="background:{_nc["bg"]};color:{_nc["color"]};font-size:.65rem;font-weight:700;text-transform:uppercase;padding:.15rem .5rem;border-radius:20px;">{_nc["emoji"]} {_cat}</span><span style="font-size:.7rem;color:#9ab09a;margin-left:.5rem;">from {_n.get("submitted_by","")}</span></div><div style="font-size:.9rem;font-weight:700;color:#1a2e44;margin:.3rem 0 .2rem;">{_n.get("title","")}</div><div style="font-size:.82rem;color:#3a4a3a;line-height:1.5;">{_n.get("body","")}</div></div>', unsafe_allow_html=True)
                with _nc2:
                    if edit:
                        st.write("")
                        if st.button("\U0001f5d1\ufe0f", key=f"top_del_n_{_nid}", help="Delete notice"): delete_notice(_nid); st.rerun()
        else:
            st.markdown('<div style="text-align:center;padding:1rem;color:#9ab09a;font-size:.85rem;">No notices today \u2014 staff can add via the \U0001f4dd Quick Add tab</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    s1, s2, s3, s4 = st.tabs(["\U0001f465 Staff & Meetings","\U0001f68c Travel & Vehicles","\U0001f4cc Responsibilities & NIT","\U0001f4ca Program Changes"])

    with s1:
        import pandas as pd
        if edit:
            auto_fact = daily_fun_fact(current_date); current_fact = (bulletin_data.get("fun_fact") or "").strip()
            fc1, fc2 = st.columns([5,1])
            with fc1: new_fact = st.text_input("\U0001f4a1 Fun Fact of the Day", value=current_fact if current_fact else auto_fact)
            with fc2:
                st.markdown("<div style='padding-top:1.85rem;'>", unsafe_allow_html=True)
                if st.button("\U0001f3b2 New", key="new_fact", use_container_width=True): bulletin_data["fun_fact"] = auto_fact; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            bulletin_data["fun_fact"] = new_fact

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>\U0001f645 Staff Absent</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                sa_df = pd.DataFrame(bulletin_data["staff_absent"])
                sa_edited = st.data_editor(sa_df, key="sa_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["staff_absent"] = sa_edited.to_dict("records")
            else:
                _s_rows = [r for r in bulletin_data["staff_absent"] if (r.get("Staff Member") or "").strip()]
                if _s_rows: st.markdown('<table class="data-table"><tr><th>Staff Member</th><th>TRT</th></tr>'+"".join([f"<tr><td><strong>{r.get('Staff Member','')}</strong></td><td>{r.get('TRT','')}</td></tr>" for r in _s_rows])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\u2705</div>No staff absent today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header blue"><h3>\U0001f392 Student Absent</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                st_df = pd.DataFrame(bulletin_data["student_absent"])
                st_edited = st.data_editor(st_df, key="st_editor", hide_index=True, use_container_width=True, num_rows="dynamic")
                bulletin_data["student_absent"] = st_edited.to_dict("records")
            else:
                _st_rows = [r for r in bulletin_data["student_absent"] if (r.get("Student") or "").strip()]
                if _st_rows: st.markdown('<table class="data-table"><tr><th>Student</th><th>Program</th><th>Reason</th></tr>'+"".join([f"<tr><td><strong>{r.get('Student','')}</strong></td><td>{r.get('Program','')}</td><td>{r.get('Reason','')}</td></tr>" for r in _st_rows])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\u2705</div>No students absent today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header blue"><h3>\U0001f68c Excursions</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["excursions"]); edited = st.data_editor(df, key="ex_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["excursions"] = edited.to_dict("records")
            else:
                rows = bulletin_data["excursions"]; has_data = any(any(v for v in r.values()) for r in rows)
                if has_data: st.markdown('<table class="data-table"><tr><th>Program</th><th>Staff</th><th>Departing</th><th>Returning</th><th>Location</th></tr>'+"".join([f"<tr><td>{r.get('Program','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Location','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\U0001f5fa\ufe0f</div>No excursions today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header brown"><h3>\U0001f4e5 Entry Meetings \u2013 Annette</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["entry_meetings"]); edited = st.data_editor(df, key="em_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["entry_meetings"] = edited.to_dict("records")
            else:
                rows = bulletin_data["entry_meetings"]; has_data = any(any(v for v in r.values()) for r in rows)
                if has_data: st.markdown('<table class="data-table"><tr><th>Time</th><th>Program</th><th>Student</th></tr>'+"".join([f"<tr><td>{r.get('Time','')}</td><td>{r.get('Program','')}</td><td>{r.get('Student','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4ed</div>No entry meetings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

        with col_right:
            st.markdown('<div class="section-card"><div class="section-card-header navy"><h3>\U0001f91d Staff Meetings</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["staff_meetings"]); edited = st.data_editor(df, key="sm_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["staff_meetings"] = edited.to_dict("records")
            else:
                all_mtgs = list(bulletin_data["staff_meetings"] or []) + load_scheduled_meetings(current_date); has_data = any(any(v for v in r.values()) for r in all_mtgs)
                if has_data: st.markdown('<table class="data-table"><tr><th>Type</th><th>Staff</th><th>Location</th><th>Depart</th><th>Return</th><th>Student</th></tr>'+"".join([f"<tr><td>{r.get('Type','')}</td><td>{r.get('Staff Member','')}</td><td>{r.get('Location','')}</td><td>{r.get('Time Departing','')}</td><td>{r.get('Time Returning','')}</td><td>{r.get('Student','')}</td></tr>" for r in all_mtgs if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4c5</div>No staff meetings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header slate"><h3>\U0001f4ac Additional Staff Messages</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                df = pd.DataFrame(bulletin_data["additional_messages"]); edited = st.data_editor(df, key="msg_editor", hide_index=True, use_container_width=True, num_rows="dynamic"); bulletin_data["additional_messages"] = edited.to_dict("records")
            else:
                rows = bulletin_data["additional_messages"]; has_data = any(any(v for v in r.values()) for r in rows)
                if has_data: st.markdown('<table class="data-table"><tr><th>Staff</th><th>Details</th></tr>'+"".join([f"<tr><td><strong>{r.get('Staff Name','')}</strong></td><td>{r.get('Details','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4ad</div>No additional messages</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>\U0001f465 Visitors on Site</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                vis_df = pd.DataFrame(bulletin_data.get("visitors_on_site", []))
                vis_edited = st.data_editor(vis_df, key="vis_editor", hide_index=True, use_container_width=True, num_rows="dynamic",
                    column_config={"Reason": st.column_config.SelectboxColumn("Reason", options=VISITOR_REASON_OPTIONS, required=False)})
                bulletin_data["visitors_on_site"] = vis_edited.to_dict("records")
            else:
                vis_rows = bulletin_data.get("visitors_on_site", []); has_vis = any(any(v for v in r.values()) for r in vis_rows)
                if has_vis: st.markdown('<table class="data-table"><tr><th>Visitor</th><th>Reason</th><th>Staff Responsible</th><th>Arriving</th><th>Departing</th><th>Location</th></tr>'+"".join([f"<tr><td><strong>{r.get('Visitor Name','')}</strong></td><td>{r.get('Reason','')}</td><td>{r.get('Staff Responsible','')}</td><td>{r.get('Arriving','')}</td><td>{r.get('Departing','')}</td><td>{r.get('Location','')}</td></tr>" for r in vis_rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                else: st.markdown('<div class="empty-state"><div class="icon">\U0001f6b6</div>No visitors today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

    with s2:
        import pandas as pd
        st.markdown('<div style="font-size:.8rem;font-weight:600;color:#4a6640;margin-bottom:.5rem;">\U0001f4c5 Planned Travel \u2014 expected arrivals &amp; departures</div>', unsafe_allow_html=True)
        jp_col, py_col, sy_col = st.columns(3)

        def render_travel_card(col, key, label, color):
            with col:
                st.markdown(f'<div class="section-card"><div class="section-card-header" style="background:{color};"><h3>{label}</h3></div><div class="section-card-body">', unsafe_allow_html=True)
                rows = bulletin_data[key]
                if edit:
                    df = pd.DataFrame(rows)
                    edited = st.data_editor(df, key=f"{key}_editor", hide_index=True, use_container_width=True, num_rows="dynamic",
                        column_config={"Transport": st.column_config.SelectboxColumn("Transport", options=TRANSPORT_OPTIONS, required=False)})
                    bulletin_data[key] = edited.to_dict("records")
                else:
                    has_data = any(any(v for v in r.values()) for r in rows)
                    if has_data:
                        st.markdown('<table class="data-table"><tr><th>Student</th><th>Arrives</th><th>Departs</th><th>Transport</th></tr>'+"".join([f"<tr><td>{r.get('Student','')}</td><td>{r.get('Arrival Time','')}</td><td>{r.get('Departure Time','')}</td><td>{r.get('Transport','')}</td></tr>" for r in rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
                    else: st.markdown('<div class="empty-state"><div class="icon">\U0001f690</div>No travel today</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)

        render_travel_card(jp_col, "travel_jp", "\U0001f7e6 Junior Primary \u2013 Travel", "#4a7fb5")
        render_travel_card(py_col, "travel_py", "\U0001f7e3 Primary Years \u2013 Travel", "#7a5bb5")
        render_travel_card(sy_col, "travel_sy", "\U0001f7eb Senior Years \u2013 Travel", "#8c6a4f")

        st.markdown('<div style="font-size:.8rem;font-weight:600;color:#c0392b;margin:.75rem 0 .5rem;">\U0001f504 Travel Plan Changes \u2014 update if a student\u2019s plan changes during the day</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-card"><div class="section-card-header red"><h3>\U0001f504 Travel Plan Changes</h3></div><div class="section-card-body">', unsafe_allow_html=True)
        tc_rows = bulletin_data.get("travel_changes", [])
        if edit:
            tc_df = pd.DataFrame(tc_rows)
            tc_edited = st.data_editor(tc_df, key="tc_editor", hide_index=True, use_container_width=True, num_rows="dynamic",
                column_config={
                    "Program": st.column_config.SelectboxColumn("Program", options=["JP","PY","SY"], required=False),
                    "Change Type": st.column_config.SelectboxColumn("Change Type", options=CHANGE_TYPE_OPTIONS, required=False),
                    "How Departed": st.column_config.SelectboxColumn("How Departed", options=TRANSPORT_OPTIONS, required=False),
                })
            bulletin_data["travel_changes"] = tc_edited.to_dict("records")
            st.markdown('<div style="background:#fff8f7;border:1px solid #f5c6c0;border-radius:8px;padding:.5rem .75rem;margin-top:.5rem;font-size:.75rem;color:#7a2a2a;">\U0001f4a1 <strong>Tip:</strong> Fill in whenever a student\u2019s travel plan changes \u2014 e.g. early departure, parent collecting instead of taxi. Appears highlighted on the staff room display so staff notice it immediately.</div>', unsafe_allow_html=True)
        else:
            has_tc = any(any(v for v in r.values()) for r in tc_rows)
            if has_tc:
                st.markdown('<table class="data-table"><tr><th>Student</th><th>Program</th><th>Change</th><th>Reason</th><th>Time</th><th>How Departed</th></tr>'+"".join([f"<tr><td><strong>{r.get('Student','')}</strong></td><td>{r.get('Program','')}</td><td><span class='change-badge'>{r.get('Change Type','')}</span></td><td>{r.get('Reason','')}</td><td><strong style='color:#c0392b;'>{r.get('Time','')}</strong></td><td>{r.get('How Departed','')}</td></tr>" for r in tc_rows if any(v for v in r.values())])+"</table>", unsafe_allow_html=True)
            else: st.markdown('<div class="empty-state"><div class="icon">\u2705</div>No travel changes today</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card"><div class="section-card-header navy"><h3>\U0001f697 Vehicle Bookings \u2014 Van &amp; Kia</h3></div><div class="section-card-body">', unsafe_allow_html=True)
        vb_list = bulletin_data.get("vehicle_bookings",[])
        if isinstance(vb_list, dict): vb_list = []
        if edit:
            if vb_list:
                st.markdown("**Current bookings:**")
                for _bi, _bk in enumerate(vb_list):
                    _bc1, _bc2, _bc3, _bc4 = st.columns([1,2,2,1])
                    with _bc1: st.markdown(f"**{'\U0001f690 Van' if _bk.get('vehicle','')=='Van' else '\U0001f699 Kia'}**")
                    with _bc2: st.markdown(f"**{_bk.get('booker','\u2014')}**")
                    with _bc3: st.markdown("\U0001f550 Whole day" if _bk.get("whole_day",True) else f"\U0001f550 {_bk.get('start_time','?')} \u2013 {_bk.get('end_time','?')}")
                    with _bc4:
                        if st.button("\U0001f5d1\ufe0f", key=f"vb_del_{_bi}"): vb_list.pop(_bi); bulletin_data["vehicle_bookings"] = vb_list; st.rerun()
                st.markdown("---")
            st.markdown("**Add a booking:**")
            _av1, _av2, _av3 = st.columns([1,2,2])
            with _av1: _new_vehicle = st.selectbox("Vehicle", ["Van","Kia"], key="vb_new_vehicle")
            with _av2: _new_booker = st.text_input("Booked by", key="vb_new_booker", placeholder="e.g. Sarah")
            with _av3: _new_whole = st.checkbox("Whole day", value=True, key="vb_new_whole")
            if not _new_whole:
                _at1, _at2 = st.columns(2)
                with _at1: _new_start = st.text_input("Start time", key="vb_new_start", placeholder="e.g. 9:30")
                with _at2: _new_end = st.text_input("End time", key="vb_new_end", placeholder="e.g. 12:00")
            else: _new_start = _new_end = ""
            if st.button("\u2795 Add Booking", type="primary", key="vb_add_btn"):
                if _new_booker.strip(): vb_list.append({"vehicle":_new_vehicle,"booker":_new_booker.strip(),"whole_day":_new_whole,"start_time":_new_start.strip(),"end_time":_new_end.strip()}); bulletin_data["vehicle_bookings"] = vb_list; st.rerun()
                else: st.warning("Please enter a name.")
        else:
            if vb_list and any(b.get("booker","") for b in vb_list):
                def _vbt(b): return "Whole day" if b.get("whole_day",True) else f"{b.get('start_time','?')} \u2013 {b.get('end_time','?')}"
                st.markdown('<table class="data-table"><tr><th>Vehicle</th><th>Booked By</th><th>Time</th></tr>'+"".join([f'<tr><td>{"🚐 Van" if b.get("vehicle","")=="Van" else "🚙 Kia"}</td><td><span class="vehicle-booking">{b.get("booker","")}</span></td><td class="vehicle-time">{_vbt(b)}</td></tr>' for b in vb_list if b.get("booker","")])+"</table>", unsafe_allow_html=True)
            else: st.markdown('<div class="empty-state"><div class="icon">\U0001f697</div>No vehicle bookings today</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    with s3:
        resp_col, nit_col = st.columns(2)
        with resp_col:
            st.markdown('<div class="section-card"><div class="section-card-header amber"><h3>\u2b50 Staff Responsibilities</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            sr = bulletin_data["staff_responsibilities"]
            if edit:
                bulletin_data["staff_responsibilities"] = {"kitchen_duties": st.text_input("\U0001f373 Kitchen Duties", sr.get("kitchen_duties",""), key="sr_k"),"meeting_pd_focus": st.text_input("\U0001f4cc Staff Meeting PD Focus", sr.get("meeting_pd_focus",""), key="sr_pd"),"chair": st.text_input("\U0001fa91 Meeting Chair", sr.get("chair",""), key="sr_c"),"minutes": st.text_input("\U0001f4dd Meeting Minutes", sr.get("minutes",""), key="sr_m"),}
            else:
                kitchen = sr.get("kitchen_duties","")
                st.markdown(f'<table class="data-table"><tr class="kitchen-row"><td><span class="kitchen-badge">\U0001f373 Kitchen</span></td><td><strong>{kitchen or "\u2014"}</strong></td></tr><tr><td>\U0001f4cc PD Focus</td><td>{sr.get("meeting_pd_focus","") or "\u2014"}</td></tr><tr><td>\U0001fa91 Chair</td><td>{sr.get("chair","") or "\u2014"}</td></tr><tr><td>\U0001f4dd Minutes</td><td>{sr.get("minutes","") or "\u2014"}</td></tr></table>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
        with nit_col:
            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>\U0001f4cb Additional NIT Booking</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            if edit:
                bulletin_data["nit_booking"] = st.text_area("NIT Booking Details", value=bulletin_data.get("nit_booking",""), height=120, label_visibility="collapsed")
            else:
                nit = bulletin_data.get("nit_booking","")
                st.markdown(f'<p style="font-size:.85rem;color:#2a3a2a;line-height:1.6;">{nit}</p>' if nit else '<div class="empty-state"><div class="icon">\U0001f4cb</div>No NIT bookings today</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

    with s4:
        _changes = load_bulletin_changes(current_date)

        def _render_change_view(ch, ci, total):
            reason = ch.get("reason",""); absent = ch.get("staff_absent",""); has_trt = ch.get("has_trt",False); trt_name = ch.get("trt_name",""); staff_rows = ch.get("staff_rows",[])
            color = "#dc2626" if reason == "Staff Absence" else "#0e7490"; bg_tint = "#fff5f5" if reason == "Staff Absence" else "#f0f9ff"; icon = "\U0001f645" if reason == "Staff Absence" else "\U0001f4cc"
            st.markdown(f'<div style="display:flex;align-items:center;gap:.75rem;margin:1rem 0 .4rem;"><div style="background:{color};color:white;font-weight:800;font-size:.75rem;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{ci+1}</div><div style="font-size:.9rem;font-weight:700;color:{color};">{icon} {reason}' + (f' \u2014 <span style="color:#1a2e44;">{absent}</span>' if absent else "") + (f' &nbsp;<span style="background:{color}22;color:{color};font-size:.72rem;font-weight:600;padding:.1rem .5rem;border-radius:10px;">TRT: {trt_name or "on site"}</span>' if has_trt else "") + f'</div>' + (f'<div style="flex:1;height:1px;background:{color}33;"></div>' if ci < total - 1 else "") + f'</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown(f'<div style="background:{bg_tint};border:1.5px solid {color}44;border-left:5px solid {color};border-radius:10px;padding:.85rem 1rem;margin-bottom:.5rem;">', unsafe_allow_html=True)
                tt_html = _timetable_grid_html(staff_rows, PC_TIME_SLOTS)
                if tt_html: st.markdown(tt_html, unsafe_allow_html=True)
                else:
                    for row in staff_rows:
                        name = row.get("name",""); blocks = row.get("blocks",[])
                        if blocks:
                            badges = " ".join([f'<span style="background:{_slot_color_bg(b.get("role",""))};color:{_slot_color_fg(b.get("role",""))};padding:1px 7px;border-radius:8px;font-size:.72rem;font-weight:600;">{b.get("start","")}&ndash;{b.get("end","")} {b.get("role","")}{(" \u2192 "+b["person"]) if b.get("person") and b.get("role")=="Lunch Cover" else ""}{(" \u21a9 "+b["person"]) if b.get("person") and b.get("role")=="Lunch Break" else ""}</span>' for b in blocks if b.get("role") or b.get("start")])
                            if badges: st.markdown(f'<div style="margin:3px 0;font-size:.82rem;"><b>{name}:</b> {badges}</div>', unsafe_allow_html=True)
                    if not any(row.get("blocks") for row in staff_rows): st.markdown('<div style="color:#9ab09a;font-size:.82rem;font-style:italic;">No timetable blocks recorded.</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                if edit:
                    dc1, dc2, dc3 = st.columns([2, 2, 6])
                    with dc1:
                        if st.button("\u270f\ufe0f Edit this change", key=f"ch_edit_{ch.get('id',ci)}_{ci}", use_container_width=True):
                            st.session_state["_pc_form_id"] = int(_time.time() * 1000); st.session_state["_pc_editing"] = dict(ch); st.session_state["_pc_adding"] = False; st.rerun()
                    with dc2:
                        if st.button("\U0001f5d1\ufe0f Delete", key=f"ch_del_{ch.get('id',ci)}_{ci}", use_container_width=True): delete_bulletin_change(ch["id"]); st.rerun()
                    with dc3: st.markdown(f'<div style="padding-top:.45rem;font-size:.72rem;color:#9ab09a;">Saved to database \u00b7 click \u270f\ufe0f to reopen and modify timetable</div>', unsafe_allow_html=True)
            if ci < total - 1: st.markdown('<div style="border-top:2px dashed #e0e8dc;margin:1rem 0;"></div>', unsafe_allow_html=True)

        if not _changes:
            st.markdown('<div style="text-align:center;padding:1.5rem;color:#9ab09a;font-size:.85rem;background:#f8fdf6;border-radius:10px;">\U0001f4ed No program changes recorded for this day.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:.82rem;font-weight:600;color:#4a8f33;margin-bottom:.25rem;">\U0001f4ca {len(_changes)} change{"s" if len(_changes)!=1 else ""} recorded for {current_date.strftime("%-d %B")}:</div>', unsafe_allow_html=True)
            for _ci, _ch in enumerate(_changes): _render_change_view(_ch, _ci, len(_changes))

        if edit:
            st.markdown("---")

            def _render_change_form(d, existing=None):
                is_edit = existing is not None; form_id = st.session_state.get("_pc_form_id", 0); pfx = f"_pcf_{form_id}"; rows_key = f"{pfx}_rows"
                existing_rows = []
                if existing:
                    rr = existing.get("staff_rows",[]); existing_rows = json.loads(rr) if isinstance(rr,str) else (rr or [])
                if rows_key not in st.session_state:
                    st.session_state[rows_key] = existing_rows if existing_rows else [{"name":"","normal_prog":"","blocks":[]}]
                st.markdown(f'<div style="background:#f8fdf6;border:2px solid {"#c97b1a" if is_edit else "#6BBF4E"};border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;">', unsafe_allow_html=True)
                st.markdown(f"#### {'✏️ Editing' if is_edit else '➕ New'} Program Change")
                reason_opts = ["Staff Absence","Site Need / Other"]; r_idx = 1 if (existing or {}).get("reason","") == "Site Need / Other" else 0
                reason = st.radio("Reason for change", reason_opts, index=r_idx, key=f"{pfx}_reason", horizontal=True)
                staff_absent = ""; has_trt = False; trt_name = ""
                if reason == "Staff Absence":
                    c1, c2 = st.columns(2)
                    with c1: staff_absent = st.text_input("Absent staff member *", value=(existing or {}).get("staff_absent",""), key=f"{pfx}_absent", placeholder="e.g. Sarah Jones")
                    with c2: has_trt = st.checkbox("TRT coming in today?", value=bool((existing or {}).get("has_trt",False)), key=f"{pfx}_trt")
                    if has_trt: trt_name = st.text_input("TRT name", value=(existing or {}).get("trt_name",""), key=f"{pfx}_trt_name", placeholder="e.g. Michael Brown")
                else:
                    c1, c2 = st.columns(2)
                    with c1: staff_absent = st.text_input("Who / what is the change for?", value=(existing or {}).get("staff_absent",""), key=f"{pfx}_absent2", placeholder="e.g. PY program, Caitie")
                    with c2: has_trt = st.checkbox("TRT / relief staff involved?", value=bool((existing or {}).get("has_trt",False)), key=f"{pfx}_trt2")
                    if has_trt: trt_name = st.text_input("Relief staff name", value=(existing or {}).get("trt_name",""), key=f"{pfx}_trt_name2")
                st.markdown("---")
                st.markdown('<div style="background:#e8f5e1;border-radius:8px;padding:.6rem .9rem;margin-bottom:.75rem;font-size:.82rem;color:#1a2e44;"><strong>\U0001f4cb Timetable rows</strong> \u2014 add one row per staff member whose day is affected. Fill in time blocks for the changed part of their day. Click <strong>\U0001f4be Save Program Change</strong> when done.</div>', unsafe_allow_html=True)
                rows = st.session_state[rows_key]
                for ri, row in enumerate(rows):
                    st.markdown(f'<div style="background:white;border:1.5px solid #d8ead2;border-radius:10px;padding:.85rem;margin-bottom:.6rem;">', unsafe_allow_html=True)
                    rc1, rc2, rc3 = st.columns([3,2,1])
                    with rc1: row["name"] = st.text_input("Staff / SSO name *", value=row.get("name",""), placeholder="e.g. Sarah Jones", key=f"{pfx}_r{ri}_name")
                    with rc2: row["normal_prog"] = st.text_input("Normal program/role (optional)", value=row.get("normal_prog",""), placeholder="e.g. JP teacher", key=f"{pfx}_r{ri}_norm")
                    with rc3:
                        st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                        if ri > 0 and st.button("\U0001f5d1 Row", key=f"{pfx}_r{ri}_dr"): rows.pop(ri); st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    blocks = row.setdefault("blocks",[])
                    qp_cols = st.columns([3,1])
                    with qp_cols[0]: preset = st.selectbox("\u26a1 Quick fill \u2014 cover the whole day as:", ["--- or enter blocks below ---","JP Cover (full day)","PY Cover (full day)","SY Cover (full day)","NIT (full day)"], key=f"{pfx}_r{ri}_preset")
                    with qp_cols[1]:
                        st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                        if st.button("\u25b6 Apply", key=f"{pfx}_r{ri}_apply_preset"):
                            role_map = {"JP Cover (full day)":"JP","PY Cover (full day)":"PY","SY Cover (full day)":"SY","NIT (full day)":"NIT"}
                            if preset in role_map:
                                row["blocks"] = [{"start":"9:00","end":"2:45","role":role_map[preset],"person":""}]
                                for k,v in [("s","9:00"),("e","2:45"),("r",role_map[preset]),("p","")]: st.session_state[f"{pfx}_r{ri}_b0_{k}"] = v
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    if blocks: st.markdown("**Time blocks:**")
                    for bi, block in enumerate(blocks):
                        s_key = f"{pfx}_r{ri}_b{bi}_s"; e_key = f"{pfx}_r{ri}_b{bi}_e"; r_key = f"{pfx}_r{ri}_b{bi}_r"; p_key = f"{pfx}_r{ri}_b{bi}_p"
                        for key2, val2 in [(s_key, block.get("start","")), (e_key, block.get("end","")), (r_key, block.get("role","")), (p_key, block.get("person",""))]:
                            if key2 not in st.session_state: st.session_state[key2] = val2
                        bc1, bc2, bc3, bc4, bc5, bc6 = st.columns([1.5,1.5,2,2,0.5,0.5])
                        with bc1: block["start"] = st.selectbox("Start", [""] + PC_TIME_SLOTS, key=s_key)
                        with bc2: block["end"] = st.selectbox("End", [""] + PC_TIME_SLOTS, key=e_key)
                        with bc3: block["role"] = st.selectbox("Role", ROLE_OPTIONS, key=r_key)
                        with bc4:
                            live_role = st.session_state.get(r_key, "")
                            if live_role == "Lunch Cover": block["person"] = st.text_input("Releasing (who)", key=p_key, placeholder="Staff member getting lunch break")
                            elif live_role == "Lunch Break": block["person"] = st.text_input("Covered by (who)", key=p_key, placeholder="Staff member providing cover")
                            else: block["person"] = st.text_input("Detail (optional)", key=p_key, placeholder="e.g. covering Annette")
                        with bc5:
                            st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                            if st.button("\u2715", key=f"{pfx}_r{ri}_b{bi}_del"):
                                blocks.pop(bi)
                                for old_bi in range(bi, len(blocks)+1):
                                    for sfx in ("_s","_e","_r","_p"): st.session_state.pop(f"{pfx}_r{ri}_b{old_bi}{sfx}", None)
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                        with bc6:
                            if bi < len(blocks)-1:
                                st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                                if st.button("\u2193", key=f"{pfx}_r{ri}_b{bi}_dn"):
                                    blocks[bi], blocks[bi+1] = blocks[bi+1], blocks[bi]
                                    for sfx in ("_s","_e","_r","_p"):
                                        ka = f"{pfx}_r{ri}_b{bi}{sfx}"; kb = f"{pfx}_r{ri}_b{bi+1}{sfx}"
                                        va = st.session_state.get(ka); vb_val = st.session_state.get(kb)
                                        if va is not None: st.session_state[kb] = va
                                        if vb_val is not None: st.session_state[ka] = vb_val
                                    st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
                        live_s = st.session_state.get(s_key, ""); live_e = st.session_state.get(e_key, ""); live_r = st.session_state.get(r_key, "")
                        if live_s and live_e and live_r and _t2m(live_s) >= _t2m(live_e):
                            st.markdown(f'<div style="background:#fee2e2;border:1.5px solid #fca5a5;border-radius:6px;padding:.35rem .75rem;margin:.2rem 0 .4rem;font-size:.75rem;color:#991b1b;">\u26d4 Block {bi+1}: <strong>Start ({live_s}) is the same as or after End ({live_e})</strong> \u2014 this block will be skipped. Swap the times or delete this block.</div>', unsafe_allow_html=True)
                    if blocks:
                        broken = [bi2+1 for bi2, block2 in enumerate(blocks) if _t2m(st.session_state.get(f"{pfx}_r{ri}_b{bi2}_s", block2.get("start",""))) >= _t2m(st.session_state.get(f"{pfx}_r{ri}_b{bi2}_e", block2.get("end",""))) and st.session_state.get(f"{pfx}_r{ri}_b{bi2}_s") and st.session_state.get(f"{pfx}_r{ri}_b{bi2}_e") and st.session_state.get(f"{pfx}_r{ri}_b{bi2}_r")]
                        if broken: st.markdown(f'<div style="background:#fff7ed;border:1.5px solid #fed7aa;border-radius:6px;padding:.4rem .85rem;margin:.3rem 0;">\u26a0\ufe0f <strong>Block{"s" if len(broken)>1 else ""} {", ".join(str(b) for b in broken)} {"have" if len(broken)>1 else "has"} start \u2265 end</strong> and will not appear on the timetable.</div>', unsafe_allow_html=True)
                        ts_preview = blocks_to_slots(blocks)
                        if any(v.get("value","") for v in ts_preview.values()):
                            preview_html = _timetable_grid_html([{"name": st.session_state.get(f"{pfx}_r{ri}_name", row.get("name","(Preview)")),"normal_prog": st.session_state.get(f"{pfx}_r{ri}_norm", row.get("normal_prog","")),"time_slots": ts_preview}], PC_TIME_SLOTS)
                            if preview_html:
                                st.markdown('<div style="background:#f0f7eb;border-radius:8px;padding:.5rem .75rem;margin:.4rem 0;border:1px solid #c8e0c8;"><div style="font-size:.68rem;font-weight:600;color:#4a8f33;margin-bottom:3px;">\U0001f441\ufe0f Live timetable preview</div>', unsafe_allow_html=True)
                                st.markdown(preview_html, unsafe_allow_html=True); st.markdown("</div>", unsafe_allow_html=True)
                        else: st.markdown('<div style="font-size:.72rem;color:#c97b1a;padding:.3rem 0;">\u26a0\ufe0f Select a Role for each block to see the timetable preview.</div>', unsafe_allow_html=True)
                    ba1, ba2 = st.columns(2)
                    with ba1:
                        if st.button("\u2795 Add time block", key=f"{pfx}_r{ri}_ab", use_container_width=True):
                            last_bi = len(blocks)-1; last_end = st.session_state.get(f"{pfx}_r{ri}_b{last_bi}_e","") or (blocks[last_bi].get("end","") if last_bi >= 0 else "9:00"); new_bi = len(blocks)
                            blocks.append({"start":last_end,"end":"","role":"","person":""})
                            for k,v in [(f"{pfx}_r{ri}_b{new_bi}_s",last_end),(f"{pfx}_r{ri}_b{new_bi}_e",""),(f"{pfx}_r{ri}_b{new_bi}_r",""),(f"{pfx}_r{ri}_b{new_bi}_p","")]: st.session_state[k] = v
                            st.rerun()
                    with ba2:
                        if st.button("\U0001f37d\ufe0f Add lunch block", key=f"{pfx}_r{ri}_add_lunch", use_container_width=True):
                            bi_new = len(blocks); blocks.append({"start":"12:00","end":"12:30","role":"Lunch Break","person":""})
                            for k,v in [(f"{pfx}_r{ri}_b{bi_new}_s","12:00"),(f"{pfx}_r{ri}_b{bi_new}_e","12:30"),(f"{pfx}_r{ri}_b{bi_new}_r","Lunch Break"),(f"{pfx}_r{ri}_b{bi_new}_p","")]: st.session_state[k] = v
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                if st.button("\u2795 Add another staff member", key=f"{pfx}_ar", use_container_width=True): rows.append({"name":"","normal_prog":"","blocks":[]}); st.rerun()
                st.markdown("---")
                all_broken = [f"{st.session_state.get(f'{pfx}_r{ri2}_name','') or f'Row {ri2+1}'} \u2014 Block {bi2+1} ({st.session_state.get(f'{pfx}_r{ri2}_b{bi2}_s','')}\u2192{st.session_state.get(f'{pfx}_r{ri2}_b{bi2}_e','')})" for ri2, row2 in enumerate(st.session_state[rows_key]) for bi2 in range(len(row2.get("blocks",[]))) if st.session_state.get(f"{pfx}_r{ri2}_b{bi2}_s") and st.session_state.get(f"{pfx}_r{ri2}_b{bi2}_e") and st.session_state.get(f"{pfx}_r{ri2}_b{bi2}_r") and _t2m(st.session_state.get(f"{pfx}_r{ri2}_b{bi2}_s","")) >= _t2m(st.session_state.get(f"{pfx}_r{ri2}_b{bi2}_e",""))]
                if all_broken: st.error("\u26d4 **Cannot save \u2014 fix blocks with Start \u2265 End:**\n\n" + "\n".join(f"- {b}" for b in all_broken))
                sa1, sa2 = st.columns(2)
                with sa1:
                    if st.button("\U0001f4be Save Program Change", type="primary", key=f"{pfx}_save", use_container_width=True, disabled=bool(all_broken)):
                        if reason == "Staff Absence" and not staff_absent.strip(): st.warning("Please enter the absent staff member's name.")
                        else:
                            valid_rows = []
                            for ri, row in enumerate(st.session_state[rows_key]):
                                name = st.session_state.get(f"{pfx}_r{ri}_name", row.get("name","")).strip(); norm = st.session_state.get(f"{pfx}_r{ri}_norm", row.get("normal_prog",""))
                                fresh_blocks = [{"start": st.session_state.get(f"{pfx}_r{ri}_b{bi}_s",""),"end": st.session_state.get(f"{pfx}_r{ri}_b{bi}_e",""),"role": st.session_state.get(f"{pfx}_r{ri}_b{bi}_r",""),"person": st.session_state.get(f"{pfx}_r{ri}_b{bi}_p","")} for bi in range(len(row.get("blocks",[])))]
                                if name or fresh_blocks: valid_rows.append({"name": name, "normal_prog": norm, "blocks": fresh_blocks})
                            entry = {"id": (existing or {}).get("id"),"reason": reason,"staff_absent": staff_absent.strip(),"has_trt": has_trt,"trt_name": trt_name.strip() if has_trt else "","staff_rows": valid_rows}
                            saved = save_bulletin_change(d, entry)
                            if saved:
                                st.success("\u2705 Saved!")
                                for k in [k for k in st.session_state if k.startswith(pfx)]: del st.session_state[k]
                                st.session_state["_pc_editing"] = None; st.session_state["_pc_adding"] = False; st.rerun()
                with sa2:
                    if st.button("Cancel", key=f"{pfx}_cancel", use_container_width=True):
                        for k in [k for k in st.session_state if k.startswith(pfx)]: del st.session_state[k]
                        st.session_state["_pc_editing"] = None; st.session_state["_pc_adding"] = False; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            _editing = st.session_state.get("_pc_editing"); _adding = st.session_state.get("_pc_adding", False)
            if not _editing and not _adding:
                if st.button("\u2795 Add Program Change", type="primary", key="pc_add_new", use_container_width=True):
                    st.session_state["_pc_form_id"] = int(_time.time() * 1000); st.session_state["_pc_adding"] = True; st.session_state["_pc_editing"] = None; st.rerun()
            if _adding and not _editing: _render_change_form(current_date, existing=None)
            elif _editing: _render_change_form(current_date, existing=_editing)

        if _changes:
            st.markdown("---")
            st.markdown('<div style="background:white;border-radius:12px;border:1.5px solid #d8e8d4;padding:1.25rem 1.5rem;margin-bottom:1rem;"><div style="font-size:1rem;font-weight:700;color:#1a2e44;margin-bottom:.2rem;">\U0001f4e4 Share / Download Program Changes</div><div style="font-size:.8rem;color:#7a907a;">Plain text for SMS \u00b7 Printable/PDF sheet for email or TRT</div></div>', unsafe_allow_html=True)
            _plain = _build_plain_text_bc(_changes, current_date); _html_export = _build_html_sheet_bc(_changes, current_date)
            ex1, ex2, ex3 = st.columns([1,1,2])
            with ex1: st.download_button("\U0001f4f1 Download text (SMS/email)", data=_plain, file_name=f"CLC_ProgramChanges_{current_date.strftime('%Y-%m-%d')}.txt", mime="text/plain", use_container_width=True, type="secondary")
            with ex2: st.download_button("\U0001f5a8\ufe0f Download printable sheet", data=_html_export, file_name=f"CLC_ProgramChanges_{current_date.strftime('%Y-%m-%d')}.html", mime="text/html", use_container_width=True, type="secondary")
            with ex3: st.markdown('<div style="font-size:.75rem;color:#7a907a;padding-top:.5rem;">\U0001f4a1 <strong>Text file</strong> \u2014 paste into SMS or email &nbsp;\u00b7&nbsp; <strong>Printable sheet</strong> \u2014 open in browser then Print or Save as PDF</div>', unsafe_allow_html=True)
            with st.expander("\U0001f441\ufe0f Preview plain text"): st.code(_plain, language=None)

    st.markdown('</div>', unsafe_allow_html=True)

    if edit:
        st.markdown('<div style="background:white;border-top:2px solid #e8f0e3;padding:1rem 2rem;position:sticky;bottom:0;z-index:100;display:flex;gap:1rem;align-items:center;">', unsafe_allow_html=True)
        bsv1, bsv2, bsv3 = st.columns([2,2,6])
        with bsv1:
            if st.button("\U0001f4be Save Bulletin", type="primary", use_container_width=True, key="bottom_save"): st.session_state["_pending_save"] = True
        with bsv2:
            if st.button("\U0001f6aa Discard & Exit", type="secondary", use_container_width=True, key="bottom_discard"): st.session_state.edit_mode = False; st.rerun()
        with bsv3: st.markdown('<span style="font-size:.78rem;color:#9ab09a;">\U0001f4a1 Changes are saved to the database and appear on the staff room display immediately.</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("_pending_save"):
        st.session_state["_pending_save"] = False
        save_data = {k: v for k, v in bulletin_data.items() if k != "id"}
        db.save_bulletin(current_date, save_data)
        st.session_state.edit_mode = False; st.success("\u2705 Bulletin saved!")
        if st.query_params.get("from_display") == "true":
            st.markdown('<meta http-equiv="refresh" content="2;url=/?display=true">', unsafe_allow_html=True); st.info("\u21a9\ufe0f Returning to staff room display in 2 seconds...")
        st.rerun()


with quickadd_tab:
    st.markdown("""<div style="background:linear-gradient(135deg,#3d7a28,#6BBF4E);border-radius:14px;padding:1.5rem 2rem;margin-bottom:1.5rem;color:white;"><div style="font-size:1.3rem;font-weight:700;margin-bottom:.3rem;">\U0001f4dd Add a Staff Notice</div><div style="font-size:.85rem;opacity:.85;">No password needed. Your notice will appear on today's bulletin and the staff room display straight away.</div></div>""", unsafe_allow_html=True)
    qa_col, preview_col = st.columns(2)
    with qa_col:
        with st.form("quick_add_form", clear_on_submit=True):
            qa_name = st.text_input("Your name *", placeholder="e.g. Sarah"); qa_cat = st.selectbox("Category *", list(NOTICE_CATS.keys()))
            qa_title = st.text_input("Title *", placeholder="e.g. Staff meeting moved to Room 3"); qa_body = st.text_area("Details", height=120); qa_date = st.date_input("For which day?", value=date.today())
            if st.form_submit_button("\U0001f4e2 Post Notice", type="primary", use_container_width=True):
                if not qa_name.strip(): st.warning("Please enter your name.")
                elif not qa_title.strip(): st.warning("Please enter a title.")
                else: save_notice({"submitted_by":qa_name.strip(),"category":qa_cat,"title":qa_title.strip(),"body":qa_body.strip(),"notice_date":str(qa_date)}); st.success(f"\u2705 Notice posted for {qa_date.strftime('%-d %B')}!"); st.balloons()
    with preview_col:
        st.markdown("**Category guide:**")
        for cat, cfg in NOTICE_CATS.items(): st.markdown(f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;"><span style="background:{cfg["bg"]};color:{cfg["color"]};font-size:.72rem;font-weight:700;padding:.2rem .6rem;border-radius:20px;min-width:90px;text-align:center;">{cfg["emoji"]} {cat}</span></div>', unsafe_allow_html=True)
    st.markdown("---"); st.markdown(f"**Notices posted for {date.today().strftime('%A %-d %B')}:**")
    listed = load_notices(for_date=date.today())
    if not listed: st.markdown('<div style="text-align:center;padding:2rem;color:#9ab09a;font-size:.85rem;">No notices yet today \u2014 be the first!</div>', unsafe_allow_html=True)
    else:
        for n in listed:
            cat = n.get("category","General"); nc = NOTICE_CATS.get(cat, NOTICE_CATS["General"]); nid = n.get("id","")
            nl1, nl2 = st.columns([9,1])
            with nl1: st.markdown(f'<div style="background:white;border-radius:10px;border-left:4px solid {nc["color"]};padding:.75rem 1rem;margin-bottom:.5rem;"><span style="background:{nc["bg"]};color:{nc["color"]};font-size:.65rem;font-weight:700;text-transform:uppercase;padding:.15rem .5rem;border-radius:20px;">{nc["emoji"]} {cat}</span><span style="font-size:.7rem;color:#9ab09a;margin-left:.5rem;">from {n.get("submitted_by","")}</span><div style="font-size:.9rem;font-weight:700;color:#1a2e44;margin:.3rem 0 .2rem;">{n.get("title","")}</div><div style="font-size:.82rem;color:#3a4a3a;line-height:1.5;">{n.get("body","") or ""}</div></div>', unsafe_allow_html=True)
            with nl2:
                st.write("")
                if st.session_state.authenticated:
                    if st.button("\U0001f5d1\ufe0f", key=f"qa_del_{nid}"): delete_notice(nid); st.rerun()


with archive_tab:
    st.markdown("### \U0001f5c2\ufe0f Bulletin Archive")
    a1, a2 = st.tabs(["Browse by Week / Term","Search"])
    with a1:
        c1, c2 = st.columns(2)
        with c1: browse_date = st.date_input("Select a date", value=date.today(), key="archive_date")
        with c2: browse_mode = st.selectbox("Browse by", ["Week","Term"])
        y = browse_date.year; terms_map = {1:(date(y,1,28),date(y,4,11)),2:(date(y,4,28),date(y,7,4)),3:(date(y,7,21),date(y,9,26)),4:(date(y,10,13),date(y,12,12))}
        if browse_mode == "Week":
            wk = week_dates(browse_date); results = db.get_bulletins_range(wk[0], wk[-1]); st.markdown(f"**Week of {wk[0].strftime('%-d %b %Y')}**")
        else:
            t_start = t_end = None
            for t,(s,e) in terms_map.items():
                if s <= browse_date <= e: t_start, t_end = s, e; st.markdown(f"**Term {t}, {y}**"); break
            results = db.get_bulletins_range(t_start, t_end) if t_start else []
            if not t_start: st.info("Date is outside term dates.")
        if results:
            for row in results:
                d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                st.markdown(f'<div class="arch-card"><div class="arch-card-date">{d.strftime("%A %-d %B %Y")}</div><div class="arch-card-fact">\U0001f4a1 {row.get("fun_fact","") or "No fun fact recorded"}</div></div>', unsafe_allow_html=True)
                if st.button(f"Open \u2192", key=f"arch_{row['date']}"): st.session_state.selected_date = d; st.rerun()
        else: st.markdown('<div class="empty-state"><div class="icon">\U0001f4ed</div>No bulletins found for this period</div>', unsafe_allow_html=True)
    with a2:
        keyword = st.text_input("\U0001f50d Search all bulletins", placeholder="Enter staff name, student, excursion, note...")
        if keyword and len(keyword) >= 2:
            results = db.search_bulletins(keyword)
            if results:
                st.markdown(f"**{len(results)} result(s) found for '{keyword}'**")
                for row in results:
                    d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                    st.markdown(f'<div class="arch-card"><div class="arch-card-date">{d.strftime("%A %-d %B %Y")}</div></div>', unsafe_allow_html=True)
                    if st.button(f"Open \u2192", key=f"search_{row['date']}"): st.session_state.selected_date = d; st.rerun()
            else: st.markdown(f'<div class="empty-state"><div class="icon">\U0001f50d</div>No results for "{keyword}"</div>', unsafe_allow_html=True)


with login_tab:
    if st.session_state.authenticated:
        st.success("\u2705 You are logged in as Staff")
        st.markdown("You can now edit bulletins \u2014 head to the **\U0001f4cb Bulletin** tab and click **\u270f\ufe0f Edit**.")
        if st.button("\U0001f6aa Logout", type="secondary"): st.session_state.authenticated = False; st.session_state.edit_mode = False; st.rerun()
    else:
        st.markdown('<div class="auth-gate"><h2>\U0001f510 Staff Login</h2><p>Login to create and edit daily bulletins.</p>', unsafe_allow_html=True)
        pw = st.text_input("Password", type="password", placeholder="Enter staff password")
        if st.button("Login", type="primary", use_container_width=True):
            if pw == ADMIN_PASSWORD: st.session_state.authenticated = True; st.success("\u2705 Logged in! Go to the Bulletin tab to start editing."); st.rerun()
            else: st.error("Incorrect password.")
        st.markdown('</div>', unsafe_allow_html=True)
