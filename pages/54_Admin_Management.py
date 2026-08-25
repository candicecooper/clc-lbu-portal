"""
Admin Duties Checklist
Cowandilla Learning Centre – LBU Portal Tool

Shared, live checklist of admin duties: pick your name, tick jobs off,
hand a job to a teammate, and see a dated "This Week" view of what's daily
vs weekly. Backed by Supabase (project cmqyrfekxgjdtuloseri) so every tick
and assignment is saved centrally and shows up for anyone else with this
page open — matching how the rest of the portal stores data.

Setup (one-off):
1. Run supabase_schema.sql once in the Supabase project's SQL editor —
   it creates checklist_staff / checklist_assignments / checklist_completions
   and seeds the starting staff list.
2. Optionally add SUPABASE_URL / SUPABASE_KEY to .streamlit/secrets.toml
   (falls back to the hardcoded project values below if not set, same
   st.secrets → env var → default chain used elsewhere in the portal).
3. `pip install supabase` (and optionally `streamlit-autorefresh` for
   near-live updates across users without a manual refresh).

Note on scope: unlike the Safety & Risk Plan Builder, this tool holds no
student data — only staff names, job assignments, and tick timestamps —
so storing it in Supabase doesn't raise the same data-governance concerns.

Note on login: there's no real password-protected sign-in here, just a
name picker (see checklist_staff) — matching what was agreed for this
tool specifically. If the portal later adds real Supabase Auth, the
identity block below is the piece to swap out.
"""

import streamlit as st
import os
from datetime import date, datetime, timedelta

# ── Supabase client (fails to a read-only "offline" mode if unavailable) ───
try:
    from supabase import create_client
except Exception:
    create_client = None

# ── Optional near-live refresh across users (fails silently if unavailable) ─
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

# ── Brand colours (matches portal house style) ──────────────────────────────
TEAL        = "#1A7A6E"
TEAL_LIGHT  = "#D6EEEB"
AMBER       = "#D97706"
AMBER_LIGHT = "#FEF3C7"
GREY_DARK   = "#2E4057"
GREY_LIGHT  = "#F2F6F6"
SAFETY_RED  = "#C0392B"

SSO_LABEL = {"am": "8–9am", "pm": "2:45–4pm", "both": "8–9am · 2:45–4pm"}
WEEKDAY_COLS = ["Mon", "Tue", "Wed", "Thu", "Fri"]  # date.weekday(): Mon=0..Fri=4

DEFAULT_STAFF = ["Candice", "Vinnie", "Annette", "Bonnie", "Naomi"]

