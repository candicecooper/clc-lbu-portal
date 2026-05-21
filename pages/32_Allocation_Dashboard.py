import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from supabase import create_client, Client
import folium
from streamlit_folium import st_folium
from collections import Counter

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Allocation Dashboard | CLC-LBU", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Hide sidebar */
    [data-testid="stSidebar"] {display: none;}
    
    /* Main container */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Header */
    .dashboard-header {
        background: linear-gradient(135deg, #1A7A6E 0%, #4A9B8E 100%);
        padding: 2.5rem 3rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .dashboard-header h1 {
        color: white;
        margin: 0;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .dashboard-header p {
        color: #D6F0EB;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        transition: transform 0.2s;
        border-left: 5px solid #1A7A6E;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    .metric-number {
        font-size: 3.5rem;
        font-weight: 700;
        color: #1A7A6E;
        margin: 0;
        line-height: 1;
    }
    .metric-label {
        font-size: 0.95rem;
        color: #666;
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Info boxes */
    .info-box {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #C8760A;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Privacy badge */
    .privacy-badge {
        background: #D6F0EB;
        color: #1A7A6E;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin-top: 1rem;
    }
    
    /* Section headers */
    .section-header {
        color: #1A7A6E;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #1A7A6E;
    }
    
    /* Drill-down badge */
    .drill-badge {
        background: #C8760A;
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-left: 0.5rem;
    }
    
    /* Interactive hint */
    .interactive-hint {
        background: #FFF9E6;
        border: 2px dashed #C8760A;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
        color: #C8760A;
        font-weight: 600;
    }
    
    /* Refresh badge */
    .refresh-badge {
        background: #4CAF50;
        color: white;
        padding: 0.3rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-left: 0.5rem;
    }
    
    /* Sync section */
    .sync-box {
        background: #FFF9E6;
        border: 2px solid #C8760A;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE CONNECTION
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def init_supabase():
    """Initialize Supabase client - cached to avoid reconnecting"""
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY environment variables.")
        st.stop()
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)  # Cache for 60 seconds, then refresh
def load_allocation_data():
    """Load allocation data from Supabase - refreshes every 60 seconds"""
    try:
        supabase = init_supabase()
        
        # Fetch all records from allocation_tracker table
        response = supabase.table('allocation_tracker').select('*').execute()
        
        if not response.data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(response.data)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error loading data from Supabase: {str(e)}")
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="dashboard-header">
    <h1>📊 Allocation Dashboard</h1>
    <p>Live student allocation overview • Interactive drill-down analytics</p>
    <span class="privacy-badge">🔒 Privacy Protected • De-identified Data</span>
    <span class="refresh-badge">🔄 Auto-refresh 60s</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN SECTION: DATA SYNC
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("🔧 **ADMIN: Sync Data from Excel**", expanded=False):
    st.markdown("""
    <div class="sync-box">
    <strong>🔒 Privacy-Preserving Sync</strong><br>
    Upload your allocation Excel file to update the dashboard. <strong>Student names are automatically removed</strong> during sync.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload Allocation Excel File",
            type=['xlsx', 'xlsm'],
            help="CLC_Allocation_Dashboard Excel file - student names will NOT be synced",
            key="excel_upload"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        sync_button = st.button("🔄 Sync to Dashboard", type="primary", use_container_width=True, disabled=(uploaded_file is None))
    
    if uploaded_file is not None and sync_button:
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Read Excel file
            status_text.text("Reading Excel file...")
            progress_bar.progress(10)
            df_excel = pd.read_excel(uploaded_file, sheet_name='Data_Model')
            
            # DEBUG: Show raw Excel values IMMEDIATELY after reading
            st.info(f"📄 **Excel file read:** {len(df_excel)} rows")
            
            with st.expander("🔍 DEBUG: Raw Excel Data (Before ANY Processing)", expanded=True):
                st.write("**Previous_CLC_Placement column in Excel:**")
                if 'Previous_CLC_Placement' in df_excel.columns:
                    prev_counts = df_excel['Previous_CLC_Placement'].value_counts()
                    st.write(prev_counts)
                    st.write(f"**Type of values:** {df_excel['Previous_CLC_Placement'].dtype}")
                    st.write(f"**Sample raw values:** {df_excel['Previous_CLC_Placement'].head(5).tolist()}")
                    st.write(f"**Students with 'Yes':** {(df_excel['Previous_CLC_Placement'] == 'Yes').sum()}")
                else:
                    st.error("❌ Previous_CLC_Placement column NOT FOUND in Excel!")
                    st.write(f"**Available columns:** {list(df_excel.columns)}")
            
            status_text.text(f"Processing {len(df_excel)} student records...")
            progress_bar.progress(20)
            
            # Prepare sync data (de-identify)
            def prepare_sync_data(df):
                """De-identify and map Excel columns to Supabase schema"""
                import numpy as np
                
                sync_df = pd.DataFrame()
                
                # Map columns (Excel -> Supabase) - STUDENT NAMES EXCLUDED
                # Note: 'id' column (UUID) will be auto-generated by Supabase
                # Student_ID from Excel goes to 'student_id' (text) column
                column_mapping = {
                    'Student_ID': 'student_id',  # Store Excel ID as text, not UUID
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
                    'Bespoke_Placement': 'bespoke_placement',  # Your non-typical placement flag
                    'Waitlist_Status': 'waitlist_status',  # Waitlist tracking
                    'Waitlist_Date': 'waitlist_date',  # When joined waitlist
                    'Allocated_From_Waitlist': 'allocated_from_waitlist',  # Previously waitlisted
                    'Exit_Reason': 'exit_reason',
                    'Transition_Plan': 'transition_plan',
                    'Notes': 'notes'
                }
                
                # Map columns
                for excel_col, db_col in column_mapping.items():
                    if excel_col in df.columns:
                        sync_df[db_col] = df[excel_col]
                
                # DEBUG: Check if previous_clc_placement survived column mapping
                if 'previous_clc_placement' in sync_df.columns:
                    st.write("✅ **After column mapping - previous_clc_placement exists**")
                    st.write(f"Values: {sync_df['previous_clc_placement'].value_counts().to_dict()}")
                else:
                    st.error("❌ previous_clc_placement NOT in sync_df after mapping!")
                
                # Convert Yes/No to boolean for flags ONLY
                # Previous placements will be handled separately
                flag_columns = ['flag_asd', 'flag_adhd', 'flag_mental_health', 'flag_odd_cd',
                              'flag_care_cps', 'flag_aboriginal', 'flag_eald', 'flag_other',
                              'bespoke_placement']  # Include bespoke_placement in flag conversion
                
                for flag_col in flag_columns:
                    if flag_col in sync_df.columns:
                        sync_df[flag_col] = sync_df[flag_col].map({'Yes': True, 'No': False, '': False})
                        sync_df[flag_col] = sync_df[flag_col].fillna(False)
                
                # Convert year level to string
                if 'year_level' in sync_df.columns:
                    sync_df['year_level'] = sync_df['year_level'].astype(str).str.strip()
                    # Replace 'nan' string with None
                    sync_df['year_level'] = sync_df['year_level'].replace('nan', None)
                
                # Handle dates
                date_columns = ['referral_date', 'placement_start', 'placement_end', 'waitlist_date']
                for date_col in date_columns:
                    if date_col in sync_df.columns:
                        sync_df[date_col] = pd.to_datetime(sync_df[date_col], errors='coerce')
                        # Convert valid dates to string, keep NaT as None
                        sync_df[date_col] = sync_df[date_col].apply(
                            lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None
                        )
                
                # COMPREHENSIVE NaN handling - convert all NaN/inf values to None
                # This is critical for JSON serialization
                sync_df = sync_df.replace([np.nan, np.inf, -np.inf], None)
                sync_df = sync_df.replace({pd.NA: None, pd.NaT: None})
                
                # Additional pass to catch any remaining NaN in object columns
                for col in sync_df.columns:
                    if sync_df[col].dtype == 'object':
                        sync_df[col] = sync_df[col].where(pd.notna(sync_df[col]), None)
                
                # Convert integer columns with NaN to nullable int or None
                int_columns = ['total_previous_placements']
                for col in int_columns:
                    if col in sync_df.columns:
                        sync_df[col] = sync_df[col].where(pd.notna(sync_df[col]), None)
                        # Convert valid values to int
                        sync_df[col] = sync_df[col].apply(
                            lambda x: int(x) if x is not None and pd.notna(x) else None
                        )
                
                # FINAL AGGRESSIVE CLEANUP: Convert to dict and clean any remaining NaN
                # This catches edge cases that pandas might miss
                records = sync_df.to_dict('records')
                
                # Deep clean each record
                cleaned_records = []
                for record in records:
                    cleaned_record = {}
                    for key, value in record.items():
                        # Convert any remaining NaN/inf to None
                        if pd.isna(value) or (isinstance(value, float) and (np.isinf(value) or np.isnan(value))):
                            cleaned_record[key] = None
                        # Convert numpy bool to Python bool
                        elif isinstance(value, (np.bool_, bool)):
                            cleaned_record[key] = bool(value)
                        # Convert numpy int to Python int
                        elif isinstance(value, (np.integer, np.int64, np.int32)):
                            cleaned_record[key] = int(value)
                        # Convert numpy float to Python float (if not NaN)
                        elif isinstance(value, (np.floating, np.float64, np.float32)):
                            cleaned_record[key] = float(value) if not np.isnan(value) else None
                        else:
                            cleaned_record[key] = value
                    cleaned_records.append(cleaned_record)
                
                # Convert back to DataFrame for consistency
                sync_df = pd.DataFrame(cleaned_records)
                
                # DEBUG: Check values BEFORE to_yes_no conversion
                if 'previous_clc_placement' in sync_df.columns:
                    st.write("🔍 **Before to_yes_no conversion:**")
                    st.write(f"Values: {sync_df['previous_clc_placement'].value_counts().to_dict()}")
                    st.write(f"Sample: {sync_df['previous_clc_placement'].head(5).tolist()}")
                
                # NOW handle text columns AFTER aggressive cleanup to preserve values
                
                # Previous_CLC_Placement and Previous_Other_LC: Convert to Yes/No
                for yes_no_col in ['previous_clc_placement', 'previous_other_lc']:
                    if yes_no_col in sync_df.columns:
                        def to_yes_no(val):
                            if pd.isna(val) or val is None or val == '' or val == 'None':
                                return 'No'
                            val_str = str(val).strip().lower()
                            return 'Yes' if val_str == 'yes' else 'No'
                        sync_df[yes_no_col] = sync_df[yes_no_col].apply(to_yes_no)
                
                # Waitlist columns: Keep as-is but clean
                for text_col in ['waitlist_status', 'allocated_from_waitlist']:
                    if text_col in sync_df.columns:
                        def clean_text(val):
                            if pd.isna(val) or val is None or val == '' or val == 'None':
                                return None
                            return str(val).strip()
                        sync_df[text_col] = sync_df[text_col].apply(clean_text)
                
                # DEBUG: Check values AFTER to_yes_no conversion
                if 'previous_clc_placement' in sync_df.columns:
                    st.write("✅ **After to_yes_no conversion:**")
                    st.write(f"Values: {sync_df['previous_clc_placement'].value_counts().to_dict()}")
                    st.success(f"**YES count: {(sync_df['previous_clc_placement'] == 'Yes').sum()}**")
                
                # Add current_status
                sync_df['current_status'] = 'Active'
                
                # Add timestamps
                now = datetime.now().isoformat()
                sync_df['created_at'] = now
                sync_df['updated_at'] = now
                
                return sync_df
            
            sync_data = prepare_sync_data(df_excel)
            
            # DEBUG: Show previous_clc_placement values before sync
            with st.expander("🔍 Debug: Check Previous Placement Data", expanded=False):
                if 'previous_clc_placement' in sync_data.columns:
                    prev_clc_counts = sync_data['previous_clc_placement'].value_counts()
                    st.write("**Previous CLC Placement values:**")
                    st.write(prev_clc_counts)
                    st.write(f"**Type:** {type(sync_data['previous_clc_placement'].iloc[0]) if len(sync_data) > 0 else 'N/A'}")
                else:
                    st.error("❌ previous_clc_placement column missing from sync data!")
            
            # Initialize Supabase
            status_text.text("Connecting to database...")
            progress_bar.progress(40)
            supabase = init_supabase()
            
            # Clear existing data
            status_text.text("Clearing old dashboard data...")
            progress_bar.progress(50)
            supabase.table('allocation_tracker').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            
            # Insert new data
            status_text.text(f"Uploading {len(sync_data)} de-identified records...")
            progress_bar.progress(60)
            
            # Convert to list of dicts
            records = sync_data.to_dict('records')
            
            # FINAL ULTIMATE NaN KILLER - check every single value before Supabase
            def kill_all_nans(record):
                """Remove ALL NaN values from a record, no matter what"""
                clean = {}
                # Integer columns that must be int, not float or string
                int_columns = {'total_previous_placements'}
                
                for key, value in record.items():
                    # Check for NaN in every possible way
                    try:
                        if value is None:
                            clean[key] = None
                        elif key in int_columns:
                            # Special handling for integer columns
                            if pd.isna(value) or value is None or value == '' or value == 'None':
                                clean[key] = None
                            else:
                                # Convert to int (handles float 0.0 -> int 0)
                                try:
                                    clean[key] = int(float(value))
                                except:
                                    clean[key] = None
                        elif isinstance(value, float):
                            # Check if it's NaN or inf
                            import math
                            if math.isnan(value) or math.isinf(value):
                                clean[key] = None
                            else:
                                clean[key] = value
                        elif isinstance(value, str):
                            # String is fine
                            clean[key] = value if value not in ['nan', 'NaN', 'NaT'] else None
                        elif isinstance(value, bool):
                            # Boolean is fine
                            clean[key] = value
                        elif isinstance(value, int):
                            # Int is fine
                            clean[key] = value
                        else:
                            # Try to convert, if fails set to None
                            try:
                                # Check if pandas/numpy thinks it's NaN
                                if pd.isna(value):
                                    clean[key] = None
                                else:
                                    clean[key] = value
                            except:
                                clean[key] = value
                    except:
                        # If anything fails, set to None to be safe
                        clean[key] = None
                return clean
            
            # Clean every single record
            records = [kill_all_nans(record) for record in records]
            
            # Insert in batches
            batch_size = 50
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                supabase.table('allocation_tracker').insert(batch).execute()
                progress_bar.progress(60 + int(30 * ((i + len(batch)) / len(records))))
            
            # Clear cache to force reload
            load_allocation_data.clear()
            
            # Complete
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            st.success(f"""
            ✅ **Sync Successful!** {len(sync_data)} records synced to dashboard.
            
            **Privacy Status:** ✅ No student names were transmitted or stored in database.
            
            Dashboard below will refresh automatically in 60 seconds, or refresh your browser now.
            """)
            
            # Force page rerun to show new data
            st.rerun()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Sync failed: {str(e)}")
            st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
df_raw = load_allocation_data()

if len(df_raw) == 0:
    st.info("""
    📭 **No allocation data in dashboard yet.**
    
    **To get started:**
    1. Click "🔧 ADMIN: Sync Data from Excel" above
    2. Upload your allocation Excel file
    3. Click "Sync to Dashboard"
    4. Dashboard will populate with de-identified data
    """)
    st.stop()

# Show last update time
current_year = datetime.now().year
st.caption(f"📅 Last updated: {datetime.now().strftime('%d/%m/%Y %I:%M %p')} | Current year: {current_year} | Total records: {len(df_raw)}")

# Validate year
if current_year != 2026:
    st.warning(f"⚠️ System year is {current_year}, not 2026. Year level and term calculations may be incorrect. Please check your server's system time.")

# ══════════════════════════════════════════════════════════════════════════════
# DATA PROCESSING & MAPPING
# ══════════════════════════════════════════════════════════════════════════════
# Create working copy
df = df_raw.copy()

# Map Supabase columns to dashboard expectations
df['record_id'] = df.get('student_id', df.get('id', ''))  # Use student_id if available, fallback to id
df['school'] = df['referring_school'].fillna('Unknown School')
df['status'] = df['allocation_status'].fillna('Unknown Status')
df['program'] = df['allocated_program'].fillna('Unknown Program')
df['partnership'] = df['partnership_area'].fillna('')

# Handle dates
df['referral_date'] = pd.to_datetime(df['referral_date'], errors='coerce')
df['year'] = df['referral_date'].dt.year
df['month'] = df['referral_date'].dt.month

# Get year level from database
def calculate_year_level_from_dob(dob):
    """Calculate year level from date of birth as fallback"""
    if pd.isna(dob):
        return "Unknown"
    dob = pd.to_datetime(dob)
    today = datetime.now()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 5: return "R"
    elif age == 5: return "R"
    elif age == 6: return "1"
    elif age == 7: return "2"
    elif age == 8: return "3"
    elif age == 9: return "4"
    elif age == 10: return "5"
    elif age == 11: return "6"
    elif age == 12: return "7"
    elif age == 13: return "8"
    elif age == 14: return "9"
    elif age >= 15: return "10"
    else: return "Unknown"

# Use database year_level
if 'year_level' in df.columns:
    df['year_level'] = df['year_level'].fillna('Unknown').astype(str)
else:
    df['year_level'] = "Unknown"

# Create SWD and DCP flags
df['swd'] = (
    df.get('flag_asd', False) | 
    df.get('flag_adhd', False) | 
    df.get('flag_mental_health', False) | 
    df.get('flag_odd_cd', False)
).map({True: 'Yes', False: 'No'})

df['dcp'] = df.get('flag_care_cps', False).map({True: 'Yes', False: 'No'})

# Map other flags
df['aboriginal'] = df.get('flag_aboriginal', False).map({True: 'Yes', False: 'No'})
df['eald'] = df.get('flag_eald', False).map({True: 'Yes', False: 'No'})
df['care_cps'] = df.get('flag_care_cps', False).map({True: 'Yes', False: 'No'})
df['mental_health'] = df.get('flag_mental_health', False).map({True: 'Yes', False: 'No'})

# Previous placements - already converted to Yes/No during sync
df['prev_clc'] = df.get('previous_clc_placement', 'No').fillna('No')
df['prev_other'] = df.get('previous_other_lc', 'No').fillna('No')

# DEBUG: Show what's actually in the dashboard data
with st.expander("🔍 Debug: Dashboard Previous Placement Data", expanded=False):
    st.write("**Raw previous_clc_placement from database:**")
    if 'previous_clc_placement' in df.columns:
        st.write(df['previous_clc_placement'].value_counts())
        st.write(f"**Sample values:** {df['previous_clc_placement'].head(5).tolist()}")
    else:
        st.error("Column 'previous_clc_placement' not found in database!")
    
    st.write("**Processed prev_clc values:**")
    st.write(df['prev_clc'].value_counts())
    st.write(f"**Total returning (prev_clc=='Yes'):** {(df['prev_clc'] == 'Yes').sum()}")

# Priority
df['priority'] = df.get('priority_level', '')

# Current status
df['current_status'] = df.get('current_status', 'Active')

# Define terms
def get_term(month):
    if pd.isna(month) or month is None:
        return "Unknown"
    try:
        month = int(month)
        if month <= 3:
            return "Term 1"
        elif month <= 6:
            return "Term 2"
        elif month <= 9:
            return "Term 3"
        else:
            return "Term 4"
    except (ValueError, TypeError):
        return "Unknown"

df['term'] = df['month'].apply(get_term)

# Program placement - use Excel's Bespoke_Placement flag
# This is YOUR authoritative definition of non-typical placement
if 'bespoke_placement' in df.columns:
    # Handle BOTH boolean (from database) and text 'Yes'/'No' (from Excel)
    def parse_bespoke(val):
        if pd.isna(val) or val == '' or val is None:
            return False
        if isinstance(val, bool):
            return val  # Already boolean from database
        if isinstance(val, str):
            return val.strip().lower() in ['yes', 'true', '1']
        return False
    
    df['program_mismatch'] = df['bespoke_placement'].apply(parse_bespoke)
    
    # DEBUG: Show bespoke placement values
    if st.checkbox("🔍 Debug: Show Bespoke Placement Data", value=False):
        st.write("**Bespoke Placement Values:**")
        debug_df = df[['student_id', 'referring_school', 'year_level', 'allocated_program', 'bespoke_placement', 'program_mismatch']].copy()
        st.dataframe(debug_df[debug_df['program_mismatch'] == True])
        st.write(f"**Total Non-Typical:** {len(debug_df[debug_df['program_mismatch'] == True])}")
    
    # Still calculate expected_program for display purposes
    def get_expected_program(year_level):
        """Determine expected program based on year level"""
        if pd.isna(year_level) or year_level == '' or year_level == "Unknown" or year_level == 'None':
            return "Unknown"
        year_level = str(year_level).upper()
        if year_level in ['R', '1']:
            return "Junior Primary (R-1)"
        elif year_level in ['3', '4', '5', '6']:
            return "Primary Years (3-6)"
        elif year_level in ['7', '8', '9', '10']:
            return "Senior Years (7-10)"
        else:
            return "Unknown"
    
    df['expected_program'] = df['year_level'].apply(get_expected_program)
else:
    # Fallback: calculate based on year level if Bespoke_Placement not available
    def get_expected_program(year_level):
        """Determine expected program based on year level"""
        if pd.isna(year_level) or year_level == '' or year_level == "Unknown" or year_level == 'None':
            return "Unknown"
        year_level = str(year_level).upper()
        if year_level in ['R', '1']:
            return "Junior Primary (R-1)"
        elif year_level in ['3', '4', '5', '6']:
            return "Primary Years (3-6)"
        elif year_level in ['7', '8', '9', '10']:
            return "Senior Years (7-10)"
        else:
            return "Unknown"

    df['expected_program'] = df['year_level'].apply(get_expected_program)
    df['program_mismatch'] = (df['program'] != df['expected_program']) & (df['expected_program'] != "Unknown")

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔍 Filters & View Options</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    terms = ['All Terms'] + sorted([t for t in df['term'].unique() if pd.notna(t)])
    selected_term = st.selectbox("📅 Select Term", terms, key="term_filter")

with col2:
    partnerships = ['All Partnerships'] + sorted([p for p in df['partnership'].unique() if p != '' and pd.notna(p)])
    selected_partnership = st.selectbox("🤝 Select Partnership", partnerships, key="partnership_filter")

with col3:
    programs = ['All Programs'] + sorted([p for p in df['program'].unique() if pd.notna(p)])
    selected_program = st.selectbox("📚 Select Program", programs, key="program_filter")

# Apply filters
filtered_df = df.copy()

if selected_term != 'All Terms':
    filtered_df = filtered_df[filtered_df['term'] == selected_term]

if selected_partnership != 'All Partnerships':
    filtered_df = filtered_df[filtered_df['partnership'] == selected_partnership]

if selected_program != 'All Programs':
    filtered_df = filtered_df[filtered_df['program'] == selected_program]

# Show filter status
if selected_term != 'All Terms' or selected_partnership != 'All Partnerships' or selected_program != 'All Programs':
    active_filters = []
    if selected_term != 'All Terms':
        active_filters.append(f"**{selected_term}**")
    if selected_partnership != 'All Partnerships':
        active_filters.append(f"**{selected_partnership}**")
    if selected_program != 'All Programs':
        active_filters.append(f"**{selected_program}**")
    st.info(f"🔎 Showing data for: {' • '.join(active_filters)} | Displaying {len(filtered_df)} of {len(df)} records")

# ══════════════════════════════════════════════════════════════════════════════
# KEY METRICS
# ══════════════════════════════════════════════════════════════════════════════
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{len(filtered_df)}</div>
        <div class="metric-label">Total Referrals</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    allocated = len(filtered_df[filtered_df['status'] == 'Allocated'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{allocated}</div>
        <div class="metric-label">Allocated</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    mismatch_filtered = len(filtered_df[filtered_df['program_mismatch'] == True])
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #C8760A;">
        <div class="metric-number" style="color: #C8760A;">{mismatch_filtered}</div>
        <div class="metric-label">Non-Typical Placement</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    swd_count = len(filtered_df[filtered_df['swd'] == 'Yes'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{swd_count}</div>
        <div class="metric-label">SWD</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    dcp_count = len(filtered_df[filtered_df['dcp'] == 'Yes'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{dcp_count}</div>
        <div class="metric-label">DCP</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    partnership_count = len(filtered_df[filtered_df['partnership'] != ''])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{partnership_count}</div>
        <div class="metric-label">Partnership Students</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ADELAIDE CATCHMENT MAP
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🗺️ Adelaide Catchment Map</div>', unsafe_allow_html=True)
st.markdown("**Geographic distribution of student allocations across partnership areas**")

# Count by partnership from filtered data
partnership_counts = Counter()
for _, record in filtered_df.iterrows():
    partnership = record.get('partnership', '')
    if partnership and partnership != '':
        partnership_counts[partnership] += 1

total_map_students = sum(partnership_counts.values())

# Partnership regions with coordinates
partnership_regions = {
    "Le Fevre Peninsula": {"color": "#E74C3C", "coords": [[-34.78, 138.48], [-34.78, 138.52], [-34.84, 138.52], [-34.85, 138.50], [-34.84, 138.48]]},
    "Western Adelaide Shores": {"color": "#1ABC9C", "coords": [[-34.85, 138.48], [-34.85, 138.52], [-34.88, 138.52], [-34.88, 138.48]]},
    "Inner West": {"color": "#3498DB", "coords": [[-34.90, 138.54], [-34.90, 138.58], [-34.94, 138.58], [-34.94, 138.54]]},
    "West Torrens": {"color": "#F39C12", "coords": [[-34.93, 138.55], [-34.93, 138.59], [-34.96, 138.59], [-34.96, 138.55]]},
    "Adelaide Prospect": {"color": "#34495E", "coords": [[-34.84, 138.58], [-34.84, 138.62], [-34.88, 138.62], [-34.88, 138.58]]},
    "Holdfast": {"color": "#E67E22", "coords": [[-35.00, 138.50], [-35.00, 138.55], [-35.05, 138.55], [-35.05, 138.50]]},
    "Greenhill South": {"color": "#2ECC71", "coords": [[-34.96, 138.60], [-34.96, 138.66], [-35.01, 138.66], [-35.01, 138.60]]},
    "Mitcham Hills": {"color": "#9B59B6", "coords": [[-34.96, 138.62], [-34.96, 138.68], [-35.01, 138.68], [-35.01, 138.62]]},
    "Orion": {"color": "#8E44AD", "coords": [[-34.68, 138.61], [-34.68, 138.67], [-34.73, 138.67], [-34.73, 138.61]]},
    "Marion Inland": {"color": "#16A085", "coords": [[-35.00, 138.54], [-35.00, 138.59], [-35.05, 138.59], [-35.05, 138.54]]},
    "Marion Coastal": {"color": "#27AE60", "coords": [[-35.03, 138.50], [-35.03, 138.54], [-35.08, 138.54], [-35.08, 138.50]]},
    "Onkaparinga": {"color": "#D35400", "coords": [[-35.10, 138.50], [-35.10, 138.58], [-35.18, 138.58], [-35.18, 138.50]]}
}

# Map layout
map_col, stats_col = st.columns([3, 1])

with map_col:
    # Create map
    m = folium.Map(location=[-34.92, 138.60], zoom_start=10, tiles='OpenStreetMap')
    max_count = max(partnership_counts.values()) if partnership_counts else 1
    
    # Add partnership regions
    for partnership_name, region_data in partnership_regions.items():
        count = partnership_counts.get(partnership_name, 0)
        if count > 0:
            opacity = 0.3 + (count / max_count) * 0.5
            percentage = (count / total_map_students * 100) if total_map_students > 0 else 0
            
            folium.Polygon(
                locations=region_data["coords"],
                color=region_data["color"],
                fill=True,
                fillColor=region_data["color"],
                fillOpacity=opacity,
                weight=3,
                popup=folium.Popup(
                    f"""<div style='font-family: Arial; padding: 10px;'>
                    <h4 style='margin: 0; color: {region_data["color"]};'>{partnership_name}</h4>
                    <p style='margin: 5px 0; font-size: 24px; font-weight: bold;'>{count}</p>
                    <p style='margin: 0; color: #666;'>{percentage:.1f}% of total</p></div>""",
                    max_width=200
                ),
                tooltip=f"{partnership_name}: {count} students"
            ).add_to(m)
    
    # Add CLC marker
    folium.Marker(
        location=[-34.9286, 138.5830],
        popup="🏫 CLC-LBU<br>Cowandilla Learning Centre",
        tooltip="Cowandilla Learning Centre",
        icon=folium.Icon(color='green', icon='home', prefix='fa')
    ).add_to(m)
    
    st_folium(m, width=None, height=500)

with stats_col:
    st.markdown("**Distribution**")
    for partnership, count in sorted(partnership_counts.items(), key=lambda x: x[1], reverse=True):
        if partnership:
            percentage = (count / total_map_students * 100) if total_map_students > 0 else 0
            color = partnership_regions.get(partnership, {}).get('color', '#95A5A6')
            st.markdown(f"""
                <div style='padding: 10px; margin-bottom: 8px; border-left: 4px solid {color}; 
                            background: white; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <div style='font-weight: 600; font-size: 0.85em;'>{partnership}</div>
                    <div style='font-size: 1.6em; font-weight: bold; color: {color};'>{count}</div>
                    <div style='font-size: 0.8em; color: #666;'>{percentage:.1f}%</div>
                </div>
            """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE DRILL-DOWN SECTIONS
# ══════════════════════════════════════════════════════════════════════════════

# [REST OF THE DASHBOARD CODE CONTINUES EXACTLY AS BEFORE - ALL TABS, CHARTS, ETC.]
# For brevity, I'll indicate where the existing tab code goes...

st.markdown('<div class="section-header">🎯 Interactive Drill-Down Analytics <span class="drill-badge">Click to Explore</span></div>', unsafe_allow_html=True)

# Create tabs for different drill-down views
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Partnership Deep Dive",
    "🏫 School Distribution",
    "📅 Term Trends",
    "🎨 Program Breakdown",
    "⚠️ Non-Typical Placements",
    "🔄 Placement History",
    "⏳ Waitlist & Non-Placed"  # NEW TAB
])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: PARTNERSHIP DEEP DIVE
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 🤝 Partnership Enrollment Distribution")
    
    partnership_df = filtered_df[filtered_df['partnership'] != ''].copy()
    
    if len(partnership_df) > 0:
        partnership_counts = partnership_df['partnership'].value_counts().reset_index()
        partnership_counts.columns = ['Partnership', 'Count']
        
        fig_partnership = px.bar(
            partnership_counts,
            x='Partnership',
            y='Count',
            title='Students by Partnership',
            color='Count',
            color_continuous_scale='Teal',
            text='Count'
        )
        fig_partnership.update_traces(textposition='outside')
        fig_partnership.update_layout(
            showlegend=False,
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Partnership",
            yaxis_title="Number of Students"
        )
        st.plotly_chart(fig_partnership, use_container_width=True)
        
        st.markdown("#### 🔍 Drill Down into Specific Partnership")
        selected_partnership_drill = st.selectbox(
            "Select a partnership to see detailed breakdown:",
            [''] + sorted(partnership_df['partnership'].unique().tolist()),
            key="partnership_drill"
        )
        
        if selected_partnership_drill:
            partnership_detail_df = partnership_df[partnership_df['partnership'] == selected_partnership_drill]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**📌 {selected_partnership_drill} Overview**")
                st.metric("Total Students", len(partnership_detail_df))
                
                schools_in_partnership = partnership_detail_df['school'].value_counts()
                st.markdown("**🏫 Referring Schools:**")
                for school, count in schools_in_partnership.items():
                    st.write(f"• {school}: **{count}** student(s)")
            
            with col2:
                programs_in_partnership = partnership_detail_df['program'].value_counts()
                fig_programs = px.pie(
                    values=programs_in_partnership.values,
                    names=programs_in_partnership.index,
                    title=f'Programs in {selected_partnership_drill}',
                    color_discrete_sequence=px.colors.sequential.Teal
                )
                st.plotly_chart(fig_programs, use_container_width=True)
            
            st.markdown("**📋 Student Records:**")
            detail_display = partnership_detail_df[['record_id', 'school', 'year_level', 'program', 'expected_program', 'program_mismatch', 'term', 'swd', 'dcp']].copy()
            detail_display.columns = ['Record ID', 'School', 'Year', 'Program', 'Expected', 'Non-Typical', 'Term', 'SWD', 'DCP']
            detail_display['Non-Typical'] = detail_display['Non-Typical'].apply(lambda x: '⚠️' if x else '✓')
            st.dataframe(detail_display, use_container_width=True, hide_index=True)
    else:
        st.info("No partnership data available for the selected filters.")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: SCHOOL DISTRIBUTION
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 🏫 Students Allocated Per School")
    
    school_counts = filtered_df['school'].value_counts().reset_index()
    school_counts.columns = ['School', 'Count']
    school_counts = school_counts.sort_values('Count', ascending=False)
    
    fig_schools = px.bar(
        school_counts,
        y='School',
        x='Count',
        orientation='h',
        title='Student Allocation by Referring School',
        color='Count',
        color_continuous_scale='Oranges',
        text='Count'
    )
    fig_schools.update_traces(textposition='outside')
    fig_schools.update_layout(
        height=max(400, len(school_counts) * 30),
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis_title="School",
        xaxis_title="Number of Students"
    )
    st.plotly_chart(fig_schools, use_container_width=True)
    
    st.markdown("#### 🔍 Drill Down into Specific School")
    selected_school = st.selectbox(
        "Select a school to see detailed breakdown:",
        [''] + school_counts['School'].tolist(),
        key="school_drill"
    )
    
    if selected_school:
        school_detail_df = filtered_df[filtered_df['school'] == selected_school]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Total Students", len(school_detail_df))
            
        with col2:
            partnership_name = school_detail_df['partnership'].iloc[0] if len(school_detail_df) > 0 and school_detail_df['partnership'].iloc[0] != '' else "No Partnership"
            st.metric("🤝 Partnership", partnership_name)
            
        with col3:
            primary_program = school_detail_df['program'].mode()[0] if len(school_detail_df) > 0 else "N/A"
            st.metric("📚 Primary Program", primary_program)
        
        col1, col2 = st.columns(2)
        
        with col1:
            program_dist = school_detail_df['program'].value_counts()
            fig_prog = px.bar(
                x=program_dist.index,
                y=program_dist.values,
                title=f'Programs at {selected_school}',
                color=program_dist.values,
                color_continuous_scale='Teal',
                text=program_dist.values
            )
            fig_prog.update_traces(textposition='outside')
            fig_prog.update_layout(
                showlegend=False,
                height=300,
                xaxis_title="Program",
                yaxis_title="Students"
            )
            st.plotly_chart(fig_prog, use_container_width=True)
        
        with col2:
            flag_counts = {
                'SWD': (school_detail_df['swd'] == 'Yes').sum(),
                'DCP': (school_detail_df['dcp'] == 'Yes').sum(),
                'Aboriginal': (school_detail_df['aboriginal'] == 'Yes').sum(),
                'EALD': (school_detail_df['eald'] == 'Yes').sum()
            }
            
            fig_flags = px.bar(
                x=list(flag_counts.keys()),
                y=list(flag_counts.values()),
                title=f'Support Flags at {selected_school}',
                color=list(flag_counts.values()),
                color_continuous_scale='Oranges',
                text=list(flag_counts.values())
            )
            fig_flags.update_traces(textposition='outside')
            fig_flags.update_layout(
                showlegend=False,
                height=300,
                xaxis_title="Flag Type",
                yaxis_title="Count"
            )
            st.plotly_chart(fig_flags, use_container_width=True)
        
        st.markdown("**📋 Individual Student Records:**")
        school_display = school_detail_df[['record_id', 'year_level', 'program', 'expected_program', 'program_mismatch', 'term', 'referral_date', 'swd', 'dcp', 'aboriginal', 'eald']].copy()
        school_display.columns = ['Record ID', 'Year', 'Program', 'Expected', 'Non-Typical', 'Term', 'Referral Date', 'SWD', 'DCP', 'Aboriginal', 'EALD']
        school_display['Non-Typical'] = school_display['Non-Typical'].apply(lambda x: '⚠️' if x else '✓')
        school_display['Referral Date'] = pd.to_datetime(school_display['Referral Date']).dt.strftime('%d/%m/%Y')
        st.dataframe(school_display, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: TERM TRENDS
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 📅 Term-by-Term Allocation Trends")
    
    term_counts = filtered_df['term'].value_counts().reindex(['Term 1', 'Term 2', 'Term 3', 'Term 4'], fill_value=0)
    
    fig_terms = px.bar(
        x=term_counts.index,
        y=term_counts.values,
        title='Referrals by Term',
        color=term_counts.values,
        color_continuous_scale='Viridis',
        text=term_counts.values
    )
    fig_terms.update_traces(textposition='outside')
    fig_terms.update_layout(
        showlegend=False,
        height=400,
        xaxis_title="Term",
        yaxis_title="Number of Referrals"
    )
    st.plotly_chart(fig_terms, use_container_width=True)
    
    st.markdown("#### 🔍 Drill Down into Specific Term")
    selected_term_drill = st.selectbox(
        "Select a term to see detailed breakdown:",
        [''] + ['Term 1', 'Term 2', 'Term 3', 'Term 4'],
        key="term_drill"
    )
    
    if selected_term_drill:
        term_detail_df = filtered_df[filtered_df['term'] == selected_term_drill]
        
        if len(term_detail_df) > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Total Referrals", len(term_detail_df))
            
            with col2:
                allocated_term = len(term_detail_df[term_detail_df['status'] == 'Allocated'])
                st.metric("✅ Allocated", allocated_term)
            
            with col3:
                unique_schools = term_detail_df['school'].nunique()
                st.metric("🏫 Unique Schools", unique_schools)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**🤝 Partnerships in {selected_term_drill}:**")
                partnership_term = term_detail_df[term_detail_df['partnership'] != '']['partnership'].value_counts()
                if len(partnership_term) > 0:
                    fig_pt = px.pie(
                        values=partnership_term.values,
                        names=partnership_term.index,
                        title=f'Partnership Distribution',
                        color_discrete_sequence=px.colors.sequential.Teal
                    )
                    st.plotly_chart(fig_pt, use_container_width=True)
                else:
                    st.info("No partnership data for this term")
            
            with col2:
                st.markdown(f"**📚 Programs in {selected_term_drill}:**")
                program_term = term_detail_df['program'].value_counts()
                fig_prg = px.pie(
                    values=program_term.values,
                    names=program_term.index,
                    title=f'Program Distribution',
                    color_discrete_sequence=px.colors.sequential.Oranges
                )
                st.plotly_chart(fig_prg, use_container_width=True)
            
            st.markdown(f"**🏫 Top Referring Schools in {selected_term_drill}:**")
            top_schools = term_detail_df['school'].value_counts().head(10).reset_index()
            top_schools.columns = ['School', 'Referrals']
            
            fig_top = px.bar(
                top_schools,
                x='School',
                y='Referrals',
                color='Referrals',
                color_continuous_scale='Blues',
                text='Referrals'
            )
            fig_top.update_traces(textposition='outside')
            fig_top.update_layout(
                showlegend=False,
                height=350,
                xaxis_title="School",
                yaxis_title="Number of Referrals"
            )
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info(f"No data available for {selected_term_drill}")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 4: PROGRAM BREAKDOWN
# ──────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 🎨 Program-Level Analysis")
    
    program_counts = filtered_df['program'].value_counts().reset_index()
    program_counts.columns = ['Program', 'Count']
    
    fig_prog_main = px.bar(
        program_counts,
        x='Program',
        y='Count',
        title='Students by Program Level',
        color='Count',
        color_continuous_scale='Plasma',
        text='Count'
    )
    fig_prog_main.update_traces(textposition='outside')
    fig_prog_main.update_layout(
        showlegend=False,
        height=400,
        xaxis_title="Program",
        yaxis_title="Number of Students"
    )
    st.plotly_chart(fig_prog_main, use_container_width=True)
    
    st.markdown("#### 🔍 Drill Down into Specific Program")
    selected_program_drill = st.selectbox(
        "Select a program to see detailed breakdown:",
        [''] + program_counts['Program'].tolist(),
        key="program_drill"
    )
    
    if selected_program_drill:
        program_detail_df = filtered_df[filtered_df['program'] == selected_program_drill]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Total Students", len(program_detail_df))
        
        with col2:
            unique_schools_prog = program_detail_df['school'].nunique()
            st.metric("🏫 Referring Schools", unique_schools_prog)
        
        with col3:
            partnership_students = len(program_detail_df[program_detail_df['partnership'] != ''])
            st.metric("🤝 Partnership Students", partnership_students)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**🏫 Schools in {selected_program_drill}:**")
            schools_prog = program_detail_df['school'].value_counts().head(10)
            fig_sch = px.bar(
                y=schools_prog.index,
                x=schools_prog.values,
                orientation='h',
                color=schools_prog.values,
                color_continuous_scale='Teal',
                text=schools_prog.values
            )
            fig_sch.update_traces(textposition='outside')
            fig_sch.update_layout(
                showlegend=False,
                height=400,
                yaxis_title="School",
                xaxis_title="Students"
            )
            st.plotly_chart(fig_sch, use_container_width=True)
        
        with col2:
            st.markdown(f"**🤝 Partnerships in {selected_program_drill}:**")
            partnerships_prog = program_detail_df[program_detail_df['partnership'] != '']['partnership'].value_counts()
            
            if len(partnerships_prog) > 0:
                fig_part = px.pie(
                    values=partnerships_prog.values,
                    names=partnerships_prog.index,
                    color_discrete_sequence=px.colors.sequential.Oranges
                )
                st.plotly_chart(fig_part, use_container_width=True)
            else:
                st.info("No partnership data for this program")
        
        st.markdown(f"**🏷️ Support Needs Profile for {selected_program_drill}:**")
        
        flag_data_prog = {
            'SWD': (program_detail_df['swd'] == 'Yes').sum(),
            'DCP': (program_detail_df['dcp'] == 'Yes').sum(),
            'Aboriginal': (program_detail_df['aboriginal'] == 'Yes').sum(),
            'EALD': (program_detail_df['eald'] == 'Yes').sum()
        }
        
        fig_flags_prog = px.bar(
            x=list(flag_data_prog.keys()),
            y=list(flag_data_prog.values()),
            color=list(flag_data_prog.values()),
            color_continuous_scale='RdYlGn_r',
            text=list(flag_data_prog.values())
        )
        fig_flags_prog.update_traces(textposition='outside')
        fig_flags_prog.update_layout(
            showlegend=False,
            height=350,
            xaxis_title="Support Flag",
            yaxis_title="Number of Students"
        )
        st.plotly_chart(fig_flags_prog, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 5: NON-TYPICAL PLACEMENTS
# ──────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown("### ⚠️ Students in Non-Typical Program Placements")
    
    st.markdown("""
    <div class="info-box">
    <strong>ℹ️ About Non-Typical Placements:</strong><br>
    These students are placed in a program level that doesn't match their year level. This may be appropriate based on 
    individual needs, developmental considerations, or transition planning. This view helps identify and monitor these cases.
    </div>
    """, unsafe_allow_html=True)
    
    mismatch_df = filtered_df[filtered_df['program_mismatch'] == True].copy()
    
    if len(mismatch_df) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("⚠️ Non-Typical Placements", len(mismatch_df))
        
        with col2:
            mismatch_pct = (len(mismatch_df) / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            st.metric("📊 Percentage of Cohort", f"{mismatch_pct:.1f}%")
        
        with col3:
            unique_schools_mismatch = mismatch_df['school'].nunique()
            st.metric("🏫 Schools Involved", unique_schools_mismatch)
        
        st.markdown("#### 📋 Placement Details")
        
        mismatch_summary = mismatch_df.groupby(['year_level', 'expected_program', 'program']).size().reset_index(name='count')
        mismatch_summary = mismatch_summary.sort_values('count', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔄 Mismatch Patterns:**")
            
            for _, row in mismatch_summary.iterrows():
                st.markdown(f"""
                <div style="background: #FFF9E6; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #C8760A;">
                    <strong>Year {row['year_level']}</strong><br>
                    Expected: <span style="color: #1A7A6E;">{row['expected_program']}</span><br>
                    Actual: <span style="color: #C8760A;">{row['program']}</span><br>
                    Count: <strong>{row['count']}</strong> student(s)
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**📊 Programs with Non-Typical Students:**")
            
            program_mismatch_counts = mismatch_df['program'].value_counts()
            
            fig_mismatch = px.bar(
                x=program_mismatch_counts.index,
                y=program_mismatch_counts.values,
                color=program_mismatch_counts.values,
                color_continuous_scale='Oranges',
                text=program_mismatch_counts.values
            )
            fig_mismatch.update_traces(textposition='outside')
            fig_mismatch.update_layout(
                showlegend=False,
                height=350,
                xaxis_title="Program",
                yaxis_title="Non-Typical Placements"
            )
            st.plotly_chart(fig_mismatch, use_container_width=True)
        
        st.markdown("#### 📋 Individual Student Records")
        
        mismatch_display = mismatch_df[[
            'record_id', 'school', 'year_level', 'expected_program', 'program', 
            'term', 'swd', 'dcp', 'aboriginal', 'eald'
        ]].copy()
        
        mismatch_display.columns = [
            'Record ID', 'School', 'Year Level', 'Expected Program', 'Actual Program',
            'Term', 'SWD', 'DCP', 'Aboriginal', 'EALD'
        ]
        
        st.dataframe(
            mismatch_display,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("#### 💡 Support Needs Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏷️ Support Flags in Non-Typical Placements:**")
            
            flag_counts_mismatch = {
                'SWD': (mismatch_df['swd'] == 'Yes').sum(),
                'DCP': (mismatch_df['dcp'] == 'Yes').sum(),
                'Aboriginal': (mismatch_df['aboriginal'] == 'Yes').sum(),
                'EALD': (mismatch_df['eald'] == 'Yes').sum()
            }
            
            fig_flags_mismatch = px.bar(
                x=list(flag_counts_mismatch.keys()),
                y=list(flag_counts_mismatch.values()),
                color=list(flag_counts_mismatch.values()),
                color_continuous_scale='RdYlGn_r',
                text=list(flag_counts_mismatch.values())
            )
            fig_flags_mismatch.update_traces(textposition='outside')
            fig_flags_mismatch.update_layout(
                showlegend=False,
                height=300,
                xaxis_title="Support Flag",
                yaxis_title="Count"
            )
            st.plotly_chart(fig_flags_mismatch, use_container_width=True)
        
        with col2:
            st.markdown("**🏫 Schools with Non-Typical Placements:**")
            
            school_mismatch = mismatch_df['school'].value_counts().head(8)
            
            fig_school_mismatch = px.bar(
                y=school_mismatch.index,
                x=school_mismatch.values,
                orientation='h',
                color=school_mismatch.values,
                color_continuous_scale='Oranges',
                text=school_mismatch.values
            )
            fig_school_mismatch.update_traces(textposition='outside')
            fig_school_mismatch.update_layout(
                showlegend=False,
                height=300,
                yaxis_title="School",
                xaxis_title="Count"
            )
            st.plotly_chart(fig_school_mismatch, use_container_width=True)
        
        st.markdown("#### 📥 Export Non-Typical Placements Data")
        
        csv_mismatch = mismatch_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Non-Typical Placements Report (CSV)",
            data=csv_mismatch,
            file_name=f"non_typical_placements_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    else:
        st.success("✅ All students are placed in their expected year-level program.")
        st.markdown("""
        <div class="info-box">
        <strong>Great news!</strong> Based on the current filters, all students are in programs that match their year level:
        <ul>
            <li><strong>Junior Primary (R-1):</strong> Reception and Year 1 students</li>
            <li><strong>Primary Years (3-6):</strong> Year 3-6 students</li>
            <li><strong>Senior Years (7-10):</strong> Year 7-10 students</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 6: PLACEMENT HISTORY (Returning vs First-Time Students)
# ──────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown("### 🔄 Placement History Analysis")
    
    st.markdown("""
    <div class="info-box">
    <strong>ℹ️ About Placement History:</strong><br>
    This view shows which students are returning to CLC for additional support vs. first-time placements.
    Returning students have had previous CLC placements, indicating ongoing support needs or successful re-engagement.
    </div>
    """, unsafe_allow_html=True)
    
    # Count returning vs first-time
    returning_students = filtered_df[filtered_df['prev_clc'] == 'Yes']
    firsttime_students = filtered_df[filtered_df['prev_clc'] == 'No']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🔄 Returning Students", len(returning_students))
    
    with col2:
        st.metric("🆕 First-Time Students", len(firsttime_students))
    
    with col3:
        returning_pct = (len(returning_students) / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.metric("📊 Returning %", f"{returning_pct:.1f}%")
    
    # Breakdown by program
    st.markdown("#### 📊 Returning vs First-Time by Program")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart of returning vs first-time
        placement_status_counts = filtered_df['prev_clc'].value_counts()
        placement_status_labels = placement_status_counts.index.map({'Yes': 'Returning Students', 'No': 'First-Time Students'})
        
        fig_status = px.pie(
            values=placement_status_counts.values,
            names=placement_status_labels,
            title='Overall Placement History',
            color_discrete_sequence=['#C8760A', '#1A7A6E']
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        # Bar chart by program
        program_history = filtered_df.groupby(['program', 'prev_clc']).size().unstack(fill_value=0)
        
        # Handle cases where only one type exists (all first-time or all returning)
        # Rename columns based on what actually exists
        column_mapping = {'No': 'First-Time', 'Yes': 'Returning'}
        program_history.columns = [column_mapping.get(col, col) for col in program_history.columns]
        
        # Ensure both columns exist for stacked bar chart
        if 'First-Time' not in program_history.columns:
            program_history['First-Time'] = 0
        if 'Returning' not in program_history.columns:
            program_history['Returning'] = 0
        
        # Reorder columns
        program_history = program_history[['First-Time', 'Returning']]
        
        fig_program_hist = go.Figure()
        
        fig_program_hist.add_trace(go.Bar(
            name='First-Time',
            x=program_history.index,
            y=program_history['First-Time'],
            marker_color='#1A7A6E'
        ))
        
        fig_program_hist.add_trace(go.Bar(
            name='Returning',
            x=program_history.index,
            y=program_history['Returning'],
            marker_color='#C8760A'
        ))
        
        fig_program_hist.update_layout(
            title='Placement History by Program',
            barmode='stack',
            height=350,
            xaxis_title="Program",
            yaxis_title="Number of Students"
        )
        
        st.plotly_chart(fig_program_hist, use_container_width=True)
    
    # Detailed breakdown
    if len(returning_students) > 0:
        st.markdown("#### 🔄 Returning Students Detail")
        
        returning_by_program = returning_students['program'].value_counts()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**Programs with Returning Students:**")
            for program, count in returning_by_program.items():
                st.markdown(f"""
                <div style="background: #FFF9E6; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #C8760A;">
                    <strong>{program}:</strong> {count} returning student(s)
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Support Needs Profile:**")
            returning_swd = (returning_students['swd'] == 'Yes').sum()
            returning_dcp = (returning_students['dcp'] == 'Yes').sum()
            
            st.metric("SWD", returning_swd)
            st.metric("DCP", returning_dcp)
        
        st.markdown("**📋 Returning Students List:**")
        returning_display = returning_students[[
            'record_id', 'school', 'program', 'year_level', 'term', 
            'swd', 'dcp', 'aboriginal', 'eald'
        ]].copy()
        
        returning_display.columns = [
            'Student ID', 'School', 'Program', 'Year', 'Term',
            'SWD', 'DCP', 'Aboriginal', 'EALD'
        ]
        
        st.dataframe(
            returning_display,
            use_container_width=True,
            hide_index=True,
            height=300
        )
        
        # Export option
        csv_returning = returning_students.to_csv(index=False)
        st.download_button(
            label="📥 Download Returning Students Report (CSV)",
            data=csv_returning,
            file_name=f"returning_students_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("✅ No returning students in current filtered view. All students are first-time placements.")
    
    # Schools with most returning students
    if len(returning_students) > 0:
        st.markdown("#### 🏫 Schools with Returning Students")
        
        returning_schools = returning_students['school'].value_counts().head(10)
        
        fig_schools_returning = px.bar(
            y=returning_schools.index,
            x=returning_schools.values,
            orientation='h',
            color=returning_schools.values,
            color_continuous_scale='Oranges',
            text=returning_schools.values
        )
        fig_schools_returning.update_traces(textposition='outside')
        fig_schools_returning.update_layout(
            title='Schools Referring Returning Students',
            showlegend=False,
            height=max(300, len(returning_schools) * 40),
            yaxis_title="School",
            xaxis_title="Number of Returning Students"
        )
        st.plotly_chart(fig_schools_returning, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 7: WAITLIST & NON-PLACED STUDENTS
# ──────────────────────────────────────────────────────────────────────────────
with tab7:
    st.markdown("### ⏳ Waitlist & Non-Placed Students Tracking")
    
    st.markdown("""
    <div class="info-box">
    <strong>ℹ️ About Waitlist Tracking:</strong><br>
    This view tracks students awaiting placement at CLC. When a school refers a student but no space is available, 
    schools can choose to join the waitlist or decline. This system tracks wait times, conversions to placements, 
    and provides visibility into unmet demand.
    </div>
    """, unsafe_allow_html=True)
    
    # Calculate waitlist metrics
    waitlist_students = filtered_df[filtered_df.get('waitlist_status', '') == 'On Waitlist'].copy()
    declined_students = filtered_df[filtered_df.get('waitlist_status', '') == 'Declined'].copy()
    allocated_from_waitlist = filtered_df[filtered_df.get('allocated_from_waitlist', '') == 'Yes'].copy()
    
    # Calculate days waiting for current waitlist
    if len(waitlist_students) > 0 and 'waitlist_date' in waitlist_students.columns:
        waitlist_students['waitlist_date_parsed'] = pd.to_datetime(waitlist_students['waitlist_date'], errors='coerce')
        today = pd.Timestamp.now()
        waitlist_students['days_waiting'] = (today - waitlist_students['waitlist_date_parsed']).dt.days
        waitlist_students['days_waiting'] = waitlist_students['days_waiting'].fillna(0).astype(int)
        avg_wait = waitlist_students['days_waiting'].mean() if len(waitlist_students) > 0 else 0
        longest_wait = waitlist_students['days_waiting'].max() if len(waitlist_students) > 0 else 0
    else:
        avg_wait = 0
        longest_wait = 0
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("⏳ On Waitlist", len(waitlist_students))
    
    with col2:
        st.metric("❌ Declined", len(declined_students))
    
    with col3:
        st.metric("📊 Avg Wait (Days)", f"{avg_wait:.0f}")
    
    with col4:
        st.metric("⚠️ Longest Wait (Days)", longest_wait)
    
    if len(waitlist_students) > 0:
        st.markdown("#### 📊 Current Waitlist Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Waitlist by program
            st.markdown("**Waitlist by Program:**")
            waitlist_program = waitlist_students['program'].value_counts()
            
            fig_wait_prog = px.bar(
                x=waitlist_program.index,
                y=waitlist_program.values,
                color=waitlist_program.values,
                color_continuous_scale='Reds',
                text=waitlist_program.values,
                title='Students Waiting by Program'
            )
            fig_wait_prog.update_traces(textposition='outside')
            fig_wait_prog.update_layout(
                showlegend=False,
                height=350,
                xaxis_title="Program",
                yaxis_title="Students Waiting"
            )
            st.plotly_chart(fig_wait_prog, use_container_width=True)
        
        with col2:
            # Waitlist by year level
            st.markdown("**Waitlist by Year Level:**")
            waitlist_year = waitlist_students['year_level'].value_counts().sort_index()
            
            fig_wait_year = px.bar(
                x=waitlist_year.index,
                y=waitlist_year.values,
                color=waitlist_year.values,
                color_continuous_scale='Oranges',
                text=waitlist_year.values,
                title='Students Waiting by Year Level'
            )
            fig_wait_year.update_traces(textposition='outside')
            fig_wait_year.update_layout(
                showlegend=False,
                height=350,
                xaxis_title="Year Level",
                yaxis_title="Students Waiting"
            )
            st.plotly_chart(fig_wait_year, use_container_width=True)
        
        # Schools with waitlist students
        st.markdown("**🏫 Schools with Students on Waitlist:**")
        waitlist_schools = waitlist_students['school'].value_counts().head(10)
        
        fig_wait_schools = px.bar(
            y=waitlist_schools.index,
            x=waitlist_schools.values,
            orientation='h',
            color=waitlist_schools.values,
            color_continuous_scale='Reds',
            text=waitlist_schools.values,
            title='Top Schools by Waitlist Count'
        )
        fig_wait_schools.update_traces(textposition='outside')
        fig_wait_schools.update_layout(
            showlegend=False,
            height=max(300, len(waitlist_schools) * 40),
            yaxis_title="School",
            xaxis_title="Students Waiting"
        )
        st.plotly_chart(fig_wait_schools, use_container_width=True)
        
        # Current waitlist table
        st.markdown("#### 📋 Current Waitlist Details")
        
        waitlist_display = waitlist_students[[
            'record_id', 'school', 'year_level', 'program', 'partnership',
            'waitlist_date', 'days_waiting', 'swd', 'dcp'
        ]].copy()
        
        waitlist_display.columns = [
            'Student ID', 'School', 'Year', 'Program', 'Partnership',
            'Waitlist Date', 'Days Waiting', 'SWD', 'DCP'
        ]
        
        waitlist_display['Waitlist Date'] = pd.to_datetime(waitlist_display['Waitlist Date']).dt.strftime('%d/%m/%Y')
        waitlist_display = waitlist_display.sort_values('Days Waiting', ascending=False)
        
        st.dataframe(
            waitlist_display,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Export waitlist
        csv_waitlist = waitlist_students.to_csv(index=False)
        st.download_button(
            label="📥 Download Waitlist Report (CSV)",
            data=csv_waitlist,
            file_name=f"waitlist_students_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.success("✅ No students currently on waitlist!")
    
    # Waitlist Success Stories
    if len(allocated_from_waitlist) > 0:
        st.markdown("#### ✅ Waitlist Success Stories")
        st.markdown("""
        <div style="background: #D4EDDA; padding: 1rem; border-radius: 8px; border-left: 4px solid #28A745; margin: 1rem 0;">
        <strong>{} students</strong> were successfully allocated after being on the waitlist!
        </div>
        """.format(len(allocated_from_waitlist)), unsafe_allow_html=True)
        
        # Calculate wait times for allocated students
        if 'waitlist_date' in allocated_from_waitlist.columns and 'placement_start' in allocated_from_waitlist.columns:
            allocated_from_waitlist['waitlist_date_parsed'] = pd.to_datetime(allocated_from_waitlist['waitlist_date'], errors='coerce')
            allocated_from_waitlist['placement_start_parsed'] = pd.to_datetime(allocated_from_waitlist['placement_start'], errors='coerce')
            allocated_from_waitlist['wait_duration'] = (
                allocated_from_waitlist['placement_start_parsed'] - allocated_from_waitlist['waitlist_date_parsed']
            ).dt.days
            allocated_from_waitlist['wait_duration'] = allocated_from_waitlist['wait_duration'].fillna(0).astype(int)
            
            avg_wait_before_allocation = allocated_from_waitlist['wait_duration'].mean() if len(allocated_from_waitlist) > 0 else 0
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("📊 Average Wait Before Allocation", f"{avg_wait_before_allocation:.0f} days")
            
            with col2:
                st.metric("✅ Waitlist→Allocated Success Rate", 
                         f"{len(allocated_from_waitlist)}/{len(allocated_from_waitlist) + len(waitlist_students)}")
            
            # Show allocated students
            allocated_display = allocated_from_waitlist[[
                'record_id', 'school', 'year_level', 'program',
                'waitlist_date', 'placement_start', 'wait_duration'
            ]].copy()
            
            allocated_display.columns = [
                'Student ID', 'School', 'Year', 'Program',
                'Waitlist Date', 'Allocated Date', 'Days Waited'
            ]
            
            allocated_display['Waitlist Date'] = pd.to_datetime(allocated_display['Waitlist Date']).dt.strftime('%d/%m/%Y')
            allocated_display['Allocated Date'] = pd.to_datetime(allocated_display['Allocated Date']).dt.strftime('%d/%m/%Y')
            
            st.dataframe(
                allocated_display,
                use_container_width=True,
                hide_index=True,
                height=300
            )
    
    # Declined students summary
    if len(declined_students) > 0:
        st.markdown("#### ❌ Declined Placements")
        
        col1, col2 = st.columns(2)
        
        with col1:
            declined_program = declined_students['program'].value_counts()
            fig_declined = px.pie(
                values=declined_program.values,
                names=declined_program.index,
                title='Declined by Program',
                color_discrete_sequence=px.colors.sequential.Greys
            )
            st.plotly_chart(fig_declined, use_container_width=True)
        
        with col2:
            declined_schools = declined_students['school'].value_counts().head(5)
            st.markdown("**Top Schools (Declined):**")
            for school, count in declined_schools.items():
                st.markdown(f"• **{school}:** {count} student(s)")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY STATISTICS TABLE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📋 Complete Allocation Summary</div>', unsafe_allow_html=True)

display_df = filtered_df[['record_id', 'school', 'year_level', 'program', 'expected_program', 'program_mismatch', 'partnership', 'term', 'status']].copy()
display_df.columns = ['Record ID', 'Referring School', 'Year', 'Program', 'Expected Program', 'Non-Typical', 'Partnership', 'Term', 'Status']

display_df['Non-Typical'] = display_df['Non-Typical'].apply(lambda x: '⚠️ Yes' if x else '✓ Match')

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=400,
    column_config={
        "Non-Typical": st.column_config.TextColumn(
            "Non-Typical",
            help="Indicates if student is placed in a program different from their year level",
        )
    }
)

csv = filtered_df.to_csv(index=False)
st.download_button(
    label="📥 Download Filtered Data (CSV)",
    data=csv,
    file_name=f"allocation_data_{selected_term}_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

# ══════════════════════════════════════════════════════════════════════════════
# INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">💡 Key Insights</div>', unsafe_allow_html=True)

# Show current academic year context
current_year = datetime.now().year
academic_year = f"{current_year}"
st.info(f"📅 **Academic Year Context:** Data calculated for {academic_year}. Year levels and ages are current as of {datetime.now().strftime('%B %Y')}.")

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div class="info-box">
    <strong>Student Complexity:</strong><br>
    • High prevalence of students with disabilities requiring specialized support<br>
    • Multiple co-occurring needs across cohort<br>
    • Focus on trauma-informed, neurodiversity-affirming practice<br>
    • {len(filtered_df[filtered_df['program_mismatch'] == True])} student(s) in non-typical year-level placements
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-box">
    <strong>Program Structure:</strong><br>
    • <strong>Junior Primary (R-1):</strong> Reception to Year 1 students<br>
    • <strong>Primary Years (3-6):</strong> Year 3 to Year 6 students<br>
    • <strong>Senior Years (7-10):</strong> Year 7 to Year 10 students<br>
    • Non-typical placements monitored for appropriate support
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p style="font-size: 0.9rem;">📊 Integrated Allocation Dashboard | Cowandilla Learning Centre LBU</p>
    <p style="font-size: 0.85rem; color: #1A7A6E; font-weight: 600;">
        🔄 Live Data • Auto-refresh 60s • Privacy Protected • Built-in Sync
    </p>
</div>
""", unsafe_allow_html=True)
