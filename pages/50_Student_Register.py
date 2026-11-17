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
    add_past_students,
    extend_student,
    find_past_students,
    reinitial_register_entry,
    register_aliases,
    set_register_alias,
    lookup_student,
    set_register_status_raw,
    import_from_behaviour,
    import_from_smartar,
    push_register_to_behaviour,
    delete_register_entry,
    merge_register_student,
    update_student_details,
    fetch_archive,
    fetch_register,
    register_student,
    set_student_status,
    update_student_initials,
)


def _d(val):
    """Parse an ISO date string from Supabase into a date (or None)."""
    if not val:
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except Exception:
        return None

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

# ── Result of the last archive: what was filed to the student's folder ─────
_eop = st.session_state.get("_eop_results")
if _eop:
    _icons = {"filed": "✅", "already": "📁", "none": "➖", "failed": "❌"}
    _words = {"filed": "filed now", "already": "already on file",
              "none": "nothing to file", "failed": "NOT filed"}
    _items = _eop.get("items", [])
    _failed = [i for i in _items if i["status"] == "failed"]
    _box = st.error if _failed else st.success
    with st.container(border=True):
        _box(f"🗄️ **{_eop['initials']} archived** — end-of-placement documents:")
        for _i in _items:
            st.markdown(f"{_icons.get(_i['status'], '•')} **{_i['item']}** — "
                        f"{_words.get(_i['status'], _i['status'])}"
                        + (f" · {_i['detail']}" if _i.get("detail") else ""))
        if _eop.get("sync_warnings"):
            st.warning("Could not confirm archiving in: " + "; ".join(_eop["sync_warnings"])
                       + ". Check those tools so the student isn't left active there.")
        if _failed:
            st.caption("Anything marked ❌ can be saved by hand from that tool — the student "
                       "is archived either way. Reactivating and re-archiving also re-runs this.")
        if st.button("Done", key="eop_dismiss"):
            st.session_state.pop("_eop_results", None)
            st.rerun()

with st.expander("🔧 Connection info (for setup/troubleshooting)"):
    from archive_utils import connected_project
    _url = connected_project()
    st.code(_url)
    st.caption(
        "This is the Supabase project the register reads from. If the "
        "register table is missing, run register_setup.sql in **this** "
        "project — the highlighted part of the URL matches the project "
        "ref shown in the Supabase dashboard address bar."
    )

tab_current, tab_add, tab_archived = st.tabs(
    ["👥 Current Students", "➕ Add New Student", "📦 Archived Students"]
)

