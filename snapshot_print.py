"""
snapshot_print.py — print / download builder for the Student Snapshot
=====================================================================

Used by: pages/72_Student_Snapshot.py

The Snapshot page describes a report ONCE as a list of sections made of
simple blocks; this module draws those blocks as a PDF (for printing) and
as a Word document (for editing). Both files therefore always contain the
same text.

Block types
  {"t": "p",       "text": str, "style": "" | "muted" | "callout"}
  {"t": "bullets", "items": [str, ...]}
  {"t": "kv",      "items": [(label, value), ...]}            two-column facts
  {"t": "table",   "head": [str, ...], "rows": [[str, ...]],  cells may hold \\n
                   "widths": [fraction, ...], "shade": {(row, col): "#hex"}}
  {"t": "img",     "png": bytes, "width": fraction of page width}
  {"t": "sub",     "text": str}                                small heading

Report
  {"title": str, "subtitle": str, "facts": [(label, value), ...],
   "footer": str, "sections": [{"title": str, "blocks": [...]}, ...]}
"""

from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

TEAL = "#1A7A7A"
AMBER = "#C8760A"
INK = "#1f2d2d"
MUTED = "#5a6b6b"
LINE = "#c9dada"
HEAD_FILL = "#e8f2f2"


# ──────────────────────────────────────────────────────────────────────────
# Charts (matplotlib → PNG bytes), shared by both outputs
# ──────────────────────────────────────────────────────────────────────────
def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return buf.getvalue()


def _style_ax(ax, title: str):
    ax.set_title(title, fontsize=10, color=INK, loc="left", fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#9fb3b3")
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="y", color="#e6eeee", linewidth=0.8)
    ax.set_axisbelow(True)


def chart_weekly_incidents(weeks: list, normal: list[int], critical: list[int]) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    labels = [w.strftime("%-d %b") for w in weeks]
    x = range(len(weeks))
    ax.bar(x, normal, color=TEAL, label="Incidents", width=0.65)
    ax.bar(x, critical, bottom=normal, color="#c0392b", label="Critical", width=0.65)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=0 if len(labels) <= 12 else 45, ha="center" if len(labels) <= 12 else "right")
    ax.yaxis.get_major_locator().set_params(integer=True)
    _style_ax(ax, "Incidents by week")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    return _fig_to_png(fig)


def chart_hbar(items: list[tuple[str, int]], title: str, colour: str = TEAL) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    items = list(items)[:6][::-1]
    fig, ax = plt.subplots(figsize=(3.5, 0.45 + 0.34 * max(1, len(items))))
    labels = [(k if len(k) <= 34 else k[:33] + "…") for k, _ in items]
    vals = [v for _, v in items]
    ax.barh(labels, vals, color=colour, height=0.6)
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v}", va="center", fontsize=8, color=INK)
    ax.set_xticks([])
    _style_ax(ax, title)
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    return _fig_to_png(fig)


