# ==============================================================================
# 18_Scatter_Plot_Tracker.py - CLC-LBU Portal
# Simple Paper-Style Scatter Plot Tracker
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
import json

try:
    from staff_auth import get_staff_name
except ImportError:
    def get_staff_name():
        return st.session_state.get("staff_name", "Staff")
# require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
# logout_button()

try:
    from archive_utils import fetch_register, initials_from_name
except ImportError:
    fetch_register = None
    initials_from_name = None

TEAL = "#1A7A6E"
AMBER = "#C8760A"

st.set_page_config(page_title="Scatter Plot Tracker", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f5f8fa; }
.header {
    background:linear-gradient(135deg,#1A7A6E 0%,#1A7A6EBB 100%);
    color:white; padding:1rem 1.5rem; border-radius:10px; margin-bottom:1.5rem;
}
.header h1 { margin:0; font-size:1.8rem; }
.header p { margin:.3rem 0 0; opacity:.9; font-size:.9rem; }
.grid-container {
    background:white; border:2px solid #cbd5e1; border-radius:10px;
    padding:1rem; margin-top:1rem;
}
.week-grid {
    width:100%; border-collapse:collapse; font-size:.85rem;
    margin-top:1rem;
}
.week-grid th {
    background:#1A7A6E; color:white; padding:.6rem .4rem;
    text-align:center; font-weight:600; border:1px solid #0f5f56;
}
.week-grid td {
    border:1px solid #cbd5e1; padding:.5rem .3rem;
    text-align:center; min-width:45px; cursor:pointer;
}
.week-grid td:hover { background:#e0f2fe; }
.week-grid .time-cell { 
    background:#f1f5f9; font-weight:600; text-align:left;
    padding-left:.6rem; white-space:nowrap;
}
.week-grid .activity-cell {
    background:#f8fafc; text-align:left; padding-left:.6rem;
    font-style:italic; font-size:.8rem; color:#64748b;
}
.week-grid .total-cell {
    background:#fef3c7; font-weight:700; color:#92400e;
}
.week-grid .total-row {
    background:#fef3c7; font-weight:700; color:#92400e;
    font-size:.9rem;
}
.tally { color:#dc2626; font-weight:700; font-size:1.1rem; }
.info-box {
    background:#f0f9ff; border-left:4px solid #0284c7;
    padding:.7rem 1rem; border-radius:6px; margin:.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SUPABASE
# ==============================================================================
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

# ==============================================================================
# STUDENT REGISTER INTEGRATION
# The Student Register (archive_utils.fetch_register) is the single front
# door for adding/archiving students, same as Comm Log and SMARTAR — this
# tool no longer has its own "Add Student" path. The register stores
# INITIALS ONLY (no names), while this tool's existing scatter_students
# rows are keyed by full name from before this integration. To avoid
# losing history, a registered student is matched to any existing local
# row by deriving that row's initials — if matched, the existing full
# name stays the identity key (so old weekly data keeps working); if not
# matched (never tracked here before), the initials themselves become
# the identity key going forward, since that's all the register has.
# ==============================================================================
@st.cache_data(ttl=60)
def get_trackable_students():
    if fetch_register is None:
        return []
    registered = fetch_register("active")
    sb = get_sb()
    local_rows = []
    if sb:
        try:
            local_rows = sb.table("scatter_students").select("*").execute().data or []
        except Exception:
            local_rows = []

    by_initials = {}
    for row in local_rows:
        ini = initials_from_name(row.get("student_name")) if initials_from_name else None
        if ini and ini not in by_initials:
            by_initials[ini] = row

    trackable = []
    for s in registered:
        ini = s.get("initials")
        program = s.get("program") or "-"
        match = by_initials.get(ini)
        if match:
            key = match["student_name"]
            display = f"{key} ({ini} · {program})"
        else:
            key = ini
            display = f"{ini} ({program})"
        trackable.append({
            "initials": ini,
            "program": s.get("program"),
            "key": key,
            "display": display,
            "row": match,
        })
    return trackable


def upsert_behaviour_definition(key, program, beh_name, definition):
    """Create or update this student's single tracked behaviour +
    definition in scatter_students, keyed by `key` (see note above)."""
    sb = get_sb()
    if not sb:
        return False
    try:
        beh_defs = {beh_name: definition} if beh_name and definition else {}
        existing = sb.table("scatter_students").select("id").eq("student_name", key).execute()
        if existing.data:
            sb.table("scatter_students").update({
                "behaviour_definitions": json.dumps(beh_defs) if beh_defs else None,
                "program_type": program,
            }).eq("id", existing.data[0]["id"]).execute()
        else:
            sb.table("scatter_students").insert({
                "student_name": key,
                "name": key,
                "program_type": program,
                "behaviour_definitions": json.dumps(beh_defs) if beh_defs else None,
            }).execute()
        get_trackable_students.clear()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False

# ==============================================================================
# GROQ AI (shared fallback chain — matches the fleet-wide fix used elsewhere
# in the portal: gpt-oss-120b -> qwen3.6-27b -> llama-3.3-70b-versatile,
# because Groq retired llama-3.3-70b-versatile for free/dev-tier accounts
# on 16 Aug 2026. Also self-heals the httpx "proxies" client-init error and
# 413 "request too large" by halving max_tokens and retrying.)
# ==============================================================================
GROQ_MODEL_CHAIN = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]

def groq_ai_call(prompt, temperature=0.3, max_tokens=120):
    from groq import Groq
    api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
    if not api_key:
        raise RuntimeError("Add GROQ_API_KEY to Render secrets.")
    try:
        client = Groq(api_key=api_key)
    except TypeError:
        import httpx
        client = Groq(api_key=api_key, http_client=httpx.Client())

    last_err = None
    for model in GROQ_MODEL_CHAIN:
        tokens = max_tokens
        for _attempt in range(2):
            try:
                kwargs = dict(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=tokens,
                )
                if model.startswith("qwen/"):
                    kwargs["reasoning_effort"] = "none"  # suppress thinking-token output
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                if "413" in str(e) or "too large" in str(e).lower():
                    tokens = max(tokens // 2, 20)
                    continue
                break  # non-413 error: try next model in the chain
    raise last_err

# ==============================================================================
# BEHAVIOUR TEMPLATES (shared by the Students page and the Setup page)
# ==============================================================================
BEHAVIOUR_TEMPLATES = {
    "": "—",
    "Hitting": "Making forceful contact with another person using an open or closed hand. Includes slapping, punching, striking. Excludes accidental contact, light taps, high-fives.",
    "Pushing": "Using hands, arms, or body to forcefully move another person. Includes shoving, bumping with force. Excludes gentle guidance, accidental contact.",
    "Kicking": "Making forceful contact with another person using foot or leg. Includes kicking, stomping, tripping. Excludes accidental contact, stretching.",
    "Yelling": "Speaking louder than conversational tone for 3+ seconds. Includes shouting, screaming. Excludes excited play voice, calling from distance.",
    "Task refusal": "Refusing to begin or continue assigned work. Includes saying 'no', pushing materials away. Excludes asking for help, requesting breaks.",
    "Leaving area": "Moving beyond boundaries without permission. Includes leaving classroom, wandering. Excludes transitions with class.",
    "Throwing objects": "Propelling objects through air with force. Includes throwing books, materials. Excludes passing items, accidental drops.",
    "Swearing": "Using profanity or inappropriate language. Includes curse words. Excludes repeating without understanding.",
    "Property destruction": "Damaging or breaking materials. Includes tearing, breaking, scratching. Excludes accidental damage.",
    "Self-hitting": "Making forceful contact with own body. Includes hitting head with hand or on objects. Excludes scratching itch.",
}

# ==============================================================================
# SESSION STATE
# ==============================================================================
def init():
    if 'page' not in st.session_state:
        st.session_state.page = 'students'
    if 'student_name' not in st.session_state:
        st.session_state.student_name = ''
    if 'week_start' not in st.session_state:
        st.session_state.week_start = date.today() - timedelta(days=date.today().weekday())
    if 'behaviours' not in st.session_state:
        st.session_state.behaviours = []
    if 'schedule' not in st.session_state:
        st.session_state.schedule = []
    if 'grid_data' not in st.session_state:
        st.session_state.grid_data = {}

init()

# ==============================================================================
# HEADER
# ==============================================================================
st.markdown("""
<div class='header'>
<h1>📊 Scatter Plot Tracker</h1>
<p>Simple paper-style weekly behaviour recording</p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# PAGE NAVIGATION
# ==============================================================================
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    if st.button("👤 Students", use_container_width=True, type="primary" if st.session_state.page == 'students' else "secondary"):
        st.session_state.page = 'students'
        st.rerun()
with col2:
    if st.button("📋 Setup", use_container_width=True, type="primary" if st.session_state.page == 'setup' else "secondary"):
        st.session_state.page = 'setup'
        st.rerun()
with col3:
    if st.button("✏️ Record", use_container_width=True, type="primary" if st.session_state.page == 'record' else "secondary"):
        st.session_state.page = 'record'
        st.rerun()
with col4:
    if st.button("📈 Analysis", use_container_width=True, type="primary" if st.session_state.page == 'analysis' else "secondary"):
        st.session_state.page = 'analysis'
        st.rerun()

st.markdown("---")

# ==============================================================================
# PAGE 1: STUDENTS
# ==============================================================================
# ==============================================================================
# PAGE 1: STUDENTS (target behaviour management)
# ==============================================================================
if st.session_state.page == 'students':
    st.markdown("## 👤 Target Behaviour")
    st.caption("Students are added and archived via the Student Register — they'll appear here automatically once active.")

    trackable = get_trackable_students()

    if fetch_register is None:
        st.error("❌ Could not load `archive_utils` — the Student Register module isn't available. Check the deployment.")
        st.stop()

    if not trackable:
        st.warning("⚠️ No active students found in the Student Register. Add students there first.")
        st.stop()

    selected_display = st.selectbox("Select Student", options=[t['display'] for t in trackable])
    selected = next(t for t in trackable if t['display'] == selected_display)

    # AI Connection Test
    with st.expander("🔧 Test AI Connection (click if AI not working)"):
        if st.button("Test Groq API Connection"):
            try:
                api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                if not api_key:
                    st.error("❌ No API key found. Add GROQ_API_KEY to Render secrets.")
                else:
                    st.info(f"✓ API key found: {api_key[:8]}...")
                    result = groq_ai_call("Say 'test successful'", temperature=0.0, max_tokens=10)
                    st.success(f"✅ AI Working! Response: {result}")
            except ImportError as e:
                st.error(f"❌ Groq library not installed: {e}")
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")

    st.caption("Select from templates below, or use AI to generate a custom definition")

    # Existing definition, if any
    existing_defs = {}
    if selected['row']:
        raw = selected['row'].get('behaviour_definitions')
        if raw:
            try:
                existing_defs = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                existing_defs = {}
    existing_beh = next(iter(existing_defs), '')
    existing_def = existing_defs.get(existing_beh, '')

    st.markdown("**Behaviour**")

    col1a, col1b = st.columns([1, 1])
    with col1a:
        template1 = st.selectbox(
            "Quick select from templates",
            list(BEHAVIOUR_TEMPLATES.keys()),
            index=list(BEHAVIOUR_TEMPLATES.keys()).index(existing_beh) if existing_beh in BEHAVIOUR_TEMPLATES else 0,
            key="temp1"
        )
    with col1b:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Or type your own below ↓")

    col1, col2 = st.columns([4, 1])
    with col1:
        beh1_name = st.text_input(
            "Behaviour name (select from dropdown OR type custom)",
            value=template1 if template1 else existing_beh,
            key="new_beh1",
            placeholder="e.g., 'Hitting' or 'Interrupting others'"
        )
    with col2:
        if st.button("🤖 AI", key="ai1", use_container_width=True, help="Generate definition with AI"):
            if beh1_name:
                with st.spinner("Generating..."):
                    try:
                        st.session_state['ai_gen1'] = groq_ai_call(
                            f"Write a 2-3 sentence operational definition for the school behaviour '{beh1_name}'. Format: Description. Includes examples. Excludes non-examples."
                        )
                        st.success("✅ Generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI Error: {str(e)[:100]}")

    # Show definition in prominent box
    def_value = st.session_state.get('ai_gen1', BEHAVIOUR_TEMPLATES.get(template1) or existing_def)
    if def_value:
        st.info(f"📋 **Definition:** {def_value}")

    beh1_def = st.text_area(
        "Edit definition if needed",
        value=def_value,
        height=80,
        key="def1",
        placeholder="Observable, measurable description"
    )

    if st.button("💾 Save Behaviour Definition", type="primary", use_container_width=True):
        if upsert_behaviour_definition(selected['key'], selected['program'], beh1_name, beh1_def):
            st.success(f"✅ Saved for {selected['initials']}")
            if 'ai_gen1' in st.session_state:
                del st.session_state['ai_gen1']
            st.rerun()

    st.markdown("---")

    # List students
    st.markdown("### Current Students")
    for t in trackable:
        with st.expander(f"**{t['display']}**"):
            st.markdown(f"**Program:** {t.get('program') or 'Not set'}")
            beh_defs = {}
            if t['row']:
                raw = t['row'].get('behaviour_definitions')
                if raw:
                    try:
                        beh_defs = json.loads(raw) if isinstance(raw, str) else raw
                    except Exception:
                        beh_defs = {}
            if beh_defs:
                st.markdown("**Target Behaviour:**")
                for beh_name, beh_def in beh_defs.items():
                    st.markdown(f"- **{beh_name}:** {beh_def}")
            else:
                st.caption("No behaviour definition set")

# ==============================================================================
# PAGE 2: SETUP
# ==============================================================================
elif st.session_state.page == 'setup':
    st.markdown("## 📋 Weekly Setup")
    st.caption("Set up your tracking sheet for the week")
    
    # Student selection
    st.markdown("### 1. Student")
    
    trackable = get_trackable_students()
    
    if not trackable:
        st.warning("⚠️ No active students found in the Student Register. Add students there first.")
        st.stop()
    else:
        display_options = [t['display'] for t in trackable]
        current_display = next((t['display'] for t in trackable if t['key'] == st.session_state.student_name), display_options[0])
        selected_display = st.selectbox(
            "Select Student",
            options=display_options,
            index=display_options.index(current_display)
        )
        selected_student = next(t for t in trackable if t['display'] == selected_display)
        st.session_state.student_name = selected_student['key']
    
    st.markdown("---")
    
    # Week selection
    st.markdown("### 2. Week")
    col1, col2 = st.columns(2)
    with col1:
        week_start = st.date_input(
            "Monday (start of week)",
            value=st.session_state.week_start,
            help="Select the Monday of the tracking week"
        )
        st.session_state.week_start = week_start
    with col2:
        week_end = week_start + timedelta(days=4)
        st.info(f"📅 Week: {week_start.strftime('%-d %b')} - {week_end.strftime('%-d %b %Y')}")
    
    st.markdown("---")
    
    # Target behaviours
    st.markdown("### 3. Target Behaviour")
    
    # Check if student has a pre-defined behaviour
    student_row = selected_student['row']
    has_predefined = False
    beh_defs = {}
    
    if student_row:
        raw = student_row.get('behaviour_definitions')
        if raw:
            try:
                beh_defs = json.loads(raw) if isinstance(raw, str) else raw
                has_predefined = bool(beh_defs)
            except:
                pass
    
    if has_predefined:
        st.info(f"📋 {selected_student['initials']} has a pre-defined behaviour: {', '.join(beh_defs.keys())}")
        if st.button("✨ Use Pre-defined Behaviour", use_container_width=True):
            st.session_state.behaviours = list(beh_defs.keys())[:1]
            st.rerun()
    
    st.caption("Select from templates or type a custom behaviour name")
    st.markdown("**For a custom behaviour not in templates, type the name and click AI to generate a definition**")
    
    # Behaviour
    col1, col2 = st.columns([4, 1])
    with col1:
        template1 = st.selectbox("Select Behaviour or type custom below", list(BEHAVIOUR_TEMPLATES.keys()), key="setup_temp1")
        beh1 = st.text_input(
            "Behaviour name", 
            value=(template1 if template1 and template1 != "—" else st.session_state.get('setup_beh1', '')),
            key="beh1",
            placeholder="Select from dropdown OR type custom"
        )
        # ALWAYS save to session state (not just on AI click)
        st.session_state['setup_beh1'] = beh1 if beh1 else ''
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🤖 AI", key="setup_ai1", use_container_width=True):
            if beh1:
                # Save behaviour name before generating
                st.session_state['setup_beh1'] = beh1
                
                with st.spinner("Generating..."):
                    try:
                        new_def = groq_ai_call(
                            f"Write a 2-3 sentence operational definition for the school behaviour '{beh1}'. Format: Description. Includes examples. Excludes non-examples."
                        )
                        st.session_state[f'setup_def_{beh1}'] = new_def

                        if upsert_behaviour_definition(selected_student['key'], selected_student['program'], beh1, new_def):
                            st.success("✅ Generated & saved!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"AI Error: {str(e)[:80]}")
    
    # Show definition if available
    def1 = st.session_state.get(f'setup_def_{beh1}', BEHAVIOUR_TEMPLATES.get(template1) or beh_defs.get(beh1, ''))
    if def1:
        st.info(f"📋 {def1}")
    
    st.markdown("---")
    
    # Schedule
    st.markdown("### 4. Daily Schedule")
    st.caption("Enter your time slots and activities (e.g., '9:00 - Maths', '10:30 - Recess')")
    
    # Default schedule
    if not st.session_state.schedule:
        st.session_state.schedule = [
            {"time": "9:00", "activity": "Morning routine"},
            {"time": "9:30", "activity": "Lesson 1"},
            {"time": "10:30", "activity": "Recess"},
            {"time": "11:00", "activity": "Lesson 2"},
            {"time": "12:30", "activity": "Lunch"},
            {"time": "13:00", "activity": "Lesson 3"},
            {"time": "14:00", "activity": "Pack up"},
        ]
    
    schedule_data = pd.DataFrame(st.session_state.schedule)
    
    edited_schedule = st.data_editor(
        schedule_data,
        column_config={
            "time": st.column_config.TextColumn("Time", width="small"),
            "activity": st.column_config.TextColumn("Activity", width="medium")
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True
    )
    
    st.session_state.schedule = edited_schedule.to_dict('records')
    
    st.markdown("---")
    
    # Build behaviours list from the single behaviour input (use widget, then template, then session_state)
    behaviours = []
    val1 = beh1 if beh1 else (template1 if template1 and template1 != "—" else st.session_state.get('setup_beh1', ''))
    if val1 and val1.strip():
        behaviours.append(val1.strip())
    
    st.session_state.behaviours = behaviours
    
    if behaviours:
        st.info(f"✅ Ready to track: **{behaviours[0]}**")
    else:
        st.error("❌ Please select or enter a behaviour to track")
    
    # Save and continue
    if st.button("✅ Setup Complete - Start Recording", type="primary", use_container_width=True):
        if not st.session_state.student_name:
            st.error("❌ Please select a student")
        elif not behaviours:
            st.error("❌ Please enter at least one behaviour")
        elif not st.session_state.schedule:
            st.error("❌ Please add your daily schedule")
        else:
            # Save week to database
            sb = get_sb()
            if sb:
                try:
                    week_start = st.session_state.week_start
                    sb.table("scatter_weekly_data").upsert({
                        "student_name": st.session_state.student_name,
                        "week_start": str(week_start),
                        "behaviours": json.dumps(behaviours),
                        "schedule": json.dumps(st.session_state.schedule),
                        "grid_data": json.dumps({}),
                        "created_by": get_staff_name() if hasattr(get_staff_name, '__call__') else "Staff"
                    }, on_conflict="student_name,week_start").execute()
                except Exception as e:
                    st.error(f"Save error: {e}")
            
            st.session_state.page = 'record'
            st.rerun()

# ==============================================================================
# PAGE 3: RECORDING
# ==============================================================================
elif st.session_state.page == 'record':
    
    if not st.session_state.student_name or not st.session_state.behaviours:
        st.warning("⚠️ Please complete setup first")
        if st.button("Go to Setup"):
            st.session_state.page = 'setup'
            st.rerun()
        st.stop()
    
    st.markdown(f"## ✏️ Recording: {st.session_state.student_name}")
    
    week_start = st.session_state.week_start
    week_end = week_start + timedelta(days=4)
    
    st.markdown(f"<div class='info-box'><b>Week:</b> {week_start.strftime('%-d %b')} - {week_end.strftime('%-d %b %Y')} | <b>Behaviours:</b> {', '.join(st.session_state.behaviours)}</div>", unsafe_allow_html=True)
    
    # Show behaviour definitions if student has them
    @st.cache_data(ttl=60)
    def load_students():
        sb = get_sb()
        if not sb: return []
        try:
            res = sb.table("scatter_students").select("*").order("student_name").execute()
            return res.data or []
        except:
            return []
    
    students = load_students()
    student_obj = [s for s in students if s['student_name'] == st.session_state.student_name]
    
    if student_obj:
        beh_defs = student_obj[0].get('behaviour_definitions')
        if beh_defs:
            if isinstance(beh_defs, str):
                try:
                    beh_defs = json.loads(beh_defs)
                except:
                    beh_defs = {}
            
            if beh_defs:
                with st.expander("📋 Behaviour Definitions (click to view)", expanded=False):
                    for beh in st.session_state.behaviours:
                        if beh in beh_defs:
                            st.markdown(f"**{beh}:** {beh_defs[beh]}")
                        else:
                            st.caption(f"{beh}: No definition set")
    
    # Days of week
    days = []
    for i in range(5):
        day_date = week_start + timedelta(days=i)
        days.append({
            "name": day_date.strftime("%A"),
            "short": day_date.strftime("%a"),
            "date": day_date.strftime("%-d/%-m"),
            "date_obj": day_date
        })
    
    behaviours = st.session_state.behaviours
    schedule = st.session_state.schedule
    
    # Initialize grid data if needed
    if not st.session_state.grid_data:
        st.session_state.grid_data = {}
    
    st.markdown("### 📊 Weekly Grid")
    st.caption("Click any cell to add a tally mark ( / ). Click repeatedly to add more.")
    
    # Build grid as DataFrame for display
    grid_rows = []
    
    for slot in schedule:
        time = slot['time']
        activity = slot.get('activity', '')
        
        row = {"Time": time, "Activity": activity}
        
        for day in days:
            for beh_idx, beh in enumerate(behaviours):
                cell_key = f"{day['date_obj']}_{time}_{beh_idx}"
                current_value = st.session_state.grid_data.get(cell_key, 0)
                
                # Display tally marks
                if current_value == 0:
                    display = ""
                elif current_value <= 4:
                    display = "/" * current_value
                else:
                    display = str(current_value)
                
                col_name = f"{day['short']}_{beh[:8]}"
                row[col_name] = display
        
        # Row total
        row_total = sum(st.session_state.grid_data.get(f"{d['date_obj']}_{time}_{i}", 0) 
                       for d in days for i in range(len(behaviours)))
        row["Total"] = str(row_total) if row_total > 0 else ""
        
        grid_rows.append(row)
    
    # Add totals row
    totals_row = {"Time": "TOTAL", "Activity": ""}
    week_total = 0
    
    for day in days:
        for beh_idx, beh in enumerate(behaviours):
            day_beh_total = sum(st.session_state.grid_data.get(f"{day['date_obj']}_{s['time']}_{beh_idx}", 0) 
                               for s in schedule)
            col_name = f"{day['short']}_{beh[:8]}"
            totals_row[col_name] = str(day_beh_total) if day_beh_total > 0 else ""
            week_total += day_beh_total
    
    totals_row["Total"] = str(week_total)
    grid_rows.append(totals_row)
    
    # Display grid
    grid_df = pd.DataFrame(grid_rows)
    st.dataframe(grid_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Quick recording interface
    st.markdown("### ✏️ Quick Record")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        record_day = st.selectbox("Day", [d['name'] for d in days])
        day_obj = [d for d in days if d['name'] == record_day][0]['date_obj']
    
    with col2:
        record_time = st.selectbox("Time", [s['time'] for s in schedule])
    
    with col3:
        record_beh = st.selectbox("Behaviour", behaviours)
        beh_idx = behaviours.index(record_beh)
    
    cell_key = f"{day_obj}_{record_time}_{beh_idx}"
    current = st.session_state.grid_data.get(cell_key, 0)
    
    st.info(f"Current value: **{current}** {'/' * current if current <= 4 else ''}")
    
    col_add, col_minus, col_set = st.columns(3)
    
    with col_add:
        if st.button("➕ Add Tally ( / )", use_container_width=True, type="primary"):
            st.session_state.grid_data[cell_key] = current + 1
            st.rerun()
    
    with col_minus:
        if st.button("➖ Remove Tally", use_container_width=True):
            if current > 0:
                st.session_state.grid_data[cell_key] = current - 1
                st.rerun()
    
    with col_set:
        set_value = st.number_input("Or set to:", min_value=0, max_value=20, value=current, key="set_val", label_visibility="collapsed")
        if st.button("✏️ Set", use_container_width=True):
            st.session_state.grid_data[cell_key] = set_value
            st.rerun()
    
    st.markdown("---")
    
    # Save/Load
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Week", use_container_width=True):
            sb = get_sb()
            if sb:
                try:
                    # Save as JSON blob - upsert to update if exists
                    sb.table("scatter_weekly_data").upsert({
                        "student_name": st.session_state.student_name,
                        "week_start": str(week_start),
                        "behaviours": json.dumps(behaviours),
                        "schedule": json.dumps(schedule),
                        "grid_data": json.dumps(st.session_state.grid_data),
                        "created_by": get_staff_name() if hasattr(get_staff_name, '__call__') else "Staff"
                    }, on_conflict="student_name,week_start").execute()
                    st.success("✅ Week saved!")
                except Exception as e:
                    st.error(f"Save failed: {e}")
    
    with col2:
        if st.button("📥 Load Week", use_container_width=True):
            sb = get_sb()
            if sb:
                try:
                    res = sb.table("scatter_weekly_data").select("*").eq("student_name", st.session_state.student_name).eq("week_start", str(week_start)).execute()
                    if res.data:
                        data = res.data[0]
                        st.session_state.grid_data = json.loads(data.get('grid_data', '{}'))
                        st.success("✅ Week loaded!")
                        st.rerun()
                    else:
                        st.info("No saved data for this week")
                except Exception as e:
                    st.error(f"Load failed: {e}")
    
    with col3:
        if st.button("🗑️ Clear All", use_container_width=True):
            if st.checkbox("Confirm clear all data"):
                st.session_state.grid_data = {}
                st.rerun()

# ==============================================================================
# PAGE 4: ANALYSIS
# ==============================================================================
elif st.session_state.page == 'analysis':
    st.markdown("## 📈 Scatter Plot & Analysis")
    
    if not st.session_state.student_name:
        st.warning("⚠️ Select a student in Setup first")
        if st.button("Go to Setup"):
            st.session_state.page = 'setup'
            st.rerun()
        st.stop()
    
    # Load saved weeks for analysis
    @st.cache_data(ttl=30)
    def load_all_weeks(student_name):
        sb = get_sb()
        if not sb: return []
        try:
            res = sb.table("scatter_weekly_data").select("*").eq("student_name", student_name).order("week_start").execute()
            return res.data or []
        except:
            return []
    
    weeks = load_all_weeks(st.session_state.student_name)
    
    if not weeks:
        st.info("No data yet. Record some observations first.")
        st.stop()
    
    # Week selector
    week_options = [f"{pd.to_datetime(w['week_start']).strftime('%-d %b %Y')}" for w in weeks]
    selected_week_idx = st.selectbox("Select Week", range(len(weeks)), format_func=lambda i: week_options[i])
    
    week = weeks[selected_week_idx]
    behaviours = json.loads(week.get('behaviours', '[]'))
    schedule = json.loads(week.get('schedule', '[]'))
    grid_data = json.loads(week.get('grid_data', '{}'))
    week_start = pd.to_datetime(week['week_start']).date()
    
    st.markdown(f"**Week:** {week_start.strftime('%-d %b')} - {(week_start + timedelta(days=4)).strftime('%-d %b %Y')}")
    st.markdown(f"**Behaviours:** {', '.join(behaviours)}")
    
    # Show behaviour definitions
    @st.cache_data(ttl=60)
    def load_student_defs(student_name):
        sb = get_sb()
        if not sb: return {}
        try:
            res = sb.table("scatter_students").select("behaviour_definitions").eq("student_name", student_name).execute()
            if res.data:
                defs = res.data[0].get('behaviour_definitions')
                if defs and isinstance(defs, str):
                    return json.loads(defs)
                return defs or {}
            return {}
        except:
            return {}
    
    beh_defs = load_student_defs(st.session_state.student_name)
    
    # Show definitions prominently
    st.markdown("### 📋 Behaviour Definitions")
    if beh_defs:
        for beh in behaviours:
            if beh in beh_defs:
                st.success(f"**{beh}**")
                st.write(beh_defs[beh])
                st.markdown("")
            else:
                st.warning(f"**{beh}** — No definition recorded")
                st.markdown("")
    else:
        st.info("No behaviour definitions saved for this student")
    
    st.markdown("---")
    
    # Summary stats
    days = [week_start + timedelta(days=i) for i in range(5)]
    total_incidents = sum(grid_data.values())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Incidents", total_incidents)
    with col2:
        avg_per_day = total_incidents / 5 if total_incidents > 0 else 0
        st.metric("Avg Per Day", f"{avg_per_day:.1f}")
    with col3:
        # Peak time
        time_totals = {}
        for slot in schedule:
            time = slot['time']
            time_total = sum(grid_data.get(f"{d}_{time}_{i}", 0) for d in days for i in range(len(behaviours)))
            time_totals[time] = time_total
        peak_time = max(time_totals, key=time_totals.get) if time_totals and max(time_totals.values()) > 0 else "—"
        st.metric("Peak Time", peak_time)
    
    st.markdown("---")
    
    # Build plot data
    plot_data = []
    for day_idx, day in enumerate(days):
        for slot_idx, slot in enumerate(schedule):
            time = slot['time']
            activity = slot.get('activity', '')
            
            for beh_idx, beh in enumerate(behaviours):
                cell_key = f"{day}_{time}_{beh_idx}"
                value = grid_data.get(cell_key, 0)
                
                if value > 0:
                    plot_data.append({
                        "Day": day.strftime("%a %d/%m"),
                        "Time": time,
                        "Activity": activity,
                        "Behaviour": beh,
                        "Count": value
                    })
    
    if plot_data:
        df_plot = pd.DataFrame(plot_data)
        
        # Scatter plot
        st.markdown("### 📍 Scatter Plot")
        fig = px.scatter(
            df_plot,
            x="Day",
            y="Time",
            size="Count",
            color="Behaviour",
            hover_data=["Activity", "Count"],
            title="Behaviour Occurrences by Day and Time",
            height=500
        )
        fig.update_layout(
            yaxis=dict(categoryorder='array', categoryarray=[s['time'] for s in schedule][::-1])
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # By behaviour
        st.markdown("### 📊 By Behaviour")
        beh_totals = df_plot.groupby("Behaviour")["Count"].sum().reset_index()
        fig2 = px.bar(beh_totals, x="Behaviour", y="Count")
        st.plotly_chart(fig2, use_container_width=True)
        
        # By day
        st.markdown("### 📅 By Day")
        day_totals = df_plot.groupby("Day")["Count"].sum().reset_index()
        fig3 = px.bar(day_totals, x="Day", y="Count")
        st.plotly_chart(fig3, use_container_width=True)
        
        # By time
        st.markdown("### ⏰ By Time")
        time_totals = df_plot.groupby("Time")["Count"].sum().reset_index()
        fig4 = px.bar(time_totals, x="Time", y="Count")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No observations recorded yet")

st.markdown("---")
st.caption("🏫 CLC-LBU · Scatter Plot Tracker")
