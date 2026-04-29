from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
from groq import Groq
import json

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

# ── Check for Team Meetings Integration ──────────────────────────────────────
def check_team_meetings_integration():
    """Check if this was opened from Team Meetings and extract context."""
    params = st.query_params
    
    student_param = params.get("student", None)
    meeting_id_param = params.get("meeting_id", None)
    program_param = params.get("program", None)
    term_param = params.get("term", None)
    week_param = params.get("week", None)
    return_to_param = params.get("return_to", None)
    
    return {
        "student_name": student_param,
        "meeting_id": meeting_id_param if meeting_id_param else None,  # FIXED: No int() conversion
        "program": program_param,
        "term": term_param,
        "week": week_param,
        "return_to": return_to_param
    }

integration = check_team_meetings_integration()

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY)
GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

# Main Supabase (for Team Meetings integration)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Behaviour Support Supabase (for students and goals)
import os
BEHAVIOUR_SUPABASE_URL = st.secrets.get("BEHAVIOUR_SUPABASE_URL","") or os.environ.get("BEHAVIOUR_SUPABASE_URL","")
BEHAVIOUR_SUPABASE_KEY = st.secrets.get("BEHAVIOUR_SUPABASE_KEY","") or os.environ.get("BEHAVIOUR_SUPABASE_KEY","")

if BEHAVIOUR_SUPABASE_URL and BEHAVIOUR_SUPABASE_KEY:
    behaviour_supabase = create_client(BEHAVIOUR_SUPABASE_URL, BEHAVIOUR_SUPABASE_KEY)
    has_behaviour_db = True
else:
    has_behaviour_db = False
    st.warning("⚠️ Behaviour Support database not configured - goals will save to main database")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,#7c3aed,#9b59b6);
            padding:1.5rem 2rem;border-radius:16px;margin-bottom:1.5rem;">
  <div style="font-size:2.5rem;margin-bottom:0.25rem;">🎯</div>
  <h1 style="color:white;margin:0;font-size:1.8rem;">SMARTAR Goal Builder</h1>
  <p style="color:rgba(255,255,255,0.85);margin:0.25rem 0 0;">Specific · Measurable · Achievable · Realistic · Time-bound · Adjustable · Reviewed</p>
