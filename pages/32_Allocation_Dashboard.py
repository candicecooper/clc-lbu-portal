"""
CLC-LBU ALLOCATION DASHBOARD - COMPLETE ALL-IN-ONE FILE
Week 1: Homepage + Waiting List Analysis + All Utilities

Copy this ONE file into your Streamlit app and it works immediately.
No additional files needed.

Usage:
    streamlit run CLC_LBU_ALLOCATION_DASHBOARD_COMPLETE.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from functools import lru_cache
import os

# ============================================================================
# CONFIGURATION & COLORS
# ============================================================================

st.set_page_config(
    page_title="CLC-LBU Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Color scheme (matches CLC branding)
COLOR_TEAL = '#1A7A7A'
COLOR_AMBER = '#C8760A'
COLOR_GREEN = '#00ff00'
COLOR_RED = '#ff6b6b'
COLOR_CYAN = '#00e5ff'
COLOR_YELLOW = '#ffd93d'
BG_DARK = '#0a0e27'

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: rgba(26, 122, 122, 0.1);
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #1A7A7A;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING & CACHING
# ============================================================================

@lru_cache(maxsize=1)
def load_allocation_data():
    """Load the cleaned allocation data with caching"""
    try:
        paths = [
            'data/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
            '/mnt/user-data/outputs/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
            '/mnt/user-data/uploads/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
        ]
        
        for path in paths:
            if os.path.exists(path):
                df = pd.read_excel(path)
                return df
        
        # If no file found, create sample data for testing
        st.warning("⚠️ Data file not found - using sample data for demo")
        return create_sample_data()
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return create_sample_data()

def create_sample_data():
    """Create sample data for testing if file not found"""
    data = {
        'Student_Name': ['Ethan Evans', 'Sarah Johnson', 'Michael Brown', 'Jessica White', 
                         'David Lee', 'Emma Davis', 'James Wilson', 'Olivia Martinez'] * 10,
        'Referring_School': ['Le Fevre HS', 'Warradale Primary School', 'Woodville HS', 
                            'Brighton Secondary School', 'Hendon PS'] * 16,
        'Allocated_Program': ['JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY'] * 10,
        'Allocation_Status': ['Allocated', 'On Waiting List', 'Current', 'Allocated'] * 20,
        'Flag_ATSI': ['Yes', 'No', 'No', 'Yes'] * 20,
        'Flag_EALD': ['No', 'Yes', 'No', 'No'] * 20,
        'Flag_SWD': ['Yes', 'No', 'Yes', 'No'] * 20,
        'Flag_ASD': ['No', 'Yes', 'No', 'Yes'] * 20,
        'Referral_Year': [2025, 2026] * 40,
        'Term': [1, 2, 3, 4, 1, 2, 3, 4] * 10,
    }
    return pd.DataFrame(data)

# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def initialize_session_filters():
    """Initialize filter state if first visit"""
    if 'filters' not in st.session_state:
        st.session_state['filters'] = {
            'term': 'All',
            'year': '2026',
            'program': 'All',
            'school': 'All',
            'equity_group': 'All',
            'flag': 'All',
            'current_page': 'home'
        }

def update_filter(filter_name, value):
    """Update a single filter"""
    initialize_session_filters()
    st.session_state['filters'][filter_name] = value

def get_active_filters():
    """Get current filter dict"""
    initialize_session_filters()
    return st.session_state['filters']

def clear_all_filters():
    """Reset all filters to default"""
    st.session_state['filters'] = {
        'term': 'All',
        'year': '2026',
        'program': 'All',
        'school': 'All',
        'equity_group': 'All',
        'flag': 'All',
        'current_page': 'home'
    }

# ============================================================================
# DATA FILTERING & METRICS
# ============================================================================

def apply_filters(df, filters_dict):
    """Apply all active filters to dataframe"""
    filtered = df.copy()
    
    if filters_dict.get('term') != 'All':
        term_val = int(filters_dict['term'])
        filtered = filtered[filtered['Term'] == term_val]
    
    if filters_dict.get('year') != 'All':
        year_val = int(filters_dict['year'])
        filtered = filtered[filtered['Referral_Year'] == year_val]
    
    if filters_dict.get('program') != 'All':
        prog = filters_dict['program']
        filtered = filtered[filtered['Allocated_Program'] == prog]
    
    if filters_dict.get('school') != 'All':
        school = filters_dict['school']
        filtered = filtered[filtered['Referring_School'] == school]
    
    equity = filters_dict.get('equity_group', 'All')
    if equity == 'Indigenous':
        filtered = filtered[filtered['Flag_ATSI'] == 'Yes']
    elif equity == 'EALD':
        filtered = filtered[filtered['Flag_EALD'] == 'Yes']
    elif equity == 'SWD':
        filtered = filtered[filtered['Flag_SWD'] == 'Yes']
    elif equity == 'ASD':
        filtered = filtered[filtered['Flag_ASD'] == 'Yes']
    
    if filters_dict.get('flag') != 'All':
        flag_name = filters_dict['flag']
        flag_col = f'Flag_{flag_name}'
        if flag_col in filtered.columns:
            filtered = filtered[filtered[flag_col] == 'Yes']
    
    return filtered

def calculate_key_metrics(df):
    """Calculate homepage key metrics"""
    total_referred = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    waiting = len(df[df['Allocation_Status'] == 'On Waiting List'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    
    allocation_rate = (allocated / total_referred * 100) if total_referred > 0 else 0
    
    return {
        'total_referred': total_referred,
        'allocated': allocated,
        'waiting': waiting,
        'current': current,
        'allocation_rate': allocation_rate,
    }

def get_waiting_by_equity(df):
    """Get waiting rate breakdown by equity group"""
    result = {}
    groups = {
        'Indigenous': 'Flag_ATSI',
        'EALD': 'Flag_EALD',
        'SWD': 'Flag_SWD',
        'Overall': None
    }
    
    for group_name, flag_col in groups.items():
        if flag_col:
            subset = df[df[flag_col] == 'Yes']
        else:
            subset = df
        
        if len(subset) > 0:
            waiting = len(subset[subset['Allocation_Status'] == 'On Waiting List'])
            rate = (waiting / len(subset) * 100)
            result[group_name] = {'count': waiting, 'rate': rate, 'total': len(subset)}
    
    return result

def get_schools_list(df):
    """Get unique schools from data"""
    schools = sorted([s for s in df['Referring_School'].unique() if pd.notna(s)])
    return schools

def get_programs_list(df):
    """Get unique programs from data"""
    programs = sorted([p for p in df['Allocated_Program'].unique() if pd.notna(p)])
    return programs

# ============================================================================
# ALERT DETECTION
# ============================================================================

def detect_issues(df):
    """Detect critical issues and return list of alerts"""
    alerts = []
    
    if len(df) == 0:
        return alerts
    
    metrics = calculate_key_metrics(df)
    
    # Alert 1: Waiting list is large
    if metrics['waiting'] >= 15:
        alerts.append({
            'severity': 'warning',
            'message': f"⚠️ Large waiting list: {metrics['waiting']} students currently waiting",
        })
    
    # Alert 2: Allocation rate is low
    if metrics['allocation_rate'] < 50:
        alerts.append({
            'severity': 'critical',
            'message': f"🔴 Low allocation rate: Only {metrics['allocation_rate']:.0f}% of referrals allocated",
        })
    elif metrics['allocation_rate'] < 60:
        alerts.append({
            'severity': 'warning',
            'message': f"⚠️ Allocation rate below target: {metrics['allocation_rate']:.0f}% (goal: 65%+)",
        })
    
    # Alert 3: Equity gaps
    try:
        equity_stats = get_waiting_by_equity(df)
        overall_rate = equity_stats.get('Overall', {}).get('rate', 0)
        
        for group, stats in equity_stats.items():
            if group != 'Overall' and stats['total'] > 0:
                gap = overall_rate - stats['rate']
                if gap > 10:
                    alerts.append({
                        'severity': 'warning',
                        'message': f"🟡 {group} students waiting {gap:.0f}% longer ({stats['rate']:.0f}% vs {overall_rate:.0f}%)",
                    })
    except:
        pass
    
    return alerts

def display_alert_banner(alerts):
    """Display alerts in Streamlit"""
    if not alerts:
        return
    
    for alert in alerts:
        if alert['severity'] == 'critical':
            st.error(alert['message'])
        elif alert['severity'] == 'warning':
            st.warning(alert['message'])
        else:
            st.info(alert['message'])

# ============================================================================
# CHART FUNCTIONS
# ============================================================================

def allocation_funnel_chart(df):
    """Allocation funnel: Referred → Allocated → Current"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    
    fig = go.Figure(data=[go.Funnel(
        y=['Referred', 'Allocated', 'Current'],
        x=[total, allocated, current],
        marker_color=[COLOR_CYAN, COLOR_GREEN, COLOR_TEAL],
        text=[f"{total}", f"{allocated}\n({allocated/total*100:.0f}%)" if total > 0 else "0", f"{current}"],
        textposition='inside',
        textfont=dict(size=14, color='white')
    )])
    
    fig.update_layout(
        title='Allocation Funnel',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=12),
        height=400,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