# ===========================================================================
# ADD NEW STUDENT
# ===========================================================================
with tab_add:
    with st.expander("📥 Import existing students from the Behaviour Analysis tool"):
        st.write(
            "One-off setup: creates a register entry (and archive folder) for "
            "every **active** student already in the Behaviour Analysis tool — "
            "initials, program, year level and placement dates come across "
            "automatically. Students already on the register are skipped, so "
            "it's safe to run more than once."
        )
        ib1, ib2 = st.columns(2)
        with ib1:
            if st.button("📥 Import from Behaviour tool", type="primary",
                         key="import_beh"):
                imported, skipped, problems = import_from_behaviour(user_email)
                st.success(f"Imported {imported}; skipped {skipped} already on the register.")
                for p in problems:
                    st.warning(p)
                if imported:
                    st.rerun()
        with ib2:
            if st.button("📥 Import from SMARTAR Goal tool",
                         key="import_smartar"):
                imported, skipped, problems = import_from_smartar(user_email)
                st.success(f"Imported {imported}; skipped {skipped} already on the register.")
                for p in problems:
                    st.warning(p)
                if imported:
                    st.rerun()
        st.caption(
            "Imported students may be missing program/year details — add "
            "them with ✏️ on each student's card in Current Students."
        )
        st.divider()
        st.write(
            "**📤 Push to Behaviour Analysis** — one-off backfill the other "
            "way: creates a Behaviour Analysis student for every active "
            "register student not already in its list, so data collection "
            "can begin. Safe to run repeatedly."
        )
        if st.button("📤 Push register students to Behaviour Analysis",
                     key="push_beh"):
            _c, _e, _f = push_register_to_behaviour()
            st.success(
                f"Created {_c} student(s) in Behaviour Analysis; "
                f"{_e} already there."
            )
            if _f:
                st.warning("Could not create: " + ", ".join(_f))

    st.write(
        "Complete this when a student **first arrives** at the centre. "
        "Enter their **initials** (first name + surname, e.g. JT) and "
        "program. If two students share initials, add the **second letter of "
        "the surname** to tell them apart (e.g. **B.Hi** for a second student "
        "with initials B.H.)."
    )
    with st.form("add_student", clear_on_submit=True):
        a1, a2 = st.columns(2)
        with a1:
            ns_initials = st.text_input("Student initials *", max_chars=6,
                                        placeholder="e.g. JT  (or B.Hi if initials clash)")
            ns_program = st.selectbox("Program *", PROGRAMS)
            ns_year = st.number_input("Year level *", min_value=0, max_value=12,
                                      value=0, help="Reception = 0")
        with a2:
            ns_start = st.date_input("Start date", value=date.today())
            ns_exit = st.date_input(
                "Planned exit date (end of placement)", value=None,
                help="The register flags the student for archiving once this "
                     "date passes. Placements can be extended later if a "
                     "review grants more time.",
            )
        ns_notes = st.text_area("Notes (optional — no student names)", height=68)
        add_submitted = st.form_submit_button("➕ Add student", type="primary")

    if add_submitted:
        if not ns_initials.strip():
            st.warning("The student's initials are required.")
        else:
            rec = register_student(
                initials=ns_initials,
                program=ns_program,
                year_level=int(ns_year),
                start_date=ns_start,
                planned_exit_date=ns_exit,
                notes=ns_notes,
                created_by=user_email,
            )
            if rec:
                _tools_added = []
                if rec.get("_behaviour_sync") in ("created", "exists"):
                    _tools_added.append("Behaviour Analysis")
                if rec.get("_smartar_sync") in ("created", "exists"):
                    _tools_added.append("SMARTAR Goals")
                _sync_msg = (
                    f" Ready in: {', '.join(_tools_added)}." if _tools_added else ""
                )
                st.success(
                    f"✅ Student **{rec['initials']}** ({rec['program']}) added "
                    "to the register. Their Document Archive folder is ready — "
                    "documents from the tools will file there automatically."
                    + _sync_msg
                )