</div>
""", unsafe_allow_html=True)

# Show integration context if present
if integration["meeting_id"]:
    st.markdown(f"""
    <div style="background:#ede9fe;border-left:4px solid #7c3aed;border-radius:0 8px 8px 0;
                padding:8px 14px;margin-bottom:12px;font-size:13px;color:#5b21b6;">
      🔗 <strong>Team Meeting Integration:</strong> {integration["program"]} · Term {integration["term"]} Week {integration["week"]} · Meeting ID: {integration["meeting_id"]}
    </div>
    """, unsafe_allow_html=True)
    
    if integration["return_to"] == "team_meetings":
        team_meetings_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
        st.sidebar.markdown(f"[← Back to Team Meeting]({team_meetings_url})")

# ── Fetch Students ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_students():
    names = []
    try:
        if has_behaviour_db:
            res = behaviour_supabase.table("students").select("id,name,year_level").eq("archived", False).execute()
            if res.data:
                names = [s["name"] for s in res.data]
    except Exception:
        pass
    
    # Also check scatter_students in main DB
    try:
        res2 = supabase.table("scatter_students").select("name").execute()
        if res2.data:
            scatter_names = [s["name"] for s in res2.data if s.get("name")]
            for n in scatter_names:
                if n not in names:
                    names.append(n)
    except Exception:
        pass
    
    return sorted(names)

student_names = fetch_students()

# ── Student Selection ─────────────────────────────────────────────────────────
st.markdown("### 👤 Student Selection")

col_select, col_new = st.columns([3, 1])

with col_select:
    # Pre-fill from integration if available
    default_index = 0
    if integration["student_name"] and integration["student_name"] in student_names:
        default_index = student_names.index(integration["student_name"]) + 1  # +1 for blank option
    
    selected_student = st.selectbox(
        "Select student",
        options=[""] + student_names,
        index=default_index,
        key="student_select"
    )

with col_new:
    st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
    new_student_name = st.text_input(
        "Or enter new name",
        value=integration["student_name"] if integration["student_name"] and integration["student_name"] not in student_names else "",
        key="new_student",
        label_visibility="collapsed",
        placeholder="New student name"
    )

# Determine final student name
student_name = new_student_name if new_student_name else selected_student

if not student_name:
    st.info("👆 Select or enter a student name to begin")
    st.stop()

st.success(f"✅ Working on SMARTAR goal for: **{student_name}**")

st.markdown("---")

# ── Load Existing Goals ───────────────────────────────────────────────────────
existing_goals = []

# Check for existing goal linked to this meeting
if integration["meeting_id"] and has_behaviour_db:
    try:
        result = behaviour_supabase.table('smartar_goals').select('*').eq('student_name', student_name).eq('meeting_id', integration["meeting_id"]).order('updated_at', desc=True).execute()
        if result.data:
            existing_goals = result.data
            st.info(f"📋 Found {len(existing_goals)} existing goal(s) for this student linked to this meeting")
    except Exception as e:
        st.warning(f"Could not load existing goals: {e}")

# Check for any recent goals for this student
if has_behaviour_db:
    try:
        result = behaviour_supabase.table('smartar_goals').select('*').eq('student_name', student_name).order('updated_at', desc=True).limit(5).execute()
        if result.data:
            with st.expander(f"📚 Recent goals for {student_name} ({len(result.data)} found)", expanded=False):
                for idx, goal in enumerate(result.data):
                    meeting_link = goal.get('meeting_id', 'No meeting')
                    created = goal.get('created_at', '')[:10]
                    st.markdown(f"**{idx+1}.** Created: {created} | Meeting: {meeting_link}")
                    st.text(goal.get('smartar_goal', '')[:200] + "...")
                    st.markdown("---")
    except Exception:
        pass

st.markdown("---")

# ── SMARTAR Goal Builder ──────────────────────────────────────────────────────
st.markdown("### 🎯 SMARTAR Goal Framework")

st.markdown("""
<div style="background:#f3f4f6;border-radius:8px;padding:12px;margin-bottom:16px;font-size:0.85rem;">
<strong>SMARTAR Framework:</strong><br>
<strong>S</strong>pecific – Clear, unambiguous goal<br>
<strong>M</strong>easurable – Observable evidence of progress<br>
<strong>A</strong>chievable – Within student's current capability with support<br>
<strong>R</strong>ealistic – Appropriate for student's context and timeline<br>
<strong>T</strong>ime-bound – Clear timeframe for review<br>
<strong>A</strong>djustable – Can be modified based on progress<br>
<strong>R</strong>eviewed – Regular check-ins scheduled
</div>
""", unsafe_allow_html=True)

# Load from existing goal if available
default_goal_text = ""
default_baseline = ""
default_target = ""
default_strategies = ""
default_evidence = ""
default_review_date = datetime.date.today() + datetime.timedelta(weeks=4)
default_progress_notes = ""

if existing_goals:
    latest = existing_goals[0]
    default_goal_text = latest.get('smartar_goal', '')
    default_baseline = latest.get('baseline', '')
    default_target = latest.get('target', '')
    default_strategies = latest.get('strategies', '')
    default_evidence = latest.get('evidence_methods', '')
    if latest.get('review_date'):
        try:
            default_review_date = datetime.date.fromisoformat(latest['review_date'])
        except:
            pass
    default_progress_notes = latest.get('progress_notes', '')

# Goal Text
st.markdown("#### 📝 Goal Statement")
st.caption("Write the complete SMARTAR goal in one clear statement")

goal_text = st.text_area(
    "SMARTAR Goal",
    value=default_goal_text,
    height=120,
    key="goal_text",
    placeholder="Example: By Week 8 Term 1, [Student] will independently complete 3 out of 5 worksheet tasks within a 30-minute session, using a visual timer and checklist for self-regulation, measured through teacher observation and completed work samples.",
    label_visibility="collapsed"
)

st.markdown("---")

# Baseline
st.markdown("#### 📊 Baseline (Current Level)")
st.caption("Where is the student now? What evidence do we have?")

baseline = st.text_area(
    "Baseline",
    value=default_baseline,
    height=80,
    key="baseline",
    placeholder="Example: Currently completes 1 out of 5 tasks independently. Requires 1:1 support and frequent prompts. Becomes dysregulated after 10-15 minutes.",
    label_visibility="collapsed"
)

# Target
st.markdown("#### 🎯 Target (Desired Outcome)")
st.caption("What will success look like? Be specific and measurable.")

target = st.text_area(
    "Target",
    value=default_target,
    height=80,
    key="target",
    placeholder="Example: Completes 3/5 tasks independently within 30 minutes, using self-regulation strategies (visual timer, checklist).",
    label_visibility="collapsed"
)

st.markdown("---")

# Strategies
st.markdown("#### 🛠️ Strategies & Supports")
st.caption("What supports, scaffolds, or strategies will we use?")

strategies = st.text_area(
    "Strategies",
    value=default_strategies,
    height=100,
    key="strategies",
    placeholder="Example:\n• Visual timer (5-minute intervals)\n• Task checklist with tick boxes\n• Choice of task order\n• Movement breaks between tasks\n• Positive reinforcement for effort and progress",
    label_visibility="collapsed"
)

# Evidence Methods
st.markdown("#### 📋 Evidence Collection")
st.caption("How will we measure progress? What data will we collect?")

evidence = st.text_area(
    "Evidence Methods",
    value=default_evidence,
    height=80,
    key="evidence",
    placeholder="Example: Teacher observation checklist, completed work samples, student self-assessment, photos of work",
    label_visibility="collapsed"
)

st.markdown("---")

# Timeline
st.markdown("#### 📅 Timeline & Review")

col_timeline1, col_timeline2 = st.columns(2)

with col_timeline1:
    review_date = st.date_input(
        "Review Date",
        value=default_review_date,
        key="review_date"
    )

with col_timeline2:
    review_frequency = st.selectbox(
        "Review Frequency",
        options=["Weekly", "Fortnightly", "Monthly", "Each Team Meeting"],
        index=1,
        key="review_frequency"
    )

# Progress Notes
st.markdown("#### 📈 Progress Notes")
st.caption("Record progress, adjustments, and observations")

progress_notes = st.text_area(
    "Progress Notes",
    value=default_progress_notes,
    height=100,
    key="progress_notes",
    placeholder="Record observations, adjustments made, wins, and concerns...",
    label_visibility="collapsed"
)

st.markdown("---")

# ── AI Assistance ─────────────────────────────────────────────────────────────
st.markdown("### 🤖 AI Assistance")
st.caption("Get AI help refining your SMARTAR goal")

col_ai1, col_ai2 = st.columns([3, 1])

with col_ai1:
    ai_context = st.text_area(
        "Context for AI",
        height=80,
        key="ai_context",
        placeholder="Provide context: student's strengths, challenges, current supports, behaviour of concern...",
        label_visibility="collapsed"
    )

with col_ai2:
    st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
    if st.button("✨ Refine with AI", type="secondary", use_container_width=True):
        if not ai_context:
            st.warning("⚠️ Please provide context for AI assistance")
        elif not GROQ_KEY:
            st.error("⚠️ Groq API key not configured")
        else:
            with st.spinner("Generating SMARTAR goal suggestions..."):
                try:
                    client = Groq(api_key=GROQ_KEY)
                    
                    prompt = f"""You are an expert educational psychologist specializing in trauma-informed practice and behaviour support in alternative education settings.

