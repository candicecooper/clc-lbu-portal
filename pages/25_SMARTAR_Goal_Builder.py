import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from datetime import datetime, date, timedelta
from io import BytesIO
import json
import requests
from PIL import Image

st.set_page_config(
    page_title="SMARTAR Goal Builder",
    page_icon="🎯",
    layout="wide",
)

# ─── Branding ────────────────────────────────────────────────────────────────
TEAL  = "#1A7A6E"
AMBER = "#C8760A"
PERF_COLORS = {
    "EXCEEDING": "#27ae60",
    "EXPECTED":  "#2980b9",
    "NOT YET":   "#c0392b",
}
PERF_ORDER = ["EXCEEDING", "EXPECTED", "NOT YET"]
PERF_NUM   = {"EXCEEDING": 3, "EXPECTED": 2, "NOT YET": 1}

TRACKING_PERIODS = [
    "All Day",
    "Morning Only",
    "Middle Only",
    "Afternoon Only",
    "Morning & Middle",
    "Middle & Afternoon",
]
SESSIONS_FOR_PERIOD = {
    "All Day":            ["Morning", "Middle", "Afternoon"],
    "Morning Only":       ["Morning"],
    "Middle Only":        ["Middle"],
    "Afternoon Only":     ["Afternoon"],
    "Morning & Middle":   ["Morning", "Middle"],
    "Middle & Afternoon": ["Middle", "Afternoon"],
}
DOMAINS = [
    "Behaviour", "Academic", "Social Skills",
    "Self-Regulation", "Communication", "Independence", "Other",
]

# ─── Supabase ─────────────────────────────────────────────────────────────────
from supabase import create_client

@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_sb()

# ─── Data helpers ─────────────────────────────────────────────────────────────

def all_students():
    try:
        rows = sb.table("smartar_goals").select("student_name").execute().data
        return sorted({r["student_name"] for r in rows if r.get("student_name")})
    except Exception:
        return []


def get_goals(student, status=None):
    try:
        q = sb.table("smartar_goals").select("*").eq("student_name", student)
        if status:
            q = q.eq("status", status)
        return q.order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"DB error: {e}")
        return []


def save_goal(payload: dict):
    try:
        if payload.get("id"):
            gid = payload.pop("id")
            payload["updated_at"] = datetime.utcnow().isoformat()
            sb.table("smartar_goals").update(payload).eq("id", gid).execute()
        else:
            payload["updated_at"] = datetime.utcnow().isoformat()
            sb.table("smartar_goals").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


def archive_goal(goal_id, reason=""):
    try:
        sb.table("smartar_goals").update({
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
            "status":         "Active",
            "archived_at":    None,
            "archive_reason": None,
            "updated_at":     datetime.utcnow().isoformat(),
        }).eq("id", goal_id).execute()
        return True
    except Exception:
        return False


def get_tracking(student, from_date, to_date, sessions=None):
    try:
        rows = (
            sb.table("smartar_tracking")
            .select("*")
            .eq("student_name", student)
            .gte("date", str(from_date))
            .lte("date", str(to_date))
            .order("date")
            .execute()
            .data
        )
        if sessions:
            rows = [r for r in rows if r.get("session") in sessions]
        return rows
    except Exception:
        return []


def goal_date_range(goal: dict):
    """(from_date_str, to_date_str) for the goal's active tracking window."""
    start = (goal.get("start_date") or (goal.get("created_at") or "")[:10]
             or date.today().isoformat())
    if goal.get("status") == "Archived" and goal.get("archived_at"):
        end = goal["archived_at"][:10]
    else:
        end = date.today().isoformat()
    return start, end


# ─── AI helper ────────────────────────────────────────────────────────────────

