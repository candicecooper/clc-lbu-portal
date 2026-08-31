"""
Admin Jobs Checklist
Cowandilla Learning Centre – LBU Portal Tool

Shared, live checklist of admin jobs (deliberately called "jobs" rather
than "duties" throughout this page, since "duty" already means yard/break
duty at school): pick your name, tick jobs off, and see a dated "This
Week" view of what's daily vs weekly. Backed by Supabase (project
cmqyrfekxgjdtuloseri) so every tick and roster change is saved centrally
and shows up for anyone else with this page open — matching how the rest
of the portal stores data.

A password-gated "🔒 Admin" panel (password: see ADMIN_PASSWORD below) lets
someone add a new job to any section, edit/delete a job already listed,
and create, rename, or remove sections themselves — see "Note on the
Admin panel" below for how that's stored and what the password does and
doesn't protect.

Setup (one-off):
1. Run supabase_schema.sql once in the Supabase project's SQL editor —
   it creates checklist_staff / checklist_assignments / checklist_completions
   and seeds the starting staff list.
2. Run supabase_schema_tasks.sql once too (after the above) — it creates
   checklist_tasks and seeds it with the current job list, which is what
   the Admin panel adds/edits/deletes rows in. Skipping this step doesn't
   break the page — it just falls back to the built-in DEFAULT_TASKS below
   and Admin panel changes won't be able to save.
3. Run supabase_schema_categories.sql once too (after the above two) — it
   creates checklist_categories and seeds it with the current section
   list, which is what the Admin panel's "Sections" area adds/renames/
   deletes rows in. Skipping this step doesn't break the page — it just
   falls back to the built-in DEFAULT_CATEGORIES below and new sections
   won't be able to save.
4. Run supabase_schema_roster.sql once too (after the above three) — it
   creates checklist_duty_roster, which is what drives who's responsible
   for each job, day by day (see "Note on responsibility" below). This
   REPLACES the old single "assigned to" dropdown backed by
   checklist_assignments — that table is left alone but no longer read by
   this page. Skipping this step doesn't break the page — jobs just show
   as "Unassigned" everywhere until it's run.
5. Run supabase_schema_staff_hours.sql once too (independent of the other
   migrations) — it creates checklist_staff_hours, which is what the
   "🕐 Admin hours" panel reads and writes (see "Note on admin hours"
   below). Skipping this step doesn't break the page — the panel just
   won't be able to save.
6. Optionally add SUPABASE_URL / SUPABASE_KEY to .streamlit/secrets.toml
   (falls back to the hardcoded project values below if not set, same
   st.secrets → env var → default chain used elsewhere in the portal).
7. `pip install supabase` (and optionally `streamlit-autorefresh` for
   near-live updates across users without a manual refresh).

Note on responsibility: each job can have different people responsible
on different weekdays, and a single day can have more than one person
(shared responsibility) — set this up per job from the "Manage jobs"
admin panel's "Roster" section. A single "Viewing" picker sits above the
tabs — pick a name and both the Today tab and This Week tab filter down
to just their jobs (still tickable), with "+ Name" shown for any day
they share with someone else. Leave it on "Everyone" to see the full list.

Note on admin hours: the "🕐 Admin hours" panel (next to "Manage staff")
lets you set the hours each person is picking up admin jobs, day by day —
e.g. someone might only do admin 8:00-9:00am and 2:45-4:00pm most days,
but longer on a Wednesday. This replaced the old fixed "SSO hours"
badges/toggle, which hard-coded one pair of windows onto specific jobs
and couldn't vary by day. It's purely informational: picking a name under
"Viewing jobs for" shows their hours for the week right underneath, but
it doesn't hide or filter which jobs show up.

Note on the overdue flag: on the Today tab, a DAILY job still unticked
after ADMIN_DEADLINE (2:45pm) gets a "⚠ Overdue" badge and a highlighted
row; once ticked, a job instead fades out (job-row-done). Weekly jobs are
excluded — one due "any time this week" shouldn't flag every afternoon.
This is purely a display concern (is_past_admin_deadline()), so it only
updates when the page reruns — on a tick, a tab switch, or the
streamlit-autorefresh tick if that package is installed (see below).

Note on scope: unlike the Safety & Risk Plan Builder, this tool holds no
student data — only staff names, job roster assignments, tick timestamps,
and the job text itself — so storing it in Supabase doesn't raise the
same data-governance concerns.

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

import re
import streamlit as st
import os
from datetime import date, datetime, time, timedelta
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

WEEKDAY_COLS = ["Mon", "Tue", "Wed", "Thu", "Fri"]  # date.weekday(): Mon=0..Fri=4

# Sentinel used in checklist_duty_roster.weekday for a weekly job with no
# fixed day, instead of NULL — Postgres primary keys can't contain NULL,
# and "Any" reads clearly in the data too.
WEEKDAY_ANY = "Any"

DEFAULT_STAFF = ["Candice", "Vinnie", "Annette", "Bonnie", "Naomi"]

# Password for the "Manage jobs" admin panel below. This only hides the
# panel from casual browsing — it's checked in this script, which anyone
# with repo access can read, so it isn't real security (same tradeoff as
# the anon Supabase key this whole page already ships with).
ADMIN_PASSWORD = "secret2026"

# This list is only the fallback used before the checklist_categories
# Supabase table has been migrated to (see supabase_schema_categories.sql)
# or if it can't be reached — once that table is live it's the source of
# truth, and sections added/renamed/removed via the admin panel live there
# instead (same story as DEFAULT_TASKS / checklist_tasks below).
DEFAULT_CATEGORIES = [
    {"id": "startday", "title": "Start of Day", "safety": False, "sort_order": 0},
    {"id": "email", "title": "Email Monitoring", "safety": False, "sort_order": 1},
    {"id": "allocation", "title": "Allocation Process", "safety": False, "sort_order": 2},
    {"id": "entry-meeting", "title": "Entry Meeting Follow-Up", "safety": False, "sort_order": 3},
    {"id": "new-student", "title": "New Student Process", "safety": False, "sort_order": 4},
    {"id": "end-student", "title": "End of Student Process", "safety": False, "sort_order": 5},
    {"id": "phone", "title": "Phone Management", "safety": False, "sort_order": 6},
    {"id": "taxi", "title": "Taxi Bookings", "safety": False, "sort_order": 7},
    {"id": "trt", "title": "TRT Payroll", "safety": False, "sort_order": 8},
    {"id": "medication", "title": "Medication", "safety": False, "sort_order": 9},
    {"id": "bulletin", "title": "Daily Bulletin Screen", "safety": False, "sort_order": 10},
    {"id": "foodbank", "title": "Food Bank & Kickstart", "safety": False, "sort_order": 11},
    {"id": "hazards", "title": "Hazard Management", "safety": True, "sort_order": 12},
    {"id": "ventia", "title": "Ventia", "safety": False, "sort_order": 13},
    {"id": "endday", "title": "End of Day", "safety": False, "sort_order": 14},
]

# task keys: id, category_id, text, sso (legacy — no longer read or edited
# from this page; superseded by the per-person "Admin hours" panel below),
# frequency ("daily"/"weekly"), weekday ("Mon".."Fri" or None — only
# meaningful when frequency == "weekly"), sort_order.
#
# This flat list is only the fallback used before the checklist_tasks
# Supabase table has been migrated to (see supabase_schema_tasks.sql) or if
# it can't be reached — once that table is live it's the source of truth,
# and jobs added/edited/removed via the admin panel live there instead.
DEFAULT_TASKS = [
    {"id": "startday-1", "category_id": "startday", "text": "Take the phones off the night switch", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "startday-2", "category_id": "startday", "text": "Check voicemail", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},
    {"id": "startday-3", "category_id": "startday", "text": "Check email", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 3},
    {"id": "startday-4", "category_id": "startday", "text": "Set up the staffroom bulletin display", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 4},

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

    {"id": "newstu-1", "category_id": "new-student", "text": "Notify schools of the allocation outcome", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "newstu-2", "category_id": "new-student", "text": "Update the allocation Excel database", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},
    {"id": "newstu-3", "category_id": "new-student", "text": "Add the student to the Student Register", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 3},
    {"id": "newstu-4", "category_id": "new-student", "text": "Create the student's OneDrive folder and save the referral documents in it", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 4},
    {"id": "newstu-5", "category_id": "new-student", "text": "Set the student's enrolment dates and attendance/absence tracking in the Behaviour Support tool (Analysis section)", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 5},

    {"id": "endstu-1", "category_id": "end-student", "text": "Verify all six portal tools have documents saved to the Document Archive (Communication Log, Behaviour Support, SMARTAR Goals, Interval Support Tracker, Sensory Overview, Safety & Risk Plan)", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "endstu-2", "category_id": "end-student", "text": "Move the student's folder to the Document Archive", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},
    {"id": "endstu-3", "category_id": "end-student", "text": "Save a copy to OneDrive and print a physical copy for filing", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 3},

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

    {"id": "endday-1", "category_id": "endday", "text": "Put the phones onto the night switch", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 1},
    {"id": "endday-2", "category_id": "endday", "text": "Put the vehicles down the driveway", "sso": None, "frequency": "daily", "weekday": None, "sort_order": 2},
]


def grouped_categories(tasks_flat, categories):
    """Group a flat task list under the given categories list, in display +
    sort order. `categories` is normally whatever load_categories() returns
    for this run — pass it explicitly rather than a module-level constant
    so newly-created sections show up without a code change."""
    out = []
    for cd in sorted(categories, key=lambda c: c.get("sort_order", 0)):
        cat_tasks = sorted(
            (t for t in tasks_flat if t["category_id"] == cd["id"]),
            key=lambda t: t.get("sort_order", 0),
        )
        out.append({"id": cd["id"], "title": cd["title"], "safety": cd["safety"], "tasks": cat_tasks})
    return out


def applicable_day_keys(task):
    """Which weekday keys a job's roster spans: all 5 weekdays for a daily
    job, just its fixed day for a weekly job that has one, or the single
    WEEKDAY_ANY sentinel for a weekly job with no fixed day."""
    if task["frequency"] == "daily":
        return WEEKDAY_COLS[:]
    if task["weekday"]:
        return [task["weekday"]]
    return [WEEKDAY_ANY]


def get_responsible(roster, task_id, day_key):
    """roster is the {task_id: {weekday: [staff_name, ...]}} shape returned
    by load_roster() — returns the (possibly empty) list of names responsible
    for a job on a given day key."""
    return roster.get(task_id, {}).get(day_key, [])


def day_key_for_today(task, ref_date):
    """Which single day key applies to `task` on `ref_date` — None for a
    daily job on a weekend (nothing to show), the job's fixed weekday for
    a weekly job that has one, or WEEKDAY_ANY otherwise."""
    if task["frequency"] == "daily":
        dow = ref_date.weekday()  # Mon=0..Sun=6
        if dow > 4:
            return None
        return WEEKDAY_COLS[dow]
    if task["weekday"]:
        return task["weekday"]
    return WEEKDAY_ANY


def is_viewed_responsible(task, roster, ref_date, viewing_staff):
    """Whether `task` is one of the viewed person's jobs on ref_date —
    always True when nobody's selected (viewing "Everyone"). Shared by the
    Today and This Week tabs so the same "Viewing" pick filters both."""
    if not viewing_staff:
        return True
    day_key = day_key_for_today(task, ref_date)
    if not day_key:
        return False
    return viewing_staff in get_responsible(roster, task["id"], day_key)

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

ADMIN_DEADLINE = time(14, 45)  # 2:45pm


def is_past_admin_deadline():
    """A daily job still unticked after this time flags itself on the
    Today tab — matches the old admin-hours afternoon cutoff."""
    return datetime.now().time() >= ADMIN_DEADLINE


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


def load_roster():
    """{ task_id: { weekday: [staff_name, ...] } } — who's responsible for a
    job, day by day. Multiple names under the same (task_id, weekday) means
    shared responsibility that day."""
    if not sb:
        return {}
    try:
        res = sb.table("checklist_duty_roster").select("task_id, weekday, staff_name").execute()
        out = {}
        for r in (res.data or []):
            out.setdefault(r["task_id"], {}).setdefault(r["weekday"], []).append(r["staff_name"])
        return out
    except Exception:
        return {}


def load_staff_hours():
    """{ staff_name: { weekday: "8:00–9:00am & 2:45–4:00pm" } } — the hours
    that person is picking up admin jobs that day, set from the "Admin
    hours" panel. A missing day means no admin hours set for them then."""
    if not sb:
        return {}
    try:
        res = sb.table("checklist_staff_hours").select("staff_name, weekday, hours").execute()
        out = {}
        for r in (res.data or []):
            out.setdefault(r["staff_name"], {})[r["weekday"]] = r["hours"]
        return out
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


