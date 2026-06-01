import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid

st.set_page_config(page_title="Allocation Meetings Tool", page_icon="📋", layout="wide")

# Dark theme
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] { background: #0F1729 !important; }
    .main > div { padding: 1.5rem 2rem; max-width: 1200px; margin: 0 auto; }
    h1, h2, h3 { color: #FFFFFF !important; }
    p, div, label { color: #8B9DC3 !important; }
    .stButton>button { 
        background: linear-gradient(135deg, #1A2942 0%, #243556 100%) !important; 
        border: 1.5px solid #2D3F5F !important; 
        color: #FFFFFF !important; 
        font-weight: 700 !important; 
    }
    .stButton>button:hover { border-color: #00D9FF !important; box-shadow: 0 8px 32px rgba(0, 217, 255, 0.4) !important; }
</style>
""", unsafe_allow_html=True)

st.title("📋 Allocation Meetings Tool")
st.markdown("Enter allocation information and export to paste into your main Excel file")

if 'allocations' not in st.session_state:
    st.session_state.allocations = []

# Constants
PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
STAFF_NAMES = ["Candice", "Annette", "Naomi/Cheryl", "Catie", "Ben Selga", "Ben Sutton", "Jacqui", "Brenton"]
OUTCOMES = ["Allocated", "Not Allocated"]
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

# All partnerships from your Excel
PARTNERSHIPS = [
    "Adelaide Prospect", "Anangu Lands", "Barossa Valley", "Beach Road",
    "Berri & Barmera", "Blue Lake", "Campbell", "Central East", "Central Eyre 1", "Central Eyre 2",
    "Coorong & Mallee", "Elizabeth", "Far North", "Far West", "Fleurieu", "Flinders",
    "Golden Way", "Goyder & Light", "Greater Gawler", "Greenhill South", "Heysen",
    "Holdfast", "Hollywood Lakes and Gardens", "Inner West", "Kangaroo Island",
    "Le Fevre Peninsula", "Lower Mid North", "Marion Coastal", "Marion Inland",
    "Mid North Clare", "Mitcham Hills", "Mitcham Plains", "Modbury", "Montague",
    "Morialta", "Mount Lofty", "Murraylands", "Northern Yorke", "Orion",
    "Panalatinga", "Peachey", "Pirie", "Port Augusta - Quorn", "Port Lincoln",
    "Renmark Loxton", "River Hub", "Salisbury", "Sea & Vines", "South East Coast & Vines",
    "South Valley", "Southern Yorke", "Tatiara", "Tea Tree Gully", "Torrens",
    "Torrens Valley", "Uleybury", "Upper Mid North", "Waikerie", "West Torrens",
    "Western Adelaide Shores", "Whyalla", "Wrattonbully"
]

def get_term_from_date(d):
    """Calculate term from referral date"""
    if not d:
        return None
    month = d.month
    if month in [1, 2, 3]:
        return 1
    elif month in [4, 5, 6]:
        return 2
    elif month in [7, 8, 9]:
        return 3
    else:
        return 4

# Form
st.markdown("### ➕ Enter New Allocation")

with st.form("allocation_form", border=False):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        student_name = st.text_input("Student Name *")
    with col2:
        dob = st.date_input("Date of Birth")
    with col3:
        gender = st.selectbox("Gender", [""] + GENDER_OPTIONS)
    with col4:
        year_level = st.selectbox("Year Level *", [""] + YEAR_LEVELS)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        referring_school = st.text_input("Referring School *")
    with col2:
        partnership_area = st.selectbox("Partnership Area *", [""] + PARTNERSHIPS)
    with col3:
        referral_date = st.date_input("Referral Date *", value=date.today())
    
    col1, col2 = st.columns(2)
    with col1:
        meeting_week = st.text_input("Meeting Week (e.g., Week 3)")
    with col2:
        meeting_date = st.date_input("Meeting Date", value=None)
    
    st.markdown("### 📋 Allocation Decision")
    col1, col2 = st.columns(2)
    with col1:
        allocated_program = st.selectbox("Allocated Program", [""] + PROGRAMS)
    with col2:
        allocation_status = st.selectbox("Allocation Status", [""] + OUTCOMES)
    
    st.markdown("### 📅 Placement Dates")
    col1, col2 = st.columns(2)
    with col1:
        placement_start = st.date_input("Placement Start")
    with col2:
        placement_end = st.date_input("Placement End")
    
    st.markdown("### 👤 BSE (Behaviour Support & Engagement)")
    col1, col2 = st.columns(2)
    with col1:
        bse_involved = st.selectbox("BSE Involved?", ["No", "Yes"])
    with col2:
        bse_name = st.text_input("BSE Staff Name") if bse_involved == "Yes" else None
    
    st.markdown("### 📧 Communication & Action")
    communication_to_school = st.text_area("Communication to School", height=60)
    action_owner = st.selectbox("Action Owner", [""] + STAFF_NAMES)
    
    submitted = st.form_submit_button("✅ Add to Export", use_container_width=True)
    
    if submitted:
        if not student_name or not referring_school or not year_level or not partnership_area:
            st.error("⚠️ Please fill required fields (*)")
        else:
            # Generate IDs
            student_id = f"{int(datetime.now().timestamp() % 100000000):09d}A"
            referral_id = f"{student_id}-01"
            
            # Create record with ALL Data_Model columns
            record = {
                'Student_ID': student_id,
                'Previous_Referrals': 0.0,
                'Student_Name': student_name,
                'DOB': dob,
                'Gender': gender if gender else None,
                'Year_Level': year_level,
                'Referring_School': referring_school,
                'Referral_Date': referral_date,
                'Meeting_Date': meeting_date,
                'Meeting_Week': meeting_week if meeting_week else None,
                'Previously_Referred': 'No',
                'Allocation_Status': allocation_status if allocation_status else None,
                'Allocated_Program': allocated_program if allocated_program else None,
                'Placement_Start': placement_start,
                'Partnership_Area': partnership_area,
                'Previous_CLC_Placement': 'No',
                'Previous_Other_LC': 'No',
                'Other_LC_Name': None,
                'Total_Previous_Placements': 0.0,
                'Placement_History_Notes': None,
                'Flag_EALD': 'No',
                'Flag_ATSI': 'No',
                'Flag_Attendance_Fulltime': 'No',
                'Flag_Attendance_Parttime': 'No',
                'Flag_Intervention_Custody_Order': 'No',
                'Flag_DCP_involvement': 'No',
                'Flag_Child_in_care': 'No',
                'Flag_IESP_Funding_yes': None,
                'Flag_IESP_Funding_no': None,
                'Flag_Category_1': None,
                'Flag_Category_2': None,
                'Flag_Category_3': None,
                'Flag_Category_4': None,
                'Flag_Category_5': None,
                'Flag_Category_6': None,
                'Flag_Category_7': None,
                'Flag_Category_8': None,
                'Flag_Category_9': None,
                'Flag_9plusRAAP': None,
                'Flag_SWD': 'No',
                'Flag_Speech_and_Lang': 'No',
                'Flag_ASD': 'No',
                'Flag_Intellectual': 'No',
                'Flag_Learning_Difficulty': 'No',
                'Flag_Sensory_Processing': 'No',
                'Flag_ADHD': 'No',
                'Flag_ODD': 'No',
                'Flag_PDA': 'No',
                'Flag_Medication': 'No',
                'Flag_Medical_condition': 'No',
                'Medical_Condition_Details': None,
                'Medication_Details': None,
                'Bespoke_Placement': 'No',
                'Waitlist_Status': None,
                'Waitlist_Date': None,
                'Allocated_From_Waitlist': None,
                'Extension': None,
                'Extension_Date': None,
                'Exit_Reason': None,
                'Transition_Plan': None,
                'Notes': None,
                'Placement_End': placement_end,
                'Current_Status': 'Active',
                'Behaviour_Flag': None,
                'Exclusion_End_Date': None,
                'Proposed_Extension_Finish_Date': None,
                'Extension_Weeks': None,
                'Communication_to_school': communication_to_school if communication_to_school else None,
                'Action_owner': action_owner if action_owner else None,
                'Actual_Finish_Date': None,
                'Extended_Placement': None,
                'Referral_Year': float(referral_date.year),
                'Term': float(get_term_from_date(referral_date)),
                'Extension_Status': None,
                'Referral_Occurrence': 1.0,
                'Referral_ID': referral_id,
                'BSE_Involved': bse_involved,
                'BSE_Name': bse_name,
            }
            
            st.session_state.allocations.append(record)
            st.success(f"✅ **{student_name}** added!")

# Display & Export
st.markdown("---")
st.markdown("### 📊 Records Ready for Export")

if len(st.session_state.allocations) == 0:
    st.info("No allocations yet")
else:
    df_display = pd.DataFrame(st.session_state.allocations)
    
    # Show key columns
    key_cols = ['Student_Name', 'Year_Level', 'Referring_School', 'Partnership_Area', 
                'Allocated_Program', 'Allocation_Status', 'BSE_Involved', 'BSE_Name']
    key_cols = [c for c in key_cols if c in df_display.columns]
    
    st.dataframe(df_display[key_cols], use_container_width=True, height=300)
    
    st.markdown("---")
    st.markdown("### 📥 Export Instructions")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**{len(st.session_state.allocations)} allocation(s) ready**")
        st.caption("✅ Download → Open in Excel → Copy all rows → Paste into Data_Model sheet of main file")
    
    with col2:
        # Export all 76 columns in correct order
        column_order = [
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
            'Extended_Placement', 'Referral_Year', 'Term', 'Extension_Status', 'Referral_Occurrence',
            'Referral_ID', 'BSE_Involved', 'BSE_Name'
        ]
        
        df_export = pd.DataFrame(st.session_state.allocations)[column_order]
        
        st.download_button(
            label="📥 Download Excel",
            data=df_export.to_excel(index=False, engine='openpyxl'),
            file_name=f"Allocations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("---")
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.allocations = []
        st.rerun()

st.caption("💡 Data is exported with ALL 76 columns from Data_Model - paste directly into your main file!")
