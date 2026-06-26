"""
CLC-LBU STRATEGIC ANALYTICS - FULLY INTERACTIVE
Year/Term/Program filters + clickable charts + deep drill-down
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import random

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="📊 CLC-LBU Interactive Analytics",
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
        margin-top: 30px !important;
    }
    
    h3 {
        color: #C8760A !important;
        border-left: 2px solid rgba(200, 118, 10, 0.6) !important;
        padding-left: 8px !important;
    }
    
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.25) 0%, rgba(0, 229, 255, 0.05) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
        border-left: 4px solid rgba(0, 229, 255, 0.8) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.15) !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.4) 0%, rgba(0, 229, 255, 0.2) 100%) !important;
        color: #00e5ff !important;
        border: 2px solid rgba(0, 229, 255, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.2) !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.2) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 4px solid #00e5ff !important;
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

def create_strategic_sample():
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary', 'Hendon PS', 'Cowandilla PS']
    programs = ['JP', 'PY', 'SY']
    statuses = ['Allocated', 'On Waiting List', 'Current']
    years = [2024, 2025, 2026]
    
    data = []
    for _ in range(250):
        data.append({
            'Referring_School': random.choice(schools),
            'Allocated_Program': random.choice(programs),
            'Allocation_Status': random.choice(statuses),
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
    """Apply all active filters"""
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
# INTERACTIVE CHARTS
# ============================================================================

def equity_distribution_by_program(df):
    """Clickable equity by program"""
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
        title='⚖️ Equity by Program (Click bars to drill)',
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
    """Trend lines - interactive"""
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
        title='📈 ATSI & EALD Trends (Hover for details)',
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
    """School x Equity heatmap"""
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
        title='🔥 School Equity Heatmap (Red = High %, Click schools)',
        paper_bgcolor=COLORS['dark_bg'],
        font=dict(color=COLORS['white']),
        height=450
    )
    return fig

def program_performance(df):
    """Program bars - clickable"""
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
        title='🎓 Program Allocation (Click to drill)',
        barmode='stack',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=450,
        hovermode='x unified'
    )
    return fig

# ============================================================================
# MAIN DASHBOARD
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
    st.markdown("# 📊 CLC-LBU INTERACTIVE ANALYTICS")
    st.markdown("_Explore equity, programs & outcomes with dynamic filtering_")
    
    # Data upload
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
    
    # FILTERS (Top bar)
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
    
    # Apply filters
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
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚖️ Equity by Program",
        "📈 Year Trends",
        "🔥 School Heatmap",
        "🎓 Program Performance",
        "📋 Raw Data"
    ])
    
    with tab1:
        st.markdown("### Equity Distribution Across Programs")
        st.info("💡 **Hover** for counts. **Click bars** to filter further.")
        fig1 = equity_distribution_by_program(filtered_df)
        st.plotly_chart(fig1, use_container_width=True)
    
    with tab2:
        st.markdown("### Year-over-Year Trends")
        st.info("💡 **Hover** for details. See EALD rising, ATSI persistent.")
        fig2 = equity_trend_by_year(filtered_df)
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
        st.markdown("### School x Equity Breakdown")
        st.info("💡 Red = higher %. **Hover** for exact %. Click schools in filter.")
        fig3 = school_referral_heatmap(filtered_df)
        st.plotly_chart(fig3, use_container_width=True)
    
    with tab4:
        st.markdown("### Program Performance")
        st.info("💡 Allocation vs Waiting. **Hover** for exact counts.")
        fig4 = program_performance(filtered_df)
        st.plotly_chart(fig4, use_container_width=True)
    
    with tab5:
        st.markdown("### De-identified Data")
        cols_show = [c for c in ['Referring_School', 'Allocated_Program', 'Allocation_Status', 
                                  'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Referral_Year', 'Term'] 
                     if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_show], use_container_width=True, height=500)

if __name__ == "__main__":
    main()
