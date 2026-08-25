"""
Admin Duties Checklist
Cowandilla Learning Centre – LBU Portal Tool

Shared, live checklist of admin duties: pick your name, tick jobs off,
hand a job to a teammate, and see a dated "This Week" view of what's daily
vs weekly. Backed by Supabase (project cmqyrfekxgjdtuloseri) so every tick
and assignment is saved centrally and shows up for anyone else with this
page open — matching how the rest of the portal stores data.

A password-gated "🔒 Admin" panel (password: see ADMIN_PASSWORD below) lets
someone add a new duty to any section, or edit/delete a duty already
listed — see "Note on the Admin panel" below for how that's stored and
what the password does and doesn't protect.

Setup (one-off):
1. Run supabase_schema.sql once in the Supabase project's SQL editor —
   it creates checklist_staff / checklist_assignments / checklist_completions
   and seeds the starting staff list.
2. Run supabase_schema_tasks.sql once too (after the above) — it creates
   checklist_tasks and seeds it with the current duty list, which is what
   the Admin panel adds/edits/deletes rows in. Skipping this step doesn't
   break the page — it just falls back to the built-in DEFAULT_TASKS below
   and Admin panel changes won't be able to save.
3. Optionally add SUPABASE_URL / SUPABASE_KEY to .streamlit/secrets.toml
   (falls back to the hardcoded project values below if not set, same
   st.secrets → env var → default chain used elsewhere in the portal).
4. `pip install supabase` (and optionally `streamlit-autorefresh` for
   near-live updates across users without a manual refresh).

Note on scope: unlike the Safety & Risk Plan Builder, this tool holds no
student data — only staff names, job assignments, tick timestamps, and the
duty text itself — so storing it in Supabase doesn't raise the same
data-governance concerns.

Note on login: there's no real password-protected sign-in here, just a
name picker (see checklist_staff) — matching what was agreed for this
tool specifically. If the portal later adds real Supabase Auth, the
identity block below is the piece to swap out.

Note on the Admin panel: ADMIN_PASSWORD is checked in this script, which
anyone with repo access can read — it's a "don't show this to everyone"
gate, not real security. The same anon Supabase key this whole page ships
with can already write to checklist_tasks directly, so this doesn't add
a new attack surface, it just keeps the panel out of casual browsing.
"""

import streamlit as st
import os
from datetime import date, datetime, timedelta
from uuid import uuid4

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

# Password for the "Manage duties" admin panel below. This only hides the
# panel from casual browsing — it's checked in this script, which anyone
# with repo access can read, so it isn't real security (same tradeoff as
# the anon Supabase key this whole page already ships with).
ADMIN_PASSWORD = "secret2026"

# Sections are fixed in code — the admin panel adds/edits/removes duties
# *within* these, it doesn't add new sections. Order here is display order.
CATEGORY_DEFS = [
    {"id": "email", "title": "Email Monitoring", "safety": False},
    {"id": "allocation", "title": "Allocation Process", "safety": False},
    {"id": "entry-meeting", "title": "Entry Meeting Follow-Up", "safety": False},
    {"id": "phone", "title": "Phone Management", "safety": False},
    {"id": "taxi", "title": "Taxi Bookings", "safety": False},
    {"id": "trt", "title": "TRT Payroll", "safety": False},
    {"id": "medication", "title": "Medication", "safety": False},
    {"id": "bulletin", "title": "Daily Bulletin Screen", "safety": False},
    {"id": "foodbank", "title": "Food Bank & Kickstart", "safety": False},
    {"id": "hazards", "title": "Hazard Management", "safety": True},
    {"id": "ventia", "title": "Ventia", "safety": False},
]
CATEGORY_TITLES = {c["id"]: c["title"] for c in CATEGORY_DEFS}

