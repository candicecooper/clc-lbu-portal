import streamlit as st
import json
import os
from datetime import date, datetime, timedelta
from supabase import create_client
from groq import Groq
from urllib.parse import unquote
from collections import defaultdict
import plotly.graph_objects as go
import plotly.io as pio

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="SMARTAR Goal Builder", page_icon="🎯", layout="wide")

# ── Team Meetings Integration ────────────────────────────────────────────────
def check_team_meetings_integration():
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
    url = st.secrets.get("BEHAVIOUR_SUPABASE_URL") or st.secrets.get("supabase", {}).get("url")
    key = st.secrets.get("BEHAVIOUR_SUPABASE_KEY") or st.secrets.get("supabase", {}).get("key")
    if not url or not key:
        st.error("⚠️ Supabase credentials not configured")
        st.stop()
    return create_client(url, key)

@st.cache_resource
def get_groq():
    api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("groq", {}).get("api_key")
    if not api_key:
        return None
    return Groq(api_key=api_key)

sb = get_supabase()
groq_client = get_groq()

# ── Helpers ───────────────────────────────────────────────────────────────────
LEVEL_ORDER  = ["EXCEEDING", "ABOVE", "EXPECTED", "BELOW", "NOT YET"]
LEVEL_EMOJI  = {"EXCEEDING": "🌟", "ABOVE": "✅", "EXPECTED": "🎯", "BELOW": "⚠️", "NOT YET": "❌"}
LEVEL_COLOR  = {"EXCEEDING": "#1a7a3c", "ABOVE": "#2d8a5e", "EXPECTED": "#1d6fa4", "BELOW": "#d97706", "NOT YET": "#c0392b"}

GROUPINGS    = ["Independently", "One to one", "Small group", "Large group", "Unstructured", "With a peer"]
TASK_TYPES   = ["Structured task", "Hands-on activity", "Using equipment", "Paper/pencil task", "Oral/listening activity", "Following a routine", "Computer-based task", "Other"]
SETTINGS     = ["Classroom", "During a maths lesson", "During a literacy lesson", "During morning block", "During afternoon block", "During transitions", "At recess", "At lunch", "On excursion", "During negotiated school time"]
PROMPT_TYPES = ["No prompts", "Visual prompt", "Verbal prompt", "Gestural prompt", "Model prompt", "Partial physical support", "Full physical support", "SSO support", "Verbal and gestural prompts", "Verbal and visual prompts"]
RATE_OPTIONS = [
    "3 out of 5 opportunities",
    "4 out of 5 opportunities", 
    "3 out of 5 days over 3 weeks",
    "4 out of 5 days over 3 weeks",
    "80% of the time over a 3-week period",
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
    r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).gte("session_date", since).order("session_date").execute()
    return r.data or []

def get_today_tracking(goal_id):
    r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).eq("session_date", date.today().isoformat()).execute()
    return r.data or []

def get_recent_tracking(goal_id, sessions=5):
    """Get last N tracking sessions for a goal"""
    r = sb.table("smartar_tracking").select("*").eq("goal_id", goal_id).order("session_date", desc=True).order("recorded_at", desc=True).limit(sessions).execute()
    return r.data or []

def upsert_session(goal_id, student_name, session_time, performance_level):
    today = date.today().isoformat()
    existing = sb.table("smartar_tracking").select("id").eq("goal_id", goal_id).eq("session_date", today).eq("session_time", session_time).execute()
    if existing.data:
        sb.table("smartar_tracking").update({"performance_level": performance_level}).eq("id", existing.data[0]["id"]).execute()
    else:
        sb.table("smartar_tracking").insert({
            "goal_id": goal_id, 
            "student_name": student_name,
            "session_date": today, 
            "session_time": session_time, 
            "performance_level": performance_level
        }).execute()

def calc_percentages(tracking_data):
    counts = {l: 0 for l in LEVEL_ORDER}
    for row in tracking_data:
        if row["performance_level"] in counts:
            counts[row["performance_level"]] += 1
    total = sum(counts.values())
    if total == 0:
        return counts, total, {}
    pcts = {l: round(counts[l] / total * 100, 1) for l in LEVEL_ORDER}
    return counts, total, pcts

def get_gas_dict(goal):
    """Convert individual GAS columns to dictionary"""
    return {
        "EXCEEDING": goal.get("gas_exceeding", ""),
        "ABOVE": goal.get("gas_above", ""),
        "EXPECTED": goal.get("gas_expected", ""),
        "BELOW": goal.get("gas_below", ""),
        "NOT YET": goal.get("gas_not_yet", "")
    }

