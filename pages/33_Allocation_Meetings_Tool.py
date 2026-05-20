import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
from supabase import create_client
import os
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Page config
st.set_page_config(
    page_title="Allocation Meetings - CLC-LBU",
    page_icon="📋",
    layout="wide"
)

# Initialize Supabase
@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_supabase()

# Define constants
PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
# NEW: Comprehensive flag categories organized by type
LANGUAGE_CULTURAL_FLAGS = ["EALD", "ATSI"]
ATTENDANCE_FLAGS = ["Attendance-Fulltime", "Attendance-Parttime"]
CARE_CUSTODY_FLAGS = ["Intervention/Custody Order", "DCP involvement", "Child in care"]
FUNDING_FLAGS = ["IESP Funding-yes", "IESP Funding-no", "IESP Grant", 
                 "Category 1", "Category 2", "Category 3", "Category 4", "Category 5",
                 "Category 6", "Category 7", "Category 8", "Category 9", "9+RAAP", "SWD"]
SUPPORT_NEEDS_FLAGS = ["Speech and Lang", "ASD", "Intellectual", "Learning Difficulty", 
                       "Sensory Processing", "ADHD", "ODD", "PDA"]
MEDICAL_FLAGS = ["Medication", "Medical condition"]

# Combine all for storage
ALL_FLAGS = (LANGUAGE_CULTURAL_FLAGS + ATTENDANCE_FLAGS + CARE_CUSTODY_FLAGS + 
             FUNDING_FLAGS + SUPPORT_NEEDS_FLAGS + MEDICAL_FLAGS)
STAFF_NAMES = ["Brenton McGorman", "Caitie Hook", "Ben Selga", "Ben Sutton", "Jacqui Simpson"]
OUTCOMES = ["Allocated", "Not Allocated"]
EXTENSION_OUTCOMES = ["Approved", "Not Approved"]

