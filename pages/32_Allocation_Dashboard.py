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

# Ensure required columns exist (add with safe defaults if still missing)
required_columns = {
    'partnership': '',
    'program': 'Unknown',
    'term': 'Unknown',
    'year_level': 'Unknown',
    'student_name': 'Student',
    'referring_school': 'Unknown School',
    'current_status': 'Unknown'
}

for col, default_value in required_columns.items():
    if col not in df.columns:
        df[col] = default_value
        st.warning(f"⚠️ Column '{col}' not found in data - using default values")

# Extract year from referral_year or referral_date
if 'referral_year' in df.columns:
    df['year'] = df['referral_year'].fillna(datetime.now().year).astype(int)
elif 'referral_date' in df.columns:
    df['referral_date'] = pd.to_datetime(df['referral_date'], errors='coerce')
    df['year'] = df['referral_date'].dt.year.fillna(datetime.now().year).astype(int)
    df['month'] = df['referral_date'].dt.month
else:
    df['year'] = datetime.now().year

# Calculate term from month (like old dashboard)
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

if 'month' in df.columns:
    df['term'] = df['month'].apply(get_term)
elif 'term' not in df.columns or df['term'].isna().all():
    df['term'] = 'Unknown'

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

col1, col2, col3, col4, col5, col6 = st.columns(6)

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
        
        tab1, tab2, tab3, tab4 = st.tabs(["📍 By Partnership", "📚 By Program", "📅 By Term", "🏫 By School"])
        
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

