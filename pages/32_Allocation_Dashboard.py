import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

# Initialize filters
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'year': {'2024', '2025', '2026'},
        'program': {'JP', 'PY', 'SY'},
        'status': {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'},
        'atsi': {'Yes', 'No'},
        'eald': {'Yes', 'No'},
        'attendance': {'Full-time', 'Part-time', 'Irregular'},
        'swd': {'Yes', 'No'},
        'disability': {'ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'},
        'support': {'Minimal', 'Moderate', 'Intensive', 'Specialist'},
        'partnership': {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
    }

if 'view' not in st.session_state:
    st.session_state.view = "Dashboard Overview"

# Load sample data
@st.cache_data
def load_data():
    return pd.DataFrame({
        'Student': ['John Smith', 'Mary Jones', 'Sarah Lee', 'David Chen', 'Emma Wilson', 'Alex Brown', 'Sophie Green', 'Tom White', 'Lisa Anderson', 'James Taylor', 'Rachel Martin', 'Chris Davis', 'Katie Wilson', 'Michael Brown', 'Jessica Taylor'],
        'Year': ['2026', '2026', '2026', '2025', '2026', '2025', '2026', '2026', '2025', '2026', '2026', '2025', '2026', '2026', '2025'],
        'Program': ['JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY', 'SY', 'JP', 'PY', 'SY'],
        'Status': ['Allocated', 'Allocated', 'Pending', 'Allocated', 'Not Placed', 'Allocated', 'Pending', 'Allocated', 'Allocated', 'On Waitlist', 'Allocated', 'Pending', 'Allocated', 'Allocated', 'Not Placed'],
        'ATSI': ['No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'Yes', 'No'],
        'SWD': ['Yes', 'No', 'Yes', 'No', 'Yes', 'Yes', 'No', 'No', 'Yes', 'No', 'Yes', 'Yes', 'No', 'No', 'Yes'],
        'Disability': ['ASD', 'None', 'ADHD', 'None', 'Learning', 'ASD', 'None', 'None', 'ADHD', 'None', 'Physical', 'ASD', 'None', 'None', 'Hearing'],
        'Attendance': ['Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time', 'Part-time', 'Full-time', 'Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time', 'Full-time', 'Part-time', 'Full-time'],
        'EALD': ['No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No'],
        'Category of Support': ['Moderate', 'Intensive', 'Specialist', 'Minimal', 'Intensive', 'Specialist', 'Moderate', 'Minimal', 'Intensive', 'Moderate', 'Specialist', 'Intensive', 'Minimal', 'Moderate', 'Specialist'],
        'Partnership': ['Inner West', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills', 'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast'],
    })

all_data = load_data()

# Apply filters
filtered = all_data[
    (all_data['Year'].isin(st.session_state.filters['year'])) &
    (all_data['Program'].isin(st.session_state.filters['program'])) &
    (all_data['Status'].isin(st.session_state.filters['status'])) &
    (all_data['ATSI'].isin(st.session_state.filters['atsi'])) &
    (all_data['EALD'].isin(st.session_state.filters['eald'])) &
    (all_data['Attendance'].isin(st.session_state.filters['attendance'])) &
    (all_data['SWD'].isin(st.session_state.filters['swd'])) &
    (all_data['Disability'].isin(st.session_state.filters['disability'])) &
    (all_data['Category of Support'].isin(st.session_state.filters['support'])) &
    (all_data['Partnership'].isin(st.session_state.filters['partnership']))
]

# CSS Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; color: #ffffff !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
.main { background-color: #0a0e27 !important; }
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 3rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
</style>
""", unsafe_allow_html=True)

# SIDEBAR FILTERS
with st.sidebar:
    st.markdown("## Filters")
    st.markdown("---")
    
    view_opts = ["Dashboard Overview", "All Students", "By Demographics", "By Support", "By Partnership"]
    st.session_state.view = st.radio("View", view_opts, label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("## Filter Data")
    st.markdown("---")
    
    # Year
    st.markdown("### Year")
    c1, c2 = st.columns(2)
    if c1.button("All", key="y_all"): st.session_state.filters['year'] = {'2024', '2025', '2026'}
    if c2.button("Clear", key="y_clr"): st.session_state.filters['year'] = set()
    y1, y2, y3 = st.columns(3)
    if y1.button("2024", key="y1"): st.session_state.filters['year'] ^= {"2024"}
    if y2.button("2025", key="y2"): st.session_state.filters['year'] ^= {"2025"}
    if y3.button("2026", key="y3"): st.session_state.filters['year'] ^= {"2026"}
    st.markdown("---")
    
    # Program
    st.markdown("### Program")
    c1, c2 = st.columns(2)
    if c1.button("All", key="p_all"): st.session_state.filters['program'] = {'JP', 'PY', 'SY'}
    if c2.button("Clear", key="p_clr"): st.session_state.filters['program'] = set()
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", key="p1"): st.session_state.filters['program'] ^= {"JP"}
    if p2.button("PY", key="p2"): st.session_state.filters['program'] ^= {"PY"}
    if p3.button("SY", key="p3"): st.session_state.filters['program'] ^= {"SY"}
    st.markdown("---")
    
    # Status
    st.markdown("### Status")
    c1, c2 = st.columns(2)
    if c1.button("All", key="st_all"): st.session_state.filters['status'] = {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'}
    if c2.button("Clear", key="st_clr"): st.session_state.filters['status'] = set()
    s1, s2 = st.columns(2)
    if s1.button("Allocated", key="st1"): st.session_state.filters['status'] ^= {"Allocated"}
    if s2.button("Pending", key="st2"): st.session_state.filters['status'] ^= {"Pending"}
    s3, s4 = st.columns(2)
    if s3.button("Not Placed", key="st3"): st.session_state.filters['status'] ^= {"Not Placed"}
    if s4.button("Waitlist", key="st4"): st.session_state.filters['status'] ^= {"On Waitlist"}
    st.markdown("---")
    
    # ATSI
    st.markdown("### ATSI")
    c1, c2 = st.columns(2)
    if c1.button("All", key="at_all"): st.session_state.filters['atsi'] = {'Yes', 'No'}
    if c2.button("Clear", key="at_clr"): st.session_state.filters['atsi'] = set()
    a1, a2 = st.columns(2)
    if a1.button("Yes", key="at1"): st.session_state.filters['atsi'] ^= {"Yes"}
    if a2.button("No", key="at2"): st.session_state.filters['atsi'] ^= {"No"}
    st.markdown("---")
    
    # SWD
    st.markdown("### SWD")
    c1, c2 = st.columns(2)
    if c1.button("All", key="sw_all"): st.session_state.filters['swd'] = {'Yes', 'No'}
    if c2.button("Clear", key="sw_clr"): st.session_state.filters['swd'] = set()
    sw1, sw2 = st.columns(2)
    if sw1.button("Yes", key="sw1"): st.session_state.filters['swd'] ^= {"Yes"}
    if sw2.button("No", key="sw2"): st.session_state.filters['swd'] ^= {"No"}
    st.markdown("---")
    
    # EALD
    st.markdown("### EALD")
    c1, c2 = st.columns(2)
    if c1.button("All", key="e_all"): st.session_state.filters['eald'] = {'Yes', 'No'}
    if c2.button("Clear", key="e_clr"): st.session_state.filters['eald'] = set()
    e1, e2 = st.columns(2)
    if e1.button("Yes", key="e1"): st.session_state.filters['eald'] ^= {"Yes"}
    if e2.button("No", key="e2"): st.session_state.filters['eald'] ^= {"No"}
    st.markdown("---")
    
    # Attendance
    st.markdown("### Attendance")
    c1, c2 = st.columns(2)
    if c1.button("All", key="at_a"): st.session_state.filters['attendance'] = {'Full-time', 'Part-time', 'Irregular'}
    if c2.button("Clear", key="at_c"): st.session_state.filters['attendance'] = set()
    at1, at2, at3 = st.columns(3)
    if at1.button("Full-time", key="at_1"): st.session_state.filters['attendance'] ^= {"Full-time"}
    if at2.button("Part-time", key="at_2"): st.session_state.filters['attendance'] ^= {"Part-time"}
    if at3.button("Irregular", key="at_3"): st.session_state.filters['attendance'] ^= {"Irregular"}
    st.markdown("---")
    
    # Disability
    st.markdown("### Disability")
    c1, c2 = st.columns(2)
    if c1.button("All", key="d_all"): st.session_state.filters['disability'] = {'ASD', 'ADHD', 'Learning', 'Physical', 'Hearing', 'Vision'}
    if c2.button("Clear", key="d_clr"): st.session_state.filters['disability'] = set()
    d1, d2 = st.columns(2)
    if d1.button("ASD", key="d1"): st.session_state.filters['disability'] ^= {"ASD"}
    if d2.button("ADHD", key="d2"): st.session_state.filters['disability'] ^= {"ADHD"}
    d3, d4 = st.columns(2)
    if d3.button("Learning", key="d3"): st.session_state.filters['disability'] ^= {"Learning"}
    if d4.button("Physical", key="d4"): st.session_state.filters['disability'] ^= {"Physical"}
    d5, d6 = st.columns(2)
    if d5.button("Hearing", key="d5"): st.session_state.filters['disability'] ^= {"Hearing"}
    if d6.button("Vision", key="d6"): st.session_state.filters['disability'] ^= {"Vision"}
    st.markdown("---")
    
    # Support
    st.markdown("### Category of Support")
    c1, c2 = st.columns(2)
    if c1.button("All", key="sup_all"): st.session_state.filters['support'] = {'Minimal', 'Moderate', 'Intensive', 'Specialist'}
    if c2.button("Clear", key="sup_clr"): st.session_state.filters['support'] = set()
    sup1, sup2 = st.columns(2)
    if sup1.button("Minimal", key="sup1"): st.session_state.filters['support'] ^= {"Minimal"}
    if sup2.button("Moderate", key="sup2"): st.session_state.filters['support'] ^= {"Moderate"}
    sup3, sup4 = st.columns(2)
    if sup3.button("Intensive", key="sup3"): st.session_state.filters['support'] ^= {"Intensive"}
    if sup4.button("Specialist", key="sup4"): st.session_state.filters['support'] ^= {"Specialist"}
    st.markdown("---")
    
    # Partnership
    st.markdown("### Partnership")
    c1, c2 = st.columns(2)
    if c1.button("All", key="par_all"): st.session_state.filters['partnership'] = {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
    if c2.button("Clear", key="par_clr"): st.session_state.filters['partnership'] = set()
    opts = ["Inner West", "Adelaide Prospect", "Greenhill South", "Holdfast", "Mitcham Hills"]
    for i, opt in enumerate(opts):
        if (i % 2) == 0:
            co1, co2 = st.columns(2)
        if (i % 2) == 0:
            if co1.button(opt, key=f"p_{i}"): st.session_state.filters['partnership'] ^= {opt}
        else:
            if co2.button(opt, key=f"p_{i}"): st.session_state.filters['partnership'] ^= {opt}

# MAIN DASHBOARD
st.markdown('<div style="background: linear-gradient(135deg, #1a1f3a 0%, #2a3050 100%); border: 2px solid #00e5ff; border-radius: 16px; padding: 3rem 4rem; text-align: center; margin-bottom: 3rem;"><h1 style="font-size: 3.5rem; color: #ffffff; margin: 0;">Allocation Dashboard</h1><p style="color: #00e5ff; font-size: 1.2rem; margin: 1rem 0 0 0;">Comprehensive Analytics & Support Tracking</p></div>', unsafe_allow_html=True)

# Metrics
st.markdown('<div style="background-color: #1a1f3a; border: 2px solid #00e5ff; border-radius: 14px; padding: 2rem; margin: 2rem 0;"><h2 style="color: #ffffff; font-size: 2rem; margin: 0;">Summary Metrics</h2></div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total", len(filtered))
c2.metric("Allocated", len(filtered[filtered['Status']=='Allocated']))
c3.metric("Pending", len(filtered[filtered['Status']=='Pending']))
c4.metric("ATSI", len(filtered[filtered['ATSI']=='Yes']))
c5.metric("SWD", len(filtered[filtered['SWD']=='Yes']))
c6.metric("EALD", len(filtered[filtered['EALD']=='Yes']))

st.markdown("---")

# Display based on view
if st.session_state.view == "Dashboard Overview":
    st.markdown('<div style="background-color: #1a1f3a; border: 2px solid #00e5ff; border-radius: 14px; padding: 2rem;"><h2 style="color: #ffffff;">Dashboard Overview</h2></div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        prog = filtered['Program'].value_counts()
        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14), title="By Program", height=350)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        stat = filtered['Status'].value_counts()
        fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14), title="By Status", height=350)
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        sup = filtered['Category of Support'].value_counts()
        fig = go.Figure([go.Pie(labels=sup.index, values=sup.values, marker=dict(colors=['#10b981', '#00e5ff', '#ffd93d', '#ff6b6b']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=14), title="Support Levels", height=350)
        st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view == "All Students":
    st.markdown('<div style="background-color: #1a1f3a; border: 2px solid #00e5ff; border-radius: 14px; padding: 2rem;"><h2 style="color: #ffffff;">All Students</h2></div>', unsafe_allow_html=True)
    st.dataframe(filtered[['Student', 'Year', 'Program', 'Status', 'ATSI', 'SWD', 'EALD', 'Category of Support']], use_container_width=True, hide_index=True)

elif st.session_state.view == "By Demographics":
    st.markdown('<div style="background-color: #1a1f3a; border: 2px solid #00e5ff; border-radius: 14px; padding: 2rem;"><h2 style="color: #ffffff;">Demographics</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        fig = go.Figure([go.Pie(labels=['ATSI', 'Non-ATSI'], values=[len(filtered[filtered['ATSI']=='Yes']), len(filtered[filtered['ATSI']=='No'])], marker=dict(colors=['#00e5ff', '#10b981']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="ATSI", height=350)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = go.Figure([go.Pie(labels=['EALD', 'Non-EALD'], values=[len(filtered[filtered['EALD']=='Yes']), len(filtered[filtered['EALD']=='No'])], marker=dict(colors=['#00e5ff', '#ffd93d']))])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="EALD", height=350)
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        prog = filtered['Program'].value_counts()
        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="By Program", height=350)
        st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view == "By Support":
    st.markdown('<div style="background-color: #1a1f3a; border: 2px solid #00e5ff; border-radius: 14px; padding: 2rem;"><h2 style="color: #ffffff;">Support Analysis</h2></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        sup_prog = pd.crosstab(filtered['Program'], filtered['Category of Support']).reindex(columns=['Minimal', 'Moderate', 'Intensive', 'Specialist'], fill_value=0)
        fig = go.Figure([
            go.Bar(x=sup_prog.index, y=sup_prog['Minimal'], name='Minimal', marker_color='#10b981'),
            go.Bar(x=sup_prog.index, y=sup_prog['Moderate'], name='Moderate', marker_color='#00e5ff'),
            go.Bar(x=sup_prog.index, y=sup_prog['Intensive'], name='Intensive', marker_color='#ffd93d'),
            go.Bar(x=sup_prog.index, y=sup_prog['Specialist'], name='Specialist', marker_color='#ff6b6b')
        ])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Support by Program", barmode='stack', height=400)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        sup_swd = pd.crosstab(filtered['SWD'], filtered['Category of Support']).reindex(columns=['Minimal', 'Moderate', 'Intensive', 'Specialist'], fill_value=0)
        fig = go.Figure([
            go.Bar(x=sup_swd.index, y=sup_swd['Minimal'], name='Minimal', marker_color='#10b981'),
            go.Bar(x=sup_swd.index, y=sup_swd['Moderate'], name='Moderate', marker_color='#00e5ff'),
            go.Bar(x=sup_swd.index, y=sup_swd['Intensive'], name='Intensive', marker_color='#ffd93d'),
            go.Bar(x=sup_swd.index, y=sup_swd['Specialist'], name='Specialist', marker_color='#ff6b6b')
        ])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Support by SWD", barmode='stack', height=400)
        st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view == "By Partnership":
    st.markdown('<div style="background-color: #1a1f3a; border: 2px solid #00e5ff; border-radius: 14px; padding: 2rem;"><h2 style="color: #ffffff;">Partnership Distribution</h2></div>', unsafe_allow_html=True)
    m = folium.Map(location=[-34.93, 138.60], zoom_start=11, tiles='OpenStreetMap')
    for p, coords in [('Inner West', [-34.90, 138.54]), ('Adelaide Prospect', [-34.85, 138.60]), ('Greenhill South', [-34.98, 138.63]), ('Holdfast', [-35.02, 138.52]), ('Mitcham Hills', [-34.99, 138.65])]:
        cnt = len(filtered[filtered['Partnership']==p])
        folium.CircleMarker(location=coords, radius=max(15, cnt*2), popup=f"{p}: {cnt}", color='#00e5ff', fill=True, fillColor='#00e5ff', fillOpacity=0.7, weight=2).add_to(m)
    st_folium(m, width=1200, height=600)
    st.markdown("---")
    c1, c2, c3, c4, c5 = st.columns(5)
    for i, p in enumerate(['Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills']):
        cnt = len(filtered[filtered['Partnership']==p])
        [c1, c2, c3, c4, c5][i].metric(p, cnt)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
