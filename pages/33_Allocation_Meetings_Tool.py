import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import os
import time

st.set_page_config(page_title="Allocation Meetings - CLC-LBU", page_icon="📋", layout="wide")

# Dark theme CSS
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

st.title("📋 Allocation Meetings Tool")

# File management
st.markdown("### 📁 Excel File Management")

uploaded_file = st.file_uploader("Upload your Excel file", type="xlsx")

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Data_Model")
        st.success(f"✅ File loaded successfully! {len(df)} records found.")
        st.session_state.df = df
        st.session_state.uploaded_file = uploaded_file
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        st.info("Make sure your Excel file has a sheet named 'Data_Model'")
        st.stop()
else:
    st.info("📤 Upload your Excel file to get started")
    st.stop()

if 'df' not in st.session_state:
    st.warning("Please upload a file")
    st.stop()

df = st.session_state.df

# Constants
PROGRAMS = ["Junior Primary (JP)", "Primary Years (PY)", "Senior Years (SY)"]
STAFF_NAMES = ["Candice", "Annette", "Naomi/Cheryl", "Catie", "Ben Selga", "Ben Sutton", "Jacqui", "Brenton"]
OUTCOMES = ["Allocated", "Not Allocated"]
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
YEAR_LEVELS = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
WAITLIST_STATUS_OPTIONS = ["Not Applicable", "On Waitlist", "Declined", "Site Decision", "Site Withdraw"]

# Build school map
school_map = {}
if 'Referring_School' in df.columns and 'Partnership_Area' in df.columns:
    for idx, row in df.iterrows():
        school = row.get('Referring_School')
        partnership = row.get('Partnership_Area')
        if school and pd.notna(school) and partnership and pd.notna(partnership):
            school_map[school] = partnership

ALL_SCHOOLS = sorted(list(set([s for s in school_map.keys() if pd.notna(s)])))

def get_partnership(school):
    return school_map.get(school, "")

# Tabs
tab1, tab2, tab3 = st.tabs(["➕ Create New", "📝 Complete Existing", "📊 View All"])

