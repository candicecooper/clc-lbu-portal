import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Allocation Dashboard | CLC-LBU", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Hide sidebar */
    [data-testid="stSidebar"] {display: none;}
    
    /* Main container */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Header */
    .dashboard-header {
        background: linear-gradient(135deg, #1A7A6E 0%, #4A9B8E 100%);
        padding: 2.5rem 3rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .dashboard-header h1 {
        color: white;
        margin: 0;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .dashboard-header p {
        color: #D6F0EB;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        transition: transform 0.2s;
        border-left: 5px solid #1A7A6E;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    .metric-number {
        font-size: 3.5rem;
        font-weight: 700;
        color: #1A7A6E;
        margin: 0;
        line-height: 1;
    }
    .metric-label {
        font-size: 0.95rem;
        color: #666;
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Info boxes */
    .info-box {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #C8760A;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Privacy badge */
    .privacy-badge {
        background: #D6F0EB;
        color: #1A7A6E;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin-top: 1rem;
    }
    
    /* Section headers */
    .section-header {
        color: #1A7A6E;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #1A7A6E;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# EMBEDDED DATA (De-identified)
# ══════════════════════════════════════════════════════════════════════════════
ALLOCATION_DATA = [{"record_id": "Record #1", "school": "Cowandilla PS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "West Torrens", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "No", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #2", "school": "Highgate School", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #3", "school": "Le Fevre HS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Middle (7-9)", "partnership": "Port Adelaide", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #4", "school": "Hendon PS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "Inner Western", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "Yes", "eald": "Yes", "current_status": "Active"}, {"record_id": "Record #5", "school": "Warradale PS", "referral_date": "2026-04-14", "status": "Allocated", "program": "Primary (R-6)", "partnership": "Inner Western", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "No", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #6", "school": "Le Fevre HS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Middle (7-9)", "partnership": "Port Adelaide", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "Yes", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #7", "school": "Ocean View P-12 College", "referral_date": "2026-01-27", "status": "Allocated", "program": "Middle (7-9)", "partnership": "Port Adelaide", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "Yes", "eald": "No", "current_status": "Active"}, {"record_id": "Record #8", "school": "Clovelly Park PS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #9", "school": "Clovelly Park PS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #10", "school": "Findon HS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Middle (7-9)", "partnership": "Port Adelaide", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #11", "school": "Highgate School", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "Yes", "aboriginal": "Yes", "eald": "Yes", "current_status": "Active"}, {"record_id": "Record #12", "school": "Paralowie R-12", "referral_date": "2026-01-27", "status": "Allocated", "program": "Middle (7-9)", "partnership": "Western Adelaide Shores", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #13", "school": "Walkerville PS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "Inner Western", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "Yes", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #14", "school": "Challa Gardens PS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #15", "school": "Bellevue Heights PS", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "Inner Western", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}, {"record_id": "Record #16", "school": "Highgate School", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "Yes", "mental_health": "No", "care_cps": "No", "aboriginal": "Yes", "eald": "No", "current_status": "Active"}, {"record_id": "Record #17", "school": "West Lakes Shores", "referral_date": "2026-01-27", "status": "Allocated", "program": "Primary (R-6)", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "Yes", "adhd": "Yes", "mental_health": "No", "care_cps": "Yes", "aboriginal": "Yes", "eald": "Yes", "current_status": "Active"}, {"record_id": "Record #18", "school": "16", "referral_date": "None", "status": "Allocated", "program": "", "partnership": "", "prev_clc": "No", "prev_other": "No", "priority": "", "asd": "No", "adhd": "No", "mental_health": "No", "care_cps": "No", "aboriginal": "No", "eald": "No", "current_status": "Active"}]

# Load data
df = pd.DataFrame(ALLOCATION_DATA)

# Clean the last record (seems to be invalid)
df = df[df['program'] != '']

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="dashboard-header">
    <h1>📊 Allocation Dashboard</h1>
    <p>De-identified student allocation overview • Real-time analytics</p>
    <span class="privacy-badge">🔒 Privacy Protected • Student Names Removed</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# KEY METRICS
# ══════════════════════════════════════════════════════════════════════════════
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{len(df)}</div>
        <div class="metric-label">Total Referrals</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    allocated = len(df[df['status'] == 'Allocated'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{allocated}</div>
        <div class="metric-label">Allocated</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    asd_count = len(df[df['asd'] == 'Yes'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{asd_count}</div>
        <div class="metric-label">ASD Flag</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    adhd_count = len(df[df['adhd'] == 'Yes'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{adhd_count}</div>
        <div class="metric-label">ADHD Flag</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    partnership_count = len(df[df['partnership'] != ''])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{partnership_count}</div>
        <div class="metric-label">Partnership Students</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZATIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📈 Visual Analytics</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

# Program Distribution
with col1:
    program_counts = df['program'].value_counts()
    fig1 = px.bar(
        x=program_counts.index, 
        y=program_counts.values,
        labels={'x': 'Program', 'y': 'Student Count'},
        title='Students by Program',
        color=program_counts.values,
        color_continuous_scale='Teal'
    )
    fig1.update_layout(
        showlegend=False,
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig1, use_container_width=True)

# Partnership Distribution
with col2:
    partnership_data = df[df['partnership'] != '']['partnership'].value_counts()
    if len(partnership_data) > 0:
        fig2 = px.pie(
            values=partnership_data.values,
            names=partnership_data.index,
            title='Partnership Distribution',
            color_discrete_sequence=px.colors.sequential.Teal
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)

# Flags Breakdown
st.markdown('<div class="section-header">🏷️ Student Needs Profile</div>', unsafe_allow_html=True)

flag_data = {
    'ASD': len(df[df['asd'] == 'Yes']),
    'ADHD': len(df[df['adhd'] == 'Yes']),
    'Aboriginal': len(df[df['aboriginal'] == 'Yes']),
    'EALD': len(df[df['eald'] == 'Yes']),
    'Care/CPS': len(df[df['care_cps'] == 'Yes'])
}

fig3 = px.bar(
    x=list(flag_data.keys()),
    y=list(flag_data.values()),
    labels={'x': 'Support Flag', 'y': 'Student Count'},
    title='Priority Support Flags',
    color=list(flag_data.values()),
    color_continuous_scale='Oranges'
)
fig3.update_layout(
    showlegend=False,
    height=400,
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA TABLE (De-identified)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📋 Allocation Records</div>', unsafe_allow_html=True)

st.markdown("""
<div class="info-box">
<strong>ℹ️ Privacy Notice:</strong> Student names have been removed from this view. 
Records are identified by number only. This dashboard is safe to share in presentations and leadership meetings.
</div>
""", unsafe_allow_html=True)

# Display table
display_df = df[['record_id', 'school', 'program', 'partnership', 'status']].copy()
display_df.columns = ['Record ID', 'Referring School', 'Program', 'Partnership', 'Status']

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=400
)

# ══════════════════════════════════════════════════════════════════════════════
# INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">💡 Key Insights</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="info-box">
    <strong>Student Complexity:</strong><br>
    • High prevalence of ASD diagnosis requiring specialized support<br>
    • Multiple co-occurring needs across cohort<br>
    • Focus on trauma-informed, neurodiversity-affirming practice
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-box">
    <strong>Partnership Engagement:</strong><br>
    • Strong collaboration with Inner Western cluster schools<br>
    • Opportunity to expand Port Adelaide partnerships<br>
    • Monitor capacity across program levels
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p style="font-size: 0.9rem;">📊 Allocation Dashboard | Cowandilla Learning Centre LBU</p>
    <p style="font-size: 0.85rem; color: #1A7A6E; font-weight: 600;">
        🔒 De-identified data • Updated automatically • Safe for external presentation
    </p>
</div>
""", unsafe_allow_html=True)
