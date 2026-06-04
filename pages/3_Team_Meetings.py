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
    """DISABLED — auto-init caused duplicates in multi-tab Streamlit. Save-only model."""
    return bool(st.session_state.current_meeting_id)

def trigger_autosave(program, meeting_data):
    """DISABLED — autosave caused duplicates in multi-tab Streamlit. Save-only model."""
    return False

# ── SMARTAR Goal Integration helpers ──────────────────────────────────────────
def get_smartar_goal_link(student_name, meeting_id, program, term, week_num):
    """Generate URL to SMARTAR Goal Builder with context."""
    base_url = "https://clc-lbu-portal.onrender.com/SMARTAR_Goal_Builder"
    params = f"?student={quote(student_name)}&meeting_id={meeting_id}&program={program}&term={term}&week={week_num}&return_to=team_meetings"
    return base_url + params

def fetch_synced_smartar_goal(student_name, meeting_id):
    """Fetch updated SMARTAR goal from the goal builder (Behaviour Support Supabase) with timeout."""
    try:
        # Import here to avoid issues if behaviour support connection not configured
        import os
        from supabase import create_client as _cc
        import signal
        
        # Get Behaviour Support Supabase credentials
        burl = st.secrets.get("BEHAVIOUR_SUPABASE_URL","") or os.environ.get("BEHAVIOUR_SUPABASE_URL","")
        bkey = st.secrets.get("BEHAVIOUR_SUPABASE_KEY","") or os.environ.get("BEHAVIOUR_SUPABASE_KEY","")
        
        if not burl or not bkey:
            # Behaviour Support Supabase not configured
            return None
        
        # Define timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError("SMARTAR goal fetch timed out")
        
        # Set 3 second timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(3)
        
        try:
            # Create Behaviour Support Supabase client
            behaviour_supabase = _cc(burl, bkey)
            
            # Query smartar_goals table in Behaviour Support Supabase
            result = behaviour_supabase.table('smartar_goals').select('smartar_goal').eq('student_name', student_name).eq('meeting_id', meeting_id).order('updated_at', desc=True).limit(1).execute()
            
            # Cancel alarm
            signal.alarm(0)
            
            if result.data and len(result.data) > 0:
                return result.data[0].get('smartar_goal', '')
        except TimeoutError:
            signal.alarm(0)
            return None
        finally:
            # Ensure alarm is cancelled
            signal.alarm(0)
            
    except Exception as e:
        # Log error but don't crash - integration is optional
        return None
    
    return None

# ══════════════════════════════════════════════════════════════════════════════
# NEW: SMART AI GENERATION WITH DUPLICATION DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_student_names_from_concerns(concerns_json):
    """Extract student names already documented in Student Concerns section."""
    try:
        concerns_data = json.loads(concerns_json) if isinstance(concerns_json, str) else concerns_json
        if isinstance(concerns_data, list):
            names = []
            for item in concerns_data:
                text = item.get('notes', '')
                if text.strip():
                    if '·' in text:
                        name = text.split('·')[0].strip()
                        if name:
                            names.append(name.lower())
                    else:
                        words = text.split()
                        if words:
                            name = ' '.join(words[:2]).strip()
                            names.append(name.lower())
            return names
    except:
        return []
    return []

def generate_smart_minutes_week_a(transcript, existing_concerns_json, program):
    """
    Week A AI generation with duplication detection.
    
    Intelligently splits transcript into:
    1. NEW student concerns (not already documented)
    2. General meeting minutes
    3. Suggested actions with who/when
    """
    if not GROQ_KEY or not transcript.strip():
        return None
    
    existing_students = extract_student_names_from_concerns(existing_concerns_json)
    existing_list = ", ".join(existing_students) if existing_students else "None documented yet"
    
    try:
        client = Groq(api_key=GROQ_KEY)
        prompt = f"""You are a professional minute-taker for Cowandilla Learning Centre (CLC), Learning & Behaviour Unit.

A raw transcript from a Week A 'Student Lens' team meeting for the {PROGRAMS[program]['label']} program is provided below.

CRITICAL CONTEXT — Students already documented in Student Concerns section:
{existing_list}

DO NOT repeat any information about students already listed above. Only extract NEW student concerns not yet documented.

Your job: Read the transcript and produce THREE clearly separated sections.

---
SECTION 1 — NEW STUDENT CONCERNS
ONLY include students NOT in the existing list above.

For each NEW student concern, format as:
[Student Name] · [Concern/behaviour] · [Hypothesis - why?] · [Strategy to try] · [Who] · [By when]

Example:
Jayden R · Refusing work in literacy · Possible reading anxiety, avoidance pattern · Trial audio books + visual supports · Tom · W6

If no new students discussed, write: "No new student concerns requiring documentation - see existing entries above."

---
SECTION 2 — MEETING MINUTES
Everything else — general discussion, decisions, announcements, TAC updates, reports, transitions, any other business that is NOT student-specific concerns.

Format as clear professional minutes with numbered items.

---
SECTION 3 — SUGGESTED ACTIONS
Extract all action items mentioned in the transcript.

For each action, provide:
ACTION: [Specific task]
WHO: [Person responsible]
BY WHEN: [Due date or week]
PRIORITY: [Low/Medium/High/Urgent]

Rules:
- Trauma-informed, strengths-based, plain English
- Preserve ALL factual content — do not fabricate
- Be concise but complete
- DO NOT repeat student names from existing list
- Clearly label all three sections

RAW TRANSCRIPT:
{transcript[:3500]}"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200
        )
        
        full_output = response.choices[0].message.content
        
        sections = {
            'student_concerns': '',
            'minutes': '',
            'actions': []
        }
        
        if "SECTION 2" in full_output:
            parts = full_output.split("SECTION 2", 1)
            section1 = parts[0].replace("SECTION 1 — NEW STUDENT CONCERNS", "").replace("SECTION 1", "").replace("---", "").strip()
            remaining = parts[1]
            
            if "SECTION 3" in remaining:
                section2_and_3 = remaining.split("SECTION 3", 1)
                section2 = section2_and_3[0].replace("— MEETING MINUTES", "").replace("---", "").strip()
                section3 = section2_and_3[1].replace("— SUGGESTED ACTIONS", "").replace("---", "").strip()
                
                sections['student_concerns'] = section1
                sections['minutes'] = section2
                
                actions_list = []
                current_action = {}
                
                for line in section3.split('\n'):
                    line = line.strip()
                    if line.startswith("ACTION:"):
                        if current_action.get('action'):
                            actions_list.append(current_action)
                        current_action = {'action': line.replace("ACTION:", "").strip()}
                    elif line.startswith("WHO:"):
                        current_action['who'] = line.replace("WHO:", "").strip()
                    elif line.startswith("BY WHEN:"):
                        current_action['by_when'] = line.replace("BY WHEN:", "").strip()
                    elif line.startswith("PRIORITY:"):
                        priority = line.replace("PRIORITY:", "").strip()
                        current_action['priority'] = priority if priority in ["Low", "Medium", "High", "Urgent"] else "Medium"
                
                if current_action.get('action'):
                    actions_list.append(current_action)
                
                sections['actions'] = actions_list
        
        return sections
        
    except Exception as e:
        st.error(f"AI generation error: {e}")
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
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900
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
# DUPLICATE DETECTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _meeting_signature(rec):
    """A stable key that identifies 'the same meeting'. Two records sharing this
    signature are considered duplicates of one another."""
    return (
        str(rec.get("program", "")).strip(),
        str(rec.get("meeting_date", "")).strip(),
        str(rec.get("week_type", "")).strip(),
        str(rec.get("term", "")).strip(),
        str(rec.get("week_number", "")).strip(),
    )


def find_existing_meetings(program, meeting_date, week_type, term, week_number):
    """Return all saved records matching this meeting's signature (newest first)."""
    target = (
        str(program).strip(),
        str(meeting_date).strip(),
        str(week_type).strip(),
        str(term).strip(),
        str(week_number).strip(),
    )
    matches = []
    for rec in fetch("tm_program_meetings", {"program": program}, "meeting_date"):
        if _meeting_signature(rec) == target:
            matches.append(rec)
    # Newest first (by created/updated id ordering as a fallback)
    matches.sort(key=lambda r: str(r.get("updated_at") or r.get("created_at") or r.get("id") or ""), reverse=True)
    return matches


