# =============================================================================
# 23_Professional_Language_Converter.py  -  CLC-LBU Portal
# Convert informal behaviour / strategy descriptions into professional,
# trauma-informed, BSEM-aligned documentation language using Groq AI.
# =============================================================================

import streamlit as st
from groq import Groq

st.set_page_config(
    page_title="Professional Language Converter - CLC",
    page_icon="✍️",
    layout="wide",
)

# -- Brand colours ------------------------------------------------------------
TEAL   = "#1A7A7A"
TEAL_L = "#e6f4f4"
TEAL_D = "#115555"
AMBER  = "#C8760A"
AMB_B  = "#fef3e2"
CREAM  = "#F7F9FB"

# -- CSS ----------------------------------------------------------------------
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:{CREAM}; }}

.plc-header {{
    background:linear-gradient(135deg,{TEAL} 0%,{TEAL_D} 100%);
    color:#fff; padding:1rem 1.5rem; border-radius:12px;
    margin-bottom:1.5rem; display:flex; align-items:center; gap:1rem;
}}
.plc-header .icon {{ font-size:2.2rem; }}
.plc-header h1 {{ margin:0; font-size:1.35rem; font-weight:800; }}
.plc-header p  {{ margin:.1rem 0 0; opacity:.8; font-size:.82rem; }}

