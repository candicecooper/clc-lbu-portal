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
@st.cache_resource
def get_supabase():
    # [supabase] section = BEHAVIOUR_SUPABASE_URL (correct project with smartar tables)
    # SUPABASE_URL = main project (different) — must NOT use this as fallback here
    url = (
        st.secrets.get("supabase", {}).get("url")
        or st.secrets.get("BEHAVIOUR_SUPABASE_URL")
    )
    key = (
        st.secrets.get("supabase", {}).get("key")
        or st.secrets.get("BEHAVIOUR_SUPABASE_KEY")
    )
    if not url or not key:
        st.error("⚠️ Supabase credentials not found. Check BEHAVIOUR_SUPABASE_URL in Render environment.")
        st.stop()
    return create_client(url, key)

@st.cache_resource
def get_groq():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)

sb           = get_supabase()
groq_client  = get_groq()

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
    try:
        q = sb.table("smartar_students").select("*").order("student_name")
        if not include_archived:
            q = q.eq("active", True)
        return q.execute().data or []
    except Exception as e:
        st.error(f"DB error loading students: {e}")
        return []


def get_goals(student_name=None, active_only=True):
    try:
        q = sb.table("smartar_goals").select("*")
        if student_name:
            q = q.eq("student_name", student_name)
        if active_only:
            q = q.eq("active", True)
        return q.order("created_at", desc=False).execute().data or []
    except Exception as e:
        st.error(f"DB error loading goals: {e}")
        return []


def get_all_goals_for_student(student_name: str):
    """Returns active + archived goals for a student, newest first."""
    try:
        return (
            sb.table("smartar_goals").select("*")
            .eq("student_name", student_name)
            .order("created_at", desc=True)
            .execute().data or []
        )
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


