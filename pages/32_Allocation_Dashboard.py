"""
CLC-LBU ALLOCATION DASHBOARD - FINAL WORKING VERSION
Uses config.toml + streamlit>=1.35.0 theme parameter
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import random

# ============================================================================
# PAGE CONFIG WITH THEME (streamlit 1.35.0+ supports this)
# ============================================================================

st.set_page_config(
    page_title="📊 CLC-LBU Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    theme={
        "primaryColor": "#00e5ff",
        "backgroundColor": "#0a0e27",
        "secondaryBackgroundColor": "#1a1a3e",
        "textColor": "#ffffff",
        "font": "sans serif"
    }
)

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
            return pd.read_excel(path)
    return None

def create_sample():
    students = ['Ethan Evans', 'Sarah Johnson', 'Michael Brown', 'Jessica White', 'David Lee', 
                'Emma Davis', 'James Wilson', 'Olivia Martinez', 'Noah Rodriguez', 'Ava Taylor']
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary']
    programs = ['JP', 'PY', 'SY']
    statuses = ['Allocated', 'On Waiting List', 'Current']
    
    return pd.DataFrame({
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

# ============================================================================
# FILTERS
# ============================================================================

def apply_filters(df, filters):
    if df is None:
        return df
    
    filtered = df.copy()
    
    if filters['term'] != 'All':
        filtered = filtered[filtered['Term'] == int(filters['term'])]
    if filters['year'] != 'All':
        filtered = filtered[filtered['Referral_Year'] == int(filters['year'])]
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
            colors.append(COLORS['green'] if rate >= 70 else COLORS['red'])
    
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
            st.session_state['df'] = pd.read_excel(uploaded)
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
        term = st.selectbox("📅 Term", ['All'] + list(map(str, sorted(df['Term'].unique()))))
        st.session_state['filters']['term'] = term
    
    with cols[1]:
        year = st.selectbox("📆 Year", ['All'] + list(map(str, sorted(df['Referral_Year'].unique()))))
        st.session_state['filters']['year'] = year
    
    with cols[2]:
        prog = st.selectbox("🎓 Program", ['All'] + list(df['Allocated_Program'].unique()))
        st.session_state['filters']['program'] = prog
    
    with cols[3]:
        school = st.selectbox("🏫 School", ['All'] + list(df['Referring_School'].unique()))
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
    ccols[1].plotly_chart(chart_equity(filtered), use_container_width=True)
    
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
    
    st.markdown(f"### {len(waiting)} Students Waiting")
    if len(waiting) > 0:
        st.dataframe(waiting[['Student_Name', 'Referring_School', 'Allocated_Program']], 
                    use_container_width=True, hide_index=True)

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
    
    st.markdown("### Schools")
    for school in filtered['Referring_School'].unique():
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
