from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
import os
from urllib.parse import unquote

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="SMARTAR Goal Builder", page_icon="🎯", layout="wide")
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
require_auth("SMARTAR Goal Builder", "🎯")
logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Supabase (BEHAVIOUR SUPPORT DATABASE) ────────────────────────────────────
BEHAVIOUR_SUPABASE_URL = st.secrets.get("BEHAVIOUR_SUPABASE_URL","") or os.environ.get("BEHAVIOUR_SUPABASE_URL","")
BEHAVIOUR_SUPABASE_KEY = st.secrets.get("BEHAVIOUR_SUPABASE_KEY","") or os.environ.get("BEHAVIOUR_SUPABASE_KEY","")

if not BEHAVIOUR_SUPABASE_URL or not BEHAVIOUR_SUPABASE_KEY:
    st.error("⚠️ Behaviour Support Supabase credentials not configured. Contact admin.")
    st.stop()

supabase = create_client(BEHAVIOUR_SUPABASE_URL, BEHAVIOUR_SUPABASE_KEY)

# ── SMARTAR Framework ─────────────────────────────────────────────────────────
SMARTAR_COMPONENTS = {
    "S": {
        "label": "Specific",
        "prompt": "What exactly will the student do? Be concrete and observable.",
        "placeholder": "e.g., Ask for a break using visual card when feeling overwhelmed"
    },
    "M": {
        "label": "Measurable",
        "prompt": "How will we measure progress? What does success look like?",
        "placeholder": "e.g., Uses break card 3 out of 5 times when dysregulated"
    },
    "A": {
        "label": "Achievable",
        "prompt": "Is this realistic given current skills? What supports are needed?",
        "placeholder": "e.g., With visual prompts and staff modeling, achievable in 4-6 weeks"
    },
    "R": {
        "label": "Relevant",
        "prompt": "How does this support the student's learning/wellbeing? Why does it matter?",
        "placeholder": "e.g., Reduces dysregulation episodes and increases learning time"
    },
    "T": {
        "label": "Time-bound",
        "prompt": "What's the timeline? When will we review progress?",
        "placeholder": "e.g., Review in 4 weeks (Week 8, Term 1)"
    },
    "A2": {
        "label": "Adjustable",
        "prompt": "How will we adapt if progress stalls or accelerates?",
        "placeholder": "e.g., If successful, fade visual prompt. If struggling, add sensory break options"
    },
    "R2": {
        "label": "Recorded",
        "prompt": "How will we track and document this? What data will we collect?",
        "placeholder": "e.g., Staff log each break request on scatter plot tracker"
    }
}

# ── Check for Team Meetings integration ──────────────────────────────────────
def check_team_meetings_integration():
    """Check if this session is from Team Meetings tool."""
    params = st.query_params
    
    # Check for integration parameters
    student_param = params.get("student", None)
    meeting_id_param = params.get("meeting_id", None)
    program_param = params.get("program", None)
    term_param = params.get("term", None)
    week_param = params.get("week", None)
    return_to = params.get("return_to", None)
    
    integration_active = return_to == "team_meetings"
    
    return {
        "active": integration_active,
        "student": unquote(student_param) if student_param else None,
        "meeting_id": int(meeting_id_param) if meeting_id_param else None,
        "program": program_param,
        "term": term_param,
        "week": int(week_param) if week_param else None,
        "return_to": return_to
    }

# ── Fetch students ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_students():
    """Fetch all active students from behaviour support database."""
    try:
        result = supabase.table("students").select("id,name,year_level,program").eq("archived", False).order("name").execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Could not fetch students: {e}")
        return []

