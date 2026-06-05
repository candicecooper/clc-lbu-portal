import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
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
if 'terms_selected' not in st.session_state:
    st.session_state.terms_selected = {4.0}  # Default to Term 4
if 'years_selected' not in st.session_state:
    st.session_state.years_selected = set()
if 'programs_selected' not in st.session_state:
    st.session_state.programs_selected = set()

with st.sidebar:
    st.markdown("### 📤 UPLOAD DATA")
    uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls', 'csv'], key='main_uploader')
    
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
    
    st.markdown("---")
    st.markdown("### 🎯 FILTERS")
    
    # TERM FILTER - PROPER MULTI-SELECT
    st.markdown("**Term (Select Multiple)**")
    tc1, tc2, tc3 = st.columns(3)
    if tc1.button("All Terms", key="t_all", use_container_width=True): 
        st.session_state.terms_selected = {1.0, 2.0, 3.0, 4.0}
    if tc2.button("None", key="t_none", use_container_width=True): 
        st.session_state.terms_selected = set()
    if tc3.button("Current (4)", key="t_current", use_container_width=True): 
        st.session_state.terms_selected = {4.0}
    
    t1, t2, t3, t4 = st.columns(4)
    t1_sel = 1.0 in st.session_state.terms_selected
    t2_sel = 2.0 in st.session_state.terms_selected
    t3_sel = 3.0 in st.session_state.terms_selected
    t4_sel = 4.0 in st.session_state.terms_selected
    
    if t1.button("T1" + (" ✓" if t1_sel else ""), key="t1", use_container_width=True): 
        st.session_state.terms_selected ^= {1.0}
    if t2.button("T2" + (" ✓" if t2_sel else ""), key="t2", use_container_width=True): 
        st.session_state.terms_selected ^= {2.0}
    if t3.button("T3" + (" ✓" if t3_sel else ""), key="t3", use_container_width=True): 
        st.session_state.terms_selected ^= {3.0}
    if t4.button("T4" + (" ✓" if t4_sel else ""), key="t4", use_container_width=True): 
        st.session_state.terms_selected ^= {4.0}
    
    if st.session_state.terms_selected:
        st.write(f"**Selected:** {', '.join([f'T{int(t)}' for t in sorted(st.session_state.terms_selected)])}")
    
    # YEAR FILTER
    st.markdown("**Year**")
    yc1, yc2 = st.columns(2)
    if yc1.button("All", key="y_all", use_container_width=True): 
        st.session_state.years_selected = {2025.0, 2026.0}
    if yc2.button("None", key="y_none", use_container_width=True): 
        st.session_state.years_selected = set()
    
    y1, y2 = st.columns(2)
    y1_sel = 2025.0 in st.session_state.years_selected
    y2_sel = 2026.0 in st.session_state.years_selected
    
    if y1.button("2025" + (" ✓" if y1_sel else ""), key="y1", use_container_width=True): 
        st.session_state.years_selected ^= {2025.0}
    if y2.button("2026" + (" ✓" if y2_sel else ""), key="y2", use_container_width=True): 
        st.session_state.years_selected ^= {2026.0}
    
    # PROGRAM FILTER
    st.markdown("**Program**")
    pc1, pc2 = st.columns(2)
    if pc1.button("All", key="p_all", use_container_width=True): 
        st.session_state.programs_selected = {"JP", "PY", "SY"}
    if pc2.button("None", key="p_none", use_container_width=True): 
        st.session_state.programs_selected = set()
    
    p1, p2, p3 = st.columns(3)
    p1_sel = "JP" in st.session_state.programs_selected
    p2_sel = "PY" in st.session_state.programs_selected
    p3_sel = "SY" in st.session_state.programs_selected
    
    if p1.button("JP" + (" ✓" if p1_sel else ""), key="p1", use_container_width=True): 
        st.session_state.programs_selected ^= {"JP"}
    if p2.button("PY" + (" ✓" if p2_sel else ""), key="p2", use_container_width=True): 
        st.session_state.programs_selected ^= {"PY"}
    if p3.button("SY" + (" ✓" if p3_sel else ""), key="p3", use_container_width=True): 
        st.session_state.programs_selected ^= {"SY"}

st.markdown("# 📊 CLC Allocation Dashboard")

if uploaded_file is None:
    st.warning("📤 Upload your Excel file in the sidebar to begin")
