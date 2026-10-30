"""
helper_book.py
──────────────
"My Helper Book": a small, personal communication book for one student, made of
a few big-square pages (how I feel, I need, help me, when I'm angry...).
Used by pages/73_Talk_Book.py (🧰 Helper Books tab).

• Symbols come from data/talk_book/symbols.json (the site's licensed Boardmaker
  symbols, cut from the Talk Book), referenced as "page:index", e.g. "23a:3".
• Each student's helper book is saved in talk_book_profiles under the key
  "helper:<INITIALS>" — no extra table needed.
• build_pdf() makes the printable version (pocket booklet or full A4 pages).
"""
from __future__ import annotations

import base64
import copy
import io
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "talk_book"
MAX_SQUARES = 6

PAGE_COLOURS = {
    "Blue": "#4cc0f2", "Green": "#6be04a", "Yellow": "#f7e733", "Orange": "#ff9a3d",
    "Pink": "#ff8fd0", "Purple": "#b9a6f5", "Red": "#f26464", "Teal": "#5fd3c8", "Grey": "#c4c9cf",
}


def _sq(label, sym=None, icon="", say=""):
    return {"label": label, "sym": sym, "icon": icon, "say": say, "photo": None}


DEFAULT_HELPER = {
    "title": "My Helper Book",
    "pages": [
        {"title": "I feel", "colour": "Yellow", "on": True, "squares": [
            _sq("happy", "23a:3"), _sq("sad", "23b:0"), _sq("angry", "23b:1", say="I feel angry"),
            _sq("worried", "23a:10", say="I feel worried"), _sq("scared", "23a:2", say="I feel scared"),
            _sq("frustrated", "23a:6", say="I feel frustrated")]},
        {"title": "My body feels", "colour": "Blue", "on": True, "squares": [
            _sq("tired", "5a:5", say="I feel tired"), _sq("sick", "5a:0", say="I feel sick"),
            _sq("hurt / sore", "5a:4", say="I am hurt"), _sq("hot", "5b:1", say="I am hot"),
            _sq("hungry", "5b:2", say="I am hungry"), _sq("thirsty", "5b:6", say="I am thirsty")]},
        {"title": "I need", "colour": "Green", "on": True, "squares": [
            _sq("a break", "11a:5", say="I need a break"), _sq("help", "1a:9", say="I need help"),
            _sq("the toilet", "1b:8", say="I need to go to the toilet"), _sq("a drink", "18a:7", say="I need a drink"),
            _sq("quiet", "24b:5", say="I need quiet"), _sq("space", "1b:2", say="I need some space")]},
        {"title": "Help me", "colour": "Orange", "on": True, "squares": [
            _sq("help me please", "1a:9"), _sq("I don't know", "1a:7"),
            _sq("it's too hard", "4d:4"), _sq("I don't understand", "23b:5"),
            _sq("show me", "1a:10", say="Can you show me?"), _sq("I can do it myself", "4d:3")]},
        {"title": "When I'm angry I can", "colour": "Red", "on": True, "squares": [
            _sq("stop", "1a:5", say="I'm going to stop"), _sq("go for a walk", "10d:5", say="I need to go for a walk"),
            _sq("sit down", "10d:4", say="I'm going to sit down"), _sq("squeeze my hands", "10e:3"),
            _sq("breathe slowly", "6b:5", say="I'm going to breathe slowly"),
            _sq("lie down and rest", "10d:8", say="I need to lie down")]},
        {"title": "Please", "colour": "Purple", "on": True, "squares": [
            _sq("stop", "1a:5", say="Please stop"), _sq("don't touch", "1b:6", say="Please don't touch me"),
            _sq("give me space", "1b:2", say="Please give me some space"), _sq("wait", "1a:5", say="Please wait"),
            _sq("I'm sorry", "1b:5"), _sq("thank you", "1b:4")]},
        {"title": "People who help me", "colour": "Teal", "on": True, "squares": [
            _sq("my teacher", "9f:0", say="I want my teacher"), _sq("my SSO", "9f:4", say="I want my SSO"),
            _sq("a friend", "9f:5", say="I want a friend"), _sq("mum", "9a:4", say="I want mum"),
            _sq("dad", "9a:8", say="I want dad"), _sq("someone", "5b:3", say="I want someone")]},
        {"title": "Yes / no", "colour": "Grey", "on": True, "squares": [
            _sq("yes", "4a:8"), _sq("no", "4a:0"), _sq("I don't know", "1a:7"),
            _sq("finished", "1a:6"), _sq("more", "1a:2"), _sq("not now", "22a:4", say="Not now")]},
    ],
}


