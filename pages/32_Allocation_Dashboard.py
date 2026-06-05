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
p { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
filters = {
    'year_filter': None, 'term_filter': None, 'program_filter': None,
    'partnership_filter': None, 'school_filter': None, 'atsi_filter': None,
    'swd_filter': None, 'eald_filter': None, 'status_filter': None
}
for key in filters:
    if key not in st.session_state:
        st.session_state[key] = None
if 'view' not in st.session_state:
    st.session_state.view = "Dashboard"

with st.sidebar:
    st.markdown("### 📤 UPLOAD DATA")
    uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls', 'csv'], key='main_uploader')
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
    
    st.markdown("---")
    st.markdown("### 📊 VIEW")
    st.session_state.view = st.radio("", ["Dashboard", "Disability Analysis", "School Referrals", "Extensions", "Partnerships"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 FILTERS")
    
    yc1, yc2 = st.columns(2)
    if yc1.button("All Years", key="y_all"): st.session_state.year_filter = None
    if yc2.button("Clear", key="y_clear"): st.session_state.year_filter = None
    y1, y2 = st.columns(2)
    if y1.button("2025", key="y1"): st.session_state.year_filter = 2025.0
    if y2.button("2026", key="y2"): st.session_state.year_filter = 2026.0
    if st.session_state.year_filter is not None: st.write(f"**Showing:** {int(st.session_state.year_filter)}")
    
    st.markdown("**Term**")
    tc1, tc2 = st.columns(2)
    if tc1.button("All Terms", key="t_all"): st.session_state.term_filter = None
    if tc2.button("Clear", key="t_clear"): st.session_state.term_filter = None
    t1, t2, t3, t4 = st.columns(4)
    if t1.button("T1", key="t1"): st.session_state.term_filter = 1.0
    if t2.button("T2", key="t2"): st.session_state.term_filter = 2.0
    if t3.button("T3", key="t3"): st.session_state.term_filter = 3.0
    if t4.button("T4", key="t4"): st.session_state.term_filter = 4.0
    if st.session_state.term_filter is not None: st.write(f"**Showing:** Term {int(st.session_state.term_filter)}")
    
    st.markdown("**Program**")
    pc1, pc2 = st.columns(2)
    if pc1.button("All Programs", key="p_all"): st.session_state.program_filter = None
    if pc2.button("Clear", key="p_clear"): st.session_state.program_filter = None
    p1, p2, p3 = st.columns(3)
    if p1.button("JP", key="p1"): st.session_state.program_filter = "JP"
    if p2.button("PY", key="p2"): st.session_state.program_filter = "PY"
    if p3.button("SY", key="p3"): st.session_state.program_filter = "SY"
    if st.session_state.program_filter is not None: st.write(f"**Showing:** {st.session_state.program_filter}")
    
    st.markdown("**Partnership**")
    partc1, partc2 = st.columns(2)
    if partc1.button("All", key="part_all"): st.session_state.partnership_filter = None
    if partc2.button("Clear", key="part_clear"): st.session_state.partnership_filter = None
    if uploaded_file:
        all_data = pd.read_excel(uploaded_file)
        partnerships = sorted(all_data['Partnership_Area'].dropna().unique())
        st.session_state.partnership_filter = st.selectbox("Select", [None] + partnerships, key="part_select", format_func=lambda x: "All" if x is None else x)

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
        
        # FIX: Include both "Active" and "2025" status for current cohort
        filtered = all_data[(all_data['Current_Status'] == 'Active') | (all_data['Current_Status'] == '2025')].copy()
        
        # Apply filters
        if st.session_state.year_filter is not None:
            filtered = filtered[filtered['Referral_Year'] == st.session_state.year_filter]
        if st.session_state.term_filter is not None:
            filtered = filtered[filtered['Term'] == st.session_state.term_filter]
        if st.session_state.program_filter is not None:
            filtered = filtered[filtered['Allocated_Program'] == st.session_state.program_filter]
        if st.session_state.partnership_filter is not None:
            filtered = filtered[filtered['Partnership_Area'] == st.session_state.partnership_filter]
        
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
                partnerships = filtered['Partnership_Area'].unique()
                heatmap_data = []
                for partner in sorted(partnerships):
                    partner_data = filtered[filtered['Partnership_Area'] == partner]
                    row = [len(partner_data[partner_data[col] == 'Yes']) for _, col in disability_types.items()]
                    heatmap_data.append(row)
                
                fig = go.Figure(data=go.Heatmap(
                    z=heatmap_data,
                    x=list(disability_types.keys()),
                    y=sorted(partnerships),
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
            
            st.markdown("---")
            st.markdown("### Schools by Partnership")
            
            if st.session_state.partnership_filter:
                part_schools = filtered[filtered['Partnership_Area'] == st.session_state.partnership_filter]['Referring_School'].value_counts()
                fig = go.Figure([go.Bar(y=part_schools.index, x=part_schools.values, orientation='h', marker_color='#ffd93d')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title=f"Schools in {st.session_state.partnership_filter}", height=400, showlegend=False, xaxis_title="Referrals")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Select a Partnership in filters to see schools in that partnership")
        
        elif st.session_state.view == "Extensions":
            st.markdown("### Placement Extensions Analysis")
            
            # Check if Extended_Placement column exists
            if 'Extended_Placement' in filtered.columns:
                extended = filtered['Extended_Placement'].value_counts()
                fig = go.Figure([go.Pie(labels=['Standard', 'Extended'], values=[len(filtered[filtered['Extended_Placement'] != 'Yes']), len(filtered[filtered['Extended_Placement'] == 'Yes'])], marker=dict(colors=['#10b981', '#ffd93d']))])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Standard vs Extended Placements", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.markdown(f"**Standard Placements:** {len(filtered[filtered['Extended_Placement'] != 'Yes'])}")
                st.markdown(f"**Extended Placements:** {len(filtered[filtered['Extended_Placement'] == 'Yes'])}")
            else:
                st.warning("Extended_Placement data not available")
        
        elif st.session_state.view == "Partnerships":
            st.markdown("### Partnership Comparison")
            
            partnership_stats = []
            for partner in sorted(filtered['Partnership_Area'].unique()):
                p_data = filtered[filtered['Partnership_Area'] == partner]
                partnership_stats.append({
                    'Partnership': partner,
                    'Total': len(p_data),
                    'ATSI': len(p_data[p_data['Flag_ATSI'] == 'Yes']),
                    'SWD': len(p_data[p_data['Flag_SWD'] == 'Yes']),
                    'EALD': len(p_data[p_data['Flag_EALD'] == 'Yes']),
                    'Allocated': len(p_data[p_data['Allocation_Status'] == 'Allocated'])
                })
            
            partnership_df = pd.DataFrame(partnership_stats)
            st.dataframe(partnership_df, use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            with c1:
                fig = go.Figure([go.Bar(x=partnership_df['Partnership'], y=partnership_df['Total'], marker_color='#00e5ff')])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Students by Partnership", height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=partnership_df['Partnership'], y=partnership_df['ATSI'], name='ATSI', marker_color='#ff6b6b'))
                fig.add_trace(go.Bar(x=partnership_df['Partnership'], y=partnership_df['SWD'], name='SWD', marker_color='#ffd93d'))
                fig.add_trace(go.Bar(x=partnership_df['Partnership'], y=partnership_df['EALD'], name='EALD', marker_color='#00e5ff'))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Demographics by Partnership", height=350, barmode='group')
                st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.write(traceback.format_exc())

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff;'>CLC-LBU Allocation Dashboard</p>", unsafe_allow_html=True)
