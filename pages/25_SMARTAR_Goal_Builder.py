import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
from urllib.parse import unquote

# ═══════════════════════════════════════════════════════════════════════════════
# Page Config
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="SMARTAR Goal Builder", page_icon="🎯", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
# Check for Team Meetings integration
# ═══════════════════════════════════════════════════════════════════════════════
query_params = st.query_params
from_team_meetings = query_params.get("return_to") == "team_meetings"
meeting_id = query_params.get("meeting_id")
program = query_params.get("program", "")
term = query_params.get("term", "")
week = query_params.get("week", "")
preload_student = unquote(query_params.get("student", "")) if query_params.get("student") else ""

# ═══════════════════════════════════════════════════════════════════════════════
# Database Connection
# ═══════════════════════════════════════════════════════════════════════════════
from supabase import create_client
supabase = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# Integration Status Header
# ═══════════════════════════════════════════════════════════════════════════════
if from_team_meetings:
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a4d8c,#2a6fd4);color:white;border-radius:12px;
                padding:1rem 1.5rem;margin-bottom:1.5rem;">
      <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
                  opacity:0.75;margin-bottom:0.25rem;">🔗 TEAM MEETING INTEGRATION</div>
      <div style="font-size:1.3rem;font-weight:800;margin-bottom:0.25rem;">
        Working on goal for {program} Team Meeting
      </div>
      <div style="font-size:0.85rem;opacity:0.9;">
        {term} Week {week} · Meeting ID: {meeting_id} · Student: {preload_student if preload_student else "Not specified"}
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("← Return to Team Meeting", type="secondary"):
        st.switch_page("pages/3_Team_Meetings.py")

# ═══════════════════════════════════════════════════════════════════════════════
# Groq Client
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_groq():
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

groq_client = get_groq()

def groq_chat(user_msg, system="You are a helpful assistant.", model="llama-3.3-70b-versatile", max_tokens=1500):
    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Groq API error: {e}")
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# SMARTAR Component Options (from SMARTAR Characteristics 2019)
# ═══════════════════════════════════════════════════════════════════════════════
GROUPING_OPTIONS = [
    "Independently",
    "With 1:1 adult support",
    "In a small group (2-4 students)",
    "In a large group (5+ students)",
    "With peer support"
]

TASK_TYPE_OPTIONS = [
    "Structured task",
    "Semi-structured activity",
    "Unstructured/free time",
    "Transition between activities",
    "Self-directed learning"
]

SETTING_OPTIONS = [
    "Classroom",
    "Kitchen",
    "Outdoor/Yard",
    "Playground",
    "Spill-out space",
    "During transitions",
    "Community setting"
]

PROMPT_OPTIONS = [
    "No prompts (independent)",
    "Verbal prompt",
    "Visual prompt",
    "Gestural prompt",
    "Physical prompt",
    "Combination of prompts"
]

RATE_OPTIONS = [
    "On every opportunity",
    "4 out of 5 opportunities",
    "3 out of 5 opportunities",
    "Daily",
    "Weekly",
    "By end of term"
]

GAS_LEVELS = ["EXCEEDING", "ABOVE", "EXPECTED", "BELOW", "NOT YET"]
SESSION_TIMES = ["Morning", "Middle", "Afternoon"]

# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════
def get_all_students():
    """Fetch all students with active SMARTAR goals."""
    try:
        response = supabase.table("smartar_students").select("*").order("student_name").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching students: {e}")
        return []

def get_student_goals(student_name):
    """Fetch all goals for a specific student."""
    try:
        response = supabase.table("smartar_goals").select("*").eq("student_name", student_name).order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching goals: {e}")
        return []

def get_tracking_data(goal_id, days=21):
    """Fetch tracking data for a specific goal."""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        response = supabase.table("smartar_tracking").select("*").eq("goal_id", goal_id).gte("session_date", cutoff).order("session_date", desc=True).order("session_time").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching tracking data: {e}")
        return []

