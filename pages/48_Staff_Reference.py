"""
48_Staff_Reference.py — CLC-LBU Staff Portal
=============================================
Staff Reference — policies & expectations, live from Supabase.

STAFF VIEW (default): pick a document, expand sections to read,
download the full branded Word document to print. View-only.

Deep links — used by the "Staff References" dropdown tiles on the
portal homepage so each category (or a single document) opens
directly instead of landing on the full picker:
    ?doc=<slug>          e.g. ?doc=daily-work-expectations
    ?category=<name>     e.g. ?category=DfE%20Procedures
                          (URL-encode spaces/& in the category name)
If a category has exactly one document, the deep link opens that
document directly; otherwise it opens the card grid filtered to
just that category, with a "← All categories" button to clear it.

ADMIN (password gated): edit section content/titles, reorder,
add/remove sections, add documents, publish/unpublish, and a
one-click seeder that loads the CLC 2026.8 Daily Work
Expectations starter content.

-------------------------------------------------------------------
SUPABASE SETUP — run once in the SQL editor:

create table if not exists reference_documents (
    id bigint generated always as identity primary key,
    slug text unique not null,
    doc_code text default '',
    title text not null,
    subtitle text default '',
    intro text default '',
    category text default 'Policies & Expectations',
    sort_order int default 0,
    is_published boolean default true,
    updated_at timestamptz default now()
);

create table if not exists reference_sections (
    id bigint generated always as identity primary key,
    document_id bigint references reference_documents(id) on delete cascade,
    title text not null,
    content text default '',
    sort_order int default 0,
    updated_at timestamptz default now()
);

alter table reference_documents enable row level security;
alter table reference_sections enable row level security;
create policy "ref_docs_all" on reference_documents for all using (true) with check (true);
create policy "ref_secs_all" on reference_sections for all using (true) with check (true);
-------------------------------------------------------------------
Dependencies: streamlit, supabase, python-docx (all already used by
other portal tools).
"""

import io
import json
import re
from datetime import datetime, timezone, timedelta

import streamlit as st
from supabase import create_client

# ------------------------------------------------------------------
# Page config + CLC styling
# ------------------------------------------------------------------
st.set_page_config(page_title="Staff Reference", page_icon="📖", layout="wide")

TEAL = "#00695C"
TEAL_DARK = "#004D40"
TEAL_LIGHT = "#E0F2F1"

