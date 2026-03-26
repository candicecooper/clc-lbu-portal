# ════════════════════════════════════════════════════════════════════════════
# 18_Scatter_Plot_Tracker.py  ·  CLC-LBU Portal
# Scatter Plot Tracker — tracking periods, student panel, no-behaviour option
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
.sg { width:100%; border-collapse:collapse; font-size:.8rem; }
.sg th {
    background:#1A6B8A; color:white; padding:.38rem .45rem;
    text-align:center; font-size:.7rem; font-weight:600; white-space:nowrap;
}
.sg th.lh { text-align:left; min-width:50px; }
.sg th.la { text-align:left; min-width:110px; }
.sg td { padding:.25rem .35rem; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; }
.sg td.tl { text-align:left; font-weight:600; color:#334155; font-size:.73rem;
             white-space:nowrap; background:#f8fafc; }
.sg td.al { text-align:left; color:#64748b; font-size:.7rem; background:#f8fafc; }
.c1  { background:#dbeafe; color:#1d4ed8; font-weight:700; }
.c2  { background:#fee2e2; color:#b91c1c; font-weight:700; }
.cx  { background:#f3f4f6; color:#9ca3af; font-weight:600; }
.c0  { background:#f0fdf4; color:#15803d; font-weight:600; font-size:.72rem; }
.ce  { background:white; color:#e2e8f0; font-size:.65rem; }
.kpi { background:white; border-left:4px solid #1A6B8A; border-radius:6px;
        padding:.45rem .75rem; text-align:center; margin-bottom:.4rem; }
.kpi .val { font-size:1.4rem; font-weight:700; color:#1A6B8A; }
.kpi .lbl { font-size:.67rem; color:#666; }
.kpi-a { border-color:#D4860A; }
.kpi-a .val { color:#D4860A; }
.kpi-g { border-color:#2E7D32; }
.kpi-g .val { color:#2E7D32; }
.period-badge {
    display:inline-block; background:#EBF4F9; border:1px solid #1A6B8A44;
    border-radius:20px; padding:.2rem .75rem; font-size:.78rem;
    font-weight:600; color:#1A6B8A; margin-bottom:.5rem;
}
.period-active {
    background:#f0fdf4; border:2px solid #22c55e; border-radius:10px;
    padding:.6rem 1rem; margin-bottom:.75rem;
}
.ins { background:#FEF9EC; border-left:4px solid #D4860A; border-radius:6px;
        padding:.45rem .85rem; font-size:.82rem; margin-bottom:.3rem; }
.ins-ok { background:#F0FAF4; border-left:4px solid #2EA056; }
.stu-card {
    background:white; border:1px solid #e2e8f0; border-radius:8px;
    padding:.55rem .9rem; margin-bottom:.35rem;
    display:flex; align-items:center; justify-content:space-between;
}
</style>
""", unsafe_allow_html=True)

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


@st.cache_data(ttl=30)
def load_tracked_students():
    """All students who have any scatter plot observations — for the panel."""
    sb = get_sb()
    if not sb: return []
    try:
        res = (sb.table("scatter_plot_observations")
               .select("student_id,student_name,behaviour_label,value,obs_date,created_at")
               .order("created_at", desc=True)
               .execute())
        if not res.data: return []
        df = pd.DataFrame(res.data)
        df["obs_date"] = pd.to_datetime(df["obs_date"])
        summary = []
        for sid, grp in df.groupby("student_id"):
            name     = grp["student_name"].iloc[0]
            total    = len(grp)
            last_dt  = grp["obs_date"].max()
            behs     = grp["behaviour_label"].dropna().unique().tolist()
            behs     = [b for b in behs if b][:2]
            summary.append({
                "student_id":   sid,
                "student_name": name,
                "total":        total,
                "last_date":    last_dt.strftime("%-d %b %Y") if pd.notna(last_dt) else "—",
                "behaviours":   behs,
            })
        return sorted(summary, key=lambda x: x["student_name"])
    except Exception:
        return []


def load_periods(student_id: str) -> list:
    sb = get_sb()
    if not sb: return []
    try:
        res = (sb.table("scatter_tracking_periods")
               .select("*")
               .eq("student_id", student_id)
               .order("start_date", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


def create_period(student_id, student_name, beh1, beh2, label="") -> dict | None:
    sb = get_sb()
    if not sb: return None
    try:
        # Close any open period first
        sb.table("scatter_tracking_periods").update(
            {"end_date": date.today().isoformat()}
        ).eq("student_id", student_id).is_("end_date", "null").execute()

        res = sb.table("scatter_tracking_periods").insert({
            "student_id":   student_id,
            "student_name": student_name,
            "start_date":   date.today().isoformat(),
            "end_date":     None,
            "behaviour_1":  beh1.strip(),
            "behaviour_2":  beh2.strip(),
            "label":        label.strip(),
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"Could not create period: {e}")
        return None


def load_week_obs(student_id, week_start, week_end, period_id=None):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        q = (sb.table("scatter_plot_observations")
             .select("*")
             .eq("student_id", student_id)
             .gte("obs_date", str(week_start))
             .lte("obs_date", str(week_end)))
        if period_id:
            q = q.eq("tracking_period_id", period_id)
        res = q.execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception as e:
        st.error(f"Load error: {e}")
        return pd.DataFrame()


def load_all_obs(student_id, period_id=None):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        q = (sb.table("scatter_plot_observations")
             .select("*")
             .eq("student_id", student_id)
             .order("obs_date").order("time_slot"))
        if period_id:
            q = q.eq("tracking_period_id", period_id)
        res = q.execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception:
        return pd.DataFrame()


def upsert_obs(student_id, student_name, sel_date, sel_day, sel_time, activity,
               value, beh_index, beh_label, behaviours_str,
               period_id=None, existing_id=None) -> bool:
    sb = get_sb()
    if not sb:
        st.session_state["_spt_last_error"] = "Supabase not configured — check secrets."
        return False
    row = {
        "student_id":          student_id,
        "student_name":        student_name,
        "obs_date":            sel_date.isoformat(),
        "day_of_week":         sel_day,
        "time_slot":           sel_time,
        "activity":            activity,
        "value":               value,
        "behaviour_index":     beh_index,
        "behaviour_label":     beh_label,
        "target_behaviours":   behaviours_str,
        "tracking_period_id":  period_id,
        "created_by":          get_staff_name(),
    }
    row_minimal = {k: v for k, v in row.items()
                   if k not in ("behaviour_index","behaviour_label","tracking_period_id")}
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
        err = str(e)
        if any(k in err for k in ["behaviour_index","behaviour_label","tracking_period_id","column"]):
            try:
                if existing_id:
                    sb.table("scatter_plot_observations").update({"value": value}).eq("id", existing_id).execute()
                else:
                    sb.table("scatter_plot_observations").insert(row_minimal).execute()
                st.session_state["_spt_last_error"] = (
                    "⚠️ Saved without period tracking — run scatter_periods_schema.sql in Supabase.")
                return True
            except Exception as e2:
                st.session_state["_spt_last_error"] = f"Save failed: {e2}"
                return False
        st.session_state["_spt_last_error"] = f"Save failed: {err}"
        return False


def delete_obs(obs_id):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_plot_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False


def load_schedule(student_id):
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


def save_schedule(student_id, schedule):
    sb = get_sb()
    if not sb: return
    try:
        data = {"student_id": student_id, "schedule": json.dumps(schedule)}
        ex = sb.table("scatter_plot_schedules").select("id").eq("student_id", student_id).execute()
        if ex.data:
            sb.table("scatter_plot_schedules").update(data).eq("student_id", student_id).execute()
        else:
            sb.table("scatter_plot_schedules").insert(data).execute()
    except Exception:
        pass


# ── Session state ─────────────────────────────────────────────────────────────
ss = st.session_state
for k, v in [
    ("spt_student_id", None), ("spt_student_name", ""),
    ("spt_beh1", ""),        ("spt_beh2", ""),
    ("spt_schedule", None),  ("spt_period_id", None),
    ("spt_week_start", date.today() - timedelta(days=date.today().weekday())),
]:
    if k not in ss: ss[k] = v


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
# TRACKED STUDENTS PANEL
# ════════════════════════════════════════════════════════════════════════════
tracked = load_tracked_students()
if tracked:
    with st.expander(f"📋 Students currently being tracked ({len(tracked)})", expanded=False):
        for stu in tracked:
            sc1, sc2, sc3, sc4 = st.columns([3, 3, 1.5, 1])
            with sc1:
                st.markdown(f"**{stu['student_name']}**")
            with sc2:
                behs = stu["behaviours"]
                if behs:
                    st.caption(" · ".join([f"B{i+1}: {b[:30]}" for i,b in enumerate(behs)]))
                else:
                    st.caption("—")
            with sc3:
                st.caption(f"Last: {stu['last_date']}")
            with sc4:
                if st.button("Select", key=f"panel_sel_{stu['student_id']}", use_container_width=True):
                    ss.spt_student_id   = stu["student_id"]
                    ss.spt_student_name = stu["student_name"]
                    ss.spt_schedule     = None
                    ss.spt_period_id    = None
                    ss.spt_beh1         = behs[0] if len(behs) > 0 else ""
                    ss.spt_beh2         = behs[1] if len(behs) > 1 else ""
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# STUDENT SELECTOR
# ════════════════════════════════════════════════════════════════════════════
students     = load_students_cached()
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
    ss.spt_beh1 = st.text_input("Behaviour 1 *", value=ss.spt_beh1,
                                  placeholder="e.g. Roaming instead of participating",
                                  key="spt_b1")
with hc3:
    ss.spt_beh2 = st.text_input("Behaviour 2 (optional)", value=ss.spt_beh2,
                                  placeholder="e.g. Verbal outbursts", key="spt_b2")

# Add new student
with st.expander("➕ Add a new student"):
    with st.form("spt_add_student_form"):
        ns1, ns2, ns3 = st.columns([2, 2, 1])
        with ns1:
            ns_first = st.text_input("First name *", placeholder="e.g. Alex")
            ns_edid  = st.text_input("EDID *", placeholder="e.g. ED123456")
        with ns2:
            ns_last    = st.text_input("Last name *", placeholder="e.g. Smith")
            ns_program = st.selectbox("Program *", ["JP","PY","SY"])
        with ns3:
            ns_grade = st.selectbox("Grade", ["R","Y1","Y2","Y3","Y4","Y5","Y6","Y7","Y8","Y9","Y10","Y11","Y12"])
            ns_dob   = st.date_input("Date of birth", value=None)
        if st.form_submit_button("Save Student", type="primary", use_container_width=True):
            if not ns_first.strip() or not ns_last.strip() or not ns_edid.strip():
                st.error("Please fill in first name, last name and EDID.")
            else:
                sb = get_sb()
                if sb:
                    try:
                        full_name = f"{ns_first.strip()} {ns_last.strip()}"
                        sb.table("students").insert({
                            "first_name": ns_first.strip(), "last_name": ns_last.strip(),
                            "name": full_name, "edid": ns_edid.strip(),
                            "program": ns_program, "grade": ns_grade,
                            "dob": ns_dob.isoformat() if ns_dob else None,
                            "placement_start": date.today().isoformat(), "archived": False,
                        }).execute()
                        load_students_cached.clear()
                        st.success(f"✅ {full_name} added — select them from the dropdown.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not save student: {e}")

# Student change — show explicit choice screen
if selected_id != ss.spt_student_id:
    ss.spt_student_id      = selected_id
    ss.spt_student_name    = next((s["name"] for s in students if s["id"]==selected_id),"")
    ss.spt_schedule        = None
    ss.spt_period_id       = None
    ss.spt_beh1            = ""
    ss.spt_beh2            = ""
    ss.spt_show_choice     = True
    ss.spt_show_new_period = False
    st.rerun()

# ── CHOICE SCREEN ─────────────────────────────────────────────────────────
if ss.get("spt_show_choice"):
    stu_name_c = ss.spt_student_name or student_opts.get(selected_id,"")

    sb = get_sb()
    existing_periods = []
    if sb:
        try:
            pr = (sb.table("scatter_tracking_periods")
                  .select("*").eq("student_id", selected_id)
                  .order("start_date", desc=True).execute())
            existing_periods = pr.data or []
        except Exception:
            pass

    period_count = len(existing_periods)
    st.markdown(
        f'<div style="background:white;border:2px solid #1A6B8A;border-radius:12px;'
        f'padding:1.25rem 1.5rem;margin-bottom:1rem;">'
        f'<div style="font-size:1.05rem;font-weight:700;color:#1A6B8A;margin-bottom:.25rem;">'
        f'📋 {stu_name_c}</div>'
        f'<div style="font-size:.85rem;color:#64748b;">'
        + (f"This student has {period_count} tracking period(s) on record." if existing_periods
           else "No tracking data on record yet.")
        + '</div></div>',
        unsafe_allow_html=True
    )

    if existing_periods:
        st.markdown("**Existing tracking periods:**")
        for i, p in enumerate(existing_periods):
            active_tag = " ✅ Active" if not p.get("end_date") else ""
            start_str  = pd.to_datetime(p["start_date"]).strftime("%-d %b %Y")
            end_str    = pd.to_datetime(p["end_date"]).strftime("%-d %b %Y") if p.get("end_date") else "ongoing"
            b1  = p.get("behaviour_1","")
            b2  = p.get("behaviour_2","")
            lbl = p.get("label") or ("Period " + str(len(existing_periods)-i))
            beh_text = b1 + (" · " + b2 if b2 else "")
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
                f'padding:.5rem .9rem;margin-bottom:.3rem;font-size:.83rem;">'
                f'<b>{lbl}</b>{active_tag} &nbsp;'
                f'<span style="color:#64748b;">{start_str} – {end_str}</span><br>'
                f'<span style="color:#334155;">{beh_text}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("**What would you like to do?**")

        active_p = next((p for p in existing_periods if not p.get("end_date")), existing_periods[0])
        b1_a = active_p.get("behaviour_1","")
        b2_a = active_p.get("behaviour_2","")
        preview = b1_a + (" · " + b2_a if b2_a else "")

        ch1, ch2 = st.columns(2)
        with ch1:
            cont_label = "▶  Continue current tracking  —  " + preview[:55]
            if st.button(cont_label, type="primary", use_container_width=True, key="choice_continue"):
                ss.spt_period_id   = active_p["id"]
                ss.spt_beh1        = b1_a
                ss.spt_beh2        = b2_a
                ss.spt_show_choice = False
                st.rerun()
        with ch2:
            if st.button("🔄  Start new tracking period — behaviours have changed",
                         use_container_width=True, key="choice_new"):
                ss.spt_show_choice     = False
                ss.spt_show_new_period = True
                st.rerun()

        if len(existing_periods) > 1:
            st.markdown("**Or view a specific historical period:**")
            period_opts_c = {}
            for i, p in enumerate(existing_periods):
                b1t = p.get("behaviour_1","")
                b2t = p.get("behaviour_2","")
                lbl_t = p.get("label") or ("Period " + str(len(existing_periods)-i))
                sd_t  = pd.to_datetime(p["start_date"]).strftime("%-d %b %y")
                ed_t  = pd.to_datetime(p["end_date"]).strftime("%-d %b %y") if p.get("end_date") else "now"
                period_opts_c[p["id"]] = lbl_t + " — " + b1t + (" · "+b2t if b2t else "") + " (" + sd_t + "–" + ed_t + ")"

            vc1, vc2 = st.columns([4,1])
            with vc1:
                view_pid = st.selectbox("Select period to view", list(period_opts_c.keys()),
                                        format_func=lambda x: period_opts_c[x],
                                        key="choice_view_sel")
            with vc2:
                st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
                if st.button("View", use_container_width=True, key="choice_view_btn"):
                    vp = next((p for p in existing_periods if p["id"]==view_pid), None)
                    if vp:
                        ss.spt_period_id = vp["id"]
                        ss.spt_beh1      = vp.get("behaviour_1","")
                        ss.spt_beh2      = vp.get("behaviour_2","")
                    ss.spt_show_choice = False
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown("**Enter the behaviour(s) you want to track:**")
        with st.form("choice_new_student_form"):
            cf1, cf2 = st.columns(2)
            with cf1: nb1 = st.text_input("Behaviour 1 *", placeholder="e.g. Roaming instead of participating")
            with cf2: nb2 = st.text_input("Behaviour 2 (optional)", placeholder="e.g. Verbal outbursts")
            nl = st.text_input("Label (optional)", placeholder="e.g. Term 1 Week 3")
            if st.form_submit_button("✅ Start Tracking", type="primary", use_container_width=True):
                if not nb1.strip():
                    st.error("Please enter at least Behaviour 1.")
                else:
                    sb2 = get_sb()
                    if sb2:
                        try:
                            res = sb2.table("scatter_tracking_periods").insert({
                                "student_id":   selected_id,
                                "student_name": stu_name_c,
                                "start_date":   date.today().isoformat(),
                                "behaviour_1":  nb1.strip(),
                                "behaviour_2":  nb2.strip(),
                                "label":        nl.strip(),
                            }).execute()
                            if res.data:
                                ss.spt_period_id = res.data[0]["id"]
                        except Exception as e:
                            st.error("Could not create period: " + str(e))
                    ss.spt_beh1        = nb1.strip()
                    ss.spt_beh2        = nb2.strip()
                    ss.spt_show_choice = False
                    st.rerun()

    st.stop()

# ── NEW PERIOD FORM ───────────────────────────────────────────────────────
if ss.get("spt_show_new_period"):
    stu_name_np = ss.spt_student_name or student_opts.get(selected_id,"")
    st.markdown("### 🔄 New Tracking Period — " + stu_name_np)
    st.caption("Your existing data is preserved. A new period begins today.")
    with st.form("new_period_from_choice"):
        np1, np2, np3 = st.columns([2.5, 2.5, 2])
        with np1: np_beh1  = st.text_input("Behaviour 1 *", placeholder="e.g. Hitting peers")
        with np2: np_beh2  = st.text_input("Behaviour 2 (optional)")
        with np3: np_label = st.text_input("Label (optional)", placeholder="e.g. Term 2 Week 3")
        cc1, cc2 = st.columns(2)
        with cc1: do_start  = st.form_submit_button("✅ Start New Period", type="primary", use_container_width=True)
        with cc2: do_cancel = st.form_submit_button("← Go back", use_container_width=True)
    if do_cancel:
        ss.spt_show_new_period = False
        ss.spt_show_choice     = True
        st.rerun()
    if do_start:
        if not np_beh1.strip():
            st.error("Please enter at least Behaviour 1.")
        else:
            new_p = create_period(selected_id, ss.spt_student_name,
                                  np_beh1.strip(), np_beh2.strip(), np_label.strip())
            if new_p:
                ss.spt_period_id       = new_p["id"]
                ss.spt_beh1            = np_beh1.strip()
                ss.spt_beh2            = np_beh2.strip()
                ss.spt_show_new_period = False
                load_tracked_students.clear()
                st.success("✅ New tracking period started.")
                st.rerun()
    st.stop()

student_id   = ss.spt_student_id
student_name = ss.spt_student_name or student_opts.get(student_id,"")

if not student_id:
    st.info("Select a student above to start.")
    st.stop()

# Load schedule
if ss.spt_schedule is None:
    ss.spt_schedule = load_schedule(student_id)
schedule = ss.spt_schedule

behaviours = [b for b in [ss.spt_beh1.strip(), ss.spt_beh2.strip()] if b]
if not behaviours:
    st.warning("Enter at least one target behaviour above.")
    st.stop()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# TRACKING PERIOD MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════
periods = load_periods(student_id)

# Show current active period + period switcher
if periods:
    active = next((p for p in periods if not p.get("end_date")), None)
    if active:
        beh_str = active["behaviour_1"]
        if active.get("behaviour_2"):
            beh_str += f" · {active['behaviour_2']}"
        start_str = pd.to_datetime(active["start_date"]).strftime("%-d %b %Y")
        st.markdown(
            f'<div class="period-active">'
            f'<span style="font-size:.72rem;color:#15803d;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.05em;">Active tracking period</span><br>'
            f'<span style="font-size:.88rem;font-weight:600;color:#14532d;">'
            f'{active.get("label") or ("Period " + str(len(periods)))}</span>'
            f'<span style="font-size:.78rem;color:#166534;"> — started {start_str}</span><br>'
            f'<span style="font-size:.78rem;color:#166534;">'
            f'Tracking: {beh_str}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Keep period_id in sync
        if ss.spt_period_id != active["id"]:
            ss.spt_period_id = active["id"]

    # Period selector (to view historical periods)
    if len(periods) > 1:
        period_labels = {
            p["id"]: (
                f"{'✅ ' if not p.get('end_date') else ''}"
                f"{p.get('label') or ('Period ' + str(len(periods)-i))}"
                f" — {p['behaviour_1']}"
                + (f" · {p['behaviour_2']}" if p.get('behaviour_2') else "")
                + f" ({pd.to_datetime(p['start_date']).strftime('%-d %b %y')}"
                + (f" – {pd.to_datetime(p['end_date']).strftime('%-d %b %y')}" if p.get('end_date') else " – now")
                + ")"
            )
            for i, p in enumerate(periods)
        }
        pc1, pc2 = st.columns([4, 1])
        with pc1:
            chosen_period_id = st.selectbox(
                "Viewing period", list(period_labels.keys()),
                index=0,
                format_func=lambda x: period_labels[x],
                key="spt_period_sel"
            )
        with pc2:
            st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
            if st.button("Switch view", use_container_width=True, key="spt_switch_period"):
                ss.spt_period_id = chosen_period_id
                # Load behaviours for this period
                chosen_p = next((p for p in periods if p["id"]==chosen_period_id), None)
                if chosen_p:
                    ss.spt_beh1 = chosen_p.get("behaviour_1","")
                    ss.spt_beh2 = chosen_p.get("behaviour_2","")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# Start new tracking period
with st.expander("🔄 Start new tracking period (behaviours have changed)"):
    st.caption(
        "Use this when the behaviours you are tracking change. "
        "Your existing data is preserved and can still be viewed by selecting the old period above. "
        "A new period begins today."
    )
    with st.form("spt_new_period_form"):
        np1, np2, np3 = st.columns([2.5, 2.5, 2])
        with np1:
            np_beh1 = st.text_input("New Behaviour 1 *", placeholder="e.g. Hitting peers")
        with np2:
            np_beh2 = st.text_input("New Behaviour 2 (optional)", placeholder="e.g. Spitting")
        with np3:
            np_label = st.text_input("Label (optional)", placeholder="e.g. Term 2 Week 1")
        if st.form_submit_button("✅ Start New Period", type="primary", use_container_width=True):
            if not np_beh1.strip():
                st.error("Please enter at least Behaviour 1.")
            else:
                new_p = create_period(student_id, student_name,
                                      np_beh1.strip(), np_beh2.strip(), np_label.strip())
                if new_p:
                    ss.spt_period_id = new_p["id"]
                    ss.spt_beh1      = np_beh1.strip()
                    ss.spt_beh2      = np_beh2.strip()
                    load_tracked_students.clear()
                    st.success("✅ New tracking period started.")
                    st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis & Download"])

with t_record:

    # Persistent error display
    _err = ss.get("_spt_last_error")
    if _err:
        if _err.startswith("⚠️"):
            st.warning(_err)
        else:
            st.error(_err)
        if st.button("Dismiss", key="spt_dismiss_err"):
            ss.pop("_spt_last_error", None)
            st.rerun()

    # Week navigation
    week_start = ss.spt_week_start
    week_end   = week_start + timedelta(days=4)
    this_week  = date.today() - timedelta(days=date.today().weekday())
    is_this    = week_start == this_week

    wc1, wc2, wc3, wc4 = st.columns([1,4,1,1])
    with wc1:
        if st.button("← Prev", use_container_width=True, key="spt_prev"):
            ss.spt_week_start -= timedelta(weeks=1); st.rerun()
    with wc2:
        st.markdown(
            f'<div style="text-align:center;padding:.38rem 0;font-weight:700;'
            f'color:{TEAL};font-size:.9rem;">'
            f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
            + (' &nbsp;<span style="background:#dbeafe;color:#1d4ed8;font-size:.68rem;'
               'padding:.1rem .45rem;border-radius:10px;">This week</span>' if is_this else '')
            + '</div>', unsafe_allow_html=True
        )
    with wc3:
        if st.button("Next →", use_container_width=True, key="spt_next"):
            ss.spt_week_start += timedelta(weeks=1); st.rerun()
    with wc4:
        if st.button("Today", use_container_width=True, key="spt_today"):
            ss.spt_week_start = this_week; st.rerun()

    # Load week data (filtered to current period)
    week_df = load_week_obs(student_id, week_start, week_end, ss.spt_period_id)

    # Build cell lookup: {beh_index: {time_slot: {day: {id, value}}}}
    cell_data = {i: {} for i in range(len(behaviours))}
    if not week_df.empty:
        for _, row in week_df.iterrows():
            t   = row.get("time_slot","")
            d   = row.get("day_of_week","")
            bi  = int(row.get("behaviour_index",0) or 0)
            rid = row.get("id","")
            val = row.get("value","")
            if not t or not d or bi not in cell_data: continue
            if t not in cell_data[bi]: cell_data[bi][t] = {}
            cell_data[bi][t][d] = {"id": rid, "value": val}

    # Legend
    st.markdown(
        '<div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;'
        'font-size:.75rem;margin:.25rem 0 .6rem;">'
        f'<b>Key:</b>'
        '<span style="background:#dbeafe;color:#1d4ed8;padding:.1rem .5rem;'
        'border-radius:12px;font-weight:700;">1</span> one occurrence &nbsp;'
        '<span style="background:#fee2e2;color:#b91c1c;padding:.1rem .5rem;'
        'border-radius:12px;font-weight:700;">2</span> more than one &nbsp;'
        '<span style="background:#f3f4f6;color:#9ca3af;padding:.1rem .5rem;'
        'border-radius:12px;font-weight:700;">X</span> evacuation / unable to observe &nbsp;'
        '<span style="background:#f0fdf4;color:#15803d;padding:.1rem .5rem;'
        'border-radius:12px;font-weight:600;">✓</span> observed — no behaviour'
        '</div>',
        unsafe_allow_html=True
    )

    # Grids — one tab per behaviour
    beh_tabs = st.tabs([f"Behaviour {i+1}: {b[:35] + ('…' if len(b)>35 else '')}"
                        for i, b in enumerate(behaviours)])
    day_dates = {DAYS[i]: (week_start + timedelta(days=i)).strftime("%-d/%m") for i in range(5)}
    today_day = DAYS[date.today().weekday()] if date.today().weekday() < 5 else None

    for bi, btab in enumerate(beh_tabs):
        with btab:
            th = '<th class="lh">Time</th><th class="la">Activity</th>'
            for d in DAYS:
                is_td = (d == today_day and is_this)
                bg    = 'background:#1a4d8a;' if is_td else ''
                th   += (f'<th style="{bg}">{d[:3]}<br>'
                         f'<span style="font-weight:400;font-size:.62rem;">{day_dates[d]}</span></th>')

            rows_html = ""
            for slot in schedule:
                t   = slot["time"]
                act = slot["activity"]
                rows_html += f'<tr><td class="tl">{t}</td><td class="al">{act}</td>'
                for d in DAYS:
                    cell = cell_data.get(bi,{}).get(t,{}).get(d)
                    if cell:
                        v   = cell["value"]
                        cls = {"1":"c1","2":"c2","X":"cx","0":"c0"}.get(v,"ce")
                        disp = "✓" if v == "0" else v
                        rows_html += f'<td class="{cls}">{disp}</td>'
                    else:
                        rows_html += '<td class="ce">·</td>'
                rows_html += "</tr>"

            st.markdown(
                f'<div class="grid-wrap"><table class="sg">'
                f'<thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody></table></div>',
                unsafe_allow_html=True
            )

            # Daily totals (1 and 2 only, not ✓ or X)
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
                    f"<div class='kpi kpi-a'><div class='val'>{grand}</div>"
                    f"<div class='lbl'>Incidents</div></div>", unsafe_allow_html=True
                )

    # Quick entry strip
    st.markdown("---")
    st.markdown("**➕ Record an observation**")

    slot_times = [s["time"] for s in schedule]
    today_day_name = DAYS[date.today().weekday()] if date.today().weekday() < 5 else DAYS[0]

    qc1, qc2 = st.columns([2.5, 2])
    with qc1:
        sel_time = st.selectbox("Time slot", slot_times, key="spt_q_time")
    with qc2:
        sel_day = st.selectbox("Day", DAYS,
            index=DAYS.index(today_day_name) if today_day_name in DAYS else 0,
            key="spt_q_day")

    sel_activity = next((s["activity"] for s in schedule if s["time"]==sel_time),"")
    sel_date     = week_start + timedelta(days=DAYS.index(sel_day))

    for bi, beh in enumerate(behaviours):
        existing = cell_data.get(bi,{}).get(sel_time,{}).get(sel_day)
        cur_val  = existing["value"] if existing else ""

        val_styles = {
            "1": "background:#dbeafe;color:#1d4ed8",
            "2": "background:#fee2e2;color:#b91c1c",
            "X": "background:#f3f4f6;color:#6b7280",
            "0": "background:#f0fdf4;color:#15803d",
        }
        cur_disp  = "✓" if cur_val == "0" else cur_val
        cur_badge = (
            f'<span style="padding:.1rem .45rem;border-radius:8px;font-weight:700;'
            f'{val_styles.get(cur_val,"")};font-size:.75rem;">{cur_disp}</span>'
            if cur_val else '<span style="color:#ccc;font-size:.72rem;">—</span>'
        )

        rc1, rc2, rc3, rc4, rc5, rc6 = st.columns([4, 0.7, 0.7, 0.7, 0.7, 0.5])
        with rc1:
            st.markdown(
                f'<div style="padding:.55rem 0 .2rem;font-size:.82rem;font-weight:600;color:#334155;">'
                f'B{bi+1}: {beh[:50]}{"…" if len(beh)>50 else ""} &nbsp;{cur_badge}</div>',
                unsafe_allow_html=True
            )
        with rc2:
            if st.button("1", key=f"spt_b{bi}_1", use_container_width=True, type="primary"):
                upsert_obs(student_id, student_name, sel_date, sel_day, sel_time,
                           sel_activity, "1", bi, beh, " | ".join(behaviours),
                           ss.spt_period_id, existing["id"] if existing else None)
                st.rerun()
        with rc3:
            if st.button("2", key=f"spt_b{bi}_2", use_container_width=True):
                upsert_obs(student_id, student_name, sel_date, sel_day, sel_time,
                           sel_activity, "2", bi, beh, " | ".join(behaviours),
                           ss.spt_period_id, existing["id"] if existing else None)
                st.rerun()
        with rc4:
            if st.button("X", key=f"spt_b{bi}_x", use_container_width=True):
                upsert_obs(student_id, student_name, sel_date, sel_day, sel_time,
                           sel_activity, "X", bi, beh, " | ".join(behaviours),
                           ss.spt_period_id, existing["id"] if existing else None)
                st.rerun()
        with rc5:
            if st.button("✓", key=f"spt_b{bi}_0", use_container_width=True,
                         help="Observed — no behaviour"):
                upsert_obs(student_id, student_name, sel_date, sel_day, sel_time,
                           sel_activity, "0", bi, beh, " | ".join(behaviours),
                           ss.spt_period_id, existing["id"] if existing else None)
                st.rerun()
        with rc6:
            if cur_val and st.button("✕", key=f"spt_b{bi}_clr", use_container_width=True,
                                     help="Clear this cell"):
                if existing:
                    delete_obs(existing["id"])
                    st.rerun()

    # Remove entry
    with st.expander("🗑️ Remove an entry from this week"):
        entries = []
        if not week_df.empty:
            for _, row in week_df.iterrows():
                bi  = int(row.get("behaviour_index",0) or 0)
                beh = behaviours[bi] if bi < len(behaviours) else row.get("behaviour_label","?")
                val = row.get("value","")
                disp = "✓ (no behaviour)" if val=="0" else val
                entries.append({
                    "label": f"B{bi+1} · {row['day_of_week']} {row['time_slot']} — {disp}  ({beh[:25]})",
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
                    oid = next(e["id"] for e in entries if e["label"]==chosen)
                    if delete_obs(oid): st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # Manage schedule
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
                sched[i] = {"time":nt,"activity":na}; changed = True
            if changed:
                ss.spt_schedule = sched; save_schedule(student_id, sched); st.rerun()

        st.markdown("---")
        nc1, nc2, nc3 = st.columns([1.5,3,1])
        with nc1: new_t = st.text_input("Time", placeholder="e.g. 8:45", key="sched_nt")
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
# TAB 2 — ANALYSIS (incidents only: values 1 and 2, excludes 0 and X)
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:
    st.markdown(f"#### {student_name} — Scatter Plot Analysis")
    st.caption("Analysis includes only values 1 (single) and 2 (multiple). "
               "✓ (observed, no behaviour) and X (evacuation) are excluded from charts.")

    all_obs = load_all_obs(student_id, ss.spt_period_id)

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

    # Split: incidents (1,2) vs accountability (0) vs evacuation (X)
    inc_filt  = filt[filt["value"].isin(["1","2"])].copy()
    zero_filt = filt[filt["value"]=="0"].copy()
    x_filt    = filt[filt["value"]=="X"].copy()

    n1    = (filt["value"]=="1").sum()
    n2    = (filt["value"]=="2").sum()
    n0    = len(zero_filt)
    nx    = len(x_filt)
    n_inc = n1 + n2

    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"<div class='kpi'><div class='val'>{n_inc}</div><div class='lbl'>Incident intervals</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='val'>{n1}</div><div class='lbl'>Single (1)</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n2}</div><div class='lbl'>Multiple (2)</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='kpi kpi-g'><div class='val'>{n0}</div><div class='lbl'>✓ No behaviour observed</div></div>", unsafe_allow_html=True)

    if inc_filt.empty:
        st.success("🎉 No incidents recorded in this period — only 'no behaviour' observations.")
        st.stop()

    st.markdown("---")

    # Build time label map from schedule
    time_labels = {s["time"]: f"{s['time']}  {s['activity']}" for s in schedule}
    def _sort_t(t):
        try: h,m = str(t).split(":"); return int(h)*60+int(m)
        except: return 999

    # Per-behaviour scatter plots
    an_tabs = st.tabs([f"Behaviour {i+1}: {b[:40]}" for i,b in enumerate(behaviours)] + ["Combined"])

    for bi, abtab in enumerate(an_tabs[:-1]):
        with abtab:
            b_inc = inc_filt[inc_filt["behaviour_index"]==bi].copy() \
                if "behaviour_index" in inc_filt.columns \
                else inc_filt[inc_filt.get("behaviour_label","") == behaviours[bi]].copy()
            b_zero = zero_filt[zero_filt.get("behaviour_index",pd.Series(dtype=int))==bi].copy() \
                if "behaviour_index" in zero_filt.columns else pd.DataFrame()

            if b_inc.empty:
                st.info("No incidents for this behaviour in the selected range.")
                if not b_zero.empty:
                    st.success(f"✅ {len(b_zero)} 'no behaviour observed' records — great compliance tracking!")
                continue

            bv1 = int((b_inc["value"]=="1").sum())
            bv2 = int((b_inc["value"]=="2").sum())
            kc1,kc2,kc3 = st.columns(3)
            kc1.markdown(f"<div class='kpi'><div class='val'>{bv1+bv2}</div><div class='lbl'>Incident intervals</div></div>", unsafe_allow_html=True)
            kc2.markdown(f"<div class='kpi'><div class='val'>{bv1}</div><div class='lbl'>Single (1)</div></div>", unsafe_allow_html=True)
            kc3.markdown(f"<div class='kpi kpi-a'><div class='val'>{bv2}</div><div class='lbl'>Multiple (2)</div></div>", unsafe_allow_html=True)

            st.markdown("---")

            # ── SCATTER PLOT ─────────────────────────────────────────────
            b_inc["date_str"]   = b_inc["obs_date_dt"].dt.strftime("%a %-d %b")
            b_inc["date_order"] = b_inc["obs_date_dt"].dt.date
            b_inc["time_label"] = b_inc["time_slot"].map(time_labels).fillna(b_inc["time_slot"])
            b_inc["hover"]      = (
                b_inc["date_str"] + "<br>" + b_inc["time_label"] + "<br>" +
                b_inc["value"].map({"1":"Single occurrence","2":"Multiple occurrences"}).fillna(b_inc["value"]) +
                "<br>" + b_inc["day_of_week"]
            )

            all_slots = sorted(b_inc["time_slot"].unique(), key=_sort_t)
            ordered_labels = [time_labels.get(t,t) for t in all_slots]
            date_order = sorted(b_inc["date_str"].unique(),
                                key=lambda s: b_inc.loc[b_inc["date_str"]==s,"date_order"].min())

            inc1 = b_inc[b_inc["value"]=="1"]
            inc2 = b_inc[b_inc["value"]=="2"]

            fig = go.Figure()
            if not inc1.empty:
                fig.add_trace(go.Scatter(
                    x=inc1["date_str"], y=inc1["time_label"], mode="markers",
                    name="1 — single", marker=dict(size=16, color="#3b82f6", opacity=.85,
                    line=dict(color="white",width=1.5)),
                    hovertemplate="%{customdata}<extra></extra>", customdata=inc1["hover"],
                ))
            if not inc2.empty:
                fig.add_trace(go.Scatter(
                    x=inc2["date_str"], y=inc2["time_label"], mode="markers",
                    name="2 — multiple", marker=dict(size=26, color="#ef4444", opacity=.85,
                    line=dict(color="white",width=2)),
                    hovertemplate="%{customdata}<extra></extra>", customdata=inc2["hover"],
                ))

            fig.update_layout(
                title=dict(text=f"Scatter Plot — {behaviours[bi]}", font=dict(size=14,color="#0f172a"), x=0),
                height=max(420, len(ordered_labels)*28+120),
                xaxis=dict(title="Date", categoryorder="array", categoryarray=date_order,
                           showgrid=True, gridcolor="#e2e8f0", tickfont=dict(size=11), side="top"),
                yaxis=dict(title="", categoryorder="array", categoryarray=ordered_labels[::-1],
                           showgrid=True, gridcolor="#e2e8f0", tickfont=dict(size=11), automargin=True),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
                margin=dict(l=10,r=20,t=80,b=20), hovermode="closest",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("● Small blue = single (1)  ·  ● Large red = multiple (2)  ·  "
                       "Dates along top, time slots top to bottom  ·  ✓ observations not shown")

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                daily = b_inc.groupby(b_inc["obs_date_dt"].dt.date).size().reset_index(name="count")
                daily["ds"] = pd.to_datetime(daily["obs_date_dt"]).dt.strftime("%-d %b")
                fig2 = go.Figure(go.Bar(x=daily["ds"], y=daily["count"],
                    marker_color=[AMBER if v>=3 else TEAL for v in daily["count"]],
                    text=daily["count"], textposition="outside"))
                fig2.update_layout(title="Incidents per day", height=250, showlegend=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    yaxis=dict(tickformat="d",gridcolor="#e2e8f0"), margin=dict(l=10,r=10,t=45,b=10))
                st.plotly_chart(fig2, use_container_width=True)
            with col_b:
                dow = b_inc.groupby("day_of_week").size().reindex(DAYS, fill_value=0)
                fig3 = go.Figure(go.Bar(x=dow.index, y=dow.values, marker_color=TEAL,
                    text=dow.values, textposition="outside"))
                fig3.update_layout(title="Incidents by day", height=250, showlegend=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    yaxis=dict(tickformat="d",gridcolor="#e2e8f0"), margin=dict(l=10,r=10,t=45,b=10))
                st.plotly_chart(fig3, use_container_width=True)

            # Hotspot table
            slot_counts = b_inc.groupby("time_label")["value"].agg(
                total="count",
                single=lambda x: (x=="1").sum(),
                multiple=lambda x: (x=="2").sum(),
                days=lambda x: b_inc.loc[x.index,"day_of_week"].nunique(),
            ).reset_index().sort_values("total",ascending=False)
            slot_counts.columns=["Time Slot","Total","Single (1)","Multiple (2)","Days"]
            st.markdown("**Hotspot summary:**")
            st.dataframe(slot_counts, use_container_width=True, hide_index=True)

    # Combined tab
    with an_tabs[-1]:
        if inc_filt.empty:
            st.info("No incidents recorded."); st.stop()
        if "behaviour_index" in inc_filt.columns:
            inc_filt2 = inc_filt.copy()
            inc_filt2["Behaviour"] = inc_filt2["behaviour_index"].apply(
                lambda i: f"B{int(i)+1}: {behaviours[int(i)][:35]}" if int(i)<len(behaviours) else f"B{int(i)+1}"
            )
        else:
            inc_filt2 = inc_filt.copy()
            inc_filt2["Behaviour"] = inc_filt2.get("behaviour_label","B1")

        inc_filt2["date_str"]   = inc_filt2["obs_date_dt"].dt.strftime("%a %-d %b")
        inc_filt2["date_order"] = inc_filt2["obs_date_dt"].dt.date
        inc_filt2["time_label"] = inc_filt2["time_slot"].map(time_labels).fillna(inc_filt2["time_slot"])
        inc_filt2["size_val"]   = inc_filt2["value"].map({"1":16,"2":26}).fillna(16)

        fig_c = go.Figure()
        colours = {"B1":"#3b82f6","B2":"#ef4444"}
        for b_label in inc_filt2["Behaviour"].unique():
            sub  = inc_filt2[inc_filt2["Behaviour"]==b_label]
            idx  = list(inc_filt2["Behaviour"].unique()).index(b_label)
            col  = ["#3b82f6","#ef4444","#f59e0b"][idx % 3]
            for val, sz in [("1",16),("2",26)]:
                s = sub[sub["value"]==val]
                if s.empty: continue
                fig_c.add_trace(go.Scatter(
                    x=s["date_str"], y=s["time_label"], mode="markers",
                    name=f"{b_label} ({'single' if val=='1' else 'multiple'})",
                    marker=dict(size=sz, color=col, opacity=.75,
                                line=dict(color="white",width=1.5),
                                symbol="circle" if val=="1" else "circle-open"),
                ))

        date_order_c = sorted(inc_filt2["date_str"].unique(),
                              key=lambda s: inc_filt2.loc[inc_filt2["date_str"]==s,"date_order"].min())
        all_labels_c = sorted(inc_filt2["time_label"].unique(),
                              key=lambda l: _sort_t(l.split()[0]))
        fig_c.update_layout(
            title="Combined Scatter Plot — All Behaviours",
            height=max(420, len(all_labels_c)*28+120),
            xaxis=dict(categoryorder="array", categoryarray=date_order_c,
                       showgrid=True, gridcolor="#e2e8f0", side="top"),
            yaxis=dict(categoryorder="array", categoryarray=all_labels_c[::-1],
                       showgrid=True, gridcolor="#e2e8f0", automargin=True),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=10,r=20,t=80,b=20), hovermode="closest",
        )
        st.plotly_chart(fig_c, use_container_width=True)

    # Download
    st.markdown("---")
    dl = filt.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    dl["value_desc"] = dl["value"].map({"1":"Single","2":"Multiple","X":"Evacuation","0":"No behaviour observed"})
    csv = dl[["obs_date","day_of_week","time_slot","activity","value","value_desc",
              "behaviour_index","behaviour_label","target_behaviours","created_by"]].to_csv(index=False)
    st.download_button("📥 Download CSV", csv,
        file_name=f"ScatterPlot_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv", use_container_width=True)