def create_performance_pie_chart(tracking_data, title="Performance Distribution"):
    """Create a pie chart from tracking data."""
    if not tracking_data:
        return None
    
    level_counts = {level: 0 for level in GAS_LEVELS}
    for record in tracking_data:
        level = record["performance_level"]
        if level in level_counts:
            level_counts[level] += 1
    
    # Filter out zero values
    labels = [level for level, count in level_counts.items() if count > 0]
    values = [count for count in level_counts.values() if count > 0]
    
    if not values:
        return None
    
    colors = {
        "EXCEEDING": "#10b981",
        "ABOVE": "#3b82f6",
        "EXPECTED": "#8b5cf6",
        "BELOW": "#f59e0b",
        "NOT YET": "#ef4444"
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=[colors[label] for label in labels]),
        textinfo='label+percent',
        textposition='inside',
        hovertemplate='<b>%{label}</b><br>%{value} sessions<br>%{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title=title,
        showlegend=True,
        height=350,
        margin=dict(t=40, b=0, l=0, r=0)
    )
    
    return fig

def generate_gas_levels(smartar_goal, rate):
    """Use Groq to generate GAS performance level descriptors."""
    system = """You are an educational assessment expert specializing in Goal Attainment Scaling (GAS) for students with diverse learning needs.

Given a SMARTAR goal and success rate, generate 5 performance level descriptors:
- EXCEEDING: Student exceeds the expected goal
- ABOVE: Student performing above expected level
- EXPECTED: Student meeting the goal as written
- BELOW: Student approaching but not yet meeting goal
- NOT YET: Student well below expected performance

Each descriptor should:
1. Be specific and observable
2. Scale appropriately from the base goal
3. Use positive, strengths-based language
4. Be achievable and realistic

Return ONLY a JSON object with keys: exceeding, above, expected, below, not_yet"""

    user_prompt = f"""SMARTAR Goal: {smartar_goal}
Success Rate: {rate}

Generate 5 GAS level descriptors for this goal."""

    try:
        response = groq_chat(user_prompt, system=system, max_tokens=800)
        if response:
            clean = response.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:])
            if clean.endswith("```"):
                clean = clean.rsplit("```", 1)[0]
            data = json.loads(clean)
            return data
    except Exception as e:
        st.error(f"Error generating GAS levels: {e}")
    
    return None

