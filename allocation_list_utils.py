"""
allocation_list_utils.py
Writes newly allocated students into the CLC Allocation List workbook
(e.g. CLC_Allocation_List_Week_2.xlsx) without breaking its layout.

Layout it expects (sheet "Student Information"):
  Row 2            column headings
  "JUNIOR PRIMARY" section header row  -> student rows -> spare blank rows
  "PRIMARY"        section header row  -> student rows
  "SENIORS"        section header row  -> student rows
  "TOTAL STUDENT ALLOCATED" row (count in column E)

Sections are found by scanning column A, so the tool keeps working if rows
are added or removed by hand.
"""

from __future__ import annotations

import copy
import io
import re
from dataclasses import dataclass
from datetime import date, datetime

import openpyxl
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.utils import get_column_letter, range_boundaries

SHEET_NAME = "Student Information"

# Section header text in column A  ->  program code
SECTION_HEADERS = {
    "JUNIOR PRIMARY": "JP",
    "PRIMARY": "PY",
    "SENIORS": "SY",
}
TOTAL_LABEL = "TOTAL STUDENT ALLOCATED"

# Program aliases accepted from the allocation data
PROGRAM_ALIASES = {
    "JP": "JP", "JUNIOR PRIMARY": "JP", "JUNIOR": "JP",
    "PY": "PY", "PRIMARY": "PY", "PRIMARY YEARS": "PY",
    "SY": "SY", "SENIOR": "SY", "SENIORS": "SY", "SENIOR YEARS": "SY",
}

# Column letters in the allocation list
COL = {
    "num": "A", "name": "B", "edid": "C", "dob": "D", "school": "E",
    "year": "F", "male": "G", "female": "H",
    "start_term": "I", "start_week": "J", "start_date": "K",
    "review": "L",
    "exit_term": "M", "exit_week": "N", "exit_date": "O",
    "ext_term_week": "P", "ext_end_date": "Q",
    "prev": "R",
    "ealD": "S", "atsi": "T", "dcp": "U", "sic": "V", "iesp": "W",
    "swd": "X", "speech_language": "Y", "asd": "Z", "adhd": "AA",
    "intellectual": "AB", "language_difficulty": "AC",
    "sensory_processing": "AD", "sc": "AE", "medication": "AF",
    "focus_teacher": "AG", "bsc": "AH",
}
FLAG_FIELDS = [
    "ealD", "atsi", "dcp", "sic", "swd", "speech_language", "asd", "adhd",
    "intellectual", "language_difficulty", "sensory_processing", "sc",
    "medication",
]
FLAG_LABELS = {
    "ealD": "EALD", "atsi": "ATSI", "dcp": "DCP Involve", "sic": "SIC",
    "swd": "SWD", "speech_language": "Speech and Language", "asd": "ASD",
    "adhd": "ADHD", "intellectual": "Intellectual",
    "language_difficulty": "LNG Diff", "sensory_processing": "Sensory Proces",
    "sc": "SC", "medication": "Medication",
}
LAST_COL = "AH"

# ---------------------------------------------------------------------------
# SA Department for Education term dates.  UPDATE EACH YEAR.
# (start = first day of Week 1, end = last day of term)
# ---------------------------------------------------------------------------
SA_TERMS = {
    2026: [
        (date(2026, 1, 27), date(2026, 4, 10)),
        (date(2026, 4, 27), date(2026, 7, 3)),
        (date(2026, 7, 20), date(2026, 9, 25)),
        (date(2026, 10, 12), date(2026, 12, 11)),
    ],
    2027: [
        (date(2027, 1, 27), date(2027, 4, 9)),
        (date(2027, 4, 26), date(2027, 7, 2)),
        (date(2027, 7, 19), date(2027, 9, 24)),
        (date(2027, 10, 11), date(2027, 12, 10)),
    ],
}


def term_and_week(d: date | None) -> tuple[str, str]:
    """Return ("T4", "Wk 1") for a date, or ("", "") if outside a known term."""
    if not d:
        return "", ""
    for terms in SA_TERMS.values():
        for i, (start, end) in enumerate(terms, start=1):
            if start <= d <= end:
                # Week 1 starts on the Monday of the term's first week
                monday = start.toordinal() - start.weekday()
                week = (d.toordinal() - monday) // 7 + 1
                return f"T{i}", f"Wk {week}"
    return "", ""


