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

Social and emotional capability is prioritised at LBU, so it has its own
field (not buried inside the generic AC Capability multiselect) — using
the Australian Curriculum's own four organising elements of Personal and
Social Capability (Self-awareness, Self-management, Social awareness,
Social management).

Uses st.pills() and st.segmented_control() for real pill/toggle buttons
instead of dropdowns and radio dots — these need streamlit>=1.36 in
requirements.txt. If Render is pinned to an older version, bump it there
first or these widgets will fail to import.

The AI-assisted buttons (instructional move abstraction, evidence summary
drafting) use a self-contained groq_ai_call() defined in this file — not
dependent on locating the portal's shared helper. It needs GROQ_API_KEY
in the environment (same as your other Groq-backed tools) and `groq` in
requirements.txt (see requirements-additions.txt in the deploy bundle).

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
    social_emotional text[] not null default '{}',
    ac_capabilities text[] not null default '{}',
    universal_or_targeted text not null check (universal_or_targeted in ('Universal curriculum (Tier 1)','Targeted curriculum (Tier 2)','Individualised intervention (Tier 3)')),
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
--   alter table pathway_method_bank add column if not exists social_emotional text[] not null default '{}';
--   alter table pathway_roll_up add column if not exists primary_disposition text;
--   -- If you have data from BEFORE the 3-tier model (values 'Universal'/'Targeted'):
--   -- drop the OLD constraint first, or these updates get rejected by it:
--   alter table pathway_method_bank drop constraint if exists pathway_method_bank_universal_or_targeted_check;
--   update pathway_method_bank set universal_or_targeted = 'Universal curriculum (Tier 1)' where universal_or_targeted = 'Universal';
--   update pathway_method_bank set universal_or_targeted = 'Targeted curriculum (Tier 2)' where universal_or_targeted = 'Targeted';
--   alter table pathway_method_bank add constraint pathway_method_bank_universal_or_targeted_check
--     check (universal_or_targeted in ('Universal curriculum (Tier 1)','Targeted curriculum (Tier 2)','Individualised intervention (Tier 3)'));
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


