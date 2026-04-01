# ════════════════════════════════════════════════════════════════════════════
# 18_Scatter_Plot_Tracker.py  ·  CLC-LBU Portal
# Scatter Plot Tracker
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
.stu-card {
    background:white; border:1.5px solid #e2e8f0; border-radius:10px;
    padding:.65rem 1rem; margin-bottom:.4rem; cursor:pointer;
}
.stu-card:hover { border-color:#1A6B8A; }
.stu-active { border-color:#1A6B8A; background:#EBF4F9; }
.grid-wrap { overflow-x:auto; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:.6rem; }
.sg { width:100%; border-collapse:collapse; font-size:.8rem; }
.sg th {
    background:#1A6B8A; color:white; padding:.38rem .45rem;
    text-align:center; font-size:.7rem; font-weight:600; white-space:nowrap;
}
.sg th.lh { text-align:left; min-width:50px; }
.sg th.la { text-align:left; min-width:110px; }
.sg td { padding:.25rem .35rem; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; }
.sg td.tl { text-align:left; font-weight:600; color:#334155; font-size:.73rem; white-space:nowrap; background:#f8fafc; }
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
.ins { background:#FEF9EC; border-left:4px solid #D4860A; border-radius:6px;
       padding:.45rem .85rem; font-size:.82rem; margin-bottom:.3rem; }
.ins-ok { background:#F0FAF4; border-left:4px solid #2EA056; }
.period-active {
    background:#f0fdf4; border:2px solid #22c55e; border-radius:10px;
    padding:.55rem 1rem; margin-bottom:.75rem; font-size:.85rem;
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


# ── Supabase ──────────────────────────────────────────────────────────────────
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


BEHAVIOUR_CATEGORIES = [
    "Physical — peer directed",
    "Physical — adult directed",
    "Self-injurious",
    "Property / environment",
    "Elopement / movement",
    "Verbal",
    "Refusal / non-compliance",
    "Dysregulation / other",
]
GROUPINGS = {
    "i":   "Independent",
    "1:1": "One-to-one",
    "sg":  "Small group",
    "lg":  "Large group",
    "U":   "Unstructured",
    "P":   "Peer",
}
SETTINGS = ["Classroom","Kitchen","Yard","Playground","Spill-out","Transition","Other"]

ENG_LEVELS = {
    "E": {"label":"Engaged",          "colour":"#16a34a","bg":"#dcfce7","desc":"On task, no additional support needed"},
    "P": {"label":"Partial",          "colour":"#d97706","bg":"#fef3c7","desc":"On task with support"},
    "N": {"label":"Not engaged",      "colour":"#dc2626","bg":"#fee2e2","desc":"Off task"},
}
ENG_SUPPORT = [
    "—", "1:1 SSO", "1:1 Teacher", "Small group",
    "Peer support", "Modified task", "Visual supports", "Sensory break",
]


@st.cache_data(ttl=120)
def load_behaviour_bank():
    """Load all behaviours from Supabase bank."""
    sb = get_sb()
    if not sb: return {}
    try:
        res = sb.table("scatter_behaviour_bank").select("*").order("category").order("description").execute()
        bank = {}
        for row in (res.data or []):
            cat = row["category"]
            if cat not in bank:
                bank[cat] = []
            bank[cat].append({"id": row["id"], "description": row["description"],
                               "is_custom": row.get("is_custom", False)})
        return bank
    except Exception:
        return {}


def add_custom_behaviour(category, description):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_behaviour_bank").insert({
            "category": category, "description": description, "is_custom": True
        }).execute()
        load_behaviour_bank.clear()
        return True
    except Exception as e:
        st.error("Could not save: " + str(e))
        return False


def delete_behaviour(beh_id):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_behaviour_bank").delete().eq("id", beh_id).execute()
        load_behaviour_bank.clear()
        return True
    except Exception:
        return False


def load_all_student_summaries():
    """Return list of dicts per tracked student. Queries in pages to avoid Supabase 1000-row limit."""
    sb = get_sb()
    if not sb: return []
    try:
        # Step 1: get all distinct student names using pagination
        all_rows = []
        page = 0
        page_size = 1000
        while True:
            res = (sb.table("scatter_plot_observations")
                   .select("student_name,behaviour_label,obs_date")
                   .range(page * page_size, (page + 1) * page_size - 1)
                   .execute())
            if not res.data:
                break
            all_rows.extend(res.data)
            if len(res.data) < page_size:
                break
            page += 1

        if not all_rows:
            return []

        df = pd.DataFrame(all_rows)
        df = df[df["student_name"].notna() & (df["student_name"].str.strip() != "")]
        df["obs_date"] = pd.to_datetime(df["obs_date"])
        out = []
        for name, grp in df.groupby("student_name"):
            behs = [b for b in grp["behaviour_label"].dropna().unique() if b][:2]
            out.append({
                "name":       name,
                "total":      len(grp),
                "last_date":  grp["obs_date"].max().strftime("%-d %b %Y"),
                "behaviours": behs,
            })
        return sorted(out, key=lambda x: x["name"])
    except Exception as e:
        st.error("Could not load student list: " + str(e))
        return []


def load_periods_by_name(student_name):
    sb = get_sb()
    if not sb: return []
    try:
        res = (sb.table("scatter_tracking_periods")
               .select("*")
               .eq("student_name", student_name)
               .order("start_date", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


def create_period(student_name, beh1, beh2, label=""):
    sb = get_sb()
    if not sb: return None
    try:
        # Close active periods first
        sb.table("scatter_tracking_periods").update(
            {"end_date": date.today().isoformat()}
        ).eq("student_name", student_name).is_("end_date", "null").execute()
        res = sb.table("scatter_tracking_periods").insert({
            "student_id":   student_name,  # reuse column for name
            "student_name": student_name,
            "start_date":   date.today().isoformat(),
            "end_date":     None,
            "behaviour_1":  beh1.strip(),
            "behaviour_2":  beh2.strip(),
            "label":        label.strip(),
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error("Could not create period: " + str(e))
        return None


def load_week_obs(student_name, week_start, week_end):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("scatter_plot_observations")
               .select("*")
               .eq("student_name", student_name)
               .gte("obs_date", str(week_start))
               .lte("obs_date", str(week_end))
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"]  = pd.to_datetime(df["obs_date"])
            df["day_of_week"]  = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception as e:
        st.error("Load error: " + str(e))
        return pd.DataFrame()


def load_all_obs(student_name):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("scatter_plot_observations")
               .select("*")
               .eq("student_name", student_name)
               .order("obs_date").order("time_slot")
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception:
        return pd.DataFrame()


def upsert_obs(student_name, sel_date, sel_day, sel_time, activity,
               value, beh_index, beh_label, behaviours_str,
               period_id=None, existing_id=None):
    sb = get_sb()
    if not sb:
        st.session_state["_spt_err"] = "Supabase not configured."
        return False
    row = {
        "student_id":         student_name,
        "student_name":       student_name,
        "obs_date":           sel_date.isoformat(),
        "day_of_week":        sel_day,
        "time_slot":          sel_time,
        "activity":           activity,
        "value":              value,
        "behaviour_index":    beh_index,
        "behaviour_label":    beh_label,
        "target_behaviours":  behaviours_str,
        "tracking_period_id": period_id,
        "grouping":           "",
        "setting":            "",
        "created_by":         get_staff_name(),
    }
    minimal = {k: v for k, v in row.items()
               if k not in ("behaviour_index","behaviour_label","tracking_period_id",
                             "grouping","setting")}
    try:
        if existing_id:
            sb.table("scatter_plot_observations").update(
                {"value": value, "behaviour_label": beh_label}
            ).eq("id", existing_id).execute()
        else:
            sb.table("scatter_plot_observations").insert(row).execute()
        st.session_state.pop("_spt_err", None)
        return True
    except Exception as e:
        err = str(e)
        if any(k in err for k in ["behaviour_index","behaviour_label","tracking_period_id","column"]):
            try:
                if existing_id:
                    sb.table("scatter_plot_observations").update(
                        {"value": value}).eq("id", existing_id).execute()
                else:
                    sb.table("scatter_plot_observations").insert(minimal).execute()
                st.session_state["_spt_err"] = "⚠️ Saved (run scatter_v4_schema.sql for full support)"
                return True
            except Exception as e2:
                st.session_state["_spt_err"] = "Save failed: " + str(e2)
                return False
        st.session_state["_spt_err"] = "Save failed: " + err
        return False


def load_week_eng(student_name, week_start, week_end):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("scatter_engagement_observations")
               .select("*")
               .eq("student_name", student_name)
               .gte("obs_date", str(week_start))
               .lte("obs_date", str(week_end))
               .execute())
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
            df["day_of_week"] = df["obs_date_dt"].apply(
                lambda x: DAYS[x.weekday()] if x.weekday() < 5 else "")
        return df
    except Exception as e:
        st.error("Engagement load error: " + str(e))
        return pd.DataFrame()


def load_all_eng(student_name):
    sb = get_sb()
    if not sb: return pd.DataFrame()
    try:
        res = (sb.table("scatter_engagement_observations")
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


def upsert_eng(student_name, sel_date, sel_day, sel_time, eng_level, support="—"):
    sb = get_sb()
    if not sb: return False
    try:
        # UPSERT — unique on student_name + obs_date + time_slot
        existing = (sb.table("scatter_engagement_observations")
                    .select("id")
                    .eq("student_name", student_name)
                    .eq("obs_date", sel_date.isoformat())
                    .eq("time_slot", sel_time)
                    .limit(1).execute())
        row = {
            "student_name": student_name,
            "obs_date":     sel_date.isoformat(),
            "day_of_week":  sel_day,
            "time_slot":    sel_time,
            "eng_level":    eng_level,
            "support_type": support,
            "created_by":   get_staff_name(),
        }
        if existing.data:
            sb.table("scatter_engagement_observations").update(
                {"eng_level": eng_level, "support_type": support}
            ).eq("id", existing.data[0]["id"]).execute()
        else:
            sb.table("scatter_engagement_observations").insert(row).execute()
        return True
    except Exception as e:
        st.error("Engagement save failed: " + str(e))
        return False


def delete_eng(student_name, sel_date, sel_time):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_engagement_observations").delete()            .eq("student_name", student_name)            .eq("obs_date", sel_date.isoformat())            .eq("time_slot", sel_time).execute()
        return True
    except Exception:
        return False


def delete_obs(obs_id):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_plot_observations").delete().eq("id", obs_id).execute()
        return True
    except Exception as e:
        st.error("Delete failed: " + str(e))
        return False


def load_schedule_by_name(student_name):
    sb = get_sb()
    if not sb: return DEFAULT_SCHEDULE.copy()
    try:
        res = (sb.table("scatter_plot_schedules")
               .select("schedule").eq("student_id", student_name).limit(1).execute())
        if res.data:
            raw = res.data[0]["schedule"]
            return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        pass
    return DEFAULT_SCHEDULE.copy()


def save_schedule_by_name(student_name, schedule):
    sb = get_sb()
    if not sb: return
    try:
        data = {"student_id": student_name, "schedule": json.dumps(schedule)}
        ex = sb.table("scatter_plot_schedules").select("id").eq("student_id", student_name).execute()
        if ex.data:
            sb.table("scatter_plot_schedules").update(data).eq("student_id", student_name).execute()
        else:
            sb.table("scatter_plot_schedules").insert(data).execute()
    except Exception:
        pass


# ── Session state ─────────────────────────────────────────────────────────────
ss = st.session_state
for k, v in [
    ("spt_name", ""),          ("spt_beh1", ""),
    ("spt_beh2", ""),          ("spt_schedule", None),
    ("spt_period_id", None),   ("spt_screen", "home"),
    ("spt_week_start", date.today() - timedelta(days=date.today().weekday())),
]:
    if k not in ss: ss[k] = v


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="clc-header">
  <h2>📊 Scatter Plot Tracker</h2>
  <p>Record targeted behaviour frequency across the school day
  &nbsp;·&nbsp; CLC Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# BEHAVIOUR PICKER — shared by first period + new period screens
# ════════════════════════════════════════════════════════════════════════════
def _behaviour_picker_ui(prefix, bank, label):
    """Render category → behaviour → tweak selector. Returns final behaviour string."""
    cats = list(bank.keys()) if bank else BEHAVIOUR_CATEGORIES
    cat = st.selectbox(f"Category — {label}", ["Select a category…"] + cats,
                       key=f"{prefix}_cat")
    if cat == "Select a category…":
        return ""
    behs  = bank.get(cat, [])
    descs = [b["description"] for b in behs]
    sel   = st.selectbox(f"Specific behaviour — {label}", ["Select…"] + descs,
                         key=f"{prefix}_beh")
    if sel == "Select…":
        return ""
    tweaked = st.text_input(
        "Refine wording if needed:",
        value=sel, key=f"{prefix}_tweak",
        help="Edit to make it more specific to this student, e.g. add 'during transitions'"
    )
    return tweaked.strip()


def _render_behaviour_picker(student_name, is_new_period=False):
    bank = load_behaviour_bank()

    st.markdown("#### Select behaviour(s) to track")
    st.caption(
        "Choose from the behaviour bank — pick the most specific description that matches "
        "what you want to measure. You can refine the wording below the selector."
    )

    # B1
    st.markdown("**Behaviour 1 * (required)**")
    b1 = _behaviour_picker_ui("b1", bank, "Behaviour 1")

    # B2
    st.markdown("**Behaviour 2** *(optional)*")
    b2 = _behaviour_picker_ui("b2", bank, "Behaviour 2")

    # Program type
    prog_type = st.radio(
        "Program type", ["Group program", "Modified program"],
        horizontal=True, key="picker_prog_type"
    )

    # Label
    label = st.text_input("Period label (optional)", placeholder="e.g. Term 1 Week 4",
                           key="picker_label")

    # Add custom behaviour
    with st.expander("➕ Add a custom behaviour to the bank"):
        cc1, cc2 = st.columns([2, 3])
        with cc1:
            custom_cat = st.selectbox("Category", BEHAVIOUR_CATEGORIES, key="custom_cat")
        with cc2:
            custom_desc = st.text_input("Behaviour description", key="custom_desc",
                                        placeholder="e.g. Bangs head on desk when given writing task")
        if st.button("Add to bank", key="custom_add_btn", type="secondary"):
            if custom_desc.strip():
                if add_custom_behaviour(custom_cat, custom_desc.strip()):
                    st.success("✅ Added to behaviour bank.")
                    st.rerun()
            else:
                st.warning("Please enter a description.")

    st.markdown("---")

    if st.button("✅ Start Tracking", type="primary", use_container_width=True,
                 key="picker_start_btn"):
        if not b1:
            st.error("Please select at least Behaviour 1.")
            return

        p = create_period(student_name, b1, b2, label)
        if p:
            sb2 = get_sb()
            if sb2:
                try:
                    sb2.table("scatter_tracking_periods").update(
                        {"program_type": prog_type}
                    ).eq("id", p["id"]).execute()
                except Exception:
                    pass
        ss.spt_beh1      = b1
        ss.spt_beh2      = b2
        ss.spt_period_id = p["id"] if p else None
        ss.spt_prog_type = prog_type
        ss.spt_screen    = "tracker"
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# SCREEN: HOME — pick or add student
# ════════════════════════════════════════════════════════════════════════════
if ss.spt_screen == "home":

    summaries = load_all_student_summaries()

    # Students with existing data
    if summaries:
        st.markdown("### Students with existing data")
        st.caption("Click a student to open their tracker.")
        for stu in summaries:
            c1, c2, c3, c4 = st.columns([3, 4, 2, 1])
            with c1:
                st.markdown(f"**{stu['name']}**")
            with c2:
                behs = stu["behaviours"]
                st.caption("  ·  ".join(behs) if behs else "—")
            with c3:
                st.caption(f"Last: {stu['last_date']}  ({stu['total']} obs)")
            with c4:
                if st.button("Open →", key="open_" + stu["name"], use_container_width=True):
                    ss.spt_name     = stu["name"]
                    ss.spt_schedule = None
                    ss.spt_screen   = "choose"
                    st.rerun()
        st.markdown("---")

    # Add / start new student
    st.markdown("### Start tracking a new student")
    with st.form("spt_new_stu_form"):
        new_name = st.text_input("Student name *", placeholder="e.g. Alex Smith")
        st.caption("Use the exact name as entered — this is how data is linked across sessions.")
        if st.form_submit_button("Start Tracking →", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("Please enter the student's name.")
            else:
                # Check if this name already has data
                existing = next((s for s in summaries if s["name"].lower() == new_name.strip().lower()), None)
                if existing:
                    st.warning(
                        f"⚠️ **{existing['name']}** already has {existing['total']} observations on record. "
                        "Use the 'Open →' button above to access their existing data, "
                        "or enter a different name."
                    )
                else:
                    ss.spt_name     = new_name.strip()
                    ss.spt_schedule = None
                    ss.spt_period_id = None
                    ss.spt_screen   = "choose"
                    st.rerun()
    st.stop()


# ════════════════════════════════════════════════════════════════════════════
# SCREEN: CHOOSE — continue or new period
# ════════════════════════════════════════════════════════════════════════════
if ss.spt_screen == "choose":

    student_name = ss.spt_name
    periods = load_periods_by_name(student_name)

    if st.button("← Back to student list", key="back_to_home"):
        ss.spt_screen = "home"
        st.rerun()

    st.markdown(f"### {student_name}")

    if periods:
        st.markdown("**Tracking periods on record:**")
        for i, p in enumerate(periods):
            active = not p.get("end_date")
            tag    = " ✅ Active" if active else ""
            sd     = pd.to_datetime(p["start_date"]).strftime("%-d %b %Y")
            ed     = pd.to_datetime(p["end_date"]).strftime("%-d %b %Y") if p.get("end_date") else "ongoing"
            b1     = p.get("behaviour_1","")
            b2     = p.get("behaviour_2","")
            lbl    = p.get("label") or ("Period " + str(len(periods)-i))
            behtxt = b1 + (" · " + b2 if b2 else "")
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid '
                f'{"#22c55e" if active else "#cbd5e1"};border-radius:8px;'
                f'padding:.5rem .9rem;margin-bottom:.3rem;font-size:.83rem;">'
                f'<b>{lbl}</b>{tag} &nbsp;'
                f'<span style="color:#64748b;">{sd} – {ed}</span><br>'
                f'<span style="color:#334155;">{behtxt}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        active_p = next((p for p in periods if not p.get("end_date")), periods[0])
        b1_a = active_p.get("behaviour_1","")
        b2_a = active_p.get("behaviour_2","")
        preview = b1_a + (" · " + b2_a if b2_a else "")

        st.markdown("**What would you like to do?**")
        ch1, ch2 = st.columns(2)
        with ch1:
            if st.button(
                "▶  Continue — " + preview[:50],
                type="primary", use_container_width=True, key="cont_btn"
            ):
                ss.spt_beh1      = b1_a
                ss.spt_beh2      = b2_a
                ss.spt_period_id = active_p["id"]
                ss.spt_screen    = "tracker"
                st.rerun()
        with ch2:
            if st.button(
                "🔄  New period — behaviours have changed",
                use_container_width=True, key="new_period_btn"
            ):
                ss.spt_screen = "new_period"
                st.rerun()

        if len(periods) > 1:
            st.markdown("**Or view a historical period:**")
            opts = {}
            for i, p in enumerate(periods):
                b1t  = p.get("behaviour_1","")
                b2t  = p.get("behaviour_2","")
                lbl_t= p.get("label") or ("Period " + str(len(periods)-i))
                sd_t = pd.to_datetime(p["start_date"]).strftime("%-d %b %y")
                ed_t = pd.to_datetime(p["end_date"]).strftime("%-d %b %y") if p.get("end_date") else "now"
                opts[p["id"]] = lbl_t + " — " + b1t + (" · "+b2t if b2t else "") + " (" + sd_t + "–" + ed_t + ")"
            vc1, vc2 = st.columns([4,1])
            with vc1:
                view_pid = st.selectbox("Select period", list(opts.keys()),
                                        format_func=lambda x: opts[x], key="view_period_sel")
            with vc2:
                st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
                if st.button("View", use_container_width=True, key="view_period_btn"):
                    vp = next((p for p in periods if p["id"]==view_pid), None)
                    if vp:
                        ss.spt_beh1      = vp.get("behaviour_1","")
                        ss.spt_beh2      = vp.get("behaviour_2","")
                        ss.spt_period_id = vp["id"]
                    ss.spt_screen = "tracker"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    else:
        # No periods yet — use behaviour bank picker
        _render_behaviour_picker(student_name, is_new_period=False)

    # ── DELETE ALL DATA FOR THIS STUDENT ──────────────────────────────────
    st.markdown("---")
    with st.expander("🗑️ Delete data for this student", expanded=False):
        st.warning(
            "⚠️ This permanently deletes observation data. "
            "You can delete a specific date range or all data for this student."
        )
        del_tab1, del_tab2 = st.tabs(["Delete a date range", "Delete ALL data"])
        with del_tab1:
            dd1, dd2 = st.columns(2)
            with dd1: del_from = st.date_input("From date", key="del_from")
            with dd2: del_to   = st.date_input("To date",   key="del_to")
            if st.button("🗑️ Delete observations in this range",
                         key="del_range_btn", type="secondary"):
                sb = get_sb()
                if sb:
                    try:
                        sb.table("scatter_plot_observations").delete()                            .eq("student_name", student_name)                            .gte("obs_date", str(del_from))                            .lte("obs_date", str(del_to))                            .execute()
                        st.success("✅ Deleted observations from "
                                   + del_from.strftime("%-d %b") + " to "
                                   + del_to.strftime("%-d %b %Y") + ".")
                        st.rerun()
                    except Exception as e:
                        st.error("Delete failed: " + str(e))
        with del_tab2:
            st.error("This will delete ALL observations AND all tracking periods for " + student_name + ".")
            confirm_name = st.text_input("Type the student's name to confirm:", key="del_confirm_name")
            if st.button("🗑️ Delete ALL data permanently", key="del_all_btn", type="secondary"):
                if confirm_name.strip().lower() != student_name.lower():
                    st.error("Name doesn't match — please type the student's exact name.")
                else:
                    sb = get_sb()
                    if sb:
                        try:
                            sb.table("scatter_plot_observations").delete()                                .eq("student_name", student_name).execute()
                            sb.table("scatter_tracking_periods").delete()                                .eq("student_name", student_name).execute()
                            try:
                                sb.table("scatter_plot_schedules").delete()                                    .eq("student_id", student_name).execute()
                            except Exception:
                                pass
                            st.success("✅ All data for " + student_name + " deleted.")
                            ss.spt_screen = "home"
                            st.rerun()
                        except Exception as e:
                            st.error("Delete failed: " + str(e))

    st.stop()


# ════════════════════════════════════════════════════════════════════════════
# SCREEN: NEW PERIOD
# ════════════════════════════════════════════════════════════════════════════
if ss.spt_screen == "new_period":
    st.markdown("### 🔄 New Tracking Period — " + ss.spt_name)
    st.caption("Existing data is preserved. A new period begins today.")
    if st.button("← Back", key="np_back"): ss.spt_screen = "choose"; st.rerun()
    _render_behaviour_picker(ss.spt_name, is_new_period=True)
    st.stop()


# ════════════════════════════════════════════════════════════════════════════
# SCREEN: TRACKER — the main grid + entry screen
# ════════════════════════════════════════════════════════════════════════════
student_name = ss.spt_name
behaviours   = [b for b in [ss.spt_beh1.strip(), ss.spt_beh2.strip()] if b]

if not student_name:
    ss.spt_screen = "home"; st.rerun()

# Load schedule
if ss.spt_schedule is None:
    ss.spt_schedule = load_schedule_by_name(student_name)
schedule = ss.spt_schedule

# Top bar: name + back + behaviours
tb1, tb2, tb3 = st.columns([1.5, 3, 3])
with tb1:
    if st.button("← Students", key="back_tracker", use_container_width=True):
        ss["_sched_expander_open"] = False
        ss.spt_screen = "home"; st.rerun()
with tb2:
    prog_badge = ss.get("spt_prog_type","")
    badge_html = (
        f'<span style="background:#dbeafe;color:#1d4ed8;font-size:.7rem;'
        f'font-weight:600;padding:.1rem .5rem;border-radius:10px;margin-left:.5rem;">{prog_badge}</span>'
        if prog_badge else ""
    )
    st.markdown(f"**{student_name}**" + badge_html, unsafe_allow_html=True)
    if behaviours:
        st.caption("  ·  ".join([f"B{i+1}: {b[:40]}" for i,b in enumerate(behaviours)]))
with tb3:
    if st.button("🔄 Change behaviours / new period", key="change_beh_btn", use_container_width=True):
        ss.spt_screen = "new_period"; st.rerun()

st.markdown("---")

# Tabs
t_record, t_analysis = st.tabs(["📋  Record & View", "📈  Analysis & Download"])

# ════════════════════════════════════════════════════════════════════════════
# RECORD & VIEW
# ════════════════════════════════════════════════════════════════════════════
with t_record:

    # Persistent error
    _err = ss.get("_spt_err")
    if _err:
        st.warning(_err) if _err.startswith("⚠️") else st.error(_err)
        if st.button("Dismiss", key="dismiss_err"): ss.pop("_spt_err", None); st.rerun()

    # Week navigation
    week_start = ss.spt_week_start
    week_end   = week_start + timedelta(days=4)
    this_week  = date.today() - timedelta(days=date.today().weekday())
    is_this    = week_start == this_week

    wc1, wc2, wc3, wc4 = st.columns([1,4,1,1])
    with wc1:
        if st.button("← Prev", use_container_width=True, key="prev_wk"):
            ss.spt_week_start -= timedelta(weeks=1); st.rerun()
    with wc2:
        st.markdown(
            f'<div style="text-align:center;padding:.38rem 0;font-weight:700;color:{TEAL};font-size:.9rem;">'
            f'Week of {week_start.strftime("%-d %b")} – {week_end.strftime("%-d %b %Y")}'
            + (' &nbsp;<span style="background:#dbeafe;color:#1d4ed8;font-size:.68rem;'
               'padding:.1rem .45rem;border-radius:10px;">This week</span>' if is_this else '')
            + '</div>', unsafe_allow_html=True
        )
    with wc3:
        if st.button("Next →", use_container_width=True, key="next_wk"):
            ss.spt_week_start += timedelta(weeks=1); st.rerun()
    with wc4:
        if st.button("Today", use_container_width=True, key="today_wk"):
            ss.spt_week_start = this_week; st.rerun()

    week_df = load_week_obs(student_name, week_start, week_end)

    # Cell lookup: {beh_index: {time_slot: {day: {id, value}}}}
    cell_data = {i: {} for i in range(max(len(behaviours), 1))}
    if not week_df.empty:
        for _, row in week_df.iterrows():
            t   = row.get("time_slot","")
            d   = row.get("day_of_week","")
            bi  = int(row.get("behaviour_index",0) or 0)
            val = row.get("value","")
            rid = row.get("id","")
            grp = row.get("grouping","") or ""
            stt = row.get("setting","")  or ""
            if not t or not d: continue
            if bi not in cell_data: cell_data[bi] = {}
            if t not in cell_data[bi]: cell_data[bi][t] = {}
            act = row.get("activity","") or ""
            cell_data[bi][t][d] = {"id": rid, "value": val, "grouping": grp, "setting": stt, "activity": act}

    # Legend
    st.markdown(
        '<div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;font-size:.75rem;margin:.25rem 0 .6rem;">'
        '<b>Key:</b>'
        '<span style="background:#dbeafe;color:#1d4ed8;padding:.1rem .5rem;border-radius:12px;font-weight:700;">1</span> one occurrence &nbsp;'
        '<span style="background:#fee2e2;color:#b91c1c;padding:.1rem .5rem;border-radius:12px;font-weight:700;">2</span> more than one &nbsp;'
        '<span style="background:#f3f4f6;color:#9ca3af;padding:.1rem .5rem;border-radius:12px;font-weight:700;">X</span> evacuation &nbsp;'
        '</div>', unsafe_allow_html=True
    )

    # Grid tabs — one per behaviour
    if behaviours:
        beh_tabs = st.tabs([f"B{i+1}: {b[:40]}" for i, b in enumerate(behaviours)])
    else:
        beh_tabs = [st.container()]

    day_dates  = {DAYS[i]: (week_start + timedelta(days=i)).strftime("%-d/%m") for i in range(5)}
    today_day  = DAYS[date.today().weekday()] if date.today().weekday() < 5 else None

    for bi, btab in enumerate(beh_tabs):
        with btab:
            th = '<th class="lh">Time</th><th class="la">Activity</th>'
            for d in DAYS:
                is_td = (d == today_day and is_this)
                bg = 'background:#1a4d8a;' if is_td else ''
                th += f'<th style="{bg}">{d[:3]}<br><span style="font-weight:400;font-size:.62rem;">{day_dates[d]}</span></th>'
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
                        rows_html += f'<td class="{cls}">{disp}</td>'
                    else:
                        rows_html += '<td class="ce">·</td>'
                rows_html += "</tr>"
            st.markdown(
                f'<div class="grid-wrap"><table class="sg"><thead><tr>{th}</tr></thead>'
                f'<tbody>{rows_html}</tbody></table></div>',
                unsafe_allow_html=True
            )
            # Daily totals
            if not week_df.empty and "behaviour_index" in week_df.columns:
                bw = week_df[week_df["behaviour_index"]==bi]
                tc = st.columns(6); grand = 0
                for i, d in enumerate(DAYS):
                    n = bw[(bw["day_of_week"]==d) & (bw["value"].isin(["1","2"]))].shape[0]
                    grand += n
                    tc[i].markdown(f"<div class='kpi'><div class='val'>{n}</div><div class='lbl'>{d[:3]}</div></div>", unsafe_allow_html=True)
                tc[5].markdown(f"<div class='kpi kpi-a'><div class='val'>{grand}</div><div class='lbl'>Incidents</div></div>", unsafe_allow_html=True)

    # ── INTERACTIVE ENTRY PANEL ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("**➕ Tap a time slot and day to record**")

    slot_times     = [s["time"] for s in schedule]
    today_day_name = DAYS[date.today().weekday()] if date.today().weekday() < 5 else DAYS[0]

    # Initialise selected cell state
    if "sel_time" not in ss: ss.sel_time = slot_times[0] if slot_times else ""
    if "sel_day"  not in ss: ss.sel_day  = today_day_name
    if ss.sel_time not in slot_times and slot_times: ss.sel_time = slot_times[0]
    if ss.sel_day  not in DAYS: ss.sel_day = DAYS[0]

    # ── Time slot buttons (compact row) ──────────────────────────────────
    st.markdown('<div style="font-size:.72rem;font-weight:600;color:#64748b;margin-bottom:.2rem;">TIME SLOT</div>', unsafe_allow_html=True)
    # Show in rows of 8 to avoid wrapping issues
    chunk_size = 8
    for chunk_start in range(0, len(slot_times), chunk_size):
        chunk = slot_times[chunk_start:chunk_start+chunk_size]
        cols  = st.columns(len(chunk))
        for ci, t in enumerate(chunk):
            is_sel = (t == ss.sel_time)
            # Show if any data exists for this slot this week
            has_any = any(
                cell_data.get(bi,{}).get(t,{})
                for bi in range(len(behaviours) if behaviours else 1)
            )
            label = t
            style = ("primary" if is_sel else "secondary")
            if cols[ci].button(label, key=f"tsel_{t}", use_container_width=True, type=style):
                ss.sel_time = t
                st.rerun()

    st.markdown("")

    # ── Day buttons ───────────────────────────────────────────────────────
    st.markdown('<div style="font-size:.72rem;font-weight:600;color:#64748b;margin-bottom:.2rem;">DAY</div>', unsafe_allow_html=True)
    day_cols = st.columns(5)
    for di, d in enumerate(DAYS):
        is_sel  = (d == ss.sel_day)
        d_date  = week_start + timedelta(days=di)
        d_label = d[:3] + " " + d_date.strftime("%-d/%m")
        is_today = (d == today_day_name and is_this)
        style = ("primary" if is_sel else "secondary")
        extra = " ◉" if is_today and not is_sel else ""
        if day_cols[di].button(d_label + extra, key=f"dsel_{d}", use_container_width=True, type=style):
            ss.sel_day = d
            st.rerun()

    # ── Current selection context ─────────────────────────────────────────
    sel_time     = ss.sel_time
    sel_day      = ss.sel_day
    sel_activity = next((s["activity"] for s in schedule if s["time"]==sel_time), "")
    sel_date     = week_start + timedelta(days=DAYS.index(sel_day))

    st.markdown(
        f'<div style="background:#EBF4F9;border:1.5px solid #1A6B8A;border-radius:8px;'
        f'padding:.45rem 1rem;margin:.4rem 0 .6rem;font-size:.85rem;">'
        f'<b style="color:#1A6B8A;">Recording:</b> {sel_time}'
        + (f' — {sel_activity}' if sel_activity else '')
        + f' &nbsp;·&nbsp; <b>{sel_day}</b> {sel_date.strftime("%-d %b")}</div>',
        unsafe_allow_html=True
    )

    # ── Value buttons — one row per behaviour ─────────────────────────────
    val_styles = {
        "1": "background:#dbeafe;color:#1d4ed8;",
        "2": "background:#fee2e2;color:#b91c1c;",
        "X": "background:#f3f4f6;color:#6b7280;",
    }
    for bi, beh in enumerate(behaviours if behaviours else [""]):
        existing  = cell_data.get(bi,{}).get(sel_time,{}).get(sel_day)
        cur_val   = existing["value"] if existing else ""
        cur_grp   = existing.get("grouping","") if existing else ""
        cur_set   = existing.get("setting","")  if existing else ""
        cur_disp  = cur_val or "—"
        vstyle    = val_styles.get(cur_val,"color:#9ca3af;")
        ctx_hint  = ""
        if cur_val in ("1","2") and (cur_grp or cur_set):
            ctx_hint = " &nbsp;<span style='font-size:.7rem;color:#64748b;font-weight:400;'>"
            if cur_grp: ctx_hint += GROUPINGS.get(cur_grp, cur_grp)
            if cur_grp and cur_set: ctx_hint += " · "
            if cur_set: ctx_hint += cur_set
            ctx_hint += "</span>"
        cur_badge = (
            f'<span style="font-size:.75rem;font-weight:700;padding:.1rem .45rem;'
            f'border-radius:8px;{vstyle}">{cur_disp}</span>{ctx_hint}'
        )
        lbl = (f"B{bi+1}: {beh[:45]}" if beh else "Record")
        rc1, rc2, rc3, rc4, rc5 = st.columns([3.5, .85, .85, .85, .6])
        with rc1:
            st.markdown(
                f'<div style="padding:.5rem 0 .1rem;font-size:.84rem;font-weight:600;color:#334155;">'
                f'{lbl} &nbsp;{cur_badge}</div>',
                unsafe_allow_html=True
            )
        for col, val, key_sfx in [(rc2,"1","1"),(rc3,"2","2"),(rc4,"X","x")]:
            with col:
                disp = val
                if st.button(disp, key=f"vbtn_{bi}_{key_sfx}",
                             use_container_width=True,
                             type="primary" if val=="1" else "secondary"):
                    upsert_obs(student_name, sel_date, sel_day, sel_time,
                               sel_activity, val, bi, beh,
                               " | ".join(behaviours) if behaviours else beh,
                               ss.spt_period_id,
                               existing["id"] if existing else None)
                    st.rerun()
        with rc5:
            if cur_val:
                if st.button("✕", key=f"clr_{bi}", use_container_width=True, help="Clear"):
                    if existing:
                        delete_obs(existing["id"])
                        st.rerun()

        # ── Context buttons (activity / grouping / setting) ─────────────────
        # Shown only when a behaviour (1 or 2) is recorded for this cell
        if cur_val in ("1","2"):
            ctx_key_base = f"ctx_{bi}_{sel_time}_{sel_day}"
            cur_act_ctx  = existing.get("activity","") if existing else ""

            def _ctx_row(label, options, cur_selected, col_key_sfx, update_field, shorten=8):
                st.markdown(
                    f'<div style="font-size:.7rem;font-weight:600;color:#64748b;'
                    f'margin:.3rem 0 .15rem;">{label} '
                    f'<span style="font-weight:400;">(tap to record)</span></div>',
                    unsafe_allow_html=True
                )
                n = len(options)
                # Split into two rows if more than 7 options
                chunks = [options[:7], options[7:]] if n > 7 else [options]
                for chunk in chunks:
                    cols = st.columns(len(chunk))
                    for ci2, opt in enumerate(chunk):
                        opt_key  = opt if isinstance(opt, str) else opt[0]
                        opt_disp = opt if isinstance(opt, str) else opt[1]
                        is_sel   = (cur_selected == opt_key)
                        btn_lbl  = opt_disp[:shorten] if shorten else opt_disp
                        if cols[ci2].button(
                            btn_lbl, key=f"{ctx_key_base}_{col_key_sfx}_{ci2}",
                            use_container_width=True,
                            type="primary" if is_sel else "secondary",
                            help=opt_disp if shorten else None
                        ):
                            sb_c = get_sb()
                            if sb_c and existing:
                                try:
                                    new_val = "" if is_sel else opt_key
                                    sb_c.table("scatter_plot_observations").update(
                                        {update_field: new_val}
                                    ).eq("id", existing["id"]).execute()
                                    st.rerun()
                                except Exception:
                                    pass

            # ── Activity — compact dropdown ───────────────────────────────
            ACTIVITY_CTX = [
                "—",
                "Classroom", "Morning routine", "Preferred task",
                "Reading", "Writing", "Literacy", "Maths task", "Literacy task",
                "Independent task", "Using a digital device",
                "Break", "Playground", "Yard", "Recess",
                "Spill out room / space", "Cooking", "Other",
            ]
            act_idx = ACTIVITY_CTX.index(cur_act_ctx) if cur_act_ctx in ACTIVITY_CTX else 0
            st.markdown(
                '<div style="font-size:.7rem;font-weight:600;color:#64748b;margin:.3rem 0 .1rem;">'
                'ACTIVITY</div>', unsafe_allow_html=True
            )
            new_act = st.selectbox(
                "Activity", ACTIVITY_CTX, index=act_idx,
                key=f"{ctx_key_base}_act", label_visibility="collapsed"
            )
            if new_act != cur_act_ctx and new_act != "—":
                sb_act = get_sb()
                if sb_act and existing:
                    try:
                        sb_act.table("scatter_plot_observations").update(
                            {"activity": new_act}
                        ).eq("id", existing["id"]).execute()
                        st.rerun()
                    except Exception:
                        pass

            # ── Grouping and Setting side by side ─────────────────────────
            gc, sc = st.columns(2)
            with gc:
                grp_opts = [(k, v) for k, v in GROUPINGS.items()]
                _ctx_row("GROUPING", grp_opts, cur_grp, "g", "grouping", shorten=None)
            with sc:
                _ctx_row("SETTING", SETTINGS, cur_set, "s", "setting", shorten=9)

    # ════════════════════════════════════════════════════════════════════════
    # ENGAGEMENT GRID
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 🟢 Engagement Tracker")
    st.caption(
        "Record engagement level for each time slot. "
        "**E** = Engaged (no extra support)  &nbsp;·&nbsp; "
        "**P** = Partial (on task with support)  &nbsp;·&nbsp; "
        "**N** = Not engaged (off task)"
    )

    eng_df = load_week_eng(student_name, week_start, week_end)

    # Build engagement cell lookup: {time_slot: {day: {eng_level, support_type, id}}}
    eng_data = {}
    if not eng_df.empty:
        for _, row in eng_df.iterrows():
            t  = row.get("time_slot","")
            d  = row.get("day_of_week","")
            if not t or not d: continue
            if t not in eng_data: eng_data[t] = {}
            eng_data[t][d] = {
                "eng_level":    row.get("eng_level",""),
                "support_type": row.get("support_type","") or "—",
            }

    # ── Engagement HTML grid ──────────────────────────────────────────────
    eth = '<th class="lh">Time</th><th class="la">Activity</th>'
    for d in DAYS:
        is_td = (d == today_day and is_this)
        bg    = "background:#1a4d8a;" if is_td else ""
        eth  += (f'<th style="{bg}">{d[:3]}<br>'
                 f'<span style="font-weight:400;font-size:.62rem;">{day_dates[d]}</span></th>')

    eng_rows_html = ""
    for slot in schedule:
        t   = slot["time"]
        act = slot["activity"]
        eng_rows_html += f'<tr><td class="tl">{t}</td><td class="al">{act}</td>'
        for d in DAYS:
            cell = eng_data.get(t,{}).get(d)
            if cell:
                lv  = cell["eng_level"]
                sup = cell["support_type"]
                cfg = ENG_LEVELS.get(lv, {})
                bg  = cfg.get("bg","white")
                fg  = cfg.get("colour","#334155")
                # Show level + support abbreviation
                sup_short = sup.replace("1:1 ","").replace("Visual supports","VS")                               .replace("Sensory break","Snsr").replace("Modified task","Mod")                               .replace("Peer support","Peer").replace("Small group","SG")
                sup_html  = (f'<br><span style="font-size:.6rem;opacity:.75;">{sup_short}</span>'
                             if sup and sup != "—" else "")
                eng_rows_html += (f'<td style="background:{bg};color:{fg};font-weight:700;'
                                  f'text-align:center;vertical-align:middle;padding:.2rem .3rem;">'
                                  f'{lv}{sup_html}</td>')
            else:
                eng_rows_html += '<td class="ce">·</td>'
        eng_rows_html += "</tr>"

    st.markdown(
        f'<div class="grid-wrap"><table class="sg">'
        f'<thead><tr>{eth}</tr></thead><tbody>{eng_rows_html}</tbody></table></div>',
        unsafe_allow_html=True
    )

    # ── Engagement entry strip ────────────────────────────────────────────
    st.markdown("**Record engagement for the selected time slot and day:**")
    st.markdown(
        f'<div style="background:#f0fdf4;border:1.5px solid #16a34a;border-radius:8px;'
        f'padding:.4rem 1rem;margin:.3rem 0 .5rem;font-size:.85rem;">'
        f'<b style="color:#16a34a;">Recording:</b> {sel_time}'
        + (f' — {sel_activity}' if sel_activity else '')
        + f' &nbsp;·&nbsp; <b>{sel_day}</b> {sel_date.strftime("%-d %b")}'
        + '</div>',
        unsafe_allow_html=True
    )

    cur_eng  = eng_data.get(sel_time,{}).get(sel_day,{}).get("eng_level","")
    cur_sup  = eng_data.get(sel_time,{}).get(sel_day,{}).get("support_type","—")

    # E / P / N buttons
    eng_cols = st.columns([3, 1, 1, 1, 0.7])
    with eng_cols[0]:
        st.markdown(
            '<div style="padding:.55rem 0 .1rem;font-size:.84rem;font-weight:600;color:#334155;">'
            'Engagement level</div>',
            unsafe_allow_html=True
        )
    for ci, (lv, cfg) in enumerate(ENG_LEVELS.items()):
        with eng_cols[ci+1]:
            is_sel = (cur_eng == lv)
            st.markdown("<div style='padding-top:1.75rem;'>", unsafe_allow_html=True)
            if st.button(
                lv, key=f"eng_{lv}_{sel_time}_{sel_day}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
                help=cfg["desc"]
            ):
                if is_sel:
                    # Deselect = clear
                    delete_eng(student_name, sel_date, sel_time)
                else:
                    upsert_eng(student_name, sel_date, sel_day, sel_time, lv,
                               cur_sup if cur_sup != "—" else "—")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    with eng_cols[4]:
        if cur_eng:
            st.markdown("<div style='padding-top:1.75rem;'>", unsafe_allow_html=True)
            if st.button("✕", key=f"eng_clr_{sel_time}_{sel_day}",
                         use_container_width=True, help="Clear engagement"):
                delete_eng(student_name, sel_date, sel_time)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Support type — only when E or P recorded
    if cur_eng in ("E","P"):
        sup_idx = ENG_SUPPORT.index(cur_sup) if cur_sup in ENG_SUPPORT else 0
        new_sup = st.selectbox(
            "Support type", ENG_SUPPORT, index=sup_idx,
            key=f"sup_sel_{sel_time}_{sel_day}",
            help="What support enabled or maintained engagement?"
        )
        if new_sup != cur_sup:
            upsert_eng(student_name, sel_date, sel_day, sel_time, cur_eng, new_sup)
            st.rerun()

    # ── End-of-day support type ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("**📋 Daily support type** *(optional — record once per day)*")
    SUPPORT_TYPES = [
        "—", "1:1 SSO", "1:1 Teacher", "Small group", "Whole group", "Independent / no additional support"
    ]
    sup_day   = ss.sel_day
    sup_date  = week_start + timedelta(days=DAYS.index(sup_day))

    # Load existing support record for this day
    sb_sup = get_sb()
    existing_sup = None
    if sb_sup:
        try:
            sup_res = (sb_sup.table("scatter_daily_support")
                       .select("*")
                       .eq("student_name", student_name)
                       .eq("obs_date", str(sup_date))
                       .limit(1).execute())
            if sup_res.data:
                existing_sup = sup_res.data[0]
        except Exception:
            pass

    cur_sup = existing_sup["support_type"] if existing_sup else "—"
    sup_idx = SUPPORT_TYPES.index(cur_sup) if cur_sup in SUPPORT_TYPES else 0

    sup_c1, sup_c2 = st.columns([3, 2])
    with sup_c1:
        new_sup = st.selectbox(
            f"Support on {sup_day} {sup_date.strftime('%-d %b')}",
            SUPPORT_TYPES, index=sup_idx, key=f"sup_{sup_day}"
        )
    with sup_c2:
        notes_val = existing_sup["notes"] if existing_sup else ""
        sup_notes = st.text_input("Notes (optional)", value=notes_val,
                                  key=f"sup_notes_{sup_day}", placeholder="e.g. Sarah covered 2nd half")
    if new_sup != cur_sup or sup_notes != (existing_sup["notes"] if existing_sup else ""):
        if new_sup != "—" or sup_notes.strip():
            if sb_sup:
                try:
                    if existing_sup:
                        sb_sup.table("scatter_daily_support").update(
                            {"support_type": new_sup, "notes": sup_notes}
                        ).eq("id", existing_sup["id"]).execute()
                    else:
                        sb_sup.table("scatter_daily_support").insert({
                            "student_name": student_name,
                            "obs_date":     str(sup_date),
                            "support_type": new_sup,
                            "notes":        sup_notes,
                        }).execute()
                except Exception:
                    pass

    # Remove entry expander
    with st.expander("🗑️ Remove an entry from this week"):
        entries = []
        if not week_df.empty:
            for _, row in week_df.iterrows():
                bi  = int(row.get("behaviour_index",0) or 0)
                beh = behaviours[bi] if bi < len(behaviours) else row.get("behaviour_label","?")
                val = row.get("value","")
                disp = val
                entries.append({
                    "label": f"B{bi+1} · {row['day_of_week']} {row['time_slot']} — {disp}  ({beh[:25]})",
                    "id":    row["id"],
                })
        if not entries:
            st.caption("No entries this week.")
        else:
            dc1, dc2 = st.columns([4,1])
            with dc1:
                chosen = st.selectbox("Select entry", [e["label"] for e in entries], key="del_sel")
            with dc2:
                st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
                if st.button("Remove", key="del_btn", use_container_width=True):
                    oid = next(e["id"] for e in entries if e["label"]==chosen)
                    if delete_obs(oid): st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # Manage schedule
    # Show any schedule generation message
    _sched_msg = ss.pop("_sched_msg", None) if "_sched_msg" in ss else None
    if _sched_msg:
        st.success(_sched_msg)

    # Always show current schedule as a compact preview
    _preview_sched = ss.spt_schedule or []
    if _preview_sched:
        _slots_text = "  ·  ".join(
            f"{s['time']} {('— '+s['activity'][:18]) if s.get('activity') else ''}"
            for s in _preview_sched[:8]
        ) + (" ···" if len(_preview_sched) > 8 else "")
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
            f'padding:.35rem .75rem;margin-bottom:.3rem;font-size:.72rem;color:#64748b;">'
            f'<b style="color:#1A6B8A;">Schedule ({len(_preview_sched)} slots):</b> {_slots_text}'
            f'</div>',
            unsafe_allow_html=True
        )

    _sched_open = ss.get("_sched_expander_open", False)
    with st.expander("⚙️ Manage Schedule — edit, reorder, or generate", expanded=_sched_open):
        ss["_sched_expander_open"] = True
        st.caption("Schedule is saved per student. Changes apply immediately.")
        sched = ss.spt_schedule

        # ── ACTIVITY SUGGESTIONS LIST ─────────────────────────────────────
        ACTIVITY_SUGGESTIONS = [
            "Classroom", "Morning routine", "Preferred task",
            "Reading", "Writing", "Literacy", "Maths task", "Literacy task",
            "Independent task", "Using a digital device",
            "Break", "Playground", "Yard", "Recess",
            "Spill out room / space", "Cooking", "Other",
            "De-escalation activity", "Interoception", "Breakfast", "Fitness",
            "Quiet Time", "Lunch eating", "Lunch", "I.C.T.", "Home",
        ]

        # ── EXISTING SLOTS ────────────────────────────────────────────────
        # Header row
        h1,h2,h3 = st.columns([1.5,3,1.65])
        with h1: st.caption("**Time**")
        with h2: st.caption("**Activity**")
        with h3: st.caption("**Reorder / Remove**")

        changed = False
        for i, slot in enumerate(sched):
            sc1, sc2, sc3, sc4, sc5 = st.columns([1.5, 3, .55, .55, .55])
            with sc1:
                nt = st.text_input("T", slot["time"], key=f"st_{i}",
                                   label_visibility="collapsed")
            with sc2:
                # Selectbox with custom option for autofill + text fallback
                act_opts = ["— type below —"] + ACTIVITY_SUGGESTIONS
                cur_act  = slot["activity"]
                sel_idx  = (ACTIVITY_SUGGESTIONS.index(cur_act) + 1
                            if cur_act in ACTIVITY_SUGGESTIONS else 0)
                sel_act  = st.selectbox("A", act_opts, index=sel_idx,
                                        key=f"ssel_{i}", label_visibility="collapsed")
                if sel_act == "— type below —":
                    na = st.text_input("Custom activity", value=cur_act,
                                       key=f"sa_{i}", label_visibility="collapsed",
                                       placeholder="Type activity name...")
                else:
                    na = sel_act
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
                ss.spt_schedule = sched
                save_schedule_by_name(student_name, sched)
                st.rerun()

        st.markdown("---")

        # ── ADD SINGLE SLOT ───────────────────────────────────────────────
        st.markdown("**Add a single slot:**")
        nc1, nc2, nc3 = st.columns([1.5, 3, 1])
        with nc1:
            new_t = st.text_input("Time", placeholder="e.g. 8:45", key="sched_nt")
        with nc2:
            add_act_opts  = ["— type below —"] + ACTIVITY_SUGGESTIONS
            add_act_sel   = st.selectbox("Activity", add_act_opts, key="sched_na_sel")
            if add_act_sel == "— type below —":
                new_a = st.text_input("Custom", placeholder="Activity name",
                                      key="sched_na", label_visibility="collapsed")
            else:
                new_a = add_act_sel
        with nc3:
            st.markdown("<div style='padding-top:1.8rem;'>", unsafe_allow_html=True)
            if st.button("Add slot", key="sched_add", use_container_width=True):
                if new_t.strip():
                    sched.append({"time": new_t.strip(), "activity": new_a.strip()})
                    ss.spt_schedule = sched
                    save_schedule_by_name(student_name, sched)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # ── TIMELINE GENERATOR ────────────────────────────────────────────
        st.markdown("**⚡ Generate a timeline automatically:**")
        st.caption("Enter start time, end time and interval — slots will be created for you.")

        tg1, tg2, tg3, tg4 = st.columns([1.5, 1.5, 1.5, 2])
        with tg1:
            tg_start = st.text_input("Start time", value="9:00",
                                     placeholder="e.g. 9:00", key="tg_start")
        with tg2:
            tg_end   = st.text_input("End time",   value="15:00",
                                     placeholder="e.g. 15:00", key="tg_end")
        with tg3:
            tg_freq  = st.selectbox("Interval", [5,10,15,20,30,45,60],
                                    index=2, key="tg_freq",
                                    format_func=lambda x: f"{x} min")
        with tg4:
            tg_act_opts = ["— type below —"] + ACTIVITY_SUGGESTIONS
            tg_act_sel  = st.selectbox("Default activity (optional)",
                                       tg_act_opts, key="tg_act_sel")
            if tg_act_sel == "— type below —":
                tg_act = st.text_input("Custom default activity",
                                       placeholder="Leave blank for none",
                                       key="tg_act_custom",
                                       label_visibility="collapsed")
            else:
                tg_act = tg_act_sel

        tg_replace = st.checkbox(
            "Replace entire schedule with generated timeline",
            value=False, key="tg_replace",
            help="Unchecked = adds slots to existing schedule"
        )

        if st.button("⚡ Generate Timeline", key="tg_generate", type="primary"):
            def _parse_time(ts):
                ts = ts.strip()
                try:
                    h, m = ts.split(":")
                    return int(h)*60 + int(m)
                except Exception:
                    return None

            start_m = _parse_time(tg_start)
            end_m   = _parse_time(tg_end)

            if start_m is None or end_m is None:
                st.error("Please enter valid times in HH:MM format (e.g. 9:00, 14:30).")
            elif end_m <= start_m:
                st.error("End time must be after start time.")
            elif tg_freq <= 0:
                st.error("Interval must be greater than 0.")
            else:
                new_slots = []
                t = start_m
                while t <= end_m:
                    h = t // 60
                    m = t % 60
                    time_str = f"{h}:{m:02d}"
                    new_slots.append({"time": time_str, "activity": tg_act.strip()})
                    t += tg_freq

                if tg_replace:
                    sched = new_slots
                else:
                    # Merge — add slots that don't already exist
                    existing_times = {s["time"] for s in sched}
                    for ns in new_slots:
                        if ns["time"] not in existing_times:
                            sched.append(ns)
                    # Sort by time
                    def _slot_sort(s):
                        try:
                            h, m = s["time"].split(":")
                            return int(h)*60+int(m)
                        except Exception:
                            return 999
                    sched = sorted(sched, key=_slot_sort)

                ss.spt_schedule = sched
                save_schedule_by_name(student_name, sched)
                count = len(new_slots)
                ss["_sched_msg"] = (
                    "✅ Generated " + str(count) + " slots "
                    "(" + tg_start + " – " + tg_end + ", every " + str(tg_freq) + " min). "
                    + ("Schedule replaced." if tg_replace else "Merged with existing.")
                )
                ss["_sched_expander_open"] = True
                st.rerun()

        st.markdown("---")
        if st.button("↺ Reset to default schedule", key="sched_reset"):
            ss.spt_schedule = DEFAULT_SCHEDULE.copy()
            save_schedule_by_name(student_name, DEFAULT_SCHEDULE.copy())
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS & DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════
with t_analysis:
    st.markdown(f"#### {student_name} — Scatter Plot Analysis")

    all_obs = load_all_obs(student_name)
    if all_obs.empty:
        st.info("No observations recorded yet."); st.stop()

    # ── Date range with week labels ───────────────────────────────────────
    min_date = all_obs["obs_date_dt"].min().date()
    max_date = all_obs["obs_date_dt"].max().date()

    # Build list of weeks that have data
    week_starts_with_data = sorted(set(
        (d - timedelta(days=d.weekday()))
        for d in pd.date_range(min_date, max_date).date
    ))

    an_c1, an_c2, an_c3 = st.columns([2, 2, 3])
    with an_c1:
        date_from = st.date_input("From", value=min_date, key="af")
    with an_c2:
        date_to   = st.date_input("To",   value=max_date, key="at")
    with an_c3:
        # Week selector shortcut
        week_opts = {ws: f"Week of {ws.strftime('%-d %b %Y')} – {(ws+timedelta(days=4)).strftime('%-d %b')}"
                     for ws in week_starts_with_data}
        if week_opts:
            sel_week = st.selectbox("Jump to week", ["All data"] + list(week_opts.keys()),
                                    format_func=lambda x: week_opts[x] if x != "All data" else "All data",
                                    key="an_week_sel")
            if sel_week != "All data":
                date_from = sel_week
                date_to   = sel_week + timedelta(days=4)

    filt = all_obs[
        (all_obs["obs_date_dt"].dt.date >= date_from) &
        (all_obs["obs_date_dt"].dt.date <= date_to)
    ].copy()

    if filt.empty:
        st.info("No observations in this range."); st.stop()

    inc_filt  = filt[filt["value"].isin(["1","2"])].copy()
    n1   = int((filt["value"]=="1").sum())
    n2   = int((filt["value"]=="2").sum())

    k1,k2,k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><div class='val'>{n1+n2}</div><div class='lbl'>Incident intervals</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='val'>{n1}</div><div class='lbl'>Single (1)</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n2}</div><div class='lbl'>Multiple (2)</div></div>", unsafe_allow_html=True)

    if inc_filt.empty:
        st.success("🎉 No incidents in this period."); st.stop()

    # Build time label map
    time_labels = {s["time"]: s["time"] + "  " + s["activity"] for s in schedule}
    def _sort_t(t):
        try: h,m=str(t).split(":"); return int(h)*60+int(m)
        except: return 999

    # Per-behaviour tabs + combined
    beh_list = behaviours if behaviours else ["All"]
    an_tabs  = st.tabs([f"B{i+1}: {b[:35]}" for i,b in enumerate(beh_list)] + ["Combined"])

    for bi, abtab in enumerate(an_tabs[:-1]):
        with abtab:
            b_inc = inc_filt[inc_filt["behaviour_index"]==bi].copy() \
                if "behaviour_index" in inc_filt.columns else inc_filt.copy()
            if b_inc.empty:
                st.info("No incidents for this behaviour."); continue

            b_inc["date_str"]   = b_inc["obs_date_dt"].dt.strftime("%a %-d %b")
            b_inc["date_order"] = b_inc["obs_date_dt"].dt.date
            b_inc["time_label"] = b_inc["time_slot"].map(time_labels).fillna(b_inc["time_slot"])
            b_inc["hover"]      = (b_inc["date_str"] + "<br>" + b_inc["time_label"] + "<br>" +
                                   b_inc["value"].map({"1":"Single","2":"Multiple"}).fillna(b_inc["value"]) +
                                   "<br>" + b_inc["day_of_week"])

            all_slots     = sorted(b_inc["time_slot"].unique(), key=_sort_t)
            ordered_lbl   = [time_labels.get(t,t) for t in all_slots]
            date_order    = sorted(b_inc["date_str"].unique(),
                                   key=lambda s: b_inc.loc[b_inc["date_str"]==s,"date_order"].min())

            fig = go.Figure()
            for val, sz, col, name in [("1",16,"#3b82f6","1 — single"),("2",26,"#ef4444","2 — multiple")]:
                sub = b_inc[b_inc["value"]==val]
                if sub.empty: continue
                fig.add_trace(go.Scatter(
                    x=sub["date_str"], y=sub["time_label"], mode="markers", name=name,
                    marker=dict(size=sz, color=col, opacity=.85, line=dict(color="white",width=1.5)),
                    hovertemplate="%{customdata}<extra></extra>", customdata=sub["hover"],
                ))
            fig.update_layout(
                title=beh_list[bi] if bi < len(beh_list) else "Scatter Plot",
                height=max(400,len(ordered_lbl)*28+120),
                xaxis=dict(categoryorder="array",categoryarray=date_order,
                           showgrid=True,gridcolor="#e2e8f0",side="top",tickfont=dict(size=11)),
                yaxis=dict(categoryorder="array",categoryarray=ordered_lbl[::-1],
                           showgrid=True,gridcolor="#e2e8f0",automargin=True,tickfont=dict(size=11)),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0),
                margin=dict(l=10,r=20,t=80,b=20), hovermode="closest",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("● Small blue = single (1)  ·  ● Large red = multiple (2)  ·  Dates along top, times top to bottom")

            col_a, col_b = st.columns(2)
            with col_a:
                daily = b_inc.groupby(b_inc["obs_date_dt"].dt.date).size().reset_index(name="n")
                daily["ds"] = pd.to_datetime(daily["obs_date_dt"]).dt.strftime("%-d %b")
                fig2 = go.Figure(go.Bar(x=daily["ds"],y=daily["n"],
                    marker_color=[AMBER if v>=3 else TEAL for v in daily["n"]],
                    text=daily["n"],textposition="outside"))
                fig2.update_layout(title="Per day",height=240,showlegend=False,
                    plot_bgcolor="#f8fafc",paper_bgcolor="white",
                    yaxis=dict(tickformat="d",gridcolor="#e2e8f0"),margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig2, use_container_width=True)
            with col_b:
                dow = b_inc.groupby("day_of_week").size().reindex(DAYS,fill_value=0)
                fig3 = go.Figure(go.Bar(x=dow.index,y=dow.values,marker_color=TEAL,
                    text=dow.values,textposition="outside"))
                fig3.update_layout(title="By day of week",height=240,showlegend=False,
                    plot_bgcolor="#f8fafc",paper_bgcolor="white",
                    yaxis=dict(tickformat="d",gridcolor="#e2e8f0"),margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig3, use_container_width=True)

    # ── Engagement analysis ──────────────────────────────────────────────
    all_eng = load_all_eng(student_name)
    if not all_eng.empty:
        eng_filt = all_eng[
            (all_eng["obs_date_dt"].dt.date >= date_from) &
            (all_eng["obs_date_dt"].dt.date <= date_to)
        ].copy()
        if not eng_filt.empty:
            st.markdown("---")
            st.markdown("### 🟢 Engagement Analysis")

            # KPIs
            n_e = int((eng_filt["eng_level"]=="E").sum())
            n_p = int((eng_filt["eng_level"]=="P").sum())
            n_n = int((eng_filt["eng_level"]=="N").sum())
            n_total = len(eng_filt)
            ek1,ek2,ek3,ek4 = st.columns(4)
            ek1.markdown(f"<div class='kpi'><div class='val'>{n_total}</div><div class='lbl'>Intervals recorded</div></div>", unsafe_allow_html=True)
            ek2.markdown(f"<div class='kpi kpi-g'><div class='val'>{n_e}</div><div class='lbl'>Engaged (E)</div></div>", unsafe_allow_html=True)
            ek3.markdown(f"<div class='kpi kpi-a'><div class='val'>{n_p}</div><div class='lbl'>Partial (P)</div></div>", unsafe_allow_html=True)
            ek4.markdown(f"<div class='kpi'><div class='val'>{n_n}</div><div class='lbl'>Not engaged (N)</div></div>", unsafe_allow_html=True)

            ec1, ec2 = st.columns(2)
            with ec1:
                # Engagement breakdown pie
                eng_filt["Level"] = eng_filt["eng_level"].map(
                    {k: v["label"] for k,v in ENG_LEVELS.items()}
                ).fillna(eng_filt["eng_level"])
                pie_df = eng_filt["Level"].value_counts().reset_index()
                pie_df.columns = ["Level","Count"]
                fig_pie = px.pie(
                    pie_df, values="Count", names="Level",
                    color="Level",
                    color_discrete_map={
                        "Engaged":"#16a34a",
                        "Partial":"#d97706",
                        "Not engaged":"#dc2626",
                    },
                    title="Engagement Breakdown", hole=0.4,
                )
                fig_pie.update_layout(height=290, margin=dict(l=10,r=10,t=50,b=10))
                st.plotly_chart(fig_pie, use_container_width=True)

            with ec2:
                # Engagement by time slot
                slot_eng = eng_filt.groupby(["time_slot","eng_level"]).size().reset_index(name="Count")
                slot_eng["sort_k"] = slot_eng["time_slot"].apply(
                    lambda t: int(str(t).split(":")[0])*60+int(str(t).split(":")[1]) if ":"in str(t) else 999
                )
                slot_eng["label_map"] = slot_eng["eng_level"].map(
                    {k: v["label"] for k,v in ENG_LEVELS.items()}
                )
                fig_slot = px.bar(
                    slot_eng.sort_values("sort_k"), x="Count", y="time_slot",
                    orientation="h", color="label_map",
                    color_discrete_map={
                        "Engaged":"#16a34a","Partial":"#d97706","Not engaged":"#dc2626"
                    },
                    title="Engagement by Time Slot",
                    labels={"time_slot":"","Count":"Intervals","label_map":"Level"},
                    barmode="stack",
                )
                fig_slot.update_layout(
                    height=max(280,len(slot_eng["time_slot"].unique())*22),
                    coloraxis_showscale=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    margin=dict(l=10,r=10,t=50,b=10),
                    xaxis=dict(tickformat="d"),
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig_slot, use_container_width=True)

            # Support type effectiveness
            sup_data_eng = eng_filt[eng_filt["support_type"].notna() & (eng_filt["support_type"] != "—")]
            if not sup_data_eng.empty:
                sup_data_eng = sup_data_eng.copy()
                sup_data_eng["Level"] = sup_data_eng["eng_level"].map(
                    {k: v["label"] for k,v in ENG_LEVELS.items()}
                )
                sup_grp = sup_data_eng.groupby(["support_type","Level"]).size().reset_index(name="Count")
                fig_sup = px.bar(
                    sup_grp, x="Count", y="support_type", orientation="h",
                    color="Level",
                    color_discrete_map={
                        "Engaged":"#16a34a","Partial":"#d97706","Not engaged":"#dc2626"
                    },
                    title="Engagement by Support Type",
                    labels={"support_type":"","Count":"Intervals","Level":"Engagement"},
                    barmode="stack",
                )
                fig_sup.update_layout(
                    height=max(240,len(sup_grp["support_type"].unique())*32),
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    margin=dict(l=10,r=10,t=50,b=10),
                    xaxis=dict(tickformat="d"),
                )
                st.plotly_chart(fig_sup, use_container_width=True)
                st.caption("💡 This chart shows which support types are associated with engaged vs partial vs not-engaged intervals.")

    # ── Grouping and Setting charts (shown when context data exists) ─────
    all_with_ctx = inc_filt[
        (inc_filt.get("grouping", pd.Series(dtype=str)).fillna("") != "") |
        (inc_filt.get("setting",  pd.Series(dtype=str)).fillna("") != "")
    ] if ("grouping" in inc_filt.columns or "setting" in inc_filt.columns) else pd.DataFrame()

    if not all_with_ctx.empty:
        st.markdown("---")
        st.markdown("### 🔍 Context Analysis — Grouping & Setting")
        ctx_c1, ctx_c2 = st.columns(2)

        with ctx_c1:
            grp_data = all_with_ctx[all_with_ctx.get("grouping","").fillna("") != ""]                 if "grouping" in all_with_ctx.columns else pd.DataFrame()
            if not grp_data.empty:
                grp_counts = grp_data["grouping"].map(
                    lambda x: GROUPINGS.get(x, x)
                ).value_counts().reset_index()
                grp_counts.columns = ["Grouping","Count"]
                fig_grp = px.bar(
                    grp_counts, x="Count", y="Grouping", orientation="h",
                    color="Count", color_continuous_scale=["#90CBE3", TEAL],
                    title="Incidents by Grouping",
                    labels={"Count":"Incident intervals","Grouping":""}
                )
                fig_grp.update_layout(
                    height=280, coloraxis_showscale=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    margin=dict(l=10,r=10,t=45,b=10),
                    xaxis=dict(tickformat="d")
                )
                st.plotly_chart(fig_grp, use_container_width=True)
            else:
                st.info("No grouping data recorded yet. Tap a grouping button after recording 1 or 2.")

        with ctx_c2:
            set_data = all_with_ctx[all_with_ctx.get("setting","").fillna("") != ""]                 if "setting" in all_with_ctx.columns else pd.DataFrame()
            if not set_data.empty:
                set_counts = set_data["setting"].value_counts().reset_index()
                set_counts.columns = ["Setting","Count"]
                fig_set = px.bar(
                    set_counts, x="Count", y="Setting", orientation="h",
                    color="Count", color_continuous_scale=["#90CBE3", AMBER],
                    title="Incidents by Setting",
                    labels={"Count":"Incident intervals","Setting":""}
                )
                fig_set.update_layout(
                    height=280, coloraxis_showscale=False,
                    plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    margin=dict(l=10,r=10,t=45,b=10),
                    xaxis=dict(tickformat="d")
                )
                st.plotly_chart(fig_set, use_container_width=True)
            else:
                st.info("No setting data recorded yet. Tap a setting button after recording 1 or 2.")

    with an_tabs[-1]:
        if inc_filt.empty:
            st.info("No incidents."); st.stop()
        inc2 = inc_filt.copy()
        inc2["Behaviour"] = inc2.get("behaviour_index",pd.Series(dtype=object)).apply(
            lambda i: f"B{int(i)+1}: {beh_list[int(i)][:30]}" if pd.notna(i) and int(i)<len(beh_list) else "B1"
        ) if "behaviour_index" in inc2.columns else "All"
        inc2["date_str"]   = inc2["obs_date_dt"].dt.strftime("%a %-d %b")
        inc2["date_order"] = inc2["obs_date_dt"].dt.date
        inc2["time_label"] = inc2["time_slot"].map(time_labels).fillna(inc2["time_slot"])
        date_order_c = sorted(inc2["date_str"].unique(),
                              key=lambda s: inc2.loc[inc2["date_str"]==s,"date_order"].min())
        all_lbl_c    = sorted(inc2["time_label"].unique(), key=lambda l: _sort_t(l.split()[0] if l else "0"))
        fig_c = go.Figure()
        colours = ["#3b82f6","#ef4444","#f59e0b"]
        for idx, bname in enumerate(inc2["Behaviour"].unique()):
            sub = inc2[inc2["Behaviour"]==bname]
            for val, sz in [("1",16),("2",26)]:
                s = sub[sub["value"]==val]
                if s.empty: continue
                fig_c.add_trace(go.Scatter(
                    x=s["date_str"], y=s["time_label"], mode="markers",
                    name=f"{bname} ({'single' if val=='1' else 'multiple'})",
                    marker=dict(size=sz, color=colours[idx%3], opacity=.75,
                                line=dict(color="white",width=1.5),
                                symbol="circle" if val=="1" else "circle-open"),
                ))
        fig_c.update_layout(
            title="Combined — All Behaviours",
            height=max(400,len(all_lbl_c)*28+120),
            xaxis=dict(categoryorder="array",categoryarray=date_order_c,showgrid=True,gridcolor="#e2e8f0",side="top"),
            yaxis=dict(categoryorder="array",categoryarray=all_lbl_c[::-1],showgrid=True,gridcolor="#e2e8f0",automargin=True),
            plot_bgcolor="white",paper_bgcolor="white",
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0),
            margin=dict(l=10,r=20,t=80,b=20),hovermode="closest",
        )
        st.plotly_chart(fig_c, use_container_width=True)

    st.markdown("---")

    # ── SUPPORT TYPE SUMMARY ──────────────────────────────────────────────
    sb_sup2 = get_sb()
    sup_data = []
    if sb_sup2:
        try:
            sup_res2 = (sb_sup2.table("scatter_daily_support")
                        .select("*")
                        .eq("student_name", student_name)
                        .gte("obs_date", str(date_from))
                        .lte("obs_date", str(date_to))
                        .order("obs_date")
                        .execute())
            sup_data = sup_res2.data or []
        except Exception:
            pass
    if sup_data:
        st.markdown("**Support type recorded:**")
        sup_df = pd.DataFrame(sup_data)
        sup_df["obs_date"] = pd.to_datetime(sup_df["obs_date"]).dt.strftime("%-d %b %Y")
        sup_df = sup_df[["obs_date","support_type","notes"]].rename(
            columns={"obs_date":"Date","support_type":"Support Type","notes":"Notes"})
        st.dataframe(sup_df, use_container_width=True, hide_index=True)
        st.markdown("---")

    # ── DOWNLOADS ─────────────────────────────────────────────────────────
    dl = filt.copy()
    dl["obs_date"] = dl["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    dl["value_desc"] = dl["value"].map({"1":"Single","2":"Multiple","X":"Evacuation"})
    csv = dl[["obs_date","day_of_week","time_slot","activity","value","value_desc",
              "behaviour_label","target_behaviours","created_by"]].to_csv(index=False)

    # Build formatted HTML report
    prog_type = ss.get("spt_prog_type","")
    behs_str  = "  ·  ".join([f"B{i+1}: {b}" for i,b in enumerate(behaviours)]) if behaviours else "—"
    period_lbl = ""
    if ss.spt_period_id:
        try:
            pr_res = get_sb().table("scatter_tracking_periods").select("label,start_date,end_date")                .eq("id", ss.spt_period_id).limit(1).execute()
            if pr_res.data:
                p = pr_res.data[0]
                period_lbl = p.get("label") or ""
                sd = pd.to_datetime(p["start_date"]).strftime("%-d %b %Y")
                ed = pd.to_datetime(p["end_date"]).strftime("%-d %b %Y") if p.get("end_date") else "ongoing"
                period_lbl = (period_lbl + " " if period_lbl else "") + f"({sd} – {ed})"
        except Exception:
            pass

    inc_rows = filt[filt["value"].isin(["1","2"])].copy()
    # Build grid table for report
    all_dates_sorted = sorted(filt["obs_date_dt"].dt.date.unique())
    date_labels = {d: pd.Timestamp(d).strftime("%a %-d %b") for d in all_dates_sorted}

    def build_grid_html(behaviour_idx):
        b_obs = filt[filt.get("behaviour_index", pd.Series(dtype=object)) == behaviour_idx]             if "behaviour_index" in filt.columns else filt
        cell_lookup = {}
        for _, row in b_obs.iterrows():
            cell_lookup[(row["time_slot"], row.get("day_of_week",""))] = row["value"]

        ths = "".join(f"<th style='background:#1A6B8A;color:white;padding:4px 8px;font-size:11px;'>{date_labels.get(d,str(d))}</th>"
                      for d in all_dates_sorted)
        rows_html = ""
        for slot in schedule:
            t = slot["time"]; act = slot["activity"]
            tds = ""
            for d in all_dates_sorted:
                day_name = pd.Timestamp(d).strftime("%A")
                v = cell_lookup.get((t, day_name), "")
                bg = {"1":"#dbeafe","2":"#fee2e2","X":"#f3f4f6"}.get(v,"white")
                fg = {"1":"#1d4ed8","2":"#b91c1c","X":"#6b7280"}.get(v,"#ccc")
                disp = v or "·"
                tds += f"<td style='background:{bg};color:{fg};text-align:center;padding:3px 5px;font-size:11px;font-weight:700;border:1px solid #e2e8f0;'>{disp}</td>"
            rows_html += (f"<tr><td style='padding:3px 8px;font-size:11px;font-weight:600;white-space:nowrap;border:1px solid #e2e8f0;'>{t}</td>"
                          f"<td style='padding:3px 8px;font-size:11px;color:#64748b;border:1px solid #e2e8f0;'>{act}</td>{tds}</tr>")
        return f"<table style='border-collapse:collapse;width:100%;margin-top:8px;'><thead><tr><th style='background:#1A6B8A;color:white;padding:4px 8px;font-size:11px;'>Time</th><th style='background:#1A6B8A;color:white;padding:4px 8px;font-size:11px;'>Activity</th>{ths}</tr></thead><tbody>{rows_html}</tbody></table>"

    grids_html = ""
    for bi, beh in enumerate(behaviours if behaviours else ["All observations"]):
        grids_html += f"<h3 style='color:#1A6B8A;margin:20px 0 6px;font-size:14px;'>Behaviour {bi+1}: {beh}</h3>"
        grids_html += build_grid_html(bi)

    sup_table = ""
    if sup_data:
        sup_rows = "".join(
            f"<tr><td style='padding:4px 8px;border:1px solid #e2e8f0;'>{r.get('obs_date','')}</td>"
            f"<td style='padding:4px 8px;border:1px solid #e2e8f0;font-weight:600;'>{r.get('support_type','—')}</td>"
            f"<td style='padding:4px 8px;border:1px solid #e2e8f0;color:#64748b;'>{r.get('notes','')}</td></tr>"
            for r in sup_data
        )
        sup_table = (
            "<h3 style='color:#1A6B8A;margin:20px 0 6px;font-size:14px;'>Support Type by Day</h3>"
            "<table style='border-collapse:collapse;width:100%;'>"
            "<thead><tr>"
            "<th style='background:#1A6B8A;color:white;padding:4px 8px;font-size:11px;'>Date</th>"
            "<th style='background:#1A6B8A;color:white;padding:4px 8px;font-size:11px;'>Support Type</th>"
            "<th style='background:#1A6B8A;color:white;padding:4px 8px;font-size:11px;'>Notes</th>"
            f"</tr></thead><tbody>{sup_rows}</tbody></table>"
        )

    html_report = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Scatter Plot Tracker — {student_name}</title>
<style>
@page {{ size: A4 landscape; margin: 12mm; }}
body {{ font-family: Arial, sans-serif; color: #1a2e44; margin: 0; padding: 16px; }}
@media print {{ body {{ padding: 0; }} .no-print {{ display:none; }} }}
</style></head><body>
<div style="background:linear-gradient(135deg,#1A6B8A,#1A6B8ABB);color:white;padding:16px 20px;border-radius:8px;margin-bottom:16px;">
  <div style="font-size:20px;font-weight:700;margin-bottom:4px;">📊 Scatter Plot Tracker</div>
  <div style="font-size:12px;opacity:.85;">Cowandilla Learning Centre · Learning &amp; Behaviour Unit</div>
</div>
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:12px;">
  <b>About this tool:</b> The Scatter Plot Tracker records the frequency of targeted behaviours across each time slot of the school day.
  Each cell shows whether the behaviour occurred once (1), more than once (2), was not observed (✓), or could not be observed (X).
  Patterns across time slots and days reveal when a student is most at risk and inform proactive scheduling decisions.
</div>
<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px;">
<tr><td style="padding:4px 12px 4px 0;"><b>Student:</b> {student_name}</td>
    <td style="padding:4px 12px 4px 0;"><b>Program:</b> {prog_type or "—"}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Behaviours:</b> {behs_str}</td>
    <td style="padding:4px 12px 4px 0;"><b>Period:</b> {period_lbl or "—"}</td></tr>
<tr><td style="padding:4px 12px 4px 0;"><b>Data range:</b> {date_from.strftime("%-d %b %Y") if hasattr(date_from,"strftime") else str(date_from)} – {date_to.strftime("%-d %b %Y") if hasattr(date_to,"strftime") else str(date_to)}</td>
    <td style="padding:4px 12px 4px 0;"><b>Total incidents:</b> {n1+n2} ({n1} single, {n2} multiple)</td></tr>
</table>
<div class="no-print" style="margin-bottom:12px;">
  <button onclick="window.print()" style="background:#1A6B8A;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;">🖨️ Print / Save as PDF</button>
</div>
{grids_html}
{sup_table}
<div style="margin-top:20px;font-size:10px;color:#9ca3af;border-top:1px solid #e2e8f0;padding-top:8px;">
  Generated {date.today().strftime("%-d %B %Y")} · Cowandilla Learning Centre LBU · Scatter Plot Tracker
</div>
</body></html>"""

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button("📥 Download raw data (CSV)", csv,
            file_name=f"ScatterPlot_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
            mime="text/csv", use_container_width=True)
    with dl2:
        st.download_button("📄 Download formatted report (HTML)", html_report,
            file_name=f"ScatterPlotReport_{student_name.replace(' ','_')}_{date_from}_{date_to}.html",
            mime="text/html", use_container_width=True)
    st.caption("💡 Open the HTML report in your browser and use Print → Save as PDF for a formatted printable version.")
