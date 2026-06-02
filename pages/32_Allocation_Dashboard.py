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

# ══════════════════════════════════════════════════════════════════════════════
# MODERN DARK THEME - COMPLETE REDESIGN
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CLC Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide debug by default
)

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
        padding: 2rem;
        max-width: 1600px;
        margin: 0 auto;
    }
    
    /* ===== HEADER TILES - CONSISTENT COLOR & NEON GLOW ===== */
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
        font-size: 1.8rem !important;
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
    
    /* ===== BUTTONS ===== */
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
    
    /* ===== METRIC CARDS ===== */
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
    
    /* ===== INPUTS & SELECTS ===== */
    [data-testid="stSelectbox"],
    [data-testid="stNumberInput"],
    [data-testid="stTextInput"],
    [data-testid="stDateInput"] {
        min-height: 50px !important;
    }
    
    input, select, textarea {
        background-color: #1a1f3a !important;
        color: #e0e0e0 !important;
        border: 1px solid #2a3050 !important;
        border-radius: 8px !important;
        font-family: 'Poppins', sans-serif !important;
    }
    
    input:focus, select:focus, textarea:focus {
        border-color: #00e5ff !important;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.3) !important;
    }
    
    /* ===== TABS ===== */
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
    
    /* ===== EXPANDERS ===== */
    [data-testid="stExpander"] {
        background-color: #1a1f3a !important;
        border: 1px solid #2a3050 !important;
        border-radius: 8px !important;
    }
    
    /* ===== DATAFRAMES & TABLES ===== */
    [data-testid="stDataframe"] {
        background-color: #0a0e27 !important;
    }
    
    .dataframe {
        color: #e0e0e0 !important;
    }
    
    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background-color: #0a0e27 !important;
    }
    
    /* ===== DIVIDER ===== */
    hr {
        border-color: #2a3050 !important;
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
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

# Main Title
st.markdown("""
    <div class="section-header">
        <h2>📊 Allocation Dashboard</h2>
    </div>
""", unsafe_allow_html=True)

st.markdown("**Interactive student allocation analytics and insights**")

# Sidebar Filters (Clean)
with st.sidebar:
    st.markdown("### 🔍 Filters")
    
    selected_program = st.selectbox("Program", ["All", "JP", "PY", "SY"])
    selected_status = st.selectbox("Status", ["All", "Allocated", "Pending", "Not Placed"])
    selected_term = st.selectbox("Term", ["All", "Term 1", "Term 2", "Term 3", "Term 4"])

# Summary Metrics
st.markdown("""
    <div class="section-header">
        <h3>📈 Summary Metrics</h3>
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

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📋 Allocations", "📊 Analytics", "🗺️ Geography", "📈 Trends"])

with tab1:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Student Allocations</h2>
            <p class="drill-down-subtitle">Current placement status and details</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Sample data
    df = pd.DataFrame({
        'Student': ['John Smith', 'Mary Jones', 'Sarah Lee', 'David Chen', 'Emma Wilson'],
        'Program': ['JP', 'PY', 'SY', 'JP', 'PY'],
        'Status': ['Allocated', 'Allocated', 'Pending', 'Allocated', 'Not Placed'],
        'Start Date': ['2026-06-09', '2026-06-09', 'TBD', '2026-06-16', 'TBD'],
        'School': ['Prospect Primary', 'Henley Beach', 'Cowandilla', 'Adelaide Botanic', 'Mitcham Girls']
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
    
    st.info("📍 Partnership area map would display here with interactive regions")

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
