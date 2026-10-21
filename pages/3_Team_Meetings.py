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

# Auth/login removed - portal now open to all staff
# (To re-enable: uncomment require_auth and logout_button calls below)

def _safe_staff_name():
    """Facilitator default — returns empty string (auth removed)."""
    return ""

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

# ── Groq token-budget guard ────────────────────────────────────────────────────
# The Groq account is on the on_demand tier. openai/gpt-oss-120b's cap is
# 8,000 tokens/minute total, shared across prompt + requested output.
# A safety margin is applied on top of 8,000 cap.
GROQ_TPM_LIMIT = 8000

def _fit_to_groq_budget(text: str, max_tokens: int, prompt_overhead_tokens: int = 400,
                        tpm_limit: int = GROQ_TPM_LIMIT) -> tuple[str, bool]:
    """Truncate text so prompt_overhead + text + max_tokens stays under the
    account's TPM limit, with a safety margin. Returns (possibly-truncated
    text, was_truncated)."""
    CHARS_PER_TOKEN = 4  # rough estimate for English text
    SAFETY_MARGIN = 0.85  # headroom for the estimate above being approximate
    input_token_budget = (tpm_limit - max_tokens - prompt_overhead_tokens) * SAFETY_MARGIN
    char_budget = max(0, int(input_token_budget)) * CHARS_PER_TOKEN
    if len(text) <= char_budget:
        return text, False
    return text[:char_budget], True

# ── Meeting sections fixed structure ───────────────────────────────────────────
# For Week A/B meetings: fixed sections for parsing/rebuilding organized content
MEETING_SECTIONS = [
    ("items_discussed", "Items Discussed"),
    ("actions", "Actions"),
]
_NIL_TEXT = "Nil discussed this meeting."

def _parse_meeting_sections(content: str) -> dict:
    """Split organized content into per-section text using ===SECTION=== headers.
    Missing sections return blank rather than erroring."""
    import re
    result = {key: "" for key, _ in MEETING_SECTIONS}
    if not content:
        return result
    
    for key, label in MEETING_SECTIONS:
        pattern = rf"==={re.escape(label)}===\n(.*?)(?===\w|$)"
        m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            result[key] = val if val and val != _NIL_TEXT else ""
    return result

def _build_meeting_sections(section_values: dict) -> str:
    """Combine section fields into one organized document."""
    parts = []
    for key, label in MEETING_SECTIONS:
        content = (section_values.get(key) or "").strip() or _NIL_TEXT
        parts.append(f"==={label}===\n{content}")
    return "\n\n".join(parts)


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
# WORD DOCUMENT GENERATION FOR MEETING MINUTES
# ─────────────────────────────────────────────────────────────────────────────

