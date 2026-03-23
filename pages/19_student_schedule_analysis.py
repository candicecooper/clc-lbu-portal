# ════════════════════════════════════════════════════════════════════════════
# 19_Student_Schedule_Analysis.py  ·  CLC-LBU Portal
# ACCEPT Program — Student Schedule Analysis
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from auth import require_auth, logout_button
require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
logout_button()

# ── Colours ──────────────────────────────────────────────────────────────────
TEAL  = "#1A6B8A"
AMBER = "#D4860A"

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:#f5f8fa; }}
.clc-header {{
    background: linear-gradient(135deg, {TEAL} 0%, {TEAL}BB 100%);
    color: white; padding: 1rem 1.5rem;
    border-radius: 10px; margin-bottom: 1.25rem;
}}
.clc-header h2 {{ margin:0; font-size:1.35rem; }}
.clc-header p  {{ margin:.2rem 0 0; opacity:.85; font-size:.82rem; }}
.kpi {{
    background: white; border-left: 4px solid {TEAL};
    border-radius: 6px; padding: .55rem .9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    text-align: center; margin-bottom: .5rem;
}}
.kpi .val {{ font-size: 1.7rem; font-weight: 700; color:{TEAL}; line-height: 1.1; }}
.kpi .lbl {{ font-size: .72rem; color: #666; margin-top: .15rem; }}
.kpi-amber {{ border-color:{AMBER}; }}
.kpi-amber .val {{ color:{AMBER}; }}
.insight {{
    background:#FEF9EC; border:1px solid {AMBER}55;
    border-left: 4px solid {AMBER};
    border-radius: 6px; padding: .55rem 1rem;
    font-size: .85rem; margin-bottom: .4rem;
}}
.insight-ok {{
    background:#F0FAF4; border:1px solid #2EA05655;
    border-left: 4px solid #2EA056;
}}
.legend-row {{
    display:flex; flex-wrap:wrap; gap:.5rem;
    background:#EBF4F9; border:1px solid {TEAL}44;
    border-radius:6px; padding:.5rem 1rem;
    font-size:.84rem; margin-bottom:.75rem;
}}
.legend-item {{ white-space:nowrap; }}
.badge-s {{
    background:#FEF3C7; color:#92400E;
    border-radius:4px; padding:.1rem .4rem; font-weight:600;
}}
.badge-e {{
    background:#FEE2E2; color:#991B1B;
    border-radius:4px; padding:.1rem .4rem; font-weight:600;
}}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
GROUPINGS = ["i", "1:1", "sg", "wg", "U", "P"]
GROUPING_LABELS = {
    "i":   "Independent",
    "1:1": "One-to-one",
    "sg":  "Small group",
    "wg":  "Whole group",
    "U":   "Unstructured",
    "P":   "Peer",
}
TASK_TYPES = ["Paper/pencil", "Oral/listening", "Hands on", "Play based", "Class routine", "Computer"]
RATINGS = ["s", "e"]
RATING_LABELS = {"s": "Sometimes (s)", "e": "Excessive / often (e)"}

# ── Session state init ────────────────────────────────────────────────────────
def _init():
    defaults = {
        "ssa_student":    "",
        "ssa_term":       "3",
        "ssa_week":       1,
        "ssa_behaviours": "Roaming around the environment instead of participating in learning at a particular area",
        "ssa_entries":    [],
        "ssa_saved_id":   None,
        "ssa_f_date":     date.today(),
        "ssa_f_time":     "",
        "ssa_f_activity": "",
        "ssa_f_rating":   "s",
        "ssa_f_grouping": "i",
        "ssa_f_tasks":    [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
ss = st.session_state

# ── Supabase ──────────────────────────────────────────────────────────────────
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 📂 Sessions")
    sb = get_sb()
    if sb:
        try:
            sessions = (
                sb.table("schedule_analysis_sessions")
                .select("id,student_name,term,week_number")
                .order("created_at", desc=True)
                .limit(30)
                .execute()
            )
            if sessions.data:
                opts = {
                    f"{r['student_name']} — T{r['term']} W{r['week_number']}": r["id"]
                    for r in sessions.data
                }
                chosen = st.selectbox("Load session", ["— New —"] + list(opts.keys()))
                if chosen != "— New —" and st.button("Load", use_container_width=True):
                    sid = opts[chosen]
                    rec = sb.table("schedule_analysis_sessions").select("*").eq("id", sid).single().execute().data
                    entries_raw = sb.table("schedule_analysis_entries").select("*").eq("session_id", sid).execute().data
                    ss.ssa_student    = rec["student_name"]
                    ss.ssa_term       = rec["term"]
                    ss.ssa_week       = rec["week_number"]
                    ss.ssa_behaviours = rec["target_behaviours"]
                    ss.ssa_saved_id   = sid
                    ss.ssa_entries    = [
                        {
                            "date":     e["entry_date"],
                            "time":     e["time_slot"],
                            "activity": e["class_activity"],
                            "rating":   e["rating"],
                            "grouping": e["grouping"],
                            "tasks":    e["task_types"],
                        }
                        for e in entries_raw
                    ]
                    st.success("Loaded!")
                    st.rerun()
        except Exception as e:
            st.caption(f"⚠️ {e}")
    else:
        st.caption("Supabase not configured.")

    st.markdown("---")
    if st.button("🆕 New Session", use_container_width=True):
        for k in list(ss.keys()):
            if k.startswith("ssa_"):
                del st.session_state[k]
        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="clc-header">
  <h2>🗂️ ACCEPT Program — Student Schedule Analysis</h2>
  <p>Aligning Curriculum for Competency in Education and Purposeful Transition &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
t_entry, t_data, t_analysis = st.tabs([
    "📋  Entry Form",
    "📄  View & Edit Records",
    "📈  Analysis & Insights",
])

# ────────────────────────────────────────────────────────────────────────────
# TAB 1 — ENTRY FORM
# ────────────────────────────────────────────────────────────────────────────
with t_entry:

    c1, c2, c3 = st.columns([3, 1, 1])
    ss.ssa_student = c1.text_input("Student", ss.ssa_student)
    ss.ssa_term    = c2.text_input("Term", ss.ssa_term)
    ss.ssa_week    = int(c3.number_input("Week", 1, 20, int(ss.ssa_week)))

    ss.ssa_behaviours = st.text_area("Target Behaviours", ss.ssa_behaviours, height=68)

    st.markdown("""
    <div class="legend-row">
        <span class="legend-item"><b>Rating:</b></span>
        <span class="legend-item"><span class="badge-s">s</span> = sometimes</span>
        <span class="legend-item"><span class="badge-e">e</span> = excessive / often</span>
        &nbsp;&nbsp;
        <span class="legend-item"><b>Grouping:</b></span>
        <span class="legend-item"><b>i</b> = independent</span>
        <span class="legend-item"><b>1:1</b> = one to one</span>
        <span class="legend-item"><b>sg</b> = small group</span>
        <span class="legend-item"><b>wg</b> = whole group</span>
        <span class="legend-item"><b>U</b> = unstructured</span>
        <span class="legend-item"><b>P</b> = peer</span>
    </div>
    """, unsafe_allow_html=True)

    with st.form("ssa_add_entry", clear_on_submit=True):
        st.markdown("#### ＋ Add Observation")
        fc1, fc2, fc3 = st.columns([2, 1, 3])
        f_date     = fc1.date_input("Date", ss.ssa_f_date)
        f_time     = fc2.text_input("Time (e.g. 9:30)", ss.ssa_f_time)
        f_activity = fc3.text_input("Class / Activity", ss.ssa_f_activity)

        fc4, fc5 = st.columns(2)
        f_rating   = fc4.selectbox("Rating", RATINGS, format_func=lambda x: RATING_LABELS[x])
        f_grouping = fc5.selectbox("Grouping", GROUPINGS, format_func=lambda x: f"{x} — {GROUPING_LABELS[x]}")
        f_tasks    = st.multiselect("Task Type", TASK_TYPES)

        submitted = st.form_submit_button("Add observation", type="primary", use_container_width=True)

    if submitted:
        ss.ssa_entries.append({
            "date":     f_date.isoformat(),
            "time":     f_time,
            "activity": f_activity,
            "rating":   f_rating,
            "grouping": f_grouping,
            "tasks":    f_tasks,
        })
        st.success(f"✅ Added: {f_activity} ({f_time}) — {RATING_LABELS[f_rating]}")
        st.rerun()

    n = len(ss.ssa_entries)
    if n > 0:
        n_e = sum(1 for e in ss.ssa_entries if e["rating"] == "e")
        n_s = sum(1 for e in ss.ssa_entries if e["rating"] == "s")
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='kpi'><div class='val'>{n}</div><div class='lbl'>Total observations</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='kpi kpi-amber'><div class='val'>{n_e}</div><div class='lbl'>Excessive / often (e)</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='kpi'><div class='val'>{n_s}</div><div class='lbl'>Sometimes (s)</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("💾 Save to Supabase", type="primary", disabled=(n == 0)):
        sb = get_sb()
        if sb:
            try:
                payload = {
                    "student_name":      ss.ssa_student,
                    "term":              ss.ssa_term,
                    "week_number":       int(ss.ssa_week),
                    "target_behaviours": ss.ssa_behaviours,
                }
                if ss.ssa_saved_id:
                    sb.table("schedule_analysis_sessions").update(payload).eq("id", ss.ssa_saved_id).execute()
                    sid = ss.ssa_saved_id
                    sb.table("schedule_analysis_entries").delete().eq("session_id", sid).execute()
                else:
                    res = sb.table("schedule_analysis_sessions").insert(payload).execute()
                    sid = res.data[0]["id"]
                    ss.ssa_saved_id = sid

                rows = [
                    {
                        "session_id":     sid,
                        "entry_date":     e["date"],
                        "time_slot":      e["time"],
                        "class_activity": e["activity"],
                        "rating":         e["rating"],
                        "grouping":       e["grouping"],
                        "task_types":     e["tasks"],
                    }
                    for e in ss.ssa_entries
                ]
                if rows:
                    sb.table("schedule_analysis_entries").insert(rows).execute()
                st.success("✅ Session saved successfully!")
            except Exception as e:
                st.error(f"Save failed: {e}")
        else:
            st.warning("Supabase not configured.")

# ────────────────────────────────────────────────────────────────────────────
# TAB 2 — VIEW & EDIT
# ────────────────────────────────────────────────────────────────────────────
with t_data:
    if not ss.ssa_entries:
        st.info("No observations recorded yet. Use the Entry Form to add records.")
        st.stop()

    df_raw = pd.DataFrame(ss.ssa_entries)
    df_raw["tasks_str"] = df_raw["tasks"].apply(lambda t: ", ".join(t) if isinstance(t, list) else t)

    display = df_raw[["date", "time", "activity", "rating", "grouping", "tasks_str"]].copy()
    display.columns = ["Date", "Time", "Class / Activity", "Rating", "Grouping", "Task Types"]

    edited = st.data_editor(
        display,
        use_container_width=True,
        hide_index=False,
        column_config={
            "Date":     st.column_config.DateColumn("Date"),
            "Rating":   st.column_config.SelectboxColumn("Rating", options=RATINGS),
            "Grouping": st.column_config.SelectboxColumn("Grouping", options=GROUPINGS),
        },
        num_rows="dynamic",
        key="ssa_de"
    )

    del_idx = st.number_input("Delete row (by index)", min_value=0, max_value=max(0, len(ss.ssa_entries) - 1), step=1, value=0)
    if st.button("🗑️ Delete this row") and ss.ssa_entries:
        ss.ssa_entries.pop(int(del_idx))
        st.success("Row deleted.")
        st.rerun()

# ────────────────────────────────────────────────────────────────────────────
# TAB 3 — ANALYSIS
# ────────────────────────────────────────────────────────────────────────────
with t_analysis:
    if not ss.ssa_entries:
        st.info("No observations recorded yet. Add data via the Entry Form first.")
        st.stop()

    df = pd.DataFrame(ss.ssa_entries)
    df["rating_label"]   = df["rating"].map(RATING_LABELS)
    df["grouping_label"] = df["grouping"].map(GROUPING_LABELS)
    df["is_excessive"]   = df["rating"] == "e"

    n_total     = len(df)
    n_excessive = int(df["is_excessive"].sum())
    pct_excess  = round(100 * n_excessive / n_total) if n_total else 0
    top_group   = df.groupby("grouping_label")["is_excessive"].sum().idxmax() if n_excessive else "—"

    st.markdown(f"### Analysis — {ss.ssa_student} &nbsp;|&nbsp; Term {ss.ssa_term}, Week {ss.ssa_week}")

    k1, k2, k3, k4 = st.columns(4)
    for col, val, lbl, amber in [
        (k1, n_total,         "Total observations",      False),
        (k2, n_excessive,     "Excessive / often (e)",   True),
        (k3, f"{pct_excess}%","% rated excessive",       True),
        (k4, top_group,       "Grouping with most (e)",  True),
    ]:
        cls  = "kpi kpi-amber" if amber else "kpi"
        vcls = f"color:{AMBER}" if amber else f"color:{TEAL}"
        col.markdown(
            f"<div class='{cls}'><div class='val' style='{vcls};font-size:1.1rem'>{val}</div>"
            f"<div class='lbl'>{lbl}</div></div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        rating_counts = df["rating_label"].value_counts().reset_index()
        rating_counts.columns = ["Rating", "Count"]
        fig_pie = px.pie(
            rating_counts, values="Count", names="Rating",
            color="Rating",
            color_discrete_map={"Sometimes (s)": "#FCD34D", "Excessive / often (e)": "#EF4444"},
            title="Rating Breakdown (s vs e)", hole=0.4,
        )
        fig_pie.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        grp_df = df.groupby(["grouping_label", "rating_label"]).size().reset_index(name="Count")
        fig_grp = px.bar(
            grp_df, x="grouping_label", y="Count", color="rating_label",
            color_discrete_map={"Sometimes (s)": "#FCD34D", "Excessive / often (e)": "#EF4444"},
            title="Behaviour Rating by Grouping",
            labels={"grouping_label": "Grouping", "rating_label": "Rating"},
            barmode="stack",
        )
        fig_grp.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_grp, use_container_width=True)

    st.markdown("### 📚 Task Type Analysis")
    task_rows = []
    for _, row in df.iterrows():
        tasks = row["tasks"] if isinstance(row["tasks"], list) else []
        if not tasks:
            tasks = ["(not recorded)"]
        for task in tasks:
            task_rows.append({"Task Type": task, "Rating": row["rating_label"], "is_e": row["is_excessive"]})

    df_tasks = pd.DataFrame(task_rows)
    if not df_tasks.empty:
        task_counts = df_tasks.groupby(["Task Type", "Rating"]).size().reset_index(name="Count")
        fig_tasks = px.bar(
            task_counts, x="Task Type", y="Count", color="Rating",
            color_discrete_map={"Sometimes (s)": "#FCD34D", "Excessive / often (e)": "#EF4444"},
            title="Behaviour Frequency by Task Type", barmode="stack",
        )
        fig_tasks.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_tasks, use_container_width=True)

        task_e_rate = df_tasks.groupby("Task Type")["is_e"].agg(["sum", "count"]).reset_index()
        task_e_rate.columns = ["Task Type", "Excessive count", "Total"]
        task_e_rate["% excessive"] = (100 * task_e_rate["Excessive count"] / task_e_rate["Total"]).round(0).astype(int).astype(str) + "%"
        task_e_rate = task_e_rate.sort_values("Excessive count", ascending=False)
        st.dataframe(task_e_rate, use_container_width=True, hide_index=True)

    st.markdown("### 🏫 Activity Analysis")
    act_df = df.groupby(["activity", "rating_label"]).size().reset_index(name="Count")
    if not act_df.empty:
        fig_act = px.bar(
            act_df, x="Count", y="activity", orientation="h", color="rating_label",
            color_discrete_map={"Sometimes (s)": "#FCD34D", "Excessive / often (e)": "#EF4444"},
            title="Behaviour by Class / Activity",
            labels={"activity": "", "rating_label": "Rating"},
            barmode="stack",
        )
        fig_act.update_layout(height=360, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_act, use_container_width=True)

    df_time = df[df["time"].str.strip() != ""].copy()
    if not df_time.empty:
        try:
            df_time["hour"] = df_time["time"].str.split(":").str[0].astype(int)
            hour_df = df_time.groupby(["hour", "rating_label"]).size().reset_index(name="Count")
            hour_df["Time"] = hour_df["hour"].apply(lambda h: f"{h}:00")
            st.markdown("### 🕐 Time-of-Day Pattern")
            fig_time = px.bar(
                hour_df.sort_values("hour"), x="Time", y="Count", color="rating_label",
                color_discrete_map={"Sometimes (s)": "#FCD34D", "Excessive / often (e)": "#EF4444"},
                title="Behaviour by Hour of Day", barmode="stack",
            )
            fig_time.update_layout(height=300, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_time, use_container_width=True)
        except Exception:
            pass

    st.markdown("### 💡 Pattern Insights")
    insights = []

    if n_excessive > 0:
        grp_exc = df.groupby("grouping_label")["is_excessive"].agg(["sum", "count"])
        grp_exc["rate"] = grp_exc["sum"] / grp_exc["count"]
        worst_grp  = grp_exc["rate"].idxmax()
        worst_rate = round(100 * grp_exc.loc[worst_grp, "rate"])
        insights.append(("warn",
            f"⚠️ <b>{worst_grp}</b> grouping has the highest rate of excessive behaviour "
            f"({worst_rate}% of observations rated 'e'). Consider whether this grouping "
            "arrangement meets this student's regulatory needs."))

    if "Unstructured" in df["grouping_label"].values:
        n_u  = len(df[df["grouping_label"] == "Unstructured"])
        n_ue = int(df[df["grouping_label"] == "Unstructured"]["is_excessive"].sum())
        if n_ue > 0:
            insights.append(("warn",
                f"🔔 Unstructured time produced excessive behaviour in {n_ue}/{n_u} observations. "
                "Consider structured alternatives or closer supervision during these intervals."))

    if not df_tasks.empty:
        t_pure_e = task_e_rate[task_e_rate["% excessive"] == "100%"]["Task Type"].tolist()
        t_pure_e = [t for t in t_pure_e if t != "(not recorded)"]
        if t_pure_e:
            insights.append(("warn",
                f"🔴 Task types <b>{', '.join(t_pure_e)}</b> have all observations rated excessive. "
                "Review demand level, sensory factors, or environment for these tasks."))

    if n_excessive > 0:
        no_e_groups = [
            g for g in GROUPING_LABELS.values()
            if g in df["grouping_label"].values
            and int(df[df["grouping_label"] == g]["is_excessive"].sum()) == 0
        ]
        if no_e_groups:
            insights.append(("ok",
                f"✅ No excessive behaviour observed during <b>{', '.join(no_e_groups)}</b>. "
                "These arrangements appear to support positive engagement for this student."))

    if pct_excess < 25 and n_total >= 4:
        insights.append(("ok",
            "📉 The majority of observations are rated 'sometimes' rather than 'excessive'. "
            "Current support strategies appear to be containing the behaviour effectively."))

    if not insights:
        insights.append(("warn",
            "📊 Add more observations across different contexts to enable meaningful pattern analysis."))

    for kind, text in insights:
        css = "insight" if kind == "warn" else "insight insight-ok"
        st.markdown(f"<div class='{css}'>{text}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.caption("💾 Save the session in the Entry Form tab to persist this record to Supabase.")
