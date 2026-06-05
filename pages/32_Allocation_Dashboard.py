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
.main { background-color: #0a0e27 !important; }
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
[data-testid="stSidebar"] { background-color: #0a0e27 !important; border-right: 2px solid #00e5ff !important; }
[data-testid="stSidebar"] * { color: #00e5ff !important; }
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
p, label { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# Initialize session state for MULTI-SELECT filters
if 'years_selected' not in st.session_state:
    st.session_state.years_selected = set()
if 'terms_selected' not in st.session_state:
    st.session_state.terms_selected = set()
if 'programs_selected' not in st.session_state:
    st.session_state.programs_selected = set()
if 'partnerships_selected' not in st.session_state:
    st.session_state.partnerships_selected = set()
if 'view' not in st.session_state:
    st.session_state.view = "Dashboard"

with st.sidebar:
    st.markdown("### 📤 UPLOAD DATA")
    uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls', 'csv'], key='main_uploader')
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
    
    st.markdown("---")
    st.markdown("### 📊 VIEW")
    st.session_state.view = st.radio("", ["Dashboard", "Disability Analysis", "School Referrals", "Extensions", "Partnership Map"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 FILTERS (Click to Select Multiple)")
    
    # YEAR FILTER - MULTI-SELECT
    st.markdown("**Year** (Select multiple)")
    yc1, yc2, yc3 = st.columns(3)
    if yc1.button("All", key="y_all", use_container_width=True): 
        st.session_state.years_selected = {2025.0, 2026.0}
    if yc2.button("None", key="y_none", use_container_width=True): 
        st.session_state.years_selected = set()
    
    y1_col, y2_col = st.columns(2)
    y1_selected = 2025.0 in st.session_state.years_selected
    y2_selected = 2026.0 in st.session_state.years_selected
    
    if y1_col.button("2025" + (" ✓" if y1_selected else ""), key="y1", use_container_width=True, 
                     help="Click to toggle"): 
        st.session_state.years_selected ^= {2025.0}
    
    if y2_col.button("2026" + (" ✓" if y2_selected else ""), key="y2", use_container_width=True,
                     help="Click to toggle"): 
        st.session_state.years_selected ^= {2026.0}
    
    if st.session_state.years_selected:
        st.write(f"**Selected:** {', '.join([str(int(y)) for y in sorted(st.session_state.years_selected)])}")
    
    # TERM FILTER - MULTI-SELECT
    st.markdown("**Term** (Select multiple)")
    tc1, tc2, tc3 = st.columns(3)
    if tc1.button("All", key="t_all", use_container_width=True): 
        st.session_state.terms_selected = {1.0, 2.0, 3.0, 4.0}
    if tc2.button("None", key="t_none", use_container_width=True): 
        st.session_state.terms_selected = set()
    
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
    
    # PROGRAM FILTER - MULTI-SELECT
    st.markdown("**Program** (Select multiple)")
    pc1, pc2, pc3 = st.columns(3)
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
    
    if st.session_state.programs_selected:
        st.write(f"**Selected:** {', '.join(sorted(st.session_state.programs_selected))}")
    
    # PARTNERSHIP FILTER - MULTI-SELECT
    st.markdown("**Partnership** (Select multiple)")
    partc1, partc2 = st.columns(2)
    if partc1.button("All", key="part_all", use_container_width=True): 
        if uploaded_file:
            all_data = pd.read_excel(uploaded_file)
            st.session_state.partnerships_selected = set(all_data['Partnership_Area'].dropna().unique())
    if partc2.button("None", key="part_none", use_container_width=True): 
        st.session_state.partnerships_selected = set()
    
    if uploaded_file:
        all_data = pd.read_excel(uploaded_file)
        partnerships = sorted(all_data['Partnership_Area'].dropna().unique())
        for part in partnerships[:8]:  # Show first 8
            part_sel = part in st.session_state.partnerships_selected
            if st.button(part[:18] + (" ✓" if part_sel else ""), key=f"part_{part}", use_container_width=True):
                st.session_state.partnerships_selected ^= {part}
        
        if len(partnerships) > 8:
            st.write(f"*(+{len(partnerships)-8} more partnerships)*")
    
    if st.session_state.partnerships_selected:
        st.write(f"**Selected:** {len(st.session_state.partnerships_selected)} partnership(ies)")

st.markdown("## Allocation Dashboard")

if uploaded_file is None:
    st.warning("📤 Upload your Excel file in the sidebar")
else:
    try:
        all_data = pd.read_excel(uploaded_file)
        
        # Clean data
        for col in all_data.columns:
            if all_data[col].dtype == 'object':
                all_data[col] = all_data[col].astype(str).str.strip()
        
        # Start with Active + 2025 students
        filtered = all_data[(all_data['Current_Status'] == 'Active') | (all_data['Current_Status'] == '2025')].copy()
        
        # APPLY MULTI-SELECT FILTERS
        if st.session_state.years_selected:
            filtered = filtered[filtered['Referral_Year'].isin(st.session_state.years_selected)]
        
        if st.session_state.terms_selected:
            filtered = filtered[filtered['Term'].isin(st.session_state.terms_selected)]
        
        if st.session_state.programs_selected:
            filtered = filtered[filtered['Allocated_Program'].isin(st.session_state.programs_selected)]
        
        if st.session_state.partnerships_selected:
            filtered = filtered[filtered['Partnership_Area'].isin(st.session_state.partnerships_selected)]
        
        # METRICS
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total", len(filtered))
        c2.metric("Allocated", len(filtered[filtered['Allocation_Status'] == 'Allocated']))
        c3.metric("Active", len(filtered[(filtered['Current_Status'] == 'Active') | (filtered['Current_Status'] == '2025')]))
        c4.metric("ATSI", len(filtered[filtered['Flag_ATSI'] == 'Yes']))
        c5.metric("SWD", len(filtered[filtered['Flag_SWD'] == 'Yes']))
        c6.metric("EALD", len(filtered[filtered['Flag_EALD'] == 'Yes']))
        
        st.markdown("---")
        
        if st.session_state.view == "Dashboard":
            c1, c2, c3 = st.columns(3)
            with c1:
                prog = filtered['Allocated_Program'].value_counts()
                fig = go.Figure([go.Bar(x=prog.index, y=prog.values, marker_color='#00e5ff')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Program", height=300, showlegend=False, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                stat = filtered['Allocation_Status'].value_counts()
                fig = go.Figure([go.Bar(x=stat.index, y=stat.values, marker_color='#00ff00')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Status", height=300, showlegend=False, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            with c3:
                atsi_yes = (filtered['Flag_ATSI'] == 'Yes').sum()
                atsi_no = len(filtered) - atsi_yes
                fig = go.Figure([go.Pie(labels=['ATSI', 'Non-ATSI'], values=[atsi_yes, atsi_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="ATSI", height=300, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                swd_yes = (filtered['Flag_SWD'] == 'Yes').sum()
                swd_no = len(filtered) - swd_yes
                fig = go.Figure([go.Pie(labels=['SWD', 'Non-SWD'], values=[swd_yes, swd_no], marker=dict(colors=['#ff6b6b', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="SWD", height=300, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                eald_yes = (filtered['Flag_EALD'] == 'Yes').sum()
                eald_no = len(filtered) - eald_yes
                fig = go.Figure([go.Pie(labels=['EALD', 'Non-EALD'], values=[eald_yes, eald_no], marker=dict(colors=['#ffd93d', '#10b981']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="EALD", height=300, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
            with c3:
                part = filtered['Partnership_Area'].value_counts().head(8)
                fig = go.Figure([go.Bar(y=part.index, x=part.values, orientation='h', marker_color='#ffd93d')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Partnership", height=300, showlegend=False, margin=dict(t=30))
                st.plotly_chart(fig, use_container_width=True)
        
        elif st.session_state.view == "Disability Analysis":
            st.markdown("### Disability Types Breakdown")
            
            disability_types = {
                'ASD': 'Flag_ASD',
                'ADHD': 'Flag_ADHD',
                'Speech & Language': 'Flag_Speech_and_Lang',
                'Intellectual': 'Flag_Intellectual',
                'Learning Difficulty': 'Flag_Learning_Difficulty',
                'Sensory Processing': 'Flag_Sensory_Processing',
                'ODD': 'Flag_ODD',
                'PDA': 'Flag_PDA'
            }
            
            disability_counts = {name: len(filtered[filtered[col] == 'Yes']) for name, col in disability_types.items()}
            
            c1, c2 = st.columns(2)
            with c1:
                fig = go.Figure([go.Bar(x=list(disability_counts.keys()), y=list(disability_counts.values()), marker_color='#ff6b6b')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Disability Type Counts", height=400, showlegend=False, xaxis_title="", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                # Heatmap: Partnerships x Disability Types
                partnerships = sorted(filtered['Partnership_Area'].unique())
                heatmap_data = []
                for partner in partnerships:
                    partner_data = filtered[filtered['Partnership_Area'] == partner]
                    row = [len(partner_data[partner_data[col] == 'Yes']) for _, col in disability_types.items()]
                    heatmap_data.append(row)
                
                fig = go.Figure(data=go.Heatmap(
                    z=heatmap_data,
                    x=list(disability_types.keys()),
                    y=partnerships,
                    colorscale='Reds',
                    text=np.array(heatmap_data),
                    texttemplate='%{text}',
                    textfont={"size": 10},
                    colorbar=dict(title="Count")
                ))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Disability Heatmap: Partnership x Type", height=400, xaxis_title="", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
        
        elif st.session_state.view == "School Referrals":
            st.markdown("### Who Refers The Most?")
            
            referrals = filtered['Referring_School'].value_counts().head(15)
            fig = go.Figure([go.Bar(y=referrals.index, x=referrals.values, orientation='h', marker_color='#00e5ff')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Top Referring Schools", height=500, showlegend=False, xaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
        
        elif st.session_state.view == "Extensions":
            st.markdown("### Placement Extensions Analysis")
            
            if 'Extended_Placement' in filtered.columns:
                fig = go.Figure([go.Pie(labels=['Standard', 'Extended'], values=[len(filtered[filtered['Extended_Placement'] != 'Yes']), len(filtered[filtered['Extended_Placement'] == 'Yes'])], marker=dict(colors=['#10b981', '#ffd93d']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Standard vs Extended Placements", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.markdown(f"**Standard Placements:** {len(filtered[filtered['Extended_Placement'] != 'Yes'])}")
                st.markdown(f"**Extended Placements:** {len(filtered[filtered['Extended_Placement'] == 'Yes'])}")
        
        elif st.session_state.view == "Partnership Map":
            st.markdown("### Partnership Referral Heatmap")
            
            # Create heatmap: Top schools x Partnerships
            top_schools = filtered['Referring_School'].value_counts().head(12).index.tolist()
            partnerships = sorted(filtered['Partnership_Area'].unique())
            
            heatmap_data = []
            for school in top_schools:
                row = []
                for part in partnerships:
                    count = len(filtered[(filtered['Referring_School'] == school) & (filtered['Partnership_Area'] == part)])
                    row.append(count)
                heatmap_data.append(row)
            
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data,
                x=partnerships,
                y=top_schools,
                colorscale='YlOrRd',
                text=np.array(heatmap_data),
                texttemplate='%{text}',
                textfont={"size": 10},
                colorbar=dict(title="Referrals")
            ))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Schools x Partnerships - Referral Heatmap", height=500, xaxis_title="Partnership Area", yaxis_title="Referring School")
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### Partnership Summary")
            partnership_stats = []
            for partner in partnerships:
                p_data = filtered[filtered['Partnership_Area'] == partner]
                partnership_stats.append({
                    'Partnership': partner,
                    'Total': len(p_data),
                    'ATSI': len(p_data[p_data['Flag_ATSI'] == 'Yes']),
                    'SWD': len(p_data[p_data['Flag_SWD'] == 'Yes']),
                    'EALD': len(p_data[p_data['Flag_EALD'] == 'Yes']),
                    'Schools': p_data['Referring_School'].nunique()
                })
            
            partnership_df = pd.DataFrame(partnership_stats)
            st.dataframe(partnership_df, use_container_width=True, hide_index=True)
    
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.write(traceback.format_exc())

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
