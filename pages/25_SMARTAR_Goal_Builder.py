import streamlit as st
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO
from supabase import create_client
from groq import Groq
from urllib.parse import unquote
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
    return {
        "active":     return_to == "team_meetings",
        "student":    unquote(student_param) if student_param else None,
        "meeting_id": int(meeting_id_param) if meeting_id_param else None,
        "program":    program_param,
        "term":       term_param,
        "week":       int(week_param) if week_param else None,
    }

integration = check_team_meetings_integration()

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

@st.cache_resource
def get_groq():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)

groq_client = get_groq()

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
    if not groq_client:
        return "[AI unavailable — Groq API key not configured]"
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": prompt}],
        max_tokens=800,
    )
    return resp.choices[0].message.content.strip()


def ai_check_period(smartar_goal: str) -> dict:
    """Ask Groq to determine appropriate tracking period for a goal."""
    if not groq_client:
        return {"period": "All Day", "reasoning": "AI unavailable.", "confidence": "Low"}
    prompt = f"""You are an educational support specialist for students in alternative education.

Analyse this SMARTAR goal and determine the most appropriate tracking period within the school day.

Goal: {smartar_goal}

School sessions:
- Morning (~9am–11am): literacy, numeracy, structured academic learning
- Middle (~11am–1pm): recess, lunch, social time, transitions
- Afternoon (~1pm–3pm): specialist subjects, projects, outdoor education

Return ONLY valid JSON, nothing else:
{{
  "period": "All Day" | "Morning Only" | "Middle Only" | "Afternoon Only" | "Morning & Middle" | "Middle & Afternoon",
  "reasoning": "One concise sentence explaining why",
  "confidence": "High" | "Medium" | "Low"
}}

Use "All Day" unless the goal text CLEARLY references a specific time context (e.g., 'morning literacy', 'at lunch', 'during afternoon session')."""
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.1,
        )
        result = json.loads(resp.choices[0].message.content.strip())
        if result.get("period") not in TRACKING_PERIODS:
            result["period"] = "All Day"
        return result
    except Exception:
        return {"period": "All Day", "reasoning": "AI check unavailable.", "confidence": "Low"}


# ── Supabase helpers ───────────────────────────────────────────────────────────
def get_students(include_archived=False):
    def _fn(c):
        q = c.table("smartar_students").select("*").order("student_name")
        if not include_archived:
            q = q.eq("active", True)
        return q.execute().data or []
    try:
        result = _q(_fn)
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
    meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
    st.sidebar.markdown(f"""
    <a href="{meeting_url}" style="display:block;text-align:center;background:#7c3aed;color:white;
    font-weight:600;font-size:0.85rem;padding:0.5rem;border-radius:8px;text-decoration:none;
    margin-bottom:0.5rem;">← Back to Team Meeting</a>
    """, unsafe_allow_html=True)

