# ════════════════════════════════════════════════════════════════════════════
# 18_Scatter_Plot_Tracker.py  ·  CLC-LBU Portal
# ACCEPT Program — Scatter Plot Tracker
# FIX: data_editor values disappearing — df stored in session state as source
#      of truth instead of being rebuilt from sp_cells on every rerun
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from auth import require_auth, logout_button
require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
logout_button()

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
.kpi .val {{ font-size:1.7rem; font-weight:700; color:{TEAL}; line-height:1.1; }}
.kpi .lbl {{ font-size:.72rem; color:#666; margin-top:.15rem; }}
.kpi-amber {{ border-color:{AMBER}; }}
.kpi-amber .val {{ color:{AMBER}; }}
.insight {{
    background: #FEF9EC; border: 1px solid {AMBER}55;
    border-left: 4px solid {AMBER};
    border-radius: 6px; padding: .55rem 1rem;
    font-size: .85rem; margin-bottom: .4rem;
}}
.insight-ok {{
    background: #F0FAF4; border: 1px solid #2EA05655;
    border-left: 4px solid #2EA056;
}}
.key-box {{
    background: #EBF4F9; border: 1px solid {TEAL}44;
    border-radius: 6px; padding: .45rem 1rem;
    font-size: .86rem; margin-bottom: .75rem;
}}
</style>
""", unsafe_allow_html=True)

DEFAULT_SLOTS = [
    ("9:00",  "De-escalation activity"),
    ("9:15",  "Interoception"),
    ("9:20",  "Activity"),
    ("10:00", "Breakfast"),
    ("10:05", "Fitness"),
    ("10:20", "Quiet Time"),
    ("10:30", "Activity"),
    ("11:00", "Recess"),
    ("11:30", "Quiet Time"),
    ("11:40", "Activity"),
    ("12:30", "Activity"),
    ("12:50", "Lunch eating"),
    ("13:00", "Lunch"),
    ("13:30", "Quiet Time"),
    ("13:45", "I.C.T."),
    ("14:30", "Home"),
]
DAYS      = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
CELL_OPTS = ["", "1", "2", "X"]


def _build_default_df():
    """Build the starting DataFrame from default slots with all cells empty."""
    rows = []
    for t, a in DEFAULT_SLOTS:
        row = {"Time": t, "Learning Activity": a}
        for d in DAYS:
            row[d] = ""
        rows.append(row)
    return pd.DataFrame(rows)


def _init():
    defaults = {
        "sp_student":    "",
        "sp_term":       "3",
        "sp_week":       1,
        "sp_week_start": date.today(),
        "sp_behaviours": ["Roaming around the classroom"],
        "sp_anteceds":   {d: "" for d in DAYS},
        "sp_saved_id":   None,
        # ── KEY FIX: store the grid df directly in session state ──────────────
        # This is the single source of truth for the table.
        # We never rebuild it from sp_cells — that loop caused values to vanish.
        "sp_grid_df":    _build_default_df(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
ss = st.session_state


def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


def _df_to_cells_and_slots(df):
    """Extract sp_cells and sp_slots from the stored grid df (for analysis + save)."""
    cells = {}
    slots = []
    for _, row in df.iterrows():
        t = str(row.get("Time", "")).strip()
        a = str(row.get("Learning Activity", "")).strip()
        if not t:
            continue
        slots.append([t, a])
        cells[t] = {d: (row[d] if row[d] in CELL_OPTS else "") for d in DAYS}
    return cells, slots


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — load / new session
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 📂 Sessions")
    sb = get_sb()
    if sb:
        try:
            sessions = (
                sb.table("scatter_plot_sessions")
                .select("id,student_name,term,week_number,date_start")
                .order("created_at", desc=True)
                .limit(30)
                .execute()
            )
            if sessions.data:
                opts = {
                    f"{r['student_name']} — T{r['term']} W{r['week_number']} ({r['date_start']})": r["id"]
                    for r in sessions.data
                }
                chosen = st.selectbox("Load session", ["— New —"] + list(opts.keys()))
                if chosen != "— New —" and st.button("Load", use_container_width=True):
                    sid = opts[chosen]
                    rec = (
                        sb.table("scatter_plot_sessions")
                        .select("*").eq("id", sid).single().execute().data
                    )
                    entries = (
                        sb.table("scatter_plot_entries")
                        .select("*").eq("session_id", sid).execute().data
                    )
                    ss.sp_student    = rec["student_name"]
                    ss.sp_term       = rec["term"]
                    ss.sp_week       = rec["week_number"]
                    ss.sp_week_start = date.fromisoformat(rec["date_start"])
                    ss.sp_behaviours = rec["targeted_behaviours"]
                    ss.sp_anteceds   = rec.get("antecedents", {d: "" for d in DAYS})
                    ss.sp_saved_id   = sid

                    # ── Rebuild grid df from loaded entries ───────────────────
                    time_slots = rec.get("time_slots", [list(s) for s in DEFAULT_SLOTS])
                    rows = []
                    for slot in time_slots:
                        t, a = slot[0], slot[1]
                        row = {"Time": t, "Learning Activity": a}
                        for d in DAYS:
                            row[d] = ""
                        rows.append(row)
                    df = pd.DataFrame(rows)
                    for e in entries:
                        t_val = e["time_slot"]
                        d_val = e["day"]
                        v_val = e["value"]
                        mask  = df["Time"] == t_val
                        if mask.any() and d_val in DAYS:
                            df.loc[mask, d_val] = v_val
                    ss.sp_grid_df = df
                    # ─────────────────────────────────────────────────────────

                    st.success("Loaded!")
                    st.rerun()
        except Exception as e:
            st.caption(f"⚠️ {e}")
    else:
        st.caption("Add SUPABASE_URL / SUPABASE_KEY to secrets to enable save/load.")

    st.markdown("---")
    if st.button("🆕 New Session", use_container_width=True):
        for k in list(ss.keys()):
            if k.startswith("sp_"):
                del st.session_state[k]
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="clc-header">
  <h2>📊 ACCEPT Program — Scatter Plot Tracker</h2>
  <p>Aligning Curriculum for Competency in Education and Purposeful Transition
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)

t_entry, t_analysis = st.tabs(["📋  Data Entry", "📈  Analysis & Insights"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — DATA ENTRY
# ════════════════════════════════════════════════════════════════════════════
with t_entry:

    # Student info
    c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
    ss.sp_student    = c1.text_input("Student", ss.sp_student)
    ss.sp_term       = c2.text_input("Term", ss.sp_term)
    ss.sp_week       = int(c3.number_input("Week", 1, 20, int(ss.sp_week)))
    ss.sp_week_start = c4.date_input("Week commencing", ss.sp_week_start)

    # Targeted behaviours
    with st.expander("🎯 Targeted Behaviours", expanded=True):
        behs = ss.sp_behaviours[:]
        for i in range(len(behs)):
            ca, cb = st.columns([9, 1])
            behs[i] = ca.text_input(
                f"Behaviour {i+1}", behs[i],
                key=f"spt_beh_{i}", label_visibility="collapsed"
            )
            if cb.button("✕", key=f"spt_db_{i}") and len(behs) > 1:
                behs.pop(i)
                ss.sp_behaviours = behs
                st.rerun()
        if st.button("＋ Add behaviour"):
            behs.append("")
            ss.sp_behaviours = behs
            st.rerun()
        ss.sp_behaviours = behs

    # Key
    st.markdown(
        "<div class='key-box'>"
        "<b>Key:</b> &nbsp;"
        "<code>1</code> = one occurrence &nbsp;|&nbsp;"
        "<code>2</code> = more than one occurrence &nbsp;|&nbsp;"
        "<code>X</code> = class evacuation / unable to observe"
        "</div>",
        unsafe_allow_html=True
    )

    # ── Column config with date headers ──────────────────────────────────────
    col_cfg = {
        "Time":              st.column_config.TextColumn("Time", width=75),
        "Learning Activity": st.column_config.TextColumn("Learning Activity", width=190),
    }
    for i, d in enumerate(DAYS):
        dt  = ss.sp_week_start + timedelta(days=i)
        lbl = f"{d[:3]}  {dt.strftime('%-d/%-m')}"
        col_cfg[d] = st.column_config.SelectboxColumn(lbl, options=CELL_OPTS, width=95)

    # ── THE FIX: pass sp_grid_df directly — no rebuild from sp_cells ─────────
    # Use a unique key per session so the editor resets when a new session loads.
    # The key includes saved_id (or "new") to force a fresh editor on load.
    editor_key = f"sp_de_{ss.sp_saved_id or 'new'}"

    edited = st.data_editor(
        ss.sp_grid_df,          # ← source of truth from session state
        column_config=col_cfg,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=editor_key,
    )

    # Persist the edited df back to session state immediately
    # This is the ONLY place sp_grid_df is updated — no reconstruction loop
    ss.sp_grid_df = edited
    # ─────────────────────────────────────────────────────────────────────────

    # Derive cells + slots from the stored df (for totals, analysis, save)
    cells, slots = _df_to_cells_and_slots(edited)

    # Daily totals strip
    st.markdown("---")
    tot_cols    = st.columns(len(DAYS) + 2)
    tot_cols[0].markdown("**Daily totals**")
    day_totals  = {}
    grand_total = 0
    for i, d in enumerate(DAYS):
        n = sum(1 for t in cells if cells[t].get(d, "") in ["1", "2"])
        day_totals[d]  = n
        grand_total   += n
        tot_cols[i + 1].markdown(
            f"<div class='kpi'><div class='val'>{n}</div><div class='lbl'>{d[:3]}</div></div>",
            unsafe_allow_html=True
        )
    tot_cols[-1].markdown(
        f"<div class='kpi kpi-amber'><div class='val'>{grand_total}</div>"
        f"<div class='lbl'>Total</div></div>",
        unsafe_allow_html=True
    )

    # Antecedents
    st.markdown("**Antecedents / Triggers**")
    ant_cols = st.columns(5)
    for i, d in enumerate(DAYS):
        ss.sp_anteceds[d] = ant_cols[i].text_area(
            d, ss.sp_anteceds.get(d, ""),
            height=68, key=f"ant_{d}"
        )

    # Save
    st.markdown("---")
    if st.button("💾 Save to Supabase", type="primary"):
        sb = get_sb()
        if sb:
            try:
                payload = {
                    "student_name":        ss.sp_student,
                    "term":                ss.sp_term,
                    "week_number":         int(ss.sp_week),
                    "date_start":          ss.sp_week_start.isoformat(),
                    "date_end":            (ss.sp_week_start + timedelta(days=4)).isoformat(),
                    "targeted_behaviours": ss.sp_behaviours,
                    "time_slots":          slots,
                    "antecedents":         ss.sp_anteceds,
                }
                if ss.sp_saved_id:
                    sb.table("scatter_plot_sessions").update(payload).eq("id", ss.sp_saved_id).execute()
                    sid = ss.sp_saved_id
                    sb.table("scatter_plot_entries").delete().eq("session_id", sid).execute()
                else:
                    res = sb.table("scatter_plot_sessions").insert(payload).execute()
                    sid = res.data[0]["id"]
                    ss.sp_saved_id = sid

                entries = [
                    {"session_id": sid, "time_slot": t, "day": d, "value": v}
                    for t, day_vals in cells.items()
                    for d, v in day_vals.items()
                    if v
                ]
                if entries:
                    sb.table("scatter_plot_entries").insert(entries).execute()
                st.success("✅ Session saved successfully!")
            except Exception as e:
                st.error(f"Save failed: {e}")
        else:
            st.warning("Supabase not configured — data lives in session only.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYSIS & INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:

    if not ss.sp_student:
        st.info("👈 Enter student details in the Data Entry tab first.")
        st.stop()

    # Derive current cells + slots from the stored df
    cells, slots = _df_to_cells_and_slots(ss.sp_grid_df)
    slots_map    = {s[0]: s[1] for s in slots}
    times        = [s[0] for s in slots]

    SCORE    = {"1": 1, "2": 2, "X": 0, "": 0}
    INCIDENT = {"1": 1, "2": 1, "X": 0, "": 0}

    matrix = []
    for t in times:
        row = {"Time": t, "Activity": slots_map.get(t, "")}
        for d in DAYS:
            v      = cells.get(t, {}).get(d, "")
            row[d] = SCORE[v]
        row["Total"]     = sum(row[d] for d in DAYS)
        row["Incidents"] = sum(INCIDENT.get(cells.get(t, {}).get(d, ""), 0) for d in DAYS)
        matrix.append(row)

    df_m = pd.DataFrame(matrix)

    total_inc = int(df_m["Incidents"].sum())
    total_scr = int(df_m["Total"].sum())
    busiest_d = max(DAYS, key=lambda d: df_m[d].sum()) if total_inc > 0 else "—"
    peak_row  = df_m.loc[df_m["Incidents"].idxmax()] if total_inc > 0 else None
    peak_time = f"{peak_row['Time']} — {peak_row['Activity']}" if peak_row is not None else "—"

    st.markdown(
        f"### Analysis — {ss.sp_student} &nbsp;|&nbsp; Term {ss.sp_term}, Week {ss.sp_week}"
    )

    k1, k2, k3, k4 = st.columns(4)
    for col, val, lbl, amber in [
        (k1, total_inc,  "Intervals with behaviour",  False),
        (k2, total_scr,  "Weighted frequency score",  False),
        (k3, busiest_d,  "Highest-frequency day",     True),
        (k4, peak_time,  "Highest-risk time slot",    True),
    ]:
        cls  = "kpi kpi-amber" if amber else "kpi"
        vcls = f"color:{AMBER}" if amber else f"color:{TEAL}"
        col.markdown(
            f"<div class='{cls}'><div class='val' style='{vcls};font-size:1.1rem'>{val}</div>"
            f"<div class='lbl'>{lbl}</div></div>",
            unsafe_allow_html=True
        )

    if total_inc == 0:
        st.success("🎉 No behaviour incidents recorded this week — great outcome!")
        st.stop()

    st.markdown("---")

    # Heatmap
    import numpy as np
    heat_z    = df_m[DAYS].values
    hover_txt = [[cells.get(t, {}).get(d, "") or "—" for d in DAYS] for t in times]
    y_labels  = [f"{t}  {slots_map.get(t,'')}" for t in times]
    x_labels  = [
        f"{d[:3]} {(ss.sp_week_start + timedelta(days=i)).strftime('%-d/%-m')}"
        for i, d in enumerate(DAYS)
    ]

    fig_heat = go.Figure(go.Heatmap(
        z=heat_z, x=x_labels, y=y_labels,
        text=hover_txt, texttemplate="%{text}",
        colorscale=[[0, "#EBF4F9"], [0.5, "#E8A020"], [1, "#C0392B"]],
        showscale=True,
        colorbar=dict(title="Score", tickvals=[0, 1, 2]),
        zmin=0, zmax=2,
    ))
    fig_heat.update_layout(
        title="Behaviour Frequency Heatmap — Time Slot × Day",
        height=500,
        margin=dict(l=10, r=10, t=50, b=10),
        yaxis=dict(autorange="reversed"),
        xaxis=dict(side="top"),
        font=dict(size=11),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        slot_df = df_m[df_m["Incidents"] > 0].copy()
        slot_df["Label"] = slot_df["Time"] + "  " + slot_df["Activity"]
        fig_slots = px.bar(
            slot_df.sort_values("Incidents"),
            x="Incidents", y="Label", orientation="h",
            color="Incidents",
            color_continuous_scale=["#90CBE3", TEAL],
            title="Incidents by Time Slot / Activity",
            labels={"Incidents": "Intervals with behaviour", "Label": ""},
        )
        fig_slots.update_layout(
            height=400, coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        st.plotly_chart(fig_slots, use_container_width=True)

    with col_b:
        day_inc_df = pd.DataFrame({
            "Day":       DAYS,
            "Incidents": [
                sum(INCIDENT.get(cells.get(t, {}).get(d, ""), 0) for t in times)
                for d in DAYS
            ]
        })
        fig_days = px.bar(
            day_inc_df, x="Day", y="Incidents",
            color="Incidents",
            color_continuous_scale=["#90CBE3", TEAL],
            title="Incidents by Day of Week",
        )
        fig_days.update_layout(
            height=400, coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        st.plotly_chart(fig_days, use_container_width=True)

    # Activity summary
    st.markdown("### 📋 Activity-Level Summary")
    act_grp = (
        df_m[df_m["Incidents"] > 0][["Activity", "Incidents", "Total"]]
        .groupby("Activity").sum().reset_index()
        .sort_values("Incidents", ascending=False)
        .rename(columns={"Incidents": "Intervals with behaviour", "Total": "Weighted score"})
    )
    st.dataframe(act_grp, use_container_width=True, hide_index=True)

    # Antecedents
    if any(ss.sp_anteceds.get(d, "").strip() for d in DAYS):
        st.markdown("### 📝 Antecedents / Triggers")
        ant_cols = st.columns(5)
        for i, d in enumerate(DAYS):
            note = ss.sp_anteceds.get(d, "").strip()
            ant_cols[i].markdown(f"**{d[:3]}**")
            ant_cols[i].caption(note or "—")

    # Pattern insights
    st.markdown("### 💡 Pattern Insights")
    insights = []

    for _, row in df_m[df_m["Incidents"] >= 3].iterrows():
        insights.append(("warn",
            f"⚠️ <b>{row['Time']} — {row['Activity']}</b> had behaviour in "
            f"{int(row['Incidents'])}/5 days this week. Consider schedule adjustments or "
            "targeted environmental modifications at this time."))

    morning_times   = [t for t in times if t and int(t.split(":")[0]) < 12]
    afternoon_times = [t for t in times if t and int(t.split(":")[0]) >= 12]
    morn_inc = int(sum(df_m[df_m["Time"].isin(morning_times)]["Incidents"]))
    arvo_inc = int(sum(df_m[df_m["Time"].isin(afternoon_times)]["Incidents"]))
    if total_inc > 0:
        if morn_inc > arvo_inc * 1.5:
            insights.append(("warn",
                f"🌅 Behaviour is concentrated in the <b>morning session</b> "
                f"({morn_inc} morning vs {arvo_inc} afternoon intervals). "
                "Review morning routine, transitions, and arrival conditions."))
        elif arvo_inc > morn_inc * 1.5:
            insights.append(("warn",
                f"🌇 Behaviour is concentrated in the <b>afternoon session</b> "
                f"({arvo_inc} afternoon vs {morn_inc} morning intervals). "
                "Consider fatigue, hunger, or activity demand levels post-lunch."))

    double_slots = [
        f"{t} on {d[:3]}"
        for t in times for d in DAYS
        if cells.get(t, {}).get(d, "") == "2"
    ]
    if double_slots:
        insights.append(("warn",
            f"🔴 High-frequency (multiple occurrences) recorded at: "
            f"<b>{', '.join(double_slots[:6])}</b>. "
            "These are priority intervals for proactive support planning."))

    zero_days = [d for d in DAYS if day_totals.get(d, 0) == 0]
    if zero_days:
        insights.append(("ok",
            f"✅ No behaviour recorded on <b>{', '.join(zero_days)}</b>. "
            "Reflect on what was different and consider replicating those conditions."))

    if 0 < total_inc <= 3:
        insights.append(("ok",
            "📉 Low overall incident count this week. "
            "Current strategies appear to be having a positive effect."))

    if not insights:
        insights.append(("warn",
            "📊 More data needed across the week for meaningful pattern analysis."))

    for kind, text in insights:
        css = "insight" if kind == "warn" else "insight insight-ok"
        st.markdown(f"<div class='{css}'>{text}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.caption("💾 Save the session in the Data Entry tab to persist this record to Supabase.")
