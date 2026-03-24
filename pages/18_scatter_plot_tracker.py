# ════════════════════════════════════════════════════════════════════════════
# 18_Scatter_Plot_Tracker.py  ·  CLC-LBU Portal
# Scatter Plot Tracker — fast in-the-moment grid entry
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import json

from auth import require_auth, logout_button, get_staff_name
require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
logout_button()

TEAL  = "#1A6B8A"
AMBER = "#D4860A"
GREEN = "#2E7D32"

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:#f5f8fa; }}
.clc-header {{
    background: linear-gradient(135deg,{TEAL} 0%,{TEAL}BB 100%);
    color:white; padding:.85rem 1.5rem; border-radius:10px; margin-bottom:1rem;
}}
.clc-header h2 {{ margin:0; font-size:1.25rem; }}
.clc-header p  {{ margin:.2rem 0 0; opacity:.85; font-size:.78rem; }}
.quick-strip {{
    background:white; border:2px solid {TEAL}; border-radius:10px;
    padding:.75rem 1rem; margin-bottom:.75rem;
}}
.grid-table {{ width:100%; border-collapse:collapse; font-size:.82rem; margin-bottom:.5rem; }}
.grid-table th {{
    background:{TEAL}; color:white; padding:.4rem .5rem;
    text-align:center; font-size:.72rem; font-weight:600;
    white-space:nowrap;
}}
.grid-table th.time-col {{ text-align:left; min-width:55px; }}
.grid-table th.act-col  {{ text-align:left; min-width:120px; }}
.grid-table td {{
    padding:.28rem .4rem; border:1px solid #e2e8f0;
    text-align:center; font-size:.82rem; vertical-align:middle;
}}
.grid-table td.time-lbl {{
    text-align:left; font-weight:600; color:#334155;
    font-size:.75rem; white-space:nowrap; background:#f8fafc;
}}
.grid-table td.act-lbl {{
    text-align:left; color:#64748b; font-size:.72rem;
    background:#f8fafc;
}}
.cell-1  {{ background:#dbeafe; color:#1d4ed8; font-weight:700; }}
.cell-2  {{ background:#fee2e2; color:#b91c1c; font-weight:700; }}
.cell-x  {{ background:#f3f4f6; color:#9ca3af; font-weight:600; }}
.cell-empty {{ background:white; }}
.kpi {{ background:white; border-left:4px solid {TEAL}; border-radius:6px;
        padding:.45rem .75rem; text-align:center; }}
.kpi .val {{ font-size:1.5rem; font-weight:700; color:{TEAL}; line-height:1.1; }}
.kpi .lbl {{ font-size:.68rem; color:#666; }}
.kpi-a {{ border-color:{AMBER}; }}
.kpi-a .val {{ color:{AMBER}; }}
.insight {{ background:#FEF9EC; border-left:4px solid {AMBER};
            border-radius:6px; padding:.5rem .9rem; font-size:.83rem; margin-bottom:.35rem; }}
.insight-ok {{ background:#F0FAF4; border-left:4px solid #2EA056; }}
.key-legend {{
    display:flex; gap:.75rem; align-items:center;
    font-size:.75rem; margin-bottom:.5rem; flex-wrap:wrap;
}}
.k-pill {{
    padding:.15rem .55rem; border-radius:12px; font-weight:700; font-size:.72rem;
}}
</style>
""", unsafe_allow_html=True)

# ── Default schedule ──────────────────────────────────────────────────────────
DEFAULT_SCHEDULE = [
    {"time": "9:00",  "activity": "De-escalation activity"},
    {"time": "9:15",  "activity": "Interoception"},
    {"time": "9:20",  "activity": "Activity"},
    {"time": "10:00", "activity": "Breakfast"},
    {"time": "10:05", "activity": "Fitness"},
    {"time": "10:20", "activity": "Quiet Time"},
    {"time": "10:30", "activity": "Activity"},
    {"time": "11:00", "activity": "Recess"},
    {"time": "11:30", "activity": "Quiet Time"},
    {"time": "11:40", "activity": "Activity"},
    {"time": "12:30", "activity": "Activity"},
    {"time": "12:50", "activity": "Lunch eating"},
    {"time": "13:00", "activity": "Lunch"},
    {"time": "13:30", "activity": "Quiet Time"},
    {"time": "13:45", "activity": "I.C.T."},
    {"time": "14:30", "activity": "Home"},
]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


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
        res = sb.table("students").select("id,name,program").eq("archived", False).order("name").execute()
        return res.data or []
    except Exception:
        return []


def load_obs_for_week(student_id: str, week_start: date, week_end: date) -> pd.DataFrame:
    sb = get_sb()
    if not sb:
        return pd.DataFrame()
    try:
        res = (sb.table("scatter_plot_observations")
               .select("*")
               .eq("student_id", student_id)
               .gte("obs_date", str(week_start))
               .lte("obs_date", str(week_end))
               .execute())
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Load error: {e}")
        return pd.DataFrame()


def load_all_obs(student_id: str) -> pd.DataFrame:
    sb = get_sb()
    if not sb:
        return pd.DataFrame()
    try:
        res = (sb.table("scatter_plot_observations")
               .select("*")
               .eq("student_id", student_id)
               .order("obs_date").order("time_slot")
               .execute())
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def save_obs(row: dict) -> bool:
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


def update_obs_value(obs_id: str, new_value: str) -> bool:
    sb = get_sb()
    if not sb:
        return False
    try:
        sb.table("scatter_plot_observations").update({"value": new_value}).eq("id", obs_id).execute()
        return True
    except Exception:
        return False


def delete_obs(obs_id: str) -> bool:
    sb = get_sb()
    if not sb:
        return False
    try:
        sb.table("scatter_plot_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception:
        return False


def load_schedule(student_id: str) -> list:
    """Load per-student schedule from Supabase, fallback to default."""
    sb = get_sb()
    if not sb:
        return DEFAULT_SCHEDULE.copy()
    try:
        res = (sb.table("scatter_plot_schedules")
               .select("schedule")
               .eq("student_id", student_id)
               .limit(1)
               .execute())
        if res.data:
            raw = res.data[0]["schedule"]
            return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        pass
    return DEFAULT_SCHEDULE.copy()


def save_schedule(student_id: str, schedule: list):
    sb = get_sb()
    if not sb:
        return
    try:
        data = {"student_id": student_id, "schedule": json.dumps(schedule)}
        existing = sb.table("scatter_plot_schedules").select("id").eq("student_id", student_id).execute()
        if existing.data:
            sb.table("scatter_plot_schedules").update(data).eq("student_id", student_id).execute()
        else:
            sb.table("scatter_plot_schedules").insert(data).execute()
    except Exception:
        pass


# ── Session state ─────────────────────────────────────────────────────────────
if "spt_student_id"   not in st.session_state: st.session_state.spt_student_id   = None
if "spt_student_name" not in st.session_state: st.session_state.spt_student_name = ""
if "spt_behaviours"   not in st.session_state: st.session_state.spt_behaviours   = ""
if "spt_week_start"   not in st.session_state:
    today = date.today()
    st.session_state.spt_week_start = today - timedelta(days=today.weekday())
if "spt_schedule"     not in st.session_state: st.session_state.spt_schedule     = None
if "spt_edit_cell"    not in st.session_state: st.session_state.spt_edit_cell    = None  # (time, day)
if "spt_confirm_del"  not in st.session_state: st.session_state.spt_confirm_del  = None


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="clc-header">
  <h2>📊 Scatter Plot Tracker</h2>
  <p>Record targeted behaviour frequency across the school day
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STUDENT + BEHAVIOUR selector (always visible at top)
# ════════════════════════════════════════════════════════════════════════════
students = load_students_cached()
if not students:
    st.warning("No students found. Add students via the Behaviour Support tool first.")
    st.stop()

student_opts = {s["id"]: f"{s['name']}  ({s.get('program','')})" for s in students}
ids     = list(student_opts.keys())
cur_idx = ids.index(st.session_state.spt_student_id) if st.session_state.spt_student_id in ids else 0

hc1, hc2 = st.columns([2, 3])
with hc1:
    selected_id = st.selectbox(
        "Student", ids, index=cur_idx,
        format_func=lambda x: student_opts[x],
        key="spt_stu_sel"
    )
with hc2:
    st.session_state.spt_behaviours = st.text_input(
        "Target behaviour(s)",
        value=st.session_state.spt_behaviours,
        placeholder="e.g. Roaming instead of participating",
        key="spt_beh_input"
    )

# Detect student change
if selected_id != st.session_state.spt_student_id:
    st.session_state.spt_student_id   = selected_id
    st.session_state.spt_student_name = next((s["name"] for s in students if s["id"] == selected_id), "")
    st.session_state.spt_schedule     = None  # reload schedule for new student
    st.session_state.spt_edit_cell    = None
    st.rerun()

student_id   = st.session_state.spt_student_id
student_name = st.session_state.spt_student_name or student_opts.get(student_id,"")

# Load schedule for this student (cached in session state)
if st.session_state.spt_schedule is None:
    st.session_state.spt_schedule = load_schedule(student_id)
schedule = st.session_state.spt_schedule

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# TABS: Record / Analysis
# ════════════════════════════════════════════════════════════════════════════
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis & Download"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — RECORD & VIEW
# ════════════════════════════════════════════════════════════════════════════
with t_record:

    # ── Week navigation ───────────────────────────────────────────────────
    week_start = st.session_state.spt_week_start
    week_end   = week_start + timedelta(days=4)

    wc1, wc2, wc3, wc4 = st.columns([1, 3, 1, 1])
    with wc1:
        if st.button("← Prev", use_container_width=True, key="spt_prev"):
            st.session_state.spt_week_start -= timedelta(weeks=1)
            st.session_state.spt_edit_cell   = None
            st.rerun()
    with wc2:
        this_week = date.today() - timedelta(days=date.today().weekday())
        is_this   = week_start == this_week
        st.markdown(
            f'<div style="text-align:center;padding:.4rem 0;font-weight:700;'
            f'color:{TEAL};font-size:.9rem;">'
            f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
            + (' &nbsp;<span style="background:#dbeafe;color:#1d4ed8;font-size:.7rem;'
               'padding:.1rem .5rem;border-radius:10px;">This week</span>' if is_this else '')
            + '</div>',
            unsafe_allow_html=True
        )
    with wc3:
        if st.button("Next →", use_container_width=True, key="spt_next"):
            st.session_state.spt_week_start += timedelta(weeks=1)
            st.session_state.spt_edit_cell   = None
            st.rerun()
    with wc4:
        if st.button("Today", use_container_width=True, key="spt_today"):
            today = date.today()
            st.session_state.spt_week_start = today - timedelta(days=today.weekday())
            st.session_state.spt_edit_cell  = None
            st.rerun()

    # Load this week's observations
    week_obs = load_obs_for_week(student_id, week_start, week_end)

    # Build lookup: {time_slot: {day: {id, value}}}
    cell_data = {}
    if not week_obs.empty:
        for _, row in week_obs.iterrows():
            t  = row["time_slot"]
            d  = row.get("day_of_week", "")
            # If day_of_week column not present, derive from obs_date
            if not d:
                try:
                    d = DAYS[pd.to_datetime(row["obs_date"]).weekday()]
                except Exception:
                    continue
            if t not in cell_data:
                cell_data[t] = {}
            cell_data[t][d] = {"id": row["id"], "value": row["value"]}

    # ── Legend ────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="key-legend">'
        '<b style="font-size:.75rem;">Key:</b>'
        '<span class="k-pill" style="background:#dbeafe;color:#1d4ed8;">1</span>'
        '<span style="font-size:.72rem;">one occurrence</span>'
        '<span class="k-pill" style="background:#fee2e2;color:#b91c1c;">2</span>'
        '<span style="font-size:.72rem;">more than one</span>'
        '<span class="k-pill" style="background:#f3f4f6;color:#9ca3af;">X</span>'
        '<span style="font-size:.72rem;">evacuation / unable to observe</span>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Grid ──────────────────────────────────────────────────────────────
    # Build HTML grid
    day_dates = {
        DAYS[i]: (week_start + timedelta(days=i)).strftime("%-d/%m")
        for i in range(5)
    }
    today_day = DAYS[date.today().weekday()] if date.today().weekday() < 5 else None

    th_cells = '<th class="time-col">Time</th><th class="act-col">Activity</th>'
    for d in DAYS:
        is_today = (d == today_day and is_this)
        style = f' style="background:{"#1a4d8a" if is_today else TEAL};"'
        th_cells += f'<th{style}>{d[:3]}<br><span style="font-weight:400;font-size:.65rem;">{day_dates[d]}</span></th>'

    rows_html = ""
    for slot in schedule:
        t   = slot["time"]
        act = slot["activity"]
        rows_html += f'<tr><td class="time-lbl">{t}</td><td class="act-lbl">{act}</td>'
        for d in DAYS:
            cell = cell_data.get(t, {}).get(d)
            if cell:
                v   = cell["value"]
                cls = f"cell-{v.lower()}" if v in ["1","2","X"] else "cell-empty"
                rows_html += f'<td class="{cls}">{v}</td>'
            else:
                rows_html += '<td class="cell-empty"></td>'
        rows_html += "</tr>"

    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:.75rem;">'
        f'<table class="grid-table"><thead><tr>{th_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True
    )

    # ── Daily totals ──────────────────────────────────────────────────────
    if not week_obs.empty:
        # Derive day from obs_date if day_of_week column missing
        if "day_of_week" not in week_obs.columns or week_obs["day_of_week"].isna().all():
            week_obs["day_of_week"] = week_obs["obs_date"].apply(
                lambda x: DAYS[pd.to_datetime(x).weekday()] if pd.to_datetime(x).weekday() < 5 else ""
            )
        tc = st.columns(6)
        grand = 0
        for i, d in enumerate(DAYS):
            n = week_obs[
                (week_obs["day_of_week"] == d) &
                (week_obs["value"].isin(["1","2"]))
            ].shape[0]
            grand += n
            tc[i].markdown(
                f"<div class='kpi'><div class='val'>{n}</div><div class='lbl'>{d[:3]}</div></div>",
                unsafe_allow_html=True
            )
        tc[5].markdown(
            f"<div class='kpi kpi-a'><div class='val'>{grand}</div><div class='lbl'>Week total</div></div>",
            unsafe_allow_html=True
        )

    # ── QUICK ENTRY STRIP ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**➕ Record an observation**")

    # Pre-fill from edit_cell if set
    ec = st.session_state.spt_edit_cell
    pre_time = ec[0] if ec else schedule[0]["time"] if schedule else "9:00"
    pre_day  = ec[1] if ec else (today_day or DAYS[0])

    slot_times = [s["time"] for s in schedule]
    try:    pre_time_idx = slot_times.index(pre_time)
    except: pre_time_idx = 0
    try:    pre_day_idx  = DAYS.index(pre_day)
    except: pre_day_idx  = 0

    qc1, qc2, qc3, qc4, qc5 = st.columns([2, 2, 1, 1, 1])
    with qc1:
        sel_time = st.selectbox(
            "Time slot", slot_times, index=pre_time_idx,
            key="spt_q_time"
        )
    with qc2:
        sel_day  = st.selectbox(
            "Day", DAYS, index=pre_day_idx,
            key="spt_q_day"
        )
    with qc3:
        st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
        if st.button("**1**", use_container_width=True, key="spt_btn_1",
                     help="One occurrence", type="primary"):
            sel_date = week_start + timedelta(days=DAYS.index(sel_day))
            # Check if entry already exists for this cell
            existing = cell_data.get(sel_time, {}).get(sel_day)
            if existing:
                update_obs_value(existing["id"], "1")
            else:
                save_obs({
                    "student_id":        student_id,
                    "student_name":      student_name,
                    "obs_date":          sel_date.isoformat(),
                    "day_of_week":       sel_day,
                    "time_slot":         sel_time,
                    "activity":          next((s["activity"] for s in schedule if s["time"]==sel_time),""),
                    "value":             "1",
                    "target_behaviours": st.session_state.spt_behaviours,
                    "created_by":        get_staff_name(),
                })
            st.session_state.spt_edit_cell = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with qc4:
        st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
        if st.button("**2**", use_container_width=True, key="spt_btn_2",
                     help="More than one occurrence"):
            sel_date = week_start + timedelta(days=DAYS.index(sel_day))
            existing = cell_data.get(sel_time, {}).get(sel_day)
            if existing:
                update_obs_value(existing["id"], "2")
            else:
                save_obs({
                    "student_id":        student_id,
                    "student_name":      student_name,
                    "obs_date":          sel_date.isoformat(),
                    "day_of_week":       sel_day,
                    "time_slot":         sel_time,
                    "activity":          next((s["activity"] for s in schedule if s["time"]==sel_time),""),
                    "value":             "2",
                    "target_behaviours": st.session_state.spt_behaviours,
                    "created_by":        get_staff_name(),
                })
            st.session_state.spt_edit_cell = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with qc5:
        st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
        if st.button("**X**", use_container_width=True, key="spt_btn_x",
                     help="Evacuation / unable to observe"):
            sel_date = week_start + timedelta(days=DAYS.index(sel_day))
            existing = cell_data.get(sel_time, {}).get(sel_day)
            if existing:
                update_obs_value(existing["id"], "X")
            else:
                save_obs({
                    "student_id":        student_id,
                    "student_name":      student_name,
                    "obs_date":          sel_date.isoformat(),
                    "day_of_week":       sel_day,
                    "time_slot":         sel_time,
                    "activity":          next((s["activity"] for s in schedule if s["time"]==sel_time),""),
                    "value":             "X",
                    "target_behaviours": st.session_state.spt_behaviours,
                    "created_by":        get_staff_name(),
                })
            st.session_state.spt_edit_cell = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Delete a cell ─────────────────────────────────────────────────────
    with st.expander("🗑️ Remove an entry"):
        del_times = [t for t in cell_data if cell_data[t]]
        if not del_times:
            st.caption("No entries this week to remove.")
        else:
            dc1, dc2, dc3 = st.columns([2, 2, 1])
            with dc1:
                del_time = st.selectbox("Time slot", del_times, key="spt_del_t")
            with dc2:
                del_days = [d for d in cell_data.get(del_time, {})]
                del_day  = st.selectbox("Day", del_days, key="spt_del_d") if del_days else None
            with dc3:
                st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
                if del_day and st.button("Remove", type="secondary",
                                          use_container_width=True, key="spt_del_btn"):
                    obs_id = cell_data.get(del_time,{}).get(del_day,{}).get("id")
                    if obs_id:
                        delete_obs(obs_id)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Manage Schedule ───────────────────────────────────────────────────
    with st.expander("⚙️ Manage Schedule — add, reorder, or rename time slots"):
        st.caption(
            "This schedule applies to this student. "
            "Changes are saved automatically and persist across sessions."
        )

        sched = st.session_state.spt_schedule
        changed = False

        for i, slot in enumerate(sched):
            sc1, sc2, sc3, sc4, sc5 = st.columns([1.5, 3, 0.6, 0.6, 0.6])
            with sc1:
                new_t = st.text_input(
                    "Time", slot["time"], key=f"sched_t_{i}",
                    label_visibility="collapsed"
                )
            with sc2:
                new_a = st.text_input(
                    "Activity", slot["activity"], key=f"sched_a_{i}",
                    label_visibility="collapsed"
                )
            with sc3:
                if i > 0 and st.button("↑", key=f"sched_up_{i}", help="Move up"):
                    sched[i], sched[i-1] = sched[i-1], sched[i]
                    changed = True
            with sc4:
                if i < len(sched)-1 and st.button("↓", key=f"sched_dn_{i}", help="Move down"):
                    sched[i], sched[i+1] = sched[i+1], sched[i]
                    changed = True
            with sc5:
                if st.button("✕", key=f"sched_del_{i}", help="Remove slot"):
                    sched.pop(i)
                    changed = True

            if new_t != slot["time"] or new_a != slot["activity"]:
                sched[i] = {"time": new_t, "activity": new_a}
                changed = True

            if changed:
                st.session_state.spt_schedule = sched
                save_schedule(student_id, sched)
                st.rerun()

        st.markdown("---")
        st.markdown("**Add a new time slot:**")
        nc1, nc2, nc3 = st.columns([1.5, 3, 1])
        with nc1: new_slot_t = st.text_input("Time", placeholder="e.g. 8:45", key="sched_new_t")
        with nc2: new_slot_a = st.text_input("Activity", placeholder="e.g. Morning meeting", key="sched_new_a")
        with nc3:
            st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
            if st.button("Add", use_container_width=True, key="sched_add_btn"):
                if new_slot_t.strip():
                    sched.append({"time": new_slot_t.strip(), "activity": new_slot_a.strip()})
                    st.session_state.spt_schedule = sched
                    save_schedule(student_id, sched)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if st.button("↺ Reset to default schedule", key="sched_reset"):
            st.session_state.spt_schedule = DEFAULT_SCHEDULE.copy()
            save_schedule(student_id, DEFAULT_SCHEDULE.copy())
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYSIS & DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:
    st.markdown(f"#### {student_name} — Analysis")

    all_obs = load_all_obs(student_id)

    if all_obs.empty:
        st.info("No observations recorded yet.")
        st.stop()

    all_obs["obs_date"] = pd.to_datetime(all_obs["obs_date"])

    if "day_of_week" not in all_obs.columns or all_obs["day_of_week"].isna().all():
        all_obs["day_of_week"] = all_obs["obs_date"].apply(
            lambda x: DAYS[x.weekday()] if x.weekday() < 5 else ""
        )

    # Date filter
    fc1, fc2 = st.columns(2)
    with fc1:
        date_from = st.date_input("From", value=all_obs["obs_date"].min().date(), key="spt_from")
    with fc2:
        date_to   = st.date_input("To",   value=all_obs["obs_date"].max().date(), key="spt_to")

    filt = all_obs[
        (all_obs["obs_date"].dt.date >= date_from) &
        (all_obs["obs_date"].dt.date <= date_to)
    ].copy()

    if filt.empty:
        st.info("No observations in this date range.")
        st.stop()

    total   = len(filt)
    n_1     = (filt["value"]=="1").sum()
    n_2     = (filt["value"]=="2").sum()
    n_x     = (filt["value"]=="X").sum()
    n_inc   = n_1 + n_2

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='kpi'><div class='val'>{total}</div><div class='lbl'>Total recorded</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='val'>{n_1}</div><div class='lbl'>Single (1)</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n_2}</div><div class='lbl'>Multiple (2)</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi'><div class='val'>{n_inc}</div><div class='lbl'>Incident intervals</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # Chart 1: Daily frequency
    daily = filt[filt["value"].isin(["1","2"])].groupby(
        filt["obs_date"].dt.date
    ).size().reset_index(name="count")
    if not daily.empty:
        fig1 = go.Figure(go.Bar(
            x=daily["obs_date"].astype(str),
            y=daily["count"],
            marker_color=[AMBER if v >= 3 else TEAL for v in daily["count"]],
            text=daily["count"], textposition="outside",
        ))
        fig1.update_layout(
            title="Daily Incident Intervals  (amber = 3+ in one day)",
            height=280, showlegend=False,
            plot_bgcolor="#f8fafc", paper_bgcolor="white",
            yaxis=dict(tickformat="d", gridcolor="#e2e8f0"),
            margin=dict(l=10,r=10,t=50,b=10),
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: By time slot
    slot_counts = filt[filt["value"].isin(["1","2"])].groupby("time_slot").size().reset_index(name="count")
    slot_counts["sort_key"] = slot_counts["time_slot"].apply(
        lambda t: int(str(t).split(":")[0])*60 + int(str(t).split(":")[1]) if ":" in str(t) else 999
    )
    slot_counts = slot_counts.sort_values("sort_key")
    slot_counts["label"] = slot_counts["time_slot"].apply(
        lambda t: f"{t}  {next((s['activity'] for s in schedule if s['time']==t), '')}"
    )
    if not slot_counts.empty:
        fig2 = px.bar(
            slot_counts, x="count", y="label", orientation="h",
            color="count", color_continuous_scale=["#90CBE3", TEAL],
            title="Incident Intervals by Time Slot",
            labels={"count":"Intervals","label":""},
        )
        fig2.update_layout(
            height=max(280, len(slot_counts)*26),
            coloraxis_showscale=False,
            plot_bgcolor="#f8fafc", paper_bgcolor="white",
            margin=dict(l=10,r=10,t=50,b=10),
            xaxis=dict(tickformat="d"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: By day of week
    day_counts = filt[filt["value"].isin(["1","2"])].groupby("day_of_week").size().reindex(DAYS, fill_value=0)
    fig3 = go.Figure(go.Bar(
        x=day_counts.index, y=day_counts.values,
        marker_color=TEAL, text=day_counts.values, textposition="outside",
    ))
    fig3.update_layout(
        title="Incident Intervals by Day",
        height=260, showlegend=False,
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0"),
        margin=dict(l=10,r=10,t=50,b=10),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Insights
    st.markdown("### 💡 Pattern Insights")
    insights = []
    if not slot_counts.empty:
        peak = slot_counts.loc[slot_counts["count"].idxmax()]
        if peak["count"] >= 3:
            insights.append(("warn",
                f"⚠️ <b>{peak['label'].strip()}</b> had {int(peak['count'])} incident intervals. "
                "Consider proactive strategies or environmental changes at this time."))

    morn = filt[filt["value"].isin(["1","2"])]["time_slot"].apply(
        lambda t: int(str(t).split(":")[0]) < 12 if ":" in str(t) else False
    ).sum()
    arvo = n_inc - morn
    if n_inc >= 4:
        if morn > arvo * 1.5:
            insights.append(("warn",
                f"🌅 More incidents in the morning ({morn}) than afternoon ({arvo}). "
                "Review morning routine and arrival conditions."))
        elif arvo > morn * 1.5:
            insights.append(("warn",
                f"🌇 More incidents in the afternoon ({arvo}) than morning ({morn}). "
                "Consider fatigue or post-lunch activity demand."))

    if n_2 > 0 and n_inc > 0:
        pct = round(n_2/n_inc*100)
        insights.append(("warn" if pct > 30 else "ok",
            f"{'🔴' if pct > 30 else '📊'} {pct}% of incident intervals were multiple occurrences (2). "
            + ("These are high-priority intervals." if pct > 30 else "")))

    if not insights:
        insights.append(("ok","📊 More data needed for meaningful pattern analysis."))

    for kind, text in insights:
        css = "insight" if kind=="warn" else "insight insight-ok"
        st.markdown(f"<div class='{css}'>{text}</div>", unsafe_allow_html=True)

    # Download
    st.markdown("---")
    dl = filt.copy()
    dl["obs_date"] = dl["obs_date"].dt.strftime("%-d/%m/%Y")
    csv = dl[["obs_date","day_of_week","time_slot","activity","value",
              "target_behaviours","created_by","created_at"]].to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        csv,
        file_name=f"ScatterPlot_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv", use_container_width=True,
    )
