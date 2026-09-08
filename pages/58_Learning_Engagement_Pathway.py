"""
58_Learning_Engagement_Pathway.py
CLC-LBU Portal — Learning Engagement & Transfer Pathway

Click-to-fill tool: captures HOW a student engages, so the instructional
METHOD (not the task) can be tracked, reused, and replicated across
subjects/staff. Rolls up into a SMARTAR/GAS-aligned report.

Wired into the shared student_register / document_archive module
(archive_utils.py) — same pattern as Student Register, SMARTAR Goal
Builder, Behaviour Support, etc. Students are identified by INITIALS
only, never full names, matching the rest of the portal.

The Disposition bank uses the SA Curriculum's own named 12 dispositions
(DfE, "Dispositions embedded in the SA Curriculum", Jan 2026) rather than
a generic list — each with its official definition and the learning
areas the Department highlights it in. Transfer Mapping uses that same
mapping to suggest which CLC-LBU delivery contexts are worth trying next.

Uses st.pills() and st.segmented_control() for real pill/toggle buttons
instead of dropdowns and radio dots — these need streamlit>=1.36 in
requirements.txt. If Render is pinned to an older version, bump it there
first or these widgets will fail to import.

Still needs from you: the shared AI helper's import path (e.g.
groq_ai_call) to wire the "Draft evidence summary" button — everything
else below is fully wired against the real archive_utils.py / student
register you shared.

--------------------------------------------------------------------------
SUPABASE SCHEMA — run once in the SAME project archive_utils.py connects
to (check the Connection info expander in Student Register to confirm
which project that is), before deploying this page. student_id below is
the student's INITIALS (text), matching how document_archive and the
register both key students — no separate id lookup needed.
--------------------------------------------------------------------------

create table if not exists pathway_method_bank (
    id bigint generated always as identity primary key,
    observed_context text not null,
    instructional_move text not null,
    disposition text not null default '',
    ac_capabilities text[] not null default '{}',
    universal_or_targeted text not null check (universal_or_targeted in ('Universal','Targeted')),
    created_at timestamptz default now()
);

create table if not exists pathway_profile (
    student_id text primary key,           -- student initials, e.g. 'AD'
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
    primary_disposition text,
    evidence_of_transfer text,
    next_steps text,
    updated_at timestamptz default now()
);

-- MIGRATION: if you already ran the schema above before this update, run this
-- against your existing tables instead of the create-table statements:
--   alter table pathway_method_bank add column if not exists disposition text not null default '';
--   alter table pathway_roll_up add column if not exists primary_disposition text;
"""

import io
from datetime import date

import streamlit as st

from archive_utils import (
    archive_document,
    connected_project,
    fetch_register,
    _get_client,  # reuse the same self-locating Supabase client as the rest of the archive module
)

st.set_page_config(page_title="Learning Engagement & Transfer Pathway", page_icon="\U0001f9ed", layout="wide")

try:
    from theme import apply_theme
    apply_theme()
except Exception:
    pass

try:
    from auth import require_login
    require_login()
except Exception:
    pass

user_email = st.session_state.get("user_email", "unknown")
sb = _get_client()

