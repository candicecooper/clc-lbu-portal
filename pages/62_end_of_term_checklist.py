"""
62_end_of_term_checklist.py
----------------------------
End of Term actions checklist for CLC-LBU staff portal.

Landing page is deliberately minimal: pick your name (or go to Admin).
Once a name is picked, the page opens straight to that person's checklist,
split into two clearly labelled sections:
  1. Jobs everyone is expected to complete (the standard checklist)
  2. Your allocated jobs (the shared additional-jobs list, highlighting
     what's assigned to you, with the option to pick up more)
...then a sign-off section that requires everything to be ticked before
signing (or a Leadership-agreed override from Admin).

Admin (password protected) manages staff, jobs, term status and assignments,
and can see an overview of who's done what.

Requires a Supabase project with the tables in eot_checklist_schema.sql.
Uses st.secrets["SUPABASE_URL"] / st.secrets["SUPABASE_KEY"] (same pattern as
the rest of the portal). Admin password defaults to "secret2026" — set
st.secrets["EOT_ADMIN_PASSWORD"] to override it.
"""

import time
from datetime import datetime, timezone

import streamlit as st
import httpx
from supabase import create_client

try:
    import httpcore
except ImportError:  # pragma: no cover - httpcore ships as an httpx dependency
    httpcore = None

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="End of Term Checklist", page_icon="✅", layout="centered")

ADMIN_PASSWORD_DEFAULT = "secret2026"

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

sb = get_supabase()

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3, .eot-brand {
    font-family: 'Poppins', 'Inter', sans-serif !important;
}

:root {
    --eot-primary: #1F6F6B;
    --eot-primary-dark: #14504D;
    --eot-accent: #E8935B;
    --eot-bg: #FAF7F2;
    --eot-card: #FFFFFF;
    --eot-text: #22323B;
    --eot-muted: #6B7B80;
    --eot-border: #E4E0D6;
}

.stApp {
    background: var(--eot-bg);
}

.eot-hero {
    background: linear-gradient(135deg, var(--eot-primary) 0%, var(--eot-primary-dark) 100%);
    color: white;
    padding: 1.8rem 1.6rem;
    border-radius: 18px;
    margin-bottom: 1.6rem;
    box-shadow: 0 6px 18px rgba(20, 80, 77, 0.25);
}
.eot-hero h1 {
    color: white !important;
    margin: 0 0 0.2rem 0;
    font-size: 1.6rem;
}
.eot-hero p {
    color: #DDEDEB;
    margin: 0;
    font-size: 0.95rem;
}

.eot-section-label {
    display: inline-block;
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--eot-primary-dark);
    background: #E4F1EF;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    margin-bottom: 0.6rem;
}
.eot-section-label.allocated {
    color: #8A4B1F;
    background: #FBE7D6;
}
.eot-section-sub {
    color: var(--eot-muted);
    font-size: 0.88rem;
    margin-top: -0.4rem;
    margin-bottom: 0.8rem;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--eot-card);
    border: 1px solid var(--eot-border) !important;
    border-radius: 14px !important;
    padding: 0.2rem 0.4rem;
}

.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    border: none;
}
.stButton > button[kind="primary"] {
    background: var(--eot-primary);
}
.stButton > button[kind="primary"]:hover {
    background: var(--eot-primary-dark);
}

.stProgress > div > div > div > div {
    background-color: var(--eot-primary);
}

div[data-baseweb="select"] > div {
    border-radius: 10px;
}

