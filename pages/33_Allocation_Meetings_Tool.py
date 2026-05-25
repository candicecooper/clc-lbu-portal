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
STAFF_NAMES = ["Candice", "Annette", "Naomi/Cheryl", "Catie", "Ben Selga", "Ben Sutton", "Jacqui", "Brenton"]
OUTCOMES = ["Allocated", "Not Allocated"]
EXTENSION_OUTCOMES = ["Approved", "Not Approved"]

# NEW: Additional options
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
PRIORITY_OPTIONS = ["1", "2", "3", "4", "5"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
WAITLIST_STATUS_OPTIONS = ["Not Applicable", "On Waitlist", "Declined", "Site Decision", "Site Withdraw"]
MEDICAL_CONDITION_TYPES = [
    "Asthma", "Diabetes (Type 1)", "Diabetes (Type 2)", "Epilepsy/Seizure Disorder",
    "Heart Condition", "Allergy (Severe/Anaphylaxis)", "Allergy (Other)",
    "Autoimmune Disorder", "Cancer", "Chronic Pain Condition",
    "Gastrointestinal Disorder", "Kidney Disease", "Vision Impairment",
    "Hearing Impairment", "Mobility Impairment", "Other"
]

# SCHOOL-PARTNERSHIP MAPPING (from government PDF)
SCHOOL_PARTNERSHIP_MAP = {
    # Adelaide Prospect Partnership
    "Angle Vale School": "Adelaide Prospect",
    "Gawler and District College": "Adelaide Prospect",
    "Gawler East Primary School": "Adelaide Prospect",
    "Gawler Primary School": "Adelaide Prospect",
    "Hewett Primary School": "Adelaide Prospect",
    "Kingsford School": "Adelaide Prospect",
    "Nailsworth Primary School": "Adelaide Prospect",
    "Prospect North Primary School": "Adelaide Prospect",
    "Prospect Primary School": "Adelaide Prospect",
    "Walkerville Primary School": "Adelaide Prospect",
    
    # Greenhill South Partnership
    "Aberfoyle Hub School": "Greenhill South",
    "Bellevue Heights Primary School": "Greenhill South",
    "Blackwood High School": "Greenhill South",
    "Coromandel Valley Primary School": "Greenhill South",
    "Eden Hills Primary School": "Greenhill South",
    "Hawthorndene Primary School": "Greenhill South",
    "Highgate School": "Greenhill South",
    "Mitcham Primary School": "Greenhill South",
    "Springbank Secondary College": "Greenhill South",
    "Unley High School": "Greenhill South",
    
    # Heysen Partnership
    "Aberfoyle Park High School": "Heysen",
    "Kangarilla Primary School": "Heysen",
    "Mount Barker High School": "Heysen",
    "Mount Barker Primary School": "Heysen",
    "Mount Barker Primary": "Heysen",
    "Mount Barker Waldorf School": "Heysen",
    "Nairne Primary School": "Heysen",
    
    # Holdfast Partnership
    "Brighton Primary School": "Holdfast",
    "Brighton PS": "Holdfast",
    "Brighton Secondary School": "Holdfast",
    "Hallett Cove School": "Holdfast",
    "Hamilton Secondary College": "Holdfast",
    "Paringa Park Primary School": "Holdfast",
    "Pasadena High School": "Holdfast",
    "Seaview High School": "Holdfast",
    "Warradale Primary School": "Holdfast",
    
    # Inner West Partnership
    "Challa Gardens Primary School": "Inner West",
    "Cowandilla Primary School": "Inner West",
    "Findon High School": "Inner West",
    "Henley High School": "Inner West",
    "Kidman Park Primary School": "Inner West",
    "Lockleys Primary School": "Inner West",
    "Plympton Primary School": "Inner West",
    "Richmond Primary School": "Inner West",
    "West Beach Primary School": "Inner West",
    
    # Le Fevre Peninsula Partnership
    "Alberton Primary School": "Le Fevre Peninsula",
    "Ethelton Primary School": "Le Fevre Peninsula",
    "Le Fevre High School": "Le Fevre Peninsula",
    "Largs Bay School": "Le Fevre Peninsula",
    "Ocean View P-12 College": "Le Fevre Peninsula",
    "Peninsula School": "Le Fevre Peninsula",
    "Taperoo Primary School": "Le Fevre Peninsula",
    
    # Marion Coastal Partnership
    "Darlington Primary School": "Marion Coastal",
    "Marino Cove School": "Marion Coastal",
    "Marion Primary School": "Marion Coastal",
    "Mitchell Park School": "Marion Coastal",
    "Seacliff Primary School": "Marion Coastal",
    "Southern Vocational College": "Marion Coastal",
    
    # Marion Inland Partnership
    "Ascot Park Primary School": "Marion Inland",
    "Clovelly Park Primary School": "Marion Inland",
    "Clovelly Park PS": "Marion Inland",  # Alternative name
    "Glandore Community Centre": "Marion Inland",
    "Glandore Primary School": "Marion Inland",
    "Marion High School": "Marion Inland",
    "Parkside Primary School": "Marion Inland",
    "Warradale North Primary School": "Marion Inland",
    
    # Mitcham Hills Partnership
    "Aberfoyle Park Primary School": "Mitcham Hills",
    "Belair Primary School": "Mitcham Hills",
    "Bellevue Heights Primary School": "Mitcham Hills",
    "Blackwood Primary School": "Mitcham Hills",
    "Brownhill Creek Primary School": "Mitcham Hills",
    "Craigburn Primary School": "Mitcham Hills",
    "Cumberland Park Primary School": "Mitcham Hills",
    "Sturt Street Community School": "Mitcham Hills",
    
    # Onkaparinga Partnership
    "Christies Beach High School": "Onkaparinga",
    "Hackham East Primary School": "Onkaparinga",
    "Hackham West Primary School": "Onkaparinga",
    "Noarlunga Centre Primary School": "Onkaparinga",
    "Noarlunga Downs Primary School": "Onkaparinga",
    "Reynella East College": "Onkaparinga",
    "Reynella Primary School": "Onkaparinga",
    "Reynella South Primary School": "Onkaparinga",
    "Southern Vales Christian College": "Onkaparinga",
    "Willunga High School": "Onkaparinga",
    
    # Orion Partnership
    "Evanston Gardens Primary School": "Orion",
    "Evanston Primary School": "Orion",
    "Evanston South Primary School": "Orion",
    "Hillcrest Primary School": "Orion",
    "Mark Oliphant College": "Orion",
    "Paralowie R-12": "Orion",
    "Paralowie School": "Orion",
    "Playford International College": "Orion",
    
    # West Torrens Partnership
    "Cowandilla Primary School": "West Torrens",
    "Fulham Gardens Primary School": "West Torrens",
    "Fulham North Primary School": "West Torrens",
    "Henley Beach Primary School": "West Torrens",
    "Hilton Primary School": "West Torrens",
    "Underdale High School": "West Torrens",
    
    # Western Adelaide Shores Partnership
    "Hendon Primary School": "Western Adelaide Shores",
    "Hendon School": "Western Adelaide Shores",
    "Ottoway Primary School": "Western Adelaide Shores",
    "Peterhead Primary School": "Western Adelaide Shores",
    "Rosewater Primary School": "Western Adelaide Shores",
    "St Clair Primary School": "Western Adelaide Shores",
    "West Lakes Shore School": "Western Adelaide Shores",
    "West Lakes Shores": "Western Adelaide Shores",
    "Woodville High School": "Western Adelaide Shores",
    "Woodville HS": "Western Adelaide Shores",
    "Woodville Gardens School": "Western Adelaide Shores",
    
    # Other schools (partnership TBD)
    "Warriappendia Secondary School": "Other"  # Partnership to be confirmed
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

def calculate_weeks_between(start_date, end_date):
    """Calculate number of weeks between two dates"""
    if start_date and end_date:
        delta = end_date - start_date
        weeks = delta.days / 7
        return round(weeks, 1)
    return 0

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
        "Total_Previous_Placements", "Placement_History_Notes", "Priority_Level",
        "Case_Worker"
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
        
        # Determine Allocation_Status based on outcome and waitlist_status
        waitlist_status = allocation.get('waitlist_status', 'Not Applicable')
        outcome = allocation.get('outcome', '')
        
        if waitlist_status == 'Site Decision':
            allocation_status = 'SITE DECISION'  # Uppercase to stand out
        elif outcome == 'Allocated':
            allocation_status = 'Allocated'
        else:
            allocation_status = 'Waitlist'
        
        row_data = [
            student_id,                                          # 1. Student_ID
            allocation.get('student_name', '').upper(),         # 2. Student_Name
            dob,                                                 # 3. DOB
            allocation.get('gender', ''),                        # 4. Gender
            allocation.get('year_level', ''),                    # 5. Year_Level
            allocation.get('school', ''),                        # 6. Referring_School
            today,                                               # 7. Referral_Date
            allocation_status,                                   # 8. Allocation_Status
            mapped_program,                                      # 9. Allocated_Program
            start_date,                                          # 10. Placement_Start
            end_date,                                            # 11. Placement_End
            allocation.get('partnership_area', ''),              # 12. Partnership_Area
            allocation.get('previous_clc_placement', 'No'),      # 13. Previous_CLC_Placement
            allocation.get('previous_other_lc', 'No'),           # 14. Previous_Other_LC
            allocation.get('other_lc_name', ''),                 # 15. Other_LC_Name
            allocation.get('total_previous_placements', 0),      # 16. Total_Previous_Placements
            allocation.get('placement_history_notes', ''),       # 17. Placement_History_Notes
            allocation.get('priority_level', '3'),               # 18. Priority_Level
            allocation.get('case_worker', ''),                   # 19. Case_Worker
        ] + flag_values + [  # 20-52. All comprehensive flags (33 flags)
            allocation.get('bespoke_placement', 'No'),           # 53. Bespoke_Placement
            waitlist_status,                                     # 54. Waitlist_Status
            waitlist_date,                                       # 55. Waitlist_Date
            allocation.get('allocated_from_waitlist', 'No'),     # 56. Allocated_From_Waitlist
            'Active',                                            # 57. Current_Status
            '',                                                  # 58. Exit_Reason
            '',                                                  # 59. Transition_Plan
            allocation.get('queries', '')                        # 60. Notes
        ]
        
        # Write row
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row_num, col, value)
            cell.alignment = Alignment(horizontal="left", vertical="center")
            
            # RED HIGHLIGHT for Site Decision rows
            if waitlist_status == 'Site Decision':
                cell.fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                cell.font = Font(color="FFFFFF", bold=True)
    
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
    
    # Communication with Sites Quick Action
    st.markdown("---")
    st.markdown("**📧 Communication with Sites**")
    
    # Show current week communication count
    try:
        comm_count = supabase.table("allocation_students")\
            .select("id", count="exact")\
            .eq("meeting_week", selected_week)\
            .in_("outcome", ["Allocated", "Not Allocated", "Approved", "Not Approved"])\
            .not_.is_("information", "null")\
            .execute()
        
        count = comm_count.count if comm_count.count else 0
        st.metric("This Week", f"{count} comms")
    except:
        st.metric("This Week", "—")
    
    if st.button("📋 View Communications", use_container_width=True):
        st.session_state.show_comms = True
    
    if st.button("📥 Download Week Summary", use_container_width=True, type="primary"):
        st.session_state.download_comms = True

# Main content area
meeting_week_label = f"{selected_week}"

# Tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 New Allocations", 
    "🔄 Extensions", 
    "⏸️ Not Placed",
    "📊 View & Export",
    "⏳ Waitlist / Site Decision"
])

