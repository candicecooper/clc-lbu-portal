"""
Behaviour Data & Support Tools — Decision Flow guide.

Interactive companion to CLC-LBU_Behaviour_Data_Flow.docx (printable version).
Read-only reference page — no Supabase storage, no auth required (matches the
open-access pattern used by other guide/reference pages such as
57_abch_process_guide.py).

TODO before deploying — confirm and update:
  - COMM_LOG_URL, SENSORY_URL, SAFETY_PLAN_URL, SCATTER_URL, INTERVAL_URL
  - CI_THRESHOLD_TEXT (currently "two or more CIs for the same student within a term")
"""

import streamlit as st

st.set_page_config(page_title="Behaviour Data Flow Guide", layout="centered")

# ---- confirmed tool URLs -----------------------------------------------
QUICK_LOG_URL = "https://clc-lbu-portal.onrender.com/Behaviour_Support?mode=quicklog"
ABCH_FORMATTER_URL = "https://clc-lbu-portal.onrender.com/abch_report_formatter"
BEHAVIOUR_ANALYSIS_URL = "https://clc-lbu-portal.onrender.com/Behaviour_Support"

# ---- TODO: confirm these and replace the placeholders ------------------
COMM_LOG_URL = "https://clc-lbu-portal.onrender.com/Communication_Log"          # confirm
SENSORY_URL = "https://clc-lbu-portal.onrender.com/Behaviour_Support"            # confirm — sensory overview tab
SAFETY_PLAN_URL = "https://clc-lbu-portal.onrender.com/Safety_Risk_Plan"         # confirm
SCATTER_URL = "https://clc-lbu-portal.onrender.com/Scatter_Plot_Tracker"         # confirm
INTERVAL_URL = "https://clc-lbu-portal.onrender.com/Interval_Support_Tracker"    # confirm

CI_THRESHOLD_TEXT = "two or more CIs for the same student within a term"  # confirm exact figure

st.markdown("""
<style>
.flow-box {
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 6px;
    text-align: center;
    border: 1.5px solid;
}
.flow-title { font-weight: 600; font-size: 16px; margin-bottom: 2px; }
.flow-sub { font-size: 13px; font-style: italic; }
.box-gray  { background:#E9E7E0; border-color:#888780; color:#2C2C2A; }
.box-teal  { background:#D9F0E5; border-color:#0F6E56; color:#04342C; }
.box-coral { background:#FAE3D9; border-color:#D85A30; color:#4A1B0C; }
.box-blue  { background:#DCEBFB; border-color:#185FA5; color:#042C53; }
.arrow { text-align:center; color:#888780; font-size:20px; margin:2px 0 6px 0; }
.legend-chip { display:inline-block; padding:3px 10px; border-radius:12px; font-size:12px; margin-right:6px; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

st.title("Behaviour Data & Support Tools")
st.caption("Decision flow — which tool, and when. Companion to the printable flow chart.")

st.markdown(
    '<span class="legend-chip box-gray">Start</span>'
    '<span class="legend-chip box-teal">Day-to-day data recording</span>'
    '<span class="legend-chip box-coral">Threshold-triggered response</span>'
    '<span class="legend-chip box-blue">Cross-cutting communication</span>',
    unsafe_allow_html=True,
)

st.markdown('<div class="flow-box box-gray"><div class="flow-title">Behaviour incident occurs</div></div>', unsafe_allow_html=True)
st.markdown('<div class="arrow">&#9660;</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        '<div class="flow-box box-teal"><div class="flow-title">Minor behaviour incident</div>'
        '<div class="flow-sub">Quick Incident Log</div></div>', unsafe_allow_html=True,
    )
    st.link_button("Open Quick Incident Log", QUICK_LOG_URL, use_container_width=True)
with col2:
    st.markdown(
        '<div class="flow-box box-coral"><div class="flow-title">Critical incident (ABCH)</div>'
        '<div class="flow-sub">C.I. Bot preferred, or Word template</div></div>', unsafe_allow_html=True,
    )
    st.link_button("Open ABCH Report Formatter", ABCH_FORMATTER_URL, use_container_width=True)
    # Arrow only under this column — Communication Log follows from Critical
    # incidents; Minor incidents get no arrow into it.
    st.markdown('<div class="arrow">&#9660;</div>', unsafe_allow_html=True)

st.caption("Both paths also require Historical Entry into Behaviour Analysis.")
st.link_button("Open Behaviour Analysis (Historical Entry)", BEHAVIOUR_ANALYSIS_URL, use_container_width=True)

st.markdown(
    '<div class="flow-box box-blue"><div class="flow-title">Communication log</div>'
    '<div class="flow-sub">Record contact whenever parent/carer or agency is contacted</div></div>',
    unsafe_allow_html=True,
)
st.link_button("Open Communication Log", COMM_LOG_URL, use_container_width=True)

st.divider()

# ---- Threshold-triggered specialist responses --------------------------
st.subheader(":orange[Threshold-triggered responses]")
st.write("Triggered by a pattern building up across incidents over time — not a direct next step off one single incident.")

with st.expander("Sensory profile — indicators", expanded=False):
    st.markdown(
        "- Same sensory trigger recurring across incident reports (noise, crowding, touch, texture, lighting, transitions)\n"
        "- Repeated seeking or avoidance behaviour noted across several incidents, not a one-off\n"
        "- New enrolment or transition with no sensory profile on file yet\n"
        "- Behaviour Analysis data suggests an environmental/sensory correlation rather than social demand or task avoidance"
    )
    st.link_button("Open sensory overview", SENSORY_URL)

with st.expander("Safety and risk plan — indicators", expanded=False):
    st.markdown(
        "- A critical incident involving risk to the student or others (absconding/elopement, physical aggression, "
        "self-harm, property destruction with safety implications)\n"
        f"- Frequency escalation — {CI_THRESHOLD_TEXT}\n"
        "- A recurring high-risk behaviour type across multiple reports, even where no single incident was severe alone\n"
        "- Manager/TC review of a CI explicitly flags ongoing risk requiring a proactive plan"
    )
    st.link_button("Open Safety and Risk Plan Builder", SAFETY_PLAN_URL)

st.divider()

# ---- Ongoing data collection tools --------------------------------------
st.subheader(":green[Ongoing data collection tools]")
st.write("Used continuously to build the pattern picture, independent of whether a CI has occurred.")

with st.expander("Scatter plot tracker — when to use", expanded=False):
    st.markdown(
        "- Establishing whether a behaviour has a time/day pattern, before committing to anything more structured\n"
        "- One target behaviour, light-touch, paper-style weekly recording"
    )
    st.link_button("Open Scatter Plot Tracker", SCATTER_URL)

with st.expander("Interval tracker — when to use", expanded=False):
    st.markdown(
        "- A support plan is already in place and structured, more granular sampling is needed (Quick or Grid mode)\n"
        "- Recording prevention \"saves\" — evidence a strategy is working, not just when it fails"
    )
    st.link_button("Open Interval Tracker", INTERVAL_URL)

st.divider()
st.caption(
    "Assumptions in this version: CI frequency threshold shown as \u201c" + CI_THRESHOLD_TEXT +
    "\u201d — confirm and adjust if a different figure applies. Several tool links above are placeholders "
    "pending confirmed portal URLs (see TODO at the top of this file)."
)
