from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
import json
import os
import re
import time

# For transcript upload
try:
    import docx
    DOCX_AVAILABLE = True
except:
    DOCX_AVAILABLE = False

# ── Groq token-budget guard ────────────────────────────────────────────────
# The Groq account is on the on_demand tier. Groq enforces this per model —
# openai/gpt-oss-120b's actual cap on this account is 8,000 tokens/minute
# total, shared across prompt + requested output (earlier this was assumed
# to be 12,000, which was wrong and let requests through that Groq then
# rejected with a 413 "Request too large" error).
# A safety margin is applied on top of the 8,000 cap because the
# chars-per-token estimate below is approximate, and transcripts (speaker
# labels, timestamps, cross-talk) tend to tokenize less efficiently than
# plain prose — so a text that "fits" by this estimate can still occasionally
# run slightly over the real count without some headroom.
GROQ_TPM_LIMIT = 8000

def _fit_to_groq_budget(text: str, max_tokens: int, prompt_overhead_tokens: int = 400,
                         tpm_limit: int = GROQ_TPM_LIMIT) -> tuple[str, bool]:
    """Truncate text so prompt_overhead + text + max_tokens stays under the
    account's TPM limit, with a safety margin. Returns (possibly-truncated
    text, was_truncated)."""
    CHARS_PER_TOKEN = 4  # rough estimate for English text
    SAFETY_MARGIN = 0.85  # headroom for the estimate above being approximate
    input_token_budget = (tpm_limit - max_tokens - prompt_overhead_tokens) * SAFETY_MARGIN
    char_budget = max(0, int(input_token_budget)) * CHARS_PER_TOKEN
    if len(text) <= char_budget:
        return text, False
    return text[:char_budget], True

# ── Meeting Minutes fixed section structure ───────────────────────────────
# Manual entry and AI-from-transcript both produce/edit the SAME six
# sections, in this order, so the two entry methods are interchangeable.
MEETING_SECTIONS = [
    ("manager_business", "Manager's Business"),
    ("transition_coordinator", "Transition Coordinator"),
    ("finance", "Finance"),
    ("whs", "WHS"),
    ("pac", "PAC"),
    ("other_business", "Other Business"),
]
_NIL_TEXT = "Nil discussed this meeting."


def _parse_minutes_sections(minutes_text: str) -> dict:
    """Split a combined minutes string back into per-section text, using the
    '## Section Name' headers this tool writes. Missing/older-format minutes
    return blank sections rather than erroring."""
    result = {key: "" for key, _ in MEETING_SECTIONS}
    if not minutes_text:
        return result
    for key, label in MEETING_SECTIONS:
        pattern = rf"##\s*{re.escape(label)}\s*\n(.*?)(?=\n##\s|\Z)"
        m = re.search(pattern, minutes_text, re.DOTALL)
        if m:
            val = m.group(1).strip()
            result[key] = "" if val == _NIL_TEXT else val
    return result


def _build_minutes_from_sections(section_values: dict) -> str:
    """Combine the six section fields into one markdown document for storage,
    in a fixed order with consistent headers so it can be parsed back later."""
    parts = []
    for key, label in MEETING_SECTIONS:
        content = (section_values.get(key) or "").strip() or _NIL_TEXT
        parts.append(f"## {label}\n\n{content}")
    return "\n\n---\n\n".join(parts)


def _render_minutes_section_fields(seed: dict, key_prefix: str) -> dict:
    """Render one editable text_area per standing section, seeded from `seed`.
    Used identically by Manual Entry and by the AI-from-Transcript review step,
    so both methods land in the same fields."""
    values = {}
    for key, label in MEETING_SECTIONS:
        values[key] = st.text_area(
            label,
            value=seed.get(key, ""),
            height=140,
            key=f"{key_prefix}_{key}",
            placeholder=f"What was discussed under {label}? Include any decisions "
                        f"and actions (who's responsible, due date)."
        )
    return values


# ── CLC-LBU document theme ──────────────────────────────────────────────────
# Same teal + Segoe UI look already used for the on-screen minutes preview
# (see the .clc-minutes CSS below) and the "Back to Staff Portal" sidebar
# button, so the downloaded Word doc matches the rest of the tool.
_CLC_TEAL = "1A7A7A"
_CLC_TEAL_LIGHT = "EAF5F5"
_CLC_GRAY = "6B7280"
_CLC_TEXT = "1A1A1A"
_CLC_BORDER = "D9DEE2"


def _docx_shade_cell(cell, hex_fill):
    """Set a table cell's background fill colour."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_fill)
    tcPr.append(shd)


def _docx_cell_borders(cell, color=_CLC_BORDER, sz=4):
    """Give a table cell a thin single-colour border on all four sides."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(sz))
        el.set(qn('w:color'), color)
        borders.append(el)
    tcPr.append(borders)


def _docx_bottom_rule(paragraph, color=_CLC_TEAL, sz=16):
    """Add a coloured rule under a paragraph — used as a heading underline
    instead of a horizontal-rule table."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(sz))
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _docx_set_cell_text(cell, text, bold=False, color=_CLC_TEXT, size=10.5, align=None):
    from docx.shared import Pt, RGBColor
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.font.name = "Segoe UI"


def _docx_section_heading(doc, text, size=13):
    """A coloured, underlined heading used for each minutes/actions section —
    built manually (rather than doc.add_heading) so the colour always matches
    the CLC teal regardless of the template's built-in heading colours."""
    from docx.shared import Pt, RGBColor
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(_CLC_TEAL)
    run.font.name = "Segoe UI"
    _docx_bottom_rule(p, color=_CLC_BORDER, sz=6)
    return p


def _build_minutes_docx_bytes(meeting: dict):
    """Build a professionally styled Word document from a meeting record (or
    the in-progress form data) for download. Uses the same CLC-LBU teal +
    Segoe UI theme as the rest of the tool. Returns None if python-docx isn't
    available."""
    if not DOCX_AVAILABLE:
        return None
    from io import BytesIO
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    doc = docx.Document()

    # ── Base typography ──────────────────────────────────────────────────
    normal = doc.styles['Normal']
    normal.font.name = "Segoe UI"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(_CLC_TEXT)

    section = doc.sections[0]
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.8)

    # ── Letterhead ───────────────────────────────────────────────────────
    eyebrow = doc.add_paragraph()
    eyebrow.alignment = WD_ALIGN_PARAGRAPH.CENTER
    er = eyebrow.add_run("COWANDILLA LEARNING CENTRE  ·  LEARNING & BEHAVIOUR UNIT")
    er.bold = True
    er.font.size = Pt(9)
    er.font.color.rgb = RGBColor.from_string(_CLC_GRAY)
    er.font.name = "Segoe UI"

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(2)
    title.paragraph_format.space_after = Pt(12)
    tr = title.add_run("Staff Meeting Minutes")
    tr.bold = True
    tr.font.size = Pt(24)
    tr.font.color.rgb = RGBColor.from_string(_CLC_TEAL)
    tr.font.name = "Segoe UI"
    _docx_bottom_rule(title, color=_CLC_TEAL, sz=18)

    # ── Meeting details card ─────────────────────────────────────────────
    details = [
        ("Date", meeting.get('meeting_date', '') or '—'),
        ("Term / Week", f"{meeting.get('term', '')} · Week {meeting.get('week_number', '')}"),
        ("Minute Taker", meeting.get('minute_taker', '') or '—'),
        ("Attendees", meeting.get('attendees', '') or 'Not recorded'),
        ("Apologies", meeting.get('apologies', '') or 'None'),
    ]
    if meeting.get('acknowledgement_done'):
        details.append((
            "Acknowledgement of Country",
            f"Completed — led by {meeting.get('acknowledgement_by', '') or 'not recorded'}"
        ))

    table = doc.add_table(rows=len(details), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, (label, value) in enumerate(details):
        cells = table.rows[i].cells
        cells[0].width = Inches(1.9)
        cells[1].width = Inches(4.7)
        _docx_shade_cell(cells[0], _CLC_TEAL_LIGHT)
        _docx_set_cell_text(cells[0], label, bold=True, color=_CLC_TEAL, size=9.5)
        _docx_set_cell_text(cells[1], str(value), size=10)
        _docx_cell_borders(cells[0])
        _docx_cell_borders(cells[1])

    doc.add_paragraph()

    # ── Minutes sections ─────────────────────────────────────────────────
    minutes_text = meeting.get('minutes', '') or ''
    for block in minutes_text.split('\n\n---\n\n'):
        block = block.strip()
        if not block:
            continue
        if block.startswith('## '):
            lines = block.split('\n', 1)
            heading = lines[0][3:].strip()
            body = lines[1].strip() if len(lines) > 1 else ''
            _docx_section_heading(doc, heading)
            for para in body.split('\n'):
                para = para.strip()
                if not para:
                    continue
                bp = doc.add_paragraph()
                bp.paragraph_format.space_after = Pt(4)
                if para.startswith(('- ', '• ')):
                    bp.style = doc.styles['List Bullet']
                    bp.add_run(para[2:].strip())
                else:
                    bp.add_run(para)
        else:
            doc.add_paragraph(block)

    # ── Actions ───────────────────────────────────────────────────────────
    raw_actions = meeting.get('actions')
    try:
        actions_list = json.loads(raw_actions) if isinstance(raw_actions, str) else (raw_actions or [])
    except Exception:
        actions_list = []
    if actions_list:
        _docx_section_heading(doc, "Actions")
        atable = doc.add_table(rows=1, cols=3)
        atable.autofit = True
        hdr = atable.rows[0].cells
        for c, label in zip(hdr, ("Action", "Owner", "Due Date")):
            _docx_shade_cell(c, _CLC_TEAL)
            _docx_set_cell_text(c, label, bold=True, color="FFFFFF", size=10)
            _docx_cell_borders(c, color=_CLC_TEAL)
        for a in actions_list:
            row = atable.add_row().cells
            _docx_set_cell_text(row[0], a.get('action', ''), size=10)
            _docx_set_cell_text(row[1], a.get('owner', ''), size=10)
            _docx_set_cell_text(row[2], a.get('due_date', ''), size=10)
            for c in row:
                _docx_cell_borders(c)

    # ── Footer ────────────────────────────────────────────────────────────
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer_p.add_run("Cowandilla Learning Centre  ·  Learning and Behaviour Unit  ·  Staff Meeting Minutes")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor.from_string(_CLC_GRAY)
    fr.font.name = "Segoe UI"

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="STAFF Meetings | CLC-LBU", page_icon="👥", layout="wide")
apply_clc_theme()

