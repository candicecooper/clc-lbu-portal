import streamlit as st
import json
import os
from datetime import date, datetime, timedelta
from supabase import create_client
from groq import Groq
from urllib.parse import unquote

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="SMARTAR Goal Builder", page_icon="🎯", layout="wide")

# ── Team Meetings Integration Check (NEW) ────────────────────────────────────
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
    }

integration = check_team_meetings_integration()

# ── Clients ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    # Try flat structure first, then nested
    url = st.secrets.get("BEHAVIOUR_SUPABASE_URL") or st.secrets.get("supabase", {}).get("url")
    key = st.secrets.get("BEHAVIOUR_SUPABASE_KEY") or st.secrets.get("supabase", {}).get("key")
    if not url or not key:
        st.error("⚠️ Supabase credentials not configured")
        st.stop()
    return create_client(url, key)

@st.cache_resource
def get_groq():
    # Try flat structure first, then nested
    api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
    if not api_key:
        st.warning("⚠️ Groq API key not configured - AI features will be disabled")
        return None
    return Groq(api_key=api_key)

sb = get_supabase()
groq_client = get_groq()

# ── Helpers ───────────────────────────────────────────────────────────────────
LEVEL_ORDER  = ["EXCEEDING", "ABOVE", "EXPECTED", "BELOW", "NOT YET"]
LEVEL_EMOJI  = {"EXCEEDING": "🌟", "ABOVE": "✅", "EXPECTED": "🎯", "BELOW": "⚠️", "NOT YET": "❌"}
LEVEL_COLOR  = {"EXCEEDING": "#1a7a3c", "ABOVE": "#2d8a5e", "EXPECTED": "#1d6fa4", "BELOW": "#d97706", "NOT YET": "#c0392b"}

GROUPINGS    = ["Independently", "One to one", "Small group", "Large group", "Unstructured", "With a peer"]
TASK_TYPES   = ["Written task", "Hands-on activity", "Using equipment", "Paper/pencil task", "Oral/listening activity", "Following a routine", "Computer-based task", "Other"]
SETTINGS     = ["During a maths lesson", "During a literacy lesson", "During morning block", "During afternoon block", "During transitions", "At recess", "At lunch", "On excursion", "During negotiated school time", "During a learning activity"]
PROMPT_TYPES = ["independently (no prompts)", "with a gestural prompt", "with a verbal prompt", "with a visual prompt", "with a model prompt", "with partial physical support", "with full physical support", "with SSO support", "with verbal and gestural prompts", "with verbal and visual prompts"]
RATE_OPTIONS = [
    "3 out of 5 days over 3 weeks",
    "4 out of 5 days over 3 weeks",
    "3 out of 5 days over 5 weeks",
    "80% of the time over a 3-week period",
    "80% of the time over a 5-week period",
    "3 out of 3 times over a 3-week period",
    "on 3 consecutive occasions",
    "consistently over 2 weeks",
]

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
    q = q.eq("active", True).order("created_at", desc=False)
    return q.execute().data or []

def get_tracking(goal_id, days=30):
    since = (date.today() - timedelta(days=days)).isoformat()
    r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).gte("tracked_date", since).order("tracked_date").execute()
    return r.data or []

def get_today_tracking(goal_id):
    r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).eq("tracked_date", date.today().isoformat()).execute()
    return r.data or []

def upsert_session(goal_id, session, level, staff):
    today = date.today().isoformat()
    existing = sb.table("smartar_tracking").select("id").eq("goal_id", goal_id).eq("tracked_date", today).eq("session", session).execute()
    if existing.data:
        sb.table("smartar_tracking").update({"level": level, "staff_name": staff, "updated_at": datetime.utcnow().isoformat()}).eq("id", existing.data[0]["id"]).execute()
    else:
        sb.table("smartar_tracking").insert({"goal_id": goal_id, "tracked_date": today, "session": session, "level": level, "staff_name": staff}).execute()

