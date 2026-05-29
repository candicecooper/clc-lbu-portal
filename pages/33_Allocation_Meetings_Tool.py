import streamlit as st
import pandas as pd
from datetime import datetime, date
from io import BytesIO

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
st.markdown("Enter allocation information below and export to Excel for your main file")

# Initialize session state for storing records
if 'allocations' not in st.session_state:
    st.session_state.allocations = []

# Constants
PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
STAFF_NAMES = ["Candice", "Annette", "Naomi/Cheryl", "Catie", "Ben Selga", "Ben Sutton", "Jacqui", "Brenton"]
OUTCOMES = ["Allocated", "Not Allocated"]
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

# These are your partnerships from the Excel file
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

# Form to enter allocation
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
        partnership = st.selectbox("Partnership Area *", [""] + PARTNERSHIPS)
    with col3:
        referral_date = st.date_input("Referral Date *", value=date.today())
    
    col1, col2 = st.columns(2)
    
    with col1:
        meeting_week = st.text_input("Meeting Week (e.g., Week 3, Term 2)")
    with col2:
        program = st.selectbox("Allocated Program", [""] + PROGRAMS)
    
    col1, col2 = st.columns(2)
    
    with col1:
        outcome = st.selectbox("Outcome", [""] + OUTCOMES)
    with col2:
        pass  # Spacer
    
    st.markdown("### 📅 Dates")
    col1, col2 = st.columns(2)
    
    with col1:
        placement_start = st.date_input("Placement Start Date")
    with col2:
        placement_end = st.date_input("Placement End Date")
    
    st.markdown("### 👤 BSE (Behaviour Support & Engagement)")
    col1, col2 = st.columns(2)
    
    with col1:
        bse_involved = st.selectbox("BSE Involved?", ["No", "Yes"])
    with col2:
        if bse_involved == "Yes":
            bse_name = st.text_input("BSE Staff Name")
        else:
            bse_name = None
    
    st.markdown("### 📧 Communication & Action")
    communication = st.text_area("Communication to School", height=80)
    action_owner = st.selectbox("Action Owner", [""] + STAFF_NAMES)
    
    # Submit button
    submitted = st.form_submit_button("✅ Add to Export List", use_container_width=True)
    
    if submitted:
        if not student_name or not referring_school or not year_level or not partnership:
            st.error("⚠️ Please fill all required fields (*)")
        else:
            # Create record with exact column names
            record = {
                'Student_Name': student_name,
                'DOB': dob,
                'Gender': gender if gender else None,
                'Year_Level': year_level,
                'Referring_School': referring_school,
                'Partnership_Area': partnership,
                'Referral_Date': referral_date,
                'Meeting_Week': meeting_week if meeting_week else None,
                'Allocated_Program': program if program else None,
                'Allocation_Status': outcome if outcome else None,
                'Placement_Start': placement_start,
                'Placement_End': placement_end,
                'BSE_Involved': bse_involved,
                'BSE_Name': bse_name,
                'Communication_to_school': communication if communication else None,
                'Action_owner': action_owner if action_owner else None,
            }
            
            st.session_state.allocations.append(record)
            st.success(f"✅ Added **{student_name}** to export list")
            st.info(f"📊 Total allocations ready to export: {len(st.session_state.allocations)}")

# Display current allocations
st.markdown("---")
st.markdown("### 📊 Allocations Ready for Export")

if len(st.session_state.allocations) == 0:
    st.info("No allocations yet. Fill the form above and click 'Add to Export List'")
else:
    # Display as table
    df_export = pd.DataFrame(st.session_state.allocations)
    st.dataframe(df_export, use_container_width=True, height=300)
    
    st.markdown("---")
    st.markdown("### 📥 Export to Excel")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**{len(st.session_state.allocations)} allocation(s) ready to download**")
        st.caption("Copy and paste this data into your main CLC_Allocation_Dashboard Excel file")
    
    with col2:
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name='Allocations_Export', index=False)
        
        output.seek(0)
        
        st.download_button(
            label="📥 Download Excel",
            data=output.getvalue(),
            file_name=f"Allocations_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("---")
    
    if st.button("🗑️ Clear All & Start Over", use_container_width=True):
        st.session_state.allocations = []
        st.rerun()

st.markdown("---")
st.caption("💡 **How to use:** Fill the form → Click 'Add to Export List' → Download Excel → Paste into your main file")