# task keys: id, category_id, text, sso ("am"/"pm"/"both"/None),
# frequency ("daily"/"weekly"), weekday ("Mon".."Fri" or None — only
# meaningful when frequency == "weekly"), sort_order.
#
# This flat list is only the fallback used before the checklist_tasks
# Supabase table has been migrated to (see supabase_schema_tasks.sql) or if
# it can't be reached — once that table is live it's the source of truth,
# and duties added/edited/removed via the admin panel live there instead.
DEFAULT_TASKS = [
    {"id": "email-1", "category_id": "email", "text": "Check emails as they come through", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "email-2", "category_id": "email", "text": "Forward emails on to the correct people", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},
    {"id": "email-3", "category_id": "email", "text": "Respond to the admin email inbox", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 3},

    {"id": "alloc-1", "category_id": "allocation", "text": "Print referrals that come through via email no later than 9am Wednesday", "sso": "am", "frequency": "weekly", "weekday": "Wed", "sort_order": 1},
    {"id": "alloc-2", "category_id": "allocation", "text": "Give a copy to the manager and the transition coordinator", "sso": "am", "frequency": "weekly", "weekday": "Wed", "sort_order": 2},
    {"id": "alloc-3", "category_id": "allocation", "text": "Receive the transition coordinator's email with allocation outcomes", "sso": None, "frequency": "weekly", "weekday": "Wed", "sort_order": 3},
    {"id": "alloc-6", "category_id": "allocation", "text": "Send communication to referring schools, BSE and TC (using the script) before 4:00pm Wednesday", "sso": "pm", "frequency": "weekly", "weekday": "Wed", "sort_order": 4},
    {"id": "alloc-7", "category_id": "allocation", "text": "Send a separate email to the allocated teacher with the student's details (not documents)", "sso": "pm", "frequency": "weekly", "weekday": "Wed", "sort_order": 5},
    {"id": "alloc-5", "category_id": "allocation", "text": "Create a OneDrive file for the student", "sso": None, "frequency": "weekly", "weekday": "Wed", "sort_order": 6},
    {"id": "alloc-4", "category_id": "allocation", "text": "Upload the student's files to OneDrive", "sso": None, "frequency": "weekly", "weekday": "Wed", "sort_order": 7},
    {"id": "alloc-8", "category_id": "allocation", "text": "Email LBU admin the student's information for the referrals database", "sso": None, "frequency": "weekly", "weekday": "Wed", "sort_order": 8},

    {"id": "entry-1", "category_id": "entry-meeting", "text": "Scan and upload entry meeting documents to OneDrive", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "entry-4", "category_id": "entry-meeting", "text": "Place the original documents in the student's box", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},
    {"id": "entry-5", "category_id": "entry-meeting", "text": "Distribute documents to the teacher", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 3},
    {"id": "entry-2", "category_id": "entry-meeting", "text": "Enrol the student through the EMS", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 4},
    {"id": "entry-3", "category_id": "entry-meeting", "text": "Send taxi forms to LBU admin email for signing", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 5},

    {"id": "phone-1", "category_id": "phone", "text": "Transfer the phone over to mobile when not at the desk", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "phone-2", "category_id": "phone", "text": "Switch the day/night switch each morning and afternoon", "sso": "both", "frequency": "daily", "weekday": None, "sort_order": 2},
    {"id": "phone-3", "category_id": "phone", "text": "Check the message bank and action any messages left", "sso": "both", "frequency": "daily", "weekday": None, "sort_order": 3},

    {"id": "taxi-1", "category_id": "taxi", "text": "Update and confirm bookings through the 131 Cabs app", "sso": "am", "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "taxi-2", "category_id": "taxi", "text": "Upload each day's transport details to the bulletin", "sso": "am", "frequency": "daily", "weekday": None, "sort_order": 2},
    {"id": "taxi-3", "category_id": "taxi", "text": "Log pickups and the process for each student in OneNote", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 3},
    {"id": "taxi-4", "category_id": "taxi", "text": "Monitor the app for student arrivals and departures, and update as required", "sso": "both", "frequency": "daily", "weekday": None, "sort_order": 4},

    {"id": "trt-1", "category_id": "trt", "text": "Email Naomi with the day's on-site TRTs so they're added to payroll", "sso": "pm", "frequency": "daily", "weekday": None, "sort_order": 1},

    {"id": "med-2", "category_id": "medication", "text": "Ensure medication documents (e.g. medication agreement form) are signed and filed with the medicine", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "med-1", "category_id": "medication", "text": "Distribute medication to students who require it, at the correct times — set alarms as a reminder", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},

    {"id": "bull-1", "category_id": "bulletin", "text": "Update the planning room screen so staff can read the daily bulletin", "sso": "am", "frequency": "daily", "weekday": None, "sort_order": 1},

    {"id": "food-1", "category_id": "foodbank", "text": "Work out what needs ordering for the week", "sso": None, "frequency": "weekly", "weekday": None, "sort_order": 1},
    {"id": "food-2", "category_id": "foodbank", "text": "Place the weekly order", "sso": None, "frequency": "weekly", "weekday": None, "sort_order": 2},

    {"id": "haz-1", "category_id": "hazards", "text": "Check for hazards reported via email", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "haz-2", "category_id": "hazards", "text": "Action and follow up on reported hazards", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},

    {"id": "vent-1", "category_id": "ventia", "text": "Handle communication with Ventia as required", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "vent-2", "category_id": "ventia", "text": "Sign off completed jobs in the Ventia portal", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},
]


def grouped_categories(tasks_flat):
    """Group a flat task list under CATEGORY_DEFS, in display + sort order."""
    out = []
    for cd in CATEGORY_DEFS:
        cat_tasks = sorted(
            (t for t in tasks_flat if t["category_id"] == cd["id"]),
            key=lambda t: t.get("sort_order", 0),
        )
        out.append({"id": cd["id"], "title": cd["title"], "safety": cd["safety"], "tasks": cat_tasks})
    return out

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


def load_tasks():
    """Flat list of task dicts (id, category_id, text, sso, frequency,
    weekday, sort_order) — checklist_tasks is the source of truth once it
    has rows in it; falls back to the built-in DEFAULT_TASKS if the table
    is empty (not migrated to yet) or unreachable."""
    if not sb:
        return [dict(t) for t in DEFAULT_TASKS]
    try:
        res = (
            sb.table("checklist_tasks")
            .select("id, category_id, text, sso, frequency, weekday, sort_order")
            .order("sort_order")
            .execute()
        )
        rows = res.data or []
        if not rows:
            return [dict(t) for t in DEFAULT_TASKS]
        return rows
    except Exception:
        return [dict(t) for t in DEFAULT_TASKS]


def next_sort_order(tasks_flat, category_id):
    existing = [t.get("sort_order", 0) for t in tasks_flat if t["category_id"] == category_id]
    return (max(existing) + 1) if existing else 1


def add_task(category_id, text, frequency, weekday, sso, tasks_flat):
    task_id = f"{category_id}-{uuid4().hex[:8]}"
    row = {
        "id": task_id, "category_id": category_id, "text": text,
        "sso": sso or None, "frequency": frequency,
        "weekday": weekday if frequency == "weekly" else None,
        "sort_order": next_sort_order(tasks_flat, category_id),
    }
    if not sb:
        st.toast("Not connected to Supabase — duty wasn't saved", icon="⚠️")
        return
    try:
        sb.table("checklist_tasks").insert(row).execute()
    except Exception as e:
        st.toast(f"Couldn't save the new duty: {e}", icon="⚠️")


def update_task(task_id, fields):
    if not sb:
        st.toast("Not connected to Supabase — change wasn't saved", icon="⚠️")
        return
    try:
        payload = dict(fields)
        if payload.get("frequency") == "daily":
            payload["weekday"] = None
        sb.table("checklist_tasks").update(payload).eq("id", task_id).execute()
    except Exception as e:
        st.toast(f"Couldn't save that change: {e}", icon="⚠️")


def delete_task(task_id):
    if not sb:
        st.toast("Not connected to Supabase — duty wasn't deleted", icon="⚠️")
        return
    try:
        sb.table("checklist_completions").delete().eq("task_id", task_id).execute()
        sb.table("checklist_assignments").delete().eq("task_id", task_id).execute()
        sb.table("checklist_tasks").delete().eq("id", task_id).execute()
    except Exception as e:
        st.toast(f"Couldn't delete that duty: {e}", icon="⚠️")


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
        "admin_unlocked": False,
        "show_admin_login": False,
        "show_admin_panel": False,
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

# Reset the "Add a duty" form fields on the run after a successful add —
# must happen before those widgets are instantiated below (see the note in
# the "Add duty" button handler further down for why this can't happen
# in the same run as the click).
if st.session_state.get("_clear_admin_form"):
    st.session_state["admin_new_text"] = ""
    st.session_state["admin_new_freq"] = "Daily"
    st.session_state["admin_new_sso"] = "None"
    st.session_state.pop("admin_new_weekday", None)
    st.session_state["_clear_admin_form"] = False

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
    id_col1, id_col2, id_col3, id_col4 = st.columns([3, 1, 1, 1])
    with id_col1:
        st.markdown(f"Signed in as **{st.session_state.current_user}**")
    with id_col2:
        if st.button("Switch", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()
    with id_col3:
        if st.button("Manage staff", use_container_width=True):
            st.session_state.show_staff_panel = not st.session_state.show_staff_panel
    with id_col4:
        if st.button("🔒 Admin", use_container_width=True):
            if st.session_state.admin_unlocked:
                st.session_state.show_admin_panel = not st.session_state.show_admin_panel
            else:
                st.session_state.show_admin_login = not st.session_state.show_admin_login
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

# ── Admin: duty management (password-gated, Supabase-backed) ───────────────
# See the ADMIN_PASSWORD note above the constant — this is a "don't show
# this to everyone" gate, not real security.
if st.session_state.show_admin_login and not st.session_state.admin_unlocked:
    with st.expander("🔒 Admin access", expanded=True):
        st.caption("Enter the admin password to add, edit, or remove duties.")
        pw_col1, pw_col2 = st.columns([3, 1])
        admin_pw = pw_col1.text_input("Password", type="password", key="admin_pw_input", label_visibility="collapsed")
        if pw_col2.button("Unlock", use_container_width=True):
            if admin_pw == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.session_state.show_admin_login = False
                st.session_state.show_admin_panel = True
                st.rerun()
            else:
                st.error("That password isn't right.")

if st.session_state.show_admin_panel and st.session_state.admin_unlocked:
    with st.expander("🛠️ Manage duties", expanded=True):
        st.caption(
            "Add a new duty to any section below, or edit and remove ones already listed. "
            "Changes save straight to Supabase for everyone."
        )
        admin_tasks = load_tasks()

        st.markdown("**Add a duty**")
        new_text = st.text_input("Duty text", key="admin_new_text", placeholder="e.g. Print the visitor sign-in sheet")
        ac1, ac2, ac3, ac4 = st.columns(4)
        new_cat_title = ac1.selectbox("Section", [c["title"] for c in CATEGORY_DEFS], key="admin_new_cat")
        new_freq = ac2.selectbox("Frequency", ["Daily", "Weekly"], key="admin_new_freq")
        new_weekday = None
        if new_freq == "Weekly":
            new_weekday_pick = ac3.selectbox("Fixed day", ["No fixed day"] + WEEKDAY_COLS, key="admin_new_weekday")
            new_weekday = None if new_weekday_pick == "No fixed day" else new_weekday_pick
        else:
            ac3.markdown("&nbsp;", unsafe_allow_html=True)
        new_sso_pick = ac4.selectbox("SSO hours", ["None", "8–9am", "2:45–4pm", "Both"], key="admin_new_sso")
        new_sso = {"None": None, "8–9am": "am", "2:45–4pm": "pm", "Both": "both"}[new_sso_pick]

        if st.button("Add duty", key="admin_add_btn"):
            if new_text.strip():
                new_cat_id = next(c["id"] for c in CATEGORY_DEFS if c["title"] == new_cat_title)
                add_task(new_cat_id, new_text.strip(), new_freq.lower(), new_weekday, new_sso, admin_tasks)
                # Streamlit won't let a widget's session_state be changed in
                # the same run after it's been instantiated — set a flag and
                # clear the form on the next run instead, before those
                # widgets are created (see the top of the script).
                st.session_state["_clear_admin_form"] = True
                st.rerun()

        st.markdown("---")
        for cat in grouped_categories(admin_tasks):
            if not cat["tasks"]:
                continue
            st.markdown(f'<div class="sec-head">{cat["title"]}</div>', unsafe_allow_html=True)
            for t in cat["tasks"]:
                dr1, dr2, dr3, dr4, dr5 = st.columns([4, 1.2, 1, 1.3, 1])
                edited_text = dr1.text_input(
                    "Duty text", value=t["text"], key=f"dtext_{t['id']}", label_visibility="collapsed"
                )
                freq_pick = dr2.selectbox(
                    "Frequency", ["Daily", "Weekly"],
                    index=0 if t["frequency"] == "daily" else 1,
                    key=f"dfreq_{t['id']}", label_visibility="collapsed",
                )
                freq_val = freq_pick.lower()
                weekday_val = t["weekday"]
                if freq_val == "weekly":
                    wd_options = ["No fixed day"] + WEEKDAY_COLS
                    wd_index = wd_options.index(t["weekday"]) if t["weekday"] in WEEKDAY_COLS else 0
                    wd_pick = dr3.selectbox(
                        "Fixed day", wd_options, index=wd_index,
                        key=f"dweekday_{t['id']}", label_visibility="collapsed",
                    )
                    weekday_val = None if wd_pick == "No fixed day" else wd_pick
                else:
                    dr3.markdown("&nbsp;")
                    weekday_val = None
                sso_options = ["None", "8–9am", "2:45–4pm", "Both"]
                sso_map = {"None": None, "8–9am": "am", "2:45–4pm": "pm", "Both": "both"}
                sso_rev = {v: k for k, v in sso_map.items()}
                sso_pick = dr4.selectbox(
                    "SSO hours", sso_options, index=sso_options.index(sso_rev.get(t["sso"], "None")),
                    key=f"dsso_{t['id']}", label_visibility="collapsed",
                )
                sso_val = sso_map[sso_pick]

                confirm_key = f"confirm_del_{t['id']}"
                if st.session_state.get(confirm_key):
                    if dr5.button("Confirm?", key=f"delc_{t['id']}", use_container_width=True):
                        delete_task(t["id"])
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                else:
                    if dr5.button("Delete", key=f"del_{t['id']}", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()

                changed = (
                    edited_text.strip() and edited_text.strip() != t["text"]
                    or freq_val != t["frequency"]
                    or weekday_val != t["weekday"]
                    or sso_val != t["sso"]
                )
                if changed:
                    update_task(t["id"], {
                        "text": edited_text.strip() or t["text"],
                        "frequency": freq_val, "weekday": weekday_val, "sso": sso_val,
                    })
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
    checklist_tasks_flat = load_tasks()
    today = date.today()

    total_tasks, done_tasks = 0, 0
    for cat in grouped_categories(checklist_tasks_flat):
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
            for cat in grouped_categories(checklist_tasks_flat):
                for t in cat["tasks"]:
                    key = period_key_for(t, today)
                    if key in completions.get(t["id"], {}):
                        set_done(t["id"], key, False, st.session_state.current_user)
            st.rerun()
    with ctrl3:
        if st.button("🔄 Refresh now"):
            st.rerun()

    for cat in grouped_categories(checklist_tasks_flat):
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
    week_tasks_flat = load_tasks()

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

    for cat in grouped_categories(week_tasks_flat):
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
    "Ticks, assignments, and duty changes save straight to Supabase and are shared with anyone who opens this page "
    "(refresh, or wait ~20s if streamlit-autorefresh is installed, to see others' changes). "
    "\"Clear today's ticks\" only clears the current day/week — past history stays on the This Week tab."
)
