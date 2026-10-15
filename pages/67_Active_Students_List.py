"""
67_Active_Student_List.py  —  CLC-LBU portal
Live list of currently active students, kept up to date from the Allocation
Meetings Tool, downloadable each Wednesday in the Head Office spreadsheet layout
(the "CLC Allocation List").

Where the data comes from
  allocation_students  (Allocation Meetings Tool)  — new allocations, extensions,
                       end dates, flags. Read only; this page never writes to it.
  active_student_list  (this page)                 — who is on the list, plus the
                       details the Allocation tool doesn't record (EDID, review date,
                       PREV, SC, BSC) and any corrections Admin makes here.

A student is on the list when they're Allocated, not marked inactive, and their end
date (extended end date if an extension was approved) hasn't passed.

Needs: allocation_list_utils.py (repo root),
       data/allocation_list/allocation_list_template.xlsx,
       supabase_schema_active_student_list.sql run once in Supabase.
"""

import io
import os
import re
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from allocation_list_utils import (
    FLAG_FIELDS, FLAG_LABELS, NewStudent, build_list, norm_edid, norm_name,
    norm_program, read_list, term_and_week, to_date,
)

st.set_page_config(page_title="Active Student List", page_icon="📋", layout="wide")

# ---------------------------------------------------------------------------
# Access: admin / leadership only (student names, EDIDs, DOBs)
# ---------------------------------------------------------------------------
import confidential_auth  # noqa: E402

_gate = next(
    (getattr(confidential_auth, n) for n in (
        "require_confidential_password", "require_confidential_auth", "check_confidential_password",
        "confidential_gate", "require_password", "check_password",
    ) if callable(getattr(confidential_auth, n, None))),
    None,
)
if _gate is None:
    st.error("Couldn't find the password check in confidential_auth.py — page locked.")
    st.stop()
if _gate() is False:
    st.stop()

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
ALLOC_TABLE = "allocation_students"
LIST_TABLE = "active_student_list"
SETTINGS_TABLE = "active_student_list_settings"
TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "allocation_list",
    "allocation_list_template.xlsx",
)
if not os.path.exists(TEMPLATE_PATH):  # page may sit at repo root in some setups
    TEMPLATE_PATH = os.path.join("data", "allocation_list", "allocation_list_template.xlsx")

# Allocation tool flag column -> list flag key
FLAG_MAP = {
    "flag_eald": "ealD", "flag_atsi": "atsi", "flag_dcp_involvement": "dcp",
    "flag_child_in_care": "sic", "flag_swd": "swd", "flag_speech_and_lang": "speech_language",
    "flag_asd": "asd", "flag_adhd": "adhd", "flag_intellectual": "intellectual",
    "flag_learning_difficulty": "language_difficulty",
    "flag_sensory_processing": "sensory_processing", "flag_medication": "medication",
}
LIST_FLAGS = [f for f in FLAG_FIELDS if f != "sc"]  # SC has its own tick column


@st.cache_resource
def sb():
    from supabase import create_client
    return create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _yes(v) -> bool:
    return str(v or "").strip().lower() in {"yes", "y", "true", "1"}


def _iso(d):
    return d.isoformat() if isinstance(d, date) else None


def _first_name(full) -> str:
    return str(full or "").strip().split(" ")[0] if full else ""


def _gender(v) -> str:
    g = str(v or "").strip()[:1].upper()
    return g if g in ("M", "F") else ""


def _year(v) -> str:
    s = str(v or "").strip()
    return "Rec" if s.lower() in ("r", "rec", "reception") else s


def _iesp_category(r: dict):
    if _yes(r.get("flag_9plusraap")):
        return "9"
    for i in range(9, 0, -1):
        if _yes(r.get(f"flag_category_{i}")):
            return str(i)
    return ""


def _labels(keys) -> str:
    return ", ".join(FLAG_LABELS[k] for k in LIST_FLAGS if k in (keys or []))


_LABEL_TO_KEY = {v.lower(): k for k, v in FLAG_LABELS.items()}


def _keys(text) -> list[str]:
    out = []
    for part in str(text or "").split(","):
        k = _LABEL_TO_KEY.get(part.strip().lower())
        if k and k != "sc" and k not in out:
            out.append(k)
    return out


def _friday(term: int, week: int) -> date | None:
    """Friday of a given term/week (used when an exit date is unreadable)."""
    from allocation_list_utils import SA_TERMS
    terms = SA_TERMS.get(date.today().year)
    if not terms or not (1 <= term <= 4):
        return None
    start = terms[term - 1][0]
    monday = start - timedelta(days=start.weekday())
    return monday + timedelta(weeks=week - 1, days=4)


