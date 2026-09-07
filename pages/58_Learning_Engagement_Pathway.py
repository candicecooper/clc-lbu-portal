"""
58_Learning_Engagement_Pathway.py
CLC-LBU Portal — Learning Engagement & Transfer Pathway

Click-to-fill tool: captures HOW a student engages, so the instructional
METHOD (not the task) can be tracked, reused, and replicated across
subjects/staff. Rolls up into a SMARTAR/GAS-aligned report.

Uses st.pills() and st.segmented_control() for real pill/toggle buttons
instead of dropdowns and radio dots — these need streamlit>=1.36 in
requirements.txt. If Render is pinned to an older version, bump it there
first or these widgets will fail to import.

--------------------------------------------------------------------------
SUPABASE SCHEMA — run once against your students project (the one holding
student_register), before deploying this page. Adjust the student_register
column names below (marked ASSUMED) to match your real schema — I don't
have visibility into your actual table structure, only the naming pattern
you've described elsewhere (initials + program, e.g. "AD-PY").
--------------------------------------------------------------------------

create table if not exists pathway_method_bank (
    id bigint generated always as identity primary key,
    observed_context text not null,
    instructional_move text not null,
    ac_capabilities text[] not null default '{}',
    universal_or_targeted text not null check (universal_or_targeted in ('Universal','Targeted')),
    created_at timestamptz default now()
);

create table if not exists pathway_profile (
    student_id text primary key,           -- ASSUMED: student_register.id or code
    regulation_state text[] default '{}',
    sensory_preferences text[] default '{}',
    relational_trust text[] default '{}',
    environmental_needs text[] default '{}',
    updated_at timestamptz default now()
);

create table if not exists pathway_student_methods (
    id bigint generated always as identity primary key,
    student_id text not null,
    method_id bigint references pathway_method_bank(id),
    created_at timestamptz default now()
);

create table if not exists pathway_transfer_map (
    id bigint generated always as identity primary key,
    student_method_id bigint references pathway_student_methods(id),
    other_contexts text[] default '{}',
    staff_to_trial text[] default '{}',
    created_at timestamptz default now()
);

create table if not exists pathway_application_log (
    id bigint generated always as identity primary key,
    student_method_id bigint references pathway_student_methods(id),
    log_date date not null,
    staff text,
    context_applied text,
    held_up text check (held_up in ('Y','Partial','N')),
    adaptation_needed text,
    created_at timestamptz default now()
);

create table if not exists pathway_roll_up (
    student_id text primary key,
    linked_smartar_goal text,
    evidence_of_transfer text,
    next_steps text,
    updated_at timestamptz default now()
);
"""

import streamlit as st
from datetime import date
from supabase import create_client
import os

# ---- shared portal modules (already exist elsewhere in the repo) ----
from staff_auth import require_staff_login  # same gate used by other non-confidential tools
# from archive_utils import save_to_archive  # TODO: wire once confirmed — see note at bottom

st.set_page_config(page_title="Learning Engagement & Transfer Pathway", layout="wide")
require_staff_login()

# ---- Supabase connections ----
# Students project (holds student_register) — reuse existing env var pattern
sb_students = create_client(os.environ["SUPABASE_URL_STUDENTS"], os.environ["SUPABASE_KEY_STUDENTS"])
# This tool's own tables live wherever you choose — defaulting to the students project too
sb = sb_students

# ---- constant option banks (click, don't type) ----
REGULATION_OPTIONS = [
    "Settles with low-demand parallel activity first", "Needs movement before task",
    "Needs quiet/low-stimulation entry", "Responds well to a predictable greeting routine",
    "Arrives dysregulated after transitions", "Settles fastest 1:1",
]
SENSORY_OPTIONS = [
    "Prefers standing/moving over seated work", "Fidget object reduces shutdown",
    "Sensitive to noise", "Sensitive to lighting", "Needs tactile input",
    "Prefers minimal eye contact during instruction",
]
RELATIONAL_OPTIONS = [
    "Responds to playful/curious framing", "Needs acceptance before correction",
    "Shuts down at correction in front of peers", "Builds trust slowly, tests boundaries first",
    "Responds well to shared humour", "Needs empathy named explicitly before redirection",
]
ENVIRONMENTAL_OPTIONS = [
    "1:1 or small group only", "Needs visible/predictable end point to task",
    "Needs consistent seating", "Needs advance notice of transitions",
    "Needs an escape/reset option available",
]
CONTEXT_OPTIONS = [
    "Numeracy", "Literacy", "NIT", "Café / Barista Enterprise", "SY Vocational",
    "Behaviour Support routine", "Word Aware session", "Other (add below)",
]
AC_CAPABILITIES = [
    "Literacy", "Numeracy", "ICT Capability", "Critical & Creative Thinking",
    "Personal & Social Capability", "Ethical Understanding", "Intercultural Understanding",
]

