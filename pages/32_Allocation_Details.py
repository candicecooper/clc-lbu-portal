import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Try to import auth - handle different possible function names
try:
    import auth
    # Try common authentication function names
    if hasattr(auth, 'check_authentication'):
        auth.check_authentication()
    elif hasattr(auth, 'check_password'):
        if not auth.check_password():
            st.stop()
    elif hasattr(auth, 'authenticate'):
        auth.authenticate()
    elif hasattr(auth, 'require_authentication'):
        auth.require_authentication()
except ImportError:
    st.warning("⚠️ Auth module not found - continuing without authentication")
except Exception as e:
    st.warning(f"⚠️ Auth check failed: {e}")

# Import database
try:
    from database import get_supabase_client
    supabase = get_supabase_client()
except ImportError:
    st.error("⚠️ Database module not available")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Allocation Details | CLC-LBU Portal", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1A7A6E 0%, #4A9B8E 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
    }
    .main-header p {
        color: #D6F0EB;
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1A7A6E;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card h3 {
        color: #1A7A6E;
        margin: 0 0 0.5rem 0;
        font-size: 1.8rem;
    }
    .metric-card p {
        color: #666;
        margin: 0;
        font-size: 0.9rem;
    }
    .stButton>button {
        background-color: #1A7A6E;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #4A9B8E;
    }
    .warning-box {
        background-color: #FEF3D9;
        border-left: 4px solid #C8760A;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #D6F0EB;
        border-left: 4px solid #1A7A6E;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 Allocation Details & Tracking</h1>
    <p>Student referral, allocation, and placement history management</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Table name
TABLE_NAME = "allocation_tracker"

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def fetch_all_records():
    """Fetch all allocation records from Supabase"""
    try:
        response = supabase.table(TABLE_NAME).select("*").order("referral_date", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching records: {e}")
        return pd.DataFrame()

def insert_record(data):
    """Insert new allocation record"""
    try:
        response = supabase.table(TABLE_NAME).insert(data).execute()
        return True, "Record added successfully"
    except Exception as e:
        return False, f"Error: {e}"

def update_record(record_id, data):
    """Update existing allocation record"""
    try:
        response = supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True, "Record updated successfully"
    except Exception as e:
        return False, f"Error: {e}"

def delete_record(record_id):
    """Delete allocation record"""
    try:
        response = supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        return True, "Record deleted successfully"
    except Exception as e:
        return False, f"Error: {e}"

# ══════════════════════════════════════════════════════════════════════════════
# MODE TOGGLE
# ══════════════════════════════════════════════════════════════════════════════
col1, col2, col3 = st.columns([2, 2, 3])

with col1:
    mode = st.radio("", ["➕ Add/Edit Record", "📊 View Database", "📥 Dashboard Export"], horizontal=False, label_visibility="collapsed")

with col3:
    st.markdown("""
    <div class="warning-box">
    <strong>💡 Quick Guide</strong><br>
    • <strong>Add/Edit</strong>: Enter new student allocation details<br>
    • <strong>View Database</strong>: See all records with filtering<br>
    • <strong>Dashboard Export</strong>: Download visual Excel dashboard
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MODE 1: ADD/EDIT RECORD
# ══════════════════════════════════════════════════════════════════════════════
if mode == "➕ Add/Edit Record":
    st.subheader("📝 Student Allocation Entry")
    
    # Check if editing existing record
    df = fetch_all_records()
    edit_mode = False
    selected_record = None
    
    if not df.empty:
        with st.expander("🔍 Edit Existing Record"):
            student_list = df["student_name"].tolist() if "student_name" in df.columns else []
            if student_list:
                selected_student = st.selectbox("Select student to edit:", [""] + student_list)
                if selected_student:
                    selected_record = df[df["student_name"] == selected_student].iloc[0].to_dict()
                    edit_mode = True
                    st.info(f"Editing record for **{selected_student}**")
    
    # Form
    with st.form("allocation_form", clear_on_submit=not edit_mode):
        st.markdown("#### Basic Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            student_name = st.text_input("Student Name *", 
                value=selected_record.get("student_name", "") if edit_mode else "",
                placeholder="First Last")
        
        with col2:
            dob = st.date_input("Date of Birth", 
                value=pd.to_datetime(selected_record.get("dob")).date() if edit_mode and selected_record.get("dob") else None)
        
        with col3:
            gender = st.selectbox("Gender", 
                ["", "Male", "Female", "Other", "Prefer not to say"],
                index=["", "Male", "Female", "Other", "Prefer not to say"].index(selected_record.get("gender", "")) if edit_mode and selected_record.get("gender") else 0)
        
        st.markdown("#### Referral & Allocation")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            referring_school = st.text_input("Referring School *",
                value=selected_record.get("referring_school", "") if edit_mode else "",
                placeholder="e.g., Henley High School")
        
        with col2:
            referral_date = st.date_input("Referral Date *",
                value=pd.to_datetime(selected_record.get("referral_date")).date() if edit_mode and selected_record.get("referral_date") else date.today())
        
        with col3:
            allocation_status = st.selectbox("Allocation Status *",
                ["Pending", "Allocated", "Waitlist", "Declined", "Withdrawn"],
                index=["Pending", "Allocated", "Waitlist", "Declined", "Withdrawn"].index(selected_record.get("allocation_status", "Pending")) if edit_mode else 0)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            allocated_program = st.selectbox("Allocated Program",
                ["", "Primary (R-6)", "Middle (7-9)", "Secondary (10-12)", "Transition"],
                index=["", "Primary (R-6)", "Middle (7-9)", "Secondary (10-12)", "Transition"].index(selected_record.get("allocated_program", "")) if edit_mode and selected_record.get("allocated_program") else 0)
        
        with col2:
            placement_start = st.date_input("Placement Start",
                value=pd.to_datetime(selected_record.get("placement_start")).date() if edit_mode and selected_record.get("placement_start") else None)
        
        with col3:
            placement_end = st.date_input("Placement End",
                value=pd.to_datetime(selected_record.get("placement_end")).date() if edit_mode and selected_record.get("placement_end") else None)
        
        with col4:
            partnership_area = st.selectbox("Partnership Area",
                ["", "West Torrens", "Felixstow", "Western Adelaide Shores", "Inner Western", "Le Fevre", "Port Adelaide", "Other"],
                index=["", "West Torrens", "Felixstow", "Western Adelaide Shores", "Inner Western", "Le Fevre", "Port Adelaide", "Other"].index(selected_record.get("partnership_area", "")) if edit_mode and selected_record.get("partnership_area") else 0)
        
        st.markdown("#### Placement History")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            prev_clc = st.selectbox("Previous CLC Placement?",
                ["No", "Yes"],
                index=["No", "Yes"].index(selected_record.get("previous_clc_placement", "No")) if edit_mode else 0)
        
        with col2:
            prev_other_lc = st.selectbox("Previous Other LC?",
                ["No", "Yes"],
                index=["No", "Yes"].index(selected_record.get("previous_other_lc", "No")) if edit_mode else 0)
        
        with col3:
            other_lc_name = st.text_input("Other LC Name",
                value=selected_record.get("other_lc_name", "") if edit_mode else "",
                placeholder="e.g., BEC, Portside")
        
        with col4:
            total_prev_placements = st.number_input("Total Previous Placements", 
                min_value=0, max_value=10, step=1,
                value=int(selected_record.get("total_previous_placements", 0)) if edit_mode else 0)
        
        placement_history_notes = st.text_area("Placement History Notes",
            value=selected_record.get("placement_history_notes", "") if edit_mode else "",
            placeholder="e.g., 2023 CLC placement for 8 weeks, transitioned successfully to mainstream")
        
        st.markdown("#### Priority & Flags")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            priority_level = st.selectbox("Priority Level",
                ["", "1", "2", "3", "4", "5"],
                index=["", "1", "2", "3", "4", "5"].index(str(selected_record.get("priority_level", ""))) if edit_mode and selected_record.get("priority_level") else 0)
        
        st.markdown("**Priority Flags:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            flag_asd = st.checkbox("ASD", value=selected_record.get("flag_asd", False) if edit_mode else False)
            flag_adhd = st.checkbox("ADHD", value=selected_record.get("flag_adhd", False) if edit_mode else False)
        
        with col2:
            flag_mental_health = st.checkbox("Mental Health", value=selected_record.get("flag_mental_health", False) if edit_mode else False)
            flag_odd_cd = st.checkbox("ODD/CD", value=selected_record.get("flag_odd_cd", False) if edit_mode else False)
        
        with col3:
            flag_care_cps = st.checkbox("Care/CPS", value=selected_record.get("flag_care_cps", False) if edit_mode else False)
            flag_aboriginal = st.checkbox("Aboriginal", value=selected_record.get("flag_aboriginal", False) if edit_mode else False)
        
        with col4:
            flag_eald = st.checkbox("EALD", value=selected_record.get("flag_eald", False) if edit_mode else False)
            flag_other = st.checkbox("Other", value=selected_record.get("flag_other", False) if edit_mode else False)
        
        st.markdown("#### Additional Information")
        col1, col2 = st.columns(2)
        
        with col1:
            current_status = st.selectbox("Current Status",
                ["", "Active", "Completed", "Exited Early", "Transferred", "Extended"],
                index=["", "Active", "Completed", "Exited Early", "Transferred", "Extended"].index(selected_record.get("current_status", "")) if edit_mode and selected_record.get("current_status") else 0)
        
        with col2:
            exit_reason = st.text_input("Exit Reason",
                value=selected_record.get("exit_reason", "") if edit_mode else "",
                placeholder="e.g., Successful transition to mainstream")
        
        transition_plan = st.text_area("Transition Plan",
            value=selected_record.get("transition_plan", "") if edit_mode else "",
            placeholder="Brief notes on transition planning")
        
        notes = st.text_area("Additional Notes",
            value=selected_record.get("notes", "") if edit_mode else "",
            placeholder="Any other relevant information")
        
        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            submit = st.form_submit_button("💾 Save Record", use_container_width=True)
        
        with col2:
            if edit_mode:
                delete = st.form_submit_button("🗑️ Delete", use_container_width=True, type="secondary")
        
        if submit:
            if not student_name or not referring_school:
                st.error("⚠️ Student Name and Referring School are required")
            else:
                record_data = {
                    "student_name": student_name,
                    "dob": dob.isoformat() if dob else None,
                    "gender": gender if gender else None,
                    "referring_school": referring_school,
                    "referral_date": referral_date.isoformat(),
                    "allocation_status": allocation_status,
                    "allocated_program": allocated_program if allocated_program else None,
                    "placement_start": placement_start.isoformat() if placement_start else None,
                    "placement_end": placement_end.isoformat() if placement_end else None,
                    "partnership_area": partnership_area if partnership_area else None,
                    "previous_clc_placement": prev_clc,
                    "previous_other_lc": prev_other_lc,
                    "other_lc_name": other_lc_name if other_lc_name else None,
                    "total_previous_placements": total_prev_placements,
                    "placement_history_notes": placement_history_notes if placement_history_notes else None,
                    "priority_level": priority_level if priority_level else None,
                    "flag_asd": flag_asd,
                    "flag_adhd": flag_adhd,
                    "flag_mental_health": flag_mental_health,
                    "flag_odd_cd": flag_odd_cd,
                    "flag_care_cps": flag_care_cps,
                    "flag_aboriginal": flag_aboriginal,
                    "flag_eald": flag_eald,
                    "flag_other": flag_other,
                    "current_status": current_status if current_status else None,
                    "exit_reason": exit_reason if exit_reason else None,
                    "transition_plan": transition_plan if transition_plan else None,
                    "notes": notes if notes else None,
                    "updated_at": datetime.now().isoformat(),
                }
                
                if edit_mode and selected_record:
                    success, message = update_record(selected_record["id"], record_data)
                else:
                    record_data["created_at"] = datetime.now().isoformat()
                    success, message = insert_record(record_data)
                
                if success:
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        if edit_mode and 'delete' in locals() and delete:
            if st.session_state.get("confirm_delete"):
                success, message = delete_record(selected_record["id"])
                if success:
                    st.success(f"✅ {message}")
                    st.session_state["confirm_delete"] = False
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.session_state["confirm_delete"] = True
                st.warning("⚠️ Click Delete again to confirm deletion")

# ══════════════════════════════════════════════════════════════════════════════
# MODE 2: VIEW DATABASE
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "📊 View Database":
    st.subheader("📊 Allocation Database")
    
    df = fetch_all_records()
    
    if df.empty:
        st.info("📭 No allocation records found. Use Add/Edit mode to create your first record.")
    else:
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{len(df)}</h3>
                <p>Total Referrals</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            allocated = len(df[df["allocation_status"] == "Allocated"]) if "allocation_status" in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <h3>{allocated}</h3>
                <p>Allocated</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            waitlist = len(df[df["allocation_status"] == "Waitlist"]) if "allocation_status" in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <h3>{waitlist}</h3>
                <p>On Waitlist</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            re_referrals = len(df[(df["previous_clc_placement"] == "Yes") | (df["previous_other_lc"] == "Yes")]) if "previous_clc_placement" in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <h3>{re_referrals}</h3>
                <p>Re-referrals</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            partnerships = len(df[df["partnership_area"].notna()]) if "partnership_area" in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <h3>{partnerships}</h3>
                <p>Partnerships</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Filters
        with st.expander("🔍 Filters", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status_filter = st.multiselect("Allocation Status", 
                    df["allocation_status"].unique().tolist() if "allocation_status" in df.columns else [])
            
            with col2:
                program_filter = st.multiselect("Program",
                    df["allocated_program"].dropna().unique().tolist() if "allocated_program" in df.columns else [])
            
            with col3:
                partnership_filter = st.multiselect("Partnership",
                    df["partnership_area"].dropna().unique().tolist() if "partnership_area" in df.columns else [])
            
            with col4:
                priority_filter = st.multiselect("Priority Level",
                    df["priority_level"].dropna().unique().tolist() if "priority_level" in df.columns else [])
        
        # Apply filters
        filtered_df = df.copy()
        if status_filter:
            filtered_df = filtered_df[filtered_df["allocation_status"].isin(status_filter)]
        if program_filter:
            filtered_df = filtered_df[filtered_df["allocated_program"].isin(program_filter)]
        if partnership_filter:
            filtered_df = filtered_df[filtered_df["partnership_area"].isin(partnership_filter)]
        if priority_filter:
            filtered_df = filtered_df[filtered_df["priority_level"].isin(priority_filter)]
        
        st.info(f"Showing **{len(filtered_df)}** of **{len(df)}** records")
        
        # Display table
        display_cols = [
            "student_name", "referring_school", "referral_date", "allocation_status",
            "allocated_program", "partnership_area", "previous_clc_placement",
            "priority_level", "current_status"
        ]
        
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_cols],
            use_container_width=True,
            hide_index=True
        )
        
        # Export options
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        
        with col1:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Export to CSV",
                csv,
                f"allocation_data_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )

# ══════════════════════════════════════════════════════════════════════════════
# MODE 3: DASHBOARD EXPORT
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "📥 Dashboard Export":
    st.subheader("📊 Visual Dashboard Export")
    
    st.markdown("""
    <div class="success-box">
    <strong>📊 Executive Dashboard Available</strong><br>
    Download the visual allocation dashboard Excel file with charts and graphs for presentations, 
    leadership meetings, and end-of-term reporting.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Dashboard Includes:")
        st.markdown("""
        - **6 KPI tiles** (totals, allocations, re-referrals)
        - **Program capacity chart** (bar graph)
        - **Partnership distribution** (pie chart)
        - **Priority profile** (bar graph)
        - **Placement history** (doughnut chart)
        - **Key insights section**
        """)
    
    with col2:
        st.info("""
        **💡 How to Use:**
        
        1. Download the Excel dashboard template
        2. Open in Excel or Google Sheets
        3. Go to the **Data_Model** sheet
        4. Paste your allocation data or manually enter records
        5. Return to the **Dashboard** sheet to see live visual updates
        
        All charts update automatically based on your data.
        """)
    
    st.markdown("---")
    
    st.warning("📥 Download link will be added here - upload the Excel dashboard to your OneDrive and add the link")
    
    st.markdown("---")
    
    st.markdown("### 🔄 Sync Data to Dashboard")
    
    df = fetch_all_records()
    if not df.empty:
        st.info(f"✅ You have **{len(df)} records** in the database ready to export to Excel")
        
        if st.button("📤 Export Current Database to Excel Format"):
            # Export current database to Excel format matching the dashboard structure
            excel_export = df.copy()
            
            # Rename columns to match Excel dashboard
            column_mapping = {
                "student_name": "Student_Name",
                "dob": "DOB",
                "gender": "Gender",
                "referring_school": "Referring_School",
                "referral_date": "Referral_Date",
                "allocation_status": "Allocation_Status",
                "allocated_program": "Allocated_Program",
                "placement_start": "Placement_Start",
                "placement_end": "Placement_End",
                "partnership_area": "Partnership_Area",
                "previous_clc_placement": "Previous_CLC_Placement",
                "previous_other_lc": "Previous_Other_LC",
                "other_lc_name": "Other_LC_Name",
                "total_previous_placements": "Total_Previous_Placements",
                "placement_history_notes": "Placement_History_Notes",
                "priority_level": "Priority_Level",
                "current_status": "Current_Status",
                "exit_reason": "Exit_Reason",
                "transition_plan": "Transition_Plan",
                "notes": "Notes"
            }
            
            excel_export = excel_export.rename(columns=column_mapping)
            
            # Convert flags to Yes/No
            flag_cols = ["flag_asd", "flag_adhd", "flag_mental_health", "flag_odd_cd", 
                        "flag_care_cps", "flag_aboriginal", "flag_eald", "flag_other"]
            for col in flag_cols:
                if col in excel_export.columns:
                    excel_export[col] = excel_export[col].map({True: "Yes", False: "No", None: "No"})
            
            csv_export = excel_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Data Export (CSV for Excel)",
                csv_export,
                f"allocation_data_export_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                help="Import this CSV into the Data_Model sheet of your dashboard"
            )
            
            st.success("✅ Export ready! Import this file into the Data_Model sheet of your Excel dashboard.")
    else:
        st.warning("📭 No records in database to export")

# Footer
st.markdown("---")
st.caption("📊 Allocation Details & Tracking | Cowandilla Learning Centre LBU")
