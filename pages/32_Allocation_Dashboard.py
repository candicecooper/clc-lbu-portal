"""
CLC-LBU ALLOCATION DASHBOARD - CONFIG.TOML ONLY
Dark theme via config.toml (no theme parameter)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import os
import numpy as np

# ============================================================================
# PAGE CONFIGURATION (WITHOUT theme parameter)
# ============================================================================

st.set_page_config(
    page_title="📊 CLC-LBU Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# COLOR PALETTE
# ============================================================================

COLORS = {
    'teal': '#1A7A7A',
    'teal_light': '#1A7A6E',
    'amber': '#C8760A',
    'cyan': '#00e5ff',
    'green': '#00ff00',
    'red': '#ff6b6b',
    'yellow': '#ffd93d',
    'dark_bg': '#0a0e27',
    'card_bg': 'rgba(26, 122, 122, 0.1)',
    'white': '#ffffff'
}

# ============================================================================
# SESSION STATE
# ============================================================================

def initialize_session():
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    if 'filters' not in st.session_state:
        st.session_state['filters'] = {
            'term': 'All', 'year': 'All', 'program': 'All', 'school': 'All',
            'equity_group': 'All', 'flag': 'All', 'current_page': 'home'
        }
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    if 'data_filename' not in st.session_state:
        st.session_state['data_filename'] = None

initialize_session()

# ============================================================================
# DATA LOADING
# ============================================================================

def load_default_data():
    paths = ['data/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
             '/mnt/user-data/outputs/CLC_Allocation_Dashboard_2026_CLEANED.xlsx']
    for path in paths:
        if os.path.exists(path):
            return pd.read_excel(path)
    return None

def create_sample_data():
    import random
    students = ['Ethan Evans', 'Sarah Johnson', 'Michael Brown', 'Jessica White', 'David Lee', 
                'Emma Davis', 'James Wilson', 'Olivia Martinez', 'Noah Rodriguez', 'Ava Taylor']
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary', 
               'Hendon PS', 'Clovelly Park PS', 'Findon HS', 'West Lakes PS']
    programs = ['JP', 'PY', 'SY']
    statuses = ['Allocated', 'On Waiting List', 'Current']
    
    data = {
        'Student_Name': [random.choice(students) for _ in range(80)],
        'Referring_School': [random.choice(schools) for _ in range(80)],
        'Allocated_Program': [random.choice(programs) for _ in range(80)],
        'Allocation_Status': [random.choice(statuses) for _ in range(80)],
        'Flag_ATSI': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_EALD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_SWD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_ASD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_ADHD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Flag_ODD': [random.choice(['Yes', 'No']) for _ in range(80)],
        'Referral_Year': [random.choice([2025, 2026]) for _ in range(80)],
        'Term': [random.choice([1, 2, 3, 4]) for _ in range(80)],
    }
    return pd.DataFrame(data)

# ============================================================================
# FILTER MANAGEMENT
# ============================================================================

def update_filter(name, value):
    st.session_state['filters'][name] = value

def get_active_filters():
    return st.session_state['filters']

def clear_all_filters():
    st.session_state['filters'] = {
        'term': 'All', 'year': 'All', 'program': 'All', 'school': 'All',
        'equity_group': 'All', 'flag': 'All', 'current_page': st.session_state['filters']['current_page']
    }

def get_filter_summary():
    filters = get_active_filters()
    active = [f"{k}: {v}" for k, v in filters.items() if v != 'All' and k != 'current_page']
    return " | ".join(active) if active else "No filters applied ✓"

# ============================================================================
# DATA FILTERING & METRICS
# ============================================================================

def apply_filters(df, filters_dict):
    if df is None or len(df) == 0:
        return df
    filtered = df.copy()
    
    if filters_dict.get('term') != 'All':
        try:
            filtered = filtered[filtered['Term'] == int(filters_dict['term'])]
        except:
            pass
    if filters_dict.get('year') != 'All':
        try:
            filtered = filtered[filtered['Referral_Year'] == int(filters_dict['year'])]
        except:
            pass
    if filters_dict.get('program') != 'All':
        filtered = filtered[filtered['Allocated_Program'] == filters_dict['program']]
    if filters_dict.get('school') != 'All':
        filtered = filtered[filtered['Referring_School'] == filters_dict['school']]
    
    equity = filters_dict.get('equity_group', 'All')
    if equity == 'Indigenous 🇦🇺':
        filtered = filtered[filtered['Flag_ATSI'] == 'Yes']
    elif equity == 'EALD 🌍':
        filtered = filtered[filtered['Flag_EALD'] == 'Yes']
    elif equity == 'SWD ♿':
        filtered = filtered[filtered['Flag_SWD'] == 'Yes']
    elif equity == 'ASD 🧩':
        filtered = filtered[filtered['Flag_ASD'] == 'Yes']
    
    return filtered

def calculate_metrics(df):
    if df is None or len(df) == 0:
        return {'total_referred': 0, 'allocated': 0, 'waiting': 0, 'current': 0, 'allocation_rate': 0}
    
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    waiting = len(df[df['Allocation_Status'] == 'On Waiting List'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    rate = (allocated / total * 100) if total > 0 else 0
    
    return {'total_referred': total, 'allocated': allocated, 'waiting': waiting, 'current': current, 'allocation_rate': rate}

def get_unique_values(df, column):
    if df is None or column not in df.columns:
        return []
    return sorted([v for v in df[column].unique() if pd.notna(v)])

# ============================================================================
# CHARTS
# ============================================================================

def allocation_funnel(df):
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    
    fig = go.Figure(data=[go.Funnel(
        y=['📋 Referred', '✅ Allocated', '🎓 Current'],
        x=[total, allocated, current],
        marker_color=[COLORS['cyan'], COLORS['green'], COLORS['teal']],
        text=[f"{total}", f"{allocated}", f"{current}"],
        textposition='inside',
        textfont=dict(size=12, color=COLORS['white'])
    )])
    
    fig.update_layout(
        title='📊 Allocation Funnel',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white'], size=12),
        height=400,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

def waiting_trend(df):
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    try:
        waiting_by_term = df[df['Allocation_Status'] == 'On Waiting List'].groupby('Term').size().reset_index(name='Waiting')
        if len(waiting_by_term) == 0:
            return go.Figure().add_annotation(text="No waiting students ✅")
        
        fig = go.Figure(data=go.Scatter(
            x=waiting_by_term['Term'],
            y=waiting_by_term['Waiting'],
            mode='lines+markers',
            line=dict(color=COLORS['red'], width=3),
            marker=dict(size=10, color=COLORS['red']),
            fill='tozeroy',
            fillcolor='rgba(255, 107, 107, 0.15)'
        ))
        
        fig.update_layout(
            title='📈 Waiting List Trend',
            paper_bgcolor=COLORS['dark_bg'],
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['white'], size=12),
            height=400
        )
        return fig
    except:
        return go.Figure().add_annotation(text="Error")

def equity_chart(df):
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    
    groups = {'Indigenous 🇦🇺': 'Flag_ATSI', 'EALD 🌍': 'Flag_EALD', 'SWD ♿': 'Flag_SWD', 'ASD 🧩': 'Flag_ASD', 'Overall 📊': None}
    rates, labels, colors_list = [], [], []
    
    for group, flag in groups.items():
        try:
            subset = df[df[flag] == 'Yes'] if flag else df
            if len(subset) > 0:
                allocated = len(subset[subset['Allocation_Status'] == 'Allocated'])
                rate = allocated / len(subset) * 100
                rates.append(rate)
                labels.append(group)
                colors_list.append(COLORS['red'] if rate < 60 else COLORS['yellow'] if rate < 70 else COLORS['green'])
        except:
            pass
    
    if not rates:
        return go.Figure().add_annotation(text="No data")
    
    fig = go.Figure(data=go.Bar(x=labels, y=rates, marker_color=colors_list, text=[f"{r:.0f}%" for r in rates], textposition='outside'))
    fig.update_layout(title='⚖️ Equity Outcomes', paper_bgcolor=COLORS['dark_bg'], plot_bgcolor='rgba(0,0,0,0)',
                     font=dict(color=COLORS['white'], size=12), height=400, yaxis=dict(range=[0, 100]))
    return fig

def program_chart(df):
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    
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
    
    fig.update_layout(title='🎓 Program Capacity', barmode='stack', paper_bgcolor=COLORS['dark_bg'], 
                     plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white'], size=12), height=400)
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
            st.session_state['data_filename'] = uploaded.name
            st.success(f"✅ Loaded: {uploaded.name}")
    
    with col2:
        st.markdown("### 📊 **Status**")
        if st.session_state['data_loaded'] and st.session_state['df'] is not None:
            st.metric("📋 Records", len(st.session_state['df']))
    
    with col3:
        st.markdown("### 🔄 **Demo**")
        if st.button("📥 Load Demo Data"):
            st.session_state['df'] = create_sample_data()
            st.session_state['data_loaded'] = True
            st.session_state['data_filename'] = "Demo Data"
            st.rerun()
    
    st.markdown("---")
    
    if not st.session_state['data_loaded'] or st.session_state['df'] is None:
        st.info("👆 Upload Excel file or load demo data")
        return
    
    df = st.session_state['df']
    
    st.markdown("### 🔽 **Filters**")
    filter_cols = st.columns(6)
    with filter_cols[0]:
        term = st.selectbox("📅 Term", ['All'] + list(map(str, sorted(get_unique_values(df, 'Term')))), key='t')
        if term != get_active_filters()['term']:
            update_filter('term', term)
    with filter_cols[1]:
        year = st.selectbox("📆 Year", ['All'] + list(map(str, sorted(get_unique_values(df, 'Referral_Year')))), key='y')
        if year != get_active_filters()['year']:
            update_filter('year', year)
    with filter_cols[2]:
        prog = st.selectbox("🎓 Program", ['All'] + get_unique_values(df, 'Allocated_Program'), key='p')
        if prog != get_active_filters()['program']:
            update_filter('program', prog)
    with filter_cols[3]:
        school = st.selectbox("🏫 School", ['All'] + get_unique_values(df, 'Referring_School'), key='s')
        if school != get_active_filters()['school']:
            update_filter('school', school)
    with filter_cols[4]:
        equity = st.selectbox("⚖️ Equity", ['All', 'Indigenous 🇦🇺', 'EALD 🌍', 'SWD ♿', 'ASD 🧩'], key='e')
        if equity != get_active_filters()['equity_group']:
            update_filter('equity_group', equity)
    with filter_cols[5]:
        if st.button("🔄 Clear"):
            clear_all_filters()
            st.rerun()
    
    st.markdown("---")
    filtered_df = apply_filters(df, get_active_filters())
    
    st.markdown("### 📈 **Key Metrics**")
    metrics = calculate_metrics(filtered_df)
    cols = st.columns(4)
    cols[0].metric("📋 Referred", metrics['total_referred'])
    cols[1].metric("✅ Allocated", metrics['allocated'], f"{metrics['allocation_rate']:.0f}%")
    cols[2].metric("⏳ Waiting", metrics['waiting'])
    cols[3].metric("🎓 Current", metrics['current'])
    
    st.markdown("---")
    st.markdown("### 📊 **Core Analysis**")
    chart_cols = st.columns(2)
    chart_cols[0].plotly_chart(allocation_funnel(filtered_df), use_container_width=True)
    chart_cols[1].plotly_chart(waiting_trend(filtered_df), use_container_width=True)
    chart_cols = st.columns(2)
    chart_cols[0].plotly_chart(equity_chart(filtered_df), use_container_width=True)
    chart_cols[1].plotly_chart(program_chart(filtered_df), use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🔍 **Explore More**")
    nav_cols = st.columns(4)
    if nav_cols[0].button("📋 Waiting List"):
        update_filter('current_page', 'waiting')
        st.rerun()
    if nav_cols[1].button("👥 Equity"):
        update_filter('current_page', 'equity')
        st.rerun()
    if nav_cols[2].button("🏫 Schools"):
        update_filter('current_page', 'school')
        st.rerun()
    if nav_cols[3].button("📊 More"):
        update_filter('current_page', 'more')
        st.rerun()

def page_waiting(df):
    st.markdown("# 📋 WAITING LIST ANALYSIS")
    if st.button("⬅️ Back"):
        update_filter('current_page', 'home')
        st.rerun()
    st.markdown("---")
    
    if df is None:
        st.warning("No data loaded")
        return
    
    filtered_df = apply_filters(df, get_active_filters())
    waiting = filtered_df[filtered_df['Allocation_Status'] == 'On Waiting List']
    
    st.markdown(f"### 👥 **{len(waiting)} Students Waiting**")
    if len(waiting) > 0:
        cols_show = [c for c in ['Student_Name', 'Referring_School', 'Allocated_Program'] if c in waiting.columns]
        st.dataframe(waiting[cols_show], use_container_width=True, hide_index=True)
    else:
        st.success("✅ No students waiting!")

def page_equity(df):
    st.markdown("# 👥 EQUITY DEEP-DIVE")
    if st.button("⬅️ Back"):
        update_filter('current_page', 'home')
        st.rerun()
    st.markdown("---")
    
    if df is None:
        st.warning("No data loaded")
        return
    
    filtered_df = apply_filters(df, get_active_filters())
    
    tab1, tab2, tab3, tab4 = st.tabs(["🇦🇺 Indigenous", "🌍 EALD", "♿ SWD", "🧩 ASD"])
    
    with tab1:
        indigenous = filtered_df[filtered_df['Flag_ATSI'] == 'Yes']
        if len(indigenous) > 0:
            allocated = len(indigenous[indigenous['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(indigenous), f"Allocated: {allocated/len(indigenous)*100:.0f}%")
    
    with tab2:
        eald = filtered_df[filtered_df['Flag_EALD'] == 'Yes']
        if len(eald) > 0:
            allocated = len(eald[eald['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(eald), f"Allocated: {allocated/len(eald)*100:.0f}%")
    
    with tab3:
        swd = filtered_df[filtered_df['Flag_SWD'] == 'Yes']
        if len(swd) > 0:
            allocated = len(swd[swd['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(swd), f"Allocated: {allocated/len(swd)*100:.0f}%")
    
    with tab4:
        asd = filtered_df[filtered_df['Flag_ASD'] == 'Yes']
        if len(asd) > 0:
            allocated = len(asd[asd['Allocation_Status'] == 'Allocated'])
            st.metric("Students", len(asd), f"Allocated: {allocated/len(asd)*100:.0f}%")

def page_school(df):
    st.markdown("# 🏫 SCHOOL PERFORMANCE")
    if st.button("⬅️ Back"):
        update_filter('current_page', 'home')
        st.rerun()
    st.markdown("---")
    
    if df is None:
        st.warning("No data loaded")
        return
    
    filtered_df = apply_filters(df, get_active_filters())
    school_stats = []
    for school in get_unique_values(filtered_df, 'Referring_School'):
        school_df = filtered_df[filtered_df['Referring_School'] == school]
        allocated = len(school_df[school_df['Allocation_Status'] == 'Allocated'])
        total = len(school_df)
        rate = allocated / total * 100 if total > 0 else 0
        school_stats.append({'School': school, 'Referred': total, 'Allocated': allocated, 'Rate%': f"{rate:.0f}%"})
    
    if school_stats:
        st.dataframe(pd.DataFrame(school_stats), use_container_width=True, hide_index=True)

def page_more(df):
    st.markdown("# 📊 MORE ANALYSIS")
    if st.button("⬅️ Back"):
        update_filter('current_page', 'home')
        st.rerun()
    st.markdown("---")
    st.info("📈 Additional analysis pages coming soon!")

# ============================================================================
# MAIN
# ============================================================================

def main():
    initialize_session()
    
    if not st.session_state['data_loaded']:
        default_data = load_default_data()
        if default_data is not None:
            st.session_state['df'] = default_data
            st.session_state['data_loaded'] = True
            st.session_state['data_filename'] = "Default"
    
    page = get_active_filters().get('current_page', 'home')
    df = st.session_state['df']
    
    if page == 'home':
        page_home(df)
    elif page == 'waiting':
        page_waiting(df)
    elif page == 'equity':
        page_equity(df)
    elif page == 'school':
        page_school(df)
    elif page == 'more':
        page_more(df)
    else:
        page_home(df)

if __name__ == "__main__":
    main()
