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
PROGRAMS = ["Junior Primary", "Primary", "Secondary"]
CAT_FUNDING_OPTIONS = ["ATSI", "SIC", "SWD", "DCP", "SCH"]
PARTNERSHIP_OPTIONS = ["MH", "PREV", "EALD", "CAHMS", "ASD"]
STAFF_NAMES = ["Candice", "Annette", "Tom", "Gary", "Caitie", "Jacqui", 
               "Ben Sutton", "Ben Selga", "Brenton", "Vinnie"]
OUTCOMES = ["Allocated", "Not Allocated"]
EXTENSION_OUTCOMES = ["Approved", "Not Approved"]

# Program mapping for Data Entry format
PROGRAM_MAPPING = {
    "Junior Primary": "Primary (R-6)",
    "Primary": "Primary (R-6)",
    "Secondary": "Middle (7-9)"
}

# Helper functions
def get_current_term_week():
    """Calculate current term and week based on SA school calendar"""
    today = datetime.now().date()
    year = today.year
    
    # Term 2 2025 dates
    term_2_start = datetime(2025, 4, 28).date()
    term_2_end = datetime(2025, 7, 4).date()
    
    if term_2_start <= today <= term_2_end:
        weeks_in = ((today - term_2_start).days // 7) + 1
        return f"Term 2", weeks_in, year
    
    return "Term 2", 1, 2025

def get_meeting_weeks(term, year):
    """Generate list of meeting weeks for a term"""
    return [f"Week {i} {term}" for i in range(1, 11)]

def get_thursday_date(week_number, term, year):
    """Calculate Thursday date for a given week"""
    term_2_start = datetime(2025, 4, 28).date()
    days_to_add = (week_number - 1) * 7 + 3
    thursday = term_2_start + timedelta(days=days_to_add)
    return thursday

def generate_student_id():
    """Generate next Student_ID in format STU-YYYY-###"""
    year = datetime.now().year
    
    # Get highest existing ID from Supabase
    result = supabase.table("allocation_students")\
        .select("id")\
        .execute()
    
    # Count records and increment
    count = len(result.data) if result.data else 0
    next_num = count + 1
    
    return f"STU-{year}-{next_num:03d}"

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
    
    # Map partnership
    if "ASD" in partnership:
        flags["Flag_ASD"] = "Yes"
    if "MH" in partnership or "CAHMS" in partnership:
        flags["Flag_MentalHealth"] = "Yes"
    if "EALD" in partnership:
        flags["Flag_EALD"] = "Yes"
    
    return flags

def export_to_data_entry(selected_allocations):
    """Generate Excel file in Data Entry format"""
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data_Model"
    
    # Define headers (29 columns)
    headers = [
        "Student_ID", "Student_Name", "DOB", "Gender", "Referring_School",
        "Referral_Date", "Allocation_Status", "Allocated_Program", 
        "Placement_Start", "Placement_End", "Partnership_Area",
        "Previous_CLC_Placement", "Previous_Other_LC", "Other_LC_Name",
        "Total_Previous_Placements", "Placement_History_Notes", "Priority_Level",
        "Flag_ASD", "Flag_ADHD", "Flag_MentalHealth", "Flag_ODD_CD",
        "Flag_Care_CPS", "Flag_Aboriginal", "Flag_EALD", "Flag_Other",
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
        
        # Today's date as referral date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Build row data
        row_data = [
            student_id,
            allocation.get('student_name', '').upper(),
            dob,
            "",  # Gender - not captured in meeting tool
            allocation.get('school', ''),
            today,  # Referral_Date (today)
            "Allocated",  # Allocation_Status
            mapped_program,
            start_date,
            end_date if end_date else None,
            "",  # Partnership_Area - not captured
            "No",  # Previous_CLC_Placement
            "No",  # Previous_Other_LC
            None,  # Other_LC_Name
            0,  # Total_Previous_Placements
            None,  # Placement_History_Notes
            None,  # Priority_Level
            flags["Flag_ASD"],
            flags["Flag_ADHD"],
            flags["Flag_MentalHealth"],
            flags["Flag_ODD_CD"],
            flags["Flag_Care_CPS"],
            flags["Flag_Aboriginal"],
            flags["Flag_EALD"],
            flags["Flag_Other"],
            "Active",  # Current_Status
            None,  # Exit_Reason
            None,  # Transition_Plan
            allocation.get('notes', '')
        ]
        
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row_num, col, value)
            cell.alignment = Alignment(horizontal="left", vertical="center")
    
    # Adjust column widths
    for col in range(1, 30):
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
st.markdown("**Weekly student placement allocation tracking**")

# Initialize session state
if 'current_term' not in st.session_state:
    term, week, year = get_current_term_week()
    st.session_state.current_term = term
    st.session_state.current_week = week
    st.session_state.current_year = year

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

# TAB 1: New Student Allocations
with tab1:
    st.header("New Student Allocations")
    
    with st.form("new_allocation_form", clear_on_submit=True):
        st.subheader("Student Information")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            student_name = st.text_input("Name *", key="alloc_name")
            school = st.text_input("School", key="alloc_school")
        with col2:
            dob = st.date_input("Date of Birth", value=None, key="alloc_dob")
            year_level = st.text_input("Year Level", key="alloc_year_level")
        with col3:
            exc_tsp = st.text_input("Exc/TSP/ITSP", key="alloc_exc")
            edid = st.text_input("EDID", key="alloc_edid")
        
        st.markdown("---")
        st.subheader("Categorical Funding & Partnership")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Categorical Funding**")
            cat_funding = []
            for option in CAT_FUNDING_OPTIONS:
                if st.checkbox(option, key=f"cat_{option}"):
                    cat_funding.append(option)
        
        with col2:
            st.write("**Partnership**")
            partnership = []
            for option in PARTNERSHIP_OPTIONS:
                if st.checkbox(option, key=f"part_{option}"):
                    partnership.append(option)
        
        st.markdown("---")
        st.subheader("Program & Placement")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            program = st.selectbox("Program *", [""] + PROGRAMS, key="alloc_program")
        with col2:
            start_after = st.date_input("Start After", value=None, key="alloc_start")
        with col3:
            finishing_date = st.date_input("Finishing Date", value=None, key="alloc_finish")
        
        st.markdown("---")
        st.subheader("Case Support Team")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            case_worker = st.selectbox("Case Worker", [""] + STAFF_NAMES, key="alloc_cw")
        with col2:
            bsc = st.selectbox("BSC", [""] + STAFF_NAMES, key="alloc_bsc")
        with col3:
            school_contact = st.text_input("School Contact", key="alloc_school_contact")
        
        st.markdown("---")
        st.subheader("Meeting Details")
        
        queries = st.text_area("Queries", key="alloc_queries", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            outcome = st.selectbox("Outcome *", [""] + OUTCOMES, key="alloc_outcome")
        with col2:
            details = st.text_area("Details", key="alloc_details", height=100)
        
        notes = st.text_area("Notes", key="alloc_notes", height=100)
        
        # Submit button
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            submit_allocation = st.form_submit_button("➕ Add Allocation", use_container_width=True)
        
        if submit_allocation:
            if not student_name or not program or not outcome:
                st.error("⚠️ Please fill in all required fields (Name, Program, Outcome)")
            else:
                try:
                    # Insert into database
                    data = {
                        "meeting_week": meeting_week_label,
                        "meeting_date": meeting_date.isoformat(),
                        "term": st.session_state.current_term,
                        "year": st.session_state.current_year,
                        "student_name": student_name,
                        "school": school,
                        "date_of_birth": dob.isoformat() if dob else None,
                        "year_level": year_level,
                        "exc_tsp_itsp": exc_tsp,
                        "edid": edid,
                        "cat_funding": json.dumps(cat_funding),
                        "partnership": json.dumps(partnership),
                        "program": program,
                        "start_after": start_after.isoformat() if start_after else None,
                        "finishing_date": finishing_date.isoformat() if finishing_date else None,
                        "case_worker": case_worker,
                        "bsc": bsc,
                        "school_contact": school_contact,
                        "queries": queries,
                        "outcome": outcome,
                        "details": details,
                        "notes": notes,
                        "created_by": "System"
                    }
                    
                    result = supabase.table("allocation_students").insert(data).execute()
                    st.success(f"✅ Successfully added allocation for {student_name}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error saving allocation: {str(e)}")

# TAB 2: Extension Requests
with tab2:
    st.header("Extension Requests")
    
    with st.form("extension_form", clear_on_submit=True):
        st.subheader("Student Requesting Extension")
        
        col1, col2 = st.columns(2)
        with col1:
            ext_student_name = st.text_input("Student Name *", key="ext_name")
            ext_program = st.selectbox("Program *", [""] + PROGRAMS, key="ext_program")
        
        with col2:
            ext_outcome = st.selectbox("Extension Outcome", [""] + EXTENSION_OUTCOMES, key="ext_outcome")
            ext_conditional = st.checkbox("Conditional (YES/NO)", key="ext_conditional")
        
        st.markdown("---")
        st.subheader("Details")
        
        ext_info_school = st.text_area("Information to School", key="ext_info", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            ext_actioned = st.selectbox("Actioned By", [""] + STAFF_NAMES, key="ext_actioned")
        with col2:
            ext_extended_until = st.date_input("Extended Until", value=None, key="ext_until")
        
        st.markdown("---")
        st.subheader("Support Team")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            ext_referrer = st.text_input("School Referrer", key="ext_referrer")
        with col2:
            ext_caseworker = st.text_input("Caseworker", key="ext_caseworker")
        with col3:
            ext_bse = st.text_input("Behaviour Support Educator", key="ext_bse")
        
        # Submit button
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            submit_extension = st.form_submit_button("➕ Add Extension", use_container_width=True)
        
        if submit_extension:
            if not ext_student_name or not ext_program:
                st.error("⚠️ Please fill in Student Name and Program")
            else:
                try:
                    data = {
                        "meeting_week": meeting_week_label,
                        "meeting_date": meeting_date.isoformat(),
                        "term": st.session_state.current_term,
                        "year": st.session_state.current_year,
                        "student_name": ext_student_name,
                        "program": ext_program,
                        "extension_outcome": ext_outcome,
                        "conditional": ext_conditional,
                        "information_to_school": ext_info_school,
                        "actioned_by": ext_actioned,
                        "extended_until": ext_extended_until.isoformat() if ext_extended_until else None,
                        "school_referrer": ext_referrer,
                        "caseworker": ext_caseworker,
                        "behaviour_support_educator": ext_bse,
                        "created_by": "System"
                    }
                    
                    result = supabase.table("allocation_extensions").insert(data).execute()
                    st.success(f"✅ Successfully added extension request for {ext_student_name}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error saving extension: {str(e)}")

# TAB 3: Students Not Placed
with tab3:
    st.header("Students Not Placed")
    
    with st.form("not_placed_form", clear_on_submit=True):
        st.subheader("Student Information")
        
        col1, col2 = st.columns(2)
        with col1:
            np_student_name = st.text_input("Student Name *", key="np_name")
            np_program = st.selectbox("Program *", [""] + PROGRAMS, key="np_program")
        with col2:
            np_school = st.text_input("School", key="np_school")
        
        st.markdown("---")
        st.subheader("Reasons for Non-Placement")
        
        col1, col2 = st.columns(2)
        with col1:
            reason_full = st.checkbox("Program is at full capacity", key="np_full")
            reason_slc = st.checkbox("Panel explored SLC as possible option", key="np_slc")
        with col2:
            reason_docs = st.checkbox("Correct documentation needs to be provided", key="np_docs")
            reason_other = st.text_input("Other reason", key="np_other")
        
        np_info_school = st.text_area("Information to School", key="np_info", height=100)
        
        st.markdown("---")
        st.subheader("Follow-up")
        
        col1, col2 = st.columns(2)
        with col1:
            np_request_next = st.checkbox("Request to be considered next Allocation Meeting", key="np_next")
        
        st.markdown("---")
        st.subheader("Support Team")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            np_referrer = st.text_input("School Referrer", key="np_referrer")
        with col2:
            np_caseworker = st.text_input("Caseworker", key="np_caseworker")
        with col3:
            np_bse = st.text_input("Behaviour Support Educator", key="np_bse")
        
        # Submit button
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            submit_not_placed = st.form_submit_button("➕ Add Record", use_container_width=True)
        
        if submit_not_placed:
            if not np_student_name or not np_program:
                st.error("⚠️ Please fill in Student Name and Program")
            else:
                try:
                    data = {
                        "meeting_week": meeting_week_label,
                        "meeting_date": meeting_date.isoformat(),
                        "term": st.session_state.current_term,
                        "year": st.session_state.current_year,
                        "student_name": np_student_name,
                        "program": np_program,
                        "school": np_school,
                        "information_to_school": np_info_school,
                        "reason_full_capacity": reason_full,
                        "reason_slc_option": reason_slc,
                        "reason_documentation_needed": reason_docs,
                        "reason_other": reason_other,
                        "request_next_meeting": np_request_next,
                        "school_referrer": np_referrer,
                        "caseworker": np_caseworker,
                        "behaviour_support_educator": np_bse,
                        "created_by": "System"
                    }
                    
                    result = supabase.table("allocation_not_placed").insert(data).execute()
                    st.success(f"✅ Successfully added record for {np_student_name}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error saving record: {str(e)}")

# TAB 4: View & Export
with tab4:
    st.header(f"Meeting Records - {meeting_week_label}")
    
    # Fetch data for current week
    try:
        students_data = supabase.table("allocation_students")\
            .select("*")\
            .eq("meeting_week", meeting_week_label)\
            .eq("term", st.session_state.current_term)\
            .eq("year", st.session_state.current_year)\
            .execute()
        
        extensions_data = supabase.table("allocation_extensions")\
            .select("*")\
            .eq("meeting_week", meeting_week_label)\
            .eq("term", st.session_state.current_term)\
            .eq("year", st.session_state.current_year)\
            .execute()
        
        not_placed_data = supabase.table("allocation_not_placed")\
            .select("*")\
            .eq("meeting_week", meeting_week_label)\
            .eq("term", st.session_state.current_term)\
            .eq("year", st.session_state.current_year)\
            .execute()
        
        # Display counts
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("New Allocations", len(students_data.data))
        with col2:
            st.metric("Extensions", len(extensions_data.data))
        with col3:
            st.metric("Not Placed", len(not_placed_data.data))
        
        st.markdown("---")
        
        # NEW: Export to Data Entry Section
        allocated_students = [s for s in students_data.data if s.get('outcome') == 'Allocated']
        
        if allocated_students:
            st.subheader("📤 Export to Allocation Data Entry")
            st.info("💡 Select allocated students to export in Data Entry format for your SharePoint tracker")
            
            # Selection interface
            if 'selected_for_export' not in st.session_state:
                st.session_state.selected_for_export = set()
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write("**Select students to export:**")
            with col2:
                if st.button("Select All Allocated"):
                    st.session_state.selected_for_export = {s['id'] for s in allocated_students}
                    st.rerun()
            
            # Checkboxes for each allocated student
            for student in allocated_students:
                col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
                with col1:
                    is_selected = student['id'] in st.session_state.selected_for_export
                    if st.checkbox("", value=is_selected, key=f"export_{student['id']}"):
                        st.session_state.selected_for_export.add(student['id'])
                    elif is_selected:
                        st.session_state.selected_for_export.discard(student['id'])
                with col2:
                    st.write(f"**{student['student_name']}**")
                with col3:
                    st.write(student.get('program', ''))
                with col4:
                    st.write(student.get('school', '')[:20])
            
            # Export button
            if st.session_state.selected_for_export:
                st.markdown("---")
                selected_count = len(st.session_state.selected_for_export)
                
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    if st.button(f"📥 Export {selected_count} Student{'s' if selected_count > 1 else ''}", 
                               use_container_width=True, type="primary"):
                        # Get selected allocations
                        selected = [s for s in allocated_students if s['id'] in st.session_state.selected_for_export]
                        
                        # Generate Data Entry Excel
                        data_entry_excel = export_to_data_entry(selected)
                        
                        st.download_button(
                            label="⬇️ Download Data Entry Excel",
                            data=data_entry_excel,
                            file_name=f"Allocation_DataEntry_{meeting_week_label.replace(' ', '_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        
                        st.success(f"✅ Generated Data Entry format for {selected_count} student(s)")
                        st.info("📋 **Next Steps:**\n1. Download the file above\n2. Open your SharePoint Allocation Data Entry\n3. Copy rows from this file\n4. Paste into your tracker")
        
        st.markdown("---")
        
        # Display data tables
        if students_data.data:
            st.subheader("📝 Student Allocations")
            df_students = pd.DataFrame(students_data.data)
            
            # Format for display
            display_cols = ['student_name', 'school', 'program', 'outcome', 
                          'case_worker', 'bsc', 'start_after', 'finishing_date']
            display_cols = [col for col in display_cols if col in df_students.columns]
            st.dataframe(df_students[display_cols], use_container_width=True)
            
            # Edit/Delete options
            with st.expander("🔧 Manage Records"):
                record_to_edit = st.selectbox(
                    "Select record",
                    options=df_students['id'].tolist(),
                    format_func=lambda x: df_students[df_students['id'] == x]['student_name'].iloc[0]
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit", key="edit_student"):
                        st.info("Edit functionality coming soon")
                with col2:
                    if st.button("🗑️ Delete", key="delete_student"):
                        try:
                            supabase.table("allocation_students").delete().eq("id", record_to_edit).execute()
                            st.success("Record deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        if extensions_data.data:
            st.markdown("---")
            st.subheader("🔄 Extensions")
            df_extensions = pd.DataFrame(extensions_data.data)
            display_cols = ['student_name', 'program', 'extension_outcome', 
                          'conditional', 'extended_until', 'actioned_by']
            display_cols = [col for col in display_cols if col in df_extensions.columns]
            st.dataframe(df_extensions[display_cols], use_container_width=True)
        
        if not_placed_data.data:
            st.markdown("---")
            st.subheader("⏸️ Not Placed")
            df_not_placed = pd.DataFrame(not_placed_data.data)
            display_cols = ['student_name', 'school', 'program', 
                          'request_next_meeting', 'school_referrer']
            display_cols = [col for col in display_cols if col in df_not_placed.columns]
            st.dataframe(df_not_placed[display_cols], use_container_width=True)
        
        # Original Excel export (for meeting notes)
        st.markdown("---")
        st.subheader("📄 Export Meeting Notes")
        
        week_data = {
            'students': students_data.data,
            'extensions': extensions_data.data,
            'not_placed': not_placed_data.data
        }
        
        if any(week_data.values()):
            excel_file = export_to_excel(week_data)
            
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                st.download_button(
                    label="📥 Download Meeting Notes",
                    data=excel_file,
                    file_name=f"Allocation_Meeting_Notes_{meeting_week_label.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.info("No records to export for this week")
            
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        st.info("💡 Make sure the database tables have been created using the schema file")

# Footer
st.markdown("---")
st.caption("CLC-LBU Allocation Meetings Tool | Streamlit + Supabase + Excel Export")
