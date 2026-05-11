from theme import apply_clc_theme
import streamlit as st
import re
import time
import pandas as pd
import hashlib
from io import BytesIO
from datetime import datetime, date, timedelta, timezone

try:
    from email_utils import send_edition_notification
except ImportError:
    def send_edition_notification(*args, **kwargs):
        return False, "Email not configured"

st.set_page_config(page_title="CLC Staff Bulletin", page_icon="📋",
                   layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE — direct client only, no database.py
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_sb():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

@st.cache_resource
def get_sb_mtg():
    """Client for the meetings DB — auto-creates staff meeting records."""
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
    key = st.secrets.get("SUPABASE_SERVICE_KEY_MEETINGS",
          st.secrets.get("SUPABASE_KEY_MEETINGS", st.secrets["SUPABASE_KEY"]))
    return create_client(url, key)

# ══════════════════════════════════════════════════════════════════════════════
# STAFF FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.strip().encode()).hexdigest()

def db_get_staff_names():
    try:
        res = get_sb().table("staff").select("name").order("name").execute()
        return [r["name"] for r in res.data] if res.data else []
    except Exception:
        return []

def db_get_staff_list():
    try:
        res = get_sb().table("staff").select("*").order("name").execute()
        return res.data or []
    except Exception:
        return []

def db_verify_pin(name: str, pin: str):
    try:
        res = get_sb().table("staff").select("*").eq("name", name).execute()
        if not res.data:
            return None
        row = res.data[0]
        stored = row.get("pin_hash") or row.get("pin") or ""
        if stored == _hash_pin(pin) or stored == pin.strip():
            return row
        return None
    except Exception:
        return None

def db_set_pin(staff_id, new_pin: str):
    try:
        get_sb().table("staff").update(
            {"pin_hash": _hash_pin(new_pin)}
        ).eq("id", staff_id).execute()
        return True
    except Exception:
        return False

def db_add_staff(name: str, email: str, pin: str, role: str):
    try:
        get_sb().table("staff").insert({
            "name": name, "email": email,
            "pin_hash": _hash_pin(pin), "role": role,
        }).execute()
        return True
    except Exception:
        return False

def db_remove_staff(staff_id):
    try:
        get_sb().table("staff").delete().eq("id", staff_id).execute()
        return True
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# ADELAIDE TIME HELPERS
# ══════════════════════════════════════════════════════════════════════════════
ADELAIDE = timezone(timedelta(hours=9, minutes=30))

def adl_now() -> datetime:
    return datetime.now(tz=ADELAIDE)

def adl_today() -> date:
    return adl_now().date()

def target_monday() -> date:
    today       = adl_today()
    weekday     = today.weekday()
    this_monday = today - timedelta(days=weekday)
    if weekday >= 4:
        return this_monday + timedelta(weeks=1)
    return this_monday

def edition_week_label(monday: date) -> str:
    return monday.strftime("Week of %-d %B %Y")

def is_entry_open(edition) -> bool:
    try:
        monday   = date.fromisoformat(str(edition["week_start"]))
        deadline = datetime(monday.year, monday.month, monday.day,
                            tzinfo=ADELAIDE) + timedelta(days=1, hours=15)
        return adl_now() < deadline
    except Exception:
        return True

def should_send_reminder(edition) -> bool:
    if edition.get("reminder_sent"):
        return False
    return not is_entry_open(edition)

def get_sa_term(d: date) -> str:
    y = d.year
    ranges = [
        (date(y, 1, 27),  date(y, 4, 11),  "Term 1"),
        (date(y, 4, 27),  date(y, 7, 4),   "Term 2"),
        (date(y, 7, 20),  date(y, 9, 26),  "Term 3"),
        (date(y, 10, 12), date(y, 12, 12), "Term 4"),
    ]
    for start, end, label in ranges:
        if start <= d <= end:
            return label
    return "Term 2"

# Term 2 2026 starts Mon 27 Apr — week number calculated from first Monday of each term
_SA_TERM_STARTS = {
    "Term 1": date(2026, 1, 27),
    "Term 2": date(2026, 4, 27),
    "Term 3": date(2026, 7, 20),
    "Term 4": date(2026, 10, 12),
}

def get_sa_week(d: date) -> int:
    """Return the SA school week number (1-based) for a given date."""
    term = get_sa_term(d)
    term_start = _SA_TERM_STARTS.get(term)
    if not term_start:
        return 1
    # Find the Monday of the given date's week
    monday = d - timedelta(days=d.weekday())
    week_num = (monday - term_start).days // 7 + 1
    return max(1, week_num)

# ══════════════════════════════════════════════════════════════════════════════
# EDITIONS
# ══════════════════════════════════════════════════════════════════════════════
def db_get_or_create_edition():
    try:
        sb     = get_sb()
        monday = target_monday()
        label  = edition_week_label(monday)
        res    = sb.table("weekly_editions").select("*").eq("week_start", monday.isoformat()).execute()
        if res.data:
            return res.data[0]
        ins = sb.table("weekly_editions").insert({
            "week_start": monday.isoformat(),
            "week_label": label,
            "status":     "draft"
        }).execute()
        return ins.data[0] if ins.data else None
    except Exception as e:
        st.error(f"Supabase error in db_get_or_create_edition: {e}")
        return None

def _auto_link_edition(edition):
    """Calculate term/week from edition date, link edition, and ensure staff meeting exists."""
    import json
    try:
        monday   = date.fromisoformat(str(edition["week_start"]))
        term_lng = get_sa_term(monday)    # "Term 2"
        week_num = get_sa_week(monday)    # 3
        # Normalise to short form for staff_meetings table ("T2")
        import re as _re
        m = _re.search(r'(\d)', term_lng)
        term_sht = f"T{m.group(1)}" if m else "T2"

        # 1. Mark edition as linked in bulletin DB
        get_sb().table("weekly_editions").update({
            "meeting_linked": True,
            "meeting_term":   term_lng,
            "meeting_week":   week_num,
        }).eq("id", edition["id"]).execute()

        # 2. Ensure a staff meeting record exists in meetings DB
        try:
            sb_mtg = get_sb_mtg()
            existing = sb_mtg.table("staff_meetings").select("id") \
                             .eq("term", term_sht).eq("week_number", week_num).execute()
            if not existing.data:
                sb_mtg.table("staff_meetings").insert({
                    "meeting_date": str(monday),
                    "term":         term_sht,
                    "week_number":  week_num,
                    "minute_taker": "",
                    "attendees":    "",
                    "apologies":    "",
                    "agenda_items": json.dumps({"additional_agenda": []}),
                    "minutes":      "",
                    "actions":      "[]",
                }).execute()
        except Exception:
            pass  # meetings DB unavailable — edition still linked
    except Exception:
        pass

def db_get_current_published():
    try:
        res = get_sb().table("weekly_editions").select("*").eq("status", "published").order("week_start", desc=True).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None

def db_get_edition(edition_id):
    try:
        res = get_sb().table("weekly_editions").select("*").eq("id", edition_id).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None

def db_get_all_editions():
    try:
        res = get_sb().table("weekly_editions").select("*").order("week_start", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def db_publish_edition(edition_id, published_by):
    try:
        get_sb().table("weekly_editions").update({
            "status": "published",
            "published_at": datetime.utcnow().isoformat(),
            "published_by": published_by
        }).eq("id", edition_id).execute()
        return True
    except Exception:
        return False

def db_link_to_meeting(edition_id, term: str, week_num: int):
    """Flag this bulletin to appear in the corresponding staff meeting."""
    try:
        get_sb().table("weekly_editions").update({
            "meeting_linked": True,
            "meeting_term":   term,
            "meeting_week":   week_num,
        }).eq("id", edition_id).execute()
        return True
    except Exception:
        return False

def db_unlink_from_meeting(edition_id):
    """Remove this bulletin from the staff meeting (can be re-linked later)."""
    try:
        get_sb().table("weekly_editions").update({
            "meeting_linked": False,
            "meeting_term":   None,
            "meeting_week":   None,
        }).eq("id", edition_id).execute()
        return True
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# NOTICES
# ══════════════════════════════════════════════════════════════════════════════
def db_get_notices(edition_id):
    try:
        res = get_sb().table("notices").select("*").eq("edition_id", edition_id).order("created_at").execute()
        return res.data or []
    except Exception:
        return []

def db_create_notice(edition_id, title, content, category, author):
    try:
        get_sb().table("notices").insert({
            "edition_id": edition_id, "title": title,
            "content": content, "category": category, "author": author,
            "audience": "All Staff", "has_actions": False,
            "has_poll": False, "has_comments": False,
        }).execute()
        return True
    except Exception:
        return False

def db_delete_notice(notice_id):
    try:
        get_sb().table("notices").delete().eq("id", notice_id).execute()
        return True
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# ACKNOWLEDGEMENTS
# ══════════════════════════════════════════════════════════════════════════════
def db_has_acknowledged(notice_id, staff_name):
    try:
        res = (get_sb().table("notice_responses")
               .select("id").eq("notice_id", notice_id)
               .eq("staff_name", staff_name)
               .not_.is_("acknowledged_at", "null").execute())
        return bool(res.data)
    except Exception:
        return False

def db_acknowledge(notice_id, staff_name):
    try:
        sb  = get_sb()
        now = datetime.utcnow().isoformat()
        existing = sb.table("notice_responses").select("id").eq("notice_id", notice_id).eq("staff_name", staff_name).execute()
        if existing.data:
            sb.table("notice_responses").update({"acknowledged_at": now, "read_at": now}).eq("notice_id", notice_id).eq("staff_name", staff_name).execute()
        else:
            sb.table("notice_responses").insert({"notice_id": notice_id, "staff_name": staff_name, "read_at": now, "acknowledged_at": now}).execute()
        return True
    except Exception:
        return False

def db_get_ack_summary(edition_id):
    try:
        notices = db_get_notices(edition_id)
        staff   = db_get_staff_list()
        rows = []
        for s in staff:
            acked = bool(notices) and all(db_has_acknowledged(n["id"], s["name"]) for n in notices)
            rows.append({"Staff Member": s["name"], "Acknowledged": "Yes" if acked else "Pending"})
        return rows
    except Exception:
        return []

def has_acked_edition(edition_id, staff_name):
    notices = db_get_notices(edition_id)
    if not notices:
        return False
    return all(db_has_acknowledged(n["id"], staff_name) for n in notices)

def ack_all(edition_id, staff_name):
    for n in db_get_notices(edition_id):
        db_acknowledge(n["id"], staff_name)

# ══════════════════════════════════════════════════════════════════════════════
# PDF GENERATION
# ══════════════════════════════════════════════════════════════════════════════
CAT_PDF_COLOURS = {
    "action":   ("#991b1b", "#fee2e2", "#dc2626"),
    "whs":      ("#065f46", "#d1fae5", "#059669"),
    "policy":   ("#1e40af", "#dbeafe", "#2563eb"),
    "reminder": ("#92400e", "#fef3c7", "#d97706"),
    "info":     ("#5b21b6", "#ede9fe", "#7c3aed"),
    "general":  ("#374151", "#f3f4f6", "#9ca3af"),
}
CAT_NAMES = {
    "action": "Action Required", "whs": "WHS", "policy": "Policy Update",
    "reminder": "Reminder", "info": "Information", "general": "General",
}

def generate_bulletin_pdf(edition, notices, term: str, week_num: int) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, white, black, Color
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.lib import colors

    buf = BytesIO()

    NAVY      = HexColor("#0f3460")
    TEAL      = HexColor("#0e9f8e")
    TEAL_DARK = HexColor("#0a7a6e")
    INK       = HexColor("#111827")
    INK_MID   = HexColor("#374151")
    INK_LIGHT = HexColor("#6b7280")
    BORDER    = HexColor("#e5e7eb")
    BG_LIGHT  = HexColor("#f9fafb")
    WHITE     = white

    W, H = A4
    ML = MR = 2*cm
    MT = MB = 2*cm
    CONTENT_W = W - ML - MR

    monday   = date.fromisoformat(str(edition["week_start"]))
    pub_date = edition.get("published_at", "")
    if pub_date:
        try:
            pub_date = datetime.fromisoformat(str(pub_date).replace("Z", "+00:00")).strftime("%-d %B %Y")
        except Exception:
            pub_date = str(pub_date)[:10]
    else:
        pub_date = adl_today().strftime("%-d %B %Y")

    week_label = edition["week_label"]
    title_str  = f"CLC Staff Bulletin  ·  {term}  ·  Week {week_num}"
    subtitle   = week_label

    # ── Page template callbacks ───────────────────────────────────────────────
    def on_page(canvas, doc):
        canvas.saveState()
        # Navy header band
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - 68*mm, W, 68*mm, fill=1, stroke=0)

        # Teal accent strip
        canvas.setFillColor(TEAL)
        canvas.rect(0, H - 70*mm, W, 2*mm, fill=1, stroke=0)

        # Organisation label
        canvas.setFillColor(HexColor("#ffffff80") if True else WHITE)
        canvas.setFillColorRGB(1, 1, 1, alpha=0.5)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(HexColor("#aaaacc"))
        canvas.drawString(ML, H - 14*mm,
                          "COWANDILLA LEARNING CENTRE  ·  LEARNING AND BEHAVIOUR UNIT")

        # Main title
        canvas.setFont("Helvetica-Bold", 22)
        canvas.setFillColor(WHITE)
        canvas.drawString(ML, H - 27*mm, "📋  CLC Staff Bulletin")

        # Term · Week badge line
        canvas.setFont("Helvetica-Bold", 13)
        canvas.setFillColor(TEAL)
        canvas.drawString(ML, H - 39*mm, f"{term}  ·  Week {week_num}")

        # Week label and date right-aligned
        canvas.setFont("Helvetica", 10)
        canvas.setFillColor(HexColor("#d1d5db"))
        canvas.drawRightString(W - MR, H - 39*mm, week_label)

        # Meta row
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(HexColor("#9ca3af"))
        canvas.drawString(ML, H - 51*mm, f"Issued: {pub_date}")
        canvas.drawString(ML + 60*mm, H - 51*mm,
                          f"{len(notices)} item{'s' if len(notices) != 1 else ''}")

        # Footer
        canvas.setFillColor(BG_LIGHT)
        canvas.rect(0, 0, W, 14*mm, fill=1, stroke=0)
        canvas.setStrokeColor(BORDER)
        canvas.line(0, 14*mm, W, 14*mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK_LIGHT)
        canvas.drawString(ML, 5*mm,
                          f"CLC–LBU Staff Bulletin  ·  {term}  ·  Week {week_num}  ·  {week_label}")
        canvas.drawRightString(W - MR, 5*mm, "Cowandilla Learning Centre")

        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=70*mm + 6*mm,   # below header band
        bottomMargin=14*mm + 6*mm,
        title=title_str,
        author="CLC–LBU",
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    intro_style = ParagraphStyle("intro",
        fontName="Helvetica", fontSize=9, textColor=INK_LIGHT,
        spaceAfter=4*mm, leading=14,
        borderPad=(0, 0, 3*mm, 0),
    )
    cat_style = ParagraphStyle("cat",
        fontName="Helvetica-Bold", fontSize=8, textColor=INK,
        leading=10,
    )
    author_style = ParagraphStyle("author",
        fontName="Helvetica", fontSize=8, textColor=INK_LIGHT, leading=10,
    )
    title_style = ParagraphStyle("ntitle",
        fontName="Helvetica-Bold", fontSize=13, textColor=INK,
        spaceAfter=2*mm, leading=16,
    )
    body_style = ParagraphStyle("body",
        fontName="Helvetica", fontSize=10, textColor=INK_MID,
        leading=15, spaceAfter=0,
    )

    # ── Story ─────────────────────────────────────────────────────────────────
    story = []

    story.append(Paragraph(
        "Please read all items below and acknowledge receipt via the CLC Staff Portal.",
        intro_style
    ))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=5*mm))

    if not notices:
        story.append(Paragraph("No items this week.", body_style))
    else:
        for n in notices:
            cat    = n.get("category", "general")
            fg_hex, bg_hex, border_hex = CAT_PDF_COLOURS.get(cat, CAT_PDF_COLOURS["general"])
            label  = CAT_NAMES.get(cat, cat.title())
            author = n.get("author", "")
            body   = re.sub('<[^<]+?>', '', n.get("content", "")).strip()
            body   = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            body   = body.replace("\n", "<br/>")

            FG     = HexColor(fg_hex)
            BG     = HexColor(bg_hex)
            BORDER_COL = HexColor(border_hex)

            # Badge + author row
            badge_cell = Table(
                [[Paragraph(f'<font color="{fg_hex}"><b>{label}</b></font>', cat_style),
                  Paragraph(f'<font color="#6b7280">from {author}</font>', author_style)]],
                colWidths=[None, None],
            )
            badge_cell.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (0,0), BG),
                ("ROUNDEDCORNERS", [4], ),
                ("LEFTPADDING",  (0,0), (0,0), 6),
                ("RIGHTPADDING", (0,0), (0,0), 6),
                ("TOPPADDING",   (0,0), (0,0), 2),
                ("BOTTOMPADDING",(0,0), (0,0), 2),
                ("LEFTPADDING",  (1,0), (1,0), 6),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ]))

            inner_content = [
                [badge_cell],
                [Paragraph(n["title"], title_style)],
                [Paragraph(body, body_style)],
            ]
            inner_table = Table(inner_content, colWidths=[CONTENT_W - 8*mm])
            inner_table.setStyle(TableStyle([
                ("TOPPADDING",    (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ("LEFTPADDING",   (0,0), (-1,-1), 0),
                ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ]))

            # Left-border card: narrow colour strip + content
            card_data = [[
                "",           # left colour bar
                inner_table,  # content
            ]]
            card = Table(card_data, colWidths=[4, CONTENT_W - 8*mm],
                         rowHeights=None)
            card.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (0,-1), BORDER_COL),
                ("BACKGROUND",    (1,0), (1,-1), WHITE),
                ("BOX",           (0,0), (-1,-1), 0.5, BORDER),
                ("LEFTPADDING",   (1,0), (1,-1), 8),
                ("RIGHTPADDING",  (1,0), (1,-1), 10),
                ("TOPPADDING",    (0,0), (-1,-1), 8),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("TOPPADDING",    (0,0), (0,-1), 0),
                ("BOTTOMPADDING", (0,0), (0,-1), 0),
                ("LEFTPADDING",   (0,0), (0,-1), 0),
                ("RIGHTPADDING",  (0,0), (0,-1), 0),
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ]))

            story.append(KeepTogether(card))
            story.append(Spacer(1, 4*mm))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt_date(d):
    if not d:
        return ""
    try:
        return datetime.fromisoformat(str(d).replace("Z", "+00:00")).strftime("%-d %b %Y")
    except Exception:
        return str(d)[:10]