Student: {student_name}
Current goal (if exists): {goal_text}
Baseline: {baseline}
Target: {target}

Context: {ai_context}

Task: Generate a refined SMARTAR goal that is:
- Specific and observable
- Measurable with clear evidence
- Achievable within 4-8 weeks
- Realistic for this student's current level
- Time-bound with review dates
- Adjustable based on progress
- Trauma-informed and strengths-based

Provide:
1. A refined SMARTAR goal statement (1-2 sentences)
2. 3-4 specific strategies to support this goal
3. Evidence collection methods

Format as:
GOAL: [clear statement]

STRATEGIES:
• [strategy 1]
• [strategy 2]
• [strategy 3]

EVIDENCE:
[methods]
"""
                    
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1500
                    )
                    
                    ai_suggestion = response.choices[0].message.content
                    
                    st.success("✅ AI suggestions generated!")
                    st.markdown("**AI-Generated SMARTAR Goal:**")
                    st.markdown(ai_suggestion)
                    
                    st.info("💡 Review the AI suggestions above, then manually copy relevant parts into the goal fields")
                    
                except Exception as e:
                    st.error(f"AI generation failed: {e}")

st.markdown("---")

# ── Save Goal ─────────────────────────────────────────────────────────────────
st.markdown("### 💾 Save SMARTAR Goal")

col_save1, col_save2 = st.columns([2, 1])

with col_save1:
    goal_status = st.selectbox(
        "Goal Status",
        options=["Active", "In Progress", "Achieved", "Adjusted", "On Hold"],
        index=0,
        key="goal_status"
    )

with col_save2:
    st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
    save_button = st.button("💾 Save Goal", type="primary", use_container_width=True)

if save_button:
    if not goal_text or not student_name:
        st.error("⚠️ Student name and goal text are required")
    else:
        # Prepare goal data
        goal_data = {
            "student_name": student_name,
            "smartar_goal": goal_text.strip(),
            "baseline": baseline.strip(),
            "target": target.strip(),
            "strategies": strategies.strip(),
            "evidence_methods": evidence.strip(),
            "review_date": str(review_date),
            "review_frequency": review_frequency,
            "progress_notes": progress_notes.strip(),
            "status": goal_status,
            "created_by": get_staff_name(),
            "updated_at": datetime.datetime.now().isoformat(),
        }
        
        # Add meeting integration data if available
        if integration["meeting_id"]:
            goal_data["meeting_id"] = integration["meeting_id"]
            goal_data["program"] = integration["program"]
            goal_data["term"] = integration["term"]
            goal_data["week"] = integration["week"]
        
        # Save to appropriate database
        try:
            if has_behaviour_db:
                # Check if updating existing or creating new
                if existing_goals and integration["meeting_id"]:
                    # Update existing
                    goal_id = existing_goals[0]['id']
                    behaviour_supabase.table('smartar_goals').update(goal_data).eq('id', goal_id).execute()
                    st.success(f"✅ Goal updated successfully! (ID: {goal_id})")
                else:
                    # Create new
                    goal_data["created_at"] = datetime.datetime.now().isoformat()
                    result = behaviour_supabase.table('smartar_goals').insert(goal_data).execute()
                    if result.data:
                        st.success(f"✅ Goal saved successfully! (ID: {result.data[0]['id']})")
            else:
                # Fallback to main database
                st.warning("Saving to main database (behaviour database not configured)")
                result = supabase.table('smartar_goals_fallback').insert(goal_data).execute()
                st.success("✅ Goal saved!")
            
            # Show return link if from Team Meetings
            if integration["return_to"] == "team_meetings":
                st.markdown("---")
                team_meetings_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
                st.markdown(f"""
                <div style="background:#d1fae5;border-left:4px solid #059669;border-radius:0 8px 8px 0;
                            padding:12px 16px;margin:12px 0;">
                  ✅ <strong>Goal saved and synced to Team Meeting!</strong><br>
                  <a href="{team_meetings_url}" style="color:#047857;font-weight:600;">← Return to Team Meeting</a>
                </div>
                """, unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"⚠️ Failed to save goal: {e}")
            st.info("💡 Check database connection and RLS policies")

# ── Footer Info ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="background:#f9fafb;border-radius:8px;padding:12px;font-size:0.8rem;color:#6b7280;">
<strong>💡 SMARTAR Tips:</strong><br>
• Goals should be achievable within 4-8 weeks<br>
• Focus on ONE specific behaviour or skill at a time<br>
• Use trauma-informed, strengths-based language<br>
• Make success criteria observable and measurable<br>
• Build in flexibility for adjustments based on student response<br>
• Link goals to student's Individual Learning Plan (ILP) or Behaviour Support Plan (BSP)
</div>
""", unsafe_allow_html=True)