def chart_goal_levels(goals: list, levels: list, weeks: list) -> bytes:
    """Small multiples, one panel per goal: each week's sessions by GAS level,
    achieved levels stacked above the line, 'Not yet' below it.
    goals:  [(title, {date: {level: count}}), ...]
    levels: [(level, colour, above_line), ...] in stacking order"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    n = len(goals)
    up_max = max((sum(c.get(l, 0) for l, _c, up in levels if up) for _t, wl in goals for c in wl.values()), default=1)
    dn_max = max((sum(c.get(l, 0) for l, _c, up in levels if not up) for _t, wl in goals for c in wl.values()), default=0)
    fig, axes = plt.subplots(n, 1, figsize=(7.2, 0.5 + 1.75 * n), sharex=True, squeeze=False)
    x = list(range(len(weeks)))
    for ax, (title, wl) in zip(axes[:, 0], goals):
        pos = [0] * len(weeks)
        neg = [0] * len(weeks)
        for level, colour, up in levels:
            vals = [wl.get(w, {}).get(level, 0) for w in weeks]
            if not any(vals):
                continue
            if up:
                ax.bar(x, vals, bottom=pos, color=colour, width=0.55, edgecolor="white", linewidth=1)
                pos = [a + b for a, b in zip(pos, vals)]
            else:
                ax.bar(x, [-v for v in vals], bottom=[-v for v in neg], color=colour, width=0.55,
                       edgecolor="white", linewidth=1)
                neg = [a + b for a, b in zip(neg, vals)]
        ax.axhline(0, color=INK, linewidth=1.2)
        ax.set_ylim(-(dn_max + 0.8) if dn_max else -0.8, up_max + 1)
        ticks = [t for t in ax.get_yticks() if float(t).is_integer() and -dn_max <= t <= up_max]
        ax.set_yticks(ticks)
        ax.set_yticklabels([str(abs(int(t))) for t in ticks])
        _style_ax(ax, title)
        ax.title.set_fontsize(9)
    axes[-1, 0].set_xticks(x)
    axes[-1, 0].set_xticklabels([w.strftime("%-d %b") for w in weeks], rotation=0 if len(weeks) <= 12 else 45,
                                ha="center" if len(weeks) <= 12 else "right")
    handles = [Patch(color=c, label=l.capitalize()) for l, c, _up in levels
               if any(wl.get(w, {}).get(l, 0) for _t, wl in goals for w in weeks)]
    fig.legend(handles=handles, loc="upper left", ncol=len(handles), frameon=False, fontsize=8,
               bbox_to_anchor=(0.0, 1.0 + 0.02 / n), title="Sessions at:", title_fontsize=8,
               alignment="left")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.09 / max(1, n ** 0.5)))
    return _fig_to_png(fig)


def pair_png(left: bytes | None, right: bytes | None) -> bytes | None:
    """Two small charts side by side as one image (keeps both outputs simple)."""
    imgs = [b for b in (left, right) if b]
    if not imgs:
        return None
    if len(imgs) == 1:
        return imgs[0]
    from PIL import Image
    a, b = (Image.open(io.BytesIO(x)).convert("RGB") for x in imgs)
    h = max(a.height, b.height)
    gap = 40
    out = Image.new("RGB", (a.width + b.width + gap, h), "white")
    out.paste(a, (0, 0))
    out.paste(b, (a.width + gap, 0))
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────
# PDF (reportlab)
# ──────────────────────────────────────────────────────────────────────────
def render_pdf(report: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    buf = io.BytesIO()
    margin = 14 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=report.get("title", "Student Snapshot"), author="CLC-LBU portal")
    W = A4[0] - 2 * margin

    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=12.5,
                          textColor=colors.HexColor(INK), alignment=TA_LEFT)
    small = ParagraphStyle("small", parent=base, fontSize=8.3, leading=10.5)
    muted = ParagraphStyle("muted", parent=base, fontSize=8.5, textColor=colors.HexColor(MUTED))
    h1 = ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=17, leading=21,
                        textColor=colors.white)
    sub = ParagraphStyle("subw", parent=base, textColor=colors.white, fontSize=9.5)
    h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12, leading=15,
                        textColor=colors.HexColor(TEAL), spaceBefore=4, spaceAfter=3)
    h3 = ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=9.5,
                        textColor=colors.HexColor(INK), spaceBefore=3, spaceAfter=1)
    cell = ParagraphStyle("cell", parent=base, fontSize=8.3, leading=10.4)
    cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")

    def P(text, style=base):
        return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)

    story = []
    # Title band
    band = Table([[P(report.get("title", ""), h1)], [P(report.get("subtitle", ""), sub)]],
                 colWidths=[W])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(TEAL)),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
    ]))
    story += [band, Spacer(1, 5)]
    if report.get("facts"):
        story += [_pdf_kv(report["facts"], W, cell, cellb, colors, Table, TableStyle, P, cols=3),
                  Spacer(1, 4)]

    for sec in report.get("sections", []):
        head = [P(sec["title"], h2)]
        flow = []
        for b in sec.get("blocks", []):
            t = b.get("t")
            if t == "p":
                st_ = {"muted": muted, "callout": base}.get(b.get("style", ""), base)
                para = P(b["text"], st_)
                if b.get("style") == "callout":
                    box = Table([[para]], colWidths=[W])
                    box.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef6f1")),
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#2E7A48")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]))
                    flow += [box, Spacer(1, 3)]
                else:
                    flow += [para, Spacer(1, 3)]
            elif t == "sub":
                flow.append(P(b["text"], h3))
            elif t == "bullets":
                for it in b.get("items", []):
                    flow.append(Paragraph("•&nbsp;&nbsp;" + escape(str(it)).replace("\n", "<br/>"),
                                          ParagraphStyle("li", parent=base, leftIndent=10,
                                                         firstLineIndent=-8)))
                flow.append(Spacer(1, 3))
            elif t == "kv":
                flow += [_pdf_kv(b["items"], W, cell, cellb, colors, Table, TableStyle, P,
                                 cols=b.get("cols", 2)), Spacer(1, 4)]
            elif t == "table":
                head_row = [P(h, cellb) for h in b.get("head", [])]
                rows = [[P(c, cell) for c in r] for r in b.get("rows", [])]
                widths = [W * f for f in (b.get("widths") or [1 / max(1, len(head_row))] * len(head_row))]
                tbl = Table([head_row] + rows if head_row else rows, colWidths=widths, repeatRows=1 if head_row else 0)
                style = [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(LINE)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
                if head_row:
                    style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(HEAD_FILL)))
                off = 1 if head_row else 0
                for (r, c), hexc in (b.get("shade") or {}).items():
                    style.append(("BACKGROUND", (c, r + off), (c, r + off), colors.HexColor(hexc)))
                tbl.setStyle(TableStyle(style))
                flow += [tbl, Spacer(1, 5)]
            elif t == "img" and b.get("png"):
                from PIL import Image as PILImage
                im = PILImage.open(io.BytesIO(b["png"]))
                w = W * b.get("width", 1.0)
                h = w * im.height / im.width
                flow += [Image(io.BytesIO(b["png"]), width=w, height=h), Spacer(1, 4)]
        # keep each heading with the start of its content
        if flow:
            story += [KeepTogether(head + flow[:2])] + flow[2:]
        else:
            story += head
        story.append(Spacer(1, 6))

    footer_txt = report.get("footer", "")

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(margin, 9 * mm, footer_txt[:150])
        canvas.drawRightString(A4[0] - margin, 9 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _pdf_kv(items, W, cell, cellb, colors, Table, TableStyle, P, cols=2):
    pairs = [(k, v) for k, v in items if v not in (None, "")]
    rows, row = [], []
    for k, v in pairs:
        row += [P(k, cellb), P(v, cell)]
        if len(row) == cols * 2:
            rows.append(row)
            row = []
    if row:
        row += [P("", cell)] * (cols * 2 - len(row))
        rows.append(row)
    if not rows:
        rows = [[P("", cell)] * (cols * 2)]
    label_w = W * (0.13 if cols == 3 else 0.2)
    val_w = (W - label_w * cols) / cols
    tbl = Table(rows, colWidths=[label_w, val_w] * cols)
    style = [("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(LINE)),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for c in range(0, cols * 2, 2):
        style.append(("BACKGROUND", (c, 0), (c, -1), colors.HexColor(HEAD_FILL)))
    tbl.setStyle(TableStyle(style))
    return tbl


# ──────────────────────────────────────────────────────────────────────────
# Word (python-docx)
# ──────────────────────────────────────────────────────────────────────────
def _shade(cell, hexc: str):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexc.lstrip("#"))
    tcPr.append(shd)


def _cell_text(cell, text: str, bold: bool = False, size: float = 8.5):
    from docx.shared import Pt
    lines = str(text or "").split("\n")
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    for i, ln in enumerate(lines):
        if i:
            p = cell.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
        r = p.add_run(ln)
        r.bold = bold
        r.font.size = Pt(size)


def _fix_widths(tbl, widths_cm: list[float]):
    """Make Word (and LibreOffice) honour column widths: fixed layout + grid + every cell."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm
    tbl.autofit = False
    tblPr = tbl._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    grid = tbl._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths_cm):
        gc.set(qn("w:w"), str(int(w * 567)))
    for ci, w in enumerate(widths_cm):
        if ci < len(tbl.columns):
            tbl.columns[ci].width = Cm(w)
    for row in tbl.rows:
        for ci, cell in enumerate(row.cells):
            if ci < len(widths_cm):
                cell.width = Cm(widths_cm[ci])