from staff_auth import require_staff_auth, staff_logout_button
require_staff_auth("STAFF Meetings", "👥")
staff_logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Supabase Connections ──────────────────────────────────────────────────────
# STAFF Meetings uses TWO databases:
# 1. MEETINGS database (cmqyrfekxgjdtuloseri) - for meeting records and agenda items
# 2. OPERATIONAL database (lvzaebjrxrgguypqvdcq) - for bulletin (clc_events)

# Primary connection: MEETINGS database (meeting records, agenda items)
SUPABASE_URL_MEETINGS = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
SUPABASE_KEY_MEETINGS = st.secrets.get("SUPABASE_KEY_MEETINGS", st.secrets["SUPABASE_KEY"])
SUPABASE_SERVICE_KEY_MEETINGS = st.secrets.get("SUPABASE_SERVICE_KEY_MEETINGS", SUPABASE_KEY_MEETINGS)

supabase = create_client(SUPABASE_URL_MEETINGS, SUPABASE_SERVICE_KEY_MEETINGS)

# Secondary connection: OPERATIONAL database (for bulletin)
SUPABASE_URL_OPERATIONAL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY_OPERATIONAL = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY_OPERATIONAL = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY_OPERATIONAL)

supabase_ops = create_client(SUPABASE_URL_OPERATIONAL, SUPABASE_SERVICE_KEY_OPERATIONAL)

GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

# ── Supabase Storage attachment helpers ────────────────────────────────────────
# Attachments previously only saved file *metadata* (name/size/type) — nothing
# was ever uploaded anywhere, so "Add All Files" looked like it worked but
# there was never a file to open afterwards. These helpers actually upload the
# bytes to Supabase Storage (in the MEETINGS project, alongside the meeting
# records) and hand back a storage path to save with the metadata, plus a
# signed URL for opening/downloading.
MEETING_ATTACHMENTS_BUCKET = "meeting-attachments"
PD_ATTACHMENTS_BUCKET = "pd-attachments"


def _ensure_bucket(bucket_name: str):
    """Create the storage bucket if it doesn't exist yet. Safe to call any
    time — quietly no-ops if it's already there (or gets created between the
    check and the call)."""
    try:
        supabase.storage.create_bucket(bucket_name, options={"public": False})
    except Exception:
        pass


def _upload_attachment(bucket_name: str, folder: str, file) -> dict:
    """Upload one Streamlit UploadedFile to Supabase Storage.
    Returns {"path": ...} on success or {"error": ...} on failure."""
    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', file.name)
    path = f"{folder}/{int(time.time() * 1000)}_{safe_name}"
    file_bytes = file.getvalue()
    content_type = file.type or "application/octet-stream"
    try:
        supabase.storage.from_(bucket_name).upload(
            path, file_bytes, {"content-type": content_type}
        )
        return {"path": path}
    except Exception as e1:
        # Most likely cause of a first-ever upload failing: the bucket
        # doesn't exist yet. Create it and retry once before giving up.
        try:
            _ensure_bucket(bucket_name)
            supabase.storage.from_(bucket_name).upload(
                path, file_bytes, {"content-type": content_type}
            )
            return {"path": path}
        except Exception as e2:
            return {"error": f"{type(e2).__name__}: {e2}  (first attempt: {type(e1).__name__}: {e1})"}


def _extract_signed_url_value(result):
    """Pull the signed URL out of whatever shape create_signed_url() returned
    — different supabase-py/storage3 versions hand back a plain dict, a
    pydantic model, or different key casing."""
    if result is None:
        return None
    if isinstance(result, dict):
        return result.get('signedURL') or result.get('signedUrl') or result.get('signed_url')
    return (
        getattr(result, 'signedURL', None)
        or getattr(result, 'signedUrl', None)
        or getattr(result, 'signed_url', None)
    )


def _attachment_signed_url(bucket_name: str, path: str, expires_in: int = 3600):
    """Return (url, error). url is a temporary signed download URL, or None
    on failure; error is the raw exception/diagnostic text when it fails, so
    a failure can be shown to the user instead of disappearing silently."""
    if not path:
        return None, "No file path stored for this attachment."
    try:
        result = supabase.storage.from_(bucket_name).create_signed_url(path, expires_in)
        url = _extract_signed_url_value(result)
        if not url:
            return None, f"Supabase returned no signed URL ({result!r})."
        if not (url.startswith('http://') or url.startswith('https://')):
            # Some supabase-py versions return a URL relative to the storage
            # API host instead of a full URL — normalise it defensively so a
            # relative path doesn't silently produce a dead link.
            base = SUPABASE_URL_MEETINGS.rstrip('/')
            rel = url if url.startswith('/') else '/' + url
            if not rel.startswith('/storage/v1'):
                rel = '/storage/v1' + rel
            url = base + rel
        return url, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _delete_attachment(bucket_name: str, path: str):
    """Best-effort delete of the stored file when an attachment is removed
    from a meeting. Never raises — a storage hiccup shouldn't block removing
    the metadata row."""
    if not path:
        return
    try:
        supabase.storage.from_(bucket_name).remove([path])
    except Exception:
        pass


def _render_attachment_link(att: dict, bucket_name: str):
    """Render one attachment's name/description plus an Open link when the
    file was actually uploaded to storage. Attachments saved before this fix
    only ever had metadata (no 'path'), so those are flagged as needing a
    re-upload rather than shown as a dead link."""
    name = att.get('name') or att.get('filename') or 'Unnamed file'
    desc = att.get('description') or ''
    label = f"📎 **{name}**" + (f" — {desc}" if desc else "")
    path = att.get('path')
    if path:
        url, err = _attachment_signed_url(bucket_name, path)
        if url:
            st.markdown(f"{label}  \n[🔗 Open / Download]({url})")
        else:
            st.markdown(f"{label}  \n:orange[Couldn't generate a link for this file.]")
            st.caption(f"⚠️ {err}")
    else:
        st.markdown(f"{label}  \n:gray[Added before file upload was enabled — no file stored. Delete and re-upload to attach it.]")

# ── Term normalisation ─────────────────────────────────────────────────────────
# Staff Meetings stores term as "T2"; Staff Bulletin stores it as "Term 2".
# These helpers keep the two tools in sync.

def normalise_term_long(raw: str) -> str:
    """Convert ANY term format to 'Term N' (used by Staff Bulletin).
    Handles: 'T2', '2', 'term2', 'Term 2', 'TERM2', etc."""
    import re
    raw = str(raw).strip()
    m = re.search(r'(\d)', raw)
    if m:
        return f"Term {m.group(1)}"
    return raw

def normalise_term_short(raw: str) -> str:
    """Convert ANY term format to 'TN' (used by Staff Meetings)."""
    import re
    raw = str(raw).strip()
    m = re.search(r'(\d)', raw)
    if m:
        return f"T{m.group(1)}"
    return raw

