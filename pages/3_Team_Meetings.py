from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
from groq import Groq
import json
import io
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="CLC Team Meetings", page_icon="👥", layout="wide")
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
require_auth("Team Meetings", "👥")
logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)


# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "CLC2026admin")
GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Helpers ───────────────────────────────────────────────────────────────────
PROGRAMS = {
    "JP":    {"label": "Junior Primary",  "color": "#2d7d4f", "light": "#d1fae5", "emoji": "🟢"},
    "PY":    {"label": "Primary Years",   "color": "#1a4d8c", "light": "#dbeafe", "emoji": "🔵"},
    "SY":    {"label": "Senior Years",    "color": "#7c3aed", "light": "#ede9fe", "emoji": "🟣"},
    "STAFF": {"label": "Staff Meetings",  "color": "#1e6f75", "light": "#ccfbf1", "emoji": "👥"},
    "ADMIN": {"label": "Admin Meetings",  "color": "#92400e", "light": "#fef3c7", "emoji": "🏢"},
}

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
RECURRENCE_TYPES = ["Weekly", "Fortnightly", "Monthly"]

def get_program_from_params():
    params = st.query_params
    prog = params.get("program", "JP")
    return prog if prog in PROGRAMS else "JP"

def get_week_from_params():
    week_str = st.query_params.get("week", None)
    if not week_str:
        return None
    try:
        monday = datetime.date.fromisoformat(week_str)
        monday = monday - datetime.timedelta(days=monday.weekday())
        return monday, monday + datetime.timedelta(days=6)
    except ValueError:
        return None

def admin_login():
    # This is a separate in-app admin level for editing/deleting content
    # (distinct from the shared staff auth handled by auth.py above)
    if "admin" not in st.session_state:
        st.session_state.admin = False
    with st.sidebar:
        if not st.session_state.admin:
            with st.expander("🔐 Admin Login"):
                pw = st.text_input("Password", type="password", key="pw_input")
                if st.button("Login"):
                    if pw == ADMIN_PASSWORD:
                        st.session_state.admin = True
                        st.rerun()
                    else:
                        st.error("Incorrect password")
        else:
            st.success("✅ Admin logged in")
            if st.button("Logout"):
                st.session_state.admin = False
                st.rerun()

