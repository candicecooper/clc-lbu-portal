import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# Page config
st.set_page_config(
    page_title="Allocation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PROFESSIONAL COLOR SCHEME CSS
# ============================================================================
st.markdown("""
    <style>
    /* Page background */
    [data-testid="stAppViewContainer"] {
        background-color: #F5F7FA;
    }
    
    /* Header */
    [data-testid="stHeader"] {
        background-color: white;
        border-bottom: 1px solid #E5E7EB;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0F2844;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* Main content */
    .main {
        background-color: #F5F7FA;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #0B9E9E;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        padding: 10px 20px;
    }
    
    .stButton > button:hover {
        background-color: #0A8E8E;
        box-shadow: 0 4px 12px rgba(11, 158, 158, 0.3);
    }
    
    /* Inputs */
    .stSelectbox, .stTextInput, .stNumberInput, .stDateInput {
        border-radius: 8px;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #0F2844;
        color: white;
        border-radius: 8px;
    }
    
    /* Metric containers */
    [data-testid="metric-container"] {
        background-color: white;
        border-radius: 12px;
        border-left: 4px solid #0B9E9E;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Tabs */
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 2px solid #E5E7EB;
    }
    
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        border-bottom: 3px solid #0B9E9E;
        color: #0F2844;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# MAIN TITLE
# ============================================================================
st.markdown("""
    <div style='
        background: linear-gradient(135deg, #0F2844 0%, #0B9E9E 100%);
        padding: 40px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    '>
        <h1 style='
            color: white;
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        '>📊 Allocation Dashboard</h1>
        <p style='
            color: rgba(255,255,255,0.9);
            margin: 12px 0 0 0;
            font-size: 1.1rem;
            font-weight: 400;
        '>Streamlined Student Allocation Management</p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# SUMMARY METRICS SECTION
# ============================================================================
st.markdown("""
    <div style='
        background-color: #0F2844;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 4px solid #0B9E9E;
    '>
        <h2 style='margin: 0; font-size: 1.5rem; font-weight: 600;'>📈 Summary Metrics</h2>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Students", "145", "+12", delta_color="inverse")
with col2:
    st.metric("Allocated", "112", "+8", delta_color="inverse")
with col3:
    st.metric("Pending", "28", "-3")
with col4:
    st.metric("On Waitlist", "15", "+2", delta_color="inverse")

# ============================================================================
# KEY INDICATORS
# ============================================================================
st.markdown("""
    <div style='
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 20px;
        margin: 20px 0;
    '>
        <div style='
            background-color: white;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #10B981;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        '>
            <p style='color: #6B7280; font-size: 0.9rem; margin: 0 0 8px 0; font-weight: 500;'>
                Success Rate
            </p>
            <p style='color: #10B981; font-size: 2rem; margin: 0; font-weight: 700;'>
                77.2%
            </p>
            <p style='color: #9CA3AF; font-size: 0.85rem; margin: 8px 0 0 0;'>
                ↑ Up from 75% last week
            </p>
        </div>
        
        <div style='
            background-color: white;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #F59E0B;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        '>
            <p style='color: #6B7280; font-size: 0.9rem; margin: 0 0 8px 0; font-weight: 500;'>
                Average Processing Time
            </p>
            <p style='color: #F59E0B; font-size: 2rem; margin: 0; font-weight: 700;'>
                3.2 days
            </p>
            <p style='color: #9CA3AF; font-size: 0.85rem; margin: 8px 0 0 0;'>
                ↓ Down from 4.1 days
            </p>
        </div>
        
        <div style='
            background-color: white;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #0B9E9E;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        '>
            <p style='color: #6B7280; font-size: 0.9rem; margin: 0 0 8px 0; font-weight: 500;'>
                This Week Activity
            </p>
            <p style='color: #0B9E9E; font-size: 2rem; margin: 0; font-weight: 700;'>
                28 allocations
            </p>
            <p style='color: #9CA3AF; font-size: 0.85rem; margin: 8px 0 0 0;'>
                On schedule for target
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# STATUS INFORMATION
# ============================================================================
st.markdown("""
    <div style='
        background-color: #ECFDF5;
        border-left: 4px solid #10B981;
        border-radius: 8px;
        padding: 15px;
        margin: 20px 0;
    '>
        <p style='color: #065F46; margin: 0; font-weight: 600;'>
            ✅ All current allocations processed successfully
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# TABS FOR DETAILED VIEWS
# ============================================================================
tab1, tab2, tab3, tab4 = st.tabs(["📋 Recent Allocations", "📊 Statistics", "⏳ Pending Review", "📈 Trends"])

with tab1:
    st.markdown("""
        <div style='
            background-color: #0F2844;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #0B9E9E;
        '>
            <h3 style='margin: 0; font-size: 1.2rem; font-weight: 600;'>
                Recent Allocations
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Sample data
    df_recent = pd.DataFrame({
        'Student': ['John Smith', 'Mary Jones', 'Sarah Lee', 'David Chen', 'Emma Wilson'],
        'Year Level': ['5', '3', '7', '4', '6'],
        'Program': ['JP', 'JP', 'PY', 'SY', 'PY'],
        'School': ['Prospect Primary', 'Henley Beach', 'Cowandilla', 'Adelaide Botanic', 'Mitcham Girls'],
        'Status': ['✅ Allocated', '✅ Allocated', '✅ Allocated', '⏳ Pending', '✅ Allocated'],
        'Start Date': ['2026-06-09', '2026-06-09', '2026-06-16', 'TBD', '2026-06-09']
    })
    
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
    
    with st.expander("📌 View more details"):
        st.write("Detailed allocation information would appear here")

with tab2:
    st.markdown("""
        <div style='
            background-color: #0F2844;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #0B9E9E;
        '>
            <h3 style='margin: 0; font-size: 1.2rem; font-weight: 600;'>
                Program Distribution
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sample pie chart
        fig = go.Figure(data=[go.Pie(
            labels=['Junior Primary', 'Primary Years', 'Senior Years'],
            values=[45, 55, 12],
            marker=dict(colors=['#0B9E9E', '#0F2844', '#F59E0B'])
        )])
        fig.update_layout(
            height=400,
            showlegend=True,
            hovermode='closest',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Sample bar chart
        fig = go.Figure(data=[
            go.Bar(x=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], y=[8, 5, 6, 9, 7],
                   marker_color='#0B9E9E', name='Allocations')
        ])
        fig.update_layout(
            title='Allocations by Day',
            xaxis_title='Day',
            yaxis_title='Count',
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("""
        <div style='
            background-color: #0F2844;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #0B9E9E;
        '>
            <h3 style='margin: 0; font-size: 1.2rem; font-weight: 600;'>
                Pending Review
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style='
            background-color: #FFFBEB;
            border-left: 4px solid #F59E0B;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        '>
            <p style='color: #92400E; margin: 0; font-weight: 600;'>
                ⚠️ 3 allocations awaiting school confirmation
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    df_pending = pd.DataFrame({
        'Student': ['Michael Brown', 'Lisa Anderson', 'Tom Harris'],
        'Program': ['PY', 'SY', 'JP'],
        'Days Pending': [5, 8, 3],
        'Action Required': ['School Response', 'Parent Approval', 'Documentation']
    })
    
    st.dataframe(df_pending, use_container_width=True, hide_index=True)

with tab4:
    st.markdown("""
        <div style='
            background-color: #0F2844;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #0B9E9E;
        '>
            <h3 style='margin: 0; font-size: 1.2rem; font-weight: 600;'>
                Trend Analysis
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'],
        y=[18, 22, 25, 28, 32],
        mode='lines+markers',
        name='Allocations',
        line=dict(color='#0B9E9E', width=3),
        marker=dict(size=8)
    ))
    fig.update_layout(
        title='Allocation Trends - 5 Week View',
        xaxis_title='Week',
        yaxis_title='Number of Allocations',
        height=400,
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#0F2844')
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("""
    <div style='
        text-align: center;
        color: #9CA3AF;
        padding: 30px 0 20px 0;
        border-top: 1px solid #E5E7EB;
        margin-top: 40px;
    '>
        <p style='margin: 0; font-size: 0.9rem;'>
            Last updated: """ + datetime.now().strftime('%B %d, %Y at %I:%M %p') + """
        </p>
        <p style='margin: 5px 0 0 0; font-size: 0.85rem;'>
            CLC-LBU Portal • Allocation Management System
        </p>
    </div>
""", unsafe_allow_html=True)
