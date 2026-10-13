"""Planning Documents - staff download page with an admin tab to add documents and publish new versions.
Files are stored in Supabase Storage (bucket: planning-documents); the list is in table planning_documents."""
import re
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Planning Documents", page_icon="📄", layout="wide")

BUCKET = "planning-documents"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PROGRAMS = {"JP": ("Junior Primary", "Reception to Year 2", "#44546A"),
            "PY": ("Primary Years", "Years 3 to 6", "#6B4226"),
            "SY": ("Senior Years", "Years 7 to 10", "#2F4858"),
            "ALL": ("All programs", "Specialist and whole-unit documents", "#475569")}


def _call_first(module_name, names):
    """Call the first matching gate function in a shared auth module. Returns True if one ran."""
    try:
        mod = __import__(module_name)
    except Exception:
        return False
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            fn()
            return True
    return False


@st.cache_resource
def get_client():
    from supabase import create_client
    s = st.secrets
    url = s.get("SUPABASE_URL") or s["supabase"]["url"]
    key = s.get("SUPABASE_KEY") or s.get("SUPABASE_SERVICE_KEY") or s["supabase"]["key"]
    return create_client(url, key)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_file(path):
    return get_client().storage.from_(BUCKET).download(path)


def load_rows():
    r = get_client().table("planning_documents").select("*").eq("hidden", False).order("uploaded_at", desc=True).execute()
    return r.data or []


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def upload(program, title, desc, version, up):
    path = f"{program}/{datetime.now():%Y%m%d%H%M%S}_{safe_name(up.name)}"
    get_client().storage.from_(BUCKET).upload(path, up.getvalue(), {"content-type": MIME})
    get_client().table("planning_documents").insert({
        "program": program, "title": title, "description": desc, "version": version,
        "file_name": up.name, "storage_path": path, "is_current": True}).execute()


def admin_gate():
    """Confidential-password gate. Tries the shared confidential_auth module first, then a direct password check."""
    if st.session_state.get("pd_admin_ok"):
        return True
    try:
        import confidential_auth as ca
        names = ["require_confidential_auth", "require_confidential", "check_confidential_auth", "confidential_gate",
                 "require_auth", "check_password", "require_password", "gate", "login", "confidential_login"]
        found = [n for n in names if callable(getattr(ca, n, None))]
        for n in found:
            res = getattr(ca, n)()
            if res is False:
                return False
            return True
        mod_funcs = [n for n in dir(ca) if not n.startswith("_") and callable(getattr(ca, n))]
    except Exception:
        mod_funcs = None
    # Fallback: ask for the confidential password directly
    secret = None
    for k in ("CONFIDENTIAL_PASSWORD", "confidential_password", "ADMIN_PASSWORD", "admin_password"):
        try:
            if k in st.secrets:
                secret = st.secrets[k]
                break
        except Exception:
            pass
    if secret is None:
        st.error("The admin password could not be checked from this page.")
        if mod_funcs is not None:
            st.caption("Functions found in confidential_auth: " + (", ".join(mod_funcs) or "none"))
        else:
            st.caption("confidential_auth could not be imported from this page.")
        return False
    pw = st.text_input("Confidential password", type="password", key="pd_pw")
    if pw and pw == str(secret):
        st.session_state["pd_admin_ok"] = True
        st.rerun()
    elif pw:
        st.error("Incorrect password.")
    return False


# ---- staff-level gate (same shared module as the other staff tools)
_call_first("staff_auth", ["require_staff_auth", "require_staff", "check_staff_auth", "staff_gate"])

st.title("Planning Documents")
tab_dl, tab_admin = st.tabs(["Download", "Admin"])

try:
    rows = load_rows()
    db_ok = True
except Exception as e:
    rows, db_ok = [], False
    st.error("The document list could not be loaded. Check that planning_documents_schema.sql has been run and the "
             "Supabase secrets are set. Detail: " + str(e)[:200])

