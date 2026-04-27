import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime, date, timedelta
from io import BytesIO
import json
import requests

st.set_page_config(
    page_title="SMARTAR Goal Builder",
    page_icon="🎯",
    layout="wide",
)

# ─── Branding ────────────────────────────────────────────────────────────────
TEAL       = "#1A7A6E"
AMBER      = "#C8760A"
TEAL_LIGHT = "#E8F4F2"

# 4 performance levels for daily tracking (BELOW not tracked daily)
PERF_LEVELS = ["EXCEEDING", "ABOVE", "EXPECTED", "NOT YET"]
PERF_COLORS = {
    "EXCEEDING": "#27ae60",
    "ABOVE":     "#2ecc71",
    "EXPECTED":  "#2980b9",
    "NOT YET":   "#c0392b",
}
PERF_NUM = {"EXCEEDING": 4, "ABOVE": 3, "EXPECTED": 2, "NOT YET": 1}

# 5 GAS levels for goal setting
GAS_LABELS = {
    "gas_exceeding": ("EXCEEDING (+2)", "#27ae60"),
    "gas_above":     ("ABOVE (+1)",     "#2ecc71"),
    "gas_expected":  ("EXPECTED (0)",   "#2980b9"),
    "gas_below":     ("BELOW (-1)",     "#e67e22"),
    "gas_not_yet":   ("NOT YET (-2)",   "#c0392b"),
}

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

PROGRAMS = ["JP", "PY", "SY"]
DOMAINS  = ["Behaviour", "Academic", "Social Skills",
            "Self-Regulation", "Communication", "Independence", "Other"]

# ─── Supabase ─────────────────────────────────────────────────────────────────
from supabase import create_client

@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_sb()

# ─── Data helpers ─────────────────────────────────────────────────────────────

def get_students():
    try:
        return sb.table("smartar_students").select("*").order("student_name").execute().data
    except Exception:
        return []


def get_student_names():
    try:
        rows = sb.table("smartar_students").select("student_name").order("student_name").execute().data
        return [r["student_name"] for r in rows]
    except Exception:
        return []


def ensure_student(name: str):
    try:
        ex = sb.table("smartar_students").select("id").eq("student_name", name).execute().data
        if not ex:
            sb.table("smartar_students").insert({"student_name": name}).execute()
    except Exception:
        pass


def get_goals(student_name: str, status: str | None = None):
    try:
        q = sb.table("smartar_goals").select("*").eq("student_name", student_name)
        if status:
            q = q.eq("status", status)
        return q.order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error loading goals: {e}")
        return []


def save_goal(payload: dict) -> bool:
    try:
        payload["updated_at"] = datetime.utcnow().isoformat()
        if payload.get("id"):
            gid = payload.pop("id")
            sb.table("smartar_goals").update(payload).eq("id", gid).execute()
        else:
            sb.table("smartar_goals").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


def archive_goal(goal_id, reason: str = "") -> bool:
    try:
        sb.table("smartar_goals").update({
            "status":         "Archived",
            "active":         False,
            "archived_at":    datetime.utcnow().isoformat(),
            "archive_reason": reason,
            "updated_at":     datetime.utcnow().isoformat(),
        }).eq("id", goal_id).execute()
        return True
    except Exception as e:
        st.error(f"Archive error: {e}")
        return False


def restore_goal(goal_id) -> bool:
    try:
        sb.table("smartar_goals").update({
            "status":         "Active",
            "active":         True,
            "archived_at":    None,
            "archive_reason": None,
            "updated_at":     datetime.utcnow().isoformat(),
        }).eq("id", goal_id).execute()
        return True
    except Exception:
        return False


def _date_col(row: dict) -> str:
    """Return the date value from a tracking row regardless of column name."""
    return row.get("date") or row.get("tracking_date") or ""


def get_tracking(student_name: str, from_date: str, to_date: str, sessions=None):
    try:
        try:
            rows = (sb.table("smartar_tracking").select("*")
                    .eq("student_name", student_name)
                    .gte("date", from_date).lte("date", to_date)
                    .order("date").execute().data)
        except Exception:
            rows = (sb.table("smartar_tracking").select("*")
                    .eq("student_name", student_name)
                    .gte("tracking_date", from_date).lte("tracking_date", to_date)
                    .order("tracking_date").execute().data)
        if sessions:
            rows = [r for r in rows if r.get("session") in sessions]
        return rows
    except Exception:
        return []


def goal_date_range(goal: dict):
    start = goal.get("start_date") or (goal.get("created_at") or "")[:10] or date.today().isoformat()
    if goal.get("status") == "Archived" and goal.get("archived_at"):
        end = goal["archived_at"][:10]
    else:
        end = date.today().isoformat()
    return str(start)[:10], end


# ─── AI helpers ───────────────────────────────────────────────────────────────

def _groq(prompt: str, json_mode: bool = False, max_tokens: int = 400) -> str:
    key = st.secrets.get("GROQ_API_KEY", "")
    if not key:
        return ""
    body: dict = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens":  max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body, timeout=15,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""


def ai_refine_goal(exclusion_goal: str, components: dict) -> str:
    prompt = f"""You are an expert at writing SMARTAR goals for students in alternative education settings (trauma-informed, PBS framework).

Exclusion goal from home school: {exclusion_goal}

Goal components provided by teacher:
- Target skill/behaviour: {components.get('skill', '')}
- Grouping/social context: {components.get('grouping', '')}
- Task type: {components.get('task_type', '')}
- Setting: {components.get('setting', '')}
- Prompt level: {components.get('prompts', '')}
- Success rate: {components.get('rate', '')}

Write ONE complete SMARTAR goal statement. It must be Specific, Measurable, Achievable, Relevant, Time-bound, Attainable, Recorded.
Use professional trauma-informed language. Start with "[Student] will…"
Return only the goal text, nothing else."""
    return _groq(prompt, max_tokens=300)