# ── BSEM Icebreakers (5-minute activities) ────────────────────────────────────
BSEM_ICEBREAKERS = [
    {
        "week": 1,
        "name": "Two Truths and a Lie",
        "instructions": "Each person shares three statements about themselves - two true, one false. Group guesses which is the lie.",
        "time": "5 mins"
    },
    {
        "week": 2,
        "name": "Gratitude Round",
        "instructions": "Each person shares one thing they're grateful for this week (personal or professional).",
        "time": "5 mins"
    },
    {
        "week": 3,
        "name": "Brain Break: Draw Your Weekend",
        "instructions": "60 seconds to draw something from your weekend. Share with the group.",
        "time": "5 mins"
    },
    {
        "week": 4,
        "name": "Quick Check-In: Rate Your Week",
        "instructions": "Rate your week 1-10 and share one word to describe it.",
        "time": "5 mins"
    },
    {
        "week": 5,
        "name": "Wins & Learnings",
        "instructions": "Share one win and one thing you learned this week.",
        "time": "5 mins"
    },
    {
        "week": 6,
        "name": "Would You Rather?",
        "instructions": "Facilitator poses a 'Would you rather...' question. Quick votes and brief sharing.",
        "time": "5 mins"
    },
    {
        "week": 7,
        "name": "Rose, Thorn, Bud",
        "instructions": "Share: Rose (highlight), Thorn (challenge), Bud (something you're looking forward to).",
        "time": "5 mins"
    },
    {
        "week": 8,
        "name": "Quick Movement Break",
        "instructions": "Stand up stretch or brief movement activity. Can be led by different staff member each week.",
        "time": "5 mins"
    },
    {
        "week": 9,
        "name": "Shout-Outs",
        "instructions": "Acknowledge someone who helped you this week or did something great.",
        "time": "5 mins"
    },
    {
        "week": 10,
        "name": "What's In Your Cup?",
        "instructions": "Share what's filling your emotional cup or draining it this week.",
        "time": "5 mins"
    },
    {
        "week": 11,
        "name": "Reflection Round",
        "instructions": "One word to describe this term. Quick round-robin.",
        "time": "5 mins"
    }
]

# Standing agenda items
STANDING_AGENDA_ITEMS = [
    "Transition Coordinator Info",
    "Manager Info",
    "PAC (Personnel Advisory Committee)",
    "WHS (Work Health & Safety)",
    "Social Club",
    "Finance"
]

# ── Session state ──────────────────────────────────────────────────────────────
if 'current_staff_meeting_id' not in st.session_state:
    st.session_state.current_staff_meeting_id = None

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.title("👥 STAFF MEETINGS")
st.caption("Weekly All-Staff Meetings · DfE Format")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING SELECTOR
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📅 Select Meeting")

# Fetch existing meetings
try:
    result = supabase.table('staff_meetings').select('*').order('meeting_date', desc=True).limit(20).execute()
    existing_meetings = result.data if result.data else []
except Exception as e:
    st.warning(f"Could not load meetings: {e}")
    existing_meetings = []

meeting_options = ["➕ New Meeting"] + [
    f"{m['meeting_date']} - T{m.get('term', '?')} W{m.get('week_number', '?')} - {m.get('minute_taker', 'Unknown')}"
    for m in existing_meetings
]

selected_option = st.selectbox("Choose a meeting", options=meeting_options, key="staff_meeting_selector")

if selected_option == "➕ New Meeting":
    selected_record = None
    st.session_state.current_staff_meeting_id = None
else:
    idx = meeting_options.index(selected_option) - 1
    selected_record = existing_meetings[idx]
    st.session_state.current_staff_meeting_id = selected_record['id']
    
    # Delete meeting option (only for existing meetings)
    with st.expander("🗑️ Delete This Meeting", expanded=False):
        st.warning("⚠️ **Warning:** This will permanently delete this meeting record!")
        
        delete_confirmation = st.text_input(
            "Type 'DELETE' to confirm deletion",
            key="delete_confirm",
            placeholder="Type DELETE here"
        )
        
        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            if st.button("🗑️ Delete Meeting", type="secondary", disabled=(delete_confirmation != "DELETE")):
                try:
                    supabase.table('staff_meetings').delete().eq('id', st.session_state.current_staff_meeting_id).execute()
                    st.success("✅ Meeting deleted successfully!")
                    st.session_state.current_staff_meeting_id = None
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Could not delete meeting: {e}")
        
        with col_del2:
            if delete_confirmation != "DELETE":
                st.caption("Type DELETE above to enable deletion")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS: CURRENT MEETING / ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2 = st.tabs(["📝 Current Meeting", "📚 Meeting Archive"])

