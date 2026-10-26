"""
SGoal Quick Track — fast daily SMARTAR goal tracking for CLC LBU staff.
Page 26. Sessions filtered by each goal's tracking period.
"""

import streamlit as st
from datetime import date, datetime
from zoneinfo import ZoneInfo
from supabase import create_client

st.set_page_config(page_title="SGoal Quick Track", page_icon="⚡", layout="wide")

TEAL  = "#1A7A6E"
AMBER = "#C8760A"

# The portal's host (Render) runs its server clock in UTC, not Adelaide time.
# Using date.today() there rolls the "day" over at UTC midnight, which is
# ~10:30am in Adelaide during daylight saving (10am standard time) — so staff
# opening the page first thing in the morning were still being shown
# "yesterday", and the morning session (and its tracking counts) wouldn't
# appear until the UTC date caught up. Anchoring to Australia/Adelaide makes
# the rollover happen at actual local midnight regardless of server timezone.
ADELAIDE_TZ = ZoneInfo("Australia/Adelaide")

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
import time as _time

def _make_sb():
    url = (st.secrets.get("supabase", {}).get("url")
           or st.secrets.get("BEHAVIOUR_SUPABASE_URL"))
    key = (st.secrets.get("supabase", {}).get("key")
           or st.secrets.get("BEHAVIOUR_SUPABASE_KEY"))
    if not url or not key:
        st.error("⚠️ Supabase credentials not found.")
        st.stop()
    return create_client(url, key)

# Fresh client every page load — prevents stale connections on Render free tier
sb = _make_sb()

def _q(fn, retries=3):
    """Run a DB query with automatic retry + fresh client on failure."""
    global sb
    for attempt in range(retries):
        try:
            return fn(sb)
        except Exception as e:
            if attempt < retries - 1:
                _time.sleep(0.5 * (attempt + 1))
                sb = _make_sb()
            else:
                raise e

# ── Data helpers ──────────────────────────────────────────────────────────────


def get_all_students():
    """Load students with retry — no cache so stale data never blocks."""
    def _fn(c):
        return (c.table("smartar_students")
                .select("student_name, program")
                .eq("active", True)
                .order("student_name")
                .execute().data or [])
    try:
        return _q(_fn)
    except Exception as e:
        st.error(f"Error loading students: {e}")
        return []


@st.cache_data(ttl=30, show_spinner=False)
def get_active_goals(student_name: str):
    """Load active goals — cached per student, short TTL."""
    def _fn(c):
        return (c.table("smartar_goals")
                .select("id, smartar_goal, tracking_period")
                .eq("student_name", student_name)
                .eq("active", True)
                .order("created_at")
                .execute().data or [])
    try:
        result = _q(_fn)
        # Don't cache empty results — force retry next run
        if not result:
            get_active_goals.clear()
        return result
    except Exception as e:
        st.error(f"Error loading goals: {e}")
        return []


@st.cache_data(ttl=15, show_spinner=False)
def get_today_sessions(student_name: str, today_str: str):
    """Kept for compatibility — session counts now via get_session_counts."""
    return {}


@st.cache_data(ttl=8, show_spinner=False)
def get_session_counts(goal_id, today_str: str) -> dict:
    """Returns {session_time: {performance_level: count}} for today — with retry."""
    def _fn(c):
        return (c.table("smartar_tracking")
                .select("session_time, performance_level")
                .eq("goal_id", goal_id)
                .eq("session_date", today_str)
                .execute().data or [])
    try:
        rows = _q(_fn)
        counts = {}
        for r in rows:
            s = r["session_time"]
            p = r["performance_level"]
            counts.setdefault(s, {})
            counts[s][p] = counts[s].get(p, 0) + 1
        return counts
    except Exception:
        return {}