def check_goal_needs_refinement(goal_id, threshold=3):
    """Check if goal needs refinement based on recent performance"""
    recent = get_recent_tracking(goal_id, sessions=5)
    if len(recent) < threshold:
        return False, 0
    
    # Only count NOT YET (BELOW removed from tracking)
    low_performance = sum(1 for r in recent if r["performance_level"] == "NOT YET")
    if low_performance >= threshold:
        return True, low_performance
    return False, low_performance

def analyze_trend(tracking_data):
    """Analyze if performance is improving, declining, or stable"""
    if len(tracking_data) < 4:
        return "insufficient_data"
    
    # Split into first half and second half
    midpoint = len(tracking_data) // 2
    first_half = tracking_data[:midpoint]
    second_half = tracking_data[midpoint:]
    
    # Calculate average score (EXCEEDING=5, ABOVE=4, EXPECTED=3, BELOW=2, NOT YET=1)
    score_map = {"EXCEEDING": 5, "ABOVE": 4, "EXPECTED": 3, "BELOW": 2, "NOT YET": 1}
    
    first_avg = sum(score_map.get(r["performance_level"], 0) for r in first_half) / len(first_half)
    second_avg = sum(score_map.get(r["performance_level"], 0) for r in second_half) / len(second_half)
    
    diff = second_avg - first_avg
    
    if diff > 0.5:
        return "improving"
    elif diff < -0.5:
        return "declining"
    else:
        return "stable"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
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
    .alert-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 12px 0;
    }
    .success-box {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 12px 0;
    }
    .admin-panel {
        background: #f8fafc;
        border: 2px solid #cbd5e1;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
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
st.sidebar.title("🎯 SMARTAR Tool")

if integration["active"]:
    meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
    st.sidebar.markdown(f"""
    <a href="{meeting_url}" style="display:block;text-align:center;background:#7c3aed;color:white;
    font-weight:600;font-size:0.85rem;padding:0.5rem;border-radius:8px;text-decoration:none;
    margin-bottom:0.5rem;">← Back to Team Meeting</a>
    """, unsafe_allow_html=True)

view = st.sidebar.radio("View", ["🏫 Class Dashboard", "📋 Goal Builder", "📊 Daily Tracking", "📈 Progress Report", "⚙️ Admin Panel"])

st.sidebar.markdown("---")
st.sidebar.caption("SMARTAR + GAS Goal Tracking · CLC LBU")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CLASS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if view == "🏫 Class Dashboard":
    st.title("🏫 Class Dashboard")
    st.caption(f"Today — {date.today().strftime('%A, %d %B %Y')}")

    students = get_students()
    if not students:
        st.info("No students set up yet. Go to **Goal Builder** to add your first student.")
        st.stop()

    prog_filter = st.selectbox("Filter by Program", ["All", "JP", "PY", "SY"], index=0)
    if prog_filter != "All":
        students = [s for s in students if s.get("program") == prog_filter]

    if not students:
        st.warning("No students found for this program.")
        st.stop()

    for student in students:
        goals = get_goals(student["student_name"])
        if not goals:
            continue

        with st.expander(f"**{student['student_name']}** — {student.get('program','?')}  ·  {len(goals)} goal{'s' if len(goals)!=1 else ''}", expanded=True):
            for idx, goal in enumerate(goals, 1):
                tracking = get_tracking(goal["id"], days=21)
                counts, total, pcts = calc_percentages(tracking)
                today_rows = get_today_tracking(goal["id"])
                today_sessions = {r["session_time"]: r["performance_level"] for r in today_rows}
                
                # Check if goal needs refinement
                needs_refinement, low_count = check_goal_needs_refinement(goal["id"])

                st.markdown(f'<span class="goal-badge">Goal {idx}</span>', unsafe_allow_html=True)
                
                if needs_refinement:
                    st.markdown(f'<div class="alert-box">⚠️ <b>Action Needed:</b> {low_count} recent sessions show low performance. Consider refining this goal to be more achievable.</div>', unsafe_allow_html=True)

                if goal.get("exclusion_goal"):
                    st.markdown(f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> {goal["exclusion_goal"]}</div>', unsafe_allow_html=True)

                st.markdown(f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {goal.get("smartar_goal", "No goal")}</div>', unsafe_allow_html=True)

                # Today's sessions
                cols = st.columns([1, 1, 1, 2])
                for i, session in enumerate(["Morning", "Middle", "Afternoon"]):
                    lvl = today_sessions.get(session)
                    if lvl:
                        cols[i].markdown(f"**{session}**<br>{LEVEL_EMOJI.get(lvl,'')} {lvl}", unsafe_allow_html=True)
                    else:
                        cols[i].markdown(f"**{session}**<br>⬜ Not recorded", unsafe_allow_html=True)

                # 21-day summary bar
                if total > 0:
                    bar_parts = []
                    for lvl in LEVEL_ORDER:
                        pct = pcts.get(lvl, 0)
                        if pct > 0:
                            bar_parts.append(f'<div style="width:{pct}%;background:{LEVEL_COLOR[lvl]};height:14px;display:inline-block;"></div>')
                    bar_html = f'<div style="display:flex;width:100%;border-radius:6px;overflow:hidden;margin:6px 0">' + "".join(bar_parts) + '</div>'
                    st.markdown(bar_html, unsafe_allow_html=True)
                    legend = "  ".join([f'{LEVEL_EMOJI[l]} **{l}** {pcts.get(l,0):.0f}%' for l in LEVEL_ORDER if pcts.get(l,0)>0])
                    st.caption(f"Last 21 days ({total} sessions): {legend}")
                else:
                    st.caption("No tracking data yet.")

                st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GOAL BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
elif view == "📋 Goal Builder":
    st.title("📋 SMARTAR Goal Builder")

    tab1, tab2 = st.tabs(["➕ Add / Edit Goals", "👥 Manage Students"])

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
                sc1, sc2 = st.columns([4, 1])
                sc1.write(f"**{s['student_name']}** — {len(goals)} goals")
                
                if sc2.button("Delete", key=f"arch_{s['id']}"):
                    # Delete student (archive not supported - no active column)
                    sb.table("smartar_students").delete().eq("id", s["id"]).execute()
                    st.rerun()
        else:
            st.info("No students yet.")

    with tab1:
        students = get_students()
        if not students:
            st.info("Add a student first in the **Manage Students** tab.")
            st.stop()

        student_options = {s["student_name"]: s for s in students}
        
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
        existing_goals = get_goals(selected_name)

        st.markdown(f'<div class="student-header"><b>{selected_name}</b> · {student.get("program","?")} · {len(existing_goals)} active goals</div>', unsafe_allow_html=True)

        # Show existing goals
        if existing_goals:
            st.subheader("Current Goals")
            for idx, g in enumerate(existing_goals, 1):
                goal_text = g.get("smartar_goal", "No goal text")
                
                # Check if needs refinement
                needs_refinement, low_count = check_goal_needs_refinement(g["id"])
                
                with st.expander(f"Goal {idx} — {goal_text[:80]}..." + (" ⚠️ NEEDS REFINEMENT" if needs_refinement else "")):
                    if needs_refinement:
                        st.markdown(f'<div class="alert-box">⚠️ <b>Action Required:</b> {low_count} recent sessions show NOT YET performance. This goal may be too challenging. Please refine it to be more achievable and support incremental progress.</div>', unsafe_allow_html=True)
                    
                    if g.get("exclusion_goal"):
                        st.markdown(f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> {g.get("exclusion_goal","—")}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {goal_text}</div>', unsafe_allow_html=True)
                    
                    gas = get_gas_dict(g)
                    if any(gas.values()):
                        st.markdown("**GAS Performance Levels:**")
                        for lvl in LEVEL_ORDER:
                            desc = gas.get(lvl, "")
                            if desc:
                                emoji = LEVEL_EMOJI[lvl]
                                color = LEVEL_COLOR[lvl]
                                st.markdown(f'<div class="gas-level-bar"><span class="gas-level-label" style="color:{color}">{emoji} {lvl}</span><span class="gas-level-desc">{desc}</span></div>', unsafe_allow_html=True)
                    
                    if g.get("meeting_id"):
                        st.caption(f"📋 Created from {g.get('program', '')} Team Meeting · Term {g.get('term', '')} Week {g.get('week', '')}")
                    
                    if st.button(f"🗑 Archive Goal {idx}", key=f"del_{g['id']}"):
                        sb.table("smartar_goals").update({"active": False}).eq("id", g["id"]).execute()
                        st.rerun()

        # New goal form
        st.subheader(f"Add New Goal")

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
            skill = st.text_area("Expected skill / behaviour", placeholder="e.g. personal space", height=80)
            grouping = st.selectbox("Grouping", GROUPINGS)
            task_type = st.selectbox("Task type", TASK_TYPES)

        with col2:
            setting = st.selectbox("Setting", SETTINGS)
            prompts = st.selectbox("Prompts", PROMPT_TYPES)
            rate = st.selectbox("Rate / success criteria", RATE_OPTIONS)

        if skill and student_first:
            assembled = f"The student will {skill} {grouping.lower()} during {task_type.lower()} in the {setting.lower()} with a {prompts.lower()}, demonstrating successful use on {rate}."
            st.markdown("**Assembled Goal Preview:**")
            st.info(assembled)
        else:
            assembled = ""

        st.markdown("---")
        if groq_client and assembled:
            if st.button("✨ Refine Goal with AI", type="primary"):
                with st.spinner("Refining goal..."):
                    refined = groq_call(f"""Refine this SMARTAR goal into clear, professional, student-centred language suitable for an IEP/support plan. 
Keep all the specific details (grouping, task, setting, prompts, rate). Return ONLY the refined goal statement.

Goal to refine: {assembled}""")
                    st.session_state["refined_goal"] = refined
                    st.rerun()

        refined_goal = st.session_state.get("refined_goal", assembled)
        final_goal = st.text_area("Final SMARTAR Goal (edit if needed)", value=refined_goal, height=100, key="final_goal_text")

        if groq_client and final_goal:
            if st.button("🎚 Generate GAS Performance Levels", type="secondary"):
                with st.spinner("Generating GAS levels..."):
                    gas_prompt = f"""Create a Goal Attainment Scale (GAS) for this SMARTAR goal:

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
                        if "NOT_YET" in gas_levels and "NOT YET" not in gas_levels:
                            gas_levels["NOT YET"] = gas_levels.pop("NOT_YET")
                        st.session_state["gas_levels"] = gas_levels
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't parse GAS levels. Try again. ({e})")

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

        st.markdown("---")
        if st.button("💾 Save Goal", type="primary", disabled=not final_goal):
            new_goal = {
                "student_name": selected_name,
                "exclusion_goal": excl_goal.strip() if excl_goal else None,
                "smartar_goal": final_goal.strip(),
                "skill": skill.strip() if skill else None,
                "grouping": grouping,
                "task_type": task_type,
                "setting": setting,
                "prompts": prompts,
                "rate": rate,
                "active": True
            }
            
            if edited_gas:
                new_goal["gas_exceeding"] = edited_gas.get("EXCEEDING", "")
                new_goal["gas_above"] = edited_gas.get("ABOVE", "")
                new_goal["gas_expected"] = edited_gas.get("EXPECTED", "")
                new_goal["gas_below"] = edited_gas.get("BELOW", "")
                new_goal["gas_not_yet"] = edited_gas.get("NOT YET", "")
            
            if integration["active"]:
                new_goal["meeting_id"] = integration["meeting_id"]
                new_goal["program"] = integration["program"]
                new_goal["term"] = integration["term"]
                new_goal["week"] = integration["week"]
            
            sb.table("smartar_goals").insert(new_goal).execute()
            
            for k in ["refined_goal", "gas_levels"]:
                st.session_state.pop(k, None)
            
            st.success(f"✅ Goal saved for {selected_name}!")
            
            if integration["active"]:
                st.info(f"""
                🔗 **Goal synced to Team Meeting** (Meeting ID: {integration['meeting_id']})
                
                This goal will automatically appear in the Team Meeting notes.
                """)
                
                meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
                st.markdown(f"[← Return to Team Meeting]({meeting_url})")
            
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DAILY TRACKING (WITH REFINEMENT ALERTS)
# ═══════════════════════════════════════════════════════════════════════════════
elif view == "📊 Daily Tracking":
    st.title("📊 Daily Tracking")

    students = get_students()
    if not students:
        st.info("No students set up yet.")
        st.stop()

    track_date = st.date_input("Tracking date", value=date.today())
    st.markdown(f"**Recording for: {track_date.strftime('%A, %d %B %Y')}**")

    student_options = {s["student_name"]: s for s in students}
    selected_name = st.selectbox("Select student", list(student_options.keys()))
    student = student_options[selected_name]
    goals = get_goals(selected_name)

    if not goals:
        st.info(f"No goals set up for {selected_name}. Go to Goal Builder first.")
        st.stop()

    st.markdown("---")

    for idx, goal in enumerate(goals, 1):
        today_rows = sb.table("smartar_tracking").select("*").eq("goal_id", goal["id"]).eq("session_date", track_date.isoformat()).execute().data or []
        today_sessions = {r["session_time"]: r["performance_level"] for r in today_rows}
        gas = get_gas_dict(goal)
        
        # Check if goal needs refinement
        needs_refinement, low_count = check_goal_needs_refinement(goal["id"])

        st.markdown(f"### Goal {idx}")
        
        if needs_refinement:
            st.markdown(f'<div class="alert-box">⚠️ <b>IMPORTANT:</b> This student has recorded {low_count} sessions of NOT YET performance. <br><br><b>Action Required:</b> Please refine this goal to make it more achievable. We focus on incremental improvements, not persistent failure. Consider adjusting the rate, prompts, or task complexity to support the student\'s success.</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="smartar-box">🎯 {goal.get("smartar_goal", "No goal")}</div>', unsafe_allow_html=True)

        if any(gas.values()):
            with st.expander("📋 View GAS Performance Levels"):
                for lvl in LEVEL_ORDER:
                    desc = gas.get(lvl, "")
                    if desc:
                        color = LEVEL_COLOR[lvl]
                        st.markdown(f'<div class="gas-level-bar"><span class="gas-level-label" style="color:{color}">{LEVEL_EMOJI[lvl]} {lvl}</span><span class="gas-level-desc">{desc}</span></div>', unsafe_allow_html=True)

        st.markdown("**Record session:**")
        session_cols = st.columns(3)
        sessions = ["Morning", "Middle", "Afternoon"]

        for i, session in enumerate(sessions):
            with session_cols[i]:
                st.markdown(f"**{session}**")
                current = today_sessions.get(session)
                if current:
                    st.markdown(f"Currently: {LEVEL_EMOJI.get(current,'')} **{current}**")
                # Only show EXCEEDING, ABOVE, EXPECTED, NOT YET (BELOW removed)
                tracking_levels = ["EXCEEDING", "ABOVE", "EXPECTED", "NOT YET"]
                for lvl in tracking_levels:
                    btn_key = f"track_{goal['id']}_{session}_{lvl}_{track_date}"
                    is_selected = current == lvl
                    label = f"{LEVEL_EMOJI[lvl]} {lvl}" + (" ✓" if is_selected else "")
                    if st.button(label, key=btn_key, use_container_width=True,
                                 type="primary" if is_selected else "secondary"):
                        upsert_session(goal["id"], selected_name, session, lvl)
                        
                        # Show alert if recording NOT YET
                        if lvl == "NOT YET":
                            st.session_state["show_refinement_alert"] = goal["id"]
                        
                        st.rerun()

        # Show refinement reminder if just recorded NOT YET
        if st.session_state.get("show_refinement_alert") == goal["id"]:
            st.markdown(f'<div class="alert-box">⚠️ <b>IMPORTANT:</b> You\'ve recorded NOT YET for this goal. This indicates the goal may be too challenging. Please refine the goal ASAP to make it more achievable and support incremental progress. Our focus is on achievable growth, not documenting persistent challenges.</div>', unsafe_allow_html=True)
            if st.button("I understand - will refine goal as needed", key=f"ack_{goal['id']}"):
                st.session_state.pop("show_refinement_alert", None)
                st.rerun()

        st.markdown("---")

    st.success("Tracking saves immediately when you click a level button.")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PROGRESS REPORT (WITH TREND ANALYSIS)
# ═══════════════════════════════════════════════════════════════════════════════
elif view == "📈 Progress Report":
    st.title("📈 Progress Report")

    students = get_students()
    if not students:
        st.info("No students set up yet.")
        st.stop()

    student_options = {s["student_name"]: s for s in students}
    selected_name = st.selectbox("Select student", list(student_options.keys()))
    student = student_options[selected_name]
    goals = get_goals(selected_name)

    if not goals:
        st.info(f"No goals for {selected_name}.")
        st.stop()

    period = st.radio("Period", ["Last 2 weeks", "Last 3 weeks", "Last 5 weeks"], horizontal=True)
    days_map = {"Last 2 weeks": 14, "Last 3 weeks": 21, "Last 5 weeks": 35}
    days = days_map[period]

    st.markdown(f"## {selected_name} — Progress Report")
    st.caption(f"Period: last {days} days · Program: {student.get('program','?')}")

    for idx, goal in enumerate(goals, 1):
        tracking = get_tracking(goal["id"], days=days)
        counts, total, pcts = calc_percentages(tracking)
        gas = get_gas_dict(goal)
        
        # Analyze trend
        trend = analyze_trend(tracking)
        needs_refinement, low_count = check_goal_needs_refinement(goal["id"])

        st.markdown(f"### Goal {idx}")
        
        # Show trend indicator
        if trend == "improving":
            st.markdown(f'<div class="success-box">📈 <b>Improving Trend:</b> This goal shows incremental progress - student performance is getting better over time!</div>', unsafe_allow_html=True)
        elif trend == "declining":
            st.markdown(f'<div class="alert-box">📉 <b>Declining Trend:</b> Performance is decreasing. This goal may need refinement to be more achievable.</div>', unsafe_allow_html=True)
        elif trend == "stable" and needs_refinement:
            st.markdown(f'<div class="alert-box">➡️ <b>Stable but Low:</b> Performance is consistent but below expectations. Consider refining this goal for incremental success.</div>', unsafe_allow_html=True)
        
        if goal.get("exclusion_goal"):
            st.markdown(f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> {goal["exclusion_goal"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {goal.get("smartar_goal", "No goal")}</div>', unsafe_allow_html=True)

        if total == 0:
            st.warning("No tracking data for this period.")
            continue

        # Summary metrics
        mc = st.columns(5)
        for i, lvl in enumerate(LEVEL_ORDER):
            pct = pcts.get(lvl, 0)
            mc[i].metric(f"{LEVEL_EMOJI[lvl]} {lvl}", f"{pct:.0f}%", f"{counts[lvl]} sessions")

        # Progress bar
        bar_parts = []
        for lvl in LEVEL_ORDER:
            pct = pcts.get(lvl, 0)
            if pct > 0:
                bar_parts.append(f'<div style="width:{pct}%;background:{LEVEL_COLOR[lvl]};height:22px;display:inline-block;"></div>')
        bar_html = '<div style="display:flex;width:100%;border-radius:8px;overflow:hidden;margin:12px 0">' + "".join(bar_parts) + '</div>'
        st.markdown(bar_html, unsafe_allow_html=True)
        st.caption(f"Total sessions recorded: {total}")

        # Pie Chart - Performance Distribution
        st.markdown("---")
        st.markdown("**📊 Performance Distribution Chart:**")
        
        # Create pie chart data (only include levels with data)
        chart_labels = []
        chart_values = []
        chart_colors = []
        
        for lvl in LEVEL_ORDER:
            if counts[lvl] > 0:
                chart_labels.append(f"{LEVEL_EMOJI[lvl]} {lvl}")
                chart_values.append(counts[lvl])
                chart_colors.append(LEVEL_COLOR[lvl])
        
        # Create Plotly pie chart
        fig = go.Figure(data=[go.Pie(
            labels=chart_labels,
            values=chart_values,
            marker=dict(colors=chart_colors),
            textinfo='label+percent',
            textfont=dict(size=14),
            hovertemplate='<b>%{label}</b><br>Sessions: %{value}<br>Percentage: %{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title=dict(
                text=f"{selected_name} - Goal {idx} Performance ({period})",
                font=dict(size=18, color="#1d6fa4")
            ),
            showlegend=True,
            height=500,
            margin=dict(t=100, b=50, l=50, r=50)
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=True)
        
        # Download button
        img_bytes = pio.to_image(fig, format="png", width=1200, height=800, scale=2)
        st.download_button(
            label="📥 Download Chart as PNG",
            data=img_bytes,
            file_name=f"{selected_name}_Goal{idx}_Performance_{period.replace(' ', '_')}.png",
            mime="image/png",
            key=f"download_chart_{goal['id']}"
        )
        
        st.markdown("---")

        # Trend over time
        if tracking:
            from collections import defaultdict
            daily = defaultdict(lambda: {l: 0 for l in LEVEL_ORDER})
            for r in tracking:
                daily[r["session_date"]][r["performance_level"]] += 1
            dates_sorted = sorted(daily.keys())

            st.markdown("**Session breakdown by day:**")
            for d in dates_sorted[-10:]:
                row = daily[d]
                day_total = sum(row.values())
                if day_total == 0:
                    continue
                day_label = datetime.strptime(d, "%Y-%m-%d").strftime("%d %b")
                pills = " ".join([f'<span class="metric-pill" style="background:{LEVEL_COLOR[l]}22;color:{LEVEL_COLOR[l]}">{LEVEL_EMOJI[l]} {l}: {row[l]}</span>' for l in LEVEL_ORDER if row[l] > 0])
                st.markdown(f"**{day_label}** — {pills}", unsafe_allow_html=True)

        # AI narrative
        if groq_client:
            if st.button(f"✨ Generate Progress Summary (AI)", key=f"ai_report_{goal['id']}"):
                with st.spinner("Generating summary..."):
                    level_summary = ", ".join([f"{lvl}: {pcts.get(lvl,0):.0f}%" for lvl in LEVEL_ORDER])
                    trend_text = "improving" if trend == "improving" else "declining" if trend == "declining" else "stable"
                    narrative = groq_call(f"""Write a brief, professional progress summary (3–4 sentences) for a student's IEP/review meeting.

Student: {selected_name}
SMARTAR Goal: {goal.get('smartar_goal', 'No goal')}
Period: last {days} days
Performance distribution: {level_summary}
Trend: {trend_text}
Total sessions recorded: {total}

Use trauma-informed, strengths-based language. Reference the BSEM framework if relevant (Regulate, Relate, Reason). 
Be specific about the data. Focus on incremental improvements. If the trend is declining or stable with low performance, suggest refining the goal to support achievable progress rather than continuing to track persistent challenges.""")
                    st.markdown("**AI-Generated Progress Summary:**")
                    st.success(narrative)
        else:
            st.caption("⚠️ AI summaries unavailable (Groq API key not configured)")

        st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ADMIN PANEL (FULL EDITING CAPABILITY)
# ═══════════════════════════════════════════════════════════════════════════════
elif view == "⚙️ Admin Panel":
    st.title("⚙️ Admin Panel")
    st.caption("Manage students, pre-populate goals from entry meetings, and edit existing goals")

    tab1, tab2, tab3 = st.tabs(["👥 Manage Students", "📝 Edit Goals", "➕ Add Pre-Populated Goals"])
    
    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1: MANAGE STUDENTS
    # ─────────────────────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Add New Student")
        col1, col2 = st.columns([3, 1])
        new_student_name = col1.text_input("Student name", key="admin_new_student")
        if col2.button("Add Student", type="primary", key="admin_add_student"):
            if new_student_name.strip():
                sb.table("smartar_students").insert({"student_name": new_student_name.strip()}).execute()
                st.success(f"✅ {new_student_name.strip()} added to the system.")
                st.rerun()
            else:
                st.warning("Please enter a student name.")
        
        st.markdown("---")
        st.subheader("All Students")
        
        students = get_students()
        if students:
            for s in students:
                goals = get_goals(s["student_name"])
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{s['student_name']}** — {len(goals)} active goals")
                if col2.button("Delete", key=f"admin_arch_{s['id']}"):
                    sb.table("smartar_students").delete().eq("id", s["id"]).execute()
                    st.success(f"Deleted {s['student_name']}")
                    st.rerun()
        else:
            st.info("No students in the system yet.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2: EDIT EXISTING GOALS
    # ─────────────────────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Edit Existing Goals")
        
        students = get_students()
        if not students:
            st.info("No students in the system yet.")
        else:
            selected_student = st.selectbox("Select student to edit", 
                                           [s["student_name"] for s in students],
                                           key="admin_edit_student")
            
            goals = get_goals(selected_student)
            
            if not goals:
                st.info(f"No goals for {selected_student}. Use 'Add Pre-Populated Goals' tab to create initial goals.")
            else:
                for idx, goal in enumerate(goals, 1):
                    with st.expander(f"Goal {idx} — {goal.get('smartar_goal', 'No goal')[:60]}...", expanded=False):
                        st.markdown("### Edit Goal")
                        
                        # Editable fields
                        edit_excl = st.text_area(
                            "Exclusion Goal",
                            value=goal.get("exclusion_goal", ""),
                            height=100,
                            key=f"edit_excl_{goal['id']}"
                        )
                        
                        edit_smartar = st.text_area(
                            "SMARTAR Goal",
                            value=goal.get("smartar_goal", ""),
                            height=120,
                            key=f"edit_smartar_{goal['id']}"
                        )
                        
                        st.markdown("**GAS Performance Levels:**")
                        edit_gas = {}
                        for lvl in LEVEL_ORDER:
                            col_name = f"gas_{lvl.lower().replace(' ', '_')}"
                            edit_gas[lvl] = st.text_area(
                                f"{LEVEL_EMOJI[lvl]} {lvl}",
                                value=goal.get(col_name, ""),
                                height=80,
                                key=f"edit_gas_{lvl}_{goal['id']}"
                            )
                        
                        # Save button
                        col1, col2 = st.columns([1, 3])
                        if col1.button("💾 Save Changes", key=f"save_goal_{goal['id']}", type="primary"):
                            update_data = {
                                "exclusion_goal": edit_excl.strip() if edit_excl.strip() else None,
                                "smartar_goal": edit_smartar.strip(),
                                "gas_exceeding": edit_gas.get("EXCEEDING", ""),
                                "gas_above": edit_gas.get("ABOVE", ""),
                                "gas_expected": edit_gas.get("EXPECTED", ""),
                                "gas_below": edit_gas.get("BELOW", ""),
                                "gas_not_yet": edit_gas.get("NOT YET", ""),
                                "updated_at": datetime.utcnow().isoformat()
                            }
                            sb.table("smartar_goals").update(update_data).eq("id", goal["id"]).execute()
                            st.success(f"✅ Goal {idx} updated for {selected_student}")
                            st.rerun()
                        
                        if col2.button("🗑 Archive This Goal", key=f"archive_goal_{goal['id']}"):
                            sb.table("smartar_goals").update({"active": False}).eq("id", goal["id"]).execute()
                            st.success(f"Goal {idx} archived")
                            st.rerun()
    
    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3: ADD PRE-POPULATED GOALS
    # ─────────────────────────────────────────────────────────────────────────
    with tab3:
        st.subheader("Pre-Populate Goals from Entry Meeting")
        st.caption("Add initial goals before teachers start tracking - teachers can refine later based on observations")
        
        students = get_students()
        if not students:
            st.info("No students in the system yet. Add them in the 'Manage Students' tab.")
        else:
            selected_student = st.selectbox("Select student", 
                                           [s["student_name"] for s in students],
                                           key="admin_prepop_student")
            
            goals = get_goals(selected_student)
            if goals:
                st.info(f"{selected_student} currently has {len(goals)} active goal(s). You can add more below.")
            
            st.markdown("---")
            st.markdown("### New Goal Details")
            
            prepop_excl = st.text_area(
                "🏫 Exclusion Goal (from main school)",
                placeholder="Paste exclusion goal from entry meeting...",
                height=100,
                key="prepop_excl"
            )
            
            prepop_smartar = st.text_area(
                "🎯 Initial SMARTAR Goal",
                placeholder="Enter initial SMARTAR goal based on entry meeting assessment...",
                height=120,
                key="prepop_smartar"
            )
            
            st.markdown("**Optional: Add GAS Performance Levels**")
            st.caption("You can add these now or teachers can generate them later")
            
            with st.expander("Add GAS Levels (Optional)"):
                prepop_gas = {}
                for lvl in LEVEL_ORDER:
                    prepop_gas[lvl] = st.text_area(
                        f"{LEVEL_EMOJI[lvl]} {lvl}",
                        placeholder=f"Enter {lvl} performance description...",
                        height=70,
                        key=f"prepop_gas_{lvl}"
                    )
            
            if st.button("💾 Save Pre-Populated Goal", type="primary", key="save_prepop"):
                if prepop_smartar.strip():
                    new_goal = {
                        "student_name": selected_student,
                        "exclusion_goal": prepop_excl.strip() if prepop_excl.strip() else None,
                        "smartar_goal": prepop_smartar.strip(),
                        "gas_exceeding": prepop_gas.get("EXCEEDING", ""),
                        "gas_above": prepop_gas.get("ABOVE", ""),
                        "gas_expected": prepop_gas.get("EXPECTED", ""),
                        "gas_below": prepop_gas.get("BELOW", ""),
                        "gas_not_yet": prepop_gas.get("NOT YET", ""),
                        "active": True
                    }
                    sb.table("smartar_goals").insert(new_goal).execute()
                    st.success(f"✅ Goal pre-populated for {selected_student}. Teachers can now begin tracking and refine as needed.")
                    st.rerun()
                else:
                    st.warning("Please enter a SMARTAR goal.")