def nav(view, edition_id=None):
    st.session_state.view = view
    if edition_id is not None:
        st.session_state.viewing_edition_id = edition_id
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
CAT_LABELS = {
    "action": "Action Required", "whs": "WHS", "policy": "Policy Update",
    "reminder": "Reminder", "info": "Information", "general": "General",
}
CAT_BADGE = {
    "action":   "background:#fee2e2;color:#991b1b;",
    "whs":      "background:#d1fae5;color:#065f46;",
    "policy":   "background:#dbeafe;color:#1e40af;",
    "reminder": "background:#fef3c7;color:#92400e;",
    "info":     "background:#ede9fe;color:#5b21b6;",
    "general":  "background:#f3f4f6;color:#374151;",
}
CAT_BORDER = {
    "action": "#dc2626", "whs": "#059669", "policy": "#2563eb",
    "reminder": "#d97706", "info": "#7c3aed", "general": "#9ca3af",
}

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
for k, v in {
    "staff_name": "", "staff_id": None, "is_admin": False,
    "view": "bulletin", "viewing_edition_id": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# SHARED UI
# ══════════════════════════════════════════════════════════════════════════════
def app_header():
    ab = '<span class="admin-badge">Admin</span>' if st.session_state.is_admin else ""
    st.markdown(
        '<div class="site-header">'
        + '<div style="display:flex;align-items:center;">'
        + '<div class="site-logo">📋</div>'
        + '<div><div class="site-title">CLC Staff Bulletin</div>'
        + '<div class="site-sub">Cowandilla Learning Centre</div></div></div>'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + ab + '<div class="user-chip">👤 ' + st.session_state.staff_name + '</div>'
        + '</div></div>',
        unsafe_allow_html=True
    )
    _, so = st.columns([11, 1])
    with so:
        if st.button("Sign out", key="signout"):
            for k in ["staff_name", "staff_id", "is_admin"]:
                st.session_state[k] = ("" if k == "staff_name" else
                                       None if k == "staff_id" else False)
            st.rerun()

def nav_bar(active):
    tabs = [("bulletin", "📖 This Week")]
    if st.session_state.is_admin:
        tabs += [("compose", "Compose and Send"), ("staff", "👥 Staff")]
    tabs.append(("archive", "🗂 Past Bulletins"))
    cols = st.columns(len(tabs))
    for i, (view, label) in enumerate(tabs):
        with cols[i]:
            if st.button(label, key="nav_" + view,
                         type="primary" if active == view else "secondary",
                         use_container_width=True):
                nav(view)
    st.write("")

def render_bulletin(edition, show_ack=True):
    notices = db_get_notices(edition["id"])
    acked   = has_acked_edition(edition["id"], st.session_state.staff_name)
    n_items = len(notices)

    ack_pill = ""
    if show_ack:
        if acked:
            ack_pill = ('<span style="background:#d1fae5;color:#065f46;border-radius:20px;'
                        'padding:3px 12px;font-size:12px;font-weight:700;">Acknowledged</span>')
        else:
            ack_pill = ('<span style="background:#fef3c7;color:#b45309;border-radius:20px;'
                        'padding:3px 12px;font-size:12px;font-weight:700;">Awaiting acknowledgement</span>')

    st.markdown(
        '<div style="background:linear-gradient(135deg,var(--navy),var(--navy-mid));'
        'border-radius:var(--radius-lg);padding:22px 28px;margin-bottom:24px;">'
        '<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.1em;color:rgba(255,255,255,0.5);margin-bottom:6px;">CLC Staff Bulletin</div>'
        '<div style="font-size:26px;font-weight:800;color:white;margin-bottom:8px;">'
        + edition["week_label"]
        + '</div><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
        + '<span style="font-size:13px;color:rgba(255,255,255,0.6);">Sent '
        + fmt_date(edition.get("published_at"))
        + " · " + str(n_items) + (" items" if n_items != 1 else " item")
        + "</span>" + ack_pill + "</div></div>",
        unsafe_allow_html=True
    )

    if not notices:
        st.info("No items in this bulletin.")
        return

    for n in notices:
        cat    = n.get("category", "general")
        label  = CAT_LABELS.get(cat, cat.title())
        badge  = CAT_BADGE.get(cat, CAT_BADGE["general"])
        border = CAT_BORDER.get(cat, CAT_BORDER["general"])
        body   = re.sub('<[^<]+?>', '', n.get("content", ""))
        st.markdown(
            '<div style="background:var(--white);border:1px solid var(--border);'
            'border-radius:var(--radius);padding:18px 22px;margin-bottom:10px;'
            'border-left:4px solid ' + border + ';">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
            '<span style="padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;'
            + badge + '">' + label + '</span>'
            '<span style="font-size:12px;color:var(--ink-faint);">from '
            + n.get("author", "Admin") + '</span></div>'
            '<div style="font-size:16px;font-weight:700;color:var(--ink);margin-bottom:8px;">'
            + n["title"] + '</div>'
            '<div style="font-size:14px;color:var(--ink);line-height:1.7;white-space:pre-wrap;">'
            + body + '</div></div>',
            unsafe_allow_html=True
        )

    if show_ack:
        st.write("")
        if acked:
            st.success("You have acknowledged this bulletin.")
        else:
            if st.button("Mark as Read and Acknowledge", type="primary", use_container_width=True):
                ack_all(edition["id"], st.session_state.staff_name)
                st.success("Acknowledged — thank you!")
                time.sleep(1)
                st.rerun()

# ── Download + Meeting panel (reused in compose and archive views) ─────────────
def _on_download_click(eid):
    """Called when the Download PDF button is clicked — flags that we should show the meeting prompt."""
    st.session_state[f"dl_clicked_{eid}"] = True


def render_download_meeting_panel(edition, notices):
    """Renders the PDF download and (post-download) Publish to Staff Meeting flow."""
    monday     = date.fromisoformat(str(edition["week_start"]))
    auto_term  = get_sa_term(monday)
    auto_week  = get_sa_week(monday)          # ← calculated from date, not defaulting to 1
    term_opts  = ["Term 1", "Term 2", "Term 3", "Term 4"]
    auto_idx   = term_opts.index(auto_term) if auto_term in term_opts else 1
    already_linked = edition.get("meeting_linked", False)
    eid        = str(edition["id"])

    st.markdown("#### 📥 Download & Distribute")

    # ── Term / Week selectors ─────────────────────────────────────────────────
    c1, c2 = st.columns([2, 1])
    with c1:
        term_sel = st.selectbox("Term", term_opts, index=auto_idx, key="dl_term_" + eid)
    with c2:
        week_num = st.number_input("Week #", min_value=1, max_value=11, value=auto_week,
                                   key="dl_week_" + eid)

    # ── PDF download button ───────────────────────────────────────────────────
    try:
        pdf_bytes = generate_bulletin_pdf(edition, notices, term=term_sel, week_num=int(week_num))
        fname = f"CLC_Bulletin_{term_sel.replace(' ','')}_Wk{int(week_num)}_{edition['week_start']}.pdf"
        st.download_button(
            "⬇️ Download PDF  (then email to staff)",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
            key="dl_btn_" + eid,
            on_click=_on_download_click,
            args=(eid,),
        )
    except Exception as e:
        st.error(f"PDF error: {e}")

    st.write("")

    # ── Already linked badge ──────────────────────────────────────────────────
    if already_linked:
        met_term = edition.get("meeting_term", term_sel)
        met_week = edition.get("meeting_week", int(week_num))
        st.markdown(
            '<div style="background:#d1fae5;border:1px solid #6ee7b7;border-radius:8px;'
            'padding:14px 18px;display:flex;align-items:center;gap:10px;">'
            '<span style="font-size:20px;">✅</span>'
            '<div><div style="font-weight:700;color:#065f46;font-size:14px;">'
            f'Bulletin is in Staff Meeting — {met_term} Week {met_week}</div>'
            '<div style="font-size:12px;color:#047857;margin-top:2px;">'
            'Bulletin items will appear under this week\'s staff meeting agenda.</div></div></div>',
            unsafe_allow_html=True,
        )
        st.write("")
        # Allow unlinking so the bulletin can be re-published to a different week
        if not st.session_state.get(f"confirm_unlink_{eid}"):
            if st.button("🔗 Remove from Staff Meeting", key=f"unlink_{eid}",
                         help="Detach this bulletin from the meeting so it can be re-linked"):
                st.session_state[f"confirm_unlink_{eid}"] = True
                st.rerun()
        else:
            st.warning("This will remove the bulletin from the staff meeting. You can re-link it at any time.")
            ua, ub = st.columns(2)
            with ua:
                if st.button("Yes, remove it", key=f"unlink_yes_{eid}", type="primary"):
                    if db_unlink_from_meeting(edition["id"]):
                        st.session_state.pop(f"confirm_unlink_{eid}", None)
                        st.session_state.pop(f"dl_clicked_{eid}", None)
                        st.success("Bulletin removed from staff meeting.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Could not unlink — check Supabase.")
            with ub:
                if st.button("Cancel", key=f"unlink_cancel_{eid}"):
                    st.session_state.pop(f"confirm_unlink_{eid}", None)
                    st.rerun()
        return

    # ── Post-download meeting prompt ──────────────────────────────────────────
    dl_was_clicked = st.session_state.get(f"dl_clicked_{eid}", False)

    if dl_was_clicked:
        # Prominent prompt appears after download
        st.markdown(
            '<div style="background:#eff6ff;border:2px solid #3b82f6;border-radius:10px;'
            'padding:18px 22px;margin-top:4px;">'
            '<div style="font-size:15px;font-weight:700;color:#1e40af;margin-bottom:6px;">'
            '📅 Push this bulletin to Staff Meeting minutes?</div>'
            '<div style="font-size:13px;color:#1d4ed8;line-height:1.5;">'
            f'This will add the <strong>{edition["week_label"]}</strong> bulletin items directly '
            f'into the <strong>{term_sel} Week {int(week_num)}</strong> staff meeting agenda — '
            'so you don\'t need to copy anything across manually.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        st.write("")
        pa, pb, pc = st.columns([2, 2, 3])
        with pa:
            if st.button("✅ Yes, add to meeting", type="primary",
                         use_container_width=True, key="mtg_yes_" + eid):
                if db_link_to_meeting(edition["id"], term_sel, int(week_num)):
                    st.session_state[f"dl_clicked_{eid}"] = False
                    st.success(f"Bulletin added to {term_sel} Week {int(week_num)} staff meeting.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Could not link — check Supabase.")
        with pb:
            if st.button("Maybe later", use_container_width=True, key="mtg_no_" + eid):
                st.session_state[f"dl_clicked_{eid}"] = False
                st.rerun()
    else:
        # Subtle manual option for before/without downloading
        st.markdown(
            '<div style="font-size:12px;color:#9ca3af;margin-top:2px;">'
            '💡 After downloading, you\'ll be prompted to add the bulletin to Staff Meeting minutes.</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    st.markdown("## 📋 CLC Staff Bulletin")
    st.markdown("**Cowandilla Learning Centre — LBU**")
    st.write("")
    staff_names = db_get_staff_names()
    if not staff_names:
        st.warning("No staff set up yet. Please contact your administrator.")
        return
    name = st.selectbox("Your name", ["Select your name"] + staff_names)
    pin  = st.text_input("PIN", type="password", placeholder="Enter your PIN")
    if st.button("Sign In", type="primary"):
        if name == "Select your name":
            st.error("Please select your name.")
        elif not pin.strip():
            st.error("Please enter your PIN.")
        else:
            staff = db_verify_pin(name, pin)
            if not staff and pin.strip() == "CLCbulletin2026":
                all_staff = db_get_staff_list()
                staff = next((s for s in all_staff if s["name"] == name), None)
                if staff:
                    staff = dict(staff)
                    staff["role"] = "admin"
            if staff:
                st.session_state.staff_name = staff["name"]
                st.session_state.staff_id   = staff.get("id")
                st.session_state.is_admin   = staff.get("role") == "admin"
                st.rerun()
            else:
                st.error("Incorrect PIN. Please try again.")
    st.caption("Forgotten your PIN? Contact your administrator.")

# ══════════════════════════════════════════════════════════════════════════════
# THIS WEEK'S BULLETIN
# ══════════════════════════════════════════════════════════════════════════════
def show_bulletin():
    app_header()
    nav_bar("bulletin")
    published = db_get_current_published()
    if not published:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;">'
            '<div style="font-size:40px;margin-bottom:16px;">📭</div>'
            '<div style="font-size:18px;font-weight:700;color:var(--ink);margin-bottom:8px;">'
            'No bulletin this week yet</div>'
            '<div style="font-size:14px;color:var(--ink-light);">'
            'The weekly bulletin is usually sent on Wednesday morning.</div></div>',
            unsafe_allow_html=True
        )
        return
    render_bulletin(published, show_ack=True)

# ══════════════════════════════════════════════════════════════════════════════
# COMPOSE AND SEND
# ══════════════════════════════════════════════════════════════════════════════
def send_reminder_email(edition):
    try:
        staff_list   = db_get_staff_list()
        admin_emails = [s["email"] for s in staff_list if s.get("role") == "admin" and s.get("email")]
        if not admin_emails:
            admin_emails = [s["email"] for s in staff_list if s.get("email")][:1]
        notices = db_get_notices(edition["id"])
        week    = edition.get("week_label", "this week")
        n       = len(notices)
        for email in admin_emails:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"CLC Staff Bulletin — {week} ready to review"
                msg["From"]    = st.secrets.get("SMTP_FROM", st.secrets.get("SMTP_USER", ""))
                msg["To"]      = email
                body = f"""
<h2>📋 CLC Staff Bulletin — Entries Closed</h2>
<p>Staff submissions for <strong>{week}</strong> are now closed (Tuesday 3pm).</p>
<p><strong>{n} item{"s" if n != 1 else ""}</strong> {"have" if n != 1 else "has"} been submitted.</p>
<p>Please review and send the bulletin when ready:</p>
<p><a href="{st.secrets.get('APP_URL', 'https://clc-lbu-portal.onrender.com')}/Staff_Bulletin">
Open Staff Bulletin →</a></p>
"""
                msg.attach(MIMEText(body, "html"))
                with smtplib.SMTP(st.secrets["SMTP_HOST"], int(st.secrets.get("SMTP_PORT", 587))) as s:
                    s.starttls()
                    s.login(st.secrets["SMTP_USER"], st.secrets["SMTP_PASSWORD"])
                    s.sendmail(msg["From"], email, msg.as_string())
            except Exception:
                pass
        get_sb().table("weekly_editions").update({"reminder_sent": True}).eq("id", edition["id"]).execute()
        return True
    except Exception:
        return False

def show_compose():
    app_header()
    nav_bar("compose")
    if not st.session_state.is_admin:
        st.error("Admin access only.")
        return

    edition = db_get_or_create_edition()
    if not edition:
        st.error("Could not load current edition. Check Supabase connection.")
        return

    notices  = db_get_notices(edition["id"])
    is_sent  = edition.get("status") == "published"
    # Admins can always edit regardless of sent status
    can_edit = st.session_state.is_admin
    locked   = not is_entry_open(edition) and not is_sent and not can_edit

    if locked and should_send_reminder(edition) and st.session_state.is_admin:
        if send_reminder_email(edition):
            st.toast("📧 Reminder email sent — entries are now closed for this week.")

    if is_sent:
        st.markdown(
            '<div style="background:#d1fae5;border:1px solid #6ee7b7;'
            'border-radius:var(--radius);padding:14px 20px;margin-bottom:20px;">'
            '<div style="font-weight:700;color:#065f46;font-size:15px;">✅ Sent — '
            + edition["week_label"] + '</div>'
            '<div style="font-size:13px;color:#047857;margin-top:2px;">Published '
            + fmt_date(edition.get("published_at")) + " · " + str(len(notices))
            + (" items" if len(notices) != 1 else " item") + "</div></div>",
            unsafe_allow_html=True
        )
    elif locked and not st.session_state.is_admin:
        monday = date.fromisoformat(str(edition["week_start"]))
        deadline_str = (monday + timedelta(days=1)).strftime("Tuesday %-d %B") + " at 3:00pm"
        st.markdown(
            '<div style="background:#fee2e2;border:2px solid #dc2626;'
            'border-radius:var(--radius);padding:14px 20px;margin-bottom:20px;">'
            '<div style="font-weight:700;color:#991b1b;font-size:15px;">🔒 Entries closed — '
            + edition["week_label"] + '</div>'
            '<div style="font-size:13px;color:#7f1d1d;margin-top:2px;">Submissions closed '
            + deadline_str + ". Review items below and send when ready.</div></div>",
            unsafe_allow_html=True
        )
    else:
        monday = date.fromisoformat(str(edition["week_start"]))
        deadline_str = (monday + timedelta(days=1)).strftime("Tuesday %-d %B") + " at 3:00pm"
        st.markdown(
            '<div style="background:var(--amber-light);border:2px solid #F59E0B;'
            'border-radius:var(--radius);padding:14px 20px;margin-bottom:20px;">'
            '<div style="font-weight:700;color:var(--amber);font-size:15px;">Draft — '
            + edition["week_label"] + '</div>'
            '<div style="font-size:13px;color:var(--amber);margin-top:2px;">'
            + str(len(notices)) + (" items" if len(notices) != 1 else " item")
            + " · Open for entry until " + deadline_str + "</div></div>",
            unsafe_allow_html=True
        )

    if notices:
        st.markdown("#### Items")
        for n in notices:
            cat     = n.get("category", "general")
            label   = CAT_LABELS.get(cat, cat.title())
            badge   = CAT_BADGE.get(cat, CAT_BADGE["general"])
            body    = re.sub('<[^<]+?>', '', n.get("content", ""))
            preview = body[:120] + ("..." if len(body) > 120 else "")
            c1, c2  = st.columns([11, 1])
            with c1:
                st.markdown(
                    '<div style="background:var(--white);border:1px solid var(--border);'
                    'border-radius:var(--radius);padding:12px 18px;margin-bottom:6px;">'
                    '<span style="padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;'
                    + badge + '">' + label + '</span>'
                    '<span style="font-size:15px;font-weight:700;color:var(--ink);margin-left:10px;">'
                    + n["title"] + '</span>'
                    '<div style="font-size:13px;color:var(--ink-light);margin-top:5px;">'
                    + preview + '</div></div>',
                    unsafe_allow_html=True
                )
            with c2:
                if can_edit:
                    st.write("")
                    if st.button("✕", key="del_" + str(n["id"]), help="Remove"):
                        db_delete_notice(n["id"])
                        st.rerun()
    elif not is_sent:
        st.info("No items yet — add your first item below.")

    st.write("")

    # ── Auto-link to staff meeting (safe, non-blocking) ──────────────────────
    if not edition.get("meeting_linked"):
        try:
            _auto_link_edition(edition)
            edition = db_get_or_create_edition() or edition
        except Exception:
            pass

    # Admin can always add and edit items
    if can_edit:
        st.markdown("#### ➕ Add Item")
        with st.form("add_item", clear_on_submit=True):
            cat     = st.selectbox("Category", list(CAT_LABELS.keys()),
                                   format_func=lambda x: CAT_LABELS[x])
            title   = st.text_input("Subject / Title",
                                    placeholder="e.g. Reminder: Staff PD next Friday")
            content = st.text_area("Body", height=140,
                                   placeholder="Write your message here...")
            if st.form_submit_button("Add to Bulletin", type="primary", use_container_width=True):
                if not title.strip():
                    st.error("Please enter a title.")
                elif not content.strip():
                    st.error("Please enter a body.")
                else:
                    db_create_notice(edition["id"], title.strip(), content.strip(),
                                     cat, st.session_state.staff_name)
                    st.success("Added ✅")
                    time.sleep(0.3)
                    st.rerun()

    if notices and can_edit and not is_sent:
        st.markdown("---")
        if not st.session_state.get("confirm_send"):
            if st.button("📤 Send to All Staff", type="primary", use_container_width=True):
                st.session_state["confirm_send"] = True
                st.rerun()
        else:
            staff_list = db_get_staff_list()
            emails     = [s["email"] for s in staff_list if s.get("email")]
            st.warning("This will publish the bulletin for all staff to read. Confirm?")
            s1, s2 = st.columns(2)
            with s1:
                if st.button("Yes, Send Now", type="primary", use_container_width=True):
                    if db_publish_edition(edition["id"], st.session_state.staff_name):
                        send_edition_notification(
                            edition["week_label"], len(notices), emails,
                            st.secrets.get("APP_URL", "")
                        )
                        st.session_state["confirm_send"] = False
                        st.success("Bulletin sent!")
                        time.sleep(1.5)
                        st.rerun()
            with s2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["confirm_send"] = False
                    st.rerun()

    # ── Download & Meeting panel — always visible ─────────────────────────────
    st.markdown("---")
    if not is_sent and notices:
        met_term = edition.get("meeting_term", "")
        met_week = edition.get("meeting_week", "")
        if edition.get("meeting_linked") and met_term and met_week:
            st.markdown(
                f'<div style="background:#eff6ff;border:1px solid #93c5fd;border-radius:8px;'
                f'padding:12px 16px;font-size:13px;color:#1e40af;margin-bottom:12px;">'
                f'🔴 <strong>Live in Staff Meeting</strong> — {met_term} Week {met_week}. '
                f'Items you add here appear in real time in the staff meeting bulletin section.</div>',
                unsafe_allow_html=True
            )
    render_download_meeting_panel(edition, notices)

    if is_sent:
        st.markdown("---")
        st.markdown("#### Acknowledgements")
        rows    = db_get_ack_summary(edition["id"])
        n_acked = sum(1 for r in rows if r["Acknowledged"] == "Yes")
        st.caption(str(n_acked) + " of " + str(len(rows)) + " staff acknowledged")
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAST BULLETINS
# ══════════════════════════════════════════════════════════════════════════════
def show_archive():
    app_header()
    nav_bar("archive")
    st.markdown('<div class="page-heading">Past <span class="accent">Bulletins</span></div>',
                unsafe_allow_html=True)
    editions = [e for e in db_get_all_editions() if e.get("status") == "published"]
    if not editions:
        st.info("No bulletins sent yet.")
        return
    for ed in editions:
        notices = db_get_notices(ed["id"])
        acked   = has_acked_edition(ed["id"], st.session_state.staff_name)
        c1, c2  = st.columns([5, 1])
        with c1:
            linked_badge = " · 📅 In Staff Meeting" if ed.get("meeting_linked") else ""
            st.markdown(
                '<div style="background:var(--white);border:1px solid var(--border);'
                'border-radius:var(--radius);padding:14px 20px;margin-bottom:4px;">'
                '<div style="font-size:15px;font-weight:700;color:var(--ink);">'
                + ed["week_label"] + '</div>'
                '<div style="font-size:12px;color:var(--ink-faint);margin-top:3px;">Sent '
                + fmt_date(ed.get("published_at")) + " · " + str(len(notices))
                + (" items" if len(notices) != 1 else " item")
                + " · " + ("Acknowledged" if acked else "Pending")
                + linked_badge + "</div></div>",
                unsafe_allow_html=True
            )
        with c2:
            st.write("")
            if st.button("View", key="arch_" + str(ed["id"]), use_container_width=True):
                nav("archive_week", edition_id=ed["id"])
        st.write("")

def show_archive_week():
    app_header()
    ed = db_get_edition(st.session_state.viewing_edition_id)
    if not ed:
        nav("archive")
        return
    if st.button("← Back to Past Bulletins"):
        nav("archive")
    render_bulletin(ed, show_ack=True)
    if st.session_state.is_admin:
        st.markdown("---")
        notices = db_get_notices(ed["id"])
        render_download_meeting_panel(ed, notices)

# ══════════════════════════════════════════════════════════════════════════════
# STAFF MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def show_staff():
    app_header()
    nav_bar("staff")
    if not st.session_state.is_admin:
        st.error("Admin access only.")
        return
    st.markdown('<div class="page-heading">Staff <span class="accent">Management</span></div>',
                unsafe_allow_html=True)
    staff = db_get_staff_list()

    with st.expander("Add New Staff Member", expanded=len(staff) == 0):
        with st.form("add_staff"):
            c1, c2 = st.columns(2)
            with c1:
                nn = st.text_input("Full Name")
                nr = st.selectbox("Role", ["staff", "admin"])
            with c2:
                ne = st.text_input("School Email")
                np = st.text_input("Initial PIN", type="password", help="Min 4 characters")
            if st.form_submit_button("Add Staff Member", type="primary"):
                if not nn.strip():
                    st.error("Name required.")
                elif not ne.strip() or "@" not in ne:
                    st.error("Valid email required.")
                elif len(np.strip()) < 4:
                    st.error("PIN must be at least 4 characters.")
                else:
                    if db_add_staff(nn.strip(), ne.strip(), np.strip(), nr):
                        st.success(nn + " added.")
                        time.sleep(0.8)
                        st.rerun()

    st.write("")
    st.markdown("### Active Staff (" + str(len(staff)) + ")")
    if not staff:
        st.info("No staff added yet.")
        return

    for s in staff:
        c1, c2, c3, c4 = st.columns([3, 3, 1, 1])
        with c1:
            role_note = " (Admin)" if s.get("role") == "admin" else ""
            st.markdown("**" + s["name"] + "**" + role_note)
        with c2:
            st.caption(s.get("email", ""))
        with c3:
            if st.button("Reset PIN", key="reset_" + str(s["id"])):
                st.session_state["resetting_" + str(s["id"])] = True
        with c4:
            if st.button("Remove", key="rm_" + str(s["id"])):
                st.session_state["confirm_remove_" + str(s["id"])] = True

        if st.session_state.get("confirm_remove_" + str(s["id"])):
            st.warning("Remove " + s["name"] + "? Their history is kept.")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("Yes, remove", key="crm_" + str(s["id"]), type="primary"):
                    db_remove_staff(s["id"])
                    st.session_state.pop("confirm_remove_" + str(s["id"]), None)
                    st.rerun()
            with rc2:
                if st.button("Cancel", key="cncrm_" + str(s["id"])):
                    st.session_state.pop("confirm_remove_" + str(s["id"]), None)
                    st.rerun()

        if st.session_state.get("resetting_" + str(s["id"])):
            with st.form("pf_" + str(s["id"])):
                np2 = st.text_input("New PIN for " + s["name"], type="password")
                pf1, pf2 = st.columns(2)
                with pf1:
                    if st.form_submit_button("Set PIN", type="primary"):
                        if len(np2.strip()) < 4:
                            st.error("Min 4 characters.")
                        else:
                            db_set_pin(s["id"], np2.strip())
                            st.success("PIN updated for " + s["name"] + ".")
                            st.session_state.pop("resetting_" + str(s["id"]), None)
                            time.sleep(0.8)
                            st.rerun()
                with pf2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.pop("resetting_" + str(s["id"]), None)
                        st.rerun()
        st.divider()

    st.markdown("---")
    st.markdown("### Change Your Own PIN")
    with st.form("own_pin"):
        op1, op2 = st.columns(2)
        with op1:
            cur_pin = st.text_input("Current PIN", type="password")
        with op2:
            new_pin = st.text_input("New PIN", type="password")
        if st.form_submit_button("Update My PIN"):
            if not db_verify_pin(st.session_state.staff_name, cur_pin):
                st.error("Current PIN is incorrect.")
            elif len(new_pin.strip()) < 4:
                st.error("New PIN must be at least 4 characters.")
            else:
                if db_set_pin(st.session_state.staff_id, new_pin.strip()):
                    st.success("PIN updated.")

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.staff_name:
    show_login()
else:
    v = st.session_state.view
    if   v == "bulletin":     show_bulletin()
    elif v == "compose":      show_compose()
    elif v == "archive":      show_archive()
    elif v == "archive_week": show_archive_week()
    elif v == "staff":        show_staff()
    else:                     show_bulletin()
