"""
34_Staff_Reference.py
CLC-LBU Portal — Staff Reference

A hub page for internal, information-only references for staff.
Opens to a grid of reference cards. Selecting a card renders that
reference inline, with a Back button to return to the grid.

To add a new reference: add an entry to the REFERENCES list and write
its render function. If a reference should be printable, also give it a
"docx" builder function (filename, bytes) and a download button appears
automatically. Nothing else needs to change.
"""

import streamlit as st
from io import BytesIO

# NOTE: This page is intentionally open — no login required.
# (require_auth() is deliberately omitted so staff can reach it without a password.)

# python-docx is used to generate printable Word copies at runtime.
# If it isn't installed, the page still works — the download button is
# simply hidden rather than crashing the page.
try:
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False

st.set_page_config(page_title="Staff Reference | CLC-LBU", page_icon="📚", layout="wide")

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
# PRINTABLE WORD VERSION
# ══════════════════════════════════════════════════════════════════════════
_DOCX_TEAL = RGBColor(0x12, 0x5C, 0x57) if DOCX_AVAILABLE else None
_DOCX_HEAD_FILL = "1B7F79"
_DOCX_SOFT_FILL = "E8F4F2"


def _shade(cell, fill):
    """Apply a clear background fill to a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def _heading(doc, text, size=14):
    p = doc.add_paragraph()
    p.space_before = Pt(8)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = _DOCX_TEAL
    return p


def _table(doc, headers, rows, widths_cm):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.autofit = False
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].width = Cm(widths_cm[i])
        _shade(hdr[i], _DOCX_HEAD_FILL)
        run = hdr[i].paragraphs[0].add_run(h)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(10)
    for r, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].width = Cm(widths_cm[i])
            if i == 0:
                _shade(cells[i], _DOCX_SOFT_FILL)
            run = cells[i].paragraphs[0].add_run(val)
            run.font.size = Pt(10)
            if i == 0:
                run.bold = True
    doc.add_paragraph()
    return t


def build_case_management_docx():
    """Return (filename, bytes) for a printable Word copy of the process."""
    doc = Document()

    # A4, 2cm margins
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.0)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)

    # Title
    title = doc.add_paragraph()
    trun = title.add_run("Teacher Case Management Process")
    trun.bold = True
    trun.font.size = Pt(20)
    trun.font.color.rgb = _DOCX_TEAL
    sub = doc.add_paragraph()
    srun = sub.add_run("Cowandilla Learning Centre — Learning & Behaviour Unit")
    srun.italic = True
    srun.font.size = Pt(10)
    srun.font.color.rgb = RGBColor(0x4A, 0x5B, 0x59)
    doc.add_paragraph()

    doc.add_paragraph(
        "As the allocated program teacher, you are the case manager for that student for the "
        "length of their placement. That means working through the student file in order — from "
        "before the student arrives, through their review, transition and exit, to archiving the "
        "file when they return to their home school."
    )
    doc.add_paragraph(
        "The Checklist tab is your master to-do list. Everything below unpacks what each item "
        "means and where to record it. Tick items off on the Checklist as you complete them so "
        "anyone picking up the file can see at a glance where the placement is up to."
    )

    # Tab map
    _heading(doc, "How the student file is organised")
    _table(
        doc,
        ["Tab", "What it is for"],
        [
            ["Checklist", "Your master sequence of tasks for the whole placement. Tick each item as it is done."],
            ["Student Information", "The entry meeting record — who the student is, background, strengths, risks, supports and the first-week attendance timetable."],
            ["SMARTAR Goals", "The student's goals, teaching/intervention plan and resources. Where goals are amended and converted into the GAS."],
            ["Scheduled Meetings", "A tracker confirming the Review and Exit meetings are set, reminded and confirmed by everyone in the team."],
            ["Reporting", "A tracker for the report-writing steps for both the Review Report and the Transition Report (draft, final, distribution)."],
            ["Transition Plan", "The weekly transition timetable agreed at the review meeting (which days/times the student attends as they move back to home school)."],
            ["Extension Requested", "The process and paperwork to follow only if the placement needs to continue beyond the original exclusion dates."],
        ],
        [4.0, 13.0],
    )

    # Lifecycle
    _heading(doc, "The placement at a glance")
    _table(
        doc,
        ["Phase", "Stage", "Main tabs in play"],
        [
            ["1", "Before the student arrives", "Student Information, SMARTAR Goals, Scheduled Meetings"],
            ["2", "Settling in & assessment", "SMARTAR Goals"],
            ["3", "Review meeting", "Reporting, Scheduled Meetings, Transition Plan"],
            ["4", "Transition", "Transition Plan"],
            ["5", "Exit meeting", "Reporting, Scheduled Meetings"],
            ["6", "Conclusion & EMS upload", "Reporting"],
            ["7", "Archiving", "Checklist"],
        ],
        [1.6, 5.4, 10.0],
    )

    # Phase detail
    _heading(doc, "Phase-by-phase")
    phases = [
        ("Phase 1 — Before the student arrives", [
            "Read the Student Information and the Original SMARTAR Goals (developed by the TC in the SMARTAR Goal Builder).",
            "Prepare resources and set up the classroom for the student's arrival.",
            "Acknowledge the start date.",
            "Confirm the Review Meeting with the TAC.",
        ]),
        ("Phase 2 — Settling in & assessment", [
            "Complete baseline assessments: Sounds-Write, Word Aware, and Big Ideas in Number.",
            "Meet with Leadership to amend the SMARTAR Goals in the SMARTAR Goal Builder, then copy them back into the student file.",
            "Convert the SMARTAR Goal into the GAS using the SMARTAR Goal Builder.",
        ]),
        ("Phase 3 — Review meeting", [
            "Follow the Review Report process: send the draft to Leadership first, then print the final to hand out at the meeting.",
            "Hold the Review Meeting: share the report, schedule the Exit Meeting, develop and share the transition timetable, and clarify the extension process.",
        ]),
        ("Phase 4 — Transition", [
            "Distribute the electronic Transition Timetable to the TAC via email.",
            "Distribute the electronic Transition Timetable to Leadership and Admin via email.",
        ]),
        ("Phase 5 — Exit meeting", [
            "Confirm the Exit Meeting with all TAC members by email.",
            "Follow the Transition Report process: send the draft first, then print the final for the meeting.",
            "Hold the Exit Meeting and share the report.",
        ]),
        ("Phase 6 — Conclusion & EMS upload", [
            "Organise a conclusion gift for the student.",
            "Forward the Transition Report to clcadmin281@schools.sa.edu.au for upload to EMS / DAYMAP.",
        ]),
        ("Phase 7 — Archiving", [
            "Compile all documents collected during the placement and give them to ADMIN for archiving.",
        ]),
        ("Branch — if an extension is needed (Extension Requested tab)", [
            "Only use this tab if the placement needs to continue beyond the original exclusion dates.",
            "Follow the extension process and complete the paperwork before the original dates lapse. The process is clarified with the TAC at the Review Meeting.",
        ]),
    ]
    for head, items in phases:
        ph = doc.add_paragraph()
        phr = ph.add_run(head)
        phr.bold = True
        phr.font.size = Pt(11)
        for it in items:
            doc.add_paragraph(it, style="List Bullet")
    doc.add_paragraph()

    # Tracker decoders
    _heading(doc, "Decoding the tracker tabs")
    rp = doc.add_paragraph()
    rp.add_run("Reporting tab").bold = True
    rp.add_run(" — tracks each report through its writing steps:")
    for it in [
        "Draft — report drafted and sent to Leadership for review.",
        "Final — report finalised after Leadership feedback and printed for the meeting.",
        "Distribution — report shared at the meeting and forwarded for EMS/DAYMAP upload where required.",
    ]:
        doc.add_paragraph(it, style="List Bullet")
    doc.add_paragraph("This runs once for the Review Report and again for the Transition Report.")

    sm = doc.add_paragraph()
    sm.add_run("Scheduled Meetings tab").bold = True
    sm.add_run(" — confirms each meeting is locked in:")
    for it in [
        "Set — meeting date/time arranged.",
        "Reminded — TAC reminded ahead of the meeting.",
        "Confirmed — all TAC members have confirmed attendance by email.",
    ]:
        doc.add_paragraph(it, style="List Bullet")
    doc.add_paragraph("This runs for both the Review Meeting and the Exit Meeting.")
    doc.add_paragraph()

    # Checklist
    _heading(doc, "Quick-reference checklist")
    doc.add_paragraph("Mirrors the Checklist tab — work through it top to bottom.")
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
    for item in checklist:
        doc.add_paragraph(f"\u2610  {item}")
    doc.add_paragraph()

    # Glossary
    _heading(doc, "Glossary")
    _table(
        doc,
        ["Term", "Meaning"],
        [
            ["TAC", "Team Around the Child — the support team coordinating a student's placement."],
            ["SMARTAR goal", "The student's goal format used at CLC, set in the SMARTAR Goal Builder."],
            ["GAS", "Goal Attainment Scale — the scaled version of the SMARTAR goal used to measure progress."],
            ["TC", "The role that develops the original SMARTAR Goals in the SMARTAR Goal Builder."],
            ["BSC", "Behaviour Support Educator."],
            ["ISE", "Inclusive Support Educator."],
            ["EMS / DAYMAP", "The SA student management system that reports are uploaded to."],
            ["Allocation meeting", "The meeting where students are allocated to a program/teacher."],
            ["Notice of Exclusion", "The formal exclusion document setting the placement dates."],
        ],
        [3.6, 13.4],
    )

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return "Teacher_Case_Management_Process.docx", buf.getvalue()


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
        "docx": build_case_management_docx,
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

    # Printable Word copy, if this reference provides one
    builder = ref.get("docx")
    if builder:
        if DOCX_AVAILABLE:
            try:
                filename, data = builder()
                dc1, dc2 = st.columns([1, 3])
                with dc1:
                    st.download_button(
                        "📄 Download for printing (Word)",
                        data=data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key=f"dl_{ref['key']}",
                    )
                with dc2:
                    st.caption("Opens in Word — print as-is, or save as PDF before printing.")
            except Exception as e:
                st.warning(f"Printable version couldn't be generated right now ({e}).")
        else:
            st.info("Printable Word download is unavailable (python-docx is not installed on the server).")
        st.write("")

    ref["render"]()


# ──────────────────────────────────────────────────────────────────────────
if st.session_state.sr_open:
    show_reference(st.session_state.sr_open)
else:
    show_grid()