def find_duplicate_meeting_groups(program):
    """Scan all records for this program and return {signature: [records]} for any
    signature that appears more than once (i.e. true duplicates in the database)."""
    groups = {}
    for rec in fetch("tm_program_meetings", {"program": program}, "meeting_date"):
        sig = _meeting_signature(rec)
        groups.setdefault(sig, []).append(rec)
    return {sig: recs for sig, recs in groups.items() if len(recs) > 1}


# ─────────────────────────────────────────────────────────────────────────────
# SMARTAR LINK BUTTON (reliable, opens in a new tab)
# ─────────────────────────────────────────────────────────────────────────────

def smartar_link_button(url, label="🎯 Open Goal Builder"):
    """Render a styled anchor that reliably opens the Goal Builder in a NEW tab,
    so the meeting form is never lost. Markdown links / meta-refresh were unreliable."""
    st.markdown(
        f'<a href="{url}" target="_blank" rel="noopener" '
        f'style="display:inline-block;background:#1A7A6E;color:#fff;font-weight:600;'
        f'font-size:0.82rem;padding:0.4rem 0.8rem;border-radius:8px;text-decoration:none;">'
        f'{label}</a>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CURRENT SMARTAR GOALS — fetched live from the Goal Builder so they can be
# viewed (and noted against) right inside the spotlight.
# ─────────────────────────────────────────────────────────────────────────────

def _html_escape(text):
    return (str(text or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_student_smartar_goals(student_name):
    """Fetch a student's CURRENT SMARTAR goals from the Goal Builder
    (Behaviour Support Supabase, smartar_goals table). Active goals first,
    then newest first. Returns a list of dicts (empty if none / not configured).
    Cached for 60s; use fetch_student_smartar_goals.clear() to refresh."""
    if not student_name or not str(student_name).strip():
        return []
    try:
        import os
        from supabase import create_client as _cc
        burl = st.secrets.get("BEHAVIOUR_SUPABASE_URL", "") or os.environ.get("BEHAVIOUR_SUPABASE_URL", "")
        bkey = st.secrets.get("BEHAVIOUR_SUPABASE_KEY", "") or os.environ.get("BEHAVIOUR_SUPABASE_KEY", "")
        # Fallback to a nested [supabase] secrets section if present
        if not burl:
            sb = st.secrets.get("supabase", {})
            if isinstance(sb, dict):
                burl = sb.get("url", "")
                bkey = sb.get("key", "") or sb.get("service_key", "")
        if not burl or not bkey:
            return []
        client = _cc(burl, bkey)
        res = client.table("smartar_goals").select("*").eq("student_name", str(student_name).strip()).execute()
        rows = res.data or []
        # Newest first, then stable-sort so active goals come first
        rows.sort(key=lambda r: str(r.get("updated_at") or r.get("created_at") or r.get("id") or ""), reverse=True)
        rows.sort(key=lambda r: 0 if r.get("active", True) and str(r.get("status", "Active")).lower() not in ("archived", "achieved", "on hold") else 1)
        return rows
    except Exception:
        return []


def render_current_smartar_goals(student_name, max_goals=3):
    """Display a student's current SMARTAR goal(s) inline, so the team can read
    the live goal and record notes alongside it during the meeting."""
    goals = fetch_student_smartar_goals(student_name)
    if not goals:
        st.caption("ℹ️ No saved SMARTAR goal found yet — use the Goal Builder button to create one, then ↻ Refresh.")
        return

    for g in goals[:max_goals]:
        goal_text = (g.get("smartar_goal") or g.get("goal_text") or g.get("goal") or "").strip()
        status    = (g.get("status") or ("Active" if g.get("active", True) else "Archived"))
        skill     = (g.get("skill") or g.get("domain") or "").strip()
        review    = (g.get("review_date") or g.get("target_date") or "")
        header_bits = " · ".join(b for b in [status, skill] if b)

        st.markdown(
            "<div style='background:#f0f9f9;border:1px solid #1A7A6E;border-left:5px solid #1A7A6E;"
            "border-radius:0 8px 8px 0;padding:8px 12px;margin:4px 0;'>"
            "<div style='font-size:0.7rem;color:#1A7A6E;font-weight:700;letter-spacing:0.03em;'>"
            f"CURRENT SMARTAR GOAL{(' · ' + _html_escape(header_bits)) if header_bits else ''}</div>"
            f"<div style='font-size:0.9rem;color:#0f172a;margin-top:3px;'>{_html_escape(goal_text) or '—'}</div>"
            + (f"<div style='font-size:0.7rem;color:#64748B;margin-top:4px;'>Review: {_html_escape(review)}</div>" if review else "")
            + "</div>",
            unsafe_allow_html=True,
        )

        # GAS performance levels (Goal Builder schema), if present
        gas = [
            ("Exceeding",  g.get("gas_exceeding")),
            ("Above",      g.get("gas_above")),
            ("Expected",   g.get("gas_expected")),
            ("Below",      g.get("gas_below")),
            ("Not yet",    g.get("gas_not_yet")),
        ]
        if any(v for _, v in gas):
            with st.expander("📊 GAS levels", expanded=False):
                for lvl, txt in gas:
                    if txt:
                        st.markdown(f"**{lvl}:** {txt}")

        # Other detail fields (alternate schema variant), if present
        extra = [
            ("Baseline",       g.get("baseline")),
            ("Target",         g.get("target")),
            ("Strategies",     g.get("strategies")),
            ("Progress notes", g.get("progress_notes")),
        ]
        if any(v for _, v in extra):
            with st.expander("📋 Goal detail", expanded=False):
                for lbl, txt in extra:
                    if txt:
                        st.markdown(f"**{lbl}:** {txt}")


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
# PROFESSIONAL MINUTES — WORD DOCUMENT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

TEAL  = "1A7A6E"
AMBER = "C8760A"
INK   = "0F172A"
GREY  = "64748B"

def _safe_json(raw, default):
    import json as _json
    if raw is None:
        return default
    if not isinstance(raw, str):
        return raw
    try:
        return _json.loads(raw)
    except Exception:
        return default

def _doc_heading(doc, text, colour=TEAL, size=13, space_before=10, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    _para_run(p, text, bold=True, size_pt=size, colour=colour)
    return p

def _doc_rule(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), TEAL)
    pbdr.append(bottom)
    pPr.append(pbdr)

def build_minutes_docx(md, program):
    """Build a polished, sendable Word minutes document from a meeting-data dict
    (same column structure used for saving). Returns a BytesIO."""
    week_type = md.get("week_type", "")
    if program == "SPECIALIST":
        type_label = "Specialist Program Meeting"
    elif week_type == "A":
        type_label = "Week A — Student Lens"
    elif week_type == "B":
        type_label = "Week B — System Lens"
    else:
        type_label = "Team Meeting"

    prog_label = PROGRAMS.get(program, {}).get("label", program)

    doc = Document()
    # Base style
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = _rgb(INK)
    for section in doc.sections:
        section.top_margin    = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin   = Cm(2.0)
        section.right_margin  = Cm(2.0)

    # ── Title band ──
    title = doc.add_paragraph()
    title.paragraph_format.space_after = Pt(0)
    _para_run(title, "Cowandilla Learning Centre", bold=True, size_pt=18, colour=TEAL)
    sub = doc.add_paragraph()
    sub.paragraph_format.space_after = Pt(2)
    _para_run(sub, "Learning & Behaviour Unit", bold=False, size_pt=10.5, colour=GREY)
    mt = doc.add_paragraph()
    mt.paragraph_format.space_after = Pt(6)
    _para_run(mt, f"{prog_label}  ·  {type_label}", bold=True, size_pt=12, colour=AMBER)
    _doc_rule(doc)

    # ── Meeting details table ──
    details = [
        ("Date",        str(md.get("meeting_date", ""))),
        ("Term / Week", f"{md.get('term','')}  ·  Week {md.get('week_number','')}"),
        ("Facilitator", md.get("facilitator", "")),
        ("Attendees",   md.get("attendees", "") or "Not recorded"),
    ]
    tbl = doc.add_table(rows=len(details), cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl.allow_autofit = True
    for i, (label, value) in enumerate(details):
        c0, c1 = tbl.rows[i].cells
        c0.width = Cm(3.5); c1.width = Cm(13.0)
        _shade_cell(c0, "F1F5F9")
        p0 = c0.paragraphs[0]; p0.paragraph_format.space_after = Pt(1)
        _para_run(p0, label, bold=True, size_pt=9.5, colour=TEAL)
        p1 = c1.paragraphs[0]; p1.paragraph_format.space_after = Pt(1)
        _para_run(p1, str(value), size_pt=10, colour=INK)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # ── Check-in notes ──
    checkin = md.get("checkin_notes", "")
    if program == "SPECIALIST":
        cd = _safe_json(checkin, {})
        mon = cd.get("monday_teacher", "") if isinstance(cd, dict) else ""
        tf  = cd.get("tuefri_teacher", "") if isinstance(cd, dict) else ""
        if mon or tf:
            _doc_heading(doc, "Team Check-in & Handover")
            if mon:
                p = doc.add_paragraph(); _para_run(p, "Monday Teacher: ", bold=True, size_pt=10, colour=AMBER); _para_run(p, mon, size_pt=10)
            if tf:
                p = doc.add_paragraph(); _para_run(p, "Tuesday–Friday Teacher: ", bold=True, size_pt=10, colour=AMBER); _para_run(p, tf, size_pt=10)
    else:
        if isinstance(checkin, str) and checkin.strip():
            _doc_heading(doc, "Team Check-in")
            doc.add_paragraph(checkin.strip())

    # ── Student concerns (Week A / Specialist) ──
    concerns = _safe_json(md.get("student_concerns", ""), [])
    concern_items = []
    if isinstance(concerns, dict):
        # Specialist structure
        for c in concerns.get("concerns", []):
            if isinstance(c, dict):
                txt = " · ".join(v for v in [c.get("concern"), c.get("strategy"), c.get("adjustment"), c.get("who"), c.get("timeline")] if v)
                if txt:
                    concern_items.append(txt)
        prog_c = concerns.get("program_concerns", "")
    elif isinstance(concerns, list):
        for c in concerns:
            if isinstance(c, dict) and c.get("notes", "").strip():
                concern_items.append(c["notes"].strip())
        prog_c = ""
    else:
        prog_c = ""

    if concern_items:
        _doc_heading(doc, "Student Concerns")
        for txt in concern_items:
            p = doc.add_paragraph(style=None)
            p.paragraph_format.left_indent = Cm(0.4)
            p.paragraph_format.space_after = Pt(3)
            _para_run(p, "•  ", bold=True, colour=AMBER)
            _para_run(p, txt, size_pt=10)
    if isinstance(concerns, dict) and prog_c and prog_c.strip():
        p = doc.add_paragraph(); _para_run(p, "Program-level concerns: ", bold=True, size_pt=10, colour=AMBER); _para_run(p, prog_c.strip(), size_pt=10)

    # ── SMARTAR spotlight ──
    smartar = _safe_json(md.get("smartar_spotlight", ""), [])
    if isinstance(smartar, list) and any(s.get("student_name") for s in smartar if isinstance(s, dict)):
        _doc_heading(doc, "SMARTAR Goal Spotlight")
        for s in smartar:
            if isinstance(s, dict) and s.get("student_name"):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.4)
                p.paragraph_format.space_after = Pt(2)
                _para_run(p, "•  ", bold=True, colour=AMBER)
                _para_run(p, s["student_name"], bold=True, size_pt=10)
                if s.get("notes", "").strip():
                    _para_run(p, "  —  " + s["notes"].strip(), size_pt=10, colour=GREY)

    # ── Priority focus (Week B) ──
    pf = _safe_json(md.get("priority_focus", ""), {})
    pf_notes = pf.get("notes", "") if isinstance(pf, dict) else ""
    if pf_notes and pf_notes.strip():
        _doc_heading(doc, "Priority Focus — System Lens")
        for line in pf_notes.strip().split("\n"):
            if line.strip():
                doc.add_paragraph(line.strip())

    # ── Reports / TAC ──
    reports = md.get("reports_tac_notes", "")
    if isinstance(reports, str) and reports.strip():
        _doc_heading(doc, "Reports / TAC / Transitions")
        doc.add_paragraph(reports.strip())

    # ── Meeting minutes ──
    minutes = md.get("meeting_minutes", "")
    if isinstance(minutes, str) and minutes.strip():
        _doc_heading(doc, "Meeting Minutes")
        for block in minutes.strip().split("\n"):
            if block.strip():
                doc.add_paragraph(block.strip())

    # ── Actions table ──
    actions = _safe_json(md.get("actions", ""), [])
    real_actions = [a for a in actions if isinstance(a, dict) and a.get("action", "").strip()]
    if real_actions:
        _doc_heading(doc, "Actions")
        at = doc.add_table(rows=1, cols=5)
        at.alignment = WD_TABLE_ALIGNMENT.LEFT
        hdr = ["Action", "Who", "By When", "Priority", "Done"]
        widths = [Cm(7.0), Cm(3.0), Cm(2.6), Cm(2.2), Cm(1.6)]
        for j, h in enumerate(hdr):
            cell = at.rows[0].cells[j]
            cell.width = widths[j]
            _shade_cell(cell, TEAL)
            pr = cell.paragraphs[0]; pr.paragraph_format.space_after = Pt(1)
            _para_run(pr, h, bold=True, size_pt=9.5, colour="FFFFFF")
        for a in real_actions:
            row = at.add_row().cells
            vals = [a.get("action",""), a.get("who",""), a.get("by_when",""),
                    a.get("priority","Medium"), "✓" if a.get("done") else ""]
            for j, v in enumerate(vals):
                row[j].width = widths[j]
                pr = row[j].paragraphs[0]; pr.paragraph_format.space_after = Pt(1)
                _para_run(pr, str(v), size_pt=9.5)

    # ── Footer line ──
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    _doc_rule(doc)
    foot = doc.add_paragraph()
    _para_run(foot, f"Minutes generated from the CLC LBU Portal · {datetime.date.today().isoformat()}",
              italic=True, size_pt=8.5, colour=GREY)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

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
    recent_records = past_meetings[:20]
    meeting_options = ["➕ New Meeting"] + [
        f"{rec.get('meeting_date','')} - Term {rec.get('term','')} W{rec.get('week_number','')}"
        for rec in recent_records
    ]
    
    selected_meeting = st.selectbox(
        "Choose a meeting to edit or create new",
        options=meeting_options,
        key="meeting_select_specialist"
    )
    
    # Load existing meeting if selected
    selected_record = None
    if selected_meeting != "➕ New Meeting":
        # Find the selected record (aligned with meeting_options order)
        selected_idx = meeting_options.index(selected_meeting) - 1
        selected_record = recent_records[selected_idx]
        
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
    editing_existing = bool(st.session_state.current_meeting_id) and not str(st.session_state.current_meeting_id).startswith("temp_")
    save_button_text = "💾 Update Meeting Record" if editing_existing else "💾 Save Meeting Record"
    if st.button(save_button_text, type="primary", use_container_width=True, key="sp_save"):
        try:
            saved_id = None
            if editing_existing:
                supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                saved_id = st.session_state.current_meeting_id
                st.success("✅ Meeting record updated!")
            else:
                existing = find_existing_meetings(
                    "SPECIALIST", meeting_data["meeting_date"], meeting_data["week_type"],
                    meeting_data["term"], meeting_data["week_number"]
                )
                if existing:
                    saved_id = existing[0]['id']
                    supabase.table('tm_program_meetings').update(meeting_data).eq('id', saved_id).execute()
                    if len(existing) > 1:
                        dup_ids = ", ".join(str(e['id']) for e in existing[1:])
                        st.warning(f"⚠️ {len(existing)} copies of this meeting already exist. Updated the most recent. Extra IDs: {dup_ids}.")
                    else:
                        st.success("✅ A meeting for this date already existed — updated it instead of creating a duplicate.")
                else:
                    result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
                    saved_id = result.data[0]['id'] if result.data else None
                    st.success("✅ Meeting record saved!")

            if saved_id:
                st.session_state.current_meeting_id = saved_id

            st.session_state.last_autosave_time = None
            st.session_state.autosave_message = ""
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Database save failed: {e}")

    # ── Download professional minutes (Word) ──────────────────────────────────
    st.markdown("")
    try:
        _docx_buf = build_minutes_docx(meeting_data, "SPECIALIST")
        st.download_button(
            "📥 Download Minutes (Word) — ready to send to members",
            data=_docx_buf,
            file_name=f"CLC_Specialist_Minutes_{meeting_data['meeting_date']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="sp_download",
        )
        st.caption("Tip: save first so the download matches the stored record exactly.")
    except Exception as _e:
        st.caption(f"Minutes document could not be generated: {_e}")


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

    # ── Duplicate check banner ────────────────────────────────────────────────
    dup_groups = find_duplicate_meeting_groups(program)
    if dup_groups:
        with st.expander(f"⚠️ Duplicate check — {len(dup_groups)} meeting(s) saved more than once", expanded=True):
            st.caption("These meetings share the same date / term / week / type. Keep the newest and remove the extras.")
            for sig, recs in dup_groups.items():
                _, mdate, wtype, mterm, mweek = sig
                st.markdown(f"**{mdate} · Term {mterm} · Week {mweek} · Type {wtype or '—'}** — {len(recs)} copies")
                # recs are newest-first already from fetch order is by date; sort by id text desc
                recs_sorted = sorted(recs, key=lambda r: str(r.get("updated_at") or r.get("created_at") or r.get("id") or ""), reverse=True)
                keep = recs_sorted[0]
                st.caption(f"Keeping most recent (ID {keep.get('id')}). Extras: {', '.join(str(r.get('id')) for r in recs_sorted[1:])}")
                if st.session_state.get("admin"):
                    if st.button(f"🗑️ Delete {len(recs_sorted)-1} extra copy(ies)", key=f"dedupe_{program}_{mdate}_{wtype}_{mweek}"):
                        deleted = 0
                        for r in recs_sorted[1:]:
                            try:
                                delete_row("tm_program_meetings", r.get("id"))
                                deleted += 1
                            except Exception as _e:
                                st.error(f"Could not delete ID {r.get('id')}: {_e}")
                        st.success(f"Removed {deleted} duplicate copy(ies).")
                        st.rerun()
                else:
                    st.caption("🔐 Log in as admin (sidebar) to remove duplicates.")
        # refresh list after potential changes
        past_meetings = fetch("tm_program_meetings", {"program": program}, "meeting_date")

    # Meeting selection - New or Edit existing
    st.markdown("#### 📂 Select Meeting")
    # past_meetings is date-descending; show the newest 20 (newest first) so a
    # meeting you just saved is always selectable at the top.
    recent_records = past_meetings[:20]
    meeting_options = ["➕ New Meeting"] + [
        f"{rec.get('meeting_date','')} - Term {rec.get('term','')} W{rec.get('week_number','')} - Week {rec.get('week_type','')}"
        for rec in recent_records
    ]
    
    # Pre-select the meeting matching current_meeting_id (e.g. the one just saved).
    # This is driven entirely by the `index` argument with NO widget key, so we
    # never write the selectbox's own session_state key — Streamlit forbids that
    # once the widget has been instantiated, which was causing save failures.
    default_index = 0
    if st.session_state.current_meeting_id:
        for _i, _rec in enumerate(recent_records):
            if str(_rec.get("id")) == str(st.session_state.current_meeting_id):
                default_index = _i + 1  # +1 to skip the "➕ New Meeting" entry
                break

    selected_meeting = st.selectbox(
        "Choose a meeting to edit or create new",
        options=meeting_options,
        index=default_index,
    )
    
    # Load existing meeting if selected
    selected_record = None
    if selected_meeting != "➕ New Meeting":
        # Find the selected record (aligned with meeting_options order)
        selected_idx = meeting_options.index(selected_meeting) - 1
        selected_record = recent_records[selected_idx]
        
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
            # Clear session state (lists)
            for k in [f"pm_concerns_{program}", f"pm_smartar_{program}",
                      f"pm_priority_{program}", f"pm_actions_{program}"]:
                st.session_state.pop(k, None)
            # Also purge per-row widget states so a fresh meeting starts genuinely blank
            for wk in list(st.session_state.keys()):
                if wk.startswith(f"con_notes_{program}_") or wk.startswith(f"sm_notes_{program}_") \
                   or wk.startswith(f"sm_notes_b_{program}_"):
                    st.session_state.pop(wk, None)
    
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

        # Manual entry section
        st.markdown("**Option A: Manual Entry**")
        
        import uuid as _uuid
        concerns_key = f"pm_concerns_{program}"
        if concerns_key not in st.session_state:
            # Load from selected_record if editing
            if selected_record and selected_record.get('student_concerns'):
                try:
                    loaded = _json.loads(selected_record['student_concerns'])
                    st.session_state[concerns_key] = loaded if isinstance(loaded, list) else [{"notes": ""}]
                except:
                    st.session_state[concerns_key] = [{"notes": ""}]
            else:
                st.session_state[concerns_key] = [{"notes": ""}]

        concerns = st.session_state[concerns_key]

        # Give every row a STABLE id. Widget keys are tied to the id (not the list
        # position) so adding/removing a student never scrambles what was typed.
        for row in concerns:
            if not row.get("_id"):
                row["_id"] = _uuid.uuid4().hex

        delete_id = None
        for idx, row in enumerate(concerns):
            cid = row["_id"]
            col_text, col_del = st.columns([11, 0.5])
            with col_text:
                row["notes"] = st.text_area(
                    f"Student {idx + 1}",
                    value=row.get("notes", ""),
                    key=f"con_notes_{program}_{cid}",
                    height=100,
                    placeholder="Student name · Concern / behaviour · Hypothesis (why?) · Strategy to try · Who · By when",
                )
            with col_del:
                st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
                if len(concerns) > 1:
                    if st.button("✕", key=f"con_del_{program}_{cid}"):
                        delete_id = cid
        if delete_id is not None:
            # Remove the matching row AND its widget state, then rerun.
            st.session_state[concerns_key] = [c for c in concerns if c.get("_id") != delete_id]
            st.session_state.pop(f"con_notes_{program}_{delete_id}", None)
            st.rerun()

        if st.button("➕ Add student concern", key=f"con_add_{program}"):
            concerns.append({"notes": "", "_id": _uuid.uuid4().hex})
            st.rerun()
        
        # Show summary of documented students
        if concerns and any(c.get('notes', '').strip() for c in concerns):
            existing_count = len([c for c in concerns if c.get('notes', '').strip()])
            st.caption(f"📋 {existing_count} student(s) currently documented above")
        
        st.markdown("---")
        
        # AI Generation section
        st.markdown("**Option B: Generate from Transcript**")
        st.caption("AI will identify NEW student concerns not already documented above")
        
        transcript_concerns = st.text_area(
            "Meeting transcript",
            height=180,
            key=f"transcript_concerns_{program}",
            label_visibility="collapsed",
            placeholder="Paste meeting transcript here..."
        )
        
        col_gen, col_status = st.columns([2, 3])
        with col_gen:
            if st.button("✨ Analyze with AI", key=f"gen_concerns_{program}", type="primary"):
                if transcript_concerns.strip():
                    with st.spinner("Analyzing transcript..."):
                        existing_json = _json.dumps(concerns)
                        result = generate_smart_minutes_week_a(transcript_concerns, existing_json, program)
                        
                        if result:
                            st.session_state[f'_ai_new_concerns_{program}'] = result['student_concerns']
                            st.session_state[f'_ai_minutes_{program}'] = result['minutes']
                            st.session_state[f'_ai_actions_{program}'] = result['actions']
                            st.success("✓ Analysis complete!")
                            time.sleep(0.5)
                            st.rerun()
                else:
                    st.warning("Please paste transcript first")
        
        with col_status:
            if st.session_state.get(f'_ai_new_concerns_{program}'):
                st.info("✓ AI results ready below")
        
        st.markdown("---")
        
        # AI Results Review
        if st.session_state.get(f'_ai_new_concerns_{program}'):
            st.markdown("### 🤖 AI Analysis Results")
            new_concerns_text = st.session_state[f'_ai_new_concerns_{program}']
            
            if "No new student concerns" in new_concerns_text:
                st.info("✓ All students in transcript already documented")
                if st.button("Clear Results", key=f"clear_concerns_{program}"):
                    del st.session_state[f'_ai_new_concerns_{program}']
                    st.rerun()
            else:
                st.markdown("**New Student Concerns Found:**")
                edited_concerns = st.text_area(
                    "Review concerns",
                    value=new_concerns_text,
                    height=150,
                    key=f"review_concerns_{program}",
                    label_visibility="collapsed"
                )
                
                new_lines = [line.strip() for line in edited_concerns.split('\n') 
                            if line.strip() and not line.startswith("No new")]
                
                if new_lines:
                    st.caption(f"Will add {len(new_lines)} new concern(s)")
                
                col_accept, col_reject = st.columns(2)
                with col_accept:
                    if st.button("✅ Accept & Add", key=f"accept_concerns_{program}", type="primary"):
                        for line in new_lines:
                            if line:
                                concerns.append({"notes": line})
                        del st.session_state[f'_ai_new_concerns_{program}']
                        st.success(f"Added {len(new_lines)} concern(s)!")
                        time.sleep(0.5)
                        st.rerun()
                
                with col_reject:
                    if st.button("❌ Discard", key=f"reject_concerns_{program}"):
                        del st.session_state[f'_ai_new_concerns_{program}']
                        st.rerun()
        
        st.markdown("---")

        st.markdown("#### ⏱ 25–40 min | SMARTAR GOAL SPOTLIGHT — 4 Students")
        st.caption("Click student name to open Goal Builder, or add new student")

        if not st.session_state.current_meeting_id:
            st.info("💡 Save the meeting details above first — SMARTAR links will activate once the meeting has an ID.")

        if student_names:
            st.caption(f"💡 {len(student_names)} students loaded")

        # SMARTAR student selection - REDESIGNED with buttons
        st.markdown("**Select students for goal spotlight:**")
        
        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = []
        
        smartar = st.session_state[smartar_key]
        
        # Display existing students with their CURRENT SMARTAR goal + notes
        if smartar:
            hdr_l, hdr_r = st.columns([5, 1])
            with hdr_r:
                st.button("↻ Refresh goals", key=f"refresh_goals_{program}",
                          on_click=fetch_student_smartar_goals.clear,
                          help="Reload current goals from the Goal Builder")
            for idx, student_data in enumerate(smartar):
                student_name = student_data.get("student_name", "")
                if not student_name:
                    continue

                col_name, col_goal_btn, col_remove = st.columns([4, 2, 0.5])
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
                        smartar_link_button(smartar_url)
                    else:
                        st.caption("Save meeting first")
                with col_remove:
                    if st.button("✕", key=f"sm_remove_{program}_{idx}"):
                        smartar.pop(idx)
                        st.rerun()

                # Show the student's CURRENT SMARTAR goal(s) inline
                render_current_smartar_goals(student_name)

                # Meeting notes recorded alongside the goal
                student_data["notes"] = st.text_area(
                    f"Notes for {student_name}",
                    value=student_data.get("notes", ""),
                    key=f"sm_notes_{program}_{idx}",
                    height=80,
                    placeholder="Notes alongside this goal — progress, evidence, adjustments, next steps…",
                    label_visibility="collapsed"
                )
                st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

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
            if st.button("➕ Add to spotlight", key=f"add_student_{program}", type="primary"):
                if new_student_name and new_student_name.strip():
                    nm = new_student_name.strip()
                    if not any(s.get("student_name") == nm for s in smartar):
                        smartar.append({"student_name": nm, "notes": ""})
                    if not st.session_state.current_meeting_id:
                        st.session_state[f"_smartar_added_{program}"] = nm
                    st.rerun()
                else:
                    st.warning("⚠️ Please select or enter a student name")

        # After adding, show a clear, reliable link that opens the Goal Builder in a
        # NEW tab (so this meeting form is never lost). Requires a saved meeting id.
        _just_added = st.session_state.pop(f"_smartar_added_{program}", None)
        if st.session_state.current_meeting_id and smartar:
            last = smartar[-1].get("student_name", "")
            if last:
                _url = get_smartar_goal_link(last, st.session_state.current_meeting_id, program, pm_term or "T1", pm_week)
                st.markdown("**Set this student's goal:**")
                smartar_link_button(_url, f"🎯 Open Goal Builder for {last}")
        elif not st.session_state.current_meeting_id:
            st.info("💡 Save the meeting first (button at the bottom) — then a Goal Builder link will appear for each student.")
        
        st.markdown("---")

        st.markdown("#### ⏱ 40–45 min | REPORTS / TAC / TRANSITIONS")
        pm_reports = st.text_area("Reports, TAC meetings, review or transition planning",
            value=default_reports, height=80, key=f"pm_reports_{program}", label_visibility="collapsed",
            placeholder="Upcoming reports due · TAC meetings · Review or transition planning")
        priority_rows = []

    else:  # Week B - System Lens
        st.markdown("#### ⏱ 10–45 min | WEEK B — SYSTEM LENS")
        st.caption("Align to: Implementation Plan · PDP Focus Areas · LBU Priorities")

        priority_key = f"pm_priority_{program}"

        # Initialise from saved record if first load
        if priority_key not in st.session_state:
            raw_pf = selected_record.get('priority_focus', '') if selected_record else ''
            existing_focus = ""
            if raw_pf:
                try:
                    import json as _json_pf
                    pf_data = _json_pf.loads(raw_pf)
                    if isinstance(pf_data, dict):
                        existing_focus = pf_data.get("notes", "")
                    elif isinstance(pf_data, list) and pf_data:
                        lines = []
                        for r in pf_data:
                            if isinstance(r, dict):
                                parts = [v for v in r.values() if v]
                                if parts:
                                    lines.append("• " + " | ".join(parts))
                        existing_focus = "\n".join(lines)
                except Exception:
                    existing_focus = str(raw_pf)
            st.session_state[priority_key] = {"notes": existing_focus}

        priority_store = st.session_state[priority_key]
        if not isinstance(priority_store, dict):
            priority_store = {"notes": ""}
            st.session_state[priority_key] = priority_store

        # ── SINGLE TRANSCRIPT DROP ZONE ────────────────────────────────────
        st.markdown("**📋 Drop Transcript / Raw Notes**")
        st.caption(
            "Paste a voice transcript, rough notes, or dot points from the whole meeting. "
            "AI will read it and split content into the **Focus Area** summary and **Meeting Minutes** below."
        )
        st.caption("⚠️ Keep transcripts under ~3,000 characters for best results with the free Groq tier.")
        transcript_raw = st.text_area(
            "Transcript",
            height=200,
            key=f"pr_transcript_{program}",
            label_visibility="collapsed",
            placeholder=(
                "Paste full meeting transcript or rough notes here…\n\n"
                "e.g. 'We talked about BSEM implementation — Brenton said check-ins are happening but "
                "not all staff using the language consistently. Candice to model it next week. "
                "Also discussed upcoming reports — due end of week 8. Tom will send the template out by Thursday.'"
            )
        )

        if st.button("✨ Process with AI → Split into Focus Area + Minutes", key=f"pr_groq_{program}", type="primary"):
            if transcript_raw.strip():
                if GROQ_KEY:
                    with st.spinner("Reading transcript and sorting content…"):
                        try:
                            _groq_client = Groq(api_key=GROQ_KEY)
                            _prompt = f"""You are a professional minute-taker for Cowandilla Learning Centre (CLC), Learning & Behaviour Unit — an alternative education school in South Australia.

A raw transcript or rough notes from a Week B 'System Lens' team meeting for the {PROGRAMS[program]['label']} program is provided below.

Your job: Read the full transcript and produce TWO clearly separated sections.

---
SECTION 1 — FOCUS AREA SUMMARY
Extract anything about implementation fidelity, frameworks, staff practice, LBU priorities, or systemic/program concerns. Format as:

FOCUS AREA: [topic]
WHAT'S WORKING: [strengths observed]
GAP IDENTIFIED: [what needs attention]
ADJUSTMENT / NEXT STEP: [what will change and how]
EVIDENCE TO COLLECT: [how progress will be measured]
WHO & WHEN: [responsible person and timeline]

Repeat for each distinct focus area discussed.

---
SECTION 2 — MEETING MINUTES
Everything else — general discussion, decisions, announcements, upcoming events, staff matters, reports, TAC, transitions, any other business. Format as clear professional minutes with numbered items.

Rules:
- Trauma-informed, strengths-based, plain English
- Preserve ALL factual content — do not add or fabricate anything
- Be concise — one sentence per point unless more detail is essential
- Clearly label the two sections with the headings above

RAW TRANSCRIPT:
{transcript_raw[:3500]}"""
                            _resp = _groq_client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role": "user", "content": _prompt}],
                                max_tokens=900
                            )
                            full_output = _resp.choices[0].message.content

                            # Split on the SECTION 2 heading
                            split_markers = [
                                "SECTION 2 — MEETING MINUTES",
                                "SECTION 2 - MEETING MINUTES",
                                "---\nSECTION 2",
                                "\n\nSECTION 2",
                            ]
                            focus_text = full_output
                            minutes_text = ""
                            for marker in split_markers:
                                if marker in full_output:
                                    parts = full_output.split(marker, 1)
                                    focus_text = parts[0].replace("SECTION 1 — FOCUS AREA SUMMARY", "").replace("SECTION 1 - FOCUS AREA SUMMARY", "").strip()
                                    minutes_text = parts[1].strip()
                                    break

                            # Stage results — transferred to widget keys before render
                            st.session_state[f"_stage_pr_notes_{program}"] = focus_text
                            st.session_state[f"_stage_pm_minutes_{program}"] = minutes_text
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Groq error: {_e}")
                else:
                    st.warning("⚠️ Groq API key not configured.")
            else:
                st.warning("⚠️ Paste a transcript first.")

        st.markdown("---")

        # ── Focus Area notes (populated by AI or typed manually) ───────────
        st.markdown("**📝 Focus Area Summary**")
        st.caption("AI-populated from your transcript, or type freely. Edit before saving.")
        _stage_pn = st.session_state.pop(f"_stage_pr_notes_{program}", None)
        if _stage_pn is not None:
            st.session_state[f"pr_notes_{program}"] = _stage_pn
        elif f"pr_notes_{program}" not in st.session_state:
            st.session_state[f"pr_notes_{program}"] = priority_store.get("notes", "")
        _focus_notes = st.text_area(
            "Focus area notes",
            height=200,
            key=f"pr_notes_{program}",
            label_visibility="collapsed",
            placeholder=(
                "e.g.\n"
                "FOCUS AREA: BSEM implementation fidelity\n"
                "WHAT'S WORKING: Morning check-ins happening consistently\n"
                "GAP: WoT language not yet embedded in afternoon sessions\n"
                "ADJUSTMENT: Candice to model language at next team meeting\n"
                "EVIDENCE: Scatter Plot regulation data — Brenton by W7"
            )
        )
        # Keep priority_store in sync for save
        priority_store["notes"] = _focus_notes
        st.session_state[priority_key] = priority_store

        # priority_rows used downstream for save
        priority_rows = [{"notes": _focus_notes}]
        st.markdown("---")

        # SMARTAR for Week B (same as Week A)
        st.markdown("#### ⏱ SMARTAR GOAL SPOTLIGHT — 4 Students")
        st.caption("Click student name to open Goal Builder, or add new student")

        if not st.session_state.current_meeting_id:
            st.info("💡 Save the meeting details above first — SMARTAR links will activate once the meeting has an ID.")

        if student_names:
            st.caption(f"💡 {len(student_names)} students loaded")

        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = []

        smartar = st.session_state[smartar_key]
        
        # Display existing students with their CURRENT SMARTAR goal + notes
        if smartar:
            hdr_l, hdr_r = st.columns([5, 1])
            with hdr_r:
                st.button("↻ Refresh goals", key=f"refresh_goals_b_{program}",
                          on_click=fetch_student_smartar_goals.clear,
                          help="Reload current goals from the Goal Builder")
            for idx, student_data in enumerate(smartar):
                student_name = student_data.get("student_name", "")
                if not student_name:
                    continue

                col_name, col_goal_btn, col_remove = st.columns([4, 2, 0.5])
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
                        smartar_link_button(smartar_url)
                    else:
                        st.caption("Save meeting first")
                with col_remove:
                    if st.button("✕", key=f"sm_remove_b_{program}_{idx}"):
                        smartar.pop(idx)
                        st.rerun()

                # Show the student's CURRENT SMARTAR goal(s) inline
                render_current_smartar_goals(student_name)

                # Meeting notes recorded alongside the goal
                student_data["notes"] = st.text_area(
                    f"Notes for {student_name}",
                    value=student_data.get("notes", ""),
                    key=f"sm_notes_b_{program}_{idx}",
                    height=80,
                    placeholder="Notes alongside this goal — progress, evidence, adjustments, next steps…",
                    label_visibility="collapsed"
                )
                st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

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
            if st.button("➕ Add to spotlight", key=f"add_student_b_{program}", type="primary"):
                if new_student_name and new_student_name.strip():
                    nm = new_student_name.strip()
                    if not any(s.get("student_name") == nm for s in smartar):
                        smartar.append({"student_name": nm, "notes": ""})
                    st.rerun()
                else:
                    st.warning("⚠️ Please select or enter a student name")

        if st.session_state.current_meeting_id and smartar:
            last = smartar[-1].get("student_name", "")
            if last:
                _url = get_smartar_goal_link(last, st.session_state.current_meeting_id, program, pm_term or "T1", pm_week)
                st.markdown("**Set this student's goal:**")
                smartar_link_button(_url, f"🎯 Open Goal Builder for {last}")
        elif not st.session_state.current_meeting_id:
            st.info("💡 Save the meeting first (button at the bottom) — then a Goal Builder link will appear for each student.")

        pm_reports = ""
        concerns = []

    st.markdown("---")

    # MEETING MINUTES / NOTES SECTION
    st.markdown("#### 📝 MEETING MINUTES / NOTES")
    st.caption("For Week B: AI-populated from transcript above. For Week A: type manually. Edit freely before saving.")
    
    # Check for AI-generated minutes
    if st.session_state.get(f'_ai_minutes_{program}'):
        st.markdown("**🤖 AI Generated Minutes:**")
        ai_minutes = st.session_state[f'_ai_minutes_{program}']
        
        edited_minutes = st.text_area(
            "Review minutes",
            value=ai_minutes,
            height=200,
            key=f"review_minutes_{program}",
            label_visibility="collapsed"
        )
        
        col_accept, col_reject = st.columns(2)
        with col_accept:
            if st.button("✅ Accept Minutes", key=f"accept_minutes_{program}", type="primary"):
                st.session_state[f"pm_minutes_{program}"] = edited_minutes
                del st.session_state[f'_ai_minutes_{program}']
                st.success("Minutes accepted!")
                time.sleep(0.5)
                st.rerun()
        with col_reject:
            if st.button("❌ Discard", key=f"reject_minutes_{program}"):
                del st.session_state[f'_ai_minutes_{program}']
                st.rerun()
    else:
        # Regular minutes entry
        default_minutes = selected_record.get('meeting_minutes', '') if selected_record else ''
        _stage_min = st.session_state.pop(f"_stage_pm_minutes_{program}", None)
        if _stage_min is not None:
            st.session_state[f"pm_minutes_{program}"] = _stage_min
        elif f"pm_minutes_{program}" not in st.session_state:
            st.session_state[f"pm_minutes_{program}"] = default_minutes
        pm_minutes = st.text_area(
            "Meeting minutes",
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
    
    # AI-suggested actions review
    if st.session_state.get(f'_ai_actions_{program}'):
        st.markdown("**🤖 AI Suggested Actions — Review & Add:**")
        ai_actions = st.session_state[f'_ai_actions_{program}']
        
        if ai_actions:
            for ai_idx, ai_action in enumerate(ai_actions):
                cols = st.columns([3, 1.5, 1, 1, 0.7])
                cols[0].text_input("Action", value=ai_action.get('action', ''), key=f"ai_act_{program}_{ai_idx}", label_visibility="collapsed")
                cols[1].text_input("Who", value=ai_action.get('who', ''), key=f"ai_who_{program}_{ai_idx}", label_visibility="collapsed")
                cols[2].text_input("When", value=ai_action.get('by_when', ''), key=f"ai_when_{program}_{ai_idx}", label_visibility="collapsed")
                cols[3].selectbox("Pri", ["Low", "Medium", "High", "Urgent"], 
                                 index=["Low", "Medium", "High", "Urgent"].index(ai_action.get('priority', 'Medium')),
                                 key=f"ai_pri_{program}_{ai_idx}", label_visibility="collapsed")
                if cols[4].button("✅", key=f"add_ai_{program}_{ai_idx}"):
                    actions.append({
                        "action": st.session_state[f"ai_act_{program}_{ai_idx}"],
                        "who": st.session_state[f"ai_who_{program}_{ai_idx}"],
                        "by_when": st.session_state[f"ai_when_{program}_{ai_idx}"],
                        "priority": st.session_state[f"ai_pri_{program}_{ai_idx}"],
                        "notes": "",
                        "done": False
                    })
                    st.success("Action added!")
                    time.sleep(0.3)
                    st.rerun()
        
        col_all, col_clear = st.columns(2)
        with col_all:
            if st.button("✅ Accept All Actions", key=f"accept_all_actions_{program}", type="primary"):
                for ai_action in ai_actions:
                    actions.append({
                        "action": ai_action.get('action', ''),
                        "who": ai_action.get('who', ''),
                        "by_when": ai_action.get('by_when', ''),
                        "priority": ai_action.get('priority', 'Medium'),
                        "notes": "",
                        "done": False
                    })
                del st.session_state[f'_ai_actions_{program}']
                st.success(f"Added {len(ai_actions)} actions!")
                time.sleep(0.5)
                st.rerun()
        with col_clear:
            if st.button("Clear Suggestions", key=f"clear_actions_{program}"):
                del st.session_state[f'_ai_actions_{program}']
                st.rerun()
        
        st.markdown("---")
    
    # Existing actions display
    st.markdown("**Current Actions:**")

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
        actions.append({"action":"","who":"","by_when":"","priority":"Medium","notes":"","done":False})
        st.rerun()
    
    # Multiple add option
    col_add_multi, col_button = st.columns([3, 1])
    with col_add_multi:
        num_actions = st.number_input("Add multiple actions", min_value=1, max_value=10, value=3, 
                                     key=f"num_add_{program}", label_visibility="collapsed")
    with col_button:
        if st.button(f"➕ Add {num_actions} Actions", key=f"add_multi_{program}"):
            for _ in range(num_actions):
                actions.append({"action":"","who":"","by_when":"","priority":"Medium","notes":"","done":False})
            st.rerun()
    
    st.markdown("---")

    # Prepare meeting data for save - FIXED: Use local variables instead of session state
    smartar_data = [{"student_name": r.get("student_name",""), "notes": r.get("notes","")} for r in smartar]
    actions_data = [{k: v for k, v in a.items() if k != "_id"} for a in actions]

    # Robustly capture student concerns straight from each row's widget by its
    # stable id — this guarantees every student typed in (including the 2nd, 3rd…)
    # is saved, and that empty rows are dropped.
    if is_week_a:
        concerns_data = []
        for r in concerns:
            cid = r.get("_id")
            note = st.session_state.get(f"con_notes_{program}_{cid}", r.get("notes", "")) if cid else r.get("notes", "")
            if note and note.strip():
                concerns_data.append({"notes": note.strip()})
    else:
        concerns_data = []
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
    editing_existing = bool(st.session_state.current_meeting_id) and not str(st.session_state.current_meeting_id).startswith("temp_")
    save_button_text = "💾 Update Meeting Record" if editing_existing else "💾 Save Meeting Record"
    if st.button(save_button_text, type="primary", use_container_width=True, key=f"pm_save_{program}"):
        try:
            saved_id = None
            if editing_existing:
                supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                saved_id = st.session_state.current_meeting_id
                st.success("✅ Meeting record updated!")
            else:
                # DUPLICATE GUARD — never create a 2nd copy of a meeting that already
                # exists for the same date / term / week / type.
                existing = find_existing_meetings(
                    program, meeting_data["meeting_date"], meeting_data["week_type"],
                    meeting_data["term"], meeting_data["week_number"]
                )
                if existing:
                    saved_id = existing[0]['id']
                    supabase.table('tm_program_meetings').update(meeting_data).eq('id', saved_id).execute()
                    if len(existing) > 1:
                        dup_ids = ", ".join(str(e['id']) for e in existing[1:])
                        st.warning(
                            f"⚠️ {len(existing)} saved copies of this meeting already exist "
                            f"(same date / term / week / type). I updated the most recent one rather "
                            f"than adding another. Extra copies still in the database — IDs: {dup_ids}. "
                            f"Use the **Duplicate check** banner at the top of this tab to remove them."
                        )
                    else:
                        st.success("✅ A meeting for this date already existed — updated it instead of creating a duplicate.")
                else:
                    result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
                    saved_id = result.data[0]['id'] if result.data else None
                    st.success("✅ Meeting record saved!")

            # Keep the just-saved meeting loaded so you can carry on editing — this is
            # what previously made it look like a student had been 'lost'. The Select
            # Meeting dropdown re-selects it automatically from current_meeting_id
            # (index-driven), so no widget-key write is needed here.
            if saved_id:
                st.session_state.current_meeting_id = saved_id

            st.session_state.last_autosave_time = None
            st.session_state.autosave_message = ""
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Database save failed: {e}")

    # ── Download professional minutes (Word) ──────────────────────────────────
    st.markdown("")
    try:
        _docx_buf = build_minutes_docx(meeting_data, program)
        _fname = f"CLC_{program}_Minutes_{meeting_data['meeting_date']}_Week{meeting_data['week_type']}.docx"
        st.download_button(
            "📥 Download Minutes (Word) — ready to send to members",
            data=_docx_buf,
            file_name=_fname,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key=f"pm_download_{program}",
        )
        st.caption("Tip: save first so the download matches the stored record exactly.")
    except Exception as _e:
        st.caption(f"Minutes document could not be generated: {_e}")


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

        in_edit_mode = st.session_state.get(edit_key, False)
        with st.expander(header, expanded=in_edit_mode):

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
                col_edit_btn, col_dl_btn = st.columns(2)
                with col_edit_btn:
                    if st.button("✏️ Edit / Add to This Meeting", key=f"arch_open_{meeting_id}", type="secondary", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()
                with col_dl_btn:
                    try:
                        _abuf = build_minutes_docx(meeting, program)
                        st.download_button(
                            "📥 Download Minutes (Word)",
                            data=_abuf,
                            file_name=f"CLC_{program}_Minutes_{meeting_date}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key=f"arch_dl_{meeting_id}",
                        )
                    except Exception as _e:
                        st.caption(f"Minutes doc error: {_e}")

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
                    _stage_pf = st.session_state.pop(f"_stage_arch_pf_{meeting_id}", None)
                    if _stage_pf is not None:
                        st.session_state[f"arch_pf_{meeting_id}"] = _stage_pf
                    elif f"arch_pf_{meeting_id}" not in st.session_state:
                        st.session_state[f"arch_pf_{meeting_id}"] = existing_pf
                    ed_pf = st.text_area(
                        "Priority focus",
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
                                            model="llama-3.1-8b-instant",
                                            messages=[{"role": "user", "content":
                                                f"Transform these rough meeting notes into structured CLC focus-area minutes. "
                                                f"Use headings: FOCUS AREA, WHAT'S WORKING, GAP, ADJUSTMENT, EVIDENCE, WHO & WHEN. "
                                                f"Trauma-informed, strengths-based, plain English. Preserve all facts.\n\n{arch_transcript[:3000]}"}],
                                            max_tokens=800
                                        )
                                        _new_text = _r.choices[0].message.content
                                        st.session_state[f"_stage_arch_pf_{meeting_id}"] = (ed_pf + "\n\n--- AI ---\n" + _new_text).strip() if ed_pf.strip() else _new_text
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
                # Pending key carries Groq output across reruns without touching the widget key
                _stage_am = st.session_state.pop(f"_stage_arch_min_{meeting_id}", None)
                if _stage_am is not None:
                    st.session_state[f"arch_minutes_{meeting_id}"] = _stage_am
                elif f"arch_minutes_{meeting_id}" not in st.session_state:
                    st.session_state[f"arch_minutes_{meeting_id}"] = meeting.get('meeting_minutes', '') or ''
                ed_minutes = st.text_area(
                    "Meeting minutes",
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
                                        model="llama-3.1-8b-instant",
                                        messages=[{"role": "user", "content":
                                            f"Transform these notes into polished professional meeting minutes for "
                                            f"Cowandilla Learning Centre ({PROGRAMS[program]['label']} team meeting, {meeting_date}). "
                                            f"Structured, trauma-informed, plain English. Preserve all facts.\n\n{arch_min_transcript[:3000]}"}],
                                        max_tokens=900
                                    )
                                    _new_min = _r2.choices[0].message.content
                                    st.session_state[f"_stage_arch_min_{meeting_id}"] = (
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

                st.caption("Add new action (will be included when you save):")
                new_act_cols = st.columns([3, 1.5, 1, 1])
                new_act_action = new_act_cols[0].text_input("Action", key=f"arch_new_act_{meeting_id}", label_visibility="collapsed", placeholder="New action item")
                new_act_who   = new_act_cols[1].text_input("Who",    key=f"arch_new_who_{meeting_id}", label_visibility="collapsed", placeholder="Person")
                new_act_when  = new_act_cols[2].text_input("By",     key=f"arch_new_when_{meeting_id}", label_visibility="collapsed", placeholder="Date/week")
                new_act_pri   = new_act_cols[3].selectbox("Pri",     ["Medium","Low","High","Urgent"], key=f"arch_new_pri_{meeting_id}", label_visibility="collapsed")

                # NOTE: new action is appended only inside the Save block below, not here,
                # to prevent it being duplicated on every rerun.

                st.markdown("---")

                # ── Save / Cancel ──
                col_sv, col_cn = st.columns([1, 1])
                with col_sv:
                    if st.button("💾 Save All Changes", key=f"arch_save_{meeting_id}", type="primary", use_container_width=True):
                        # Append new action only at save time
                        if new_act_action.strip():
                            existing_actions.append({
                                "action": new_act_action.strip(),
                                "who": new_act_who.strip(),
                                "by_when": new_act_when.strip(),
                                "priority": new_act_pri,
                                "done": False
                            })
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
