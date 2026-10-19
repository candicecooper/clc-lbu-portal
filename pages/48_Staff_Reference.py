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
IMAGES IN SECTIONS: put a line on its own like
    ![Quick Log tile](tile_quick_log.png)
and place the PNG in the repo at data/staff_reference_images/. Images
show on the page and in the Word download, and survive a Word
download → edit → "Upload a new version" round trip.

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
    _print_bytes.clear()


def _now():
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Images inside section content: a line on its own like
#   ![Quick Log tile](tile_quick_log.png)
# Files live in the repo at data/staff_reference_images/.
# Screenshots are captured at 2x, so they display at half pixel width.
# ------------------------------------------------------------------
from pathlib import Path

IMG_LINE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)\s]+)\)\s*$")
_IMG_DIRS = [
    Path(__file__).resolve().parent.parent / "data" / "staff_reference_images",
    Path("data") / "staff_reference_images",
]


def image_path(fname):
    """Returns the image BYTES for a filename: from data/staff_reference_images/
    if present (so new/updated images can be added there), otherwise from the
    tile images built into this file. None if neither has it."""
    fname = Path(fname).name  # never allow paths outside the folder
    for d in _IMG_DIRS:
        f = d / fname
        if f.is_file():
            try:
                return f.read_bytes()
            except Exception:
                pass
    b64 = BUILTIN_IMAGES.get(fname)
    if b64:
        import base64
        return base64.b64decode(b64)
    return None


def image_display_width(data):
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            return max(40, min(700, im.width // 2))
    except Exception:
        return 334


def render_content(text):
    """st.markdown for text, st.image for image lines."""
    buf = []

    def flush():
        if any(l.strip() for l in buf):
            st.markdown("\n".join(buf))
        buf.clear()

    for line in (text or "").splitlines():
        m = IMG_LINE.match(line)
        if not m:
            buf.append(line)
            continue
        flush()
        path = image_path(m.group(2))
        if path:
            st.image(path, width=image_display_width(path))
        else:
            st.caption(f"🖼️ {m.group(1) or m.group(2)} (image not found in data/staff_reference_images)")
    flush()
    if not (text or "").strip():
        st.markdown("_(empty)_")


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
            m = IMG_LINE.match(line)
            if m:
                path = image_path(m.group(2))
                if d.paragraphs:  # keep a lead-in line on the same page as its image
                    d.paragraphs[-1].paragraph_format.keep_with_next = True
                p = d.add_paragraph()
                if path:
                    from docx.shared import Inches
                    pic = p.add_run().add_picture(io.BytesIO(path), width=Inches(image_display_width(path) / 96))
                    docpr = pic._inline.docPr
                    docpr.set("descr", Path(m.group(2)).name)   # filename — read back on upload
                    docpr.set("title", m.group(1))
                else:
                    add_runs(p, f"[image: {m.group(1) or m.group(2)}]")
                p.paragraph_format.space_after = Pt(3)
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
# PRINT LAYOUTS — landscape, column-based versions of specific documents
# for printing / pinning up. Built from the same live sections as the
# editable download, so portal edits flow through. The editable download
# (build_docx) is still the one used for the Word round trip; print
# versions are tagged and refused by the uploader.
# ------------------------------------------------------------------
PRINT_TAG = "clc-print-layout"

# Word is strict about the ORDER of child elements in table/cell/row
# properties ("unreadable content" otherwise), so insert in schema order.
_OX_ORDER = {
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize",
              "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar",
              "tblLook", "tblCaption", "tblDescription"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
             "textDirection", "tcFitText", "vAlign", "hideMark"],
    "trPr": ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit", "trHeight",
             "tblHeader", "tblCellSpacing", "jc", "hidden"],
}


def _ox_insert(parent, el):
    from docx.oxml.ns import qn
    pname = parent.tag.split("}")[1]
    order = _OX_ORDER[pname]
    name = el.tag.split("}")[1]
    for old in parent.findall(qn("w:" + name)):
        parent.remove(old)
    idx = order.index(name)
    for child in parent:
        cname = child.tag.split("}")[1]
        if cname in order and order.index(cname) > idx:
            child.addprevious(el)
            return
    parent.append(el)


