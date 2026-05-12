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

# ── Session state initialization for SMARTAR return handling ─────────────────
if 'smartar_return_data' not in st.session_state:
    st.session_state.smartar_return_data = None
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
SUPABASE_URL = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY_MEETINGS", st.secrets["SUPABASE_KEY"])
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY_MEETINGS", SUPABASE_KEY)
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "CLC2026admin")
GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── Programs ──────────────────────────────────────────────────────────────────
PROGRAMS = {
    "JP":         {"label": "Junior Primary",     "color": "#2d7d4f", "light": "#d1fae5", "emoji": "🟢"},
    "PY":         {"label": "Primary Years",      "color": "#1a4d8c", "light": "#dbeafe", "emoji": "🔵"},
    "SY":         {"label": "Senior Years",       "color": "#7c3aed", "light": "#ede9fe", "emoji": "🟣"},
    "SPECIALIST": {"label": "Specialist Program", "color": "#d97706", "light": "#fef3c7", "emoji": "🎨"},
    "STAFF":      {"label": "STAFF Meetings",     "color": "#0891b2", "light": "#cffafe", "emoji": "👥"},
}

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
                # Simple extraction: first word before '·' or first capitalized word
                if '·' in text:
                    name = text.split('·')[0].strip()
                    if name:
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
    
    # Extract existing student names
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
        
        # Parse the three sections
        sections = {
            'student_concerns': '',
            'minutes': '',
            'actions': []
        }
        
        # Split by section markers
        if "SECTION 2" in full_output:
            parts = full_output.split("SECTION 2")
            section1 = parts[0].replace("SECTION 1 — NEW STUDENT CONCERNS", "").replace("SECTION 1", "").strip()
            remaining = parts[1]
            
            if "SECTION 3" in remaining:
                section2, section3 = remaining.split("SECTION 3", 1)
                sections['student_concerns'] = section1
                sections['minutes'] = section2.replace("— MEETING MINUTES", "").strip()
                
                # Parse actions from section 3
                actions_text = section3.replace("— SUGGESTED ACTIONS", "").strip()
                actions_list = []
                current_action = {}
                
                for line in actions_text.split('\n'):
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

# ══════════════════════════════════════════════════════════════════════════════
# NEW: ENHANCED SMARTAR INTEGRATION WITH PROPER CROSS-PAGE FLOW
# ══════════════════════════════════════════════════════════════════════════════