def render_docx(report: dict) -> bytes:
    from docx import Document
    from docx.enum.section import WD_ORIENT  # noqa: F401
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(1.5))
    sec.top_margin = sec.bottom_margin = Cm(1.6)
    W = 18.0  # usable width in cm
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)

    teal = RGBColor(0x1A, 0x7A, 0x7A)
    muted = RGBColor(0x5A, 0x6B, 0x6B)

    # Title band
    band = doc.add_table(rows=1, cols=1)
    c = band.rows[0].cells[0]
    _shade(c, TEAL)
    p = c.paragraphs[0]
    r = p.add_run(report.get("title", ""))
    r.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p2 = c.add_paragraph()
    r2 = p2.add_run(report.get("subtitle", ""))
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def kv_table(items, cols=2):
        pairs = [(k, v) for k, v in items if v not in (None, "")]
        if not pairs:
            return
        nrows = (len(pairs) + cols - 1) // cols
        t = doc.add_table(rows=nrows, cols=cols * 2)
        t.style = "Table Grid"
        for i, (k, v) in enumerate(pairs):
            rr, cc = divmod(i, cols)
            kc, vc = t.rows[rr].cells[cc * 2], t.rows[rr].cells[cc * 2 + 1]
            _cell_text(kc, k, bold=True)
            _shade(kc, HEAD_FILL)
            _cell_text(vc, v)
        lw = W * (0.13 if cols == 3 else 0.2)
        vw = (W - lw * cols) / cols
        _fix_widths(t, [lw if ci % 2 == 0 else vw for ci in range(cols * 2)])

    if report.get("facts"):
        kv_table(report["facts"], cols=3)

    for s in report.get("sections", []):
        h = doc.add_heading(s["title"], level=2)
        for run in h.runs:
            run.font.color.rgb = teal
        for b in s.get("blocks", []):
            t = b.get("t")
            if t == "p":
                if b.get("style") == "callout":
                    box = doc.add_table(rows=1, cols=1)
                    box.style = "Table Grid"
                    _cell_text(box.rows[0].cells[0], b["text"], size=10)
                    _shade(box.rows[0].cells[0], "#eef6f1")
                    doc.add_paragraph().paragraph_format.space_after = Pt(0)
                else:
                    p = doc.add_paragraph()
                    r = p.add_run(str(b["text"]))
                    if b.get("style") == "muted":
                        r.font.size = Pt(8.5)
                        r.font.color.rgb = muted
            elif t == "sub":
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(1)
                r = p.add_run(b["text"])
                r.bold = True
            elif t == "bullets":
                for it in b.get("items", []):
                    doc.add_paragraph(str(it), style="List Bullet")
            elif t == "kv":
                kv_table(b["items"], cols=b.get("cols", 2))
                doc.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == "table":
                head = b.get("head", [])
                rows = b.get("rows", [])
                ncol = len(head) if head else (len(rows[0]) if rows else 1)
                tbl = doc.add_table(rows=(1 if head else 0) + len(rows), cols=ncol)
                tbl.style = "Table Grid"
                off = 0
                if head:
                    for ci, htxt in enumerate(head):
                        _cell_text(tbl.rows[0].cells[ci], htxt, bold=True)
                        _shade(tbl.rows[0].cells[ci], HEAD_FILL)
                    off = 1
                for ri, row in enumerate(rows):
                    for ci, ctxt in enumerate(row):
                        _cell_text(tbl.rows[ri + off].cells[ci], ctxt)
                for (ri, ci), hexc in (b.get("shade") or {}).items():
                    _shade(tbl.rows[ri + off].cells[ci], hexc)
                widths = b.get("widths") or [1 / ncol] * ncol
                _fix_widths(tbl, [W * f for f in widths])
                doc.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == "img" and b.get("png"):
                doc.add_picture(io.BytesIO(b["png"]), width=Cm(W * b.get("width", 1.0)))

    if report.get("footer"):
        fp = sec.footer.paragraphs[0]
        fr = fp.add_run(report["footer"])
        fr.font.size = Pt(7.5)
        fr.font.color.rgb = muted

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d")