def build_tracking_print_docx(doc_row, sections) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_BREAK
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    TEAL, TEAL_DARK, TEAL_LIGHT = "00695C", "004D40", "E0F2F1"
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    INK = RGBColor(0x1A, 0x1A, 0x1A)
    GREY = RGBColor(0x59, 0x59, 0x59)
    # column header colours, matched to the portal's own section colours
    COL = {"start": "00695C", "day": "00796B", "end": "004D40",
           "week": "00695C", "term": "004D40"}

    d = Document()
    d.core_properties.keywords = PRINT_TAG
    d.core_properties.title = doc_row["title"]
    sec0 = d.sections[0]
    sec0.orientation = WD_ORIENT.LANDSCAPE
    sec0.page_width, sec0.page_height = Cm(29.7), Cm(21.0)
    sec0.top_margin = sec0.bottom_margin = Cm(1.1)
    sec0.left_margin = sec0.right_margin = Cm(1.3)
    usable_in = (29.7 - 2.6) / 2.54

    st_ = d.styles["Normal"]
    st_.font.name = "Calibri"; st_.font.size = Pt(9.5)
    st_.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    st_.paragraph_format.space_after = Pt(0)

    # footer on every page
    fp = sec0.footer.paragraphs[0]
    acst = datetime.now(timezone(timedelta(hours=9, minutes=30)))
    fr = fp.add_run(f"CLC-LBU  |  {doc_row['title']}  |  Printed from the Staff Portal {acst.strftime('%d/%m/%Y')} "
                    "— the portal version is always current.")
    fr.font.size = Pt(7.5); fr.font.color.rgb = GREY

    def shade_cell(cell, fill):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), fill)
        _ox_insert(tcPr, shd)

    def cell_margins(cell, top=60, bottom=60, left=110, right=110):
        tcPr = cell._tc.get_or_add_tcPr()
        mar = OxmlElement("w:tcMar")
        for k, v in (("top", top), ("bottom", bottom), ("start", left), ("end", right)):
            e = OxmlElement(f"w:{k}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
        _ox_insert(tcPr, mar)

    def borders(table, color="B2DFDB", size=6, inside=True):
        tblPr = table._tbl.tblPr
        b = OxmlElement("w:tblBorders")
        edges = ["top", "left", "bottom", "right"] + (["insideH", "insideV"] if inside else [])
        for e in edges:
            el = OxmlElement(f"w:{e}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), str(size))
            el.set(qn("w:color"), color); b.append(el)
        _ox_insert(tblPr, b)

    def caption(table, tag):
        el = OxmlElement("w:tblCaption"); el.set(qn("w:val"), tag)
        _ox_insert(table._tbl.tblPr, el)

    def fixed_widths(table, widths_in):
        table.autofit = False
        tblPr = table._tbl.tblPr
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); _ox_insert(tblPr, lay)
        grid = table._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths_in):
            gc.set(qn("w:w"), str(int(w * 1440)))
        for row in table.rows:
            for c, w in zip(row.cells, widths_in):
                c.width = Inches(w)

    def runs(par, text, size=None, color=None, bold_all=False, italic=False):
        for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
            if not chunk:
                continue
            for j, part in enumerate(re.split(r"(?<!\*)\*([^*]+)\*(?!\*)", chunk)):
                if not part:
                    continue
                r = par.add_run(part)
                r.font.bold = bold_all or (i % 2 == 1)
                r.font.italic = italic or (j % 2 == 1)
                if size: r.font.size = Pt(size)
                if color is not None: r.font.color.rgb = color

    def heading_cell(cell, text, fill, sub=None):
        shade_cell(cell, fill); cell_margins(cell, 70, 70)
        p = cell.paragraphs[0]
        runs(p, text.upper(), size=10.5, color=WHITE, bold_all=True)
        if sub:
            p2 = cell.add_paragraph(); runs(p2, sub, size=8.5, color=RGBColor(0xE0, 0xF2, 0xF1), italic=True)

    def checklist_item(cell, text, first, size=9.5):
        p = cell.paragraphs[0] if first and not cell.paragraphs[0].text else cell.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Inches(0.22); pf.first_line_indent = Inches(-0.22)
        pf.space_before = Pt(0 if first else 5); pf.space_after = Pt(0)
        box = p.add_run("☐  "); box.font.size = Pt(size + 1.5); box.font.color.rgb = RGBColor(0x00, 0x69, 0x5C)
        runs(p, text, size=size, color=INK)
        return p

    def body_lines(content):
        """Split section content into (notes, items): notes are plain lines,
        items are '- ' lines with any leading ☐ stripped."""
        notes, items = [], []
        for ln in (content or "").splitlines():
            t = ln.strip()
            if not t:
                continue
            if t.startswith("- "):
                items.append(re.sub(r"^☐\s*", "", t[2:].strip()))
            else:
                notes.append(t)
        return notes, items

    def fill_column(cell, content, size=9.5):
        notes, items = body_lines(content)
        first = True
        for n in notes:
            p = cell.paragraphs[0] if first else cell.add_paragraph()
            runs(p, n.lstrip("> "), size=size - 0.5, color=GREY, italic=True)
            p.paragraph_format.space_after = Pt(3)
            first = False
        for it in items:
            checklist_item(cell, it, first, size); first = False

    def band(text, sub=None):
        t = d.add_table(rows=1, cols=1); borders(t, TEAL, 0, inside=False)
        c = t.rows[0].cells[0]; shade_cell(c, TEAL); cell_margins(c, 90, 90, 160, 160)
        p = c.paragraphs[0]
        r = p.add_run("COWANDILLA LEARNING CENTRE  |  LEARNING & BEHAVIOUR UNIT")
        r.font.size = Pt(7.5); r.font.bold = True; r.font.color.rgb = RGBColor(0xB2, 0xDF, 0xDB)
        p2 = c.add_paragraph(); runs(p2, text, size=20, color=WHITE, bold_all=True)
        if sub:
            p3 = c.add_paragraph(); runs(p3, sub, size=9.5, color=RGBColor(0xE0, 0xF2, 0xF1), italic=True)

    def section_heading(text, page_break=False):
        p = d.add_paragraph()
        if page_break:
            p.add_run().add_break(WD_BREAK.PAGE)
        r = p.add_run(text); r.font.size = Pt(14); r.font.bold = True
        r.font.color.rgb = RGBColor(0x00, 0x4D, 0x40)
        p.paragraph_format.space_before = Pt(2 if page_break else 10); p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        return p

    def spacer(pt=6):
        p = d.add_paragraph(); p.paragraph_format.space_after = Pt(0)
        r = p.add_run(""); p.paragraph_format.line_spacing = Pt(pt)

    def md_table(lines, widths=None, size=9):
        rows = []
        for ln in lines:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(cells)
        if not rows:
            return
        n = max(len(r) for r in rows)
        t = d.add_table(rows=0, cols=n); borders(t)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for ci in range(n):
                c = cells[ci]; cell_margins(c, 45, 45)
                txt = row[ci] if ci < len(row) else ""
                p = c.paragraphs[0]
                if ri == 0:
                    shade_cell(c, TEAL); runs(p, txt, size=size + 0.5, color=WHITE, bold_all=True)
                else:
                    if ri % 2 == 0: shade_cell(c, "F1F8F7")
                    runs(p, txt, size=size, color=INK, bold_all=(ci == 0))
        # repeat header row if the table breaks across pages
        trPr = t.rows[0]._tr.get_or_add_trPr()
        h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); _ox_insert(trPr, h)
        for row in t.rows:  # don't split a row across pages
            trPr = row._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); _ox_insert(trPr, cs)
        if widths:
            fixed_widths(t, widths)
        return t

    # ---- find the sections by title (falls back gracefully if renamed) ----
    def norm(t):
        return re.sub(r"[^a-z]+", " ", t.lower()).strip()

    by = {}
    for sec in sections:
        k = norm(sec["title"])
        if k.startswith("each day") and "start" in k: by["start"] = sec
        elif k.startswith("each day") and "end" in k: by["end"] = sec
        elif k == "each day" or k.startswith("each day during") or k.startswith("during the day"): by["day"] = sec
        elif k.startswith("each week"): by["week"] = sec
        elif k.startswith("each term"): by["term"] = sec
        elif "milestone" in k: by["milestones"] = sec
        elif k.startswith("quick reference"): by["quickref"] = sec
        elif k.startswith("finding the tools"): by["tools"] = sec
    used = {id(v) for v in by.values()}
    others = [s_ for s_ in sections if id(s_) not in used]
    key_of = {id(v): k for k, v in by.items()}
    meta = {"v": 1, "order": [], "note_in_header": {}}
    oi_ = 0
    for s_ in sections:
        if id(s_) in key_of:
            meta["order"].append([key_of[id(s_)], s_["title"]])
        else:
            meta["order"].append([f"other:{oi_}", s_["title"]]); oi_ += 1

    # ================= PAGE 1 — EACH DAY =================
    band(doc_row["title"], doc_row.get("subtitle"))
    if doc_row.get("intro"):
        t = d.add_table(rows=1, cols=1); borders(t, TEAL_LIGHT, 0, inside=False)
        c = t.rows[0].cells[0]; shade_cell(c, TEAL_LIGHT); cell_margins(c, 60, 60, 160, 160)
        runs(c.paragraphs[0], doc_row["intro"], size=9, color=INK)
        caption(t, "clc:intro")
    spacer(8)

    day_cols = [k for k in ("start", "day", "end") if k in by]
    if day_cols:
        section_heading("Each Day")
        weights = {"start": 0.29, "day": 0.42, "end": 0.29}
        tot = sum(weights[k] for k in day_cols)
        widths = [usable_in * weights[k] / tot for k in day_cols]
        labels = {"start": ("Start of the day", "Before students arrive"),
                  "day": ("During the day", None),
                  "end": ("End of the day", "Before you leave")}
        t = d.add_table(rows=2, cols=len(day_cols)); borders(t)
        caption(t, "clc:day:" + ",".join(day_cols))
        for ci, k in enumerate(day_cols):
            notes, _ = body_lines(by[k]["content"])
            meta["note_in_header"][k] = bool(notes)
            heading_cell(t.rows[0].cells[ci], labels[k][0], COL[k], labels[k][1] if not notes else notes[0])
            c = t.rows[1].cells[ci]; cell_margins(c, 90, 90, 120, 120)
            content = by[k]["content"]
            if notes:  # first note already shown in the header
                content = "\n".join(l for l in content.splitlines() if l.strip() != notes[0])
            fill_column(c, content, size=9.5)
        fixed_widths(t, widths)

    # ================= PAGE 2 — EACH WEEK + EACH TERM =================
    if "week" in by or "term" in by:
        section_heading("Each Week  ·  Each Term", page_break=True)
        _, wk = body_lines(by["week"]["content"]) if "week" in by else ([], [])
        _, tm = body_lines(by["term"]["content"]) if "term" in by else ([], [])
        half = (len(wk) + 1) // 2
        cols = [("week", wk[:half]), ("week", wk[half:])] if wk else []
        if tm:
            cols.append(("term", tm))
        widths = [usable_in * w for w in ([0.35, 0.35, 0.30] if (wk and tm) else [0.5, 0.5])][:len(cols)]
        t = d.add_table(rows=2, cols=len(cols)); borders(t)
        caption(t, "clc:weekterm:" + ",".join(k for k, _ in cols))
        if wk:
            hc = t.rows[0].cells[0].merge(t.rows[0].cells[1]) if len(cols) >= 2 and cols[1][0] == "week" else t.rows[0].cells[0]
            heading_cell(hc, "Each Week", COL["week"], "Team meetings, records and planning")
        if tm:
            heading_cell(t.rows[0].cells[len(cols) - 1], "Each Term", COL["term"], "Assessment, attendance and sign-off")
        for ci, (_, items) in enumerate(cols):
            c = t.rows[1].cells[ci]; cell_margins(c, 90, 90, 120, 120)
            for ii, it in enumerate(items):
                checklist_item(c, it, ii == 0, size=9.5)
        fixed_widths(t, widths)

    # ================= MILESTONES =================
    if "milestones" in by:
        section_heading(by["milestones"]["title"], page_break=("week" not in by and "term" not in by))
        notes = [l.strip() for l in by["milestones"]["content"].splitlines() if l.strip() and not l.strip().startswith("|")]
        for n in notes:
            p = d.add_paragraph(); runs(p, n, size=9, color=GREY); p.paragraph_format.space_after = Pt(4)
        tl = [l for l in by["milestones"]["content"].splitlines() if l.strip().startswith("|")]
        caption(md_table(tl, widths=[usable_in * 0.16, usable_in * 0.56, usable_in * 0.28], size=9), "clc:milestones")

    # ================= QUICK REFERENCE =================
    if "quickref" in by:
        section_heading(by["quickref"]["title"], page_break=True)
        tl = [l for l in by["quickref"]["content"].splitlines() if l.strip().startswith("|")]
        caption(md_table(tl, widths=[usable_in * 0.30, usable_in * 0.42, usable_in * 0.28], size=9.5), "clc:quickref")

    # ================= FINDING THE TOOLS — one column per portal section =================
    if "tools" in by:
        section_heading(by["tools"]["title"], page_break=True)
        lines = by["tools"]["content"].splitlines()
        intro, groups, cur = [], [], None
        for ln in lines:
            m = IMG_LINE.match(ln)
            if m and Path(m.group(2)).name.startswith("section_"):
                cur = {"header": m, "lines": []}; groups.append(cur); continue
            if cur is None:
                if ln.strip(): intro.append(ln.strip())
            else:
                cur["lines"].append(ln)
        # anything after a bold "At the top of the portal" style line becomes its own column
        final = []
        for g in groups:
            split_at = next((i for i, l in enumerate(g["lines"]) if re.fullmatch(r"\*\*.+\*\*", l.strip())), None)
            if split_at is not None:
                final.append({"header": g["header"], "lines": g["lines"][:split_at]})
                final.append({"header": None, "title": g["lines"][split_at].strip().strip("*"), "lines": g["lines"][split_at + 1:]})
            else:
                final.append(g)
        for n in intro:
            p = d.add_paragraph(); runs(p, n, size=9, color=GREY); p.paragraph_format.space_after = Pt(4)
        if final:
            ncol = len(final)
            colw = usable_in / ncol
            img_w = min(3.2, colw - 0.3)
            t = d.add_table(rows=1, cols=ncol); borders(t, "FFFFFF", 0)
            caption(t, "clc:tools")
            for ci, g in enumerate(final):
                c = t.rows[0].cells[ci]; cell_margins(c, 40, 40, 80, 80)
                first = True

                def para():
                    nonlocal first
                    p = c.paragraphs[0] if first else c.add_paragraph()
                    first = False
                    return p

                def pic(m, width_in):
                    path = image_path(m.group(2))
                    p = para()
                    if path:
                        w = min(width_in, image_display_width(path) / 96)
                        pc = p.add_run().add_picture(io.BytesIO(path), width=Inches(w))
                        pc._inline.docPr.set("descr", Path(m.group(2)).name)
                        pc._inline.docPr.set("title", m.group(1))
                    else:
                        runs(p, f"[{m.group(1) or m.group(2)}]", size=9, color=GREY)
                    p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(1)

                if g.get("header") is not None:
                    pic(g["header"], img_w)
                else:
                    p = para(); runs(p, g["title"], size=12, color=RGBColor(0x1E, 0x29, 0x3B), bold_all=True)
                    p.paragraph_format.space_after = Pt(4)
                for ln in g["lines"]:
                    tt = ln.strip()
                    if not tt:
                        continue
                    m = IMG_LINE.match(tt)
                    if m:
                        pic(m, img_w - 0.05)
                    elif tt.startswith("> "):
                        p = para(); runs(p, tt[2:], size=8.5, color=RGBColor(0x00, 0x4D, 0x40), bold_all=True)
                        p.paragraph_format.space_before = Pt(3)
                    else:
                        p = para(); runs(p, tt, size=8.5, color=INK)
                        p.paragraph_format.left_indent = Inches(0.08)
            trPr = t.rows[0]._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); _ox_insert(trPr, cs)
            fixed_widths(t, [colw] * ncol)

    # ================= anything else, in order =================
    for oi, sec in enumerate(others):
        section_heading(sec["title"])
        notes, items = body_lines(sec["content"])
        for n in notes:
            if IMG_LINE.match(n) or n.startswith("|"):
                continue
            p = d.add_paragraph(); runs(p, n.lstrip("> "), size=9.5, color=INK)
        tl = [l for l in sec["content"].splitlines() if l.strip().startswith("|")]
        if tl:
            caption(md_table(tl), f"clc:other-table:{oi}")
        if items:
            t = d.add_table(rows=1, cols=1); c = t.rows[0].cells[0]
            caption(t, f"clc:other-items:{oi}")
            for ii, it in enumerate(items):
                checklist_item(c, it, ii == 0)

    # layout info (section titles/order) for reading an edited print version back in.
    # Written directly: python-docx caps this property at 255 chars, Word doesn't.
    _desc = d.core_properties._element.get_or_add_description()
    _desc.text = "CLCMETA" + json.dumps(meta, ensure_ascii=False)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def parse_tracking_print_docx(docx_doc):
    """Reads a (possibly Word-edited) print version back into
    (intro, [(title, content), ...]) using the table tags + saved titles."""
    from docx.oxml.ns import qn
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph

    _el = docx_doc.core_properties._element.find(
        "{http://purl.org/dc/elements/1.1/}description")
    raw = (_el.text if _el is not None else "") or ""
    if not raw.startswith("CLCMETA"):
        raise ValueError("this print version is missing its layout information — "
                         "download a fresh print or editable version from the portal and edit that")
    meta = json.loads(raw[len("CLCMETA"):])

    def para_md(p):
        """Runs → markdown, merging Word's arbitrary run splits; drops the ☐ box run."""
        segs = []
        for r in p.runs:
            t = r.text
            if not t or (t.strip() == "☐"):
                continue
            key = (bool(r.bold), bool(r.italic) and not r.bold)
            if segs and segs[-1][0] == key:
                segs[-1][1] += t
            else:
                segs.append([key, t])
        out = ""
        for (b, i), t in segs:
            core = t.strip()
            if not core:
                out += t; continue
            lead, trail = t[:len(t) - len(t.lstrip())], t[len(t.rstrip()):]
            out += lead + (f"**{core}**" if b else f"*{core}*" if i else core) + trail
        out = re.sub(r"^\s*☐\s*", "", out)
        return out.strip()

    def is_item(p):
        return p.text.lstrip().startswith("☐")

    def cell_items(cell, skip=0):
        notes, items = [], []
        for p in cell.paragraphs[skip:]:
            if not p.text.strip():
                continue
            md = para_md(p)
            if is_item(p):
                items.append(md)
            elif items:  # an Enter inside an item — join it back on
                items[-1] += " " + md
            else:
                notes.append(md)
        return notes, items

    def table_md(t):
        rows = [[para_md_cell(c) for c in r.cells] for r in t.rows]
        if not rows:
            return ""
        lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * len(rows[0])) + " |"]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join(lines)

    def para_md_cell(c):
        return " ".join(re.sub(r"^\*\*(.*)\*\*$", r"\1", para_md(p)) for p in c.paragraphs if p.text.strip())

    titles = {k: t for k, t in meta["order"]}
    content, intro = {}, ""
    body = docx_doc.element.body
    pending_notes, last_heading = [], None
    heading_keys = {t: k for k, t in meta["order"]}

    for ch in body.iterchildren():
        if ch.tag == qn("w:p"):
            p = DocxParagraph(ch, docx_doc)
            txt = p.text.strip()
            if not txt and not ch.xpath(".//wp:docPr"):
                continue
            if txt in heading_keys or txt == "Each Week  ·  Each Term" or txt == "Each Day":
                last_heading = heading_keys.get(txt); pending_notes = []
                continue
            if txt:
                pending_notes.append(para_md(p))
            continue
        if ch.tag != qn("w:tbl"):
            continue
        t = DocxTable(ch, docx_doc)
        cap = ch.xpath("./w:tblPr/w:tblCaption/@w:val")
        tag = cap[0] if cap else ""
        if tag == "clc:intro":
            intro = "\n".join(para_md(p) for p in t.rows[0].cells[0].paragraphs if p.text.strip())
        elif tag.startswith("clc:day:"):
            keys = tag.split(":", 2)[2].split(",")
            for ci, k in enumerate(keys):
                lines = []
                if meta["note_in_header"].get(k):
                    hp = [p for p in t.rows[0].cells[ci].paragraphs if p.text.strip()]
                    if len(hp) > 1:
                        lines.append(para_md(hp[1]).strip("*"))
                notes, items = cell_items(t.rows[1].cells[ci])
                lines += notes + [f"- ☐ {it}" for it in items]
                content[k] = "\n".join(lines)
        elif tag.startswith("clc:weekterm:"):
            keys = tag.split(":", 2)[2].split(",")
            wk, tm = [], []
            body_cells = t.rows[1]._tr.findall(qn("w:tc"))  # body row is never merged
            for ci, k in enumerate(keys):
                if ci >= len(body_cells):
                    break
                from docx.table import _Cell
                _, items = cell_items(_Cell(body_cells[ci], t))
                (wk if k == "week" else tm).extend(items)
            if wk: content["week"] = "\n".join(f"- ☐ {it}" for it in wk)
            if tm: content["term"] = "\n".join(f"- ☐ {it}" for it in tm)
        elif tag in ("clc:milestones", "clc:quickref"):
            k = tag.split(":")[1]
            lines = pending_notes + [table_md(t)]
            content[k] = "\n".join(lines); pending_notes = []
        elif tag == "clc:tools":
            lines = list(pending_notes); pending_notes = []
            for cell in t.rows[0].cells:
                lines.append("")
                for p in cell.paragraphs:
                    pics = p._p.xpath(".//wp:docPr")
                    if pics and not p.text.strip():
                        for dp in pics:
                            fn = Path(dp.get("descr") or "").name
                            if fn:
                                lines.append(f"![{dp.get('title') or ''}]({fn})")
                        continue
                    if not p.text.strip():
                        continue
                    md = para_md(p)
                    runs_ = [r for r in p.runs if r.text.strip()]
                    all_bold = runs_ and all(r.bold for r in runs_)
                    big = runs_ and runs_[0].font.size and runs_[0].font.size.pt >= 11.5
                    if all_bold and big:
                        lines.append(f"**{md.strip('*')}**")
                    elif all_bold:
                        lines.append(f"> {md.strip('*')}")
                    else:
                        lines.append(md)
            content["tools"] = "\n".join(lines).strip()
        elif tag.startswith("clc:other-items:"):
            k = "other:" + tag.split(":")[2]
            notes, items = cell_items(t.rows[0].cells[0])
            content[k] = "\n".join(pending_notes + notes + [f"- ☐ {it}" for it in items]).strip()
            pending_notes = []
        elif tag.startswith("clc:other-table:"):
            k = "other:" + tag.split(":")[2]
            content[k] = "\n".join([content.get(k, "")] + pending_notes + [table_md(t)]).strip()
            pending_notes = []

    sections = [(title, content.get(k, "")) for k, title in meta["order"] if content.get(k, "").strip()]
    return intro, sections


