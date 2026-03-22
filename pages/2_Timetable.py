"""
CLC Timetable — Cowandilla Learning Centre
==========================================
- PyMuPDF (fitz) for PDF rendering — no poppler needed
- Per-program tabs: General, JP, PY, SY
- Auto term/week display in header
- Admin: upload, delete old versions
- Mobile-responsive layout
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

from auth import require_auth, logout_button, get_staff_name
require_auth("CLC Timetable", "📅")
logout_button("sidebar")

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

PROGRAMS = ["Specialist", "JP", "PY", "SY", "SSO", "Meetings"]
PROGRAM_LABELS = {
    "Specialist": "📋 Specialist Teacher",
    "JP":         "🟢 Junior Primary",
    "PY":         "🔵 Primary Years",
    "SY":         "🟣 Senior Years",
    "SSO":        "🟠 SSO Support",
    "Meetings":   "📅 Scheduled Meetings",
}

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
                {"content-type": "application/pdf", "upsert": "true"}
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
            mat = fitz.Matrix(2.0, 2.0)   # 2× scale ≈ 150 dpi equivalent
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(base64.b64encode(pix.tobytes("png")).decode())
        doc.close()
        return images
    except Exception:
        return None

# ── PDF split & bulk save ─────────────────────────────────────────────────────
# Page mapping (0-indexed):
#   Page 0       → Specialist
#   Pages 1–2    → JP
#   Pages 3–4    → PY
#   Page 5       → SY
#   Pages 6–7    → SSO
#   Page 8       → Meetings

PAGE_MAP = {
    "Specialist": [0],
    "JP":         [1, 2],
    "PY":         [3, 4],
    "SY":         [5],
    "SSO":        [6, 7],
    "Meetings":   [8],
}

def split_and_save_full_pdf(pdf_bytes: bytes, label: str) -> dict:
    """
    Split a full timetable PDF into per-program sections and save each one.
    Returns a dict of {program: status_message} or {"error": message}.
    """
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

    results = {}
    for program, page_indices in PAGE_MAP.items():
        # Skip pages that don't exist in this PDF
        valid_pages = [p for p in page_indices if p < total_pages]
        if not valid_pages:
            results[program] = "⚠️ Skipped — pages not found in PDF"
            continue

        try:
            # Build a new single-program PDF
            sub_doc = fitz.open()
            for page_idx in valid_pages:
                sub_doc.insert_pdf(full_doc, from_page=page_idx, to_page=page_idx)

            sub_bytes = sub_doc.tobytes()
            sub_doc.close()

            filename = f"timetable_{program.lower()}_{_uuid.uuid4().hex[:6]}.pdf"
            b64data = _b64.b64encode(sub_bytes).decode("utf-8")

            ok = save_timetable(filename, b64data, label, program)
            results[program] = "✅ Uploaded" if ok else "❌ Save failed"
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

# ── Inline Admin Bar ──────────────────────────────────────────────────────────
if not st.session_state.admin_authed:
    admin_col, login_col = st.columns([6, 1])
    with login_col:
        if st.button("🔐 Admin", use_container_width=True, key="show_admin_btn"):
            st.session_state["show_admin_login"] = not st.session_state.get("show_admin_login", False)
            st.rerun()

    if st.session_state.get("show_admin_login", False):
        st.markdown("""
        <div style="background:#eef2f7;border:1.5px solid #c5d3e0;border-radius:10px;
        padding:1rem 1.25rem;margin-bottom:1rem;">
        <div style="font-size:0.8rem;font-weight:700;color:#1a2e44;margin-bottom:0.6rem;">
        🔐 Admin Login — Upload New Timetable</div>
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
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        with lc3:
            if st.button("Cancel", use_container_width=True, key="admin_cancel"):
                st.session_state.show_admin_login = False
                st.rerun()

