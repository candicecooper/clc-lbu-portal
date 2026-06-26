"""
CLC-LBU INTERACTIVE ANALYTICS - ENHANCED
Added: Current Cohort view + Modern styling + Better text contrast
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import random
from datetime import datetime, timedelta

st.set_page_config(
    page_title="📊 CLC-LBU Interactive Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ENHANCED MODERN THEME CSS
# ============================================================================

st.markdown("""
<style>
    /* DARK BACKGROUND */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0a0e27 !important;
        border-right: 2px solid rgba(26, 122, 122, 0.5) !important;
    }
    
    /* BRIGHT HEADERS */
    h1 {
        color: #00e5ff !important;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.5) !important;
        border-bottom: 2px solid rgba(26, 122, 122, 0.3) !important;
        padding-bottom: 15px !important;
        font-size: 2.2em !important;
    }
    
    h2 {
        color: #00e5ff !important;
        border-left: 3px solid rgba(0, 229, 255, 0.5) !important;
        padding-left: 10px !important;
        margin-top: 25px !important;
    }
    
    h3 {
        color: #ffd93d !important;
        border-left: 2px solid rgba(255, 217, 61, 0.6) !important;
        padding-left: 8px !important;
    }
    
    /* BRIGHT TEXT - GREY IS GONE */
    p, span, label, .stText, [data-testid="stMarkdownContainer"] {
        color: #e8e8e8 !important;
    }
    
    /* MODERN FILTER BOXES */
    .stSelectbox > div > div {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        color: #00e5ff !important;
        border: 2px solid rgba(0, 229, 255, 0.6) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.2), inset 0 0 10px rgba(0, 229, 255, 0.05) !important;
        padding: 10px !important;
        font-weight: 500 !important;
    }
    
    /* Bright text in selectbox input */
    .stSelectbox input {
        color: #00e5ff !important;
        background-color: transparent !important;
    }
    
    .stSelectbox input::placeholder {
        color: rgba(0, 229, 255, 0.6) !important;
    }
    
    /* Dropdown content */
    [data-baseweb="select"] {
        color: #00e5ff !important;
    }
    
    [data-baseweb="select"] input {
        color: #00e5ff !important;
    }
    
    [data-baseweb="popover"] {
        background-color: rgba(10, 14, 39, 0.95) !important;
    }
    
    [data-baseweb="menu"] {
        background-color: rgba(10, 14, 39, 0.95) !important;
    }
    
    [data-baseweb="menu"] li {
        color: #e8e8e8 !important;
        background-color: transparent !important;
    }
    
    [data-baseweb="menu"] li:hover {
        background-color: rgba(0, 229, 255, 0.25) !important;
        color: #00e5ff !important;
    }
    
    .stSelectbox label {
        color: #00e5ff !important;
        font-weight: bold !important;
    }
    
    /* GLOWING METRICS */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3) 0%, rgba(0, 229, 255, 0.08) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.4) !important;
        border-left: 5px solid rgba(0, 229, 255, 0.9) !important;
        border-radius: 12px !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.2), inset 0 0 15px rgba(0, 229, 255, 0.05) !important;
        padding: 18px !important;
    }
    
    [data-testid="metric-container"] > div:first-child {
        color: #00e5ff !important;
        font-weight: bold !important;
        font-size: 1.1em !important;
    }
    
    [data-testid="metric-container"] > div:last-child {
        color: #ffd93d !important;
        font-weight: bold !important;
        font-size: 1.8em !important;
    }
    
    /* MODERN GLOWING BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.5) 0%, rgba(0, 229, 255, 0.25) 100%) !important;
        color: #00e5ff !important;
        border: 2px solid rgba(0, 229, 255, 0.6) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.25) !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
        font-size: 0.95em !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.4) 0%, rgba(26, 122, 122, 0.4) 100%) !important;
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.5), inset 0 0 10px rgba(0, 229, 255, 0.1) !important;
        border-color: #00e5ff !important;
    }
    
    /* INFO BOXES */
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.25) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 5px solid #00e5ff !important;
        border-radius: 10px !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.15) !important;
    }
    
    .stInfo > div {
        color: #e8e8e8 !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, rgba(200, 118, 10, 0.2) 0%, rgba(200, 118, 10, 0.1) 100%) !important;
        border-left: 5px solid #ffd93d !important;
        border-radius: 10px !important;
    }
    
    .stSuccess {
        background: linear-gradient(135deg, rgba(0, 255, 0, 0.15) 0%, rgba(0, 255, 0, 0.05) 100%) !important;
        border-left: 5px solid #00ff00 !important;
        border-radius: 10px !important;
    }
    
    /* TABS */
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 2px solid rgba(0, 229, 255, 0.2) !important;
    }
    
    [data-testid="stTabs"] [role="tab"] {
        color: #a8a8a8 !important;
        border-radius: 8px 8px 0 0 !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3), rgba(0, 229, 255, 0.1)) !important;
        border-bottom: 3px solid #00e5ff !important;
        color: #00e5ff !important;
        font-weight: bold !important;
    }
    
    /* DIVIDER */
    hr {
        border: 1px solid rgba(0, 229, 255, 0.15) !important;
    }
    
    /* DATAFRAME */
    [data-testid="stDataFrame"] {
        background-color: #0a0e27 !important;
    }
    
    [data-testid="stDataFrame"] > div > div {
        color: #e8e8e8 !important;
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

EQUITY_COLORS = {
    'ATSI': '#ff6b6b',
    'EALD': '#ffd93d',
    'SWD': '#00e5ff',
    'ASD': '#ff9500'
}

# ============================================================================
# SESSION STATE
# ============================================================================

def init_session():
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    if 'selected_year' not in st.session_state:
        st.session_state['selected_year'] = 'All'
    if 'selected_term' not in st.session_state:
        st.session_state['selected_term'] = 'All'
    if 'selected_program' not in st.session_state:
        st.session_state['selected_program'] = 'All'
    if 'selected_school' not in st.session_state:
        st.session_state['selected_school'] = None

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

def create_strategic_sample():
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary', 'Hendon PS', 'Cowandilla PS']
    programs = ['JP', 'PY', 'SY']
    years = [2024, 2025, 2026]
    
    data = []
    # Create 250 total records
    for i in range(250):
        # Distribute statuses: 40% Current, 40% Allocated, 20% Waiting
        if i < 100:
            status = 'Current'  # 100 current students
        elif i < 200:
            status = 'Allocated'  # 100 allocated
        else:
            status = 'On Waiting List'  # 50 waiting
        
        data.append({
            'Referring_School': random.choice(schools),
            'Allocated_Program': random.choice(programs),
            'Allocation_Status': status,
            'Flag_ATSI': 'Yes' if random.random() < 0.35 else 'No',
            'Flag_EALD': 'Yes' if random.random() < 0.22 else 'No',
            'Flag_SWD': 'Yes' if random.random() < 0.20 else 'No',
            'Flag_ASD': 'Yes' if random.random() < 0.28 else 'No',
            'Referral_Year': random.choice(years),
            'Term': random.choice([1, 2, 3, 4]),
        })
    
    return pd.DataFrame(data)

# ============================================================================
# FILTERING
# ============================================================================

def apply_filters(df):
    filtered = df.copy()
    
    if st.session_state['selected_year'] != 'All':
        filtered = filtered[filtered['Referral_Year'] == int(st.session_state['selected_year'])]
    
    if st.session_state['selected_term'] != 'All':
        filtered = filtered[filtered['Term'] == int(st.session_state['selected_term'])]
    
    if st.session_state['selected_program'] != 'All':
        filtered = filtered[filtered['Allocated_Program'] == st.session_state['selected_program']]
    
    if st.session_state['selected_school']:
        filtered = filtered[filtered['Referring_School'] == st.session_state['selected_school']]
    
    return filtered

def get_equity_count(df, flag):
    count = len(df[df[f'Flag_{flag}'] == 'Yes'])
    total = len(df)
    pct = (count / total * 100) if total > 0 else 0
    return count, pct

# ============================================================================
# CURRENT COHORT VIEW
# ============================================================================

def show_current_cohort(df):
    """Show students currently at CLC-LBU"""
    
    # DEBUG: Show available statuses
    with st.expander("🔍 Debug: Available Status Values"):
        st.write("Unique Allocation_Status values in data:")
        statuses = df['Allocation_Status'].unique()
        st.write(statuses)
    
    # Filter for current - match case-insensitive
    current = df[df['Allocation_Status'].str.lower() == 'current']
    
    # If no "Current", try "In Progress" or other common values
    if len(current) == 0:
        possible_statuses = [s for s in df['Allocation_Status'].unique() if pd.notna(s)]
        st.warning(f"⚠️ No students with status 'Current'. Found statuses: {possible_statuses}")
        
        # Try alternative names
        for alt_status in ['In Progress', 'Active', 'Enrolled', 'current']:
            alt_current = df[df['Allocation_Status'].str.lower() == alt_status.lower()]
            if len(alt_current) > 0:
                st.info(f"✅ Using status: '{alt_status}' ({len(alt_current)} students)")
                current = alt_current
                break
    
    if len(current) == 0:
        st.error("❌ No current students found. Please check your data's Allocation_Status values.")
        return
    
    st.markdown("### 👥 Current Students at CLC-LBU")
    
    # Key metrics for current cohort
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("📍 Currently Enrolled", len(current))
    
    atsi_curr = len(current[current['Flag_ATSI'] == 'Yes'])
    col2.metric("🇦🇺 ATSI", f"{atsi_curr} ({atsi_curr/len(current)*100 if len(current) > 0 else 0:.0f}%)")
    
    eald_curr = len(current[current['Flag_EALD'] == 'Yes'])
    col3.metric("🌍 EALD", f"{eald_curr} ({eald_curr/len(current)*100 if len(current) > 0 else 0:.0f}%)")
    
    swd_curr = len(current[current['Flag_SWD'] == 'Yes'])
    col4.metric("♿ SWD", f"{swd_curr} ({swd_curr/len(current)*100 if len(current) > 0 else 0:.0f}%)")
    
    asd_curr = len(current[current['Flag_ASD'] == 'Yes'])
    col5.metric("🧩 ASD", f"{asd_curr} ({asd_curr/len(current)*100 if len(current) > 0 else 0:.0f}%)")
    
    st.markdown("---")
    
    # Program distribution
    st.markdown("### 🎓 Current Students by Program")
    prog_data = []
    for prog in ['JP', 'PY', 'SY']:
        prog_count = len(current[current['Allocated_Program'] == prog])
        prog_data.append({'Program': prog, 'Count': prog_count})
    
    prog_df = pd.DataFrame(prog_data)
    
    fig1 = go.Figure(data=[
        go.Bar(
            x=prog_df['Program'],
            y=prog_df['Count'],
            marker_color=[COLORS['cyan'], COLORS['green'], COLORS['amber']],
            text=prog_df['Count'],
            textposition='outside'
        )
    ])
    
    fig1.update_layout(
        title='Current Students by Program',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        xaxis_title='Program',
        yaxis_title='Number of Students'
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Equity breakdown
        st.markdown("### ⚖️ Equity Representation (Current)")
        equity_data = []
        for equity in ['ATSI', 'EALD', 'SWD', 'ASD']:
            count = len(current[current[f'Flag_{equity}'] == 'Yes'])
            pct = (count / len(current) * 100) if len(current) > 0 else 0
            equity_data.append({'Group': equity, 'Count': count, 'Percentage': pct})
        
        equity_df = pd.DataFrame(equity_data)
        
        fig2 = go.Figure(data=[
            go.Bar(
                x=equity_df['Group'],
                y=equity_df['Count'],
                marker_color=[EQUITY_COLORS.get(g, '#00e5ff') for g in equity_df['Group']],
                text=equity_df['Count'],
                textposition='outside'
            )
        ])
        
        fig2.update_layout(
            title='Current Students by Equity Group',
            paper_bgcolor=COLORS['dark_bg'],
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['white']),
            height=400,
            xaxis_title='Equity Group',
            yaxis_title='Number of Students'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    # School distribution
    st.markdown("### 🏫 Where Current Students Came From")
    school_data = current['Referring_School'].value_counts().reset_index()
    school_data.columns = ['School', 'Count']
    school_data = school_data.sort_values('Count', ascending=True)
    
    fig3 = go.Figure(data=[
        go.Bar(
            y=school_data['School'],
            x=school_data['Count'],
            orientation='h',
            marker_color=COLORS['cyan'],
            text=school_data['Count'],
            textposition='outside'
        )
    ])
    
    fig3.update_layout(
        title='Current Students by Referring School',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        xaxis_title='Number of Students',
        yaxis_title='School'
    )
    
    st.plotly_chart(fig3, use_container_width=True)
    
    st.markdown("---")
    
    # Data table
    st.markdown("### 📊 Current Student Details")
    cols_show = [c for c in ['Referring_School', 'Allocated_Program', 'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Referral_Year', 'Term'] if c in current.columns]
    st.dataframe(current[cols_show], use_container_width=True, height=400)

# ============================================================================
# INTERACTIVE CHARTS
# ============================================================================

def equity_distribution_by_program(df):
    programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
    equity_groups = ['ATSI', 'EALD', 'SWD', 'ASD']
    
    data = []
    for prog in programs:
        prog_df = df[df['Allocated_Program'] == prog]
        for equity in equity_groups:
            count = len(prog_df[prog_df[f'Flag_{equity}'] == 'Yes'])
            total = len(prog_df)
            pct = (count / total * 100) if total > 0 else 0
            data.append({'Program': prog, 'Group': equity, 'Percentage': pct, 'Count': count})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure()
    for equity in equity_groups:
        equity_data = data_df[data_df['Group'] == equity]
        fig.add_trace(go.Bar(
            x=equity_data['Program'],
            y=equity_data['Percentage'],
            name=equity,
            marker_color=EQUITY_COLORS.get(equity, '#00e5ff'),
            customdata=equity_data['Count'],
            hovertemplate='<b>%{x}</b><br>%{fullData.name}: %{y:.1f}%<br>Count: %{customdata}<extra></extra>'
        ))
    
    fig.update_layout(
        title='⚖️ Equity by Program',
        barmode='group',
        xaxis_title='Program',
        yaxis_title='Percentage',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=450,
        hovermode='x unified'
    )
    return fig

def equity_trend_by_year(df):
    years = sorted([y for y in df['Referral_Year'].unique() if y > 0])
    equity_groups = ['ATSI', 'EALD']
    
    data = []
    for year in years:
        year_df = df[df['Referral_Year'] == year]
        for equity in equity_groups:
            count = len(year_df[year_df[f'Flag_{equity}'] == 'Yes'])
            total = len(year_df)
            pct = (count / total * 100) if total > 0 else 0
            data.append({'Year': year, 'Group': equity, 'Percentage': pct, 'Count': count})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure()
    for equity in equity_groups:
        equity_data = data_df[data_df['Group'] == equity].sort_values('Year')
        fig.add_trace(go.Scatter(
            x=equity_data['Year'],
            y=equity_data['Percentage'],
            name=equity,
            mode='lines+markers',
            line=dict(color=EQUITY_COLORS.get(equity, '#00e5ff'), width=4),
            marker=dict(size=12),
            customdata=equity_data['Count'],
            hovertemplate='<b>%{x}</b><br>%{fullData.name}: %{y:.1f}%<br>Count: %{customdata}<extra></extra>'
        ))
    
    fig.update_layout(
        title='📈 ATSI & EALD Trends',
        xaxis_title='Year',
        yaxis_title='Percentage of Referrals',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=450,
        hovermode='x unified'
    )
    return fig

def school_referral_heatmap(df):
    schools = sorted([s for s in df['Referring_School'].unique() if pd.notna(s)])
    equity_groups = ['ATSI', 'EALD', 'SWD', 'ASD']
    
    data = []
    for school in schools:
        school_df = df[df['Referring_School'] == school]
        for equity in equity_groups:
            count = len(school_df[school_df[f'Flag_{equity}'] == 'Yes'])
            total = len(school_df)
            pct = (count / total * 100) if total > 0 else 0
            data.append({'School': school, 'Group': equity, 'Percentage': pct})
    
    data_df = pd.DataFrame(data)
    pivot = data_df.pivot(index='School', columns='Group', values='Percentage')
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale='RdYlGn_r',
        text=[[f"{v:.0f}%" for v in row] for row in pivot.values],
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="% of School"),
        hovertemplate='<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='🔥 School Equity Heatmap',
        paper_bgcolor=COLORS['dark_bg'],
        font=dict(color=COLORS['white']),
        height=450
    )
    return fig

