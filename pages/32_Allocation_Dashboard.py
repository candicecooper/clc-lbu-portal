import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import folium
from streamlit_folium import st_folium
from collections import Counter
from supabase import create_client
import os

st.set_page_config(page_title="CLC Allocation Dashboard - Interactive", page_icon="📊", layout="wide")

# Custom CSS for professional appearance
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
        height: 80px;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        transform: translateY(-2px);
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2c3e50;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
    }
    .drill-down-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .drill-down-title {
        color: white;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .drill-down-subtitle {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 1.2rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 style="text-align: center; color: #2c3e50; font-size: 2.5rem; margin-bottom: 0;">📊 CLC Allocation Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #7f8c8d; font-size: 1.2rem; margin-top: 0;">Interactive Analytics & Deep Dive</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE CONNECTION (Direct - no database.py import)
# ══════════════════════════════════════════════════════════════════════════════

# Check credentials first (before caching)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY environment variables in Render.")
    st.stop()

@st.cache_resource
def init_supabase():
    """Initialize Supabase client - cached to avoid reconnecting"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)  # Cache for 60 seconds, then refresh
def load_allocation_data():
    """Load allocation data from Supabase - refreshes every 60 seconds"""
    supabase = init_supabase()
    
    # Fetch all records from allocation_tracker table
    response = supabase.table('allocation_tracker').select('*').execute()
    
    if not response.data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    return pd.DataFrame(response.data)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
try:
    df_raw = load_allocation_data()
except Exception as e:
    st.error(f"❌ Error loading data from Supabase: {str(e)}")
    st.info("""
    **Troubleshooting:**
    1. Check that SUPABASE_URL and SUPABASE_KEY are set in Render
    2. Verify the allocation_tracker table exists in Supabase
    3. Try syncing data from the main Allocation Dashboard (page 32)
    """)
    st.stop()

if len(df_raw) == 0:
    st.info("""
    📭 **No allocation data in dashboard yet.**
    
    **To get started:**
    1. Go to the main Allocation Dashboard (page 32)
    2. Click "🔧 ADMIN: Sync Data from Excel"
    3. Upload your allocation Excel file
    4. Click "Sync to Dashboard"
    5. Return here - data will be available!
    """)
    st.stop()

# Create working copy and process data
df = df_raw.copy()

# Map Supabase column names to dashboard expected names
column_mapping = {
    'partnership_area': 'partnership',
    'allocated_program': 'program',
    'referral_term': 'term',
    'allocation_status': 'current_status'
}

# Apply mappings if source columns exist
for supabase_col, dashboard_col in column_mapping.items():
    if supabase_col in df.columns and dashboard_col not in df.columns:
        df[dashboard_col] = df[supabase_col]

# Extract year from referral_year or referral_date
if 'referral_year' in df.columns:
    df['year'] = df['referral_year'].fillna(datetime.now().year).astype(int)
elif 'referral_date' in df.columns:
    df['referral_date'] = pd.to_datetime(df['referral_date'], errors='coerce')
    df['year'] = df['referral_date'].dt.year.fillna(datetime.now().year).astype(int)
    df['month'] = df['referral_date'].dt.month
else:
    df['year'] = datetime.now().year

# Calculate term from month (like old dashboard) - DO THIS BEFORE required columns check
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
    except:
        return "Unknown"

# Only calculate term if not already present
if 'term' not in df.columns or df['term'].isna().all():
    if 'month' in df.columns:
        df['term'] = df['month'].apply(get_term)
    else:
        df['term'] = 'Unknown'

# Ensure required columns exist (add with safe defaults if still missing)
required_columns = {
    'partnership': '',
    'program': 'Unknown',
    'year_level': 'Unknown',
    'student_name': 'Student',
    'referring_school': 'Unknown School',
    'current_status': 'Unknown'
}

for col, default_value in required_columns.items():
    if col not in df.columns:
        df[col] = default_value
        st.warning(f"⚠️ Column '{col}' not found in data - using default values")

# Process bespoke placement - case insensitive
if 'bespoke_placement' in df.columns:
    df['program_mismatch'] = df['bespoke_placement'].fillna('').astype(str).str.lower().map({
        'yes': True, 'y': True, '1': True, 'true': True,
        'no': False, 'n': False, '0': False, 'false': False, '': False
    }).fillna(False)
else:
    df['program_mismatch'] = False

# Show last update
st.caption(f"📅 Last updated: {datetime.now().strftime('%d/%m/%Y %I:%M %p')} | Total records: {len(df)}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN SECTION: DATA SYNC
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("🔧 **ADMIN: Sync Data from Excel**", expanded=False):
    st.markdown("""
    **🔒 Privacy-Preserving Sync**  
    Upload your allocation Excel file to update the dashboard. **Student names are automatically removed** during sync.
    """)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload Allocation Excel File",
            type=['xlsx', 'xlsm'],
            help="CLC_Allocation_Dashboard Excel file - student names will NOT be synced",
            key="excel_upload_interactive"
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
            
            st.info(f"📄 **Excel file read:** {len(df_excel)} rows")
            
            # Map Excel columns to Supabase schema (copy from old dashboard)
            status_text.text(f"Processing {len(df_excel)} student records...")
            progress_bar.progress(20)
            
            sync_df = pd.DataFrame()
            
            column_mapping = {
                'Student_ID': 'student_id',
                'Gender': 'gender',
                'Year_Level': 'year_level',
                'Referring_School': 'referring_school',
                'Referral_Date': 'referral_date',
                'Referral_Year': 'referral_year',
                'Allocation_Status': 'allocation_status',
                'Allocated_Program': 'allocated_program',
                'Placement_Start': 'placement_start',
                'Placement_End': 'placement_end',
                'Exclusion_End_Date': 'exclusion_end_date',
                'Actual_Finish_Date': 'actual_finish_date',
                'Extended_Placement': 'extended_placement',
                'Partnership_Area': 'partnership_area',
                'Previous_CLC_Placement': 'previous_clc_placement',
                'Flag_ASD': 'flag_asd',
                'Flag_ADHD': 'flag_adhd',
                'Flag_DCP_involvement': 'flag_dcp_involvement',
                'Flag_Child_in_care': 'flag_child_in_care',
                'Flag_Aboriginal': 'flag_aboriginal',
                'Flag_ATSI': 'flag_aboriginal',
                'Flag_EALD': 'flag_eald',
                'Bespoke_Placement': 'bespoke_placement',
                'Current_Status': 'current_status',
                'Notes': 'notes'
            }
            
            # Map columns
            for excel_col, db_col in column_mapping.items():
                if excel_col in df_excel.columns:
                    sync_df[db_col] = df_excel[excel_col]
            
            # Convert Yes/No to boolean for flags
            flag_columns = ['flag_asd', 'flag_adhd', 'flag_dcp_involvement', 'flag_child_in_care',
                          'flag_aboriginal', 'flag_eald', 'bespoke_placement', 'extended_placement']
            
            for flag_col in flag_columns:
                if flag_col in sync_df.columns:
                    sync_df[flag_col] = sync_df[flag_col].map({'Yes': True, 'No': False, '': False}).fillna(False)
            
            # Convert dates
            date_columns = ['referral_date', 'placement_start', 'placement_end']
            for date_col in date_columns:
                if date_col in sync_df.columns:
                    sync_df[date_col] = pd.to_datetime(sync_df[date_col], errors='coerce')
                    sync_df[date_col] = sync_df[date_col].dt.strftime('%Y-%m-%d')
            
            # Convert integers
            int_columns = ['referral_year']
            for int_col in int_columns:
                if int_col in sync_df.columns:
                    sync_df[int_col] = pd.to_numeric(sync_df[int_col], errors='coerce').fillna(0).astype(int)
            
            # Clean NaNs
            sync_df = sync_df.replace({float('nan'): None, 'nan': None, 'NaT': None})
            
            # Validate required fields
            records = sync_df.to_dict('records')
            
            for record in records:
                if not record.get('allocation_status'):
                    record['allocation_status'] = 'Allocated'
            
            # Clear old data
            status_text.text("Clearing old dashboard data...")
            progress_bar.progress(50)
            supabase = init_supabase()
            supabase.table('allocation_tracker').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            
            # Insert new data
            status_text.text(f"Uploading {len(records)} de-identified records...")
            progress_bar.progress(60)
            
            # Insert in batches
            batch_size = 50
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                supabase.table('allocation_tracker').insert(batch).execute()
                progress_bar.progress(60 + int(30 * ((i + len(batch)) / len(records))))
            
            # Clear cache
            load_allocation_data.clear()
            
            # Complete
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            st.success(f"""
            ✅ **Sync Successful!** {len(records)} records synced to dashboard.
            
            **Privacy Status:** ✅ No student names were transmitted or stored in database.
            
            Dashboard will refresh now...
            """)
            
            # Force page rerun
            st.rerun()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Sync failed: {str(e)}")
            st.exception(e)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔍 Filters</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 2, 2, 1.5])

with col1:
    years = ['All Years'] + sorted([int(y) for y in df['year'].unique() if pd.notna(y)], reverse=True)
    year_index = years.index(2026) if 2026 in years else 0
    selected_year = st.selectbox("📅 Year", years, index=year_index, key="year_filter")

with col2:
    if 'term' in df.columns:
        terms = ['All Terms'] + sorted([t for t in df['term'].unique() if pd.notna(t)])
    else:
        terms = ['All Terms']
    selected_term = st.selectbox("🗓️ Term", terms, key="term_filter")

with col3:
    statuses = ['Active Only', 'All Statuses', 'Inactive Only', 'Pending Only']
    selected_status = st.selectbox("📊 Status", statuses, index=0, key="status_filter")

with col4:
    if 'partnership' in df.columns:
        partnerships = ['All Partnerships'] + sorted([p for p in df['partnership'].unique() if p != '' and pd.notna(p)])
    else:
        partnerships = ['All Partnerships']
    selected_partnership = st.selectbox("🤝 Partnership", partnerships, key="partnership_filter")

with col5:
    if 'program' in df.columns:
        programs = ['All Programs'] + sorted([p for p in df['program'].unique() if pd.notna(p)])
    else:
        programs = ['All Programs']
    selected_program = st.selectbox("📚 Program", programs, key="program_filter")

# Apply filters
filtered_df = df.copy()

if selected_year != 'All Years':
    filtered_df = filtered_df[filtered_df['year'] == selected_year]

if selected_term != 'All Terms' and 'term' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['term'] == selected_term]

# Apply status filter
if 'current_status' in filtered_df.columns:
    if selected_status == 'Active Only':
        filtered_df = filtered_df[filtered_df['current_status'].fillna('').astype(str).str.lower() == 'active']
    elif selected_status == 'Inactive Only':
        filtered_df = filtered_df[filtered_df['current_status'].fillna('').astype(str).str.lower() == 'inactive']
    elif selected_status == 'Pending Only':
        filtered_df = filtered_df[filtered_df['current_status'].fillna('').astype(str).str.lower() == 'pending']

if selected_partnership != 'All Partnerships' and 'partnership' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['partnership'] == selected_partnership]

if selected_program != 'All Programs' and 'program' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['program'] == selected_program]

# Show filter status
active_filters = []
if selected_year != 'All Years':
    active_filters.append(f"**{selected_year}**")
if selected_term != 'All Terms':
    active_filters.append(f"**{selected_term}**")
if selected_status != 'All Statuses':
    active_filters.append(f"**{selected_status}**")
if selected_partnership != 'All Partnerships':
    active_filters.append(f"**{selected_partnership}**")
if selected_program != 'All Programs':
    active_filters.append(f"**{selected_program}**")

if active_filters:
    st.info(f"🔎 Showing: {' • '.join(active_filters)} | {len(filtered_df)} of {len(df)} records")

# Warning for partial year data
if selected_year == 2026:
    st.warning("⚠️ **2026 Data is Partial Year** (Terms 1-2 only). Percentages reflect current cohort.")
elif selected_year == 'All Years' and len(df['year'].unique()) > 1:
    st.warning("⚠️ **Multi-Year View**: Comparing full year with partial year data.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE METRICS - CLICK TO DRILL DOWN
# ══════════════════════════════════════════════════════════════════════════════

# Initialize session state
if 'drill_down_view' not in st.session_state:
    st.session_state.drill_down_view = None

# Calculate metrics
total_referrals = len(filtered_df)

# Allocated count
if 'allocation_status' in filtered_df.columns:
    allocated_count = len(filtered_df[filtered_df['allocation_status'].fillna('').astype(str).str.lower().isin(['allocated', 'active'])])
elif 'current_status' in filtered_df.columns:
    allocated_count = len(filtered_df[filtered_df['current_status'].fillna('').astype(str).str.lower() == 'active'])
else:
    allocated_count = 0

# Non-typical count
mismatch_count = len(filtered_df[filtered_df['program_mismatch'] == True])

# SWD count
disability_cols = ['flag_asd', 'flag_adhd', 'flag_intellectual', 'flag_learning_difficulty', 'flag_sensory_processing', 'flag_odd', 'flag_pda']
available_disability_cols = [col for col in disability_cols if col in filtered_df.columns]
if available_disability_cols:
    swd_mask = filtered_df[available_disability_cols].fillna(False).any(axis=1)
    swd_count = int(swd_mask.sum())
else:
    swd_count = 0

# DCP count
if 'flag_dcp_involvement' in filtered_df.columns:
    dcp_count = len(filtered_df[
        (filtered_df['flag_dcp_involvement'] == True) |
        (filtered_df['flag_dcp_involvement'] == 'Yes') |
        (filtered_df['flag_dcp_involvement'].fillna('').astype(str).str.lower().isin(['yes', 'true', '1', 'y']))
    ])
else:
    dcp_count = 0

partnerships_count = filtered_df['partnership'].nunique() if 'partnership' in filtered_df.columns else 0

# Display clickable metrics
st.markdown('<div class="section-header">📊 Key Metrics - Click Any Card to Explore</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    if st.button(f"**{total_referrals}**\n\nTotal\nReferrals", use_container_width=True, key="btn_referrals"):
        st.session_state.drill_down_view = "referrals"
        st.rerun()

with col2:
    if st.button(f"**{allocated_count}**\n\nAllocated", use_container_width=True, key="btn_allocated"):
        st.session_state.drill_down_view = "allocated"
        st.rerun()

with col3:
    if st.button(f"**{mismatch_count}**\n\nNon-Typical", use_container_width=True, key="btn_nontypical"):
        st.session_state.drill_down_view = "nontypical"
        st.rerun()

with col4:
    if st.button(f"**{swd_count}**\n\nSWD", use_container_width=True, key="btn_swd"):
        st.session_state.drill_down_view = "swd"
        st.rerun()

with col5:
    if st.button(f"**{dcp_count}**\n\nDCP", use_container_width=True, key="btn_dcp"):
        st.session_state.drill_down_view = "dcp"
        st.rerun()

with col6:
    if st.button(f"**{partnerships_count}**\n\nPartnerships", use_container_width=True, key="btn_partnerships"):
        st.session_state.drill_down_view = "partnerships"
        st.rerun()

with col7:
    # Calculate extensions - with improved detection
    extended_count = 0
    
    # Check what extension-related columns we have
    has_exclusion_end = 'exclusion_end_date' in filtered_df.columns or 'placement_end' in filtered_df.columns
    has_actual_finish = 'actual_finish_date' in filtered_df.columns
    has_extended_flag = 'extended_placement' in filtered_df.columns
    
    if has_exclusion_end and has_actual_finish:
        # Calculate from dates
        exclusion_col = 'exclusion_end_date' if 'exclusion_end_date' in filtered_df.columns else 'placement_end'
        temp_df = filtered_df.copy()
        temp_df['exclusion_dt'] = pd.to_datetime(temp_df[exclusion_col], errors='coerce')
        temp_df['actual_dt'] = pd.to_datetime(temp_df['actual_finish_date'], errors='coerce')
        
        extended_count = len(temp_df[
            pd.notna(temp_df['exclusion_dt']) & 
            pd.notna(temp_df['actual_dt']) &
            (temp_df['actual_dt'] > temp_df['exclusion_dt'])
        ])
    elif has_extended_flag:
        # Use flag
        extended_count = len(filtered_df[
            (filtered_df['extended_placement'] == True) |
            (filtered_df['extended_placement'] == 'Yes') |
            (filtered_df['extended_placement'].fillna('').astype(str).str.lower().isin(['yes', 'true', '1', 'y']))
        ])
    
    if st.button(f"**{extended_count}**\n\nExtensions", use_container_width=True, key="btn_extensions"):
        st.session_state.drill_down_view = "extensions"
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DRILL-DOWN VIEWS
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.drill_down_view:
    st.markdown("---")
    
    # Close button
    col_spacer, col_close = st.columns([5, 1])
    with col_close:
        if st.button("✖️ Close", key="close_btn", use_container_width=True):
            st.session_state.drill_down_view = None
            st.rerun()
    
    # ═══════════════════════════════════════════════════════════════════════
    # REFERRALS DRILL-DOWN
    # ═══════════════════════════════════════════════════════════════════════
    if st.session_state.drill_down_view == "referrals":
        st.markdown(f"""
        <div class="drill-down-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <h2 class="drill-down-title">📊 Total Referrals Deep Dive</h2>
            <p class="drill-down-subtitle">Analyzing {total_referrals} referrals across partnerships, programs, and terms</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📍 By Partnership", "📚 By Program", "📅 By Term", "🏫 By School", "📊 Year Comparison", "📈 Term Trends"])
        
        with tab1:
            st.markdown("### Referrals by Partnership")
            if 'partnership' in filtered_df.columns:
                partnership_data = filtered_df['partnership'].value_counts().reset_index()
                partnership_data.columns = ['Partnership', 'Referrals']
                partnership_data['Percentage'] = (partnership_data['Referrals'] / total_referrals * 100).round(1)
                partnership_data = partnership_data.sort_values('Referrals', ascending=False)
                
                col_chart, col_table = st.columns([2, 1])
                
                with col_chart:
                    fig = go.Figure(go.Bar(
                        y=partnership_data['Partnership'],
                        x=partnership_data['Referrals'],
                        orientation='h',
                        text=[f"{r} ({p}%)" for r, p in zip(partnership_data['Referrals'], partnership_data['Percentage'])],
                        textposition='auto',
                        marker=dict(color=partnership_data['Referrals'], colorscale='Viridis', showscale=False)
                    ))
                    fig.update_layout(title="Referrals by Partnership", xaxis_title="Referrals", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_table:
                    st.markdown("**Top Partnerships**")
                    for _, row in partnership_data.head(10).iterrows():
                        st.markdown(f"**{row['Partnership']}**")
                        st.progress(row['Percentage'] / 100)
                        st.caption(f"{row['Referrals']} ({row['Percentage']}%)")
            else:
                st.info("Partnership data not available in dataset")
        
        with tab2:
            st.markdown("### Referrals by Program")
            if 'program' in filtered_df.columns:
                program_data = filtered_df['program'].value_counts().reset_index()
                program_data.columns = ['Program', 'Referrals']
                program_data['Percentage'] = (program_data['Referrals'] / total_referrals * 100).round(1)
                
                col_pie, col_stats = st.columns([2, 1])
                
                with col_pie:
                    colors = {'JP': '#E74C3C', 'PY': '#3498DB', 'SY': '#2ECC71'}
                    fig = go.Figure(go.Pie(
                        labels=program_data['Program'],
                        values=program_data['Referrals'],
                        hole=0.4,
                        textinfo='label+percent',
                        marker=dict(colors=[colors.get(p, '#95A5A6') for p in program_data['Program']])
                    ))
                    fig.update_layout(title="Program Distribution", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_stats:
                    st.markdown("**Program Breakdown**")
                    for _, row in program_data.iterrows():
                        st.metric(row['Program'], row['Referrals'], f"{row['Percentage']}%")
            else:
                st.info("Program data not available in dataset")
        
        with tab3:
            st.markdown("### Referrals by Term")
            if 'term' in filtered_df.columns:
                term_data = filtered_df['term'].value_counts().reset_index().sort_values('term')
                term_data.columns = ['Term', 'Referrals']
                
                fig = go.Figure(go.Bar(
                    x=term_data['Term'],
                    y=term_data['Referrals'],
                    text=term_data['Referrals'],
                    textposition='auto',
                    marker_color='#2ECC71'
                ))
                fig.update_layout(title="Referral Trends by Term", xaxis_title="Term", yaxis_title="Referrals", height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Term data not available in dataset")
        
        with tab4:
            st.markdown("### Top Referring Schools")
            if 'referring_school' in filtered_df.columns:
                school_data = filtered_df['referring_school'].value_counts().head(15).reset_index()
                school_data.columns = ['School', 'Referrals']
                school_data['Percentage'] = (school_data['Referrals'] / total_referrals * 100).round(1)
                
                fig = go.Figure(go.Bar(
                    y=school_data['School'],
                    x=school_data['Referrals'],
                    orientation='h',
                    text=school_data['Referrals'],
                    textposition='auto',
                    marker_color='#9B59B6'
                ))
                fig.update_layout(title="Top 15 Referring Schools", xaxis_title="Referrals", height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(school_data, use_container_width=True, hide_index=True)
        
        with tab5:
            st.markdown("### Year-over-Year Comparison")
            
            if 'year' in filtered_df.columns:
                year_data = filtered_df.groupby('year').size().reset_index(name='Referrals')
                year_data = year_data.sort_values('year')
                
                col_chart, col_table = st.columns([2, 1])
                
                with col_chart:
                    fig = go.Figure(go.Bar(
                        x=year_data['year'].astype(str),
                        y=year_data['Referrals'],
                        text=year_data['Referrals'],
                        textposition='auto',
                        marker_color='#3498DB'
                    ))
                    fig.update_layout(
                        title="Referrals by Year",
                        xaxis_title="Year",
                        yaxis_title="Referrals",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_table:
                    st.markdown("**Year Summary**")
                    for _, row in year_data.iterrows():
                        st.metric(f"Year {int(row['year'])}", int(row['Referrals']))
                
                # Year-over-year change
                if len(year_data) > 1:
                    st.markdown("### Year-over-Year Growth")
                    year_data['YoY Change'] = year_data['Referrals'].diff()
                    year_data['YoY %'] = (year_data['Referrals'].pct_change() * 100).round(1)
                    
                    display_yoy = year_data[['year', 'Referrals', 'YoY Change', 'YoY %']].copy()
                    display_yoy.columns = ['Year', 'Referrals', 'Change from Prior Year', 'Change %']
                    st.dataframe(display_yoy, use_container_width=True, hide_index=True)
            else:
                st.info("Year data not available")
        
        with tab6:
            st.markdown("### Term Trends")
            
            if 'term' in filtered_df.columns and 'year' in filtered_df.columns:
                term_year_data = filtered_df.groupby(['year', 'term']).size().reset_index(name='Referrals')
                
                # Create line chart showing term trends across years
                fig = go.Figure()
                
                for year in sorted(term_year_data['year'].unique()):
                    year_data = term_year_data[term_year_data['year'] == year]
                    fig.add_trace(go.Scatter(
                        x=year_data['term'],
                        y=year_data['Referrals'],
                        mode='lines+markers',
                        name=str(int(year)),
                        line=dict(width=3),
                        marker=dict(size=10)
                    ))
                
                fig.update_layout(
                    title="Referral Trends by Term (Multi-Year)",
                    xaxis_title="Term",
                    yaxis_title="Referrals",
                    height=400,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Heatmap
                st.markdown("### Term Heatmap")
                pivot_data = term_year_data.pivot(index='year', columns='term', values='Referrals').fillna(0)
                
                fig = go.Figure(go.Heatmap(
                    z=pivot_data.values,
                    x=pivot_data.columns,
                    y=[str(int(y)) for y in pivot_data.index],
                    colorscale='Blues',
                    text=pivot_data.values,
                    texttemplate='%{text}',
                    textfont={"size": 16},
                    colorbar=dict(title="Referrals")
                ))
                fig.update_layout(
                    title="Referrals Heatmap (Year x Term)",
                    xaxis_title="Term",
                    yaxis_title="Year",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Data table
                st.dataframe(pivot_data, use_container_width=True)
            else:
                st.info("Term or year data not available for trend analysis")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ALLOCATED VS WAITLIST DRILL-DOWN
    # ═══════════════════════════════════════════════════════════════════════
    elif st.session_state.drill_down_view == "allocated":
        if 'allocation_status' in filtered_df.columns:
            status_col = 'allocation_status'
        elif 'current_status' in filtered_df.columns:
            status_col = 'current_status'
        else:
            st.warning("Status information not available")
            st.stop()
        
        allocated_df = filtered_df[filtered_df[status_col].fillna('').astype(str).str.lower().isin(['allocated', 'active'])]
        waitlist_df = filtered_df[~filtered_df[status_col].fillna('').astype(str).str.lower().isin(['allocated', 'active'])]
        
        st.markdown(f"""
        <div class="drill-down-header" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
            <h2 class="drill-down-title">✅ Allocated vs Waitlist Analysis</h2>
            <p class="drill-down-subtitle">{len(allocated_df)} allocated • {len(waitlist_df)} on waitlist</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("✅ Allocated", len(allocated_df), f"{len(allocated_df)/total_referrals*100:.1f}%")
        with col_m2:
            st.metric("⏳ Waiting", len(waitlist_df), f"{len(waitlist_df)/total_referrals*100:.1f}%")
        
        tab1, tab2, tab3 = st.tabs(["✅ Allocated Details", "⏳ Waitlist Analysis", "📊 Comparison"])
        
        with tab1:
            st.markdown("### Where Students Are Allocated")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**By Partnership**")
                if len(allocated_df) > 0 and 'partnership' in allocated_df.columns:
                    alloc_partnership = allocated_df['partnership'].value_counts().reset_index()
                    alloc_partnership.columns = ['Partnership', 'Allocated']
                    
                    fig = go.Figure(go.Bar(
                        x=alloc_partnership['Partnership'],
                        y=alloc_partnership['Allocated'],
                        text=alloc_partnership['Allocated'],
                        textposition='auto',
                        marker_color='#2ECC71'
                    ))
                    fig.update_layout(title="Allocated by Partnership", height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No partnership data available")
            
            with col_b:
                st.markdown("**By Program**")
                if len(allocated_df) > 0 and 'program' in allocated_df.columns:
                    alloc_program = allocated_df['program'].value_counts().reset_index()
                    alloc_program.columns = ['Program', 'Allocated']
                    
                    fig = go.Figure(go.Pie(
                        labels=alloc_program['Program'],
                        values=alloc_program['Allocated'],
                        hole=0.4
                    ))
                    fig.update_layout(title="Program Distribution", height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No program data available")
        
        with tab2:
            st.markdown("### Students Awaiting Allocation")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**Waitlist by Partnership**")
                if len(waitlist_df) > 0 and 'partnership' in waitlist_df.columns:
                    wait_partnership = waitlist_df['partnership'].value_counts().reset_index()
                    wait_partnership.columns = ['Partnership', 'Waiting']
                    
                    fig = go.Figure(go.Bar(
                        x=wait_partnership['Partnership'],
                        y=wait_partnership['Waiting'],
                        text=wait_partnership['Waiting'],
                        textposition='auto',
                        marker_color='#E74C3C'
                    ))
                    fig.update_layout(title="Waitlist by Partnership", height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("✓ No students on waitlist or partnership data unavailable")
            
            with col_b:
                st.markdown("**Waitlist by Program**")
                if len(waitlist_df) > 0 and 'program' in waitlist_df.columns:
                    wait_program = waitlist_df['program'].value_counts().reset_index()
                    wait_program.columns = ['Program', 'Waiting']
                    
                    fig = go.Figure(go.Pie(
                        labels=wait_program['Program'],
                        values=wait_program['Waiting'],
                        hole=0.4
                    ))
                    fig.update_layout(title="Program Waitlist", height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("✓ No students on waitlist or program data unavailable")
        
        with tab3:
            st.markdown("### Side-by-Side Comparison")
            
            comparison_data = pd.DataFrame({
                'Status': ['Allocated', 'Waiting'],
                'Count': [len(allocated_df), len(waitlist_df)]
            })
            
            fig = go.Figure(go.Bar(
                x=comparison_data['Status'],
                y=comparison_data['Count'],
                text=comparison_data['Count'],
                textposition='auto',
                marker_color=['#2ECC71', '#E74C3C']
            ))
            fig.update_layout(title="Allocation Status Overview", yaxis_title="Students", height=400)
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════
    # NON-TYPICAL PLACEMENT DRILL-DOWN
    # ═══════════════════════════════════════════════════════════════════════
    elif st.session_state.drill_down_view == "nontypical":
        nontypical_df = filtered_df[filtered_df['program_mismatch'] == True]
        
        st.markdown(f"""
        <div class="drill-down-header" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h2 class="drill-down-title">⚠️ Non-Typical Placements Deep Dive</h2>
            <p class="drill-down-subtitle">{len(nontypical_df)} students in non-typical year level placements</p>
        </div>
        """, unsafe_allow_html=True)
        
        if len(nontypical_df) > 0:
            tab1, tab2 = st.tabs(["👥 Student Details", "📊 Analysis"])
            
            with tab1:
                st.markdown("### Students in Non-Typical Programs")
                display_cols = []
                if 'student_name' in nontypical_df.columns:
                    display_cols.append('student_name')
                if 'year_level' in nontypical_df.columns:
                    display_cols.append('year_level')
                if 'program' in nontypical_df.columns:
                    display_cols.append('program')
                if 'partnership' in nontypical_df.columns:
                    display_cols.append('partnership')
                if 'term' in nontypical_df.columns:
                    display_cols.append('term')
                
                if display_cols:
                    display_df = nontypical_df[display_cols].copy()
                    display_df.columns = [col.replace('_', ' ').title() for col in display_cols]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            with tab2:
                st.markdown("### Non-Typical Placement Breakdown")
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if 'year_level' in nontypical_df.columns:
                        st.markdown("**By Year Level**")
                        year_breakdown = nontypical_df['year_level'].value_counts().reset_index()
                        year_breakdown.columns = ['Year Level', 'Count']
                        
                        fig = go.Figure(go.Bar(
                            x=year_breakdown['Year Level'],
                            y=year_breakdown['Count'],
                            text=year_breakdown['Count'],
                            textposition='auto',
                            marker_color='#E67E22'
                        ))
                        fig.update_layout(title="Non-Typical by Year Level", height=300)
                        st.plotly_chart(fig, use_container_width=True)
                
                with col_b:
                    if 'program' in nontypical_df.columns:
                        st.markdown("**By Program Placed**")
                        prog_breakdown = nontypical_df['program'].value_counts().reset_index()
                        prog_breakdown.columns = ['Program', 'Count']
                        
                        fig = go.Figure(go.Bar(
                            x=prog_breakdown['Program'],
                            y=prog_breakdown['Count'],
                            text=prog_breakdown['Count'],
                            textposition='auto',
                            marker_color='#C0392B'
                        ))
                        fig.update_layout(title="Actual Programs", height=300)
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("✓ No non-typical placements in current filter")

    # ═══════════════════════════════════════════════════════════════════════
    # SWD DRILL-DOWN
    # ═══════════════════════════════════════════════════════════════════════
    elif st.session_state.drill_down_view == "swd":
        disability_cols = ['flag_asd', 'flag_adhd', 'flag_intellectual', 'flag_learning_difficulty', 'flag_sensory_processing', 'flag_odd', 'flag_pda']
        disability_labels = ['ASD', 'ADHD', 'Intellectual', 'Learning Difficulty', 'Sensory Processing', 'ODD', 'PDA']
        available_cols = [col for col in disability_cols if col in filtered_df.columns]
        
        if available_cols:
            swd_df = filtered_df[filtered_df[available_cols].fillna(False).any(axis=1)].copy()
            
            st.markdown(f"""
            <div class="drill-down-header" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <h2 class="drill-down-title">♿ Students with Disabilities Deep Dive</h2>
                <p class="drill-down-subtitle">{len(swd_df)} students with disabilities ({len(swd_df)/len(filtered_df)*100:.1f}% of cohort)</p>
            </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2, tab3, tab4 = st.tabs(["📊 By Disability Type", "🔗 Co-occurring Conditions", "🤝 By Partnership", "📚 By Program"])
            
            with tab1:
                st.markdown("### Breakdown by Disability Type")
                
                disability_counts = []
                for col, label in zip(disability_cols, disability_labels):
                    if col in swd_df.columns:
                        count = int(swd_df[col].fillna(False).sum())
                        pct = (count / len(swd_df) * 100) if len(swd_df) > 0 else 0
                        disability_counts.append({'Disability': label, 'Count': count, 'Percentage': pct})
                
                disability_breakdown = pd.DataFrame(disability_counts).sort_values('Count', ascending=False)
                
                col_chart, col_table = st.columns([2, 1])
                
                with col_chart:
                    fig = go.Figure(go.Bar(
                        y=disability_breakdown['Disability'],
                        x=disability_breakdown['Count'],
                        orientation='h',
                        text=disability_breakdown['Count'],
                        textposition='auto',
                        marker=dict(color=disability_breakdown['Count'], colorscale='Purples', showscale=False)
                    ))
                    fig.update_layout(title="Students by Disability Type", xaxis_title="Count", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_table:
                    st.markdown("**Summary**")
                    for _, row in disability_breakdown.iterrows():
                        st.metric(row['Disability'], row['Count'], f"{row['Percentage']:.1f}%")
            
            with tab2:
                st.markdown("### Co-occurring Conditions (Dual/Multiple Diagnosis)")
                
                swd_df['disability_count'] = swd_df[available_cols].fillna(False).sum(axis=1)
                
                col_m1, col_m2, col_m3 = st.columns(3)
                single = len(swd_df[swd_df['disability_count'] == 1])
                dual = len(swd_df[swd_df['disability_count'] == 2])
                multiple = len(swd_df[swd_df['disability_count'] >= 3])
                
                with col_m1:
                    st.metric("Single Diagnosis", single, f"{single/len(swd_df)*100:.1f}%")
                with col_m2:
                    st.metric("Dual Diagnosis", dual, f"{dual/len(swd_df)*100:.1f}%")
                with col_m3:
                    st.metric("3+ Diagnoses", multiple, f"{multiple/len(swd_df)*100:.1f}%")
                
                diagnosis_breakdown = swd_df['disability_count'].value_counts().sort_index().reset_index()
                diagnosis_breakdown.columns = ['Number of Conditions', 'Students']
                
                fig = go.Figure(go.Bar(
                    x=[f"{int(n)} Condition{'s' if n > 1 else ''}" for n in diagnosis_breakdown['Number of Conditions']],
                    y=diagnosis_breakdown['Students'],
                    text=diagnosis_breakdown['Students'],
                    textposition='auto',
                    marker_color='#9B59B6'
                ))
                fig.update_layout(title="Distribution of Co-occurring Conditions", yaxis_title="Students", height=350)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(diagnosis_breakdown, use_container_width=True, hide_index=True)
            
            with tab3:
                st.markdown("### SWD by Partnership")
                
                swd_partnership = swd_df['partnership'].value_counts().reset_index()
                swd_partnership.columns = ['Partnership', 'SWD Count']
                
                # Calculate percentage
                for idx, row in swd_partnership.iterrows():
                    total_in_partnership = len(filtered_df[filtered_df['partnership'] == row['Partnership']])
                    if total_in_partnership > 0:
                        swd_partnership.loc[idx, '% of Partnership'] = f"{row['SWD Count']/total_in_partnership*100:.1f}%"
                
                fig = go.Figure(go.Bar(
                    x=swd_partnership['Partnership'],
                    y=swd_partnership['SWD Count'],
                    text=swd_partnership['SWD Count'],
                    textposition='auto',
                    marker_color='#8E44AD'
                ))
                fig.update_layout(title="SWD Distribution by Partnership", yaxis_title="SWD Count", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(swd_partnership, use_container_width=True, hide_index=True)
            
            with tab4:
                st.markdown("### SWD by Program")
                
                swd_program = swd_df['program'].value_counts().reset_index()
                swd_program.columns = ['Program', 'SWD Count']
                
                fig = go.Figure(go.Bar(
                    x=swd_program['Program'],
                    y=swd_program['SWD Count'],
                    text=swd_program['SWD Count'],
                    textposition='auto',
                    marker_color=['#E74C3C', '#3498DB', '#2ECC71']
                ))
                fig.update_layout(title="SWD by Program", yaxis_title="SWD Count", height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Disability data not available")

    # ═══════════════════════════════════════════════════════════════════════
    # DCP DRILL-DOWN
    # ═══════════════════════════════════════════════════════════════════════
    elif st.session_state.drill_down_view == "dcp":
        if 'flag_dcp_involvement' in filtered_df.columns:
            dcp_df = filtered_df[
                (filtered_df['flag_dcp_involvement'] == True) |
                (filtered_df['flag_dcp_involvement'] == 'Yes') |
                (filtered_df['flag_dcp_involvement'].fillna('').astype(str).str.lower().isin(['yes', 'true', '1', 'y']))
            ].copy()
            
            st.markdown(f"""
            <div class="drill-down-header" style="background: linear-gradient(135deg, #ff9966 0%, #ff5e62 100%);">
                <h2 class="drill-down-title">👨‍👩‍👧 DCP Involvement Deep Dive</h2>
                <p class="drill-down-subtitle">{len(dcp_df)} students with DCP involvement ({len(dcp_df)/len(filtered_df)*100:.1f}% of cohort)</p>
            </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["📍 DCP by Partnership", "👥 Student Details"])
            
            with tab1:
                st.markdown("### DCP Involvement by Partnership")
                
                if len(dcp_df) > 0:
                    dcp_partnership = dcp_df['partnership'].value_counts().reset_index()
                    dcp_partnership.columns = ['Partnership', 'DCP Count']
                    
                    # Calculate percentage
                    for idx, row in dcp_partnership.iterrows():
                        total = len(filtered_df[filtered_df['partnership'] == row['Partnership']])
                        if total > 0:
                            dcp_partnership.loc[idx, '% of Partnership'] = f"{row['DCP Count']/total*100:.1f}%"
                    
                    fig = go.Figure(go.Bar(
                        x=dcp_partnership['Partnership'],
                        y=dcp_partnership['DCP Count'],
                        text=dcp_partnership['DCP Count'],
                        textposition='auto',
                        marker_color='#E67E22'
                    ))
                    fig.update_layout(title="DCP Students by Partnership", yaxis_title="DCP Count", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(dcp_partnership, use_container_width=True, hide_index=True)
                else:
                    st.info("No DCP students in current filter")
            
            with tab2:
                st.markdown("### DCP Student Details")
                
                if len(dcp_df) > 0:
                    display_cols = []
                    if 'student_name' in dcp_df.columns:
                        display_cols.append('student_name')
                    if 'partnership' in dcp_df.columns:
                        display_cols.append('partnership')
                    if 'program' in dcp_df.columns:
                        display_cols.append('program')
                    if 'year_level' in dcp_df.columns:
                        display_cols.append('year_level')
                    if 'term' in dcp_df.columns:
                        display_cols.append('term')
                    
                    if display_cols:
                        display_df = dcp_df[display_cols].copy()
                        display_df.columns = [col.replace('_', ' ').title() for col in display_cols]
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("DCP data not available")
    
    # ═══════════════════════════════════════════════════════════════════════
    # PARTNERSHIPS DRILL-DOWN
    # ═══════════════════════════════════════════════════════════════════════
    elif st.session_state.drill_down_view == "partnerships":
        st.markdown(f"""
        <div class="drill-down-header" style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);">
            <h2 class="drill-down-title">🤝 Partnership Deep Dive</h2>
            <p class="drill-down-subtitle">Analyzing {partnerships_count} active partnerships</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["🔴 ATSI by Partnership", "🌏 EALD by Partnership", "👨‍👩‍👧 DCP by Partnership", "📚 Programs by Partnership"])
        
        with tab1:
            st.markdown("### ATSI Representation by Partnership")
            
            atsi_col = 'flag_aboriginal' if 'flag_aboriginal' in filtered_df.columns else 'flag_atsi' if 'flag_atsi' in filtered_df.columns else None
            
            if atsi_col:
                atsi_df = filtered_df[filtered_df[atsi_col].fillna(False) == True]
                
                if len(atsi_df) > 0:
                    atsi_partnership = atsi_df['partnership'].value_counts().reset_index()
                    atsi_partnership.columns = ['Partnership', 'ATSI Count']
                    
                    # Calculate percentage
                    for idx, row in atsi_partnership.iterrows():
                        total = len(filtered_df[filtered_df['partnership'] == row['Partnership']])
                        if total > 0:
                            atsi_partnership.loc[idx, 'ATSI %'] = f"{row['ATSI Count']/total*100:.1f}%"
                    
                    atsi_partnership = atsi_partnership.sort_values('ATSI Count', ascending=False)
                    
                    fig = go.Figure(go.Bar(
                        x=atsi_partnership['Partnership'],
                        y=atsi_partnership['ATSI Count'],
                        text=atsi_partnership['ATSI Count'],
                        textposition='auto',
                        marker_color='#E74C3C'
                    ))
                    fig.update_layout(title="ATSI Students by Partnership", yaxis_title="ATSI Count", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(atsi_partnership, use_container_width=True, hide_index=True)
                else:
                    st.info("No ATSI students in current filter")
            else:
                st.warning("ATSI data not available")
        
        with tab2:
            st.markdown("### EALD Representation by Partnership")
            
            if 'flag_eald' in filtered_df.columns:
                eald_df = filtered_df[filtered_df['flag_eald'].fillna(False) == True]
                
                if len(eald_df) > 0:
                    eald_partnership = eald_df['partnership'].value_counts().reset_index()
                    eald_partnership.columns = ['Partnership', 'EALD Count']
                    
                    fig = go.Figure(go.Bar(
                        x=eald_partnership['Partnership'],
                        y=eald_partnership['EALD Count'],
                        text=eald_partnership['EALD Count'],
                        textposition='auto',
                        marker_color='#3498DB'
                    ))
                    fig.update_layout(title="EALD Students by Partnership", yaxis_title="EALD Count", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(eald_partnership, use_container_width=True, hide_index=True)
                else:
                    st.info("No EALD students in current filter")
            else:
                st.warning("EALD data not available")
        
        with tab3:
            st.markdown("### DCP Involvement by Partnership")
            
            if 'flag_dcp_involvement' in filtered_df.columns:
                dcp_df = filtered_df[
                    (filtered_df['flag_dcp_involvement'] == True) |
                    (filtered_df['flag_dcp_involvement'] == 'Yes') |
                    (filtered_df['flag_dcp_involvement'].fillna('').astype(str).str.lower().isin(['yes', 'true', '1', 'y']))
                ]
                
                if len(dcp_df) > 0:
                    dcp_partnership = dcp_df['partnership'].value_counts().reset_index()
                    dcp_partnership.columns = ['Partnership', 'DCP Count']
                    
                    fig = go.Figure(go.Bar(
                        x=dcp_partnership['Partnership'],
                        y=dcp_partnership['DCP Count'],
                        text=dcp_partnership['DCP Count'],
                        textposition='auto',
                        marker_color='#E67E22'
                    ))
                    fig.update_layout(title="DCP Students by Partnership", yaxis_title="DCP Count", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(dcp_partnership, use_container_width=True, hide_index=True)
                else:
                    st.info("No DCP students in current filter")
            else:
                st.warning("DCP data not available")
        
        with tab4:
            st.markdown("### Program Distribution by Partnership")
            
            prog_by_partnership = filtered_df.groupby(['partnership', 'program']).size().reset_index()
            prog_by_partnership.columns = ['Partnership', 'Program', 'Count']
            
            fig = go.Figure()
            
            colors = {'JP': '#E74C3C', 'PY': '#3498DB', 'SY': '#2ECC71'}
            for program in filtered_df['program'].unique():
                if pd.notna(program):
                    prog_data = prog_by_partnership[prog_by_partnership['Program'] == program]
                    fig.add_trace(go.Bar(
                        name=program,
                        x=prog_data['Partnership'],
                        y=prog_data['Count'],
                        text=prog_data['Count'],
                        textposition='auto',
                        marker_color=colors.get(program, '#95A5A6')
                    ))
            
            fig.update_layout(
                title="Programs by Partnership",
                xaxis_title="Partnership",
                yaxis_title="Students",
                barmode='stack',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXTENSIONS DRILL-DOWN
    # ═══════════════════════════════════════════════════════════════════════
    elif st.session_state.drill_down_view == "extensions":
        st.markdown(f"""
        <div class="drill-down-header" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h2 class="drill-down-title">⏱️ Placement Extensions vs. Exclusion End Date</h2>
            <p class="drill-down-subtitle">Comparing students who finished at exclusion end date vs. those with extensions</p>
        </div>
        """, unsafe_allow_html=True)
        
        # DEBUG: Show available columns
        with st.expander("🔍 Debug: Available Extension Columns", expanded=False):
            st.write("**Checking for extension-related columns:**")
            
            cols_check = {
                'exclusion_end_date': 'exclusion_end_date' in extensions_df.columns,
                'placement_end': 'placement_end' in extensions_df.columns,
                'actual_finish_date': 'actual_finish_date' in extensions_df.columns,
                'extended_placement': 'extended_placement' in extensions_df.columns
            }
            
            for col, exists in cols_check.items():
                if exists:
                    st.success(f"✅ `{col}` column found")
                    # Show sample data
                    non_null = extensions_df[col].notna().sum()
                    st.caption(f"   {non_null} non-null values out of {len(extensions_df)}")
                else:
                    st.error(f"❌ `{col}` column not found")
            
            st.write(f"\n**All available columns:**")
            st.write(list(extensions_df.columns))
        
        # Calculate extension data
        extensions_df = filtered_df.copy()
        
        # Check for exclusion_end_date or placement_end column
        exclusion_col = None
        if 'exclusion_end_date' in extensions_df.columns:
            exclusion_col = 'exclusion_end_date'
        elif 'placement_end' in extensions_df.columns:
            exclusion_col = 'placement_end'
        
        has_dates = exclusion_col and 'actual_finish_date' in extensions_df.columns
        
        if has_dates:
            # Convert dates
            extensions_df['exclusion_end_dt'] = pd.to_datetime(extensions_df[exclusion_col], errors='coerce')
            extensions_df['actual_finish_dt'] = pd.to_datetime(extensions_df['actual_finish_date'], errors='coerce')
            
            # Only consider completed placements (have actual finish date)
            completed_df = extensions_df[pd.notna(extensions_df['actual_finish_dt'])].copy()
            
            if len(completed_df) > 0:
                # Calculate categories
                completed_df['status'] = completed_df.apply(
                    lambda row: 'Extended' if pd.notna(row['exclusion_end_dt']) and row['actual_finish_dt'] > row['exclusion_end_dt']
                    else 'On Time' if pd.notna(row['exclusion_end_dt']) and row['actual_finish_dt'] == row['exclusion_end_dt']
                    else 'Early' if pd.notna(row['exclusion_end_dt']) and row['actual_finish_dt'] < row['exclusion_end_dt']
                    else 'Unknown',
                    axis=1
                )
                
                # Count by status
                extended_count = len(completed_df[completed_df['status'] == 'Extended'])
                on_time_count = len(completed_df[completed_df['status'] == 'On Time'])
                early_count = len(completed_df[completed_df['status'] == 'Early'])
                
                # Display summary metrics
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("Total Completed", len(completed_df))
                with col_m2:
                    st.metric("✅ At Exclusion Date", on_time_count, f"{on_time_count/len(completed_df)*100:.1f}%")
                with col_m3:
                    st.metric("⏱️ Extended", extended_count, f"{extended_count/len(completed_df)*100:.1f}%")
                with col_m4:
                    st.metric("⚡ Finished Early", early_count, f"{early_count/len(completed_df)*100:.1f}%")
                
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 By Partnership", "📚 By Program", "👥 Student Details"])
                
                with tab1:
                    st.markdown("### Completion vs. Exclusion End Date")
                    
                    col_pie, col_bar = st.columns(2)
                    
                    with col_pie:
                        # Pie chart of completion status
                        status_counts = completed_df['status'].value_counts()
                        
                        fig = go.Figure(go.Pie(
                            labels=status_counts.index,
                            values=status_counts.values,
                            hole=0.4,
                            marker=dict(colors=['#2ECC71', '#3498DB', '#E74C3C', '#95A5A6'])
                        ))
                        fig.update_layout(title="Exclusion Date Compliance", height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col_bar:
                        # Bar chart
                        fig = go.Figure(go.Bar(
                            x=status_counts.index,
                            y=status_counts.values,
                            text=status_counts.values,
                            textposition='auto',
                            marker_color=['#2ECC71', '#3498DB', '#E74C3C', '#95A5A6']
                        ))
                        fig.update_layout(
                            title="Students by Completion Status",
                            yaxis_title="Students",
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Extension duration analysis
                    if extended_count > 0:
                        st.markdown("### Extension Duration Beyond Exclusion Date")
                        
                        extended_students = completed_df[completed_df['status'] == 'Extended'].copy()
                        extended_students['extension_days'] = (
                            extended_students['actual_finish_dt'] - extended_students['exclusion_end_dt']
                        ).dt.days
                        
                        col_stats1, col_stats2, col_stats3 = st.columns(3)
                        
                        with col_stats1:
                            avg_extension = extended_students['extension_days'].mean()
                            st.metric("Average Extension", f"{avg_extension:.0f} days")
                        
                        with col_stats2:
                            max_extension = extended_students['extension_days'].max()
                            st.metric("Longest Extension", f"{max_extension:.0f} days")
                        
                        with col_stats3:
                            min_extension = extended_students['extension_days'].min()
                            st.metric("Shortest Extension", f"{min_extension:.0f} days")
                        
                        # Histogram of extension lengths
                        fig = go.Figure(go.Histogram(
                            x=extended_students['extension_days'],
                            nbinsx=20,
                            marker_color='#3498DB'
                        ))
                        fig.update_layout(
                            title="Distribution of Days Extended Beyond Exclusion Date",
                            xaxis_title="Days Beyond Exclusion Date",
                            yaxis_title="Number of Students",
                            height=300
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Show comparison
                    st.markdown("### Summary")
                    st.info(f"""
                    **Of {len(completed_df)} completed placements:**
                    - ✅ **{on_time_count} students ({on_time_count/len(completed_df)*100:.1f}%)** finished exactly at their exclusion end date
                    - ⏱️ **{extended_count} students ({extended_count/len(completed_df)*100:.1f}%)** were extended beyond their exclusion date
                    - ⚡ **{early_count} students ({early_count/len(completed_df)*100:.1f}%)** finished before their exclusion date
                    """)
                
                with tab2:
                    st.markdown("### Extensions by Partnership")
                    
                    if 'partnership' in completed_df.columns:
                        partnership_status = completed_df.groupby(['partnership', 'status']).size().unstack(fill_value=0)
                        
                        fig = go.Figure()
                        
                        colors = {'On Time': '#2ECC71', 'Extended': '#3498DB', 'Early': '#E74C3C', 'Unknown': '#95A5A6'}
                        for status in partnership_status.columns:
                            fig.add_trace(go.Bar(
                                name=status,
                                x=partnership_status.index,
                                y=partnership_status[status],
                                marker_color=colors.get(status, '#95A5A6')
                            ))
                        
                        fig.update_layout(
                            title="Completion vs Exclusion Date by Partnership",
                            xaxis_title="Partnership",
                            yaxis_title="Students",
                            barmode='stack',
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Table with percentages
                        partnership_summary = pd.DataFrame()
                        for partnership in partnership_status.index:
                            total = partnership_status.loc[partnership].sum()
                            extended_pct = (partnership_status.loc[partnership].get('Extended', 0) / total * 100) if total > 0 else 0
                            on_time_pct = (partnership_status.loc[partnership].get('On Time', 0) / total * 100) if total > 0 else 0
                            partnership_summary = pd.concat([partnership_summary, pd.DataFrame({
                                'Partnership': [partnership],
                                'Total': [total],
                                'At Exclusion Date': [partnership_status.loc[partnership].get('On Time', 0)],
                                'Extended': [partnership_status.loc[partnership].get('Extended', 0)],
                                'Extended %': [f"{extended_pct:.1f}%"]
                            })])
                        
                        st.dataframe(partnership_summary.reset_index(drop=True), use_container_width=True, hide_index=True)
                    else:
                        st.info("Partnership data not available")
                
                with tab3:
                    st.markdown("### Extensions by Program")
                    
                    if 'program' in completed_df.columns:
                        program_status = completed_df.groupby(['program', 'status']).size().unstack(fill_value=0)
                        
                        fig = go.Figure()
                        
                        colors = {'On Time': '#2ECC71', 'Extended': '#3498DB', 'Early': '#E74C3C', 'Unknown': '#95A5A6'}
                        for status in program_status.columns:
                            fig.add_trace(go.Bar(
                                name=status,
                                x=program_status.index,
                                y=program_status[status],
                                marker_color=colors.get(status, '#95A5A6')
                            ))
                        
                        fig.update_layout(
                            title="Completion Status by Program (JP/PY/SY)",
                            xaxis_title="Program",
                            yaxis_title="Students",
                            barmode='group',
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Program data not available")
                
                with tab4:
                    st.markdown("### Student Details")
                    
                    # Filter options
                    status_filter = st.selectbox("Filter by Status:", ['All'] + list(completed_df['status'].unique()))
                    
                    display_df = completed_df if status_filter == 'All' else completed_df[completed_df['status'] == status_filter]
                    
                    # Show relevant columns
                    display_cols = []
                    for col in ['student_name', 'partnership', 'program', exclusion_col, 'actual_finish_date', 'status']:
                        if col in display_df.columns:
                            display_cols.append(col)
                    
                    if display_cols:
                        show_df = display_df[display_cols].copy()
                        col_names = []
                        for c in display_cols:
                            if c == exclusion_col:
                                col_names.append('Exclusion End Date')
                            else:
                                col_names.append(c.replace('_', ' ').title())
                        show_df.columns = col_names
                        
                        # Add extension days column for extended students
                        if 'Status' in show_df.columns and 'Extended' in show_df['Status'].values:
                            extended_mask = display_df['status'] == 'Extended'
                            extension_days = (display_df['actual_finish_dt'] - display_df['exclusion_end_dt']).dt.days
                            show_df['Days Extended'] = extension_days
                            show_df.loc[~extended_mask, 'Days Extended'] = ''
                        
                        st.dataframe(show_df, use_container_width=True, hide_index=True)
                        
                        st.caption(f"Showing {len(display_df)} of {len(completed_df)} completed placements")
            else:
                st.info("No completed placements found (students need an actual_finish_date)")
        
        elif 'extended_placement' in extensions_df.columns:
            # Simplified view using extended_placement flag
            extended_students = extensions_df[extensions_df['extended_placement'] == True]
            not_extended = extensions_df[extensions_df['extended_placement'] == False]
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Extended Beyond Exclusion", len(extended_students), 
                         f"{len(extended_students)/len(extensions_df)*100:.1f}%")
            with col_m2:
                st.metric("Finished at Exclusion Date", len(not_extended),
                         f"{len(not_extended)/len(extensions_df)*100:.1f}%")
            
            st.markdown("### Extension Status")
            
            status_data = pd.DataFrame({
                'Status': ['Extended', 'At Exclusion Date'],
                'Count': [len(extended_students), len(not_extended)]
            })
            
            fig = go.Figure(go.Bar(
                x=status_data['Status'],
                y=status_data['Count'],
                text=status_data['Count'],
                textposition='auto',
                marker_color=['#3498DB', '#2ECC71']
            ))
            fig.update_layout(title="Extensions vs. Exclusion Date Compliance", yaxis_title="Students", height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.warning("""
            **Extension data not available**
            
            To track extensions vs. exclusion dates, your Excel file needs:
            - `Exclusion_End_Date` (or `Placement_End`) column AND
            - `Actual_Finish_Date` column
            
            OR
            
            - `Extended_Placement` column (Yes/No flag)
            
            Add these columns to your Excel file to enable extension tracking.
            """)

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# QUICK OVERVIEW (when no drill-down active)
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state.drill_down_view:
    st.markdown('<div class="section-header">🗺️ Adelaide Catchment Map</div>', unsafe_allow_html=True)
    st.markdown("**Geographic distribution of student allocations across partnership areas**")
    
    # Count by partnership
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
    
    # Partnership distribution in expander
    with st.expander("📊 View Partnership Distribution", expanded=False):
        cols = st.columns(3)
        sorted_partnerships = sorted(partnership_counts.items(), key=lambda x: x[1], reverse=True)
        
        for idx, (partnership, count) in enumerate(sorted_partnerships):
            if partnership:
                percentage = (count / total_map_students * 100) if total_map_students > 0 else 0
                color = partnership_regions.get(partnership, {}).get('color', '#95A5A6')
                
                col_idx = idx % 3
                with cols[col_idx]:
                    st.markdown(f"""
                        <div style='padding: 8px; margin-bottom: 6px; border-left: 3px solid {color}; 
                                    background: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
                            <div style='font-weight: 600; font-size: 0.8em;'>{partnership}</div>
                            <div style='font-size: 1.3em; font-weight: bold; color: {color};'>{count}</div>
                            <div style='font-size: 0.75em; color: #666;'>{percentage:.1f}%</div>
                        </div>
                    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; padding: 2rem 0;'>
    <p style='margin: 0; font-size: 0.9rem;'>📊 CLC Allocation Dashboard - Interactive Analytics</p>
    <p style='margin: 0.5rem 0 0 0; font-size: 0.8rem;'>Click any metric card to explore detailed analysis</p>
</div>
""", unsafe_allow_html=True)
