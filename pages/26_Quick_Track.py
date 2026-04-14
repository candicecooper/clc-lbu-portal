import streamlit as st
from datetime import date, time, datetime
from supabase import create_client

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quick Track", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Supabase client ──────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = st.secrets.get("BEHAVIOUR_SUPABASE_URL") or st.secrets.get("supabase", {}).get("url")
    key = st.secrets.get("BEHAVIOUR_SUPABASE_KEY") or st.secrets.get("supabase", {}).get("key")
    if not url or not key:
        st.error("⚠️ Supabase credentials not configured")
        st.stop()
    return create_client(url, key)

sb = get_supabase()

# ── Constants ─────────────────────────────────────────────────────────────────
PROGRAMS = ["JP", "PY", "SY"]
SESSIONS = ["Morning", "Middle", "Afternoon"]
LEVELS = ["EXCEEDING", "ABOVE", "EXPECTED", "NOT YET"]
LEVEL_EMOJI = {"EXCEEDING": "🌟", "ABOVE": "✅", "EXPECTED": "🎯", "NOT YET": "❌"}
LEVEL_COLOR = {"EXCEEDING": "#1a7a3c", "ABOVE": "#2d8a5e", "EXPECTED": "#1d6fa4", "NOT YET": "#c0392b"}

# ── Database helpers ──────────────────────────────────────────────────────────
def get_students_by_program(program):
    """Get all students in a program"""
    try:
        r = sb.table("smartar_students").select("*").eq("program", program).eq("active", True).order("student_name").execute()
        return r.data or []
    except Exception as e:
        st.error(f"Error loading students: {e}")
        return []

def get_active_goals(student_name):
    """Get active goals for a student"""
    try:
        r = sb.table("smartar_goals").select("*").eq("student_name", student_name).eq("active", True).order("created_at").execute()
        return r.data or []
    except Exception as e:
        st.error(f"Error loading goals: {e}")
        return []

def get_today_observations(goal_id, session_time):
    """Get all observations for a goal in a specific session today"""
    try:
        today = date.today().isoformat()
        r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).eq("session_date", today).eq("session_time", session_time).order("recorded_at").execute()
        return r.data or []
    except Exception as e:
        st.error(f"Error loading observations: {e}")
        return []

