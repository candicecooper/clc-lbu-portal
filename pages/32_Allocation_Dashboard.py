import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium
from datetime import datetime

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

if 'selected_view' not in st.session_state:
    st.session_state.selected_view = "Dashboard Overview"

# SAMPLE DATA
@st.cache_data
def get_student_data():
    data = {
        'Student': ['John Smith', 'Mary Jones', 'Sarah Lee', 'David Chen', 'Emma Wilson', 'Alex Brown', 'Sophie Green', 'Tom White', 'Lisa Anderson', 'James Taylor', 'Rachel Martin', 'Chris Davis', 'Katie Wilson', 'Michael Brown', 'Jessica Taylor'],
        'Program': ['JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY', 'SY'],
        'Status': ['Allocated', 'Allocated', 'Pending', 'Allocated', 'Not Placed', 'Allocated', 'Pending', 'Allocated', 'Allocated', 'On Waitlist', 'Allocated', 'Pending', 'Allocated', 'Allocated', 'Not Placed'],
        'ATSI': ['No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'Yes', 'No'],
        'SWD': ['Yes', 'No', 'Yes', 'No', 'Yes', 'Yes', 'No', 'No', 'Yes', 'No', 'Yes', 'Yes', 'No', 'No', 'Yes'],
        'Disability': ['ASD', 'None', 'ADHD', 'None', 'Learning', 'ASD', 'None', 'None', 'ADHD', 'None', 'Physical', 'ASD', 'None', 'None', 'Hearing'],
        'Attendance': ['Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time', 'Part-time', 'Full-time', 'Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time', 'Full-time', 'Part-time', 'Full-time'],
        'EALD': ['No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No'],
        'Behaviour': ['None', 'Mild', 'Moderate', 'None', 'Severe', 'Mild', 'None', 'None', 'Mild', 'Moderate', 'None', 'Severe', 'Mild', 'None', 'Moderate'],
        'Partnership': ['Inner West', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast'],
        'Term': ['Term 2'] * 15
    }
    return pd.DataFrame(data)

def filter_data(df):
    filtered = df[
        (df['Program'].isin(st.session_state.filter_states['programs'])) &
        (df['Status'].isin(st.session_state.filter_states['status'])) &
        (df['ATSI'].isin(st.session_state.filter_states['atsi'])) &
        (df['EALD'].isin(st.session_state.filter_states['eald'])) &
        (df['Attendance'].isin(st.session_state.filter_states['attendance'])) &
        (df['SWD'].isin(st.session_state.filter_states['swd'])) &
        (df['Disability'].isin(st.session_state.filter_states['disability'])) &
        (df['Behaviour'].isin(st.session_state.filter_states['behaviour'])) &
        (df['Partnership'].isin(st.session_state.filter_states['partnership']))
    ]
    return filtered

all_students = get_student_data()
filtered_students = filter_data(all_students)

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
    hr {
        border-color: #2a3050 !important;
        margin: 2rem 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR FILTERS
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## Filters")
    st.markdown("---")
    
    # VIEW SELECTION
    st.markdown("### View")
    st.session_state.selected_view = st.radio(
        "Select Dashboard",
        ["Dashboard Overview", "All Students", "By Demographics", "By Disability", "By Partnership"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("## Filter Data")
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
    
    # ATSI
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
    
    # SWD
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
    
    # EALD
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
    
    # DISABILITY TYPE
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

# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="main-title"><h1>Allocation Dashboard</h1><p>Term 2, 2026 - Comprehensive Analytics</p></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title"><h2>Summary Metrics</h2></div>', unsafe_allow_html=True)

total = len(filtered_students)
allocated = len(filtered_students[filtered_students['Status'] == 'Allocated'])
pending = len(filtered_students[filtered_students['Status'] == 'Pending'])
atsi = len(filtered_students[filtered_students['ATSI'] == 'Yes'])
swd = len(filtered_students[filtered_students['SWD'] == 'Yes'])
eald = len(filtered_students[filtered_students['EALD'] == 'Yes'])

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1: st.metric("Total", total)
with col2: st.metric("Allocated", allocated)
with col3: st.metric("Pending", pending)
with col4: st.metric("ATSI", atsi)
with col5: st.metric("SWD", swd)
with col6: st.metric("EALD", eald)

st.markdown("---")

# DISPLAY VIEWS
if st.session_state.selected_view == "Dashboard Overview":
    st.markdown('<div class="section-title"><h2>Dashboard Overview - All Analytics</h2></div>', unsafe_allow_html=True)
    
    # Row 1
    col1, col2, col3 = st.columns(3)
    
    with col1:
        prog_counts = filtered_students['Program'].value_counts()
        fig = go.Figure(data=[go.Bar(x=prog_counts.index, y=prog_counts.values, marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="By Program", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        status_counts = filtered_students['Status'].value_counts()
        fig = go.Figure(data=[go.Bar(x=status_counts.index, y=status_counts.values, marker_color='#00ff00')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="By Status", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        att_counts = filtered_students['Attendance'].value_counts()
        fig = go.Figure(data=[go.Pie(labels=att_counts.index, values=att_counts.values, marker=dict(colors=['#00e5ff', '#ff6b6b', '#ffd93d']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="Attendance", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    # Row 2
    col1, col2, col3 = st.columns(3)
    
    with col1:
        atsi_counts = filtered_students['ATSI'].value_counts()
        fig = go.Figure(data=[go.Pie(labels=['ATSI', 'Non-ATSI'], values=[len(filtered_students[filtered_students['ATSI']=='Yes']), len(filtered_students[filtered_students['ATSI']=='No'])], marker=dict(colors=['#00e5ff', '#10b981']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="ATSI Status", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        swd_counts = filtered_students['SWD'].value_counts()
        fig = go.Figure(data=[go.Pie(labels=['SWD', 'Non-SWD'], values=[len(filtered_students[filtered_students['SWD']=='Yes']), len(filtered_students[filtered_students['SWD']=='No'])], marker=dict(colors=['#00e5ff', '#10b981']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="SWD Status", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        eald_counts = filtered_students['EALD'].value_counts()
        fig = go.Figure(data=[go.Pie(labels=['EALD', 'Non-EALD'], values=[len(filtered_students[filtered_students['EALD']=='Yes']), len(filtered_students[filtered_students['EALD']=='No'])], marker=dict(colors=['#00e5ff', '#ffd93d']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="EALD Status", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    # Row 3
    col1, col2 = st.columns(2)
    
    with col1:
        beh_counts = filtered_students['Behaviour'].value_counts()
        fig = go.Figure(data=[go.Bar(x=beh_counts.index, y=beh_counts.values, marker_color='#ff6b6b')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="By Behaviour Level", height=350, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        dis_counts = filtered_students[filtered_students['Disability'] != 'None']['Disability'].value_counts()
        if len(dis_counts) > 0:
            fig = go.Figure(data=[go.Bar(x=dis_counts.index, y=dis_counts.values, marker_color='#ffd93d')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=12), title="Disability Types", height=350, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

elif st.session_state.selected_view == "All Students":
    st.markdown('<div class="section-title"><h2>All Students</h2></div>', unsafe_allow_html=True)
    display_cols = ['Student', 'Program', 'Status', 'ATSI', 'SWD', 'EALD', 'Disability', 'Attendance', 'Behaviour', 'Partnership']
    st.dataframe(filtered_students[display_cols], use_container_width=True, hide_index=True)

elif st.session_state.selected_view == "By Demographics":
    st.markdown('<div class="section-title"><h2>Demographics Analysis</h2></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        atsi_counts = filtered_students['ATSI'].value_counts()
        fig = go.Figure(data=[go.Pie(labels=['ATSI', 'Non-ATSI'], values=[len(filtered_students[filtered_students['ATSI']=='Yes']), len(filtered_students[filtered_students['ATSI']=='No'])], marker=dict(colors=['#00e5ff', '#10b981']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        eald_counts = filtered_students['EALD'].value_counts()
        fig = go.Figure(data=[go.Pie(labels=['EALD', 'Non-EALD'], values=[len(filtered_students[filtered_students['EALD']=='Yes']), len(filtered_students[filtered_students['EALD']=='No'])], marker=dict(colors=['#00e5ff', '#ffd93d']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'))
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        prog_counts = filtered_students['Program'].value_counts()
        fig = go.Figure(data=[go.Bar(x=prog_counts.index, y=prog_counts.values, marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="By Program")
        st.plotly_chart(fig, use_container_width=True)

elif st.session_state.selected_view == "By Disability":
    st.markdown('<div class="section-title"><h2>Disability Support Analysis</h2></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        swd_counts = filtered_students['SWD'].value_counts()
        fig = go.Figure(data=[go.Pie(labels=['SWD', 'Non-SWD'], values=[len(filtered_students[filtered_students['SWD']=='Yes']), len(filtered_students[filtered_students['SWD']=='No'])], marker=dict(colors=['#00e5ff', '#10b981']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Students with Disabilities")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        dis_counts = filtered_students[filtered_students['Disability'] != 'None']['Disability'].value_counts()
        if len(dis_counts) > 0:
            fig = go.Figure(data=[go.Bar(x=dis_counts.index, y=dis_counts.values, marker_color='#ffd93d')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Disability Types", xaxis_title='Type', yaxis_title='Count')
            st.plotly_chart(fig, use_container_width=True)

elif st.session_state.selected_view == "By Partnership":
    st.markdown('<div class="section-title"><h2>Partnership Area Distribution</h2></div>', unsafe_allow_html=True)
    m = folium.Map(location=[-34.93, 138.60], zoom_start=11, tiles='OpenStreetMap')
    partnerships = {'Inner West': {'coords': [-34.90, 138.54]}, 'Adelaide Prospect': {'coords': [-34.85, 138.60]}, 'Greenhill South': {'coords': [-34.98, 138.63]}, 'Holdfast': {'coords': [-35.02, 138.52]}, 'Mitcham Hills': {'coords': [-34.99, 138.65]}}
    for p, d in partnerships.items():
        count = len(filtered_students[filtered_students['Partnership'] == p])
        folium.CircleMarker(location=d['coords'], radius=max(15, count*2), popup=f"{p}<br>Students: {count}", color='#00e5ff', fill=True, fillColor='#00e5ff', fillOpacity=0.7, weight=2).add_to(m)
    st_folium(m, width=1200, height=600)
    st.markdown("---")
    c1, c2, c3, c4, c5 = st.columns(5)
    for i, (p, d) in enumerate(partnerships.items()):
        count = len(filtered_students[filtered_students['Partnership'] == p])
        [c1, c2, c3, c4, c5][i].metric(p, count)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-weight: 600;'>CLC-LBU Allocation Dashboard • Term 2, 2026</p>", unsafe_allow_html=True)
