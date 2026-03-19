"""
CLC Safety & Risk Management Plan Builder
Cowandilla Learning Centre – LBU Portal Tool

Multi-step wizard that:
1. Collects student details
2. Optionally ingests an existing school safety plan (docx)
3. Uses AI to extract risks and prompt CLC-specific contextualisation
4. Generates a formatted CLC .docx Safety & Risk Management Plan
"""

import streamlit as st
import anthropic
import json
import os
import io
from datetime import date
from copy import deepcopy

# python-docx for output
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Cm, Inches, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Brand colours ──────────────────────────────────────────────────────────────
TEAL       = "#1A7A6E"
TEAL_LIGHT = "#D6EEEB"
AMBER      = "#D97706"
AMBER_LIGHT= "#FEF3C7"
GREY_DARK  = "#2E4057"
GREY_LIGHT = "#F2F6F6"
RED_RISK   = "#C0392B"
ORANGE_RISK= "#E67E22"
YELLOW_RISK= "#F1C40F"

# ── Risk matrix ────────────────────────────────────────────────────────────────
LIKELIHOOD_OPTIONS = ["A – Rare", "B – Unlikely", "C – Likely sometimes", "D – Likely/frequently", "E – Almost certain"]
CONSEQUENCE_OPTIONS= ["1 – Insignificant", "2 – Minor", "3 – Moderate", "4 – Major", "5 – Catastrophic"]

RISK_MATRIX = {
    ("E","5"): "EXTREME", ("E","4"): "EXTREME", ("E","3"): "EXTREME",
    ("E","2"): "HIGH",    ("E","1"): "HIGH",
    ("D","5"): "EXTREME", ("D","4"): "EXTREME", ("D","3"): "HIGH",
    ("D","2"): "HIGH",    ("D","1"): "MODERATE",
    ("C","5"): "EXTREME", ("C","4"): "EXTREME", ("C","3"): "HIGH",
    ("C","2"): "MODERATE",("C","1"): "LOW",
    ("B","5"): "HIGH",    ("B","4"): "HIGH",    ("B","3"): "MODERATE",
    ("B","2"): "LOW",     ("B","1"): "LOW",
    ("A","5"): "HIGH",    ("A","4"): "HIGH",    ("A","3"): "MODERATE",
    ("A","2"): "LOW",     ("A","1"): "LOW",
}

RISK_COLOURS = {
    "EXTREME": RED_RISK, "HIGH": ORANGE_RISK, "MODERATE": YELLOW_RISK, "LOW": "#27AE60"
}

