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
    rename_student,
    set_student_status,
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


def _student_labels() -> dict:
    """{initials: 'INI · PROGRAM · Yr N'} for every registered student,
    so folders display identically everywhere."""
    labels = {}
    for s in fetch_register(None):
        bits = [s["initials"]]
        if s.get("program"):
            bits.append(s["program"])
        if s.get("year_level") is not None:
            bits.append(f"Yr {s['year_level']}")
        labels[s["initials"]] = " · ".join(bits)
    return labels


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
    # Apply a pending folder-button selection, or a request to clear back to
    # the directory, BEFORE the widget is created (Streamlit forbids setting
    # a widget's key after it's instantiated).
    if "_sf_pending" in st.session_state:
        st.session_state["student_folder_initials"] = st.session_state.pop(
            "_sf_pending"
        )
    if st.session_state.pop("_sf_clear", False):
        st.session_state["student_folder_initials"] = ""

    _labels = _student_labels()
    _conf_ok = _confidential_unlocked()
    _currently_open = st.session_state.get("student_folder_initials", "").strip()

    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.write(
            "Active students are listed below, grouped by program and term — "
            "click a folder to open it. Search by initials, or switch to "
            "archived students."
        )
    with top_r:
        if _currently_open:
            st.write("")
            if st.button("⬅️ All active folders", use_container_width=True):
                st.session_state["_sf_clear"] = True
                st.session_state.pop("_folder_arch", None)
                st.rerun()

    sc1, sc2 = st.columns([1, 3])
    with sc1:
        sf_initials = st.text_input(
            "Or search by initials", max_chars=4, placeholder="e.g. JT",
            key="student_folder_initials",
        )

    if sf_initials.strip():
        ini = sf_initials.strip().upper()
        recs = fetch_archive(
            include_confidential=_conf_ok,
            student_initials=ini,
            limit=500,
        )
        _display = _labels.get(ini, ini)

        # Student status controls (register-linked students only)
        from datetime import date as _date
        _reg_active = {s["initials"]: s for s in fetch_register("active")}
        _reg_archived = {s["initials"]: s for s in fetch_register("archived")}

        if ini in _reg_active:
            _s = _reg_active[ini]
            sc_a, sc_b = st.columns([3, 1])
            with sc_b:
                if st.button("📦 Archive student", key=f"folder_arch_{ini}"):
                    st.session_state["_folder_arch"] = ini
            if st.session_state.get("_folder_arch") == ini:
                st.warning(
                    f"⚠️ Archive student **{_display}**? Use this when their "
                    "placement has ended. Their folder and every document "
                    "move to 📦 Archived students — nothing is deleted, and "
                    "they can be reactivated if they return."
                )
                fa1, fa2, fa3 = st.columns([2, 1, 1])
                with fa1:
                    _fa_exit = st.date_input(
                        "Exit date", value=_date.today(), key=f"fa_exit_{ini}"
                    )
                with fa2:
                    st.write("")
                    if st.button("Yes, archive", key=f"fa_yes_{ini}",
                                 type="primary"):
                        if set_student_status(_s["id"], "archived", _fa_exit):
                            st.session_state.pop("_folder_arch", None)
                            st.rerun()
                with fa3:
                    st.write("")
                    if st.button("Cancel", key=f"fa_no_{ini}"):
                        st.session_state.pop("_folder_arch", None)
                        st.rerun()
        elif ini in _reg_archived:
            _s = _reg_archived[ini]
            sc_a, sc_b = st.columns([3, 1])
            with sc_a:
                st.caption(
                    f"📦 Archived student · exited {_s.get('exit_date') or '—'}"
                )
            with sc_b:
                if st.button("↩️ Reactivate", key=f"folder_react_{ini}"):
                    if set_student_status(_s["id"], "active", None):
                        st.rerun()
        else:
            # Unlinked folder — offer to move its documents to a student
            st.info(
                "🗂️ **This folder isn't linked to the register** — usually a "
                "document filed under mis-derived initials. Move everything "
                "into the correct student's folder:"
            )
            _all_reg = fetch_register(None)
            _mv_pairs = [
                (_labels.get(s["initials"], s["initials"]), s["initials"])
                for s in _all_reg
            ]
            _mv_seen = set()
            _mv_pairs = [
                p for p in _mv_pairs
                if not (p[1] in _mv_seen or _mv_seen.add(p[1]))
            ]
            mv1, mv2 = st.columns([3, 1])
            with mv1:
                _mv_choice = st.selectbox(
                    "Move all documents into",
                    ["— choose student —"] + [p[0] for p in _mv_pairs],
                    key=f"mv_to_{ini}",
                )
            with mv2:
                st.write("")
                if st.button("🔀 Move documents", key=f"mv_go_{ini}",
                             type="primary"):
                    _target = next(
                        (p[1] for p in _mv_pairs if p[0] == _mv_choice), None
                    )
                    if not _target:
                        st.warning("Choose the student to move them into.")
                    else:
                        _moved = rename_student(ini, _target)
                        st.success(
                            f"Moved {_moved} document(s) into {_mv_choice}."
                        )
                        st.session_state["_sf_pending"] = _target
                        st.rerun()

        # --- Upload straight into this folder (works for active AND
        # archived students — nothing here is gated on register status) ---
        with st.expander("➕ Upload a document to this folder", expanded=False):
            with st.form(f"folder_upload_{ini}", clear_on_submit=True):
                fu = st.file_uploader(
                    "Document",
                    type=["docx", "pdf", "xlsx", "pptx", "png", "jpg"],
                    key=f"fu_file_{ini}",
                )
                fu1, fu2 = st.columns(2)
                with fu1:
                    fu_title = st.text_input("Title *", key=f"fu_title_{ini}")
                    fu_doc_type = st.selectbox(
                        "Document type *", DOC_TYPES, key=f"fu_type_{ini}"
                    )
                with fu2:
                    fu_term = st.selectbox(
                        "Term *", TERMS, index=1, key=f"fu_term_{ini}"
                    )
                    fu_year = st.selectbox(
                        "Year *", [2026, 2025], key=f"fu_year_{ini}"
                    )
                fu_conf = st.checkbox(
                    "Confidential 🔒", value=False, key=f"fu_conf_{ini}"
                )
                fu_notes = st.text_area(
                    "Notes (optional)", height=68, key=f"fu_notes_{ini}"
                )
                fu_submit = st.form_submit_button(
                    f"Archive to {_display}", type="primary"
                )

            if fu_submit:
                if not fu or not fu_title.strip():
                    st.warning("A file and a title are both required.")
                elif fu_conf and not _conf_ok:
                    st.warning(
                        "Unlock the confidential section (Browse tab) before "
                        "archiving confidential documents."
                    )
                else:
                    fu_rec = archive_document(
                        source_tool="Manual Upload",
                        doc_type=fu_doc_type,
                        title=fu_title.strip(),
                        file_bytes=fu.getvalue(),
                        filename=fu.name,
                        student_initials=ini,
                        term=fu_term,
                        year=int(fu_year),
                        confidential=fu_conf,
                        created_by=user_email,
                        notes=fu_notes.strip() or None,
                    )
                    if fu_rec:
                        st.success(f"Archived to {_display}: {fu_rec['title']}")
                        st.rerun()

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
        # Directory: every registered student (even with no docs yet),
        # grouped by Program (JP / PY / SY) then by term, plus any folders
        # that exist outside the register. Archived students are hidden
        # behind an explicit toggle so the default view is always "all
        # active" — this tab never silently reopens the last folder you
        # had open, because sf_initials is empty every time you land here
        # with nothing searched/selected.
        all_recs = fetch_archive(include_confidential=_conf_ok, limit=1000)
        counts: dict[str, int] = {}
        recs_by_ini: dict[str, list] = {}
        for r in all_recs:
            if r.get("student_initials"):
                counts[r["student_initials"]] = counts.get(r["student_initials"], 0) + 1
                recs_by_ini.setdefault(r["student_initials"], []).append(r)

        _PROGRAM_ORDER = ["JP", "PY", "SY"]

        def _term_sort_key(term, year):
            try:
                yy = int(year) if year else 0
            except Exception:
                yy = 0
            t_idx = TERMS.index(term) if term in TERMS else -1
            return (yy, t_idx)

        def _current_term_key(ini):
            """(term, year) of this student's most recently added document,
            used to place their folder under the right term — or None if
            they have no documents archived yet."""
            recs_ = recs_by_ini.get(ini, [])
            if not recs_:
                return None
            best = max(recs_, key=lambda r: _term_sort_key(r.get("term"), r.get("year")))
            t, y = best.get("term"), best.get("year")
            return (t, y) if t else None

        def _term_key_label(key):
            if key is None:
                return "No documents yet"
            t, y = key
            return f"{t} {y}" if y else t

        def _folder_grid(entries, key_prefix):
            cols = st.columns(4)
            for i, (ini, label) in enumerate(entries):
                with cols[i % 4]:
                    if st.button(label, key=f"{key_prefix}_{i}_{ini}",
                                 use_container_width=True):
                        st.session_state["_sf_pending"] = ini
                        st.rerun()

        def _render_by_program_term(students, key_prefix, badge):
            by_program: dict[str, list] = {}
            for s in students:
                prog = s.get("program") or "No program set"
                by_program.setdefault(prog, []).append(s)

            ordered_programs = sorted(
                by_program,
                key=lambda p: (
                    _PROGRAM_ORDER.index(p) if p in _PROGRAM_ORDER else 99, p
                ),
            )
            for prog in ordered_programs:
                st.markdown(f"#### {prog}")
                by_term: dict = {}
                for s in by_program[prog]:
                    by_term.setdefault(_current_term_key(s["initials"]), []).append(s)

                term_keys = sorted(
                    (k for k in by_term if k is not None),
                    key=lambda k: _term_sort_key(k[0], k[1]),
                    reverse=True,
                )
                if None in by_term:
                    term_keys.append(None)

                for tkey in term_keys:
                    st.caption(_term_key_label(tkey))
                    entries = [
                        (
                            s["initials"],
                            f"{badge} {_labels.get(s['initials'], s['initials'])} "
                            f"({counts.get(s['initials'], 0)})",
                        )
                        for s in by_term[tkey]
                    ]
                    _folder_grid(entries, f"{key_prefix}_{prog}_{_term_key_label(tkey)}")
                st.write("")

        seen = set()
        _active_reg = [
            s for s in fetch_register("active")
            if not (s["initials"] in seen or seen.add(s["initials"]))
        ]
        _archived_reg = [
            s for s in fetch_register("archived")
            if not (s["initials"] in seen or seen.add(s["initials"]))
        ]
        other_entries = [
            (ini, f"📁 {_labels.get(ini, ini)} ({counts[ini]})")
            for ini in sorted(counts) if ini not in seen
        ]

        st.markdown("### 👥 Active students — by program & term")
        if _active_reg:
            _render_by_program_term(_active_reg, "cur", "📁")
        else:
            st.info(
                "No active students yet — add them in the Student Register "
                "when they arrive, and their folders will appear here."
            )

        st.divider()
        _show_archived = st.session_state.get("sf_show_archived", False)
        if st.button(
            "📦 Hide archived folders" if _show_archived
            else "📦 Show archived folders"
        ):
            st.session_state["sf_show_archived"] = not _show_archived
            st.rerun()

        if _show_archived:
            st.markdown("### 📦 Archived students — by program & term")
            st.caption(
                "Students who have transitioned out — every document remains "
                "here, fully accessible, and you can still upload to their "
                "folder."
            )
            if _archived_reg:
                _render_by_program_term(_archived_reg, "arc", "📦")
            else:
                st.info("No archived students yet.")

        if other_entries:
            st.divider()
            st.markdown("### 🗂️ Folders not linked to the register")
            st.caption(
                "Documents filed under initials with no register entry — "
                "merge these into the right student via Admin, or add the "
                "student to the register."
            )
            _folder_grid(other_entries, "oth")

# ===========================================================================
# ADD DOCUMENT (manual upload — for docs created outside the portal)
# ===========================================================================
with tab_add:
    st.write(
        "Most documents are archived automatically by their source tool. "
        "Use this form to archive something created outside the portal "
        "(e.g. a term report or a scanned plan)."
    )

    _add_labels = _student_labels()
    _active_set = {s["initials"] for s in fetch_register("active")}
    _archived_set = {s["initials"] for s in fetch_register("archived")}

    _seen_add = set()
    _dedup_students = [
        s for s in fetch_register(None)
        if not (s["initials"] in _seen_add or _seen_add.add(s["initials"]))
    ]

    _option_map = {"— Not student-linked —": None}
    _student_options = ["— Not student-linked —"]
    for s in _dedup_students:
        _badge = "📦" if s["initials"] in _archived_set else "🟢"
        _label = f"{_badge} {_add_labels.get(s['initials'], s['initials'])}"
        if s["initials"] in _archived_set:
            _label += " (archived)"
        _student_options.append(_label)
        _option_map[_label] = s["initials"]
    _student_options.append("Other (type initials manually)")

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
            m_ini = _option_map.get(m_student)

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
