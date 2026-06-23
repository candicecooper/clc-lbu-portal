"""
CLC-LBU ALLOCATION DASHBOARD (Page 32)
Enhanced with School Socioeconomic Data & Equity Analysis
Dark Neon Theme | Folium Adelaide Map | Multi-Select Filters
Real Excel Data Integration | Equity Analysis (ATSI/SWD/EALD)
Persistent Data Storage | School Profile Drill-Down

DEPLOYMENT: Render (clc-lbu-portal)
DATA: File upload → Persistent pickle storage
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from collections import Counter
import os
import pickle
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ============================================================================
# CONFIG & STYLING
# ============================================================================



# Helper function to safely access flag columns
def safe_flag_count(df, column, value='Yes'):
    """Safely count rows where a flag column equals a value."""
    if df is None or df.empty or column not in df.columns:
        return 0
    try:
        return len(df[df[column] == value])
    except:
        return 0

def safe_flag_filter(df, column, value='Yes'):
    """Safely filter by a flag column."""
    if df is None or df.empty or column not in df.columns:
        return pd.DataFrame()
    try:
        return df[df[column] == value]
    except:
        return pd.DataFrame()

def safe_school_count(df, flag_col, value='Yes'):
    """Safely get school value counts for a flag column."""
    if df is None or df.empty or flag_col not in df.columns or 'Referring_School' not in df.columns:
        return pd.Series()
    try:
        filtered_data = df[df[flag_col] == value]
        if filtered_data.empty:
            return pd.Series()
        return filtered_data['Referring_School'].value_counts().head(8)
    except:
        return pd.Series()
def safe_allocation_status_count(df, status='Allocated'):
    """Safely count allocation status."""
    if df is None or df.empty or 'Allocation_Status' not in df.columns:
        return 0
    try:
        return len(df[df['Allocation_Status'] == status])
    except:
        return 0

def safe_program_distribution(df):
    """Safely get program distribution."""
    if df is None or df.empty or 'Allocated_Program' not in df.columns:
        return pd.Series()
    try:
        return df['Allocated_Program'].value_counts()
    except:
        return pd.Series()

def safe_allocation_distribution(df):
    """Safely get allocation status distribution."""
    if df is None or df.empty or 'Allocation_Status' not in df.columns:
        return pd.Series()
    try:
        return df['Allocation_Status'].value_counts()
    except:
        return pd.Series()



st.set_page_config(
    page_title="Allocation Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark neon theme
st.markdown("""
<style>
    * { color: #ffffff; }
    
    [data-testid="stAppViewContainer"] { background-color: #0a0e27; }
    [data-testid="stSidebar"] { background-color: #0f1434; border-right: 2px solid #00e5ff; }
    [data-testid="stMainBlockContainer"] { background-color: #0a0e27; }
    
    h1, h2, h3, h4, h5, h6 { color: #00e5ff; font-weight: 700; }
    
    [data-testid="stSidebar"] h3 { font-size: 16px !important; color: #00e5ff; }
    [data-testid="stSidebar"] .stButton > button { font-size: 13px !important; min-height: auto !important; }
    
    .stButton > button {
        background: linear-gradient(135deg, #1a1f3a 0%, #0f1434 100%);
        border: 1px solid #00e5ff;
        color: #00e5ff;
        border-radius: 4px;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.6);
        border-color: #00ffff;
    }
    
    [data-testid="stTabs"] button {
        background-color: transparent;
        border: 1px solid #00e5ff;
        color: #00e5ff;
        border-radius: 4px;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        background-color: #00e5ff;
        color: #0a0e27;
    }
    
    .metric-box { background: rgba(0, 229, 255, 0.05); border: 1px solid #00e5ff; border-radius: 4px; padding: 12px; }
    
    .modebar-btn { background: transparent !important; box-shadow: none !important; border: none !important; }
    .modebar { background: transparent !important; }
    .modebar-btn svg { opacity: 0.6 !important; }
    
    [data-testid="stToolbar"] { visibility: hidden !important; height: 0 !important; }
    footer { visibility: hidden !important; height: 0 !important; }
    
    [data-testid="stFileUploadDropzone"] { box-shadow: none !important; }
    
    .stExpander { border: 1px solid #00e5ff; border-radius: 4px; }
    [data-testid="stExpander"] button { color: #00e5ff; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA PERSISTENCE & LOADING
# ============================================================================

DATA_FILE = "clc_lbu_data.pkl"

def save_data_to_file(data):
    """Save dataframe to pickle file"""
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(data, f)

def load_data_from_file():
    """Load dataframe from pickle file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return None
    return None

def clear_data_file():
    """Clear saved data file"""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

def load_school_socioeconomic_data():
    """Load school socioeconomic data from CSV"""
    import os
    
    # Try multiple locations in order of preference
    possible_paths = [
        # GitHub data folder (production on Render)
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'school_socioeconomic_data.csv'),
        # Relative path from app root
        'data/school_socioeconomic_data.csv',
        # Absolute paths for local development
        '/mnt/user-data/outputs/school_socioeconomic_data.csv',
        '/mnt/user-data/uploads/school_socioeconomic_data.csv',
    ]
    
    school_data = None
    for path in possible_paths:
        try:
            if os.path.exists(path):
                school_data = pd.read_csv(path)
                break
        except Exception as e:
            continue
    
    if school_data is None:
        return None
    
    # Convert Last_Updated to datetime
    if 'Last_Updated' in school_data.columns:
        try:
            school_data['Last_Updated'] = pd.to_datetime(school_data['Last_Updated'], errors='coerce')
        except:
            pass
    
    return school_data

# ============================================================================
# SESSION STATE & DATA INITIALIZATION
# ============================================================================

if 'data' not in st.session_state:
    st.session_state.data = load_data_from_file()

if 'drill_down_view' not in st.session_state:
    st.session_state.drill_down_view = None

# ============================================================================
# SIDEBAR: UPLOAD & FILTERS
# ============================================================================

st.sidebar.markdown("## 📊 ALLOCATION DASHBOARD")

# Upload section
st.sidebar.markdown("### 📤 Upload Data")
uploaded_file = st.sidebar.file_uploader("Choose CLC Allocation Excel file", type=['xlsx'])

if uploaded_file is not None:
    try:
        data = pd.read_excel(uploaded_file)
        st.session_state.data = data
        save_data_to_file(data)
        st.sidebar.success(f"✅ Data loaded: {len(data)} rows")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")

if st.session_state.data is not None:
    st.sidebar.write(f"**Current Data**: {len(st.session_state.data)} students")
    if st.sidebar.button("🔄 Clear Saved Data & Upload New"):
        clear_data_file()
        st.session_state.data = None
        st.rerun()

# Clear filters button
if st.sidebar.button("🔓 Show All Data (Clear All Filters)"):
    st.session_state.term_filter = set()
    st.session_state.year_filter = set()
    st.session_state.program_filter = set()

# Filters
if st.session_state.data is not None:
    with st.sidebar.expander("🔍 FILTERS", expanded=True):
        
        # Initialize filter session state
        if 'term_filter' not in st.session_state:
            st.session_state.term_filter = set()
        if 'year_filter' not in st.session_state:
            st.session_state.year_filter = set()
        if 'program_filter' not in st.session_state:
            st.session_state.program_filter = set()
        
        # Term filter
        st.markdown("**Term**")
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("All", key="term_all"):
                st.session_state.term_filter = set()
            if st.button("None", key="term_none"):
                st.session_state.term_filter = {1.0, 2.0, 3.0, 4.0}
        with c2:
            for term in [1.0, 2.0, 3.0, 4.0]:
                if st.checkbox(f"T{int(term)}", value=term not in st.session_state.term_filter, key=f"term_{int(term)}"):
                    st.session_state.term_filter.discard(term)
                else:
                    st.session_state.term_filter.add(term)
        
        # Year filter
        st.markdown("**Year**")
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("All", key="year_all"):
                st.session_state.year_filter = set()
            if st.button("None", key="year_none"):
                st.session_state.year_filter = {2025.0, 2026.0}
        with c2:
            if st.checkbox("2025", value=2025.0 not in st.session_state.year_filter, key="year_2025"):
                st.session_state.year_filter.discard(2025.0)
            else:
                st.session_state.year_filter.add(2025.0)
            if st.checkbox("2026", value=2026.0 not in st.session_state.year_filter, key="year_2026"):
                st.session_state.year_filter.discard(2026.0)
            else:
                st.session_state.year_filter.add(2026.0)
        
        # Program filter
        st.markdown("**Program**")
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("All", key="prog_all"):
                st.session_state.program_filter = set()
            if st.button("None", key="prog_none"):
                st.session_state.program_filter = {'JP', 'PY', 'SY'}
        with c2:
            for prog in ['JP', 'PY', 'SY']:
                if st.checkbox(prog, value=prog not in st.session_state.program_filter, key=f"prog_{prog}"):
                    st.session_state.program_filter.discard(prog)
                else:
                    st.session_state.program_filter.add(prog)

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

if st.session_state.data is None:
    st.error("❌ No data loaded. Please upload allocation file.")
else:
    
    # Apply filters
    data = st.session_state.data.copy()
    filtered = data.copy()
    
    # Filter by Term (if column exists)
    if 'Term' in filtered.columns and st.session_state.term_filter:
        filtered = filtered[~filtered['Term'].isin(st.session_state.term_filter)]
    
    # Filter by Year (if column exists)
    if 'Referral_Year' in filtered.columns and st.session_state.year_filter:
        filtered = filtered[~filtered['Referral_Year'].isin(st.session_state.year_filter)]
    
    # Filter by Program (if column exists)
    if 'Allocated_Program' in filtered.columns and st.session_state.program_filter:
        try:
            filtered = filtered[~filtered['Allocated_Program'].isin(st.session_state.program_filter)]
        except:
            pass  # If filtering fails, keep original data
    
    # ========================================================================
    # MAIN OVERVIEW (No drill-down)
    # ========================================================================
    
    if st.session_state.drill_down_view is None:
        
        st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
        # Build info string with proper error handling for missing columns
        info_parts = [f"Data: {len(filtered):,} students"]
        if 'Term' in filtered.columns and len(filtered['Term'].dropna()) > 0:
            terms = sorted([int(t) for t in filtered['Term'].dropna().unique()])
            info_parts.append(f"Terms: {terms}")
        if 'Referral_Year' in filtered.columns and len(filtered['Referral_Year'].dropna()) > 0:
            years = sorted([int(y) for y in filtered['Referral_Year'].dropna().unique()])
            info_parts.append(f"Years: {years}")
        st.markdown(f"*{' | '.join(info_parts)}*")
        
        # ====================================================================
        # METRICS & DRILL-DOWN BUTTONS
        # ====================================================================
        
        st.markdown("## 📈 Key Metrics")
        
        total_count = len(filtered)
        allocated_count = safe_allocation_status_count(filtered, 'Allocated')
        atsi_count = safe_flag_count(filtered, 'Flag_ATSI')
        swd_count = safe_flag_count(filtered, 'Flag_SWD')
        eald_count = safe_flag_count(filtered, 'Flag_EALD')
        
        # Count repeating students
        student_col = None
        for col in ['Student_Name', 'student_name', 'Student', 'Name', 'Full_Name']:
            if col in filtered.columns:
                student_col = col
                break
        
        repeating_count = 0
        if student_col:
            student_counts = filtered[student_col].value_counts()
            repeating_count = len(student_counts[student_counts > 1])
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        
        with c1:
            if st.button(f"📍 **TOTAL**\n{total_count}", use_container_width=True):
                st.session_state.drill_down_view = 'total'
                st.rerun()
        
        with c2:
            if st.button(f"✅ **ALLOCATED**\n{allocated_count}", use_container_width=True):
                st.session_state.drill_down_view = 'allocated'
                st.rerun()
        
        with c3:
            if st.button(f"🔴 **ATSI**\n{atsi_count}", use_container_width=True):
                st.session_state.drill_down_view = 'atsi'
                st.rerun()
        
        with c4:
            if st.button(f"🟠 **SWD**\n{swd_count}", use_container_width=True):
                st.session_state.drill_down_view = 'swd'
                st.rerun()
        
        with c5:
            if st.button(f"🟡 **EALD**\n{eald_count}", use_container_width=True):
                st.session_state.drill_down_view = 'eald'
                st.rerun()
        
        with c6:
            if st.button(f"🔄 **REPEATING**\n{repeating_count}", use_container_width=True):
                st.session_state.drill_down_view = 'repeating'
                st.rerun()
        
        # ====================================================================
        # PROGRAM DISTRIBUTION
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## Allocation Overview")
        
        c1, c2 = st.columns(2)
        
        with c1:
            if 'Allocated_Program' in filtered.columns and len(filtered) > 0:
                program_dist = safe_program_distribution(filtered)
                fig_prog = go.Figure([go.Bar(
                    x=program_dist.index,
                    y=program_dist.values,
                    marker_color=['#00e5ff', '#00ff00', '#ff6b6b'],
                    text=program_dist.values,
                    textposition='outside'
                )])
                fig_prog.update_xaxes(showgrid=False)
                fig_prog.update_yaxes(showgrid=False, dtick=5)
                fig_prog.update_layout(
                title="Program Distribution",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                height=350,
                showlegend=False,
                margin=dict(l=0, r=120, t=40, b=0)
            )
            st.plotly_chart(fig_prog, use_container_width=True)
        
        with c2:
            # Allocation status
            alloc_status = safe_allocation_distribution(filtered)
            colors_alloc = ['#00ff00' if x == 'Allocated' else '#ff6b6b' for x in alloc_status.index]
            fig_alloc = go.Figure([go.Bar(
                x=alloc_status.index,
                y=alloc_status.values,
                marker_color=colors_alloc,
                text=alloc_status.values,
                textposition='outside'
            )])
            fig_alloc.update_xaxes(showgrid=False)
            fig_alloc.update_yaxes(showgrid=False, dtick=5)
            fig_alloc.update_layout(
                title="Allocation Status",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                height=350,
                showlegend=False,
                margin=dict(l=0, r=120, t=40, b=0)
            )
            st.plotly_chart(fig_alloc, use_container_width=True)
        
        # ====================================================================
        # SCHOOL EQUITY CONTEXT - SOCIOECONOMIC ANALYSIS
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 🏫 School Equity Context - Socioeconomic & Demographic Analysis")
        
        school_ses_data = load_school_socioeconomic_data()
        
        if school_ses_data is not None:
            # Check data freshness
            latest_update = school_ses_data['Last_Updated'].max()
            days_old = (pd.Timestamp.now() - latest_update).days
            
            if days_old <= 90:
                st.success(f"✅ School data current (updated {days_old} days ago)")
            elif days_old <= 180:
                st.warning(f"⚠️ School data {days_old} days old - recommend refresh soon")
            else:
                st.error(f"❌ School data {days_old} days old - NEEDS UPDATE")
            
            st.caption(f"**Last Updated**: {latest_update.strftime('%Y-%m-%d')}")
            
            # Merge school data with CLC referrals
            if 'Referring_School' in filtered.columns:
                school_analysis = []
                
                for school_name in filtered['Referring_School'].unique():
                    if pd.isna(school_name):
                        continue
                    
                    school_students = filtered[filtered['Referring_School'] == school_name]
                    total_from_school = len(school_students)
                    
                    # Find school in SES data
                    school_info = school_ses_data[school_ses_data['School_Name'] == school_name]
                    
                    if len(school_info) > 0 and total_from_school > 0:
                        school_info = school_info.iloc[0]
                        
                        # Calculate percentages
                        indigenous_referrals = len(school_students[school_students['Flag_ATSI'] == 'Yes'])
                        swd_referrals = len(school_students[school_students['Flag_SWD'] == 'Yes'])
                        eald_referrals = len(school_students[school_students['Flag_EALD'] == 'Yes'])
                        
                        indigenous_pct = int(indigenous_referrals / total_from_school * 100) if total_from_school > 0 else 0
                        swd_pct = int(swd_referrals / total_from_school * 100) if total_from_school > 0 else 0
                        eald_pct = int(eald_referrals / total_from_school * 100) if total_from_school > 0 else 0
                        
                        # Calculate over-representation
                        indigenous_variance = indigenous_pct - int(school_info['Indigenous_Percent'])
                        eald_variance = eald_pct - int(school_info['EALD_Percent'])
                        
                        school_analysis.append({
                            'School': school_name,
                            'Total_Referrals': total_from_school,
                            'SEIFA_IRSAD': school_info['SEIFA_IRSAD'],
                            'Disadvantage': school_info['Disadvantage_Level'],
                            'School_Indigenous_%': int(school_info['Indigenous_Percent']),
                            'Referred_Indigenous_%': indigenous_pct,
                            'Indigenous_Variance': indigenous_variance,
                            'School_EALD_%': int(school_info['EALD_Percent']),
                            'Referred_EALD_%': eald_pct,
                            'EALD_Variance': eald_variance,
                            'SWD_%': swd_pct,
                            'Year12_Completion': int(school_info['Year12_Completion_Rate'])
                        })
                
                if school_analysis:
                    school_analysis_df = pd.DataFrame(school_analysis).sort_values('Total_Referrals', ascending=False).head(15)
                    
                    # Visualizations
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        st.markdown("### School Disadvantage vs CLC Referrals")
                        fig_ses = go.Figure([go.Scatter(
                            x=school_analysis_df['SEIFA_IRSAD'],
                            y=school_analysis_df['Total_Referrals'],
                            mode='markers+text',
                            marker=dict(
                                size=12,
                                color=school_analysis_df['Total_Referrals'],
                                colorscale='Reds',
                                showscale=True,
                                colorbar=dict(title="Referrals")
                            ),
                            text=school_analysis_df['School'],
                            textposition='top center',
                            textfont=dict(size=8, color='#ffffff')
                        )])
                        fig_ses.update_xaxes(title="SEIFA IRSAD (lower = more disadvantaged)", showgrid=False, color='#ffffff')
                        fig_ses.update_yaxes(title="# CLC Referrals", dtick=1, showgrid=False, color='#ffffff')
                        fig_ses.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), height=400, showlegend=False)
                        st.plotly_chart(fig_ses, use_container_width=True)
                    
                    with c2:
                        st.markdown("### Indigenous Over-Representation")
                        top_indigenous = school_analysis_df[school_analysis_df['Indigenous_Variance'] > 0].sort_values('Indigenous_Variance', ascending=True).tail(10)
                        if len(top_indigenous) > 0:
                            colors_ind = ['#ff6b6b' if x > 0 else '#00e5ff' for x in top_indigenous['Indigenous_Variance']]
                            fig_ind = go.Figure([go.Bar(
                                y=top_indigenous['School'],
                                x=top_indigenous['Indigenous_Variance'],
                                orientation='h',
                                marker_color=colors_ind,
                                text=top_indigenous['Indigenous_Variance'].astype(int),
                                textposition='outside'
                            )])
                            fig_ind.add_vline(x=0, line_dash="dash", line_color="#ffffff", opacity=0.3)
                            fig_ind.update_xaxes(showgrid=False, color='#ffffff')
                            fig_ind.update_yaxes(showgrid=False, color='#ffffff')
                            fig_ind.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), height=400, showlegend=False, xaxis_title="% Over-representation", margin=dict(l=180, r=120, t=0, b=0))
                            st.plotly_chart(fig_ind, use_container_width=True)
                    
                    # School profile table
                    st.markdown("### School Equity Profiles")
                    st.markdown("*School characteristics vs CLC referral patterns (top 15 referring schools)*")
                    
                    display_cols = ['School', 'Disadvantage', 'Total_Referrals', 'School_Indigenous_%', 'Referred_Indigenous_%', 'Indigenous_Variance', 'School_EALD_%', 'Referred_EALD_%', 'EALD_Variance', 'SWD_%']
                    st.dataframe(school_analysis_df[display_cols], use_container_width=True, hide_index=True)
                    
                    # Key insights
                    st.markdown("### 🔍 Key Insights")
                    
                    insight_cols = st.columns(2)
                    
                    with insight_cols[0]:
                        highest_indigenous = school_analysis_df.nlargest(1, 'Indigenous_Variance')
                        if len(highest_indigenous) > 0:
                            school = highest_indigenous.iloc[0]
                            st.write(f"🔴 **{school['School']}**: Indigenous students **over-represented by +{int(school['Indigenous_Variance'])}%**\n({int(school['School_Indigenous_%'])}% in school → {int(school['Referred_Indigenous_%'])}% of CLC referrals)")
                    
                    with insight_cols[1]:
                        most_disadvantaged = school_analysis_df[school_analysis_df['Disadvantage'] == 'Very High'].sort_values('Total_Referrals', ascending=False).head(1)
                        if len(most_disadvantaged) > 0:
                            school = most_disadvantaged.iloc[0]
                            st.write(f"⚠️ **{school['School']}** (SEIFA {int(school['SEIFA_IRSAD'])}): **Very High disadvantage**\n{int(school['Total_Referrals'])} CLC referrals | {int(school['Year12_Completion'])}% Yr12 completion")
        else:
            st.info("📋 **School Socioeconomic Data Not Loaded**\n\nTo enable school equity analysis:\n1. Download template: `school_socioeconomic_data_TEMPLATE.csv` from outputs\n2. Update with your SA school data (populate all fields)\n3. Save as `school_socioeconomic_data.csv` in data folder in GitHub\n4. Reload dashboard\n\nThis enables analysis of school disadvantage, Indigenous%, EALD% correlations with CLC referrals.")
        
        # ====================================================================
        # EQUITY ANALYSIS: SCHOOL REPRESENTATION
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 📊 School Referral Patterns by Equity Group")
        
        # Top schools by equity groups
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("### 🔴 Top Schools - ATSI Referrals")
            atsi_schools = safe_school_count(filtered, 'Flag_ATSI')
            fig_atsi = go.Figure([go.Bar(
                y=atsi_schools.index,
                x=atsi_schools.values,
                orientation='h',
                marker_color='#ff6b6b',
                text=atsi_schools.values,
                textposition='outside'
            )])
            fig_atsi.update_xaxes(showgrid=False, color='#ffffff')
            fig_atsi.update_yaxes(showgrid=False, color='#ffffff')
            fig_atsi.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=10), height=350, showlegend=False, margin=dict(l=150, r=80, t=0, b=0))
            st.plotly_chart(fig_atsi, use_container_width=True)
        
        with c2:
            st.markdown("### 🟠 Top Schools - SWD Referrals")
            swd_schools = safe_school_count(filtered, 'Flag_SWD')
            fig_swd = go.Figure([go.Bar(
                y=swd_schools.index,
                x=swd_schools.values,
                orientation='h',
                marker_color='#ffd93d',
                text=swd_schools.values,
                textposition='outside'
            )])
            fig_swd.update_xaxes(showgrid=False, color='#ffffff')
            fig_swd.update_yaxes(showgrid=False, color='#ffffff')
            fig_swd.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=10), height=350, showlegend=False, margin=dict(l=150, r=80, t=0, b=0))
            st.plotly_chart(fig_swd, use_container_width=True)
        
        with c3:
            st.markdown("### 🟡 Top Schools - EALD Referrals")
            eald_schools = safe_school_count(filtered, 'Flag_EALD')
            fig_eald = go.Figure([go.Bar(
                y=eald_schools.index,
                x=eald_schools.values,
                orientation='h',
                marker_color='#00ff00',
                text=eald_schools.values,
                textposition='outside'
            )])
            fig_eald.update_xaxes(showgrid=False, color='#ffffff')
            fig_eald.update_yaxes(showgrid=False, color='#ffffff')
            fig_eald.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=10), height=350, showlegend=False, margin=dict(l=150, r=80, t=0, b=0))
            st.plotly_chart(fig_eald, use_container_width=True)
        
        # ====================================================================
        # EALD ANALYSIS
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 🌐 EALD Allocation Analysis")
        
        st.markdown("### EALD Allocation Status by Program")
        for prog in ['JP', 'PY', 'SY']:
            prog_data = filtered[filtered['Allocated_Program'] == prog] if 'Allocated_Program' in filtered.columns else pd.DataFrame()
            if len(prog_data) > 0:
                eald_allocated = len(prog_data[(prog_data['Flag_EALD'] == 'Yes') & (prog_data['Allocation_Status'] == 'Allocated')]) if 'Flag_EALD' in prog_data.columns and 'Allocation_Status' in prog_data.columns else 0
                eald_waiting = len(prog_data[(prog_data['Flag_EALD'] == 'Yes') & (prog_data['Allocation_Status'] == 'On Waiting List')]) if 'Flag_EALD' in prog_data.columns and 'Allocation_Status' in prog_data.columns else 0
                eald_total = safe_flag_count(prog_data, 'Flag_EALD')
                
                if eald_total > 0:
                    alloc_rate = int(eald_allocated / eald_total * 100)
                    st.write(f"**{prog} Program**: {eald_total} EALD students → {eald_allocated} Allocated ({alloc_rate}%) | {eald_waiting} Waiting List")
        
        # ====================================================================
        # MULTIPLE DISABILITIES
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## Students with Multiple Disabilities")
        st.markdown("*Students with 2+ identified disabilities are shown in multiple categories below - these are the SAME students, not duplicates*")
        
        disability_cols = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
        
        # Count disabilities per student
        filtered_copy = filtered.copy()
        filtered_copy['disability_count'] = 0
        for col in disability_cols:
            if col in filtered_copy.columns:
                filtered_copy['disability_count'] += (filtered_copy[col] == 'Yes').astype(int)
        
        # Distribution of students by number of disabilities
        disability_dist = filtered_copy['disability_count'].value_counts().sort_index()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("No Identified Disabilities", int(disability_dist.get(0, 0)))
        c2.metric("1 Disability", int(disability_dist.get(1, 0)))
        c3.metric("2 Disabilities", int(disability_dist.get(2, 0)))
        c4.metric("3+ Disabilities", int(disability_dist.get(3, 0)) + int(disability_dist.get(4, 0)) + int(disability_dist.get(5, 0)))
        
        # Disability breakdown
        st.markdown("### Disability Type Distribution")
        
        disability_counts = {}
        for col in disability_cols:
            if col in filtered.columns:
                count = len(filtered[filtered[col] == 'Yes'])
                disability_name = col.replace('Flag_', '').replace('_', ' ')
                disability_counts[disability_name] = count
        
        if disability_counts:
            disability_df = pd.DataFrame(list(disability_counts.items()), columns=['Disability', 'Count']).sort_values('Count', ascending=True)
            
            fig_dis = go.Figure([go.Bar(
                y=disability_df['Disability'],
                x=disability_df['Count'],
                orientation='h',
                marker_color='#00e5ff',
                text=disability_df['Count'],
                textposition='outside'
            )])
            fig_dis.update_xaxes(showgrid=False, color='#ffffff')
            fig_dis.update_yaxes(showgrid=False, color='#ffffff')
            fig_dis.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False, margin=dict(l=150, r=80, t=0, b=0))
            st.plotly_chart(fig_dis, use_container_width=True)
        
        # ====================================================================
        # PARTNERSHIP MAP
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 🗺️ Adelaide Partnership Map")
        
        # Partnership coordinates (Adelaide)
        partnership_coords = {
            'Inner West': (-34.8500, 139.0000),
            'Le Fevre Peninsula': (-34.8200, 138.9500),
            'Holdfast': (-35.1000, 139.1500),
            'West Torrens': (-34.8800, 139.0200),
            'Playford': (-34.6800, 139.1500),
            'Onkaparinga': (-35.1500, 139.2000),
        }
        
        m = folium.Map(
            location=[-34.92, 139.10],
            zoom_start=11,
            tiles='CartoDB positron'
        )
        
        partnership_counts = filtered['Partnership_Area'].value_counts()
        max_count = partnership_counts.max()
        
        for area, (lat, lng) in partnership_coords.items():
            count = partnership_counts.get(area, 0)
            if count > 0:
                intensity = count / max_count
                color = '#ff6b6b' if intensity > 0.7 else '#ffd93d' if intensity > 0.4 else '#00e5ff'
                
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=10 + (intensity * 15),
                    popup=f"{area}<br>{count} students",
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=2
                ).add_to(m)
        
        st_folium(m, width=1200, height=400)
    
    # ========================================================================
    # DRILL-DOWN VIEWS
    # ========================================================================
    
    else:
        
        # Back button
        if st.button("← Back to Overview"):
            st.session_state.drill_down_view = None
            st.rerun()
        
        view = st.session_state.drill_down_view
        
        # Filter data based on drill-down view
        if view == 'total':
            drill_data = filtered
            title = "📍 Total Students"
        elif view == 'allocated':
            drill_data = filtered[filtered['Allocation_Status'] == 'Allocated'] if 'Allocation_Status' in filtered.columns else pd.DataFrame()
            title = "✅ Allocated Students"
        elif view == 'atsi':
            drill_data = safe_flag_filter(filtered, 'Flag_ATSI')
            title = "🔴 ATSI Students"
        elif view == 'swd':
            drill_data = safe_flag_filter(filtered, 'Flag_SWD')
            title = "🟠 SWD Students"
        elif view == 'eald':
            drill_data = safe_flag_filter(filtered, 'Flag_EALD')
            title = "🟡 EALD Students"
        elif view == 'repeating':
            # Find repeating students
            student_col = None
            for col in ['Student_Name', 'student_name', 'Student', 'Name', 'Full_Name']:
                if col in filtered.columns:
                    student_col = col
                    break
            
            if student_col:
                student_counts = filtered[student_col].value_counts()
                repeating_students = student_counts[student_counts > 1].index
                drill_data = filtered[filtered[student_col].isin(repeating_students)]
            else:
                drill_data = filtered
            
            title = "🔄 Repeating Students"
        
        st.markdown(f"# {title}")
        st.markdown(f"*{len(drill_data)} students*")
        
        # Tabs for drill-down
        tabs = st.tabs(["Overview", "By Program", "By Partnership", "By School", "Disability Profile", "Trends"])
        
        with tabs[0]:  # Overview
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", len(drill_data))
            c2.metric("ATSI", safe_flag_count(drill_data, 'Flag_ATSI'))
            c3.metric("SWD", safe_flag_count(drill_data, 'Flag_SWD'))
            c4.metric("EALD", safe_flag_count(drill_data, 'Flag_EALD'))
            
            # Program distribution
            prog_dist = safe_program_distribution(drill_data)
            fig = go.Figure([go.Pie(labels=prog_dist.index, values=prog_dist.values)])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'))
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[1]:  # By Program
            for prog in ['JP', 'PY', 'SY']:
                prog_data = drill_data[drill_data['Allocated_Program'] == prog] if 'Allocated_Program' in drill_data.columns else pd.DataFrame()
                if len(prog_data) > 0:
                    st.markdown(f"### {prog} Program ({len(prog_data)} students)")
                    st.write(f"**ATSI**: {safe_flag_count(prog_data, 'Flag_ATSI')} | **SWD**: {safe_flag_count(prog_data, 'Flag_SWD')} | **EALD**: {safe_flag_count(prog_data, 'Flag_EALD')}")
        
        with tabs[2]:  # By Partnership
            partnership_dist = drill_data['Partnership_Area'].value_counts().head(12)
            fig = go.Figure([go.Bar(
                y=partnership_dist.index,
                x=partnership_dist.values,
                orientation='h',
                marker_color='#00e5ff'
            )])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, margin=dict(l=200, r=80, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[3]:  # By School
            school_dist = drill_data['Referring_School'].value_counts().head(12)
            fig = go.Figure([go.Bar(
                y=school_dist.index,
                x=school_dist.values,
                orientation='h',
                marker_color='#00ff00'
            )])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, margin=dict(l=200, r=80, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[4]:  # Disability Profile
            st.markdown("### Disability Distribution in this Cohort")
            disability_cols = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
            disability_counts = {}
            for col in disability_cols:
                if col in drill_data.columns:
                    count = len(drill_data[drill_data[col] == 'Yes'])
                    disability_name = col.replace('Flag_', '').replace('_', ' ')
                    disability_counts[disability_name] = count
            
            if disability_counts:
                dis_df = pd.DataFrame(list(disability_counts.items()), columns=['Disability', 'Count']).sort_values('Count', ascending=True)
                fig = go.Figure([go.Bar(
                    y=dis_df['Disability'],
                    x=dis_df['Count'],
                    orientation='h',
                    marker_color='#ffd93d'
                )])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=350, margin=dict(l=150, r=80, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
        
        with tabs[5]:  # Trends
            st.markdown("### Allocation Trends by Term")
            valid_terms = sorted([t for t in drill_data['Term'].unique() if pd.notna(t)])
            
            if len(valid_terms) > 1:
                trend_data = []
                for term in valid_terms:
                    term_count = len(drill_data[drill_data['Term'] == term])
                    trend_data.append({'Term': f"T{int(term)}", 'Count': term_count})
                
                trend_df = pd.DataFrame(trend_data)
                fig = go.Figure([go.Scatter(
                    x=trend_df['Term'],
                    y=trend_df['Count'],
                    mode='lines+markers',
                    marker=dict(size=10, color='#00e5ff'),
                    line=dict(color='#00e5ff', width=2)
                )])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=350)
                st.plotly_chart(fig, use_container_width=True)
