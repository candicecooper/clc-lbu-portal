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

/* Style containers as cards */
.element-container:has(> .section-card) {{
    margin-bottom: 1rem;
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

# -- System prompt ------------------------------------------------------------
SYSTEM_PROMPT = """You are a professional education support writer for an Australian alternative education setting (Cowandilla Learning Centre — Learning and Behaviour Unit). You work with students who have experienced trauma, disengagement, and exclusion from mainstream schooling. Staff will describe student behaviour and support strategies in informal plain language. Your job is to rewrite these descriptions in professional, appropriate, and clinically informed language.

Your writing must be grounded in the following frameworks — weave their language, concepts, and rationale naturally through all descriptions:

BERRY STREET EDUCATION MODEL (BSEM):
- Reference the five BSEM domains where relevant: Regulation, Relationships, Resilience, Engagement, and Character.
- Frame behaviour through the lens of stress response, trauma history, and unmet needs rather than defiance or non-compliance.
- Use BSEM language: regulation, co-regulation, felt safety, relational trust, restorative practice, proactive strategies, the stress-behaviour-learning connection.
- Describe student strengths as assets within the BSEM framework (e.g. relational motivation, desire for connection, emerging capacity for reflection).

TRAUMA-INFORMED PRACTICE:
- Apply the core principles: safety, trustworthiness, choice, collaboration, empowerment, cultural sensitivity.
- Frame escalating behaviour as a stress response, not a character flaw or deliberate disruption.
- Reference the Regulate–Relate–Reason sequence where appropriate (a student must be regulated before they can access reasoning or learning).
- Where relevant, reference the Window of Tolerance, neuroception, and the role of predictability and routine in felt safety.
- Describe all adult responses as intentional, co-regulatory, and proactive.

PBIS (POSITIVE BEHAVIOURAL INTERVENTIONS AND SUPPORTS):
- Frame strategies within a tiered support model where appropriate (Tier 1 universal, Tier 2 targeted, Tier 3 intensive).
- Use PBIS language: clearly defined expectations, positive reinforcement, consistent prompting, data-informed decision-making, least restrictive response, planned consequences.
- Describe visual systems, prompts, and structured consequences using PBIS framing — as proactive tools that increase predictability and reduce ambiguity for the student.
- Refer to consequences as planned, non-punitive responses designed to teach, not punish.

BEHAVIOUR ANALYSIS (Applied Behaviour Analysis / Functional Behaviour Assessment):
- Describe behaviour in terms of its function where possible: sensory, escape/avoidance, attention-seeking, access to tangibles/activities.
- Use antecedent-behaviour-consequence (ABC) framing where relevant.
- Identify the likely communicative function of the behaviour (e.g. "the behaviour appears to serve a function of seeking social connection and sensory stimulation").
- Describe strategies in terms of antecedent modifications, teaching replacement behaviours, and consequence strategies.
- Reference reinforcement, extinction, prompting hierarchies, and generalisation where applicable.

SMART / SMARTAR GOALS:
- Where strategies or goals are described, frame them as Specific, Measurable, Achievable, Relevant, and Time-bound.
- Where the description includes targets or outcomes, reframe these in SMARTAR language.
- Reference data collection, progress monitoring, and review cycles where relevant.

Always produce TWO versions:
1. STANDARD VERSION — professional language for team meetings, parent communication, or general documentation. Clear and accessible. Uses bullet points where describing a multi-step strategy. Label this section clearly with: --- STANDARD VERSION ---
2. FORMAL VERSION — more clinical and structured, suitable for official documentation, DfE records, Individual Education Plans, or Behaviour Support Plans. Uses the frameworks above more explicitly. Label this section clearly with: --- FORMAL VERSION ---

In BOTH versions:
- Use person-first, strengths-based language throughout
- Reflect the student's motivation, relational capacity, and strengths alongside their challenges
- Avoid deficit, pathologising, or punitive framing
- Do not invent clinical diagnoses or labels not mentioned by the staff member
- Use Australian English spelling (e.g. behaviour, organisation, recognise, programme)
- Do not use the student's name — refer to "the student" or "they"
- Keep content accurate to what was described — expand the professional framing but do not fabricate details"""

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

# -- Input section: Prompt starters -------------------------------------------
st.markdown("""
<div class="section-card">
  <h3>Prompt starters</h3>
</div>
""", unsafe_allow_html=True)

cols = st.columns(5)
for i, (label, prefix) in enumerate(STARTERS.items()):
    col = cols[i % 5]
    with col:
        if st.button(label, key=f"starter_{i}", use_container_width=True):
            st.session_state.plc_input = prefix
            st.rerun()

# -- Input section: Your description ------------------------------------------
st.markdown("""
<div class="section-card">
  <h3>Your description</h3>
</div>
""", unsafe_allow_html=True)

user_input = st.text_area(
    label="Description",
    value=st.session_state.plc_input,
    height=200,
    placeholder="Type your description here, or tap a prompt starter above to begin...",
    label_visibility="collapsed",
    key="plc_textarea",
)
st.caption(f"{len(user_input)} characters — write as you normally would, no need for formal language.")

col_btn, col_clear, _ = st.columns([2, 1, 4])
with col_btn:
    convert = st.button("✍️ Convert to professional language", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear", use_container_width=True):
        st.session_state.plc_input = ""
        st.session_state.plc_standard = ""
        st.session_state.plc_formal = ""
        st.rerun()

# -- Conversion ---------------------------------------------------------------
if convert:
    if not user_input.strip():
        st.warning("Please enter a description first.")
    else:
        with st.spinner("Converting — this may take a moment..."):
            try:
                client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=1800,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_input.strip()},
                    ],
                )
                raw = response.choices[0].message.content or ""

                # Split on section markers
                standard = ""
                formal = ""
                if "--- STANDARD VERSION ---" in raw and "--- FORMAL VERSION ---" in raw:
                    parts = raw.split("--- FORMAL VERSION ---")
                    standard = parts[0].replace("--- STANDARD VERSION ---", "").strip()
                    formal = parts[1].strip() if len(parts) > 1 else ""
                else:
                    # Fallback: put everything in standard
                    standard = raw.strip()
                    formal = ""

                st.session_state.plc_standard = standard
                st.session_state.plc_formal = formal

            except Exception as e:
                st.error(f"Something went wrong: {e}")

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
        st.markdown("""
        <div class="section-card">
          <h3>Standard version</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(
            f'<div class="output-box">{st.session_state.plc_standard}</div>',
            unsafe_allow_html=True,
        )
        
        st.download_button(
            label="⬇️ Download standard version",
            data=st.session_state.plc_standard,
            file_name="professional_description_standard.txt",
            mime="text/plain",
        )

    with tab2:
        if st.session_state.plc_formal:
            st.markdown("""
            <div class="section-card">
              <h3>Formal / documentation version</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(
                f'<div class="output-box">{st.session_state.plc_formal}</div>',
                unsafe_allow_html=True,
            )
            
            st.download_button(
                label="⬇️ Download formal version",
                data=st.session_state.plc_formal,
                file_name="professional_description_formal.txt",
                mime="text/plain",
            )
        else:
            st.info("Formal version not available for this output. Check the Standard version tab.")
