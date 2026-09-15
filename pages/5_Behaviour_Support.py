"""
Behaviour Data & Support Tools — Decision Flow guide.

Interactive companion + self-generating printable Word version, both driven
from the single CONTENT dict below. Editing CONTENT (box text, indicators,
the CI threshold, colours) updates the live page AND the downloadable
.docx on the very next page load — there is no separate offline build step
and no static file to keep in sync.

Read-only reference page — no Supabase storage, no auth required (matches
the open-access pattern used by 57_abch_process_guide.py).

TODO before deploying: none — all tool URLs below are confirmed.
"""

import io

import streamlit as st
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

st.set_page_config(page_title="Behaviour Data Flow Guide", layout="centered")

# =====================================================================
# SINGLE SOURCE OF TRUTH — edit here, both outputs update automatically
# =====================================================================

CI_THRESHOLD_TEXT = "two or more CIs for the same student within a term"  # confirm exact figure

URLS = {
    "quick_log": "https://clc-lbu-portal.onrender.com/Behaviour_Support?mode=quicklog",
    "abch_formatter": "https://clc-lbu-portal.onrender.com/abch_report_formatter",
    "comm_log": "https://clc-lbu-portal.onrender.com/communication_log",
    "sensory": "https://clc-lbu-portal.onrender.com/Sensory_Overview",
    "safety_plan": "https://clc-lbu-portal.onrender.com/Safety_risk_plan_builder",
    "scatter": "https://clc-lbu-portal.onrender.com/scatter_plot_tracker",
    "interval": "https://clc-lbu-portal.onrender.com/Interval_Support_Tracker",
}

CONTENT = {
    "title": "Behaviour Data & Support Tools",
    "subtitle": "Decision flow — which tool, and when",
    "legend": [
        ("gray", "Start"),
        ("teal", "Day-to-day data recording"),
        ("coral", "Threshold-triggered response"),
        ("blue", "Cross-cutting communication"),
    ],
    "start_box": {"title": "Behaviour incident occurs", "sub": None, "color": "gray"},
    "branch_boxes": [
        {"title": "Minor behaviour incident", "sub": "Quick Incident Log", "color": "teal",
         "url_key": "quick_log", "url_label": "Open Quick Incident Log",
         "note": "Auto-enters into Behaviour Support Tool — no further staff action needed"},
        {"title": "Critical incident (ABCH)", "sub": "C.I. Bot preferred, or Word template", "color": "coral",
         "url_key": "abch_formatter", "url_label": "Open ABCH Report Formatter", "arrow_below": True,
         "note": "Admin enters this into Behaviour Support Tool (Historical Entry) once posted to "
                 "Teams — not a staff action"},
    ],
    "comm_log_box": {"title": "Communication log",
                      "sub": "Record contact whenever parent/carer or agency is contacted", "color": "blue",
                      "url_key": "comm_log", "url_label": "Open Communication Log", "requires_login": True},
    "threshold_section": {
        "heading": "Threshold-triggered responses",
        "note": "Triggered by a pattern building up across incidents over time — not a direct next step "
                "off one single incident.",
        "boxes": [
            {
                "title": "Sensory profile", "sub": "Sensory-linked patterns", "color": "coral",
                "url_key": "sensory", "url_label": "Open sensory overview", "requires_login": True,
                "indicators": [
                    "Same sensory trigger recurring across incident reports (noise, crowding, touch, "
                    "texture, lighting, transitions)",
                    "Repeated seeking or avoidance behaviour noted across several incidents, not a one-off",
                    "New enrolment or transition with no sensory profile on file yet",
                    "Behaviour Analysis data suggests an environmental/sensory correlation rather than "
                    "social demand or task avoidance",
                ],
            },
            {
                "title": "Safety and risk plan", "sub": "Escalating risk behaviour", "color": "coral",
                "url_key": "safety_plan", "url_label": "Open Safety and Risk Plan Builder",
                "requires_login": True,
                "indicators": [
                    "A critical incident involving risk to the student or others (absconding/elopement, "
                    "physical aggression, self-harm, property destruction with safety implications)",
                    f"Frequency escalation — {CI_THRESHOLD_TEXT}",
                    "A recurring high-risk behaviour type across multiple reports, even where no single "
                    "incident was severe alone",
                    "Manager/TC review of a CI explicitly flags ongoing risk requiring a proactive plan",
                ],
            },
        ],
    },
    "ongoing_section": {
        "heading": "Ongoing data collection tools",
        "note": "Used continuously to build the pattern picture, independent of whether a CI has occurred.",
        "boxes": [
            {
                "title": "Scatter plot tracker", "sub": "Weekly pattern baseline", "color": "teal",
                "url_key": "scatter", "url_label": "Open Scatter Plot Tracker", "requires_login": True,
                "indicators": [
                    "Establishing whether a behaviour has a time/day pattern, before committing to "
                    "anything more structured",
                    "One target behaviour, light-touch, paper-style weekly recording",
                ],
            },
            {
                "title": "Interval tracker", "sub": "Structured interval data", "color": "teal",
                "url_key": "interval", "url_label": "Open Interval Tracker", "requires_login": True,
                "indicators": [
                    "A support plan is already in place and structured, more granular sampling is "
                    "needed (Quick or Grid mode)",
                    "Recording prevention \"saves\" — evidence a strategy is working, not just when it fails",
                ],
            },
        ],
    },
    "comm_log_points": [
        "Every time a parent/carer is contacted about a CI (a separate, mandatory step from the ABCH "
        "report's own notification field)",
        "Any other contact with a parent/carer or external agency relevant to the student's behaviour, "
        "safety or wellbeing — not gated behind an incident",
    ],
    "footer_note": (
        f"Assumptions in this version: CI frequency threshold shown as \u201c{CI_THRESHOLD_TEXT}\u201d — "
        "confirm and adjust if a different figure applies. Links marked \u26A0 require login — the "
        "portal does not currently redirect back to the requested tool after signing in, so you may "
        "land on the Behaviour Support home page instead and need to navigate from the sidebar."
    ),
}