st.markdown(
    f"""
    <style>
    .ref-header {{
        background: linear-gradient(120deg, {TEAL_DARK}, {TEAL});
        color: white; padding: 1.2rem 1.5rem; border-radius: 12px;
        margin-bottom: 1rem;
    }}
    .ref-header h1 {{ color: white; font-size: 1.6rem; margin: 0; }}
    .ref-header p {{ color: {TEAL_LIGHT}; margin: 0.3rem 0 0 0; font-size: 0.95rem; }}
    .ref-intro {{
        background: {TEAL_LIGHT}; border-left: 6px solid {TEAL};
        padding: 0.8rem 1rem; border-radius: 6px; margin-bottom: 1rem;
        color: #1a1a1a;
    }}
    div[data-testid="stExpander"] details summary p {{
        font-weight: 700; color: {TEAL_DARK}; font-size: 1.02rem;
    }}
    .cat-heading {{
        display: flex; align-items: center; gap: 0.5rem;
        color: {TEAL_DARK}; font-size: 1.15rem; font-weight: 700;
        margin: 1.2rem 0 0.6rem 0;
    }}
    .doc-card-code {{
        color: {TEAL}; font-weight: 700; font-size: 0.78rem;
        letter-spacing: 0.03em; text-transform: uppercase; margin-bottom: 0.15rem;
    }}
    .doc-card-title {{
        font-weight: 700; font-size: 1.05rem; color: #1a1a1a; margin-bottom: 0.3rem;
        min-height: 2.6rem;
    }}
    .doc-card-sub {{
        color: #444; font-size: 0.88rem; margin-bottom: 0.5rem; min-height: 2.4rem;
    }}
    .doc-card-meta {{
        color: #888; font-size: 0.78rem; margin-bottom: 0.6rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Supabase connection (tolerant of the two secret layouts used
# across the portal)
# ------------------------------------------------------------------
def _get_supabase():
    url = key = None
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_ANON_KEY")
    except Exception:
        pass
    if not url:
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"].get("key") or st.secrets["supabase"].get("anon_key")
        except Exception:
            pass
    if not url or not key:
        st.error("Supabase credentials not found in secrets. Add SUPABASE_URL and SUPABASE_KEY.")
        st.stop()
    return create_client(url, key)


sb = _get_supabase()

# ------------------------------------------------------------------
# Admin gate.
# Uses the shared confidential password. If your confidential_auth
# module exposes a check function, swap the marked block for it —
# otherwise this reads the same secret directly.
# ------------------------------------------------------------------
def admin_unlocked() -> bool:
    if st.session_state.get("ref_admin_ok"):
        return True
    pw = None
    for k in ("CONFIDENTIAL_PASSWORD", "confidential_password", "ADMIN_PASSWORD"):
        try:
            pw = st.secrets.get(k)
        except Exception:
            pw = None
        if pw:
            break
    if not pw:
        st.warning("No admin password configured in secrets (CONFIDENTIAL_PASSWORD).")
        return False
    entered = st.text_input("Admin password", type="password", key="ref_admin_pw")
    if entered:
        if entered == pw:
            st.session_state["ref_admin_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ------------------------------------------------------------------
# Data access
# ------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_documents(include_unpublished: bool = False):
    q = sb.table("reference_documents").select("*").order("sort_order").order("id")
    res = q.execute()
    docs = res.data or []
    if not include_unpublished:
        docs = [d for d in docs if d.get("is_published")]
    return docs


@st.cache_data(ttl=60)
def fetch_sections(document_id: int):
    res = (
        sb.table("reference_sections")
        .select("*")
        .eq("document_id", document_id)
        .order("sort_order")
        .order("id")
        .execute()
    )
    return res.data or []


def clear_caches():
    fetch_documents.clear()
    fetch_sections.clear()
    _docx_bytes.clear()


def _now():
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Markdown -> docx (minimal, matches the content conventions used
# in the seeded sections: '- ' bullets, '**bold**', '> ' callouts)
# ------------------------------------------------------------------
def build_docx(doc_row, sections) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    TEAL_RGB = RGBColor(0x00, 0x69, 0x5C)
    TEAL_DARK_RGB = RGBColor(0x00, 0x4D, 0x40)
    GREY = RGBColor(0x59, 0x59, 0x59)

    d = Document()
    for s in d.sections:
        s.top_margin = s.bottom_margin = Pt(36)
        s.left_margin = s.right_margin = Pt(45)

    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    def shade(par, hexcolor):
        pPr = par._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), hexcolor)
        pPr.append(shd)

    # Title block
    t1 = d.add_paragraph()
    r = t1.add_run("COWANDILLA LEARNING CENTRE  |  LEARNING & BEHAVIOUR UNIT")
    r.font.size = Pt(8); r.font.bold = True; r.font.color.rgb = RGBColor(0xE0, 0xF2, 0xF1)
    shade(t1, "00695C")
    t2 = d.add_paragraph()
    r = t2.add_run(f"{doc_row.get('doc_code','')}  {doc_row['title']}".strip())
    r.font.size = Pt(20); r.font.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    shade(t2, "00695C")
    if doc_row.get("subtitle"):
        t3 = d.add_paragraph()
        r = t3.add_run(doc_row["subtitle"])
        r.font.size = Pt(10); r.font.italic = True; r.font.color.rgb = RGBColor(0xE0, 0xF2, 0xF1)
        shade(t3, "00695C")
    d.add_paragraph()

    def add_runs(par, text):
        # split on **bold** markers
        for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
            if chunk == "":
                continue
            run = par.add_run(chunk)
            if i % 2 == 1:
                run.font.bold = True

    if doc_row.get("intro"):
        p = d.add_paragraph()
        add_runs(p, doc_row["intro"])
        shade(p, "E0F2F1")

    def add_table(block_lines):
        rows = []
        for ln in block_lines:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue  # separator row
            rows.append(cells)
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        t = d.add_table(rows=0, cols=ncols)
        t.style = "Table Grid"
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for ci in range(ncols):
                text = row[ci] if ci < len(row) else ""
                par = cells[ci].paragraphs[0]
                add_runs(par, text)
                for run in par.runs:
                    run.font.size = Pt(9.5)
                    if ri == 0:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                tcPr = cells[ci]._tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:fill"), "00695C" if ri == 0 else ("F2F2F2" if ri % 2 == 0 else "FFFFFF"))
                tcPr.append(shd)
        d.add_paragraph()

    for sec in sections:
        # Real Word "Heading 2" so a downloaded copy can be edited in Word
        # and uploaded back as a new version (Admin → Upload a new version).
        h = d.add_paragraph(style="Heading 2")
        r = h.add_run(sec["title"])
        r.font.name = "Calibri"
        r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = TEAL_DARK_RGB
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        lines = (sec.get("content") or "").splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line.strip():
                i += 1
                continue
            if line.lstrip().startswith("|"):
                block = []
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    block.append(lines[i]); i += 1
                add_table(block)
                continue
            if line.startswith("- "):
                p = d.add_paragraph(style="List Bullet")
                add_runs(p, line[2:])
            elif line.startswith("> "):
                p = d.add_paragraph()
                add_runs(p, line[2:])
                shade(p, "E0F2F1")
            else:
                p = d.add_paragraph()
                add_runs(p, line)
            p.paragraph_format.space_after = Pt(3)
            i += 1

    acst = datetime.now(timezone(timedelta(hours=9, minutes=30)))
    f = d.add_paragraph()
    r = f.add_run(f"CLC-LBU  |  Downloaded from the Staff Portal {acst.strftime('%d/%m/%Y')} — the portal version is always current.")
    r.font.size = Pt(8); r.font.color.rgb = GREY

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------
# Word upload -> sections parser (admin "upload a document" flow)
#
# Walks the .docx body in document order (paragraphs + tables
# interleaved), and:
#   - splits into sections on the chosen heading level
#   - converts bulleted paragraphs to '- ' lines
#   - converts bold runs to '**bold**'
#   - converts tables to '| a | b |' pipe rows (single-cell tables,
#     e.g. callout boxes, become '> ' highlighted notes instead)
# Works well on .docx files that use Word's built-in Heading styles;
# for documents formatted with plain bold lines instead of Styles,
# the "Bold standalone lines" option is offered as a fallback.
# ------------------------------------------------------------------
def _run_to_md(run):
    text = run.text
    if not text:
        return ""
    return f"**{text}**" if run.bold else text


def _para_to_md(paragraph):
    return "".join(_run_to_md(r) for r in paragraph.runs).strip() or paragraph.text.strip()


def _is_bullet_para(paragraph):
    style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
    if any(k in style_name for k in ("list bullet", "list paragraph", "bullet")):
        return True
    pPr = paragraph._p.pPr
    return pPr is not None and pPr.numPr is not None


def _is_split_heading(paragraph, split_level):
    text = paragraph.text.strip()
    if not text:
        return False
    style_name = (paragraph.style.name or "") if paragraph.style else ""
    if split_level == "Heading 1":
        return style_name == "Heading 1"
    if split_level == "Heading 2":
        return style_name in ("Heading 1", "Heading 2")
    if split_level == "Bold standalone lines":
        runs = [r for r in paragraph.runs if r.text.strip()]
        return bool(runs) and all(r.bold for r in runs) and len(text) <= 120
    return False


def _table_block_to_md(table):
    rows = table.rows
    if not rows:
        return ""
    if len(rows) == 1 and len(rows[0].cells) == 1:
        text = rows[0].cells[0].text.strip()
        return f"> {text}" if text else ""
    header = [c.text.strip().replace("\n", " ") for c in rows[0].cells]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in rows[1:]:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def parse_docx_to_sections(file_bytes: bytes, split_level: str):
    """Returns (intro_text, [(section_title, section_content), ...])."""
    from docx import Document as DocxDocument
    from docx.oxml.ns import qn
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph

    doc = DocxDocument(io.BytesIO(file_bytes))

    def iter_block_items(parent):
        for child in parent.element.body.iterchildren():
            if child.tag == qn("w:p"):
                yield DocxParagraph(child, parent)
            elif child.tag == qn("w:tbl"):
                yield DocxTable(child, parent)

    sections, intro_lines = [], []
    current_title, current_lines = None, []

    def flush():
        nonlocal current_title, current_lines
        if current_title:
            sections.append((current_title, "\n".join(current_lines).strip()))
        current_title, current_lines = None, []

    def para_fill(p):
        fills = p._p.xpath("./w:pPr/w:shd/@w:fill")
        return (fills[-1] if fills else "").upper()

    for block in iter_block_items(doc):
        target = current_lines if current_title else intro_lines
        if isinstance(block, DocxTable):
            md = _table_block_to_md(block)
            if md:
                if target and target[-1].strip() and not md.startswith("> "):
                    target.append("")
                target.append(md)
            continue
        fill = para_fill(block)
        # Skip the portal's own export chrome (teal title banner + download footer)
        # so a downloaded-then-edited copy re-uploads cleanly.
        if fill == "00695C":
            continue
        if block.text.strip().startswith("CLC-LBU  |  Downloaded from the Staff Portal"):
            continue
        if _is_split_heading(block, split_level):
            flush()
            current_title = block.text.strip()
            continue
        text = _para_to_md(block)
        style_name = (block.style.name or "") if block.style else ""
        if style_name.startswith("Heading") and text:
            line = f"**{text}**"
        elif _is_bullet_para(block):
            line = f"- {text}" if text else ""
        elif fill == "E0F2F1" and text and current_title:
            line = f"> {text}"  # highlighted note
        else:
            line = text
        if line:
            # Keep a blank line where a list/note/table meets ordinary text,
            # otherwise Markdown would run the text into the bullet above it.
            kind = lambda l: "-" if l.startswith("- ") else (">" if l.startswith("> ") else ("|" if l.startswith("|") else "p"))
            prev = next((l for l in reversed(target) if l.strip()), None)
            if prev is not None and target[-1].strip() and kind(prev) != kind(line) and "p" in (kind(prev), kind(line)):
                target.append("")
            target.append(line)

    flush()
    intro = "\n".join(intro_lines).strip()
    sections = [(t, c) for t, c in sections if t.strip()]
    return intro, sections


def _upload_parse_widget(prefix):
    """Renders an uploader + split-level choice + Parse button + preview.
    Returns the parsed {"intro", "sections", "filename"} dict once a
    parse has run this session, else None."""
    f = st.file_uploader("Upload a Word document (.docx)", type=["docx"], key=f"{prefix}_file")
    split_level = st.radio(
        "How should sections be detected?",
        ["Heading 2", "Heading 1", "Bold standalone lines"],
        horizontal=True, key=f"{prefix}_split",
        help="Heading 1/2 use Word's built-in heading styles (most CLC documents use Heading 2 for section titles). "
             "'Bold standalone lines' treats any short, fully-bold line as a section title instead — use this if the "
             "document wasn't formatted with Word Styles.",
    )
    if f is not None and st.button("🔍 Parse document", key=f"{prefix}_parsebtn"):
        try:
            intro, sections = parse_docx_to_sections(f.getvalue(), split_level)
            if not sections:
                st.warning("No sections were detected with that setting — try a different option above.")
                st.session_state.pop(f"{prefix}_parsed", None)
            else:
                st.session_state[f"{prefix}_parsed"] = {"intro": intro, "sections": sections, "filename": f.name}
        except Exception as e:
            st.error(f"Couldn't read that file ({e}). Make sure it's a .docx (Word 'Save As' if it's a .doc).")
            st.session_state.pop(f"{prefix}_parsed", None)

    parsed = st.session_state.get(f"{prefix}_parsed")
    if parsed:
        st.success(f"Found {len(parsed['sections'])} section(s) in {parsed['filename']}.")
        with st.expander("Preview parsed sections", expanded=True):
            if parsed["intro"]:
                st.caption("Text before the first section heading:")
                preview = parsed["intro"][:400] + ("…" if len(parsed["intro"]) > 400 else "")
                st.markdown(preview)
                st.divider()
            for t, c in parsed["sections"]:
                st.markdown(f"**{t}**")
                preview = (c[:220] + "…") if len(c) > 220 else c
                st.caption(preview or "_(empty)_")
        return parsed
    return None


# ------------------------------------------------------------------
# Seed content — CLC 2026.8 Daily Work Expectations (current as of
# 20 July 2026). Loaded via the admin "Seed" button when empty.
# ------------------------------------------------------------------
SEED_DOC = {
    "slug": "daily-work-expectations",
    "doc_code": "CLC 2026.8",
    "title": "Daily Work Expectations",
    "subtitle": "Norms for every working day at CLC",
    "intro": "**Staff Portal:** Daily processes run through the CLC-LBU Staff Portal — absence procedures, Staff Bulletin, CLC Calendar, NIT Bookings, Communication Log and hazard reporting. Bookmark it.",
    "category": "Policies & Expectations",
    "sort_order": 1,
    "is_published": True,
}

SEED_SECTIONS = [
    ("Hours and start of day", """- Administration hours: **8:00am – 4:00pm**. Teaching staff are on site **8:30am – 3:30pm** and available via mobile until 4:00pm. Face-to-face teaching (9:00am – 3:00pm) excludes NIT and meal breaks.
- Program teachers exercise duty of care by supervising their students throughout face-to-face teaching time.
- Be prepared for the working day by 8:30am (SSOs by scheduled start time): **Staff Bulletin checked on the staff portal**, emails checked, phone calls made or returned."""),
    ("Absences and whereabouts", """- **Unplanned absence:** call or text the **Manager and Transition Coordinator by 6:30am**. Then follow the **Unplanned Absence procedure on the staff portal** — all steps, including recording the absence via EIK (edHR self-service).
- Maintain an **up-to-date TRT plan** (timetable, room access, program information) so your program can run in your absence.
- **Planned absence:** request leave in advance through your line manager — follow the **Planned Absence procedure on the staff portal** and complete the Planned Absence form (observe LSL and sick leave timeframes).
- **All staff sign in and out at Admin every day** — on arrival, on departure, and whenever leaving site during the day. This is an **expectation, not a negotiation**: it is how we account for everyone in an emergency.
- Seek Site Leader approval in advance to leave before 3:30pm.
- If absent for more than 2 days, set an automatic email reply directing stakeholders to CLC administration so enquiries can be managed during your leave."""),
    ("Equipment and breaks", """- Carry your keys/fobs at all times. Walkie-talkies charged and carried all day.
- Take a 30-minute meal break within the first 5 hours of the working day — timing depends on program needs and SSO cover, negotiated with your line manager if required.
- With **3 or fewer students** attending, lunch breaks in two-teacher programs can be **informally managed between the two teachers** — the same expectation as informal NIT arrangements. Any change to these arrangements is raised with leadership beforehand."""),
    ("End of day", """- Teachers remain on site until 3:30pm and are contactable on mobile until 4:00pm. Requests to leave earlier go to your line manager.
- All students require supervision while on the CLC site. Exercise duty of care **until students are picked up by carer or taxi (by 3:00pm)** — if you cannot, arrange other supervision through your line manager.
- Check emails before leaving from 3:30pm. Lock student laptops/iPads away securely. Program phone **locked away/stored in the agreed location** so it can be accessed if a staff member is away; phone messaging switched on after 3:30pm.
- Lock building entry/exit; turn off computers, screens and air conditioning."""),
    ("Site environment", """- Meeting/staff rooms locked after use and left clean and tidy; meeting rooms are booked by **entering the booking on the Daily Bulletin**; lights and air conditioning off.
- **All staff are allocated a week** to complete kitchen duties (roster displayed in kitchen).
- Every program has a welcome sign on the door; staff photos displayed near the front entrance for visitors.
- Security: individual alarm codes are issued; keys and personal items locked away at all times; front door locked at all times with the doorbell available for visitors.
- Report hazards and maintenance issues via the **Report a Hazard tile on the staff portal**."""),
    ("Communication and documentation", """**Two records, no exceptions:**
- **Every meeting** — including TAC, Transition and Review — whether held face-to-face, over the phone or via email → documented officially in the **student file**, accessible through the portal (where the case management checklist also sits). It is an expectation that **ALL meetings are uploaded**.
- **All other communication** with families, schools, SSS and agencies — calls, emails, texts, conversations → entered in the **Communication Log on the staff portal**.

This applies to every staff member and every contact, however brief. **If it isn't recorded, it didn't happen.**
> **Trial:** The Communication Log is being trialled as our system for day-to-day contact. Capture the contact at the time it happens — date, who, method, summary. Feedback on the trial goes to your line manager.
- Use the departmental signature block and corporate branding/writing style. LBU font is Calibri 11 for any documentation distributed to stakeholders.
- Letters to outside agencies/stakeholders are ratified and co-signed by the Site Leader on Learning Centre letterhead.
- Use the Transition Report template for Exit meetings: send electronically to the home-school Principal (cc your line manager), distribute hard copies at the Exit meeting, and save the report to the **student file**.
- Respond to stakeholder emails within **24–48 hours**.
- Program teachers can expect newly referred student information by 3:30pm Wednesdays."""),
    ("Attire and mobile phones", """- No thongs or backless/open-front shoes. Risk-assess jewellery, scarves and long hair worn down.
- **Site uniform:** to be worn when leaving the site — e.g. excursions and offsite meetings.
- Personal mobile phones are **not out at any time you are student-facing** — this includes, but is not limited to, face-to-face teaching (also yard duty, transitions and excursions). Phones stay out of sight; staff model the student ICT device policy.
- Program/site mobiles are used for parent and stakeholder contact where the landline is unavailable or inappropriate — charged and switched on for excursion days."""),
    ("Non-Instruction Time (NIT)", """- With **4 or more students** attending, the **formal NIT timetable** applies (see PAC-ratified NIT guidelines). View and book NIT via **NIT Bookings on the staff portal**.
- With **3 or fewer students** attending, **informal NIT arrangements** apply. This means the two teachers in a program **release each other** for their allocated NIT, and the NIT teacher may be deployed elsewhere — **at the discretion of leadership and according to site needs**.
- Any change to NIT or lunch break arrangements is raised with leadership **beforehand** — leadership makes the final decision.
- NIT is calculated per face-to-face teaching minutes and may alter with teacher–student contact time. Missed NIT is individually negotiated with line management within the PAC-approved timeframe.

**Booking times — additional NIT**
- Booking times are **additional NIT**. Meetings should be scheduled within your allocated NIT in the first instance — that is what NIT is for.
- Where a meeting time within your allocated NIT **cannot be agreed with the other attendees**, a Booking time supports attendance at the offsite or student meeting. In this case, **entering the meeting in NIT Bookings on the staff portal is required**.
- Booking times are **never used for personal appointments** — personal appointments are managed through the leave process.
- Booking times are not for make-up NIT, **unless agreed to by leadership beforehand** — this is the only exception."""),
    ("Staff meetings", """- Staff meetings start at **3:10pm Wednesdays**; attendance at all staff meetings is required, including signing in.
- The **Staff Bulletin is sent out COB Tuesday** with business and information that can be shared without needing face-to-face time — read it before Wednesday's meeting so meeting time stays focused.
- Participate — share data and teaching and learning strategies, and engage in the administration and training components.
- Arrange any site/student meetings outside of staff meeting time."""),
    ("Team meetings", """- Program teams meet **once a week**, following the alternating fortnightly structure: **Week A — student lens** (individual students, goals, data, interventions); **Week B — system lens** (curriculum and program improvement).
- All team meetings are **documented in minutes via the Team Meetings tool on the staff portal**, including agreements made and who is actioning them.
- Agreements made in team meetings **are actioned** — actions are reviewed at the following meeting before new business.
- If you do not attend a meeting, **follow up with the minutes and action any agreements** that involve you — absence doesn't pause your actions."""),
    ("Offsite meetings and travel", """- All site/student meeting times are communicated to site admin and entered in the **CLC Calendar on the staff portal**.
- Use the government vehicle in the first instance when travelling between programs or offsite (as negotiated with your line manager).
- Pre-approval is required when leaving the premises between 8:30am and 3:30pm; sign out at Admin on departure, sign in on return, and sign in when attending offsite meetings."""),
    ("Student attendance", """- Ring the student's caregiver **by 9:30am** when a student is absent and record the reason on **EMS**. All absences must be investigated and explained.
- Attach student attendance data to the Transition Report at exit. **Attendance concerns are discussed with leadership** — refer to the Student Attendance Improvement Plan (induction folder) for managing ongoing non-attendance."""),
    ("Mail and first aid", """- Send information to carers via registered post only — liaise with site administration.
- Program teachers maintain first aid equipment and facilities daily, consulting the site's nominated First Aid staff on procedures and systems.
- Student medication is kept in a locked medication box (program teachers and administration both hold keys). Complete the medication log when administering medication at the CORRECT time.
- If medication is administered at a time that differs from the medication plan, complete a medication error log and inform the Site Manager and parent."""),
    ("Student file boxes", """- Program teachers can expect student file boxes **within 24 hours of the entry meeting** — or, if the student is starting the next day, **by the end of the entry-meeting day**."""),
]

