"""
CLC Safety & Risk Management Plan Builder
==========================================
Revised structure (aligned to CLC S&R Plan format):

- BOC column: observable behaviour + characterised by + function  (NO triggers — triggers → BSP)
- Proactive strategies: environmental, supervision, structural only
- Reactive procedures: tiered (early signs / on grounds / left grounds / returned / post-incident)
- Contextual risks section captured separately at start
- AI mode: upload existing docs → extract & contextualise
- Manual mode: step-by-step builder from scratch
"""

import streamlit as st
from groq import Groq
import json, os, io
from datetime import date
from copy import deepcopy

from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Brand colours ──────────────────────────────────────────────────────────────
TEAL        = "#1A7A6E"
TEAL_LIGHT  = "#D6EEEB"
AMBER       = "#D97706"
AMBER_LIGHT = "#FEF3C7"
GREY_DARK   = "#2E4057"
GREY_LIGHT  = "#F2F6F6"
RED_BG      = "#FCDCDC"
RED_TXT     = "#7A1A1A"
ORG_BG      = "#FEF0CC"
ORG_TXT     = "#7A4000"

# ── Risk matrix ────────────────────────────────────────────────────────────────
LIKELIHOOD_OPTIONS  = ["A – Rare","B – Unlikely","C – Likely sometimes",
                       "D – Likely/frequently","E – Almost certain"]
CONSEQUENCE_OPTIONS = ["1 – Insignificant","2 – Minor","3 – Moderate",
                       "4 – Major","5 – Catastrophic"]
RISK_MATRIX = {
    ("E","5"):"EXTREME",("E","4"):"EXTREME",("E","3"):"EXTREME",("E","2"):"HIGH",  ("E","1"):"HIGH",
    ("D","5"):"EXTREME",("D","4"):"EXTREME",("D","3"):"HIGH",   ("D","2"):"HIGH",  ("D","1"):"MODERATE",
    ("C","5"):"EXTREME",("C","4"):"EXTREME",("C","3"):"HIGH",   ("C","2"):"MODERATE",("C","1"):"LOW",
    ("B","5"):"HIGH",   ("B","4"):"HIGH",   ("B","3"):"MODERATE",("B","2"):"LOW",  ("B","1"):"LOW",
    ("A","5"):"HIGH",   ("A","4"):"HIGH",   ("A","3"):"MODERATE",("A","2"):"LOW",  ("A","1"):"LOW",
}
RISK_COLOURS = {"EXTREME":"#C0392B","HIGH":"#E67E22","MODERATE":"#d4a017","LOW":"#27AE60"}

BLANK_RISK = {
    "issue_title":        "",   # short label for sidebar
    "boc_description":    "",   # narrative description of the behaviour
    "characterised_by":   "",   # bullet-style: what does it look like?
    "function":           "",   # function of the behaviour
    "likelihood":         "D – Likely/frequently",
    "consequence":        "4 – Major",
    # Proactive strategies (environmental/supervisory ONLY — no triggers/relational)
    "env_supervision":    "",   # environment & supervision strategies
    "structural":         "",   # physical/structural strategies (gate, keys, radio, etc.)
    "contextual_note":    "",   # medication/other current context affecting strategies
    # Reactive procedures — tiered
    "react_early":        "",   # early signs of dysregulation
    "react_on_grounds":   "",   # has left program space but still on CLC grounds
    "react_left_grounds": "",   # has left CLC grounds
    "react_returned":     "",   # when student is returned
    "react_post":         "",   # post-incident actions
    "clc_notes":          "",   # additional CLC-specific notes
}

def compute_risk_level(likelihood: str, consequence: str) -> str:
    l_key = likelihood[0] if likelihood else "D"
    c_key = consequence[0] if consequence else "4"
    return RISK_MATRIX.get((l_key, c_key), "HIGH")

def risk_badge(level: str) -> str:
    colour = RISK_COLOURS.get(level, "#888")
    return f'<span style="background:{colour};color:white;padding:2px 10px;border-radius:12px;font-size:0.82em;font-weight:700">{level}</span>'

def init_state():
    defaults = {
        "step": 1,
        "current_risk": 0,
        "student": {
            "name": "", "dob": "", "edsas": "", "program": "JP",
            "home_school": "", "key_staff": "", "plan_date": str(date.today()),
            "review_date": "", "sapol_ref": "", "status_note": "",
        },
        "contextual_risks": "",   # CLC-specific contextual risk paragraph
        "risks": [],
        "priority_actions": "",
        "review_date_final": "",
        "source_mode": None,      # "upload" or "manual"
        "upload_extracted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Safety & Risk Plan Builder", page_icon="🛡️", layout="wide")