else:
    try:
        all_data = pd.read_excel(uploaded_file)
        
        # Clean data
        for col in all_data.columns:
            if all_data[col].dtype == 'object':
                all_data[col] = all_data[col].astype(str).str.strip()
        
        # Start with Active + 2025 students
        filtered = all_data[(all_data['Current_Status'] == 'Active') | (all_data['Current_Status'] == '2025')].copy()
        
        # APPLY FILTERS
        if st.session_state.terms_selected:
            filtered = filtered[filtered['Term'].isin(st.session_state.terms_selected)]
        
        if st.session_state.years_selected:
            filtered = filtered[filtered['Referral_Year'].isin(st.session_state.years_selected)]
        
        if st.session_state.programs_selected:
            filtered = filtered[filtered['Allocated_Program'].isin(st.session_state.programs_selected)]
        
        # FILTER TITLE
        filter_text = "**Filters Applied:** "
        parts = []
        if st.session_state.terms_selected:
            parts.append(f"Terms: {', '.join([f'T{int(t)}' for t in sorted(st.session_state.terms_selected)])}")
        if st.session_state.years_selected:
            parts.append(f"Years: {', '.join([str(int(y)) for y in sorted(st.session_state.years_selected)])}")
        if st.session_state.programs_selected:
            parts.append(f"Programs: {', '.join(sorted(st.session_state.programs_selected))}")
        
        if parts:
            st.markdown(filter_text + " | ".join(parts))
        else:
            st.markdown("**No filters applied - showing all data**")
        
        st.markdown("---")
        
        # METRICS
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total", len(filtered))
        c2.metric("Allocated", len(filtered[filtered['Allocation_Status'] == 'Allocated']))
        c3.metric("Active", len(filtered[(filtered['Current_Status'] == 'Active') | (filtered['Current_Status'] == '2025')]))
        c4.metric("ATSI", len(filtered[filtered['Flag_ATSI'] == 'Yes']))
        c5.metric("SWD", len(filtered[filtered['Flag_SWD'] == 'Yes']))
        c6.metric("EALD", len(filtered[filtered['Flag_EALD'] == 'Yes']))
        
        st.markdown("---")
        
        # MAIN DASHBOARD
        st.markdown("## Current Term Overview")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            prog = filtered['Allocated_Program'].value_counts()
            if len(prog) > 0:
                fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Program", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            stat = filtered['Allocation_Status'].value_counts()
            if len(stat) > 0:
                fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Status", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with c3:
            atsi_yes = (filtered['Flag_ATSI'] == 'Yes').sum()
            atsi_no = len(filtered) - atsi_yes
            fig = go.Figure([go.Pie(labels=['ATSI', 'Non-ATSI'], values=[atsi_yes, atsi_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="ATSI Distribution", height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            swd_yes = (filtered['Flag_SWD'] == 'Yes').sum()
            swd_no = len(filtered) - swd_yes
            fig = go.Figure([go.Pie(labels=['SWD', 'Non-SWD'], values=[swd_yes, swd_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="SWD Distribution", height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            eald_yes = (filtered['Flag_EALD'] == 'Yes').sum()
            eald_no = len(filtered) - eald_yes
            fig = go.Figure([go.Pie(labels=['EALD', 'Non-EALD'], values=[eald_yes, eald_no], marker=dict(colors=['#ffd93d', '#10b981']))])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="EALD Distribution", height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with c3:
            part = filtered['Partnership_Area'].value_counts().head(8)
            if len(part) > 0:
                fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#ffd93d')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Partnership", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        # ADELAIDE MAP WITH PARTNERSHIPS
        st.markdown("---")
        st.markdown("## Partnership Distribution Across Adelaide")
        
        partnership_coords = {
            'Inner West': (-34.8, 138.55),
            'Le Fevre Peninsula': (-34.82, 138.48),
            'Holdfast': (-35.03, 138.52),
            'West Torrens': (-34.87, 138.5),
            'Western Adelaide Shores': (-34.76, 138.4),
            'Marion Inland': (-35.13, 138.58),
            'Adelaide Prospect': (-34.93, 138.58),
        }
        
        partnership_data = filtered['Partnership_Area'].value_counts()
        
        lats = []
        lons = []
        sizes = []
        labels = []
        
        for part, coord in partnership_coords.items():
            if part in partnership_data.index:
                lats.append(coord[0])
                lons.append(coord[1])
                sizes.append(partnership_data[part] * 8)
                labels.append(f"{part}: {partnership_data[part]}")
        
        fig = go.Figure(data=go.Scattergeo(
            lon=lons,
            lat=lats,
            mode='markers+text',
            text=[p.split(':')[0] for p in labels],
            textposition='top center',
            marker=dict(
                size=sizes,
                color=sizes,
                colorscale='Reds',
                showscale=True,
                colorbar=dict(title="Students"),
                opacity=0.7
            ),
            hovertext=labels,
            hoverinfo='text'
        ))
        
        fig.update_layout(
            title='Partnership Locations & Allocation Volume',
            geo=dict(
                scope='oceania',
                showland=True,
                landcolor='rgba(100,100,100,0.2)',
                center=dict(lon=138.5, lat=-34.95),
                projection_type='mercator',
                visible=True
            ),
            paper_bgcolor='rgba(10,14,39,0.9)',
            plot_bgcolor='rgba(10,14,39,0.9)',
            font=dict(color='#ffffff'),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # ATSI ANALYSIS
        st.markdown("---")
        st.markdown("## ATSI Analysis & Drill Down")
        
        atsi_students = filtered[filtered['Flag_ATSI'] == 'Yes']
        non_atsi_students = filtered[filtered['Flag_ATSI'] == 'No']
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**ATSI Students:** {len(atsi_students)} ({len(atsi_students)/len(filtered)*100:.1f}%)")
            st.markdown(f"**ATSI Allocated:** {len(atsi_students[atsi_students['Allocation_Status'] == 'Allocated'])} ({len(atsi_students[atsi_students['Allocation_Status'] == 'Allocated'])/len(atsi_students)*100:.0f}%)" if len(atsi_students) > 0 else "N/A")
        
        with c2:
            st.markdown(f"**Non-ATSI Students:** {len(non_atsi_students)} ({len(non_atsi_students)/len(filtered)*100:.1f}%)")
            st.markdown(f"**Non-ATSI Allocated:** {len(non_atsi_students[non_atsi_students['Allocation_Status'] == 'Allocated'])} ({len(non_atsi_students[non_atsi_students['Allocation_Status'] == 'Allocated'])/len(non_atsi_students)*100:.0f}%)" if len(non_atsi_students) > 0 else "N/A")
        
        c1, c2 = st.columns(2)
        with c1:
            atsi_prog = atsi_students['Allocated_Program'].value_counts()
            if len(atsi_prog) > 0:
                fig = go.Figure([go.Bar(x=atsi_prog.index, y=atsi_prog.values, marker_color='#ff6b6b')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="ATSI by Program", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            atsi_part = atsi_students['Partnership_Area'].value_counts()
            if len(atsi_part) > 0:
                fig = go.Figure([go.Bar(y=atsi_part.index, x=atsi_part.values, orientation='h', marker_color='#ff6b6b')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="ATSI by Partnership", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        # EALD ANALYSIS
        st.markdown("---")
        st.markdown("## EALD Analysis & Drill Down")
        
        eald_students = filtered[filtered['Flag_EALD'] == 'Yes']
        non_eald_students = filtered[filtered['Flag_EALD'] == 'No']
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**EALD Students:** {len(eald_students)} ({len(eald_students)/len(filtered)*100:.1f}%)")
            st.markdown(f"**EALD Allocated:** {len(eald_students[eald_students['Allocation_Status'] == 'Allocated'])} ({len(eald_students[eald_students['Allocation_Status'] == 'Allocated'])/len(eald_students)*100:.0f}%)" if len(eald_students) > 0 else "N/A")
        
        with c2:
            st.markdown(f"**Non-EALD Students:** {len(non_eald_students)} ({len(non_eald_students)/len(filtered)*100:.1f}%)")
            st.markdown(f"**Non-EALD Allocated:** {len(non_eald_students[non_eald_students['Allocation_Status'] == 'Allocated'])} ({len(non_eald_students[non_eald_students['Allocation_Status'] == 'Allocated'])/len(non_eald_students)*100:.0f}%)" if len(non_eald_students) > 0 else "N/A")
        
        c1, c2 = st.columns(2)
        with c1:
            eald_prog = eald_students['Allocated_Program'].value_counts()
            if len(eald_prog) > 0:
                fig = go.Figure([go.Bar(x=eald_prog.index, y=eald_prog.values, marker_color='#ffd93d')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="EALD by Program", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            eald_part = eald_students['Partnership_Area'].value_counts()
            if len(eald_part) > 0:
                fig = go.Figure([go.Bar(y=eald_part.index, x=eald_part.values, orientation='h', marker_color='#ffd93d')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="EALD by Partnership", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        # SCHOOL REFERRALS
        st.markdown("---")
        st.markdown("## Top Referring Schools")
        
        referrals = filtered['Referring_School'].value_counts().head(15)
        if len(referrals) > 0:
            fig = go.Figure([go.Bar(y=referrals.index, x=referrals.values, orientation='h', marker_color='#00e5ff')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Top 15 Referrers", height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # EXTENSIONS
        st.markdown("---")
        st.markdown("## Placement Extensions")
        
        if 'Extended_Placement' in filtered.columns:
            ext_count = len(filtered[filtered['Extended_Placement'] == 'Yes'])
            std_count = len(filtered[filtered['Extended_Placement'] != 'Yes'])
            
            fig = go.Figure([go.Pie(labels=['Standard Placement', 'Extended Placement'], values=[std_count, ext_count], marker=dict(colors=['#10b981', '#ffd93d']))])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Placement Types", height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.write(traceback.format_exc())

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
