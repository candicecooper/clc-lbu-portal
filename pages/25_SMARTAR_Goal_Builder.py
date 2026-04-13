import streamlit as st
import json
import os
from datetime import date, datetime, timedelta
from supabase import create_client
from groq import Groq
from urllib.parse import unquote

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="SMARTAR Goal Builder", page_icon="🎯", layout="wide")

# ── Clients ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    # SMARTAR uses Behaviour Support Supabase (where smartar_goals table lives)
    url = st.secrets.get("BEHAVIOUR_SUPABASE_URL") or st.secrets.get("supabase", {}).get("url")
    key = st.secrets.get("BEHAVIOUR_SUPABASE_KEY") or st.secrets.get("supabase", {}).get("key")
    if not url or not key:
        st.error("⚠️ Behaviour Support Supabase credentials not configured")
        st.stop()
    return create_client(url, key)

@st.cache_resource
def get_groq():
    api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
    if not api_key:
        st.warning("⚠️ Groq API key not configured - AI features disabled")
        return None
    return Groq(api_key=api_key)

sb = get_supabase()
groq_client = get_groq()

# ── Team Meetings Integration ────────────────────────────────────────────────
def check_team_meetings_integration():
    """Check if this session is from Team Meetings tool."""
    params = st.query_params
    
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

integration = check_team_meetings_integration()

# ── Helpers ───────────────────────────────────────────────────────────────────
PROGRAMS = ["JP", "PY", "SY"]

def groq_call(prompt, system="You are an expert educator supporting students in alternative education settings. Be concise and practical."):
    if not groq_client:
        return "[AI features unavailable - Groq API key not configured]"
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

# ── Supabase helpers ──────────────────────────────────────────────────────────
def get_students():
    r = sb.table("smartar_students").select("*").order("student_name").execute()
    return r.data or []

