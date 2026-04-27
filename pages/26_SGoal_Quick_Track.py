"""
SGoal Quick Track — fast daily SMARTAR goal tracking for CLC LBU staff.
Page 26. Sessions shown are filtered by each goal's AI-assigned tracking period.
"""

import streamlit as st
from datetime import date, datetime
from supabase import create_client

st.set_page_config(
    page_title="SGoal Quick Track",
    page_icon="⚡",
    layout="wide",
)

# ─── Branding ────────────────────────────────────────────────────────────────
TEAL  = "#1A7A6E"
AMBER = "#C8760A"

PERF_LEVELS = ["EXCEEDING", "EXPECTED", "NOT YET"]

PERF_STYLE = {
    "EXCEEDING": ("🌟", "#27ae60", "white"),
    "EXPECTED":  ("✅", "#2980b9", "white"),
    "NOT YET":   ("⚠️", "#e74c3c", "white"),
}

SESSIONS_FOR_PERIOD = {
    "All Day":            ["Morning", "Middle", "Afternoon"],
    "Morning Only":       ["Morning"],
    "Middle Only":        ["Middle"],
    "Afternoon Only":     ["Afternoon"],
    "Morning & Middle":   ["Morning", "Middle"],
    "Middle & Afternoon": ["Middle", "Afternoon"],
}

SESSION_ICONS = {
    "Morning":   "🌅",
    "Middle":    "☀️",
    "Afternoon": "🌤️",
}

# ─── Supabase ─────────────────────────────────────────────────────────────────

@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_sb()

# ─── Data helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_programs():
    try:
        rows = sb.table("students").select("program").execute().data
        progs = sorted({r["program"] for r in rows if r.get("program")})
        return progs if progs else ["JP", "PY", "SY"]
    except Exception:
        return ["JP", "PY", "SY"]


@st.cache_data(ttl=60)
def get_students_for_program(program: str):
    try:
        rows = (
            sb.table("students")
            .select("name")
            .eq("program", program)
            .order("name")
            .execute()
            .data
        )
        return [r["name"] for r in rows]
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_active_goals(student: str):
    try:
        rows = (
            sb.table("smartar_goals")
            .select("id, goal_text, domain, tracking_period")
            .eq("student_name", student)
            .eq("status", "Active")
            .order("created_at")
            .execute()
            .data
        )
        return rows
    except Exception:
        return []


def get_today_tracking(student: str, today_str: str):
    """Returns dict of {(session): performance} for today."""
    try:
        rows = (
            sb.table("smartar_tracking")
            .select("session, performance")
            .eq("student_name", student)
            .eq("date", today_str)
            .execute()
            .data
        )
        return {r["session"]: r["performance"] for r in rows}
    except Exception:
        return {}


def save_tracking(student: str, session: str, performance: str, today_str: str):
    """Upsert tracking entry for today."""
    try:
        # Check if entry exists
        existing = (
            sb.table("smartar_tracking")
            .select("id")
            .eq("student_name", student)
            .eq("date", today_str)
            .eq("session", session)
            .execute()
            .data
        )
        payload = {
            "student_name": student,
            "date":         today_str,
            "session":      session,
            "performance":  performance,
            "updated_at":   datetime.utcnow().isoformat(),
        }
        if existing:
            sb.table("smartar_tracking").update(payload).eq("id", existing[0]["id"]).execute()
        else:
            sb.table("smartar_tracking").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


# ─── Styles ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
  [data-testid="stSidebar"] {{ display: none !important; }}

  /* Session button grid */
  .session-label {{
      font-weight: 700;
      font-size: 15px;
      color: {TEAL};
      margin-bottom: 4px;
  }}
  .goal-header {{
      background: {TEAL}18;
      border-left: 4px solid {TEAL};
      border-radius: 5px;
      padding: 8px 12px;
      margin: 8px 0 6px 0;
      font-size: 13px;
  }}
  .goal-period-tag {{
      display: inline-block;
      background: {AMBER};
      color: white;
      border-radius: 10px;
      padding: 1px 9px;
      font-size: 11px;
      font-weight: 600;
      margin-left: 8px;
  }}
  .today-banner {{
      background: {TEAL};
      color: white;
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 16px;
      text-align: center;
  }}
  .saved-badge {{
      background: #27ae60;
      color: white;
      border-radius: 10px;
      padding: 1px 9px;
      font-size: 11px;
      font-weight: 600;
  }}
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────