# task keys: id, text, sso ("am"/"pm"/"both"/None), frequency ("daily"/"weekly"),
# weekday ("Mon".."Fri" or None — only meaningful when frequency == "weekly")
CATEGORIES = [
    {"id": "email", "title": "Email Monitoring", "safety": False, "tasks": [
        {"id": "email-1", "text": "Check emails as they come through", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "email-2", "text": "Forward emails on to the correct people", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "email-3", "text": "Respond to the admin email inbox", "sso": None, "frequency": "daily", "weekday": None},
    ]},
    {"id": "allocation", "title": "Allocation Process", "safety": False, "tasks": [
        {"id": "alloc-1", "text": "Print referrals that come through via email no later than 9am Wednesday", "sso": "am", "frequency": "weekly", "weekday": "Wed"},
        {"id": "alloc-2", "text": "Give a copy to the manager and the transition coordinator", "sso": "am", "frequency": "weekly", "weekday": "Wed"},
        {"id": "alloc-3", "text": "Receive the transition coordinator's email with allocation outcomes", "sso": None, "frequency": "weekly", "weekday": "Wed"},
        {"id": "alloc-6", "text": "Send communication to referring schools, BSE and TC (using the script) before 4:00pm Wednesday", "sso": "pm", "frequency": "weekly", "weekday": "Wed"},
        {"id": "alloc-7", "text": "Send a separate email to the allocated teacher with the student's details (not documents)", "sso": "pm", "frequency": "weekly", "weekday": "Wed"},
        {"id": "alloc-5", "text": "Create a OneDrive file for the student", "sso": None, "frequency": "weekly", "weekday": "Wed"},
        {"id": "alloc-4", "text": "Upload the student's files to OneDrive", "sso": None, "frequency": "weekly", "weekday": "Wed"},
        {"id": "alloc-8", "text": "Email LBU admin the student's information for the referrals database", "sso": None, "frequency": "weekly", "weekday": "Wed"},
    ]},
    {"id": "entry-meeting", "title": "Entry Meeting Follow-Up", "safety": False, "tasks": [
        {"id": "entry-1", "text": "Scan and upload entry meeting documents to OneDrive", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "entry-4", "text": "Place the original documents in the student's box", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "entry-5", "text": "Distribute documents to the teacher", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "entry-2", "text": "Enrol the student through the EMS", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "entry-3", "text": "Send taxi forms to LBU admin email for signing", "sso": None, "frequency": "daily", "weekday": None},
    ]},
    {"id": "phone", "title": "Phone Management", "safety": False, "tasks": [
        {"id": "phone-1", "text": "Transfer the phone over to mobile when not at the desk", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "phone-2", "text": "Switch the day/night switch each morning and afternoon", "sso": "both", "frequency": "daily", "weekday": None},
        {"id": "phone-3", "text": "Check the message bank and action any messages left", "sso": "both", "frequency": "daily", "weekday": None},
    ]},
    {"id": "taxi", "title": "Taxi Bookings", "safety": False, "tasks": [
        {"id": "taxi-1", "text": "Update and confirm bookings through the 131 Cabs app", "sso": "am", "frequency": "daily", "weekday": None},
        {"id": "taxi-2", "text": "Upload each day's transport details to the bulletin", "sso": "am", "frequency": "daily", "weekday": None},
        {"id": "taxi-3", "text": "Log pickups and the process for each student in OneNote", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "taxi-4", "text": "Monitor the app for student arrivals and departures, and update as required", "sso": "both", "frequency": "daily", "weekday": None},
    ]},
    {"id": "trt", "title": "TRT Payroll", "safety": False, "tasks": [
        {"id": "trt-1", "text": "Email Naomi with the day's on-site TRTs so they're added to payroll", "sso": "pm", "frequency": "daily", "weekday": None},
    ]},
    {"id": "medication", "title": "Medication", "safety": False, "tasks": [
        {"id": "med-2", "text": "Ensure medication documents (e.g. medication agreement form) are signed and filed with the medicine", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "med-1", "text": "Distribute medication to students who require it, at the correct times — set alarms as a reminder", "sso": None, "frequency": "daily", "weekday": None},
    ]},
    {"id": "bulletin", "title": "Daily Bulletin Screen", "safety": False, "tasks": [
        {"id": "bull-1", "text": "Update the planning room screen so staff can read the daily bulletin", "sso": "am", "frequency": "daily", "weekday": None},
    ]},
    {"id": "foodbank", "title": "Food Bank & Kickstart", "safety": False, "tasks": [
        {"id": "food-1", "text": "Work out what needs ordering for the week", "sso": None, "frequency": "weekly", "weekday": None},
        {"id": "food-2", "text": "Place the weekly order", "sso": None, "frequency": "weekly", "weekday": None},
    ]},
    {"id": "hazards", "title": "Hazard Management", "safety": True, "tasks": [
        {"id": "haz-1", "text": "Check for hazards reported via email", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "haz-2", "text": "Action and follow up on reported hazards", "sso": None, "frequency": "daily", "weekday": None},
    ]},
    {"id": "ventia", "title": "Ventia", "safety": False, "tasks": [
        {"id": "vent-1", "text": "Handle communication with Ventia as required", "sso": None, "frequency": "daily", "weekday": None},
        {"id": "vent-2", "text": "Sign off completed jobs in the Ventia portal", "sso": None, "frequency": "daily", "weekday": None},
    ]},
]

# ══════════════════════════════════════════════════════════════════════════
# SUPABASE CONNECTION — same st.secrets → env var → default chain used
# elsewhere in the portal (see GROQ_API_KEY in the Safety Plan Builder).
# The anon/publishable key is safe to ship in the page; Row Level Security
# policies on the tables (see supabase_schema.sql) control what it can do.
#
# st.secrets.get(...) raises StreamlitSecretNotFoundError (rather than
# returning the default) when no secrets.toml exists at all anywhere on the
# machine — as opposed to just missing that one key — so this is wrapped
# to fall back cleanly on a page/host with no secrets file configured.
# ══════════════════════════════════════════════════════════════════════════
def get_secret(key, default=""):
    try:
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key, default)