def wednesday_of(d: date) -> date:
    """The coming Wednesday (today if it's Wednesday) — the Head Office send day."""
    return d + timedelta(days=(2 - d.weekday()) % 7)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    try:
        rows = sb().table(SETTINGS_TABLE).select("*").execute().data or []
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


def save_setting(key, value):
    sb().table(SETTINGS_TABLE).upsert({"key": key, "value": value}).execute()


def load_alloc() -> dict[str, dict]:
    rows = sb().table(ALLOC_TABLE).select("*").eq("outcome", "Allocated").execute().data or []
    return {str(r["id"]): r for r in rows}


def load_list() -> list[dict]:
    return sb().table(LIST_TABLE).select("*").execute().data or []


def alloc_values(a: dict) -> dict:
    """The Allocation Meetings Tool's view of a student, in list terms."""
    ext = to_date(a.get("proposed_extension_finish_date")) if a.get("extension_status") == "Approved" else None
    return {
        "student_name": str(a.get("student_name") or "").strip(),
        "dob": to_date(a.get("date_of_birth")),
        "school": str(a.get("school") or "").strip(),
        "year_level": _year(a.get("year_level")),
        "gender": _gender(a.get("gender")),
        "program": norm_program(a.get("program")),
        "start_date": to_date(a.get("start_after")),
        "exit_date": to_date(a.get("finishing_date")),
        "ext_end_date": ext,
        "focus_teacher": _first_name(a.get("actioned_by") or a.get("case_worker")),
        "flags": [k for db, k in FLAG_MAP.items() if _yes(a.get(db))],
        "bsc": str(a.get("bse") or "").strip(),
        "iesp": _iesp_category(a),
    }


OVERRIDABLE = ["student_name", "dob", "school", "year_level", "gender", "program",
               "start_date", "exit_date", "ext_end_date", "focus_teacher", "flags"]
LOCAL_ONLY = ["edid", "review", "prev", "sc"]
FALLBACK = ["bsc", "iesp"]  # local value if typed, else the Allocation tool's


def merged(row: dict, alloc: dict | None) -> dict:
    """One student as shown on the list: overrides > Allocation tool values."""
    base = alloc_values(alloc) if alloc else {}
    m = {"_id": row["id"], "_alloc_id": row.get("allocation_id"), "_base": base,
         "_inactive": False, "_actual_finish": None}
    for f in OVERRIDABLE:
        v = row.get(f)
        if f in ("dob", "start_date", "exit_date", "ext_end_date"):
            v = to_date(v)
        m[f] = v if v not in (None, "") else base.get(f, [] if f == "flags" else None)
    for f in LOCAL_ONLY:
        m[f] = row.get(f)
    for f in FALLBACK:
        m[f] = row.get(f) or base.get(f) or ""
    m["removed"] = bool(row.get("removed"))
    if alloc:
        m["_inactive"] = str(alloc.get("current_status") or "").strip().lower() == "inactive"
        m["_actual_finish"] = to_date(alloc.get("actual_finish_date"))
    m["_source"] = "Allocation tool" if alloc else ("Manual" if not row.get("allocation_id") else "⚠️ Allocation record gone")
    return m


def end_of(m: dict) -> date | None:
    return m.get("ext_end_date") or m.get("exit_date")


def is_active(m: dict, as_of: date) -> bool:
    if m["removed"] or m["_inactive"]:
        return False
    if m["_actual_finish"] and m["_actual_finish"] < as_of:
        return False
    end = end_of(m)
    week_monday = as_of - timedelta(days=as_of.weekday())
    return not (end and end < week_monday)


def auto_add_new(alloc: dict[str, dict], rows: list[dict], baseline: date) -> int:
    """Create list rows for students allocated since the list started."""
    have = {str(r.get("allocation_id")) for r in rows if r.get("allocation_id")}
    new = []
    for aid, a in alloc.items():
        if aid in have:
            continue
        md, sd = to_date(a.get("meeting_date")), to_date(a.get("start_after"))
        if (md and md >= baseline) or (sd and sd >= baseline):
            new.append({"allocation_id": aid})
    if new:
        sb().table(LIST_TABLE).insert(new).execute()
    return len(new)


