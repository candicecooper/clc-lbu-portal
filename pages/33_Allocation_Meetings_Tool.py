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

PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
STAFF_NAMES = ["Candice", "Annette", "Naomi", "Cheryl", "Caitie", "Ben Selga", "Ben Sutton", "Jacqui", "Brenton", "Vinnie", "Tom"]
OUTCOMES = ["Allocated", "Not Allocated"]
EXTENSION_OUTCOMES = ["Approved", "Not Approved"]
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
PRIORITY_OPTIONS = ["1", "2", "3", "4", "5"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
YES_NO = ["", "Yes", "No"]
WAITLIST_STATUS_OPTIONS = ["Not Applicable", "On Waitlist", "Declined", "Site Decision", "Site Withdraw"]

MEDICAL_CONDITION_TYPES = [
    "Anaphylaxis / Severe Allergy", "Asthma", "Diabetes (Type 1)", "Epilepsy / Seizure Disorder",
    "Cardiac Condition", "Genetic / Chromosomal Condition", "Physical Disability",
    "Gastrointestinal Condition", "Autoimmune Condition", "Hearing Impairment",
    "Vision Impairment", "Chronic Pain Condition", "Sleep Disorder", "Continence Condition",
    "Other Medical Condition"
]

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
    ("9+ RAAP", "Flag_9plusRAAP", "flag_9plusraap"),
]

FUNDING_CATEGORIES = [(f"Category {i}", f"Flag_Category_{i}", f"flag_category_{i}") for i in range(1, 10)]

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
    'Referral_Occurrence', 'Referral_ID'
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
    'Referral_Occurrence': None, 'Referral_ID': None,
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

@st.cache_data
def load_school_partnerships():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school_partnerships.csv")
    try:
        df = pd.read_csv(csv_path)
        df = df.dropna(subset=["School"])
        mapping = dict(zip(df["School"].str.strip(), df["Partnership_Area"].fillna("").str.strip()))
        if mapping:
            return mapping
    except Exception:
        pass
    return _FALLBACK_SCHOOLS

SCHOOL_PARTNERSHIP_MAP = load_school_partnerships()
ALL_SCHOOLS = sorted(SCHOOL_PARTNERSHIP_MAP.keys())
PARTNERSHIP_AREAS = sorted(set(SCHOOL_PARTNERSHIP_MAP.values()))

