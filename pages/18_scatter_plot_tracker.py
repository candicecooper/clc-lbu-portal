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

from auth import require_auth, logout_button, get_staff_name
# require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
# logout_button()

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
if st.session_state.page == 'students':
    st.markdown("## 👤 Student Management")
    
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
    
    # Add student
    with st.expander("➕ Add New Student", expanded=not students):
        new_name = st.text_input("Student Name")
        new_prog = st.selectbox("Program", ["JP", "PY", "SY"])
        
        st.markdown("**Optional: Target Behaviours with Definitions**")
        
        # AI Connection Test
        with st.expander("🔧 Test AI Connection (click if AI not working)"):
            if st.button("Test Groq API Connection"):
                try:
                    from groq import Groq
                    api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                    
                    if not api_key:
                        st.error("❌ No API key found. Add GROQ_API_KEY to Render secrets.")
                    else:
                        st.info(f"✓ API key found: {api_key[:8]}...")
                        
                        client = Groq(api_key=api_key)
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": "Say 'test successful'"}],
                            max_tokens=10
                        )
                        
                        st.success(f"✅ AI Working! Response: {response.choices[0].message.content}")
                except ImportError as e:
                    st.error(f"❌ Groq library not installed: {e}")
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")
        
        st.caption("Select from templates below, or use AI to generate custom definitions")
        
        # Pre-built templates
        TEMPLATES = {
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
        
        # Behaviour 1
        st.markdown("**Behaviour 1**")
        
        col1a, col1b = st.columns([1, 1])
        with col1a:
            template1 = st.selectbox("Quick select from templates", list(TEMPLATES.keys()), key="temp1")
        with col1b:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("Or type your own below ↓")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            beh1_name = st.text_input(
                "Behaviour name (select from dropdown OR type custom)", 
                value=template1 if template1 else "",
                key="new_beh1",
                placeholder="e.g., 'Hitting' or 'Interrupting others'"
            )
        with col2:
            if st.button("🤖 AI", key="ai1", use_container_width=True, help="Generate definition with AI"):
                if beh1_name:
                    with st.spinner("Generating..."):
                        try:
                            from groq import Groq
                            api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                            
                            if not api_key:
                                st.error("Add GROQ_API_KEY to Render Environment Variables")
                            else:
                                client = Groq(api_key=api_key)
                                
                                response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{
                                        "role": "user",
                                        "content": f"Write a 2-3 sentence operational definition for the school behaviour '{beh1_name}'. Format: Description. Includes examples. Excludes non-examples."
                                    }],
                                    temperature=0.3,
                                    max_tokens=120
                                )
                                
                                st.session_state['ai_gen1'] = response.choices[0].message.content.strip()
                                st.success("✅ Generated!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"AI Error: {str(e)[:100]}")
        
        # Show definition in prominent box
        def_value = st.session_state.get('ai_gen1', TEMPLATES.get(template1, ''))
        if def_value:
            st.info(f"📋 **Definition:** {def_value}")
        
        beh1_def = st.text_area(
            "Edit definition if needed",
            value=def_value,
            height=80,
            key="def1",
            placeholder="Observable, measurable description"
        )
        
        # Behaviour 2
        st.markdown("**Behaviour 2 (optional)**")
        
        col2a, col2b = st.columns([1, 1])
        with col2a:
            template2 = st.selectbox("Quick select from templates", list(TEMPLATES.keys()), key="temp2")
        with col2b:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("Or type your own below ↓")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            beh2_name = st.text_input(
                "Behaviour name (select from dropdown OR type custom)",
                value=template2 if template2 else "",
                key="new_beh2",
                placeholder="e.g., 'Task refusal' or custom behaviour"
            )
        with col2:
            if st.button("🤖 AI", key="ai2", use_container_width=True):
                if beh2_name:
                    with st.spinner("Generating..."):
                        try:
                            from groq import Groq
                            api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                            
                            if not api_key:
                                st.error("Add GROQ_API_KEY to Render")
                            else:
                                client = Groq(api_key=api_key)
                                
                                response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{
                                        "role": "user",
                                        "content": f"Write a 2-3 sentence operational definition for the school behaviour '{beh2_name}'. Format: Description. Includes examples. Excludes non-examples."
                                    }],
                                    temperature=0.3,
                                    max_tokens=120
                                )
                                
                                st.session_state['ai_gen2'] = response.choices[0].message.content.strip()
                                st.success("✅ Generated!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"AI Error: {str(e)[:100]}")
        
        def_value2 = st.session_state.get('ai_gen2', TEMPLATES.get(template2, ''))
        if def_value2:
            st.info(f"📋 **Definition:** {def_value2}")
        
        beh2_def = st.text_area(
            "Edit definition if needed",
            value=def_value2,
            height=80,
            key="def2"
        )
        
        # Behaviour 3
        st.markdown("**Behaviour 3 (optional)**")
        
        col3a, col3b = st.columns([1, 1])
        with col3a:
            template3 = st.selectbox("Quick select from templates", list(TEMPLATES.keys()), key="temp3")
        with col3b:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("Or type your own below ↓")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            beh3_name = st.text_input(
                "Behaviour name (select from dropdown OR type custom)",
                value=template3 if template3 else "",
                key="new_beh3",
                placeholder="e.g., 'Swearing' or custom behaviour"
            )
        with col2:
            if st.button("🤖 AI", key="ai3", use_container_width=True):
                if beh3_name:
                    with st.spinner("Generating..."):
                        try:
                            from groq import Groq
                            api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                            
                            if not api_key:
                                st.error("Add GROQ_API_KEY to Render")
                            else:
                                client = Groq(api_key=api_key)
                                
                                response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{
                                        "role": "user",
                                        "content": f"Write a 2-3 sentence operational definition for the school behaviour '{beh3_name}'. Format: Description. Includes examples. Excludes non-examples."
                                    }],
                                    temperature=0.3,
                                    max_tokens=120
                                )
                                
                                st.session_state['ai_gen3'] = response.choices[0].message.content.strip()
                                st.success("✅ Generated!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"AI Error: {str(e)[:100]}")
        
        def_value3 = st.session_state.get('ai_gen3', TEMPLATES.get(template3, ''))
        if def_value3:
            st.info(f"📋 **Definition:** {def_value3}")
        
        beh3_def = st.text_area(
            "Edit definition if needed",
            value=def_value3,
            height=80,
            key="def3"
        )
        
        if st.button("Add Student", type="primary", use_container_width=True):
            if new_name:
                # Build definitions dict
                beh_defs = {}
                if beh1_name and beh1_def: beh_defs[beh1_name] = beh1_def
                if beh2_name and beh2_def: beh_defs[beh2_name] = beh2_def
                if beh3_name and beh3_def: beh_defs[beh3_name] = beh3_def
                
                sb = get_sb()
                if sb:
                    try:
                        sb.table("scatter_students").insert({
                            "student_name": new_name,
                            "program_type": new_prog,
                            "behaviour_definitions": json.dumps(beh_defs) if beh_defs else None
                        }).execute()
                        st.success(f"✅ Added {new_name}")
                        # Clear AI generated definitions
                        for key in ['ai_def1', 'ai_def2', 'ai_def3']:
                            if key in st.session_state:
                                del st.session_state[key]
                        load_students.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    # List students
    if students:
        st.markdown("### Current Students")
        for stu in students:
            with st.expander(f"**{stu['student_name']}** ({stu.get('program_type', '-')})"):
                st.markdown(f"**Program:** {stu.get('program_type', 'Not set')}")
                
                # Show behaviour definitions
                beh_defs = stu.get('behaviour_definitions')
                if beh_defs:
                    if isinstance(beh_defs, str):
                        try:
                            beh_defs = json.loads(beh_defs)
                        except:
                            beh_defs = {}
                    
                    if beh_defs:
                        st.markdown("**Target Behaviours:**")
                        for beh_name, beh_def in beh_defs.items():
                            st.markdown(f"- **{beh_name}:** {beh_def}")
                    else:
                        st.caption("No behaviour definitions set")
                else:
                    st.caption("No behaviour definitions set")
                
                st.markdown("---")
                
                if st.button("🗑️ Delete Student", key=f"del_{stu['id']}", use_container_width=True):
                    if st.checkbox(f"Confirm delete {stu['student_name']}", key=f"conf_{stu['id']}"):
                        sb = get_sb()
                        if sb:
                            try:
                                sb.table("scatter_students").delete().eq("id", stu['id']).execute()
                                st.success("✅ Deleted")
                                load_students.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

# ==============================================================================
# PAGE 2: SETUP
# ==============================================================================
elif st.session_state.page == 'setup':
    st.markdown("## 📋 Weekly Setup")
    st.caption("Set up your tracking sheet for the week")
    
    # Student selection
    st.markdown("### 1. Student")
    
    @st.cache_data(ttl=120)
    def load_students():
        sb = get_sb()
        if not sb: return []
        try:
            res = sb.table("scatter_students").select("*").order("student_name").execute()
            return res.data or []
        except:
            return []
    
    students = load_students()
    
    if not students:
        st.warning("⚠️ No students found. Add a student first.")
        new_name = st.text_input("Student Name")
        new_prog = st.selectbox("Program", ["JP", "PY", "SY"])
        if st.button("Add Student", type="primary"):
            sb = get_sb()
            if sb and new_name:
                try:
                    sb.table("scatter_students").insert({
                        "student_name": new_name.strip(),
                        "program_type": new_prog
                    }).execute()
                    st.success(f"✅ Added {new_name}")
                    load_students.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        student_names = [s['student_name'] for s in students]
        selected = st.selectbox(
            "Select Student",
            options=student_names,
            index=student_names.index(st.session_state.student_name) if st.session_state.student_name in student_names else 0
        )
        st.session_state.student_name = selected
    
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
    st.markdown("### 3. Target Behaviours")
    
    # Check if student has pre-defined behaviours
    student_obj = [s for s in students if s['student_name'] == selected][0] if selected else None
    has_predefined = False
    
    if student_obj:
        beh_defs = student_obj.get('behaviour_definitions')
        if beh_defs:
            if isinstance(beh_defs, str):
                try:
                    beh_defs = json.loads(beh_defs)
                    has_predefined = bool(beh_defs)
                except:
                    pass
            else:
                has_predefined = bool(beh_defs)
    
    if has_predefined:
        st.info(f"📋 {selected} has pre-defined behaviours: {', '.join(beh_defs.keys())}")
        if st.button("✨ Use Pre-defined Behaviours", use_container_width=True):
            st.session_state.behaviours = list(beh_defs.keys())[:3]
            st.rerun()
    
    st.caption("Select from templates or type custom behaviour names")
    
    # Behaviour templates
    TEMPLATES = {
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
    
    st.markdown("**For custom behaviours not in templates, type name and click AI to generate definition**")
    
    # Behaviour 1
    col1, col2 = st.columns([4, 1])
    with col1:
        template1 = st.selectbox("Select Behaviour 1 or type custom below", list(TEMPLATES.keys()), key="setup_temp1")
        beh1 = st.text_input(
            "Behaviour 1 name", 
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
                        from groq import Groq
                        api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                        
                        if api_key:
                            client = Groq(api_key=api_key)
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{
                                    "role": "user",
                                    "content": f"Write a 2-3 sentence operational definition for the school behaviour '{beh1}'. Format: Description. Includes examples. Excludes non-examples."
                                }],
                                temperature=0.3,
                                max_tokens=120
                            )
                            
                            # Save to student's behaviour definitions
                            new_def = response.choices[0].message.content.strip()
                            st.session_state[f'setup_def_{beh1}'] = new_def
                            
                            # Update student record
                            sb = get_sb()
                            if sb and st.session_state.student_name:
                                try:
                                    # Get current definitions
                                    res = sb.table("scatter_students").select("behaviour_definitions").eq("student_name", st.session_state.student_name).execute()
                                    current_defs = {}
                                    if res.data:
                                        defs = res.data[0].get('behaviour_definitions')
                                        if defs:
                                            current_defs = json.loads(defs) if isinstance(defs, str) else defs
                                    
                                    # Add new definition
                                    current_defs[beh1] = new_def
                                    
                                    # Save back
                                    sb.table("scatter_students").update({
                                        "behaviour_definitions": json.dumps(current_defs)
                                    }).eq("student_name", st.session_state.student_name).execute()
                                    
                                    st.success("✅ Generated & saved!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Save error: {e}")
                        else:
                            st.error("Add GROQ_API_KEY to Render")
                    except Exception as e:
                        st.error(f"AI Error: {str(e)[:80]}")
    
    # Show definition if available
    def1 = st.session_state.get(f'setup_def_{beh1}', TEMPLATES.get(template1, ''))
    if def1:
        st.info(f"📋 {def1}")
    
    # Behaviour 2
    col1, col2 = st.columns([4, 1])
    with col1:
        template2 = st.selectbox("Select Behaviour 2 (optional)", list(TEMPLATES.keys()), key="setup_temp2")
        beh2 = st.text_input(
            "Behaviour 2 name",
            value=(template2 if template2 and template2 != "—" else st.session_state.get('setup_beh2', '')),
            key="beh2",
            placeholder="Select from dropdown OR type custom"
        )
        # ALWAYS save to session state
        st.session_state['setup_beh2'] = beh2 if beh2 else ''
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🤖 AI", key="setup_ai2", use_container_width=True):
            if beh2:
                # Save behaviour name before generating
                st.session_state['setup_beh2'] = beh2
                
                with st.spinner("Generating..."):
                    try:
                        from groq import Groq
                        api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                        
                        if api_key:
                            client = Groq(api_key=api_key)
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{
                                    "role": "user",
                                    "content": f"Write a 2-3 sentence operational definition for the school behaviour '{beh2}'. Format: Description. Includes examples. Excludes non-examples."
                                }],
                                temperature=0.3,
                                max_tokens=120
                            )
                            
                            new_def = response.choices[0].message.content.strip()
                            st.session_state[f'setup_def_{beh2}'] = new_def
                            
                            sb = get_sb()
                            if sb and st.session_state.student_name:
                                try:
                                    res = sb.table("scatter_students").select("behaviour_definitions").eq("student_name", st.session_state.student_name).execute()
                                    current_defs = {}
                                    if res.data:
                                        defs = res.data[0].get('behaviour_definitions')
                                        if defs:
                                            current_defs = json.loads(defs) if isinstance(defs, str) else defs
                                    
                                    current_defs[beh2] = new_def
                                    
                                    sb.table("scatter_students").update({
                                        "behaviour_definitions": json.dumps(current_defs)
                                    }).eq("student_name", st.session_state.student_name).execute()
                                    
                                    st.success("✅ Generated & saved!")
                                    st.rerun()
                                except:
                                    pass
                        else:
                            st.error("Add GROQ_API_KEY")
                    except Exception as e:
                        st.error(f"AI Error: {str(e)[:80]}")
    
    def2 = st.session_state.get(f'setup_def_{beh2}', TEMPLATES.get(template2, ''))
    if def2:
        st.info(f"📋 {def2}")
    
    # Behaviour 3
    col1, col2 = st.columns([4, 1])
    with col1:
        template3 = st.selectbox("Select Behaviour 3 (optional)", list(TEMPLATES.keys()), key="setup_temp3")
        beh3 = st.text_input(
            "Behaviour 3 name",
            value=(template3 if template3 and template3 != "—" else st.session_state.get('setup_beh3', '')),
            key="beh3",
            placeholder="Select from dropdown OR type custom"
        )
        # ALWAYS save to session state
        st.session_state['setup_beh3'] = beh3 if beh3 else ''
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🤖 AI", key="setup_ai3", use_container_width=True):
            if beh3:
                # Save behaviour name before generating
                st.session_state['setup_beh3'] = beh3
                
                with st.spinner("Generating..."):
                    try:
                        from groq import Groq
                        api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
                        
                        if api_key:
                            client = Groq(api_key=api_key)
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{
                                    "role": "user",
                                    "content": f"Write a 2-3 sentence operational definition for the school behaviour '{beh3}'. Format: Description. Includes examples. Excludes non-examples."
                                }],
                                temperature=0.3,
                                max_tokens=120
                            )
                            
                            new_def = response.choices[0].message.content.strip()
                            st.session_state[f'setup_def_{beh3}'] = new_def
                            
                            sb = get_sb()
                            if sb and st.session_state.student_name:
                                try:
                                    res = sb.table("scatter_students").select("behaviour_definitions").eq("student_name", st.session_state.student_name).execute()
                                    current_defs = {}
                                    if res.data:
                                        defs = res.data[0].get('behaviour_definitions')
                                        if defs:
                                            current_defs = json.loads(defs) if isinstance(defs, str) else defs
                                    
                                    current_defs[beh3] = new_def
                                    
                                    sb.table("scatter_students").update({
                                        "behaviour_definitions": json.dumps(current_defs)
                                    }).eq("student_name", st.session_state.student_name).execute()
                                    
                                    st.success("✅ Generated & saved!")
                                    st.rerun()
                                except:
                                    pass
                        else:
                            st.error("Add GROQ_API_KEY")
                    except Exception as e:
                        st.error(f"AI Error: {str(e)[:80]}")
    
    def3 = st.session_state.get(f'setup_def_{beh3}', TEMPLATES.get(template3, ''))
    if def3:
        st.info(f"📋 {def3}")
    
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
    
    # DEBUG: Show raw values
    with st.expander("🔍 DEBUG - Click to see what values we have", expanded=False):
        st.write("**Widget values:**")
        st.write(f"- beh1 (widget): `{beh1}` (length: {len(beh1) if beh1 else 0})")
        st.write(f"- beh2 (widget): `{beh2}` (length: {len(beh2) if beh2 else 0})")
        st.write(f"- beh3 (widget): `{beh3}` (length: {len(beh3) if beh3 else 0})")
        st.write("")
        st.write("**Session state values:**")
        st.write(f"- setup_beh1: `{st.session_state.get('setup_beh1', 'NOT SET')}`")
        st.write(f"- setup_beh2: `{st.session_state.get('setup_beh2', 'NOT SET')}`")
        st.write(f"- setup_beh3: `{st.session_state.get('setup_beh3', 'NOT SET')}`")
    
    # Build behaviours list from inputs (use template, then widget, then session_state)
    behaviours = []
    
    # Behaviour 1
    val1 = beh1 if beh1 else (template1 if template1 and template1 != "—" else st.session_state.get('setup_beh1', ''))
    if val1 and val1.strip():
        behaviours.append(val1.strip())
        st.write(f"DEBUG: Added behaviour 1: '{val1.strip()}'")
    
    # Behaviour 2  
    val2 = beh2 if beh2 else (template2 if template2 and template2 != "—" else st.session_state.get('setup_beh2', ''))
    if val2 and val2.strip():
        behaviours.append(val2.strip())
        st.write(f"DEBUG: Added behaviour 2: '{val2.strip()}'")
    
    # Behaviour 3
    val3 = beh3 if beh3 else (template3 if template3 and template3 != "—" else st.session_state.get('setup_beh3', ''))
    if val3 and val3.strip():
        behaviours.append(val3.strip())
        st.write(f"DEBUG: Added behaviour 3: '{val3.strip()}'")
    
    st.session_state.behaviours = behaviours
    
    # Debug: Show what will be saved
    if behaviours:
        st.info(f"✅ Ready to track: **{', '.join(behaviours)}** ({len(behaviours)} behaviour(s))")
    else:
        st.error("❌ No behaviours detected!")
    
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
    
    # Debug: Show exactly what we have
    st.success(f"✅ Tracking **{len(behaviours)}** behaviour(s):")
    for i, beh in enumerate(behaviours):
        st.write(f"  {i+1}. {beh}")
    
    if len(behaviours) == 1:
        st.warning("⚠️ Only 1 behaviour detected. If you set up multiple behaviours, they may not have been saved correctly. Check Setup page.")
    
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