def upsert_session(goal_id, student_name, session_time, performance_level):
    today = date.today().isoformat()
    try:
        ex = (
            sb.table("smartar_tracking").select("id")
            .eq("goal_id", goal_id)
            .eq("session_date", today)
            .eq("session_time", session_time)
            .execute().data
        )
        payload = {
            "goal_id": goal_id, "student_name": student_name,
            "session_date": today, "session_time": session_time,
            "performance_level": performance_level,
        }
        if ex:
            sb.table("smartar_tracking").update(payload).eq("id", ex[0]["id"]).execute()
        else:
            sb.table("smartar_tracking").insert(payload).execute()
    except Exception as e:
        st.error(f"Save error: {e}")


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
    ["🏫 Class Dashboard", "📋 Goal Builder",
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

        # Pre-select from Team Meetings integration
        if integration["active"] and integration["student"]:
            default_idx = list(student_options.keys()).index(integration["student"]) \
                if integration["student"] in student_options else 0
        else:
            default_idx = 0

        selected_name  = st.selectbox("Select student", list(student_options.keys()),
                                      index=default_idx)
        student        = student_options[selected_name]
        existing_goals = get_goals(selected_name)

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
                period       = g.get("tracking_period", "All Day")

                with st.expander(
                    f"Goal {idx} — {_short(goal_text, 80)}"
                    + (" ⚠️ NEEDS REFINEMENT" if needs_ref else ""),
                ):
                    if needs_ref:
                        st.markdown(
                            f'<div class="alert-box">⚠️ <b>Action Required:</b> {low_c} recent '
                            f'sessions show NOT YET. Please refine this goal.</div>',
                            unsafe_allow_html=True,
                        )
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

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"🗑 Archive Goal {idx}", key=f"del_{g['id']}"):
                            st.session_state[f"arch_gb_{g['id']}"] = True
                    if st.session_state.get(f"arch_gb_{g['id']}"):
                        reason = st.text_input("Archive reason (optional):",
                                               key=f"arch_gb_r_{g['id']}")
                        ca, cb = st.columns(2)
                        with ca:
                            if st.button("Confirm Archive", key=f"arch_gb_d_{g['id']}", type="primary"):
                                if archive_goal(g["id"], reason):
                                    st.session_state.pop(f"arch_gb_{g['id']}", None)
                                    st.rerun()
                        with cb:
                            if st.button("Cancel", key=f"arch_gb_x_{g['id']}"):
                                st.session_state.pop(f"arch_gb_{g['id']}", None)
                                st.rerun()

        # ── NEW GOAL FORM ─────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Add New Goal")
        st.markdown(
            "**Step 1 — Exclusion Goal from Home School**"
        )
        excl_goal = st.text_area(
            "🏫 Exclusion Goal (from main school)",
            placeholder="Paste the exclusion goal as received from the main school…",
            height=80,
        )

        st.markdown("---")
        st.markdown(
            "**Step 2 — Build the SMARTAR Goal using the Hierarchy of Prompts**"
        )
        st.caption(
            "Complete each field. The goal statement will be assembled automatically "
            "from your selections, then refined by AI."
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
            st.markdown("**Assembled Goal Preview:**")
            st.info(assembled)
        else:
            assembled = ""

        st.markdown("---")
        st.markdown("**Step 3 — Refine and Finalise the SMARTAR Goal**")

        # AI refinement
        if groq_client and assembled:
            if st.button("✨ Refine Goal with AI", type="primary", key="refine_btn"):
                with st.spinner("Refining goal…"):
                    refined = groq_call(
                        f"""Refine this goal into clear, professional, student-centred language 
suitable for an IEP/support plan. Keep all specific details (grouping, task, setting, prompts, rate). 
Return ONLY the refined goal statement — no explanation, no preamble.

Goal to refine: {assembled}"""
                    )
                    st.session_state["refined_goal"] = refined
                    st.session_state.pop("gb_ai_period", None)
                    st.rerun()

        refined_goal = st.session_state.get("refined_goal", assembled)
        final_goal   = st.text_area(
            "Final SMARTAR Goal (edit if needed)",
            value=refined_goal, height=100, key="final_goal_text",
        )

        # ── Tracking Period ───────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Step 4 — Tracking Period**")
        st.caption(
            "Determines which sessions Quick Track shows for this goal. "
            "AI will check the goal text for time-specific language."
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

        # ── GAS Levels ────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Step 5 — Goal Attainment Scaling (GAS)**")

        if groq_client and final_goal:
            if st.button("🎚 Generate GAS Performance Levels with AI",
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
        if gas_levels:
            st.markdown("**Review GAS Performance Levels:**")
        for lvl in LEVEL_ORDER:
            key     = lvl if lvl in gas_levels else lvl.replace(" ", "_")
            default = gas_levels.get(lvl, gas_levels.get(key, ""))
            color   = LEVEL_COLOR[lvl]
            edited_gas[lvl] = st.text_area(
                f"{LEVEL_EMOJI[lvl]} {lvl}",
                value=default, height=70, key=f"gas_edit_{lvl}",
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

            for k in ["refined_goal", "gas_levels", "gb_ai_period"]:
                st.session_state.pop(k, None)

            st.success(f"✅ Goal saved for {selected_name}!")
            if integration["active"]:
                meeting_url = f"https://clc-lbu-portal.onrender.com/Team_Meetings?program={integration['program']}"
                st.markdown(f"[← Return to Team Meeting]({meeting_url})")
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
        today_rows     = (
            sb.table("smartar_tracking").select("*")
            .eq("goal_id", goal["id"])
            .eq("session_date", track_date.isoformat())
            .execute().data or []
        )
        today_sessions = {r["session_time"]: r["performance_level"] for r in today_rows}
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

        st.markdown("**Record session:**")
        sess_cols = st.columns(len(sessions))

        for i, session in enumerate(sessions):
            with sess_cols[i]:
                st.markdown(f"**{session}**")
                current = today_sessions.get(session)
                if current:
                    st.markdown(f"Currently: {LEVEL_EMOJI.get(current,'')} **{current}**")
                for lvl in TRACK_LEVELS:
                    is_sel  = current == lvl
                    label   = f"{LEVEL_EMOJI[lvl]} {lvl}" + (" ✓" if is_sel else "")
                    btn_key = f"track_{goal['id']}_{session}_{lvl}_{track_date}"
                    if st.button(label, key=btn_key, use_container_width=True,
                                 type="primary" if is_sel else "secondary"):
                        upsert_session(goal["id"], selected_name, session, lvl)
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

    # ── Manage Students ───────────────────────────────────────────────────────
    with tab_students:
        st.subheader("Add New Student")
        col1, col2, col3 = st.columns([3, 1, 1])
        new_sname = col1.text_input("Student name", key="admin_new_student")
        new_sprog = col2.selectbox("Program", PROGRAMS, key="admin_new_prog")
        if col3.button("Add Student", type="primary", key="admin_add_student"):
            if new_sname.strip():
                try:
                    sb.table("smartar_students").insert({
                        "student_name": new_sname.strip(),
                        "program":      new_sprog,
                        "active":       True,
                    }).execute()
                    st.success(f"✅ {new_sname.strip()} added to {new_sprog}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a student name.")

        st.markdown("---")
        show_archived = st.checkbox("Show archived students", value=False)
        students_all  = get_students(include_archived=show_archived)
        active_s      = [s for s in students_all if s.get("active", True)]
        archived_s    = [s for s in students_all if not s.get("active", True)]

        st.info(f"📊 {len(active_s)} active" +
                (f" | 📦 {len(archived_s)} archived" if show_archived and archived_s else ""))

        student_list = students_all if show_archived else active_s
        snames       = [s["student_name"] + (" [ARCHIVED]" if not s.get("active", True) else "")
                        for s in student_list]
        sel_s        = st.selectbox("Select student to manage", ["— Select —"] + snames,
                                    key="admin_edit_select")

        if sel_s != "— Select —":
            clean = sel_s.replace(" [ARCHIVED]", "")
            s     = next(x for x in student_list if x["student_name"] == clean)
            is_arch = not s.get("active", True)

            goals_s = get_goals(s["student_name"])
            st.markdown(f"### {s['student_name']}" + (" 📦 [ARCHIVED]" if is_arch else ""))
            st.caption(f"{len(goals_s)} active goals")

            c1, c2 = st.columns([2, 1])
            prog_idx = PROGRAMS.index(s.get("program","JP")) if s.get("program") in PROGRAMS else 0
            new_prog_s = c1.selectbox("Program", PROGRAMS, index=prog_idx,
                                      key=f"prog_{s['id']}", disabled=is_arch)
            if c2.button("Update", key=f"prog_upd_{s['id']}", disabled=is_arch):
                sb.table("smartar_students").update({"program": new_prog_s})\
                  .eq("id", s["id"]).execute()
                st.success("Updated.")
                st.rerun()

            st.markdown("---")
            if is_arch:
                if st.button(f"♻️ Restore {s['student_name']}", key=f"restore_s_{s['id']}", type="primary"):
                    sb.table("smartar_students").update({"active": True}).eq("id", s["id"]).execute()
                    st.success("Restored.")
                    st.rerun()
            else:
                if st.button(f"📦 Archive {s['student_name']}", key=f"archive_s_{s['id']}"):
                    sb.table("smartar_students").update({"active": False}).eq("id", s["id"]).execute()
                    st.success("Archived — data preserved.")
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