view = st.sidebar.radio(
    "View",
    ["🏫 Class Dashboard", "🆕 New Student Setup", "📋 Goal Builder",
     "👩‍💼 Leadership Dashboard",
     "📊 Daily Tracking", "📈 Progress Report", "⚙️ Admin Panel"],
)
st.sidebar.markdown("---")
st.sidebar.caption("SMARTAR + GAS Goal Tracking · CLC LBU")


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
# 2. NEW STUDENT SETUP  (leadership)
# ══════════════════════════════════════════════════════════════════════════════
elif view == "🆕 New Student Setup":
    st.title("🆕 New Student Setup")
    st.caption(
        "Complete this form when a new student is admitted to set up their student record, "
        "record the exclusion goal from their home school, and enter the initial entry SMARTAR goal. "
        "Teachers will then see this information in the Goal Builder."
    )

    st.markdown(
        '<div class="admin-panel">'
        '🔒 <b>Leadership / Coordinator use</b> — this section creates the student record and '
        'entry-level documentation. Teachers build and refine goals from the Goal Builder tab.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Step 1: Student details ───────────────────────────────────────────────
    st.subheader("Step 1 — Student Details")
    ns_c1, ns_c2 = st.columns([3, 1])
    ns_name = ns_c1.text_input(
        "Student first name (as it will appear in all goals)",
        placeholder="e.g. Jordan",
        key="ns_name",
    )
    ns_prog = ns_c2.selectbox("Program", PROGRAMS, key="ns_prog")

    # Check for duplicate
    _existing_students = get_students()
    _existing_names    = [s["student_name"].lower() for s in _existing_students]
    if ns_name.strip() and ns_name.strip().lower() in _existing_names:
        st.warning(
            f"⚠️ A student named **{ns_name.strip()}** already exists in the system. "
            f"Go to Goal Builder to view and manage their goals."
        )

    # ── Step 2: Entry Goals (exclusion + SMARTAR pairs) ───────────────────────
    st.markdown("---")
    st.subheader("Step 2 — Entry Goals")
    st.caption(
        "Enter one goal pair per behaviour of concern. Each pair is an **Exclusion Goal** from "
        "the home school (the reason for referral) and the **Entry SMARTAR Goal** — the replacement "
        "behaviour teachers will work toward. Add as many pairs as needed."
    )

    # Initialise paired goal list in session state
    if "ns_goal_list" not in st.session_state:
        st.session_state["ns_goal_list"] = [{"excl": "", "smartar": "", "id": 0}]

    # AI drafter — stages a goal into a chosen slot's smartar field
    if groq_client:
        with st.expander("✨ AI Goal Drafter — describe a behaviour, get a draft SMARTAR goal", expanded=False):
            st.caption(
                "Describe a behaviour of concern. AI drafts a single entry-level SMARTAR goal "
                "you can drop into any slot below. Run it as many times as needed."
            )
            _ns_beh = st.text_area(
                "What is the behaviour of concern?",
                placeholder=(
                    "e.g. Student has been excluded for frequent physical altercations with peers "
                    "during unstructured time. Has difficulty regulating when frustrated…"
                ),
                height=80, key="ns_beh_brief",
            )
            if st.button("🤖 Draft SMARTAR Goal", key="ns_draft_btn",
                         disabled=not _ns_beh.strip()):
                with st.spinner("Drafting entry SMARTAR goal…"):
                    _ns_dp = f"""You are an expert at writing initial SMARTAR goals for students being enrolled in an alternative education setting (CLC Learning and Behaviour Unit, Adelaide SA).

Write ONE entry-level SMARTAR goal based on this behaviour of concern:
{_ns_beh.strip()}

Rules:
- Use "[Student]" as a placeholder for the student's name
- Target the REPLACEMENT behaviour (what the student WILL DO)
- Entry-level — achievable starting point, not too high a bar
- Trauma-informed, strengths-based language (PBS/BSEM)
- ONE sentence only — no "and" joining two separate actions
- Include a realistic prompt level and success rate

Return ONLY the goal sentence — nothing else."""
                    try:
                        _ns_draft = groq_call(_ns_dp)
                        if _ns_draft and len(_ns_draft) > 20 and "[AI unavailable" not in _ns_draft:
                            _ns_draft = (_ns_draft.strip().strip('"').strip("'")
                                         .replace("[Student]", ns_name.strip().split()[0] if ns_name.strip() else "[Student]")
                                         .replace("[student]", ns_name.strip().split()[0] if ns_name.strip() else "[Student]"))
                            st.session_state["ns_entry_draft"] = _ns_draft
                            st.rerun()
                        else:
                            st.warning("Unexpected AI response — type the goal manually below.")
                    except Exception as _nd_e:
                        st.error(f"AI error: {_nd_e}")

            if st.session_state.get("ns_entry_draft"):
                st.markdown(
                    f'<div class="smartar-box">🤖 <b>AI Draft:</b> '
                    f'{st.session_state["ns_entry_draft"]}</div>',
                    unsafe_allow_html=True,
                )
                # Let user choose which slot to drop into
                _slot_options = [
                    f"Goal {i+1}" + (f" — {g['excl'][:40]}…" if len(g['excl']) > 40 else (f" — {g['excl']}" if g['excl'] else ""))
                    for i, g in enumerate(st.session_state["ns_goal_list"])
                ]
                _target_slot = st.selectbox("Add draft to:", _slot_options, key="ns_draft_slot")
                _slot_idx = _slot_options.index(_target_slot)

                _add_col, _dis_col = st.columns([2, 2])
                with _add_col:
                    if st.button("➕ Add to Selected Slot", key="ns_add_draft_to_list", type="primary"):
                        st.session_state["ns_goal_list"][_slot_idx]["smartar"] = st.session_state["ns_entry_draft"]
                        st.session_state.pop("ns_entry_draft", None)
                        st.rerun()
                with _dis_col:
                    if st.button("✖ Discard Draft", key="ns_discard_draft"):
                        st.session_state.pop("ns_entry_draft", None)
                        st.rerun()

    # ── Goal pairs ────────────────────────────────────────────────────────────
    _gl  = st.session_state["ns_goal_list"]
    _to_del = []

    for _gi, _gentry in enumerate(_gl):
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'
            f'padding:14px 16px;margin-bottom:14px;">'
            f'<span style="font-weight:700;color:#1A7A6E">Goal {_gi + 1}</span></div>',
            unsafe_allow_html=True,
        )
        _pair_col, _del_col = st.columns([11, 1])
        with _pair_col:
            _new_excl = st.text_area(
                f"🏫 Exclusion Goal {_gi + 1} — reason for referral from home school",
                value=_gentry["excl"],
                placeholder="e.g. The student has been excluded for physical aggression towards peers…",
                height=75,
                key=f"ns_excl_text_{_gentry['id']}",
            )
            if _new_excl != _gentry["excl"]:
                st.session_state["ns_goal_list"][_gi]["excl"] = _new_excl

            _new_smartar = st.text_area(
                f"🎯 Entry SMARTAR Goal {_gi + 1} — replacement behaviour to work toward",
                value=_gentry["smartar"],
                placeholder=(
                    "e.g. Jordan will use a calm-down card to request a break when feeling "
                    "overwhelmed, one to one in the classroom, with a verbal prompt, on 3 out of 5 opportunities."
                ),
                height=90,
                key=f"ns_smartar_text_{_gentry['id']}",
            )
            if _new_smartar != _gentry["smartar"]:
                st.session_state["ns_goal_list"][_gi]["smartar"] = _new_smartar

        with _del_col:
            st.markdown("<div style='margin-top:30px'>", unsafe_allow_html=True)
            if len(_gl) > 1:
                if st.button("🗑", key=f"ns_goal_del_{_gentry['id']}", help="Remove this goal pair"):
                    _to_del.append(_gi)
            st.markdown("</div>", unsafe_allow_html=True)

    if _to_del:
        st.session_state["ns_goal_list"] = [g for i, g in enumerate(_gl) if i not in _to_del]
        st.rerun()

    if st.button("➕ Add Another Goal", key="ns_add_goal"):
        _new_id2 = max(g["id"] for g in st.session_state["ns_goal_list"]) + 1
        st.session_state["ns_goal_list"].append({"excl": "", "smartar": "", "id": _new_id2})
        st.rerun()

    _filled_pairs = [g for g in st.session_state["ns_goal_list"] if g["smartar"].strip()]
    if _filled_pairs:
        st.caption(f"✅ {len(_filled_pairs)} goal{'s' if len(_filled_pairs) != 1 else ''} ready to save.")
    else:
        st.caption("💡 Enter at least one SMARTAR goal (Goal 1) to enable save.")

    # ── Save ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    _ns_ready = (
        ns_name.strip()
        and bool(_filled_pairs)
        and ns_name.strip().lower() not in _existing_names
    )
    if not ns_name.strip():
        st.caption("💡 Enter a student name to enable save.")
    elif ns_name.strip().lower() in _existing_names:
        st.caption("⚠️ Student already exists — go to Goal Builder.")

    if st.button(
        f"💾 Save Student & {len(_filled_pairs)} Goal{'s' if len(_filled_pairs) != 1 else ''}",
        type="primary", key="ns_save", disabled=not _ns_ready,
    ):
        try:
            sb.table("smartar_students").insert({
                "student_name": ns_name.strip(),
                "program":      ns_prog,
                "active":       True,
            }).execute()
            for _fp in _filled_pairs:
                sb.table("smartar_goals").insert({
                    "student_name":    ns_name.strip(),
                    "exclusion_goal":  _fp["excl"].strip() if _fp["excl"].strip() else None,
                    "smartar_goal":    _fp["smartar"].strip(),
                    "tracking_period": "All Day",
                    "active":          True,
                    "status":          "Active",
                    "start_date":      date.today().isoformat(),
                }).execute()
            for _nk in ["ns_entry_draft", "ns_goal_list"]:
                st.session_state.pop(_nk, None)
            st.success(
                f"✅ **{ns_name.strip()}** added to **{ns_prog}** with "
                f"**{len(_filled_pairs)} entry goal{'s' if len(_filled_pairs) != 1 else ''}** saved. "
                f"Teachers can now open this student in the Goal Builder."
            )
            st.balloons()
        except Exception as _ns_err:
            st.error(f"Save error: {_ns_err}")

    # ── Existing students quick view ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("Current Students")
    _all_students = get_students()
    if _all_students:
        for _s in _all_students:
            _sg = get_goals(_s["student_name"], active_only=True)
            _sc1, _sc2, _sc3 = st.columns([3, 1, 1])
            _sc1.write(f"**{_s['student_name']}** — {_s.get('program','?')} — {len(_sg)} active goal(s)")
            _sc2.caption(_s.get("created_at","")[:10] or "")
            if _sc3.button("Archive Student", key=f"ns_arch_{_s['id']}"):
                sb.table("smartar_students").update({"active": False}).eq("id", _s["id"]).execute()
                st.success(f"Archived {_s['student_name']}")
                st.rerun()
    else:
        st.info("No students yet — add your first student above.")

    # ── Archived students ─────────────────────────────────────────────────────
    _archived_s_list = [s for s in get_students(include_archived=True)
                        if not s.get("active", True) and not s.get("placement_ended", False)]
    _ended_s_list    = [s for s in get_students(include_archived=True)
                        if s.get("placement_ended", False)]

    _total_non_active = len(_archived_s_list) + len(_ended_s_list)
    if _total_non_active:
        st.markdown("---")
        with st.expander(
            f"🗃️ Non-Active Students ({_total_non_active}) — archived · placement ended · delete",
            expanded=False,
        ):
            st.caption(
                "**Archived** — hidden from Goal Builder and tracking but data is intact. "
                "Choose what to do with each student below.\n\n"
                "🏁 **End Placement** — student has left CLC. Data is preserved in the archive "
                "permanently but the student will no longer appear in any active views.\n\n"
                "🗑 **Permanently Delete** — for students entered in error. Removes the student "
                "record, all goals, and all tracking data. Cannot be undone."
            )

            if _archived_s_list:
                st.markdown("**Archived students**")
                for _as in _archived_s_list:
                    _asg = get_goals(_as["student_name"], active_only=False)
                    with st.container():
                        st.markdown(
                            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;'
                            f'border-radius:8px;padding:10px 14px;margin-bottom:10px;">'
                            f'<b>{_as["student_name"]}</b> &nbsp;·&nbsp; {_as.get("program","?")} '
                            f'&nbsp;·&nbsp; {len(_asg)} goal(s)</div>',
                            unsafe_allow_html=True,
                        )
                        _ab1, _ab2, _ab3 = st.columns(3)
                        with _ab1:
                            if st.button("♻️ Restore to Active",
                                         key=f"ns_restore_{_as['id']}"):
                                sb.table("smartar_students").update({"active": True}).eq(
                                    "id", _as["id"]
                                ).execute()
                                st.success(f"✅ {_as['student_name']} restored.")
                                st.rerun()
                        with _ab2:
                            if st.button("🏁 End Placement",
                                         key=f"ns_endplacement_{_as['id']}"):
                                st.session_state[f"ns_end_confirm_{_as['id']}"] = True
                        with _ab3:
                            if st.button("🗑 Delete Permanently",
                                         key=f"ns_del_{_as['id']}"):
                                st.session_state[f"ns_del_confirm_{_as['id']}"] = True

                        # End Placement confirmation
                        if st.session_state.get(f"ns_end_confirm_{_as['id']}"):
                            st.markdown(
                                f'<div class="period-box">🏁 <b>End placement for '
                                f'{_as["student_name"]}?</b><br>'
                                f'This student will be marked as placement ended. '
                                f'All goals and tracking data are permanently preserved in the archive '
                                f'but the student will not appear in any active views.</div>',
                                unsafe_allow_html=True,
                            )
                            _ea, _eb = st.columns(2)
                            with _ea:
                                if st.button(f"Yes — end placement",
                                             key=f"ns_end_conf_{_as['id']}", type="primary"):
                                    sb.table("smartar_students").update({
                                        "active": False, "placement_ended": True
                                    }).eq("id", _as["id"]).execute()
                                    st.session_state.pop(f"ns_end_confirm_{_as['id']}", None)
                                    st.success(f"🏁 {_as['student_name']} — placement ended. Data preserved.")
                                    st.rerun()
                            with _eb:
                                if st.button("Cancel", key=f"ns_end_cancel_{_as['id']}"):
                                    st.session_state.pop(f"ns_end_confirm_{_as['id']}", None)
                                    st.rerun()

                        # Delete confirmation
                        if st.session_state.get(f"ns_del_confirm_{_as['id']}"):
                            st.markdown(
                                f'<div class="alert-box">⚠️ <b>Permanently delete '
                                f'{_as["student_name"]}?</b><br>'
                                f'Use this only if the student was entered in error. '
                                f'This will permanently remove the student record, all goals, '
                                f'and all tracking data. This cannot be undone.</div>',
                                unsafe_allow_html=True,
                            )
                            _da, _db = st.columns(2)
                            with _da:
                                if st.button(f"Yes — permanently delete",
                                             key=f"ns_del_conf_{_as['id']}", type="primary"):
                                    try:
                                        _del_gs = sb.table("smartar_goals").select("id").eq(
                                            "student_name", _as["student_name"]
                                        ).execute().data or []
                                        for _dg in _del_gs:
                                            sb.table("smartar_tracking").delete().eq(
                                                "goal_id", _dg["id"]
                                            ).execute()
                                        sb.table("smartar_goals").delete().eq(
                                            "student_name", _as["student_name"]
                                        ).execute()
                                        sb.table("smartar_students").delete().eq(
                                            "id", _as["id"]
                                        ).execute()
                                        st.session_state.pop(f"ns_del_confirm_{_as['id']}", None)
                                        st.success(f"✅ {_as['student_name']} permanently deleted.")
                                        st.rerun()
                                    except Exception as _nde:
                                        st.error(f"Delete error: {_nde}")
                            with _db:
                                if st.button("Cancel", key=f"ns_del_cancel_{_as['id']}"):
                                    st.session_state.pop(f"ns_del_confirm_{_as['id']}", None)
                                    st.rerun()

            if _ended_s_list:
                if _archived_s_list:
                    st.markdown("---")
                st.markdown("**Placement ended students** — data preserved permanently")
                for _es in _ended_s_list:
                    _esg = get_goals(_es["student_name"], active_only=False)
                    st.markdown(
                        f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;'
                        f'border-radius:8px;padding:10px 14px;margin-bottom:8px;">'
                        f'🏁 <b>{_es["student_name"]}</b> &nbsp;·&nbsp; {_es.get("program","?")} '
                        f'&nbsp;·&nbsp; {len(_esg)} goal(s) &nbsp;·&nbsp; '
                        f'<span style="color:#16a34a">Placement ended — data archived</span></div>',
                        unsafe_allow_html=True,
                    )
                    _pb1, _pb2 = st.columns([2, 4])
                    with _pb1:
                        if st.button("♻️ Restore to Active",
                                     key=f"ns_restore_end_{_es['id']}"):
                            sb.table("smartar_students").update({
                                "active": True, "placement_ended": False
                            }).eq("id", _es["id"]).execute()
                            st.success(f"✅ {_es['student_name']} restored to active.")
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 3. GOAL BUILDER  (teachers)
# ══════════════════════════════════════════════════════════════════════════════
elif view == "📋 Goal Builder":
    st.title("📋 SMARTAR Goal Builder")
    st.caption("Select a student to view their current goal, then archive, modify, or refine it.")

    students = get_students()
    if not students:
        st.info("No students set up yet. Ask your coordinator to add students via **New Student Setup**.")
        st.stop()

    student_options = {s["student_name"]: s for s in students}

    # ── Student selector — no default (prevent accidental wrong-student edits) ─
    if integration["active"] and integration["student"] and integration["student"] in student_options:
        _sb_options = list(student_options.keys())
        _sb_index   = _sb_options.index(integration["student"]) + 1  # +1 for placeholder
    else:
        _sb_index = 0  # lands on placeholder

    _sb_choice = st.selectbox(
        "Select student",
        ["— Select a student —"] + list(student_options.keys()),
        index=_sb_index,
        key="gb_student_select",
    )

    if _sb_choice == "— Select a student —":
        st.info("Select a student above to view their goals.")
        st.stop()

    selected_name  = _sb_choice
    student        = student_options[selected_name]
    existing_goals = get_goals(selected_name, active_only=True)
    archived_goals = [g for g in get_goals(selected_name, active_only=False) if not g.get("active", True)]

    st.markdown(
        f'<div class="student-header"><b>{selected_name}</b> · '
        f'{student.get("program","?")} · {len(existing_goals)} active goal(s)</div>',
        unsafe_allow_html=True,
    )

    # ── Current goals — flat display, each with inline archive + modify ───────
    if existing_goals:
        for idx, g in enumerate(existing_goals, 1):
            goal_text        = g.get("smartar_goal", "No goal text")
            needs_ref, low_c = check_goal_needs_refinement(g["id"])
            period           = g.get("tracking_period", "All Day")

            st.markdown(
                f'<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;'
                f'padding:14px 18px;margin-bottom:6px;">'
                f'<span style="font-weight:700;color:#0369a1">Goal {idx}</span>'
                + (f' &nbsp;<span style="background:#fef3c7;color:#92400e;font-size:0.78rem;'
                   f'padding:2px 8px;border-radius:4px;font-weight:600">⚠️ NEEDS REFINEMENT</span>'
                   if needs_ref else "") +
                f'</div>',
                unsafe_allow_html=True,
            )

            if needs_ref:
                st.markdown(
                    f'<div class="alert-box">⚠️ <b>Action Required:</b> {low_c} recent sessions '
                    f'show NOT YET. Please refine this goal.</div>', unsafe_allow_html=True,
                )
            if g.get("exclusion_goal"):
                st.markdown(
                    f'<div class="exclusion-box">🏫 <b>Exclusion Goal from Home School:</b><br>'
                    f'{g.get("exclusion_goal","—")}</div>', unsafe_allow_html=True,
                )
            st.markdown(
                f'<div class="smartar-box">🎯 <b>Current SMARTAR Goal:</b><br>{goal_text}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="period-box" style="margin-bottom:10px;">📅 Tracking period: '
                f'<strong>{period}</strong> — {", ".join(SESSIONS_FOR_PERIOD.get(period, ALL_SESSIONS))}</div>',
                unsafe_allow_html=True,
            )
            gas = get_gas_dict(g)
            if any(gas.values()):
                with st.expander("📊 GAS Performance Levels"):
                    for lvl in LEVEL_ORDER:
                        desc = gas.get(lvl,"")
                        if desc:
                            st.markdown(
                                f'<div class="gas-level-bar"><span class="gas-level-label" '
                                f'style="color:{LEVEL_COLOR[lvl]}">{LEVEL_EMOJI[lvl]} {lvl}</span>'
                                f'<span class="gas-level-desc">{desc}</span></div>',
                                unsafe_allow_html=True,
                            )

            # ── Archive inline ────────────────────────────────────────────────
            if st.button(f"🗑 Archive Goal {idx}", key=f"del_{g['id']}"):
                st.session_state[f"arch_gb_{g['id']}"] = True
            if st.session_state.get(f"arch_gb_{g['id']}"):
                reason = st.text_input("Archive reason (optional):", key=f"arch_gb_r_{g['id']}")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("Confirm Archive", key=f"arch_gb_d_{g['id']}", type="primary"):
                        if archive_goal(g["id"], reason):
                            st.session_state.pop(f"arch_gb_{g['id']}", None)
                            st.session_state["build_new_after_archive"]  = True
                            st.session_state["archived_excl_goal"]       = g.get("exclusion_goal","")
                            st.session_state["archived_student"]         = g.get("student_name","")
                            st.session_state["archived_smartar_goal"]    = goal_text
                            st.rerun()
                with cb:
                    if st.button("Cancel", key=f"arch_gb_x_{g['id']}"):
                        st.session_state.pop(f"arch_gb_{g['id']}", None)
                        st.rerun()

            # ── Modify / refine this goal — inline below ──────────────────────
            with st.expander(f"✏️ Modify / Refine Goal {idx}", expanded=False):
                st.caption(
                    "The exclusion goal and current SMARTAR goal are shown above as your reference. "
                    "Edit the goal text directly below, then use the hierarchy builder or AI tool to refine."
                )
                # Pre-fill with current goal text so staff always see exactly what they're working from
                _mod_key = f"gb_working_goal_{g['id']}"
                if _mod_key not in st.session_state:
                    st.session_state[_mod_key] = goal_text

                _working_goal = st.text_area(
                    "Working goal — edit directly or use tools below",
                    value=st.session_state[_mod_key],
                    height=100,
                    key=f"gb_wg_ta_{g['id']}_{hash(st.session_state[_mod_key])}",
                )
                if _working_goal.strip() and _working_goal != st.session_state[_mod_key]:
                    st.session_state[_mod_key] = _working_goal

                _excl_ref   = g.get("exclusion_goal","")
                _refine_tab, _ai_tab_g = st.tabs(["📐 Hierarchy Builder", "✨ AI Goal Tool"])

                # ── Hierarchy builder ─────────────────────────────────────────
                with _refine_tab:
                    st.caption("Select each element to assemble a new version of the goal, then refine with AI.")
                    _hb_c1, _hb_c2 = st.columns(2)
                    with _hb_c1:
                        _hb_first  = st.text_input("Student first name", value=selected_name.split()[0], key=f"hb_first_{g['id']}")
                        _hb_skill  = st.text_area("Expected skill / behaviour",
                                                  placeholder="e.g. use a break card to request a break",
                                                  height=75, key=f"hb_skill_{g['id']}")
                        _hb_group  = st.selectbox("Grouping", GROUPINGS, key=f"hb_grouping_{g['id']}")
                        _hb_task   = st.selectbox("Task type", TASK_TYPES, key=f"hb_task_{g['id']}")
                    with _hb_c2:
                        _hb_set    = st.selectbox("Setting", SETTINGS, key=f"hb_setting_{g['id']}")
                        _hb_prompt = st.selectbox("Prompt level", PROMPT_TYPES, key=f"hb_prompts_{g['id']}")
                        _hb_rate   = st.selectbox("Rate / success criteria", RATE_OPTIONS, key=f"hb_rate_{g['id']}")

                    _assembled = (
                        f"{_hb_first} will {_hb_skill} {_hb_group.lower()} during {_hb_task.lower()} "
                        f"in the {_hb_set.lower()} with {_hb_prompt.lower()}, "
                        f"demonstrating successful use on {_hb_rate}."
                        if _hb_skill and _hb_first else ""
                    )
                    if _assembled:
                        st.markdown("**Assembled preview:**")
                        st.info(_assembled)
                        if st.button("✨ Refine assembled goal with AI", key=f"hb_refine_{g['id']}",
                                     type="primary"):
                            if groq_client:
                                with st.spinner("Refining…"):
                                    try:
                                        _ref = groq_call(
                                            f"""Rewrite into ONE fluent professional SMARTAR goal sentence.
Fix doubled words; start "{_hb_first} will..."; keep ALL specific details;
one sentence only; trauma-informed strengths-based language (PBS/BSEM);
do NOT add "appropriately" or "independently" unless already present.
Goal: {_assembled}
Return ONLY the final goal statement."""
                                        )
                                        if _ref and len(_ref) > 20 and "[AI unavailable" not in _ref:
                                            st.session_state[_mod_key] = _ref.strip().strip('"').strip("'")
                                            st.rerun()
                                    except Exception as _re:
                                        st.error(f"AI error: {_re}")
                            else:
                                st.warning("AI unavailable.")

                # ── AI goal tool ──────────────────────────────────────────────
                with _ai_tab_g:
                    _ai_mode_g = st.radio(
                        "What would you like to do?",
                        ["🔧 Modify the current goal based on observed behaviours",
                         "🔄 Create a new replacement goal from observed behaviours"],
                        key=f"ai_mode_{g['id']}",
                    )
                    _ai_desc_g = st.text_area(
                        "📝 Describe the behaviours you're observing / what needs to change",
                        placeholder=(
                            "e.g. The student is now managing the break card request but still "
                            "struggles to return to task. Goal should now focus on returning to "
                            "work within 5 minutes after a break…"
                        ),
                        height=110, key=f"ai_desc_{g['id']}",
                    )
                    _ai_c1, _ai_c2 = st.columns(2)
                    with _ai_c1:
                        _ai_prompt_g = st.selectbox("Target prompt level", PROMPT_TYPES, key=f"ai_prompt_{g['id']}")
                        _ai_rate_g   = st.selectbox("Target success rate",  RATE_OPTIONS,  key=f"ai_rate_{g['id']}")
                    with _ai_c2:
                        _ai_set_g    = st.selectbox("Setting",  SETTINGS,  key=f"ai_set_{g['id']}")
                        _ai_group_g  = st.selectbox("Grouping", GROUPINGS, key=f"ai_group_{g['id']}")

                    if groq_client and st.button(
                        "🤖 Generate", type="primary", key=f"ai_gen_btn_{g['id']}",
                        disabled=not _ai_desc_g.strip(),
                    ):
                        with st.spinner("Generating…"):
                            if "Modify" in _ai_mode_g:
                                _ai_p = f"""Modify this SMARTAR goal based on the observed behaviours described.

CURRENT GOAL: {st.session_state[_mod_key]}
OBSERVED / REQUESTED CHANGES: {_ai_desc_g.strip()}
UPDATED CONTEXT: Setting: {_ai_set_g} | Grouping: {_ai_group_g} | Prompt: {_ai_prompt_g} | Rate: {_ai_rate_g}

✅ ONE sentence, ONE target skill, build on the existing goal
❌ No "and" joining two separate actions | no preamble
Return ONLY the modified goal sentence."""
                            else:
                                _ai_p = f"""Write ONE new SMARTAR goal for this student based on the observed behaviour.

OBSERVED BEHAVIOUR: {_ai_desc_g.strip()}
CONTEXT: Setting: {_ai_set_g} | Grouping: {_ai_group_g} | Prompt: {_ai_prompt_g} | Rate: {_ai_rate_g}
STUDENT NAME: {selected_name.split()[0]}

✅ ONE sentence, ONE replacement/target behaviour
✅ Start with "{selected_name.split()[0]} will..."
❌ No "and" joining two separate actions | no preamble
Return ONLY the goal sentence."""
                            try:
                                _ai_result = groq_call(_ai_p)
                                if _ai_result and len(_ai_result) > 20 and "[AI unavailable" not in _ai_result:
                                    st.session_state[_mod_key] = _ai_result.strip().strip('"').strip("'")
                                    st.rerun()
                            except Exception as _ae:
                                st.error(f"AI error: {_ae}")
                    if not _ai_desc_g.strip():
                        st.caption("💡 Describe the behaviours / changes above to enable generation.")

                # ── Finalise & save ───────────────────────────────────────────
                st.markdown("---")
                _final_g = st.session_state.get(_mod_key, goal_text)
                st.markdown(
                    f'<div class="smartar-box" style="margin-bottom:10px;">🎯 <b>Goal to save:</b><br>'
                    f'{_final_g}</div>', unsafe_allow_html=True,
                )

                # Auto-generate GAS for the working goal
                _gas_key = f"gas_levels_{g['id']}"
                if _final_g and _final_g != goal_text and groq_client and not st.session_state.get(_gas_key):
                    with st.spinner("🤖 Generating GAS levels…"):
                        try:
                            _gr2 = groq_call(
                                f"""GAS for: "{_final_g}"
EXPECTED (0) = goal verbatim. Scale only rate/criteria.
Return ONLY JSON: {{"EXCEEDING":"...","ABOVE":"...","EXPECTED":"...","BELOW":"...","NOT_YET":"..."}}"""
                            )
                            _gp2 = json.loads(_gr2.strip().strip("```json").strip("```").strip())
                            if "NOT_YET" in _gp2:
                                _gp2["NOT YET"] = _gp2.pop("NOT_YET")
                            st.session_state[_gas_key] = _gp2
                            st.rerun()
                        except Exception:
                            pass

                _excl_update = st.text_area(
                    "🏫 Exclusion goal (leave blank to keep existing)",
                    value=_excl_ref, height=65,
                    key=f"gb_excl_update_{g['id']}",
                )
                _period_key = f"gb_period_{g['id']}"
                _period_val = st.session_state.get(_period_key, period)
                _tracking_g = st.selectbox(
                    "Tracking period", TRACKING_PERIODS,
                    index=TRACKING_PERIODS.index(_period_val) if _period_val in TRACKING_PERIODS else 0,
                    key=f"gb_tp_{g['id']}",
                )

                _gas_g = st.session_state.get(_gas_key, {})
                _edited_gas_g = {}
                if _gas_g:
                    if st.button("🔄 Re-generate GAS", key=f"gb_regen_gas_{g['id']}"):
                        st.session_state.pop(_gas_key, None)
                        st.rerun()
                    with st.expander("📊 GAS Levels (auto-generated — edit if needed)"):
                        _ggver = hash(str(sorted(_gas_g.items())))
                        for _lvl in LEVEL_ORDER:
                            _lk = _lvl if _lvl in _gas_g else _lvl.replace(" ","_")
                            _edited_gas_g[_lvl] = st.text_area(
                                f"{LEVEL_EMOJI[_lvl]} {_lvl}",
                                value=_gas_g.get(_lvl, _gas_g.get(_lk,"")), height=60,
                                key=f"gb_gas_{g['id']}_{_lvl}_{_ggver}",
                            )
                else:
                    st.caption("GAS levels will auto-generate when the goal changes from the original.")

                if st.button(f"💾 Save Updated Goal", type="primary",
                             key=f"gb_save_{g['id']}", disabled=not _final_g.strip()):
                    _fg_gas = _edited_gas_g or _gas_g
                    try:
                        sb.table("smartar_goals").insert({
                            "student_name":    selected_name,
                            "exclusion_goal":  _excl_update.strip() or _excl_ref or None,
                            "smartar_goal":    _final_g.strip(),
                            "tracking_period": _tracking_g,
                            "active":          True,
                            "status":          "Active",
                            "start_date":      date.today().isoformat(),
                            "gas_exceeding":   _fg_gas.get("EXCEEDING",""),
                            "gas_above":       _fg_gas.get("ABOVE",""),
                            "gas_expected":    _fg_gas.get("EXPECTED",""),
                            "gas_below":       _fg_gas.get("BELOW",""),
                            "gas_not_yet":     _fg_gas.get("NOT YET",""),
                        }).execute()
                        # Clear working state for this goal
                        for _ck2 in [_mod_key, _gas_key]:
                            st.session_state.pop(_ck2, None)
                        st.success(f"✅ Updated goal saved for {selected_name}!")
                        if integration["active"]:
                            st.markdown(f"[← Return to Team Meeting](https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']})")
                        st.rerun()
                    except Exception as _se2:
                        st.error(f"Save error: {_se2}")

            st.markdown("---")


    # ── Archived goals ────────────────────────────────────────────────────────
    if archived_goals:
        with st.expander(f"🗃️ Archived Goals ({len(archived_goals)})", expanded=False):
            st.caption("Preserved with all tracking data.")
            for ag in archived_goals:
                ag_text = ag.get("smartar_goal","—")
                with st.expander(f"🟠 {_short(ag_text, 70)} — archived {(ag.get('archived_at') or '')[:10]}", expanded=False):
                    if ag.get("exclusion_goal"):
                        st.markdown(f'<div class="exclusion-box">🏫 {ag["exclusion_goal"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="archived-box">🎯 {ag_text}</div>', unsafe_allow_html=True)
                    if ag.get("archive_reason"):
                        st.caption(f"Reason: {ag['archive_reason']}")
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        if st.button("♻️ Restore", key=f"restore_gb_{ag['id']}", type="primary"):
                            if restore_goal(ag["id"]):
                                st.success("✅ Goal restored.")
                                st.rerun()

    # ── Manage student ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚙️ Manage Student", expanded=False):
        st.caption("Archive this student. To add a new student, use New Student Setup in the sidebar.")
        if st.button(f"🗑 Archive student — {selected_name}", key="mgmt_archive_student"):
            st.session_state["mgmt_arch_confirm"] = True
        if st.session_state.get("mgmt_arch_confirm"):
            st.warning(f"⚠️ This will archive {selected_name}. All data is preserved.")
            mc1, mc2 = st.columns(2)
            with mc1:
                if st.button("Confirm Archive", type="primary", key="mgmt_arch_confirm_btn"):
                    sb.table("smartar_students").update({"active":False}).eq("id", student["id"]).execute()
                    st.session_state.pop("mgmt_arch_confirm", None)
                    st.success(f"✅ {selected_name} archived.")
                    st.rerun()
            with mc2:
                if st.button("Cancel", key="mgmt_arch_cancel"):
                    st.session_state.pop("mgmt_arch_confirm", None)
                    st.rerun()