def load_categories():
    """Flat list of section dicts (id, title, safety, sort_order) —
    checklist_categories is the source of truth once it has rows in it;
    falls back to the built-in DEFAULT_CATEGORIES if the table is empty
    (not migrated to yet) or unreachable."""
    if not sb:
        return [dict(c) for c in DEFAULT_CATEGORIES]
    try:
        res = (
            sb.table("checklist_categories")
            .select("id, title, safety, sort_order")
            .order("sort_order")
            .execute()
        )
        rows = res.data or []
        if not rows:
            # The table exists but is empty — most likely someone used the
            # "Add a new section" admin form before ever running
            # supabase_schema_categories.sql. Seed it with the built-in
            # defaults now so the 11 default sections don't silently
            # disappear once the table has any rows at all (this fallback
            # only kicks in while the table is EMPTY). Best-effort — this
            # run still shows the defaults either way.
            try:
                sb.table("checklist_categories").insert([dict(c) for c in DEFAULT_CATEGORIES]).execute()
            except Exception:
                pass
            return [dict(c) for c in DEFAULT_CATEGORIES]
        return rows
    except Exception:
        return [dict(c) for c in DEFAULT_CATEGORIES]


def slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "section"


def new_category_id(title, categories):
    base = slugify(title)
    cid = base
    existing_ids = {c["id"] for c in categories}
    n = 2
    while cid in existing_ids:
        cid = f"{base}-{n}"
        n += 1
    return cid