def refine_smartar_goal(components):
    """Use Groq to refine assembled SMARTAR goal into professional language."""
    system = """You are an educational goal-writing expert. Refine the assembled SMARTAR goal into clear, professional, observable language suitable for student IEPs.

Rules:
- Keep it specific and measurable
- Use positive, strengths-based language
- Ensure it's achievable and realistic
- Make it time-bound and contextual
- Write in active voice
- Be concise (1-2 sentences max)

Return ONLY the refined goal text, nothing else."""

    assembled = f"{components['skill']} {components['grouping']} during {components['task_type']} in {components['setting']} with {components['prompts']} {components['rate']}"
    
    try:
        refined = groq_chat(f"Assembled goal: {assembled}\n\nRefine this into a professional SMARTAR goal.", system=system, max_tokens=300)
        return refined.strip() if refined else assembled
    except Exception as e:
        st.error(f"Error refining goal: {e}")
        return assembled

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: GOAL BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
def render_goal_builder():
    st.markdown("## 📋 Goal Builder")
    st.markdown("Build new SMARTAR goals with AI-assisted refinement and GAS level generation.")
    
    # Integration context display
    if from_team_meetings:
        st.info(f"✨ Building goal for **{preload_student}** from {program} Team Meeting ({term} Week {week})")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Student & Exclusion Goal")
        student_name = st.text_input("Student Name", value=preload_student, key="gb_student")
        exclusion_goal = st.text_area("Exclusion Goal (from main school)", height=100, 
                                     help="Paste the exclusion goal provided by the mainstream school", 
                                     key="gb_exclusion")
    
    with col2:
        st.markdown("### SMARTAR Components")
        skill = st.text_input("Skill/Behaviour (what)", placeholder="e.g., 'Will use a calm voice'", key="gb_skill")
        grouping = st.selectbox("Grouping (with whom)", GROUPING_OPTIONS, key="gb_grouping")
        task_type = st.selectbox("Task Type (during what)", TASK_TYPE_OPTIONS, key="gb_task")
        setting = st.selectbox("Setting (where)", SETTING_OPTIONS, key="gb_setting")
        prompts = st.selectbox("Prompts (support level)", PROMPT_OPTIONS, key="gb_prompts")
        rate = st.selectbox("Rate (how often)", RATE_OPTIONS, key="gb_rate")
    
    st.markdown("---")
    
    if st.button("🤖 Refine Goal with AI", type="primary", use_container_width=True):
        if not student_name or not skill:
            st.error("Please enter student name and skill/behaviour.")
        else:
            with st.spinner("Refining SMARTAR goal..."):
                components = {
                    "skill": skill,
                    "grouping": grouping,
                    "task_type": task_type,
                    "setting": setting,
                    "prompts": prompts,
                    "rate": rate
                }
                refined = refine_smartar_goal(components)
                st.session_state["refined_goal"] = refined
                st.session_state["goal_components"] = components
                st.success("Goal refined! Review below.")
                st.rerun()
    
    if "refined_goal" in st.session_state:
        st.markdown("### ✨ Refined SMARTAR Goal")
        refined_goal = st.text_area("Edit if needed", value=st.session_state["refined_goal"], height=100, key="gb_refined_edit")
        
        if st.button("📊 Generate GAS Levels", type="secondary", use_container_width=True):
            with st.spinner("Generating performance level descriptors..."):
                gas_data = generate_gas_levels(refined_goal, st.session_state["goal_components"]["rate"])
                if gas_data:
                    st.session_state["gas_levels"] = gas_data
                    st.success("GAS levels generated! Review and save below.")
                    st.rerun()
    
    if "gas_levels" in st.session_state:
        st.markdown("### 📈 GAS Performance Levels")
        st.markdown("Review and edit each performance level descriptor:")
        
        gas_levels_edit = {}
        for level in ["exceeding", "above", "expected", "below", "not_yet"]:
            label = level.replace("_", " ").upper()
            gas_levels_edit[level] = st.text_area(
                f"**{label}**",
                value=st.session_state["gas_levels"].get(level, ""),
                height=80,
                key=f"gb_gas_{level}"
            )
        
        st.markdown("---")
        
        save_label = "💾 Save Goal & Sync to Team Meeting" if from_team_meetings else "💾 Save Goal to Database"
        
        if st.button(save_label, type="primary", use_container_width=True):
            try:
                # Check if student exists, create if not
                student_check = supabase.table("smartar_students").select("*").eq("student_name", student_name).execute()
                if not student_check.data:
                    supabase.table("smartar_students").insert({"student_name": student_name}).execute()
                
                # Save goal with meeting context if from team meetings
                goal_data = {
                    "student_name": student_name,
                    "exclusion_goal": exclusion_goal,
                    "smartar_goal": refined_goal,
                    "skill": st.session_state["goal_components"]["skill"],
                    "grouping": st.session_state["goal_components"]["grouping"],
                    "task_type": st.session_state["goal_components"]["task_type"],
                    "setting": st.session_state["goal_components"]["setting"],
                    "prompts": st.session_state["goal_components"]["prompts"],
                    "rate": st.session_state["goal_components"]["rate"],
                    "gas_exceeding": gas_levels_edit["exceeding"],
                    "gas_above": gas_levels_edit["above"],
                    "gas_expected": gas_levels_edit["expected"],
                    "gas_below": gas_levels_edit["below"],
                    "gas_not_yet": gas_levels_edit["not_yet"],
                    "active": True
                }
                
                # Add meeting context if from team meetings
                if from_team_meetings and meeting_id:
                    goal_data["meeting_id"] = int(meeting_id)
                    goal_data["program"] = program
                    goal_data["term"] = term
                    goal_data["week"] = week
                
                supabase.table("smartar_goals").insert(goal_data).execute()
                
                if from_team_meetings:
                    st.success(f"✅ Goal saved for {student_name} and synced to {program} Team Meeting!")
                    st.balloons()
                    st.info("Goal will automatically appear in the team meeting minutes. You can return to the meeting now.")
                else:
                    st.success(f"✅ Goal saved for {student_name}!")
                
                # Clear session state
                for key in ["refined_goal", "goal_components", "gas_levels"]:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Error saving goal: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: DAILY TRACKING