def improve_with_ai(raw_text: str, program: str, meeting_date: str, dsm_summary: str = "") -> str:
    if not GROQ_KEY:
        return raw_text
    client = Groq(api_key=GROQ_KEY)
    
    if program == "STAFF":
        dsm_context = f"""
PART 1 — DIGITAL STAFF MEETING (already recorded, include as first section):
{dsm_summary}
""" if dsm_summary else ""
        
        prompt = f"""You are a professional minute-taker for Cowandilla Learning Centre (CLC), Learning & Behaviour Unit — an alternative education school in South Australia.

Meeting: Staff Meeting (Combined — Digital + Face-to-Face)
Date: {meeting_date}
{dsm_context}
PART 2 — FACE-TO-FACE MEETING TRANSCRIPT:
{raw_text}

Transform the face-to-face transcript into polished, professional minutes using this EXACT structure:

## PART 2 — FACE-TO-FACE STAFF MEETING

### Attendance
List names present and apologies from the transcript. If not clear, note "See attendance record."

### Apologies
Names with apologies.

### Arising Business
Any matters arising from previous meetings mentioned in the transcript.

### Standing Items
Present each discussion point as a numbered item:
1. **Item title** — summary of discussion and any decisions made

### Actions
| Action | Assigned To | Due |
|--------|-------------|-----|
| (list all actions agreed) | (who) | (when) |

### Next Meeting
Date/time if mentioned, otherwise leave blank.

Rules:
- Professional but warm, accessible language appropriate for a school setting
- Trauma-informed, strengths-based framing
- Preserve ALL factual content — do not add or fabricate anything
- Keep it concise — one clear sentence per discussion point unless more detail is essential
- Use plain English, avoid jargon

Transcript to transform:
{raw_text}"""
    else:
        prompt = f"""You are a professional minute-taker for an alternative education school (Cowandilla Learning Centre, Learning & Behaviour Unit).

Program team: {PROGRAMS[program]['label']} ({program})
Meeting date: {meeting_date}

Transform the following raw transcript or rough notes into polished, professional meeting minutes.

Format requirements:
- Clear heading with meeting details
- Numbered agenda items with concise summaries
- Action items clearly identified with: Action | Assigned to | Timeline
- Professional but accessible language
- Trauma-informed, strengths-based framing where relevant
- Preserve all factual content — do not add or fabricate information
- End with a summary table of all action items

Raw input:
{raw_text}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000
    )
    return response.choices[0].message.content

# ── DB helpers ────────────────────────────────────────────────────────────────
def fetch(table, filters=None, order=None):
    q = supabase.table(table).select("*")
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    if order:
        q = q.order(order, desc=True)
    return q.execute().data or []

def insert(table, data):
    supabase.table(table).insert(data).execute()

def update_row(table, row_id, data):
    supabase.table(table).update(data).eq("id", row_id).execute()

def delete_row(table, row_id):
    supabase.table(table).delete().eq("id", row_id).execute()

# ─────────────────────────────────────────────────────────────────────────────
# WORD DOCUMENT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _hex(colour):
    return colour.lstrip("#").upper()

def _shade_cell(cell, hex_colour):
    try:
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  _hex(hex_colour))
        tcPr.append(shd)
    except Exception:
        pass

def _rgb(hex_colour):
    h = _hex(hex_colour)
    return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def _para_run(para, text, bold=False, italic=False, size_pt=10, colour="0f172a"):
    run = para.add_run(str(text))
    run.bold           = bold
    run.italic         = italic
    run.font.size      = Pt(size_pt)
    run.font.color.rgb = _rgb(colour)
    return run

def _add_banner(doc, text, bg="1e293b", fg="FFFFFF", size=12):
    table = doc.add_table(rows=1, cols=1)
    cell  = table.cell(0, 0)
    _shade_cell(cell, bg)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after  = Pt(3)
    _para_run(p, f"  {text}", bold=True, size_pt=size, colour=fg)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

def _add_kv_table(doc, rows, col1_bg="1e3a5f", col1_fg="FFFFFF", col2_bg="f8fafc", col2_fg="0f172a"):
    table = doc.add_table(rows=len(rows), cols=2)
    try:
        table.style = "Table Grid"
    except Exception:
        pass
    for i, (k, v) in enumerate(rows):
        c1, c2 = table.cell(i, 0), table.cell(i, 1)
        if i == 0:
            _shade_cell(c1, col1_bg); _shade_cell(c2, col1_bg)
            _para_run(c1.paragraphs[0], k, bold=True, size_pt=9, colour=col1_fg)
            _para_run(c2.paragraphs[0], v, bold=True, size_pt=9, colour=col1_fg)
        else:
            _shade_cell(c1, "e2e8f0"); _shade_cell(c2, col2_bg)
            _para_run(c1.paragraphs[0], k, bold=True, size_pt=9, colour="334155")
            _para_run(c2.paragraphs[0], v, bold=False, size_pt=9, colour=col2_fg)
    try:
        for row in table.rows:
            row.cells[0].width = Cm(5)
            row.cells[1].width = Cm(12)
    except Exception:
        pass
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def _add_attendance_table(doc, present, apologies):
    rows = max(len(present), len(apologies), 1)
    table = doc.add_table(rows=rows + 1, cols=2)
    try:
        table.style = "Table Grid"
    except Exception:
        pass
    for ci, (hdr, bg) in enumerate([("✅  Present", "2d7d4f"), ("⚠️  Apologies", "92400e")]):
        c = table.cell(0, ci)
        _shade_cell(c, bg)
        _para_run(c.paragraphs[0], hdr, bold=True, size_pt=9, colour="FFFFFF")
    for ri in range(rows):
        pn = present[ri]   if ri < len(present)   else ""
        an = apologies[ri] if ri < len(apologies) else ""
        for ci, name in enumerate([pn, an]):
            cell = table.cell(ri + 1, ci)
            _shade_cell(cell, "f8fafc" if ri % 2 == 0 else "FFFFFF")
            _para_run(cell.paragraphs[0], name, size_pt=9)
    try:
        for row in table.rows:
            row.cells[0].width = Cm(8.5)
            row.cells[1].width = Cm(8.5)
    except Exception:
        pass
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def _add_digital_items_table(doc, items):
    if not items:
        p = doc.add_paragraph("No digital meeting items recorded.")
        p.paragraph_format.space_after = Pt(6)
        return
    headers = ["Item / Notice", "Raised By", "Actioned By", "Status"]
    table = doc.add_table(rows=len(items) + 1, cols=4)
    try:
        table.style = "Table Grid"
    except Exception:
        pass
    for ci, hdr in enumerate(headers):
        c = table.cell(0, ci)
        _shade_cell(c, "1e3a5f")
        _para_run(c.paragraphs[0], hdr, bold=True, size_pt=9, colour="FFFFFF")
    for ri, item in enumerate(items):
        status = str(item.get("status", "Noted"))
        row_bg = "f0f9ff" if ri % 2 == 0 else "FFFFFF"
        status_bg = "d1fae5" if "action" in status.lower() else "fef3c7" if "pending" in status.lower() else "f1f5f9"
        vals = [item.get("item",""), item.get("raised_by",""), item.get("actioned_by",""), status]
        for ci, val in enumerate(vals):
            cell = table.cell(ri + 1, ci)
            _shade_cell(cell, status_bg if ci == 3 else row_bg)
            _para_run(cell.paragraphs[0], str(val), size_pt=9)
    widths = [8.5, 3, 3, 2.5]
    try:
        for ci, w in enumerate(widths):
            for row in table.rows:
                row.cells[ci].width = Cm(w)
    except Exception:
        pass
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def _add_actions_table(doc, action_text):
    lines = [l.strip() for l in action_text.strip().splitlines() if l.strip()]
    if not lines:
        return
    _add_banner(doc, "✅  ACTION ITEMS SUMMARY", bg="4c1d95", fg="FFFFFF", size=11)
    table = doc.add_table(rows=len(lines) + 1, cols=3)
    try:
        table.style = "Table Grid"
    except Exception:
        pass
    for ci, hdr in enumerate(["Action", "Assigned To", "Due Date"]):
        c = table.cell(0, ci)
        _shade_cell(c, "5b21b6")
        _para_run(c.paragraphs[0], hdr, bold=True, size_pt=9, colour="FFFFFF")
    for ri, line in enumerate(lines):
        parts = [p.strip() for p in line.split("|")]
        for ci in range(3):
            cell = table.cell(ri + 1, ci)
            _shade_cell(cell, "f5f3ff" if ri % 2 == 0 else "FFFFFF")
            _para_run(cell.paragraphs[0], parts[ci] if ci < len(parts) else "", size_pt=9)
    try:
        for row in table.rows:
            row.cells[0].width = Cm(9.5)
            row.cells[1].width = Cm(4)
            row.cells[2].width = Cm(3.5)
    except Exception:
        pass
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def _add_content_block(doc, text, placeholder="Not recorded."):
    content = (text or "").strip()
    if not content:
        p = doc.add_paragraph(placeholder)
        p.paragraph_format.space_after = Pt(4)
        return
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            p = doc.add_paragraph(stripped)
            p.paragraph_format.space_after = Pt(2)
            p.runs[0].font.size = Pt(10) if p.runs else None
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def _doc_cover(doc, program, title, meeting_date):
    prog = PROGRAMS[program]
    prog_colours = {
        "JP": "2d7d4f", "PY": "1a4d8c", "SY": "7c3aed",
        "STAFF": "1e6f75", "ADMIN": "92400e"
    }
    accent = prog_colours.get(program, "1e293b")
    table = doc.add_table(rows=1, cols=1)
    cell  = table.cell(0, 0)
    _shade_cell(cell, "0f172a")
    p1 = cell.paragraphs[0]
    p1.paragraph_format.space_before = Pt(8)
    p1.paragraph_format.space_after  = Pt(2)
    _para_run(p1, "  Cowandilla Learning Centre — Learning & Behaviour Unit",
              bold=True, size_pt=9, colour="94a3b8")
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_before = Pt(2)
    p2.paragraph_format.space_after  = Pt(2)
    _para_run(p2, f"  {title or prog['label'] + ' Meeting Minutes'}",
              bold=True, size_pt=17, colour="FFFFFF")
    p3 = cell.add_paragraph()
    p3.paragraph_format.space_before = Pt(2)
    p3.paragraph_format.space_after  = Pt(8)
    _para_run(p3, f"  {prog['label']}   ·   {meeting_date}",
              bold=False, size_pt=10, colour=accent.upper() if len(accent) == 6 else "7dd3fc")
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def generate_combined_docx(m: dict) -> bytes:
    try:
        doc = Document()
        for section in doc.sections:
            section.top_margin    = Cm(1.8)
            section.bottom_margin = Cm(1.8)
            section.left_margin   = Cm(2.2)
            section.right_margin  = Cm(2.2)
        prog = "STAFF"
        _doc_cover(doc, prog, m.get("title",""), m.get("meeting_date",""))
        _add_banner(doc, "📋  MEETING DETAILS", bg="1e3a5f")
        _add_kv_table(doc, [
            ("Field",    "Details"),
            ("Program",  PROGRAMS[prog]["label"]),
            ("Date",     m.get("meeting_date", "—")),
            ("Chair",    m.get("chair", "—") or "—"),
            ("Location", m.get("location", "—") or "—"),
        ])
        _add_banner(doc, "🙋  ATTENDANCE", bg="1e3a5f")
        present   = [n.strip() for n in (m.get("attendees")  or "").split(",") if n.strip()]
        apologies = [n.strip() for n in (m.get("apologies")  or "").split(",") if n.strip()]
        _add_attendance_table(doc, present, apologies)
        _add_banner(doc, "💻  PART 1 — DIGITAL STAFF MEETING", bg="1a4d8c")
        digital_summary = (m.get("digital_summary") or "").strip()
        if digital_summary:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            _para_run(p, "Digital Meeting Summary", bold=True, size_pt=10, colour="1a4d8c")
            _add_content_block(doc, digital_summary)
        p = doc.add_paragraph()
        _para_run(p, "Items Raised — Viewed & Actioned Status", bold=True, size_pt=10, colour="1a4d8c")
        p.paragraph_format.space_after = Pt(4)
        try:
            digital_items = json.loads(m.get("digital_items") or "[]")
        except Exception:
            digital_items = []
        _add_digital_items_table(doc, digital_items)
        _add_banner(doc, "👥  PART 2 — FACE-TO-FACE MEETING", bg="2d7d4f")
        ff = (m.get("face_to_face_content") or m.get("content") or "").strip()
        _add_content_block(doc, ff, placeholder="No face-to-face minutes recorded.")
        action_text = (m.get("action_summary") or "").strip()
        if action_text:
            _add_actions_table(doc, action_text)
        doc.add_paragraph()
        footer_table = doc.add_table(rows=1, cols=1)
        fc = footer_table.cell(0, 0)
        _shade_cell(fc, "f1f5f9")
        fp = fc.paragraphs[0]
        fp.paragraph_format.space_before = Pt(4)
        fp.paragraph_format.space_after  = Pt(4)
        _para_run(fp,
            f"  Generated {datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')}  "
            f"·  CLC Learning & Behaviour Unit  ·  CONFIDENTIAL",
            italic=True, size_pt=8, colour="64748b")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        doc2 = Document()
        doc2.add_paragraph(f"Error generating formatted document: {e}")
        doc2.add_paragraph(f"Title: {m.get('title','')}")
        doc2.add_paragraph(f"Date: {m.get('meeting_date','')}")
        doc2.add_paragraph(m.get("digital_summary",""))
        doc2.add_paragraph(m.get("face_to_face_content","") or m.get("content",""))
        doc2.add_paragraph(m.get("action_summary",""))
        buf2 = io.BytesIO()
        doc2.save(buf2)
        buf2.seek(0)
        return buf2.getvalue()

def generate_team_docx(m: dict, program: str) -> bytes:
    try:
        doc = Document()
        for section in doc.sections:
            section.top_margin    = Cm(1.8)
            section.bottom_margin = Cm(1.8)
            section.left_margin   = Cm(2.2)
            section.right_margin  = Cm(2.2)
        prog_colours = {
            "JP": "2d7d4f", "PY": "1a4d8c", "SY": "7c3aed",
            "STAFF": "1e6f75", "ADMIN": "92400e"
        }
        col = prog_colours.get(program, "1e293b")
        _doc_cover(doc, program, m.get("title",""), m.get("meeting_date",""))
        _add_banner(doc, "📋  MEETING DETAILS", bg=col)
        _add_kv_table(doc, [
            ("Field",    "Details"),
            ("Program",  PROGRAMS[program]["label"]),
            ("Date",     m.get("meeting_date", "—")),
            ("Chair",    m.get("chair", "—") or "—"),
            ("Location", m.get("location", "—") or "—"),
        ])
        _add_banner(doc, "🙋  ATTENDANCE", bg=col)
        present   = [n.strip() for n in (m.get("attendees")  or "").split(",") if n.strip()]
        apologies = [n.strip() for n in (m.get("apologies")  or "").split(",") if n.strip()]
        _add_attendance_table(doc, present, apologies)
        _add_banner(doc, "📝  MEETING MINUTES", bg=col)
        content = (m.get("content") or m.get("face_to_face_content") or "").strip()
        _add_content_block(doc, content, placeholder="No minutes recorded.")
        action_text = (m.get("action_summary") or "").strip()
        if action_text:
            _add_actions_table(doc, action_text)
        doc.add_paragraph()
        footer_table = doc.add_table(rows=1, cols=1)
        fc = footer_table.cell(0, 0)
        _shade_cell(fc, "f1f5f9")
        fp = fc.paragraphs[0]
        fp.paragraph_format.space_before = Pt(4)
        fp.paragraph_format.space_after  = Pt(4)
        _para_run(fp,
            f"  Generated {datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')}  "
            f"·  CLC Learning & Behaviour Unit  ·  CONFIDENTIAL",
            italic=True, size_pt=8, colour="64748b")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        doc2 = Document()
        doc2.add_paragraph(f"Error generating formatted document: {e}")
        doc2.add_paragraph(f"Title: {m.get('title','')}")
        doc2.add_paragraph(f"Date: {m.get('meeting_date','')}")
        doc2.add_paragraph(m.get("content",""))
        doc2.add_paragraph(m.get("action_summary",""))
        buf2 = io.BytesIO()
        doc2.save(buf2)
        buf2.seek(0)
        return buf2.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def render_schedules(program):
    st.subheader("📅 Meeting Schedules")
    schedules = fetch("tm_schedules", {"program": program}, "created_at")
    if schedules:
        for s in schedules:
            rec_label  = s.get("recurrence_type", "Weekly")
            day_label  = s.get("day_of_week", "")
            time_label = s.get("meeting_time", "")
            flags = []
            if s.get("show_in_calendar"): flags.append("📅 Calendar")
            if s.get("show_in_bulletin"): flags.append("📋 Bulletin")
            flag_str = "  ·  ".join(flags) if flags else "No flags"
            with st.expander(
                f"📌 {s.get('schedule_name','Unnamed')} — {rec_label} {day_label} {time_label}",
                expanded=False
            ):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Recurrence:** {rec_label}")
                c2.markdown(f"**Day/Time:** {day_label} {time_label}")
                c3.markdown(f"**Flags:** {flag_str}")
                if s.get("notes"):
                    st.caption(s["notes"])
                if st.session_state.get("admin"):
                    col_e, col_d = st.columns(2)
                    with col_d:
                        if st.button("🗑️ Delete", key=f"del_sched_{s['id']}"):
                            delete_row("tm_schedules", s["id"])
                            st.rerun()
    else:
        st.info("No schedules set up yet.")
    if st.session_state.get("admin"):
        with st.expander("➕ Add Schedule"):
            with st.form(f"sched_form_{program}"):
                s_name = st.text_input("Schedule name *", placeholder="e.g. Weekly JP Team Meeting")
                sc1, sc2, sc3 = st.columns(3)
                with sc1: s_rec  = st.selectbox("Recurrence", RECURRENCE_TYPES)
                with sc2: s_day  = st.selectbox("Day of week", DAYS_OF_WEEK)
                with sc3: s_time = st.text_input("Time", placeholder="e.g. 9:00am")
                s_cal  = st.checkbox("Show in Calendar")
                s_bull = st.checkbox("Show in Bulletin")
                s_notes = st.text_area("Notes (optional)", height=60)
                if st.form_submit_button("Add Schedule"):
                    if s_name.strip():
                        insert("tm_schedules", {
                            "program": program, "schedule_name": s_name.strip(),
                            "recurrence_type": s_rec, "day_of_week": s_day,
                            "meeting_time": s_time.strip(),
                            "show_in_calendar": s_cal, "show_in_bulletin": s_bull,
                            "notes": s_notes.strip(),
                        })
                        st.success("Schedule added!")
                        st.rerun()
                    else:
                        st.warning("Please enter a schedule name.")


def render_agenda(program):
    is_staff = (program == "STAFF")
    st.subheader("📋 Agenda")

    if is_staff:
        # ── DfE Meeting Structure — Chair's Running Sheet ──────────────────
        # Load schedules for chair/minutes taker
        schedules = fetch("tm_schedules", {"program": "STAFF"}, "created_at")
        chair_name = schedules[0].get("chair","—") if schedules and schedules[0].get("chair") else "—"
        minutes_name = schedules[0].get("minutes_taker","—") if schedules and schedules[0].get("minutes_taker") else "—"

        # Load agenda items
        items = fetch("tm_agenda_items", {"program": program}, "created_at")
        open_items   = [i for i in items if i.get("status","open") != "closed"]
        closed_items = [i for i in items if i.get("status","open") == "closed"]

        st.markdown("""
        <div style="background:linear-gradient(135deg,#1e6f75,#0f4f54);color:white;border-radius:10px;padding:1rem 1.5rem;margin-bottom:1rem;">
          <div style="font-size:1rem;font-weight:700;margin-bottom:0.25rem;">📋 Chair's Running Sheet — DfE Meeting Structure</div>
          <div style="font-size:0.8rem;opacity:0.8;">Cowandilla Learning Centre · LBU Staff Meeting</div>
        </div>
        """, unsafe_allow_html=True)

        def agenda_section(num, title, icon, content_html, color="#1e293b"):
            st.markdown(f"""
            <div style="border:1.5px solid #e2e8f0;border-left:5px solid {color};border-radius:8px;padding:0.85rem 1rem;margin-bottom:0.75rem;background:white;">
              <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">
                <span style="background:{color};color:white;font-weight:700;font-size:0.75rem;padding:0.15rem 0.5rem;border-radius:20px;">Item {num}</span>
                <span style="font-size:1rem;">{icon}</span>
                <span style="font-weight:700;color:{color};font-size:0.95rem;">{title}</span>
              </div>
              <div style="font-size:0.85rem;color:#475569;padding-left:0.25rem;">{content_html}</div>
            </div>
            """, unsafe_allow_html=True)

        # Item 1 — Welcome
        agenda_section(1, "Welcome", "👋",
            f"Chair <strong>{chair_name}</strong> opens the meeting and welcomes all staff.",
            color="#1e6f75")

        # Item 2 — Acknowledgement of Chair and Minute Taker
        agenda_section(2, "Acknowledgement of Chair & Minute Taker", "📌",
            f"<strong>Chair:</strong> {chair_name}<br><strong>Minute Taker:</strong> {minutes_name}",
            color="#1a4d8c")

        # Item 3 — Apologies
        agenda_section(3, "Apologies", "🙏",
            "Chair calls for apologies. Minute taker records names of staff unable to attend.",
            color="#92400e")

        # Item 4 — Confirmation of Previous Minutes
        agenda_section(4, "Confirmation of Previous Minutes", "✅",
            "Chair asks if previous minutes are a true and accurate record. Moved and seconded.",
            color="#065f46")

        # Item 5 — Business Arising from Previous Minutes
        agenda_section(5, "Business Arising from Previous Minutes", "🔁",
            "Review of actions from previous meeting. Staff report on progress.",
            color="#6d28d9")

        # Items 6+ — Agenda items from staff
        if open_items:
            for idx_i, item in enumerate(open_items):
                item_num = 6 + idx_i
                desc_html = f"<br><em style='color:#64748b;'>{item['description']}</em>" if item.get("description") else ""
                submitted = f"<br><span style='font-size:0.78rem;color:#94a3b8;'>Submitted by {item.get('submitted_by','—')}</span>"
                c1, c2 = st.columns([5, 1])
                with c1:
                    agenda_section(item_num, item['title'], "📌",
                        f"{desc_html}{submitted}", color="#1e6f75")
                with c2:
                    st.write("")
                    st.write("")
                    if st.session_state.get("admin"):
                        if st.button("✅ Close", key=f"close_agenda_{item['id']}"):
                            update_row("tm_agenda_items", item["id"], {"status": "closed"})
                            st.rerun()
                        if st.button("🗑️", key=f"del_agenda_{item['id']}"):
                            delete_row("tm_agenda_items", item["id"])
                            st.rerun()
        else:
            st.info("No additional agenda items submitted yet. Staff can add items below.")

        # Standing item — Other Business
        agenda_section(6 + len(open_items), "General Business / Other Business", "💬",
            "Chair invites any other matters not previously listed. Brief discussion only.",
            color="#475569")

        # Standing item — Next Meeting
        agenda_section(7 + len(open_items), "Next Meeting", "📅",
            "Chair confirms date, time and location of next meeting.",
            color="#475569")

        # Standing item — Close
        agenda_section(8 + len(open_items), "Close of Meeting", "🔔",
            "Chair formally closes the meeting and thanks staff for their attendance.",
            color="#1e6f75")

        if closed_items:
            with st.expander(f"✅ Closed agenda items ({len(closed_items)})"):
                for item in closed_items:
                    st.markdown(f"~~{item['title']}~~ — {item.get('submitted_by','—')}")

    else:
        # Standard agenda for JP/PY/SY/ADMIN
        items = fetch("tm_agenda_items", {"program": program}, "created_at")
        open_items   = [i for i in items if i.get("status","open") != "closed"]
        closed_items = [i for i in items if i.get("status","open") == "closed"]
        if open_items:
            for item in open_items:
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"📌 **{item['title']}**")
                    if item.get("description"):
                        st.caption(item["description"])
                    st.caption(f"Submitted by {item.get('submitted_by','—')}  ·  {str(item.get('created_at',''))[:10]}")
                with c2:
                    if st.session_state.get("admin"):
                        if st.button("✅ Close", key=f"close_agenda_{item['id']}"):
                            update_row("tm_agenda_items", item["id"], {"status": "closed"})
                            st.rerun()
                        if st.button("🗑️", key=f"del_agenda_{item['id']}"):
                            delete_row("tm_agenda_items", item["id"])
                            st.rerun()
                st.divider()
        else:
            st.info("No open agenda items.")
        if closed_items:
            with st.expander(f"✅ Closed items ({len(closed_items)})"):
                for item in closed_items:
                    st.markdown(f"~~{item['title']}~~ — {item.get('submitted_by','—')}")

    with st.expander("➕ Submit an Agenda Item"):
        with st.form(f"agenda_form_{program}"):
            a_title = st.text_input("Item title *")
            a_desc  = st.text_area("Description (optional)", height=80)
            a_by    = st.text_input("Your name", value=get_staff_name())
            if st.form_submit_button("Submit"):
                if a_title.strip():
                    insert("tm_agenda_items", {
                        "program": program, "title": a_title.strip(),
                        "description": a_desc.strip(),
                        "submitted_by": a_by.strip(), "status": "open",
                    })
                    st.success("Agenda item submitted!")
                    st.rerun()
                else:
                    st.warning("Please enter a title.")


def render_minutes(program, week_range=None):
    prog_colours = {
        "JP": "#2d7d4f", "PY": "#1a4d8c", "SY": "#7c3aed",
        "STAFF": "#1e6f75", "ADMIN": "#92400e"
    }
    accent   = prog_colours.get(program, "#1e293b")
    is_staff = (program == "STAFF")

    if week_range:
        monday, sunday = week_range
        week_str = f"{monday.strftime('%-d %b')} – {sunday.strftime('%-d %b %Y')}"
        st.markdown(f"""
        <div style="background:#e8edf3;border:1px solid #b8cfe8;border-radius:8px;
                    padding:10px 16px;margin-bottom:14px;font-size:13px;color:#1a2e44;">
          🔗 <strong>Linked from Digital Staff Meeting</strong> — week of {week_str}
        </div>""", unsafe_allow_html=True)

    minutes_list = fetch("tm_minutes", {"program": program}, "meeting_date")

    if minutes_list:
        for m in minutes_list:
            auto_expand = False
            if week_range:
                try:
                    md = datetime.date.fromisoformat(m["meeting_date"])
                    auto_expand = week_range[0] <= md <= week_range[1]
                except Exception:
                    pass

            label = f"📄  {m.get('meeting_date','')}  —  {m.get('title','Untitled')}"
            with st.expander(label, expanded=auto_expand):
                st.markdown(f"""
                <div style="background:{accent};border-radius:8px;padding:10px 16px;
                            margin-bottom:12px;display:flex;gap:2rem;flex-wrap:wrap;">
                  <span style="color:white;font-size:13px;"><strong>Chair:</strong>&nbsp;{m.get('chair','—') or '—'}</span>
                  <span style="color:white;font-size:13px;"><strong>Location:</strong>&nbsp;{m.get('location','—') or '—'}</span>
                  <span style="color:white;font-size:13px;"><strong>Date:</strong>&nbsp;{m.get('meeting_date','—')}</span>
                </div>""", unsafe_allow_html=True)

                present_raw   = m.get("attendees", "") or ""
                apologies_raw = m.get("apologies", "") or ""
                present_list   = [n.strip() for n in present_raw.split(",")   if n.strip()]
                apologies_list = [n.strip() for n in apologies_raw.split(",") if n.strip()]

                if present_list or apologies_list:
                    st.markdown("""
                    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
                                padding:10px 16px;margin-bottom:12px;">
                      <strong style="font-size:13px;">🙋 Attendance</strong>
                    </div>""", unsafe_allow_html=True)
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        st.markdown("**✅ Present**")
                        st.markdown("\n".join(f"- {n}" for n in present_list) if present_list else "_None recorded_")
                    with ac2:
                        st.markdown("**⚠️ Apologies**")
                        st.markdown("\n".join(f"- {n}" for n in apologies_list) if apologies_list else "_None_")

                if is_staff:
                    st.markdown("""
                    <div style="background:#dbeafe;border-left:5px solid #1a4d8c;
                                border-radius:0 8px 8px 0;padding:10px 16px;margin:14px 0 8px;">
                      <strong style="color:#1a4d8c;font-size:14px;">💻 Part 1 — Digital Staff Meeting</strong>
                    </div>""", unsafe_allow_html=True)
                    digital_summary = (m.get("digital_summary") or "").strip()
                    if digital_summary:
                        st.markdown(digital_summary)
                    else:
                        st.caption("_No digital meeting summary recorded._")
                    st.markdown("**Items raised — viewed & actioned:**")
                    try:
                        items = json.loads(m.get("digital_items") or "[]")
                    except Exception:
                        items = []
                    if items:
                        import pandas as pd
                        df = pd.DataFrame(items)
                        df.columns = [c.replace("_", " ").title() for c in df.columns]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.caption("_No items recorded._")
                    st.markdown("""
                    <div style="background:#d1fae5;border-left:5px solid #2d7d4f;
                                border-radius:0 8px 8px 0;padding:10px 16px;margin:14px 0 8px;">
                      <strong style="color:#2d7d4f;font-size:14px;">👥 Part 2 — Face-to-Face Meeting</strong>
                    </div>""", unsafe_allow_html=True)
                    ff = (m.get("face_to_face_content") or m.get("content") or "").strip()
                    if ff:
                        st.markdown(ff)
                    else:
                        st.caption("_No face-to-face minutes recorded._")
                else:
                    content = (m.get("content") or m.get("face_to_face_content") or "").strip()
                    if content:
                        st.markdown(content)
                    else:
                        st.caption("_No minutes content recorded._")

                action_text = (m.get("action_summary") or "").strip()
                if action_text:
                    st.markdown("""
                    <div style="background:#f5f3ff;border-left:5px solid #5b21b6;
                                border-radius:0 8px 8px 0;padding:8px 14px;margin:12px 0 4px;">
                      <strong style="color:#5b21b6;">✅ Action Items</strong>
                    </div>""", unsafe_allow_html=True)
                    lines = [l.strip() for l in action_text.splitlines() if l.strip()]
                    for line in lines:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 2:
                            st.markdown(f"🔲 **{parts[0]}** — {parts[1]}" + (f" _(due {parts[2]})_" if len(parts) > 2 else ""))
                        else:
                            st.markdown(f"🔲 {line}")

                st.markdown("")
                if is_staff:
                    docx_bytes = generate_combined_docx(m)
                else:
                    docx_bytes = generate_team_docx(m, program)

                safe_title = (m.get("title") or "minutes").replace(" ", "_")
                st.download_button(
                    label     = "📥 Download Word Document",
                    data      = docx_bytes,
                    file_name = f"{safe_title}_{m.get('meeting_date','')}.docx",
                    mime      = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key       = f"dl_{m['id']}",
                    type      = "primary",
                )

                if st.session_state.get("admin"):
                    st.divider()
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        if st.button("✏️ Edit", key=f"edit_min_{m['id']}"):
                            st.session_state[f"editing_min_{m['id']}"] = True
                    with ec2:
                        if st.button("🗑️ Delete", key=f"del_min_{m['id']}"):
                            delete_row("tm_minutes", m["id"])
                            st.rerun()
                    if st.session_state.get(f"editing_min_{m['id']}"):
                        with st.form(f"edit_min_form_{m['id']}"):
                            ec1, ec2 = st.columns([3, 1])
                            with ec1: etitle = st.text_input("Title", value=m.get("title",""))
                            with ec2: edate  = st.date_input("Date", value=datetime.date.fromisoformat(m["meeting_date"]) if m.get("meeting_date") else datetime.date.today())
                            ec3, ec4, ec5 = st.columns(3)
                            with ec3: echair = st.text_input("Chair", value=m.get("chair",""))
                            with ec4: eloc   = st.text_input("Location", value=m.get("location",""))
                            with ec5: pass
                            eatt  = st.text_input("Present (comma-separated)", value=m.get("attendees",""))
                            eapol = st.text_input("Apologies (comma-separated)", value=m.get("apologies",""))
                            if is_staff:
                                edigital = st.text_area("Digital meeting summary", value=m.get("digital_summary",""), height=120)
                                eitems   = st.text_area("Digital items (Item|Raised By|Actioned By|Status)", value="\n".join(
                                    f"{i.get('item','')}|{i.get('raised_by','')}|{i.get('actioned_by','')}|{i.get('status','')}"
                                    for i in json.loads(m.get("digital_items") or "[]")
                                ), height=100)
                                eff      = st.text_area("Face-to-face minutes", value=m.get("face_to_face_content",""), height=200)
                                econtent = ""
                            else:
                                edigital = ""; eitems = ""; eff = ""
                                econtent = st.text_area("Minutes", value=m.get("content",""), height=280)
                            eactions = st.text_area("Action items (Action|Assigned To|Due)", value=m.get("action_summary",""))
                            if st.form_submit_button("💾 Save Changes"):
                                parsed_items = []
                                if is_staff:
                                    for line in eitems.splitlines():
                                        parts = [p.strip() for p in line.split("|")]
                                        if parts and parts[0]:
                                            parsed_items.append({
                                                "item": parts[0], "raised_by": parts[1] if len(parts)>1 else "",
                                                "actioned_by": parts[2] if len(parts)>2 else "",
                                                "status": parts[3] if len(parts)>3 else "Noted"
                                            })
                                update_row("tm_minutes", m["id"], {
                                    "title": etitle, "meeting_date": str(edate),
                                    "chair": echair, "location": eloc,
                                    "attendees": eatt, "apologies": eapol,
                                    "digital_summary": edigital,
                                    "digital_items": json.dumps(parsed_items),
                                    "face_to_face_content": eff,
                                    "content": econtent,
                                    "action_summary": eactions
                                })
                                del st.session_state[f"editing_min_{m['id']}"]
                                st.rerun()
    else:
        st.info("No minutes recorded yet. Use the form below to add the first entry.")

    if not st.session_state.get("admin"):
        return
    st.divider()
    if is_staff:
        _render_new_staff_minutes()
    else:
        _render_new_team_minutes(program)


def _render_new_staff_minutes():
    st.subheader("✍️ Record Combined Staff Meeting Minutes")
    
    # ── Step 1: Load DSM content (outside form so it shows immediately) ────────
    _dsm_summary = ""
    _dsm_week_label = ""
    _dsm_items_raw = ""
    _dsm_loaded = False
    try:
        _dsm_res = supabase.table("weekly_editions").select("*").eq("status","published").order("week_start", desc=True).limit(1).execute()
        if _dsm_res.data:
            _dsm_ed = _dsm_res.data[0]
            _dsm_week_label = _dsm_ed.get("week_label", "Digital Staff Meeting")
            _notices_res = supabase.table("notices").select("*").eq("edition_id", _dsm_ed["id"]).order("created_at").execute()
            _notices = _notices_res.data or []
            if _notices:
                _dsm_summary = "\n\n".join([
                    f"**{n.get('section','General')}**\n{n.get('content','')}"
                    for n in _notices if n.get("content","").strip()
                ])
                _dsm_items_raw = "\n".join([
                    f"{n.get('section','Item')}|Digital Staff Meeting|All Staff|Noted"
                    for n in _notices if n.get("content","").strip()
                ])
                _dsm_loaded = True
    except Exception as _e:
        st.caption(f"Could not auto-load DSM: {_e}")

    # Show DSM preview
    if _dsm_loaded:
        st.markdown(f"""
        <div style="background:#dbeafe;border-left:5px solid #1a4d8c;border-radius:0 8px 8px 0;
                    padding:10px 16px;margin-bottom:16px;">
          <strong style="color:#1a4d8c;">💻 Part 1 — Digital Staff Meeting auto-loaded:</strong>
          <span style="font-size:0.85rem;color:#1a4d8c;margin-left:8px;">{_dsm_week_label}</span>
          <div style="font-size:0.78rem;color:#374151;margin-top:4px;">
            {len([n for n in (_dsm_summary or "").split(chr(10)+chr(10)) if n.strip()])} item(s) loaded and will appear as Part 1 of the minutes.
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#fef3c7;border-left:5px solid #d97706;border-radius:0 8px 8px 0;
                    padding:10px 16px;margin-bottom:16px;font-size:13px;">
          ⚠️ No published Digital Staff Meeting found. Part 1 will be blank — you can fill it in manually below.
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;
                padding:10px 16px;margin-bottom:16px;font-size:13px;color:#14532d;">
      🎙️ <strong>How to use:</strong> After your face-to-face meeting, paste the recording transcript 
      into the field below. AI will combine Part 1 (Digital Staff Meeting) with the structured 
      face-to-face minutes into a single professional record.
    </div>""", unsafe_allow_html=True)

    with st.form("new_staff_minutes_form", clear_on_submit=True):
        st.markdown("##### 📋 Meeting Details")
        dc1, dc2, dc3 = st.columns([3, 2, 2])
        with dc1: m_title    = st.text_input("Meeting title *", placeholder="e.g. Staff Meeting — T1 W8")
        with dc2: m_date     = st.date_input("Date *", value=datetime.date.today())
        with dc3: m_chair    = st.text_input("Chair", value=get_staff_name())
        m_location = st.text_input("Location / format", placeholder="e.g. Staff Room")

        st.markdown("##### 🙋 Attendance")
        ac1, ac2 = st.columns(2)
        with ac1:
            m_attendees = st.text_area("Present — one name per line", height=100)
        with ac2:
            m_apologies = st.text_area("Apologies — one name per line", height=100)

        st.markdown("##### 💻 Part 1 — Digital Staff Meeting")
        st.caption("Auto-loaded from the most recently published Digital Staff Meeting. Edit if needed.")
        m_digital_summary = st.text_area("Digital meeting summary", height=90,
            value=_dsm_summary,
            placeholder="Will be auto-loaded from the published Digital Staff Meeting.")
        st.markdown("**Items table** (one per line: `Item | Raised By | Actioned By | Status`)")
        m_digital_items_raw = st.text_area("Digital items", height=100,
            value=_dsm_items_raw,
            placeholder="Timetable update Week 8 | Candice Cooper | All staff | Noted")

        st.markdown("##### 🎙️ Part 2 — Face-to-Face Meeting Transcript")
        st.markdown("""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
                    padding:10px 14px;font-size:12px;color:#475569;margin-bottom:8px;">
          <strong>Instructions for minute taker:</strong><br>
          1. Record your face-to-face meeting using your phone or recording device<br>
          2. Use a transcription tool (e.g. Otter.ai, Teams transcript, or your phone's speech-to-text)<br>
          3. Paste the full transcript into the field below<br>
          4. Click <strong>✨ Process with AI</strong> — the AI will structure it into professional minutes
        </div>""", unsafe_allow_html=True)
        m_ff_content = st.text_area(
            "Paste face-to-face meeting transcript here",
            height=300,
            placeholder="Paste the full transcript here. Include everything — the AI will extract what's relevant and structure it correctly...")

        st.markdown("##### ✅ Action Items (optional — AI will also extract these)")
        st.caption("Add any actions the AI might miss. One per line: `Action | Assigned To | Due`")
        m_actions = st.text_area("Additional action items", height=60,
            placeholder="Update student profiles | Candice Cooper | Week 9")

        st.markdown("---")
        st.markdown("##### ✔️ Confirmation")
        m_confirmed_by = st.text_input("Your name (confirming minutes are accurate) *",
            value=get_staff_name(),
            placeholder="e.g. Sarah Jones")
        m_confirmed = st.checkbox(
            "I confirm that these minutes accurately represent what was discussed in this meeting.",
            value=False)

        submitted = st.form_submit_button("✨ Process with AI & Save Minutes", type="primary",
                                          use_container_width=True)

        if submitted:
            if not m_title.strip():
                st.warning("Please enter a meeting title.")
            elif not m_confirmed:
                st.warning("Please confirm the minutes are accurate before saving.")
            elif not m_confirmed_by.strip():
                st.warning("Please enter your name for confirmation.")
            else:
                attendees_str = ", ".join(n.strip() for n in m_attendees.replace("\n",",").split(",") if n.strip())
                apologies_str = ", ".join(n.strip() for n in m_apologies.replace("\n",",").split(",") if n.strip())
                digital_items = []
                for line in m_digital_items_raw.splitlines():
                    parts = [p.strip() for p in line.split("|")]
                    if parts and parts[0]:
                        digital_items.append({
                            "item": parts[0],
                            "raised_by": parts[1] if len(parts) > 1 else "",
                            "actioned_by": parts[2] if len(parts) > 2 else "",
                            "status": parts[3] if len(parts) > 3 else "Noted",
                        })
                final_ff = m_ff_content.strip()
                if final_ff:
                    with st.spinner("✨ AI is processing your transcript into structured minutes…"):
                        final_ff = improve_with_ai(final_ff, "STAFF", str(m_date), dsm_summary=m_digital_summary.strip())
                else:
                    final_ff = "_No face-to-face transcript provided._"

                confirmation_note = f"\n\n---\n*Minutes confirmed by {m_confirmed_by.strip()} on {datetime.date.today().strftime('%-d %B %Y')}.*"
                final_ff = final_ff + confirmation_note

                insert("tm_minutes", {
                    "program": "STAFF",
                    "title": m_title.strip(),
                    "meeting_date": str(m_date),
                    "chair": m_chair.strip(),
                    "location": m_location.strip(),
                    "attendees": attendees_str,
                    "apologies": apologies_str,
                    "digital_summary": m_digital_summary.strip(),
                    "digital_items": json.dumps(digital_items),
                    "face_to_face_content": final_ff,
                    "content": "",
                    "action_summary": m_actions.strip(),
                })
                st.success("✅ Combined staff meeting minutes saved!")
                st.rerun()


# ── Meeting type templates ────────────────────────────────────────────────────
STUDENT_LENS_TEMPLATE = """## ⬤ WEEK A — STUDENT LENS
Individual Progress · SMARTAR Goals · Evidence

---

### 0–10 min | TEAM CHECK-IN — Regulation Before Reaction
What do we need to know to support students effectively today?


---

### 10–25 min | STUDENT CONCERNS — Structured Problem Solving
*Facilitator prompt: Push for function-based thinking, not description.*

| Student | Concern / Behaviour | Hypothesis (Why?) | Strategy to Try | Who | By When |
|---------|--------------------|--------------------|-----------------|-----|---------|
|         |                    |                    |                 |     |         |
|         |                    |                    |                 |     |         |
|         |                    |                    |                 |     |         |
|         |                    |                    |                 |     |         |

---

### 25–40 min | SMARTAR GOAL SPOTLIGHT — 4 Students
*Rule: No update without evidence. What data or artefact supports this?*

| Student | Goal Area | Current Level / Evidence | Next Adjustment | Responsible |
|---------|-----------|--------------------------|-----------------|-------------|
|         |           |                          |                 |             |
|         |           |                          |                 |             |
|         |           |                          |                 |             |
|         |           |                          |                 |             |

---

### 40–45 min | REPORTS / TAC / TRANSITIONS
Upcoming reports due · TAC meetings · Review or transition planning


---

### ⭐ MEETING CLOSE — Before You Leave, Name:
1. What is the single most important thing we agreed on today?

2. What will look DIFFERENT in practice by next week?

3. Carry forward to next meeting:

---

### ACTIONS
| Action | Who | By When | ✓ Check Next Meeting |
|--------|-----|---------|----------------------|
|        |     |         |                      |
|        |     |         |                      |
|        |     |         |                      |

"""

SYSTEM_LENS_TEMPLATE = """## ⬤ WEEK B — SYSTEM LENS
CLC Priorities · Innovation Fidelity · Staff Alignment · Artefacts

---

### 0–10 min | TEAM CHECK-IN
Quick updates impacting program delivery


---

### 10–30 min | CLC PRIORITY FOCUS — Implementation Fidelity
*Align to: Implementation Plan · PDP Focus Areas · LBU Priorities*

| Priority Area | What's Working | Gap Identified | Adjustment | Evidence to Collect | Who |
|---------------|---------------|----------------|------------|---------------------|-----|
|               |               |                |            |                     |     |
|               |               |                |            |                     |     |
|               |               |                |            |                     |     |

---

### 30–45 min | SMARTAR GOAL SPOTLIGHT — 4 Students

| Student | Goal Area | Current Level / Evidence | Next Adjustment | Responsible |
|---------|-----------|--------------------------|-----------------|-------------|
|         |           |                          |                 |             |
|         |           |                          |                 |             |
|         |           |                          |                 |             |
|         |           |                          |                 |             |

---

### ⭐ MEETING CLOSE — Before You Leave, Name:
1. What is the single most important thing we agreed on today?

2. What will look DIFFERENT in practice by next week?

3. Carry forward to next meeting:

---

### ACTIONS
| Action | Who | By When | ✓ Check Next Meeting |
|--------|-----|---------|----------------------|
|        |     |         |                      |
|        |     |         |                      |
|        |     |         |                      |

"""

ADHOC_MINUTES_TEMPLATE = """## Meeting Minutes

### Purpose / Agenda
What is this meeting about?

---

### Discussion
Key points discussed:


---

### Decisions Made


---

### ⭐ MEETING CLOSE
1. What is the single most important thing we agreed on today?

2. What will look DIFFERENT in practice?

---

### ACTIONS
| Action | Who | By When |
|--------|-----|---------|
|        |     |         |
|        |     |         |

"""

def _render_new_team_minutes(program):
    st.subheader("✍️ Record New Minutes")

    # Meeting type selector
    meeting_type = st.radio(
        "Meeting type",
        ["🔍 Week A — Student Lens", "⚙️ Week B — System Lens", "📋 Ad-hoc / Additional Meeting"],
        horizontal=True,
        key=f"meeting_type_{program}",
    )
    is_student_lens = "Student" in meeting_type
    is_system_lens = "System" in meeting_type
    is_adhoc = "Ad-hoc" in meeting_type

    if is_student_lens:
        st.markdown("""
        <div style="background:#dbeafe;border-left:4px solid #1a4d8c;border-radius:0 8px 8px 0;
                    padding:8px 14px;margin-bottom:12px;font-size:13px;color:#1a4d8c;">
          🔍 <strong>Week A — Student Lens</strong> · Individual Progress · SMARTAR Goals · Evidence
        </div>""", unsafe_allow_html=True)
        template = STUDENT_LENS_TEMPLATE
        title_placeholder = f"{PROGRAMS[program]['label']} Student Lens — T1 W4"
    elif is_system_lens:
        st.markdown("""
        <div style="background:#f0fdf4;border-left:4px solid #2d7d4f;border-radius:0 8px 8px 0;
                    padding:8px 14px;margin-bottom:12px;font-size:13px;color:#2d7d4f;">
          ⚙️ <strong>Week B — System Lens</strong> · CLC Priorities · Innovation Fidelity · Staff Alignment
        </div>""", unsafe_allow_html=True)
        template = SYSTEM_LENS_TEMPLATE
        title_placeholder = f"{PROGRAMS[program]['label']} System Lens — T1 W4"
    else:
        st.markdown("""
        <div style="background:#fef3c7;border-left:4px solid #d97706;border-radius:0 8px 8px 0;
                    padding:8px 14px;margin-bottom:12px;font-size:13px;color:#92400e;">
          📋 <strong>Ad-hoc / Additional Meeting</strong> · Record minutes for any unscheduled or additional team meeting.
          Use the template or drop in a transcript for AI formatting.
        </div>""", unsafe_allow_html=True)
        template = ADHOC_MINUTES_TEMPLATE
        title_placeholder = f"{PROGRAMS[program]['label']} Additional Meeting"

    # Input method
    ff_method = st.radio("Minutes input method",
        ["📝 Use structured template", "🎙️ Drop transcript — AI will structure it"],
        horizontal=True, key=f"ff_method_{program}")
    do_ai = "🎙️" in ff_method

    with st.form(f"new_minutes_form_{program}", clear_on_submit=True):
        st.markdown("##### 📋 Meeting Details")
        dc1, dc2, dc3 = st.columns([3, 2, 2])
        with dc1: m_title    = st.text_input("Meeting title *", placeholder=title_placeholder)
        with dc2: m_date     = st.date_input("Date *", value=datetime.date.today())
        with dc3: m_chair    = st.text_input("Chair", value=get_staff_name())
        m_location = st.text_input("Location / format", placeholder="e.g. Room 3 / Teams")

        st.markdown("##### 🙋 Attendance")
        ac1, ac2 = st.columns(2)
        with ac1: m_attendees = st.text_area("Present — one name per line", height=90)
        with ac2: m_apologies = st.text_area("Apologies — one name per line", height=90)

        schedules  = fetch("tm_schedules", {"program": program})
        sched_opts = {s["schedule_name"]: s["id"] for s in schedules}
        sched_opts["General / Unassigned"] = None
        m_sched = st.selectbox("Associated schedule", list(sched_opts.keys()))

        st.markdown("##### 📝 Minutes")
        if do_ai:
            st.caption("Paste transcript or rough notes — AI will structure into the correct format.")
            m_content = st.text_area("Paste transcript here", height=280,
                placeholder="Paste your meeting recording transcript or rough notes here...")
        else:
            st.caption("Pre-filled with the structured template. Edit as you go.")
            m_content = st.text_area("Minutes", height=400, value=template)

        st.markdown("##### ✅ Action Items")
        st.caption("One per line: `Action | Assigned To | Due date`")
        m_actions = st.text_area("Action items", height=80,
            placeholder="Update student profiles | Jane Smith | Week 5")

        submitted = st.form_submit_button(
            "✨ Improve with AI & Save" if do_ai else "💾 Save Minutes", type="primary")

        if submitted:
            if not m_title.strip():
                st.warning("Please enter a meeting title.")
            else:
                attendees_str = ", ".join(n.strip() for n in m_attendees.replace("\n",",").split(",") if n.strip())
                apologies_str = ", ".join(n.strip() for n in m_apologies.replace("\n",",").split(",") if n.strip())
                final_content = m_content.strip()
                if do_ai and final_content:
                    # Add meeting type context to AI prompt
                    if is_student_lens:
                        lens_type = "Week A Student Lens"
                    elif is_system_lens:
                        lens_type = "Week B System Lens"
                    else:
                        lens_type = "Ad-hoc"
                    lens_context = f"This is a {lens_type} meeting for {PROGRAMS[program]['label']} program at Cowandilla Learning Centre LBU."
                    with st.spinner("AI is structuring your minutes…"):
                        final_content = improve_with_ai(
                            f"{lens_context}\n\n{final_content}", program, str(m_date))
                # Prepend meeting type badge
                if is_student_lens: type_badge = "🔍 Week A — Student Lens"
                elif is_system_lens: type_badge = "⚙️ Week B — System Lens"
                else: type_badge = "📋 Ad-hoc Meeting"
                final_content = f"**Meeting Type: {type_badge}**\n\n" + final_content
                insert("tm_minutes", {
                    "program": program, "schedule_id": sched_opts.get(m_sched),
                    "title": m_title.strip(), "meeting_date": str(m_date),
                    "chair": m_chair.strip(), "location": m_location.strip(),
                    "attendees": attendees_str, "apologies": apologies_str,
                    "content": final_content, "action_summary": m_actions.strip(),
                    "digital_summary": "", "digital_items": "[]", "face_to_face_content": "",
                })
                st.success("✅ Minutes saved!")
                st.rerun()


def render_actions(program):
    st.subheader("✅ Action Items")
    actions = fetch("tm_actions", {"program": program}, "due_date")
    open_actions = [a for a in actions if a.get("status") != "completed"]
    completed    = [a for a in actions if a.get("status") == "completed"]
    if open_actions:
        st.markdown("**Open Actions**")
        for a in open_actions:
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                st.markdown(f"🔲 **{a['action']}**")
                st.caption(f"Assigned to: {a.get('assigned_to','—')} · Due: {a.get('due_date','—')}")
            with c2:
                if st.session_state.get("admin"):
                    if st.button("✅ Mark complete", key=f"complete_{a['id']}"):
                        update_row("tm_actions", a["id"], {"status": "completed"})
                        st.rerun()
            with c3:
                if st.session_state.get("admin"):
                    if st.button("🗑️", key=f"del_action_{a['id']}"):
                        delete_row("tm_actions", a["id"])
                        st.rerun()
            st.divider()
    else:
        st.info("No open action items.")
    if completed:
        with st.expander(f"✅ Completed ({len(completed)})"):
            for a in completed:
                st.markdown(f"~~{a['action']}~~ — {a.get('assigned_to','—')}")
    if st.session_state.get("admin"):
        with st.expander("➕ Add Action Item"):
            with st.form("action_form"):
                a_text = st.text_input("Action")
                a_col1, a_col2 = st.columns(2)
                with a_col1: a_assigned = st.text_input("Assigned to")
                with a_col2: a_due = st.date_input("Due date", value=datetime.date.today() + datetime.timedelta(weeks=2))
                a_notes = st.text_input("Notes (optional)")
                if st.form_submit_button("Add"):
                    if a_text.strip():
                        insert("tm_actions", {
                            "program": program, "action": a_text.strip(),
                            "assigned_to": a_assigned.strip(), "due_date": str(a_due),
                            "notes": a_notes.strip(), "status": "open"
                        })
                        st.success("Action added!")
                        st.rerun()


def render_attendance(program):
    st.subheader("🙋 Attendance")
    schedules = fetch("tm_schedules", {"program": program})
    if not schedules:
        st.info("Add a meeting schedule first.")
        return
    sched_opts = {s["schedule_name"]: s["id"] for s in schedules}
    sel_sched = st.selectbox("Meeting", list(sched_opts.keys()), key="att_sched")
    sel_date  = st.date_input("Meeting date", value=datetime.date.today(), key="att_date")
    existing = supabase.table("tm_attendance").select("*").eq("program", program)\
        .eq("schedule_id", sched_opts[sel_sched]).eq("meeting_date", str(sel_date)).execute().data or []
    if existing:
        st.markdown("**Attendance record:**")
        for att in existing:
            status_icon = "✅" if att["status"] == "present" else "❌"
            st.markdown(f"{status_icon} {att['staff_name']} — {att['status'].title()}")
    else:
        st.info("No attendance recorded for this meeting date yet.")
    if st.session_state.get("admin"):
        with st.expander("📝 Record Attendance"):
            with st.form("attendance_form"):
                names_raw  = st.text_area("Staff names (one per line)")
                status_val = st.selectbox("Status for all entered", ["present", "absent", "apology"])
                if st.form_submit_button("Save"):
                    names = [n.strip() for n in names_raw.splitlines() if n.strip()]
                    for name in names:
                        check = supabase.table("tm_attendance").select("id")\
                            .eq("program", program).eq("schedule_id", sched_opts[sel_sched])\
                            .eq("meeting_date", str(sel_date)).eq("staff_name", name).execute().data
                        if check:
                            update_row("tm_attendance", check[0]["id"], {"status": status_val})
                        else:
                            insert("tm_attendance", {
                                "program": program, "schedule_id": sched_opts[sel_sched],
                                "meeting_date": str(sel_date), "staff_name": name, "status": status_val
                            })
                    st.success(f"Attendance saved for {len(names)} staff member(s).")
                    st.rerun()


def render_documents(program):
    st.subheader("📎 Supporting Documents")
    docs = fetch("tm_documents", {"program": program}, "created_at")
    if docs:
        for d in docs:
            c1, c2 = st.columns([5, 1])
            with c1:
                if d.get("url"):
                    st.markdown(f"📄 [{d['title']}]({d['url']})")
                else:
                    st.markdown(f"📄 **{d['title']}**")
                if d.get("description"):
                    st.caption(d["description"])
                st.caption(f"Added: {d.get('created_at','')[:10]}")
            if st.session_state.get("admin"):
                with c2:
                    if st.button("🗑️", key=f"del_doc_{d['id']}"):
                        delete_row("tm_documents", d["id"])
                        st.rerun()
            st.divider()
    else:
        st.info("No documents added yet.")
    if st.session_state.get("admin"):
        with st.expander("➕ Add Document Link"):
            with st.form("doc_form"):
                d_title = st.text_input("Title")
                d_url   = st.text_input("URL (optional)")
                d_desc  = st.text_area("Description (optional)")
                if st.form_submit_button("Add"):
                    if d_title.strip():
                        insert("tm_documents", {
                            "program": program, "title": d_title.strip(),
                            "url": d_url.strip(), "description": d_desc.strip()
                        })
                        st.success("Document added!")
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def _render_adhoc_meeting(program, last_actions):
    """Ad-hoc / additional meeting form with transcript → AI minutes."""
    import json as _json

    prog_label = PROGRAMS[program]["label"]

    st.markdown("#### 📋 Meeting Details")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: ah_date      = st.date_input("Date", value=datetime.date.today(), key=f"ah_date_{program}")
    with mc2: ah_purpose   = st.text_input("Meeting purpose / title *", key=f"ah_purpose_{program}",
                                            placeholder="e.g. Emergency planning meeting")
    with mc3: ah_facilitator = st.text_input("Facilitator", value=get_staff_name(), key=f"ah_fac_{program}")
    ah_attendees = st.text_input("Attendees", placeholder="Names separated by commas", key=f"ah_att_{program}")

    st.markdown("---")

    # Input method
    input_method = st.radio(
        "How would you like to record minutes?",
        ["📝 Type / fill in template", "🎙️ Paste transcript — AI will format"],
        horizontal=True, key=f"ah_method_{program}")
    use_ai = "🎙️" in input_method

    st.markdown("---")

    if use_ai:
        st.markdown("#### 🎙️ Meeting Transcript")
        st.markdown("""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
            padding:10px 14px;font-size:12px;color:#475569;margin-bottom:8px;">
            <strong>Instructions:</strong><br>
            1. Record your meeting using your phone or a recording tool<br>
            2. Transcribe using Otter.ai, Teams transcript, or phone speech-to-text<br>
            3. Paste the full transcript below — AI will structure it into professional minutes
        </div>""", unsafe_allow_html=True)
        ah_transcript = st.text_area("Paste transcript here", height=300,
            key=f"ah_transcript_{program}",
            placeholder="Paste full transcript here. Include everything — AI will extract what's relevant...")
        ah_content = ""
    else:
        ah_transcript = ""
        st.markdown("#### 📝 Minutes")
        ah_content = st.text_area("Minutes", height=300, key=f"ah_content_{program}",
            value="""## Purpose / Agenda
What is this meeting about?

---

## Discussion
Key points discussed:


---

## Decisions Made


---

## Meeting Close
What is the single most important thing agreed today?

---

## Actions
| Action | Who | By When |
|--------|-----|---------|
|        |     |         |
""")

    st.markdown("---")

    # Actions table
    st.markdown("#### ✅ Actions")
    actions_key = f"ah_actions_{program}"
    if actions_key not in st.session_state:
        carried = [a for a in last_actions if not a.get("done", False)]
        st.session_state[actions_key] = carried if carried else [{"action":"","who":"","by_when":""}]

    ah_actions = st.session_state[actions_key]
    ah_cols = st.columns([4,1,1,0.5])
    for h, label in zip(ah_cols, ["Action","Who","By When",""]):
        h.markdown(f"**{label}**" if label else "")

    for idx, row in enumerate(ah_actions):
        a1,a2,a3,a4 = st.columns([4,1,1,0.5])
        with a1: row["action"]  = st.text_input("Act", value=row.get("action",""),  key=f"ah_act_a_{program}_{idx}", label_visibility="collapsed")
        with a2: row["who"]     = st.text_input("Who", value=row.get("who",""),     key=f"ah_act_w_{program}_{idx}", label_visibility="collapsed")
        with a3: row["by_when"] = st.text_input("By",  value=row.get("by_when",""), key=f"ah_act_by_{program}_{idx}", label_visibility="collapsed")
        with a4:
            if len(ah_actions) > 1:
                if st.button("✕", key=f"ah_act_del_{program}_{idx}"):
                    ah_actions.pop(idx); st.rerun()
    if st.button("➕ Add action", key=f"ah_act_add_{program}"):
        ah_actions.append({"action":"","who":"","by_when":""}); st.rerun()

    st.markdown("---")

    # Confirmation
    ah_confirmed_by = st.text_input("Your name (confirming minutes are accurate)",
        value=get_staff_name(), key=f"ah_confirmed_{program}")
    ah_confirmed = st.checkbox(
        "I confirm these minutes accurately represent what was discussed.",
        key=f"ah_confirm_chk_{program}")

    if st.button("✨ Process & Save Minutes", type="primary", use_container_width=True, key=f"ah_save_{program}"):
        if not ah_purpose.strip():
            st.warning("Please enter a meeting purpose / title.")
        elif not ah_confirmed:
            st.warning("Please tick the confirmation checkbox before saving.")
        elif not ah_confirmed_by.strip():
            st.warning("Please enter your name.")
        else:
            final_content = ""
            if use_ai and ah_transcript.strip():
                with st.spinner("✨ AI is structuring your transcript into minutes…"):
                    prompt = f"""You are a professional minute-taker for Cowandilla Learning Centre (CLC), 
Learning & Behaviour Unit — {prog_label} team. 

Meeting: {ah_purpose.strip()}
Date: {ah_date}
Facilitator: {ah_facilitator.strip()}
Attendees: {ah_attendees.strip()}

Transform this transcript into professional meeting minutes using this structure:

## {ah_purpose.strip()}

### Attendance
{ah_attendees.strip() or "See attendance record"}

### Purpose
{ah_purpose.strip()}

### Discussion
(Extract and summarise key discussion points)

### Decisions Made
(List decisions reached)

### Meeting Close
(Key agreement or next step)

### Actions
| Action | Who | By When |
|--------|-----|---------|
(Extract all actions mentioned)

Rules:
- Professional but warm, accessible language
- Trauma-informed, strengths-based framing
- Preserve ALL factual content — do not fabricate
- Concise — one clear sentence per point unless more detail is essential

Transcript:
{ah_transcript.strip()}"""
                    if GROQ_KEY:
                        client = Groq(api_key=GROQ_KEY)
                        resp = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"user","content":prompt}],
                            max_tokens=2000,
                        )
                        final_content = resp.choices[0].message.content
                    else:
                        final_content = ah_transcript.strip()
            else:
                final_content = ah_content.strip()

            confirmation_note = f"\n\n---\n*Minutes confirmed by {ah_confirmed_by.strip()} on {datetime.date.today().strftime('%-d %B %Y')}.*"
            final_content = final_content + confirmation_note

            try:
                insert("tm_minutes", {
                    "program": program,
                    "schedule_id": None,
                    "title": ah_purpose.strip(),
                    "meeting_date": str(ah_date),
                    "chair": ah_facilitator.strip(),
                    "location": "",
                    "attendees": ah_attendees.strip(),
                    "apologies": "",
                    "content": final_content,
                    "action_summary": "\n".join(
                        f"{a.get('action','')} | {a.get('who','')} | {a.get('by_when','')}"
                        for a in ah_actions if a.get("action","").strip()
                    ),
                    "digital_summary": "",
                    "digital_items": "[]",
                    "face_to_face_content": "",
                })
                st.success("✅ Ad-hoc meeting minutes saved!")
                st.session_state.pop(f"ah_actions_{program}", None)
                st.rerun()
            except Exception as e:
                st.error(f"Could not save: {e}")


def render_program_meeting(program):
    """Structured weekly program meeting — Week A (Student Lens) or Week B (System Lens)."""
    import json as _json

    prog_label = PROGRAMS[program]["label"]
    accent = PROGRAMS[program]["color"]

    # ── Fetch students for this program ──────────────────────────────────────
    @st.cache_data(ttl=120)
    def fetch_students(prog):
        try:
            # Try behaviour Supabase first
            import os
            from supabase import create_client as _cc
            burl = st.secrets.get("BEHAVIOUR_SUPABASE_URL","") or os.environ.get("BEHAVIOUR_SUPABASE_URL","")
            bkey = st.secrets.get("BEHAVIOUR_SUPABASE_KEY","") or os.environ.get("BEHAVIOUR_SUPABASE_KEY","")
            if burl:
                bsb = _cc(burl, bkey)
                res = bsb.table("students").select("id,name,year_level").eq("archived", False).execute()
                if res.data:
                    return [s["name"] for s in res.data]
        except Exception:
            pass
        return []

    student_names = fetch_students(program)

    # ── Detect last meeting week type ─────────────────────────────────────────
    last_records = fetch("tm_program_meetings", {"program": program}, "meeting_date")
    last_week_type = None
    last_actions = []
    if last_records:
        last = last_records[-1]
        last_week_type = last.get("week_type")
        try:
            last_actions = _json.loads(last.get("actions", "[]") or "[]")
        except Exception:
            last_actions = []

    suggested_type = "B" if last_week_type == "A" else "A"

    # ── Week type selector ────────────────────────────────────────────────────
    wt_col1, wt_col2 = st.columns([3, 2])
    with wt_col1:
        week_type = st.radio(
            "Meeting type",
            ["A — Student Lens", "B — System Lens", "📋 Ad-hoc Meeting"],
            index=0 if suggested_type == "A" else 1,
            horizontal=True,
            key=f"pm_wt_{program}",
        )
    with wt_col2:
        if last_week_type:
            st.caption(f"Last scheduled meeting: Week {last_week_type}")

    is_week_a = week_type.startswith("A")
    is_adhoc  = week_type.startswith("📋")

    if is_week_a:
        st.markdown(f"""<div style="background:#dbeafe;border-left:5px solid #1a4d8c;
            border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#1a4d8c;">
            ⬤ <strong>WEEK A — STUDENT LENS</strong> · Individual Progress · SMARTAR Goals · Evidence
        </div>""", unsafe_allow_html=True)
    elif is_adhoc:
        st.markdown(f"""<div style="background:#f3f0ff;border-left:5px solid #6d28d9;
            border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#4c1d95;">
            📋 <strong>AD-HOC / ADDITIONAL MEETING</strong> · Record minutes for any unscheduled or additional team meeting.
            Use the transcript tool to paste a recording and have AI format the minutes.
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="background:#fef3c7;border-left:5px solid #d97706;
            border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#92400e;">
            ⬤ <strong>WEEK B — SYSTEM LENS</strong> · CLC Priorities · Innovation Fidelity · Staff Alignment
        </div>""", unsafe_allow_html=True)

    # ── Ad-hoc meeting — separate flow ───────────────────────────────────────
    if is_adhoc:
        _render_adhoc_meeting(program, last_actions)
        return

    # ── Meeting details ───────────────────────────────────────────────────────
    st.markdown("#### 📋 Meeting Details")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: pm_date = st.date_input("Date", value=datetime.date.today(), key=f"pm_date_{program}")
    with mc2: pm_term = st.text_input("Term", placeholder="T1", key=f"pm_term_{program}")
    with mc3: pm_week = st.number_input("Week #", min_value=1, max_value=11, value=1, key=f"pm_week_{program}")
    with mc4: pm_facilitator = st.text_input("Facilitator", value=get_staff_name(), key=f"pm_fac_{program}")
    pm_attendees = st.text_input("Attendees", placeholder="Names separated by commas", key=f"pm_att_{program}")

    st.markdown("""<div style="background:#f0f9f9;border:1px solid #1A7A7A;border-radius:8px;
        padding:6px 12px;font-size:0.78rem;color:#1A7A7A;margin-bottom:8px;">
        <strong>Meeting Norms:</strong> ☑ Student-centred &nbsp;·&nbsp; ☑ Evidence before opinion
        &nbsp;·&nbsp; ☑ Clear actions + ownership &nbsp;·&nbsp; ☑ Stick to time
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Section 1: Check-In ───────────────────────────────────────────────────
    checkin_label = "TEAM CHECK-IN — Regulation Before Reaction" if is_week_a else "TEAM CHECK-IN"
    checkin_prompt = "What do we need to know to support students effectively today?" if is_week_a else "Quick updates impacting program delivery"
    st.markdown(f"#### ⏱ 0–10 min | {checkin_label}")
    st.caption(checkin_prompt)
    pm_checkin = st.text_area("Check-in notes", height=80, key=f"pm_checkin_{program}",
        label_visibility="collapsed", placeholder=checkin_prompt)

    st.markdown("---")

    if is_week_a:
        # ── Week A: Student Concerns ──────────────────────────────────────────
        st.markdown("#### ⏱ 10–25 min | STUDENT CONCERNS — Structured Problem Solving")
        st.caption("Facilitator prompt: Push for function-based thinking, not description.")

        concerns_key = f"pm_concerns_{program}"
        if concerns_key not in st.session_state:
            st.session_state[concerns_key] = [{"student":"","concern":"","hypothesis":"","strategy":"","who":"","by_when":""}]

        concerns = st.session_state[concerns_key]
        header_cols = st.columns([2,2,2,2,1,1,0.5])
        for h, label in zip(header_cols, ["Student","Concern / Behaviour","Hypothesis (Why?)","Strategy to Try","Who","By When",""]):
            h.markdown(f"**{label}**" if label else "")

        for idx, row in enumerate(concerns):
            c1,c2,c3,c4,c5,c6,c7 = st.columns([2,2,2,2,1,1,0.5])
            with c1: row["student"] = st.selectbox("S",[""] + student_names, key=f"con_stu_{program}_{idx}", label_visibility="collapsed")
            with c2: row["concern"] = st.text_input("C", value=row["concern"], key=f"con_c_{program}_{idx}", label_visibility="collapsed")
            with c3: row["hypothesis"] = st.text_input("H", value=row["hypothesis"], key=f"con_h_{program}_{idx}", label_visibility="collapsed")
            with c4: row["strategy"] = st.text_input("St", value=row["strategy"], key=f"con_st_{program}_{idx}", label_visibility="collapsed")
            with c5: row["who"] = st.text_input("W", value=row["who"], key=f"con_w_{program}_{idx}", label_visibility="collapsed")
            with c6: row["by_when"] = st.text_input("By", value=row["by_when"], key=f"con_by_{program}_{idx}", label_visibility="collapsed")
            with c7:
                if len(concerns) > 1:
                    if st.button("✕", key=f"con_del_{program}_{idx}"):
                        concerns.pop(idx); st.rerun()
        if st.button("➕ Add student concern", key=f"con_add_{program}"):
            concerns.append({"student":"","concern":"","hypothesis":"","strategy":"","who":"","by_when":""}); st.rerun()

        st.markdown("---")

        # ── Week A: SMARTAR Spotlight ─────────────────────────────────────────
        st.markdown("#### ⏱ 25–40 min | SMARTAR GOAL SPOTLIGHT — 4 Students")
        st.caption("Rule: No update without evidence. What data or artefact supports this?")

        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = [{"student":"","goal_area":"","evidence":"","adjustment":"","responsible":""} for _ in range(4)]

        smartar = st.session_state[smartar_key]
        sh_cols = st.columns([2,2,2,2,1,0.5])
        for h, label in zip(sh_cols, ["Student","Goal Area","Current Level / Evidence","Next Adjustment","Responsible",""]):
            h.markdown(f"**{label}**" if label else "")

        for idx, row in enumerate(smartar):
            s1,s2,s3,s4,s5,s6 = st.columns([2,2,2,2,1,0.5])
            with s1: row["student"] = st.selectbox("S",[""] + student_names, key=f"sm_stu_{program}_{idx}", label_visibility="collapsed")
            with s2: row["goal_area"] = st.text_input("G", value=row["goal_area"], key=f"sm_g_{program}_{idx}", label_visibility="collapsed")
            with s3: row["evidence"] = st.text_input("E", value=row["evidence"], key=f"sm_e_{program}_{idx}", label_visibility="collapsed")
            with s4: row["adjustment"] = st.text_input("A", value=row["adjustment"], key=f"sm_a_{program}_{idx}", label_visibility="collapsed")
            with s5: row["responsible"] = st.text_input("R", value=row["responsible"], key=f"sm_r_{program}_{idx}", label_visibility="collapsed")
            with s6:
                if len(smartar) > 1:
                    if st.button("✕", key=f"sm_del_{program}_{idx}"):
                        smartar.pop(idx); st.rerun()
        if st.button("➕ Add SMARTAR row", key=f"sm_add_{program}"):
            smartar.append({"student":"","goal_area":"","evidence":"","adjustment":"","responsible":""}); st.rerun()

        st.markdown("---")

        # ── Week A: Reports / TAC ─────────────────────────────────────────────
        st.markdown("#### ⏱ 40–45 min | REPORTS / TAC / TRANSITIONS")
        pm_reports = st.text_area("Reports, TAC meetings, review or transition planning",
            height=80, key=f"pm_reports_{program}", label_visibility="collapsed",
            placeholder="Upcoming reports due · TAC meetings · Review or transition planning")
        priority_rows = []

    else:
        # ── Week B: CLC Priority Focus ────────────────────────────────────────
        st.markdown("#### ⏱ 10–30 min | CLC PRIORITY FOCUS — Implementation Fidelity")
        st.caption("Align to: Implementation Plan · PDP Focus Areas · LBU Priorities")

        priority_key = f"pm_priority_{program}"
        if priority_key not in st.session_state:
            st.session_state[priority_key] = [{"area":"","working":"","gap":"","adjustment":"","evidence":"","who":""}]

        priority_rows = st.session_state[priority_key]
        ph_cols = st.columns([2,2,2,2,2,1,0.5])
        for h, label in zip(ph_cols, ["Priority Area","What's Working","Gap Identified","Adjustment","Evidence to Collect","Who",""]):
            h.markdown(f"**{label}**" if label else "")

        for idx, row in enumerate(priority_rows):
            p1,p2,p3,p4,p5,p6,p7 = st.columns([2,2,2,2,2,1,0.5])
            with p1: row["area"] = st.text_input("A", value=row["area"], key=f"pr_a_{program}_{idx}", label_visibility="collapsed")
            with p2: row["working"] = st.text_input("W", value=row["working"], key=f"pr_w_{program}_{idx}", label_visibility="collapsed")
            with p3: row["gap"] = st.text_input("G", value=row["gap"], key=f"pr_g_{program}_{idx}", label_visibility="collapsed")
            with p4: row["adjustment"] = st.text_input("Adj", value=row["adjustment"], key=f"pr_adj_{program}_{idx}", label_visibility="collapsed")
            with p5: row["evidence"] = st.text_input("E", value=row["evidence"], key=f"pr_e_{program}_{idx}", label_visibility="collapsed")
            with p6: row["who"] = st.text_input("Who", value=row["who"], key=f"pr_who_{program}_{idx}", label_visibility="collapsed")
            with p7:
                if len(priority_rows) > 1:
                    if st.button("✕", key=f"pr_del_{program}_{idx}"):
                        priority_rows.pop(idx); st.rerun()
        if st.button("➕ Add priority row", key=f"pr_add_{program}"):
            priority_rows.append({"area":"","working":"","gap":"","adjustment":"","evidence":"","who":""}); st.rerun()

        st.markdown("---")

        # ── Week B: SMARTAR Spotlight ─────────────────────────────────────────
        st.markdown("#### ⏱ 30–45 min | SMARTAR GOAL SPOTLIGHT — 4 Students")
        st.caption("Rule: No update without evidence.")

        smartar_key = f"pm_smartar_{program}"
        if smartar_key not in st.session_state:
            st.session_state[smartar_key] = [{"student":"","goal_area":"","evidence":"","adjustment":"","responsible":""} for _ in range(4)]

        smartar = st.session_state[smartar_key]
        sh_cols = st.columns([2,2,2,2,1,0.5])
        for h, label in zip(sh_cols, ["Student","Goal Area","Current Level / Evidence","Next Adjustment","Responsible",""]):
            h.markdown(f"**{label}**" if label else "")

        for idx, row in enumerate(smartar):
            s1,s2,s3,s4,s5,s6 = st.columns([2,2,2,2,1,0.5])
            with s1: row["student"] = st.selectbox("S",[""] + student_names, key=f"sm_stu_{program}_{idx}", label_visibility="collapsed")
            with s2: row["goal_area"] = st.text_input("G", value=row["goal_area"], key=f"sm_g_{program}_{idx}", label_visibility="collapsed")
            with s3: row["evidence"] = st.text_input("E", value=row["evidence"], key=f"sm_e_{program}_{idx}", label_visibility="collapsed")
            with s4: row["adjustment"] = st.text_input("A", value=row["adjustment"], key=f"sm_a_{program}_{idx}", label_visibility="collapsed")
            with s5: row["responsible"] = st.text_input("R", value=row["responsible"], key=f"sm_r_{program}_{idx}", label_visibility="collapsed")
            with s6:
                if len(smartar) > 1:
                    if st.button("✕", key=f"sm_del_{program}_{idx}"):
                        smartar.pop(idx); st.rerun()
        if st.button("➕ Add SMARTAR row", key=f"sm_add_{program}"):
            smartar.append({"student":"","goal_area":"","evidence":"","adjustment":"","responsible":""}); st.rerun()

        pm_reports = ""
        concerns = []

    st.markdown("---")

    # ── Meeting Close ─────────────────────────────────────────────────────────
    st.markdown("#### ⭐ MEETING CLOSE")
    pm_decision = st.text_input("1. What is the single most important thing we agreed on today?",
        key=f"pm_dec_{program}", placeholder="The most important agreement...")
    pm_practice = st.text_input("2. What will look DIFFERENT in practice by next week?",
        key=f"pm_prac_{program}", placeholder="Concrete change to practice...")
    pm_carry = st.text_input("3. Carry forward to next meeting:",
        key=f"pm_carry_{program}", placeholder="Anything not resolved today...")

    st.markdown("---")

    # ── Actions — with carry-forward ─────────────────────────────────────────
    st.markdown("#### ✅ ACTIONS")
    actions_key = f"pm_actions_{program}"
    if actions_key not in st.session_state:
        # Pre-populate with incomplete actions from last meeting
        carried = [a for a in last_actions if not a.get("done", False)]
        st.session_state[actions_key] = carried if carried else [{"action":"","who":"","by_when":"","done":False}]

    actions = st.session_state[actions_key]

    if last_actions:
        incomplete = [a for a in last_actions if not a.get("done", False)]
        if incomplete:
            st.caption(f"⬆️ {len(incomplete)} action(s) carried forward from last meeting")

    ah_cols = st.columns([4,1,1,0.7,0.5])
    for h, label in zip(ah_cols, ["Action","Who","By When","✓ Done",""]):
        h.markdown(f"**{label}**" if label else "")

    for idx, row in enumerate(actions):
        a1,a2,a3,a4,a5 = st.columns([4,1,1,0.7,0.5])
        with a1: row["action"] = st.text_input("Act", value=row.get("action",""), key=f"act_a_{program}_{idx}", label_visibility="collapsed")
        with a2: row["who"] = st.text_input("Who", value=row.get("who",""), key=f"act_w_{program}_{idx}", label_visibility="collapsed")
        with a3: row["by_when"] = st.text_input("By", value=row.get("by_when",""), key=f"act_by_{program}_{idx}", label_visibility="collapsed")
        with a4: row["done"] = st.checkbox("✓", value=row.get("done",False), key=f"act_done_{program}_{idx}")
        with a5:
            if len(actions) > 1:
                if st.button("✕", key=f"act_del_{program}_{idx}"):
                    actions.pop(idx); st.rerun()

    if st.button("➕ Add action", key=f"act_add_{program}"):
        actions.append({"action":"","who":"","by_when":"","done":False}); st.rerun()

    st.markdown("---")

    # ── Save ──────────────────────────────────────────────────────────────────
    if st.button("💾 Save Meeting Record", type="primary", use_container_width=True, key=f"pm_save_{program}"):
        smartar_data = st.session_state.get(f"pm_smartar_{program}", [])
        actions_data = st.session_state.get(f"pm_actions_{program}", [])
        concerns_data = st.session_state.get(f"pm_concerns_{program}", []) if is_week_a else []
        priority_data = st.session_state.get(f"pm_priority_{program}", []) if not is_week_a else []

        try:
            insert("tm_program_meetings", {
                "program": program,
                "meeting_date": str(pm_date),
                "term": pm_term.strip(),
                "week_number": int(pm_week),
                "week_type": "A" if is_week_a else "B",
                "facilitator": pm_facilitator.strip(),
                "attendees": pm_attendees.strip(),
                "checkin_notes": pm_checkin.strip(),
                "student_concerns": _json.dumps(concerns_data),
                "smartar_spotlight": _json.dumps(smartar_data),
                "reports_tac_notes": pm_reports.strip() if is_week_a else "",
                "priority_focus": _json.dumps(priority_data),
                "key_decision": pm_decision.strip(),
                "practice_change": pm_practice.strip(),
                "carry_forward": pm_carry.strip(),
                "actions": _json.dumps(actions_data),
            })
            st.success("✅ Meeting record saved!")
            # Clear session state for this meeting
            for k in [f"pm_concerns_{program}", f"pm_smartar_{program}",
                      f"pm_priority_{program}", f"pm_actions_{program}"]:
                st.session_state.pop(k, None)
            st.rerun()
        except Exception as e:
            st.error(f"Could not save: {e}")

    # ── Past meetings ─────────────────────────────────────────────────────────
    if last_records:
        with st.expander(f"📚 Past meeting records ({len(last_records)})", expanded=False):
            for rec in reversed(last_records[-5:]):
                wt = rec.get("week_type","?")
                badge = "🔵 Week A" if wt == "A" else "🟡 Week B"
                st.markdown(f"**{badge}** · {rec.get('meeting_date','')} · Term {rec.get('term','')} W{rec.get('week_number','')}")
                key_dec = rec.get("key_decision","")
                if key_dec:
                    st.caption(f"Key decision: {key_dec}")
                st.divider()


def main():
    program   = get_program_from_params()
    prog_info = PROGRAMS[program]
    week_range = get_week_from_params()

    admin_login()

    grad_end = {
        "JP": "#3fa86a", "PY": "#2a6fd4", "SY": "#9b59b6",
        "STAFF": "#2a9fa8", "ADMIN": "#c97b1a"
    }.get(program, "#2a6fd4")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{prog_info['color']},{grad_end});
                padding:1.5rem 2rem;border-radius:16px;margin-bottom:1.5rem;">
      <div style="font-size:2.5rem;margin-bottom:0.25rem;">{prog_info['emoji']}</div>
      <h1 style="color:white;margin:0;font-size:1.8rem;">{prog_info['label']}</h1>
      <p style="color:rgba(255,255,255,0.85);margin:0.25rem 0 0;">Cowandilla Learning Centre · LBU</p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🔀 Switch Program")
        for p, info in PROGRAMS.items():
            if p != program:
                st.markdown(f"[{info['emoji']} {info['label']}](?program={p})")
        st.divider()
        if st.session_state.get("admin"):
            st.markdown("### ⚙️ Admin Mode Active")
            st.caption("You can add, edit and delete all content.")

    # ── Kaurna Welcome & Icebreaker (Staff Meeting only) ──────────────────────
    if program == "STAFF":
        import random as _random, hashlib as _hashlib
        from datetime import date as _date

        KAURNA_WELCOME = (
            "We acknowledge the Kaurna people as the traditional custodians of the land on which we meet today. "
            "We pay our respect to Elders past, present and emerging, and recognise their continuing connection "
            "to land, waters and community. We acknowledge that sovereignty was never ceded."
        )

        ICEBREAKERS = [
            ("🌟 Rose, Bud, Thorn", "Each person shares one **Rose** (something positive), one **Bud** (something they're looking forward to), and one **Thorn** (a challenge). Quick, strengths-based and trauma-informed — helps staff feel seen before getting into business."),
            ("🎯 Two Truths & a Wish", "Each person shares two things that are true about their week and one thing they wish had happened differently. Normalises struggle and celebrates wins in equal measure."),
            ("🌈 Colour of Your Week", "Each person names a colour that represents their week and briefly explains why. No wrong answers — invites emotional vocabulary without pressure."),
            ("🧠 Regulation Check-In", "On a scale of a traffic light — 🔴 Red, 🟡 Yellow, 🟢 Green — where are you right now? Optional: share one thing that's contributing to that state. Grounded in Berry Street's regulation-first approach."),
            ("💬 Appreciations Round", "Each person gives a genuine appreciation to a colleague — specific and behavioural. 'I noticed you did X and it made a difference because Y.' Builds psychological safety and models Berry Street's relational practice."),
            ("🎒 One Word Check-In", "Go around the room. Each person says one word that describes where they are at right now. No explanation needed unless they want to share. Fast, respectful of energy levels, and sets a relational tone."),
            ("🔦 Spotlight: Strengths", "Each person names one strength they brought to their work this week — their own or a student's. Aligns with Berry Street's strengths-based lens and helps staff shift into a positive frame before problem-solving."),
            ("🌊 Waves & Anchors", "Each person shares one thing that's been a 'wave' (something challenging or unpredictable) and one 'anchor' (something that has kept them grounded). Trauma-informed, honours complexity of the work."),
            ("📖 Story Starter", "A prompt is given — e.g. 'The best thing a student did this week was...' or 'Something that surprised me was...' Each person responds in one or two sentences. Opens the meeting with student-centred, hopeful thinking."),
            ("🤝 Shoutout Circle", "Before the agenda begins, anyone can give a shoutout to a colleague for something they observed. Creates a culture of noticing and naming positive contributions — aligned to relational and restorative practice."),
        ]

        # Rotate icebreaker by week
        _week_seed = int(_hashlib.md5(str(_date.today().isocalendar()[:2]).encode()).hexdigest(), 16)
        _icebreaker = ICEBREAKERS[_week_seed % len(ICEBREAKERS)]

        ic1, ic2 = st.columns(2)
        with ic1:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1a3a2a,#2d6b4a);color:white;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">
              <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;opacity:0.7;margin-bottom:0.5rem;">🌿 Kaurna Welcome to Country</div>
              <div style="font-size:0.88rem;line-height:1.6;font-style:italic;">"{KAURNA_WELCOME}"</div>
            </div>
            """, unsafe_allow_html=True)
        with ic2:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1a2e44,#2d4a6e);color:white;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">
              <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;opacity:0.7;margin-bottom:0.5rem;">🎯 Berry Street Icebreaker — This Week</div>
              <div style="font-size:1rem;font-weight:700;margin-bottom:0.4rem;">{_icebreaker[0]}</div>
              <div style="font-size:0.84rem;line-height:1.55;opacity:0.9;">{_icebreaker[1]}</div>
            </div>
            """, unsafe_allow_html=True)

    if program in ("JP", "PY", "SY"):
        tab_meeting, tab_sched, tab_agenda, tab_minutes, tab_actions, tab_attend, tab_docs = st.tabs([
            "🗒️ Program Meeting", "📅 Schedules", "📋 Agenda", "📝 Minutes", "✅ Actions", "🙋 Attendance", "📎 Documents"
        ])
        with tab_meeting: render_program_meeting(program)
    else:
        tab_sched, tab_agenda, tab_minutes, tab_actions, tab_attend, tab_docs = st.tabs([
            "📅 Schedules", "📋 Agenda", "📝 Minutes", "✅ Actions", "🙋 Attendance", "📎 Documents"
        ])

    with tab_sched:   render_schedules(program)
    with tab_agenda:  render_agenda(program)
    with tab_minutes: render_minutes(program, week_range=week_range if program == "STAFF" else None)
    with tab_actions: render_actions(program)
    with tab_attend:  render_attendance(program)
    with tab_docs:    render_documents(program)


if __name__ == "__main__":
    main()