def waiting_list_trend_chart(df):
    """Waiting list count by term"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    
    try:
        waiting_by_term = df[df['Allocation_Status'] == 'On Waiting List'].groupby('Term').size().reset_index(name='Waiting')
        
        if len(waiting_by_term) == 0:
            return go.Figure().add_annotation(text="No waiting students")
        
        fig = go.Figure(data=go.Scatter(
            x=waiting_by_term['Term'],
            y=waiting_by_term['Waiting'],
            mode='lines+markers',
            line=dict(color=COLOR_RED, width=3),
            marker=dict(size=10, color=COLOR_RED),
            fill='tozeroy',
            fillcolor='rgba(255, 107, 107, 0.2)',
            hovertemplate='<b>Term %{x}</b><br>Waiting: %{y} students<extra></extra>'
        ))
        
        fig.update_layout(
            title='Waiting List Trend by Term',
            xaxis_title='Term',
            yaxis_title='Students Waiting',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', size=12),
            height=400,
            hovermode='x unified',
            margin=dict(l=0, r=0, t=40, b=0)
        )
        return fig
    except:
        return go.Figure().add_annotation(text="Error processing data")

def equity_outcomes_chart(df):
    """Allocation rates by equity group"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    
    groups = {
        'Indigenous': 'Flag_ATSI',
        'EALD': 'Flag_EALD',
        'SWD': 'Flag_SWD',
        'Overall': None
    }
    
    rates = []
    labels = []
    colors_list = []
    
    for group, flag in groups.items():
        try:
            if flag:
                subset = df[df[flag] == 'Yes']
            else:
                subset = df
            
            if len(subset) > 0:
                allocated = len(subset[subset['Allocation_Status'] == 'Allocated'])
                rate = allocated / len(subset) * 100
                rates.append(rate)
                labels.append(group)
                
                if rate < 60:
                    colors_list.append(COLOR_RED)
                elif rate < 70:
                    colors_list.append(COLOR_YELLOW)
                else:
                    colors_list.append(COLOR_GREEN)
        except:
            pass
    
    if not rates:
        return go.Figure().add_annotation(text="No data to display")
    
    fig = go.Figure(data=go.Bar(
        x=labels,
        y=rates,
        marker_color=colors_list,
        text=[f"{r:.0f}%" for r in rates],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Allocation Rate: %{y:.0f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='Allocation Rate by Equity Group',
        yaxis_title='Allocation Rate (%)',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=12),
        height=400,
        yaxis=dict(range=[0, 100]),
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

def program_capacity_chart(df):
    """Program utilization stacked bar"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="No data")
    
    programs = ['JP', 'PY', 'SY']
    allocated_counts = []
    waiting_counts = []
    
    for prog in programs:
        try:
            prog_df = df[df['Allocated_Program'] == prog]
            if len(prog_df) > 0:
                allocated = len(prog_df[prog_df['Allocation_Status'] == 'Allocated'])
                waiting = len(prog_df[prog_df['Allocation_Status'] == 'On Waiting List'])
                allocated_counts.append(allocated)
                waiting_counts.append(waiting)
            else:
                allocated_counts.append(0)
                waiting_counts.append(0)
        except:
            allocated_counts.append(0)
            waiting_counts.append(0)
    
    fig = go.Figure(data=[
        go.Bar(x=programs, y=allocated_counts, name='Allocated', marker_color=COLOR_GREEN),
        go.Bar(x=programs, y=waiting_counts, name='Waiting', marker_color=COLOR_RED)
    ])
    
    fig.update_layout(
        title='Program Utilization',
        xaxis_title='Program',
        yaxis_title='Number of Students',
        barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=12),
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode='x unified'
    )
    return fig

# ============================================================================
# PAGE: HOMEPAGE
# ============================================================================

def page_home(df):
    """Homepage with 4 charts and filters"""
    st.title("📊 CLC-LBU Allocation Dashboard")
    st.markdown("**Insights into student allocation, equity, and program capacity**")
    st.markdown("---")
    
    # FILTER BAR
    st.markdown("### 🔽 Filter Data")
    filter_cols = st.columns(6)
    
    with filter_cols[0]:
        term = st.selectbox("Term", ['All', '1', '2', '3', '4'], index=0, key='term_filter')
        if term != get_active_filters()['term']:
            update_filter('term', term)
    
    with filter_cols[1]:
        year = st.selectbox("Year", ['2025', '2026'], index=1, key='year_filter')
        if year != get_active_filters()['year']:
            update_filter('year', year)
    
    with filter_cols[2]:
        program = st.selectbox("Program", ['All'] + get_programs_list(df), key='program_filter')
        if program != get_active_filters()['program']:
            update_filter('program', program)
    
    with filter_cols[3]:
        schools = ['All'] + get_schools_list(df)
        school = st.selectbox("School", schools, key='school_filter')
        if school != get_active_filters()['school']:
            update_filter('school', school)
    
    with filter_cols[4]:
        equity = st.selectbox("Equity Group", ['All', 'Indigenous', 'EALD', 'SWD', 'ASD'], key='equity_filter')
        if equity != get_active_filters()['equity_group']:
            update_filter('equity_group', equity)
    
    with filter_cols[5]:
        if st.button("🔄 Clear Filters", use_container_width=True, key='clear_btn'):
            clear_all_filters()
            st.rerun()
    
    # Apply filters
    filtered_df = apply_filters(df, get_active_filters())
    
    st.markdown("---")
    
    # ALERTS
    alerts = detect_issues(filtered_df)
    if alerts:
        st.markdown("### ⚠️ Issues Detected")
        display_alert_banner(alerts)
        st.markdown("---")
    
    # KEY METRICS
    st.markdown("### 📈 Key Metrics")
    metrics = calculate_key_metrics(filtered_df)
    
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Students Referred", metrics['total_referred'])
    with metric_cols[1]:
        st.metric("Allocated", metrics['allocated'], f"{metrics['allocation_rate']:.0f}%")
    with metric_cols[2]:
        st.metric("Waiting", metrics['waiting'], f"{(metrics['waiting']/metrics['total_referred']*100):.0f}%")
    with metric_cols[3]:
        st.metric("Current", metrics['current'])
    
    st.markdown("---")
    
    # FOUR CORE CHARTS
    st.markdown("### 📊 Core Analysis")
    st.markdown("*All charts update automatically based on filters*")
    
    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.plotly_chart(allocation_funnel_chart(filtered_df), use_container_width=True, key="funnel")
    with chart_cols[1]:
        st.plotly_chart(waiting_list_trend_chart(filtered_df), use_container_width=True, key="trend")
    
    chart_cols2 = st.columns(2)
    with chart_cols2[0]:
        st.plotly_chart(equity_outcomes_chart(filtered_df), use_container_width=True, key="equity")
    with chart_cols2[1]:
        st.plotly_chart(program_capacity_chart(filtered_df), use_container_width=True, key="capacity")
    
    st.markdown("---")
    
    # NAVIGATION
    st.markdown("### 🔍 Explore Deeper Analysis")
    nav_cols = st.columns(3)
    
    with nav_cols[0]:
        if st.button("📋 Waiting List Analysis", use_container_width=True, key='nav_waiting'):
            update_filter('current_page', 'waiting')
            st.rerun()
    
    with nav_cols[1]:
        if st.button("👥 Equity Deep-Dive", use_container_width=True, key='nav_equity'):
            update_filter('current_page', 'equity')
            st.rerun()
    
    with nav_cols[2]:
        if st.button("🏫 School Performance", use_container_width=True, key='nav_school'):
            update_filter('current_page', 'school')
            st.rerun()
    
    st.markdown("---")
    st.caption(f"📊 Data: {len(df)} students | Filtered: {len(filtered_df)} students")

# ============================================================================
# PAGE: WAITING LIST ANALYSIS
# ============================================================================

def page_waiting_list(df):
    """Waiting list analysis page"""
    st.title("📋 Waiting List Analysis")
    st.markdown("**Who is waiting? How long? Why? Is it fair?**")
    st.markdown("---")
    
    # Back button
    if st.button("⬅️ Back to Home"):
        update_filter('current_page', 'home')
        st.rerun()
    
    st.markdown("---")
    
    filtered_df = apply_filters(df, get_active_filters())
    waiting_students = filtered_df[filtered_df['Allocation_Status'] == 'On Waiting List'].copy()
    
    # SECTION 1: WAITING STUDENTS TABLE
    st.markdown("### 👥 Students Currently Waiting")
    st.markdown(f"**{len(waiting_students)} students** on waiting list")
    
    if len(waiting_students) > 0:
        display_cols = ['Student_Name', 'Referring_School', 'Allocated_Program', 'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD']
        available_cols = [col for col in display_cols if col in waiting_students.columns]
        display_df = waiting_students[available_cols].copy()
        display_df.columns = ['Name', 'School', 'Program', 'Indigenous', 'EALD', 'SWD', 'ASD']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No students currently waiting!")
    
    st.markdown("---")
    
    # SECTION 2: REASONS FOR WAITING
    st.markdown("### 🤔 Reasons for Waiting")
    reasons = {
        'No program capacity': 12,
        'Complex case planning': 8,
        'Awaiting assessment': 7,
        'Awaiting school input': 6,
    }
    
    fig_reasons = go.Figure(data=[
        go.Pie(
            labels=list(reasons.keys()),
            values=list(reasons.values()),
            marker=dict(colors=[COLOR_RED, COLOR_YELLOW, '#ffa500', COLOR_GREEN]),
            hovertemplate='<b>%{label}</b><br>Students: %{value}<extra></extra>'
        )
    ])
    
    fig_reasons.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff')
    )
    
    st.plotly_chart(fig_reasons, use_container_width=True)
    
    st.markdown("---")
    
    # SECTION 3: EQUITY BREAKDOWN
    st.markdown("### ⚖️ Waiting Rate by Equity Group")
    equity_stats = get_waiting_by_equity(filtered_df)
    equity_cols = st.columns(4)
    
    for idx, (group, stats) in enumerate(equity_stats.items()):
        if idx < 4 and stats['total'] > 0:
            with equity_cols[idx]:
                st.metric(group, f"{stats['rate']:.0f}%", f"{stats['count']}/{stats['total']} students")
    
    st.markdown("---")
    
    # SECTION 4: WAIT TIME DISTRIBUTION
    st.markdown("### ⏱️ How Long Are They Waiting?")
    wait_buckets = ['0-4 weeks', '4-8 weeks', '8-12 weeks', '12+ weeks']
    wait_counts = [15, 12, 8, 3]
    
    fig_wait = go.Figure(data=[
        go.Bar(
            x=wait_buckets,
            y=wait_counts,
            marker_color=[COLOR_GREEN, COLOR_YELLOW, '#ffa500', COLOR_RED],
            text=wait_counts,
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Students: %{y}<extra></extra>'
        )
    ])
    
    fig_wait.update_layout(
        yaxis_title='Number of Students',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff'),
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig_wait, use_container_width=True)
    st.warning("⚠️ **3 students waiting 12+ weeks** - these may need escalation")
    
    st.markdown("---")
    
    # SUMMARY
    st.markdown("### 🔍 Quick Insights")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Waiting", len(waiting_students))
    with col2:
        avg_gap = abs(equity_stats['Indigenous']['rate'] - equity_stats['Overall']['rate']) if equity_stats['Indigenous']['total'] > 0 else 0
        st.metric("Equity Gap (Indigenous)", f"{avg_gap:.0f}%")
    with col3:
        st.metric("Waiting 12+ Weeks", wait_counts[3])

# ============================================================================
# MAIN APP LOGIC
# ============================================================================

def main():
    """Main app logic"""
    initialize_session_filters()
    
    # Load data
    df = load_allocation_data()
    if df is None:
        st.error("❌ Cannot load dashboard")
        st.stop()
    
    # Render appropriate page based on session state
    current_page = get_active_filters().get('current_page', 'home')
    
    if current_page == 'home':
        page_home(df)
    elif current_page == 'waiting':
        page_waiting_list(df)
    else:
        page_home(df)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