# ═══════════════════════════════════════════════════════════════════════════════
def render_daily_tracking():
    st.markdown("## 📊 Daily Tracking")
    st.markdown("Record session-by-session performance levels for active goals.")
    
    students = get_all_students()
    if not students:
        st.info("No students with active goals yet. Create a goal in the Goal Builder tab.")
        return
    
    student_names = [s["student_name"] for s in students]
    
    # Pre-select student if from team meetings
    default_idx = 0
    if from_team_meetings and preload_student in student_names:
        default_idx = student_names.index(preload_student)
    
    selected_student = st.selectbox("Select Student", student_names, index=default_idx, key="dt_student")
    
    if selected_student:
        goals = get_student_goals(selected_student)
        active_goals = [g for g in goals if g.get("active", True)]
        
        if not active_goals:
            st.info(f"No active goals for {selected_student}. Create a goal in the Goal Builder tab.")
            return
        
        goal_options = [f"{g['smartar_goal'][:60]}..." if len(g['smartar_goal']) > 60 else g['smartar_goal'] for g in active_goals]
        selected_goal_idx = st.selectbox("Select Goal", range(len(goal_options)), format_func=lambda i: goal_options[i], key="dt_goal")
        
        goal = active_goals[selected_goal_idx]
        
        st.markdown("---")
        st.markdown("### 🎯 Goal Details")
        st.info(f"**SMARTAR Goal:** {goal['smartar_goal']}")
        
        # Display GAS levels
        with st.expander("📈 View GAS Performance Levels"):
            for level, label in [("gas_exceeding", "EXCEEDING"), ("gas_above", "ABOVE"), 
                                ("gas_expected", "EXPECTED"), ("gas_below", "BELOW"), ("gas_not_yet", "NOT YET")]:
                st.markdown(f"**{label}:** {goal.get(level, 'Not set')}")
        
        st.markdown("---")
        st.markdown("### 📅 Today's Tracking")
        
        today = date.today().isoformat()
        
        # Check existing tracking for today
        existing_tracking = supabase.table("smartar_tracking").select("*").eq("goal_id", goal["id"]).eq("session_date", today).execute()
        tracked_sessions = {t["session_time"]: t["performance_level"] for t in (existing_tracking.data or [])}
        
        col1, col2, col3 = st.columns(3)
        
        for col, session in zip([col1, col2, col3], SESSION_TIMES):
            with col:
                st.markdown(f"**{session} Session**")
                if session in tracked_sessions:
                    st.success(f"✅ Recorded: {tracked_sessions[session]}")
                else:
                    for level in GAS_LEVELS:
                        if st.button(level, key=f"dt_{session}_{level}", use_container_width=True):
                            try:
                                supabase.table("smartar_tracking").insert({
                                    "goal_id": goal["id"],
                                    "student_name": selected_student,
                                    "session_date": today,
                                    "session_time": session,
                                    "performance_level": level
                                }).execute()
                                st.success(f"✅ {session} session recorded: {level}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving: {e}")
        
        # Add 21-day performance pie chart
        st.markdown("---")
        st.markdown("### 📊 21-Day Performance Distribution")
        tracking_data = get_tracking_data(goal["id"], days=21)
        if tracking_data:
            pie_chart = create_performance_pie_chart(tracking_data, f"Last 21 Days - {len(tracking_data)} Sessions")
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True)
        else:
            st.info("No tracking data yet. Start recording sessions above!")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: CLASS DASHBOARD (keep existing code)
# TAB 4: PROGRESS REPORT (keep existing code)
# ═══════════════════════════════════════════════════════════════════════════════

def render_class_dashboard():
    # ... [Keep all existing class dashboard code]
    pass

def render_progress_report():
    # ... [Keep all existing progress report code]
    pass

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.title("🎯 SMARTAR Goal Builder")
    
    if from_team_meetings:
        st.markdown("**Team Meeting Integration Active** — Goals will sync back to meeting minutes")
    else:
        st.markdown("Build, track, and report on student SMARTAR goals with GAS performance levels.")
    
    tab = st.radio(
        "Navigation",
        ["📋 Goal Builder", "📊 Daily Tracking", "🏫 Class Dashboard", "📈 Progress Report"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    if tab == "📋 Goal Builder":
        render_goal_builder()
    elif tab == "📊 Daily Tracking":
        render_daily_tracking()
    elif tab == "🏫 Class Dashboard":
        render_class_dashboard()
    elif tab == "📈 Progress Report":
        render_progress_report()
    
    # Show integration status in sidebar
    if from_team_meetings:
        with st.sidebar:
            st.markdown("### 🔗 Integration Status")
            st.success("✅ Connected to Team Meeting")
            st.markdown(f"**Program:** {program}")
            st.markdown(f"**Term:** {term} Week {week}")
            if meeting_id:
                st.markdown(f"**Meeting ID:** {meeting_id}")
            if preload_student:
                st.markdown(f"**Student:** {preload_student}")

if __name__ == "__main__":
    main()
