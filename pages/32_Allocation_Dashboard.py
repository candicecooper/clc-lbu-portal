import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from supabase import create_client, Client

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
            st.warning("📋 No allocation data found in database. The dashboard will show empty until records are added.")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(response.data)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error loading data from Supabase: {str(e)}")
        st.stop()

# Load data
df_raw = load_allocation_data()

if len(df_raw) == 0:
    st.info("📭 **The allocation_tracker table is currently empty.** Add student records to see the dashboard populate with data.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# DATA PROCESSING & MAPPING
# ══════════════════════════════════════════════════════════════════════════════

# Create a working copy
df = df_raw.copy()

# Map Supabase columns to dashboard expectations
df['record_id'] = df['id']
df['school'] = df['referring_school']
df['status'] = df['allocation_status']
df['program'] = df['allocated_program']
df['partnership'] = df['partnership_area'].fillna('')

# Handle dates
df['referral_date'] = pd.to_datetime(df['referral_date'], errors='coerce')
df['year'] = df['referral_date'].dt.year
df['month'] = df['referral_date'].dt.month

# Get year level from database (added via SQL script)
# If year_level is empty, calculate from DOB as fallback
def calculate_year_level_from_dob(dob):
    """Calculate year level from date of birth as fallback"""
    if pd.isna(dob):
        return "Unknown"
    
    dob = pd.to_datetime(dob)
    today = datetime.now()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    # SA school entry: Reception at age 5
    if age < 5:
        return "R"
    elif age == 5:
        return "R"
    elif age == 6:
        return "1"
    elif age == 7:
        return "2"
    elif age == 8:
        return "3"
    elif age == 9:
        return "4"
    elif age == 10:
        return "5"
    elif age == 11:
        return "6"
    elif age == 12:
        return "7"
    elif age == 13:
        return "8"
    elif age == 14:
        return "9"
    elif age >= 15:
        return "10"
    else:
        return "Unknown"

# Use database year_level, calculate from DOB if missing
if 'year_level' in df.columns:
    df['year_level'] = df['year_level'].fillna('').astype(str)
    # Fill empty year_levels with calculated values
    mask = (df['year_level'] == '') | (df['year_level'] == 'None') | (df['year_level'].isna())
    df.loc[mask, 'year_level'] = df.loc[mask, 'dob'].apply(calculate_year_level_from_dob)
else:
    # If column doesn't exist yet, calculate from DOB
    df['year_level'] = df['dob'].apply(calculate_year_level_from_dob)

# Create SWD and DCP flags
# SWD = Students with Disabilities (any disability flag is true)
df['swd'] = (
    df.get('flag_asd', False) | 
    df.get('flag_adhd', False) | 
    df.get('flag_mental_health', False) | 
    df.get('flag_odd_cd', False)
).map({True: 'Yes', False: 'No'})

# DCP = Department Child Protection
df['dcp'] = df.get('flag_care_cps', False).map({True: 'Yes', False: 'No'})

# Map other flags
df['aboriginal'] = df.get('flag_aboriginal', False).map({True: 'Yes', False: 'No'})
df['eald'] = df.get('flag_eald', False).map({True: 'Yes', False: 'No'})
df['care_cps'] = df.get('flag_care_cps', False).map({True: 'Yes', False: 'No'})
df['mental_health'] = df.get('flag_mental_health', False).map({True: 'Yes', False: 'No'})

# Previous placements
df['prev_clc'] = df.get('previous_clc_placement', '').apply(lambda x: 'Yes' if x and x != '' else 'No')
df['prev_other'] = df.get('previous_other_lc', '').apply(lambda x: 'Yes' if x and x != '' else 'No')

# Priority
df['priority'] = df.get('priority_level', '')

# Current status
df['current_status'] = df.get('current_status', 'Active')

# Define terms based on SA school year
def get_term(month):
    if pd.isna(month):
        return "Unknown"
    if month <= 3:
        return "Term 1"
    elif month <= 6:
        return "Term 2"
    elif month <= 9:
        return "Term 3"
    else:
        return "Term 4"

df['term'] = df['month'].apply(get_term)

# ══════════════════════════════════════════════════════════════════════════════
# PROGRAM PLACEMENT LOGIC
# ══════════════════════════════════════════════════════════════════════════════
def get_expected_program(year_level):
    """Determine expected program based on year level"""
    if pd.isna(year_level) or year_level == '' or year_level == "Unknown":
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

# Add expected program and mismatch flag
df['expected_program'] = df['year_level'].apply(get_expected_program)
df['program_mismatch'] = (df['program'] != df['expected_program']) & (df['expected_program'] != "Unknown")

# Calculate percentage in non-typical placement
mismatch_count = df['program_mismatch'].sum()
mismatch_percentage = (mismatch_count / len(df) * 100) if len(df) > 0 else 0

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="dashboard-header">
    <h1>📊 Allocation Dashboard</h1>
    <p>Live student allocation overview • Interactive drill-down analytics</p>
    <span class="privacy-badge">🔒 Privacy Protected</span>
    <span class="refresh-badge">🔄 Live Data • Auto-refresh 60s</span>
</div>
""", unsafe_allow_html=True)

# Show last update time
st.caption(f"📅 Last updated: {datetime.now().strftime('%d/%m/%Y %I:%M %p')} | Total records: {len(df)}")

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔍 Filters & View Options</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    # Term filter
    terms = ['All Terms'] + sorted(df['term'].unique().tolist())
    selected_term = st.selectbox("📅 Select Term", terms, key="term_filter")

with col2:
    # Partnership filter
    partnerships = ['All Partnerships'] + sorted([p for p in df['partnership'].unique() if p != ''])
    selected_partnership = st.selectbox("🤝 Select Partnership", partnerships, key="partnership_filter")

with col3:
    # Program filter
    programs = ['All Programs'] + sorted(df['program'].unique().tolist())
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
# KEY METRICS (FILTERED)
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
# INTERACTIVE DRILL-DOWN SECTIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🎯 Interactive Drill-Down Analytics <span class="drill-badge">Click to Explore</span></div>', unsafe_allow_html=True)

# Create tabs for different drill-down views
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Partnership Deep Dive",
    "🏫 School Distribution",
    "📅 Term Trends",
    "🎨 Program Breakdown",
    "⚠️ Non-Typical Placements"
])

# [Rest of the tabs code continues exactly as before, with the same structure...]
# For brevity, I'll include the key sections with proper data mapping

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

# Continue with remaining tabs using same structure...
# [School Distribution, Term Trends, Program Breakdown, Non-Typical Placements tabs]

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
        school_display['Referral Date'] = school_display['Referral Date'].dt.strftime('%d/%m/%Y')
        st.dataframe(school_display, use_container_width=True, hide_index=True)

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

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p style="font-size: 0.9rem;">📊 Live Allocation Dashboard | Cowandilla Learning Centre LBU</p>
    <p style="font-size: 0.85rem; color: #1A7A6E; font-weight: 600;">
        🔄 Connected to Supabase • Auto-refresh every 60 seconds • Live data
    </p>
</div>
""", unsafe_allow_html=True)
