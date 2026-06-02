import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import folium
from streamlit_folium import st_folium
from collections import Counter
from supabase import create_client
import os

st.set_page_config(
    page_title="CLC Allocation Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize session state for filters
if 'selected_programs' not in st.session_state:
    st.session_state.selected_programs = {'JP', 'PY', 'SY'}
if 'selected_status' not in st.session_state:
    st.session_state.selected_status = {'Allocated', 'Pending'}
if 'selected_partnership' not in st.session_state:
    st.session_state.selected_partnership = {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
if 'selected_year_level' not in st.session_state:
    st.session_state.selected_year_level = {'R', '1', '2', '3', '4', '5', '6', '7'}

# MODERN TYPOGRAPHY & COLOR SCHEME
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Font & Background */
    * {
        font-family: 'Poppins', sans-serif !important;
    }
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main {
        background-color: #0a0e27 !important;
        color: #e0e0e0 !important;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    
    p, span, div, label {
        font-family: 'Poppins', sans-serif !important;
        color: #b0b8d0 !important;
    }
    
    /* Main Container */
    .main > div {
        padding: 2.5rem;
        max-width: 1600px;
        margin: 0 auto;
    }
    
    /* IMPRESSIVE MAIN TITLE */
    .main-title {
        background: linear-gradient(135deg, #1a1f3a 0%, #2a3050 100%);
        border: 2px solid #00e5ff;
        border-radius: 16px;
        padding: 3.5rem 4rem;
        margin-bottom: 3rem;
        box-shadow: 0 0 40px rgba(0, 229, 255, 0.4), 
                    inset 0 0 30px rgba(0, 229, 255, 0.1);
        text-align: center;
    }
    
    .main-title h1 {
        font-size: 3.5rem !important;
        color: #ffffff !important;
        margin: 0 !important;
        font-weight: 800 !important;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
        letter-spacing: -1px !important;
    }
    
    .main-title p {
        color: rgba(255, 255, 255, 0.85) !important;
        font-size: 1.2rem !important;
        margin: 1rem 0 0 0 !important;
        font-weight: 400 !important;
    }
    
    /* Filter Cards */
    .filter-card {
        background-color: #1a1f3a;
        border: 2px solid #2a3050;
        border-radius: 10px;
        padding: 12px 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
        font-weight: 600;
        color: #b0b8d0;
    }
    
    .filter-card:hover {
        border-color: #00e5ff;
        color: #00e5ff;
    }
    
    .filter-card-active {
        background-color: #1a1f3a;
        border: 2px solid #00e5ff;
        color: #00e5ff;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
    }
    
    /* Header Tiles */
    .section-header, .drill-down-header {
        background-color: #1a1f3a !important;
        border: 2px solid #00e5ff !important;
        border-radius: 14px !important;
        padding: 2rem !important;
        margin: 2rem 0 1.5rem 0 !important;
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.35), 
                    inset 0 0 20px rgba(0, 229, 255, 0.08) !important;
        transition: all 0.3s ease !important;
    }
    
    .section-header:hover, .drill-down-header:hover {
        box-shadow: 0 0 40px rgba(0, 229, 255, 0.5), 
                    inset 0 0 20px rgba(0, 229, 255, 0.12) !important;
    }
    
    .section-header h2, .section-header h3 {
        color: #ffffff !important;
        font-size: 2rem !important;
        margin: 0 !important;
        font-weight: 700 !important;
    }
    
    .drill-down-header h1, .drill-down-header h2 {
        color: #ffffff !important;
        font-size: 2.2rem !important;
        margin: 0 !important;
        font-weight: 800 !important;
    }
    
    .drill-down-subtitle {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 1.1rem !important;
        margin-top: 0.5rem !important;
        font-weight: 400 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1a1f3a !important;
        color: #00e5ff !important;
        border: 1.5px solid #00e5ff !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 0.75rem 1.5rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.2) !important;
    }
    
    .stButton > button:hover {
        background-color: #00e5ff !important;
        color: #0a0e27 !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Metric Cards */
    [data-testid="metric-container"] {
        background-color: #1a1f3a !important;
        border: 1px solid #2a3050 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="metric-container"]:hover {
        border-color: #00e5ff !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.2) !important;
    }
    
    [data-testid="metric-value"] {
        color: #00e5ff !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
    }
    
    [data-testid="metric-label"] {
        color: #b0b8d0 !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }
    
    /* Tabs */
    [data-baseweb="tab-list"] {
        border-bottom: 2px solid #2a3050 !important;
        gap: 1rem !important;
    }
    
    [data-baseweb="tab"] {
        color: #b0b8d0 !important;
        font-weight: 600 !important;
        border-radius: 8px 8px 0 0 !important;
    }
    
    [aria-selected="true"] {
        color: #00e5ff !important;
        border-bottom: 3px solid #00e5ff !important;
    }
    
    /* Hide accessibility labels */
    [aria-label="keyboard_double"] {
        display: none !important;
    }
    
    label {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

try:
    supabase = init_supabase()
except:
    supabase = None

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - CARD-BASED FILTERS
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### Select What to Analyse")
    
    # Year Selection
    st.markdown("**Year**")
    year_col1, year_col2, year_col3 = st.columns(3)
    if year_col1.button("2024", use_container_width=True):
        st.session_state.selected_year = 2024
    if year_col2.button("2025", use_container_width=True):
        st.session_state.selected_year = 2025
    if year_col3.button("2026", use_container_width=True):
        st.session_state.selected_year = 2026
    
    st.markdown("---")
    
    # Term Selection
    st.markdown("**Term**")
    term_col1, term_col2, term_col3, term_col4 = st.columns(4)
    if term_col1.button("Term 1", use_container_width=True):
        st.session_state.selected_term = "Term 1"
    if term_col2.button("Term 2", use_container_width=True):
        st.session_state.selected_term = "Term 2"
    if term_col3.button("Term 3", use_container_width=True):
        st.session_state.selected_term = "Term 3"
    if term_col4.button("Term 4", use_container_width=True):
        st.session_state.selected_term = "Term 4"
    
    st.markdown("---")
    
    # Program Selection
    st.markdown("**Program**")
    prog_buttons = st.columns(5)
    
    if prog_buttons[0].button("Select All", use_container_width=True, key="btn_prog_all"):
        st.session_state.selected_programs = {"JP", "PY", "SY"}
    
    if prog_buttons[4].button("Clear All", use_container_width=True, key="btn_prog_clear"):
        st.session_state.selected_programs = set()
    
    prog_col1, prog_col2, prog_col3 = st.columns(3)
    
    if prog_col1.button("JP", use_container_width=True, key="btn_jp"):
        if "JP" in st.session_state.selected_programs:
            st.session_state.selected_programs.remove("JP")
        else:
            st.session_state.selected_programs.add("JP")
    
    if prog_col2.button("PY", use_container_width=True, key="btn_py"):
        if "PY" in st.session_state.selected_programs:
            st.session_state.selected_programs.remove("PY")
        else:
            st.session_state.selected_programs.add("PY")
    
    if prog_col3.button("SY", use_container_width=True, key="btn_sy"):
        if "SY" in st.session_state.selected_programs:
            st.session_state.selected_programs.remove("SY")
        else:
            st.session_state.selected_programs.add("SY")
    
    st.markdown("---")
    
    # Status Selection
    st.markdown("**Allocation Status**")
    status_buttons = st.columns(6)
    
    if status_buttons[0].button("Select All", use_container_width=True, key="btn_status_all"):
        st.session_state.selected_status = {"Allocated", "Pending", "Not Placed", "On Waitlist"}
    
    if status_buttons[5].button("Clear All", use_container_width=True, key="btn_status_clear"):
        st.session_state.selected_status = set()
    
    status_col1, status_col2 = st.columns(2)
    
    if status_col1.button("Allocated", use_container_width=True, key="btn_allocated"):
        if "Allocated" in st.session_state.selected_status:
            st.session_state.selected_status.remove("Allocated")
        else:
            st.session_state.selected_status.add("Allocated")
    
    if status_col2.button("Pending", use_container_width=True, key="btn_pending"):
        if "Pending" in st.session_state.selected_status:
            st.session_state.selected_status.remove("Pending")
        else:
            st.session_state.selected_status.add("Pending")
    
    status_col3, status_col4 = st.columns(2)
    
    if status_col3.button("Not Placed", use_container_width=True, key="btn_notplaced"):
        if "Not Placed" in st.session_state.selected_status:
            st.session_state.selected_status.remove("Not Placed")
        else:
            st.session_state.selected_status.add("Not Placed")
    
    if status_col4.button("Waitlist", use_container_width=True, key="btn_waitlist"):
        if "On Waitlist" in st.session_state.selected_status:
            st.session_state.selected_status.remove("On Waitlist")
        else:
            st.session_state.selected_status.add("On Waitlist")
    
    st.markdown("---")
    
    # Partnership Selection
    st.markdown("**Partnership Area**")
    partner_buttons = st.columns(6)
    
    if partner_buttons[0].button("Select All", use_container_width=True, key="btn_partner_all"):
        st.session_state.selected_partnership = {"Inner West", "Adelaide Prospect", "Greenhill South", "Holdfast", "Mitcham Hills"}
    
    if partner_buttons[5].button("Clear All", use_container_width=True, key="btn_partner_clear"):
        st.session_state.selected_partnership = set()
    
    partnership_options = ["Inner West", "Adelaide Prospect", "Greenhill South", "Holdfast", "Mitcham Hills"]
    
    for i, partnership in enumerate(partnership_options):
        if i % 2 == 0:
            col1, col2 = st.columns(2)
        
        if i % 2 == 0:
            if col1.button(partnership, use_container_width=True, key=f"btn_partner_{partnership}"):
                if partnership in st.session_state.selected_partnership:
                    st.session_state.selected_partnership.remove(partnership)
                else:
                    st.session_state.selected_partnership.add(partnership)
        else:
            if col2.button(partnership, use_container_width=True, key=f"btn_partner_{partnership}"):
                if partnership in st.session_state.selected_partnership:
                    st.session_state.selected_partnership.remove(partnership)
                else:
                    st.session_state.selected_partnership.add(partnership)
    
    st.markdown("---")
    
    # Year Level Selection
    st.markdown("**Year Level**")
    level_buttons = st.columns(6)
    
    if level_buttons[0].button("Select All", use_container_width=True, key="btn_level_all"):
        st.session_state.selected_year_level = {"R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}
    
    if level_buttons[5].button("Clear All", use_container_width=True, key="btn_level_clear"):
        st.session_state.selected_year_level = set()
    
    year_levels = ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    
    for i in range(0, len(year_levels), 3):
        cols = st.columns(3)
        for j, level in enumerate(year_levels[i:i+3]):
            if cols[j].button(level, use_container_width=True, key=f"btn_level_{level}"):
                if level in st.session_state.selected_year_level:
                    st.session_state.selected_year_level.remove(level)
                else:
                    st.session_state.selected_year_level.add(level)
    
    st.markdown("---")
    
    st.markdown("### Data Management")
    
    uploaded_file = st.file_uploader("Upload Excel", type=['xlsx', 'xls', 'csv'])
    if uploaded_file is not None:
        st.success("File uploaded")
    
    if st.button("Export Data", use_container_width=True):
        st.info("Preparing download...")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

# Impressive Main Title
st.markdown("""
    <div class="main-title">
        <h1>Allocation Dashboard</h1>
        <p>Student placement analytics and management</p>
    </div>
""", unsafe_allow_html=True)

# Summary Metrics
st.markdown("""
    <div class="section-header">
        <h2>Summary Metrics</h2>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Students", "145", "+12")
with col2:
    st.metric("Allocated", "112", "+8")
with col3:
    st.metric("Pending", "28", "-3")
with col4:
    st.metric("On Waitlist", "15", "+2")

st.markdown("---")

# Display current filters
st.markdown("""
    <div class="section-header">
        <h3>Current Filters</h3>
    </div>
""", unsafe_allow_html=True)

filter_text = f"""
**Programs:** {', '.join(sorted(st.session_state.selected_programs)) if st.session_state.selected_programs else 'None'}  
**Status:** {', '.join(sorted(st.session_state.selected_status)) if st.session_state.selected_status else 'None'}  
**Partnership Areas:** {', '.join(sorted(st.session_state.selected_partnership)) if st.session_state.selected_partnership else 'None'}  
**Year Levels:** {', '.join(sorted(st.session_state.selected_year_level)) if st.session_state.selected_year_level else 'None'}
"""

st.markdown(filter_text)

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Allocations", "Analytics", "Geography", "Trends"])

with tab1:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Student Allocations</h2>
            <p class="drill-down-subtitle">Current placement status and details</p>
        </div>
    """, unsafe_allow_html=True)
    
    df = pd.DataFrame({
        'Student': ['John Smith', 'Mary Jones', 'Sarah Lee', 'David Chen', 'Emma Wilson'],
        'Program': ['JP', 'PY', 'SY', 'JP', 'PY'],
        'Status': ['Allocated', 'Allocated', 'Pending', 'Allocated', 'Not Placed'],
        'Year Level': ['2', '4', '7', '1', '5'],
        'School': ['Prospect Primary', 'Henley Beach', 'Cowandilla', 'Adelaide Botanic', 'Mitcham Girls'],
        'Partnership': ['Inner West', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast']
    })
    
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Analytics Overview</h2>
            <p class="drill-down-subtitle">Distribution and breakdown analysis</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure(data=[go.Pie(
            labels=['Allocated', 'Pending', 'Not Placed'],
            values=[112, 28, 5],
            marker=dict(colors=['#00e5ff', '#ff6b6b', '#ffd93d'])
        )])
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins'),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = go.Figure(data=[
            go.Bar(x=['JP', 'PY', 'SY'], y=[45, 55, 12], marker_color='#00e5ff')
        ])
        fig.update_layout(
            title='By Program',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins'),
            xaxis_title='Program',
            yaxis_title='Count'
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Geographic Distribution</h2>
            <p class="drill-down-subtitle">Student allocation across partnership areas</p>
        </div>
    """, unsafe_allow_html=True)
    
    m = folium.Map(
        location=[-34.93, 138.60],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
    partnerships_map = {
        'Inner West': {'coords': [-34.90, 138.54], 'count': 28},
        'Adelaide Prospect': {'coords': [-34.85, 138.60], 'count': 35},
        'Greenhill South': {'coords': [-34.98, 138.63], 'count': 22},
        'Holdfast': {'coords': [-35.02, 138.52], 'count': 18},
        'Mitcham Hills': {'coords': [-34.99, 138.65], 'count': 15}
    }
    
    for partnership, data in partnerships_map.items():
        folium.CircleMarker(
            location=data['coords'],
            radius=15,
            popup=f"{partnership}<br>Students: {data['count']}",
            color='#00e5ff',
            fill=True,
            fillColor='#00e5ff',
            fillOpacity=0.7,
            weight=2,
            tooltip=f"{partnership}: {data['count']}"
        ).add_to(m)
    
    folium.Marker(
        location=[-34.9286, 138.5830],
        popup="CLC-LBU Cowandilla",
        icon=folium.Icon(color='green', icon='home'),
        tooltip="Cowandilla"
    ).add_to(m)
    
    st_folium(m, width=1200, height=500)
    
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Inner West", "28")
    with col2:
        st.metric("Adelaide Prospect", "35")
    with col3:
        st.metric("Greenhill South", "22")
    with col4:
        st.metric("Holdfast", "18")
    with col5:
        st.metric("Mitcham Hills", "15")

with tab4:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Allocation Trends</h2>
            <p class="drill-down-subtitle">Historical data and forecasting</p>
        </div>
    """, unsafe_allow_html=True)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'],
        y=[18, 22, 25, 28, 32],
        mode='lines+markers',
        name='Allocations',
        line=dict(color='#00e5ff', width=3),
        marker=dict(size=8)
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0', family='Poppins'),
        hovermode='x unified',
        xaxis_title='Week',
        yaxis_title='Allocations'
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem 0;'>
    <p style='font-size: 0.9rem; margin: 0;'>CLC-LBU Allocation Dashboard</p>
    <p style='font-size: 0.8rem; margin: 0.5rem 0 0 0;'>Modern analytics platform</p>
</div>
""", unsafe_allow_html=True)
