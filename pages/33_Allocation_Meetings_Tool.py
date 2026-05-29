import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os
from io import BytesIO
import shutil

# Page config
st.set_page_config(
    page_title="Allocation Meetings - CLC-LBU",
    page_icon="📋",
    layout="wide"
)

# Persistent file storage - saves to app directory
PERSISTENT_DIR = "/tmp/clc_allocation"
os.makedirs(PERSISTENT_DIR, exist_ok=True)
STORED_FILE_PATH = os.path.join(PERSISTENT_DIR, "CLC_Allocation_Data.xlsx")

# Initialize session state
if 'loaded_file' not in st.session_state:
    st.session_state.loaded_file = None
if 'df_cache' not in st.session_state:
    st.session_state.df_cache = None

# Define constants
PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
STAFF_NAMES = ["Candice", "Annette", "Naomi/Cheryl", "Catie", "Ben Selga", "Ben Sutton", "Jacqui", "Brenton"]
OUTCOMES = ["Allocated", "Not Allocated"]
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
WAITLIST_STATUS_OPTIONS = ["Not Applicable", "On Waitlist", "Declined", "Site Decision", "Site Withdraw"]

# Load school-partnership mapping from stored file
def load_school_partnership_map(df):
    """Load school mapping from Data_Model sheet"""
    school_map = {}
    if 'Referring_School' in df.columns and 'Partnership_Area' in df.columns:
        for idx, row in df.iterrows():
            school = row.get('Referring_School')
            partnership = row.get('Partnership_Area')
            if school and partnership:
                school_map[school] = partnership
    return school_map

# Load Excel data
def load_allocation_data(file_path):
    """Load allocation data from Excel"""
    try:
        df = pd.read_excel(file_path, sheet_name="Data_Model")
        return df
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return None

# Save data to Excel
def save_allocation_data(df, file_path):
    """Save allocation data back to Excel"""
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name="Data_Model", index=False)
        return True
    except Exception as e:
        st.error(f"Error saving to Excel: {str(e)}")
        return False

def get_partnership_from_school(school, school_map):
    """Get partnership area based on school name"""
    return school_map.get(school, "")

