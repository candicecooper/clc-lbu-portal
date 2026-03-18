from theme import apply_clc_theme
from auth import require_auth, logout_button, get_staff_name
import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import uuid
import os

st.set_page_config(page_title="CLC Leadership", page_icon="👔", layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()

PORTAL_URL = "https://16cefb77.clc-portal.pages.dev/"
st.sidebar.markdown(
    f'<a href="{PORTAL_URL}" target="_self" style="display:block;text-align:center;'
    f'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    f'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    f'🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

st.markdown("""
<style>
  .doc-card { background:white;border:1px solid #e2e8f0;border-radius:10px;padding:1rem 1.25rem;margin-bottom:0.6rem;display:flex;align-items:center;gap:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.06); }
  .doc-icon { font-size:1.6rem;flex-shrink:0; }
  .doc-info { flex:1;min-width:0; }
  .doc-title { font-weight:600;font-size:0.95rem;color:#0f172a; }
  .doc-meta  { font-size:0.78rem;color:#64748b;margin-top:2px; }
  .folder-header { background:linear-gradient(135deg,#1A7A7A,#0f5f5f);color:white;border-radius:10px;padding:0.85rem 1.25rem;margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem; }
  .folder-header h3 { margin:0;font-size:1rem;font-weight:700; }
  .folder-header p  { margin:0.15rem 0 0;font-size:0.8rem;opacity:0.7; }
  .alloc-banner {
    background: linear-gradient(135deg, #0D5C6E 0%, #1A7A8F 100%);
    border-left: 5px solid #F5A623;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1.1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    box-shadow: 0 2px 8px rgba(13,92,110,0.15);
  }
  .alloc-banner-text { flex: 1; }
  .alloc-banner-text h4 { margin: 0; color: white; font-size: 1rem; font-weight: 700; }
  .alloc-banner-text p  { margin: 0.2rem 0 0; color: rgba(255,255,255,0.75); font-size: 0.82rem; }
</style>
""", unsafe_allow_html=True)

ALLOCATION_DASHBOARD_URL = "https://schoolssaedu-my.sharepoint.com/:x:/g/personal/candice_cooper330_schools_sa_edu_au/IQBwBkyLQUyyQbJk9mO8m4l9AWdt9I-B5mQ3krc0USBYfSI?email=Annette.Balestrin13%40schools.sa.edu.au&e=0HwxwB"

# ── SUPABASE ───────────────────────────────────────────────────────────────────
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
        return create_client(url, key)
    except Exception as e:
        st.warning(f"Supabase not connected: {e}")
        return None

supabase = init_supabase()
BUCKET = "clc-documents"

FOLDERS = {
    "leadership_documents": {
        "label": "Documents",
        "icon":  "🗂️",
        "desc":  "Site plans, strategic documents and leadership resources",
    },
    "leadership_allocation": {
        "label": "Allocation",
        "icon":  "📋",
        "desc":  "Staff allocation documents and planning",
    },
    "leadership_partnerships": {
        "label": "Partnership Details",
        "icon":  "🤝",
        "desc":  "Partnership agreements, contacts and collaboration documents",
    },
}

# ── AUTH ───────────────────────────────────────────────────────────────────────
def check_leadership_access():
    return st.session_state.get("leadership_access", False)

# ── DB HELPERS ─────────────────────────────────────────────────────────────────
def load_docs(folder_key):
    if not supabase:
        return st.session_state.get(f"local_docs_{folder_key}", [])
    try:
        resp = supabase.table("clc_documents").select("*").eq("section", folder_key).order("uploaded_at", desc=True).execute()
        return resp.data or []
    except Exception as e:
        st.error(f"Could not load documents: {e}")
        return []

def save_doc_record(folder_key, title, filename, storage_path, uploaded_by, file_size):
    record = {
        "id": str(uuid.uuid4()), "section": folder_key,
        "title": title.strip(), "filename": filename,
        "storage_path": storage_path, "uploaded_by": uploaded_by,
        "uploaded_at": datetime.now().isoformat(),
        "file_size_kb": round(file_size / 1024, 1),
    }
    if supabase:
        try:
            supabase.table("clc_documents").insert(record).execute()
            return True
        except Exception as e:
            st.error(f"Could not save record: {e}")
            return False
    key = f"local_docs_{folder_key}"
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state[key].insert(0, record)
    return True

def delete_doc(doc):
    if supabase:
        try:
            supabase.storage.from_(BUCKET).remove([doc["storage_path"]])
            supabase.table("clc_documents").delete().eq("id", doc["id"]).execute()
            return True
        except Exception as e:
            st.error(f"Delete failed: {e}")
    return False

def get_download_url(storage_path):
    if not supabase:
        return None
    try:
        resp = supabase.storage.from_(BUCKET).create_signed_url(storage_path, 3600)
        return resp.get("signedURL") or resp.get("signed_url")
    except Exception:
        return None

# ── ALLOCATION DASHBOARD BANNER ────────────────────────────────────────────────
def render_allocation_banner():
    st.markdown("""
    <div class="alloc-banner">
      <span style="font-size:2rem;">📊</span>
      <div class="alloc-banner-text">
        <h4>CLC Allocation Dashboard 2026</h4>
        <p>Live allocation tracker — student placements, program capacity & priority profiles · Stored in OneDrive</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.link_button(
        "📊 Open Allocation Dashboard (OneDrive)",
        ALLOCATION_DASHBOARD_URL,
        use_container_width=True,
        type="primary",
    )
    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

# ── FOLDER RENDERER ────────────────────────────────────────────────────────────
def render_folder(folder_key, folder_cfg):
    docs = load_docs(folder_key)
    st.markdown(f"""
    <div class="folder-header">
      <span style="font-size:1.5rem;">{folder_cfg['icon']}</span>
      <div><h3>{folder_cfg['label']}</h3><p>{folder_cfg['desc']}</p></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Allocation Dashboard pinned tile (partnerships only) ───────────────────
    if folder_key == "leadership_partnerships":
        render_allocation_banner()

    with st.expander("➕ Upload to this folder", expanded=False):
        doc_title     = st.text_input("Document Title *", placeholder="e.g. 2026 Site Plan Draft", key=f"title_{folder_key}")
        uploaded_file = st.file_uploader("Choose file",
            type=["pdf","docx","doc","xlsx","xls","pptx","ppt","png","jpg","jpeg","txt"],
            key=f"upload_{folder_key}")
        uploader_name = st.text_input("Your name", placeholder="e.g. Candice Cooper", key=f"uploader_{folder_key}")
        if st.button("📤 Upload Document", key=f"upload_btn_{folder_key}", type="primary"):
            if not doc_title:
                st.warning("Please enter a document title.")
            elif not uploaded_file:
                st.warning("Please select a file.")
            else:
                safe_name    = uploaded_file.name.replace(" ", "_")
                storage_path = f"{folder_key}/{uuid.uuid4().hex[:8]}_{safe_name}"
                file_bytes   = uploaded_file.read()
                upload_ok    = True
                if supabase:
                    try:
                        supabase.storage.from_(BUCKET).upload(
                            storage_path, file_bytes,
                            {"content-type": uploaded_file.type or "application/octet-stream"})
                    except Exception as e:
                        st.error(f"Storage upload failed: {e}")
                        upload_ok = False
                if upload_ok and save_doc_record(folder_key, doc_title, uploaded_file.name,
                                                  storage_path, uploader_name or "Leadership", len(file_bytes)):
                    st.success(f"✅ '{doc_title}' uploaded!")
                    st.rerun()

    if not docs:
        st.info("No documents yet. Use the upload panel above to add the first one.")
    else:
        st.markdown(f"**{len(docs)} document{'s' if len(docs) != 1 else ''}**")
        for doc in docs:
            ext  = doc.get("filename", "").rsplit(".", 1)[-1].lower()
            icon = {"pdf":"📕","docx":"📝","doc":"📝","xlsx":"📊","xls":"📊",
                    "pptx":"📊","ppt":"📊","png":"🖼️","jpg":"🖼️","jpeg":"🖼️","txt":"📄"}.get(ext, "📄")
            try:
                ts = datetime.fromisoformat(doc["uploaded_at"]).strftime("%d %b %Y")
            except Exception:
                ts = doc.get("uploaded_at", "")[:10]
            by_str   = f"Uploaded by {doc['uploaded_by']} · " if doc.get("uploaded_by") else ""
            size_str = f"{doc.get('file_size_kb','?')} KB" if doc.get("file_size_kb") else ""
            col_info, col_btn = st.columns([5, 2])
            with col_info:
                st.markdown(f"""<div class="doc-card"><div class="doc-icon">{icon}</div><div class="doc-info"><div class="doc-title">{doc['title']}</div><div class="doc-meta">{by_str}{ts}{' · ' + size_str if size_str else ''}</div></div></div>""", unsafe_allow_html=True)
            with col_btn:
                st.write("")
                url = get_download_url(doc.get("storage_path", ""))
                if url:
                    st.link_button("⬇ Download", url, use_container_width=True)
                else:
                    st.caption("No download link")
                if st.button("🗑️ Delete", key=f"del_{doc['id']}", use_container_width=True):
                    st.session_state[f"confirm_del_{doc['id']}"] = True
                    st.rerun()
                if st.session_state.get(f"confirm_del_{doc['id']}"):
                    st.warning(f"Delete '{doc['title']}'?")
                    cy, cn = st.columns(2)
                    with cy:
                        if st.button("Yes", key=f"yes_del_{doc['id']}", type="primary"):
                            if delete_doc(doc):
                                st.session_state[f"confirm_del_{doc['id']}"] = False
                                st.success("Deleted")
                                st.rerun()
                    with cn:
                        if st.button("No", key=f"no_del_{doc['id']}"):
                            st.session_state[f"confirm_del_{doc['id']}"] = False
                            st.rerun()
    st.markdown("---")

# ── LOGIN WALL ─────────────────────────────────────────────────────────────────
def render_login_wall():
    st.markdown("""
    <div style="max-width:420px;margin:4rem auto;text-align:center;">
      <div style="background:linear-gradient(135deg,#1A7A7A,#0f5f5f);color:white;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;">
        <div style="font-size:2.5rem;">👔</div>
        <h2 style="margin:0.5rem 0 0;font-size:1.3rem;font-weight:700;">CLC Leadership</h2>
        <p style="margin:0.4rem 0 0;opacity:0.7;font-size:0.85rem;">Cowandilla Learning Centre — LBU Staff Portal</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input("Enter leadership password", type="password", key="leadership_pwd")
        if st.button("🔓 Enter", key="leadership_login_btn", type="primary", use_container_width=True):
            try:
                admin_pass = st.secrets.get("ADMIN_PASSWORD", "") or os.environ.get("ADMIN_PASSWORD", "clcstaff2026")
            except Exception:
                admin_pass = "clcstaff2026"
            if pwd == admin_pass:
                st.session_state.leadership_access = True
                st.rerun()
            else:
                st.error("🚫 Incorrect password. This area is for CLC Leadership only.")

# ── MAIN ───────────────────────────────────────────────────────────────────────
if not check_leadership_access():
    render_login_wall()
    st.stop()

st.markdown("""
<div style="background:linear-gradient(135deg,#1A7A7A,#0f5f5f);color:white;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1.5rem;">
  <h1 style="margin:0;font-size:1.4rem;font-weight:700;">👔 CLC Leadership</h1>
  <p style="margin:0.3rem 0 0;opacity:0.7;font-size:0.85rem;">Leadership documents and resources — Cowandilla Learning Centre</p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Logout", key="leadership_logout"):
    st.session_state.leadership_access = False
    st.rerun()

for folder_key, folder_cfg in FOLDERS.items():
    render_folder(folder_key, folder_cfg)