.framework-bar {{
    display:flex; flex-wrap:wrap; gap:.4rem; margin-bottom:1.25rem;
}}
.fw-badge {{
    padding:.2rem .65rem; border-radius:20px; font-size:.72rem;
    font-weight:700; letter-spacing:.3px;
}}
.fw-bsem   {{ background:#dbeafe; color:#1e40af; }}
.fw-ti     {{ background:#dcfce7; color:#166534; }}
.fw-pbis   {{ background:#fef3c7; color:#92400e; }}
.fw-ba     {{ background:#ede9fe; color:#5b21b6; }}
.fw-smart  {{ background:#fce7f3; color:#9d174d; }}

.section-card {{
    background:#fff; border-radius:12px; border:1px solid #dde6ee;
    padding:1.1rem 1.3rem; margin-bottom:1rem;
    box-shadow:0 2px 8px rgba(0,0,0,.05);
}}
.section-card h3 {{
    margin:0 0 .75rem; font-size:1rem; font-weight:800; color:{TEAL};
}}

.output-box {{
    background:{TEAL_L}; border:1px solid {TEAL}; border-radius:10px;
    padding:1rem 1.25rem; white-space:pre-wrap; font-size:.9rem;
    line-height:1.75; color:#1c2320;
}}

.amber-note {{
    background:{AMB_B}; border:1px solid {AMBER}; border-radius:8px;
    padding:.55rem .9rem; font-size:.78rem; color:#7a4a08;
    margin-bottom:1rem;
}}
</style>
""", unsafe_allow_html=True)

# -- Header -------------------------------------------------------------------
st.markdown("""
<div class="plc-header">
  <div class="icon">✍️</div>
  <div>
    <h1>Professional Language Converter</h1>
    <p>Describe student behaviour or a support strategy in plain language — AI rewrites it for professional documentation</p>
  </div>
</div>
""", unsafe_allow_html=True)

# -- Framework badges ---------------------------------------------------------
st.markdown("""
<div class="framework-bar">
  <span class="fw-badge fw-bsem">Berry Street Education Model</span>
  <span class="fw-badge fw-ti">Trauma-Informed Practice</span>
  <span class="fw-badge fw-pbis">PBIS</span>
  <span class="fw-badge fw-ba">Behaviour Analysis</span>
  <span class="fw-badge fw-smart">SMARTAR</span>
</div>
""", unsafe_allow_html=True)

# -- Shared context prompt (injected into both calls) -------------------------
SHARED_CONTEXT = """You are a professional education support writer for an Australian alternative education setting (Cowandilla Learning Centre — Learning and Behaviour Unit). You work with students who have experienced trauma, disengagement, and exclusion from mainstream schooling. Staff will describe student behaviour and support strategies in informal plain language. Your job is to rewrite these descriptions in professional, appropriate, and clinically informed language.

Your writing must be grounded in the following frameworks — weave their language, concepts, and rationale naturally through all descriptions:

BERRY STREET EDUCATION MODEL (BSEM): Reference the five BSEM domains where relevant: Regulation, Relationships, Resilience, Engagement, and Character. Frame behaviour through the lens of stress response, trauma history, and unmet needs rather than defiance or non-compliance. Use BSEM language: regulation, co-regulation, felt safety, relational trust, restorative practice, proactive strategies, the stress-behaviour-learning connection. Describe student strengths as assets within the BSEM framework.

TRAUMA-INFORMED PRACTICE: Apply the core principles: safety, trustworthiness, choice, collaboration, empowerment. Frame escalating behaviour as a stress response, not a character flaw or deliberate disruption. Reference the Regulate-Relate-Reason sequence where appropriate. Describe all adult responses as intentional, co-regulatory, and proactive.

PBIS: Frame strategies within a tiered support model where appropriate. Use PBIS language: clearly defined expectations, positive reinforcement, consistent prompting, data-informed decision-making, least restrictive response, planned consequences. Refer to consequences as planned, non-punitive responses designed to teach, not punish.

BEHAVIOUR ANALYSIS: Describe behaviour in terms of its function where possible: sensory, escape/avoidance, attention-seeking, access to activities. Use ABC framing where relevant. Describe strategies in terms of antecedent modifications and teaching replacement behaviours.

SMARTAR: Where strategies or goals are described, frame them in measurable, time-bound, reviewable language.

In all writing: use person-first, strengths-based language. Avoid deficit or punitive framing. Do not invent clinical labels not mentioned. Use Australian English spelling. Refer to the student as "the student" or "they", not by name."""

SYSTEM_STANDARD = SHARED_CONTEXT + """

Write a STANDARD VERSION only — professional language suitable for team meetings, parent communication, or general documentation. Clear, accessible prose. Use bullet points where describing a multi-step strategy. Keep it concise and practical. Do not include headings or labels — just write the description directly."""

SYSTEM_FORMAL = SHARED_CONTEXT + """

Write a FORMAL VERSION only — clinical and structured language suitable for official documentation, DfE records, Individual Education Plans, or Behaviour Support Plans. Use the frameworks above more explicitly and precisely. More formal in tone and structure. Do not include headings or labels — just write the description directly."""

# -- Prompt starters ----------------------------------------------------------
STARTERS = {
    "Describe the student's behaviour": "The student's behaviour includes: ",
    "Explain your support strategy": "The strategy I use to support this student is: ",
    "Describe the student's strengths": "This student's strengths include: ",
    "Describe triggers / antecedents": "Before the behaviour occurs, I usually notice: ",
    "Describe peer interactions": "When interacting with peers, this student: ",
    "Explain a consequence / response": "When the behaviour occurs, our response is: ",
    "Describe self-regulation": "This student's ability to self-regulate looks like: ",
    "Explain communication style": "This student communicates by: ",
    "Describe sensory needs": "This student's sensory needs and responses include: ",
    "Describe transitions / routine": "During transitions or changes in routine, this student: ",
}

# -- Session state ------------------------------------------------------------
if "plc_input" not in st.session_state:
    st.session_state.plc_input = ""
if "plc_standard" not in st.session_state:
    st.session_state.plc_standard = ""
if "plc_formal" not in st.session_state:
    st.session_state.plc_formal = ""

# -- Input section ------------------------------------------------------------
with st.container():
    st.markdown('<div class="section-card"><h3>Prompt starters</h3>', unsafe_allow_html=True)
    cols = st.columns(5)
    for i, (label, prefix) in enumerate(STARTERS.items()):
        col = cols[i % 5]
        with col:
            if st.button(label, key=f"starter_{i}", use_container_width=True):
                st.session_state.plc_input = prefix
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card"><h3>Your description</h3>', unsafe_allow_html=True)
user_input = st.text_area(
    label="Description",
    value=st.session_state.plc_input,
    height=200,
    placeholder="Type your description here, or tap a prompt starter above to begin...",
    label_visibility="collapsed",
    key="plc_textarea",
)
st.caption(f"{len(user_input)} characters — write as you normally would, no need for formal language.")
st.markdown("</div>", unsafe_allow_html=True)

col_btn, col_clear, _ = st.columns([2, 1, 4])
with col_btn:
    convert = st.button("✍️ Convert to professional language", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear", use_container_width=True):
        st.session_state.plc_input = ""
        st.session_state.plc_standard = ""
        st.session_state.plc_formal = ""
        st.rerun()

# -- Conversion — two separate calls, each under 800 tokens ------------------
def call_groq(system_prompt, user_text):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        max_tokens=800,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )
    return (response.choices[0].message.content or "").strip()

if convert:
    if not user_input.strip():
        st.warning("Please enter a description first.")
    else:
        text = user_input.strip()
        error = None
        standard = ""
        formal = ""

        with st.spinner("Generating standard version..."):
            try:
                standard = call_groq(SYSTEM_STANDARD, text)
            except Exception as e:
                error = str(e)

        if not error:
            with st.spinner("Generating formal version..."):
                try:
                    formal = call_groq(SYSTEM_FORMAL, text)
                except Exception as e:
                    error = str(e)

        if error:
            st.error(f"Something went wrong: {error}")
        else:
            st.session_state.plc_standard = standard
            st.session_state.plc_formal = formal

# -- Output -------------------------------------------------------------------
if st.session_state.plc_standard:
    st.markdown("---")
    st.markdown(f"""
    <div class="amber-note">
      ⚠️ AI-generated output — review before use in official documentation.
      Ensure accuracy reflects your knowledge of the student.
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📄 Standard version", "📋 Formal / documentation"])

    with tab1:
        st.markdown('<div class="section-card"><h3>Standard version</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="output-box">{st.session_state.plc_standard}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ Download standard version",
            data=st.session_state.plc_standard,
            file_name="professional_description_standard.txt",
            mime="text/plain",
            key="dl_standard",
        )

    with tab2:
        st.markdown('<div class="section-card"><h3>Formal / documentation version</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="output-box">{st.session_state.plc_formal}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ Download formal version",
            data=st.session_state.plc_formal,
            file_name="professional_description_formal.txt",
            mime="text/plain",
            key="dl_formal",
        )