with st.expander("\U0001f527 Connection info (for setup/troubleshooting)"):
    st.code(connected_project())
    st.caption(
        "This is the Supabase project the archive module is connected to — "
        "run the SQL block in this file's docstring against the SAME "
        "project so student initials line up with the register."
    )

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
DISPOSITION_OPTIONS = [
    "Community-minded", "Confident", "Creative", "Curious", "Empathetic", "Open-minded",
    "Reflective", "Resilient", "Resourceful", "Respectful", "Responsible", "Self-aware",
]
# Source: SA Curriculum "Dispositions embedded in the SA Curriculum" (DfE, Jan 2026) —
# the 12 dispositions named and defined for public education, each highlighted in
# specific learning areas because those areas afford authentic contexts for developing it.
SA_DISPOSITION_WHAT_IT_IS = {
    "Community-minded": "Being willing to think beyond ourselves by valuing belonging, human interconnectedness and the reality of our multicultural society.",
    "Confident": "Believing in yourself and your abilities; trusting the choices you make on your own and with others.",
    "Creative": "Imagining and exploring ideas, experimenting with new possibilities, playing with alternatives and developing original expressions or solutions.",
    "Curious": "Being eager to explore, ask questions and understand the things you wonder about.",
    "Empathetic": "Relating to and seeking to understand the feelings, experiences and perspectives of others.",
    "Open-minded": "Willing to consider diverse ideas and perspectives and to question one's own beliefs and biases.",
    "Reflective": "Thoughtfully considering the world around us, our emotions, behaviours, perspectives and ways of learning, then monitoring and adjusting these based on insights gained.",
    "Resilient": "Persevering and adapting in the face of challenges.",
    "Resourceful": "Making the most of what is available to find effective ways to navigate challenges.",
    "Respectful": "Acknowledging each other's beliefs, values and experiences while honouring the rights of self, others and the environment.",
    "Responsible": "Being accountable for your actions, fulfilling your commitments and considering how your choices affect yourself, others and the environment.",
    "Self-aware": "Being sensitive and responsive to your own feelings, thoughts, actions, biases and influences.",
}
SA_DISPOSITION_LEARNING_AREAS = {
    "Community-minded": ["Languages"],
    "Confident": ["The Arts"],
    "Creative": ["The Arts", "Technologies"],
    "Curious": ["English", "HASS", "Science", "Technologies"],
    "Empathetic": ["English", "HASS", "Languages", "Technologies", "The Arts"],
    "Open-minded": ["Science"],
    "Reflective": ["English", "Languages", "Mathematics"],
    "Resilient": ["HPE", "Mathematics", "Technologies"],
    "Resourceful": ["English", "HPE", "Mathematics"],
    "Respectful": ["HPE"],
    "Responsible": ["HASS", "HPE", "Science"],
    "Self-aware": ["The Arts"],
}
# Best-effort bridge from the official SA Curriculum learning areas to the CLC-LBU
# delivery contexts staff actually log against — adjust as your program structure evolves.
LEARNING_AREA_TO_CLC_CONTEXT = {
    "Mathematics": ["Numeracy"],
    "English": ["Literacy", "Word Aware session"],
    "HPE": ["Behaviour Support routine", "NIT"],
    "Technologies": ["SY Vocational", "Café / Barista Enterprise"],
    "HASS": [], "Languages": [], "Science": [], "The Arts": [],
}

def curriculum_suggested_contexts(disposition):
    """Contexts the SA Curriculum itself flags as authentic homes for this disposition,
    translated into the CLC-LBU delivery contexts staff already log against."""
    areas = SA_DISPOSITION_LEARNING_AREAS.get(disposition, [])
    suggested = []
    for area in areas:
        for ctx in LEARNING_AREA_TO_CLC_CONTEXT.get(area, []):
            if ctx not in suggested:
                suggested.append(ctx)
    return suggested

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

# ---- student picker — reuses the shared register, same as every other tool ----
students = fetch_register("active")
student_labels = {f"{s['initials']}-{s.get('program') or '?'}": s["initials"] for s in students}
if not student_labels:
    st.info("No active students on the register yet — add them in Student Register first.")
    st.stop()

st.title("Learning Engagement & Transfer Pathway")
st.caption("Capture HOW a student engages, so the teaching METHOD can be replicated — not duplicated.")