def get_goals(student_name=None):
    q = sb.table("smartar_goals").select("*")
    if student_name:
        q = q.eq("student_name", student_name)
    q = q.eq("active", True)
    try:
        q = q.order("created_at", desc=True)
    except:
        pass
    return q.execute().data or []

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .student-header {
        background: linear-gradient(135deg, #1d6fa4, #134e7a);
        color: white;
        padding: 14px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
    .exclusion-box {
        background: #fff7ed;
        border-left: 4px solid #f97316;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        font-size: 0.88rem;
        margin-bottom: 8px;
    }
    .smartar-box {
        background: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        font-size: 0.88rem;
    }
    .integration-banner {
        background: linear-gradient(135deg, #7c3aed, #5b21b6);
        color: white;
        padding: 12px 18px;
        border-radius: 10px;
        margin-bottom: 16px;
        border-left: 5px solid #fbbf24;
    }
</style>
""", unsafe_allow_html=True)

# ── Team Meetings Integration Banner ─────────────────────────────────────────
if integration["active"]:
    st.markdown(f"""
    <div class="integration-banner">
        <div style="font-size:1.1rem;font-weight:700;margin-bottom:0.25rem;">
            🔗 Team Meeting Integration Active
        </div>
        <div style="font-size:0.85rem;opacity:0.9;">
            {integration["program"]} Team Meeting · Term {integration["term"]} Week {integration["week"]} · Meeting ID: {integration["meeting_id"]}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🎯 SMARTAR Goal Builder")
staff_name = st.sidebar.text_input("Your name", key="staff_name", placeholder="Enter your name")

# Return to Team Meeting button if integration active
if integration["active"]:
    meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
    st.sidebar.markdown(f"""
    <a href="{meeting_url}" style="display:block;text-align:center;background:#7c3aed;color:white;
    font-weight:600;font-size:0.85rem;padding:0.5rem;border-radius:8px;text-decoration:none;
    margin-bottom:0.5rem;">← Back to Team Meeting</a>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.caption("SMARTAR Goal Tool · CLC LBU")

# ═══════════════════════════════════════════════════════════════════════════════
# GOAL BUILDER (SIMPLIFIED - NO TRACKING)
# ═══════════════════════════════════════════════════════════════════════════════

st.title("📋 SMARTAR Goal Builder")

tab1, tab2 = st.tabs(["➕ Create / Edit Goals", "👥 Manage Students"])

# ── Student management ────────────────────────────────────────────────────
with tab2:
    st.subheader("Add New Student")
    c1, c2, c3 = st.columns([3, 1, 1])
    new_name = c1.text_input("Student first name", key="new_student_name")
    new_prog = c2.selectbox("Program", PROGRAMS, key="new_prog")
    if c3.button("Add Student", type="primary"):
        if new_name.strip():
            sb.table("smartar_students").insert({"student_name": new_name.strip(), "program": new_prog}).execute()
            st.success(f"✅ {new_name.strip()} added.")
            st.rerun()
        else:
            st.warning("Please enter a student name.")

    st.subheader("Current Students")
    students = get_students()
    if students:
        for s in students:
            goals = get_goals(s["student_name"])
            sc1, sc2, sc3 = st.columns([3, 1, 1])
            sc1.write(f"**{s['student_name']}** — {s.get('program','?')} — {len(goals)} goals")
            if sc3.button("Archive", key=f"arch_{s['id']}"):
                sb.table("smartar_students").update({"active": False}).eq("id", s["id"]).execute()
                st.rerun()
    else:
        st.info("No students yet.")

# ── Goal builder ──────────────────────────────────────────────────────────
with tab1:
    students = get_students()
    if not students:
        st.info("Add a student first in the **Manage Students** tab.")
        st.stop()

    student_options = {s["student_name"]: s for s in students}
    
    # Pre-select student from Team Meetings if integration active
    if integration["active"] and integration["student"]:
        if integration["student"] in student_options:
            default_student = integration["student"]
        else:
            st.info(f"Student '{integration['student']}' from Team Meeting not found in SMARTAR database. Add them in 'Manage Students' tab first, or select a different student below.")
            default_student = list(student_options.keys())[0]
    else:
        default_student = list(student_options.keys())[0]
    
    selected_name = st.selectbox("Select student", list(student_options.keys()), 
                                 index=list(student_options.keys()).index(default_student) if default_student in student_options else 0)
    student = student_options[selected_name]
    existing_goals = get_goals(selected_name)

    st.markdown(f'<div class="student-header"><b>{selected_name}</b> · {student.get("program","?")} · {len(existing_goals)} active goals</div>', unsafe_allow_html=True)

    # Show existing goals
    if existing_goals:
        st.subheader("Current Goals")
        for idx, g in enumerate(existing_goals):
            goal_num = idx + 1
            goal_text = g.get("smartar_goal", "No goal text")
            with st.expander(f"Goal {goal_num} — {goal_text[:80]}..."):
                if g.get("exclusion_goal"):
                    st.markdown(f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> {g.get("exclusion_goal","—")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {goal_text}</div>', unsafe_allow_html=True)
                
                # Show Team Meeting context if this goal has it
                if g.get("meeting_id"):
                    st.caption(f"📋 Created from {g.get('program', '')} Team Meeting · Term {g.get('term', '')} Week {g.get('week', '')}")
                
                if st.button(f"🗑 Archive Goal {goal_num}", key=f"del_{g['id']}"):
                    sb.table("smartar_goals").update({"active": False}).eq("id", g["id"]).execute()
                    st.rerun()

    # New goal form
    st.subheader(f"Add New Goal")

    excl_goal = st.text_area(
        "🏫 Exclusion Goal (from main school)",
        placeholder="Paste the exclusion goal as received from the main school...",
        height=80
    )

    st.markdown("#### Enter SMARTAR Goal")
    final_goal = st.text_area(
        "Goal statement", 
        height=150,
        placeholder="Enter the SMARTAR goal here. Be specific, measurable, achievable, relevant, time-bound, adjustable, and recorded."
    )

    # AI refinement (optional)
    if groq_client and final_goal:
        if st.button("✨ Refine Goal with AI (Optional)", type="secondary"):
            with st.spinner("Refining goal..."):
                refined = groq_call(f"""You are an expert educator specialising in the SMARTAR framework and alternative education.

Refine this goal statement into clear, professional, student-centred language suitable for an IEP/support plan. 
Make it SMARTAR compliant: Specific, Measurable, Achievable, Relevant, Time-bound, Adjustable, Recorded.
Return ONLY the refined goal statement, nothing else.

Goal to refine: {final_goal}""")
                final_goal = refined
                st.rerun()

    # Save goal WITH TEAM MEETINGS INTEGRATION
    st.markdown("---")
    if st.button("💾 Save Goal", type="primary", disabled=not final_goal):
        if not staff_name:
            st.warning("Enter your name in the sidebar first.")
        else:
            new_goal = {
                "student_name": selected_name,
                "exclusion_goal": excl_goal.strip() if excl_goal else None,
                "smartar_goal": final_goal.strip(),
                "created_by": staff_name,
                "active": True
            }
            
            # Add Team Meetings context if integration active
            if integration["active"]:
                new_goal["meeting_id"] = integration["meeting_id"]
                new_goal["program"] = integration["program"]
                new_goal["term"] = integration["term"]
                new_goal["week"] = integration["week"]
            
            sb.table("smartar_goals").insert(new_goal).execute()
            
            st.success(f"✅ Goal saved for {selected_name}!")
            
            # Show integration success message
            if integration["active"]:
                st.info(f"""
                🔗 **Goal synced to Team Meeting** (Meeting ID: {integration['meeting_id']})
                
                This goal will automatically appear in the Team Meeting notes.
                """)
                
                # Show return button
                meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
                st.markdown(f"[← Return to Team Meeting]({meeting_url})")
            
            st.rerun()
