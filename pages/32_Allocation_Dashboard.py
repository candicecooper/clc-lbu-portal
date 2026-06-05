import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

# MINIMAL CSS - no hiding anything
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
.main { background-color: #0a0e27 !important; }
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
[data-testid="stSidebar"] { background-color: #0a0e27 !important; border-right: 2px solid #00e5ff !important; }
[data-testid="stSidebar"] * { color: #00e5ff !important; }
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
p { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

if 'filters' not in st.session_state:
    st.session_state.filters = {
        'year': {'2025', '2026'},
        'program': {'JP', 'PY', 'SY'},
        'status': {'Allocated', 'Pending', 'Not Placed', 'On Waitlist'},
        'atsi': {'Yes', 'No'},
        'eald': {'Yes', 'No'},
        'attendance': {'Full-time', 'Part-time', 'Irregular'},
        'swd': {'Yes', 'No'},
        'swd_type': {'Speech and Language', 'ASD', 'Intellectual', 'Learning Difficulty', 'Sensory Processing', 'ADHD', 'ODD', 'PDA'},
        'cat_support': {'1', '2', '3', '4', '5', '6', '7', '8', '9', '9+ RAAP'},
    }
if 'view' not in st.session_state:
    st.session_state.view = "Dashboard Overview"

with st.sidebar:
    st.markdown("### 📤 UPLOAD DATA")
    uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls', 'csv'], key='main_uploader')
    
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} loaded")
    
    st.markdown("---")
    st.markdown("### 📊 VIEW")
    st.session_state.view = st.radio("", ["Dashboard Overview", "All Students"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 QUICK FILTERS")
    
    st.markdown("**Year**")
    yc1, yc2 = st.columns(2)
    if yc1.button("All", key="y_all", use_container_width=True): st.session_state.filters['year'] = {'2025', '2026'}
    if yc2.button("Clear", key="y_clear", use_container_width=True): st.session_state.filters['year'] = set()
    y1, y2 = st.columns(2)
    if y1.button("2025", use_container_width=True, key="y1"): st.session_state.filters['year'] ^= {"2025"}
    if y2.button("2026", use_container_width=True, key="y2"): st.session_state.filters['year'] ^= {"2026"}
    
    st.markdown("**Program**")
    pc1, pc2 = st.columns(2)
    if pc1.button("All", key="p_all", use_container_width=True): st.session_state.filters['program'] = {'JP', 'PY', 'SY'}
    if pc2.button("Clear", key="p_clear", use_container_width=True): st.session_state.filters['program'] = set()
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", use_container_width=True, key="p1"): st.session_state.filters['program'] ^= {"JP"}
    if p2.button("PY", use_container_width=True, key="p2"): st.session_state.filters['program'] ^= {"PY"}
    if p3.button("SY", use_container_width=True, key="p3"): st.session_state.filters['program'] ^= {"SY"}
    
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
    
    st.markdown("**ATSI**")
    ac1, ac2 = st.columns(2)
    if ac1.button("All", key="a_all", use_container_width=True): st.session_state.filters['atsi'] = {'Yes', 'No'}
    if ac2.button("Clear", key="a_clear", use_container_width=True): st.session_state.filters['atsi'] = set()
    a1, a2 = st.columns(2)
    if a1.button("Yes", use_container_width=True, key="a1"): st.session_state.filters['atsi'] ^= {"Yes"}
    if a2.button("No", use_container_width=True, key="a2"): st.session_state.filters['atsi'] ^= {"No"}
    
    st.markdown("**EALD**")
    ec1, ec2 = st.columns(2)
    if ec1.button("All", key="e_all", use_container_width=True): st.session_state.filters['eald'] = {'Yes', 'No'}
    if ec2.button("Clear", key="e_clear", use_container_width=True): st.session_state.filters['eald'] = set()
    e1, e2 = st.columns(2)
    if e1.button("Yes", use_container_width=True, key="e1"): st.session_state.filters['eald'] ^= {"Yes"}
    if e2.button("No", use_container_width=True, key="e2"): st.session_state.filters['eald'] ^= {"No"}
    
    st.markdown("**SWD**")
    swdc1, swdc2 = st.columns(2)
    if swdc1.button("All", key="swd_all", use_container_width=True): st.session_state.filters['swd'] = {'Yes', 'No'}
    if swdc2.button("Clear", key="swd_clear", use_container_width=True): st.session_state.filters['swd'] = set()
    swd1, swd2 = st.columns(2)
    if swd1.button("Yes", use_container_width=True, key="swd1"): st.session_state.filters['swd'] ^= {"Yes"}
    if swd2.button("No", use_container_width=True, key="swd2"): st.session_state.filters['swd'] ^= {"No"}
    
    st.markdown("**SWD Type**")
    swdtc1, swdtc2 = st.columns(2)
    if swdtc1.button("All", key="swdt_all", use_container_width=True): st.session_state.filters['swd_type'] = {'Speech and Language', 'ASD', 'Intellectual', 'Learning Difficulty', 'Sensory Processing', 'ADHD', 'ODD', 'PDA'}
    if swdtc2.button("Clear", key="swdt_clear", use_container_width=True): st.session_state.filters['swd_type'] = set()
    swdt1, swdt2 = st.columns(2)
    if swdt1.button("Speech & Lang", use_container_width=True, key="swdt1"): st.session_state.filters['swd_type'] ^= {"Speech and Language"}
    if swdt2.button("ASD", use_container_width=True, key="swdt2"): st.session_state.filters['swd_type'] ^= {"ASD"}

st.markdown("## Allocation Dashboard")

if uploaded_file is None:
    st.warning("📤 Use the upload button in the sidebar to load your Excel file")
    st.info("""
    **To get started:**
    1. Look for **📤 UPLOAD DATA** at the top of the sidebar
    2. Click on it
    3. Select your Excel file (CLC_Allocation_Dashboard_2026_WithNames_1.xlsx)
    4. Dashboard will load automatically
    """)
else:
    try:
        all_data = pd.read_excel(uploaded_file)
        
        # Transform
        all_data['Status'] = 'Unknown'
        all_data['Program'] = all_data.get('Allocated_Program', 'Unknown')
        all_data['ATSI'] = all_data.get('Flag_ATSI', 'No').fillna('No').astype(str)
        all_data['SWD'] = all_data.get('Flag_SWD', 'No').fillna('No').astype(str)
        all_data['EALD'] = all_data.get('Flag_EALD', 'No').fillna('No').astype(str)
        all_data['Year'] = '2026'
        
        st.success(f"✅ Loaded {len(all_data)} records")
        
        # Metrics
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total", len(all_data))
        c2.metric("Allocated", len(all_data[all_data['Allocation_Status'].notna()]))
        c3.metric("Pending", 0)
        c4.metric("ATSI", len(all_data[all_data['ATSI']=='Yes']))
        c5.metric("SWD", len(all_data[all_data['SWD']=='Yes']))
        c6.metric("EALD", len(all_data[all_data['EALD']=='Yes']))
        
        st.markdown("---")
        
        if st.session_state.view == "Dashboard Overview":
            c1, c2, c3 = st.columns(3)
            
            with c1:
                prog = all_data['Allocated_Program'].value_counts() if 'Allocated_Program' in all_data.columns else pd.Series()
                if len(prog) > 0:
                    fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Program", height=280, margin=dict(t=30))
                    st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                stat = all_data['Allocation_Status'].value_counts() if 'Allocation_Status' in all_data.columns else pd.Series()
                if len(stat) > 0:
                    fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Status", height=280, margin=dict(t=30))
                    st.plotly_chart(fig, use_container_width=True)
            
            with c3:
                atsi_yes = (all_data['ATSI']=='Yes').sum()
                atsi_no = (all_data['ATSI']=='No').sum()
                fig = go.Figure([go.Pie(labels=['ATSI', 'Non-ATSI'], values=[atsi_yes, atsi_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="ATSI", height=280, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            
            c1, c2 = st.columns(2)
            with c1:
                swd_yes = (all_data['SWD']=='Yes').sum()
                swd_no = (all_data['SWD']=='No').sum()
                fig = go.Figure([go.Pie(labels=['SWD', 'Non-SWD'], values=[swd_yes, swd_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="SWD", height=280, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                eald_yes = (all_data['EALD']=='Yes').sum()
                eald_no = (all_data['EALD']=='No').sum()
                fig = go.Figure([go.Pie(labels=['EALD', 'Non-EALD'], values=[eald_yes, eald_no], marker=dict(colors=['#ffd93d', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="EALD", height=280, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
        
        elif st.session_state.view == "All Students":
            cols_to_show = [c for c in ['Allocated_Program', 'Allocation_Status', 'ATSI', 'SWD', 'EALD'] if c in all_data.columns]
            if cols_to_show:
                st.dataframe(all_data[cols_to_show], use_container_width=True, hide_index=True, height=400)
    
    except Exception as e:
        st.error(f"❌ Error: {e}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
