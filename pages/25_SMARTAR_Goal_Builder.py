import streamlit as st

# ── Document Archive integration (fails silently if unavailable) ──────────
try:
    from archive_utils import archive_once, archive_document, initials_from_name
except Exception:
    def archive_once(*_a, **_k):
        pass
    def archive_document(**_k):
        return None
    def initials_from_name(name):
        parts = [p for p in str(name or "").replace("_", " ").split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or None

import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
from io import BytesIO
from supabase import create_client
from urllib.parse import unquote, quote
from collections import defaultdict

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="SMARTAR Goal Builder", page_icon="🎯", layout="wide")

# ── Team Meetings Integration ─────────────────────────────────────────────────
def check_team_meetings_integration():
    params = st.query_params
    student_param   = params.get("student", None)
    meeting_id_param = params.get("meeting_id", None)
    program_param   = params.get("program", None)
    term_param      = params.get("term", None)
    week_param      = params.get("week", None)
    return_to       = params.get("return_to", None)
    def _safe_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    return {
        "active":     return_to == "team_meetings",
        "student":    unquote(student_param) if student_param else None,
        # meeting_id may be an integer OR a UUID string — never force int() or the
        # whole page crashes to a white screen on load.
        "meeting_id": meeting_id_param if meeting_id_param else None,
        "program":    program_param,
        "term":       term_param,
        "week":       _safe_int(week_param),
    }

integration = check_team_meetings_integration()

def team_meeting_return_url(integ):
    """Build a reliable URL back to the Team Meetings page, carrying the program
    and the originating meeting id so the meeting re-opens on arrival."""
    prog = integ.get("program") or "JP"
    url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={quote(str(prog))}"
    if integ.get("meeting_id"):
        url += f"&open_meeting={quote(str(integ['meeting_id']))}"
    return url


# ── Clients ───────────────────────────────────────────────────────────────────
def _get_sb_creds():
    url = (st.secrets.get("supabase", {}).get("url")
           or st.secrets.get("BEHAVIOUR_SUPABASE_URL"))
    key = (st.secrets.get("supabase", {}).get("key")
           or st.secrets.get("BEHAVIOUR_SUPABASE_KEY"))
    return url, key

def _make_sb():
    url, key = _get_sb_creds()
    if not url or not key:
        st.error("⚠️ Supabase credentials not found.")
        st.stop()
    return create_client(url, key)

# Fresh client on every page load — prevents stale connections on Render free tier
sb = _make_sb()

# ══════════════════════════════════════════════════════════════════════════
# RESILIENT GROQ AI HELPER — portal-wide standard (Aug 2026)
#
# Fixes the recurring portal-wide Groq issue, which has three stacked causes:
#   1) A stale groq/httpx combo can raise
#      "Client.__init__() got an unexpected keyword argument 'proxies'" on
#      client creation — worked around by retrying with an explicit http_client.
#   2) Groq retired "llama-3.3-70b-versatile" for free/dev-tier accounts
#      (16 Aug 2026), so any call hardcoded to that model can start failing
#      with a model-not-found/decommissioned error — worked around by trying
#      a small chain of current models instead of one hardcoded name.
#   3) qwen/qwen3.6-27b is a hybrid-thinking model — left to its defaults it
#      spends the whole max_tokens budget on a <think> chain-of-thought block
#      before ever writing the actual answer, which shows up as "Extra data"/
#      JSON-parse errors or empty/truncated replies. Fixed by scoping
#      reasoning_effort="none" to that model only — gpt-oss and llama don't
#      accept that parameter, so it must NOT be sent to them.
# It also self-heals 413 "request too large" errors by halving max_tokens
# and retrying, instead of failing outright.
#
# Use groq_ai_call(prompt, ...) anywhere in a tool instead of building a
# Groq client or calling chat.completions.create directly.
# ══════════════════════════════════════════════════════════════════════════
_GROQ_MODEL_CHAIN = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]
def _get_groq_client(api_key):
    from groq import Groq
    try:
        return Groq(api_key=api_key)
    except TypeError:
        import httpx
        return Groq(api_key=api_key, http_client=httpx.Client())
