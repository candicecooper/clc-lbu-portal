"""
CLC-LBU ALLOCATION DASHBOARD - INTERACTIVE OVERHAUL
Complete drill-down analytics with 4+ levels of analysis
Modern glowing theme with interactive charts and breadcrumb navigation
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
    page_title="📊 CLC-LBU Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# MODERN GLOWING THEME CSS
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
    
    /* GLOWING HEADERS */
    h1 {
        color: #00e5ff !important;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.5) !important;
        border-bottom: 2px solid rgba(26, 122, 122, 0.3) !important;
        padding-bottom: 15px !important;
        font-weight: bold !important;
    }
    
    h2 {
        color: #00e5ff !important;
        text-shadow: 0 0 15px rgba(0, 229, 255, 0.3) !important;
        border-left: 3px solid rgba(0, 229, 255, 0.5) !important;
        padding-left: 10px !important;
    }
    
    h3 {
        color: #00e5ff !important;
        border-left: 2px solid rgba(200, 118, 10, 0.6) !important;
        padding-left: 8px !important;
    }
    
    /* GLOWING METRIC BOXES */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.25) 0%, rgba(0, 229, 255, 0.05) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
        border-left: 4px solid rgba(0, 229, 255, 0.8) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.15), inset 0 0 20px rgba(0, 229, 255, 0.05) !important;
        padding: 15px !important;
    }
    
    [data-testid="metric-container"] > div:first-child {
        color: #00e5ff !important;
        font-weight: bold !important;
    }
    
    /* GLOWING BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.4) 0%, rgba(0, 229, 255, 0.2) 100%) !important;
        color: #00e5ff !important;
        border: 2px solid rgba(0, 229, 255, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.2) !important;
        font-weight: bold !important;
        transition: all 0.3s !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.3) 0%, rgba(26, 122, 122, 0.3) 100%) !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.4) !important;
        border-color: #00e5ff !important;
    }
    
    /* GLOWING INFO BOXES */
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.2) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 4px solid #00e5ff !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.15) !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, rgba(200, 118, 10, 0.2) 0%, rgba(200, 118, 10, 0.1) 100%) !important;
        border-left: 4px solid #C8760A !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(200, 118, 10, 0.15) !important;
    }
    
    .stSuccess {
        background: linear-gradient(135deg, rgba(0, 255, 0, 0.15) 0%, rgba(0, 255, 0, 0.05) 100%) !important;
        border-left: 4px solid #00ff00 !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.15) !important;
    }
    
    /* SELECTBOX GLOW */
    .stSelectbox > div > div {
        background-color: rgba(26, 122, 122, 0.15) !important;
        color: #ffffff !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
        border-radius: 6px !important;
        box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.1) !important;
    }
    
    /* TABS GLOW */
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3), rgba(0, 229, 255, 0.1)) !important;
        border-bottom: 3px solid #00e5ff !important;
        color: #00e5ff !important;
    }
    
    /* SUBTLE DIVIDER */
    hr {
        border: 1px solid rgba(0, 229, 255, 0.15) !important;
        margin: 20px 0 !important;
    }
    
    /* TEXT */
    p, span, label {
        color: #ffffff !important;
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
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    if 'drill_path' not in st.session_state:
        st.session_state['drill_path'] = []
    if 'drill_filters' not in st.session_state:
        st.session_state['drill_filters'] = {}

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
            # Safe int conversion
            for col in ['Term', 'Referral_Year']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            return df
    return None

def create_sample():
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary']
    programs = ['JP', 'PY', 'SY']
    statuses = ['Allocated', 'On Waiting List', 'Current']
    
    df = pd.DataFrame({
        'Referring_School': [random.choice(schools) for _ in range(120)],
        'Allocated_Program': [random.choice(programs) for _ in range(120)],
        'Allocation_Status': [random.choice(statuses) for _ in range(120)],
        'Flag_ATSI': [random.choice(['Yes', 'No']) for _ in range(120)],
        'Flag_EALD': [random.choice(['Yes', 'No']) for _ in range(120)],
        'Flag_SWD': [random.choice(['Yes', 'No']) for _ in range(120)],
        'Flag_ASD': [random.choice(['Yes', 'No']) for _ in range(120)],
        'Referral_Year': [random.choice([2025, 2026]) for _ in range(120)],
        'Term': [random.choice([1, 2, 3, 4]) for _ in range(120)],
    })
    return df

# ============================================================================
# FILTERING & METRICS
# ============================================================================

def apply_drill_filters(df):
    """Apply current drill filters"""
    filtered = df.copy()
    for key, value in st.session_state['drill_filters'].items():
        if value and value != 'All':
            filtered = filtered[filtered[key] == value]
    return filtered

def get_metrics(df):
    """Calculate key metrics"""
    if df is None or len(df) == 0:
        return {'total': 0, 'allocated': 0, 'waiting': 0, 'rate': 0}
    
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    waiting = len(df[df['Allocation_Status'] == 'On Waiting List'])
    rate = (allocated / total * 100) if total > 0 else 0
    
    return {'total': total, 'allocated': allocated, 'waiting': waiting, 'rate': rate}

# ============================================================================
# DRILL-DOWN NAVIGATION
# ============================================================================

def show_breadcrumb():
    """Show navigation breadcrumb"""
    if not st.session_state['drill_path']:
        return
    
    breadcrumb = " → ".join(st.session_state['drill_path'])
    st.markdown(f"📍 **Path:** {breadcrumb}")
    
    if st.button("🏠 Back to Overview"):
        st.session_state['drill_path'] = []
        st.session_state['drill_filters'] = {}
        st.rerun()

def drill_to(level_name, filter_key, filter_value):
    """Drill down to next level"""
    st.session_state['drill_path'].append(f"{level_name}: {filter_value}")
    st.session_state['drill_filters'][filter_key] = filter_value
    st.rerun()

# ============================================================================
# CHARTS WITH DRILL-DOWN
# ============================================================================

def program_distribution_chart(df):
    """Program distribution - clickable"""
    if df is None or len(df) == 0:
        return go.Figure()
    
    prog_counts = df['Allocated_Program'].value_counts().reset_index()
    prog_counts.columns = ['Program', 'Count']
    
    fig = go.Figure(data=[
        go.Bar(
            x=prog_counts['Program'],
            y=prog_counts['Count'],
            marker_color=[COLORS['cyan'], COLORS['green'], COLORS['teal']],
            text=prog_counts['Count'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Students: %{y}<br><i>Click to drill down</i><extra></extra>',
            customdata=prog_counts['Program']
        )
    ])
    
    fig.update_layout(
        title='🎓 Program Distribution',
        xaxis_title='Program',
        yaxis_title='Number of Students',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        hovermode='closest'
    )
    
    return fig, prog_counts

def school_performance_chart(df):
    """School performance - clickable"""
    if df is None or len(df) == 0:
        return go.Figure()
    
    school_stats = []
    for school in df['Referring_School'].unique():
        school_df = df[df['Referring_School'] == school]
        allocated = len(school_df[school_df['Allocation_Status'] == 'Allocated'])
        total = len(school_df)
        rate = (allocated / total * 100) if total > 0 else 0
        school_stats.append({'School': school, 'Rate': rate, 'Total': total})
    
    stats_df = pd.DataFrame(school_stats).sort_values('Rate', ascending=False)
    
    colors_list = [COLORS['green'] if r >= 70 else COLORS['yellow'] if r >= 60 else COLORS['red'] for r in stats_df['Rate']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=stats_df['School'],
            y=stats_df['Rate'],
            marker_color=colors_list,
            text=[f"{r:.0f}%" for r in stats_df['Rate']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Allocation Rate: %{y:.0f}%<br><i>Click to drill down</i><extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='🏫 School Allocation Rates',
        xaxis_title='School',
        yaxis_title='Allocation Rate %',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
        yaxis=dict(range=[0, 100])
    )
    
    return fig, stats_df

def equity_breakdown_chart(df):
    """Equity group breakdown - clickable"""
    if df is None or len(df) == 0:
        return go.Figure()
    
    equity_data = []
    for flag in ['Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD']:
        count = len(df[df[flag] == 'Yes'])
        equity_data.append({'Group': flag.replace('Flag_', ''), 'Count': count})
    
    equity_df = pd.DataFrame(equity_data)
    
    fig = go.Figure(data=[
        go.Bar(
            x=equity_df['Group'],
            y=equity_df['Count'],
            marker_color=[COLORS['cyan'], COLORS['green'], COLORS['yellow'], COLORS['red']],
            text=equity_df['Count'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Count: %{y}<br><i>Click to drill down</i><extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='⚖️ Equity Groups',
        xaxis_title='Group',
        yaxis_title='Number of Students',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    
    return fig, equity_df

def allocation_status_chart(df):
    """Allocation status breakdown"""
    if df is None or len(df) == 0:
        return go.Figure()
    
    status_counts = df['Allocation_Status'].value_counts()
    
    fig = go.Figure(data=[
        go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            marker_colors=[COLORS['green'], COLORS['red'], COLORS['cyan']],
            textposition='inside',
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='📊 Allocation Status',
        paper_bgcolor=COLORS['dark_bg'],
        font=dict(color=COLORS['white']),
        height=400
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
    st.markdown("# 📊 CLC-LBU INTERACTIVE ALLOCATION DASHBOARD")
    st.markdown("_Explore allocation data with 4+ levels of drill-down analysis_")
    
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
        if st.button("📥 Load Demo"):
            st.session_state['df'] = create_sample()
            st.session_state['data_loaded'] = True
            st.rerun()
    
    if df is None:
        st.info("👆 Upload or load demo data")
        return
    
    # Breadcrumb navigation
    show_breadcrumb()
    
    # Apply drill filters
    filtered_df = apply_drill_filters(df)
    metrics = get_metrics(filtered_df)
    
    # Key metrics
    st.markdown("### 📈 Key Metrics")
    cols = st.columns(4)
    cols[0].metric("📋 Total", metrics['total'])
    cols[1].metric("✅ Allocated", metrics['allocated'], f"{metrics['rate']:.0f}%")
    cols[2].metric("⏳ Waiting", metrics['waiting'])
    cols[3].metric("📊 Allocation Rate", f"{metrics['rate']:.0f}%")
    
    st.markdown("---")
    
    # LEVEL 1: OVERVIEW
    if not st.session_state['drill_path']:
        st.markdown("### 🎯 Overview - Click any chart to drill down")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig1, prog_data = program_distribution_chart(filtered_df)
            st.plotly_chart(fig1, use_container_width=True)
            
            st.markdown("**🎓 Drill by Program:**")
            for _, row in prog_data.iterrows():
                if st.button(f"→ {row['Program']} ({row['Count']} students)", key=f"prog_{row['Program']}"):
                    drill_to("Program", "Allocated_Program", row['Program'])
        
        with col2:
            fig2, school_data = school_performance_chart(filtered_df)
            st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("**🏫 Drill by School:**")
            school_cols = st.columns(2)
            schools = sorted(filtered_df['Referring_School'].unique())
            for idx, school in enumerate(schools):
                col = school_cols[idx % 2]
                with col:
                    if st.button(f"→ {school}", key=f"school_{idx}"):
                        drill_to("School", "Referring_School", school)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            fig3 = allocation_status_chart(filtered_df)
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            fig4, equity_data = equity_breakdown_chart(filtered_df)
            st.plotly_chart(fig4, use_container_width=True)
            
            st.markdown("**⚖️ Drill by Equity Group:**")
            equity_cols = st.columns(2)
            for idx, (_, row) in enumerate(equity_data.iterrows()):
                col = equity_cols[idx % 2]
                with col:
                    if st.button(f"→ {row['Group']} ({row['Count']})", key=f"equity_{row['Group']}"):
                        flag_map = {'ATSI': 'Flag_ATSI', 'EALD': 'Flag_EALD', 'SWD': 'Flag_SWD', 'ASD': 'Flag_ASD'}
                        # Special handling for flags
                        st.session_state['drill_path'].append(f"Equity: {row['Group']}")
                        st.session_state['drill_filters'][flag_map[row['Group']]] = 'Yes'
                        st.rerun()
    
    # LEVEL 2+: DETAILED DRILL-DOWN
    else:
        st.markdown(f"### 🔍 Detailed Analysis")
        
        # Show current filtered data summary
        st.markdown(f"**Currently viewing:** {len(filtered_df)} students")
        
        # Metrics for this drill level
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📋 Total", len(filtered_df))
        allocated = len(filtered_df[filtered_df['Allocation_Status'] == 'Allocated'])
        rate = (allocated / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        col2.metric("✅ Allocated", allocated, f"{rate:.0f}%")
        col3.metric("⏳ Waiting", len(filtered_df[filtered_df['Allocation_Status'] == 'On Waiting List']))
        col4.metric("📊 Rate", f"{rate:.0f}%")
        
        # Show available drill-down options based on current filters
        st.markdown("---")
        st.markdown("**📍 Next Level Drill-Down Options:**")
        
        # Show which dimensions are still available
        current_dims = set(st.session_state['drill_filters'].keys())
        available_dims = {
            'Allocated_Program': filtered_df['Allocated_Program'].unique(),
            'Referring_School': filtered_df['Referring_School'].unique(),
            'Term': sorted(filtered_df['Term'].unique()),
            'Referral_Year': sorted(filtered_df['Referral_Year'].unique()),
        }
        
        for dim_key, dim_values in available_dims.items():
            if dim_key not in current_dims and len(dim_values) > 1:
                dim_label = {'Allocated_Program': '🎓 Program', 'Referring_School': '🏫 School', 
                            'Term': '📅 Term', 'Referral_Year': '📆 Year'}[dim_key]
                
                st.markdown(f"**{dim_label}:**")
                cols = st.columns(min(4, len(dim_values)))
                
                for idx, val in enumerate(dim_values):
                    col = cols[idx % len(cols)]
                    with col:
                        if st.button(f"→ {val}", key=f"drill_{dim_key}_{val}"):
                            drill_to(dim_label, dim_key, val)
        
        # Show data table
        st.markdown("---")
        st.markdown(f"**📊 Data Table ({len(filtered_df)} records):**")
        
        # De-identified display
        cols_show = [c for c in ['Referring_School', 'Allocated_Program', 'Allocation_Status', 
                                  'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Term', 'Referral_Year'] 
                     if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_show], use_container_width=True, height=400)

if __name__ == "__main__":
    main()