def ai_generate_gas(smartar_goal: str) -> dict:
    prompt = f"""You are an expert at Goal Attainment Scaling (GAS) in alternative education (CLC LBU context).

SMARTAR Goal: {smartar_goal}

Write 5 observable, measurable GAS level descriptors.

Return ONLY valid JSON:
{{
  "gas_exceeding": "What does much better than expected look like? (+2)",
  "gas_above": "What does better than expected look like? (+1)",
  "gas_expected": "What does meeting the goal look like? (0)",
  "gas_below": "What does somewhat less than expected look like? (-1)",
  "gas_not_yet": "What does much less than expected look like? (-2)"
}}"""
    raw = _groq(prompt, json_mode=True, max_tokens=600)
    try:
        return json.loads(raw)
    except Exception:
        return {}


def ai_period_check(smartar_goal: str) -> dict:
    prompt = f"""You are an educational support specialist. Determine the best daily tracking period for this SMARTAR goal.

Goal: {smartar_goal}

School sessions:
- Morning (~9am–11am): literacy, numeracy, structured academic learning
- Middle (~11am–1pm): recess, lunch, social time, transitions
- Afternoon (~1pm–3pm): specialist subjects, projects, outdoor education

Return ONLY valid JSON:
{{
  "period": "All Day" | "Morning Only" | "Middle Only" | "Afternoon Only" | "Morning & Middle" | "Middle & Afternoon",
  "reasoning": "One concise sentence",
  "confidence": "High" | "Medium" | "Low"
}}

Use "All Day" unless the goal CLEARLY references a specific time context."""
    raw = _groq(prompt, json_mode=True, max_tokens=200)
    try:
        result = json.loads(raw)
        if result.get("period") not in TRACKING_PERIODS:
            result["period"] = "All Day"
        return result
    except Exception:
        return {"period": "All Day", "reasoning": "AI check unavailable.", "confidence": "Low"}


# ─── Chart helpers ────────────────────────────────────────────────────────────

def _short(text: str, n: int = 65) -> str:
    return text[:n] + "…" if len(text) > n else text


def _df(rows):
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    date_col = "date" if "date" in df.columns else "tracking_date" if "tracking_date" in df.columns else None
    if date_col:
        df["_date"] = pd.to_datetime(df[date_col])
    df["perf_num"] = df["performance"].map(PERF_NUM).fillna(0)
    return df


