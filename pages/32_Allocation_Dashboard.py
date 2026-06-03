import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

# Initialize session state
if 'filter_states' not in st.session_state:
    st.session_state.filter_states = {
        'programs': {'JP', 'PY', 'SY'},
        'status': {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'},
        'atsi': {'Yes', 'No'},
        'eald': {'Yes', 'No'},
        'attendance': {'Full-time', 'Part-time', 'Irregular'},
        'swd': {'Yes', 'No'},
        'disability': {'ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'},
        'behaviour': {'None', 'Mild', 'Moderate', 'Severe'},
        'partnership': {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
    }

# CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
    * {
        font-family: 'Poppins', sans-serif !important;
    }
    body, [data-testid="stAppViewContainer"] {
        background-color: #0a0e27 !important;
    }
    .main {
        background-color: #0a0e27 !important;
        padding: 2rem !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #ffffff !important;
    }
    .metric-box {
        background-color: #1a1f3a !important;
        border: 2px solid #00e5ff !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        text-align: center !important;
    }
    .metric-value {
        color: #00ff00 !important;
        font-size: 2.8rem !important;
        font-weight: 800 !important;
    }
    .metric-label {
        color: #00e5ff !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        margin-top: 0.5rem !important;
    }
    .main-title {
        background: linear-gradient(135deg, #1a1f3a 0%, #2a3050 100%);
        border: 2px solid #00e5ff;
        border-radius: 16px;
        padding: 3.5rem 4rem;
        margin-bottom: 3rem;
        box-shadow: 0 0 40px rgba(0, 229, 255, 0.4);
        text-align: center;
    }
    .main-title h1 {
        font-size: 3.5rem !important;
        color: #ffffff !important;
        margin: 0 !important;
        font-weight: 800 !important;
    }
    .main-title p {
        color: #00e5ff !important;
        font-size: 1.2rem !important;
        margin: 1rem 0 0 0 !important;
    }
    .section-title {
        background-color: #1a1f3a !important;
        border: 2px solid #00e5ff !important;
        border-radius: 14px !important;
        padding: 2rem !important;
        margin: 2rem 0 1.5rem 0 !important;
    }
    .section-title h2 {
        color: #ffffff !important;
        font-size: 2rem !important;
        margin: 0 !important;
        font-weight: 700 !important;
    }
    .stButton > button {
        background-color: #1a1f3a !important;
        color: #00e5ff !important;
        border: 2px solid #00e5ff !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1rem !important;
        font-size: 0.9rem !important;
    }
    .stButton > button:hover {
        background-color: #00e5ff !important;
        color: #0a0e27 !important;
    }
    [data-testid="metric-container"] {
        background-color: #1a1f3a !important;
        border: 2px solid #00e5ff !important;
        border-radius: 12px !important;
        padding: 2rem !important;
    }
    [data-testid="metric-value"] {
        color: #00ff00 !important;
        font-size: 3rem !important;
        font-weight: 800 !important;
    }
    [data-testid="metric-label"] {
        color: #00e5ff !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    [data-baseweb="tab"] {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    [aria-selected="true"] {
        color: #00e5ff !important;
        border-bottom: 3px solid #00e5ff !important;
    }
    hr {
        border-color: #2a3050 !important;
        margin: 2rem 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - ALL FILTERS HERE
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## Filters")
    st.markdown("---")
    
    # PROGRAM
    st.markdown("### Program")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="prog_all", use_container_width=True):
            st.session_state.filter_states['programs'] = {'JP', 'PY', 'SY'}
    with col2:
        if st.button("Clear All", key="prog_clear", use_container_width=True):
            st.session_state.filter_states['programs'] = set()
    
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", key="jp", use_container_width=True):
        st.session_state.filter_states['programs'] ^= {"JP"}
    if p2.button("PY", key="py", use_container_width=True):
        st.session_state.filter_states['programs'] ^= {"PY"}
    if p3.button("SY", key="sy", use_container_width=True):
        st.session_state.filter_states['programs'] ^= {"SY"}
    
    st.markdown("---")
    
    # STATUS
    st.markdown("### Status")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="status_all", use_container_width=True):
            st.session_state.filter_states['status'] = {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'}
    with col2:
        if st.button("Clear All", key="status_clear", use_container_width=True):
            st.session_state.filter_states['status'] = set()
    
    s1, s2 = st.columns(2)
    if s1.button("Allocated", key="alloc", use_container_width=True):
        st.session_state.filter_states['status'] ^= {"Allocated"}
    if s2.button("Pending", key="pend", use_container_width=True):
        st.session_state.filter_states['status'] ^= {"Pending"}
    
    s3, s4 = st.columns(2)
    if s3.button("Not Placed", key="notpl", use_container_width=True):
        st.session_state.filter_states['status'] ^= {"Not Placed"}
    if s4.button("Waitlist", key="wait", use_container_width=True):
        st.session_state.filter_states['status'] ^= {"On Waitlist"}
    
    st.markdown("---")
    
    # DEMOGRAPHICS
    st.markdown("### ATSI")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="atsi_all", use_container_width=True):
            st.session_state.filter_states['atsi'] = {'Yes', 'No'}
    with col2:
        if st.button("Clear All", key="atsi_clear", use_container_width=True):
            st.session_state.filter_states['atsi'] = set()
    
    a1, a2 = st.columns(2)
    if a1.button("Yes", key="atsi_y", use_container_width=True):
        st.session_state.filter_states['atsi'] ^= {"Yes"}
    if a2.button("No", key="atsi_n", use_container_width=True):
        st.session_state.filter_states['atsi'] ^= {"No"}
    
    st.markdown("---")
    
    st.markdown("### EALD")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="eald_all", use_container_width=True):
            st.session_state.filter_states['eald'] = {'Yes', 'No'}
    with col2:
        if st.button("Clear All", key="eald_clear", use_container_width=True):
            st.session_state.filter_states['eald'] = set()
    
    e1, e2 = st.columns(2)
    if e1.button("Yes", key="eald_y", use_container_width=True):
        st.session_state.filter_states['eald'] ^= {"Yes"}
    if e2.button("No", key="eald_n", use_container_width=True):
        st.session_state.filter_states['eald'] ^= {"No"}
    
    st.markdown("---")
    
    # ATTENDANCE
    st.markdown("### Attendance")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="att_all", use_container_width=True):
            st.session_state.filter_states['attendance'] = {'Full-time', 'Part-time', 'Irregular'}
    with col2:
        if st.button("Clear All", key="att_clear", use_container_width=True):
            st.session_state.filter_states['attendance'] = set()
    
    at1, at2, at3 = st.columns(3)
    if at1.button("Full-time", key="ft", use_container_width=True):
        st.session_state.filter_states['attendance'] ^= {"Full-time"}
    if at2.button("Part-time", key="pt", use_container_width=True):
        st.session_state.filter_states['attendance'] ^= {"Part-time"}
    if at3.button("Irregular", key="irr", use_container_width=True):
        st.session_state.filter_states['attendance'] ^= {"Irregular"}
    
    st.markdown("---")
    
    # DISABILITY
    st.markdown("### SWD")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="swd_all", use_container_width=True):
            st.session_state.filter_states['swd'] = {'Yes', 'No'}
    with col2:
        if st.button("Clear All", key="swd_clear", use_container_width=True):
            st.session_state.filter_states['swd'] = set()
    
    sw1, sw2 = st.columns(2)
    if sw1.button("Yes", key="swd_y", use_container_width=True):
        st.session_state.filter_states['swd'] ^= {"Yes"}
    if sw2.button("No", key="swd_n", use_container_width=True):
        st.session_state.filter_states['swd'] ^= {"No"}
    
    st.markdown("---")
    
    st.markdown("### Disability Type")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="dis_all", use_container_width=True):
            st.session_state.filter_states['disability'] = {'ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'}
    with col2:
        if st.button("Clear All", key="dis_clear", use_container_width=True):
            st.session_state.filter_states['disability'] = set()
    
    d1, d2 = st.columns(2)
    if d1.button("ASD", key="asd", use_container_width=True):
        st.session_state.filter_states['disability'] ^= {"ASD"}
    if d2.button("ADHD", key="adhd", use_container_width=True):
        st.session_state.filter_states['disability'] ^= {"ADHD"}
    
    d3, d4 = st.columns(2)
    if d3.button("Learning", key="learn", use_container_width=True):
        st.session_state.filter_states['disability'] ^= {"Learning"}
    if d4.button("Physical", key="phys", use_container_width=True):
        st.session_state.filter_states['disability'] ^= {"Physical"}
    
    d5, d6 = st.columns(2)
    if d5.button("Hearing", key="hear", use_container_width=True):
        st.session_state.filter_states['disability'] ^= {"Hearing"}
    if d6.button("Vision", key="vis", use_container_width=True):
        st.session_state.filter_states['disability'] ^= {"Vision"}
    
    st.markdown("---")
    
    # BEHAVIOUR
    st.markdown("### Behaviour Level")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="beh_all", use_container_width=True):
            st.session_state.filter_states['behaviour'] = {'None', 'Mild', 'Moderate', 'Severe'}
    with col2:
        if st.button("Clear All", key="beh_clear", use_container_width=True):
            st.session_state.filter_states['behaviour'] = set()
    
    b1, b2 = st.columns(2)
    if b1.button("None", key="beh_n", use_container_width=True):
        st.session_state.filter_states['behaviour'] ^= {"None"}
    if b2.button("Mild", key="beh_m", use_container_width=True):
        st.session_state.filter_states['behaviour'] ^= {"Mild"}
    
    b3, b4 = st.columns(2)
    if b3.button("Moderate", key="beh_mo", use_container_width=True):
        st.session_state.filter_states['behaviour'] ^= {"Moderate"}
    if b4.button("Severe", key="beh_s", use_container_width=True):
        st.session_state.filter_states['behaviour'] ^= {"Severe"}
    
    st.markdown("---")
    
    # PARTNERSHIP
    st.markdown("### Partnership Area")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="par_all", use_container_width=True):
            st.session_state.filter_states['partnership'] = {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
    with col2:
        if st.button("Clear All", key="par_clear", use_container_width=True):
            st.session_state.filter_states['partnership'] = set()
    
    opts = ["Inner West", "Adelaide Prospect", "Greenhill South", "Holdfast", "Mitcham Hills"]
    for i, opt in enumerate(opts):
        if (i % 2) == 0:
            co1, co2 = st.columns(2)
        if (i % 2) == 0:
            if co1.button(opt, key=f"par_{opt}", use_container_width=True):
                st.session_state.filter_states['partnership'] ^= {opt}
        else:
            if co2.button(opt, key=f"par_{opt}", use_container_width=True):
                st.session_state.filter_states['partnership'] ^= {opt}
    
    st.markdown("---")
    
    # DASHBOARD VIEW
    st.markdown("### Dashboard View")
    selected_view = st.radio(
        "Select View",
        ["All Students", "By Demographics", "By Disability", "By Partnership", "Analytics"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### Data Management")
    st.file_uploader("Upload Excel", type=['xlsx', 'xls', 'csv'])
    st.button("Export Data", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD - CLEAN
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="main-title"><h1>Allocation Dashboard</h1><p>Comprehensive student placement analytics</p></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title"><h2>Summary Metrics</h2></div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1: st.metric("Total", "145")
with col2: st.metric("Allocated", "112")
with col3: st.metric("Pending", "28")
with col4: st.metric("ATSI", "42")
with col5: st.metric("SWD", "58")
with col6: st.metric("EALD", "31")

st.markdown("---")

# DISPLAY SELECTED VIEW
if selected_view == "All Students":
    st.markdown('<div class="section-title"><h2>All Students</h2></div>', unsafe_allow_html=True)
    df = pd.DataFrame({
        'Student': ['John Smith', 'Mary Jones', 'Sarah Lee', 'David Chen', 'Emma Wilson'],
        'Program': ['JP', 'PY', 'SY', 'JP', 'PY'],
        'Status': ['Allocated', 'Allocated', 'Pending', 'Allocated', 'Not Placed'],
        'ATSI': ['No', 'Yes', 'No', 'Yes', 'No'],
        'SWD': ['Yes', 'No', 'Yes', 'No', 'Yes'],
        'Disability': ['ASD', 'None', 'ADHD', 'None', 'Learning'],
        'Attendance': ['Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time'],
        'Partnership': ['Inner West', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast']
    })
    st.dataframe(df, use_container_width=True, hide_index=True)

elif selected_view == "By Demographics":
    st.markdown('<div class="section-title"><h2>Demographics Breakdown</h2></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(data=[go.Pie(labels=['ATSI', 'Non-ATSI'], values=[42, 103], marker=dict(colors=['#00e5ff', '#ff6b6b']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = go.Figure(data=[go.Pie(labels=['EALD', 'Non-EALD'], values=[31, 114], marker=dict(colors=['#00e5ff', '#ffd93d']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)

elif selected_view == "By Disability":
    st.markdown('<div class="section-title"><h2>Disability Support</h2></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(data=[go.Pie(labels=['SWD', 'No Support'], values=[58, 87], marker=dict(colors=['#00e5ff', '#10b981']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = go.Figure(data=[go.Bar(x=['ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'], y=[18, 14, 16, 5, 3, 2], marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14), xaxis_title='Type', yaxis_title='Count')
        st.plotly_chart(fig, use_container_width=True)

elif selected_view == "By Partnership":
    st.markdown('<div class="section-title"><h2>Partnership Distribution</h2></div>', unsafe_allow_html=True)
    m = folium.Map(location=[-34.93, 138.60], zoom_start=11, tiles='OpenStreetMap')
    partnerships = {'Inner West': {'coords': [-34.90, 138.54], 'count': 28}, 'Adelaide Prospect': {'coords': [-34.85, 138.60], 'count': 35}, 'Greenhill South': {'coords': [-34.98, 138.63], 'count': 22}, 'Holdfast': {'coords': [-35.02, 138.52], 'count': 18}, 'Mitcham Hills': {'coords': [-34.99, 138.65], 'count': 15}}
    for p, d in partnerships.items():
        folium.CircleMarker(location=d['coords'], radius=15, popup=f"{p}: {d['count']}", color='#00e5ff', fill=True, fillColor='#00e5ff', fillOpacity=0.7, weight=2).add_to(m)
    st_folium(m, width=1200, height=500)
    st.markdown("---")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("Inner West", "28")
    with c2: st.metric("Adelaide Prospect", "35")
    with c3: st.metric("Greenhill South", "22")
    with c4: st.metric("Holdfast", "18")
    with c5: st.metric("Mitcham Hills", "15")

elif selected_view == "Analytics":
    st.markdown('<div class="section-title"><h2>Analytics</h2></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(data=[go.Bar(x=['JP', 'PY', 'SY'], y=[45, 55, 12], marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = go.Figure(data=[go.Scatter(x=['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'], y=[18, 22, 25, 28, 32], mode='lines+markers', line=dict(color='#00e5ff', width=3), marker=dict(size=8))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-weight: 600;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