def default_helper() -> dict:
    return copy.deepcopy(DEFAULT_HELPER)


@lru_cache(maxsize=1)
def symbols() -> dict:
    """{"23a:3": {"label": "happy", "page": "Feelings", "img": "data:image/webp;base64,..."}}"""
    p = DATA_DIR / "symbols.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def symbol_options() -> list[str]:
    """Symbol keys sorted by label, for a searchable selectbox."""
    s = symbols()
    return sorted(s, key=lambda k: (s[k]["label"].lower(), k))


def symbol_label(key: str | None) -> str:
    if not key:
        return "— no symbol (use emoji / photo) —"
    v = symbols().get(key)
    return f'{v["label"]}  ·  {v["page"]}' if v else key


def square_image(sq: dict) -> str | None:
    """Data URL for a square: its own photo first, then its symbol."""
    if sq.get("photo"):
        return sq["photo"]
    if sq.get("sym") and sq["sym"] in symbols():
        return symbols()[sq["sym"]]["img"]
    return None


def for_component(helper: dict) -> dict:
    """The shape the Talk Book component expects for helper mode (images resolved)."""
    pages = []
    for p in helper.get("pages", []):
        if not p.get("on", True):
            continue
        pages.append({
            "title": p.get("title", ""),
            "colour": PAGE_COLOURS.get(p.get("colour"), "#c4c9cf"),
            "squares": [{"label": s.get("label", ""), "say": s.get("say") or s.get("label", ""),
                         "icon": s.get("icon", ""), "img": square_image(s)}
                        for s in p.get("squares", []) if s.get("label")][:MAX_SQUARES],
        })
    return {"title": helper.get("title") or "My Helper Book", "pages": pages}


def photo_to_data_url(file_bytes: bytes, max_px: int = 300) -> str:
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes))).convert("RGB")
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ──────────────────────────────────────────────────────────────────────────
# Printable PDF
# ──────────────────────────────────────────────────────────────────────────
def _img_reader(data_url: str):
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    raw = base64.b64decode(data_url.split(",", 1)[1])
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[3])
    return ImageReader(bg), bg.size


def _hex(c):
    from reportlab.lib.colors import HexColor
    return HexColor(c)


def _fit_text(c, text, font, size, max_w, min_size=6):
    while size > min_size and c.stringWidth(text, font, size) > max_w:
        size -= 0.5
    return size