# NEW: Additional options
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
PRIORITY_OPTIONS = ["Standard", "High", "Urgent"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
WAITLIST_STATUS_OPTIONS = ["Not Applicable", "On Waitlist", "Declined"]

# SCHOOL-PARTNERSHIP MAPPING (from government PDF)
SCHOOL_PARTNERSHIP_MAP = {
    "Bellevue Heights PS": "Mitcham Hills",
    "Challa Gardens PS": "Inner West",
    "Clovelly Park PS": "Marion Inland",
    "Cowandilla PS": "West Torrens",
    "Findon HS": "Inner West",
    "Hendon PS": "Western Adelaide Shores",
    "Highgate School": "Greenhill South",
    "Le Fevre HS": "Le Fevre Peninsula",
    "Mount Barker Primary School": "Heysen",
    "Mount Barker Primary": "Heysen",
    "Ocean View P-12 College": "Le Fevre Peninsula",
    "Paralowie R-12": "Orion",
    "Paralowie School": "Orion",
    "Walkerville PS": "Adelaide Prospect",
    "Warradale PS": "Holdfast",
    "West Lakes Shore School": "Western Adelaide Shores",
    "West Lakes Shores": "Western Adelaide Shores"
}

# All schools (sorted for dropdown)
ALL_SCHOOLS = sorted(list(SCHOOL_PARTNERSHIP_MAP.keys()))

# All partnerships (sorted)
PARTNERSHIP_AREAS = [
    "Adelaide Prospect", "Anangu Lands", "Barossa Valley", "Beach Road",
    "Berri & Barmera", "Blue Lake", "Campbell", "Central East", "Central Eyre 1", "Central Eyre 2",
    "Coorong & Mallee", "Elizabeth", "Far North", "Far West", "Fleurieu", "Flinders",
    "Golden Way", "Goyder & Light", "Greater Gawler", "Greenhill South", "Heysen",
    "Holdfast", "Hollywood Lakes and Gardens", "Inner West", "Kangaroo Island",
    "Le Fevre Peninsula", "Lower Mid North", "Marion Coast", "Marion Inland",
    "Mid North Clare", "Mitcham Hills", "Mitcham Plains", "Modbury", "Montague",
    "Morialta", "Mount Lofty", "Murraylands", "Northern Yorke", "Orion",
    "Panalatinga", "Peachey", "Pirie", "Port Augusta - Quorn", "Port Lincoln",
    "Renmark Loxton", "River Hub", "Salisbury", "Sea & Vines", "South East Coast & Vines",
    "South Valley", "Southern Yorke", "Tatiara", "Tea Tree Gully", "Torrens",
    "Torrens Valley", "Uleybury", "Upper Mid North", "Waikerie", "West Torrens",
    "Western Adelaide Shores", "Whyalla", "Wrattonbully"
]

# Program mapping for Data Entry format
PROGRAM_MAPPING = {
    "Junior Primary (JP)": "JP",
    "Primary Years (PY)": "PY",
    "Senior Years (SY)": "SY"
}

# Helper functions
def get_current_term_week():
    """Calculate current term and week based on SA school calendar"""
    today = datetime.now().date()
    year = today.year
    
    # Term 2 2026 dates
    term_2_start = datetime(2026, 4, 27).date()
    term_2_end = datetime(2026, 7, 3).date()
    
    if term_2_start <= today <= term_2_end:
        weeks_in = ((today - term_2_start).days // 7) + 1
        return f"Term 2", weeks_in, year
    
    return "Term 2", 1, 2026

def get_meeting_weeks(term, year):
    """Generate list of meeting weeks for a term"""
    return [f"Week {i} {term}" for i in range(1, 11)]

def get_thursday_date(week_number, term, year):
    """Calculate Thursday date for a given week"""
    term_2_start = datetime(2026, 4, 27).date()
    days_to_add = (week_number - 1) * 7 + 3
    thursday = term_2_start + timedelta(days=days_to_add)
    return thursday

def get_partnership_from_school(school_name):
    """Auto-lookup partnership from school name"""
    return SCHOOL_PARTNERSHIP_MAP.get(school_name, "")

def map_flags_from_allocation(cat_funding, partnership):
    """Map comprehensive flags to Yes/No columns for export"""
    flags = {}
    
    # Parse JSON if string
    if isinstance(cat_funding, str):
        try:
            cat_funding = json.loads(cat_funding)
        except:
            cat_funding = []
    if isinstance(partnership, str):
        try:
            partnership = json.loads(partnership)
        except:
            partnership = []
    
    # Combine all flags
    all_flags = cat_funding + partnership
    
    # Map each possible flag to Yes/No
    for flag in ALL_FLAGS:
        flag_key = flag.replace(" ", "_").replace("/", "_").replace("+", "plus").replace("-", "_")
        flags[f"Flag_{flag_key}"] = "Yes" if flag in all_flags else "No"
    
    return flags

def export_to_data_entry(selected_allocations):
    """Generate Excel file in Data Entry format with ALL database fields"""
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data_Model"
    
    # Define headers - COMPLETE SET with comprehensive flags
    # Generate flag headers from ALL_FLAGS list
    flag_headers = [f"Flag_{flag.replace(' ', '_').replace('/', '_').replace('+', 'plus').replace('-', '_')}" 
                    for flag in ALL_FLAGS]
    
    headers = [
        "Student_ID", "Student_Name", "DOB", "Gender", "Year_Level", "Referring_School",
        "Referral_Date", "Allocation_Status", "Allocated_Program", 
        "Placement_Start", "Placement_End", "Partnership_Area",
        "Previous_CLC_Placement", "Previous_Other_LC", "Other_LC_Name",
        "Total_Previous_Placements", "Placement_History_Notes", "Priority_Level"
    ] + flag_headers + [
        "Bespoke_Placement",
        "Waitlist_Status", "Waitlist_Date", "Allocated_From_Waitlist",
        "Current_Status", "Exit_Reason", "Transition_Plan", "Notes"
    ]
    
    # Style header row
    header_fill = PatternFill(start_color="1A7A6E", end_color="1A7A6E", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(1, col, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Add data rows
    for row_num, allocation in enumerate(selected_allocations, 2):
        # Generate Student_ID
        student_id = f"STU-{datetime.now().year}-{row_num-1:03d}"
        
        # Get flags from categorical funding and partnership
        flags = map_flags_from_allocation(
            allocation.get('cat_funding', []),
            allocation.get('partnership', [])
        )
        
        # Map program
        program = allocation.get('program', '')
        mapped_program = PROGRAM_MAPPING.get(program, program)
        
        # Format dates
        dob = allocation.get('date_of_birth', '')
        if dob and isinstance(dob, str):
            try:
                dob = datetime.strptime(dob, '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                pass
        
        start_date = allocation.get('start_after', '')
        if start_date and isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                pass
        
        end_date = allocation.get('finishing_date', '')
        if end_date and isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                pass
        
        waitlist_date = allocation.get('waitlist_date', '')
        if waitlist_date and isinstance(waitlist_date, str):
            try:
                waitlist_date = datetime.strptime(waitlist_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                pass
        
        # Today's date as referral date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Build row data - COMPLETE SET with comprehensive flags
        # Generate flag header keys to match the flags dictionary
        flag_keys = [f"Flag_{flag.replace(' ', '_').replace('/', '_').replace('+', 'plus').replace('-', '_')}" 
                     for flag in ALL_FLAGS]
        
        # Get flag values in same order as headers
        flag_values = [flags.get(key, "No") for key in flag_keys]
        
        row_data = [
            student_id,                                          # 1. Student_ID
            allocation.get('student_name', '').upper(),         # 2. Student_Name
            dob,                                                 # 3. DOB
            allocation.get('gender', ''),                        # 4. Gender
            allocation.get('year_level', ''),                    # 5. Year_Level
            allocation.get('school', ''),                        # 6. Referring_School
            today,                                               # 7. Referral_Date
            "Allocated" if allocation.get('outcome') == 'Allocated' else "Waitlist",  # 8. Allocation_Status
            mapped_program,                                      # 9. Allocated_Program
            start_date,                                          # 10. Placement_Start
            end_date,                                            # 11. Placement_End
            allocation.get('partnership_area', ''),              # 12. Partnership_Area
            allocation.get('previous_clc_placement', 'No'),      # 13. Previous_CLC_Placement
            allocation.get('previous_other_lc', 'No'),           # 14. Previous_Other_LC
            allocation.get('other_lc_name', ''),                 # 15. Other_LC_Name
            allocation.get('total_previous_placements', 0),      # 16. Total_Previous_Placements
            allocation.get('placement_history_notes', ''),       # 17. Placement_History_Notes
            allocation.get('priority_level', 'Standard'),        # 18. Priority_Level
        ] + flag_values + [  # 19-51. All comprehensive flags (33 flags)
            allocation.get('bespoke_placement', 'No'),           # 52. Bespoke_Placement
            allocation.get('waitlist_status', 'Not Applicable'), # 53. Waitlist_Status
            waitlist_date,                                       # 54. Waitlist_Date
            allocation.get('allocated_from_waitlist', 'No'),     # 55. Allocated_From_Waitlist
            "Active",                                            # 56. Current_Status
            allocation.get('exit_reason', ''),                   # 57. Exit_Reason
            allocation.get('transition_plan', ''),               # 58. Transition_Plan
            allocation.get('notes', '')                          # 59. Notes
        ]
        
        # Write row
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row_num, col, value)
            cell.alignment = Alignment(horizontal="left", vertical="center")
    
    # Adjust column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return output

def export_to_excel(week_data):
    """Export meeting data to Excel (original format)"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Student Allocations
        if week_data['students']:
            df_students = pd.DataFrame(week_data['students'])
            
            # Expand JSON columns
            if 'cat_funding' in df_students.columns:
                df_students['cat_funding'] = df_students['cat_funding'].apply(
                    lambda x: ', '.join(json.loads(x)) if isinstance(x, str) else ', '.join(x) if x else ''
                )
            if 'partnership' in df_students.columns:
                df_students['partnership'] = df_students['partnership'].apply(
                    lambda x: ', '.join(json.loads(x)) if isinstance(x, str) else ', '.join(x) if x else ''
                )
            
            df_students.to_excel(writer, sheet_name='Student Allocations', index=False)
        
        # Extensions
        if week_data['extensions']:
            df_extensions = pd.DataFrame(week_data['extensions'])
            df_extensions.to_excel(writer, sheet_name='Extensions', index=False)
        
        # Not Placed
        if week_data['not_placed']:
            df_not_placed = pd.DataFrame(week_data['not_placed'])
            df_not_placed.to_excel(writer, sheet_name='Not Placed', index=False)
    
    output.seek(0)
    return output

# Main app
st.title("📋 Allocation Meetings")
st.markdown("**Two-Stage Workflow: Pre-Meeting → Meeting Day → Export**")
st.caption("✨ Smart autofill • Partnership auto-lookup • Draft system")

# Initialize session state
if 'current_term' not in st.session_state:
    term, week, year = get_current_term_week()
    st.session_state.current_term = term
    st.session_state.current_week = week
    st.session_state.current_year = year

if 'selected_draft_id' not in st.session_state:
    st.session_state.selected_draft_id = None

# Sidebar - Week Navigation
with st.sidebar:
    st.header("📅 Meeting Selection")
    
    # Term and Year
    col1, col2 = st.columns(2)
    with col1:
        term_options = ["Term 1", "Term 2", "Term 3", "Term 4"]
        st.session_state.current_term = st.selectbox(
            "Term",
            term_options,
            index=term_options.index(st.session_state.current_term)
        )
    
    with col2:
        st.session_state.current_year = st.selectbox(
            "Year",
            [2024, 2025, 2026],
            index=[2024, 2025, 2026].index(st.session_state.current_year)
        )
    
    # Week selector
    meeting_weeks = get_meeting_weeks(st.session_state.current_term, st.session_state.current_year)
    selected_week = st.selectbox(
        "Week",
        meeting_weeks,
        index=st.session_state.current_week - 1
    )
    
    # Extract week number
    week_number = int(selected_week.split()[1])
    st.session_state.current_week = week_number
    
    # Calculate meeting date (Thursday)
    meeting_date = get_thursday_date(
        week_number, 
        st.session_state.current_term, 
        st.session_state.current_year
    )
    
    st.info(f"**Meeting Date:** {meeting_date.strftime('%A, %B %d, %Y')}")
    
    # Quick navigation
    st.markdown("---")
    st.markdown("**Quick Actions**")
    
    if st.button("📥 Export Current Week", use_container_width=True):
        st.session_state.show_export = True
    
    if st.button("🔍 Search Archive", use_container_width=True):
        st.session_state.show_archive = True

# Main content area
meeting_week_label = f"{selected_week}"

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 New Allocations", 
    "🔄 Extensions", 
    "⏸️ Not Placed",
    "📊 View & Export"
])

# TAB 1: New Student Allocations - SIMPLIFIED TWO-STAGE
with tab1:
    st.header("New Student Allocations")
    
    # STAGE SELECTOR
    stage_choice = st.radio(
        "Select what you want to do:",
        ["➕ Create New Draft (Stage 1)", "📝 Complete Existing Draft (Stage 2)"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if stage_choice == "📝 Complete Existing Draft (Stage 2)":
        # STAGE 2: Load and complete draft
        st.subheader("📂 Select Draft to Complete")
        
        try:
            # Fetch ALL records for debugging
            all_records = supabase.table("allocation_students")\
                .select("*")\
                .eq("meeting_week", meeting_week_label)\
                .eq("term", st.session_state.current_term)\
                .eq("year", st.session_state.current_year)\
                .execute()
            
            st.write(f"**Debug:** Found {len(all_records.data) if all_records.data else 0} total records")
            
            # Filter for drafts - outcome is NULL/None
            drafts_list = []
            if all_records.data:
                for record in all_records.data:
                    outcome = record.get('outcome')
                    # In Supabase, NULL comes back as None in Python
                    is_draft = (outcome is None)
                    st.write(f"- Record: {record.get('student_name')} | outcome='{outcome}' | type={type(outcome)} | is_draft={is_draft}")
                    if is_draft:
                        drafts_list.append(record)
            
            if not drafts_list:
                st.info("✅ No drafts found. Create a new draft in Stage 1.")
            else:
                draft_options = {f"{d['student_name']} ({d.get('school', 'No school')})": d for d in drafts_list}
                
                selected_draft_display = st.selectbox(
                    f"Select one of {len(drafts_list)} draft(s):",
                    list(draft_options.keys())
                )
                
                draft = draft_options[selected_draft_display]
                
                # Show what was already entered
                st.success(f"✅ Loaded draft for: **{draft['student_name']}**")
                
                with st.expander("👀 View Pre-Entered Information", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Name:** {draft.get('student_name')}")
                        st.write(f"**School:** {draft.get('school')}")
                        st.write(f"**Partnership:** {draft.get('partnership_area')}")
                    with col2:
                        st.write(f"**DOB:** {draft.get('date_of_birth', 'Not entered')}")
                        st.write(f"**Gender:** {draft.get('gender', 'Not entered')}")
                        st.write(f"**Year Level:** {draft.get('year_level')}")
                    with col3:
                        st.write(f"**Priority:** {draft.get('priority_level', 'Standard')}")
                        st.write(f"**Previous CLC:** {draft.get('previous_clc_placement', 'No')}")
                        queries_text = draft.get('queries') or 'None'
                st.write(f"**Queries:** {queries_text[:50]}..." if len(queries_text) > 50 else f"**Queries:** {queries_text}")
                
                st.markdown("---")
                st.markdown("### 🎯 Complete Allocation on Meeting Day")
                
                with st.form("complete_draft_form"):
                    # SECTION 5: Outcome
                    st.markdown("### 5️⃣ Allocation Outcome")
                    col1, col2 = st.columns(2)
                    with col1:
                        outcome = st.selectbox("Outcome *", [""] + OUTCOMES)
                    with col2:
                        details = st.text_area("Outcome Details", height=100)
                    
                    # Only show these sections if Allocated
                    if outcome == "Allocated":
                        # SECTION 6: Waitlist
                        st.markdown("---")
                        st.markdown("### 6️⃣ Waitlist Information")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            waitlist_status = st.selectbox("Waitlist Status", WAITLIST_STATUS_OPTIONS)
                        with col2:
                            if waitlist_status == "On Waitlist":
                                # Waitlist date: 1 year ago to 1 year from now
                                waitlist_min = datetime.now().date() - timedelta(days=365)
                                waitlist_max = datetime.now().date() + timedelta(days=365)
                                waitlist_date = st.date_input("Waitlist Date", value=None, min_value=waitlist_min, max_value=waitlist_max)
                            else:
                                waitlist_date = None
                        with col3:
                            if waitlist_status == "On Waitlist":
                                allocated_from_waitlist = st.selectbox("Allocated from Waitlist?", ["No", "Yes"])
                            else:
                                allocated_from_waitlist = "No"
                        
                        # SECTION 7: Program & Placement
                        st.markdown("---")
                        st.markdown("### 7️⃣ Program & Placement")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            program = st.selectbox("Program *", [""] + PROGRAMS)
                        with col2:
                            # Exclusion start date: Jan 1, 2026 to end of 2028
                            start_min = datetime(2026, 1, 1).date()
                            start_max = datetime(2028, 12, 31).date()
                            start_after = st.date_input("Exclusion Start Date", value=None, min_value=start_min, max_value=start_max)
                        with col3:
                            # Exclusion end date: Jan 1, 2026 to end of 2028
                            finish_min = datetime(2026, 1, 1).date()
                            finish_max = datetime(2028, 12, 31).date()
                            finishing_date = st.date_input("Exclusion End Date", value=None, min_value=finish_min, max_value=finish_max)
                        with col4:
                            bespoke_placement = st.selectbox("Bespoke Placement?", ["No", "Yes"])
                        
                        if bespoke_placement == "Yes":
                            st.info("💡 **Bespoke:** Year level doesn't match standard program")
                        
                        # SECTION 8: Case Support Team
                        st.markdown("---")
                        st.markdown("### 8️⃣ Case Support Team")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            case_worker = st.selectbox("Case Worker", [""] + STAFF_NAMES)
                        with col2:
                            bsc = st.text_input("BSE (Behaviour Support Educator)")
                        with col3:
                            school_contact = st.text_input("School Contact")
                        
                        notes = st.text_area("Additional Notes", height=80)
                    else:
                        # Not allocated - set defaults (None for database fields)
                        waitlist_status = "Not Applicable"
                        waitlist_date = None
                        allocated_from_waitlist = "No"
                        program = None  # Must be None, not empty string (database constraint)
                        start_after = None
                        finishing_date = None
                        bespoke_placement = "No"
                        case_worker = None  # None instead of empty string
                        bsc = None  # None instead of empty string
                        school_contact = None  # None instead of empty string
                        notes = None  # None instead of empty string
                    
                    # Submit
                    st.markdown("---")
                    submitted = st.form_submit_button("✅ Complete Allocation", type="primary", use_container_width=True)
                    
                    if submitted:
                        # Validation
                        missing = []
                        if not outcome:
                            missing.append("Outcome")
                        if outcome == "Allocated" and not program:
                            missing.append("Program")
                        
                        if missing:
                            st.error(f"⚠️ Please fill in required fields: {', '.join(missing)}")
                        else:
                            try:
                                # Helper: Convert empty strings to None for database
                                def none_if_empty(value):
                                    return None if value == "" or value == [] else value
                                
                                # Update the draft with completion data
                                update_data = {
                                    "outcome": outcome,
                                    "details": none_if_empty(details),
                                    "waitlist_status": waitlist_status,
                                    "waitlist_date": waitlist_date.isoformat() if waitlist_date else None,
                                    "allocated_from_waitlist": allocated_from_waitlist,
                                    "program": none_if_empty(program),  # Convert "" to None
                                    "start_after": start_after.isoformat() if start_after else None,
                                    "finishing_date": finishing_date.isoformat() if finishing_date else None,
                                    "bespoke_placement": bespoke_placement,
                                    "case_worker": none_if_empty(case_worker),  # Convert "" to None
                                    "bsc": none_if_empty(bsc),  # Convert "" to None
                                    "school_contact": none_if_empty(school_contact),  # Convert "" to None
                                    "notes": none_if_empty(notes)  # Convert "" to None
                                }
                                
                                # Debug: Show what we're sending
                                st.write("🔍 **Debug: Data being saved:**")
                                st.json({
                                    "outcome": update_data["outcome"],
                                    "program": update_data["program"],
                                    "case_worker": update_data["case_worker"],
                                    "bsc": update_data["bsc"]
                                })
                                
                                result = supabase.table("allocation_students")\
                                    .update(update_data)\
                                    .eq("id", draft['id'])\
                                    .execute()
                                
                                st.success(f"✅ Allocation completed for {draft['student_name']}!")
                                st.balloons()
                                st.info("🎉 This student is now ready for export in the View & Export tab")
                                
                            except Exception as e:
                                st.error(f"❌ Error completing allocation: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
                
        except Exception as e:
            st.error(f"Error: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    else:
        # STAGE 1: Create new draft - FULL VERSION
        st.subheader("➕ Stage 1: Pre-Meeting Draft")
        st.caption("Leadership enters student information before allocation meeting")
        
        with st.form("create_draft_form", clear_on_submit=True):
            # SECTION 1: Student Information
            st.markdown("### 1️⃣ Student Information")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                student_name = st.text_input("Name *")
            with col2:
                # Date range: 20 years ago to today
                min_date = datetime.now().date() - timedelta(days=365*20)
                max_date = datetime.now().date()
                dob = st.date_input("Date of Birth", value=None, min_value=min_date, max_value=max_date)
            with col3:
                gender = st.selectbox("Gender", [""] + GENDER_OPTIONS)
            with col4:
                year_level = st.selectbox("Year Level *", [""] + YEAR_LEVELS)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                school = st.selectbox("Referring School * (searchable)", [""] + ALL_SCHOOLS)
            with col2:
                auto_partnership = get_partnership_from_school(school) if school else ""
                partnership_area = st.text_input("Partnership Area (auto-filled)", value=auto_partnership, disabled=True)
            with col3:
                priority_level = st.selectbox("Priority Level", [""] + PRIORITY_OPTIONS)
            
            # SECTION 2: Placement History
            st.markdown("---")
            st.markdown("### 2️⃣ Placement History")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                previous_clc = st.selectbox("Previous CLC Placement?", ["No", "Yes"])
            with col2:
                previous_other_lc = st.selectbox("Previous Other LC?", ["No", "Yes"])
            with col3:
                previously_referred = st.selectbox("Previously Referred?", ["No", "Yes"])
            with col4:
                if previous_other_lc == "Yes":
                    other_lc_name = st.text_input("Other LC Name")
                else:
                    other_lc_name = ""
            
            if previous_clc == "Yes" or previous_other_lc == "Yes" or previously_referred == "Yes":
                col1, col2 = st.columns(2)
                with col1:
                    total_placements = st.number_input("Total Previous Placements/Referrals", min_value=0, value=1)
                with col2:
                    placement_history_notes = st.text_input("Placement/Referral History Notes")
            else:
                total_placements = 0
                placement_history_notes = ""
            
            # SECTION 3: Student Flags (Comprehensive)
            st.markdown("---")
            st.markdown("### 3️⃣ Student Flags & Support Needs")
            st.caption("Select all that apply - organized by category")
            
            selected_flags = []
            
            # Row 1: Language/Cultural & Attendance
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Language & Cultural**")
                for flag in LANGUAGE_CULTURAL_FLAGS:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            
            with col2:
                st.write("**Attendance**")
                for flag in ATTENDANCE_FLAGS:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            
            # Row 2: Care/Custody & Medical
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Care & Custody**")
                for flag in CARE_CUSTODY_FLAGS:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            
            with col2:
                st.write("**Medical**")
                medical_condition_details = ""  # Initialize first
                for flag in MEDICAL_FLAGS:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
                
                # Medical condition details field - only show if checked
                if "Medical condition" in selected_flags:
                    medical_condition_details = st.text_input("Medical Condition Details", placeholder="Please specify medical condition")
            
            # Row 3: Funding (full width - lots of options)
            st.write("**Funding & Categories**")
            col1, col2, col3 = st.columns(3)
            funding_split = len(FUNDING_FLAGS) // 3 + 1
            
            with col1:
                for flag in FUNDING_FLAGS[:funding_split]:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            with col2:
                for flag in FUNDING_FLAGS[funding_split:funding_split*2]:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            with col3:
                for flag in FUNDING_FLAGS[funding_split*2:]:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            
            # Row 4: Support Needs (full width - lots of options)
            st.write("**Support Needs & Diagnoses**")
            col1, col2, col3 = st.columns(3)
            support_split = len(SUPPORT_NEEDS_FLAGS) // 3 + 1
            
            with col1:
                for flag in SUPPORT_NEEDS_FLAGS[:support_split]:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            with col2:
                for flag in SUPPORT_NEEDS_FLAGS[support_split:support_split*2]:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            with col3:
                for flag in SUPPORT_NEEDS_FLAGS[support_split*2:]:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
            
            # SECTION 4: Meeting Details
            st.markdown("---")
            st.markdown("### 4️⃣ Queries/Notes for Meeting")
            queries = st.text_area("Queries/Notes", height=100)
            
            # Submit
            st.markdown("---")
            submitted = st.form_submit_button("💾 Save Draft (Complete Later)", type="primary", use_container_width=True)
            
            if submitted:
                # Validation
                missing = []
                if not student_name:
                    missing.append("Name")
                if not year_level:
                    missing.append("Year Level")
                if not school:
                    missing.append("School")
                
                if missing:
                    st.error(f"⚠️ Please fill in required fields: {', '.join(missing)}")
                else:
                    try:
                        data = {
                            "meeting_week": meeting_week_label,
                            "meeting_date": meeting_date.isoformat(),
                            "term": st.session_state.current_term,
                            "year": st.session_state.current_year,
                            "student_name": student_name,
                            "school": school,
                            "date_of_birth": dob.isoformat() if dob else None,
                            "gender": gender,
                            "year_level": year_level,
                            "partnership_area": auto_partnership,
                            "priority_level": priority_level if priority_level else "Standard",
                            "previous_clc_placement": previous_clc,
                            "previous_other_lc": previous_other_lc,
                            "previously_referred": previously_referred,  # NEW
                            "other_lc_name": other_lc_name if previous_other_lc == "Yes" else None,
                            "total_previous_placements": total_placements,
                            "placement_history_notes": placement_history_notes,
                            "medical_condition_details": medical_condition_details if "Medical condition" in selected_flags else None,  # NEW
                            "cat_funding": json.dumps(selected_flags),  # All flags stored here
                            "partnership": json.dumps([]),  # Legacy field, kept empty
                            "queries": queries,
                            "outcome": None  # Draft status
                        }
                        
                        result = supabase.table("allocation_students").insert(data).execute()
                        st.success(f"✅ Draft saved for {student_name}! Complete on meeting day.")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error saving draft: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

# TAB 2: Extensions (placeholder)
with tab2:
    st.header("🔄 Extensions")
    st.info("Extension requests feature coming soon...")

# TAB 3: Not Placed (placeholder)
with tab3:
    st.header("⏸️ Not Placed")
    st.info("Not placed tracking feature coming soon...")

# TAB 4: View & Export
with tab4:
    st.header("📊 View & Export Completed Allocations")
    
    # Fetch completed allocations (outcome is NOT NULL)
    try:
        # Correct way to query for NOT NULL in Supabase
        completed = supabase.table("allocation_students")\
            .select("*")\
            .in_("outcome", ["Allocated", "Not Allocated"])\
            .order("created_at", desc=True)\
            .execute()
        
        st.write(f"**Debug:** Query returned {len(completed.data) if completed.data else 0} records")
        if completed.data:
            for record in completed.data:
                st.write(f"- {record.get('student_name')}: outcome={record.get('outcome')}")
        
        if not completed.data:
            st.info("📭 No completed allocations yet. Complete some drafts in the New Allocations tab!")
        else:
            st.success(f"✅ Found {len(completed.data)} completed allocation(s)")
            
            # Display table
            st.subheader("Completed Allocations")
            
            # Convert to simple display format
            display_data = []
            for record in completed.data:
                display_data.append({
                    "Student": record.get("student_name", ""),
                    "School": record.get("school", ""),
                    "Year": record.get("year_level", ""),
                    "Program": record.get("program", ""),
                    "Outcome": record.get("outcome", ""),
                    "Meeting": record.get("meeting_week", ""),
                    "Date": record.get("meeting_date", "")
                })
            
            st.dataframe(display_data, use_container_width=True)
            
            # Export section
            st.markdown("---")
            st.subheader("📤 Export to Excel")
            
            # Select allocations to export
            all_selected = st.checkbox("Select all", value=True)
            
            if all_selected:
                selected_ids = [r["id"] for r in completed.data]
            else:
                # Show checkboxes for individual selection
                st.write("Select allocations to export:")
                selected_ids = []
                for record in completed.data:
                    if st.checkbox(f"{record['student_name']} - {record.get('school', '')}", key=f"export_{record['id']}"):
                        selected_ids.append(record["id"])
            
            if st.button("📥 Download Excel", type="primary"):
                if not selected_ids:
                    st.error("Please select at least one allocation to export")
                else:
                    # Filter to selected records
                    to_export = [r for r in completed.data if r["id"] in selected_ids]
                    
                    try:
                        # Generate Excel
                        excel_bytes = export_to_data_entry(to_export)
                        
                        # Download button
                        st.download_button(
                            label="💾 Save Excel File",
                            data=excel_bytes,
                            file_name=f"CLC_Allocations_{meeting_week_label.replace(' ', '_')}_{st.session_state.current_term.replace(' ', '_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success(f"✅ Excel file ready! {len(to_export)} allocation(s) exported.")
                        
                    except Exception as e:
                        st.error(f"Error generating Excel: {e}")
                        import traceback
                        st.code(traceback.format_exc())
    
    except Exception as e:
        st.error(f"Error loading allocations: {e}")
        import traceback
        st.code(traceback.format_exc())

# Caption
st.caption("CLC-LBU Allocation Meetings Tool V3 | Simplified Draft System")