def program_performance(df):
    programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
    
    data = []
    for prog in programs:
        prog_df = df[df['Allocated_Program'] == prog]
        allocated = len(prog_df[prog_df['Allocation_Status'] == 'Allocated'])
        waiting = len(prog_df[prog_df['Allocation_Status'] == 'On Waiting List'])
        data.append({'Program': prog, 'Allocated': allocated, 'Waiting': waiting, 'Total': len(prog_df)})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=data_df['Program'], y=data_df['Allocated'], name='✅ Allocated', marker_color=COLORS['green']))
    fig.add_trace(go.Bar(x=data_df['Program'], y=data_df['Waiting'], name='⏳ Waiting', marker_color=COLORS['red']))
    
    fig.update_layout(
        title='🎓 Program Allocation',
        barmode='stack',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=450,
        hovermode='x unified'
    )
    return fig

# ============================================================================
# MAIN
# ============================================================================

def main():
    if not st.session_state['data_loaded']:
        default = load_data()
        if default is not None:
            st.session_state['df'] = default
            st.session_state['data_loaded'] = True
    
    df = st.session_state['df']
    
    st.markdown("# 📊 CLC-LBU INTERACTIVE ANALYTICS")
    st.markdown("_Explore equity, programs & outcomes with dynamic filtering_")
    
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
            st.session_state['df'] = create_strategic_sample()
            st.session_state['data_loaded'] = True
            st.rerun()
    
    if df is None:
        st.info("👆 Upload or load demo")
        return
    
    # FILTERS
    st.markdown("## 🔍 Filters")
    
    filter_cols = st.columns(5)
    
    with filter_cols[0]:
        years = sorted([y for y in df['Referral_Year'].unique() if y > 0])
        selected_year = st.selectbox("📆 Year", ['All'] + [str(y) for y in years], index=0)
        st.session_state['selected_year'] = selected_year
    
    with filter_cols[1]:
        terms = sorted([t for t in df['Term'].unique() if t > 0])
        selected_term = st.selectbox("📅 Term", ['All'] + [str(t) for t in terms], index=0)
        st.session_state['selected_term'] = selected_term
    
    with filter_cols[2]:
        programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
        selected_program = st.selectbox("🎓 Program", ['All'] + programs, index=0)
        st.session_state['selected_program'] = selected_program
    
    with filter_cols[3]:
        schools = sorted([s for s in df['Referring_School'].unique() if pd.notna(s)])
        selected_school = st.selectbox("🏫 School", ['All'] + schools, index=0)
        st.session_state['selected_school'] = None if selected_school == 'All' else selected_school
    
    with filter_cols[4]:
        if st.button("🔄 Reset Filters"):
            st.session_state['selected_year'] = 'All'
            st.session_state['selected_term'] = 'All'
            st.session_state['selected_program'] = 'All'
            st.session_state['selected_school'] = None
            st.rerun()
    
    filtered_df = apply_filters(df)
    
    st.markdown("---")
    
    # KEY METRICS
    st.markdown("## 📈 Filtered Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total = len(filtered_df)
    col1.metric("📋 Total", total)
    
    allocated = len(filtered_df[filtered_df['Allocation_Status'] == 'Allocated'])
    rate = (allocated / total * 100) if total > 0 else 0
    col2.metric("✅ Allocated", f"{allocated} ({rate:.0f}%)")
    
    atsi_count, atsi_pct = get_equity_count(filtered_df, 'ATSI')
    col3.metric("🇦🇺 ATSI", f"{atsi_count} ({atsi_pct:.0f}%)")
    
    eald_count, eald_pct = get_equity_count(filtered_df, 'EALD')
    col4.metric("🌍 EALD", f"{eald_count} ({eald_pct:.0f}%)")
    
    asd_count, asd_pct = get_equity_count(filtered_df, 'ASD')
    col5.metric("🧩 ASD", f"{asd_count} ({asd_pct:.0f}%)")
    
    st.markdown("---")
    
    # TABS
    st.markdown("## 📊 Analysis")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👥 Current Cohort",
        "⚖️ Equity by Program",
        "📈 Year Trends",
        "🔥 School Heatmap",
        "🎓 Program Performance",
        "📋 Raw Data"
    ])
    
    with tab1:
        show_current_cohort(filtered_df)
    
    with tab2:
        fig1 = equity_distribution_by_program(filtered_df)
        st.plotly_chart(fig1, use_container_width=True)
    
    with tab3:
        fig2 = equity_trend_by_year(filtered_df)
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab4:
        fig3 = school_referral_heatmap(filtered_df)
        st.plotly_chart(fig3, use_container_width=True)
    
    with tab5:
        fig4 = program_performance(filtered_df)
        st.plotly_chart(fig4, use_container_width=True)
    
    with tab6:
        st.markdown("### De-identified Data")
        cols_show = [c for c in ['Referring_School', 'Allocated_Program', 'Allocation_Status', 
                                  'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Referral_Year', 'Term'] 
                     if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_show], use_container_width=True, height=500)

if __name__ == "__main__":
    main()