def groq_ai_call(prompt, system=None, max_tokens=800):
    """Self-contained AI call for this page — not dependent on finding the portal's
    shared helper. Mirrors the resilience pattern already rolled out fleet-wide
    (Behaviour Support, Minutes Polisher, etc.): a model fallback chain, a fix for
    the httpx/'proxies' client-init clash on older groq wheels, reasoning_effort
    disabled on the Qwen hybrid-thinking model so it returns plain text instead of
    a <think> block, and self-healing max_tokens halving on 413 "too large" errors.
    Reads GROQ_API_KEY from the environment, same as your other Groq-backed tools.
    Requires `groq` in requirements.txt (see requirements-additions.txt in the deploy bundle).
    """
    from groq import Groq
    import httpx

    models = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]

    try:
        client = Groq()
    except TypeError:
        client = Groq(http_client=httpx.Client())

    last_err = None
    for model in models:
        tokens = max_tokens
        for _ in range(3):
            try:
                kwargs = {"reasoning_effort": "none"} if "qwen" in model else {}
                resp = client.chat.completions.create(
                    model=model, messages=messages, max_tokens=tokens, temperature=0.3, **kwargs,
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                if "413" in str(e) or "too large" in str(e).lower():
                    tokens = max(400, tokens // 2)
                    continue
                break  # non-413 error on this model — try the next model in the chain
    raise RuntimeError(f"Groq call failed on every model in the chain: {last_err}")


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

# ---- light visual polish, scoped to this page only ----
st.markdown("""
<style>
[data-testid="stAppViewContainer"] .main .block-container { padding-top: 1.5rem; max-width: 1100px; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0; padding: 8px 18px; font-weight: 500;
    background-color: rgba(31,56,100,0.04);
}
.stTabs [aria-selected="true"] { background-color: rgba(31,56,100,0.10); }
div[data-testid="stExpander"] { border-radius: 12px; border: 1px solid rgba(31,56,100,0.12); }
div[data-testid="stMetric"] {
    background-color: rgba(31,56,100,0.04); border-radius: 12px;
    padding: 12px 16px; border: 1px solid rgba(31,56,100,0.10);
}
.stButton>button { border-radius: 8px; }
.stButton>button[kind="primary"] { background-color: #1F3864; border-color: #1F3864; }
.pathway-header {
    background: linear-gradient(135deg, #1F3864 0%, #2E5E8C 100%);
    border-radius: 16px; padding: 22px 28px; margin-bottom: 18px; color: white;
}
.pathway-header h1 { color: white; font-size: 26px; margin: 0 0 4px 0; }
.pathway-header p { color: rgba(255,255,255,0.85); margin: 0; font-size: 14px; }
.student-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 44px; height: 44px; border-radius: 50%; background: #1F3864;
    color: white; font-weight: 600; font-size: 15px; margin-right: 12px;
}
</style>
""", unsafe_allow_html=True)

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
    "Shows hyperarousal signs (fidgety, loud, fast talking)",
    "Shows hypoarousal signs (withdrawn, flat, slow to respond)",
    "Co-regulates well with a trusted adult nearby",
    "Needs a named \u2018reset\u2019 option before re-engaging",
    "Responds to rhythmic/repetitive activity to settle",
    "Needs a breathing/grounding strategy prompted",
    "Escalates quickly under time pressure",
    "Settles with a physical comfort item (weighted item, fidget)",
    "Needs warning before demands increase",
    "Regulates better after a movement break",
]
SENSORY_OPTIONS = [
    "Prefers standing/moving over seated work", "Fidget object reduces shutdown",
    "Sensitive to noise", "Sensitive to lighting", "Needs tactile input",
    "Prefers minimal eye contact during instruction",
    "Sensory seeking (craves movement/pressure/input)",
    "Sensory avoiding (overwhelmed by input)", "Sensitive to smell",
    "Sensitive to textures (clothing, materials)", "Needs noise-cancelling headphones",
    "Prefers dim/natural lighting", "Benefits from weighted blanket/lap pad",
    "Needs a chewable/oral sensory tool", "Sensitive to crowded/busy spaces",
    "Prefers own space bubble (no touching)",
]
RELATIONAL_OPTIONS = [
    "Responds to playful/curious framing", "Needs acceptance before correction",
    "Shuts down at correction in front of peers", "Builds trust slowly, tests boundaries first",
    "Responds well to shared humour", "Needs empathy named explicitly before redirection",
    "Prefers the same trusted adult for difficult conversations",
    "Responds to curiosity (\u2018I wonder what happened\u2019) over interrogation",
    "Needs repair after conflict, not just consequence",
    "Wary of new adults, needs time to warm up",
    "Responds to genuine praise, not generic praise",
    "Needs choice offered rather than told",
    "Tests the relationship through provocation",
    "Responds well to side-by-side conversation (not face-to-face)",
    "Needs the adult to stay calm/non-reactive when escalated",
]
ENVIRONMENTAL_OPTIONS = [
    "1:1 or small group only", "Needs visible/predictable end point to task",
    "Needs consistent seating", "Needs advance notice of transitions",
    "Needs an escape/reset option available", "Needs a visual schedule/timetable",
    "Needs clear physical boundaries (desk, mat, space)",
    "Prefers back-to-wall or door-visible seating", "Needs reduced visual clutter",
    "Benefits from a consistent daily routine", "Needs an adult within sight/reach",
    "Struggles with unstructured/free time", "Needs a first/then visual structure",
    "Benefits from a calm-down/safe space", "Needs movement breaks scheduled in",
]
CONTEXT_OPTIONS = [
    "Numeracy", "Literacy", "NIT", "Café / Barista Enterprise", "SY Vocational",
    "Behaviour Support routine", "Word Aware session", "Other (add below)",
]
AC_CAPABILITIES = [
    "Literacy", "Numeracy", "ICT Capability", "Critical & Creative Thinking",
    "Personal & Social Capability", "Ethical Understanding", "Intercultural Understanding",
]
# LBU prioritises social and emotional capability, so it gets its own field rather than
# sitting as one item inside the generic AC Capability multiselect. These four are the
# Australian Curriculum's own organising elements of Personal and Social Capability —
# not a separate framework bolted on.
SEL_ELEMENTS = ["Self-awareness", "Self-management", "Social awareness", "Social management"]
SEL_WHAT_IT_IS = {
    "Self-awareness": "Recognising and naming one's own emotions, strengths, values and limitations.",
    "Self-management": "Regulating emotions, showing self-discipline, setting goals, and adapting to change.",
    "Social awareness": "Recognising and understanding others' emotions and perspectives, and appreciating diversity.",
    "Social management": "Communicating, collaborating and resolving conflict effectively in relationships.",
}
# Source: LBU's own "Personal and Social Capability Program Map" (uploaded doc) — the
# actual named programs/BSEM domains staff already run against each SEL element, shown
# as reference so a pick is grounded in a real intervention, not just a label.
SEL_LBU_PROGRAMS = {
    "Self-awareness": [
        "Interoception \u2014 Ready to Learn Kit (DfE)", "BSEM Stamina \u2014 Growth Mindset (self-assessment rubric)",
        "BSEM Stamina \u2014 Emotional Intelligence (savouring)", "BSEM Engagement \u2014 Willingness (gratitude, mindgames)",
        "BSEM Body \u2014 Mindfulness / Present Centred Grounded", "BSEM Body \u2014 De-escalation (what is stress, de/escalation maps)",
        "BSEM Character \u2014 Hope (images of the future)", "BSEM Character \u2014 Character Strengths (VIA Survey, strength ranking)",
    ],
    "Self-management": [
        "BSEM Body \u2014 Self-regulation", "BSEM Body \u2014 De-escalation (Ready to Learn Plan / WOT)",
        "BSEM Stamina \u2014 Growth Mindset (mindset awareness)", "BSEM Stamina \u2014 Emotional Intelligence (turning down the volume)",
        "BSEM Stamina \u2014 Resilience (unhelpful thinking, mindhooks, diffusion)", "BSEM Character \u2014 Hope (the hope map)",
        "Zones of Regulation", "Alert Program (How Fast Does Your Engine Run) \u2014 JP",
    ],
    "Social awareness": [
        "BSEM Engagement \u2014 Positive Movement and Rhythm (brain breaks)", "Rhythm to Recovery (NIT lessons)",
        "Relational Mapping (ACF)", "BSEM Stamina \u2014 Emotional Intelligence (emotional communication)",
        "BSEM Engagement \u2014 Willingness (SMART goals, motivational interviewing)",
        "BSEM Character \u2014 Character Strengths (strength of community)", "Secret Agent Society",
    ],
    "Social management": [
        "Child Protection Curriculum", "Restorative Practice", "Relational Mapping",
        "BSEM Relationships \u2014 Attachment (redefining power)", "A 5 is Against the Law (social boundaries)",
        "BSEM Body \u2014 Self Regulation (percussion games, action stations)",
        "BSEM Stamina \u2014 Emotional Intelligence (empathy, how full are their buckets)",
        "BSEM Engagement \u2014 Willingness (problem solving) / Cultivating Wonder (wall of awesome)",
    ],
}
# LBU runs a 3-tier PBS model (confirmed across Zones of Regulation, Secret Agent Society,
# and the Alert Program in the same program map), not a binary Universal/Targeted split.
TIER_OPTIONS = ["Universal curriculum (Tier 1)", "Targeted curriculum (Tier 2)", "Individualised intervention (Tier 3)"]
# Formal/informal assessment sources already in use at LBU (from the same uploaded doc) —
# shown as a reference so an Engagement Profile note can point back to real evidence.
LBU_ASSESSMENTS = [
    "Visual comprehension assessment (formal, once)",
    "Sensory overview (formal pre) / responses to sensory input (informal)",
    "Forced Choice Reinforcement Survey \u2014 likes/dislikes/tolerates (formal pre-test)",
    "ABC (Antecedent-Behaviour-Consequence) scatter plot data (formal, frequent)",
    "Anxiety Scale assessment \u2014 complex Autism (formal pre)",
    "Sounds-Write assessments (formal)",
    "Word Aware vocabulary assessment (formal, every 5 weeks)",
    "Relational Mapping (individualised, needs basis, via Transition Coordinator)",
    "States of arousal \u2014 Window of Tolerance",
    "Memory: Narrative Autobiographical (informal)",
    "Use of language (informal)",
    "Use of higher cognitive functions and social interactions (informal)",
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

st.markdown("""
<div class="pathway-header">
<h1>\U0001f9ed Learning Engagement &amp; Transfer Pathway</h1>
<p>Capture HOW a student engages, so the teaching METHOD can be replicated — not duplicated.</p>
</div>
""", unsafe_allow_html=True)

col_pick, col_badge = st.columns([3, 1])
with col_pick:
    selected_label = st.selectbox("Student", sorted(student_labels.keys()))
student_id = student_labels[selected_label]  # student's initials

# ---- fetch this student's data once, reuse across the header dashboard and every tab ----
existing = sb.table("pathway_profile").select("*").eq("student_id", student_id).execute().data
existing = existing[0] if existing else {}
attached = sb.table("pathway_student_methods").select("id, method_id, pathway_method_bank(*)").eq("student_id", student_id).execute().data

profile_items = sum(len(existing.get(k, [])) for k in
                     ("regulation_state", "sensory_preferences", "relational_trust", "environmental_needs"))
held_contexts = set()
for a in attached:
    logs = sb.table("pathway_application_log").select("context_applied, held_up").eq("student_method_id", a["id"]).execute().data
    held_contexts.update(e["context_applied"] for e in logs if e.get("held_up") in ("Y", "Partial"))

with col_badge:
    initials = student_id[:2].upper()
    st.markdown(f"<div style='padding-top:26px'><span class='student-badge'>{initials}</span></div>", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("Engagement notes", profile_items)
m2.metric("Methods attached", len(attached))
m3.metric("Contexts held in", len(held_contexts))
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    f"{'\u2705 ' if profile_items else ''}\U0001f9e9 Engagement Profile",
    f"{'\u2705 ' if attached else ''}\U0001f9ed Method Signature",
    "\U0001f501 Transfer Mapping",
    "\U0001f4dd Application Log",
    "\U0001f4ca Reporting Roll-up",
])

# ================= TAB 1 — Engagement Profile =================
with tab1:
    st.subheader("\U0001f9e9 How this student comes online")
    st.caption("Click what applies — add your own if it's not listed. This becomes the foundation everything else builds on.")
    with st.expander(f"\U0001f4cb LBU assessment sources that can inform this ({len(LBU_ASSESSMENTS)})"):
        for a_item in LBU_ASSESSMENTS:
            st.write(f"\u2022 {a_item}")

    with st.container(border=True):
        reg = chip_picker("Regulation state / Window of Tolerance", REGULATION_OPTIONS, existing.get("regulation_state", []), "reg")
        sens = chip_picker("Sensory preferences", SENSORY_OPTIONS, existing.get("sensory_preferences", []), "sens")
        rel = chip_picker("Relational trust markers (PACE)", RELATIONAL_OPTIONS, existing.get("relational_trust", []), "rel")
        env = chip_picker("Environmental needs", ENVIRONMENTAL_OPTIONS, existing.get("environmental_needs", []), "env")

    if st.button("\U0001f4be Save Engagement Profile", type="primary"):
        sb.table("pathway_profile").upsert({
            "student_id": student_id, "regulation_state": reg, "sensory_preferences": sens,
            "relational_trust": rel, "environmental_needs": env,
        }).execute()
        st.success("Saved — nice work building this student's profile!")

# ================= TAB 2 — Method Signature =================
with tab2:
    st.subheader("\U0001f9ed The transferable teaching move")
    st.markdown(
        "<span style='background:#DCE6F1;color:#0C447C;padding:2px 10px;border-radius:12px;font-size:13px;'>\u25cf Universal curriculum (Tier 1)</span> "
        "<span style='background:#FFF2CC;color:#854F0B;padding:2px 10px;border-radius:12px;font-size:13px;'>\u25cf Targeted curriculum (Tier 2)</span> "
        "<span style='background:#FADBD8;color:#943126;padding:2px 10px;border-radius:12px;font-size:13px;'>\u25cf Individualised intervention (Tier 3)</span>",
        unsafe_allow_html=True,
    )
    st.caption("LBU's own 3-tier PBS model (seen across Zones of Regulation, Secret Agent Society, and the Alert Program).")
    st.write("")

    bank = sb.table("pathway_method_bank").select("*").order("instructional_move").execute().data
    bank_labels = {f"{m['instructional_move']} \u2014 {m.get('disposition') or 'no disposition set'} ({m['observed_context']})": m for m in bank}

    mode = st.segmented_control("Attach a method to this student", ["Pick from existing bank", "+ New method signature"])

    with st.container(border=True):
        if mode == "Pick from existing bank" and bank_labels:
            pick = st.selectbox("Method", sorted(bank_labels.keys()))
            if st.button("\U0001f517 Attach to student"):
                sb.table("pathway_student_methods").insert({
                    "student_id": student_id, "method_id": bank_labels[pick]["id"],
                }).execute()
                st.success("Attached.")
        else:
            ctx = st.pills("Observed context", CONTEXT_OPTIONS, selection_mode="single")
            if ctx == "Other (add below)":
                ctx = st.text_input("Custom context")
            concrete_move = st.text_area(
                "What did you actually do?",
                placeholder="e.g. I used counters to teach place value, working through ten short problems with a break in the middle",
                key="concrete_move",
            )
            if st.button("\u2728 Turn this into an abstract instructional move"):
                if not concrete_move.strip():
                    st.warning("Describe what you actually did first, above.")
                else:
                    try:
                        prompt = (
                            "A teacher described a lesson activity in plain language. Rewrite it as ONE "
                            "sentence describing the underlying instructional MOVE abstractly enough to "
                            "transfer to a completely different subject — strip out the specific subject, "
                            "content, and materials, and name the teaching technique itself (e.g. "
                            "'concrete-before-abstract sequencing', 'short curiosity-framed task cycles with "
                            "a visible end point', 'choice offered before task begins'). "
                            f"Teacher's description: \"{concrete_move.strip()}\""
                        )
                        draft = groq_ai_call(prompt)
                    except Exception as e:
                        draft = (
                            f"(AI call failed — {e}. Abstract it yourself in the meantime: describe the "
                            "TECHNIQUE, not the subject. E.g. \"used counters to teach place value\" → "
                            "\"concrete-before-abstract sequencing\". Edit the field below.)"
                        )
                    st.session_state["move_draft"] = draft
            move = st.text_area(
                "Instructional move (abstracted)",
                value=st.session_state.get("move_draft", ""),
                help="This is what gets saved and reused across students — keep it free of subject-specific detail.",
            )
            st.markdown("**\U0001f9ed Disposition activated** \u2014 the habit that actually transfers; capability and knowledge below are what gets demonstrated once it does.")
            disposition = st.pills("Disposition activated", DISPOSITION_OPTIONS, selection_mode="single", label_visibility="collapsed")
            if disposition:
                areas = ", ".join(SA_DISPOSITION_LEARNING_AREAS.get(disposition, []))
                st.caption(f"SA Curriculum: *{SA_DISPOSITION_WHAT_IT_IS[disposition]}* Highlighted in: {areas}.")
            else:
                disposition = st.text_input("Not listed? Name it here")
            st.markdown("**\U0001f49b Social & emotional capability** \u2014 prioritised at LBU; from the Australian Curriculum's own Personal and Social Capability elements.")
            social_emotional = st.pills("Social & emotional capability", SEL_ELEMENTS, selection_mode="multi", label_visibility="collapsed") or []
            if social_emotional:
                st.caption(" \u00b7 ".join(f"**{e}**: {SEL_WHAT_IT_IS[e]}" for e in social_emotional))
                lbu_programs = sorted({p for e in social_emotional for p in SEL_LBU_PROGRAMS.get(e, [])})
                with st.expander(f"\U0001f4d6 LBU programs that build this ({len(lbu_programs)})"):
                    for p in lbu_programs:
                        st.write(f"\u2022 {p}")
            caps = st.pills("AC General Capability targeted", AC_CAPABILITIES, selection_mode="multi") or []
            ut = st.segmented_control("Tier", TIER_OPTIONS)
            if st.button("\u2728 Create & attach", type="primary"):
                new = sb.table("pathway_method_bank").insert({
                    "observed_context": ctx, "instructional_move": move, "disposition": disposition,
                    "social_emotional": social_emotional, "ac_capabilities": caps, "universal_or_targeted": ut,
                }).execute().data[0]
                sb.table("pathway_student_methods").insert({
                    "student_id": student_id, "method_id": new["id"],
                }).execute()
                st.session_state.pop("move_draft", None)
                st.success("Created and attached.")

    st.divider()
    st.markdown("**\U0001f4cc Methods attached to this student**")
    if not attached:
        st.caption("Nothing attached yet — pick or create a method signature above to get started.")
    for a in attached:
        m = a["pathway_method_bank"]
        tier = m["universal_or_targeted"]
        badge_colour, badge_text = {
            "Universal curriculum (Tier 1)": ("#DCE6F1", "#0C447C"),
            "Targeted curriculum (Tier 2)": ("#FFF2CC", "#854F0B"),
            "Individualised intervention (Tier 3)": ("#FADBD8", "#943126"),
        }.get(tier, ("#F2F2F2", "#444441"))
        with st.container(border=True):
            st.markdown(
                f"<span style='background:{badge_colour};color:{badge_text};padding:2px 10px;"
                f"border-radius:12px;font-size:12px;font-weight:600;'>{tier}</span>"
                f"&nbsp;&nbsp;**{m['instructional_move']}**",
                unsafe_allow_html=True,
            )
            st.caption(
                f"{m['observed_context']} \u00b7 disposition: **{m.get('disposition') or '\u2014'}** \u00b7 "
                f"SEL: **{', '.join(m.get('social_emotional') or []) or '\u2014'}** \u00b7 {', '.join(m['ac_capabilities'])}"
            )

# ================= TAB 3 — Transfer Mapping =================
with tab3:
    st.subheader("\U0001f501 Where else this disposition shows up")
    st.caption("Disposition-led, not method-led: a disposition like curiosity doesn't care which subject it's in. Ask where else it could be invited — capability and knowledge will follow it in.")
    if not attached:
        st.info("\U0001f449 Attach a method signature in Tab 2 first — Transfer Mapping needs one to work from.")
    else:
        with st.container(border=True):
            method_choice = st.selectbox(
                "Method signature (for its disposition)", attached,
                format_func=lambda a: f"{a['pathway_method_bank']['instructional_move']} — {a['pathway_method_bank'].get('disposition') or 'no disposition set'}",
            )
            st.write(f"Disposition: **{method_choice['pathway_method_bank'].get('disposition') or '\u2014'}**")
            disp = method_choice["pathway_method_bank"].get("disposition")
            suggested = curriculum_suggested_contexts(disp) if disp else []
            if suggested:
                areas = ", ".join(SA_DISPOSITION_LEARNING_AREAS.get(disp, []))
                st.caption(f"\U0001f4a1 SA Curriculum highlights {disp} in: {areas} \u2014 pre-selected below, adjust as needed.")
            other_contexts = st.pills(
                "Other contexts this disposition could show up in", CONTEXT_OPTIONS,
                selection_mode="multi", default=suggested, key="tm_ctx",
            ) or []
            staff_trial = st.text_input("Staff to invite it (comma-separated)")
            if st.button("\U0001f4be Save transfer mapping", type="primary"):
                sb.table("pathway_transfer_map").insert({
                    "student_method_id": method_choice["id"],
                    "other_contexts": other_contexts,
                    "staff_to_trial": [s.strip() for s in staff_trial.split(",") if s.strip()],
                }).execute()
                st.success("Saved.")

# ================= TAB 4 — Application Log =================
with tab4:
    st.subheader("\U0001f4dd Evidence the replication happened")
    if not attached:
        st.info("\U0001f449 Attach a method signature in Tab 2 first — the log needs one to record against.")
    else:
        with st.container(border=True):
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
            if st.button("\U0001f4be Log entry", type="primary"):
                sb.table("pathway_application_log").insert({
                    "student_method_id": log_method["id"], "log_date": str(log_date),
                    "staff": staff, "context_applied": ctx_applied,
                    "held_up": held_up, "adaptation_needed": adaptation,
                }).execute()
                st.success("Logged.")

        entries = sb.table("pathway_application_log").select("*").eq("student_method_id", log_method["id"]).order("log_date").execute().data
        if entries:
            st.markdown("**\U0001f4c3 Log history**")
            st.dataframe(
                [{"Date": e["log_date"], "Staff": e["staff"], "Context": e["context_applied"],
                  "Held up?": e["held_up"], "Adaptation": e["adaptation_needed"]} for e in entries],
                use_container_width=True, hide_index=True,
            )

# ================= TAB 5 — Reporting Roll-up =================
with tab5:
    st.subheader("\U0001f4ca SMARTAR / GAS-aligned roll-up")
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
                st.metric(f"\U0001f9ed {disp}", len(ctxs))
                if ctxs:
                    st.caption(", ".join(sorted(ctxs)))
    else:
        st.info("\U0001f449 No methods attached yet — disposition strength will show here once logged.")

    st.divider()
    st.markdown("**\U0001f4da Capability & knowledge evidence** _(supporting detail — where the disposition showed up, not the headline)_")
    replicated_contexts = {e["context_applied"] for e in all_logs if e["held_up"] in ("Y", "Partial")}
    st.write(f"Contexts replicated in overall: {len(replicated_contexts)} — {', '.join(sorted(replicated_contexts)) or '\u2014'}")

    sel_seen = sorted({el for a in attached for el in (a["pathway_method_bank"].get("social_emotional") or [])})
    st.markdown("**\U0001f49b Social & emotional capability demonstrated** _(LBU priority — shown here as supporting evidence, not separate from the disposition story)_")
    st.write(", ".join(sel_seen) or "\u2014")

    existing_rollup = sb.table("pathway_roll_up").select("*").eq("student_id", student_id).execute().data
    existing_rollup = existing_rollup[0] if existing_rollup else {}

    with st.container(border=True):
        default_primary = ", ".join(disposition_contexts.keys()) if disposition_contexts else ""
        primary_disposition = st.text_input("Primary disposition(s) demonstrated", value=existing_rollup.get("primary_disposition", default_primary))
        smartar_goal = st.text_input("Linked SMARTAR / GAS goal", value=existing_rollup.get("linked_smartar_goal", ""))

        if st.button("\u2728 Draft evidence summary from logged data"):
            try:
                prompt = (
                    "Summarise, in 2-3 sentences for a staff report, the evidence that this student's "
                    f"dispositions have transferred across contexts. Disposition -> contexts held up in: "
                    f"{ {k: sorted(v) for k, v in disposition_contexts.items()} }. Log detail: {all_logs}"
                )
                draft = groq_ai_call(prompt)
            except Exception as e:
                draft = f"(AI call failed — {e}. Draft manually below.)"
            st.session_state["evidence_draft"] = draft

        evidence = st.text_area("Evidence of transfer", value=st.session_state.get("evidence_draft", existing_rollup.get("evidence_of_transfer", "")))
        next_steps = st.text_area("Next steps", value=existing_rollup.get("next_steps", ""))

        if st.button("\U0001f4be Save roll-up", type="primary"):
            sb.table("pathway_roll_up").upsert({
                "student_id": student_id, "linked_smartar_goal": smartar_goal,
                "primary_disposition": primary_disposition,
                "evidence_of_transfer": evidence, "next_steps": next_steps,
            }).execute()
            st.success("Saved.")

    def build_docx() -> bytes:
        """Build a Word report mirroring the CLC-LBU_Learning_Engagement_Transfer_Pathway.docx
        template's visual design — navy header banner, bordered/shaded tables, tier-coloured
        cells — filled with this student's live data."""
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_ALIGN_VERTICAL
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        NAVY = RGBColor(0x1F, 0x38, 0x64)
        WHITE = RGBColor(0xFF, 0xFF, 0xFF)
        GREY_FILL = "F2F2F2"
        TIER_FILLS = {
            "Universal curriculum (Tier 1)": ("DCE6F1", "0C447C"),
            "Targeted curriculum (Tier 2)": ("FFF2CC", "854F0B"),
            "Individualised intervention (Tier 3)": ("FADBD8", "943126"),
        }
        HELD_COLOURS = {"Y": ("E2F0D9", "375623"), "Partial": ("FFF2CC", "854F0B"), "N": ("FADBD8", "943126")}

        def shade_cell(cell, hex_fill):
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), hex_fill)
            cell._tc.get_or_add_tcPr().append(shd)

        def set_cell_text(cell, text, bold=False, color=None, size=10, align=None):
            cell.text = ""
            p = cell.paragraphs[0]
            if align:
                p.alignment = align
            run = p.add_run(text)
            run.bold = bold
            run.font.size = Pt(size)
            if color:
                run.font.color.rgb = color
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        def header_row(table, labels, widths_cm):
            row = table.rows[0].cells
            for i, label in enumerate(labels):
                shade_cell(row[i], "1F3864")
                set_cell_text(row[i], label, bold=True, color=WHITE, size=10)
                table.columns[i].width = Cm(widths_cm[i])

        doc = Document()
        doc.styles["Normal"].font.name = "Calibri"
        doc.styles["Normal"].font.size = Pt(10)
        for section in doc.sections:
            section.left_margin = Cm(1.8)
            section.right_margin = Cm(1.8)
            section.top_margin = Cm(1.5)
            section.bottom_margin = Cm(1.5)

        # ---- navy header banner ----
        banner = doc.add_table(rows=1, cols=1)
        banner.autofit = False
        cell = banner.rows[0].cells[0]
        shade_cell(cell, "1F3864")
        cell.width = Cm(17.5)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run("Learning Engagement & Transfer Pathway")
        run.bold = True
        run.font.size = Pt(20)
        run.font.color.rgb = WHITE
        p2 = cell.add_paragraph()
        p2.paragraph_format.space_after = Pt(6)
        run2 = p2.add_run(f"{student_id}  \u00b7  Program: {selected_label.split('-')[-1]}  \u00b7  Teaching for Transfer series")
        run2.font.size = Pt(11)
        run2.font.color.rgb = RGBColor(0xD6, 0xE0, 0xEE)
        for c in banner.rows[0].cells:
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

        # ---- Part 1: Engagement Profile ----
        h = doc.add_heading("Part 1 \u2014 Engagement Profile", level=1)
        h.runs[0].font.color.rgb = NAVY
        t1 = doc.add_table(rows=1, cols=2)
        t1.style = "Table Grid"
        header_row(t1, ["Domain", "What supports engagement"], [4.5, 13.0])
        for label_, vals in [
            ("Regulation state", existing.get("regulation_state", [])),
            ("Sensory preferences", existing.get("sensory_preferences", [])),
            ("Relational trust (PACE)", existing.get("relational_trust", [])),
            ("Environmental needs", existing.get("environmental_needs", [])),
        ]:
            row = t1.add_row().cells
            set_cell_text(row[0], label_, bold=True, size=10)
            set_cell_text(row[1], ", ".join(vals) or "\u2014", size=10)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ---- Part 2: Method Signatures ----
        h = doc.add_heading("Part 2 \u2014 Method Signatures", level=1)
        h.runs[0].font.color.rgb = NAVY
        t2 = doc.add_table(rows=1, cols=6)
        t2.style = "Table Grid"
        header_row(
            t2, ["Observed context", "Instructional move", "Disposition", "SEL", "AC Capability", "Tier"],
            [2.6, 4.2, 2.2, 2.4, 2.6, 3.3],
        )
        for a in attached:
            m = a["pathway_method_bank"]
            row = t2.add_row().cells
            set_cell_text(row[0], m["observed_context"], size=9)
            set_cell_text(row[1], m["instructional_move"], size=9)
            set_cell_text(row[2], m.get("disposition") or "\u2014", bold=True, size=9)
            set_cell_text(row[3], ", ".join(m.get("social_emotional") or []) or "\u2014", bold=True, size=9)
            set_cell_text(row[4], ", ".join(m["ac_capabilities"]) or "\u2014", size=9)
            tier = m["universal_or_targeted"]
            fill, text_col = TIER_FILLS.get(tier, (GREY_FILL, "444444"))
            shade_cell(row[5], fill)
            set_cell_text(row[5], tier, bold=True, size=9, color=RGBColor.from_string(text_col))
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ---- Part 4: Application Log ----
        h = doc.add_heading("Part 4 \u2014 Application Log", level=1)
        h.runs[0].font.color.rgb = NAVY
        t4 = doc.add_table(rows=1, cols=5)
        t4.style = "Table Grid"
        header_row(t4, ["Date", "Staff", "Context", "Held up?", "Adaptation"], [2.3, 3.7, 3.7, 2.0, 5.5])
        for e in all_logs:
            row = t4.add_row().cells
            set_cell_text(row[0], str(e.get("log_date") or ""), size=9)
            set_cell_text(row[1], str(e.get("staff") or ""), size=9)
            set_cell_text(row[2], str(e.get("context_applied") or ""), size=9)
            held = str(e.get("held_up") or "")
            fill, text_col = HELD_COLOURS.get(held, (GREY_FILL, "444444"))
            shade_cell(row[3], fill)
            set_cell_text(row[3], held, bold=True, size=9, color=RGBColor.from_string(text_col), align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_text(row[4], str(e.get("adaptation_needed") or ""), size=9)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ---- Part 5: Reporting Roll-up ----
        h = doc.add_heading("Part 5 \u2014 Reporting Roll-up", level=1)
        h.runs[0].font.color.rgb = NAVY
        disp_summary = "; ".join(
            f"{d}: {len(c)} context(s) ({', '.join(sorted(c)) or '\u2014'})" for d, c in disposition_contexts.items()
        ) or "\u2014"
        rollup_rows = [
            ("Primary disposition(s) demonstrated", primary_disposition or "\u2014"),
            ("Contexts the disposition held up in", disp_summary),
            ("Linked SMARTAR / GAS goal", smartar_goal or "\u2014"),
            ("Capability & knowledge evidence (supporting detail)",
             f"Contexts replicated overall \u2014 {len(replicated_contexts)} ({', '.join(sorted(replicated_contexts)) or '\u2014'})"),
            ("Social & Emotional Capability demonstrated (LBU priority)", ", ".join(sel_seen) or "\u2014"),
            ("Evidence of transfer", evidence or "\u2014"),
            ("Next steps", next_steps or "\u2014"),
        ]
        t5 = doc.add_table(rows=0, cols=2)
        t5.style = "Table Grid"
        for label_, value in rollup_rows:
            row = t5.add_row().cells
            t5.columns[0].width = Cm(5.5)
            t5.columns[1].width = Cm(12.0)
            shade_cell(row[0], GREY_FILL)
            set_cell_text(row[0], label_, bold=True, size=9.5)
            set_cell_text(row[1], value, size=9.5)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    st.divider()
    st.markdown("**\U0001f4c4 Export**")
    if st.button("\U0001f4c4 Generate & save to archive", type="primary"):
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
