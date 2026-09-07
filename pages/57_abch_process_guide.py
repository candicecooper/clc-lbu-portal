
"""
57_abch_process_guide.py

Interactive walkthrough of the CLC-LBU Behaviour Incident Reporting Procedure.
Turns the flow-chart procedure document into a clickable hub: each stage links
straight out to the tool that handles it (C.I. Bot, blank ABCH form download,
ABCH Report Formatter, Teams channel), or across to the Behaviour Support Tool
for the Quick Incident Log / direct entry / Historical Entry routes.

WIRING NOTES (please check these before deploying):
- PAGE PATHS: st.page_link() needs the real relative path to each page file in
  this repo's `pages/` folder. I've guessed the two page-internal targets below
  from what's on file (5_Behaviour_Support.py, 51_abch_report_formatter.py) —
  update BEHAVIOUR_SUPPORT_PAGE / FORMATTER_PAGE if your filenames differ.
- ASSET: CLC_ABC-H_Blank_Template.docx should sit alongside this file (or update
  BLANK_TEMPLATE_PATH) so the download button can read it.
- AUTH: wrapped with the shared staff_auth module, matching other staff-level
  tools in the portal. Swap/remove if this page should be open access instead.
- EdChat link: the URL already has the join code embedded (?c=...), so clicking
  it should not prompt staff to type a code manually. Any further login prompt
  staff see is EdChat/DfE's own authentication, not something this portal
  controls.
"""

import streamlit as st
from pathlib import Path

from staff_auth import require_staff_auth, staff_logout_button

st.set_page_config(page_title="ABCH Process Guide", page_icon="\U0001F4CB", layout="wide")

require_staff_auth()

# ---------------------------------------------------------------------------
# Config — check these against your actual repo structure before deploying
# ---------------------------------------------------------------------------
CI_BOT_URL = "https://edchat.sa.edu.au/join?c=S20OS4"
TEAMS_ABCH_URL = (
    "https://teams.microsoft.com/l/channel/19%3Ace8c1831b7444ddfa4f0624f8734f0af%40thread.tacv2/"
    "ABC-H%20documents?groupId=30474510-1e28-4896-9e8a-280df15e6337&tenantId=73bbf4e9-0688-4946-aea9-bd0bb40ecf07"
)
BEHAVIOUR_SUPPORT_PAGE = "pages/5_Behaviour_Support.py"  # Quick Incident Log + direct Behaviour Analysis entry + Historical Entry
FORMATTER_PAGE = "pages/51_abch_report_formatter.py"     # ABCH Report Formatter
BLANK_TEMPLATE_PATH = Path(__file__).parent / "CLC_ABC-H_Blank_Template.docx"

# ---------------------------------------------------------------------------
# Palette — matches the CLC-LBU Behaviour Incident Reporting Procedure document
# ---------------------------------------------------------------------------
COLORS = {
    "grey":   {"fill": "#E7E7E7", "border": "#6B7280", "text": "#374151"},
    "coral":  {"fill": "#FCE3D6", "border": "#C2410C", "text": "#9A3412"},
    "teal":   {"fill": "#D7F0EC", "border": "#0F766E", "text": "#0B5A54"},
    "purple": {"fill": "#EDE4FB", "border": "#6B46A6", "text": "#4C2E8C"},
    "blue":   {"fill": "#DCEAFB", "border": "#1D4ED8", "text": "#1E40AF"},
    "amber":  {"fill": "#FDEDC8", "border": "#B45309", "text": "#92400E"},
}