.eot-signed-badge {
    display: inline-block;
    background: #E4F1EF;
    color: var(--eot-primary-dark);
    padding: 0.5rem 0.9rem;
    border-radius: 10px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# Transient network errors between Render and Supabase (dropped HTTP/2
# connections, "Resource temporarily unavailable", etc.) happen occasionally
# and aren't caused by anything wrong with the data. Retry a couple of times
# before giving up, so a checkbox click or a page load doesn't crash on a
# one-off blip.
_TRANSIENT_ERRORS = tuple(
    e for e in [
        getattr(httpx, "ReadError", None),
        getattr(httpx, "ConnectError", None),
        getattr(httpx, "RemoteProtocolError", None),
        getattr(httpx, "TimeoutException", None),
        getattr(httpx, "NetworkError", None),
        getattr(httpcore, "ReadError", None) if httpcore else None,
        getattr(httpcore, "ConnectError", None) if httpcore else None,
    ] if e is not None
)

def _run(query, retries=2, delay=0.6):
    """Execute a Supabase query builder, retrying on transient network errors."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return query.execute()
        except _TRANSIENT_ERRORS as e:
            last_exc = e
            if attempt < retries:
                time.sleep(delay)
                continue
    st.error(
        "Lost connection to the database for a moment — this is usually just a "
        "network blip. Please try again in a few seconds (refresh the page if "
        "it keeps happening)."
    )
    st.stop()
    raise last_exc  # unreachable, keeps linters happy

# Admin gate — tries the portal's shared staff_auth module first (in case
# Candice wants to switch this tool over to it later), otherwise uses the
# password below. Different portal tools may call the gate function
# different things, so a few common names are tried before falling back.
def admin_gate() -> bool:
    try:
        import staff_auth
        for fn_name in ("check_password", "verify_password", "authenticate",
                         "staff_login", "require_staff_password", "password_gate",
                         "login", "check_staff_password", "require_login"):
            fn = getattr(staff_auth, fn_name, None)
            if callable(fn):
                return fn()
    except ImportError:
        pass

    pw = st.text_input("Admin password", type="password", key="eot_admin_pw")
    correct = st.secrets.get("EOT_ADMIN_PASSWORD", ADMIN_PASSWORD_DEFAULT)
    return pw == correct

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Default job lists — from the CLC-LBU paper "End of Term actions" checklist.
# These can be loaded into a term via the Admin tab, and edited/added to
# freely afterwards — they're just a starting point, not fixed.
# ---------------------------------------------------------------------------

DEFAULT_STANDARD_JOBS = [
    "All communication with parents uploaded to EMS",
    "Program Notebooks all up to date",
    "Checklists for each student up to date",
    "EMS attendance updated",
    "Classroom is clean (surface tops clear)",
    "Spill out is clean and organised - items stored away",
    "Program phones are locked away in Admin Safe",
    "Classroom door, light and heater turned off and locked",
    "Own absences are entered on to Edi",
    "Desk in planning room cleared and items in cupboard",
    "Laptops locked away if not taken home",
    "Term database entered on OneNote",
    "Staff kitchen fridge/freezer - take home anything you don't want thrown out",
    "Walkie talkies on charge",
]

DEFAULT_ADDITIONAL_JOBS = [
    "Staff kitchen cleaning - fridge, benches, microwave",
    "Student kitchen pantry",
    "Student kitchen fridge - JP",
    "Student kitchen fridge - PY",
    "Student kitchen fridge - SY",
    "Van cleaning - wash, vac and fill with petrol (Friday)",
    "Kia - wash, vac and fill with petrol",
    "Teacher prep room - ensure every desk is clean and clear, all items stored in cupboards",
    "Staff kitchen - empty of all items and clean fridge and freezer",
    "Move vans to yard (Friday arvo)",
]

# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------

def get_terms():
    return _run(sb.table("eot_terms").select("*").order("id", desc=True)).data

def get_open_terms(terms=None):
    terms = terms if terms is not None else get_terms()
    return [t for t in terms if t["is_active"]]

def set_term_open(term_id, is_open):
    _run(sb.table("eot_terms").update({"is_active": is_open}).eq("id", term_id))

def create_term(label, instructions, meeting_details, copy_jobs_from_term_id=None, seed_defaults=False):
    # New terms start open for checking; existing terms are left as they are
    # (admin can close any term manually from the archive list).
    new_term = _run(sb.table("eot_terms").insert({
        "label": label,
        "instructions": instructions,
        "meeting_details": meeting_details,
        "is_active": True,
    })).data[0]

    if copy_jobs_from_term_id:
        std_jobs = _run(sb.table("eot_standard_jobs").select("*").eq("term_id", copy_jobs_from_term_id).order("order_index")).data
        for j in std_jobs:
            _run(sb.table("eot_standard_jobs").insert({
                "term_id": new_term["id"],
                "action_text": j["action_text"],
                "order_index": j["order_index"],
            }))
        add_jobs = _run(sb.table("eot_additional_jobs").select("*").eq("term_id", copy_jobs_from_term_id).order("order_index")).data
        for j in add_jobs:
            _run(sb.table("eot_additional_jobs").insert({
                "term_id": new_term["id"],
                "action_text": j["action_text"],
                "order_index": j["order_index"],
            }))
    elif seed_defaults:
        for i, text in enumerate(DEFAULT_STANDARD_JOBS):
            _run(sb.table("eot_standard_jobs").insert({"term_id": new_term["id"], "action_text": text, "order_index": i}))
        for i, text in enumerate(DEFAULT_ADDITIONAL_JOBS):
            _run(sb.table("eot_additional_jobs").insert({"term_id": new_term["id"], "action_text": text, "order_index": i}))
    return new_term

def load_default_standard_jobs(term_id):
    existing = {j["action_text"].strip().lower() for j in get_standard_jobs(term_id)}
    current_max = len(existing)
    added = 0
    for text in DEFAULT_STANDARD_JOBS:
        if text.strip().lower() not in existing:
            _run(sb.table("eot_standard_jobs").insert({"term_id": term_id, "action_text": text, "order_index": current_max + added}))
            added += 1
    return added

def load_default_additional_jobs(term_id):
    existing = {j["action_text"].strip().lower() for j in get_additional_jobs(term_id)}
    current_max = len(existing)
    added = 0
    for text in DEFAULT_ADDITIONAL_JOBS:
        if text.strip().lower() not in existing:
            _run(sb.table("eot_additional_jobs").insert({"term_id": term_id, "action_text": text, "order_index": current_max + added}))
            added += 1
    return added

def get_staff(active_only=True):
    q = sb.table("eot_staff").select("*").order("name")
    if active_only:
        q = q.eq("active", True)
    return _run(q).data

def add_staff(name):
    name = name.strip()
    existing = _run(sb.table("eot_staff").select("*").ilike("name", name)).data
    if existing:
        _run(sb.table("eot_staff").update({"active": True}).eq("id", existing[0]["id"]))
    else:
        _run(sb.table("eot_staff").insert({"name": name}))

def remove_staff(staff_id):
    _run(sb.table("eot_staff").update({"active": False}).eq("id", staff_id))

def get_standard_jobs(term_id):
    return _run(sb.table("eot_standard_jobs").select("*").eq("term_id", term_id).order("order_index")).data

def add_standard_job(term_id, text, order_index):
    _run(sb.table("eot_standard_jobs").insert({"term_id": term_id, "action_text": text, "order_index": order_index}))

def update_standard_job(job_id, text):
    _run(sb.table("eot_standard_jobs").update({"action_text": text}).eq("id", job_id))

def delete_standard_job(job_id):
    _run(sb.table("eot_standard_jobs").delete().eq("id", job_id))

def get_completions(term_id, staff_id):
    rows = _run(sb.table("eot_staff_completions").select("*").eq("term_id", term_id).eq("staff_id", staff_id)).data
    return {r["job_id"]: r for r in rows}

def set_completion(term_id, staff_id, job_id, completed):
    existing = _run(sb.table("eot_staff_completions").select("id").eq("term_id", term_id).eq("staff_id", staff_id).eq("job_id", job_id)).data
    payload = {"completed": completed, "completed_at": now_iso() if completed else None}
    if existing:
        _run(sb.table("eot_staff_completions").update(payload).eq("id", existing[0]["id"]))
    else:
        payload.update({"term_id": term_id, "staff_id": staff_id, "job_id": job_id})
        _run(sb.table("eot_staff_completions").insert(payload))

def get_signoff(term_id, staff_id):
    rows = _run(sb.table("eot_staff_signoff").select("*").eq("term_id", term_id).eq("staff_id", staff_id)).data
    return rows[0] if rows else None

def sign_off(term_id, staff_id, signature_name):
    existing = get_signoff(term_id, staff_id)
    payload = {"signed": True, "signature_name": signature_name, "signed_at": now_iso()}
    if existing:
        _run(sb.table("eot_staff_signoff").update(payload).eq("id", existing["id"]))
    else:
        payload.update({"term_id": term_id, "staff_id": staff_id})
        _run(sb.table("eot_staff_signoff").insert(payload))

def unsign(term_id, staff_id):
    existing = get_signoff(term_id, staff_id)
    if existing:
        _run(sb.table("eot_staff_signoff").update({"signed": False}).eq("id", existing["id"]))

def get_additional_jobs(term_id):
    return _run(sb.table("eot_additional_jobs").select("*").eq("term_id", term_id).order("order_index")).data

def add_additional_job(term_id, text, order_index):
    _run(sb.table("eot_additional_jobs").insert({"term_id": term_id, "action_text": text, "order_index": order_index}))

def update_additional_job(job_id, text):
    _run(sb.table("eot_additional_jobs").update({"action_text": text}).eq("id", job_id))

def delete_additional_job(job_id):
    _run(sb.table("eot_additional_assignments").delete().eq("additional_job_id", job_id))
    _run(sb.table("eot_additional_jobs").delete().eq("id", job_id))

def get_assignments(term_id):
    rows = _run(sb.table("eot_additional_assignments").select("*, eot_staff(name)").eq("term_id", term_id)).data
    by_job = {}
    for r in rows:
        by_job.setdefault(r["additional_job_id"], []).append(r)
    return by_job

def assign_staff(term_id, job_id, staff_id):
    existing = _run(sb.table("eot_additional_assignments").select("id").eq("additional_job_id", job_id).eq("staff_id", staff_id)).data
    if not existing:
        _run(sb.table("eot_additional_assignments").insert({"term_id": term_id, "additional_job_id": job_id, "staff_id": staff_id}))

def unassign_staff(job_id, staff_id):
    _run(sb.table("eot_additional_assignments").delete().eq("additional_job_id", job_id).eq("staff_id", staff_id))

def set_additional_complete(job_id, completed, by_name=""):
    payload = {"completed": completed, "completed_at": now_iso() if completed else None, "completed_by": by_name if completed else ""}
    _run(sb.table("eot_additional_jobs").update(payload).eq("id", job_id))

# ---------------------------------------------------------------------------
# Session state / navigation
# ---------------------------------------------------------------------------

if "eot_view" not in st.session_state:
    st.session_state.eot_view = "landing"
if "eot_staff_id" not in st.session_state:
    st.session_state.eot_staff_id = None
if "eot_term_id" not in st.session_state:
    st.session_state.eot_term_id = None

def go_to(view):
    st.session_state.eot_view = view
    st.rerun()

def go_home():
    st.session_state.eot_view = "landing"
    st.session_state.eot_staff_id = None
    st.session_state.eot_term_id = None
    st.rerun()

# ---------------------------------------------------------------------------
# Hero header (shown on every screen)
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="eot-hero">
        <h1>✅ End of Term Checklist</h1>
        <p>Cowandilla Learning Centre — Learning &amp; Behaviour Unit</p>
    </div>
    """,
    unsafe_allow_html=True,
)