LOGIN_NOTE = "Requires login — after signing in you'll land on the portal home; use the sidebar to open this tool"

# Colour ramps shared by the live page and the generated Word doc
COLORS = {
    "gray":  {"fill": "E9E7E0", "text": "444441"},
    "teal":  {"fill": "D9F0E5", "text": "0F6E56"},
    "coral": {"fill": "FAE3D9", "text": "712B13"},
    "blue":  {"fill": "DCEBFB", "text": "0C447C"},
}

# =====================================================================
# Word document generation — mirrors CONTENT exactly, regenerated fresh
# on every page load, so it can never drift from what's shown above
# =====================================================================

def _set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_cell_border(cell, hex_color, sz=4):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), hex_color)
        borders.append(el)
    tcPr.append(borders)


def _set_col_widths(table, widths_in):
    for row in table.rows:
        for cell, w in zip(row.cells, widths_in):
            cell.width = Inches(w)


def _styled_box(doc, title, sub, color_key, width_in):
    c = COLORS[color_key]
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _set_col_widths(table, [width_in])
    cell = table.rows[0].cells[0]
    _set_cell_background(cell, c["fill"])
    _set_cell_border(cell, c["text"])
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor.from_string(c["text"])
    if sub:
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(sub)
        r2.italic = True
        r2.font.size = Pt(9)
        r2.font.color.rgb = RGBColor.from_string(c["text"])
    return table


def _two_box_row(doc, left, right, half_in=3.05, gap_in=0.4):
    table = doc.add_table(rows=1, cols=3)
    table.autofit = False
    _set_col_widths(table, [half_in, gap_in, half_in])
    left_cell, gap_cell, right_cell = table.rows[0].cells

    def fill(cell, box):
        c = COLORS[box["color"]]
        inner = cell.add_table(rows=1, cols=1)
        inner.autofit = False
        _set_col_widths(inner, [half_in])
        icell = inner.rows[0].cells[0]
        _set_cell_background(icell, c["fill"])
        _set_cell_border(icell, c["text"])
        p = icell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(box["title"])
        r.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor.from_string(c["text"])
        if box.get("sub"):
            p2 = icell.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r2 = p2.add_run(box["sub"])
            r2.italic = True
            r2.font.size = Pt(9)
            r2.font.color.rgb = RGBColor.from_string(c["text"])
        cell.paragraphs[0].text = ""
        if box.get("note"):
            note_p = cell.add_paragraph()
            note_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            note_r = note_p.add_run(box["note"])
            note_r.italic = True
            note_r.font.size = Pt(8)
            note_r.font.color.rgb = RGBColor.from_string("6B6A65")

    fill(left_cell, left)
    fill(right_cell, right)
    return table