else:
    # ── Upload panel (shown inline at top when logged in) ──
    st.markdown("""
    <div style="background:linear-gradient(90deg,#1a2e44,#2d4f72);border-radius:12px;
    padding:1rem 1.25rem;margin-bottom:1.25rem;">
    <div style="font-size:0.9rem;font-weight:700;color:white;margin-bottom:0.75rem;">
    📤 Upload New Timetable</div>
    </div>""", unsafe_allow_html=True)

    upload_mode = st.radio("Upload mode", 
        ["📄 Full PDF (auto-split all sections)", "📑 Single section PDF"],
        horizontal=True, key="upload_mode")
    
    if upload_mode == "📄 Full PDF (auto-split all sections)":
        st.markdown("""<div style="background:#e8f5e1;border:1px solid #6BBF4E;border-radius:8px;
            padding:0.75rem 1rem;font-size:0.85rem;color:#1a2e44;margin-bottom:0.75rem;">
            📋 <strong>Page mapping:</strong> Page 1 = Specialist Teacher (Roisin) · 
            Pages 2–3 = JP · Pages 4–5 = PY · Page 6 = SY · 
            Pages 7–8 = SSO · Page 9 = Meetings
        </div>""", unsafe_allow_html=True)
        
        full_lbl = st.text_input("Label for all sections", placeholder="e.g. Term 1 · Week 6 · 2 Mar 2026", key="full_lbl")
        full_file = st.file_uploader("Upload full timetable PDF (all pages)", type=["pdf"], key="full_pdf")
        
        fc1, fc2 = st.columns(2)
        with fc1:
            if st.button("✅ Split & Upload All Sections", type="primary", use_container_width=True, key="full_upload_btn"):
                if not full_file:
                    st.error("Please choose a PDF file.")
                elif not full_lbl.strip():
                    st.error("Please add a label.")
                else:
                    full_file.seek(0)
                    raw = full_file.read()
                    with st.spinner("Splitting PDF and uploading all sections..."):
                        results = split_and_save_full_pdf(raw, full_lbl.strip())
                    if "error" in results:
                        st.error(f"❌ Split failed: {results['error']}")
                    else:
                        st.cache_resource.clear()
                        for prog, msg in results.items():
                            label = PROGRAM_LABELS.get(prog, prog)
                            st.markdown(f"**{label}:** {msg}")
                        st.success("✅ All sections uploaded!")
                        st.rerun()
        with fc2:
            if st.button("🚪 Logout Admin", use_container_width=True, key="logout_full"):
                st.session_state.admin_authed = False
                st.rerun()
    
    else:
        with st.form("upload_form_top", clear_on_submit=False):
            col_prog, col_lbl = st.columns([1, 2])
            with col_prog:
                prog_choice = st.selectbox("Program", options=PROGRAMS,
                                           format_func=lambda p: PROGRAM_LABELS[p])
            with col_lbl:
                lbl = st.text_input("Label", placeholder="e.g. Term 1 · Week 6 · 2 Mar 2026")

            file = st.file_uploader("Choose PDF", type=["pdf"], label_visibility="collapsed")

            uc1, uc2 = st.columns(2)
            with uc1:
                submitted = st.form_submit_button("✅ Upload & Set as Current",
                                                  type="primary", use_container_width=True)
            with uc2:
                logout = st.form_submit_button("🚪 Logout Admin", use_container_width=True)

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
            if logout:
                st.session_state.admin_authed = False
                st.rerun()

    # ── Version history with delete ──
    with st.expander("🗂️ Version History & Delete Old Versions"):
        for program in PROGRAMS:
            all_tt = get_all_timetables(program)
            if not all_tt:
                continue
            prog_label_str = PROGRAM_LABELS[program]
            st.markdown(f"**{prog_label_str}**")
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

st.markdown("---")

# ── Helper: render one program's timetable ────────────────────────────────────
def render_timetable_view(program: str):
    current = get_timetable(program)

    if current:
        label    = current.get("label") or current.get("filename", "Current Timetable")
        filename = current.get("filename", "timetable.pdf")
        uploaded = fmt_date(current.get("uploaded_at", ""))
        uploader = current.get("uploaded_by", "Admin")

        try:
            storage_path = current.get("storage_path", "")
            if storage_path:
                # Fetch from Supabase Storage
                _res = get_client().storage.from_(TIMETABLE_BUCKET).download(storage_path)
                pdf_bytes = _res if isinstance(_res, bytes) else bytes(_res)
                has_pdf = True
            elif current.get("file_data"):
                pdf_bytes = base64.b64decode(current["file_data"])
                has_pdf = True
            else:
                has_pdf = False
                pdf_bytes = None
        except Exception as _e:
            has_pdf   = False
            pdf_bytes = None

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

        if has_pdf:
            with st.spinner("Loading timetable…"):
                images = pdf_to_images(pdf_bytes)

            if images:
                st.markdown('<div class="card-wrap">', unsafe_allow_html=True)
                for i, img_b64 in enumerate(images):
                    if i > 0:
                        st.markdown('<hr class="page-divider">', unsafe_allow_html=True)
                    st.markdown(
                        f'<img src="data:image/png;base64,{img_b64}" '
                        f'class="timetable-img" alt="Page {i+1}">',
                        unsafe_allow_html=True,
                    )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Could not render PDF as image. Please download below.")

            st.download_button(
                label=f"⬇  Download {filename}",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                key=f"dl_{program}",
            )
        else:
            st.warning("Could not load timetable data — please ask admin to re-upload.")

    else:
        prog_label = PROGRAM_LABELS.get(program, program)
        st.markdown(f"""<div class="card-wrap"><div class="no-tt">
          <div class="no-tt-icon">📅</div>
          <h3>No timetable uploaded yet</h3>
          <p>{prog_label} timetable will appear here once uploaded by admin.</p>
        </div></div>""", unsafe_allow_html=True)


# ── Program tabs ──────────────────────────────────────────────────────────────
tab_labels = [PROGRAM_LABELS[p] for p in PROGRAMS]
tabs = st.tabs(tab_labels)

for tab, program in zip(tabs, PROGRAMS):
    with tab:
        render_timetable_view(program)


st.markdown('</div>', unsafe_allow_html=True)