if len(SCHOOL_PARTNERSHIP_MAP) <= len(_FALLBACK_SCHOOLS):
    st.sidebar.warning(
        "⚠️ Full school list not found — showing a short fallback list. "
        "Upload `school_partnerships.csv` to the same portal folder as this page to load all schools."
    )

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_current_term_week():
    today = datetime.now().date()
    term_2_start = datetime(2026, 4, 27).date()
    term_2_end = datetime(2026, 7, 3).date()
    if term_2_start <= today <= term_2_end:
        weeks_in = ((today - term_2_start).days // 7) + 1
        return "Term 2", weeks_in, 2026
    return "Term 2", 1, 2026

def get_meeting_weeks(term, year):
    return [f"Week {i} {term}" for i in range(1, 11)]

def get_thursday_date(week_number, term, year):
    term_2_start = datetime(2026, 4, 27).date()
    days_to_add = (week_number - 1) * 7 + 3
    return term_2_start + timedelta(days=days_to_add)

def get_partnership_from_school(school_name):
    return SCHOOL_PARTNERSHIP_MAP.get(school_name, "")

def yn(value):
    """Normalise a checkbox/bool into the Yes/'' convention used in the master Excel."""
    return "Yes" if value else ""

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
    Append new records directly onto the user's real master Excel file, matching
    whatever column order that file already uses (read from its own header row).
    Returns (updated_workbook_bytes, sheet_name, appended_count, skipped_duplicates,
             unmatched_export_columns).
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

    # Find the Student_Name column (if present) for duplicate detection
    name_col_idx = header_index.get("Student_Name")
    existing_names = set()
    if name_col_idx is not None:
        for row in ws.iter_rows(min_row=2, values_only=True):
            if len(row) > name_col_idx and row[name_col_idx]:
                existing_names.add(str(row[name_col_idx]).strip().lower())

    unmatched_columns = [col for col in EXPORT_COLUMNS if col not in header_index]

    appended = 0
    skipped = []
    for record in records:
        student_name = str(record.get("student_name", "")).strip()
        if student_name and student_name.lower() in existing_names:
            skipped.append(student_name)
            continue

        new_row = [""] * len(existing_headers)
        for col in EXPORT_COLUMNS:
            if col not in header_index:
                continue
            db_field = FIELD_MAP.get(col)
            value = clean_value(record.get(db_field, "")) if db_field else ""
            new_row[header_index[col]] = value

        ws.append(new_row)
        appended += 1
        if student_name:
            existing_names.add(student_name.lower())

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output, sheet_name, appended, skipped, unmatched_columns

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
    with col1:
        st.session_state.current_term = st.selectbox("Term", ["Term 1", "Term 2", "Term 3", "Term 4"])
    with col2:
        st.session_state.current_year = st.selectbox("Year", [2024, 2025, 2026])

    meeting_weeks = get_meeting_weeks(st.session_state.current_term, st.session_state.current_year)
    selected_week = st.selectbox("Week", meeting_weeks, index=st.session_state.current_week - 1)
    week_number = int(selected_week.split()[1])

    meeting_date = get_thursday_date(week_number, st.session_state.current_term, st.session_state.current_year)
    st.info(f"**Meeting Date:** {meeting_date.strftime('%A, %B %d, %Y')}")
    st.caption(f"📚 {len(ALL_SCHOOLS)} schools loaded across {len(PARTNERSHIP_AREAS)} partnership areas")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📝 New Allocations", "🔄 Extensions", "⏸️ Not Placed", "📊 View & Export", "⏳ Waitlist"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NEW ALLOCATIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("New Student Allocations")
    stage_choice = st.radio("Stage:", ["➕ Create Draft (Stage 1)", "📝 Complete Draft (Stage 2)"], horizontal=True)
    st.markdown("---")

    if stage_choice == "📝 Complete Draft (Stage 2)":
        st.subheader("📂 Select Draft to Complete")
        try:
            drafts = supabase.table("allocation_students").select("*") \
                .eq("meeting_week", selected_week).is_("outcome", "null").execute()

            if drafts.data:
                draft_options = {d['student_name']: d for d in drafts.data}
                selected = st.selectbox("Select draft:", list(draft_options.keys()))
                draft = draft_options[selected]
                st.success(f"✅ Loaded: **{draft['student_name']}**")

                with st.form("complete_allocation"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        program = st.selectbox("Program *", PROGRAMS)
                    with col2:
                        outcome = st.selectbox("Outcome *", OUTCOMES)
                    with col3:
                        case_worker = st.selectbox("Action Owner", [""] + STAFF_NAMES)

                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input("Start Date", value=None)
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

                    if st.form_submit_button("✅ Save Allocation", type="primary", use_container_width=True):
                        try:
                            supabase.table("allocation_students").update({
                                "program": program,
                                "outcome": outcome,
                                "case_worker": case_worker or None,
                                "actioned_by": case_worker or None,
                                "start_after": start_date.isoformat() if start_date else None,
                                "finishing_date": end_date.isoformat() if end_date else None,
                                "bespoke_placement": yn(bespoke),
                                "information": information or None,
                                "waitlist_status": waitlist_status if outcome == "Not Allocated" else "Not Applicable",
                                "waitlist_date": waitlist_date.isoformat() if waitlist_date else None,
                                "exit_reason": exit_reason or None,
                                "transition_plan": transition_plan or None,
                                "notes": notes or None,
                            }).eq("id", draft['id']).execute()

                            st.success(f"✅ Allocation saved for {draft['student_name']}!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("✅ No drafts to complete. Create one in Stage 1.")
        except Exception as e:
            st.error(f"Error: {e}")

    else:
        st.subheader("➕ Create New Draft")

        with st.form("new_draft"):
            col1, col2, col3 = st.columns(3)
            with col1:
                student_name = st.text_input("Name *")
            with col2:
                dob = st.date_input("DOB", value=None)
            with col3:
                gender = st.selectbox("Gender", [""] + GENDER_OPTIONS)

            col1, col2, col3 = st.columns(3)
            with col1:
                school = st.selectbox("School *", [""] + ALL_SCHOOLS)
            with col2:
                auto_partnership = get_partnership_from_school(school) if school else ""
                partnership = st.text_input("Partnership", value=auto_partnership, disabled=True)
            with col3:
                year_level = st.selectbox("Year Level *", [""] + YEAR_LEVELS)

            col1, col2, col3 = st.columns(3)
            with col1:
                priority_level = st.selectbox("Priority Level", [""] + PRIORITY_OPTIONS)
            with col2:
                referral_date = st.date_input("Referral Date", value=None)
            with col3:
                previously_referred = st.selectbox("Previously Referred?", YES_NO)

            previous_referrals = st.text_input("Number of Previous Referrals")

            with st.expander("🏠 Placement History"):
                pcol1, pcol2, pcol3 = st.columns(3)
                with pcol1:
                    previous_clc_placement = st.selectbox("Previous CLC Placement?", YES_NO)
                with pcol2:
                    previous_other_lc = st.selectbox("Previous Other LC?", YES_NO)
                with pcol3:
                    other_lc_name = st.text_input("Other LC Name")
                total_previous_placements = st.text_input("Total Previous Placements")
                placement_history_notes = st.text_area("Placement History Notes")

            with st.expander("🏷️ Support Flags & Funding"):
                st.caption("These feed the Dashboard's disability & funding analytics directly.")
                flag_values = {}
                cols = st.columns(3)
                for i, (label, excel_col, db_col) in enumerate(BOOL_FLAGS):
                    with cols[i % 3]:
                        flag_values[db_col] = st.checkbox(label, key=f"draft_{db_col}")

                st.markdown("**Funding Categories**")
                fcols = st.columns(3)
                funding_values = {}
                for i, (label, excel_col, db_col) in enumerate(FUNDING_CATEGORIES):
                    with fcols[i % 3]:
                        funding_values[db_col] = st.checkbox(label, key=f"draft_{db_col}")

                acol1, acol2 = st.columns(2)
                with acol1:
                    attendance = st.selectbox("Attendance", ["", "Full-time", "Part-time"])
                with acol2:
                    iesp_funding = st.selectbox("IESP Funding", YES_NO)

            with st.expander("💊 Medical & Medication"):
                mcol1, mcol2 = st.columns(2)
                with mcol1:
                    has_medical = st.checkbox("Medical Condition")
                    medical_type = st.selectbox(
                        "Condition Type *", [""] + MEDICAL_CONDITION_TYPES,
                        disabled=not has_medical
                    )
                    medical_details = st.text_area("Medical Condition Details", disabled=not has_medical)
                with mcol2:
                    has_medication = st.checkbox("Medication")
                    medication_details = st.text_area("Medication Details", disabled=not has_medication)

            queries = st.text_area("Queries/Notes for Meeting")

            submitted = st.form_submit_button("💾 Save Draft", type="primary", use_container_width=True)
            if submitted:
                if not student_name or not school or not year_level:
                    st.error("Please fill required fields (Name, School, Year Level)")
                elif has_medical and not medical_type:
                    st.error("Please select a Medical Condition Type — required when Medical Condition is checked")
                else:
                    try:
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
                            "priority_level": priority_level if priority_level else "3",
                            "referral_date": referral_date.isoformat() if referral_date else None,
                            "previously_referred": previously_referred,
                            "previous_referrals": previous_referrals,
                            "previous_clc_placement": previous_clc_placement,
                            "previous_other_lc": previous_other_lc,
                            "other_lc_name": other_lc_name,
                            "total_previous_placements": total_previous_placements,
                            "placement_history_notes": placement_history_notes,
                            "flag_attendance_fulltime": yn(attendance == "Full-time"),
                            "flag_attendance_parttime": yn(attendance == "Part-time"),
                            "flag_iesp_funding_yes": yn(iesp_funding == "Yes"),
                            "flag_iesp_funding_no": yn(iesp_funding == "No"),
                            "flag_medication": yn(has_medication),
                            "medication_details": medication_details if has_medication else None,
                            "flag_medical_condition": yn(has_medical),
                            "medical_condition_details": (
                                f"{medical_type}: {medical_details}" if has_medical and medical_details
                                else medical_type if has_medical else None
                            ),
                            "queries": queries,
                            "outcome": None,
                        }
                        for db_col, val in flag_values.items():
                            record[db_col] = yn(val)
                        for db_col, val in funding_values.items():
                            record[db_col] = yn(val)

                        supabase.table("allocation_students").insert(record).execute()
                        st.success(f"✅ Draft saved for {student_name}!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXTENSIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("🔄 Extensions")
    st.info("Record an extension decision for a currently allocated student.")

    try:
        allocated = supabase.table("allocation_students").select("*").eq("outcome", "Allocated").execute()
        if allocated.data:
            options = {r['student_name']: r for r in allocated.data}
            chosen = st.selectbox("Select allocated student", list(options.keys()))
            record = options[chosen]

            with st.form("extension_form"):
                col1, col2 = st.columns(2)
                with col1:
                    ext_outcome = st.selectbox("Extension Outcome *", EXTENSION_OUTCOMES)
                with col2:
                    ext_weeks = st.text_input("Extension Weeks")

                col1, col2 = st.columns(2)
                with col1:
                    ext_date = st.date_input("Extension Decision Date", value=datetime.now().date())
                with col2:
                    proposed_finish = st.date_input("Proposed Extension Finish Date", value=None)

                ext_comm = st.text_area("Communication to School")
                ext_owner = st.selectbox("Action Owner", [""] + STAFF_NAMES)

                if st.form_submit_button("✅ Save Extension", type="primary", use_container_width=True):
                    try:
                        supabase.table("allocation_students").update({
                            "extension": yn(ext_outcome == "Approved"),
                            "extension_status": ext_outcome,
                            "extension_date": ext_date.isoformat() if ext_date else None,
                            "extension_weeks": ext_weeks,
                            "proposed_extension_finish_date": proposed_finish.isoformat() if proposed_finish else None,
                            "information": ext_comm or record.get("information"),
                            "actioned_by": ext_owner or record.get("actioned_by"),
                        }).eq("id", record["id"]).execute()
                        st.success(f"✅ Extension recorded for {chosen}!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("No allocated students found yet.")
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

    try:
        full_data = supabase.table("allocation_students").select("*") \
            .eq("meeting_week", selected_week).not_.is_("outcome", "null").execute()

        if full_data.data:
            allocated = [r for r in full_data.data if r.get('outcome') == 'Allocated']
            not_allocated = [r for r in full_data.data if r.get('outcome') == 'Not Allocated']

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(full_data.data))
            with col2:
                st.metric("Allocated", len(allocated))
            with col3:
                st.metric("Not Allocated", len(not_allocated))

            st.markdown("---")
            st.subheader("📋 Pre-Export Review & Validation")

            export_records = allocated + not_allocated
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
            with st.expander("Click to review records being exported", expanded=True):
                preview_data = [{
                    "Student": r.get('student_name', ''), "Year": r.get('year_level', ''),
                    "Program": r.get('program', ''), "School": r.get('school', ''),
                    "Outcome": r.get('outcome', ''), "Action Owner": r.get('actioned_by', ''),
                } for r in export_records]
                st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
                st.caption(f"📊 {len(export_records)} record(s) ready for export")

            st.markdown("---")
            st.subheader("🔄 Sync Directly Into Your Master Excel File")
            st.caption(
                "Upload your live CLC_Allocation_Dashboard file below — the tool matches its "
                "existing columns, skips students already in it, appends the rest, and gives you "
                "back the updated file ready to save over the SharePoint copy. No manual copy/paste."
            )

            master_file = st.file_uploader(
                "Upload master Excel file (e.g. CLC_Allocation_Dashboard_2026_WithNames.xlsx)",
                type=['xlsx'], key="master_upload"
            )

            if master_file is not None and not validation_issues:
                if st.button("🔄 Append & Download Updated Master File", type="primary", use_container_width=True):
                    try:
                        updated_bytes, sheet_used, appended, skipped, unmatched = sync_into_master_workbook(
                            master_file.getvalue(), export_records
                        )
                        st.success(f"✅ Appended {appended} new record(s) to the **{sheet_used}** sheet.")
                        if skipped:
                            st.warning(f"🔄 Skipped {len(skipped)} already-present student(s): {', '.join(skipped)}")
                        if unmatched:
                            st.info(
                                f"ℹ️ {len(unmatched)} field(s) had no matching column in your file and were left blank: "
                                f"{', '.join(unmatched)}"
                            )
                        st.download_button(
                            label="💾 Download Updated Master Excel",
                            data=updated_bytes.getvalue(),
                            file_name=master_file.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        st.caption("Save this file over your SharePoint copy to complete the sync.")
                    except Exception as e:
                        st.error(f"Sync error: {e}")
                        import traceback
                        st.code(traceback.format_exc())
            elif validation_issues:
                st.error("❌ Fix the validation issues above before syncing")

            st.markdown("---")
            with st.expander("📥 Alternative: download new rows only (for manual paste)"):
                if st.button("📥 Download New Rows Only", use_container_width=True):
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
        else:
            st.info("📭 No completed records for this week")

    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WAITLIST
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("⏳ Waitlist Management")
    try:
        waitlisted = supabase.table("allocation_students").select("*") \
            .not_.in_("waitlist_status", ["Not Applicable", ""]).execute()

        records = [r for r in waitlisted.data if r.get("waitlist_status")]
        if records:
            for r in records:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 2])
                    with c1:
                        st.markdown(f"**{r.get('student_name', 'Unknown')}** — {r.get('school', '')}")
                        st.caption(f"Status: {r.get('waitlist_status', '')} • Year {r.get('year_level', '')}")
                    with c2:
                        if st.button("Move to Waitlist", key=f"wl_{r['id']}", use_container_width=True):
                            supabase.table("allocation_students").update(
                                {"waitlist_status": "On Waitlist"}
                            ).eq("id", r["id"]).execute()
                            st.rerun()
                    with c3:
                        if st.button("Site Withdraw", key=f"sw_{r['id']}", use_container_width=True):
                            supabase.table("allocation_students").update(
                                {"waitlist_status": "Site Withdraw"}
                            ).eq("id", r["id"]).execute()
                            st.rerun()
        else:
            st.info("No students currently on the waitlist.")
    except Exception as e:
        st.error(f"Error: {e}")

st.caption("CLC-LBU Allocation Meetings Tool")