SUPABASE_URL = get_secret("SUPABASE_URL", "https://cmqyrfekxgjdtuloseri.supabase.co")
SUPABASE_KEY = get_secret("SUPABASE_KEY", "sb_publishable_KbEHgtFyQ-rCoct7d71blQ_ZP_pfPGG")


@st.cache_resource
def get_supabase():
    if create_client is None:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


sb = get_supabase()

# ══════════════════════════════════════════════════════════════════════════
# DATE HELPERS
# ══════════════════════════════════════════════════════════════════════════

def monday_of(d):
    return d - timedelta(days=d.weekday())


def week_start_iso(d):
    return monday_of(d).isoformat()


def period_key_for(task, ref_date):
    return week_start_iso(ref_date) if task["frequency"] == "weekly" else ref_date.isoformat()


def format_day_label(d):
    return d.strftime("%a %d %b")


def format_time(iso_ts):
    if not iso_ts:
        return ""
    try:
        ts = iso_ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%-I:%M%p").lower()
    except Exception:
        return ""


def freq_badge_text(task):
    if task["frequency"] == "weekly":
        return f"Weekly · {task['weekday']}" if task["weekday"] else "Weekly"
    return "Daily"


# ══════════════════════════════════════════════════════════════════════════
# SUPABASE READ/WRITE — every rerun reloads fresh so all viewers converge on
# the same data; writes are per-row (no full-document conflicts to resolve).
# ══════════════════════════════════════════════════════════════════════════

def load_staff():
    if not sb:
        return DEFAULT_STAFF[:]
    try:
        res = sb.table("checklist_staff").select("name").order("name").execute()
        names = [r["name"] for r in (res.data or [])]
        return names or DEFAULT_STAFF[:]
    except Exception:
        return DEFAULT_STAFF[:]


def load_assignments():
    if not sb:
        return {}
    try:
        res = sb.table("checklist_assignments").select("task_id, assignee").execute()
        return {r["task_id"]: r["assignee"] for r in (res.data or []) if r.get("assignee")}
    except Exception:
        return {}


def load_completions():
    """{ task_id: { period_key: {"by": ..., "at": ...} } }"""
    if not sb:
        return {}
    try:
        res = sb.table("checklist_completions").select("task_id, period_key, done_by, done_at").execute()
        out = {}
        for r in (res.data or []):
            out.setdefault(r["task_id"], {})[r["period_key"]] = {"by": r.get("done_by") or "Unknown", "at": r.get("done_at")}
        return out
    except Exception:
        return {}


def set_done(task_id, period_key, done, by):
    if not sb:
        st.toast("Not connected to Supabase — change wasn't saved", icon="⚠️")
        return
    try:
        if done:
            sb.table("checklist_completions").upsert(
                {"task_id": task_id, "period_key": period_key, "done_by": by,
                 "done_at": datetime.utcnow().isoformat()},
                on_conflict="task_id,period_key",
            ).execute()
        else:
            sb.table("checklist_completions").delete().eq("task_id", task_id).eq("period_key", period_key).execute()
    except Exception as e:
        st.toast(f"Couldn't save: {e}", icon="⚠️")


def set_assignee(task_id, name):
    if not sb:
        st.toast("Not connected to Supabase — change wasn't saved", icon="⚠️")
        return
    try:
        if name:
            sb.table("checklist_assignments").upsert(
                {"task_id": task_id, "assignee": name, "updated_at": datetime.utcnow().isoformat()},
                on_conflict="task_id",
            ).execute()
        else:
            sb.table("checklist_assignments").delete().eq("task_id", task_id).execute()
    except Exception as e:
        st.toast(f"Couldn't save: {e}", icon="⚠️")


def add_staff(name):
    if not sb:
        st.toast("Not connected to Supabase — name wasn't saved", icon="⚠️")
        return
    try:
        sb.table("checklist_staff").insert({"name": name}).execute()
    except Exception as e:
        st.toast(f"Couldn't add name: {e}", icon="⚠️")


