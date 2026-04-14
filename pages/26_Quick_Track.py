import streamlit as st
from datetime import date
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
        r = sb.table("smartar_students").select("*").eq("program", program).order("student_name").execute()
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

def get_today_tracking(goal_id):
    """Get today's tracking for a goal"""
    try:
        today = date.today().isoformat()
        r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).eq("session_date", today).execute()
        return {row["session_time"]: row["performance_level"] for row in (r.data or [])}
    except Exception as e:
        st.error(f"Error loading tracking: {e}")
        return {}

def track_session(goal_id, student_name, session_time, level):
    """Save tracking - auto-update if exists, insert if new"""
    try:
        today = date.today().isoformat()
        existing = sb.table("smartar_tracking").select("id").eq("goal_id", goal_id).eq("session_date", today).eq("session_time", session_time).execute()
        
        if existing.data:
            # Update existing
            sb.table("smartar_tracking").update({"performance_level": level}).eq("id", existing.data[0]["id"]).execute()
        else:
            # Insert new
            sb.table("smartar_tracking").insert({
                "goal_id": goal_id,
                "student_name": student_name,
                "session_date": today,
                "session_time": session_time,
                "performance_level": level
            }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving tracking: {e}")
        return False

# ── Initialize session state ──────────────────────────────────────────────────
if "selected_program" not in st.session_state:
    st.session_state.selected_program = "JP"
if "selected_student" not in st.session_state:
    st.session_state.selected_student = None

# ── CSS styling ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Compact header */
    .main-header {
        background: linear-gradient(135deg, #1d6fa4, #134e7a);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    /* Student card */
    .student-card {
        background: #f8fafc;
        border: 2px solid #cbd5e1;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
    }
    
    /* Goal box */
    .goal-box {
        background: white;
        border-left: 4px solid #1d6fa4;
        padding: 12px;
        margin-bottom: 12px;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Session label */
    .session-label {
        font-weight: 600;
        font-size: 0.9rem;
        color: #475569;
        text-align: center;
        margin-bottom: 8px;
    }
    
    /* Current status badge */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 4px 0;
    }
    
    /* Compact spacing */
    .stButton button {
        width: 100%;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.5rem;
    }
    
    /* Date badge */
    .date-badge {
        background: #e0f2fe;
        color: #0369a1;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="main-header">
    <h2 style="margin:0;">⚡ Quick Track</h2>
    <div style="font-size:0.85rem;opacity:0.9;margin-top:4px;">Fast Daily Performance Tracking · CLC LBU</div>
</div>
""", unsafe_allow_html=True)

# Date display
today_display = date.today().strftime("%A, %d %B %Y")
st.markdown(f'<div class="date-badge">📅 {today_display}</div>', unsafe_allow_html=True)

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
            st.session_state.selected_student = None  # Reset student selection
            st.rerun()

with col2:
    st.markdown("### 2️⃣ Select Student")
    
    students = get_students_by_program(st.session_state.selected_program)
    
    if not students:
        st.info(f"No students in {st.session_state.selected_program} program yet.")
        st.stop()
    
    # Create student buttons in rows
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
        st.warning(f"No active goals for {st.session_state.selected_student}. Add goals in the SMARTAR Goal Builder first.")
        st.stop()
    
    # Display each goal with tracking interface
    for idx, goal in enumerate(goals, 1):
        st.markdown(f'<div class="goal-box">', unsafe_allow_html=True)
        
        # Goal header
        st.markdown(f"**Goal {idx}:** {goal['smartar_goal'][:100]}{'...' if len(goal.get('smartar_goal', '')) > 100 else ''}")
        
        # Get today's tracking
        today_tracking = get_today_tracking(goal["id"])
        
        # Create session columns
        session_cols = st.columns(3)
        
        for col_idx, session in enumerate(SESSIONS):
            with session_cols[col_idx]:
                st.markdown(f'<div class="session-label">{session}</div>', unsafe_allow_html=True)
                
                # Show current status if exists
                current = today_tracking.get(session)
                if current:
                    color = LEVEL_COLOR.get(current, "#64748b")
                    st.markdown(
                        f'<div class="status-badge" style="background:{color}22;color:{color};border:1px solid {color};">'
                        f'{LEVEL_EMOJI.get(current, "")} {current}</div>',
                        unsafe_allow_html=True
                    )
                
                # Tracking buttons
                for level in LEVELS:
                    is_current = current == level
                    btn_label = f"{LEVEL_EMOJI[level]} {level}" + (" ✓" if is_current else "")
                    
                    if st.button(
                        btn_label,
                        key=f"track_{goal['id']}_{session}_{level}",
                        type="primary" if is_current else "secondary",
                        use_container_width=True
                    ):
                        success = track_session(goal["id"], st.session_state.selected_student, session, level)
                        if success:
                            st.success(f"✅ Saved: {session} → {level}", icon="✅")
                        st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

else:
    st.info("👆 Select a program and student to begin tracking")

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.caption("💡 **Tip:** This page stays open - just click to track and it auto-saves. Switch students anytime without losing your place.")
st.caption("📅 **Tracking flexibility:** Track only the sessions relevant to each goal (Morning only, Afternoon only, or all three). Leave sessions blank if they don't apply.")
st.caption("🎯 View detailed reports and manage goals in the **SMARTAR Goal Builder** tool.")