PRINT_LAYOUTS = {
    "teacher-tracking-checklist": ("🖨️ Print version (landscape)", build_tracking_print_docx),
}


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
    if PRINT_TAG in (doc.core_properties.keywords or ""):
        return parse_tracking_print_docx(doc)

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
        pics = block._p.xpath(".//wp:docPr")
        if pics and not block.text.strip():
            for dp in pics:
                fname = Path(dp.get("descr") or "").name
                if fname.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    target.append(f"![{dp.get('title') or ''}]({fname})")
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
            kind = lambda l: "-" if l.startswith("- ") else (">" if l.startswith("> ") else ("|" if l.startswith("|") else ("!" if l.startswith("![") else "p")))
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
        except ValueError as e:
            st.error(f"Can't use that file: {e}.")
            st.session_state.pop(f"{prefix}_parsed", None)
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
    ("Each Day — Start of the Day", """- ☐ **By 8:30am:** Sign in on arrival at the front office. Staff Bulletin checked on the staff portal, emails checked, phone calls made or returned.
- ☐ **By 9:30am: Attendance** — for every absent student, ring/text the caregiver and **record the reason on EMS**. All absences must be investigated and explained. Late arrivals and early finishes noted so attendance in the **Behaviour Support tool** matches what happened."""),
    ("Each Day", """Record each day, not at the end of the week.
- ☐ **Micro Behaviours:** in *Incident Management*. Record at least 1 micro behaviour for each student, each day.
- ☐ **ABCH / Critical Incident:** record Critical Incidents using the C.I. Bot or the Word Template. CI needs to be completed and finished by the end of the day or within 24 hours.
- ☐ **Communication:** record every communication in the **Communication Log** — any communication that has occurred (phone calls, emails, texts or face-to-face conversations) with families, school, SSS or agencies.
- ☐ **Any meeting:** TAC, Transition, Review (face-to-face, phone or email) documented and **uploaded to the student file**.
- ☐ **Behaviour data tools** in use for a student (e.g. **Scatter Plot Tracker**, **Interval Support Tracker**) filled in each session they apply to.
- ☐ Stakeholder **Emails** answered within **24–48 hours**. If on leave for over 2 working days, an automatic email response needs to be implemented.
- ☐ **Leaving Site:** please sign out and in at the front office as part of WH&S."""),
    ("Each Day — End of the Day", """- ☐ Any incidents, contacts or meetings from today that weren't logged at the time → logged **before you leave**.
- ☐ Emails checked before leaving from 3:30pm.
- ☐ Student laptops/iPads locked away; program phone stored in the agreed location.
- ☐ **Sign out** when leaving for the day at the front office."""),
    ("Each Week", """- ☐ **Team meeting** held and **minuted in the Team Meetings tool** — agreements recorded with who is actioning them. Last week's actions reviewed before new business.
- ☐ **Week A (student lens):** each student's goals, data and interventions discussed — bring the Behaviour Support, SMARTAR and attendance data to the meeting.
- ☐ **Week B (system lens):** curriculum and program improvement.
- ☐ Missed a meeting? Read the minutes and **action anything assigned to you**.
- ☐ **OneNote student file: Checklist tab** updated for every student — tick off what's been completed so anyone can see where the placement is up to.
- ☐ **SMARTAR / GAS progress** recorded for each student in **SGoal Quick Track**.
- ☐ **Wednesday:** read the Staff Bulletin (sent COB Tuesday) before the 3:10pm staff meeting.
- ☐ Offsite and student meetings for the coming week entered in the **Daily Bulletin**; Booking time entered in **NIT Bookings**."""),
    ("Each Student Placement — Milestones", """Full detail is in the **Teacher Case Management Process** document. The tracking points are:
| When | What is Recorded | Where |
| --- | --- | --- |
| Before student starts | Student Information and Original SMARTAR Goals read; Review Meeting confirmed with TAC | OneNote student file |
| Within the first weeks | Baseline assessments completed: Sounds-Write, Word Aware, Big Ideas in Number | Assessment Data / student file |
| Within the first weeks | SMARTAR Goals amended with Leadership, converted to GAS | SMARTAR Goal Builder → copied to student file |
| Review Meeting | Review Report: draft report emailed to Leadership 24hrs before the meeting; once sent back to you, print and have ready to share with TAC. At meeting: exit meeting scheduled; transition timetable agreed upon and shared; extension (if applicable) discussed and information shared around timelines and expectations | Reporting, Scheduled Meetings and Transition Plan tabs |
| Transition Timetable | Transition timetable emailed to TAC, Leadership and Admin; uploaded to Student Files – Transition Plan | Email + Transition Plan tab |
| Exit Meeting | Transition Report with attendance data attached; draft Exit report emailed to Leadership 24hrs before the meeting | Reporting tab; report to student file |
| After Exit Meeting | Transition Report sent to clc.admin281@schools.sa.edu.au | Email |
| Archiving | All documents compiled and handed to Admin | Checklist tab |"""),
    ("Each Term", """- ☐ **Term assessment data** entered for every student.
- ☐ **Attendance concerns** raised with leadership (see the Student Attendance Improvement Plan for ongoing non-attendance).
- ☐ **End of Term Checklist** completed and signed off on the staff portal."""),
    ("Quick reference — What goes where", """| What | Where | When |
| --- | --- | --- |
| Student Absence | EMS | By 9:30am |
| Micro Behaviours | Quick Incident Log | 1 or more recordings each day |
| ABCH / Critical Incident | C.I. Bot → ABCH Report Formatter → Teams ABCH (@Manager @TC) | Same day or completed within 24 hours |
| Contact with families, schools, agencies | Communication Log | Each day |
| Meetings (TAC, Review, Transition, Exit) | Student file | Same day |
| Tracking Tools | In the drop-down tiles | Where applicable |
| Team meeting minutes and actions | Team Meetings tool | Weekly |
| Case management progress | OneNote Checklist tab | Weekly, and as milestones happen |
| Goal progress | SGoal Quick Track | Weekly |
| Offsite meetings | CLC Bulletin | Before the week |
| Term assessments | Assessment Data | Each term |
| End of term sign-off | End of Term Checklist | End of term |"""),
    ("Finding the tools on the portal", """Open the section on the portal home page, then click the tile.

![Incident Management section](section_incident_management.png)
![Quick Log tile](tile_quick_log.png)
Record at least 1 micro behaviour for each student, each day.

![ABCH Process tile](tile_abch_process.png)
Record Critical Incidents using the C.I. Bot or the Word Template.

![ABCH Report Formatter tile](tile_abch_report_formatter.png)
Copy the report and paste, then format the report. Post to **TEAMS – ABC-H Documents** and tag **@Manager** and **@TC**.
> CI needs to be completed and finished by the end of the day or within 24 hours.

![Reporting Tools section](section_reporting_tools.png)
![Communication Log tile](tile_communication_log.png)
Record every communication that has occurred (phone calls, emails, texts or face-to-face conversations) with families, school, SSS or agencies.

![Student Files tile](tile_student_files.png)
Takes you into OneNote – CLC staff 2026 – Student Files 2026. Record in **Scheduled Meetings** all meetings that have been organised (TAC, Transition, Review).

![Tracking Tools section](section_tracking_tools.png)
These resources can be used to support tracking of behaviour and the student's profile, e.g.:

![Sensory Overview tile](tile_sensory_overview.png)
![SMARTAR Goal Builder tile](tile_smartar_goal_builder.png)
Has each of the student's SMARTAR Goals.

**At the top of the portal**
![SGoal Quick Track tile](tile_sgoal_quick_track.png)
Use this tool to track SMARTAR goals quickly."""),
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
            pl = PRINT_LAYOUTS.get(doc.get("slug"))
            if pl:
                st.download_button(
                    pl[0],
                    data=_print_bytes(doc["id"], doc.get("updated_at") or ""),
                    file_name=_docx_filename(doc).replace(".docx", "_print.docx"),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True, type="primary",
                    key=f"pdl_{doc['id']}",
                )
            st.download_button(
                "⬇️ Editable Word version" if pl else "⬇️ Download full document (Word)",
                data=build_docx(doc, sections),
                file_name=_docx_filename(doc),
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
            render_content(sec.get("content"))

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
                        render_content("\n".join(
                            l if IMG_LINE.match(l) else _highlight(l, query)
                            for l in (sec.get("content") or "").splitlines()
                        ))
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
                        render_content(sec.get("content"))
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
                has_print = doc.get("slug") in PRINT_LAYOUTS
                st.download_button(
                    "🖨️ Print" if has_print else "⬇️ Word",
                    data=(_print_bytes if has_print else _docx_bytes)(doc["id"], doc.get("updated_at") or ""),
                    file_name=_docx_filename(doc).replace(".docx", "_print.docx") if has_print else _docx_filename(doc),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"carddl_{doc['id']}",
                )


def _docx_filename(doc):
    return f"{(doc.get('doc_code','') + '_' + doc['title']).strip('_').replace(' ', '_')}.docx"


@st.cache_data(ttl=60)
def _print_bytes(doc_id, updated_at):
    """Landscape print version for documents that have one, cached per version."""
    doc = next((d for d in fetch_documents(include_unpublished=True) if d["id"] == doc_id), None)
    if not doc or doc.get("slug") not in PRINT_LAYOUTS:
        return b""
    return PRINT_LAYOUTS[doc["slug"]][1](doc, fetch_sections(doc_id))


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
            "Word *Heading 2* — keep new section titles in that style so they're picked up. "
            "Documents with a 🖨️ print version: you can edit and upload **either** the print or the editable "
            "version — keep the ☐ boxes at the start of each checklist item."
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

    seed_pack = next((secs for meta_, secs in SEED_PACKS if meta_["slug"] == doc.get("slug")), None)
    if seed_pack:
        with st.expander("↺ Restore a section from the built-in version"):
            st.caption("Puts one section back to the version built into the portal page — e.g. "
                       "**Finding the tools on the portal** with the tile images. Replaces that section if it "
                       "exists (matched by title), otherwise adds it at the end. Other sections aren't touched.")
            seed_titles = [t for t, _ in seed_pack]
            default_ix = next((i for i, t in enumerate(seed_titles) if t.lower().startswith("finding the tools")), 0)
            pick_t = st.selectbox("Section", seed_titles, index=default_ix, key=f"rs_pick_{doc['id']}")
            if st.button("↺ Restore this section", key=f"rs_go_{doc['id']}"):
                new_c = dict(seed_pack)[pick_t]
                match = next((x for x in sections if x["title"].strip().lower() == pick_t.strip().lower()), None)
                if match:
                    sb.table("reference_sections").update(
                        {"title": pick_t, "content": new_c, "updated_at": _now()}).eq("id", match["id"]).execute()
                else:
                    sb.table("reference_sections").insert(
                        {"document_id": doc["id"], "title": pick_t, "content": new_c,
                         "sort_order": (sections[-1]["sort_order"] + 1) if sections else 1}).execute()
                sb.table("reference_documents").update({"updated_at": _now()}).eq("id", doc["id"]).execute()
                clear_caches()
                st.session_state["ref_flash"] = f"Restored '{pick_t}'."
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
                "Content — '- ' for bullets, **bold**, '> ' for a highlighted note, ![caption](file.png) on its own line for an image",
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
# Built-in portal tile images (captured from the launcher, v59) used by
# "Finding the tools on the portal". A file of the same name placed in
# data/staff_reference_images/ overrides the built-in copy.
# ------------------------------------------------------------------
BUILTIN_IMAGES = {
    "section_incident_management.png": "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",
    "section_reporting_tools.png": "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",
    "section_tracking_tools.png": "iVBORw0KGgoAAAANSUhEUgAAApwAAABGCAIAAADuE9OSAAAXYElEQVR42u3deUCUdf4H8O9zzH0BcqOAEIqSaWGmJOuRmZloqXmkZYayapu1rq7tT9c2u7Nf7lqZZ5lJlqtpllbmVd4iuOINCaIggsIw9/Fc+8ewwzzPPMMMCHJ9Xn/tIo7P83yn5/18r8+DcRyHAAAAAND24XAJAAAAAAh1AAAAALQiZCC/5LBwZj1nrWExDCmD8JAYeBQAAAAA2lSo68vZ07sd+XscVaWs4I8iEonew2V9Rsg0oRhcRAAAAKA1wEQXylUUMXtXWy8dpur/yziBeg2TDs1UQt8dAAAAaI2hvv1tS94uR4M+ZeAz8sdeVMLVBAAAAFpLqDttKHuhsSiXbsQH9RwknbBUTZBwSVuLymIGJ7DQWBhEAQCADhnqqzINZZeYRn/WPf0k05Zr4Jq2uKpSNnuh6dZVBiEUlURMeU+ji4BoBwCAjhTqX71quniIusOP6/+0/IlXmngcPnuhyWZqfIUcgkTTV2jbVqtseMVEO+tO+aGx8l7DpIH/9S/nmwqO1TVlr2HSCa+r29Dpt6cW/3yukfKYyxrwdMOaEgAAGqR2uDxvl8NvoiuDMMaJHNb67rbH/21PHihJ7CtpwkO8fp626O/gFi9pe61y7SxF2ev+b490tkF/vfQCbwLl6n/otnX67anFr5+nPZsyZQiLAACg2eAIIYeF2/Optf7f6zlY+rddwQt/CI7r7Wfa/If/t8BlbVkxPXhtFNsLVjoAAECHCfV962x+O0Z9R8sQQhIZuv9xWf2/efsae/QbO1zZFjTyZVVYHOH63xGJxOMvwcYEAADoEEiGQjk7/GewTFlbZEaq8F9t5lC2LW2ivKkOsUsKKTrDWlHE2D1+LlWgqG4iXdIOuCA/NBaf+5Wu7a5+hxYHAIBGhnrBMSftbOIPNVdxFVeYiESiST5tynviK+o3zjMVnqhbBxAWR8xYqYUWdQvvSrTRI4cWBwCARoa637JxvkQmEQ9PUpScoU7tFKlUc+mwMyJR0SYuAeVANwtpp53ThROi/VqHhasoYihHbR8xuhup0GKN+Ff0ZYxZz3EcFx5PaEJbYwea45CxkjVUstowPCiyYUdoM3G3ihm5BguJIchWub6b45DpFltTwcqUWHA0IVU08tuiL2PsFk4XjmvDcKxJm9FpQ6UXaNeGFAzDYnoQ7hEyAAAIKNRvFDRyafTEpZrQWLzPCGl5IVN2Ufghd7LfvTkc2mT3XAzY5V4ya7XWoud2r7Dk76kdqXhonHzUPN7086VD1KFs27WzvLPDMBR7Hxndjew3Vu53cLu6jD38la04j7p9jbfsuXMKed+j0tRR8sZFy+1r7KeZNU6P1Y0SOZq5SheVRHj3aLunSaYu0/jq72bMV/V7SsZx6NROx761VvfqCokcxfeRjHxZVf85Oizcka/tghcEpI6SDZ+tVAZhZ352bl1q9jzIJftC7n6Wn/rOcf6gU7CnICQGT+wreXiyolMX/8msL2cPbbIVnaI8T5OUotheZMoQ2YNjZHeS7hyLzuxx5v/iuJJDsR7/3eAE6nq/pHMKOfAZuVwN6Q5Au0U5kLWGbXRBkYoiJrwrgWEIIURa9OJ7bKKTibA44szPPofm3ff66O6Ed6j7+tjWw2lF6/9kdFVo8WY3czvesZw/6BQNiZIzdMkZ+vg2++NzlQOeFl89wDLowGe2Q5tsjNhTU+l5uvQ8/dtG2/jX1A3dAWgzchteMXomOoahyW9pXIneUCzD0U709WLT5SO8MRvKjgqPUx+fqsmYr0rNEF8defkotW2p2Xv+O/cHR1EulbVG1+KtXF7AbH3DXFnEiD5vVZc5cn9wDJyieGSGAidQQ9uRdqKiXLoolz6xzT5usTo6mWjcEf77dbPo95Bl0JVT1JVTVN4ux+S31F3uhcUCALRDRbn0pr8aKTt68ElZxnwV1pAHeHM1t3GesbyQCY3F52wIksgQbrotsiKpy73k7PW68UvUT/5N1bijbP2hvm+91VeiO61o3WyjaKILOli7/2nN/UFk9sFm4lbPNBzcIJ7onu3x5V9MDarLy9Bo419Mhgre5R35ijKpfyN3Z7MM2vKaWZDonv/cjnctnqVs3C4eojYt8FklRl/ObnjZSFNcCzZx7veOVTMMoonuefq/bbStmmEQPZEA27GymFmdZcj93tHQIywvZFbPNPj6HrqZbrOfzzVWFDEIANAOQ712EDFnh2P72xYu4LumuZpbN8dQXsgghG5fY2+XMAghXKkTeSpIeqg2IboPaOTsqDKoVS+6NlSwOdt9rvnf/o7Z+waqCcUikwjvwia7llu8NwRufd1843JAt2CGRluXmuov6cP75KVmQW2Z/k/L+49v/F6DolPUxd/8PL4c3GDzHi3Y8Y7Z74jQnpXWlmrisov0zmUWNrAcLC9gti0VOZ1vFgfajiyDdi6zlJ5v2GTWj/+yCB4XgqPxXsOk/cfLBf1+yoG+fdMMtz8A2p+EVIm7d356t2PHOwHluivRq67XdvB0EXhoHIEQItWdcKtBeNtyD0X6min0W7QrNLZVL7023qq9EOEJREwyqQ3DGZoLiSZcUXRuv5N/xclR81Rh8YTr3nrgM+uhTXUPBJQdndppHzStbm788hFK0LUlSDR4uiJ9ioLjUNlFes8q67V82qMfxh3ZbB+a6X92ff9627l9vGNL6i8ZOfeOtqFfPkohhKK6Efc/LguOJgyVbP4eh2AZwfVztKGCN99zfKvdauAE35nBzyvSpypIKaoqZb97z1ycRwt+527a+YEw0eN6k2MWqsLiCI5FJ76171lp9SzgevkoVXiCcj/OutrxyileO5JSNDRT+fBkOU6gqlJ25/tmz1EWlkG7V1izVge6IL+ymCk+zbvO6VPlw2fXteaFX53f/N3sPosblxnBEQIA2kWokxPfUG95rfY/9rxdDpZFYxfVNw5v0QsTPfMTrUSGEEKkphNe2QzDeu7iJ63Z0EzF4OcVggcXuQrLmK+qLmUqrzJV1xmlDn/uQ61767NEhobPVhadojxXApbylxQc3yocA5jyvsZ9L47rTc74RPvFn02egXF8q33w8z6ndV3O7XMe+IzXYw5PICa/rbnzBdgpg6UT31S7v0D9npJtWWIWPNkUn6b7jKgbtsn5zusc39V0S6s9x06d8ekrtBvnmX4/SbVIy5ZdpG/wl2omPiiZ9mHttcJw1H+8vHNPcu0so2fwn9xu94zME9t454hhaNqH2vj7Sfc5Pv8v7aYFvDL718/RNwuZyMAWN+hvCKeoHhrLG3HpOUj6xJ9VJflUeDwRFkeExhGt/FkZANDIm/AQ6WRSs3mRyXVH+s+PDoR85rpFz62dzUv0rFVabXhtEpCde5JXcpr+ztv6Q/3BJ2VDXhDpHOsi8H5P+ama1ymW8Ax1Y2Xd3dlu5gTXs+9omaB3heFozKuqD8fX4ASKvIeISSYjk0jagaS+utwYKr1Ab32DN/qqCcWfX177aHYncAI9Plfp+dXBMDTiT0pBqN++Vne+lUWMYCnG/SNl7kR3f8jYReoPxurZlpgIPrPHKTjHcYtVgqefzj3Je4dK839xenbNnTbk2o9gN3OeewQQQn3HyNyJ7j7Hx+eqCo7VeP4wf68jMimgsRPv7Wpn9zoHTuHler+nZH6/jQCAdiA5XTL5Lf+5Lkj04Ch8xsq6REcIkfcOkf76ha1pD06mwhL7tfZBwoHPNHgzGcch/Q32So5wEprxuPkX51GC6ZCUISLrEoKj8Je+1IXGEXgADz83f2d+/cLm+a9I5GjahxpNaBNscwqJwb33UegicHUIZq6uOxPT7boHl2vnhDPHD4wUCR5NKJaQKmmRznrxaUqQ36KFAfqMkHmGOseikvza8e3iPOFh9xwk0o6hsXjnFNJzKj3w1+d4V2f6eaX10hHngAnyhAckjaiFAABo67k+9X1N9qsm193eO9cFid6pMz5jpU7diXevICOTCF0ELlhN7e6GuveqlV2iXe8FuXGZdsXYrRLG1R33Xkn08CS5pHX3LkgpConxP2xdUcSUnKEri5nKIrqmgjXeYhl/CSVYyYxhKL6P+PNNeEKggxmupvU0fom6qQr2BUeJf442HDdXM54PNG7eM+VR3cU/JDKJaJFQd60CdfO1GSz+fmHTVFxhXKHuvSI9rrd4O8b14oV6RVGgoa7QYj3SJYK3I5acoUvOmBFCQZF4dDIZ24vsOUgaHIXD/Q6AjiCpv+TZDzRfzhfJde9En7lKpwoWPv2TCKFBzyl2LuO9Wu3ib86fPraGxhKHs2s78b9+YeNY5LRxOTtqA2bLa+YBT8tLL9CCTepyNdaEhd+bCUFifnP06BZ7eUGDx47tFl7gkTLUHOXVruRQoh3HRvA1VFDPBbKbWcEn+Cp8pg1rgTTiWCSofKzysRdDIkMKDea5mc3wv5kUwQ43iRz5ek4VjHM4rchu5gKsFZMxX1V82mA3iywnrLnJ1tx0Xjjo/Okja3hXYuTLysQHYYkcAO1fYl/Jsx9oNi0wue5jrlwf8aLSM9HD4ojMT7TeiY5cb2nrO0bm3e07stn+3XsWd/0si577cYV131qbe/PVzUJm+9sWd8a7PTROLlO17ZHDb5aYt71p8ZXoGIZE9wHW/inO+yPa0SxHeHK7o0G725uWYI6HZRDnoyoB3jp6mIzv7fI4vw/PMdz/fh5oO3o/FXEB12jQhOJzs4MSUv1UlaksZja8YhIskwQAtONcn7ZcK5HXdTL/OanGneiR9xAzV4knem2oYxia8Lpa2kSV2nv8Qdqmr+aJbXbBtjGJDHVPk6RPlT8yQ/HsMs3//RTc+zGfswuqIN6F5jgk2g9rKO/u/pbXTDZjy2wYU+qEWe05+x7Iz5v3mQNHcg2vFSw+dtZxLBJcQ1Uw3tB2FJwjTgj/dX+5jk1foZ23NWjSm+pB0xQJqaSvYY/9622+agQBANqZ+D7kCyvqct19/4lIJDI/0daz5qb2FhbelZjynrZJ3k6RvVBY76xtOckfe4jpQc7/NnjqMs3w2crB0xXd0iRyNYZ8R5X3e1Bu/i7e46+4wgRec2b8ErXnVnjX2MnWpS1TjUQXLjzHq/8RD5vygpYZTgjiD4lXXBE/jJu/M4LF+SExREPbsbyQ9+HBUTjW8IGq4Cg8ZYh0WJZi+grtoj3BL27QjVmo6pwi7MEf/go66wB0FJ1TyBdWaD13RUV3J2as1NY/u1d350pIJScuVd/5AjfTbXbdHGPbzfVbxbx797AshTJIeAVvlTC+H6+EE59n94oM3Tqs3Mrphjcf1b8zUr/mj8Ztb1rMVT4DfsAEecoQ6dBMhWCWpOAYJVqktvkfIYXnmLfLIfpNaKl96oJFbVdP095V/xBC+b8IDzshVeLrHM8fEKm7ZzMKdzB6L77zi2XQrat1r4rHMBSZRPQdLctapXWtTnUru0QjAEBHyvXMj2rXt3d9gHzhY63f9Tq87kjKEOms9bpAloULCAb3a2621VznWCTYkOZ9BQ0VbEm+z6xS6rC43qQg8PTlwktxZLPd1Ue0Grjr5+jzBxwK3/P0rp4xTqAJ/1AT/M7bruWWu3+d1Z0wQX2V309SJ7fzAtJczWW/amZaKIMEqwg5Dv3sVbC26jqb4zUq494l6N2OuT/YvZfE7/nUKliU1zPg6aej39g3zjMtn1Dzj8HVK6YYjm4R1vPBcBTTg3cMhAT2uQHQsUQnEwu2B8/9SvfCR9pA3sUszO/wrsSLXwSlT5UTgb0RShOKj5qnXLAjeFiWQpDra2cbRd8W05phuLACTB6/K2yoYDcvMlP2+j7kD1N5l4J2og0vG4tyadf6KYZGe9fYBIue+jwmC+SChycQgoI5lB1tXmTm7vrjk6D2GULo+w8sa2cZf1lt27vGtnOZ5V/P1Hi/u++uSUglY/i100/vdmx/2+KaQedY9PtJatVMg2D6YzB/gkPQjpQdrZ1lvHqadj32WQ3ctjfMp3byvh5RSYSgCE89jJVs4Qmquox1Nd/hbNsl/vY2i5678CvvkSG6G1SUA6DDwYkG1HMTSRKpAg2frUwdJT+y2Xb5KOUuk+7dJR30nCJtUu3NfdA0BeVAnnVsDBXsujmGGSt1TVIj5a7pkiLxHFDN+c5RfYPt3JOkHFxlEVOUS/ktkdYtTZKcLvG8QVeXsZ/PNUoVKDSWqCxmBH07mQob8kKg9dv/8Kziwq9Oz9oAZRfpgxtsotXxms8DT8iOfm0XTENcO0sLisYn9pUIyqffNRkL1GuyDJ6NlbfLkbfLEZFA1NxkvVczJKdLktMl9bejzcSt/5NRpsJ0ESLFlXECjXlVHfgR9n9afnSL3f1ARjlQ9qum+x6VBkcTCCHKzp3+0SFYx/fwJAXc4AAADQt1l05d8NF/VSGEKouZ8gKmspiuKGIICRaRQEQkEuHxhOsFJ56GZSkYmjucbfcMs/UvGjI/aUu53n+8XDBLeiWHEvwkZbC0/hezjv+7es0fjZX86XmnTaRQD4ajcX9XB359MBxNeF3z8XM1nk8GBzfYuqVJY5LvXjcOJ9D419SfvWR0WHwOxqRmyGKSyZYK9ZhkYvQC1Y53LYKfi77ANDyBGL9EHWA7Oiyc6OsSRi9QNagJgiLx4bOVP3/CmxfwrHAnfJ57ThH4MAAAoIN26/3+RnhXovdj0kdnKae+r5n8lnpopiJlsNQ70V0em6MUvAa0qpRdN8cgukypdUoeKBEt7OqWPlXee4Sf9YQyFZa1WnuPv1q5qmBsyruaHukNu1N36oI/OovXs2cZ9M1iE+28qxcqujsx53Odr2JtfUfLRi9QtWxTpmbIJryulvobBOmeJslaJT5ZJVNhM1f5b0e5Bpv0ljo1o8GrTAc+Ix81TynxV6tJIkMjXlI++kfopgMAGttTb7Qn/qyknZznXGN1Gbt2tmHmpzpfm+Vbm4lvqPevtx360iZY5xUUiQ/LUvZ+TCoo7ekr16ct15RdYo5+bTt/wCn4qM4p5L1DpamjZAGWHhNImyg/t9953aMGu76c3bXcMmbhXc3RkBg8a7W28DiVv9epv8FgGFKH4CExeJ8RMl+PfXdZr2HS7g+H5Oyw5+ywuysp1X71pajXMFnaBHn9L1WTq7FpyzU3LjFHxNoxLJ7o95QsNaPxdZEfGifvOUi6f73t7D6n97BHTA+yR7okdZRcUN4ZAABEYRzXLH3o796zCNYQhcbiWWt0Ck2buTdZ9FzBMWd1GYsQ0oTinbrgCQ9IGreV327iSvJp/Q3GYeXC4ojY+yTqkA5xjz6y2f7Tx3XDy9pwfMH2oJY6mLJLzK1i2lDJSpVYSAwR34cMZCmpr3bUheMRiWRU061c41hUXcbevsZUXWdYFoV2IWLvI+upXQgAAHcv1BFC375lOb2bl+v9npJlzFfBRW9n3K/28fsdiOlBzlqnhSsGAADNhGy+jx67SMVxvDeMeW/zBW2UtYYrOOYsyqMLjjktei5jvsr7td81N9lz+3lPdd0GwDovAABom6GOEBq3WMVQ3Nm9tSu4kvpL4Yq3D7+stnpOr3z/gaU4j3pglCwigXC9ma3wBLX7nxbPDf2kFPV7Ug6XDgAAmk8zDr+75exwGCrZoEi872gZXPH2wXSbWz5RX38RHoFhWQpB+XoAAABtL9RBu1Ryht70V1OA76B7ZKZi8POQ6AAAAKEOWm9/nf3xI+v5A856quxFJBCj/qKK70PC5QIAAAh10NrZjNy5A87r5+iq60xVKeOwcLpwPCyeSOgr6Z4mbcT7gQAAAECoAwAAAB0a9KIAAAAACHUAAAAAQKgDAAAAAEIdAAAAABDqAAAAAIQ6AAAAACDUAQAAAAChDgAAAAAIdQAAAABCHQAAAAAQ6gAAAACAUAcAAAAAhDoAAAAAINQBAAAACHUAAAAAQKgDAAAAAEIdAAAAABDqAAAAAIQ6AAAAACDUAQAAAAChDgAAAIBGwBanVcFVAAAAAKCnDgAAAAAIdQAAAABAqAMAAADA238B1VEWyWP1wXYAAAAASUVORK5CYII=",
    "tile_abch_process.png": "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",
    "tile_abch_report_formatter.png": "iVBORw0KGgoAAAANSUhEUgAAApwAAACECAIAAACyM2wtAAA/Y0lEQVR42u2dd1gUxxvH373jjt5771IE7L33qDH23nvvxqgx9sTee+xGE3vF3kVRURFBeufovcPV/f0xsCzHQQBRib/38/A87O3Otndn5zvzzjuzFE3TUDk0TQtFkmKhWCKVyWQymayqxAiCIAiC1C0cDsXhcJS4HBVlnjJfiaKoKhJTCkWdpmmapgsKRYXFQhp1HEEQBEHqARQFairK6mp8iqIUqrsCUadFIuH166IHD8DGVuraUOLqJtXV5/G4Ksp8LpdTdR0BQRAEQZC6gqaBlslkNC2RSsViqUQiBQCKotTV+OqqyhUVuZyo0zQNBQUFa9dK/PzYLX/+4p+5XbqgcREEQRDkGyKT0UXFIpFIDADKfCVtTTWKAra0l4k6TdMygaBg9WpZfHzZAXg8/oqV3Fat0JQIgiAIUi+kXSorKhaJxBIul6OjpabEcqJzGEWnc3IKVq0qp+gA3JYtUdERBEEQpP7A4XLU1FV4PK5UKsvOLZTRNNM+5xBFB4mkYNUqWUKC3J5KU6ej+RAEQRCkXkEBaKir8nlKRNdLpJxpqRdfuiQNDpavC3h4cIyM0HYIgiAIUg9RV1fhcrlisbSgUFgi3DRNy7KyhP/8UzE1t3sPNBmCIAiC1GNdVwaAgiKhVCajaZpD03TxqVNQVCTftNfUVGrfAe2FIAiCIPUWLoejzOfRNBQUCGma5tAFBeL79xWk69YdVFTQXgiCIAhSn1FR5VMUFAnFNA0ciZ8fSCQVE3GcndFSCIIgCFLP4VAUj8cDAJFYzJG8e6cwEaWugZZCEARBkPqPkhIHAEQiKUcaGak4ia4OmglBEARB/gONdQ4HAMQSKQeyshS31HX10EwIgiAIUv/hUhQA0DTNkVUm6hrofkcQBEGQ/wAUhwMAUhnNAbFYcRIeD82EIAiCIP8BUS/9pAsHbYEgCIIg3wco6giCIAiCoo4gCIIgCIo6giAIgiAo6giCIAiCoKgjCIIgCIo6giAIgiAo6giCIAiCoKgjCIIgCIKijiAIgiAo6giCIAiCoKgjCIIgCIKijiAIgiAIijqCIAiCICjqCIIgCPJ9oVQ/L4vOzpZcviSLjACR4s+9U7o6/F9/k0VFUhqalJERPkgEQRAEqY+iLktNFc2dTeflVZGGMjQEADotXbR+nfLmrajrCIIgCFIf3e+SY0erVvRybfqUFOGSRXRSEj5LBEEQBEW9/rXUPwX8eyKKKtP19HThz4vp5GR8nAiCIMj/M/XR/U5nZVUjEV3uV2amcMki5c1bKXPzr3CFWdk5Z89fY36qq6lOHDusivRnz1/Nys6tbKuTg12njq35PF51Th0WEfXmrV9UdFxicoq2pqaNtYWNtWXTxm4mxoYK0z95/iowOIwsD/ixp4W5aWVHvnDFMzUtgyxPmzSq6usJi4i6/8hLQSWRokyMDa2tzB3sbbW1NPEFq342YNDSUB83egiaC0GQ70TUa1kVILq+bcdX0PX7D5/tOXCcvaZDmxYODraVpf/nwo2wiKgqDqivpzN8yE8TxgzV0daqLE1IWMSGzXt93vkpcltQ3bu237DqZ10dbblNz1+8OXv+Kllu0dSjClG/fPX2B/9Asjxx7NCqRT08MkbOAhVp2bzxwjmTmzXxwNesmtmAYG1tgaKOIEjt+K6GtNE5OcIli+i4uC99ojsPnsqt8bz3+HMOmJGZfeDP08PGzsovKFSY4NLVWwNHTFOo6ABA0/SDR15Dx86Mio6rP4/D553f5FlLX/t8+P5em7CIqAaNOpG/jdv2YzlSCxYuXcvYMCc3D82LIP/fLXWJBAA45ua84SPktkjfv1OysvpyZ05OSfN+/Z4s6+nqZGZlA8DNOw8XzJ5cnd3btm7GLKenZ0XFxEokUvIzJlawadv+Dat/ltvlr3+urN+0u9xjU+I6N3AUiUSxgnihUERWxsUljJ+28Mo/RwwN9L7mo7C2tjA3NSbLhYXF0TFxTBldWFg0d/FvNy4eNzXB4QmVZgM5DPX10D4Igvx/iTqdlUXHx1MWFkrjJ3zlU99lNdMnjx+xddchABAIEt9/8K+Oq/nk4R3sn7l5+Tv3HmU85Fdu3Plt2XxlZX5Ze/e934bNe5ifXTq2mTh2eJPGDZX5fAAQikQXr3juP3wqIzMbAFJS0zds3rN765qvaZD+fXvOmT6eveb+o+e/b9mblJwKADm5efsOnfx9zVJ82arIBgiCIP/fLXUA4drVSu07KL6r4SNAReVLifr9ElF3crTv368nEXUAuH3vSS36j7U0NVb+Mvfl63cxsQIAkEikMXECJ0d7JsHm7Qfp0qjAHt067N22jsMp6zRR5vPHjBjU2MN13JSFxHV/5/6ThXMm21hbfsNH07NbR2Mjg6FjZpKfXt4+laUUiyWxsYKMrGy+Mr+xuyvFGtRQNSKxOD4+Kb+gwNnJoZoxhkKhKDwqms/j2VhbVnOXkh1FovCIqIKCosaNSupS34qk5NTk1DRzMxMjA/3q7yWTyaJjBOkZmXa21lV4cTKzsgXxifZ2NhrqanKbcvPywyOjpVKpq3ODilsrHic5JS0vL19dQ82lgQOXy/2iNql1FiI3xeVwGns0RCVAUNTrQWM9IUF8/pzCTdz+A6gvI+pxcQm+Hz+R5XZtmhsZ6Ls6OwaFhAPA7XuPly2ezePV2KRcLrdJo4ZE1In2MJueer0OCAwhy5YWZpvXr2ArOoObq/OYkYMOHT1T6kt4NmPKmG/7dBq5u1pZmcfFJQBAckpaekaWgb4uW1+Pnz5/6+5jdu+DpYXZgB97jhs1RFu7XNi89+v3E6YvIst/rFk68KcfDhz569ipc4WFRcR67g2dZ08b36lDK4VXkp6Rtf/wqRev38bGxpM1FEXZ21p369J++uTRchIlkUhdm3Uly8OH/LR6+YItOw+eu3SjuFgIAM/uXbx55+G2XYfZu5z468KJvy4AQN9eXXduWf0ljHnv4fPTf18KDglnQi50tLXcGjpNnzS6VYsmconHTlnw5u0HALC3s75z9fSFK557DpxITUsHgK1/rOzftwc7TdvWzU4e3uH10mfX/mNMTps8fsTiedOUlLgAEBgStmf/8SfPX5VUIpX582ZOmjpxpEItP3v+2o3bDxg7A4Cammqn9q1X/jKPXZnwaNWT2JOhRYcfycKEsUNP/nWxOuatdRba+sfK1i2a/L5lz90HzxgroRIgKOr/p3jefcQsd2zXCgDatGpGRD0jM/uFt0+XTm1rcdiU1HRm2cHOhll+8eotszxu5KAqGkkDfuzl/ymYLBcWFdUHW5mbGhNRB4DMrDJRz8jMnjFv+ceAILn0gvjEvYdO3n/kdfTAFmMjg8oOu2r99otXbzE/pVKpn3/g1DlLJ40bvmzxLLnEQSHh0+YsI5JWVh2k6YiomIiomEdPXvy5b1MVIwI2bd9/+u/L39CGMpls9YYd5y/flFufnZP7wvvtC++3i+ZOraICd+/h85Vrt1bpvRA/ef5qxrzlNGuM6LFT57Jzcjeu/eXWvcfLVm4UikRsKd266xCHQ00eXy6WJTAkbN7i1YL4RLnjFxYW3bn/xP9T8JG9m6oYHlJTPicL0bRsxtzlgSFhWJoh3yX4QZeacfPOQ7KgoqLcrKk7ALRv04LZeutubWLg33/wJ80mABjwY081NVVmk69v2Tw83bt2rOIgdrZWJw/vIH+L5k6tD7aKTyybDsigNPhLJpPNX7KaKY65XK6Dva2Hmwvj1g4Nj5wya2nlowBuX7x6i8vl2ttZuzg5sDcdP33+yo277DWp6RmTZy5hK7qVlTnbcR0RFTN97nK5ViNLIRL+uXhdbqWpiVHb1s2aNnJj1liYm7Zt3axt62Z2dtZ1bsO9B0+yFZ3HU3Jv6Mz2MO/Ye0TurhmKi4X7Dp2s+vi5uXl/bNtH07SLk4OVVdlY0MvXbnu99Fm5ZqtQJDIyNJA76eYdB9lj84qLhdPnLGcU3bmBw5CBfSeMGcpUTxMSkyfOXJKXX0B+tmrRuG3rZuwH0apFE2JDMxPjfzXvZ2ahm7cfoqIj2FJHAACCQyMio2LJcpuWTUkh0ryZh4a6GilBHj59kV9QWHWnI6PfAJCUkvreN+Ca5z2pVAoAzZt6rFg6l504OTWVLBga6JmbGX/m9V+/9eCtr39lW1PT0+vQVrfuPRYISkp5IwN9PV0dsvz3hWs+7/3Ico9uHVavWEgK99y8/DUbdhBHSGh45N8Xrk2bOKriYX0/ftLX0zlzbI+9nTUAxMbGr1y/jTHpvkMnB/zYk+mh2LL9IIkfBAA3F6d1qxe7uTjRNP3O13/Zqk1EhMIjo4+eOicX6Efwfv2ex1OaN2tS315drK0s8gsKlZX5/Xp379e7e1hE1I+DJ5bcRdcOy5fM/hL5LTwyev+fp8gyRVFL5k8fNby/uppaTk7e0VPnDh8r6W3ZuHVf9y7ttTQ15HZPSEwGgH69u08cN9TRwY5DcfILCiqewsHe9vaVUw72NgDw6o3v7IW/ksw8d8kqqVR67MDWDu1aAkB8QtKS5RuYvqcHj70aONiR5bPnrzI1pzUrFo4aPoBxoqxYs+XqjbvEF/Xo6csBP/YEgCP7tgDAwqVrb5UOBN23Yz0zVdGEMUOrNu9nZiGvlz6GBnpLFkxv07KZibFhanoGlmwIivr/KbfvPWGWmzUtiYlT5vNbt2r68PELACgsLHrw+PnAfj9UcZCxUxZUXOlobzt25MCBP/Vmx70DADMBma6Ozudf/yWW1/oLUVBYGB0ruOH54My5K8zKQQN6M8tnzpXE+dvaWO3YuIq5Xy1Njc0bVgSHlVSbLl69pbBEBoA929bZlzbarK0tjh3cOnT0jODQCCI8r31827ZuDgAJiSmMW8XI0ODM8d3EBUJRVItmjc6fPtD9x5GkV/7cxRvTJ41WGAyxfeOqH3p0Yq6wDg3FdPHKoa2lxQxeYGwFAMuXzJ4wZmhJGm3NxfOmSiSSY6fOAUBObt51z/tjRw6qeLSRw/qv/bXsRBXnJgKA+bMmEUUHgDatmk4cO2zvoZMkM08eP4IoOmkx/7Zi/sDhJU6g6GhB2VmG9nd1buD/KShOkDhyWH9mPZfLnTph5NVSR0JIaAT82PPzTfeZWUhLU+Pv43utrS2YGieWbAiK+leF07ix8uq1oKyseLNEItr0h9Tb+2uI+v0y73rXjmV95927dCCiDgC37z2uWtQra5MdPn6Ww+UO7t9bYbRw9WN6vz57DhyvYnY5Wxur8aNL1CgoJJyZHmdgv15yNRgeT2nowL6bth8gTXBBfKKlhZnc0dq2btaiWSP2Gj6PN37M0GW/bSQ/X/l8IKL+1Mub6SceNqgvu1MDAAz0dfv06kpqOalp6X7+gXKHBQBLSzNG0escZqoDOdjT/TLjLFRUlAcP6COXcsyIQcdPnyf3+OS5t0JRnzJuxL9eSasWjcs9L9uyOR4cy/eCs6M90jLKGrhqaqptWjVt06ppxYNzuWUdfGlpddAm/vws1L1rB0bREQRF/Vsgk8mCgqpKUH4e+C/E+w/+jD+5iUdDpnEDAD9077Ru4y7S7Hv+wkcu0luOebMmMcsikSgmVvDk+SuhUJSQmLJy7VY//6A/WEO69XS109IzASAnN/fzb8G9obOmpnplWz8Fhubm5det0Rq5u+7cvEpfr8TNEBRc1pcZGRWz7/ApufTxCWVf24uIiq1YIrs6N6h4Fo+Gzswy09cbGBzO0q0mFfdq27oZ47oICAypKOrWlubfMNfHJyRlZeeQ5aaN3TQ15B+cuZmxg51NeGQ0AHz0V/CCKClxLS3Nqj6LMp8vNzOxEresTFBTVZVLrKTEJaHmMhmt8E0Ni4j64BeYkZVN03RMjOD1W1/21joQ9c/OQt/2sSIIijrI/P2F/v7f/DLuPnxeVrqp8OVKE1MTI+L0o2n69t1HVczdXbH7ViBInLtkFQmhv3T1VuuWTX7q04Ns0tfTI6Kelp75r731/8rShTMUyhth+NhZzNzvdcKg/r03rv2F7WMoYMUuXb/1oOrd0xR1diqsLZmbmTDLGRklXwPKY32919RYwXx2ZqZlMQqJSSkVE/CUvuDbwa7bsVFTLRmKmcO6fmMjxV/rMTczJqKel1+QkZnNVJ5KRf3fr5/i1I0HKDY2fu+hk0+9XtV5vVCOz89CXCUuIAiK+reF49gAKpstRCqVhYV+6ca6VCr1vF1Wgrz2+VDFlOa37j6u0Qc5LC3Ntv2xss+gErE/+89VRtTdGzqFhEWQC3jvG1DZUOxvy5CBfcnoZwD48DFwx94jZNnX75NEImX3VXNqMg9JcVGxwragAmVi1RuYFiSHU3YuiVRacS8VVoeOwgRfFIWheeW0hzUhgaySy1NRUWZlUcm3ygC+Hz+Nn7qQPb8CAGhraTZr6tG6RZM/tu6ry6Lgs7MQgqCof+tL7NKV93NVk4yKDx2U3Lj+Ra/hzdsPTBz1v/LBP1AgSPxXzycbB3sbczMTEq7sFxBE0zQRqvZtWjBjsi9d86xC1N+8/cCE4HXv2v7Azt+/2gMyMzVmHAAtmjW6efshaT7GxArOnLvC/iitjk6Zp3f31rW9e3au6blSFfXLxsUnMMt6etoVz5WckmZnK/85gKSkVGZZX1envmV7dmhkcqrigQmJpbdAUVSdhFLWju27/2QU3draYvigH5s39fBwc+FwOEKhqG5F/fOzEIKgqH9jpO/ewtEjVCUtdVoikT5/9qWvgR333sDBzsBAgRNYkJDEdLpf87w3d+bEmjVBSltmNE3nFxSSPtSuXdoZGeiTUTf3Hj5/8MirRzfFM+NeuV42WLlVs8bfzKfC4SxdOHPqnJJK2MEjfw0Z2JfpD27ACryKiIwGqHGJHBAYWnHlK1bQGTPOypEV9PD6rW/FD6gww6IAoAFrXt56grGRgY62VnZOLgB8DAjKyy+Q61bPys4JKh1v7erkWIupDOuEzKzst+8/lmS8Fk2OHtjCnkm3zr3xn5+FEARF/RtD5+VJrnzLWb3EYgn7Iy47t6xytFcwN9aDR16zF60sFfX7NRL1Z15vmLk79PV0mOJbmc8fMaw/E1u+bNVGfQNd9tQchItXb129eZfZpV+pM/yb0KlDq5bNG5OvxGbn5B4+embJgumlQmtrbGRAps+7fvvB5PEj5ILS79x/+uHjJxdnh0ZurhXb1gDw/oP/y1fv2rVpzqwRicXnL3syPxnjtG5eFj1w5dqd6ZNHq6uVRSSkpWdeu3mvxGLK/OZNazZpPwfKHP70F+v66diu1Y3bDwCguFh4/tKNKRPKTc56+uxlZnrUNpV/8+1Lk59XNva9RVMPubnxq5j2nz3hsZwNqzDv52chBEFR/8ZQFha8yVOpyj6kIZGIT52URUV+uQt45vWaaXA42NsqVHQA6NyxjZamBkkpiE/84B/YRNGHItiTzxCev3xz/PQF5mfvnl3ZW6dOHPn0+SsyBWxefsGIcbO7dWk3dEBfdXU1ABCJxBevepJZrJn0et/ambxsyaxBI6aR5VNnL40ZOYiM1OJwONMmjSafkY2LS5i18Nd1vy5mJjLzeunzx9a9pLw2NzO+e/2Mwq+nzFuyav2qn3t07cDjKUVFx/26dmtEVAzZZGSg36lD65In5WDbu2eXO/efAEBqesaYifN/X7vU1dkRAIJCwhctW8fElo8ZMUguxOzfm9GsL8kGfAopLhayu7friknjh98ojeTYsvOQjKZHDx+grqYmFkv2HDzBTD6jrqY2YezQb/Ws9VleK9+PnyQSqVJpJNrb9x9/Z31gUN6GrMF7b9769eresTrmrZMshCAo6t8SbgMnbquqAsQ4H3y/qKizm+lV9OHxeEo/9Oh84UpJq/HW3ccKRV3h5DNlRaSezoyp5abyVubz9+/cMG3OL2R+FQB49OTloycvFe7etXO7GVPHfvNH5ubi1L9vDxKcLBSJdu0/tmndMrJp9PABDx4/J2GG3q/f9/hpdMvmjd1cnfz8g95/KBvjMHvaeIXFsYO9bURk9IKlazQ11M3NTEkUIcOqFQvYXujlS2Z7v35HPu4eGBI2YPgUKytzCzOTN2/9pKWhZw52NvNq2FECAJoa6sznat77BXToMVhHV7t1i6brf1tch2Z0dXacPnkMI97bdh3evf9YEw+3tIzM6Jg4JtmKpXO+4Qwq6mpq7du2eOH9ljzQYWNmdu3SrrCwKCQs4oX3WzU1VWU+nz17fNmjZM2qO3fxb67OjmERUY9unTM1MaravJ+ZhRDk++Y/MPe75PEj4fx5wiWLFf8tXCC5fu3LnV0oFD18+oL5WfVsJH16dWGWb915KK1hTLW9nfW+HesrFtDGRgZ/Hdv9rxOhjBkxaN/29TX6qOiXY/7syUyReuX6HWb4OIfD2bNtnYebC/lJ0/Sbtx+OnTrHLo4njRs+ZGBfhYcd8GOPju1bEaeFnKKvXDq3Z7dy0+ObGBsePbCF7beIi0vwfv2eeS72dtZ/7t+sqlqbD/r9tnQ+s5yTmxcbGx8cEl73Zpw1qT+rM0Uslvi892Mr+oLZk4dWYquvxqyp45gOo0/BoXsOHD968h8i88sWzdTV1Va41099ezLZgLhPJBJpUOnsAlWY9zOzEIKgqH97ZOFhsqBAxX+hIV90PNu9R8/IrDJQpe+d0KpFE8aRm5GZ/cL7XXVOweMpubk6r1u56Nblk5V9kV1LU2PPtnXHDmzt3aOz3Gwh2lqaA37sdeLQ9lXL5yvVmzG4Fuam7BlDma/OA4COttbZE3tW/DzHzcWJ3bCmKKpDu5a7t6yp+LE1YCU6tHvjgtmT2R3kdrZWR/dvUTiMsJG7642LxwYP6CM39ZiOttasaeMunz1swRrjXiM6dWh1dP8W9gRwgcFhYnEdjytTUuJu/WPlzi2rK2a8ls0b/3Ny76xp4775s27e1OPUkR1O5YMNWzZrfHjPxhFD+1dxa8cObpWbKY8J/avavJ+VhRDku4bK6t5d4QbV23e/1TUVjxpBZ2fXfn8eT/XqdeB8zx+gS01LT0xKEQpFSjylRm6uSv/Z+TSkUmlCQnJaZqaRvr6xiaFCNwP7Y9hLFkwnE3qLxRJBfGJaeoayMr+Ru+u/TqNbWFgUEBQCNABAHRpNJpMlJaclp6RIJFJzc9NaVxGqQ0hYRE5OXmmdyezzP/BT56SkpsfECpSV+Y4OtuxaV9UUFRXHCuJzcvJUVJSdGziwq1/VMW91shCC/D+QlZ0P9bNPndO4ifTpk9rv3qTJ963oAGBkaGBkaPAd3AiXy7WyMmd/9LPaNTclO1ur6oc3q6mptmrepO7zKodjbmb8dfTVuYFDPX+axkYGlX3FvApUVVUqu7XqmLfWWQhBvkvqo/jx58zlOLvU8n7s7PmLluBzRRAEQf4PqZfR72pqytt3SJ89lT57Sld/8gp1NW6Hjkpdu333zXQEQRAE+e+IOgBQFLdzF27nLviEEARBEKSaYKMWQRAEQbCljiBfhbatm4V9fIZ2QBAEwZY6giAIgqCoIwiCIAiCoo4gCIIgCIo6giAIgiAo6giCIAiCoo4gCIIgCIo6giAIgiAo6giCIAiCoKgjCIIgCIKijiAIgiAo6giCIAiCoKgjCIIgCIKijiAIgiAIijqCIAiC/J+Bn179z1BYVBQfnyQUifT1dMxMTdAg/yGKioqkMhoANNTV0BoIgnznop6UlDJr4cqK6y3MTbt1bte+bUsDfd16bsfKboFhxdK5LZp6VJFg4IipAODkaLdp/XL2+vyCwvOXb77z9U9OTmVWWlqYjR05qEWzRswaiUQ6dMwMAPBwd1n76yLM2fWKjdv2BwSGAsDfJ/aqqqp8tfOu/n2Hf0AwAPx9Yo+qqur3Z9ijJ/+5dfcxAAwf3G/E0J/Ym/YcOPHkuTcAdGrfasGcKexNF67c/OfCDQD4oWfn6ZNG1zfjn79889zFG9UpNBCkIvXa/R6fkHTq7KVfVv6RlJRa5wfPyc0bOGLqwBFT123cVZ8tsGTFBs/bD9mKDgCC+MQ/tu67dPX2lzu19+v3xD5f9Cxfmc+/KYlEGhAYggVHPcGjoQtZCA6LkNvkHxhMFvwCguQ2BYdGyO2OINhS/yI42NuMGzUYAKRSWZwg4cnzVzGxgsys7L2HTvyx9pf/hEGZW5DD2sq8podKSUtf88fOjIwsAHBr6PRD985amhopaWkBn0JevH4nk8rOnr9qZKTfsV0rzMdfB5FYvGXHQT//wCXzZ7Ru2QQN8s1xd3NWUuJKJNKg4DCJRKqkxGVqw+TFAYCcnLw4QYKVpTlTLQsJjQQAiqLcGjqhDREU9S+Impqqe0NnstzYw/WHnp3n/7wmOTk1ODQiOkZga2PJTpyRmZWamq7EU3Kws6EoSuEBi4qKU9PTRUKxqalxTbszM7OyExKTAUBDXd3G2qKyU1RxC1UTFh4llUltrCwqc82dPnORFExtWjVdMn86h8MBAHdw7t6lQ6sWTbfuOgQAZ89dadOyKY/Hq7h7QWFRfEKikYGBrq62wuNLpdLU1PT0rCwDXT1TU6M6eYL5BYWxcfHmZqY62posv0JSdk4OAJiZGuvr6f6b2bMSk1N1tbXMzUwrS5OUlJKemQUARob6xkaGVRyNpmlBfKJQKHJ0sP38u5NJZSKRSCqVbdt9aP6cKR3atPj8Y5LHJJXIHBxs+IqeI5vUtIycnFxLCzMVFWWFCRKTkjOzc0yNjaq2M03T6RlZGVlZOppahoZ6XC5XYbKc3Lw4QYIyn29sbKitpfn5t0DTdHJyanpmloW5ma6OVmVpQsIjJWIJxaFsra3U1apyXKuqqrg4OQQEhkok0tDwyIYuDcj6oOAwAFBXVwOAgoLCwOAwRtTDo6KLi4UA4OLsqKmhLvdKCkUiALC1saq6uFCYr6pp/Ipk5+QJ4hP0dLXNTE2qLmfEYnFIeCTQwOFwnBztmUpMZe+Ihoa6qbFRZbkFQVH/2vB5vHatm1++dhsAQsIiiKiLxeLzlz29vH1SU9NJMl0drbatm48bPYRdoMQnJJ27dOPlq3fsNvTAfj+0bd0MAH5dsyUoJJys//AxkPRnnz66i7zkWVk5F656PnzsJZFIS9vZFrOmjm3gaFcn9xUdIzjx13nSyUpRVNfO7aZNGiWXJi0tw/uNLwDo6enMmTGBKDpD29bNWjZv5PPuY2papv+nkGZN3MsdP1Zw8M+/wiOjyc92bZrPmjZOjVV1SM/IOnvuqs+7D4VFxWSNnY1V967te/fsAgAikXj4uFlM4rPnr549f9XB3mbr779WvJd/Ll6/cNkTAP5Yu9TzzuPXb31lUtnPC2YQO0dGx567dOPde38mfcsWjWdOGcdIPhMK0Lypx5QJI/YdPvUpMJRs6tqp7ZiRg+WK/uhYwbmL133efWTWtGvTfPSwAaamxnIHbNmicc+uHQ8cOZ2ZmW1nY7Vx3bLq31RlqKgor/h57vpNu4NCwnfuOQIAn6PrD554PXjoxTwmFRXlpo0ajh01xMS4pJryMSB4ze87AGDW9HE2VhZHjv9DElMUNXJY/yED+rAFICs798y5K4+fviQ/G7o0mDtzgsLzet55dN3zfnpGJlMNbduq2bjRQ9gKl52Td/GK58MnXiKRmKxxcrQbNWyAh7tL7W5h7KhB9rbWfx7/OzEpBQDUVFUG/PTDgB978XjliiDv1+8vXPGMjYsnP7lcTr8+PUYPH1iFerk1dCKvUlBIOCPqgcHhAGBtaU7TEBwa/ikojORtAAgOLnnx3V3Lmuk+b/3OX74ZFRNXUldQUenRreOwwT8yVYrK8tX2Tb/VyPgVRFpy3fP+let3ioqLAcDU1KiyPn6pVOp559GN2w8yM7PJGmNjw0H9evXo1lGuHlDxHWnfpsXIYT9hdC2Ker1AS1ODLOTl55MK8oYte0n4Cbs4u3X3sUxGM9KYnZO3ftPu1LQMdrKIyJhtuw+vVJ7btLwEVmwprlizNSUljb0yNi5+7cZdq5bPd3K0/8w78vMP2rB5t1QqY6r8j568UKsQPBUQVKJtndu3VlPUlJ88fuSPvbsDgImxEQAw7zUtk23ZeYjdB//y1TuxRLJ88WxG0Zev2sSU6YSomLg/j/+tpanRroYqRUHJie8/fO79uqQKRUqZgE8hG7bsYVSBKT2Tk9PWr1qspVmu5SejZdt3H2HkAQAeP/P2CwjavnEVUwPw8w/auH2/SChi7/jy1buATyG/rZjvYGvDtoNEItl36GR2Tm7dZkgVFeWVv8zdtP2A/6eQHbv/lEqknTu0rsVxzl26ef7SDfaa4mKh9xvf5JT0zRtWyGlYcnLaydMXmBoYTdN/n7+mzOf/1LcH41Vasnx9VnbZzQYGh+3Yc1RFVb6JdvHqrb/PX2OvKSwsevjkRUJiyh9rl5I1KWnpa37fKRfGERoetXbTrmWLZzOhWzW6hezs3C07DjK3UFhU/Pf5a4HBYWtWLGTSXLlx56+/r5RXMtm1m/cyMrIWzJksV69l8HB3JVFvIaFl3eqfAkMAwNLSDACCQ8ODgsNomibZkul993ArqaBcunr77Pmr5Tx8xcU3bt0PDA5bvXyBpqZ61fmq+sav2NzfsGUPuzRLSkrdsuNg+7YtKzbQt+w89M7Xn70yJSXt4NEzIeFRc2dMYHRd4Tvy4tXboNDw31cvZSpbCIr6NyMyKoYsGBroA8CrN77kHXBxclgwZ4qOjtanTyEnz14SxCfeuf+kX+9upMV27+FToujdu7SfPH6Eiory42fe+w6dpGna8+6jpk3cJ44flpmevXH7fgBo4Gg3ZsRAUj0HgJN/XSKKPnxwv07tW6trqL5+43vyzKXCwqI9B0/u2rxarm0hR2FhUcVAKg11deJmkMlkJ06fJ4res1vHAT/21NTS9Hn74fCJv+V2YRorDvaK/cZGhvpGhvqsAqJkISgkXF1NbfTwgVYWZm/e+5HWg89bv+CwCJcGDgBwzfMeUfSe3TpOHj9CKBK9fed35OQ/xcXCv85dbdu6uZISd91vi4NDw0lZ2bNbx/ZtW1TmwaOh5MRPvV43buTaqX0bPR1tAwNdoVC0/8hpkUispaU5buSgls0b5+cX3H347MatB3GChFNnLs2dOZF9HN8Pn4yNDdf8uqiBg21CUtLxUxeDQ8MzM7OvXL89adxwAMjLy9+68yAprUYPH9itS3upVHrz9oMbtx7k5uVv2/XngZ0bOBwOYwffD5/U1dWGD+7n1MAeAGp0U1Wjqqr627IFJ/66cPve4937j9G0rEvHtjU6QnpG1tUbdwBAT0d70fxprs6OEZExl67d8nn3MSom7qmXd/cuHcq1rW8/NDE27N2ri7qG+r0HTwODwgDg/KUbfX/oSjznF654ElFxcXKYOG6YhZlpeET0gaN/hUVEsY8jEouJDBsZ6s2eNsHD3SUvL3/jtv3BoRHBoeFBweGuLo4AsPfACaLoLVs0Hj9qsIaG+vsPAUdP/FNYVHzoz9ON9m7k83g1vYWbtx82buQ6btQQEyODwJCIg3+ezszK/ugf9MrHt03LpsR9deafqwBga205ZsRAF2eH+ITkvy9e8/sY5OXt08jdpVuX9gqN6eRgp6amWlhYFBQSTrrVYwXxmdk5AGBnbUnUODsnNyomzt7WWiaTBYdEEP8Ecbx9DAgiis5X5i+cPcXD3TkjPfPPk/98CgyNjIo5fvr8/NmT2O+XXL6qvvEr4uXtQ0ozPV2dGVPHNnRxTE1LP3X20v1HzytWxYiim5ubzJ85ycLcNCombsfeI5mZ2U+eebs4O/To0kHuHRk+uF+vHp0LCwuev/C5cMUzMzP75NmLyxbNQs1DUf9myGSyC5c9n7/0IV44NxcnAGjezGPLhhXRsYKWzZuQBlzTJu6p6RmHj50FgNCIaCLq8fFJ5CA/9elOCu6undoq83mqKip2djYA4GBrk6OfR9Kos3rBBYJEL28fAOjSsS0zQqZn904ZWdkXLnsmJiYHBoc19nCt4rIjImNWrd8ut7JJo4arli8AgE+BoXHxiQDgaG87c+rYEj9z53aZWTnybYXSNo2GRo1HNq9ftYT0ILZs0RgAiK4L4hKIqI8Y8lOrZo0Tk5J79egMAHw+r2vndh8Dgp6/9ElJSUvPyDI00HNv6JyXV8BUp6oTJdC2dfOfF0xnft578JTUjcaOHEiKY01NjYljh0VGxQYGhz178XrKhJFyg7vmz55ErtDBzvbnhTOmzv5ZKpU9fuY9YcxQDofz4tVb0s7r0LblkIF9yC4Txw6LjokLCAxNSUn76B/UpLEbczQul7N+1RJb67I4jBrdVH5BYXSpM1YhrVs2UVJSunHr/p4DJ2gZ3bVzu+o/ID1d7W2//xoVKzAzNXa0twUARwfbMcMHEpdpeESMnCIaGOhtWr+cmKt188YLlq5NTEopLCpOTU03NTUuLhY+eepNHuXSRbPIe+Hh7jJ/5sQVa7awj5OUnEIqlM4NHIgjXVNTY+GcKR8/BdnaWFlbWgBAnCAhMDiMCP+iOVOVlfnkdcjMzP774nUzc5OU5FRLS/Oa3oK2tuYvC2eRl7F5E/dpk0Zt2n4AAJ488yaifu3mPZqmOVzOonlTLcxNyQEXzpkye8HK/ILCJ89fVSbqFEU1adTw5at3xcXCiOgYZ0d7UukhFWKuUkn7Pig4zN7WOjI6tqCgEAAaubsQX8KjJyU+8wmjh5DgRzVL86ULZk6fu6youNj79bspE0ey+/Xl8lX1jV+Rh4+9yMKMyaOJ/8PGynLpgpkz5i3Pzctnl4SPHr8gyz8vmE4eU0OXBvNnTlr9+w4AePrsFRF15h1p26oZKb50dbRGDusfER0TEhLBpSixWMz7t7gNBEW9LomJEZBsKpVKY2LjyesHAKNHDDQ01AcAPo/n6GDLDk5JSEz6VOqpzs8veROMjAzIwqadh0YM6dfY3VWzeo7lj5+CmHYwu8FtoK/HaHbVol41YREl7uXWrcrFTrdv00JO1Lml3kuJWFKjU5iaGDMxQQDQtJEbEXUSWQYAGupq7m7O7m7OTJERFhkdK0gs6ebIyzc00KvFrTVvVm5Arf+nEqeiuro625LWVhaBwWFSqSw6RkDahQRjY0Oi6ARdHa1GHq6+Hz4VFBTGxSfYWFl+Ki2pu5cv3Lt1aU+6VANDwtmibmJixFb0mhIXl1CxciYHh8tRVVEpKi7ee+gkTdOVqY6CHTkcS0tzS9ZjysvLf1PaCcpkYwY3VyemAsTj8Zo0akh6ptPSM01NjaNj4kRiMfEns+MTXZwdjY0N2R1JBvr6HC5HJpU9f+mjqaXZsW1LB3sbQ0N9tgAHlMY0dO7Qlig6oVePzr16dGbCx2p6C82bNmL7RZo39eAr80VCUXhENHFE+/oFkMpWVnZOVnaOXIYJCYtg/OcKPPANnUn0THBIuLOjPelQ19HWsrWxpChKT0c7MzsnKCSiX58ejIueqdJ9DAgizXS2u0VTU71D+1b3Hz4TicVhYZFV5KvqG79io4WMrFNVUWnOmnBCVVWleVOPx8+8y5x2ggTiePBwcyaKXtrv4GJubpKQkBwcGlFUVKyqqsK8Iz27d2Sfa9bUcVqamlW7GBEU9S9Cbl6+XH85l8sZPrjfwH4/sHuwLlzxfPvWL5P15svR94cuT569zMrOTUxM3rHnCADY21o3btSwW6d2VYd5Mx1j5y/fhMsKE+RUfQtVz/1SVFRUKlrack0xiqJoxscHoF3a5ZxVw15huWhhprdeJis7eGh45A3P+x8+BpHwnDpBQ11doSW37DhYiamz2T8rBgyTDhcAyMrMsbGyzMrKKa21lHuCTA1GrgDVUPvic7dpaWiQAr0WiMXiazfvvfb5EFWlP6C0YlTumaqoqJT2fQAAFJQ6dXS05ePJjQ312WZRV1Md0r/PhSueAHDrzqNbdx6pqal6uLm0bdO8XatmpNM6s9TOJuXflIrR4DW6BbmARy6Xa2xoIIhPzM7JFYvFUqksv6CQPESFdSmpVJadk1dZwLx76XDzyKhYAAgOCSMqSyoBHu6uT71eBQaFAkBEZCxb1IVCEWkTGxroyfXFWFmYkYXk1KryVfWNL4dQKCJxuLq62nKVFSbnl+b/kjeFRM+wsba0SEhIpmk6NT3d2tKC9Y4YV/1yISjqXwlTU6NO7cvCjjQ11Js1cWePWfIPCN64fT8ZkWJsbGhsZKCioqyjpSXXC6Wnq7tt48qbtx/FxSeEhkUVFBRGRsdGRsfevPNwwazJbVo1rewCGN+UvZ2NXEmqUIxrbO7SyrKsNFCu1IUIbEUnDRSmnOraSUGXbWpaRkpqGgCYGBkaGupX/xouX7t95lyJV8De1lpdQ01fTzc7O+fDx8A6fJQ8Po+p5ShMoKxSzvculcg7JOjSWoiMpgGAx+OylYzV6qVKay3SOrx+Kyvzdb8trtqFfvPOo3sPngHA3BkTauR+z8rOXbZqIxm+oaam6mBnzeFynBzsz1++WRtTKykxjT95LaywZuSw/iYmhgGfQuMECZHRsYWFRa99fF/7+D50d1m2aJaqqgqv8jjzz7kFqVT+6TAZXiqV8fk8UqnV1FC3tbWq5hHY5YaZqXFiUkpkdFxSUiqpULq7OZXmQOenXq/y8guSklIiY2JJ0UE8/EzjlaYrelOofz1vTY1fLv+XekEqJpMrCpSUlBSuBwBOaW1AKpGx3xEERb2+YGigP3xwvyoSXLjqWVws5PN5K36e26hULby8fSqGlujp6o4fPYS8bJHRsa/evL96455IKNp14FjTxm5sv2K5Cyidj7Zv765dOrSp8xvU1CgJ5k9MLleFjykNi2O778isGt6v340c1r9iO+nY6XM+b/0A4Ldf5lVf1AuLii5duw0AFuamv/4818SkpMJ0+PjZur1Tg9LGwexp442qcXmJSSnsyUMAgEwSAADaOprA6gFJSk5hH5CJnzA0NKjD69dQV6ui072oqOj3rfsCg8Ioilo4b2pNB7bdvf+EyOHYUYP69e5BpCUzK6t2os6MEEkqn6kkEmlCQnLF9F06tiWu5ry8Ar+AwGs37kXFxPkHBF+/9WDEkH5M50ty+WkcCwqLZFIZCQWvxS3El7+S4mIhUyEgTWQjI4OUlDRNLc3aTXLc2KNhYlJKcnJqcGjJiLVGbq6lm0qc58FhkcQgjdxdS5WbQ5zk6WkZxcVCdmOduWDjKvNVTY3PqjRwtLQ0c3Pz0tPlTy1ISGSnNCq9gMTkFLmDkAAdiqJICVDZO5KZlaWpoYG96f8n/Me+0paSkg4AFmamjVjtv4ovz7MXr//6+/I/F6+Tl8fR3nbcqCFNm7gBgEgoSkvPKFfJZdWUmRmm/PzKNVuTU9IeP30ZFR3HjFyvHfZ2Ja2Qp17eQtawk/sP5SslOtqa7Vo3B4DsnNytuw6xB8wAwMtXb4mia2trurvVYKrLzMxs4udo3Kgho+gAkJCQJJeSYloqtWoBu5X22X/wC2Cv/xQc+vLVu4rz/ublF3h5v2F+RkXHkXAtVRUVawsL9qNhIptKTFcaQ9SoGnb4zJtiFH39pr0kGmverEm1GKqeUurR7d6lPdNYjI9Prt31WFqY8ZX5ABAcGh4VXeYJ93rlIzeiLzEp+brn/d37j8cJEoD0HLdtOWXiiJJMnpwCAA1LR28/9XrFHo748LHXhBmLVq7bGh0rqMUt+PoFsB/6wycvSM+FU+ncDx4NnQEgKSlFIEhg7+j16q3vh4DsnLx/yW+l2eO5tw8AWJqbMTVdXR0t4vd6+fpt6bnKRqiT0eoisZhMFE/ILyh84e0DACoqys5OjnVi/Io42FsTR8XDJy/KiprktLfvP7KTmZgYGhsbAkBgUFisoKz2HxAUQp6ji5MDmWOgsnfk8LGzE6Yt2rTjgLD8UDcERf3bY2VpBgDxiUnBpVPHvH3/8ebtB3LJHj/zvnLj7oXLnldv3iU+q8jo2KioONICI52ympoapL85Mio2PDKaBOwYGxl26dQWAJ6/fHPir4sxcQKZTJaWlnHgz1N7D51cvHy9ID6x6itMS884f/lmxT/yNjo3cCDlS2Zm9p4Dx5KSUvMLCm/celDR0wAAo0cMMjLUAwD/gOBFv6w9dvr8a58PD554bd11ePueIyTN1AkjaxT/YlI6vZS/f1B6RhYAiMWSK9fvMOFRFZvavh8+paZlxMQJavSk2rdubmZmAgBnz1+7c/9JSlo6AAQGh+3ed3zb7sNr/tghN34dAI6dOv/hY2BRUXF4RPT2PX+SlV07tyU32L5NCzNTY+KYuXT1dnZOXnpG1om/LvoHBAGAq7Nj40YNq+8/qN1NkSbmhi37gkPDKYpaNH9a7QapW5iX9Nc+83pN3LYCQeKJMxdr6W1T4nbrVOL8377nz/DI6OJi4fsPAcdOnpNLmZGZffLMxader3bvP04kVigUkTmOAMDWxgoATIwNSTs+NS1j94HjSUkpuXl5l6/dPv3PZZlUFheXYGxkUItbkEplW3Ydio4RFBUVvXrjy4SFdutcEl3Yr3d3LpdD0/S23X++8vHNLyiUSqWPn77cuefI+s17jp78u2ojMIPOSVQmEwdaotxuzgDw0T+oNHFZrOtPfbpzuBwAOHn20pu3H4qKigSChC07DpC+9j69ujHOic80fkU6l4bmnT1/lZw6Kjpu886DFVsOgwf0LjnFriPkFIHBYbv2HiMrhwwoGQzCfkcuX7udlZ2bkJi0a99Rn3cfC4uKi4uFlXkoke+J/1g8ZN9eXX39PolE4hVrtlhbWeQXFGRkZDVr4v7+Q7nm4Igh/SIioguLik+fvXz6bLmAtwljhjKTYrZo1ujZizcFBYVLf/0DAI4f3Karqz1u1JCQsIikpNQbt+7fuHWfve+40YPlpqqtSFJSKvnCkhxmZibWlhYURc2bOXHVhu0FBYXeb3yZ8rRfn+6Pnr4sLCxi72JooLdmxaK1m3anpKRl5+R63n7oefshO8Go4QNqOleMkhK3d8/OV2/ci4tPnDbnFwc7m8TklMLCoqaN3Xz9PrFTWltZmJoaJSWlhkVETZ+7zNrKYteW1dU/EY/Hmz113PrNu/PyC/48Xq5EVlVRmT1tPJ9fzhnYwNGOQ1FyH9dp4GA3evgA5oAzp439ffPe4mIhmQ+OSaatrTljytjqzOP7mTclEok3bt8fFBzG5XI+Z5rYzh3bXPe8l19QePz0has37mpra8fECpo1cY+JFdTugGNHDgwJjYiOFSQmpZDMDACO9rbaOprs6fzcXJ3at2nx4tXbqJi4WQvLTaVnY23JRO+PHTkoJDwiKSnV+/U7ZkIh4uadObVkasKa3kLnDq3f+vovWraOvbJn907t2jQvafJamo0fPeT46Qtx8YlywZWW5mbjRw2p2gLqaqquzo5BIeEkWkVuUncPVyfP2w/JcD4nRzu2Tltamo8bOfjkmYsioYiMsmPnyeGDf6wr41ekQ5sWvr7+T71eFxcLmVOrqan269P9Zvk3vXvn9u/ef/R591GQkMicoqRI/KErE5zPfkfOnLvKhM4AgI621tQJI1DwsKVe72jaxH3m1LFkSufYuHgKqFnTx/Xv21MumYuT46Z1y5nygim2lsyfzh53NHnCyIE/9WJCakkQr4625sa1y/r06qrP+t6rva31b7/MYwfh1xo7W6u1Kxd5uLuQ9gGXy/mhZ+dxlZRZpqbGWzf82qdXV2PWVFBKStxO7Vvt2Lxq6MC+tbiAEUP69+3djcQlhUdGm5kYr1u1uOIMuHw+b/niOZ3atyLexThBQk19d64ujhvX/dK2VVN1VkBAq5ZNNq9fVjF6jgJYNG+ae2lZrK6u1rNbx5W/zGNPjO/m4vT76qWtWjZRK43w19HW6tKx7aZ1yy0tTKtzSZ97UxQo8/lcLmfJ/BmfM0Gsgb7uL0tmEU9GVnZuckrq4AF9Fs+bVusDqqqqrlqxsEuntqql4YeNG7kuXTRTbhY2iqIWzp0yefwIPVa8J5/P69Or62/L5jFxG7q62r+v/uWHnp31dHXYFazfls1ngkxregu6utq/LJpJ0gOAkaHe2JGDppefHblfnx4rlsxu6NKACa0g1/b7mp+rEzXCxEBQFOXm6lTeOe/M1Pkq5r3+P/Zcumimq7Mjl1tiLjNT48ED+qxZsUCu6vk5xlfInBkThg/5iXkcluZmy5bMqhisTlHUzwtmjh01iBnrweFyHO1tZ08fN2XCyHJ3WuEdAYC2rZqu+21JFR9TQL4nqKzu3RXn1Nt36+1FSyTSpKQUKS21sjCv+s0pKipKTk2XyqRGBvpy85IyyGSyiMgYALCztZab2zIjMysjI8vQQL+yb6J8DkVFRfEJyRbmJtX81jL5bIZIJLa0MGePiK0dQqEoNi5eW0fL+N/iy8icHloaGuzh7zWCpunEpOQiodDcxFjuZpkptZkPyWdmZWVl59pYWVT2lRHyyOITknhKSsyU77XwotfupiQSaUh4BJkK6TOhaTo1PSM3N8/a0qI64lHNy4sRCPR19Sob/cUYkPVBF/0qZlZPS8vIzsk1NDRQmOX+9RaYud8H/tRr3KghNE0nJafQNF21wIjFkpg4gYqyiomxwdcM7xKJxbFx8cZGBpWVFXVifIUIBAlcJa6pifG/OpzyCwoTE5OtLM2rng+RvCNSmQw/6PL/Q1Z2/n9V1JHvhoqijnxPyIk6GgRBvrSoc9AQCIIgCPJ9gKKOIAiCIN8JOBsw8k0rlRyKfHmCHZOFfDcYGxqQ5/v53yxGEKQ6YJ86giAIgvznwT51BEEQBPmuQFFHEARBEBR1BEEQBEFQ1BEEQRAEQVFHEARBEARFHUEQBEFQ1BEEQRAEQVFHEARBEARFHUEQBEEQFHUEQRAEQVFHEARBEARFHUEQBEGQbyzqPJ7CDXRBAVoHQRAEQeo/NF0q6hxdXcVJMjPRTAiCIAjyHxB1mQwAuByKA5WIuiw7C82EIAiCIPUfKU0DAEVRHI6dnWLZT0lBMyEIgiBI/UcmlQGAEpfD4TZrjqKOIAiCIP9dRCIJAPB4Shylxo0UxsrJQoLRTAiCIAhSz5FKZRKpFACU+VwOpa6u1L27AlH386OzsFsdQRAEQeo1RcUiAFDhKwEAh6Io/ugxChrrUqn02VM0FoIgCILU52a6WCwBAFVVPkVRHADg6Osp9e6jIOnDh2gvBEEQBKm3FBQUA4CKMo/LoUpa6gCgPHYsx8ZGLqksKpIWCNBkCIIgCFIfFb2wWCqTKXE56qp8IEPayD9KQ115zVrKwEBuB/GZv9BqCIIgCFLfyC8oEokkHA6loa5MUUCa6ByqFI6RkfKataCmxt5H6vVcessTbYcgCIIg9QSZVJabVygWSymK0lRT5nLKpJyiS5HJZDQNspwc4bq1smDWeDYOh7dwsVK3bmhHBEEQBPmWci6ji4tFQpEYAJS4XE11PofDoSjgMLpOFB0AZDIZWaSlUsmD++Lbd8DSUurSUOLsIjMw4vG4Ksp8DpfDoSg0K4IgCIJ8BWgaaJlMStNSiVQikYolUgDgUJSqipIyn0dRFKPoQDrTiaKXl3agaVomo4tFYqFIwnz7BUEQBEGQbwhFgTJfSYXPIy1zpn1OFB0ASkSd6Dqj7iVNdpqmaVoskQlFEhlNk5Y82hRBEARBvqKQUxwOxaEoZb4ST4npPgemG51R9HKijiAIgiDIfxoOmgBBEARBvg/+B5j0GsRPNtEBAAAAAElFTkSuQmCC",
    "tile_communication_log.png": "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",
    "tile_quick_log.png": "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",
    "tile_sensory_overview.png": "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",
    "tile_sgoal_quick_track.png": "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",
    "tile_smartar_goal_builder.png": "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",
    "tile_student_files.png": "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",
}


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
