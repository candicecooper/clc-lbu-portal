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
    """Insert a new observation or update an existing one.
    Falls back to a minimal row if the behaviour_index/label columns don't exist yet.
    Stores any error in session state so it survives st.rerun()."""
    sb = get_sb()
    if not sb:
        st.session_state["_spt_last_error"] = "Supabase not configured — check secrets."
        return False

    # Full row including new columns
    row = {
        "student_id":        student_id,
        "student_name":      student_name,
        "obs_date":          sel_date.isoformat(),
        "day_of_week":       sel_day,
        "time_slot":         sel_time,
        "activity":          activity,
        "value":             value,
        "behaviour_index":   beh_index,
        "behaviour_label":   beh_label,
        "target_behaviours": behaviours_str,
        "created_by":        get_staff_name(),
    }
    # Minimal row — used as fallback if new columns not yet added via SQL
    row_minimal = {k: v for k, v in row.items()
                   if k not in ("behaviour_index", "behaviour_label")}

    try:
        if existing_id:
            sb.table("scatter_plot_observations").update(
                {"value": value, "behaviour_label": beh_label}
            ).eq("id", existing_id).execute()
        else:
            sb.table("scatter_plot_observations").insert(row).execute()
        st.session_state.pop("_spt_last_error", None)
        return True
    except Exception as e:
        err_str = str(e)
        # If error is about missing columns, retry with minimal row
        if "behaviour_index" in err_str or "behaviour_label" in err_str or "column" in err_str.lower():
            try:
                if existing_id:
                    sb.table("scatter_plot_observations").update(
                        {"value": value}
                    ).eq("id", existing_id).execute()
                else:
                    sb.table("scatter_plot_observations").insert(row_minimal).execute()
                st.session_state["_spt_last_error"] = (
                    "⚠️ Saved without behaviour tracking — run scatter_v4_schema.sql "
                    "in Supabase to enable full 2-behaviour support."
                )
                return True
            except Exception as e2:
                st.session_state["_spt_last_error"] = f"Save failed: {e2}"
                return False
        st.session_state["_spt_last_error"] = f"Save failed: {err_str}"
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

    # Show any persistent save error (survives rerun)
    _err = st.session_state.get("_spt_last_error")
    if _err:
        if _err.startswith("⚠️"):
            st.warning(_err)
        else:
            st.error(_err)
        if st.button("Dismiss", key="spt_dismiss_err"):
            st.session_state.pop("_spt_last_error", None)
            st.rerun()

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
                ok = upsert_obs(student_id, student_name, sel_date, sel_day,
                           sel_time, sel_activity, "1", bi, beh,
                           " | ".join(behaviours),
                           existing_id=existing["id"] if existing else None)
                st.rerun()  # always rerun — error stored in session state if failed
        with rc3:
            if st.button("2", key=f"spt_b{bi}_2", use_container_width=True):
                ok = upsert_obs(student_id, student_name, sel_date, sel_day,
                           sel_time, sel_activity, "2", bi, beh,
                           " | ".join(behaviours),
                           existing_id=existing["id"] if existing else None)
                st.rerun()
        with rc4:
            if st.button("X", key=f"spt_b{bi}_x", use_container_width=True):
                ok = upsert_obs(student_id, student_name, sel_date, sel_day,
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

    # Build ordered time slot list for y-axis (schedule order, top = earliest)
    sched_times = [s["time"] for s in schedule]
    def _sort_key(t):
        try: h,m = str(t).split(":"); return int(h)*60+int(m)
        except: return 999
    sched_times_sorted = sorted(set(sched_times), key=_sort_key)
    # Map time -> "HH:MM  Activity" label
    time_labels = {
        s["time"]: f"{s['time']}  {s['activity']}" for s in schedule
    }

    for bi, abtab in enumerate(an_tabs[:-1]):
        with abtab:
            b_filt = filt[filt["behaviour_index"] == bi].copy() \
                if "behaviour_index" in filt.columns \
                else filt[filt.get("behaviour_label","") == behaviours[bi]].copy()

            if b_filt.empty:
                st.info("No observations for this behaviour in the selected range.")
                continue

            inc = b_filt[b_filt["value"].isin(["1","2"])].copy()
            n1  = int((b_filt["value"]=="1").sum())
            n2  = int((b_filt["value"]=="2").sum())
            nx  = int((b_filt["value"]=="X").sum())

            k1,k2,k3,k4 = st.columns(4)
            k1.markdown(f"<div class='kpi'><div class='val'>{len(b_filt)}</div><div class='lbl'>Total recorded</div></div>", unsafe_allow_html=True)
            k2.markdown(f"<div class='kpi'><div class='val'>{n1}</div><div class='lbl'>Single (1)</div></div>", unsafe_allow_html=True)
            k3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n2}</div><div class='lbl'>Multiple (2)</div></div>", unsafe_allow_html=True)
            k4.markdown(f"<div class='kpi'><div class='val'>{n1+n2}</div><div class='lbl'>Incident intervals</div></div>", unsafe_allow_html=True)

            if inc.empty:
                st.info("No incidents (1 or 2) recorded for this behaviour in the selected range.")
                continue

            st.markdown("---")

            # ── MAIN SCATTER PLOT ────────────────────────────────────────────
            # X = date, Y = time slot (reversed so earliest is at top)
            # Size = weight (1 → small, 2 → large)
            # Colour = value

            inc["date_str"]    = inc["obs_date_dt"].dt.strftime("%a %-d %b")
            inc["date_order"]  = inc["obs_date_dt"].dt.date  # for sorting
            inc["time_label"]  = inc["time_slot"].map(time_labels).fillna(inc["time_slot"])
            inc["size_val"]    = inc["value"].map({"1": 18, "2": 32}).fillna(18)
            inc["colour_val"]  = inc["value"].map({"1": "#3b82f6", "2": "#ef4444"}).fillna("#3b82f6")
            inc["hover_label"] = (
                inc["date_str"] + "<br>" +
                inc["time_label"] + "<br>" +
                inc["value"].map({"1":"Single occurrence","2":"Multiple occurrences"}).fillna(inc["value"]) +
                inc["day_of_week"].apply(lambda d: f"<br>{d}")
            )

            # Y-axis order: schedule order, earliest at top
            all_time_slots = inc["time_slot"].unique().tolist()
            ordered_slots  = [t for t in sched_times_sorted if t in all_time_slots]
            ordered_slots += [t for t in all_time_slots if t not in ordered_slots]
            ordered_labels = [time_labels.get(t, t) for t in ordered_slots]

            # Split into 1s and 2s for separate traces (different colour + size)
            inc1 = inc[inc["value"]=="1"]
            inc2 = inc[inc["value"]=="2"]

            fig_scatter = go.Figure()

            if not inc1.empty:
                fig_scatter.add_trace(go.Scatter(
                    x=inc1["date_str"],
                    y=inc1["time_label"],
                    mode="markers",
                    name="1 — single occurrence",
                    marker=dict(
                        size=16,
                        color="#3b82f6",
                        opacity=0.85,
                        line=dict(color="white", width=1.5),
                        symbol="circle",
                    ),
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=inc1["hover_label"],
                ))

            if not inc2.empty:
                fig_scatter.add_trace(go.Scatter(
                    x=inc2["date_str"],
                    y=inc2["time_label"],
                    mode="markers",
                    name="2 — multiple occurrences",
                    marker=dict(
                        size=26,
                        color="#ef4444",
                        opacity=0.85,
                        line=dict(color="white", width=2),
                        symbol="circle",
                    ),
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=inc2["hover_label"],
                ))

            # X-axis: sorted by date
            date_order = sorted(inc["date_str"].unique(),
                                key=lambda s: inc.loc[inc["date_str"]==s, "date_order"].min())

            fig_scatter.update_layout(
                title=dict(
                    text=f"Scatter Plot — {behaviours[bi]}",
                    font=dict(size=14, color="#0f172a"),
                    x=0,
                ),
                height=max(420, len(ordered_labels) * 28 + 120),
                xaxis=dict(
                    title="Date",
                    categoryorder="array",
                    categoryarray=date_order,
                    showgrid=True,
                    gridcolor="#e2e8f0",
                    tickfont=dict(size=11),
                    side="top",           # dates along the top, like a timetable
                ),
                yaxis=dict(
                    title="",
                    categoryorder="array",
                    categoryarray=ordered_labels[::-1],  # earliest at top
                    showgrid=True,
                    gridcolor="#e2e8f0",
                    tickfont=dict(size=11),
                    automargin=True,
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0, font=dict(size=11),
                ),
                margin=dict(l=10, r=20, t=80, b=20),
                hovermode="closest",
            )

            # Highlight cells that appear on multiple days (hotspots)
            hotspot_slots = inc.groupby("time_label")["date_order"].nunique()
            hotspot_slots = hotspot_slots[hotspot_slots >= 3].index.tolist()
            for hs in hotspot_slots:
                fig_scatter.add_hrect(
                    y0=hs, y1=hs,
                    fillcolor=AMBER, opacity=0.08,
                    layer="below", line_width=0,
                )

            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption(
                "● Small blue = single occurrence (1)  &nbsp;·&nbsp;  "
                "● Large red = multiple occurrences (2)  &nbsp;·&nbsp;  "
                "Dates run left to right along the top, time slots run top to bottom."
            )

            st.markdown("---")

            # ── FREQUENCY SUMMARY CHARTS ─────────────────────────────────────
            col_a, col_b = st.columns(2)

            with col_a:
                # Daily frequency bar
                daily = inc.groupby(inc["obs_date_dt"].dt.date).size().reset_index(name="count")
                daily["date_str"] = pd.to_datetime(daily["obs_date_dt"]).dt.strftime("%-d %b")
                fig_daily = go.Figure(go.Bar(
                    x=daily["date_str"], y=daily["count"],
                    marker_color=[AMBER if v>=3 else TEAL for v in daily["count"]],
                    text=daily["count"], textposition="outside",
                ))
                fig_daily.update_layout(
                    title="Incidents per day",
                    height=260, showlegend=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    yaxis=dict(tickformat="d", gridcolor="#e2e8f0"),
                    margin=dict(l=10,r=10,t=45,b=10),
                )
                st.plotly_chart(fig_daily, use_container_width=True)

            with col_b:
                # By day of week
                dow = inc.groupby("day_of_week").size().reindex(DAYS, fill_value=0)
                fig_dow = go.Figure(go.Bar(
                    x=dow.index, y=dow.values, marker_color=TEAL,
                    text=dow.values, textposition="outside",
                ))
                fig_dow.update_layout(
                    title="Incidents by day of week",
                    height=260, showlegend=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    yaxis=dict(tickformat="d", gridcolor="#e2e8f0"),
                    margin=dict(l=10,r=10,t=45,b=10),
                )
                st.plotly_chart(fig_dow, use_container_width=True)

            # Hotspot time slots table
            slot_counts = inc.groupby("time_label")["value"].agg(
                total="count",
                single=lambda x: (x=="1").sum(),
                multiple=lambda x: (x=="2").sum(),
                days=lambda x: inc.loc[x.index, "day_of_week"].nunique(),
            ).reset_index().sort_values("total", ascending=False)
            slot_counts.columns = ["Time Slot","Total intervals","Single (1)","Multiple (2)","Days affected"]
            st.markdown("**Hotspot summary by time slot:**")
            st.dataframe(slot_counts, use_container_width=True, hide_index=True)

            # Pattern insights
            st.markdown("**💡 Pattern insights:**")
            if not slot_counts.empty:
                top = slot_counts.iloc[0]
                if top["Total intervals"] >= 3:
                    st.markdown(
                        f'<div class="ins">⚠️ <b>{top["Time Slot"].strip()}</b> — '
                        f'{int(top["Total intervals"])} incident intervals across '
                        f'{int(top["Days affected"])} day(s). '
                        "Consider proactive strategies or environmental changes at this time.</div>",
                        unsafe_allow_html=True
                    )
            morn = inc["time_slot"].apply(
                lambda t: int(str(t).split(":")[0]) < 12 if ":" in str(t) else False
            ).sum()
            arvo = len(inc) - morn
            if len(inc) >= 4:
                if morn > arvo * 1.5:
                    st.markdown(
                        f'<div class="ins">🌅 Incidents concentrated in the <b>morning</b> '                        f'({morn} vs {arvo} afternoon). Review arrival routine and morning transitions.</div>',
                        unsafe_allow_html=True
                    )
                elif arvo > morn * 1.5:
                    st.markdown(
                        f'<div class="ins">🌇 Incidents concentrated in the <b>afternoon</b> '                        f'({arvo} vs {morn} morning). Consider fatigue and post-lunch demand levels.</div>',
                        unsafe_allow_html=True
                    )
            if n2 > 0 and (n1+n2) > 0:
                pct = round(n2/(n1+n2)*100)
                if pct > 30:
                    st.markdown(
                        f'<div class="ins">🔴 {pct}% of intervals were <b>multiple occurrences (2)</b>. '                        f'These are high-priority intervals for targeted support.</div>',
                        unsafe_allow_html=True
                    )
            zero_days = [d for d in DAYS if dow.get(d,0) == 0]
            if zero_days and len(inc) >= 3:
                st.markdown(
                    f'<div class="ins ins-ok">✅ No incidents on <b>{", ".join(zero_days)}</b>. '                    f'Reflect on what conditions were different and consider replicating them.</div>',
                    unsafe_allow_html=True
                )

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