def current_term_week(today: date | None = None) -> tuple[str, str]:
    return term_and_week(today or date.today())


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------
def to_date(value) -> date | None:
    """Accept date/datetime/ISO string/'d/m/yyyy' and return a date."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:19] if "T" in s else s, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def is_yes(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"y", "yes", "true", "1", "x", "✓"}


def norm_edid(value) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def norm_program(value) -> str:
    """Accepts JP / 'Junior Primary' / 'Junior Primary (JP)' etc."""
    v = str(value or "").strip().upper()
    m = re.search(r"\((JP|PY|SY)\)", v)
    if m:
        return m.group(1)
    return PROGRAM_ALIASES.get(v, "")


def year_cell(value):
    """Keep 'Rec' as text, year numbers as numbers (matches the existing list)."""
    s = str(value or "").strip()
    if not s:
        return None
    if s.lower() in {"r", "rec", "reception", "0"}:
        return "Rec"
    s = re.sub(r"(?i)^(yr|year)\s*", "", s)
    return int(s) if s.isdigit() else s


# ---------------------------------------------------------------------------
# Student record
# ---------------------------------------------------------------------------
@dataclass
class NewStudent:
    name: str
    edid: str
    program: str                 # JP / PY / SY
    dob: date | None = None
    school: str = ""
    year: str = ""
    gender: str = ""             # "M" / "F" / ""
    start_date: date | None = None
    exit_date: date | None = None
    review: str = ""             # free text, e.g. "22 Oct @ 1pm"
    prev: str | int | None = None
    iesp: str | int | None = None
    flags: dict | None = None    # {"asd": True, ...}
    focus_teacher: str = ""
    bsc: str = ""

    def problems(self) -> list[str]:
        out = []
        if not self.name.strip():
            out.append("no student name")
        if self.program not in ("JP", "PY", "SY"):
            out.append("program not JP / PY / SY")
        return out


# ---------------------------------------------------------------------------
# Workbook structure
# ---------------------------------------------------------------------------
@dataclass
class Section:
    program: str
    header_row: int
    first_row: int
    last_row: int  # last row belonging to this section (before next header)


def _cell_text(ws, row, col="A") -> str:
    v = ws[f"{col}{row}"].value
    return str(v).strip().upper() if v is not None else ""


def find_layout(ws) -> tuple[list[Section], int]:
    """Return the three sections and the TOTAL row number."""
    headers = []
    total_row = None
    for r in range(1, ws.max_row + 1):
        t = _cell_text(ws, r)
        if t in SECTION_HEADERS:
            headers.append((r, SECTION_HEADERS[t]))
        elif t.startswith("TOTAL"):
            total_row = r
            break
    if total_row is None or len(headers) != 3:
        raise ValueError(
            "Couldn't find the JUNIOR PRIMARY / PRIMARY / SENIORS headings and the "
            "TOTAL row in column A. Is this the CLC Allocation List?"
        )
    sections = []
    for i, (r, prog) in enumerate(headers):
        nxt = headers[i + 1][0] if i + 1 < len(headers) else total_row
        sections.append(Section(prog, r, r + 1, nxt - 1))
    return sections, total_row


def norm_name(value) -> str:
    """'PAYTON  HARVEY ' -> 'payton harvey' (the list mixes upper and title case)."""
    return re.sub(r"[^a-z' -]", "", re.sub(r"\s+", " ", str(value or "").strip().lower()))


def existing_names(ws) -> dict[str, str]:
    """normalised student name -> program for every student already on the list."""
    sections, _ = find_layout(ws)
    found = {}
    for s in sections:
        for r in range(s.first_row, s.last_row + 1):
            n = norm_name(ws[f"{COL['name']}{r}"].value)
            if n:
                found[n] = s.program
    return found


def existing_edids(ws) -> dict[str, str]:
    """EDID -> program for every student already on the list."""
    sections, _ = find_layout(ws)
    found = {}
    for s in sections:
        for r in range(s.first_row, s.last_row + 1):
            e = norm_edid(ws[f"{COL['edid']}{r}"].value)
            if e:
                found[e] = s.program
    return found


def _row_is_empty(ws, r) -> bool:
    return not str(ws[f"{COL['name']}{r}"].value or "").strip() and not norm_edid(
        ws[f"{COL['edid']}{r}"].value
    )


# ---------------------------------------------------------------------------
# Row insertion that keeps merges, heights and conditional formatting intact
# (openpyxl's insert_rows doesn't move any of these on its own)
# ---------------------------------------------------------------------------
def _shift_range(ref: str, at: int, n: int, extend_end_at: int | None) -> str:
    min_col, min_row, max_col, max_row = range_boundaries(ref)
    if min_row >= at:
        min_row += n
        max_row += n
    elif max_row >= at:
        max_row += n
    elif extend_end_at is not None and max_row == extend_end_at:
        max_row += n  # range ended on the section's last row: grow it
    a = f"{get_column_letter(min_col)}{min_row}"
    b = f"{get_column_letter(max_col)}{max_row}"
    return a if a == b else f"{a}:{b}"


_REF = re.compile(r"(?<![A-Za-z$])(\$?)([A-Z]{1,3})(\$?)(\d+)(?![\d(])")


def _shift_formula(f: str, at: int, n: int) -> str:
    """Move row numbers >= at down by n in a conditional-format formula."""
    if f.startswith('"'):
        return f

    def rep(m):
        row = int(m.group(4))
        if row >= at:
            row += n
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{row}"

    return _REF.sub(rep, f)


def insert_rows_keep_format(ws, at: int, n: int, template_row: int):
    """Insert n rows before `at`, styled like template_row."""
    # merges
    merges = [str(m) for m in ws.merged_cells.ranges]
    for m in merges:
        ws.unmerge_cells(m)
    # row heights
    heights = {r: d.height for r, d in ws.row_dimensions.items() if d.height}
    # conditional formatting
    old_cf = ws.conditional_formatting
    cf_rules = []
    for cf in old_cf:
        refs = str(cf.sqref).split()
        cf_rules.append((refs, cf.rules))

    ws.insert_rows(at, n)
    tmpl = template_row + n if template_row >= at else template_row

    for m in merges:
        ws.merge_cells(_shift_range(m, at, n, None))

    for r in sorted(heights, reverse=True):
        if r >= at:
            ws.row_dimensions[r + n].height = heights[r]
    tmpl_h = heights.get(template_row)
    for i in range(n):
        ws.row_dimensions[at + i].height = tmpl_h

    new_cf = ConditionalFormattingList()
    for refs, rules in cf_rules:
        shifted = " ".join(_shift_range(x, at, n, at - 1) for x in refs)
        # rule formulas are relative to the first range's top-left cell
        moved = range_boundaries(refs[0])[1] >= at
        for rule in rules:
            if moved and rule.formula:
                rule.formula = [_shift_formula(f, at, n) for f in rule.formula]
            new_cf.add(shifted, rule)
    ws.conditional_formatting = new_cf

    max_col = openpyxl.utils.column_index_from_string(LAST_COL)
    for i in range(n):
        for c in range(1, max_col + 1):
            src = ws.cell(tmpl, c)
            dst = ws.cell(at + i, c)
            if src.has_style:
                dst._style = copy.copy(src._style)


# ---------------------------------------------------------------------------
# Writing a student
# ---------------------------------------------------------------------------
def _write_student(ws, r: int, s: NewStudent):
    def put(key, value):
        ws[f"{COL[key]}{r}"] = value if value not in ("", None) else None

    put("name", s.name.strip())
    put("edid", norm_edid(s.edid))
    put("dob", s.dob)
    put("school", s.school.strip())
    put("year", year_cell(s.year))
    g = s.gender.strip().upper()[:1]
    put("male", "y" if g == "M" else None)
    put("female", "y" if g == "F" else None)
    st, sw = term_and_week(s.start_date)
    put("start_term", st)
    put("start_week", sw)
    put("start_date", s.start_date)
    put("review", s.review.strip())
    et, ew = term_and_week(s.exit_date)
    put("exit_term", et)
    put("exit_week", ew)
    put("exit_date", s.exit_date)
    put("prev", s.prev)
    put("iesp", s.iesp)
    for f in FLAG_FIELDS:
        put(f, "y" if (s.flags or {}).get(f) else None)
    put("focus_teacher", s.focus_teacher.strip())
    put("bsc", s.bsc.strip())
    for key in ("dob", "start_date", "exit_date"):
        cell = ws[f"{COL[key]}{r}"]
        if cell.number_format == "General":  # keep each column's own date style
            cell.number_format = "d-mmm" if key == "exit_date" else "d/mm/yyyy"


def set_header_week(ws, term: str, week: int) -> bool:
    """Update the printed page header, e.g. 'TERM 4  WEEK 2' -> 'TERM 4  WEEK 3'."""
    changed = False
    for hdr in (ws.oddHeader, ws.evenHeader, ws.firstHeader):
        for part in (hdr.left, hdr.center, hdr.right):
            if part.text and re.search(r"(?i)TERM\s*\d+\s*WEEK\s*\d+", part.text):
                part.text = re.sub(
                    r"(?i)TERM\s*\d+(\s*)WEEK\s*\d+",
                    lambda m: f"TERM {term.lstrip('Tt')}{m.group(1)}WEEK {week}",
                    part.text,
                )
                changed = True
    return changed


def _renumber_and_total(ws):
    sections, total_row = find_layout(ws)
    total = 0
    for s in sections:
        n = 0
        for r in range(s.first_row, s.last_row + 1):
            if _row_is_empty(ws, r):
                ws[f"{COL['num']}{r}"] = None
            else:
                n += 1
                ws[f"{COL['num']}{r}"] = n
        total += n
    ws[f"E{total_row}"] = total
    return total


@dataclass
class AddResult:
    added: list[tuple[str, str]]      # (name, program)
    skipped: list[tuple[str, str]]    # (name, reason)
    total: int
    workbook_bytes: bytes


def add_students(
    xlsx_bytes: bytes,
    students: list[NewStudent],
    header_term: str | None = None,
    header_week: int | None = None,
) -> AddResult:
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb[SHEET_NAME] if SHEET_NAME in wb.sheetnames else wb.worksheets[0]

    on_list = existing_edids(ws)
    names_on_list = existing_names(ws)
    added, skipped = [], []
    seen, seen_names = set(), set()

    for s in students:
        label = s.name.strip() or "(no name)"
        issues = s.problems()
        if issues:
            skipped.append((label, ", ".join(issues)))
            continue
        e = norm_edid(s.edid)
        nm = norm_name(s.name)
        if (e and (e in on_list or e in seen)) or nm in names_on_list or nm in seen_names:
            skipped.append((label, "already on the list"))
            continue

        sections, _ = find_layout(ws)
        sec = next(x for x in sections if x.program == s.program)
        target = next(
            (r for r in range(sec.first_row, sec.last_row + 1) if _row_is_empty(ws, r)),
            None,
        )
        if target is None:
            # section full: add a row at the bottom of it, styled like the last row
            target = sec.last_row + 1
            insert_rows_keep_format(ws, target, 1, template_row=sec.last_row)
        _write_student(ws, target, s)
        h = ws.row_dimensions[target].height
        if not h or h < 28:
            ws.row_dimensions[target].height = 30  # spare rows are short
        if e:
            seen.add(e)
        seen_names.add(nm)
        added.append((label, s.program))

    total = _renumber_and_total(ws)
    if header_term and header_week:
        set_header_week(ws, header_term, header_week)
    out = io.BytesIO()
    wb.save(out)
    return AddResult(added, skipped, total, out.getvalue())


def next_week_filename(current_name: str) -> str:
    """CLC_Allocation_List_Week_2.xlsx -> CLC_Allocation_List_Week_3.xlsx"""
    m = re.search(r"(?i)(week[_\s-]*)(\d+)", current_name)
    if m:
        return current_name[: m.start(2)] + str(int(m.group(2)) + 1) + current_name[m.end(2):]
    stem = current_name.rsplit(".", 1)[0]
    return f"{stem}_updated.xlsx"
