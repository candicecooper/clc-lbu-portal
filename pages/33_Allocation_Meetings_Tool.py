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
CAT_FUNDING_OPTIONS = ["ATSI", "SIC", "SWD", "DCP", "SCH"]
PARTNERSHIP_OPTIONS = ["MH", "PREV", "EALD", "CAHMS", "ASD"]
STAFF_NAMES = ["Candice", "Annette", "Tom", "Gary", "Caitie", "Jacqui", 
               "Ben Sutton", "Ben Selga", "Brenton", "Vinnie"]
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
    """Map categorical funding and partnership to flag columns"""
    flags = {
        "Flag_ASD": "No",
        "Flag_ADHD": "No",
        "Flag_MentalHealth": "No",
        "Flag_ODD_CD": "No",
        "Flag_Care_CPS": "No",
        "Flag_Aboriginal": "No",
        "Flag_EALD": "No",
        "Flag_Other": "No"
    }
    
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
    
    # Map categorical funding
    if "ATSI" in cat_funding:
        flags["Flag_Aboriginal"] = "Yes"
    if "SIC" in cat_funding or "DCP" in cat_funding:
        flags["Flag_Care_CPS"] = "Yes"
    if "SWD" in cat_funding:
        flags["Flag_Other"] = "Yes"
    
    # Map partnership
    if "ASD" in partnership:
        flags["Flag_ASD"] = "Yes"
    if "MH" in partnership or "CAHMS" in partnership:
        flags["Flag_MentalHealth"] = "Yes"
    if "EALD" in partnership:
        flags["Flag_EALD"] = "Yes"
    
    return flags

def export_to_data_entry(selected_allocations):
    """Generate Excel file in Data Entry format with ALL database fields"""
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data_Model"
    
    # Define headers - COMPLETE SET matching allocation_tracker table
    headers = [
        "Student_ID", "Student_Name", "DOB", "Gender", "Year_Level", "Referring_School",
        "Referral_Date", "Allocation_Status", "Allocated_Program", 
        "Placement_Start", "Placement_End", "Partnership_Area",
        "Previous_CLC_Placement", "Previous_Other_LC", "Other_LC_Name",
        "Total_Previous_Placements", "Placement_History_Notes", "Priority_Level",
        "Flag_ASD", "Flag_ADHD", "Flag_MentalHealth", "Flag_ODD_CD",
        "Flag_Care_CPS", "Flag_Aboriginal", "Flag_EALD", "Flag_Other",
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
        
        # Build row data - COMPLETE SET
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
            flags["Flag_ASD"],                                   # 19. Flag_ASD
            flags["Flag_ADHD"],                                  # 20. Flag_ADHD
            flags["Flag_MentalHealth"],                          # 21. Flag_MentalHealth
            flags["Flag_ODD_CD"],                                # 22. Flag_ODD_CD
            flags["Flag_Care_CPS"],                              # 23. Flag_Care_CPS
            flags["Flag_Aboriginal"],                            # 24. Flag_Aboriginal
            flags["Flag_EALD"],                                  # 25. Flag_EALD
            flags["Flag_Other"],                                 # 26. Flag_Other
            allocation.get('bespoke_placement', 'No'),           # 27. Bespoke_Placement
            allocation.get('waitlist_status', 'Not Applicable'), # 28. Waitlist_Status
            waitlist_date,                                       # 29. Waitlist_Date
            allocation.get('allocated_from_waitlist', 'No'),     # 30. Allocated_From_Waitlist
            "Active",                                            # 31. Current_Status
            allocation.get('exit_reason', ''),                   # 32. Exit_Reason
            allocation.get('transition_plan', ''),               # 33. Transition_Plan
            allocation.get('notes', '')                          # 34. Notes
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
                        st.write(f"**Queries:** {draft.get('queries', 'None')[:50]}...")
                
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
                                waitlist_date = st.date_input("Waitlist Date", value=None)
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
                            start_after = st.date_input("Start After", value=None)
                        with col3:
                            finishing_date = st.date_input("Finishing Date", value=None)
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
                            bsc = st.selectbox("BSC", [""] + STAFF_NAMES)
                        with col3:
                            school_contact = st.text_input("School Contact")
                        
                        notes = st.text_area("Additional Notes", height=80)
                    else:
                        # Not allocated - set defaults
                        waitlist_status = "Not Applicable"
                        waitlist_date = None
                        allocated_from_waitlist = "No"
                        program = ""
                        start_after = None
                        finishing_date = None
                        bespoke_placement = "No"
                        case_worker = ""
                        bsc = ""
                        school_contact = ""
                        notes = ""
                    
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
                                # Update the draft with completion data
                                update_data = {
                                    "outcome": outcome,
                                    "details": details,
                                    "waitlist_status": waitlist_status,
                                    "waitlist_date": waitlist_date.isoformat() if waitlist_date else None,
                                    "allocated_from_waitlist": allocated_from_waitlist,
                                    "program": program,
                                    "start_after": start_after.isoformat() if start_after else None,
                                    "finishing_date": finishing_date.isoformat() if finishing_date else None,
                                    "bespoke_placement": bespoke_placement,
                                    "case_worker": case_worker,
                                    "bsc": bsc,
                                    "school_contact": school_contact,
                                    "notes": notes
                                }
                                
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
                dob = st.date_input("Date of Birth", value=None)
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
            
            col1, col2, col3 = st.columns(3)
            with col1:
                previous_clc = st.selectbox("Previous CLC Placement?", ["No", "Yes"])
            with col2:
                previous_other_lc = st.selectbox("Previous Other LC?", ["No", "Yes"])
            with col3:
                if previous_other_lc == "Yes":
                    other_lc_name = st.text_input("Other LC Name")
                else:
                    other_lc_name = ""
            
            if previous_clc == "Yes" or previous_other_lc == "Yes":
                col1, col2 = st.columns(2)
                with col1:
                    total_placements = st.number_input("Total Previous Placements", min_value=0, value=1)
                with col2:
                    placement_history_notes = st.text_input("Placement History Notes")
            else:
                total_placements = 0
                placement_history_notes = ""
            
            # SECTION 3: Categorical Funding & Partnership
            st.markdown("---")
            st.markdown("### 3️⃣ Categorical Funding & Partnership Support")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Categorical Funding**")
                cat_funding = []
                for option in CAT_FUNDING_OPTIONS:
                    if st.checkbox(option, key=f"cat_{option}"):
                        cat_funding.append(option)
            
            with col2:
                st.write("**Partnership Support**")
                partnership = []
                for option in PARTNERSHIP_OPTIONS:
                    if st.checkbox(option, key=f"part_{option}"):
                        partnership.append(option)
            
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
                            "other_lc_name": other_lc_name if previous_other_lc == "Yes" else None,
                            "total_previous_placements": total_placements,
                            "placement_history_notes": placement_history_notes,
                            "cat_funding": json.dumps(cat_funding),
                            "partnership": json.dumps(partnership),
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

# Rest of tabs remain unchanged...
st.caption("CLC-LBU Allocation Meetings Tool V3 | Simplified Draft System")
