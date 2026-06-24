"""
CLC-LBU ALLOCATION DASHBOARD - FINAL VERSION
- No theme parameter (uses config.toml)
- Dark theme CSS fallback in Python
- Fixed float/int conversion
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
# DARK THEME CSS (BACKUP - in case config.toml doesn't load)
# ============================================================================

st.markdown("""
<style>
    /* Main background */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0a0e27 !important;
        border-right: 3px solid #1A7A7A !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #00e5ff !important;
        font-weight: bold !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1A7A7A !important;
        color: #ffffff !important;
        border: 2px solid #00e5ff !important;
        font-weight: bold !important;
    }
    
    .stButton > button:hover {
        background-color: #00e5ff !important;
        color: #0a0e27 !important;
    }
    
    /* Selectbox & Input */
    .stSelectbox [data-testid="stSelectboxContainer"] {
        background-color: #1a1a3e !important;
    }
    
    .stSelectbox > div > div {
        background-color: #1a1a3e !important;
        color: #ffffff !important;
        border: 1px solid #1A7A7A !important;
    }
    
    /* File uploader */
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(26, 122, 122, 0.2) !important;
        border: 2px dashed #1A7A7A !important;
    }
    
    /* Metrics */
    [data-testid="metric-container"] {
        background-color: rgba(26, 122, 122, 0.15) !important;
        border-left: 4px solid #1A7A7A !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    
    /* Tabs */
    [data-testid="stTabs"] [role="tablist"] {
        background-color: #0a0e27 !important;
        border-bottom: 2px solid #1A7A7A !important;
    }
    
    [data-testid="stTabs"] [role="tab"] {
        background-color: rgba(26, 122, 122, 0.3) !important;
        color: #ffffff !important;
    }
    
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background-color: #1A7A7A !important;
        color: #00e5ff !important;
        border-bottom: 3px solid #00e5ff !important;
    }
    
    /* Tables */
    [data-testid="stDataFrame"] {
        background-color: #0a0e27 !important;
    }
    
    /* Info/Warning boxes */
    .stInfo, .stWarning, .stSuccess {
        background-color: rgba(26, 122, 122, 0.2) !important;
        border-left: 4px solid #1A7A7A !important;
    }
    
    /* Text */
    p, span, label {
        color: #ffffff !important;
    }
    
    /* Divider */
    hr {
        border-color: #1A7A7A !important;
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
    'white': '#ffffff'
}

# ============================================================================
# SESSION STATE
# ============================================================================

def init_session():
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    if 'filters' not in st.session_state:
        st.session_state['filters'] = {
            'term': 'All', 'year': 'All', 'program': 'All', 'school': 'All',
            'equity_group': 'All', 'current_page': 'home'
        }
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False

init_session()

# ============================================================================
# DATA
# ============================================================================

def load_data():
    paths = ['data/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
             '/mnt/user-data/outputs/CLC_Allocation_Dashboard_2026_CLEANED.xlsx']
    for path in paths:
        if os.path.exists(path):
            df = pd.read_excel(path)
            # Convert Term and Referral_Year to int (handle floats like 2.0)
            if 'Term' in df.columns:
                df['Term'] = df['Term'].astype(float).astype(int)
            if 'Referral_Year' in df.columns:
                df['Referral_Year'] = df['Referral_Year'].astype(float).astype(int)
            return df
    return None

def create_sample():
    students = ['Ethan Evans', 'Sarah Johnson', 'Michael Brown', 'Jessica White', 'David Lee', 
                'Emma Davis', 'James Wilson', 'Olivia Martinez', 'Noah Rodriguez', 'Ava Taylor']
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary']
    programs = ['JP', 'PY', 'SY']
    statuses = ['Allocated', 'On Waiting List', 'Current']
    
    df = pd.DataFrame({
        'Student_Name': [random.choice(students) for _ in range(80)],
        'Referring_School': [random.choice(schools) for _ in range(80)],
        'Allocated_Program': [random.choice(programs) for _ in range(80)],
        'Allocation_Status': [random.choice(statuses) for _ in range(80)],
        'Flag_ATSI': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_EALD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_SWD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_ASD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Referral_Year': [random.choice([2025, 2026]) for _ in range(80)],
        'Term': [random.choice([1, 2, 3, 4]) for _ in range(80)],
    })
    
    # Ensure types are correct
    df['Term'] = df['Term'].astype(int)
    df['Referral_Year'] = df['Referral_Year'].astype(int)
    return df