def ai_period_check(goal_text: str) -> dict:
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    if not groq_key:
        return {"period": "All Day",
                "reasoning": "AI key not configured.",
                "confidence": "Low"}
    prompt = f"""You are an educational support specialist. Analyse this student SMARTAR goal and determine the most appropriate tracking period within the school day.

Goal: {goal_text}

School sessions:
- Morning (~9am–11am): literacy, numeracy, structured academic learning
- Middle (~11am–1pm): recess, lunch, social time, transitions
- Afternoon (~1pm–3pm): specialist subjects, projects, outdoor education

Return ONLY valid JSON, no markdown or extra text:
{{
  "period": "All Day" | "Morning Only" | "Middle Only" | "Afternoon Only" | "Morning & Middle" | "Middle & Afternoon",
  "reasoning": "One concise sentence",
  "confidence": "High" | "Medium" | "Low"
}}

Rules:
- Use "All Day" unless the goal text CLEARLY references a specific time context
- "Morning Only" if the goal mentions morning block, assembly, literacy/numeracy time
- "Middle Only" if the goal mentions lunch, recess, break time, social time, playground
- "Afternoon Only" if the goal mentions afternoon session, specialist, outdoor ed
- Combinations if multiple relevant sessions mentioned
- Default "All Day" when uncertain"""
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":           "llama-3.3-70b-versatile",
                "messages":        [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature":     0.1,
                "max_tokens":      250,
            },
            timeout=12,
        )
        if r.status_code == 200:
            return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception:
        pass
    return {"period": "All Day",
            "reasoning": "AI check unavailable – defaulting to All Day.",
            "confidence": "Low"}


# ─── Chart helpers ────────────────────────────────────────────────────────────

def _short(text: str, n: int = 65) -> str:
    return text[:n] + "…" if len(text) > n else text


def _df(rows):
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["perf_num"] = df["performance"].map(PERF_NUM)
    return df