def next_category_sort_order(categories):
    existing = [c.get("sort_order", 0) for c in categories]
    return (max(existing) + 1) if existing else 1


def add_category(title, safety, categories):
    row = {
        "id": new_category_id(title, categories), "title": title,
        "safety": bool(safety), "sort_order": next_category_sort_order(categories),
    }
    if not sb:
        st.toast("Not connected to Supabase — section wasn't saved", icon="⚠️")
        return
    try:
        sb.table("checklist_categories").insert(row).execute()
    except Exception as e:
        st.toast(f"Couldn't save the new section: {e}", icon="⚠️")


def update_category(category_id, fields):
    if not sb:
        st.toast("Not connected to Supabase — change wasn't saved", icon="⚠️")
        return
    try:
        sb.table("checklist_categories").update(fields).eq("id", category_id).execute()
    except Exception as e:
        st.toast(f"Couldn't save that change: {e}", icon="⚠️")


def delete_category(category_id, tasks_flat):
    # Guard: refuse if any job still lives in this section, so we never
    # orphan a task whose category_id no longer matches any known section.
    if any(t["category_id"] == category_id for t in tasks_flat):
        return
    if not sb:
        st.toast("Not connected to Supabase — section wasn't deleted", icon="⚠️")
        return
    try:
        sb.table("checklist_categories").delete().eq("id", category_id).execute()
    except Exception as e:
        st.toast(f"Couldn't delete that section: {e}", icon="⚠️")