# ══════════════════════════════════════════════════════════════════════════════
# 4. LEADERSHIP DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif view == "👩‍💼 Leadership Dashboard":
    st.title("👩‍💼 Leadership Dashboard")
    st.caption(
        "Program-level overview for leadership. Select a program to see all students, "
        "their current goals, and tracking status at a glance — "
        "to identify who needs goal review, teacher follow-up, or tracking support."
    )

    # ── Helpers ───────────────────────────────────────────────────────────────
    FLAG_NONE        = "✅ On track"
    FLAG_NOT_TRACKED = "⬜ Not being tracked"
    FLAG_SPARSE      = "🟡 Tracking sparse"
    FLAG_TOO_EASY    = "🔵 Goal too easy — consistently exceeding"
    FLAG_NOT_ACHIEV  = "🔴 Not achieving — review needed"
    FLAG_NEEDS_REF   = "🟠 Needs goal refinement"
    FLAG_IMPROVING   = "📈 Improving"
    FLAG_DECLINING   = "📉 Declining — needs attention"

    def _flag_goal(goal_id):
        """Return (flag_str, recent_data, counts, total) for a goal."""
        recent = get_recent_tracking(goal_id, sessions=10)
        if not recent:
            return FLAG_NOT_TRACKED, [], {}, 0
        counts, total, pcts = calc_percentages(recent)
        if total < 3:
            return FLAG_SPARSE, recent, counts, total
        high  = pcts.get("EXCEEDING", 0) + pcts.get("ABOVE", 0)
        low   = pcts.get("NOT YET", 0)
        below = pcts.get("BELOW", 0) + low
        needs_ref, _ = check_goal_needs_refinement(goal_id)
        if needs_ref:
            return FLAG_NOT_ACHIEV, recent, counts, total
        if high >= 70:
            return FLAG_TOO_EASY, recent, counts, total
        if below >= 60:
            return FLAG_NEEDS_REF, recent, counts, total
        trend = analyze_trend(recent)
        if trend == "declining":
            return FLAG_DECLINING, recent, counts, total
        if trend == "improving":
            return FLAG_IMPROVING, recent, counts, total
        return FLAG_NONE, recent, counts, total

    FLAG_COLOR = {
        FLAG_NONE:        "#d1fae5",
        FLAG_NOT_TRACKED: "#f3f4f6",
        FLAG_SPARSE:      "#fef9c3",
        FLAG_TOO_EASY:    "#dbeafe",
        FLAG_NOT_ACHIEV:  "#fee2e2",
        FLAG_NEEDS_REF:   "#ffedd5",
        FLAG_IMPROVING:   "#dcfce7",
        FLAG_DECLINING:   "#fee2e2",
    }
    FLAG_BORDER = {
        FLAG_NONE:        "#6ee7b7",
        FLAG_NOT_TRACKED: "#d1d5db",
        FLAG_SPARSE:      "#fcd34d",
        FLAG_TOO_EASY:    "#93c5fd",
        FLAG_NOT_ACHIEV:  "#fca5a5",
        FLAG_NEEDS_REF:   "#fb923c",
        FLAG_IMPROVING:   "#86efac",
        FLAG_DECLINING:   "#f87171",
    }

    # ── Program tabs ──────────────────────────────────────────────────────────
    _prog_tabs = st.tabs(["📚 JP — Junior Primary", "📖 PY — Primary Years", "🎓 SY — Senior Years"])

    for _prog_tab, _prog in zip(_prog_tabs, PROGRAMS):
        with _prog_tab:
            all_students = get_students()
            prog_students = [s for s in all_students if s.get("program") == _prog]

            if not prog_students:
                st.info(f"No active students in {_prog}.")
                continue

            # ── Summary banner ─────────────────────────────────────────────
            _all_flags = []
            _student_data = []  # cache per-student flags so we only fetch once
            for _ps in prog_students:
                _ps_goals = get_goals(_ps["student_name"], active_only=True)
                _ps_goal_flags = []
                for _g in _ps_goals:
                    _flag, _rec, _cnt, _tot = _flag_goal(_g["id"])
                    _ps_goal_flags.append((_g, _flag, _rec, _cnt, _tot))
                    _all_flags.append(_flag)
                _student_data.append((_ps, _ps_goals, _ps_goal_flags))

            _total_s   = len(prog_students)
            _n_untrack = sum(1 for f in _all_flags if f == FLAG_NOT_TRACKED)
            _n_sparse  = sum(1 for f in _all_flags if f == FLAG_SPARSE)
            _n_easy    = sum(1 for f in _all_flags if f == FLAG_TOO_EASY)
            _n_achiev  = sum(1 for f in _all_flags if f in (FLAG_NOT_ACHIEV, FLAG_DECLINING))
            _n_ref     = sum(1 for f in _all_flags if f == FLAG_NEEDS_REF)
            _n_good    = sum(1 for f in _all_flags if f in (FLAG_NONE, FLAG_IMPROVING))

            st.markdown(
                f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;">'
                f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
                f'padding:10px 16px;text-align:center;min-width:90px;">'
                f'<div style="font-size:1.5rem;font-weight:700">{_total_s}</div>'
                f'<div style="font-size:0.75rem;color:#166534">Students</div></div>'
                f'<div style="background:#f3f4f6;border:1px solid #d1d5db;border-radius:8px;'
                f'padding:10px 16px;text-align:center;min-width:90px;">'
                f'<div style="font-size:1.5rem;font-weight:700">{_n_untrack}</div>'
                f'<div style="font-size:0.75rem;color:#6b7280">Not tracked</div></div>'
                f'<div style="background:#fef9c3;border:1px solid #fcd34d;border-radius:8px;'
                f'padding:10px 16px;text-align:center;min-width:90px;">'
                f'<div style="font-size:1.5rem;font-weight:700">{_n_sparse}</div>'
                f'<div style="font-size:0.75rem;color:#92400e">Sparse</div></div>'
                f'<div style="background:#fee2e2;border:1px solid #fca5a5;border-radius:8px;'
                f'padding:10px 16px;text-align:center;min-width:90px;">'
                f'<div style="font-size:1.5rem;font-weight:700">{_n_achiev}</div>'
                f'<div style="font-size:0.75rem;color:#991b1b">Not achieving</div></div>'
                f'<div style="background:#dbeafe;border:1px solid #93c5fd;border-radius:8px;'
                f'padding:10px 16px;text-align:center;min-width:90px;">'
                f'<div style="font-size:1.5rem;font-weight:700">{_n_easy}</div>'
                f'<div style="font-size:0.75rem;color:#1e40af">Too easy</div></div>'
                f'<div style="background:#ffedd5;border:1px solid #fb923c;border-radius:8px;'
                f'padding:10px 16px;text-align:center;min-width:90px;">'
                f'<div style="font-size:1.5rem;font-weight:700">{_n_ref}</div>'
                f'<div style="font-size:0.75rem;color:#9a3412">Needs review</div></div>'
                f'<div style="background:#d1fae5;border:1px solid #6ee7b7;border-radius:8px;'
                f'padding:10px 16px;text-align:center;min-width:90px;">'
                f'<div style="font-size:1.5rem;font-weight:700">{_n_good}</div>'
                f'<div style="font-size:0.75rem;color:#065f46">On track</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── Filter strip ───────────────────────────────────────────────
            _filter_opts = [
                "All students",
                "⬜ Not being tracked",
                "🟡 Sparse tracking",
                "🔴 Not achieving / declining",
                "🔵 Goal too easy",
                "🟠 Needs review",
                "✅ On track / improving",
            ]
            _filter = st.selectbox(
                "Filter by status",
                _filter_opts,
                key=f"ld_filter_{_prog}",
            )

            # ── Notes store (session state — lightweight, doesn't persist) ─
            if f"ld_notes_{_prog}" not in st.session_state:
                st.session_state[f"ld_notes_{_prog}"] = {}

            # ── Student cards ──────────────────────────────────────────────
            _shown = 0
            for _ps, _ps_goals, _ps_goal_flags in _student_data:

                # Determine worst flag for this student (for filter)
                _priority = [
                    FLAG_NOT_TRACKED, FLAG_NOT_ACHIEV, FLAG_DECLINING,
                    FLAG_NEEDS_REF, FLAG_SPARSE, FLAG_TOO_EASY,
                    FLAG_IMPROVING, FLAG_NONE,
                ]
                _student_flags = [f for _, f, _, _, _ in _ps_goal_flags]
                _worst = next(
                    (f for f in _priority if f in _student_flags),
                    FLAG_NONE,
                )

                # Apply filter
                if _filter != "All students":
                    _pass = False
                    if "Not being tracked"   in _filter and _worst == FLAG_NOT_TRACKED: _pass = True
                    if "Sparse"              in _filter and _worst == FLAG_SPARSE:      _pass = True
                    if "Not achieving"       in _filter and _worst in (FLAG_NOT_ACHIEV, FLAG_DECLINING): _pass = True
                    if "too easy"            in _filter and _worst == FLAG_TOO_EASY:    _pass = True
                    if "Needs review"        in _filter and _worst == FLAG_NEEDS_REF:   _pass = True
                    if "On track"            in _filter and _worst in (FLAG_NONE, FLAG_IMPROVING): _pass = True
                    if not _pass:
                        continue

                _shown += 1
                _card_bg  = FLAG_COLOR.get(_worst, "#f8fafc")
                _card_bdr = FLAG_BORDER.get(_worst, "#e2e8f0")

                with st.expander(
                    f"{'🔴' if _worst in (FLAG_NOT_ACHIEV, FLAG_DECLINING) else '🟡' if _worst in (FLAG_SPARSE, FLAG_NEEDS_REF, FLAG_NOT_TRACKED) else '🔵' if _worst == FLAG_TOO_EASY else '✅'} "
                    f"**{_ps['student_name']}** — {len(_ps_goals)} goal(s) — {_worst}",
                    expanded=(_worst in (FLAG_NOT_ACHIEV, FLAG_DECLINING, FLAG_NOT_TRACKED)),
                ):
                    if not _ps_goals:
                        st.warning("No active goals set up for this student.")
                        continue

                    for _gi2, (_g, _flag, _rec, _cnt, _tot) in enumerate(_ps_goal_flags, 1):
                        _gtext  = _g.get("smartar_goal","—")
                        _excl   = _g.get("exclusion_goal","")
                        _period = _g.get("tracking_period","All Day")

                        # Goal header card
                        st.markdown(
                            f'<div style="background:{FLAG_COLOR.get(_flag,"#f8fafc")};'
                            f'border-left:4px solid {FLAG_BORDER.get(_flag,"#e2e8f0")};'
                            f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px;">'
                            f'<span style="font-weight:700;color:#0369a1">Goal {_gi2}</span> &nbsp; '
                            f'<span style="font-size:0.8rem;font-weight:600">{_flag}</span><br>'
                            + (f'<span style="font-size:0.78rem;color:#b45309">🏫 {_excl}</span><br>' if _excl else "")
                            + f'<span style="font-size:0.88rem">{_gtext}</span><br>'
                            f'<span style="font-size:0.75rem;color:#6b7280">📅 {_period} &nbsp;·&nbsp; '
                            f'{_tot} observations (last 10)</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                        # Mini bar chart of performance distribution
                        if _tot > 0:
                            _, _, _pcts = calc_percentages(_rec)
                            _bar_html = '<div style="display:flex;height:18px;border-radius:4px;overflow:hidden;margin-bottom:6px;">'
                            for _lvl in LEVEL_ORDER:
                                _pct = _pcts.get(_lvl, 0)
                                if _pct > 0:
                                    _bar_html += (
                                        f'<div style="width:{_pct}%;background:{LEVEL_COLOR[_lvl]};'
                                        f'display:flex;align-items:center;justify-content:center;'
                                        f'font-size:0.65rem;color:white;font-weight:600;'
                                        f'white-space:nowrap;overflow:hidden;" title="{_lvl} {_pct:.0f}%">'
                                        f'{_pct:.0f}%</div>'
                                    )
                            _bar_html += '</div>'
                            _pill_html = " &nbsp; ".join(
                                f'<span style="font-size:0.72rem;font-weight:600;color:{LEVEL_COLOR[_lvl]}">'
                                f'{LEVEL_EMOJI[_lvl]} {_lvl} {_pcts.get(_lvl,0):.0f}%</span>'
                                for _lvl in LEVEL_ORDER if _pcts.get(_lvl, 0) > 0
                            )
                            st.markdown(
                                _bar_html + _pill_html,
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                '<div style="background:#f3f4f6;border-radius:4px;padding:6px 10px;'
                                'font-size:0.8rem;color:#6b7280;margin-bottom:6px;">'
                                '⬜ No tracking data recorded yet.</div>',
                                unsafe_allow_html=True,
                            )

                        # Last recorded session
                        if _rec:
                            _last = _rec[0]
                            _last_date  = _last.get("session_date","")
                            _last_level = _last.get("performance_level","")
                            st.caption(
                                f"Last tracked: **{_last_date}** · "
                                f"{LEVEL_EMOJI.get(_last_level,'')} {_last_level}"
                            )

                        st.markdown("---")

                    # ── Leadership note ─────────────────────────────────────
                    _note_key = f"ld_note_{_prog}_{_ps['student_name']}"
                    _note_val = st.session_state[f"ld_notes_{_prog}"].get(_ps["student_name"], "")
                    _note_new = st.text_area(
                        "📝 Leadership note (for discussion with teacher — not saved to database)",
                        value=_note_val,
                        height=65,
                        placeholder=(
                            "e.g. Discuss goal difficulty with teacher in next check-in. "
                            "Student consistently exceeding — may need to increase prompt fading…"
                        ),
                        key=_note_key,
                    )
                    if _note_new != _note_val:
                        st.session_state[f"ld_notes_{_prog}"][_ps["student_name"]] = _note_new

            if _shown == 0:
                st.info("No students match the selected filter.")

            # ── Export notes summary ───────────────────────────────────────
            _notes = st.session_state.get(f"ld_notes_{_prog}", {})
            _notes_filled = {k: v for k, v in _notes.items() if v.strip()}
            if _notes_filled:
                st.markdown("---")
                with st.expander("📋 Export discussion notes", expanded=False):
                    st.caption("Copy this summary to use in your check-in with teachers.")
                    _export_txt = f"Leadership Check-in Notes — {_prog} Program\n"
                    _export_txt += f"Generated: {date.today().strftime('%d %B %Y')}\n\n"
                    for _sname, _snote in _notes_filled.items():
                        _export_txt += f"{'─'*50}\n{_sname}\n{_snote}\n\n"
                    st.text_area("", value=_export_txt.strip(), height=200,
                                 key=f"ld_export_{_prog}")



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
            st.download_button(
                "⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"{selected_name}_SMARTAR_Progress_Report.pdf",
                mime="application/pdf",
                key="dl_pdf_final",
            )


# ══════════════════════════════════════════════════════════════════════════════
# 5. ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
elif view == "⚙️ Admin Panel":
    st.title("⚙️ Admin Panel")
    st.caption("Manage students · Pre-populate goals from entry meetings · Edit existing goals")

    tab_students, tab_edit, tab_prepop = st.tabs([
        "👥 Manage Students", "📝 Edit Goals", "➕ Pre-populate Goals",
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
                st.markdown(
                    '<div class="period-box" style="margin-bottom:10px;">'
                    'This student is archived — hidden from active views but all data is intact. '
                    'Choose an action below.</div>',
                    unsafe_allow_html=True,
                )
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("♻️ Restore to Active",
                                 key=f"restore_s_{s['id']}", type="primary",
                                 help="Return student to active — they will reappear in Goal Builder and tracking"):
                        sb.table("smartar_students").update({"active": True}).eq("id", s["id"]).execute()
                        st.success("✅ Restored to active.")
                        st.rerun()
                with c2:
                    if st.button("🏁 End Placement",
                                 key=f"end_s_{s['id']}",
                                 help="Student has left CLC — data preserved permanently, no longer tracked"):
                        st.session_state[f"confirm_end_s_{s['id']}"] = True
                with c3:
                    if st.button("🗑 Permanently Delete",
                                 key=f"del_s_{s['id']}",
                                 help="For students entered in error — removes all data and cannot be undone"):
                        st.session_state[f"confirm_delete_s_{s['id']}"] = True

                # End Placement confirmation
                if st.session_state.get(f"confirm_end_s_{s['id']}"):
                    st.markdown(
                        f'<div class="period-box">🏁 <b>End placement for {s["student_name"]}?</b><br>'
                        f'All goals and tracking data will be preserved permanently in the archive. '
                        f'The student will no longer appear in Goal Builder, tracking, or reports.</div>',
                        unsafe_allow_html=True,
                    )
                    _ea, _eb = st.columns(2)
                    with _ea:
                        if st.button("Yes — end placement",
                                     key=f"end_s_conf_{s['id']}", type="primary"):
                            sb.table("smartar_students").update({
                                "active": False, "placement_ended": True
                            }).eq("id", s["id"]).execute()
                            st.session_state.pop(f"confirm_end_s_{s['id']}", None)
                            st.success(f"🏁 {s['student_name']} — placement ended. Data preserved.")
                            st.rerun()
                    with _eb:
                        if st.button("Cancel", key=f"end_s_cancel_{s['id']}"):
                            st.session_state.pop(f"confirm_end_s_{s['id']}", None)
                            st.rerun()

                # Permanent delete confirmation
                if st.session_state.get(f"confirm_delete_s_{s['id']}"):
                    st.markdown(
                        f'<div class="alert-box">⚠️ <b>Permanently delete {s["student_name"]}?</b><br>'
                        f'Use this only if the student was <b>entered in error</b>. '
                        f'This will permanently remove the student record, <b>all goals</b>, '
                        f'and <b>all tracking data</b>. This cannot be undone.</div>',
                        unsafe_allow_html=True,
                    )
                    _da, _db = st.columns(2)
                    with _da:
                        if st.button(f"Yes — permanently delete",
                                     key=f"del_s_conf_{s['id']}", type="primary"):
                            try:
                                _del_goals = sb.table("smartar_goals").select("id").eq(
                                    "student_name", s["student_name"]
                                ).execute().data or []
                                for _dg in _del_goals:
                                    sb.table("smartar_tracking").delete().eq(
                                        "goal_id", _dg["id"]
                                    ).execute()
                                sb.table("smartar_goals").delete().eq(
                                    "student_name", s["student_name"]
                                ).execute()
                                sb.table("smartar_students").delete().eq(
                                    "id", s["id"]
                                ).execute()
                                st.session_state.pop(f"confirm_delete_s_{s['id']}", None)
                                st.success(f"✅ {s['student_name']} and all data permanently deleted.")
                                st.rerun()
                            except Exception as _de:
                                st.error(f"Delete error: {_de}")
                    with _db:
                        if st.button("Cancel", key=f"del_s_cancel_{s['id']}"):
                            st.session_state.pop(f"confirm_delete_s_{s['id']}", None)
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