with tab2:
    st.subheader("📚 Past STAFF Meetings")
    
    if existing_meetings:
        for meeting in existing_meetings:
            with st.expander(f"📅 {meeting['meeting_date']} - T{meeting.get('term', '?')} W{meeting.get('week_number', '?')} - {meeting.get('minute_taker', 'Unknown')}"):
                st.write(f"**Attendees:** {meeting.get('attendees', 'Not recorded')}")
                st.write(f"**Apologies:** {meeting.get('apologies', 'None')}")
                
                st.markdown("---")
                st.write("**📄 Minutes:**")
                meeting_minutes = meeting.get('minutes', 'No minutes recorded')
                if meeting_minutes and meeting_minutes != 'No minutes recorded':
                    st.markdown('''<style>
.clc-minutes { font-family: "Segoe UI", Arial, sans-serif !important; font-size: 14px !important; line-height: 1.7 !important; color: #1a1a1a !important; }
.clc-minutes p, .clc-minutes li, .clc-minutes td, .clc-minutes th, .clc-minutes strong, .clc-minutes em { font-family: "Segoe UI", Arial, sans-serif !important; font-size: 14px !important; }
.clc-minutes h1,.clc-minutes h2,.clc-minutes h3,.clc-minutes h4 { font-family: "Segoe UI", Arial, sans-serif !important; font-size: 15px !important; font-weight: 700 !important; margin-top: 1em; }
.clc-minutes table { border-collapse: collapse; width: 100%; }
.clc-minutes th { background: #f0f0f0; padding: 6px 10px; border: 1px solid #ddd; }
.clc-minutes td { padding: 6px 10px; border: 1px solid #ddd; }
</style>''', unsafe_allow_html=True)
                    st.markdown(f'<div class="clc-minutes">' + meeting_minutes + '</div>', unsafe_allow_html=True)
                else:
                    st.info("No minutes recorded for this meeting")
                
                if meeting.get('actions'):
                    st.markdown("---")
                    st.write("**Actions:**")
                    try:
                        actions = json.loads(meeting['actions']) if isinstance(meeting['actions'], str) else meeting['actions']
                        for action in actions:
                            st.write(f"- {action.get('action', '')} - **{action.get('owner', '')}** - Due: {action.get('due_date', '')}")
                    except:
                        pass
                
                # Show meeting attachments if present
                if meeting.get('meeting_attachments'):
                    st.markdown("---")
                    st.write("**📎 Meeting Attachments:**")
                    try:
                        attachments = json.loads(meeting['meeting_attachments']) if isinstance(meeting['meeting_attachments'], str) else meeting['meeting_attachments']
                        if attachments:
                            for att in attachments:
                                _render_attachment_link(att, MEETING_ATTACHMENTS_BUCKET)
                    except:
                        pass
                
                # Show PD information if present
                if meeting.get('pd_notes') or meeting.get('pd_attendees') or meeting.get('pd_title'):
                    st.markdown("---")
                    st.write("**🎓 Professional Development:**")
                    if meeting.get('pd_title'):
                        st.write(f"**Session Title:** {meeting['pd_title']}")
                    if meeting.get('pd_attendees'):
                        st.write(f"**PD Attendees:** {meeting['pd_attendees']}")
                    if meeting.get('pd_absent'):
                        st.write(f"**PD Absent:** {meeting['pd_absent']}")
                    if meeting.get('pd_notes'):
                        st.write("**PD Notes:**")
                        st.markdown(meeting['pd_notes'])
                    if meeting.get('pd_attachments'):
                        try:
                            attachments = json.loads(meeting['pd_attachments']) if isinstance(meeting['pd_attachments'], str) else meeting['pd_attachments']
                            if attachments:
                                st.write("**PD Attachments:**")
                                for att in attachments:
                                    _render_attachment_link(att, PD_ATTACHMENTS_BUCKET)
                        except:
                            pass

                # ── Download + delete this archived meeting ────────────────────
                st.markdown("---")
                col_arc_dl, col_arc_del = st.columns([1, 1])
                with col_arc_dl:
                    if DOCX_AVAILABLE and (meeting.get('minutes') or '').strip():
                        st.download_button(
                            "📥 Download Minutes (.docx)",
                            data=_build_minutes_docx_bytes(meeting),
                            file_name=f"Staff_Meeting_Minutes_{meeting.get('meeting_date', '')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key=f"download_archived_{meeting['id']}"
                        )
                    else:
                        st.button("📥 Download Minutes (.docx)", disabled=True,
                                  use_container_width=True, key=f"download_archived_disabled_{meeting['id']}")

                with col_arc_del:
                    confirm_key = f"confirm_delete_archived_{meeting['id']}"
                    if st.session_state.get(confirm_key):
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("⚠️ Confirm delete", key=f"confirm_del_{meeting['id']}",
                                        type="secondary", use_container_width=True):
                                try:
                                    supabase.table('staff_meetings').delete().eq('id', meeting['id']).execute()
                                    st.success("✅ Deleted.")
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"⚠️ Could not delete: {e}")
                        with col_no:
                            if st.button("Cancel", key=f"cancel_del_{meeting['id']}", use_container_width=True):
                                st.session_state[confirm_key] = False
                                st.rerun()
                    else:
                        if st.button("🗑️ Delete this meeting", key=f"del_{meeting['id']}", use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.rerun()
    else:
        st.info("No archived meetings yet.")

with tab1:
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # MEETING FORM
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📋 Meeting Details")
    
    col1, col2, col3 = st.columns(3)
    
    # Defaults
    if selected_record:
        default_date = datetime.date.fromisoformat(selected_record['meeting_date'])
        default_term = selected_record.get('term', 'T2')
        default_week = selected_record.get('week_number', 1)
    else:
        default_date = datetime.date.today()
        default_term = 'T2'
        default_week = 1

    _term_opts = ["T1", "T2", "T3", "T4"]
    _term_idx  = _term_opts.index(normalise_term_short(default_term)) if normalise_term_short(default_term) in _term_opts else 1

    with col1:
        meeting_date = st.date_input("Meeting Date", value=default_date, key="staff_date")

    with col2:
        term = st.selectbox("Term", options=_term_opts, index=_term_idx, key="staff_term")
    
    with col3:
        week_number = st.number_input("Week Number", min_value=1, max_value=11, value=default_week, key="staff_week")
    
    default_minute_taker = selected_record.get('minute_taker', '') if selected_record else ''
    minute_taker = st.text_input("Minute Taker", value=default_minute_taker, key="minute_taker")
    
    st.markdown("---")
    # ══════════════════════════════════════════════════════════════════════════════
    # 1. STAFF BULLETIN FOR THE WEEK
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📋 Staff Bulletin (This Week)")
    
    # Auto-load bulletin from Staff Bulletin tool based on term and week
    try:
        # Normalise term to "Term N" format (Staff Bulletin always stores it that way)
        term_long = normalise_term_long(term)
        # Find bulletin edition linked to this meeting's term/week
        bulletin_result = supabase_ops.table('weekly_editions').select('*').eq('meeting_linked', True).eq('meeting_term', term_long).eq('meeting_week', int(week_number)).execute()

        # ── Bulletin link status ──────────────────────────────────────────────
        with st.expander("🗓️ Bulletin link status", expanded=False):
            st.write(f"**Querying:** meeting_linked=True, meeting_term=`{term_long}`, meeting_week=`{int(week_number)}`")
            all_linked = supabase_ops.table('weekly_editions').select('id,week_label,week_start,meeting_linked,meeting_term,meeting_week').eq('meeting_linked', True).execute()
            st.write("**All linked editions in Supabase:**")
            if all_linked.data:
                import re as _re
                from datetime import date as _date, timedelta as _td
                _TERM_STARTS = {"Term 1": _date(2026,1,27), "Term 2": _date(2026,4,27),
                                "Term 3": _date(2026,7,20), "Term 4": _date(2026,10,12)}
                for row in all_linked.data:
                    st.write(f"- `{row.get('week_label')}` → term=`{repr(row.get('meeting_term'))}` week=`{repr(row.get('meeting_week'))}`")
                    # Offer repair if week looks wrong
                    ws = row.get('week_start')
                    stored_term = row.get('meeting_term', '')
                    if ws and stored_term in _TERM_STARTS:
                        d = _date.fromisoformat(str(ws))
                        correct_week = (d - _TERM_STARTS[stored_term]).days // 7 + 1
                        correct_week = max(1, correct_week)
                        if correct_week != row.get('meeting_week'):
                            st.warning(f"  ⚠️ Week should be **{correct_week}** (stored as {row.get('meeting_week')})")
                            if st.button(f"🔧 Fix to Week {correct_week}", key=f"repair_{row['id']}"):
                                supabase_ops.table('weekly_editions').update(
                                    {"meeting_week": correct_week}
                                ).eq('id', row['id']).execute()
                                st.success(f"Fixed! Now week {correct_week}")
                                st.rerun()
            else:
                st.write("None found — nothing is linked at all in Supabase")
            st.write(f"**Query result:** {bulletin_result.data}")
        # ─────────────────────────────────────────────────────────────────────
        
        if bulletin_result.data and len(bulletin_result.data) > 0:
            edition = bulletin_result.data[0]
            
            # Get all notices for this edition
            notices_result = supabase_ops.table('notices').select('*').eq('edition_id', edition['id']).order('created_at').execute()

            is_draft = edition.get('status', 'draft') == 'draft'

            # Status badge
            if is_draft:
                st.markdown(
                    '<div style="background:#fef9c3;border:1px solid #fde047;border-radius:6px;'
                    'padding:8px 14px;font-size:13px;color:#854d0e;margin-bottom:10px;">'
                    '🟡 <strong>Bulletin is in draft</strong> — items are live here as they are added. '
                    'Staff will see the full bulletin once you click Send.</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div style="background:#dcfce7;border:1px solid #86efac;border-radius:6px;'
                    'padding:8px 14px;font-size:13px;color:#14532d;margin-bottom:10px;">'
                    '✅ <strong>Bulletin sent</strong> — all items confirmed.</div>',
                    unsafe_allow_html=True
                )

            if notices_result.data:
                for notice in notices_result.data:
                    category = notice.get('category', 'general')
                    author   = notice.get('author', 'Staff')
                    with st.expander(f"📌 {notice['title']} ({category.upper()})"):
                        st.write(f"**From:** {author}")
                        st.write(f"**Category:** {category.title()}")
                        st.markdown("---")
                        st.write(notice.get('content', ''))
            else:
                st.info("No bulletin items added yet — they will appear here as they are added in the Bulletin tool.")

            # Allow admin to remove the bulletin link
            st.write("")
            edition_id_str = str(edition['id'])
            if not st.session_state.get(f"mtg_unlink_confirm_{edition_id_str}"):
                if st.button("🗑️ Remove bulletin from this meeting", key=f"mtg_unlink_{edition_id_str}",
                             help="Detaches this bulletin so it can be re-linked or replaced"):
                    st.session_state[f"mtg_unlink_confirm_{edition_id_str}"] = True
                    st.rerun()
            else:
                st.warning(f"Remove the **{edition.get('week_label', '')}** bulletin from this meeting? "
                           "It can be re-linked from the Staff Bulletin tool at any time.")
                cu1, cu2 = st.columns(2)
                with cu1:
                    if st.button("Yes, remove it", key=f"mtg_unlink_yes_{edition_id_str}", type="primary"):
                        try:
                            supabase_ops.table('weekly_editions').update({
                                "meeting_linked": False,
                                "meeting_term":   None,
                                "meeting_week":   None,
                            }).eq('id', edition['id']).execute()
                            st.session_state.pop(f"mtg_unlink_confirm_{edition_id_str}", None)
                            st.success("Bulletin removed from this meeting.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as ue:
                            st.error(f"Could not remove: {ue}")
                with cu2:
                    if st.button("Cancel", key=f"mtg_unlink_cancel_{edition_id_str}"):
                        st.session_state.pop(f"mtg_unlink_confirm_{edition_id_str}", None)
                        st.rerun()
        else:
            st.info(f"ℹ️ No bulletin linked for {term_long} Week {int(week_number)} yet")
            st.caption("The bulletin will appear here automatically once the Staff Bulletin tool opens this week's edition.")
    
    except Exception as e:
        st.warning(f"Could not load bulletin: {e}")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 2. ATTENDANCE
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("👥 Attendance")
    
    default_attendees = selected_record.get('attendees', '') if selected_record else ''
    attendees = st.text_area("Attendees Present", value=default_attendees, height=80, key="attendees", 
                             placeholder="List staff members present...")
    
    default_apologies = selected_record.get('apologies', '') if selected_record else ''
    apologies = st.text_area("Apologies", value=default_apologies, height=60, key="apologies",
                             placeholder="List staff members with apologies...")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 3. ACKNOWLEDGEMENT OF COUNTRY
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("🪃 Acknowledgement of Country")
    
    # Video playback - Read from environment variable
    VIDEO_URL = os.environ.get("ACKNOWLEDGEMENT_VIDEO_URL", "") or st.secrets.get("ACKNOWLEDGEMENT_VIDEO_URL", "")
    
    if VIDEO_URL:
        with st.expander("📹 Watch Acknowledgement of Country Video", expanded=False):
            st.video(VIDEO_URL)
            st.caption("Play this video at the start of the meeting")
    else:
        st.info("📹 **Video not configured yet** - Add ACKNOWLEDGEMENT_VIDEO_URL to Render environment variables to enable video playback")
    
    # Text version option
    with st.expander("📄 Or Read Acknowledgement of Country (Text Version)", expanded=False):
        st.markdown("""
        *"Before we begin, I acknowledge the Kaurna people as the Traditional Custodians of this land, and pay my respects to their Elders past, present, and emerging.*
        
        *As a Learning and Behaviour Unit, we recognise that many of our students carry trauma — and we acknowledge the particular trauma that colonisation has caused and continues to cause for Aboriginal and Torres Strait Islander peoples.*
        
        *We are committed to trauma-informed, culturally responsive practice that honours the strengths, resilience, and cultures of all our students and their families.*
        
        *I extend my respect to any Aboriginal and Torres Strait Islander people present today."*
        """)
        st.caption("Chair can read this aloud at the start of the meeting")
    
    acknowledgement_done = st.checkbox("✅ Acknowledgement completed", value=selected_record.get('acknowledgement_done', False) if selected_record else False)
    acknowledgement_by = st.text_input("Led by", value=selected_record.get('acknowledgement_by', '') if selected_record else '', placeholder="Who led the Acknowledgement?")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 4. ICEBREAKER / BSEM ACTIVITY (5 mins)
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("🎯 Icebreaker / BSEM Activity (5 mins)")
    
    # Get icebreaker for this week
    week_idx = (int(week_number) - 1) % len(BSEM_ICEBREAKERS)
    icebreaker = BSEM_ICEBREAKERS[week_idx]
    
    with st.expander(f"💡 Suggested Activity: **{icebreaker['name']}**", expanded=True):
        st.write(f"**Time:** {icebreaker['time']}")
        st.write(f"**Instructions:** {icebreaker['instructions']}")
    
    icebreaker_notes = st.text_area("Icebreaker Notes (optional)", 
                                    value=selected_record.get('icebreaker', '') if selected_record else '',
                                    height=80, 
                                    placeholder="Any notes about how the icebreaker went...",
                                    key="icebreaker")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 5. AGENDA ITEMS
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📑 Meeting Agenda")
    
    # Standing agenda items
    st.write("**Standing Items:**")
    
    # Load agenda data
    if selected_record and selected_record.get('agenda_items'):
        try:
            agenda_data = json.loads(selected_record['agenda_items']) if isinstance(selected_record['agenda_items'], str) else selected_record['agenda_items']
        except:
            agenda_data = {}
    else:
        agenda_data = {}

    # Pre-populate the additional items text area from saved data
    # (only if session state hasn't been set yet for this meeting)
    _saved_additional = agenda_data.get('additional_agenda', [])
    _ss_key = f"agenda_loaded_{st.session_state.current_staff_meeting_id}"
    if _saved_additional and not st.session_state.get(_ss_key):
        st.session_state['simple_agenda_items'] = "\n".join(_saved_additional)
        st.session_state[_ss_key] = True
    
    for item in STANDING_AGENDA_ITEMS:
        with st.expander(f"📌 {item}"):
            agenda_data[item] = st.text_area(
                f"Notes for {item}", 
                value=agenda_data.get(item, ''),
                height=100,
                key=f"agenda_{item.replace(' ', '_')}",
                placeholder=f"Add information/updates for {item}..."
            )
    
    # ── ADDITIONAL AGENDA ITEMS ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📋 Additional Agenda Items")

    # Initialise in agenda_data
    if 'additional_agenda' not in agenda_data:
        agenda_data['additional_agenda'] = []

    # Use session state as the live list so changes survive widget rerenders
    ss_key = f"addl_items_{st.session_state.current_staff_meeting_id or 'new'}"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = list(agenda_data.get('additional_agenda', []))

    additional_items = st.session_state[ss_key]

    # ── Load Staff Submissions button ─────────────────────────────────────────
    col_load1, col_load2 = st.columns([2, 3])
    with col_load1:
        if st.button("📥 Load Staff Submissions", key="load_pending_items", type="secondary",
                     use_container_width=True):
            try:
                pending_result = supabase_ops.table('staff_agenda_items') \
                                             .select('*').eq('status', 'pending').execute()
                if pending_result.data:
                    loaded_count = 0
                    for item in pending_result.data:
                        label = f"📌 {item['item_text']}  — submitted by {item['submitted_by']}"
                        if label not in additional_items:
                            additional_items.append(label)
                            loaded_count += 1
                        supabase_ops.table('staff_agenda_items') \
                                    .update({'status': 'added'}).eq('id', item['id']).execute()

                    st.session_state[ss_key] = additional_items

                    if st.session_state.current_staff_meeting_id:
                        agenda_data['additional_agenda'] = additional_items
                        supabase.table('staff_meetings').update({
                            "agenda_items": json.dumps(agenda_data)
                        }).eq('id', st.session_state.current_staff_meeting_id).execute()

                    if loaded_count:
                        st.success(f"✅ {loaded_count} item(s) loaded!")
                    else:
                        st.info("No new pending submissions.")
                    st.rerun()
                else:
                    st.info("No pending agenda items found.")
            except Exception as e:
                st.error(f"Error: {e}")
    with col_load2:
        st.caption("Pulls items submitted by staff via the Submit Agenda Item tool")

    st.write("")

    # ── Display current items as cards ────────────────────────────────────────
    if additional_items:
        st.markdown(
            f'<div style="font-size:13px;color:#6b7280;margin-bottom:8px;">'
            f'{len(additional_items)} item(s) on agenda</div>',
            unsafe_allow_html=True
        )
        items_to_remove = []
        for i, item_text in enumerate(additional_items):
            col_item, col_del = st.columns([11, 1])
            with col_item:
                st.markdown(
                    f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
                    f'padding:10px 14px;font-family:Segoe UI,Arial,sans-serif;font-size:14px;'
                    f'color:#14532d;margin-bottom:4px;">{item_text}</div>',
                    unsafe_allow_html=True
                )
            with col_del:
                if st.button("✕", key=f"remove_item_{i}", help="Remove this item"):
                    items_to_remove.append(i)

        if items_to_remove:
            for idx in sorted(items_to_remove, reverse=True):
                additional_items.pop(idx)
            st.session_state[ss_key] = additional_items
            st.rerun()
    else:
        st.markdown(
            '<div style="background:#f9fafb;border:1px dashed #d1d5db;border-radius:8px;'
            'padding:16px;text-align:center;color:#9ca3af;font-size:13px;">'
            'No additional items yet — load staff submissions or add one below</div>',
            unsafe_allow_html=True
        )

    # ── Manual add ────────────────────────────────────────────────────────────
    st.write("")
    col_new, col_add = st.columns([4, 1])
    with col_new:
        new_item = st.text_input("Add an agenda item", key="new_agenda_item",
                                 placeholder="Type item and click Add →",
                                 label_visibility="collapsed")
    with col_add:
        if st.button("➕ Add", key="add_agenda_item", use_container_width=True):
            if new_item.strip():
                additional_items.append(new_item.strip())
                st.session_state[ss_key] = additional_items
                st.session_state['new_agenda_item'] = ""
                st.rerun()

    # Keep agenda_data in sync with session state list
    additional_items = st.session_state[ss_key]
    agenda_data['additional_agenda'] = additional_items

    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 6. MINUTES (Manual OR AI Transcript) — both land in the same six sections:
    # Manager's Business, Transition Coordinator, Finance, WHS, PAC, Other Business
    # ══════════════════════════════════════════════════════════════════════════════
    
    minutes = selected_record.get('minutes', '') if selected_record else ''
    has_existing_minutes = bool(minutes and minutes.strip())
    
    with st.expander("📄 Meeting Minutes", expanded=not has_existing_minutes):
        
        minutes_method = st.radio("Minutes Entry Method",
                                  options=["✍️ Manual Entry", "🤖 AI from Transcript"],
                                  horizontal=True, key="minutes_entry_method")
        
        if minutes_method == "✍️ Manual Entry":
            st.caption("Enter notes for each standing item. Leave a section blank if it wasn't discussed.")
            seed = _parse_minutes_sections(minutes)
            section_values = _render_minutes_section_fields(seed, key_prefix="manual_section")
            minutes = _build_minutes_from_sections(section_values)
        
        else:  # AI from Transcript
            st.markdown("**Paste your transcript below, or upload a file (.txt / .docx)**")
            st.caption(
                "Two steps: Step 1 condenses the transcript into a short synthesis of what was "
                "actually discussed — the Acknowledgement of Country and icebreaker activity are "
                "dropped automatically, not just summarised. Step 2 sorts that short synthesis "
                "(not the raw transcript) into the six sections below, which is what keeps each AI "
                "call well under Groq's token limit."
            )

            _mkey = st.session_state.current_staff_meeting_id or "new"
            synthesis_state_key = f"transcript_synthesis_{_mkey}"
            synthesis_widget_key = f"synthesis_editor_{_mkey}"

            # ── Paste or upload ───────────────────────────────────────────────
            transcript_text = ""

            pasted = st.text_area(
                "Paste transcript here",
                height=180,
                key="transcript_paste",
                placeholder="Paste your meeting transcript or voice-to-text output here…"
            )
            if pasted.strip():
                transcript_text = pasted.strip()

            transcript_file = st.file_uploader(
                "Or upload a file",
                type=['txt', 'docx'],
                key="transcript_upload",
                label_visibility="collapsed"
            )
            if transcript_file and not transcript_text:
                if transcript_file.name.endswith('.txt'):
                    transcript_text = transcript_file.read().decode('utf-8')
                else:
                    if DOCX_AVAILABLE:
                        try:
                            doc = docx.Document(transcript_file)
                            transcript_text = '\n'.join([p.text for p in doc.paragraphs])
                        except Exception as e:
                            st.error(f"Could not read .docx: {e}")
                    else:
                        st.error("python-docx not installed — please paste the transcript instead.")

            st.markdown("---")

            # ══════════════════════════════════════════════════════════════════
            # STEP 1 — Synthesise the transcript. This drops the Acknowledgement
            # of Country and icebreaker activity entirely and condenses the rest,
            # so the text that later gets classified into sections is small — the
            # raw transcript never goes near the classifier prompt.
            # ══════════════════════════════════════════════════════════════════
            st.markdown("##### Step 1 · Synthesise transcript")

            if transcript_text and GROQ_KEY:
                if st.button("🧹 Synthesise Transcript", key="synthesise_transcript_btn"):
                    with st.spinner("Condensing transcript…"):
                        try:
                            from groq import Groq
                            client = Groq(api_key=GROQ_KEY)

                            transcript_for_synthesis, was_truncated = _fit_to_groq_budget(
                                transcript_text, max_tokens=1200, prompt_overhead_tokens=350
                            )
                            if was_truncated:
                                st.warning(
                                    "⚠️ This transcript is longer than the AI can read in one go "
                                    "(Groq's 8,000 tokens/minute limit on the current plan). Only "
                                    "the first part was synthesised. Paste the rest of the transcript "
                                    "above and click **Synthesise Transcript** again — the new part "
                                    "will be added to the synthesis below rather than replacing it."
                                )

                            synthesis_prompt = f"""Read the transcript of a school staff meeting below
and condense it into a short, information-dense synthesis of what was
actually discussed, ready to be sorted into meeting minutes afterwards.

Rules:
1. COMPLETELY leave out the Acknowledgement of Country (the formal
   acknowledgement/welcome-to-country reading) — do not mention that it
   happened, just omit it entirely.
2. COMPLETELY leave out the icebreaker / BSEM activity (warm-up games,
   check-ins, "two truths and a lie", wellbeing rounds, etc.) — omit it
   entirely, do not summarise it.
3. Keep every substantive point: updates given, decisions made, concerns
   raised, and action items (what needs to be done, who's responsible, and
   any due date mentioned).
4. Keep staff names, dates and figures that are mentioned.
5. Write in tight prose or bullet points — no filler, no small talk, no
   repeated pleasantries.
6. Do not invent anything that isn't in the transcript.

Return ONLY the condensed synthesis text — no preamble, no commentary.

TRANSCRIPT:
{transcript_for_synthesis}"""

                            response = client.chat.completions.create(
                                model="openai/gpt-oss-120b",
                                messages=[{"role": "user", "content": synthesis_prompt}],
                                temperature=0.2,
                                max_tokens=1200
                            )
                            new_synthesis = response.choices[0].message.content.strip()

                            existing_synthesis = (st.session_state.get(synthesis_state_key) or "").strip()
                            if existing_synthesis:
                                combined = existing_synthesis + "\n\n— continued —\n\n" + new_synthesis
                                st.success("✅ Transcript synthesised and added to the synthesis below.")
                            else:
                                combined = new_synthesis
                                st.success("✅ Transcript synthesised — review it below before generating minutes.")

                            st.session_state[synthesis_state_key] = combined
                            # Widget key already exists once rendered, so setting it here
                            # (not just the value= below) is what actually updates the box.
                            st.session_state[synthesis_widget_key] = combined

                        except Exception as e:
                            st.error(f"Synthesis failed: {e}")

            elif transcript_text and not GROQ_KEY:
                st.warning("⚠️ GROQ_API_KEY not configured.")
            else:
                st.caption("Paste or upload a transcript above, then click **Synthesise Transcript**.")

            current_synthesis = st.session_state.get(synthesis_state_key, "")

            synthesis_for_minutes = ""
            if current_synthesis:
                col_syn, col_syn_clear = st.columns([5, 1])
                with col_syn:
                    st.caption(
                        "Review/edit the synthesis below — this is what Step 2 sorts into "
                        "sections, not the raw transcript."
                    )
                with col_syn_clear:
                    if st.button("🗑️ Clear", key="clear_synthesis_btn", help="Clear the synthesis and start over"):
                        st.session_state[synthesis_state_key] = ""
                        st.session_state.pop(synthesis_widget_key, None)
                        st.rerun()
                synthesis_for_minutes = st.text_area(
                    "Transcript synthesis",
                    value=current_synthesis,
                    height=180,
                    key=synthesis_widget_key,
                    label_visibility="collapsed"
                )

            st.markdown("---")

            # ══════════════════════════════════════════════════════════════════
            # STEP 2 — Sort the (short) synthesis into the six standing sections
            # ══════════════════════════════════════════════════════════════════
            st.markdown("##### Step 2 · Generate structured minutes")

            if synthesis_for_minutes.strip() and GROQ_KEY:
                if st.button("🤖 Generate Structured Minutes", type="primary", key="generate_minutes_btn"):

                    with st.spinner("Generating structured minutes…"):
                        try:
                            from groq import Groq
                            client = Groq(api_key=GROQ_KEY)

                            synthesis_for_ai, was_truncated = _fit_to_groq_budget(
                                synthesis_for_minutes.strip(), max_tokens=2000, prompt_overhead_tokens=400
                            )
                            if was_truncated:
                                st.warning(
                                    "⚠️ Even the synthesis is longer than the AI can process in one "
                                    "go. Trim the synthesis above (or split the transcript into "
                                    "smaller parts at Step 1) and try again."
                                )

                            section_list = "\n".join(f"- {label}" for _, label in MEETING_SECTIONS)

                            prompt = f"""Read the synthesis of a school staff meeting below and sort what
was discussed into EXACTLY these six standing sections, in this order:
{section_list}

For each section, summarise what was discussed, any decisions made, and any
action items (what needs to be done, who's responsible, and the due date if
mentioned). If a section was not discussed at all, use exactly this text for
it: "{_NIL_TEXT}"

Do not invent information that isn't in the synthesis. If something doesn't
clearly belong to one of the six sections, put it under "Other Business".

Return ONLY a JSON object with exactly these keys, no preamble or commentary:
{{
  "manager_business": "...",
  "transition_coordinator": "...",
  "finance": "...",
  "whs": "...",
  "pac": "...",
  "other_business": "..."
}}

MEETING SYNTHESIS:
{synthesis_for_ai}"""

                            response = client.chat.completions.create(
                                model="openai/gpt-oss-120b",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.2,
                                max_tokens=2000
                            )
                            raw = response.choices[0].message.content.strip()
                            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                            if not json_match:
                                raise ValueError("AI did not return the expected structured format — try again.")
                            new_sections = json.loads(json_match.group())
                            new_sections = {
                                key: str(new_sections.get(key, "")).strip()
                                for key, _ in MEETING_SECTIONS
                            }

                            # The synthesis already merges any multi-part transcript (Step 1
                            # appends rather than overwrites), so a single classification pass
                            # over the whole thing can just replace the draft sections outright.
                            st.session_state["ai_section_values"] = new_sections
                            # Sync the edit widgets too — once a widget key exists in
                            # session_state, its `value=` argument is ignored on rerun,
                            # so this is what actually updates what's shown for editing.
                            for key, _ in MEETING_SECTIONS:
                                st.session_state[f"ai_section_manual_{key}"] = new_sections[key]

                            st.success("✅ Minutes generated — review the sections below before saving.")

                        except Exception as e:
                            st.error(f"AI extraction failed: {e}")

            elif synthesis_for_minutes.strip() and not GROQ_KEY:
                st.warning("⚠️ GROQ_API_KEY not configured.")
            else:
                st.caption("Complete Step 1 above to produce a synthesis, then generate structured minutes from it.")

            # ── Review and edit the generated sections before saving ──────────
            if st.session_state.get("ai_section_values"):
                st.markdown("---")
                st.markdown("#### ✏️ Review and edit before saving")
                col_edit, col_clear = st.columns([5, 1])
                with col_clear:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Clear draft", key="clear_ai_sections"):
                        st.session_state["ai_section_values"] = None
                        for key, _ in MEETING_SECTIONS:
                            st.session_state.pop(f"ai_section_manual_{key}", None)
                        st.rerun()
                seed = st.session_state.get("ai_section_values", {})
                section_values = _render_minutes_section_fields(seed, key_prefix="ai_section_manual")
                minutes = _build_minutes_from_sections(section_values)
            else:
                st.info("Paste or upload a transcript, then run Step 1 and Step 2 above to fill in "
                         "the sections.")
                # minutes keeps whatever was previously saved until something is generated

        if minutes and minutes.strip():
            with st.expander("👁️ Preview combined minutes"):
                st.markdown(minutes)

st.subheader("✅ Actions")

# Load actions
if selected_record and selected_record.get('actions'):
    try:
        if isinstance(selected_record['actions'], str):
            actions = json.loads(selected_record['actions'])
        else:
            actions = selected_record['actions']
    except:
        actions = []
else:
    actions = []

# AI Action Extraction option (if minutes exist)
if minutes and minutes.strip() and GROQ_KEY:
    with st.expander("🤖 Extract Actions from Minutes with AI", expanded=False):
        st.caption("AI will scan the minutes and extract action items automatically")
        
        if st.button("🤖 Extract Actions", type="secondary", key="extract_actions_ai"):
            with st.spinner("Extracting actions from minutes..."):
                try:
                    from groq import Groq
                    client = Groq(api_key=GROQ_KEY)

                    minutes_for_ai, was_truncated = _fit_to_groq_budget(
                        minutes, max_tokens=2000, prompt_overhead_tokens=250
                    )
                    if was_truncated:
                        st.warning(
                            "⚠️ These minutes are longer than the AI can process in one go "
                            "(Groq's 8,000 tokens/minute limit on the current plan). "
                            "Only the first part was sent — check for any actions later in "
                            "the minutes and add them manually if missed."
                        )

                    action_prompt = f"""From these meeting minutes, extract all action items.

For each action, identify:
1. What needs to be done (the action)
2. Who is responsible (name if mentioned, otherwise "Unassigned")
3. Deadline (if mentioned, otherwise leave blank)

Return ONLY a JSON array in this exact format:
[
  {{"action": "action description", "owner": "person name", "due_date": "YYYY-MM-DD or blank"}},
  {{"action": "action description", "owner": "person name", "due_date": "YYYY-MM-DD or blank"}}
]

If no actions found, return: []

Meeting Minutes:
{minutes_for_ai}

JSON array of actions:"""

                    response = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[{"role": "user", "content": action_prompt}],
                        temperature=0.2,
                        max_tokens=2000
                    )
                    
                    extracted_text = response.choices[0].message.content.strip()
                    
                    # Try to parse JSON
                    import re
                    # Extract JSON array from response
                    json_match = re.search(r'\[.*\]', extracted_text, re.DOTALL)
                    if json_match:
                        extracted_actions = json.loads(json_match.group())
                        
                        if extracted_actions:
                            st.success(f"✅ Found {len(extracted_actions)} action items!")
                            
                            # Show preview
                            for action in extracted_actions:
                                st.write(f"• {action.get('action', '')} - **{action.get('owner', 'Unassigned')}** - {action.get('due_date', 'No deadline')}")
                            
                            if st.button("➕ Add All Actions", key="add_extracted_actions"):
                                # Add to actions list
                                for action in extracted_actions:
                                    actions.append({
                                        "action": action.get('action', ''),
                                        "owner": action.get('owner', 'Unassigned'),
                                        "due_date": action.get('due_date', ''),
                                        "done": False
                                    })
                                st.success(f"Added {len(extracted_actions)} actions!")
                                st.rerun()
                        else:
                            st.info("No action items found in minutes")
                    else:
                        st.warning("Could not parse AI response. Add actions manually below.")
                        
                except Exception as e:
                    st.error(f"Action extraction failed: {e}")

# Display existing actions
if actions:
    st.write("**Current Actions:**")
    for idx, action in enumerate(actions):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.write(f"{idx+1}. {action.get('action', '')} - **{action.get('owner', 'Unassigned')}** - Due: {action.get('due_date', 'No date')}")
        with col_b:
            if st.button("🗑️", key=f"delete_action_{idx}"):
                actions.pop(idx)
                st.rerun()

st.write("**Add New Action:**")
col_a1, col_a2, col_a3, col_a4 = st.columns([3, 2, 2, 1])

with col_a1:
    new_action = st.text_input("Action Description", key="new_action", placeholder="What needs to be done?")

with col_a2:
    new_owner = st.text_input("Assigned To", key="new_owner", placeholder="Who will do it?")

with col_a3:
    new_due = st.date_input("Due Date", key="new_due", value=None)

with col_a4:
    st.write("")  # Spacing
    st.write("")  # Spacing
    if st.button("➕ Add", key="add_action_btn", use_container_width=True):
        if new_action.strip():
            actions.append({
                "action": new_action.strip(),
                "owner": new_owner.strip(),
                "due_date": str(new_due) if new_due else "",
                "done": False
            })
            st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING ATTACHMENTS (General)
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📎 Meeting Attachments")

with st.expander("📁 Attach Files to Meeting", expanded=False):

    # Kept in session_state, not just re-read from the saved record, so files
    # added here survive the rerun this section triggers — previously they
    # were silently lost on rerun before "Save Meeting" ever saw them.
    _mtg_key = st.session_state.current_staff_meeting_id or "new"
    _meeting_att_ss_key = f"meeting_attachments_{_mtg_key}"
    if _meeting_att_ss_key not in st.session_state:
        if selected_record and selected_record.get('meeting_attachments'):
            try:
                _seed = json.loads(selected_record['meeting_attachments']) if isinstance(selected_record['meeting_attachments'], str) else selected_record['meeting_attachments']
            except Exception:
                _seed = []
        else:
            _seed = []
        st.session_state[_meeting_att_ss_key] = _seed
    meeting_attachments = st.session_state[_meeting_att_ss_key]

    # Display existing attachments
    if meeting_attachments:
        st.write("**Attached Files:**")
        for idx, attachment in enumerate(meeting_attachments):
            col_m1, col_m2 = st.columns([4, 1])
            with col_m1:
                _render_attachment_link(attachment, MEETING_ATTACHMENTS_BUCKET)
            with col_m2:
                if st.button("🗑️", key=f"delete_meeting_attachment_{idx}"):
                    _delete_attachment(MEETING_ATTACHMENTS_BUCKET, attachment.get('path'))
                    meeting_attachments.pop(idx)
                    st.session_state[_meeting_att_ss_key] = meeting_attachments
                    st.rerun()

    # Add multiple attachments at once
    st.write("**Add Files:**")
    meeting_uploaded_files = st.file_uploader("Upload files (select multiple)",
                                             type=['pdf', 'docx', 'pptx', 'txt', 'jpg', 'png', 'xlsx', 'csv', 'mp4', 'mov'],
                                             accept_multiple_files=True,
                                             key="meeting_file_upload")

    if meeting_uploaded_files:
        st.write(f"**{len(meeting_uploaded_files)} file(s) selected**")

        # Show selected files
        for f in meeting_uploaded_files:
            st.caption(f"📄 {f.name}")

        # Description for all files
        meeting_batch_desc = st.text_input("Description for all files (optional)",
                                          key="meeting_batch_desc",
                                          placeholder="E.g., Budget documents, Policy drafts")

        if st.button("➕ Add All Files", key="add_all_meeting_attachments", type="secondary"):
            added, failed = 0, []
            with st.spinner("Uploading file(s)…"):
                for file in meeting_uploaded_files:
                    result = _upload_attachment(MEETING_ATTACHMENTS_BUCKET, f"meeting_{_mtg_key}", file)
                    if "path" in result:
                        meeting_attachments.append({
                            "name": file.name,
                            "description": meeting_batch_desc if meeting_batch_desc else "",
                            "filename": file.name,
                            "path": result["path"],
                            "size": file.size,
                            "type": file.type,
                            "uploaded_date": str(datetime.date.today())
                        })
                        added += 1
                    else:
                        failed.append((file.name, result.get("error", "unknown error")))
            st.session_state[_meeting_att_ss_key] = meeting_attachments
            for name, err in failed:
                st.error(f"⚠️ Could not upload {name}: {err}")
            if added:
                st.success(f"✅ Uploaded and added {added} file(s) to meeting!")
                st.info("💡 Click 'Save Meeting' at the bottom to save these to the meeting record.")
                st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 7. PROFESSIONAL DEVELOPMENT
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("🎓 Professional Development Component")

with st.expander("📚 PD Session Details", expanded=True):

    # PD Title
    default_pd_title = selected_record.get('pd_title', '') if selected_record else ''
    pd_title = st.text_input("PD Session Title", value=default_pd_title, key="pd_title",
                             placeholder="e.g. Sounds-Write Introduction, Berry Street Module 3, WHS Refresher…")

    st.write("**PD Attendance** (Auto-filled from meeting attendance - edit if needed)")
    
    col_pd1, col_pd2 = st.columns(2)
    
    with col_pd1:
        # Pre-fill with meeting attendees but allow editing
        default_pd_attendees = selected_record.get('pd_attendees', attendees) if selected_record else attendees
        pd_attendees = st.text_area("PD Attendees", value=default_pd_attendees, height=80, key="pd_attendees",
                                   placeholder="Staff who attended PD session...")
    
    with col_pd2:
        default_pd_absent = selected_record.get('pd_absent', apologies) if selected_record else apologies
        pd_absent = st.text_area("PD Absentees/Left Early", value=default_pd_absent, height=80, key="pd_absent",
                                placeholder="Staff who missed PD or left early...")
    
    st.markdown("---")
    
    # PD Content Entry Method
    st.write("**PD Content Entry:**")
    
    # Initialize pd_notes (will be set in either manual or AI path)
    pd_notes = selected_record.get('pd_notes', '') if selected_record else ''
    
    pd_method = st.radio("Choose entry method", options=["✍️ Manual Entry", "🤖 AI from Transcript"], 
                       horizontal=True, key="pd_method")
    
    if pd_method == "✍️ Manual Entry":
        pd_notes = st.text_area("PD Main Points / Notes", value=pd_notes, height=300, key="pd_notes",
                               placeholder="Document key points from the PD session...")
    
    else:  # AI from Transcript
        st.write("**Upload PD Transcript**")
        
        pd_transcript_file = st.file_uploader("Upload PD transcript (.txt or .docx)", 
                                             type=['txt', 'docx'], 
                                             key="pd_transcript_upload")
        
        if pd_transcript_file:
            # Read transcript
            if pd_transcript_file.name.endswith('.txt'):
                pd_transcript_text = pd_transcript_file.read().decode('utf-8')
            else:  # .docx
                if DOCX_AVAILABLE:
                    try:
                        pd_doc = docx.Document(pd_transcript_file)
                        pd_transcript_text = '\n'.join([para.text for para in pd_doc.paragraphs])
                    except Exception as e:
                        st.error(f"Could not read .docx file: {e}")
                        pd_transcript_text = ""
                else:
                    st.error("python-docx not installed. Please use .txt file.")
                    pd_transcript_text = ""
            
            if pd_transcript_text and GROQ_KEY:
                if st.button("🤖 Extract PD Notes with AI", type="secondary", key="extract_pd_ai"):
                    with st.spinner("Processing PD transcript..."):
                        try:
                            from groq import Groq
                            client = Groq(api_key=GROQ_KEY)

                            pd_transcript_for_ai, was_truncated = _fit_to_groq_budget(
                                pd_transcript_text, max_tokens=3000, prompt_overhead_tokens=250
                            )
                            if was_truncated:
                                st.warning(
                                    "⚠️ This PD transcript is longer than the AI can process in one go "
                                    "(Groq's 8,000 tokens/minute limit on the current plan). "
                                    "Only the first part was sent — review the extracted notes and "
                                    "add anything from later in the session by hand, or split the "
                                    "transcript into parts and run each separately."
                                )

                            prompt = f"""Extract the main points and key learnings from this professional development session transcript.

Structure the output with:
- Topic/Title of PD session
- Key points covered (bullet points)
- Main takeaways
- Any action items or next steps

Transcript:
{pd_transcript_for_ai}

Format as clear, structured notes."""

                            response = client.chat.completions.create(
                                model="openai/gpt-oss-120b",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.3,
                                max_tokens=3000
                            )
                            
                            extracted_pd = response.choices[0].message.content
                            
                            st.success("✅ PD notes extracted!")
                            pd_notes = st.text_area("Edit AI-Generated PD Notes", value=extracted_pd, 
                                                   height=300, key="ai_pd_notes")
                            
                        except Exception as e:
                            st.error(f"AI extraction failed: {e}")
                            pd_notes = st.text_area("Manual entry (AI failed)", height=300, key="fallback_pd_notes")
            elif not GROQ_KEY:
                st.warning("⚠️ GROQ_API_KEY not configured. Using manual entry.")
                pd_notes = st.text_area("PD Notes", height=300, key="manual_pd_notes_fallback")
            else:
                pd_notes = ""
        else:
            st.info("Upload a transcript to use AI extraction")
            pd_notes = ""
    
    st.markdown("---")
    
    # PD Attachments
    st.write("**PD Attachments / Resources:**")

    # Kept in session_state, not just re-read from the saved record, so files
    # added here survive the rerun this section triggers — previously they
    # were silently lost on rerun before "Save Meeting" ever saw them.
    _pd_att_ss_key = f"pd_attachments_{_mtg_key}"
    if _pd_att_ss_key not in st.session_state:
        if selected_record and selected_record.get('pd_attachments'):
            try:
                _pd_seed = json.loads(selected_record['pd_attachments']) if isinstance(selected_record['pd_attachments'], str) else selected_record['pd_attachments']
            except Exception:
                _pd_seed = []
        else:
            _pd_seed = []
        st.session_state[_pd_att_ss_key] = _pd_seed
    pd_attachments = st.session_state[_pd_att_ss_key]

    # Display existing attachments
    if pd_attachments:
        st.write("**Uploaded Attachments:**")
        for idx, attachment in enumerate(pd_attachments):
            col_att1, col_att2 = st.columns([4, 1])
            with col_att1:
                _render_attachment_link(attachment, PD_ATTACHMENTS_BUCKET)
            with col_att2:
                if st.button("🗑️", key=f"delete_pd_attachment_{idx}"):
                    _delete_attachment(PD_ATTACHMENTS_BUCKET, attachment.get('path'))
                    pd_attachments.pop(idx)
                    st.session_state[_pd_att_ss_key] = pd_attachments
                    st.rerun()

    # Add multiple attachments at once
    st.write("**Add New Attachments:**")
    uploaded_files = st.file_uploader("Upload files (select multiple)",
                                     type=['pdf', 'docx', 'pptx', 'txt', 'jpg', 'png', 'xlsx', 'mp4', 'mov'],
                                     accept_multiple_files=True,
                                     key="pd_file_upload")

    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected**")

        # Show selected files
        for f in uploaded_files:
            st.caption(f"📄 {f.name}")

        # Description for all files (optional)
        batch_description = st.text_input("Description for all files (optional)",
                                         key="pd_batch_desc",
                                         placeholder="E.g., Restorative Practices Resources")

        if st.button("➕ Add All Files", key="add_all_pd_attachments", type="secondary"):
            added, failed = 0, []
            with st.spinner("Uploading file(s)…"):
                for file in uploaded_files:
                    result = _upload_attachment(PD_ATTACHMENTS_BUCKET, f"pd_{_mtg_key}", file)
                    if "path" in result:
                        pd_attachments.append({
                            "name": file.name,
                            "description": batch_description if batch_description else "",
                            "filename": file.name,
                            "path": result["path"],
                            "size": file.size,
                            "type": file.type,
                            "uploaded_date": str(datetime.date.today())
                        })
                        added += 1
                    else:
                        failed.append((file.name, result.get("error", "unknown error")))
            st.session_state[_pd_att_ss_key] = pd_attachments
            for name, err in failed:
                st.error(f"⚠️ Could not upload {name}: {err}")
            if added:
                st.success(f"✅ Uploaded and added {added} file(s) to PD!")
                st.info("💡 Click 'Save Meeting' at the bottom to save these to the meeting record.")
                st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD + SAVE
# ══════════════════════════════════════════════════════════════════════════════

meeting_data = {
    "meeting_date": str(meeting_date),
    "term": term.strip(),
    "week_number": int(week_number),
    "minute_taker": minute_taker.strip(),
    "attendees": attendees.strip(),
    "apologies": apologies.strip(),
    "acknowledgement_done": acknowledgement_done,
    "acknowledgement_by": acknowledgement_by.strip(),
    "icebreaker": icebreaker_notes.strip(),
    "agenda_items": json.dumps(agenda_data),
    "minutes": minutes.strip() if minutes else '',
    "actions": json.dumps(actions) if actions else '[]',
    "meeting_attachments": json.dumps(meeting_attachments) if meeting_attachments else '[]',
    "pd_attendees": pd_attendees.strip(),
    "pd_absent": pd_absent.strip(),
    "pd_notes": pd_notes.strip() if pd_notes else '',
    "pd_title": pd_title.strip() if pd_title else '',
    "pd_attachments": json.dumps(pd_attachments) if pd_attachments else '[]'
}

col_dl, col_save = st.columns([1, 2])
with col_dl:
    if DOCX_AVAILABLE and meeting_data["minutes"].strip():
        st.download_button(
            "📥 Download Minutes (.docx)",
            data=_build_minutes_docx_bytes(meeting_data),
            file_name=f"Staff_Meeting_Minutes_{meeting_data['meeting_date']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="download_current_minutes"
        )
    else:
        st.button("📥 Download Minutes (.docx)", disabled=True, use_container_width=True,
                  help="Add some minutes content first" if DOCX_AVAILABLE else "python-docx not installed")

with col_save:
    if st.button("💾 Save Meeting", type="primary", use_container_width=True, key="save_meeting"):
        try:
            if st.session_state.current_staff_meeting_id:
                # Update existing
                result = supabase.table('staff_meetings').update(meeting_data).eq('id', st.session_state.current_staff_meeting_id).execute()
                st.success("✅ **Meeting Saved Successfully!**")
                st.info("📄 Minutes, agenda, and actions have been saved. The Minutes section will collapse on next page load.")
                time.sleep(2)
                st.rerun()
            else:
                # Create new
                result = supabase.table('staff_meetings').insert(meeting_data).execute()
                if result.data:
                    st.session_state.current_staff_meeting_id = result.data[0]['id']
                    st.success("✅ **New Meeting Created & Saved!**")
                    st.info("📄 All meeting details saved successfully.")
                    time.sleep(2)
                    st.rerun()

        except Exception as e:
            st.error(f"⚠️ Could not save meeting: {e}")

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre · LBU · STAFF Meetings")
