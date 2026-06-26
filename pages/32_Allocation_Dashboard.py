"""
CLC-LBU STRATEGIC ANALYTICS - COMPREHENSIVE INSIGHTS
Comorbidity, Intersectionality, Complexity, Retention, School Concentration
Raw data hidden in separate tab
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import random
from datetime import datetime

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
    
    p, span, label, .stText {
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
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.15) !important;
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
    schools = ['Le Fevre HS', 'Warradale Primary', 'Woodville HS', 'Brighton Secondary', 'Hendon PS', 'Cowandilla PS']
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
    
    return filtered

# ============================================================================
# ADVANCED ANALYTICS
# ============================================================================

def add_complexity_score(df):
    """Calculate complexity: number of diagnoses per student"""
    flags = ['Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD']
    df['Complexity_Score'] = df[flags].apply(
        lambda row: sum([1 for f in flags if row[f] == 'Yes']), 
        axis=1
    )
    return df

def comorbidity_analysis(df):
    """Analyze students with multiple diagnoses"""
    df = add_complexity_score(df)
    
    # Count by complexity
    complexity_counts = df['Complexity_Score'].value_counts().sort_index()
    
    fig = go.Figure(data=[
        go.Bar(
            x=['No Flags', '1 Diagnosis', '2 Diagnoses', '3 Diagnoses', '4 Diagnoses'],
            y=[complexity_counts.get(i, 0) for i in range(5)],
            marker_color=['#00e5ff', '#ffd93d', '#ff9500', '#ff6b6b', '#ff4444'],
            text=[complexity_counts.get(i, 0) for i in range(5)],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Students: %{y}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='📊 Student Complexity: Multiple Diagnoses',
        xaxis_title='Number of Diagnoses',
        yaxis_title='Number of Students',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    
    return fig, df

def intersectionality_analysis(df):
    """Analyze intersecting identities (ATSI + ASD, EALD + SWD, etc.)"""
    
    intersections = [
        ('ATSI + ASD', ('Flag_ATSI', 'Flag_ASD')),
        ('ATSI + SWD', ('Flag_ATSI', 'Flag_SWD')),
        ('ATSI + EALD', ('Flag_ATSI', 'Flag_EALD')),
        ('EALD + SWD', ('Flag_EALD', 'Flag_SWD')),
        ('EALD + ASD', ('Flag_EALD', 'Flag_ASD')),
        ('SWD + ASD', ('Flag_SWD', 'Flag_ASD')),
    ]
    
    data = []
    for label, (flag1, flag2) in intersections:
        count = len(df[(df[flag1] == 'Yes') & (df[flag2] == 'Yes')])
        total = len(df)
        pct = (count / total * 100) if total > 0 else 0
        data.append({'Intersection': label, 'Count': count, 'Percentage': pct})
    
    data_df = pd.DataFrame(data)
    
    fig = go.Figure(data=[
        go.Bar(
            y=data_df['Intersection'],
            x=data_df['Count'],
            orientation='h',
            marker_color=COLORS['amber'],
            text=data_df['Count'],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Students: %{x}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='🔀 Intersectionality: Students with Multiple Identities',
        xaxis_title='Number of Students',
        yaxis_title='Identity Intersections',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    
    return fig

def school_needs_concentration(df):
    """Which schools have students with highest complexity"""
    df = add_complexity_score(df)
    
    school_stats = []
    for school in df['Referring_School'].unique():
        school_df = df[df['Referring_School'] == school]
        avg_complexity = school_df['Complexity_Score'].mean()
        total_students = len(school_df)
        multi_diagnosis = len(school_df[school_df['Complexity_Score'] > 1])
        
        school_stats.append({
            'School': school,
            'Avg_Complexity': avg_complexity,
            'Total_Students': total_students,
            'Multi_Diagnosis': multi_diagnosis
        })
    
    school_df = pd.DataFrame(school_stats).sort_values('Avg_Complexity', ascending=True)
    
    fig = go.Figure(data=[
        go.Bar(
            y=school_df['School'],
            x=school_df['Avg_Complexity'],
            orientation='h',
            marker_color=COLORS['red'],
            text=[f"{c:.2f}" for c in school_df['Avg_Complexity']],
            textposition='outside',
            customdata=school_df['Multi_Diagnosis'],
            hovertemplate='<b>%{y}</b><br>Avg Complexity: %{x:.2f}<br>Multi-Diagnosis: %{customdata}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='🏥 School Needs Concentration: Average Student Complexity',
        xaxis_title='Average Complexity Score',
        yaxis_title='School',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    
    return fig

def retention_analysis(df):
    """Students returning/staying vs leaving"""
    df = add_complexity_score(df)
    
    # Count by status and complexity
    status_complexity = []
    for status in df['Allocation_Status'].unique():
        status_df = df[df['Allocation_Status'] == status]
        avg_complexity = status_df['Complexity_Score'].mean()
        count = len(status_df)
        status_complexity.append({'Status': status, 'Complexity': avg_complexity, 'Count': count})
    
    status_df = pd.DataFrame(status_complexity)
    
    fig = go.Figure(data=[
        go.Bar(
            x=status_df['Status'],
            y=status_df['Complexity'],
            marker_color=[COLORS['green'], COLORS['red'], COLORS['cyan']],
            text=[f"{c:.2f}" for c in status_df['Complexity']],
            textposition='outside',
            customdata=status_df['Count'],
            hovertemplate='<b>%{x}</b><br>Avg Complexity: %{y:.2f}<br>Count: %{customdata}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='🔄 Allocation Status by Student Complexity',
        xaxis_title='Allocation Status',
        yaxis_title='Average Complexity Score',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400
    )
    
    return fig

def program_complexity_distribution(df):
    """How programs distribute complex students"""
    df = add_complexity_score(df)
    
    programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
    
    data = []
    for prog in programs:
        prog_df = df[df['Allocated_Program'] == prog]
        for complexity in range(5):
            count = len(prog_df[prog_df['Complexity_Score'] == complexity])
            if count > 0:
                data.append({
                    'Program': prog,
                    'Complexity': f"{complexity} Diagnoses",
                    'Count': count
                })
    
    data_df = pd.DataFrame(data)
    
    fig = px.bar(
        data_df,
        x='Program',
        y='Count',
        color='Complexity',
        barmode='stack',
        color_discrete_sequence=['#00e5ff', '#ffd93d', '#ff9500', '#ff6b6b', '#ff4444']
    )
    
    fig.update_layout(
        title='📚 Program Distribution: Student Complexity Levels',
        xaxis_title='Program',
        yaxis_title='Number of Students',
        paper_bgcolor=COLORS['dark_bg'],
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['white']),
        height=400,
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
    
    st.markdown("# 📊 CLC-LBU COMPREHENSIVE INSIGHTS")
    st.markdown("_Comorbidity, Intersectionality, Complexity & Concentration_")
    
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
    col1.metric("📋 Total Students", len(filtered_df))
    col2.metric("✅ Active", len(filtered_df[filtered_df['Allocation_Status'] == 'Active']))
    
    atsi_count = len(filtered_df[filtered_df['Flag_ATSI'] == 'Yes'])
    col3.metric("🇦🇺 ATSI", f"{atsi_count} ({atsi_count/len(filtered_df)*100 if len(filtered_df) > 0 else 0:.0f}%)")
    
    multi_flag_count = len(filtered_df[filtered_df[[c for c in filtered_df.columns if c.startswith('Flag_')]].apply(lambda row: (row == 'Yes').sum() > 1, axis=1)])
    col4.metric("🔀 Multi-Diagnosis", f"{multi_flag_count} ({multi_flag_count/len(filtered_df)*100 if len(filtered_df) > 0 else 0:.0f}%)")
    
    high_complexity = len(filtered_df[filtered_df[[c for c in filtered_df.columns if c.startswith('Flag_')]].apply(lambda row: (row == 'Yes').sum() >= 3, axis=1)])
    col5.metric("⚠️ High Complexity", f"{high_complexity}")
    
    st.markdown("---")
    
    # TABS
    st.markdown("## 📊 Analysis")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Complexity",
        "🔀 Intersectionality",
        "🏥 School Concentration",
        "🔄 Status & Complexity",
        "📚 Program Distribution",
        "📋 Raw Data"
    ])
    
    with tab1:
        st.markdown("### Student Complexity: Multiple Diagnoses")
        st.info("💡 How many diagnoses/flags does each student have? More = higher support needs")
        fig, _ = comorbidity_analysis(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown("### Intersecting Identities")
        st.info("💡 Students who belong to multiple equity groups - understanding layered needs")
        fig = intersectionality_analysis(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### Which Schools Refer Students with Greatest Complexity?")
        st.info("💡 Socioeconomic & need concentration - which schools need most support")
        fig = school_needs_concentration(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.markdown("### Student Complexity by Allocation Status")
        st.info("💡 Are more complex students allocated? Retained? Waiting?")
        fig = retention_analysis(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.markdown("### How Programs Handle Different Complexity Levels")
        st.info("💡 Which program serves students with highest complexity? Is it spread evenly?")
        fig = program_complexity_distribution(filtered_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab6:
        st.markdown("### De-identified Raw Data")
        cols_show = [c for c in ['Referring_School', 'Allocated_Program', 'Allocation_Status', 
                                  'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Referral_Year', 'Term'] 
                     if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_show], use_container_width=True, height=500)

if __name__ == "__main__":
    main()
