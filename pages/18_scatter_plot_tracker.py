# ==============================================================================
# 18_Scatter_Plot_Tracker.py - CLC-LBU Portal
# Paper-Style Scatter Plot with Student Details & Analysis
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
.saved-week {
    background:#f0f9ff; border-left:4px solid #0284c7;
    padding:.8rem 1rem; border-radius:6px; margin:.5rem 0;
    cursor:pointer;
}
.saved-week:hover { background:#e0f2fe; }
.active-week {
    background:#dcfce7; border-left:4px solid #22c55e;
}
.info-box {
    background:#f0f9ff; border-left:4px solid #0284c7;
    padding:.7rem 1rem; border-radius:6px; margin:.5rem 0;
}
.tally { color:#dc2626; font-weight:700; font-size:1.1rem; }
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
    if 'week_id' not in st.session_state:
        st.session_state.week_id = None
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
<p>Weekly behaviour recording with student details and analysis</p>
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
    if st.button("📋 Setup Week", use_container_width=True, type="primary" if st.session_state.page == 'setup' else "secondary"):
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
# PAGE 1: STUDENT DETAILS
# ==============================================================================
if st.session_state.page == 'students':
    st.markdown("## 👤 Student Details")
    
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
    
    tab1, tab2 = st.tabs(["📋 Manage Students", "➕ Add Student"])
    
    with tab1:
        if not students:
            st.info("No students yet. Add one in the 'Add Student' tab.")
        else:
            for stu in students:
                with st.expander(f"**{stu['student_name']}** ({stu.get('program_type', '-')})"):
                    st.markdown(f"**Program:** {stu.get('program_type', 'Not set')}")
                    st.markdown(f"**Added:** {pd.to_datetime(stu['created_at']).strftime('%-d %b %Y')}")
                    
                    # Behaviour definitions
                    st.markdown("### Target Behaviours & Definitions")
                    
                    beh_defs = stu.get('behaviour_definitions', {})
                    if isinstance(beh_defs, str):
                        try:
                            beh_defs = json.loads(beh_defs)
                        except:
                            beh_defs = {}
                    
                    if beh_defs:
                        for beh, defn in beh_defs.items():
                            st.markdown(f"**{beh}:** {defn}")
                    else:
                        st.caption("No behaviour definitions set")
                    
                    # Edit
                    st.markdown("---")
                    edit_name = st.text_input("Name", value=stu['student_name'], key=f"edit_name_{stu['id']}")
                    edit_prog = st.selectbox("Program", ["JP", "PY", "SY"], 
                                            index=["JP", "PY", "SY"].index(stu.get('program_type', 'PY')) if stu.get('program_type') in ["JP", "PY", "SY"] else 1,
                                            key=f"edit_prog_{stu['id']}")
                    
                    # Behaviour definitions editor
                    st.markdown("**Behaviour Definitions:**")
                    st.caption("Click ✨ Generate for AI-suggested definitions")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        beh1_name = st.text_input("Behaviour 1", key=f"b1n_{stu['id']}")
                    with col2:
                        if st.button("✨", key=f"gen1_{stu['id']}", use_container_width=True):
                            if beh1_name:
                                try:
                                    from groq import Groq
                                    groq_client = Groq(api_key=st.secrets.get("groq", {}).get("api_key", ""))
                                    
                                    prompt = f"""Create a concise operational definition for the behaviour "{beh1_name}" suitable for school behaviour tracking. 

Requirements:
- Observable and measurable
- Clear and specific
- 2-3 sentences maximum
- Include what it looks like
- No medical/diagnostic language

Format: Just the definition, no preamble."""
                                    
                                    response = groq_client.chat.completions.create(
                                        model="llama-3.3-70b-versatile",
                                        messages=[{"role": "user", "content": prompt}],
                                        temperature=0.3,
                                        max_tokens=200
                                    )
                                    
                                    definition = response.choices[0].message.content.strip()
                                    st.session_state[f'edit_gen1_{stu["id"]}'] = definition
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    beh1_def = st.text_area(
                        "Definition 1", 
                        value=st.session_state.get(f'edit_gen1_{stu["id"]}', ''),
                        key=f"b1d_{stu['id']}", 
                        height=60
                    )
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        beh2_name = st.text_input("Behaviour 2", key=f"b2n_{stu['id']}")
                    with col2:
                        if st.button("✨", key=f"gen2_{stu['id']}", use_container_width=True):
                            if beh2_name:
                                try:
                                    from groq import Groq
                                    groq_client = Groq(api_key=st.secrets.get("groq", {}).get("api_key", ""))
                                    
                                    prompt = f"""Create a concise operational definition for the behaviour "{beh2_name}" suitable for school behaviour tracking. 

Requirements:
- Observable and measurable
- Clear and specific
- 2-3 sentences maximum
- Include what it looks like
- No medical/diagnostic language

Format: Just the definition, no preamble."""
                                    
                                    response = groq_client.chat.completions.create(
                                        model="llama-3.3-70b-versatile",
                                        messages=[{"role": "user", "content": prompt}],
                                        temperature=0.3,
                                        max_tokens=200
                                    )
                                    
                                    definition = response.choices[0].message.content.strip()
                                    st.session_state[f'edit_gen2_{stu["id"]}'] = definition
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    beh2_def = st.text_area(
                        "Definition 2",
                        value=st.session_state.get(f'edit_gen2_{stu["id"]}', ''),
                        key=f"b2d_{stu['id']}", 
                        height=60
                    )
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        beh3_name = st.text_input("Behaviour 3", key=f"b3n_{stu['id']}")
                    with col2:
                        if st.button("✨", key=f"gen3_{stu['id']}", use_container_width=True):
                            if beh3_name:
                                try:
                                    from groq import Groq
                                    groq_client = Groq(api_key=st.secrets.get("groq", {}).get("api_key", ""))
                                    
                                    prompt = f"""Create a concise operational definition for the behaviour "{beh3_name}" suitable for school behaviour tracking. 

Requirements:
- Observable and measurable
- Clear and specific
- 2-3 sentences maximum
- Include what it looks like
- No medical/diagnostic language

Format: Just the definition, no preamble."""
                                    
                                    response = groq_client.chat.completions.create(
                                        model="llama-3.3-70b-versatile",
                                        messages=[{"role": "user", "content": prompt}],
                                        temperature=0.3,
                                        max_tokens=200
                                    )
                                    
                                    definition = response.choices[0].message.content.strip()
                                    st.session_state[f'edit_gen3_{stu["id"]}'] = definition
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    beh3_def = st.text_area(
                        "Definition 3",
                        value=st.session_state.get(f'edit_gen3_{stu["id"]}', ''),
                        key=f"b3d_{stu['id']}", 
                        height=60
                    )
                    
                    new_defs = {}
                    if beh1_name: new_defs[beh1_name] = beh1_def
                    if beh2_name: new_defs[beh2_name] = beh2_def
                    if beh3_name: new_defs[beh3_name] = beh3_def
                    
                    col_save, col_del = st.columns(2)
                    with col_save:
                        if st.button("💾 Update", key=f"save_{stu['id']}", use_container_width=True):
                            sb = get_sb()
                            if sb and edit_name:
                                try:
                                    sb.table("scatter_students").update({
                                        "student_name": edit_name,
                                        "program_type": edit_prog,
                                        "behaviour_definitions": json.dumps(new_defs)
                                    }).eq("id", stu['id']).execute()
                                    st.success("✅ Updated!")
                                    load_students.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_{stu['id']}", use_container_width=True):
                            if st.checkbox(f"Confirm delete {stu['student_name']}", key=f"confirm_{stu['id']}"):
                                sb = get_sb()
                                if sb:
                                    try:
                                        sb.table("scatter_students").delete().eq("id", stu['id']).execute()
                                        st.success("✅ Deleted!")
                                        load_students.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
    
    with tab2:
        st.markdown("### Add New Student")
        new_name = st.text_input("Student Name")
        new_prog = st.selectbox("Program", ["JP", "PY", "SY"])
        
        st.markdown("**Optional: Add Behaviour Definitions**")
        st.caption("Type a behaviour name and click 'Generate Definition' for an AI-suggested operational definition")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_beh1_name = st.text_input("Behaviour 1 Name", key="new_b1n")
        with col2:
            if st.button("✨ Generate", key="gen_b1", use_container_width=True):
                if new_beh1_name:
                    # Generate definition using Groq
                    try:
                        from groq import Groq
                        groq_client = Groq(api_key=st.secrets.get("groq", {}).get("api_key", ""))
                        
                        prompt = f"""Create a concise operational definition for the behaviour "{new_beh1_name}" suitable for school behaviour tracking. 

Requirements:
- Observable and measurable
- Clear and specific
- 2-3 sentences maximum
- Include what it looks like
- No medical/diagnostic language

Format: Just the definition, no preamble."""
                        
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            max_tokens=200
                        )
                        
                        definition = response.choices[0].message.content.strip()
                        st.session_state['gen_def_b1'] = definition
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate: {e}")
        
        new_beh1_def = st.text_area(
            "Behaviour 1 Definition", 
            value=st.session_state.get('gen_def_b1', ''),
            height=80,
            key="new_b1d"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_beh2_name = st.text_input("Behaviour 2 Name", key="new_b2n")
        with col2:
            if st.button("✨ Generate", key="gen_b2", use_container_width=True):
                if new_beh2_name:
                    try:
                        from groq import Groq
                        groq_client = Groq(api_key=st.secrets.get("groq", {}).get("api_key", ""))
                        
                        prompt = f"""Create a concise operational definition for the behaviour "{new_beh2_name}" suitable for school behaviour tracking. 

Requirements:
- Observable and measurable
- Clear and specific
- 2-3 sentences maximum
- Include what it looks like
- No medical/diagnostic language

Format: Just the definition, no preamble."""
                        
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            max_tokens=200
                        )
                        
                        definition = response.choices[0].message.content.strip()
                        st.session_state['gen_def_b2'] = definition
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate: {e}")
        
        new_beh2_def = st.text_area(
            "Behaviour 2 Definition",
            value=st.session_state.get('gen_def_b2', ''),
            height=80,
            key="new_b2d"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_beh3_name = st.text_input("Behaviour 3 Name", key="new_b3n")
        with col2:
            if st.button("✨ Generate", key="gen_b3", use_container_width=True):
                if new_beh3_name:
                    try:
                        from groq import Groq
                        groq_client = Groq(api_key=st.secrets.get("groq", {}).get("api_key", ""))
                        
                        prompt = f"""Create a concise operational definition for the behaviour "{new_beh3_name}" suitable for school behaviour tracking. 

Requirements:
- Observable and measurable
- Clear and specific
- 2-3 sentences maximum
- Include what it looks like
- No medical/diagnostic language

Format: Just the definition, no preamble."""
                        
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            max_tokens=200
                        )
                        
                        definition = response.choices[0].message.content.strip()
                        st.session_state['gen_def_b3'] = definition
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate: {e}")
        
        new_beh3_def = st.text_area(
            "Behaviour 3 Definition",
            value=st.session_state.get('gen_def_b3', ''),
            height=80,
            key="new_b3d"
        )
        
        if st.button("➕ Add Student", type="primary", use_container_width=True):
            if not new_name:
                st.error("Name required")
            else:
                beh_defs = {}
                if new_beh1_name: beh_defs[new_beh1_name] = new_beh1_def
                if new_beh2_name: beh_defs[new_beh2_name] = new_beh2_def
                
                sb = get_sb()
                if sb:
                    try:
                        sb.table("scatter_students").insert({
                            "student_name": new_name,
                            "program_type": new_prog,
                            "behaviour_definitions": json.dumps(beh_defs) if beh_defs else None
                        }).execute()
                        st.success(f"✅ Added {new_name}!")
                        load_students.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ==============================================================================
# PAGE 2: SETUP WEEK
# ==============================================================================
elif st.session_state.page == 'setup':
    st.markdown("## 📋 Setup Week")
    
    # Student selection
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
    
    if not students:
        st.warning("⚠️ No students. Go to Students page to add one.")
        st.stop()
    
    # Load saved weeks for this student
    @st.cache_data(ttl=30)
    def load_saved_weeks(student_name):
        sb = get_sb()
        if not sb: return []
        try:
            res = sb.table("scatter_weekly_data").select("*").eq("student_name", student_name).order("week_start", desc=True).execute()
            return res.data or []
        except:
            return []
    
    st.markdown("### 1. Select Student")
    student_names = [s['student_name'] for s in students]
    selected = st.selectbox(
        "Student",
        options=student_names,
        index=student_names.index(st.session_state.student_name) if st.session_state.student_name in student_names else 0
    )
    st.session_state.student_name = selected
    
    # Show saved weeks
    saved_weeks = load_saved_weeks(selected)
    
    if saved_weeks:
        st.markdown("### 📚 Saved Weeks - Click to Resume")
        for week in saved_weeks:
            week_start = pd.to_datetime(week['week_start']).date()
            week_end = week_start + timedelta(days=4)
            behs = json.loads(week.get('behaviours', '[]'))
            
            # Count observations
            grid_data = json.loads(week.get('grid_data', '{}'))
            obs_count = sum(1 for v in grid_data.values() if v > 0)
            
            is_active = st.session_state.week_id == week['id']
            card_class = "saved-week active-week" if is_active else "saved-week"
            
            st.markdown(f"<div class='{card_class}'>📅 <b>{week_start.strftime('%-d %b')} - {week_end.strftime('%-d %b %Y')}</b><br>Behaviours: {', '.join(behs)}<br>Observations: {obs_count}</div>", unsafe_allow_html=True)
            
            if st.button(f"Load This Week", key=f"load_{week['id']}", use_container_width=True):
                st.session_state.week_id = week['id']
                st.session_state.week_start = week_start
                st.session_state.behaviours = behs
                st.session_state.schedule = json.loads(week.get('schedule', '[]'))
                st.session_state.grid_data = grid_data
                st.success(f"✅ Loaded week {week_start.strftime('%-d %b')}")
                load_saved_weeks.clear()
                st.rerun()
        
        st.markdown("---")
    
    st.markdown("### 2. Create New Week")
    
    col1, col2 = st.columns(2)
    with col1:
        week_start = st.date_input(
            "Monday (start of week)",
            value=st.session_state.week_start,
            help="Select the Monday"
        )
    with col2:
        week_end = week_start + timedelta(days=4)
        st.info(f"📅 Week: {week_start.strftime('%-d %b')} - {week_end.strftime('%-d %b %Y')}")
    
    # Get student's predefined behaviours
    student = [s for s in students if s['student_name'] == selected][0]
    beh_defs = student.get('behaviour_definitions', {})
    if isinstance(beh_defs, str):
        try:
            beh_defs = json.loads(beh_defs)
        except:
            beh_defs = {}
    
    st.markdown("### 3. Target Behaviours")
    
    if beh_defs:
        st.info(f"📋 Pre-defined behaviours for {selected}: {', '.join(beh_defs.keys())}")
        use_predefined = st.checkbox("Use pre-defined behaviours", value=True)
        
        if use_predefined:
            behaviours = list(beh_defs.keys())
        else:
            beh1 = st.text_input("Behaviour 1", value=st.session_state.behaviours[0] if len(st.session_state.behaviours) > 0 else "")
            beh2 = st.text_input("Behaviour 2", value=st.session_state.behaviours[1] if len(st.session_state.behaviours) > 1 else "")
            beh3 = st.text_input("Behaviour 3", value=st.session_state.behaviours[2] if len(st.session_state.behaviours) > 2 else "")
            behaviours = [b.strip() for b in [beh1, beh2, beh3] if b.strip()]
    else:
        beh1 = st.text_input("Behaviour 1", value=st.session_state.behaviours[0] if len(st.session_state.behaviours) > 0 else "")
        beh2 = st.text_input("Behaviour 2", value=st.session_state.behaviours[1] if len(st.session_state.behaviours) > 1 else "")
        beh3 = st.text_input("Behaviour 3", value=st.session_state.behaviours[2] if len(st.session_state.behaviours) > 2 else "")
        behaviours = [b.strip() for b in [beh1, beh2, beh3] if b.strip()]
    
    st.markdown("### 4. Daily Schedule")
    
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
    st.session_state.behaviours = behaviours
    st.session_state.week_start = week_start
    
    if st.button("✅ Save & Start Recording", type="primary", use_container_width=True):
        if not behaviours:
            st.error("❌ Add at least one behaviour")
        else:
            sb = get_sb()
            if sb:
                try:
                    # Create new week
                    result = sb.table("scatter_weekly_data").insert({
                        "student_name": selected,
                        "week_start": str(week_start),
                        "behaviours": json.dumps(behaviours),
                        "schedule": json.dumps(st.session_state.schedule),
                        "grid_data": json.dumps({})
                    }).execute()
                    
                    st.session_state.week_id = result.data[0]['id']
                    st.session_state.grid_data = {}
                    st.success("✅ Week created!")
                    load_saved_weeks.clear()
                    st.session_state.page = 'record'
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ==============================================================================
# PAGE 3: RECORDING
# ==============================================================================
elif st.session_state.page == 'record':
    
    if not st.session_state.student_name or not st.session_state.week_id:
        st.warning("⚠️ Please set up a week first")
        if st.button("Go to Setup"):
            st.session_state.page = 'setup'
            st.rerun()
        st.stop()
    
    st.markdown(f"## ✏️ Recording: {st.session_state.student_name}")
    
    week_start = st.session_state.week_start
    week_end = week_start + timedelta(days=4)
    
    st.markdown(f"<div class='info-box'><b>Week:</b> {week_start.strftime('%-d %b')} - {week_end.strftime('%-d %b %Y')} | <b>Behaviours:</b> {', '.join(st.session_state.behaviours)}</div>", unsafe_allow_html=True)
    
    # Auto-save button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("💾 Save Now", use_container_width=True):
            sb = get_sb()
            if sb:
                try:
                    sb.table("scatter_weekly_data").update({
                        "grid_data": json.dumps(st.session_state.grid_data)
                    }).eq("id", st.session_state.week_id).execute()
                    st.success("✅ Saved!")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # Days
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
    
    # Build grid
    st.markdown("### 📊 Weekly Grid")
    st.caption("Tally marks: blank = 0, / = 1, // = 2, /// = 3, //// = 4, 5+ = number")
    
    grid_rows = []
    
    for slot in schedule:
        time = slot['time']
        activity = slot.get('activity', '')
        
        row = {"Time": time, "Activity": activity}
        
        for day in days:
            for beh_idx, beh in enumerate(behaviours):
                cell_key = f"{day['date_obj']}_{time}_{beh_idx}"
                current_value = st.session_state.grid_data.get(cell_key, 0)
                
                if current_value == 0:
                    display = ""
                elif current_value <= 4:
                    display = "/" * current_value
                else:
                    display = str(current_value)
                
                col_name = f"{day['short']}_{beh[:8]}"
                row[col_name] = display
        
        row_total = sum(st.session_state.grid_data.get(f"{d['date_obj']}_{time}_{i}", 0) 
                       for d in days for i in range(len(behaviours)))
        row["Total"] = str(row_total) if row_total > 0 else ""
        
        grid_rows.append(row)
    
    # Totals row
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
    
    grid_df = pd.DataFrame(grid_rows)
    st.dataframe(grid_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Quick recording
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
            # Auto-save
            sb = get_sb()
            if sb:
                try:
                    sb.table("scatter_weekly_data").update({
                        "grid_data": json.dumps(st.session_state.grid_data)
                    }).eq("id", st.session_state.week_id).execute()
                except:
                    pass
            st.rerun()
    
    with col_minus:
        if st.button("➖ Remove Tally", use_container_width=True):
            if current > 0:
                st.session_state.grid_data[cell_key] = current - 1
                sb = get_sb()
                if sb:
                    try:
                        sb.table("scatter_weekly_data").update({
                            "grid_data": json.dumps(st.session_state.grid_data)
                        }).eq("id", st.session_state.week_id).execute()
                    except:
                        pass
                st.rerun()
    
    with col_set:
        set_value = st.number_input("Set to:", min_value=0, max_value=20, value=current, label_visibility="collapsed")
        if st.button("✏️ Set", use_container_width=True):
            st.session_state.grid_data[cell_key] = set_value
            sb = get_sb()
            if sb:
                try:
                    sb.table("scatter_weekly_data").update({
                        "grid_data": json.dumps(st.session_state.grid_data)
                    }).eq("id", st.session_state.week_id).execute()
                except:
                    pass
            st.rerun()

# ==============================================================================
# PAGE 4: ANALYSIS
# ==============================================================================
elif st.session_state.page == 'analysis':
    st.markdown("## 📈 Scatter Plot & Analysis")
    
    if not st.session_state.student_name:
        st.warning("⚠️ Select a student first")
        if st.button("Go to Setup"):
            st.session_state.page = 'setup'
            st.rerun()
        st.stop()
    
    # Load all weeks for this student
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
    week_options = [f"{pd.to_datetime(w['week_start']).strftime('%-d %b %Y')} - {(pd.to_datetime(w['week_start']) + timedelta(days=4)).strftime('%-d %b')}" for w in weeks]
    selected_week_idx = st.selectbox("Select Week to Analyze", range(len(weeks)), format_func=lambda i: week_options[i])
    
    week = weeks[selected_week_idx]
    behaviours = json.loads(week.get('behaviours', '[]'))
    schedule = json.loads(week.get('schedule', '[]'))
    grid_data = json.loads(week.get('grid_data', '{}'))
    week_start = pd.to_datetime(week['week_start']).date()
    
    st.markdown(f"### Analysis: {st.session_state.student_name}")
    st.markdown(f"**Week:** {week_start.strftime('%-d %b')} - {(week_start + timedelta(days=4)).strftime('%-d %b %Y')}")
    st.markdown(f"**Behaviours:** {', '.join(behaviours)}")
    
    st.markdown("---")
    
    # Summary stats
    st.markdown("### 📊 Summary Statistics")
    
    days = []
    for i in range(5):
        day_date = week_start + timedelta(days=i)
        days.append(day_date)
    
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
        peak_time = max(time_totals, key=time_totals.get) if time_totals else "—"
        st.metric("Peak Time", peak_time)
    
    st.markdown("---")
    
    # Scatter plot visualization
    st.markdown("### 📍 Scatter Plot Visualization")
    
    # Build data for plotting
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
                        "Day_num": day_idx,
                        "Time": time,
                        "Time_num": slot_idx,
                        "Activity": activity,
                        "Behaviour": beh,
                        "Count": value
                    })
    
    if plot_data:
        df_plot = pd.DataFrame(plot_data)
        
        # Create scatter plot
        fig = px.scatter(
            df_plot,
            x="Day",
            y="Time",
            size="Count",
            color="Behaviour",
            hover_data=["Activity", "Count"],
            title="Behaviour Occurrences by Day and Time",
            height=600
        )
        
        fig.update_layout(
            yaxis=dict(categoryorder='array', categoryarray=[s['time'] for s in schedule][::-1]),
            xaxis=dict(categoryorder='category ascending')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # By behaviour chart
        st.markdown("### 📊 By Behaviour")
        beh_totals = df_plot.groupby("Behaviour")["Count"].sum().reset_index()
        fig2 = px.bar(beh_totals, x="Behaviour", y="Count", title="Total Incidents by Behaviour")
        st.plotly_chart(fig2, use_container_width=True)
        
        # By day chart
        st.markdown("### 📅 By Day")
        day_totals = df_plot.groupby("Day")["Count"].sum().reset_index()
        fig3 = px.bar(day_totals, x="Day", y="Count", title="Total Incidents by Day")
        st.plotly_chart(fig3, use_container_width=True)
        
        # By time chart
        st.markdown("### ⏰ By Time")
        time_totals = df_plot.groupby("Time")["Count"].sum().reset_index()
        fig4 = px.bar(time_totals, x="Time", y="Count", title="Total Incidents by Time")
        st.plotly_chart(fig4, use_container_width=True)
        
        # Pattern analysis
        st.markdown("### 🔍 Pattern Analysis")
        
        # Find patterns
        patterns = []
        
        # Peak day
        peak_day_data = day_totals.loc[day_totals['Count'].idxmax()]
        patterns.append(f"**Peak day:** {peak_day_data['Day']} ({peak_day_data['Count']} incidents)")
        
        # Peak time
        peak_time_data = time_totals.loc[time_totals['Count'].idxmax()]
        patterns.append(f"**Peak time:** {peak_time_data['Time']} ({peak_time_data['Count']} incidents)")
        
        # Most common behaviour
        peak_beh_data = beh_totals.loc[beh_totals['Count'].idxmax()]
        patterns.append(f"**Most frequent behaviour:** {peak_beh_data['Behaviour']} ({peak_beh_data['Count']} incidents)")
        
        for p in patterns:
            st.markdown(f"- {p}")
        
    else:
        st.info("No observations recorded for this week yet")

st.markdown("---")
st.caption("🏫 CLC-LBU · Scatter Plot Tracker")