# Dark Theme CSS
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background: #0F1729 !important;
    }
    
    .main > div {
        padding: 1.5rem 2rem;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    h1, h2, h3 {
        color: #FFFFFF !important;
    }
    
    p, div, label {
        color: #8B9DC3 !important;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1A2942 0%, #243556 100%) !important;
        border: 1.5px solid #2D3F5F !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    
    .stButton>button:hover {
        border-color: #00D9FF !important;
        box-shadow: 0 8px 32px rgba(0, 217, 255, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1>📋 Allocation Meetings Tool</h1>", unsafe_allow_html=True)
st.markdown("<p>Manage student allocations and track meeting decisions</p>", unsafe_allow_html=True)
st.markdown("---")

# FILE MANAGEMENT SECTION
st.markdown("### 📁 Excel File Management")

col1, col2, col3 = st.columns([2, 1, 1])

# Check if file exists from previous upload
file_exists = os.path.exists(STORED_FILE_PATH)

with col1:
    if file_exists:
        st.success(f"✅ File loaded: `CLC_Allocation_Data.xlsx`")
        st.caption(f"Last modified: {datetime.fromtimestamp(os.path.getmtime(STORED_FILE_PATH)).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.info("📤 No file loaded yet. Upload your Excel file below.")

with col2:
    uploaded_file = st.file_uploader(
        "Upload/Update File",
        type="xlsx",
        help="Upload your CLC_Allocation_Dashboard Excel file"
    )
    
    if uploaded_file is not None:
        # Save uploaded file to persistent storage
        with open(STORED_FILE_PATH, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ File uploaded and saved!")
        st.session_state.loaded_file = STORED_FILE_PATH
        st.session_state.df_cache = None  # Clear cache to reload
        st.rerun()

with col3:
    if file_exists:
        # Read file for download
        with open(STORED_FILE_PATH, "rb") as f:
            file_data = f.read()
        st.download_button(
            label="📥 Download Current",
            data=file_data,
            file_name=f"CLC_Allocation_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download the current Excel file with all updates"
        )

st.markdown("---")

# Load data
if file_exists or st.session_state.loaded_file:
    if st.session_state.df_cache is None:
        df = load_allocation_data(STORED_FILE_PATH)
        st.session_state.df_cache = df
    else:
        df = st.session_state.df_cache
    
    if df is None:
        st.error("Failed to load Excel file. Please upload a valid file.")
        st.stop()
    
    # Get school map from data
    school_map = load_school_partnership_map(df)
    ALL_SCHOOLS = sorted([s for s in school_map.keys() if pd.notna(s)])
    PARTNERSHIP_AREAS = sorted(list(set(school_map.values())))
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Create New", "📝 Complete Existing", "📊 View All", "⚙️ Settings"])

    with tab1:
        st.subheader("➕ Create New Allocation Draft")
        st.caption("Fill in student details before the meeting. Complete on meeting day.")
        
        with st.form("new_allocation_draft"):
            # SECTION 1: Basic Information
            st.markdown("### 1️⃣ Student Details")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                student_name = st.text_input("Name *")
            with col2:
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
                auto_partnership = get_partnership_from_school(school, school_map) if school else ""
                partnership_area = st.text_input("Partnership Area (auto-filled)", value=auto_partnership, disabled=True)
            with col3:
                priority_level = st.selectbox("Priority Level", [""] + ["1", "2", "3", "4", "5"])
            
            # SECTION 2: Placement History
            st.markdown("### 2️⃣ Placement History")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                previous_clc = st.selectbox("Previous CLC Placement?", ["No", "Yes"])
            with col2:
                if previous_clc == "Yes":
                    previous_other_lc = st.selectbox("Previous Other LC?", ["No", "Yes"])
                else:
                    previous_other_lc = "No"
            with col3:
                if previous_other_lc == "Yes":
                    other_lc_name = st.text_input("Other LC Name")
                else:
                    other_lc_name = None
            
            # SECTION 3: Flags
            st.markdown("### 3️⃣ Student Flags")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write("**Language & Culture**")
                flag_eald = st.checkbox("EALD")
                flag_atsi = st.checkbox("ATSI")
            with col2:
                st.write("**Attendance**")
                flag_attendance_full = st.checkbox("Fulltime")
                flag_attendance_part = st.checkbox("Parttime")
            with col3:
                st.write("**Care & Custody**")
                flag_custody = st.checkbox("Intervention/Custody Order")
                flag_dcp = st.checkbox("DCP involvement")
                flag_child_care = st.checkbox("Child in care")
            with col4:
                st.write("**Support Needs**")
                flag_swd = st.checkbox("SWD")
                flag_asd = st.checkbox("ASD")
                flag_speech = st.checkbox("Speech & Language")
            
            # SECTION 4: Dates & Status
            st.markdown("### 4️⃣ Referral Information")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                referral_date = st.date_input("Referral Date *", value=date.today())
            with col2:
                meeting_week = st.text_input("Meeting Week (e.g., Week 3, Term 2)", placeholder="e.g., Week 3")
            with col3:
                meeting_date = st.date_input("Meeting Date (optional)", value=None)
            
            # Submit
            submitted = st.form_submit_button("✅ Create Draft", type="primary", use_container_width=True)
            
            if submitted:
                if not student_name or not school or not year_level or not referral_date:
                    st.error("⚠️ Please fill in all required fields (*)")
                else:
                    try:
                        # Create new row
                        new_row = {
                            'Student_ID': f"NEW_{int(datetime.now().timestamp())}",
                            'Student_Name': student_name,
                            'DOB': dob,
                            'Gender': gender if gender else None,
                            'Year_Level': year_level,
                            'Referring_School': school,
                            'Partnership_Area': partnership_area,
                            'Referral_Date': referral_date,
                            'Meeting_Week': meeting_week,
                            'Meeting_Date': meeting_date,
                            'Allocation_Status': None,
                            'Previous_CLC_Placement': previous_clc,
                            'Previous_Other_LC': previous_other_lc,
                            'Other_LC_Name': other_lc_name,
                            'Flag_EALD': 'Yes' if flag_eald else 'No',
                            'Flag_ATSI': 'Yes' if flag_atsi else 'No',
                            'Flag_Attendance_Fulltime': 'Yes' if flag_attendance_full else 'No',
                            'Flag_Attendance_Parttime': 'Yes' if flag_attendance_part else 'No',
                            'Flag_Intervention_Custody_Order': 'Yes' if flag_custody else 'No',
                            'Flag_DCP_involvement': 'Yes' if flag_dcp else 'No',
                            'Flag_Child_in_care': 'Yes' if flag_child_care else 'No',
                            'Flag_SWD': 'Yes' if flag_swd else 'No',
                            'Flag_ASD': 'Yes' if flag_asd else 'No',
                            'Flag_Speech_and_Lang': 'Yes' if flag_speech else 'No',
                            'Referral_Year': datetime.now().year,
                        }
                        
                        # Add row to dataframe
                        new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        
                        # Save to Excel
                        if save_allocation_data(new_df, STORED_FILE_PATH):
                            st.success(f"✅ Draft created for **{student_name}**!")
                            st.balloons()
                            st.session_state.df_cache = None  # Clear cache
                            st.info("💡 Go to Tab 2 to complete this allocation on meeting day.")
                        else:
                            st.error("Failed to save to Excel")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

    with tab2:
        st.subheader("📝 Complete Existing Draft")
        st.caption("Select a draft to complete with allocation decision details")
        
        # Reload fresh data
        df_fresh = load_allocation_data(STORED_FILE_PATH)
        
        # Find drafts (rows with no Allocation_Status)
        drafts = df_fresh[df_fresh['Allocation_Status'].isna()]
        
        if len(drafts) == 0:
            st.info("✅ No drafts found. Create a new draft in Tab 1.")
        else:
            draft_options = {f"{row['Student_Name']} ({row.get('Referring_School', 'No school')})": idx 
                            for idx, row in drafts.iterrows()}
            
            selected_display = st.selectbox(
                f"Select one of {len(drafts)} draft(s):",
                list(draft_options.keys())
            )
            
            draft_idx = draft_options[selected_display]
            draft = drafts.loc[draft_idx]
            
            st.success(f"✅ Loaded draft for: **{draft['Student_Name']}**")
            
            # Show draft details
            with st.expander("📋 View Draft Details", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**School:** {draft.get('Referring_School', 'N/A')}")
                    st.write(f"**Year Level:** {draft.get('Year_Level', 'N/A')}")
                with col2:
                    st.write(f"**Gender:** {draft.get('Gender', 'N/A')}")
                    st.write(f"**Partnership:** {draft.get('Partnership_Area', 'N/A')}")
                with col3:
                    st.write(f"**Referral Date:** {draft.get('Referral_Date', 'N/A')}")
            
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
                    case_worker = st.text_input("Case Worker Name")
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
                        waitlist_date = st.date_input("Waitlist Date", value=date.today())
                    else:
                        waitlist_date = None
                
                # BSE Section
                st.markdown("### 👤 BSE (Behaviour Support & Engagement)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    bse_involved = st.selectbox("BSE Involved?", ["No", "Yes"])
                with col2:
                    if bse_involved == "Yes":
                        bse_name = st.text_input("BSE Staff Name *", placeholder="Enter name of BSE staff member")
                    else:
                        bse_name = None
                
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
                    if not outcome:
                        st.error("⚠️ Please select an outcome")
                    elif bse_involved == "Yes" and not bse_name:
                        st.error("⚠️ Please enter BSE staff name if BSE is involved")
                    else:
                        try:
                            # Update the row
                            df_fresh.loc[draft_idx, 'Allocated_Program'] = program
                            df_fresh.loc[draft_idx, 'Allocation_Status'] = outcome
                            df_fresh.loc[draft_idx, 'Placement_Start'] = start_after
                            df_fresh.loc[draft_idx, 'Placement_End'] = finishing_date
                            df_fresh.loc[draft_idx, 'Bespoke_Placement'] = bespoke
                            df_fresh.loc[draft_idx, 'Waitlist_Status'] = waitlist_status
                            df_fresh.loc[draft_idx, 'Waitlist_Date'] = waitlist_date
                            df_fresh.loc[draft_idx, 'Communication_to_school'] = information
                            df_fresh.loc[draft_idx, 'Action_owner'] = actioned_by
                            
                            # Add BSE columns if they don't exist
                            if 'BSE_Involved' not in df_fresh.columns:
                                df_fresh['BSE_Involved'] = None
                            if 'BSE_Name' not in df_fresh.columns:
                                df_fresh['BSE_Name'] = None
                            
                            df_fresh.loc[draft_idx, 'BSE_Involved'] = bse_involved
                            df_fresh.loc[draft_idx, 'BSE_Name'] = bse_name
                            
                            # Save to Excel
                            if save_allocation_data(df_fresh, STORED_FILE_PATH):
                                st.success(f"✅ Allocation completed for {draft['Student_Name']}!")
                                st.balloons()
                                st.session_state.df_cache = None  # Clear cache
                                st.info("💡 Go to Tab 3 to view all allocations.")
                            else:
                                st.error("Failed to save to Excel")
                                
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())

    with tab3:
        st.subheader("📊 View All Allocations")
        
        # Reload data
        df_view = load_allocation_data(STORED_FILE_PATH)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filter_type = st.selectbox("Filter by Status", ["All", "Completed", "Drafts"])
        with col2:
            if st.button("🔄 Refresh Data"):
                st.session_state.df_cache = None
                st.rerun()
        
        if filter_type == "Completed":
            view_df = df_view[df_view['Allocation_Status'].notna()]
        elif filter_type == "Drafts":
            view_df = df_view[df_view['Allocation_Status'].isna()]
        else:
            view_df = df_view
        
        # Display key columns
        display_cols = ['Student_Name', 'Referring_School', 'Year_Level', 'Allocation_Status', 
                        'Allocated_Program', 'Placement_Start', 'Partnership_Area']
        available_cols = [col for col in display_cols if col in view_df.columns]
        
        st.dataframe(view_df[available_cols], use_container_width=True, height=400)
        
        st.caption(f"Total: {len(view_df)} records | Completed: {len(view_df[view_df['Allocation_Status'].notna()])} | Drafts: {len(view_df[view_df['Allocation_Status'].isna()])}")

    with tab4:
        st.subheader("⚙️ Settings")
        
        st.info(f"📂 **Storage:** Persistent (on Render)")
        st.info(f"📊 **Data Sheet:** Data_Model")
        
        st.markdown("### 📈 Data Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Students", len(df))
        with col2:
            completed = len(df[df['Allocation_Status'].notna()])
            st.metric("Completed", completed)
        with col3:
            drafts = len(df[df['Allocation_Status'].isna()])
            st.metric("Drafts", drafts)
        
        st.markdown("### 🔧 Maintenance")
        
        if st.button("💾 Force Save Excel File", help="Ensures all changes are saved"):
            if save_allocation_data(df, STORED_FILE_PATH):
                st.success("✅ File saved successfully!")
            else:
                st.error("❌ Error saving file")
        
        if st.checkbox("Show column names"):
            st.write("Available columns in Data_Model sheet:")
            st.code("\n".join(df.columns.tolist()))

else:
    st.warning("⚠️ Please upload an Excel file to get started!")


# Dark Theme CSS
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background: #0F1729 !important;
    }
    
    .main > div {
        padding: 1.5rem 2rem;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    h1, h2, h3 {
        color: #FFFFFF !important;
    }
    
    p, div, label {
        color: #8B9DC3 !important;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1A2942 0%, #243556 100%) !important;
        border: 1.5px solid #2D3F5F !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    
    .stButton>button:hover {
        border-color: #00D9FF !important;
        box-shadow: 0 8px 32px rgba(0, 217, 255, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1>📋 Allocation Meetings Tool</h1>", unsafe_allow_html=True)
st.markdown("<p>Manage student allocations and track meeting decisions</p>", unsafe_allow_html=True)
st.markdown("---")

# Load data
df = load_allocation_data(STORED_FILE_PATH)

if df is None:
    st.stop()

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["➕ Create New", "📝 Complete Existing", "📊 View All", "⚙️ Settings"])

with tab1:
    st.subheader("➕ Create New Allocation Draft")
    st.caption("Fill in student details before the meeting. Complete on meeting day.")
    
    with st.form("new_allocation_draft"):
        # SECTION 1: Basic Information
        st.markdown("### 1️⃣ Student Details")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            student_name = st.text_input("Name *")
        with col2:
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
            priority_level = st.selectbox("Priority Level", [""] + ["1", "2", "3", "4", "5"])
        
        # SECTION 2: Placement History
        st.markdown("### 2️⃣ Placement History")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            previous_clc = st.selectbox("Previous CLC Placement?", ["No", "Yes"])
        with col2:
            if previous_clc == "Yes":
                previous_other_lc = st.selectbox("Previous Other LC?", ["No", "Yes"])
            else:
                previous_other_lc = "No"
        with col3:
            if previous_other_lc == "Yes":
                other_lc_name = st.text_input("Other LC Name")
            else:
                other_lc_name = None
        
        # SECTION 3: Flags
        st.markdown("### 3️⃣ Student Flags")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("**Language & Culture**")
            flag_eald = st.checkbox("EALD")
            flag_atsi = st.checkbox("ATSI")
        with col2:
            st.write("**Attendance**")
            flag_attendance_full = st.checkbox("Fulltime")
            flag_attendance_part = st.checkbox("Parttime")
        with col3:
            st.write("**Care & Custody**")
            flag_custody = st.checkbox("Intervention/Custody Order")
            flag_dcp = st.checkbox("DCP involvement")
            flag_child_care = st.checkbox("Child in care")
        with col4:
            st.write("**Support Needs**")
            flag_swd = st.checkbox("SWD")
            flag_asd = st.checkbox("ASD")
            flag_speech = st.checkbox("Speech & Language")
        
        # SECTION 4: Dates & Status
        st.markdown("### 4️⃣ Referral Information")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            referral_date = st.date_input("Referral Date *", value=date.today())
        with col2:
            meeting_week = st.text_input("Meeting Week (e.g., Week 3, Term 2)", placeholder="e.g., Week 3")
        with col3:
            meeting_date = st.date_input("Meeting Date (optional)", value=None)
        
        # Submit
        submitted = st.form_submit_button("✅ Create Draft", type="primary", use_container_width=True)
        
        if submitted:
            if not student_name or not school or not year_level or not referral_date:
                st.error("⚠️ Please fill in all required fields (*)")
            else:
                try:
                    # Create new row
                    new_row = {
                        'Student_ID': f"NEW_{int(datetime.now().timestamp())}",
                        'Student_Name': student_name,
                        'DOB': dob,
                        'Gender': gender if gender else None,
                        'Year_Level': year_level,
                        'Referring_School': school,
                        'Partnership_Area': partnership_area,
                        'Referral_Date': referral_date,
                        'Meeting_Week': meeting_week,
                        'Meeting_Date': meeting_date,
                        'Allocation_Status': None,  # To be completed in Stage 2
                        'Previous_CLC_Placement': previous_clc,
                        'Previous_Other_LC': previous_other_lc,
                        'Other_LC_Name': other_lc_name,
                        'Flag_EALD': 'Yes' if flag_eald else 'No',
                        'Flag_ATSI': 'Yes' if flag_atsi else 'No',
                        'Flag_Attendance_Fulltime': 'Yes' if flag_attendance_full else 'No',
                        'Flag_Attendance_Parttime': 'Yes' if flag_attendance_part else 'No',
                        'Flag_Intervention_Custody_Order': 'Yes' if flag_custody else 'No',
                        'Flag_DCP_involvement': 'Yes' if flag_dcp else 'No',
                        'Flag_Child_in_care': 'Yes' if flag_child_care else 'No',
                        'Flag_SWD': 'Yes' if flag_swd else 'No',
                        'Flag_ASD': 'Yes' if flag_asd else 'No',
                        'Flag_Speech_and_Lang': 'Yes' if flag_speech else 'No',
                        'Referral_Year': datetime.now().year,
                        'Term': 1,  # Auto-detect later
                    }
                    
                    # Add row to dataframe
                    new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Save to Excel
                    if save_allocation_data(new_df):
                        st.success(f"✅ Draft created for **{student_name}**!")
                        st.balloons()
                        st.info("💡 Go to Tab 2 to complete this allocation on meeting day.")
                    else:
                        st.error("Failed to save to Excel")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

with tab2:
    st.subheader("📝 Complete Existing Draft")
    st.caption("Select a draft to complete with allocation decision details")
    
    # Reload fresh data
    df_fresh = load_allocation_data(STORED_FILE_PATH)
    
    # Find drafts (rows with no Allocation_Status)
    drafts = df_fresh[df_fresh['Allocation_Status'].isna()]
    
    if len(drafts) == 0:
        st.info("✅ No drafts found. Create a new draft in Tab 1.")
    else:
        draft_options = {f"{row['Student_Name']} ({row.get('Referring_School', 'No school')})": idx 
                        for idx, row in drafts.iterrows()}
        
        selected_display = st.selectbox(
            f"Select one of {len(drafts)} draft(s):",
            list(draft_options.keys())
        )
        
        draft_idx = draft_options[selected_display]
        draft = drafts.loc[draft_idx]
        
        st.success(f"✅ Loaded draft for: **{draft['Student_Name']}**")
        
        # Show draft details
        with st.expander("📋 View Draft Details", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**School:** {draft.get('Referring_School', 'N/A')}")
                st.write(f"**Year Level:** {draft.get('Year_Level', 'N/A')}")
            with col2:
                st.write(f"**Gender:** {draft.get('Gender', 'N/A')}")
                st.write(f"**Partnership:** {draft.get('Partnership_Area', 'N/A')}")
            with col3:
                st.write(f"**Referral Date:** {draft.get('Referral_Date', 'N/A')}")
        
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
                case_worker = st.text_input("Case Worker Name")
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
                    waitlist_date = st.date_input("Waitlist Date", value=date.today())
                else:
                    waitlist_date = None
            
            # BSE Section
            st.markdown("### 👤 BSE (Behaviour Support & Engagement)")
            col1, col2 = st.columns([1, 1])
            with col1:
                bse_involved = st.selectbox("BSE Involved?", ["No", "Yes"])
            with col2:
                if bse_involved == "Yes":
                    bse_name = st.text_input("BSE Staff Name *", placeholder="Enter name of BSE staff member")
                else:
                    bse_name = None
            
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
                if not outcome:
                    st.error("⚠️ Please select an outcome")
                elif bse_involved == "Yes" and not bse_name:
                    st.error("⚠️ Please enter BSE staff name if BSE is involved")
                else:
                    try:
                        # Update the row
                        df_fresh.loc[draft_idx, 'Allocated_Program'] = program
                        df_fresh.loc[draft_idx, 'Allocation_Status'] = outcome
                        df_fresh.loc[draft_idx, 'Placement_Start'] = start_after
                        df_fresh.loc[draft_idx, 'Placement_End'] = finishing_date
                        df_fresh.loc[draft_idx, 'Bespoke_Placement'] = bespoke
                        df_fresh.loc[draft_idx, 'Waitlist_Status'] = waitlist_status
                        df_fresh.loc[draft_idx, 'Waitlist_Date'] = waitlist_date
                        df_fresh.loc[draft_idx, 'Communication_to_school'] = information
                        df_fresh.loc[draft_idx, 'Action_owner'] = actioned_by
                        
                        # Add BSE columns if they don't exist
                        if 'BSE_Involved' not in df_fresh.columns:
                            df_fresh['BSE_Involved'] = None
                        if 'BSE_Name' not in df_fresh.columns:
                            df_fresh['BSE_Name'] = None
                        
                        df_fresh.loc[draft_idx, 'BSE_Involved'] = bse_involved
                        df_fresh.loc[draft_idx, 'BSE_Name'] = bse_name
                        
                        # Save to Excel
                        if save_allocation_data(df_fresh):
                            st.success(f"✅ Allocation completed for {draft['Student_Name']}!")
                            st.balloons()
                            st.info("💡 Go to Tab 3 to view all allocations.")
                        else:
                            st.error("Failed to save to Excel")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

with tab3:
    st.subheader("📊 View All Allocations")
    
    # Reload data
    df_view = load_allocation_data(STORED_FILE_PATH)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        filter_type = st.selectbox("Filter by Status", ["All", "Completed", "Drafts"])
    with col2:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    if filter_type == "Completed":
        view_df = df_view[df_view['Allocation_Status'].notna()]
    elif filter_type == "Drafts":
        view_df = df_view[df_view['Allocation_Status'].isna()]
    else:
        view_df = df_view
    
    # Display key columns
    display_cols = ['Student_Name', 'Referring_School', 'Year_Level', 'Allocation_Status', 
                    'Allocated_Program', 'Placement_Start', 'Partnership_Area']
    available_cols = [col for col in display_cols if col in view_df.columns]
    
    st.dataframe(view_df[available_cols], use_container_width=True, height=400)
    
    st.caption(f"Total: {len(view_df)} records | Completed: {len(view_df[view_df['Allocation_Status'].notna()])} | Drafts: {len(view_df[view_df['Allocation_Status'].isna()])}")

with tab4:
    st.subheader("⚙️ Settings")
    
    st.info(f"📂 **Excel File:** {EXCEL_FILE}")
    st.info(f"📊 **Data Sheet:** {DATA_SHEET}")
    
    st.markdown("### 📈 Data Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Students", len(df))
    with col2:
        completed = len(df[df['Allocation_Status'].notna()])
        st.metric("Completed", completed)
    with col3:
        drafts = len(df[df['Allocation_Status'].isna()])
        st.metric("Drafts", drafts)
    
    st.markdown("### 🔧 Maintenance")
    
    if st.button("💾 Force Save Excel File", help="Ensures all changes are saved"):
        if save_allocation_data(df):
            st.success("✅ File saved successfully!")
        else:
            st.error("❌ Error saving file")
    
    if st.checkbox("Show column names"):
        st.write("Available columns in Data_Model sheet:")
        st.code("\n".join(df.columns.tolist()))
