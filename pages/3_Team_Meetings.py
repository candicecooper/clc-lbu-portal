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
# Team Meetings uses the MEETINGS database (cmqyrfekxgjdtuloseri project)
SUPABASE_URL = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY_MEETINGS", st.secrets["SUPABASE_KEY"])
# Use service_role key to bypass RLS (this is an internal staff tool)
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY_MEETINGS", SUPABASE_KEY)
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "CLC2026admin")
GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

# Create Supabase client with service_role key to avoid RLS issues
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── Programs ──────────────────────────────────────────────────────────────────
PROGRAMS = {
    "JP":         {"label": "Junior Primary",     "color": "#2d7d4f", "light": "#d1fae5", "emoji": "🟢"},
    "PY":         {"label": "Primary Years",      "color": "#1a4d8c", "light": "#dbeafe", "emoji": "🔵"},
    "SY":         {"label": "Senior Years",       "color": "#7c3aed", "light": "#ede9fe", "emoji": "🟣"},
    "SPECIALIST": {"label": "Specialist Program", "color": "#d97706", "light": "#fef3c7", "emoji": "🎨"},
    "STAFF":      {"label": "STAFF Meetings",     "color": "#0891b2", "light": "#cffafe", "emoji": "👥"},
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

# ── Auto-initialization & Auto-save helpers ───────────────────────────────────
def auto_initialize_meeting(program, meeting_data):
    """Create meeting ID immediately if it doesn't exist and there's any content."""
    if st.session_state.current_meeting_id:
        return True  # Already initialized
    
    # Check if there's ANY content worth initializing for
    has_any_content = any([
        meeting_data.get("meeting_date"),
        meeting_data.get("facilitator"),
        meeting_data.get("attendees"),
        meeting_data.get("checkin_notes"),
        meeting_data.get("student_concerns"),
        meeting_data.get("smartar_spotlight"),
        meeting_data.get("actions")
    ])
    
    if has_any_content:
        try:
            # Create minimal meeting record to get ID
            result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
            if result.data:
                st.session_state.current_meeting_id = result.data[0]['id']
                st.session_state.autosave_message = f"✅ Meeting initialized (ID: {st.session_state.current_meeting_id}) - SMARTAR links now active!"
                return True
        except Exception as e:
            # If DB save fails, create temporary ID so SMARTAR links work
            import random
            st.session_state.current_meeting_id = f"temp_{random.randint(100000, 999999)}"
            st.session_state.autosave_message = f"⚠️ Temp ID created for SMARTAR - save manually to persist data"
            return False
    
    return False

def trigger_autosave(program, meeting_data):
    """Trigger auto-save if 2 minutes have passed since last save."""
    current_time = time.time()
    
    # First, ensure meeting is initialized
    auto_initialize_meeting(program, meeting_data)
    
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
        
        if has_content and st.session_state.current_meeting_id:
            try:
                # Always update (never insert here - initialization handles that)
                if not str(st.session_state.current_meeting_id).startswith("temp_"):
                    supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                    st.session_state.last_autosave_time = current_time
                    st.session_state.autosave_message = f"✓ Auto-saved at {datetime.datetime.now().strftime('%I:%M %p')}"
                    return True
            except Exception as e:
                st.session_state.autosave_message = f"⚠ Auto-save failed - save manually"
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
# WORD DOCUMENT HELPERS (keeping existing - truncated for brevity)
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

# ─────────────────────────────────────────────────────────────────────────────
# SPECIALIST PROGRAM MEETING (single template - not Week A/B)
# ─────────────────────────────────────────────────────────────────────────────

def render_specialist_meeting():
    """Specialist Program Meeting — Job Share Coordination, Curriculum, Budget, Artifacts"""
    import json as _json
    
    program = "SPECIALIST"
    accent = PROGRAMS[program]["color"]

    # Auto-save status display
    if st.session_state.autosave_message:
        st.caption(st.session_state.autosave_message)

    # Fetch past meetings for Specialist
    past_meetings = fetch("tm_program_meetings", {"program": "SPECIALIST"}, "meeting_date")
    
    # Meeting selection - New or Edit existing
    st.markdown("#### 📂 Select Meeting")
    meeting_options = ["➕ New Meeting"] + [
        f"{rec.get('meeting_date','')} - Term {rec.get('term','')} W{rec.get('week_number','')}"
        for rec in reversed(past_meetings[-20:])  # Show last 20 meetings
    ]
    
    selected_meeting = st.selectbox(
        "Choose a meeting to edit or create new",
        options=meeting_options,
        key="meeting_select_specialist"
    )
    
    # Load existing meeting if selected
    selected_record = None
    if selected_meeting != "➕ New Meeting":
        # Find the selected record
        selected_idx = meeting_options.index(selected_meeting) - 1
        selected_record = list(reversed(past_meetings[-20:]))[selected_idx]
        
        # Set current_meeting_id so it updates instead of creating new
        if not st.session_state.current_meeting_id or st.session_state.current_meeting_id != selected_record['id']:
            st.session_state.current_meeting_id = selected_record['id']
            
            # Load data into session state
            try:
                if selected_record.get('student_concerns'):
                    concerns_data = _json.loads(selected_record['student_concerns'])
                    if isinstance(concerns_data, dict) and 'concerns' in concerns_data:
                        st.session_state["sp_concerns"] = concerns_data['concerns']
                if selected_record.get('curriculum_coverage'):
                    curriculum_data = _json.loads(selected_record['curriculum_coverage'])
                    if isinstance(curriculum_data, dict) and 'modules' in curriculum_data:
                        st.session_state["sp_curriculum"] = curriculum_data['modules']
                if selected_record.get('actions'):
                    st.session_state["sp_actions"] = _json.loads(selected_record['actions'])
            except:
                pass
        
        st.info(f"✏️ Editing existing meeting - Meeting ID: {selected_record['id']}")
        
        # Show saved minutes in an expander for reference
        if selected_record.get('meeting_minutes'):
            with st.expander("📄 View Saved Minutes from This Meeting", expanded=False):
                st.markdown(selected_record['meeting_minutes'])
    else:
        # Clear meeting_id for new meeting
        if selected_meeting == "➕ New Meeting" and st.session_state.current_meeting_id:
            st.session_state.current_meeting_id = None
            # Clear session state
            for k in ["sp_concerns", "sp_curriculum", "sp_actions"]:
                st.session_state.pop(k, None)
    
    st.markdown("---")

    st.markdown(f"""<div style="background:#fef3c7;border-left:5px solid #d97706;
        border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#92400e;">
        🎨 <strong>SPECIALIST PROGRAM MEETING</strong> · Job Share Coordination · Curriculum Delivery · Budget & Foodbank · Student Artifacts
    </div>""", unsafe_allow_html=True)

    if not st.session_state.current_meeting_id:
        st.markdown("""
        <div style="background:#e0f2fe;border-left:4px solid #0284c7;border-radius:0 8px 8px 0;
                    padding:8px 14px;margin-bottom:12px;font-size:13px;color:#075985;">
          ℹ️ <strong>New Meeting:</strong> Meeting ID will be created automatically when you start entering content.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"✅ Meeting Active (ID: {st.session_state.current_meeting_id})")

    st.markdown("#### 📋 Meeting Details")
    mc1, mc2, mc3, mc4 = st.columns(4)
    
    # Pre-populate with existing data if editing
    default_date = datetime.date.fromisoformat(selected_record['meeting_date']) if selected_record else datetime.date.today()
    default_term = selected_record.get('term', '') if selected_record else ''
    default_week = selected_record.get('week_number', 1) if selected_record else 1
    default_facilitator = selected_record.get('facilitator', get_staff_name()) if selected_record else get_staff_name()
    default_attendees = selected_record.get('attendees', '') if selected_record else ''
    
    # Get check-in notes if editing
    default_monday_notes = ""
    default_tuefri_notes = ""
    if selected_record and selected_record.get('checkin_notes'):
        try:
            checkin_data = _json.loads(selected_record['checkin_notes'])
            default_monday_notes = checkin_data.get('monday_teacher', '')
            default_tuefri_notes = checkin_data.get('tuefri_teacher', '')
        except:
            pass
    
    with mc1: sp_date        = st.date_input("Date", value=default_date, key="sp_date")
    with mc2: sp_term        = st.text_input("Term", value=default_term, placeholder="T1", key="sp_term")
    with mc3: sp_week        = st.number_input("Week #", min_value=1, max_value=11, value=default_week, key="sp_week")
    with mc4: sp_facilitator = st.text_input("Facilitator", value=default_facilitator, key="sp_fac")
    sp_attendees = st.text_input("Attendees (Both job share teachers + others)", value=default_attendees, placeholder="Names separated by commas", key="sp_att")

    st.markdown("---")

    # ── SECTION 1: Team Check-in ──
    st.markdown("#### ⏱ 0–10 min | TEAM CHECK-IN & HANDOVER")
    st.caption("Quick updates from both job share teachers. Any handover issues from previous week?")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Monday Teacher (0.2):**")
        sp_monday_notes = st.text_area(
            "Monday teacher notes",
            value=default_monday_notes,
            height=100,
            key="sp_monday_notes",
            placeholder="How did Monday sessions go? Kitchen/BSEM notes? Concerns for week ahead?",
            label_visibility="collapsed"
        )
    with col2:
        st.markdown("**Tuesday–Friday Teacher (0.8):**")
        sp_tuefri_notes = st.text_area(
            "Tue-Fri teacher notes",
            value=default_tuefri_notes,
            height=100,
            key="sp_tuefri_notes",
            placeholder="How was curriculum delivery this week? Student engagement? Handover working?",
            label_visibility="collapsed"
        )
    
    st.markdown("---")

    # ── SECTION 2: Student & Program Concerns ──
    st.markdown("#### ⏱ 10–25 min | STUDENT & PROGRAM CONCERNS")
    st.caption("Flag students needing additional support or program adjustments")

    concerns_key = "sp_concerns"
    if concerns_key not in st.session_state:
        st.session_state[concerns_key] = [{"concern":"","strategy":"","adjustment":"","who":"","timeline":""}]

    concerns = st.session_state[concerns_key]
    ch_cols = st.columns([2.5,2,2,1,1,0.5])
    for h, label in zip(ch_cols, ["Student / Group | Concern","Current Strategy","Adjustment Needed","Who","Timeline",""]):
        h.markdown(f"**{label}**" if label else "")

    for idx, row in enumerate(concerns):
        c1,c2,c3,c4,c5,c6 = st.columns([2.5,2,2,1,1,0.5])
        with c1: row["concern"]    = st.text_input("Con", value=row.get("concern",""),    key=f"spc_con_{idx}",    label_visibility="collapsed", placeholder="Student name · Concern / context")
        with c2: row["strategy"]   = st.text_input("Str", value=row.get("strategy",""),   key=f"spc_str_{idx}",    label_visibility="collapsed", placeholder="Current strategy")
        with c3: row["adjustment"] = st.text_input("Adj", value=row.get("adjustment",""), key=f"spc_adj_{idx}",    label_visibility="collapsed", placeholder="What needs to change")
        with c4: row["who"]        = st.text_input("Who", value=row.get("who",""),        key=f"spc_who_{idx}",    label_visibility="collapsed", placeholder="Person")
        with c5: row["timeline"]   = st.text_input("By",  value=row.get("timeline",""),   key=f"spc_time_{idx}",   label_visibility="collapsed", placeholder="When")
        with c6:
            if len(concerns) > 1:
                if st.button("✕", key=f"spc_del_{idx}"):
                    concerns.pop(idx); st.rerun()
    
    if st.button("➕ Add concern", key="spc_add"):
        concerns.append({"concern":"","strategy":"","adjustment":"","who":"","timeline":""}); st.rerun()

    st.markdown("**Program-level concerns:**")
    sp_program_concerns = st.text_area(
        "Program concerns",
        height=80,
        key="sp_prog_concerns",
        placeholder="NIT release coverage? Timetable changes? Cross-program coordination? Safety/BSP updates?",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # ── SECTION 3: Curriculum Coverage ──
    st.markdown("#### ⏱ 25–35 min | CURRICULUM COVERAGE CHECK-IN")
    st.caption("Track progress, student engagement, and needed adjustments across all modules")

    curriculum_key = "sp_curriculum"
    if curriculum_key not in st.session_state:
        st.session_state[curriculum_key] = [
            {"module": "Cooking (all programs)", "progress": "", "engagement": "", "adjustments": "", "resources": ""},
            {"module": "BSEM Stamina & Character Strengths", "progress": "", "engagement": "", "adjustments": "", "resources": ""},
            {"module": "Child Protection — Right to be Safe", "progress": "", "engagement": "", "adjustments": "", "resources": ""},
            {"module": "5 is Against the Law", "progress": "", "engagement": "", "adjustments": "", "resources": ""},
            {"module": "Sexual Health Ed (SY only — Elephant Ed)", "progress": "", "engagement": "", "adjustments": "", "resources": ""},
        ]

    curriculum = st.session_state[curriculum_key]
    cur_cols = st.columns([2,2,2,2,2])
    for h, label in zip(cur_cols, ["Module / Area","Progress This Week","Student Engagement","Adjustments Needed","Resources / Support"]):
        h.markdown(f"**{label}**")

    for idx, row in enumerate(curriculum):
        cu1,cu2,cu3,cu4,cu5 = st.columns([2,2,2,2,2])
        with cu1: st.markdown(f"`{row['module']}`")
        with cu2: row["progress"]    = st.text_input("Prog",  value=row.get("progress",""),    key=f"cur_prog_{idx}",  label_visibility="collapsed", placeholder="What was covered")
        with cu3: row["engagement"]  = st.text_input("Eng",   value=row.get("engagement",""),  key=f"cur_eng_{idx}",   label_visibility="collapsed", placeholder="Student response")
        with cu4: row["adjustments"] = st.text_input("Adj",   value=row.get("adjustments",""), key=f"cur_adj_{idx}",   label_visibility="collapsed", placeholder="Changes needed")
        with cu5: row["resources"]   = st.text_input("Res",   value=row.get("resources",""),   key=f"cur_res_{idx}",   label_visibility="collapsed", placeholder="What's needed")

    st.markdown("**Coverage gaps or concerns:**")
    sp_coverage_gaps = st.text_area(
        "Coverage gaps",
        height=80,
        key="sp_coverage_gaps",
        placeholder="Students missing key curriculum? Pacing issues? Equity concerns across JP/PY/SY?",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # ── SECTION 4: Budget & Foodbank ──
    st.markdown("#### ⏱ 35–40 min | BUDGET & FOODBANK UPDATE")

    col_fb1, col_fb2, col_fb3 = st.columns(3)
    with col_fb1:
        sp_foodbank_submitted = st.selectbox("Foodbank order submitted this fortnight?", ["Not due", "Yes", "No"], key="sp_fb_submitted")
    with col_fb2:
        sp_stock_ok = st.selectbox("Stock levels OK for next week?", ["Yes", "No — gaps identified"], key="sp_stock")
    with col_fb3:
        sp_ingredient_gaps = st.text_input("Ingredient gaps/substitutions needed", key="sp_gaps", placeholder="List any gaps")

    st.markdown("**Cooking Budget Tracking:**")
    budget_cols = st.columns([2,2,2,4])
    with budget_cols[0]: st.markdown("**Program**")
    with budget_cols[1]: st.markdown("**Spent to Date**")
    with budget_cols[2]: st.markdown("**Remaining**")
    with budget_cols[3]: st.markdown("**Notes / Adjustments**")

    for prog_name in ["JP", "PY", "SY"]:
        bc1, bc2, bc3, bc4 = st.columns([2,2,2,4])
        with bc1: st.markdown(f"`{prog_name}`")
        with bc2: st.text_input(f"Spent {prog_name}", key=f"budget_spent_{prog_name}", label_visibility="collapsed", placeholder="$")
        with bc3: st.text_input(f"Remain {prog_name}", key=f"budget_remain_{prog_name}", label_visibility="collapsed", placeholder="$")
        with bc4: st.text_input(f"Notes {prog_name}", key=f"budget_notes_{prog_name}", label_visibility="collapsed", placeholder="Any concerns or adjustments")

    sp_budget_concerns = st.text_area(
        "Budget concerns",
        height=60,
        key="sp_budget_concerns",
        placeholder="Equitable spending? Specialist equipment needed? Budget adjustment for term remainder?",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # ── SECTION 5: Artifact Check-In ──
    st.markdown("#### ⏱ 40–45 min | ARTIFACT CHECK-IN")
    st.caption("Student reporting artifacts for end-of-placement reports — tracked by program")

    for prog_name, prog_label in [("JP", "JUNIOR PRIMARY"), ("PY", "PRIMARY YEARS"), ("SY", "SENIOR YEARS")]:
        st.markdown(f"**{prog_label} ({prog_name})**")
        
        modules = ["Cooking", "BSEM", "Child Protection", "5 is Against the Law"]
        if prog_name == "SY":
            modules.append("Sexual Health Ed (Elephant Ed)")
        
        art_cols = st.columns([2,2,2,3])
        with art_cols[0]: st.markdown("**Module**")
        with art_cols[1]: st.markdown("**Status**")
        with art_cols[2]: st.markdown("**Timeline**")
        with art_cols[3]: st.markdown("**Support Needed**")

        for module in modules:
            a1,a2,a3,a4 = st.columns([2,2,2,3])
            with a1: st.markdown(f"`{module}`")
            with a2: st.selectbox(f"Status {prog_name} {module}", ["Not Started", "In Progress", "Complete"], key=f"art_status_{prog_name}_{module}", label_visibility="collapsed")
            with a3: st.text_input(f"Timeline {prog_name} {module}", key=f"art_timeline_{prog_name}_{module}", label_visibility="collapsed", placeholder="Due date")
            with a4: st.text_input(f"Support {prog_name} {module}", key=f"art_support_{prog_name}_{module}", label_visibility="collapsed", placeholder="What's needed")
        
        st.markdown("")  # Spacing between programs

    st.markdown("**Cross-program reporting concerns:**")
    sp_artifact_concerns = st.text_area(
        "Artifact concerns",
        height=60,
        key="sp_artifact_concerns",
        placeholder="Programs ahead/behind? Deadline alignment? Support needed from program teachers?",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # ── SECTION 6: Actions ──
    st.markdown("#### ✅ ACTIONS — Clear Ownership & Accountability")
    st.caption("Each action must have: specific task, responsible person, and due date")

    actions_key = "sp_actions"
    if actions_key not in st.session_state:
        st.session_state[actions_key] = [{"action":"","who":"","by_when":"","priority":"Medium","done":False}]

    actions = st.session_state[actions_key]
    ah_cols = st.columns([4,1.5,1,1,0.7,0.5])
    for h, label in zip(ah_cols, ["Action","Who","By When","Priority","✓ Done",""]):
        h.markdown(f"**{label}**" if label else "")

    for idx, row in enumerate(actions):
        a1,a2,a3,a4,a5,a6 = st.columns([4,1.5,1,1,0.7,0.5])
        with a1: row["action"]   = st.text_input("Act", value=row.get("action",""),   key=f"spa_a_{idx}",    label_visibility="collapsed", placeholder="Specific action")
        with a2: row["who"]      = st.text_input("Who", value=row.get("who",""),      key=f"spa_w_{idx}",    label_visibility="collapsed", placeholder="Person")
        with a3: row["by_when"]  = st.text_input("By",  value=row.get("by_when",""),  key=f"spa_by_{idx}",   label_visibility="collapsed", placeholder="When")
        with a4: row["priority"] = st.selectbox("Pri",  ["Low","Medium","High","Urgent"], index=["Low","Medium","High","Urgent"].index(row.get("priority","Medium")), key=f"spa_pri_{idx}", label_visibility="collapsed")
        with a5: row["done"]     = st.checkbox("✓",     value=row.get("done",False),   key=f"spa_done_{idx}")
        with a6:
            if len(actions) > 1:
                if st.button("✕", key=f"spa_del_{idx}"):
                    actions.pop(idx); st.rerun()

    if st.button("➕ Add action", key="spa_add"):
        actions.append({"action":"","who":"","by_when":"","priority":"Medium","done":False}); st.rerun()

    st.markdown("---")
    
    # MEETING MINUTES / NOTES SECTION
    st.markdown("#### 📝 MEETING MINUTES / NOTES")
    st.caption("Comprehensive meeting notes - discussions, decisions, key points raised")
    
    default_sp_minutes = ""
    if selected_record and selected_record.get('meeting_minutes'):
        default_sp_minutes = selected_record['meeting_minutes']
    
    sp_minutes = st.text_area(
        "Meeting minutes",
        value=default_sp_minutes,
        height=200,
        key="sp_minutes",
        label_visibility="collapsed",
        placeholder="Record comprehensive meeting minutes here - discussions, decisions, key points, follow-up items..."
    )

    st.markdown("---")

    # Prepare meeting data - FIXED: Use local variables instead of session state
    concerns_data = concerns  # Use local variable
    curriculum_data = curriculum  # Use local variable
    actions_data = actions  # Use local variable
    
    # Collect budget data
    budget_data = {}
    for prog_name in ["JP", "PY", "SY"]:
        budget_data[prog_name] = {
            "spent": st.session_state.get(f"budget_spent_{prog_name}", ""),
            "remaining": st.session_state.get(f"budget_remain_{prog_name}", ""),
            "notes": st.session_state.get(f"budget_notes_{prog_name}", "")
        }
    
    # Collect artifact data
    artifact_data = {}
    for prog_name in ["JP", "PY", "SY"]:
        modules = ["Cooking", "BSEM", "Child Protection", "5 is Against the Law"]
        if prog_name == "SY":
            modules.append("Sexual Health Ed (Elephant Ed)")
        artifact_data[prog_name] = {}
        for module in modules:
            artifact_data[prog_name][module] = {
                "status": st.session_state.get(f"art_status_{prog_name}_{module}", "Not Started"),
                "timeline": st.session_state.get(f"art_timeline_{prog_name}_{module}", ""),
                "support": st.session_state.get(f"art_support_{prog_name}_{module}", "")
            }

    meeting_data = {
        "program": "SPECIALIST",
        "meeting_date": str(sp_date),
        "term": sp_term.strip(),
        "week_number": int(sp_week),
        "week_type": "SPECIALIST",  # No A/B for specialist
        "facilitator": sp_facilitator.strip(),
        "attendees": sp_attendees.strip(),
        "checkin_notes": _json.dumps({
            "monday_teacher": sp_monday_notes,
            "tuefri_teacher": sp_tuefri_notes
        }),
        "student_concerns": _json.dumps({
            "concerns": concerns_data,
            "program_concerns": sp_program_concerns
        }),
        "curriculum_coverage": _json.dumps({
            "modules": curriculum_data,
            "coverage_gaps": sp_coverage_gaps
        }),
        "budget_foodbank": _json.dumps({
            "foodbank_submitted": sp_foodbank_submitted,
            "stock_ok": sp_stock_ok,
            "ingredient_gaps": sp_ingredient_gaps,
            "budget": budget_data,
            "concerns": sp_budget_concerns
        }),
        "artifacts": _json.dumps({
            "artifact_data": artifact_data,
            "concerns": sp_artifact_concerns
        }),
        "meeting_minutes": sp_minutes.strip(),
        "actions": _json.dumps(actions_data),
    }

    # Trigger auto-save/auto-initialization
    trigger_autosave("SPECIALIST", meeting_data)

    # Manual save button
    save_button_text = "💾 Update Meeting Record" if st.session_state.current_meeting_id else "💾 Save Meeting Record"
    if st.button(save_button_text, type="primary", use_container_width=True, key="sp_save"):
        try:
            if st.session_state.current_meeting_id and not str(st.session_state.current_meeting_id).startswith("temp_"):
                supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                st.success("✅ Meeting record updated!")
            else:
                result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
                if result.data:
                    st.session_state.current_meeting_id = result.data[0]['id']
                st.success("✅ Meeting record saved!")
            
            # Clear session state
            for k in ["sp_concerns", "sp_curriculum", "sp_actions"]:
                st.session_state.pop(k, None)
            
            st.session_state.last_autosave_time = None
            st.session_state.autosave_message = ""
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Database save failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAM MEETING (JP/PY/SY) - WITH SMARTAR INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def render_program_meeting(program):
    import json as _json
    prog_label = PROGRAMS[program]["label"]
    accent = PROGRAMS[program]["color"]

    # Auto-save status display
    if st.session_state.autosave_message:
        st.caption(st.session_state.autosave_message)

    # Fetch past meetings for this program
    past_meetings = fetch("tm_program_meetings", {"program": program}, "meeting_date")
    
    # Meeting selection - New or Edit existing
    st.markdown("#### 📂 Select Meeting")
    meeting_options = ["➕ New Meeting"] + [
        f"{rec.get('meeting_date','')} - Term {rec.get('term','')} W{rec.get('week_number','')} - Week {rec.get('week_type','')}"
        for rec in reversed(past_meetings[-20:])  # Show last 20 meetings
    ]
    
    selected_meeting = st.selectbox(
        "Choose a meeting to edit or create new",
        options=meeting_options,
        key=f"meeting_select_{program}"
    )
    
    # Load existing meeting if selected
    selected_record = None
    if selected_meeting != "➕ New Meeting":
        # Find the selected record
        selected_idx = meeting_options.index(selected_meeting) - 1
        selected_record = list(reversed(past_meetings[-20:]))[selected_idx]
        
        # Set current_meeting_id so it updates instead of creating new
        if not st.session_state.current_meeting_id or st.session_state.current_meeting_id != selected_record['id']:
            st.session_state.current_meeting_id = selected_record['id']
            
            # Load data into session state
            try:
                if selected_record.get('student_concerns'):
                    st.session_state[f"pm_concerns_{program}"] = _json.loads(selected_record['student_concerns'])
                if selected_record.get('smartar_spotlight'):
                    st.session_state[f"pm_smartar_{program}"] = _json.loads(selected_record['smartar_spotlight'])
                if selected_record.get('priority_focus'):
                    st.session_state[f"pm_priority_{program}"] = _json.loads(selected_record['priority_focus'])
                if selected_record.get('actions'):
                    st.session_state[f"pm_actions_{program}"] = _json.loads(selected_record['actions'])
            except:
                pass
        
        st.info(f"✏️ Editing existing meeting - Meeting ID: {selected_record['id']}")
        
        # Show saved minutes in an expander for reference
        if selected_record.get('meeting_minutes'):
            with st.expander("📄 View Saved Minutes from This Meeting", expanded=False):
                st.markdown(selected_record['meeting_minutes'])
    else:
        # Clear meeting_id for new meeting
        if selected_meeting == "➕ New Meeting" and st.session_state.current_meeting_id:
            st.session_state.current_meeting_id = None
            # Clear session state
            for k in [f"pm_concerns_{program}", f"pm_smartar_{program}",
                      f"pm_priority_{program}", f"pm_actions_{program}"]:
                st.session_state.pop(k, None)
    
    st.markdown("---")

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
    
    # Pre-populate with existing data if editing
    default_date = datetime.date.fromisoformat(selected_record['meeting_date']) if selected_record else datetime.date.today()
    default_term = selected_record.get('term', '') if selected_record else ''
    default_week = selected_record.get('week_number', 1) if selected_record else 1
    default_facilitator = selected_record.get('facilitator', get_staff_name()) if selected_record else get_staff_name()
    default_attendees = selected_record.get('attendees', '') if selected_record else ''
    default_checkin = selected_record.get('checkin_notes', '') if selected_record else ''
    default_reports = selected_record.get('reports_tac_notes', '') if selected_record else ''
    
    with mc1: pm_date        = st.date_input("Date", value=default_date, key=f"pm_date_{program}")
    with mc2: pm_term        = st.text_input("Term", value=default_term, placeholder="T1", key=f"pm_term_{program}")
    with mc3: pm_week        = st.number_input("Week #", min_value=1, max_value=11, value=default_week, key=f"pm_week_{program}")
    with mc4: pm_facilitator = st.text_input("Facilitator", value=default_facilitator, key=f"pm_fac_{program}")
    pm_attendees = st.text_input("Attendees", value=default_attendees, placeholder="Names separated by commas", key=f"pm_att_{program}")

    st.markdown("""<div style="background:#f0f9f9;border:1px solid #1A7A7A;border-radius:8px;
        padding:6px 12px;font-size:0.78rem;color:#1A7A7A;margin-bottom:8px;">
        <strong>Meeting Norms:</strong> ☑ Student-centred &nbsp;·&nbsp; ☑ Evidence before opinion
        &nbsp;·&nbsp; ☑ Clear actions + ownership &nbsp;·&nbsp; ☑ Stick to time
    </div>""", unsafe_allow_html=True)
    
    # STATUS DISPLAY - Updated messaging
    if not st.session_state.current_meeting_id:
        st.markdown("""
        <div style="background:#e0f2fe;border-left:4px solid #0284c7;border-radius:0 8px 8px 0;
                    padding:8px 14px;margin-bottom:12px;font-size:13px;color:#075985;">
          ℹ️ <strong>New Meeting:</strong> Meeting ID will be created automatically when you start entering content. 
          SMARTAR links will appear as soon as you enter a student name below.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"✅ Meeting Active (ID: {st.session_state.current_meeting_id}) - SMARTAR integration ready")
    
    st.markdown("---")

    checkin_label  = "TEAM CHECK-IN — Regulation Before Reaction" if is_week_a else "TEAM CHECK-IN"
    checkin_prompt = "What do we need to know to support students effectively today?" if is_week_a else "Quick updates impacting program delivery"
    st.markdown(f"#### ⏱ 0–10 min | {checkin_label}")
    st.caption(checkin_prompt)
    pm_checkin = st.text_area("Check-in notes", value=default_checkin, height=80, key=f"pm_checkin_{program}",
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
        st.caption("Click student name to open Goal Builder, or add new student")
        
        # Create minimal meeting record immediately if needed for SMARTAR links
        if not st.session_state.current_meeting_id:
            # Create bare minimum meeting record to get ID
            minimal_meeting = {
                "program": program,
                "meeting_date": str(pm_date),
                "term": pm_term.strip() or "T1",
                "week_number": int(pm_week),
                "week_type": "A" if is_week_a else "B",
                "facilitator": pm_facilitator.strip() or get_staff_name(),
                "attendees": "",
                "checkin_notes": "",
                "student_concerns": "[]",
                "smartar_spotlight": "[]",
                "reports_tac_notes": "",
                "priority_focus": "[]",
                "meeting_minutes": "",
                "actions": "[]",
            }
            try:
                result = supabase.table('tm_program_meetings').insert(minimal_meeting).execute()
                if result.data:
                    st.session_state.current_meeting_id = result.data[0]['id']
                    st.success(f"✅ Meeting initialized - ID: {st.session_state.current_meeting_id}")
            except Exception as e:
                st.error(f"⚠️ Could not create meeting: {e}")
                st.info("💡 You can still use SMARTAR Goal Builder - goals will sync when meeting is saved")

        if student_names:
            st.caption(f"💡 {len(student_names)} students loaded")

        # SMARTAR student selection - REDESIGNED with buttons
        st.markdown("**Select students for goal spotlight:**")
        
        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = []
        
        smartar = st.session_state[smartar_key]
        
        # Display existing students with Goal Builder buttons
        if smartar:
            for idx, student_data in enumerate(smartar):
                student_name = student_data.get("student_name", "")
                if not student_name:
                    continue
                    
                col_name, col_goal_btn, col_status, col_remove = st.columns([3, 2, 1.5, 0.5])
                
                with col_name:
                    st.markdown(f"**{idx + 1}. {student_name}**")
                
                with col_goal_btn:
                    if st.session_state.current_meeting_id:
                        smartar_url = get_smartar_goal_link(
                            student_name, 
                            st.session_state.current_meeting_id,
                            program,
                            pm_term or "T1",
                            pm_week
                        )
                        st.markdown(f"[🎯 Open Goal Builder]({smartar_url})", unsafe_allow_html=True)
                    else:
                        st.caption("Initializing...")
                
                with col_status:
                    if st.session_state.current_meeting_id:
                        synced_goal = fetch_synced_smartar_goal(student_name, st.session_state.current_meeting_id)
                        if synced_goal:
                            st.success("✓ Synced")
                            # Update notes with synced goal
                            if "SMARTAR Goal:" not in student_data.get("notes", ""):
                                student_data["notes"] = f"SMARTAR Goal: {synced_goal}\n\n{student_data.get('notes', '')}"
                        else:
                            st.info("No goal yet")
                
                with col_remove:
                    if st.button("✕", key=f"sm_remove_{program}_{idx}"):
                        smartar.pop(idx)
                        st.rerun()
                
                # Optional notes field (collapsed)
                with st.expander(f"📝 Notes for {student_name}", expanded=False):
                    student_data["notes"] = st.text_area(
                        f"Notes for {student_name}",
                        value=student_data.get("notes", ""),
                        key=f"sm_notes_{program}_{idx}",
                        height=80,
                        placeholder="Additional notes about this student's goals...",
                        label_visibility="collapsed"
                    )
        
        st.markdown("---")
        
        # Add student section - SIMPLIFIED
        st.markdown("**Add student to spotlight:**")
        
        col_select, col_add = st.columns([4, 1])
        
        with col_select:
            # Student selector with autocomplete
            new_student_name = st.selectbox(
                "Select student",
                options=[""] + student_names,
                key=f"new_student_select_{program}",
                label_visibility="collapsed"
            )
            # OR manual entry
            if not new_student_name:
                new_student_name = st.text_input(
                    "Or type student name",
                    key=f"new_student_manual_{program}",
                    placeholder="Type student name if not in list...",
                    label_visibility="collapsed"
                )
        
        with col_add:
            st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
            if st.button("➕ Add & Open Goal Builder", key=f"add_student_{program}", type="primary"):
                if new_student_name and new_student_name.strip():
                    # Add to smartar list
                    smartar.append({"student_name": new_student_name.strip(), "notes": ""})
                    
                    # Open SMARTAR Goal Builder immediately
                    if st.session_state.current_meeting_id:
                        smartar_url = get_smartar_goal_link(
                            new_student_name.strip(), 
                            st.session_state.current_meeting_id,
                            program,
                            pm_term or "T1",
                            pm_week
                        )
                        st.markdown(f"""
                        <meta http-equiv="refresh" content="0; url={smartar_url}">
                        <div style="background:#dbeafe;border-left:4px solid #0284c7;border-radius:8px;
                                    padding:12px 16px;margin:12px 0;font-size:14px;">
                          🎯 <strong>Opening SMARTAR Goal Builder for {new_student_name}...</strong><br>
                          If it doesn't open automatically, <a href="{smartar_url}" target="_blank">click here</a>
                        </div>
                        """, unsafe_allow_html=True)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("⚠️ Meeting not initialized yet - fill in meeting details first")
                else:
                    st.warning("⚠️ Please select or enter a student name")
        
        st.markdown("---")

        st.markdown("#### ⏱ 40–45 min | REPORTS / TAC / TRANSITIONS")
        pm_reports = st.text_area("Reports, TAC meetings, review or transition planning",
            value=default_reports, height=80, key=f"pm_reports_{program}", label_visibility="collapsed",
            placeholder="Upcoming reports due · TAC meetings · Review or transition planning")
        priority_rows = []

    else:  # Week B - System Lens
        st.markdown("#### ⏱ 10–30 min | CLC PRIORITY FOCUS — Implementation Fidelity")
        st.caption("Align to: Implementation Plan · PDP Focus Areas · LBU Priorities")

        priority_key = f"pm_priority_{program}"
        # Migrate legacy list format → dict with free text
        if priority_key not in st.session_state:
            # Try to load existing priority_focus from selected_record
            raw_pf = selected_record.get('priority_focus', '') if selected_record else ''
            existing_text = ""
            if raw_pf:
                try:
                    import json as _json_pf
                    pf_data = _json_pf.loads(raw_pf)
                    if isinstance(pf_data, dict):
                        existing_text = pf_data.get("notes", "")
                    elif isinstance(pf_data, list) and pf_data:
                        # Legacy row format — convert to readable text block
                        lines = []
                        for r in pf_data:
                            if isinstance(r, dict):
                                parts = [v for v in r.values() if v]
                                if parts:
                                    lines.append("• " + " | ".join(parts))
                        existing_text = "\n".join(lines)
                except Exception:
                    existing_text = str(raw_pf)
            st.session_state[priority_key] = {"notes": existing_text}

        priority_store = st.session_state[priority_key]
        if not isinstance(priority_store, dict):
            priority_store = {"notes": ""}
            st.session_state[priority_key] = priority_store

        # ── Main free-text focus area ──────────────────────────────────────
        st.markdown("**📝 Focus Area Notes**")
        st.caption("Type freely — what was the focus, what's working, gaps, adjustments, who owns what.")
        priority_store["notes"] = st.text_area(
            "Focus area notes",
            value=priority_store.get("notes", ""),
            height=220,
            key=f"pr_notes_{program}",
            label_visibility="collapsed",
            placeholder=(
                "e.g.\n"
                "FOCUS: Implementation fidelity — Regulate-Relate-Reason framework\n"
                "WORKING: Morning regulation check-ins consistent across SY\n"
                "GAP: Inconsistent use of Window of Tolerance language in SY afternoon sessions\n"
                "ADJUSTMENT: Candice to model WoT language in SY team meeting next week\n"
                "EVIDENCE: Student regulation data from Scatter Plot — Brenton by W7"
            )
        )

        # ── Transcript drop + Groq recalibration ──────────────────────────
        with st.expander("📋 Drop Transcript / Raw Notes → Recalibrate with AI", expanded=False):
            st.caption(
                "Paste rough notes, a voice transcript, or bullet points. "
                "Groq will reshape them into structured focus-area minutes."
            )
            transcript_raw = st.text_area(
                "Paste transcript or raw notes here",
                height=180,
                key=f"pr_transcript_{program}",
                label_visibility="collapsed",
                placeholder="Paste meeting transcript, voice-to-text, or rough dot points here..."
            )
            if st.button("✨ Recalibrate with AI", key=f"pr_groq_{program}", type="primary"):
                if transcript_raw.strip():
                    if GROQ_KEY:
                        with st.spinner("Recalibrating with Groq…"):
                            try:
                                _groq_client = Groq(api_key=GROQ_KEY)
                                _prompt = f"""You are a professional minute-taker for Cowandilla Learning Centre (CLC), Learning & Behaviour Unit — an alternative education setting in South Australia.

The following is a raw transcript or rough notes from a Week B 'System Lens' team meeting for the {PROGRAMS[program]['label']} program.

Your job: Transform these notes into clear, structured focus-area minutes. Use this format:

FOCUS AREA: [what was discussed]
WHAT'S WORKING: [strengths, positives]
GAP IDENTIFIED: [what needs attention]
ADJUSTMENT / NEXT STEP: [specific action or change]
EVIDENCE TO COLLECT: [how progress will be measured]
WHO & WHEN: [responsible person and timeline]

Rules:
- Use professional but warm, plain-English language
- Trauma-informed, strengths-based framing
- Preserve ALL factual content — do not add or fabricate
- If multiple focus areas were discussed, repeat the structure for each
- Keep it concise and actionable

Raw input:
{transcript_raw}"""
                                _resp = _groq_client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": _prompt}],
                                    max_tokens=2000
                                )
                                recalibrated = _resp.choices[0].message.content
                                # Append to existing notes or replace if empty
                                if priority_store.get("notes", "").strip():
                                    priority_store["notes"] = (
                                        priority_store["notes"].strip()
                                        + "\n\n--- AI Recalibration ---\n"
                                        + recalibrated
                                    )
                                else:
                                    priority_store["notes"] = recalibrated
                                st.session_state[priority_key] = priority_store
                                st.success("✅ Recalibrated! Review and edit above before saving.")
                                st.rerun()
                            except Exception as _e:
                                st.error(f"Groq error: {_e}")
                    else:
                        st.warning("⚠️ Groq API key not configured — cannot recalibrate.")
                else:
                    st.warning("⚠️ Paste some content first.")

        # priority_rows used downstream for save — wrap in list for compatibility
        priority_rows = [{"notes": priority_store.get("notes", "")}]
        st.markdown("---")

        # SMARTAR for Week B (same as Week A)
        st.markdown("#### ⏱ 30–45 min | SMARTAR GOAL SPOTLIGHT — 4 Students")
        st.caption("Click student name to open Goal Builder, or add new student")
        
        # Create minimal meeting record immediately if needed
        if not st.session_state.current_meeting_id:
            minimal_meeting = {
                "program": program,
                "meeting_date": str(pm_date),
                "term": pm_term.strip() or "T1",
                "week_number": int(pm_week),
                "week_type": "A" if is_week_a else "B",
                "facilitator": pm_facilitator.strip() or get_staff_name(),
                "attendees": "",
                "checkin_notes": "",
                "student_concerns": "[]",
                "smartar_spotlight": "[]",
                "reports_tac_notes": "",
                "priority_focus": "[]",
                "meeting_minutes": "",
                "actions": "[]",
            }
            try:
                result = supabase.table('tm_program_meetings').insert(minimal_meeting).execute()
                if result.data:
                    st.session_state.current_meeting_id = result.data[0]['id']
                    st.success(f"✅ Meeting initialized - ID: {st.session_state.current_meeting_id}")
            except Exception as e:
                st.error(f"⚠️ Could not create meeting: {e}")

        if student_names:
            st.caption(f"💡 {len(student_names)} students loaded")

        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = []

        smartar = st.session_state[smartar_key]
        
        # Display existing students
        if smartar:
            for idx, student_data in enumerate(smartar):
                student_name = student_data.get("student_name", "")
                if not student_name:
                    continue
                    
                col_name, col_goal_btn, col_status, col_remove = st.columns([3, 2, 1.5, 0.5])
                
                with col_name:
                    st.markdown(f"**{idx + 1}. {student_name}**")
                
                with col_goal_btn:
                    if st.session_state.current_meeting_id:
                        smartar_url = get_smartar_goal_link(
                            student_name, 
                            st.session_state.current_meeting_id,
                            program,
                            pm_term or "T1",
                            pm_week
                        )
                        st.markdown(f"[🎯 Open Goal Builder]({smartar_url})", unsafe_allow_html=True)
                    else:
                        st.caption("Initializing...")
                
                with col_status:
                    if st.session_state.current_meeting_id:
                        synced_goal = fetch_synced_smartar_goal(student_name, st.session_state.current_meeting_id)
                        if synced_goal:
                            st.success("✓ Synced")
                            if "SMARTAR Goal:" not in student_data.get("notes", ""):
                                student_data["notes"] = f"SMARTAR Goal: {synced_goal}\n\n{student_data.get('notes', '')}"
                        else:
                            st.info("No goal yet")
                
                with col_remove:
                    if st.button("✕", key=f"sm_remove_b_{program}_{idx}"):
                        smartar.pop(idx)
                        st.rerun()
                
                with st.expander(f"📝 Notes for {student_name}", expanded=False):
                    student_data["notes"] = st.text_area(
                        f"Notes for {student_name}",
                        value=student_data.get("notes", ""),
                        key=f"sm_notes_b_{program}_{idx}",
                        height=80,
                        placeholder="Additional notes about this student's goals...",
                        label_visibility="collapsed"
                    )
        
        st.markdown("---")
        
        # Add student section
        st.markdown("**Add student to spotlight:**")
        
        col_select, col_add = st.columns([4, 1])
        
        with col_select:
            new_student_name = st.selectbox(
                "Select student",
                options=[""] + student_names,
                key=f"new_student_select_b_{program}",
                label_visibility="collapsed"
            )
            if not new_student_name:
                new_student_name = st.text_input(
                    "Or type student name",
                    key=f"new_student_manual_b_{program}",
                    placeholder="Type student name if not in list...",
                    label_visibility="collapsed"
                )
        
        with col_add:
            st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
            if st.button("➕ Add & Open Goal Builder", key=f"add_student_b_{program}", type="primary"):
                if new_student_name and new_student_name.strip():
                    smartar.append({"student_name": new_student_name.strip(), "notes": ""})
                    
                    if st.session_state.current_meeting_id:
                        smartar_url = get_smartar_goal_link(
                            new_student_name.strip(), 
                            st.session_state.current_meeting_id,
                            program,
                            pm_term or "T1",
                            pm_week
                        )
                        st.markdown(f"""
                        <meta http-equiv="refresh" content="0; url={smartar_url}">
                        <div style="background:#dbeafe;border-left:4px solid #0284c7;border-radius:8px;
                                    padding:12px 16px;margin:12px 0;font-size:14px;">
                          🎯 <strong>Opening SMARTAR Goal Builder for {new_student_name}...</strong><br>
                          If it doesn't open automatically, <a href="{smartar_url}" target="_blank">click here</a>
                        </div>
                        """, unsafe_allow_html=True)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("⚠️ Meeting not initialized yet - fill in meeting details first")
                else:
                    st.warning("⚠️ Please select or enter a student name")

        pm_reports = ""
        concerns = []

    st.markdown("---")
    
    # MEETING MINUTES / NOTES SECTION
    st.markdown("#### 📝 MEETING MINUTES / NOTES")
    st.caption("Comprehensive meeting notes - discussions, decisions, key points raised")
    
    default_minutes = selected_record.get('meeting_minutes', '') if selected_record else ''
    pm_minutes = st.text_area(
        "Meeting minutes",
        value=default_minutes,
        height=200,
        key=f"pm_minutes_{program}",
        label_visibility="collapsed",
        placeholder="Record comprehensive meeting minutes here - discussions, decisions, key points, follow-up items..."
    )
    
    st.markdown("---")
    
    # ACTIONS SECTION
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

    # Prepare meeting data for save - FIXED: Use local variables instead of session state
    smartar_data = [{"student_name": r.get("student_name",""), "notes": r.get("notes","")} for r in smartar]
    actions_data = actions  # Use local variable directly
    concerns_data = [{"notes": r.get("notes","")} for r in concerns] if is_week_a else []
    # Week B: priority_rows is [{notes: "..."}]; Week A: empty
    if not is_week_a and priority_rows:
        priority_data = priority_rows[0] if isinstance(priority_rows[0], dict) else {"notes": ""}
    else:
        priority_data = {}

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
        "meeting_minutes": pm_minutes.strip(),
        "actions": _json.dumps(actions_data),
    }

    # Trigger auto-save/auto-initialization
    trigger_autosave(program, meeting_data)

    # Manual save button
    save_button_text = "💾 Update Meeting Record" if st.session_state.current_meeting_id and not str(st.session_state.current_meeting_id).startswith("temp_") else "💾 Save Meeting Record"
    if st.button(save_button_text, type="primary", use_container_width=True, key=f"pm_save_{program}"):
        try:
            if st.session_state.current_meeting_id and not str(st.session_state.current_meeting_id).startswith("temp_"):
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
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Database save failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MEETING ARCHIVE - View and Edit Past Meetings
# ─────────────────────────────────────────────────────────────────────────────

