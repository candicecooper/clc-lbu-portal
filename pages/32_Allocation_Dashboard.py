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
        'swd_type': {'Physical', 'Sensory', 'Cognitive', 'Behaviour', 'Multiple'},
        'cat_support': {'Cat 1', 'Cat 2', 'Cat 3', 'Cat 4'},
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
        'SWD Type': ['Physical', 'None', 'Cognitive', 'None', 'Behaviour', 'Sensory', 'None', 'None', 'Multiple', 'None', 'Cognitive', 'Behaviour', 'None', 'None', 'Sensory'],
        'Attendance': ['Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time', 'Part-time', 'Full-time', 'Full-time', 'Part-time', 'Full-time', 'Irregular', 'Full-time', 'Full-time', 'Part-time', 'Full-time'],
        'EALD': ['No', 'Yes', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No', 'Yes', 'No', 'No'],
        'Category of Support': ['Cat 2', 'Cat 3', 'Cat 4', 'Cat 1', 'Cat 3', 'Cat 4', 'Cat 2', 'Cat 1', 'Cat 3', 'Cat 2', 'Cat 4', 'Cat 3', 'Cat 1', 'Cat 2', 'Cat 4'],
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
if 'SWD Type' in all_data.columns:
    filter_conditions &= all_data['SWD Type'].isin(st.session_state.filters['swd_type'])
if 'Category of Support' in all_data.columns:
    filter_conditions &= all_data['Category of Support'].isin(st.session_state.filters['cat_support'])
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
    st.session_state.view = st.radio("", ["Dashboard Overview", "All Students"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 QUICK FILTERS")
    
    # Year
    st.markdown("**Year**")
    yc1, yc2 = st.columns(2)
    if yc1.button("All", key="y_all", use_container_width=True): st.session_state.filters['year'] = {'2024', '2025', '2026'}
    if yc2.button("Clear", key="y_clear", use_container_width=True): st.session_state.filters['year'] = set()
    y1, y2, y3 = st.columns(3)
    if y1.button("2024", use_container_width=True, key="y1"): st.session_state.filters['year'] ^= {"2024"}
    if y2.button("2025", use_container_width=True, key="y2"): st.session_state.filters['year'] ^= {"2025"}
    if y3.button("2026", use_container_width=True, key="y3"): st.session_state.filters['year'] ^= {"2026"}
    
    # Program
    st.markdown("**Program**")
    pc1, pc2 = st.columns(2)
    if pc1.button("All", key="p_all", use_container_width=True): st.session_state.filters['program'] = {'JP', 'PY', 'SY'}
    if pc2.button("Clear", key="p_clear", use_container_width=True): st.session_state.filters['program'] = set()
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", use_container_width=True, key="p1"): st.session_state.filters['program'] ^= {"JP"}
    if p2.button("PY", use_container_width=True, key="p2"): st.session_state.filters['program'] ^= {"PY"}
    if p3.button("SY", use_container_width=True, key="p3"): st.session_state.filters['program'] ^= {"SY"}
    
    # Status
    st.markdown("**Status**")
    sc1, sc2 = st.columns(2)
    if sc1.button("All", key="s_all", use_container_width=True): st.session_state.filters['status'] = {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'}
    if sc2.button("Clear", key="s_clear", use_container_width=True): st.session_state.filters['status'] = set()
    s1, s2 = st.columns(2)
    if s1.button("Allocated", use_container_width=True, key="s1"): st.session_state.filters['status'] ^= {"Allocated"}
    if s2.button("Pending", use_container_width=True, key="s2"): st.session_state.filters['status'] ^= {"Pending"}
    s3, s4 = st.columns(2)
    if s3.button("Not Placed", use_container_width=True, key="s3"): st.session_state.filters['status'] ^= {"Not Placed"}
    if s4.button("Waitlist", use_container_width=True, key="s4"): st.session_state.filters['status'] ^= {"On Waitlist"}
    
    # ATSI
    st.markdown("**ATSI**")
    ac1, ac2 = st.columns(2)
    if ac1.button("All", key="a_all", use_container_width=True): st.session_state.filters['atsi'] = {'Yes', 'No'}
    if ac2.button("Clear", key="a_clear", use_container_width=True): st.session_state.filters['atsi'] = set()
    a1, a2 = st.columns(2)
    if a1.button("Yes", use_container_width=True, key="a1"): st.session_state.filters['atsi'] ^= {"Yes"}
    if a2.button("No", use_container_width=True, key="a2"): st.session_state.filters['atsi'] ^= {"No"}
    
    # EALD
    st.markdown("**EALD**")
    ec1, ec2 = st.columns(2)
    if ec1.button("All", key="e_all", use_container_width=True): st.session_state.filters['eald'] = {'Yes', 'No'}
    if ec2.button("Clear", key="e_clear", use_container_width=True): st.session_state.filters['eald'] = set()
    e1, e2 = st.columns(2)
    if e1.button("Yes", use_container_width=True, key="e1"): st.session_state.filters['eald'] ^= {"Yes"}
    if e2.button("No", use_container_width=True, key="e2"): st.session_state.filters['eald'] ^= {"No"}
    
    # SWD (EXPANDED)
    st.markdown("**SWD**")
    swdc1, swdc2 = st.columns(2)
    if swdc1.button("All", key="swd_all", use_container_width=True): st.session_state.filters['swd'] = {'Yes', 'No'}
    if swdc2.button("Clear", key="swd_clear", use_container_width=True): st.session_state.filters['swd'] = set()
    swd1, swd2 = st.columns(2)
    if swd1.button("Yes", use_container_width=True, key="swd1"): st.session_state.filters['swd'] ^= {"Yes"}
    if swd2.button("No", use_container_width=True, key="swd2"): st.session_state.filters['swd'] ^= {"No"}
    
    # SWD Type
    st.markdown("**SWD Type**")
    swdtc1, swdtc2 = st.columns(2)
    if swdtc1.button("All", key="swdt_all", use_container_width=True): st.session_state.filters['swd_type'] = {'Physical', 'Sensory', 'Cognitive', 'Behaviour', 'Multiple'}
    if swdtc2.button("Clear", key="swdt_clear", use_container_width=True): st.session_state.filters['swd_type'] = set()
    swdt1, swdt2 = st.columns(2)
    if swdt1.button("Physical", use_container_width=True, key="swdt1"): st.session_state.filters['swd_type'] ^= {"Physical"}
    if swdt2.button("Sensory", use_container_width=True, key="swdt2"): st.session_state.filters['swd_type'] ^= {"Sensory"}
    swdt3, swdt4 = st.columns(2)
    if swdt3.button("Cognitive", use_container_width=True, key="swdt3"): st.session_state.filters['swd_type'] ^= {"Cognitive"}
    if swdt4.button("Behaviour", use_container_width=True, key="swdt4"): st.session_state.filters['swd_type'] ^= {"Behaviour"}
    swdt5 = st.columns(1)
    if swdt5[0].button("Multiple", use_container_width=True, key="swdt5"): st.session_state.filters['swd_type'] ^= {"Multiple"}
    
    # Attendance
    st.markdown("**Attendance**")
    attc1, attc2 = st.columns(2)
    if attc1.button("All", key="att_all", use_container_width=True): st.session_state.filters['attendance'] = {'Full-time', 'Part-time', 'Irregular'}
    if attc2.button("Clear", key="att_clear", use_container_width=True): st.session_state.filters['attendance'] = set()
    att1, att2, att3 = st.columns(3)
    if att1.button("Full-time", use_container_width=True, key="att1"): st.session_state.filters['attendance'] ^= {"Full-time"}
    if att2.button("Part-time", use_container_width=True, key="att2"): st.session_state.filters['attendance'] ^= {"Part-time"}
    if att3.button("Irregular", use_container_width=True, key="att3"): st.session_state.filters['attendance'] ^= {"Irregular"}
    
    # Category of Support
    st.markdown("**Category of Support**")
    catc1, catc2 = st.columns(2)
    if catc1.button("All", key="cat_all", use_container_width=True): st.session_state.filters['cat_support'] = {'Cat 1', 'Cat 2', 'Cat 3', 'Cat 4'}
    if catc2.button("Clear", key="cat_clear", use_container_width=True): st.session_state.filters['cat_support'] = set()
    cat1, cat2, cat3, cat4 = st.columns(4)
    if cat1.button("Cat 1", use_container_width=True, key="cat1"): st.session_state.filters['cat_support'] ^= {"Cat 1"}
    if cat2.button("Cat 2", use_container_width=True, key="cat2"): st.session_state.filters['cat_support'] ^= {"Cat 2"}
    if cat3.button("Cat 3", use_container_width=True, key="cat3"): st.session_state.filters['cat_support'] ^= {"Cat 3"}
    if cat4.button("Cat 4", use_container_width=True, key="cat4"): st.session_state.filters['cat_support'] ^= {"Cat 4"}

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
    with c2:
        if 'Status' in filtered.columns:
            stat = filtered['Status'].value_counts()
            fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Status", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
    with c3:
        if 'Category of Support' in filtered.columns:
            sup = filtered['Category of Support'].value_counts()
            fig = go.Figure([go.Pie(labels=sup.index, values=sup.values)])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support", height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if 'Program' in filtered.columns and 'Category of Support' in filtered.columns:
            sup_prog = pd.crosstab(filtered['Program'], filtered['Category of Support']).reindex(columns=['Cat 1', 'Cat 2', 'Cat 3', 'Cat 4'], fill_value=0)
            fig = go.Figure([go.Bar(x=sup_prog.index, y=sup_prog['Cat 1'], name='Cat 1', marker_color='#10b981'), go.Bar(x=sup_prog.index, y=sup_prog['Cat 2'], name='Cat 2', marker_color='#00e5ff'), go.Bar(x=sup_prog.index, y=sup_prog['Cat 3'], name='Cat 3', marker_color='#ffd93d'), go.Bar(x=sup_prog.index, y=sup_prog['Cat 4'], name='Cat 4', marker_color='#ff6b6b')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support by Program", barmode='stack', height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if 'SWD Type' in filtered.columns and 'Category of Support' in filtered.columns:
            sup_swd = pd.crosstab(filtered['SWD Type'], filtered['Category of Support']).reindex(columns=['Cat 1', 'Cat 2', 'Cat 3', 'Cat 4'], fill_value=0)
            fig = go.Figure([go.Bar(x=sup_swd.index, y=sup_swd['Cat 1'], name='Cat 1', marker_color='#10b981'), go.Bar(x=sup_swd.index, y=sup_swd['Cat 2'], name='Cat 2', marker_color='#00e5ff'), go.Bar(x=sup_swd.index, y=sup_swd['Cat 3'], name='Cat 3', marker_color='#ffd93d'), go.Bar(x=sup_swd.index, y=sup_swd['Cat 4'], name='Cat 4', marker_color='#ff6b6b')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Support by SWD Type", barmode='stack', height=280, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view == "All Students":
    cols_to_show = [c for c in ['Student', 'Program', 'Status', 'ATSI', 'SWD', 'SWD Type', 'Category of Support'] if c in filtered.columns]
    if cols_to_show:
        st.dataframe(filtered[cols_to_show], use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No matching columns found in data")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-size: 0.85rem;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
