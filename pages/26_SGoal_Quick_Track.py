"""
SGoal Quick Track — fast daily SMARTAR goal tracking for CLC LBU staff.
Page 26. Sessions filtered by each goal's tracking period.
"""

import streamlit as st
from datetime import date, datetime
from supabase import create_client

st.set_page_config(page_title="SGoal Quick Track", page_icon="⚡", layout="wide")

TEAL  = "#1A7A6E"
AMBER = "#C8760A"

# 4 tracking levels — matches Goal Builder (BELOW not tracked daily)
PERF_LEVELS = ["EXCEEDING", "ABOVE", "EXPECTED", "NOT YET"]
PERF_STYLE  = {
    "EXCEEDING": ("🌟", "#27ae60"),
    "ABOVE":     ("✅", "#2ecc71"),
    "EXPECTED":  ("🎯", "#2980b9"),
    "NOT YET":   ("❌", "#c0392b"),
}
SESSION_ICONS = {"Morning": "🌅", "Middle": "☀️", "Afternoon": "🌤️"}
SESSIONS_FOR_PERIOD = {
    "All Day":            ["Morning", "Middle", "Afternoon"],
    "Morning Only":       ["Morning"],
    "Middle Only":        ["Middle"],
    "Afternoon Only":     ["Afternoon"],
    "Morning & Middle":   ["Morning", "Middle"],
    "Middle & Afternoon": ["Middle", "Afternoon"],
}

# ── Supabase — same project as Goal Builder ───────────────────────────────────
@st.cache_resource
def get_sb():
    # Priority: [supabase] section first (written by start.sh from BEHAVIOUR_ vars)
    # then direct BEHAVIOUR_ keys — never fall through to SUPABASE_URL (wrong project)
    url = (
        st.secrets.get("supabase", {}).get("url")
        or st.secrets.get("BEHAVIOUR_SUPABASE_URL")
    )
    key = (
        st.secrets.get("supabase", {}).get("key")
        or st.secrets.get("BEHAVIOUR_SUPABASE_KEY")
    )
    if not url or not key:
        st.error("⚠️ Supabase credentials not found.")
        st.stop()
    return create_client(url, key)

sb = get_sb()

# ── Data helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def get_all_students():
    """Load from smartar_students — same table as Goal Builder."""
    try:
        rows = (
            sb.table("smartar_students")
            .select("student_name, program")
            .eq("active", True)
            .order("student_name")
            .execute().data
        )
        return rows or []
    except Exception as e:
        st.error(f"Error loading students: {e}")
        return []


@st.cache_data(ttl=30)
def get_active_goals(student_name: str):
    """Load active goals — uses active=True and smartar_goal column."""
    try:
        rows = (
            sb.table("smartar_goals")
            .select("id, smartar_goal, tracking_period")
            .eq("student_name", student_name)
            .eq("active", True)
            .order("created_at")
            .execute().data
        )
        return rows or []
    except Exception as e:
        st.error(f"Error loading goals: {e}")
        return []


def get_today_sessions(student_name: str, today_str: str):
    """Returns dict {(goal_id, session_time): performance_level} for today."""
    try:
        rows = (
            sb.table("smartar_tracking")
            .select("goal_id, session_time, performance_level")
            .eq("student_name", student_name)
            .eq("session_date", today_str)
            .execute().data
        )
        return {(r["goal_id"], r["session_time"]): r["performance_level"] for r in rows}
    except Exception:
        return {}


def save_session(goal_id, student_name: str, session_time: str,
                 performance_level: str, today_str: str) -> bool:
    """Upsert a tracking record — matches smartar_tracking schema."""
    try:
        existing = (
            sb.table("smartar_tracking")
            .select("id")
            .eq("goal_id", goal_id)
            .eq("session_date", today_str)
            .eq("session_time", session_time)
            .execute().data
        )
        payload = {
            "goal_id":           goal_id,
            "student_name":      student_name,
            "session_date":      today_str,
            "session_time":      session_time,
            "performance_level": performance_level,
        }
        if existing:
            sb.table("smartar_tracking").update(payload).eq("id", existing[0]["id"]).execute()
        else:
            sb.table("smartar_tracking").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  [data-testid="stSidebar"] {{ display: none !important; }}
  .today-banner {{
      background: {TEAL}; color: white; border-radius: 8px;
      padding: 8px 16px; font-size: 15px; font-weight: 600;
      margin-bottom: 16px; text-align: center;
  }}
  .goal-header {{
      background: {TEAL}18; border-left: 4px solid {TEAL};
      border-radius: 5px; padding: 8px 12px; margin: 10px 0 6px 0; font-size: 13px;
  }}
  .period-tag {{
      display: inline-block; background: {AMBER}; color: white;
      border-radius: 10px; padding: 1px 9px; font-size: 11px;
      font-weight: 600; margin-left: 8px;
  }}
  .sess-label {{
      font-weight: 700; font-size: 14px; color: {TEAL}; margin-bottom: 4px;
  }}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("⚡ SGoal Quick Track")