all_terms = get_terms()
open_terms = get_open_terms(all_terms)

# ---------------------------------------------------------------------------
# Landing — just term (if needed), name, or Admin
# ---------------------------------------------------------------------------

if st.session_state.eot_view == "landing":
    if not open_terms:
        st.info("No term is currently open for checking. Check back once your admin opens one, or go to Admin below.")
        term = None
    elif len(open_terms) == 1:
        term = open_terms[0]
        st.caption(f"Open term: **{term['label']}**")
    else:
        term_label = st.selectbox("Term", [t["label"] for t in open_terms], key="landing_term")
        term = next(t for t in open_terms if t["label"] == term_label)

    staff_list = get_staff()
    name_options = ["— Select your name —"] + [s["name"] for s in staff_list]
    picked = st.selectbox("Who are you?", name_options, key="landing_who")

    if picked != "— Select your name —" and term:
        staff = next(s for s in staff_list if s["name"] == picked)
        st.session_state.eot_staff_id = staff["id"]
        st.session_state.eot_term_id = term["id"]
        go_to("staff")

    st.markdown("<div style='text-align:center; color:#9AA5A9; margin: 1.2rem 0 0.6rem;'>— or —</div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("🔐 Admin", use_container_width=True):
            go_to("admin")

# ---------------------------------------------------------------------------
# Staff view — everyone's jobs, then allocated jobs, then sign-off
# ---------------------------------------------------------------------------

elif st.session_state.eot_view == "staff":
    staff_list = get_staff()
    term = next((t for t in all_terms if t["id"] == st.session_state.eot_term_id), None)
    staff = next((s for s in staff_list if s["id"] == st.session_state.eot_staff_id), None)

    if not term or not staff:
        go_home()

    if st.button("⬅ Back"):
        go_home()

    st.markdown(f"### Hi {staff['name']} 👋")
    st.caption(term["label"])
    if term.get("instructions"):
        st.info(term["instructions"])
    if term.get("meeting_details"):
        st.markdown(f"**{term['meeting_details']}**")

    signoff = get_signoff(term["id"], staff["id"])
    is_signed = bool(signoff and signoff["signed"])

    # --- Section 1: everyone's jobs -------------------------------------
    st.markdown('<span class="eot-section-label">Everyone\'s jobs</span>', unsafe_allow_html=True)
    st.markdown('<div class="eot-section-sub">These are expected of every staff member before you leave for the holidays.</div>', unsafe_allow_html=True)

    jobs = get_standard_jobs(term["id"])
    completions = get_completions(term["id"], staff["id"])
    done_count = 0
    with st.container(border=True):
        if not jobs:
            st.caption("No standard checklist items have been set up for this term yet.")
        else:
            for job in jobs:
                existing = completions.get(job["id"])
                checked = bool(existing and existing["completed"])
                if checked:
                    done_count += 1
                new_val = st.checkbox(job["action_text"], value=checked, key=f"job_{job['id']}_{staff['id']}", disabled=is_signed)
                if new_val != checked:
                    set_completion(term["id"], staff["id"], job["id"], new_val)
                    st.rerun()
            st.progress(done_count / len(jobs) if jobs else 0)
            st.caption(f"{done_count} of {len(jobs)} complete")

    # --- Section 2: allocated jobs ---------------------------------------
    st.markdown('<span class="eot-section-label allocated">Your allocated jobs</span>', unsafe_allow_html=True)
    st.markdown('<div class="eot-section-sub">Shared jobs specifically assigned to you.</div>', unsafe_allow_html=True)

    add_jobs = get_additional_jobs(term["id"])
    assignments = get_assignments(term["id"])
    my_jobs = []
    other_jobs = []
    for j in add_jobs:
        assigned = assignments.get(j["id"], [])
        assigned_names = [a["eot_staff"]["name"] for a in assigned if a.get("eot_staff")]
        if staff["name"] in assigned_names:
            my_jobs.append((j, assigned_names))
        else:
            other_jobs.append((j, assigned_names))

    with st.container(border=True):
        if not my_jobs:
            st.caption("Nothing has been specifically allocated to you yet.")
        else:
            for job, assigned_names in my_jobs:
                others = [n for n in assigned_names if n != staff["name"]]
                label = job["action_text"] + (f"  _(with {', '.join(others)})_" if others else "")
                new_complete = st.checkbox(label, value=job["completed"], key=f"myaddcomplete_{job['id']}")
                if new_complete != job["completed"]:
                    set_additional_complete(job["id"], new_complete, by_name=staff["name"])
                    st.rerun()

    with st.expander("See other shared jobs — pick one up if you can help"):
        if not other_jobs:
            st.caption("Nothing else on the shared list right now.")
        else:
            for job, assigned_names in other_jobs:
                cols = st.columns([4, 2])
                with cols[0]:
                    label = job["action_text"]
                    if job["completed"]:
                        st.markdown(f"~~{label}~~ ✅")
                    else:
                        st.markdown(label)
                    st.caption("Assigned: " + (", ".join(assigned_names) if assigned_names else "Unassigned"))
                with cols[1]:
                    if st.button("Assign to me", key=f"assign_other_{job['id']}"):
                        assign_staff(term["id"], job["id"], staff["id"])
                        st.rerun()

    # --- Sign off ----------------------------------------------------------
    st.markdown('<span class="eot-section-label">Sign off</span>', unsafe_allow_html=True)
    with st.container(border=True):
        if is_signed:
            st.markdown(f'<div class="eot-signed-badge">✅ Signed by {signoff["signature_name"]} on {signoff["signed_at"][:16].replace("T", " ")}</div>', unsafe_allow_html=True)
            if st.button("Unlock to make changes"):
                unsign(term["id"], staff["id"])
                st.rerun()
        else:
            all_complete = (not jobs) or (done_count == len(jobs))
            if not all_complete:
                st.warning(
                    "All items above must be completed before you can sign off. "
                    "If there is any reason you're unable to complete an item, "
                    "this needs to be discussed with Leadership before signing."
                )
            sig_name = st.text_input("Type your full name to sign", key="sig_name_input", disabled=not all_complete)
            if st.button("Sign & Submit", type="primary", disabled=not all_complete):
                if sig_name.strip().lower() == staff["name"].strip().lower():
                    sign_off(term["id"], staff["id"], sig_name.strip())
                    st.rerun()
                else:
                    st.error(f"Please type your name exactly as selected above ({staff['name']}) to confirm.")

# ---------------------------------------------------------------------------
# Admin view
# ---------------------------------------------------------------------------

elif st.session_state.eot_view == "admin":
    if st.button("⬅ Back"):
        go_home()

    st.markdown('<span class="eot-section-label">Admin</span>', unsafe_allow_html=True)
    if admin_gate():

        st.markdown("#### Terms")
        with st.expander("Open / close terms for checking", expanded=not open_terms):
            if not all_terms:
                st.caption("No terms yet — create one below.")
            for t in all_terms:
                c1, c2 = st.columns([4, 2])
                c1.write(t["label"])
                new_state = c2.checkbox("Open for checking", value=t["is_active"], key=f"open_{t['id']}")
                if new_state != t["is_active"]:
                    set_term_open(t["id"], new_state)
                    st.rerun()

        with st.expander("Start a new term"):
            new_label = st.text_input("Term label", placeholder="e.g. 2026 Term 4")
            new_instructions = st.text_area("Instructions", value="Please hand this checklist to Annette at check in Friday arvo at 2:15 in the planning room")
            new_meeting = st.text_input("End of term meeting details", placeholder="e.g. End of Term Staff Meeting Wednesday 3:00 start - all Staff Kent Town Hotel")
            copy_from = st.selectbox(
                "Job list to start with",
                ["Start blank", "Use the standard CLC-LBU list"] + [t["label"] for t in all_terms],
            )
            if st.button("Create new term", type="primary"):
                if new_label.strip():
                    copy_id = None
                    seed = False
                    if copy_from == "Use the standard CLC-LBU list":
                        seed = True
                    elif copy_from != "Start blank":
                        copy_id = next(t["id"] for t in all_terms if t["label"] == copy_from)
                    create_term(new_label.strip(), new_instructions.strip(), new_meeting.strip(), copy_id, seed_defaults=seed)
                    st.success(f"Created '{new_label}' and opened it for checking.")
                    st.rerun()
                else:
                    st.error("Give the new term a label first.")

        if not all_terms:
            st.info("Create a term above to manage its jobs, staff and assignments.")
        else:
            st.markdown("---")
            st.markdown("#### Manage a term")
            default_idx = 0
            if open_terms:
                default_idx = all_terms.index(open_terms[0])
            manage_label = st.selectbox("Term to manage", [t["label"] for t in all_terms], index=default_idx, key="manage_term_select")
            manage_term = next(t for t in all_terms if t["label"] == manage_label)

            st.markdown("---")
            st.markdown("#### Staff")
            staff_list = get_staff()
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Add staff member", key="add_staff_name")
                if st.button("Add staff"):
                    if new_name.strip():
                        add_staff(new_name)
                        st.rerun()
            with col2:
                if staff_list:
                    remove_name = st.selectbox("Remove staff member", [s["name"] for s in staff_list], key="remove_staff_select")
                    if st.button("Remove selected staff", type="secondary"):
                        sid = next(s["id"] for s in staff_list if s["name"] == remove_name)
                        remove_staff(sid)
                        st.rerun()

            st.markdown("---")
            st.markdown(f"#### Standard checklist items — {manage_term['label']}")
            if st.button("Load standard CLC-LBU list (adds any missing items)"):
                n = load_default_standard_jobs(manage_term["id"])
                st.success(f"Added {n} item(s) from the standard list." if n else "Everything from the standard list is already here.")
                st.rerun()
            std_jobs = get_standard_jobs(manage_term["id"])
            for j in std_jobs:
                c1, c2, c3 = st.columns([4, 1, 1])
                edited = c1.text_input("Item text", value=j["action_text"], key=f"edit_std_{j['id']}", label_visibility="collapsed")
                if c2.button("Save", key=f"save_std_{j['id']}"):
                    if edited.strip() and edited.strip() != j["action_text"]:
                        update_standard_job(j["id"], edited.strip())
                        st.rerun()
                if c3.button("Delete", key=f"del_std_{j['id']}"):
                    delete_standard_job(j["id"])
                    st.rerun()
            new_job = st.text_input("Add a standard checklist item", key="new_std_job")
            if st.button("Add item"):
                if new_job.strip():
                    add_standard_job(manage_term["id"], new_job.strip(), len(std_jobs))
                    st.rerun()

            st.markdown("---")
            st.markdown(f"#### Additional jobs — {manage_term['label']}")
            if st.button("Load standard CLC-LBU additional jobs (adds any missing items)"):
                n = load_default_additional_jobs(manage_term["id"])
                st.success(f"Added {n} item(s) from the standard list." if n else "Everything from the standard list is already here.")
                st.rerun()
            add_jobs = get_additional_jobs(manage_term["id"])
            for j in add_jobs:
                c1, c2, c3 = st.columns([4, 1, 1])
                edited = c1.text_input("Job text", value=j["action_text"], key=f"edit_add_{j['id']}", label_visibility="collapsed")
                if c2.button("Save", key=f"save_add_{j['id']}"):
                    if edited.strip() and edited.strip() != j["action_text"]:
                        update_additional_job(j["id"], edited.strip())
                        st.rerun()
                if c3.button("Delete", key=f"del_add_{j['id']}"):
                    delete_additional_job(j["id"])
                    st.rerun()
            new_add_job = st.text_input("Add an additional job", key="new_add_job")
            if st.button("Add additional job"):
                if new_add_job.strip():
                    add_additional_job(manage_term["id"], new_add_job.strip(), len(add_jobs))
                    st.rerun()

            st.markdown("---")
            st.markdown(f"#### Assign staff to additional jobs — {manage_term['label']}")
            assignments = get_assignments(manage_term["id"])
            if not add_jobs:
                st.caption("Add some additional jobs above first.")
            elif not staff_list:
                st.caption("Add some staff above first.")
            else:
                for j in add_jobs:
                    assigned = assignments.get(j["id"], [])
                    assigned_names = [a["eot_staff"]["name"] for a in assigned if a.get("eot_staff")]
                    picked_names = st.multiselect(j["action_text"], [s["name"] for s in staff_list], default=assigned_names, key=f"assign_multi_{j['id']}")
                    if set(picked_names) != set(assigned_names):
                        for name in picked_names:
                            if name not in assigned_names:
                                sid = next(s["id"] for s in staff_list if s["name"] == name)
                                assign_staff(manage_term["id"], j["id"], sid)
                        for name in assigned_names:
                            if name not in picked_names:
                                sid = next(s["id"] for s in staff_list if s["name"] == name)
                                unassign_staff(j["id"], sid)
                        st.rerun()

            st.markdown("---")
            st.markdown(f"#### Overview — who's done what — {manage_term['label']}")
            std_jobs_for_overview = get_standard_jobs(manage_term["id"])
            rows = []
            for s in staff_list:
                comps = get_completions(manage_term["id"], s["id"])
                done = sum(1 for v in comps.values() if v["completed"])
                signoff = get_signoff(manage_term["id"], s["id"])
                is_signed = bool(signoff and signoff["signed"])
                rows.append({
                    "Staff": s["name"],
                    "Standard items done": f"{done}/{len(std_jobs_for_overview)}" if std_jobs_for_overview else "0/0",
                    "Signed off": "✅ " + signoff["signature_name"] if is_signed else "—",
                })
            if rows:
                st.table(rows)
                st.caption(
                    "Leadership override: if a staff member has a genuine reason they can't "
                    "complete an item and Leadership has agreed, sign off on their behalf below."
                )
                unsigned = [s for s in staff_list if not (get_signoff(manage_term["id"], s["id"]) or {}).get("signed")]
                if unsigned:
                    override_name = st.selectbox("Staff member", [s["name"] for s in unsigned], key="override_signoff_select")
                    if st.button("Sign off on their behalf (Leadership override)"):
                        sid = next(s["id"] for s in unsigned if s["name"] == override_name)
                        sign_off(manage_term["id"], sid, f"{override_name} (Leadership override)")
                        st.rerun()
            else:
                st.info("No staff to show yet.")
    else:
        st.caption("Enter the admin password above to manage staff, jobs, terms and assignments.")
