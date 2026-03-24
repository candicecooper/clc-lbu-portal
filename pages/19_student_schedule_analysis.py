# ════════════════════════════════════════════════════════════════════════════
# 19_Student_Schedule_Analysis.py  ·  CLC-LBU Portal
# Schedule Analysis — form-based per-observation entry
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from auth import require_auth, logout_button, get_staff_name
require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
logout_button()

TEAL  = "#1A6B8A"
AMBER = "#D4860A"

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:#f5f8fa; }}
.clc-header {{
    background: linear-gradient(135deg, {TEAL} 0%, {TEAL}BB 100%);
    color: white; padding: 1rem 1.5rem; border-radius: 10px; margin-bottom: 1.25rem;
}}
.clc-header h2 {{ margin:0; font-size:1.35rem; }}
.clc-header p  {{ margin:.2rem 0 0; opacity:.85; font-size:.82rem; }}
.kpi {{
    background: white; border-left: 4px solid {TEAL}; border-radius: 6px;
    padding: .55rem .9rem; box-shadow: 0 1px 4px rgba(0,0,0,.08);
    text-align: center; margin-bottom: .5rem;
}}
.kpi .val {{ font-size:1.7rem; font-weight:700; color:{TEAL}; line-height:1.1; }}
.kpi .lbl {{ font-size:.72rem; color:#666; margin-top:.15rem; }}
.kpi-amber {{ border-color:{AMBER}; }}
.kpi-amber .val {{ color:{AMBER}; }}
.insight {{
    background: #FEF9EC; border: 1px solid {AMBER}55;
    border-left: 4px solid {AMBER}; border-radius: 6px;
    padding: .55rem 1rem; font-size: .85rem; margin-bottom: .4rem;
}}
.insight-ok {{
    background: #F0FAF4; border: 1px solid #2EA05655;
    border-left: 4px solid #2EA056;
}}
.badge-s {{ background:#FEF3C7;color:#92400E;border-radius:4px;padding:.1rem .4rem;font-weight:600;font-size:.8rem; }}
.badge-e {{ background:#FEE2E2;color:#991B1B;border-radius:4px;padding:.1rem .4rem;font-weight:600;font-size:.8rem; }}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
GROUPINGS = ["i", "1:1", "sg", "wg", "U", "P"]
GROUPING_LABELS = {
    "i":"Independent","1:1":"One-to-one","sg":"Small group",
    "wg":"Whole group","U":"Unstructured","P":"Peer",
}
TASK_TYPES = ["Paper/pencil","Oral/listening","Hands on","Play based","Class routine","Computer"]
RATINGS    = ["s","e"]
RATING_LABELS = {"s":"Sometimes (s)","e":"Excessive / often (e)"}


# ── Supabase ──────────────────────────────────────────────────────────────────
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


@st.cache_data(ttl=30)
def load_students():
    sb = get_sb()
    if not sb:
        return []
    try:
        res = sb.table("students").select("id,name,program").eq("archived", False).order("name").execute()
        return res.data or []
    except Exception:
        return []


def load_observations(student_id: str) -> pd.DataFrame:
    sb = get_sb()
    if not sb:
        return pd.DataFrame()
    try:
        res = (sb.table("schedule_analysis_observations")
               .select("*")
               .eq("student_id", student_id)
               .order("obs_date")
               .order("obs_time")
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty and "task_types" in df.columns:
            df["task_types"] = df["task_types"].apply(
                lambda x: x if isinstance(x, list) else []
            )
        return df
    except Exception as e:
        st.error(f"Could not load observations: {e}")
        return pd.DataFrame()


def save_observation(row: dict) -> bool:
    sb = get_sb()
    if not sb:
        st.warning("Supabase not configured.")
        return False
    try:
        import json
        if isinstance(row.get("task_types"), list):
            row["task_types"] = row["task_types"]  # supabase handles jsonb lists natively
        sb.table("schedule_analysis_observations").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False


def delete_observation(obs_id: str) -> bool:
    sb = get_sb()
    if not sb:
        return False
    try:
        sb.table("schedule_analysis_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False


# ── Session state ─────────────────────────────────────────────────────────────
if "saa_student_id"   not in st.session_state: st.session_state.saa_student_id   = None
if "saa_student_name" not in st.session_state: st.session_state.saa_student_name = ""
if "saa_behaviours"   not in st.session_state: st.session_state.saa_behaviours   = ""


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="clc-header">
  <h2>🗂️ Schedule Analysis</h2>
  <p>Log behaviour observations by grouping, task type and time for functional pattern analysis
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STUDENT SELECTOR
# ════════════════════════════════════════════════════════════════════════════
students = load_students()
student_opts = {s["id"]: f"{s['name']}  ({s.get('program','')})" for s in students}

if students:
    ids     = list(student_opts.keys())
    cur_idx = ids.index(st.session_state.saa_student_id) if st.session_state.saa_student_id in ids else 0

    sc1, sc2, sc3 = st.columns([3, 2, 1])
    with sc1:
        selected_id = st.selectbox(
            "Student", ids, index=cur_idx,
            format_func=lambda x: student_opts[x],
            key="saa_sel"
        )
    with sc2:
        st.session_state.saa_behaviours = st.text_input(
            "Target behaviour(s)",
            value=st.session_state.saa_behaviours,
            placeholder="e.g. Roaming instead of participating",
            key="saa_beh_top"
        )
    with sc3:
        st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True, key="saa_refresh"):
            load_observations.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if selected_id != st.session_state.saa_student_id:
        st.session_state.saa_student_id   = selected_id
        st.session_state.saa_student_name = next((s["name"] for s in students if s["id"] == selected_id), "")
       
        st.rerun()
else:
    st.warning("No students found. Add students via the Admin section of the Behaviour Support tool.")
    st.stop()

student_id   = st.session_state.saa_student_id
student_name = st.session_state.saa_student_name or student_opts.get(student_id, "")

obs_df = load_observations(student_id)

st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
t_add, t_view, t_analysis = st.tabs([
    "➕  Record Observation",
    "📄  View & Edit Records",
    "📈  Analysis & Download",
])


# ────────────────────────────────────────────────────────────────────────────
# TAB 1 — RECORD OBSERVATION
# ────────────────────────────────────────────────────────────────────────────
with t_add:
    st.markdown(f"#### Recording for: **{student_name}**")

    st.markdown("""
    <div style='background:#EBF4F9;border-left:4px solid #1A6B8A;border-radius:6px;
    padding:.5rem 1rem;margin-bottom:1rem;font-size:.85rem;'>
    <b>Rating:</b> &nbsp;
    <span class="badge-s">s</span> = sometimes &nbsp;|&nbsp;
    <span class="badge-e">e</span> = excessive / often
    &nbsp;&nbsp;&nbsp;
    <b>Grouping:</b> &nbsp;
    <b>i</b> = independent &nbsp;
    <b>1:1</b> = one to one &nbsp;
    <b>sg</b> = small group &nbsp;
    <b>wg</b> = whole group &nbsp;
    <b>U</b> = unstructured &nbsp;
    <b>P</b> = peer
    </div>
    """, unsafe_allow_html=True)

    with st.form("saa_add_obs", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns([2, 1, 2])
        with fc1:
            obs_date   = st.date_input("Date *", value=date.today())
        with fc2:
            obs_time   = st.text_input("Time", placeholder="e.g. 9:30")
        with fc3:
            activity   = st.text_input("Class / Activity *", placeholder="e.g. Maths — independent task")

        fc4, fc5 = st.columns(2)
        with fc4:
            rating     = st.selectbox(
                "Rating *",
                RATINGS,
                format_func=lambda x: RATING_LABELS[x]
            )
        with fc5:
            grouping   = st.selectbox(
                "Grouping *",
                GROUPINGS,
                format_func=lambda x: f"{x} — {GROUPING_LABELS[x]}"
            )

        task_types = st.multiselect("Task type(s)", TASK_TYPES)
        notes      = st.text_input("Notes (optional)", placeholder="Any context")

        submitted = st.form_submit_button("💾 Save Observation", type="primary", use_container_width=True)

    if submitted:
        if not activity.strip():
            st.error("Please enter the class / activity.")
        else:
            row = {
                "student_id":        student_id,
                "student_name":      student_name,
                "obs_date":          obs_date.isoformat(),
                "obs_time":          obs_time.strip(),
                "class_activity":    activity.strip(),
                "rating":            rating,
                "grouping":          grouping,
                "task_types":        task_types,
                "target_behaviours": st.session_state.saa_behaviours,
                "notes":             notes.strip(),
                "created_by":        get_staff_name(),
            }
            if save_observation(row):
                rating_label = RATING_LABELS[rating]
                st.success(
                    f"✅ Saved — {obs_date.strftime('%-d %b')} · {activity.strip()} · "
                    f"**{rating_label}** · {GROUPING_LABELS[grouping]}"
                )
                
                st.rerun()

    # ── Recent observations ───────────────────────────────────────────────
    if not obs_df.empty:
        st.markdown("---")
        st.markdown("#### Recent observations")
        recent = obs_df.sort_values("created_at", ascending=False).head(15)
        for _, row in recent.iterrows():
            r   = row.get("rating","")
            cls = "badge-e" if r == "e" else "badge-s"
            d_str = pd.to_datetime(row["obs_date"]).strftime("%-d %b")
            act   = row.get("class_activity","") or ""
            grp   = GROUPING_LABELS.get(row.get("grouping",""), row.get("grouping",""))
            tasks = row.get("task_types",[]) or []
            task_str = ", ".join(tasks) if tasks else ""
            note  = row.get("notes","") or ""
            rid   = row.get("id","")
            rc1, rc2 = st.columns([9, 1])
            with rc1:
                st.markdown(
                    f'<span class="{cls}">{RATING_LABELS.get(r,r)}</span> '
                    f'<b>{d_str}</b>'
                    + (f' {row.get("obs_time","")}' if row.get("obs_time") else '')
                    + f' — {act}'
                    + f' <span style="color:{TEAL};font-size:.8rem;">· {grp}</span>'
                    + (f' <span style="color:#888;font-size:.78rem;">· {task_str}</span>' if task_str else '')
                    + (f' <span style="color:#888;font-size:.78rem;">· {note}</span>' if note else ''),
                    unsafe_allow_html=True
                )
            with rc2:
                if st.button("🗑️", key=f"del_saa_{rid}", help="Delete"):
                    if delete_observation(rid):
                        
                        st.rerun()


# ────────────────────────────────────────────────────────────────────────────
# TAB 2 — VIEW & EDIT RECORDS
# ────────────────────────────────────────────────────────────────────────────
with t_view:
    st.markdown(f"#### {student_name} — All Observations")

    if obs_df.empty:
        st.info("No observations yet.")
    else:
        obs_df["obs_date"] = pd.to_datetime(obs_df["obs_date"])

        # Date filter
        vc1, vc2 = st.columns(2)
        with vc1:
            v_from = st.date_input("From", value=obs_df["obs_date"].min().date(), key="saa_v_from")
        with vc2:
            v_to   = st.date_input("To",   value=obs_df["obs_date"].max().date(), key="saa_v_to")

        view_df = obs_df[
            (obs_df["obs_date"].dt.date >= v_from) &
            (obs_df["obs_date"].dt.date <= v_to)
        ].copy()

        if view_df.empty:
            st.info("No observations in this range.")
        else:
            view_df["Date"]           = view_df["obs_date"].dt.strftime("%-d/%m/%Y")
            view_df["Time"]           = view_df.get("obs_time","")
            view_df["Activity"]       = view_df.get("class_activity","")
            view_df["Rating"]         = view_df["rating"].map(RATING_LABELS).fillna(view_df["rating"])
            view_df["Grouping"]       = view_df["grouping"].map(GROUPING_LABELS).fillna(view_df["grouping"])
            view_df["Task Types"]     = view_df["task_types"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else ""
            )
            view_df["Notes"]          = view_df.get("notes","")

            display_cols = ["Date","Time","Activity","Rating","Grouping","Task Types","Notes"]
            st.dataframe(
                view_df[display_cols],
                use_container_width=True, hide_index=True
            )
            st.caption(f"{len(view_df)} observations in range")


# ────────────────────────────────────────────────────────────────────────────
# TAB 3 — ANALYSIS & DOWNLOAD
# ────────────────────────────────────────────────────────────────────────────
with t_analysis:
    st.markdown(f"#### {student_name} — Analysis")

    if obs_df.empty:
        st.info("No observations recorded yet.")
        st.stop()

    obs_df["obs_date"] = pd.to_datetime(obs_df["obs_date"])

    fc1, fc2 = st.columns(2)
    with fc1:
        date_from = st.date_input("From", value=obs_df["obs_date"].min().date(), key="saa_from")
    with fc2:
        date_to   = st.date_input("To",   value=obs_df["obs_date"].max().date(), key="saa_to")

    filtered = obs_df[
        (obs_df["obs_date"].dt.date >= date_from) &
        (obs_df["obs_date"].dt.date <= date_to)
    ].copy()

    if filtered.empty:
        st.info("No observations in this date range.")
        st.stop()

    filtered["is_e"] = filtered["rating"] == "e"
    filtered["rating_label"] = filtered["rating"].map(RATING_LABELS)
    filtered["grouping_label"] = filtered["grouping"].map(GROUPING_LABELS).fillna(filtered["grouping"])

    total      = len(filtered)
    n_e        = int(filtered["is_e"].sum())
    n_s        = total - n_e
    pct_e      = round(100 * n_e / total) if total else 0

    # ── KPIs ─────────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><div class='val'>{total}</div><div class='lbl'>Total observations</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi kpi-amber'><div class='val'>{n_e}</div><div class='lbl'>Excessive / often (e)</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><div class='val'>{pct_e}%</div><div class='lbl'>% rated excessive</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Chart 1: Rating breakdown ─────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        rating_counts = filtered["rating_label"].value_counts().reset_index()
        rating_counts.columns = ["Rating","Count"]
        fig1 = px.pie(
            rating_counts, values="Count", names="Rating",
            color="Rating",
            color_discrete_map={
                "Sometimes (s)":"#FCD34D",
                "Excessive / often (e)":"#EF4444",
            },
            title="Rating Breakdown", hole=0.4,
        )
        fig1.update_layout(height=300, margin=dict(l=10,r=10,t=50,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        grp_df = (filtered.groupby(["grouping_label","rating_label"])
                  .size().reset_index(name="Count"))
        fig2 = px.bar(
            grp_df, x="grouping_label", y="Count", color="rating_label",
            color_discrete_map={
                "Sometimes (s)":"#FCD34D",
                "Excessive / often (e)":"#EF4444",
            },
            title="Rating by Grouping",
            labels={"grouping_label":"Grouping","rating_label":"Rating"},
            barmode="stack",
        )
        fig2.update_layout(height=300, margin=dict(l=10,r=10,t=50,b=10),
                           yaxis=dict(tickformat="d"))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Chart 2: Task type analysis ───────────────────────────────────────
    task_rows = []
    for _, row in filtered.iterrows():
        tasks = row.get("task_types",[]) or []
        if not tasks:
            tasks = ["(not recorded)"]
        for task in tasks:
            task_rows.append({
                "Task Type": task,
                "Rating":    row["rating_label"],
                "is_e":      row["is_e"],
            })
    if task_rows:
        df_tasks = pd.DataFrame(task_rows)
        task_counts = (df_tasks.groupby(["Task Type","Rating"])
                       .size().reset_index(name="Count"))
        fig3 = px.bar(
            task_counts, x="Task Type", y="Count", color="Rating",
            color_discrete_map={
                "Sometimes (s)":"#FCD34D",
                "Excessive / often (e)":"#EF4444",
            },
            title="Behaviour Frequency by Task Type", barmode="stack",
        )
        fig3.update_layout(height=320, margin=dict(l=10,r=10,t=50,b=10),
                           yaxis=dict(tickformat="d"))
        st.plotly_chart(fig3, use_container_width=True)

    # ── Chart 3: Activity ────────────────────────────────────────────────
    act_df = (filtered.groupby(["class_activity","rating_label"])
              .size().reset_index(name="Count"))
    if not act_df.empty:
        fig4 = px.bar(
            act_df, x="Count", y="class_activity", orientation="h",
            color="rating_label",
            color_discrete_map={
                "Sometimes (s)":"#FCD34D",
                "Excessive / often (e)":"#EF4444",
            },
            title="Behaviour by Activity", barmode="stack",
            labels={"class_activity":"","rating_label":"Rating"},
        )
        fig4.update_layout(
            height=max(280, len(act_df["class_activity"].unique())*30),
            margin=dict(l=10,r=10,t=50,b=10),
            xaxis=dict(tickformat="d"),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Daily trend ───────────────────────────────────────────────────────
    daily = (filtered.groupby(filtered["obs_date"].dt.date)["is_e"]
             .agg(["sum","count"]).reset_index())
    daily.columns = ["date","excessive","total"]
    daily["not_excessive"] = daily["total"] - daily["excessive"]
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        x=daily["date"].astype(str), y=daily["not_excessive"],
        name="Sometimes (s)", marker_color="#FCD34D",
    ))
    fig5.add_trace(go.Bar(
        x=daily["date"].astype(str), y=daily["excessive"],
        name="Excessive (e)", marker_color="#EF4444",
    ))
    fig5.update_layout(
        barmode="stack", title="Daily Observation Volume",
        height=280, margin=dict(l=10,r=10,t=50,b=10),
        yaxis=dict(tickformat="d"),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig5, use_container_width=True)

    # ── Pattern insights ──────────────────────────────────────────────────
    st.markdown("### 💡 Pattern Insights")
    insights = []

    if n_e > 0:
        grp_exc = filtered.groupby("grouping_label")["is_e"].agg(["sum","count"])
        grp_exc["rate"] = grp_exc["sum"] / grp_exc["count"]
        worst = grp_exc["rate"].idxmax()
        worst_rate = round(100 * grp_exc.loc[worst,"rate"])
        insights.append(("warn",
            f"⚠️ <b>{worst}</b> grouping has the highest rate of excessive behaviour "
            f"({worst_rate}%). Consider whether this arrangement meets this student's regulatory needs."))

    if "Unstructured" in filtered["grouping_label"].values:
        n_u  = (filtered["grouping_label"]=="Unstructured").sum()
        n_ue = filtered[filtered["grouping_label"]=="Unstructured"]["is_e"].sum()
        if n_ue > 0:
            insights.append(("warn",
                f"🔔 Unstructured time produced excessive behaviour in {n_ue}/{n_u} observations. "
                "Consider structured alternatives or closer supervision."))

    no_e_groups = [
        g for g in GROUPING_LABELS.values()
        if g in filtered["grouping_label"].values
        and int(filtered[filtered["grouping_label"]==g]["is_e"].sum()) == 0
    ]
    if no_e_groups and n_e > 0:
        insights.append(("ok",
            f"✅ No excessive behaviour in <b>{', '.join(no_e_groups)}</b>. "
            "These arrangements appear to support positive engagement."))

    if pct_e < 25 and total >= 4:
        insights.append(("ok",
            "📉 Most observations are 'sometimes' not 'excessive'. "
            "Current strategies appear to be containing the behaviour effectively."))

    if not insights:
        insights.append(("warn",
            "📊 Add more observations across different contexts for meaningful pattern analysis."))

    for kind, text in insights:
        css = "insight" if kind == "warn" else "insight insight-ok"
        st.markdown(f"<div class='{css}'>{text}</div>", unsafe_allow_html=True)

    # ── Download ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Download Data")
    dl_cols = ["obs_date","obs_time","class_activity","rating","grouping",
               "task_types","notes","target_behaviours","created_by","created_at"]
    dl_df   = filtered[[c for c in dl_cols if c in filtered.columns]].copy()
    dl_df["obs_date"]   = dl_df["obs_date"].dt.strftime("%-d/%m/%Y")
    dl_df["task_types"] = dl_df["task_types"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else ""
    )
    csv = dl_df.to_csv(index=False)
    st.download_button(
        "📥 Download as CSV",
        csv,
        file_name=f"ScheduleAnalysis_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.dataframe(dl_df, use_container_width=True, hide_index=True)
