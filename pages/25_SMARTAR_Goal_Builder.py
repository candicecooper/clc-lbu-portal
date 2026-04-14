# ════════════════════════════════════════════════════════════════════════════
# 21_Instruction_Goal_Tracker.py  ·  CLC-LBU Portal
# Trial-by-trial data on specific target instructions — SMARTAR goal monitoring
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

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f5f8fa; }
.clc-header {
    background:linear-gradient(135deg,#1A6B8A 0%,#1A6B8ABB 100%);
    color:white; padding:.85rem 1.5rem; border-radius:10px; margin-bottom:1rem;
}
.clc-header h2 { margin:0; font-size:1.25rem; }
.clc-header p  { margin:.2rem 0 0; opacity:.85; font-size:.78rem; }
.goal-card {
    background:white; border:1.5px solid #e2e8f0; border-radius:10px;
    padding:.65rem 1rem; margin-bottom:.4rem;
}
.goal-card.active { border-color:#1A6B8A; }
.kpi { background:white; border-left:4px solid #1A6B8A; border-radius:6px;
       padding:.4rem .7rem; text-align:center; }
.kpi .val { font-size:1.35rem; font-weight:700; color:#1A6B8A; }
.kpi .lbl { font-size:.67rem; color:#666; }
.kpi-g { border-color:#16a34a; } .kpi-g .val { color:#16a34a; }
.kpi-a { border-color:#d97706; } .kpi-a .val { color:#d97706; }
.trial-row {
    background:white; border:1px solid #e2e8f0; border-radius:8px;
    padding:.4rem .75rem; margin-bottom:.25rem; font-size:.82rem;
}
</style>
""", unsafe_allow_html=True)

RESPONSE_OPTS = {
    "independent":  {"label":"✅ Independent",      "short":"Ind",  "colour":"#16a34a","score":1},
    "prompt_1":     {"label":"🟡 1 prompt",          "short":"P1",   "colour":"#ca8a04","score":0.5},
    "prompt_2":     {"label":"🟠 2 prompts",         "short":"P2",   "colour":"#d97706","score":0.25},
    "prompt_3plus": {"label":"🔴 3+ prompts",        "short":"P3+",  "colour":"#dc2626","score":0},
    "refused":      {"label":"❌ Refused",           "short":"Ref",  "colour":"#7f1d1d","score":0},
}


def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


def load_known_students():
    sb = get_sb()
    if not sb: return []
    try:
        res = sb.table("scatter_plot_observations").select("student_name").execute()
        names = sorted({r["student_name"] for r in (res.data or []) if r.get("student_name","").strip()})
        return names
    except Exception:
        return []


def load_goals(student_name):
    sb = get_sb()
    if not sb: return []
    try:
        res = (sb.table("instruction_goals")
               .select("*").eq("student_name", student_name)
               .order("created_at", desc=False).execute())
        return res.data or []
    except Exception:
        return []


def create_goal(student_name, instruction, target_pct, target_trials):
    sb = get_sb()
    if not sb: return None
    try:
        res = sb.table("instruction_goals").insert({
            "student_name":  student_name,
            "instruction":   instruction,
            "target_pct":    target_pct,
            "target_trials": target_trials,
            "active":        True,
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error("Could not save goal: " + str(e))
        return None


def archive_goal(goal_id):
    sb = get_sb()
    if not sb: return
    try:
        sb.table("instruction_goals").update({"active": False}).eq("id", goal_id).execute()
    except Exception:
        pass


def delete_goal(goal_id):
    sb = get_sb()
    if not sb: return
    try:
        sb.table("instruction_trials").delete().eq("goal_id", goal_id).execute()
        sb.table("instruction_goals").delete().eq("id", goal_id).execute()
    except Exception as e:
        st.error("Delete failed: " + str(e))


def load_trials(goal_id):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("instruction_trials")
               .select("*").eq("goal_id", goal_id)
               .order("obs_date").order("created_at").execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
        return df
    except Exception:
        return pd.DataFrame()


def add_trial(student_name, goal_id, obs_date, time_slot, response, context):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("instruction_trials").insert({
            "student_name": student_name,
            "goal_id":      goal_id,
            "obs_date":     obs_date.isoformat(),
            "time_slot":    time_slot,
            "response":     response,
            "context":      context,
            "created_by":   get_staff_name(),
        }).execute()
        return True
    except Exception as e:
        st.error("Save failed: " + str(e))
        return False


def delete_trial(trial_id):
    sb = get_sb()
    if not sb: return
    try:
        sb.table("instruction_trials").delete().eq("id", trial_id).execute()
    except Exception:
        pass


# ── Session state ─────────────────────────────────────────────────────────────
ss = st.session_state
for k, v in [
    ("igt_name", ""),
    ("igt_goal_id", None),
]:
    if k not in ss: ss[k] = v


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="clc-header">
  <h2>🎯 Instruction Goal Tracker</h2>
  <p>Trial-by-trial data on target instructions — SMARTAR goal monitoring
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STUDENT SELECTOR
# ════════════════════════════════════════════════════════════════════════════
known = load_known_students()
sc1, sc2 = st.columns([3,1])
with sc1:
    if known:
        name_opts = ["— type name below —"] + known
        sel_opt = st.selectbox("Select student", name_opts, key="igt_sel_opt")
        if sel_opt != "— type name below —" and sel_opt != ss.igt_name:
            ss.igt_name = sel_opt
            ss.igt_goal_id = None
            st.rerun()
with sc2:
    st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
    if st.button("➕ New name", key="igt_new_btn", use_container_width=True):
        ss.igt_name = ""; ss.igt_goal_id = None
    st.markdown("</div>", unsafe_allow_html=True)

if not ss.igt_name:
    new_name = st.text_input("Student name", placeholder="Type and press Enter", key="igt_name_inp")
    if new_name.strip():
        ss.igt_name = new_name.strip()
        ss.igt_goal_id = None
        st.rerun()
    st.stop()

student_name = ss.igt_name
st.markdown(f"**{student_name}**  "
            f"<span style='font-size:.78rem;color:#64748b;'>— Instruction Goal Tracker</span>",
            unsafe_allow_html=True)
if st.button("← Change student", key="igt_change"):
    ss.igt_name = ""; ss.igt_goal_id = None; st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# GOALS PANEL
# ════════════════════════════════════════════════════════════════════════════
goals = load_goals(student_name)
active_goals   = [g for g in goals if g.get("active", True)]
archived_goals = [g for g in goals if not g.get("active", True)]

# If the stored goal_id is no longer valid, clear it
if ss.igt_goal_id and not any(g["id"]==ss.igt_goal_id for g in goals):
    ss.igt_goal_id = None

# ── Add new goal ──────────────────────────────────────────────────────────
with st.expander("➕ Add a new target instruction", expanded=(not active_goals)):
    with st.form("igt_new_goal_form"):
        new_instr = st.text_area(
            "Target instruction *",
            placeholder=(
                "e.g. Sits in seat within 30 seconds of being asked\n"
                "e.g. Transitions to next activity within 2 prompts\n"
                "e.g. Follows a direct instruction from staff"
            ),
            height=80
        )
        nc1, nc2 = st.columns(2)
        with nc1:
            new_pct    = st.number_input("Success target (%)", min_value=50, max_value=100,
                                          value=80, step=5)
        with nc2:
            new_trials = st.number_input("Trials to assess over", min_value=5, max_value=50,
                                          value=10, step=5)
        st.caption(
            f"Goal will be met when the student follows the instruction independently "
            f"on {new_pct}% or more of {new_trials} consecutive trials."
        )
        if st.form_submit_button("✅ Save Goal", type="primary", use_container_width=True):
            if not new_instr.strip():
                st.error("Please enter the target instruction.")
            else:
                g = create_goal(student_name, new_instr.strip(), int(new_pct), int(new_trials))
                if g:
                    ss.igt_goal_id = g["id"]
                    st.success("✅ Goal saved.")
                    st.rerun()

# ── Goal selector ─────────────────────────────────────────────────────────
if not active_goals:
    st.info("No active goals yet. Add one above.")
    st.stop()

st.markdown("### Active goals")
for g in active_goals:
    is_sel = (ss.igt_goal_id == g["id"])
    border = "border-color:#1A6B8A;background:#EBF4F9;" if is_sel else ""
    gc1, gc2 = st.columns([5,1])
    with gc1:
        st.markdown(
            f'<div class="goal-card{"  active" if is_sel else ""}" '
            f'style="{border}">'
            f'<div style="font-size:.88rem;font-weight:600;color:#1A6B8A;">'
            f'{"🎯 " if is_sel else ""}{g["instruction"]}</div>'
            f'<div style="font-size:.72rem;color:#64748b;margin-top:.15rem;">'
            f'Target: {g["target_pct"]}% independent over {g["target_trials"]} trials</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with gc2:
        st.markdown("<div style='padding-top:.4rem;'>", unsafe_allow_html=True)
        if not is_sel:
            if st.button("Select", key=f"sel_goal_{g['id']}", use_container_width=True):
                ss.igt_goal_id = g["id"]; st.rerun()
        else:
            if st.button("Archive", key=f"arch_goal_{g['id']}", use_container_width=True):
                archive_goal(g["id"])
                ss.igt_goal_id = None
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

if not ss.igt_goal_id:
    st.info("Select a goal above to record trials and view analysis.")
    if archived_goals:
        with st.expander(f"Archived goals ({len(archived_goals)})"):
            for g in archived_goals:
                ac1, ac2 = st.columns([5,1])
                with ac1:
                    st.markdown(f'<div class="goal-card" style="opacity:.6;">'
                                f'<div style="font-size:.85rem;">{g["instruction"]}</div>'
                                f'</div>', unsafe_allow_html=True)
                with ac2:
                    st.markdown("<div style='padding-top:.4rem;'>", unsafe_allow_html=True)
                    if st.button("View", key=f"view_arch_{g['id']}", use_container_width=True):
                        ss.igt_goal_id = g["id"]; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ════════════════════════════════════════════════════════════════════════════
# SELECTED GOAL — RECORD + ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
goal = next(g for g in goals if g["id"]==ss.igt_goal_id)
trials_df = load_trials(ss.igt_goal_id)

st.markdown("---")
st.markdown(f"### 🎯 {goal['instruction']}")
st.caption(
    f"Target: **{goal['target_pct']}% independent** across {goal['target_trials']} trials"
)

t_record, t_analysis = st.tabs(["📋  Record trials", "📈  Progress analysis"])

# ════════════════════════════════════════════════════════════════════════════
# RECORD TRIALS
# ════════════════════════════════════════════════════════════════════════════
with t_record:

    st.markdown("**Record a new trial:**")
    with st.form("igt_trial_form", clear_on_submit=True):
        tf1, tf2, tf3 = st.columns([2, 1.5, 2])
        with tf1:
            trial_date = st.date_input("Date", value=date.today(), key="igt_trial_date")
        with tf2:
            trial_time = st.text_input("Time slot", placeholder="e.g. 10:30", key="igt_trial_time")
        with tf3:
            trial_ctx  = st.text_input("Context", placeholder="e.g. Maths, transition from yard",
                                        key="igt_trial_ctx")

        st.markdown("**Response:**")
        resp_cols = st.columns(len(RESPONSE_OPTS))
        trial_resp = st.radio(
            "Response", list(RESPONSE_OPTS.keys()),
            format_func=lambda x: RESPONSE_OPTS[x]["label"],
            horizontal=True, key="igt_resp_radio"
        )
        submitted = st.form_submit_button("💾 Save trial", type="primary", use_container_width=True)

    if submitted:
        if add_trial(student_name, ss.igt_goal_id, trial_date,
                     trial_time.strip(), trial_resp, trial_ctx.strip()):
            st.success(f"✅ Trial saved — {RESPONSE_OPTS[trial_resp]['label']}")
            st.rerun()

    # ── Recent trials list ─────────────────────────────────────────────────
    st.markdown("---")
    if trials_df.empty:
        st.info("No trials recorded yet.")
    else:
        st.markdown(f"**{len(trials_df)} trials recorded:**")
        for _, row in trials_df.sort_values("created_at", ascending=False).head(30).iterrows():
            resp    = row.get("response","")
            cfg     = RESPONSE_OPTS.get(resp,{})
            col     = cfg.get("colour","#334155")
            lbl     = cfg.get("label", resp)
            d_str   = row["obs_date_dt"].strftime("%-d %b %Y")
            t_str   = row.get("time_slot","") or ""
            ctx     = row.get("context","") or ""
            tid     = row.get("id","")

            rc1, rc2 = st.columns([10,1])
            with rc1:
                st.markdown(
                    f'<div class="trial-row">'
                    f'<span style="color:{col};font-weight:700;">{lbl}</span>'
                    f' &nbsp;·&nbsp; <b>{d_str}</b>'
                    + (f' {t_str}' if t_str else '')
                    + (f' &nbsp;—&nbsp; <span style="color:#64748b;">{ctx}</span>' if ctx else '')
                    + f'</div>',
                    unsafe_allow_html=True
                )
            with rc2:
                if st.button("🗑️", key=f"del_trial_{tid}", help="Delete this trial"):
                    delete_trial(tid)
                    st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# PROGRESS ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:
    if trials_df.empty:
        st.info("Record trials to see progress analysis.")
        st.stop()

    target_pct    = goal["target_pct"]
    target_trials = goal["target_trials"]
    n_total = len(trials_df)
    n_ind   = (trials_df["response"]=="independent").sum()
    pct_ind = round(100 * n_ind / n_total) if n_total else 0

    # ── KPIs ──────────────────────────────────────────────────────────────
    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"<div class='kpi'><div class='val'>{n_total}</div><div class='lbl'>Total trials</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi kpi-g'><div class='val'>{n_ind}</div><div class='lbl'>Independent</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><div class='val'>{pct_ind}%</div><div class='lbl'>% independent</div></div>", unsafe_allow_html=True)
    # Check if goal is met (last target_trials at or above target_pct)
    if n_total >= target_trials:
        recent = trials_df.tail(target_trials)
        recent_pct = round(100*(recent["response"]=="independent").sum()/target_trials)
        goal_met = recent_pct >= target_pct
        k4.markdown(
            f"<div class='kpi {'kpi-g' if goal_met else 'kpi-a'}'>"
            f"<div class='val'>{'✅' if goal_met else '⏳'}</div>"
            f"<div class='lbl'>Last {target_trials} trials: {recent_pct}% ind.</div></div>",
            unsafe_allow_html=True
        )
    else:
        k4.markdown(
            f"<div class='kpi'><div class='val'>{target_trials-n_total}</div>"
            f"<div class='lbl'>More trials needed to assess</div></div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ── Rolling independence rate + goal line ──────────────────────────────
    trials_df_s = trials_df.sort_values("created_at").reset_index(drop=True)
    trials_df_s["trial_num"] = range(1, len(trials_df_s)+1)
    trials_df_s["ind"] = (trials_df_s["response"]=="independent").astype(int)
    # Rolling 10-trial average
    win = min(target_trials, n_total)
    trials_df_s["rolling_pct"] = (
        trials_df_s["ind"].rolling(win, min_periods=1).mean() * 100
    ).round(1)
    trials_df_s["date_label"] = trials_df_s["obs_date_dt"].dt.strftime("%-d %b")

    fig_prog = go.Figure()
    # Individual trials
    colour_map = {k: v["colour"] for k,v in RESPONSE_OPTS.items()}
    for resp_key, cfg in RESPONSE_OPTS.items():
        sub = trials_df_s[trials_df_s["response"]==resp_key]
        if sub.empty: continue
        fig_prog.add_trace(go.Scatter(
            x=sub["trial_num"],
            y=[cfg["score"]*100]*len(sub),
            mode="markers",
            name=cfg["label"],
            marker=dict(size=10, color=cfg["colour"], opacity=.7,
                        symbol="circle"),
            hovertemplate=f"{cfg['label']}<br>Trial %{{x}}<extra></extra>",
        ))
    # Rolling rate
    fig_prog.add_trace(go.Scatter(
        x=trials_df_s["trial_num"],
        y=trials_df_s["rolling_pct"],
        mode="lines+markers",
        name=f"Rolling {win}-trial rate",
        line=dict(color=TEAL, width=2.5),
        marker=dict(size=5, color=TEAL),
        hovertemplate="Trial %{x}: %{y}% independent<extra></extra>",
    ))
    # Goal line
    fig_prog.add_hline(
        y=target_pct,
        line_dash="dash", line_color="#16a34a", line_width=2,
        annotation_text=f"Goal: {target_pct}%",
        annotation_position="bottom right",
        annotation_font_color="#16a34a",
    )
    fig_prog.update_layout(
        title=f"Independence rate across {n_total} trials (rolling {win}-trial window)",
        height=360,
        xaxis=dict(title="Trial number", tickformat="d", gridcolor="#e2e8f0"),
        yaxis=dict(title="% independent", range=[0,105], tickformat="d",
                   gridcolor="#e2e8f0", ticksuffix="%"),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10,r=10,t=60,b=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig_prog, use_container_width=True)

    # ── Response breakdown ─────────────────────────────────────────────────
    resp_counts = trials_df["response"].value_counts().reset_index()
    resp_counts.columns = ["response","count"]
    resp_counts["label"] = resp_counts["response"].map(
        {k: v["label"] for k,v in RESPONSE_OPTS.items()}
    )
    resp_counts["colour"] = resp_counts["response"].map(
        {k: v["colour"] for k,v in RESPONSE_OPTS.items()}
    )
    fig_resp = px.bar(
        resp_counts, x="label", y="count",
        color="label",
        color_discrete_map={v["label"]: v["colour"] for v in RESPONSE_OPTS.values()},
        title="Response breakdown — all trials",
        labels={"label":"Response","count":"Trials"},
    )
    fig_resp.update_layout(
        height=280, showlegend=False,
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        margin=dict(l=10,r=10,t=50,b=10),
        yaxis=dict(tickformat="d"),
    )
    st.plotly_chart(fig_resp, use_container_width=True)

    # ── Context breakdown ──────────────────────────────────────────────────
    ctx_df = trials_df[trials_df["context"].str.strip() != ""].copy()
    if not ctx_df.empty:
        ctx_df["Ind"] = (ctx_df["response"]=="independent").astype(int)
        ctx_pct = ctx_df.groupby("context")["Ind"].agg(
            pct=lambda x: round(100*x.mean()),
            trials="count"
        ).reset_index().sort_values("pct", ascending=False)
        ctx_pct["label"] = ctx_pct["context"] + " (n=" + ctx_pct["trials"].astype(str) + ")"
        fig_ctx = px.bar(
            ctx_pct, x="pct", y="label", orientation="h",
            color="pct",
            color_continuous_scale=["#dc2626","#d97706","#16a34a"],
            range_color=[0,100],
            title="% independent by context",
            labels={"pct":"% independent","label":""},
        )
        fig_ctx.update_layout(
            height=max(240, len(ctx_pct)*30),
            coloraxis_showscale=False,
            plot_bgcolor="#f8fafc", paper_bgcolor="white",
            margin=dict(l=10,r=10,t=50,b=10),
            xaxis=dict(tickformat="d", ticksuffix="%"),
        )
        st.plotly_chart(fig_ctx, use_container_width=True)
        st.caption("💡 Green bars show contexts where the student follows the instruction independently. "
                   "Red bars show contexts needing more support.")

    # ── Download ───────────────────────────────────────────────────────────
    st.markdown("---")
    dl = trials_df.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    dl["response_label"] = dl["response"].map({k: v["label"] for k,v in RESPONSE_OPTS.items()})
    csv = dl[["obs_date","time_slot","response","response_label","context","created_by"]].to_csv(index=False)
    st.download_button("📥 Download trial data (CSV)", csv,
        file_name=f"InstructionTrials_{student_name.replace(' ','_')}.csv",
        mime="text/csv", use_container_width=True)

    # ── Goal management ────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚙️ Manage this goal"):
        st.warning("Deleting removes all trial data for this goal permanently.")
        confirm = st.text_input("Type DELETE to confirm", key="igt_del_confirm")
        if st.button("🗑️ Delete goal and all trials", key="igt_del_btn", type="secondary"):
            if confirm.strip() == "DELETE":
                delete_goal(ss.igt_goal_id)
                ss.igt_goal_id = None
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("Type DELETE to confirm.")
