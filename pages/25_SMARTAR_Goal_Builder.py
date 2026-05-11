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

    # ── Step 2: Exclusion goal ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Step 2 — Exclusion Goal from Home School")
    st.caption(
        "Paste the exclusion goal exactly as received from the student's home school. "
        "This will be visible to all staff in the Goal Builder."
    )
    ns_excl = st.text_area(
        "🏫 Exclusion Goal",
        placeholder=(
            "e.g. The student will reduce incidents of physical aggression towards peers "
            "to fewer than 2 per week across a 4-week period…"
        ),
        height=100,
        key="ns_excl",
    )

    # ── Step 3: Entry SMARTAR goal ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Step 3 — Entry SMARTAR Goal")
    st.caption(
        "Enter the initial SMARTAR goal for this student. This is the starting point — "
        "teachers will refine this further using the hierarchy of prompts or AI tools in the Goal Builder. "
        "Type directly or use the AI helper below."
    )

    # Optional AI help for entry goal
    if groq_client:
        with st.expander("✨ Need help writing the entry goal? Use AI to draft it.", expanded=False):
            st.caption(
                "Briefly describe what you know so far about the key behaviour of concern "
                "and the AI will draft a starting SMARTAR goal."
            )
            _ns_beh = st.text_area(
                "What is the primary behaviour of concern?",
                placeholder=(
                    "e.g. Student has been excluded for frequent physical altercations with peers "
                    "during unstructured time. Has difficulty regulating when frustrated…"
                ),
                height=80,
                key="ns_beh_brief",
            )
            if st.button(
                "🤖 Draft Entry Goal",
                key="ns_draft_btn",
                disabled=not _ns_beh.strip(),
            ):
                with st.spinner("Drafting entry SMARTAR goal…"):
                    _ns_draft_prompt = f"""You are an expert at writing initial SMARTAR goals for students being enrolled in an alternative education setting (CLC Learning and Behaviour Unit, Adelaide SA).

Write ONE entry-level SMARTAR goal based on this behaviour of concern:
{_ns_beh.strip()}

Rules:
- Use "[Student]" as a placeholder for the student's name
- Target the REPLACEMENT behaviour (what the student WILL DO)
- Be achievable as an entry-level goal — don't set the bar too high initially
- Use trauma-informed, strengths-based language (PBS/BSEM framework)
- One sentence only — no preamble
- Include a realistic prompt level and success rate for an entry goal

Return ONLY the goal sentence — nothing else."""
                    try:
                        _ns_draft = groq_call(_ns_draft_prompt)
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
                    f'<div class="smartar-box">🤖 <b>AI Draft:</b> {st.session_state["ns_entry_draft"]}</div>',
                    unsafe_allow_html=True,
                )
                if st.button("✅ Use this as my entry goal", key="ns_use_draft"):
                    st.session_state["ns_entry_goal_prefill"] = st.session_state["ns_entry_draft"]
                    st.rerun()

    _ns_goal_default = st.session_state.get("ns_entry_goal_prefill", "")
    ns_entry_goal = st.text_area(
        "🎯 Entry SMARTAR Goal",
        value=_ns_goal_default,
        placeholder=(
            "e.g. Jordan will use a calm-down card to request a break when feeling "
            "overwhelmed during structured tasks in the classroom, one to one, with a "
            "verbal prompt from an adult, on 3 out of 5 opportunities."
        ),
        height=110,
        key=f"ns_entry_goal_{hash(_ns_goal_default)}",
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    _ns_ready = (
        ns_name.strip()
        and ns_entry_goal.strip()
        and ns_name.strip().lower() not in _existing_names
    )
    if not ns_name.strip():
        st.caption("💡 Enter a student name to enable save.")
    elif ns_name.strip().lower() in _existing_names:
        st.caption("⚠️ Student already exists — go to Goal Builder.")
    elif not ns_entry_goal.strip():
        st.caption("💡 Enter an entry SMARTAR goal (Step 3) to enable save.")

    if st.button(
        "💾 Save Student & Entry Goal",
        type="primary",
        key="ns_save",
        disabled=not _ns_ready,
    ):
        try:
            # 1. Create student record
            sb.table("smartar_students").insert({
                "student_name": ns_name.strip(),
                "program":      ns_prog,
                "active":       True,
            }).execute()
            # 2. Create initial goal record
            _ns_goal_rec = {
                "student_name":  ns_name.strip(),
                "exclusion_goal": ns_excl.strip() if ns_excl.strip() else None,
                "smartar_goal":  ns_entry_goal.strip(),
                "tracking_period": "All Day",
                "active":        True,
                "status":        "Active",
                "start_date":    date.today().isoformat(),
            }
            sb.table("smartar_goals").insert(_ns_goal_rec).execute()
            # Clear draft state
            for _nk in ["ns_entry_draft", "ns_entry_goal_prefill"]:
                st.session_state.pop(_nk, None)
            st.success(
                f"✅ **{ns_name.strip()}** added to **{ns_prog}** with entry goal saved. "
                f"Teachers can now open this student in the Goal Builder to refine the goal."
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
    _archived_s_list = [s for s in get_students(include_archived=True) if not s.get("active", True)]
    if _archived_s_list:
        st.markdown("---")
        with st.expander(f"🗃️ Archived Students ({len(_archived_s_list)}) — restore or permanently delete", expanded=False):
            st.caption("Archived students are hidden from Goal Builder and tracking views but all data is preserved unless permanently deleted.")
            for _as in _archived_s_list:
                _asg = get_goals(_as["student_name"], active_only=False)
                _ac1, _ac2, _ac3 = st.columns([3, 1, 1])
                _ac1.write(f"**{_as['student_name']}** — {_as.get('program','?')} — {len(_asg)} goal(s)")
                with _ac2:
                    if st.button("♻️ Restore", key=f"ns_restore_{_as['id']}"):
                        sb.table("smartar_students").update({"active": True}).eq("id", _as["id"]).execute()
                        st.success(f"✅ {_as['student_name']} restored.")
                        st.rerun()
                with _ac3:
                    if st.button("🗑 Delete", key=f"ns_del_{_as['id']}"):
                        st.session_state[f"ns_del_confirm_{_as['id']}"] = True

                if st.session_state.get(f"ns_del_confirm_{_as['id']}"):
                    st.markdown(
                        f'<div class="alert-box">⚠️ <b>Permanently delete {_as["student_name"]}?</b><br>'
                        f'This will delete the student record, all goals, and all tracking data. '
                        f'This cannot be undone.</div>',
                        unsafe_allow_html=True,
                    )
                    _nda, _ndb = st.columns(2)
                    with _nda:
                        if st.button(f"Yes — permanently delete {_as['student_name']}",
                                     key=f"ns_del_conf_{_as['id']}", type="primary"):
                            try:
                                _del_gs = sb.table("smartar_goals").select("id").eq(
                                    "student_name", _as["student_name"]
                                ).execute().data or []
                                for _dg in _del_gs:
                                    sb.table("smartar_tracking").delete().eq("goal_id", _dg["id"]).execute()
                                sb.table("smartar_goals").delete().eq("student_name", _as["student_name"]).execute()
                                sb.table("smartar_students").delete().eq("id", _as["id"]).execute()
                                st.session_state.pop(f"ns_del_confirm_{_as['id']}", None)
                                st.success(f"✅ {_as['student_name']} permanently deleted.")
                                st.rerun()
                            except Exception as _nde:
                                st.error(f"Delete error: {_nde}")
                    with _ndb:
                        if st.button("Cancel", key=f"ns_del_cancel_{_as['id']}"):
                            st.session_state.pop(f"ns_del_confirm_{_as['id']}", None)
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 3. GOAL BUILDER  (teachers)
# ══════════════════════════════════════════════════════════════════════════════
elif view == "📋 Goal Builder":
    st.title("📋 SMARTAR Goal Builder")
    st.caption(
        "Select a student to view their current goals, then refine using the hierarchy builder or AI tool."
    )

    students = get_students()
    if not students:
        st.info("No students set up yet. Ask your coordinator to add students via **New Student Setup**.")
        st.stop()

    student_options = {s["student_name"]: s for s in students}
    if integration["active"] and integration["student"]:
        default_idx = (list(student_options.keys()).index(integration["student"])
                       if integration["student"] in student_options else 0)
    else:
        default_idx = 0

    selected_name  = st.selectbox("Select student", list(student_options.keys()), index=default_idx)
    student        = student_options[selected_name]
    existing_goals = get_goals(selected_name, active_only=True)
    archived_goals = [g for g in get_goals(selected_name, active_only=False) if not g.get("active", True)]

    st.markdown(
        f'<div class="student-header"><b>{selected_name}</b> · '
        f'{student.get("program","?")} · {len(existing_goals)} active goal(s)</div>',
        unsafe_allow_html=True,
    )

    # ── Current goals: show exclusion + SMARTAR prominently ──────────────────
    if existing_goals:
        st.subheader("Current Goals")
        for idx, g in enumerate(existing_goals, 1):
            goal_text        = g.get("smartar_goal", "No goal text")
            needs_ref, low_c = check_goal_needs_refinement(g["id"])
            period           = g.get("tracking_period", "All Day")
            with st.expander(
                f"Goal {idx} — {_short(goal_text, 80)}" + (" ⚠️ NEEDS REFINEMENT" if needs_ref else ""),
                expanded=True,
            ):
                if needs_ref:
                    st.markdown(
                        f'<div class="alert-box">⚠️ <b>Action Required:</b> {low_c} recent sessions '
                        f'show NOT YET. Please refine this goal.</div>', unsafe_allow_html=True,
                    )
                if g.get("exclusion_goal"):
                    st.markdown(
                        f'<div class="exclusion-box">🏫 <b>Exclusion Goal from Home School:</b> '
                        f'{g.get("exclusion_goal","—")}</div>', unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div class="smartar-box">🎯 <b>Current SMARTAR Goal:</b> {goal_text}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="period-box">📅 Tracking period: <strong>{period}</strong>'
                    f' — {", ".join(SESSIONS_FOR_PERIOD.get(period, ALL_SESSIONS))}</div>',
                    unsafe_allow_html=True,
                )
                gas = get_gas_dict(g)
                if any(gas.values()):
                    with st.expander("📊 GAS Performance Levels"):
                        for lvl in LEVEL_ORDER:
                            desc = gas.get(lvl, "")
                            if desc:
                                st.markdown(
                                    f'<div class="gas-level-bar"><span class="gas-level-label" '
                                    f'style="color:{LEVEL_COLOR[lvl]}">{LEVEL_EMOJI[lvl]} {lvl}</span>'
                                    f'<span class="gas-level-desc">{desc}</span></div>',
                                    unsafe_allow_html=True,
                                )
                if g.get("meeting_id"):
                    st.caption(f"📋 {g.get('program','')} Team Meeting · Term {g.get('term','')} Week {g.get('week','')}")

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

    # ── Archived goals ────────────────────────────────────────────────────────
    if archived_goals:
        with st.expander(f"🗃️ Archived Goals ({len(archived_goals)})", expanded=False):
            st.caption("Preserved with all tracking data.")
            for ag in archived_goals:
                ag_text = ag.get("smartar_goal","—")
                with st.expander(f"🟠 {_short(ag_text, 70)} — archived {(ag.get('archived_at') or '')[:10]}", expanded=False):
                    st.markdown(f'<div class="archived-box">🎯 {ag_text}</div>', unsafe_allow_html=True)
                    if ag.get("archive_reason"):
                        st.caption(f"Reason: {ag['archive_reason']}")
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        if st.button("♻️ Restore", key=f"restore_gb_{ag['id']}", type="primary"):
                            if restore_goal(ag["id"]):
                                st.success("✅ Goal restored.")
                                st.rerun()
                    with rc2:
                        if st.button("➕ Build Updated Goal from this", key=f"upd_gb_{ag['id']}"):
                            st.session_state["build_new_after_archive"] = True
                            st.session_state["archived_excl_goal"]      = ag.get("exclusion_goal","")
                            st.session_state["archived_smartar_goal"]   = ag.get("smartar_goal","")
                            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # REFINE / ADD GOAL — three-tab structure
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    build_after_archive = st.session_state.get("build_new_after_archive", False)
    _archived_excl      = st.session_state.get("archived_excl_goal", "")
    _archived_smartar   = st.session_state.get("archived_smartar_goal", "")
    _current_smartar    = existing_goals[0].get("smartar_goal","") if existing_goals else ""
    _current_excl       = existing_goals[0].get("exclusion_goal","") if existing_goals else ""

    if build_after_archive:
        st.markdown(
            f'<div class="success-box">✅ Goal archived. Build an updated SMARTAR goal for '
            f'<strong>{selected_name}</strong> using one of the paths below.</div>',
            unsafe_allow_html=True,
        )
        if st.button("✖ Cancel", key="cancel_new_after_arch"):
            for _ck in ["build_new_after_archive","archived_excl_goal","archived_student","archived_smartar_goal"]:
                st.session_state.pop(_ck, None)
            st.rerun()

    st.subheader("Refine or Add a Goal")
    _ref_tab, _ai_tab, _mgmt_tab = st.tabs([
        "📐 Manual — Hierarchy Builder",
        "✨ AI Goal Tool",
        "⚙️ Manage Student",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1: MANUAL HIERARCHY BUILDER
    # ─────────────────────────────────────────────────────────────────────────
    with _ref_tab:
        st.caption("Build a precise SMARTAR goal by selecting each element of the hierarchy of prompts.")
        excl_goal_default = _archived_excl or _current_excl
        if excl_goal_default:
            st.markdown(
                f'<div class="exclusion-box">🏫 <b>Exclusion Goal (reference):</b> '
                f'{excl_goal_default}</div>', unsafe_allow_html=True,
            )
        excl_goal = st.text_area(
            "🏫 Exclusion Goal — update if changed (leave blank to keep existing)",
            value=excl_goal_default, height=70, key="hb_excl_goal",
            placeholder="Paste updated exclusion goal, or leave as-is…",
        )

        st.markdown("**Build the SMARTAR Goal using the Hierarchy of Prompts**")
        _ai_skill_hint = st.session_state.get("ai_prefill_skill","")
        _ai_task_hint  = st.session_state.get("ai_prefill_task","")
        if _ai_skill_hint or _ai_task_hint:
            st.caption(f"💡 AI suggestions — Skill: *{_ai_skill_hint}*" +
                       (f"  ·  Task type: **{_ai_task_hint}**" if _ai_task_hint else ""))

        col1, col2 = st.columns(2)
        with col1:
            student_first = st.text_input("Student first name", value=selected_name.split()[0], key="hb_first")
            skill = st.text_area("Expected skill / behaviour", value=_ai_skill_hint,
                                  placeholder="e.g. use a break card to request a break",
                                  height=80, key="hb_skill")
            grouping  = st.selectbox("Grouping", GROUPINGS, key="hb_grouping")
            _task_idx = TASK_TYPES.index(_ai_task_hint) if _ai_task_hint in TASK_TYPES else 0
            task_type = st.selectbox("Task type", TASK_TYPES, index=_task_idx, key="hb_task")
        with col2:
            setting = st.selectbox("Setting", SETTINGS, key="hb_setting")
            prompts = st.selectbox("Prompt level (Hierarchy of Prompts)", PROMPT_TYPES, key="hb_prompts")
            rate    = st.selectbox("Rate / success criteria", RATE_OPTIONS, key="hb_rate")

        assembled = (
            f"{student_first} will {skill} {grouping.lower()} during {task_type.lower()} "
            f"in the {setting.lower()} with {prompts.lower()}, demonstrating successful use on {rate}."
            if skill and student_first else ""
        )
        if assembled:
            st.session_state["gb_assembled"] = assembled
        current_assembled = st.session_state.get("gb_assembled","")
        if current_assembled:
            st.markdown("**Assembled Goal Preview:**")
            st.info(current_assembled)

        st.markdown("---")
        st.markdown("**Refine and Finalise**")
        refine_col, _ = st.columns([2, 3])
        with refine_col:
            if st.button("✨ Refine with AI", type="primary", key="hb_refine_btn",
                         disabled=not current_assembled.strip()):
                if not groq_client:
                    st.warning("⚠️ AI unavailable.")
                else:
                    with st.spinner("Refining…"):
                        try:
                            refined = groq_call(
                                f"""Rewrite into ONE fluent professional SMARTAR goal sentence.
Rules: fix doubled words; start "{student_first} will..."; keep ALL specific details;
one sentence only; trauma-informed strengths-based language (PBS/BSEM);
do NOT add "appropriately" or "independently" unless already present.
Goal: {current_assembled}
Return ONLY the final goal statement."""
                            )
                            if refined and len(refined) > 20 and "[AI unavailable" not in refined:
                                st.session_state["refined_goal"]    = refined.strip().strip('"').strip("'")
                                st.session_state["gb_goal_for_gas"] = st.session_state["refined_goal"]
                                st.session_state.pop("gas_levels", None)
                                st.session_state.pop("gb_ai_period", None)
                                st.rerun()
                        except Exception as e:
                            st.error(f"AI error: {e}")
        if not current_assembled.strip():
            st.caption("💡 Complete skill/behaviour above to enable AI refinement.")

        _goal_default = st.session_state.get("refined_goal") or current_assembled or ""
        final_goal    = st.text_area("Final SMARTAR Goal (edit if needed)", value=_goal_default,
                                     height=100, key=f"hb_final_goal_{hash(_goal_default)}")
        if final_goal and final_goal != st.session_state.get("refined_goal"):
            st.session_state["refined_goal"] = final_goal

        # Auto GAS
        _gas_source = st.session_state.get("refined_goal") or current_assembled
        if _gas_source and groq_client and not st.session_state.get("gas_levels"):
            with st.spinner("🤖 Auto-generating GAS levels…"):
                try:
                    _gr = groq_call(
                        f"""GAS for: "{_gas_source}"
EXPECTED (0) = goal verbatim. Scale only rate/criteria.
Return ONLY JSON: {{"EXCEEDING":"...","ABOVE":"...","EXPECTED":"...","BELOW":"...","NOT_YET":"..."}}"""
                    )
                    _gp = json.loads(_gr.strip().strip("```json").strip("```").strip())
                    if "NOT_YET" in _gp:
                        _gp["NOT YET"] = _gp.pop("NOT_YET")
                    st.session_state["gas_levels"]      = _gp
                    st.session_state["gas_last_source"] = _gas_source
                    st.rerun()
                except Exception:
                    pass

        # Tracking period
        st.markdown("---")
        st.markdown("**Tracking Period**")
        ai_period_result = st.session_state.get("gb_ai_period")
        if final_goal.strip():
            if st.button("🤖 Check with AI", key="hb_check_period"):
                with st.spinner("Analysing…"):
                    ai_period_result = ai_check_period(final_goal)
                    st.session_state["gb_ai_period"] = ai_period_result
                    st.rerun()
        suggested = "All Day"
        if ai_period_result:
            st.info(f"**AI Recommendation:** {ai_period_result['period']}\n\n"
                    f"*{ai_period_result.get('reasoning','')}*  \nConfidence: {ai_period_result.get('confidence','Low')}")
            suggested = ai_period_result.get("period","All Day")
            if suggested not in TRACKING_PERIODS:
                suggested = "All Day"
        tracking_period = st.selectbox("Tracking Period", TRACKING_PERIODS,
                                       index=TRACKING_PERIODS.index(suggested), key="hb_tracking_period")
        st.caption(f"📅 Sessions: **{', '.join(SESSIONS_FOR_PERIOD[tracking_period])}**")

        # GAS levels
        st.markdown("---")
        st.markdown("**Goal Attainment Scaling (GAS)**")
        if groq_client and final_goal:
            if st.button("🔄 Re-generate GAS", key="hb_gen_gas"):
                with st.spinner("Generating…"):
                    try:
                        _rg = json.loads(groq_call(
                            f"""GAS for: "{final_goal}"
EXPECTED = goal verbatim. Scale only rate/criteria.
Return ONLY JSON: {{"EXCEEDING":"...","ABOVE":"...","EXPECTED":"...","BELOW":"...","NOT_YET":"..."}}"""
                        ).strip().strip("```json").strip("```").strip())
                        if "NOT_YET" in _rg:
                            _rg["NOT YET"] = _rg.pop("NOT_YET")
                        st.session_state["gas_levels"] = _rg
                        st.rerun()
                    except Exception as e:
                        st.error(f"Parse error: {e}")

        gas_levels = st.session_state.get("gas_levels",{})
        edited_gas = {}
        _gas_ver   = hash(str(sorted(gas_levels.items()))) if gas_levels else 0
        for lvl in LEVEL_ORDER:
            _key    = lvl if lvl in gas_levels else lvl.replace(" ","_")
            default = gas_levels.get(lvl, gas_levels.get(_key,""))
            edited_gas[lvl] = st.text_area(f"{LEVEL_EMOJI[lvl]} {lvl}", value=default, height=70,
                                           key=f"hb_gas_edit_{lvl}_{_gas_ver}")

        # Save
        st.markdown("---")
        if st.button("💾 Save Goal", type="primary", disabled=not final_goal, key="hb_save_goal"):
            new_goal = {
                "student_name":    selected_name,
                "exclusion_goal":  excl_goal.strip() if excl_goal.strip() else None,
                "smartar_goal":    final_goal.strip(),
                "skill":           skill.strip() if skill else None,
                "grouping":        grouping, "task_type": task_type,
                "setting":         setting,  "prompts":   prompts, "rate": rate,
                "tracking_period": tracking_period,
                "active":          True, "status": "Active",
                "start_date":      date.today().isoformat(),
                "gas_exceeding":   edited_gas.get("EXCEEDING",""),
                "gas_above":       edited_gas.get("ABOVE",""),
                "gas_expected":    edited_gas.get("EXPECTED",""),
                "gas_below":       edited_gas.get("BELOW",""),
                "gas_not_yet":     edited_gas.get("NOT YET",""),
            }
            if integration["active"]:
                new_goal.update({"meeting_id": integration["meeting_id"],
                                 "program": integration["program"],
                                 "term": integration["term"], "week": integration["week"]})
            try:
                sb.table("smartar_goals").insert(new_goal).execute()
                for k in ["refined_goal","gas_levels","gb_ai_period","gb_assembled","gb_goal_for_gas",
                          "build_new_after_archive","archived_excl_goal","archived_student",
                          "archived_smartar_goal","ai_gen_goals","ai_gen_analysis","ai_gen_multiple",
                          "ai_gen_count","ai_queued_goals","ai_prefill_skill","ai_prefill_task",
                          "ai_mod_result","ai_mod_gas"]:
                    st.session_state.pop(k, None)
                st.success(f"✅ Goal saved for {selected_name}!")
                if integration["active"]:
                    st.markdown(f"[← Return to Team Meeting](https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']})")
                st.rerun()
            except Exception as e:
                st.error(f"Save error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2: AI GOAL TOOL
    # ─────────────────────────────────────────────────────────────────────────
    with _ai_tab:
        if not groq_client:
            st.warning("⚠️ Groq AI is not configured — GROQ_API_KEY missing.")
            st.stop()

        _ai_mode_options = [
            "🔧 Modify / refine the current SMARTAR goal",
            "🔄 Create a new replacement goal based on observed behaviours",
        ]
        if not existing_goals and not build_after_archive:
            st.info("No current goal found — using 'Create new replacement goal' mode.")
            _ai_mode = _ai_mode_options[1]
        else:
            _ai_mode = st.radio("What would you like to do?", _ai_mode_options, key="ai_tool_mode")

        st.markdown("---")

        def _replace_student(text):
            return (text.replace("[Student]", selected_name.split()[0])
                        .replace("[student]", selected_name.split()[0]))

        def _gen_gas_ai(goal_text):
            try:
                _gr = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role":"user","content":
                        f"""GAS for: {goal_text}
EXPECTED (0) = goal verbatim. Scale only rate/criteria above and below.
Return ONLY valid JSON: {{"EXCEEDING":"...","ABOVE":"...","EXPECTED":"...","BELOW":"...","NOT_YET":"..."}}"""}],
                    response_format={"type":"json_object"}, max_tokens=500, temperature=0.1,
                )
                _gp = json.loads(_gr.choices[0].message.content.strip())
                if "NOT_YET" in _gp:
                    _gp["NOT YET"] = _gp.pop("NOT_YET")
                return _gp
            except Exception:
                return {}

        # ── MODE A: MODIFY ────────────────────────────────────────────────────
        if _ai_mode == _ai_mode_options[0]:
            st.markdown("**🔧 Modify / refine the current SMARTAR goal**")
            st.caption("The AI modifies the existing goal based on what you describe — same student, evolved skill.")
            _base_goal = _archived_smartar or _current_smartar
            if _base_goal:
                st.markdown(
                    f'<div class="smartar-box">🎯 <b>Current goal (base):</b> {_base_goal}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No current SMARTAR goal found.")

            _mod_desc = st.text_area(
                "📝 What behaviours are you observing? What needs to change in the goal?",
                placeholder=(
                    "e.g. The student now manages the initial break request but struggles to return "
                    "to task after the break. Goal should now focus on returning to work within 5 minutes…"
                ),
                height=120, key="ai_mod_desc",
            )
            _mod_c1, _mod_c2 = st.columns(2)
            with _mod_c1:
                _mod_prompt  = st.selectbox("Target prompt level", PROMPT_TYPES, key="ai_mod_prompt")
                _mod_rate    = st.selectbox("Target success rate",  RATE_OPTIONS,  key="ai_mod_rate")
            with _mod_c2:
                _mod_setting  = st.selectbox("Setting",  SETTINGS,  key="ai_mod_setting")
                _mod_grouping = st.selectbox("Grouping", GROUPINGS, key="ai_mod_grouping")

            if st.button("🤖 Generate Modified Goal", type="primary", key="ai_mod_generate",
                         disabled=not (_mod_desc.strip() and _base_goal)):
                with st.spinner("Generating…"):
                    _mp = f"""You are an expert at writing SMARTAR goals (trauma-informed, PBS, BSEM, alternative education).

CURRENT GOAL: {_base_goal}

OBSERVED BEHAVIOURS / REQUESTED CHANGES: {_mod_desc.strip()}

UPDATED CONTEXT:
- Setting: {_mod_setting} | Grouping: {_mod_grouping}
- Prompt level: {_mod_prompt} | Success rate: {_mod_rate}

TASK: Modify the current goal to address the described changes.
✅ ONE sentence, ONE target behaviour/skill
✅ Build on the existing goal unless change is fundamental
✅ Keep the student name exactly as written
✅ Trauma-informed, strengths-based language
❌ Never contain "and" joining two separate actions
❌ No preamble, no explanation

Return ONLY the modified goal sentence."""
                    try:
                        _mr = groq_call(_mp)
                        if _mr and len(_mr) > 20 and "[AI unavailable" not in _mr:
                            st.session_state["ai_mod_result"] = _mr.strip().strip('"').strip("'")
                            st.rerun()
                    except Exception as _me:
                        st.error(f"AI error: {_me}")

            if not (_mod_desc.strip() and _base_goal):
                st.caption("💡 Describe the behaviours / changes above to enable generation.")

            if st.session_state.get("ai_mod_result"):
                st.markdown("---")
                st.markdown("**✅ Modified Goal — Review and Save:**")
                _mod_ver  = hash(st.session_state.get("ai_mod_result",""))
                _mod_edit = st.text_area("Edit directly if needed",
                                         value=st.session_state["ai_mod_result"], height=95,
                                         key=f"ai_mod_edit_{_mod_ver}")
                if _mod_edit.strip() and _mod_edit != st.session_state.get("ai_mod_result"):
                    st.session_state["ai_mod_result"] = _mod_edit.strip()

                _mod_excl   = st.text_area("🏫 Exclusion goal (leave blank to keep existing)",
                                           value=_archived_excl or _current_excl, height=65,
                                           key="ai_mod_excl")
                _mod_period = st.selectbox("Tracking period", TRACKING_PERIODS, key="ai_mod_period")

                if not st.session_state.get("ai_mod_gas"):
                    if st.button("📊 Auto-generate GAS", key="ai_mod_gen_gas"):
                        with st.spinner("Generating GAS…"):
                            st.session_state["ai_mod_gas"] = _gen_gas_ai(_mod_edit)
                            st.rerun()

                _mod_gas = st.session_state.get("ai_mod_gas",{})
                _mod_edited_gas = {}
                if _mod_gas:
                    with st.expander("📊 GAS Levels (edit if needed)"):
                        _mgver = hash(str(sorted(_mod_gas.items())))
                        for _lvl in LEVEL_ORDER:
                            _mk    = _lvl if _lvl in _mod_gas else _lvl.replace(" ","_")
                            _mod_edited_gas[_lvl] = st.text_area(
                                f"{LEVEL_EMOJI[_lvl]} {_lvl}",
                                value=_mod_gas.get(_lvl, _mod_gas.get(_mk,"")), height=60,
                                key=f"mod_gas_{_lvl}_{_mgver}",
                            )

                if st.button("💾 Save Modified Goal", type="primary", key="ai_mod_save",
                             disabled=not _mod_edit.strip()):
                    _fmgas = _mod_edited_gas or _mod_gas
                    try:
                        sb.table("smartar_goals").insert({
                            "student_name":    selected_name,
                            "exclusion_goal":  _mod_excl.strip() or _current_excl or None,
                            "smartar_goal":    _mod_edit.strip(),
                            "tracking_period": _mod_period,
                            "active":          True, "status": "Active",
                            "start_date":      date.today().isoformat(),
                            "gas_exceeding":   _fmgas.get("EXCEEDING",""),
                            "gas_above":       _fmgas.get("ABOVE",""),
                            "gas_expected":    _fmgas.get("EXPECTED",""),
                            "gas_below":       _fmgas.get("BELOW",""),
                            "gas_not_yet":     _fmgas.get("NOT YET",""),
                        }).execute()
                        for _mk2 in ["ai_mod_result","ai_mod_gas","build_new_after_archive",
                                     "archived_excl_goal","archived_smartar_goal"]:
                            st.session_state.pop(_mk2, None)
                        st.success(f"✅ Modified goal saved for {selected_name}!")
                        st.rerun()
                    except Exception as _mse:
                        st.error(f"Save error: {_mse}")

        # ── MODE B: NEW REPLACEMENT GOAL ──────────────────────────────────────
        else:
            st.markdown("**🔄 Create new replacement goal based on observed behaviours**")
            st.caption(
                "Describe what you are observing. The AI analyses the behaviours, "
                "identifies if multiple distinct goals are needed, and generates one per behaviour."
            )
            if _current_excl or _archived_excl:
                st.markdown(
                    f'<div class="exclusion-box">🏫 <b>Exclusion Goal (reference):</b> '
                    f'{_current_excl or _archived_excl}</div>', unsafe_allow_html=True,
                )

            beh_desc = st.text_area(
                "📝 Describe the behaviour(s) of concern you are observing",
                placeholder=(
                    "e.g. The student frequently leaves their seat during structured tasks, "
                    "calls out without permission, and also struggles with peer conflict at recess…"
                ),
                height=130, key="beh_desc_input",
            )
            _bg1, _bg2 = st.columns(2)
            with _bg1:
                beh_setting  = st.selectbox("Primary setting", SETTINGS,   key="beh_setting_input")
                beh_grouping = st.selectbox("Grouping context", GROUPINGS, key="beh_grouping_input")
            with _bg2:
                beh_prompt = st.selectbox("Target prompt level", PROMPT_TYPES, key="beh_prompt_input")
                beh_rate   = st.selectbox("Target success rate",  RATE_OPTIONS,  key="beh_rate_input")
            beh_extras = st.text_area(
                "Additional context (optional)",
                placeholder="e.g. responds well to visual supports; peer conflict is a trigger…",
                height=60, key="beh_extras_input",
            )

            if st.button("🤖 Analyse & Generate Goals", type="primary", key="gen_from_beh",
                         disabled=not st.session_state.get("beh_desc_input","").strip()):
                with st.spinner("Step 1: Identifying distinct behaviours…"):
                    _extras_line  = (f"\nAdditional context: {beh_extras.strip()}" if beh_extras.strip() else "")
                    _raw_desc     = st.session_state.get("beh_desc_input","").strip()
                    _split_system = ("You are a PBS/ABA specialist. Your only job right now is to "
                                     "IDENTIFY and SEPARATE distinct behaviours — NOT to write goals.")
                    _split_user   = f"""List every DISTINCT behaviour from this description that requires its own SMARTAR goal.

DESCRIPTION: {_raw_desc}{_extras_line}

RULES: Each distinct ACTION = own entry. Different settings = separate entries. Different skills = separate entries.
GOOD SPLIT: "leaves seat, calls out, peer conflict at recess" → 3 entries.
BAD SPLIT: same → "Classroom disruption" (too vague, groups everything).

Return ONLY valid JSON: {{"behaviours": [{{"label": "Short label", "description": "One sentence"}}]}}"""
                    try:
                        _sr = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"system","content":_split_system},
                                      {"role":"user","content":_split_user}],
                            response_format={"type":"json_object"}, max_tokens=600, temperature=0.1,
                        )
                        _behaviours_list = json.loads(_sr.choices[0].message.content.strip()).get("behaviours",[])
                    except Exception as _se:
                        st.error(f"Behaviour analysis error: {_se}")
                        _behaviours_list = []

                if _behaviours_list:
                    with st.spinner(f"Step 2: Writing {len(_behaviours_list)} goal(s)…"):
                        _goal_system = ("Expert SMARTAR goal writer (PBS/ABA, trauma-informed, BSEM). "
                                        "ONE goal per call. ONE skill per goal. "
                                        "NEVER 'and' joining two separate actions.")
                        _goals_out = []
                        for _beh in _behaviours_list:
                            _gu = f"""Write ONE SMARTAR goal for this single behaviour:
BEHAVIOUR: {_beh.get('description', _beh.get('label',''))}
CONTEXT: Setting: {beh_setting} | Grouping: {beh_grouping} | Prompt: {beh_prompt} | Rate: {beh_rate}
✅ ONE replacement behaviour | start "[Student] will..." | one sentence | embed all context naturally | trauma-informed
❌ No "and" joining two actions | no preamble
EXAMPLE: "[Student] will use a break card to request a break when overwhelmed, working independently, with a verbal prompt, on 3 out of 5 opportunities."
Return ONLY JSON: {{"goal":"...","task_type":"Best fit from: {', '.join(TASK_TYPES)}","skill":"ONE core skill (5-10 words)"}}"""
                            try:
                                _gr2 = groq_client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role":"system","content":_goal_system},
                                              {"role":"user","content":_gu}],
                                    response_format={"type":"json_object"}, max_tokens=300, temperature=0.2,
                                )
                                _gp2   = json.loads(_gr2.choices[0].message.content.strip())
                                _raw_g = _replace_student(_gp2.get("goal",""))
                                _goals_out.append({
                                    "behaviour_label": _beh.get("label",""),
                                    "goal": _raw_g, "edited_goal": _raw_g,
                                    "task_type": _gp2.get("task_type",""), "skill": _gp2.get("skill",""),
                                })
                            except Exception as _ge:
                                st.warning(f"Could not generate goal for '{_beh.get('label','')}': {_ge}")

                        if _goals_out:
                            import re as _re
                            for _gitem in _goals_out:
                                if _re.search(r'\bwill\b.+\band\b.+(?:ing|se|ain|rn|ck|out|ort)\b',
                                              _gitem.get("goal",""), _re.IGNORECASE):
                                    _gitem["_and_warning"] = True
                            st.session_state["ai_gen_goals"]    = _goals_out
                            st.session_state["ai_gen_multiple"] = len(_goals_out) > 1
                            st.session_state["ai_gen_count"]    = len(_goals_out)
                            st.session_state["ai_gen_analysis"] = (
                                f"{len(_goals_out)} distinct behaviour(s): " +
                                ", ".join(b.get("label","") for b in _behaviours_list)
                            )
                            st.session_state.pop("ai_queued_goals", None)
                            st.rerun()

            if not st.session_state.get("beh_desc_input","").strip():
                st.caption("💡 Describe the behaviour(s) above to enable AI analysis.")

            # Generated goals
            _gen_goals = st.session_state.get("ai_gen_goals",[])
            if _gen_goals:
                st.markdown("---")
                _is_multi  = st.session_state.get("ai_gen_multiple", False)
                _analysis  = st.session_state.get("ai_gen_analysis","")
                _beh_count = st.session_state.get("ai_gen_count", 1)
                if _is_multi:
                    st.markdown(
                        f'<div class="alert-box">⚠️ <b>{_beh_count} distinct behaviours identified</b> — '
                        f'each needs a separate SMARTAR goal.<br>'
                        f'<span style="font-size:0.88rem">{_analysis}</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.caption("Review each goal, then queue to save.")
                else:
                    st.markdown(
                        f'<div class="success-box">✅ <b>One behaviour identified.</b> '
                        f'<span style="font-size:0.88rem">{_analysis}</span></div>',
                        unsafe_allow_html=True,
                    )

                for _gi, _goal_item in enumerate(_gen_goals):
                    _glabel = _goal_item.get("behaviour_label", f"Goal {_gi+1}")
                    _gver   = hash(_goal_item.get("edited_goal","") + str(_gi))
                    with st.expander(
                        f"{'📌' if _is_multi else '🎯'} {'Goal '+str(_gi+1)+' — ' if _is_multi else ''}{_glabel}",
                        expanded=True,
                    ):
                        st.caption(f"Skill: *{_goal_item.get('skill','')}*  ·  Task type: **{_goal_item.get('task_type','')}**")
                        if _goal_item.get("_and_warning"):
                            st.markdown(
                                '<div class="alert-box">⚠️ This goal may still contain "and" '
                                'linking multiple actions — edit or regenerate.</div>',
                                unsafe_allow_html=True,
                            )
                        _edited = st.text_area("Edit directly if needed",
                                               value=_goal_item.get("edited_goal", _goal_item["goal"]),
                                               height=95, key=f"ai_goal_edit_{_gi}_{_gver}")
                        if _edited.strip() and _edited != _goal_item.get("edited_goal"):
                            st.session_state["ai_gen_goals"][_gi]["edited_goal"] = _edited

                        _add_el = st.text_area("➕ Add missing elements or request changes (optional)",
                                               placeholder="e.g. specify morning only; change success rate to 4/5…",
                                               height=55, key=f"ai_add_elements_{_gi}")
                        _gc1, _gc2, _gc3 = st.columns([2,2,2])
                        with _gc1:
                            if st.button("🔄 Regenerate", key=f"regen_goal_{_gi}",
                                         disabled=not _edited.strip()):
                                with st.spinner("Regenerating…"):
                                    _rp2 = f"""Rewrite as ONE fluent sentence (trauma-informed, PBS).
Goal: {_edited}
{"Changes: " + _add_el.strip() if _add_el.strip() else "Polish only."}
✅ One sentence | one skill | keep student name
❌ No "and" joining two separate actions
Return ONLY the new goal sentence."""
                                    try:
                                        _rr2 = groq_call(_rp2)
                                        if _rr2 and len(_rr2) > 20 and "[AI unavailable" not in _rr2:
                                            st.session_state["ai_gen_goals"][_gi]["edited_goal"] = (
                                                _rr2.strip().strip('"').strip("'"))
                                            st.rerun()
                                    except Exception as _re3:
                                        st.error(f"Error: {_re3}")
                        with _gc2:
                            _queued        = st.session_state.get("ai_queued_goals",[])
                            _already_qued  = any(q["_idx"] == _gi for q in _queued)
                            if _already_qued:
                                st.success("✅ Queued")
                            else:
                                if st.button("📋 Queue to Save", type="primary",
                                             key=f"queue_goal_{_gi}", disabled=not _edited.strip()):
                                    with st.spinner("Generating GAS…"):
                                        _qgas = _gen_gas_ai(_edited.strip())
                                    _q2 = st.session_state.get("ai_queued_goals",[])
                                    _q2.append({
                                        "_idx": _gi, "behaviour_label": _glabel,
                                        "goal": _edited.strip(), "task_type": _goal_item.get("task_type",""),
                                        "skill": _goal_item.get("skill",""), "gas": _qgas,
                                        "tracking_period": "All Day",
                                    })
                                    st.session_state["ai_queued_goals"] = _q2
                                    st.rerun()
                        with _gc3:
                            if not _is_multi:
                                if st.button("✅ Use this Goal →", key=f"use_direct_{_gi}",
                                             disabled=not _edited.strip()):
                                    st.session_state["refined_goal"]     = _edited.strip()
                                    st.session_state["gb_goal_for_gas"]  = _edited.strip()
                                    st.session_state["ai_prefill_skill"] = _goal_item.get("skill","")
                                    st.session_state["ai_prefill_task"]  = _goal_item.get("task_type","")
                                    st.session_state.pop("gas_levels", None)
                                    st.rerun()

                if st.button("🗑 Clear & Start Over", key="clear_ai_gen"):
                    for _k in ["ai_gen_goals","ai_gen_analysis","ai_gen_multiple","ai_gen_count",
                               "ai_queued_goals","ai_prefill_skill","ai_prefill_task"]:
                        st.session_state.pop(_k, None)
                    st.rerun()

            # Queued goals
            _queued_goals = st.session_state.get("ai_queued_goals",[])
            if _queued_goals:
                st.markdown("---")
                st.markdown(
                    f'<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:12px 16px;'
                    f'border-radius:0 8px 8px 0;margin-bottom:12px;">📋 <b>{len(_queued_goals)} '
                    f'goal{"s" if len(_queued_goals)!=1 else ""} queued to save</b></div>',
                    unsafe_allow_html=True,
                )
                _q_excl = st.text_area("🏫 Exclusion goal (shared across queued goals)",
                                       value=_current_excl or _archived_excl or "",
                                       height=65, key="queue_shared_excl")
                _to_remove = []
                for _qi, _qg in enumerate(_queued_goals):
                    _qver = hash(_qg["goal"] + str(_qi))
                    with st.expander(f"📌 Goal {_qi+1} — {_qg['behaviour_label']}", expanded=True):
                        _q_goal_edit = st.text_area("SMARTAR Goal", value=_qg["goal"], height=90,
                                                    key=f"qgoal_edit_{_qi}_{_qver}")
                        if _q_goal_edit.strip() and _q_goal_edit != _qg["goal"]:
                            st.session_state["ai_queued_goals"][_qi]["goal"] = _q_goal_edit.strip()
                        _qadd = st.text_area("➕ Changes (optional)", height=50, key=f"qadd_{_qi}",
                                             placeholder="e.g. morning only; change success rate…")
                        if st.button("🔄 Regenerate", key=f"qregen_{_qi}"):
                            with st.spinner("…"):
                                try:
                                    _qrr2 = groq_call(
                                        f"""Rewrite as ONE sentence (PBS, trauma-informed).
Goal: {_q_goal_edit}
{"Changes: " + _qadd.strip() if _qadd.strip() else "Polish only."}
No "and" joining two actions. Return ONLY new goal sentence."""
                                    )
                                    if _qrr2 and len(_qrr2) > 20 and "[AI unavailable" not in _qrr2:
                                        st.session_state["ai_queued_goals"][_qi]["goal"] = (
                                            _qrr2.strip().strip('"').strip("'"))
                                        with st.spinner("Updating GAS…"):
                                            st.session_state["ai_queued_goals"][_qi]["gas"] = (
                                                _gen_gas_ai(st.session_state["ai_queued_goals"][_qi]["goal"]))
                                        st.rerun()
                                except Exception as _qre2:
                                    st.error(f"Error: {_qre2}")

                        _qperiod_idx = (TRACKING_PERIODS.index(_qg.get("tracking_period","All Day"))
                                        if _qg.get("tracking_period","All Day") in TRACKING_PERIODS else 0)
                        _qperiod = st.selectbox("Tracking period", TRACKING_PERIODS,
                                                index=_qperiod_idx, key=f"qperiod_{_qi}")
                        if _qperiod != _qg.get("tracking_period"):
                            st.session_state["ai_queued_goals"][_qi]["tracking_period"] = _qperiod

                        _qgas    = _qg.get("gas",{})
                        _qed_gas = {}
                        if _qgas:
                            with st.expander("📊 GAS Levels (edit if needed)"):
                                _qgver = hash(str(sorted(_qgas.items())))
                                for _qlvl in LEVEL_ORDER:
                                    _qk    = _qlvl if _qlvl in _qgas else _qlvl.replace(" ","_")
                                    _qed_gas[_qlvl] = st.text_area(
                                        f"{LEVEL_EMOJI[_qlvl]} {_qlvl}",
                                        value=_qgas.get(_qlvl, _qgas.get(_qk,"")), height=60,
                                        key=f"qgas_{_qi}_{_qlvl}_{_qgver}",
                                    )
                                st.session_state["ai_queued_goals"][_qi]["gas_edited"] = _qed_gas
                        else:
                            if st.button("🔄 Generate GAS", key=f"qgas_gen_{_qi}"):
                                with st.spinner("…"):
                                    st.session_state["ai_queued_goals"][_qi]["gas"] = _gen_gas_ai(_q_goal_edit)
                                    st.rerun()

                        _qs1, _qs2 = st.columns([2,2])
                        with _qs1:
                            if st.button(f"💾 Save Goal {_qi+1}", type="primary",
                                         key=f"qsave_{_qi}", disabled=not _q_goal_edit.strip()):
                                _fqgas = _qg.get("gas_edited") or _qg.get("gas",{})
                                try:
                                    sb.table("smartar_goals").insert({
                                        "student_name":    selected_name,
                                        "exclusion_goal":  _q_excl.strip() or None,
                                        "smartar_goal":    _q_goal_edit.strip(),
                                        "tracking_period": _qperiod,
                                        "active": True, "status": "Active",
                                        "start_date": date.today().isoformat(),
                                        "gas_exceeding": _fqgas.get("EXCEEDING",""),
                                        "gas_above":     _fqgas.get("ABOVE",""),
                                        "gas_expected":  _fqgas.get("EXPECTED",""),
                                        "gas_below":     _fqgas.get("BELOW",""),
                                        "gas_not_yet":   _fqgas.get("NOT YET",""),
                                    }).execute()
                                    st.success(f"✅ Goal {_qi+1} saved!")
                                    _to_remove.append(_qi)
                                except Exception as _qse2:
                                    st.error(f"Save error: {_qse2}")
                        with _qs2:
                            if st.button("🗑 Remove from Queue", key=f"qremove_{_qi}"):
                                _to_remove.append(_qi)

                if _to_remove:
                    st.session_state["ai_queued_goals"] = [
                        g for i, g in enumerate(_queued_goals) if i not in _to_remove
                    ]
                    st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3: MANAGE STUDENT
    # ─────────────────────────────────────────────────────────────────────────
    with _mgmt_tab:
        st.caption("Archive this student. To add a new student, use **New Student Setup** in the sidebar.")
        st.subheader(f"Student: {selected_name}")
        st.markdown(f'Program: **{student.get("program","?")}** · Active: **{len(existing_goals)}** · '
                    f'Archived: **{len(archived_goals)}**')
        st.markdown("---")
        if st.button(f"🗑 Archive student — {selected_name}", key="mgmt_archive_student"):
            st.session_state["mgmt_arch_confirm"] = True
        if st.session_state.get("mgmt_arch_confirm"):
            st.warning(f"⚠️ This will archive **{selected_name}**. All data is preserved.")
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
# 4. DAILY TRACKING
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
                c1, c2, c3 = st.columns(3)
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
                with c3:
                    if st.button("🗑 Permanently Delete", key=f"del_s_{s['id']}"):
                        st.session_state[f"confirm_delete_s_{s['id']}"] = True

                if st.session_state.get(f"confirm_delete_s_{s['id']}"):
                    st.markdown(
                        f'<div class="alert-box">⚠️ <b>Permanently delete {s["student_name"]}?</b><br>'
                        f'This will delete the student record, <b>all goals</b>, and <b>all tracking data</b>. '
                        f'This cannot be undone.</div>',
                        unsafe_allow_html=True,
                    )
                    _da, _db = st.columns(2)
                    with _da:
                        if st.button(f"Yes, permanently delete {s['student_name']}",
                                     key=f"del_s_conf_{s['id']}", type="primary"):
                            try:
                                # Cascade: tracking → goals → student
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
                                st.success(f"✅ {s['student_name']} and all associated data permanently deleted.")
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
