# ════════════════════════════════════════════════════════════════════════════
# 19_Student_Schedule_Analysis.py  ·  CLC-LBU Portal
# Schedule Analysis — fast in-the-moment observation entry
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from auth import require_auth, logout_button, get_staff_name
require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
logout_button()

TEAL  = "#1A6B8A"
AMBER = "#D4860A"

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:#f5f8fa; }}
.clc-header {{
    background:linear-gradient(135deg,{TEAL} 0%,{TEAL}BB 100%);
    color:white; padding:.85rem 1.5rem; border-radius:10px; margin-bottom:1rem;
}}
.clc-header h2 {{ margin:0; font-size:1.25rem; }}
.clc-header p  {{ margin:.2rem 0 0; opacity:.85; font-size:.78rem; }}
.kpi {{ background:white; border-left:4px solid {TEAL}; border-radius:6px;
        padding:.45rem .75rem; text-align:center; }}
.kpi .val {{ font-size:1.5rem; font-weight:700; color:{TEAL}; line-height:1.1; }}
.kpi .lbl {{ font-size:.68rem; color:#666; }}
.kpi-a {{ border-color:{AMBER}; }}
.kpi-a .val {{ color:{AMBER}; }}
.obs-row {{
    background:white; border:1px solid #e2e8f0; border-radius:8px;
    padding:.5rem .75rem; margin-bottom:.35rem;
    display:flex; align-items:center; gap:.5rem; font-size:.82rem;
}}
.badge-s {{ background:#FEF3C7;color:#92400E;border-radius:4px;
            padding:.15rem .5rem;font-weight:700;font-size:.75rem; }}
.badge-e {{ background:#FEE2E2;color:#991B1B;border-radius:4px;
            padding:.15rem .5rem;font-weight:700;font-size:.75rem; }}
.insight {{ background:#FEF9EC; border-left:4px solid {AMBER};
            border-radius:6px; padding:.5rem .9rem; font-size:.83rem; margin-bottom:.35rem; }}
.insight-ok {{ background:#F0FAF4; border-left:4px solid #2EA056; }}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
GROUPINGS = ["i","1:1","sg","wg","U","P"]
GROUPING_LABELS = {
    "i":"Independent","1:1":"One-to-one","sg":"Small group",
    "wg":"Whole group","U":"Unstructured","P":"Peer",
}
TASK_TYPES = ["Paper/pencil","Oral/listening","Hands on","Play based","Class routine","Computer"]
RATING_LABELS = {"s":"Sometimes (s)","e":"Excessive / often (e)"}


# ── Supabase ──────────────────────────────────────────────────────────────────
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


@st.cache_data(ttl=60)
def load_students_cached():
    sb = get_sb()
    if not sb:
        return []
    try:
        res = sb.table("students").select("id,name,program").eq("archived",False).order("name").execute()
        return res.data or []
    except Exception:
        return []


def load_obs(student_id: str) -> pd.DataFrame:
    sb = get_sb()
    if not sb:
        return pd.DataFrame()
    try:
        res = (sb.table("schedule_analysis_observations")
               .select("*")
               .eq("student_id", student_id)
               .order("obs_date").order("obs_time")
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty and "task_types" in df.columns:
            df["task_types"] = df["task_types"].apply(lambda x: x if isinstance(x,list) else [])
        return df
    except Exception as e:
        st.error(f"Load error: {e}")
        return pd.DataFrame()


def save_obs(row: dict) -> bool:
    sb = get_sb()
    if not sb:
        st.warning("Supabase not configured.")
        return False
    try:
        sb.table("schedule_analysis_observations").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False


def delete_obs(obs_id: str) -> bool:
    sb = get_sb()
    if not sb:
        return False
    try:
        sb.table("schedule_analysis_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception:
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
  <p>Log observations by grouping, task type and time for functional pattern analysis
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STUDENT SELECTOR
# ════════════════════════════════════════════════════════════════════════════
students     = load_students_cached()
if not students:
    st.warning("No students found. Add students via the Behaviour Support tool first.")
    st.stop()

student_opts = {s["id"]: f"{s['name']}  ({s.get('program','')})" for s in students}
ids     = list(student_opts.keys())
cur_idx = ids.index(st.session_state.saa_student_id) if st.session_state.saa_student_id in ids else 0

hc1, hc2 = st.columns([2, 3])
with hc1:
    selected_id = st.selectbox(
        "Student", ids, index=cur_idx,
        format_func=lambda x: student_opts[x],
        key="saa_stu_sel"
    )
with hc2:
    st.session_state.saa_behaviours = st.text_input(
        "Target behaviour(s)",
        value=st.session_state.saa_behaviours,
        placeholder="e.g. Roaming instead of participating in learning",
        key="saa_beh_input"
    )

if selected_id != st.session_state.saa_student_id:
    st.session_state.saa_student_id   = selected_id
    st.session_state.saa_student_name = next((s["name"] for s in students if s["id"]==selected_id),"")
    st.rerun()

student_id   = st.session_state.saa_student_id
student_name = st.session_state.saa_student_name or student_opts.get(student_id,"")
obs_df       = load_obs(student_id)

st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis & Download"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — RECORD & VIEW
# ════════════════════════════════════════════════════════════════════════════
with t_record:

    # ── Legend ────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#EBF4F9;border-left:4px solid #1A6B8A;border-radius:6px;'
        'padding:.4rem .9rem;margin-bottom:.75rem;font-size:.8rem;">'
        '<b>Rating:</b> &nbsp;'
        '<span class="badge-s">s</span> sometimes &nbsp;|&nbsp;'
        '<span class="badge-e">e</span> excessive / often'
        '&nbsp;&nbsp;&nbsp;<b>Grouping:</b> &nbsp;'
        '<b>i</b> independent &nbsp;<b>1:1</b> one-to-one &nbsp;'
        '<b>sg</b> small group &nbsp;<b>wg</b> whole group &nbsp;'
        '<b>U</b> unstructured &nbsp;<b>P</b> peer'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Quick entry form ──────────────────────────────────────────────────
    st.markdown(f"**➕ Add observation for {student_name}**")

    with st.form("saa_quick_form", clear_on_submit=True):
        # Row 1: date / time / activity
        rc1, rc2, rc3 = st.columns([1.5, 1, 3])
        with rc1: obs_date = st.date_input("Date *", value=date.today())
        with rc2: obs_time = st.text_input("Time", placeholder="9:30")
        with rc3: activity = st.text_input("Class / Activity *", placeholder="e.g. Maths — independent task")

        # Row 2: rating / grouping / tasks — large, obvious buttons
        rc4, rc5, rc6 = st.columns([1.5, 2, 3])
        with rc4:
            rating = st.radio(
                "Rating *",
                ["s","e"],
                format_func=lambda x: RATING_LABELS[x],
                horizontal=False,
                key="saa_rating_radio"
            )
        with rc5:
            grouping = st.radio(
                "Grouping *",
                GROUPINGS,
                format_func=lambda x: f"{x} — {GROUPING_LABELS[x]}",
                horizontal=False,
                key="saa_grp_radio"
            )
        with rc6:
            task_types = st.multiselect("Task type(s)", TASK_TYPES)
            notes      = st.text_input("Notes", placeholder="Optional context")

        submitted = st.form_submit_button(
            "💾 Save Observation", type="primary", use_container_width=True
        )

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
            if save_obs(row):
                badge = "badge-e" if rating=="e" else "badge-s"
                st.success(
                    f"✅ Saved — {obs_date.strftime('%-d %b')} · {activity.strip()} · "
                    f"{RATING_LABELS[rating]} · {GROUPING_LABELS[grouping]}"
                )
                st.rerun()

    # ── Recent observations ───────────────────────────────────────────────
    st.markdown("---")
    if obs_df.empty:
        st.info("No observations recorded yet for this student.")
    else:
        # Date filter for view
        obs_df["obs_date_dt"] = pd.to_datetime(obs_df["obs_date"])
        max_d = obs_df["obs_date_dt"].max().date()
        min_d = obs_df["obs_date_dt"].min().date()

        # Default: show last 14 days
        default_from = max(min_d, max_d - timedelta(days=13))

        vc1, vc2, vc3 = st.columns([2, 2, 2])
        with vc1:
            view_from = st.date_input("Show from", value=default_from, key="saa_vf",
                                      min_value=min_d, max_value=max_d)
        with vc2:
            view_to   = st.date_input("Show to",   value=max_d, key="saa_vt",
                                      min_value=min_d, max_value=max_d)
        with vc3:
            st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
            if st.button("🔄 Refresh", use_container_width=True, key="saa_refresh"):
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        view_df = obs_df[
            (obs_df["obs_date_dt"].dt.date >= view_from) &
            (obs_df["obs_date_dt"].dt.date <= view_to)
        ].sort_values("obs_date_dt", ascending=False)

        if view_df.empty:
            st.info("No observations in this date range.")
        else:
            st.markdown(f"**{len(view_df)} observations — {view_from.strftime('%-d %b')} to {view_to.strftime('%-d %b %Y')}**")

            # Quick counts
            n_e = (view_df["rating"]=="e").sum()
            n_s = (view_df["rating"]=="s").sum()
            mc1, mc2, mc3 = st.columns(3)
            mc1.markdown(f"<div class='kpi'><div class='val'>{len(view_df)}</div><div class='lbl'>Total</div></div>", unsafe_allow_html=True)
            mc2.markdown(f"<div class='kpi'><div class='val'>{n_s}</div><div class='lbl'>Sometimes (s)</div></div>", unsafe_allow_html=True)
            mc3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n_e}</div><div class='lbl'>Excessive (e)</div></div>", unsafe_allow_html=True)

            st.markdown("")

            # List of observations
            for _, row in view_df.iterrows():
                r      = row.get("rating","")
                badge  = "badge-e" if r=="e" else "badge-s"
                d_str  = row["obs_date_dt"].strftime("%-d %b")
                t_str  = row.get("obs_time","") or ""
                act    = row.get("class_activity","") or ""
                grp    = GROUPING_LABELS.get(row.get("grouping",""), row.get("grouping",""))
                tasks  = row.get("task_types",[]) or []
                task_s = ", ".join(tasks) if tasks else ""
                note   = row.get("notes","") or ""
                rid    = row.get("id","")

                col1, col2 = st.columns([10, 1])
                with col1:
                    st.markdown(
                        f'<div style="background:white;border:1px solid #e2e8f0;border-radius:8px;'
                        f'padding:.45rem .75rem;margin-bottom:.25rem;">'
                        f'<span class="{badge}">{RATING_LABELS.get(r,r)}</span> &nbsp;'
                        f'<b>{d_str}</b>{(" " + t_str) if t_str else ""}'
                        f' &nbsp;—&nbsp; {act}'
                        f' &nbsp;<span style="color:{TEAL};font-size:.78rem;">{grp}</span>'
                        + (f'&nbsp;<span style="color:#888;font-size:.75rem;">· {task_s}</span>' if task_s else "")
                        + (f'&nbsp;<span style="color:#aaa;font-size:.73rem;">· {note}</span>' if note else "")
                        + '</div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    if st.button("🗑️", key=f"del_saa_{rid}", help="Delete"):
                        if delete_obs(rid):
                            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYSIS & DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:
    st.markdown(f"#### {student_name} — Analysis")

    if obs_df.empty:
        st.info("No observations recorded yet.")
        st.stop()

    obs_df["obs_date_dt"] = pd.to_datetime(obs_df["obs_date"])

    fc1, fc2 = st.columns(2)
    with fc1:
        date_from = st.date_input("From", value=obs_df["obs_date_dt"].min().date(), key="saa_from")
    with fc2:
        date_to   = st.date_input("To",   value=obs_df["obs_date_dt"].max().date(), key="saa_to")

    filt = obs_df[
        (obs_df["obs_date_dt"].dt.date >= date_from) &
        (obs_df["obs_date_dt"].dt.date <= date_to)
    ].copy()

    if filt.empty:
        st.info("No observations in this date range.")
        st.stop()

    filt["is_e"] = filt["rating"] == "e"
    filt["rating_label"]   = filt["rating"].map(RATING_LABELS)
    filt["grouping_label"] = filt["grouping"].map(GROUPING_LABELS).fillna(filt["grouping"])

    total = len(filt)
    n_e   = int(filt["is_e"].sum())
    pct_e = round(100*n_e/total) if total else 0

    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><div class='val'>{total}</div><div class='lbl'>Total observations</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi kpi-a'><div class='val'>{n_e}</div><div class='lbl'>Excessive (e)</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><div class='val'>{pct_e}%</div><div class='lbl'>% excessive</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    col_a, col_b = st.columns(2)

    # Chart 1: Rating breakdown
    with col_a:
        rc = filt["rating_label"].value_counts().reset_index()
        rc.columns = ["Rating","Count"]
        fig1 = px.pie(rc, values="Count", names="Rating",
            color="Rating",
            color_discrete_map={"Sometimes (s)":"#FCD34D","Excessive / often (e)":"#EF4444"},
            title="Rating Breakdown", hole=0.4)
        fig1.update_layout(height=290, margin=dict(l=10,r=10,t=50,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: By grouping
    with col_b:
        gd = filt.groupby(["grouping_label","rating_label"]).size().reset_index(name="Count")
        fig2 = px.bar(gd, x="grouping_label", y="Count", color="rating_label",
            color_discrete_map={"Sometimes (s)":"#FCD34D","Excessive / often (e)":"#EF4444"},
            title="Rating by Grouping",
            labels={"grouping_label":"","rating_label":"Rating"}, barmode="stack")
        fig2.update_layout(height=290, margin=dict(l=10,r=10,t=50,b=10),
                           yaxis=dict(tickformat="d"))
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: By activity
    act_df = filt.groupby(["class_activity","rating_label"]).size().reset_index(name="Count")
    if not act_df.empty:
        fig3 = px.bar(act_df, x="Count", y="class_activity", orientation="h",
            color="rating_label",
            color_discrete_map={"Sometimes (s)":"#FCD34D","Excessive / often (e)":"#EF4444"},
            title="Behaviour by Activity",
            labels={"class_activity":"","rating_label":"Rating"}, barmode="stack")
        fig3.update_layout(
            height=max(280, len(act_df["class_activity"].unique())*28),
            margin=dict(l=10,r=10,t=50,b=10), xaxis=dict(tickformat="d"))
        st.plotly_chart(fig3, use_container_width=True)

    # Chart 4: Task type
    task_rows = []
    for _, row in filt.iterrows():
        tasks = row.get("task_types",[]) or []
        if not tasks: tasks = ["(not recorded)"]
        for task in tasks:
            task_rows.append({"Task Type":task,"Rating":row["rating_label"],"is_e":row["is_e"]})
    if task_rows:
        df_tasks = pd.DataFrame(task_rows)
        tc = df_tasks.groupby(["Task Type","Rating"]).size().reset_index(name="Count")
        fig4 = px.bar(tc, x="Task Type", y="Count", color="Rating",
            color_discrete_map={"Sometimes (s)":"#FCD34D","Excessive / often (e)":"#EF4444"},
            title="Behaviour by Task Type", barmode="stack")
        fig4.update_layout(height=300, margin=dict(l=10,r=10,t=50,b=10),
                           yaxis=dict(tickformat="d"))
        st.plotly_chart(fig4, use_container_width=True)

    # Insights
    st.markdown("### 💡 Pattern Insights")
    insights = []
    if n_e > 0:
        ge = filt.groupby("grouping_label")["is_e"].agg(["sum","count"])
        ge["rate"] = ge["sum"]/ge["count"]
        worst = ge["rate"].idxmax()
        insights.append(("warn",
            f"⚠️ <b>{worst}</b> grouping has the highest rate of excessive behaviour "
            f"({round(ge.loc[worst,'rate']*100)}%). Consider whether this arrangement "
            "meets this student's regulatory needs."))

    no_e = [g for g in GROUPING_LABELS.values()
            if g in filt["grouping_label"].values
            and int(filt[filt["grouping_label"]==g]["is_e"].sum())==0]
    if no_e and n_e > 0:
        insights.append(("ok",
            f"✅ No excessive behaviour in <b>{', '.join(no_e)}</b>. "
            "These arrangements support positive engagement for this student."))

    if pct_e < 25 and total >= 4:
        insights.append(("ok",
            "📉 Most observations are 'sometimes' rather than 'excessive'. "
            "Current strategies appear to be containing the behaviour effectively."))

    if not insights:
        insights.append(("warn","📊 Add more observations across contexts for meaningful pattern analysis."))

    for kind, text in insights:
        css = "insight" if kind=="warn" else "insight insight-ok"
        st.markdown(f"<div class='{css}'>{text}</div>", unsafe_allow_html=True)

    # Download
    st.markdown("---")
    dl = filt.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    dl["task_types"] = dl["task_types"].apply(lambda x: ", ".join(x) if isinstance(x,list) else "")
    csv = dl[["obs_date","obs_time","class_activity","rating","grouping",
              "task_types","notes","target_behaviours","created_by","created_at"]].to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        csv,
        file_name=f"ScheduleAnalysis_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv", use_container_width=True,
    )