def render_meeting_archive(program):
    """Display archive of past meetings with full section editing."""
    import json as _json

    st.markdown("### 📚 Meeting Archive")
    st.caption(f"Browse and edit past {PROGRAMS[program]['label']} meetings")

    all_meetings = fetch("tm_program_meetings", {"program": program}, "meeting_date")

    if not all_meetings:
        st.info("No past meetings found. Start recording meetings in the Program Meeting tab!")
        return

    st.markdown(f"**Total meetings recorded:** {len(all_meetings)}")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_term = st.selectbox(
            "Filter by term",
            ["All Terms"] + sorted(set(m.get('term', '') for m in all_meetings if m.get('term'))),
            key=f"archive_filter_term_{program}"
        )
    with col_filter2:
        if program in ["JP", "PY", "SY"]:
            filter_week_type = st.selectbox(
                "Filter by type", ["All Types", "Week A", "Week B"],
                key=f"archive_filter_type_{program}"
            )
        else:
            filter_week_type = "All Types"

    filtered_meetings = all_meetings
    if filter_term != "All Terms":
        filtered_meetings = [m for m in filtered_meetings if m.get('term') == filter_term]
    if filter_week_type == "Week A":
        filtered_meetings = [m for m in filtered_meetings if m.get('week_type') == 'A']
    elif filter_week_type == "Week B":
        filtered_meetings = [m for m in filtered_meetings if m.get('week_type') == 'B']

    st.markdown("---")

    for meeting in reversed(filtered_meetings):
        meeting_date  = meeting.get('meeting_date', 'Unknown')
        term          = meeting.get('term', '')
        week_num      = meeting.get('week_number', '')
        week_type     = meeting.get('week_type', '')
        facilitator   = meeting.get('facilitator', '')
        meeting_id    = meeting.get('id', '')
        edit_key      = f"arch_edit_{meeting_id}"

        if program in ["JP", "PY", "SY"]:
            week_badge = "🔵 Week A" if week_type == "A" else "🟡 Week B"
            header = f"{week_badge} | {meeting_date} | Term {term} W{week_num} | {facilitator}"
        else:
            header = f"🎨 Specialist | {meeting_date} | Term {term} W{week_num} | {facilitator}"

        with st.expander(header, expanded=False):

            in_edit_mode = st.session_state.get(edit_key, False)

            if not in_edit_mode:
                # ── READ VIEW ──────────────────────────────────────────────
                st.markdown(f"**Facilitator:** {facilitator} &nbsp;|&nbsp; **Attendees:** {meeting.get('attendees','Not recorded')}")
                st.markdown(f"<small style='color:#888;'>Meeting ID: {meeting_id}</small>", unsafe_allow_html=True)
                st.markdown("")

                # Check-in notes
                raw_checkin = meeting.get('checkin_notes', '')
                if raw_checkin:
                    st.markdown("**📋 Check-in Notes:**")
                    if program == "SPECIALIST":
                        try:
                            cd = _json.loads(raw_checkin)
                            if cd.get('monday_teacher'):
                                st.markdown(f"*Monday:* {cd['monday_teacher']}")
                            if cd.get('tuefri_teacher'):
                                st.markdown(f"*Tue–Fri:* {cd['tuefri_teacher']}")
                        except Exception:
                            st.markdown(raw_checkin)
                    else:
                        st.markdown(raw_checkin)

                # Priority focus (Week B)
                if week_type == "B" and meeting.get('priority_focus'):
                    st.markdown("**🎯 Priority Focus:**")
                    try:
                        pf = _json.loads(meeting['priority_focus'])
                        if isinstance(pf, dict):
                            st.markdown(pf.get('notes', ''))
                        elif isinstance(pf, list):
                            for r in pf:
                                if isinstance(r, dict) and any(r.values()):
                                    st.markdown("• " + " | ".join(v for v in r.values() if v))
                    except Exception:
                        st.markdown(str(meeting['priority_focus']))

                # Student concerns (Week A)
                if week_type == "A" and meeting.get('student_concerns'):
                    try:
                        sc = _json.loads(meeting['student_concerns'])
                        if isinstance(sc, list) and sc:
                            st.markdown("**👥 Student Concerns:**")
                            for r in sc:
                                note = r.get('notes','') if isinstance(r, dict) else str(r)
                                if note:
                                    st.markdown(f"• {note}")
                    except Exception:
                        pass

                # Meeting minutes
                current_minutes = meeting.get('meeting_minutes', '')
                st.markdown("**📝 Meeting Minutes:**")
                if current_minutes:
                    st.markdown(current_minutes)
                else:
                    st.caption("No minutes recorded yet.")

                # Actions summary
                if meeting.get('actions'):
                    try:
                        actions = _json.loads(meeting['actions'])
                        if actions:
                            st.markdown("**✅ Actions:**")
                            for a in actions:
                                if a.get('action'):
                                    done = "✅" if a.get("done") else "🔲"
                                    p_emoji = {"Low":"⬇️","Medium":"➡️","High":"⬆️","Urgent":"🔴"}.get(a.get("priority","Medium"),"➡️")
                                    st.markdown(f"{done} {p_emoji} {a['action']} — {a.get('who','')} by {a.get('by_when','')}")
                    except Exception:
                        pass

                st.markdown("")
                if st.button("✏️ Edit / Add to This Meeting", key=f"arch_open_{meeting_id}", type="secondary"):
                    st.session_state[edit_key] = True
                    st.rerun()

            else:
                # ── FULL EDIT MODE ─────────────────────────────────────────
                st.markdown(
                    f"""<div style="background:#fef3c7;border-left:4px solid #d97706;
                    border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:10px;font-size:13px;color:#92400e;">
                    ✏️ <strong>Editing:</strong> {meeting_date} — Term {term} W{week_num}
                    </div>""",
                    unsafe_allow_html=True
                )

                # ── Header fields ──
                col_d, col_f, col_a = st.columns([1.5, 1.5, 3])
                with col_d:
                    try:
                        ed_date = st.date_input("Date", value=datetime.date.fromisoformat(meeting_date), key=f"arch_date_{meeting_id}")
                    except Exception:
                        ed_date = st.date_input("Date", value=datetime.date.today(), key=f"arch_date_{meeting_id}")
                with col_f:
                    ed_fac = st.text_input("Facilitator", value=facilitator, key=f"arch_fac_{meeting_id}")
                with col_a:
                    ed_att = st.text_input("Attendees", value=meeting.get('attendees',''), key=f"arch_att_{meeting_id}")

                st.markdown("---")

                # ── Check-in notes ──
                st.markdown("**📋 Check-in Notes**")
                raw_checkin = meeting.get('checkin_notes','')
                if program == "SPECIALIST":
                    try:
                        cd = _json.loads(raw_checkin) if raw_checkin else {}
                    except Exception:
                        cd = {}
                    c1, c2 = st.columns(2)
                    with c1:
                        ed_mon = st.text_area("Monday Teacher", value=cd.get('monday_teacher',''), height=80, key=f"arch_mon_{meeting_id}")
                    with c2:
                        ed_tuefri = st.text_area("Tue–Fri Teacher", value=cd.get('tuefri_teacher',''), height=80, key=f"arch_tuefri_{meeting_id}")
                    ed_checkin_json = _json.dumps({"monday_teacher": ed_mon, "tuefri_teacher": ed_tuefri})
                    ed_checkin_raw = None
                else:
                    ed_checkin_raw = st.text_area(
                        "Check-in notes",
                        value=raw_checkin,
                        height=90,
                        key=f"arch_checkin_{meeting_id}",
                        label_visibility="collapsed",
                        placeholder="Check-in / regulation notes from the meeting…"
                    )
                    ed_checkin_json = None

                st.markdown("---")

                # ── Priority focus (Week B) ──
                ed_priority_json = None
                if week_type == "B":
                    st.markdown("**🎯 Priority Focus Notes**")
                    raw_pf = meeting.get('priority_focus','')
                    existing_pf = ""
                    if raw_pf:
                        try:
                            pf = _json.loads(raw_pf)
                            if isinstance(pf, dict):
                                existing_pf = pf.get('notes','')
                            elif isinstance(pf, list):
                                lines = []
                                for r in pf:
                                    if isinstance(r, dict):
                                        parts = [v for v in r.values() if v]
                                        if parts:
                                            lines.append("• " + " | ".join(parts))
                                existing_pf = "\n".join(lines)
                        except Exception:
                            existing_pf = str(raw_pf)
                    ed_pf = st.text_area(
                        "Priority focus",
                        value=existing_pf,
                        height=160,
                        key=f"arch_pf_{meeting_id}",
                        label_visibility="collapsed",
                        placeholder="Type or append priority focus notes…"
                    )
                    # Groq recalibration for archive priority notes
                    with st.expander("📋 Paste Transcript → Recalibrate with AI", expanded=False):
                        arch_transcript = st.text_area(
                            "Transcript",
                            height=120,
                            key=f"arch_pf_transcript_{meeting_id}",
                            label_visibility="collapsed",
                            placeholder="Paste rough notes or transcript here…"
                        )
                        if st.button("✨ Recalibrate", key=f"arch_pf_groq_{meeting_id}"):
                            if arch_transcript.strip() and GROQ_KEY:
                                with st.spinner("Recalibrating…"):
                                    try:
                                        _gc = Groq(api_key=GROQ_KEY)
                                        _r = _gc.chat.completions.create(
                                            model="llama-3.3-70b-versatile",
                                            messages=[{"role": "user", "content":
                                                f"Transform these rough meeting notes into structured CLC focus-area minutes. "
                                                f"Use headings: FOCUS AREA, WHAT'S WORKING, GAP, ADJUSTMENT, EVIDENCE, WHO & WHEN. "
                                                f"Trauma-informed, strengths-based, plain English. Preserve all facts.\n\n{arch_transcript}"}],
                                            max_tokens=1500
                                        )
                                        _new_text = _r.choices[0].message.content
                                        st.session_state[f"arch_pf_{meeting_id}"] = (ed_pf + "\n\n--- AI ---\n" + _new_text).strip() if ed_pf.strip() else _new_text
                                        st.rerun()
                                    except Exception as _e:
                                        st.error(f"Groq error: {_e}")
                    ed_priority_json = _json.dumps({"notes": ed_pf})
                    st.markdown("---")

                # ── Student concerns (Week A) ──
                ed_concerns_json = None
                if week_type == "A":
                    st.markdown("**👥 Student Concerns**")
                    raw_sc = meeting.get('student_concerns','')
                    existing_sc = ""
                    if raw_sc:
                        try:
                            sc = _json.loads(raw_sc)
                            if isinstance(sc, list):
                                existing_sc = "\n\n".join(r.get('notes','') for r in sc if isinstance(r,dict) and r.get('notes'))
                        except Exception:
                            existing_sc = str(raw_sc)
                    ed_sc = st.text_area(
                        "Student concerns",
                        value=existing_sc,
                        height=140,
                        key=f"arch_sc_{meeting_id}",
                        label_visibility="collapsed",
                        placeholder="Add or edit student concern notes…"
                    )
                    ed_concerns_json = _json.dumps([{"notes": ed_sc}])
                    st.markdown("---")

                # ── Meeting minutes ──
                st.markdown("**📝 Meeting Minutes**")
                st.caption("Edit existing minutes or append new content — add your notes at the bottom.")
                ed_minutes = st.text_area(
                    "Meeting minutes",
                    value=meeting.get('meeting_minutes',''),
                    height=280,
                    key=f"arch_minutes_{meeting_id}",
                    label_visibility="collapsed",
                    placeholder="Add or edit meeting minutes here…"
                )

                # Groq recalibration for minutes
                with st.expander("📋 Generate Minutes from Transcript (Groq)", expanded=False):
                    arch_min_transcript = st.text_area(
                        "Raw transcript",
                        height=140,
                        key=f"arch_min_transcript_{meeting_id}",
                        label_visibility="collapsed",
                        placeholder="Paste raw transcript or rough notes to generate polished minutes…"
                    )
                    if st.button("✨ Generate Minutes with AI", key=f"arch_min_groq_{meeting_id}"):
                        if arch_min_transcript.strip() and GROQ_KEY:
                            with st.spinner("Generating…"):
                                try:
                                    _gc2 = Groq(api_key=GROQ_KEY)
                                    _r2 = _gc2.chat.completions.create(
                                        model="llama-3.3-70b-versatile",
                                        messages=[{"role": "user", "content":
                                            f"Transform these notes into polished professional meeting minutes for "
                                            f"Cowandilla Learning Centre ({PROGRAMS[program]['label']} team meeting, {meeting_date}). "
                                            f"Structured, trauma-informed, plain English. Preserve all facts.\n\n{arch_min_transcript}"}],
                                        max_tokens=2500
                                    )
                                    _new_min = _r2.choices[0].message.content
                                    st.session_state[f"arch_minutes_{meeting_id}"] = (
                                        (ed_minutes + "\n\n--- AI Generated ---\n" + _new_min).strip()
                                        if ed_minutes.strip() else _new_min
                                    )
                                    st.rerun()
                                except Exception as _e:
                                    st.error(f"Groq error: {_e}")

                st.markdown("---")

                # ── Actions — add new rows ──
                st.markdown("**✅ Actions**")
                existing_actions = []
                if meeting.get('actions'):
                    try:
                        existing_actions = _json.loads(meeting['actions'])
                    except Exception:
                        existing_actions = []

                # Show existing + allow toggling done
                if existing_actions:
                    st.caption("Existing actions:")
                    for aidx, a in enumerate(existing_actions):
                        if a.get('action'):
                            ac1, ac2 = st.columns([5, 1])
                            with ac1:
                                p_emoji = {"Low":"⬇️","Medium":"➡️","High":"⬆️","Urgent":"🔴"}.get(a.get("priority","Medium"),"➡️")
                                st.markdown(f"{p_emoji} **{a['action']}** — {a.get('who','')} by {a.get('by_when','')}")
                            with ac2:
                                existing_actions[aidx]["done"] = st.checkbox(
                                    "Done", value=a.get("done", False),
                                    key=f"arch_done_{meeting_id}_{aidx}"
                                )

                st.caption("Add new action:")
                new_act_cols = st.columns([3, 1.5, 1, 1])
                new_act_action = new_act_cols[0].text_input("Action", key=f"arch_new_act_{meeting_id}", label_visibility="collapsed", placeholder="New action item")
                new_act_who   = new_act_cols[1].text_input("Who",    key=f"arch_new_who_{meeting_id}", label_visibility="collapsed", placeholder="Person")
                new_act_when  = new_act_cols[2].text_input("By",     key=f"arch_new_when_{meeting_id}", label_visibility="collapsed", placeholder="Date/week")
                new_act_pri   = new_act_cols[3].selectbox("Pri",     ["Medium","Low","High","Urgent"], key=f"arch_new_pri_{meeting_id}", label_visibility="collapsed")

                if new_act_action.strip():
                    existing_actions.append({
                        "action": new_act_action.strip(),
                        "who": new_act_who.strip(),
                        "by_when": new_act_when.strip(),
                        "priority": new_act_pri,
                        "done": False
                    })

                st.markdown("---")

                # ── Save / Cancel ──
                col_sv, col_cn = st.columns([1, 1])
                with col_sv:
                    if st.button("💾 Save All Changes", key=f"arch_save_{meeting_id}", type="primary", use_container_width=True):
                        try:
                            update_payload = {
                                "meeting_date": str(ed_date),
                                "facilitator": ed_fac.strip(),
                                "attendees": ed_att.strip(),
                                "meeting_minutes": ed_minutes.strip(),
                                "actions": _json.dumps(existing_actions),
                            }
                            if ed_checkin_json is not None:
                                update_payload["checkin_notes"] = ed_checkin_json
                            elif ed_checkin_raw is not None:
                                update_payload["checkin_notes"] = ed_checkin_raw.strip()
                            if ed_priority_json is not None:
                                update_payload["priority_focus"] = ed_priority_json
                            if ed_concerns_json is not None:
                                update_payload["student_concerns"] = ed_concerns_json

                            result = supabase.table('tm_program_meetings') \
                                .update(update_payload) \
                                .eq('id', str(meeting_id)) \
                                .execute()
                            st.success("✅ Meeting updated successfully!")
                            st.session_state[edit_key] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ Save failed: {e}")
                            st.info("Check the console or try again. Meeting ID: " + str(meeting_id))

                with col_cn:
                    if st.button("❌ Cancel", key=f"arch_cancel_{meeting_id}", use_container_width=True):
                        st.session_state[edit_key] = False
                        st.rerun()

def main():
    program   = get_program_from_params()
    prog_info = PROGRAMS[program]
    week_range = get_week_from_params()

    admin_login()

    grad_end = {
        "JP": "#3fa86a", "PY": "#2a6fd4", "SY": "#9b59b6",
        "SPECIALIST": "#f59e0b"
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

    if program == "SPECIALIST":
        tab_meeting, tab_archive = st.tabs(["🎨 Specialist Meeting", "📚 Archive"])
        with tab_meeting:
            render_specialist_meeting()
        with tab_archive:
            render_meeting_archive(program)
            
    elif program in ("JP", "PY", "SY"):
        tab_meeting, tab_archive = st.tabs(["🗒️ Program Meeting", "📚 Archive"])
        with tab_meeting: 
            render_program_meeting(program)
        with tab_archive:
            render_meeting_archive(program)


if __name__ == "__main__":
    main()
