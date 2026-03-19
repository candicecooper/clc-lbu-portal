from theme import apply_clc_theme
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

from auth import require_auth, logout_button, get_staff_name
require_auth("Daily Bulletin", "📰")
logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)


# ── DESIGN SYSTEM ─────────────────────────────────────────────

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

# ── NEW PROGRAM CHANGES SYSTEM ────────────────────────────────────────────────
def load_changes(d: date):
    """Load program changes for a specific date from Supabase."""
    try:
        res = _get_sb().table("bulletin_changes").select("*").eq("bulletin_date", str(d)).order("created_at").execute()
        return res.data or []
    except Exception:
        return []

def save_change(d: date, entry: dict):
    """Save a program change entry to Supabase. Returns the saved record."""
    try:
        data = {
            "bulletin_date": str(d),
            "reason": entry.get("reason", ""),
            "staff_absent": entry.get("staff_absent", ""),
            "has_trt": entry.get("has_trt", False),
            "trt_name": entry.get("trt_name", ""),
            "staff_rows": entry.get("staff_rows", []),
        }
        if entry.get("id"):
            res = _get_sb().table("bulletin_changes").update(data).eq("id", entry["id"]).execute()
        else:
            res = _get_sb().table("bulletin_changes").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"Could not save change: {e}")
        return None

def delete_change(change_id: str):
    try:
        _get_sb().table("bulletin_changes").delete().eq("id", change_id).execute()
        return True
    except Exception as e:
        st.error(f"Could not delete: {e}")
        return False

ROLE_OPTIONS = ["", "JP", "PY", "SY", "NIT", "Lunch Cover", "Lunch Break", "Release", "Planning", "Other"]
ROLE_COLORS  = {
    "JP": "#dbeafe", "PY": "#ede9fe", "SY": "#fef3c7",
    "NIT": "#f1f5f9", "Lunch Cover": "#fef9c3", "Lunch Break": "#cffafe",
    "Release": "#dcfce7", "Planning": "#fce7f3", "Other": "#f3f4f6",
}

def _role_badge(role):
    color = ROLE_COLORS.get(role, "#f3f4f6")
    return f'<span style="background:{color};padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:600;">{role}</span>'