def _wrap(c, text, font, size, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_page(c, x, y, w, h, page: dict, scale: float):
    """One helper-book page inside the box (x, y, w, h). scale 1 = A6."""
    pad = 6 * scale
    band = 22 * scale
    colour = PAGE_COLOURS.get(page.get("colour"), "#c4c9cf")
    c.setStrokeColor(_hex("#8a96a3"))
    c.setLineWidth(1)
    c.setFillColor(_hex("#ffffff"))
    c.roundRect(x + pad / 2, y + pad / 2, w - pad, h - pad, 8 * scale, stroke=1, fill=1)
    # title band
    c.setFillColor(_hex(colour))
    c.roundRect(x + pad, y + h - pad - band, w - 2 * pad, band, 6 * scale, stroke=0, fill=1)
    c.setFillColor(_hex("#17202b"))
    title = page.get("title", "")
    fs = _fit_text(c, title, "Helvetica-Bold", 14 * scale, w - 4 * pad)
    c.setFont("Helvetica-Bold", fs)
    c.drawCentredString(x + w / 2, y + h - pad - band + (band - fs) / 2 + fs * 0.18, title)
    # 2 x 3 grid
    sqs = [s for s in page.get("squares", []) if s.get("label")][:MAX_SQUARES]
    gx, gy = x + pad, y + pad
    gw, gh = w - 2 * pad, h - 2 * pad - band - pad
    cols, rows = 2, 3
    gap = 4 * scale
    cw, ch = (gw - gap * (cols - 1)) / cols, (gh - gap * (rows - 1)) / rows
    for i, s in enumerate(sqs):
        col, row = i % cols, i // cols
        sx = gx + col * (cw + gap)
        sy = gy + gh - (row + 1) * ch - row * gap
        c.setStrokeColor(_hex(colour))
        c.setLineWidth(1.6 * scale)
        c.setFillColor(_hex("#ffffff"))
        c.roundRect(sx, sy, cw, ch, 5 * scale, stroke=1, fill=1)
        label_fs = 9.5 * scale
        lines = _wrap(c, s["label"], "Helvetica-Bold", label_fs, cw - 6 * scale)[:2]
        text_h = len(lines) * label_fs * 1.1 + 3 * scale
        img = square_image(s)
        box_h = ch - text_h - 6 * scale
        box_w = cw - 8 * scale
        if img:
            try:
                rdr, (iw, ih) = _img_reader(img)
                k = min(box_w / iw, box_h / ih)
                dw, dh = iw * k, ih * k
                c.drawImage(rdr, sx + (cw - dw) / 2, sy + text_h + 2 * scale + (box_h - dh) / 2, dw, dh)
            except Exception:  # noqa: BLE001
                pass
        c.setFillColor(_hex("#17202b"))
        c.setFont("Helvetica-Bold", label_fs)
        for j, ln in enumerate(lines):
            c.drawCentredString(sx + cw / 2, sy + 3 * scale + (len(lines) - 1 - j) * label_fs * 1.1, ln)


def _draw_cover(c, x, y, w, h, title: str, name: str, scale: float):
    pad = 6 * scale
    c.setStrokeColor(_hex("#8a96a3"))
    c.setFillColor(_hex("#ffffff"))
    c.roundRect(x + pad / 2, y + pad / 2, w - pad, h - pad, 8 * scale, stroke=1, fill=1)
    c.setFillColor(_hex("#1A7A7A"))
    c.roundRect(x + pad, y + h * 0.55, w - 2 * pad, h * 0.45 - pad, 6 * scale, stroke=0, fill=1)
    c.setFillColor(_hex("#ffffff"))
    fs = _fit_text(c, title, "Helvetica-Bold", 22 * scale, w - 4 * pad)
    c.setFont("Helvetica-Bold", fs)
    c.drawCentredString(x + w / 2, y + h * 0.8, title)
    if name:
        fs2 = _fit_text(c, name, "Helvetica-Bold", 18 * scale, w - 4 * pad)
        c.setFont("Helvetica-Bold", fs2)
        c.drawCentredString(x + w / 2, y + h * 0.66, name)
    help_img = symbols().get("1a:9", {}).get("img")
    if help_img:
        try:
            rdr, (iw, ih) = _img_reader(help_img)
            k = min((w * 0.35) / iw, (h * 0.18) / ih)
            c.drawImage(rdr, x + (w - iw * k) / 2, y + h * 0.33, iw * k, ih * k)
        except Exception:  # noqa: BLE001
            pass
    c.setFillColor(_hex("#17202b"))
    msg = "If I show you this book, please be patient and help me point to what I need."
    fs3 = 9 * scale
    c.setFont("Helvetica", fs3)
    for j, ln in enumerate(_wrap(c, msg, "Helvetica", fs3, w - 6 * pad)):
        c.drawCentredString(x + w / 2, y + h * 0.25 - j * fs3 * 1.3, ln)


def build_pdf(helper: dict, layout: str = "pocket", name: str = "", page_titles: list[str] | None = None) -> bytes:
    """layout 'pocket' = 4 A6 pages per A4 sheet (cut along the dashed lines, stack in order, staple);
    layout 'a4' = one page per A4 sheet (desk, wall or break space)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pages = [p for p in helper.get("pages", []) if p.get("on", True)
             and (page_titles is None or p.get("title") in page_titles)]
    title = helper.get("title") or "My Helper Book"
    items = [("cover", None)] + [("page", p) for p in pages]

    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(title + (f" — {name}" if name else ""))

    if layout == "a4":
        m = 28
        for kind, p in items:
            if kind == "cover":
                _draw_cover(c, m, m, W - 2 * m, H - 2 * m, title, name, 2.0)
            else:
                _draw_page(c, m, m, W - 2 * m, H - 2 * m, p, 2.0)
            c.showPage()
    else:
        qw, qh = W / 2, H / 2
        slots = [(0, qh), (qw, qh), (0, 0), (qw, 0)]
        for start in range(0, len(items), 4):
            for (kind, p), (sx, sy) in zip(items[start:start + 4], slots):
                if kind == "cover":
                    _draw_cover(c, sx + 6, sy + 6, qw - 12, qh - 12, title, name, 1.0)
                else:
                    _draw_page(c, sx + 6, sy + 6, qw - 12, qh - 12, p, 1.0)
            c.setStrokeColor(_hex("#9aa5b1"))
            c.setDash(4, 4)
            c.setLineWidth(0.6)
            c.line(qw, 0, qw, H)
            c.line(0, qh, W, qh)
            c.setDash()
            c.setFont("Helvetica", 7)
            c.setFillColor(_hex("#9aa5b1"))
            c.drawString(8, 4, "Cut along the dashed lines, stack in order and staple or ring-bind. Laminate for longer life.")
            c.showPage()
    c.save()
    return buf.getvalue()