def _arrow(doc, right_only=False, half_in=3.05, gap_in=0.4):
    if right_only:
        table = doc.add_table(rows=1, cols=3)
        table.autofit = False
        _set_col_widths(table, [half_in, gap_in, half_in])
        cells = table.rows[0].cells
        cells[0].text = ""
        cells[1].text = ""
        p = cells[2].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("\u25BC")
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor.from_string("888780")
    else:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("\u25BC")
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor.from_string("888780")


def _sub_heading(doc, text, color_key):
    c = COLORS[color_key]
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor.from_string(c["text"])


def _body(doc, text):
    p = doc.add_paragraph(text)
    p.runs[0].font.size = Pt(10)


def _bullets(doc, items):
    start = len(doc.paragraphs)
    for item in items:
        doc.add_paragraph(item, style="List Bullet")
    for p in doc.paragraphs[start:]:
        for r in p.runs:
            r.font.size = Pt(10)


def build_docx() -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin = section.right_margin = Inches(0.75)
    section.top_margin = section.bottom_margin = Inches(0.75)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title_p.add_run(CONTENT["title"])
    tr.bold = True
    tr.font.size = Pt(20)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sub_p.add_run(CONTENT["subtitle"])
    sr.font.size = Pt(12)
    sr.font.color.rgb = RGBColor.from_string("5F5E5A")

    # legend
    legend_table = doc.add_table(rows=1, cols=len(CONTENT["legend"]))
    legend_table.autofit = True
    for cell, (color_key, label) in zip(legend_table.rows[0].cells, CONTENT["legend"]):
        c = COLORS[color_key]
        _set_cell_background(cell, c["fill"])
        _set_cell_border(cell, c["text"], sz=2)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(label)
        r.bold = True
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(c["text"])

    doc.add_paragraph()

    _styled_box(doc, CONTENT["start_box"]["title"], CONTENT["start_box"]["sub"],
                CONTENT["start_box"]["color"], 6.5)
    _arrow(doc)

    left_box, right_box = CONTENT["branch_boxes"]
    _two_box_row(doc, left_box, right_box)
    if right_box.get("arrow_below"):
        _arrow(doc, right_only=True)

    _styled_box(doc, CONTENT["comm_log_box"]["title"], CONTENT["comm_log_box"]["sub"],
                CONTENT["comm_log_box"]["color"], 6.5)

    ts = CONTENT["threshold_section"]
    _sub_heading(doc, ts["heading"], "coral")
    _body(doc, ts["note"])
    _two_box_row(doc, ts["boxes"][0], ts["boxes"][1])
    doc.add_paragraph()
    for box in ts["boxes"]:
        h = doc.add_paragraph()
        hr = h.add_run(f"{box['title']} — indicators")
        hr.bold = True
        hr.font.size = Pt(11)
        _bullets(doc, box["indicators"])

    os_ = CONTENT["ongoing_section"]
    _sub_heading(doc, os_["heading"], "teal")
    _body(doc, os_["note"])
    _two_box_row(doc, os_["boxes"][0], os_["boxes"][1])
    doc.add_paragraph()
    for box in os_["boxes"]:
        h = doc.add_paragraph()
        hr = h.add_run(f"{box['title']} — when to use")
        hr.bold = True
        hr.font.size = Pt(11)
        _bullets(doc, box["indicators"])

    _sub_heading(doc, "Communication log — always relevant", "blue")
    _bullets(doc, CONTENT["comm_log_points"])

    _sub_heading(doc, "Tool locations in the portal", "gray")
    url_table = doc.add_table(rows=1, cols=3)
    url_table.autofit = True
    hdr = url_table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Tool", "Portal location", "Login?"
    for cell in hdr:
        for r in cell.paragraphs[0].runs:
            r.bold = True
            r.font.size = Pt(9)
    for box in [CONTENT["branch_boxes"][0], CONTENT["branch_boxes"][1], CONTENT["comm_log_box"],
                *ts["boxes"], *os_["boxes"]]:
        row = url_table.add_row().cells
        row[0].text = box["title"]
        row[1].text = URLS.get(box.get("url_key", ""), "to be confirmed")
        row[2].text = "Required" if box.get("requires_login") else "—"
        for c in row:
            for r in c.paragraphs[0].runs:
                r.font.size = Pt(9)

    doc.add_paragraph()
    footer_p = doc.add_paragraph()
    fr = footer_p.add_run(CONTENT["footer_note"])
    fr.italic = True
    fr.font.size = Pt(9)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