def chip_picker(label, options, existing, key):
    """Pill buttons (st.pills, multi-select) + a small free-text add-on for genuinely new
    descriptors — those then become click options for every future student too."""
    st.write(label)
    chosen = st.pills(
        label, options, selection_mode="multi",
        default=[o for o in existing if o in options],
        key=f"{key}_pills", label_visibility="collapsed",
    ) or []
    custom_existing = [o for o in existing if o not in options]
    extra = st.text_input(f"Add custom ({label.lower()}, comma-separated)", value=", ".join(custom_existing), key=f"{key}_extra")
    extra_items = [e.strip() for e in extra.split(",") if e.strip()]
    return list(chosen) + extra_items

# ---- student picker (initials + program only — no full names in this tool) ----
@st.cache_data(ttl=60)
def load_students():
    # ASSUMED columns: id, initials, program, status — adjust to your real student_register schema
    res = sb_students.table("student_register").select("id, initials, program, status").execute()
    return [r for r in res.data if r.get("status", "active") == "active"]

students = load_students()
student_labels = {f"{s['initials']}-{s['program']}": s["id"] for s in students}
if not student_labels:
    st.warning("No active students found in student_register — check column names match your schema.")
    st.stop()

st.title("Learning Engagement & Transfer Pathway")
st.caption("Capture HOW a student engages, so the teaching METHOD can be replicated — not duplicated.")

selected_label = st.selectbox("Student", sorted(student_labels.keys()))
student_id = student_labels[selected_label]

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1 · Engagement Profile", "2 · Method Signature", "3 · Transfer Mapping",
    "4 · Application Log", "5 · Reporting Roll-up",
])

# ================= TAB 1 — Engagement Profile =================
with tab1:
    st.subheader("How this student comes online")
    existing = sb.table("pathway_profile").select("*").eq("student_id", student_id).execute().data
    existing = existing[0] if existing else {}

    reg = chip_picker("Regulation state / Window of Tolerance", REGULATION_OPTIONS, existing.get("regulation_state", []), "reg")
    sens = chip_picker("Sensory preferences", SENSORY_OPTIONS, existing.get("sensory_preferences", []), "sens")
    rel = chip_picker("Relational trust markers (PACE)", RELATIONAL_OPTIONS, existing.get("relational_trust", []), "rel")
    env = chip_picker("Environmental needs", ENVIRONMENTAL_OPTIONS, existing.get("environmental_needs", []), "env")

    if st.button("Save Engagement Profile", type="primary"):
        sb.table("pathway_profile").upsert({
            "student_id": student_id, "regulation_state": reg, "sensory_preferences": sens,
            "relational_trust": rel, "environmental_needs": env,
        }).execute()
        st.success("Saved.")

# ================= TAB 2 — Method Signature =================
with tab2:
    st.subheader("The transferable teaching move")
    st.caption("Blue = Universal (works for most students) · Yellow = Targeted (specific to this student)")

    bank = sb.table("pathway_method_bank").select("*").order("instructional_move").execute().data
    bank_labels = {f"{m['instructional_move']} ({m['observed_context']})": m for m in bank}

    mode = st.segmented_control("Attach a method to this student", ["Pick from existing bank", "+ New method signature"])

    if mode == "Pick from existing bank" and bank_labels:
        pick = st.selectbox("Method", sorted(bank_labels.keys()))
        if st.button("Attach to student"):
            sb.table("pathway_student_methods").insert({
                "student_id": student_id, "method_id": bank_labels[pick]["id"],
            }).execute()
            st.success("Attached.")
    else:
        ctx = st.pills("Observed context", CONTEXT_OPTIONS, selection_mode="single")
        if ctx == "Other (add below)":
            ctx = st.text_input("Custom context")
        move = st.text_area("Instructional move — describe abstractly (e.g. \"concrete-before-abstract sequencing\", not \"used counters in maths\")")
        caps = st.pills("AC General Capability targeted", AC_CAPABILITIES, selection_mode="multi") or []
        ut = st.segmented_control("Universal or Targeted?", ["Universal", "Targeted"])
        if st.button("Create & attach", type="primary"):
            new = sb.table("pathway_method_bank").insert({
                "observed_context": ctx, "instructional_move": move,
                "ac_capabilities": caps, "universal_or_targeted": ut,
            }).execute().data[0]
            sb.table("pathway_student_methods").insert({
                "student_id": student_id, "method_id": new["id"],
            }).execute()
            st.success("Created and attached.")

    st.divider()
    st.markdown("**Methods attached to this student**")
    attached = sb.table("pathway_student_methods").select("id, method_id, pathway_method_bank(*)").eq("student_id", student_id).execute().data
    for a in attached:
        m = a["pathway_method_bank"]
        colour = "🔵" if m["universal_or_targeted"] == "Universal" else "🟡"
        st.write(f"{colour} **{m['instructional_move']}** — {m['observed_context']} · {', '.join(m['ac_capabilities'])}")

