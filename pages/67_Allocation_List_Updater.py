"""
67_Allocation_List_Updater.py  —  CLC-LBU portal
Adds newly allocated students (saved by the Allocation Meetings Tool) into the
weekly CLC Allocation List spreadsheet.

Flow
 1. Admin uploads this week's list (e.g. CLC_Allocation_List_Week_2.xlsx)
 2. Tool reads allocated students from Supabase and shows which ones are NOT
    on the list yet (matched by name — the Allocation tool has no EDID)
 3. Admin ticks who to add, checks/edits details, picks the new week
 4. Downloads next week's list (…_Week_3.xlsx) with students in the right
    JP / Primary / Seniors block, numbering + total + page header updated

Nothing is written back to Supabase; the uploaded file is never changed.
"""

import io
import os
from datetime import date, timedelta

import openpyxl
import pandas as pd
import streamlit as st

from allocation_list_utils import (
    FLAG_LABELS, NewStudent, add_students, current_term_week,
    existing_edids, existing_names, norm_edid, norm_name, norm_program,
    next_week_filename, to_date,
)

st.set_page_config(page_title="Allocation List Updater", page_icon="📋", layout="wide")

# ---------------------------------------------------------------------------
# Access: admin / leadership only (student names and DOBs)
# Uses the portal's shared confidential password gate.
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
# Source: the Allocation Meetings Tool's table (33_Allocation_Meetings_Tool.py)
# ---------------------------------------------------------------------------
ALLOCATION_TABLE = "allocation_students"

# Allocation tool flag column  ->  allocation list column (see allocation_list_utils.COL)
FLAG_MAP = {
    "flag_eald": "ealD",
    "flag_atsi": "atsi",
    "flag_dcp_involvement": "dcp",
    "flag_child_in_care": "sic",
    "flag_swd": "swd",
    "flag_speech_and_lang": "speech_language",
    "flag_asd": "asd",
    "flag_adhd": "adhd",
    "flag_intellectual": "intellectual",
    "flag_learning_difficulty": "language_difficulty",
    "flag_sensory_processing": "sensory_processing",
    "flag_medication": "medication",
}


@st.cache_resource
def _supabase():
    from supabase import create_client
    return create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))


def _yes(v) -> bool:
    return str(v or "").strip().lower() in {"yes", "y", "true", "1"}


def _iesp_category(r: dict):
    """Highest funding category ticked (9+ RAAP counts as 9), else blank."""
    if _yes(r.get("flag_9plusraap")):
        return 9
    for i in range(9, 0, -1):
        if _yes(r.get(f"flag_category_{i}")):
            return i
    return None


def _first_name(full) -> str:
    return str(full or "").strip().split(" ")[0] if full else ""


@st.cache_data(ttl=60)
def load_allocated() -> list[dict]:
    rows = (
        _supabase().table(ALLOCATION_TABLE).select("*")
        .eq("outcome", "Allocated").execute().data or []
    )
    out = []
    for r in rows:
        out.append({
            "Add": True,
            "Program": norm_program(r.get("program")),
            "Student": str(r.get("student_name") or "").strip(),
            "EDID": "",
            "DOB": to_date(r.get("date_of_birth")),
            "School": str(r.get("school") or ""),
            "Year": str(r.get("year_level") or ""),
            "Gender": str(r.get("gender") or "")[:1].upper() if str(r.get("gender") or "")[:1].upper() in ("M", "F") else "",
            "Start date": to_date(r.get("start_after")),
            "Exit date": to_date(r.get("finishing_date")),
            "Review": "",
            "Focus teacher": _first_name(r.get("actioned_by") or r.get("case_worker")),
            "BSC": str(r.get("bse") or ""),
            "IESP": _iesp_category(r),
            "Flags": [FLAG_LABELS[col] for db, col in FLAG_MAP.items() if _yes(r.get(db))],
            "_finished": to_date(r.get("actual_finish_date")),
            "_meeting": to_date(r.get("meeting_date")),
        })
    return out


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.title("📋 Allocation List Updater")
st.caption("Adds students allocated in the Allocation Meetings Tool to the weekly CLC Allocation List.")

up = st.file_uploader("1. Upload this week's allocation list", type=["xlsx"])
if not up:
    st.info("Upload the current list (e.g. CLC_Allocation_List_Week_2.xlsx) to begin.")
    st.stop()

xlsx_bytes = up.getvalue()
try:
    _ws = openpyxl.load_workbook(io.BytesIO(xlsx_bytes)).worksheets[0]
    on_list = existing_edids(_ws)
    names_on_list = existing_names(_ws)
except Exception as e:  # wrong file / layout changed
    st.error(f"Couldn't read that file: {e}")
    st.stop()

counts = {p: sum(1 for v in on_list.values() if v == p) for p in ("JP", "PY", "SY")}
c1, c2, c3, c4 = st.columns(4)
c1.metric("On list", len(on_list))
c2.metric("JP", counts["JP"])
c3.metric("Primary", counts["PY"])
c4.metric("Seniors", counts["SY"])

try:
    allocated = load_allocated()
except Exception as e:
    st.error(f"Couldn't load allocations from Supabase: {e}")
    allocated = []

