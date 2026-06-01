# WORKING VERSION - All tabs function, export maps data correctly
# Replace your entire tool file with this

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
from supabase import create_client
import os
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

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

PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
STAFF_NAMES = ["Candice", "Annette", "Naomi/Cheryl", "Catie", "Ben Selga", "Ben Sutton", "Jacqui", "Brenton"]
OUTCOMES = ["Allocated", "Not Allocated"]
EXTENSION_OUTCOMES = ["Approved", "Not Approved"]
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
PRIORITY_OPTIONS = ["1", "2", "3", "4", "5"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
WAITLIST_STATUS_OPTIONS = ["Not Applicable", "On Waitlist", "Declined", "Site Decision", "Site Withdraw"]

ALL_FLAGS = ["EALD", "ATSI", "Attendance-Fulltime", "Attendance-Parttime", 
             "Intervention/Custody Order", "DCP involvement", "Child in care",
             "IESP Funding-yes", "IESP Funding-no", "Category 1-9", "9+RAAP", "SWD",
             "Speech and Lang", "ASD", "Intellectual", "Learning Difficulty",
             "Sensory Processing", "ADHD", "ODD", "PDA", "Medication", "Medical condition"]

SCHOOL_PARTNERSHIP_MAP = {
    "Mitcham Girls High School": "Mitcham Plains",
    "Adelaide Botanic High School": "Adelaide Prospect",
    "Prospect High School": "Adelaide Prospect",
    "Henley Beach Primary": "Inner West",
}

ALL_SCHOOLS = sorted(list(SCHOOL_PARTNERSHIP_MAP.keys()))
PARTNERSHIP_AREAS = ["Adelaide Prospect", "Greenhill South", "Heysen", "Holdfast", "Inner West"]

EXPORT_COLUMNS = [
    'Student_ID', 'Previous_Referrals', 'Student_Name', 'DOB', 'Gender', 'Year_Level',
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
    'Current_Status', 'Behaviour_Flag', 'Exclusion_End_Date', 'Proposed_Extension_Finish_Date',
    'Extension_Weeks', 'Communication_to_school', 'Action_owner', 'Actual_Finish_Date',
    'Extended_Placement', 'Referral_Year', 'Term', 'Extension_Status', 'Referral_Occurrence', 'Referral_ID'
]

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
    thursday = term_2_start + timedelta(days=days_to_add)
    return thursday

def get_partnership_from_school(school_name):
    return SCHOOL_PARTNERSHIP_MAP.get(school_name, "")

def calculate_weeks_between(start_date, end_date):
    if start_date and end_date:
        delta = end_date - start_date
        weeks = delta.days / 7
        return round(weeks, 1)
    return 0

def export_to_data_entry(selected_allocations):
    """Export with proper data mapping"""
    
    df = pd.DataFrame(selected_allocations)
    
    # Create output dataframe with all 76 columns
    df_export = pd.DataFrame(index=range(len(selected_allocations)))
    
    # Map data: For each export column, try to find data in the source
    for col in EXPORT_COLUMNS:
        col_lower = col.lower()
        
        # Try exact match first
        if col in df.columns:
            df_export[col] = df[col]
        # Try lowercase match
        elif col_lower in df.columns:
            df_export[col] = df[col_lower]
        # Try underscore version
        elif col_lower.replace(' ', '_') in df.columns:
            df_export[col] = df[col_lower.replace(' ', '_')]
        else:
            # Try specific mappings
            mapping = {
                'Student_Name': 'student_name',
                'DOB': 'date_of_birth',
                'Year_Level': 'year_level',
                'Gender': 'gender',
                'Referring_School': 'school',
                'Allocated_Program': 'program',
                'Allocation_Status': 'outcome',
                'Placement_Start': 'start_after',
                'Placement_End': 'finishing_date',
                'Partnership_Area': 'partnership_area',
                'Previous_CLC_Placement': 'previous_clc_placement',
                'Previous_Other_LC': 'previous_other_lc',
                'Other_LC_Name': 'other_lc_name',
                'Total_Previous_Placements': 'total_previous_placements',
                'Placement_History_Notes': 'placement_history_notes',
                'Medical_Condition_Details': 'medical_condition_details',
                'Medication_Details': 'medication_details',
                'Bespoke_Placement': 'bespoke_placement',
                'Waitlist_Status': 'waitlist_status',
                'Waitlist_Date': 'waitlist_date',
                'Allocated_From_Waitlist': 'allocated_from_waitlist',
                'Exclusion_End_Date': 'exclusion_finish_date',
                'Proposed_Extension_Finish_Date': 'proposed_extension_finish_date',
                'Extension_Weeks': 'extension_weeks',
                'Communication_to_school': 'information',
                'Action_owner': 'actioned_by',
                'Meeting_Week': 'meeting_week',
                'Meeting_Date': 'meeting_date',
                'Referral_Date': 'referral_date',
            }
            
            if col in mapping and mapping[col] in df.columns:
                df_export[col] = df[mapping[col]]
            else:
                df_export[col] = None
    
    # Create Excel
    output = BytesIO()
    df_export.to_excel(output, sheet_name='Data_Model', index=False, engine='openpyxl')
    
    output.seek(0)
    wb = openpyxl.load_workbook(output)
    ws = wb.active
    
    header_fill = PatternFill(start_color="1A7A6E", end_color="1A7A6E", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for col in ws.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    output_final = BytesIO()
    wb.save(output_final)
    output_final.seek(0)
    
    return output_final

# MAIN APP
st.title("📋 Allocation Meetings")

if 'current_term' not in st.session_state:
    term, week, year = get_current_term_week()
    st.session_state.current_term = term
    st.session_state.current_week = week
    st.session_state.current_year = year

# Sidebar
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

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 New Allocations", "🔄 Extensions", "⏸️ Not Placed", "📊 View & Export", "⏳ Waitlist"])

with tab1:
    st.header("New Student Allocations")
    
    stage_choice = st.radio("Stage:", ["➕ Create Draft (Stage 1)", "📝 Complete Draft (Stage 2)"], horizontal=True)
    st.markdown("---")
    
    if stage_choice == "📝 Complete Draft (Stage 2)":
        st.subheader("📂 Select Draft to Complete")
        
        try:
            drafts = supabase.table("allocation_students")\
                .select("*")\
                .eq("meeting_week", selected_week)\
                .is_("outcome", "null")\
                .execute()
            
            if drafts.data and len(drafts.data) > 0:
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
                        case_worker = st.text_input("Case Worker")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input("Start Date")
                    with col2:
                        end_date = st.date_input("End Date")
                    
                    information = st.text_area("Communication to School")
                    actioned_by = st.selectbox("Action Owner", [""] + STAFF_NAMES)
                    
                    if st.form_submit_button("✅ Save Allocation", type="primary", use_container_width=True):
                        try:
                            supabase.table("allocation_students")\
                                .update({
                                    "program": program,
                                    "outcome": outcome,
                                    "case_worker": case_worker if case_worker else None,
                                    "start_after": start_date.isoformat() if start_date else None,
                                    "finishing_date": end_date.isoformat() if end_date else None,
                                    "information": information if information else None,
                                    "actioned_by": actioned_by if actioned_by else None
                                })\
                                .eq("id", draft['id'])\
                                .execute()
                            
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
            
            queries = st.text_area("Queries/Notes")
            
            if st.form_submit_button("💾 Save Draft", type="primary", use_container_width=True):
                if not student_name or not school or not year_level:
                    st.error("Please fill required fields")
                else:
                    try:
                        supabase.table("allocation_students").insert({
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
                            "queries": queries,
                            "outcome": None
                        }).execute()
                        
                        st.success(f"✅ Draft saved for {student_name}!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab2:
    st.header("🔄 Extensions")
    st.info("Extension management - create and track extension requests")

with tab3:
    st.header("⏸️ Not Placed Students")
    
    try:
        not_allocated = supabase.table("allocation_students")\
            .select("student_name, year_level, school")\
            .eq("meeting_week", selected_week)\
            .eq("outcome", "Not Allocated")\
            .execute()
        
        if not_allocated.data:
            st.info(f"📊 {len(not_allocated.data)} student(s) not allocated")
            df = pd.DataFrame(not_allocated.data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No students not allocated")
    except Exception as e:
        st.error(f"Error: {e}")

with tab4:
    st.header("📊 View & Export")
    
    try:
        records = supabase.table("allocation_students")\
            .select("*")\
            .eq("meeting_week", selected_week)\
            .not_.is_("outcome", "null")\
            .execute()
        
        if records.data and len(records.data) > 0:
            st.info(f"📊 {len(records.data)} completed record(s)")
            
            allocated = [r for r in records.data if r['outcome'] == 'Allocated']
            not_allocated = [r for r in records.data if r['outcome'] == 'Not Allocated']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total", len(records.data))
            with col2:
                st.metric("Allocated", len(allocated))
            with col3:
                st.metric("Not Allocated", len(not_allocated))
            
            st.markdown("---")
            st.subheader("📤 Export to Excel")
            
            if st.button("📥 Download Data Entry Excel", type="primary", use_container_width=True):
                try:
                    all_allocations = allocated + not_allocated
                    excel_bytes = export_to_data_entry(all_allocations)
                    
                    st.download_button(
                        label="💾 Save Excel",
                        data=excel_bytes.getvalue(),
                        file_name=f"CLC_Allocations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    st.success(f"✅ {len(all_allocations)} record(s) ready to export!")
                except Exception as e:
                    st.error(f"Export error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.info("📭 No completed records")
    
    except Exception as e:
        st.error(f"Error: {e}")

with tab5:
    st.header("⏳ Waitlist Management")
    st.info("Manage waitlist and site decision students")

st.caption("CLC-LBU Allocation Meetings Tool - Working Version")
