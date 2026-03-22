"""
17_TAC_Meeting_Brief.py
CLC LBU — TAC Meeting Preparation Brief Builder
Two modes: Guided (step-by-step prompting) | Transcript (AI transforms a meeting transcript)
"""

import streamlit as st
import json
import re
from datetime import date, datetime
from io import BytesIO

st.set_page_config(
    page_title="TAC Brief Builder | CLC LBU",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from auth import require_auth, logout_button
require_auth("TAC Brief Builder", "📋")
logout_button("sidebar")

# ── DESIGN ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"]{background:#f0f4f0!important;font-family:'DM Sans',sans-serif}
[data-testid="stHeader"]{display:none}[data-testid="stSidebar"]{display:none}
#MainMenu,footer,.stDeployButton{display:none}
.main .block-container{padding:0!important;max-width:100%!important}
.top-nav{background:#1a2e44;padding:0 2rem;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:1000;box-shadow:0 2px 12px rgba(0,0,0,0.2)}
.top-nav-logo{width:32px;height:32px;background:linear-gradient(135deg,#1a7a6e,#2d9e8f);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;color:white;font-size:.85rem}
.content-area{padding:1.5rem 2rem 4rem;max-width:1300px;margin:0 auto}
.hero{background:linear-gradient(135deg,#1a2e44 0%,#1a7a6e 100%);padding:1.5rem 2rem;border-radius:14px;margin-bottom:1.5rem;color:white}
.hero-title{font-size:1.4rem;font-weight:700;margin-bottom:.2rem}
.hero-sub{font-size:.85rem;opacity:.8}
.step-bar{display:flex;gap:0;margin-bottom:1.5rem;border-radius:10px;overflow:hidden;border:1.5px solid #d8e8d4}
.step-item{flex:1;padding:.55rem .5rem;text-align:center;font-size:.72rem;font-weight:600;color:#7a9a7a;background:white;transition:.15s}
.step-item.active{background:#1a7a6e;color:white}
.step-item.done{background:#e8f5e1;color:#2d6b1a}
.card{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);overflow:hidden;margin-bottom:1.25rem}
.card-header{padding:.65rem 1rem;display:flex;align-items:center;gap:.5rem}
.card-header.teal{background:#1a7a6e}
.card-header.navy{background:#1a2e44}
.card-header.amber{background:#e8a125}
.card-header.red{background:#b91c1c}
.card-header.slate{background:#6a7f8a}
.card-header.green{background:#4a8f33}
.card-header h3{font-size:.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.1em;margin:0}
.card-header.amber h3{color:#1a2e44}
.card-body{padding:1rem 1.25rem}
.mode-tile{border:2.5px solid #e0e8dc;border-radius:12px;padding:1.5rem;cursor:pointer;transition:.15s;background:white;text-align:center}
.mode-tile:hover{border-color:#1a7a6e;box-shadow:0 4px 16px rgba(26,122,110,0.12)}
.mode-tile.selected{border-color:#1a7a6e;background:#f0faf8}
.mode-icon{font-size:2.5rem;margin-bottom:.6rem}
.mode-title{font-weight:700;font-size:1rem;color:#1a2e44;margin-bottom:.3rem}
.mode-desc{font-size:.82rem;color:#7a907a;line-height:1.5}
.prompt-q{background:#f0faf8;border-left:3px solid #1a7a6e;border-radius:0 8px 8px 0;padding:.75rem 1rem;margin-bottom:.5rem;font-size:.88rem;font-weight:600;color:#1a2e44}
.ai-badge{background:#dbeafe;color:#1d4ed8;border-radius:20px;padding:.2rem .6rem;font-size:.68rem;font-weight:600}
.section-label{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#1a7a6e;margin:1rem 0 .3rem}
.info-box{background:#e0f7f4;border-radius:8px;padding:.75rem 1rem;font-size:.82rem;color:#1a2e44;margin-bottom:1rem;border-left:3px solid #1a7a6e}
.stTextInput input,.stTextArea textarea,.stSelectbox select{border:1.5px solid #d8e8d4!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:#1a7a6e!important;box-shadow:0 0 0 3px rgba(26,122,110,0.12)!important}
.stButton button{border-radius:8px!important;font-weight:600!important;font-size:.85rem!important}
.stButton button[kind="primary"]{background:#1a7a6e!important;border:none!important}
.stButton button[kind="primary"]:hover{background:#155f56!important}
label[data-testid="stWidgetLabel"] p{font-size:.72rem!important;font-weight:600!important;color:#4a6a5a!important;text-transform:uppercase!important;letter-spacing:.06em!important}
[data-baseweb="tab-list"]{background:transparent!important;gap:.25rem!important;border-bottom:2px solid #e0e8dc!important;padding:0!important}
[data-baseweb="tab"]{background:transparent!important;border-radius:8px 8px 0 0!important;padding:.5rem 1rem!important;font-size:.82rem!important;font-weight:600!important;color:#7a907a!important;border:none!important}
[aria-selected="true"][data-baseweb="tab"]{background:white!important;color:#1a7a6e!important;border-bottom:2px solid #1a7a6e!important}
</style>
""", unsafe_allow_html=True)

# ── GROQ ─────────────────────────────────────────────────────
def groq_call(prompt: str, max_tokens: int = 3000, system: str = "") -> str:
    try:
        from groq import Groq
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens,
            messages=messages
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[AI error: {e}]"

# ── SESSION STATE ─────────────────────────────────────────────
def init():
    defaults = {
        "tac_step": 1,           # 1=mode, 2=student, 3=content, 4=review, 5=done
        "tac_mode": None,        # "guided" | "transcript"
        "student": {
            "name": "", "dob": "", "age": "", "edsas": "",
            "home_school": "", "program": "JP", "plan_date": str(date.today()),
            "meeting_date": "", "meeting_location": "", "meeting_purpose": "",
            "attendees": "",
        },
        "brief": {
            "purpose": "",
            "agenda": [],         # list of {title, bullets:[str], sub:[{text,bullets}]}
            "bse_questions": [],  # list of {q, context}
            "clc_evidence": "",
            "clc_needs_tac": "",
            "immediate_risks": "",
            "actions": [],        # list of {owner, action, priority}
        },
        "transcript_text": "",
        "ai_working": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init()

s = st.session_state.student
b = st.session_state.brief
TEAL = "#1a7a6e"
NAVY = "#1a2e44"

# ── TOP NAV ───────────────────────────────────────────────────
st.markdown("""
<div class="top-nav">
  <div style="display:flex;align-items:center;gap:.75rem;">
    <div class="top-nav-logo">TAC</div>
    <div>
      <div style="font-weight:700;font-size:.95rem;color:white;">TAC Brief Builder</div>
      <div style="font-size:.72rem;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:.06em;">CLC LBU — Meeting Preparation</div>
    </div>
  </div>
  <div style="font-size:.75rem;color:rgba(255,255,255,.5);">📋 Cowandilla Learning Centre</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="content-area">', unsafe_allow_html=True)

# ── STEP BAR ──────────────────────────────────────────────────
STEPS = ["1 · Mode","2 · Student","3 · Content","4 · Review","5 · Download"]
step_html = '<div class="step-bar">'
for i, label in enumerate(STEPS, 1):
    cls = "active" if i == st.session_state.tac_step else ("done" if i < st.session_state.tac_step else "")
    step_html += f'<div class="step-item {cls}">{label}</div>'
step_html += "</div>"
st.markdown(step_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STEP 1 — MODE SELECTION
# ══════════════════════════════════════════════════════════════
if st.session_state.tac_step == 1:
    st.markdown("""
    <div class="hero">
      <div class="hero-title">📋 TAC Meeting Preparation Brief</div>
      <div class="hero-sub">Build a professional, structured TAC Preparation Brief — guided step-by-step or by transforming a meeting transcript.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**How would you like to build this brief?**")
    m1, m2 = st.columns(2)

    with m1:
        sel_guided = st.session_state.tac_mode == "guided"
        st.markdown(f'<div class="mode-tile {"selected" if sel_guided else ""}">'
            f'<div class="mode-icon">🧭</div>'
            f'<div class="mode-title">Guided Builder</div>'
            f'<div class="mode-desc">I\'ll prompt you through each section of the brief — purpose of meeting, agenda items, questions for the BSE, CLC position, and action items. Best when building from scratch or planning ahead of a meeting.</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button("Select: Guided Builder", type="primary" if sel_guided else "secondary",
                     use_container_width=True, key="sel_guided"):
            st.session_state.tac_mode = "guided"
            st.rerun()

    with m2:
        sel_trans = st.session_state.tac_mode == "transcript"
        st.markdown(f'<div class="mode-tile {"selected" if sel_trans else ""}">'
            f'<div class="mode-icon">🎙️</div>'
            f'<div class="mode-title">Transcript Transform</div>'
            f'<div class="mode-desc">Paste or upload a transcript from a previous TAC or planning meeting. The AI will read it and draft the full brief for you — including agenda items, questions, CLC position, and actions. You review and edit before downloading.</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button("Select: Transcript Transform", type="primary" if sel_trans else "secondary",
                     use_container_width=True, key="sel_trans"):
            st.session_state.tac_mode = "transcript"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.tac_mode:
        mode_label = "Guided Builder 🧭" if st.session_state.tac_mode == "guided" else "Transcript Transform 🎙️"
        st.success(f"Selected: **{mode_label}**")
        if st.button("Continue →", type="primary"):
            st.session_state.tac_step = 2
            st.rerun()

# ══════════════════════════════════════════════════════════════
# STEP 2 — STUDENT DETAILS
# ══════════════════════════════════════════════════════════════
elif st.session_state.tac_step == 2:
    st.markdown('<div class="card"><div class="card-header teal"><h3>👤 Student Snapshot</h3></div><div class="card-body">', unsafe_allow_html=True)
    st.markdown('<div class="info-box">These details populate the Student Snapshot section at the top of the brief. DOB, EDSAS and home school are required.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        s["name"]         = st.text_input("Full name *", value=s["name"], placeholder="e.g. Xavier Shilton Sumner")
        s["dob"]          = st.text_input("Date of birth * (DD/MM/YYYY)", value=s["dob"])
        s["age"]          = st.text_input("Age", value=s["age"])
        s["edsas"]        = st.text_input("EDSAS ID *", value=s["edsas"], placeholder="e.g. 10981999M")
        s["home_school"]  = st.text_input("Home school *", value=s["home_school"], placeholder="e.g. Mount Barker Primary School")
    with c2:
        s["program"]      = st.selectbox("CLC Program", ["JP","PY","SY","Other"],
                                index=["JP","PY","SY","Other"].index(s["program"]) if s["program"] in ["JP","PY","SY","Other"] else 0)
        s["meeting_date"] = st.text_input("TAC meeting date", value=s["meeting_date"], placeholder="e.g. Monday 23 March 2026")
        s["meeting_location"] = st.text_input("Meeting location / platform", value=s["meeting_location"], placeholder="e.g. CLC Office / Teams")
        s["attendees"]    = st.text_area("Expected attendees (one per line)", value=s["attendees"], height=110,
                                placeholder="e.g.\nAnnette (CLC)\nSarah Cromer (BSE)\nKinship carer\nDCP worker")
        s["plan_date"]    = st.text_input("Brief prepared date", value=s["plan_date"])

    st.markdown('</div></div>', unsafe_allow_html=True)

    # Additional context
    st.markdown('<div class="card"><div class="card-header navy"><h3>📋 Student Context</h3></div><div class="card-body">', unsafe_allow_html=True)
    st.markdown("*Brief context about this student at CLC — background, current concerns, key needs. This feeds the AI for both modes.*")

    c3, c4 = st.columns(2)
    with c3:
        s["disability_diagnosis"] = st.text_area(
            "Disability / diagnosis / medical background",
            value=s.get("disability_diagnosis",""),
            height=100,
            placeholder="e.g. ADHD — medication transition in progress. Possible ABI under investigation. Kinship care, DCP involved."
        )
        s["behaviour_profile"] = st.text_area(
            "Behaviour profile at CLC",
            value=s.get("behaviour_profile",""),
            height=100,
            placeholder="e.g. Rapid escalation, fence climbing, absconding, peer-triggered. Responds well to movement and 1:1."
        )
    with c4:
        s["placement_context"] = st.text_area(
            "Exclusion / placement context",
            value=s.get("placement_context",""),
            height=100,
            placeholder="e.g. Excluded from home school after absconding onto Hahndorf Freeway. DCP vehicle for transport."
        )
        s["support_context"] = st.text_area(
            "Support team / funding context",
            value=s.get("support_context",""),
            height=100,
            placeholder="e.g. NDIS: OT, play therapist, PBS. ISP funding at home school — allocation under review."
        )
    st.markdown('</div></div>', unsafe_allow_html=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("← Back", use_container_width=True):
            st.session_state.tac_step = 1; st.rerun()
    with bc2:
        if st.button("Continue →", type="primary", use_container_width=True):
            errors = []
            if not s["name"].strip():      errors.append("Student name is required.")
            if not s["dob"].strip():       errors.append("Date of birth is required.")
            if not s["edsas"].strip():     errors.append("EDSAS ID is required.")
            if not s["home_school"].strip(): errors.append("Home school is required.")
            if errors:
                for e in errors: st.error(e)
            else:
                st.session_state.tac_step = 3
                st.rerun()

# ══════════════════════════════════════════════════════════════
# STEP 3 — CONTENT (GUIDED or TRANSCRIPT)
# ══════════════════════════════════════════════════════════════
elif st.session_state.tac_step == 3:

    # ── SYSTEM PROMPT HELPER ──────────────────────────────────
    def _student_context_str():
        return f"""
Student: {s['name']} | DOB: {s['dob']} | Age: {s['age']} | EDSAS: {s['edsas']}
Home school: {s['home_school']} | CLC Program: {s['program']}
Disability/medical: {s.get('disability_diagnosis','')}
Behaviour profile: {s.get('behaviour_profile','')}
Placement context: {s.get('placement_context','')}
Support/funding: {s.get('support_context','')}
Meeting date: {s['meeting_date']} | Attendees: {s['attendees']}
"""

    SYSTEM_PROMPT = """You are a specialist educator at Cowandilla Learning Centre (CLC) LBU in Adelaide, South Australia.
CLC is a program option for students with educational exclusion.
You write professional, evidence-based TAC (Team Around the Child) meeting preparation briefs.
Language is clear, specific, and professional. Avoid jargon. Use observable, evidence-based descriptions.
All content must relate specifically to the student described — do not generalise."""

    # ══ GUIDED MODE ══════════════════════════════════════════
    if st.session_state.tac_mode == "guided":
        tabs = st.tabs(["📌 Purpose & Agenda","❓ BSE Questions","🏫 CLC Position","✅ Actions"])

        # ── TAB 1: Purpose & Agenda ───────────────────────────
        with tabs[0]:
            st.markdown('<div class="card"><div class="card-header teal"><h3>Purpose of This Meeting</h3></div><div class="card-body">', unsafe_allow_html=True)
            st.markdown('<div class="prompt-q">What is the specific purpose of this TAC meeting? What has triggered it, and what does CLC need the TAC to agree on or action?</div>', unsafe_allow_html=True)

            b["purpose"] = st.text_area(
                "Meeting purpose",
                value=b["purpose"],
                height=130,
                placeholder="e.g. This TAC follows a critical incident on [date] in which [student] absconded from CLC grounds… The meeting will review the Safety & Risk Plan, discuss the learning model, and clarify medication and attendance arrangements.",
                label_visibility="collapsed"
            )

            ai1, ai2 = st.columns([1,5])
            with ai1:
                if st.button("✨ AI Draft", key="ai_purpose"):
                    with st.spinner("Drafting purpose…"):
                        b["purpose"] = groq_call(
                            f"Write a professional, specific meeting purpose paragraph (3-5 sentences) for a TAC preparation brief. Student context:\n{_student_context_str()}\nFocus on: what triggered this meeting, what CLC needs the TAC to address, and what outcomes are needed.",
                            800, SYSTEM_PROMPT
                        )
                    st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

            # Agenda items
            st.markdown('<div class="card"><div class="card-header navy"><h3>Proposed Agenda Items</h3></div><div class="card-body">', unsafe_allow_html=True)
            st.markdown('<div class="prompt-q">What are the key agenda items for this TAC? Add each item below — title and the key discussion points or questions under each one.</div>', unsafe_allow_html=True)

            if not b["agenda"]:
                b["agenda"] = [{"title":"", "content":""}]

            for ai_idx, item in enumerate(b["agenda"]):
                st.markdown(f'<div style="background:#f8fdf8;border:1.5px solid #d0e8d0;border-radius:10px;padding:.85rem;margin-bottom:.6rem;">', unsafe_allow_html=True)
                ac1, ac2 = st.columns([4,1])
                with ac1:
                    item["title"] = st.text_input(
                        f"Agenda item {ai_idx+1} title",
                        value=item["title"],
                        placeholder="e.g. Safety & Risk Plan — review and sign-off",
                        key=f"ag_title_{ai_idx}"
                    )
                with ac2:
                    st.markdown("<div style='padding-top:1.75rem;'>", unsafe_allow_html=True)
                    if ai_idx > 0:
                        if st.button("🗑️", key=f"ag_del_{ai_idx}", use_container_width=True):
                            b["agenda"].pop(ai_idx); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                item["content"] = st.text_area(
                    "Discussion points / questions / proposals",
                    value=item["content"],
                    height=120,
                    placeholder="e.g.\n• Review the updated Safety & Risk Management Plan\n• Confirm environmental modifications made at CLC\n• Discuss CCRP escalation",
                    key=f"ag_content_{ai_idx}"
                )

                aic1, aic2 = st.columns([1,5])
                with aic1:
                    if item["title"] and st.button("✨ AI Expand", key=f"ai_agenda_{ai_idx}"):
                        with st.spinner(f"Expanding '{item['title']}'…"):
                            result = groq_call(
                                f"Write 4-6 specific, actionable discussion points for the agenda item titled '{item['title']}' in a TAC meeting preparation brief.\nStudent context:\n{_student_context_str()}\nReturn as bullet points starting with •, no preamble.",
                                600, SYSTEM_PROMPT
                            )
                            item["content"] = result
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            ba1, ba2 = st.columns([1,3])
            with ba1:
                if st.button("➕ Add Agenda Item", use_container_width=True):
                    b["agenda"].append({"title":"","content":""}); st.rerun()
            with ba2:
                if st.button("✨ AI Suggest Agenda", use_container_width=True, key="ai_agenda_full"):
                    with st.spinner("Generating agenda…"):
                        raw = groq_call(
                            f"""Generate a TAC meeting agenda for this student. Return as JSON array only (no markdown):
[{{"title":"agenda item title","content":"bullet points as single string with \\n• between items"}}]
Include 5-7 agenda items covering: safety/risk plan, learning model, any medical/medication issues, attendance, funding/support, assessments, transition planning.
Student context:\n{_student_context_str()}""",
                            1500, SYSTEM_PROMPT
                        )
                        raw = raw.replace("```json","").replace("```","").strip()
                        try:
                            b["agenda"] = json.loads(raw)
                        except:
                            st.warning("Could not parse AI agenda. Try again or add items manually.")
                    st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

        # ── TAB 2: BSE Questions ──────────────────────────────
        with tabs[1]:
            st.markdown('<div class="card"><div class="card-header teal"><h3>Questions for the BSE / Support Specialist</h3></div><div class="card-body">', unsafe_allow_html=True)
            st.markdown('<div class="prompt-q">What questions does CLC need to put to the Behaviour Support Educator or other specialist at this meeting? Include the context/reasoning behind each question.</div>', unsafe_allow_html=True)

            if not b["bse_questions"]:
                b["bse_questions"] = [{"q":"","context":""}]

            for qi, qitem in enumerate(b["bse_questions"]):
                st.markdown('<div style="background:#f8fdf8;border:1.5px solid #d0e8d0;border-radius:10px;padding:.85rem;margin-bottom:.6rem;">', unsafe_allow_html=True)
                qc1, qc2 = st.columns([4,1])
                with qc1:
                    qitem["q"] = st.text_input(
                        f"Question {qi+1}",
                        value=qitem["q"],
                        placeholder="e.g. Is this case appropriate for escalation to CCRP?",
                        key=f"bse_q_{qi}"
                    )
                with qc2:
                    st.markdown("<div style='padding-top:1.75rem;'>", unsafe_allow_html=True)
                    if qi > 0:
                        if st.button("🗑️", key=f"bse_del_{qi}", use_container_width=True):
                            b["bse_questions"].pop(qi); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                qitem["context"] = st.text_area(
                    "Context / reasoning behind this question",
                    value=qitem["context"],
                    height=80,
                    placeholder="e.g. Given the severity of risk (absconding onto arterial roads) and the complexity of need, we want to understand whether CCRP escalation is warranted and what that process would involve.",
                    key=f"bse_ctx_{qi}"
                )
                st.markdown('</div>', unsafe_allow_html=True)

            qb1, qb2 = st.columns([1,3])
            with qb1:
                if st.button("➕ Add Question", use_container_width=True):
                    b["bse_questions"].append({"q":"","context":""}); st.rerun()
            with qb2:
                if st.button("✨ AI Generate Questions", use_container_width=True, key="ai_bse_full"):
                    with st.spinner("Generating BSE questions…"):
                        raw = groq_call(
                            f"""Generate 6-8 specific, well-contextualised questions for a BSE/support specialist at a TAC meeting.
Return as JSON array only (no markdown):
[{{"q":"specific question","context":"2-3 sentence context explaining why CLC is asking this"}}]
Questions should cover: risk escalation (CCRP), funding/ISP allocation, current intervention effectiveness, assessment pathways (psych/speech), medication management, and transition planning.
Student context:\n{_student_context_str()}""",
                            2000, SYSTEM_PROMPT
                        )
                        raw = raw.replace("```json","").replace("```","").strip()
                        try:
                            b["bse_questions"] = json.loads(raw)
                        except:
                            st.warning("Could not parse. Try again or add questions manually.")
                    st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

        # ── TAB 3: CLC Position ───────────────────────────────
        with tabs[2]:
            st.markdown('<div class="card"><div class="card-header teal"><h3>CLC Position — Key Messages for TAC</h3></div><div class="card-body">', unsafe_allow_html=True)
            st.markdown('<div class="prompt-q">What is CLC\'s evidence-based position going into this meeting? Complete the three sections below.</div>', unsafe_allow_html=True)

            b["clc_evidence"] = st.text_area(
                "What the evidence from CLC is telling us",
                value=b["clc_evidence"],
                height=130,
                placeholder="e.g.\n• Student requires a movement-based, low-demand, 1:1 learning environment\n• Group program is not safe or appropriate at this stage\n• Transitions require individual planning",
                key="clc_ev"
            )
            b["clc_needs_tac"] = st.text_area(
                "What CLC needs the TAC to understand",
                value=b["clc_needs_tac"],
                height=110,
                placeholder="e.g.\n• CLC can trial 1:1 now because numbers are low — this cannot be guaranteed long-term\n• The trial will generate data the TAC can use for transition planning",
                key="clc_nt"
            )
            b["immediate_risks"] = st.text_area(
                "Immediate risks requiring TAC agreement",
                value=b["immediate_risks"],
                height=110,
                placeholder="e.g.\n• Medication transition window — elevated absconding risk\n• Fence/gate audit required\n• SAPOL protocol — once called, staff do not pursue by vehicle",
                key="clc_ir"
            )

            ai_pos = st.columns([1,5])
            with ai_pos[0]:
                if st.button("✨ AI Draft All", key="ai_clc_pos"):
                    with st.spinner("Drafting CLC position…"):
                        raw = groq_call(
                            f"""Draft the three CLC position sections for a TAC preparation brief. Return as JSON only (no markdown):
{{"evidence":"bullet points as string with \\n• between items","needs_tac":"bullet points","immediate_risks":"bullet points"}}
Student context:\n{_student_context_str()}""",
                            1200, SYSTEM_PROMPT
                        )
                        raw = raw.replace("```json","").replace("```","").strip()
                        try:
                            parsed = json.loads(raw)
                            b["clc_evidence"]    = parsed.get("evidence","")
                            b["clc_needs_tac"]   = parsed.get("needs_tac","")
                            b["immediate_risks"] = parsed.get("immediate_risks","")
                        except:
                            st.warning("Could not parse AI response. Fill in manually or try again.")
                    st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

        # ── TAB 4: Actions ────────────────────────────────────
        with tabs[3]:
            st.markdown('<div class="card"><div class="card-header teal"><h3>Actions — To Be Confirmed at TAC</h3></div><div class="card-body">', unsafe_allow_html=True)
            st.markdown('<div class="prompt-q">What actions need to be assigned and agreed at this meeting? For each action note the owner (e.g. CLC, BSE, SSS, DCP, Family, All) and priority (URGENT / STANDARD).</div>', unsafe_allow_html=True)

            if not b["actions"]:
                b["actions"] = [{"owner":"CLC","action":"","priority":"STANDARD"}]

            for ai2_idx, action in enumerate(b["actions"]):
                ac1, ac2, ac3, ac4 = st.columns([1.5, 5, 1.5, 0.6])
                with ac1:
                    action["owner"] = st.text_input("Owner", value=action["owner"],
                        key=f"act_own_{ai2_idx}", placeholder="e.g. CLC")
                with ac2:
                    action["action"] = st.text_input("Action", value=action["action"],
                        key=f"act_txt_{ai2_idx}", placeholder="e.g. Conduct fence/gate risk audit")
                with ac3:
                    action["priority"] = st.selectbox("Priority", ["URGENT","STANDARD"],
                        index=0 if action["priority"]=="URGENT" else 1,
                        key=f"act_pri_{ai2_idx}")
                with ac4:
                    st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                    if ai2_idx > 0:
                        if st.button("✕", key=f"act_del_{ai2_idx}"): b["actions"].pop(ai2_idx); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            ab1, ab2 = st.columns([1,3])
            with ab1:
                if st.button("➕ Add Action", use_container_width=True):
                    b["actions"].append({"owner":"CLC","action":"","priority":"STANDARD"}); st.rerun()
            with ab2:
                if st.button("✨ AI Generate Actions", use_container_width=True, key="ai_actions"):
                    with st.spinner("Generating action list…"):
                        raw = groq_call(
                            f"""Generate 10-14 specific action items for a TAC meeting, matching this student's situation.
Return as JSON array only (no markdown):
[{{"owner":"owner name","action":"specific action description","priority":"URGENT or STANDARD"}}]
Owners: CLC, BSE, SSS, DCP, Family, All, CLC/BSE, BSE/SSS
Cover: safety audit, plan sign-off, learning model trial, medication, assessment pathways, funding, transition planning.
Student context:\n{_student_context_str()}""",
                            1500, SYSTEM_PROMPT
                        )
                        raw = raw.replace("```json","").replace("```","").strip()
                        try:
                            b["actions"] = json.loads(raw)
                        except:
                            st.warning("Could not parse. Try again or add manually.")
                    st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

    # ══ TRANSCRIPT MODE ═══════════════════════════════════════
    else:
        st.markdown('<div class="card"><div class="card-header teal"><h3>🎙️ Paste Meeting Transcript</h3></div><div class="card-body">', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
        Paste the transcript below — this can be a Teams auto-transcript, meeting notes, a voice memo transcription,
        or even rough notes from a previous TAC or planning conversation.
        The AI will read it and draft the full brief. You review and edit in the next step.
        </div>
        """, unsafe_allow_html=True)

        st.session_state.transcript_text = st.text_area(
            "Transcript / meeting notes",
            value=st.session_state.transcript_text,
            height=320,
            placeholder="Paste your transcript or meeting notes here…\n\nCan include:\n• Teams / Zoom auto-transcript\n• Dictated voice memo text\n• Hand-written notes typed up\n• Previous TAC meeting minutes\n• Planning conversation notes",
            label_visibility="collapsed"
        )

        if st.session_state.transcript_text.strip():
            st.success(f"✅ {len(st.session_state.transcript_text.split())} words — ready to transform")

        # File upload option
        st.markdown("**Or upload a .txt file:**")
        uploaded_txt = st.file_uploader("Upload transcript (.txt)", type=["txt"], key="transcript_upload")
        if uploaded_txt:
            st.session_state.transcript_text = uploaded_txt.read().decode("utf-8", errors="ignore")
            st.rerun()

        st.markdown('</div></div>', unsafe_allow_html=True)

        if st.session_state.transcript_text.strip():
            if st.button("✨ Transform Transcript into Brief", type="primary", use_container_width=True, key="ai_transform"):
                with st.spinner("Reading transcript and drafting brief — this may take 30 seconds…"):
                    prompt = f"""You are building a TAC Meeting Preparation Brief for Cowandilla Learning Centre (CLC) LBU.

STUDENT DETAILS:
{_student_context_str()}

TRANSCRIPT / MEETING NOTES:
{st.session_state.transcript_text[:12000]}

Based ONLY on what is actually discussed in the transcript above, draft the full brief content.
Do not invent information not present in the transcript.

Return as JSON only (no markdown fences):
{{
  "purpose": "2-4 sentence paragraph describing the purpose of this TAC meeting",
  "agenda": [
    {{"title":"agenda item title","content":"bullet points as string with \\n• between items"}}
  ],
  "bse_questions": [
    {{"q":"question for BSE/specialist","context":"2-3 sentence context"}}
  ],
  "clc_evidence": "bullet points as string with \\n• between items",
  "clc_needs_tac": "bullet points as string with \\n• between items",
  "immediate_risks": "bullet points as string with \\n• between items",
  "actions": [
    {{"owner":"owner","action":"specific action","priority":"URGENT or STANDARD"}}
  ]
}}

Include 5-7 agenda items, 5-8 BSE questions, 8-14 actions. Be specific and grounded in the transcript evidence."""

                    raw = groq_call(prompt, 4000, SYSTEM_PROMPT)
                    raw = raw.replace("```json","").replace("```","").strip()
                    if not raw.startswith("{"):
                        idx = raw.find("{")
                        if idx != -1: raw = raw[idx:]
                    try:
                        parsed = json.loads(raw)
                        b["purpose"]         = parsed.get("purpose","")
                        b["agenda"]          = parsed.get("agenda",[])
                        b["bse_questions"]   = parsed.get("bse_questions",[])
                        b["clc_evidence"]    = parsed.get("clc_evidence","")
                        b["clc_needs_tac"]   = parsed.get("clc_needs_tac","")
                        b["immediate_risks"] = parsed.get("immediate_risks","")
                        b["actions"]         = parsed.get("actions",[])
                        st.success("✅ Brief drafted from transcript — move to the next step to review and edit.")
                        st.session_state.tac_step = 4
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not parse AI response ({e}). Try again.")

    # ── Nav buttons ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    n1, n2 = st.columns(2)
    with n1:
        if st.button("← Back to Student Details", use_container_width=True):
            st.session_state.tac_step = 2; st.rerun()
    with n2:
        if st.button("Review Brief →", type="primary", use_container_width=True):
            st.session_state.tac_step = 4; st.rerun()


# ══════════════════════════════════════════════════════════════
# STEP 4 — REVIEW & EDIT
# ══════════════════════════════════════════════════════════════
elif st.session_state.tac_step == 4:
    st.markdown('<div class="info-box">Review and edit all sections below before generating the final document. Every field is editable.</div>', unsafe_allow_html=True)

    rev_tabs = st.tabs(["📋 Purpose & Agenda","❓ BSE Questions","🏫 CLC Position","✅ Actions","👤 Student"])

    with rev_tabs[0]:
        st.markdown('<div class="section-label">Meeting Purpose</div>', unsafe_allow_html=True)
        b["purpose"] = st.text_area("Purpose", value=b["purpose"], height=120, label_visibility="collapsed", key="rev_purpose")

        st.markdown('<div class="section-label">Proposed Agenda</div>', unsafe_allow_html=True)
        if not b["agenda"]:
            b["agenda"] = [{"title":"","content":""}]
        for ri, item in enumerate(b["agenda"]):
            st.markdown(f'<div style="background:#f8fdf8;border:1.5px solid #d0e8d0;border-radius:8px;padding:.75rem;margin-bottom:.5rem;">', unsafe_allow_html=True)
            rc1, rc2 = st.columns([5,1])
            with rc1:
                item["title"] = st.text_input(f"Item {ri+1} title", value=item["title"], key=f"rev_agt_{ri}")
            with rc2:
                st.markdown("<div style='padding-top:1.75rem;'>", unsafe_allow_html=True)
                if ri > 0 and st.button("🗑️", key=f"rev_agd_{ri}"): b["agenda"].pop(ri); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            item["content"] = st.text_area("Discussion points", value=item["content"], height=100, key=f"rev_agc_{ri}", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
        if st.button("➕ Add Agenda Item", key="rev_add_ag"): b["agenda"].append({"title":"","content":""}); st.rerun()

    with rev_tabs[1]:
        st.markdown('<div class="section-label">Questions for BSE / Support Specialist</div>', unsafe_allow_html=True)
        if not b["bse_questions"]:
            b["bse_questions"] = [{"q":"","context":""}]
        for qi, qitem in enumerate(b["bse_questions"]):
            st.markdown('<div style="background:#f8fdf8;border:1.5px solid #d0e8d0;border-radius:8px;padding:.75rem;margin-bottom:.5rem;">', unsafe_allow_html=True)
            qc1, qc2 = st.columns([5,1])
            with qc1:
                qitem["q"] = st.text_input(f"Q{qi+1}", value=qitem["q"], key=f"rev_q_{qi}")
            with qc2:
                st.markdown("<div style='padding-top:1.75rem;'>", unsafe_allow_html=True)
                if qi > 0 and st.button("🗑️", key=f"rev_qd_{qi}"): b["bse_questions"].pop(qi); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            qitem["context"] = st.text_area("Context", value=qitem["context"], height=75, key=f"rev_qc_{qi}", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
        if st.button("➕ Add Question", key="rev_add_q"): b["bse_questions"].append({"q":"","context":""}); st.rerun()

    with rev_tabs[2]:
        b["clc_evidence"]    = st.text_area("What the evidence from CLC is telling us", value=b["clc_evidence"], height=120, key="rev_ev")
        b["clc_needs_tac"]   = st.text_area("What CLC needs the TAC to understand", value=b["clc_needs_tac"], height=100, key="rev_nt")
        b["immediate_risks"] = st.text_area("Immediate risks requiring TAC agreement", value=b["immediate_risks"], height=100, key="rev_ir")

    with rev_tabs[3]:
        if not b["actions"]:
            b["actions"] = [{"owner":"CLC","action":"","priority":"STANDARD"}]
        for ai_idx3, action in enumerate(b["actions"]):
            ac1, ac2, ac3, ac4 = st.columns([1.5,5,1.5,.6])
            with ac1: action["owner"]    = st.text_input("Owner", value=action["owner"], key=f"rev_ao_{ai_idx3}")
            with ac2: action["action"]   = st.text_input("Action", value=action["action"], key=f"rev_at_{ai_idx3}")
            with ac3: action["priority"] = st.selectbox("Priority", ["URGENT","STANDARD"],
                index=0 if action.get("priority","")=="URGENT" else 1, key=f"rev_ap_{ai_idx3}")
            with ac4:
                st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
                if ai_idx3 > 0 and st.button("✕", key=f"rev_ad_{ai_idx3}"): b["actions"].pop(ai_idx3); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        if st.button("➕ Add Action", key="rev_add_ac"): b["actions"].append({"owner":"CLC","action":"","priority":"STANDARD"}); st.rerun()

    with rev_tabs[4]:
        c1r, c2r = st.columns(2)
        with c1r:
            s["name"]         = st.text_input("Full name", value=s["name"], key="rev_sn")
            s["dob"]          = st.text_input("Date of birth", value=s["dob"], key="rev_dob")
            s["age"]          = st.text_input("Age", value=s["age"], key="rev_age")
            s["edsas"]        = st.text_input("EDSAS ID", value=s["edsas"], key="rev_eid")
            s["home_school"]  = st.text_input("Home school", value=s["home_school"], key="rev_hs")
        with c2r:
            s["program"]       = st.text_input("CLC Program", value=s["program"], key="rev_prog")
            s["meeting_date"]  = st.text_input("Meeting date", value=s["meeting_date"], key="rev_md")
            s["meeting_location"] = st.text_input("Meeting location", value=s["meeting_location"], key="rev_ml")
            s["attendees"]     = st.text_area("Attendees", value=s["attendees"], height=100, key="rev_att")

    st.markdown("<br>", unsafe_allow_html=True)
    rv1, rv2 = st.columns(2)
    with rv1:
        if st.button("← Back to Content", use_container_width=True):
            st.session_state.tac_step = 3; st.rerun()
    with rv2:
        if st.button("📄 Generate Document →", type="primary", use_container_width=True):
            st.session_state.tac_step = 5; st.rerun()


# ══════════════════════════════════════════════════════════════
# STEP 5 — GENERATE & DOWNLOAD
# ══════════════════════════════════════════════════════════════
elif st.session_state.tac_step == 5:

    def build_docx():
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
        import copy

        doc = Document()

        # Page margins
        for section in doc.sections:
            section.page_width  = Cm(29.7)
            section.page_height = Cm(21.0)
            section.left_margin = section.right_margin = Cm(1.8)
            section.top_margin  = section.bottom_margin = Cm(1.5)

        TEAL_RGB   = RGBColor(0x1a, 0x7a, 0x6e)
        NAVY_RGB   = RGBColor(0x1a, 0x2e, 0x44)
        AMBER_RGB  = RGBColor(0xe8, 0xa1, 0x25)
        RED_RGB    = RGBColor(0xb9, 0x1c, 0x1c)
        BODY_RGB   = RGBColor(0x2e, 0x40, 0x57)
        WHITE_RGB  = RGBColor(0xff, 0xff, 0xff)
        CREAM_RGB  = RGBColor(0xfe, 0xf3, 0xc7)
        LTGREY_RGB = RGBColor(0xf2, 0xf6, 0xf6)

        def hex_fill(cell, hex_color):
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), hex_color)
            tcPr.append(shd)

        def cell_border(cell, color_hex="1A7A6E"):
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement("w:tcBorders")
            for side in ["top","left","bottom","right"]:
                b = OxmlElement(f"w:{side}")
                b.set(qn("w:val"), "single")
                b.set(qn("w:sz"), "4")
                b.set(qn("w:color"), color_hex)
                tcBorders.append(b)
            tcPr.append(tcBorders)

        def no_border(cell):
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement("w:tcBorders")
            for side in ["top","left","bottom","right","insideH","insideV"]:
                b = OxmlElement(f"w:{side}")
                b.set(qn("w:val"), "none")
                b.set(qn("w:sz"), "0")
                b.set(qn("w:color"), "FFFFFF")
                tcBorders.append(b)
            tcPr.append(tcBorders)

        def para(cell_or_doc, text, bold=False, size=9, color=None, space_before=30, space_after=30, align=None, italic=False):
            if hasattr(cell_or_doc, "paragraphs") and hasattr(cell_or_doc, "_tc"):
                p = cell_or_doc.add_paragraph()
            else:
                p = cell_or_doc.add_paragraph()
            p.paragraph_format.space_before = Pt(space_before / 4)
            p.paragraph_format.space_after  = Pt(space_after / 4)
            if align: p.alignment = align
            run = p.add_run(text)
            run.bold   = bold
            run.italic = italic
            run.font.name = "Arial"
            run.font.size = Pt(size)
            if color: run.font.color.rgb = color
            return p

        def section_heading(doc, text, bg_hex="1A7A6E", text_color=WHITE_RGB, size=9.5):
            tbl = doc.add_table(rows=1, cols=1)
            tbl.style = "Table Grid"
            tbl.autofit = False
            from docx.oxml import OxmlElement as OE
            tW = tbl._tbl.find(qn("w:tblPr"))
            if tW is None:
                tW = OE("w:tblPr"); tbl._tbl.insert(0, tW)
            tw = OE("w:tblW"); tw.set(qn("w:w"), "0"); tw.set(qn("w:type"), "auto"); tW.append(tw)
            cell = tbl.rows[0].cells[0]
            hex_fill(cell, bg_hex)
            no_border(cell)
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            mar = OxmlElement("w:tcMar")
            for side in ["top","left","bottom","right"]:
                m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), "100"); m.set(qn("w:type"), "dxa"); mar.append(m)
            tcPr.append(mar)
            para(cell, text, bold=True, size=size, color=text_color, space_before=0, space_after=0)
            doc.add_paragraph().paragraph_format.space_after = Pt(1)
            return tbl

        def bullet_lines(doc_or_cell, text, size=8.5, color=None, indent_left=360, hanging=180):
            """Render newline-separated • bullets as proper paragraph bullets."""
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for line in lines:
                line_text = line.lstrip("•").strip()
                if not line_text: continue
                if hasattr(doc_or_cell, "_tc"):
                    p = doc_or_cell.add_paragraph()
                else:
                    p = doc_or_cell.add_paragraph()
                p.paragraph_format.space_before = Pt(1.5)
                p.paragraph_format.space_after  = Pt(1.5)
                p.paragraph_format.left_indent  = Pt(indent_left / 20)
                p.paragraph_format.first_line_indent = Pt(-hanging / 20)
                run = p.add_run(f"•  {line_text}")
                run.font.name = "Arial"
                run.font.size = Pt(size)
                if color: run.font.color.rgb = color

        # ── HEADER TABLE ──────────────────────────────────────
        hdr = doc.add_table(rows=1, cols=1)
        hdr.autofit = True
        hc = hdr.rows[0].cells[0]
        hex_fill(hc, "1A2E44")
        no_border(hc)
        tc = hc._tc; tcPr = tc.get_or_add_tcPr()
        mar = OxmlElement("w:tcMar")
        for side, val in [("top","150"),("left","200"),("bottom","150"),("right","200")]:
            m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), val); m.set(qn("w:type"), "dxa"); mar.append(m)
        tcPr.append(mar)
        p_title = hc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(0); p_title.paragraph_format.space_after = Pt(4)
        rt = p_title.add_run("TAC MEETING — PREPARATION BRIEF")
        rt.bold = True; rt.font.name = "Arial"; rt.font.size = Pt(14); rt.font.color.rgb = WHITE_RGB

        subtitle = s["name"]
        if s.get("home_school"): subtitle += f"  |  {s['home_school']}"
        if s.get("meeting_date"): subtitle += f"  |  {s['meeting_date']}"
        p_sub = hc.add_paragraph()
        p_sub.paragraph_format.space_before = Pt(0); p_sub.paragraph_format.space_after = Pt(0)
        rs = p_sub.add_run(subtitle)
        rs.font.name = "Arial"; rs.font.size = Pt(8.5); rs.font.color.rgb = CREAM_RGB

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ── STUDENT SNAPSHOT ─────────────────────────────────
        section_heading(doc, "STUDENT SNAPSHOT", "1A7A6E")
        snap = doc.add_table(rows=3, cols=2)
        snap.autofit = True
        snap_data = [
            [f"Full name: {s['name']}", f"Home school: {s.get('home_school','')}"],
            [f"Date of birth: {s.get('dob','')}  |  Age: {s.get('age','')}  |  EDSAS: {s.get('edsas','')}", f"CLC Program: {s.get('program','')}  |  Brief date: {s.get('plan_date','')}"],
            [f"Meeting: {s.get('meeting_date','')}  |  {s.get('meeting_location','')}", f"Attendees: {s.get('attendees','').replace(chr(10),', ')}" if s.get('attendees') else ""],
        ]
        for ri2, row_data in enumerate(snap_data):
            for ci2, text in enumerate(row_data):
                cell = snap.rows[ri2].cells[ci2]
                no_border(cell)
                hex_fill(cell, "F2F6F6")
                tc2 = cell._tc; tcPr2 = tc2.get_or_add_tcPr()
                mar2 = OxmlElement("w:tcMar")
                for side, val in [("top","50"),("left","120"),("bottom","50"),("right","120")]:
                    m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), val); m.set(qn("w:type"), "dxa"); mar2.append(m)
                tcPr2.append(mar2)
                if text:
                    p_snap = cell.add_paragraph()
                    p_snap.paragraph_format.space_before = Pt(1); p_snap.paragraph_format.space_after = Pt(1)
                    # Bold the label
                    parts = text.split(": ", 1)
                    if len(parts) == 2:
                        rb = p_snap.add_run(parts[0] + ": ")
                        rb.bold = True; rb.font.name = "Arial"; rb.font.size = Pt(8.5); rb.font.color.rgb = BODY_RGB
                        rv = p_snap.add_run(parts[1])
                        rv.font.name = "Arial"; rv.font.size = Pt(8.5); rv.font.color.rgb = BODY_RGB
                    else:
                        rn = p_snap.add_run(text)
                        rn.font.name = "Arial"; rn.font.size = Pt(8.5); rn.font.color.rgb = BODY_RGB
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

        # ── PURPOSE ──────────────────────────────────────────
        section_heading(doc, "Purpose of This Meeting", "2E4057")
        p_pur = doc.add_paragraph()
        p_pur.paragraph_format.space_before = Pt(2)
        p_pur.paragraph_format.space_after  = Pt(6)
        rp = p_pur.add_run(b.get("purpose",""))
        rp.font.name = "Arial"; rp.font.size = Pt(8.5); rp.font.color.rgb = BODY_RGB
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

        # ── AGENDA ───────────────────────────────────────────
        section_heading(doc, "Proposed Agenda", "2E4057")
        for ag_idx, item in enumerate(b.get("agenda",[])):
            if not item.get("title"): continue
            # Numbered heading
            p_h = doc.add_paragraph()
            p_h.paragraph_format.space_before = Pt(4)
            p_h.paragraph_format.space_after  = Pt(2)
            rh = p_h.add_run(f"{ag_idx+1}.  {item['title']}")
            rh.bold = True; rh.font.name = "Arial"; rh.font.size = Pt(9); rh.font.color.rgb = NAVY_RGB
            # Content bullets
            content = item.get("content","")
            if content:
                bullet_lines(doc, content, size=8.5, color=BODY_RGB)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

        # ── BSE QUESTIONS TABLE ───────────────────────────────
        section_heading(doc, "Questions for the BSE / Support Specialist", "1A7A6E")
        questions = [q for q in b.get("bse_questions",[]) if q.get("q")]
        if questions:
            qtbl = doc.add_table(rows=len(questions)+1, cols=2)
            qtbl.autofit = True
            # Header row
            for ci_h, htext in enumerate(["#","Question and context"]):
                hc2 = qtbl.rows[0].cells[ci_h]
                hex_fill(hc2, "2E4057")
                no_border(hc2)
                ph = hc2.add_paragraph(); ph.paragraph_format.space_before = Pt(2); ph.paragraph_format.space_after = Pt(2)
                rh2 = ph.add_run(htext); rh2.bold = True; rh2.font.name = "Arial"; rh2.font.size = Pt(8.5); rh2.font.color.rgb = WHITE_RGB
            # Set column widths
            for row in qtbl.rows:
                for ci3, cell in enumerate(row.cells):
                    cell.width = Cm(1.2 if ci3 == 0 else 23.0)
                    no_border(cell)
                    hex_fill(cell, "F8FDFB" if row == qtbl.rows[0] else "FFFFFF")
                    tc3 = cell._tc; tcPr3 = tc3.get_or_add_tcPr()
                    mar3 = OxmlElement("w:tcMar")
                    for side, val in [("top","50"),("left","120"),("bottom","50"),("right","120")]:
                        m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), val); m.set(qn("w:type"), "dxa"); mar3.append(m)
                    tcPr3.append(mar3)
            for qi2, qitem in enumerate(questions):
                r = qtbl.rows[qi2+1]
                # Number cell
                pn = r.cells[0].add_paragraph()
                pn.paragraph_format.space_before = Pt(2); pn.paragraph_format.space_after = Pt(2)
                rn2 = pn.add_run(str(qi2+1)); rn2.bold = True; rn2.font.name = "Arial"; rn2.font.size = Pt(8.5); rn2.font.color.rgb = TEAL_RGB
                # Question + context cell
                pq = r.cells[1].add_paragraph()
                pq.paragraph_format.space_before = Pt(2); pq.paragraph_format.space_after = Pt(2)
                rq = pq.add_run(qitem.get("q","")); rq.bold = True; rq.font.name = "Arial"; rq.font.size = Pt(8.5); rq.font.color.rgb = NAVY_RGB
                if qitem.get("context"):
                    pc = r.cells[1].add_paragraph()
                    pc.paragraph_format.space_before = Pt(1); pc.paragraph_format.space_after = Pt(2)
                    rc = pc.add_run(qitem["context"]); rc.font.name = "Arial"; rc.font.size = Pt(8); rc.font.color.rgb = BODY_RGB; rc.italic = True
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

        # ── CLC POSITION ─────────────────────────────────────
        section_heading(doc, "CLC Position — Key Messages for TAC", "2E4057")
        pos_sections = [
            ("What the evidence from CLC is telling us", b.get("clc_evidence",""), "1A7A6E"),
            ("What CLC needs the TAC to understand", b.get("clc_needs_tac",""), "1A2E44"),
            ("Immediate risks requiring TAC agreement", b.get("immediate_risks",""), "B91C1C"),
        ]
        for pos_title, pos_content, pos_color in pos_sections:
            ptbl = doc.add_table(rows=1, cols=1)
            ptbl.autofit = True
            pc2 = ptbl.rows[0].cells[0]
            no_border(pc2); hex_fill(pc2, "F8FDFB")
            cell_border(pc2, pos_color)
            tc4 = pc2._tc; tcPr4 = tc4.get_or_add_tcPr()
            mar4 = OxmlElement("w:tcMar")
            for side, val in [("top","80"),("left","150"),("bottom","80"),("right","150")]:
                m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), val); m.set(qn("w:type"), "dxa"); mar4.append(m)
            tcPr4.append(mar4)
            ph2 = pc2.add_paragraph()
            ph2.paragraph_format.space_before = Pt(0); ph2.paragraph_format.space_after = Pt(3)
            rh3 = ph2.add_run(pos_title); rh3.bold = True; rh3.font.name = "Arial"; rh3.font.size = Pt(8.5)
            rh3.font.color.rgb = RGBColor(int(pos_color[:2],16), int(pos_color[2:4],16), int(pos_color[4:],16))
            if pos_content:
                lines = [l.strip().lstrip("•").strip() for l in pos_content.splitlines() if l.strip()]
                for line in lines:
                    if not line: continue
                    pb = pc2.add_paragraph()
                    pb.paragraph_format.space_before = Pt(1); pb.paragraph_format.space_after = Pt(1)
                    pb.paragraph_format.left_indent = Pt(18); pb.paragraph_format.first_line_indent = Pt(-9)
                    rb2 = pb.add_run(f"•  {line}"); rb2.font.name = "Arial"; rb2.font.size = Pt(8.5); rb2.font.color.rgb = BODY_RGB
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

        # ── ACTIONS TABLE ─────────────────────────────────────
        section_heading(doc, "Actions — To Be Confirmed at TAC", "2E4057")
        actions = [a for a in b.get("actions",[]) if a.get("action")]
        if actions:
            atbl = doc.add_table(rows=len(actions)+1, cols=3)
            atbl.autofit = True
            # Header
            for ci5, htext in enumerate(["Owner","Action","Priority"]):
                hcell = atbl.rows[0].cells[ci5]
                hex_fill(hcell, "1A2E44"); no_border(hcell)
                ph3 = hcell.add_paragraph()
                ph3.paragraph_format.space_before = Pt(2); ph3.paragraph_format.space_after = Pt(2)
                rh4 = ph3.add_run(htext); rh4.bold = True; rh4.font.name = "Arial"; rh4.font.size = Pt(8.5); rh4.font.color.rgb = WHITE_RGB
            # Rows
            for ai5, action in enumerate(actions):
                row = atbl.rows[ai5+1]
                row_data = [action.get("owner",""), action.get("action",""), action.get("priority","")]
                is_urgent = action.get("priority","") == "URGENT"
                for ci6, text in enumerate(row_data):
                    cell = row.cells[ci6]
                    no_border(cell)
                    hex_fill(cell, "FFF3CD" if is_urgent else "FFFFFF")
                    tc5 = cell._tc; tcPr5 = tc5.get_or_add_tcPr()
                    mar5 = OxmlElement("w:tcMar")
                    for side, val in [("top","50"),("left","120"),("bottom","50"),("right","120")]:
                        m = OxmlElement(f"w:{side}"); m.set(qn("w:w"), val); m.set(qn("w:type"), "dxa"); mar5.append(m)
                    tcPr5.append(mar5)
                    pa = cell.add_paragraph()
                    pa.paragraph_format.space_before = Pt(2); pa.paragraph_format.space_after = Pt(2)
                    ra = pa.add_run(text); ra.font.name = "Arial"; ra.font.size = Pt(8.5); ra.font.color.rgb = BODY_RGB
                    if ci6 == 2 and is_urgent:
                        ra.bold = True; ra.font.color.rgb = RGBColor(0x92, 0x40, 0x0e)

        # ── FOOTER ───────────────────────────────────────────
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        footer_txt = f"Cowandilla Learning Centre  |  LBU {s.get('program','')} Program  |  TAC Preparation Brief  |  {s.get('meeting_date','')}  |  Prepared by CLC program staff"
        p_foot = doc.add_paragraph()
        p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rf = p_foot.add_run(footer_txt)
        rf.font.name = "Arial"; rf.font.size = Pt(7); rf.font.color.rgb = RGBColor(0x9a, 0xb0, 0x9a); rf.italic = True

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    # Generate
    with st.spinner("Generating your TAC Preparation Brief…"):
        try:
            docx_buf = build_docx()
            st.session_state["_tac_docx"] = docx_buf.getvalue()
        except Exception as e:
            st.error(f"Document generation error: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.stop()

    st.markdown("""
    <div class="hero" style="text-align:center;">
      <div style="font-size:2rem;margin-bottom:.5rem;">✅</div>
      <div class="hero-title">TAC Preparation Brief Ready</div>
      <div class="hero-sub">Your document is ready to download. Open in Word, review, and distribute to TAC members.</div>
    </div>
    """, unsafe_allow_html=True)

    # Summary card
    st.markdown('<div class="card"><div class="card-header teal"><h3>📋 Brief Summary</h3></div><div class="card-body">', unsafe_allow_html=True)
    ssum1, ssum2, ssum3, ssum4 = st.columns(4)
    with ssum1:
        st.metric("Student", s.get("name","—").split()[0] if s.get("name") else "—")
    with ssum2:
        st.metric("Agenda Items", len([a for a in b.get("agenda",[]) if a.get("title")]))
    with ssum3:
        st.metric("BSE Questions", len([q for q in b.get("bse_questions",[]) if q.get("q")]))
    with ssum4:
        st.metric("Actions", len([a for a in b.get("actions",[]) if a.get("action")]))
    st.markdown('</div></div>', unsafe_allow_html=True)

    # Download
    fname = f"TAC_Brief_{s.get('name','').replace(' ','_')}_{date.today().strftime('%Y-%m-%d')}.docx"
    st.download_button(
        "📥 Download TAC Preparation Brief (.docx)",
        data=st.session_state["_tac_docx"],
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    with d1:
        if st.button("← Back to Review", use_container_width=True):
            st.session_state.tac_step = 4; st.rerun()
    with d2:
        if st.button("🔄 Start a New Brief", use_container_width=True):
            for k in ["tac_step","tac_mode","student","brief","transcript_text"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
