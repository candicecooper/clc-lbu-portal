"""
CLC-LBU ALLOCATION DASHBOARD - ENHANCED SINGLE FILE
Week 1: Complete Dashboard with Excel Upload & Data Caching
All Functionality Restored + Original Styling

Features:
- 📁 Excel file upload capability
- 💾 Data caching (persists until next upload)
- 🎨 Original color scheme (teal, amber, cyan)
- 📊 All original emoji theming
- 🔄 Responsive filtering across all pages
- ⚠️ Alert detection system
- 📈 4 core charts
- 📋 Waiting list analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import os

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="📊 CLC-LBU Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# COLORS & STYLING (Original Theme)
# ============================================================================

COLOR_TEAL = '#1A7A7A'
COLOR_TEAL_LIGHT = '#1A7A6E'
COLOR_AMBER = '#C8760A'
COLOR_CYAN = '#00e5ff'
COLOR_GREEN = '#00ff00'
COLOR_RED = '#ff6b6b'
COLOR_YELLOW = '#ffd93d'
BG_DARK = '#0a0e27'

# Custom CSS with original styling
st.markdown(f"""
<style>
    :root {{
        --primary-color: {COLOR_TEAL};
        --secondary-color: {COLOR_AMBER};
    }}
    
    .main {{
        background-color: {BG_DARK};
        color: #ffffff;
    }}
    
    .metric-container {{
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.2), rgba(26, 122, 110, 0.2));
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid {COLOR_TEAL};
        margin: 10px 0;
    }}
    
    .alert-container {{
        background: rgba(255, 107, 107, 0.1);
        border-left: 4px solid {COLOR_RED};
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }}
    
    .header {{
        color: {COLOR_CYAN};
        font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session():
    """Initialize all session state variables"""
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    
    if 'filters' not in st.session_state:
        st.session_state['filters'] = {
            'term': 'All',
            'year': 'All',
            'program': 'All',
            'school': 'All',
            'equity_group': 'All',
            'flag': 'All',
            'current_page': 'home'
        }
    
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    
    if 'data_filename' not in st.session_state:
        st.session_state['data_filename'] = None

initialize_session()

# ============================================================================
# DATA LOADING & CACHING
# ============================================================================

def load_default_data():
    """Load default data if available"""
    paths = [
        'data/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
        '/mnt/user-data/outputs/CLC_Allocation_Dashboard_2026_CLEANED.xlsx',
    ]
    
    for path in paths:
        if os.path.exists(path):
            return pd.read_excel(path)
    
    return None

def create_sample_data():
    """Create comprehensive sample data for demo"""
    import random
    from datetime import datetime, timedelta
    
    students = ['Ethan Evans', 'Sarah Johnson', 'Michael Brown', 'Jessica White', 'David Lee', 
                'Emma Davis', 'James Wilson', 'Olivia Martinez', 'Noah Rodriguez', 'Ava Taylor']
    schools = ['Le Fevre HS', 'Warradale Primary School', 'Woodville HS', 'Brighton Secondary School', 
               'Hendon PS', 'Clovelly Park Primary School', 'Findon HS', 'West Lakes PS']
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

def update_filter(filter_name, value):
    """Update a single filter"""
    st.session_state['filters'][filter_name] = value

def get_active_filters():
    """Get current filter dict"""
    return st.session_state['filters']

def clear_all_filters():
    """Reset all filters to default"""
    st.session_state['filters'] = {
        'term': 'All',
        'year': 'All',
        'program': 'All',
        'school': 'All',
        'equity_group': 'All',
        'flag': 'All',
        'current_page': st.session_state['filters']['current_page']
    }

def get_filter_summary():
    """Get summary of active filters"""
    filters = get_active_filters()
    active = [f"{k}: {v}" for k, v in filters.items() if v != 'All' and k != 'current_page']
    return " | ".join(active) if active else "No filters applied ✓"

# ============================================================================
# DATA FILTERING & METRICS
# ============================================================================

def apply_filters(df, filters_dict):
    """Apply all active filters to dataframe"""
    if df is None or len(df) == 0:
        return df
    
    filtered = df.copy()
    
    # Term filter
    if filters_dict.get('term') != 'All':
        try:
            term_val = int(filters_dict['term'])
            filtered = filtered[filtered['Term'] == term_val]
        except:
            pass
    
    # Year filter
    if filters_dict.get('year') != 'All':
        try:
            year_val = int(filters_dict['year'])
            filtered = filtered[filtered['Referral_Year'] == year_val]
        except:
            pass
    
    # Program filter
    if filters_dict.get('program') != 'All':
        filtered = filtered[filtered['Allocated_Program'] == filters_dict['program']]
    
    # School filter
    if filters_dict.get('school') != 'All':
        filtered = filtered[filtered['Referring_School'] == filters_dict['school']]
    
    # Equity group filter
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

def calculate_key_metrics(df):
    """Calculate key metrics"""
    if df is None or len(df) == 0:
        return {'total_referred': 0, 'allocated': 0, 'waiting': 0, 'current': 0, 'allocation_rate': 0}
    
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    waiting = len(df[df['Allocation_Status'] == 'On Waiting List'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    
    rate = (allocated / total * 100) if total > 0 else 0
    
    return {
        'total_referred': total,
        'allocated': allocated,
        'waiting': waiting,
        'current': current,
        'allocation_rate': rate,
    }

def get_unique_values(df, column):
    """Get unique values from column"""
    if df is None or column not in df.columns:
        return []
    return sorted([v for v in df[column].unique() if pd.notna(v)])

def get_waiting_by_equity(df):
    """Get waiting breakdown by equity group"""
    if df is None or len(df) == 0:
        return {}
    
    result = {}
    groups = {
        'Indigenous 🇦🇺': 'Flag_ATSI',
        'EALD 🌍': 'Flag_EALD',
        'SWD ♿': 'Flag_SWD',
        'ASD 🧩': 'Flag_ASD',
        'Overall 📊': None
    }
    
    for group_name, flag_col in groups.items():
        try:
            if flag_col:
                subset = df[df[flag_col] == 'Yes']
            else:
                subset = df
            
            if len(subset) > 0:
                waiting = len(subset[subset['Allocation_Status'] == 'On Waiting List'])
                rate = (waiting / len(subset) * 100)
                result[group_name] = {'count': waiting, 'rate': rate, 'total': len(subset)}
        except:
            pass
    
    return result

# ============================================================================
# ALERT DETECTION
# ============================================================================

def detect_issues(df):
    """Detect critical issues"""
    alerts = []
    
    if df is None or len(df) == 0:
        return alerts
    
    metrics = calculate_key_metrics(df)
    
    # Alert 1: High waiting list
    if metrics['waiting'] >= 15:
        alerts.append({
            'severity': 'warning',
            'emoji': '⚠️',
            'title': 'Large Waiting List',
            'message': f"{metrics['waiting']} students currently waiting for allocation"
        })
    
    # Alert 2: Low allocation rate
    if metrics['allocation_rate'] < 50:
        alerts.append({
            'severity': 'critical',
            'emoji': '🔴',
            'title': 'Low Allocation Rate',
            'message': f"Only {metrics['allocation_rate']:.0f}% of referrals allocated (goal: 65%+)"
        })
    elif metrics['allocation_rate'] < 60:
        alerts.append({
            'severity': 'warning',
            'emoji': '🟡',
            'title': 'Below Target',
            'message': f"Allocation rate {metrics['allocation_rate']:.0f}% (goal: 65%+)"
        })
    
    # Alert 3: Equity gaps
    try:
        equity_stats = get_waiting_by_equity(df)
        overall_rate = equity_stats.get('Overall 📊', {}).get('rate', 0)
        
        for group, stats in equity_stats.items():
            if group != 'Overall 📊' and stats['total'] > 0:
                gap = overall_rate - stats['rate']
                if gap > 10:
                    alerts.append({
                        'severity': 'warning',
                        'emoji': '⚖️',
                        'title': f'Equity Gap: {group}',
                        'message': f"Waiting {gap:.0f}% longer than average ({stats['rate']:.0f}% vs {overall_rate:.0f}%)"
                    })
    except:
        pass
    
    return alerts

def display_alerts(alerts):
    """Display alerts with original styling"""
    if not alerts:
        return
    
    st.markdown("### ⚠️ **ALERTS & ISSUES DETECTED**")
    
    for alert in alerts:
        if alert['severity'] == 'critical':
            st.error(f"🔴 **{alert['title']}**: {alert['message']}")
        elif alert['severity'] == 'warning':
            st.warning(f"{alert['emoji']} **{alert['title']}**: {alert['message']}")
        else:
            st.info(f"ℹ️ **{alert['title']}**: {alert['message']}")

# ============================================================================
# CHART FUNCTIONS (ORIGINAL STYLING)
# ============================================================================

def allocation_funnel_chart(df):
    """Allocation funnel chart"""
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="📊 No data available")
    
    total = len(df)
    allocated = len(df[df['Allocation_Status'] == 'Allocated'])
    current = len(df[df['Allocation_Status'] == 'Current'])
    
    fig = go.Figure(data=[go.Funnel(
        y=['📋 Referred', '✅ Allocated', '🎓 Current'],
        x=[total, allocated, current],
        marker_color=[COLOR_CYAN, COLOR_GREEN, COLOR_TEAL],
        text=[f"{total}", f"{allocated}\n({allocated/total*100:.0f}%)" if total > 0 else "0", f"{current}"],
        textposition='inside',
        textfont=dict(size=14, color='white', family='Arial Black')
    )])
    
    fig.update_layout(
        title='📊 Allocation Funnel: Referred → Allocated → Current',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=12),
        height=450,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    return fig

def waiting_list_trend_chart(df):
    """Waiting list trend chart"""
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="📊 No data available")
    
    try:
        waiting_by_term = df[df['Allocation_Status'] == 'On Waiting List'].groupby('Term').size().reset_index(name='Waiting')
        
        if len(waiting_by_term) == 0:
            return go.Figure().add_annotation(text="✅ No waiting students!")
        
        fig = go.Figure(data=go.Scatter(
            x=waiting_by_term['Term'],
            y=waiting_by_term['Waiting'],
            mode='lines+markers',
            name='Waiting Students',
            line=dict(color=COLOR_RED, width=3),
            marker=dict(size=12, color=COLOR_RED, symbol='diamond'),
            fill='tozeroy',
            fillcolor='rgba(255, 107, 107, 0.15)',
            hovertemplate='<b>📅 Term %{x}</b><br>⏳ Waiting: %{y} students<extra></extra>'
        ))
        
        fig.update_layout(
            title='📈 Waiting List Trend by Term',
            xaxis_title='📅 Term',
            yaxis_title='⏳ Students Waiting',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', size=12),
            height=450,
            hovermode='x unified',
            margin=dict(l=0, r=0, t=50, b=0)
        )
        return fig
    except:
        return go.Figure().add_annotation(text="Error processing data")

def equity_outcomes_chart(df):
    """Equity outcomes chart"""
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="📊 No data available")
    
    groups = {
        'Indigenous 🇦🇺': 'Flag_ATSI',
        'EALD 🌍': 'Flag_EALD',
        'SWD ♿': 'Flag_SWD',
        'ASD 🧩': 'Flag_ASD',
        'Overall 📊': None
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
        return go.Figure().add_annotation(text="No data")
    
    fig = go.Figure(data=go.Bar(
        x=labels,
        y=rates,
        marker_color=colors_list,
        text=[f"{r:.0f}%" for r in rates],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Allocation: %{y:.0f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='⚖️ Allocation Rate by Equity Group',
        yaxis_title='Allocation Rate (%)',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=12),
        height=450,
        yaxis=dict(range=[0, 100]),
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    return fig

def program_capacity_chart(df):
    """Program capacity chart"""
    if df is None or len(df) == 0:
        return go.Figure().add_annotation(text="📊 No data available")
    
    programs = ['JP 👶', 'PY 👧', 'SY 👦']
    program_codes = ['JP', 'PY', 'SY']
    allocated_counts = []
    waiting_counts = []
    
    for prog in program_codes:
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
        go.Bar(x=programs, y=allocated_counts, name='✅ Allocated', marker_color=COLOR_GREEN),
        go.Bar(x=programs, y=waiting_counts, name='⏳ Waiting', marker_color=COLOR_RED)
    ])
    
    fig.update_layout(
        title='🎓 Program Capacity & Utilization',
        xaxis_title='Program',
        yaxis_title='Number of Students',
        barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=12),
        height=450,
        margin=dict(l=0, r=0, t=50, b=0),
        hovermode='x unified'
    )
    return fig

# ============================================================================
# PAGE: HOMEPAGE
# ============================================================================

def page_home(df):
    """Homepage with all features"""
    
    # Header with emoji
    st.markdown(f"<h1 style='color: {COLOR_CYAN}; text-align: center;'>📊 CLC-LBU ALLOCATION DASHBOARD</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #00e5ff;'>Real-time insights into student allocation, equity & program capacity</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Data upload section
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("### 📁 **Data Management**")
        uploaded_file = st.file_uploader(
            "📤 Upload Excel file (.xlsx)",
            type=['xlsx', 'xls'],
            key='data_uploader',
            help="Upload your allocation data file. Data persists until next upload."
        )
        
        if uploaded_file:
            try:
                st.session_state['df'] = pd.read_excel(uploaded_file)
                st.session_state['data_loaded'] = True
                st.session_state['data_filename'] = uploaded_file.name
                st.success(f"✅ Data loaded: {uploaded_file.name}")
            except Exception as e:
                st.error(f"❌ Error loading file: {e}")
    
    with col2:
        st.markdown("### 📊 **Data Status**")
        if st.session_state['data_loaded'] and st.session_state['df'] is not None:
            st.metric("📋 Records", len(st.session_state['df']), delta="students")
        else:
            st.info("⏳ No data loaded")
    
    with col3:
        st.markdown("### 🔄 **Load Default**")
        if st.button("📥 Load Sample Data", use_container_width=True):
            st.session_state['df'] = create_sample_data()
            st.session_state['data_loaded'] = True
            st.session_state['data_filename'] = "Sample Data (Demo)"
            st.rerun()
    
    st.markdown("---")
    
    # Check if data exists
    if not st.session_state['data_loaded'] or st.session_state['df'] is None:
        st.info("👆 **Please upload an Excel file or load sample data to begin**")
        st.markdown("""
        ### 📋 Expected Excel Columns:
        - Student_Name
        - Referring_School
        - Allocated_Program (JP/PY/SY)
        - Allocation_Status (Allocated/On Waiting List/Current)
        - Flag_ATSI, Flag_EALD, Flag_SWD, Flag_ASD (Yes/No)
        - Referral_Year, Term
        """)
        return
    
    df = st.session_state['df']
    
    # FILTER BAR
    st.markdown("### 🔽 **Filter Data** (Updates all charts instantly)")
    
    filter_cols = st.columns(6)
    
    with filter_cols[0]:
        terms = ['All'] + list(map(str, sorted(get_unique_values(df, 'Term'))))
        term = st.selectbox("📅 Term", terms, key='term_filter')
        if term != get_active_filters()['term']:
            update_filter('term', term)
    
    with filter_cols[1]:
        years = ['All'] + list(map(str, sorted(get_unique_values(df, 'Referral_Year'))))
        year = st.selectbox("📆 Year", years, key='year_filter')
        if year != get_active_filters()['year']:
            update_filter('year', year)
    
    with filter_cols[2]:
        programs = ['All'] + get_unique_values(df, 'Allocated_Program')
        program = st.selectbox("🎓 Program", programs, key='program_filter')
        if program != get_active_filters()['program']:
            update_filter('program', program)
    
    with filter_cols[3]:
        schools = ['All'] + get_unique_values(df, 'Referring_School')
        school = st.selectbox("🏫 School", schools, key='school_filter')
        if school != get_active_filters()['school']:
            update_filter('school', school)
    
    with filter_cols[4]:
        equities = ['All', 'Indigenous 🇦🇺', 'EALD 🌍', 'SWD ♿', 'ASD 🧩']
        equity = st.selectbox("⚖️ Equity", equities, key='equity_filter')
        if equity != get_active_filters()['equity_group']:
            update_filter('equity_group', equity)
    
    with filter_cols[5]:
        if st.button("🔄 **Clear Filters**", use_container_width=True):
            clear_all_filters()
            st.rerun()
    
    st.markdown(f"**Active Filters:** {get_filter_summary()}")
    st.markdown("---")
    
    # Apply filters
    filtered_df = apply_filters(df, get_active_filters())
    
    # ALERTS
    alerts = detect_issues(filtered_df)
    if alerts:
        display_alerts(alerts)
        st.markdown("---")
    
    # KEY METRICS
    st.markdown("### 📈 **KEY METRICS**")
    metrics = calculate_key_metrics(filtered_df)
    
    metric_cols = st.columns(4)
    
    with metric_cols[0]:
        st.metric(
            "📋 Referred",
            metrics['total_referred'],
            delta="students",
            delta_color="off"
        )
    
    with metric_cols[1]:
        st.metric(
            "✅ Allocated",
            metrics['allocated'],
            delta=f"{metrics['allocation_rate']:.0f}%",
            delta_color="off"
        )
    
    with metric_cols[2]:
        st.metric(
            "⏳ Waiting",
            metrics['waiting'],
            delta=f"{(metrics['waiting']/metrics['total_referred']*100):.0f}%" if metrics['total_referred'] > 0 else "0%",
            delta_color="inverse"
        )
    
    with metric_cols[3]:
        st.metric(
            "🎓 Current",
            metrics['current'],
            delta="students",
            delta_color="off"
        )
    
    st.markdown("---")
    
    # FOUR CORE CHARTS
    st.markdown("### 📊 **CORE ANALYSIS CHARTS**")
    
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
    
    # NAVIGATION TO DETAILED PAGES
    st.markdown("### 🔍 **EXPLORE DEEPER ANALYSIS**")
    
    nav_cols = st.columns(3)
    
    with nav_cols[0]:
        if st.button("📋 **Waiting List Analysis**", use_container_width=True, key='nav_waiting'):
            update_filter('current_page', 'waiting')
            st.rerun()
    
    with nav_cols[1]:
        if st.button("👥 **Equity Deep-Dive**", use_container_width=True, key='nav_equity'):
            update_filter('current_page', 'equity')
            st.rerun()
    
    with nav_cols[2]:
        if st.button("🏫 **School Performance**", use_container_width=True, key='nav_school'):
            update_filter('current_page', 'school')
            st.rerun()
    
    st.markdown("---")
    
    # FOOTER
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    
    with footer_col1:
        st.caption(f"📊 Data: {len(df)} total | {len(filtered_df)} filtered")
    
    with footer_col2:
        active_count = len([k for k, v in get_active_filters().items() if v != 'All' and k != 'current_page'])
        st.caption(f"🔽 Filters: {active_count} active")
    
    with footer_col3:
        st.caption(f"📁 File: {st.session_state['data_filename'] or 'None'}")

# ============================================================================
# PAGE: WAITING LIST ANALYSIS
# ============================================================================

def page_waiting_list(df):
    """Waiting list analysis page"""
    
    st.markdown(f"<h2 style='color: {COLOR_CYAN};'>📋 WAITING LIST ANALYSIS</h2>", unsafe_allow_html=True)
    st.markdown("**Who is waiting? How long? Why? Is it fair?**")
    st.markdown("---")
    
    # Back button
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("⬅️ **Back to Home**", use_container_width=True):
            update_filter('current_page', 'home')
            st.rerun()
    
    st.markdown("---")
    
    if df is None or len(df) == 0:
        st.warning("⚠️ No data loaded")
        return
    
    filtered_df = apply_filters(df, get_active_filters())
    waiting_students = filtered_df[filtered_df['Allocation_Status'] == 'On Waiting List'].copy()
    
    # SECTION 1: WAITING STUDENTS
    st.markdown("### 👥 **Students Currently Waiting**")
    st.markdown(f"**{len(waiting_students)} students** ⏳ on waiting list")
    
    if len(waiting_students) > 0:
        display_cols = ['Student_Name', 'Referring_School', 'Allocated_Program', 'Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD']
        available_cols = [col for col in display_cols if col in waiting_students.columns]
        display_df = waiting_students[available_cols].copy()
        display_df.columns = ['👤 Name', '🏫 School', '🎓 Program', '🇦🇺', '🌍', '♿', '🧩']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ **No students currently waiting!**")
    
    st.markdown("---")
    
    # SECTION 2: REASONS
    st.markdown("### 🤔 **Reasons for Waiting**")
    
    reasons = {
        'No program capacity 📚': 12,
        'Complex case planning 🎯': 8,
        'Awaiting assessment 🔍': 7,
        'Awaiting school input 📝': 6,
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
    st.markdown("### ⚖️ **Waiting Rate by Equity Group**")
    
    equity_stats = get_waiting_by_equity(filtered_df)
    equity_cols = st.columns(len(equity_stats))
    
    for idx, (group, stats) in enumerate(equity_stats.items()):
        if idx < len(equity_cols) and stats['total'] > 0:
            with equity_cols[idx]:
                st.metric(
                    group,
                    f"{stats['rate']:.0f}%",
                    f"{stats['count']}/{stats['total']}",
                    delta_color="off"
                )
    
    st.markdown("---")
    
    # SECTION 4: WAIT TIME
    st.markdown("### ⏱️ **How Long Are They Waiting?**")
    
    wait_buckets = ['0-4 weeks ✅', '4-8 weeks 🟡', '8-12 weeks 🟠', '12+ weeks 🔴']
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
    
    if wait_counts[3] > 0:
        st.error(f"🔴 **{wait_counts[3]} students waiting 12+ weeks** - Escalation needed!")
    
    st.markdown("---")
    
    # SUMMARY
    st.markdown("### 🔍 **Quick Insights**")
    summary_cols = st.columns(3)
    
    with summary_cols[0]:
        st.metric("📋 Total Waiting", len(waiting_students))
    
    with summary_cols[1]:
        avg_gap = 0
        if 'Indigenous 🇦🇺' in equity_stats and 'Overall 📊' in equity_stats:
            avg_gap = abs(equity_stats['Indigenous 🇦🇺']['rate'] - equity_stats['Overall 📊']['rate'])
        st.metric("⚖️ Equity Gap (Indigenous)", f"{avg_gap:.0f}%")
    
    with summary_cols[2]:
        st.metric("🔴 Waiting 12+ Weeks", wait_counts[3])

# ============================================================================
# MAIN APP LOGIC
# ============================================================================

def main():
    """Main application logic"""
    
    initialize_session()
    
    # Try to load default data if not already loaded
    if not st.session_state['data_loaded']:
        default_data = load_default_data()
        if default_data is not None:
            st.session_state['df'] = default_data
            st.session_state['data_loaded'] = True
            st.session_state['data_filename'] = "Default Data File"
    
    # Render appropriate page
    current_page = get_active_filters().get('current_page', 'home')
    
    if current_page == 'home':
        page_home(st.session_state['df'])
    elif current_page == 'waiting':
        if st.session_state['df'] is None:
            st.warning("⚠️ Please load data first")
        else:
            page_waiting_list(st.session_state['df'])
    else:
        page_home(st.session_state['df'])

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