SEED_DOC_CM = {
    "slug": "teacher-case-management-process",
    "doc_code": "",
    "title": "Teacher Case Management Process",
    "subtitle": "How to case manage a student placement end to end — and what each OneNote tab is for",
    "intro": "As the allocated program teacher, **you are the case manager** for that student for the length of their placement — from before they arrive, through review, transition and exit, to archiving the file when they return to their home school. The **Checklist tab is your master to-do list**; everything here unpacks what each item means. Tick items off as you complete them so anyone picking up the file can see at a glance where the placement is up to.",
    "category": "Policies & Expectations",
    "sort_order": 2,
    "is_published": True,
}

SEED_SECTIONS_CM = [
    ("How the student file is organised", """Each student's section contains the following pages. You move through them roughly top to bottom across the placement.
| Tab | What it is for |
| --- | --- |
| Checklist | Your master sequence of tasks for the whole placement. Tick each item as it is done. |
| Student Information | The entry meeting record — who the student is, background, strengths, risks, supports and the first-week attendance timetable. |
| SMARTAR Goals | The student's goals, teaching/intervention plan and resources. Where goals are amended and converted into the GAS. |
| Scheduled Meetings | A tracker confirming the Review and Exit meetings are set, reminded and confirmed by everyone in the team. |
| Reporting | A tracker for the report-writing steps for both the Review Report and the Transition Report (draft, final, distribution). |
| Transition Plan | The weekly transition timetable agreed at the review meeting (which days/times the student attends as they move back to home school). |
| Extension Requested | The process and paperwork to follow only if the placement needs to continue beyond the original exclusion dates. |"""),
    ("The placement at a glance", """The placement runs through seven phases. Detailed steps for each are in the next section.
| Phase | Stage | Main tabs in play |
| --- | --- | --- |
| 1 | Before the student arrives | Student Information, SMARTAR Goals, Scheduled Meetings |
| 2 | Settling in & assessment | SMARTAR Goals |
| 3 | Review meeting | Reporting, Scheduled Meetings, Transition Plan |
| 4 | Transition | Transition Plan |
| 5 | Exit meeting | Reporting, Scheduled Meetings |
| 6 | Conclusion & EMS upload | Reporting |
| 7 | Archiving | Checklist |"""),
    ("Phase 1 — Before the student arrives", """- Read the **Student Information** and the **Original SMARTAR Goals** (developed by the TC in the SMARTAR Goal Builder) so you know the student before day one.
- Prepare resources and set up the classroom for the student's arrival.
- Acknowledge the **start date**.
- Confirm the **Review Meeting** with the TAC (Team Around the Child)."""),
    ("Phase 2 — Settling in & assessment", """- Complete baseline assessments: **Sounds-Write**, **Word Aware**, and **Big Ideas in Number**.
- Meet with **Leadership** to amend the SMARTAR Goals — do this in the SMARTAR Goal Builder, then copy the updated goals back into the student file.
- Convert the SMARTAR Goal into the **GAS** (Goal Attainment Scale) using the SMARTAR Goal Builder."""),
    ("Phase 3 — Review meeting", """- Follow the **Review Report** process: send the **draft** to Leadership first, then **print** the final to hand out at the meeting.
- Hold the **Review Meeting**. At this meeting you: share the report, schedule the **Exit Meeting**, develop and share the **transition timetable**, and clarify the **extension process** (in case the placement needs to continue)."""),
    ("Phase 4 — Transition", """- Distribute the **electronic Transition Timetable** to the **TAC** via email.
- Distribute the **electronic Transition Timetable** to **Leadership and Admin** via email."""),
    ("Phase 5 — Exit meeting", """- Confirm the **Exit Meeting** with all TAC members by email.
- Follow the **Transition Report** process: send the **draft** first, then **print** the final to hand out at the meeting.
- Hold the **Exit Meeting** and share the report."""),
    ("Phase 6 — Conclusion & EMS upload", """- Organise a **conclusion gift** for the student.
- Forward the **Transition Report** to **clc.admin281@schools.sa.edu.au** so admin can upload it to **EMS**."""),
    ("Phase 7 — Archiving", """- Compile **all documents** collected during the placement and give them to **ADMIN** for archiving."""),
    ("Branch — if an extension is needed", """- Only use the **Extension Requested** tab if the placement needs to continue **beyond the original exclusion dates**.
- Follow the extension process and complete the paperwork held on this tab before the original dates lapse. The extension process is clarified with the TAC at the Review Meeting."""),
    ("Decoding the tracker tabs", """**Reporting tab** — tracks each report through its writing steps:
- **Draft** — report drafted and sent to Leadership for review.
- **Final** — report finalised after Leadership feedback and printed for the meeting.
- **Distribution** — report shared at the meeting and forwarded for EMS upload where required.

This runs once for the **Review Report** and again for the **Transition Report**.

**Scheduled Meetings tab** — confirms each meeting is locked in:
- **Set** — meeting date/time arranged.
- **Reminded** — TAC reminded ahead of the meeting.
- **Confirmed** — all TAC members have confirmed attendance by email.

This runs for both the **Review Meeting** and the **Exit Meeting**."""),
    ("Quick-reference checklist", """This mirrors the **Checklist** tab — work through it top to bottom.
- ☐ Read Information and Original SMARTAR Goals (developed by the TC in the SMARTAR Goal Builder)
- ☐ Prepare resources for classroom for arrival
- ☐ Start Date acknowledged
- ☐ Review Meeting confirmed by TAC
- ☐ Sounds-Write and Word Aware assessments completed
- ☐ Big Ideas in Number assessment completed
- ☐ Meet with Leadership to amend SMARTAR Goals (in the SMARTAR Goal Builder, then copy back into the student file)
- ☐ Convert SMARTAR Goal into the GAS (using the SMARTAR Goal Builder)
- ☐ Review Report process followed — draft sent, then printed to hand out at the meeting
- ☐ Review Meeting held — report shared, exit meeting scheduled, transition timetable developed and shared, extension process clarified
- ☐ Electronic Transition Timetable distributed to TAC via email
- ☐ Electronic Transition Timetable distributed to Leadership and Admin via email
- ☐ Exit Meeting confirmed by all TAC through email
- ☐ Transition Report process followed — draft sent, then printed to hand out at the meeting
- ☐ Exit Meeting held — report shared
- ☐ Organise conclusion gift
- ☐ Forward Transition Report to clc.admin281@schools.sa.edu.au for EMS upload
- ☐ Compile all documents collected during placement and give to ADMIN for archiving"""),
    ("Glossary", """| Term | Meaning |
| --- | --- |
| TAC | Team Around the Child — the support team coordinating a student's placement. |
| SMARTAR goal | The student's goal format used at CLC, set in the SMARTAR Goal Builder. |
| GAS | Goal Attainment Scale — the scaled version of the SMARTAR goal used to measure progress. |
| TC | Transition Coordinator — develops the original SMARTAR Goals in the SMARTAR Goal Builder. |
| BSC | Behaviour Support Educator. |
| ISE | Inclusive Support Educator. |
| EMS | The SA student management system that reports are uploaded to. |
| Allocation meeting | The meeting where students are allocated to a program/teacher. |
| Notice of Exclusion | The formal exclusion document setting the placement dates. |"""),
]