def remove_staff(name):
    if not sb:
        st.toast("Not connected to Supabase — name wasn't removed", icon="⚠️")
        return
    try:
        sb.table("checklist_assignments").delete().eq("assignee", name).execute()
        sb.table("checklist_staff").delete().eq("name", name).execute()
    except Exception as e:
        st.toast(f"Couldn't remove name: {e}", icon="⚠️")


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "current_user": None,
        "filter_sso": False,
        "week_offset": 0,
        "show_staff_panel": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Admin Duties Checklist | LBU",
    page_icon="✅", layout="wide", initial_sidebar_state="collapsed"
)

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}

  .clc-header {{ background:{TEAL}; color:white; padding:18px 28px 14px; border-radius:10px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; }}
  .clc-header h1 {{ margin:0; font-size:1.3rem; font-weight:700; }}
  .clc-header p  {{ margin:0; font-size:0.82rem; opacity:0.8; }}
  .clc-badge {{ background:{AMBER}; color:white; font-size:0.72rem; font-weight:700; padding:4px 10px; border-radius:20px; }}

  .sec-head {{ font-size:11px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:{TEAL}; margin:18px 0 8px; border-bottom:2px solid {TEAL_LIGHT}; padding-bottom:4px; }}

  .task-badge {{ display:inline-block; font-size:10px; font-weight:700; padding:2px 8px; border-radius:20px; margin-right:5px; white-space:nowrap; }}
  .badge-sso  {{ background:{TEAL_LIGHT}; color:{TEAL}; }}
  .badge-freq {{ background:{GREY_LIGHT}; color:#5C6B74; }}
  .badge-done {{ background:#d1fae5; color:#065f46; }}

  .cat-card {{ border:1px solid #e2e8f0; border-left-width:4px; border-radius:10px; padding:10px 16px 4px; margin-bottom:14px; background:white; }}
  .cat-card.safety {{ border-left-color:{SAFETY_RED}; }}
  .cat-card.normal {{ border-left-color:{TEAL}; }}
  .cat-title {{ font-weight:700; color:{GREY_DARK}; font-size:14.5px; }}
  .cat-count {{ float:right; font-size:12px; font-weight:600; color:#888; background:{GREY_LIGHT}; padding:2px 10px; border-radius:20px; }}

  div[data-testid="stExpander"] {{ border:1.5px solid {TEAL_LIGHT} !important; border-radius:8px !important; }}
  .stButton > button {{ font-family:'DM Sans',sans-serif !important; font-weight:600 !important; border-radius:8px !important; }}
</style>
""", unsafe_allow_html=True)

init_state()

if st_autorefresh:
    # Near-live updates across users without a manual refresh. Optional —
    # `pip install streamlit-autorefresh` to enable; degrades silently
    # without it (see the try/except import at the top of this file).
    st_autorefresh(interval=20_000, key="checklist_autorefresh")

st.markdown(f"""
<div class="clc-header">
  <div><h1>✅ Admin Duties Checklist</h1>
  <p>Cowandilla Learning Centre — LBU Portal Tool</p></div>
  <span class="clc-badge">{"SUPABASE CONNECTED" if sb else "OFFLINE — CHECK CONNECTION"}</span>
</div>""", unsafe_allow_html=True)

staff = load_staff()

# ── Identity ─────────────────────────────────────────────────────────────
if st.session_state.current_user:
    id_col1, id_col2, id_col3 = st.columns([4, 1, 1])
    with id_col1:
        st.markdown(f"Signed in as **{st.session_state.current_user}**")
    with id_col2:
        if st.button("Switch", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()
    with id_col3:
        if st.button("Manage staff", use_container_width=True):
            st.session_state.show_staff_panel = not st.session_state.show_staff_panel
else:
    st.markdown('<div class="sec-head">Who\'s ticking things off?</div>', unsafe_allow_html=True)
    st.caption("This labels your ticks and job assignments so the team can see who did what — it isn't a password, so please pick your real name.")
    pick_cols = st.columns(len(staff) if staff else 1)
    for i, name in enumerate(staff):
        with pick_cols[i]:
            if st.button(name, key=f"pick_{name}", use_container_width=True):
                st.session_state.current_user = name
                st.rerun()
    with st.expander("Not on the list? Add your name"):
        new_signin_name = st.text_input("Name", key="signin_new_name", label_visibility="collapsed", placeholder="Your name")
        if st.button("Add & continue", key="signin_add_btn"):
            if new_signin_name.strip():
                add_staff(new_signin_name.strip())
                st.session_state.current_user = new_signin_name.strip()
                st.rerun()

if st.session_state.show_staff_panel:
    with st.expander("⚙️ Manage staff", expanded=True):
        st.caption("Anyone with this page can edit this list — there's no password behind it, so it's really just a shared roster to keep names consistent.")
        for name in staff:
            rc1, rc2 = st.columns([5, 1])
            rc1.write(name)
            if rc2.button("Remove", key=f"rm_{name}"):
                remove_staff(name)
                if st.session_state.current_user == name:
                    st.session_state.current_user = None
                st.rerun()
        new_staff_name = st.text_input("Add a name", key="staff_add_input", label_visibility="collapsed", placeholder="Add a name")
        if st.button("Add name", key="staff_add_btn"):
            if new_staff_name.strip():
                add_staff(new_staff_name.strip())
                st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_checklist, tab_week = st.tabs(["📋 Checklist", "📅 This Week"])

# ── Checklist tab ───────────────────────────────────────────────────────────
with tab_checklist:
    assignments = load_assignments()
    completions = load_completions()
    today = date.today()

    total_tasks, done_tasks = 0, 0
    for cat in CATEGORIES:
        for t in cat["tasks"]:
            total_tasks += 1
            if period_key_for(t, today) in completions.get(t["id"], {}):
                done_tasks += 1
    st.progress(done_tasks / total_tasks if total_tasks else 0,
                text=f"{done_tasks}/{total_tasks} done today")
    st.caption("🟢 8–9am / 2:45–4pm badges mark tasks that fit an SSO's admin hours. Daily / Weekly badges show how often a job comes around.")

    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 3])
    with ctrl1:
        st.session_state.filter_sso = st.toggle("SSO hours only", value=st.session_state.filter_sso)
    with ctrl2:
        if st.button("Clear today's ticks"):
            for cat in CATEGORIES:
                for t in cat["tasks"]:
                    key = period_key_for(t, today)
                    if key in completions.get(t["id"], {}):
                        set_done(t["id"], key, False, st.session_state.current_user)
            st.rerun()
    with ctrl3:
        if st.button("🔄 Refresh now"):
            st.rerun()

    for cat in CATEGORIES:
        tasks = cat["tasks"]
        if st.session_state.filter_sso:
            tasks = [t for t in tasks if t["sso"]]
        if not tasks:
            continue

        cat_done = sum(1 for t in tasks if period_key_for(t, today) in completions.get(t["id"], {}))
        safety_cls = "safety" if cat["safety"] else "normal"
        st.markdown(
            f'<div class="cat-card {safety_cls}">'
            f'<span class="cat-count">{cat_done}/{len(tasks)}</span>'
            f'<span class="cat-title">{cat["title"]}</span></div>',
            unsafe_allow_html=True,
        )

        for t in tasks:
            key = period_key_for(t, today)
            comp = completions.get(t["id"], {}).get(key)
            checked = comp is not None

            row = st.columns([0.5, 5, 2, 2])
            new_val = row[0].checkbox("", value=checked, key=f"chk_{t['id']}", label_visibility="collapsed")

            badges = f'<span class="task-badge badge-freq">{freq_badge_text(t)}</span>'
            if t["sso"]:
                badges += f'<span class="task-badge badge-sso">{SSO_LABEL[t["sso"]]}</span>'
            if comp:
                badges += f'<span class="task-badge badge-done">Done by {comp["by"]} · {format_time(comp["at"])}</span>'
            row[1].markdown(f'{t["text"]}<br/>{badges}', unsafe_allow_html=True)

            current_assignee = assignments.get(t["id"])
            options = ["Unassigned"] + staff
            idx = options.index(current_assignee) if current_assignee in options else 0
            picked = row[2].selectbox("Assigned to", options, index=idx, key=f"asg_{t['id']}", label_visibility="collapsed")

            if new_val != checked:
                set_done(t["id"], key, new_val, st.session_state.current_user or "Unknown")
                st.rerun()
            if picked != (current_assignee or "Unassigned"):
                set_assignee(t["id"], None if picked == "Unassigned" else picked)
                st.rerun()

# ── This Week tab ────────────────────────────────────────────────────────────
with tab_week:
    assignments = load_assignments()
    completions = load_completions()

    nav1, nav2, nav3, nav4 = st.columns([1, 3, 1, 1])
    with nav1:
        if st.button("‹ Prev", key="week_prev"):
            st.session_state.week_offset -= 1
            st.rerun()
    monday = monday_of(date.today()) + timedelta(weeks=st.session_state.week_offset)
    week_dates = [monday + timedelta(days=i) for i in range(5)]
    with nav2:
        st.markdown(f"**Week of {format_day_label(week_dates[0])} – {format_day_label(week_dates[-1])}**")
    with nav3:
        if st.button("This week", key="week_today_btn"):
            st.session_state.week_offset = 0
            st.rerun()
    with nav4:
        if st.button("Next ›", key="week_next"):
            st.session_state.week_offset += 1
            st.rerun()

    today_iso = date.today().isoformat()

    header_cols = st.columns([3, 1, 1, 1, 1, 1])
    header_cols[0].markdown("**Task**")
    for i, d in enumerate(week_dates):
        label = format_day_label(d)
        if d.isoformat() == today_iso:
            header_cols[i + 1].markdown(f"**:green[{label}]**")
        else:
            header_cols[i + 1].markdown(f"**{label}**")
    st.markdown("---")

    any_day_tasks = []

    for cat in CATEGORIES:
        pinned = [t for t in cat["tasks"] if t["frequency"] == "daily" or (t["frequency"] == "weekly" and t["weekday"])]
        any_day = [t for t in cat["tasks"] if t["frequency"] == "weekly" and not t["weekday"]]
        any_day_tasks.extend((cat, t) for t in any_day)
        if not pinned:
            continue

        st.markdown(f'<div class="sec-head">{cat["title"]}</div>', unsafe_allow_html=True)
        for t in pinned:
            row = st.columns([3, 1, 1, 1, 1, 1])
            assignee = assignments.get(t["id"])
            label = t["text"] + (f"  ·  *{assignee}*" if assignee else "")
            row[0].markdown(label)
            for i, d in enumerate(week_dates):
                col_short = WEEKDAY_COLS[d.weekday()]
                applies = t["frequency"] == "daily" or t["weekday"] == col_short
                if not applies:
                    row[i + 1].markdown("—")
                else:
                    key = period_key_for(t, d)
                    comp = completions.get(t["id"], {}).get(key)
                    checked = comp is not None
                    new_val = row[i + 1].checkbox(
                        "", value=checked, key=f"wk_{t['id']}_{key}",
                        label_visibility="collapsed",
                        help=f"Done by {comp['by']} · {format_time(comp['at'])}" if comp else None,
                    )
                    if new_val != checked:
                        set_done(t["id"], key, new_val, st.session_state.current_user or "Unknown")
                        st.rerun()

    if any_day_tasks:
        st.markdown('<div class="sec-head">Weekly (any day this week)</div>', unsafe_allow_html=True)
        for cat, t in any_day_tasks:
            key = period_key_for(t, monday)
            comp = completions.get(t["id"], {}).get(key)
            checked = comp is not None
            assignee = assignments.get(t["id"])
            c1, c2 = st.columns([6, 1])
            label = f'{cat["title"]} — {t["text"]}' + (f"  ·  *{assignee}*" if assignee else "")
            c1.markdown(label)
            new_val = c2.checkbox("", value=checked, key=f"anyday_{t['id']}", label_visibility="collapsed")
            if new_val != checked:
                set_done(t["id"], key, new_val, st.session_state.current_user or "Unknown")
                st.rerun()

st.markdown("---")
st.caption(
    "Ticks and assignments save straight to Supabase and are shared with anyone who opens this page "
    "(refresh, or wait ~20s if streamlit-autorefresh is installed, to see others' changes). "
    "\"Clear today's ticks\" only clears the current day/week — past history stays on the This Week tab."
)