st.title("⚡ SGoal Quick Track")
st.markdown(
    "Fast daily SMARTAR goal tracking — keep this open while teaching. "
    "Sessions shown are tailored to each goal's tracking period."
)

today = date.today()
today_str = today.isoformat()
today_fmt = today.strftime("%A, %d %B %Y")

st.markdown(
    f'<div class="today-banner">📅 {today_fmt}</div>',
    unsafe_allow_html=True,
)

# ─── Program + Student selectors ─────────────────────────────────────────────

col_prog, col_student = st.columns([1, 2])

with col_prog:
    programs = get_programs()
    program  = st.selectbox("📚 Program", programs, key="qt_program")

with col_student:
    students = get_students_for_program(program)
    if not students:
        students = []
    student = st.selectbox(
        "👤 Student",
        students if students else ["— no students found —"],
        key="qt_student",
    )

if not students or student == "— no students found —":
    st.info("No students found for this program. Check the SMARTAR Goal Builder or add students.")
    st.stop()

# ─── Load goals + today's tracking ───────────────────────────────────────────

active_goals   = get_active_goals(student)
today_tracking = get_today_tracking(student, today_str)

st.markdown("---")

if not active_goals:
    st.warning(
        f"**{student}** has no active SMARTAR goals. "
        "Set one up in the SMARTAR Goal Builder first."
    )
    st.stop()

# ─── Per-goal tracking blocks ─────────────────────────────────────────────────

for g_idx, goal in enumerate(active_goals):
    period   = goal.get("tracking_period") or "All Day"
    sessions = SESSIONS_FOR_PERIOD.get(period, ["Morning", "Middle", "Afternoon"])
    domain   = goal.get("domain", "")
    goal_text = goal.get("goal_text", "")

    # Truncate goal text for display
    display_goal = goal_text[:85] + "…" if len(goal_text) > 85 else goal_text

    st.markdown(
        f'<div class="goal-header">'
        f'<strong>{domain}</strong>'
        f'<span class="goal-period-tag">{period}</span><br>'
        f'<span style="font-size:12px;color:#444">{display_goal}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Build one row of session columns
    # Only show sessions relevant to this goal's tracking period
    sess_cols = st.columns(len(sessions))

    for s_idx, session in enumerate(sessions):
        current_perf = today_tracking.get(session)
        icon = SESSION_ICONS.get(session, "🕐")

        with sess_cols[s_idx]:
            st.markdown(
                f'<div class="session-label">{icon} {session}</div>',
                unsafe_allow_html=True,
            )

            for perf in PERF_LEVELS:
                p_icon, p_bg, p_fg = PERF_STYLE[perf]
                is_selected = (current_perf == perf)

                if is_selected:
                    # Show highlighted selected state
                    btn_label = f"{p_icon} ✓ {perf}"
                    btn_key   = f"qt_{g_idx}_{session}_{perf}"
                    # Still clickable to deselect / re-confirm
                    if st.button(
                        btn_label,
                        key=btn_key,
                        use_container_width=True,
                        type="primary",
                    ):
                        # Already saved — clicking again re-saves (harmless)
                        save_tracking(student, session, perf, today_str)
                        get_today_tracking.clear()
                        st.rerun()
                else:
                    btn_label = f"{p_icon} {perf}"
                    btn_key   = f"qt_{g_idx}_{session}_{perf}"
                    if st.button(btn_label, key=btn_key, use_container_width=True):
                        if save_tracking(student, session, perf, today_str):
                            get_today_tracking.clear()
                            st.toast(f"✅ {session} → {perf}", icon="✅")
                            st.rerun()

    st.markdown("&nbsp;")

# ─── Today's summary ─────────────────────────────────────────────────────────

if today_tracking:
    st.divider()
    st.markdown(f"##### 📋 Today's Recorded Sessions — {student}")
    cols = st.columns(len(today_tracking))
    for i, (sess, perf) in enumerate(sorted(today_tracking.items())):
        p_icon, p_bg, _ = PERF_STYLE.get(perf, ("", TEAL, "white"))
        cols[i].markdown(
            f"**{sess}**  \n"
            f"<span style='background:{p_bg};color:white;"
            f"padding:2px 10px;border-radius:10px;font-size:12px'>"
            f"{p_icon} {perf}</span>",
            unsafe_allow_html=True,
        )

# ─── Footer ───────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    f"Tracking for **{student}** · {today_fmt}  \n"
    "Data saves instantly. Switch students anytime. "
    "View full reports in **SMARTAR Goal Builder → Progress Reports**."
)