def next_sort_order(tasks_flat, category_id):
    existing = [t.get("sort_order", 0) for t in tasks_flat if t["category_id"] == category_id]
    return (max(existing) + 1) if existing else 1


def add_task(category_id, text, frequency, weekday, tasks_flat):
    task_id = f"{category_id}-{uuid4().hex[:8]}"
    row = {
        "id": task_id, "category_id": category_id, "text": text,
        "sso": None, "frequency": frequency,
        "weekday": weekday if frequency == "weekly" else None,
        "sort_order": next_sort_order(tasks_flat, category_id),
    }
    if not sb:
        st.toast("Not connected to Supabase — job wasn't saved", icon="⚠️")
        return
    try:
        sb.table("checklist_tasks").insert(row).execute()
    except Exception as e:
        st.toast(f"Couldn't save the new job: {e}", icon="⚠️")


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
        st.toast("Not connected to Supabase — job wasn't deleted", icon="⚠️")
        return
    try:
        sb.table("checklist_completions").delete().eq("task_id", task_id).execute()
        sb.table("checklist_duty_roster").delete().eq("task_id", task_id).execute()
        sb.table("checklist_tasks").delete().eq("id", task_id).execute()
    except Exception as e:
        st.toast(f"Couldn't delete that job: {e}", icon="⚠️")


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


def add_roster_entry(task_id, weekday, staff_name):
    if not sb:
        st.toast("Not connected to Supabase — change wasn't saved", icon="⚠️")
        return
    try:
        sb.table("checklist_duty_roster").insert(
            {"task_id": task_id, "weekday": weekday, "staff_name": staff_name}
        ).execute()
    except Exception as e:
        st.toast(f"Couldn't save the roster change: {e}", icon="⚠️")


def remove_roster_entry(task_id, weekday, staff_name):
    if not sb:
        st.toast("Not connected to Supabase — change wasn't saved", icon="⚠️")
        return
    try:
        sb.table("checklist_duty_roster").delete().eq("task_id", task_id).eq("weekday", weekday).eq(
            "staff_name", staff_name
        ).execute()
    except Exception as e:
        st.toast(f"Couldn't save the roster change: {e}", icon="⚠️")


