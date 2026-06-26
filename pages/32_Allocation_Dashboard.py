"""
CLC-LBU STRATEGIC ANALYTICS - COMPLETE
ALL previous views + NEW insights
Correct hierarchy: ATSI | EALD | SWD (contains ASD, ADHD, etc.)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import random

st.set_page_config(
    page_title="📊 CLC-LBU Strategic Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ENHANCED CSS
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
        color: #ffd93d !important;
        border-left: 2px solid rgba(255, 217, 61, 0.6) !important;
        padding-left: 8px !important;
    }
    
    p, span, label {
        color: #e8e8e8 !important;
    }
    
    .stSelectbox > div > div {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border: 2px solid rgba(0, 229, 255, 0.6) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.2) !important;
        padding: 10px !important;
    }
    
    .stSelectbox > div > div > div {
        color: #00e5ff !important;
        font-weight: bold !important;
    }
    
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3) 0%, rgba(0, 229, 255, 0.08) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.4) !important;
        border-left: 5px solid rgba(0, 229, 255, 0.9) !important;
        border-radius: 12px !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.2) !important;
        padding: 18px !important;
    }
    
    [data-testid="metric-container"] > div:first-child {
        color: #00e5ff !important;
        font-weight: bold !important;
    }
    
    [data-testid="metric-container"] > div:last-child {
        color: #ffd93d !important;
        font-weight: bold !important;
        font-size: 1.8em !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.5) 0%, rgba(0, 229, 255, 0.25) 100%) !important;
        color: #00e5ff !important;
        border: 2px solid rgba(0, 229, 255, 0.6) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.25) !important;
        font-weight: bold !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.25) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 5px solid #00e5ff !important;
        border-radius: 10px !important;
    }
    
    hr {
        border: 1px solid rgba(0, 229, 255, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

COLORS = {
    'teal': '#1A7A7A',
    'cyan': '#00e5ff',
    'green': '#00ff00',
    'red': '#ff6b6b',
    'yellow': '#ffd93d',
    'dark_bg': '#0a0e27',
    'white': '#ffffff',
    'amber': '#C8760A',
    'atsi': '#ff6b6b',
    'eald': '#ffd93d',
    'swd': '#00e5ff',
    'asd': '#ff9500',
    'adhd': '#9d4edd'
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

def create_demo_data():
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary', 'Hendon PS']
    programs = ['JP', 'PY', 'SY']
    years = [2024, 2025, 2026]
    
    data = []
    for i in range(250):
        if i < 100:
            status = 'Active'
        elif i < 200:
            status = 'Allocated'
        else:
            status = 'On Waiting List'
        
        data.append({
            'Referring_School': random.choice(schools),
            'Allocated_Program': random.choice(programs),
            'Allocation_Status': status,
            'Flag_ATSI': 'Yes' if random.random() < 0.35 else 'No',
            'Flag_EALD': 'Yes' if random.random() < 0.22 else 'No',
            'Flag_SWD': 'Yes' if random.random() < 0.25 else 'No',
            'Flag_ASD': 'Yes' if random.random() < 0.15 else 'No',
            'Flag_ADHD': 'Yes' if random.random() < 0.12 else 'No',
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
    
    return filtered

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_complexity_score(df):
    """Calculate complexity: SWD sub-types + equity groups"""
    df = df.copy()
    flags = ['Flag_ATSI', 'Flag_EALD', 'Flag_SWD']
    df['Complexity_Score'] = df[flags].apply(
        lambda row: sum([1 for f in flags if row[f] == 'Yes']), 
        axis=1
    )
    return df

def add_swd_detail(df):
    """Add SWD sub-type details"""
    df = df.copy()
    swd_types = []
    for idx, row in df.iterrows():
        types = []
        if row.get('Flag_ASD') == 'Yes':
            types.append('ASD')
        if row.get('Flag_ADHD') == 'Yes':
            types.append('ADHD')
        swd_types.append(', '.join(types) if types else 'Other')
    df['SWD_Detail'] = swd_types
    return df

# ============================================================================
# PREVIOUS TABS - EQUITY OVERVIEW
# ============================================================================

def equity_by_program(df):
    """PREVIOUS: Equity distribution by program"""
    programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
    
    data = []
    for prog in programs:
        prog_df = df[df['Allocated_Program'] == prog]
        
        atsi = len(prog_df[prog_df['Flag_ATSI'] == 'Yes'])
        eald = len(prog_df[prog_df['Flag_EALD'] == 'Yes'])
        swd = len(prog_df[prog_df['Flag_SWD'] == 'Yes'])
        
        total = len(prog_df)
        
        data.append({'Program': prog, 'ATSI': atsi/total*100 if total > 0 else 0, 
                     'EALD': eald/total*100 if total > 0 else 0, 
                     'SWD': swd/total*100 if total > 0 else 0})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=data_df['Program'], y=data_df['ATSI'], name='ATSI', marker_color=COLORS['atsi']))
    fig.add_trace(go.Bar(x=data_df['Program'], y=data_df['EALD'], name='EALD', marker_color=COLORS['eald']))
    fig.add_trace(go.Bar(x=data_df['Program'], y=data_df['SWD'], name='SWD (all types)', marker_color=COLORS['swd']))
    
    fig.update_layout(
        title='⚖️ Equity Distribution by Program',
        barmode='group',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

def equity_trend(df):
    """PREVIOUS: Trends over time"""
    years = sorted([y for y in df['Referral_Year'].unique() if y > 0])
    
    data = []
    for year in years:
        year_df = df[df['Referral_Year'] == year]
        total = len(year_df)
        atsi_pct = len(year_df[year_df['Flag_ATSI'] == 'Yes']) / total * 100 if total > 0 else 0
        eald_pct = len(year_df[year_df['Flag_EALD'] == 'Yes']) / total * 100 if total > 0 else 0
        
        data.append({'Year': year, 'ATSI': atsi_pct, 'EALD': eald_pct})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data_df['Year'], y=data_df['ATSI'], name='ATSI', mode='lines+markers', 
                             line=dict(color=COLORS['atsi'], width=3), marker=dict(size=10)))
    fig.add_trace(go.Scatter(x=data_df['Year'], y=data_df['EALD'], name='EALD', mode='lines+markers',
                             line=dict(color=COLORS['eald'], width=3), marker=dict(size=10)))
    
    fig.update_layout(
        title='📈 ATSI & EALD Year Trends',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

# ============================================================================
# NEW TABS - INSIGHTS
# ============================================================================

def swd_breakdown(df):
    """NEW: SWD detail - show ASD, ADHD as sub-types"""
    df = add_swd_detail(df)
    swd_df = df[df['Flag_SWD'] == 'Yes']
    
    # Count ASD only, ADHD only, both, other
    asd_only = len(swd_df[(swd_df['Flag_ASD'] == 'Yes') & (swd_df['Flag_ADHD'] == 'No')])
    adhd_only = len(swd_df[(swd_df['Flag_ADHD'] == 'Yes') & (swd_df['Flag_ASD'] == 'No')])
    both = len(swd_df[(swd_df['Flag_ASD'] == 'Yes') & (swd_df['Flag_ADHD'] == 'Yes')])
    other_swd = len(swd_df) - asd_only - adhd_only - both
    
    labels = ['ASD Only', 'ADHD Only', 'ASD + ADHD', 'Other SWD']
    values = [asd_only, adhd_only, both, other_swd]
    colors = [COLORS['asd'], COLORS['adhd'], '#e636ff', COLORS['swd']]
    
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker=dict(colors=colors))])
    
    fig.update_layout(
        title='🧩 SWD Breakdown: Types of Disability',
        paper_bgcolor=COLORS['dark_bg'],
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

def complexity_analysis(df):
    """NEW: Complexity - ATSI + EALD + SWD combinations"""
    df = add_complexity_score(df)
    
    complexity_counts = df['Complexity_Score'].value_counts().sort_index()
    
    fig = go.Figure(data=[
        go.Bar(
            x=['No Flag', 'One (ATSI/EALD/SWD)', 'Two Flags', 'All Three'],
            y=[complexity_counts.get(i, 0) for i in range(4)],
            marker_color=[COLORS['cyan'], COLORS['yellow'], COLORS['amber'], COLORS['red']],
            text=[complexity_counts.get(i, 0) for i in range(4)],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title='📊 Student Complexity: ATSI + EALD + SWD Combinations',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

def intersectionality(df):
    """NEW: Show ATSI+SWD, EALD+SWD, ATSI+EALD"""
    intersections = [
        ('ATSI + SWD', ('Flag_ATSI', 'Flag_SWD')),
        ('ATSI + EALD', ('Flag_ATSI', 'Flag_EALD')),
        ('EALD + SWD', ('Flag_EALD', 'Flag_SWD')),
        ('All Three', (None, None)),
    ]
    
    data = []
    for label, (flag1, flag2) in intersections:
        if label == 'All Three':
            count = len(df[(df['Flag_ATSI'] == 'Yes') & (df['Flag_EALD'] == 'Yes') & (df['Flag_SWD'] == 'Yes')])
        else:
            count = len(df[(df[flag1] == 'Yes') & (df[flag2] == 'Yes')])
        
        data.append({'Intersection': label, 'Count': count})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure(data=[
        go.Bar(
            y=data_df['Intersection'],
            x=data_df['Count'],
            orientation='h',
            marker_color=[COLORS['red'], COLORS['yellow'], COLORS['cyan'], COLORS['amber']],
            text=data_df['Count'],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title='🔀 Intersectionality: Multiple Equity Groups',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    return fig

# ============================================================================
# COMPARISON ANALYSIS
# ============================================================================

def show_comparison(df):
    """Compare programs and terms flexibly"""
    
    st.markdown("### 🔄 Program & Term Comparison")
    st.info("💡 Select what to compare: multiple programs, multiple terms, or same term across years")
    
    # Control panel
    col1, col2 = st.columns(2)
    
    with col1:
        comparison_type = st.radio("Compare by:", ["Programs", "Terms", "Years (same term)"])
    
    with col2:
        st.write("")  # Spacing
    
    # Get comparison data based on selection
    compare_data = []
    
    if comparison_type == "Programs":
        programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
        selected_progs = st.multiselect("Select programs to compare", programs, default=programs)
        
        col1, col2 = st.columns(2)
        with col1:
            selected_year = st.selectbox("Year", ['All'] + sorted([str(y) for y in df['Referral_Year'].unique() if y > 0]))
        with col2:
            selected_term = st.selectbox("Term", ['All'] + sorted([str(t) for t in df['Term'].unique() if t > 0]))
        
        for prog in selected_progs:
            subset = df[df['Allocated_Program'] == prog]
            if selected_year != 'All':
                subset = subset[subset['Referral_Year'] == int(selected_year)]
            if selected_term != 'All':
                subset = subset[subset['Term'] == int(selected_term)]
            
            compare_data.append({
                'Group': prog,
                'Total': len(subset),
                'Allocated': len(subset[subset['Allocation_Status'] == 'Allocated']),
                'Active': len(subset[subset['Allocation_Status'] == 'Active']),
                'ATSI': len(subset[subset['Flag_ATSI'] == 'Yes']),
                'EALD': len(subset[subset['Flag_EALD'] == 'Yes']),
                'SWD': len(subset[subset['Flag_SWD'] == 'Yes'])
            })
    
    elif comparison_type == "Terms":
        terms = sorted([t for t in df['Term'].unique() if t > 0])
        selected_terms = st.multiselect("Select terms to compare", [str(t) for t in terms], default=[str(t) for t in terms])
        
        col1, col2 = st.columns(2)
        with col1:
            selected_prog = st.selectbox("Program", ['All'] + sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)]))
        with col2:
            selected_year = st.selectbox("Year", ['All'] + sorted([str(y) for y in df['Referral_Year'].unique() if y > 0]))
        
        for term_str in selected_terms:
            term = int(term_str)
            subset = df[df['Term'] == term]
            if selected_prog != 'All':
                subset = subset[subset['Allocated_Program'] == selected_prog]
            if selected_year != 'All':
                subset = subset[subset['Referral_Year'] == int(selected_year)]
            
            compare_data.append({
                'Group': f'Term {term}',
                'Total': len(subset),
                'Allocated': len(subset[subset['Allocation_Status'] == 'Allocated']),
                'Active': len(subset[subset['Allocation_Status'] == 'Active']),
                'ATSI': len(subset[subset['Flag_ATSI'] == 'Yes']),
                'EALD': len(subset[subset['Flag_EALD'] == 'Yes']),
                'SWD': len(subset[subset['Flag_SWD'] == 'Yes'])
            })
    
    else:  # Years (same term)
        years = sorted([y for y in df['Referral_Year'].unique() if y > 0])
        selected_years = st.multiselect("Select years to compare", [str(y) for y in years], default=[str(y) for y in years])
        
        col1, col2 = st.columns(2)
        with col1:
            selected_term = st.selectbox("Term", sorted([str(t) for t in df['Term'].unique() if t > 0]))
        with col2:
            selected_prog = st.selectbox("Program", ['All'] + sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)]))
        
        for year_str in selected_years:
            year = int(year_str)
            subset = df[(df['Referral_Year'] == year) & (df['Term'] == int(selected_term))]
            if selected_prog != 'All':
                subset = subset[subset['Allocated_Program'] == selected_prog]
            
            compare_data.append({
                'Group': str(year),
                'Total': len(subset),
                'Allocated': len(subset[subset['Allocation_Status'] == 'Allocated']),
                'Active': len(subset[subset['Allocation_Status'] == 'Active']),
                'ATSI': len(subset[subset['Flag_ATSI'] == 'Yes']),
                'EALD': len(subset[subset['Flag_EALD'] == 'Yes']),
                'SWD': len(subset[subset['Flag_SWD'] == 'Yes'])
            })
    
    # Display comparison
    if compare_data:
        compare_df = pd.DataFrame(compare_data)
        
        st.markdown("---")
        st.markdown("### 📊 Comparison Results")
        
        # Metrics comparison
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            fig = go.Figure(data=[
                go.Bar(x=compare_df['Group'], y=compare_df['Total'], marker_color=COLORS['cyan'],
                       text=compare_df['Total'], textposition='outside')
            ])
            fig.update_layout(title='Total Students', paper_bgcolor=COLORS['dark_bg'], 
                            plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white']), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = go.Figure(data=[
                go.Bar(x=compare_df['Group'], y=compare_df['Allocated'], marker_color=COLORS['green'],
                       text=compare_df['Allocated'], textposition='outside')
            ])
            fig.update_layout(title='Allocated Students', paper_bgcolor=COLORS['dark_bg'],
                            plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white']), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            fig = go.Figure(data=[
                go.Bar(x=compare_df['Group'], y=compare_df['Active'], marker_color=COLORS['amber'],
                       text=compare_df['Active'], textposition='outside')
            ])
            fig.update_layout(title='Active Students', paper_bgcolor=COLORS['dark_bg'],
                            plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white']), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            allocation_rate = (compare_df['Allocated'] / compare_df['Total'] * 100).round(0).astype(int)
            fig = go.Figure(data=[
                go.Bar(x=compare_df['Group'], y=allocation_rate, marker_color=COLORS['yellow'],
                       text=[f"{rate}%" for rate in allocation_rate], textposition='outside')
            ])
            fig.update_layout(title='Allocation Rate %', paper_bgcolor=COLORS['dark_bg'],
                            plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white']), 
                            yaxis=dict(range=[0, 100]), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # Equity comparison
        st.markdown("---")
        st.markdown("### ⚖️ Equity Distribution")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig = go.Figure(data=[
                go.Bar(x=compare_df['Group'], y=compare_df['ATSI'], marker_color=COLORS['atsi'],
                       text=compare_df['ATSI'], textposition='outside')
            ])
            fig.update_layout(title='🇦🇺 ATSI Students', paper_bgcolor=COLORS['dark_bg'],
                            plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white']), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = go.Figure(data=[
                go.Bar(x=compare_df['Group'], y=compare_df['EALD'], marker_color=COLORS['eald'],
                       text=compare_df['EALD'], textposition='outside')
            ])
            fig.update_layout(title='🌍 EALD Students', paper_bgcolor=COLORS['dark_bg'],
                            plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white']), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            fig = go.Figure(data=[
                go.Bar(x=compare_df['Group'], y=compare_df['SWD'], marker_color=COLORS['swd'],
                       text=compare_df['SWD'], textposition='outside')
            ])
            fig.update_layout(title='♿ SWD Students', paper_bgcolor=COLORS['dark_bg'],
                            plot_bgcolor='rgba(0,0,0,0)', font=dict(color=COLORS['white']), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # Data table
        st.markdown("---")
        st.markdown("### 📋 Comparison Table")
        st.dataframe(compare_df, use_container_width=True)

def main():
    if not st.session_state['data_loaded']:
        default = load_data()
        if default is not None:
            st.session_state['df'] = default
            st.session_state['data_loaded'] = True
    
    df = st.session_state['df']
    
    st.markdown("# 📊 CLC-LBU STRATEGIC ANALYTICS")
    st.markdown("_Equity groups: ATSI | EALD | SWD (includes ASD, ADHD, other disabilities)_")
    
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
    
    with col2:
        if st.button("📥 Load Demo"):
            st.session_state['df'] = create_demo_data()
            st.session_state['data_loaded'] = True
            st.rerun()
    
    if df is None:
        st.info("👆 Upload or load demo")
        return
    
    # FILTERS
    st.markdown("## 🔍 Filters")
    
    filter_cols = st.columns(4)
    
    with filter_cols[0]:
        years = sorted([y for y in df['Referral_Year'].unique() if y > 0])
        st.session_state['selected_year'] = st.selectbox("📆 Year", ['All'] + [str(y) for y in years], index=0)
    
    with filter_cols[1]:
        terms = sorted([t for t in df['Term'].unique() if t > 0])
        st.session_state['selected_term'] = st.selectbox("📅 Term", ['All'] + [str(t) for t in terms], index=0)
    
    with filter_cols[2]:
        programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
        st.session_state['selected_program'] = st.selectbox("🎓 Program", ['All'] + programs, index=0)
    
    with filter_cols[3]:
        if st.button("🔄 Reset"):
            st.session_state['selected_year'] = 'All'
            st.session_state['selected_term'] = 'All'
            st.session_state['selected_program'] = 'All'
            st.rerun()
    
    filtered_df = apply_filters(df)
    
    st.markdown("---")
    
    # KEY METRICS
    st.markdown("## 📈 Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📋 Total", len(filtered_df))
    col2.metric("✅ Active", len(filtered_df[filtered_df['Allocation_Status'] == 'Active']))
    
    atsi_count = len(filtered_df[filtered_df['Flag_ATSI'] == 'Yes'])
    col3.metric("🇦🇺 ATSI", f"{atsi_count} ({atsi_count/len(filtered_df)*100 if len(filtered_df) > 0 else 0:.0f}%)")
    
    eald_count = len(filtered_df[filtered_df['Flag_EALD'] == 'Yes'])
    col4.metric("🌍 EALD", f"{eald_count} ({eald_count/len(filtered_df)*100 if len(filtered_df) > 0 else 0:.0f}%)")
    
    swd_count = len(filtered_df[filtered_df['Flag_SWD'] == 'Yes'])
    col5.metric("♿ SWD", f"{swd_count} ({swd_count/len(filtered_df)*100 if len(filtered_df) > 0 else 0:.0f}%)")
    
    st.markdown("---")
    
    # ALL TABS
    st.markdown("## 📊 Analysis")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "⚖️ Equity by Program",
        "📈 Trends",
        "🧩 SWD Types",
        "📊 Complexity",
        "🔀 Intersectionality",
        "🔄 Compare Programs/Terms",
        "📋 Raw Data",
        "ℹ️ Key Insights"
    ])
    
    with tab1:
        fig = equity_by_program(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = equity_trend(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### SWD Sub-Types: ASD, ADHD, Other Disabilities")
        st.info("💡 Of students with SWD flag, what are the specific disability types?")
        fig = swd_breakdown(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.markdown("### Student Complexity: Multiple Equity Flags")
        st.info("💡 Students with ATSI + EALD + SWD = highest complexity")
        fig = complexity_analysis(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.markdown("### Intersecting Equity Groups")
        st.info("💡 Students at intersection of multiple equity concerns")
        fig = intersectionality(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab6:
        st.markdown("### De-identified Raw Data")
        cols_show = [c for c in ['Referring_School', 'Allocated_Program', 'Allocation_Status', 
                                  'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Flag_ADHD', 'Referral_Year', 'Term'] 
                     if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_show], use_container_width=True, height=500)
    
    with tab7:
        st.markdown("### 💡 Key Strategic Insights")
        st.markdown("""
        **Three Separate Equity Groups:**
        - 🇦🇺 **ATSI** (Aboriginal/Torres Strait Islander)
        - 🌍 **EALD** (English as Additional Language or Dialect)
        - ♿ **SWD** (Students with Disabilities) - *umbrella category*
        
        **Under SWD:**
        - 🧩 ASD (Autism Spectrum Disorder)
        - 🟣 ADHD (Attention Deficit/Hyperactivity Disorder)
        - Other disabilities (intellectual, physical, sensory, etc.)
        
        **Why This Matters:**
        - Students can have ATSI status AND be in SWD
        - Students can be EALD AND have ASD
        - Some students are at ALL THREE intersections
        - Complexity increases support needs exponentially
        """)

if __name__ == "__main__":
    main()