SEED_DOC_TT = {
    "slug": "teacher-tracking-checklist",
    "doc_code": "",
    "title": "Teacher Tracking Checklist",
    "subtitle": "What gets recorded, where, and when — daily, weekly, each placement and each term",
    "intro": "This checklist pulls every student-tracking and record-keeping expectation from **CLC 2026.8 Daily Work Expectations** and the **Teacher Case Management Process** into one place, sorted by how often it happens. It applies to **every teacher in every program**. **If it isn't recorded, it didn't happen.**",
    "category": "Policies & Expectations",
    "sort_order": 3,
    "is_published": True,
}

SEED_SECTIONS_TT = [
    ("Every day — start of day", """- ☐ **By 8:30am:** Staff Bulletin checked on the staff portal, emails checked, phone calls made or returned.
- ☐ **By 9:30am:** for every absent student, ring the caregiver and **record the reason on EMS**. All absences must be investigated and explained.
- ☐ Late arrivals and early finishes noted so attendance in the **Behaviour Support tool** matches what happened."""),
    ("Every day — as it happens", """Record at the time, not at the end of the week.
- ☐ **Minor incident** → **Quick Incident Log** on the staff portal. It enters the Behaviour Support tool automatically — no second step.
- ☐ **ABCH / Critical Incident** → **C.I. Bot** (preferred) or the Word template → **ABCH Report Formatter** → post to the **Teams ABCH channel** and tag **@Manager and @TC**. Same day.
- ☐ **Any contact** with families, schools, SSS or agencies — call, email, text or conversation, however brief → **Communication Log** on the staff portal (date, who, method, summary).
- ☐ **Any meeting** — TAC, Transition, Review — face-to-face, phone or email → documented and **uploaded to the student file**.
- ☐ **Medication** given → medication log completed at the correct time. If given at a different time to the plan → medication error log, and inform the Site Manager and parent.
- ☐ **Behaviour data tools** in use for a student (e.g. **Scatter Plot Tracker**, **Interval Support Tracker**) → filled in each session they apply to.
- ☐ Stakeholder emails answered within **24–48 hours**."""),
    ("Every day — end of day", """- ☐ Any incidents, contacts or meetings from today that weren't logged at the time → logged **before you leave**.
- ☐ Emails checked before leaving from 3:30pm.
- ☐ Student laptops/iPads locked away; program phone stored in the agreed location."""),
    ("Every week", """- ☐ **Team meeting** held and **minuted in the Team Meetings tool** — agreements recorded with who is actioning them. Last week's actions reviewed before new business.
- ☐ **Week A (student lens):** each student's goals, data and interventions discussed — bring the Behaviour Support, SMARTAR and attendance data to the meeting.
- ☐ **Week B (system lens):** curriculum and program improvement.
- ☐ Missed a meeting? Read the minutes and **action anything assigned to you**.
- ☐ **OneNote student file — Checklist tab** updated for every student: tick off what's been completed so anyone can see where the placement is up to.
- ☐ **SMARTAR / GAS progress** recorded for each student in **SGoal Quick Track**.
- ☐ **Wednesday:** read newly referred student information (expected by 3:30pm) and the **Staff Bulletin** (sent COB Tuesday) before the 3:10pm staff meeting. Come ready to share data and strategies.
- ☐ Offsite and student meetings for the coming week entered in the **CLC Calendar**; any Booking time entered in **NIT Bookings**."""),
    ("Each student placement — milestones", """Full detail is in the **Teacher Case Management Process** document. The tracking points are:
| When | What is recorded | Where |
| --- | --- | --- |
| Before arrival | Student Information and Original SMARTAR Goals read; Review Meeting confirmed with TAC | OneNote student file |
| First weeks | Baseline assessments: Sounds-Write, Word Aware, Big Ideas in Number | Assessment Data / student file |
| First weeks | SMARTAR Goals amended with Leadership, converted to GAS | SMARTAR Goal Builder → copied to student file |
| Review meeting | Review Report (draft to Leadership → print); Exit meeting scheduled; transition timetable shared | Reporting, Scheduled Meetings, Transition Plan tabs |
| Transition | Transition timetable emailed to TAC, Leadership and Admin | Email + Transition Plan tab |
| Exit meeting | Transition Report (with attendance data attached); exit confirmed by all TAC | Reporting tab; report to student file |
| Conclusion | Transition Report sent to clc.admin281@schools.sa.edu.au for EMS upload | Email |
| Archiving | All documents compiled and handed to Admin | Checklist tab |
| Extension (only if needed) | Extension paperwork completed before the original dates lapse | Extension Requested tab |"""),
    ("Each term", """- ☐ **Term assessment data** entered for every student.
- ☐ Attendance concerns raised with leadership (see the Student Attendance Improvement Plan for ongoing non-attendance).
- ☐ **End of Term Checklist** completed and signed off on the staff portal."""),
    ("Quick reference — what goes where", """| What | Where | When |
| --- | --- | --- |
| Student absence reason | EMS | By 9:30am |
| Minor incident | Quick Incident Log | At the time |
| ABCH / Critical Incident | C.I. Bot → ABCH Report Formatter → Teams ABCH (@Manager @TC) | Same day |
| Contact with families, schools, agencies | Communication Log | At the time |
| Meetings (TAC, Review, Transition, Exit) | Student file | Same day |
| Medication given | Medication log | At the time |
| Scatter Plot / Interval data | Scatter Plot Tracker / Interval Support Tracker | Each session it applies |
| Team meeting minutes and actions | Team Meetings tool | Weekly |
| Case management progress | OneNote Checklist tab | Weekly, and as milestones happen |
| Goal progress | SGoal Quick Track | Weekly |
| Offsite meetings | CLC Calendar | Before the week |
| Term assessments | Assessment Data | Each term |
| End of term sign-off | End of Term Checklist | End of term |"""),
]