# ============================================================================
# FILTERS - FIXED INT CONVERSION
# ============================================================================

def apply_filters(df, filters):
    if df is None:
        return df
    
    filtered = df.copy()
    
    # FIX: Handle float to int conversion properly
    if filters['term'] != 'All':
        try:
            term_val = int(float(filters['term']))
            filtered = filtered[filtered['Term'] == term_val]
        except (ValueError, TypeError):
            pass
    
    if filters['year'] != 'All':
        try:
            year_val = int(float(filters['year']))
            filtered = filtered[filtered['Referral_Year'] == year_val]
        except (ValueError, TypeError):
            pass
    
    if filters['program'] != 'All':
        filtered = filtered[filtered['Allocated_Program'] == filters['program']]
    
    if filters['school'] != 'All':
        filtered = filtered[filtered['Referring_School'] == filters['school']]
    
    return filtered

def get_metrics(df):
    if df is None or len(df) == 0:
        return {'total': 0, 'allocated': 0, 'waiting': 0, 'current': 0, 'rate': 0}
    
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    waiting = len(df[df['Allocation_Status'] == 'On Waiting List'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    rate = (allocated / total * 100) if total > 0 else 0
    
    return {'total': total, 'allocated': allocated, 'waiting': waiting, 'current': current, 'rate': rate}

# ============================================================================
# CHARTS
# ============================================================================

def chart_funnel(df):
    if df is None or len(df) == 0:
        return go.Figure()
    
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    
    fig = go.Figure(data=[go.Funnel(
        y=['📋 Referred', '✅ Allocated', '🎓 Current'],
        x=[total, allocated, current],
        marker_color=[COLORS['cyan'], COLORS['green'], COLORS['teal']]
    )])
    
    fig.update_layout(
        title='📊 Allocation Funnel',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

def chart_waiting(df):
    if df is None or len(df) == 0:
        return go.Figure()
    
    try:
        waiting_by_term = df[df['Allocation_Status'] == 'On Waiting List'].groupby('Term').size().reset_index(name='Waiting')
        
        if len(waiting_by_term) == 0:
            return go.Figure()
        
        fig = go.Figure(data=go.Scatter(
            x=waiting_by_term['Term'],
            y=waiting_by_term['Waiting'],
            mode='lines+markers',
            line=dict(color=COLORS['red'], width=3),
            marker=dict(size=10, color=COLORS['red'])
        ))
        
        fig.update_layout(
            title='📈 Waiting List Trend',
            paper_bgcolor=COLORS['dark_bg'],
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['white']),
            height=400
        )
        return fig
    except:
        return go.Figure()

def chart_equity(df):
    if df is None or len(df) == 0:
        return go.Figure()
    
    groups = [('Indigenous 🇦🇺', 'Flag_ATSI'), ('EALD 🌍', 'Flag_EALD'), 
              ('SWD ♿', 'Flag_SWD'), ('ASD 🧩', 'Flag_ASD')]
    
    rates, labels, colors = [], [], []
    
    for name, flag in groups:
        subset = df[df[flag] == 'Yes']
        if len(subset) > 0:
            allocated = len(subset[subset['Allocation_Status'] == 'Allocated'])
            rate = allocated / len(subset) * 100
            rates.append(rate)
            labels.append(name)
            colors.append(COLORS['green'] if rate >= 70 else COLORS['yellow'] if rate >= 60 else COLORS['red'])
    
    if not rates:
        return go.Figure()
    
    fig = go.Figure(data=go.Bar(x=labels, y=rates, marker_color=colors))
    fig.update_layout(
        title='⚖️ Equity Outcomes',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        yaxis=dict(range=[0, 100])
    )
    return fig

def chart_program(df):
    if df is None or len(df) == 0:
        return go.Figure()
    
    programs = ['JP 👶', 'PY 👧', 'SY 👦']
    prog_codes = ['JP', 'PY', 'SY']
    allocated, waiting = [], []
    
    for prog in prog_codes:
        prog_df = df[df['Allocated_Program'] == prog]
        allocated.append(len(prog_df[prog_df['Allocation_Status'] == 'Allocated']))
        waiting.append(len(prog_df[prog_df['Allocation_Status'] == 'On Waiting List']))
    
    fig = go.Figure(data=[
        go.Bar(x=programs, y=allocated, name='✅ Allocated', marker_color=COLORS['green']),
        go.Bar(x=programs, y=waiting, name='⏳ Waiting', marker_color=COLORS['red'])
    ])
    
    fig.update_layout(
        title='🎓 Program Capacity',
        barmode='stack',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

# ============================================================================
# PAGES
# ============================================================================

def page_home(df):
    st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
    st.markdown("_Real-time insights into student allocation, equity & program capacity_")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("### 📁 **Data Management**")
        uploaded = st.file_uploader("📤 Upload Excel (.xlsx)", type=['xlsx', 'xls'])
        if uploaded:
            df_new = pd.read_excel(uploaded)
            # Convert numeric columns
            if 'Term' in df_new.columns:
                df_new['Term'] = df_new['Term'].astype(float).astype(int)
            if 'Referral_Year' in df_new.columns:
                df_new['Referral_Year'] = df_new['Referral_Year'].astype(float).astype(int)
            st.session_state['df'] = df_new
            st.session_state['data_loaded'] = True
            st.success(f"✅ Loaded: {uploaded.name}")
    
    with col2:
        st.markdown("### 📊 **Status**")
        if st.session_state['data_loaded'] and st.session_state['df'] is not None:
            st.metric("📋 Records", len(st.session_state['df']))
    
    with col3:
        st.markdown("### 🔄 **Demo**")
        if st.button("📥 Load Demo"):
            st.session_state['df'] = create_sample()
            st.session_state['data_loaded'] = True
            st.rerun()
    
    st.markdown("---")
    
    if not st.session_state['data_loaded'] or st.session_state['df'] is None:
        st.info("👆 Upload Excel or load demo data")
        return
    
    df = st.session_state['df']
    
    st.markdown("### 🔽 **Filters**")
    cols = st.columns(6)
    
    with cols[0]:
        terms = sorted([str(int(t)) for t in df['Term'].unique()])
        term = st.selectbox("📅 Term", ['All'] + terms)
        st.session_state['filters']['term'] = term
    
    with cols[1]:
        years = sorted([str(int(y)) for y in df['Referral_Year'].unique()])
        year = st.selectbox("📆 Year", ['All'] + years)
        st.session_state['filters']['year'] = year
    
    with cols[2]:
        progs = sorted(df['Allocated_Program'].unique())
        prog = st.selectbox("🎓 Program", ['All'] + list(progs))
        st.session_state['filters']['program'] = prog
    
    with cols[3]:
        schools = sorted(df['Referring_School'].unique())
        school = st.selectbox("🏫 School", ['All'] + list(schools))
        st.session_state['filters']['school'] = school
    
    with cols[4]:
        equity = st.selectbox("⚖️ Equity", ['All', 'Indigenous 🇦🇺', 'EALD 🌍', 'SWD ♿', 'ASD 🧩'])
        st.session_state['filters']['equity_group'] = equity
    
    with cols[5]:
        if st.button("🔄 Clear"):
            st.session_state['filters'] = {
                'term': 'All', 'year': 'All', 'program': 'All', 'school': 'All', 'equity_group': 'All'
            }
            st.rerun()
    
    st.markdown("---")
    
    filtered = apply_filters(df, st.session_state['filters'])
    metrics = get_metrics(filtered)
    
    st.markdown("### 📈 **Metrics**")
    mcols = st.columns(4)
    mcols[0].metric("📋 Referred", metrics['total'])
    mcols[1].metric("✅ Allocated", metrics['allocated'], f"{metrics['rate']:.0f}%")
    mcols[2].metric("⏳ Waiting", metrics['waiting'])
    mcols[3].metric("🎓 Current", metrics['current'])
    
    st.markdown("---")
    st.markdown("### 📊 **Charts**")
    
    ccols = st.columns(2)
    ccols[0].plotly_chart(chart_funnel(filtered), use_container_width=True)
    ccols[1].plotly_chart(chart_waiting(filtered), use_container_width=True)
    
    ccols = st.columns(2)
    ccols[0].plotly_chart(chart_equity(filtered), use_container_width=True)
    ccols[1].plotly_chart(chart_program(filtered), use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### 🔍 **Pages**")
    nav = st.columns(4)
    if nav[0].button("📋 Waiting List"):
        st.session_state['filters']['current_page'] = 'waiting'
        st.rerun()
    if nav[1].button("👥 Equity"):
        st.session_state['filters']['current_page'] = 'equity'
        st.rerun()
    if nav[2].button("🏫 Schools"):
        st.session_state['filters']['current_page'] = 'school'
        st.rerun()

def page_waiting(df):
    st.markdown("# 📋 WAITING LIST")
    if st.button("⬅️ Back"):
        st.session_state['filters']['current_page'] = 'home'
        st.rerun()
    st.markdown("---")
    
    if df is None:
        st.warning("No data")
        return
    
    filtered = apply_filters(df, st.session_state['filters'])
    waiting = filtered[filtered['Allocation_Status'] == 'On Waiting List']
    
    st.markdown(f"### 👥 **{len(waiting)} Students Waiting**")
    if len(waiting) > 0:
        cols_show = [c for c in ['Student_Name', 'Referring_School', 'Allocated_Program'] if c in waiting.columns]
        st.dataframe(waiting[cols_show], use_container_width=True, hide_index=True)

def page_equity(df):
    st.markdown("# 👥 EQUITY DEEP-DIVE")
    if st.button("⬅️ Back"):
        st.session_state['filters']['current_page'] = 'home'
        st.rerun()
    st.markdown("---")
    
    if df is None:
        st.warning("No data")
        return
    
    filtered = apply_filters(df, st.session_state['filters'])
    
    t1, t2, t3, t4 = st.tabs(["🇦🇺 Indigenous", "🌍 EALD", "♿ SWD", "🧩 ASD"])
    
    with t1:
        indigen = filtered[filtered['Flag_ATSI'] == 'Yes']
        if len(indigen) > 0:
            allocated = len(indigen[indigen['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(indigen), f"{allocated/len(indigen)*100:.0f}% allocated")
        else:
            st.info("No data")
    
    with t2:
        eald = filtered[filtered['Flag_EALD'] == 'Yes']
        if len(eald) > 0:
            allocated = len(eald[eald['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(eald), f"{allocated/len(eald)*100:.0f}% allocated")
        else:
            st.info("No data")
    
    with t3:
        swd = filtered[filtered['Flag_SWD'] == 'Yes']
        if len(swd) > 0:
            allocated = len(swd[swd['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(swd), f"{allocated/len(swd)*100:.0f}% allocated")
        else:
            st.info("No data")
    
    with t4:
        asd = filtered[filtered['Flag_ASD'] == 'Yes']
        if len(asd) > 0:
            allocated = len(asd[asd['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(asd), f"{allocated/len(asd)*100:.0f}% allocated")
        else:
            st.info("No data")

def page_school(df):
    st.markdown("# 🏫 SCHOOL PERFORMANCE")
    if st.button("⬅️ Back"):
        st.session_state['filters']['current_page'] = 'home'
        st.rerun()
    st.markdown("---")
    
    if df is None:
        st.warning("No data")
        return
    
    filtered = apply_filters(df, st.session_state['filters'])
    
    st.markdown("### 📊 **Schools**")
    for school in sorted(filtered['Referring_School'].unique()):
        school_data = filtered[filtered['Referring_School'] == school]
        allocated = len(school_data[school_data['Allocation_Status'] == 'Allocated'])
        st.metric(school, f"{allocated}/{len(school_data)}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    if not st.session_state['data_loaded']:
        default = load_data()
        if default is not None:
            st.session_state['df'] = default
            st.session_state['data_loaded'] = True
    
    page = st.session_state['filters']['current_page']
    df = st.session_state['df']
    
    if page == 'home':
        page_home(df)
    elif page == 'waiting':
        page_waiting(df)
    elif page == 'equity':
        page_equity(df)
    elif page == 'school':
        page_school(df)
    else:
        page_home(df)

if __name__ == "__main__":
    main()