# ================= TAB 3 — Transfer Mapping =================
with tab3:
    st.subheader("Where else this method applies")
    if not attached:
        st.info("Attach a method signature in Tab 2 first.")
    else:
        method_choice = st.selectbox(
            "Method signature", attached,
            format_func=lambda a: a["pathway_method_bank"]["instructional_move"],
        )
        other_contexts = st.pills("Other contexts it could apply", CONTEXT_OPTIONS, selection_mode="multi", key="tm_ctx") or []
        staff_trial = st.text_input("Staff to try it (comma-separated)")
        if st.button("Save transfer mapping", type="primary"):
            sb.table("pathway_transfer_map").insert({
                "student_method_id": method_choice["id"],
                "other_contexts": other_contexts,
                "staff_to_trial": [s.strip() for s in staff_trial.split(",") if s.strip()],
            }).execute()
            st.success("Saved.")

# ================= TAB 4 — Application Log =================
with tab4:
    st.subheader("Evidence the replication happened")
    if not attached:
        st.info("Attach a method signature in Tab 2 first.")
    else:
        log_method = st.selectbox(
            "Method signature", attached,
            format_func=lambda a: a["pathway_method_bank"]["instructional_move"],
            key="log_method",
        )
        c1, c2 = st.columns(2)
        with c1:
            log_date = st.date_input("Date", value=date.today())
            staff = st.text_input("Staff")
        with c2:
            ctx_applied = st.pills("Context applied in", CONTEXT_OPTIONS, selection_mode="single", key="log_ctx")
            held_up = st.segmented_control("Held up?", ["Y", "Partial", "N"])
        adaptation = st.text_area("Adaptation needed (if any)")
        if st.button("Log entry", type="primary"):
            sb.table("pathway_application_log").insert({
                "student_method_id": log_method["id"], "log_date": str(log_date),
                "staff": staff, "context_applied": ctx_applied,
                "held_up": held_up, "adaptation_needed": adaptation,
            }).execute()
            st.success("Logged.")

        st.divider()
        entries = sb.table("pathway_application_log").select("*").eq("student_method_id", log_method["id"]).order("log_date").execute().data
        if entries:
            st.table([{"Date": e["log_date"], "Staff": e["staff"], "Context": e["context_applied"],
                       "Held up?": e["held_up"], "Adaptation": e["adaptation_needed"]} for e in entries])

# ================= TAB 5 — Reporting Roll-up =================
with tab5:
    st.subheader("SMARTAR / GAS-aligned roll-up")

    all_logs = []
    for a in attached:
        entries = sb.table("pathway_application_log").select("*").eq("student_method_id", a["id"]).execute().data
        all_logs.extend(entries)

    replicated_contexts = {e["context_applied"] for e in all_logs if e["held_up"] in ("Y", "Partial")}
    st.metric("Contexts replicated in", len(replicated_contexts))
    if replicated_contexts:
        st.write(", ".join(sorted(replicated_contexts)))

    existing_rollup = sb.table("pathway_roll_up").select("*").eq("student_id", student_id).execute().data
    existing_rollup = existing_rollup[0] if existing_rollup else {}

    smartar_goal = st.text_input("Linked SMARTAR / GAS goal", value=existing_rollup.get("linked_smartar_goal", ""))

    if st.button("✨ Draft evidence summary from logged data"):
        # Uses the portal's shared Groq/Claude helper — see groq_ai_call() pattern used elsewhere in the repo
        try:
            from ai_helpers import groq_ai_call  # TODO: confirm actual import path in your repo
            prompt = (
                "Summarise, in 2-3 sentences for a staff report, the evidence that this teaching "
                f"method has transferred across contexts. Contexts replicated: {sorted(replicated_contexts)}. "
                f"Log detail: {all_logs}"
            )
            draft = groq_ai_call(prompt)
        except Exception:
            draft = "(AI helper not wired yet — draft manually below.)"
        st.session_state["evidence_draft"] = draft

    evidence = st.text_area("Evidence of transfer", value=st.session_state.get("evidence_draft", existing_rollup.get("evidence_of_transfer", "")))
    next_steps = st.text_area("Next steps", value=existing_rollup.get("next_steps", ""))

    if st.button("Save roll-up", type="primary"):
        sb.table("pathway_roll_up").upsert({
            "student_id": student_id, "linked_smartar_goal": smartar_goal,
            "evidence_of_transfer": evidence, "next_steps": next_steps,
        }).execute()
        st.success("Saved.")

    st.divider()
    if st.button("📄 Export to Word"):
        st.info("Word export mirrors the CLC-LBU_Learning_Engagement_Transfer_Pathway.docx layout — "
                "wire this to python-docx using the same section structure once this page is deployed. "
                "Add python-docx to requirements.txt if not already present.")

    # TODO: once confirmed, wire archive_utils.save_to_archive(...) here, following the
    # same pattern as SMARTAR Goal Builder / Behaviour Support / Communication Log.