def render_change_card(ch, idx, edit):
    """Render a saved change entry as a card."""
    reason = ch.get("reason", "")
    absent = ch.get("staff_absent", "")
    has_trt = ch.get("has_trt", False)
    trt_name = ch.get("trt_name", "")
    rows = ch.get("staff_rows", [])
    
    header = f"{'🙅 ' if reason=='Staff Absence' else '📌 '}{reason}"
    if absent: header += f" — {absent}"
    if has_trt and trt_name: header += f" (TRT: {trt_name})"
    
    with st.container():
        st.markdown(f"""<div style="background:white;border:1.5px solid #e0e8dc;border-left:4px solid #6BBF4E;
            border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.75rem;">
            <div style="font-weight:700;color:#1a2e44;margin-bottom:0.5rem;">{header}</div>""",
            unsafe_allow_html=True)
        
        for row in rows:
            name = row.get("name", "")
            blocks = row.get("blocks", [])
            if blocks:
                block_html = " · ".join([
                    f'<span style="background:{ROLE_COLORS.get(b.get("role",""), "#f3f4f6")};'
                    f'padding:1px 6px;border-radius:8px;font-size:0.72rem;font-weight:600;">'
                    f'{b.get("start","")}–{b.get("end","")} {b.get("role","")}'
                    f'{" → " + b.get("person","") if b.get("person") else ""}</span>'
                    for b in blocks
                ])
                st.markdown(f'<div style="margin:2px 0;font-size:0.82rem;color:#1a2e44;"><b>{name}:</b> {block_html}</div>',
                    unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        if edit:
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("✏️ Edit", key=f"ch_edit_{ch['id']}_{idx}", use_container_width=True):
                    st.session_state["pc_editing"] = ch
                    st.rerun()
            with c2:
                if st.button("🗑️ Delete", key=f"ch_del_{ch['id']}_{idx}", use_container_width=True):
                    delete_change(ch["id"])
                    st.rerun()

def render_change_form(current_date, edit, existing=None):
    """Render the form to add/edit a program change entry."""
    if not edit:
        return
    
    is_editing = existing is not None
    prefix = f"pcf_{'e' if is_editing else 'n'}"
    
    st.markdown(f"#### {'✏️ Edit' if is_editing else '➕ Add'} Program Change")
    
    with st.container():
        st.markdown('<div style="background:#f8fdf6;border:1.5px solid #c8e0c8;border-radius:12px;padding:1rem 1.25rem;">', unsafe_allow_html=True)
        
        # Step 1: Reason
        reason = st.radio("Reason for change", ["Staff Absence", "Site Need / Other"],
                          index=0 if (existing or {}).get("reason","") != "Site Need / Other" else 1,
                          key=f"{prefix}_reason", horizontal=True)
        
        staff_absent = ""
        has_trt = False
        trt_name = ""
        
        if reason == "Staff Absence":
            c1, c2 = st.columns(2)
            with c1:
                staff_absent = st.text_input("Absent staff member *",
                    value=(existing or {}).get("staff_absent", ""),
                    placeholder="e.g. John Smith", key=f"{prefix}_absent")
            with c2:
                has_trt = st.checkbox("TRT coming in?",
                    value=(existing or {}).get("has_trt", False), key=f"{prefix}_trt")
            if has_trt:
                trt_name = st.text_input("TRT name",
                    value=(existing or {}).get("trt_name", ""),
                    placeholder="e.g. Ms Jones", key=f"{prefix}_trt_name")
        
        st.markdown("---")
        st.markdown("**Staff timetable rows** — add each person whose day is affected:")
        
        # Manage rows in session state
        rows_key = f"{prefix}_rows"
        if rows_key not in st.session_state:
            if existing and existing.get("staff_rows"):
                st.session_state[rows_key] = existing["staff_rows"]
            elif has_trt and trt_name:
                st.session_state[rows_key] = [{"name": trt_name or "TRT", "blocks": []}]
            else:
                st.session_state[rows_key] = [{"name": staff_absent or "", "blocks": []}]
        
        rows = st.session_state[rows_key]
        
        for ri, row in enumerate(rows):
            st.markdown(f'<div style="background:white;border:1px solid #d8ead2;border-radius:8px;padding:0.75rem;margin-bottom:0.5rem;">', unsafe_allow_html=True)
            
            rc1, rc2, rc3 = st.columns([3, 2, 1])
            with rc1:
                row["name"] = st.text_input("Staff / SSO name",
                    value=row.get("name", ""),
                    placeholder="e.g. Sarah Jones", key=f"{prefix}_r{ri}_name")
            with rc2:
                autofill = st.selectbox("Autofill all blocks with",
                    ROLE_OPTIONS, key=f"{prefix}_r{ri}_autofill")
            with rc3:
                st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                if st.button("▶ Fill", key=f"{prefix}_r{ri}_fill", help="Fill all blocks with selected role"):
                    if autofill:
                        for b in row["blocks"]:
                            b["role"] = autofill
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Show existing blocks
            blocks = row.get("blocks", [])
            for bi, block in enumerate(blocks):
                bc1, bc2, bc3, bc4, bc5 = st.columns([2, 2, 2, 2, 1])
                with bc1:
                    block["start"] = st.text_input("Start", value=block.get("start", ""),
                        placeholder="9:00", key=f"{prefix}_r{ri}_b{bi}_start")
                with bc2:
                    block["end"] = st.text_input("End", value=block.get("end", ""),
                        placeholder="10:30", key=f"{prefix}_r{ri}_b{bi}_end")
                with bc3:
                    try:
                        ridx = ROLE_OPTIONS.index(block.get("role",""))
                    except ValueError:
                        ridx = 0
                    block["role"] = st.selectbox("Role", ROLE_OPTIONS, index=ridx,
                        key=f"{prefix}_r{ri}_b{bi}_role")
                with bc4:
                    block["person"] = st.text_input("Covering/detail",
                        value=block.get("person",""),
                        placeholder="Optional", key=f"{prefix}_r{ri}_b{bi}_person")
                with bc5:
                    st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                    if st.button("✕", key=f"{prefix}_r{ri}_b{bi}_del"):
                        blocks.pop(bi)
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            
            row["blocks"] = blocks
            
            ba1, ba2 = st.columns([2, 5])
            with ba1:
                if st.button("➕ Add time block", key=f"{prefix}_r{ri}_addblock"):
                    row["blocks"].append({"start": "", "end": "", "role": "", "person": ""})
                    st.rerun()
            with ba2:
                if len(rows) > 1:
                    if st.button(f"🗑️ Remove {row.get('name','this row') or 'this row'}", key=f"{prefix}_r{ri}_delrow"):
                        rows.pop(ri)
                        st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("➕ Add another staff member", key=f"{prefix}_addrow"):
            rows.append({"name": "", "blocks": []})
            st.rerun()
        
        st.markdown("---")
        sa1, sa2, sa3 = st.columns([2, 2, 3])
        with sa1:
            if st.button("💾 Save This Change", type="primary", key=f"{prefix}_save", use_container_width=True):
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
                    saved = save_change(current_date, entry)
                    if saved:
                        st.success("✅ Change saved!")
                        # Clear form state
                        for k in list(st.session_state.keys()):
                            if k.startswith(prefix):
                                del st.session_state[k]
                        st.session_state["pc_editing"] = None
                        st.session_state["pc_adding"] = False
                        st.rerun()
        with sa2:
            if st.button("Cancel", key=f"{prefix}_cancel", use_container_width=True):
                for k in list(st.session_state.keys()):
                    if k.startswith(prefix):
                        del st.session_state[k]
                st.session_state["pc_editing"] = None
                st.session_state["pc_adding"] = False
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


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

    
    # Auto-refresh every 60 seconds — keeps data current and rolls over at midnight
    if "display_last_refresh" not in st.session_state:
        st.session_state.display_last_refresh = time.time()
    if time.time() - st.session_state.display_last_refresh > 60:
        st.session_state.display_last_refresh = time.time()
        # Snap to today on each refresh cycle
        st.session_state.display_date = date.today()
        st.rerun()

    # Google fonts
    
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
        pass  # display content restored below
    
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

# ── PAGE TABS ─────────────────────────────────────────────────
page_tab, quickadd_tab, archive_tab, login_tab = st.tabs(["📋 Bulletin", "📝 Quick Add", "🗂️ Archive", "🔐 Staff"])

with page_tab:
    # Date selector
    _edit = st.session_state.get("authenticated", False)
    
    # Week navigation
    _week = week_dates(st.session_state.get("selected_date", _default_date()))
    _nav_l, _nav_m, _nav_r = st.columns([1, 4, 1])
    with _nav_l:
        if st.button("← Prev Week", key="pt_prev"):
            st.session_state.selected_date = _week[0] - timedelta(days=7); st.rerun()
    with _nav_m:
        _day_cols = st.columns(5)
        for _i, _d in enumerate(_week):
            with _day_cols[_i]:
                _is_cur = _d == st.session_state.get("selected_date", _default_date())
                if st.button(_d.strftime("%a %-d %b"), key=f"pt_day_{_d}",
                             type="primary" if _is_cur else "secondary", use_container_width=True):
                    st.session_state.selected_date = _d; st.rerun()
    with _nav_r:
        if st.button("Next Week →", key="pt_next"):
            st.session_state.selected_date = _week[0] + timedelta(days=7); st.rerun()
    
    _cur_date = st.session_state.get("selected_date", _default_date())
    st.markdown(f"## 📊 Program Changes — {_cur_date.strftime('%A %-d %B %Y')}")
    st.caption("Changes are saved immediately — no risk of losing data.")
    
    if not _edit:
        st.info("🔐 Log in as staff to add or edit program changes.")
    
    # Load existing changes
    _changes = load_changes(_cur_date)
    
    if _changes:
        st.markdown(f"**{len(_changes)} change(s) recorded:**")
        for _ci, _ch in enumerate(_changes):
            render_change_card(_ch, _ci, _edit)
    else:
        st.markdown('<div style="text-align:center;padding:1.5rem;color:#9ab09a;font-size:0.85rem;background:#f8fdf6;border-radius:10px;">📭 No program changes recorded for this day</div>', unsafe_allow_html=True)
    
    if _edit:
        st.markdown("---")
        _editing = st.session_state.get("pc_editing")
        _adding = st.session_state.get("pc_adding", False)
        
        if not _editing and not _adding:
            if st.button("➕ Add Program Change", type="primary", key="pc_add_new", use_container_width=True):
                st.session_state["pc_adding"] = True
                st.session_state["pc_editing"] = None
                st.rerun()
        
        if _adding and not _editing:
            render_change_form(_cur_date, True, existing=None)
        elif _editing:
            render_change_form(_cur_date, True, existing=_editing)

with quickadd_tab:
    pass  # quickadd content below

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