# Only students who still have a placement ahead of them and aren't on the list yet
today = date.today()
show_all = st.toggle(
    "Include older allocations",
    help="Off: hides students whose placement has finished, whose end date is more than a week "
         "ago, or who were allocated more than a term ago.",
)


def _current(a) -> bool:
    if a["_finished"] and a["_finished"] < today:
        return False
    if a["Exit date"] and a["Exit date"] < today - timedelta(days=7):
        return False
    if not a["Exit date"] and a["_meeting"] and a["_meeting"] < today - timedelta(weeks=11):
        return False
    return True


new = [
    a for a in allocated
    if norm_name(a["Student"]) not in names_on_list and (show_all or _current(a))
]

st.subheader("2. New students to add")
if not new:
    st.success("Everyone currently allocated in the Allocation Meetings Tool is already on this list.")
    st.stop()

st.caption(
    f"{len(new)} allocated student(s) aren't on this list yet (matched by name). Untick anyone who "
    "shouldn't be added. **Type in each EDID** — the Allocation tool doesn't record it. Add the review "
    "date and fix anything else here; Program decides the block (JP / PY / SY)."
)
df = pd.DataFrame(new).drop(columns=["_finished", "_meeting"])
df["Flags"] = df["Flags"].apply(lambda x: ", ".join(x))
edited = st.data_editor(
    df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Add": st.column_config.CheckboxColumn(width="small"),
        "Program": st.column_config.SelectboxColumn(options=["JP", "PY", "SY"], required=True, width="small"),
        "EDID": st.column_config.TextColumn(help="Type the student's EDID, e.g. 110182084P"),
        "DOB": st.column_config.DateColumn(format="D/MM/YYYY"),
        "Start date": st.column_config.DateColumn(format="D/MM/YYYY"),
        "Exit date": st.column_config.DateColumn(format="D/MM/YYYY"),
        "Gender": st.column_config.SelectboxColumn(options=["M", "F", ""], width="small"),
        "Review": st.column_config.TextColumn(help="e.g. 22 Oct @ 1pm"),
        "IESP": st.column_config.NumberColumn(help="Funding category (1–9)", width="small"),
        "Flags": st.column_config.TextColumn(help="Comma-separated, e.g. ASD, ADHD"),
    },
    key="new_students",
)

missing_edid = edited[edited["Add"] & (edited["EDID"].fillna("").str.strip() == "")]
if len(missing_edid):
    st.warning(
        f"{len(missing_edid)} ticked student(s) have no EDID yet — they'll still be added, "
        "with the EDID cell left blank."
    )
for e in edited["EDID"].fillna(""):
    if norm_edid(e) and norm_edid(e) in on_list:
        st.warning(f"EDID {norm_edid(e)} is already on the list — that student will be skipped.")

st.subheader("3. Week for the new list")
# Default: the week after the uploaded list (from its page header), else this week
import re  # noqa: E402

_hdr = " ".join(filter(None, [_ws.oddHeader.center.text, _ws.oddHeader.left.text, _ws.oddHeader.right.text]))
_m = re.search(r"(?i)TERM\s*(\d)\s*WEEK\s*(\d+)", _hdr)
if _m:
    t_default, w_default = int(_m.group(1)), int(_m.group(2)) + 1
    if w_default > 11:
        t_default, w_default = min(t_default + 1, 4), 1
else:
    term_now, week_now = current_term_week()
    t_default = int(term_now[1:]) if term_now else 4
    w_default = int(week_now.split()[-1]) if week_now else 1
a, b = st.columns(2)
term = a.selectbox("Term", [1, 2, 3, 4], index=t_default - 1)
week = b.number_input("Week", min_value=1, max_value=11, value=w_default)

label_to_flag = {v.lower(): k for k, v in FLAG_LABELS.items()}
students = []
for _, r in edited[edited["Add"]].iterrows():
    flags = {}
    for part in str(r["Flags"] or "").split(","):
        k = label_to_flag.get(part.strip().lower())
        if k:
            flags[k] = True
    students.append(NewStudent(
        name=r["Student"], edid=r["EDID"] or "", program=r["Program"] or "",
        dob=to_date(r["DOB"]), school=r["School"] or "", year=r["Year"] or "", gender=r["Gender"] or "",
        start_date=to_date(r["Start date"]), exit_date=to_date(r["Exit date"]),
        review=r["Review"] or "", flags=flags,
        iesp=int(r["IESP"]) if pd.notna(r["IESP"]) else None,
        focus_teacher=r["Focus teacher"] or "", bsc=r["BSC"] or "",
    ))

if st.button(f"Build list with {len(students)} new student(s)", type="primary", disabled=not students):
    result = add_students(xlsx_bytes, students, header_term=f"T{term}", header_week=int(week))
    if result.added:
        st.success(
            f"Added {len(result.added)}: "
            + ", ".join(f"{n} ({p})" for n, p in result.added)
            + f". Total allocated is now {result.total}."
        )
    for n, why in result.skipped:
        st.warning(f"Skipped {n}: {why}")
    fname = next_week_filename(up.name)
    st.download_button(
        f"⬇️ Download {fname}", result.workbook_bytes, file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption("Remember to also add new students to the Student Register and create their OneDrive folder.")
