import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="CLC Allocation Dashboard", page_icon="📊", layout="wide")

if 'term_filter' not in st.session_state:
    st.session_state.term_filter = 4.0
if 'view' not in st.session_state:
    st.session_state.view = "Current Allocations"

# Load Excel file
default_file = '/mnt/user-data/uploads/CLC_Allocation_Dashboard_2026_WithNames_1.xlsx'
if os.path.exists(default_file):
    all_data = pd.read_excel(default_file)
else:
    all_data = pd.DataFrame()

# Clean data - convert Yes/No flags to proper format
if len(all_data) > 0:
    all_data['ATSI'] = all_data['Flag_ATSI'].fillna('No').astype(str).map({'Yes': 'Yes', 'No': 'No', '1': 'Yes', '0': 'No'})
    all_data['SWD'] = all_data['Flag_SWD'].fillna('No').astype(str).map({'Yes': 'Yes', 'No': 'No', '1': 'Yes', '0': 'No'})
    all_data['EALD'] = all_data['Flag_EALD'].fillna('No').astype(str).map({'Yes': 'Yes', 'No': 'No', '1': 'Yes', '0': 'No'})
    all_data['Allocated'] = all_data['Allocation_Status'].notna() & (all_data['Allocation_Status'] != '')
    all_data['Term'] = all_data['Term'].fillna(4)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
