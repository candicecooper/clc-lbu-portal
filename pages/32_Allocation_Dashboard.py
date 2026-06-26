"""
CLC-LBU ALLOCATION DASHBOARD - STRATEGIC ANALYTICS
Focus: Equity groups (ATSI, EALD, SWD, ASD) across programs, terms, years
Story: Trends, overrepresentation, retention, school patterns, allocation quality
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
    page_title="📊 CLC-LBU Strategic Analytics",
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
    
    .stTabs [role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3), rgba(0, 229, 255, 0.1)) !important;
        border-bottom: 3px solid #00e5ff !important;
        color: #00e5ff !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.2) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 4px solid #00e5ff !important;
        border-radius: 8px !important;
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

# Equity colors
EQUITY_COLORS = {
    'ATSI': '#ff6b6b',      # Red - overrepresented
    'EALD': '#ffd93d',      # Yellow - rising
    'SWD': '#00e5ff',       # Cyan - stable
    'ASD': '#ff9500'        # Orange - overrepresented
}

# ============================================================================
# SESSION STATE
# ============================================================================

def init_session():
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    if 'current_view' not in st.session_state:
        st.session_state['current_view'] = 'overview'
    if 'selected_equity' not in st.session_state:
        st.session_state['selected_equity'] = None

init_session()

# ============================================================================
# DATA LOADING & PROCESSING
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
    """Create sample data with realistic distributions"""
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary', 'Hendon PS', 'Cowandilla PS']
    programs = ['JP', 'PY', 'SY']
    statuses = ['Allocated', 'On Waiting List', 'Current']
    years = [2024, 2025, 2026]
    
    data = []
    for _ in range(200):
        school = random.choice(schools)
        year = random.choice(years)
        prog = random.choice(programs)
        
        # ATSI overrepresentation
        atsi = 'Yes' if random.random() < 0.35 else 'No'  # Higher prevalence
        # EALD rising trend
        eald = 'Yes' if random.random() < (0.25 if year == 2026 else 0.18) else 'No'
        # SWD stable
        swd = 'Yes' if random.random() < 0.20 else 'No'
        # ASD overrepresented in behaviour
        asd = 'Yes' if random.random() < 0.28 else 'No'
        
        data.append({
            'Referring_School': school,
            'Allocated_Program': prog,
            'Allocation_Status': random.choice(statuses),
            'Flag_ATSI': atsi,
            'Flag_EALD': eald,
            'Flag_SWD': swd,
            'Flag_ASD': asd,
            'Referral_Year': year,
            'Term': random.choice([1, 2, 3, 4]),
        })
    
    return pd.DataFrame(data)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_equity_count(df, flag):
    """Get count and percentage for an equity group"""
    count = len(df[df[f'Flag_{flag}'] == 'Yes'])
    total = len(df)
    pct = (count / total * 100) if total > 0 else 0
    return count, pct

def get_program_stats(df):
    """Get stats by program"""
    stats = []
    for prog in ['JP', 'PY', 'SY']:
        prog_df = df[df['Allocated_Program'] == prog]
        allocated = len(prog_df[prog_df['Allocation_Status'] == 'Allocated'])
        
        stats.append({
            'Program': prog,
            'Total': len(prog_df),
            'Allocated': allocated,
            'Rate': (allocated / len(prog_df) * 100) if len(prog_df) > 0 else 0,
            'Waiting': len(prog_df[prog_df['Allocation_Status'] == 'On Waiting List']),
            'ATSI': len(prog_df[prog_df['Flag_ATSI'] == 'Yes']),
            'EALD': len(prog_df[prog_df['Flag_EALD'] == 'Yes']),
            'SWD': len(prog_df[prog_df['Flag_SWD'] == 'Yes']),
            'ASD': len(prog_df[prog_df['Flag_ASD'] == 'Yes']),
        })
    
    return pd.DataFrame(stats)

# ============================================================================
# STRATEGIC CHARTS
# ============================================================================

def equity_distribution_by_program(df):
    """Show equity groups across programs - tells the story"""
    programs = ['JP', 'PY', 'SY']
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
            text=[f"{p:.0f}%" for p in equity_data['Percentage']],
            textposition='outside'
        ))
    
    fig.update_layout(
        title='⚖️ Equity Group Representation by Program (%)',
        barmode='group',
        xaxis_title='Program',
        yaxis_title='Percentage of Students',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        hovermode='x unified'
    )
    return fig

def equity_trend_by_year(df):
    """Show ATSI/EALD trends over time"""
    years = sorted([y for y in df['Referral_Year'].unique() if y > 0])
    equity_groups = ['ATSI', 'EALD']
    
    data = []
    for year in years:
        year_df = df[df['Referral_Year'] == year]
        for equity in equity_groups:
            count = len(year_df[year_df[f'Flag_{equity}'] == 'Yes'])
            total = len(year_df)
            pct = (count / total * 100) if total > 0 else 0
            data.append({'Year': year, 'Group': equity, 'Percentage': pct})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure()
    for equity in equity_groups:
        equity_data = data_df[data_df['Group'] == equity].sort_values('Year')
        fig.add_trace(go.Scatter(
            x=equity_data['Year'],
            y=equity_data['Percentage'],
            name=equity,
            mode='lines+markers',
            line=dict(color=EQUITY_COLORS.get(equity, '#00e5ff'), width=3),
            marker=dict(size=10),
            fill='tozeroy',
            fillcolor=f"rgba({int(EQUITY_COLORS[equity][1:3], 16)}, {int(EQUITY_COLORS[equity][3:5], 16)}, {int(EQUITY_COLORS[equity][5:7], 16)}, 0.1)"
        ))
    
    fig.update_layout(
        title='📈 ATSI & EALD Trend (EALD Rising, ATSI Overrepresented)',
        xaxis_title='Year',
        yaxis_title='Percentage of Referrals',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        hovermode='x unified'
    )
    return fig

def school_referral_patterns(df):
    """Which schools refer the most"""
    school_counts = df['Referring_School'].value_counts().reset_index()
    school_counts.columns = ['School', 'Count']
    school_counts = school_counts.sort_values('Count', ascending=True)
    
    fig = go.Figure(data=[
        go.Bar(
            y=school_counts['School'],
            x=school_counts['Count'],
            orientation='h',
            marker_color=COLORS['cyan'],
            text=school_counts['Count'],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title='🏫 Referral Volume by School',
        xaxis_title='Number of Referrals',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

def program_performance(df):
    """Program comparison - allocation success"""
    prog_stats = get_program_stats(df)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=prog_stats['Program'],
        y=prog_stats['Allocated'],
        name='✅ Allocated',
        marker_color=COLORS['green']
    ))
    
    fig.add_trace(go.Bar(
        x=prog_stats['Program'],
        y=prog_stats['Waiting'],
        name='⏳ Waiting',
        marker_color=COLORS['red']
    ))
    
    fig.update_layout(
        title='🎓 Program Allocation Performance',
        barmode='stack',
        xaxis_title='Program',
        yaxis_title='Number of Students',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

def allocation_rate_by_program(df):
    """Allocation success rate by program"""
    prog_stats = get_program_stats(df)
    
    fig = go.Figure(data=[
        go.Bar(
            x=prog_stats['Program'],
            y=prog_stats['Rate'],
            marker_color=[COLORS['green'] if r >= 70 else COLORS['yellow'] if r >= 60 else COLORS['red'] for r in prog_stats['Rate']],
            text=[f"{r:.0f}%" for r in prog_stats['Rate']],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title='📊 Allocation Success Rate by Program',
        xaxis_title='Program',
        yaxis_title='Allocation Rate %',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        yaxis=dict(range=[0, 100])
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
    st.markdown("# 📊 CLC-LBU STRATEGIC ANALYTICS DASHBOARD")
    st.markdown("_Understanding equity, programs, and outcomes across the centre_")
    
    # Data management
    col1, col2, col3 = st.columns([2, 1, 1])
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
    
    with col3:
        if st.button("📥 Load Strategic Demo"):
            st.session_state['df'] = create_strategic_sample()
            st.session_state['data_loaded'] = True
            st.rerun()
    
    if df is None:
        st.info("👆 Upload or load demo data to start")
        return
    
    # KEY METRICS OVERVIEW
    st.markdown("## 📈 Centre Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total = len(df)
    col1.metric("📋 Total Referrals", total)
    
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    rate = (allocated / total * 100) if total > 0 else 0
    col2.metric("✅ Allocated", f"{allocated} ({rate:.0f}%)")
    
    atsi_count, atsi_pct = get_equity_count(df, 'ATSI')
    col3.metric("🇦🇺 ATSI (Overrepresented)", f"{atsi_count} ({atsi_pct:.0f}%)")
    
    eald_count, eald_pct = get_equity_count(df, 'EALD')
    col4.metric("🌍 EALD (Rising)", f"{eald_count} ({eald_pct:.0f}%)")
    
    asd_count, asd_pct = get_equity_count(df, 'ASD')
    col5.metric("🧩 ASD (Overrepresented)", f"{asd_count} ({asd_pct:.0f}%)")
    
    st.markdown("---")
    
    # STRATEGIC TABS
    st.markdown("## 🎯 Strategic Analysis")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚖️ Equity Overview",
        "📈 Trends",
        "🏫 Schools",
        "🎓 Programs",
        "📊 Detailed Data"
    ])
    
    with tab1:
        st.markdown("### Equity Representation Across Programs")
        st.info("📌 **Story**: See how ATSI and ASD are overrepresented. EALD rising. Show program differences.")
        
        col1, col2 = st.columns(2)
        with col1:
            fig1 = equity_distribution_by_program(df)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            prog_stats = get_program_stats(df)
            st.markdown("### Program Summary")
            st.dataframe(prog_stats[['Program', 'Total', 'Allocated', 'ATSI', 'EALD', 'SWD', 'ASD']], use_container_width=True)
    
    with tab2:
        st.markdown("### Year-on-Year Trends")
        st.info("📌 **Story**: EALD allocations rising. ATSI consistently overrepresented. Track changes.")
        
        fig2 = equity_trend_by_year(df)
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
        st.markdown("### School Referral Patterns")
        st.info("📌 **Story**: Which schools refer most. High-referral schools may indicate need or socioeconomic factors.")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig3 = school_referral_patterns(df)
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            school_counts = df['Referring_School'].value_counts().reset_index()
            school_counts.columns = ['School', 'Count']
            st.markdown("### Referral Count by School")
            st.dataframe(school_counts, use_container_width=True)
    
    with tab4:
        st.markdown("### Program Comparison")
        st.info("📌 **Story**: Compare JP, PY, SY. Allocation rates. Equity group distribution.")
        
        col1, col2 = st.columns(2)
        with col1:
            fig4 = program_performance(df)
            st.plotly_chart(fig4, use_container_width=True)
        
        with col2:
            fig5 = allocation_rate_by_program(df)
            st.plotly_chart(fig5, use_container_width=True)
    
    with tab5:
        st.markdown("### Full Data Export")
        st.markdown("De-identified data for manual analysis")
        
        cols_show = [c for c in ['Referring_School', 'Allocated_Program', 'Allocation_Status', 
                                  'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Referral_Year', 'Term'] 
                     if c in df.columns]
        st.dataframe(df[cols_show], use_container_width=True, height=500)

if __name__ == "__main__":
    main()