st.markdown(
    "Fast daily SMARTAR goal tracking — keep this open while teaching. "
    "Sessions shown are tailored to each goal's tracking period."
)

today     = date.today()
today_str = today.isoformat()
today_fmt = today.strftime("%A, %d %B %Y")

st.markdown(f'<div class="today-banner">📅 {today_fmt}</div>', unsafe_allow_html=True)

# ── Student selector ──────────────────────────────────────────────────────────
all_students = get_all_students()

if not all_students:
    st.warning("No students found. Add students in the SMARTAR Goal Builder first.")
    st.stop()

# Group by program for the filter
programs_avail = sorted({s.get("program","?") for s in all_students})
col_prog, col_student = st.columns([1, 2])

with col_prog:
    prog_opts = ["All"] + programs_avail
    program   = st.selectbox("📚 Program", prog_opts, key="qt_prog")

with col_student:
    if program == "All":
        filtered = [s["student_name"] for s in all_students]
    else:
        filtered = [s["student_name"] for s in all_students if s.get("program") == program]

    if not filtered:
        st.warning("No students in this program.")
        st.stop()

    student = st.selectbox("👤 Student", filtered, key="qt_student")

# ── Load goals + today's tracking ────────────────────────────────────────────
active_goals  = get_active_goals(student)
today_tracked = get_today_sessions(student, today_str)

st.markdown("---")

if not active_goals:
    st.warning(
        f"**{student}** has no active SMARTAR goals. "
        "Set one up in the SMARTAR Goal Builder first."
    )
    st.stop()

# ── Per-goal tracking blocks ──────────────────────────────────────────────────
for g_idx, goal in enumerate(active_goals):
    goal_id    = goal["id"]
    period     = goal.get("tracking_period") or "All Day"
    sessions   = SESSIONS_FOR_PERIOD.get(period, ["Morning", "Middle", "Afternoon"])
    goal_text  = goal.get("smartar_goal") or goal.get("goal_text") or "—"
    display    = goal_text[:85] + "…" if len(goal_text) > 85 else goal_text

    st.markdown(
        f'<div class="goal-header">'
        f'<strong>Goal {g_idx + 1}</strong>'
        f'<span class="period-tag">{period}</span><br>'
        f'<span style="font-size:12px;color:#444">{display}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    sess_cols = st.columns(len(sessions))

    for s_idx, session in enumerate(sessions):
        current = today_tracked.get((goal_id, session))
        icon    = SESSION_ICONS.get(session, "🕐")

        with sess_cols[s_idx]:
            st.markdown(
                f'<div class="sess-label">{icon} {session}</div>',
                unsafe_allow_html=True,
            )
            for perf in PERF_LEVELS:
                p_icon, p_bg = PERF_STYLE[perf]
                is_sel  = current == perf
                label   = f"{p_icon} {'✓ ' if is_sel else ''}{perf}"
                btn_key = f"qt_{g_idx}_{session}_{perf}"
                if st.button(label, key=btn_key, use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    if save_session(goal_id, student, session, perf, today_str):
                        get_today_sessions.clear() if hasattr(get_today_sessions, 'clear') else None
                        st.toast(f"✅ {session} → {perf}")
                        st.rerun()

    st.markdown("&nbsp;")

# ── Today's summary ───────────────────────────────────────────────────────────
if today_tracked:
    st.divider()
    st.markdown(f"##### 📋 Today's Recorded — {student}")
    summary_items = sorted(today_tracked.items(), key=lambda x: (x[0][1]))
    cols = st.columns(max(len(summary_items), 1))
    for i, ((gid, sess), perf) in enumerate(summary_items):
        p_icon, p_bg = PERF_STYLE.get(perf, ("", TEAL))
        # Find goal number
        g_num = next((j+1 for j, g in enumerate(active_goals) if g["id"] == gid), "?")
        cols[i].markdown(
            f"**Goal {g_num} · {sess}**  \n"
            f"<span style='background:{p_bg};color:white;padding:2px 10px;"
            f"border-radius:10px;font-size:12px'>{p_icon} {perf}</span>",
            unsafe_allow_html=True,
        )

st.divider()
st.caption(
    f"Tracking for **{student}** · {today_fmt}  \n"
    "Data saves instantly. View reports in **SMARTAR Goal Builder → Progress Report**."
)