def generate_minutes_docx(program, meeting_date, facilitator, attendees, extracted_notes, summary_notes, transcript):
    """Generate professional Word document matching CLC LBU minutes format"""
    doc = Document()
    
    # ── Base style ──
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(31, 41, 55)  # Dark gray
    
    for section in doc.sections:
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
    
    # ── Title band (matching CLC LBU format) ──
    title = doc.add_heading("Cowandilla Learning Centre", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title_run = title.runs[0]
    title_run.font.color.rgb = RGBColor(0, 128, 128)  # Teal
    title_run.font.size = Pt(18)
    
    sub = doc.add_paragraph("Learning & Behaviour Unit")
    sub_run = sub.runs[0]
    sub_run.font.size = Pt(10.5)
    sub_run.font.color.rgb = RGBColor(107, 114, 128)  # Gray
    
    prog_label = PROGRAMS.get(program, {}).get("label", program)
    meeting_type = doc.add_paragraph(f"{prog_label}  ·  Ad-Hoc Meeting")
    meeting_type_run = meeting_type.runs[0]
    meeting_type_run.bold = True
    meeting_type_run.font.size = Pt(12)
    meeting_type_run.font.color.rgb = RGBColor(217, 119, 6)  # Amber/Gold
    
    # Horizontal rule
    doc.add_paragraph("_" * 80).paragraph_format.space_after = Pt(6)
    
    # ── Meeting Details Table ──
    details = [
        ("Date", str(meeting_date)),
        ("Facilitator", facilitator or ""),
        ("Attendees", attendees or "Not recorded"),
    ]
    
    tbl = doc.add_table(rows=len(details), cols=2)
    tbl.style = 'Light Grid Accent 1'
    
    for i, (label, value) in enumerate(details):
        c0, c1 = tbl.rows[i].cells
        c0.width = Cm(3.5)
        c1.width = Cm(13.0)
        
        # Style left column
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(1)
        run0 = p0.add_run(label)
        run0.bold = True
        run0.font.size = Pt(9.5)
        run0.font.color.rgb = RGBColor(0, 128, 128)
        
        # Style right column
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(1)
        run1 = p1.add_run(str(value))
        run1.font.size = Pt(10)
        run1.font.color.rgb = RGBColor(31, 41, 55)
    
    doc.add_paragraph()
    doc.add_paragraph()
    
    # ── Meeting Minutes / Key Points ──
    heading = doc.add_heading("Meeting Minutes", level=1)
    heading_run = heading.runs[0]
    heading_run.font.color.rgb = RGBColor(0, 128, 128)
    
    if extracted_notes and extracted_notes.strip():
        doc.add_paragraph(extracted_notes)
    elif summary_notes and summary_notes.strip():
        doc.add_paragraph(summary_notes)
    else:
        p = doc.add_paragraph("No meeting summary recorded")
        p.runs[0].italic = True
    
    # ── Full Transcript (removed - not needed in final minutes) ──
    
    # ── Footer ──
    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.paragraph_format.space_before = Pt(12)
    
    footer_run = footer.add_run(f"Minutes generated from the CLC LBU Portal · {datetime.datetime.now().strftime('%A, %d %B %Y')}")
    footer_run.italic = True
    footer_run.font.size = Pt(9)
    footer_run.font.color.rgb = RGBColor(107, 114, 128)
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    return doc

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
    default_facilitator = selected_record.get('facilitator', _safe_staff_name()) if selected_record else _safe_staff_name()
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

    # ── AD-HOC MEETINGS FOR SPECIALIST ────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📝 Ad-Hoc Specialist Meetings")
    st.caption("Quick notes from unscheduled or urgent specialist team conversations")
    
    active_tab, archive_tab = st.tabs(["📋 Active Meetings", "📚 Archive"])
    
    with active_tab:
        try:
            # Load active ad-hoc meetings for Specialist
            active_meetings = supabase.table('tm_program_meetings').select("*").eq('program', 'SPECIALIST').eq('week_type', 'ad-hoc').order('meeting_date', desc=True).execute()
            active_adhoc = active_meetings.data or []
            
            if active_adhoc:
                st.markdown("**Click to open and manage:**")
                for mtg in active_adhoc:
                    mtg_date = mtg.get('meeting_date', '')
                    mtg_facilitator = mtg.get('facilitator', '')
                    mtg_id = mtg.get('id', '')
                    
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        if st.button(f"📝 {mtg_date} — {mtg_facilitator}", key=f"load_active_{mtg_id}", use_container_width=True):
                            st.session_state.current_meeting_id = mtg_id
                            st.rerun()
                    
                    with col2:
                        if st.button("👁️ View", key=f"view_active_{mtg_id}", use_container_width=True):
                            st.info(f"**{mtg_facilitator}** | {mtg_date}\n\n{mtg.get('checkin_notes', '[No notes]')}")
                    
                    with col3:
                        if st.button("📥 Download", key=f"dl_active_{mtg_id}", use_container_width=True):
                            doc = generate_minutes_docx(
                                program='SPECIALIST',
                                meeting_date=mtg_date,
                                facilitator=mtg_facilitator,
                                attendees=mtg.get('attendees', ''),
                                extracted_notes=mtg.get('checkin_notes', ''),
                                summary_notes=mtg.get('reports_tac_notes', ''),
                                transcript=mtg.get('meeting_minutes', '')
                            )
                            doc_bytes = io.BytesIO()
                            doc.save(doc_bytes)
                            doc_bytes.seek(0)
                            st.download_button(
                                label="📥 Download",
                                data=doc_bytes,
                                file_name=f"Minutes_{mtg_date}_{mtg_facilitator}_Specialist.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_doc_{mtg_id}"
                            )
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_active_{mtg_id}", use_container_width=True):
                            if st.session_state.get(f"confirm_delete_{mtg_id}", False):
                                try:
                                    supabase.table('tm_program_meetings').delete().eq('id', mtg_id).execute()
                                    st.success(f"🗑️ Deleted")
                                except Exception as e:
                                    st.error(f"Error: {e}")
                            else:
                                st.session_state[f"confirm_delete_{mtg_id}"] = True
                                st.warning("Click again to confirm")
            else:
                st.info("No active ad-hoc specialist meetings yet")
        except Exception as e:
            st.error(f"Could not load active meetings: {e}")
    
    with archive_tab:
        st.info("Ad-hoc specialist meetings can be deleted when no longer needed.")
    
    # ── NEW AD-HOC MEETING FORM ────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ➕ Record New Ad-Hoc Specialist Meeting")
    
    adhoc_col1, adhoc_col2, adhoc_col3, adhoc_col4 = st.columns(4)
    
    with adhoc_col1: adhoc_date = st.date_input("Date", key="adhoc_date_SPECIALIST")
    with adhoc_col2: adhoc_term = st.text_input("Term", placeholder="e.g. Term 1", key="adhoc_term_SPECIALIST")
    with adhoc_col3: adhoc_facilitator = st.text_input("Facilitator", key="adhoc_fac_SPECIALIST")
    with adhoc_col4: adhoc_attendees = st.text_input("Attendees", placeholder="Names", key="adhoc_att_SPECIALIST")
    
    st.markdown("##### 📝 Meeting Notes")
    adhoc_notes = st.text_area(
        "Meeting details, decisions, action items",
        height=150,
        key="adhoc_notes_SPECIALIST",
        placeholder="Paste your meeting notes here...",
        label_visibility="collapsed"
    )
    
    if st.button("💾 Save Ad-Hoc Meeting", type="primary", use_container_width=True, key="save_adhoc_SPECIALIST"):
        if not adhoc_notes.strip():
            st.error("Please add meeting notes")
        else:
            try:
                meeting_payload = {
                    'program': 'SPECIALIST',
                    'meeting_date': str(adhoc_date),
                    'term': adhoc_term.strip(),
                    'week_type': 'ad-hoc',
                    'facilitator': adhoc_facilitator.strip(),
                    'attendees': adhoc_attendees.strip(),
                    'checkin_notes': adhoc_notes.strip(),
                    'student_concerns': _json.dumps([]),
                    'smartar_spotlight': _json.dumps([]),
                    'reports_tac_notes': adhoc_notes.strip(),
                    'priority_focus': _json.dumps([]),
                    'meeting_minutes': adhoc_notes.strip(),
                    'actions': _json.dumps([]),
                }
                
                result = supabase.table('tm_program_meetings').insert(meeting_payload).execute()
                if result.data:
                    st.success(f"✅ Ad-Hoc Meeting Saved (ID: {result.data[0]['id']})")
                    st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAM MEETING (JP/PY/SY) - WITH SMARTAR INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# PROGRAM MEETINGS (v2) — one structure for every meeting type
# Student Lens, System Lens and Ad-Hoc all share the same sections:
#   1. Meeting details (type is ticked here)
#   2. Agenda items (optional, set before the meeting)
#   3. Transcript or summary (paste or upload)
#   4. Minutes (generated from 2 + 3, editable, Polisher-style)
#   5. Save & download
# Records stay in tm_program_meetings. Old records are never rewritten on
# open — they are only changed when you press Save.
# ─────────────────────────────────────────────────────────────────────────────
import re

MEETING_TYPES = {
    "student": {"label": "Student Lens",   "week_type": "A",      "icon": "🔵"},
    "system":  {"label": "System Lens",    "week_type": "B",      "icon": "🟡"},
    "adhoc":   {"label": "Ad-Hoc Meeting", "week_type": "ad-hoc", "icon": "⚪"},
}
_TYPE_FROM_WEEK = {"A": "student", "B": "system", "ad-hoc": "adhoc"}
_PM_MINUTES_MODEL = "openai/gpt-oss-120b"
_PM_OPTIONAL_COLS = ("agenda_items", "source_transcript")

_PM_EXTRACT_SYSTEM = """You are recording the minutes of a school team meeting at Cowandilla Learning Centre (an alternative education setting in South Australia). You are given ONE PART of a transcript or summary. Record what is in THIS part only and return JSON only.

Rules:
- Do NOT summarise or shorten. Capture every substantive point, update, concern, question, decision and idea. Keep the names, dates, figures, student references and key wording used. Write each point as one complete sentence. A part with many points should give many points.
- ACTIONS: capture EVERY task, follow-up, commitment or request, however casually it is said ("I'll...", "can you...", "we need to...", "let's...", "by Friday", "next week", "I'm going to..."). Actions are often mentioned in passing, so check the whole part. For each: "who" is the person responsible, as named in the transcript ("Not stated" if unclear); "due" is any date or timing mentioned ("Not stated" if none).
- ARISING: matters that refer back to an earlier meeting or earlier decision.
- Do not invent anything. Leave out small talk and pleasantries.
- Return ONLY this JSON object, with exactly these keys:
{"items": [{"agenda": 0, "topic": "short title", "points": ["complete sentence", "..."]}], "arising": ["..."], "actions": [{"action": "...", "who": "...", "due": "..."}], "next_meeting": ""}
- "agenda" is the number of the agenda item the points belong to, using the numbers given by the user. Use 0 if the points are not on the agenda or no agenda was given."""


def _pm_chunks(text, size=9000):
    """Split a transcript into parts of roughly `size` characters on line breaks,
    so no part is too big for the AI's per-minute token limit."""
    chunks, cur, n = [], [], 0
    for ln in (text or "").splitlines(keepends=True):
        while len(ln) > size:
            if cur:
                chunks.append("".join(cur))
                cur, n = [], 0
            chunks.append(ln[:size])
            ln = ln[size:]
        if n + len(ln) > size and cur:
            chunks.append("".join(cur))
            cur, n = [], 0
        cur.append(ln)
        n += len(ln)
    if cur:
        chunks.append("".join(cur))
    return [c for c in chunks if c.strip()]


def _pm_call(client, messages, max_tokens=2500):
    """One Groq call with rate-limit waiting. Requests low reasoning effort so the
    model's thinking does not use up the output budget."""
    for _attempt in range(6):
        try:
            try:
                resp = client.chat.completions.create(
                    model=_PM_MINUTES_MODEL, messages=messages, temperature=0.1,
                    max_tokens=max_tokens, reasoning_effort="low",
                )
            except Exception as e:
                if "reasoning" in str(e).lower() and "rate" not in str(e).lower():
                    resp = client.chat.completions.create(
                        model=_PM_MINUTES_MODEL, messages=messages, temperature=0.1, max_tokens=max_tokens,
                    )
                else:
                    raise
            return resp.choices[0].message.content or ""
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate limit" in msg.lower():
                wait = 20.0
                m = re.search(r"try again in ([\d.]+)\s*(ms|s)\b", msg)
                if m:
                    wait = float(m.group(1)) / (1000.0 if m.group(2) == "ms" else 1.0) + 2.0
                time.sleep(min(wait, 90.0))
                continue
            raise
    raise RuntimeError("The AI service is still rate-limited. Wait a minute and try again.")


def _pm_parse_json(raw):
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    a, b = s.find("{"), s.rfind("}")
    if a == -1 or b == -1:
        return None
    try:
        data = json.loads(s[a:b + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _pm_as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    return [x for x in v if x is not None]


def _pm_generate_minutes(program, meeting_date, facilitator, attendees, agenda_text, source_text, type_label, progress=None):
    """Read the transcript part by part, keep every point and action, then build
    Polisher-style minutes in code (no second AI pass that could shorten them)."""
    client = Groq(api_key=GROQ_KEY)
    agenda_lines = [a.strip() for a in (agenda_text or "").splitlines() if a.strip()]
    agenda_block = (
        "\n".join(f"{i}. {a}" for i, a in enumerate(agenda_lines, 1))
        if agenda_lines else "None set. Use agenda 0 for every point."
    )
    parts = _pm_chunks(source_text)
    if not parts:
        raise ValueError("The transcript is empty.")

    results = []
    for n, part in enumerate(parts, 1):
        if progress:
            progress(n - 1, len(parts))
        user = (
            f"Program: {PROGRAMS[program]['label']} ({program}). Meeting type: {type_label}. Date: {meeting_date}.\n\n"
            f"AGENDA ITEMS (in order):\n{agenda_block}\n\n"
            f"THIS IS PART {n} OF {len(parts)} OF THE TRANSCRIPT:\n{part}"
        )
        parsed = None
        for _try in range(2):
            raw = _pm_call(client, [
                {"role": "system", "content": _PM_EXTRACT_SYSTEM},
                {"role": "user", "content": user},
            ], max_tokens=2500)
            parsed = _pm_parse_json(raw)
            if parsed is not None:
                break
        if parsed is None:
            raise RuntimeError(f"Part {n} of {len(parts)} could not be read by the AI. Try again.")
        results.append(parsed)
        if n < len(parts):
            time.sleep(15)  # keep under the per-minute token limit between parts
    if progress:
        progress(len(parts), len(parts))

    # ── Merge every part, keeping all points and removing only repeated actions
    by_agenda = {i: [] for i in range(1, len(agenda_lines) + 1)}
    other_topics = {}
    arising, actions, seen = [], [], set()
    next_meeting = ""
    total_points = 0
    for res in results:
        for it in _pm_as_list(res.get("items")):
            if not isinstance(it, dict):
                continue
            pts = [str(p).strip() for p in _pm_as_list(it.get("points")) if str(p).strip()]
            total_points += len(pts)
            try:
                ag = int(it.get("agenda") or 0)
            except Exception:
                ag = 0
            if agenda_lines and 1 <= ag <= len(agenda_lines):
                by_agenda[ag].extend(pts)
            else:
                title = str(it.get("topic") or "Discussion").strip() or "Discussion"
                other_topics.setdefault(title, []).extend(pts)
        for a in _pm_as_list(res.get("arising")):
            if str(a).strip():
                arising.append(str(a).strip())
        for a in _pm_as_list(res.get("actions")):
            if not isinstance(a, dict):
                continue
            act = str(a.get("action", "")).strip()
            if not act:
                continue
            key = re.sub(r"\W+", " ", act.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            actions.append({
                "action": act,
                "who": str(a.get("who") or "Not stated").strip() or "Not stated",
                "due": str(a.get("due") or "Not stated").strip() or "Not stated",
            })
        if not next_meeting and str(res.get("next_meeting") or "").strip():
            next_meeting = str(res.get("next_meeting")).strip()

    def _cell(t):
        return str(t).replace("|", "/").replace("\n", " ").strip()

    # Attendance and apologies come from what was entered on the form
    att_lines = [l.strip() for l in (attendees or "").splitlines() if l.strip()]
    apol = [l for l in att_lines if re.match(r"apolog", l, re.I)]
    pres = [l for l in att_lines if not re.match(r"apolog", l, re.I)]
    apol_text = re.sub(r"^apolog\w*\s*[:\-]?\s*", "", " ".join(apol), flags=re.I).strip()

    md = []
    md.append("### Attendance\n" + ("\n".join(pres) if pres else "See attendance record."))
    md.append("### Apologies\n" + (apol_text or "None recorded."))
    md.append("### Arising Business\n" + ("\n".join(f"- {a}" for a in arising) if arising else "Nil."))

    blocks = []
    if agenda_lines:
        for i, title in enumerate(agenda_lines, 1):
            pts = by_agenda.get(i, [])
            body = "\n".join(f"- {p}" for p in pts) if pts else "- No discussion recorded for this item."
            blocks.append(f"{i}. **{title}**\n{body}")
    if other_topics:
        if agenda_lines:
            lines = []
            for topic, pts in other_topics.items():
                for p in pts:
                    lines.append(f"- **{topic}:** {p}")
            blocks.append(f"{len(agenda_lines) + 1}. **Other business**\n" + "\n".join(lines))
        else:
            for k, (topic, pts) in enumerate(other_topics.items(), 1):
                body = "\n".join(f"- {p}" for p in pts) if pts else "- No detail recorded."
                blocks.append(f"{k}. **{topic}**\n{body}")
    md.append("### Items Discussed\n" + ("\n\n".join(blocks) if blocks else "No items recorded."))

    rows = ["| Action | Assigned To | Due |", "|--------|-------------|-----|"]
    for a in actions:
        rows.append(f"| {_cell(a['action'])} | {_cell(a['who'])} | {_cell(a['due'])} |")
    if not actions:
        rows.append("| None identified | | |")
    md.append("### Actions\n" + "\n".join(rows))
    md.append("### Next Meeting\n" + (next_meeting or "To be confirmed."))

    stats = {"parts": len(parts), "points": total_points, "actions": len(actions)}
    return "\n\n".join(md), stats


def _pm_init(key, default):
    """Seed a widget's session value once. Widgets then read from session state."""
    if key not in st.session_state:
        st.session_state[key] = default


def _pm_parse_date(value):
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except Exception:
        return datetime.date.today()


def _pm_label(rec):
    tkey = _TYPE_FROM_WEEK.get(rec.get("week_type"), "")
    tlabel = MEETING_TYPES.get(tkey, {}).get("label", "Meeting")
    wk = f" · Week {rec.get('week_number')}" if rec.get("week_type") in ("A", "B") else ""
    return f"{rec.get('meeting_date', '?')} · {tlabel}{wk} · {rec.get('facilitator') or 'no facilitator'}"


def _pm_legacy_source(rec, program):
    """The transcript/summary a record was built from. Newer records use
    source_transcript; older ad-hoc records kept it in checkin_notes."""
    if program == "SPECIALIST":
        return ""
    if rec.get("source_transcript"):
        return rec["source_transcript"]
    if rec.get("week_type") == "ad-hoc":
        return rec.get("checkin_notes") or ""
    return ""


def _pm_legacy_extras(rec):
    """Earlier-format fields kept on old Week A/B and Specialist records, shown
    read-only so nothing saved before this change disappears from view."""
    parts = []
    checkin = rec.get("checkin_notes") or ""
    if rec.get("week_type") != "ad-hoc" and checkin.strip():
        if rec.get("program") == "SPECIALIST":
            cd = _safe_json(checkin, {})
            if isinstance(cd, dict):
                if cd.get("monday_teacher"):
                    parts.append(f"**Monday teacher:** {cd['monday_teacher']}")
                if cd.get("tuefri_teacher"):
                    parts.append(f"**Tue–Fri teacher:** {cd['tuefri_teacher']}")
        else:
            parts.append(f"**Check-in notes:**\n\n{checkin}")
    sc = _safe_json(rec.get("student_concerns") or "", [])
    if isinstance(sc, list):
        notes = [x.get("notes", "") for x in sc if isinstance(x, dict) and (x.get("notes") or "").strip()]
        if notes:
            parts.append("**Student concerns:**\n\n" + "\n".join(f"- {n}" for n in notes))
    pf = _safe_json(rec.get("priority_focus") or "", {})
    pf_text = pf.get("notes", "") if isinstance(pf, dict) else ""
    if pf_text and pf_text.strip():
        parts.append(f"**Priority focus:**\n\n{pf_text}")
    sm = _safe_json(rec.get("smartar_spotlight") or "", [])
    if isinstance(sm, list):
        names = [
            s.get("student_name") + (f" — {s.get('notes')}" if s.get("notes") else "")
            for s in sm if isinstance(s, dict) and s.get("student_name")
        ]
        if names:
            parts.append("**SMARTAR spotlight:**\n\n" + "\n".join(f"- {n}" for n in names))
    return "\n\n".join(parts)


def _pm_read_upload(up):
    raw = up.getvalue()
    if up.name.lower().endswith(".docx"):
        d = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in d.paragraphs).strip()
    return raw.decode("utf-8", errors="replace").strip()


def _pm_write(payload, mid):
    """Insert or update. If the optional v2 columns are not in the database yet,
    save everything else and report which columns were skipped."""
    tbl = supabase.table("tm_program_meetings")

    def _do(p):
        if mid:
            return tbl.update(p).eq("id", mid).execute()
        return tbl.insert(p).execute()

    try:
        return _do(payload), []
    except Exception as e:
        msg = str(e).lower()
        if "column" in msg and "does not exist" in msg:
            missing = [c for c in _PM_OPTIONAL_COLS if c in msg] or list(_PM_OPTIONAL_COLS)
            slim = {k: v for k, v in payload.items() if k not in _PM_OPTIONAL_COLS}
            return _do(slim), missing
        raise


def _pm_parse_actions(md):
    """Read the rows of the Actions table into a list the app can store."""
    m = re.search(r"###\s*Actions\s*\n(.*?)(?=\n###\s|\Z)", md or "", re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(c and set(c) <= set("-: ") for c in cells):
            continue  # separator row
        if cells and cells[0].lower() == "action":
            continue  # header row
        if any(cells):
            rows.append({
                "action": cells[0],
                "assigned_to": cells[1] if len(cells) > 1 else "",
                "due": cells[2] if len(cells) > 2 else "",
            })
    return rows


# ── Word document (styled like Minutes Polisher) ─────────────────────────────

def _pm_inline(par, text, size_pt=10.5, colour=INK, bold_all=False):
    for part in re.split(r"(\*\*[^*]+\*\*)", text or ""):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            _para_run(par, part[2:-2], bold=True, size_pt=size_pt, colour=colour)
        else:
            _para_run(par, part, bold=bold_all, size_pt=size_pt, colour=colour)


def _pm_add_md(doc, md):
    lines = (md or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or set(line) <= set("-*_"):
            i += 1
            continue
        if line.startswith("#"):
            _doc_heading(doc, line.lstrip("#").strip().replace("**", ""),
                         size=12.5, space_before=12, space_after=3)
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(c and set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                ncols = max(len(r) for r in rows)
                tbl = doc.add_table(rows=len(rows), cols=ncols)
                tbl.style = "Table Grid"
                for r_i, r in enumerate(rows):
                    for c_i in range(ncols):
                        cell = tbl.rows[r_i].cells[c_i]
                        cell.text = ""
                        par = cell.paragraphs[0]
                        par.paragraph_format.space_after = Pt(1)
                        txt = r[c_i] if c_i < len(r) else ""
                        if r_i == 0:
                            _shade_cell(cell, "EAF5F5")
                            _para_run(par, txt.replace("**", ""), bold=True, size_pt=9.5, colour=TEAL)
                        else:
                            _pm_inline(par, txt, size_pt=9.5)
                doc.add_paragraph().paragraph_format.space_after = Pt(2)
            continue
        m = re.match(r"^(\d+)[\.\)]\s+(.*)$", line)
        if m:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.first_line_indent = Cm(-0.6)
            p.paragraph_format.space_after = Pt(4)
            _para_run(p, f"{m.group(1)}.  ", bold=True, size_pt=10.5, colour=AMBER)
            _pm_inline(p, m.group(2))
            i += 1
            continue
        if line[:2] in ("- ", "* "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_after = Pt(3)
            _para_run(p, "•  ", bold=True, colour=AMBER)
            _pm_inline(p, line[2:])
            i += 1
            continue
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        _pm_inline(p, line)
        i += 1


def build_program_minutes_docx(program, meta, minutes_md):
    from io import BytesIO
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = _rgb(INK)
    for s in doc.sections:
        s.top_margin = Cm(1.8)
        s.bottom_margin = Cm(1.8)
        s.left_margin = Cm(2.0)
        s.right_margin = Cm(2.0)

    prog_label = PROGRAMS.get(program, {}).get("label", program)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    _para_run(p, "Cowandilla Learning Centre", bold=True, size_pt=18, colour=TEAL)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    _para_run(p, "Learning & Behaviour Unit", size_pt=10.5, colour=GREY)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    _para_run(p, f"{prog_label}  ·  {meta.get('type_label', 'Meeting')}", bold=True, size_pt=12, colour=AMBER)
    _doc_rule(doc)

    term_week = meta.get("term", "") or ""
    if meta.get("week") not in (None, ""):
        term_week = f"{term_week}  ·  Week {meta.get('week')}"
    details = [
        ("Date", meta.get("date", "") or "—"),
        ("Term / Week", term_week or "—"),
        ("Facilitator", meta.get("facilitator") or "—"),
        ("Attendees", meta.get("attendees") or "Not recorded"),
    ]
    tbl = doc.add_table(rows=len(details), cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, (label, value) in enumerate(details):
        c0, c1 = tbl.rows[i].cells
        c0.width = Cm(3.5)
        c1.width = Cm(13.0)
        _shade_cell(c0, "F1F5F9")
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(1)
        _para_run(p0, label, bold=True, size_pt=9.5, colour=TEAL)
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(1)
        _para_run(p1, str(value), size_pt=10, colour=INK)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

    _pm_add_md(doc, minutes_md)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _pm_filename(program, meta):
    kind = meta.get("type_label", "Meeting").replace(" ", "_")
    return f"{program}_{kind}_Minutes_{meta.get('date', '')}.docx"


# ── Meeting form (one structure for all types) ───────────────────────────────

def render_program_meeting(program):
    auto_term, auto_week = get_current_term_week()

    for kind, msg in st.session_state.pop("pm2_flash", []):
        getattr(st, kind)(msg)

    past = fetch("tm_program_meetings", {"program": program}, "meeting_date")
    by_id = {r["id"]: r for r in past}
    st.session_state.setdefault("pm2_nonce", 0)

    # ── Choose a meeting ─────────────────────────────────────────────────────
    st.markdown("#### 📂 Choose a meeting")
    cur = st.session_state.get("current_meeting_id")
    if cur not in by_id:
        cur = None
    options = [None] + [r["id"] for r in past]
    sel_key = f"pm2_select_{program}_{cur}"

    def _on_select(k=sel_key):
        new_val = st.session_state.get(k)
        st.session_state.current_meeting_id = new_val
        if new_val is None:
            st.session_state.pm2_nonce += 1

    st.selectbox(
        "Meeting",
        options,
        index=options.index(cur),
        format_func=lambda x: "➕ New meeting" if x is None else _pm_label(by_id[x]),
        key=sel_key,
        on_change=_on_select,
    )

    rec = by_id.get(cur) if cur else None
    mid = cur if cur else f"new{st.session_state.pm2_nonce}"

    def K(field):
        return f"pm2_{program}_{mid}_{field}"

    # Seed every field once from the record (or blank for a new meeting)
    d_type = _TYPE_FROM_WEEK.get(rec.get("week_type"), "student") if rec else "student"
    d_date = _pm_parse_date(rec.get("meeting_date")) if rec else datetime.date.today()
    d_term = (rec.get("term") or auto_term) if rec else auto_term
    try:
        d_week = int(rec.get("week_number")) if rec and rec.get("week_number") not in (None, "") else auto_week
    except Exception:
        d_week = auto_week
    _pm_init(K("type"), d_type)
    _pm_init(K("date"), d_date)
    _pm_init(K("term"), d_term)
    _pm_init(K("week"), d_week)
    _pm_init(K("facilitator"), (rec.get("facilitator") or "") if rec else "")
    _pm_init(K("attendees"), (rec.get("attendees") or "") if rec else "")
    _pm_init(K("agenda"), (rec.get("agenda_items") or "") if rec else "")
    _pm_init(K("transcript"), _pm_legacy_source(rec, program) if rec else "")
    minutes_default = (rec.get("meeting_minutes") or "") if rec else ""
    if rec and rec.get("week_type") == "ad-hoc" and minutes_default.strip() == (rec.get("checkin_notes") or "").strip():
        minutes_default = rec.get("reports_tac_notes") or ""  # old ad-hoc: summary lived here
    _pm_init(K("minutes"), minutes_default)

    # 1 ── Meeting details (tick the type) ─────────────────────────────────────
    st.markdown("#### 1️⃣ Meeting details")
    st.radio(
        "Meeting type",
        list(MEETING_TYPES.keys()),
        horizontal=True,
        key=K("type"),
        format_func=lambda k: f"{MEETING_TYPES[k]['icon']} {MEETING_TYPES[k]['label']}",
    )
    c1, c2, c3, c4 = st.columns([1.2, 1, 0.8, 1.6])
    c1.date_input("Date", key=K("date"))
    c2.text_input("Term", key=K("term"), placeholder="T1")
    c3.number_input("Week", min_value=1, max_value=11, step=1, key=K("week"))
    c4.text_input("Facilitator", key=K("facilitator"))
    st.text_area(
        "Attendees and apologies (as recorded)",
        key=K("attendees"),
        height=80,
        placeholder="Present: …\nApologies: …",
    )

    # 2 ── Agenda items (optional) ─────────────────────────────────────────────
    st.markdown("#### 2️⃣ Agenda items (optional)")
    st.text_area(
        "Agenda items, one per line",
        key=K("agenda"),
        height=100,
        placeholder="Leave blank if there is no agenda for this meeting.",
    )

    # 3 ── Transcript or summary ───────────────────────────────────────────────
    st.markdown("#### 3️⃣ Transcript or summary")
    up = st.file_uploader("Upload a transcript (.txt or .docx)", type=["txt", "docx"], key=K("upload"))
    if up is not None:
        sig_key = K("upload_sig")
        sig = f"{up.name}:{up.size}"
        if st.session_state.get(sig_key) != sig:
            try:
                text = _pm_read_upload(up)
                if text:
                    st.session_state[K("transcript")] = text
                    st.session_state[sig_key] = sig
            except Exception as e:
                st.error(f"Could not read that file: {e}")
    st.text_area(
        "Transcript or summary (paste here, or upload above)",
        key=K("transcript"),
        height=260,
    )
    st.caption(f"{len((st.session_state.get(K('transcript')) or '').split())} words captured")

    # 4 ── Minutes ─────────────────────────────────────────────────────────────
    st.markdown("#### 4️⃣ Minutes")
    st.caption("Generating minutes fills the box below. Review and edit before saving. Generating again replaces what is in the box.")
    if st.button("🤖 Generate minutes from transcript", type="primary", key=K("gen"), use_container_width=True):
        src = (st.session_state.get(K("transcript")) or "").strip()
        if not src:
            st.warning("Add a transcript or summary in section 3 first.")
        elif not GROQ_KEY:
            st.warning("GROQ_API_KEY is not configured.")
        else:
            pb = st.progress(0.0, text="Reading transcript…")

            def _pm_progress(done, total, _pb=pb):
                _pb.progress(min(done / total, 1.0) if total else 1.0,
                             text=f"Reading part {min(done + 1, total)} of {total}…")

            try:
                md, stats = _pm_generate_minutes(
                    program,
                    str(st.session_state[K("date")]),
                    st.session_state.get(K("facilitator"), ""),
                    st.session_state.get(K("attendees"), ""),
                    st.session_state.get(K("agenda"), ""),
                    src,
                    MEETING_TYPES[st.session_state[K("type")]]["label"],
                    progress=_pm_progress,
                )
                st.session_state[K("minutes")] = md
                pb.empty()
                st.success(
                    f"Minutes written from {stats['parts']} part(s): {stats['points']} points and "
                    f"{stats['actions']} action(s) captured. Check the actions against the transcript before saving."
                )
            except Exception as e:
                pb.empty()
                st.error(f"Minutes could not be generated: {e}")

    st.text_area("Minutes", key=K("minutes"), height=460, label_visibility="collapsed")
    with st.expander("👁️ Preview formatted minutes"):
        preview = st.session_state.get(K("minutes")) or ""
        st.markdown(preview if preview.strip() else "_No minutes yet._")

    # 5 ── Save & download ─────────────────────────────────────────────────────
    st.markdown("#### 5️⃣ Save & download")
    b1, b2 = st.columns(2)
    save_clicked = b1.button("💾 Save meeting", type="primary", key=K("save"), use_container_width=True)

    if save_clicked:
        week_type = MEETING_TYPES[st.session_state[K("type")]]["week_type"]
        minutes_text = (st.session_state.get(K("minutes")) or "").strip()
        source_text = (st.session_state.get(K("transcript")) or "").strip()
        if not minutes_text and not source_text:
            st.error("Add a transcript or write minutes before saving.")
        else:
            payload = {
                "program": program,
                "meeting_date": str(st.session_state[K("date")]),
                "term": (st.session_state.get(K("term")) or "").strip(),
                "week_number": int(st.session_state[K("week")]),
                "week_type": week_type,
                "facilitator": (st.session_state.get(K("facilitator")) or "").strip(),
                "attendees": (st.session_state.get(K("attendees")) or "").strip(),
                "agenda_items": (st.session_state.get(K("agenda")) or "").strip(),
                "source_transcript": source_text,
                "meeting_minutes": minutes_text,
                "actions": json.dumps(_pm_parse_actions(minutes_text)),
            }
            if rec is None:
                # New rows need the legacy columns to hold a value
                payload.update({
                    "checkin_notes": "",
                    "reports_tac_notes": "",
                    "student_concerns": json.dumps([]),
                    "smartar_spotlight": json.dumps([]),
                    "priority_focus": json.dumps([]),
                })
            ok, result, missing = True, None, []
            try:
                result, missing = _pm_write(payload, cur)
            except Exception as e:
                ok = False
                st.error(f"Save failed: {e}")
            if ok:
                flash = [("success", "✅ Meeting saved." if rec is None else "✅ Meeting updated.")]
                if rec is None and result.data:
                    st.session_state.current_meeting_id = result.data[0]["id"]
                if missing:
                    flash.append((
                        "warning",
                        f"Saved the minutes, but the database has no '{', '.join(missing)}' column yet, "
                        "so the agenda and/or transcript were not stored. Run "
                        "migration_tm_program_meetings_v2.sql in Supabase, then save again."
                    ))
                st.session_state.pm2_flash = flash
                st.rerun()

    minutes_now = st.session_state.get(K("minutes")) or ""
    meta_now = {
        "date": str(st.session_state.get(K("date"), "")),
        "term": st.session_state.get(K("term"), ""),
        "week": st.session_state.get(K("week")) if MEETING_TYPES[st.session_state.get(K("type"), "student")]["week_type"] != "ad-hoc" else "",
        "facilitator": st.session_state.get(K("facilitator"), ""),
        "attendees": st.session_state.get(K("attendees"), ""),
        "type_label": MEETING_TYPES[st.session_state.get(K("type"), "student")]["label"],
    }
    if minutes_now.strip():
        b2.download_button(
            "📥 Download minutes (.docx)",
            data=build_program_minutes_docx(program, meta_now, minutes_now),
            file_name=_pm_filename(program, meta_now),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=K("dl"),
            use_container_width=True,
        )
    else:
        b2.button("📥 Download minutes (.docx)", disabled=True, key=K("dl_off"), use_container_width=True)


# ── Archive (one table for every meeting type) ───────────────────────────────

def _pm_archive_detail(program, r):
    mid = r["id"]
    wk_type = r.get("week_type")
    tkey = _TYPE_FROM_WEEK.get(wk_type, "student")
    meta = {
        "date": str(r.get("meeting_date", "")),
        "term": r.get("term", ""),
        "week": r.get("week_number") if wk_type != "ad-hoc" else "",
        "facilitator": r.get("facilitator", ""),
        "attendees": r.get("attendees", ""),
        "type_label": MEETING_TYPES.get(tkey, {}).get("label", "Meeting"),
    }
    minutes = r.get("meeting_minutes") or ""
    with st.container(border=True):
        st.markdown(f"**{_pm_label(r)}**")
        st.caption(
            f"Term {r.get('term') or '—'} · Facilitator: {r.get('facilitator') or '—'} · "
            f"Attendees: {r.get('attendees') or 'not recorded'}"
        )
        if (r.get("agenda_items") or "").strip():
            st.markdown("**Agenda items**")
            st.markdown("\n".join(f"- {a.strip()}" for a in r["agenda_items"].splitlines() if a.strip()))
        st.markdown("**Minutes**")
        st.markdown(minutes if minutes.strip() else "_No minutes recorded._")

        src = _pm_legacy_source(r, r.get("program", ""))
        if src.strip():
            with st.expander("📄 Transcript / summary"):
                st.text(src)

        extras = _pm_legacy_extras(r)
        if extras.strip():
            with st.expander("🗂️ Earlier-format fields (kept from before)"):
                st.markdown(extras)

        bc1, bc2, bc3 = st.columns([1.3, 1, 1])
        with bc1:
            if st.button("✏️ Edit in meeting form", key=f"pm2_arch_edit_{mid}", type="primary", use_container_width=True):
                st.session_state.current_meeting_id = mid
                st.session_state.pm2_flash = [("success", "Opened for editing. Click the 🗒️ Program Meeting tab to continue.")]
                st.rerun()
        with bc2:
            if minutes.strip():
                st.download_button(
                    "📥 Download minutes (.docx)",
                    data=build_program_minutes_docx(program, meta, minutes),
                    file_name=_pm_filename(program, meta),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"pm2_arch_dl_{mid}",
                    use_container_width=True,
                )
            else:
                st.button("📥 Download minutes (.docx)", disabled=True, key=f"pm2_arch_dl_off_{mid}", use_container_width=True)
        with bc3:
            ck = f"pm2_arch_confirm_{mid}"
            if st.session_state.get(ck):
                yes, no = st.columns(2)
                if yes.button("⚠️ Confirm", key=f"pm2_arch_yes_{mid}", use_container_width=True):
                    try:
                        supabase.table("tm_program_meetings").delete().eq("id", mid).execute()
                        deleted = True
                    except Exception as e:
                        st.error(f"Could not delete: {e}")
                        deleted = False
                    if deleted:
                        st.session_state[ck] = False
                        if st.session_state.get("current_meeting_id") == mid:
                            st.session_state.current_meeting_id = None
                        st.session_state.pm2_flash = [("success", "Meeting deleted.")]
                        st.rerun()
                if no.button("Cancel", key=f"pm2_arch_no_{mid}", use_container_width=True):
                    st.session_state[ck] = False
                    st.rerun()
            else:
                if st.button("🗑️ Delete", key=f"pm2_arch_del_{mid}", use_container_width=True):
                    st.session_state[ck] = True
                    st.rerun()


def render_meeting_archive(program):
    st.markdown("### 📚 Meeting Archive")
    st.caption(f"All {PROGRAMS[program]['label']} meetings. Open one to read, edit, download or delete it.")

    recs = fetch("tm_program_meetings", {"program": program}, "meeting_date")
    if not recs:
        st.info("No meetings saved yet. Record one in the 🗒️ Program Meeting tab.")
        return

    f_choice = st.selectbox(
        "Show",
        ["All meetings", "Student Lens", "System Lens", "Ad-Hoc"],
        key=f"pm2_arch_filter_{program}",
    )
    want = {"Student Lens": "A", "System Lens": "B", "Ad-Hoc": "ad-hoc"}.get(f_choice)
    shown = [r for r in recs if want is None or r.get("week_type") == want]

    groups = {}
    for r in shown:
        groups.setdefault(r.get("term") or "Term not recorded", []).append(r)
    ordered_terms = sorted([t for t in groups if t != "Term not recorded"], reverse=True)
    if "Term not recorded" in groups:
        ordered_terms.append("Term not recorded")

    ratios = [1.5, 0.8, 1.3, 1.8, 0.9, 1.0]
    for term in ordered_terms:
        st.markdown(
            f'<div style="margin-top:20px;padding:10px 14px;background:#1A7A6E;border-radius:6px 6px 0 0;'
            f'font-size:15px;font-weight:700;color:white;font-family:Segoe UI,Arial,sans-serif;">'
            f'🗓️ {term} &nbsp;·&nbsp; {len(groups[term])} meeting(s)</div>',
            unsafe_allow_html=True,
        )
        hcols = st.columns(ratios, gap="small")
        for hc, htext in zip(hcols, ["Type", "Week", "Date", "Facilitator", "Minutes", ""]):
            hc.markdown(
                f'<div style="background:#EAF5F5;padding:8px 10px;border-bottom:2px solid #1A7A6E;'
                f'font-size:13px;font-weight:700;color:#1A7A6E;font-family:Segoe UI,Arial,sans-serif;">{htext}</div>',
                unsafe_allow_html=True,
            )

        rows = sorted(groups[term], key=lambda x: str(x.get("meeting_date", "")), reverse=True)
        for idx, r in enumerate(rows):
            mid = r["id"]
            open_key = f"pm2_arch_open_{mid}"
            is_open = st.session_state.get(open_key, False)
            bg = "#FAFBFC" if idx % 2 else "white"
            cell = f"background:{bg};padding:8px;border-bottom:1px solid #D9DEE2;font-size:13.5px;font-family:Segoe UI,Arial,sans-serif;"
            tkey = _TYPE_FROM_WEEK.get(r.get("week_type"), "")
            type_text = MEETING_TYPES.get(tkey, {}).get("label", "—")
            week_text = f"W{r.get('week_number')}" if r.get("week_type") in ("A", "B") else "—"
            has_min = "✅" if (r.get("meeting_minutes") or "").strip() else "—"
            rc = st.columns(ratios, gap="small")
            rc[0].markdown(f'<div style="{cell}">{type_text}</div>', unsafe_allow_html=True)
            rc[1].markdown(f'<div style="{cell}">{week_text}</div>', unsafe_allow_html=True)
            rc[2].markdown(f'<div style="{cell}">{r.get("meeting_date", "")}</div>', unsafe_allow_html=True)
            rc[3].markdown(f'<div style="{cell}">{r.get("facilitator") or "—"}</div>', unsafe_allow_html=True)
            rc[4].markdown(f'<div style="{cell}text-align:center;">{has_min}</div>', unsafe_allow_html=True)
            with rc[5]:
                if st.button("▾ Close" if is_open else "▸ Open", key=f"pm2_arch_btn_{mid}", use_container_width=True):
                    st.session_state[open_key] = not is_open
                    st.rerun()
            if is_open:
                _pm_archive_detail(program, r)



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