def to_student(m: dict) -> NewStudent:
    return NewStudent(
        name=m["student_name"] or "", edid=m.get("edid") or "", program=m.get("program") or "",
        dob=m.get("dob"), school=m.get("school") or "", year=m.get("year_level") or "",
        gender=m.get("gender") or "", start_date=m.get("start_date"), exit_date=m.get("exit_date"),
        review=m.get("review") or "", prev=m.get("prev") or None,
        iesp=int(m["iesp"]) if str(m.get("iesp") or "").isdigit() else (m.get("iesp") or None),
        flags={k: True for k in (m.get("flags") or [])} | ({"sc": True} if m.get("sc") else {}),
        focus_teacher=m.get("focus_teacher") or "", bsc=m.get("bsc") or "",
        ext_end_date=m.get("ext_end_date"),
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.title("📋 Active Student List")
st.caption(
    "Live list of current students. New allocations and approved extensions come across "
    "from the Allocation Meetings Tool automatically; students drop off once their end date passes."
)

try:
    settings = load_settings()
    alloc = load_alloc()
    rows = load_list()
except Exception as e:
    st.error(
        f"Couldn't load from Supabase: {e}\n\nIf this is the first run, run "
        "`supabase_schema_active_student_list.sql` in the Supabase SQL editor."
    )
    st.stop()

baseline = to_date(settings.get("baseline_date"))
if baseline:
    added_now = auto_add_new(alloc, rows, baseline)
    if added_now:
        rows = load_list()
        st.toast(f"{added_now} newly allocated student(s) added to the list")

tab_list, tab_add, tab_import = st.tabs(["📋 Live list", "➕ Add / remove", "📥 Set up (one-off import)"])

# ============================================================================
# LIVE LIST
# ============================================================================
with tab_list:
    if not baseline:
        st.info(
            "The list hasn't been set up yet. Go to **📥 Set up** and import your current "
            "allocation list (e.g. CLC_Allocation_List_Week_2.xlsx) — that becomes the starting point."
        )
    else:

        c1, c2, c3 = st.columns([1.2, 1, 1])
        as_of = c1.date_input(
            "List for", value=wednesday_of(date.today()), format="DD/MM/YYYY",
            help="Usually the Wednesday it's sent to Head Office. Students whose end date is before "
                 "that week are left off.",
        )
        t, w = term_and_week(as_of)
        t_num = int(t[1:]) if t else 4
        w_num = int(w.split()[-1]) if w else 1
        term = c2.selectbox("Term (header)", [1, 2, 3, 4], index=t_num - 1)
        week = c3.number_input("Week (header)", 1, 11, w_num)

        all_m = [merged(r, alloc.get(str(r.get("allocation_id")))) for r in rows]
        active = [m for m in all_m if is_active(m, as_of)]
        recently_ended = [
            m for m in all_m
            if not is_active(m, as_of) and not m["removed"] and end_of(m)
            and as_of - timedelta(days=21) <= end_of(m) < as_of
        ]

        k = st.columns(5)
        k[0].metric("Active", len(active))
        for i, (p, lbl) in enumerate([("JP", "Junior Primary"), ("PY", "Primary"), ("SY", "Seniors")], 1):
            k[i].metric(lbl, sum(1 for m in active if m["program"] == p))
        k[4].metric("Missing EDID", sum(1 for m in active if not m.get("edid")))

        no_prog = [m for m in active if m["program"] not in ("JP", "PY", "SY")]
        if no_prog:
            st.warning("No program set for: " + ", ".join(m["student_name"] for m in no_prog)
                       + " — set it below or they won't appear in the download.")

        st.caption(
            "Edit cells directly, then **Save changes**. Changes here are kept on this list only — "
            "the Allocation Meetings Tool isn't changed. Flags: comma-separated, e.g. ASD, ADHD."
        )

        edited_all = []
        for p, lbl in [("JP", "Junior Primary"), ("PY", "Primary"), ("SY", "Seniors"), ("", "No program set")]:
            group = [m for m in active if (m["program"] or "") == p] if p else no_prog
            if not group:
                continue
            group.sort(key=lambda m: (m.get("start_date") or date.max, (m["student_name"] or "").lower()))
            st.markdown(f"#### {lbl} ({len(group)})")
            df = pd.DataFrame([{
                "_id": m["_id"],
                "Student": m["student_name"], "EDID": m.get("edid") or "", "DOB": m.get("dob"),
                "School": m.get("school") or "", "Yr": m.get("year_level") or "", "M/F": m.get("gender") or "",
                "Start": m.get("start_date"), "Exit": m.get("exit_date"), "Extended to": m.get("ext_end_date"),
                "Review": m.get("review") or "", "PREV": m.get("prev") or "", "IESP": m.get("iesp") or "",
                "Flags": _labels(m.get("flags")), "SC": bool(m.get("sc")),
                "Focus teacher": m.get("focus_teacher") or "", "BSC": m.get("bsc") or "",
                "Program": m["program"] or "", "Source": m["_source"],
            } for m in group])
            ed = st.data_editor(
                df, hide_index=True, use_container_width=True, key=f"ed_{p or 'none'}",
                column_order=[c for c in df.columns if c != "_id"],
                column_config={
                    "DOB": st.column_config.DateColumn(format="D/MM/YYYY"),
                    "Start": st.column_config.DateColumn(format="D/MM/YYYY"),
                    "Exit": st.column_config.DateColumn(format="D/MM/YYYY"),
                    "Extended to": st.column_config.DateColumn(format="D/MM/YYYY", help="Approved extension end date"),
                    "M/F": st.column_config.SelectboxColumn(options=["M", "F", ""], width="small"),
                    "Program": st.column_config.SelectboxColumn(options=["JP", "PY", "SY"], width="small"),
                    "SC": st.column_config.CheckboxColumn(width="small"),
                    "Review": st.column_config.TextColumn(help="e.g. 22 Oct @ 1pm"),
                    "Source": st.column_config.TextColumn(disabled=True),
                },
            )
            edited_all.append(ed)

        if st.button("💾 Save changes", type="primary"):
            by_id = {m["_id"]: m for m in active}
            updates = 0
            for ed in edited_all:
                for _, r in ed.iterrows():
                    m = by_id[r["_id"]]
                    base = m["_base"]
                    new = {
                        "student_name": str(r["Student"] or "").strip(), "dob": to_date(r["DOB"]),
                        "school": str(r["School"] or "").strip(), "year_level": _year(r["Yr"]),
                        "gender": r["M/F"] or "", "program": r["Program"] or "",
                        "start_date": to_date(r["Start"]), "exit_date": to_date(r["Exit"]),
                        "ext_end_date": to_date(r["Extended to"]),
                        "focus_teacher": str(r["Focus teacher"] or "").strip(), "flags": _keys(r["Flags"]),
                    }
                    payload = {
                        "edid": norm_edid(r["EDID"]) or None, "review": str(r["Review"] or "").strip() or None,
                        "prev": str(r["PREV"] or "").strip() or None, "sc": bool(r["SC"]),
                        "bsc": (str(r["BSC"] or "").strip() or None) if str(r["BSC"] or "").strip() != base.get("bsc", "") else None,
                        "iesp": (str(r["IESP"] or "").strip() or None) if str(r["IESP"] or "").strip() != base.get("iesp", "") else None,
                    }
                    for f, v in new.items():
                        same = (sorted(v) == sorted(base.get(f) or [])) if f == "flags" else (v or None) == (base.get(f) or None)
                        if base and same:
                            payload[f] = None            # matches Allocation tool: no override
                        else:
                            payload[f] = _iso(v) if isinstance(v, date) else (v if v not in ("", []) else None)
                    payload["updated_at"] = datetime.now().astimezone().isoformat()
                    sb().table(LIST_TABLE).update(payload).eq("id", m["_id"]).execute()
                    updates += 1
            st.success(f"Saved {updates} row(s).")
            st.rerun()

        if recently_ended:
            with st.expander(f"👋 Finished in the last 3 weeks ({len(recently_ended)}) — not on this list"):
                st.dataframe(pd.DataFrame([{
                    "Student": m["student_name"], "Program": m["program"],
                    "Ended": end_of(m), "Source": m["_source"],
                } for m in recently_ended]), hide_index=True, use_container_width=True)
                st.caption("If someone here should still be on the list, give them an extended end date "
                           "in the Allocation Meetings Tool, or add one on the ➕ tab.")

        st.markdown("---")
        st.subheader("⬇️ Download for Head Office")
        missing = [m["student_name"] for m in active if not m.get("edid")]
        if missing:
            st.warning(f"No EDID yet for: {', '.join(missing)} (they'll be listed with the EDID blank).")
        if not os.path.exists(TEMPLATE_PATH):
            st.error("Template missing: data/allocation_list/allocation_list_template.xlsx")
        else:
            result = build_list(open(TEMPLATE_PATH, "rb").read(),
                                [to_student(m) for m in active], f"T{term}", int(week))
            for n, why in result.skipped:
                st.warning(f"Not in download — {n}: {why}")
            fname = f"CLC_Allocation_List_T{term}_Week_{int(week)}.xlsx"
            st.download_button(
                f"⬇️ Download {fname}  ({result.total} students)", result.workbook_bytes, file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary",
            )

# ============================================================================
# ADD / REMOVE
# ============================================================================
with tab_add:
    st.subheader("➕ Add a student by hand")
    st.caption("Only for students who aren't in the Allocation Meetings Tool — "
               "anyone allocated there appears on the list by themselves.")
    with st.form("add_manual", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        name = a1.text_input("Student name *")
        edid = a2.text_input("EDID")
        prog = a3.selectbox("Program *", ["", "JP", "PY", "SY"])
        b1, b2, b3, b4 = st.columns(4)
        dob = b1.date_input("DOB", value=None, format="DD/MM/YYYY", min_value=date(2005, 1, 1))
        school = b2.text_input("School")
        yr = b3.text_input("Year (Rec, 1–10)")
        gender = b4.selectbox("Gender", ["", "M", "F"])
        c1_, c2_, c3_, c4_ = st.columns(4)
        start = c1_.date_input("Start date", value=None, format="DD/MM/YYYY")
        exit_ = c2_.date_input("Exit date", value=None, format="DD/MM/YYYY")
        ext = c3_.date_input("Extended to", value=None, format="DD/MM/YYYY")
        review = c4_.text_input("Review", placeholder="22 Oct @ 1pm")
        d1, d2, d3 = st.columns(3)
        teacher = d1.text_input("Focus teacher")
        bsc = d2.text_input("BSC")
        flags = d3.multiselect("Flags", [FLAG_LABELS[k] for k in LIST_FLAGS])
        if st.form_submit_button("Add to list", type="primary"):
            if not name.strip() or not prog:
                st.error("Name and program are required.")
            else:
                sb().table(LIST_TABLE).insert({
                    "student_name": name.strip(), "edid": norm_edid(edid) or None, "program": prog,
                    "dob": _iso(dob), "school": school.strip() or None, "year_level": _year(yr) or None,
                    "gender": gender or None, "start_date": _iso(start), "exit_date": _iso(exit_),
                    "ext_end_date": _iso(ext), "review": review.strip() or None,
                    "focus_teacher": teacher.strip() or None, "bsc": bsc.strip() or None,
                    "flags": _keys(", ".join(flags)),
                }).execute()
                st.success(f"Added {name.strip()}.")
                st.rerun()

    st.markdown("---")
    st.subheader("➖ Take a student off the list")
    st.caption("Use this for a student who has left early. It doesn't change the Allocation Meetings Tool.")
    today_m = [merged(r, alloc.get(str(r.get("allocation_id")))) for r in rows]
    on_now = sorted([m for m in today_m if is_active(m, date.today())], key=lambda m: m["student_name"] or "")
    if on_now:
        pick = st.selectbox("Student", on_now, format_func=lambda m: f"{m['student_name']} ({m['program']})")
        reason = st.text_input("Reason (optional)")
        if st.button("Remove from list"):
            sb().table(LIST_TABLE).update({"removed": True, "removed_reason": reason or None}).eq("id", pick["_id"]).execute()
            st.success(f"Removed {pick['student_name']}.")
            st.rerun()

    removed = [m for m in today_m if m["removed"]]
    if removed:
        with st.expander(f"Removed students ({len(removed)})"):
            back = st.selectbox("Put back on the list", removed, format_func=lambda m: m["student_name"])
            if st.button("Restore"):
                sb().table(LIST_TABLE).update({"removed": False, "removed_reason": None}).eq("id", back["_id"]).execute()
                st.rerun()

# ============================================================================
# ONE-OFF IMPORT
# ============================================================================
with tab_import:
    st.subheader("📥 Start the live list from your current spreadsheet")
    st.caption(
        "Upload the latest allocation list (e.g. CLC_Allocation_List_Week_2.xlsx). Each student is "
        "matched to the Allocation Meetings Tool by name. Matched students stay linked, so future "
        "extensions and end-date changes flow through; anyone not found is added as a manual entry. "
        "EDIDs, review dates, PREV, SC and BSC are brought across. From then on, anyone newly "
        "allocated in the Allocation tool is added automatically."
    )
    if baseline:
        st.info(f"The list was set up on {baseline.strftime('%d/%m/%Y')}. Importing again updates "
                "matching students' details and adds anyone missing — nothing is deleted.")
    up = st.file_uploader("Allocation list (.xlsx)", type=["xlsx"], key="import_up")
    if up:
        try:
            src = read_list(up.getvalue())
        except Exception as e:
            st.error(f"Couldn't read that file: {e}")
            st.stop()

        by_name = {}
        for aid, a in alloc.items():
            by_name.setdefault(norm_name(a.get("student_name")), []).append((aid, a))
        existing_alloc = {str(r.get("allocation_id")): r for r in rows if r.get("allocation_id")}
        existing_manual = {norm_name(r.get("student_name")): r for r in rows if not r.get("allocation_id")}

        plan, notes = [], []
        for s in src:
            cands = by_name.get(norm_name(s["student_name"]), [])
            if len(cands) > 1 and s["dob"]:
                cands = [c for c in cands if to_date(c[1].get("date_of_birth")) == s["dob"]] or cands
            if len(cands) > 1:  # several referrals: take the most recent allocation
                cands.sort(key=lambda c: str(c[1].get("meeting_date") or ""), reverse=True)
            match = cands[0] if cands else None
            if not s["exit_date"] and s["_exit_tw"]:
                mt = re.match(r"(?i)\s*T\s*(\d)\D+(\d+)", s["_exit_tw"])
                if mt:
                    s["exit_date"] = _friday(int(mt.group(1)), int(mt.group(2)))
                    notes.append(f"{s['student_name']}: exit date unreadable — used Friday of {s['_exit_tw']}.")
            if s["_fixed"]:
                notes.append(f"{s['student_name']}: {', '.join(s['_fixed'])} date had day/month swapped — corrected.")
            plan.append((s, match))

        st.dataframe(pd.DataFrame([{
            "Program": s["program"], "Student": s["student_name"],
            "Match": "✅ Allocation tool" if m else "➕ Manual entry",
            "Start": s["start_date"], "Exit": s["exit_date"], "Extended to": s["ext_end_date"],
        } for s, m in plan]), hide_index=True, use_container_width=True)
        for n in notes:
            st.caption("• " + n)

        if st.button(f"Import {len(plan)} students", type="primary"):
            done = 0
            for s, match in plan:
                local = {
                    "edid": s["edid"] or None, "review": s["review"] or None, "prev": s["prev"] or None,
                    "sc": "sc" in s["flags"], "bsc": s["bsc"] or None, "iesp": s["iesp"] or None,
                }
                full = {
                    "student_name": s["student_name"], "dob": _iso(s["dob"]), "school": s["school"] or None,
                    "year_level": _year(s["year_level"]) or None, "gender": s["gender"] or None,
                    "program": s["program"], "start_date": _iso(s["start_date"]),
                    "exit_date": _iso(s["exit_date"]), "ext_end_date": _iso(s["ext_end_date"]),
                    "focus_teacher": s["focus_teacher"] or None,
                    "flags": [f for f in s["flags"] if f != "sc"],
                }
                if match:
                    aid, a = match
                    base = alloc_values(a)
                    # the list wins wherever it differs: it's what Head Office has been sent
                    over = {}
                    for f, v in full.items():
                        bv = base.get(f)
                        bv = _iso(bv) if isinstance(bv, date) else bv
                        if f == "flags":
                            if v and sorted(v) != sorted(bv or []):
                                over[f] = v
                        elif v not in (None, "") and str(v) != str(bv or ""):
                            over[f] = v
                    payload = {"allocation_id": aid, **local, **{f: None for f in full}, **over}
                    if aid in existing_alloc:
                        sb().table(LIST_TABLE).update(payload).eq("id", existing_alloc[aid]["id"]).execute()
                    else:
                        sb().table(LIST_TABLE).insert(payload).execute()
                else:
                    payload = {**local, **full}
                    ex = existing_manual.get(norm_name(s["student_name"]))
                    if ex:
                        sb().table(LIST_TABLE).update(payload).eq("id", ex["id"]).execute()
                    else:
                        sb().table(LIST_TABLE).insert(payload).execute()
                done += 1
            if not baseline:
                # two weeks back, so last meeting's allocations (not yet on the spreadsheet)
                # are picked up too; anyone already finished is filtered out by end date
                save_setting("baseline_date", (date.today() - timedelta(days=14)).isoformat())
            st.success(f"Imported {done} students. The live list is ready.")
            st.rerun()
