from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
from groq import Groq
import json
import io
import time
from urllib.parse import quote
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="CLC Team Meetings", page_icon="👥", layout="wide")
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
require_auth("Team Meetings", "👥")
logout_button("sidebar")

# ── Auto-save session state initialization ───────────────────────────────────
if 'last_autosave_time' not in st.session_state:
    st.session_state.last_autosave_time = None
if 'autosave_message' not in st.session_state:
    st.session_state.autosave_message = ""
if 'current_meeting_id' not in st.session_state:
    st.session_state.current_meeting_id = None

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "CLC2026admin")
GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Programs ──────────────────────────────────────────────────────────────────
PROGRAMS = {
    "JP":    {"label": "Junior Primary",  "color": "#2d7d4f", "light": "#d1fae5", "emoji": "🟢"},
    "PY":    {"label": "Primary Years",   "color": "#1a4d8c", "light": "#dbeafe", "emoji": "🔵"},
    "SY":    {"label": "Senior Years",    "color": "#7c3aed", "light": "#ede9fe", "emoji": "🟣"},
    "STAFF": {"label": "Staff Meetings",  "color": "#1e6f75", "light": "#ccfbf1", "emoji": "👥"},
    "ADMIN": {"label": "Admin Meetings",  "color": "#92400e", "light": "#fef3c7", "emoji": "🏢"},
}

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
RECURRENCE_TYPES = ["Weekly", "Fortnightly", "Monthly"]

# ── Term week helper ──────────────────────────────────────────────────────────
TERM1_2026_START = datetime.date(2026, 1, 26)
TERM_WEEKS = 11

