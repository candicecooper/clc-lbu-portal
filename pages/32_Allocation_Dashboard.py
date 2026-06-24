"""
CLC-LBU ALLOCATION DASHBOARD - SIMPLE FOCUSED DRILL-DOWN
Click Program → See Schools + Equity Groups
Click School → See Equity Breakdown
Click Equity → See Details
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import random

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="📊 CLC-LBU Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# GLOWING THEME CSS
# ============================================================================

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0a0e27 !important;
        border-right: 2px solid rgba(26, 122, 122, 0.5) !important;
    }
    
    h1 {
        color: #00e5ff !important;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.5) !important;
        border-bottom: 2px solid rgba(26, 122, 122, 0.3) !important;
        padding-bottom: 15px !important;
    }
    
    h2 {
        color: #00e5ff !important;
        border-left: 3px solid rgba(0, 229, 255, 0.5) !important;
        padding-left: 10px !important;
    }
    
    h3 {
        color: #00e5ff !important;
        border-left: 2px solid rgba(200, 118, 10, 0.6) !important;
        padding-left: 8px !important;
    }
    
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.25) 0%, rgba(0, 229, 255, 0.05) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
        border-left: 4px solid rgba(0, 229, 255, 0.8) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.15), inset 0 0 20px rgba(0, 229, 255, 0.05) !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.4) 0%, rgba(0, 229, 255, 0.2) 100%) !important;
        color: #00e5ff !important;
        border: 2px solid rgba(0, 229, 255, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.2) !important;
        font-weight: bold !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.3) 0%, rgba(26, 122, 122, 0.3) 100%) !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.4) !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.2) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 4px solid #00e5ff !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.15) !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, rgba(200, 118, 10, 0.2) 0%, rgba(200, 118, 10, 0.1) 100%) !important;
        border-left: 4px solid #C8760A !important;
    }
    
    .stSuccess {
        background: linear-gradient(135deg, rgba(0, 255, 0, 0.15) 0%, rgba(0, 255, 0, 0.05) 100%) !important;
        border-left: 4px solid #00ff00 !important;
    }
    
    hr {
        border: 1px solid rgba(0, 229, 255, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# COLORS
# ============================================================================

COLORS = {
    'teal': '#1A7A7A',
    'cyan': '#00e5ff',
    'green': '#00ff00',
    'red': '#ff6b6b',
    'yellow': '#ffd93d',
    'dark_bg': '#0a0e27',
    'white': '#ffffff',
    'amber': '#C8760A'
}

# ============================================================================
# SESSION STATE
# ============================================================================

def init_session():
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    if 'selected_program' not in st.session_state:
        st.session_state['selected_program'] = None
    if 'selected_school' not in st.session_state:
        st.session_state['selected_school'] = None
    if 'selected_equity' not in st.session_state:
        st.session_state['selected_equity'] = None

init_session()

# ============================================================================
# DATA LOADING
# ============================================================================

def load_data():
    paths = ['data/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
             '/mnt/user-data/outputs/CLC_Allocation_Dashboard_2026_CLEANED.xlsx']
    for path in paths:
        if os.path.exists(path):
            df = pd.read_excel(path)
            for col in ['Term', 'Referral_Year']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            return df
    return None

def create_sample():
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary', 'Hendon PS']
    programs = ['JP', 'PY', 'SY']
    statuses = ['Allocated', 'On Waiting List', 'Current']
    
    df = pd.DataFrame({
        'Referring_School': [random.choice(schools) for _ in range(150)],
        'Allocated_Program': [random.choice(programs) for _ in range(150)],
        'Allocation_Status': [random.choice(statuses) for _ in range(150)],
        'Flag_ATSI': [random.choice(['Yes', 'No']) for _ in range(150)],
        'Flag_EALD': [random.choice(['Yes', 'No']) for _ in range(150)],
        'Flag_SWD': [random.choice(['Yes', 'No']) for _ in range(150)],
        'Flag_ASD': [random.choice(['Yes', 'No']) for _ in range(150)],
        'Referral_Year': [random.choice([2025, 2026]) for _ in range(150)],
        'Term': [random.choice([1, 2, 3, 4]) for _ in range(150)],
    })
    return df

# ============================================================================
# NAVIGATION & DISPLAY
# ============================================================================

def show_breadcrumb():
    """Show navigation trail"""
    path = []
    if st.session_state['selected_program']:
        path.append(f"📚 {st.session_state['selected_program']}")
    if st.session_state['selected_school']:
        path.append(f"🏫 {st.session_state['selected_school']}")
    if st.session_state['selected_equity']:
        path.append(f"👥 {st.session_state['selected_equity']}")
    
    if path:
        st.markdown(f"**Navigation:** {' → '.join(path)}")
        
        col1, col2, col3 = st.columns([1, 1, 6])
        with col1:
            if st.button("🔙 Reset Program"):
                st.session_state['selected_program'] = None
                st.session_state['selected_school'] = None
                st.session_state['selected_equity'] = None
                st.rerun()
        with col2:
            if st.session_state['selected_school'] and st.button("🔙 Reset School"):
                st.session_state['selected_school'] = None
                st.session_state['selected_equity'] = None
                st.rerun()

# ============================================================================
# LEVEL 1: PROGRAMS
# ============================================================================

def show_programs(df):
    """Level 1: Select Program"""
    st.markdown("## 📚 Select a Program")
    st.markdown("Click a program to see schools and equity breakdown")
    
    cols = st.columns(3)
    programs = sorted(df['Allocated_Program'].unique())
    
    for idx, prog in enumerate(programs):
        with cols[idx]:
            prog_df = df[df['Allocated_Program'] == prog]
            count = len(prog_df)
            allocated = len(prog_df[prog_df['Allocation_Status'] == 'Allocated'])
            
            st.metric(f"📚 {prog}", count, f"{allocated} allocated")
            
            if st.button(f"→ Explore {prog}", key=f"prog_{prog}"):
                st.session_state['selected_program'] = prog
                st.rerun()

# ============================================================================
# LEVEL 2: SCHOOLS & EQUITY (by Program)
# ============================================================================

def show_program_detail(df):
    """Level 2: Program detail with schools and equity"""
    prog = st.session_state['selected_program']
    prog_df = df[df['Allocated_Program'] == prog]
    
    st.markdown(f"## 📚 Program: {prog}")
    st.markdown(f"**{len(prog_df)} students** | **{len(prog_df[prog_df['Allocation_Status'] == 'Allocated'])} allocated**")
    
    # SCHOOLS
    st.markdown("### 🏫 Schools in this Program")
    
    schools = sorted(prog_df['Referring_School'].unique())
    cols = st.columns(min(3, len(schools)))
    
    for idx, school in enumerate(schools):
        col = cols[idx % len(cols)]
        with col:
            school_df = prog_df[prog_df['Referring_School'] == school]
            count = len(school_df)
            allocated = len(school_df[school_df['Allocation_Status'] == 'Allocated'])
            
            st.metric(f"🏫 {school}", count, f"{allocated} allocated")
            
            if st.button(f"→ Drill to {school}", key=f"school_{prog}_{school}"):
                st.session_state['selected_school'] = school
                st.rerun()
    
    st.markdown("---")
    
    # EQUITY BREAKDOWN
    st.markdown("### ⚖️ Equity Groups in this Program")
    
    equity_cols = st.columns(4)
    equity_groups = {
        'ATSI': ('Flag_ATSI', '🇦🇺 Indigenous'),
        'EALD': ('Flag_EALD', '🌍 EALD'),
        'SWD': ('Flag_SWD', '♿ SWD'),
        'ASD': ('Flag_ASD', '🧩 ASD')
    }
    
    for idx, (key, (flag, label)) in enumerate(equity_groups.items()):
        col = equity_cols[idx]
        with col:
            equity_df = prog_df[prog_df[flag] == 'Yes']
            count = len(equity_df)
            allocated = len(equity_df[equity_df['Allocation_Status'] == 'Allocated'])
            
            st.metric(label, count, f"{allocated} allocated")
            
            if st.button(f"→ {label}", key=f"equity_{prog}_{key}"):
                st.session_state['selected_equity'] = label
                st.rerun()
    
    # DATA TABLE
    st.markdown("---")
    st.markdown(f"### 📊 All {prog} Data")
    cols_show = [c for c in ['Referring_School', 'Allocation_Status', 'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Term', 'Referral_Year'] if c in prog_df.columns]
    st.dataframe(prog_df[cols_show], use_container_width=True, height=300)

# ============================================================================
# LEVEL 3: SCHOOL DETAIL & EQUITY (by Program + School)
# ============================================================================

def show_school_detail(df):
    """Level 3: School detail with equity breakdown"""
    prog = st.session_state['selected_program']
    school = st.session_state['selected_school']
    
    school_df = df[(df['Allocated_Program'] == prog) & (df['Referring_School'] == school)]
    
    st.markdown(f"## 🏫 {school} (Program: {prog})")
    st.markdown(f"**{len(school_df)} students** | **{len(school_df[school_df['Allocation_Status'] == 'Allocated'])} allocated**")
    
    # EQUITY BREAKDOWN FOR THIS SCHOOL
    st.markdown("### ⚖️ Equity Groups at this School")
    
    equity_cols = st.columns(4)
    equity_groups = {
        'ATSI': ('Flag_ATSI', '🇦🇺 Indigenous'),
        'EALD': ('Flag_EALD', '🌍 EALD'),
        'SWD': ('Flag_SWD', '♿ SWD'),
        'ASD': ('Flag_ASD', '🧩 ASD')
    }
    
    for idx, (key, (flag, label)) in enumerate(equity_groups.items()):
        col = equity_cols[idx]
        with col:
            equity_df = school_df[school_df[flag] == 'Yes']
            count = len(equity_df)
            allocated = len(equity_df[equity_df['Allocation_Status'] == 'Allocated'])
            
            st.metric(label, count, f"{allocated} allocated")
            
            if st.button(f"→ {label}", key=f"equity_detail_{prog}_{school}_{key}"):
                st.session_state['selected_equity'] = label
                st.rerun()
    
    # DATA TABLE
    st.markdown("---")
    st.markdown(f"### 📊 Students from {school}")
    cols_show = [c for c in ['Allocation_Status', 'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Term', 'Referral_Year'] if c in school_df.columns]
    st.dataframe(school_df[cols_show], use_container_width=True, height=300)

# ============================================================================
# LEVEL 4: EQUITY DETAIL (by Program + School + Equity)
# ============================================================================

def show_equity_detail(df):
    """Level 4: Equity group detail"""
    prog = st.session_state['selected_program']
    school = st.session_state['selected_school']
    equity_label = st.session_state['selected_equity']
    
    # Map label to flag
    equity_map = {'🇦🇺 Indigenous': 'Flag_ATSI', '🌍 EALD': 'Flag_EALD', '♿ SWD': 'Flag_SWD', '🧩 ASD': 'Flag_ASD'}
    flag = equity_map.get(equity_label, 'Flag_ATSI')
    
    equity_df = df[(df['Allocated_Program'] == prog) & 
                    (df['Referring_School'] == school) & 
                    (df[flag] == 'Yes')]
    
    st.markdown(f"## {equity_label} in {school} ({prog})")
    st.markdown(f"**{len(equity_df)} students** | **{len(equity_df[equity_df['Allocation_Status'] == 'Allocated'])} allocated**")
    
    # METRICS
    cols = st.columns(4)
    cols[0].metric("📋 Total", len(equity_df))
    allocated = len(equity_df[equity_df['Allocation_Status'] == 'Allocated'])
    rate = (allocated / len(equity_df) * 100) if len(equity_df) > 0 else 0
    cols[1].metric("✅ Allocated", allocated, f"{rate:.0f}%")
    cols[2].metric("⏳ Waiting", len(equity_df[equity_df['Allocation_Status'] == 'On Waiting List']))
    cols[3].metric("📊 Current", len(equity_df[equity_df['Allocation_Status'] == 'Current']))
    
    # STATUS BREAKDOWN
    st.markdown("---")
    st.markdown("### 📊 Allocation Status")
    
    status_cols = st.columns(3)
    statuses = ['Allocated', 'On Waiting List', 'Current']
    status_colors = [COLORS['green'], COLORS['red'], COLORS['cyan']]
    
    for idx, status in enumerate(statuses):
        col = status_cols[idx]
        with col:
            count = len(equity_df[equity_df['Allocation_Status'] == status])
            st.metric(f"📌 {status}", count)
    
    # DATA TABLE
    st.markdown("---")
    st.markdown(f"### 📊 Detailed Data")
    cols_show = [c for c in ['Allocation_Status', 'Term', 'Referral_Year'] if c in equity_df.columns]
    st.dataframe(equity_df[cols_show], use_container_width=True, height=300)

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Load data
    if not st.session_state['data_loaded']:
        default = load_data()
        if default is not None:
            st.session_state['df'] = default
            st.session_state['data_loaded'] = True
    
    df = st.session_state['df']
    
    # Header
    st.markdown("# 📊 CLC-LBU Allocation Dashboard")
    st.markdown("_Click to drill down: Program → Schools → Equity Groups_")
    
    # Data management
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded = st.file_uploader("📤 Upload Excel", type=['xlsx', 'xls'])
        if uploaded:
            df = pd.read_excel(uploaded)
            for col in ['Term', 'Referral_Year']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            st.session_state['df'] = df
            st.session_state['data_loaded'] = True
            st.success(f"✅ Loaded: {uploaded.name}")
    
    with col2:
        if st.button("📥 Load Demo"):
            st.session_state['df'] = create_sample()
            st.session_state['data_loaded'] = True
            st.rerun()
    
    if df is None:
        st.info("👆 Upload or load demo data to start")
        return
    
    # Breadcrumb
    show_breadcrumb()
    st.markdown("---")
    
    # DRILL-DOWN FLOW
    if not st.session_state['selected_program']:
        # LEVEL 1: Show programs
        show_programs(df)
    
    elif st.session_state['selected_program'] and not st.session_state['selected_school']:
        # LEVEL 2: Show program detail + schools + equity
        show_program_detail(df)
    
    elif st.session_state['selected_school'] and not st.session_state['selected_equity']:
        # LEVEL 3: Show school detail + equity breakdown
        show_school_detail(df)
    
    else:
        # LEVEL 4: Show equity detail
        show_equity_detail(df)

if __name__ == "__main__":
    main()
