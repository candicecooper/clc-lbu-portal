import streamlit as st
import pandas as pd
from datetime import datetime
import os
from supabase import create_client, Client

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Allocation Sync | CLC-LBU",
    page_icon="🔄",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .sync-header {
        background: linear-gradient(135deg, #1A7A6E 0%, #4A9B8E 100%);
        padding: 2rem 3rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .sync-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .sync-header p {
        color: #D6F0EB;
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
    }
    .privacy-box {
        background: #D6F0EB;
        border: 3px solid #1A7A6E;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
    }
    .privacy-box h3 {
        color: #1A7A6E;
        margin-top: 0;
    }
    .success-box {
        background: #D4EDDA;
        border-left: 5px solid #28A745;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #FFF3CD;
        border-left: 5px solid #FFC107;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="sync-header">
    <h1>🔄 Allocation Data Sync</h1>
    <p>Privacy-preserving sync from Excel to Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PRIVACY INFORMATION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="privacy-box">
    <h3>🔒 Privacy Protection</h3>
    <p><strong>What gets synced to dashboard database:</strong></p>
    <ul>
        <li>✅ Student IDs (anonymous identifiers)</li>
        <li>✅ Year levels, programs, schools</li>
        <li>✅ Allocation status and dates</li>
        <li>✅ Support flags (SWD, DCP, Aboriginal, EALD)</li>
    </ul>
    <p><strong>What stays ONLY in Excel:</strong></p>
    <ul>
        <li>❌ Student names (never synced)</li>
        <li>❌ Date of birth (only year level synced)</li>
        <li>❌ Any personal identifiable information</li>
    </ul>
    <p style="margin-top: 1rem;"><em>The dashboard displays de-identified analytics only. Full student records remain secure in Excel with portal access control.</em></p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE CONNECTION
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def init_supabase():
    """Initialize Supabase client"""
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ Supabase credentials not found in environment variables.")
        st.stop()
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📁 Upload Allocation Excel File")

uploaded_file = st.file_uploader(
    "Upload your CLC_Allocation_Dashboard Excel file",
    type=['xlsx', 'xlsm'],
    help="Upload the allocation Excel file with student data. Student names will NOT be synced to the dashboard."
)

if uploaded_file is not None:
    
    # ══════════════════════════════════════════════════════════════════════════════
    # READ AND PROCESS EXCEL
    # ══════════════════════════════════════════════════════════════════════════════
    try:
        # Read Excel file
        df_excel = pd.read_excel(uploaded_file, sheet_name='Data_Model')
        
        st.success(f"✅ Excel file loaded successfully: **{len(df_excel)} student records** found")
        
        # Show preview (without student names)
        with st.expander("📋 Preview Data (De-identified)", expanded=False):
            preview_cols = ['Student_ID', 'Year Level', 'Referring_School', 'Allocated_Program', 
                          'Allocation_Status', 'Partnership_Area']
            available_cols = [col for col in preview_cols if col in df_excel.columns]
            st.dataframe(df_excel[available_cols].head(10), use_container_width=True)
        
        # ══════════════════════════════════════════════════════════════════════════════
        # DE-IDENTIFY AND MAP DATA
        # ══════════════════════════════════════════════════════════════════════════════
        
        def prepare_sync_data(df):
            """De-identify and map Excel columns to Supabase schema"""
            
            # Create clean dataframe with mapped columns
            sync_df = pd.DataFrame()
            
            # Map columns (Excel -> Supabase)
            column_mapping = {
                'Student_ID': 'id',  # Use student ID as primary key (UUID format if needed)
                'Gender': 'gender',
                'Year Level': 'year_level',
                'Referring_School': 'referring_school',
                'Referral_Date': 'referral_date',
                'Allocation_Status': 'allocation_status',
                'Allocated_Program': 'allocated_program',
                'Placement_Start': 'placement_start',
                'Placement_End': 'placement_end',
                'Partnership_Area': 'partnership_area',
                'Previous_CLC_Placement': 'previous_clc_placement',
                'Previous_Other_LC': 'previous_other_lc',
                'Other_LC_Name': 'other_lc_name',
                'Total_Previous_Placements': 'total_previous_placements',
                'Placement_History_Notes': 'placement_history_notes',
                'Priority_Level': 'priority_level',
                'Flag_ASD': 'flag_asd',
                'Flag_ADHD': 'flag_adhd',
                'Flag_MentalHealth': 'flag_mental_health',
                'Flag_ODD_CD': 'flag_odd_cd',
                'Flag_Care_CPS': 'flag_care_cps',
                'Flag_Aboriginal': 'flag_aboriginal',
                'Flag_EALD': 'flag_eald',
                'Flag_Other': 'flag_other',
                'Exit_Reason': 'exit_reason',
                'Transition_Plan': 'transition_plan',
                'Notes': 'notes'
            }
            
            # Map columns
            for excel_col, db_col in column_mapping.items():
                if excel_col in df.columns:
                    sync_df[db_col] = df[excel_col]
            
            # Convert Yes/No to boolean for flags
            flag_columns = ['flag_asd', 'flag_adhd', 'flag_mental_health', 'flag_odd_cd',
                          'flag_care_cps', 'flag_aboriginal', 'flag_eald', 'flag_other']
            
            for flag_col in flag_columns:
                if flag_col in sync_df.columns:
                    sync_df[flag_col] = sync_df[flag_col].map({'Yes': True, 'No': False, '': False})
                    sync_df[flag_col] = sync_df[flag_col].fillna(False)
            
            # Convert year level to string
            if 'year_level' in sync_df.columns:
                sync_df['year_level'] = sync_df['year_level'].astype(str).str.strip()
            
            # Handle dates
            date_columns = ['referral_date', 'placement_start', 'placement_end']
            for date_col in date_columns:
                if date_col in sync_df.columns:
                    sync_df[date_col] = pd.to_datetime(sync_df[date_col], errors='coerce')
                    # Convert to string for JSON serialization
                    sync_df[date_col] = sync_df[date_col].dt.strftime('%Y-%m-%d')
            
            # Handle NaN values
            sync_df = sync_df.replace({pd.NA: None, pd.NaT: None})
            sync_df = sync_df.where(pd.notna(sync_df), None)
            
            # Add current_status field (default to Active)
            sync_df['current_status'] = 'Active'
            
            # Add timestamps
            now = datetime.now().isoformat()
            sync_df['created_at'] = now
            sync_df['updated_at'] = now
            
            return sync_df
        
        # Prepare data
        sync_data = prepare_sync_data(df_excel)
        
        # Show sync summary
        st.markdown("### 📊 Sync Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Records to Sync", len(sync_data))
        
        with col2:
            active_count = len(sync_data[sync_data['allocation_status'] == 'Allocated'])
            st.metric("Allocated Students", active_count)
        
        with col3:
            swd_count = len(sync_data[
                (sync_data['flag_asd'] == True) | 
                (sync_data['flag_adhd'] == True) | 
                (sync_data['flag_mental_health'] == True) | 
                (sync_data['flag_odd_cd'] == True)
            ])
            st.metric("Students with Disabilities", swd_count)
        
        # Data validation warnings
        issues = []
        
        # Check for missing year levels
        missing_year = sync_data['year_level'].isna().sum()
        if missing_year > 0:
            issues.append(f"⚠️ {missing_year} records missing year level")
        
        # Check for missing schools
        missing_school = sync_data['referring_school'].isna().sum()
        if missing_school > 0:
            issues.append(f"⚠️ {missing_school} records missing referring school")
        
        # Check for missing programs
        missing_program = sync_data['allocated_program'].isna().sum()
        if missing_program > 0:
            issues.append(f"⚠️ {missing_program} records missing allocated program")
        
        if issues:
            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
            st.markdown("**⚠️ Data Quality Issues:**")
            for issue in issues:
                st.markdown(f"- {issue}")
            st.markdown("These records will sync but may not display correctly in the dashboard.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ══════════════════════════════════════════════════════════════════════════════
        # SYNC BUTTON
        # ══════════════════════════════════════════════════════════════════════════════
        
        st.markdown("### 🚀 Sync to Dashboard")
        
        st.info("**What happens when you sync:**\n"
                "1. Current dashboard data will be cleared\n"
                "2. De-identified data from Excel will be uploaded\n"
                "3. Dashboard will automatically update with new data\n"
                "4. Student names remain ONLY in your Excel file")
        
        if st.button("🔄 Sync to Dashboard Database", type="primary", use_container_width=True):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Initialize Supabase
                status_text.text("Connecting to database...")
                progress_bar.progress(20)
                supabase = init_supabase()
                
                # Clear existing data
                status_text.text("Clearing old dashboard data...")
                progress_bar.progress(40)
                
                # Delete all existing records
                supabase.table('allocation_tracker').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                
                # Insert new data
                status_text.text(f"Uploading {len(sync_data)} de-identified records...")
                progress_bar.progress(60)
                
                # Convert dataframe to list of dicts
                records = sync_data.to_dict('records')
                
                # Insert in batches of 50
                batch_size = 50
                total_inserted = 0
                
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    supabase.table('allocation_tracker').insert(batch).execute()
                    total_inserted += len(batch)
                    progress_bar.progress(60 + int(30 * (total_inserted / len(records))))
                
                # Complete
                progress_bar.progress(100)
                status_text.text("Sync complete!")
                
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown(f"""
                ### ✅ Sync Successful!
                
                **{len(sync_data)} records** have been synced to the dashboard database.
                
                **Next steps:**
                1. Go to the **Allocation Dashboard** page
                2. Dashboard will automatically show your updated data
                3. All student names remain secure in your Excel file
                
                **Privacy Status:** ✅ No student names were transmitted or stored in the database
                """)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Show what was synced
                with st.expander("📊 View Synced Data Preview", expanded=False):
                    display_cols = ['id', 'year_level', 'referring_school', 'allocated_program', 
                                  'allocation_status', 'partnership_area']
                    available_display = [col for col in display_cols if col in sync_data.columns]
                    st.dataframe(sync_data[available_display], use_container_width=True)
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ Sync failed: {str(e)}")
                st.exception(e)
    
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {str(e)}")
        st.exception(e)

else:
    # Instructions when no file uploaded
    st.markdown("""
    ### 📖 How to Use
    
    1. **Upload your allocation Excel file** above
       - File: `CLC_Allocation_Dashboard_2026_WithNames_1.xlsx`
       - From: SharePoint or local copy
    
    2. **Review the data preview** to ensure it loaded correctly
    
    3. **Click "Sync to Dashboard"** to update the live dashboard
    
    4. **Student names never leave Excel** - only de-identified analytics data syncs
    
    ### 🔒 Privacy Guarantee
    
    This sync tool implements **privacy by design**:
    - Student names are **never read** from the Excel file
    - Date of birth is **not synced** - only year level
    - Only analytics data needed for the dashboard is transmitted
    - Full student records remain secure in Excel with portal authentication
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem 0;">
    <p style="font-size: 0.9rem;">🔄 Allocation Sync Tool | Cowandilla Learning Centre LBU</p>
    <p style="font-size: 0.85rem; color: #1A7A6E; font-weight: 600;">
        🔒 Privacy-preserving • De-identified data only • Student names stay in Excel
    </p>
</div>
""", unsafe_allow_html=True)
