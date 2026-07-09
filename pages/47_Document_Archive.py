"""
45_Document_Archive.py — CLC-LBU Portal Document Archive
==========================================================

Central archive browser. Documents generated across the portal
(PDPs, Behaviour Summaries/BAPs, Safety & Risk Plans, and later
meeting docs, term reports and bulletins) land here and can be
searched, downloaded, and (for admins) soft-deleted or restored.

Rename to fit your page numbering. Requires archive_utils.py in the
repo root alongside the other shared modules.
"""

import streamlit as st

from archive_utils import (
    DOC_TYPES,
    SOURCE_TOOLS,
    TERMS,
    archive_document,
    download_bytes,
    download_link_html,
    fetch_archive,
    restore,
    soft_delete,
)

st.set_page_config(page_title="Document Archive", page_icon="🗄️", layout="wide")

# --- Portal theme & auth (match your other pages) -------------------------
try:
    from theme import apply_theme
    apply_theme()
except Exception:
    pass

try:
    from auth import require_login  # >>> ADJUST to your actual auth helper
    require_login()
except Exception:
    pass


# --- Confidential gate ------------------------------------------------------
def _confidential_unlocked() -> bool:
    """Return True if this session has passed the confidential gate.

    >>> ADJUST: wire this to your confidential_auth.py. If it exposes a
    check function like `check_confidential_access()` that renders its
    own password prompt and returns True/False, just call it here.
    """
    try:
        from confidential_auth import check_confidential_access
        return bool(check_confidential_access())
    except Exception:
        return bool(st.session_state.get("confidential_authenticated", False))


st.title("🗄️ Document Archive")
st.caption(
    "Central archive of documents generated across the portal. "
    "Student-linked documents are stored with initials only."
)

user_email = st.session_state.get("user_email", "unknown")

tab_browse, tab_student, tab_add, tab_admin = st.tabs(
    ["🔍 Browse", "👤 Student Folders", "➕ Add Document", "🛠️ Admin"]
)