SEED_PACKS = [
    (SEED_DOC, SEED_SECTIONS),
    (SEED_DOC_CM, SEED_SECTIONS_CM),
    (SEED_DOC_TT, SEED_SECTIONS_TT),
]


def seed_starter_content():
    seeded, skipped = [], []
    for doc_meta, secs in SEED_PACKS:
        existing = sb.table("reference_documents").select("id").eq("slug", doc_meta["slug"]).execute().data
        if existing:
            skipped.append(doc_meta["title"])
            continue
        doc = sb.table("reference_documents").insert(doc_meta).execute().data[0]
        rows = [
            {"document_id": doc["id"], "title": t, "content": c, "sort_order": i + 1}
            for i, (t, c) in enumerate(secs)
        ]
        sb.table("reference_sections").insert(rows).execute()
        seeded.append(f"{doc_meta['title']} ({len(rows)} sections)")
    clear_caches()
    msg = []
    if seeded:
        msg.append("Seeded: " + "; ".join(seeded) + ".")
    if skipped:
        msg.append("Already existed (untouched): " + "; ".join(skipped) + ".")
    return bool(seeded), " ".join(msg)


# ------------------------------------------------------------------
# STAFF VIEW
# ------------------------------------------------------------------
def _group_by_category(docs):
    order, grouped = [], {}
    for d in docs:
        cat = d.get("category") or "Policies & Expectations"
        if cat not in grouped:
            grouped[cat] = []
            order.append(cat)
        grouped[cat].append(d)
    return order, grouped