init_state()

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

  .srp-header {{
    background: linear-gradient(135deg, {TEAL} 0%, #0F4556 100%);
    color: white; padding: 1.4rem 1.8rem; border-radius: 10px;
    margin-bottom: 1.4rem;
  }}
  .srp-header h2 {{ margin: 0 0 .15rem; font-size: 1.35rem; font-weight: 700; }}
  .srp-header p  {{ margin: 0; opacity: .85; font-size: .9rem; }}

  .step-bar {{
    display: flex; gap: 4px; margin-bottom: 1.4rem;
    background: {GREY_LIGHT}; border-radius: 8px; padding: 6px;
  }}
  .step-pill {{
    flex: 1; text-align: center; padding: 6px 4px; border-radius: 6px;
    font-size: .78rem; font-weight: 600; color: #888;
  }}
  .step-pill.active  {{ background: {TEAL}; color: white; }}
  .step-pill.done    {{ background: {TEAL_LIGHT}; color: {TEAL}; }}

  .card {{
    background: white; border-radius: 10px; padding: 1.2rem 1.4rem;
    border: 1px solid #e2e8f0; margin-bottom: 1rem;
  }}
  .card-amber {{
    background: {AMBER_LIGHT}; border-radius: 10px; padding: 1rem 1.2rem;
    border: 1px solid #fbbf24; margin-bottom: 1rem;
  }}
  .card-teal {{
    background: {TEAL_LIGHT}; border-radius: 10px; padding: 1rem 1.2rem;
    border: 1px solid {TEAL}; margin-bottom: 1rem;
  }}
  .section-heading {{
    color: {TEAL}; font-weight: 700; font-size: .95rem;
    text-transform: uppercase; letter-spacing: .05em;
    border-bottom: 2px solid {TEAL_LIGHT}; padding-bottom: 4px; margin-bottom: .8rem;
  }}
  .sub-heading {{
    color: {GREY_DARK}; font-weight: 600; font-size: .88rem;
    margin: 1rem 0 .3rem;
  }}
  .field-note {{
    font-size: .78rem; color: #666; font-style: italic; margin-top: -0.4rem; margin-bottom: 0.5rem;
  }}
  .risk-chip {{
    display: inline-block; border-radius: 6px; padding: 2px 10px;
    font-size: .78rem; font-weight: 700; color: white; margin-left: 6px;
  }}
  .tier-label {{
    font-size: .78rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: {TEAL}; margin: .9rem 0 .2rem;
  }}
  .tier-divider {{
    border: none; border-top: 1px solid {TEAL_LIGHT}; margin: .8rem 0;
  }}
  .note-box {{
    background: #fffbeb; border-left: 4px solid {AMBER}; padding: .8rem 1rem;
    border-radius: 0 8px 8px 0; margin: .6rem 0; font-size: .86rem;
  }}
  .stTextArea textarea {{ font-size: .85rem !important; }}
  .stTextInput input  {{ font-size: .88rem !important; }}
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="srp-header">
  <h2>🛡️ Safety &amp; Risk Management Plan Builder</h2>
  <p>Cowandilla Learning Centre &nbsp;|&nbsp; Learning &amp; Behaviour Unit</p>
</div>
""", unsafe_allow_html=True)

# ── Step bar ───────────────────────────────────────────────────────────────────
STEPS = ["1 · Student", "2 · Source", "3 · Context", "4 · Risks", "5 · Review", "6 · Generate"]
def step_bar(current):
    pills = ""
    for i, label in enumerate(STEPS, 1):
        cls = "active" if i == current else ("done" if i < current else "step-pill")
        pills += f'<div class="step-pill {cls}">{label}</div>'
    st.markdown(f'<div class="step-bar">{pills}</div>', unsafe_allow_html=True)

step_bar(st.session_state.step)

# ══════════════════════════════════════════════════════════════════════════════
# GROQ CLIENT
# ══════════════════════════════════════════════════════════════════════════════
def get_groq():
    key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
    return Groq(api_key=key) if key else None

def groq_chat(prompt: str, system: str = "", max_tokens: int = 2000) -> str:
    client = get_groq()
    if not client:
        return "⚠️ Groq API key not configured."
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile", messages=messages, max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI error: {e}"

# ── Extract text from uploaded docx ───────────────────────────────────────────
def extract_docx_text(uploaded_file) -> str:
    try:
        doc = DocxDocument(io.BytesIO(uploaded_file.read()))
        lines = []
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    lines.append(row_text)
        return "\n".join(lines)
    except Exception as e:
        return f"[Error reading document: {e}]"

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 · STUDENT DETAILS
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == 1:
    st.markdown('<div class="section-heading">Student Details</div>', unsafe_allow_html=True)
    s = st.session_state.student

    c1, c2 = st.columns(2)
    with c1:
        s["name"]        = st.text_input("Full Name *", s["name"])
        s["dob"]         = st.text_input("Date of Birth (DD/MM/YYYY)", s["dob"])
        s["edsas"]       = st.text_input("EDSAS ID", s["edsas"])
        s["program"]     = st.selectbox("Program", ["JP – CLC LBU","MP – CLC LBU","SP – CLC LBU"],
                                        index=["JP – CLC LBU","MP – CLC LBU","SP – CLC LBU"].index(s["program"])
                                        if s["program"] in ["JP – CLC LBU","MP – CLC LBU","SP – CLC LBU"] else 0)
    with c2:
        s["home_school"]  = st.text_input("Home School", s["home_school"])
        s["key_staff"]    = st.text_input("Key CLC Staff (comma separated)", s["key_staff"])
        s["plan_date"]    = st.text_input("Plan Date", s["plan_date"])
        s["review_date"]  = st.text_input("Review Date", s["review_date"])

    s["sapol_ref"]    = st.text_input("SAPOL Reference (if applicable)", s["sapol_ref"])
    s["status_note"]  = st.text_area("Status / Alert Note (e.g. medication transition, critical incident)", s["status_note"], height=80)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Continue →", type="primary", use_container_width=True):
        if not s["name"].strip():
            st.error("Student name is required.")
        else:
            st.session_state.step = 2
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 · SOURCE — UPLOAD OR BUILD FROM SCRATCH
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 2:
    st.markdown('<div class="section-heading">Source Documents</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="note-box">
    Choose how to build this plan. You can upload existing documents and let AI extract
    and contextualise them for CLC, or build entirely from scratch using the step-by-step builder.
    </div>
    """, unsafe_allow_html=True)

    tab_upload, tab_scratch = st.tabs(["📄 Upload existing documents", "✏️ Build from scratch"])

    with tab_upload:
        st.markdown('<div class="sub-heading">Upload any relevant documents</div>', unsafe_allow_html=True)
        st.markdown('<p class="field-note">You can upload multiple files — school safety plan, BAP, incident reports, psychologist reports. The AI will read all of them and generate CLC-contextualised risk rows.</p>', unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Upload documents (.docx, .pdf, .txt)",
            type=["docx","txt"],
            accept_multiple_files=True,
            key="source_docs"
        )

        if uploaded_files:
            st.success(f"{len(uploaded_files)} file(s) uploaded.")

        extra_context = st.text_area(
            "Anything else the AI should know? (verbal briefing, recent incident summary, etc.)",
            height=100,
            key="extra_context_upload"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✨ Extract & generate risks from documents", type="primary", disabled=not uploaded_files):
            with st.spinner("Reading documents and generating CLC-contextualised risks…"):
                all_text = ""
                for f in uploaded_files:
                    if f.name.endswith(".docx"):
                        all_text += f"\n\n=== {f.name} ===\n" + extract_docx_text(f)
                    else:
                        all_text += f"\n\n=== {f.name} ===\n" + f.read().decode("utf-8", errors="ignore")

                student = st.session_state.student
                system = """You are an expert in behaviour support and safety planning for students with complex needs in a specialised South Australian school program. You understand DfE Safety & Risk Plan requirements, trauma-informed practice, and the Berry Street Education Model."""

                prompt = f"""
A student named {student['name']} (DOB: {student['dob']}, Program: {student['program']}) at Cowandilla Learning Centre LBU has the following background documents:

{all_text}

Additional context: {extra_context}

CLC is a small group setting (up to 10 students) with an adjacent carpark, climbable external fence, and nearby busy roads. Staff use walkie talkies and maintain line-of-sight supervision. Plans follow DfE Safety & Risk Plan format.

IMPORTANT STRUCTURAL RULES:
- The "Behaviour of Concern" (BOC) column contains ONLY: the observable behaviour, what it looks like (characterised by), and its function. NO triggers — triggers belong in the Behaviour Support Plan, not the Safety & Risk Plan.
- Proactive strategies contain ONLY environmental, supervisory, and structural strategies (e.g. gate checks, staff positioning, walkie talkies, vehicle keys, visual schedules). NOT relational/skill-building strategies — those belong in the BSP.
- Reactive procedures use a tiered structure: early signs / on grounds / left grounds / returned to CLC / post-incident.

Extract or generate 2–5 risks. Return ONLY a JSON array. Each item must have these exact keys:
issue_title, boc_description, characterised_by, function,
likelihood (use "D – Likely/frequently" or similar), consequence (use "4 – Major" or similar),
env_supervision, structural, contextual_note,
react_early, react_on_grounds, react_left_grounds, react_returned, react_post,
contextual_risks_paragraph (one paragraph of CLC-specific contextual factors to include at the top of the plan)

Return ONLY valid JSON, no markdown, no explanation.
"""
                raw = groq_chat(prompt, system=system, max_tokens=4000)
                try:
                    raw_clean = raw.strip()
                    if raw_clean.startswith("```"):
                        raw_clean = "\n".join(raw_clean.split("\n")[1:])
                    if raw_clean.endswith("```"):
                        raw_clean = raw_clean.rsplit("```", 1)[0]
                    data = json.loads(raw_clean)
                    if isinstance(data, list) and data:
                        ctx = data[0].pop("contextual_risks_paragraph", "")
                        if ctx:
                            st.session_state.contextual_risks = ctx
                        st.session_state.risks = []
                        for d in data:
                            r = deepcopy(BLANK_RISK)
                            for k in r:
                                if k in d:
                                    r[k] = d[k]
                            st.session_state.risks.append(r)
                        st.session_state.source_mode = "upload"
                        st.session_state.upload_extracted = True
                        st.session_state.step = 3
                        st.rerun()
                    else:
                        st.error("AI returned unexpected format. Try again or use manual mode.")
                except Exception as e:
                    st.error(f"Could not parse AI response: {e}")
                    st.code(raw[:1000])

    with tab_scratch:
        st.markdown("""
        <div class="card-teal">
        Build the plan step by step without uploading documents.
        You can still use AI to generate strategies once you've described each risk.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Build from scratch →", type="primary", use_container_width=True):
            if not st.session_state.risks:
                st.session_state.risks = [deepcopy(BLANK_RISK)]
            st.session_state.source_mode = "manual"
            st.session_state.step = 3
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back to student details"):
        st.session_state.step = 1
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 · CONTEXTUAL RISKS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 3:
    st.markdown('<div class="section-heading">CLC Contextual Risks</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="note-box">
    <strong>What goes here:</strong> CLC-specific environmental and contextual factors that create risks
    which cannot be fully addressed through standard school-based planning. This section appears at the top
    of the plan before the risk table. Do not include triggers or behaviour descriptions here.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="field-note">Examples: physical environment (carpark, fence, roads), group composition, medication status, pending assessments, placement type.</p>', unsafe_allow_html=True)

    st.session_state.contextual_risks = st.text_area(
        "Current contextual risks — CLC setting",
        st.session_state.contextual_risks,
        height=220,
        help="Write as dot points or prose. This will appear verbatim in the plan under 'Current Contextual Risks — CLC Setting'."
    )

    if st.session_state.source_mode == "manual" or not st.session_state.contextual_risks.strip():
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("✨ Generate contextual risks with AI"):
            ai_context_prompt = st.text_area(
                "Describe the CLC situation in a few sentences (setting, environment, student profile, any current factors):",
                height=100,
                key="ctx_ai_prompt"
            )
            if st.button("Generate contextual risks paragraph", key="gen_ctx"):
                with st.spinner("Generating…"):
                    student = st.session_state.student
                    result = groq_chat(
                        f"""Write a concise dot-point paragraph of CLC-specific contextual risks for a Safety & Risk Plan.
Student: {student['name']}, {student['program']} program. Context: {ai_context_prompt}
CLC factors to consider: small group (up to 10), carpark adjacent to playground via climbable fence, busy roads nearby (Jenkins/Marion/Sir Donald Bradman Drive, proximity to South Road), staff use walkie talkies and maintain line-of-sight.
Write 4–6 dot points. Do NOT include triggers, BOC descriptions, or strategies — contextual factors only.
Format as plain text dot points starting with -""",
                        system="You are an expert in DfE safety planning for students with complex needs."
                    )
                    st.session_state.contextual_risks = result
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with c2:
        if st.button("Continue to Risk Builder →", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 · RISK BUILDER
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 4:
    student = st.session_state.student
    risks   = st.session_state.risks

    left, right = st.columns([1, 2], gap="large")

    with left:
        st.markdown('<div class="section-heading">Risk Areas</div>', unsafe_allow_html=True)

        for i, r in enumerate(risks):
            level  = compute_risk_level(r["likelihood"], r["consequence"])
            colour = RISK_COLOURS.get(level, "#888")
            label  = r["issue_title"] or f"Risk {i+1} (unnamed)"
            prefix = "▶ " if i == st.session_state.current_risk else ""
            if st.button(f"{prefix}{label}", key=f"sel_{i}", use_container_width=True):
                st.session_state.current_risk = i
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("＋ Add risk", use_container_width=True):
            risks.append(deepcopy(BLANK_RISK))
            st.session_state.current_risk = len(risks) - 1
            st.rerun()

        if len(risks) > 1:
            if st.button("🗑 Remove current risk", use_container_width=True):
                risks.pop(st.session_state.current_risk)
                st.session_state.current_risk = max(0, st.session_state.current_risk - 1)
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("→ Continue to Review", type="primary", use_container_width=True):
            if all(r["issue_title"].strip() == "" for r in risks):
                st.error("Complete at least one risk before continuing.")
            else:
                st.session_state.step = 5
                st.rerun()

        if st.button("← Back", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

    with right:
        if not risks:
            st.markdown('<div class="card-teal">Click <em>＋ Add risk</em> on the left to begin.</div>', unsafe_allow_html=True)
        else:
            idx = min(st.session_state.current_risk, len(risks)-1)
            r   = risks[idx]
            level = compute_risk_level(r["likelihood"], r["consequence"])

            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem">
              <div style="font-size:1.05rem;font-weight:700;color:{GREY_DARK}">Risk {idx+1}</div>
              {risk_badge(level)}
            </div>
            """, unsafe_allow_html=True)

            # ── AI note for uploaded plans ─────────────────────────────────
            if st.session_state.upload_extracted and st.session_state.source_mode == "upload":
                st.markdown(f"""
                <div class="card-amber">
                <strong>⚡ AI-extracted risk</strong><br>
                Review each field carefully. The AI has generated CLC-contextualised content
                but you should verify and edit based on your knowledge of this student.
                </div>
                """, unsafe_allow_html=True)

            # ── BOC section ────────────────────────────────────────────────
            st.markdown('<div class="section-heading">Behaviour of Concern (BOC)</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="note-box">
            The BOC column contains the <strong>observable behaviour only</strong> — what it looks like,
            how it is characterised, and its function. <strong>Do not include triggers here</strong> —
            triggers belong in the Behaviour Support Plan.
            </div>
            """, unsafe_allow_html=True)

            r["issue_title"] = st.text_input(
                "Risk title (short label for sidebar)",
                r["issue_title"], key=f"title_{idx}"
            )
            r["boc_description"] = st.text_area(
                "Behaviour description",
                r["boc_description"], height=100, key=f"boc_{idx}",
                help="Describe the behaviour as it appears — what staff observe. No triggers."
            )
            r["characterised_by"] = st.text_area(
                "Characterised by (dot points — what does it look like specifically?)",
                r["characterised_by"], height=120, key=f"char_{idx}",
                help="e.g. Running at speed, covering significant distances; climbing fence within seconds; non-responsive to verbal de-escalation while in flight"
            )
            st.markdown('<p class="field-note">Use dot points. Be observable and specific — speed, distance, duration, what staff see.</p>', unsafe_allow_html=True)

            r["function"] = st.text_input(
                "Function of the behaviour",
                r["function"], key=f"func_{idx}",
                help="e.g. Avoidance — peer and adult; Escape from perceived social threat"
            )

            # ── Risk rating ────────────────────────────────────────────────
            st.markdown('<div class="section-heading">Risk Rating</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                r["likelihood"] = st.selectbox("Likelihood", LIKELIHOOD_OPTIONS,
                    index=LIKELIHOOD_OPTIONS.index(r["likelihood"]) if r["likelihood"] in LIKELIHOOD_OPTIONS else 3,
                    key=f"lik_{idx}")
            with c2:
                r["consequence"] = st.selectbox("Consequence", CONSEQUENCE_OPTIONS,
                    index=CONSEQUENCE_OPTIONS.index(r["consequence"]) if r["consequence"] in CONSEQUENCE_OPTIONS else 3,
                    key=f"con_{idx}")
            level = compute_risk_level(r["likelihood"], r["consequence"])
            st.markdown(f'**Risk level:** {risk_badge(level)}', unsafe_allow_html=True)

            # ── Proactive strategies ───────────────────────────────────────
            st.markdown('<div class="section-heading">Proactive Strategies</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="note-box">
            Proactive strategies in a Safety &amp; Risk Plan are <strong>environmental, supervisory, and
            structural only</strong>. Relational strategies, skill-building, and social/emotional programs
            belong in the Behaviour Support Plan — not here.
            </div>
            """, unsafe_allow_html=True)

            r["env_supervision"] = st.text_area(
                "Environment & supervision strategies",
                r["env_supervision"], height=130, key=f"env_{idx}",
                help="e.g. Gate latched at all times; staff maintain line-of-sight; minimum 1:1 supervision during unstructured time"
            )
            st.markdown('<p class="field-note">Gate/fence security, staff positioning, line-of-sight requirements, zone/time restrictions.</p>', unsafe_allow_html=True)

            r["structural"] = st.text_area(
                "Structural & operational strategies",
                r["structural"], height=110, key=f"struct_{idx}",
                help="e.g. All staff carry walkie talkies; vehicle keys in leaders office; school mobile for SAPOL; visual schedule posted"
            )
            st.markdown('<p class="field-note">Walkie talkies, vehicle key location, SAPOL contact readiness, visual schedules, peer grouping structure.</p>', unsafe_allow_html=True)

            r["contextual_note"] = st.text_area(
                "Current contextual factor affecting strategies (optional)",
                r["contextual_note"], height=80, key=f"ctx_{idx}",
                help="e.g. During medication wean period: reduce cognitive load, consider reduced hours, increase adult proximity"
            )
            st.markdown('<p class="field-note">Medication transition, pending assessments, current exclusion period, etc.</p>', unsafe_allow_html=True)

            # ── Reactive procedures ────────────────────────────────────────
            st.markdown('<div class="section-heading">Reactive Procedures (Tiered)</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="note-box">
            Use a tiered structure matching escalation levels. Staff should be able to locate
            the right tier quickly in a crisis — keep each tier concise and action-focused.
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="tier-label">🟡 Early signs of dysregulation</div>', unsafe_allow_html=True)
            r["react_early"] = st.text_area(
                "What to do at first signs",
                r["react_early"], height=110, key=f"re_early_{idx}",
                help="Specific staff actions when early warning signs are observed — before escalation occurs"
            )

            st.markdown('<hr class="tier-divider">', unsafe_allow_html=True)
            st.markdown('<div class="tier-label">🟠 Student has left the program space but remains on CLC grounds</div>', unsafe_allow_html=True)
            r["react_on_grounds"] = st.text_area(
                "Response — on CLC grounds",
                r["react_on_grounds"], height=110, key=f"re_gnd_{idx}"
            )

            st.markdown('<hr class="tier-divider">', unsafe_allow_html=True)
            st.markdown('<div class="tier-label">🔴 Student has left CLC grounds</div>', unsafe_allow_html=True)
            r["react_left_grounds"] = st.text_area(
                "Response — off CLC grounds (community follow protocol)",
                r["react_left_grounds"], height=130, key=f"re_off_{idx}"
            )

            st.markdown('<hr class="tier-divider">', unsafe_allow_html=True)
            st.markdown('<div class="tier-label">🟢 When student is returned to CLC</div>', unsafe_allow_html=True)
            r["react_returned"] = st.text_area(
                "Response — on return",
                r["react_returned"], height=100, key=f"re_ret_{idx}"
            )

            st.markdown('<hr class="tier-divider">', unsafe_allow_html=True)
            st.markdown('<div class="tier-label">📋 Post-incident actions</div>', unsafe_allow_html=True)
            r["react_post"] = st.text_area(
                "Post-incident requirements",
                r["react_post"], height=110, key=f"re_post_{idx}",
                help="e.g. ABCH Critical Incident Report, IRMS, CARL, DCP notification, staff debrief, plan review"
            )

            # ── AI generation ──────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("✨ Generate strategies & procedures with AI"):
                st.markdown('<p class="field-note">Fill in the BOC fields first, then generate. AI will produce CLC-contextualised content following the correct S&R Plan structure.</p>', unsafe_allow_html=True)
                if st.button("Generate proactive strategies & tiered reactive procedures", key=f"gen_ai_{idx}", type="primary"):
                    with st.spinner("Generating CLC-contextualised content…"):
                        student = st.session_state.student
                        sys_prompt = """You are an expert in DfE Safety & Risk Plan requirements for students with complex needs in specialised SA school programs. You understand trauma-informed practice and CPI low-arousal approaches."""
                        user_prompt = f"""
Generate proactive strategies and tiered reactive procedures for the following risk for a student at Cowandilla Learning Centre LBU:

Student: {student['name']}, Age group: {student['program']}, Key staff: {student['key_staff']}
CLC context: {st.session_state.contextual_risks}

Risk title: {r['issue_title']}
Behaviour description: {r['boc_description']}
Characterised by: {r['characterised_by']}
Function: {r['function']}
Risk level: {compute_risk_level(r['likelihood'], r['consequence'])}

CRITICAL RULES:
1. Proactive strategies = ENVIRONMENTAL, SUPERVISORY, STRUCTURAL only. No relational strategies, no skill-building — those go in the BSP.
2. Reactive procedures must use a TIERED structure: early signs / on grounds / left grounds / returned to CLC / post-incident.
3. Be specific — name roles (Staff 1, Staff 2, Admin/Naomi), physical locations, exact actions.
4. CLC physical context: carpark adjacent via climbable fence, Jenkins/Marion/Sir Donald Bradman Drive nearby, South Road ~15 min at pace. Staff use walkie talkies. Vehicle keys in leaders office. School mobile for SAPOL.

Return ONLY a JSON object with these exact keys:
env_supervision, structural, contextual_note,
react_early, react_on_grounds, react_left_grounds, react_returned, react_post

No markdown, no explanation, only valid JSON.
"""
                        raw = groq_chat(user_prompt, system=sys_prompt, max_tokens=2500)
                        try:
                            raw_clean = raw.strip()
                            if raw_clean.startswith("```"):
                                raw_clean = "\n".join(raw_clean.split("\n")[1:])
                            if raw_clean.endswith("```"):
                                raw_clean = raw_clean.rsplit("```", 1)[0]
                            data = json.loads(raw_clean)
                            for k in ["env_supervision","structural","contextual_note",
                                      "react_early","react_on_grounds","react_left_grounds",
                                      "react_returned","react_post"]:
                                if k in data:
                                    r[k] = data[k]
                            st.success("Generated! Review and edit each field.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Parse error: {e}")
                            st.code(raw[:1000])

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 · REVIEW
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 5:
    st.markdown('<div class="section-heading">Review Plan</div>', unsafe_allow_html=True)

    if st.session_state.contextual_risks:
        with st.expander("📋 Contextual Risks (CLC Setting)", expanded=False):
            st.write(st.session_state.contextual_risks)

    for i, r in enumerate(st.session_state.risks):
        level = compute_risk_level(r["likelihood"], r["consequence"])
        with st.expander(f"Risk {i+1}: {r['issue_title'] or '(unnamed)'} — {level}", expanded=(i==0)):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Behaviour of Concern**")
                st.write(r["boc_description"] or "—")
                st.markdown("**Characterised by**")
                st.write(r["characterised_by"] or "—")
                st.markdown("**Function**")
                st.write(r["function"] or "—")
            with c2:
                st.markdown("**Environment & supervision**")
                st.write(r["env_supervision"] or "—")
                st.markdown("**Structural strategies**")
                st.write(r["structural"] or "—")
            st.markdown("**Reactive procedures**")
            for tier, label in [
                ("react_early",        "🟡 Early signs"),
                ("react_on_grounds",   "🟠 On CLC grounds"),
                ("react_left_grounds", "🔴 Left grounds"),
                ("react_returned",     "🟢 On return"),
                ("react_post",         "📋 Post-incident"),
            ]:
                if r[tier]:
                    st.markdown(f"*{label}:* {r[tier]}")

    st.markdown("---")
    st.markdown('<div class="section-heading">Priority Actions & Sign-off</div>', unsafe_allow_html=True)
    st.session_state.priority_actions = st.text_area(
        "Priority actions following this plan (will appear in the document)",
        st.session_state.priority_actions, height=180
    )
    st.session_state.review_date_final = st.text_input(
        "Final review date",
        st.session_state.review_date_final or st.session_state.student.get("review_date","")
    )

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Edit risks", use_container_width=True):
            st.session_state.step = 4
            st.rerun()
    with c2:
        if st.button("→ Generate document", type="primary", use_container_width=True):
            st.session_state.step = 6
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 · GENERATE DOCX
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 6:
    st.markdown('<div class="section-heading">Generate Document</div>', unsafe_allow_html=True)

    def hex_to_rgb(hex_color):
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2],16) for i in (0,2,4))

    def set_cell_bg(cell, hex_color):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  hex_color.lstrip("#"))
        tcPr.append(shd)

    def set_cell_borders(cell, color="CCCCCC"):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        bdr  = OxmlElement("w:tcBorders")
        for side in ["top","left","bottom","right"]:
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"),   "single")
            el.set(qn("w:sz"),    "4")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), color.lstrip("#"))
            bdr.append(el)
        tcPr.append(bdr)

    def add_cell_text(cell, text, bold=False, italic=False, size=9,
                      color="1A1A1A", align=WD_ALIGN_PARAGRAPH.LEFT):
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = align
        run  = para.add_run(text)
        run.bold   = bold
        run.italic = italic
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(*hex_to_rgb(color))

    def add_para(cell, text, bold=False, italic=False, size=9, color="1A1A1A", space_after=2):
        para = cell.add_paragraph()
        para.paragraph_format.space_after = Pt(space_after)
        run  = para.add_run(text)
        run.bold   = bold
        run.italic = italic
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(*hex_to_rgb(color))

    def add_bullets(cell, text, size=9):
        for line in text.split("\n"):
            line = line.strip().lstrip("-•").strip()
            if not line:
                continue
            para = cell.add_paragraph(style="List Bullet")
            para.paragraph_format.space_after = Pt(1)
            run  = para.add_run(line)
            run.font.size = Pt(size)
            run.font.color.rgb = RGBColor(*hex_to_rgb("1A1A1A"))

    def add_tier(cell, label, text, size=9):
        if not text.strip():
            return
        add_para(cell, label, bold=True, size=size, color="1A7A6E", space_after=1)
        add_bullets(cell, text, size=size)

    def build_docx():
        doc = DocxDocument()

        # Page margins
        for section in doc.sections:
            section.page_width  = Cm(21)
            section.page_height = Cm(29.7)
            for attr in ["left_margin","right_margin","top_margin","bottom_margin"]:
                setattr(section, attr, Cm(1.8))

        student = st.session_state.student
        risks   = st.session_state.risks

        # ── Title block ───────────────────────────────────────────────────
        title_tbl = doc.add_table(rows=1, cols=1)
        title_tbl.style = "Table Grid"
        cell = title_tbl.cell(0,0)
        set_cell_bg(cell, "1A7A6E")
        set_cell_borders(cell, "1A7A6E")
        cell.text = ""
        for txt, sz, b in [
            ("SAFETY & RISK MANAGEMENT PLAN", 16, True),
            (f"{student['name']}  |  Cowandilla Learning Centre  |  LBU {student['program']}", 11, False)
        ]:
            p2 = cell.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r2 = p2.add_run(txt)
            r2.bold = b
            r2.font.size  = Pt(sz)
            r2.font.color.rgb = RGBColor(255,255,255)

        doc.add_paragraph()

        # ── Student details table ─────────────────────────────────────────
        det_tbl = doc.add_table(rows=2, cols=2)
        det_tbl.style = "Table Grid"

        left_cell  = det_tbl.cell(0,0)
        right_cell = det_tbl.cell(0,1)
        for cell in [left_cell, right_cell]:
            set_cell_borders(cell)

        left_items = [
            ("Full Name:", student["name"]),
            ("Date of Birth:", student["dob"]),
            ("EDSAS ID:", student["edsas"]),
            ("Program:", student["program"]),
        ]
        right_items = [
            ("Home School:", student["home_school"]),
            ("Key Staff:", student["key_staff"]),
            ("Plan Date:", student["plan_date"]),
            ("Review Date:", st.session_state.review_date_final or student["review_date"]),
        ]
        left_cell.text = ""
        for label, val in left_items:
            add_para(left_cell, f"{label}  {val}", size=9)
        right_cell.text = ""
        for label, val in right_items:
            add_para(right_cell, f"{label}  {val}", size=9)

        # Status row
        status_cell = det_tbl.cell(1,0)
        det_tbl.cell(1,0).merge(det_tbl.cell(1,1))
        set_cell_bg(status_cell, "FDF0DC")
        set_cell_borders(status_cell)
        status_cell.text = ""
        if student["sapol_ref"]:
            add_para(status_cell, f"SAPOL Reference: {student['sapol_ref']}", bold=True, size=9)
        if student["status_note"]:
            add_para(status_cell, f"⚠ {student['status_note']}", italic=True, size=9)

        doc.add_paragraph()

        # ── Contextual risks ──────────────────────────────────────────────
        if st.session_state.contextual_risks.strip():
            ctx_tbl = doc.add_table(rows=2, cols=1)
            ctx_tbl.style = "Table Grid"

            hdr_cell = ctx_tbl.cell(0,0)
            set_cell_bg(hdr_cell, "1A7A6E")
            set_cell_borders(hdr_cell, "1A7A6E")
            add_cell_text(hdr_cell, "CURRENT CONTEXTUAL RISKS — CLC SETTING",
                          bold=True, size=10, color="FFFFFF")

            body_cell = ctx_tbl.cell(1,0)
            set_cell_borders(body_cell)
            body_cell.text = ""
            add_bullets(body_cell, st.session_state.contextual_risks, size=9)

            doc.add_paragraph()

        # ── Risk table ────────────────────────────────────────────────────
        risk_tbl = doc.add_table(rows=1, cols=4)
        risk_tbl.style = "Table Grid"

        headers = [
            "Concerning Behaviour of Concern",
            "Risk",
            "Proactive Strategies to Prevent/Reduce",
            "Procedure to Follow if it Occurs"
        ]
        for j, hdr in enumerate(headers):
            hc = risk_tbl.cell(0, j)
            set_cell_bg(hc, "1A7A6E")
            set_cell_borders(hc, "1A7A6E")
            add_cell_text(hc, hdr, bold=True, size=9, color="FFFFFF")

        for r in st.session_state.risks:
            row  = risk_tbl.add_row()
            level = compute_risk_level(r["likelihood"], r["consequence"])
            level_bg = {"EXTREME":"FCDCDC","HIGH":"FEF0CC","MODERATE":"FEFACC","LOW":"E8F5E9"}.get(level,"FFFFFF")
            level_col= {"EXTREME":"7A1A1A","HIGH":"7A4000","MODERATE":"5A5A00","LOW":"1B5E20"}.get(level,"333333")

            # Col 0: BOC
            boc_cell = row.cells[0]
            set_cell_borders(boc_cell)
            boc_cell.text = ""
            add_para(boc_cell, r["issue_title"], bold=True, size=9)
            if r["boc_description"]:
                add_para(boc_cell, r["boc_description"], size=9, space_after=4)
            if r["characterised_by"]:
                add_para(boc_cell, "Characterised by:", bold=True, size=9, space_after=1)
                add_bullets(boc_cell, r["characterised_by"], size=9)
            if r["function"]:
                add_para(boc_cell, f"Function: {r['function']}", italic=True, size=9)

            # Col 1: Risk rating
            rat_cell = row.cells[1]
            set_cell_bg(rat_cell, level_bg)
            set_cell_borders(rat_cell, level_bg)
            rat_cell.text = ""
            l_key = r["likelihood"][0]
            c_key = r["consequence"][0]
            add_para(rat_cell, f"{l_key}{c_key}", bold=True, size=13, color=level_col)
            add_para(rat_cell, level, bold=True, size=8, color=level_col)
            rat_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Col 2: Proactive
            pro_cell = row.cells[2]
            set_cell_borders(pro_cell)
            pro_cell.text = ""
            if r["env_supervision"]:
                add_para(pro_cell, "Environment & supervision", bold=True, size=9)
                add_bullets(pro_cell, r["env_supervision"], size=9)
            if r["structural"]:
                add_para(pro_cell, "Operational & structural", bold=True, size=9)
                add_bullets(pro_cell, r["structural"], size=9)
            if r["contextual_note"]:
                add_para(pro_cell, "Current contextual factor", bold=True, size=9)
                add_bullets(pro_cell, r["contextual_note"], size=9)

            # Col 3: Reactive (tiered)
            res_cell = row.cells[3]
            set_cell_borders(res_cell)
            res_cell.text = ""
            add_tier(res_cell, "If early signs of dysregulation are observed",         r["react_early"])
            add_tier(res_cell, "If student has left program space but remains on CLC grounds", r["react_on_grounds"])
            add_tier(res_cell, "If student has left CLC grounds",                      r["react_left_grounds"])
            add_tier(res_cell, "When student is returned to CLC",                      r["react_returned"])
            add_tier(res_cell, "Post-incident",                                        r["react_post"])

        # Set column widths
        from docx.oxml.ns import qn as _qn
        from docx.oxml    import OxmlElement as _OE
        def set_col_width(tbl, widths_cm):
            tblGrid = _OE("w:tblGrid")
            for w in widths_cm:
                gc = _OE("w:gridCol")
                gc.set(_qn("w:w"), str(int(w * 567)))
                tblGrid.append(gc)
            tbl._tbl.insert(0, tblGrid)
        set_col_width(risk_tbl, [5.5, 1.7, 5.9, 6.1])

        doc.add_paragraph()

        # ── Priority actions ──────────────────────────────────────────────
        if st.session_state.priority_actions.strip():
            act_tbl = doc.add_table(rows=2, cols=1)
            act_tbl.style = "Table Grid"
            hc2 = act_tbl.cell(0,0)
            set_cell_bg(hc2, "1A7A6E")
            set_cell_borders(hc2, "1A7A6E")
            add_cell_text(hc2, "PRIORITY ACTIONS", bold=True, size=10, color="FFFFFF")
            bc2 = act_tbl.cell(1,0)
            set_cell_borders(bc2)
            bc2.text = ""
            add_bullets(bc2, st.session_state.priority_actions, size=9)
            doc.add_paragraph()

        # ── Sign-off ──────────────────────────────────────────────────────
        sig_tbl = doc.add_table(rows=2, cols=3)
        sig_tbl.style = "Table Grid"
        for j, hdr in enumerate(["Prepared by", "Reviewed by / TAC sign-off", "Next Review Date"]):
            hc3 = sig_tbl.cell(0, j)
            set_cell_bg(hc3, "1A7A6E")
            set_cell_borders(hc3, "1A7A6E")
            add_cell_text(hc3, hdr, bold=True, size=9, color="FFFFFF")
        vals = [
            "_________________________________________\n\nDate: ____________________",
            "All TAC members to sign and date",
            st.session_state.review_date_final or "—"
        ]
        for j, val in enumerate(vals):
            sc = sig_tbl.cell(1, j)
            set_cell_borders(sc)
            sc.text = ""
            add_para(sc, val, size=9)

        # ── Risk matrix ───────────────────────────────────────────────────
        doc.add_paragraph()
        mat_tbl = doc.add_table(rows=7, cols=6)
        mat_tbl.style = "Table Grid"
        mat_headers = ["Likelihood \\ Consequence","1 – Insignificant","2 – Minor","3 – Moderate","4 – Major","5 – Catastrophic"]
        for j, h in enumerate(mat_headers):
            hc4 = mat_tbl.cell(0,j)
            set_cell_bg(hc4, "1A7A6E")
            set_cell_borders(hc4, "1A7A6E")
            add_cell_text(hc4, h, bold=True, size=8, color="FFFFFF", align=WD_ALIGN_PARAGRAPH.CENTER)
        mat_data = [
            ("E – Almost Certain",  ["High","High","Extreme","Extreme","Extreme"]),
            ("D – Likely/Frequently",["Moderate","High","High","Extreme","Extreme"]),
            ("C – Likely Sometimes", ["Low","Moderate","High","Extreme","Extreme"]),
            ("B – Unlikely",         ["Low","Low","Moderate","High","Extreme"]),
            ("A – Rare",             ["Low","Low","Moderate","High","High"]),
        ]
        level_styles = {
            "Extreme":  ("FCDCDC","7A1A1A"),
            "High":     ("FEF0CC","7A4000"),
            "Moderate": ("FEFACC","5A5A00"),
            "Low":      ("E8F5E9","1B5E20"),
        }
        for i, (lik, vals_row) in enumerate(mat_data, 1):
            add_cell_text(mat_tbl.cell(i,0), lik, bold=True, size=8)
            set_cell_borders(mat_tbl.cell(i,0))
            for j, v in enumerate(vals_row, 1):
                mc = mat_tbl.cell(i,j)
                bg, col = level_styles.get(v, ("FFFFFF","333333"))
                set_cell_bg(mc, bg)
                set_cell_borders(mc, bg)
                add_cell_text(mc, v, bold=True, size=8, color=col, align=WD_ALIGN_PARAGRAPH.CENTER)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    with st.spinner("Building your Safety & Risk Management Plan…"):
        try:
            docx_buf = build_docx()
            student_name_safe = st.session_state.student["name"].replace(" ","_")
            filename = f"Safety_Risk_Plan_{student_name_safe}_{date.today().strftime('%d%b%Y')}.docx"

            st.success("✅ Your Safety & Risk Management Plan is ready.")
            st.markdown("""
            <div class="card-teal">
            <strong>Structure reminder:</strong><br>
            This document contains the Safety &amp; Risk Plan only — BOC, risk ratings,
            environmental/supervisory strategies, and tiered reactive procedures.<br><br>
            <strong>Relational strategies, skill-building targets, scripted language, and peer
            management protocols should be documented in the Behaviour Support Plan</strong>
            (separate document).
            </div>
            """, unsafe_allow_html=True)

            st.download_button(
                label="⬇️ Download Safety & Risk Plan (.docx)",
                data=docx_buf,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("← Back to review"):
                st.session_state.step = 5
                st.rerun()

            if st.button("🔄 Start new plan", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        except Exception as e:
            st.error(f"Error generating document: {e}")
            import traceback
            st.code(traceback.format_exc())
            if st.button("← Back to review"):
                st.session_state.step = 5
                st.rerun()