def save_session(goal_id, student_name: str, session_time: str,
                 performance_level: str, today_str: str) -> bool:
    """Always INSERT — allows multiple observations per session."""
    payload = {
        "goal_id":           goal_id,
        "student_name":      student_name,
        "session_date":      today_str,
        "session_time":      session_time,
        "performance_level": performance_level,
    }
    try:
        _q(lambda c: c.table("smartar_tracking").insert(payload).execute())
        get_session_counts.clear()   # invalidate count cache immediately
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

# Anchor "today" to Adelaide local time (not the server's own timezone) so the
# day rolls over at local midnight — see ADELAIDE_TZ note above.
today     = datetime.now(ADELAIDE_TZ).date()
today_str = today.isoformat()
today_fmt = today.strftime("%A, %d %B %Y")

# ── Date-change detection ─────────────────────────────────────────────────────
# If the app has been open since yesterday, wipe all caches so tracking counts
# and student lists reflect the correct day immediately.
if st.session_state.get("_qt_last_date") != today_str:
    st.session_state["_qt_last_date"] = today_str
    get_active_goals.clear()
    get_session_counts.clear()
    st.rerun()

_banner_col, _refresh_col = st.columns([5, 1])
with _banner_col:
    st.markdown(f'<div class="today-banner">📅 {today_fmt}</div>', unsafe_allow_html=True)
with _refresh_col:
    if st.button("🔄 Refresh", key="qt_refresh_btn", use_container_width=True):
        get_active_goals.clear()
        get_session_counts.clear()
        st.rerun()

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

    # Get per-level counts for this goal today
    sess_counts = get_session_counts(goal_id, today_str)
    sess_cols   = st.columns(len(sessions))

    for s_idx, session in enumerate(sessions):
        lvl_counts = sess_counts.get(session, {})
        total_obs  = sum(lvl_counts.values())
        icon       = SESSION_ICONS.get(session, "🕐")

        with sess_cols[s_idx]:
            obs_badge = f" · <small>{total_obs} obs</small>" if total_obs else ""
            st.markdown(
                f'<div class="sess-label">{icon} {session}{obs_badge}</div>',
                unsafe_allow_html=True,
            )
            for perf in PERF_LEVELS:
                p_icon, p_bg = PERF_STYLE[perf]
                n       = lvl_counts.get(perf, 0)
                count_s = f" ×{n}" if n > 0 else ""
                label   = f"{p_icon} {perf}{count_s}"
                btn_key = f"qt_{student}_{g_idx}_{session}_{perf}"
                if st.button(label, key=btn_key, use_container_width=True,
                             type="primary" if n > 0 else "secondary"):
                    if save_session(goal_id, student, session, perf, today_str):
                        st.toast(f"✅ {session} → {perf}")
                        st.rerun()

    st.markdown("&nbsp;")

# ── Today's summary ───────────────────────────────────────────────────────────
# Build summary from get_session_counts across all goals
any_today = False
summary_rows = []
for goal in active_goals:
    sc = get_session_counts(goal["id"], today_str)
    for sess, lvl_d in sc.items():
        for perf, n in lvl_d.items():
            summary_rows.append((goal, sess, perf, n))
            any_today = True

if any_today:
    st.divider()
    st.markdown(f"##### 📋 Today's Observations — {student}")
    for goal, sess, perf, n in summary_rows:
        g_num  = next((j+1 for j, g in enumerate(active_goals) if g["id"] == goal["id"]), "?")
        p_icon, p_bg = PERF_STYLE.get(perf, ("", TEAL))
        st.markdown(
            f"**Goal {g_num} · {sess}** — "
            f"<span style='background:{p_bg};color:white;padding:2px 10px;"
            f"border-radius:10px;font-size:12px'>{p_icon} {perf} ×{n}</span>",
            unsafe_allow_html=True,
        )

st.divider()
st.caption(
    f"Tracking for **{student}** · {today_fmt}  \n"
    "Data saves instantly. View reports in **SMARTAR Goal Builder → Progress Report**."
)