# TAB 1: New Student Allocations - SIMPLIFIED TWO-STAGE
with tab1:
    st.header("New Student Allocations")
    
    # ============================================================================
    # WAITLIST AUTO-POPULATION
    # ============================================================================
    
    # Check for waitlist students that haven't been imported for this week yet
    try:
        # Get waitlist students
        waitlist_students = supabase.table("allocation_students")\
            .select("*")\
            .in_("waitlist_status", ["On Waitlist", "Site Decision"])\
            .not_.is_("outcome", "null")\
            .execute()
        
        # Check if any have already been imported for this week
        if waitlist_students.data and len(waitlist_students.data) > 0:
            # Get existing drafts for this week
            existing_drafts = supabase.table("allocation_students")\
                .select("student_name, school")\
                .eq("meeting_week", meeting_week_label)\
                .eq("term", st.session_state.current_term)\
                .eq("year", st.session_state.current_year)\
                .is_("outcome", "null")\
                .execute()
            
            # Create a set of existing draft student+school combinations
            existing_combinations = set()
            if existing_drafts.data:
                for draft in existing_drafts.data:
                    existing_combinations.add(f"{draft.get('student_name')}_{draft.get('school')}")
            
            # Filter waitlist students that haven't been imported yet
            students_to_import = []
            for student in waitlist_students.data:
                combination = f"{student.get('student_name')}_{student.get('school')}"
                if combination not in existing_combinations:
                    students_to_import.append(student)
            
            if students_to_import:
                # Show import banner
                st.info(f"📋 **{len(students_to_import)} student(s) from waitlist/site decision** are ready to import for {meeting_week_label}")
                
                with st.expander("👁️ View Waitlist Students Ready to Import", expanded=False):
                    for student in students_to_import:
                        status_icon = "🔴" if student.get('waitlist_status') == 'Site Decision' else "📋"
                        st.write(f"{status_icon} **{student.get('student_name')}** - {student.get('school')} ({student.get('waitlist_status')})")
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("📥 Import Waitlist Students", type="primary", use_container_width=True):
                        imported_count = 0
                        
                        with st.spinner("Importing waitlist students..."):
                            for student in students_to_import:
                                try:
                                    # Create draft from waitlist student
                                    draft_data = {
                                        "meeting_week": meeting_week_label,
                                        "meeting_date": meeting_date.isoformat(),
                                        "term": st.session_state.current_term,
                                        "year": st.session_state.current_year,
                                        "student_name": student.get('student_name'),
                                        "school": student.get('school'),
                                        "date_of_birth": student.get('date_of_birth'),
                                        "gender": student.get('gender'),
                                        "year_level": student.get('year_level'),
                                        "partnership_area": student.get('partnership_area'),
                                        "priority_level": student.get('priority_level', '3'),
                                        "previous_clc_placement": student.get('previous_clc_placement', 'No'),
                                        "previous_other_lc": student.get('previous_other_lc', 'No'),
                                        "previously_referred": student.get('previously_referred', 'No'),
                                        "other_lc_name": student.get('other_lc_name'),
                                        "total_previous_placements": student.get('total_previous_placements', 0),
                                        "placement_history_notes": student.get('placement_history_notes'),
                                        "medical_condition_details": student.get('medical_condition_details'),
                                        "medication_details": student.get('medication_details'),
                                        "cat_funding": student.get('cat_funding'),
                                        "partnership": student.get('partnership'),
                                        "queries": f"⏳ FROM WAITLIST - Original status: {student.get('waitlist_status')} (Week {student.get('meeting_week')})",
                                        "allocated_from_waitlist": "Yes",  # Flag to track this came from waitlist
                                        "original_waitlist_record_id": student.get('id'),  # Link to original record
                                        "outcome": None  # Draft status
                                    }
                                    
                                    supabase.table("allocation_students").insert(draft_data).execute()
                                    imported_count += 1
                                    
                                except Exception as e:
                                    st.error(f"Error importing {student.get('student_name')}: {e}")
                        
                        if imported_count > 0:
                            st.success(f"✅ Successfully imported {imported_count} student(s) from waitlist!")
                            st.balloons()
                            st.info("💡 Go to Stage 2 to complete these allocations. They're flagged as 'FROM WAITLIST' in the queries field.")
                            st.rerun()
                        else:
                            st.warning("No students were imported. Check errors above.")
                
                st.markdown("---")
    
    except Exception as e:
        st.error(f"Error checking waitlist: {e}")
    
    # ============================================================================
    # MAIN ALLOCATION WORKFLOW
    # ============================================================================
    
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
            # Fetch ALL records for this week
            all_records = supabase.table("allocation_students")\
                .select("*")\
                .eq("meeting_week", meeting_week_label)\
                .eq("term", st.session_state.current_term)\
                .eq("year", st.session_state.current_year)\
                .execute()
            
            # Filter for drafts - outcome is NULL/None and no extension dates
            drafts_list = []
            if all_records.data:
                for record in all_records.data:
                    outcome = record.get('outcome')
                    # Draft if outcome is None AND no extension fields
                    is_draft = (outcome is None and not record.get('exclusion_finish_date'))
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
                
                # Check if from waitlist
                if draft.get('allocated_from_waitlist') == 'Yes':
                    st.success(f"✅ Loaded draft for: **{draft['student_name']}** ⏳ FROM WAITLIST")
                    st.info(f"📋 This student was previously on waitlist. Original week: {draft.get('queries', '').split('Week ')[-1].rstrip(')') if 'Week' in draft.get('queries', '') else 'Unknown'}")
                else:
                    st.success(f"✅ Loaded draft for: **{draft['student_name']}**")
                
                # Show draft details
                with st.expander("📋 View Draft Details", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**School:** {draft.get('school', 'N/A')}")
                        st.write(f"**Year Level:** {draft.get('year_level', 'N/A')}")
                    with col2:
                        st.write(f"**Gender:** {draft.get('gender', 'N/A')}")
                        st.write(f"**Priority:** {draft.get('priority_level', 'N/A')}")
                    with col3:
                        st.write(f"**Partnership:** {draft.get('partnership_area', 'N/A')}")
                        if draft.get('case_worker'):
                            st.write(f"**Case Worker:** {draft.get('case_worker')}")
                        if draft.get('queries'):
                            st.write(f"**Queries:** {draft.get('queries')}")
                
                # COMPLETION FORM
                st.markdown("---")
                st.subheader("✏️ Complete Allocation Decision")
                
                with st.form("complete_allocation_form"):
                    # Allocation decision
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        program = st.selectbox("Program *", PROGRAMS)
                    
                    with col2:
                        outcome = st.selectbox("Outcome *", OUTCOMES)
                    
                    with col3:
                        school_contact = st.text_input("School Contact Person")
                    
                    # Case Worker and Dates
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        case_worker = st.text_input("Case Worker Name", help="Name of the case worker assigned to this student")
                    with col2:
                        start_after = st.date_input("Start After", value=None)
                    with col3:
                        finishing_date = st.date_input("Finishing Date", value=None)
                    
                    # Bespoke and Waitlist
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        bespoke = st.selectbox("Bespoke Placement?", ["No", "Yes"])
                    with col2:
                        waitlist_status = st.selectbox("Waitlist Status", WAITLIST_STATUS_OPTIONS)
                    with col3:
                        if waitlist_status == "On Waitlist":
                            waitlist_date = st.date_input("Waitlist Date", value=datetime.now().date())
                        else:
                            waitlist_date = None
                    
                    # Communication
                    st.markdown("### 📧 Communication to School")
                    information = st.text_area(
                        "Information to be shared with school",
                        help="This will be included in the communication summary"
                    )
                    
                    actioned_by = st.selectbox("To be actioned by", [""] + STAFF_NAMES)
                    
                    # Submit
                    submitted = st.form_submit_button("✅ Complete & Save Allocation", type="primary", use_container_width=True)
                    
                    if submitted:
                        # Validation
                        if not outcome:
                            st.error("⚠️ Please select an outcome")
                        else:
                            try:
                                update_data = {
                                    "program": program,
                                    "outcome": outcome,
                                    "school_contact": school_contact,
                                    "case_worker": case_worker if case_worker else None,
                                    "start_after": start_after.isoformat() if start_after else None,
                                    "finishing_date": finishing_date.isoformat() if finishing_date else None,
                                    "bespoke_placement": bespoke,
                                    "waitlist_status": waitlist_status,
                                    "waitlist_date": waitlist_date.isoformat() if waitlist_date else None,
                                    "information": information if information else None,
                                    "actioned_by": actioned_by if actioned_by else None
                                }
                                
                                result = supabase.table("allocation_students")\
                                    .update(update_data)\
                                    .eq("id", draft['id'])\
                                    .execute()
                                
                                st.success(f"✅ Allocation completed for {draft['student_name']}!")
                                st.balloons()
                                st.info("💡 Go to Tab 4 to view and export this allocation.")
                                
                            except Exception as e:
                                st.error(f"❌ Error updating allocation: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
        
        except Exception as e:
            st.error(f"❌ Error loading drafts: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    else:
        # STAGE 1: Create New Draft
        st.subheader("➕ Create New Allocation Draft")
        st.caption("Fill in student details before the meeting. Complete on meeting day.")
        
        with st.form("new_allocation_draft"):
            # SECTION 1: Basic Information
            st.markdown("### 1️⃣ Student Details")
            
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
                medical_condition_details = ""  # Initialize
                medication_details = ""  # Initialize
                
                for flag in MEDICAL_FLAGS:
                    if st.checkbox(flag, key=f"flag_{flag}"):
                        selected_flags.append(flag)
                
                # Medical condition dropdown - REQUIRED if Medical condition is checked
                if "Medical condition" in selected_flags:
                    medical_condition_details = st.selectbox(
                        "Medical Condition Type *",
                        [""] + MEDICAL_CONDITION_TYPES,
                        help="Required - select the type of medical condition"
                    )
                
                # Medication details text box - OPTIONAL if Medication is checked
                if "Medication" in selected_flags:
                    medication_details = st.text_input(
                        "Medication Details (Optional)",
                        placeholder="e.g., Ritalin 10mg twice daily",
                        help="Optional - enter medication names and dosages if known"
                    )
            
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
                if "Medical condition" in selected_flags and not medical_condition_details:
                    missing.append("Medical Condition Type")
                
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
                            "priority_level": priority_level if priority_level else "3",
                            "previous_clc_placement": previous_clc,
                            "previous_other_lc": previous_other_lc,
                            "previously_referred": previously_referred,
                            "other_lc_name": other_lc_name if previous_other_lc == "Yes" else None,
                            "total_previous_placements": total_placements,
                            "placement_history_notes": placement_history_notes,
                            "medical_condition_details": medical_condition_details if "Medical condition" in selected_flags else None,
                            "medication_details": medication_details if "Medication" in selected_flags else None,
                            "cat_funding": json.dumps(selected_flags),
                            "partnership": json.dumps([]),
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

# TAB 2: Extensions - TWO-STAGE WORKFLOW
with tab2:
    st.header("🔄 Extensions")
    
    # STAGE SELECTOR
    extension_stage = st.radio(
        "Select what you want to do:",
        ["➕ Request New Extension (Stage 1)", "📝 Complete Extension Request (Stage 2)"],
        horizontal=True,
        key="extension_stage_selector"
    )
    
    st.markdown("---")
    
    if extension_stage == "📝 Complete Extension Request (Stage 2)":
        # STAGE 2: Complete existing extension request
        st.subheader("📂 Select Extension Request to Complete")
        
        try:
            # Fetch extension drafts - records with exclusion_finish_date but outcome is NULL
            extension_records = supabase.table("allocation_students")\
                .select("*")\
                .eq("meeting_week", meeting_week_label)\
                .eq("term", st.session_state.current_term)\
                .eq("year", st.session_state.current_year)\
                .not_.is_("exclusion_finish_date", "null")\
                .execute()
            
            # Filter for drafts (outcome is None)
            extension_drafts = []
            if extension_records.data:
                for record in extension_records.data:
                    if record.get('outcome') is None:
                        extension_drafts.append(record)
            
            if not extension_drafts:
                st.info("✅ No extension requests found. Create one in Stage 1.")
            else:
                extension_options = {f"{d['student_name']} - {d.get('program', 'N/A')} ({d.get('school', 'N/A')})": d for d in extension_drafts}
                
                selected_extension_display = st.selectbox(
                    f"Select one of {len(extension_drafts)} extension request(s):",
                    list(extension_options.keys())
                )
                
                extension_draft = extension_options[selected_extension_display]
                
                st.success(f"✅ Loaded extension request for: **{extension_draft['student_name']}**")
                
                # Show extension details (read-only)
                with st.expander("📋 View Extension Request Details", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Student:** {extension_draft.get('student_name')}")
                        st.write(f"**Program:** {extension_draft.get('program')}")
                        st.write(f"**School:** {extension_draft.get('school')}")
                    with col2:
                        st.write(f"**Exclusion Finish Date:** {extension_draft.get('exclusion_finish_date')}")
                        st.write(f"**Proposed Extension Date:** {extension_draft.get('proposed_extension_finish_date')}")
                        st.write(f"**Proposed Weeks:** {extension_draft.get('extension_weeks', 0)}")
                
                # COMPLETION FORM
                st.markdown("---")
                st.subheader("✏️ Complete Extension Decision")
                
                with st.form("complete_extension_form"):
                    # Extension decision
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        extension_outcome = st.radio(
                            "Extension Decision *",
                            EXTENSION_OUTCOMES,
                            horizontal=True
                        )
                    
                    with col2:
                        actioned_by = st.selectbox("To be actioned by", [""] + STAFF_NAMES)
                    
                    # Communication
                    st.markdown("### 📧 Communication to School")
                    information = st.text_area(
                        "Information to be shared with school",
                        help="This will be included in the communication summary",
                        key="extension_info"
                    )
                    
                    # Submit
                    submitted = st.form_submit_button("✅ Complete & Save Extension", type="primary", use_container_width=True)
                    
                    if submitted:
                        if not extension_outcome:
                            st.error("⚠️ Please select an outcome")
                        else:
                            try:
                                update_data = {
                                    "outcome": extension_outcome,
                                    "information": information if information else None,
                                    "actioned_by": actioned_by if actioned_by else None
                                }
                                
                                result = supabase.table("allocation_students")\
                                    .update(update_data)\
                                    .eq("id", extension_draft['id'])\
                                    .execute()
                                
                                st.success(f"✅ Extension {extension_outcome.lower()} for {extension_draft['student_name']}!")
                                st.balloons()
                                st.info("💡 Go to Tab 4 to view this extension or download communications.")
                                
                            except Exception as e:
                                st.error(f"❌ Error updating extension: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
        
        except Exception as e:
            st.error(f"❌ Error loading extension requests: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    else:
        # STAGE 1: Create New Extension Request
        st.subheader("➕ Request New Extension")
        st.caption("Fill in extension details before the meeting. Complete decision on meeting day.")
        
        with st.form("new_extension_request"):
            # Extension Request Details
            st.markdown("### 📝 Extension Request Details")
            
            col1, col2 = st.columns(2)
            with col1:
                student_name = st.text_input("Student Name *", key="ext_student_name")
                program = st.selectbox("Program *", [""] + PROGRAMS, key="ext_program")
                school = st.selectbox("School * (searchable)", [""] + ALL_SCHOOLS, key="ext_school")
            
            with col2:
                exclusion_finish_date = st.date_input(
                    "Current Exclusion Finish Date *",
                    value=None,
                    key="ext_exclusion_date"
                )
                proposed_extension_finish_date = st.date_input(
                    "Proposed Extension Finish Date *",
                    value=None,
                    key="ext_proposed_date"
                )
                
                # Calculate weeks
                if exclusion_finish_date and proposed_extension_finish_date:
                    extension_weeks = calculate_weeks_between(exclusion_finish_date, proposed_extension_finish_date)
                    st.metric("Proposed Extension (weeks)", f"{extension_weeks}")
                else:
                    extension_weeks = 0
                    st.metric("Proposed Extension (weeks)", "—")
            
            # Submit
            st.markdown("---")
            submitted = st.form_submit_button("💾 Save Extension Request (Complete Later)", type="primary", use_container_width=True)
            
            if submitted:
                # Validation
                missing = []
                if not student_name:
                    missing.append("Student Name")
                if not program:
                    missing.append("Program")
                if not school:
                    missing.append("School")
                if not exclusion_finish_date:
                    missing.append("Exclusion Finish Date")
                if not proposed_extension_finish_date:
                    missing.append("Proposed Extension Finish Date")
                
                if missing:
                    st.error(f"⚠️ Please fill in required fields: {', '.join(missing)}")
                elif proposed_extension_finish_date <= exclusion_finish_date:
                    st.error("⚠️ Proposed extension date must be after the current exclusion finish date")
                else:
                    try:
                        data = {
                            "meeting_week": meeting_week_label,
                            "meeting_date": meeting_date.isoformat(),
                            "term": st.session_state.current_term,
                            "year": st.session_state.current_year,
                            "student_name": student_name,
                            "program": program,
                            "school": school,
                            "exclusion_finish_date": exclusion_finish_date.isoformat(),
                            "proposed_extension_finish_date": proposed_extension_finish_date.isoformat(),
                            "extension_weeks": extension_weeks,
                            "outcome": None  # Draft status
                        }
                        
                        result = supabase.table("allocation_students").insert(data).execute()
                        st.success(f"✅ Extension request saved for {student_name}! Complete on meeting day.")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error saving extension request: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

# TAB 3: Not Placed - AUTO-COMPILED
with tab3:
    st.header("⏸️ Not Placed Students")
    st.caption("Automatically compiled from allocation outcomes")
    
    try:
        # Fetch students marked as "Not Allocated"
        not_allocated = supabase.table("allocation_students")\
            .select("student_name, year_level, school, program")\
            .eq("meeting_week", meeting_week_label)\
            .eq("outcome", "Not Allocated")\
            .execute()
        
        if not_allocated.data and len(not_allocated.data) > 0:
            st.info(f"📊 **{len(not_allocated.data)} student(s)** not allocated this week")
            
            # Display as table
            display_data = []
            for record in not_allocated.data:
                display_data.append({
                    "Student Name": record.get("student_name", ""),
                    "Year Level": record.get("year_level", ""),
                    "School": record.get("school", ""),
                    "Proposed Program": record.get("program", "")
                })
            
            df_not_allocated = pd.DataFrame(display_data)
            st.dataframe(df_not_allocated, use_container_width=True, hide_index=True)
            
            # Export option
            st.markdown("---")
            if st.button("📥 Download Not Allocated List", type="primary"):
                # Create Excel
                from openpyxl import Workbook
                from io import BytesIO
                
                wb = Workbook()
                ws = wb.active
                ws.title = "Not Allocated"
                
                # Headers
                headers = ["Student Name", "Year Level", "School", "Proposed Program"]
                header_fill = PatternFill(start_color="DC3545", end_color="DC3545", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for col_idx, header in enumerate(headers, 1):
                    cell = ws.cell(1, col_idx, header)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Add data
                for row_idx, record in enumerate(not_allocated.data, 2):
                    ws.cell(row_idx, 1, record.get('student_name', ''))
                    ws.cell(row_idx, 2, record.get('year_level', ''))
                    ws.cell(row_idx, 3, record.get('school', ''))
                    ws.cell(row_idx, 4, record.get('program', ''))
                
                # Adjust widths
                ws.column_dimensions['A'].width = 25
                ws.column_dimensions['B'].width = 12
                ws.column_dimensions['C'].width = 30
                ws.column_dimensions['D'].width = 20
                
                # Save to bytes
                output = BytesIO()
                wb.save(output)
                excel_data = output.getvalue()
                
                st.download_button(
                    label="💾 Save Not Allocated List",
                    data=excel_data,
                    file_name=f"Not_Allocated_{selected_week.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.success("✅ No students marked as 'Not Allocated' for this week")
    
    except Exception as e:
        st.error(f"❌ Error loading not allocated students: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# TAB 4: View & Export
with tab4:
    st.header("📊 View & Export Completed Allocations")
    
    try:
        # Get ALL records with outcomes (both allocations and extensions)
        full_data = supabase.table("allocation_students")\
            .select("*")\
            .eq("meeting_week", meeting_week_label)\
            .not_.is_("outcome", "null")\
            .execute()
        
        if full_data.data and len(full_data.data) > 0:
            # DEBUG: Show all outcomes
            with st.expander("🔍 Debug: View All Outcomes", expanded=False):
                st.write(f"**Total records fetched:** {len(full_data.data)}")
                for idx, record in enumerate(full_data.data, 1):
                    st.write(f"{idx}. {record.get('student_name', 'N/A')} - Outcome: '{record.get('outcome')}'")
            
            # Separate allocations, not allocated, and extensions
            allocated = [r for r in full_data.data if r.get('outcome') == 'Allocated']
            not_allocated = [r for r in full_data.data if r.get('outcome') == 'Not Allocated']
            extensions = [r for r in full_data.data if r.get('outcome') in ['Approved', 'Not Approved']]
            
            # DEBUG: Show counts
            st.write(f"**Debug counts:** Allocated={len(allocated)}, Not Allocated={len(not_allocated)}, Extensions={len(extensions)}")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(full_data.data))
            with col2:
                st.metric("Allocated", len(allocated))
            with col3:
                st.metric("Not Allocated", len(not_allocated))
            with col4:
                st.metric("Extensions", len(extensions))
            
            st.markdown("---")
            
            # Display allocated students
            if allocated:
                st.subheader(f"✅ Allocated Students ({len(allocated)})")
                display_data = []
                for record in allocated:
                    display_data.append({
                        "Student": record.get("student_name", ""),
                        "Year": record.get("year_level", ""),
                        "Program": record.get("program", ""),
                        "Case Worker": record.get("case_worker", ""),
                        "School": record.get("school", "")
                    })
                st.dataframe(display_data, use_container_width=True)
            
            # Display not allocated students
            st.markdown("---")
            st.subheader(f"⏸️ Not Allocated Students ({len(not_allocated)})")
            if not_allocated:
                display_data = []
                for record in not_allocated:
                    display_data.append({
                        "Student": record.get("student_name", ""),
                        "Year": record.get("year_level", ""),
                        "Program": record.get("program", ""),
                        "Case Worker": record.get("case_worker", ""),
                        "School": record.get("school", "")
                    })
                st.dataframe(display_data, use_container_width=True)
            else:
                st.info("✅ No students marked as 'Not Allocated' for this week")
            
            # Display extensions
            if extensions:
                st.markdown("---")
                st.subheader(f"🔄 Extensions ({len(extensions)})")
                display_data = []
                for record in extensions:
                    display_data.append({
                        "Student": record.get("student_name", ""),
                        "Program": record.get("program", ""),
                        "School": record.get("school", ""),
                        "Exclusion End": record.get("exclusion_finish_date", ""),
                        "Proposed End": record.get("proposed_extension_finish_date", ""),
                        "Weeks": record.get("extension_weeks", ""),
                        "Outcome": record.get("outcome", "")
                    })
                st.dataframe(display_data, use_container_width=True)
            
            # Export section
            st.markdown("---")
            st.subheader("📤 Export to Excel")
            
            if st.button("📥 Download Data Entry Excel", type="primary"):
                try:
                    # Combine allocated and not allocated for export
                    all_allocations = allocated + not_allocated
                    
                    if all_allocations:
                        excel_bytes = export_to_data_entry(all_allocations)
                        
                        st.download_button(
                            label="💾 Save Data Entry Excel",
                            data=excel_bytes,
                            file_name=f"CLC_Allocations_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success(f"✅ Excel file ready! {len(all_allocations)} allocation(s) exported ({len(allocated)} allocated, {len(not_allocated)} not allocated).")
                    else:
                        st.warning("⚠️ No allocations to export")
                    
                except Exception as e:
                    st.error(f"❌ Error generating Excel: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.info("📭 No completed records found. Create allocations or extensions in Tabs 1-2!")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# TAB 5: Waitlist / Site Decision Management
with tab5:
    st.header("⏳ Waitlist / Site Decision Management")
    st.caption("Students awaiting next allocation meeting or school decision")
    
    try:
        # Fetch students on waitlist or site decision (across ALL weeks)
        waitlist_data = supabase.table("allocation_students")\
            .select("*")\
            .in_("waitlist_status", ["On Waitlist", "Site Decision"])\
            .not_.is_("outcome", "null")\
            .order("waitlist_date", desc=True)\
            .execute()
        
        if waitlist_data.data and len(waitlist_data.data) > 0:
            # Separate by status
            on_waitlist = [r for r in waitlist_data.data if r.get('waitlist_status') == 'On Waitlist']
            site_decision = [r for r in waitlist_data.data if r.get('waitlist_status') == 'Site Decision']
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Waiting", len(waitlist_data.data))
            with col2:
                st.metric("On Waitlist", len(on_waitlist))
            with col3:
                st.metric("Site Decision", len(site_decision))
            
            st.markdown("---")
            
            # SITE DECISION SECTION (Priority - needs immediate action)
            if site_decision:
                st.subheader(f"🔴 Site Decision ({len(site_decision)}) - ACTION REQUIRED")
                st.warning("⚠️ These students are waiting for school decision. Cannot remain in this status long!")
                
                display_data = []
                for record in site_decision:
                    display_data.append({
                        "Student": record.get("student_name", ""),
                        "Year": record.get("year_level", ""),
                        "School": record.get("school", ""),
                        "Program": record.get("program", ""),
                        "Case Worker": record.get("case_worker", ""),
                        "Meeting Week": record.get("meeting_week", ""),
                        "Waitlist Date": record.get("waitlist_date", ""),
                        "ID": record.get("id", "")
                    })
                
                df_site_decision = pd.DataFrame(display_data)
                st.dataframe(df_site_decision.drop(columns=['ID']), use_container_width=True, hide_index=True)
                
                # Update Site Decision status
                st.markdown("#### ✏️ Update Site Decision")
                st.caption("Move to waitlist when school confirms, or withdraw if school declines")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    student_to_update = st.selectbox(
                        "Select student",
                        [""] + [f"{r['student_name']} - {r['school']}" for r in site_decision],
                        key="update_site_decision"
                    )
                
                with col2:
                    if st.button("📋 Move to Waitlist", type="primary", disabled=not student_to_update, use_container_width=True):
                        if student_to_update:
                            # Find the record
                            selected_record = next((r for r in site_decision if f"{r['student_name']} - {r['school']}" == student_to_update), None)
                            if selected_record:
                                try:
                                    supabase.table("allocation_students")\
                                        .update({"waitlist_status": "On Waitlist"})\
                                        .eq("id", selected_record['id'])\
                                        .execute()
                                    st.success(f"✅ Moved {selected_record['student_name']} to Waitlist")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                
                with col3:
                    if st.button("🚫 Site Withdraw", type="secondary", disabled=not student_to_update, use_container_width=True):
                        if student_to_update:
                            # Find the record
                            selected_record = next((r for r in site_decision if f"{r['student_name']} - {r['school']}" == student_to_update), None)
                            if selected_record:
                                try:
                                    supabase.table("allocation_students")\
                                        .update({"waitlist_status": "Site Withdraw"})\
                                        .eq("id", selected_record['id'])\
                                        .execute()
                                    st.success(f"✅ Marked {selected_record['student_name']} as Site Withdraw")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
            
            # ON WAITLIST SECTION
            if on_waitlist:
                st.markdown("---")
                st.subheader(f"📋 On Waitlist ({len(on_waitlist)})")
                st.info("💡 These students will auto-populate when you create allocations for future weeks")
                
                display_data = []
                for record in on_waitlist:
                    display_data.append({
                        "Student": record.get("student_name", ""),
                        "Year": record.get("year_level", ""),
                        "School": record.get("school", ""),
                        "Program": record.get("program", ""),
                        "Case Worker": record.get("case_worker", ""),
                        "Meeting Week": record.get("meeting_week", ""),
                        "Waitlist Date": record.get("waitlist_date", ""),
                        "ID": record.get("id", "")
                    })
                
                df_waitlist = pd.DataFrame(display_data)
                st.dataframe(df_waitlist.drop(columns=['ID']), use_container_width=True, hide_index=True)
                
                # Delete option for waitlist
                st.markdown("#### ❌ Remove from Waitlist")
                st.caption("Use if school has withdrawn the referral")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    student_to_remove_wl = st.selectbox(
                        "Select student to remove",
                        [""] + [f"{r['student_name']} - {r['school']}" for r in on_waitlist],
                        key="remove_waitlist"
                    )
                
                with col2:
                    if st.button("🗑️ Remove", type="secondary", disabled=not student_to_remove_wl, key="remove_wl_btn"):
                        if student_to_remove_wl:
                            # Find the record
                            selected_record = next((r for r in on_waitlist if f"{r['student_name']} - {r['school']}" == student_to_remove_wl), None)
                            if selected_record:
                                # Update to remove from waitlist but keep in database
                                try:
                                    supabase.table("allocation_students")\
                                        .update({"waitlist_status": "Declined"})\
                                        .eq("id", selected_record['id'])\
                                        .execute()
                                    st.success(f"✅ Removed {selected_record['student_name']} from Waitlist")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
            
            # Export waitlist/site decision
            st.markdown("---")
            st.subheader("📥 Export Waitlist/Site Decision Data")
            st.caption("Includes all waitlist history: active, withdrawn, and declined")
            
            if st.button("📥 Download Complete Waitlist Data", type="primary"):
                try:
                    # Fetch ALL waitlist-related records (including withdrawn and declined)
                    all_waitlist_data = supabase.table("allocation_students")\
                        .select("*")\
                        .in_("waitlist_status", ["On Waitlist", "Site Decision", "Site Withdraw", "Declined"])\
                        .not_.is_("outcome", "null")\
                        .order("waitlist_date", desc=True)\
                        .execute()
                    
                    if all_waitlist_data.data:
                        from openpyxl import Workbook
                        from io import BytesIO
                        
                        wb = Workbook()
                        ws = wb.active
                        ws.title = "Waitlist Summary"
                        
                        # Headers
                        headers = ["Student", "Year", "School", "Program", "Case Worker", "Status", "Meeting Week", "Waitlist Date"]
                        header_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
                        header_font = Font(bold=True, color="FFFFFF")
                        
                        for col_idx, header in enumerate(headers, 1):
                            cell = ws.cell(1, col_idx, header)
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal='center', vertical='center')
                        
                        # Add data
                        row_idx = 2
                        for record in all_waitlist_data.data:
                            ws.cell(row_idx, 1, record.get('student_name', ''))
                            ws.cell(row_idx, 2, record.get('year_level', ''))
                            ws.cell(row_idx, 3, record.get('school', ''))
                            ws.cell(row_idx, 4, record.get('program', ''))
                            ws.cell(row_idx, 5, record.get('case_worker', ''))
                            ws.cell(row_idx, 6, record.get('waitlist_status', ''))
                            ws.cell(row_idx, 7, record.get('meeting_week', ''))
                            ws.cell(row_idx, 8, record.get('waitlist_date', ''))
                            
                            # Color coding
                            waitlist_status = record.get('waitlist_status', '')
                            
                            # RED for site decision (urgent)
                            if waitlist_status == 'Site Decision':
                                for col in range(1, 9):
                                    cell = ws.cell(row_idx, col)
                                    cell.fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                                    cell.font = Font(color="FFFFFF", bold=True)
                            
                            # ORANGE for site withdraw
                            elif waitlist_status == 'Site Withdraw':
                                for col in range(1, 9):
                                    cell = ws.cell(row_idx, col)
                                    cell.fill = PatternFill(start_color="FF6600", end_color="FF6600", fill_type="solid")
                                    cell.font = Font(color="FFFFFF")
                            
                            # GREY for declined
                            elif waitlist_status == 'Declined':
                                for col in range(1, 9):
                                    cell = ws.cell(row_idx, col)
                                    cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                                    cell.font = Font(color="666666")
                            
                            row_idx += 1
                        
                        # Adjust widths
                        ws.column_dimensions['A'].width = 25
                        ws.column_dimensions['B'].width = 10
                        ws.column_dimensions['C'].width = 30
                        ws.column_dimensions['D'].width = 20
                        ws.column_dimensions['E'].width = 20
                        ws.column_dimensions['F'].width = 15
                        ws.column_dimensions['G'].width = 15
                        ws.column_dimensions['H'].width = 15
                        
                        # Save to bytes
                        output = BytesIO()
                        wb.save(output)
                        excel_data = output.getvalue()
                        
                        st.download_button(
                            label="💾 Save Complete Waitlist Data",
                            data=excel_data,
                            file_name=f"Waitlist_Complete_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success(f"✅ Export ready! {len(all_waitlist_data.data)} total records (active + historical)")
                    else:
                        st.info("No waitlist data to export")
                        
                except Exception as e:
                    st.error(f"Error creating export: {e}")
        else:
            st.success("✅ No students currently on waitlist or awaiting site decision")
    
    except Exception as e:
        st.error(f"❌ Error loading waitlist: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# ============================================================================
# COMMUNICATION MODAL/SECTION (triggered from sidebar)
# ============================================================================

# Show communications view if button clicked
if st.session_state.get('show_comms', False):
    st.markdown("---")
    st.header("📧 Communication with Sites")
    
    try:
        # Fetch current week communications (both allocations and extensions)
        comm_data = supabase.table("allocation_students")\
            .select("student_name, school, program, school_contact, outcome, information, actioned_by")\
            .eq("meeting_week", selected_week)\
            .in_("outcome", ["Allocated", "Not Allocated", "Approved", "Not Approved"])\
            .execute()
        
        if comm_data.data:
            st.success(f"✅ {len(comm_data.data)} communication(s) for {selected_week}")
            
            # Display table
            display_data = []
            for record in comm_data.data:
                display_data.append({
                    "School": record.get("school", ""),
                    "Student": record.get("student_name", ""),
                    "Program": record.get("program", ""),
                    "School Contact": record.get("school_contact", ""),
                    "Type": "Extension" if record.get("outcome") in ["Approved", "Not Approved"] else "Allocation",
                    "Outcome": record.get("outcome", ""),
                    "Information to be Shared": record.get("information", ""),
                    "To be Actioned By": record.get("actioned_by", "")
                })
            
            df_comm = pd.DataFrame(display_data)
            st.dataframe(df_comm, use_container_width=True, hide_index=True)
            
            if st.button("✖️ Close"):
                st.session_state.show_comms = False
                st.rerun()
        else:
            st.info("📭 No communications for this week yet")
    except Exception as e:
        st.error(f"Error: {e}")

# Download communications if button clicked
if st.session_state.get('download_comms', False):
    try:
        # Fetch current week communications (both allocations and extensions)
        comm_data = supabase.table("allocation_students")\
            .select("student_name, school, program, school_contact, outcome, information, actioned_by, exclusion_finish_date, proposed_extension_finish_date, extension_weeks, waitlist_status")\
            .eq("meeting_week", selected_week)\
            .in_("outcome", ["Allocated", "Not Allocated", "Approved", "Not Approved"])\
            .execute()
        
        if comm_data.data:
            # Create Excel
            from openpyxl import Workbook
            from openpyxl.styles import PatternFill, Font, Alignment
            from io import BytesIO
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Communication Summary"
            
            # Headers
            headers = ["School", "Student", "Program", "School Contact", "Type", "Outcome", 
                      "Waitlist Status", "Extension Details", "Information to be Shared", "To be Actioned By"]
            
            # Style header
            header_fill = PatternFill(start_color="1A7A6E", end_color="1A7A6E", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(1, col_idx, header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Add data
            for row_idx, record in enumerate(comm_data.data, 2):
                # Determine type
                is_extension = record.get('outcome') in ['Approved', 'Not Approved']
                record_type = "Extension" if is_extension else "Allocation"
                
                # Extension details
                ext_details = ""
                if is_extension:
                    ext_details = f"Current end: {record.get('exclusion_finish_date', 'N/A')}, Proposed: {record.get('proposed_extension_finish_date', 'N/A')}, Weeks: {record.get('extension_weeks', 'N/A')}"
                
                waitlist_status = record.get('waitlist_status', 'Not Applicable')
                
                ws.cell(row_idx, 1, record.get('school', ''))
                ws.cell(row_idx, 2, record.get('student_name', ''))
                ws.cell(row_idx, 3, record.get('program', ''))
                ws.cell(row_idx, 4, record.get('school_contact', ''))
                ws.cell(row_idx, 5, record_type)
                ws.cell(row_idx, 6, record.get('outcome', ''))
                ws.cell(row_idx, 7, waitlist_status)
                ws.cell(row_idx, 8, ext_details)
                ws.cell(row_idx, 9, record.get('information', ''))
                ws.cell(row_idx, 10, record.get('actioned_by', ''))
                
                # RED HIGHLIGHT for Site Decision rows
                if waitlist_status == 'Site Decision':
                    for col in range(1, 11):
                        cell = ws.cell(row_idx, col)
                        cell.fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                        cell.font = Font(color="FFFFFF", bold=True)
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 25  # School
            ws.column_dimensions['B'].width = 20  # Student
            ws.column_dimensions['C'].width = 20  # Program
            ws.column_dimensions['D'].width = 20  # School Contact
            ws.column_dimensions['E'].width = 12  # Type
            ws.column_dimensions['F'].width = 15  # Outcome
            ws.column_dimensions['G'].width = 18  # Waitlist Status
            ws.column_dimensions['H'].width = 40  # Extension Details
            ws.column_dimensions['I'].width = 40  # Information
            ws.column_dimensions['J'].width = 20  # Actioned By
            
            # Save to bytes
            output = BytesIO()
            wb.save(output)
            excel_data = output.getvalue()
            
            # Download button
            st.download_button(
                label="💾 Save Communication Summary",
                data=excel_data,
                file_name=f"Communication_{selected_week.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success(f"✅ Communication summary ready! {len(comm_data.data)} record(s)")
            st.session_state.download_comms = False
        else:
            st.info("📭 No communications for this week")
            st.session_state.download_comms = False
    except Exception as e:
        st.error(f"Error: {e}")
        st.session_state.download_comms = False

# Caption
st.caption("CLC-LBU Allocation Meetings Tool V4 | Extensions & Not Allocated Auto-compile")
