# ════════════════════════════════════════════════════════════════════════════
# 18_Scatter_Plot_Tracker.py  ·  CLC-LBU Portal
# Scatter Plot Tracker — form-based per-observation entry
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
.obs-pill {{
    display:inline-block; padding:.2rem .6rem; border-radius:20px;
    font-size:.75rem; font-weight:700; margin:.1rem;
}}
.obs-1  {{ background:#dbeafe; color:#1d4ed8; }}
.obs-2  {{ background:#fee2e2; color:#b91c1c; }}
.obs-x  {{ background:#f3f4f6; color:#6b7280; }}
</style>
""", unsafe_allow_html=True)

# ── Time slots ────────────────────────────────────────────────────────────────
DEFAULT_SLOTS = [
    "9:00", "9:15", "9:20", "10:00", "10:05", "10:20", "10:30",
    "11:00", "11:30", "11:40", "12:30", "12:50", "13:00",
    "13:30", "13:45", "14:30",
]
DEFAULT_ACTIVITIES = {
    "9:00": "De-escalation activity", "9:15": "Interoception",
    "9:20": "Activity", "10:00": "Breakfast", "10:05": "Fitness",
    "10:20": "Quiet Time", "10:30": "Activity", "11:00": "Recess",
    "11:30": "Quiet Time", "11:40": "Activity", "12:30": "Activity",
    "12:50": "Lunch eating", "13:00": "Lunch", "13:30": "Quiet Time",
    "13:45": "I.C.T.", "14:30": "Home",
}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


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
        res = (sb.table("scatter_plot_observations")
               .select("*")
               .eq("student_id", student_id)
               .order("obs_date")
               .order("time_slot")
               .execute())
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Could not load observations: {e}")
        return pd.DataFrame()


def save_observation(row: dict) -> bool:
    sb = get_sb()
    if not sb:
        st.warning("Supabase not configured.")
        return False
    try:
        sb.table("scatter_plot_observations").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False


def delete_observation(obs_id: str) -> bool:
    sb = get_sb()
    if not sb:
        return False
    try:
        sb.table("scatter_plot_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False


# ── Session state ─────────────────────────────────────────────────────────────
if "spt_student_id"   not in st.session_state: st.session_state.spt_student_id   = None
if "spt_student_name" not in st.session_state: st.session_state.spt_student_name = ""
if "spt_behaviours"   not in st.session_state: st.session_state.spt_behaviours   = ""
if "spt_reload"       not in st.session_state: st.session_state.spt_reload       = True


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="clc-header">
  <h2>📊 Scatter Plot Tracker</h2>
  <p>Record and analyse targeted behaviour frequency across the school day
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STUDENT SELECTOR  (persistent — sits above all tabs)
# ════════════════════════════════════════════════════════════════════════════
students = load_students()
student_opts = {s["id"]: f"{s['name']}  ({s.get('program','')})" for s in students}

if students:
    # Find current index
    ids = list(student_opts.keys())
    cur_idx = ids.index(st.session_state.spt_student_id) if st.session_state.spt_student_id in ids else 0

    sc1, sc2, sc3 = st.columns([3, 2, 1])
    with sc1:
        selected_id = st.selectbox(
            "Student", ids,
            index=cur_idx,
            format_func=lambda x: student_opts[x],
            key="spt_sel"
        )
    with sc2:
        st.session_state.spt_behaviours = st.text_input(
            "Target behaviour(s)",
            value=st.session_state.spt_behaviours,
            placeholder="e.g. Roaming around the environment",
            key="spt_beh_top"
        )
    with sc3:
        st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
        if st.button("🔄 Refresh data", use_container_width=True, key="spt_refresh"):
            load_observations.clear()
            st.session_state.spt_reload = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Detect student change — reload observations
    if selected_id != st.session_state.spt_student_id:
        st.session_state.spt_student_id   = selected_id
        st.session_state.spt_student_name = next((s["name"] for s in students if s["id"] == selected_id), "")
        st.session_state.spt_reload = True
        load_observations.clear()
        st.rerun()
else:
    st.warning("No students found. Add students via the Admin section of the Behaviour Support tool.")
    st.stop()

student_id   = st.session_state.spt_student_id
student_name = st.session_state.spt_student_name or student_opts.get(student_id, "")

# Load all observations for this student
obs_df = load_observations(student_id)
st.session_state.spt_reload = False

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
t_add, t_grid, t_analysis = st.tabs([
    "➕  Record Observation",
    "📅  Weekly Grid",
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
    <b>Key:</b> &nbsp;
    <code>1</code> = one occurrence &nbsp;|&nbsp;
    <code>2</code> = more than one occurrence &nbsp;|&nbsp;
    <code>X</code> = class evacuation / unable to observe
    </div>
    """, unsafe_allow_html=True)

    with st.form("spt_add_obs", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns([2, 2, 1])
        with fc1:
            obs_date = st.date_input("Date *", value=date.today())
        with fc2:
            time_opts  = DEFAULT_SLOTS + ["Other"]
            time_sel   = st.selectbox("Time slot *", time_opts)
        with fc3:
            # Large, obvious value selector
            value_sel = st.selectbox(
                "Value *",
                ["1 — one occurrence",
                 "2 — more than one occurrence",
                 "X — evacuation / unable to observe"],
            )

        # Activity — auto-fills from time slot
        default_act = DEFAULT_ACTIVITIES.get(time_sel, "") if time_sel != "Other" else ""
        fc4, fc5 = st.columns([3, 1])
        with fc4:
            activity = st.text_input("Learning activity", value=default_act,
                                     placeholder="e.g. Quiet Time")
        with fc5:
            custom_time = ""
            if time_sel == "Other":
                custom_time = st.text_input("Custom time", placeholder="e.g. 8:45")

        notes = st.text_input("Notes (optional)", placeholder="Any context about this observation")

        submitted = st.form_submit_button("💾 Save Observation", type="primary", use_container_width=True)

    if submitted:
        actual_time = custom_time.strip() if time_sel == "Other" else time_sel
        actual_value = value_sel[0]  # "1", "2", or "X"

        if not actual_time:
            st.error("Please enter a time.")
        else:
            row = {
                "student_id":        student_id,
                "student_name":      student_name,
                "obs_date":          obs_date.isoformat(),
                "time_slot":         actual_time,
                "activity":          activity.strip(),
                "value":             actual_value,
                "target_behaviours": st.session_state.spt_behaviours,
                "notes":             notes.strip(),
                "created_by":        get_staff_name(),
            }
            if save_observation(row):
                st.success(f"✅ Saved — {obs_date.strftime('%-d %b')} · {actual_time} · **{actual_value}**")
                load_observations.clear()
                st.rerun()

    # ── Recent observations ───────────────────────────────────────────────
    if not obs_df.empty:
        st.markdown("---")
        st.markdown("#### Recent observations")
        recent = obs_df.sort_values("created_at", ascending=False).head(15)
        for _, row in recent.iterrows():
            v   = row.get("value","")
            cls = f"obs-{v.lower()}" if v in ["1","2","X"] else "obs-x"
            d_str = pd.to_datetime(row["obs_date"]).strftime("%-d %b")
            act   = row.get("activity","") or ""
            note  = row.get("notes","") or ""
            rid   = row.get("id","")
            rc1, rc2 = st.columns([9, 1])
            with rc1:
                st.markdown(
                    f'<span class="obs-pill {cls}">{v}</span> '
                    f'<b>{d_str}</b> &nbsp; {row["time_slot"]}'
                    + (f' — {act}' if act else '')
                    + (f' <span style="color:#888;font-size:.8rem;">· {note}</span>' if note else ''),
                    unsafe_allow_html=True
                )
            with rc2:
                if st.button("🗑️", key=f"del_obs_{rid}", help="Delete this observation"):
                    if delete_observation(rid):
                        load_observations.clear()
                        st.rerun()


# ────────────────────────────────────────────────────────────────────────────
# TAB 2 — WEEKLY GRID VIEW (read-only, reconstructed from saved observations)
# ────────────────────────────────────────────────────────────────────────────
with t_grid:
    st.markdown(f"#### {student_name} — Weekly Grid")

    if obs_df.empty:
        st.info("No observations recorded yet. Use the **Record Observation** tab to add data.")
    else:
        obs_df["obs_date"] = pd.to_datetime(obs_df["obs_date"])

        # Week picker
        all_dates  = sorted(obs_df["obs_date"].dt.date.unique())
        first_date = all_dates[0]
        last_date  = all_dates[-1]

        # Default to week of most recent observation
        default_monday = last_date - timedelta(days=last_date.weekday())
        if "spt_grid_week" not in st.session_state:
            st.session_state.spt_grid_week = default_monday

        wc1, wc2, wc3 = st.columns([1, 3, 1])
        with wc1:
            if st.button("← Prev week", use_container_width=True, key="spt_prev_wk"):
                st.session_state.spt_grid_week -= timedelta(weeks=1)
                st.rerun()
        with wc2:
            week_start = st.session_state.spt_grid_week
            week_end   = week_start + timedelta(days=4)
            st.markdown(
                f'<div style="text-align:center;padding:.45rem 0;font-weight:600;color:{TEAL};">'
                f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
                f'</div>',
                unsafe_allow_html=True
            )
        with wc3:
            if st.button("Next week →", use_container_width=True, key="spt_next_wk"):
                st.session_state.spt_grid_week += timedelta(weeks=1)
                st.rerun()

        # Filter to this week
        week_obs = obs_df[
            (obs_df["obs_date"].dt.date >= week_start) &
            (obs_df["obs_date"].dt.date <= week_end)
        ].copy()

        # Build grid: rows = time slots, cols = days
        all_times = DEFAULT_SLOTS.copy()
        extra_times = [t for t in week_obs["time_slot"].unique() if t not in all_times]
        all_times  += sorted(extra_times)

        # Day labels with dates
        day_dates = {
            DAYS[i]: (week_start + timedelta(days=i)).strftime("%-d/%m")
            for i in range(5)
        }

        grid_rows = []
        for t in all_times:
            row = {
                "Time": t,
                "Activity": DEFAULT_ACTIVITIES.get(t, ""),
            }
            for d in DAYS:
                d_date = week_start + timedelta(days=DAYS.index(d))
                matches = week_obs[
                    (week_obs["time_slot"] == t) &
                    (week_obs["obs_date"].dt.date == d_date)
                ]
                if matches.empty:
                    row[f"{d[:3]}\n{day_dates[d]}"] = ""
                else:
                    vals = matches["value"].tolist()
                    row[f"{d[:3]}\n{day_dates[d]}"] = " ".join(vals)
            # Row total
            total = sum(
                1 for d in DAYS
                if week_obs[
                    (week_obs["time_slot"] == t) &
                    (week_obs["obs_date"].dt.date == (week_start + timedelta(days=DAYS.index(d))))
                ].shape[0] > 0
            )
            row["Total"] = total if total > 0 else ""
            grid_rows.append(row)

        grid_df = pd.DataFrame(grid_rows)
        # Only show rows that have at least one observation
        day_cols = [c for c in grid_df.columns if c not in ["Time","Activity","Total"]]
        has_data = grid_df[day_cols].apply(lambda r: r.astype(bool).any(), axis=1)
        display_df = grid_df[has_data | grid_df["Time"].isin(DEFAULT_SLOTS)]

        if display_df.empty or not has_data.any():
            st.info(f"No observations recorded for the week of {week_start.strftime('%-d %b')}.")
        else:
            # Style the grid
            def _style_cell(val):
                if val == "1":  return "background:#dbeafe;color:#1d4ed8;font-weight:700;text-align:center;"
                if val == "2":  return "background:#fee2e2;color:#b91c1c;font-weight:700;text-align:center;"
                if val == "X":  return "background:#f3f4f6;color:#6b7280;font-weight:600;text-align:center;"
                if "2" in str(val): return "background:#fee2e2;color:#b91c1c;font-weight:700;text-align:center;"
                if "1" in str(val): return "background:#dbeafe;color:#1d4ed8;font-weight:700;text-align:center;"
                return ""

            styled = display_df.style.applymap(
                _style_cell,
                subset=[c for c in display_df.columns if c not in ["Time","Activity"]]
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Antecedents row
            st.markdown("**Antecedents / Triggers for this week:**")
            ant_cols = st.columns(5)
            for i, d in enumerate(DAYS):
                ant_cols[i].text_area(
                    f"{d[:3]} {day_dates[d]}",
                    key=f"spt_ant_{d}_{week_start}",
                    height=60,
                    placeholder="Any triggers noted..."
                )

            # Week totals
            st.markdown("**Week totals:**")
            tc = st.columns(6)
            grand = 0
            for i, d in enumerate(DAYS):
                d_date = week_start + timedelta(days=i)
                n = week_obs[week_obs["obs_date"].dt.date == d_date].shape[0]
                grand += n
                tc[i].markdown(
                    f"<div class='kpi'><div class='val'>{n}</div>"
                    f"<div class='lbl'>{d[:3]}</div></div>",
                    unsafe_allow_html=True
                )
            tc[5].markdown(
                f"<div class='kpi kpi-amber'><div class='val'>{grand}</div>"
                f"<div class='lbl'>Total</div></div>",
                unsafe_allow_html=True
            )


# ────────────────────────────────────────────────────────────────────────────
# TAB 3 — ANALYSIS & DOWNLOAD
# ────────────────────────────────────────────────────────────────────────────
with t_analysis:
    st.markdown(f"#### {student_name} — Analysis")

    if obs_df.empty:
        st.info("No observations recorded yet.")
        st.stop()

    obs_df["obs_date"] = pd.to_datetime(obs_df["obs_date"])

    # Date range filter
    fc1, fc2 = st.columns(2)
    with fc1:
        date_from = st.date_input(
            "From", value=obs_df["obs_date"].min().date(), key="spt_from"
        )
    with fc2:
        date_to = st.date_input(
            "To", value=obs_df["obs_date"].max().date(), key="spt_to"
        )

    filtered = obs_df[
        (obs_df["obs_date"].dt.date >= date_from) &
        (obs_df["obs_date"].dt.date <= date_to)
    ].copy()

    if filtered.empty:
        st.info("No observations in this date range.")
        st.stop()

    # ── KPIs ─────────────────────────────────────────────────────────────
    total     = len(filtered)
    n_1       = (filtered["value"] == "1").sum()
    n_2       = (filtered["value"] == "2").sum()
    n_x       = (filtered["value"] == "X").sum()
    days_span = max((filtered["obs_date"].max() - filtered["obs_date"].min()).days, 1)

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='kpi'><div class='val'>{total}</div><div class='lbl'>Total observations</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='val'>{n_1}</div><div class='lbl'>Single occurrence (1)</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi kpi-amber'><div class='val'>{n_2}</div><div class='lbl'>Multiple occurrences (2)</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi'><div class='val'>{days_span}</div><div class='lbl'>Days in range</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Chart 1: Daily frequency ──────────────────────────────────────────
    daily = (filtered.groupby(filtered["obs_date"].dt.date)["value"]
             .count().reset_index(name="count"))
    daily["obs_date"] = pd.to_datetime(daily["obs_date"])
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=daily["obs_date"].dt.strftime("%-d %b"),
        y=daily["count"],
        marker=dict(color=[
            "#C0392B" if v >= 3 else TEAL for v in daily["count"]
        ]),
        text=daily["count"], textposition="outside",
    ))
    fig1.update_layout(
        title="Daily Observation Count  (red = 3+ intervals)",
        height=300, showlegend=False,
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0"),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: Time of day ──────────────────────────────────────────────
    time_counts = filtered.groupby("time_slot")["value"].count().reset_index(name="count")
    # Sort by time
    def t_sort(ts):
        try:
            h, m = str(ts).split(":")
            return int(h)*60+int(m)
        except:
            return 999
    time_counts["sort"] = time_counts["time_slot"].apply(t_sort)
    time_counts = time_counts.sort_values("sort")
    time_counts["label"] = time_counts["time_slot"].apply(
        lambda t: f"{t}  {DEFAULT_ACTIVITIES.get(t,'')}"
    )

    fig2 = px.bar(
        time_counts, x="count", y="label", orientation="h",
        color="count", color_continuous_scale=["#90CBE3", TEAL],
        title="Observations by Time Slot",
        labels={"count":"Observations","label":""},
    )
    fig2.update_layout(
        height=max(300, len(time_counts)*28), coloraxis_showscale=False,
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(tickformat="d"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Chart 3: Value breakdown ──────────────────────────────────────────
    val_counts = filtered["value"].value_counts().reset_index()
    val_counts.columns = ["Value","Count"]
    val_map = {"1":"1 — single","2":"2 — multiple","X":"X — evac/unable"}
    val_counts["Label"] = val_counts["Value"].map(val_map).fillna(val_counts["Value"])
    colour_map = {"1":"#3b82f6","2":"#ef4444","X":"#9ca3af"}
    val_counts["colour"] = val_counts["Value"].map(colour_map).fillna("#888")

    fig3 = px.pie(
        val_counts, values="Count", names="Label",
        color="Value",
        color_discrete_map={v: colour_map.get(v,"#888") for v in val_counts["Value"]},
        title="Observation Value Breakdown", hole=0.4,
    )
    fig3.update_layout(height=320, margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig3, use_container_width=True)

    # ── Pattern insights ──────────────────────────────────────────────────
    st.markdown("### 💡 Pattern Insights")
    insights = []

    peak_time_row = time_counts.loc[time_counts["count"].idxmax()]
    insights.append(("warn" if peak_time_row["count"] >= 3 else "ok",
        f"{'⚠️' if peak_time_row['count'] >= 3 else '📊'} "
        f"<b>{peak_time_row['label'].strip()}</b> has the most observations "
        f"({int(peak_time_row['count'])} total). "
        + ("Consider proactive strategies at this time." if peak_time_row["count"] >= 3 else "")))

    if n_2 > 0:
        pct_multi = round(n_2 / (n_1 + n_2) * 100) if (n_1 + n_2) > 0 else 0
        insights.append(("warn",
            f"🔴 {n_2} intervals had <b>multiple occurrences</b> — "
            f"{pct_multi}% of all behaviour intervals. "
            "These are priority times for proactive support planning."))

    # Morning vs afternoon
    filtered["hour"] = filtered["time_slot"].apply(
        lambda t: int(str(t).split(":")[0]) if ":" in str(t) else 9
    )
    morn = (filtered["hour"] < 12).sum()
    arvo = (filtered["hour"] >= 12).sum()
    if morn > arvo * 1.5 and total >= 4:
        insights.append(("warn",
            f"🌅 Behaviour is concentrated in the <b>morning</b> ({morn} vs {arvo} afternoon observations). "
            "Review morning routine and arrival conditions."))
    elif arvo > morn * 1.5 and total >= 4:
        insights.append(("warn",
            f"🌇 Behaviour is concentrated in the <b>afternoon</b> ({arvo} vs {morn} morning observations). "
            "Consider fatigue, hunger, or activity demand levels post-lunch."))

    zero_count_days = days_span - len(daily)
    if zero_count_days > 0:
        insights.append(("ok",
            f"✅ {zero_count_days} day(s) in the range had no observations recorded. "
            "Reflect on what conditions were different on those days."))

    for kind, text in insights:
        css = "insight" if kind == "warn" else "insight insight-ok"
        st.markdown(f"<div class='{css}'>{text}</div>", unsafe_allow_html=True)

    # ── Download ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Download Data")
    dl_cols = ["obs_date","time_slot","activity","value","notes","target_behaviours","created_by","created_at"]
    dl_df   = filtered[[c for c in dl_cols if c in filtered.columns]].copy()
    dl_df["obs_date"] = dl_df["obs_date"].dt.strftime("%-d/%m/%Y")
    csv = dl_df.to_csv(index=False)
    st.download_button(
        "📥 Download as CSV",
        csv,
        file_name=f"ScatterPlot_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.dataframe(dl_df, use_container_width=True, hide_index=True)
