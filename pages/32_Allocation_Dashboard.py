import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

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

# Initialize session state
if 'year_filter' not in st.session_state:
    st.session_state.year_filter = None
if 'partnership_filter' not in st.session_state:
    st.session_state.partnership_filter = None
if 'school_filter' not in st.session_state:
    st.session_state.school_filter = None
if 'term_filter' not in st.session_state:
    st.session_state.term_filter = None
if 'program_filter' not in st.session_state:
    st.session_state.program_filter = None
if 'atsi_filter' not in st.session_state:
    st.session_state.atsi_filter = None
if 'swd_filter' not in st.session_state:
    st.session_state.swd_filter = None
if 'eald_filter' not in st.session_state:
    st.session_state.eald_filter = None
if 'status_filter' not in st.session_state:
    st.session_state.status_filter = None
if 'view' not in st.session_state:
    st.session_state.view = "Current Status"

with st.sidebar:
    st.markdown("### 📤 UPLOAD DATA")
    uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls', 'csv'], key='main_uploader')
    
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
    
    st.markdown("---")
    st.markdown("### 📊 VIEW")
    st.session_state.view = st.radio("", ["Current Status", "All Students"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 FILTERS")
    
    # YEAR FILTER
    st.markdown("**Year**")
    yc1, yc2 = st.columns(2)
    if yc1.button("All Years", key="y_all", use_container_width=True): 
        st.session_state.year_filter = None
    if yc2.button("Clear", key="y_clear", use_container_width=True): 
        st.session_state.year_filter = None
    y1, y2 = st.columns(2)
    if y1.button("2025", use_container_width=True, key="y1"): 
        st.session_state.year_filter = 2025.0
    if y2.button("2026", use_container_width=True, key="y2"): 
        st.session_state.year_filter = 2026.0
    if st.session_state.year_filter is not None:
        st.write(f"**Showing:** {int(st.session_state.year_filter)}")
    
    # TERM FILTER
    st.markdown("**Term**")
    tc1, tc2 = st.columns(2)
    if tc1.button("All Terms", key="t_all", use_container_width=True): 
        st.session_state.term_filter = None
    if tc2.button("Clear", key="t_clear", use_container_width=True): 
        st.session_state.term_filter = None
    t1, t2, t3, t4 = st.columns(4)
    if t1.button("T1", use_container_width=True, key="t1"): 
        st.session_state.term_filter = 1.0
    if t2.button("T2", use_container_width=True, key="t2"): 
        st.session_state.term_filter = 2.0
    if t3.button("T3", use_container_width=True, key="t3"): 
        st.session_state.term_filter = 3.0
    if t4.button("T4", use_container_width=True, key="t4"): 
        st.session_state.term_filter = 4.0
    if st.session_state.term_filter is not None:
        st.write(f"**Showing:** Term {int(st.session_state.term_filter)}")
    
    # PROGRAM FILTER
    st.markdown("**Program**")
    pc1, pc2 = st.columns(2)
    if pc1.button("All Programs", key="p_all", use_container_width=True): 
        st.session_state.program_filter = None
    if pc2.button("Clear", key="p_clear", use_container_width=True): 
        st.session_state.program_filter = None
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", use_container_width=True, key="p1"): 
        st.session_state.program_filter = "JP"
    if p2.button("PY", use_container_width=True, key="p2"): 
        st.session_state.program_filter = "PY"
    if p3.button("SY", use_container_width=True, key="p3"): 
        st.session_state.program_filter = "SY"
    if st.session_state.program_filter is not None:
        st.write(f"**Showing:** {st.session_state.program_filter}")
    
    # PARTNERSHIP FILTER
    st.markdown("**Partnership**")
    partc1, partc2 = st.columns(2)
    if partc1.button("All Partnerships", key="part_all", use_container_width=True): 
        st.session_state.partnership_filter = None
    if partc2.button("Clear", key="part_clear", use_container_width=True): 
        st.session_state.partnership_filter = None
    
    if uploaded_file:
        all_data = pd.read_excel(uploaded_file)
        partnerships = sorted(all_data['Partnership_Area'].dropna().unique())
        
        # Show as buttons for main ones, dropdown for all
        if len(partnerships) <= 8:
            for i, part in enumerate(partnerships):
                if (i % 2) == 0:
                    col1, col2 = st.columns(2)
                if i % 2 == 0:
                    if col1.button(part[:15], use_container_width=True, key=f"part_{i}"):
                        st.session_state.partnership_filter = part
                else:
                    if col2.button(part[:15], use_container_width=True, key=f"part_{i}"):
                        st.session_state.partnership_filter = part
        else:
            st.session_state.partnership_filter = st.selectbox("Select Partnership", [None] + partnerships, key="part_select", format_func=lambda x: "All" if x is None else x)
    
    if st.session_state.partnership_filter is not None:
        st.write(f"**Showing:** {st.session_state.partnership_filter[:20]}")
    
    # SCHOOL FILTER
    st.markdown("**Referring School**")
    sc1, sc2 = st.columns(2)
    if sc1.button("All Schools", key="sch_all", use_container_width=True): 
        st.session_state.school_filter = None
    if sc2.button("Clear", key="sch_clear", use_container_width=True): 
        st.session_state.school_filter = None
    
    if uploaded_file:
        all_data = pd.read_excel(uploaded_file)
        schools = sorted(all_data['Referring_School'].dropna().unique())
        st.session_state.school_filter = st.selectbox("Select School", [None] + schools, key="sch_select", format_func=lambda x: "All" if x is None else x)
    
    if st.session_state.school_filter is not None:
        st.write(f"**Showing:** {st.session_state.school_filter[:25]}")
    
    # ATSI FILTER
    st.markdown("**ATSI**")
    ac1, ac2 = st.columns(2)
    if ac1.button("All ATSI", key="a_all", use_container_width=True): 
        st.session_state.atsi_filter = None
    if ac2.button("Clear", key="a_clear", use_container_width=True): 
        st.session_state.atsi_filter = None
    a1, a2 = st.columns(2)
    if a1.button("Yes", use_container_width=True, key="a1"): 
        st.session_state.atsi_filter = "Yes"
    if a2.button("No", use_container_width=True, key="a2"): 
        st.session_state.atsi_filter = "No"
    if st.session_state.atsi_filter is not None:
        st.write(f"**Showing:** {st.session_state.atsi_filter}")
    
    # SWD FILTER
    st.markdown("**SWD**")
    swdc1, swdc2 = st.columns(2)
    if swdc1.button("All SWD", key="swd_all", use_container_width=True): 
        st.session_state.swd_filter = None
    if swdc2.button("Clear", key="swd_clear", use_container_width=True): 
        st.session_state.swd_filter = None
    swd1, swd2 = st.columns(2)
    if swd1.button("Yes", use_container_width=True, key="swd1"): 
        st.session_state.swd_filter = "Yes"
    if swd2.button("No", use_container_width=True, key="swd2"): 
        st.session_state.swd_filter = "No"
    if st.session_state.swd_filter is not None:
        st.write(f"**Showing:** {st.session_state.swd_filter}")
    
    # EALD FILTER
    st.markdown("**EALD**")
    ec1, ec2 = st.columns(2)
    if ec1.button("All EALD", key="e_all", use_container_width=True): 
        st.session_state.eald_filter = None
    if ec2.button("Clear", key="e_clear", use_container_width=True): 
        st.session_state.eald_filter = None
    e1, e2 = st.columns(2)
    if e1.button("Yes", use_container_width=True, key="e1"): 
        st.session_state.eald_filter = "Yes"
    if e2.button("No", use_container_width=True, key="e2"): 
        st.session_state.eald_filter = "No"
    if st.session_state.eald_filter is not None:
        st.write(f"**Showing:** {st.session_state.eald_filter}")

st.markdown("## Allocation Dashboard")

if uploaded_file is None:
    st.warning("📤 Use the upload button in the sidebar to load your Excel file")
else:
    try:
        all_data = pd.read_excel(uploaded_file)
        
        # Clean data
        all_data['Flag_ATSI'] = all_data['Flag_ATSI'].astype(str).str.strip()
        all_data['Flag_SWD'] = all_data['Flag_SWD'].astype(str).str.strip()
        all_data['Flag_EALD'] = all_data['Flag_EALD'].astype(str).str.strip()
        all_data['Allocated_Program'] = all_data['Allocated_Program'].astype(str).str.strip()
        all_data['Current_Status'] = all_data['Current_Status'].astype(str).str.strip()
        all_data['Partnership_Area'] = all_data['Partnership_Area'].astype(str).str.strip()
        all_data['Referring_School'] = all_data['Referring_School'].astype(str).str.strip()
        
        # START WITH ACTIVE STUDENTS
        filtered = all_data[all_data['Current_Status'] == 'Active'].copy()
        
        # APPLY FILTERS
        if st.session_state.year_filter is not None:
            filtered = filtered[filtered['Referral_Year'] == st.session_state.year_filter]
        
        if st.session_state.term_filter is not None:
            filtered = filtered[filtered['Term'] == st.session_state.term_filter]
        
        if st.session_state.program_filter is not None:
            filtered = filtered[filtered['Allocated_Program'] == st.session_state.program_filter]
        
        if st.session_state.partnership_filter is not None:
            filtered = filtered[filtered['Partnership_Area'] == st.session_state.partnership_filter]
        
        if st.session_state.school_filter is not None:
            filtered = filtered[filtered['Referring_School'] == st.session_state.school_filter]
        
        if st.session_state.atsi_filter is not None:
            filtered = filtered[filtered['Flag_ATSI'] == st.session_state.atsi_filter]
        
        if st.session_state.swd_filter is not None:
            filtered = filtered[filtered['Flag_SWD'] == st.session_state.swd_filter]
        
        if st.session_state.eald_filter is not None:
            filtered = filtered[filtered['Flag_EALD'] == st.session_state.eald_filter]
        
        if st.session_state.status_filter == "Allocated":
            filtered = filtered[filtered['Allocation_Status'] == 'Allocated']
        elif st.session_state.status_filter == "Active":
            filtered = filtered[filtered['Current_Status'] == 'Active']
        
        # METRICS
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total", len(filtered))
        c2.metric("Allocated", len(filtered[filtered['Allocation_Status'] == 'Allocated']))
        c3.metric("Active", len(filtered[filtered['Current_Status'] == 'Active']))
        c4.metric("ATSI", len(filtered[filtered['Flag_ATSI'] == 'Yes']))
        c5.metric("SWD", len(filtered[filtered['Flag_SWD'] == 'Yes']))
        c6.metric("EALD", len(filtered[filtered['Flag_EALD'] == 'Yes']))
        
        st.markdown("---")
        
        if st.session_state.view == "Current Status":
            c1, c2, c3 = st.columns(3)
            
            with c1:
                prog = filtered['Allocated_Program'].value_counts()
                if len(prog) > 0:
                    fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Program", height=280, margin=dict(t=30), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                stat = filtered['Allocation_Status'].value_counts()
                if len(stat) > 0:
                    fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="Allocation Status", height=280, margin=dict(t=30), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            
            with c3:
                atsi_yes = (filtered['Flag_ATSI'] == 'Yes').sum()
                atsi_no = (filtered['Flag_ATSI'] == 'No').sum()
                fig = go.Figure([go.Pie(labels=['ATSI', 'Non-ATSI'], values=[atsi_yes, atsi_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="ATSI Distribution", height=280, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                swd_yes = (filtered['Flag_SWD'] == 'Yes').sum()
                swd_no = (filtered['Flag_SWD'] == 'No').sum()
                fig = go.Figure([go.Pie(labels=['SWD', 'Non-SWD'], values=[swd_yes, swd_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="SWD Distribution", height=280, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                eald_yes = (filtered['Flag_EALD'] == 'Yes').sum()
                eald_no = (filtered['Flag_EALD'] == 'No').sum()
                fig = go.Figure([go.Pie(labels=['EALD', 'Non-EALD'], values=[eald_yes, eald_no], marker=dict(colors=['#ffd93d', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=11), title="EALD Distribution", height=280, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            
            with c3:
                part = filtered['Partnership_Area'].value_counts()
                if len(part) > 0:
                    fig = go.Figure([go.Bar(x=part.index, y=part.values, marker_color='#ffd93d')])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff', size=9), title="Partnership", height=280, margin=dict(t=30), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
        
        elif st.session_state.view == "All Students":
            cols_to_show = [c for c in ['Allocated_Program', 'Allocation_Status', 'Current_Status', 'Term', 'Partnership_Area', 'Referring_School', 'Flag_ATSI', 'Flag_SWD', 'Flag_EALD'] if c in filtered.columns]
            if cols_to_show:
                st.dataframe(filtered[cols_to_show], use_container_width=True, hide_index=True, height=400)
    
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.write(traceback.format_exc())

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