def groq_ai_call(prompt, max_tokens=1500, temperature=0.1, api_key=None, system=None):
    """Resilient Groq chat-completion call. Returns the response text (str).
    Raises the last error encountered if every model/retry combination fails
    — wrap the call in try/except at the call site if you want a graceful
    fallback instead of Streamlit's default traceback."""
    api_key = api_key or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("Groq API key not configured.")
    client = _get_groq_client(api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    last_err = None
    for model in _GROQ_MODEL_CHAIN:
        tokens = max_tokens
        for _attempt in range(2):  # original size, then one halved retry
            try:
                kwargs = dict(model=model, messages=messages, max_tokens=tokens, temperature=temperature)
                if model == "qwen/qwen3.6-27b":
                    kwargs["reasoning_effort"] = "none"
                resp = client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if "413" in msg or "too large" in msg:
                    tokens = max(256, tokens // 2)
                    continue  # retry same model with a smaller token budget
                break  # any other error: move on to the next model in the chain
    raise last_err

GROQ_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
# groq_client is kept as a plain availability flag — every actual call now
# goes through groq_ai_call(), which builds its own resilient client per call.
groq_client = bool(GROQ_KEY)

import time as _time

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

# ── Constants ─────────────────────────────────────────────────────────────────
LEVEL_ORDER  = ["EXCEEDING", "ABOVE", "EXPECTED", "BELOW", "NOT YET"]
TRACK_LEVELS = ["EXCEEDING", "ABOVE", "EXPECTED", "NOT YET"]   # BELOW not tracked daily
LEVEL_EMOJI  = {"EXCEEDING": "🌟", "ABOVE": "✅", "EXPECTED": "🎯", "BELOW": "⚠️", "NOT YET": "❌"}
LEVEL_COLOR  = {
    "EXCEEDING": "#1a7a3c", "ABOVE": "#2d8a5e",
    "EXPECTED":  "#1d6fa4", "BELOW": "#d97706", "NOT YET": "#c0392b",
}
MPL_COLOR = {
    "EXCEEDING": "#27ae60", "ABOVE": "#2ecc71",
    "EXPECTED":  "#2980b9", "BELOW": "#e67e22",  "NOT YET": "#c0392b",
}

# Hierarchy of prompts (PBS/ABA framework)
GROUPINGS    = ["Independently", "One to one", "Small group", "Large group",
                "Unstructured", "With a peer"]
TASK_TYPES   = ["Structured task", "Hands-on activity", "Using equipment",
                "Paper/pencil task", "Oral/listening activity", "Following a routine",
                "Computer-based task", "Other"]
SETTINGS     = ["Classroom", "During a maths lesson", "During a literacy lesson",
                "During morning block", "During afternoon block", "During transitions",
                "At recess", "At lunch", "On excursion", "During negotiated school time"]
PROMPT_TYPES = ["No prompts", "Visual prompt", "Verbal prompt", "Gestural prompt",
                "Model prompt", "Partial physical support", "Full physical support",
                "SSO support", "Verbal and gestural prompts", "Verbal and visual prompts"]
RATE_OPTIONS = [
    "3 out of 5 opportunities",
    "4 out of 5 opportunities",
    "3 out of 5 days over 3 weeks",
    "4 out of 5 days over 3 weeks",
    "80% of the time over a 3-week period",
    "on 3 consecutive occasions",
    "consistently over 2 weeks",
]

TRACKING_PERIODS = [
    "All Day", "Morning Only", "Middle Only", "Afternoon Only",
    "Morning & Middle", "Middle & Afternoon",
]
SESSIONS_FOR_PERIOD = {
    "All Day":            ["Morning", "Middle", "Afternoon"],
    "Morning Only":       ["Morning"],
    "Middle Only":        ["Middle"],
    "Afternoon Only":     ["Afternoon"],
    "Morning & Middle":   ["Morning", "Middle"],
    "Middle & Afternoon": ["Middle", "Afternoon"],
}
ALL_SESSIONS = ["Morning", "Middle", "Afternoon"]

PROGRAMS = ["JP", "PY", "SY"]

# ── AI helpers ────────────────────────────────────────────────────────────────
def groq_call(prompt,
              system="You are an expert educator supporting students in alternative "
                     "education settings. Be concise and practical."):
    if not GROQ_KEY:
        return "[AI unavailable — Groq API key not configured]"
    try:
        return groq_ai_call(prompt, max_tokens=800, api_key=GROQ_KEY, system=system)
    except Exception as e:
        return f"[AI unavailable: {e}]"


def ai_check_period(smartar_goal: str) -> dict:
    """Ask Groq to determine appropriate tracking period for a goal."""
    if not GROQ_KEY:
        return {"period": "All Day", "reasoning": "AI unavailable.", "confidence": "Low"}
    prompt = f"""You are an educational support specialist for students in alternative education.

Analyse this SMARTAR goal and determine the most appropriate tracking period within the school day.

Goal: {smartar_goal}

School sessions:
- Morning (~9am–11am): literacy, numeracy, structured academic learning
- Middle (~11am–1pm): recess, lunch, social time, transitions
- Afternoon (~1pm–3pm): specialist subjects, projects, outdoor education

Return ONLY valid JSON, nothing else — no markdown fences, no preamble:
{{
  "period": "All Day" | "Morning Only" | "Middle Only" | "Afternoon Only" | "Morning & Middle" | "Middle & Afternoon",
  "reasoning": "One concise sentence explaining why",
  "confidence": "High" | "Medium" | "Low"
}}

Use "All Day" unless the goal text CLEARLY references a specific time context (e.g., 'morning literacy', 'at lunch', 'during afternoon session')."""
    try:
        raw = groq_ai_call(prompt, max_tokens=200, temperature=0.1, api_key=GROQ_KEY)
        raw = raw.replace("```json", "").replace("```", "").strip()
        if not raw.startswith("{"):
            start = raw.find("{")
            if start != -1:
                raw = raw[start:]
        result = json.loads(raw)
        if result.get("period") not in TRACKING_PERIODS:
            result["period"] = "All Day"
        return result
    except Exception:
        return {"period": "All Day", "reasoning": "AI check unavailable.", "confidence": "Low"}


# ── Supabase helpers ───────────────────────────────────────────────────────────
def get_students(include_archived=False):
    """By default returns only students who are on placement right now —
    excludes both goal-archived students and students whose placement has
    ended, so they drop off every student picker/report once marked done.
    The placement_ended check is done in Python (not as a DB .eq filter) so
    older rows that predate that column (NULL rather than False) aren't
    accidentally hidden."""
    def _fn(c):
        q = c.table("smartar_students").select("*").order("student_name")
        if not include_archived:
            q = q.eq("active", True)
        return q.execute().data or []
    try:
        result = _q(_fn)
        if not include_archived:
            result = [s for s in result if not s.get("placement_ended")]
        return result
    except Exception as e:
        st.error(f"DB error loading students: {e}")
        return []


def get_goals(student_name=None, active_only=True):
    def _fn(c):
        q = c.table("smartar_goals").select("*")
        if student_name:
            q = q.eq("student_name", student_name)
        if active_only:
            q = q.eq("active", True)
        return q.order("created_at", desc=False).execute().data or []
    try:
        return _q(_fn)
    except Exception as e:
        st.error(f"DB error loading goals: {e}")
        return []


def get_all_goals_for_student(student_name: str):
    """Returns active + archived goals for a student, newest first."""
    def _fn(c):
        return (
            c.table("smartar_goals").select("*")
            .eq("student_name", student_name)
            .order("created_at", desc=True)
            .execute().data or []
        )
    try:
        return _q(_fn)
    except Exception:
        return []


def get_tracking(goal_id, days=30):
    since = (date.today() - timedelta(days=days)).isoformat()
    try:
        return (
            sb.table("smartar_tracking").select("*")
            .eq("goal_id", goal_id)
            .gte("session_date", since)
            .order("session_date")
            .execute().data or []
        )
    except Exception:
        return []


def get_tracking_range(goal_id, from_date: str, to_date: str, sessions=None):
    """Get tracking for a goal within an explicit date range."""
    try:
        rows = (
            sb.table("smartar_tracking").select("*")
            .eq("goal_id", goal_id)
            .gte("session_date", from_date)
            .lte("session_date", to_date)
            .order("session_date")
            .execute().data or []
        )
        if sessions:
            rows = [r for r in rows if r.get("session_time") in sessions]
        return rows
    except Exception:
        return []


def get_today_tracking(goal_id):
    try:
        return (
            sb.table("smartar_tracking").select("*")
            .eq("goal_id", goal_id)
            .eq("session_date", date.today().isoformat())
            .execute().data or []
        )
    except Exception:
        return []


def get_recent_tracking(goal_id, sessions=5):
    try:
        return (
            sb.table("smartar_tracking").select("*")
            .eq("goal_id", goal_id)
            .order("session_date", desc=True)
            .order("recorded_at", desc=True)
            .limit(sessions)
            .execute().data or []
        )
    except Exception:
        return []


def upsert_session(goal_id, student_name, session_time, performance_level,
                   track_date=None):
    """Always INSERT new observation — allows multiple per session per day."""
    record_date = track_date or date.today().isoformat()
    try:
        sb.table("smartar_tracking").insert({
            "goal_id":           goal_id,
            "student_name":      student_name,
            "session_date":      record_date,
            "session_time":      session_time,
            "performance_level": performance_level,
        }).execute()
    except Exception as e:
        st.error(f"Save error: {e}")


def get_session_counts(goal_id, track_date):
    """Returns {session_time: {performance_level: count}} for given date."""
    try:
        rows = (
            sb.table("smartar_tracking").select("session_time, performance_level")
            .eq("goal_id", goal_id)
            .eq("session_date", track_date)
            .execute().data or []
        )
        counts = {}
        for r in rows:
            s = r["session_time"]
            p = r["performance_level"]
            counts.setdefault(s, {})
            counts[s][p] = counts[s].get(p, 0) + 1
        return counts
    except Exception:
        return {}


def get_tracking_entries(goal_id, track_date):
    """Full tracking rows (including id) for one goal on one date — powers the
    delete-a-mistaken-observation UI in Daily Tracking."""
    try:
        return (
            sb.table("smartar_tracking").select("id, session_time, performance_level, recorded_at")
            .eq("goal_id", goal_id)
            .eq("session_date", track_date)
            .order("recorded_at")
            .execute().data or []
        )
    except Exception:
        return []


def delete_tracking_entry(tracking_id) -> bool:
    try:
        sb.table("smartar_tracking").delete().eq("id", tracking_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete error: {e}")
        return False


def archive_goal(goal_id, reason: str = ""):
    try:
        sb.table("smartar_goals").update({
            "active":         False,
            "status":         "Archived",
            "archived_at":    datetime.utcnow().isoformat(),
            "archive_reason": reason,
            "updated_at":     datetime.utcnow().isoformat(),
        }).eq("id", goal_id).execute()
        return True
    except Exception as e:
        st.error(f"Archive error: {e}")
        return False


def restore_goal(goal_id):
    try:
        sb.table("smartar_goals").update({
            "active":         True,
            "status":         "Active",
            "archived_at":    None,
            "archive_reason": None,
            "updated_at":     datetime.utcnow().isoformat(),
        }).eq("id", goal_id).execute()
        return True
    except Exception:
        return False


def goal_date_range(goal: dict):
    start = goal.get("start_date") or (goal.get("created_at") or "")[:10] or date.today().isoformat()
    if not goal.get("active", True) and goal.get("archived_at"):
        end = goal["archived_at"][:10]
    else:
        end = date.today().isoformat()
    return str(start)[:10], end


def calc_percentages(tracking_data):
    counts = {l: 0 for l in LEVEL_ORDER}
    for row in tracking_data:
        lvl = row.get("performance_level")
        if lvl in counts:
            counts[lvl] += 1
    total = sum(counts.values())
    pcts  = {l: round(counts[l] / total * 100, 1) for l in LEVEL_ORDER} if total else {}
    return counts, total, pcts


def get_gas_dict(goal):
    return {
        "EXCEEDING": goal.get("gas_exceeding", ""),
        "ABOVE":     goal.get("gas_above",     ""),
        "EXPECTED":  goal.get("gas_expected",  ""),
        "BELOW":     goal.get("gas_below",     ""),
        "NOT YET":   goal.get("gas_not_yet",   ""),
    }


def check_goal_needs_refinement(goal_id, threshold=3):
    recent = get_recent_tracking(goal_id, sessions=5)
    if len(recent) < threshold:
        return False, 0
    low = sum(1 for r in recent if r.get("performance_level") == "NOT YET")
    return low >= threshold, low


# ── Consecutive-day streak detector → "consider revising this goal" nudges ────
STREAK_POSITIVE_LEVELS = {"EXCEEDING", "ABOVE"}
STREAK_NEGATIVE_LEVELS = {"BELOW", "NOT YET"}


@st.cache_data(ttl=60, show_spinner=False)
def check_goal_streak(goal_id, days=5):
    """Looks at the most recent `days` DISTINCT school days that have at least
    one tracking entry for this goal (pulled from tracking rows directly, so a
    day isn't counted twice for multiple sessions). Cached briefly since it's
    now called twice per visible goal on Program Snapshot (once for the
    top-of-page summary tiles, once again in the per-program detail panel).

    Returns (streak_type, day_count):
      - ("positive", days) if every entry on each of those days is
        EXCEEDING/ABOVE — the student may be ready for a harder goal.
      - ("negative", days) if every entry on each of those days is
        BELOW/NOT YET — the goal may need easing.
      - (None, 0) if there aren't yet `days` distinct tracked days, or the
        days are mixed.
    """
    rows = get_tracking(goal_id, days=45)
    if not rows:
        return None, 0
    by_day = defaultdict(set)
    for r in rows:
        by_day[str(r.get("session_date", ""))[:10]].add(r.get("performance_level"))
    recent_days = sorted(by_day.keys(), reverse=True)[:days]
    if len(recent_days) < days:
        return None, 0
    if all(by_day[d] and by_day[d] <= STREAK_POSITIVE_LEVELS for d in recent_days):
        return "positive", days
    if all(by_day[d] and by_day[d] <= STREAK_NEGATIVE_LEVELS for d in recent_days):
        return "negative", days
    return None, 0


def render_streak_alert(streak_type: str, days: int = 5) -> str:
    if streak_type == "positive":
        return (
            f'<div class="success-box">🚀 <b>{days} consecutive days of EXCEEDING/ABOVE.</b> '
            f'This student may be ready for a more challenging goal — consider revising it upward.</div>'
        )
    return (
        f'<div class="alert-box">📉 <b>{days} consecutive days of BELOW/NOT YET.</b> '
        f'This goal may be too difficult right now — consider revising it to better support this student.</div>'
    )


def jump_to_edit_goal(student_name: str, goal_id):
    """Navigates to Goal Builder, selects the given student, and flags that
    goal's edit form to auto-open and auto-expand — used by the streak nudges
    (and anywhere else) so staff can act on an alert in one click instead of
    hunting for the right student/goal themselves."""
    st.session_state["nav_view"] = "📋 Goal Builder"
    st.session_state["gb_student_select"] = student_name
    st.session_state[f"editgoal_open_{goal_id}"] = True
    st.rerun()


def analyze_trend(tracking_data):
    if len(tracking_data) < 4:
        return "insufficient_data"
    score_map = {"EXCEEDING": 5, "ABOVE": 4, "EXPECTED": 3, "BELOW": 2, "NOT YET": 1}
    mid = len(tracking_data) // 2
    first_avg = sum(score_map.get(r.get("performance_level",""), 0) for r in tracking_data[:mid]) / mid
    second_avg = sum(score_map.get(r.get("performance_level",""), 0) for r in tracking_data[mid:]) / (len(tracking_data)-mid)
    diff = second_avg - first_avg
    if diff > 0.5:   return "improving"
    if diff < -0.5:  return "declining"
    return "stable"


def _short(text: str, n: int = 65) -> str:
    return text[:n] + "…" if len(text) > n else text


# ── Tracking-frequency helpers (powers Program Snapshot) ───────────────────────
def count_school_days(start: date, end: date) -> int:
    """Weekdays (Mon–Fri) from start to end, inclusive. 0 if start > end."""
    if start > end:
        return 0
    total_days = (end - start).days + 1
    full_weeks, extra = divmod(total_days, 7)
    count = full_weeks * 5
    for i in range(extra):
        d = start + timedelta(days=full_weeks * 7 + i)
        if d.weekday() < 5:
            count += 1
    return count


def most_recent_school_day(ref: date) -> date:
    """ref, or the Friday before it if ref falls on a weekend."""
    d = ref
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d -= timedelta(days=1)
    return d


def school_days_since(last_entry: date, as_of: date) -> int:
    """School days strictly after last_entry, up to and including as_of."""
    if last_entry >= as_of:
        return 0
    return count_school_days(last_entry + timedelta(days=1), as_of)


def count_expected_days(start: date, end: date, excused: set | None = None) -> int:
    """Weekdays (Mon–Fri) from start to end inclusive, minus any date in
    `excused` (ISO date strings) — attendance-aware sibling of
    count_school_days(). With no excused dates it behaves identically."""
    if start > end:
        return 0
    excused = excused or set()
    n, d = 0, start
    while d <= end:
        if d.weekday() < 5 and d.isoformat() not in excused:
            n += 1
        d += timedelta(days=1)
    return n


def expected_days_since(last_entry: date, as_of: date, excused: set | None = None) -> int:
    """Expected school days strictly after last_entry, up to and including
    as_of, excluding any date in `excused` — attendance-aware sibling of
    school_days_since()."""
    if last_entry >= as_of:
        return 0
    return count_expected_days(last_entry + timedelta(days=1), as_of, excused)


def goal_tracking_frequency(goal_id, goal_start, recent_window_days: int = 14,
                            excused_dates: set | None = None) -> dict:
    """
    How consistently a goal is being tracked, assuming an entry is expected
    every school day (Mon–Fri) the student was actually at school.

    excused_dates: ISO date strings (from the Behaviour Support Tool's
    attendance record — full-day Absent or No School) that are dropped from
    the expected-days count entirely, so a day the student genuinely couldn't
    have been tracked never counts against them. Empty/None = old behaviour.

    Returns:
        status: "not_started" | "needs_increase" | "on_track"
        last_entry: date of the most recent observation, or None
        consistency_pct: % of expected school days (last `recent_window_days`
            calendar days, or since the goal started if more recent) that
            have at least one observation
        days_behind: expected school days elapsed since the last observation,
            measured against the last COMPLETED school day (so today isn't
            flagged before the day is even over)
        expected_days / actual_days: the raw counts behind consistency_pct
        excused_in_window: how many of the window's weekdays were excused
            (absence / no school) — 0 if attendance wasn't available/matched
    """
    today = date.today()
    excused_dates = excused_dates or set()
    try:
        start_d = date.fromisoformat(str(goal_start)[:10]) if goal_start else today
    except Exception:
        start_d = today

    all_rows = get_tracking_range(goal_id, start_d.isoformat(), today.isoformat())
    if not all_rows:
        return {
            "status": "not_started", "last_entry": None, "consistency_pct": 0,
            "expected_days": count_expected_days(start_d, today, excused_dates), "actual_days": 0,
            "days_behind": None, "excused_in_window": 0,
        }

    tracked_dates = sorted({r["session_date"] for r in all_rows})
    last_entry = date.fromisoformat(tracked_dates[-1][:10])

    window_from      = max(start_d, today - timedelta(days=recent_window_days))
    recent_tracked   = {d for d in tracked_dates if d >= window_from.isoformat()}
    expected_days    = count_expected_days(window_from, today, excused_dates) or 1
    actual_days      = len(recent_tracked)
    consistency_pct  = min(round(actual_days / expected_days * 100), 100)
    excused_in_window = count_school_days(window_from, today) - count_expected_days(window_from, today, excused_dates)

    last_completed_school_day = most_recent_school_day(today - timedelta(days=1))
    days_behind = expected_days_since(last_entry, last_completed_school_day, excused_dates)

    status = "needs_increase" if (days_behind >= 1 or consistency_pct < 60) else "on_track"

    return {
        "status": status, "last_entry": last_entry, "consistency_pct": consistency_pct,
        "expected_days": expected_days, "actual_days": actual_days, "days_behind": days_behind,
        "excused_in_window": excused_in_window,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS (generic key/value) — powers the teacher-email-per-program mapping
# and the daily alert dedupe log. Needs a `smartar_settings` table:
#   create table smartar_settings (key text primary key, value text);
# Every call fails soft (returns default / False) if the table doesn't exist
# yet, so the rest of the app keeps working even before it's created.
# ══════════════════════════════════════════════════════════════════════════════
SMARTAR_SETTINGS_SQL = (
    "create table if not exists smartar_settings (\n"
    "    key   text primary key,\n"
    "    value text\n"
    ");"
)


def get_setting(key: str, default=None):
    try:
        r = sb.table("smartar_settings").select("value").eq("key", key).execute().data
        if r:
            return r[0]["value"]
    except Exception:
        pass
    return default


def set_setting(key: str, value: str) -> bool:
    try:
        sb.table("smartar_settings").upsert({"key": key, "value": value}).execute()
        return True
    except Exception as e:
        st.error(f"Couldn't save setting — has the `smartar_settings` table been created? ({e})")
        return False


def get_teacher_emails() -> dict:
    """{"JP": "teacher@school...", "PY": "...", "SY": "..."}"""
    raw = get_setting("teacher_emails", "{}")
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return {}


def set_teacher_emails(mapping: dict) -> bool:
    return set_setting("teacher_emails", json.dumps(mapping))


def _get_alert_log() -> dict:
    raw = get_setting("teacher_alert_log", "{}")
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# OUTBOUND EMAIL — same route as the Hazard Report / Credit Card tools: a
# Google Apps Script webhook on the CLC Gmail account (works on Render's free
# plan, which blocks outbound SMTP ports), falling back to direct Gmail SMTP
# if no webhook is configured. Uses the SAME secret names those tools use, so
# if email already works there, it works here with nothing extra to set up.
# ══════════════════════════════════════════════════════════════════════════════
def _secret(*paths, default=None):
    """Return the first secret found. Each path is 'KEY' or 'section.key'.
    Checks Render/host environment variables first, then Streamlit secrets —
    identical lookup order to hazard_utils._secret()."""
    for p in paths:
        if "." not in p and os.environ.get(p):
            return os.environ[p]
    for p in paths:
        try:
            node = st.secrets
            for part in p.split("."):
                node = node[part]
            if node:
                return node
        except Exception:
            continue
    return default


def _smtp_settings():
    user = _secret("GMAIL_USER", "SMTP_USER", "EMAIL_USER", "EMAIL_SENDER", "gmail.user",
                   "gmail.address", "smtp.user", "smtp.username", "email.user", "email.sender",
                   default="clc.digitalstaffmeeting@gmail.com")
    pwd = _secret("GMAIL_APP_PASSWORD", "GMAIL_PASSWORD", "SMTP_PASSWORD", "EMAIL_PASSWORD",
                 "gmail.app_password", "gmail.password", "smtp.password", "email.password")
    host = _secret("SMTP_HOST", "smtp.host", "smtp.server", default="smtp.gmail.com")
    port = int(_secret("SMTP_PORT", "smtp.port", default=587))
    return user, pwd, host, port


def email_is_configured() -> bool:
    _user, pwd, _host, _port = _smtp_settings()
    webhook = _secret("EMAIL_WEBHOOK_URL", "email.webhook_url", "gmail.webhook_url")
    return bool(webhook or pwd)


def _send_via_webhook(url: str, token: str, recipients: list, subject: str, html: str):
    """Send through the Google Apps Script web app on the CLC Gmail account
    (plain HTTPS, so it works on Render's free plan) — identical request
    shape to hazard_utils._send_via_webhook()."""
    import json
    import urllib.request
    body = json.dumps({
        "token": token, "to": ",".join(recipients), "subject": subject, "html": html,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        reply = resp.read().decode(errors="ignore").strip()
    if reply.startswith("OK"):
        return True, f"Email sent to {len(recipients)} recipient(s)."
    return False, f"Email failed: Apps Script replied '{reply[:150]}'"


def _send_via_smtp(user, pwd, host, port, recipients, msg):
    """Try the configured port first, then the other Gmail port (587 STARTTLS
    / 465 SSL) — identical fallback order to hazard_utils._send_via_smtp()."""
    import smtplib
    errors = []
    for p in dict.fromkeys([port, 587, 465]):
        try:
            if p == 465:
                with smtplib.SMTP_SSL(host, 465, timeout=20) as s:
                    s.login(user, pwd)
                    s.sendmail(user, recipients, msg.as_string())
            else:
                with smtplib.SMTP(host, p, timeout=20) as s:
                    s.starttls()
                    s.login(user, pwd)
                    s.sendmail(user, recipients, msg.as_string())
            return
        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(f"Gmail rejected the login ({e.smtp_code}) – check the app password") from e
        except Exception as e:
            errors.append(f"port {p}: {e or type(e).__name__}")
    raise RuntimeError("; ".join(errors) + ". If this keeps happening, set up EMAIL_WEBHOOK_URL "
                                           "(same as the Hazard Report tool).")


def smartar_portal_url() -> str | None:
    base = _secret("PORTAL_URL", "portal.url", default="https://clc-lbu-portal.onrender.com")
    return f"{base.rstrip('/')}/SMARTAR_Goal_Builder" if base else None


def send_teacher_alert_email(student_name: str, program: str, days_silent: int, to_addr: str):
    """Returns (ok, msg). Recipient comes from the teacher-email-per-program
    mapping Candice fills in on the Admin Panel's Teacher Alerts tab — unlike
    the Hazard Report's fixed Admin/Leadership recipient list, here SHE sets
    who gets alerted for each program. The send mechanism itself (webhook
    first, SMTP fallback) is identical to send_hazard_email(). `to_addr` may
    hold more than one address (comma- or semicolon-separated) — each
    program's box accepts a list, same as the Hazard Report recipients."""
    import re
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from html import escape

    recipients = [e.strip() for e in re.split(r"[,;]", to_addr or "") if e.strip()]
    if not recipients:
        return False, "No teacher email set for this program."
    user, pwd, host, port = _smtp_settings()
    webhook = _secret("EMAIL_WEBHOOK_URL", "email.webhook_url", "gmail.webhook_url")
    webhook_token = _secret("EMAIL_WEBHOOK_TOKEN", "email.webhook_token", "gmail.webhook_token", default="")
    if not pwd and not webhook:
        return False, ("Email isn't set up for the portal yet — this needs the same "
                       "EMAIL_WEBHOOK_URL (or Gmail app password) the Hazard Report tool uses.")

    subject = f"🔔 SMARTAR tracking reminder: {student_name} — {days_silent} school day(s) with no data"
    portal_url = smartar_portal_url()
    html = f"""
    <div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px'>
      <h2 style='margin:0 0 8px'>SMARTAR Tracking Reminder</h2>
      <p>No SMARTAR tracking has been recorded for <b>{escape(student_name)}</b> ({escape(program)})
      for the last <b>{days_silent}</b> school day(s).</p>
      <p>Please record an observation in the <b>Daily Tracking</b> tab when you're next able to.</p>
      <p style='margin-top:14px;color:#888;font-size:0.85em'>This is an automated reminder from the
      SMARTAR Goal Builder{f" — <a href='{portal_url}'>open the tool</a>" if portal_url else ""}.</p>
    </div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"CLC Portal <{user}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    # 1. Web route (works on Render free plan) if it has been set up
    if webhook:
        try:
            return _send_via_webhook(webhook, webhook_token, recipients, subject, html)
        except Exception as e:
            if not pwd:
                return False, f"Email failed: {e}"
    # 2. Gmail SMTP (needs a host that allows email ports)
    try:
        _send_via_smtp(user, pwd, host, port, recipients, msg)
        return True, f"Email sent to {len(recipients)} recipient(s)."
    except Exception as e:
        return False, f"Email failed: {e}"


def student_school_days_silent(student: dict) -> int | None:
    """Expected school days since this student's most recent tracking entry,
    counting ANY of their active goals (not just one) — used for the 'hasn't
    had data entered for two straight days' teacher reminder. Days the
    student was marked Absent or there was No School (Behaviour Support
    Tool) don't count, same as the Program Snapshot status. Returns None if
    the student has no active goal, or has never had anything tracked yet
    (that case is already covered by the 'Not Started' status elsewhere)."""
    student_name = student["student_name"]
    goals = get_goals(student_name)
    if not goals:
        return None
    goal_ids = [g["id"] for g in goals]
    rows = get_tracking_for_goals(
        goal_ids, (date.today() - timedelta(days=60)).isoformat(), date.today().isoformat()
    )
    if not rows:
        return None
    last_date = max(date.fromisoformat(str(r["session_date"])[:10]) for r in rows)
    last_completed = most_recent_school_day(date.today() - timedelta(days=1))
    excused_dates = get_excused_dates_for_student(student)
    return expected_days_since(last_date, last_completed, excused_dates)


def run_teacher_alert_check(students: list, min_days_silent: int = 2, dry_run: bool = False) -> list:
    """For every active student who has gone >= min_days_silent school days
    without any tracking entry, emails that program's teacher (deduped to
    once per calendar day per student via the settings-backed alert log).
    Returns a list of result rows for display: {student, program,
    days_silent, teacher_email, sent, note}."""
    teacher_emails = get_teacher_emails()
    log = _get_alert_log()
    today_str = date.today().isoformat()
    results = []
    for s in students:
        days_silent = student_school_days_silent(s)
        if days_silent is None or days_silent < min_days_silent:
            continue
        prog = s.get("program", "?")
        teacher_email = teacher_emails.get(prog, "")
        already_today = log.get(s["student_name"]) == today_str
        row = {
            "student": s["student_name"], "program": prog, "days_silent": days_silent,
            "teacher_email": teacher_email, "sent": False, "note": "",
        }
        if not teacher_email:
            row["note"] = f"No teacher email set for {prog} — add one below."
        elif already_today:
            row["note"] = "Already alerted today."
        elif dry_run:
            row["note"] = "Would send now."
        else:
            ok, msg = send_teacher_alert_email(s["student_name"], prog, days_silent, teacher_email)
            row["sent"] = ok
            row["note"] = "✅ Email sent." if ok else f"❌ Send failed: {msg}"
            if ok:
                log[s["student_name"]] = today_str
        results.append(row)
    if not dry_run:
        set_setting("teacher_alert_log", json.dumps(log))
    return results


# ══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE (from the Behaviour Support Tool) — so a day a student was
# marked absent, or there was no school, isn't counted as a missed tracking
# entry. Reads the portal-wide `students` + `student_attendance` tables in
# the same Supabase project this tool already connects to — nothing here is
# written, and if a student can't be confidently matched, their tracking
# status just falls back to the old (attendance-blind) behaviour.
# ══════════════════════════════════════════════════════════════════════════════
ATTENDANCE_EXCUSED_TYPES = {"Absent", "No school"}


@st.cache_data(ttl=300, show_spinner=False)
def _behaviour_student_id_map() -> dict:
    """{(first_name_lower, program): students.id} from the Behaviour Support
    Tool's central `students` table. Only kept when the first name is unique
    within that program — if two active students share a first name in the
    same program, neither is mapped, so attendance is never borrowed from
    the wrong student."""
    try:
        rows = (sb.table("students").select("id, first_name, name, program")
               .eq("archived", False).execute().data or [])
    except Exception:
        return {}
    by_key = defaultdict(list)
    for r in rows:
        fname = (r.get("first_name") or "").strip()
        if not fname and r.get("name"):
            fname = str(r["name"]).split()[0]
        if not fname:
            continue
        key = (fname.lower(), (r.get("program") or "").strip())
        by_key[key].append(str(r["id"]))
    return {k: v[0] for k, v in by_key.items() if len(v) == 1}


@st.cache_data(ttl=120, show_spinner=False)
def _attendance_exceptions_for(behaviour_student_id: str) -> list:
    try:
        res = (sb.table("student_attendance").select("exceptions")
              .eq("student_id", behaviour_student_id).limit(1).execute())
        if res.data:
            return res.data[0].get("exceptions") or []
    except Exception:
        pass
    return []


def get_excused_dates_for_student(student: dict) -> set:
    """ISO date strings this student was marked Absent, or there was No
    School, in the Behaviour Support Tool's attendance record. Empty set —
    i.e. no change to the existing expected-every-school-day logic — if the
    student can't be matched to a Behaviour Support record or has no
    attendance recorded yet."""
    key = ((student.get("student_name") or "").strip().lower(),
          (student.get("program") or "").strip())
    behaviour_id = _behaviour_student_id_map().get(key)
    if not behaviour_id:
        return set()
    exceptions = _attendance_exceptions_for(behaviour_id)
    return {
        e.get("date") for e in exceptions
        if e.get("type") in ATTENDANCE_EXCUSED_TYPES and e.get("date")
    }


def attendance_match_coverage(students: list) -> tuple:
    """(matched_names, unmatched_names) — a quick diagnostic so a silent
    name/program mismatch between this tool and the Behaviour Support Tool
    is visible rather than quietly producing the wrong consistency numbers."""
    id_map = _behaviour_student_id_map()
    matched, unmatched = [], []
    for s in students:
        key = ((s.get("student_name") or "").strip().lower(), (s.get("program") or "").strip())
        (matched if key in id_map else unmatched).append(s["student_name"])
    return matched, unmatched


# ── Program Snapshot — status meta + per-student aggregation ───────────────────
SNAPSHOT_STATUS_META = {
    # key: (emoji, label, colour)
    "on_track":       ("✅", "On Track",       "#16a34a"),
    "needs_increase": ("⚠️", "Needs Increase", "#d97706"),
    "not_started":    ("🔴", "Not Started",    "#c0392b"),
    "no_goal":        ("⚪", "No Goal Set",     "#9ca3af"),
}
# Lower number = more urgent — used to pick the "worst" status across a
# student's goals, and to sort the dashboard so what needs attention floats up.
SNAPSHOT_SEVERITY = {"no_goal": 0, "not_started": 1, "needs_increase": 2, "on_track": 3}


def build_student_snapshot(student: dict) -> dict:
    """Aggregates one student's active goal(s) into a single Program Snapshot
    row: student, program, overall status (the worst status across their
    goals), goal_count, and the per-goal detail (goal + its frequency info).
    Attendance (Behaviour Support Tool) is factored in once per student and
    applied to every one of their goals."""
    s_goals = get_goals(student["student_name"])
    if not s_goals:
        return {
            "student": student["student_name"], "program": student.get("program", "?"),
            "status": "no_goal", "goal_count": 0, "goals": [],
        }
    excused_dates = get_excused_dates_for_student(student)
    goals_info = []
    worst_status = "on_track"
    for g in s_goals:
        freq = goal_tracking_frequency(g["id"], g.get("start_date"), excused_dates=excused_dates)
        goals_info.append({"goal": g, "freq": freq})
        if SNAPSHOT_SEVERITY[freq["status"]] < SNAPSHOT_SEVERITY[worst_status]:
            worst_status = freq["status"]
    return {
        "student": student["student_name"], "program": student.get("program", "?"),
        "status": worst_status, "goal_count": len(s_goals), "goals": goals_info,
    }


def render_snapshot_card(snap: dict) -> str:
    """Compact HTML card for the Program Snapshot dashboard grid — everything
    visible at a glance, no click-through needed."""
    emoji, label, color = SNAPSHOT_STATUS_META[snap["status"]]
    student = snap["student"]

    if not snap["goals"]:
        body = (
            "<div style='font-size:0.78rem;color:#888;margin-top:4px;'>"
            "No SMARTAR goal has been created yet.</div>"
        )
    else:
        # Show the goal driving the overall status (falls back to the first goal).
        rep = next((gi for gi in snap["goals"] if gi["freq"]["status"] == snap["status"]),
                   snap["goals"][0])
        g, freq = rep["goal"], rep["freq"]
        goal_title = _short(g.get("smartar_goal", ""), 55)
        last_entry = freq["last_entry"].strftime("%d %b") if freq["last_entry"] else "Never"
        extra = f" · +{snap['goal_count']-1} more goal(s)" if snap["goal_count"] > 1 else ""
        body = (
            f"<div style='font-size:0.78rem;color:#555;margin-top:4px;'>🎯 {goal_title}</div>"
            f"<div style='font-size:0.72rem;color:#888;margin-top:6px;'>"
            f"Last entry: {last_entry} · Consistency: {freq['consistency_pct']}%{extra}</div>"
        )

    return (
        f"<div style='border:1px solid #e5e7eb;border-left:5px solid {color};border-radius:10px;"
        f"padding:12px 14px;margin-bottom:14px;background:#ffffff;min-height:96px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:baseline;gap:8px;'>"
        f"<div style='font-weight:700;font-size:0.95rem;color:#1f2937;'>{student}</div>"
        f"<div style='font-size:0.72rem;font-weight:700;color:{color};white-space:nowrap;'>{emoji} {label}</div>"
        f"</div>{body}</div>"
    )


def render_student_tile(snap: dict) -> str:
    """Bigger, bolder tile for the Program Snapshot grid — one per active
    student, coloured as a tracking-consistency alert (green/amber/red/grey)
    so the whole program's status reads at a glance. Pair with a button
    underneath (Streamlit can't make arbitrary HTML clickable) that opens
    that student's goal charts."""
    emoji, label, color = SNAPSHOT_STATUS_META[snap["status"]]
    student = snap["student"]

    if snap["goals"]:
        rep = next((gi for gi in snap["goals"] if gi["freq"]["status"] == snap["status"]),
                   snap["goals"][0])
        freq = rep["freq"]
        last_entry = freq["last_entry"].strftime("%d %b") if freq["last_entry"] else "Never"
        goal_line = f"{snap['goal_count']} goal{'s' if snap['goal_count'] != 1 else ''} · Last entry: {last_entry}"
        pct_line = f"{freq['consistency_pct']}% consistency (14 school days)"
    else:
        goal_line = "No SMARTAR goal set yet"
        pct_line = ""

    return (
        f"<div style='background:{color}1a;border:2px solid {color};border-radius:14px;"
        f"padding:14px 16px 10px;min-height:122px;'>"
        f"<div style='font-weight:700;font-size:1.0rem;color:#1f2937;'>{student}</div>"
        f"<div style='font-size:0.74rem;font-weight:700;color:{color};margin-top:3px;'>{emoji} {label}</div>"
        f"<div style='font-size:0.76rem;color:#555;margin-top:10px;'>{goal_line}</div>"
        f"<div style='font-size:0.76rem;color:#555;'>{pct_line}</div>"
        f"</div>"
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROGRAM SNAPSHOT — analytics-dashboard helpers (KPI tiles, trend charts,
# engagement funnel, drill-down). All numbers below come from real tracking
# rows — no figure here is simulated or estimated.
# ══════════════════════════════════════════════════════════════════════════════
PROGRAM_SCORE_MAP = {"EXCEEDING": 5, "ABOVE": 4, "EXPECTED": 3, "BELOW": 2, "NOT YET": 1}


def get_tracking_for_goals(goal_ids: list, from_date: str, to_date: str) -> list:
    """Bulk-fetch tracking rows for several goals at once (one query per
    program tab instead of one per goal) — powers the dashboard charts/table."""
    if not goal_ids:
        return []
    try:
        return (
            sb.table("smartar_tracking").select("goal_id, session_date, performance_level")
            .in_("goal_id", goal_ids)
            .gte("session_date", from_date)
            .lte("session_date", to_date)
            .execute().data or []
        )
    except Exception:
        return []


def program_time_series(tracking_rows: list, from_d: date, to_d: date) -> pd.DataFrame:
    """Daily entry count + average performance score across a program's goals,
    with every calendar day in the window present (0 entries on gaps)."""
    idx = pd.date_range(from_d, to_d, freq="D")
    if not tracking_rows:
        return pd.DataFrame({"date": idx, "entries": 0.0, "avg_score": None})
    df = pd.DataFrame(tracking_rows)
    df["score"] = df["performance_level"].map(PROGRAM_SCORE_MAP)
    daily = df.groupby("session_date").agg(entries=("performance_level", "count"),
                                           avg_score=("score", "mean"))
    daily.index = pd.to_datetime(daily.index)
    out = pd.DataFrame(index=idx).join(daily)
    out["entries"] = out["entries"].fillna(0)
    return out.reset_index().rename(columns={"index": "date"})


def program_funnel_counts(prog_snaps: list) -> dict:
    total = len(prog_snaps)
    with_goal     = sum(1 for sn in prog_snaps if sn["goal_count"] > 0)
    with_tracking = sum(1 for sn in prog_snaps if sn["status"] in ("needs_increase", "on_track"))
    on_track      = sum(1 for sn in prog_snaps if sn["status"] == "on_track")
    return {"total": total, "with_goal": with_goal,
            "with_tracking": with_tracking, "on_track": on_track}


def render_kpi_tile(label: str, value: str, sublabel: str, color1: str, color2: str) -> str:
    """One gradient KPI tile, matching the brief/funnel-dashboard reference look."""
    return (
        f"<div style='background:linear-gradient(135deg,{color1},{color2});color:white;"
        f"border-radius:12px;padding:14px 16px;min-height:88px;'>"
        f"<div style='font-size:0.72rem;font-weight:600;opacity:0.9;letter-spacing:.03em;'>{label}</div>"
        f"<div style='font-size:1.55rem;font-weight:700;margin-top:4px;'>{value}</div>"
        f"<div style='font-size:0.72rem;opacity:0.85;margin-top:2px;'>{sublabel}</div>"
        f"</div>"
    )


def fig_entries_line(ts_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ts_df["date"], y=ts_df["entries"], mode="lines", name="Entries",
        line=dict(color="#1A7A6E", width=2.5), fill="tozeroy", fillcolor="rgba(26,122,110,0.12)",
    ))
    fig.update_layout(
        title=dict(text="Tracking Entries / Day", font=dict(size=14)),
        height=260, margin=dict(l=10, r=10, t=36, b=10),
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f0f0f0", rangemode="tozero"),
    )
    return fig


def fig_score_line(ts_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ts_df["date"], y=ts_df["avg_score"], mode="lines+markers", name="Avg performance",
        line=dict(color="#1d6fa4", width=2.5), marker=dict(size=5), connectgaps=True,
    ))
    fig.update_layout(
        title=dict(text="Average Performance Level / Day", font=dict(size=14)),
        height=260, margin=dict(l=10, r=10, t=36, b=10),
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(range=[0.5, 5.5], tickmode="array", tickvals=[1, 2, 3, 4, 5],
                   ticktext=["NOT YET", "BELOW", "EXPECTED", "ABOVE", "EXCEEDING"],
                   showgrid=True, gridcolor="#f0f0f0"),
    )
    return fig


def fig_engagement_funnel(counts: dict) -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=["Active Students", "Have a Goal", "Being Tracked", "On Track"],
        x=[counts["total"], counts["with_goal"], counts["with_tracking"], counts["on_track"]],
        textinfo="value+percent initial",
        marker=dict(color=["#1d6fa4", "#2980b9", "#16a34a", "#15803d"]),
        connector=dict(line=dict(color="#e5e7eb", width=1)),
    ))
    fig.update_layout(
        title=dict(text="Engagement Funnel", font=dict(size=14)),
        height=280, margin=dict(l=10, r=10, t=36, b=10),
        paper_bgcolor="white",
    )
    return fig


def fig_goal_detail_chart(tracking_rows: list) -> go.Figure | None:
    """Drill-down chart for one student's goal — every observation plotted by
    date and coloured by performance level."""
    if not tracking_rows:
        return None
    df = pd.DataFrame(tracking_rows)
    df["score"] = df["performance_level"].map(PROGRAM_SCORE_MAP)
    df["date"]  = pd.to_datetime(df["session_date"])
    fig = go.Figure()
    daily_avg = df.groupby("date")["score"].mean().reset_index()
    fig.add_trace(go.Scatter(x=daily_avg["date"], y=daily_avg["score"], mode="lines",
                             line=dict(color="#94a3b8", width=1.5), name="Daily average",
                             hoverinfo="skip"))
    for lvl in LEVEL_ORDER:
        sub = df[df["performance_level"] == lvl]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["date"], y=sub["score"], mode="markers", name=lvl,
            marker=dict(color=MPL_COLOR.get(lvl, "#888"), size=9, line=dict(color="white", width=1)),
        ))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=20, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
        yaxis=dict(range=[0.5, 5.5], tickmode="array", tickvals=[1, 2, 3, 4, 5],
                   ticktext=["NOT YET", "BELOW", "EXPECTED", "ABOVE", "EXCEEDING"],
                   showgrid=True, gridcolor="#f0f0f0"),
        xaxis=dict(showgrid=False),
    )
    return fig


# ── Chart helpers (matplotlib — no clipping, named titles) ────────────────────
def make_goal_chart_mpl(tracking_data, goal_text: str, from_date: str,
                        to_date: str, student_name: str = "") -> bytes | None:
    """
    Returns PNG bytes. Title = full SMARTAR goal text.
    Uses bbox_inches='tight' so nothing is cut off.
    """
    if not tracking_data:
        return None

    df = pd.DataFrame(tracking_data)
    df["_date"]    = pd.to_datetime(df["session_date"])
    score_map      = {"EXCEEDING": 4, "ABOVE": 3, "EXPECTED": 2, "NOT YET": 1}
    df["_score"]   = df["performance_level"].map(score_map).fillna(0)

    fig = plt.figure(figsize=(15, 9), facecolor="white")
    title = _short(goal_text, 100)
    fig.suptitle(title, fontsize=10, fontweight="bold", color="#1A7A6E", y=0.98, wrap=True)
    if student_name:
        fig.text(0.5, 0.955, student_name, ha="center", fontsize=9,
                 color="#C8760A", fontweight="bold")

    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.32,
                           top=0.92, bottom=0.08, left=0.07, right=0.97)

    # ── Top: time series ──────────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    daily = df.groupby("_date")["_score"].mean().reset_index()
    ax1.plot(daily["_date"], daily["_score"], color="#1A7A6E", lw=1.5, alpha=0.45, zorder=1)
    sc_col = [MPL_COLOR.get(p, "#888") for p in df["performance_level"]]
    ax1.scatter(df["_date"], df["_score"], c=sc_col, s=100, zorder=2,
                edgecolors="white", linewidth=0.9)
    ax1.set_yticks([1, 2, 3, 4])
    ax1.set_yticklabels(["NOT YET", "EXPECTED", "ABOVE", "EXCEEDING"], fontsize=9)
    ax1.set_ylim(0.3, 4.7)
    ax1.set_title("Performance Over Time", fontsize=10, color="#1A7A6E",
                  fontweight="bold", loc="left", pad=6)
    ax1.annotate(f"Tracked: {from_date}  →  {to_date}",
                 xy=(0.01, 0.05), xycoords="axes fraction", fontsize=8, color="gray")
    patches = [mpatches.Patch(color=MPL_COLOR[p], label=p)
               for p in TRACK_LEVELS if p in df["performance_level"].values]
    ax1.legend(handles=patches, fontsize=8, loc="upper right", framealpha=0.7, ncol=4)
    ax1.grid(axis="y", alpha=0.22)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.tick_params(axis="x", rotation=35, labelsize=8)

    # ── Bottom-left: distribution pie ─────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    counts_d = df["performance_level"].value_counts().reindex(TRACK_LEVELS).dropna()
    if not counts_d.empty:
        pie_c = [MPL_COLOR[l] for l in counts_d.index]
        _, _, autotexts = ax2.pie(
            counts_d.values, labels=counts_d.index, colors=pie_c,
            autopct="%1.0f%%", startangle=90,
            textprops={"fontsize": 9},
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_fontsize(9)
            at.set_fontweight("bold")
    ax2.set_title("Distribution", fontsize=10, color="#1A7A6E",
                  fontweight="bold", loc="left", pad=6)

    # ── Bottom-right: by session ──────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    if "session_time" in df.columns:
        sesses = [s for s in ALL_SESSIONS if s in df["session_time"].values]
        if sesses:
            x = np.arange(len(sesses))
            w = 0.2
            for i, perf in enumerate(TRACK_LEVELS):
                vals = [df[(df["session_time"] == s) & (df["performance_level"] == perf)].shape[0]
                        for s in sesses]
                ax3.bar(x + i * w, vals, w, label=perf,
                        color=MPL_COLOR[perf], alpha=0.85, edgecolor="white")
            ax3.set_xticks(x + w * 1.5)
            ax3.set_xticklabels(sesses, fontsize=9)
            ax3.legend(fontsize=7, ncol=2)
            ax3.spines[["top", "right"]].set_visible(False)
            ax3.tick_params(labelsize=8)
            ax3.yaxis.get_major_locator().set_params(integer=True)
        else:
            ax3.axis("off")
    else:
        ax3.axis("off")
    ax3.set_title("By Session", fontsize=10, color="#1A7A6E",
                  fontweight="bold", loc="left", pad=6)

    fig.text(0.5, 0.01,
             f"CLC Learning and Behaviour Unit  |  Generated {datetime.now().strftime('%d %b %Y')}",
             ha="center", fontsize=7.5, color="#888", style="italic")

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def make_student_pdf(student_name: str, goal_chart_list: list) -> bytes:
    """goal_chart_list: [(goal_dict, png_bytes, from_d, to_d), …]"""
    from PIL import Image as PILImage
    buf = BytesIO()
    with PdfPages(buf) as pdf:
        # Cover
        fig, ax = plt.subplots(figsize=(11.69, 8.27), facecolor="white")
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0.78), 1, 0.22, transform=ax.transAxes,
                                   facecolor="#1A7A6E"))
        ax.text(0.5, 0.895, "SMARTAR Goal Progress Report", ha="center", va="center",
                fontsize=22, fontweight="bold", color="white", transform=ax.transAxes)
        ax.text(0.5, 0.635, student_name, ha="center", va="center",
                fontsize=20, fontweight="bold", color="#C8760A", transform=ax.transAxes)
        ax.text(0.5, 0.545, f"Generated: {datetime.now().strftime('%d %B %Y')}",
                ha="center", fontsize=12, color="gray", transform=ax.transAxes)
        ax.text(0.5, 0.47, "CLC Learning and Behaviour Unit",
                ha="center", fontsize=11, color="gray", transform=ax.transAxes)
        ax.text(0.5, 0.39, f"Goals with data: {len(goal_chart_list)}",
                ha="center", fontsize=11, color="#555", transform=ax.transAxes)
        pdf.savefig(fig, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        for idx, (goal, png_bytes, from_d, to_d) in enumerate(goal_chart_list, 1):
            if not png_bytes:
                continue
            img    = PILImage.open(BytesIO(png_bytes))
            pg_fig, pg_ax = plt.subplots(figsize=(11.69, 8.27), facecolor="white")
            pg_ax.imshow(np.array(img))
            pg_ax.axis("off")
            status = "Active" if goal.get("active", True) else "Archived"
            pg_fig.text(0.5, 0.005,
                        f"Goal {idx}  ·  [{status}]  ·  Period: {goal.get('tracking_period','All Day')}",
                        ha="center", fontsize=8, color="gray")
            pdf.savefig(pg_fig, bbox_inches="tight", facecolor="white")
            plt.close(pg_fig)

    buf.seek(0)
    return buf.getvalue()


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.gas-level-bar {
    display: flex; align-items: center; gap: 10px;
    padding: 6px 0; border-bottom: 1px solid #f0f0f0;
}
.gas-level-label { font-weight: 600; font-size: 0.82rem; width: 100px; flex-shrink: 0; }
.gas-level-desc  { font-size: 0.85rem; color: #374151; flex: 1; }
.student-header  {
    background: linear-gradient(135deg, #1d6fa4, #134e7a);
    color: white; padding: 14px 20px; border-radius: 10px; margin-bottom: 16px;
}
.metric-pill {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.8rem; font-weight: 600; margin: 2px;
}
.goal-badge {
    background: #e0f2fe; color: #0369a1;
    font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; font-weight: 600;
}
.exclusion-box {
    background: #fff7ed; border-left: 4px solid #f97316;
    padding: 10px 14px; border-radius: 0 8px 8px 0;
    font-size: 0.88rem; margin-bottom: 8px;
}
.smartar-box {
    background: #f0fdf4; border-left: 4px solid #16a34a;
    padding: 10px 14px; border-radius: 0 8px 8px 0; font-size: 0.88rem;
}
.period-box {
    background: #eff6ff; border-left: 4px solid #3b82f6;
    padding: 8px 14px; border-radius: 0 8px 8px 0;
    font-size: 0.84rem; margin-top: 6px;
}
.integration-banner {
    background: linear-gradient(135deg, #7c3aed, #5b21b6);
    color: white; padding: 12px 18px; border-radius: 10px;
    margin-bottom: 16px; border-left: 5px solid #fbbf24;
}
.alert-box {
    background: #fef3c7; border-left: 4px solid #f59e0b;
    padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 12px 0;
}
.success-box {
    background: #d1fae5; border-left: 4px solid #10b981;
    padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 12px 0;
}
.archived-box {
    background: #fff7ed; border-left: 4px solid #C8760A;
    padding: 10px 14px; border-radius: 0 8px 8px 0;
    font-size: 0.88rem; margin-bottom: 8px; opacity: 0.85;
}
.admin-panel { background: #f8fafc; border: 2px solid #cbd5e1; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ── Integration banner ─────────────────────────────────────────────────────────
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
    st.sidebar.link_button("← Back to Team Meeting",
                           team_meeting_return_url(integration),
                           use_container_width=True)

view = st.sidebar.radio(
    "View",
    ["🏫 Class Dashboard", "📋 Goal Builder",
     "📊 Daily Tracking", "📈 Progress Report",
     "🗺️ Program Snapshot", "⚙️ Admin Panel"],
    key="nav_view",
)
st.sidebar.markdown("---")
st.sidebar.caption("SMARTAR + GAS Goal Tracking · CLC LBU")

# ── Date-change detection ─────────────────────────────────────────────────────
# Detects midnight rollover: if the app has been open since yesterday, clear
# stale cached data and rerun so date.today() is correct everywhere.
_today_str = date.today().isoformat()
if st.session_state.get("_gb_last_date") != _today_str:
    st.session_state["_gb_last_date"] = _today_str
    st.cache_data.clear()
    st.rerun()

# ── Sidebar refresh button ────────────────────────────────────────────────────
if st.sidebar.button("🔄 Refresh Data", key="sb_refresh_gb", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ── Automatic daily teacher-alert check ────────────────────────────────────────
# Runs quietly once per browser session per day (whenever anyone first opens
# the app that day) so reminder emails go out without staff needing to visit
# Admin Panel. Sending itself is deduped globally via the Supabase-backed
# alert log, so it's harmless even if several people trigger this on the
# same day — only the first actually-due alert per student per day sends.
if st.session_state.get("_teacher_alert_checked_date") != _today_str:
    st.session_state["_teacher_alert_checked_date"] = _today_str
    if email_is_configured() and any(get_teacher_emails().values()):
        try:
            run_teacher_alert_check(get_students())
        except Exception:
            pass  # never let the background alert check break the app


# ══════════════════════════════════════════════════════════════════════════════
# 1. CLASS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if view == "🏫 Class Dashboard":
    st.title("🏫 Class Dashboard")
    st.caption(f"Today — {date.today().strftime('%A, %d %B %Y')}")

    students = get_students()
    if not students:
        st.info("No students set up yet. Go to **Goal Builder** to add your first student.")
        st.stop()

    prog_filter = st.selectbox("Filter by Program", ["All"] + PROGRAMS, index=0)
    if prog_filter != "All":
        students = [s for s in students if s.get("program") == prog_filter]

    if not students:
        st.warning("No students found for this program.")
        st.stop()

    for student in students:
        goals = get_goals(student["student_name"])
        if not goals:
            continue

        with st.expander(
            f"**{student['student_name']}** — {student.get('program','?')}  ·  "
            f"{len(goals)} goal{'s' if len(goals) != 1 else ''}",
            expanded=True,
        ):
            for idx, goal in enumerate(goals, 1):
                tracking          = get_tracking(goal["id"], days=21)
                counts, total, pcts = calc_percentages(tracking)
                today_rows        = get_today_tracking(goal["id"])
                today_sessions    = {r["session_time"]: r["performance_level"] for r in today_rows}
                needs_ref, low_c  = check_goal_needs_refinement(goal["id"])
                period            = goal.get("tracking_period", "All Day")
                sessions_today    = SESSIONS_FOR_PERIOD.get(period, ALL_SESSIONS)

                st.markdown(f'<span class="goal-badge">Goal {idx}</span>', unsafe_allow_html=True)
                if needs_ref:
                    st.markdown(
                        f'<div class="alert-box">⚠️ <b>Action Needed:</b> {low_c} recent sessions '
                        f'show NOT YET. Consider refining this goal.</div>',
                        unsafe_allow_html=True,
                    )
                if goal.get("exclusion_goal"):
                    st.markdown(
                        f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> {goal["exclusion_goal"]}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {goal.get("smartar_goal","No goal")}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="period-box">📅 Tracking period: <strong>{period}</strong> '
                    f'— sessions: {", ".join(sessions_today)}</div>',
                    unsafe_allow_html=True,
                )

                # Today's sessions (only relevant to tracking period)
                sess_cols = st.columns(len(sessions_today))
                for i, session in enumerate(sessions_today):
                    lvl = today_sessions.get(session)
                    if lvl:
                        sess_cols[i].markdown(
                            f"**{session}**<br>{LEVEL_EMOJI.get(lvl,'')} {lvl}",
                            unsafe_allow_html=True,
                        )
                    else:
                        sess_cols[i].markdown(f"**{session}**<br>⬜ Not recorded",
                                              unsafe_allow_html=True)

                # 21-day bar
                if total > 0:
                    bar_parts = []
                    for lvl in LEVEL_ORDER:
                        pct = pcts.get(lvl, 0)
                        if pct > 0:
                            bar_parts.append(
                                f'<div style="width:{pct}%;background:{LEVEL_COLOR[lvl]};'
                                f'height:14px;display:inline-block;"></div>'
                            )
                    st.markdown(
                        '<div style="display:flex;width:100%;border-radius:6px;overflow:hidden;margin:6px 0">'
                        + "".join(bar_parts) + "</div>",
                        unsafe_allow_html=True,
                    )
                    legend = "  ".join([
                        f'{LEVEL_EMOJI[l]} **{l}** {pcts.get(l,0):.0f}%'
                        for l in LEVEL_ORDER if pcts.get(l, 0) > 0
                    ])
                    st.caption(f"Last 21 days ({total} sessions): {legend}")
                else:
                    st.caption("No tracking data yet.")
                st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# 2. GOAL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
elif view == "📋 Goal Builder":
    st.title("📋 SMARTAR Goal Builder")
    st.caption("Build goals using the hierarchy of prompts — from exclusion goal through to GAS levels.")

    tab_build, tab_students = st.tabs(["➕ Add / Edit Goals", "👥 Manage Students"])

    # ── Manage Students ───────────────────────────────────────────────────────
    with tab_students:
        st.subheader("Add New Student")
        c1, c2, c3 = st.columns([3, 1, 1])
        new_name = c1.text_input("Student first name", key="new_student_name")
        new_prog = c2.selectbox("Program", PROGRAMS, key="new_prog")
        if c3.button("Add Student", type="primary"):
            if new_name.strip():
                sb.table("smartar_students").insert({
                    "student_name": new_name.strip(),
                    "program":      new_prog,
                    "active":       True,
                }).execute()
                st.success(f"✅ {new_name.strip()} added to {new_prog}.")
                st.rerun()
            else:
                st.warning("Please enter a student name.")

        st.subheader("Current Students")
        students = get_students()
        if students:
            for s in students:
                goals_s = get_goals(s["student_name"])
                sc1, sc2 = st.columns([4, 1])
                sc1.write(f"**{s['student_name']}** — {s.get('program','❓')} — {len(goals_s)} active goals")
                if sc2.button("Archive", key=f"arch_s_{s['id']}"):
                    sb.table("smartar_students").update({"active": False}).eq("id", s["id"]).execute()
                    st.success(f"Archived {s['student_name']}")
                    st.rerun()
        else:
            st.info("No students yet.")

    # ── Goal Builder form ─────────────────────────────────────────────────────
    with tab_build:
        students = get_students()
        if not students:
            st.info("Add a student first in the **Manage Students** tab.")
            st.stop()

        student_options = {s["student_name"]: s for s in students}

        # A stale deep-link (e.g. jump_to_edit_goal targeting an archived
        # student) shouldn't crash the selectbox — just drop it.
        if st.session_state.get("gb_student_select") not in student_options:
            st.session_state.pop("gb_student_select", None)

        # Pre-select from Team Meetings integration
        if integration["active"] and integration["student"]:
            default_idx = list(student_options.keys()).index(integration["student"]) \
                if integration["student"] in student_options else 0
        else:
            default_idx = 0

        selected_name  = st.selectbox("Select student", list(student_options.keys()),
                                      index=default_idx, key="gb_student_select")
        student        = student_options[selected_name]
        existing_goals  = get_goals(selected_name, active_only=True)
        archived_goals  = get_goals(selected_name, active_only=False)
        archived_goals  = [g for g in archived_goals if not g.get("active", True)]

        st.markdown(
            f'<div class="student-header"><b>{selected_name}</b> · '
            f'{student.get("program","?")} · {len(existing_goals)} active goals</div>',
            unsafe_allow_html=True,
        )

        # Show existing goals
        if existing_goals:
            st.subheader("Current Goals")
            for idx, g in enumerate(existing_goals, 1):
                goal_text    = g.get("smartar_goal", "No goal text")
                needs_ref, low_c = check_goal_needs_refinement(g["id"])
                streak_type, streak_days = check_goal_streak(g["id"])
                period       = g.get("tracking_period", "All Day")
                editing_goal = st.session_state.get(f"editgoal_open_{g['id']}", False)

                title_flag = " ⚠️ NEEDS REFINEMENT" if needs_ref else (
                    " 🚀 CONSIDER RAISING" if streak_type == "positive" else
                    " 📉 CONSIDER REVISING" if streak_type == "negative" else ""
                )
                with st.expander(
                    f"Goal {idx} — {_short(goal_text, 80)}" + title_flag,
                    expanded=editing_goal,
                ):
                    if needs_ref:
                        st.markdown(
                            f'<div class="alert-box">⚠️ <b>Action Required:</b> {low_c} recent '
                            f'sessions show NOT YET. Please refine this goal.</div>',
                            unsafe_allow_html=True,
                        )
                    if streak_type:
                        st.markdown(render_streak_alert(streak_type, streak_days), unsafe_allow_html=True)

                    if not editing_goal:
                        # ── READ-ONLY DISPLAY ─────────────────────────────────
                        if g.get("exclusion_goal"):
                            st.markdown(
                                f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> '
                                f'{g.get("exclusion_goal","—")}</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {goal_text}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="period-box">📅 Tracking period: <strong>{period}</strong>'
                            f' — {", ".join(SESSIONS_FOR_PERIOD.get(period, ALL_SESSIONS))}</div>',
                            unsafe_allow_html=True,
                        )

                        gas = get_gas_dict(g)
                        if any(gas.values()):
                            st.markdown("**GAS Performance Levels:**")
                            for lvl in LEVEL_ORDER:
                                desc = gas.get(lvl, "")
                                if desc:
                                    color = LEVEL_COLOR[lvl]
                                    st.markdown(
                                        f'<div class="gas-level-bar">'
                                        f'<span class="gas-level-label" style="color:{color}">'
                                        f'{LEVEL_EMOJI[lvl]} {lvl}</span>'
                                        f'<span class="gas-level-desc">{desc}</span></div>',
                                        unsafe_allow_html=True,
                                    )
                        if g.get("meeting_id"):
                            st.caption(f"📋 Created from {g.get('program','')} Team Meeting · "
                                       f"Term {g.get('term','')} Week {g.get('week','')}")

                        st.markdown("<br>", unsafe_allow_html=True)
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            if st.button("✏️ Edit Goal", key=f"editgoal_btn_{g['id']}",
                                         use_container_width=True):
                                st.session_state[f"editgoal_open_{g['id']}"] = True
                                st.rerun()
                        with ec2:
                            if st.button(f"🗑 Archive Goal {idx}", key=f"del_{g['id']}",
                                         use_container_width=True):
                                st.session_state[f"arch_gb_{g['id']}"] = True
                        if st.session_state.get(f"arch_gb_{g['id']}"):
                            reason = st.text_input("Archive reason (optional):",
                                                   key=f"arch_gb_r_{g['id']}")
                            ca, cb = st.columns(2)
                            with ca:
                                if st.button("Confirm Archive", key=f"arch_gb_d_{g['id']}", type="primary"):
                                    if archive_goal(g["id"], reason):
                                        st.session_state.pop(f"arch_gb_{g['id']}", None)
                                        # Pre-fill exclusion goal from archived goal for new build
                                        st.session_state["build_new_after_archive"] = True
                                        st.session_state["archived_excl_goal"] = g.get("exclusion_goal","")
                                        st.session_state["archived_student"] = g.get("student_name","")
                                        st.rerun()
                            with cb:
                                if st.button("Cancel", key=f"arch_gb_x_{g['id']}"):
                                    st.session_state.pop(f"arch_gb_{g['id']}", None)
                                    st.rerun()

                    else:
                        # ── FULL EDIT FORM — change anything about a saved goal ─
                        st.markdown(
                            '<div class="success-box">✏️ <b>Editing this goal.</b> '
                            'Changes save directly — no need to archive and rebuild.</div>',
                            unsafe_allow_html=True,
                        )
                        edit_excl = st.text_area(
                            "🏫 Exclusion Goal", value=g.get("exclusion_goal", "") or "",
                            height=80, key=f"editgoal_excl_{g['id']}",
                        )
                        edit_smartar = st.text_area(
                            "🎯 SMARTAR Goal", value=g.get("smartar_goal", ""),
                            height=100, key=f"editgoal_smt_{g['id']}",
                        )
                        edit_period = st.selectbox(
                            "📅 Tracking Period", TRACKING_PERIODS,
                            index=TRACKING_PERIODS.index(period) if period in TRACKING_PERIODS else 0,
                            key=f"editgoal_per_{g['id']}",
                            help="Determines which sessions Quick Track / Daily Tracking shows for this goal.",
                        )
                        cur_start = g.get("start_date")
                        try:
                            cur_start_d = date.fromisoformat(str(cur_start)[:10]) if cur_start else date.today()
                        except Exception:
                            cur_start_d = date.today()
                        edit_start = st.date_input(
                            "Start Date (update when refining goal)",
                            value=cur_start_d, key=f"editgoal_start_{g['id']}",
                        )

                        st.markdown("**GAS Performance Levels:**")
                        gas_current = get_gas_dict(g)
                        edit_gas = {}
                        for lvl in LEVEL_ORDER:
                            edit_gas[lvl] = st.text_area(
                                f"{LEVEL_EMOJI[lvl]} {lvl}",
                                value=gas_current.get(lvl, ""),
                                height=70, key=f"editgoal_gas_{lvl}_{g['id']}",
                            )

                        svc1, svc2 = st.columns(2)
                        with svc1:
                            if st.button("💾 Save Changes", key=f"editgoal_save_{g['id']}",
                                         type="primary", use_container_width=True,
                                         disabled=not edit_smartar.strip()):
                                sb.table("smartar_goals").update({
                                    "exclusion_goal":  edit_excl.strip() or None,
                                    "smartar_goal":    edit_smartar.strip(),
                                    "tracking_period": edit_period,
                                    "start_date":      edit_start.isoformat(),
                                    "gas_exceeding":   edit_gas.get("EXCEEDING", ""),
                                    "gas_above":       edit_gas.get("ABOVE", ""),
                                    "gas_expected":    edit_gas.get("EXPECTED", ""),
                                    "gas_below":       edit_gas.get("BELOW", ""),
                                    "gas_not_yet":     edit_gas.get("NOT YET", ""),
                                    "updated_at":      datetime.utcnow().isoformat(),
                                }).eq("id", g["id"]).execute()
                                st.session_state.pop(f"editgoal_open_{g['id']}", None)
                                st.success("✅ Goal updated.")
                                st.rerun()
                        with svc2:
                            if st.button("Cancel", key=f"editgoal_cancel_{g['id']}",
                                         use_container_width=True):
                                st.session_state.pop(f"editgoal_open_{g['id']}", None)
                                st.rerun()

        # ── ARCHIVED GOALS — restore button ──────────────────────────────────
        if archived_goals:
            st.markdown("---")
            st.markdown(f"**🗃️ Archived Goals ({len(archived_goals)})**")
            st.caption("These goals are preserved with all tracking data. Restore to make active again.")
            for ag in archived_goals:
                ag_text  = ag.get("smartar_goal", "—")
                ag_date  = (ag.get("archived_at") or "")[:10]
                ag_reason = ag.get("archive_reason", "")
                with st.expander(
                    f"🟠 {_short(ag_text, 70)} — archived {ag_date}",
                    expanded=False,
                ):
                    st.markdown(
                        f'<div class="archived-box">🎯 <b>SMARTAR Goal:</b> {ag_text}</div>',
                        unsafe_allow_html=True,
                    )
                    if ag_reason:
                        st.caption(f"Archive reason: {ag_reason}")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("♻️ Restore this Goal", key=f"restore_gb_{ag['id']}", type="primary"):
                            if restore_goal(ag["id"]):
                                st.success("✅ Goal restored to Active.")
                                st.rerun()
                    with c2:
                        if st.button("➕ Build Updated Goal from this", key=f"upd_gb_{ag['id']}"):
                            st.session_state["build_new_after_archive"] = True
                            st.session_state["archived_excl_goal"] = ag.get("exclusion_goal", "")
                            st.rerun()

        # ── NEW GOAL FORM ─────────────────────────────────────────────────────
        st.markdown("---")

        build_after_archive = st.session_state.get("build_new_after_archive", False)

        if build_after_archive:
            st.markdown(
                f'<div class="success-box">✅ Goal archived. Now build an updated '
                f'SMARTAR goal for <strong>{selected_name}</strong> using the hierarchy of prompts below.</div>',
                unsafe_allow_html=True,
            )
            if st.button("✖ Cancel — go back", key="cancel_new_after_arch"):
                st.session_state.pop("build_new_after_archive", None)
                st.session_state.pop("archived_excl_goal", None)
                st.rerun()
            excl_goal_default = st.session_state.get("archived_excl_goal", "")
            st.subheader("Build Updated Goal")
        else:
            st.subheader("Add New Goal")
            st.markdown("**Step 1 — Exclusion Goal from Home School**")
            excl_goal_default = ""

        excl_goal = st.text_area(
            "🏫 Exclusion Goal (from main school)",
            value=excl_goal_default,
            placeholder="Paste the exclusion goal as received from the main school…",
            height=80,
        )

        # ── STEP 2: AI-ASSISTED GOAL GENERATION ──────────────────────────────
        st.markdown("---")
        st.markdown("**Step 2 — AI-Assisted Goal Generation** 🤖")
        st.caption(
            "Describe the behaviour of concern and Groq will draft a SMARTAR goal using the "
            "hierarchy of prompts. You can then edit it directly or add missing elements and have "
            "Groq recreate it — then click **Use this Goal** to move forward."
        )

        ai_student_first = st.text_input(
            "Student first name (for goal)",
            value=selected_name.split()[0],
            key="ai_student_first",
        )

        boc_text = st.text_area(
            "📝 Describe the behaviour of concern",
            placeholder=(
                "e.g. Frequently refuses to start written tasks during literacy, calls out "
                "and leaves seat, requires multiple prompts before engaging with structured "
                "activities. Needs a goal around initiating tasks with reduced prompting…"
            ),
            height=110,
            key="boc_description",
        )

        with st.expander(
            "🔧 Guide the AI with hierarchy preferences (optional — leave as 'AI decides' to let Groq choose)",
            expanded=False,
        ):
            ah_col1, ah_col2 = st.columns(2)
            with ah_col1:
                ah_grouping  = st.selectbox("Grouping",               ["AI decides"] + GROUPINGS,    key="ah_grouping")
                ah_task_type = st.selectbox("Task type",               ["AI decides"] + TASK_TYPES,   key="ah_task_type")
                ah_setting   = st.selectbox("Setting",                 ["AI decides"] + SETTINGS,     key="ah_setting")
            with ah_col2:
                ah_prompts   = st.selectbox("Prompt level",            ["AI decides"] + PROMPT_TYPES, key="ah_prompts")
                ah_rate      = st.selectbox("Rate / success criteria", ["AI decides"] + RATE_OPTIONS, key="ah_rate")

        gen_btn_col, _ = st.columns([2, 3])
        with gen_btn_col:
            if st.button(
                "🤖 Generate SMARTAR Goal from Description",
                type="primary",
                key="gen_from_boc_btn",
                disabled=not (boc_text.strip() and ai_student_first.strip()),
            ):
                if not groq_client:
                    st.warning("⚠️ AI unavailable — GROQ_API_KEY not configured.")
                else:
                    hierarchy_context = ""
                    if ah_grouping  != "AI decides": hierarchy_context += f"\n- Grouping: {ah_grouping}"
                    if ah_task_type != "AI decides": hierarchy_context += f"\n- Task type: {ah_task_type}"
                    if ah_setting   != "AI decides": hierarchy_context += f"\n- Setting: {ah_setting}"
                    if ah_prompts   != "AI decides": hierarchy_context += f"\n- Prompt level: {ah_prompts}"
                    if ah_rate      != "AI decides": hierarchy_context += f"\n- Rate / success criteria: {ah_rate}"

                    if not hierarchy_context:
                        hierarchy_context = (
                            "\n(Choose the most appropriate hierarchy elements based on "
                            "the behaviour description)"
                        )

                    gen_prompt = f"""You are an expert at writing SMARTAR goals for students in alternative education settings using a trauma-informed, PBS (Positive Behaviour Support) framework aligned with BSEM.

Student name: {ai_student_first}
Behaviour of concern: {boc_text}

Preferred hierarchy elements (use these; if not specified, choose the most appropriate):{hierarchy_context}

Available hierarchy options to draw from:
- Groupings: {', '.join(GROUPINGS)}
- Task types: {', '.join(TASK_TYPES)}
- Settings: {', '.join(SETTINGS)}
- Prompt levels (hierarchy of prompts): {', '.join(PROMPT_TYPES)}
- Rate / success criteria options: {', '.join(RATE_OPTIONS)}

SMARTAR requirements:
- Specific: names the student, the replacement skill/behaviour, setting, grouping, task type, prompt level
- Measurable: includes a clear success rate from the options above
- Achievable: realistic for an alternative education setting with high-needs students
- Relevant: directly addresses the behaviour of concern as a POSITIVE replacement behaviour
- Time-bound: success criteria references a time period
- Aspirational + Reviewed: strengths-based language, implies ongoing monitoring

Rules:
- Write ONE fluent, professional goal statement
- Start with "{ai_student_first} will..."
- Frame positively — what the student WILL do (replacement behaviour), not what they won't
- Trauma-informed, strengths-based language (BSEM: Regulate, Relate, Reason)
- Do NOT use the word "appropriately" unless essential
- One sentence only — no preamble, no explanation, no bullet points

Return ONLY the goal statement."""

                    with st.spinner("🤖 Generating SMARTAR goal…"):
                        try:
                            generated = groq_call(gen_prompt)
                            if generated and len(generated) > 20 and "[AI unavailable" not in generated:
                                generated = generated.strip().strip('"').strip("'")
                                st.session_state["ai_generated_goal"]         = generated
                                st.session_state["ai_generated_goal_current"] = generated
                                st.session_state.pop("ai_additional_elements", None)
                                st.rerun()
                            else:
                                st.warning(
                                    "Unexpected AI response — try describing the behaviour "
                                    "in more detail or adjusting the hierarchy options."
                                )
                        except Exception as e:
                            st.error(f"AI error: {e}")

        if not (boc_text.strip() and ai_student_first.strip()):
            st.caption("💡 Enter a student name and describe the behaviour to enable AI generation.")

        # ── Generated goal: review, edit, add elements, recreate ─────────────
        if st.session_state.get("ai_generated_goal"):
            st.markdown("---")
            st.markdown("**✨ AI-Generated Goal — Review & Refine**")

            _cur_ai = st.session_state["ai_generated_goal"]
            _ai_edit_key = f"ai_goal_edit_{hash(_cur_ai)}"
            ai_goal_edited = st.text_area(
                "Edit the generated goal directly:",
                value=_cur_ai,
                height=100,
                key=_ai_edit_key,
            )
            # Keep a running copy of what the user has manually edited
            if ai_goal_edited and ai_goal_edited != _cur_ai:
                st.session_state["ai_generated_goal_current"] = ai_goal_edited

            st.markdown("**🔧 Add any missing elements or adjustments:**")
            st.caption(
                "Describe anything that was missed or needs changing — "
                "e.g. *'change setting to during maths lessons'*, "
                "*'prompt level should be gestural not verbal'*, "
                "*'add that he uses a visual schedule to self-prompt'*"
            )
            additional_elements = st.text_area(
                "Additional elements / modifications to incorporate:",
                placeholder=(
                    "e.g. The goal should specify that Jake uses a visual schedule, "
                    "and the setting should be during morning maths not literacy…"
                ),
                height=90,
                key="ai_additional_elements",
            )

            rc_col, use_col, clear_col = st.columns([2, 1, 1])
            with rc_col:
                if st.button(
                    "🔄 Recreate Goal with Modifications",
                    key="recreate_ai_goal_btn",
                    disabled=not additional_elements.strip(),
                    type="secondary",
                ):
                    if not groq_client:
                        st.warning("⚠️ AI unavailable.")
                    else:
                        base_goal = (
                            st.session_state.get("ai_generated_goal_current")
                            or ai_goal_edited
                            or _cur_ai
                        )
                        _ai_sname = st.session_state.get("ai_student_first") or selected_name.split()[0]
                        recreate_prompt = f"""You are an expert at writing SMARTAR goals for students in alternative education settings (trauma-informed, PBS framework).

Recreate this SMARTAR goal incorporating ALL of the requested modifications.

Current goal:
{base_goal}

Modifications / additional elements to incorporate:
{additional_elements}

Requirements:
- Return ONE fluent, professional goal statement
- Preserve all specificity from the original that hasn't been changed
- Incorporate every modification requested — do not silently drop any
- Start with "{_ai_sname} will..."
- Maintain trauma-informed, strengths-based language
- One sentence only — no preamble, no explanation, no bullet points

Return ONLY the final goal statement."""
                        with st.spinner("🔄 Recreating goal with your modifications…"):
                            try:
                                recreated = groq_call(recreate_prompt)
                                if recreated and len(recreated) > 20 and "[AI unavailable" not in recreated:
                                    recreated = recreated.strip().strip('"').strip("'")
                                    st.session_state["ai_generated_goal"]         = recreated
                                    st.session_state["ai_generated_goal_current"] = recreated
                                    st.session_state.pop("ai_additional_elements", None)
                                    st.rerun()
                                else:
                                    st.warning("Unexpected AI response — try again.")
                            except Exception as e:
                                st.error(f"AI error: {e}")

            with use_col:
                if st.button("✅ Use this Goal", key="use_ai_goal_btn", type="primary"):
                    goal_to_use = (
                        st.session_state.get("ai_generated_goal_current")
                        or ai_goal_edited
                        or _cur_ai
                    )
                    st.session_state["refined_goal"]   = goal_to_use
                    st.session_state["gb_assembled"]   = goal_to_use
                    # clear AI state
                    for _k in ["ai_generated_goal", "ai_generated_goal_current",
                                "ai_additional_elements", "gas_levels",
                                "gb_ai_period", "gas_last_source"]:
                        st.session_state.pop(_k, None)
                    st.rerun()

            with clear_col:
                if st.button("🗑 Clear", key="clear_ai_goal_btn"):
                    for _k in ["ai_generated_goal", "ai_generated_goal_current",
                                "ai_additional_elements"]:
                        st.session_state.pop(_k, None)
                    st.rerun()

            st.markdown(
                '<div class="success-box">✅ Happy with the goal? Click '
                '<strong>Use this Goal</strong> above to set it as the final goal — '
                'then complete the Tracking Period and GAS levels below.</div>',
                unsafe_allow_html=True,
            )

        # ── MANUAL ALTERNATIVE ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Or: Build Manually Using the Hierarchy of Prompts**")
        st.caption(
            "Complete each field below to assemble a goal statement manually, "
            "then use AI to refine it — or use the AI generator above."
        )

        col1, col2 = st.columns(2)
        with col1:
            student_first = st.text_input(
                "Student first name (as it appears in goal)",
                value=selected_name.split()[0],
            )
            skill    = st.text_area("Expected skill / behaviour",
                                    placeholder="e.g. use a break card to request a break",
                                    height=80)
            grouping = st.selectbox("Grouping", GROUPINGS)
            task_type = st.selectbox("Task type", TASK_TYPES)

        with col2:
            setting = st.selectbox("Setting", SETTINGS)
            prompts = st.selectbox("Prompt level (Hierarchy of Prompts)", PROMPT_TYPES)
            rate    = st.selectbox("Rate / success criteria", RATE_OPTIONS)

        # Auto-assembled preview
        if skill and student_first:
            assembled = (
                f"{student_first} will {skill} {grouping.lower()} during "
                f"{task_type.lower()} in the {setting.lower()} with "
                f"{prompts.lower()}, demonstrating successful use on {rate}."
            )
        else:
            assembled = ""

        # ── Step 3: Refine ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Step 3 — Refine and Finalise the SMARTAR Goal**")

        # Keep assembled in session state so it persists across reruns
        if assembled:
            st.session_state["gb_assembled"] = assembled
        current_assembled = st.session_state.get("gb_assembled", "")

        # Show assembled preview
        if current_assembled:
            st.markdown("**Assembled Goal Preview:**")
            st.info(current_assembled)

        refine_col, _ = st.columns([2, 3])
        with refine_col:
            if st.button("✨ Refine Goal with AI", type="primary",
                         key="refine_btn", disabled=not current_assembled.strip()):
                if not groq_client:
                    st.warning("⚠️ AI unavailable — GROQ_API_KEY not configured. Edit manually below.")
                else:
                    with st.spinner("Refining goal…"):
                        try:
                            refined = groq_call(
                                f"""You are an expert at writing SMARTAR goals for students in alternative education (trauma-informed, PBS framework).

Rewrite this assembled goal into ONE fluent, professional goal statement for an IEP/support plan.

Rules:
- Fix repeated/doubled words (e.g. "during during" → "during", "the the" → "the")
- Start with "{student_first} will..."
- Keep ALL specific details: skill/behaviour, grouping, task type, setting, prompt level, success rate
- One sentence only — no preamble, no explanation, no bullet points
- Trauma-informed, strengths-based language
- Do NOT add "appropriately" or "independently" unless already in the original

Goal to refine:
{current_assembled}

Return ONLY the final goal statement."""
                            )
                            if refined and len(refined) > 20 and "[AI unavailable" not in refined:
                                refined = refined.strip().strip('"').strip("'")
                                st.session_state["refined_goal"] = refined
                                st.session_state["gb_goal_for_gas"] = refined
                                st.session_state.pop("gas_levels", None)
                                st.session_state.pop("gb_ai_period", None)
                                st.rerun()
                            else:
                                st.warning("Unexpected AI response — edit manually below.")
                        except Exception as e:
                            st.error(f"AI error: {e}")
        if not current_assembled.strip():
            st.caption("💡 Complete skill/behaviour in Step 2 to enable AI refinement.")

        # Final goal text area — driven by session state so value persists
        # Prefer: refined_goal > assembled > empty
        _goal_default = (st.session_state.get("refined_goal")
                         or current_assembled
                         or "")
        # Use a dynamic key so the widget re-renders when refined_goal changes
        _goal_key = f"final_goal_{hash(_goal_default)}"
        final_goal = st.text_area(
            "Final SMARTAR Goal (edit if needed)",
            value=_goal_default,
            height=100,
            key=_goal_key,
        )
        # Keep session state in sync with any manual edits
        if final_goal and final_goal != st.session_state.get("refined_goal"):
            st.session_state["refined_goal"] = final_goal

        # ── Auto-generate GAS when goal is ready and GAS not yet done ──────────
        _gas_source = st.session_state.get("refined_goal") or current_assembled
        _gas_done   = bool(st.session_state.get("gas_levels"))
        _gas_last   = st.session_state.get("gas_last_source", "")

        # Generate when: source exists, AI available, and source has changed or GAS never done
        if _gas_source and groq_client and (not _gas_done or _gas_source != _gas_last):
            if not _gas_done:  # only auto-run if GAS is empty
                with st.spinner("🤖 Auto-generating GAS performance levels…"):
                    try:
                        gas_raw = groq_call(
                            f"""Create a Goal Attainment Scale (GAS) for this SMARTAR goal.

Goal: {_gas_source}

The EXPECTED level (0) IS the goal exactly as written — copy it verbatim.
Scale above and below by changing ONLY the rate/frequency/success criteria.

Return ONLY valid JSON, no markdown, no extra text:
{{
  "EXCEEDING": "Goal text with higher rate/criteria",
  "ABOVE": "Goal text with slightly higher rate/criteria",
  "EXPECTED": "Exact goal text as written",
  "BELOW": "Goal text with slightly lower rate/criteria",
  "NOT_YET": "Goal text with much lower rate/criteria"
}}"""
                        )
                        gas_clean  = gas_raw.strip().strip("```json").strip("```").strip()
                        gas_parsed = json.loads(gas_clean)
                        if "NOT_YET" in gas_parsed:
                            gas_parsed["NOT YET"] = gas_parsed.pop("NOT_YET")
                        st.session_state["gas_levels"]     = gas_parsed
                        st.session_state["gas_last_source"] = _gas_source
                        st.rerun()
                    except Exception as ex:
                        st.caption(f"⚠️ GAS auto-generate failed ({ex}) — fill in manually below.")

        # ── Step 4: Tracking Period ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Step 4 — Tracking Period**")
        st.caption(
            "Determines which sessions Quick Track shows for this goal. "
            "AI checks the goal text for time-specific language."
        )

        ai_period_result = st.session_state.get("gb_ai_period")

        if final_goal.strip():
            if st.button("🤖 Check Tracking Period with AI", key="check_period_btn"):
                with st.spinner("Analysing goal for time context…"):
                    ai_period_result = ai_check_period(final_goal)
                    st.session_state["gb_ai_period"] = ai_period_result
                    st.rerun()

        suggested = "All Day"
        if ai_period_result:
            conf = ai_period_result.get("confidence", "Low")
            st.info(
                f"**AI Recommendation:** {ai_period_result['period']}\n\n"
                f"*{ai_period_result.get('reasoning','')}*  \nConfidence: {conf}"
            )
            suggested = ai_period_result.get("period", "All Day")
            if suggested not in TRACKING_PERIODS:
                suggested = "All Day"

        tracking_period = st.selectbox(
            "Tracking Period", TRACKING_PERIODS,
            index=TRACKING_PERIODS.index(suggested),
            key="gb_tracking_period",
            help="Override AI recommendation if needed.",
        )
        st.caption(f"📅 Sessions to track: **{', '.join(SESSIONS_FOR_PERIOD[tracking_period])}**")

        # ── Step 5: GAS Levels ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Step 5 — Goal Attainment Scaling (GAS)**")
        st.caption("Auto-filled from the SMARTAR goal. Edit any field before saving.")

        if groq_client and final_goal:
            if st.button("🔄 Re-generate GAS Levels with AI",
                         type="secondary", key="gen_gas_btn"):
                with st.spinner("Generating GAS levels…"):
                    gas_prompt = f"""Create a Goal Attainment Scale (GAS) for this SMARTAR goal:

"{final_goal}"

Create 5 performance level descriptions that logically scale above and below the EXPECTED level.
The EXPECTED level IS the goal as written.

Return ONLY a JSON object with these exact keys: EXCEEDING, ABOVE, EXPECTED, BELOW, NOT_YET
Each value should be a brief modified version of the goal at that level.
Only modify the rate/frequency/success criteria to show each level.
No markdown, no explanation, pure JSON only."""
                    raw = groq_call(gas_prompt)
                    try:
                        raw_clean  = raw.strip().strip("```json").strip("```").strip()
                        gas_parsed = json.loads(raw_clean)
                        if "NOT_YET" in gas_parsed and "NOT YET" not in gas_parsed:
                            gas_parsed["NOT YET"] = gas_parsed.pop("NOT_YET")
                        st.session_state["gas_levels"] = gas_parsed
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't parse GAS levels. Try again. ({e})")

        gas_levels = st.session_state.get("gas_levels", {})
        edited_gas = {}
        # Use a version counter in the key so widgets re-render when gas_levels changes
        _gas_ver = hash(str(sorted(gas_levels.items()))) if gas_levels else 0
        if gas_levels:
            st.markdown("**Review GAS Performance Levels:**")
            st.caption("Auto-filled from your goal. Edit any field before saving.")
        else:
            st.caption("Fill in skill/behaviour above — GAS levels will auto-generate.")
        for lvl in LEVEL_ORDER:
            _key    = lvl if lvl in gas_levels else lvl.replace(" ", "_")
            default = gas_levels.get(lvl, gas_levels.get(_key, ""))
            color   = LEVEL_COLOR[lvl]
            # Dynamic key forces widget to re-render with new value when gas_levels changes
            edited_gas[lvl] = st.text_area(
                f"{LEVEL_EMOJI[lvl]} {lvl}",
                value=default, height=70,
                key=f"gas_edit_{lvl}_{_gas_ver}",
            )

        # ── Save ──────────────────────────────────────────────────────────────
        st.markdown("---")
        if st.button("💾 Save Goal", type="primary", disabled=not final_goal,
                     key="save_goal_btn"):
            new_goal = {
                "student_name":    selected_name,
                "exclusion_goal":  excl_goal.strip() if excl_goal else None,
                "smartar_goal":    final_goal.strip(),
                "skill":           skill.strip() if skill else None,
                "grouping":        grouping,
                "task_type":       task_type,
                "setting":         setting,
                "prompts":         prompts,
                "rate":            rate,
                "tracking_period": tracking_period,
                "active":          True,
                "status":          "Active",
                "start_date":      date.today().isoformat(),
            }
            if edited_gas:
                new_goal["gas_exceeding"] = edited_gas.get("EXCEEDING", "")
                new_goal["gas_above"]     = edited_gas.get("ABOVE", "")
                new_goal["gas_expected"]  = edited_gas.get("EXPECTED", "")
                new_goal["gas_below"]     = edited_gas.get("BELOW", "")
                new_goal["gas_not_yet"]   = edited_gas.get("NOT YET", "")
            if integration["active"]:
                new_goal.update({
                    "meeting_id": integration["meeting_id"],
                    "program":    integration["program"],
                    "term":       integration["term"],
                    "week":       integration["week"],
                })


            sb.table("smartar_goals").insert(new_goal).execute()

            for k in ["refined_goal", "gas_levels", "gb_ai_period",
                      "gb_assembled", "gb_goal_for_gas",
                      "build_new_after_archive", "archived_excl_goal", "archived_student"]:
                st.session_state.pop(k, None)

            st.success(f"✅ Goal saved for {selected_name}!")
            if integration["active"]:
                st.link_button("← Return to Team Meeting",
                               team_meeting_return_url(integration),
                               type="primary", use_container_width=True)
                st.caption("Your goal is saved. Click above to go back — the meeting will reopen with this goal showing.")
            else:
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# 3. DAILY TRACKING
# ══════════════════════════════════════════════════════════════════════════════
elif view == "📊 Daily Tracking":
    st.title("📊 Daily Tracking")

    col1, col2 = st.columns([6, 1])
    if col2.button("🔄 Refresh", type="secondary"):
        st.rerun()

    students = get_students()
    if not students:
        st.info("No students set up yet.")
        st.stop()

    track_date     = st.date_input("Tracking date", value=date.today())
    st.markdown(f"**Recording for: {track_date.strftime('%A, %d %B %Y')}**")

    student_options = {s["student_name"]: s for s in students}
    selected_name   = st.selectbox("Select student", list(student_options.keys()))
    goals           = get_goals(selected_name)

    if not goals:
        st.info(f"No goals set up for {selected_name}. Go to Goal Builder first.")
        st.stop()

    st.markdown("---")

    for idx, goal in enumerate(goals, 1):
        # today_sessions not used for display — get_session_counts handles counts
        gas            = get_gas_dict(goal)
        needs_ref, low_c = check_goal_needs_refinement(goal["id"])
        streak_type, streak_days = check_goal_streak(goal["id"])

        # Determine which sessions to show based on tracking period
        period   = goal.get("tracking_period", "All Day")
        sessions = SESSIONS_FOR_PERIOD.get(period, ALL_SESSIONS)

        st.markdown(f"### Goal {idx}")
        if needs_ref:
            st.markdown(
                f'<div class="alert-box">⚠️ <b>IMPORTANT:</b> {low_c} recent sessions show '
                f'NOT YET. Please refine this goal to make it more achievable.</div>',
                unsafe_allow_html=True,
            )
        if streak_type:
            st.markdown(render_streak_alert(streak_type, streak_days), unsafe_allow_html=True)
            if st.button("✏️ Edit this goal in Goal Builder", key=f"streak_jump_track_{goal['id']}"):
                jump_to_edit_goal(selected_name, goal["id"])
        st.markdown(
            f'<div class="smartar-box">🎯 {goal.get("smartar_goal","No goal")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="period-box">📅 Tracking period: <strong>{period}</strong>'
            f' — recording sessions: <strong>{", ".join(sessions)}</strong></div>',
            unsafe_allow_html=True,
        )

        if any(gas.values()):
            with st.expander("📋 View GAS Performance Levels"):
                for lvl in LEVEL_ORDER:
                    desc = gas.get(lvl, "")
                    if desc:
                        color = LEVEL_COLOR[lvl]
                        st.markdown(
                            f'<div class="gas-level-bar">'
                            f'<span class="gas-level-label" style="color:{color}">'
                            f'{LEVEL_EMOJI[lvl]} {lvl}</span>'
                            f'<span class="gas-level-desc">{desc}</span></div>',
                            unsafe_allow_html=True,
                        )

        st.markdown("**Record observation:**")
        st.caption("Each button tap adds one observation — tap as many times as observed.")
        sess_counts = get_session_counts(goal["id"], track_date.isoformat())
        sess_cols   = st.columns(len(sessions))

        for i, session in enumerate(sessions):
            lvl_counts = sess_counts.get(session, {})
            total_obs  = sum(lvl_counts.values())
            with sess_cols[i]:
                obs_label = f"**{session}**" + (f" · {total_obs} obs" if total_obs else "")
                st.markdown(obs_label)
                for lvl in TRACK_LEVELS:
                    n       = lvl_counts.get(lvl, 0)
                    count_s = f" ×{n}" if n else ""
                    label   = f"{LEVEL_EMOJI[lvl]} {lvl}{count_s}"
                    btn_key = f"track_{goal['id']}_{session}_{lvl}_{track_date}"
                    if st.button(label, key=btn_key, use_container_width=True,
                                 type="primary" if n > 0 else "secondary"):
                        upsert_session(goal["id"], selected_name, session, lvl,
                                       track_date=track_date.isoformat())
                        if lvl == "NOT YET":
                            st.session_state["show_ref_alert"] = goal["id"]
                        st.rerun()

        if st.session_state.get("show_ref_alert") == goal["id"]:
            st.markdown(
                '<div class="alert-box">⚠️ NOT YET recorded. Please refine the goal '
                'to make it more achievable — focus on incremental progress.</div>',
                unsafe_allow_html=True,
            )
            if st.button("I understand — will refine goal as needed", key=f"ack_{goal['id']}"):
                st.session_state.pop("show_ref_alert", None)
                st.rerun()

        # ── Delete a mistaken observation ───────────────────────────────────
        # Always visible (even with 0 entries) so the control is easy to find —
        # only its contents depend on whether anything's been recorded yet.
        day_entries = get_tracking_entries(goal["id"], track_date.isoformat())
        with st.expander(
            f"🗑 Manage observations for {track_date.strftime('%d %b %Y')} "
            f"({len(day_entries)} recorded)"
        ):
            if not day_entries:
                st.caption(f"No observations recorded for {selected_name} on this date yet.")
            else:
                st.caption("Tapped the wrong button? Delete the incorrect observation below.")
                for row in day_entries:
                    lvl   = row.get("performance_level", "")
                    sess  = row.get("session_time", "")
                    stamp = row.get("recorded_at", "")
                    time_str = ""
                    if stamp:
                        try:
                            time_str = datetime.fromisoformat(
                                str(stamp).replace("Z", "+00:00")
                            ).strftime("%I:%M %p")
                        except Exception:
                            time_str = ""

                    confirm_key = f"confirm_del_track_{row['id']}"
                    dcol1, dcol2 = st.columns([4, 1])
                    with dcol1:
                        st.markdown(
                            f"{LEVEL_EMOJI.get(lvl,'')} **{sess}** — {lvl}"
                            + (f"  ·  logged {time_str}" if time_str else "")
                        )
                    with dcol2:
                        if st.button("🗑 Delete", key=f"del_track_{row['id']}",
                                     use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    if st.session_state.get(confirm_key):
                        st.warning(
                            f"Delete this {lvl} observation for {sess} "
                            f"({track_date.strftime('%d %b %Y')})? This can't be undone."
                        )
                        ccol1, ccol2 = st.columns(2)
                        with ccol1:
                            if st.button("✅ Confirm delete", key=f"del_track_confirm_{row['id']}",
                                         type="primary", use_container_width=True):
                                if delete_tracking_entry(row["id"]):
                                    st.session_state.pop(confirm_key, None)
                                    st.success("Observation deleted.")
                                    st.rerun()
                        with ccol2:
                            if st.button("Cancel", key=f"del_track_cancel_{row['id']}",
                                         use_container_width=True):
                                st.session_state.pop(confirm_key, None)
                                st.rerun()
                    st.markdown(
                        "<hr style='margin:6px 0;border:none;border-top:1px solid #eee;'>",
                        unsafe_allow_html=True,
                    )

        st.markdown("---")

    st.success("Tracking saves immediately when you click a level button.")


# ══════════════════════════════════════════════════════════════════════════════
# 4. PROGRESS REPORT
# ══════════════════════════════════════════════════════════════════════════════
elif view == "📈 Progress Report":
    st.title("📈 Progress Report")
    st.caption("Charts use the full SMARTAR goal as the title. PNG downloads are full-size — nothing clipped.")

    students = get_students()
    if not students:
        st.info("No students set up yet.")
        st.stop()

    student_options = {s["student_name"]: s for s in students}
    selected_name   = st.selectbox("Select student", list(student_options.keys()))
    student         = student_options[selected_name]

    # Show active AND archived goals
    all_goals = get_all_goals_for_student(selected_name)
    if not all_goals:
        st.info(f"No goals for {selected_name}.")
        st.stop()

    period_filter = st.radio(
        "Report period (for active goals without a fixed range)",
        ["Last 2 weeks", "Last 3 weeks", "Last 5 weeks"],
        horizontal=True,
    )
    days_map = {"Last 2 weeks": 14, "Last 3 weeks": 21, "Last 5 weeks": 35}
    default_days = days_map[period_filter]

    st.markdown(f"## {selected_name} — Progress Report")
    st.caption(f"Program: {student.get('program','?')} · {len(all_goals)} total goals")

    goal_chart_list = []   # for PDF: (goal, png_bytes, from_d, to_d)

    for idx, goal in enumerate(all_goals, 1):
        is_active = goal.get("active", True)
        status    = "Active" if is_active else "Archived"
        s_icon    = "🟢" if is_active else "🟠"
        period    = goal.get("tracking_period", "All Day")
        sessions  = SESSIONS_FOR_PERIOD.get(period, ALL_SESSIONS)

        # Date range: for archived goals use start→archived_at; for active use start→today
        from_d, to_d = goal_date_range(goal)

        tracking = get_tracking_range(goal["id"], from_d, to_d, sessions=sessions)

        if tracking:
            actual_from = min(r["session_date"] for r in tracking)[:10]
            actual_to   = max(r["session_date"] for r in tracking)[:10]
            track_str   = f"{actual_from} → {actual_to}"
            n_entries   = len(tracking)
        else:
            actual_from = from_d
            actual_to   = to_d
            track_str   = "No entries yet"
            n_entries   = 0

        counts, total, pcts = calc_percentages(tracking)
        trend = analyze_trend(tracking)
        needs_ref, low_c = check_goal_needs_refinement(goal["id"])
        streak_type, streak_days = check_goal_streak(goal["id"])

        smartar_text = goal.get("smartar_goal", "No goal text")

        st.markdown(
            f"### {s_icon} Goal {idx} ({status}): {goal.get('domain','')} — "
            f"{_short(smartar_text, 55)}"
        )

        # Goal start / date range info
        goal_start = goal.get("start_date")
        if goal_start:
            try:
                start_obj = date.fromisoformat(str(goal_start)[:10])
                days_active = (date.today() - start_obj).days
                st.caption(
                    f"📅 **Goal started:** {start_obj.strftime('%d %B %Y')} "
                    f"({days_active} days ago) · "
                    f"**Tracking period:** {period} ({', '.join(sessions)}) · "
                    f"**Data range:** {track_str} · **Entries:** {n_entries}"
                )
            except Exception:
                st.caption(f"Tracking: {track_str} · Entries: {n_entries}")
        else:
            st.caption(f"Tracking: {track_str} · Entries: {n_entries}")

        if goal.get("archive_reason"):
            st.caption(f"Archive reason: {goal['archive_reason']}")

        # Trend / refinement alerts
        if trend == "improving":
            st.markdown(
                '<div class="success-box">📈 <b>Improving Trend:</b> Performance is getting better over time.</div>',
                unsafe_allow_html=True,
            )
        elif trend == "declining":
            st.markdown(
                '<div class="alert-box">📉 <b>Declining Trend:</b> Consider refining this goal.</div>',
                unsafe_allow_html=True,
            )
        elif trend == "stable" and needs_ref:
            st.markdown(
                '<div class="alert-box">➡️ <b>Stable but Low:</b> Consistent low performance — consider refining.</div>',
                unsafe_allow_html=True,
            )

        if streak_type and is_active:
            st.markdown(render_streak_alert(streak_type, streak_days), unsafe_allow_html=True)
            if st.button("✏️ Edit this goal in Goal Builder", key=f"streak_jump_report_{goal['id']}"):
                jump_to_edit_goal(selected_name, goal["id"])

        if goal.get("exclusion_goal"):
            st.markdown(
                f'<div class="exclusion-box">🏫 <b>Exclusion Goal:</b> {goal["exclusion_goal"]}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="smartar-box">🎯 <b>SMARTAR Goal:</b> {smartar_text}</div>',
            unsafe_allow_html=True,
        )

        if total == 0:
            st.warning("No tracking data for this goal's period yet.")
            st.markdown("---")
            continue

        # Summary metrics
        mc = st.columns(4)
        for i, lvl in enumerate(TRACK_LEVELS):
            pct = pcts.get(lvl, 0)
            mc[i].metric(f"{LEVEL_EMOJI[lvl]} {lvl}", f"{pct:.0f}%",
                         f"{counts[lvl]} sessions")

        # Progress bar
        bar_parts = []
        for lvl in LEVEL_ORDER:
            pct = pcts.get(lvl, 0)
            if pct > 0:
                bar_parts.append(
                    f'<div style="width:{pct}%;background:{LEVEL_COLOR[lvl]};'
                    f'height:22px;display:inline-block;"></div>'
                )
        st.markdown(
            '<div style="display:flex;width:100%;border-radius:8px;overflow:hidden;margin:12px 0">'
            + "".join(bar_parts) + "</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Total sessions: {total}")

        # Matplotlib chart (full SMARTAR goal as title, PNG download no clipping)
        png_bytes = make_goal_chart_mpl(
            tracking, smartar_text, actual_from, actual_to,
            student_name=selected_name,
        )
        if png_bytes:
            goal_chart_list.append((goal, png_bytes, actual_from, actual_to))
            col_chart, col_dl = st.columns([5, 1])
            with col_chart:
                st.image(png_bytes, use_container_width=True)
            with col_dl:
                safe = smartar_text[:25].replace(" ", "_").replace("/", "-")
                st.download_button(
                    "📥 Download\nPNG",
                    data=png_bytes,
                    file_name=f"{selected_name}_goal{idx}_{safe}.png",
                    mime="image/png",
                    key=f"dl_png_{goal['id']}",
                    use_container_width=True,
                )

        # Day-by-day breakdown
        if tracking:
            daily = defaultdict(lambda: {l: 0 for l in LEVEL_ORDER})
            for r in tracking:
                daily[r["session_date"]][r.get("performance_level","")] += 1
            dates_sorted = sorted(daily.keys())
            st.markdown("**Session breakdown by day:**")
            for d_str in dates_sorted[-10:]:
                row       = daily[d_str]
                day_total = sum(row.values())
                if day_total == 0:
                    continue
                day_label = datetime.strptime(d_str, "%Y-%m-%d").strftime("%d %b")
                pills     = " ".join([
                    f'<span class="metric-pill" style="background:{LEVEL_COLOR[l]}22;color:{LEVEL_COLOR[l]}">'
                    f'{LEVEL_EMOJI[l]} {l}: {row[l]}</span>'
                    for l in LEVEL_ORDER if row.get(l, 0) > 0
                ])
                st.markdown(f"**{day_label}** — {pills}", unsafe_allow_html=True)

        # AI narrative
        if groq_client:
            if st.button(f"✨ Generate Progress Summary (AI)", key=f"ai_rpt_{goal['id']}"):
                with st.spinner("Generating summary…"):
                    lvl_summary = ", ".join([f"{l}: {pcts.get(l,0):.0f}%" for l in TRACK_LEVELS])
                    trend_text  = {"improving": "improving", "declining": "declining"}.get(trend, "stable")
                    narrative   = groq_call(
                        f"""Write a professional progress summary (3–4 sentences) for a student's review meeting.

Student: {selected_name}
SMARTAR Goal: {smartar_text}
Tracking period: {from_d} to {to_d} ({n_entries} sessions recorded)
Performance: {lvl_summary}
Trend: {trend_text}

Use trauma-informed, strengths-based language referencing the BSEM framework (Regulate, Relate, Reason) where relevant. Be specific about the data. If low performance, suggest refining the goal to support achievable progress."""
                    )
                    st.markdown("**AI-Generated Progress Summary:**")
                    st.success(narrative)
        st.markdown("---")

    # PDF download all goals
    if goal_chart_list:
        st.markdown("#### 📄 Download All Goal Charts as PDF")
        if st.button("Generate PDF Report", type="primary", key="gen_pdf"):
            with st.spinner("Building PDF…"):
                pdf_bytes = make_student_pdf(selected_name, goal_chart_list)
            _ini = initials_from_name(selected_name)
            _saved = archive_document(
                source_tool="SMARTAR Goal Builder",
                doc_type="SMARTAR Goals",
                title=f"SMARTAR Progress Report — {_ini} — {datetime.now():%d %b %Y}",
                file_bytes=pdf_bytes,
                filename=f"{_ini}_SMARTAR_Progress_Report_{datetime.now():%Y%m%d}.pdf",
                student_initials=_ini,
                created_by=st.session_state.get("user_email", "unknown"),
            )
            if _saved:
                st.success(f"🗄️ Saved to {_ini}'s Document Archive folder.")
            else:
                st.error("⚠️ Could NOT save to the Document Archive — the report was NOT "
                         "filed. This is usually a database permission (RLS) issue on the "
                         "document_archive table or the document-archive storage bucket. "
                         "You can still download the PDF below, but it is not in the archive.")
            st.download_button(
                "⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"{selected_name}_SMARTAR_Progress_Report.pdf",
                mime="application/pdf",
                key="dl_pdf_final",
            )


# ══════════════════════════════════════════════════════════════════════════════
# 5. PROGRAM SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════
elif view == "🗺️ Program Snapshot":
    st.title("🗺️ Program Snapshot")
    st.caption(
        "Every active student's SMARTAR goal(s) and how consistently tracking is "
        "being entered. Expected frequency: an observation on every school day (Mon–Fri)."
    )

    students = get_students()  # active, on-placement students only
    if not students:
        st.info("No active students set up yet.")
        st.stop()

    display_mode = st.radio(
        "Display",
        ["📇 Dashboard — all students at a glance", "📋 Detailed list"],
        horizontal=True, key="snap_display_mode",
    )

    with st.spinner("Building snapshot…"):
        all_snapshots = [build_student_snapshot(s) for s in students]

    # ── Summary tiles across every program ──────────────────────────────────
    STREAK_TILE_DAYS = 4  # deliberately shorter than the 5-day revision nudge
                          # used elsewhere — an earlier, broader warning signal

    no_data_students = sorted({sn["student"] for sn in all_snapshots if sn["status"] == "not_started"})

    positive_streak_students, negative_streak_students = set(), set()
    for sn in all_snapshots:
        for gi in sn["goals"]:
            s_type, _ = check_goal_streak(gi["goal"]["id"], days=STREAK_TILE_DAYS)
            if s_type == "positive":
                positive_streak_students.add(sn["student"])
            elif s_type == "negative":
                negative_streak_students.add(sn["student"])

    silent_students = sorted({
        s["student_name"] for s in students
        if (student_school_days_silent(s) or 0) >= 2
    })

    mcols = st.columns(5)
    mcols[0].metric("🧑‍🎓 Active Students", len(students))
    mcols[1].metric("⚪ No Data Tracked", len(no_data_students))
    mcols[2].metric(f"🚀 {STREAK_TILE_DAYS}+ Days Achieving/Above", len(positive_streak_students))
    mcols[3].metric(f"📉 {STREAK_TILE_DAYS}+ Days Below/Not Yet", len(negative_streak_students))
    mcols[4].metric("⚠️ 2+ Days No Data Entered", len(silent_students))

    no_goal_students = sorted(sn["student"] for sn in all_snapshots if sn["status"] == "no_goal")
    if no_goal_students:
        st.caption(f"ℹ️ {len(no_goal_students)} student(s) have no SMARTAR goal set yet: "
                  f"{', '.join(no_goal_students)}.")

    # ── Who's behind each tile — a bare count isn't actionable on its own ──
    if no_data_students or positive_streak_students or negative_streak_students or silent_students:
        with st.expander("👀 Who's in each tile above"):
            if no_data_students:
                st.markdown(f"**⚪ No data tracked:** {', '.join(no_data_students)}")
            if positive_streak_students:
                st.markdown(f"**🚀 {STREAK_TILE_DAYS}+ days achieving/above:** "
                           f"{', '.join(sorted(positive_streak_students))}")
            if negative_streak_students:
                st.markdown(f"**📉 {STREAK_TILE_DAYS}+ days below/not yet:** "
                           f"{', '.join(sorted(negative_streak_students))}")
            if silent_students:
                st.markdown(f"**⚠️ 2+ days no data entered:** {', '.join(silent_students)}")

    # ── Attendance-matching diagnostic — so a silent name/program mismatch
    # with the Behaviour Support Tool is visible, not just a wrong number ──
    matched, unmatched = attendance_match_coverage(students)
    if matched:
        cap = f"🔗 Attendance from the Behaviour Support Tool is linked for {len(matched)}/{len(students)} student(s) — excused (absent / no school) days are excluded from their expected tracking days."
        if unmatched:
            cap += f" Not linked for: {', '.join(unmatched)} (check the first name matches exactly, incl. program, in both tools)."
        st.caption(cap)
    else:
        st.caption(
            "ℹ️ No students could be matched to the Behaviour Support Tool's attendance records yet "
            "(so absence days aren't currently excluded from expected tracking days — everything below "
            "assumes every school day as before)."
        )

    st.markdown("---")

    if display_mode.startswith("📇"):
        # ── DASHBOARD — KPI tiles, trend charts, engagement funnel, table,
        # and a drill-down panel, one tab per program ─────────────────────
        tabs = st.tabs(PROGRAMS)
        for tab, prog in zip(tabs, PROGRAMS):
            with tab:
                prog_snaps = sorted(
                    [sn for sn in all_snapshots if sn["program"] == prog],
                    key=lambda sn: (SNAPSHOT_SEVERITY[sn["status"]], sn["student"]),
                )
                if not prog_snaps:
                    st.info(f"No active students in {prog}.")
                    continue

                # One bulk query for every goal in this program, instead of
                # one query per goal.
                prog_goal_ids = [gi["goal"]["id"] for sn in prog_snaps for gi in sn["goals"]]
                window_to     = date.today()
                window_from   = window_to - timedelta(days=27)  # ~4 weeks of chart history
                prog_tracking = get_tracking_for_goals(
                    prog_goal_ids, window_from.isoformat(), window_to.isoformat()
                )

                # ── KPI tiles ────────────────────────────────────────────
                total_students  = len(prog_snaps)
                goals_tracked   = sum(sn["goal_count"] for sn in prog_snaps)
                on_track_n      = sum(1 for sn in prog_snaps if sn["status"] == "on_track")
                attention_n     = total_students - on_track_n
                all_consistency = [gi["freq"]["consistency_pct"]
                                   for sn in prog_snaps for gi in sn["goals"]]
                avg_consistency = round(sum(all_consistency) / len(all_consistency)) if all_consistency else 0

                this_week_from = (window_to - timedelta(days=6)).isoformat()
                last_week_from = (window_to - timedelta(days=13)).isoformat()
                last_week_to   = (window_to - timedelta(days=7)).isoformat()
                entries_this_week = sum(1 for r in prog_tracking if r["session_date"] >= this_week_from)
                entries_last_week = sum(1 for r in prog_tracking
                                        if last_week_from <= r["session_date"] <= last_week_to)
                if entries_last_week:
                    wow = round((entries_this_week - entries_last_week) / entries_last_week * 100)
                    wow_str = f"{'+' if wow >= 0 else ''}{wow}% vs last week"
                else:
                    wow_str = "No data last week"

                kpis = [
                    ("ACTIVE STUDENTS",   str(total_students),            f"in {prog}",
                     "#1d6fa4", "#134e7a"),
                    ("GOALS TRACKED",     str(goals_tracked),             "active SMARTAR goals",
                     "#7c3aed", "#5b21b6"),
                    ("ENTRIES THIS WEEK", str(entries_this_week),         wow_str,
                     "#0891b2", "#0e7490"),
                    ("AVG CONSISTENCY",   f"{avg_consistency}%",          "last 14 school days",
                     "#16a34a", "#166534"),
                    ("ON TRACK",          f"{on_track_n}/{total_students}", "meeting expected frequency",
                     "#ca8a04", "#92400e"),
                    ("NEEDS ATTENTION",   str(attention_n),               "below expected / not started",
                     "#dc2626", "#991b1b"),
                ]
                kpi_cols = st.columns(6)
                for col, (label, value, sub, c1, c2) in zip(kpi_cols, kpis):
                    with col:
                        st.markdown(render_kpi_tile(label, value, sub, c1, c2), unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Program trends — tucked into an expander so the student
                # tiles below are the main focus of the page ───────────────
                with st.expander("📈 Program Trends & Engagement Funnel"):
                    ts_df = program_time_series(prog_tracking, window_from, window_to)
                    cchart1, cchart2 = st.columns(2)
                    with cchart1:
                        st.plotly_chart(fig_entries_line(ts_df), use_container_width=True,
                                        key=f"entries_chart_{prog}")
                    with cchart2:
                        st.plotly_chart(fig_score_line(ts_df), use_container_width=True,
                                        key=f"score_chart_{prog}")
                    funnel_counts = program_funnel_counts(prog_snaps)
                    st.plotly_chart(fig_engagement_funnel(funnel_counts), use_container_width=True,
                                    key=f"funnel_chart_{prog}")

                tracking_by_goal = defaultdict(list)
                for r in prog_tracking:
                    tracking_by_goal[r["goal_id"]].append(r)

                # ── Student tile grid — one tile per active student, coloured ──
                # as a tracking-consistency alert (green/amber/red/grey). Click
                # a tile's button to open that student's goal charts below,
                # side by side.
                st.markdown("#### 👥 Active Students")
                st.caption(
                    "🟢 On track · 🟠 Needs increase · 🔴 Not started · ⚪ No goal set — "
                    "click a tile to view that student's goal charts."
                )

                selected_key = f"snap_selected_{prog}"
                TILE_COLS = 4
                for row_start in range(0, len(prog_snaps), TILE_COLS):
                    row = prog_snaps[row_start:row_start + TILE_COLS]
                    tile_cols = st.columns(TILE_COLS)
                    for col, sn in zip(tile_cols, row):
                        with col:
                            st.markdown(render_student_tile(sn), unsafe_allow_html=True)
                            is_open = st.session_state.get(selected_key) == sn["student"]
                            if st.button(
                                "✖ Close" if is_open else "🔍 View Goals",
                                key=f"tile_btn_{prog}_{sn['student']}",
                                use_container_width=True,
                                type="primary" if is_open else "secondary",
                            ):
                                st.session_state[selected_key] = None if is_open else sn["student"]
                                st.rerun()

                # ── Detail panel for the selected student — every one of their
                # goals, charts side by side ────────────────────────────────
                selected_student = st.session_state.get(selected_key)
                if selected_student:
                    sel_snap = next((sn for sn in prog_snaps if sn["student"] == selected_student), None)
                    if sel_snap:
                        st.markdown("---")
                        sel_emoji, sel_label, sel_color = SNAPSHOT_STATUS_META[sel_snap["status"]]
                        st.markdown(
                            f'<div style="font-size:1.25rem;font-weight:700;color:#1f2937;">'
                            f'📂 {selected_student} '
                            f'<span style="color:{sel_color};font-size:0.8rem;font-weight:700;">'
                            f'{sel_emoji} {sel_label}</span></div>',
                            unsafe_allow_html=True,
                        )
                        if not sel_snap["goals"]:
                            st.info(f"{selected_student} doesn't have a SMARTAR goal yet. "
                                    "Go to **Goal Builder** to create one.")
                        else:
                            MAX_DETAIL_COLS = 3
                            goal_list = sel_snap["goals"]
                            for gchunk_start in range(0, len(goal_list), MAX_DETAIL_COLS):
                                gchunk = goal_list[gchunk_start:gchunk_start + MAX_DETAIL_COLS]
                                detail_cols = st.columns(len(gchunk))
                                for col, gi in zip(detail_cols, gchunk):
                                    g, freq = gi["goal"], gi["freq"]
                                    g_emoji, g_label, g_color = SNAPSHOT_STATUS_META[freq["status"]]
                                    streak_type, streak_days = check_goal_streak(g["id"])
                                    with col:
                                        with st.container(border=True):
                                            st.markdown(
                                                f'<div class="smartar-box">🎯 {g.get("smartar_goal","No goal text")} '
                                                f'<span style="float:right;color:{g_color};font-weight:700;'
                                                f'font-size:0.8rem;">{g_emoji} {g_label}</span></div>',
                                                unsafe_allow_html=True,
                                            )
                                            if streak_type:
                                                st.markdown(render_streak_alert(streak_type, streak_days),
                                                           unsafe_allow_html=True)
                                                if st.button("✏️ Edit this goal",
                                                            key=f"streak_jump_tile_{g['id']}"):
                                                    jump_to_edit_goal(selected_student, g["id"])

                                            mc1, mc2 = st.columns(2)
                                            mc1.metric("Last entry", freq["last_entry"].strftime("%d %b")
                                                      if freq["last_entry"] else "Never")
                                            mc2.metric("Consistency", f"{freq['consistency_pct']}%")
                                            if freq.get("excused_in_window"):
                                                st.caption(f"📅 {freq['excused_in_window']} absence/no-school "
                                                          f"day(s) excluded from the last 14 school days.")

                                            # Reuses the bulk program-wide query
                                            # fetched above — no extra DB round trip.
                                            detail_fig = fig_goal_detail_chart(tracking_by_goal.get(g["id"], []))
                                            if detail_fig:
                                                st.plotly_chart(detail_fig, use_container_width=True,
                                                                key=f"detail_chart_{g['id']}")
                                            else:
                                                st.caption("No observations recorded yet for this goal.")

    else:
        # ── DETAILED LIST — same data, drill into each goal ─────────────────
        prog_filter = st.selectbox("Filter by Program", ["All"] + PROGRAMS, index=0,
                                   key="snap_prog_filter")
        status_filter = st.multiselect(
            "Show only",
            options=list(SNAPSHOT_STATUS_META.keys()),
            default=list(SNAPSHOT_STATUS_META.keys()),
            format_func=lambda k: f"{SNAPSHOT_STATUS_META[k][0]} {SNAPSHOT_STATUS_META[k][1]}",
            key="snap_status_filter",
        )

        visible = sorted(
            [sn for sn in all_snapshots
             if (prog_filter == "All" or sn["program"] == prog_filter)
             and sn["status"] in status_filter],
            key=lambda sn: (sn["program"], sn["student"]),
        )
        if not visible:
            st.info("No students match the selected filters.")
            st.stop()

        current_program = None
        for snap in visible:
            if snap["program"] != current_program:
                current_program = snap["program"]
                st.markdown(f"### {current_program} Program")

            emoji, label, color = SNAPSHOT_STATUS_META[snap["status"]]

            if not snap["goals"]:
                st.markdown(
                    f'<div style="border-left:4px solid {color};padding:8px 14px;margin-bottom:8px;'
                    f'background:#fafafa;border-radius:0 8px 8px 0;">'
                    f'<b>{snap["student"]}</b> — {emoji} {label}'
                    f'<div style="font-size:0.82rem;color:#666;">'
                    f'No SMARTAR goal has been created for this student yet.</div></div>',
                    unsafe_allow_html=True,
                )
                continue

            with st.expander(
                f"{emoji} **{snap['student']}** — {label}  ·  "
                f"{snap['goal_count']} goal{'s' if snap['goal_count'] != 1 else ''}"
            ):
                for gi in snap["goals"]:
                    g, freq = gi["goal"], gi["freq"]
                    g_emoji, g_label, g_color = SNAPSHOT_STATUS_META[freq["status"]]
                    last_entry_str = freq["last_entry"].strftime("%d %b") if freq["last_entry"] else "Never"

                    tracking_21          = get_tracking(g["id"], days=21)
                    _, total_21, pcts_21 = calc_percentages(tracking_21)
                    perf_summary = (
                        "  ".join(f"{LEVEL_EMOJI[l]} {pcts_21.get(l,0):.0f}%"
                                  for l in TRACK_LEVELS if pcts_21.get(l, 0) > 0)
                        if total_21 else "No performance data yet"
                    )

                    st.markdown(
                        f'<div class="smartar-box">🎯 {g.get("smartar_goal","No goal text")} '
                        f'<span style="float:right;color:{g_color};font-weight:700;font-size:0.8rem;">'
                        f'{g_emoji} {g_label}</span></div>',
                        unsafe_allow_html=True,
                    )
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.metric("Last entry", last_entry_str)
                    fc2.metric("Consistency (14 days)", f"{freq['consistency_pct']}%")
                    fc3.metric("Tracking period", g.get("tracking_period", "All Day"))
                    st.caption(f"Performance (last 21 days): {perf_summary}")
                    if freq.get("excused_in_window"):
                        st.caption(f"📅 {freq['excused_in_window']} absence/no-school day(s) "
                                  f"excluded from the last 14 school days.")

                    if freq["status"] == "needs_increase":
                        st.markdown(
                            '<div class="alert-box">⚠️ Tracking has fallen behind — an entry is '
                            'expected every school day. Please follow up with the staff recording '
                            'for this student.</div>',
                            unsafe_allow_html=True,
                        )
                    elif freq["status"] == "not_started":
                        st.markdown(
                            '<div class="alert-box">🔴 No tracking has been entered for this goal yet.</div>',
                            unsafe_allow_html=True,
                        )

                    streak_type, streak_days = check_goal_streak(g["id"])
                    if streak_type:
                        st.markdown(render_streak_alert(streak_type, streak_days), unsafe_allow_html=True)
                        if st.button("✏️ Edit this goal in Goal Builder",
                                    key=f"streak_jump_snaplist_{g['id']}"):
                            jump_to_edit_goal(snap["student"], g["id"])

                    st.markdown("<hr style='margin:8px 0;border:none;border-top:1px solid #eee;'>",
                               unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 6. ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
elif view == "⚙️ Admin Panel":
    st.title("⚙️ Admin Panel")
    st.caption("Manage students · Pre-populate goals from entry meetings · Edit existing goals")

    tab_students, tab_edit, tab_prepop, tab_alerts = st.tabs([
        "👥 Manage Students", "📝 Edit Goals", "➕ Pre-populate Goals", "✉️ Teacher Alerts",
    ])

    # -- Manage Students --------------------------------------------------------
    with tab_students:
        st.subheader("Add New Student")
        col1, col2, col3 = st.columns([3, 1, 1])
        new_sname = col1.text_input("Student name", key="admin_new_student")
        new_sprog = col2.selectbox("Program", PROGRAMS, key="admin_new_prog")
        if col3.button("Add Student", type="primary", key="admin_add_student"):
            if new_sname.strip():
                try:
                    sb.table("smartar_students").insert({
                        "student_name":    new_sname.strip(),
                        "program":         new_sprog,
                        "active":          True,
                        "placement_ended": False,
                    }).execute()
                    st.success(f"Added {new_sname.strip()} to {new_sprog}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a student name.")

        st.markdown("---")
        st.subheader("🗑️ Bulk Archive / End Placement")
        st.caption(
            "Select several students at once — handy when a term ends and a batch "
            "of placements finish together. This only changes the student's status; "
            "their goals and tracking history are kept."
        )

        bulk_candidates = [
            s for s in get_students(include_archived=True)
            if s.get("active", True) and not s.get("placement_ended", False)
        ]
        if not bulk_candidates:
            st.caption("No active students available to archive.")
        else:
            bulk_prog_filter = st.selectbox(
                "Filter by program (optional)", ["All"] + PROGRAMS, key="bulk_prog_filter"
            )
            bulk_pool = bulk_candidates
            if bulk_prog_filter != "All":
                bulk_pool = [s for s in bulk_pool if s.get("program") == bulk_prog_filter]

            bulk_names = sorted(s["student_name"] for s in bulk_pool)
            selected_bulk = st.multiselect(
                "Select students", bulk_names, key="bulk_select_students",
                help="Only currently active (on-placement) students are listed here.",
            )

            bulk_action = st.radio(
                "Action to apply",
                ["Archive (goal archived — still accessible in Admin)",
                 "End Placement (student has left CLC — hidden everywhere, data kept)"],
                key="bulk_action_choice",
            )
            is_end_action = bulk_action.startswith("End")

            if selected_bulk:
                if not st.session_state.get("confirm_bulk_action"):
                    if st.button(f"⚙️ Apply to {len(selected_bulk)} student(s)",
                                 type="primary", key="bulk_apply_btn"):
                        st.session_state["confirm_bulk_action"] = True
                        st.rerun()
                else:
                    st.warning(
                        f"This will set **{len(selected_bulk)}** student(s) to "
                        f"**{'Placement Ended' if is_end_action else 'Archived'}**: "
                        f"{', '.join(selected_bulk)}. Continue?"
                    )
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ Confirm", type="primary", key="bulk_confirm_btn",
                                     use_container_width=True):
                            target_ids = [s["id"] for s in bulk_pool
                                          if s["student_name"] in selected_bulk]
                            update = {"active": False}
                            if is_end_action:
                                update["placement_ended"] = True
                            ok_count, fail_count = 0, 0
                            for sid in target_ids:
                                try:
                                    sb.table("smartar_students").update(update).eq("id", sid).execute()
                                    ok_count += 1
                                except Exception:
                                    fail_count += 1
                            st.session_state.pop("confirm_bulk_action", None)
                            if fail_count:
                                st.warning(f"Updated {ok_count} student(s) — {fail_count} failed.")
                            else:
                                st.success(f"✅ Updated {ok_count} student(s).")
                            st.rerun()
                    with cc2:
                        if st.button("Cancel", key="bulk_cancel_btn", use_container_width=True):
                            st.session_state.pop("confirm_bulk_action", None)
                            st.rerun()

        st.markdown("---")
        st.caption("Active = on placement. Archived = goal archived, student still accessible. Placement Ended = student left CLC, hidden from tools but data preserved.")

        col_show1, col_show2 = st.columns(2)
        show_archived  = col_show1.checkbox("Show archived students", value=False)
        show_placement = col_show2.checkbox("Show placement-ended students", value=False)

        students_all = get_students(include_archived=True)
        active_s   = [s for s in students_all
                      if s.get("active", True) and not s.get("placement_ended", False)]
        archived_s = [s for s in students_all
                      if not s.get("active", True) and not s.get("placement_ended", False)]
        ended_s    = [s for s in students_all if s.get("placement_ended", False)]

        st.info(
            f"{len(active_s)} active"
            + (f"  |  {len(archived_s)} goal-archived" if show_archived else "")
            + (f"  |  {len(ended_s)} placement ended" if show_placement else "")
        )

        display_students = list(active_s)
        if show_archived:
            display_students += archived_s
        if show_placement:
            display_students += ended_s

        def _s_label(s):
            if s.get("placement_ended", False): return s["student_name"] + " [PLACEMENT ENDED]"
            if not s.get("active", True): return s["student_name"] + " [ARCHIVED]"
            return s["student_name"]

        snames = [_s_label(s) for s in display_students]
        sel_s  = st.selectbox("Select student to manage", ["-- Select --"] + snames,
                              key="admin_edit_select")

        if sel_s != "-- Select --":
            clean   = sel_s.replace(" [ARCHIVED]", "").replace(" [PLACEMENT ENDED]", "")
            s       = next(x for x in display_students if x["student_name"] == clean)
            is_end  = s.get("placement_ended", False)
            is_arch = not s.get("active", True) and not is_end

            goals_s = get_goals(s["student_name"])
            status_tag = " [PLACEMENT ENDED]" if is_end else " [ARCHIVED]" if is_arch else ""
            st.markdown(f"### {s['student_name']}{status_tag}")
            st.caption(f"Program: {s.get('program','--')} · {len(goals_s)} active goals")

            if not is_arch and not is_end:
                c1, c2 = st.columns([2, 1])
                prog_idx   = PROGRAMS.index(s.get("program","JP")) if s.get("program") in PROGRAMS else 0
                new_prog_s = c1.selectbox("Program", PROGRAMS, index=prog_idx,
                                          key=f"prog_{s['id']}")
                if c2.button("Update Program", key=f"prog_upd_{s['id']}"):
                    sb.table("smartar_students").update({"program": new_prog_s}).eq("id", s["id"]).execute()
                    st.success("Updated.")
                    st.rerun()

            st.markdown("---")

            if is_end:
                st.warning("This student has left CLC. All data is preserved.")
                if st.button("Restore to Active", key=f"restore_end_{s['id']}", type="primary"):
                    sb.table("smartar_students").update({"active": True, "placement_ended": False}).eq("id", s["id"]).execute()
                    st.success("Restored to active.")
                    st.rerun()

            elif is_arch:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Restore to Active", key=f"restore_s_{s['id']}", type="primary"):
                        sb.table("smartar_students").update({"active": True}).eq("id", s["id"]).execute()
                        st.success("Restored.")
                        st.rerun()
                with c2:
                    if st.button("Mark Placement Ended", key=f"end_s_{s['id']}"):
                        sb.table("smartar_students").update({"active": False, "placement_ended": True}).eq("id", s["id"]).execute()
                        st.success("Marked as placement ended.")
                        st.rerun()

            else:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"Archive {s['student_name']}", key=f"archive_s_{s['id']}"):
                        sb.table("smartar_students").update({"active": False}).eq("id", s["id"]).execute()
                        st.success("Archived — still accessible in Admin.")
                        st.rerun()
                with c2:
                    if st.button("End Placement", key=f"end_active_{s['id']}"):
                        st.session_state[f"confirm_end_{s['id']}"] = True
                if st.session_state.get(f"confirm_end_{s['id']}"):
                    st.warning(f"This will hide {s['student_name']} from all tools. All data preserved. Continue?")
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("Confirm End Placement", key=f"end_conf_{s['id']}", type="primary"):
                            sb.table("smartar_students").update({"active": False, "placement_ended": True}).eq("id", s["id"]).execute()
                            st.session_state.pop(f"confirm_end_{s['id']}", None)
                            st.success(f"{s['student_name']} marked as placement ended.")
                            st.rerun()
                    with cb:
                        if st.button("Cancel", key=f"end_cancel_{s['id']}"):
                            st.session_state.pop(f"confirm_end_{s['id']}", None)
                            st.rerun()
    # ── Edit Goals ────────────────────────────────────────────────────────────
    with tab_edit:
        st.subheader("Edit Existing Goals")
        students_e = get_students()
        if not students_e:
            st.info("No students in the system yet.")
        else:
            sel_e  = st.selectbox("Select student", [s["student_name"] for s in students_e],
                                  key="admin_edit_student")
            goals_e = get_all_goals_for_student(sel_e)

            if not goals_e:
                st.info(f"No goals for {sel_e}. Use Pre-populate Goals to create initial goals.")
            else:
                for idx, goal in enumerate(goals_e, 1):
                    is_active_g = goal.get("active", True)
                    status_g    = "Active" if is_active_g else "Archived"
                    label       = (f"[{status_g}] Goal {idx} — "
                                   f"{_short(goal.get('smartar_goal',''), 55)}")

                    with st.expander(label, expanded=False):
                        edit_excl = st.text_area(
                            "Exclusion Goal", value=goal.get("exclusion_goal", ""),
                            height=80, key=f"edit_excl_{goal['id']}",
                        )
                        edit_smartar = st.text_area(
                            "SMARTAR Goal", value=goal.get("smartar_goal", ""),
                            height=100, key=f"edit_smt_{goal['id']}",
                        )
                        edit_period = st.selectbox(
                            "Tracking Period", TRACKING_PERIODS,
                            index=TRACKING_PERIODS.index(goal.get("tracking_period","All Day"))
                              if goal.get("tracking_period") in TRACKING_PERIODS else 0,
                            key=f"edit_per_{goal['id']}",
                        )

                        dc1, dc2 = st.columns(2)
                        cur_start = goal.get("start_date")
                        try:
                            cur_start_d = date.fromisoformat(str(cur_start)[:10]) if cur_start else date.today()
                        except Exception:
                            cur_start_d = date.today()
                        edit_start = dc1.date_input(
                            "Start Date (update when refining goal)",
                            value=cur_start_d, key=f"edit_start_{goal['id']}",
                        )
                        days_tracked = (date.today() - cur_start_d).days
                        dc2.metric("Days Tracked", f"{days_tracked} days")

                        st.markdown("**GAS Performance Levels:**")
                        edit_gas = {}
                        for lvl in LEVEL_ORDER:
                            col_name = f"gas_{lvl.lower().replace(' ','_')}"
                            edit_gas[lvl] = st.text_area(
                                f"{LEVEL_EMOJI[lvl]} {lvl}",
                                value=goal.get(col_name, ""),
                                height=70, key=f"edit_gas_{lvl}_{goal['id']}",
                            )

                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("💾 Save Changes", key=f"save_e_{goal['id']}", type="primary"):
                                update = {
                                    "exclusion_goal":  edit_excl.strip() or None,
                                    "smartar_goal":    edit_smartar.strip(),
                                    "tracking_period": edit_period,
                                    "start_date":      edit_start.isoformat(),
                                    "gas_exceeding":   edit_gas.get("EXCEEDING",""),
                                    "gas_above":       edit_gas.get("ABOVE",""),
                                    "gas_expected":    edit_gas.get("EXPECTED",""),
                                    "gas_below":       edit_gas.get("BELOW",""),
                                    "gas_not_yet":     edit_gas.get("NOT YET",""),
                                    "updated_at":      datetime.utcnow().isoformat(),
                                }
                                sb.table("smartar_goals").update(update)\
                                  .eq("id", goal["id"]).execute()
                                st.success("✅ Goal updated.")
                                st.rerun()
                        with c2:
                            if is_active_g:
                                if st.button("🗃️ Archive", key=f"arch_e_{goal['id']}"):
                                    st.session_state[f"arch_e_c_{goal['id']}"] = True
                                if st.session_state.get(f"arch_e_c_{goal['id']}"):
                                    reason_e = st.text_input("Reason:", key=f"arch_e_r_{goal['id']}")
                                    if st.button("Confirm", key=f"arch_e_d_{goal['id']}", type="primary"):
                                        archive_goal(goal["id"], reason_e)
                                        st.session_state.pop(f"arch_e_c_{goal['id']}", None)
                                        st.rerun()
                            else:
                                if st.button("♻️ Restore", key=f"restore_e_{goal['id']}"):
                                    restore_goal(goal["id"])
                                    st.rerun()
                        with c3:
                            if not is_active_g:
                                if st.button("➕ New Goal (same student)",
                                             key=f"new_from_e_{goal['id']}"):
                                    st.info("Go to **Goal Builder** to create an updated goal "
                                            f"for {sel_e}.")

    # ── Pre-populate Goals ─────────────────────────────────────────────────────
    with tab_prepop:
        st.subheader("Pre-populate Goals from Entry Meeting")
        st.caption(
            "Add initial goals after an entry meeting so teachers can begin tracking "
            "straight away. Goals can be refined later as teachers observe the student."
        )
        students_p = get_students()
        if not students_p:
            st.info("Add students in Manage Students tab first.")
        else:
            sel_p   = st.selectbox("Select student", [s["student_name"] for s in students_p],
                                   key="admin_pp_student")
            goals_p = get_goals(sel_p)
            if goals_p:
                st.info(f"{sel_p} already has {len(goals_p)} active goal(s). You can add more below.")

            pp_excl = st.text_area(
                "🏫 Exclusion Goal (from main school)",
                placeholder="Paste exclusion goal from entry meeting…",
                height=80, key="pp_excl",
            )
            pp_smartar = st.text_area(
                "🎯 Initial SMARTAR Goal",
                placeholder="Enter initial SMARTAR goal — teachers can refine based on observations.",
                height=100, key="pp_smartar",
            )
            pp_period = st.selectbox("Tracking Period", TRACKING_PERIODS, key="pp_period")

            st.markdown("**Optional: Add GAS Performance Levels**")
            with st.expander("Add GAS Levels (can be done later)"):
                pp_gas = {}
                for lvl in LEVEL_ORDER:
                    pp_gas[lvl] = st.text_area(
                        f"{LEVEL_EMOJI[lvl]} {lvl}",
                        placeholder=f"{lvl} performance description…",
                        height=65, key=f"pp_gas_{lvl}",
                    )

            if st.button("💾 Save Pre-Populated Goal", type="primary", key="save_pp"):
                if pp_smartar.strip():
                    new_g = {
                        "student_name":    sel_p,
                        "exclusion_goal":  pp_excl.strip() or None,
                        "smartar_goal":    pp_smartar.strip(),
                        "tracking_period": pp_period,
                        "gas_exceeding":   pp_gas.get("EXCEEDING",""),
                        "gas_above":       pp_gas.get("ABOVE",""),
                        "gas_expected":    pp_gas.get("EXPECTED",""),
                        "gas_below":       pp_gas.get("BELOW",""),
                        "gas_not_yet":     pp_gas.get("NOT YET",""),
                        "start_date":      date.today().isoformat(),
                        "active":          True,
                        "status":          "Active",
                    }
                    sb.table("smartar_goals").insert(new_g).execute()
                    st.success(
                        f"✅ Goal pre-populated for {sel_p}. "
                        "Teachers can now begin tracking and refine as needed."
                    )
                    st.rerun()
                else:
                    st.warning("Please enter a SMARTAR goal.")

    # -- Teacher Alerts -----------------------------------------------------
    with tab_alerts:
        st.subheader("✉️ Teacher Email Reminders")
        st.caption(
            "If an active student has gone 2+ school days with no tracking data "
            "entered for any of their goals, a reminder email goes to the teacher "
            "mapped to that student's program."
        )

        if not email_is_configured():
            st.warning(
                "📪 Email isn't set up yet on this deployment. This uses the same sending "
                "route as the **Hazard Report** and **Credit Card** tools — the CLC Gmail "
                "account (`clc.digitalstaffmeeting@gmail.com`) via the `EMAIL_WEBHOOK_URL` "
                "Apps Script route (or Gmail SMTP as a fallback). If those tools' email "
                "alerts already work, this should too with nothing extra to configure — "
                "if not, it needs the same Render secrets they use. Until then, checks "
                "below will run but nothing will actually be emailed."
            )
        else:
            st.caption("✅ Email is configured — using the same CLC Gmail route as Hazard Report / Credit Card.")

        with st.expander("⚙️ One-time setup — database table"):
            st.caption(
                "Teacher emails and the daily alert log are stored in Supabase. "
                "If this is the first time using this tab, run this once in your "
                "Supabase SQL editor:"
            )
            st.code(SMARTAR_SETTINGS_SQL, language="sql")

        st.markdown("---")
        st.markdown("**Teacher email per program**")
        st.caption("You can list more than one address per program, separated by commas.")
        current_emails = get_teacher_emails()
        ecols = st.columns(3)
        new_emails = {}
        for ecol, prog in zip(ecols, PROGRAMS):
            new_emails[prog] = ecol.text_input(
                f"{prog} teacher email", value=current_emails.get(prog, ""),
                key=f"teacher_email_{prog}", placeholder="name@school..., name2@school...",
            )
        if st.button("💾 Save teacher emails", key="save_teacher_emails"):
            if set_teacher_emails(new_emails):
                st.success("✅ Teacher emails saved.")
                st.rerun()

        st.markdown("---")
        st.markdown("**Check now**")
        st.caption(
            "This also runs automatically once a day — the first time anyone opens "
            "this app that day — so reminders still go out even if no one visits "
            "this tab. Use the buttons below to check on demand or confirm it's working. "
            "A student is only ever emailed about once per calendar day."
        )

        students_a = get_students()
        acol1, acol2 = st.columns(2)
        with acol1:
            if st.button("🔍 Preview (no emails sent)", key="alert_preview"):
                st.session_state["alert_check_results"] = run_teacher_alert_check(students_a, dry_run=True)
        with acol2:
            if st.button("📧 Check & Send Reminders Now", type="primary", key="alert_send_now"):
                st.session_state["alert_check_results"] = run_teacher_alert_check(students_a, dry_run=False)

        alert_results = st.session_state.get("alert_check_results")
        if alert_results is not None:
            if not alert_results:
                st.success("✅ No active students currently have 2+ school days of silence.")
            else:
                st.dataframe(
                    pd.DataFrame(alert_results)[
                        ["student", "program", "days_silent", "teacher_email", "sent", "note"]
                    ].rename(columns={
                        "student": "Student", "program": "Program",
                        "days_silent": "School days silent", "teacher_email": "Teacher email",
                        "sent": "Sent", "note": "Note",
                    }),
                    use_container_width=True, hide_index=True,
                )