with tab1:
    st.subheader("➕ Create New Allocation Draft")
    
    with st.form("new_draft"):
        st.markdown("### Student Details")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            student_name = st.text_input("Name *")
        with col2:
            dob = st.date_input("Date of Birth")
        with col3:
            gender = st.selectbox("Gender", [""] + GENDER_OPTIONS)
        with col4:
            year_level = st.selectbox("Year Level *", [""] + YEAR_LEVELS)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            school = st.selectbox("Referring School *", [""] + ALL_SCHOOLS)
        with col2:
            partnership = st.text_input("Partnership", value=get_partnership(school) if school else "", disabled=True)
        with col3:
            priority = st.selectbox("Priority", [""] + ["1", "2", "3", "4", "5"])
        
        st.markdown("### Dates")
        col1, col2 = st.columns(2)
        with col1:
            referral_date = st.date_input("Referral Date *", value=date.today())
        with col2:
            meeting_week = st.text_input("Meeting Week (e.g., Week 3)")
        
        submitted = st.form_submit_button("✅ Create Draft", use_container_width=True)
        
        if submitted:
            if not student_name or not school or not year_level:
                st.error("⚠️ Please fill required fields (*)")
            else:
                try:
                    new_row = {
                        'Student_ID': f"NEW_{int(datetime.now().timestamp())}",
                        'Student_Name': student_name,
                        'DOB': dob,
                        'Gender': gender if gender else None,
                        'Year_Level': year_level,
                        'Referring_School': school,
                        'Partnership_Area': partnership,
                        'Referral_Date': referral_date,
                        'Meeting_Week': meeting_week,
                        'Allocation_Status': None,
                    }
                    
                    new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    st.session_state.df = new_df
                    
                    st.success(f"✅ Draft created for **{student_name}**!")
                    st.info("💡 Go to Tab 2 to complete this allocation")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with tab2:
    st.subheader("📝 Complete Existing Draft")
    
    df_fresh = st.session_state.df
    drafts = df_fresh[df_fresh['Allocation_Status'].isna()]
    
    if len(drafts) == 0:
        st.info("✅ No drafts to complete")
    else:
        draft_options = {f"{row['Student_Name']} ({row.get('Referring_School', '?')})": idx 
                        for idx, row in drafts.iterrows()}
        
        selected = st.selectbox("Select draft:", list(draft_options.keys()))
        draft_idx = draft_options[selected]
        draft = drafts.loc[draft_idx]
        
        st.success(f"✅ **{draft['Student_Name']}**")
        
        with st.form("complete_draft"):
            st.markdown("### Allocation Details")
            col1, col2 = st.columns(2)
            with col1:
                program = st.selectbox("Program *", PROGRAMS)
            with col2:
                outcome = st.selectbox("Outcome *", OUTCOMES)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                case_worker = st.text_input("Case Worker")
            with col2:
                start_date = st.date_input("Start After")
            with col3:
                end_date = st.date_input("Finishing Date")
            
            st.markdown("### 👤 BSE (Behaviour Support & Engagement)")
            col1, col2 = st.columns(2)
            with col1:
                bse_involved = st.selectbox("BSE Involved?", ["No", "Yes"])
            with col2:
                if bse_involved == "Yes":
                    bse_name = st.text_input("BSE Staff Name *")
                else:
                    bse_name = None
            
            st.markdown("### Communication")
            info = st.text_area("Information for school")
            actioned_by = st.selectbox("Actioned by", [""] + STAFF_NAMES)
            
            submitted = st.form_submit_button("✅ Save", use_container_width=True)
            
            if submitted:
                if not outcome:
                    st.error("⚠️ Select outcome")
                elif bse_involved == "Yes" and not bse_name:
                    st.error("⚠️ Enter BSE name")
                else:
                    try:
                        df_fresh.loc[draft_idx, 'Allocated_Program'] = program
                        df_fresh.loc[draft_idx, 'Allocation_Status'] = outcome
                        df_fresh.loc[draft_idx, 'Placement_Start'] = start_date
                        df_fresh.loc[draft_idx, 'Placement_End'] = end_date
                        df_fresh.loc[draft_idx, 'Communication_to_school'] = info
                        df_fresh.loc[draft_idx, 'Action_owner'] = actioned_by
                        
                        if 'BSE_Involved' not in df_fresh.columns:
                            df_fresh['BSE_Involved'] = None
                        if 'BSE_Name' not in df_fresh.columns:
                            df_fresh['BSE_Name'] = None
                        
                        df_fresh.loc[draft_idx, 'BSE_Involved'] = bse_involved
                        df_fresh.loc[draft_idx, 'BSE_Name'] = bse_name
                        
                        st.session_state.df = df_fresh
                        st.success(f"✅ Saved!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

with tab3:
    st.subheader("📊 View All")
    
    df_view = st.session_state.df
    
    col1, col2 = st.columns([3, 1])
    with col1:
        filter_type = st.selectbox("Filter", ["All", "Completed", "Drafts"])
    with col2:
        if st.button("Refresh"):
            st.rerun()
    
    if filter_type == "Completed":
        view_df = df_view[df_view['Allocation_Status'].notna()]
    elif filter_type == "Drafts":
        view_df = df_view[df_view['Allocation_Status'].isna()]
    else:
        view_df = df_view
    
    cols_to_show = ['Student_Name', 'Referring_School', 'Year_Level', 'Allocation_Status', 'Allocated_Program']
    cols_to_show = [c for c in cols_to_show if c in view_df.columns]
    
    st.dataframe(view_df[cols_to_show], use_container_width=True, height=400)
    st.caption(f"Total: {len(view_df)} | Completed: {len(view_df[view_df['Allocation_Status'].notna()])} | Drafts: {len(view_df[view_df['Allocation_Status'].isna()])}")

st.markdown("---")
st.markdown("### 📥 Download Updated File")

try:
    buffer = pd.ExcelWriter("temp.xlsx", engine="openpyxl")
    st.session_state.df.to_excel(buffer, sheet_name="Data_Model", index=False)
    buffer.close()
    
    with open("temp.xlsx", "rb") as f:
        file_data = f.read()
    
    st.download_button(
        label="📥 Download Excel",
        data=file_data,
        file_name=f"CLC_Allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
except Exception as e:
    st.error(f"Download error: {str(e)}")