def add_observation(goal_id, student_name, session_time, level):
    """Add a new observation (allows multiple per session)"""
    try:
        today = date.today().isoformat()
        sb.table("smartar_tracking").insert({
            "goal_id": goal_id,
            "student_name": student_name,
            "session_date": today,
            "session_time": session_time,
            "performance_level": level
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving observation: {e}")
        return False

def delete_observation(record_id):
    """Delete an observation"""
    try:
        sb.table("smartar_tracking").delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting observation: {e}")
        return False

def clear_session(goal_id, session_time):
    """Clear all observations for a session"""
    try:
        today = date.today().isoformat()
        sb.table("smartar_tracking").delete().eq("goal_id", goal_id).eq("session_date", today).eq("session_time", session_time).execute()
        return True
    except Exception as e:
        st.error(f"Error clearing session: {e}")
        return False

# ── Initialize session state ──────────────────────────────────────────────────
if "selected_program" not in st.session_state:
    st.session_state.selected_program = "JP"
if "selected_student" not in st.session_state:
    st.session_state.selected_student = None

# ── CSS styling ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    
    .main-header {
        background: linear-gradient(135deg, #1d6fa4, #134e7a);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .goal-box {
        background: white;
        border-left: 4px solid #1d6fa4;
        padding: 12px;
        margin-bottom: 12px;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .session-header {
        background: #f1f5f9;
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        color: #475569;
        text-align: center;
        margin-bottom: 8px;
    }
    
    .observation-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .counter-display {
        background: #f8fafc;
        border: 2px solid #cbd5e1;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        margin: 8px 0;
    }
    
    .stButton button {
        width: 100%;
        font-weight: 600;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="main-header">
    <h2 style="margin:0;">⚡ Quick Track - Multi-Observation Mode</h2>
    <div style="font-size:0.85rem;opacity:0.9;margin-top:4px;">Track multiple attempts per session · CLC LBU</div>
</div>
""", unsafe_allow_html=True)

today_display = date.today().strftime("%A, %d %B %Y")
st.markdown(f"**📅 {today_display}**")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# PROGRAM & STUDENT SELECTION
# ══════════════════════════════════════════════════════════════════════════════
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 1️⃣ Select Program")
    for prog in PROGRAMS:
        if st.button(
            f"**{prog}**", 
            key=f"prog_{prog}",
            type="primary" if st.session_state.selected_program == prog else "secondary",
            use_container_width=True
        ):
            st.session_state.selected_program = prog
            st.session_state.selected_student = None
            st.rerun()

with col2:
    st.markdown("### 2️⃣ Select Student")
    
    students = get_students_by_program(st.session_state.selected_program)
    
    if not students:
        st.info(f"No students in {st.session_state.selected_program} program yet.")
        st.stop()
    
    num_cols = 3
    student_rows = [students[i:i + num_cols] for i in range(0, len(students), num_cols)]
    
    for row in student_rows:
        cols = st.columns(num_cols)
        for idx, student in enumerate(row):
            with cols[idx]:
                is_selected = st.session_state.selected_student == student["student_name"]
                if st.button(
                    student["student_name"],
                    key=f"student_{student['id']}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True
                ):
                    st.session_state.selected_student = student["student_name"]
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TRACKING INTERFACE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.selected_student:
    st.markdown("---")
    st.markdown(f"### 3️⃣ Track: **{st.session_state.selected_student}** ({st.session_state.selected_program})")
    
    goals = get_active_goals(st.session_state.selected_student)
    
    if not goals:
        st.warning(f"No active goals for {st.session_state.selected_student}. Add goals in SMARTAR Goal Builder first.")
        st.stop()
    
    # Display each goal with multi-observation tracking
    for idx, goal in enumerate(goals, 1):
        st.markdown(f'<div class="goal-box">', unsafe_allow_html=True)
        
        # Goal header
        st.markdown(f"**Goal {idx}:** {goal['smartar_goal']}")
        st.caption(f"Goal ID: {goal['id']} • Rate: {goal.get('rate', 'Not specified')}")
        
        # Session tabs or columns
        session_tabs = st.tabs(SESSIONS)
        
        for session_idx, session in enumerate(SESSIONS):
            with session_tabs[session_idx]:
                st.markdown(f'<div class="session-header">{session} Session</div>', unsafe_allow_html=True)
                
                # Get observations for this session
                observations = get_today_observations(goal["id"], session)
                
                # Display counter
                level_counts = {}
                for obs in observations:
                    level = obs["performance_level"]
                    level_counts[level] = level_counts.get(level, 0) + 1
                
                total_obs = len(observations)
                
                if total_obs > 0:
                    st.markdown(f"""
                    <div class="counter-display">
                        <div style="font-size:1.5rem;font-weight:700;color:#1d6fa4;">{total_obs}</div>
                        <div style="font-size:0.85rem;color:#64748b;">Total Observations</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show breakdown
                    breakdown = " ".join([
                        f'<span class="observation-badge" style="background:{LEVEL_COLOR[lvl]}22;color:{LEVEL_COLOR[lvl]};border:1px solid {LEVEL_COLOR[lvl]};">'
                        f'{LEVEL_EMOJI[lvl]} {lvl}: {count}</span>'
                        for lvl, count in level_counts.items()
                    ])
                    st.markdown(breakdown, unsafe_allow_html=True)
                    
                    # Show individual observations with delete option
                    with st.expander(f"View all {total_obs} observations", expanded=False):
                        for obs in observations:
                            col_time, col_level, col_del = st.columns([2, 3, 1])
                            time_recorded = obs.get("recorded_at", "")
                            if time_recorded:
                                try:
                                    dt = datetime.fromisoformat(time_recorded.replace('Z', '+00:00'))
                                    time_str = dt.strftime("%I:%M %p")
                                except:
                                    time_str = "Unknown"
                            else:
                                time_str = "Unknown"
                            
                            col_time.caption(f"🕐 {time_str}")
                            col_level.markdown(f"{LEVEL_EMOJI[obs['performance_level']]} {obs['performance_level']}")
                            if col_del.button("🗑", key=f"del_{obs['id']}", help="Delete this observation"):
                                if delete_observation(obs["id"]):
                                    st.rerun()
                    
                    # Clear session button
                    if st.button(f"🔄 Clear {session} Session", key=f"clear_{goal['id']}_{session}", type="secondary"):
                        if clear_session(goal["id"], session):
                            st.success(f"Cleared all {session} observations")
                            st.rerun()
                
                else:
                    st.info(f"No observations recorded for {session} session yet")
                
                # Add observation buttons
                st.markdown("**Record Observation:**")
                btn_cols = st.columns(4)
                
                for btn_idx, level in enumerate(LEVELS):
                    with btn_cols[btn_idx]:
                        if st.button(
                            f"{LEVEL_EMOJI[level]}\n{level}",
                            key=f"add_{goal['id']}_{session}_{level}",
                            use_container_width=True,
                            type="primary"
                        ):
                            success = add_observation(goal["id"], st.session_state.selected_student, session, level)
                            if success:
                                st.success(f"➕ Added: {level}", icon="✅")
                                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

else:
    st.info("👆 Select a program and student to begin tracking")

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.caption("💡 **Multi-Observation Mode:** Track multiple attempts per session (e.g., 5 observations to assess '3 out of 5 opportunities')")
st.caption("📊 **Each click adds a new observation** - perfect for rate-based goals")
st.caption("🎯 View summary reports in the **SMARTAR Goal Builder** tool")
