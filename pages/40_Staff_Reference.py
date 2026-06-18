"""
34_Staff_Reference.py
CLC-LBU Portal — Staff Reference

A hub page for internal, information-only references for staff.
Opens to a grid of reference cards. Selecting a card renders that
reference inline, with a Back button to return to the grid.

To add a new reference: add an entry to the REFERENCES list and write
its render function. Nothing else needs to change.
"""

import streamlit as st
from auth import require_auth

st.set_page_config(page_title="Staff Reference | CLC-LBU", page_icon="📚", layout="wide")
require_auth()

# ──────────────────────────────────────────────────────────────────────────
# Branding / styling
# ──────────────────────────────────────────────────────────────────────────
TEAL = "#1b7f79"
TEAL_DARK = "#125c57"
GREEN_SOFT = "#e8f4f2"

st.markdown(f"""
<style>
  .sr-header {{
      background: linear-gradient(135deg, {TEAL} 0%, {TEAL_DARK} 100%);
      color: #ffffff; padding: 1.4rem 1.6rem; border-radius: 14px;
      margin-bottom: 1.4rem;
  }}
  .sr-header h1 {{ margin: 0; font-size: 1.7rem; color:#fff; }}
  .sr-header p  {{ margin: .35rem 0 0; opacity: .92; font-size: .98rem; }}

  .sr-card {{
      border: 1px solid #d9e6e4; border-left: 6px solid {TEAL};
      border-radius: 12px; padding: 1.1rem 1.2rem; background: #fff;
      height: 100%;
  }}
  .sr-card h3 {{ margin: .1rem 0 .4rem; color: {TEAL_DARK}; font-size: 1.12rem; }}
  .sr-card p  {{ margin: 0; color: #4a5b59; font-size: .92rem; line-height: 1.4; }}
  .sr-icon    {{ font-size: 1.6rem; }}

  .sr-section {{
      background: {GREEN_SOFT}; border-radius: 10px;
      padding: .9rem 1.1rem; margin: .6rem 0 1.1rem;
  }}
  .sr-section h4 {{ margin: 0; color: {TEAL_DARK}; }}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# Navigation state
# ──────────────────────────────────────────────────────────────────────────
if "sr_open" not in st.session_state:
    st.session_state.sr_open = None


# ══════════════════════════════════════════════════════════════════════════
# REFERENCE CONTENT
# ══════════════════════════════════════════════════════════════════════════
def render_case_management():
    st.markdown(
        '<div class="sr-section"><h4>Teacher Case Management Process</h4>'
        '<p style="margin:.3rem 0 0;color:#4a5b59;">How to case manage a student '
        'placement from before they arrive through to archiving the file.</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown("""
As the allocated program teacher, **you are the case manager** for that student
for the length of their placement. That means working through the student file in
order — from before the student arrives, through their review, transition and exit,
to archiving the file when they return to their home school.

The **Checklist** tab is your master to-do list. Everything below simply unpacks
what each item means and where to record it. Tick items off on the Checklist as
you complete them so anyone picking up the file can see at a glance where the
placement is up to.
""")

    # ---- Tab map -----------------------------------------------------------
    st.markdown("#### How the student file is organised")
    st.markdown("Each student's section contains the following pages. You move through "
                "them roughly top to bottom across the placement.")
    st.table({
        "Tab": [
            "Checklist", "Student Information", "SMARTAR Goals", "Scheduled Meetings",
            "Reporting", "Transition Plan", "Extension Requested",
        ],
        "What it is for": [
            "Your master sequence of tasks for the whole placement. Tick each item as it is done.",
            "The entry meeting record — who the student is, background, strengths, risks, supports and the first-week attendance timetable.",
            "The student's goals, teaching/intervention plan and resources. Where goals are amended and converted into the GAS.",
            "A tracker confirming the Review and Exit meetings are set, reminded and confirmed by everyone in the team.",
            "A tracker for the report-writing steps for both the Review Report and the Transition Report (draft, final, distribution).",
            "The weekly transition timetable agreed at the review meeting (which days/times the student attends as they move back to home school).",
            "The process and paperwork to follow only if the placement needs to continue beyond the original exclusion dates.",
        ],
    })

    # ---- Lifecycle at a glance --------------------------------------------
    st.markdown("#### The placement at a glance")
    st.markdown("The placement runs through seven phases. Detailed steps for each follow below.")
    st.table({
        "Phase": ["1", "2", "3", "4", "5", "6", "7"],
        "Stage": [
            "Before the student arrives",
            "Settling in & assessment",
            "Review meeting",
            "Transition",
            "Exit meeting",
            "Conclusion & EMS upload",
            "Archiving",
        ],
        "Main tabs in play": [
            "Student Information, SMARTAR Goals, Scheduled Meetings",
            "SMARTAR Goals",
            "Reporting, Scheduled Meetings, Transition Plan",
            "Transition Plan",
            "Reporting, Scheduled Meetings",
            "Reporting",
            "Checklist",
        ],
    })

    # ---- Phase detail ------------------------------------------------------
    st.markdown("#### Phase-by-phase")

    with st.expander("Phase 1 — Before the student arrives", expanded=True):
        st.markdown("""
- Read the **Student Information** and the **Original SMARTAR Goals** (developed by the TC in the SMARTAR Goal Builder) so you know the student before day one.
- Prepare resources and set up the classroom for the student's arrival.
- Acknowledge the **start date**.
- Confirm the **Review Meeting** with the TAC (Team Around the Child).
""")

    with st.expander("Phase 2 — Settling in & assessment"):
        st.markdown("""
- Complete baseline assessments: **Sounds-Write**, **Word Aware**, and **Big Ideas in Number**.
- Meet with **Leadership** to amend the SMARTAR Goals — do this in the SMARTAR Goal Builder, then copy the updated goals back into the student file.
- Convert the SMARTAR Goal into the **GAS** (Goal Attainment Scale) using the SMARTAR Goal Builder.
""")

    with st.expander("Phase 3 — Review meeting"):
        st.markdown("""
- Follow the **Review Report** process: send the **draft** to Leadership first, then **print** the final to hand out at the meeting.
- Hold the **Review Meeting**. At this meeting you:
  - share the report,
  - schedule the **Exit Meeting**,
  - develop and share the **transition timetable**,
  - clarify the **extension process** (in case the placement needs to continue — see the branch below).
""")

    with st.expander("Phase 4 — Transition"):
        st.markdown("""
- Distribute the **electronic Transition Timetable** to the **TAC** via email.
- Distribute the **electronic Transition Timetable** to **Leadership and Admin** via email.
""")

    with st.expander("Phase 5 — Exit meeting"):
        st.markdown("""
- Confirm the **Exit Meeting** with all TAC members by email.
- Follow the **Transition Report** process: send the **draft** first, then **print** the final to hand out at the meeting.
- Hold the **Exit Meeting** and share the report.
""")

    with st.expander("Phase 6 — Conclusion & EMS upload"):
        st.markdown("""
- Organise a **conclusion gift** for the student.
- Forward the **Transition Report** to **clcadmin281@schools.sa.edu.au** so admin can upload it to **EMS / DAYMAP**.
""")

    with st.expander("Phase 7 — Archiving"):
        st.markdown("""
- Compile **all documents** collected during the placement and give them to **ADMIN** for archiving.
""")

    with st.expander("Branch — if an extension is needed (Extension Requested tab)"):
        st.markdown("""
Only use this tab if the placement needs to continue **beyond the original exclusion dates**.
Follow the extension process and complete the paperwork held on this tab before the
original dates lapse. The extension process is clarified with the TAC at the Review Meeting.
""")

    # ---- Tracker decoders --------------------------------------------------
    st.markdown("#### Decoding the tracker tabs")

    st.markdown("**Reporting tab** — tracks each report through its writing steps:")
    st.markdown("""
- **Draft** — report drafted and sent to Leadership for review.
- **Final** — report finalised after Leadership feedback and printed for the meeting.
- **Distribution** — report shared at the meeting and forwarded for EMS/DAYMAP upload where required.

This runs once for the **Review Report** and again for the **Transition Report**.
""")

    st.markdown("**Scheduled Meetings tab** — confirms each meeting is locked in:")
    st.markdown("""
- **Set** — meeting date/time arranged.
- **Reminded** — TAC reminded ahead of the meeting.
- **Confirmed** — all TAC members have confirmed attendance by email.

This runs for both the **Review Meeting** and the **Exit Meeting**.
""")

    # ---- Quick-reference checklist -----------------------------------------
    st.markdown("#### Quick-reference checklist")
    st.markdown("This mirrors the **Checklist** tab — work through it top to bottom.")
    checklist = [
        "Read Information and Original SMARTAR Goals (developed by the TC in the SMARTAR Goal Builder)",
        "Prepare resources for classroom for arrival",
        "Start Date acknowledged",
        "Review Meeting confirmed by TAC",
        "Sounds-Write and Word Aware assessments completed",
        "Big Ideas in Number assessment completed",
        "Meet with Leadership to amend SMARTAR Goals (in the SMARTAR Goal Builder, then copy back into the student file)",
        "Convert SMARTAR Goal into the GAS (using the SMARTAR Goal Builder)",
        "Review Report process followed — draft sent, then printed to hand out at the meeting",
        "Review Meeting held — report shared, exit meeting scheduled, transition timetable developed and shared, extension process clarified",
        "Electronic Transition Timetable distributed to TAC via email",
        "Electronic Transition Timetable distributed to Leadership and Admin via email",
        "Exit Meeting confirmed by all TAC through email",
        "Transition Report process followed — draft sent, then printed to hand out at the meeting",
        "Exit Meeting held — report shared",
        "Organise conclusion gift",
        "Forward Transition Report to clcadmin281@schools.sa.edu.au for EMS upload",
        "Compile all documents collected during placement and give to ADMIN for archiving",
    ]
    st.markdown("\n".join(f"- {item}" for item in checklist))

    # ---- Glossary ----------------------------------------------------------
    st.markdown("#### Glossary")
    st.table({
        "Term": [
            "TAC", "SMARTAR goal", "GAS", "TC", "BSC", "ISE",
            "EMS / DAYMAP", "Allocation meeting", "Notice of Exclusion",
        ],
        "Meaning": [
            "Team Around the Child — the support team coordinating a student's placement.",
            "The student's goal format used at CLC, set in the SMARTAR Goal Builder.",
            "Goal Attainment Scale — the scaled version of the SMARTAR goal used to measure progress.",
            "The role that develops the original SMARTAR Goals in the SMARTAR Goal Builder.",
            "Behaviour Support Educator.",
            "Inclusive Support Educator.",
            "The SA student management system that reports are uploaded to.",
            "The meeting where students are allocated to a program/teacher.",
            "The formal exclusion document setting the placement dates.",
        ],
    })

    st.caption("One expansion to confirm: **TAC** as *Team Around the Child*.")


# ══════════════════════════════════════════════════════════════════════════
# REFERENCE REGISTRY  — add new internal references here
# ══════════════════════════════════════════════════════════════════════════
REFERENCES = [
    {
        "key": "case_management",
        "icon": "🗂️",
        "title": "Teacher Case Management Process",
        "blurb": "How to case manage a student placement end to end — pre-arrival, "
                 "review, transition, exit and archiving — and what each OneNote tab is for.",
        "render": render_case_management,
    },
    # Example of how to add the next one:
    # {
    #     "key": "another_reference",
    #     "icon": "📄",
    #     "title": "Another Reference",
    #     "blurb": "Short description shown on the card.",
    #     "render": render_another_reference,
    # },
]
REF_BY_KEY = {r["key"]: r for r in REFERENCES}


# ══════════════════════════════════════════════════════════════════════════
# VIEW
# ══════════════════════════════════════════════════════════════════════════
def show_grid():
    st.markdown("""
<div class="sr-header">
  <h1>📚 Staff Reference</h1>
  <p>Internal information and process guides for CLC-LBU staff.</p>
</div>
""", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, ref in enumerate(REFERENCES):
        with cols[i % 3]:
            st.markdown(
                f'<div class="sr-card"><div class="sr-icon">{ref["icon"]}</div>'
                f'<h3>{ref["title"]}</h3><p>{ref["blurb"]}</p></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"open_{ref['key']}", use_container_width=True):
                st.session_state.sr_open = ref["key"]
                st.rerun()
            st.write("")


def show_reference(key):
    ref = REF_BY_KEY.get(key)
    if not ref:
        st.session_state.sr_open = None
        st.rerun()
        return

    if st.button("← Back to Staff Reference", key="sr_back"):
        st.session_state.sr_open = None
        st.rerun()

    st.markdown(
        f'<div class="sr-header"><h1>{ref["icon"]} {ref["title"]}</h1></div>',
        unsafe_allow_html=True,
    )
    ref["render"]()


# ──────────────────────────────────────────────────────────────────────────
if st.session_state.sr_open:
    show_reference(st.session_state.sr_open)
else:
    show_grid()