def step_card(title, subtitle, palette_key, key=None, dashed=False):
    """Render one flow-chart-style step box."""
    p = COLORS[palette_key]
    border_style = "dashed" if dashed else "solid"
    st.markdown(
        f"""
        <div style="
            background:{p['fill']};
            border:2px {border_style} {p['border']};
            border-radius:8px;
            padding:14px 18px;
            margin-bottom:8px;
            text-align:center;
        ">
            <div style="font-weight:700; color:{p['text']}; font-size:1.02rem;">{title}</div>
            <div style="font-style:italic; color:{p['text']}; font-size:0.85rem; margin-top:2px;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def arrow(label=None):
    st.markdown(
        f"""
        <div style="text-align:center; color:#6B7280; margin:2px 0 8px 0;">
            <div style="font-size:1.3rem; line-height:1;">&#8595;</div>
            {f'<div style="font-size:0.8rem; font-style:italic;">{label}</div>' if label else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("ABCH / Critical Incident Reporting — Process Guide")
st.caption("Follow the flow below. Every stage links straight to the tool or channel you need for that step.")
staff_logout_button()

st.divider()

# ---------------------------------------------------------------------------
# Stage 1 — start
# ---------------------------------------------------------------------------
step_card("Student allocated & entered on the portal / Behaviour Analysis tool", "Admin", "grey")
arrow()
step_card("Behaviour incident occurs", "Staff", "coral")
arrow("What kind of incident is it?")

col1, col2 = st.columns(2)
with col1:
    step_card("Minor / routine", "Quick Incident Log — completed directly in the portal", "grey")
    st.page_link(BEHAVIOUR_SUPPORT_PAGE, label="Open Quick Incident Log \u2192", icon="\U0001F4DD")
with col2:
    step_card("ABCH / Critical Incident", "continues below", "coral")

st.divider()

# ---------------------------------------------------------------------------
# Stage 2 — choose method
# ---------------------------------------------------------------------------
st.subheader("Choose how to complete the ABCH / Critical Incident report")

m1, m2, m3 = st.columns(3)
with m1:
    step_card("C.I. Bot", "EdChat chatbot \u00b7 preferred", "teal")
    st.link_button("Open the C.I. Bot \u2192", CI_BOT_URL, use_container_width=True)
    st.caption("Link already includes the join code — you shouldn't need to type it in.")
with m2:
    step_card("Word template", "completed by Staff", "coral")
    if BLANK_TEMPLATE_PATH.exists():
        st.download_button(
            "Download blank ABC-H form \u2192",
            data=BLANK_TEMPLATE_PATH.read_bytes(),
            file_name="CLC_ABC-H_Blank_Template.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    else:
        st.warning("Blank template file not found next to this page — check BLANK_TEMPLATE_PATH.")
with m3:
    step_card("Behaviour Analysis tool", "direct entry \u00b7 not preferred currently", "grey", dashed=True)
    st.page_link(BEHAVIOUR_SUPPORT_PAGE, label="Open Behaviour Analysis tool \u2192", icon="\u26A0\uFE0F")

arrow()
step_card(
    "If using the C.I. Bot: drop the completed text into the ABCH Report Formatter",
    "Save and edit the formatted report as needed \u00b7 Staff",
    "teal",
)
st.page_link(FORMATTER_PAGE, label="Open ABCH Report Formatter \u2192", icon="\U0001F4C4")
arrow("Both the C.I. Bot and Word template paths converge here")

st.divider()

# ---------------------------------------------------------------------------
# Stage 3 — Teams + Historical Entry (parallel)
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    step_card("Add / attach the report to the Teams ABCH link", "@Manager and @TC tagged \u00b7 Staff", "blue")
    st.link_button("Open Teams ABCH channel \u2192", TEAMS_ABCH_URL, use_container_width=True)
with c2:
    step_card(
        "\u26A0 Also upload to the Behaviour Analysis tool",
        "via Historical Entry, in the Analysis section \u00b7 Staff \u00b7 commonly missed step",
        "amber",
    )
    st.page_link(BEHAVIOUR_SUPPORT_PAGE, label="Go to Historical Entry \u2192", icon="\U0001F4C5")

arrow()
step_card("Manager and TC alerted via Teams \u2014 review the report", "Manager \u00b7 Transition Coordinator (TC)", "purple")
arrow()
step_card("Report entered on IRMS", "@Admin", "teal")
arrow()
step_card("Printed and signed", "Admin", "teal")
arrow()
step_card("IRMS actioned and signed copy filed in OneDrive", "Admin \u00b7 end of process", "grey")

st.divider()

# ---------------------------------------------------------------------------
# Reference material
# ---------------------------------------------------------------------------
with st.expander("Role quick reference"):
    st.markdown(
        """
        **Staff**
        - Log minor incidents directly with the Quick Incident Log
        - Complete ABCH / Critical Incident reports via the C.I. Bot (preferred) or the Word template
        - If using the C.I. Bot: drop the text into the ABCH Report Formatter, then save/edit as needed
        - Add the finished report to the Teams ABCH link and tag @Manager and @TC
        - Also upload the report to the Behaviour Analysis tool via Historical Entry — this step is often missed

        **Manager & TC**
        - Alerted via the Teams ABCH link
        - Review the report

        **Admin**
        - Enter the reviewed report on IRMS
        - Print and sign
        - Action IRMS and file the signed copy in OneDrive
        """
    )

with st.expander("Notes"):
    st.markdown(
        """
        Direct entry through the Behaviour Analysis tool is not the preferred method at this time —
        staff should use the C.I. Bot or the Word template instead.

        Regardless of which platform is used to complete the ABCH report (C.I. Bot or Word template),
        staff still need to separately upload the report to the Behaviour Analysis tool through
        Historical Entry in the Analysis section. This step is currently the one most often missed.
        """
    )
