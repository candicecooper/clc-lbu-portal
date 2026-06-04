import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

if 'filters' not in st.session_state:
    st.session_state.filters = {
        'year': {'2024', '2025', '2026'},
        'program': {'JP', 'PY', 'SY'},
        'status': {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'},
        'atsi': {'Yes', 'No'},
        'eald': {'Yes', 'No'},
        'attendance': {'Full-time', 'Part-time', 'Irregular'},
        'swd': {'Yes', 'No'},
        'support': {'Minimal', 'Moderate', 'Intensive', 'Specialist'},
        'partnership': {'Inner West', 'Adelaide Prospect', 'Greenhill South', 'Holdfast', 'Mitcham Hills'}
    }
    st.session_state.data = None

if 'view' not in st.session_state:
    st.session_state.view = "Dashboard Overview"

@st.cache_data
def get_sample():
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

all_data = st.session_state.data if st.session_state.data is not None else get_sample()

# Build filter conditions only for columns that exist
filter_conditions = pd.Series([True] * len(all_data), index=all_data.index)

if 'Year' in all_data.columns:
    filter_conditions &= all_data['Year'].isin(st.session_state.filters['year'])
if 'Program' in all_data.columns:
    filter_conditions &= all_data['Program'].isin(st.session_state.filters['program'])
if 'Status' in all_data.columns:
    filter_conditions &= all_data['Status'].isin(st.session_state.filters['status'])
if 'ATSI' in all_data.columns:
    filter_conditions &= all_data['ATSI'].isin(st.session_state.filters['atsi'])
if 'EALD' in all_data.columns:
    filter_conditions &= all_data['EALD'].isin(st.session_state.filters['eald'])
if 'Attendance' in all_data.columns:
    filter_conditions &= all_data['Attendance'].isin(st.session_state.filters['attendance'])
if 'SWD' in all_data.columns:
    filter_conditions &= all_data['SWD'].isin(st.session_state.filters['swd'])
if 'Category of Support' in all_data.columns:
    filter_conditions &= all_data['Category of Support'].isin(st.session_state.filters['support'])
if 'Partnership' in all_data.columns:
    filter_conditions &= all_data['Partnership'].isin(st.session_state.filters['partnership'])

filtered = all_data[filter_conditions]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
.main { background-color: #0a0e27 !important; padding: 1rem !important; }
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
[data-testid="stSidebar"] { background-color: #0a0e27 !important; }
[data-testid="stSidebar"] * { color: #00e5ff !important; }
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2.2rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; padding: 0.3rem 0.6rem !important; font-size: 0.75rem !important; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 📤 UPLOAD DATA")
    uploaded = st.file_uploader("", type=['xlsx', 'xls', 'csv'])
    if uploaded is not None:
        try:
            new_data = pd.read_excel(uploaded) if uploaded.name.endswith(('xlsx', 'xls')) else pd.read_csv(uploaded)
            st.session_state.data = new_data
            all_data = new_data
            st.success(f"✓ Loaded {len(new_data)} records")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.markdown("---")
    
    st.markdown("### 📊 VIEW")
    st.session_state.view = st.radio("", ["Dashboard Overview", "All Students", "By Demographics", "By Support", "By Partnership"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 QUICK FILTERS")
    
    st.markdown("**Year:** ")
    y1, y2, y3 = st.columns(3)
    if y1.button("2024", use_container_width=True, key="y1"): st.session_state.filters['year'] ^= {"2024"}
    if y2.button("2025", use_container_width=True, key="y2"): st.session_state.filters['year'] ^= {"2025"}
    if y3.button("2026", use_container_width=True, key="y3"): st.session_state.filters['year'] ^= {"2026"}
    
    st.markdown("**Program:** ")
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", use_container_width=True, key="p1"): st.session_state.filters['program'] ^= {"JP"}
    if p2.button("PY", use_container_width=True, key="p2"): st.session_state.filters['program'] ^= {"PY"}
    if p3.button("SY", use_container_width=True, key="p3"): st.session_state.filters['program'] ^= {"SY"}
    
    st.markdown("**Status:** ")
    s1, s2 = st.columns(2)
    if s1.button("Allocated", use_container_width=True, key="s1"): st.session_state.filters['status'] ^= {"Allocated"}
    if s2.button("Pending", use_container_width=True, key="s2"): st.session_state.filters['status'] ^= {"Pending"}
    s3, s4 = st.columns(2)
    if s3.button("Not Placed", use_container_width=True, key="s3"): st.session_state.filters['status'] ^= {"Not Placed"}
    if s4.button("Waitlist", use_container_width=True, key="s4"): st.session_state.filters['status'] ^= {"On Waitlist"}
    
    st.markdown("**Demographics:** ")
    a1, s1, e1 = st.columns(3)
    if a1.button("ATSI", use_container_width=True, key="atsi"): st.session_state.filters['atsi'] ^= {"Yes"}
    if s1.button("SWD", use_container_width=True, key="swd"): st.session_state.filters['swd'] ^= {"Yes"}
    if e1.button("EALD", use_container_width=True, key="eald"): st.session_state.filters['eald'] ^= {"Yes"}
    
    st.markdown("**Support:** ")
    sup1, sup2 = st.columns(2)
    if sup1.button("Minimal", use_container_width=True, key="sup1"): st.session_state.filters['support'] ^= {"Minimal"}
    if sup2.button("Moderate", use_container_width=True, key="sup2"): st.session_state.filters['support'] ^= {"Moderate"}
    sup3, sup4 = st.columns(2)
    if sup3.button("Intensive", use_container_width=True, key="sup3"): st.session_state.filters['support'] ^= {"Intensive"}
    if sup4.button("Specialist", use_container_width=True, key="sup4"): st.session_state.filters['support'] ^= {"Specialist"}

st.markdown("## Allocation Dashboard")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total", len(filtered))
c2.metric("Allocated", len(filtered[filtered['Status']=='Allocated']) if 'Status' in filtered.columns else 0)
c3.metric("Pending", len(filtered[filtered['Status']=='Pending']) if 'Status' in filtered.columns else 0)
c4.metric("ATSI", len(filtered[filtered['ATSI']=='Yes']) if 'ATSI' in filtered.columns else 0)
c5.metric("SWD", len(filtered[filtered['SWD']=='Yes']) if 'SWD' in filtered.columns else 0)
c6.metric("EALD", len(filtered[filtered['EALD']=='Yes']) if 'EALD' in filtered.columns else 0)

st.markdown("---")

if st.session_state.view == "Dashboard Overview":
    c1, c2, c3 = st.columns(3)
    with c1:
        if 'Program' in filtered.columns:
            prog = filtered['Program'].value_counts()
            fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Program", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Program column not found")
    with c2:
        if 'Status' in filtered.columns:
            stat = filtered['Status'].value_counts()
            fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Status", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Status column not found")
    with c3:
        if 'Category of Support' in filtered.columns:
            sup = filtered['Category of Support'].value_counts()
            fig = go.Figure([go.Pie(labels=sup.index, values=sup.values)])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Support column not found")
    
    c1, c2 = st.columns(2)
    with c1:
        if 'Program' in filtered.columns and 'Category of Support' in filtered.columns:
            sup_prog = pd.crosstab(filtered['Program'], filtered['Category of Support']).reindex(columns=['Minimal', 'Moderate', 'Intensive', 'Specialist'], fill_value=0)
            fig = go.Figure([go.Bar(x=sup_prog.index, y=sup_prog['Minimal'], name='Min', marker_color='#10b981'), go.Bar(x=sup_prog.index, y=sup_prog['Moderate'], name='Mod', marker_color='#00e5ff'), go.Bar(x=sup_prog.index, y=sup_prog['Intensive'], name='Int', marker_color='#ffd93d'), go.Bar(x=sup_prog.index, y=sup_prog['Specialist'], name='Spec', marker_color='#ff6b6b')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support by Program", barmode='stack', height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if 'SWD' in filtered.columns and 'Category of Support' in filtered.columns:
            sup_swd = pd.crosstab(filtered['SWD'], filtered['Category of Support']).reindex(columns=['Minimal', 'Moderate', 'Intensive', 'Specialist'], fill_value=0)
            fig = go.Figure([go.Bar(x=sup_swd.index, y=sup_swd['Minimal'], name='Min', marker_color='#10b981'), go.Bar(x=sup_swd.index, y=sup_swd['Moderate'], name='Mod', marker_color='#00e5ff'), go.Bar(x=sup_swd.index, y=sup_swd['Intensive'], name='Int', marker_color='#ffd93d'), go.Bar(x=sup_swd.index, y=sup_swd['Specialist'], name='Spec', marker_color='#ff6b6b')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support by SWD", barmode='stack', height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view == "All Students":
    cols_to_show = [c for c in ['Student', 'Program', 'Status', 'ATSI', 'SWD', 'Category of Support'] if c in filtered.columns]
    if cols_to_show:
        st.dataframe(filtered[cols_to_show], use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No matching columns found in data")

elif st.session_state.view == "By Demographics":
    c1, c2, c3 = st.columns(3)
    with c1:
        fig = go.Figure([go.Pie(labels=['ATSI', 'Non-ATSI'], values=[len(filtered[filtered['ATSI']=='Yes']), len(filtered[filtered['ATSI']=='No'])])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="ATSI", height=300, margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = go.Figure([go.Pie(labels=['EALD', 'Non-EALD'], values=[len(filtered[filtered['EALD']=='Yes']), len(filtered[filtered['EALD']=='No'])])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="EALD", height=300, margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        prog = filtered['Program'].value_counts()
        fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Program", height=300, margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view == "By Support":
    c1, c2 = st.columns(2)
    with c1:
        sup = filtered['Category of Support'].value_counts()
        fig = go.Figure([go.Pie(labels=sup.index, values=sup.values)])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support Levels", height=320, margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        sup_prog = pd.crosstab(filtered['Program'], filtered['Category of Support']).reindex(columns=['Minimal', 'Moderate', 'Intensive', 'Specialist'], fill_value=0)
        fig = go.Figure([go.Bar(x=sup_prog.index, y=sup_prog['Minimal'], name='Min', marker_color='#10b981'), go.Bar(x=sup_prog.index, y=sup_prog['Moderate'], name='Mod', marker_color='#00e5ff'), go.Bar(x=sup_prog.index, y=sup_prog['Intensive'], name='Int', marker_color='#ffd93d'), go.Bar(x=sup_prog.index, y=sup_prog['Specialist'], name='Spec', marker_color='#ff6b6b')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="By Program", barmode='group', height=320, margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view == "By Partnership":
    m = folium.Map(location=[-34.93, 138.60], zoom_start=11, tiles='OpenStreetMap')
    for p, coords in [('Inner West', [-34.90, 138.54]), ('Adelaide Prospect', [-34.85, 138.60]), ('Greenhill South', [-34.98, 138.63]), ('Holdfast', [-35.02, 138.52]), ('Mitcham Hills', [-34.99, 138.65])]:
        cnt = len(filtered[filtered['Partnership']==p])
        folium.CircleMarker(location=coords, radius=max(10, cnt*2), popup=f"{p}: {cnt}", color='#00e5ff', fill=True, fillColor='#00e5ff', fillOpacity=0.7, weight=2).add_to(m)
    st_folium(m, width=1200, height=450)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-size: 0.85rem;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
