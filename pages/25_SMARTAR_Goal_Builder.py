import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from groq import Groq
import json

# ═══════════════════════════════════════════════════════════════════════════════
# Page Config
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="SMARTAR Goal Builder", page_icon="🎯", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
# Database Connection - Direct connection to bypass cache issues
# ═══════════════════════════════════════════════════════════════════════════════
from supabase import create_client
supabase = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORARY DEBUG - Remove after testing
# ═══════════════════════════════════════════════════════════════════════════════
st.write("🔍 DEBUG INFO:")
st.write(f"**Supabase URL:** {st.secrets['supabase']['url']}")
st.write(f"**Expected project:** lvzaebjrxrgguypqvdcq")

# Test if we can query an existing table
try:
    test = supabase.table("tm_documents").select("*").limit(1).execute()
    st.success(f"✅ Can connect! Found {len(test.data)} tm_documents")
except Exception as e:
    st.error(f"❌ Connection test failed: {e}")

# Test if smartar_students is accessible
try:
    test2 = supabase.table("smartar_students").select("*").limit(1).execute()
    st.success(f"✅ smartar_students accessible! Found {len(test2.data)} students")
except Exception as e:
    st.error(f"❌ smartar_students error: {e}")
st.write("---")

# ═══════════════════════════════════════════════════════════════════════════════
# Groq Client - FIXED to use GROQ_API_KEY format
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
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Student & Exclusion Goal")
        student_name = st.text_input("Student Name", key="gb_student")
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
        
        if st.button("💾 Save Goal to Database", type="primary", use_container_width=True):
            try:
                # Check if student exists, create if not
                student_check = supabase.table("smartar_students").select("*").eq("student_name", student_name).execute()
                if not student_check.data:
                    supabase.table("smartar_students").insert({"student_name": student_name}).execute()
                
                # Save goal
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
                
                supabase.table("smartar_goals").insert(goal_data).execute()
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
    selected_student = st.selectbox("Select Student", student_names, key="dt_student")
    
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

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: CLASS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def render_class_dashboard():
    st.markdown("## 🏫 Class Dashboard")
    st.markdown("Overview of all students and their goal progress.")
    
    students = get_all_students()
    if not students:
        st.info("No students with active goals yet.")
        return
    
    today = date.today().isoformat()
    
    for student in students:
        goals = get_student_goals(student["student_name"])
        active_goals = [g for g in goals if g.get("active", True)]
        
        if not active_goals:
            continue
        
        with st.expander(f"**{student['student_name']}** ({len(active_goals)} active goal{'s' if len(active_goals) > 1 else ''})", expanded=False):
            for goal in active_goals:
                st.markdown(f"**Goal:** {goal['smartar_goal']}")
                
                # Today's sessions
                today_tracking = supabase.table("smartar_tracking").select("*").eq("goal_id", goal["id"]).eq("session_date", today).execute()
                tracked_today = {t["session_time"]: t["performance_level"] for t in (today_tracking.data or [])}
                
                col1, col2, col3 = st.columns(3)
                for col, session in zip([col1, col2, col3], SESSION_TIMES):
                    with col:
                        if session in tracked_today:
                            st.success(f"{session}: {tracked_today[session]}")
                        else:
                            st.warning(f"{session}: Not recorded")
                
                # 21-day progress bar
                tracking_data = get_tracking_data(goal["id"], days=21)
                if tracking_data:
                    level_counts = {level: 0 for level in GAS_LEVELS}
                    for record in tracking_data:
                        level = record["performance_level"]
                        if level in level_counts:
                            level_counts[level] += 1
                    
                    total = sum(level_counts.values())
                    if total > 0:
                        st.markdown("**21-Day Progress:**")
                        progress_html = "<div style='display:flex; height:20px; border-radius:4px; overflow:hidden;'>"
                        colors = {"EXCEEDING": "#10b981", "ABOVE": "#3b82f6", "EXPECTED": "#8b5cf6", "BELOW": "#f59e0b", "NOT YET": "#ef4444"}
                        for level in GAS_LEVELS:
                            pct = (level_counts[level] / total) * 100
                            if pct > 0:
                                progress_html += f"<div style='width:{pct}%; background:{colors[level]}; height:100%;' title='{level}: {level_counts[level]}'></div>"
                        progress_html += "</div>"
                        st.markdown(progress_html, unsafe_allow_html=True)
                        
                        # Legend
                        legend_html = "<div style='display:flex; gap:12px; margin-top:8px; font-size:12px;'>"
                        for level in GAS_LEVELS:
                            legend_html += f"<span><span style='display:inline-block; width:12px; height:12px; background:{colors[level]}; border-radius:2px; margin-right:4px;'></span>{level}: {level_counts[level]}</span>"
                        legend_html += "</div>"
                        st.markdown(legend_html, unsafe_allow_html=True)
                
                st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: PROGRESS REPORT