def make_goal_chart(rows, goal_text: str, from_date: str, to_date: str,
                    student_name: str = "") -> bytes | None:
    """
    Returns PNG bytes for a single goal's progress chart.
    Full title uses the actual goal text – not a generic label.
    Matplotlib with bbox_inches='tight' ensures nothing is clipped.
    """
    df = _df(rows)
    if df.empty:
        return None

    short_goal = _short(goal_text, 80)

    fig = plt.figure(figsize=(15, 9), facecolor="white")
    fig.suptitle(
        short_goal,
        fontsize=11,
        fontweight="bold",
        color=TEAL,
        y=0.98,
        wrap=True,
    )
    if student_name:
        fig.text(0.5, 0.955, student_name, ha="center", fontsize=9,
                 color=AMBER, fontweight="bold")

    gs = gridspec.GridSpec(
        2, 2, figure=fig,
        hspace=0.45, wspace=0.32,
        top=0.92, bottom=0.08,
        left=0.07, right=0.97,
    )

    # ── Top row: performance over time ───────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    daily = df.groupby("date")["perf_num"].mean().reset_index()
    ax1.plot(daily["date"], daily["perf_num"],
             color=TEAL, lw=1.5, alpha=0.45, zorder=1)
    sc_colors = [PERF_COLORS.get(p, "#888") for p in df["performance"]]
    ax1.scatter(df["date"], df["perf_num"],
                c=sc_colors, s=100, zorder=2,
                edgecolors="white", linewidth=0.9)
    ax1.set_yticks([1, 2, 3])
    ax1.set_yticklabels(["NOT YET", "EXPECTED", "EXCEEDING"], fontsize=9)
    ax1.set_ylim(0.3, 3.7)
    ax1.set_title("Performance Over Time", fontsize=10, color=TEAL,
                  fontweight="bold", loc="left", pad=6)
    ax1.annotate(
        f"Tracked: {from_date}  →  {to_date}",
        xy=(0.01, 0.05), xycoords="axes fraction",
        fontsize=8, color="gray",
    )
    ax1.tick_params(axis="x", rotation=35, labelsize=8)
    ax1.grid(axis="y", alpha=0.22)
    ax1.spines[["top", "right"]].set_visible(False)

    # Legend patches
    import matplotlib.patches as mpatches
    patches = [
        mpatches.Patch(color=PERF_COLORS[p], label=p)
        for p in PERF_ORDER if p in df["performance"].values
    ]
    ax1.legend(handles=patches, fontsize=8, loc="upper right",
               framealpha=0.7, ncol=3)

    # ── Bottom-left: distribution pie ────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    counts = df["performance"].value_counts().reindex(PERF_ORDER).dropna()
    if not counts.empty:
        pie_c = [PERF_COLORS[l] for l in counts.index]
        _, _, autotexts = ax2.pie(
            counts.values, labels=counts.index,
            colors=pie_c, autopct="%1.0f%%", startangle=90,
            textprops={"fontsize": 9},
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_fontsize(9)
            at.set_fontweight("bold")
    ax2.set_title("Distribution", fontsize=10, color=TEAL,
                  fontweight="bold", loc="left", pad=6)

    # ── Bottom-right: by session ─────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    if "session" in df.columns:
        sesses = [s for s in ["Morning", "Middle", "Afternoon"]
                  if s in df["session"].values]
        if sesses:
            x = np.arange(len(sesses))
            w = 0.26
            for i, perf in enumerate(PERF_ORDER):
                vals = [
                    df[(df["session"] == s) & (df["performance"] == perf)].shape[0]
                    for s in sesses
                ]
                ax3.bar(x + i * w, vals, w, label=perf,
                        color=PERF_COLORS[perf], alpha=0.85,
                        edgecolor="white", linewidth=0.8)
            ax3.set_xticks(x + w)
            ax3.set_xticklabels(sesses, fontsize=9)
            ax3.legend(fontsize=8)
            ax3.spines[["top", "right"]].set_visible(False)
            ax3.tick_params(labelsize=8)
            ax3.yaxis.get_major_locator().set_params(integer=True)
        else:
            ax3.axis("off")
            ax3.text(0.5, 0.5, "No session data", ha="center", va="center",
                     transform=ax3.transAxes, color="gray")
    else:
        ax3.axis("off")
    ax3.set_title("By Session", fontsize=10, color=TEAL,
                  fontweight="bold", loc="left", pad=6)

    fig.text(
        0.5, 0.01,
        f"CLC Learning and Behaviour Unit  |  Generated {datetime.now().strftime('%d %b %Y')}",
        ha="center", fontsize=7.5, color="#888", style="italic",
    )

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def make_student_pdf(student_name: str, goal_rows_list: list) -> bytes:
    """
    goal_rows_list: [(goal_dict, tracking_rows, from_d, to_d), …]
    Returns multi-page PDF bytes.
    """
    buf = BytesIO()
    with PdfPages(buf) as pdf:
        # Cover page ─────────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(11.69, 8.27), facecolor="white")
        ax.axis("off")
        ax.add_patch(plt.Rectangle(
            (0, 0.78), 1, 0.22,
            transform=ax.transAxes, facecolor=TEAL, zorder=0,
        ))
        ax.text(0.5, 0.895, "SMARTAR Goal Progress Report",
                ha="center", va="center", fontsize=22, fontweight="bold",
                color="white", transform=ax.transAxes)
        ax.text(0.5, 0.635, student_name,
                ha="center", va="center", fontsize=20,
                fontweight="bold", color=AMBER, transform=ax.transAxes)
        ax.text(0.5, 0.545,
                f"Generated: {datetime.now().strftime('%d %B %Y')}",
                ha="center", fontsize=12, color="gray",
                transform=ax.transAxes)
        ax.text(0.5, 0.47,
                "CLC Learning and Behaviour Unit",
                ha="center", fontsize=11, color="gray",
                transform=ax.transAxes)
        ax.text(0.5, 0.39,
                f"Goals included in this report: {len(goal_rows_list)}",
                ha="center", fontsize=11, color="#555",
                transform=ax.transAxes)
        pdf.savefig(fig, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        # One page per goal ───────────────────────────────────────────────────
        for idx, (goal, rows, from_d, to_d) in enumerate(goal_rows_list, 1):
            png_bytes = make_goal_chart(
                rows, goal["goal_text"], from_d, to_d,
                student_name=student_name,
            )
            if not png_bytes:
                continue
            img = Image.open(BytesIO(png_bytes))
            pg_fig, pg_ax = plt.subplots(
                figsize=(11.69, 8.27), facecolor="white")
            pg_ax.imshow(np.array(img))
            pg_ax.axis("off")
            status = goal.get("status", "Active")
            domain = goal.get("domain", "")
            period = goal.get("tracking_period", "All Day")
            pg_fig.text(
                0.5, 0.005,
                f"Goal {idx}  ·  [{status}]  ·  {domain}  ·  Period: {period}",
                ha="center", fontsize=8, color="gray",
            )
            pdf.savefig(pg_fig, bbox_inches="tight", facecolor="white")
            plt.close(pg_fig)

    buf.seek(0)
    return buf.getvalue()


# ─── Styles ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  [data-testid="stSidebar"] {{ display: none !important; }}
  .goal-card {{
      border: 1px solid #ddd;
      border-left: 5px solid {TEAL};
      border-radius: 6px;
      padding: 12px 16px;
      margin-bottom: 10px;
      background: #fafafa;
  }}
  .archived-card {{
      border-left-color: {AMBER} !important;
      background: #fffbf4 !important;
  }}
  h1, h2 {{ color: {TEAL}; }}
  .stTabs [role="tablist"] button {{ font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🎯 SMARTAR Goal Builder")
st.caption(
    "**S**pecific · **M**easurable · **A**chievable · **R**elevant · "
    "**T**ime-bound · **A**ttainable · **R**ecorded"
)

# Preload from query params (e.g. from Team Meetings link)
params          = st.query_params
preload_student = params.get("student", "")
preload_goal    = params.get("goal", "")

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Goal Builder",
    "📋 Student Goals",
    "📈 Progress Reports",
    "📚 Goal Bank",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – GOAL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Build a SMARTAR Goal")

    # If editing an existing goal, load it into session state
    edit_goal_data = st.session_state.get("gb_edit_data", {})

    c1, c2 = st.columns([2, 1])
    with c1:
        student_name = st.text_input(
            "Student Name",
            value=edit_goal_data.get("student_name", preload_student),
            placeholder="Enter student name",
            key="gb_student",
        )
    with c2:
        domain_idx = DOMAINS.index(edit_goal_data.get("domain", "Behaviour")) \
            if edit_goal_data.get("domain") in DOMAINS else 0
        domain = st.selectbox("Goal Domain", DOMAINS, index=domain_idx, key="gb_domain")

    goal_text = st.text_area(
        "Goal Text",
        value=edit_goal_data.get("goal_text", preload_goal),
        height=100,
        placeholder="Write the full SMARTAR goal statement here…",
        key="gb_goal_text",
    )

    # ── AI tracking period check ─────────────────────────────────────────────
    ai_key = "gb_ai_result"
    ai_result = st.session_state.get(ai_key)

    if goal_text.strip():
        if st.button("🤖 Check Recommended Tracking Period (AI)", key="gb_ai_btn"):
            with st.spinner("Analysing goal text…"):
                ai_result = ai_period_check(goal_text)
                st.session_state[ai_key] = ai_result

    suggested_period = "All Day"
    if ai_result:
        confidence = ai_result.get("confidence", "Low")
        col_clr = {"High": "green", "Medium": "orange", "Low": "gray"}.get(confidence, "gray")
        st.info(
            f"**AI Recommendation:** {ai_result['period']}\n\n"
            f"*{ai_result.get('reasoning', '')}*  \n"
            f"Confidence: {confidence}"
        )
        suggested_period = ai_result.get("period", "All Day")
        if suggested_period not in TRACKING_PERIODS:
            suggested_period = "All Day"

    period_idx = TRACKING_PERIODS.index(
        edit_goal_data.get("tracking_period", suggested_period)
        if edit_goal_data.get("tracking_period") in TRACKING_PERIODS
        else suggested_period
    )
    tracking_period = st.selectbox(
        "Tracking Period",
        TRACKING_PERIODS,
        index=period_idx,
        key="gb_period",
        help="Which sessions of the day this goal should be tracked. "
             "AI check above will suggest the best fit.",
    )
    st.caption(
        f"📅 Sessions to track: **{', '.join(SESSIONS_FOR_PERIOD[tracking_period])}**"
    )

    with st.expander("📝 SMARTAR Components (optional detail)"):
        specific = st.text_area(
            "🎯 Specific – What exactly will the student do?",
            value=edit_goal_data.get("specific", ""),
            height=65, key="gb_s",
        )
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            mm_opts = [
                "Frequency count", "Duration", "Percentage/Rate",
                "Rating scale", "Observation checklist", "Other",
            ]
            mm_idx = mm_opts.index(edit_goal_data.get("measurement_method", "Frequency count")) \
                if edit_goal_data.get("measurement_method") in mm_opts else 0
            measurement_method = st.selectbox(
                "📏 Measurement Method", mm_opts, index=mm_idx, key="gb_mm")
        with col_m2:
            measurement_detail = st.text_input(
                "Measurement detail (e.g. 4/5 opportunities)",
                value=edit_goal_data.get("measurement_detail", ""),
                key="gb_md",
            )
        achievable = st.text_area(
            "✅ Achievable – Why is this achievable for this student now?",
            value=edit_goal_data.get("achievable", ""),
            height=65, key="gb_a",
        )
        relevant = st.text_area(
            "🎓 Relevant – Why is this meaningful for this student?",
            value=edit_goal_data.get("relevant", ""),
            height=65, key="gb_r",
        )
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_val = date.today()
            if edit_goal_data.get("start_date"):
                try:
                    start_val = date.fromisoformat(edit_goal_data["start_date"])
                except Exception:
                    pass
            start_date = st.date_input("Goal Start Date", value=start_val, key="gb_start")
        with col_d2:
            target_val = date.today() + timedelta(weeks=8)
            if edit_goal_data.get("target_date"):
                try:
                    target_val = date.fromisoformat(edit_goal_data["target_date"])
                except Exception:
                    pass
            target_date = st.date_input("Target Review Date", value=target_val, key="gb_target")
        attainable = st.text_area(
            "🏆 Attainable – Supports / scaffolding in place?",
            value=edit_goal_data.get("attainable", ""),
            height=65, key="gb_att",
        )
        recorded = st.text_area(
            "📊 Recorded – How will progress be recorded?",
            value=edit_goal_data.get("recorded", ""),
            height=65, key="gb_rec",
        )

    with st.expander("📊 Goal Attainment Scaling (GAS) Levels"):
        gas_labels = {
            "+2": "Much better than expected",
            "+1": "Better than expected",
            "0":  "Expected outcome (goal met)",
            "-1": "Somewhat less than expected",
            "-2": "Much less than expected",
        }
        existing_gas = {}
        if edit_goal_data.get("gas_levels"):
            try:
                existing_gas = json.loads(edit_goal_data["gas_levels"])
            except Exception:
                pass
        gas = {}
        for level, desc in gas_labels.items():
            gas[level] = st.text_input(
                f"{level}: {desc}",
                value=existing_gas.get(level, ""),
                key=f"gb_gas_{level}",
            )

    with st.expander("⚙️ Goal Settings"):
        success_pct = st.slider(
            "Success Threshold (%)", 50, 100,
            value=edit_goal_data.get("success_percentage", 80),
            key="gb_pct",
        )
        trial_count = st.number_input(
            "Trials per measurement", 1, 20,
            value=edit_goal_data.get("trial_count", 5),
            key="gb_trials",
        )
        notes = st.text_area(
            "Additional Notes",
            value=edit_goal_data.get("notes", ""),
            height=65, key="gb_notes",
        )

    st.divider()
    edit_id = st.session_state.get("gb_edit_id")
    save_label = "💾 Update Goal" if edit_id else "💾 Save New Goal"

    if st.button(save_label, type="primary", key="gb_save"):
        if student_name.strip() and goal_text.strip():
            payload = {
                "student_name":       student_name.strip(),
                "goal_text":          goal_text.strip(),
                "domain":             domain,
                "status":             "Active",
                "start_date":         str(start_date),
                "target_date":        str(target_date),
                "tracking_period":    tracking_period,
                "specific":           specific,
                "measurement_method": measurement_method,
                "measurement_detail": measurement_detail,
                "achievable":         achievable,
                "relevant":           relevant,
                "attainable":         attainable,
                "recorded":           recorded,
                "success_percentage": success_pct,
                "trial_count":        trial_count,
                "notes":              notes,
                "gas_levels":         json.dumps(gas),
            }
            if edit_id:
                payload["id"] = edit_id
            if save_goal(payload):
                st.success("✅ Goal saved successfully!")
                for k in ["gb_ai_result", "gb_edit_id", "gb_edit_data"]:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            st.warning("Please enter student name and goal text.")

    if edit_id:
        if st.button("✖ Cancel Edit", key="gb_cancel"):
            for k in ["gb_edit_id", "gb_edit_data"]:
                st.session_state.pop(k, None)
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – STUDENT GOALS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📋 Student Goals")

    students = all_students()
    if students:
        sg_student = st.selectbox("Select Student", students, key="sg_sel")
    else:
        sg_student = st.text_input("Student Name", key="sg_txt")

    if sg_student:
        active_goals   = get_goals(sg_student, status="Active")
        archived_goals = get_goals(sg_student, status="Archived")
        completed_goals = get_goals(sg_student, status="Completed")

        # ── Active Goals ─────────────────────────────────────────────────────
        st.markdown(f"#### ✅ Active Goals ({len(active_goals)})")
        if not active_goals:
            st.info("No active goals. Create one in the Goal Builder tab.")

        for g in active_goals:
            from_d, to_d = goal_date_range(g)
            period = g.get("tracking_period", "All Day")
            sessions_str = ", ".join(SESSIONS_FOR_PERIOD.get(period, ["All Day"]))

            st.markdown(f"""<div class="goal-card">
                <strong>{g.get('domain','—')}</strong>&nbsp;·&nbsp;
                <em style="color:{TEAL}">{period} ({sessions_str})</em><br>
                <span style="font-size:14px">{g['goal_text']}</span><br>
                <small style="color:#888">
                  Started: {from_d}&nbsp;·&nbsp;Target: {g.get('target_date','—')}
                </small>
            </div>""", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("📝 Edit", key=f"edit_{g['id']}"):
                    st.session_state["gb_edit_id"]   = g["id"]
                    st.session_state["gb_edit_data"]  = g
                    st.session_state["gb_ai_result"]  = None
                    st.info("Switch to the **Goal Builder** tab to edit this goal.")
            with c2:
                if st.button("✅ Mark Complete", key=f"comp_{g['id']}"):
                    sb.table("smartar_goals").update({"status": "Completed"}).eq("id", g["id"]).execute()
                    st.rerun()
            with c3:
                if st.button("🗃️ Archive Goal", key=f"arch_{g['id']}"):
                    st.session_state[f"arch_confirm_{g['id']}"] = True

            if st.session_state.get(f"arch_confirm_{g['id']}"):
                reason_key = f"arch_reason_{g['id']}"
                reason = st.text_input(
                    "Archive reason (optional – e.g. 'Goal updated', 'Achieved'):",
                    key=reason_key,
                )
                ca, cb = st.columns(2)
                with ca:
                    if st.button("✓ Confirm Archive", key=f"arch_do_{g['id']}", type="primary"):
                        if archive_goal(g["id"], reason):
                            st.success("✅ Goal archived. All tracking data preserved.")
                            st.session_state.pop(f"arch_confirm_{g['id']}", None)
                            st.rerun()
                with cb:
                    if st.button("✖ Cancel", key=f"arch_cancel_{g['id']}"):
                        st.session_state.pop(f"arch_confirm_{g['id']}", None)
                        st.rerun()
            st.markdown("---")

        # ── Archived Goals ───────────────────────────────────────────────────
        if archived_goals:
            st.markdown(f"#### 🗃️ Archived Goals ({len(archived_goals)})")
            for g in archived_goals:
                from_d, to_d = goal_date_range(g)
                period = g.get("tracking_period", "All Day")
                archived_at = (g.get("archived_at") or "")[:10]
                reason = g.get("archive_reason", "")

                with st.expander(
                    f"🗃 {g.get('domain','—')} – {_short(g['goal_text'], 60)}"
                ):
                    st.markdown(f"""<div class="goal-card archived-card">
                        <strong>{g.get('domain','—')}</strong>&nbsp;·&nbsp;
                        <em style="color:{AMBER}">{period}</em><br>
                        <span style="font-size:14px">{g['goal_text']}</span><br>
                        <small style="color:#888">
                          Active: {from_d} → {archived_at}
                          {f'&nbsp;·&nbsp;Reason: {reason}' if reason else ''}
                        </small>
                    </div>""", unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("♻️ Restore to Active", key=f"restore_{g['id']}"):
                            restore_goal(g["id"])
                            st.rerun()
                    with c2:
                        if st.button("➕ Start Updated Goal", key=f"new_from_{g['id']}"):
                            st.session_state["gb_student"]   = g["student_name"]
                            st.session_state["gb_edit_id"]   = None
                            st.session_state["gb_edit_data"] = {}
                            st.info(
                                "Switch to **Goal Builder** tab to create an updated "
                                "goal for this student."
                            )

        # ── Completed Goals ──────────────────────────────────────────────────
        if completed_goals:
            st.markdown(f"#### 🏆 Completed Goals ({len(completed_goals)})")
            for g in completed_goals:
                from_d, to_d = goal_date_range(g)
                with st.expander(
                    f"🏆 {g.get('domain','—')} – {_short(g['goal_text'], 60)}"
                ):
                    st.markdown(f"**Goal:** {g['goal_text']}")
                    st.caption(f"Period: {from_d} → {to_d}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – PROGRESS REPORTS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📈 Progress Reports")

    students = all_students()
    if students:
        rpt_student = st.selectbox("Select Student", students, key="rpt_sel")
    else:
        rpt_student = st.text_input("Student Name", key="rpt_txt")

    if rpt_student:
        # Fetch all goals (all statuses)
        all_goals = (
            get_goals(rpt_student, "Active") +
            get_goals(rpt_student, "Archived") +
            get_goals(rpt_student, "Completed")
        )
        # Sort by start_date descending
        all_goals.sort(
            key=lambda g: g.get("start_date") or (g.get("created_at") or "")[:10],
            reverse=True,
        )

        if not all_goals:
            st.info("No goals found for this student.")
        else:
            st.caption(f"{len(all_goals)} goal(s) found · charts use full goal text as title")

            goal_rows_list = []  # for PDF

            for idx, goal in enumerate(all_goals, 1):
                from_d, to_d = goal_date_range(goal)
                period   = goal.get("tracking_period", "All Day")
                sessions = SESSIONS_FOR_PERIOD.get(period, ["Morning", "Middle", "Afternoon"])
                tracking = get_tracking(rpt_student, from_d, to_d, sessions=sessions)

                if tracking:
                    actual_from = min(r["date"] for r in tracking)[:10]
                    actual_to   = max(r["date"] for r in tracking)[:10]
                    track_str   = f"{actual_from} → {actual_to}"
                    n_entries   = len(tracking)
                else:
                    actual_from = from_d
                    actual_to   = to_d
                    track_str   = "No entries yet"
                    n_entries   = 0

                status = goal.get("status", "Active")
                status_icon = {"Active": "🟢", "Archived": "🟠", "Completed": "🔵"}.get(status, "⚪")
                domain = goal.get("domain", "—")

                expander_title = (
                    f"{status_icon} Goal {idx} ({status}): "
                    f"{domain} – {_short(goal['goal_text'], 55)}"
                )

                with st.expander(expander_title, expanded=(idx == 1)):
                    col_info, col_dl = st.columns([3, 1])

                    with col_info:
                        st.markdown(
                            f"**Domain:** {domain}&nbsp;&nbsp;**Period:** {period}"
                            f"&nbsp;&nbsp;(**Sessions:** {', '.join(sessions)})"
                        )
                        st.markdown(f"**Goal:** {goal['goal_text']}")
                        st.markdown(
                            f"**Goal active:** {from_d} → {to_d}"
                            f"&nbsp;&nbsp;·&nbsp;&nbsp;"
                            f"**Tracking entries:** {n_entries}"
                        )
                        st.markdown(f"**Tracking date range:** {track_str}")
                        if goal.get("archive_reason"):
                            st.caption(f"Archive reason: {goal['archive_reason']}")

                    if tracking:
                        goal_rows_list.append((goal, tracking, actual_from, actual_to))
                        png_bytes = make_goal_chart(
                            tracking, goal["goal_text"],
                            actual_from, actual_to,
                            student_name=rpt_student,
                        )
                        if png_bytes:
                            st.image(png_bytes, use_container_width=True)
                            with col_dl:
                                safe_name = goal["goal_text"][:30].replace(" ", "_").replace("/", "-")
                                st.download_button(
                                    "📥 PNG",
                                    data=png_bytes,
                                    file_name=f"{rpt_student}_{domain}_goal{idx}_{safe_name}.png",
                                    mime="image/png",
                                    key=f"dl_png_{goal['id']}",
                                    help="Download this chart as PNG",
                                )
                    else:
                        st.info("No tracking data recorded for this goal's sessions and period yet.")

            # ── Download All as PDF ──────────────────────────────────────────
            if goal_rows_list:
                st.divider()
                st.markdown("#### 📄 Download All Goal Charts")
                st.caption(
                    f"Includes {len(goal_rows_list)} goal(s) with tracking data as a "
                    "multi-page PDF with cover page."
                )
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
    st.info("Select a template to pre-load it into the Goal Builder.")

    templates = {
        "Self-Regulation": [
            "When feeling frustrated, [Student] will use a break card to request a 5-minute sensory break before escalating, measured by frequency count, 4 out of 5 opportunities daily.",
            "[Student] will identify their emotion using the Zones of Regulation before transitioning between activities, in 3 out of 5 transitions per day.",
            "[Student] will use a self-regulation strategy (e.g. deep breathing, fidget, movement break) when prompted during periods of dysregulation, 3 out of 5 opportunities.",
        ],
        "Communication": [
            "[Student] will use a verbal or AAC-supported request to ask for help during structured tasks, in 4 out of 5 opportunities across the school day.",
            "[Student] will initiate a social greeting with a peer or staff member during morning arrival, on 3 out of 5 school days.",
            "[Student] will use 2–3 word phrases to communicate wants or needs to a familiar adult, in 4 out of 5 daily communication opportunities.",
        ],
        "Behaviour": [
            "[Student] will remain in the classroom for a full structured learning session (45 min) without needing a sensory break, on 3 out of 5 days per week.",
            "[Student] will transition between activities within 3 minutes of the schedule change signal, in 4 out of 5 transitions daily.",
            "[Student] will use a safe touch or verbal request rather than physical aggression when seeking peer interaction, in 4 out of 5 observed interactions.",
        ],
        "Academic": [
            "[Student] will independently complete a 10-minute reading task with fewer than 2 prompts, in 3 out of 5 sessions.",
            "[Student] will attempt all items on a 10-question maths worksheet before requesting support, in 4 out of 5 sessions.",
        ],
        "Social Skills": [
            "[Student] will participate in a structured peer activity for a minimum of 10 minutes without leaving or becoming dysregulated, in 3 out of 5 sessions.",
            "[Student] will take turns with a peer in a structured game without adult prompting, in 3 out of 5 opportunities.",
        ],
        "Independence": [
            "[Student] will independently unpack their bag and begin morning routine tasks within 5 minutes of arriving at school, on 4 out of 5 days.",
            "[Student] will pack away materials at the end of a task without a verbal prompt, in 3 out of 5 opportunities.",
        ],
    }

    for category, goal_list in templates.items():
        with st.expander(f"**{category}** ({len(goal_list)} templates)"):
            for g in goal_list:
                cols = st.columns([6, 1])
                cols[0].markdown(f"_{g}_")
                if cols[1].button("Use", key=f"tpl_{abs(hash(g))}"):
                    st.session_state["gb_goal_text"] = g
                    st.session_state.pop("gb_ai_result", None)
                    st.success("Template loaded into Goal Builder tab.")