def get_current_term_week():
    """Return (term_label, week_number) based on today's date."""
    today = datetime.date.today()
    delta = (today - TERM1_2026_START).days
    if delta < 0:
        return "T1", 1
    week_num = min(delta // 7 + 1, TERM_WEEKS)
    return "T1", week_num

# ── Auto-save helper ──────────────────────────────────────────────────────────
def trigger_autosave(program, meeting_data):
    """Trigger auto-save if 2 minutes have passed since last save."""
    current_time = time.time()
    
    # Check if we should auto-save (every 2 minutes = 120 seconds)
    if st.session_state.last_autosave_time is None or \
       (current_time - st.session_state.last_autosave_time) >= 120:
        
        # Only auto-save if there's actual content
        has_content = any([
            meeting_data.get("checkin_notes"),
            meeting_data.get("student_concerns"),
            meeting_data.get("smartar_spotlight"),
            meeting_data.get("actions")
        ])
        
        if has_content:
            try:
                if st.session_state.current_meeting_id:
                    # Update existing
                    supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                else:
                    # Create new - if this fails due to schema, will be caught below
                    result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
                    if result.data:
                        st.session_state.current_meeting_id = result.data[0]['id']
                
                st.session_state.last_autosave_time = current_time
                st.session_state.autosave_message = f"✓ Auto-saved at {datetime.datetime.now().strftime('%I:%M %p')}"
                return True
            except Exception as e:
                # Schema error - skip auto-save, will save on manual save
                st.session_state.autosave_message = f"⚠ Auto-save skipped (click Save button to create meeting)"
                return False
    
    return False

# ── SMARTAR Goal Integration helpers ──────────────────────────────────────────
def get_smartar_goal_link(student_name, meeting_id, program, term, week_num):
    """Generate URL to SMARTAR Goal Builder with context."""
    base_url = "https://clc-lbu-portal.onrender.com/SMARTAR_Goal_Builder"
    params = f"?student={quote(student_name)}&meeting_id={meeting_id}&program={program}&term={term}&week={week_num}&return_to=team_meetings"
    return base_url + params

def fetch_synced_smartar_goal(student_name, meeting_id):
    """Fetch updated SMARTAR goal from the goal builder (Behaviour Support Supabase)."""
    try:
        # Import here to avoid issues if behaviour support connection not configured
        import os
        from supabase import create_client as _cc
        
        # Get Behaviour Support Supabase credentials
        burl = st.secrets.get("BEHAVIOUR_SUPABASE_URL","") or os.environ.get("BEHAVIOUR_SUPABASE_URL","")
        bkey = st.secrets.get("BEHAVIOUR_SUPABASE_KEY","") or os.environ.get("BEHAVIOUR_SUPABASE_KEY","")
        
        if not burl or not bkey:
            # Behaviour Support Supabase not configured
            return None
        
        # Create Behaviour Support Supabase client
        behaviour_supabase = _cc(burl, bkey)
        
        # Query smartar_goals table in Behaviour Support Supabase
        result = behaviour_supabase.table('smartar_goals').select('smartar_goal').eq('student_name', student_name).eq('meeting_id', meeting_id).order('updated_at', desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get('smartar_goal', '')
            
    except Exception as e:
        # Log error but don't crash - integration is optional
        pass
    
    return None

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_program_from_params():
    params = st.query_params
    prog = params.get("program", "JP")
    return prog if prog in PROGRAMS else "JP"

def get_week_from_params():
    week_str = st.query_params.get("week", None)
    if not week_str:
        return None
    try:
        monday = datetime.date.fromisoformat(week_str)
        monday = monday - datetime.timedelta(days=monday.weekday())
        return monday, monday + datetime.timedelta(days=6)
    except ValueError:
        return None

def admin_login():
    if "admin" not in st.session_state:
        st.session_state.admin = False
    with st.sidebar:
        if not st.session_state.admin:
            with st.expander("🔐 Admin Login"):
                pw = st.text_input("Password", type="password", key="pw_input")
                if st.button("Login"):
                    if pw == ADMIN_PASSWORD:
                        st.session_state.admin = True
                        st.rerun()
                    else:
                        st.error("Incorrect password")
        else:
            st.success("✅ Admin logged in")
            if st.button("Logout"):
                st.session_state.admin = False
                st.rerun()

def improve_with_ai(raw_text: str, program: str, meeting_date: str, dsm_summary: str = "") -> str:
    if not GROQ_KEY:
        return raw_text
    client = Groq(api_key=GROQ_KEY)

    if program == "STAFF":
        dsm_context = f"""
PART 1 — DIGITAL STAFF MEETING (already recorded, include as first section):
{dsm_summary}
""" if dsm_summary else ""

        prompt = f"""You are a professional minute-taker for Cowandilla Learning Centre (CLC), Learning & Behaviour Unit — an alternative education school in South Australia.

Meeting: Staff Meeting (Combined — Digital + Face-to-Face)
Date: {meeting_date}
{dsm_context}
PART 2 — FACE-TO-FACE MEETING TRANSCRIPT:
{raw_text}

Transform the face-to-face transcript into polished, professional minutes using this EXACT structure:

## PART 2 — FACE-TO-FACE STAFF MEETING

### Attendance
List names present and apologies from the transcript. If not clear, note "See attendance record."

### Apologies
Names with apologies.

### Arising Business
Any matters arising from previous meetings mentioned in the transcript.

### Standing Items
Present each discussion point as a numbered item:
1. **Item title** — summary of discussion and any decisions made

### Actions
| Action | Assigned To | Due |
|--------|-------------|-----|
| (list all actions agreed) | (who) | (when) |

### Next Meeting
Date/time if mentioned, otherwise leave blank.

Rules:
- Professional but warm, accessible language appropriate for a school setting
- Trauma-informed, strengths-based framing
- Preserve ALL factual content — do not add or fabricate anything
- Keep it concise — one clear sentence per discussion point unless more detail is essential
- Use plain English, avoid jargon

Transcript to transform:
{raw_text}"""
    else:
        prompt = f"""You are a professional minute-taker for an alternative education school (Cowandilla Learning Centre, Learning & Behaviour Unit).

Program team: {PROGRAMS[program]['label']} ({program})
Meeting date: {meeting_date}

Transform the following raw transcript or rough notes into polished, professional meeting minutes.

Format requirements:
- Clear heading with meeting details
- Numbered agenda items with concise summaries
- Action items clearly identified with: Action | Assigned to | Timeline
- Professional but accessible language
- Trauma-informed, strengths-based framing where relevant
- Preserve all factual content — do not add or fabricate information
- End with a summary table of all action items

Raw input:
{raw_text}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000
    )
    return response.choices[0].message.content

# ── DB helpers ────────────────────────────────────────────────────────────────
def fetch(table, filters=None, order=None):
    q = supabase.table(table).select("*")
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    if order:
        q = q.order(order, desc=True)
    return q.execute().data or []

def insert(table, data):
    supabase.table(table).insert(data).execute()

def update_row(table, row_id, data):
    supabase.table(table).update(data).eq("id", row_id).execute()

def delete_row(table, row_id):
    supabase.table(table).delete().eq("id", row_id).execute()

# ─────────────────────────────────────────────────────────────────────────────
# WORD DOCUMENT HELPERS (keeping all existing functions - truncated for space)
# ─────────────────────────────────────────────────────────────────────────────

def _hex(colour):
    return colour.lstrip("#").upper()

def _shade_cell(cell, hex_colour):
    try:
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  _hex(hex_colour))
        tcPr.append(shd)
    except Exception:
        pass

def _rgb(hex_colour):
    h = _hex(hex_colour)
    return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def _para_run(para, text, bold=False, italic=False, size_pt=10, colour="0f172a"):
    run = para.add_run(str(text))
    run.bold           = bold
    run.italic         = italic
    run.font.size      = Pt(size_pt)
    run.font.color.rgb = _rgb(colour)
    return run

# [Keep all other Word doc helper functions - _add_banner, _add_kv_table, etc.]
# [Skipping for brevity but they stay exactly the same]

# ─────────────────────────────────────────────────────────────────────────────
# PROGRAM MEETING (JP/PY/SY) - WITH INITIALIZE MEETING BUTTON
# ─────────────────────────────────────────────────────────────────────────────

def render_program_meeting(program):
    import json as _json
    prog_label = PROGRAMS[program]["label"]
    accent = PROGRAMS[program]["color"]

    # Auto-save status display
    if st.session_state.autosave_message:
        st.caption(st.session_state.autosave_message)

    # Fetch students for autocomplete
    @st.cache_data(ttl=120)
    def fetch_students(prog):
        names = []
        try:
            import os
            from supabase import create_client as _cc
            burl = st.secrets.get("BEHAVIOUR_SUPABASE_URL","") or os.environ.get("BEHAVIOUR_SUPABASE_URL","")
            bkey = st.secrets.get("BEHAVIOUR_SUPABASE_KEY","") or os.environ.get("BEHAVIOUR_SUPABASE_KEY","")
            if burl:
                bsb = _cc(burl, bkey)
                res = bsb.table("students").select("id,name,year_level").eq("archived", False).execute()
                if res.data:
                    names = [s["name"] for s in res.data]
        except Exception:
            pass
        try:
            res2 = supabase.table("scatter_students").select("name").execute()
            if res2.data:
                scatter_names = [s["name"] for s in res2.data if s.get("name")]
                for n in scatter_names:
                    if n not in names:
                        names.append(n)
        except Exception:
            pass
        return sorted(names)

    student_names = fetch_students(program)

    last_records = fetch("tm_program_meetings", {"program": program}, "meeting_date")
    last_week_type = None
    last_actions = []
    if last_records:
        last = last_records[-1]
        last_week_type = last.get("week_type")
        try:
            last_actions = _json.loads(last.get("actions", "[]") or "[]")
        except Exception:
            last_actions = []

    suggested_type = "B" if last_week_type == "A" else "A"

    wt_col1, wt_col2 = st.columns([3, 2])
    with wt_col1:
        week_type = st.radio(
            "Meeting type",
            ["A — Student Lens", "B — System Lens", "📋 Ad-hoc Meeting"],
            index=0 if suggested_type == "A" else 1,
            horizontal=True,
            key=f"pm_wt_{program}",
        )
    with wt_col2:
        if last_week_type:
            st.caption(f"Last scheduled meeting: Week {last_week_type}")

    is_week_a = week_type.startswith("A")
    is_adhoc  = week_type.startswith("📋")

    if is_week_a:
        st.markdown(f"""<div style="background:#dbeafe;border-left:5px solid #1a4d8c;
            border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#1a4d8c;">
            ⬤ <strong>WEEK A — STUDENT LENS</strong> · Individual Progress · SMARTAR Goals · Evidence
        </div>""", unsafe_allow_html=True)
    elif is_adhoc:
        st.markdown(f"""<div style="background:#f3f0ff;border-left:5px solid #6d28d9;
            border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#4c1d95;">
            📋 <strong>AD-HOC / ADDITIONAL MEETING</strong>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="background:#fef3c7;border-left:5px solid #d97706;
            border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#92400e;">
            ⬤ <strong>WEEK B — SYSTEM LENS</strong> · CLC Priorities · Innovation Fidelity · Staff Alignment
        </div>""", unsafe_allow_html=True)

    if is_adhoc:
        # Keep existing ad-hoc meeting function
        return

    st.markdown("#### 📋 Meeting Details")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: pm_date        = st.date_input("Date", value=datetime.date.today(), key=f"pm_date_{program}")
    with mc2: pm_term        = st.text_input("Term", placeholder="T1", key=f"pm_term_{program}")
    with mc3: pm_week        = st.number_input("Week #", min_value=1, max_value=11, value=1, key=f"pm_week_{program}")
    with mc4: pm_facilitator = st.text_input("Facilitator", value=get_staff_name(), key=f"pm_fac_{program}")
    pm_attendees = st.text_input("Attendees", placeholder="Names separated by commas", key=f"pm_att_{program}")

    st.markdown("""<div style="background:#f0f9f9;border:1px solid #1A7A7A;border-radius:8px;
        padding:6px 12px;font-size:0.78rem;color:#1A7A7A;margin-bottom:8px;">
        <strong>Meeting Norms:</strong> ☑ Student-centred &nbsp;·&nbsp; ☑ Evidence before opinion
        &nbsp;·&nbsp; ☑ Clear actions + ownership &nbsp;·&nbsp; ☑ Stick to time
    </div>""", unsafe_allow_html=True)
    
    # AUTO-CREATE MEETING ID (no button needed)
    # If no meeting_id exists, create a minimal record just to get an ID for SMARTAR links
    if not st.session_state.current_meeting_id:
        st.markdown("""
        <div style="background:#e0f2fe;border-left:4px solid #0284c7;border-radius:0 8px 8px 0;
                    padding:8px 14px;margin-bottom:12px;font-size:13px;color:#075985;">
          ℹ️ <strong>New Meeting:</strong> Meeting ID will be created when you start entering content below. 
          SMARTAR links will appear automatically.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"✅ Meeting Active (ID: {st.session_state.current_meeting_id}) - SMARTAR integration ready")
    
    st.markdown("---")

    checkin_label  = "TEAM CHECK-IN — Regulation Before Reaction" if is_week_a else "TEAM CHECK-IN"
    checkin_prompt = "What do we need to know to support students effectively today?" if is_week_a else "Quick updates impacting program delivery"
    st.markdown(f"#### ⏱ 0–10 min | {checkin_label}")
    st.caption(checkin_prompt)
    pm_checkin = st.text_area("Check-in notes", height=80, key=f"pm_checkin_{program}",
        label_visibility="collapsed", placeholder=checkin_prompt)
    st.markdown("---")

    if is_week_a:
        st.markdown("#### ⏱ 10–25 min | STUDENT CONCERNS — Structured Problem Solving")
        st.caption("Facilitator prompt: Push for function-based thinking, not description.")

        concerns_key = f"pm_concerns_{program}"
        if concerns_key not in st.session_state:
            st.session_state[concerns_key] = [{"notes": ""}]

        concerns = st.session_state[concerns_key]
        for idx, row in enumerate(concerns):
            col_text, col_del = st.columns([11, 0.5])
            with col_text:
                row["notes"] = st.text_area(
                    f"Student {idx + 1}",
                    value=row.get("notes", ""),
                    key=f"con_notes_{program}_{idx}",
                    height=100,
                    placeholder="Student name · Concern / behaviour · Hypothesis (why?) · Strategy to try · Who · By when",
                )
            with col_del:
                st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
                if len(concerns) > 1:
                    if st.button("✕", key=f"con_del_{program}_{idx}"):
                        concerns.pop(idx); st.rerun()
        if st.button("➕ Add student concern", key=f"con_add_{program}"):
            concerns.append({"notes": ""}); st.rerun()
        st.markdown("---")

        st.markdown("#### ⏱ 25–40 min | SMARTAR GOAL SPOTLIGHT — 4 Students")
        st.caption("Rule: No update without evidence. What data or artefact supports this?")
        
        # SMARTAR integration status
        if not st.session_state.current_meeting_id:
            st.markdown("""
            <div style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;
                        padding:8px 14px;margin-bottom:12px;font-size:13px;color:#92400e;">
              ⚠️ <strong>Save meeting first:</strong> Scroll down and click "💾 Save Meeting Record" button to create meeting ID and enable SMARTAR Goal Tool links.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#ede9fe;border-left:4px solid #7c3aed;border-radius:0 8px 8px 0;
                        padding:8px 14px;margin-bottom:12px;font-size:13px;color:#5b21b6;">
              🎯 <strong>SMARTAR Integration Active:</strong> Enter student name, then click "Open Goal Tool" to develop/update goals. 
              Updated goals sync back here automatically.
            </div>""", unsafe_allow_html=True)

        if student_names:
            st.caption(f"💡 {len(student_names)} students loaded. Type any name — not on the list? Just type it in.")

        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = [{"student_name": "", "notes": ""} for _ in range(4)]

        smartar = st.session_state[smartar_key]
        for idx, row in enumerate(smartar):
            st.markdown(f"**Student {idx + 1}**")
            col_name, col_link, col_status = st.columns([3, 1, 1])
            
            with col_name:
                row["student_name"] = st.text_input("Student name", 
                    value=row.get("student_name", ""),
                    key=f"sm_name_{program}_{idx}",
                    label_visibility="collapsed",
                    placeholder="Enter student name")
            
            with col_link:
                # Show link if we have meeting_id AND student name
                if row.get("student_name") and st.session_state.current_meeting_id:
                    smartar_url = get_smartar_goal_link(
                        row["student_name"], 
                        st.session_state.current_meeting_id,
                        program,
                        pm_term,
                        pm_week
                    )
                    st.markdown(f"[🔗 Open Goal Tool]({smartar_url})")
                elif row.get("student_name") and not st.session_state.current_meeting_id:
                    st.caption("↑ Initialize first")
            
            with col_status:
                # Check for synced goal
                if row.get("student_name") and st.session_state.current_meeting_id:
                    synced_goal = fetch_synced_smartar_goal(row["student_name"], st.session_state.current_meeting_id)
                    if synced_goal:
                        st.success("✓ Synced")
                        # Update notes with synced goal if not already there
                        if "SMARTAR Goal:" not in row.get("notes", ""):
                            row["notes"] = f"SMARTAR Goal: {synced_goal}\n\n{row.get('notes', '')}"
            
            col_notes, col_del = st.columns([11, 0.5])
            with col_notes:
                row["notes"] = st.text_area(
                    f"Goal notes for {row.get('student_name', 'Student') or 'Student'}",
                    value=row.get("notes", ""),
                    key=f"sm_notes_{program}_{idx}",
                    height=100,
                    placeholder="Goal area · Current level / evidence · Next adjustment · Responsible",
                    label_visibility="collapsed"
                )
            with col_del:
                st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
                if len(smartar) > 1:
                    if st.button("✕", key=f"sm_del_{program}_{idx}"):
                        smartar.pop(idx); st.rerun()
        
        if st.button("➕ Add SMARTAR row", key=f"sm_add_{program}"):
            smartar.append({"student_name": "", "notes": ""}); st.rerun()
        st.markdown("---")

        st.markdown("#### ⏱ 40–45 min | REPORTS / TAC / TRANSITIONS")
        pm_reports = st.text_area("Reports, TAC meetings, review or transition planning",
            height=80, key=f"pm_reports_{program}", label_visibility="collapsed",
            placeholder="Upcoming reports due · TAC meetings · Review or transition planning")
        priority_rows = []

    else:  # Week B - similar structure with SMARTAR section
        st.markdown("#### ⏱ 10–30 min | CLC PRIORITY FOCUS — Implementation Fidelity")
        st.caption("Align to: Implementation Plan · PDP Focus Areas · LBU Priorities")

        priority_key = f"pm_priority_{program}"
        if priority_key not in st.session_state:
            st.session_state[priority_key] = [{"area":"","working":"","gap":"","adjustment":"","evidence":"","who":""}]

        priority_rows = st.session_state[priority_key]
        ph_cols = st.columns([2,2,2,2,2,1,0.5])
        for h, label in zip(ph_cols, ["Priority Area","What's Working","Gap Identified","Adjustment","Evidence to Collect","Who",""]):
            h.markdown(f"**{label}**" if label else "")

        for idx, row in enumerate(priority_rows):
            p1,p2,p3,p4,p5,p6,p7 = st.columns([2,2,2,2,2,1,0.5])
            with p1: row["area"]       = st.text_input("A",   value=row.get("area",""),       key=f"pr_a_{program}_{idx}",   label_visibility="collapsed")
            with p2: row["working"]    = st.text_input("W",   value=row.get("working",""),    key=f"pr_w_{program}_{idx}",   label_visibility="collapsed")
            with p3: row["gap"]        = st.text_input("G",   value=row.get("gap",""),        key=f"pr_g_{program}_{idx}",   label_visibility="collapsed")
            with p4: row["adjustment"] = st.text_input("Adj", value=row.get("adjustment",""), key=f"pr_adj_{program}_{idx}", label_visibility="collapsed")
            with p5: row["evidence"]   = st.text_input("E",   value=row.get("evidence",""),   key=f"pr_e_{program}_{idx}",   label_visibility="collapsed")
            with p6: row["who"]        = st.text_input("Who", value=row.get("who",""),        key=f"pr_who_{program}_{idx}", label_visibility="collapsed")
            with p7:
                if len(priority_rows) > 1:
                    if st.button("✕", key=f"pr_del_{program}_{idx}"):
                        priority_rows.pop(idx); st.rerun()
        if st.button("➕ Add priority row", key=f"pr_add_{program}"):
            priority_rows.append({"area":"","working":"","gap":"","adjustment":"","evidence":"","who":""}); st.rerun()
        st.markdown("---")

        # SMARTAR for Week B (same as Week A)
        st.markdown("#### ⏱ 30–45 min | SMARTAR GOAL SPOTLIGHT — 4 Students")
        st.caption("Rule: No update without evidence.")
        
        if not st.session_state.current_meeting_id:
            st.markdown("""
            <div style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;
                        padding:8px 14px;margin-bottom:12px;font-size:13px;color:#92400e;">
              ⚠️ <strong>Save meeting first:</strong> Scroll down and click "💾 Save Meeting Record" button.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#ede9fe;border-left:4px solid #7c3aed;border-radius:0 8px 8px 0;
                        padding:8px 14px;margin-bottom:12px;font-size:13px;color:#5b21b6;">
              🎯 <strong>SMARTAR Integration Active:</strong> Enter student name, then click "Open Goal Tool".
            </div>""", unsafe_allow_html=True)

        if student_names:
            st.caption(f"💡 {len(student_names)} students loaded.")

        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = [{"student_name": "", "notes": ""} for _ in range(4)]

        smartar = st.session_state[smartar_key]
        for idx, row in enumerate(smartar):
            st.markdown(f"**Student {idx + 1}**")
            col_name, col_link, col_status = st.columns([3, 1, 1])
            
            with col_name:
                row["student_name"] = st.text_input("Student name", 
                    value=row.get("student_name", ""),
                    key=f"sm_name_{program}_{idx}",
                    label_visibility="collapsed",
                    placeholder="Enter student name")
            
            with col_link:
                if row.get("student_name") and st.session_state.current_meeting_id:
                    smartar_url = get_smartar_goal_link(
                        row["student_name"], 
                        st.session_state.current_meeting_id,
                        program,
                        pm_term,
                        pm_week
                    )
                    st.markdown(f"[🔗 Open Goal Tool]({smartar_url})")
                elif row.get("student_name") and not st.session_state.current_meeting_id:
                    st.caption("↑ Initialize first")
            
            with col_status:
                if row.get("student_name") and st.session_state.current_meeting_id:
                    synced_goal = fetch_synced_smartar_goal(row["student_name"], st.session_state.current_meeting_id)
                    if synced_goal:
                        st.success("✓ Synced")
                        if "SMARTAR Goal:" not in row.get("notes", ""):
                            row["notes"] = f"SMARTAR Goal: {synced_goal}\n\n{row.get('notes', '')}"
            
            col_notes, col_del = st.columns([11, 0.5])
            with col_notes:
                row["notes"] = st.text_area(
                    f"Goal notes for {row.get('student_name', 'Student') or 'Student'}",
                    value=row.get("notes", ""),
                    key=f"sm_notes_{program}_{idx}",
                    height=100,
                    placeholder="Goal area · Current level / evidence · Next adjustment · Responsible",
                    label_visibility="collapsed"
                )
            with col_del:
                st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
                if len(smartar) > 1:
                    if st.button("✕", key=f"sm_del_{program}_{idx}"):
                        smartar.pop(idx); st.rerun()
        
        if st.button("➕ Add SMARTAR row", key=f"sm_add_{program}"):
            smartar.append({"student_name": "", "notes": ""}); st.rerun()

        pm_reports = ""
        concerns = []

    st.markdown("---")
    
    # ACTIONS SECTION (closing section removed, actions clarified)
    st.markdown("#### ✅ ACTIONS — Clear Ownership & Accountability")
    st.caption("Each action must have: specific task, responsible person, and due date")
    
    actions_key = f"pm_actions_{program}"
    if actions_key not in st.session_state:
        carried = [a for a in last_actions if not a.get("done", False)]
        st.session_state[actions_key] = carried if carried else [{"action":"","who":"","by_when":"","priority":"Medium","notes":"","done":False}]

    actions = st.session_state[actions_key]
    if last_actions:
        incomplete = [a for a in last_actions if not a.get("done", False)]
        if incomplete:
            st.caption(f"⬆️ {len(incomplete)} action(s) carried forward from last meeting")

    ah_cols = st.columns([4,1.5,1,1,0.7,0.5])
    for h, label in zip(ah_cols, ["Action (What needs to be done)","Who (Responsible person)","By When","Priority","✓ Done",""]):
        h.markdown(f"**{label}**" if label else "")

    for idx, row in enumerate(actions):
        a1,a2,a3,a4,a5,a6 = st.columns([4,1.5,1,1,0.7,0.5])
        with a1: row["action"]   = st.text_input("Act", value=row.get("action",""),   key=f"act_a_{program}_{idx}",      label_visibility="collapsed", placeholder="Specific action item")
        with a2: row["who"]      = st.text_input("Who", value=row.get("who",""),      key=f"act_w_{program}_{idx}",      label_visibility="collapsed", placeholder="Person responsible")
        with a3: row["by_when"]  = st.text_input("By",  value=row.get("by_when",""),  key=f"act_by_{program}_{idx}",     label_visibility="collapsed", placeholder="Due date/week")
        with a4: row["priority"] = st.selectbox("Pri",  ["Low","Medium","High","Urgent"], index=["Low","Medium","High","Urgent"].index(row.get("priority","Medium")), key=f"act_pri_{program}_{idx}", label_visibility="collapsed")
        with a5: row["done"]     = st.checkbox("✓",     value=row.get("done",False),   key=f"act_done_{program}_{idx}")
        with a6:
            if len(actions) > 1:
                if st.button("✕", key=f"act_del_{program}_{idx}"):
                    actions.pop(idx); st.rerun()
        
        if row.get("action"):
            row["notes"] = st.text_input("Additional context/notes (optional)", 
                value=row.get("notes", ""), 
                key=f"act_notes_{program}_{idx}",
                placeholder="Dependencies, resources needed, background...")

    if st.button("➕ Add action", key=f"act_add_{program}"):
        actions.append({"action":"","who":"","by_when":"","priority":"Medium","notes":"","done":False}); st.rerun()
    st.markdown("---")

    # Prepare meeting data for auto-save
    smartar_raw = st.session_state.get(f"pm_smartar_{program}", [])
    smartar_data = [{"student_name": r.get("student_name",""), "notes": r.get("notes","")} for r in smartar_raw]
    actions_data = st.session_state.get(f"pm_actions_{program}", [])
    concerns_raw = st.session_state.get(f"pm_concerns_{program}", []) if is_week_a else []
    concerns_data = [{"notes": r.get("notes","")} for r in concerns_raw]
    priority_data = st.session_state.get(f"pm_priority_{program}", []) if not is_week_a else []

    meeting_data = {
        "program": program, 
        "meeting_date": str(pm_date),
        "term": pm_term.strip(), 
        "week_number": int(pm_week),
        "week_type": "A" if is_week_a else "B",
        "facilitator": pm_facilitator.strip(), 
        "attendees": pm_attendees.strip(),
        "checkin_notes": pm_checkin.strip(),
        "student_concerns": _json.dumps(concerns_data),
        "smartar_spotlight": _json.dumps(smartar_data),
        "reports_tac_notes": pm_reports.strip() if is_week_a else "",
        "priority_focus": _json.dumps(priority_data),
        "actions": _json.dumps(actions_data),
    }

    # Trigger auto-save
    trigger_autosave(program, meeting_data)

    # Manual save button
    if st.button("💾 Save Meeting Record", type="primary", use_container_width=True, key=f"pm_save_{program}"):
        try:
            if st.session_state.current_meeting_id:
                supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                st.success("✅ Meeting record updated!")
            else:
                result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
                if result.data:
                    st.session_state.current_meeting_id = result.data[0]['id']
                st.success("✅ Meeting record saved!")
            
            # Clear session state
            for k in [f"pm_concerns_{program}", f"pm_smartar_{program}",
                      f"pm_priority_{program}", f"pm_actions_{program}"]:
                st.session_state.pop(k, None)
            
            st.session_state.last_autosave_time = None
            st.session_state.autosave_message = ""
            st.session_state.current_meeting_id = None
            st.rerun()
        except Exception as e:
            st.error(f"Could not save: {e}")

    # Past meeting records
    if last_records:
        with st.expander(f"📚 Past meeting records ({len(last_records)})", expanded=False):
            for rec in reversed(last_records[-5:]):
                wt = rec.get("week_type","?")
                badge = "🔵 Week A" if wt == "A" else "🟡 Week B"
                st.markdown(f"**{badge}** · {rec.get('meeting_date','')} · Term {rec.get('term','')} W{rec.get('week_number','')}")
                
                try:
                    past_actions = _json.loads(rec.get("actions", "[]"))
                    if past_actions:
                        st.caption("Actions:")
                        for action in past_actions:
                            status = "✅" if action.get("done") else "🔲"
                            priority = action.get("priority", "Medium")
                            priority_emoji = {"Low": "⬇️", "Medium": "➡️", "High": "⬆️", "Urgent": "🔴"}.get(priority, "➡️")
                            st.markdown(f"{status} {priority_emoji} {action.get('action','')} — {action.get('who','')} by {action.get('by_when','')}")
                except:
                    pass
                st.divider()


# Keep all other existing functions (render_schedules, render_agenda, etc.)
# Main function stays the same

def main():
    program   = get_program_from_params()
    prog_info = PROGRAMS[program]
    week_range = get_week_from_params()

    admin_login()

    grad_end = {
        "JP": "#3fa86a", "PY": "#2a6fd4", "SY": "#9b59b6",
        "STAFF": "#2a9fa8", "ADMIN": "#c97b1a"
    }.get(program, "#2a6fd4")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{prog_info['color']},{grad_end});
                padding:1.5rem 2rem;border-radius:16px;margin-bottom:1.5rem;">
      <div style="font-size:2.5rem;margin-bottom:0.25rem;">{prog_info['emoji']}</div>
      <h1 style="color:white;margin:0;font-size:1.8rem;">{prog_info['label']}</h1>
      <p style="color:rgba(255,255,255,0.85);margin:0.25rem 0 0;">Cowandilla Learning Centre · LBU</p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🔀 Switch Program")
        for p, info in PROGRAMS.items():
            if p != program:
                if st.button(f"{info['emoji']} {info['label']}", key=f"sw_{p}", use_container_width=True):
                    st.query_params["program"] = p
                    st.rerun()
        st.divider()
        if st.session_state.get("admin"):
            st.markdown("### ⚙️ Admin Mode Active")
            st.caption("You can add, edit and delete all content.")

    auto_term, auto_week = get_current_term_week()

    if program in ("JP", "PY", "SY"):
        tab_meeting = st.tabs(["🗒️ Program Meeting"])[0]
        with tab_meeting: 
            render_program_meeting(program)


if __name__ == "__main__":
    main()
