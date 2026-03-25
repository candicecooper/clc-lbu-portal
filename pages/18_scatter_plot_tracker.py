# ════════════════════════════════════════════════════════════════════════════
# 18_Scatter_Plot_Tracker.py  ·  CLC-LBU Portal
# Scatter Plot Tracker — up to 2 behaviours, tab per behaviour, edit-in-place
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

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:#f5f8fa; }}
.clc-header {{
    background:linear-gradient(135deg,{TEAL} 0%,{TEAL}BB 100%);
    color:white; padding:.85rem 1.5rem; border-radius:10px; margin-bottom:1rem;
}}
.clc-header h2 {{ margin:0; font-size:1.25rem; }}
.clc-header p  {{ margin:.2rem 0 0; opacity:.85; font-size:.78rem; }}
.grid-wrap {{ overflow-x:auto; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:.6rem; }}
.sg {{ width:100%; border-collapse:collapse; font-size:.8rem; }}
.sg th {{
    background:{TEAL}; color:white; padding:.38rem .45rem;
    text-align:center; font-size:.7rem; font-weight:600; white-space:nowrap;
}}
.sg th.lh {{ text-align:left; min-width:50px; }}
.sg th.la {{ text-align:left; min-width:110px; }}
.sg td {{ padding:.25rem .35rem; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; }}
.sg td.tl {{ text-align:left; font-weight:600; color:#334155; font-size:.73rem;
             white-space:nowrap; background:#f8fafc; }}
.sg td.al {{ text-align:left; color:#64748b; font-size:.7rem; background:#f8fafc; }}
.c1  {{ background:#dbeafe; color:#1d4ed8; font-weight:700; }}
.c2  {{ background:#fee2e2; color:#b91c1c; font-weight:700; }}
.cx  {{ background:#f3f4f6; color:#9ca3af; font-weight:600; }}
.ce  {{ background:white; color:#ccc; font-size:.65rem; }}
.kpi {{ background:white; border-left:4px solid {TEAL}; border-radius:6px;
        padding:.45rem .75rem; text-align:center; margin-bottom:.4rem; }}
.kpi .val {{ font-size:1.4rem; font-weight:700; color:{TEAL}; }}
.kpi .lbl {{ font-size:.67rem; color:#666; }}
.kpi-a {{ border-color:{AMBER}; }}
.kpi-a .val {{ color:{AMBER}; }}
.ins {{ background:#FEF9EC; border-left:4px solid {AMBER}; border-radius:6px;
        padding:.45rem .85rem; font-size:.82rem; margin-bottom:.3rem; }}
.ins-ok {{ background:#F0FAF4; border-left:4px solid #2EA056; }}
</style>
""", unsafe_allow_html=True)

# ── Default schedule ──────────────────────────────────────────────────────────
DEFAULT_SCHEDULE = [
    {"time":"9:00",  "activity":"De-escalation activity"},
    {"time":"9:15",  "activity":"Interoception"},
    {"time":"9:20",  "activity":"Activity"},
    {"time":"10:00", "activity":"Breakfast"},
    {"time":"10:05", "activity":"Fitness"},
    {"time":"10:20", "activity":"Quiet Time"},
    {"time":"10:30", "activity":"Activity"},
    {"time":"11:00", "activity":"Recess"},
    {"time":"11:30", "activity":"Quiet Time"},
    {"time":"11:40", "activity":"Activity"},
    {"time":"12:30", "activity":"Activity"},
    {"time":"12:50", "activity":"Lunch eating"},
    {"time":"13:00", "activity":"Lunch"},
    {"time":"13:30", "activity":"Quiet Time"},
    {"time":"13:45", "activity":"I.C.T."},
    {"time":"14:30", "activity":"Home"},
]
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]


# ── Supabase helpers ──────────────────────────────────────────────────────────
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


@st.cache_data(ttl=60)
def load_students_cached():
    sb = get_sb()
    if not sb: return []
    try:
        res = sb.table("students").select("id,name,program").eq("archived",False).order("name").execute()
        return res.data or []
    except Exception:
        return []


def load_week_obs(student_id: str, week_start: date, week_end: date) -> pd.DataFrame:
    """Load all observations for this student in the given week."""
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("scatter_plot_observations")
               .select("*")
               .eq("student_id", student_id)
               .gte("obs_date", str(week_start))
               .lte("obs_date", str(week_end))
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            # Always derive day_of_week from obs_date (more reliable than stored value)
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else ""
            )
        return df
    except Exception as e:
        st.error(f"Load error: {e}")
        return pd.DataFrame()


def load_all_obs(student_id: str) -> pd.DataFrame:
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("scatter_plot_observations")
               .select("*")
               .eq("student_id", student_id)
               .order("obs_date").order("time_slot")
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else ""
            )
        return df
    except Exception:
        return pd.DataFrame()


def upsert_obs(student_id, student_name, sel_date, sel_day, sel_time, activity,
               value, beh_index, beh_label, behaviours_str, existing_id=None) -> bool:
    """Insert a new observation or update an existing one."""
    sb = get_sb()
    if not sb:
        st.warning("Supabase not configured.")
        return False
    row = {
        "student_id":        student_id,
        "student_name":      student_name,
        "obs_date":          sel_date.isoformat(),
        "day_of_week":       sel_day,
        "time_slot":         sel_time,
        "activity":          activity,
        "value":             value,
        "behaviour_index":   beh_index,       # 0 or 1
        "behaviour_label":   beh_label,       # the text of this behaviour
        "target_behaviours": behaviours_str,
        "created_by":        get_staff_name(),
    }
    try:
        if existing_id:
            sb.table("scatter_plot_observations").update(
                {"value": value, "behaviour_label": beh_label}
            ).eq("id", existing_id).execute()
        else:
            sb.table("scatter_plot_observations").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False


def delete_obs(obs_id: str) -> bool:
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_plot_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False


def load_schedule(student_id: str) -> list:
    sb = get_sb()
    if not sb: return DEFAULT_SCHEDULE.copy()
    try:
        res = (sb.table("scatter_plot_schedules")
               .select("schedule").eq("student_id", student_id).limit(1).execute())
        if res.data:
            raw = res.data[0]["schedule"]
            return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        pass
    return DEFAULT_SCHEDULE.copy()


def save_schedule(student_id: str, schedule: list):
    sb = get_sb()
    if not sb: return
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
ss = st.session_state
if "spt_student_id"   not in ss: ss.spt_student_id   = None
if "spt_student_name" not in ss: ss.spt_student_name = ""
if "spt_beh1"         not in ss: ss.spt_beh1         = ""
if "spt_beh2"         not in ss: ss.spt_beh2         = ""
if "spt_schedule"     not in ss: ss.spt_schedule     = None
if "spt_week_start"   not in ss:
    today = date.today()
    ss.spt_week_start = today - timedelta(days=today.weekday())


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
# STUDENT + BEHAVIOURS (always visible)
# ════════════════════════════════════════════════════════════════════════════
students     = load_students_cached()
if not students:
    st.warning("No students found. Add students via the Behaviour Support tool first.")
    st.stop()

student_opts = {s["id"]: f"{s['name']}  ({s.get('program','')})" for s in students}
ids     = list(student_opts.keys())
cur_idx = ids.index(ss.spt_student_id) if ss.spt_student_id in ids else 0

hc1, hc2, hc3 = st.columns([2, 2.5, 2.5])
with hc1:
    selected_id = st.selectbox(
        "Student", ids, index=cur_idx,
        format_func=lambda x: student_opts[x],
        key="spt_stu_sel"
    )
with hc2:
    ss.spt_beh1 = st.text_input(
        "Behaviour 1 *",
        value=ss.spt_beh1,
        placeholder="e.g. Roaming instead of participating",
        key="spt_b1"
    )
with hc3:
    ss.spt_beh2 = st.text_input(
        "Behaviour 2 (optional)",
        value=ss.spt_beh2,
        placeholder="e.g. Verbal outbursts",
        key="spt_b2"
    )

# Student change
if selected_id != ss.spt_student_id:
    ss.spt_student_id   = selected_id
    ss.spt_student_name = next((s["name"] for s in students if s["id"]==selected_id),"")
    ss.spt_schedule     = None
    st.rerun()

student_id   = ss.spt_student_id
student_name = ss.spt_student_name or student_opts.get(student_id,"")

# Load schedule
if ss.spt_schedule is None:
    ss.spt_schedule = load_schedule(student_id)
schedule = ss.spt_schedule

# Behaviours list (only defined ones)
behaviours = [b for b in [ss.spt_beh1.strip(), ss.spt_beh2.strip()] if b]
if not behaviours:
    st.info("Enter at least one target behaviour above to start recording.")
    st.stop()

beh_labels = {i: b for i, b in enumerate(behaviours)}

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# TABS: Record+View  /  Analysis
# ════════════════════════════════════════════════════════════════════════════
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis & Download"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — RECORD & VIEW
# ════════════════════════════════════════════════════════════════════════════
with t_record:

    # ── Week navigation ───────────────────────────────────────────────────
    week_start = ss.spt_week_start
    week_end   = week_start + timedelta(days=4)
    this_week  = date.today() - timedelta(days=date.today().weekday())

    wc1, wc2, wc3, wc4 = st.columns([1,4,1,1])
    with wc1:
        if st.button("← Prev", use_container_width=True, key="spt_prev"):
            ss.spt_week_start -= timedelta(weeks=1); st.rerun()
    with wc2:
        is_this = week_start == this_week
        st.markdown(
            f'<div style="text-align:center;padding:.38rem 0;font-weight:700;color:{TEAL};font-size:.9rem;">'
            f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
            + (' &nbsp;<span style="background:#dbeafe;color:#1d4ed8;font-size:.68rem;'
               'padding:.1rem .45rem;border-radius:10px;">This week</span>' if is_this else '')
            + '</div>',
            unsafe_allow_html=True
        )
    with wc3:
        if st.button("Next →", use_container_width=True, key="spt_next"):
            ss.spt_week_start += timedelta(weeks=1); st.rerun()
    with wc4:
        if st.button("Today", use_container_width=True, key="spt_today"):
            ss.spt_week_start = this_week; st.rerun()

    # Load week data
    week_df = load_week_obs(student_id, week_start, week_end)

    # Build lookup: {beh_index: {time_slot: {day: {id, value}}}}
    cell_data = {i: {} for i in range(len(behaviours))}
    if not week_df.empty:
        for _, row in week_df.iterrows():
            t   = row.get("time_slot","")
            d   = row.get("day_of_week","")
            bi  = int(row.get("behaviour_index", 0))
            rid = row.get("id","")
            val = row.get("value","")
            if not t or not d or bi not in cell_data: continue
            if t not in cell_data[bi]: cell_data[bi][t] = {}
            cell_data[bi][d] = {"id": rid, "value": val, "time": t}
            # Store under time key too for quick lookup
            if t not in cell_data[bi]: cell_data[bi][t] = {}
            cell_data[bi][t][d] = {"id": rid, "value": val}

    # ── Key legend ────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;'
        'font-size:.75rem;margin:.25rem 0 .6rem;">'
        f'<b>Key:</b>'
        '<span style="background:#dbeafe;color:#1d4ed8;padding:.1rem .5rem;'
        'border-radius:12px;font-weight:700;">1</span> one occurrence &nbsp;'
        '<span style="background:#fee2e2;color:#b91c1c;padding:.1rem .5rem;'
        'border-radius:12px;font-weight:700;">2</span> more than one &nbsp;'
        '<span style="background:#f3f4f6;color:#9ca3af;padding:.1rem .5rem;'
        'border-radius:12px;font-weight:700;">X</span> evacuation / unable to observe'
        '</div>',
        unsafe_allow_html=True
    )

    # ── QUICK ENTRY ───────────────────────────────────────────────────────
    st.markdown("**➕ Record an observation**")

    slot_times = [s["time"] for s in schedule]
    today_day  = DAYS[date.today().weekday()] if date.today().weekday() < 5 else DAYS[0]

    # ── Time + Day selectors ─────────────────────────────────────────────
    qc1, qc2 = st.columns([2.5, 2])
    with qc1:
        sel_time = st.selectbox("Time slot", slot_times, key="spt_q_time")
    with qc2:
        sel_day = st.selectbox("Day", DAYS,
            index=DAYS.index(today_day) if today_day in DAYS else 0,
            key="spt_q_day")

    sel_activity = next((s["activity"] for s in schedule if s["time"]==sel_time),"")
    sel_date     = week_start + timedelta(days=DAYS.index(sel_day))

    # ── One button row per behaviour ──────────────────────────────────────
    for bi, beh in enumerate(behaviours):
        existing = cell_data.get(bi,{}).get(sel_time,{}).get(sel_day)
        cur_val  = existing["value"] if existing else ""

        # Behaviour label + current value indicator
        val_colours = {
            "1": "background:#dbeafe;color:#1d4ed8",
            "2": "background:#fee2e2;color:#b91c1c",
            "X": "background:#f3f4f6;color:#6b7280",
        }
        cur_badge = (
            f'<span style="padding:.1rem .45rem;border-radius:8px;font-weight:700;'
            f'{val_colours.get(cur_val,"")};font-size:.75rem;">{cur_val}</span>'
            if cur_val else
            '<span style="color:#ccc;font-size:.72rem;">—</span>'
        )

        rc1, rc2, rc3, rc4, rc5 = st.columns([4, 0.7, 0.7, 0.7, 0.5])
        with rc1:
            st.markdown(
                f'<div style="padding:.55rem 0 .2rem;font-size:.82rem;font-weight:600;'
                f'color:#334155;">B{bi+1}: {beh[:50]}{"…" if len(beh)>50 else ""} '
                f'&nbsp;{cur_badge}</div>',
                unsafe_allow_html=True
            )
        with rc2:
            if st.button("1", key=f"spt_b{bi}_1", use_container_width=True, type="primary"):
                upsert_obs(student_id, student_name, sel_date, sel_day,
                           sel_time, sel_activity, "1", bi, beh,
                           " | ".join(behaviours),
                           existing_id=existing["id"] if existing else None)
                st.rerun()
        with rc3:
            if st.button("2", key=f"spt_b{bi}_2", use_container_width=True):
                upsert_obs(student_id, student_name, sel_date, sel_day,
                           sel_time, sel_activity, "2", bi, beh,
                           " | ".join(behaviours),
                           existing_id=existing["id"] if existing else None)
                st.rerun()
        with rc4:
            if st.button("X", key=f"spt_b{bi}_x", use_container_width=True):
                upsert_obs(student_id, student_name, sel_date, sel_day,
                           sel_time, sel_activity, "X", bi, beh,
                           " | ".join(behaviours),
                           existing_id=existing["id"] if existing else None)
                st.rerun()
        with rc5:
            if cur_val and st.button("✕", key=f"spt_b{bi}_clr",
                                     use_container_width=True, help="Clear this cell"):
                if existing:
                    delete_obs(existing["id"])
                    st.rerun()

    st.markdown("---")

    # ── GRIDS — one tab per behaviour ─────────────────────────────────────
    beh_tabs = st.tabs([f"Behaviour {i+1}: {b[:35]}{'…' if len(b)>35 else ''}"
                        for i, b in enumerate(behaviours)])

    day_dates = {DAYS[i]: (week_start + timedelta(days=i)).strftime("%-d/%m") for i in range(5)}
    today_day_name = DAYS[date.today().weekday()] if date.today().weekday() < 5 else None

    for bi, btab in enumerate(beh_tabs):
        with btab:
            # Build grid HTML
            th = '<th class="lh">Time</th><th class="la">Activity</th>'
            for d in DAYS:
                is_td = (d == today_day_name and is_this)
                bg    = 'background:#1a4d8a;' if is_td else ''
                th   += f'<th style="{bg}">{d[:3]}<br><span style="font-weight:400;font-size:.62rem;">{day_dates[d]}</span></th>'

            rows_html = ""
            for slot in schedule:
                t   = slot["time"]
                act = slot["activity"]
                rows_html += f'<tr><td class="tl">{t}</td><td class="al">{act}</td>'
                for d in DAYS:
                    cell = cell_data.get(bi,{}).get(t,{}).get(d)
                    if cell:
                        v   = cell["value"]
                        cls = {"1":"c1","2":"c2","X":"cx"}.get(v,"ce")
                        rows_html += f'<td class="{cls}">{v}</td>'
                    else:
                        rows_html += '<td class="ce">·</td>'
                rows_html += "</tr>"

            st.markdown(
                f'<div class="grid-wrap"><table class="sg">'
                f'<thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody></table></div>',
                unsafe_allow_html=True
            )

            # Daily totals for this behaviour
            if not week_df.empty:
                beh_week = week_df[week_df.get("behaviour_index", pd.Series(dtype=int)) == bi] \
                    if "behaviour_index" in week_df.columns \
                    else week_df[week_df.get("behaviour_label","") == behaviours[bi]]
                tc = st.columns(6)
                grand = 0
                for i, d in enumerate(DAYS):
                    n = beh_week[
                        (beh_week["day_of_week"]==d) & (beh_week["value"].isin(["1","2"]))
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

    # ── Remove an entry ────────────────────────────────────────────────────
    with st.expander("🗑️ Remove an entry from this week"):
        # Build list of all filled cells
        entries = []
        if not week_df.empty:
            for _, row in week_df.iterrows():
                bi  = int(row.get("behaviour_index", 0))
                beh = behaviours[bi] if bi < len(behaviours) else row.get("behaviour_label","?")
                entries.append({
                    "label": f"B{bi+1} · {row['day_of_week']} {row['time_slot']} — {row['value']}  ({beh[:25]})",
                    "id":    row["id"],
                })
        if not entries:
            st.caption("No entries this week.")
        else:
            dc1, dc2 = st.columns([4,1])
            with dc1:
                chosen = st.selectbox("Select entry to remove",
                                      [e["label"] for e in entries], key="spt_del_sel")
            with dc2:
                st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
                if st.button("Remove", key="spt_del_btn", use_container_width=True):
                    obs_id = next(e["id"] for e in entries if e["label"]==chosen)
                    if delete_obs(obs_id): st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Manage Schedule ────────────────────────────────────────────────────
    with st.expander("⚙️ Manage Schedule — add, reorder, rename time slots"):
        st.caption("Schedule is saved per student and persists across sessions.")
        sched   = ss.spt_schedule
        changed = False

        for i, slot in enumerate(sched):
            sc1, sc2, sc3, sc4, sc5 = st.columns([1.5,3,0.55,0.55,0.55])
            with sc1:
                nt = st.text_input("Time",     slot["time"],     key=f"st_{i}", label_visibility="collapsed")
            with sc2:
                na = st.text_input("Activity", slot["activity"], key=f"sa_{i}", label_visibility="collapsed")
            with sc3:
                if i > 0 and st.button("↑", key=f"su_{i}"):
                    sched[i], sched[i-1] = sched[i-1], sched[i]; changed = True
            with sc4:
                if i < len(sched)-1 and st.button("↓", key=f"sd_{i}"):
                    sched[i], sched[i+1] = sched[i+1], sched[i]; changed = True
            with sc5:
                if st.button("✕", key=f"sx_{i}"):
                    sched.pop(i); changed = True
            if nt != slot["time"] or na != slot["activity"]:
                sched[i] = {"time": nt, "activity": na}; changed = True
            if changed:
                ss.spt_schedule = sched; save_schedule(student_id, sched); st.rerun()

        st.markdown("---")
        st.markdown("**Add a slot:**")
        nc1, nc2, nc3 = st.columns([1.5,3,1])
        with nc1: new_t = st.text_input("Time",     placeholder="e.g. 8:45", key="sched_nt")
        with nc2: new_a = st.text_input("Activity", placeholder="e.g. Morning check-in", key="sched_na")
        with nc3:
            st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
            if st.button("Add", key="sched_add", use_container_width=True):
                if new_t.strip():
                    sched.append({"time":new_t.strip(),"activity":new_a.strip()})
                    ss.spt_schedule = sched; save_schedule(student_id, sched); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        if st.button("↺ Reset to default schedule", key="sched_reset"):
            ss.spt_schedule = DEFAULT_SCHEDULE.copy()
            save_schedule(student_id, DEFAULT_SCHEDULE.copy()); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYSIS & DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:
    st.markdown(f"#### {student_name} — Analysis")

    all_obs = load_all_obs(student_id)
    if all_obs.empty:
        st.info("No observations recorded yet."); st.stop()

    fc1, fc2 = st.columns(2)
    with fc1: date_from = st.date_input("From", value=all_obs["obs_date_dt"].min().date(), key="spt_af")
    with fc2: date_to   = st.date_input("To",   value=all_obs["obs_date_dt"].max().date(), key="spt_at")

    filt = all_obs[
        (all_obs["obs_date_dt"].dt.date >= date_from) &
        (all_obs["obs_date_dt"].dt.date <= date_to)
    ].copy()

    if filt.empty:
        st.info("No observations in this date range."); st.stop()

    # One analysis section per behaviour
    an_tabs = st.tabs([f"Behaviour {i+1}: {b[:40]}" for i,b in enumerate(behaviours)] + ["Combined"])

    for bi, abtab in enumerate(an_tabs[:-1]):
        with abtab:
            b_filt = filt[filt.get("behaviour_index", pd.Series(dtype=object)) == bi] \
                if "behaviour_index" in filt.columns \
                else filt[filt.get("behaviour_label","") == behaviours[bi]]

            if b_filt.empty:
                st.info("No observations for this behaviour in the selected range."); continue

            inc = b_filt[b_filt["value"].isin(["1","2"])]
            n1  = (b_filt["value"]=="1").sum()
            n2  = (b_filt["value"]=="2").sum()
            nx  = (b_filt["value"]=="X").sum()

            k1,k2,k3,k4 = st.columns(4)
            k1.markdown(f"<div class='kpi'><div class='val'>{len(b_filt)}</div><div class='lbl'>Total recorded</div></div>", unsafe_allow_html=True)
            k2.markdown(f"<div class='kpi'><div class='val'>{n1}</div><div class='lbl'>Single (1)</div></div>", unsafe_allow_html=True)
            k3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n2}</div><div class='lbl'>Multiple (2)</div></div>", unsafe_allow_html=True)
            k4.markdown(f"<div class='kpi'><div class='val'>{n1+n2}</div><div class='lbl'>Incident intervals</div></div>", unsafe_allow_html=True)

            if inc.empty: continue

            # Daily frequency
            daily = inc.groupby(inc["obs_date_dt"].dt.date).size().reset_index(name="count")
            fig1 = go.Figure(go.Bar(
                x=[str(d) for d in daily["obs_date_dt"]],
                y=daily["count"],
                marker_color=[AMBER if v>=3 else TEAL for v in daily["count"]],
                text=daily["count"], textposition="outside",
            ))
            fig1.update_layout(title="Daily Incident Intervals", height=250, showlegend=False,
                plot_bgcolor="#f8fafc", paper_bgcolor="white",
                yaxis=dict(tickformat="d",gridcolor="#e2e8f0"), margin=dict(l=10,r=10,t=45,b=10))
            st.plotly_chart(fig1, use_container_width=True)

            # By time slot
            sc = inc.groupby("time_slot").size().reset_index(name="count")
            sc["sort_k"] = sc["time_slot"].apply(
                lambda t: int(str(t).split(":")[0])*60+int(str(t).split(":")[1]) if ":"in str(t) else 999)
            sc = sc.sort_values("sort_k")
            sc["label"] = sc["time_slot"].apply(
                lambda t: f"{t}  {next((s['activity'] for s in schedule if s['time']==t),'')}")
            fig2 = px.bar(sc, x="count", y="label", orientation="h",
                color="count", color_continuous_scale=["#90CBE3",TEAL],
                title="By Time Slot", labels={"count":"Intervals","label":""})
            fig2.update_layout(height=max(240,len(sc)*24),coloraxis_showscale=False,
                plot_bgcolor="#f8fafc",paper_bgcolor="white",
                margin=dict(l=10,r=10,t=45,b=10),xaxis=dict(tickformat="d"))
            st.plotly_chart(fig2, use_container_width=True)

            # By day
            dc = inc.groupby("day_of_week").size().reindex(DAYS, fill_value=0)
            fig3 = go.Figure(go.Bar(x=dc.index, y=dc.values, marker_color=TEAL,
                text=dc.values, textposition="outside"))
            fig3.update_layout(title="By Day", height=240, showlegend=False,
                plot_bgcolor="#f8fafc",paper_bgcolor="white",
                yaxis=dict(tickformat="d",gridcolor="#e2e8f0"),margin=dict(l=10,r=10,t=45,b=10))
            st.plotly_chart(fig3, use_container_width=True)

    # Combined tab
    with an_tabs[-1]:
        inc_all = filt[filt["value"].isin(["1","2"])]
        if inc_all.empty:
            st.info("No incidents recorded.")
        else:
            if "behaviour_index" in inc_all.columns:
                inc_all = inc_all.copy()
                inc_all["Behaviour"] = inc_all["behaviour_index"].apply(
                    lambda i: f"B{int(i)+1}: {behaviours[int(i)][:35]}" if int(i) < len(behaviours) else f"B{int(i)+1}"
                )
            else:
                inc_all = inc_all.copy()
                inc_all["Behaviour"] = inc_all.get("behaviour_label","B1")

            daily_c = inc_all.groupby([inc_all["obs_date_dt"].dt.date,"Behaviour"]).size().reset_index(name="count")
            daily_c["obs_date_dt"] = daily_c["obs_date_dt"].astype(str)
            fig_c = px.bar(daily_c, x="obs_date_dt", y="count", color="Behaviour",
                title="Combined Daily Incident Intervals",
                labels={"obs_date_dt":"Date","count":"Intervals"},
                barmode="stack")
            fig_c.update_layout(height=300,plot_bgcolor="#f8fafc",paper_bgcolor="white",
                margin=dict(l=10,r=10,t=50,b=10),yaxis=dict(tickformat="d"))
            st.plotly_chart(fig_c, use_container_width=True)

    # Download
    st.markdown("---")
    dl = filt.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    csv = dl[["obs_date","day_of_week","time_slot","activity","value",
              "behaviour_index","behaviour_label","target_behaviours","created_by"]].to_csv(index=False)
    st.download_button("📥 Download CSV", csv,
        file_name=f"ScatterPlot_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv", use_container_width=True)
