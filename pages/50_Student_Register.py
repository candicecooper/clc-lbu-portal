"""
48_Student_Register.py — CLC-LBU Student Register
===================================================

Admin-run register of students at the centre:
  • ADD a student when they first arrive (name, initials, program, start date)
  • ARCHIVE a student when they transition out (kept, never deleted)
  • Fix initials if needed — their Document Archive folder moves with them

The Document Archive uses this register to show student names next to
folders and to offer a student picker when archiving documents manually.
Designed to be simple enough to hand to admin staff as a routine job.
"""

from datetime import date

import streamlit as st

from archive_utils import (
    PROGRAMS,
    fetch_archive,
    fetch_register,
    register_student,
    set_student_status,
    update_student_initials,
)

st.set_page_config(page_title="Student Register", page_icon="🧑‍🎓", layout="wide")

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

st.title("🧑‍🎓 Student Register")
st.caption(
    "Add students when they arrive at the centre; archive them when they "
    "transition out. Students are recorded by initials and program only — "
    "no names are stored. The Document Archive builds each student's "
    "folder from this register."
)

user_email = st.session_state.get("user_email", "unknown")

tab_current, tab_add, tab_archived = st.tabs(
    ["👥 Current Students", "➕ Add New Student", "📦 Archived Students"]
)

# ===========================================================================
# ADD NEW STUDENT
# ===========================================================================
with tab_add:
    st.write(
        "Complete this when a student **first arrives** at the centre. "
        "Enter their **initials** (first name + surname, e.g. JT) and "
        "program. If two students would clash, add a third letter "
        "(e.g. first two letters of the surname)."
    )
    with st.form("add_student", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            ns_initials = st.text_input("Student initials *", max_chars=4,
                                        placeholder="e.g. JT")
        with a2:
            ns_program = st.selectbox("Program *", PROGRAMS)
        with a3:
            ns_start = st.date_input("Start date", value=date.today())
        ns_notes = st.text_area("Notes (optional — no student names)", height=68)
        add_submitted = st.form_submit_button("➕ Add student", type="primary")

    if add_submitted:
        if not ns_initials.strip():
            st.warning("The student's initials are required.")
        else:
            rec = register_student(
                initials=ns_initials,
                program=ns_program,
                start_date=ns_start,
                notes=ns_notes,
                created_by=user_email,
            )
            if rec:
                st.success(
                    f"✅ Student **{rec['initials']}** ({rec['program']}) added "
                    "to the register. Their Document Archive folder is ready — "
                    "documents from the tools will file there automatically."
                )

# ===========================================================================
# CURRENT STUDENTS
# ===========================================================================
with tab_current:
    students = fetch_register("active")
    if not students:
        st.info("No active students on the register yet — add the first in the Add New Student tab.")
    else:
        # doc counts per initials (one query, counted client-side)
        _docs = fetch_archive(include_confidential=True, limit=1000)
        _counts: dict[str, int] = {}
        for d in _docs:
            if d.get("student_initials"):
                _counts[d["student_initials"]] = _counts.get(d["student_initials"], 0) + 1

        st.markdown(f"**{len(students)} active student(s)**")
        for s in students:
            sid = s["id"]
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.markdown(f"📁 **{s['initials']}**  ·  {s.get('program') or '—'}")
                    st.caption(
                        f"{s.get('program') or '—'} · started "
                        f"{s.get('start_date') or '—'} · "
                        f"{_counts.get(s['initials'], 0)} archived document(s)"
                    )
                    if s.get("notes"):
                        st.caption(f"📝 {s['notes']}")
                with c2:
                    if st.button("✏️ Change initials", key=f"ini_{sid}"):
                        st.session_state["_edit_ini"] = sid
                with c3:
                    if st.button("📦 Archive student", key=f"arch_{sid}"):
                        st.session_state["_confirm_arch"] = sid

                if st.session_state.get("_edit_ini") == sid:
                    e1, e2, e3 = st.columns([2, 1, 1])
                    with e1:
                        new_ini = st.text_input(
                            "New initials", value=s["initials"], max_chars=4,
                            key=f"new_ini_{sid}",
                        )
                    with e2:
                        st.write("")
                        if st.button("Save", key=f"ini_save_{sid}", type="primary"):
                            if new_ini.strip() and new_ini.strip().upper() != s["initials"]:
                                moved = update_student_initials(
                                    sid, s["initials"], new_ini
                                )
                                st.success(
                                    f"Initials updated; {moved} archived "
                                    "document(s) moved to the new folder."
                                )
                            st.session_state.pop("_edit_ini", None)
                            st.rerun()
                    with e3:
                        st.write("")
                        if st.button("Cancel", key=f"ini_cancel_{sid}"):
                            st.session_state.pop("_edit_ini", None)
                            st.rerun()

                if st.session_state.get("_confirm_arch") == sid:
                    st.warning(
                        f"⚠️ Archive student **{s['initials']}**? Use this when a "
                        "student transitions out of the centre. Their record "
                        "and all archived documents are **kept** — they move "
                        "to the Archived Students tab and can be reactivated "
                        "if the student returns."
                    )
                    ad1, ad2, ad3 = st.columns([2, 1, 2])
                    with ad1:
                        arch_exit = st.date_input(
                            "Exit date", value=date.today(), key=f"exit_{sid}"
                        )
                    with ad2:
                        st.write("")
                        if st.button(
                            "Yes, archive", key=f"arch_yes_{sid}", type="primary"
                        ):
                            if set_student_status(sid, "archived", arch_exit):
                                st.session_state.pop("_confirm_arch", None)
                                st.rerun()
                    with ad3:
                        st.write("")
                        if st.button("Cancel", key=f"arch_no_{sid}"):
                            st.session_state.pop("_confirm_arch", None)
                            st.rerun()

# ===========================================================================
# ARCHIVED STUDENTS
# ===========================================================================
with tab_archived:
    archived = fetch_register("archived")
    if not archived:
        st.info("No archived students yet.")
    else:
        st.write(
            "Students who have transitioned out. Their Document Archive "
            "folders remain fully searchable. Reactivate if a student returns."
        )
        for s in archived:
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"📁 **{s['initials']}** · {s.get('program') or '—'}")
                st.caption(
                    f"{s.get('program') or '—'} · "
                    f"{s.get('start_date') or '—'} → {s.get('exit_date') or '—'}"
                )
            with c2:
                if st.button("↩️ Reactivate", key=f"react_{s['id']}"):
                    if set_student_status(s["id"], "active", None):
                        st.rerun()