def set_staff_hours(name, weekday, hours):
    if not sb:
        st.toast("Not connected to Supabase — hours weren't saved", icon="⚠️")
        return
    try:
        if hours:
            sb.table("checklist_staff_hours").upsert(
                {"staff_name": name, "weekday": weekday, "hours": hours},
                on_conflict="staff_name,weekday",
            ).execute()
        else:
            sb.table("checklist_staff_hours").delete().eq("staff_name", name).eq("weekday", weekday).execute()
    except Exception as e:
        st.toast(f"Couldn't save those hours: {e}", icon="⚠️")


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
        sb.table("checklist_duty_roster").delete().eq("staff_name", name).execute()
        sb.table("checklist_staff_hours").delete().eq("staff_name", name).execute()
        sb.table("checklist_staff").delete().eq("name", name).execute()
    except Exception as e:
        st.toast(f"Couldn't remove name: {e}", icon="⚠️")


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "current_user": None,
        "week_offset": 0,
        "show_staff_panel": False,
        "show_hours_panel": False,
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
    page_title="Admin Jobs Checklist | LBU",
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
  .badge-freq {{ background:{GREY_LIGHT}; color:#5C6B74; }}
  .badge-done {{ background:#d1fae5; color:#065f46; }}
  .badge-overdue {{ background:{AMBER}; color:white; }}
  .badge-assignee {{ background:{GREY_LIGHT}; color:#5C6B74; }}
  .badge-assignee-shared {{ background:{TEAL_LIGHT}; color:{TEAL}; }}
  .badge-assignee-unassigned {{ background:{GREY_LIGHT}; color:#98a2ac; font-style:italic; }}

  /* Once ticked for the day, a job visually recedes... */
  .job-row-done {{ opacity:0.55; }}
  /* ...but a daily job still sitting untouched after the 2:45pm cutoff
     flags itself instead, so it doesn't quietly get missed. */
  .job-row-overdue {{ background:{AMBER_LIGHT}; border-radius:6px; padding:4px 8px; margin:-4px -8px; }}

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

# Reset the "Add a job" form fields on the run after a successful add —
# must happen before those widgets are instantiated below (see the note in
# the "Add job" button handler further down for why this can't happen
# in the same run as the click).
if st.session_state.get("_clear_admin_form"):
    st.session_state["admin_new_text"] = ""
    st.session_state["admin_new_freq"] = "Daily"
    st.session_state.pop("admin_new_weekday", None)
    st.session_state["_clear_admin_form"] = False

# Same defer-to-next-run trick as above, for the "Add a new section" form.
if st.session_state.get("_clear_admin_section_form"):
    st.session_state["admin_new_section_title"] = ""
    st.session_state["admin_new_section_safety"] = False
    st.session_state["_clear_admin_section_form"] = False

if st_autorefresh:
    # Near-live updates across users without a manual refresh. Optional —
    # `pip install streamlit-autorefresh` to enable; degrades silently
    # without it (see the try/except import at the top of this file).
    st_autorefresh(interval=20_000, key="checklist_autorefresh")

st.markdown(f"""
<div class="clc-header">
  <div><h1>✅ Admin Jobs Checklist</h1>
  <p>Cowandilla Learning Centre — LBU Portal Tool</p></div>
  <span class="clc-badge">{"SUPABASE CONNECTED" if sb else "OFFLINE — CHECK CONNECTION"}</span>
</div>""", unsafe_allow_html=True)

staff = load_staff()

# ── Identity ─────────────────────────────────────────────────────────────
if st.session_state.current_user:
    id_col1, id_col2, id_col3, id_col4, id_col5 = st.columns([3, 1, 1, 1, 1])
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
        if st.button("🕐 Admin hours", use_container_width=True):
            st.session_state.show_hours_panel = not st.session_state.show_hours_panel
    with id_col5:
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

if st.session_state.show_hours_panel:
    with st.expander("🕐 Admin hours", expanded=True):
        st.caption(
            "Set the hours each person is doing admin jobs, day by day — e.g. "
            "\"8:00–9:00am & 2:45–4:00pm\" most days but \"8:00am–4:00pm\" on "
            "Wednesday. Leave a day blank if they're not doing admin that day. "
            "Saves straight to Supabase and shows up next to their name when "
            "you pick them under \"Viewing jobs for\"."
        )
        hours_staff = load_staff()
        current_hours = load_staff_hours()
        if not hours_staff:
            st.caption("Add staff names first (Manage staff) before setting their admin hours.")
        else:
            hhead = st.columns([2] + [2] * len(WEEKDAY_COLS))
            hhead[0].markdown("**Name**")
            for i, day in enumerate(WEEKDAY_COLS):
                hhead[i + 1].markdown(f"**{day}**")
            for name in hours_staff:
                hrow = st.columns([2] + [2] * len(WEEKDAY_COLS))
                hrow[0].write(name)
                for i, day in enumerate(WEEKDAY_COLS):
                    existing = current_hours.get(name, {}).get(day, "")
                    picked = hrow[i + 1].text_input(
                        f"{name} {day} admin hours", value=existing, placeholder="—",
                        key=f"hours_{name}_{day}", label_visibility="collapsed",
                    )
                    if picked.strip() != existing:
                        set_staff_hours(name, day, picked.strip())
                        st.rerun()

# ── Admin: job management (password-gated, Supabase-backed) ───────────────
# See the ADMIN_PASSWORD note above the constant — this is a "don't show
# this to everyone" gate, not real security.
if st.session_state.show_admin_login and not st.session_state.admin_unlocked:
    with st.expander("🔒 Admin access", expanded=True):
        st.caption("Enter the admin password to add, edit, or remove jobs.")
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
    with st.expander("🛠️ Manage jobs", expanded=True):
        st.caption(
            "Add a new job to any section below, or edit and remove ones already listed. "
            "Changes save straight to Supabase for everyone."
        )
        admin_tasks = load_tasks()
        admin_categories = load_categories()
        admin_roster = load_roster()
        admin_staff = load_staff()

        st.markdown("**Sections**")
        for cat in sorted(admin_categories, key=lambda c: c.get("sort_order", 0)):
            duty_count = sum(1 for t in admin_tasks if t["category_id"] == cat["id"])
            sc1, sc2, sc3, sc4 = st.columns([3, 2, 1, 1])
            edited_title = sc1.text_input(
                "Section name", value=cat["title"], key=f"cat_title_{cat['id']}", label_visibility="collapsed"
            )
            edited_safety = sc2.checkbox(
                "Highlight as safety", value=cat["safety"], key=f"cat_safety_{cat['id']}"
            )
            sc3.markdown(f"{duty_count} " + ("job" if duty_count == 1 else "jobs"))

            confirm_cat_key = f"confirm_delcat_{cat['id']}"
            if duty_count > 0:
                sc4.button("Delete", key=f"delcat_{cat['id']}", use_container_width=True, disabled=True,
                           help="Move or delete this section's jobs first")
            elif st.session_state.get(confirm_cat_key):
                if sc4.button("Confirm?", key=f"delcatc_{cat['id']}", use_container_width=True):
                    delete_category(cat["id"], admin_tasks)
                    st.session_state.pop(confirm_cat_key, None)
                    st.rerun()
            else:
                if sc4.button("Delete", key=f"delcat_{cat['id']}", use_container_width=True):
                    st.session_state[confirm_cat_key] = True
                    st.rerun()

            if edited_title.strip() and edited_title.strip() != cat["title"]:
                update_category(cat["id"], {"title": edited_title.strip()})
                st.rerun()
            if edited_safety != cat["safety"]:
                update_category(cat["id"], {"safety": edited_safety})
                st.rerun()

        st.markdown("**Add a new section**")
        nsc1, nsc2, nsc3 = st.columns([3, 2, 1])
        new_section_title = nsc1.text_input(
            "New section name", key="admin_new_section_title",
            placeholder="e.g. Excursions", label_visibility="collapsed",
        )
        new_section_safety = nsc2.checkbox("Highlight as safety", key="admin_new_section_safety")
        if nsc3.button("Add section", key="admin_add_section_btn", use_container_width=True):
            if new_section_title.strip():
                add_category(new_section_title.strip(), new_section_safety, admin_categories)
                # Same next-run clearing trick as the "Add a job" form below.
                st.session_state["_clear_admin_section_form"] = True
                st.rerun()

        st.markdown("---")
        st.markdown("**Add a job**")
        new_text = st.text_input("Job text", key="admin_new_text", placeholder="e.g. Print the visitor sign-in sheet")
        ac1, ac2, ac3 = st.columns(3)
        cat_titles_sorted = [c["title"] for c in sorted(admin_categories, key=lambda c: c.get("sort_order", 0))]
        new_cat_title = ac1.selectbox("Section", cat_titles_sorted, key="admin_new_cat")
        new_freq = ac2.selectbox("Frequency", ["Daily", "Weekly"], key="admin_new_freq")
        new_weekday = None
        if new_freq == "Weekly":
            new_weekday_pick = ac3.selectbox("Fixed day", ["No fixed day"] + WEEKDAY_COLS, key="admin_new_weekday")
            new_weekday = None if new_weekday_pick == "No fixed day" else new_weekday_pick
        else:
            ac3.markdown("&nbsp;", unsafe_allow_html=True)

        if st.button("Add job", key="admin_add_btn"):
            if new_text.strip():
                new_cat_id = next(c["id"] for c in admin_categories if c["title"] == new_cat_title)
                add_task(new_cat_id, new_text.strip(), new_freq.lower(), new_weekday, admin_tasks)
                # Streamlit won't let a widget's session_state be changed in
                # the same run after it's been instantiated — set a flag and
                # clear the form on the next run instead, before those
                # widgets are created (see the top of the script).
                st.session_state["_clear_admin_form"] = True
                st.rerun()

        st.markdown("---")
        st.markdown("**Jobs**")
        for cat in grouped_categories(admin_tasks, admin_categories):
            if not cat["tasks"]:
                continue
            st.markdown(f'<div class="sec-head">{cat["title"]}</div>', unsafe_allow_html=True)
            for t in cat["tasks"]:
                dr1, dr2, dr3, dr4 = st.columns([4, 1.2, 1, 1])
                edited_text = dr1.text_input(
                    "Job text", value=t["text"], key=f"dtext_{t['id']}", label_visibility="collapsed"
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

                confirm_key = f"confirm_del_{t['id']}"
                if st.session_state.get(confirm_key):
                    if dr4.button("Confirm?", key=f"delc_{t['id']}", use_container_width=True):
                        delete_task(t["id"])
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                else:
                    if dr4.button("Delete", key=f"del_{t['id']}", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()

                changed = (
                    edited_text.strip() and edited_text.strip() != t["text"]
                    or freq_val != t["frequency"]
                    or weekday_val != t["weekday"]
                )
                if changed:
                    update_task(t["id"], {
                        "text": edited_text.strip() or t["text"],
                        "frequency": freq_val, "weekday": weekday_val,
                    })
                    st.rerun()

                with st.expander(f"Roster — who's responsible for \"{t['text'][:60]}\"", expanded=False):
                    if not admin_staff:
                        st.caption("Add staff names first.")
                    else:
                        for day_key in applicable_day_keys(t):
                            day_label = "Any day this week" if day_key == WEEKDAY_ANY else day_key
                            current_resp = get_responsible(admin_roster, t["id"], day_key)
                            picked_resp = st.multiselect(
                                day_label,
                                admin_staff,
                                default=[n for n in current_resp if n in admin_staff],
                                key=f"roster_{t['id']}_{day_key}",
                            )
                            if set(picked_resp) != set(current_resp):
                                for n in picked_resp:
                                    if n not in current_resp:
                                        add_roster_entry(t["id"], day_key, n)
                                for n in current_resp:
                                    if n not in picked_resp:
                                        remove_roster_entry(t["id"], day_key, n)
                                st.rerun()

st.markdown("---")

# "Viewing" is a separate picker from the signed-in identity — anyone can
# look at anyone's jobs, on either tab below, without switching who they're
# signed in as. It lives once here, above the tabs, so the same person you
# pick stays selected whether you're looking at Today or This Week. Reset
# it before the widget is instantiated if the previously-viewed person is
# no longer on staff (same defer-to-next-run pattern used for the admin
# forms above).
viewing_staff_names = load_staff()
viewing_options = ["Everyone"] + viewing_staff_names
if st.session_state.get("week_viewing") not in viewing_options:
    st.session_state["week_viewing"] = "Everyone"
vwcol1, vwcol2 = st.columns([1, 4])
with vwcol1:
    st.markdown("**Viewing jobs for:**")
with vwcol2:
    viewing_pick = st.selectbox(
        "Viewing", viewing_options, key="week_viewing", label_visibility="collapsed"
    )
viewing_staff = None if viewing_pick == "Everyone" else viewing_pick

# Shows the viewed person's admin hours (from the "Admin hours" panel)
# right under the picker, so choosing a name also tells you when they're
# actually rostered on for admin — e.g. someone's narrower morning/
# afternoon windows, longer on a particular day.
if viewing_staff:
    hours_for_viewed = load_staff_hours().get(viewing_staff, {})
    hour_parts = [f"{day} {hours_for_viewed[day]}" for day in WEEKDAY_COLS if hours_for_viewed.get(day)]
    if hour_parts:
        st.caption("🕐 " + viewing_staff + "'s admin hours: " + " · ".join(hour_parts))
    else:
        st.caption(f'No admin hours set yet for {viewing_staff} — add them from "Admin hours" above.')

# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_checklist, tab_week = st.tabs(["📋 Today", "📅 This Week"], key="main_tabs")

# ── Today tab ───────────────────────────────────────────────────────────────
with tab_checklist:
    roster = load_roster()
    completions = load_completions()
    checklist_tasks_flat = load_tasks()
    checklist_categories = load_categories()
    today = date.today()

    total_tasks, done_tasks = 0, 0
    for cat in grouped_categories(checklist_tasks_flat, checklist_categories):
        for t in cat["tasks"]:
            if not is_viewed_responsible(t, roster, today, viewing_staff):
                continue
            total_tasks += 1
            if period_key_for(t, today) in completions.get(t["id"], {}):
                done_tasks += 1
    st.progress(done_tasks / total_tasks if total_tasks else 0,
                text=f"{done_tasks}/{total_tasks} done today")
    st.caption(
        "Daily / Weekly badges show how often a job comes around. See \"Admin hours\" above for who's picking up "
        "admin jobs, and when. A daily job still unticked after 2:45pm flags itself ⚠ Overdue; ticking a job off fades it out."
    )

    ctrl1, ctrl2 = st.columns([2, 3])
    with ctrl1:
        if st.button("Clear today's ticks"):
            for cat in grouped_categories(checklist_tasks_flat, checklist_categories):
                for t in cat["tasks"]:
                    key = period_key_for(t, today)
                    if key in completions.get(t["id"], {}):
                        set_done(t["id"], key, False, st.session_state.current_user)
            st.rerun()
    with ctrl2:
        if st.button("🔄 Refresh now"):
            st.rerun()

    for cat in grouped_categories(checklist_tasks_flat, checklist_categories):
        tasks = cat["tasks"]
        if viewing_staff:
            tasks = [t for t in tasks if is_viewed_responsible(t, roster, today, viewing_staff)]
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
            # Only daily jobs have a same-day deadline — a weekly job due
            # "any time this week" shouldn't flag as overdue every single
            # afternoon.
            overdue = t["frequency"] == "daily" and not checked and is_past_admin_deadline()

            row = st.columns([0.5, 5, 2])
            new_val = row[0].checkbox("", value=checked, key=f"chk_{t['id']}", label_visibility="collapsed")

            badges = f'<span class="task-badge badge-freq">{freq_badge_text(t)}</span>'
            if overdue:
                badges += '<span class="task-badge badge-overdue">⚠ Overdue</span>'
            if comp:
                badges += f'<span class="task-badge badge-done">Done by {comp["by"]} · {format_time(comp["at"])}</span>'
            row_cls = "job-row-overdue" if overdue else ("job-row-done" if checked else "")
            row_body = f'{t["text"]}<br/>{badges}'
            # Only wrap in a styling <div> when there's actually a class to
            # apply -- an outer block-level element (even an empty-class
            # one) stops Streamlit from auto-wrapping the text in its usual
            # <p>, which would otherwise be a needless DOM/structure change
            # for the common (not-overdue, not-done) row.
            if row_cls:
                row_body = f'<div class="{row_cls}">{row_body}</div>'
            row[1].markdown(row_body, unsafe_allow_html=True)

            # Read-only "who's on this today" badge — responsibility is set
            # per-weekday from the "Manage jobs" admin panel's Roster
            # editor, not edited inline here.
            today_day_key = day_key_for_today(t, today)
            responsible_today = get_responsible(roster, t["id"], today_day_key) if today_day_key else []
            if not responsible_today:
                assignee_html = '<span class="task-badge badge-assignee-unassigned">Unassigned</span>'
            elif len(responsible_today) > 1:
                assignee_html = f'<span class="task-badge badge-assignee-shared">{" & ".join(responsible_today)}</span>'
            else:
                assignee_html = f'<span class="task-badge badge-assignee">{responsible_today[0]}</span>'
            row[2].markdown(assignee_html, unsafe_allow_html=True)

            if new_val != checked:
                set_done(t["id"], key, new_val, st.session_state.current_user or "Unknown")
                st.rerun()

# ── This Week tab ────────────────────────────────────────────────────────────
with tab_week:
    roster = load_roster()
    completions = load_completions()
    week_tasks_flat = load_tasks()
    week_categories = load_categories()
    # viewing_staff comes from the shared "Viewing" picker above the tabs —
    # same selection as the Today tab, so switching tabs doesn't lose it.

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

    for cat in grouped_categories(week_tasks_flat, week_categories):
        pinned = [t for t in cat["tasks"] if t["frequency"] == "daily" or (t["frequency"] == "weekly" and t["weekday"])]
        any_day = [t for t in cat["tasks"] if t["frequency"] == "weekly" and not t["weekday"]]
        any_day_tasks.extend((cat, t) for t in any_day)
        if not pinned:
            continue

        cat_header_shown = False
        for t in pinned:
            day_infos = []
            for d in week_dates:
                col_short = WEEKDAY_COLS[d.weekday()]
                applies = t["frequency"] == "daily" or t["weekday"] == col_short
                responsible = get_responsible(roster, t["id"], col_short) if applies else []
                day_infos.append({"date": d, "applies": applies, "responsible": responsible})

            if viewing_staff:
                relevant = any(di["applies"] and viewing_staff in di["responsible"] for di in day_infos)
                if not relevant:
                    continue

            if not cat_header_shown:
                st.markdown(f'<div class="sec-head">{cat["title"]}</div>', unsafe_allow_html=True)
                cat_header_shown = True

            row = st.columns([3, 1, 1, 1, 1, 1])
            week_roster_union = []
            for di in day_infos:
                for n in di["responsible"]:
                    if n not in week_roster_union:
                        week_roster_union.append(n)
            label = t["text"] + (f"  ·  *{' & '.join(week_roster_union)}*" if week_roster_union else "")
            row[0].markdown(label)

            for i, di in enumerate(day_infos):
                viewer_blocked = viewing_staff and viewing_staff not in di["responsible"]
                if not di["applies"] or viewer_blocked:
                    row[i + 1].markdown("—")
                else:
                    key = period_key_for(t, di["date"])
                    comp = completions.get(t["id"], {}).get(key)
                    checked = comp is not None
                    help_parts = []
                    if comp:
                        help_parts.append(f"Done by {comp['by']} · {format_time(comp['at'])}")
                    if di["responsible"]:
                        help_parts.append("Responsible: " + " & ".join(di["responsible"]))
                    new_val = row[i + 1].checkbox(
                        "", value=checked, key=f"wk_{t['id']}_{key}",
                        label_visibility="collapsed",
                        help=" — ".join(help_parts) if help_parts else None,
                    )
                    if viewing_staff:
                        others = [n for n in di["responsible"] if n != viewing_staff]
                        if others:
                            # A leading "+ " reads as a Markdown bullet list
                            # marker (stripped from the rendered text) —
                            # parenthesise it instead so the "+" survives.
                            row[i + 1].caption("(+ " + ", ".join(others) + ")")
                    if new_val != checked:
                        set_done(t["id"], key, new_val, st.session_state.current_user or "Unknown")
                        st.rerun()

    filtered_any_day = []
    for cat, t in any_day_tasks:
        responsible = get_responsible(roster, t["id"], WEEKDAY_ANY)
        if viewing_staff and viewing_staff not in responsible:
            continue
        filtered_any_day.append((cat, t, responsible))

    if filtered_any_day:
        st.markdown('<div class="sec-head">Weekly (any day this week)</div>', unsafe_allow_html=True)
        for cat, t, responsible in filtered_any_day:
            key = period_key_for(t, monday)
            comp = completions.get(t["id"], {}).get(key)
            checked = comp is not None
            c1, c2 = st.columns([6, 1])
            if viewing_staff:
                others = [n for n in responsible if n != viewing_staff]
                suffix = f"  ·  *+ {', '.join(others)}*" if others else ""
            else:
                suffix = f"  ·  *{' & '.join(responsible)}*" if responsible else ""
            label = f'{cat["title"]} — {t["text"]}' + suffix
            c1.markdown(label)
            new_val = c2.checkbox("", value=checked, key=f"anyday_{t['id']}", label_visibility="collapsed")
            if new_val != checked:
                set_done(t["id"], key, new_val, st.session_state.current_user or "Unknown")
                st.rerun()

st.markdown("---")
st.caption(
    "Ticks, rosters, admin hours, and job changes save straight to Supabase and are shared with anyone who opens this page "
    "(refresh, or wait ~20s if streamlit-autorefresh is installed, to see others' changes). "
    "\"Clear today's ticks\" only clears the current day/week — past history stays on the This Week tab."
)