# Blank risk template
BLANK_RISK = {
    "issue_title": "",
    "issue_detail": "",
    "triggers": "",
    "function": "",
    "likelihood": "D – Likely/frequently",
    "consequence": "3 – Moderate",
    "proactive": "",
    "procedure": "",
    "clc_notes": "",
    "from_school": False,
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Safety & Risk Plan Builder | CLC LBU",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
  }}

  /* Top bar */
  .clc-header {{
    background: {TEAL};
    color: white;
    padding: 18px 28px 14px;
    border-radius: 10px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .clc-header h1 {{ margin:0; font-size:1.3rem; font-weight:700; letter-spacing:0.02em; }}
  .clc-header p  {{ margin:0; font-size:0.82rem; opacity:0.8; }}
  .clc-badge {{
    background: {AMBER};
    color: white;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 20px;
    letter-spacing: 0.05em;
  }}

  /* Step progress */
  .step-bar {{
    display: flex;
    gap: 6px;
    margin-bottom: 28px;
  }}
  .step-item {{
    flex: 1;
    padding: 8px 0;
    text-align: center;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: 6px;
    background: #E8F5F3;
    color: #888;
    border: 2px solid transparent;
    letter-spacing: 0.03em;
  }}
  .step-item.active {{
    background: {TEAL};
    color: white;
    border-color: {TEAL};
  }}
  .step-item.done {{
    background: #D6EEEB;
    color: {TEAL};
    border-color: {TEAL};
  }}

  /* Cards */
  .card {{
    background: white;
    border: 1.5px solid #E2EEF0;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }}
  .card-teal {{
    background: {TEAL_LIGHT};
    border-color: {TEAL};
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 14px;
  }}
  .card-amber {{
    background: {AMBER_LIGHT};
    border-left: 4px solid {AMBER};
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 14px;
    font-size: 0.87rem;
  }}
  .card-risk {{
    border-left: 4px solid {RED_RISK};
    background: #FDF3F2;
    border-radius: 6px;
    padding: 14px 18px;
    margin: 8px 0;
  }}

  /* Risk badge */
  .risk-badge {{
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 4px;
    color: white;
    letter-spacing: 0.05em;
    margin-left: 8px;
  }}

  /* AI bubble */
  .ai-bubble {{
    background: linear-gradient(135deg, #1A7A6E15, #1A7A6E08);
    border: 1.5px solid {TEAL};
    border-radius: 12px 12px 12px 2px;
    padding: 14px 18px;
    margin: 10px 0 16px;
    font-size: 0.88rem;
    line-height: 1.6;
    color: #1A3530;
  }}
  .ai-label {{
    font-size: 0.7rem;
    font-weight: 700;
    color: {TEAL};
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }}

  /* Section heading */
  .section-heading {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {TEAL};
    margin: 20px 0 8px;
    border-bottom: 2px solid {TEAL_LIGHT};
    padding-bottom: 4px;
  }}

  /* Risk summary card */
  .risk-summary {{
    background: white;
    border: 1.5px solid #E2EEF0;
    border-left: 5px solid {TEAL};
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
    cursor: pointer;
  }}
  .risk-title {{ font-weight: 600; font-size: 0.92rem; color: {GREY_DARK}; }}
  .risk-meta  {{ font-size: 0.78rem; color: #888; margin-top: 3px; }}

  /* Streamlit tweaks */
  .stTextInput > div > div > input,
  .stTextArea > div > div > textarea,
  .stSelectbox > div > div {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
  }}
  .stButton > button {{
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
  }}
  div[data-testid="stExpander"] {{
    border: 1.5px solid #D6EEEB !important;
    border-radius: 8px !important;
  }}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key:
        st.error("⚠️  ANTHROPIC_API_KEY not found. Add it to your Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)


def extract_docx_text(uploaded_file) -> str:
    """Extract plain text from an uploaded docx using python-docx (no pandoc required)."""
    try:
        doc = DocxDocument(io.BytesIO(uploaded_file.read()))
        lines = []
        # Body paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text.strip())
        # Table cells (risk rows are almost always in tables)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = " ".join(
                        p.text.strip() for p in cell.paragraphs if p.text.strip()
                    )
                    if cell_text:
                        lines.append(cell_text)
        return "\n".join(lines)
    except Exception as e:
        return f"[Extraction error: {e}]"


def ai_extract_risks(plan_text: str, student_name: str):
    """Ask AI to extract risk rows from a school plan as structured JSON."""
    client = get_client()
    prompt = f"""You are analysing a Safety and Risk Management Plan from a mainstream school for a student named {student_name}.

Extract all identified risk/concern rows from the plan below. For each risk, return a JSON object with:
- issue_title: short name (e.g. "Absconding from school grounds")
- issue_detail: full description of the behaviour/concern (2-4 sentences)
- triggers: known triggers listed (as a string, semicolons between items)
- function: function of behaviour if stated (e.g. "Avoidance – adult")
- likelihood: likelihood code if present (A/B/C/D/E), default "D"
- consequence: consequence code if present (1-2-3-4-5), default "3"
- proactive: proactive strategies (as string with newlines)
- procedure: reactive procedures (as string with newlines)

Return ONLY a JSON array of risk objects. No preamble, no markdown fences.

PLAN TEXT:
{plan_text[:8000]}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = resp.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        risks = json.loads(raw)
        for r in risks:
            r["from_school"] = True
            r["clc_notes"] = ""
        return risks
    except Exception as e:
        st.warning(f"AI extraction encountered an issue ({e}). You can enter risks manually.")
        return []


def ai_contextualise(risk: dict, student: dict, all_risks: list) -> str:
    """Generate CLC-specific contextualisation questions and suggestions for a risk."""
    client = get_client()
    risk_text = f"""
Risk: {risk.get('issue_title','')}
Detail: {risk.get('issue_detail','')}
Triggers: {risk.get('triggers','')}
Function: {risk.get('function','')}
School proactive strategies: {risk.get('proactive','')}
School procedures: {risk.get('procedure','')}
"""
    context = f"""Student: {student.get('name','Unknown')}, Age {student.get('age','')}, Program {student.get('program','')}
Home school: {student.get('home_school','')}
CLC staff involved: {student.get('key_staff','')}
CLC context notes: {student.get('clc_context','')}
"""
    prompt = f"""You are a behaviour support specialist helping CLC (Cowandilla Learning Centre) staff adapt a mainstream school Safety & Risk Management Plan for use in their specialist Learning and Behaviour Unit (LBU).

CLC is a small specialist site in Adelaide for students excluded from mainstream education. Key contextual differences:
- CLC is adjacent to a carpark accessible from the playground via a climbable fence, with Jenkins Road, Marion Road, and Sir Donald Bradman Drive nearby
- All staff carry walkie talkies; a program vehicle is available
- Cohort is small; peer dynamics are heightened
- CARL, DCP, IRMS, and TAC processes apply
- Trauma-informed, relational practice underpins all work

STUDENT CONTEXT:
{context}

SCHOOL RISK (to be adapted for CLC):
{risk_text}

Your task: Write a SHORT, professional advisory note (200-300 words) for the staff member completing this plan that:
1. Highlights what aspects of this risk are likely to be DIFFERENT at CLC vs the home school (physical environment, staffing, peer cohort, processes)
2. Asks 3-4 specific CLC-contextualising questions the staff member should consider before finalising this section (e.g. "Has this behaviour been observed at CLC?", "Who is Xavier's key worker?")
3. Suggests 2-3 CLC-specific additions to the proactive strategies or procedures that the school plan may have missed

Keep it practical, direct, and relevant to a trauma-informed specialist setting. Do not repeat the school plan content back verbatim."""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"[AI unavailable: {e}]"


def ai_generate_clc_strategies(risk: dict, student: dict) -> dict:
    """Generate CLC-specific proactive strategies and procedures."""
    client = get_client()
    prompt = f"""You are a behaviour support specialist writing a CLC (Cowandilla Learning Centre) Safety & Risk Management Plan for a student.

Student: {student.get('name','')}, Age {student.get('age','')}, Program {student.get('program','')}
Key staff: {student.get('key_staff','')}

Risk: {risk.get('issue_title','')}
Detail: {risk.get('issue_detail','')}
Triggers: {risk.get('triggers','')}
Function of behaviour: {risk.get('function','')}
Staff notes / CLC context: {risk.get('clc_notes','')}

CLC context: small specialist site in Adelaide, adjacent to carpark/busy roads, walkie talkies carried, TAC processes, CARL/DCP/IRMS reporting, trauma-informed relational practice.

Generate CLC-specific content in two sections. Return as JSON only (no markdown):
{{
  "proactive": "bullet list of 5-8 CLC-specific proactive strategies, one per line starting with •",
  "procedure": "structured reactive procedures with subheadings, using format:\\n### Subheading\\n• bullet\\n• bullet\\n\\n### Next subheading\\n• bullet"
}}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except Exception:
        return {"proactive": "", "procedure": ""}


def compute_risk_level(likelihood: str, consequence: str) -> str:
    l = likelihood.split("–")[0].strip().split(" ")[0]
    c = consequence.split("–")[0].strip().split(" ")[0]
    return RISK_MATRIX.get((l, c), "HIGH")


def risk_badge_html(level: str) -> str:
    colour = RISK_COLOURS.get(level, "#888")
    return f'<span class="risk-badge" style="background:{colour}">{level}</span>'


# ── Session state init ─────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "step": 1,
        "student": {
            "name": "", "dob": "", "age": "", "edsas": "",
            "program": "JP", "home_school": "", "key_staff": "",
            "clc_context": "", "plan_date": str(date.today()),
        },
        "school_plan_text": "",
        "risks": [],
        "current_risk": 0,
        "generating": False,
        "ai_context_cache": {},
        "priority_actions": "",
        "review_date": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="clc-header">
  <div>
    <h1>🛡️ Safety &amp; Risk Management Plan Builder</h1>
    <p>Cowandilla Learning Centre — Learning &amp; Behaviour Unit</p>
  </div>
  <span class="clc-badge">PORTAL TOOL</span>
</div>
""", unsafe_allow_html=True)

# ── Step progress bar ──────────────────────────────────────────────────────────
STEPS = ["1 · Student", "2 · School Plan", "3 · Build Risks", "4 · Review", "5 · Generate"]
bar_html = '<div class="step-bar">'
for i, label in enumerate(STEPS, 1):
    cls = "active" if i == st.session_state.step else ("done" if i < st.session_state.step else "step-item")
    if cls == "active":
        bar_html += f'<div class="step-item active">{label}</div>'
    elif i < st.session_state.step:
        bar_html += f'<div class="step-item done">✓ {label}</div>'
    else:
        bar_html += f'<div class="step-item">{label}</div>'
bar_html += "</div>"
st.markdown(bar_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 · Student Details
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == 1:
    st.markdown('<div class="section-heading">Student Details</div>', unsafe_allow_html=True)

    s = st.session_state.student
    col1, col2 = st.columns(2)
    with col1:
        s["name"]        = st.text_input("Full Name *", value=s["name"])
        s["dob"]         = st.text_input("Date of Birth (DD/MM/YYYY)", value=s["dob"])
        s["age"]         = st.text_input("Age", value=s["age"])
        s["edsas"]       = st.text_input("EDSAS ID", value=s["edsas"])
    with col2:
        s["program"]     = st.selectbox("Program", ["JP","MP","SP","Other"], index=["JP","MP","SP","Other"].index(s["program"]) if s["program"] in ["JP","MP","SP","Other"] else 0)
        s["home_school"] = st.text_input("Home School", value=s["home_school"])
        s["key_staff"]   = st.text_input("CLC Key Staff Involved (names)", value=s["key_staff"], help="e.g. Annette, Vinnie, Naomi")
        s["plan_date"]   = st.text_input("Plan Date", value=s["plan_date"])

    st.markdown('<div class="section-heading">CLC Context</div>', unsafe_allow_html=True)
    s["clc_context"] = st.text_area(
        "Brief context about this student at CLC (triggers, history, current concerns)",
        value=s["clc_context"], height=100,
        help="This will inform AI-generated prompts throughout the plan builder."
    )

    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("Continue →", type="primary", use_container_width=False):
        if not s["name"].strip():
            st.error("Student name is required.")
        else:
            st.session_state.step = 2
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 · School Plan Upload
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 2:
    st.markdown('<div class="section-heading">Existing School Safety Plan</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="card-amber">
    <strong>Does {st.session_state.student['name']}'s home school have an existing Safety &amp; Risk Management Plan?</strong><br>
    If yes, upload it below and the AI will extract the risk rows and pre-populate the builder —
    you'll then review and adapt each one for CLC's context.
    If no, you'll build the plan from scratch.
    </div>
    """, unsafe_allow_html=True)

    col_upload, col_skip = st.columns([2, 1])

    with col_upload:
        uploaded = st.file_uploader(
            "Upload school plan (.docx)",
            type=["docx"],
            help="Upload the most recent version from the student's home school."
        )

    if uploaded:
        with st.spinner("Extracting document text…"):
            plan_text = extract_docx_text(uploaded)
            st.session_state.school_plan_text = plan_text

        st.markdown(f"""
        <div class="card-teal">
        ✅ <strong>Document received.</strong> The AI will now extract risk rows from this plan.
        Click <em>Extract &amp; Continue</em> to proceed.
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Preview extracted text"):
            st.text(plan_text[:2000] + ("…" if len(plan_text) > 2000 else ""))

        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("← Back", use_container_width=True):
                st.session_state.step = 1; st.rerun()
        with col_b:
            if st.button("Extract risks from school plan →", type="primary", use_container_width=True):
                with st.spinner("AI is reading the school plan and extracting risks…"):
                    extracted = ai_extract_risks(plan_text, st.session_state.student["name"])
                if extracted:
                    # Merge with any manually added risks, don't duplicate
                    existing_titles = [r["issue_title"] for r in st.session_state.risks]
                    for r in extracted:
                        if r["issue_title"] not in existing_titles:
                            st.session_state.risks.append({**BLANK_RISK, **r})
                    st.success(f"Extracted {len(extracted)} risk(s) from the school plan.")
                st.session_state.step = 3; st.rerun()
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("← Back", use_container_width=True):
                st.session_state.step = 1; st.rerun()
        with col_b:
            if st.button("No school plan – build from scratch →", type="primary", use_container_width=True):
                st.session_state.step = 3; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 · Risk Builder
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 3:

    student = st.session_state.student
    risks = st.session_state.risks

    # Sidebar-style risk list
    left, right = st.columns([1, 2], gap="large")

    with left:
        st.markdown('<div class="section-heading">Risk Areas</div>', unsafe_allow_html=True)

        for i, r in enumerate(risks):
            level = compute_risk_level(r["likelihood"], r["consequence"])
            col_sel = "#1A7A6E20" if i == st.session_state.current_risk else "white"
            border  = f"border-left: 5px solid {RISK_COLOURS.get(level,'#888')};"
            label   = r["issue_title"] or f"Risk {i+1} (unnamed)"
            if st.button(f"{'▶ ' if i==st.session_state.current_risk else ''}{label}", key=f"sel_{i}",
                         use_container_width=True):
                st.session_state.current_risk = i
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("＋ Add new risk", use_container_width=True):
            risks.append(deepcopy(BLANK_RISK))
            st.session_state.current_risk = len(risks) - 1
            st.rerun()

        if risks:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("→ Continue to Review", type="primary", use_container_width=True):
                # Validate at least one risk has a title
                if all(r["issue_title"].strip() == "" for r in risks):
                    st.error("Please complete at least one risk before continuing.")
                else:
                    st.session_state.step = 4; st.rerun()

        if st.button("← Back", use_container_width=True):
            st.session_state.step = 2; st.rerun()

    with right:
        if not risks:
            st.markdown(f"""
            <div class="card-teal">
            <strong>No risks added yet.</strong><br>
            Click <em>＋ Add new risk</em> on the left to begin, or go back and upload a school plan
            to have risks extracted automatically.
            </div>
            """, unsafe_allow_html=True)
        else:
            idx = st.session_state.current_risk
            if idx >= len(risks):
                idx = 0; st.session_state.current_risk = 0
            r = risks[idx]

            badge = f" {risk_badge_html(compute_risk_level(r['likelihood'], r['consequence']))}" if r['issue_title'] else ""
            origin = f'<span style="font-size:0.72rem;color:#888;margin-left:8px;">{"📋 from school plan" if r.get("from_school") else "✏️ manual entry"}</span>'
            st.markdown(f'<div class="section-heading">Risk {idx+1} of {len(risks)} {badge} {origin}</div>', unsafe_allow_html=True)

            # ── AI Contextualisation Prompt ────────────────────────────────
            if r.get("from_school") and r["issue_title"]:
                cache_key = f"ctx_{idx}_{r['issue_title']}"
                if cache_key not in st.session_state.ai_context_cache:
                    with st.spinner("AI is generating CLC contextualisation prompts…"):
                        advice = ai_contextualise(r, student, risks)
                        st.session_state.ai_context_cache[cache_key] = advice
                advice = st.session_state.ai_context_cache.get(cache_key, "")
                if advice:
                    st.markdown(f"""
                    <div class="ai-bubble">
                    <div class="ai-label">🤖 AI · CLC CONTEXTUALISATION PROMPTS</div>
                    {advice.replace(chr(10), "<br>")}
                    </div>
                    """, unsafe_allow_html=True)

            # ── Issue details ──────────────────────────────────────────────
            st.markdown('<div class="section-heading">Issue / Behaviour</div>', unsafe_allow_html=True)
            r["issue_title"] = st.text_input("Short title for this risk *",
                value=r["issue_title"], key=f"title_{idx}",
                placeholder="e.g. Absconding from CLC grounds")
            r["issue_detail"] = st.text_area("Full description of the behaviour/concern",
                value=r["issue_detail"], key=f"detail_{idx}", height=110,
                placeholder="Describe what the behaviour looks like, how often, and any relevant history at CLC…")
            r["triggers"] = st.text_input("Known triggers",
                value=r["triggers"], key=f"triggers_{idx}",
                placeholder="e.g. Peer conflict; transition; unexpected change; adult demands")
            r["function"] = st.text_input("Function of behaviour",
                value=r["function"], key=f"function_{idx}",
                placeholder="e.g. Avoidance – adult and peer")

            # ── CLC-specific context note ──────────────────────────────────
            st.markdown('<div class="section-heading">CLC-Specific Context</div>', unsafe_allow_html=True)
            st.caption("Note any CLC-specific factors that differ from the school plan — environment, staffing, peers, incidents observed at CLC to date.")
            r["clc_notes"] = st.text_area("CLC context notes for this risk",
                value=r["clc_notes"], key=f"clcnotes_{idx}", height=90,
                placeholder="e.g. Xavier has already climbed the carpark fence at CLC on 19/03/2026. Jenkins Road and Marion Road are within 100m of the site…")

            # ── Risk rating ────────────────────────────────────────────────
            st.markdown('<div class="section-heading">Risk Rating</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                r["likelihood"] = st.selectbox("Likelihood", LIKELIHOOD_OPTIONS,
                    index=LIKELIHOOD_OPTIONS.index(r["likelihood"]) if r["likelihood"] in LIKELIHOOD_OPTIONS else 3,
                    key=f"like_{idx}")
            with c2:
                r["consequence"] = st.selectbox("Consequence", CONSEQUENCE_OPTIONS,
                    index=CONSEQUENCE_OPTIONS.index(r["consequence"]) if r["consequence"] in CONSEQUENCE_OPTIONS else 2,
                    key=f"cons_{idx}")
            with c3:
                level = compute_risk_level(r["likelihood"], r["consequence"])
                col = RISK_COLOURS.get(level, "#888")
                st.markdown(f"""
                <div style="background:{col};color:white;border-radius:8px;padding:20px 12px 12px;text-align:center;margin-top:4px;">
                  <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;opacity:0.9;">RISK LEVEL</div>
                  <div style="font-size:1.5rem;font-weight:700;margin-top:2px;">{level}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── Strategies ─────────────────────────────────────────────────
            st.markdown('<div class="section-heading">Proactive Strategies</div>', unsafe_allow_html=True)

            gen_col, _ = st.columns([1, 2])
            with gen_col:
                if st.button("✨ Generate CLC strategies with AI", key=f"gen_{idx}",
                             disabled=not r["issue_title"].strip()):
                    with st.spinner("Generating CLC-specific strategies…"):
                        generated = ai_generate_clc_strategies(r, student)
                        if generated.get("proactive"):
                            r["proactive"] = generated["proactive"]
                        if generated.get("procedure"):
                            r["procedure"] = generated["procedure"]
                    st.rerun()

            r["proactive"] = st.text_area(
                "Proactive strategies (one per line, start each with •)",
                value=r["proactive"], key=f"proactive_{idx}", height=180,
                placeholder="• Ensure playground gate is always latched and supervised\n• All staff to carry walkie talkies during break times\n• Embed daily co-regulation check-in…"
            )

            st.markdown('<div class="section-heading">Reactive Procedures</div>', unsafe_allow_html=True)
            st.caption("Use ### Subheading to break into sections (e.g. ### If Xavier shows early warning signs:)")
            r["procedure"] = st.text_area(
                "Step-by-step procedures",
                value=r["procedure"], key=f"procedure_{idx}", height=220,
                placeholder="### If early signs of dysregulation:\n• Offer co-regulation strategy…\n\n### If Xavier has left the grounds:\n• Staff 1 follow on foot…\n• Radio location updates…"
            )

            # ── Delete ─────────────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑 Remove this risk", key=f"del_{idx}"):
                risks.pop(idx)
                st.session_state.current_risk = max(0, idx - 1)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 · Review
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 4:
    student = st.session_state.student
    risks = st.session_state.risks

    st.markdown('<div class="section-heading">Plan Summary — Review Before Generating</div>', unsafe_allow_html=True)

    # Student panel
    st.markdown(f"""
    <div class="card">
    <strong>{student['name']}</strong> &nbsp;|&nbsp; DOB: {student['dob']} &nbsp;|&nbsp; Age: {student['age']} &nbsp;|&nbsp;
    EDSAS: {student['edsas']} &nbsp;|&nbsp; Program: {student['program']} &nbsp;|&nbsp;
    Home school: {student['home_school']}<br>
    <span style="color:#666;font-size:0.85rem;">Key staff: {student['key_staff']} &nbsp;·&nbsp; Plan date: {student['plan_date']}</span>
    </div>
    """, unsafe_allow_html=True)

    if not risks:
        st.warning("No risks have been added. Go back to Step 3 to add risks.")
    else:
        st.markdown(f"**{len(risks)} risk(s) identified:**")
        for i, r in enumerate(risks):
            level = compute_risk_level(r["likelihood"], r["consequence"])
            col = RISK_COLOURS.get(level, "#888")
            title = r["issue_title"] or f"Unnamed risk {i+1}"
            with st.expander(f"Risk {i+1}: {title}  [{level}]"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Likelihood:** {r['likelihood']}")
                    st.markdown(f"**Consequence:** {r['consequence']}")
                    st.markdown(f"**Function:** {r['function'] or '—'}")
                    st.markdown(f"**Triggers:** {r['triggers'] or '—'}")
                with c2:
                    st.markdown(f"**Risk level:** :red[{level}]" if level in ("EXTREME","HIGH") else f"**Risk level:** {level}")
                    st.markdown(f"**CLC notes:** {r['clc_notes'] or '—'}")
                st.markdown("**Proactive strategies:**")
                st.text(r["proactive"] or "(none entered)")
                st.markdown("**Procedures:**")
                st.text(r["procedure"] or "(none entered)")

    # Priority actions
    st.markdown('<div class="section-heading">Priority Actions</div>', unsafe_allow_html=True)
    st.session_state.priority_actions = st.text_area(
        "List any priority actions arising from this plan (one per line)",
        value=st.session_state.priority_actions,
        height=130,
        placeholder="• Schedule TAC meeting within 5 school days\n• Conduct fence risk audit\n• Ensure all staff have read and signed this plan…"
    )

    # Review date
    st.session_state.review_date = st.text_input("Review Date", value=st.session_state.review_date, placeholder="e.g. 19/05/2026")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        if st.button("← Back to risks", use_container_width=True):
            st.session_state.step = 3; st.rerun()
    with col_c:
        if st.button("✅ Generate Safety Plan (.docx)", type="primary", use_container_width=True):
            if not risks or all(r["issue_title"].strip() == "" for r in risks):
                st.error("Please complete at least one risk row.")
            else:
                st.session_state.step = 5; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 · Generate .docx
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 5:
    student = st.session_state.student
    risks = st.session_state.risks
    priority_actions = st.session_state.get("priority_actions", "")
    review_date = st.session_state.get("review_date", "")

    st.markdown('<div class="section-heading">Generating Document</div>', unsafe_allow_html=True)

    def rgb(hex_str):
        h = hex_str.lstrip("#")
        return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

    def set_cell_bg(cell, hex_color):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), hex_color.lstrip("#"))
        tcPr.append(shd)

    def set_cell_borders(cell, color="1A7A6E", size="4"):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        for side in ['top','left','bottom','right']:
            border = OxmlElement(f'w:{side}')
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), size)
            border.set(qn('w:space'), '0')
            border.set(qn('w:color'), color.lstrip("#"))
            tcBorders.append(border)
        tcPr.append(tcBorders)

    def add_run(para, text, bold=False, italic=False, size=18, color="000000", font="Arial"):
        run = para.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(size / 2)
        run.font.color.rgb = rgb(color)
        run.font.name = font
        return run

    def cell_para(cell, text, bold=False, italic=False, size=18, color="000000",
                  align=WD_ALIGN_PARAGRAPH.LEFT, space_before=40, space_after=40):
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before / 20)
        p.paragraph_format.space_after  = Pt(space_after / 20)
        p.alignment = align
        if text:
            add_run(p, text, bold=bold, italic=italic, size=size, color=color)
        return p

    def cell_bullet(cell, text, size=17, color="333333"):
        p = cell.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after  = Pt(1)
        add_run(p, text, size=size, color=color)
        return p

    def add_procedure_content(cell, text: str):
        """Parse ### Subheading and • bullets from procedure text into formatted paragraphs."""
        if not text.strip():
            cell_para(cell, "(Not completed)", italic=True, color="888888")
            return
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("###"):
                heading = line.lstrip("# ").strip()
                p = cell.add_paragraph()
                p.paragraph_format.space_before = Pt(5)
                p.paragraph_format.space_after  = Pt(2)
                add_run(p, heading, bold=True, color=TEAL.lstrip("#"), size=17)
            elif line.startswith("•") or line.startswith("-"):
                txt = line.lstrip("•-").strip()
                cell_bullet(cell, txt)
            else:
                p = cell.add_paragraph()
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after  = Pt(2)
                add_run(p, line, size=17)

    def add_proactive_content(cell, text: str):
        if not text.strip():
            cell_para(cell, "(Not completed)", italic=True, color="888888")
            return
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("•") or line.startswith("-"):
                cell_bullet(cell, line.lstrip("•-").strip())
            elif line.startswith("###"):
                p = cell.add_paragraph()
                add_run(p, line.lstrip("# "), bold=True, color=TEAL.lstrip("#"), size=17)
            else:
                p = cell.add_paragraph()
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after  = Pt(2)
                add_run(p, line, size=17)

    # ── Build docx ─────────────────────────────────────────────────────────
    with st.spinner("Building your Safety & Risk Management Plan…"):
        doc = DocxDocument()

        # Page margins
        section = doc.sections[0]
        section.page_width  = Cm(21)
        section.page_height = Cm(29.7)
        for attr in ('left_margin','right_margin','top_margin','bottom_margin'):
            setattr(section, attr, Cm(1.5))

        # Title block
        title_tbl = doc.add_table(rows=1, cols=1)
        title_tbl.style = 'Table Grid'
        tc = title_tbl.rows[0].cells[0]
        set_cell_bg(tc, TEAL.lstrip("#"))
        p1 = tc.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_run(p1, "SAFETY & RISK MANAGEMENT PLAN", bold=True, size=28, color="FFFFFF")
        p2 = cell_para(tc, f"{student['name']}  |  Cowandilla Learning Centre  |  LBU {student['program']} Program",
                       size=18, color="FEF3C7", align=WD_ALIGN_PARAGRAPH.CENTER, space_before=20, space_after=40)

        doc.add_paragraph()

        # Student details table
        det = doc.add_table(rows=3, cols=2)
        det.style = 'Table Grid'
        # Header row
        hdr = det.rows[0].cells[0].merge(det.rows[0].cells[1])
        set_cell_bg(hdr, GREY_DARK.lstrip("#"))
        set_cell_borders(hdr, color=TEAL.lstrip("#"))
        p = hdr.paragraphs[0]
        add_run(p, "STUDENT DETAILS", bold=True, size=18, color="FFFFFF")

        # Detail rows
        row1 = det.rows[1]
        row2 = det.rows[2]
        details_l = [
            ("Full Name", student['name']),
            ("Date of Birth", student['dob']),
            ("Age", student['age']),
            ("EDSAS ID", student['edsas']),
        ]
        details_r = [
            ("Home School", student['home_school']),
            ("Program", student['program']),
            ("Plan Date", student['plan_date']),
            ("Review Date", review_date or "TBC"),
        ]
        for cell_obj, items in [(row1.cells[0], details_l), (row1.cells[1], details_r)]:
            set_cell_bg(cell_obj, "F2F6F6")
            set_cell_borders(cell_obj, color=TEAL.lstrip("#"))
            cell_obj.paragraphs[0].clear()
            for label, val in items:
                p = cell_obj.add_paragraph()
                add_run(p, f"{label}: ", bold=True, size=17, color=GREY_DARK.lstrip("#"))
                add_run(p, val, size=17)

        # Status note row
        status_row = det.rows[2]
        status_cell = status_row.cells[0].merge(status_row.cells[1])
        set_cell_bg(status_cell, AMBER_LIGHT.lstrip("#"))
        set_cell_borders(status_cell, color=AMBER.lstrip("#"))
        p = status_cell.paragraphs[0]
        add_run(p, "⚠  Key Staff: ", bold=True, size=17, color=AMBER.lstrip("#"))
        add_run(p, student['key_staff'] or "—", size=17)
        if student['clc_context']:
            p2 = status_cell.add_paragraph()
            add_run(p2, "CLC Context: ", bold=True, size=16, color="666666")
            add_run(p2, student['clc_context'], size=16, italic=True)

        doc.add_paragraph()

        # ── Main risk table ──────────────────────────────────────────────
        heading_p = doc.add_paragraph()
        add_run(heading_p, "IDENTIFIED RISKS AND MANAGEMENT STRATEGIES", bold=True, size=20, color=GREY_DARK.lstrip("#"))
        note_p = doc.add_paragraph()
        add_run(note_p, "* Risk ratings use the Likelihood/Consequence matrix at the end of this document.", italic=True, size=15, color="666666")

        main_tbl = doc.add_table(rows=1, cols=4)
        main_tbl.style = 'Table Grid'

        # Set column widths
        col_widths = [Cm(5.5), Cm(2.0), Cm(7.0), Cm(8.5)]
        for i, w in enumerate(col_widths):
            for cell_obj in main_tbl.columns[i].cells:
                cell_obj.width = w

        # Header row
        headers = ["Concerning Issue", "Risk Level *", "Proactive Strategies", "Procedure to Follow"]
        for i, h in enumerate(headers):
            c = main_tbl.rows[0].cells[i]
            set_cell_bg(c, TEAL.lstrip("#"))
            set_cell_borders(c, color=TEAL.lstrip("#"))
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_run(p, h, bold=True, size=18, color="FFFFFF")

        # Risk rows
        for r in risks:
            if not r["issue_title"].strip():
                continue
            level = compute_risk_level(r["likelihood"], r["consequence"])
            level_hex = RISK_COLOURS.get(level, "#888").lstrip("#")
            row = main_tbl.add_row()

            # Col 0: Issue
            c0 = row.cells[0]
            set_cell_bg(c0, "D6EEEB")
            set_cell_borders(c0, color=TEAL.lstrip("#"))
            c0.paragraphs[0].clear()
            p = c0.paragraphs[0]
            add_run(p, r["issue_title"], bold=True, size=18, color=GREY_DARK.lstrip("#"))
            if r["issue_detail"]:
                p2 = c0.add_paragraph()
                p2.paragraph_format.space_before = Pt(4)
                add_run(p2, r["issue_detail"], size=16)
            if r["triggers"]:
                p3 = c0.add_paragraph()
                p3.paragraph_format.space_before = Pt(6)
                add_run(p3, "Triggers: ", bold=True, size=16, color=TEAL.lstrip("#"))
                add_run(p3, r["triggers"], size=16)
            if r["function"]:
                p4 = c0.add_paragraph()
                add_run(p4, "Function: ", bold=True, size=15, color="555555")
                add_run(p4, r["function"], size=15, italic=True)
            if r["clc_notes"]:
                p5 = c0.add_paragraph()
                p5.paragraph_format.space_before = Pt(5)
                add_run(p5, "CLC Notes: ", bold=True, size=15, color=AMBER.lstrip("#"))
                add_run(p5, r["clc_notes"], size=15, italic=True)

            # Col 1: Risk rating
            c1 = row.cells[1]
            set_cell_bg(c1, level_hex)
            set_cell_borders(c1, color=level_hex)
            l_code = r["likelihood"].split("–")[0].strip().split(" ")[0]
            c_code = r["consequence"].split("–")[0].strip().split(" ")[0]
            p1 = c1.paragraphs[0]
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_run(p1, f"{l_code}{c_code}", bold=True, size=26, color="FFFFFF")
            p2 = c1.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_run(p2, level, bold=True, size=15, color="FFFFFF")

            # Col 2: Proactive
            c2 = row.cells[2]
            set_cell_borders(c2, color=TEAL.lstrip("#"))
            c2.paragraphs[0].clear()
            add_proactive_content(c2, r["proactive"])

            # Col 3: Procedure
            c3 = row.cells[3]
            set_cell_borders(c3, color=TEAL.lstrip("#"))
            c3.paragraphs[0].clear()
            add_procedure_content(c3, r["procedure"])

        # Footer note row
        footer_row = main_tbl.add_row()
        footer_cell = footer_row.cells[0].merge(footer_row.cells[1]).merge(footer_row.cells[2]).merge(footer_row.cells[3])
        set_cell_bg(footer_cell, "F2F6F6")
        set_cell_borders(footer_cell, color=TEAL.lstrip("#"))
        p = footer_cell.paragraphs[0]
        add_run(p, "* To assess degree of risk, refer to the Likelihood/Consequence matrix on the following page. "
                   "Risk ratings reflect probability and severity without proactive strategies in place.", italic=True, size=14, color="666666")

        doc.add_paragraph()

        # ── Priority actions ─────────────────────────────────────────────
        if priority_actions.strip():
            pa_heading = doc.add_paragraph()
            add_run(pa_heading, "PRIORITY ACTIONS", bold=True, size=20, color=GREY_DARK.lstrip("#"))

            pa_tbl = doc.add_table(rows=1, cols=1)
            pa_tbl.style = 'Table Grid'
            pa_cell = pa_tbl.rows[0].cells[0]
            set_cell_bg(pa_cell, AMBER_LIGHT.lstrip("#"))
            set_cell_borders(pa_cell, color=AMBER.lstrip("#"))
            pa_cell.paragraphs[0].clear()
            for line in priority_actions.splitlines():
                line = line.strip()
                if not line: continue
                if line.startswith("•") or line.startswith("-"):
                    cell_bullet(pa_cell, line.lstrip("•-").strip())
                else:
                    p = pa_cell.add_paragraph()
                    add_run(p, line, size=17)

            doc.add_paragraph()

        # ── Endorsement table ────────────────────────────────────────────
        sign_heading = doc.add_paragraph()
        add_run(sign_heading, "PLAN ENDORSEMENT & REVIEW", bold=True, size=18, color=GREY_DARK.lstrip("#"))

        sign_tbl = doc.add_table(rows=2, cols=3)
        sign_tbl.style = 'Table Grid'
        hdr_row = sign_tbl.rows[0]
        for ci, label in enumerate(["Prepared by", "Reviewed by", "Next Review Date"]):
            c = hdr_row.cells[ci]
            set_cell_bg(c, GREY_DARK.lstrip("#"))
            set_cell_borders(c, color=TEAL.lstrip("#"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_run(c.paragraphs[0], label, bold=True, size=16, color="FFFFFF")
        val_row = sign_tbl.rows[1]
        for ci, val in enumerate(["_______________________", "_______________________", review_date or "TBC"]):
            c = val_row.cells[ci]
            set_cell_bg(c, "F2F6F6")
            set_cell_borders(c, color=TEAL.lstrip("#"))
            p = c.paragraphs[0]
            add_run(p, val, size=17)
            note = c.add_paragraph()
            add_run(note, "Date: ___________" if ci < 2 else "(earlier if incidents occur)", size=14, color="888888", italic=True)

        doc.add_page_break()

        # ── Risk matrix page ─────────────────────────────────────────────
        mx_heading = doc.add_paragraph()
        add_run(mx_heading, "LEVEL OF RISK – REFERENCE MATRIX", bold=True, size=22, color=GREY_DARK.lstrip("#"))

        # Matrix table
        likelihoods = ["E – Almost Certain", "D – Likely/Frequently", "C – Likely Sometimes", "B – Unlikely", "A – Rare"]
        consequences_short = ["1 Insignificant", "2 Minor", "3 Moderate", "4 Major", "5 Catastrophic"]
        matrix_data = [
            ["High","High","Extreme","Extreme","Extreme"],
            ["Moderate","High","High","Extreme","Extreme"],
            ["Low","Moderate","High","Extreme","Extreme"],
            ["Low","Low","Moderate","High","Extreme"],
            ["Low","Low","Moderate","High","High"],
        ]
        fill_map = {"Extreme":"C0392B","High":"E67E22","Moderate":"F1C40F","Low":"27AE60"}

        mx_tbl = doc.add_table(rows=len(likelihoods)+1, cols=len(consequences_short)+1)
        mx_tbl.style = 'Table Grid'

        # Header row
        mx_tbl.rows[0].cells[0].paragraphs[0].clear()
        set_cell_bg(mx_tbl.rows[0].cells[0], GREY_DARK.lstrip("#"))
        add_run(mx_tbl.rows[0].cells[0].paragraphs[0], "Likelihood \\ Consequences", bold=True, size=14, color="FFFFFF")
        for ci, c_label in enumerate(consequences_short):
            c = mx_tbl.rows[0].cells[ci+1]
            set_cell_bg(c, GREY_DARK.lstrip("#"))
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_run(p, c_label, bold=True, size=14, color="FFFFFF")

        for ri, (like, row_data) in enumerate(zip(likelihoods, matrix_data)):
            row = mx_tbl.rows[ri+1]
            c0 = row.cells[0]
            set_cell_bg(c0, "F2F6F6")
            p = c0.paragraphs[0]
            add_run(p, like, bold=True, size=14, color=GREY_DARK.lstrip("#"))
            for ci, val in enumerate(row_data):
                c = row.cells[ci+1]
                fhex = fill_map.get(val, "888888")
                set_cell_bg(c, fhex)
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                text_col = "FFFFFF" if val != "Moderate" else "333333"
                add_run(p, val, bold=True, size=14, color=text_col)

        doc.add_paragraph()

        # Legend
        legend_heading = doc.add_paragraph()
        add_run(legend_heading, "NOTES ON ANALYSING RISKS", bold=True, size=18, color=GREY_DARK.lstrip("#"))

        legend_data = [
            ("E – Almost Certain", "5 – Catastrophic: Serious injury or near-miss; severe incident (weapon, suicidal ideation); major behaviour continuing over significant period."),
            ("D – Likely/Frequently", "4 – Major: Injury or near-miss; distress to others; ED155/ED165 and critical incident report; violence (>1 incident)."),
            ("C – Likely Sometimes", "3 – Moderate: Regional support and cross-agency involvement; incident reports; repeated suspension/take home; complex welfare/health."),
            ("B – Unlikely", "2 – Minor: Impact on learning; staff team approach required; referral suggested; frequent repeats and take-home suspensions."),
            ("A – Rare", "1 – Insignificant: Behaviour managed within program; discussion with line manager; review at team meeting."),
        ]
        leg_tbl = doc.add_table(rows=len(legend_data)+1, cols=2)
        leg_tbl.style = 'Table Grid'
        for ci, lbl in enumerate(["Likelihood", "Consequences"]):
            c = leg_tbl.rows[0].cells[ci]
            set_cell_bg(c, GREY_DARK.lstrip("#"))
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_run(p, lbl, bold=True, size=16, color="FFFFFF")
        for ri, (like, cons) in enumerate(legend_data):
            c0 = leg_tbl.rows[ri+1].cells[0]
            c1 = leg_tbl.rows[ri+1].cells[1]
            set_cell_bg(c0, "F2F6F6")
            add_run(c0.paragraphs[0], like, bold=True, size=15, color=GREY_DARK.lstrip("#"))
            add_run(c1.paragraphs[0], cons, size=15)

        # ── Save to buffer ───────────────────────────────────────────────
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

    # ── Download ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="card-teal">
    ✅ <strong>Plan generated successfully!</strong><br>
    Your Safety &amp; Risk Management Plan for <strong>{student['name']}</strong> is ready to download.
    The document includes {len([r for r in risks if r['issue_title'].strip()])} risk row(s), priority actions, and the full risk rating matrix.
    </div>
    """, unsafe_allow_html=True)

    safe_name = student['name'].replace(" ", "_").replace("/","")
    filename = f"Safety_Risk_Plan_{safe_name}_CLC_{student['plan_date'].replace('/','')}.docx"

    st.download_button(
        label="⬇️  Download Safety & Risk Plan (.docx)",
        data=buf,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Back to Review", use_container_width=True):
            st.session_state.step = 4; st.rerun()
    with col_b:
        if st.button("🔄 Start a new plan", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