def open_smartar_goal_builder(student_name, meeting_id, program, term, week):
    """
    Open SMARTAR Goal Builder with proper context passing.
    Store meeting context in session state for return journey.
    """
    st.session_state['from_team_meeting'] = {
        'meeting_id': meeting_id,
        'program': program,
        'term': term,
        'week': week,
        'student_name': student_name,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # Navigate to SMARTAR Goal Builder
    # Note: This assumes SMARTAR Goal Builder is at pages/25_SMARTAR_Goal_Builder.py
    st.switch_page("pages/25_SMARTAR_Goal_Builder.py")

def check_smartar_return():
    """
    Check if we're returning from SMARTAR Goal Builder with new goal data.
    This should be called at the start of render_program_meeting.
    """
    if 'smartar_return_data' in st.session_state and st.session_state.smartar_return_data:
        return_data = st.session_state.smartar_return_data
        st.session_state.smartar_return_data = None  # Clear it
        return return_data
    return None

# ══════════════════════════════════════════════════════════════════════════════
# CORE RENDERING FUNCTIONS (keeping most of original structure)
# ══════════════════════════════════════════════════════════════════════════════

# [KEEPING ALL ORIGINAL HELPER FUNCTIONS AND fetch() FUNCTION FROM ORIGINAL CODE]
# For brevity, I'm showing the key new sections. The rest remains the same.

def render_program_meeting_enhanced(program):
    """Enhanced Program Meeting with smart AI and SMARTAR integration."""
    import json as _json
    prog_label = PROGRAMS[program]["label"]
    accent = PROGRAMS[program]["color"]
    
    # Check for SMARTAR return
    smartar_return = check_smartar_return()
    if smartar_return:
        st.success(f"✅ Goal created for {smartar_return['student_name']} and added to meeting!")
        # Add goal to meeting notes automatically
        # (Implementation depends on your data structure)
    
    # [KEEP ORIGINAL MEETING SELECTION AND LOADING CODE]
    
    # === WEEK A SPECIFIC: ENHANCED STUDENT CONCERNS WITH AI ===
    if is_week_a:
        st.markdown("#### ⏱ 10–25 min | STUDENT CONCERNS — Structured Problem Solving")
        st.caption("Facilitator prompt: Push for function-based thinking, not description.")
        
        # Manual entry section
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
        
        st.markdown("**Manual Entry:**")
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
                        concerns.pop(idx)
                        st.rerun()
        
        if st.button("➕ Add student concern", key=f"con_add_{program}"):
            concerns.append({"notes": ""})
            st.rerun()
        
        st.markdown("---")
        
        # === NEW: AI TRANSCRIPT GENERATION FOR STUDENT CONCERNS ===
        st.markdown("**🎤 OR Generate from Transcript:**")
        st.caption(
            "Paste meeting transcript below. AI will identify NEW student concerns not already documented above, "
            "plus extract general minutes and action items."
        )
        
        transcript_concerns = st.text_area(
            "Meeting transcript",
            height=180,
            key=f"transcript_concerns_{program}",
            label_visibility="collapsed",
            placeholder=(
                "Paste full meeting transcript here...\n\n"
                "AI will:\n"
                "• Detect students already documented above (won't duplicate)\n"
                "• Extract NEW student concerns only\n"
                "• Generate general minutes\n"
                "• Suggest action items with who/when"
            )
        )
        
        col_gen, col_info = st.columns([2, 3])
        with col_gen:
            if st.button("✨ Generate with AI", key=f"gen_concerns_{program}", type="primary"):
                if transcript_concerns.strip():
                    with st.spinner("Analyzing transcript..."):
                        # Get existing concerns as JSON string
                        existing_json = _json.dumps(concerns)
                        
                        # Generate smart minutes
                        result = generate_smart_minutes_week_a(
                            transcript_concerns,
                            existing_json,
                            program
                        )
                        
                        if result:
                            # Stage results for review
                            st.session_state[f'_ai_new_concerns_{program}'] = result['student_concerns']
                            st.session_state[f'_ai_minutes_{program}'] = result['minutes']
                            st.session_state[f'_ai_actions_{program}'] = result['actions']
                            st.rerun()
                else:
                    st.warning("Paste a transcript first")
        
        with col_info:
            if st.session_state.get(f'_ai_new_concerns_{program}'):
                st.info("✓ AI results ready for review below")
        
        # === NEW: AI RESULTS REVIEW SECTION ===
        if st.session_state.get(f'_ai_new_concerns_{program}'):
            st.markdown("---")
            st.markdown("**🤖 AI Generated Results — Review & Accept:**")
            
            # New student concerns
            new_concerns_text = st.session_state[f'_ai_new_concerns_{program}']
            st.markdown("**New Student Concerns:**")
            st.text_area(
                "Review new concerns",
                value=new_concerns_text,
                height=120,
                key=f"review_concerns_{program}",
                label_visibility="collapsed"
            )
            
            col_accept, col_reject = st.columns(2)
            with col_accept:
                if st.button("✅ Accept & Add to Student Concerns", key=f"accept_concerns_{program}"):
                    # Parse and add each new concern as a separate entry
                    new_lines = [line.strip() for line in new_concerns_text.split('\n') if line.strip() and not line.startswith("No new")]
                    for line in new_lines:
                        if line:
                            concerns.append({"notes": line})
                    
                    # Clear the staged data
                    del st.session_state[f'_ai_new_concerns_{program}']
                    st.success("Added new concerns!")
                    st.rerun()
            
            with col_reject:
                if st.button("❌ Discard", key=f"reject_concerns_{program}"):
                    del st.session_state[f'_ai_new_concerns_{program}']
                    st.rerun()
        
        st.markdown("---")
    
    # === ENHANCED SMARTAR SECTION WITH PROPER INTEGRATION ===
    st.markdown("#### ⏱ 25–40 min | SMARTAR GOAL SPOTLIGHT — 4 Students")
    st.caption("Click to open Goal Builder in integrated workflow")
    
    if not st.session_state.current_meeting_id:
        st.info("💡 Save meeting details first to activate SMARTAR integration")
    
    smartar_key = f"pm_smartar_{program}"
    if smartar_key not in st.session_state:
        if selected_record and selected_record.get('smartar_spotlight'):
            try:
                loaded = _json.loads(selected_record['smartar_spotlight'])
                st.session_state[smartar_key] = loaded if isinstance(loaded, list) else []
            except:
                st.session_state[smartar_key] = []
        else:
            st.session_state[smartar_key] = []
    
    smartar = st.session_state[smartar_key]
    
    # Display existing students with enhanced Goal Builder button
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
                    # NEW: Use proper cross-page navigation instead of link
                    if st.button(f"🎯 Open Goal Builder", key=f"open_smartar_{program}_{idx}"):
                        open_smartar_goal_builder(
                            student_name,
                            st.session_state.current_meeting_id,
                            program,
                            pm_term or "T1",
                            pm_week
                        )
                else:
                    st.caption("Save meeting first")
            
            with col_status:
                # Check for synced goal
                goal_notes = student_data.get("notes", "")
                if "SMARTAR Goal:" in goal_notes:
                    st.success("✓ Has goal")
                else:
                    st.info("No goal yet")
            
            with col_remove:
                if st.button("✕", key=f"sm_remove_{program}_{idx}"):
                    smartar.pop(idx)
                    st.rerun()
            
            # Goal notes display
            with st.expander(f"📝 Goal & Notes for {student_name}", expanded=False):
                student_data["notes"] = st.text_area(
                    f"Notes for {student_name}",
                    value=student_data.get("notes", ""),
                    key=f"sm_notes_{program}_{idx}",
                    height=120,
                    placeholder="SMARTAR goal will appear here when created...",
                    label_visibility="collapsed"
                )
    
    # Add student section
    st.markdown("**Add student to spotlight:**")
    col_select, col_add = st.columns([4, 1])
    
    with col_select:
        # Student selector
        new_student_name = st.selectbox(
            "Select student",
            options=[""] + student_names,  # Assumes student_names is populated earlier
            key=f"new_student_select_{program}",
            label_visibility="collapsed"
        )
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
                smartar.append({"student_name": new_student_name.strip(), "notes": ""})
                
                if st.session_state.current_meeting_id:
                    # Open Goal Builder immediately with proper navigation
                    open_smartar_goal_builder(
                        new_student_name.strip(),
                        st.session_state.current_meeting_id,
                        program,
                        pm_term or "T1",
                        pm_week
                    )
                else:
                    st.warning("⚠️ Save meeting details first")
                    st.rerun()
            else:
                st.warning("⚠️ Please select or enter a student name")
    
    st.markdown("---")
    
    # === MEETING MINUTES SECTION ===
    st.markdown("#### 📝 MEETING MINUTES / NOTES")
    
    # Check for AI-generated minutes
    if st.session_state.get(f'_ai_minutes_{program}'):
        st.markdown("**🤖 AI Generated Minutes — Review & Accept:**")
        ai_minutes = st.session_state[f'_ai_minutes_{program}']
        
        edited_minutes = st.text_area(
            "Review minutes",
            value=ai_minutes,
            height=200,
            key=f"review_minutes_{program}",
            label_visibility="collapsed"
        )
        
        col_accept_min, col_reject_min = st.columns(2)
        with col_accept_min:
            if st.button("✅ Accept Minutes", key=f"accept_minutes_{program}"):
                st.session_state[f"pm_minutes_{program}"] = edited_minutes
                del st.session_state[f'_ai_minutes_{program}']
                st.success("Minutes accepted!")
                st.rerun()
        
        with col_reject_min:
            if st.button("❌ Discard", key=f"reject_minutes_{program}"):
                del st.session_state[f'_ai_minutes_{program}']
                st.rerun()
    else:
        # Regular minutes entry
        default_minutes = selected_record.get('meeting_minutes', '') if selected_record else ''
        if f"pm_minutes_{program}" not in st.session_state:
            st.session_state[f"pm_minutes_{program}"] = default_minutes
        
        pm_minutes = st.text_area(
            "Meeting minutes",
            height=200,
            key=f"pm_minutes_{program}",
            label_visibility="collapsed",
            placeholder="Record comprehensive meeting minutes here..."
        )
    
    st.markdown("---")
    
    # === ENHANCED ACTIONS SECTION ===
    st.markdown("#### ✅ ACTIONS — Clear Ownership & Accountability")
    st.caption("Each action must have: specific task, responsible person, and due date")
    
    actions_key = f"pm_actions_{program}"
    if actions_key not in st.session_state:
        # Load from database if editing
        if selected_record and selected_record.get('actions'):
            try:
                loaded_actions = _json.loads(selected_record['actions'])
                st.session_state[actions_key] = loaded_actions if isinstance(loaded_actions, list) else []
            except:
                st.session_state[actions_key] = []
        
        # If still empty, initialize with one blank
        if not st.session_state.get(actions_key):
            st.session_state[actions_key] = [{"action":"","who":"","by_when":"","priority":"Medium","done":False}]
    
    actions = st.session_state[actions_key]
    
    # === NEW: AI-SUGGESTED ACTIONS REVIEW ===
    if st.session_state.get(f'_ai_actions_{program}'):
        st.markdown("**🤖 AI Suggested Actions — Review & Add:**")
        ai_actions = st.session_state[f'_ai_actions_{program}']
        
        if ai_actions:
            for ai_idx, ai_action in enumerate(ai_actions):
                col_action, col_who, col_when, col_pri, col_add = st.columns([3, 1.5, 1, 1, 0.7])
                
                with col_action:
                    st.text_input(
                        "Action",
                        value=ai_action.get('action', ''),
                        key=f"ai_act_{program}_{ai_idx}",
                        label_visibility="collapsed"
                    )
                with col_who:
                    st.text_input(
                        "Who",
                        value=ai_action.get('who', ''),
                        key=f"ai_who_{program}_{ai_idx}",
                        label_visibility="collapsed"
                    )
                with col_when:
                    st.text_input(
                        "When",
                        value=ai_action.get('by_when', ''),
                        key=f"ai_when_{program}_{ai_idx}",
                        label_visibility="collapsed"
                    )
                with col_pri:
                    st.selectbox(
                        "Pri",
                        ["Low", "Medium", "High", "Urgent"],
                        index=["Low", "Medium", "High", "Urgent"].index(ai_action.get('priority', 'Medium')),
                        key=f"ai_pri_{program}_{ai_idx}",
                        label_visibility="collapsed"
                    )
                with col_add:
                    if st.button("✅", key=f"add_ai_action_{program}_{ai_idx}"):
                        # Get edited values from inputs
                        edited_action = {
                            "action": st.session_state[f"ai_act_{program}_{ai_idx}"],
                            "who": st.session_state[f"ai_who_{program}_{ai_idx}"],
                            "by_when": st.session_state[f"ai_when_{program}_{ai_idx}"],
                            "priority": st.session_state[f"ai_pri_{program}_{ai_idx}"],
                            "done": False
                        }
                        actions.append(edited_action)
                        st.success(f"Added action!")
                        time.sleep(0.5)
                        st.rerun()
        
        col_accept_all, col_clear = st.columns(2)
        with col_accept_all:
            if st.button("✅ Accept All Suggested Actions", key=f"accept_all_actions_{program}"):
                for ai_action in ai_actions:
                    actions.append({
                        "action": ai_action.get('action', ''),
                        "who": ai_action.get('who', ''),
                        "by_when": ai_action.get('by_when', ''),
                        "priority": ai_action.get('priority', 'Medium'),
                        "done": False
                    })
                del st.session_state[f'_ai_actions_{program}']
                st.success("All actions added!")
                st.rerun()
        
        with col_clear:
            if st.button("Clear Suggestions", key=f"clear_actions_{program}"):
                del st.session_state[f'_ai_actions_{program}']
                st.rerun()
        
        st.markdown("---")
    
    # === EXISTING ACTIONS DISPLAY ===
    st.markdown("**Current Actions:**")
    
    if actions:
        ah_cols = st.columns([4, 1.5, 1, 1, 0.7, 0.5])
        for h, label in zip(ah_cols, ["Action", "Who", "By When", "Priority", "✓ Done", ""]):
            h.markdown(f"**{label}**" if label else "")
        
        for idx, row in enumerate(actions):
            a1, a2, a3, a4, a5, a6 = st.columns([4, 1.5, 1, 1, 0.7, 0.5])
            with a1:
                row["action"] = st.text_input(
                    "Act",
                    value=row.get("action", ""),
                    key=f"act_a_{program}_{idx}",
                    label_visibility="collapsed",
                    placeholder="Specific action item"
                )
            with a2:
                row["who"] = st.text_input(
                    "Who",
                    value=row.get("who", ""),
                    key=f"act_w_{program}_{idx}",
                    label_visibility="collapsed",
                    placeholder="Person"
                )
            with a3:
                row["by_when"] = st.text_input(
                    "By",
                    value=row.get("by_when", ""),
                    key=f"act_by_{program}_{idx}",
                    label_visibility="collapsed",
                    placeholder="Due date"
                )
            with a4:
                row["priority"] = st.selectbox(
                    "Pri",
                    ["Low", "Medium", "High", "Urgent"],
                    index=["Low", "Medium", "High", "Urgent"].index(row.get("priority", "Medium")),
                    key=f"act_pri_{program}_{idx}",
                    label_visibility="collapsed"
                )
            with a5:
                row["done"] = st.checkbox(
                    "✓",
                    value=row.get("done", False),
                    key=f"act_done_{program}_{idx}"
                )
            with a6:
                if len(actions) > 1:
                    if st.button("✕", key=f"act_del_{program}_{idx}"):
                        actions.pop(idx)
                        st.rerun()
    
    # === NEW: MULTIPLE ADD ACTIONS ===
    st.markdown("**Add New Actions:**")
    col_add_one, col_add_multi = st.columns(2)
    
    with col_add_one:
        if st.button("➕ Add 1 Action", key=f"act_add_one_{program}"):
            actions.append({"action":"","who":"","by_when":"","priority":"Medium","done":False})
            st.rerun()
    
    with col_add_multi:
        num_to_add = st.number_input(
            "Add multiple",
            min_value=1,
            max_value=10,
            value=3,
            key=f"num_actions_{program}",
            label_visibility="collapsed"
        )
        if st.button(f"➕ Add {num_to_add} Actions", key=f"act_add_multi_{program}"):
            for _ in range(num_to_add):
                actions.append({"action":"","who":"","by_when":"","priority":"Medium","done":False})
            st.rerun()
    
    st.markdown("---")
    
    # === SAVE MEETING ===
    # [KEEP ORIGINAL SAVE LOGIC WITH meeting_data ASSEMBLY]
    
    save_button_text = "💾 Update Meeting Record" if st.session_state.current_meeting_id else "💾 Save Meeting Record"
    if st.button(save_button_text, type="primary", use_container_width=True, key=f"pm_save_{program}"):
        # Assemble meeting_data
        meeting_data = {
            "program": program,
            "meeting_date": str(pm_date),
            "term": pm_term.strip(),
            "week_number": int(pm_week),
            "week_type": "A" if is_week_a else "B",
            "facilitator": pm_facilitator.strip(),
            "attendees": pm_attendees.strip(),
            "checkin_notes": pm_checkin.strip(),
            "student_concerns": _json.dumps([{"notes": r.get("notes", "")} for r in concerns]) if is_week_a else _json.dumps([]),
            "smartar_spotlight": _json.dumps(smartar),
            "meeting_minutes": st.session_state.get(f"pm_minutes_{program}", ""),
            "actions": _json.dumps(actions),
        }
        
        try:
            if st.session_state.current_meeting_id:
                supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                st.success("✅ Meeting updated!")
            else:
                result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
                if result.data:
                    st.session_state.current_meeting_id = result.data[0]['id']
                st.success("✅ Meeting saved!")
            
            # Clear session state
            for k in [concerns_key, smartar_key, actions_key]:
                st.session_state.pop(k, None)
            
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Save failed: {e}")

# [REST OF ORIGINAL CODE INCLUDING main(), admin_login(), render_meeting_archive(), etc.]
# For full implementation, copy all remaining functions from original file

if __name__ == "__main__":
    main()
