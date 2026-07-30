"""
47_Document_Archive.py — CLC-LBU Portal Document Archive
==========================================================

Central archive browser: Browse (filters + confidential gate),
Student Folders (per-student view fed by the Student Register),
Add Document (manual upload), Admin (rename/merge folders,
confirmed delete, restore).
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
    fetch_register,
    register_program_map,
    rename_student,
    restore,
    soft_delete,
)

st.set_page_config(page_title="Document Archive", page_icon="🗄️", layout="wide")

try:
    from theme import apply_theme
    apply_theme()
except Exception:
    pass

try:
    from auth import require_login
    require_login()
except Exception:
    pass


# --- Confidential gate (wired to the portal's shared confidential_auth) ----
try:
    from confidential_auth import (
        SESSION_KEY as _CONF_KEY,
        _get_confidential_password,
        is_confidential_unlocked,
    )
    _CONF_AVAILABLE = True
except Exception:
    _CONF_AVAILABLE = False
    _CONF_KEY = "clc_confidential_ok"

    def is_confidential_unlocked():
        return bool(st.session_state.get(_CONF_KEY, False))


def _confidential_unlocked() -> bool:
    """True if the shared confidential section is unlocked this session."""
    return is_confidential_unlocked()


def _render_confidential_unlock():
    """Inline unlock for the confidential section (same shared password
    and session flag as Leadership / PDP Builder / LC Meeting Summariser,
    so unlocking here unlocks those too for this session)."""
    if not _CONF_AVAILABLE:
        st.warning(
            "confidential_auth.py was not found in the repo root, so "
            "confidential documents cannot be unlocked on this page."
        )
        return
    pwd = st.text_input(
        "Confidential password", type="password", key="arch_conf_pwd"
    )
    if st.button("🔓 Unlock confidential documents", key="arch_conf_btn"):
        if pwd and pwd == _get_confidential_password():
            st.session_state[_CONF_KEY] = True
            st.rerun()
        else:
            st.error("🚫 Incorrect password. This area is for CLC Leadership only.")


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
            st.success(
                "Confidential section unlocked for this session "
                "(also unlocks Leadership, PDP Builder and LC Meeting Summariser)."
            )
        else:
            _render_confidential_unlock()

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
            "Search titles", placeholder="e.g. safety plan, transition"
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
    # Apply a pending folder-button selection BEFORE the widget is created
    # (Streamlit forbids setting a widget's key after it's instantiated).
    if "_sf_pending" in st.session_state:
        st.session_state["student_folder_initials"] = st.session_state.pop(
            "_sf_pending"
        )

    st.write(
        "Enter a student's initials to open their folder — every archived "
        "document for that student, grouped by type."
    )

    _programs = register_program_map()

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
        _display = f"{ini} ({_programs[ini]})" if _programs.get(ini) else ini
        if not recs:
            st.info(f"No archived documents found for **{_display}**.")
        else:
            st.markdown(f"### 📁 {_display} — {len(recs)} document(s)")
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
                            if st.button("🗑️ Delete", key=f"sf_del_{rid}"):
                                st.session_state["_confirm_del"] = rid

                        if st.session_state.get("_confirm_del") == rid:
                            st.error(
                                f"⚠️ **You are about to delete:** {rec['title']} "
                                f"({rec['doc_type']}, added {str(rec.get('created_at',''))[:10]}). "
                                "**Before confirming, check you are keeping the right "
                                "version** — open both documents if unsure. Deleted "
                                "documents move to Admin → Deleted, where they can be "
                                "restored."
                            )
                            dc1, dc2, _sp = st.columns([1, 1, 3])
                            with dc1:
                                if st.button(
                                    "Yes, delete this document",
                                    key=f"sf_del_yes_{rid}", type="primary",
                                ):
                                    if soft_delete(
                                        rid,
                                        st.session_state.get("user_email", "unknown"),
                                    ):
                                        st.session_state.pop("_confirm_del", None)
                                        st.rerun()
                            with dc2:
                                if st.button("Cancel", key=f"sf_del_no_{rid}"):
                                    st.session_state.pop("_confirm_del", None)
                                    st.rerun()
    else:
        # Directory: every ACTIVE registered student (even with no docs
        # yet), plus any folders that exist outside the register.
        all_recs = fetch_archive(include_confidential=_conf_ok, limit=1000)
        counts: dict[str, int] = {}
        for r in all_recs:
            if r.get("student_initials"):
                counts[r["student_initials"]] = counts.get(r["student_initials"], 0) + 1

        active = fetch_register("active")
        directory = []  # (initials, label)
        seen = set()
        for s in active:
            n = counts.get(s["initials"], 0)
            prog = f" · {s['program']}" if s.get("program") else ""
            directory.append((s["initials"], f"📁 {s['initials']}{prog} ({n})"))
            seen.add(s["initials"])
        for ini in sorted(counts):
            if ini not in seen:
                directory.append((ini, f"📁 {ini} ({counts[ini]})"))

        if directory:
            st.markdown("**Student folders:**")
            cols = st.columns(4)
            for i, (ini, label) in enumerate(directory):
                with cols[i % 4]:
                    if st.button(label, key=f"open_{ini}", use_container_width=True):
                        st.session_state["_sf_pending"] = ini
                        st.rerun()
            st.caption(
                "Folders showing a program come from the Student Register; "
                "add new students there when they arrive at the centre."
            )
        else:
            st.info(
                "No students yet — add them in the Student Register when "
                "they arrive, and their folders will appear here."
            )

# ===========================================================================
# ADD DOCUMENT (manual upload — for docs created outside the portal)
# ===========================================================================
with tab_add:
    st.write(
        "Most documents are archived automatically by their source tool. "
        "Use this form to archive something created outside the portal "
        "(e.g. a term report or a scanned plan)."
    )

    _active_students = fetch_register("active")
    _student_options = ["— Not student-linked —"] + [
        f"{s['initials']} — {s.get('program') or ''}".strip(" —") for s in _active_students
    ] + ["Other (type initials manually)"]

    with st.form("manual_archive", clear_on_submit=True):
        up = st.file_uploader(
            "Document",
            type=["docx", "pdf", "xlsx", "pptx", "png", "jpg"],
        )
        a1, a2 = st.columns(2)
        with a1:
            m_title = st.text_input("Title *")
            m_doc_type = st.selectbox("Document type *", DOC_TYPES)
            m_student = st.selectbox("Student", _student_options)
            m_initials_manual = st.text_input(
                "Initials (only if 'Other' chosen above)", max_chars=4
            )
        with a2:
            m_term = st.selectbox("Term *", TERMS, index=1)
            m_year = st.selectbox("Year *", [2026, 2025])
            m_conf = st.checkbox("Confidential 🔒", value=False)
        m_notes = st.text_area("Notes (optional)", height=68)

        submitted = st.form_submit_button("Archive document", type="primary")

    if submitted:
        if m_student == "— Not student-linked —":
            m_ini = None
        elif m_student.startswith("Other"):
            m_ini = m_initials_manual.strip().upper() or None
        else:
            m_ini = m_student.split(" — ")[0]

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
                student_initials=m_ini,
                term=m_term,
                year=int(m_year),
                confidential=m_conf,
                created_by=user_email,
                notes=m_notes.strip() or None,
            )
            if rec:
                st.success(f"Archived: {rec['title']}")

# ===========================================================================
# ADMIN — rename/merge folders, confirmed delete, restore
# ===========================================================================
with tab_admin:
    if not _confidential_unlocked():
        st.info("Unlock the confidential section (Browse tab) to manage the archive.")
    else:
        st.subheader("📁 Rename / merge student folder")
        st.caption(
            "Moves every document from one set of initials to another. "
            "Renaming onto initials that already exist merges the two folders. "
            "(To change a registered student's initials, prefer the Student "
            "Register — it updates both the register and the folder together.)"
        )
        _all = fetch_archive(include_confidential=True, limit=1000)
        _folders = sorted({r["student_initials"] for r in _all if r.get("student_initials")})
        rn1, rn2, rn3 = st.columns([2, 2, 1])
        with rn1:
            rn_from = st.selectbox(
                "Current folder", ["—"] + _folders, key="rn_from"
            )
        with rn2:
            rn_to = st.text_input(
                "New initials", max_chars=4, key="rn_to", placeholder="e.g. JT"
            )
        with rn3:
            st.write("")
            st.write("")
            if st.button("Rename", type="primary", key="rn_go"):
                if rn_from == "—" or not rn_to.strip():
                    st.warning("Choose a folder and enter the new initials.")
                elif rn_from == rn_to.strip().upper():
                    st.info("Those are already the folder's initials.")
                else:
                    moved = rename_student(rn_from, rn_to)
                    if moved:
                        st.success(
                            f"Moved {moved} document(s): {rn_from} → {rn_to.strip().upper()}"
                        )
                        st.rerun()

        st.divider()
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
                st.session_state["_confirm_del"] = rec["id"]
            if st.session_state.get("_confirm_del") == rec["id"]:
                st.error(
                    f"⚠️ **You are about to delete:** {rec['title']}. "
                    "**Check you are keeping the right version before "
                    "confirming.** Deleted documents can be restored from "
                    "the Deleted list below."
                )
                a1, a2, _ = st.columns([1, 1, 3])
                with a1:
                    if st.button(
                        "Yes, delete", key=f"del_yes_{rec['id']}", type="primary"
                    ):
                        if soft_delete(rec["id"], user_email):
                            st.session_state.pop("_confirm_del", None)
                            st.rerun()
                with a2:
                    if st.button("Cancel", key=f"del_no_{rec['id']}"):
                        st.session_state.pop("_confirm_del", None)
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
