import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="CLC Allocation Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize session state for filters
if 'selected_programs' not in st.session_state:
    st.session_state.selected_programs = {'JP', 'PY', 'SY'}
if 'selected_status' not in st.session_state:
    st.session_state.selected_status = {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'}
if 'selected_atsi' not in st.session_state:
    st.session_state.selected_atsi = {'Yes', 'No'}
if 'selected_attendance' not in st.session_state:
    st.session_state.selected_attendance = {'Full-time', 'Part-time', 'Irregular'}
if 'selected_swd' not in st.session_state:
    st.session_state.selected_swd = {'Yes', 'No'}
if 'selected_disability' not in st.session_state:
    st.session_state.selected_disability = {'ASD', 'ADHD', 'Learning Disability', 'Physical', 'Hearing', 'Vision', 'Other'}
if 'selected_eald' not in st.session_state:
    st.session_state.selected_eald = {'Yes', 'No'}
if 'selected_behaviour' not in st.session_state:
    st.session_state.selected_behaviour = {'Mild', 'Moderate', 'Severe', 'None'}
if 'selected_referral' not in st.session_state:
    st.session_state.selected_referral = {'First', 'Multiple'}
if 'selected_partnership' not in st.session_state:
    st.session_state.selected_partnership = {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}

# MODERN DARK THEME
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif !important;
    }
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main {
        background-color: #0a0e27 !important;
        color: #e0e0e0 !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    
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
        box-shadow: 0 0 40px rgba(0, 229, 255, 0.4), inset 0 0 30px rgba(0, 229, 255, 0.1);
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
    
    /* Section Headers */
    .section-header, .drill-down-header {
        background-color: #1a1f3a !important;
        border: 2px solid #00e5ff !important;
        border-radius: 14px !important;
        padding: 2rem !important;
        margin: 2rem 0 1.5rem 0 !important;
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.35), inset 0 0 20px rgba(0, 229, 255, 0.08) !important;
        transition: all 0.3s ease !important;
    }
    
    .section-header h2, .section-header h3, .drill-down-header h2 {
        color: #ffffff !important;
        font-size: 2rem !important;
        margin: 0 !important;
        font-weight: 700 !important;
    }
    
    /* Expanders */
    [data-testid="stExpander"] {
        background-color: #1a1f3a !important;
        border: 1px solid #2a3050 !important;
        border-radius: 10px !important;
    }
    
    [data-testid="stExpanderDetails"] {
        background-color: #141829 !important;
        padding: 1rem !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1a1f3a !important;
        color: #00e5ff !important;
        border: 1.5px solid #00e5ff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.2) !important;
        font-size: 0.85rem !important;
    }
    
    .stButton > button:hover {
        background-color: #00e5ff !important;
        color: #0a0e27 !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.5) !important;
    }
    
    /* Metrics */
    [data-testid="metric-container"] {
        background-color: #1a1f3a !important;
        border: 1px solid #2a3050 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
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
    
    /* Hide accessibility labels */
    [aria-label="keyboard_double"], label {
        display: none !important;
    }
    
    hr {
        border-color: #2a3050 !important;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - EXPANDABLE FILTER SECTIONS
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### Advanced Filters")
    
    # Program & Status
    with st.expander("📚 Program & Status", expanded=True):
        st.markdown("**Program**")
        prog_col1, prog_col2, prog_col3 = st.columns([1,1,1])
        if prog_col1.button("JP", use_container_width=True, key="btn_jp"):
            st.session_state.selected_programs ^= {"JP"}
        if prog_col2.button("PY", use_container_width=True, key="btn_py"):
            st.session_state.selected_programs ^= {"PY"}
        if prog_col3.button("SY", use_container_width=True, key="btn_sy"):
            st.session_state.selected_programs ^= {"SY"}
        
        st.markdown("**Status**")
        status_col1, status_col2 = st.columns(2)
        if status_col1.button("Allocated", key="btn_allocated"):
            st.session_state.selected_status ^= {"Allocated"}
        if status_col2.button("Pending", key="btn_pending"):
            st.session_state.selected_status ^= {"Pending"}
        
        status_col3, status_col4 = st.columns(2)
        if status_col3.button("Not Placed", key="btn_notplaced"):
            st.session_state.selected_status ^= {"Not Placed"}
        if status_col4.button("Waitlist", key="btn_waitlist"):
            st.session_state.selected_status ^= {"On Waitlist"}
    
    # Demographics
    with st.expander("👥 Demographics"):
        st.markdown("**ATSI (Aboriginal/Torres Strait Islander)**")
        atsi_col1, atsi_col2 = st.columns(2)
        if atsi_col1.button("Yes", key="btn_atsi_yes"):
            st.session_state.selected_atsi ^= {"Yes"}
        if atsi_col2.button("No", key="btn_atsi_no"):
            st.session_state.selected_atsi ^= {"No"}
        
        st.markdown("**EALD (English as Additional Language)**")
        eald_col1, eald_col2 = st.columns(2)
        if eald_col1.button("Yes", key="btn_eald_yes"):
            st.session_state.selected_eald ^= {"Yes"}
        if eald_col2.button("No", key="btn_eald_no"):
            st.session_state.selected_eald ^= {"No"}
    
    # Attendance
    with st.expander("📅 Attendance"):
        att_col1, att_col2, att_col3 = st.columns(3)
        if att_col1.button("Full-time", key="btn_fulltime"):
            st.session_state.selected_attendance ^= {"Full-time"}
        if att_col2.button("Part-time", key="btn_parttime"):
            st.session_state.selected_attendance ^= {"Part-time"}
        if att_col3.button("Irregular", key="btn_irregular"):
            st.session_state.selected_attendance ^= {"Irregular"}
    
    # Disability Support
    with st.expander("♿ Disability Support"):
        st.markdown("**SWD (Students with Disabilities)**")
        swd_col1, swd_col2 = st.columns(2)
        if swd_col1.button("Yes", key="btn_swd_yes"):
            st.session_state.selected_swd ^= {"Yes"}
        if swd_col2.button("No", key="btn_swd_no"):
            st.session_state.selected_swd ^= {"No"}
        
        st.markdown("**Disability Type**")
        dis_col1, dis_col2 = st.columns(2)
        
        if dis_col1.button("ASD", key="btn_asd"):
            st.session_state.selected_disability ^= {"ASD"}
        if dis_col2.button("ADHD", key="btn_adhd"):
            st.session_state.selected_disability ^= {"ADHD"}
        
        dis_col3, dis_col4 = st.columns(2)
        if dis_col3.button("Learning", key="btn_learning"):
            st.session_state.selected_disability ^= {"Learning Disability"}
        if dis_col4.button("Physical", key="btn_physical"):
            st.session_state.selected_disability ^= {"Physical"}
        
        dis_col5, dis_col6 = st.columns(2)
        if dis_col5.button("Hearing", key="btn_hearing"):
            st.session_state.selected_disability ^= {"Hearing"}
        if dis_col6.button("Vision", key="btn_vision"):
            st.session_state.selected_disability ^= {"Vision"}
    
    # Behaviour & Support
    with st.expander("⚠️ Behaviour & Support"):
        st.markdown("**Behaviour Concerns**")
        beh_col1, beh_col2 = st.columns(2)
        if beh_col1.button("None", key="btn_beh_none"):
            st.session_state.selected_behaviour ^= {"None"}
        if beh_col2.button("Mild", key="btn_beh_mild"):
            st.session_state.selected_behaviour ^= {"Mild"}
        
        beh_col3, beh_col4 = st.columns(2)
        if beh_col3.button("Moderate", key="btn_beh_moderate"):
            st.session_state.selected_behaviour ^= {"Moderate"}
        if beh_col4.button("Severe", key="btn_beh_severe"):
            st.session_state.selected_behaviour ^= {"Severe"}
        
        st.markdown("**Referral Type**")
        ref_col1, ref_col2 = st.columns(2)
        if ref_col1.button("First Time", key="btn_ref_first"):
            st.session_state.selected_referral ^= {"First"}
        if ref_col2.button("Multiple", key="btn_ref_multiple"):
            st.session_state.selected_referral ^= {"Multiple"}
    
    # Partnership
    with st.expander("🤝 Partnership Area"):
        partner_options = ["Inner West", "Adelaide Prospect", "Greenhill South", "Holdfast", "Mitcham Hills"]
        for i, opt in enumerate(partner_options):
            if (i % 2) == 0:
                col1, col2 = st.columns(2)
            if (i % 2) == 0:
                if col1.button(opt, key=f"btn_partner_{opt}"):
                    st.session_state.selected_partnership ^= {opt}
            else:
                if col2.button(opt, key=f"btn_partner_{opt}"):
                    st.session_state.selected_partnership ^= {opt}
    
    st.markdown("---")
    st.markdown("### Data Management")
    
    uploaded_file = st.file_uploader("Upload Excel", type=['xlsx', 'xls', 'csv'])
    if st.button("Export Data", use_container_width=True):
        st.info("Preparing download...")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

# Main Title
st.markdown("""
    <div class="main-title">
        <h1>Allocation Dashboard</h1>
        <p>Comprehensive student placement analytics and management</p>
    </div>
""", unsafe_allow_html=True)

# Summary Metrics
st.markdown("""
    <div class="section-header">
        <h2>Summary Metrics</h2>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total", "145")
with col2:
    st.metric("Allocated", "112")
with col3:
    st.metric("Pending", "28")
with col4:
    st.metric("ATSI", "42")
with col5:
    st.metric("SWD", "58")
with col6:
    st.metric("EALD", "31")

st.markdown("---")

# Current Filters Display
with st.expander("🔍 Active Filters (Click to see)", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"**Program:** {', '.join(sorted(st.session_state.selected_programs)) or 'None'}")
        st.caption(f"**Status:** {', '.join(sorted(st.session_state.selected_status)) or 'None'}")
    with col2:
        st.caption(f"**ATSI:** {', '.join(sorted(st.session_state.selected_atsi)) or 'None'}")
        st.caption(f"**SWD:** {', '.join(sorted(st.session_state.selected_swd)) or 'None'}")
    with col3:
        st.caption(f"**Attendance:** {', '.join(sorted(st.session_state.selected_attendance)) or 'None'}")
        st.caption(f"**Partnership:** {', '.join(sorted(st.session_state.selected_partnership)) or 'None'}")

st.markdown("---")

# Tabs for different views
tab1, tab2, tab3, tab4, tab5 = st.tabs(["All Students", "By Demographics", "By Disability", "By Partnership", "Analytics"])

with tab1:
    st.markdown("""
        <div class="drill-down-header">
            <h2>All Students</h2>
        </div>
    """, unsafe_allow_html=True)
    
    df_students = pd.DataFrame({
        'Student': ['John Smith', 'Mary Jones', 'Sarah Lee', 'David Chen', 'Emma Wilson', 'Alex Brown', 'Sophie Green', 'Tom White'],
        'Program': ['JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY'],
        'Status': ['Allocated', 'Allocated', 'Pending', 'Allocated', 'Not Placed', 'Allocated', 'Pending', 'Allocated'],
        'ATSI': ['No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No'],
        'SWD': ['Yes', 'No', 'Yes', 'No', 'Yes', 'Yes', 'No', 'No'],
        'Disability': ['ASD', 'None', 'ADHD', 'None', 'Learning', 'ASD', 'None', 'None'],
        'Attendance': ['Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time', 'Part-time', 'Full-time', 'Full-time'],
        'Partnership': ['Inner West', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills', 'Inner West', 'Adelaide Prospect']
    })
    
    st.dataframe(df_students, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Demographics Breakdown</h2>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure(data=[go.Pie(
            labels=['ATSI', 'Non-ATSI'],
            values=[42, 103],
            marker=dict(colors=['#00e5ff', '#ff6b6b'])
        )])
        fig.update_layout(
            title='ATSI Status',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = go.Figure(data=[go.Pie(
            labels=['EALD', 'Non-EALD'],
            values=[31, 114],
            marker=dict(colors=['#00e5ff', '#ffd93d'])
        )])
        fig.update_layout(
            title='EALD Status',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins')
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Disability Support Breakdown</h2>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure(data=[go.Pie(
            labels=['SWD', 'No Support Need'],
            values=[58, 87],
            marker=dict(colors=['#00e5ff', '#10b981'])
        )])
        fig.update_layout(
            title='Students with Disabilities',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = go.Figure(data=[go.Bar(
            x=['ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'],
            y=[18, 14, 16, 5, 3, 2],
            marker_color='#00e5ff'
        )])
        fig.update_layout(
            title='Disability Types',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins'),
            xaxis_title='Type',
            yaxis_title='Count'
        )
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Partnership Area Distribution</h2>
        </div>
    """, unsafe_allow_html=True)
    
    m = folium.Map(location=[-34.93, 138.60], zoom_start=11, tiles='OpenStreetMap')
    
    partnerships_data = {
        'Inner West': {'coords': [-34.90, 138.54], 'count': 28},
        'Adelaide Prospect': {'coords': [-34.85, 138.60], 'count': 35},
        'Greenhill South': {'coords': [-34.98, 138.63], 'count': 22},
        'Holdfast': {'coords': [-35.02, 138.52], 'count': 18},
        'Mitcham Hills': {'coords': [-34.99, 138.65], 'count': 15}
    }
    
    for partnership, data in partnerships_data.items():
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

with tab5:
    st.markdown("""
        <div class="drill-down-header">
            <h2>Analytics & Trends</h2>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure(data=[
            go.Bar(x=['JP', 'PY', 'SY'], y=[45, 55, 12], marker_color='#00e5ff')
        ])
        fig.update_layout(
            title='Allocations by Program',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins'),
            xaxis_title='Program',
            yaxis_title='Count'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'],
            y=[18, 22, 25, 28, 32],
            mode='lines+markers',
            line=dict(color='#00e5ff', width=3),
            marker=dict(size=8)
        ))
        fig.update_layout(
            title='Allocation Trends',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Poppins'),
            xaxis_title='Week',
            yaxis_title='Allocations'
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("CLC-LBU Allocation Dashboard • Modern analytics platform")