def _render_document(doc):
    st.markdown(
        f"""<div class="ref-header">
        <h1>{doc.get('doc_code','')}&nbsp; {doc['title']}</h1>
        <p>{doc.get('subtitle','')}</p></div>""",
        unsafe_allow_html=True,
    )

    sections = fetch_sections(doc["id"])

    col1, col2 = st.columns([3, 1])
    with col2:
        if sections:
            st.download_button(
                "⬇️ Download full document (Word)",
                data=build_docx(doc, sections),
                file_name=f"{(doc.get('doc_code','') + '_' + doc['title']).strip('_').replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key=f"dl_{doc['id']}",
            )
    with col1:
        if doc.get("intro"):
            intro_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", doc["intro"])
            st.markdown(f"<div class='ref-intro'>{intro_html}</div>", unsafe_allow_html=True)

    if not sections:
        st.info("This document has no sections yet.")
        return

    expand_all = st.toggle("Expand all sections", value=False, key=f"exp_{doc['id']}")
    for sec in sections:
        with st.expander(sec["title"], expanded=expand_all):
            st.markdown(sec.get("content") or "_(empty)_")

    upd = doc.get("updated_at", "")
    if upd:
        st.caption(f"Portal version is the current version. Last updated: {upd[:10]}")


def _highlight(text, query):
    return re.sub(f"({re.escape(query)})", r"**\1**", text, flags=re.IGNORECASE)


def _anthropic_key():
    for k in ("ANTHROPIC_API_KEY", "anthropic_api_key"):
        try:
            key = st.secrets.get(k)
        except Exception:
            key = None
        if key:
            return key
    return None