with tab_dl:
    st.write("Download a blank Word copy to complete for each unit or student. Save it under a new name so the "
             "original template stays clean. Older versions are listed under each document.")
    q = st.text_input("Search documents", "").lower().strip()
    for code, (name, sub, colour) in PROGRAMS.items():
        cur = [r for r in rows if r["program"] == code and r["is_current"]
               and q in (r["title"] + " " + (r["description"] or "")).lower()]
        if not cur:
            continue
        st.markdown(f"<h3 style='color:{colour};margin-bottom:0'>{name}</h3><div style='color:#666'>{sub}</div>",
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for i, r in enumerate(cur):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{r['title']}**")
                    st.caption(f"Version {r['version']} · updated {r['uploaded_at'][:10]}")
                    if r.get("description"):
                        st.write(r["description"])
                    try:
                        st.download_button("Download Word file", fetch_file(r["storage_path"]),
                                           file_name=r["file_name"], mime=MIME, key=f"d_{r['id']}")
                    except Exception:
                        st.warning("This file could not be loaded.")
                    older = [o for o in rows if o["program"] == code and o["title"] == r["title"] and not o["is_current"]]
                    if older:
                        with st.expander(f"Previous versions ({len(older)})"):
                            for o in older:
                                try:
                                    st.download_button(f"Version {o['version']} ({o['uploaded_at'][:10]})",
                                                       fetch_file(o["storage_path"]), file_name=o["file_name"],
                                                       mime=MIME, key=f"d_{o['id']}")
                                except Exception:
                                    st.caption(f"Version {o['version']} unavailable")
    if db_ok and not rows:
        st.info("No documents have been added yet. Use the Admin tab to upload the first ones.")

with tab_admin:
    if not admin_gate():
        st.stop()
    if not db_ok:
        st.stop()

    st.subheader("Add a new document")
    with st.form("add_doc", clear_on_submit=True):
        prog = st.selectbox("Group", list(PROGRAMS), format_func=lambda c: PROGRAMS[c][0])
        title = st.text_input("Title")
        desc = st.text_area("Short description")
        ver = st.text_input("Version", "1.0")
        up = st.file_uploader("Word file", type=["docx"])
        if st.form_submit_button("Add document"):
            if not (title.strip() and up):
                st.error("A title and a Word file are required.")
            else:
                upload(prog, title.strip(), desc.strip(), ver.strip() or "1.0", up)
                st.cache_data.clear()
                st.success(f"Added {title.strip()} (version {ver}).")

    st.subheader("Publish a new version")
    cur_all = [r for r in rows if r["is_current"]]
    if cur_all:
        with st.form("new_ver", clear_on_submit=True):
            pick = st.selectbox("Document", cur_all, format_func=lambda r: f"{PROGRAMS[r['program']][0]} - {r['title']} (v{r['version']})")
            nver = st.text_input("New version number", placeholder="1.1")
            nup = st.file_uploader("Updated Word file", type=["docx"])
            if st.form_submit_button("Publish new version"):
                if not (nver.strip() and nup):
                    st.error("A version number and a Word file are required.")
                else:
                    upload(pick["program"], pick["title"], pick.get("description") or "", nver.strip(), nup)
                    get_client().table("planning_documents").update({"is_current": False}).eq("id", pick["id"]).execute()
                    st.cache_data.clear()
                    st.success("New version published. The previous version is kept under Previous versions.")

    st.subheader("Remove a document from the list")
    if cur_all:
        rm = st.selectbox("Document to remove", cur_all, key="rm",
                          format_func=lambda r: f"{PROGRAMS[r['program']][0]} - {r['title']} (v{r['version']})")
        if st.button("Remove from list"):
            get_client().table("planning_documents").update({"hidden": True}).eq("program", rm["program"]).eq("title", rm["title"]).execute()
            st.success("Removed from the list. The files stay in storage.")