selected_label = st.selectbox("Student", sorted(student_labels.keys()))
student_id = student_labels[selected_label]  # student's initials

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1 \u00b7 Engagement Profile", "2 \u00b7 Method Signature", "3 \u00b7 Transfer Mapping",
    "4 \u00b7 Application Log", "5 \u00b7 Reporting Roll-up",
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
    st.caption("Blue = Universal (works for most students) \u00b7 Yellow = Targeted (specific to this student)")

    bank = sb.table("pathway_method_bank").select("*").order("instructional_move").execute().data
    bank_labels = {f"{m['instructional_move']} \u2014 {m.get('disposition') or 'no disposition set'} ({m['observed_context']})": m for m in bank}

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
        st.markdown("**Disposition activated** \u2014 the habit that actually transfers; capability and knowledge below are what gets demonstrated once it does.")
        disposition = st.pills("Disposition activated", DISPOSITION_OPTIONS, selection_mode="single", label_visibility="collapsed")
        if disposition:
            areas = ", ".join(SA_DISPOSITION_LEARNING_AREAS.get(disposition, []))
            st.caption(f"SA Curriculum: *{SA_DISPOSITION_WHAT_IT_IS[disposition]}* Highlighted in: {areas}.")
        else:
            disposition = st.text_input("Not listed? Name it here")
        caps = st.pills("AC General Capability targeted", AC_CAPABILITIES, selection_mode="multi") or []
        ut = st.segmented_control("Universal or Targeted?", ["Universal", "Targeted"])
        if st.button("Create & attach", type="primary"):
            new = sb.table("pathway_method_bank").insert({
                "observed_context": ctx, "instructional_move": move, "disposition": disposition,
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
        colour = "\U0001f535" if m["universal_or_targeted"] == "Universal" else "\U0001f7e1"
        st.write(
            f"{colour} **{m['instructional_move']}** \u2014 {m['observed_context']} \u00b7 "
            f"disposition: **{m.get('disposition') or '\u2014'}** \u00b7 {', '.join(m['ac_capabilities'])}"
        )

# ================= TAB 3 — Transfer Mapping =================
with tab3:
    st.subheader("Where else this disposition shows up")
    st.caption("Disposition-led, not method-led: a disposition like curiosity doesn't care which subject it's in. Ask where else it could be invited — capability and knowledge will follow it in.")
    if not attached:
        st.info("Attach a method signature in Tab 2 first.")
    else:
        method_choice = st.selectbox(
            "Method signature (for its disposition)", attached,
            format_func=lambda a: f"{a['pathway_method_bank']['instructional_move']} — {a['pathway_method_bank'].get('disposition') or 'no disposition set'}",
        )
        st.write(f"Disposition: **{method_choice['pathway_method_bank'].get('disposition') or '\u2014'}**")
        disp = method_choice["pathway_method_bank"].get("disposition")
        suggested = curriculum_suggested_contexts(disp) if disp else []
        if suggested:
            areas = ", ".join(SA_DISPOSITION_LEARNING_AREAS.get(disp, []))
            st.caption(f"SA Curriculum highlights {disp} in: {areas} \u2014 pre-selected below, adjust as needed.")
        other_contexts = st.pills(
            "Other contexts this disposition could show up in", CONTEXT_OPTIONS,
            selection_mode="multi", default=suggested, key="tm_ctx",
        ) or []
        staff_trial = st.text_input("Staff to invite it (comma-separated)")
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
    st.caption("Leads with disposition strength — how many contexts the disposition itself has been seen operating in — since that's the strongest evidence of transfer.")

    all_logs = []
    for a in attached:
        entries = sb.table("pathway_application_log").select("*").eq("student_method_id", a["id"]).execute().data
        all_logs.extend(entries)

    # Group by DISPOSITION first — the headline metric — not by method
    disposition_contexts = {}
    for a in attached:
        m = a["pathway_method_bank"]
        disp = m.get("disposition") or "(no disposition set)"
        held = {e["context_applied"] for e in all_logs if e.get("held_up") in ("Y", "Partial")
                and e["student_method_id"] == a["id"]}
        disposition_contexts.setdefault(disp, set()).update(held)

    if disposition_contexts:
        cols = st.columns(len(disposition_contexts))
        for col, (disp, ctxs) in zip(cols, disposition_contexts.items()):
            with col:
                st.metric(disp, len(ctxs))
                if ctxs:
                    st.caption(", ".join(sorted(ctxs)))
    else:
        st.info("No methods attached yet — disposition strength will show here once logged.")

    st.divider()
    st.markdown("**Capability & knowledge evidence** _(supporting detail — where the disposition showed up, not the headline)_")
    replicated_contexts = {e["context_applied"] for e in all_logs if e["held_up"] in ("Y", "Partial")}
    st.write(f"Contexts replicated in overall: {len(replicated_contexts)} — {', '.join(sorted(replicated_contexts)) or '\u2014'}")

    existing_rollup = sb.table("pathway_roll_up").select("*").eq("student_id", student_id).execute().data
    existing_rollup = existing_rollup[0] if existing_rollup else {}

    default_primary = ", ".join(disposition_contexts.keys()) if disposition_contexts else ""
    primary_disposition = st.text_input("Primary disposition(s) demonstrated", value=existing_rollup.get("primary_disposition", default_primary))
    smartar_goal = st.text_input("Linked SMARTAR / GAS goal", value=existing_rollup.get("linked_smartar_goal", ""))

    if st.button("\u2728 Draft evidence summary from logged data"):
        # TODO: point this at the portal's actual shared AI helper (e.g. groq_ai_call) —
        # not present in archive_utils.py / Student Register, so still needs its import path.
        try:
            from ai_helpers import groq_ai_call
            prompt = (
                "Summarise, in 2-3 sentences for a staff report, the evidence that this student's "
                f"dispositions have transferred across contexts. Disposition -> contexts held up in: "
                f"{ {k: sorted(v) for k, v in disposition_contexts.items()} }. Log detail: {all_logs}"
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
            "primary_disposition": primary_disposition,
            "evidence_of_transfer": evidence, "next_steps": next_steps,
        }).execute()
        st.success("Saved.")

    st.divider()

    def build_docx() -> bytes:
        """Build a Word report mirroring the CLC-LBU_Learning_Engagement_Transfer_Pathway.docx
        template, filled with this student's live data."""
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        NAVY = RGBColor(0x1F, 0x38, 0x64)
        doc = Document()

        doc.add_heading("Learning Engagement & Transfer Pathway", level=0)
        p = doc.add_paragraph(f"Student: {student_id}   \u00b7   Program: {selected_label.split('-')[-1]}")
        p.runs[0].font.size = Pt(11)

        doc.add_heading("Part 1 \u2014 Engagement Profile", level=1)
        for label_, vals in [
            ("Regulation state", existing.get("regulation_state", [])),
            ("Sensory preferences", existing.get("sensory_preferences", [])),
            ("Relational trust (PACE)", existing.get("relational_trust", [])),
            ("Environmental needs", existing.get("environmental_needs", [])),
        ]:
            doc.add_paragraph(f"{label_}: {', '.join(vals) or '\u2014'}")

        doc.add_heading("Part 2 \u2014 Method Signatures", level=1)
        for a in attached:
            m = a["pathway_method_bank"]
            doc.add_paragraph(
                f"[{m['universal_or_targeted']}] {m['instructional_move']} "
                f"\u2014 {m['observed_context']} \u00b7 disposition: {m.get('disposition') or '\u2014'} "
                f"\u00b7 {', '.join(m['ac_capabilities'])}"
            )

        doc.add_heading("Part 4 \u2014 Application Log", level=1)
        table = doc.add_table(rows=1, cols=5)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        for i, h in enumerate(["Date", "Staff", "Context", "Held up?", "Adaptation"]):
            hdr[i].text = h
        for e in all_logs:
            row = table.add_row().cells
            row[0].text = str(e.get("log_date") or "")
            row[1].text = str(e.get("staff") or "")
            row[2].text = str(e.get("context_applied") or "")
            row[3].text = str(e.get("held_up") or "")
            row[4].text = str(e.get("adaptation_needed") or "")

        doc.add_heading("Part 5 \u2014 Reporting Roll-up", level=1)
        doc.add_paragraph(f"Primary disposition(s) demonstrated: {primary_disposition or '\u2014'}")
        disp_summary = "; ".join(f"{d}: {len(c)} context(s) ({', '.join(sorted(c)) or '\u2014'})" for d, c in disposition_contexts.items())
        doc.add_paragraph(f"Contexts the disposition held up in: {disp_summary or '\u2014'}")
        doc.add_paragraph(f"Linked SMARTAR / GAS goal: {smartar_goal or '\u2014'}")
        doc.add_paragraph(f"Capability & knowledge evidence (supporting detail): contexts replicated overall — {len(replicated_contexts)} ({', '.join(sorted(replicated_contexts)) or '\u2014'})")
        doc.add_paragraph(f"Evidence of transfer: {evidence or '\u2014'}")
        doc.add_paragraph(f"Next steps: {next_steps or '\u2014'}")

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    if st.button("\U0001f4c4 Generate & save to archive"):
        file_bytes = build_docx()
        filename = f"Learning_Engagement_Pathway_{student_id}.docx"
        rec = archive_document(
            source_tool="Learning Engagement Pathway",
            doc_type="Other",  # consider adding "Learning Engagement Pathway" to DOC_TYPES in archive_utils.py
            title=f"Learning Engagement & Transfer Pathway \u2014 {student_id}",
            file_bytes=file_bytes,
            filename=filename,
            student_initials=student_id,
            created_by=user_email,
        )
        st.download_button("\u2b07\ufe0f Download Word doc", data=file_bytes, file_name=filename)
        if rec:
            st.success("Saved to Document Archive.")
