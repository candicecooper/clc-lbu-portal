import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import os
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from supabase import create_client

st.set_page_config(
    page_title="Allocation Meetings - CLC-LBU",
    page_icon="📋",
    layout="wide"
)

@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_supabase()

# ══════════════════════════════════════════════════════════════════════════════
# STATIC LISTS
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
DEFAULT_STAFF_NAMES = ["Ben Sutton", "Jacqui Simpson", "Caitie Hook", "Ben Selga", "Brenton McGorman", "Roisin McIlduff"]

def load_dropdown_list(list_name, default_list):
    """Load an editable dropdown list from Supabase (managed via the Admin tab).
    Falls back to the hardcoded default if the table doesn't exist yet or is empty
    for this list — so the tool never breaks even before the admin table is set up."""
    try:
        result = supabase.table("dropdown_options").select("*") \
            .eq("list_name", list_name).order("sort_order").execute()
        values = [r["option_value"] for r in result.data if r.get("option_value")]
        if values:
            return values
    except Exception:
        pass
    return default_list

STAFF_NAMES = load_dropdown_list("focus_teacher", DEFAULT_STAFF_NAMES)
PROGRAMS = load_dropdown_list("program", DEFAULT_PROGRAMS)
OUTCOMES = ["Allocated", "Not Allocated"]
EXTENSION_OUTCOMES = ["Approved", "Not Approved"]
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
PRIORITY_OPTIONS = ["1", "2", "3", "4", "5"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
YES_NO = ["", "Yes", "No"]
WAITLIST_STATUS_OPTIONS = ["Not Applicable", "On Waitlist", "Declined", "Site Decision", "Site Withdraw"]

DEFAULT_MEDICAL_CONDITION_TYPES = [
    "Anaphylaxis / Severe Allergy", "Asthma", "Diabetes (Type 1)", "Epilepsy / Seizure Disorder",
    "Cardiac Condition", "Genetic / Chromosomal Condition", "Physical Disability",
    "Gastrointestinal Condition", "Autoimmune Condition", "Hearing Impairment",
    "Vision Impairment", "Chronic Pain Condition", "Sleep Disorder", "Continence Condition",
    "Other Medical Condition"
]
MEDICAL_CONDITION_TYPES = load_dropdown_list("medical_condition_type", DEFAULT_MEDICAL_CONDITION_TYPES)

DEFAULT_IESP_OPTIONS = ["No", "Currently Being Reviewed", "IESP Grant"]
IESP_OPTIONS = load_dropdown_list("iesp_funding_option", DEFAULT_IESP_OPTIONS)

# Support flag checkboxes: (Display label, Excel column name, Supabase field name)
BOOL_FLAGS = [
    ("EALD", "Flag_EALD", "flag_eald"),
    ("ATSI / Aboriginal", "Flag_ATSI", "flag_atsi"),
    ("DCP Involvement", "Flag_DCP_involvement", "flag_dcp_involvement"),
    ("Child in Care", "Flag_Child_in_care", "flag_child_in_care"),
    ("Intervention / Custody Order", "Flag_Intervention_Custody_Order", "flag_intervention_custody_order"),
    ("SWD (Student with Disability)", "Flag_SWD", "flag_swd"),
    ("Speech and Language", "Flag_Speech_and_Lang", "flag_speech_and_lang"),
    ("ASD", "Flag_ASD", "flag_asd"),
    ("Intellectual Disability", "Flag_Intellectual", "flag_intellectual"),
    ("Learning Difficulty", "Flag_Learning_Difficulty", "flag_learning_difficulty"),
    ("Sensory Processing", "Flag_Sensory_Processing", "flag_sensory_processing"),
    ("ADHD", "Flag_ADHD", "flag_adhd"),
    ("ODD", "Flag_ODD", "flag_odd"),
    ("PDA", "Flag_PDA", "flag_pda"),
]

FUNDING_CATEGORIES = [(f"Category {i}", f"Flag_Category_{i}", f"flag_category_{i}") for i in range(1, 10)]
FUNDING_CATEGORIES.append(("9+ RAAP", "Flag_9plusRAAP", "flag_9plusraap"))

# Full 74-column export order — must match the real Sheet1 layout exactly
EXPORT_COLUMNS = [
    'Current_Status', 'Student_ID', 'Previous_Referrals', 'Student_Name', 'DOB', 'Gender', 'Year_Level',
    'Referring_School', 'Referral_Date', 'Meeting_Date', 'Meeting_Week', 'Previously_Referred',
    'Allocation_Status', 'Allocated_Program', 'Placement_Start', 'Partnership_Area',
    'Previous_CLC_Placement', 'Previous_Other_LC', 'Other_LC_Name', 'Total_Previous_Placements',
    'Placement_History_Notes', 'Flag_EALD', 'Flag_ATSI', 'Flag_Attendance_Fulltime',
    'Flag_Attendance_Parttime', 'Flag_Intervention_Custody_Order', 'Flag_DCP_involvement',
    'Flag_Child_in_care', 'Flag_IESP_Funding_yes', 'Flag_IESP_Funding_no', 'Flag_Category_1',
    'Flag_Category_2', 'Flag_Category_3', 'Flag_Category_4', 'Flag_Category_5', 'Flag_Category_6',
    'Flag_Category_7', 'Flag_Category_8', 'Flag_Category_9', 'Flag_9plusRAAP', 'Flag_SWD',
    'Flag_Speech_and_Lang', 'Flag_ASD', 'Flag_Intellectual', 'Flag_Learning_Difficulty',
    'Flag_Sensory_Processing', 'Flag_ADHD', 'Flag_ODD', 'Flag_PDA', 'Flag_Medication',
    'Flag_Medical_condition', 'Medical_Condition_Details', 'Medication_Details',
    'Bespoke_Placement', 'Waitlist_Status', 'Waitlist_Date', 'Allocated_From_Waitlist',
    'Extension', 'Extension_Date', 'Exit_Reason', 'Transition_Plan', 'Notes', 'Placement_End',
    'Exclusion_End_Date', 'Proposed_Extension_Finish_Date', 'Extension_Weeks', 'Action_owner',
    'Actual_Finish_Date', 'Extended_Placement', 'Referral_Year', 'Term', 'Extension_Status',
    'Referral_Occurrence', 'Referral_ID', 'BSE', 'Exclusion_Start_Date'
]

# Excel column -> Supabase field. None means the column is left blank on export
# (either an Excel-side formula, or not currently captured by the tool).
FIELD_MAP = {
    'Current_Status': 'current_status', 'Student_ID': None, 'Previous_Referrals': 'previous_referrals',
    'Student_Name': 'student_name', 'DOB': 'date_of_birth', 'Gender': 'gender', 'Year_Level': 'year_level',
    'Referring_School': 'school', 'Referral_Date': 'referral_date', 'Meeting_Date': 'meeting_date',
    'Meeting_Week': 'meeting_week', 'Previously_Referred': 'previously_referred',
    'Allocation_Status': 'outcome', 'Allocated_Program': 'program', 'Placement_Start': 'start_after',
    'Partnership_Area': 'partnership_area', 'Previous_CLC_Placement': 'previous_clc_placement',
    'Previous_Other_LC': 'previous_other_lc', 'Other_LC_Name': 'other_lc_name',
    'Total_Previous_Placements': 'total_previous_placements',
    'Placement_History_Notes': 'placement_history_notes', 'Flag_EALD': 'flag_eald',
    'Flag_ATSI': 'flag_atsi', 'Flag_Attendance_Fulltime': 'flag_attendance_fulltime',
    'Flag_Attendance_Parttime': 'flag_attendance_parttime',
    'Flag_Intervention_Custody_Order': 'flag_intervention_custody_order',
    'Flag_DCP_involvement': 'flag_dcp_involvement', 'Flag_Child_in_care': 'flag_child_in_care',
    'Flag_IESP_Funding_yes': 'flag_iesp_funding_yes', 'Flag_IESP_Funding_no': 'flag_iesp_funding_no',
    'Flag_Category_1': 'flag_category_1', 'Flag_Category_2': 'flag_category_2',
    'Flag_Category_3': 'flag_category_3', 'Flag_Category_4': 'flag_category_4',
    'Flag_Category_5': 'flag_category_5', 'Flag_Category_6': 'flag_category_6',
    'Flag_Category_7': 'flag_category_7', 'Flag_Category_8': 'flag_category_8',
    'Flag_Category_9': 'flag_category_9', 'Flag_9plusRAAP': 'flag_9plusraap', 'Flag_SWD': 'flag_swd',
    'Flag_Speech_and_Lang': 'flag_speech_and_lang', 'Flag_ASD': 'flag_asd',
    'Flag_Intellectual': 'flag_intellectual', 'Flag_Learning_Difficulty': 'flag_learning_difficulty',
    'Flag_Sensory_Processing': 'flag_sensory_processing', 'Flag_ADHD': 'flag_adhd',
    'Flag_ODD': 'flag_odd', 'Flag_PDA': 'flag_pda', 'Flag_Medication': 'flag_medication',
    'Flag_Medical_condition': 'flag_medical_condition',
    'Medical_Condition_Details': 'medical_condition_details', 'Medication_Details': 'medication_details',
    'Bespoke_Placement': 'bespoke_placement', 'Waitlist_Status': 'waitlist_status',
    'Waitlist_Date': 'waitlist_date', 'Allocated_From_Waitlist': 'allocated_from_waitlist',
    'Extension': 'extension', 'Extension_Date': 'extension_date', 'Exit_Reason': 'exit_reason',
    'Transition_Plan': 'transition_plan', 'Notes': 'notes', 'Placement_End': 'finishing_date',
    'Exclusion_End_Date': 'exclusion_end_date',
    'Proposed_Extension_Finish_Date': 'proposed_extension_finish_date',
    'Extension_Weeks': 'extension_weeks', 'Action_owner': 'actioned_by',
    'Actual_Finish_Date': 'actual_finish_date', 'Extended_Placement': 'extended_placement',
    'Referral_Year': 'year', 'Term': 'term', 'Extension_Status': 'extension_status',
    'Referral_Occurrence': None, 'Referral_ID': None, 'BSE': 'bse', 'Exclusion_Start_Date': 'exclusion_start_date',
}

# ══════════════════════════════════════════════════════════════════════════════
# SCHOOL / PARTNERSHIP LIST — loaded from school_partnerships.csv (same folder)
# Falls back to a short embedded list if the file isn't deployed yet, so the
# tool never breaks — but the CSV should sit next to this file for the full list.
# ══════════════════════════════════════════════════════════════════════════════

_FALLBACK_SCHOOLS = {
    "Adelaide Botanic High School": "Adelaide Prospect",
    "Adelaide High School": "Adelaide Prospect",
    "Cowandilla Primary School": "Inner West",
    "Henley Beach Primary School": "Inner West",
    "Mitcham Girls High School": "Mitcham Plains",
    "Prospect High School": "Adelaide Prospect",
}

def _parse_school_csv(source):
    df = pd.read_csv(source, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    if "School" not in df.columns or "Partnership_Area" not in df.columns:
        raise ValueError(f"CSV missing School/Partnership_Area columns — found {list(df.columns)}")
    df = df.dropna(subset=["School"])
    mapping = dict(zip(df["School"].astype(str).str.strip(), df["Partnership_Area"].fillna("").astype(str).str.strip()))
    mapping = {k: v for k, v in mapping.items() if k}
    if not mapping:
        raise ValueError("CSV parsed but produced no rows")
    return mapping

@st.cache_data
def load_school_partnerships():
    """Search several likely locations for school_partnerships.csv so this
    doesn't depend on one exact folder layout. Returns (mapping, path_used)."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "school_partnerships.csv"),
        os.path.join(os.getcwd(), "school_partnerships.csv"),
        os.path.join(os.getcwd(), "pages", "school_partnerships.csv"),
        os.path.join(here, "..", "school_partnerships.csv"),
        os.path.join(here, "pages", "school_partnerships.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return _parse_school_csv(path), path
            except Exception:
                continue

    # Last resort: search recursively under the current working directory
    for root, _dirs, files in os.walk(os.getcwd()):
        if "school_partnerships.csv" in files:
            path = os.path.join(root, "school_partnerships.csv")
            try:
                return _parse_school_csv(path), path
            except Exception:
                continue

    return _FALLBACK_SCHOOLS, None

SCHOOL_PARTNERSHIP_MAP, _schools_csv_path = load_school_partnerships()

# Manual override: if auto-detection failed, let a staff member upload the CSV
# directly for this session so the tool works today regardless of repo layout.
if _schools_csv_path is None:
    st.sidebar.warning(
        f"⚠️ Full school list not found on disk (checked script folder, working "
        f"directory `{os.getcwd()}`, and a recursive search). Showing a short "
        f"fallback list."
    )
    manual_csv = st.sidebar.file_uploader(
        "Upload school_partnerships.csv for this session", type=["csv"], key="manual_school_csv"
    )
    if manual_csv is not None:
        try:
            SCHOOL_PARTNERSHIP_MAP = _parse_school_csv(manual_csv)
            st.sidebar.success(f"✅ Loaded {len(SCHOOL_PARTNERSHIP_MAP)} schools for this session")
        except Exception as e:
            st.sidebar.error(f"Couldn't read that file: {e}")

ALL_SCHOOLS = sorted(SCHOOL_PARTNERSHIP_MAP.keys())
PARTNERSHIP_AREAS = sorted(set(SCHOOL_PARTNERSHIP_MAP.values()))


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

TERM_DATES_2026 = {
    'Term 1': date(2026, 1, 27),
    'Term 2': date(2026, 4, 27),
    'Term 3': date(2026, 7, 20),
    'Term 4': date(2026, 10, 12),
}

def _monday_of_week(d):
    return d - timedelta(days=d.weekday())

def get_current_term_week():
    today = datetime.now().date()
    if today.year == 2026:
        applicable = None
        for term_name, start in TERM_DATES_2026.items():
            if start <= today:
                applicable = (term_name, start)
        if applicable is None:
            return 'Term 1', 1, 2026
        term_name, start = applicable
        weeks_in = ((today - _monday_of_week(start)).days // 7) + 1
        weeks_in = max(1, min(weeks_in, 10))
        return term_name, weeks_in, 2026
    return 'Term 1', 1, today.year

def get_meeting_weeks(term, year):
    return [f"Week {i} {term}" for i in range(1, 11)]

def get_wednesday_date(week_number, term, year):
    start = TERM_DATES_2026.get(term, TERM_DATES_2026['Term 2']) if year == 2026 else TERM_DATES_2026['Term 2']
    week1_monday = _monday_of_week(start)
    return week1_monday + timedelta(days=(week_number - 1) * 7 + 2)

def get_partnership_from_school(school_name):
    return SCHOOL_PARTNERSHIP_MAP.get(school_name, "")

# ══════════════════════════════════════════════════════════════════════════════
# FORM READER — pre-fills the Referral / Extension Request screens from an
# uploaded Word or PDF form. Runs entirely inside this app (no outside service).
# Nothing is saved from here: it only fills the on-screen boxes for review.
# ══════════════════════════════════════════════════════════════════════════════
import re as _re
import difflib as _difflib

_CHK_ON, _CHK_OFF = "☒", "☐"


def _docx_cell_texts(file_bytes):
    """Return one text string per table cell (nested tables kept separate), with
    Word checkboxes rendered as ☒ (ticked) / ☐ (empty). Also returns any text
    outside tables."""
    import docx
    from docx.oxml.ns import qn
    W14 = "http://schemas.microsoft.com/office/word/2010/wordml"

    d = docx.Document(BytesIO(file_bytes))
    w_val = qn("w:val")

    def truthy(el, default=False):
        if el is None:
            return default
        v = el.get(w_val)
        return v not in ("0", "false", "off")

    def emit(el, out):
        for ch in el:
            tag = ch.tag
            if tag == qn("w:tbl") or tag == qn("w:instrText") or tag == qn("w:drawing") \
                    or tag.endswith("}Fallback") or tag == qn("w:delText"):
                continue
            if tag == qn("w:sdt"):
                cb = ch.find(qn("w:sdtPr") + "/{%s}checkbox" % W14)
                if cb is not None:
                    chk = cb.find("{%s}checked" % W14)
                    on = chk is not None and chk.get("{%s}val" % W14) in ("1", "true")
                    out.append(_CHK_ON if on else _CHK_OFF)
                    continue
                content = ch.find(qn("w:sdtContent"))
                if content is not None:
                    emit(content, out)
                continue
            if tag == qn("w:ffData"):
                cb = ch.find(qn("w:checkBox"))
                if cb is not None:
                    c = cb.find(qn("w:checked"))
                    dflt = cb.find(qn("w:default"))
                    on = truthy(c) if c is not None else truthy(dflt)
                    out.append(_CHK_ON if on else _CHK_OFF)
                continue
            if tag == qn("w:t"):
                out.append(ch.text or "")
            elif tag == qn("w:tab"):
                out.append(" ")
            elif tag == qn("w:br"):
                out.append("\n")
            elif tag == qn("w:p"):
                emit(ch, out)
                out.append("\n")
            else:
                emit(ch, out)

    cells = []
    for tc in d.element.body.iter(qn("w:tc")):
        out = []
        emit(tc, out)
        txt = "".join(out)
        txt = _re.sub(r"[ \t ]+", " ", txt)
        txt = _re.sub(r"\n\s*\n+", "\n", txt).strip()
        if txt:
            cells.append(txt)
    loose = []
    for p in d.paragraphs:
        if p.text.strip():
            loose.append(p.text.strip())
    return cells, loose


def _pdf_text_and_fields(file_bytes):
    """Text of a PDF plus any fillable-form field values. Returns (text, fields, n_chars)."""
    from pypdf import PdfReader
    r = PdfReader(BytesIO(file_bytes))
    text = "\n".join((pg.extract_text() or "") for pg in r.pages)
    fields = {}
    try:
        for k, v in (r.get_fields() or {}).items():
            val = v.get("/V")
            if val not in (None, "", "/Off"):
                fields[str(k)] = str(val)
    except Exception:
        pass
    return text, fields, len(text.strip())


def _parse_date_text(s):
    if not s:
        return None
    s = s.strip()
    m = _re.search(r"(\d{1,2})[./\-\s](\d{1,2})[./\-\s](\d{2,4})", s)
    if m:
        d_, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d_)
        except ValueError:
            pass
    try:
        from dateutil import parser as _dp
        return _dp.parse(s, dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


def _after_label(text, label_pattern, stop_patterns=()):
    """Text following `label:` up to the end of the line (or, if the value runs on
    to following lines, up to the next stop label)."""
    m = _re.search(label_pattern + r"\s*:?[ \t]*(.*)", text, flags=_re.I | _re.M)
    if not m:
        return ""
    val = m.group(1).strip()
    if stop_patterns:
        rest = text[m.end(1):]
        for ln in rest.split("\n"):
            if any(_re.search(sp, ln, flags=_re.I) for sp in stop_patterns) or not ln.strip():
                if not ln.strip():
                    continue
                break
            val += " " + ln.strip()
    return _re.sub(r"[_\.]{3,}", "", val).strip(" :-")


def _norm_school(s):
    s = (s or "").lower()
    s = _re.sub(r"[^a-z0-9 ]", " ", s)
    s = _re.sub(r"\b(primary|school|ps|p s|r 7|r 12|r 10|area|college|campus|the)\b", " ", s)
    return _re.sub(r"\s+", " ", s).strip()


def match_school(name, schools):
    """Best match in the 799-school list. Returns (match or '', confident?)."""
    if not name:
        return "", False
    low = {s.lower(): s for s in schools}
    if name.lower() in low:
        return low[name.lower()], True
    nn = _norm_school(name)
    if not nn:
        return "", False
    normed = {s: _norm_school(s) for s in schools}
    exact = [s for s, n in normed.items() if n == nn]
    if len(exact) == 1:
        return exact[0], True
    close = _difflib.get_close_matches(nn, list(set(normed.values())), n=3, cutoff=0.8)
    if close:
        cands = [s for s, n in normed.items() if n == close[0]]
        return cands[0], len(cands) == 1
    return "", False


def match_student(name, records):
    """Match a name from a form to one of the records. Forgiving about middle names,
    'Surname, First' order, extra words and small spelling differences.
    Returns (record or None, confident?)."""
    if not name:
        return None, False
    def toks(n):
        n = (n or "").lower()
        if "," in n:
            last, first = n.split(",", 1)
            n = f"{first} {last}"
        n = _re.sub(r"[^a-z' \-]", " ", n).replace("-", " ")
        return [t for t in n.split() if t not in ("mr", "ms", "miss", "student")]
    tt = toks(name)
    if not tt:
        return None, False
    scored = []
    for r in records:
        rt = toks(r.get("student_name"))
        if not rt:
            continue
        if rt == tt:
            score = 1.0
        elif set(tt) <= set(rt) or set(rt) <= set(tt):
            score = 0.95
        elif tt[0] == rt[0] and tt[-1] == rt[-1]:
            score = 0.93
        else:
            score = _difflib.SequenceMatcher(None, " ".join(tt), " ".join(rt)).ratio()
            if tt[-1] == rt[-1] and score < 0.8:   # same surname, similar first name
                score = max(score, _difflib.SequenceMatcher(None, tt[0], rt[0]).ratio() * 0.9)
        scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] < 0.75:
        return None, False
    top = scored[0][0]
    ties = [r for sc, r in scored if sc >= top - 0.001]
    return scored[0][1], (len(ties) == 1 and top >= 0.9)


def _first_checked(cell, labels):
    for lab in labels:
        if _re.search(_CHK_ON + r"\s*" + lab, cell, flags=_re.I):
            return True
    return False


def parse_referral_docx(file_bytes):
    cells, _ = _docx_cell_texts(file_bytes)
    alltext = "\n".join(cells)
    out, notes = {}, []

    def lab(pattern):
        for c in cells:
            m = _re.match(r"\s*" + pattern + r"\s*:?[ \t]*(.*)", c, flags=_re.I | _re.S)
            if m:
                v = _re.sub(r"[_\.]{3,}", "", m.group(1)).strip()
                return v.split("\n")[0].strip() if v else ""
        return ""

    out["student_name"] = lab(r"Student\s+Name")
    dob_raw = lab(r"Date of Birth")
    out["dob"] = _parse_date_text(dob_raw)
    if dob_raw and not out["dob"]:
        notes.append(f"Couldn't read the date of birth ('{dob_raw}') — please enter it.")
    yl = lab(r"Year level")
    m = _re.search(r"\b(R|Reception|10|[1-9])\b", yl, flags=_re.I)
    out["year_level"] = ("R" if m and m.group(1).lower().startswith("r") else m.group(1)) if m else ""
    out["ed_id"] = lab(r"ED\s*ID")
    out["school_raw"] = lab(r"School")
    out["partnership_raw"] = lab(r"Partnership")

    for c in cells:
        if _re.match(r"\s*Exclusion Dates", c, flags=_re.I):
            continue
    ex_from = ex_to = ""
    for c in cells:
        m1 = _re.match(r"\s*From\s*:?[ \t]*(.*)", c, flags=_re.I | _re.S)
        m2 = _re.match(r"\s*To\s*:?[ \t]*(.*)", c, flags=_re.I | _re.S)
        if m1 and not ex_from:
            ex_from = m1.group(1).strip()
        if m2 and not ex_to:
            ex_to = m2.group(1).strip()
    out["exclusion_start"] = _parse_date_text(ex_from)
    out["exclusion_end"] = _parse_date_text(ex_to)

    # previous LC placement
    prev_cell = next((c for c in cells if _re.search(r"Previous LC placement", c, flags=_re.I)), "")
    prev_names = []
    for nm, label in (("Beafield", "Beafield"), ("Cowandilla", "Cowandilla"), ("Southern", "Southern")):
        if _re.search(_CHK_ON + r"\s*" + label, prev_cell, flags=_re.I):
            prev_names.append(nm)
    out["prev_clc"] = "Cowandilla" in prev_names
    out["prev_other_lc_names"] = [n for n in prev_names if n != "Cowandilla"]
    ym = _re.search(r"Year\s*:?\s*([0-9R,\s/&and]+)$", prev_cell.strip(), flags=_re.I)
    out["prev_year"] = ym.group(1).strip() if ym else ""

    # flags
    flagmap = {
        "flag_eald": r"EALD", "flag_atsi": r"Aboriginal\s*/?\s*TSI",
        "flag_intervention_custody_order": r"Intervention\s*/?\s*Custody",
        "flag_dcp_involvement": r"DCP involvement", "flag_child_in_care": r"Child in Care",
        "flag_swd": r"SWD", "flag_speech_and_lang": r"Speech", "flag_asd": r"ASD",
        "flag_intellectual": r"Intellectual", "flag_learning_difficulty": r"Learning difficulty",
        "flag_sensory_processing": r"Sensory processing", "flag_medication": r"Medication",
        "flag_medical_condition": r"Medical Condition",
    }
    flags = {}
    for k, pat in flagmap.items():
        flags[k] = any(_first_checked(c, [pat]) for c in cells)
    out["flags"] = flags

    attends = next((c for c in cells if _re.search(r"Currently attends", c, flags=_re.I)), "")
    ft = _re.search(r"Full time\s*(" + _CHK_ON + "|" + _CHK_OFF + ")", attends, flags=_re.I)
    pt = _re.search(r"Part time\s*(" + _CHK_ON + "|" + _CHK_OFF + ")", attends, flags=_re.I)
    out["attendance"] = "Full-time" if ft and ft.group(1) == _CHK_ON else \
        "Part-time" if pt and pt.group(1) == _CHK_ON else ""

    iesp = next((c for c in cells if _re.search(r"IESP Funding", c, flags=_re.I)), "")
    out["iesp_yes"] = bool(_re.search(_CHK_ON + r"\s*Yes", iesp, flags=_re.I))
    out["iesp_no"] = bool(_re.search(_CHK_ON + r"\s*No\b", iesp, flags=_re.I))
    out["iesp_grant"] = bool(_re.search(_CHK_ON + r"\s*IESP Grant", iesp, flags=_re.I))
    cats = set()
    for ck, num in _re.findall("(" + _CHK_ON + r")\s*(9\s*\+\s*RAAP|[1-9])(?!\d)", iesp, flags=_re.I):
        cats.add("9plusraap" if "raap" in num.lower() else num)
    out["categories"] = cats

    med = next((c for c in cells if _re.search(r"Medical Condition", c, flags=_re.I)
                and _re.search(r"specify", c, flags=_re.I)), "")
    mm = _re.search(r"specify\s*:?\s*(.*)", med, flags=_re.I | _re.S)
    out["medical_details"] = _re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""

    out["referrer"] = lab(r"School referrer")
    return out, notes


def parse_extension_docx(file_bytes):
    cells, _ = _docx_cell_texts(file_bytes)
    alltext = "\n".join(cells)
    out, notes = {}, []

    def block(label, stops):
        """Text after `label:` that may run over several lines, up to the next label."""
        for c in cells:
            m = _re.search(label + r"\s*:?[ \t]*(.*)", c, flags=_re.I | _re.S)
            if m:
                v = m.group(1)
                for sp in stops:
                    s = _re.search(sp, v, flags=_re.I)
                    if s:
                        v = v[:s.start()]
                v = _re.sub(r"[_\.]{3,}", "", v)
                return _re.sub(r"\s+", " ", v).strip(" :-")
        return ""

    out["form_date"] = _parse_date_text(block(r"^\s*Date", [r"Student", r"School"]))
    out["student_name"] = block(r"Student", [r"ED\s*ID", r"\n"]).split("\n")[0].strip()
    out["ed_id"] = block(r"ED\s*ID", [r"\bSchool\b"])
    out["school_raw"] = block(r"(?<![A-Za-z])School(?! Contact)(?! to)", [r"School Contact", r"ED\s*ID"])
    out["contact"] = block(r"School Contact", [])
    out["exclusion_start"] = _parse_date_text(block(r"Exclusion start date", [r"Exclusion end"]))
    out["exclusion_end"] = _parse_date_text(block(r"Exclusion end date", []))
    req_end_raw = block(r"Requested extension end date(?:\s*\([^)]*\))?", [r"Number of days"])
    out["proposed_finish"] = _parse_date_text(req_end_raw)
    if req_end_raw and not out["proposed_finish"]:
        notes.append(f"Couldn't read the requested end date ('{req_end_raw}').")
    wk_raw = block(r"Number of days\s*/\s*weeks", [r"Reason for"])
    out["weeks_raw"] = wk_raw
    wm = _re.search(r"(\d+(?:\.\d+)?)\s*(week|wk|day)?", wk_raw, flags=_re.I)
    weeks = ""
    if wm:
        unit = (wm.group(2) or "").lower()
        n = float(wm.group(1))
        if unit.startswith("day"):
            weeks = str(max(1, round(n / 5)))
            notes.append(f"The form says '{wk_raw}' — converted to {weeks} week(s) at 5 school days a week. Please check.")
        else:
            weeks = str(int(n)) if n == int(n) else str(n)
    out["weeks"] = weeks
    out["reason"] = block(r"Reason for extension", [r"Intended outcomes"])
    out["outcomes"] = block(r"Intended outcomes of extension", [r"As Principal"])
    return out, notes


def parse_pdf_form(file_bytes, kind):
    """Best-effort for PDFs that still hold real text. Returns (parsed, notes, readable)."""
    text, fields, n = _pdf_text_and_fields(file_bytes)
    if n < 40 and not fields:
        return {}, [], False
    out, notes = {}, []
    def g(pat, stops=()):
        return _after_label(text, pat, stops)
    if kind == "referral":
        out["student_name"] = g(r"Student\s+Name\s*:")
        out["dob"] = _parse_date_text(g(r"Date of Birth\s*:"))
        out["year_level"] = (_re.search(r"\b(R|10|[1-9])\b", g(r"Year level\s*:")) or [None, ""])[1] if g(r"Year level\s*:") else ""
        out["school_raw"] = g(r"(?:^|\s)School\s*:")
        out["exclusion_start"] = _parse_date_text(g(r"(?:^|\s)From\s*:"))
        out["exclusion_end"] = _parse_date_text(g(r"(?:^|\s)To\s*:"))
        out["flags"], out["categories"] = {}, set()
        out["iesp_yes"] = out["iesp_no"] = out["iesp_grant"] = False
        out["attendance"] = ""
        out["prev_clc"] = False
        out["prev_other_lc_names"] = []
        out["medical_details"] = ""
        notes.append("This PDF was read as plain text, so the tick boxes can't be read reliably — "
                     "please set the support flags, funding and medical sections yourself.")
    else:
        out["student_name"] = g(r"(?:^|\s)Student\s*:")
        out["school_raw"] = g(r"(?:^|\s)School\s*:")
        out["exclusion_start"] = _parse_date_text(g(r"Exclusion start date"))
        out["exclusion_end"] = _parse_date_text(g(r"Exclusion end date"))
        out["proposed_finish"] = _parse_date_text(g(r"Requested extension end date(?:\s*\([^)]*\))?"))
        wk = g(r"Number of days\s*/\s*weeks")
        out["weeks_raw"] = wk
        m = _re.search(r"(\d+)", wk)
        out["weeks"] = m.group(1) if m else ""
        out["reason"] = g(r"Reason for extension", [r"Intended outcomes"])
        out["outcomes"] = g(r"Intended outcomes of extension", [r"As Principal"])
    return out, notes, True


def read_uploaded_form(uploaded, kind):
    """Read an uploaded form. Returns (parsed or None, notes, status) where status is
    ok / scan (no readable text) / olddoc / missing (library not installed) / error."""
    name = uploaded.name.lower()
    data = uploaded.getvalue()
    try:
        if name.endswith(".docx"):
            fn = parse_referral_docx if kind == "referral" else parse_extension_docx
            parsed, notes = fn(data)
            return parsed, notes, "ok"
        if name.endswith(".doc"):
            return None, [], "olddoc"
        if name.endswith(".pdf"):
            parsed, notes, readable = parse_pdf_form(data, kind)
            return (parsed, notes, "ok") if readable else (None, [], "scan")
        return None, [], "scan"
    except ImportError as e:
        return None, [str(e)], "missing"
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"], "error"


def show_unreadable_form_message(uploaded, status, notes):
    if status == "scan":
        st.warning(
            "📷 This looks like a scan or photo, so there's no text in it for the tool to read. "
            "It's shown below so you can type the details in from it."
        )
        if uploaded.name.lower().endswith((".png", ".jpg", ".jpeg")):
            st.image(uploaded.getvalue(), use_container_width=True)
    elif status == "olddoc":
        st.warning("This is an old-style .doc file. Open it in Word, choose Save As → Word Document (.docx), then upload that.")
    elif status == "missing":
        st.error("The form-reading add-on isn't installed on the server yet "
                 "(`python-docx`, `pypdf` and `python-dateutil` need to be in requirements.txt). "
                 f"Detail: {' '.join(notes)}")
    else:
        st.error(f"Couldn't read that file. {' '.join(notes)}")


def apply_referral_prefill(p):
    """Fill the Referral screen's boxes from a parsed form. Returns warnings."""
    ss = st.session_state
    warns = []
    ss["ref_name"] = p.get("student_name") or ""
    dob = p.get("dob")
    if dob and date(2000, 1, 1) <= dob <= date.today():
        ss["ref_dob"] = dob
    else:
        ss["ref_dob"] = None
        if dob:
            warns.append(f"Date of birth {dob:%d/%m/%Y} is outside the allowed range — please check it.")
    ss["ref_year"] = p["year_level"] if p.get("year_level") in YEAR_LEVELS else ""
    school, confident = match_school(p.get("school_raw", ""), ALL_SCHOOLS)
    ss["ref_school"] = school
    if p.get("school_raw") and not school:
        warns.append(f"School '{p['school_raw']}' wasn't found in the school list — please choose it.")
    elif school and not confident:
        warns.append(f"School matched as '{school}' from '{p['school_raw']}' — please confirm.")
    ss["ref_excl_start"] = p.get("exclusion_start")
    ss["ref_excl_end"] = p.get("exclusion_end")

    ss["ref_prev_clc"] = "Yes" if p.get("prev_clc") else ""
    others = p.get("prev_other_lc_names") or []
    ss["ref_prev_other"] = "Yes" if others else ""
    ss["ref_other_lc_name"] = ", ".join(others)
    ss["ref_prev_notes"] = f"Previous placement year: {p['prev_year']}" if p.get("prev_year") else ""

    flags = p.get("flags", {})
    for _label, _xl, db_col in BOOL_FLAGS:
        ss[f"draft_{db_col}"] = bool(flags.get(db_col))
    cats = p.get("categories", set())
    for i, (_label, _xl, db_col) in enumerate(FUNDING_CATEGORIES, start=1):
        key = "9plusraap" if db_col == "flag_9plusraap" else str(i)
        ss[f"draft_{db_col}"] = key in cats

    ss["ref_attendance"] = p.get("attendance") or ""
    if cats:
        ss["ref_iesp"] = ""
    elif p.get("iesp_grant") and "IESP Grant" in IESP_OPTIONS:
        ss["ref_iesp"] = "IESP Grant"
    elif p.get("iesp_no") and "No" in IESP_OPTIONS:
        ss["ref_iesp"] = "No"
    else:
        ss["ref_iesp"] = ""

    has_med = bool(flags.get("flag_medical_condition"))
    ss["ref_has_medical"] = has_med
    ss["ref_medical_type"] = ""
    ss["ref_medical_details"] = p.get("medical_details") or ""
    if has_med:
        warns.append("Medical condition is ticked — please choose the Condition Type (the form only has free text).")
    has_meds = bool(flags.get("flag_medication"))
    ss["ref_has_medication"] = has_meds
    ss["ref_medication_details"] = ""
    if has_meds:
        warns.append("Medication is ticked — the form doesn't name it, so add the details if you have them.")
    if not p.get("student_name"):
        warns.append("No student name was found — this may be a blank form, or the name is in a place the tool didn't expect.")
    return warns


def yn(value):
    """Normalise a checkbox/bool into the Yes/'' convention used in the master Excel."""
    return "Yes" if value else ""

def num_or_none(value):
    """Some Supabase columns (previous_referrals, total_previous_placements,
    extension_weeks) are integer-typed. An empty string fails there — send NULL instead."""
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None

def clean_num_display(value):
    """Display helper: the extension_weeks column stores whole numbers as e.g. 2.0 —
    show '2' instead of '2.0' without changing what's actually stored."""
    if value is None or value == "":
        return "?"
    try:
        f = float(value)
        return str(int(f)) if f == int(f) else str(f)
    except (TypeError, ValueError):
        return str(value)

def parse_stored_date(value):
    """Turn a stored ISO date string back into a date object for a date_input default."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except Exception:
        return None

def is_yes(value):
    return str(value).strip().lower() == "yes"

def clean_value(v):
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    if isinstance(v, (datetime, date)):
        return v
    return v

def build_export_rows(records):
    """Turn Supabase records into row lists in EXPORT_COLUMNS order."""
    rows = []
    for record in records:
        row = []
        for col in EXPORT_COLUMNS:
            db_field = FIELD_MAP.get(col)
            if db_field is None:
                row.append("")
            else:
                row.append(clean_value(record.get(db_field, "")))
        rows.append(row)
    return rows

def export_new_workbook(records):
    """Build a brand-new, correctly-ordered Excel of just the selected records."""
    rows = build_export_rows(records)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data_Model"
    ws.append(EXPORT_COLUMNS)
    for row in rows:
        ws.append(row)

    header_fill = PatternFill(start_color="1A7A6E", end_color="1A7A6E", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for col_cells in ws.columns:
        max_length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=8)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_length + 2, 50)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def sync_into_master_workbook(uploaded_bytes, records):
    """
    Upsert records directly onto the user's real master Excel file, matching whatever
    column order that file already uses (read from its own header row).
    - A student not already in the file (by name) is appended as a new row.
    - A student already in the file has their EXISTING row updated in place — only
      cells where the incoming record has a non-blank value are overwritten, so this
      is how extension/waitlist changes made after the original allocation reach the
      Excel file without wiping out anything already there for that row.
    Returns (updated_workbook_bytes, sheet_name, appended_count, appended_names,
             updated_count, updated_names, unmatched_export_columns, name_column_found).
    """
    wb = openpyxl.load_workbook(BytesIO(uploaded_bytes))

    sheet_name = None
    for candidate in ("Data_Model", "Sheet1"):
        if candidate in wb.sheetnames:
            sheet_name = candidate
            break
    if sheet_name is None:
        sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]

    existing_headers = [c.value for c in ws[1]]
    header_index = {str(h).strip(): idx for idx, h in enumerate(existing_headers) if h}

    # Find the Student_Name column (required for matching existing rows)
    name_col_idx = header_index.get("Student_Name")
    name_column_found = name_col_idx is not None
    existing_row_by_name = {}
    if name_col_idx is not None:
        for row_num in range(2, ws.max_row + 1):
            val = ws.cell(row=row_num, column=name_col_idx + 1).value
            if val:
                existing_row_by_name[str(val).strip().lower()] = row_num

    unmatched_columns = [col for col in EXPORT_COLUMNS if col not in header_index]

    appended, appended_names = 0, []
    updated, updated_names = 0, []

    for record in records:
        student_name = str(record.get("student_name", "")).strip()
        match_row = existing_row_by_name.get(student_name.lower()) if student_name else None

        if match_row:
            changed = False
            for col in EXPORT_COLUMNS:
                if col not in header_index:
                    continue
                db_field = FIELD_MAP.get(col)
                if not db_field:
                    continue
                value = clean_value(record.get(db_field, ""))
                if value in ("", None):
                    continue  # never blank out existing data — only fill in real values
                ws.cell(row=match_row, column=header_index[col] + 1, value=value)
                changed = True
            if changed:
                updated += 1
                updated_names.append(student_name)
        else:
            new_row = [""] * len(existing_headers)
            for col in EXPORT_COLUMNS:
                if col not in header_index:
                    continue
                db_field = FIELD_MAP.get(col)
                value = clean_value(record.get(db_field, "")) if db_field else ""
                new_row[header_index[col]] = value

            ws.append(new_row)
            appended += 1
            appended_names.append(student_name or "(no name)")
            if student_name:
                existing_row_by_name[student_name.lower()] = ws.max_row

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return (output, sheet_name, appended, appended_names, updated, updated_names,
            unmatched_columns, name_column_found)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

st.title("📋 Allocation Meetings")

if 'current_term' not in st.session_state:
    term, week, year = get_current_term_week()
    st.session_state.current_term = term
    st.session_state.current_week = week
    st.session_state.current_year = year

with st.sidebar:
    st.header("📅 Meeting Selection")
    col1, col2 = st.columns(2)
    term_options = ["Term 1", "Term 2", "Term 3", "Term 4"]
    year_options = [2024, 2025, 2026]
    with col1:
        st.session_state.current_term = st.selectbox(
            "Term", term_options,
            index=term_options.index(st.session_state.current_term) if st.session_state.current_term in term_options else 0
        )
    with col2:
        st.session_state.current_year = st.selectbox(
            "Year", year_options,
            index=year_options.index(st.session_state.current_year) if st.session_state.current_year in year_options else 0
        )

    meeting_weeks = get_meeting_weeks(st.session_state.current_term, st.session_state.current_year)
    selected_week = st.selectbox("Week", meeting_weeks, index=st.session_state.current_week - 1)
    week_number = int(selected_week.split()[1])

    meeting_date = get_wednesday_date(week_number, st.session_state.current_term, st.session_state.current_year)
    st.info(f"**Meeting Date:** {meeting_date.strftime('%A, %B %d, %Y')}")
    st.caption(f"📚 {len(ALL_SCHOOLS)} schools loaded across {len(PARTNERSHIP_AREAS)} partnership areas")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📝 New Allocations", "🔄 Extensions", "⏸️ Not Placed", "📊 View & Export", "⏳ Waitlist", "⚙️ Admin"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NEW ALLOCATIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("New Student Allocations")
    stage_choice = st.radio("Stage:", ["➕ Referral", "📝 Allocation Outcome"], horizontal=True)
    st.markdown("---")

    if stage_choice == "📝 Allocation Outcome":
        st.subheader("📂 Select Referral to Progress")

        show_all_weeks = st.checkbox(
            "🔍 Show drafts from all weeks",
            help="Use this if a draft you created isn't showing up under the current week — earlier "
                 "versions of this tool sometimes defaulted to the wrong week, so drafts may be filed "
                 "under a different Term/Year/Week than you expect."
        )

        try:
            query = supabase.table("allocation_students").select("*").is_("outcome", "null")
            if not show_all_weeks:
                query = query.eq("meeting_week", selected_week)
            drafts = query.execute()

            if drafts.data:
                st.caption(f"📋 {len(drafts.data)} draft(s) found")
                label_for = lambda d: f"{d['student_name']} ({d.get('meeting_week', 'no week set')})" if show_all_weeks else d['student_name']
                # Keyed by the record's unique id (not name) — two drafts sharing the same
                # student name used to silently collide and hide one of them from this list.
                draft_by_id = {d['id']: d for d in drafts.data}
                selected_id = st.selectbox(
                    "Select draft:", list(draft_by_id.keys()),
                    format_func=lambda i: label_for(draft_by_id[i])
                )
                draft = draft_by_id[selected_id]
                st.success(f"✅ Loaded: **{draft['student_name']}**")

                if draft.get('meeting_week') != selected_week:
                    st.info(
                        f"This draft was filed under **{draft.get('meeting_week', 'an earlier week')}**, "
                        f"not the currently selected **{selected_week}**."
                    )
                    if st.button("📌 Reassign this draft to the currently selected week", key=f"reassign_{draft['id']}"):
                        supabase.table("allocation_students").update({
                            "meeting_week": selected_week,
                            "meeting_date": meeting_date.isoformat(),
                            "term": st.session_state.current_term,
                            "year": st.session_state.current_year,
                        }).eq("id", draft["id"]).execute()
                        st.success("Reassigned — reload this draft to continue.")
                        st.rerun()

                dcol1, dcol2 = st.columns([3, 1])
                with dcol2:
                    if st.button("🗑️ Delete This Draft", key=f"del_draft_{draft['id']}", use_container_width=True):
                        st.session_state[f"confirm_delete_{draft['id']}"] = True

                if st.session_state.get(f"confirm_delete_{draft['id']}"):
                    st.warning(f"⚠️ Delete **{draft['student_name']}**'s draft permanently? This can't be undone.")
                    ccol1, ccol2 = st.columns(2)
                    with ccol1:
                        if st.button("✅ Yes, delete it", key=f"confirm_del_{draft['id']}", type="primary", use_container_width=True):
                            supabase.table("allocation_students").delete().eq("id", draft["id"]).execute()
                            st.session_state.pop(f"confirm_delete_{draft['id']}", None)
                            st.success(f"Deleted {draft['student_name']}")
                            st.rerun()
                    with ccol2:
                        if st.button("Cancel", key=f"cancel_del_{draft['id']}", use_container_width=True):
                            st.session_state.pop(f"confirm_delete_{draft['id']}", None)
                            st.rerun()

                with st.form("complete_allocation"):
                    st.markdown("#### 📋 Referral Details — review and edit if needed")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        student_name = st.text_input("Name *", value=draft.get('student_name') or "")
                    with col2:
                        dob = st.date_input(
                            "DOB", value=parse_stored_date(draft.get('date_of_birth')),
                            min_value=date(2000, 1, 1), max_value=date.today()
                        )
                    with col3:
                        gender = st.selectbox(
                            "Gender", [""] + GENDER_OPTIONS,
                            index=([""] + GENDER_OPTIONS).index(draft.get('gender')) if draft.get('gender') in GENDER_OPTIONS else 0
                        )

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        school = st.selectbox(
                            "School *", [""] + ALL_SCHOOLS,
                            index=([""] + ALL_SCHOOLS).index(draft.get('school')) if draft.get('school') in ALL_SCHOOLS else 0
                        )
                    with col2:
                        edit_auto_partnership = get_partnership_from_school(school) if school else ""
                        st.text_input("Partnership", value=edit_auto_partnership, disabled=True)
                    with col3:
                        year_level = st.selectbox(
                            "Year Level *", [""] + YEAR_LEVELS,
                            index=([""] + YEAR_LEVELS).index(draft.get('year_level')) if draft.get('year_level') in YEAR_LEVELS else 0
                        )

                    col1, col2 = st.columns(2)
                    with col1:
                        referral_date = st.date_input("Referral Date", value=parse_stored_date(draft.get('referral_date')))
                    with col2:
                        previously_referred = st.selectbox(
                            "Previously Referred?", YES_NO,
                            index=YES_NO.index(draft.get('previously_referred')) if draft.get('previously_referred') in YES_NO else 0
                        )
                    previous_referrals = st.text_input("Number of Previous Referrals", value=draft.get('previous_referrals') or "")

                    ecol1, ecol2 = st.columns(2)
                    with ecol1:
                        exclusion_start_date = st.date_input(
                            "Exclusion Start Date", value=parse_stored_date(draft.get('exclusion_start_date'))
                        )
                    with ecol2:
                        exclusion_end_date = st.date_input(
                            "Exclusion End Date", value=parse_stored_date(draft.get('exclusion_end_date'))
                        )

                    edit_needs_priority = st.checkbox(
                        "Needs prioritising against other waiting referrals",
                        value=bool(draft.get('priority_level'))
                    )
                    if edit_needs_priority:
                        priority_level = st.selectbox(
                            "Priority Level *", [""] + PRIORITY_OPTIONS,
                            index=([""] + PRIORITY_OPTIONS).index(draft.get('priority_level')) if draft.get('priority_level') in PRIORITY_OPTIONS else 0
                        )
                    else:
                        priority_level = ""

                    with st.expander("🏠 Placement History"):
                        pcol1, pcol2, pcol3 = st.columns(3)
                        with pcol1:
                            previous_clc_placement = st.selectbox(
                                "Previous CLC Placement?", YES_NO,
                                index=YES_NO.index(draft.get('previous_clc_placement')) if draft.get('previous_clc_placement') in YES_NO else 0
                            )
                        with pcol2:
                            previous_other_lc = st.selectbox(
                                "Previous Other LC?", YES_NO,
                                index=YES_NO.index(draft.get('previous_other_lc')) if draft.get('previous_other_lc') in YES_NO else 0
                            )
                        with pcol3:
                            other_lc_name = st.text_input("Other LC Name", value=draft.get('other_lc_name') or "")
                        total_previous_placements = st.text_input(
                            "Total Previous Placements", value=draft.get('total_previous_placements') or ""
                        )
                        placement_history_notes = st.text_area(
                            "Placement History Notes", value=draft.get('placement_history_notes') or ""
                        )

                    with st.expander("🏷️ Support Flags & Funding"):
                        edit_flag_values = {}
                        cols = st.columns(3)
                        for i, (label, excel_col, db_col) in enumerate(BOOL_FLAGS):
                            with cols[i % 3]:
                                edit_flag_values[db_col] = st.checkbox(
                                    label, value=is_yes(draft.get(db_col)), key=f"edit_{db_col}"
                                )

                        st.markdown("**Funding Categories**")
                        st.caption("Ticking any category here automatically sets IESP Funding to Yes.")
                        fcols = st.columns(3)
                        edit_funding_values = {}
                        for i, (label, excel_col, db_col) in enumerate(FUNDING_CATEGORIES):
                            with fcols[i % 3]:
                                edit_funding_values[db_col] = st.checkbox(
                                    label, value=is_yes(draft.get(db_col)), key=f"edit_{db_col}"
                                )

                        acol1, acol2 = st.columns(2)
                        with acol1:
                            attendance_options = ["", "Full-time", "Part-time"]
                            current_attendance = (
                                "Full-time" if is_yes(draft.get('flag_attendance_fulltime'))
                                else "Part-time" if is_yes(draft.get('flag_attendance_parttime')) else ""
                            )
                            attendance = st.selectbox("Attendance", attendance_options, index=attendance_options.index(current_attendance))
                        with acol2:
                            iesp_options = [""] + IESP_OPTIONS
                            current_iesp = draft.get('flag_iesp_funding_no') or ""
                            iesp_status_if_no_category = st.selectbox(
                                "IESP Funding (if no category ticked above)", iesp_options,
                                index=iesp_options.index(current_iesp) if current_iesp in iesp_options else 0,
                                help="Ignored if any funding category above is ticked — that automatically means Yes."
                            )

                    with st.expander("💊 Medical & Medication"):
                        mcol1, mcol2 = st.columns(2)
                        with mcol1:
                            has_medical = st.checkbox("Medical Condition", value=is_yes(draft.get('flag_medical_condition')))
                            stored_medical = draft.get('medical_condition_details') or ""
                            stored_medical_type = stored_medical.split(":")[0] if ":" in stored_medical else stored_medical
                            medical_type = st.selectbox(
                                "Condition Type *", [""] + MEDICAL_CONDITION_TYPES,
                                index=([""] + MEDICAL_CONDITION_TYPES).index(stored_medical_type) if stored_medical_type in MEDICAL_CONDITION_TYPES else 0,
                                disabled=not has_medical
                            )
                            medical_details = st.text_area(
                                "Medical Condition Details",
                                value=stored_medical.split(":", 1)[1].strip() if ":" in stored_medical else "",
                                disabled=not has_medical
                            )
                        with mcol2:
                            has_medication = st.checkbox("Medication", value=is_yes(draft.get('flag_medication')))
                            medication_details = st.text_area(
                                "Medication Details", value=draft.get('medication_details') or "", disabled=not has_medication
                            )

                    bse = st.text_input("BSE", value=draft.get('bse') or "")
                    queries = st.text_area("Queries/Notes for Meeting", value=draft.get('queries') or "")

                    st.markdown("---")
                    st.markdown("#### ✅ Allocation Outcome")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        program = st.selectbox("Program *", PROGRAMS)
                    with col2:
                        outcome = st.selectbox("Outcome *", OUTCOMES)
                    with col3:
                        case_worker = st.selectbox("Focus Teacher", [""] + STAFF_NAMES)

                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input("Allocation Date", value=None)
                    with col2:
                        end_date = st.date_input("End Date", value=None)

                    bespoke = st.checkbox("Bespoke Placement")
                    information = st.text_area("Communication to School")

                    st.markdown("**If not allocated**")
                    wcol1, wcol2 = st.columns(2)
                    with wcol1:
                        waitlist_status = st.selectbox("Waitlist Status", WAITLIST_STATUS_OPTIONS)
                    with wcol2:
                        waitlist_date = st.date_input("Waitlist Date", value=None)
                    exit_reason = st.text_input("Exit Reason (if applicable)")
                    transition_plan = st.text_area("Transition Plan (if applicable)")
                    notes = st.text_area("Additional Notes")

                    bcol1, bcol2 = st.columns(2)
                    with bcol1:
                        save_draft_clicked = st.form_submit_button(
                            "💾 Save Changes (keep here, don't finalize)", use_container_width=True
                        )
                    with bcol2:
                        finalize_clicked = st.form_submit_button(
                            "✅ Finalize Allocation", type="primary", use_container_width=True
                        )

                    if save_draft_clicked or finalize_clicked:
                        if not student_name or not school or not year_level:
                            st.error("Please fill required fields (Name, School, Year Level)")
                        elif has_medical and not medical_type:
                            st.error("Please select a Medical Condition Type — required when Medical Condition is checked")
                        elif edit_needs_priority and not priority_level:
                            st.error("Please select a Priority Level — required when prioritisation is needed")
                        else:
                            try:
                                edit_any_category_selected = any(edit_funding_values.values())
                                if edit_any_category_selected:
                                    edit_iesp_yes, edit_iesp_no = "Yes", ""
                                else:
                                    edit_iesp_yes = ""
                                    edit_iesp_no = iesp_status_if_no_category

                                update_payload = {
                                    "student_name": student_name,
                                    "date_of_birth": dob.isoformat() if dob else None,
                                    "gender": gender,
                                    "school": school,
                                    "year_level": year_level,
                                    "partnership_area": edit_auto_partnership,
                                    "referral_date": referral_date.isoformat() if referral_date else None,
                                    "previously_referred": previously_referred,
                                    "previous_referrals": num_or_none(previous_referrals),
                                    "priority_level": priority_level if priority_level else None,
                                    "previous_clc_placement": previous_clc_placement,
                                    "previous_other_lc": previous_other_lc,
                                    "other_lc_name": other_lc_name,
                                    "total_previous_placements": num_or_none(total_previous_placements),
                                    "placement_history_notes": placement_history_notes,
                                    "flag_attendance_fulltime": yn(attendance == "Full-time"),
                                    "flag_attendance_parttime": yn(attendance == "Part-time"),
                                    "flag_iesp_funding_yes": edit_iesp_yes,
                                    "flag_iesp_funding_no": edit_iesp_no,
                                    "flag_medication": yn(has_medication),
                                    "medication_details": medication_details if has_medication else None,
                                    "flag_medical_condition": yn(has_medical),
                                    "medical_condition_details": (
                                        f"{medical_type}: {medical_details}" if has_medical and medical_details
                                        else medical_type if has_medical else None
                                    ),
                                    "queries": queries,
                                    "bse": bse or None,
                                    "exclusion_start_date": exclusion_start_date.isoformat() if exclusion_start_date else None,
                                    "exclusion_end_date": exclusion_end_date.isoformat() if exclusion_end_date else None,
                                    "program": program,
                                    "case_worker": case_worker or None,
                                    "actioned_by": case_worker or None,
                                    "start_after": start_date.isoformat() if start_date else None,
                                    "finishing_date": end_date.isoformat() if end_date else None,
                                    "bespoke_placement": yn(bespoke),
                                    "information": information or None,
                                    "waitlist_date": waitlist_date.isoformat() if waitlist_date else None,
                                    "exit_reason": exit_reason or None,
                                    "transition_plan": transition_plan or None,
                                    "notes": notes or None,
                                }

                                if finalize_clicked:
                                    update_payload["outcome"] = outcome
                                    update_payload["waitlist_status"] = waitlist_status if outcome == "Not Allocated" else "Not Applicable"
                                # else: leave outcome untouched — stays a draft, keeps showing in Stage 2

                                for db_col, val in edit_flag_values.items():
                                    update_payload[db_col] = yn(val)
                                for db_col, val in edit_funding_values.items():
                                    update_payload[db_col] = yn(val)

                                supabase.table("allocation_students").update(update_payload).eq("id", draft['id']).execute()

                                if finalize_clicked:
                                    st.success(f"✅ Allocation finalized for {student_name}!")
                                    st.balloons()
                                else:
                                    st.success(f"💾 Changes saved for {student_name} — still here in Stage 2.")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
            else:
                st.info("✅ No drafts to complete. Create one in Stage 1.")
        except Exception as e:
            st.error(f"Error: {e}")

    else:
        st.subheader("➕ New Referral")

        with st.expander("📄 Upload a completed Referral Form to pre-fill this screen", expanded=False):
            st.caption(
                "Upload the Word (.docx) or PDF referral form. The tool reads it inside this app (nothing is "
                "sent to an outside service) and fills in the boxes below. **Nothing is saved** until you "
                "check it and press Save Draft."
            )
            ref_upload = st.file_uploader(
                "Referral form", type=["docx", "doc", "pdf", "png", "jpg", "jpeg"],
                key=f"ref_form_upload_{st.session_state.get('ref_upload_n', 0)}"
            )
            if ref_upload is not None:
                ref_parsed, ref_notes, ref_status = read_uploaded_form(ref_upload, "referral")
                if ref_status != "ok":
                    show_unreadable_form_message(ref_upload, ref_status, ref_notes)
                else:
                    st.markdown(
                        f"**Found:** {ref_parsed.get('student_name') or '—'} · "
                        f"DOB {ref_parsed['dob']:%d/%m/%Y}" if ref_parsed.get("dob") else
                        f"**Found:** {ref_parsed.get('student_name') or '—'} · DOB —"
                    )
                    st.caption(
                        f"School on form: {ref_parsed.get('school_raw') or '—'} · "
                        f"Year {ref_parsed.get('year_level') or '—'} · ED ID {ref_parsed.get('ed_id') or '—'}"
                    )
                    for n_ in ref_notes:
                        st.warning(n_)
                    if st.button("✨ Fill the form below from this file", type="primary", key="ref_apply_prefill"):
                        warns_ = apply_referral_prefill(ref_parsed)
                        st.success("Form filled in below — please check every section before saving.")
                        for w_ in warns_:
                            st.warning(w_)

        with st.form("new_draft", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                student_name = st.text_input("Name *", key="ref_name")
            with col2:
                dob = st.date_input("DOB", value=None, min_value=date(2000, 1, 1), max_value=date.today(), key="ref_dob")
            with col3:
                gender = st.selectbox("Gender", [""] + GENDER_OPTIONS)

            col1, col2, col3 = st.columns(3)
            with col1:
                school = st.selectbox("School *", [""] + ALL_SCHOOLS, key="ref_school")
            with col2:
                auto_partnership = get_partnership_from_school(school) if school else ""
                partnership = st.text_input("Partnership", value=auto_partnership, disabled=True)
            with col3:
                year_level = st.selectbox("Year Level *", [""] + YEAR_LEVELS, key="ref_year")

            col1, col2 = st.columns(2)
            with col1:
                referral_date = st.date_input("Referral Date", value=None)
            with col2:
                previously_referred = st.selectbox("Previously Referred?", YES_NO)

            previous_referrals = st.text_input("Number of Previous Referrals")

            col1, col2 = st.columns(2)
            with col1:
                exclusion_start_date = st.date_input("Exclusion Start Date", value=None, key="ref_excl_start")
            with col2:
                exclusion_end_date = st.date_input("Exclusion End Date", value=None, key="ref_excl_end")

            needs_priority = st.checkbox(
                "Needs prioritising against other waiting referrals",
                help="Only tick this if there are multiple referrals waiting and this student needs "
                     "to be ordered against them for placement. Leave unticked if the student is "
                     "going straight in — Priority Level isn't needed in that case."
            )
            if needs_priority:
                priority_level = st.selectbox("Priority Level *", [""] + PRIORITY_OPTIONS)
            else:
                priority_level = ""
                st.caption("Straight in — no priority ordering needed.")

            with st.expander("🏠 Placement History"):
                pcol1, pcol2, pcol3 = st.columns(3)
                with pcol1:
                    previous_clc_placement = st.selectbox("Previous CLC Placement?", YES_NO, key="ref_prev_clc")
                with pcol2:
                    previous_other_lc = st.selectbox("Previous Other LC?", YES_NO, key="ref_prev_other")
                with pcol3:
                    other_lc_name = st.text_input("Other LC Name", key="ref_other_lc_name")
                total_previous_placements = st.text_input("Total Previous Placements")
                placement_history_notes = st.text_area("Placement History Notes", key="ref_prev_notes")

            with st.expander("🏷️ Support Flags & Funding"):
                st.caption("These feed the Dashboard's disability & funding analytics directly.")
                flag_values = {}
                cols = st.columns(3)
                for i, (label, excel_col, db_col) in enumerate(BOOL_FLAGS):
                    with cols[i % 3]:
                        flag_values[db_col] = st.checkbox(label, key=f"draft_{db_col}")

                st.markdown("**Funding Categories**")
                st.caption("Ticking any category here automatically sets IESP Funding to Yes.")
                fcols = st.columns(3)
                funding_values = {}
                for i, (label, excel_col, db_col) in enumerate(FUNDING_CATEGORIES):
                    with fcols[i % 3]:
                        funding_values[db_col] = st.checkbox(label, key=f"draft_{db_col}")

                acol1, acol2 = st.columns(2)
                with acol1:
                    attendance = st.selectbox("Attendance", ["", "Full-time", "Part-time"], key="ref_attendance")
                with acol2:
                    iesp_status_if_no_category = st.selectbox(
                        "IESP Funding (if no category ticked above)",
                        [""] + IESP_OPTIONS,
                        key="ref_iesp",
                        help="Ignored if any funding category above is ticked — that automatically means Yes."
                    )

            with st.expander("💊 Medical & Medication"):
                mcol1, mcol2 = st.columns(2)
                with mcol1:
                    has_medical = st.checkbox("Medical Condition", key="ref_has_medical")
                    medical_type = st.selectbox(
                        "Condition Type *", [""] + MEDICAL_CONDITION_TYPES,
                        disabled=not has_medical, key="ref_medical_type"
                    )
                    medical_details = st.text_area("Medical Condition Details", disabled=not has_medical, key="ref_medical_details")
                with mcol2:
                    has_medication = st.checkbox("Medication", key="ref_has_medication")
                    medication_details = st.text_area("Medication Details", disabled=not has_medication, key="ref_medication_details")

            bse = st.text_input("BSE")
            queries = st.text_area("Queries/Notes for Meeting")

            submitted = st.form_submit_button("💾 Save Draft", type="primary", use_container_width=True)
            if submitted:
                if not student_name or not school or not year_level:
                    st.error("Please fill required fields (Name, School, Year Level)")
                elif has_medical and not medical_type:
                    st.error("Please select a Medical Condition Type — required when Medical Condition is checked")
                elif needs_priority and not priority_level:
                    st.error("Please select a Priority Level — required when prioritisation is needed")
                else:
                    try:
                        any_category_selected = any(funding_values.values())
                        if any_category_selected:
                            iesp_yes, iesp_no = "Yes", ""
                        else:
                            iesp_yes = ""
                            iesp_no = iesp_status_if_no_category

                        record = {
                            "meeting_week": selected_week,
                            "meeting_date": meeting_date.isoformat(),
                            "term": st.session_state.current_term,
                            "year": st.session_state.current_year,
                            "student_name": student_name,
                            "school": school,
                            "date_of_birth": dob.isoformat() if dob else None,
                            "gender": gender,
                            "year_level": year_level,
                            "partnership_area": auto_partnership,
                            "priority_level": priority_level if priority_level else None,
                            "referral_date": referral_date.isoformat() if referral_date else None,
                            "previously_referred": previously_referred,
                            "previous_referrals": num_or_none(previous_referrals),
                            "previous_clc_placement": previous_clc_placement,
                            "previous_other_lc": previous_other_lc,
                            "other_lc_name": other_lc_name,
                            "total_previous_placements": num_or_none(total_previous_placements),
                            "placement_history_notes": placement_history_notes,
                            "flag_attendance_fulltime": yn(attendance == "Full-time"),
                            "flag_attendance_parttime": yn(attendance == "Part-time"),
                            "flag_iesp_funding_yes": iesp_yes,
                            "flag_iesp_funding_no": iesp_no,
                            "flag_medication": yn(has_medication),
                            "medication_details": medication_details if has_medication else None,
                            "flag_medical_condition": yn(has_medical),
                            "medical_condition_details": (
                                f"{medical_type}: {medical_details}" if has_medical and medical_details
                                else medical_type if has_medical else None
                            ),
                            "queries": queries,
                            "bse": bse or None,
                            "exclusion_start_date": exclusion_start_date.isoformat() if exclusion_start_date else None,
                            "exclusion_end_date": exclusion_end_date.isoformat() if exclusion_end_date else None,
                            "outcome": None,
                        }
                        for db_col, val in flag_values.items():
                            record[db_col] = yn(val)
                        for db_col, val in funding_values.items():
                            record[db_col] = yn(val)

                        supabase.table("allocation_students").insert(record).execute()
                        st.session_state["ref_upload_n"] = st.session_state.get("ref_upload_n", 0) + 1
                        st.success(f"✅ Draft saved for {student_name}!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXTENSIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("🔄 Extensions")

    if st.session_state.get("last_extension_saved"):
        info = st.session_state["last_extension_saved"]
        st.success(f"✅ Last saved: **{info['name']}** — {info['detail']} (saved {info['when']})")
        st.caption("This confirmation stays here until you save another extension, so you can check it any time.")

    ext_stage = st.radio(
        "Stage:", ["➕ Extension Request", "✅ Extension Decision"], horizontal=True,
        help="Log the request first without an outcome, then come back here to record the decision "
             "once it's been made — the same way referrals work in New Allocations."
    )
    st.markdown("---")

    try:
        all_students = supabase.table("allocation_students").select("*").execute()

        def _is_active(r):
            if str(r.get("outcome", "")).strip().lower() != "allocated":
                return False
            if str(r.get("current_status", "")).strip().lower() == "inactive":
                return False
            return True

        def _has_pending_request(r):
            # extension_date is only ever set when a decision is actually recorded through this
            # tool — extension_status can hold leftover "Not Approved" junk from the old Excel
            # import even when no real decision has ever been made, so it can't be trusted here.
            return bool(r.get("extension_weeks") or r.get("proposed_extension_finish_date")) and not r.get("extension_date")

        allocated_data = [r for r in all_students.data if _is_active(r)]

        with st.expander("🔍 Debug: what's actually in the database"):
            st.write(f"Total rows in `allocation_students`: {len(all_students.data)}")
            outcome_counts = {}
            for r in all_students.data:
                key = repr(r.get("outcome"))
                outcome_counts[key] = outcome_counts.get(key, 0) + 1
            st.write("Breakdown by `outcome` value (exact, including hidden spaces/case):")
            st.write(outcome_counts)
            allocated_total = sum(1 for r in all_students.data if str(r.get("outcome", "")).strip().lower() == "allocated")
            st.write(
                f"Of {allocated_total} allocated student(s), {len(allocated_data)} are considered "
                f"**active** and shown below; {allocated_total - len(allocated_data)} are excluded "
                "(marked Inactive via Current_Status)."
            )

        if ext_stage == "➕ Extension Request":
            st.subheader("➕ New Extension Request")
            st.caption("Log the request details — no outcome yet. This moves them into Extension Decision once saved.")

            eligible = [r for r in allocated_data if not _has_pending_request(r)]
            if eligible:
                sorted_students = sorted(eligible, key=lambda r: (r.get('student_name') or '').lower())
                options = {
                    f"{r['student_name']} — {r.get('school', 'no school')} (Year {r.get('year_level', '?')})": r
                    for r in sorted_students
                }
                ext_pf = st.session_state.get("ext_prefill") or {}

                with st.expander("📄 Upload a completed Extension Request Form to pre-fill this screen", expanded=False):
                    st.caption(
                        "Upload the Word (.docx) or PDF request form. It's read inside this app (nothing is sent "
                        "to an outside service) and fills in the student, weeks, finish date and reason. "
                        "**Nothing is saved** until you check it and press Save Extension Request."
                    )
                    ext_upload = st.file_uploader(
                        "Extension request form", type=["docx", "doc", "pdf", "png", "jpg", "jpeg"],
                        key=f"ext_form_upload_{st.session_state.get('ext_upload_n', 0)}"
                    )
                    if ext_upload is not None:
                        ext_parsed, ext_notes, ext_status = read_uploaded_form(ext_upload, "extension")
                        if ext_status != "ok":
                            show_unreadable_form_message(ext_upload, ext_status, ext_notes)
                        else:
                            matched_rec, matched_ok = match_student(ext_parsed.get("student_name"), eligible)
                            st.markdown(f"**Found:** {ext_parsed.get('student_name') or '—'}")
                            fin_ = ext_parsed.get("proposed_finish")
                            st.caption(
                                f"School on form: {ext_parsed.get('school_raw') or '—'} · "
                                f"Requested end date: {fin_:%d/%m/%Y}" if fin_ else
                                f"School on form: {ext_parsed.get('school_raw') or '—'} · Requested end date: —"
                            )
                            st.caption(f"Weeks on form: {ext_parsed.get('weeks_raw') or '—'}")
                            for n_ in ext_notes:
                                st.warning(n_)
                            if st.button("✨ Fill the form below from this file", type="primary", key="ext_apply_prefill"):
                                label_ = next((k for k, v in options.items() if matched_rec and v["id"] == matched_rec["id"]), None)
                                reason_parts = []
                                if ext_parsed.get("reason"):
                                    reason_parts.append(f"Reason: {ext_parsed['reason']}")
                                if ext_parsed.get("outcomes"):
                                    reason_parts.append(f"Intended outcomes: {ext_parsed['outcomes']}")
                                st.session_state["ext_prefill"] = {
                                    "label": label_,
                                    "weeks": ext_parsed.get("weeks") or "",
                                    "finish": ext_parsed.get("proposed_finish"),
                                    "reason": "\n".join(reason_parts),
                                }
                                ext_pf = st.session_state["ext_prefill"]
                                st.success("Form filled in below — please check it before saving.")
                                if not label_:
                                    fn_ = ext_parsed.get("student_name") or "the student"
                                    anyrec = match_student(ext_parsed.get("student_name"), all_students.data)[0]
                                    if not ext_parsed.get("student_name"):
                                        st.warning("No student name was found on the form — please choose the student from the list.")
                                    elif not anyrec:
                                        st.warning(f"I read the name as '{fn_}', but nobody in the database is close to that. "
                                                   "Please choose the student from the list (the name on the form may be spelled differently).")
                                    elif str(anyrec.get("outcome", "")).strip().lower() != "allocated":
                                        st.warning(f"Found '{anyrec.get('student_name')}' but their outcome is "
                                                   f"'{anyrec.get('outcome') or 'not yet decided'}', not Allocated, so they can't have an extension.")
                                    elif str(anyrec.get("current_status", "")).strip().lower() == "inactive":
                                        st.warning(f"Found '{anyrec.get('student_name')}' but their Current Status is Inactive, "
                                                   "so they're not in the active list.")
                                    elif _has_pending_request(anyrec):
                                        st.warning(f"'{anyrec.get('student_name')}' already has a request waiting for a decision "
                                                   "(see Extension Decision), so they aren't in this list.")
                                    else:
                                        st.warning(f"Found '{anyrec.get('student_name')}' but couldn't place them in the list — please choose them.")
                                elif not matched_ok:
                                    st.warning("Student matched on a close name — please confirm it's the right one.")
                                if not ext_parsed.get("weeks"):
                                    st.warning("No number of weeks was found on the form — please enter it.")
                                if not ext_parsed.get("proposed_finish"):
                                    st.warning("No requested end date was found — please enter it.")

                _opt_keys = list(options.keys())
                _idx = _opt_keys.index(ext_pf["label"]) if ext_pf.get("label") in _opt_keys else 0
                chosen = st.selectbox(f"Select allocated student ({len(options)} total — type to search)", _opt_keys, index=_idx)
                record = options[chosen]

                with st.form("extension_request_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        ext_weeks = st.text_input("Extension Weeks Requested", value=ext_pf.get("weeks", ""))
                    with col2:
                        proposed_finish = st.date_input("Proposed Extension Finish Date", value=ext_pf.get("finish"))

                    ext_comm = st.text_area("Reason for request / communication so far", value=ext_pf.get("reason", ""))
                    ext_owner = st.selectbox("Focus Teacher", [""] + STAFF_NAMES)

                    if st.form_submit_button("💾 Save Extension Request", type="primary", use_container_width=True):
                        try:
                            result = supabase.table("allocation_students").update({
                                "extension_weeks": num_or_none(ext_weeks),
                                "proposed_extension_finish_date": proposed_finish.isoformat() if proposed_finish else None,
                                "information": ext_comm or record.get("information"),
                                "actioned_by": ext_owner or record.get("actioned_by"),
                            }).eq("id", record["id"]).execute()

                            if not result.data:
                                st.error("⚠️ The update ran but returned no confirmation — nothing may have been saved.")
                            else:
                                st.session_state.pop("ext_prefill", None)
                                st.session_state["ext_upload_n"] = st.session_state.get("ext_upload_n", 0) + 1
                                st.session_state["last_extension_saved"] = {
                                    "name": result.data[0].get("student_name"),
                                    "detail": f"Request logged, {clean_num_display(result.data[0].get('extension_weeks'))} weeks requested",
                                    "when": datetime.now().strftime("%I:%M %p"),
                                }
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("No allocated students currently need a new extension request logged.")

        else:
            st.subheader("✅ Record Extension Decision")
            pending = [r for r in allocated_data if _has_pending_request(r)]
            if pending:
                sorted_pending = sorted(pending, key=lambda r: (r.get('student_name') or '').lower())
                options = {
                    f"{r['student_name']} — {r.get('school', 'no school')} "
                    f"(requested {r.get('extension_weeks') or '?'} wks)": r
                    for r in sorted_pending
                }
                chosen = st.selectbox(f"Select pending request ({len(options)} total)", list(options.keys()))
                record = options[chosen]

                with st.form("extension_decision_form"):
                    st.caption("Details from the request — edit if needed before recording the decision.")
                    col1, col2 = st.columns(2)
                    with col1:
                        ext_weeks = st.text_input("Extension Weeks", value=record.get("extension_weeks") or "")
                    with col2:
                        proposed_finish = st.date_input(
                            "Proposed Extension Finish Date",
                            value=parse_stored_date(record.get("proposed_extension_finish_date"))
                        )
                    ext_comm = st.text_area("Communication to School", value=record.get("information") or "")
                    ext_owner = st.selectbox(
                        "Focus Teacher", [""] + STAFF_NAMES,
                        index=([""] + STAFF_NAMES).index(record.get("actioned_by")) if record.get("actioned_by") in STAFF_NAMES else 0
                    )

                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        ext_outcome = st.selectbox("Extension Outcome *", EXTENSION_OUTCOMES)
                    with col2:
                        ext_date = st.date_input("Extension Decision Date", value=datetime.now().date())

                    if st.form_submit_button("✅ Save Decision", type="primary", use_container_width=True):
                        try:
                            result = supabase.table("allocation_students").update({
                                "extension": yn(ext_outcome == "Approved"),
                                "extension_status": ext_outcome,
                                "extension_date": ext_date.isoformat() if ext_date else None,
                                "extension_weeks": num_or_none(ext_weeks),
                                "proposed_extension_finish_date": proposed_finish.isoformat() if proposed_finish else None,
                                "information": ext_comm or record.get("information"),
                                "actioned_by": ext_owner or record.get("actioned_by"),
                            }).eq("id", record["id"]).execute()

                            if not result.data:
                                st.error("⚠️ The update ran but returned no confirmation — nothing may have been saved.")
                            else:
                                st.session_state["last_extension_saved"] = {
                                    "name": result.data[0].get("student_name"),
                                    "detail": f"Decision: {result.data[0].get('extension_status')}, "
                                              f"{clean_num_display(result.data[0].get('extension_weeks'))} weeks",
                                    "when": datetime.now().strftime("%I:%M %p"),
                                }
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("No pending extension requests waiting on a decision. Log one under Extension Request first.")
    except Exception as e:
        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — NOT PLACED
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("⏸️ Not Placed Students")
    try:
        not_allocated = supabase.table("allocation_students").select("*") \
            .eq("meeting_week", selected_week).eq("outcome", "Not Allocated").execute()

        if not_allocated.data:
            st.info(f"📊 {len(not_allocated.data)} student(s) not allocated this week")
            df = pd.DataFrame(not_allocated.data)
            show_cols = [c for c in ["student_name", "year_level", "school", "waitlist_status", "exit_reason"] if c in df.columns]
            st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
        else:
            st.success("✅ No students not allocated this week")
    except Exception as e:
        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — VIEW & EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("📊 View & Export Completed Allocations")

    with st.expander("🔍 Debug: every student with extension data, ignoring scope/filters entirely"):
        try:
            everyone = supabase.table("allocation_students").select("*").execute().data
            with_extension = [r for r in everyone if r.get("extension_status")]
            st.write(f"Total rows in database: {len(everyone)}")
            st.write(f"Rows with a non-blank `extension_status`: {len(with_extension)}")
            if with_extension:
                st.dataframe(
                    pd.DataFrame([{
                        "Student": r.get("student_name"), "Outcome": r.get("outcome"),
                        "Current_Status": r.get("current_status"), "Extension_Status": r.get("extension_status"),
                        "Extension_Weeks": r.get("extension_weeks"), "Meeting_Week": r.get("meeting_week"),
                    } for r in with_extension]),
                    use_container_width=True, hide_index=True
                )
        except Exception as e:
            st.error(f"Debug error: {e}")

    scope = st.radio(
        "Show:",
        [
            "This meeting week only", "All allocated & completed records",
            "Extensions decided this week", "All extensions ever recorded"
        ],
        horizontal=True, index=0,
        help="'This meeting week only' now includes both new allocations from this week AND any "
             "extension decided this week, even for a student allocated earlier. "
             "'Extensions decided this week' narrows to just the extension decisions on their own."
    )

    try:
        query = supabase.table("allocation_students").select("*").not_.is_("outcome", "null")
        week_monday = meeting_date - timedelta(days=2)
        week_sunday = meeting_date + timedelta(days=4)

        if scope == "This meeting week only":
            # Combines two different things that both count as "this week's activity":
            # students newly allocated/decided this meeting week, OR any student (regardless
            # of when they were originally allocated) who had an extension decided this week.
            query = query.or_(
                f"meeting_week.eq.{selected_week},"
                f"and(extension_date.gte.{week_monday.isoformat()},extension_date.lte.{week_sunday.isoformat()})"
            )
        elif scope == "Extensions decided this week":
            # extension_date is only ever set by actually using the Extensions tab —
            # this filters out leftover "Not Approved" placeholder values that came
            # across from the Excel import with no real decision behind them, and
            # ties the list to the Term/Year/Week currently selected in the sidebar.
            query = query.gte("extension_date", week_monday.isoformat()).lte("extension_date", week_sunday.isoformat())
        elif scope == "All extensions ever recorded":
            query = query.not_.is_("extension_date", "null")
        full_data = query.execute()

        if full_data.data:
            ext_approved = [r for r in full_data.data if r.get('extension_status') == 'Approved']
            ext_not_approved = [r for r in full_data.data if r.get('extension_status') == 'Not Approved']
            has_extension_ids = {r['id'] for r in ext_approved + ext_not_approved}
            allocated = [r for r in full_data.data if r.get('outcome') == 'Allocated' and r['id'] not in has_extension_ids]
            not_allocated = [r for r in full_data.data if r.get('outcome') == 'Not Allocated' and r['id'] not in has_extension_ids]

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Records", len(full_data.data))
            with col2:
                st.metric("Allocated", len(allocated))
            with col3:
                st.metric("Not Allocated", len(not_allocated))
            with col4:
                st.metric("Extension Approved", len(ext_approved))
            with col5:
                st.metric("Extension Not Approved", len(ext_not_approved))
            st.caption(
                "A student who was extended is counted once, under Extension — not also under "
                "Allocated — since they'd already been allocated previously."
            )

            st.markdown("---")
            st.subheader("📋 Pre-Export Review & Validation")

            export_records = allocated + not_allocated + ext_approved + ext_not_approved
            validation_issues = []
            for record in export_records:
                issues = []
                if not record.get('student_name'):
                    issues.append("Missing student name")
                if not record.get('school'):
                    issues.append("Missing school")
                if record.get('outcome') == 'Allocated' and not record.get('program'):
                    issues.append("Missing program")
                if issues:
                    validation_issues.append({'student': record.get('student_name', 'Unknown'), 'issues': issues})

            if validation_issues:
                st.warning(f"⚠️ **{len(validation_issues)} record(s) have issues:**")
                for issue in validation_issues:
                    st.write(f"  • **{issue['student']}**: {', '.join(issue['issues'])}")
            else:
                st.success(f"✅ **All {len(export_records)} record(s) pass validation!**")

            st.markdown("---")
            st.subheader("👁️ Export Preview")

            def _preview_table(records):
                data = [{
                    "Student": r.get('student_name', ''), "Year": r.get('year_level', ''),
                    "Program": r.get('program', ''), "School": r.get('school', ''),
                    "Outcome": r.get('outcome', ''), "Focus Teacher": r.get('actioned_by', ''),
                    "Extension": r.get('extension_status', ''), "Ext. Weeks": r.get('extension_weeks', ''),
                    "Meeting Week": r.get('meeting_week', ''), "BSE": r.get('bse', ''),
                } for r in records]
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

            with st.expander(f"✅ Allocated ({len(allocated)})", expanded=True):
                if allocated:
                    _preview_table(allocated)
                else:
                    st.caption("None in this view.")

            with st.expander(f"⏸️ Not Allocated ({len(not_allocated)})"):
                if not_allocated:
                    _preview_table(not_allocated)
                else:
                    st.caption("None in this view.")

            with st.expander(f"🔄 Extension Approved ({len(ext_approved)})"):
                if ext_approved:
                    _preview_table(ext_approved)
                else:
                    st.caption("None in this view.")

            with st.expander(f"🔄 Extension Not Approved ({len(ext_not_approved)})"):
                if ext_not_approved:
                    _preview_table(ext_not_approved)
                else:
                    st.caption("None in this view.")

            st.caption(f"📊 {len(export_records)} record(s) total, ready for export")

            with st.expander("🔎 View all captured data (every field, per student)"):
                full_rows = build_export_rows(export_records)
                st.dataframe(
                    pd.DataFrame(full_rows, columns=EXPORT_COLUMNS),
                    use_container_width=True, hide_index=True
                )

            st.markdown("---")
            with st.expander("↩️ Reopen a Record to Stage 2"):
                st.caption(
                    "Sends a student back to an unfinished draft — their outcome is cleared, and they'll "
                    "show up in Stage 2 (Complete Draft) again to review and re-finalize. Nothing else "
                    "about their record is changed."
                )
                reopen_by_id = {r['id']: r for r in export_records}
                reopen_id = st.selectbox(
                    "Select student to reopen:", list(reopen_by_id.keys()),
                    format_func=lambda i: f"{reopen_by_id[i]['student_name']} ({reopen_by_id[i].get('outcome', '')})",
                    key="reopen_record_select"
                )
                reopen_record = reopen_by_id[reopen_id]

                if st.button("↩️ Reopen to Stage 2", key=f"reopen_{reopen_record['id']}"):
                    supabase.table("allocation_students").update({"outcome": None}).eq("id", reopen_record["id"]).execute()
                    st.success(f"{reopen_record['student_name']} sent back to Stage 2.")
                    st.rerun()

            st.markdown("---")
            with st.expander("🗑️ Delete a Record"):
                del_by_id = {r['id']: r for r in export_records}
                del_id = st.selectbox(
                    "Select student to delete:", list(del_by_id.keys()),
                    format_func=lambda i: f"{del_by_id[i]['student_name']} ({del_by_id[i].get('school', '')})",
                    key="del_record_select"
                )
                del_record = del_by_id[del_id]

                if st.button("🗑️ Delete This Record", key=f"del_rec_{del_record['id']}"):
                    st.session_state[f"confirm_del_rec_{del_record['id']}"] = True

                if st.session_state.get(f"confirm_del_rec_{del_record['id']}"):
                    st.warning(
                        f"⚠️ Permanently delete **{del_record['student_name']}**'s record "
                        f"(outcome: {del_record.get('outcome', '')})? This can't be undone and won't "
                        "affect anything already in your Excel file."
                    )
                    dccol1, dccol2 = st.columns(2)
                    with dccol1:
                        if st.button("✅ Yes, delete it", key=f"do_delete_rec_{del_record['id']}", type="primary", use_container_width=True):
                            supabase.table("allocation_students").delete().eq("id", del_record["id"]).execute()
                            st.session_state.pop(f"confirm_del_rec_{del_record['id']}", None)
                            st.success(f"Deleted {del_record['student_name']}")
                            st.rerun()
                    with dccol2:
                        if st.button("Cancel", key=f"cancel_del_rec_{del_record['id']}", use_container_width=True):
                            st.session_state.pop(f"confirm_del_rec_{del_record['id']}", None)
                            st.rerun()

            st.markdown("---")
            st.subheader("📥 Download Records for Your Master Excel File")
            st.caption(
                "Download the records below as a ready-formatted Excel file, matching your master "
                "file's column layout exactly. Open it alongside your master file and paste the rows "
                "in — this is the most reliable option right now."
            )
            if st.button("📥 Download Records", type="primary", use_container_width=True):
                try:
                    excel_bytes = export_new_workbook(export_records)
                    st.download_button(
                        label=f"💾 Save Excel ({len(export_records)} rows)",
                        data=excel_bytes.getvalue(),
                        file_name=f"CLC_Allocations_{selected_week.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Export error: {e}")

            st.markdown("---")
            with st.expander("🧪 Experimental: sync directly into your master file (still being debugged)"):
                st.caption(
                    "Upload your live CLC_Allocation_Dashboard file below — the tool matches its "
                    "existing columns, updates students already in it (e.g. with new extension info), "
                    "appends new students, and gives you back the updated file. This hasn't been "
                    "reliably showing changes in Excel yet — use the download option above instead "
                    "for now."
                )

                master_file = st.file_uploader(
                    "Upload master Excel file (e.g. CLC_Allocation_Dashboard_2026_WithNames.xlsx)",
                    type=['xlsx'], key="master_upload"
                )

                if master_file is not None and not validation_issues:
                    if st.button("🔄 Sync & Download Updated Master File", use_container_width=True):
                        try:
                            (updated_bytes, sheet_used, appended, appended_names, updated,
                             updated_names, unmatched, name_column_found) = sync_into_master_workbook(
                                master_file.getvalue(), export_records
                            )

                            if not name_column_found:
                                st.error(
                                    "⚠️ No `Student_Name` column was found in your uploaded file's "
                                    f"**{sheet_used}** sheet — matching against existing students was skipped, "
                                    "and every record was appended as new. This may mean the wrong sheet or file "
                                    "was used. Double-check this is the right file."
                                )

                            if appended == 0 and updated == 0:
                                st.error("❌ Nothing changed — no records had new data to write.")
                            if appended:
                                st.success(f"✅ Added {appended} new student row(s) to **{sheet_used}**:")
                                st.write(", ".join(appended_names))
                            if updated:
                                st.success(
                                    f"✅ Updated {updated} existing student row(s) in **{sheet_used}** "
                                    f"(e.g. new extension or waitlist info):"
                                )
                                st.write(", ".join(updated_names))
                            if unmatched:
                                st.info(
                                    f"ℹ️ {len(unmatched)} field(s) had no matching column in your file and were left blank: "
                                    f"{', '.join(unmatched)}"
                                )

                            if appended or updated:
                                st.markdown("**🔍 Verify — read directly from the file about to be downloaded:**")
                                verify_wb = openpyxl.load_workbook(BytesIO(updated_bytes.getvalue()))
                                verify_ws = verify_wb[sheet_used]
                                verify_headers = [str(c.value) for c in verify_ws[1]]
                                name_idx = verify_headers.index("Student_Name") if "Student_Name" in verify_headers else None
                                changed_names = set(n.lower() for n in appended_names + updated_names)
                                verify_rows = [
                                    row for row in verify_ws.iter_rows(min_row=2, values_only=True)
                                    if name_idx is not None and row[name_idx] and str(row[name_idx]).strip().lower() in changed_names
                                ]
                                st.dataframe(
                                    pd.DataFrame(verify_rows, columns=verify_headers),
                                    use_container_width=True, hide_index=True
                                )

                            st.download_button(
                                label="💾 Download Updated Master Excel",
                                data=updated_bytes.getvalue(),
                                file_name=master_file.name,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Sync error: {e}")
                            import traceback
                            st.code(traceback.format_exc())
                elif validation_issues:
                    st.error("❌ Fix the validation issues above before syncing")
        else:
            st.info("📭 No records match the selected scope above")

    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WAITLIST
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("⏳ Waitlist Management")

    show_removed = st.checkbox(
        "Show removed students too (Declined / Site Withdraw)",
        help="Off by default — students disappear from this list once set to Declined or Site Withdraw."
    )

    try:
        active_statuses = ["On Waitlist", "Site Decision", "Declined", "Site Withdraw"] if show_removed else ["On Waitlist", "Site Decision"]
        waitlisted = supabase.table("allocation_students").select("*") \
            .in_("waitlist_status", active_statuses).execute()

        records = waitlisted.data
        if records:
            for r in records:
                with st.container(border=True):
                    st.markdown(f"**{r.get('student_name', 'Unknown')}** — {r.get('school', '')} • Year {r.get('year_level', '')}")
                    st.caption(f"Current status: {r.get('waitlist_status', '')}")

                    c1, c2 = st.columns([2, 1])
                    with c1:
                        status_options = ["On Waitlist", "Declined", "Site Decision", "Site Withdraw"]
                        current = r.get('waitlist_status')
                        new_status = st.selectbox(
                            "Set status", status_options,
                            index=status_options.index(current) if current in status_options else 0,
                            key=f"status_{r['id']}"
                        )
                    with c2:
                        st.write("")
                        st.write("")
                        if st.button("💾 Update Status", key=f"update_{r['id']}", use_container_width=True):
                            supabase.table("allocation_students").update(
                                {"waitlist_status": new_status}
                            ).eq("id", r["id"]).execute()
                            st.success(f"Status updated to {new_status}")
                            st.rerun()

                    with st.expander(f"🎓 Allocate {r.get('student_name', 'this student')} now"):
                        with st.form(f"allocate_from_waitlist_{r['id']}"):
                            acol1, acol2, acol3 = st.columns(3)
                            with acol1:
                                alloc_program = st.selectbox("Program *", PROGRAMS, key=f"prog_{r['id']}")
                            with acol2:
                                alloc_start = st.date_input("Allocation Date", value=None, key=f"start_{r['id']}")
                            with acol3:
                                alloc_worker = st.selectbox("Focus Teacher", [""] + STAFF_NAMES, key=f"worker_{r['id']}")

                            if st.form_submit_button("✅ Allocate Now", type="primary", use_container_width=True):
                                supabase.table("allocation_students").update({
                                    "outcome": "Allocated",
                                    "program": alloc_program,
                                    "start_after": alloc_start.isoformat() if alloc_start else None,
                                    "case_worker": alloc_worker or None,
                                    "actioned_by": alloc_worker or None,
                                    "waitlist_status": "Not Applicable",
                                    "allocated_from_waitlist": "Yes",
                                }).eq("id", r["id"]).execute()
                                st.success(f"✅ {r.get('student_name')} allocated!")
                                st.balloons()
                                st.rerun()
        else:
            st.info("No students currently on the waitlist.")
    except Exception as e:
        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ADMIN
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.header("⚙️ Admin — Manage Dropdown Lists")
    st.caption(
        "Add or remove options for the tool's dropdowns without needing a code change. "
        "Changes here take effect the next time the tool loads."
    )

    admin_password = st.text_input("🔐 Enter admin password", type="password", key="admin_pw")
    if admin_password.strip() != "secret2026":
        if admin_password:
            st.error("❌ Incorrect password.")
        st.stop()

    st.success("✅ Access granted")

    MANAGED_LISTS = {
        "Focus Teacher": ("focus_teacher", DEFAULT_STAFF_NAMES),
        "Program": ("program", DEFAULT_PROGRAMS),
        "Medical Condition Type": ("medical_condition_type", DEFAULT_MEDICAL_CONDITION_TYPES),
        "IESP Funding Option": ("iesp_funding_option", DEFAULT_IESP_OPTIONS),
    }

    list_label = st.selectbox("Which list do you want to manage?", list(MANAGED_LISTS.keys()))
    list_name, default_values = MANAGED_LISTS[list_label]

    try:
        supabase.table("dropdown_options").select("id").limit(1).execute()
        table_exists = True
        table_error = None
    except Exception as e:
        table_exists = False
        table_error = str(e)

    if not table_exists:
        st.error(
            "The `dropdown_options` table doesn't exist in Supabase yet (or couldn't be reached). "
            "Run this once in the Supabase SQL editor, then refresh this page:"
        )
        st.code(
            "CREATE TABLE dropdown_options (\n"
            "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    list_name TEXT NOT NULL,\n"
            "    option_value TEXT NOT NULL,\n"
            "    sort_order INTEGER DEFAULT 0\n"
            ");",
            language="sql"
        )
        with st.expander("Technical details"):
            st.code(table_error or "No error detail available")
        st.stop()

    current = supabase.table("dropdown_options").select("*") \
        .eq("list_name", list_name).order("sort_order").execute().data

    if not current:
        st.info(f"No custom options saved yet for **{list_label}** — currently using the built-in defaults below.")
        st.write(", ".join(default_values))
        if st.button(f"📋 Load these {len(default_values)} defaults into the editable list"):
            for i, val in enumerate(default_values):
                supabase.table("dropdown_options").insert(
                    {"list_name": list_name, "option_value": val, "sort_order": i}
                ).execute()
            st.rerun()
    else:
        st.markdown(f"**Current {list_label} options:**")
        for item in current:
            ccol1, ccol2 = st.columns([4, 1])
            with ccol1:
                st.write(item["option_value"])
            with ccol2:
                if st.button("🗑️ Remove", key=f"rm_{item['id']}"):
                    supabase.table("dropdown_options").delete().eq("id", item["id"]).execute()
                    st.rerun()

        st.markdown("---")
        with st.form(f"add_option_{list_name}", clear_on_submit=True):
            new_value = st.text_input(f"Add a new {list_label}")
            if st.form_submit_button("➕ Add") and new_value.strip():
                next_order = max([c.get("sort_order", 0) for c in current], default=-1) + 1
                supabase.table("dropdown_options").insert(
                    {"list_name": list_name, "option_value": new_value.strip(), "sort_order": next_order}
                ).execute()
                st.rerun()

st.caption("CLC-LBU Allocation Meetings Tool")