def calc_percentages(tracking_data):
    counts = {l: 0 for l in LEVEL_ORDER}
    for row in tracking_data:
        if row["level"] in counts:
            counts[row["level"]] += 1
    total = sum(counts.values())
    if total == 0:
        return counts, total, {}
    pcts = {l: round(counts[l] / total * 100, 1) for l in LEVEL_ORDER}
    return counts, total, pcts

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .gas-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .gas-level-bar {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .gas-level-label {
        font-weight: 600;
        font-size: 0.82rem;
        width: 90px;
        flex-shrink: 0;
    }
    .gas-level-desc {
        font-size: 0.85rem;
        color: #374151;
        flex: 1;
    }
    .student-header {
        background: linear-gradient(135deg, #1d6fa4, #134e7a);
        color: white;
        padding: 14px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
    .metric-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }
    .session-btn-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    .goal-badge {
        background: #e0f2fe;
        color: #0369a1;
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
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
    div[data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 0.95rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ── Team Meetings Integration Banner (NEW) ───────────────────────────────────
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
st.sidebar.title("🎯 SMARTAR Tool")
staff_name = st.sidebar.text_input("Your name", key="staff_name", placeholder="Enter your name")

# Return to Team Meeting button if integration active (NEW)
if integration["active"]:
    meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
    st.sidebar.markdown(f"""
    <a href="{meeting_url}" style="display:block;text-align:center;background:#7c3aed;color:white;
    font-weight:600;font-size:0.85rem;padding:0.5rem;border-radius:8px;text-decoration:none;
    margin-bottom:0.5rem;">← Back to Team Meeting</a>
    """, unsafe_allow_html=True)

view = st.sidebar.radio("View", ["📋 Goal Builder"])

st.sidebar.markdown("---")
st.sidebar.info("📊 **Tracking Features Temporarily Disabled**\n\nClass Dashboard, Daily Tracking, and Progress Reports are disabled due to database schema differences. Goal Builder with Team Meetings integration is fully functional.")
st.sidebar.markdown("---")
st.sidebar.caption("SMARTAR + GAS Goal Tracking · CLC LBU")

# ═══════════════════════════════════════════════════════════════════════════════
# GOAL BUILDER (WITH TEAM MEETINGS INTEGRATION)
# ═══════════════════════════════════════════════════════════════════════════════
st.title("📋 SMARTAR Goal Builder")

tab1, tab2 = st.tabs(["➕ Add / Edit Goals", "👥 Manage Students"])

# ── Student management (UNCHANGED) ────────────────────────────────────────
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

# ── Goal builder (WITH INTEGRATION ADDED) ─────────────────────────────────
with tab1:
    students = get_students()
    if not students:
        st.info("Add a student first in the **Manage Students** tab.")
        st.stop()

    student_options = {s["student_name"]: s for s in students}
    
    # (NEW) Pre-select student from Team Meetings if integration active
    if integration["active"] and integration["student"]:
        if integration["student"] in student_options:
            default_idx = list(student_options.keys()).index(integration["student"])
        else:
            st.info(f"Student '{integration['student']}' from Team Meeting not found. Add them in 'Manage Students' tab or select different student.")
            default_idx = 0
    else:
        default_idx = 0
    
    selected_name = st.selectbox("Select student", list(student_options.keys()), index=default_idx)
    student = student_options[selected_name]
    existing_goals = get_goals(student["student_name"])

    st.markdown(f'<div class="student-header"><b>{selected_name}</b> · {student.get("program","?")} · {len(existing_goals)}/4 goals</div>', unsafe_allow_html=True)

    # Show existing goals
    if existing_goals:
        st.subheader("Current Goals")
        for idx, g in enumerate(existing_goals, 1):
            goal_text = g.get("smartar_goal", "No goal text")
            with st.expander(f"Goal {idx} — {goal_text[:80]}..."):
                st.markdown(f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> {g.get("exclusion_goal","—")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {goal_text}</div>', unsafe_allow_html=True)
                gas = json.loads(g.get("gas_levels", "{}")) if isinstance(g.get("gas_levels"), str) else (g.get("gas_levels") or {})
                if gas:
                    st.markdown("**GAS Performance Levels:**")
                    for lvl in LEVEL_ORDER:
                        desc = gas.get(lvl, "")
                        emoji = LEVEL_EMOJI[lvl]
                        color = LEVEL_COLOR[lvl]
                        st.markdown(f'<div class="gas-level-bar"><span class="gas-level-label" style="color:{color}">{emoji} {lvl}</span><span class="gas-level-desc">{desc}</span></div>', unsafe_allow_html=True)
                
                # (NEW) Show Team Meeting context if this goal has it
                if g.get("meeting_id"):
                    st.caption(f"📋 Created from {g.get('program', '')} Team Meeting · Term {g.get('term', '')} Week {g.get('week', '')}")
                
                if st.button(f"🗑 Archive Goal {idx}", key=f"del_{g['id']}"):
                    sb.table("smartar_goals").update({"active": False}).eq("id", g["id"]).execute()
                    st.rerun()

    # New goal form (UNCHANGED except save section)
    if len(existing_goals) >= 4:
        st.warning("This student already has 4 active goals. Archive one before adding another.")
        st.stop()

    st.subheader(f"Add Goal {len(existing_goals)+1}")

    excl_goal = st.text_area(
        "🏫 Exclusion Goal (from main school)",
        placeholder="Paste the exclusion goal as received from the main school...",
        height=80
    )

    st.markdown("#### Build the SMARTAR Goal")
    st.caption("Complete each field — the goal statement will be assembled automatically, then refined by AI.")

    col1, col2 = st.columns(2)

    with col1:
        student_first = st.text_input("Student first name (as it appears in goal)", value=selected_name.split()[0])
        skill = st.text_area("Expected skill / behaviour", placeholder="e.g. build his learning resilience by staying on task", height=80)
        grouping = st.selectbox("Grouping", GROUPINGS)
        task_type = st.selectbox("Task type", TASK_TYPES)

    with col2:
        setting = st.selectbox("Setting", SETTINGS)
        time_freq = st.text_input("Time / frequency of assessment", placeholder="e.g. each day, once a week, daily")
        prompts = st.selectbox("Prompts (from least to most)", PROMPT_TYPES)
        rate = st.selectbox("Rate / success criteria", RATE_OPTIONS)

    # Assemble preview goal
    if skill and student_first:
        assembled = f"{student_first} will {skill} {grouping.lower()} {task_type.lower()} {setting.lower()} {time_freq} {prompts} {rate}."
        st.markdown("**Assembled Goal Preview:**")
        st.info(assembled)
    else:
        assembled = ""

    # AI refinement
    st.markdown("---")
    col_a, col_b = st.columns(2)

    if col_a.button("✨ Refine Goal with AI", disabled=(not assembled or not groq_client), type="primary"):
        with st.spinner("Refining goal..."):
            refined = groq_call(f"""You are an expert educator specialising in the SMARTAR framework and alternative education.

Refine this goal statement into clear, professional, student-centred language suitable for an IEP/support plan. 
Keep all the specific details (grouping, task, setting, time, prompts, rate). 
Do NOT change the student's name. Return ONLY the refined goal statement, nothing else.

Goal to refine: {assembled}""")
        st.session_state["refined_goal"] = refined

    refined_goal = st.session_state.get("refined_goal", assembled)
    if refined_goal:
        final_goal = st.text_area("Final SMARTAR Goal (edit if needed)", value=refined_goal, height=100, key="final_goal_text")
    else:
        final_goal = assembled

    # GAS level generation
    if st.button("🎚 Generate GAS Performance Levels", disabled=(not final_goal or not groq_client), type="secondary"):
        with st.spinner("Generating GAS levels..."):
            gas_prompt = f"""You are an expert educator creating a Goal Attainment Scale (GAS) for this SMARTAR goal:

"{final_goal}"

Create 5 performance level descriptions that logically scale above and below this EXPECTED level.
The EXPECTED level IS the goal as written.

Return ONLY a JSON object with these exact keys: EXCEEDING, ABOVE, EXPECTED, BELOW, NOT_YET
Each value should be a brief modified version of the goal showing what the student does at that level.
Keep the student name. Only modify the rate/frequency/success criteria to show each level.
No markdown, no explanation, pure JSON only."""
            raw = groq_call(gas_prompt)
            try:
                raw_clean = raw.strip().strip("```json").strip("```").strip()
                gas_levels = json.loads(raw_clean)
                # normalise key
                if "NOT_YET" in gas_levels and "NOT YET" not in gas_levels:
                    gas_levels["NOT YET"] = gas_levels.pop("NOT_YET")
                st.session_state["gas_levels"] = gas_levels
            except Exception as e:
                st.error(f"Couldn't parse GAS levels. Try again. ({e})")
                st.code(raw)

    gas_levels = st.session_state.get("gas_levels", {})
    if gas_levels:
        st.markdown("**Review GAS Performance Levels:**")
        edited_gas = {}
        for lvl in LEVEL_ORDER:
            key = lvl if lvl in gas_levels else lvl.replace(" ", "_")
            default = gas_levels.get(lvl, gas_levels.get(key, ""))
            color = LEVEL_COLOR[lvl]
            edited_gas[lvl] = st.text_area(
                f"{LEVEL_EMOJI[lvl]} {lvl}",
                value=default,
                height=70,
                key=f"gas_edit_{lvl}"
            )
    else:
        edited_gas = {}

    # Save goal (WITH TEAM MEETINGS INTEGRATION ADDED)
    st.markdown("---")
    if st.button("💾 Save Goal", type="primary", disabled=not final_goal):
        if not staff_name:
            st.warning("Enter your name in the sidebar first.")
        else:
            new_goal = {
                "student_name": selected_name,
                "exclusion_goal": excl_goal.strip() if excl_goal else None,
                "smartar_goal": final_goal.strip(),
                "gas_levels": json.dumps(edited_gas) if edited_gas else None,
                "created_by": staff_name,
                "active": True
            }
            
            # (NEW) Add Team Meetings context if integration active
            if integration["active"]:
                new_goal["meeting_id"] = integration["meeting_id"]
                new_goal["program"] = integration["program"]
                new_goal["term"] = integration["term"]
                new_goal["week"] = integration["week"]
            
            sb.table("smartar_goals").insert(new_goal).execute()
            
            # clear session state
            for k in ["refined_goal", "gas_levels"]:
                st.session_state.pop(k, None)
            
            st.success(f"✅ Goal saved for {selected_name}!")
            
            # (NEW) Show integration success message
            if integration["active"]:
                st.info(f"""
                🔗 **Goal synced to Team Meeting** (Meeting ID: {integration['meeting_id']})
                
                This goal will automatically appear in the Team Meeting notes.
                """)
                
                # Show return button
                meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
                st.markdown(f"[← Return to Team Meeting]({meeting_url})")
            
            st.rerun()
