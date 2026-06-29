"""
CLC Timetable — Cowandilla Learning Centre
==========================================
- PyMuPDF (fitz) for PDF rendering — no poppler needed
- Per-program tabs: General, JP, PY, SY
- Auto term/week display in header
- Admin: upload, delete old versions
- Mobile-responsive layout
- INTELLIGENT SECTION DETECTION: Groups pages by detected section titles
"""

import streamlit as st
import base64
from datetime import datetime, timezone, date
from io import BytesIO

st.set_page_config(
    page_title="CLC Timetable",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# No authentication required for viewing timetables
# Admin password required for upload/delete functions

# ── SA School Calendar 2026 ───────────────────────────────────────────────────
# (term_number, first_monday, total_weeks)
SA_TERMS = [
    (1, date(2026, 1, 26), 11),
    (2, date(2026, 4, 27), 10),
    (3, date(2026, 7, 20), 10),
    (4, date(2026, 10, 12), 9),
]

def get_term_week_label() -> str:
    """Return e.g. 'Term 1 · Week 5' or 'School Holidays' based on today's date."""
    today = date.today()
    for term_num, first_mon, total_weeks in SA_TERMS:
        term_end = date.fromordinal(first_mon.toordinal() + total_weeks * 7 - 1)
        if first_mon <= today <= term_end:
            week_num = (today - first_mon).days // 7 + 1
            return f"Term {term_num}  ·  Week {week_num}"
    # Check if before first term
    if today < SA_TERMS[0][1]:
        return "Week 0 — Pre-Term"
    return "School Holidays"

# ── Supabase ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

PROGRAMS = ["Specialist", "JP", "PY", "SY", "SSO", "Leadership", "Meetings", "Yard", "Kitchen"]
PROGRAM_LABELS = {
    "Specialist": "📋 Specialist Teacher",
    "JP":         "🟢 Junior Primary",
    "PY":         "🔵 Primary Years",
    "SY":         "🟣 Senior Years",
    "SSO":        "🟠 SSO Support",
    "Leadership": "👔 Leadership",
    "Meetings":   "📅 Scheduled Meetings",
    "Yard":       "🌳 Yard Bookings",
    "Kitchen":    "🍳 Student Kitchen",
}

# Programs included in the full-PDF auto-split detection (teacher timetable pages only).
# Yard / Kitchen bookings are uploaded separately (PDF or Excel), so they're excluded here.
SPLIT_PROGRAMS = ["Specialist", "JP", "PY", "SY", "SSO", "Leadership", "Meetings"]

# Booking sheets — managed in their own admin zone so they can never affect teacher timetables.
BOOKING_PROGRAMS = ["Yard", "Kitchen"]

# ── File-type helpers (PDF vs Excel) ──────────────────────────────────────────
CONTENT_TYPES = {
    "pdf":  "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls":  "application/vnd.ms-excel",
    "xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
}

def file_ext(filename: str) -> str:
    fn = (filename or "").lower()
    return fn.rsplit(".", 1)[-1] if "." in fn else ""

def file_kind(filename: str) -> str:
    """Return 'excel', 'pdf', or 'unknown' based on extension."""
    ext = file_ext(filename)
    if ext in ("xlsx", "xls", "xlsm"):
        return "excel"
    if ext == "pdf":
        return "pdf"
    return "unknown"

def download_mime(filename: str) -> str:
    return CONTENT_TYPES.get(file_ext(filename), "application/octet-stream")

def get_timetable(program: str):
    """Return the latest timetable row for a given program."""
    try:
        result = (
            get_client()
            .table("timetable_store")
            .select("*")
            .eq("program", program)
            .order("uploaded_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def get_all_timetables(program: str):
    """Return all rows for a program (id + meta, no file_data) ordered newest first."""
    try:
        result = (
            get_client()
            .table("timetable_store")
            .select("id, filename, label, uploaded_by, uploaded_at, program")
            .eq("program", program)
            .order("uploaded_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []

TIMETABLE_BUCKET = "notice-attachments"  # reuse existing bucket

def save_timetable(filename, file_b64, label, program, uploaded_by="Admin"):
    """Save timetable — stores PDF in Supabase Storage, path in DB."""
    import base64 as _b64, uuid as _uuid
    try:
        client = get_client()
        # Decode b64 back to bytes for storage upload
        pdf_bytes = _b64.b64decode(file_b64)
        storage_path = f"timetables/{program}/{_uuid.uuid4().hex[:8]}_{filename}"
        try:
            client.storage.from_(TIMETABLE_BUCKET).upload(
                storage_path, pdf_bytes,
                {"content-type": download_mime(filename), "upsert": "true"}
            )
            use_storage = True
        except Exception:
            use_storage = False
            storage_path = ""

        client.table("timetable_store").insert({
            "filename":     filename,
            "file_data":    file_b64 if not use_storage else "",
            "storage_path": storage_path if use_storage else "",
            "label":        label,
            "program":      program,
            "uploaded_by":  uploaded_by,
            "uploaded_at":  datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False

def delete_timetable(row_id: int):
    try:
        get_client().table("timetable_store").delete().eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False

def verify_admin(password: str) -> bool:
    """Verify admin password for upload/delete functions."""
    return password == st.secrets.get("ADMIN_PASSWORD", "CLC2026admin")

def fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%-d %b %Y, %-I:%M %p")
    except Exception:
        return iso or ""

# ── PDF rendering via PyMuPDF (no poppler required) ───────────────────────────
def pdf_to_images(pdf_bytes: bytes) -> list | None:
    """Convert PDF bytes → list of base64 PNG strings via PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page in doc:
            mat = fitz.Matrix(2.5, 2.5)   # 2.5× scale — crisper when enlarged
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(base64.b64encode(pix.tobytes("png")).decode())
        doc.close()
        return images
    except Exception:
        return None

# ── Excel rendering → styled HTML tables (one per sheet) ──────────────────────
def excel_to_html(xls_bytes: bytes) -> str | None:
    """Convert Excel bytes → styled HTML tables (one per non-empty sheet).
    Returns None if pandas/openpyxl unavailable or the file can't be read."""
    try:
        import pandas as pd
        xls = pd.ExcelFile(BytesIO(xls_bytes))
    except Exception:
        return None

    parts = []
    for sheet_name in xls.sheet_names:
        try:
            df = xls.parse(sheet_name, header=None)
        except Exception:
            continue
        # Trim fully-empty rows/columns so the table isn't padded with blanks
        df = df.dropna(how="all").dropna(axis=1, how="all")
        if df.empty:
            continue
        df = df.fillna("")
        table_html = df.to_html(index=False, header=False, border=0,
                                classes="xls-table", escape=True)
        show_name = len(xls.sheet_names) > 1
        name_html = f'<div class="xls-sheet-name">📋 {sheet_name}</div>' if show_name else ""
        parts.append(f"{name_html}{table_html}")

    return "\n".join(parts) if parts else None
# Section detection - looks for exact phrases in the header band area
# These should match the exact wording in the colored header band of each timetable page
# Note: All matching is case-insensitive
SECTION_HEADERS = {
    "Specialist": ["specialist teacher timetable", "specialist teacher", "roisin"],
    "JP":         ["junior primary program timetable", "junior primary program", "junior primary", "jp program"],
    "PY":         ["primary years program timetable", "primary years program", "primary years", "py program"],
    "SY":         ["senior years program timetable", "senior years program", "senior years", "sy program"],
    "SSO":        ["sso support timetable", "sso support", "sso program", "support staff"],
    "Leadership": ["leadership timetable", "leadership team", "leadership", "manager", "candice", "annette"],
    "Meetings":   ["scheduled meetings timetable", "scheduled meetings", "meetings timetable", "meeting schedule", "staff meetings"],
}

# Staff names that indicate SSO section (case-insensitive)
SSO_STAFF = ["naomi", "vinnie", "cheryl", "jacqui", "caitie"]

# Header phrases used to auto-split a COMBINED bookings PDF into Yard vs Kitchen.
# Most specific first; the bare word ("yard"/"kitchen") is the last-resort fallback.
BOOKING_SECTION_HEADERS = {
    "Yard":    ["yard booking", "yard bookings", "yard duty", "yard roster", "yard timetable", "yard"],
    "Kitchen": ["student kitchen", "kitchen booking", "kitchen bookings", "kitchen roster", "kitchen timetable", "kitchen"],
}

_STAFF_SENTINEL = object()

def detect_page_section(page, page_num: int, headers=None, staff_map=None) -> tuple[str | None, str]:
    """
    Analyze a page's header band and return the section name if detected.
    `headers`   : {section: [phrases]} to look for (defaults to teacher SECTION_HEADERS)
    `staff_map` : {section: [names]} to look for as a backup (e.g. SSO staff); None to skip
    Returns (section_name, debug_info).
    """
    import fitz  # PyMuPDF - needed for fitz.Rect

    if headers is None:
        headers = SECTION_HEADERS

    try:
        # Extract text from just the top 20% of the page (header band area)
        page_rect = page.rect
        header_height = page_rect.height * 0.20  # Top 20% of page
        header_rect = fitz.Rect(0, 0, page_rect.width, header_height)
        header_text = page.get_text(clip=header_rect).lower().strip()

        # Also get first 300 characters of full page for backup detection
        preview = page.get_text().lower()[:300]

        # 1. Section header phrases in the header band (highest priority)
        for section, phrases in headers.items():
            for phrase in phrases:
                if phrase in header_text:
                    return section, f"Header: '{phrase}'"

        # 2. Staff names in the header band
        if staff_map:
            for section, names in staff_map.items():
                for nm in names:
                    if nm in header_text:
                        return section, f"Staff: '{nm}'"

        # 3. Fallback: header phrases anywhere in the page preview
        for section, phrases in headers.items():
            for phrase in phrases:
                if phrase in preview:
                    return section, f"Preview: '{phrase}'"

        # 4. Fallback: staff names in the preview
        if staff_map:
            for section, names in staff_map.items():
                for nm in names:
                    if nm in preview:
                        return section, f"Staff: '{nm}' (preview)"

        return None, f"No match (header: '{header_text[:50]}...')"

    except Exception as e:
        return None, f"Error: {e}"

def split_and_save_full_pdf(pdf_bytes: bytes, label: str,
                            target_programs=None, headers=None,
                            staff_map=_STAFF_SENTINEL, file_prefix="timetable") -> dict:
    """
    Split a combined PDF into per-section files by detecting section headers,
    grouping consecutive pages with the same section together.
    Defaults target the teacher timetable; pass booking config to split Yard/Kitchen.
    Returns {section: status_message} (plus "_debug") or {"error": message}.
    """
    if target_programs is None:
        target_programs = SPLIT_PROGRAMS
    if headers is None:
        headers = SECTION_HEADERS
    if staff_map is _STAFF_SENTINEL:
        staff_map = {"SSO": SSO_STAFF}

    try:
        import fitz  # PyMuPDF
        import base64 as _b64, uuid as _uuid
    except ImportError:
        return {"error": "PyMuPDF (fitz) is not installed."}

    try:
        full_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(full_doc)
    except Exception as e:
        return {"error": f"Could not open PDF: {e}"}

    # First pass: detect which section each page belongs to
    page_sections = []
    debug_info = []

    for page_num in range(total_pages):
        page = full_doc[page_num]
        section, debug = detect_page_section(page, page_num, headers, staff_map)
        page_sections.append(section)
        debug_info.append(f"Page {page_num + 1}: {section or 'UNDETECTED'} — {debug}")

    # Group consecutive pages by section (undetected pages join the current section)
    section_groups = {}
    current_section = None

    for page_num, section in enumerate(page_sections):
        if section:
            current_section = section
            section_groups.setdefault(section, []).append(page_num)
        elif current_section:
            section_groups[current_section].append(page_num)
            debug_info[page_num] = f"Page {page_num + 1}: {current_section} (continuation) — {debug_info[page_num].split(' — ')[1]}"
        # else: no section and no current section → page skipped

    results = {"_debug": "\n".join(debug_info)}

    for program in target_programs:
        if program not in section_groups:
            results[program] = "⚠️ Not found in PDF"
            continue

        page_indices = section_groups[program]

        try:
            sub_doc = fitz.open()
            for page_idx in page_indices:
                sub_doc.insert_pdf(full_doc, from_page=page_idx, to_page=page_idx)

            sub_bytes = sub_doc.tobytes()
            sub_doc.close()

            filename = f"{file_prefix}_{program.lower()}_{_uuid.uuid4().hex[:6]}.pdf"
            b64data = _b64.b64encode(sub_bytes).decode("utf-8")

            ok = save_timetable(filename, b64data, label, program)
            page_count = len(page_indices)
            page_list = ", ".join([str(p + 1) for p in page_indices])
            results[program] = (f"✅ Uploaded ({page_count} page{'s' if page_count != 1 else ''}: {page_list})"
                                if ok else "❌ Save failed")
        except Exception as e:
            results[program] = f"❌ Error: {e}"

    full_doc.close()
    return results

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');
*,*::before,*::after{box-sizing:border-box}
:root{
  --navy:#1a2e44;--navy-mid:#2d4f72;--navy-light:#e8edf3;--navy-border:#c5d3e0;
  --green:#059669;--green-light:#d1fae5;
  --red:#dc2626;--red-light:#fee2e2;
  --white:#ffffff;--bg:#f4f6f9;--ink:#1a2332;--ink-light:#6b7f94;--radius:12px
}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif!important;background:var(--bg)!important}
.block-container{padding:0!important;max-width:100%!important}
header{display:none!important}

/* ── Header ── */
.app-header{
  background:linear-gradient(135deg,var(--navy) 0%,var(--navy-mid) 100%);
  padding:22px 32px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;
}
.app-header-left{display:flex;align-items:center;gap:14px}
.app-header-icon{
  width:44px;height:44px;min-width:44px;
  background:rgba(255,255,255,0.12);border-radius:10px;
  display:flex;align-items:center;justify-content:center;font-size:22px;
}
.app-header-title{
  font-family:'DM Serif Display',serif;font-size:22px;
  color:white;line-height:1.1;
}
.app-header-sub{font-size:12px;color:rgba(255,255,255,0.55);margin-top:2px}
.header-badges{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.badge-white{
  background:rgba(255,255,255,0.12);
  border:1px solid rgba(255,255,255,0.2);
  border-radius:20px;padding:4px 12px;
  font-size:11px;font-weight:600;color:rgba(255,255,255,0.85);
  white-space:nowrap;
}
.badge-term{
  background:rgba(200,168,75,0.25);
  border:1px solid rgba(200,168,75,0.4);
  border-radius:20px;padding:4px 12px;
  font-size:11px;font-weight:700;color:#f0d080;
  white-space:nowrap;
}

/* ── Layout ── */
.main-wrap{max-width:980px;margin:0 auto;padding:28px 16px 60px}

/* ── Cards ── */
.card-wrap{
  background:var(--white);border:1px solid var(--navy-border);
  border-radius:14px;overflow:hidden;margin-bottom:18px;
}
.card-header{
  background:linear-gradient(90deg,var(--navy-light),#f0f4f8);
  padding:14px 20px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
  border-bottom:1px solid var(--navy-border);
}
.card-title{font-size:14px;font-weight:700;color:var(--navy)}
.card-meta{font-size:11px;color:var(--ink-light);margin-top:2px}
.badge-green{
  background:var(--green-light);color:var(--green);
  font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;
  white-space:nowrap;
}

/* ── Timetable image ── */
.timetable-img{width:100%;display:block}
.page-divider{border:none;border-top:2px dashed var(--navy-border);margin:4px 0}

/* ── Excel booking tables ── */
.xls-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;padding:14px 16px;font-size:13px}
.xls-sheet-name{
  font-size:0.85em;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;
  color:var(--navy-mid);margin:14px 0 8px;
}
.xls-table{
  width:100%;border-collapse:collapse;font-size:1em;margin-bottom:8px;
  font-family:'DM Sans',sans-serif;
}
.xls-table td{
  border:1px solid var(--navy-border);padding:0.55em 0.85em;
  color:var(--ink);vertical-align:top;white-space:nowrap;
}
.xls-table tr:nth-child(even) td{background:#fafbfd}
.xls-table tr:first-child td{
  background:var(--navy-light)!important;font-weight:700;color:var(--navy);
  position:sticky;top:0;
}

/* ── Empty state ── */
.no-tt{text-align:center;padding:48px 20px;color:var(--ink-light)}
.no-tt-icon{font-size:44px;margin-bottom:10px}
.no-tt h3{font-size:17px;font-weight:600;color:var(--navy);margin-bottom:6px}

/* ── Section label ── */
.section-label{
  font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
  color:var(--ink-light);margin:24px 0 10px;
}

/* ── History rows ── */
.history-row{
  background:var(--white);border:1px solid var(--navy-border);
  border-radius:10px;padding:10px 14px;margin-bottom:7px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;
}
.history-label{font-size:13px;font-weight:600;color:var(--ink)}
.history-meta{font-size:11px;color:var(--ink-light);margin-top:1px}

/* ── Admin panel ── */
.admin-panel{
  background:var(--white);border:1px solid var(--navy-border);
  border-radius:14px;padding:20px 24px;margin-bottom:18px;
}

/* ── Buttons ── */
.stButton>button{border-radius:8px!important;font-weight:600!important;font-family:'DM Sans',sans-serif!important}
.stButton>button[kind="primary"]{background:var(--navy)!important;border-color:var(--navy)!important;color:white!important}
.stDownloadButton>button{
  background:var(--navy)!important;color:white!important;
  border-radius:8px!important;font-weight:600!important;width:100%;
}
div[data-testid="stExpander"]{border:1px solid var(--navy-border)!important;border-radius:var(--radius)!important}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{gap:4px;background:transparent}
.stTabs [data-baseweb="tab"]{
  background:#e8edf3;border-radius:8px 8px 0 0;
  color:var(--navy);font-weight:600;padding:8px 18px;border:none;font-size:13px;
}
.stTabs [aria-selected="true"]{background:var(--navy-mid)!important;color:#fff!important}

/* ── Mobile ── */
@media(max-width:600px){
  .app-header{padding:16px 16px}
  .app-header-title{font-size:18px}
  .main-wrap{padding:16px 10px 40px}
  .admin-panel{padding:16px 14px}
  .card-header{padding:12px 14px}
  .stTabs [data-baseweb="tab"]{padding:6px 10px;font-size:12px}
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

# ── Header ────────────────────────────────────────────────────────────────────
term_label = get_term_week_label()

st.markdown(f"""
<div class="app-header">
  <div class="app-header-left">
    <div class="app-header-icon">📅</div>
    <div>
      <div class="app-header-title">CLC Timetable</div>
      <div class="app-header-sub">Cowandilla Learning Centre — LBU</div>
    </div>
  </div>
  <div class="header-badges">
    <span class="badge-term">📆 {term_label}</span>
    <span class="badge-white">Always the latest version</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

# ── Admin Access Bar ──────────────────────────────────────────────────────────
if not st.session_state.admin_authed:
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔐 Admin", use_container_width=True, key="show_admin_btn"):
            st.session_state["show_admin_login"] = not st.session_state.get("show_admin_login", False)
            st.rerun()

    if st.session_state.get("show_admin_login", False):
        st.markdown("""
        <div style="background:#eef2f7;border:1.5px solid #c5d3e0;border-radius:10px;
        padding:1rem 1.25rem;margin-bottom:1rem;">
        <div style="font-size:0.8rem;font-weight:700;color:#1a2e44;margin-bottom:0.6rem;">
        🔐 Admin Login — Upload & Manage Timetables</div>
        </div>""", unsafe_allow_html=True)
        lc1, lc2, lc3 = st.columns([3, 1, 1])
        with lc1:
            admin_pw = st.text_input("Password", type="password", key="admin_pw_inline",
                                     label_visibility="collapsed", placeholder="Enter admin password…")
        with lc2:
            if st.button("Login", type="primary", use_container_width=True, key="admin_login_btn"):
                if verify_admin(admin_pw):
                    st.session_state.admin_authed = True
                    st.session_state.show_admin_login = False
                    st.success("✅ Admin access granted")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        with lc3:
            if st.button("Cancel", use_container_width=True, key="admin_cancel"):
                st.session_state.show_admin_login = False
                st.rerun()

# ── Upload Panel (only shown when admin authenticated) ────────────────────────
if st.session_state.admin_authed:
    st.markdown("""
    <div style="background:linear-gradient(90deg,#1a2e44,#2d4f72);border-radius:12px;
    padding:1rem 1.25rem;margin-bottom:1.25rem;">
    <div style="font-size:0.9rem;font-weight:700;color:white;">📤 Upload Staff Timetables</div>
    <div style="font-size:0.72rem;color:rgba(255,255,255,0.75);margin-top:3px;">
    Specialist, JP, PY, SY, SSO, Leadership &amp; Meetings — Yard &amp; Kitchen bookings have their own zone below.</div>
    </div>""", unsafe_allow_html=True)

    upload_mode = st.radio("Upload mode", 
        ["📄 Full PDF (auto-split all sections)", "📑 Single section (PDF or Excel)"],
        horizontal=True, key="upload_mode")
    
    if upload_mode == "📄 Full PDF (auto-split all sections)":
        st.markdown("""<div style="background:#e8f5e1;border:1px solid #6BBF4E;border-radius:8px;
            padding:0.75rem 1rem;font-size:0.85rem;color:#1a2e44;margin-bottom:0.75rem;">
            🧠 <strong>Smart detection:</strong> The tool reads the header band at the top of each page 
            to determine which section it belongs to. It looks for program names (Specialist Teacher, 
            Junior Primary Program, etc.) and staff names (Naomi, Vinnie, Cheryl, etc.) to correctly 
            group pages together. After uploading, you'll see exactly what was detected on each page.
        </div>""", unsafe_allow_html=True)
        
        full_lbl = st.text_input("Label for all sections", placeholder="e.g. Term 1 · Week 6 · 2 Mar 2026", key="full_lbl")
        full_file = st.file_uploader("Upload full timetable PDF (all pages)", type=["pdf"], key="full_pdf")
        
        if st.button("✅ Split & Upload All Sections", type="primary", use_container_width=True, key="full_upload_btn"):
            if not full_file:
                st.error("Please choose a PDF file.")
            elif not full_lbl.strip():
                st.error("Please add a label.")
            else:
                full_file.seek(0)
                raw = full_file.read()
                with st.spinner("Detecting sections and splitting PDF..."):
                    results = split_and_save_full_pdf(raw, full_lbl.strip())
                if "error" in results:
                    st.error(f"❌ Split failed: {results['error']}")
                else:
                    st.cache_resource.clear()
                    
                    # Show debug info first
                    if "_debug" in results:
                        with st.expander("🔍 Page Detection Details", expanded=True):
                            st.text(results["_debug"])
                    
                    # Show results for each program
                    for prog, msg in results.items():
                        if prog == "_debug":
                            continue
                        label = PROGRAM_LABELS.get(prog, prog)
                        st.markdown(f"**{label}:** {msg}")
                    st.success("✅ All sections uploaded!")
                    st.rerun()

    else:
        st.markdown("""<div style="background:#eef6ff;border:1px solid #c5d3e0;border-radius:8px;
            padding:0.7rem 1rem;font-size:0.83rem;color:#1a2e44;margin-bottom:0.75rem;">
            📑 Upload a <strong>PDF or Excel</strong> file to a single staff timetable section.
            PDFs render as page images; Excel files (.xlsx) display as live tables.
            <em>Yard &amp; Student Kitchen bookings have their own upload area further down.</em>
        </div>""", unsafe_allow_html=True)
        with st.form("upload_form_top", clear_on_submit=False):
            col_prog, col_lbl = st.columns([1, 2])
            with col_prog:
                prog_choice = st.selectbox("Program", options=SPLIT_PROGRAMS,
                                           format_func=lambda p: PROGRAM_LABELS[p])
            with col_lbl:
                lbl = st.text_input("Label", placeholder="e.g. Term 1 · Week 6 · 2 Mar 2026")

            file = st.file_uploader("Choose PDF or Excel file",
                                    type=["pdf", "xlsx", "xls", "xlsm"],
                                    label_visibility="collapsed")

            submitted = st.form_submit_button("✅ Upload & Set as Current",
                                              type="primary", use_container_width=True)

            if submitted:
                if not file:
                    st.error("Please choose a PDF file.")
                elif not lbl.strip():
                    st.error("Please add a label.")
                else:
                    file.seek(0)
                    raw = file.read()
                    b64data = base64.b64encode(raw).decode("utf-8")
                    if save_timetable(file.name, b64data, lbl.strip(), prog_choice):
                        st.success(f"✅ {PROGRAM_LABELS[prog_choice]} timetable updated — {lbl.strip()}")
                        st.cache_resource.clear()
                        st.rerun()

    st.markdown("---")

    # ── Bookings upload zone (isolated — can only write to Yard / Kitchen) ──
    st.markdown("""
    <div style="background:linear-gradient(90deg,#1b6e3c,#2e9e5b);border-radius:12px;
    padding:1rem 1.25rem;margin-bottom:1rem;">
    <div style="font-size:0.9rem;font-weight:700;color:white;">📥 Upload Yard &amp; Kitchen Bookings</div>
    <div style="font-size:0.72rem;color:rgba(255,255,255,0.85);margin-top:3px;">
    Separate from staff timetables — uploading here only updates the booking sheet you choose.</div>
    </div>""", unsafe_allow_html=True)

    booking_mode = st.radio("Bookings upload mode",
        ["📄 Combined PDF (auto-split Yard & Kitchen)", "📑 Single booking sheet (PDF or Excel)"],
        horizontal=True, key="booking_mode")

    if booking_mode == "📄 Combined PDF (auto-split Yard & Kitchen)":
        st.markdown("""<div style="background:#e8f5e1;border:1px solid #6BBF4E;border-radius:8px;
            padding:0.75rem 1rem;font-size:0.85rem;color:#1a2e44;margin-bottom:0.75rem;">
            🧠 <strong>Smart split:</strong> Upload one PDF containing both the Yard and Student
            Kitchen pages. The tool reads the header band of each page (looking for "Yard" /
            "Student Kitchen") and files each page under the correct booking sheet. You'll see
            exactly what was detected on every page after uploading.
        </div>""", unsafe_allow_html=True)

        combo_lbl  = st.text_input("Label for both sheets", placeholder="e.g. Term 1 · Week 6", key="combo_booking_lbl")
        combo_file = st.file_uploader("Upload combined bookings PDF (Yard + Kitchen)", type=["pdf"], key="combo_booking_pdf")

        if st.button("✅ Split & Upload Bookings", type="primary", use_container_width=True, key="combo_booking_btn"):
            if not combo_file:
                st.error("Please choose a PDF file.")
            elif not combo_lbl.strip():
                st.error("Please add a label.")
            else:
                combo_file.seek(0)
                raw = combo_file.read()
                with st.spinner("Detecting Yard & Kitchen pages..."):
                    results = split_and_save_full_pdf(
                        raw, combo_lbl.strip(),
                        target_programs=BOOKING_PROGRAMS,
                        headers=BOOKING_SECTION_HEADERS,
                        staff_map=None,
                        file_prefix="booking",
                    )
                if "error" in results:
                    st.error(f"❌ Split failed: {results['error']}")
                else:
                    st.cache_resource.clear()
                    if "_debug" in results:
                        with st.expander("🔍 Page Detection Details", expanded=True):
                            st.text(results["_debug"])
                    for prog, msg in results.items():
                        if prog == "_debug":
                            continue
                        st.markdown(f"**{PROGRAM_LABELS.get(prog, prog)}:** {msg}")
                    st.success("✅ Bookings uploaded!")
                    st.rerun()

    else:
        st.markdown("""<div style="background:#e8f5e1;border:1px solid #6BBF4E;border-radius:8px;
            padding:0.7rem 1rem;font-size:0.83rem;color:#1a2e44;margin-bottom:0.75rem;">
            Upload a <strong>PDF or Excel</strong> file for 🌳 Yard Bookings or 🍳 Student Kitchen.
            Excel (.xlsx) displays as a live table; PDF renders as page images.
        </div>""", unsafe_allow_html=True)

        with st.form("booking_upload_form", clear_on_submit=False):
            bcol_prog, bcol_lbl = st.columns([1, 2])
            with bcol_prog:
                booking_choice = st.selectbox("Booking sheet", options=BOOKING_PROGRAMS,
                                              format_func=lambda p: PROGRAM_LABELS[p],
                                              key="booking_prog")
            with bcol_lbl:
                booking_lbl = st.text_input("Label", placeholder="e.g. Term 1 · Week 6",
                                            key="booking_lbl")

            booking_file = st.file_uploader("Choose PDF or Excel file",
                                            type=["pdf", "xlsx", "xls", "xlsm"],
                                            label_visibility="collapsed", key="booking_file")

            booking_submitted = st.form_submit_button("✅ Upload Booking & Set as Current",
                                                      type="primary", use_container_width=True)

            if booking_submitted:
                if not booking_file:
                    st.error("Please choose a PDF or Excel file.")
                elif not booking_lbl.strip():
                    st.error("Please add a label.")
                else:
                    booking_file.seek(0)
                    braw = booking_file.read()
                    bb64 = base64.b64encode(braw).decode("utf-8")
                    if save_timetable(booking_file.name, bb64, booking_lbl.strip(), booking_choice):
                        st.success(f"✅ {PROGRAM_LABELS[booking_choice]} updated — {booking_lbl.strip()}")
                        st.cache_resource.clear()
                        st.rerun()

    st.markdown("---")

    # ── Version history with delete (admin only) ──
    def _render_history(programs):
        any_rows = False
        for program in programs:
            all_tt = get_all_timetables(program)
            if not all_tt:
                continue
            any_rows = True
            st.markdown(f"**{PROGRAM_LABELS[program]}**")
            for i, tt in enumerate(all_tt):
                row_id   = tt.get("id")
                tt_label = tt.get("label") or tt.get("filename", "")
                tt_meta  = f"Uploaded {fmt_date(tt.get('uploaded_at', ''))} · {tt.get('filename', '')}"
                is_current = (i == 0)
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    badge = " ✅ Current" if is_current else ""
                    st.markdown(f'<div style="font-size:0.82rem;font-weight:600;color:#1a2e44;">📄 {tt_label}{badge}</div>'
                                f'<div style="font-size:0.72rem;color:#6b7f94;">{tt_meta}</div>',
                                unsafe_allow_html=True)
                with col_del:
                    if not is_current:
                        if st.button("🗑", key=f"del_{row_id}", help="Delete this version"):
                            if delete_timetable(row_id):
                                st.success("Deleted.")
                                st.rerun()
                    else:
                        st.markdown("<div style='font-size:11px;color:#9aa5b4;text-align:center;padding-top:8px;'>active</div>",
                                    unsafe_allow_html=True)
        if not any_rows:
            st.caption("Nothing uploaded yet.")

    with st.expander("🗂️ Timetable Version History & Delete"):
        _render_history(SPLIT_PROGRAMS)

    with st.expander("🗂️ Bookings Version History & Delete"):
        _render_history(BOOKING_PROGRAMS)
    
    # Logout button
    if st.button("🚪 Logout Admin", use_container_width=False, key="logout_admin"):
        st.session_state.admin_authed = False
        st.rerun()

st.markdown("---")

# ── Helper: render one program's timetable / bookings ─────────────────────────
def render_timetable_view(program: str):
    current = get_timetable(program)

    if not current:
        prog_label = PROGRAM_LABELS.get(program, program)
        st.markdown(f"""<div class="card-wrap"><div class="no-tt">
          <div class="no-tt-icon">📅</div>
          <h3>Nothing uploaded yet</h3>
          <p>{prog_label} will appear here once uploaded by admin (PDF or Excel).</p>
        </div></div>""", unsafe_allow_html=True)
        return

    label    = current.get("label") or current.get("filename", "Current")
    filename = current.get("filename", "timetable.pdf")
    uploaded = fmt_date(current.get("uploaded_at", ""))
    uploader = current.get("uploaded_by", "Admin")
    kind     = file_kind(filename)

    # ── Load the raw file bytes (Storage first, then inline b64 fallback) ──
    try:
        storage_path = current.get("storage_path", "")
        if storage_path:
            _res = get_client().storage.from_(TIMETABLE_BUCKET).download(storage_path)
            file_bytes = _res if isinstance(_res, bytes) else bytes(_res)
            has_file = True
        elif current.get("file_data"):
            file_bytes = base64.b64decode(current["file_data"])
            has_file = True
        else:
            has_file, file_bytes = False, None
    except Exception:
        has_file, file_bytes = False, None

    st.markdown(f"""
    <div class="card-wrap">
      <div class="card-header">
        <div>
          <div class="card-title">📄 {label}</div>
          <div class="card-meta">Uploaded {uploaded} by {uploader}</div>
        </div>
        <span class="badge-green">✅ Current</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if not has_file:
        st.warning("Could not load this file — please ask admin to re-upload.")
        return

    # ── Excel → live tables ──
    if kind == "excel":
        with st.spinner("Loading bookings…"):
            html = excel_to_html(file_bytes)
        if html:
            wrap_style = ""
            if program in BOOKING_PROGRAMS:
                zoom = st.slider("🔍 View size — drag to enlarge", min_value=100, max_value=260,
                                 value=150, step=10, format="%d%%", key=f"zoom_{program}")
                wrap_style = f"font-size:{round(13 * zoom / 100)}px;"
            st.markdown(f'<div class="card-wrap"><div class="xls-scroll" style="{wrap_style}">{html}</div></div>',
                        unsafe_allow_html=True)
        else:
            st.info("Couldn't display this spreadsheet inline (the openpyxl package may be "
                    "missing from requirements). You can still download it below.")
        st.download_button(
            label=f"⬇  Download {filename}",
            data=file_bytes,
            file_name=filename,
            mime=download_mime(filename),
            use_container_width=True,
            key=f"dl_{program}",
        )
        return

    # ── PDF (default) → page images ──
    with st.spinner("Loading…"):
        images = pdf_to_images(file_bytes)

    if images:
        img_width = "100%"
        if program in BOOKING_PROGRAMS:
            zoom = st.slider("🔍 View size — drag to enlarge", min_value=100, max_value=260,
                             value=150, step=10, format="%d%%", key=f"zoom_{program}")
            img_width = f"{zoom}%"
        st.markdown('<div class="card-wrap"><div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">',
                    unsafe_allow_html=True)
        for i, img_b64 in enumerate(images):
            if i > 0:
                st.markdown('<hr class="page-divider">', unsafe_allow_html=True)
            st.markdown(
                f'<img src="data:image/png;base64,{img_b64}" '
                f'class="timetable-img" style="width:{img_width};max-width:none;" alt="Page {i+1}">',
                unsafe_allow_html=True,
            )
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Could not render PDF as image. Please download below.")

    st.download_button(
        label=f"⬇  Download {filename}",
        data=file_bytes,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
        key=f"dl_{program}",
    )


# ── Program tabs ──────────────────────────────────────────────────────────────
tab_labels = [PROGRAM_LABELS[p] for p in PROGRAMS]
tabs = st.tabs(tab_labels)

for tab, program in zip(tabs, PROGRAMS):
    with tab:
        render_timetable_view(program)


st.markdown('</div>', unsafe_allow_html=True)
