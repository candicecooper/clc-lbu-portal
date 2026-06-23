"""
CLC-LBU ALLOCATION DASHBOARD (Page 32) - COMPLETE & ENHANCED
Enhanced with School Socioeconomic Data & Comprehensive Equity Analysis
16 Drill-Down Metrics | 7-Tab EALD Analysis | ATSI/SWD/ASD Deep-Dive
Dark Neon Theme | Folium Adelaide Map | Multi-Select Filters
Real Excel Data Integration | Persistent Data Storage

DEPLOYMENT: Render (clc-lbu-portal)
FEATURES: Enhanced metrics, comprehensive EALD, allocation bottleneck analysis
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

# Define disability columns globally (used throughout the app)
disability_cols = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']

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
    
    .plotly .paper { background-color: #0a0e27 !important; }
    .hovertext { background: #0f1434 !important; color: #ffffff !important; border: 1px solid #00e5ff !important; border-radius: 4px !important; box-shadow: 0 0 10px rgba(0, 229, 255, 0.3) !important; }
    .plotly-graph-div { background: #0a0e27 !important; }
    .legendtext, .legend { background: rgba(15, 20, 52, 0.9) !important; }
    .xtick, .ytick { color: #ffffff !important; }
    .gridlayer, .zerolinelayer { opacity: 0.1 !important; }
    .js-plotly-plot .plotly-graph-div { background-color: #0a0e27 !important; }
    g.hoverlayer { filter: invert(0) !important; }
    g.hoverlayer path { fill: #0f1434 !important; stroke: #00e5ff !important; }
    text.hovertext { fill: #ffffff !important; }
    text { fill: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA PERSISTENCE & LOADING
# ============================================================================

DATA_FILE = "clc_lbu_data.pkl"

def save_data_to_file(data):
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(data, f)

def load_data_from_file():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return None
    return None

def clear_data_file():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

def load_school_socioeconomic_data():
    import os
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'school_socioeconomic_data.csv'),
        'data/school_socioeconomic_data.csv',
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

if st.sidebar.button("🔓 Show All Data (Clear All Filters)"):
    st.session_state.term_filter = set()
    st.session_state.year_filter = set()
    st.session_state.program_filter = set()

if st.session_state.data is not None:
    with st.sidebar.expander("🔍 FILTERS", expanded=True):
        
        if 'term_filter' not in st.session_state:
            st.session_state.term_filter = set()
        if 'year_filter' not in st.session_state:
            st.session_state.year_filter = set()
        if 'program_filter' not in st.session_state:
            st.session_state.program_filter = set()
        
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
    
    data = st.session_state.data.copy()
    filtered = data.copy()
    
    if 'Term' in filtered.columns and st.session_state.term_filter:
        filtered = filtered[~filtered['Term'].isin(st.session_state.term_filter)]
    
    if 'Referral_Year' in filtered.columns and st.session_state.year_filter:
        filtered = filtered[~filtered['Referral_Year'].isin(st.session_state.year_filter)]
    
    if 'Allocated_Program' in filtered.columns and st.session_state.program_filter:
        try:
            filtered = filtered[~filtered['Allocated_Program'].isin(st.session_state.program_filter)]
        except:
            pass
    
    if st.session_state.drill_down_view is None:
        
        st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
        info_parts = [f"Data: {len(filtered):,} students"]
        if 'Term' in filtered.columns and len(filtered['Term'].dropna()) > 0:
            terms = sorted([int(t) for t in filtered['Term'].dropna().unique()])
            info_parts.append(f"Terms: {terms}")
        if 'Referral_Year' in filtered.columns and len(filtered['Referral_Year'].dropna()) > 0:
            years = sorted([int(y) for y in filtered['Referral_Year'].dropna().unique()])
            info_parts.append(f"Years: {years}")
        st.markdown(f"*{' | '.join(info_parts)}*")
        
        # ====================================================================
        # ENHANCED KEY METRICS (16 DRILL-DOWNS)
        # ====================================================================
        
        st.markdown("## 📈 Key Metrics - Comprehensive Analysis")
        
        total_count = len(filtered)
        allocated_count = safe_allocation_status_count(filtered, 'Allocated')
        waiting_count = safe_allocation_status_count(filtered, 'On Waiting List')
        atsi_count = safe_flag_count(filtered, 'Flag_ATSI')
        swd_count = safe_flag_count(filtered, 'Flag_SWD')
        eald_count = safe_flag_count(filtered, 'Flag_EALD')
        asd_count = safe_flag_count(filtered, 'Flag_ASD')
        
        filtered_copy = filtered.copy()
        filtered_copy['disability_count'] = 0
        for col in disability_cols:
            if col in filtered_copy.columns:
                filtered_copy['disability_count'] += (filtered_copy[col] == 'Yes').astype(int)
        multi_disability_count = len(filtered_copy[filtered_copy['disability_count'] >= 2])
        
        student_col = None
        for col in ['Student_Name', 'student_name', 'Student', 'Name', 'Full_Name']:
            if col in filtered.columns:
                student_col = col
                break
        
        repeating_count = 0
        if student_col:
            student_counts = filtered[student_col].value_counts()
            repeating_count = len(student_counts[student_counts > 1])
        
        partnership_count = filtered['Partnership_Area'].nunique() if 'Partnership_Area' in filtered.columns else 0
        school_count = filtered['Referring_School'].nunique() if 'Referring_School' in filtered.columns else 0
        year_2025_count = len(filtered[filtered['Referral_Year'] == 2025.0]) if 'Referral_Year' in filtered.columns else 0
        year_2026_count = len(filtered[filtered['Referral_Year'] == 2026.0]) if 'Referral_Year' in filtered.columns else 0
        early_referral_count = len(filtered[filtered['Term'] == 1.0]) if 'Term' in filtered.columns else 0
        
        st.markdown("### Primary Cohorts")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            if st.button(f"📍 **TOTAL**\n{total_count}", use_container_width=True, key="metric_total"):
                st.session_state.drill_down_view = 'total'
                st.rerun()
        with col2:
            if st.button(f"✅ **ALLOCATED**\n{allocated_count}", use_container_width=True, key="metric_allocated"):
                st.session_state.drill_down_view = 'allocated'
                st.rerun()
        with col3:
            if st.button(f"⏳ **WAITING**\n{waiting_count}", use_container_width=True, key="metric_waiting"):
                st.session_state.drill_down_view = 'waiting'
                st.rerun()
        with col4:
            if st.button(f"🔴 **ATSI**\n{atsi_count}", use_container_width=True, key="metric_atsi"):
                st.session_state.drill_down_view = 'atsi'
                st.rerun()
        with col5:
            if st.button(f"🟠 **SWD**\n{swd_count}", use_container_width=True, key="metric_swd"):
                st.session_state.drill_down_view = 'swd'
                st.rerun()
        with col6:
            if st.button(f"🟡 **EALD**\n{eald_count}", use_container_width=True, key="metric_eald"):
                st.session_state.drill_down_view = 'eald'
                st.rerun()
        
        st.markdown("### Disability & Cohort Profiles")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            if st.button(f"🧠 **ASD**\n{asd_count}", use_container_width=True, key="metric_asd"):
                st.session_state.drill_down_view = 'asd'
                st.rerun()
        with col2:
            if st.button(f"🔀 **MULTI-\nDISABILITY**\n{multi_disability_count}", use_container_width=True, key="metric_multi"):
                st.session_state.drill_down_view = 'multi_disability'
                st.rerun()
        with col3:
            if st.button(f"🔄 **REPEATING**\n{repeating_count}", use_container_width=True, key="metric_repeating"):
                st.session_state.drill_down_view = 'repeating'
                st.rerun()
        with col4:
            if st.button(f"📅 **2025\nCOHORT**\n{year_2025_count}", use_container_width=True, key="metric_2025"):
                st.session_state.drill_down_view = 'cohort_2025'
                st.rerun()
        with col5:
            if st.button(f"📅 **2026\nCOHORT**\n{year_2026_count}", use_container_width=True, key="metric_2026"):
                st.session_state.drill_down_view = 'cohort_2026'
                st.rerun()
        with col6:
            if st.button(f"🌍 **EARLY\nREFERRALS**\n{early_referral_count}", use_container_width=True, key="metric_early"):
                st.session_state.drill_down_view = 'early_referrals'
                st.rerun()
        
        st.markdown("### Referral Sources & Patterns")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button(f"🏛️ **PARTNER\nAREAS**\n{partnership_count}", use_container_width=True, key="metric_partnership"):
                st.session_state.drill_down_view = 'partnership_breakdown'
                st.rerun()
        with col2:
            if st.button(f"🏫 **REFERRING\nSCHOOLS**\n{school_count}", use_container_width=True, key="metric_schools"):
                st.session_state.drill_down_view = 'school_breakdown'
                st.rerun()
        with col3:
            atsi_and_swd = len(filtered[(filtered['Flag_ATSI'] == 'Yes') & (filtered['Flag_SWD'] == 'Yes')])
            if st.button(f"🔗 **ATSI +\nSWD**\n{atsi_and_swd}", use_container_width=True, key="metric_atsi_swd"):
                st.session_state.drill_down_view = 'atsi_swd_overlap'
                st.rerun()
        with col4:
            eald_and_asd = len(filtered[(filtered['Flag_EALD'] == 'Yes') & (filtered['Flag_ASD'] == 'Yes')])
            if st.button(f"🔗 **EALD +\nASD**\n{eald_and_asd}", use_container_width=True, key="metric_eald_asd"):
                st.session_state.drill_down_view = 'eald_asd_overlap'
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
        # SCHOOL EQUITY CONTEXT
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 🏫 School Equity Context - Socioeconomic & Demographic Analysis")
        
        school_ses_data = load_school_socioeconomic_data()
        
        if school_ses_data is not None:
            latest_update = school_ses_data['Last_Updated'].max()
            days_old = (pd.Timestamp.now() - latest_update).days
            
            if days_old <= 90:
                st.success(f"✅ School data current (updated {days_old} days ago)")
            elif days_old <= 180:
                st.warning(f"⚠️ School data {days_old} days old - recommend refresh soon")
            else:
                st.error(f"❌ School data {days_old} days old - NEEDS UPDATE")
            
            st.caption(f"**Last Updated**: {latest_update.strftime('%Y-%m-%d')}")
            
            if 'Referring_School' in filtered.columns:
                school_analysis = []
                
                for school_name in filtered['Referring_School'].unique():
                    if pd.isna(school_name):
                        continue
                    
                    school_students = filtered[filtered['Referring_School'] == school_name]
                    total_from_school = len(school_students)
                    school_info = school_ses_data[school_ses_data['School_Name'] == school_name]
                    
                    if len(school_info) > 0 and total_from_school > 0:
                        school_info = school_info.iloc[0]
                        
                        indigenous_referrals = len(school_students[school_students['Flag_ATSI'] == 'Yes'])
                        swd_referrals = len(school_students[school_students['Flag_SWD'] == 'Yes'])
                        eald_referrals = len(school_students[school_students['Flag_EALD'] == 'Yes'])
                        
                        indigenous_pct = int(indigenous_referrals / total_from_school * 100) if total_from_school > 0 else 0
                        swd_pct = int(swd_referrals / total_from_school * 100) if total_from_school > 0 else 0
                        eald_pct = int(eald_referrals / total_from_school * 100) if total_from_school > 0 else 0
                        
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
                    
                    st.markdown("### School Equity Profiles")
                    st.markdown("*School characteristics vs CLC referral patterns (top 15 referring schools)*")
                    display_cols = ['School', 'Disadvantage', 'Total_Referrals', 'School_Indigenous_%', 'Referred_Indigenous_%', 'Indigenous_Variance', 'School_EALD_%', 'Referred_EALD_%', 'EALD_Variance', 'SWD_%']
                    st.dataframe(school_analysis_df[display_cols], use_container_width=True, hide_index=True)
                    
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
            st.info("📋 **School Socioeconomic Data Not Loaded**")
        
        # ====================================================================
        # EQUITY ANALYSIS: SCHOOL REPRESENTATION
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 📊 School Referral Patterns by Equity Group")
        
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
        # COMPREHENSIVE EALD ANALYSIS (7 TABS)
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 🌐 COMPREHENSIVE EALD ANALYSIS")
        
        if 'Flag_EALD' in filtered.columns:
            
            eald_students = safe_flag_filter(filtered, 'Flag_EALD')
            eald_total = len(eald_students)
            
            if eald_total > 0:
                
                eald_pct = (eald_total / len(filtered) * 100) if len(filtered) > 0 else 0
                
                st.markdown(f"### EALD Representation: **{eald_pct:.1f}%** ({eald_total}/{len(filtered)} students)")
                
                if eald_pct >= 20:
                    st.warning(f"⚠️ **HIGH EALD REPRESENTATION**: {eald_pct:.1f}% of referrals")
                elif eald_pct >= 15:
                    st.info(f"📊 **SIGNIFICANT EALD COHORT**: {eald_pct:.1f}% of referrals")
                
                # EALD TABS
                eald_tabs = st.tabs(["Overview", "By Program", "By School", "Allocation", "Comorbidity", "Trends", "Partnership"])
                
                # TAB 1: OVERVIEW
                with eald_tabs[0]:
                    st.markdown("### EALD Student Profile")
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    eald_allocated = safe_allocation_status_count(eald_students, 'Allocated')
                    eald_waiting = safe_allocation_status_count(eald_students, 'On Waiting List')
                    eald_allocation_rate = (eald_allocated / eald_total * 100) if eald_total > 0 else 0
                    eald_atsi = safe_flag_count(eald_students, 'Flag_ATSI')
                    eald_swd = safe_flag_count(eald_students, 'Flag_SWD')
                    
                    with col1:
                        st.metric("Total EALD", eald_total)
                    with col2:
                        st.metric("Allocated", eald_allocated, delta=f"{eald_allocation_rate:.0f}%")
                    with col3:
                        st.metric("Waiting", eald_waiting)
                    with col4:
                        st.metric("Also ATSI", eald_atsi)
                    with col5:
                        st.metric("Also SWD", eald_swd)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        allocation_dist = pd.Series({
                            'Allocated': eald_allocated,
                            'Waiting': eald_waiting,
                            'Other': eald_total - eald_allocated - eald_waiting
                        })
                        allocation_dist = allocation_dist[allocation_dist > 0]
                        
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=allocation_dist.index,
                            values=allocation_dist.values,
                            marker=dict(colors=['#00ff00', '#ff6b6b', '#ffd93d'])
                        )])
                        fig_pie.update_layout(
                            title='EALD Allocation Status',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#ffffff'),
                            height=350
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    with col2:
                        prog_dist = eald_students['Allocated_Program'].value_counts() if 'Allocated_Program' in eald_students.columns else pd.Series()
                        
                        if len(prog_dist) > 0:
                            fig_prog = go.Figure([go.Bar(
                                x=prog_dist.index,
                                y=prog_dist.values,
                                marker_color=['#00e5ff', '#00ff00', '#ff6b6b'],
                                text=prog_dist.values,
                                textposition='outside'
                            )])
                            fig_prog.update_layout(
                                title='EALD by Program',
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#ffffff'),
                                height=350,
                                showlegend=False
                            )
                            st.plotly_chart(fig_prog, use_container_width=True)
                
                # TAB 2: BY PROGRAM
                with eald_tabs[1]:
                    st.markdown("### EALD Analysis by Program")
                    
                    program_analysis = []
                    for prog in ['JP', 'PY', 'SY']:
                        prog_eald = eald_students[eald_students['Allocated_Program'] == prog] if 'Allocated_Program' in eald_students.columns else pd.DataFrame()
                        
                        if len(prog_eald) > 0:
                            allocated = safe_allocation_status_count(prog_eald, 'Allocated')
                            waiting = safe_allocation_status_count(prog_eald, 'On Waiting List')
                            total = len(prog_eald)
                            alloc_rate = (allocated / total * 100) if total > 0 else 0
                            
                            atsi = safe_flag_count(prog_eald, 'Flag_ATSI')
                            swd = safe_flag_count(prog_eald, 'Flag_SWD')
                            asd = safe_flag_count(prog_eald, 'Flag_ASD')
                            adhd = safe_flag_count(prog_eald, 'Flag_ADHD')
                            
                            program_analysis.append({
                                'Program': prog,
                                'Total': total,
                                'Allocated': allocated,
                                'Waiting': waiting,
                                'Allocation %': f"{alloc_rate:.0f}%",
                                'Also ATSI': atsi,
                                'Also SWD': swd,
                                'Also ASD': asd,
                                'Also ADHD': adhd
                            })
                    
                    if program_analysis:
                        prog_df = pd.DataFrame(program_analysis)
                        st.dataframe(prog_df, use_container_width=True, hide_index=True)
                        
                        fig = go.Figure()
                        prog_df_numeric = prog_df.copy()
                        prog_df_numeric['Allocated'] = pd.to_numeric(prog_df_numeric['Allocated'])
                        prog_df_numeric['Waiting'] = pd.to_numeric(prog_df_numeric['Waiting'])
                        
                        fig.add_trace(go.Bar(x=prog_df_numeric['Program'], y=prog_df_numeric['Allocated'], name='Allocated', marker_color='#00ff00'))
                        fig.add_trace(go.Bar(x=prog_df_numeric['Program'], y=prog_df_numeric['Waiting'], name='Waiting', marker_color='#ff6b6b'))
                        
                        fig.update_layout(
                            title='EALD: Allocated vs Waiting by Program',
                            barmode='stack',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#ffffff'),
                            height=350,
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # TAB 3: BY SCHOOL
                with eald_tabs[2]:
                    st.markdown("### Top EALD Referring Schools")
                    
                    if 'Referring_School' in eald_students.columns:
                        school_eald = eald_students['Referring_School'].value_counts().head(12)
                        
                        fig = go.Figure([go.Bar(
                            y=school_eald.index,
                            x=school_eald.values,
                            orientation='h',
                            marker_color='#00e5ff',
                            text=school_eald.values,
                            textposition='outside'
                        )])
                        fig.update_layout(
                            title='Schools with Most EALD Referrals',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#ffffff'),
                            height=400,
                            margin=dict(l=200, r=80, t=0, b=0),
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("### School Breakdown")
                        school_detail = []
                        for school in school_eald.index:
                            school_eald_data = eald_students[eald_students['Referring_School'] == school]
                            total = len(school_eald_data)
                            allocated = safe_allocation_status_count(school_eald_data, 'Allocated')
                            waiting = safe_allocation_status_count(school_eald_data, 'On Waiting List')
                            alloc_rate = (allocated / total * 100) if total > 0 else 0
                            
                            school_detail.append({
                                'School': school,
                                'EALD Students': total,
                                'Allocated': allocated,
                                'Waiting': waiting,
                                'Allocation %': f"{alloc_rate:.0f}%"
                            })
                        
                        if school_detail:
                            detail_df = pd.DataFrame(school_detail)
                            st.dataframe(detail_df, use_container_width=True, hide_index=True)
                
                # TAB 4: ALLOCATION
                with eald_tabs[3]:
                    st.markdown("### EALD Allocation Deep-Dive")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### Allocation Bottlenecks by Program")
                        
                        bottleneck_data = []
                        for prog in ['JP', 'PY', 'SY']:
                            prog_eald = eald_students[eald_students['Allocated_Program'] == prog] if 'Allocated_Program' in eald_students.columns else pd.DataFrame()
                            if len(prog_eald) > 0:
                                waiting = safe_allocation_status_count(prog_eald, 'On Waiting List')
                                total = len(prog_eald)
                                waiting_pct = (waiting / total * 100) if total > 0 else 0
                                bottleneck_data.append({'Program': prog, 'Waiting %': waiting_pct, 'Waiting Count': waiting})
                        
                        if bottleneck_data:
                            bottleneck_df = pd.DataFrame(bottleneck_data)
                            fig = go.Figure([go.Bar(
                                x=bottleneck_df['Program'],
                                y=bottleneck_df['Waiting %'],
                                marker_color=['#ff6b6b' if x > 30 else '#ffd93d' if x > 15 else '#00ff00' for x in bottleneck_df['Waiting %']],
                                text=[f"{int(x)}% ({int(bottleneck_df.loc[idx, 'Waiting Count'])})" for idx, x in enumerate(bottleneck_df['Waiting %'])],
                                textposition='outside'
                            )])
                            fig.update_layout(
                                title='EALD Waiting List % by Program',
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#ffffff'),
                                height=350,
                                showlegend=False
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.markdown("### EALD Time in System")
                        
                        if 'Term' in eald_students.columns:
                            term_allocation = []
                            for term in sorted([t for t in eald_students['Term'].unique() if pd.notna(t)]):
                                term_eald = eald_students[eald_students['Term'] == term]
                                allocated = safe_allocation_status_count(term_eald, 'Allocated')
                                total = len(term_eald)
                                alloc_rate = (allocated / total * 100) if total > 0 else 0
                                term_allocation.append({'Term': f"T{int(term)}", 'Allocation %': alloc_rate})
                            
                            if term_allocation:
                                term_df = pd.DataFrame(term_allocation)
                                fig = go.Figure([go.Scatter(
                                    x=term_df['Term'],
                                    y=term_df['Allocation %'],
                                    mode='lines+markers',
                                    marker=dict(size=12, color='#00e5ff'),
                                    line=dict(color='#00e5ff', width=3),
                                    fill='tozeroy'
                                )])
                                fig.update_layout(
                                    title='EALD Allocation Rate by Term',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='#ffffff'),
                                    height=350,
                                    xaxis=dict(showgrid=False),
                                    yaxis=dict(showgrid=False)
                                )
                                st.plotly_chart(fig, use_container_width=True)
                
                # TAB 5: COMORBIDITY
                with eald_tabs[4]:
                    st.markdown("### EALD Students: Co-occurring Disabilities")
                    
                    disability_cols_full = ['Flag_ATSI', 'Flag_ASD', 'Flag_ADHD', 'Flag_SWD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
                    
                    comorbidity_data = {}
                    for col in disability_cols_full:
                        if col in eald_students.columns:
                            count = safe_flag_count(eald_students, col)
                            pct = (count / eald_total * 100) if eald_total > 0 else 0
                            disability_name = col.replace('Flag_', '').replace('_', ' ')
                            comorbidity_data[disability_name] = {'Count': count, 'Percentage': pct}
                    
                    if comorbidity_data:
                        comorbid_df = pd.DataFrame(comorbidity_data).T.sort_values('Percentage', ascending=True)
                        
                        fig = go.Figure([go.Bar(
                            y=comorbid_df.index,
                            x=comorbid_df['Percentage'],
                            orientation='h',
                            marker_color='#ffd93d',
                            text=[f"{int(comorbid_df.loc[idx, 'Count'])}" for idx in comorbid_df.index],
                            textposition='outside'
                        )])
                        fig.update_layout(
                            title='Disabilities in EALD Students',
                            xaxis_title='Percentage of EALD Students (%)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#ffffff'),
                            height=400,
                            margin=dict(l=180, r=80, t=40, b=0),
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.dataframe(comorbid_df, use_container_width=True)
                
                # TAB 6: TRENDS
                with eald_tabs[5]:
                    st.markdown("### EALD Trends Over Time")
                    
                    if 'Term' in eald_students.columns and 'Referral_Year' in eald_students.columns:
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### Referrals by Term")
                            term_counts = eald_students['Term'].value_counts().sort_index()
                            
                            fig = go.Figure([go.Bar(
                                x=[f"T{int(t)}" for t in term_counts.index],
                                y=term_counts.values,
                                marker_color='#00e5ff',
                                text=term_counts.values,
                                textposition='outside'
                            )])
                            fig.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#ffffff'),
                                height=350,
                                showlegend=False
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.markdown("#### Referrals by Year")
                            year_counts = eald_students['Referral_Year'].value_counts().sort_index()
                            
                            fig = go.Figure([go.Bar(
                                x=[f"{int(y)}" for y in year_counts.index],
                                y=year_counts.values,
                                marker_color='#00ff00',
                                text=year_counts.values,
                                textposition='outside'
                            )])
                            fig.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#ffffff'),
                                height=350,
                                showlegend=False
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                # TAB 7: PARTNERSHIP
                with eald_tabs[6]:
                    st.markdown("### EALD by Partnership Area")
                    
                    if 'Partnership_Area' in eald_students.columns:
                        partnership_eald = eald_students['Partnership_Area'].value_counts()
                        
                        fig = go.Figure([go.Bar(
                            y=partnership_eald.index,
                            x=partnership_eald.values,
                            orientation='h',
                            marker_color='#ff6b6b',
                            text=partnership_eald.values,
                            textposition='outside'
                        )])
                        fig.update_layout(
                            title='EALD Students by Partnership Area',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#ffffff'),
                            height=400,
                            margin=dict(l=150, r=80, t=0, b=0),
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("### Partnership Detail")
                        partnership_detail = []
                        for area in partnership_eald.index:
                            area_eald = eald_students[eald_students['Partnership_Area'] == area]
                            total = len(area_eald)
                            allocated = safe_allocation_status_count(area_eald, 'Allocated')
                            waiting = safe_allocation_status_count(area_eald, 'On Waiting List')
                            alloc_rate = (allocated / total * 100) if total > 0 else 0
                            
                            partnership_detail.append({
                                'Partnership Area': area,
                                'EALD Students': total,
                                'Allocated': allocated,
                                'Waiting': waiting,
                                'Allocation %': f"{alloc_rate:.0f}%"
                            })
                        
                        if partnership_detail:
                            detail_df = pd.DataFrame(partnership_detail)
                            st.dataframe(detail_df, use_container_width=True, hide_index=True)
        
        # ====================================================================
        # ATSI, SWD, ASD ANALYSIS SECTIONS
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## 🔴 ATSI Enrollment Trends by Program & Term")
        
        def analyze_atsi_trends(df):
            if 'Flag_ATSI' not in df.columns or 'Term' not in df.columns or 'Allocated_Program' not in df.columns:
                return None
            atsi_data = df[df['Flag_ATSI'] == 'Yes'].copy()
            if atsi_data.empty:
                return None
            atsi_data['Term'] = pd.to_numeric(atsi_data['Term'], errors='coerce')
            atsi_data = atsi_data.dropna(subset=['Term'])
            programs = sorted([p for p in atsi_data['Allocated_Program'].unique() if pd.notna(p)])
            if not programs:
                return None
            trend_data = {}
            for program in programs:
                prog_data = atsi_data[atsi_data['Allocated_Program'] == program]
                term_counts = prog_data.groupby('Term').size().sort_index()
                trend_data[program] = term_counts
            return trend_data, programs, atsi_data
        
        if 'Flag_ATSI' in filtered.columns:
            trend_results = analyze_atsi_trends(filtered)
            if trend_results and filtered[filtered['Flag_ATSI'] == 'Yes'].shape[0] > 0:
                trend_data, programs, atsi_students = trend_results
                
                fig_atsi = go.Figure()
                colors = ['#00e5ff', '#00ff00', '#ff6b6b', '#ffd93d']
                for idx, program in enumerate(programs):
                    if program in trend_data:
                        term_counts = trend_data[program]
                        fig_atsi.add_trace(go.Scatter(
                            x=term_counts.index.astype(int),
                            y=term_counts.values,
                            mode='lines+markers',
                            name=f'{program} Program',
                            line=dict(color=colors[idx % len(colors)], width=3),
                            marker=dict(size=10),
                            hovertemplate='<b>%{fullData.name}</b><br>Term: %{x}<br>Students: %{y}<extra></extra>'
                        ))
                
                fig_atsi.update_layout(
                    title='ATSI Student Enrollment Trends',
                    xaxis_title='Term',
                    yaxis_title='Number of ATSI Students',
                    hovermode='x unified',
                    height=450,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ffffff'),
                    xaxis=dict(showgrid=False, tickmode='linear', tick0=1),
                    yaxis=dict(showgrid=False),
                    legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='left', x=0.01, bgcolor='rgba(0,0,0,0.5)', bordercolor='#00e5ff', borderwidth=1)
                )
                st.plotly_chart(fig_atsi, use_container_width=True)
                
                st.markdown("### 📊 Current Enrollments by Program")
                cols = st.columns(min(3, len(programs)))
                for idx, program in enumerate(programs):
                    if program in trend_data:
                        term_counts = trend_data[program]
                        current_term = term_counts.index.max()
                        current_count = term_counts.iloc[-1]
                        if len(term_counts) > 1:
                            previous_count = term_counts.iloc[-2]
                            change = current_count - previous_count
                            change_pct = (change / previous_count * 100) if previous_count > 0 else 0
                        else:
                            change = 0
                            change_pct = 0
                        total_atsi = len(atsi_students[atsi_students['Allocated_Program'] == program])
                        with cols[idx % 3]:
                            st.metric(f"{program} Program", f"{current_count}", delta=f"{change:+d} ({change_pct:+.0f}%)", delta_color="off")
                            st.caption(f"Term {int(current_term)} | Total: {total_atsi}")
                
                st.markdown("### 📋 Detailed Breakdown")
                detail_data = []
                for program in programs:
                    if program in trend_data:
                        term_counts = trend_data[program]
                        for term, count in term_counts.items():
                            detail_data.append({'Program': program, 'Term': int(term), 'ATSI Students': count})
                if detail_data:
                    detail_df = pd.DataFrame(detail_data).sort_values(['Program', 'Term'])
                    st.dataframe(detail_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("### 📌 Key Insights")
                    col1, col2, col3, col4 = st.columns(4)
                    total_atsi = len(atsi_students)
                    allocated_atsi = len(atsi_students[atsi_students['Allocation_Status'] == 'Allocated']) if 'Allocation_Status' in atsi_students.columns else 0
                    waiting_atsi = len(atsi_students[atsi_students['Allocation_Status'] == 'On Waiting List']) if 'Allocation_Status' in atsi_students.columns else 0
                    allocation_rate = (allocated_atsi / total_atsi * 100) if total_atsi > 0 else 0
                    
                    with col1:
                        st.info(f"**Total ATSI**\n{total_atsi}")
                    with col2:
                        st.success(f"**Allocated**\n{allocated_atsi}")
                    with col3:
                        st.warning(f"**Waiting**\n{waiting_atsi}")
                    with col4:
                        st.metric("Allocation %", f"{allocation_rate:.0f}%")
        
        st.markdown("---")
        st.markdown("## 🟠 SWD Enrollment Trends by Program & Term")
        
        def analyze_swd_trends(df):
            if 'Flag_SWD' not in df.columns or 'Term' not in df.columns or 'Allocated_Program' not in df.columns:
                return None
            swd_data = df[df['Flag_SWD'] == 'Yes'].copy()
            if swd_data.empty:
                return None
            swd_data['Term'] = pd.to_numeric(swd_data['Term'], errors='coerce')
            swd_data = swd_data.dropna(subset=['Term'])
            programs = sorted([p for p in swd_data['Allocated_Program'].unique() if pd.notna(p)])
            if not programs:
                return None
            trend_data = {}
            for program in programs:
                prog_data = swd_data[swd_data['Allocated_Program'] == program]
                term_counts = prog_data.groupby('Term').size().sort_index()
                trend_data[program] = term_counts
            return trend_data, programs, swd_data
        
        if 'Flag_SWD' in filtered.columns:
            trend_results = analyze_swd_trends(filtered)
            if trend_results and filtered[filtered['Flag_SWD'] == 'Yes'].shape[0] > 0:
                trend_data, programs, swd_students = trend_results
                
                fig_swd = go.Figure()
                colors = ['#00e5ff', '#00ff00', '#ff6b6b', '#ffd93d']
                for idx, program in enumerate(programs):
                    if program in trend_data:
                        term_counts = trend_data[program]
                        fig_swd.add_trace(go.Scatter(
                            x=term_counts.index.astype(int),
                            y=term_counts.values,
                            mode='lines+markers',
                            name=f'{program} Program',
                            line=dict(color=colors[idx % len(colors)], width=3),
                            marker=dict(size=10),
                            hovertemplate='<b>%{fullData.name}</b><br>Term: %{x}<br>Students: %{y}<extra></extra>'
                        ))
                
                fig_swd.update_layout(
                    title='SWD Student Enrollment Trends',
                    xaxis_title='Term',
                    yaxis_title='Number of SWD Students',
                    hovermode='x unified',
                    height=450,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ffffff'),
                    xaxis=dict(showgrid=False, tickmode='linear', tick0=1),
                    yaxis=dict(showgrid=False),
                    legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='left', x=0.01, bgcolor='rgba(0,0,0,0.5)', bordercolor='#00e5ff', borderwidth=1)
                )
                st.plotly_chart(fig_swd, use_container_width=True)
                
                st.markdown("### 📊 Current Enrollments by Program")
                cols = st.columns(min(3, len(programs)))
                for idx, program in enumerate(programs):
                    if program in trend_data:
                        term_counts = trend_data[program]
                        current_term = term_counts.index.max()
                        current_count = term_counts.iloc[-1]
                        if len(term_counts) > 1:
                            previous_count = term_counts.iloc[-2]
                            change = current_count - previous_count
                            change_pct = (change / previous_count * 100) if previous_count > 0 else 0
                        else:
                            change = 0
                            change_pct = 0
                        total_swd = len(swd_students[swd_students['Allocated_Program'] == program])
                        with cols[idx % 3]:
                            st.metric(f"{program} Program", f"{current_count}", delta=f"{change:+d} ({change_pct:+.0f}%)", delta_color="off")
                            st.caption(f"Term {int(current_term)} | Total: {total_swd}")
                
                st.markdown("### 📋 Detailed Breakdown")
                detail_data = []
                for program in programs:
                    if program in trend_data:
                        term_counts = trend_data[program]
                        for term, count in term_counts.items():
                            detail_data.append({'Program': program, 'Term': int(term), 'SWD Students': count})
                if detail_data:
                    detail_df = pd.DataFrame(detail_data).sort_values(['Program', 'Term'])
                    st.dataframe(detail_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("### 📌 Key Insights")
                    col1, col2, col3, col4 = st.columns(4)
                    total_swd = len(swd_students)
                    allocated_swd = len(swd_students[swd_students['Allocation_Status'] == 'Allocated']) if 'Allocation_Status' in swd_students.columns else 0
                    waiting_swd = len(swd_students[swd_students['Allocation_Status'] == 'On Waiting List']) if 'Allocation_Status' in swd_students.columns else 0
                    allocation_rate = (allocated_swd / total_swd * 100) if total_swd > 0 else 0
                    
                    with col1:
                        st.info(f"**Total SWD**\n{total_swd}")
                    with col2:
                        st.success(f"**Allocated**\n{allocated_swd}")
                    with col3:
                        st.warning(f"**Waiting**\n{waiting_swd}")
                    with col4:
                        st.metric("Allocation %", f"{allocation_rate:.0f}%")
        
        st.markdown("---")
        st.markdown("## 🧠 ASD Overrepresentation Analysis")
        
        if 'Flag_ASD' in filtered.columns:
            total_students = len(filtered)
            asd_count = len(filtered[filtered['Flag_ASD'] == 'Yes'])
            asd_percentage = (asd_count / total_students * 100) if total_students > 0 else 0
            
            st.markdown(f"### Overall ASD Representation: **{asd_percentage:.1f}%** ({asd_count}/{total_students} students)")
            
            if asd_percentage >= 90:
                st.error(f"⚠️ **CRITICAL OVERREPRESENTATION**: {asd_percentage:.1f}% of all CLC referrals are identified with ASD")
            elif asd_percentage >= 80:
                st.warning(f"⚠️ **SIGNIFICANT OVERREPRESENTATION**: {asd_percentage:.1f}% of all CLC referrals are identified with ASD")
            else:
                st.info(f"📊 ASD Representation: {asd_percentage:.1f}%")
            
            st.markdown("### ASD vs All Other Students")
            col1, col2 = st.columns(2)
            
            with col1:
                asd_vs_other = pd.Series({'ASD': asd_count, 'Non-ASD': total_students - asd_count})
                fig_pie = go.Figure(data=[go.Pie(
                    labels=asd_vs_other.index,
                    values=asd_vs_other.values,
                    marker=dict(colors=['#ff6b6b', '#00e5ff'])
                )])
                fig_pie.update_layout(
                    title='ASD vs Non-ASD Distribution',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ffffff'),
                    height=400
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.markdown("### ASD Distribution by Program")
                prog_data = []
                for prog in ['JP', 'PY', 'SY']:
                    prog_students = filtered[filtered['Allocated_Program'] == prog] if 'Allocated_Program' in filtered.columns else pd.DataFrame()
                    if len(prog_students) > 0:
                        prog_asd = len(prog_students[prog_students['Flag_ASD'] == 'Yes'])
                        prog_total = len(prog_students)
                        prog_pct = (prog_asd / prog_total * 100) if prog_total > 0 else 0
                        prog_data.append({'Program': prog, 'ASD': prog_asd, 'Total': prog_total, 'ASD %': prog_pct})
                
                if prog_data:
                    prog_df = pd.DataFrame(prog_data)
                    fig_prog = go.Figure(data=[
                        go.Bar(x=prog_df['Program'], y=prog_df['ASD'], name='ASD', marker_color='#ff6b6b'),
                        go.Bar(x=prog_df['Program'], y=prog_df['Total'] - prog_df['ASD'], name='Non-ASD', marker_color='#00e5ff')
                    ])
                    fig_prog.update_layout(
                        title='ASD by Program',
                        barmode='stack',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#ffffff'),
                        height=400,
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=False)
                    )
                    st.plotly_chart(fig_prog, use_container_width=True)
            
            st.markdown("### ASD Enrollment Trends by Term")
            
            asd_filtered = filtered[filtered['Flag_ASD'] == 'Yes'].copy()
            if 'Term' in asd_filtered.columns:
                asd_filtered['Term'] = pd.to_numeric(asd_filtered['Term'], errors='coerce')
                asd_filtered = asd_filtered.dropna(subset=['Term'])
                
                term_asd = asd_filtered.groupby('Term').size()
                term_total = filtered.groupby('Term').size() if 'Term' in filtered.columns else pd.Series()
                
                if len(term_asd) > 0 and len(term_total) > 0:
                    term_pct = (term_asd / term_total * 100).reindex(term_asd.index, fill_value=0)
                    
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(
                        x=term_asd.index.astype(int),
                        y=term_pct.values,
                        mode='lines+markers',
                        name='ASD %',
                        line=dict(color='#ff6b6b', width=3),
                        marker=dict(size=10),
                        fill='tozeroy',
                        hovertemplate='Term: %{x}<br>ASD %: %{y:.1f}%<extra></extra>'
                    ))
                    fig_trend.update_layout(
                        title='ASD Percentage Over Terms',
                        xaxis_title='Term',
                        yaxis_title='Percentage of Referrals (%)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#ffffff'),
                        height=400,
                        xaxis=dict(showgrid=False, tickmode='linear', tick0=1),
                        yaxis=dict(showgrid=False)
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
            
            st.markdown("### ASD Comorbidity Analysis")
            st.markdown("*Students with ASD who ALSO have other identified disabilities*")
            
            disability_cols_asd = ['Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
            
            asd_with_other = {}
            for col in disability_cols_asd:
                if col in asd_filtered.columns:
                    count = len(asd_filtered[asd_filtered[col] == 'Yes'])
                    pct = (count / asd_count * 100) if asd_count > 0 else 0
                    disability_name = col.replace('Flag_', '').replace('_', ' ')
                    asd_with_other[disability_name] = {'Count': count, 'Percentage': pct}
            
            if asd_with_other:
                comorbid_df = pd.DataFrame(asd_with_other).T.sort_values('Percentage', ascending=True)
                
                fig_comorbid = go.Figure(data=[go.Bar(
                    y=comorbid_df.index,
                    x=comorbid_df['Percentage'],
                    orientation='h',
                    marker_color='#ffd93d',
                    text=[f"{int(comorbid_df.loc[idx, 'Count'])}" for idx in comorbid_df.index],
                    textposition='outside'
                )])
                fig_comorbid.update_layout(
                    title='Additional Disabilities in ASD Students',
                    xaxis_title='Percentage of ASD Students (%)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ffffff'),
                    height=400,
                    margin=dict(l=200, r=80, t=40, b=0),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig_comorbid, use_container_width=True)
                
                st.dataframe(comorbid_df, use_container_width=True)
            
            st.markdown("### 📌 ASD Key Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            asd_allocated = len(asd_filtered[asd_filtered['Allocation_Status'] == 'Allocated']) if 'Allocation_Status' in asd_filtered.columns else 0
            asd_waiting = len(asd_filtered[asd_filtered['Allocation_Status'] == 'On Waiting List']) if 'Allocation_Status' in asd_filtered.columns else 0
            asd_allocation_rate = (asd_allocated / asd_count * 100) if asd_count > 0 else 0
            
            with col1:
                st.metric("Total ASD", asd_count)
            with col2:
                st.metric("Allocated", asd_allocated)
            with col3:
                st.metric("Waiting", asd_waiting)
            with col4:
                st.metric("Allocation %", f"{asd_allocation_rate:.0f}%")
            
            st.markdown("### 🔍 Critical Findings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"📊 **Overall ASD Rate**: {asd_percentage:.1f}% of all referrals\n\n**Finding**: This represents significant overrepresentation compared to typical ASD prevalence rates (1-2% in general population)")
            
            with col2:
                non_asd_with_multi = len(filtered[(filtered['Flag_ASD'] != 'Yes')])
                if non_asd_with_multi > 0:
                    st.warning(f"⚠️ **Only {non_asd_with_multi} non-ASD students** ({100-asd_percentage:.1f}% of referrals)\n\n**Question**: Are other conditions being underidentified?")
        
        # ====================================================================
        # MULTIPLE DISABILITIES
        # ====================================================================
        
        st.markdown("---")
        st.markdown("## Students with Multiple Disabilities")
        st.markdown("*Students with 2+ identified disabilities*")
        
        filtered_copy = filtered.copy()
        filtered_copy['disability_count'] = 0
        for col in disability_cols:
            if col in filtered_copy.columns:
                filtered_copy['disability_count'] += (filtered_copy[col] == 'Yes').astype(int)
        
        disability_dist = filtered_copy['disability_count'].value_counts().sort_index()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("No Disabilities", int(disability_dist.get(0, 0)))
        c2.metric("1 Disability", int(disability_dist.get(1, 0)))
        c3.metric("2 Disabilities", int(disability_dist.get(2, 0)))
        c4.metric("3+ Disabilities", int(disability_dist.get(3, 0)) + int(disability_dist.get(4, 0)) + int(disability_dist.get(5, 0)))
        
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
        
        if st.button("← Back to Overview"):
            st.session_state.drill_down_view = None
            st.rerun()
        
        view = st.session_state.drill_down_view
        
        if view == 'total':
            drill_data = filtered
            title = "📍 Total Students"
        elif view == 'allocated':
            drill_data = filtered[filtered['Allocation_Status'] == 'Allocated'] if 'Allocation_Status' in filtered.columns else pd.DataFrame()
            title = "✅ Allocated Students"
        elif view == 'waiting':
            drill_data = filtered[filtered['Allocation_Status'] == 'On Waiting List'] if 'Allocation_Status' in filtered.columns else pd.DataFrame()
            title = "⏳ Waiting List Students"
        elif view == 'atsi':
            drill_data = safe_flag_filter(filtered, 'Flag_ATSI')
            title = "🔴 ATSI Students"
        elif view == 'swd':
            drill_data = safe_flag_filter(filtered, 'Flag_SWD')
            title = "🟠 SWD Students"
        elif view == 'eald':
            drill_data = safe_flag_filter(filtered, 'Flag_EALD')
            title = "🟡 EALD Students"
        elif view == 'asd':
            drill_data = safe_flag_filter(filtered, 'Flag_ASD')
            title = "🧠 ASD Students"
        elif view == 'multi_disability':
            filtered_copy = filtered.copy()
            filtered_copy['disability_count'] = 0
            for col in disability_cols:
                if col in filtered_copy.columns:
                    filtered_copy['disability_count'] += (filtered_copy[col] == 'Yes').astype(int)
            drill_data = filtered_copy[filtered_copy['disability_count'] >= 2]
            title = "🔀 Multi-Disability Students"
        elif view == 'repeating':
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
        elif view == 'cohort_2025':
            drill_data = filtered[filtered['Referral_Year'] == 2025.0] if 'Referral_Year' in filtered.columns else pd.DataFrame()
            title = "📅 2025 Cohort"
        elif view == 'cohort_2026':
            drill_data = filtered[filtered['Referral_Year'] == 2026.0] if 'Referral_Year' in filtered.columns else pd.DataFrame()
            title = "📅 2026 Cohort"
        elif view == 'early_referrals':
            drill_data = filtered[filtered['Term'] == 1.0] if 'Term' in filtered.columns else pd.DataFrame()
            title = "🌍 Early Referrals (Term 1)"
        elif view == 'partnership_breakdown':
            drill_data = filtered
            title = "🏛️ Partnership Areas"
        elif view == 'school_breakdown':
            drill_data = filtered
            title = "🏫 Referring Schools"
        elif view == 'atsi_swd_overlap':
            drill_data = filtered[(filtered['Flag_ATSI'] == 'Yes') & (filtered['Flag_SWD'] == 'Yes')]
            title = "🔗 ATSI + SWD (Both)"
        elif view == 'eald_asd_overlap':
            drill_data = filtered[(filtered['Flag_EALD'] == 'Yes') & (filtered['Flag_ASD'] == 'Yes')]
            title = "🔗 EALD + ASD (Both)"
        else:
            drill_data = filtered
            title = "Drill-Down View"
        
        st.markdown(f"# {title}")
        st.markdown(f"*{len(drill_data)} students*")
        
        tabs = st.tabs(["Overview", "By Program", "By Partnership", "By School", "Disability Profile", "Trends"])
        
        with tabs[0]:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", len(drill_data))
            c2.metric("ATSI", safe_flag_count(drill_data, 'Flag_ATSI'))
            c3.metric("SWD", safe_flag_count(drill_data, 'Flag_SWD'))
            c4.metric("EALD", safe_flag_count(drill_data, 'Flag_EALD'))
            
            prog_dist = safe_program_distribution(drill_data)
            fig = go.Figure([go.Pie(labels=prog_dist.index, values=prog_dist.values)])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'))
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[1]:
            for prog in ['JP', 'PY', 'SY']:
                prog_data = drill_data[drill_data['Allocated_Program'] == prog] if 'Allocated_Program' in drill_data.columns else pd.DataFrame()
                if len(prog_data) > 0:
                    st.markdown(f"### {prog} Program ({len(prog_data)} students)")
                    st.write(f"**ATSI**: {safe_flag_count(prog_data, 'Flag_ATSI')} | **SWD**: {safe_flag_count(prog_data, 'Flag_SWD')} | **EALD**: {safe_flag_count(prog_data, 'Flag_EALD')}")
        
        with tabs[2]:
            partnership_dist = drill_data['Partnership_Area'].value_counts().head(12)
            fig = go.Figure([go.Bar(
                y=partnership_dist.index,
                x=partnership_dist.values,
                orientation='h',
                marker_color='#00e5ff'
            )])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, margin=dict(l=200, r=80, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[3]:
            school_dist = drill_data['Referring_School'].value_counts().head(12)
            fig = go.Figure([go.Bar(
                y=school_dist.index,
                x=school_dist.values,
                orientation='h',
                marker_color='#00ff00'
            )])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, margin=dict(l=200, r=80, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[4]:
            st.markdown("### Disability Distribution")
            disability_cols_drill = ['Flag_ASD', 'Flag_ADHD', 'Flag_Speech_and_Lang', 'Flag_Intellectual', 'Flag_Learning_Difficulty', 'Flag_Sensory_Processing', 'Flag_ODD', 'Flag_PDA']
            disability_counts = {}
            for col in disability_cols_drill:
                if col in drill_data.columns:
                    count = safe_flag_count(drill_data, col)
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
        
        with tabs[5]:
            st.markdown("### Trends by Term")
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