# =====================================================================
# Live page rendering — reads from the same CONTENT dict above
# =====================================================================

st.markdown("""
<style>
.flow-box { border-radius: 8px; padding: 14px 18px; margin-bottom: 6px; text-align: center; border: 1.5px solid; }
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


def _box_html(box):
    sub_html = f'<div class="flow-sub">{box["sub"]}</div>' if box.get("sub") else ""
    return (f'<div class="flow-box box-{box["color"]}"><div class="flow-title">{box["title"]}</div>'
            f'{sub_html}</div>')


st.title(CONTENT["title"])
st.caption(CONTENT["subtitle"])

st.markdown(
    "".join(f'<span class="legend-chip box-{k}">{label}</span>' for k, label in CONTENT["legend"]),
    unsafe_allow_html=True,
)

docx_bytes = build_docx()  # regenerated from CONTENT on every page load
st.download_button(
    "Download printable version (Word)",
    data=docx_bytes,
    file_name="CLC-LBU_Behaviour_Data_Flow.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    use_container_width=True,
)

st.markdown(_box_html(CONTENT["start_box"]), unsafe_allow_html=True)
st.markdown('<div class="arrow">&#9660;</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
left_box, right_box = CONTENT["branch_boxes"]
with col1:
    st.markdown(_box_html(left_box), unsafe_allow_html=True)
    st.link_button(left_box["url_label"], URLS[left_box["url_key"]], use_container_width=True)
    if left_box.get("note"):
        st.caption(left_box["note"])
with col2:
    st.markdown(_box_html(right_box), unsafe_allow_html=True)
    st.link_button(right_box["url_label"], URLS[right_box["url_key"]], use_container_width=True)
    if right_box.get("note"):
        st.caption(right_box["note"])
    if right_box.get("arrow_below"):
        st.markdown('<div class="arrow">&#9660;</div>', unsafe_allow_html=True)

st.markdown(_box_html(CONTENT["comm_log_box"]), unsafe_allow_html=True)
st.link_button(CONTENT["comm_log_box"]["url_label"], URLS[CONTENT["comm_log_box"]["url_key"]],
                use_container_width=True)
if CONTENT["comm_log_box"].get("requires_login"):
    st.caption(f"\u26A0\uFE0F {LOGIN_NOTE}")

st.divider()

ts = CONTENT["threshold_section"]
st.subheader(f":orange[{ts['heading']}]")
st.write(ts["note"])
for box in ts["boxes"]:
    with st.expander(f"{box['title']} — indicators", expanded=False):
        st.markdown("\n".join(f"- {i}" for i in box["indicators"]))
        st.link_button(box["url_label"], URLS[box["url_key"]])
        if box.get("requires_login"):
            st.caption(f"\u26A0\uFE0F {LOGIN_NOTE}")

st.divider()

os_ = CONTENT["ongoing_section"]
st.subheader(f":green[{os_['heading']}]")
st.write(os_["note"])
for box in os_["boxes"]:
    with st.expander(f"{box['title']} — when to use", expanded=False):
        st.markdown("\n".join(f"- {i}" for i in box["indicators"]))
        st.link_button(box["url_label"], URLS[box["url_key"]])
        if box.get("requires_login"):
            st.caption(f"\u26A0\uFE0F {LOGIN_NOTE}")

st.divider()
st.caption(CONTENT["footer_note"])