# ===========================================================================
# BROWSE
# ===========================================================================
with tab_browse:
    show_confidential = False
    with st.expander("🔒 Confidential documents", expanded=False):
        st.write(
            "PDPs, leadership documents and LC meeting records are only "
            "shown after unlocking the confidential section."
        )
        if _confidential_unlocked():
            show_confidential = True
            st.success("Confidential section unlocked for this session.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        f_doc_type = st.selectbox("Document type", ["All"] + DOC_TYPES)
    with c2:
        f_tool = st.selectbox("Source tool", ["All"] + SOURCE_TOOLS)
    with c3:
        f_term = st.selectbox("Term", ["All"] + TERMS)
    with c4:
        f_year = st.selectbox("Year", ["All", 2026, 2025])

    c5, c6 = st.columns([1, 3])
    with c5:
        f_initials = st.text_input(
            "Student initials", max_chars=4, placeholder="e.g. JT"
        )
    with c6:
        f_keyword = st.text_input(
            "Search titles", placeholder="e.g. safety plan, PDP, transition"
        )

    records = fetch_archive(
        include_confidential=show_confidential,
        doc_type=None if f_doc_type == "All" else f_doc_type,
        source_tool=None if f_tool == "All" else f_tool,
        term=None if f_term == "All" else f_term,
        year=None if f_year == "All" else int(f_year),
        student_initials=f_initials or None,
        keyword=f_keyword or None,
    )

    st.markdown(f"**{len(records)} document(s) found**")
    st.divider()

    if not records:
        st.info("No documents match the current filters.")

    for rec in records:
        rid = rec["id"]
        lock = "🔒 " if rec.get("confidential") else ""
        initials = f" · {rec['student_initials']}" if rec.get("student_initials") else ""

        with st.container(border=True):
            left, right = st.columns([4, 1])
            with left:
                st.markdown(f"**{lock}{rec['title']}**")
                st.caption(
                    f"{rec['doc_type']} · {rec['source_tool']}{initials} · "
                    f"{rec.get('term', '')} {rec.get('year', '')} · "
                    f"added {str(rec.get('created_at', ''))[:10]} "
                    f"by {rec.get('created_by', 'unknown')}"
                )
                if rec.get("notes"):
                    st.caption(f"📝 {rec['notes']}")
            with right:
                # Fetch bytes on demand, then render an iOS-safe link.
                if st.button("Prepare download", key=f"dl_{rid}"):
                    st.session_state[f"bytes_{rid}"] = download_bytes(
                        rec["storage_path"]
                    )
                if st.session_state.get(f"bytes_{rid}"):
                    st.markdown(
                        download_link_html(
                            st.session_state[f"bytes_{rid}"],
                            rec["file_name"],
                        ),
                        unsafe_allow_html=True,
                    )

# ===========================================================================
# STUDENT FOLDERS — everything for one student, grouped by document type
# ===========================================================================
with tab_student:
    st.write(
        "Enter a student's initials to open their folder — every archived "
        "document for that student, grouped by type."
    )

    sc1, sc2 = st.columns([1, 3])
    with sc1:
        sf_initials = st.text_input(
            "Student initials", max_chars=4, placeholder="e.g. JT",
            key="student_folder_initials",
        )

    _conf_ok = _confidential_unlocked()

    if sf_initials.strip():
        ini = sf_initials.strip().upper()
        recs = fetch_archive(
            include_confidential=_conf_ok,
            student_initials=ini,
            limit=500,
        )
        if not recs:
            st.info(f"No archived documents found for **{ini}**.")
        else:
            st.markdown(f"### 📁 {ini} — {len(recs)} document(s)")
            by_type: dict[str, list] = {}
            for r in recs:
                by_type.setdefault(r["doc_type"], []).append(r)

            for dtype in sorted(by_type):
                with st.expander(
                    f"{dtype} ({len(by_type[dtype])})", expanded=True
                ):
                    for rec in by_type[dtype]:
                        rid = rec["id"]
                        lock = "🔒 " if rec.get("confidential") else ""
                        l, r_ = st.columns([4, 1])
                        with l:
                            st.markdown(f"**{lock}{rec['title']}**")
                            st.caption(
                                f"{rec['source_tool']} · "
                                f"{rec.get('term', '')} {rec.get('year', '')} · "
                                f"added {str(rec.get('created_at', ''))[:10]} "
                                f"by {rec.get('created_by', 'unknown')}"
                            )
                        with r_:
                            if st.button("Prepare download", key=f"sf_dl_{rid}"):
                                st.session_state[f"bytes_{rid}"] = download_bytes(
                                    rec["storage_path"]
                                )
                            if st.session_state.get(f"bytes_{rid}"):
                                st.markdown(
                                    download_link_html(
                                        st.session_state[f"bytes_{rid}"],
                                        rec["file_name"],
                                    ),
                                    unsafe_allow_html=True,
                                )
    else:
        # Directory of all students with archived documents
        all_recs = fetch_archive(include_confidential=_conf_ok, limit=1000)
        counts: dict[str, int] = {}
        for r in all_recs:
            if r.get("student_initials"):
                counts[r["student_initials"]] = counts.get(r["student_initials"], 0) + 1
        if counts:
            st.markdown("**Students with archived documents:**")
            cols = st.columns(6)
            for i, ini in enumerate(sorted(counts)):
                with cols[i % 6]:
                    if st.button(
                        f"📁 {ini} ({counts[ini]})", key=f"open_{ini}",
                        use_container_width=True,
                    ):
                        st.session_state["student_folder_initials"] = ini
                        st.rerun()
        else:
            st.info("No student-linked documents archived yet.")

# ===========================================================================
# ADD DOCUMENT (manual upload — for docs created outside the portal)
# ===========================================================================
with tab_add:
    st.write(
        "Most documents are archived automatically by their source tool. "
        "Use this form to archive something created outside the portal "
        "(e.g. a term report or a scanned plan)."
    )

    with st.form("manual_archive", clear_on_submit=True):
        up = st.file_uploader(
            "Document",
            type=["docx", "pdf", "xlsx", "pptx", "png", "jpg"],
        )
        a1, a2 = st.columns(2)
        with a1:
            m_title = st.text_input("Title *")
            m_doc_type = st.selectbox("Document type *", DOC_TYPES)
            m_initials = st.text_input(
                "Student initials (if student-linked)", max_chars=4
            )
        with a2:
            m_term = st.selectbox("Term *", TERMS, index=1)
            m_year = st.selectbox("Year *", [2026, 2025])
            m_conf = st.checkbox("Confidential 🔒", value=False)
        m_notes = st.text_area("Notes (optional)", height=68)

        submitted = st.form_submit_button("Archive document", type="primary")

    if submitted:
        if not up or not m_title.strip():
            st.warning("A file and a title are both required.")
        elif m_conf and not _confidential_unlocked():
            st.warning(
                "Unlock the confidential section (Browse tab) before "
                "archiving confidential documents."
            )
        else:
            rec = archive_document(
                source_tool="Manual Upload",
                doc_type=m_doc_type,
                title=m_title.strip(),
                file_bytes=up.getvalue(),
                filename=up.name,
                student_initials=m_initials or None,
                term=m_term,
                year=int(m_year),
                confidential=m_conf,
                created_by=user_email,
                notes=m_notes.strip() or None,
            )
            if rec:
                st.success(f"Archived: {rec['title']}")

# ===========================================================================
# ADMIN — soft delete / restore (confidential gate required)
# ===========================================================================
with tab_admin:
    if not _confidential_unlocked():
        st.info("Unlock the confidential section (Browse tab) to manage the archive.")
    else:
        st.subheader("Manage documents")
        all_recs = fetch_archive(include_confidential=True, include_deleted=True)

        active = [r for r in all_recs if not r.get("deleted")]
        deleted = [r for r in all_recs if r.get("deleted")]

        st.markdown("**Active documents**")
        for rec in active:
            c1, c2 = st.columns([5, 1])
            c1.write(
                f"{'🔒 ' if rec.get('confidential') else ''}{rec['title']} "
                f"({rec['doc_type']}, {rec.get('term','')} {rec.get('year','')})"
            )
            if c2.button("Delete", key=f"del_{rec['id']}"):
                if soft_delete(rec["id"], user_email):
                    st.rerun()

        if deleted:
            st.divider()
            st.markdown("**Deleted (restorable)**")
            for rec in deleted:
                c1, c2 = st.columns([5, 1])
                c1.write(
                    f"~~{rec['title']}~~ · deleted by "
                    f"{rec.get('deleted_by', '?')} "
                    f"{str(rec.get('deleted_at', ''))[:10]}"
                )
                if c2.button("Restore", key=f"res_{rec['id']}"):
                    if restore(rec["id"]):
                        st.rerun()
