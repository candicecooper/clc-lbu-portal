# ════════════════════════════════════════════════════════════════════════════
# 27_Interval_Support_Tracker.py  ·  CLC-LBU Portal
# Window of Tolerance interval tracker — regulation state + support per slot
# ════════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime

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
.grid-wrap { overflow-x:auto; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:.6rem; }
.sg { width:100%; border-collapse:collapse; font-size:.78rem; }
.sg th {
    background:#1A6B8A; color:white; padding:.35rem .45rem;
    text-align:center; font-size:.68rem; font-weight:600; white-space:nowrap;
}
.sg th.lh { text-align:left; min-width:48px; }
.sg td { padding:.22rem .3rem; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; font-size:.72rem; }
.sg td.tl { text-align:left; font-weight:600; color:#334155; font-size:.7rem; white-space:nowrap; background:#f8fafc; padding:.22rem .5rem; }
.kpi { background:white; border-left:4px solid #1A6B8A; border-radius:6px;
       padding:.4rem .7rem; text-align:center; margin-bottom:.35rem; }
.kpi .val { font-size:1.3rem; font-weight:700; color:#1A6B8A; }
.kpi .lbl { font-size:.65rem; color:#666; }
.kpi-g { border-color:#16a34a; } .kpi-g .val { color:#16a34a; }
.kpi-y { border-color:#ca8a04; } .kpi-y .val { color:#ca8a04; }
.kpi-r { border-color:#dc2626; } .kpi-r .val { color:#dc2626; }
.kpi-b { border-color:#2563eb; } .kpi-b .val { color:#2563eb; }
.rec-bar {
    background:#EBF4F9; border:1.5px solid #1A6B8A; border-radius:8px;
    padding:.45rem 1rem; margin:.3rem 0 .5rem; font-size:.85rem;
}
</style>
""", unsafe_allow_html=True)

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

# 15-minute intervals 9:00 to 14:30
def _gen_slots():
    slots = []
    t = 9 * 60
    while t <= 14 * 60 + 30:
        slots.append(f"{t//60}:{t%60:02d}")
        t += 15
    return slots
SLOT_TIMES = _gen_slots()

REG_STATES = {
    "in_window":    {"label": "In window",    "emoji": "🟢", "short": "W",   "bg": "#dcfce7", "fg": "#16a34a", "desc": "Regulated — learning ready | Examples: on task, following instructions, engaged with activity, responding to requests, maintaining focus, calm body, appropriate interactions"},
    "coping":       {"label": "Coping",        "emoji": "🟡", "short": "C",   "bg": "#fef9c3", "fg": "#ca8a04", "desc": "At edge — actively managing, dysregulated | Examples: fidgeting, tapping, rocking, making noises, ignoring instructions, moving around, slow to respond, avoiding eye contact, restless, grumbling"},
    "hyperaroused": {"label": "Hyperaroused",  "emoji": "🔴", "short": "H+",  "bg": "#fee2e2", "fg": "#dc2626", "desc": "Above window — fight/flight response | Physiological: dilated pupils, dry mouth, shallow breathing, faster heartbeat, sweating, tensed muscles, butterflies in stomach | Behavioural: agitated movement, unable to find stillness, hyper-vigilant, impulsive, emotionally flooded, reactive, defensive, self-destructive"},
    "hypoaroused":  {"label": "Hypoaroused",   "emoji": "🔵", "short": "H-",  "bg": "#dbeafe", "fg": "#2563eb", "desc": "Below window — shutdown/freeze response | Examples: staring blankly, non-responsive, slumped posture, minimal movement, very slow responses, appearing asleep or zoned out, refusing to engage, head down, monosyllabic or mute"},
}

SUPPORT_TYPES = [
    "None", "1:1 SSO", "1:1 Teacher", "Small group",
    "Visual supports", "Modified task", "Sensory break", "Peer support",
]

GROUPING_TYPES = {
    "1:1":         "1:1",
    "independent": "Independent",
    "small_group": "Small group",
    "large_group": "Large group (≤10)",
    "leadership_intervention": "Leadership intervention",
    "with_parent_carer": "With parent/carer",
}

ACTIVITY_TYPES = [
    "Structured",
    "Unstructured",
    "Yard play",
    "Preferred task",
    "Non-preferred task",
    "Self directed wandering",
    "Transition in",
    "Transition out",
    "Absconding",
    "Other",
]

OUTCOMES = {
    "on_task":           {"label": "On task",           "short": "T",  "bg": "#dcfce7", "fg": "#16a34a"},
    "partial":           {"label": "Partial",           "short": "P",  "bg": "#fef9c3", "fg": "#ca8a04"},
    "escalated":         {"label": "Escalated",         "short": "E",  "bg": "#fee2e2", "fg": "#dc2626"},
    "avoidance":         {"label": "Avoidance",         "short": "A",  "bg": "#fef9c3", "fg": "#ca8a04"},
    "seeking_input":     {"label": "Seeking input",     "short": "SI", "bg": "#dcfce7", "fg": "#16a34a"},
    "seeking_attention":  {"label": "Seeking attention",  "short": "SA", "bg": "#fef9c3", "fg": "#ca8a04"},
    "passive_observation": {"label": "Passive observation", "short": "PO", "bg": "#dcfce7", "fg": "#16a34a"},
}

# ── Saves log vocabulary (prevention / de-escalation) ────────────────────────
# A "save" = an early escalation sign was caught, a support applied, an outcome
# followed. Lists below drive the tap-chips; edit freely to match site language.
SAVE_SIGNS = [
    "Pacing / restless", "Raised voice", "Fidgeting", "Verbal refusal",
    "Withdrawing / quiet", "Seeking to leave", "Physical tension",
    "Escalating language", "Sensory overwhelm",
]

SAVE_SUPPORTS = [
    # Relational / co-regulation
    "Co-regulation / calm presence", "Emotion coaching / PACE",
    # Movement & body
    "Movement break", "Walk and talk", "Food / drink",
    # Task & demand
    "Reduced demand", "Task paused", "Offered choice",
    "Preferred activity", "Group task change",
    # Environment & sensory
    "Change of space", "Quiet / retreat space",
    "Sensory tool", "Reduced sensory input", "Visual support / cue",
    # People & staffing
    "1:1 SSO", "1:1 Teacher", "Carer support",
    "Intentional parent engagement", "Leadership support",
]

SAVE_OUTCOMES = {
    "returned_to_window": {"label": "Returned to window", "emoji": "🟢", "bg": "#dcfce7", "fg": "#16a34a", "success": True},
    "held_in_coping":     {"label": "Held in coping",     "emoji": "🟡", "bg": "#fef9c3", "fg": "#ca8a04", "success": True},
    "escalated_anyway":   {"label": "Escalated anyway",   "emoji": "🔴", "bg": "#fee2e2", "fg": "#dc2626", "success": False},
}


def multi_select_widget(label, options, key, default=None):
    """Tappable multi-select. Prefers st.pills, falls back to multiselect."""
    default = default or []
    if hasattr(st, "pills"):
        return st.pills(label, options, selection_mode="multi", default=default,
                        key=key, label_visibility="collapsed") or []
    return st.multiselect(label, options, default=default, key=key, label_visibility="collapsed")


def single_choice_widget(label, options, key, default=None):
    """Tappable single-select. Prefers segmented_control, then pills, then radio."""
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options, selection_mode="single", default=default,
                                    key=key, label_visibility="collapsed")
    if hasattr(st, "pills"):
        return st.pills(label, options, selection_mode="single", default=default,
                        key=key, label_visibility="collapsed")
    idx = options.index(default) if default in options else None
    return st.radio(label, options, index=idx, key=key,
                    horizontal=True, label_visibility="collapsed")


@st.cache_resource
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


@st.cache_data(ttl=60)
def load_known_students():
    """Returns students with interval data, excluding archived ones."""
    sb = get_sb()
    if not sb: return []
    try:
        res = sb.table("interval_support_observations").select("student_name").execute()
        all_names = sorted({r["student_name"] for r in (res.data or [])
                            if r.get("student_name","").strip()})
        try:
            ar = sb.table("interval_archived_students") \
                   .select("student_name").eq("archived", True).execute()
            archived = {r["student_name"] for r in (ar.data or [])}
            all_names = [n for n in all_names if n not in archived]
        except Exception:
            pass
        return all_names
    except Exception:
        return []


@st.cache_data(ttl=60)
def load_week_obs(student_name, week_start, week_end):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("interval_support_observations")
               .select("*").eq("student_name", student_name)
               .gte("obs_date", str(week_start)).lte("obs_date", str(week_end)).execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception as e:
        st.error("Load error: " + str(e)); return pd.DataFrame()


@st.cache_data(ttl=60)
def load_all_obs(student_name):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("interval_support_observations")
               .select("*").eq("student_name", student_name)
               .order("obs_date").order("time_slot").execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception:
        return pd.DataFrame()


def _bust_obs_caches():
    """Clear caches affected by writes to interval_support_observations."""
    for fn in (load_week_obs, load_all_obs, load_known_students, get_expected_intervals):
        try: fn.clear()
        except Exception: pass


def upsert_field(student_name, sel_date, sel_day, sel_time, field, value):
    sb = get_sb()
    if not sb: return False
    try:
        ex = (sb.table("interval_support_observations")
              .select("id").eq("student_name", student_name)
              .eq("obs_date", sel_date.isoformat()).eq("time_slot", sel_time)
              .limit(1).execute())
        if ex.data:
            sb.table("interval_support_observations").update(
                {field: value}).eq("id", ex.data[0]["id"]).execute()
        else:
            sb.table("interval_support_observations").insert({
                "student_name": student_name,
                "obs_date":     sel_date.isoformat(),
                "day_of_week":  sel_day,
                "time_slot":    sel_time,
                "regulated":    "",
                field:          value,
                "created_by":   get_staff_name(),
            }).execute()
        _bust_obs_caches()
        return True
    except Exception as e:
        st.error("Save failed: " + str(e)); return False


def clear_interval(student_name, sel_date, sel_time):
    sb = get_sb()
    if not sb: return
    try:
        sb.table("interval_support_observations").delete()\
          .eq("student_name", student_name).eq("obs_date", sel_date.isoformat())\
          .eq("time_slot", sel_time).execute()
        _bust_obs_caches()
    except Exception:
        pass


@st.cache_data(ttl=60)
def get_student_time_window(student_name):
    """Get custom time window for student. Returns (start_time, end_time) or None."""
    sb = get_sb()
    if not sb: return None
    try:
        res = (sb.table("interval_student_settings")
               .select("start_time,end_time")
               .eq("student_name", student_name)
               .limit(1).execute())
        if res.data:
            return (res.data[0].get("start_time"), res.data[0].get("end_time"))
        return None
    except Exception as e:
        # Silently return None if table not in schema cache yet
        if "PGRST205" in str(e) or "schema cache" in str(e):
            return None
        return None


def set_student_time_window(student_name, start_time, end_time):
    """Set custom time window for student."""
    sb = get_sb()
    if not sb: return False
    try:
        ex = (sb.table("interval_student_settings")
              .select("id").eq("student_name", student_name)
              .limit(1).execute())
        if ex.data:
            sb.table("interval_student_settings").update({
                "start_time": start_time,
                "end_time": end_time,
            }).eq("id", ex.data[0]["id"]).execute()
        else:
            sb.table("interval_student_settings").insert({
                "student_name": student_name,
                "start_time": start_time,
                "end_time": end_time,
            }).execute()
        try:
            get_student_time_window.clear(); get_expected_intervals.clear()
        except Exception: pass
        return True
    except Exception as e:
        error_msg = str(e)
        if "PGRST205" in error_msg or "schema cache" in error_msg:
            st.error("⚠️ Tables created but not yet recognized by Supabase API. Please restart the API server in your Supabase dashboard (Settings → API → Restart API) or wait 2-3 minutes and try again.")
        else:
            st.error(f"Failed to save time window: {e}")
        return False


@st.cache_data(ttl=60)
def get_day_status(student_name, obs_date):
    """Get status for a specific day (absent/holiday/etc). Returns status string or None."""
    sb = get_sb()
    if not sb: return None
    try:
        res = (sb.table("interval_day_status")
               .select("status")
               .eq("student_name", student_name)
               .eq("obs_date", obs_date.isoformat())
               .limit(1).execute())
        if res.data:
            return res.data[0].get("status")
        return None
    except Exception:
        # Silently return None if table not in schema cache yet
        return None


def set_day_status(student_name, obs_date, status):
    """Set status for a day. Pass empty string to clear."""
    sb = get_sb()
    if not sb: return False
    try:
        if not status or status.strip() == "":
            # Clear status
            sb.table("interval_day_status").delete()\
              .eq("student_name", student_name)\
              .eq("obs_date", obs_date.isoformat()).execute()
        else:
            ex = (sb.table("interval_day_status")
                  .select("id").eq("student_name", student_name)
                  .eq("obs_date", obs_date.isoformat())
                  .limit(1).execute())
            if ex.data:
                sb.table("interval_day_status").update({
                    "status": status,
                }).eq("id", ex.data[0]["id"]).execute()
            else:
                sb.table("interval_day_status").insert({
                    "student_name": student_name,
                    "obs_date": obs_date.isoformat(),
                    "status": status,
                }).execute()
        try:
            get_day_status.clear(); get_expected_intervals.clear()
        except Exception: pass
        return True
    except Exception as e:
        error_msg = str(e)
        if "PGRST205" in error_msg or "schema cache" in error_msg:
            st.error("⚠️ Tables created but not yet recognized by Supabase API. Please restart the API server in your Supabase dashboard (Settings → API → Restart API) or wait 2-3 minutes and try again.")
        else:
            st.error(f"Failed to save day status: {e}")
        return False


def copy_interval_data(interval_data):
    """Copy interval data to session state."""
    ss.ist_copied_interval = {
        "regulated": interval_data.get("regulated", ""),
        "grouping_type": interval_data.get("grouping_type", ""),
        "activity_types": interval_data.get("activity_types", ""),
        "outcome": interval_data.get("outcome", ""),
    }


def paste_interval_data(student_name, sel_date, sel_day, sel_time):
    """Paste copied interval data to the selected cell."""
    if not ss.ist_copied_interval:
        return False
    for field, value in ss.ist_copied_interval.items():
        if value:  # Only paste non-empty fields
            upsert_field(student_name, sel_date, sel_day, sel_time, field, value)
    return True


@st.cache_data(ttl=60)
def get_expected_intervals(student_name, date_from, date_to):
    """
    Calculate expected intervals based on:
    - Student's time window (part-time vs full-time)
    - Days marked as absent/holiday/transition
    Returns: (expected_intervals, attendance_days, non_attendance_days)
    """
    # Get student's time window
    time_window = get_student_time_window(student_name)
    if time_window and time_window[0] and time_window[1]:
        start_idx = SLOT_TIMES.index(time_window[0]) if time_window[0] in SLOT_TIMES else 0
        end_idx = SLOT_TIMES.index(time_window[1]) if time_window[1] in SLOT_TIMES else len(SLOT_TIMES)-1
        slots_per_day = end_idx - start_idx + 1
    else:
        slots_per_day = len(SLOT_TIMES)  # Default full day
    
    # Get all school days in range (Monday-Friday)
    total_days = 0
    attendance_days = 0
    non_attendance_info = []
    
    current_date = date_from
    while current_date <= date_to:
        if current_date.weekday() < 5:  # Monday=0, Friday=4
            total_days += 1
            day_status = get_day_status(student_name, current_date)
            if day_status:
                non_attendance_info.append((current_date, day_status))
            else:
                attendance_days += 1
        current_date += timedelta(days=1)
    
    expected_intervals = attendance_days * slots_per_day
    
    return expected_intervals, attendance_days, total_days, non_attendance_info


@st.cache_data(ttl=60)
def get_daily_note(student_name, obs_date):
    """Get anecdotal note for a specific day. Returns note text or None."""
    sb = get_sb()
    if not sb: return None
    try:
        res = (sb.table("interval_daily_notes")
               .select("note")
               .eq("student_name", student_name)
               .eq("obs_date", obs_date.isoformat())
               .limit(1).execute())
        if res.data:
            return res.data[0].get("note", "")
        return None
    except Exception:
        return None


def set_daily_note(student_name, obs_date, note):
    """Set anecdotal note for a day. Pass empty string to clear."""
    sb = get_sb()
    if not sb: return False
    try:
        if not note or note.strip() == "":
            # Clear note
            sb.table("interval_daily_notes").delete()\
              .eq("student_name", student_name)\
              .eq("obs_date", obs_date.isoformat()).execute()
        else:
            ex = (sb.table("interval_daily_notes")
                  .select("id").eq("student_name", student_name)
                  .eq("obs_date", obs_date.isoformat())
                  .limit(1).execute())
            if ex.data:
                sb.table("interval_daily_notes").update({
                    "note": note.strip(),
                }).eq("id", ex.data[0]["id"]).execute()
            else:
                sb.table("interval_daily_notes").insert({
                    "student_name": student_name,
                    "obs_date": obs_date.isoformat(),
                    "note": note.strip(),
                }).execute()
        try:
            get_daily_note.clear(); get_all_daily_notes.clear()
        except Exception: pass
        return True
    except Exception as e:
        if "PGRST205" in str(e) or "schema cache" in str(e):
            st.error("⚠️ Daily notes table not yet recognized. Create the table and restart the Supabase API.")
        else:
            st.error(f"Failed to save note: {e}")
        return False


@st.cache_data(ttl=60)
def get_all_daily_notes(student_name, date_from, date_to):
    """Get all daily notes for a date range. Returns dict {date: note}."""
    sb = get_sb()
    if not sb: return {}
    try:
        res = (sb.table("interval_daily_notes")
               .select("obs_date,note")
               .eq("student_name", student_name)
               .gte("obs_date", date_from.isoformat())
               .lte("obs_date", date_to.isoformat())
               .execute())
        if res.data:
            return {row["obs_date"]: row["note"] for row in res.data}
        return {}
    except Exception as e:
        # Silently return empty dict if table not available yet
        error_str = str(e)
        if "PGRST205" not in error_str and "schema cache" not in error_str:
            # Log unexpected errors for debugging
            st.warning(f"Note: Daily notes feature requires database setup. Error: {error_str}")
        return {}


# ── Saves (prevention / de-escalation) ──────────────────────────────────────
def insert_save(student_name, sel_date, save_time, time_slot, signs, supports, outcome, note):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("interval_saves").insert({
            "student_name": student_name,
            "obs_date":     sel_date.isoformat(),
            "save_time":    save_time,
            "time_slot":    time_slot,
            "early_sign":   ", ".join(signs),
            "support_used": ", ".join(supports),
            "outcome":      outcome,
            "notes":        note.strip() if note else "",
            "created_by":   get_staff_name(),
        }).execute()
        try:
            load_saves_day.clear(); load_all_saves.clear()
        except Exception: pass
        return True
    except Exception as e:
        es = str(e)
        if "PGRST205" in es or "schema cache" in es:
            st.error("Saves table not found — run interval_saves_table.sql in Supabase first.")
        else:
            st.error("Save failed: " + es)
        return False


@st.cache_data(ttl=60)
def load_saves_day(student_name, sel_date):
    sb = get_sb()
    if not sb: return []
    try:
        res = (sb.table("interval_saves").select("*")
               .eq("student_name", student_name)
               .eq("obs_date", sel_date.isoformat())
               .order("save_time").execute())
        return res.data or []
    except Exception:
        return []


@st.cache_data(ttl=60)
def load_all_saves(student_name):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("interval_saves").select("*")
               .eq("student_name", student_name)
               .order("obs_date").execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
        return df
    except Exception:
        return pd.DataFrame()


def delete_save(save_id):
    sb = get_sb()
    if not sb: return
    try:
        sb.table("interval_saves").delete().eq("id", save_id).execute()
        try:
            load_saves_day.clear(); load_all_saves.clear()
        except Exception: pass
    except Exception:
        pass


# ── Session state ─────────────────────────────────────────────────────────────
ss = st.session_state
for k, v in [
    ("ist_name", ""),
    ("ist_week", date.today() - timedelta(days=date.today().weekday())),
    ("ist_sel_time", SLOT_TIMES[0]),
    ("ist_sel_day",  DAYS[min(date.today().weekday(), 4)]),
    ("ist_copied_interval", None),  # For copy/paste functionality
]:
    if k not in ss: ss[k] = v


st.markdown("""
<div class="clc-header">
  <h2>🔵 Interval Support Tracker
    <span style="background:#16a34a;color:white;font-size:.6rem;font-weight:700;
                 padding:.15rem .5rem;border-radius:10px;vertical-align:middle;
                 margin-left:.5rem;">BUILD C · Quick + Grid entry</span>
  </h2>
  <p>Window of Tolerance — regulation state &amp; support per 15-minute interval
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)

# ── Student selector ──────────────────────────────────────────────────────────
known = load_known_students()

if not ss.ist_name:
    st.markdown("#### Select or add a student")

    if known:
        opts = ["— select existing —"] + known
        sel_opt = st.selectbox("Existing students", opts, index=0, key="ist_sel_opt")
        if sel_opt != "— select existing —":
            ss.ist_name = sel_opt
            st.rerun()
        st.markdown(
            "<div style='text-align:center;color:#94a3b8;font-size:.82rem;"
            "padding:.4rem 0;'>— or add a new student below —</div>",
            unsafe_allow_html=True)
    else:
        st.info("No students tracked yet. Add the first one below.")

    with st.form("ist_new_student_form", clear_on_submit=True):
        new_n = st.text_input(
            "New student name",
            placeholder="e.g. Alex Smith",
            key="ist_name_inp"
        )
        submitted = st.form_submit_button(
            "▶ Start tracking", type="primary", use_container_width=True
        )
    if submitted:
        if new_n.strip():
            ss.ist_name = new_n.strip()
            st.rerun()
        else:
            st.error("Please enter a student name.")

    st.stop()

student_name = ss.ist_name

# Active student bar
bar1, bar2, bar3 = st.columns([5, 1, 1])
with bar1:
    st.markdown(
        f'<div style="background:#EBF4F9;border:1.5px solid #1A6B8A;border-radius:8px;'
        f'padding:.45rem .9rem;font-weight:700;color:#1A6B8A;font-size:.95rem;">'
        f'👤 {student_name}</div>',
        unsafe_allow_html=True)
with bar2:
    if known and len(known) > 1:
        other = [n for n in known if n != student_name]
        switch = st.selectbox("Switch", ["—"] + other, index=0,
                              key="ist_switch", label_visibility="collapsed")
        if switch != "—":
            ss.ist_name = switch
            st.rerun()
with bar3:
    if st.button("+ New", key="ist_new", use_container_width=True):
        ss.ist_name = ""
        st.rerun()

# ── Archive management ───────────────────────────────────────────────────
with st.expander("🗄️ Archive / manage student data", expanded=False):
    arch_tabs = st.tabs(["Archive a student", "View archived students"])

    with arch_tabs[0]:
        st.caption(
            "Archiving moves a student out of the active list. "
            "Their data is preserved and can be restored at any time."
        )
        if not known:
            st.info("No students with data yet.")
        else:
            arch_name = st.selectbox("Select student to archive",
                                     known, key="ist_arch_sel")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🗄️ Archive this student", key="ist_arch_btn",
                             use_container_width=True, type="secondary"):
                    sb = get_sb()
                    if sb:
                        try:
                            sb.table("interval_archived_students").upsert(
                                {"student_name": arch_name, "archived": True},
                                on_conflict="student_name"
                            ).execute()
                            _bust_obs_caches()
                            if ss.ist_name == arch_name:
                                ss.ist_name = ""
                            st.success(f"✅ {arch_name} archived.")
                            st.rerun()
                        except Exception as e:
                            st.error("Could not archive: " + str(e))
            with col_b:
                if st.button("🗑️ Delete ALL data for this student", key="ist_del_btn",
                             use_container_width=True, type="secondary"):
                    ss["ist_confirm_del"] = arch_name
                    st.rerun()

            if ss.get("ist_confirm_del") == arch_name:
                st.warning(f"⚠️ This permanently deletes all interval data for **{arch_name}**.")
                confirm = st.text_input("Type the student name to confirm",
                                        key="ist_del_confirm")
                if st.button("Confirm delete", key="ist_del_confirm_btn", type="secondary"):
                    if confirm.strip().lower() == arch_name.lower():
                        sb = get_sb()
                        if sb:
                            try:
                                sb.table("interval_support_observations").delete() \
                                  .eq("student_name", arch_name).execute()
                                try:
                                    sb.table("interval_archived_students").delete() \
                                      .eq("student_name", arch_name).execute()
                                except Exception:
                                    pass
                                _bust_obs_caches()
                                ss.pop("ist_confirm_del", None)
                                if ss.ist_name == arch_name:
                                    ss.ist_name = ""
                                st.success(f"✅ All data for {arch_name} deleted.")
                                st.rerun()
                            except Exception as e:
                                st.error("Delete failed: " + str(e))
                    else:
                        st.error("Name does not match.")

    with arch_tabs[1]:
        sb = get_sb()
        archived_names = []
        if sb:
            try:
                ar = sb.table("interval_archived_students") \
                       .select("student_name").eq("archived", True).execute()
                archived_names = [r["student_name"] for r in (ar.data or [])]
            except Exception:
                pass

        if not archived_names:
            st.info("No archived students.")
        else:
            st.markdown(f"**{len(archived_names)} archived student(s):**")
            for aname in archived_names:
                ac1, ac2, ac3 = st.columns([3, 1, 1])
                with ac1:
                    st.markdown(f"**{aname}**")
                with ac2:
                    if st.button("Restore", key=f"restore_{aname}",
                                 use_container_width=True):
                        try:
                            sb.table("interval_archived_students").update(
                                {"archived": False}
                            ).eq("student_name", aname).execute()
                            _bust_obs_caches()
                            st.success(f"✅ {aname} restored.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with ac3:
                    if st.button("View data", key=f"view_arch_{aname}",
                                 use_container_width=True):
                        ss.ist_name = aname
                        st.rerun()

# ── Student settings ───────────────────────────────────────────────────
with st.expander("⚙️ Student settings & day status", expanded=False):
    set_tabs = st.tabs(["⏰ Observation hours", "📅 Mark days"])
    
    with set_tabs[0]:
        st.caption("Set custom observation hours for this student (e.g., part-time attendance)")
        current_window = get_student_time_window(student_name)
        
        col1, col2 = st.columns(2)
        with col1:
            start_idx = SLOT_TIMES.index(current_window[0]) if current_window and current_window[0] in SLOT_TIMES else 0
            start_time = st.selectbox("Start time", SLOT_TIMES, index=start_idx, key="ist_start_time")
        with col2:
            end_idx = SLOT_TIMES.index(current_window[1]) if current_window and current_window[1] in SLOT_TIMES else len(SLOT_TIMES)-1
            end_time = st.selectbox("End time", SLOT_TIMES, index=end_idx, key="ist_end_time")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Save observation hours", key="ist_save_window", use_container_width=True, type="primary"):
                if set_student_time_window(student_name, start_time, end_time):
                    st.success(f"✅ Observation hours set: {start_time}–{end_time}")
                    st.rerun()
        with col_b:
            if current_window and st.button("🔄 Reset to default (9:00–14:30)", key="ist_reset_window", use_container_width=True):
                if set_student_time_window(student_name, None, None):
                    st.success("✅ Reset to default hours")
                    st.rerun()
        
        if current_window:
            st.info(f"ℹ️ Current setting: **{current_window[0]}–{current_window[1]}**  (only these slots will show in the grid)")
    
    with set_tabs[1]:
        st.caption("Mark entire days as absent, holiday, or not in attendance")
        
        # Show current week days
        week_start_here = ss.ist_week
        week_days = [(week_start_here + timedelta(days=i), DAYS[i]) for i in range(5)]
        
        for day_date, day_name in week_days:
            current_status = get_day_status(student_name, day_date)
            
            status_display = f"**{day_name} {day_date.strftime('%-d/%m')}**"
            if current_status:
                status_display += f" — <span style='background:#fef9c3;padding:.1rem .4rem;border-radius:4px;font-size:.75rem;'>{current_status.upper()}</span>"
            
            st.markdown(status_display, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("Absent", key=f"day_absent_{day_date}", use_container_width=True, 
                           type="primary" if current_status == "absent" else "secondary"):
                    set_day_status(student_name, day_date, "absent")
                    st.rerun()
            with col2:
                if st.button("Holiday", key=f"day_holiday_{day_date}", use_container_width=True,
                           type="primary" if current_status == "holiday" else "secondary"):
                    set_day_status(student_name, day_date, "holiday")
                    st.rerun()
            with col3:
                if st.button("Transition", key=f"day_transition_{day_date}", use_container_width=True,
                           type="primary" if current_status == "transition" else "secondary"):
                    set_day_status(student_name, day_date, "transition")
                    st.rerun()
            with col4:
                if current_status and st.button("Clear", key=f"day_clear_{day_date}", use_container_width=True):
                    set_day_status(student_name, day_date, "")
                    st.rerun()
            
            st.markdown("<div style='margin-bottom:.5rem;'></div>", unsafe_allow_html=True)

st.markdown("---")
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis"])

# ════════════════════════════════════════════════════════════════════════════
# RECORD & VIEW
# ════════════════════════════════════════════════════════════════════════════
with t_record:
    week_start = ss.ist_week
    week_end   = week_start + timedelta(days=4)
    this_week  = date.today() - timedelta(days=date.today().weekday())
    is_this    = week_start == this_week

    # Week nav
    wc1,wc2,wc3,wc4 = st.columns([1,4,1,1])
    with wc1:
        if st.button("← Prev", key="ist_prev", use_container_width=True):
            ss.ist_week -= timedelta(weeks=1); st.rerun()
    with wc2:
        st.markdown(
            f'<div style="text-align:center;padding:.35rem 0;font-weight:700;'
            f'color:{TEAL};font-size:.9rem;">'
            f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
            + (' &nbsp;<span style="background:#dbeafe;color:#1d4ed8;font-size:.68rem;'
               'padding:.1rem .45rem;border-radius:10px;">This week</span>' if is_this else '')
            + '</div>', unsafe_allow_html=True)
    with wc3:
        if st.button("Next →", key="ist_next", use_container_width=True):
            ss.ist_week += timedelta(weeks=1); st.rerun()
    with wc4:
        if st.button("Today", key="ist_today", use_container_width=True):
            ss.ist_week = this_week; st.rerun()

    week_df   = load_week_obs(student_name, week_start, week_end)
    day_dates = {DAYS[i]: (week_start+timedelta(days=i)).strftime("%-d/%m") for i in range(5)}
    today_day = DAYS[min(date.today().weekday(), 4)]

    # Build cell lookup
    cell_data = {}
    if not week_df.empty:
        for _, row in week_df.iterrows():
            t = row.get("time_slot",""); d = row.get("day_of_week","")
            if not t or not d: continue
            if t not in cell_data: cell_data[t] = {}
            cell_data[t][d] = row.to_dict()

    # Initialise selected cell
    from datetime import datetime as _dt
    _now_m = _dt.now().hour*60 + _dt.now().minute
    _nearest = min(SLOT_TIMES, key=lambda t: abs(int(t.split(":")[0])*60+int(t.split(":")[1])-_now_m))
    if ss.ist_sel_time not in SLOT_TIMES: ss.ist_sel_time = _nearest
    if ss.ist_sel_day  not in DAYS:       ss.ist_sel_day  = today_day

    sel_time = ss.ist_sel_time
    sel_day  = ss.ist_sel_day
    sel_date = week_start + timedelta(days=DAYS.index(sel_day))

    # ── Field label/key maps ──────────────────────────────────────────────
    REG_LABELS = [c["label"] for c in REG_STATES.values()]
    REG_L2K    = {c["label"]: k for k, c in REG_STATES.items()}
    REG_K2L    = {k: c["label"] for k, c in REG_STATES.items()}
    GRP_LABELS = list(GROUPING_TYPES.values())
    GRP_L2K    = {v: k for k, v in GROUPING_TYPES.items()}
    GRP_K2L    = {k: v for k, v in GROUPING_TYPES.items()}
    OUT_LABELS = [c["label"] for c in OUTCOMES.values()]
    OUT_L2K    = {c["label"]: k for k, c in OUTCOMES.items()}
    OUT_K2L    = {k: c["label"] for k, c in OUTCOMES.items()}

    # Slots limited to the student's recording window
    student_window = get_student_time_window(student_name)
    if student_window and student_window[0] and student_window[1] \
       and student_window[0] in SLOT_TIMES and student_window[1] in SLOT_TIMES:
        s_i = SLOT_TIMES.index(student_window[0]); e_i = SLOT_TIMES.index(student_window[1])
        display_slots = SLOT_TIMES[s_i:e_i + 1]
    else:
        display_slots = SLOT_TIMES
    if ss.ist_sel_time not in display_slots:
        ss.ist_sel_time = display_slots[0]
    sel_time = ss.ist_sel_time

    # Compact legend
    leg_parts = " &nbsp;".join(
        f'<span style="background:{v["bg"]};color:{v["fg"]};padding:.05rem .35rem;'
        f'border-radius:5px;font-weight:700;font-size:.62rem;">{v["short"]}</span>'
        f'<span style="font-size:.62rem;color:#475569;"> {v["label"]}</span>'
        for v in REG_STATES.values())
    st.markdown(f'<div style="margin:.1rem 0 .35rem;display:flex;flex-wrap:wrap;gap:.2rem;">'
                f'{leg_parts}</div>', unsafe_allow_html=True)

    # ── Day picker (stable options) ────────────────────────────────────────
    day_short = [d[:3] for d in DAYS]
    picked_day = single_choice_widget("Day", day_short, "ist_day_pick", default=sel_day[:3])
    if picked_day and DAYS[day_short.index(picked_day)] != ss.ist_sel_day:
        ss.ist_sel_day = DAYS[day_short.index(picked_day)]
        st.rerun()
    sel_day  = ss.ist_sel_day
    sel_date = week_start + timedelta(days=DAYS.index(sel_day))

    # ── Entry mode toggle ──────────────────────────────────────────────────
    mode = single_choice_widget("Mode", ["⚡ Quick", "📋 Grid"], "ist_entry_mode",
                                default="⚡ Quick") or "⚡ Quick"

    # ════════════════════════════════════════════════════════════════════════
    # GRID MODE — whole day in a table, save once
    # ════════════════════════════════════════════════════════════════════════
    if mode == "📋 Grid":
        st.caption(f"Fill the day top to bottom, then **Save day** once — no reload between cells. "
                   f"Editing **{sel_day} {sel_date.strftime('%-d %b')}**.")
        rows = []
        for t in display_slots:
            c = cell_data.get(t, {}).get(sel_day, {})
            acts = [a.strip() for a in (c.get("activity_types", "") or "").split(",") if a.strip()]
            rows.append({
                "Time":       t,
                "Regulation": REG_K2L.get(c.get("regulated", "") or "", ""),
                "Grouping":   GRP_K2L.get(c.get("grouping_type", "") or "", ""),
                "Activity":   acts[0] if acts else "",
                "Behaviour":  OUT_K2L.get(c.get("outcome", "") or "", ""),
            })
        grid_df = pd.DataFrame(rows)
        edited = st.data_editor(
            grid_df, key=f"ist_grid_{sel_day}_{sel_date}", hide_index=True,
            use_container_width=True, num_rows="fixed",
            column_config={
                "Time":       st.column_config.TextColumn("Time", disabled=True, width="small"),
                "Regulation": st.column_config.SelectboxColumn("Regulation", options=[""] + REG_LABELS, width="medium"),
                "Grouping":   st.column_config.SelectboxColumn("Grouping", options=[""] + GRP_LABELS, width="medium"),
                "Activity":   st.column_config.SelectboxColumn("Activity", options=[""] + ACTIVITY_TYPES, width="medium"),
                "Behaviour":  st.column_config.SelectboxColumn("Behaviour", options=[""] + OUT_LABELS, width="medium"),
            },
        )
        st.caption("Grid sets a single activity per slot; use Quick mode for multiple activities on one interval.")
        if st.button("💾  Save day", key="ist_grid_save", type="primary", use_container_width=True):
            n = 0
            for i, t in enumerate(display_slots):
                o = grid_df.iloc[i]; nw = edited.iloc[i]
                if nw["Regulation"] != o["Regulation"]:
                    upsert_field(student_name, sel_date, sel_day, t, "regulated", REG_L2K.get(nw["Regulation"], "")); n += 1
                if nw["Grouping"] != o["Grouping"]:
                    upsert_field(student_name, sel_date, sel_day, t, "grouping_type", GRP_L2K.get(nw["Grouping"], "")); n += 1
                if nw["Activity"] != o["Activity"]:
                    upsert_field(student_name, sel_date, sel_day, t, "activity_types", nw["Activity"] or ""); n += 1
                if nw["Behaviour"] != o["Behaviour"]:
                    upsert_field(student_name, sel_date, sel_day, t, "outcome", OUT_L2K.get(nw["Behaviour"], "")); n += 1
            st.success(f"✅ Saved {n} change(s) for {sel_day}")
            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # QUICK MODE — one interval, big targets, save & next
    # ════════════════════════════════════════════════════════════════════════
    else:
        idx = display_slots.index(sel_time) if sel_time in display_slots else 0

        def _fmt_slot(t):
            return ("✓ " if cell_data.get(t, {}).get(sel_day, {}).get("regulated") else "") + t

        sc1, sc2, sc3 = st.columns([1, 4, 1])
        with sc1:
            if st.button("◀", key="ist_slot_prev", use_container_width=True, disabled=(idx == 0)):
                ss.ist_sel_time = display_slots[idx - 1]; st.rerun()
        with sc2:
            pick = st.selectbox("Slot", display_slots, index=idx, format_func=_fmt_slot,
                                label_visibility="collapsed")
            if pick != sel_time:
                ss.ist_sel_time = pick; st.rerun()
        with sc3:
            if st.button("▶", key="ist_slot_next", use_container_width=True,
                         disabled=(idx >= len(display_slots) - 1)):
                ss.ist_sel_time = display_slots[idx + 1]; st.rerun()

        cur = cell_data.get(sel_time, {}).get(sel_day, {})
        cur_reg_l = REG_K2L.get(cur.get("regulated", "") or "", None)
        cur_grp_l = GRP_K2L.get(cur.get("grouping_type", "") or "", None)
        cur_out_l = OUT_K2L.get(cur.get("outcome", "") or "", None)
        cur_acts  = [a.strip() for a in (cur.get("activity_types", "") or "").split(",") if a.strip()]
        done = "✓ recorded" if cur.get("regulated") else "not yet recorded"
        done_col = "#16a34a" if cur.get("regulated") else "#94a3b8"
        st.markdown(
            f'<div style="font-weight:700;color:{TEAL};margin:.2rem 0 .1rem;">'
            f'📍 {sel_time} · {sel_day} {sel_date.strftime("%-d %b")} '
            f'<span style="font-weight:600;font-size:.72rem;color:{done_col};">— {done}</span></div>',
            unsafe_allow_html=True)

        ks = f"{sel_time}_{sel_day}"
        with st.form(f"ist_quick_{ks}", border=True):
            st.markdown('<div style="font-size:.66rem;font-weight:700;color:#1A6B8A;">REGULATION STATE</div>', unsafe_allow_html=True)
            q_reg = single_choice_widget("Regulation", REG_LABELS, f"ist_q_reg_{ks}", default=cur_reg_l)
            st.markdown('<div style="font-size:.66rem;font-weight:700;color:#1A6B8A;margin-top:.35rem;">GROUPING</div>', unsafe_allow_html=True)
            q_grp = single_choice_widget("Grouping", GRP_LABELS, f"ist_q_grp_{ks}", default=cur_grp_l)
            st.markdown('<div style="font-size:.66rem;font-weight:700;color:#1A6B8A;margin-top:.35rem;">ACTIVITY <span style="font-weight:400;">(tap multiple)</span></div>', unsafe_allow_html=True)
            q_act = multi_select_widget("Activity", ACTIVITY_TYPES, f"ist_q_act_{ks}", default=cur_acts)
            st.markdown('<div style="font-size:.66rem;font-weight:700;color:#1A6B8A;margin-top:.35rem;">OBSERVABLE BEHAVIOUR</div>', unsafe_allow_html=True)
            q_out = single_choice_widget("Behaviour", OUT_LABELS, f"ist_q_out_{ks}", default=cur_out_l)
            bq1, bq2 = st.columns([3, 2])
            with bq1:
                save_next = st.form_submit_button("💾  Save & next ▶", use_container_width=True, type="primary")
            with bq2:
                save_stay = st.form_submit_button("💾  Save", use_container_width=True)

        if save_next or save_stay:
            def _w(field, newval, oldval):
                if (newval or "") != (oldval or ""):
                    upsert_field(student_name, sel_date, sel_day, sel_time, field, newval or "")
            _w("regulated",      REG_L2K.get(q_reg, ""),      cur.get("regulated", ""))
            _w("grouping_type",  GRP_L2K.get(q_grp, ""),      cur.get("grouping_type", ""))
            _w("activity_types", ",".join(q_act or []),       cur.get("activity_types", ""))
            _w("outcome",        OUT_L2K.get(q_out, ""),      cur.get("outcome", ""))
            if save_next and idx < len(display_slots) - 1:
                ss.ist_sel_time = display_slots[idx + 1]
            st.success("✅ Saved")
            st.rerun()

        # Copy / paste / clear (outside the form — buttons can't live in a form)
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            if cur.get("regulated") and st.button("📋 Copy", key=f"ist_copy_{ks}", use_container_width=True):
                copy_interval_data(cur); st.rerun()
        with qc2:
            if ss.ist_copied_interval and st.button("📥 Paste here", key=f"ist_paste_{ks}",
                                                     use_container_width=True, type="primary"):
                paste_interval_data(student_name, sel_date, sel_day, sel_time)
                ss.ist_copied_interval = None; st.rerun()
        with qc3:
            if cur.get("regulated") and st.button("🗑️ Clear", key=f"ist_clear_{ks}", use_container_width=True):
                clear_interval(student_name, sel_date, sel_time); st.rerun()
        if ss.ist_copied_interval:
            st.caption("📋 An interval is copied — open any slot and tap **Paste here**.")

    # ── Week overview (read-only heatmap) ──────────────────────────────────
    with st.expander("📅 Week overview (read-only)", expanded=False):
        hc = st.columns([1.1] + [1] * 5)
        with hc[0]:
            st.markdown('<div style="font-size:.6rem;font-weight:700;color:white;background:#1A6B8A;'
                        'border-radius:5px;padding:.2rem;text-align:center;">Time</div>', unsafe_allow_html=True)
        for di, d in enumerate(DAYS):
            with hc[di + 1]:
                is_sd = (d == sel_day)
                st.markdown(f'<div style="font-size:.6rem;font-weight:700;color:white;'
                            f'background:{"#0f3d5c" if is_sd else "#1A6B8A"};border-radius:5px;'
                            f'padding:.2rem;text-align:center;">{d[:3]}<br>'
                            f'<span style="font-weight:400;">{day_dates[d]}</span></div>', unsafe_allow_html=True)
        for t in display_slots:
            rc = st.columns([1.1] + [1] * 5)
            with rc[0]:
                st.markdown(f'<div style="font-size:.62rem;color:#475569;text-align:center;'
                            f'padding:.15rem;">{t}</div>', unsafe_allow_html=True)
            for di, d in enumerate(DAYS):
                c = cell_data.get(t, {}).get(d, {})
                reg = c.get("regulated", "") or ""
                cfg = REG_STATES.get(reg, {})
                bg = cfg.get("bg", "#f8fafc"); fg = cfg.get("fg", "#cbd5e1")
                txt = cfg.get("short", "·") if reg else "·"
                with rc[di + 1]:
                    st.markdown(f'<div style="font-size:.62rem;font-weight:700;color:{fg};'
                                f'background:{bg};border-radius:5px;padding:.15rem;text-align:center;">'
                                f'{txt}</div>', unsafe_allow_html=True)

    # ── Daily notes section ───────────────────────────────────────────────────
    st.markdown('<div style="border-top:1px solid #e2e8f0;margin:.6rem 0 .4rem;"></div>',
                unsafe_allow_html=True)
    
    current_note = get_daily_note(student_name, sel_date) or ""
    has_note = bool(current_note and current_note.strip())
    
    st.markdown(
        '<div style="font-size:.75rem;font-weight:700;color:#1A6B8A;margin-bottom:.3rem;">'
        f'📝 DAILY NOTE — {sel_day} {sel_date.strftime("%-d %b %Y")}'
        + (' <span style="background:#16a34a;color:white;padding:.1rem .4rem;border-radius:3px;font-size:.65rem;margin-left:.3rem;">✓ SAVED</span>' if has_note else '')
        + '</div>',
        unsafe_allow_html=True)
    
    st.caption("Optional anecdotal information for this day (e.g., incidents, observations, context)")
    
    note_text = st.text_area(
        "Daily note",
        value=current_note,
        height=80,
        key=f"daily_note_{sel_date}",
        label_visibility="collapsed",
        placeholder="e.g., Student arrived upset after family conflict. Early intervention by leadership at 10:00. Calmed after sensory break..."
    )
    
    note_col1, note_col2 = st.columns([3, 1])
    with note_col1:
        if st.button("💾 Save note", key=f"save_note_{sel_date}", use_container_width=True, type="primary"):
            if set_daily_note(student_name, sel_date, note_text):
                st.success("✅ Note saved!")
                st.rerun()
    
    with note_col2:
        if current_note:
            if st.button("🗑️ Clear note", key=f"clear_note_{sel_date}", use_container_width=True):
                if set_daily_note(student_name, sel_date, ""):
                    st.success("✅ Note cleared")
                    st.rerun()

    # ════════════════════════════════════════════════════════════════════
    # LOG A SAVE — early sign caught & turned around (form: no per-tap reruns)
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin:.7rem 0 .2rem;'></div>", unsafe_allow_html=True)
    todays_saves = load_saves_day(student_name, sel_date)
    save_count_lbl = f" · {len(todays_saves)} logged today" if todays_saves else ""
    with st.expander(f"⚡  Log a SAVE — early sign caught & turned around{save_count_lbl}", expanded=False):
        st.caption(
            f"For **{sel_day} {sel_date.strftime('%-d %b')}** — log when an escalation was "
            "starting and a support turned it around. Tap your selections, then Log once."
        )

        _outcome_labels = [ov["emoji"] + " " + ov["label"] for ov in SAVE_OUTCOMES.values()]
        _label_to_key   = {ov["emoji"] + " " + ov["label"]: k for k, ov in SAVE_OUTCOMES.items()}

        with st.form("ist_save_form", clear_on_submit=True, border=False):
            st.markdown('<div style="font-size:.72rem;font-weight:700;color:#1A6B8A;'
                        'margin:.2rem 0 .15rem;">⚠️ Early sign(s) observed</div>', unsafe_allow_html=True)
            f_signs = multi_select_widget("Early signs", SAVE_SIGNS, "ist_f_signs")

            st.markdown('<div style="font-size:.72rem;font-weight:700;color:#1A6B8A;'
                        'margin:.5rem 0 .15rem;">🛟 Support(s) applied</div>', unsafe_allow_html=True)
            f_supports = multi_select_widget("Supports", SAVE_SUPPORTS, "ist_f_supports")
            f_other = st.text_input("Other support (if not listed)", key="ist_f_other",
                                    placeholder="Other support used (optional)",
                                    label_visibility="collapsed")

            st.markdown('<div style="font-size:.72rem;font-weight:700;color:#1A6B8A;'
                        'margin:.5rem 0 .15rem;">🎯 Outcome</div>', unsafe_allow_html=True)
            f_outcome_label = single_choice_widget("Outcome", _outcome_labels, "ist_f_outcome")

            f_note = st.text_input("Note (optional)", key="ist_f_note",
                                   placeholder="e.g., flagged at task change — offered choice + movement break, settled within 5 min",
                                   label_visibility="collapsed")

            submitted = st.form_submit_button("💾  Log save", use_container_width=True, type="primary")

        if submitted:
            outcome_key = _label_to_key.get(f_outcome_label, "")
            if not f_signs or not outcome_key:
                st.warning("Pick at least one early sign and an outcome, then Log.")
            else:
                supports = list(f_supports)
                if f_other and f_other.strip():
                    supports.append(f_other.strip())
                now_hhmm = datetime.now().strftime("%-H:%M")
                _nm = datetime.now().hour * 60 + datetime.now().minute
                nearest = min(SLOT_TIMES, key=lambda t: abs(int(t.split(":")[0]) * 60 + int(t.split(":")[1]) - _nm))
                if insert_save(student_name, sel_date, now_hhmm, nearest,
                               list(f_signs), supports, outcome_key, f_note):
                    st.success("✅ Save logged")
                    st.rerun()

        # Today's saves (buttons must sit outside the form)
        if todays_saves:
            st.markdown("<div style='margin:.5rem 0 .2rem;font-size:.72rem;font-weight:700;"
                        "color:#475569;'>Logged on this day</div>", unsafe_allow_html=True)
            for sv in todays_saves:
                ov = SAVE_OUTCOMES.get(sv.get("outcome", ""), {"emoji": "•", "label": sv.get("outcome", ""), "bg": "#f1f5f9", "fg": "#475569"})
                sc1, sc2 = st.columns([6, 1])
                with sc1:
                    st.markdown(
                        f'<div style="background:{ov["bg"]};border-radius:6px;padding:.35rem .6rem;'
                        f'font-size:.74rem;color:#334155;margin-bottom:.25rem;">'
                        f'<strong>{sv.get("save_time","")}</strong> &nbsp;'
                        f'<span style="color:{ov["fg"]};font-weight:700;">{ov["emoji"]} {ov["label"]}</span><br>'
                        f'<span style="font-size:.7rem;">⚠️ {sv.get("early_sign","—")} &nbsp;→&nbsp; '
                        f'🛟 {sv.get("support_used","—")}</span>'
                        + (f'<br><span style="font-size:.68rem;color:#64748b;">{sv.get("notes","")}</span>' if sv.get("notes") else "")
                        + '</div>', unsafe_allow_html=True)
                with sc2:
                    if st.button("🗑️", key=f"del_save_{sv['id']}", use_container_width=True):
                        delete_save(sv["id"]); st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ════════════════════════════════════════════════════════════════════════════

def _slot_to_min(t):
    """Convert 'H:MM' string to minutes-since-midnight."""
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 9999


def _groq_hypothesis(prompt_text):
    """Call Groq to generate a clinical hypothesis. Returns None if unavailable."""
    try:
        import requests as _req
        key = st.secrets.get("groq", {}).get("api_key") or st.secrets.get("GROQ_API_KEY", "")
        if not key:
            return None
        resp = _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "max_tokens": 220,
                "temperature": 0.4,
                "messages": [
                    {"role": "system", "content":
                        "You are a specialist behaviour support practitioner at an alternative education setting "
                        "for students with complex needs. Write a concise, data-grounded clinical hypothesis "
                        "(3–5 sentences, plain English, no bullet points) interpreting the pattern described. "
                        "Acknowledge what the data suggests, note what this means for the student's support needs, "
                        "and identify one key question or recommendation for the team. Do not use the student's "
                        "full name — refer to 'the student'."},
                    {"role": "user", "content": prompt_text},
                ]
            },
            timeout=12,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _rpt_fig(fig, height=380, margin_b=100, margin_l=65, margin_r=30, margin_t=65, font_size=12):
    """
    Return a copy of fig sized and styled for the HTML report.
    Sets explicit width so the chart fills the 820px report column without clipping,
    increases font sizes and margins so axis labels aren't cropped, and turns off
    autosize so Plotly doesn't try to resize to the Streamlit container.
    """
    import copy
    f = copy.deepcopy(fig)
    f.update_layout(
        width=820,
        height=height,
        autosize=False,
        font=dict(size=font_size, family="Arial, sans-serif"),
        margin=dict(l=margin_l, r=margin_r, t=margin_t, b=margin_b),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.04,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
    )
    # Make sure x/y grid lines remain clean
    f.update_xaxes(gridcolor="#e2e8f0", tickfont=dict(size=11))
    f.update_yaxes(gridcolor="#e2e8f0", tickfont=dict(size=11))
    return f


def _hypothesis_box(text, key=None):
    """Render a teal hypothesis card. key stores text in ss for report."""
    if key:
        ss[key] = text
    st.markdown(
        f'<div style="background:#EBF4F9;border-left:4px solid #1A6B8A;border-radius:0 8px 8px 0;'
        f'padding:.6rem 1rem;margin:.3rem 0 .7rem;font-size:.82rem;color:#1e3a4a;line-height:1.5;">'
        f'<span style="font-size:.68rem;font-weight:700;color:#1A6B8A;letter-spacing:.05em;">'
        f'🔍 HYPOTHESIS</span><br>{text}</div>',
        unsafe_allow_html=True)


def _generate_questions(data_summary):
    """Call Groq to generate specific investigative questions from data patterns."""
    try:
        import requests as _req
        key = st.secrets.get("groq", {}).get("api_key") or st.secrets.get("GROQ_API_KEY", "")
        if not key:
            return None
        resp = _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "max_tokens": 400,
                "temperature": 0.5,
                "messages": [
                    {"role": "system", "content":
                        "You are a specialist behaviour support practitioner reviewing interval observation data. "
                        "Based on the patterns in the data, generate exactly 5 specific, practical investigative "
                        "questions the team should ask to better understand the student's regulation. "
                        "Questions must be grounded in the actual data patterns described — reference specific "
                        "times, days, activities, or support arrangements from the data. "
                        "Number each question 1–5. Each question should be one sentence ending in a question mark. "
                        "Do not use bullet points. Do not use the student's full name — say 'the student'. "
                        "Focus on: what is happening at the times/days of best regulation (not just why it's bad), "
                        "what specific tasks or routines occur at those times, "
                        "what staff actions or environments correlate with regulation, "
                        "and what would help the team build on strengths rather than only manage difficulties."},
                    {"role": "user", "content": data_summary},
                ]
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


with t_analysis:
    st.markdown(f"#### {student_name} — Regulation & Support Analysis")
    all_obs = load_all_obs(student_name)
    if all_obs.empty:
        st.info("No observations recorded yet."); st.stop()

    fc1, fc2 = st.columns(2)
    with fc1: date_from = st.date_input("From", value=all_obs["obs_date_dt"].min().date(), key="ist_af")
    with fc2: date_to   = st.date_input("To",   value=all_obs["obs_date_dt"].max().date(), key="ist_at")

    # Calculate expected intervals based on attendance and time window
    expected_intervals, attendance_days, total_school_days, non_attendance_info = get_expected_intervals(
        student_name, date_from, date_to
    )
    
    # Get student time window for display
    time_window = get_student_time_window(student_name)
    if time_window and time_window[0] and time_window[1]:
        time_window_display = f"{time_window[0]}–{time_window[1]}"
        is_part_time = True
    else:
        time_window_display = "Full day (default)"
        is_part_time = False
    
    # Filter observations: exclude non-attendance days
    non_attendance_dates = [info[0] for info in non_attendance_info]
    
    filt = all_obs[
        (all_obs["obs_date_dt"].dt.date >= date_from) &
        (all_obs["obs_date_dt"].dt.date <= date_to) &
        (~all_obs["obs_date_dt"].dt.date.isin(non_attendance_dates)) &  # Exclude non-attendance
        (all_obs["regulated"].notna()) &
        (all_obs["regulated"].str.strip() != "")
    ].copy()

    if filt.empty:
        st.info("No regulation data in this range."); st.stop()

    filt["State"]  = filt["regulated"].map({k: v["emoji"]+" "+v["label"] for k,v in REG_STATES.items()})
    colour_map     = {v["emoji"]+" "+v["label"]: v["fg"] for v in REG_STATES.values()}
    state_order    = [v["emoji"]+" "+v["label"] for v in REG_STATES.values()]

    # ── Time frame and attendance summary ─────────────────────────────────────
    slot_mins = filt["time_slot"].dropna().apply(_slot_to_min)
    min_slot  = filt.loc[slot_mins.idxmin(), "time_slot"] if not slot_mins.empty else "—"
    max_slot  = filt.loc[slot_mins.idxmax(), "time_slot"] if not slot_mins.empty else "—"
    n_days_with_data = filt["obs_date_dt"].dt.date.nunique()
    date_span = f"{date_from.strftime('%-d %b')} – {date_to.strftime('%-d %b %Y')}"
    
    # Attendance summary
    non_attendance_days = len(non_attendance_info)
    attendance_pct = round(100 * attendance_days / total_school_days) if total_school_days else 0

    st.markdown(
        f'<div style="background:#f0f9ff;border:1.5px solid #7dd3fc;border-radius:8px;'
        f'padding:.55rem 1rem;margin-bottom:.6rem;font-size:.82rem;color:#0c4a6e;">'
        f'<strong>📅 Period:</strong> {date_span} &nbsp;·&nbsp; '
        f'<strong>{n_days_with_data} day{"s" if n_days_with_data != 1 else ""}</strong> with data recorded'
        f'</div>',
        unsafe_allow_html=True)
    
    # Attendance breakdown
    att_col1, att_col2 = st.columns([2, 3])
    with att_col1:
        st.markdown(
            f'<div style="background:#dcfce7;border:1.5px solid #16a34a;border-radius:8px;'
            f'padding:.5rem .9rem;font-size:.8rem;">'
            f'<div style="color:#15803d;font-weight:700;margin-bottom:.2rem;">✅ Attendance</div>'
            f'<div style="color:#166534;"><strong>{attendance_days}</strong> of {total_school_days} school days '
            f'<span style="font-weight:600;">({attendance_pct}%)</span></div>'
            f'</div>',
            unsafe_allow_html=True)
    
    with att_col2:
        if non_attendance_days > 0:
            non_att_summary = ", ".join([f"{d.strftime('%-d/%m')} ({s})" for d, s in non_attendance_info[:3]])
            if non_attendance_days > 3:
                non_att_summary += f" +{non_attendance_days - 3} more"
            
            st.markdown(
                f'<div style="background:#fef9c3;border:1.5px solid #eab308;border-radius:8px;'
                f'padding:.5rem .9rem;font-size:.8rem;">'
                f'<div style="color:#854d0e;font-weight:700;margin-bottom:.2rem;">⚠️ Non-attendance</div>'
                f'<div style="color:#713f12;">{non_attendance_days} day{"s" if non_attendance_days != 1 else ""}: '
                f'{non_att_summary}</div>'
                f'</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div style="background:#f1f5f9;border:1.5px solid #94a3b8;border-radius:8px;'
                f'padding:.5rem .9rem;font-size:.8rem;">'
                f'<div style="color:#475569;font-weight:600;">No absences marked</div>'
                f'</div>',
                unsafe_allow_html=True)
    
    # Time window info
    st.markdown(
        f'<div style="background:#fef3c7;border:1.5px solid #f59e0b;border-radius:8px;'
        f'padding:.45rem .9rem;margin-top:.5rem;font-size:.78rem;color:#78350f;">'
        f'<strong>⏰ Observation hours:</strong> {time_window_display}'
        + (' <span style="background:#dc2626;color:white;padding:.1rem .4rem;border-radius:3px;font-size:.7rem;font-weight:600;">PART-TIME</span>' if is_part_time else '')
        + f' &nbsp;·&nbsp; <strong>Expected intervals:</strong> {expected_intervals} '
        f'({attendance_days} days × time window)'
        f'</div>',
        unsafe_allow_html=True)

    # ── Prevention & Regulation (the "what could have been" story) ────────────
    st.markdown("<div style='margin:.8rem 0 .2rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:1rem;font-weight:800;color:#1A6B8A;">'
                '🛡️ Prevention &amp; Regulation</div>', unsafe_allow_html=True)
    st.caption("Regulation maintained through site modifications — and the escalations that were caught and turned around.")

    _band_map = {"in_window": "In window", "coping": "Coping",
                 "hyperaroused": "Outside window", "hypoaroused": "Outside window"}
    _bands = filt["regulated"].map(_band_map)
    total_int = int(len(filt))
    n_win = int((_bands == "In window").sum())
    n_cop = int((_bands == "Coping").sum())
    n_out = int((_bands == "Outside window").sum())
    pct_wincop = round(100 * (n_win + n_cop) / total_int) if total_int else 0
    pct_out    = round(100 * n_out / total_int) if total_int else 0

    # Saves in range
    saves_all = load_all_saves(student_name)
    if not saves_all.empty:
        sv = saves_all[(saves_all["obs_date_dt"].dt.date >= date_from) &
                       (saves_all["obs_date_dt"].dt.date <= date_to)].copy()
    else:
        sv = pd.DataFrame()
    n_saves = int(len(sv))
    n_succ  = int(sv["outcome"].isin(["returned_to_window", "held_in_coping"]).sum()) if n_saves else 0
    succ_rate = round(100 * n_succ / n_saves) if n_saves else 0

    # Proactive support dose (intervals with a support logged + saves)
    mod_dose = 0
    if "support_used" in filt.columns:
        mod_dose = int(filt["support_used"].fillna("").apply(
            lambda s: bool(str(s).strip()) and str(s).strip() not in ("None",)).sum())
    mod_dose += n_saves

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi kpi-g"><div class="val">{pct_wincop}%</div>'
                    f'<div class="lbl">Intervals in window or coping</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="kpi kpi-r"><div class="val">{pct_out}%</div>'
                    f'<div class="lbl">Intervals outside window</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi kpi-b"><div class="val">{n_saves}</div>'
                    f'<div class="lbl">Saves logged</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi kpi-g"><div class="val">{n_succ}</div>'
                    f'<div class="lbl">Escalations turned around</div></div>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:.76rem;color:#475569;margin:.1rem 0 .5rem;">'
        f'<strong>{mod_dose}</strong> proactive supports recorded across this period'
        + (f' &nbsp;·&nbsp; saves de-escalation rate <strong>{succ_rate}%</strong> '
           f'({n_succ} of {n_saves} held in or returned to window)' if n_saves else '')
        + '</div>', unsafe_allow_html=True)

    # Regulation profile by week — shows the coping → in-window shift over time
    fdf = filt.copy()
    fdf["band"] = _bands.values
    fdf["wkdt"] = fdf["obs_date_dt"].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
    fdf["wk"]   = fdf["wkdt"].dt.strftime("%-d %b")
    wk_order = fdf.sort_values("wkdt")["wk"].unique().tolist()
    if len(wk_order) >= 1:
        tot_wk = fdf.groupby("wk").size().to_dict()
        band_cols = {"In window": "#16a34a", "Coping": "#ca8a04", "Outside window": "#dc2626"}
        figp = go.Figure()
        for bname, bcol in band_cols.items():
            yvals = []
            for wk in wk_order:
                sub = fdf[(fdf["wk"] == wk) & (fdf["band"] == bname)]
                yvals.append(round(100 * len(sub) / tot_wk[wk], 1) if tot_wk.get(wk) else 0)
            figp.add_trace(go.Bar(name=bname, x=wk_order, y=yvals, marker_color=bcol,
                                  text=[f"{v:.0f}%" if v >= 8 else "" for v in yvals],
                                  textposition="inside", insidetextanchor="middle"))
        figp.update_layout(barmode="stack", height=330, margin=dict(l=45, r=20, t=30, b=40),
                           yaxis_title="% of intervals", legend=dict(orientation="h", y=1.12),
                           font=dict(size=12), plot_bgcolor="white")
        figp.update_yaxes(range=[0, 100], gridcolor="#eef2f6")
        st.markdown('<div style="font-size:.82rem;font-weight:700;color:#334155;margin:.3rem 0 .1rem;">'
                    'Regulation profile by week</div>', unsafe_allow_html=True)
        st.plotly_chart(figp, use_container_width=True)
        st.caption("A shrinking amber band with a growing green band over time is the goal: "
                   "less scaffolding needed to stay regulated.")

    # Saves detail
    if n_saves:
        sv["wkdt"] = sv["obs_date_dt"].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
        sv["wk"]   = sv["wkdt"].dt.strftime("%-d %b")
        sv["res"]  = sv["outcome"].map({k: v["label"] for k, v in SAVE_OUTCOMES.items()})
        sv_wk_order = sv.sort_values("wkdt")["wk"].unique().tolist()
        out_cols = {v["label"]: v["fg"] for v in SAVE_OUTCOMES.values()}
        figs = go.Figure()
        for lbl, col in out_cols.items():
            yv = [int(((sv["wk"] == wk) & (sv["res"] == lbl)).sum()) for wk in sv_wk_order]
            figs.add_trace(go.Bar(name=lbl, x=sv_wk_order, y=yv, marker_color=col))
        figs.update_layout(barmode="stack", height=300, margin=dict(l=45, r=20, t=30, b=40),
                           yaxis_title="saves", legend=dict(orientation="h", y=1.15),
                           font=dict(size=12), plot_bgcolor="white")
        figs.update_yaxes(gridcolor="#eef2f6")
        st.markdown('<div style="font-size:.82rem;font-weight:700;color:#334155;margin:.5rem 0 .1rem;">'
                    'Saves by week &amp; outcome</div>', unsafe_allow_html=True)
        st.plotly_chart(figs, use_container_width=True)

        # ── Support analysis: usage, effectiveness, repertoire ────────────────
        # Explode supports across all saves, keeping each save's outcome alongside.
        exp = sv[["support_used", "early_sign", "outcome"]].copy()
        exp["support_used"] = exp["support_used"].fillna("")
        exp["sup"] = exp["support_used"].str.split(", ")
        exp = exp.explode("sup")
        exp["sup"] = exp["sup"].str.strip()
        exp = exp[exp["sup"] != ""]

        if not exp.empty:
            exp["ok"] = exp["outcome"].isin(["returned_to_window", "held_in_coping"])
            eff = (exp.groupby("sup")
                      .agg(used=("ok", "size"), turned=("ok", "sum"))
                      .reset_index())
            eff["rate"] = (100 * eff["turned"] / eff["used"]).round()
            eff = eff.sort_values(["used", "rate"], ascending=[False, False])

            st.markdown('<div style="font-size:.82rem;font-weight:700;color:#334155;margin:.6rem 0 .1rem;">'
                        'Support effectiveness — what turns this student around</div>',
                        unsafe_allow_html=True)
            st.caption("How often each support was applied during a save, and how often that save ended in "
                       "the student returning to window or being held in coping. Higher bars used more often; "
                       "the % is the turn-around rate. ⚠️ Treat supports used fewer than 3 times as indicative only.")

            # Horizontal bar: usage with success portion shaded, rate + n labelled
            eff_plot = eff.sort_values("used")
            fige = go.Figure()
            fige.add_trace(go.Bar(
                y=eff_plot["sup"], x=eff_plot["turned"], orientation="h",
                name="Turned around", marker_color="#16a34a"))
            fige.add_trace(go.Bar(
                y=eff_plot["sup"], x=(eff_plot["used"] - eff_plot["turned"]), orientation="h",
                name="Escalated anyway", marker_color="#dc2626"))
            fige.update_layout(
                barmode="stack", height=max(240, len(eff_plot) * 30 + 80),
                margin=dict(l=10, r=20, t=30, b=35),
                xaxis_title="times applied during saves",
                legend=dict(orientation="h", y=1.08), font=dict(size=12), plot_bgcolor="white")
            fige.update_xaxes(gridcolor="#eef2f6", tickformat="d")
            st.plotly_chart(fige, use_container_width=True)

            # Effectiveness table with low-n flag
            tbl = eff.copy()
            tbl["Support"] = tbl["sup"]
            tbl["Times applied"] = tbl["used"].astype(int)
            tbl["Turned around"] = tbl["turned"].astype(int)
            tbl["Turn-around rate"] = tbl.apply(
                lambda r: (f"{int(r['rate'])}%" + ("  ⚠️ low n" if r["used"] < 3 else "")), axis=1)
            st.dataframe(
                tbl[["Support", "Times applied", "Turned around", "Turn-around rate"]]
                   .set_index("Support"),
                use_container_width=True)

            # ── Response repertoire: which supports for which early sign ───────
            rep = sv[["early_sign", "support_used"]].copy()
            rep["early_sign"] = rep["early_sign"].fillna("")
            rep["support_used"] = rep["support_used"].fillna("")
            rep["sign"] = rep["early_sign"].str.split(", ")
            rep = rep.explode("sign")
            rep["sign"] = rep["sign"].str.strip()
            rep = rep[rep["sign"] != ""]
            if not rep.empty:
                st.markdown('<div style="font-size:.82rem;font-weight:700;color:#334155;margin:.7rem 0 .1rem;">'
                            'Response repertoire — supports used for each early sign</div>',
                            unsafe_allow_html=True)
                st.caption("The go-to supports staff reach for when each warning sign appears. Useful for "
                           "building a shared, consistent response plan.")
                sign_order = rep["sign"].value_counts().index.tolist()
                rep_rows = []
                for sgn in sign_order:
                    sub = rep[rep["sign"] == sgn]
                    sup_counts = (sub["support_used"].str.split(", ").explode().str.strip())
                    sup_counts = sup_counts[sup_counts != ""].value_counts().head(3)
                    top_txt = ", ".join(f"{s} ({c})" for s, c in sup_counts.items()) or "—"
                    rep_rows.append({"Early sign": f"{sgn}  ·  {len(sub)}×", "Most-used supports": top_txt})
                st.dataframe(pd.DataFrame(rep_rows).set_index("Early sign"), use_container_width=True)

            st.caption("Note: supports are often applied to the hardest moments, so a lower turn-around rate "
                       "may reflect harder situations rather than a weaker support. Read alongside the regulation "
                       "trend and anecdotal notes, not in isolation.")
    else:
        st.info("No saves logged in this period yet. Log saves from the **Record & View** tab "
                "(⚡ Log a SAVE) to build the prevention picture.")

    st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:.7rem 0;'>", unsafe_allow_html=True)

    # ── Daily notes (anecdotal context) ───────────────────────────────────────
    daily_notes = get_all_daily_notes(student_name, date_from, date_to)
    if daily_notes:
        st.markdown("<div style='margin:.6rem 0;'></div>", unsafe_allow_html=True)
        with st.expander(f"📝 Daily notes — anecdotal context ({len(daily_notes)} day{'s' if len(daily_notes) != 1 else ''} with notes)", expanded=True):
            for note_date_str, note_text in sorted(daily_notes.items()):
                note_date = datetime.strptime(note_date_str, "%Y-%m-%d").date()
                day_name = DAYS[note_date.weekday()] if note_date.weekday() < 5 else note_date.strftime("%A")
                
                st.markdown(
                    f'<div style="background:#fef9c3;border-left:3px solid #eab308;padding:.5rem .8rem;'
                    f'margin-bottom:.5rem;font-size:.8rem;">'
                    f'<div style="font-weight:700;color:#854d0e;margin-bottom:.2rem;">'
                    f'{day_name} {note_date.strftime("%-d %b %Y")}</div>'
                    f'<div style="color:#713f12;">{note_text}</div>'
                    f'</div>',
                    unsafe_allow_html=True)

    st.markdown("<div style='margin:.6rem 0;'></div>", unsafe_allow_html=True)

    # ── What does "interval" mean? ────────────────────────────────────────────
    data_collection_rate = round(100 * len(filt) / expected_intervals) if expected_intervals else 0
    
    st.info(
        f"ℹ️ **What is an interval?** Each interval represents one 15-minute observation window. "
        f"This student's expected intervals: **{expected_intervals}** (based on {attendance_days} attendance days "
        f"and their observation hours). Data was recorded for **{len(filt)} intervals ({data_collection_rate}%)**. "
        f"Non-attendance days (absent/holiday/transition) are excluded from analysis."
    )

    n_tot  = len(filt)
    n_win  = int((filt["regulated"]=="in_window").sum())
    n_cop  = int((filt["regulated"]=="coping").sum())
    n_hyp  = int((filt["regulated"]=="hyperaroused").sum())
    n_hypo = int((filt["regulated"]=="hypoaroused").sum())

    pct_inwin = round(100*n_win/n_tot) if n_tot else 0
    pct_cop_only = round(100*n_cop/n_tot) if n_tot else 0

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.markdown(f"<div class='kpi'><div class='val'>{n_tot}</div><div class='lbl'>Intervals recorded<br><span style='font-size:.58rem;'>{data_collection_rate}% of expected</span></div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi kpi-g'><div class='val'>{n_win}</div><div class='lbl'>🟢 In window<br><span style='font-size:.58rem;'>{pct_inwin}%</span></div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi kpi-y'><div class='val'>{n_cop}</div><div class='lbl'>🟡 Coping<br><span style='font-size:.58rem;'>{pct_cop_only}% — at edge</span></div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi kpi-r'><div class='val'>{n_hyp}</div><div class='lbl'>🔴 Hyperaroused</div></div>", unsafe_allow_html=True)
    k5.markdown(f"<div class='kpi kpi-b'><div class='val'>{n_hypo}</div><div class='lbl'>🔵 Hypoaroused</div></div>", unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:.8rem;color:#475569;text-align:center;margin:.3rem 0 .2rem;">'
        f'<strong>{pct_inwin}%</strong> of intervals fully within the window of tolerance '
        f'({n_win} of {n_tot}). &nbsp;'
        f'<strong>{pct_cop_only}%</strong> coping (at edge — student is managing but struggling).</div>'
        f'<div style="font-size:.75rem;color:#dc2626;text-align:center;margin:0 0 .6rem;">'
        f'⚠️ Only <em>In window</em> (green) indicates genuine regulation. '
        f'A predominantly yellow day is still a difficult day.</div>',
        unsafe_allow_html=True)

    st.markdown("---")

    # ── Chart 1: Regulation across the day ───────────────────────────────────
    st.markdown("##### 📊 Regulation state across the day")
    st.caption(
        f"Each bar represents one 15-minute time slot. Height = number of intervals recorded at that time. "
        f"Colour shows regulation state across **{attendance_days} attendance days** (non-attendance days excluded). "
        f"Time window: {time_window_display}"
    )
    slot_df = filt.groupby(["time_slot","State"]).size().reset_index(name="n")
    slot_df["sort_k"] = slot_df["time_slot"].apply(_slot_to_min)
    slot_df = slot_df.sort_values("sort_k")
    # Only show states that actually have data
    active_states_slot = [s for s in state_order if s in slot_df["State"].values]
    fig1 = px.bar(slot_df, x="time_slot", y="n", color="State",
        color_discrete_map=colour_map, barmode="stack",
        labels={"time_slot":"Time","n":"Intervals","State":""},
        category_orders={"State": active_states_slot})
    fig1.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(tickangle=-45, gridcolor="#e2e8f0", title=""),
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="15-min intervals recorded"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=55,b=70))
    st.plotly_chart(fig1, use_container_width=True)
    ss["rpt_fig1"] = _rpt_fig(fig1, height=400, margin_b=130, margin_l=70).to_html(full_html=False, include_plotlyjs=False)

    # Hypothesis: time-of-day
    best_slot = slot_df[slot_df["State"].str.contains("In window")].groupby("time_slot")["n"].sum()
    worst_slot_df = slot_df[slot_df["State"].str.contains("Hyperaroused|Hypoaroused")].groupby("time_slot")["n"].sum()
    best_t  = best_slot.idxmax()  if not best_slot.empty  else None
    worst_t = worst_slot_df.idxmax() if not worst_slot_df.empty else None
    hyp1_prompt = (
        f"Student attended {attendance_days} school days in this period (non-attendance days excluded). "
        f"Observation hours: {time_window_display}. "
        f"{n_tot} intervals recorded ({data_collection_rate}% of {expected_intervals} expected). "
        f"Regulation breakdown: {n_win} fully in-window (regulated), {n_cop} coping (at the edge — actively managing but not fully regulated), {n_hyp} hyperaroused, {n_hypo} hypoaroused. "
        f"Note: 'coping' means the student is at the edge of their window and actively managing — it is NOT a successful state. "
        + (f"Time slot with highest in-window count: {best_t}. " if best_t else "")
        + (f"Most dysregulation observed at: {worst_t}. " if worst_t else "")
        + "Interpret this time-of-day pattern and its implications for scheduling and support."
    )
    with st.spinner("Generating hypothesis…"):
        hyp1 = _groq_hypothesis(hyp1_prompt)
    if hyp1:
        _hypothesis_box(hyp1, key="rpt_hyp_time")
    else:
        best_str  = f"Best full regulation is seen at {best_t}. " if best_t else ""
        worst_str = f"Dysregulation is most prominent at {worst_t}. " if worst_t else ""
        _hypothesis_box(
            f"{n_win} of {n_tot} intervals ({round(100*n_win/n_tot) if n_tot else 0}%) were fully within the window of tolerance. "
            + best_str + worst_str +
            "This pattern suggests consideration of scheduling demands and staffing intensity "
            "relative to time of day when planning this student's program.",
            key="rpt_hyp_time"
        )

    st.markdown("---")

    # ── Chart 2: Daily regulation trend ──────────────────────────────────────
    st.markdown("##### 📈 Daily regulation trend")
    
    # Load daily notes for this period to mark days with notes
    daily_notes = get_all_daily_notes(student_name, date_from, date_to)
    has_notes = len(daily_notes) > 0
    
    st.caption(
        f"Percentage of each day's recorded intervals in each regulation state, "
        f"across **{n_days_with_data} attendance days with data** (non-attendance days excluded). "
        "Only states that were actually observed appear. "
        "The dashed green line marks the 70% in-window benchmark. "
        "🟡 Coping = dysregulated — at the edge of the window."
        + (" **📝 Days with notes are marked with a note icon.**" if has_notes else "")
    )

    # ── Robust daily % calc (avoids pandas groupby.apply lambda issues) ───────
    _dc = filt.groupby(["obs_date_dt","regulated"]).size().unstack(fill_value=0)
    _dt = _dc.sum(axis=1)
    _daily = pd.DataFrame(index=_dc.index)
    for _state, _col in [("in_window","pct_win"),("coping","pct_cop"),
                          ("hyperaroused","pct_hyp"),("hypoaroused","pct_hypo")]:
        _daily[_col] = (_dc.get(_state, pd.Series(0, index=_dc.index)) / _dt * 100).round(0).astype(int)
    _daily = _daily.reset_index()
    _daily["date_lbl"] = pd.to_datetime(_daily["obs_date_dt"]).dt.strftime("%a %-d %b")
    
    # Mark days with notes
    _daily["has_note"] = _daily["obs_date_dt"].apply(
        lambda d: d.strftime("%Y-%m-%d") in daily_notes
    )

    # Build grouped bar chart — clearer than lines for ≤10 data points
    _state_cfg = [
        ("pct_win",  "🟢 In window",    "#16a34a"),
        ("pct_cop",  "🟡 Coping ⚠️",   "#ca8a04"),
        ("pct_hyp",  "🔴 Hyperaroused", "#dc2626"),
        ("pct_hypo", "🔵 Hypoaroused",  "#2563eb"),
    ]
    fig2 = go.Figure()
    for col, name, col_c in _state_cfg:
        if _daily[col].max() > 0:
            fig2.add_trace(go.Bar(
                name=name,
                x=_daily["date_lbl"],
                y=_daily[col],
                marker_color=col_c,
                text=_daily[col].astype(str) + "%",
                textposition="inside",
                textfont=dict(color="white", size=11, family="Arial"),
                hovertemplate=f"{name}: %{{y}}%<extra></extra>",
            ))
    
    # Add note markers above bars for days with notes
    if has_notes:
        days_with_notes = _daily[_daily["has_note"]]
        for idx, row in days_with_notes.iterrows():
            fig2.add_annotation(
                x=row["date_lbl"],
                y=105,  # Position above the bars
                text="📝",
                showarrow=False,
                font=dict(size=16),
                xanchor="center",
                yanchor="bottom"
            )
    
    fig2.add_hline(y=70, line_dash="dot", line_color="#16a34a", line_width=2,
                   annotation_text="70% in-window target",
                   annotation_font_color="#16a34a",
                   annotation_font_size=11,
                   annotation_position="bottom right")
    fig2.update_layout(
        barmode="group",
        height=350,
        plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(range=[0,110], gridcolor="#e2e8f0", title="% of intervals", ticksuffix="%"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=60,b=20),
        bargap=0.25, bargroupgap=0.05,
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Key for note markers
    if has_notes:
        st.markdown(
            '<div style="background:#fef9c3;border-left:3px solid #eab308;padding:.35rem .7rem;'
            'margin-top:.3rem;font-size:.75rem;color:#854d0e;">'
            '<strong>📝 Note:</strong> Days marked with 📝 have anecdotal notes. '
            'See the "Daily notes" section above for details.</div>',
            unsafe_allow_html=True
        )

    # ── Report version: pure HTML table with CSS bars — no Plotly export issues ──
    _state_colours = {
        "pct_win":  ("#16a34a", "#dcfce7", "🟢 In window"),
        "pct_cop":  ("#ca8a04", "#fef9c3", "🟡 Coping ⚠️"),
        "pct_hyp":  ("#dc2626", "#fee2e2", "🔴 Hyperaroused"),
        "pct_hypo": ("#2563eb", "#dbeafe", "🔵 Hypoaroused"),
    }
    _rpt_daily_html = """
<table style="border-collapse:collapse;width:100%;font-size:.82rem;margin:.4rem 0 .6rem;">
<thead><tr style="background:#1A6B8A;color:white;">
  <th style="padding:.4rem .7rem;text-align:left;">Date</th>
  <th style="padding:.4rem .7rem;text-align:center;color:#86efac;">🟢 In window</th>
  <th style="padding:.4rem .7rem;text-align:center;color:#fde68a;">🟡 Coping ⚠️</th>
  <th style="padding:.4rem .7rem;text-align:center;color:#fca5a5;">🔴 Hyperaroused</th>
  <th style="padding:.4rem .7rem;text-align:center;color:#93c5fd;">🔵 Hypoaroused</th>
</tr></thead><tbody>"""
    for _, _r in _daily.iterrows():
        _rpt_daily_html += f'<tr><td style="padding:.38rem .7rem;font-weight:600;border-bottom:1px solid #e2e8f0;white-space:nowrap;">{_r["date_lbl"]}</td>'
        for _col, (_fg, _bg, _lbl) in _state_colours.items():
            _v = int(_r[_col])
            # Mini horizontal bar inside the cell
            _bar = (f'<div style="background:{_bg};border-radius:4px;height:18px;width:100%;position:relative;">'
                    f'<div style="background:{_fg};border-radius:4px;height:18px;width:{_v}%;"></div>'
                    f'<span style="position:absolute;left:50%;top:0;transform:translateX(-50%);'
                    f'font-weight:700;font-size:.8rem;line-height:18px;color:{"white" if _v>30 else _fg};">'
                    f'{_v}%</span></div>')
            _rpt_daily_html += f'<td style="padding:.25rem .5rem;border-bottom:1px solid #e2e8f0;min-width:100px;">{_bar}</td>'
        _rpt_daily_html += '</tr>'
    _rpt_daily_html += '</tbody></table>'
    # 70% benchmark note
    _rpt_daily_html += '<p style="font-size:.75rem;color:#475569;margin:.1rem 0 .5rem;">Dashed green benchmark: 70% in-window is the target. 🟡 Coping = dysregulated — at the edge of the window.</p>'
    ss["rpt_fig2"] = _rpt_daily_html

    # Make the daily df available for report
    daily = _daily

    st.markdown("---")

    # ── Chart 3: Day of week ──────────────────────────────────────────────────
    st.markdown("##### 📅 Regulation by day of week")
    st.caption(
        "Total intervals per day across the observation period, coloured by regulation state. "
        "Taller bars mean more intervals were recorded on that day. "
        "The colour split shows how regulation varied across days of the week."
    )
    dow = filt.groupby(["day_of_week","State"]).size().reset_index(name="n")
    dow["sort_k"] = dow["day_of_week"].apply(lambda d: DAYS.index(d) if d in DAYS else 9)
    dow = dow.sort_values("sort_k")
    active_states_dow = [s for s in state_order if s in dow["State"].values]
    # Best day = highest % fully IN WINDOW (not coping — coping means struggling)
    _dow_counts = filt.groupby(["day_of_week","regulated"]).size().unstack(fill_value=0)
    _dow_total  = _dow_counts.sum(axis=1)
    dow_win = (_dow_counts.get("in_window", pd.Series(0, index=_dow_counts.index)) / _dow_total * 100).round(0).astype(int).reset_index(name="pct_win")
    dow_cop = (_dow_counts.get("coping",    pd.Series(0, index=_dow_counts.index)) / _dow_total * 100).round(0).astype(int).reset_index(name="pct_cop")
    dow_reg = dow_win.merge(dow_cop, on="day_of_week")
    dow_reg["sort_k"] = dow_reg["day_of_week"].apply(lambda d: DAYS.index(d) if d in DAYS else 9)
    dow_reg = dow_reg.sort_values("sort_k")
    best_day  = dow_reg.loc[dow_reg["pct_win"].idxmax(), "day_of_week"] if not dow_reg.empty else None
    worst_day = dow_reg.loc[dow_reg["pct_win"].idxmin(), "day_of_week"] if not dow_reg.empty else None
    best_pct  = dow_reg["pct_win"].max() if not dow_reg.empty else 0
    worst_pct = dow_reg["pct_win"].min() if not dow_reg.empty else 0

    fig4 = px.bar(dow, x="day_of_week", y="n", color="State",
        color_discrete_map=colour_map, barmode="stack",
        labels={"day_of_week":"","n":"Intervals","State":""},
        category_orders={"day_of_week": DAYS, "State": active_states_dow})
    fig4.update_layout(height=280, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0",
                   title="15-min intervals recorded"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig4, use_container_width=True)
    ss["rpt_fig4"] = _rpt_fig(fig4, height=320, margin_b=55, margin_l=65).to_html(full_html=False, include_plotlyjs=False)

    # Build a separate NORMALISED (100% stacked) bar for the report so bar height
    # always reflects the proportion, not raw count — matches the % table below.
    fig4_pct = px.bar(dow, x="day_of_week", y="n", color="State",
        color_discrete_map=colour_map, barmode="relative",
        labels={"day_of_week":"","n":"Intervals","State":""},
        category_orders={"day_of_week": DAYS, "State": active_states_dow})
    fig4_pct.update_layout(barnorm="percent")
    fig4_pct.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="% of intervals",
                   ticksuffix="%", range=[0,105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=10,r=10,t=50,b=10))
    ss["rpt_fig4_pct"] = _rpt_fig(fig4_pct, height=320, margin_b=55, margin_l=70).to_html(full_html=False, include_plotlyjs=False)

    # Per-day summary under chart
    dow_summary_parts = []
    for _, r in dow_reg.iterrows():
        dow_summary_parts.append(
            f"<strong>{r['day_of_week'][:3]}:</strong> {r['pct_win']}% in-window, {r['pct_cop']}% coping"
        )
    st.markdown(
        '<div style="font-size:.75rem;color:#475569;margin:.2rem 0 .5rem;">'
        + " &nbsp;·&nbsp; ".join(dow_summary_parts) + "</div>",
        unsafe_allow_html=True)
    st.caption(
        "⚠️ 'In window' (green) is the only indicator of genuine regulation. "
        "'Coping' (yellow) means the student is at the edge of their window and actively managing — "
        "a predominantly yellow day still represents a student who is struggling."
    )

    hyp_dow_prompt = (
        f"Student regulation by day of week — % of intervals FULLY IN WINDOW (regulated): "
        + ", ".join(f"{r['day_of_week']} {r['pct_win']}% in-window / {r['pct_cop']}% coping" for _, r in dow_reg.iterrows()) + ". "
        + f"IMPORTANT: 'coping' means the student is at the edge of their window and struggling — it is NOT a successful state. "
        + (f"Best day is {best_day} ({best_pct}% fully in-window). " if best_day else "")
        + (f"Most difficult day is {worst_day} ({worst_pct}% fully in-window). " if worst_day else "")
        + "Interpret this weekly pattern using Window of Tolerance framework. "
          "What might explain why the student is more regulated on certain days? "
          "Pose specific questions the team should investigate about the most difficult day."
    )
    with st.spinner("Generating hypothesis…"):
        hyp_dow = _groq_hypothesis(hyp_dow_prompt)
    if hyp_dow:
        _hypothesis_box(hyp_dow, key="rpt_hyp_dow")
    else:
        _hypothesis_box(
            (f"The student demonstrates the highest proportion of fully regulated intervals on {best_day} ({best_pct}% in-window). " if best_day else "")
            + (f"The most challenging day is {worst_day}, with only {worst_pct}% of intervals reaching full regulation. " if worst_day and worst_day != best_day else "")
            + "Note that days with a high proportion of 'coping' intervals still represent a student who is actively struggling — "
              "coping is the edge of the window, not a position of stability. "
              "The team should investigate what structural differences exist between the best and worst days: "
              "timetable, staffing, peer groupings, and the sequence and demands of activities.",
            key="rpt_hyp_dow"
        )

    st.markdown("---")

    # ── Chart 4: Support / grouping type volume ───────────────────────────────
    sup_filt = filt[
        filt.get("grouping_type", pd.Series(dtype=str)).notna() &
        (filt.get("grouping_type", pd.Series(dtype=str)).str.strip() != "")
    ].copy() if "grouping_type" in filt.columns else pd.DataFrame()

    if not sup_filt.empty:
        st.markdown("##### 👥 Level of support — how often was each grouping recorded?")
        st.caption(
            "Shows the total number of 15-minute intervals recorded under each support/grouping arrangement, "
            "coloured by the regulation state during that interval. "
            "This identifies which support type is most frequently used and how effective it is."
        )
        sup_filt["Grouping"] = sup_filt["grouping_type"].map(GROUPING_TYPES).fillna(sup_filt["grouping_type"])

        # Volume chart: total intervals per grouping, colour = regulation state
        grp_state = sup_filt.groupby(["Grouping","State"]).size().reset_index(name="n")
        active_states_grp = [s for s in state_order if s in grp_state["State"].values]
        fig_grp = px.bar(grp_state, x="n", y="Grouping", color="State",
            color_discrete_map=colour_map, barmode="stack", orientation="h",
            labels={"Grouping":"","n":"Intervals","State":""},
            category_orders={"State": active_states_grp})
        fig_grp.update_layout(height=max(220, len(grp_state["Grouping"].unique())*60+80),
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(autorange="reversed"),
            xaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="15-min intervals recorded"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
            margin=dict(l=10,r=10,t=50,b=10))
        st.plotly_chart(fig_grp, use_container_width=True)

        # ── Report version: pure HTML — Plotly horizontal bar exports are unreliable ──
        _grp_totals = sup_filt.groupby("Grouping").size().sort_values(ascending=False)
        _max_n = _grp_totals.max() if not _grp_totals.empty else 1
        _state_bar_cfg = [
            ("in_window",    "#16a34a", "🟢 In window"),
            ("coping",       "#ca8a04", "🟡 Coping ⚠️"),
            ("hyperaroused", "#dc2626", "🔴 Hyperaroused"),
            ("hypoaroused",  "#2563eb", "🔵 Hypoaroused"),
        ]
        _grp_html = """
<table style="border-collapse:collapse;width:100%;font-size:.82rem;margin:.4rem 0 .6rem;">
<thead><tr style="background:#1A6B8A;color:white;">
  <th style="padding:.4rem .8rem;text-align:left;min-width:130px;">Support type</th>
  <th style="padding:.4rem .8rem;text-align:center;">Total intervals</th>
  <th style="padding:.4rem .8rem;text-align:left;" colspan="2">Intervals by regulation state</th>
</tr></thead><tbody>"""
        for _grp_name, _grp_total in _grp_totals.items():
            _grp_sub = sup_filt[sup_filt["Grouping"] == _grp_name]
            # One row per grouping showing stacked segments
            _bar_segments = ""
            for _reg_key, _fg, _lbl in _state_bar_cfg:
                _cnt = int((_grp_sub["regulated"] == _reg_key).sum())
                if _cnt > 0:
                    _pct_of_max = round(100 * _cnt / _max_n)
                    _pct_of_grp = round(100 * _cnt / _grp_total)
                    _bar_segments += (
                        f'<span title="{_lbl}: {_cnt} intervals ({_pct_of_grp}%)" '
                        f'style="display:inline-block;height:22px;width:{_pct_of_max}%;'
                        f'background:{_fg};border-radius:3px;margin-right:2px;'
                        f'vertical-align:middle;min-width:2px;"></span>'
                    )
            _detail_parts = []
            for _reg_key, _fg, _lbl in _state_bar_cfg:
                _cnt = int((_grp_sub["regulated"] == _reg_key).sum())
                if _cnt > 0:
                    _pct_of_grp = round(100 * _cnt / _grp_total)
                    _detail_parts.append(
                        f'<span style="color:{_fg};font-weight:700;">{_lbl}: {_cnt} ({_pct_of_grp}%)</span>'
                    )
            _grp_html += (
                f'<tr style="border-bottom:1px solid #e2e8f0;">'
                f'<td style="padding:.45rem .8rem;font-weight:700;white-space:nowrap;">{_grp_name}</td>'
                f'<td style="padding:.45rem .8rem;text-align:center;font-weight:700;">{_grp_total}</td>'
                f'<td style="padding:.45rem .8rem;width:35%;">{_bar_segments}</td>'
                f'<td style="padding:.45rem .8rem;font-size:.78rem;">{" &nbsp; ".join(_detail_parts)}</td>'
                f'</tr>'
            )
        _grp_html += "</tbody></table>"
        _grp_html += '<p style="font-size:.75rem;color:#475569;margin:.1rem 0 .5rem;">Bar width is proportional to the grouping with the most intervals. Each colour segment represents a regulation state.</p>'
        ss["rpt_fig_grp"] = _grp_html

        # Regulation breakdown table (replaces misleading % heatmap)
        st.markdown("**Regulation breakdown by support type** — counts and percentages")
        st.caption(
            "Shows how many 15-minute intervals were recorded in each regulation state per support arrangement. "
            "⚠️ Rows with fewer than 3 intervals should be interpreted with caution — "
            "a single interval showing 100% in-window or 100% dysregulated reflects only one moment, not a pattern."
        )
        # Build a readable table
        pivot_counts = sup_filt.groupby(["Grouping","State"]).size().unstack(fill_value=0)
        pivot_counts["Total"] = pivot_counts.sum(axis=1)
        ordered_state_cols = [s for s in state_order if s in pivot_counts.columns]
        table_rows = []
        for grp_name, row in pivot_counts.iterrows():
            total = int(row["Total"])
            reliability = "⚠️ low n" if total < 3 else ""
            row_dict = {"Grouping": grp_name, "n (total)": f"{total} {reliability}"}
            for sc in ordered_state_cols:
                cnt = int(row.get(sc, 0))
                pct = round(100*cnt/total) if total else 0
                row_dict[sc] = f"{cnt} ({pct}%)" if cnt > 0 else "—"
            table_rows.append(row_dict)
        tbl_df = pd.DataFrame(table_rows).set_index("Grouping")
        st.dataframe(tbl_df, use_container_width=True)

        # Build summary for hypothesis
        grp_counts = sup_filt["Grouping"].value_counts()
        top_grp    = grp_counts.index[0] if not grp_counts.empty else "unknown"
        top_grp_n  = int(grp_counts.iloc[0]) if not grp_counts.empty else 0
        top_grp_pct = round(100*top_grp_n/len(sup_filt)) if len(sup_filt) else 0
        # Plain-language support summary for report
        support_summary_parts = [f"{g}: {n} interval{'s' if n!=1 else ''} ({round(100*n/len(sup_filt))}%)"
                                  for g, n in grp_counts.items()]
        ss["rpt_support_summary"] = " · ".join(support_summary_parts)
        ss["rpt_top_grp"] = top_grp
        ss["rpt_top_grp_pct"] = top_grp_pct
        # Use in-window only for regulation rate
        grp_win_rates = {}
        for g in sup_filt["Grouping"].unique():
            sub = sup_filt[sup_filt["Grouping"]==g]
            if len(sub) >= 3:
                grp_win_rates[g] = round(100*(sub["regulated"]=="in_window").sum()/len(sub))
        hyp_grp_prompt = (
            f"Student support type distribution across {len(sup_filt)} intervals: "
            + ", ".join(f"{g} ({n} intervals, {round(100*n/len(sup_filt))}%)" for g, n in grp_counts.items()) + ". "
            + f"Most common support arrangement is '{top_grp}' ({top_grp_pct}% of intervals). "
            + ("In-window regulation rates (only rows with ≥3 intervals): "
               + "; ".join(f"{g}: {pct}% in-window" for g, pct in grp_win_rates.items()) + ". "
               if grp_win_rates else "")
            + "Interpret what this reveals about the student's dependence on intensive support, "
              "and what the data implies for resourcing, fading support, or building independence."
        )
        with st.spinner("Generating hypothesis…"):
            hyp_grp = _groq_hypothesis(hyp_grp_prompt)
        if hyp_grp:
            _hypothesis_box(hyp_grp, key="rpt_hyp_grp")
        else:
            _hypothesis_box(
                f"The data shows that {top_grp_pct}% of observed intervals occurred under '{top_grp}' support. "
                "This indicates the current level of support is the primary context in which this student's "
                "regulation is being observed and maintained. The team should consider whether this level of "
                "resourcing is sustainable, what structured plans exist for support-fading, and how the "
                "student's regulation changes in lower-support contexts.",
                key="rpt_hyp_grp"
            )
    else:
        st.info("Record grouping/support data during observations to see this chart.")

    st.markdown("---")

    # ── Chart 5: Activity type vs regulation ─────────────────────────────────
    if "activity_types" in filt.columns:
        act_rows = []
        for _, row in filt.iterrows():
            acts = [a.strip() for a in str(row.get("activity_types","")).split(",") if a.strip()]
            for act in acts:
                act_rows.append({
                    "Activity": act,
                    "State":    row["State"],
                    "Grouping": GROUPING_TYPES.get(row.get("grouping_type",""),"") if row.get("grouping_type") else "",
                })
        if act_rows:
            st.markdown("##### 🎯 Regulation by activity type")
            st.caption(
                "Each bar represents all 15-minute intervals recorded during that activity type. "
                "When an interval has multiple activity types selected, it is counted in each. "
                "Colour shows regulation state during that activity."
            )
            act_df = pd.DataFrame(act_rows)
            adf    = act_df.groupby(["Activity","State"]).size().reset_index(name="n")
            active_states_act = [s for s in state_order if s in adf["State"].values]
            fig6 = px.bar(adf, x="n", y="Activity", color="State",
                color_discrete_map=colour_map, barmode="stack", orientation="h",
                labels={"Activity":"","n":"Intervals","State":""},
                category_orders={"State": active_states_act})
            fig6.update_layout(height=max(220,len(adf["Activity"].unique())*60+80),
                plot_bgcolor="white", paper_bgcolor="white",
                yaxis=dict(autorange="reversed"),
                xaxis=dict(tickformat="d", gridcolor="#e2e8f0", title="15-min intervals recorded"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
                margin=dict(l=10,r=10,t=50,b=10))
            st.plotly_chart(fig6, use_container_width=True)

            # Explicit report version — preserve autorange='reversed'
            import copy as _cp2
            _fig6r = _cp2.deepcopy(fig6)
            _n_act_rows = len(adf["Activity"].unique())
            _fig6r.update_layout(
                width=820, height=max(300, _n_act_rows * 85 + 120), autosize=False,
                font=dict(size=12, family="Arial, sans-serif"),
                margin=dict(l=145, r=30, t=75, b=60),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.04,
                            xanchor="left", x=0, font=dict(size=11)),
                xaxis=dict(gridcolor="#e2e8f0", tickfont=dict(size=11), title="15-min intervals recorded"),
                yaxis=dict(gridcolor="#e2e8f0", tickfont=dict(size=12),
                           autorange="reversed"),
            )
            ss["rpt_fig6"] = _fig6r.to_html(full_html=False, include_plotlyjs=False)

            # Build hypothesis
            act_counts  = act_df["Activity"].value_counts()
            top_act     = act_counts.index[0] if not act_counts.empty else "unknown"
            act_reg_pct = {}
            for act in act_df["Activity"].unique():
                sub = act_df[act_df["Activity"]==act]
                reg_n = sub["State"].str.contains("In window|Coping").sum()
                act_reg_pct[act] = round(100*reg_n/len(sub)) if len(sub) else 0

            # Support info for top activity
            top_act_grp = act_df[act_df["Activity"]==top_act]["Grouping"].value_counts()
            top_grp_for_act = top_act_grp.index[0] if not top_act_grp.empty else "unrecorded grouping"

            hyp_act_prompt = (
                f"Student activity type data across all intervals: "
                + ", ".join(f"{a} ({n} intervals, {act_reg_pct.get(a,0)}% regulated)" for a, n in act_counts.items()) + ". "
                + f"Most common activity is '{top_act}' — primarily with '{top_grp_for_act}' support. "
                + "Interpret what this reveals about demand tolerance, preferred vs non-preferred tasks, "
                  "and what this implies for curriculum design and support planning. "
                  "Note whether regulation is contingent on activity preference, and question whether "
                  "the student is building capacity for non-preferred tasks."
            )
            with st.spinner("Generating hypothesis…"):
                hyp_act = _groq_hypothesis(hyp_act_prompt)
            if hyp_act:
                _hypothesis_box(hyp_act, key="rpt_hyp_act")
            else:
                best_act  = max(act_reg_pct, key=act_reg_pct.get) if act_reg_pct else None
                worst_act = min(act_reg_pct, key=act_reg_pct.get) if act_reg_pct else None
                _hypothesis_box(
                    f"The majority of observed intervals involved '{top_act}' tasks, predominantly under '{top_grp_for_act}' support. "
                    + (f"Highest in-window regulation was observed during '{best_act}' activities ({act_reg_pct[best_act]}% in-window). " if best_act else "")
                    + (f"Greatest dysregulation occurred during '{worst_act}' activities ({act_reg_pct[worst_act]}% in-window). " if worst_act and worst_act != best_act else "")
                    + "The team should consider whether regulation during preferred or structured tasks "
                      "is contingent on high levels of 1:1 support, and build a plan to gradually "
                      "introduce demand and fade support across this student's program.",
                    key="rpt_hyp_act"
                )
            st.markdown("---")

    dl = filt.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    csv = dl[["obs_date","day_of_week","time_slot","regulated","State",
              "grouping_type","activity_types","outcome","created_by"]].to_csv(index=False)

    st.markdown("---")

    # ── Build data summary for questions generator ────────────────────────────
    # Identify time slots where student is consistently in-window
    slot_win = filt[filt["regulated"]=="in_window"].groupby("time_slot").size()
    slot_tot = filt.groupby("time_slot").size()
    slot_pct_win = (slot_win / slot_tot * 100).fillna(0).round(0)
    strong_slots = slot_pct_win[slot_pct_win >= 70].sort_values(ascending=False)
    weak_slots   = slot_pct_win[slot_pct_win <= 20].sort_values()

    questions_data_summary = (
        f"Student: {student_name}. Observation period: {date_span}. "
        f"Time range: {min_slot}–{max_slot}. Days observed: {n_days_with_data}. "
        f"Total intervals: {n_tot}. In-window: {n_win} ({pct_inwin}%). Coping (dysregulated): {n_cop} ({pct_cop_only}%). "
        f"Hyperaroused: {n_hyp}. Hypoaroused: {n_hypo}. "
        + (f"Time slots with ≥70% in-window (consistently regulated): {', '.join(strong_slots.index.tolist())}. " if not strong_slots.empty else "")
        + (f"Time slots with ≤20% in-window (consistently dysregulated): {', '.join(weak_slots.index.tolist())}. " if not weak_slots.empty else "")
        + (f"Best day: {best_day} ({best_pct}% in-window). Worst day: {worst_day} ({worst_pct}% in-window). " if best_day else "")
        + (f"Support distribution: {ss.get('rpt_support_summary','')}. " if ss.get("rpt_support_summary") else "")
        + "Generate 5 specific investigative questions grounded in these patterns."
    )

    # ── Report generator ─────────────────────────────────────────────────────
    with st.expander("📄 Generate analysis report", expanded=False):
        st.caption(
            "Scroll through the Analysis tab first so every chart and hypothesis is generated, "
            "then complete the fields below and click Generate."
        )
        report_title  = st.text_input("Report title",  value=f"Interval Support Analysis — {student_name}", key="rpt_title")
        report_author = st.text_input("Prepared by",   value=get_staff_name() or "", key="rpt_author")
        additional_details = st.text_area(
            "Additional context / staff observations",
            placeholder=(
                "Add any context to be included in the report — e.g. what specific tasks were "
                "running at the times of best regulation, staffing notes, environmental factors, "
                "recent changes to the student's program or home situation, etc."
            ),
            height=120,
            key="rpt_additional"
        )

        if st.button("📄 Generate report", key="rpt_gen_btn", type="primary", use_container_width=True):

            # ── Generate investigative questions ────────────────────────────
            with st.spinner("Generating investigative questions…"):
                questions_text = _generate_questions(questions_data_summary)
            if not questions_text:
                # Rule-based fallback
                q_lines = []
                if not strong_slots.empty:
                    q_lines.append(f"1. What specific tasks or routines are running at {strong_slots.index[0]} each day, given that this is when the student is most consistently within their window?")
                if not weak_slots.empty:
                    q_lines.append(f"2. What is happening at {weak_slots.index[0]} that consistently results in dysregulation — is this a transition point, change of staff, or particular demand?")
                if best_day and worst_day and best_day != worst_day:
                    q_lines.append(f"3. What structural differences exist between {best_day} and {worst_day} in terms of timetable, staffing, and peer grouping that could explain the difference in regulation?")
                q_lines.append(f"4. Given that {ss.get('rpt_top_grp_pct',0)}% of observed intervals involve {ss.get('rpt_top_grp','1:1')} support, what is the plan for building the student's capacity to function in lower-support contexts?")
                q_lines.append("5. Which specific activities or times of regulation could be used as a foundation for gradually introducing demand and building the student's window of tolerance?")
                questions_text = "\n".join(q_lines[:5])

            ss["rpt_questions"] = questions_text

            # Show questions in UI before download
            st.markdown("**Questions generated for this student:**")
            st.info(questions_text)

            # ── Retrieve stored data ────────────────────────────────────────
            hyp_time  = ss.get("rpt_hyp_time", "")
            hyp_dow_  = ss.get("rpt_hyp_dow",  "")
            hyp_grp_  = ss.get("rpt_hyp_grp",  "")
            hyp_act_  = ss.get("rpt_hyp_act",  "")
            fig1_html     = ss.get("rpt_fig1",    "")
            fig2_html     = ss.get("rpt_fig2",    "")
            fig4_html     = ss.get("rpt_fig4",    "")
            fig4_pct_html = ss.get("rpt_fig4_pct","")
            fig_grp_html  = ss.get("rpt_fig_grp", "")
            fig6_html     = ss.get("rpt_fig6",    "")
            support_summary = ss.get("rpt_support_summary", "")
            top_grp      = ss.get("rpt_top_grp", "")
            top_grp_pct  = ss.get("rpt_top_grp_pct", 0)

            missing = [n for n, h in [("Regulation across the day", fig1_html), ("Day of week", fig4_html)] if not h]
            if missing:
                st.warning("⚠️ Some charts missing — scroll through the Analysis tab first: " + ", ".join(missing))

            # ── Inner HTML helpers ──────────────────────────────────────────
            def _hyp_block(text):
                if not text: return ""
                return (
                    '<div class="hyp"><div class="hyp-label">🔍 Hypothesis</div>'
                    f'<p>{text}</p></div>'
                )

            def _chart_block(title, info_text, chart_html, hyp_text=""):
                ch = chart_html or '<p class="no-data">Chart not yet generated — scroll through the Analysis tab and regenerate.</p>'
                return (
                    f'<h2>{title}</h2>'
                    f'<div class="info-box">{info_text}</div>'
                    f'<div class="chart-wrap">{ch}</div>'
                    + _hyp_block(hyp_text)
                )

            # ── Day of week table ───────────────────────────────────────────
            dow_html_table = ""
            if not dow_reg.empty:
                dow_html_table = (
                    '<table><thead><tr>'
                    '<th>Day</th><th>n (intervals)</th>'
                    '<th style="color:#16a34a;">🟢 In window</th>'
                    '<th style="color:#ca8a04;">🟡 Coping ⚠️</th>'
                    '<th style="color:#dc2626;">🔴 Hyperaroused</th>'
                    '<th style="color:#2563eb;">🔵 Hypoaroused</th>'
                    '</tr></thead><tbody>'
                )
                for _, r in dow_reg.iterrows():
                    d   = r["day_of_week"]
                    sub = filt[filt["day_of_week"] == d]
                    tot = len(sub)
                    p_h  = round(100*(sub["regulated"]=="hyperaroused").sum()/tot) if tot else 0
                    p_ho = round(100*(sub["regulated"]=="hypoaroused").sum()/tot)  if tot else 0
                    dow_html_table += (
                        f'<tr><td><strong>{d}</strong></td><td>{tot}</td>'
                        f'<td style="color:#16a34a;font-weight:700;">{r["pct_win"]}%</td>'
                        f'<td style="color:#ca8a04;">{r["pct_cop"]}%</td>'
                        f'<td style="color:#dc2626;">{p_h}%</td>'
                        f'<td style="color:#2563eb;">{p_ho}%</td></tr>'
                    )
                dow_html_table += '</tbody></table>'
                dow_html_table += '<p style="font-size:.75rem;color:#64748b;margin-top:.2rem;">⚠️ Coping = at the edge of the window — the student is struggling to manage, not regulated.</p>'

            # ── Support summary HTML ────────────────────────────────────────
            support_summary_html = ""
            if support_summary:
                support_summary_html = (
                    f'<div class="support-summary">'
                    f'<strong>Support profile across all {n_tot} observed intervals:</strong><br>'
                    f'{support_summary}<br>'
                    + (f'<br><strong>⚠️ {top_grp_pct}% of all observed intervals involved {top_grp} support.</strong> '
                       'This data represents what was observed — it does not mean the student '
                       'was unsupported during other intervals; it means those intervals were '
                       'not recorded under a different grouping arrangement.' if top_grp_pct >= 70 else '')
                    + '</div>'
                )

            # ── Support breakdown table ─────────────────────────────────────
            grp_html_table = ""
            if not sup_filt.empty and "Grouping" in sup_filt.columns:
                pivot_c = sup_filt.groupby(["Grouping","State"]).size().unstack(fill_value=0)
                pivot_c["Total"] = pivot_c.sum(axis=1)
                osc = [s for s in state_order if s in pivot_c.columns]
                grp_html_table = '<table><thead><tr><th>Grouping</th><th>Total (n)</th>'
                for sc in osc: grp_html_table += f'<th>{sc}</th>'
                grp_html_table += '</tr></thead><tbody>'
                for g, row in pivot_c.iterrows():
                    total = int(row["Total"])
                    warn  = " ⚠️" if total < 3 else ""
                    grp_html_table += f'<tr><td><strong>{g}</strong>{warn}</td><td>{total}</td>'
                    for sc in osc:
                        cnt = int(row.get(sc, 0))
                        pct = round(100*cnt/total) if total else 0
                        grp_html_table += f'<td>{"—" if cnt==0 else f"{cnt} ({pct}%)"}</td>'
                    grp_html_table += '</tr>'
                grp_html_table += '</tbody></table>'
                grp_html_table += '<p style="font-size:.75rem;color:#64748b;">⚠️ Rows with n &lt; 3 reflect a single moment, not a pattern.</p>'

            # ── Questions HTML ──────────────────────────────────────────────
            qs_html = ""
            if questions_text:
                lines = [l.strip() for l in questions_text.strip().split("\n") if l.strip()]
                qs_html = '<ol class="questions">' + "".join(f"<li>{l.lstrip('0123456789. ')}</li>" for l in lines) + "</ol>"

            # ── Additional details HTML ─────────────────────────────────────
            additional_html = ""
            if additional_details and additional_details.strip():
                safe_ad = additional_details.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
                additional_html = f'<div class="additional"><div class="add-label">📝 Additional staff observations</div><p>{safe_ad}</p></div>'

            # ── Assemble full report ────────────────────────────────────────
            html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{report_title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  body {{font-family:Arial,sans-serif;font-size:13px;color:#1e293b;margin:0;padding:0;background:white;}}
  .page {{max-width:900px;margin:0 auto;padding:30px 36px;}}
  h1 {{font-size:1.45rem;color:#1A6B8A;border-bottom:3px solid #1A6B8A;padding-bottom:.5rem;margin-bottom:.3rem;}}
  h2 {{font-size:1.05rem;color:#1A6B8A;margin:2rem 0 .4rem;border-bottom:1px solid #e2e8f0;padding-bottom:.25rem;}}
  .meta {{font-size:.78rem;color:#64748b;margin-bottom:1rem;}}
  .obs-box {{background:#f0f9ff;border:1.5px solid #7dd3fc;border-radius:8px;padding:.65rem 1.1rem;font-size:.83rem;margin-bottom:.8rem;}}
  .warn {{background:#fef9c3;border-left:4px solid #ca8a04;border-radius:0 6px 6px 0;padding:.55rem 1rem;font-size:.82rem;margin-bottom:1rem;line-height:1.6;}}
  .kpi-row {{display:flex;gap:.8rem;margin-bottom:1rem;flex-wrap:wrap;}}
  .kpi {{background:white;border-left:4px solid #1A6B8A;border-radius:6px;padding:.5rem .9rem;min-width:110px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.08);}}
  .kpi .val {{font-size:1.6rem;font-weight:700;color:#1A6B8A;}}
  .kpi .lbl {{font-size:.65rem;color:#64748b;line-height:1.4;}}
  .kpi.g {{border-color:#16a34a;}} .kpi.g .val {{color:#16a34a;}}
  .kpi.y {{border-color:#ca8a04;}} .kpi.y .val {{color:#ca8a04;}}
  .kpi.r {{border-color:#dc2626;}} .kpi.r .val {{color:#dc2626;}}
  .kpi.b {{border-color:#2563eb;}} .kpi.b .val {{color:#2563eb;}}
  .info-box {{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:.5rem .9rem;font-size:.8rem;color:#475569;margin-bottom:.5rem;line-height:1.5;}}
  .chart-wrap {{margin:.2rem 0 .6rem;border:1px solid #e2e8f0;border-radius:8px;overflow:visible;padding:.3rem;width:820px;max-width:100%;}}
  .hyp {{background:#EBF4F9;border-left:4px solid #1A6B8A;border-radius:0 8px 8px 0;padding:.65rem 1.1rem;margin:.6rem 0 1.2rem;font-size:.83rem;line-height:1.6;}}
  .hyp-label {{font-size:.65rem;font-weight:700;color:#1A6B8A;letter-spacing:.06em;margin-bottom:.3rem;}}
  .support-summary {{background:#f0f9ff;border:1.5px solid #7dd3fc;border-radius:8px;padding:.65rem 1.1rem;font-size:.83rem;margin:.4rem 0 .7rem;line-height:1.6;}}
  .questions {{background:#f0fdf4;border:1.5px solid #86efac;border-radius:8px;padding:.8rem 1.1rem .8rem 2rem;margin:1rem 0;font-size:.84rem;line-height:1.8;color:#14532d;}}
  .questions li {{margin-bottom:.3rem;}}
  .additional {{background:#fefce8;border-left:4px solid #ca8a04;border-radius:0 8px 8px 0;padding:.65rem 1.1rem;margin:1rem 0;font-size:.83rem;line-height:1.6;}}
  .add-label {{font-size:.65rem;font-weight:700;color:#92400e;letter-spacing:.06em;margin-bottom:.3rem;}}
  .no-data {{color:#94a3b8;font-size:.8rem;font-style:italic;margin:.5rem 0 1rem;}}
  table {{border-collapse:collapse;width:100%;margin:.5rem 0 .8rem;font-size:.8rem;}}
  thead th {{background:#1A6B8A;color:white;padding:.4rem .65rem;text-align:left;font-weight:600;}}
  td {{border:1px solid #e2e8f0;padding:.32rem .65rem;}}
  tr:nth-child(even) td {{background:#f8fafc;}}
  .footer {{font-size:.68rem;color:#94a3b8;border-top:1px solid #e2e8f0;margin-top:2.5rem;padding-top:.6rem;}}
  @media print {{
    body {{font-size:11px;}}
    .page {{padding:18px 22px;}}
    .chart-wrap {{page-break-inside:avoid;}}
    h2 {{page-break-after:avoid;}}
  }}
</style>
</head>
<body>
<div class="page">

  <h1>{report_title}</h1>
  <div class="meta">
    {'Prepared by: <strong>' + report_author + '</strong> &nbsp;·&nbsp; ' if report_author else ''}
    Generated: <strong>{date.today().strftime('%-d %B %Y')}</strong>
  </div>

  <div class="obs-box">
    <strong>📅 Observation window:</strong> {date_span} &nbsp;·&nbsp;
    <strong>{n_days_with_data} school day{"s" if n_days_with_data!=1 else ""}</strong> with data &nbsp;·&nbsp;
    <strong>Time range: {min_slot}–{max_slot}</strong>
  </div>

  <div class="warn">
    <strong>⚠️ How to read this report — regulation states:</strong><br>
    🟢 <strong>In window</strong> — genuinely regulated; calm, present, learning-ready.<br>
    🟡 <strong>Coping</strong> — <strong>at the edge of the window and dysregulated</strong>.
    The student is actively working to manage their arousal state. This is not a stable or successful position.
    A session that is predominantly yellow is still a difficult session.<br>
    🔴 <strong>Hyperaroused</strong> — above the window; fight/flight/fright response.<br>
    🔵 <strong>Hypoaroused</strong> — below the window; shutdown/freeze/dissociation.<br><br>
    Each <em>interval</em> = one 15-minute observation window. Data was collected between
    <strong>{min_slot} and {max_slot}</strong> only.
  </div>

  <h2>Overall regulation summary</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="val">{n_tot}</div><div class="lbl">Total intervals<br>(15-min windows)</div></div>
    <div class="kpi g"><div class="val">{n_win}</div><div class="lbl">🟢 In window<br>{pct_inwin}%</div></div>
    <div class="kpi y"><div class="val">{n_cop}</div><div class="lbl">🟡 Coping (dysregulated)<br>{pct_cop_only}%</div></div>
    <div class="kpi r"><div class="val">{n_hyp}</div><div class="lbl">🔴 Hyperaroused</div></div>
    <div class="kpi b"><div class="val">{n_hypo}</div><div class="lbl">🔵 Hypoaroused</div></div>
  </div>

  {_chart_block(
    "📊 Regulation state across the day",
    f"Each bar = one 15-minute time slot between {min_slot} and {max_slot}, across all {n_days_with_data} observed days. "
    "Bar height = number of intervals recorded at that time. Colour = regulation state. "
    "<strong>🟡 Yellow (Coping) = dysregulated</strong> — the student is at the edge of their window and struggling to manage. "
    "Tall green bars = the student was consistently within their window at that time.",
    fig1_html, hyp_time
  )}

  <h2>📈 Daily regulation trend</h2>
  <div class="info-box">
    Percentage of each day's recorded intervals in each regulation state, across the {n_days_with_data} observed school days.
    Each row is one school day. The bar in each cell shows the proportion visually.
    <strong>Days with the longest green bar are the strongest days for regulation.</strong>
    🟡 Coping = dysregulated — at the edge of the window, not stable.
  </div>
  {fig2_html or '<p class="no-data">Daily trend not yet generated — scroll through the Analysis tab and regenerate.</p>'}

  <h2>📅 Regulation by day of week</h2>
  <div class="info-box">
    The bar chart below shows each day's intervals as a <strong>100% normalised bar</strong> —
    bar colour split reflects the <em>proportion</em> of intervals in each state, regardless of how many
    intervals were recorded on that day. This matches the percentage table.
    <strong>Best days are those with the most green (In window), not yellow.</strong>
    🟡 Coping = dysregulated.
  </div>
  <div class="chart-wrap">{fig4_pct_html or fig4_html or '<p class="no-data">Chart not yet generated.</p>'}</div>
  {dow_html_table}
  {_hyp_block(hyp_dow_)}

  <h2>👥 Level of support</h2>
  {support_summary_html}
  <div class="info-box">
    The bar chart shows the total number of intervals recorded under each support/grouping arrangement,
    coloured by regulation state during that interval.
    The table below shows exact counts and percentages per regulation state.
    <strong>⚠️ Rows with n &lt; 3 should not be used to draw conclusions.</strong>
  </div>
  {fig_grp_html or '<p class="no-data">Support chart not yet generated — scroll through the Analysis tab and regenerate.</p>'}
  {grp_html_table}
  {_hyp_block(hyp_grp_)}

  {_chart_block(
    "🎯 Regulation by activity type",
    "Each bar = all intervals recorded during that activity type, coloured by regulation state. "
    "When an interval has multiple activities selected, it is counted in each. "
    "🟡 Coping = dysregulated.",
    fig6_html or "", hyp_act_
  ) if fig6_html else (
    '<h2>🎯 Regulation by activity type</h2>'
    '<div class="no-data">No activity data recorded, or chart not yet generated.</div>'
    + _hyp_block(hyp_act_)
  )}

  <h2>🔎 Questions for the team to investigate</h2>
  <div class="info-box">
    The following questions were generated from the patterns in this student's data.
    They are intended to guide discussion at the next team meeting or TAC.
  </div>
  {qs_html or '<p class="no-data">Questions not generated — regenerate the report after scrolling through all charts.</p>'}

  {additional_html}

  <div class="footer">
    Interval Support Tracker &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit &nbsp;·&nbsp;
    Generated {date.today().strftime('%-d %B %Y')}
    {(' &nbsp;·&nbsp; Prepared by: ' + report_author) if report_author else ''}
  </div>
</div>
</body>
</html>"""

            st.download_button(
                "⬇️ Download report (HTML — opens in any browser)",
                html_report,
                file_name=f"IST_Report_{student_name.replace(' ','_')}_{date.today()}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.success("✅ Report ready. Open in Chrome, Edge or Firefox to view interactive charts and print.")

    st.download_button("📥 Download raw data (CSV)", csv,
        file_name=f"IntervalSupport_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv", use_container_width=True)