# ===========================================================================
# CURRENT STUDENTS
# ===========================================================================
with tab_current:
    students = fetch_register("active")
    if not students:
        st.info("No active students on the register yet — add the first in the Add New Student tab.")
    else:
        _today = date.today()
        _overdue = [
            s for s in students
            if _d(s.get("planned_exit_date")) and _d(s["planned_exit_date"]) < _today
        ]
        _due_soon = [
            s for s in students
            if _d(s.get("planned_exit_date"))
            and _today <= _d(s["planned_exit_date"]) <= _today.fromordinal(_today.toordinal() + 14)
        ]
        if _overdue:
            st.error(
                "🚨 **Past planned exit date — action required:** "
                + ", ".join(f"**{s['initials']}**" for s in _overdue)
                + ". Each must be either **archived** (placement ended) or "
                "**extended** (new exit date from their review) below."
            )
        if _due_soon:
            st.warning(
                "📅 Exit date within 14 days: "
                + ", ".join(
                    f"**{s['initials']}** ({_d(s['planned_exit_date']):%d %b})"
                    for s in _due_soon
                )
            )
        # doc counts per initials (one query, counted client-side)
        _docs = fetch_archive(include_confidential=True, limit=1000)
        _counts: dict[str, int] = {}
        for d in _docs:
            if d.get("student_initials"):
                _counts[d["student_initials"]] = _counts.get(d["student_initials"], 0) + 1

        st.markdown(f"**{len(students)} active student(s)**")
        for s in students:
            sid = s["id"]
            _exit = _d(s.get("planned_exit_date"))
            _is_overdue = bool(_exit and _exit < date.today())
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    _flag = " 🚨 **PAST EXIT DATE**" if _is_overdue else ""
                    _yl = f" · Yr {s['year_level']}" if s.get("year_level") is not None else ""
                    st.markdown(f"📁 **{s['initials']}**  ·  {s.get('program') or '—'}{_yl}{_flag}")
                    _ext = (
                        f" · extended ×{s['extension_count']}"
                        f" (was {_d(s.get('previous_exit_date')):%d %b %Y})"
                        if s.get("extension_count") and _d(s.get("previous_exit_date"))
                        else ""
                    )
                    st.caption(
                        f"started {s.get('start_date') or '—'} · planned exit "
                        f"{_exit.strftime('%d %b %Y') if _exit else 'not set'}{_ext} · "
                        f"{_counts.get(s['initials'], 0)} archived document(s)"
                    )
                    if s.get("notes"):
                        st.caption(f"📝 {s['notes']}")
                with c2:
                    if st.button("📅 Extend placement", key=f"ext_{sid}"):
                        st.session_state["_extend"] = sid
                    if st.button("✏️ Edit details", key=f"ini_{sid}"):
                        st.session_state["_edit_ini"] = sid
                    if st.button("🔀 Merge / ❌ Remove", key=f"fix_{sid}"):
                        st.session_state["_fix"] = sid
                with c3:
                    if _is_overdue:
                        st.error("Archive or extend:")
                    if st.button("📦 Archive student", key=f"arch_{sid}",
                                 type="primary" if _is_overdue else "secondary"):
                        st.session_state["_confirm_arch"] = sid

                if st.session_state.get("_extend") == sid:
                    st.info(
                        f"**Extend placement for {s['initials']}** — enter the "
                        "new exit date agreed at their review. The current "
                        f"planned exit ({_exit.strftime('%d %b %Y') if _exit else 'not set'}) "
                        "is kept on record."
                    )
                    x1, x2, x3 = st.columns([2, 1, 1])
                    with x1:
                        new_exit = st.date_input(
                            "New planned exit date",
                            value=_exit or date.today(),
                            key=f"new_exit_{sid}",
                        )
                    with x2:
                        st.write("")
                        if st.button("Save extension", key=f"ext_save_{sid}",
                                     type="primary"):
                            if extend_student(sid, _exit, new_exit):
                                st.session_state.pop("_extend", None)
                                st.rerun()
                    with x3:
                        st.write("")
                        if st.button("Cancel", key=f"ext_cancel_{sid}"):
                            st.session_state.pop("_extend", None)
                            st.rerun()

                if st.session_state.get("_edit_ini") == sid:
                    e1, e2, e3, e4, e5 = st.columns([1.5, 1.5, 1.5, 1, 1])
                    with e1:
                        new_ini = st.text_input(
                            "Initials", value=s["initials"], max_chars=4,
                            key=f"new_ini_{sid}",
                        )
                    with e2:
                        _prog_idx = PROGRAMS.index(s["program"]) if s.get("program") in PROGRAMS else 0
                        new_prog = st.selectbox("Program", PROGRAMS,
                                                index=_prog_idx, key=f"new_prog_{sid}")
                    with e3:
                        new_year = st.number_input(
                            "Year level", min_value=0, max_value=12,
                            value=int(s["year_level"]) if s.get("year_level") is not None else 0,
                            key=f"new_year_{sid}",
                        )
                    with e4:
                        st.write("")
                        if st.button("Save", key=f"ini_save_{sid}", type="primary"):
                            update_student_details(sid, new_prog, int(new_year))
                            if new_ini.strip() and new_ini.strip().upper() != s["initials"]:
                                moved = update_student_initials(
                                    sid, s["initials"], new_ini
                                )
                                st.success(
                                    f"Details updated; {moved} archived "
                                    "document(s) moved to the new folder."
                                )
                            st.session_state.pop("_edit_ini", None)
                            st.rerun()
                    with e5:
                        st.write("")
                        if st.button("Cancel", key=f"ini_cancel_{sid}"):
                            st.session_state.pop("_edit_ini", None)
                            st.rerun()

                if st.session_state.get("_fix") == sid:
                    _docs_n = _counts.get(s["initials"], 0)
                    st.info(
                        f"**Fix duplicate / bad entry — {s['initials']}** "
                        f"({_docs_n} archived document(s)). Merging moves their "
                        "documents into another student's folder and removes "
                        "this entry. Removing deletes just this register entry "
                        "— any documents keep the old initials until merged."
                    )
                    _others = [
                        x["initials"] for x in students if x["id"] != sid
                    ]
                    f1, f2, f3, f4 = st.columns([2, 1.2, 1.2, 1])
                    with f1:
                        merge_target = st.selectbox(
                            "Merge documents into", ["—"] + _others,
                            key=f"merge_to_{sid}",
                        )
                    with f2:
                        st.write("")
                        if st.button("🔀 Merge & remove", key=f"merge_go_{sid}",
                                     type="primary"):
                            if merge_target != "—":
                                moved = merge_register_student(
                                    sid, s["initials"], merge_target
                                )
                                st.success(
                                    f"Merged: {moved} document(s) moved to "
                                    f"{merge_target}; duplicate removed."
                                )
                                st.session_state.pop("_fix", None)
                                st.rerun()
                            else:
                                st.warning("Choose who to merge into.")
                    with f3:
                        st.write("")
                        if st.button("❌ Remove entry only", key=f"rm_go_{sid}"):
                            if delete_register_entry(sid):
                                st.session_state.pop("_fix", None)
                                st.rerun()
                    with f4:
                        st.write("")
                        if st.button("Cancel", key=f"fix_cancel_{sid}"):
                            st.session_state.pop("_fix", None)
                            st.rerun()

                if st.session_state.get("_confirm_arch") == sid:
                    st.warning(
                        f"⚠️ Archive student **{s['initials']}**? Use this when a "
                        "student transitions out of the centre. Their record "
                        "and all archived documents are **kept** — they move "
                        "to the Archived Students tab and can be reactivated "
                        "if the student returns."
                    )

                    # ── Document completeness check ──────────────────────────
                    # doc types the archive step files automatically (if data exists)
                    _AUTO = {"SMARTAR Goals", "Behaviour Report", "Sensory Overview",
                             "Window of Tolerance", "Communication Log Export"}
                    _EXPECTED = [
                        ("SMARTAR Goals", "SMARTAR Goal Report"),
                        ("Behaviour Report", "Behaviour Summary"),
                        ("Sensory Overview", "Sensory Overview"),
                        ("Window of Tolerance", "Window of Tolerance"),
                        ("Safety & Risk Plan", "Safety & Risk Plan"),
                        ("Communication Log Export", "Communication Log"),
                    ]
                    try:
                        _sdocs = fetch_archive(student_initials=s["initials"],
                                               include_confidential=True, limit=1000)
                    except Exception:
                        _sdocs = []
                    _have = {d.get("doc_type") for d in _sdocs}
                    st.markdown("**Document folder check** — what's on file for "
                                f"**{s['initials']}**:")
                    _missing = []
                    for _dt, _label in _EXPECTED:
                        _n = sum(1 for d in _sdocs if d.get("doc_type") == _dt)
                        _on = f"{_n} on file" if _n else "none on file yet"
                        if _dt in {"SMARTAR Goals", "Behaviour Report", "Communication Log Export"}:
                            st.markdown(f"- 🔄 {_label} · {_on} — **a final version will be "
                                        "generated and filed** when you archive")
                        elif _dt in _AUTO:
                            st.markdown(f"- 🔄 {_label} · {_on} — **filed automatically** "
                                        "if one has been created and the archive copy is out of date")
                        elif _dt in _have:
                            st.markdown(f"- ✅ {_label} · {_on}")
                        else:
                            st.markdown(f"- ❌ **{_label} — not in the archive**")
                            _missing.append(_label)
                    _other = [d for d in _sdocs
                              if d.get("doc_type") not in {e[0] for e in _EXPECTED}]
                    if _other:
                        st.caption(f"Plus {len(_other)} other document(s) on file.")
                    if _missing:
                        st.warning(
                            "**" + ", ".join(_missing) + "** can't be filed automatically "
                            "(that builder doesn't keep saved data). If the student has one, "
                            "open the builder and use *Save to archive* first. You can still "
                            "archive without it if it genuinely doesn't apply."
                        )

                    ad1, ad2, ad3 = st.columns([2, 1, 2])
                    with ad1:
                        arch_exit = st.date_input(
                            "Exit date",
                            value=_exit if (_exit and _exit <= date.today()) else date.today(),
                            key=f"exit_{sid}",
                        )
                    with ad2:
                        st.write("")
                        if st.button(
                            "Yes, archive", key=f"arch_yes_{sid}", type="primary"
                        ):
                            with st.spinner(f"Archiving {s['initials']} and filing their "
                                            "end-of-placement documents… (this can take "
                                            "up to a minute)"):
                                _ok = set_student_status(sid, "archived", arch_exit)
                            if _ok:
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
    # ── Past students who never made it onto the register ────────────────
    with st.expander("🔎 Find past students missing from the register",
                     expanded=bool(st.session_state.get("_past_found")
                                   or st.session_state.get("_past_added"))):
        st.caption(
            "Students archived inside the Behaviour Support Tool or SMARTAR, or "
            "who left before the register existed, have no register entry — so "
            "they don't show under *Archived students* in the Document Archive. "
            "This finds them and adds them here **as archived** (never active). "
            "Nothing is changed until you tick students and click Add."
        )
        if st.button("Search for past students", key="past_find"):
            with st.spinner("Checking the Behaviour tool, SMARTAR and the archive…"):
                st.session_state["_past_found"] = find_past_students()
        _pf = st.session_state.get("_past_found")
        if _pf:
            _cands, _notes = _pf
            if not _cands:
                st.success("✅ No missing past students — everyone who has left is on the register.")
            else:
                st.write(f"Found **{len(_cands)}** past student(s) not on the register. "
                         "Untick anyone who shouldn't be added (e.g. a duplicate or a typo).")
                _picked = []
                for _c in _cands:
                    _lbl = (f"**{_c['initials']}** · {_c.get('program') or 'no program'}"
                            + (f" · left {_c['exit_date']}" if _c.get("exit_date") else "")
                            + f" · {_c['docs']} document(s)"
                            + f" — found in: {', '.join(_c['sources'])}")
                    if st.checkbox(_lbl, value=True, key=f"past_{_c['initials']}"):
                        _picked.append(_c)
                if st.button(f"➕ Add {len(_picked)} as archived students",
                             type="primary", disabled=not _picked, key="past_add"):
                    _n, _probs = add_past_students(_picked, user_email)
                    st.session_state.pop("_past_found", None)
                    st.session_state["_past_added"] = (_n, _probs)
                    st.rerun()
            for _nt in _notes:
                st.caption(f"ℹ️ {_nt}")
        _pa = st.session_state.pop("_past_added", None)
        if _pa:
            st.success(f"✅ Added {_pa[0]} past student(s). They now appear under "
                       "*Archived students* here and in the Document Archive.")
            for _pr in _pa[1]:
                st.caption(f"⚠️ {_pr}")

    # ── Look up one student: why aren't they showing? ─────────────────────
    with st.expander("🩺 Look up a student — why isn't someone showing?",
                     expanded=bool(st.session_state.get("_lookup_ini"))):
        _lq = st.text_input("Initials", max_chars=6, placeholder="e.g. EE",
                            key="lookup_q").strip().upper()
        if st.button("Look up", key="lookup_go") and _lq:
            st.session_state["_lookup_ini"] = _lq
        _li = st.session_state.get("_lookup_ini")
        if _li:
            _lk = lookup_student(_li)
            for _e in _lk["errors"]:
                st.caption(f"⚠️ {_e}")
            _reg = _lk["register"]
            _beh, _sma, _docs = _lk["behaviour"], _lk["smartar"], _lk["docs"]

            st.markdown(f"#### {_li}")
            st.markdown("**Student Register:** " + (
                "; ".join(f"initials `{r['initials']}` · {r.get('program') or 'no program'} · "
                          f"status `{r.get('status')}`" for r in _reg) if _reg else "❌ no entry"))
            st.markdown("**Behaviour Support Tool:** " + (
                ", ".join(f"{b.get('program') or '—'} " + ("archived" if b["archived"] else "**active**")
                          for b in _beh) if _beh else "not found"))
            st.markdown("**SMARTAR:** " + (
                ", ".join(f"{m.get('program') or '—'} " + ("**active**" if m["active"] else "inactive")
                          for m in _sma) if _sma else "not found"))
            if _lk.get("aka"):
                st.markdown("**Also used by:** " + ", ".join(
                    f"register student `{a['initials']}` ({a.get('program') or '—'}), who is "
                    f"known as {_li} in the other tools" for a in _lk["aka"]))
            st.markdown("**Document Archive:** " + (
                ", ".join(f"{n} filed under `{k}`" for k, n in _docs.items())
                if _docs else "no documents"))

            st.markdown("**Why, and the fix:**")
            if not _reg:
                _still_active = any(not b["archived"] for b in _beh) or any(m["active"] for m in _sma)
                if _still_active:
                    st.warning(f"{_li} isn't on the register and is still **active** in the "
                               "Behaviour or SMARTAR tool, so *Find past students* leaves them out. "
                               "If they have left, add them as archived below; if they're still "
                               "here, add them on the Add New Student tab.")
                else:
                    st.warning(f"{_li} isn't on the register, so the Document Archive can't "
                               "list them under Archived students.")
                if st.button(f"➕ Add {_li} to the register as an archived student",
                             key="lookup_add"):
                    _prog = next((x.get("program") for x in _beh + _sma if x.get("program")), None)
                    _n, _pr = add_past_students(
                        [{"initials": _li, "program": _prog, "sources": ["manual lookup"]}],
                        user_email)
                    if _n:
                        st.success(f"✅ {_li} added as archived — they'll now show in the "
                                   "Document Archive's Archived view.")
                    for _x in _pr:
                        st.caption(f"⚠️ {_x}")
            else:
                if len(_reg) > 1:
                    # Suggest which to keep: correctly-typed initials, archived, has an exit date
                    _keep = max(_reg, key=lambda r: (r["initials"] == _li,
                                                     str(r.get("status")) == "archived",
                                                     bool(r.get("exit_date"))))
                    _progs = {r.get("program") for r in _reg}
                    _two = len(_progs) > 1 or len(_beh) > 1 or len(_sma) > 1
                    st.warning(
                        f"{_li} has **{len(_reg)} register entries**"
                        + (f" in different programs ({', '.join(sorted(p or '—' for p in _progs))})" if len(_progs) > 1 else "")
                        + ". Which is it?\n\n"
                        "- **Two different students who share these initials** — give one of them "
                        "new initials (e.g. add a letter from their surname) so each gets their own "
                        "folder. Documents stay where they are; if any belong to the renamed "
                        "student, move them in the Document Archive (open the folder → *Move*).\n"
                        "- **The same student entered twice** — remove the extra entry. Documents "
                        "aren't affected.\n\n"
                        "Until this is sorted, the Document Archive shows **one** shared "
                        f"{_li} folder (under the first entry's program).")
                    if _two:
                        st.caption("The Behaviour tool and/or SMARTAR also hold more than one "
                                   f"{_li} record, which suggests two different students.")
                for _n, r in enumerate(_reg, 1):
                    _st = str(r.get("status") or "")
                    _odd_ini = r["initials"] != _li
                    with st.container(border=True):
                        _tag = ""
                        if len(_reg) > 1 and not _two:
                            _tag = " · ⭐ suggested to keep" if r is _keep else " · suggested to remove"
                        st.markdown(f"**Entry {_n}** — initials `{r['initials']}` · "
                                    f"{r.get('program') or 'no program'} · status `{r.get('status')}` · "
                                    f"{r.get('start_date') or '—'} → {r.get('exit_date') or '—'}{_tag}")
                        _aka = register_aliases(r.get("notes"))
                        if _aka:
                            st.caption("Known in the other tools as: **" + ", ".join(_aka) + "** "
                                       f"(their records there are matched using this + program).")
                        _ac1, _ac2 = st.columns([2, 1])
                        with _ac1:
                            _al = st.text_input(
                                "Known by different initials in the other tools? (e.g. their "
                                "initials before they were changed)", max_chars=6,
                                placeholder="e.g. EE", key=f"lookup_aka_{r['id']}")
                        with _ac2:
                            st.write("")
                            if st.button("Save", key=f"lookup_aka_go_{r['id']}",
                                         disabled=not _al.strip()):
                                _okA, _msgA = set_register_alias(r["id"], _al)
                                (st.success if _okA else st.error)(_msgA)
                        if _odd_ini:
                            st.warning(f"Initials are stored as `{r['initials']}` (extra spaces or "
                                       f"lower case), so they don't match `{_li}`.")
                            if st.button(f"Re-save initials as {_li}", key=f"lookup_ini_{r['id']}"):
                                update_student_initials(r["id"], r["initials"], _li)
                                st.success(f"Initials re-saved as {_li} (any documents moved with them).")
                        if _st == "archived":
                            st.caption("Archived ✓ — shows in the Document Archive under "
                                       "📦 Archived students.")
                        elif _st == "active":
                            st.caption("Active — shows under Current Students. If they've left, "
                                       "archive them there (that also files their documents).")
                        else:
                            st.error(f"Status `{r.get('status')}` isn't 'active' or 'archived', "
                                     "so this entry is hidden from **both** lists.")
                            if st.button("Set to archived", key=f"lookup_fix_{r['id']}"):
                                if set_register_status_raw(r["id"], "archived"):
                                    st.success("Fixed — now archived.")
                        if len(_reg) > 1:
                            _rc1, _rc2 = st.columns([2, 1])
                            with _rc1:
                                _ni = st.text_input("Different student? New initials for this entry",
                                                    max_chars=4, placeholder=f"e.g. {_li}J",
                                                    key=f"lookup_newini_{r['id']}")
                            with _rc2:
                                st.write("")
                                if st.button("Give new initials", key=f"lookup_reini_{r['id']}",
                                             disabled=not _ni.strip()):
                                    _ok2, _msg = reinitial_register_entry(r["id"], _ni)
                                    (st.success if _ok2 else st.error)(_msg)
                                    if _ok2:
                                        st.rerun()
                            _ok = st.checkbox("Same student entered twice — remove this entry",
                                              key=f"lookup_delok_{r['id']}")
                            if st.button("🗑️ Remove this entry", key=f"lookup_del_{r['id']}",
                                         disabled=not _ok):
                                if delete_register_entry(r["id"]):
                                    st.success("Duplicate removed.")
                                    st.rerun()
            _variants = [k for k in _docs if k.strip().upper() != _li and "(deleted)" not in k]
            if _variants:
                st.info("Some documents are filed under a different code ("
                        + ", ".join(f"`{v}`" for v in _variants) + "), so they sit in a separate "
                        f"folder. In the Document Archive, open that folder and use *Move to a "
                        f"student* (or Admin → merge folders) to move them into {_li}.")
            if st.button("Clear", key="lookup_clear"):
                st.session_state.pop("_lookup_ini", None)
                st.rerun()

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
                    f"{s.get('start_date') or '—'} → {s.get('exit_date') or '—'}"
                    + (f" · {s['extension_count']} extension(s)" if s.get("extension_count") else "")
                )
            with c2:
                if st.button("↩️ Reactivate", key=f"react_{s['id']}"):
                    if set_student_status(s["id"], "active", None):
                        st.rerun()