* { font-family: 'Poppins', sans-serif !important; }
body, [data-testid="stAppViewContainer"] { background-color: #0a0e27 !important; }
.main { background-color: #0a0e27 !important; padding: 1rem !important; }
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
[data-testid="stSidebar"] { background-color: #0a0e27 !important; }
[data-testid="stSidebar"] * { color: #00e5ff !important; }
[data-testid="metric-value"] { color: #00ff00 !important; font-size: 2rem !important; }
[data-testid="metric-label"] { color: #00e5ff !important; font-size: 0.9rem !important; }
.stButton > button { background-color: #1a1f3a !important; color: #00e5ff !important; border: 2px solid #00e5ff !important; padding: 0.3rem 0.6rem !important; font-size: 0.75rem !important; }
.stButton > button:hover { background-color: #00e5ff !important; color: #0a0e27 !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 📊 VIEW")
    st.session_state.view = st.radio("", ["Current Allocations", "ATSI Analysis", "SWD Analysis", "EALD Analysis", "Comparative", "By Term/Year"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎯 FILTER")
    
    st.markdown("**Term**")
    terms = sorted(all_data['Term'].dropna().unique())
    tc1, tc2 = st.columns(2)
    if tc1.button("Current (4)", use_container_width=True, key="term_cur"): st.session_state.term_filter = 4.0
    if tc2.button("All Terms", use_container_width=True, key="term_all"): st.session_state.term_filter = None
    for term in sorted(terms):
        if st.button(f"Term {int(term)}", use_container_width=True, key=f"term_{int(term)}"): st.session_state.term_filter = term

# Filter to selected term
if st.session_state.term_filter is not None:
    filtered = all_data[all_data['Term'] == st.session_state.term_filter].copy()
    term_label = f"Term {int(st.session_state.term_filter)}"
else:
    filtered = all_data.copy()
    term_label = "All Terms"

st.markdown(f"## CLC Allocation Analysis - {term_label}")
st.markdown(f"**Total Referrals: {len(filtered)}** | **Allocated: {filtered['Allocated'].sum()}** ({filtered['Allocated'].sum()/len(filtered)*100:.1f}%)")
st.markdown("---")

# CURRENT ALLOCATIONS VIEW
if st.session_state.view == "Current Allocations":
    st.markdown("### Current Allocation Status")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    total = len(filtered)
    allocated = filtered['Allocated'].sum()
    atsi_count = (filtered['ATSI'] == 'Yes').sum()
    swd_count = (filtered['SWD'] == 'Yes').sum()
    eald_count = (filtered['EALD'] == 'Yes').sum()
    
    c1.metric("Total", total)
    c2.metric("Allocated", f"{allocated}\n({allocated/total*100:.0f}%)")
    c3.metric("ATSI", f"{atsi_count}\n({atsi_count/total*100:.0f}%)")
    c4.metric("SWD", f"{swd_count}\n({swd_count/total*100:.0f}%)")
    c5.metric("EALD", f"{eald_count}\n({eald_count/total*100:.0f}%)")
    
    st.markdown("---")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        status = filtered['Allocation_Status'].value_counts()
        fig = go.Figure([go.Bar(x=status.index, y=status.values, marker_color=['#00ff00', '#ffd93d'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Status", height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        atsi_data = pd.DataFrame({
            'Group': ['ATSI', 'Non-ATSI'],
            'Allocated': [
                filtered[filtered['ATSI']=='Yes']['Allocated'].sum(),
                filtered[filtered['ATSI']=='No']['Allocated'].sum()
            ],
            'Total': [
                (filtered['ATSI']=='Yes').sum(),
                (filtered['ATSI']=='No').sum()
            ]
        })
        atsi_data['Rate'] = atsi_data['Allocated'] / atsi_data['Total'] * 100
        fig = go.Figure([go.Bar(x=atsi_data['Group'], y=atsi_data['Rate'], marker_color=['#ff6b6b', '#10b981'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Rate (%)", height=300, showlegend=False, yaxis_title='% Allocated')
        st.plotly_chart(fig, use_container_width=True)
    
    with c3:
        swd_data = pd.DataFrame({
            'Group': ['SWD', 'Non-SWD'],
            'Allocated': [
                filtered[filtered['SWD']=='Yes']['Allocated'].sum(),
                filtered[filtered['SWD']=='No']['Allocated'].sum()
            ],
            'Total': [
                (filtered['SWD']=='Yes').sum(),
                (filtered['SWD']=='No').sum()
            ]
        })
        swd_data['Rate'] = swd_data['Allocated'] / swd_data['Total'] * 100
        fig = go.Figure([go.Bar(x=swd_data['Group'], y=swd_data['Rate'], marker_color=['#ff6b6b', '#10b981'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="SWD Allocation Rate (%)", height=300, showlegend=False, yaxis_title='% Allocated')
        st.plotly_chart(fig, use_container_width=True)

# ATSI ANALYSIS VIEW
elif st.session_state.view == "ATSI Analysis":
    st.markdown("### ATSI Student Analysis")
    
    atsi_total = (filtered['ATSI'] == 'Yes').sum()
    atsi_allocated = filtered[filtered['ATSI']=='Yes']['Allocated'].sum()
    non_atsi_total = (filtered['ATSI'] == 'No').sum()
    non_atsi_allocated = filtered[filtered['ATSI']=='No']['Allocated'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ATSI Students", atsi_total)
    c2.metric("ATSI Allocated", f"{atsi_allocated}\n({atsi_allocated/atsi_total*100:.0f}%)" if atsi_total > 0 else 0)
    c3.metric("Non-ATSI Students", non_atsi_total)
    c4.metric("Non-ATSI Allocated", f"{non_atsi_allocated}\n({non_atsi_allocated/non_atsi_total*100:.0f}%)" if non_atsi_total > 0 else 0)
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        comparison = pd.DataFrame({
            'Group': ['ATSI', 'Non-ATSI'],
            'Allocated': [atsi_allocated, non_atsi_allocated],
            'Not Allocated': [atsi_total - atsi_allocated, non_atsi_total - non_atsi_allocated]
        })
        fig = go.Figure(data=[
            go.Bar(x=comparison['Group'], y=comparison['Allocated'], name='Allocated', marker_color='#00ff00'),
            go.Bar(x=comparison['Group'], y=comparison['Not Allocated'], name='Not Allocated', marker_color='#ff6b6b')
        ])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Comparison", barmode='stack', height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown("#### 📊 Key Findings")
        st.markdown(f"""
- **ATSI Representation:** {atsi_total/len(filtered)*100:.1f}% of referrals
- **ATSI Allocation Rate:** {atsi_allocated/atsi_total*100:.1f}%
- **Non-ATSI Allocation Rate:** {non_atsi_allocated/non_atsi_total*100:.1f}%
- **Difference:** {abs(atsi_allocated/atsi_total*100 - non_atsi_allocated/non_atsi_total*100):.1f} percentage points
        """)

# SWD ANALYSIS VIEW
elif st.session_state.view == "SWD Analysis":
    st.markdown("### Student with Disabilities (SWD) Analysis")
    
    swd_total = (filtered['SWD'] == 'Yes').sum()
    swd_allocated = filtered[filtered['SWD']=='Yes']['Allocated'].sum()
    non_swd_total = (filtered['SWD'] == 'No').sum()
    non_swd_allocated = filtered[filtered['SWD']=='No']['Allocated'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SWD Students", swd_total)
    c2.metric("SWD Allocated", f"{swd_allocated}\n({swd_allocated/swd_total*100:.0f}%)" if swd_total > 0 else 0)
    c3.metric("Non-SWD Students", non_swd_total)
    c4.metric("Non-SWD Allocated", f"{non_swd_allocated}\n({non_swd_allocated/non_swd_total*100:.0f}%)" if non_swd_total > 0 else 0)
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        comparison = pd.DataFrame({
            'Group': ['SWD', 'Non-SWD'],
            'Allocated': [swd_allocated, non_swd_allocated],
            'Not Allocated': [swd_total - swd_allocated, non_swd_total - non_swd_allocated]
        })
        fig = go.Figure(data=[
            go.Bar(x=comparison['Group'], y=comparison['Allocated'], name='Allocated', marker_color='#00ff00'),
            go.Bar(x=comparison['Group'], y=comparison['Not Allocated'], name='Not Allocated', marker_color='#ff6b6b')
        ])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Comparison", barmode='stack', height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown("#### 📊 Key Findings")
        st.markdown(f"""
- **SWD Representation:** {swd_total/len(filtered)*100:.1f}% of referrals
- **SWD Allocation Rate:** {swd_allocated/swd_total*100:.1f}%
- **Non-SWD Allocation Rate:** {non_swd_allocated/non_swd_total*100:.1f}%
- **Difference:** {abs(swd_allocated/swd_total*100 - non_swd_allocated/non_swd_total*100):.1f} percentage points
        """)

# EALD ANALYSIS VIEW
elif st.session_state.view == "EALD Analysis":
    st.markdown("### EALD Student Analysis")
    
    eald_total = (filtered['EALD'] == 'Yes').sum()
    eald_allocated = filtered[filtered['EALD']=='Yes']['Allocated'].sum()
    non_eald_total = (filtered['EALD'] == 'No').sum()
    non_eald_allocated = filtered[filtered['EALD']=='No']['Allocated'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EALD Students", eald_total)
    c2.metric("EALD Allocated", f"{eald_allocated}\n({eald_allocated/eald_total*100:.0f}%)" if eald_total > 0 else 0)
    c3.metric("Non-EALD Students", non_eald_total)
    c4.metric("Non-EALD Allocated", f"{non_eald_allocated}\n({non_eald_allocated/non_eald_total*100:.0f}%)" if non_eald_total > 0 else 0)
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        comparison = pd.DataFrame({
            'Group': ['EALD', 'Non-EALD'],
            'Allocated': [eald_allocated, non_eald_allocated],
            'Not Allocated': [eald_total - eald_allocated, non_eald_total - non_eald_allocated]
        })
        fig = go.Figure(data=[
            go.Bar(x=comparison['Group'], y=comparison['Allocated'], name='Allocated', marker_color='#00ff00'),
            go.Bar(x=comparison['Group'], y=comparison['Not Allocated'], name='Not Allocated', marker_color='#ff6b6b')
        ])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Comparison", barmode='stack', height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown("#### 📊 Key Findings")
        st.markdown(f"""
- **EALD Representation:** {eald_total/len(filtered)*100:.1f}% of referrals
- **EALD Allocation Rate:** {eald_allocated/eald_total*100:.1f}%
- **Non-EALD Allocation Rate:** {non_eald_allocated/non_eald_total*100:.1f}%
- **Growth Indicator:** {'Rising' if eald_total > 5 else 'Emerging'} need
        """)

# COMPARATIVE VIEW
elif st.session_state.view == "Comparative":
    st.markdown("### Comparative Analysis - All Demographics")
    
    c1, c2 = st.columns(2)
    
    with c1:
        comp_data = pd.DataFrame({
            'Group': ['ATSI', 'SWD', 'EALD'],
            'Count': [
                (filtered['ATSI']=='Yes').sum(),
                (filtered['SWD']=='Yes').sum(),
                (filtered['EALD']=='Yes').sum()
            ],
            'Percentage': [
                (filtered['ATSI']=='Yes').sum()/len(filtered)*100,
                (filtered['SWD']=='Yes').sum()/len(filtered)*100,
                (filtered['EALD']=='Yes').sum()/len(filtered)*100
            ]
        })
        fig = go.Figure([go.Bar(x=comp_data['Group'], y=comp_data['Percentage'], marker_color=['#ff6b6b', '#ff6b6b', '#ffd93d'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Demographic Representation (%)", height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        alloc_rates = pd.DataFrame({
            'Group': ['ATSI', 'Non-ATSI', 'SWD', 'Non-SWD', 'EALD', 'Non-EALD'],
            'Rate': [
                filtered[filtered['ATSI']=='Yes']['Allocated'].sum() / (filtered['ATSI']=='Yes').sum() * 100 if (filtered['ATSI']=='Yes').sum() > 0 else 0,
                filtered[filtered['ATSI']=='No']['Allocated'].sum() / (filtered['ATSI']=='No').sum() * 100 if (filtered['ATSI']=='No').sum() > 0 else 0,
                filtered[filtered['SWD']=='Yes']['Allocated'].sum() / (filtered['SWD']=='Yes').sum() * 100 if (filtered['SWD']=='Yes').sum() > 0 else 0,
                filtered[filtered['SWD']=='No']['Allocated'].sum() / (filtered['SWD']=='No').sum() * 100 if (filtered['SWD']=='No').sum() > 0 else 0,
                filtered[filtered['EALD']=='Yes']['Allocated'].sum() / (filtered['EALD']=='Yes').sum() * 100 if (filtered['EALD']=='Yes').sum() > 0 else 0,
                filtered[filtered['EALD']=='No']['Allocated'].sum() / (filtered['EALD']=='No').sum() * 100 if (filtered['EALD']=='No').sum() > 0 else 0,
            ]
        })
        fig = go.Figure([go.Bar(x=alloc_rates['Group'], y=alloc_rates['Rate'], marker_color=['#ff6b6b', '#10b981', '#ff6b6b', '#10b981', '#ffd93d', '#10b981'])])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Allocation Rates (%)", height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# BY TERM/YEAR VIEW
elif st.session_state.view == "By Term/Year":
    st.markdown("### Trends Over Terms & Years")
    
    by_term = all_data.groupby('Term').agg({
        'ATSI': lambda x: (x == 'Yes').sum(),
        'SWD': lambda x: (x == 'Yes').sum(),
        'EALD': lambda x: (x == 'Yes').sum(),
        'Allocated': 'sum'
    }).reset_index()
    by_term['Total'] = all_data.groupby('Term').size().values
    by_term['ATSI_Rate'] = by_term['ATSI'] / by_term['Total'] * 100
    by_term['SWD_Rate'] = by_term['SWD'] / by_term['Total'] * 100
    by_term['EALD_Rate'] = by_term['EALD'] / by_term['Total'] * 100
    
    c1, c2 = st.columns(2)
    
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=by_term['Term'], y=by_term['ATSI_Rate'], mode='lines+markers', name='ATSI', line=dict(color='#ff6b6b', width=3)))
        fig.add_trace(go.Scatter(x=by_term['Term'], y=by_term['SWD_Rate'], mode='lines+markers', name='SWD', line=dict(color='#ff6b6b', width=3)))
        fig.add_trace(go.Scatter(x=by_term['Term'], y=by_term['EALD_Rate'], mode='lines+markers', name='EALD', line=dict(color='#ffd93d', width=3)))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Demographic % by Term", height=350, xaxis_title='Term', yaxis_title='%')
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        fig = go.Figure([go.Bar(x=by_term['Term'], y=by_term['Total'], marker_color='#00e5ff')])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), title="Total Referrals by Term", height=350, xaxis_title='Term', yaxis_title='Count', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00e5ff; font-size: 0.85rem;'>CLC-LBU Allocation Dashboard • Demographics & Equity Analysis</p>", unsafe_allow_html=True)
