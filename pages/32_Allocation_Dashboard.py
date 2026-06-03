import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

# Initialize session state
defaults = {
    'selected_programs': {'JP', 'PY', 'SY'},
    'selected_status': {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'},
    'selected_atsi': {'Yes', 'No'},
    'selected_attendance': {'Full-time', 'Part-time', 'Irregular'},
    'selected_swd': {'Yes', 'No'},
    'selected_disability': {'ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'},
    'selected_eald': {'Yes', 'No'},
    'selected_behaviour': {'None', 'Mild', 'Moderate', 'Severe'},
    'selected_referral': {'First', 'Multiple'},
    'selected_partnership': {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# DARK THEME CSS - MAXIMUM CONTRAST AND CLARITY
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif !important;
    }
    
    body, html, [data-testid="stAppViewContainer"] {
        background-color: #0a0e27 !important;
    }
    
    .main {
        background-color: #0a0e27 !important;
        padding: 2rem !important;
    }
    
    /* MAXIMUM CONTRAST TEXT */
    p, span, div, label {
        color: #ffffff !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* Metric cards - BRIGHT VALUES */
    [data-testid="metric-container"] {
        background-color: #1a1f3a !important;
        border: 2px solid #00e5ff !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.3) !important;
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
        font-weight: 500 !important;
    }
    
    .section-header {
        background-color: #1a1f3a !important;
        border: 2px solid #00e5ff !important;
        border-radius: 14px !important;
        padding: 2rem !important;
        margin: 2rem 0 1.5rem 0 !important;
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.35) !important;
    }
    
    .section-header h2 {
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
        padding: 0.6rem 1.2rem !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #00e5ff !important;
        color: #0a0e27 !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.5) !important;
    }
    
    [data-testid="stExpander"] {
        background-color: #1a1f3a !important;
        border: 1px solid #2a3050 !important;
        border-radius: 10px !important;
        margin-bottom: 1rem !important;
    }
    
    [data-testid="stExpanderDetails"] {
        background-color: #141829 !important;
        padding: 1.5rem !important;
    }
    
    hr {
        border-color: #2a3050 !important;
        margin: 2rem 0 !important;
    }
    
    [data-baseweb="tab"] {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    [aria-selected="true"] {
        color: #00e5ff !important;
        border-bottom: 3px solid #00e5ff !important;
    }
    
    /* Hide problematic elements */
    [aria-label*="arrow"], [aria-label*="keyboard"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# SIDEBAR FILTERS
with st.sidebar:
    st.markdown("### Advanced Filters")
    st.markdown("---")
    
    with st.expander("Program and Status", expanded=True):
        st.markdown("**Program**")
        p1, p2, p3 = st.columns(3)
        if p1.button("JP", key="jp", use_container_width=True): st.session_state.selected_programs ^= {"JP"}
        if p2.button("PY", key="py", use_container_width=True): st.session_state.selected_programs ^= {"PY"}
        if p3.button("SY", key="sy", use_container_width=True): st.session_state.selected_programs ^= {"SY"}
        
        st.markdown("**Status**")
        s1, s2 = st.columns(2)
        if s1.button("Allocated", key="alloc", use_container_width=True): st.session_state.selected_status ^= {"Allocated"}
        if s2.button("Pending", key="pend", use_container_width=True): st.session_state.selected_status ^= {"Pending"}
        s3, s4 = st.columns(2)
        if s3.button("Not Placed", key="notpl", use_container_width=True): st.session_state.selected_status ^= {"Not Placed"}
        if s4.button("Waitlist", key="wait", use_container_width=True): st.session_state.selected_status ^= {"On Waitlist"}
    
    with st.expander("Demographics"):
        st.markdown("**ATSI**")
        a1, a2 = st.columns(2)
        if a1.button("Yes", key="atsi_y", use_container_width=True): st.session_state.selected_atsi ^= {"Yes"}
        if a2.button("No", key="atsi_n", use_container_width=True): st.session_state.selected_atsi ^= {"No"}
        
        st.markdown("**EALD**")
        e1, e2 = st.columns(2)
        if e1.button("Yes", key="eald_y", use_container_width=True): st.session_state.selected_eald ^= {"Yes"}
        if e2.button("No", key="eald_n", use_container_width=True): st.session_state.selected_eald ^= {"No"}
    
    with st.expander("Attendance"):
        at1, at2, at3 = st.columns(3)
        if at1.button("Full-time", key="ft", use_container_width=True): st.session_state.selected_attendance ^= {"Full-time"}
        if at2.button("Part-time", key="pt", use_container_width=True): st.session_state.selected_attendance ^= {"Part-time"}
        if at3.button("Irregular", key="irr", use_container_width=True): st.session_state.selected_attendance ^= {"Irregular"}
    
    with st.expander("Disability Support"):
        st.markdown("**SWD**")
        sw1, sw2 = st.columns(2)
        if sw1.button("Yes", key="swd_y", use_container_width=True): st.session_state.selected_swd ^= {"Yes"}
        if sw2.button("No", key="swd_n", use_container_width=True): st.session_state.selected_swd ^= {"No"}
        
        st.markdown("**Type**")
        d1, d2 = st.columns(2)
        if d1.button("ASD", key="asd", use_container_width=True): st.session_state.selected_disability ^= {"ASD"}
        if d2.button("ADHD", key="adhd", use_container_width=True): st.session_state.selected_disability ^= {"ADHD"}
        d3, d4 = st.columns(2)
        if d3.button("Learning", key="learn", use_container_width=True): st.session_state.selected_disability ^= {"Learning"}
        if d4.button("Physical", key="phys", use_container_width=True): st.session_state.selected_disability ^= {"Physical"}
        d5, d6 = st.columns(2)
        if d5.button("Hearing", key="hear", use_container_width=True): st.session_state.selected_disability ^= {"Hearing"}
        if d6.button("Vision", key="vis", use_container_width=True): st.session_state.selected_disability ^= {"Vision"}
    
    with st.expander("Behaviour"):
        st.markdown("**Level**")
        b1, b2 = st.columns(2)
        if b1.button("None", key="beh_n", use_container_width=True): st.session_state.selected_behaviour ^= {"None"}
        if b2.button("Mild", key="beh_m", use_container_width=True): st.session_state.selected_behaviour ^= {"Mild"}
        b3, b4 = st.columns(2)
        if b3.button("Moderate", key="beh_mo", use_container_width=True): st.session_state.selected_behaviour ^= {"Moderate"}
        if b4.button("Severe", key="beh_s", use_container_width=True): st.session_state.selected_behaviour ^= {"Severe"}
    
    with st.expander("Partnership"):
        opts = ["Inner West", "Adelaide Prospect", "Greenhill South", "Holdfast", "Mitcham Hills"]
        for i, opt in enumerate(opts):
            if (i % 2) == 0:
                co1, co2 = st.columns(2)
            if (i % 2) == 0:
                if co1.button(opt, key=f"par_{opt}", use_container_width=True): st.session_state.selected_partnership ^= {opt}
            else:
                if co2.button(opt, key=f"par_{opt}", use_container_width=True): st.session_state.selected_partnership ^= {opt}
    
    st.markdown("---")
    st.markdown("### Data Management")
    st.file_uploader("Upload Excel", type=['xlsx', 'xls', 'csv'])
    st.button("Export Data", use_container_width=True)

# MAIN DASHBOARD
st.markdown('<div class="main-title"><h1>Allocation Dashboard</h1><p>Comprehensive student placement analytics</p></div>', unsafe_allow_html=True)

st.markdown('<div class="section-header"><h2>Summary Metrics</h2></div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1: st.metric("Total", "145")
with col2: st.metric("Allocated", "112")
with col3: st.metric("Pending", "28")
with col4: st.metric("ATSI", "42")
with col5: st.metric("SWD", "58")
with col6: st.metric("EALD", "31")

st.markdown("---")

# Active Filters - NOT in expander
st.markdown('<div style="background-color: #1a1f3a; border: 2px solid #00e5ff; border-radius: 10px; padding: 1.5rem; margin: 2rem 0;"><h3 style="color: #ffffff; margin-top: 0;">Active Filters</h3></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Program:** {', '.join(sorted(st.session_state.selected_programs))}")
    st.markdown(f"**Status:** {', '.join(sorted(st.session_state.selected_status))}")
with col2:
    st.markdown(f"**ATSI:** {', '.join(sorted(st.session_state.selected_atsi))}")
    st.markdown(f"**SWD:** {', '.join(sorted(st.session_state.selected_swd))}")
with col3:
    st.markdown(f"**Attendance:** {', '.join(sorted(st.session_state.selected_attendance))}")
    st.markdown(f"**Partnership:** {', '.join(sorted(st.session_state.selected_partnership))}")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["All Students", "By Demographics", "By Disability", "By Partnership", "Analytics"])

with tab1:
    st.markdown('<div class="section-header"><h2>All Students</h2></div>', unsafe_allow_html=True)
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

with tab2:
    st.markdown('<div class="section-header"><h2>Demographics Breakdown</h2></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(data=[go.Pie(labels=['ATSI', 'Non-ATSI'], values=[42, 103], marker=dict(colors=['#00e5ff', '#ff6b6b']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = go.Figure(data=[go.Pie(labels=['EALD', 'Non-EALD'], values=[31, 114], marker=dict(colors=['#00e5ff', '#ffd93d']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown('<div class="section-header"><h2>Disability Support</h2></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(data=[go.Pie(labels=['SWD', 'No Support'], values=[58, 87], marker=dict(colors=['#00e5ff', '#10b981']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = go.Figure(data=[go.Bar(x=['ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'], y=[18, 14, 16, 5, 3, 2], marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14), xaxis_title='Type', yaxis_title='Count')
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown('<div class="section-header"><h2>Partnership Distribution</h2></div>', unsafe_allow_html=True)
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

with tab5:
    st.markdown('<div class="section-header"><h2>Analytics</h2></div>', unsafe_allow_html=True)
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
