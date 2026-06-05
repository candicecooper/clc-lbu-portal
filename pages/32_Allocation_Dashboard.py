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
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2.5rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; font-weight: 600; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
p { color: #ffffff !important; }

.dashboard-title {
    background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 229, 255, 0.05) 100%);
    border: 2px solid rgba(0, 229, 255, 0.4);
    border-radius: 12px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 0 30px rgba(0, 229, 255, 0.15);
}
</style>

<div class="dashboard-title">
    <h1 style="margin: 0; text-align: center; color: #00e5ff; font-size: 2.8em; letter-spacing: 2px; font-weight: 800;">
        📊 CLC-LBU ALLOCATION DASHBOARD
    </h1>
    <p style="text-align: center; color: #ffffff; margin: 10px 0 0 0; font-size: 1.15em; font-weight: 500;">
        Student Allocation & Equity Analysis
    </p>
</div>
""", unsafe_allow_html=True)

if 'terms_selected' not in st.session_state:
    st.session_state.terms_selected = {2.0}
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
    
    st.markdown("**Term**")
    tc1, tc2, tc3 = st.columns(3)
    if tc1.button("All", key="t_all", use_container_width=True): 
        st.session_state.terms_selected = {1.0, 2.0, 3.0, 4.0}
    if tc2.button("None", key="t_none", use_container_width=True): 
        st.session_state.terms_selected = set()
    if tc3.button("T2 Now", key="t_current", use_container_width=True): 
        st.session_state.terms_selected = {2.0}
    
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

if uploaded_file is None:
    st.warning("📤 Upload your Excel file in the sidebar to begin")
else:
    try:
        all_data = pd.read_excel(uploaded_file)
        
        for col in all_data.columns:
            if all_data[col].dtype == 'object':
                all_data[col] = all_data[col].astype(str).str.strip()
        
        filtered = all_data[(all_data['Current_Status'] == 'Active') | (all_data['Current_Status'] == '2025')].copy()
        
        if st.session_state.terms_selected:
            filtered = filtered[filtered['Term'].isin(st.session_state.terms_selected)]
        
        if st.session_state.years_selected:
            filtered = filtered[filtered['Referral_Year'].isin(st.session_state.years_selected)]
        
        if st.session_state.programs_selected:
            filtered = filtered[filtered['Allocated_Program'].isin(st.session_state.programs_selected)]
        
        # METRICS - WHOLE NUMBERS ONLY
        total = int(len(filtered))
        allocated = int(len(filtered[filtered['Allocation_Status'] == 'Allocated']))
        atsi = int(len(filtered[filtered['Flag_ATSI'] == 'Yes']))
        eald = int(len(filtered[filtered['Flag_EALD'] == 'Yes']))
        swd = int(len(filtered[filtered['Flag_SWD'] == 'Yes']))
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Students", total)
        c2.metric("Allocated", allocated)
        c3.metric("ATSI", atsi)
        c4.metric("SWD", swd)
        c5.metric("EALD", eald)
        
        st.markdown("---")
        
        # PROGRAM DISTRIBUTION
        st.markdown("## Program Distribution")
        prog = filtered['Allocated_Program'].value_counts().sort_index()
        if len(prog) > 0:
            fig = go.Figure([go.Bar(
                x=prog.index, 
                y=prog.values, 
                marker_color=['#00e5ff', '#ffd93d', '#ff6b6b'][:len(prog)],
                text=prog.values.astype(int),
                textposition='outside',
                textfont=dict(size=16, color='#ffffff')
            )])
            fig.update_yaxes(dtick=1)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='#ffffff', size=14),
                height=350,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # ADELAIDE MAP WITH SATELLITE STYLE
        st.markdown("## 🗺️ Partnership Distribution Across Adelaide")
        
        partnership_coords = {
            'Inner West': (-34.800, 138.550),
            'Le Fevre Peninsula': (-34.820, 138.480),
            'Holdfast': (-35.030, 138.520),
            'West Torrens': (-34.870, 138.500),
            'Western Adelaide Shores': (-34.760, 138.400),
            'Marion Inland': (-35.130, 138.580),
            'Adelaide Prospect': (-34.930, 138.580),
        }
        
        partnership_data = filtered['Partnership_Area'].value_counts()
        
        lats, lons, sizes, labels, colors_list = [], [], [], [], []
        
        for part, (lat, lon) in partnership_coords.items():
            if part in partnership_data.index:
                count = int(partnership_data[part])
                lats.append(lat)
                lons.append(lon)
                sizes.append(max(20, count * 6))
                labels.append(f"<b>{part}</b><br>{count} students")
                colors_list.append(count)
        
        fig = go.Figure(data=go.Scattergeo(
            lon=lons, lat=lats, mode='markers+text',
            text=[p.split('<')[0].replace('<b>', '').replace('</b>', '') for p in labels],
            textposition='top center', textfont=dict(size=11, color='#00e5ff', family='Poppins'),
            marker=dict(
                size=sizes, 
                color=colors_list, 
                colorscale='Reds', 
                showscale=True,
                colorbar=dict(title="Students", tickcolor='#ffffff', tickfont=dict(color='#ffffff')),
                opacity=0.85, 
                line=dict(width=2, color='#00e5ff')
            ),
            hovertext=labels, 
            hoverinfo='text'
        ))
        
        fig.update_layout(
            title=dict(text='Click to zoom • Scroll to pan', x=0.5, xanchor='center'),
            geo=dict(
                scope='oceania',
                showland=True,
                landcolor='rgba(50, 50, 50, 0.6)',
                oceancolor='rgba(20, 20, 40, 0.4)',
                coastlinecolor='rgba(0, 229, 255, 0.5)',
                center=dict(lon=138.5, lat=-34.95),
                projection_type='mercator',
                lataxis_range=[-35.4, -34.5],
                lonaxis_range=[137.9, 139.1]
            ),
            paper_bgcolor='rgba(10,14,39,0.95)',
            plot_bgcolor='rgba(10,14,39,0.95)',
            font=dict(color='#ffffff', size=12),
            height=550,
            hovermode='closest',
            margin=dict(r=0, t=50, l=0, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # EQUITY ANALYSIS - ATSI
        st.markdown("## ATSI Equity Analysis")
        
        atsi_allocated = int(len(filtered[(filtered['Flag_ATSI'] == 'Yes') & (filtered['Allocation_Status'] == 'Allocated')]))
        atsi_total = int(len(filtered[filtered['Flag_ATSI'] == 'Yes']))
        non_atsi_allocated = int(len(filtered[(filtered['Flag_ATSI'] == 'No') & (filtered['Allocation_Status'] == 'Allocated')]))
        non_atsi_total = int(len(filtered[filtered['Flag_ATSI'] == 'No']))
        
        atsi_rate = (atsi_allocated / atsi_total * 100) if atsi_total > 0 else 0
        non_atsi_rate = (non_atsi_allocated / non_atsi_total * 100) if non_atsi_total > 0 else 0
        gap = atsi_rate - non_atsi_rate
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("ATSI Allocated", atsi_allocated)
        col2.metric("ATSI Allocation %", f"{int(atsi_rate)}%")
        col3.metric("Non-ATSI %", f"{int(non_atsi_rate)}%")
        col4.metric("Equity Gap", f"{int(gap):+d}%")
        
        fig = go.Figure(data=[
            go.Bar(
                x=['ATSI', 'Non-ATSI'], 
                y=[atsi_rate, non_atsi_rate], 
                marker_color=['#ff6b6b', '#10b981'], 
                text=[f'{int(atsi_rate)}%', f'{int(non_atsi_rate)}%'], 
                textposition='outside',
                textfont=dict(size=14, color='#ffffff')
            )
        ])
        fig.update_yaxes(dtick=20)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        atsi_by_prog = filtered[filtered['Flag_ATSI'] == 'Yes']['Allocated_Program'].value_counts().sort_index()
        if len(atsi_by_prog) > 0:
            fig = go.Figure([go.Bar(
                x=atsi_by_prog.index, 
                y=atsi_by_prog.values, 
                marker_color='#ff6b6b', 
                text=atsi_by_prog.values.astype(int), 
                textposition='outside',
                textfont=dict(size=14)
            )])
            fig.update_yaxes(dtick=1)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="ATSI by Program", height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # EQUITY ANALYSIS - EALD
        st.markdown("## EALD Equity Analysis")
        
        eald_allocated = int(len(filtered[(filtered['Flag_EALD'] == 'Yes') & (filtered['Allocation_Status'] == 'Allocated')]))
        eald_total = int(len(filtered[filtered['Flag_EALD'] == 'Yes']))
        non_eald_allocated = int(len(filtered[(filtered['Flag_EALD'] == 'No') & (filtered['Allocation_Status'] == 'Allocated')]))
        non_eald_total = int(len(filtered[filtered['Flag_EALD'] == 'No']))
        
        eald_rate = (eald_allocated / eald_total * 100) if eald_total > 0 else 0
        non_eald_rate = (non_eald_allocated / non_eald_total * 100) if non_eald_total > 0 else 0
        eald_gap = eald_rate - non_eald_rate
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("EALD Allocated", eald_allocated)
        col2.metric("EALD Allocation %", f"{int(eald_rate)}%")
        col3.metric("Non-EALD %", f"{int(non_eald_rate)}%")
        col4.metric("Equity Gap", f"{int(eald_gap):+d}%")
        
        fig = go.Figure(data=[
            go.Bar(
                x=['EALD', 'Non-EALD'], 
                y=[eald_rate, non_eald_rate], 
                marker_color=['#ffd93d', '#10b981'], 
                text=[f'{int(eald_rate)}%', f'{int(non_eald_rate)}%'], 
                textposition='outside',
                textfont=dict(size=14, color='#ffffff')
            )
        ])
        fig.update_yaxes(dtick=20)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        eald_by_prog = filtered[filtered['Flag_EALD'] == 'Yes']['Allocated_Program'].value_counts().sort_index()
        if len(eald_by_prog) > 0:
            fig = go.Figure([go.Bar(
                x=eald_by_prog.index, 
                y=eald_by_prog.values, 
                marker_color='#ffd93d', 
                text=eald_by_prog.values.astype(int), 
                textposition='outside',
                textfont=dict(size=14)
            )])
            fig.update_yaxes(dtick=1)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="EALD by Program", height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # TOP REFERRERS
        st.markdown("## Top Referring Schools")
        referrals = filtered['Referring_School'].value_counts().head(12)
        if len(referrals) > 0:
            fig = go.Figure([go.Bar(
                y=referrals.index, 
                x=referrals.values, 
                orientation='h', 
                marker_color='#00e5ff', 
                text=referrals.values.astype(int), 
                textposition='outside',
                textfont=dict(size=14)
            )])
            fig.update_xaxes(dtick=1)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.write(traceback.format_exc())

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-size: 0.9em;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