# ═══════════════════════════════════════════════════════════════════════════════
def render_progress_report():
    st.markdown("## 📈 Progress Report")
    st.markdown("Generate narrative summaries for review meetings and reports.")
    
    students = get_all_students()
    if not students:
        st.info("No students with active goals yet.")
        return
    
    student_names = [s["student_name"] for s in students]
    selected_student = st.selectbox("Select Student", student_names, key="pr_student")
    
    if selected_student:
        goals = get_student_goals(selected_student)
        active_goals = [g for g in goals if g.get("active", True)]
        
        if not active_goals:
            st.info(f"No active goals for {selected_student}.")
            return
        
        goal_options = [f"{g['smartar_goal'][:60]}..." if len(g['smartar_goal']) > 60 else g['smartar_goal'] for g in active_goals]
        selected_goal_idx = st.selectbox("Select Goal", range(len(goal_options)), format_func=lambda i: goal_options[i], key="pr_goal")
        
        goal = active_goals[selected_goal_idx]
        
        days = st.slider("Reporting Period (days)", 7, 90, 21, key="pr_days")
        
        if st.button("Generate Progress Report", type="primary", use_container_width=True):
            tracking_data = get_tracking_data(goal["id"], days=days)
            
            if not tracking_data:
                st.warning(f"No tracking data available for the last {days} days.")
                return
            
            # Calculate statistics
            level_counts = {level: 0 for level in GAS_LEVELS}
            for record in tracking_data:
                level = record["performance_level"]
                if level in level_counts:
                    level_counts[level] += 1
            
            total = sum(level_counts.values())
            percentages = {level: (count/total)*100 if total > 0 else 0 for level, count in level_counts.items()}
            
            st.markdown("### 📊 Performance Breakdown")
            col1, col2, col3, col4, col5 = st.columns(5)
            for col, level in zip([col1, col2, col3, col4, col5], GAS_LEVELS):
                with col:
                    st.metric(level, f"{percentages[level]:.1f}%", f"{level_counts[level]} sessions")
            
            st.markdown("---")
            st.markdown("### 📝 AI-Generated Narrative Summary")
            
            with st.spinner("Generating narrative..."):
                system = """You are an educational psychologist writing progress reports for students with diverse learning needs.

Write a strengths-based, trauma-informed narrative summary using:
- BSEM (Berry Street Education Model) language
- Positive, growth-oriented tone
- Specific data references
- Recognition of progress and effort
- Constructive next steps

Keep it professional, concise (2-3 paragraphs), and suitable for inclusion in IEP/review meeting notes."""

                data_summary = f"""Student: {selected_student}
Goal: {goal['smartar_goal']}
Reporting Period: {days} days
Total Sessions: {total}

Performance Distribution:
- EXCEEDING: {percentages['EXCEEDING']:.1f}% ({level_counts['EXCEEDING']} sessions)
- ABOVE: {percentages['ABOVE']:.1f}% ({level_counts['ABOVE']} sessions)
- EXPECTED: {percentages['EXPECTED']:.1f}% ({level_counts['EXPECTED']} sessions)
- BELOW: {percentages['BELOW']:.1f}% ({level_counts['BELOW']} sessions)
- NOT YET: {percentages['NOT YET']:.1f}% ({level_counts['NOT YET']} sessions)

Write a narrative progress summary based on this data."""

                narrative = groq_chat(data_summary, system=system, max_tokens=600)
                
                if narrative:
                    st.markdown(narrative)
                    st.markdown("---")
                    
                    # Copy button
                    st.text_area("Copy for meeting notes:", value=narrative, height=200, key="pr_narrative_copy")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.title("🎯 SMARTAR Goal Builder")
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

if __name__ == "__main__":
    main()