def make_goal_chart(rows, smartar_goal: str, from_date: str, to_date: str,
                    student_name: str = "") -> bytes | None:
    df = _df(rows)
    if df.empty:
        return None

    fig = plt.figure(figsize=(15, 9), facecolor="white")
    fig.suptitle(_short(smartar_goal, 100), fontsize=10, fontweight="bold",
                 color=TEAL, y=0.98, wrap=True)
    if student_name:
        fig.text(0.5, 0.955, student_name, ha="center", fontsize=9,
                 color=AMBER, fontweight="bold")

    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.32,
                           top=0.92, bottom=0.08, left=0.07, right=0.97)

    # Performance over time
    ax1 = fig.add_subplot(gs[0, :])
    if "_date" in df.columns:
        daily = df.groupby("_date")["perf_num"].mean().reset_index()
        ax1.plot(daily["_date"], daily["perf_num"], color=TEAL, lw=1.5, alpha=0.45, zorder=1)
        sc_colors = [PERF_COLORS.get(p, "#888") for p in df["performance"]]
        ax1.scatter(df["_date"], df["perf_num"], c=sc_colors, s=100, zorder=2,
                    edgecolors="white", linewidth=0.9)
        ax1.tick_params(axis="x", rotation=35, labelsize=8)
    ax1.set_yticks([1, 2, 3, 4])
    ax1.set_yticklabels(["NOT YET", "EXPECTED", "ABOVE", "EXCEEDING"], fontsize=9)
    ax1.set_ylim(0.3, 4.7)
    ax1.set_title("Performance Over Time", fontsize=10, color=TEAL, fontweight="bold",
                  loc="left", pad=6)
    ax1.annotate(f"Tracked: {from_date}  →  {to_date}", xy=(0.01, 0.05),
                 xycoords="axes fraction", fontsize=8, color="gray")
    patches = [mpatches.Patch(color=PERF_COLORS[p], label=p)
               for p in PERF_LEVELS if p in df["performance"].values]
    ax1.legend(handles=patches, fontsize=8, loc="upper right", framealpha=0.7, ncol=4)
    ax1.grid(axis="y", alpha=0.22)
    ax1.spines[["top", "right"]].set_visible(False)

    # Distribution pie
    ax2 = fig.add_subplot(gs[1, 0])
    counts = df["performance"].value_counts().reindex(PERF_LEVELS).dropna()
    if not counts.empty:
        pie_c = [PERF_COLORS[l] for l in counts.index]
        _, _, autotexts = ax2.pie(counts.values, labels=counts.index, colors=pie_c,
                                   autopct="%1.0f%%", startangle=90,
                                   textprops={"fontsize": 9},
                                   wedgeprops={"edgecolor": "white", "linewidth": 1.5})
        for at in autotexts:
            at.set_fontsize(9)
            at.set_fontweight("bold")
    ax2.set_title("Distribution", fontsize=10, color=TEAL, fontweight="bold", loc="left", pad=6)

    # By session
    ax3 = fig.add_subplot(gs[1, 1])
    if "session" in df.columns:
        sesses = [s for s in ["Morning", "Middle", "Afternoon"] if s in df["session"].values]
        if sesses:
            x = np.arange(len(sesses))
            w = 0.2
            for i, perf in enumerate(PERF_LEVELS):
                vals = [df[(df["session"] == s) & (df["performance"] == perf)].shape[0]
                        for s in sesses]
                ax3.bar(x + i * w, vals, w, label=perf, color=PERF_COLORS[perf],
                        alpha=0.85, edgecolor="white")
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
    ax3.set_title("By Session", fontsize=10, color=TEAL, fontweight="bold", loc="left", pad=6)

    fig.text(0.5, 0.01,
             f"CLC Learning and Behaviour Unit  |  Generated {datetime.now().strftime('%d %b %Y')}",
             ha="center", fontsize=7.5, color="#888", style="italic")

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def make_student_pdf(student_name: str, goal_rows_list: list) -> bytes:
    from PIL import Image as PILImage
    buf = BytesIO()
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(11.69, 8.27), facecolor="white")
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0.78), 1, 0.22, transform=ax.transAxes, facecolor=TEAL))
        ax.text(0.5, 0.895, "SMARTAR Goal Progress Report", ha="center", va="center",
                fontsize=22, fontweight="bold", color="white", transform=ax.transAxes)
        ax.text(0.5, 0.635, student_name, ha="center", va="center",
                fontsize=20, fontweight="bold", color=AMBER, transform=ax.transAxes)
        ax.text(0.5, 0.545, f"Generated: {datetime.now().strftime('%d %B %Y')}",
                ha="center", fontsize=12, color="gray", transform=ax.transAxes)
        ax.text(0.5, 0.47, "CLC Learning and Behaviour Unit",
                ha="center", fontsize=11, color="gray", transform=ax.transAxes)
        ax.text(0.5, 0.39, f"Goals with tracking data: {len(goal_rows_list)}",
                ha="center", fontsize=11, color="#555", transform=ax.transAxes)
        pdf.savefig(fig, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        for idx, (goal, rows, from_d, to_d) in enumerate(goal_rows_list, 1):
            goal_text = goal.get("smartar_goal") or goal.get("goal_text") or ""
            png_bytes = make_goal_chart(rows, goal_text, from_d, to_d, student_name)
            if not png_bytes:
                continue
            img = PILImage.open(BytesIO(png_bytes))
            pg_fig, pg_ax = plt.subplots(figsize=(11.69, 8.27), facecolor="white")
            pg_ax.imshow(np.array(img))
            pg_ax.axis("off")
            pg_fig.text(0.5, 0.005,
                        f"Goal {idx}  ·  [{goal.get('status','Active')}]  ·  "
                        f"{goal.get('domain','')}  ·  Period: {goal.get('tracking_period','All Day')}",
                        ha="center", fontsize=8, color="gray")
            pdf.savefig(pg_fig, bbox_inches="tight", facecolor="white")
            plt.close(pg_fig)

    buf.seek(0)
    return buf.getvalue()


# ─── Styles ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  [data-testid="stSidebar"] {{ display: none !important; }}
  .goal-card {{
      border: 1px solid #ccc;
      border-left: 5px solid {TEAL};
      border-radius: 6px;
      padding: 12px 16px;
      margin-bottom: 10px;
      background: {TEAL_LIGHT};
  }}
  .archived-card {{ border-left-color: {AMBER} !important; background: #fffbf4 !important; }}
  .step-header {{
      background: {TEAL};
      color: white;
      padding: 6px 14px;
      border-radius: 5px;
      margin: 10px 0 6px 0;
      font-weight: 600;
      font-size: 14px;
  }}
  h1 {{ color: {TEAL}; }}
  .stTabs [role="tablist"] button {{ font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🎯 SMARTAR Goal Builder")
st.caption("**S**pecific · **M**easurable · **A**chievable · **R**elevant · "
           "**T**ime-bound · **A**ttainable · **R**ecorded")

params          = st.query_params
preload_student = params.get("student", "")
preload_goal    = params.get("goal", "")
from_team       = params.get("from_team_meetings", "false").lower() == "true"

if from_team:
    st.info("📋 Opened from Team Meeting — goal will sync back automatically after saving.")
    if st.button("← Return to Team Meeting"):
        st.switch_page("pages/11_Team_Meetings.py")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Goal Builder",
    "📊 Student Goals",
    "📈 Progress Reports",
    "📚 Goal Bank",
    "⚙️ Admin Panel",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – GOAL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 🎯 Build a SMARTAR Goal")

    edit_data = st.session_state.get("gb_edit_data", {})
    edit_id   = st.session_state.get("gb_edit_id")

    c1, c2 = st.columns([2, 1])
    with c1:
        student_name = st.text_input(
            "Student Name",
            value=edit_data.get("student_name", preload_student),
            placeholder="Enter student name", key="gb_student",
        )
    with c2:
        d_idx = DOMAINS.index(edit_data.get("domain", "Behaviour")) \
            if edit_data.get("domain") in DOMAINS else 0
        domain = st.selectbox("Goal Domain", DOMAINS, index=d_idx, key="gb_domain")

    # Step 1 — Exclusion Goal
    st.markdown('<div class="step-header">Step 1 — Exclusion Goal from Home School</div>',
                unsafe_allow_html=True)
    exclusion_goal = st.text_area(
        "What is the exclusion goal or concern from the student's home school?",
        value=edit_data.get("exclusion_goal", preload_goal), height=80,
        placeholder="E.g., 'Student is excluded for persistent aggression toward peers and staff'",
        key="gb_exclusion_goal",
    )

    # Step 2 — Components
    st.markdown('<div class="step-header">Step 2 — SMARTAR Goal Components</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        skill     = st.text_input("🎯 Skill / Target Behaviour",
                                  value=edit_data.get("skill", ""),
                                  placeholder="E.g., 'use a break card to request a break'",
                                  key="gb_skill")
        grouping  = st.text_input("👥 Grouping / Social Context",
                                  value=edit_data.get("grouping", ""),
                                  placeholder="E.g., 'in a small group of 3 peers'",
                                  key="gb_grouping")
        task_type = st.text_input("📋 Task Type",
                                  value=edit_data.get("task_type", ""),
                                  placeholder="E.g., 'during structured literacy activities'",
                                  key="gb_task_type")
    with c2:
        setting = st.text_input("📍 Setting",
                                value=edit_data.get("setting", ""),
                                placeholder="E.g., 'in the classroom'",
                                key="gb_setting")
        prompts = st.text_input("💬 Prompt Level",
                                value=edit_data.get("prompts", ""),
                                placeholder="E.g., 'with 1 verbal prompt'",
                                key="gb_prompts")
        rate    = st.text_input("📊 Success Rate / Criteria",
                                value=edit_data.get("rate", ""),
                                placeholder="E.g., '4 out of 5 opportunities'",
                                key="gb_rate")

    if st.button("🤖 Generate SMARTAR Goal from Components (AI)", key="gb_gen_btn"):
        if exclusion_goal.strip() or skill.strip():
            with st.spinner("Generating goal…"):
                refined = ai_refine_goal(exclusion_goal, {
                    "skill": skill, "grouping": grouping, "task_type": task_type,
                    "setting": setting, "prompts": prompts, "rate": rate,
                })
                if refined:
                    st.session_state["gb_smartar_val"] = refined
                    st.success("Goal generated — review and edit below.")
                else:
                    st.warning("AI unavailable. Write the goal manually below.")
        else:
            st.warning("Enter the exclusion goal or skill first.")

    # Step 3 — SMARTAR Goal Statement
    st.markdown('<div class="step-header">Step 3 — SMARTAR Goal Statement</div>',
                unsafe_allow_html=True)
    smartar_goal = st.text_area(
        "Full SMARTAR Goal",
        value=st.session_state.get("gb_smartar_val", edit_data.get("smartar_goal", "")),
        height=100,
        placeholder="[Student] will… measured by… in X out of Y opportunities…",
        key="gb_smartar_goal",
    )

    # AI Tracking Period Check
    ai_result = st.session_state.get("gb_ai_result")
    if smartar_goal.strip():
        if st.button("🤖 Check Tracking Period with AI", key="gb_period_btn"):
            with st.spinner("Analysing…"):
                ai_result = ai_period_check(smartar_goal)
                st.session_state["gb_ai_result"] = ai_result

    suggested_period = "All Day"
    if ai_result:
        conf = ai_result.get("confidence", "Low")
        st.info(f"**AI Recommendation:** {ai_result['period']}\n\n"
                f"*{ai_result.get('reasoning', '')}*  \nConfidence: {conf}")
        suggested_period = ai_result.get("period", "All Day")

    p_idx = TRACKING_PERIODS.index(
        edit_data.get("tracking_period", suggested_period)
        if edit_data.get("tracking_period") in TRACKING_PERIODS else suggested_period
    )
    tracking_period = st.selectbox(
        "Tracking Period", TRACKING_PERIODS, index=p_idx, key="gb_period",
        help="AI analyses goal text for time-specific language. Override if needed.",
    )
    st.caption(f"📅 Sessions: **{', '.join(SESSIONS_FOR_PERIOD[tracking_period])}**")

    # Step 4 — GAS Levels
    st.markdown('<div class="step-header">Step 4 — Goal Attainment Scaling (GAS)</div>',
                unsafe_allow_html=True)

    if smartar_goal.strip():
        if st.button("🤖 Generate GAS Levels with AI", key="gb_gas_btn"):
            with st.spinner("Generating GAS levels…"):
                gas_ai = ai_generate_gas(smartar_goal)
                if gas_ai:
                    st.session_state["gb_gas_ai"] = gas_ai
                    st.success("GAS levels generated — review and edit below.")
                else:
                    st.warning("AI unavailable. Enter GAS levels manually.")

    gas_ai_vals = st.session_state.get("gb_gas_ai", {})
    gas_vals = {}
    for gas_key, (gas_label, gas_color) in GAS_LABELS.items():
        default_val = gas_ai_vals.get(gas_key) or edit_data.get(gas_key) or ""
        gas_vals[gas_key] = st.text_area(
            f"**{gas_label}**",
            value=default_val, height=70, key=f"gb_{gas_key}",
        )

    # Step 5 — Settings
    st.markdown('<div class="step-header">Step 5 — Goal Settings & Timeline</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        sv = date.today()
        if edit_data.get("start_date"):
            try: sv = date.fromisoformat(str(edit_data["start_date"])[:10])
            except Exception: pass
        start_date = st.date_input("Goal Start Date", value=sv, key="gb_start")
    with c2:
        tv = date.today() + timedelta(weeks=8)
        if edit_data.get("target_date"):
            try: tv = date.fromisoformat(str(edit_data["target_date"])[:10])
            except Exception: pass
        target_date = st.date_input("Target Review Date", value=tv, key="gb_target")
    with c3:
        success_pct = st.slider("Success Threshold (%)", 50, 100,
                                value=int(edit_data.get("success_percentage", 80)),
                                key="gb_pct")

    notes = st.text_area("Additional Notes", value=edit_data.get("notes", ""),
                         height=65, key="gb_notes")

    st.divider()
    save_label = "💾 Update Goal" if edit_id else "💾 Save New Goal"
    if st.button(save_label, type="primary", key="gb_save"):
        if student_name.strip() and smartar_goal.strip():
            ensure_student(student_name.strip())
            payload = {
                "student_name":       student_name.strip(),
                "exclusion_goal":     exclusion_goal.strip(),
                "smartar_goal":       smartar_goal.strip(),
                "domain":             domain,
                "skill":              skill,
                "grouping":           grouping,
                "task_type":          task_type,
                "setting":            setting,
                "prompts":            prompts,
                "rate":               rate,
                "gas_exceeding":      gas_vals.get("gas_exceeding", ""),
                "gas_above":          gas_vals.get("gas_above", ""),
                "gas_expected":       gas_vals.get("gas_expected", ""),
                "gas_below":          gas_vals.get("gas_below", ""),
                "gas_not_yet":        gas_vals.get("gas_not_yet", ""),
                "status":             "Active",
                "active":             True,
                "start_date":         str(start_date),
                "target_date":        str(target_date),
                "tracking_period":    tracking_period,
                "success_percentage": success_pct,
                "notes":              notes,
            }
            if edit_id:
                payload["id"] = edit_id
            if save_goal(payload):
                st.success("✅ Goal saved successfully!")
                for k in ["gb_edit_id", "gb_edit_data", "gb_ai_result",
                          "gb_smartar_val", "gb_gas_ai"]:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            st.warning("Please enter student name and SMARTAR goal.")

    if edit_id:
        if st.button("✖ Cancel Edit", key="gb_cancel"):
            for k in ["gb_edit_id", "gb_edit_data"]:
                st.session_state.pop(k, None)
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – STUDENT GOALS OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📊 Student Goals Overview")

    try:
        all_active = sb.table("smartar_goals").select("*").eq("status", "Active")\
                       .order("updated_at", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Error: {e}")
        all_active = []

    if not all_active:
        st.info("No active goals. Create goals in the Goal Builder tab.")
    else:
        students_dict: dict[str, list] = {}
        for g in all_active:
            students_dict.setdefault(g.get("student_name", "Unknown"), []).append(g)

        for student, goals in sorted(students_dict.items()):
            with st.expander(
                f"**{student}** — {len(goals)} active goal{'s' if len(goals) > 1 else ''}",
                expanded=False,
            ):
                for goal in goals:
                    period = goal.get("tracking_period", "All Day")
                    from_d, to_d = goal_date_range(goal)
                    st.markdown(f"""<div class="goal-card">
                        <strong>{goal.get('domain','—')}</strong> ·
                        <em style="color:{TEAL}">{period}</em><br>
                        <span style="font-size:13px">
                          <strong>SMARTAR:</strong> {goal.get('smartar_goal','—')}
                        </span><br>
                        {f'<span style="font-size:12px;color:#555"><strong>Excl. goal:</strong> {goal.get("exclusion_goal","")}</span><br>' if goal.get("exclusion_goal") else ""}
                        <small style="color:#888">Started: {from_d} · Target: {goal.get('target_date','—')} · 
                        Days tracked: {(date.today() - date.fromisoformat(str(from_d)[:10])).days if from_d else '—'}</small>
                    </div>""", unsafe_allow_html=True)

                    with st.expander("📊 GAS Levels", expanded=False):
                        for gas_key, (gas_label, gas_color) in GAS_LABELS.items():
                            val = goal.get(gas_key, "")
                            if val:
                                st.markdown(
                                    f'<div style="border-left:4px solid {gas_color};'
                                    f'padding:4px 10px;margin:2px 0;font-size:12px">'
                                    f'<strong>{gas_label}:</strong> {val}</div>',
                                    unsafe_allow_html=True,
                                )

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("📝 Edit", key=f"edit2_{goal['id']}"):
                            st.session_state["gb_edit_id"]    = goal["id"]
                            st.session_state["gb_edit_data"]  = goal
                            st.session_state["gb_smartar_val"] = goal.get("smartar_goal", "")
                            st.session_state["gb_ai_result"]  = None
                            st.info("Switch to **Goal Builder** tab to edit.")
                    with c2:
                        if st.button("✅ Mark Complete", key=f"comp2_{goal['id']}"):
                            sb.table("smartar_goals").update({"status": "Completed", "active": False})\
                              .eq("id", goal["id"]).execute()
                            st.rerun()
                    with c3:
                        if st.button("🗃️ Archive", key=f"arch2_{goal['id']}"):
                            st.session_state[f"arch_c_{goal['id']}"] = True

                    if st.session_state.get(f"arch_c_{goal['id']}"):
                        reason = st.text_input("Archive reason (optional):",
                                               key=f"arch_r_{goal['id']}")
                        ca, cb = st.columns(2)
                        with ca:
                            if st.button("✓ Confirm Archive", key=f"arch_d_{goal['id']}", type="primary"):
                                if archive_goal(goal["id"], reason):
                                    st.success("Goal archived. All tracking data preserved.")
                                    st.session_state.pop(f"arch_c_{goal['id']}", None)
                                    st.rerun()
                        with cb:
                            if st.button("✖ Cancel", key=f"arch_x_{goal['id']}"):
                                st.session_state.pop(f"arch_c_{goal['id']}", None)
                                st.rerun()
                    st.markdown("---")

    # Archived section
    st.markdown("---")
    st.markdown("#### 🗃️ Archived & Completed Goals")
    try:
        arch = (sb.table("smartar_goals").select("*").eq("status", "Archived")
                .order("archived_at", desc=True).execute().data or [])
        comp = (sb.table("smartar_goals").select("*").eq("status", "Completed")
                .order("updated_at", desc=True).execute().data or [])
        archived_all = arch + comp
    except Exception:
        archived_all = []

    if not archived_all:
        st.caption("No archived or completed goals.")
    else:
        arch_by_student: dict[str, list] = {}
        for g in archived_all:
            arch_by_student.setdefault(g.get("student_name", "Unknown"), []).append(g)
        for student, goals in sorted(arch_by_student.items()):
            with st.expander(f"**{student}** — {len(goals)} archived/completed"):
                for goal in goals:
                    from_d, to_d = goal_date_range(goal)
                    archived_at  = (goal.get("archived_at") or "")[:10]
                    icon = "🟠" if goal.get("status") == "Archived" else "🔵"
                    st.markdown(
                        f'{icon} **[{goal.get("status")}]** {goal.get("domain","—")} — '
                        f'{_short(goal.get("smartar_goal",""), 60)}'
                    )
                    st.caption(
                        f'Active: {from_d} → {archived_at or to_d}'
                        + (f' · {goal.get("archive_reason","")}' if goal.get("archive_reason") else "")
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("♻️ Restore", key=f"restore_{goal['id']}"):
                            restore_goal(goal["id"])
                            st.rerun()
                    with c2:
                        if st.button("➕ New Goal (same student)", key=f"new_{goal['id']}"):
                            st.session_state["gb_edit_id"]   = None
                            st.session_state["gb_edit_data"] = {"student_name": goal["student_name"]}
                            st.info("Switch to **Goal Builder** tab.")
                    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – PROGRESS REPORTS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📈 Progress Reports")
    st.caption("Charts title = actual SMARTAR goal text. PNG downloads are full-size with no clipping.")

    student_names = get_student_names()
    if student_names:
        rpt_student = st.selectbox("Select Student", student_names, key="rpt_sel")
    else:
        rpt_student = st.text_input("Student Name", key="rpt_txt")

    if rpt_student:
        all_goals = (
            get_goals(rpt_student, "Active") +
            get_goals(rpt_student, "Archived") +
            get_goals(rpt_student, "Completed")
        )
        all_goals.sort(
            key=lambda g: g.get("start_date") or (g.get("created_at") or "")[:10],
            reverse=True,
        )

        if not all_goals:
            st.info("No goals found for this student.")
        else:
            goal_rows_list = []

            for idx, goal in enumerate(all_goals, 1):
                from_d, to_d = goal_date_range(goal)
                period       = goal.get("tracking_period", "All Day")
                sessions     = SESSIONS_FOR_PERIOD.get(period, ["Morning", "Middle", "Afternoon"])
                tracking     = get_tracking(rpt_student, from_d, to_d, sessions=sessions)
                smartar_text = goal.get("smartar_goal") or goal.get("goal_text") or "—"

                if tracking:
                    actual_from = min(_date_col(r) for r in tracking)[:10]
                    actual_to   = max(_date_col(r) for r in tracking)[:10]
                    track_str   = f"{actual_from} → {actual_to}"
                    n_entries   = len(tracking)
                else:
                    actual_from = from_d
                    actual_to   = to_d
                    track_str   = "No entries yet"
                    n_entries   = 0

                status = goal.get("status", "Active")
                s_icon = {"Active": "🟢", "Archived": "🟠", "Completed": "🔵"}.get(status, "⚪")

                with st.expander(
                    f"{s_icon} Goal {idx} ({status}): {goal.get('domain','—')} — "
                    f"{_short(smartar_text, 55)}",
                    expanded=(idx == 1),
                ):
                    col_info, col_dl = st.columns([3, 1])
                    with col_info:
                        st.markdown(
                            f"**Domain:** {goal.get('domain','—')} · **Period:** {period} · "
                            f"**Sessions:** {', '.join(sessions)}"
                        )
                        st.markdown(f"**SMARTAR Goal:** {smartar_text}")
                        if goal.get("exclusion_goal"):
                            st.caption(f"Exclusion goal: {goal['exclusion_goal']}")
                        st.markdown(
                            f"**Goal active:** {from_d} → {to_d} · **Entries:** {n_entries}"
                        )
                        st.markdown(f"**Tracking date range:** {track_str}")
                        if goal.get("archive_reason"):
                            st.caption(f"Archive reason: {goal['archive_reason']}")

                    if tracking:
                        goal_rows_list.append((goal, tracking, actual_from, actual_to))
                        png_bytes = make_goal_chart(
                            tracking, smartar_text, actual_from, actual_to,
                            student_name=rpt_student,
                        )
                        if png_bytes:
                            st.image(png_bytes, use_container_width=True)
                            with col_dl:
                                safe = smartar_text[:25].replace(" ", "_").replace("/", "-")
                                st.download_button(
                                    "📥 PNG",
                                    data=png_bytes,
                                    file_name=f"{rpt_student}_{goal.get('domain','')}_{safe}.png",
                                    mime="image/png",
                                    key=f"dl_png_{goal['id']}",
                                )
                    else:
                        st.info("No tracking data in this goal's session/period yet.")

            if goal_rows_list:
                st.divider()
                st.markdown("#### 📄 Download All Goals as PDF")
                if st.button("Generate PDF Report", type="primary", key="gen_pdf"):
                    with st.spinner("Building PDF…"):
                        pdf_bytes = make_student_pdf(rpt_student, goal_rows_list)
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"{rpt_student}_SMARTAR_Progress_Report.pdf",
                        mime="application/pdf",
                        key="dl_pdf_final",
                    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – GOAL BANK
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 📚 Goal Bank & Templates")
    st.info("Select a template to pre-load into the Goal Builder.")

    templates = {
        "Self-Regulation": [
            "When feeling frustrated, [Student] will use a break card to request a 5-minute sensory break before escalating, measured by frequency count, 4 out of 5 opportunities daily.",
            "[Student] will identify their emotion using the Zones of Regulation before transitioning between activities, in 3 out of 5 transitions per day.",
            "[Student] will use a self-regulation strategy (e.g. deep breathing, fidget, movement break) when prompted, 3 out of 5 opportunities.",
        ],
        "Behaviour": [
            "[Student] will remain in the classroom for a full structured session (45 min) without needing a break, on 3 out of 5 days per week.",
            "[Student] will transition between activities within 3 minutes of the change signal, in 4 out of 5 transitions daily.",
            "[Student] will use a safe touch or verbal request rather than physical aggression, in 4 out of 5 observed interactions.",
        ],
        "Communication": [
            "[Student] will use a verbal or AAC-supported request to ask for help during structured tasks, in 4 out of 5 opportunities.",
            "[Student] will initiate a social greeting with a peer or staff member during morning arrival, on 3 out of 5 school days.",
        ],
        "Academic": [
            "[Student] will independently complete a 10-minute reading task with fewer than 2 prompts, in 3 out of 5 sessions.",
            "[Student] will attempt all items on a 10-question maths worksheet before requesting support, in 4 out of 5 sessions.",
        ],
        "Social Skills": [
            "[Student] will participate in a structured peer activity for a minimum of 10 minutes without leaving or becoming dysregulated, 3 out of 5 sessions.",
        ],
        "Independence": [
            "[Student] will independently unpack their bag and begin morning routine within 5 minutes of arriving, on 4 out of 5 days.",
            "[Student] will pack away materials at the end of a task without a verbal prompt, in 3 out of 5 opportunities.",
        ],
    }

    for category, goal_list in templates.items():
        with st.expander(f"**{category}** ({len(goal_list)} templates)"):
            for g in goal_list:
                cols = st.columns([6, 1])
                cols[0].markdown(f"_{g}_")
                if cols[1].button("Use", key=f"tpl_{abs(hash(g))}"):
                    st.session_state["gb_smartar_val"] = g
                    st.session_state.pop("gb_ai_result", None)
                    st.success("Template loaded — switch to Goal Builder tab.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### ⚙️ Admin Panel")
    adm1, adm2, adm3 = st.tabs([
        "👥 Manage Students",
        "📝 Edit Goals",
        "➕ Pre-populate Goals",
    ])

    # ── Manage Students ───────────────────────────────────────────────────────
    with adm1:
        st.markdown("#### Add New Student")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            new_sname = st.text_input("Student Name", key="adm_new_name")
        with c2:
            new_prog = st.selectbox("Program", PROGRAMS, key="adm_new_prog")
        with c3:
            st.write("")
            if st.button("➕ Add", key="adm_add_btn"):
                if new_sname.strip():
                    try:
                        ex = sb.table("smartar_students").select("id")\
                               .eq("student_name", new_sname.strip()).execute().data
                        if ex:
                            st.warning(f"{new_sname} already exists.")
                        else:
                            sb.table("smartar_students").insert({
                                "student_name": new_sname.strip(),
                                "program":      new_prog,
                            }).execute()
                            st.success(f"✅ Added {new_sname}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Enter a name.")

        st.divider()
        st.markdown("#### All Students")
        students = get_students()
        if not students:
            st.info("No students yet.")
        else:
            for s in students:
                goals = get_goals(s["student_name"])
                with st.expander(
                    f"**{s['student_name']}** — {s.get('program','—')} — {len(goals)} goal(s)"
                ):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        new_prog_val = st.selectbox(
                            "Program", PROGRAMS,
                            index=PROGRAMS.index(s.get("program","JP"))
                              if s.get("program") in PROGRAMS else 0,
                            key=f"adm_prog_{s['id']}",
                        )
                    with c2:
                        if st.button("Update", key=f"adm_upd_{s['id']}"):
                            sb.table("smartar_students").update({"program": new_prog_val})\
                              .eq("id", s["id"]).execute()
                            st.success("Updated.")
                            st.rerun()
                    with c3:
                        if st.button("🗑️ Remove", key=f"adm_del_{s['id']}"):
                            sb.table("smartar_students").update({"active": False})\
                              .eq("id", s["id"]).execute()
                            st.success("Removed.")
                            st.rerun()

    # ── Edit Goals ────────────────────────────────────────────────────────────
    with adm2:
        st.markdown("#### Edit Existing Goals")
        student_names = get_student_names()
        if not student_names:
            st.info("No students in the system.")
        else:
            sel_student = st.selectbox("Select Student", student_names, key="adm_edit_student")
            goals = get_goals(sel_student)
            if not goals:
                st.info(f"No goals for {sel_student}.")
            else:
                goal_options = {
                    f"[{g.get('status','Active')}] {g.get('domain','—')}: "
                    f"{_short(g.get('smartar_goal',''), 50)}": g
                    for g in goals
                }
                sel_label = st.selectbox("Select Goal", list(goal_options.keys()),
                                         key="adm_edit_goal")
                goal = goal_options[sel_label]

                with st.expander("✏️ Edit Fields", expanded=True):
                    adm_excl = st.text_area("Exclusion Goal",
                                            value=goal.get("exclusion_goal", ""),
                                            height=70, key="adm_excl")
                    adm_smartar = st.text_area("SMARTAR Goal",
                                               value=goal.get("smartar_goal", ""),
                                               height=90, key="adm_smartar")
                    adm_domain = st.selectbox(
                        "Domain", DOMAINS,
                        index=DOMAINS.index(goal.get("domain","Behaviour"))
                          if goal.get("domain") in DOMAINS else 0,
                        key="adm_domain",
                    )
                    adm_period = st.selectbox(
                        "Tracking Period", TRACKING_PERIODS,
                        index=TRACKING_PERIODS.index(goal.get("tracking_period","All Day"))
                          if goal.get("tracking_period") in TRACKING_PERIODS else 0,
                        key="adm_period",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        adm_start = st.date_input(
                            "Goal Start Date",
                            value=date.fromisoformat(str(goal.get("start_date", date.today()))[:10]),
                            key="adm_start",
                        )
                    with c2:
                        adm_target = st.date_input(
                            "Target Date",
                            value=date.fromisoformat(
                                str(goal.get("target_date", date.today() + timedelta(weeks=8)))[:10]
                            ),
                            key="adm_target",
                        )

                    st.markdown("**GAS Levels**")
                    adm_gas = {}
                    for gas_key, (gas_label, gas_color) in GAS_LABELS.items():
                        adm_gas[gas_key] = st.text_area(
                            gas_label, value=goal.get(gas_key, ""),
                            height=65, key=f"adm_{gas_key}",
                        )

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("💾 Save Changes", type="primary", key="adm_save"):
                            payload = {
                                "id":              goal["id"],
                                "exclusion_goal":  adm_excl.strip(),
                                "smartar_goal":    adm_smartar.strip(),
                                "domain":          adm_domain,
                                "tracking_period": adm_period,
                                "start_date":      str(adm_start),
                                "target_date":     str(adm_target),
                            }
                            payload.update(adm_gas)
                            if save_goal(payload):
                                st.success("✅ Goal updated.")
                                st.rerun()
                    with c2:
                        if st.button("🗃️ Archive Goal", key="adm_arch"):
                            if archive_goal(goal["id"]):
                                st.success("Goal archived.")
                                st.rerun()

    # ── Pre-populate Goals ────────────────────────────────────────────────────
    with adm3:
        st.markdown("#### Pre-populate Goals from Entry Meeting")
        st.caption(
            "Set up a student's initial goals after an entry meeting "
            "so teachers can begin tracking straight away. "
            "Goals can be refined later as teachers observe the student."
        )

        student_names = get_student_names()
        if not student_names:
            st.info("Add students in the Manage Students tab first.")
        else:
            pp_student = st.selectbox("Select Student", student_names, key="adm_pp_student")
            existing   = get_goals(pp_student, "Active")
            if existing:
                st.info(f"{pp_student} already has {len(existing)} active goal(s).")

            pp_excl   = st.text_area(
                "Exclusion Goal from Home School", height=80,
                placeholder="What did the home school identify as the main concern?",
                key="adm_pp_excl",
            )
            pp_domain = st.selectbox("Domain", DOMAINS, key="adm_pp_domain")
            pp_smartar = st.text_area(
                "Initial SMARTAR Goal", height=90,
                placeholder="[Student] will… — teachers can refine this after observing the student.",
                key="adm_pp_smartar",
            )
            pp_period  = st.selectbox("Tracking Period", TRACKING_PERIODS, key="adm_pp_period")

            st.markdown("**GAS Levels** (optional — can be added/refined later)")
            pp_gas = {}
            for gas_key, (gas_label, gas_color) in GAS_LABELS.items():
                pp_gas[gas_key] = st.text_input(
                    gas_label, key=f"adm_pp_{gas_key}",
                    placeholder="Optional — leave blank to add later",
                )

            c1, c2 = st.columns(2)
            with c1:
                pp_start = st.date_input("Goal Start Date", value=date.today(), key="adm_pp_start")
            with c2:
                pp_target = st.date_input(
                    "Target Review Date",
                    value=date.today() + timedelta(weeks=8),
                    key="adm_pp_target",
                )

            if st.button("➕ Create Goal", type="primary", key="adm_pp_save"):
                if pp_student and pp_smartar.strip():
                    payload = {
                        "student_name":    pp_student,
                        "exclusion_goal":  pp_excl.strip(),
                        "smartar_goal":    pp_smartar.strip(),
                        "domain":          pp_domain,
                        "status":          "Active",
                        "active":          True,
                        "start_date":      str(pp_start),
                        "target_date":     str(pp_target),
                        "tracking_period": pp_period,
                    }
                    payload.update(pp_gas)
                    if save_goal(payload):
                        st.success(
                            f"✅ Goal created for {pp_student}. "
                            "Teachers can now begin tracking and refine as needed."
                        )
                        st.rerun()
                else:
                    st.warning("Please enter the SMARTAR goal.")