def _ai_find_sections(question, candidates, top_n=3):
    """candidates: list of (doc, sec) tuples already fetched.
    Asks Claude which sections best answer the question, returns the
    matching (doc, sec) tuples in ranked order (never invents wording —
    only picks from what's already stored). Returns (results, error)."""
    api_key = _anthropic_key()
    if not api_key:
        return None, "No ANTHROPIC_API_KEY found in secrets — add one to enable AI search."
    if not candidates:
        return [], None

    try:
        import anthropic
    except ImportError:
        return None, "The 'anthropic' package isn't installed — add it to requirements.txt."

    index_lines = []
    for i, (doc, sec) in enumerate(candidates):
        excerpt = (sec.get("content") or "").replace("\n", " ")[:220]
        index_lines.append(f"{i}. [{doc['title']} → {sec['title']}] {excerpt}")
    index_text = "\n".join(index_lines)

    prompt = (
        "Staff are searching a policy reference tool. Below is a numbered index of section "
        "titles and short excerpts. Given the staff member's question, return ONLY a JSON "
        f"array (no other text) of up to {top_n} index numbers for the sections most likely "
        "to contain the answer, ordered most relevant first. If nothing is relevant, return [].\n\n"
        f"Question: \"{question}\"\n\nIndex:\n{index_text}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "text", None)).strip()
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        idxs = json.loads(text)
        picked = [candidates[i] for i in idxs if isinstance(i, int) and 0 <= i < len(candidates)]
        return picked, None
    except Exception as e:
        return None, f"AI search failed ({e})."


def _apply_deep_link(docs):
    """Lets a portal tile jump straight into a document or category via
    URL query params, e.g. ?doc=daily-work-expectations or
    ?category=DfE%20Procedures. Applied once per session so the normal
    '← All documents' / '← All categories' back buttons still work
    afterwards without the link re-triggering."""
    if "ref_qp_applied" in st.session_state:
        return
    st.session_state["ref_qp_applied"] = True

    qp_doc = st.query_params.get("doc")
    if isinstance(qp_doc, list):
        qp_doc = qp_doc[0] if qp_doc else None
    qp_cat = st.query_params.get("category")
    if isinstance(qp_cat, list):
        qp_cat = qp_cat[0] if qp_cat else None

    if qp_doc:
        match = next((d for d in docs if d.get("slug") == qp_doc), None)
        if match:
            st.session_state["ref_selected_doc_id"] = match["id"]
        return

    if qp_cat:
        cat_docs = [d for d in docs if (d.get("category") or "Policies & Expectations") == qp_cat]
        if len(cat_docs) == 1:
            # Only one document in this category — skip the card grid and open it directly.
            st.session_state["ref_selected_doc_id"] = cat_docs[0]["id"]
        elif cat_docs:
            st.session_state["ref_category_filter"] = qp_cat


def staff_view():
    docs = fetch_documents()
    if not docs:
        st.info("No documents published yet. An administrator can seed or add documents in the Admin tab.")
        return

    _apply_deep_link(docs)

    doc_labels = {f"{d.get('doc_code','')} {d['title']}".strip(): d for d in docs}
    scope_choice = st.selectbox("Search in", ["All documents"] + list(doc_labels.keys()), key="ref_search_scope")

    def scoped_sections():
        if scope_choice == "All documents":
            out = []
            for d in docs:
                out.extend((d, sec) for sec in fetch_sections(d["id"]))
            return out
        scope_doc = doc_labels[scope_choice]
        return [(scope_doc, sec) for sec in fetch_sections(scope_doc["id"])]

    tab_kw, tab_ai = st.tabs(["🔎 Keyword search", "🤖 Ask a question"])

    searched = False

    with tab_kw:
        query = st.text_input(
            "Search for specific wording or a topic",
            placeholder="e.g. legislative limits, appeal timeframes, take-home",
        )
        if query.strip():
            searched = True
            q = query.strip().lower()
            results = [
                (doc, sec) for doc, sec in scoped_sections()
                if q in f"{sec['title']}\n{sec.get('content','')}".lower()
            ]
            if not results:
                st.info(f"No matches for “{query}”" + ("" if scope_choice == "All documents" else f" in {scope_choice}") + ".")
            else:
                st.caption(f"{len(results)} matching section(s):")
                for doc, sec in results:
                    label = sec["title"] if scope_choice != "All documents" else \
                        f"{doc.get('doc_code','')} {doc['title']} → {sec['title']}".strip()
                    with st.expander(label):
                        st.markdown(_highlight(sec.get("content") or "_(empty)_", query))
                        if st.button("Open full document →", key=f"kwopen_{doc['id']}_{sec['id']}"):
                            _open_document(doc["id"])

    with tab_ai:
        st.caption("Ask in plain language — the AI points you to the matching section(s); it doesn't rewrite the wording.")
        question = st.text_input(
            "Your question",
            placeholder="e.g. How many days can a student be suspended for?",
            key="ref_ai_question",
        )
        if st.button("Find the answer", key="ref_ai_go") and question.strip():
            searched = True
            candidates = scoped_sections()
            with st.spinner("Searching…"):
                picked, err = _ai_find_sections(question.strip(), candidates)
            if err:
                st.error(err)
            elif not picked:
                st.info("Couldn't find a section that answers that — try rephrasing, or use keyword search.")
            else:
                st.caption(f"Best match{'es' if len(picked) > 1 else ''}:")
                for i, (doc, sec) in enumerate(picked):
                    label = sec["title"] if scope_choice != "All documents" else \
                        f"{doc.get('doc_code','')} {doc['title']} → {sec['title']}".strip()
                    with st.expander(label, expanded=(i == 0)):
                        st.markdown(sec.get("content") or "_(empty)_")
                        if st.button("Open full document →", key=f"aiopen_{doc['id']}_{sec['id']}"):
                            _open_document(doc["id"])

    if searched:
        st.divider()
        return

    selected_id = st.session_state.get("ref_selected_doc_id")
    if selected_id:
        doc = next((d for d in docs if d["id"] == selected_id), None)
        if doc is None:
            st.session_state.pop("ref_selected_doc_id", None)
            st.rerun()
        if st.button("← All documents"):
            st.session_state.pop("ref_selected_doc_id", None)
            st.rerun()
        _render_document(doc)
        return

    cat_order, grouped = _group_by_category(docs)
    active_filter = st.session_state.get("ref_category_filter")
    if active_filter and active_filter in cat_order:
        if st.button("← All categories"):
            st.session_state.pop("ref_category_filter", None)
            st.rerun()
        cat_order = [active_filter]
    else:
        st.caption("Browse by document type, or use search above.")

    for cat in cat_order:
        st.markdown(f"<div class='cat-heading'>{_category_icon(cat)} {cat}</div>", unsafe_allow_html=True)
        cat_docs = grouped[cat]
        cols = st.columns(3)
        for i, doc in enumerate(cat_docs):
            with cols[i % 3]:
                _doc_card(doc)


CATEGORY_ICONS = {
    "Policies & Expectations": "📋",
    "DfE Procedures": "⚖️",
    "Role Expectations": "🧑‍🏫",
}


def _category_icon(cat):
    return CATEGORY_ICONS.get(cat, "📁")


def _open_document(doc_id):
    st.session_state["ref_selected_doc_id"] = doc_id
    st.rerun()


def _doc_card(doc):
    section_count = len(fetch_sections(doc["id"]))
    updated = (doc.get("updated_at") or "")[:10]
    meta_bits = [f"{section_count} section{'s' if section_count != 1 else ''}"]
    if updated:
        meta_bits.append(f"updated {updated}")
    with st.container(border=True):
        if doc.get("doc_code"):
            st.markdown(f"<div class='doc-card-code'>{doc['doc_code']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='doc-card-title'>{doc['title']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='doc-card-sub'>{doc.get('subtitle') or ''}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='doc-card-meta'>{' · '.join(meta_bits)}</div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Open →", key=f"open_{doc['id']}", use_container_width=True):
                _open_document(doc["id"])
        with b2:
            if section_count:
                st.download_button(
                    "⬇️ Word",
                    data=_docx_bytes(doc["id"], doc.get("updated_at") or ""),
                    file_name=_docx_filename(doc),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"carddl_{doc['id']}",
                )


def _docx_filename(doc):
    return f"{(doc.get('doc_code','') + '_' + doc['title']).strip('_').replace(' ', '_')}.docx"


@st.cache_data(ttl=60)
def _docx_bytes(doc_id, updated_at):
    """Word file for one document, cached per version (updated_at)."""
    doc = next((d for d in fetch_documents(include_unpublished=True) if d["id"] == doc_id), None)
    if not doc:
        return b""
    return build_docx(doc, fetch_sections(doc_id))


# ------------------------------------------------------------------
# ADMIN VIEW
# ------------------------------------------------------------------
def _unique_slug(title, existing_docs):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "document"
    existing = {d["slug"] for d in existing_docs}
    slug = base
    n = 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    return slug


def admin_view():
    if not admin_unlocked():
        return

    st.success("Admin unlocked — changes save straight to the portal for all staff.")
    if st.session_state.get("ref_flash"):
        st.success(st.session_state.pop("ref_flash"))

    docs = fetch_documents(include_unpublished=True)
    existing_cats = sorted({d.get("category") or "Policies & Expectations" for d in docs}) or ["Policies & Expectations"]

    with st.expander("➕ Add a new document / seed starter content"):
        c1, c2 = st.columns(2)
        with c1:
            new_code = st.text_input("Doc code (e.g. CLC 2026.8)", key="nd_code")
            new_title = st.text_input("Title", key="nd_title")
            new_sub = st.text_input("Subtitle", key="nd_sub")
            cat_choice = st.selectbox("Category", existing_cats + ["+ New category…"], key="nd_cat_choice")
            if cat_choice == "+ New category…":
                new_cat = st.text_input("New category name", key="nd_cat_new", placeholder="e.g. Role Expectations")
            else:
                new_cat = cat_choice
            if st.button("Create document"):
                if new_title.strip() and new_cat.strip():
                    slug = _unique_slug(new_title, docs)
                    sb.table("reference_documents").insert(
                        {"slug": slug, "doc_code": new_code, "title": new_title.strip(),
                         "subtitle": new_sub, "category": new_cat.strip(),
                         "sort_order": len(docs) + 1, "is_published": False}
                    ).execute()
                    clear_caches(); st.rerun()
                else:
                    st.error("Title and category are required.")
        with c2:
            st.markdown("**Starter content**")
            st.caption("Adds any starter document that isn't already in the portal. Existing documents are never touched.")
            if st.button("Seed: Daily Work Expectations + Case Management Process + Teacher Tracking Checklist"):
                ok, msg = seed_starter_content()
                (st.success if ok else st.info)(msg)
                if ok:
                    st.rerun()

    with st.expander("📤 Create a document from a Word upload"):
        st.caption(
            "Works best on .docx files that use Word's Heading styles for section titles — including every CLC "
            "document built for this portal. Bullet lists, bold text and tables convert automatically. You can "
            "edit anything afterwards."
        )
        parsed = _upload_parse_widget("up_new")
        if parsed:
            u_code = st.text_input("Doc code (optional, e.g. CLC 2026.1)", key="up_new_code")
            default_title = re.sub(r"[_\-]+", " ", parsed["filename"].rsplit(".", 1)[0]).strip()
            u_title = st.text_input("Title", value=default_title, key="up_new_title")
            u_sub = st.text_input("Subtitle", key="up_new_sub")
            u_cat_choice = st.selectbox("Category", existing_cats + ["+ New category…"], key="up_new_cat_choice")
            u_cat = st.text_input("New category name", key="up_new_cat_new", placeholder="e.g. Role Expectations") \
                if u_cat_choice == "+ New category…" else u_cat_choice
            u_intro = st.text_area("Intro / highlighted note (edit or clear the auto-detected text)",
                                    value=parsed["intro"], key="up_new_intro", height=100)
            if st.button("✅ Create document from upload", key="up_new_create"):
                if u_title.strip() and u_cat.strip():
                    slug = _unique_slug(u_title, docs)
                    docrow = sb.table("reference_documents").insert(
                        {"slug": slug, "doc_code": u_code, "title": u_title.strip(), "subtitle": u_sub,
                         "category": u_cat.strip(), "intro": u_intro, "sort_order": len(docs) + 1, "is_published": False}
                    ).execute().data[0]
                    rows = [
                        {"document_id": docrow["id"], "title": t, "content": c, "sort_order": i + 1}
                        for i, (t, c) in enumerate(parsed["sections"])
                    ]
                    sb.table("reference_sections").insert(rows).execute()
                    st.session_state.pop("up_new_parsed", None)
                    clear_caches()
                    st.success(f"Created '{u_title}' with {len(rows)} sections — unpublished. Review it below, then publish when ready.")
                    st.rerun()
                else:
                    st.error("Title and category are required.")

    if not docs:
        return

    labels = {}
    for cat in sorted({d.get("category") or "Policies & Expectations" for d in docs}):
        for d in [x for x in docs if (x.get("category") or "Policies & Expectations") == cat]:
            label = f"[{cat}]  {d.get('doc_code','')} {d['title']}".replace("  ", " ").strip()
            label += "" if d.get("is_published") else "  (unpublished)"
            labels[label] = d
    pick = st.selectbox("Edit document", list(labels.keys()), key="adm_doc")
    doc = labels[pick]

    with st.expander("Document settings", expanded=False):
        d_code = st.text_input("Doc code", value=doc.get("doc_code", ""), key=f"dc_{doc['id']}")
        d_title = st.text_input("Title", value=doc["title"], key=f"dt_{doc['id']}")
        d_sub = st.text_input("Subtitle", value=doc.get("subtitle", ""), key=f"ds_{doc['id']}")
        d_cat = st.text_input(
            "Category", value=doc.get("category") or "Policies & Expectations", key=f"dcat_{doc['id']}",
            help="Existing categories: " + ", ".join(existing_cats),
        )
        d_intro = st.text_area("Intro / highlighted note (optional, **bold** supported)", value=doc.get("intro", ""), key=f"di_{doc['id']}")
        d_pub = st.checkbox("Published (visible to staff)", value=bool(doc.get("is_published")), key=f"dp_{doc['id']}")
        cA, cB = st.columns(2)
        with cA:
            if st.button("Save document settings", key=f"dsave_{doc['id']}"):
                sb.table("reference_documents").update(
                    {"doc_code": d_code, "title": d_title, "subtitle": d_sub, "category": d_cat.strip() or "Policies & Expectations",
                     "intro": d_intro, "is_published": d_pub, "updated_at": _now()}
                ).eq("id", doc["id"]).execute()
                clear_caches(); st.success("Saved."); st.rerun()
        with cB:
            if st.button("🗑️ Delete this document (and all its sections)", key=f"ddel_{doc['id']}"):
                sb.table("reference_documents").delete().eq("id", doc["id"]).execute()
                clear_caches(); st.rerun()

    st.markdown("### Sections")
    sections = fetch_sections(doc["id"])

    with st.expander("🔁 Upload a new version (replaces this document's content)"):
        st.markdown(
            "Use this when the document has been updated in Word. The easiest way: **download the current "
            "version below, edit it in Word, then upload it here**. Each section title in the download is a "
            "Word *Heading 2* — keep new section titles in that style so they're picked up."
        )
        st.download_button(
            f"⬇️ Download current version ({len(sections)} sections) — keep as a backup",
            data=build_docx(doc, sections) if sections else b"",
            file_name=_docx_filename(doc).replace(".docx", "_backup.docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            disabled=not sections,
            key=f"rep_backup_{doc['id']}",
        )
        rp = _upload_parse_widget(f"up_rep_{doc['id']}")
        if rp:
            new_intro = rp["intro"]
            if new_intro:
                new_intro = "\n".join(l[2:] if l.startswith("> ") else l for l in new_intro.splitlines())
            replace_intro = st.checkbox(
                "Also replace the intro / highlighted note with the text found before the first section",
                value=bool(new_intro), key=f"rep_intro_{doc['id']}",
            )
            if replace_intro:
                new_intro = st.text_area("New intro", value=new_intro, key=f"rep_intro_txt_{doc['id']}", height=100)
            confirm = st.checkbox(
                f"I understand this replaces all {len(sections)} current section(s) with the "
                f"{len(rp['sections'])} section(s) from {rp['filename']}.",
                key=f"rep_confirm_{doc['id']}",
            )
            if st.button("✅ Replace with new version", key=f"rep_go_{doc['id']}", disabled=not confirm, type="primary"):
                rows = [
                    {"document_id": doc["id"], "title": t, "content": c, "sort_order": i + 1}
                    for i, (t, c) in enumerate(rp["sections"])
                ]
                # Insert the new sections first, then remove the old ones, so a
                # failed insert never leaves the document empty.
                old_ids = [s["id"] for s in sections]
                sb.table("reference_sections").insert(rows).execute()
                for sid in old_ids:
                    sb.table("reference_sections").delete().eq("id", sid).execute()
                upd = {"updated_at": _now()}
                if replace_intro:
                    upd["intro"] = new_intro
                sb.table("reference_documents").update(upd).eq("id", doc["id"]).execute()
                st.session_state.pop(f"up_rep_{doc['id']}_parsed", None)
                clear_caches()
                st.session_state["ref_flash"] = f"Replaced — '{doc['title']}' now has {len(rows)} section(s). Staff see the new version straight away."
                st.rerun()

    with st.expander("📤 Add sections from a Word upload"):
        st.caption("Parses a Word document and appends the detected sections to the end of this document.")
        parsed2 = _upload_parse_widget(f"up_add_{doc['id']}")
        if parsed2 and st.button("✅ Append parsed sections to this document", key=f"up_add_btn_{doc['id']}"):
            start = (sections[-1]["sort_order"] + 1) if sections else 1
            rows = [
                {"document_id": doc["id"], "title": t, "content": c, "sort_order": start + i}
                for i, (t, c) in enumerate(parsed2["sections"])
            ]
            sb.table("reference_sections").insert(rows).execute()
            sb.table("reference_documents").update({"updated_at": _now()}).eq("id", doc["id"]).execute()
            st.session_state.pop(f"up_add_{doc['id']}_parsed", None)
            clear_caches()
            st.success(f"Added {len(rows)} section(s).")
            st.rerun()

    for idx, sec in enumerate(sections):
        with st.expander(f"{idx+1}. {sec['title']}"):
            s_title = st.text_input("Section title", value=sec["title"], key=f"st_{sec['id']}")
            s_content = st.text_area(
                "Content — '- ' for bullets, **bold**, '> ' for a highlighted note",
                value=sec.get("content", ""), height=260, key=f"sc_{sec['id']}",
            )
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("💾 Save", key=f"ss_{sec['id']}"):
                    sb.table("reference_sections").update(
                        {"title": s_title, "content": s_content, "updated_at": _now()}
                    ).eq("id", sec["id"]).execute()
                    sb.table("reference_documents").update({"updated_at": _now()}).eq("id", doc["id"]).execute()
                    clear_caches(); st.success("Saved."); st.rerun()
            with c2:
                if idx > 0 and st.button("⬆️ Move up", key=f"su_{sec['id']}"):
                    above = sections[idx - 1]
                    sb.table("reference_sections").update({"sort_order": above["sort_order"]}).eq("id", sec["id"]).execute()
                    sb.table("reference_sections").update({"sort_order": sec["sort_order"]}).eq("id", above["id"]).execute()
                    clear_caches(); st.rerun()
            with c3:
                if idx < len(sections) - 1 and st.button("⬇️ Move down", key=f"sd_{sec['id']}"):
                    below = sections[idx + 1]
                    sb.table("reference_sections").update({"sort_order": below["sort_order"]}).eq("id", sec["id"]).execute()
                    sb.table("reference_sections").update({"sort_order": sec["sort_order"]}).eq("id", below["id"]).execute()
                    clear_caches(); st.rerun()
            with c4:
                if st.button("🗑️ Delete", key=f"sx_{sec['id']}"):
                    sb.table("reference_sections").delete().eq("id", sec["id"]).execute()
                    clear_caches(); st.rerun()

    st.markdown("#### Add section")
    a_title = st.text_input("New section title", key="ns_title")
    a_content = st.text_area("New section content", key="ns_content", height=160)
    if st.button("Add section"):
        if a_title.strip():
            sb.table("reference_sections").insert(
                {"document_id": doc["id"], "title": a_title.strip(), "content": a_content,
                 "sort_order": (sections[-1]["sort_order"] + 1) if sections else 1}
            ).execute()
            clear_caches(); st.rerun()
        else:
            st.error("Section title required.")


# ------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------
st.title("📖 Staff Reference")
st.caption("Policies and expectations — live, current, and downloadable. The portal version is always the current version.")

tab_staff, tab_admin = st.tabs(["📚 View documents", "🔐 Admin"])
with tab_staff:
    staff_view()
with tab_admin:
    admin_view()