# ── Fetch existing goal ───────────────────────────────────────────────────────
def fetch_existing_goal(student_name):
    """Fetch the most recent goal for a student."""
    try:
        result = supabase.table("smartar_goals").select("*").eq("student_name", student_name).order("updated_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None

# ── Save goal ─────────────────────────────────────────────────────────────────
def save_goal(student_name, goal_data, integration_context=None):
    """Save or update SMARTAR goal."""
    try:
        # Check if goal exists for this student
        existing = fetch_existing_goal(student_name)
        
        # Prepare goal data
        save_data = {
            "student_name": student_name,
            "smartar_goal": goal_data["goal_text"],
            "specific": goal_data.get("S", ""),
            "measurable": goal_data.get("M", ""),
            "achievable": goal_data.get("A", ""),
            "relevant": goal_data.get("R", ""),
            "time_bound": goal_data.get("T", ""),
            "adjustable": goal_data.get("A2", ""),
            "recorded": goal_data.get("R2", ""),
            "staff_name": get_staff_name(),
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        # Add Team Meetings integration context if provided
        if integration_context and integration_context.get("active"):
            save_data["meeting_id"] = integration_context.get("meeting_id")
            save_data["program"] = integration_context.get("program")
            save_data["term"] = integration_context.get("term")
            save_data["week"] = integration_context.get("week")
        
        if existing:
            # Update existing goal
            result = supabase.table("smartar_goals").update(save_data).eq("id", existing["id"]).execute()
        else:
            # Create new goal
            save_data["created_at"] = datetime.datetime.now().isoformat()
            result = supabase.table("smartar_goals").insert(save_data).execute()
        
        return True, result.data[0] if result.data else None
    except Exception as e:
        return False, str(e)

# ── Main UI ───────────────────────────────────────────────────────────────────
def main():
    # Check for Team Meetings integration
    integration = check_team_meetings_integration()
    
    # Show integration banner if active
    if integration["active"]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#7c3aed,#5b21b6);
                    padding:1rem 1.5rem;border-radius:12px;margin-bottom:1.5rem;
                    border-left:5px solid #fbbf24;">
          <div style="color:white;font-size:1.1rem;font-weight:700;margin-bottom:0.25rem;">
            🔗 Team Meeting Integration Active
          </div>
          <div style="color:rgba(255,255,255,0.9);font-size:0.85rem;">
            {integration["program"]} Team Meeting · Term {integration["term"]} Week {integration["week"]} · Meeting ID: {integration["meeting_id"]}
          </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background:linear-gradient(135deg,#7c3aed,#9b59b6);
                padding:1.5rem 2rem;border-radius:16px;margin-bottom:1.5rem;">
      <div style="font-size:2.5rem;margin-bottom:0.25rem;">🎯</div>
      <h1 style="color:white;margin:0;font-size:1.8rem;">SMARTAR Goal Builder</h1>
      <p style="color:rgba(255,255,255,0.85);margin:0.25rem 0 0;">
        Evidence-Based Goal Setting for Student Support
      </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch students
    students = fetch_students()
    student_names = [s["name"] for s in students]
    
    # Student selection
    st.markdown("### 👤 Select Student")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # If integration is active, pre-fill student name
        if integration["active"] and integration["student"]:
            selected_student = st.text_input(
                "Student name",
                value=integration["student"],
                key="student_name",
                help="From Team Meeting"
            )
        else:
            if student_names:
                selected_student = st.selectbox(
                    "Choose student",
                    options=[""] + student_names,
                    key="student_select"
                )
            else:
                selected_student = st.text_input(
                    "Student name",
                    placeholder="Enter student name",
                    key="student_name"
                )
    
    with col2:
        if integration["active"]:
            meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
            st.markdown(f"[← Back to Team Meeting]({meeting_url})")
    
    if not selected_student:
        st.info("👆 Select a student to begin building a SMARTAR goal")
        st.stop()
    
    # Check for existing goal
    existing_goal = fetch_existing_goal(selected_student)
    
    if existing_goal:
        st.success(f"✅ Existing goal found for {selected_student} (Last updated: {existing_goal.get('updated_at', 'Unknown')[:10]})")
        
        col_edit, col_new = st.columns(2)
        with col_edit:
            mode = st.radio("", ["Edit existing goal", "Create new goal"], horizontal=True)
        
        if mode == "Edit existing goal":
            # Pre-fill with existing data
            initial_data = {
                "S": existing_goal.get("specific", ""),
                "M": existing_goal.get("measurable", ""),
                "A": existing_goal.get("achievable", ""),
                "R": existing_goal.get("relevant", ""),
                "T": existing_goal.get("time_bound", ""),
                "A2": existing_goal.get("adjustable", ""),
                "R2": existing_goal.get("recorded", ""),
                "goal_text": existing_goal.get("smartar_goal", "")
            }
        else:
            initial_data = {k: "" for k in ["S", "M", "A", "R", "T", "A2", "R2", "goal_text"]}
    else:
        st.info(f"📝 Creating new goal for {selected_student}")
        initial_data = {k: "" for k in ["S", "M", "A", "R", "T", "A2", "R2", "goal_text"]}
    
    st.markdown("---")
    
    # SMARTAR Components
    st.markdown("### 🎯 Build SMARTAR Goal")
    
    st.markdown("""
    <div style="background:#f0f9ff;border-left:4px solid #0ea5e9;border-radius:0 8px 8px 0;
                padding:8px 14px;margin-bottom:16px;font-size:13px;color:#0c4a6e;">
      <strong>SMARTAR Framework:</strong> Specific · Measurable · Achievable · Relevant · Time-bound · Adjustable · Recorded
    </div>
    """, unsafe_allow_html=True)
    
    goal_components = {}
    
    for key, component in SMARTAR_COMPONENTS.items():
        st.markdown(f"#### {component['label']}")
        st.caption(component['prompt'])
        
        goal_components[key] = st.text_area(
            component['label'],
            value=initial_data.get(key, ""),
            placeholder=component['placeholder'],
            height=80,
            key=f"smartar_{key}",
            label_visibility="collapsed"
        )
        st.markdown("")
    
    st.markdown("---")
    
    # Generate full goal statement
    st.markdown("### 📋 Complete SMARTAR Goal Statement")
    st.caption("Review and edit the complete goal before saving")
    
    # Auto-generate goal text from components
    auto_goal = f"""SMARTAR Goal for {selected_student}:

**Specific:** {goal_components['S']}

**Measurable:** {goal_components['M']}

**Achievable:** {goal_components['A']}

**Relevant:** {goal_components['R']}

**Time-bound:** {goal_components['T']}

**Adjustable:** {goal_components['A2']}

**Recorded:** {goal_components['R2']}
"""
    
    final_goal = st.text_area(
        "Final goal statement",
        value=initial_data.get("goal_text") or auto_goal,
        height=300,
        key="final_goal",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Save button
    col_save, col_cancel = st.columns([3, 1])
    
    with col_save:
        if st.button("💾 Save SMARTAR Goal", type="primary", use_container_width=True):
            if not any(goal_components.values()):
                st.warning("⚠️ Please complete at least one SMARTAR component before saving")
            else:
                goal_data = {**goal_components, "goal_text": final_goal}
                success, result = save_goal(selected_student, goal_data, integration)
                
                if success:
                    st.success("✅ SMARTAR goal saved successfully!")
                    
                    # Show success message with integration context
                    if integration["active"]:
                        st.info(f"""
                        🔗 **Goal synced to Team Meeting** (Meeting ID: {integration['meeting_id']})
                        
                        This goal will automatically appear in the Team Meeting notes.
                        """)
                        
                        # Return button
                        meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
                        st.markdown(f"[← Return to Team Meeting]({meeting_url})")
                    
                    # Clear cache
                    st.cache_data.clear()
                    
                    # Auto-rerun after brief pause
                    import time
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Could not save goal: {result}")
    
    with col_cancel:
        if integration["active"]:
            meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
            if st.button("Cancel", use_container_width=True):
                st.switch_page(meeting_url)
    
    # Show existing goals for this student
    st.markdown("---")
    st.markdown("### 📚 Goal History")
    
    try:
        all_goals = supabase.table("smartar_goals").select("*").eq("student_name", selected_student).order("updated_at", desc=True).execute()
        
        if all_goals.data:
            for idx, goal in enumerate(all_goals.data[:5]):  # Show last 5 goals
                with st.expander(
                    f"Goal from {goal.get('updated_at', '')[:10]} · By {goal.get('staff_name', 'Unknown')}",
                    expanded=(idx == 0)
                ):
                    st.markdown(goal.get("smartar_goal", "No goal text"))
                    
                    # Show meeting context if available
                    if goal.get("meeting_id"):
                        st.caption(f"📋 From {goal.get('program', '')} Team Meeting · Term {goal.get('term', '')} Week {goal.get('week', '')}")
        else:
            st.info("No previous goals found for this student")
    except Exception as e:
        st.error(f"Could not load goal history: {e}")


if __name__ == "__main__":
    main()
