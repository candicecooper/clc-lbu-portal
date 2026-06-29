"""
CLC-LBU ASSESSMENT ANALYTICS
View and analyze all term assessment data
Page name: Assessment_Analytics.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

st.set_page_config(
    page_title="📊 Assessment Analytics",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# THEME
# ============================================================================

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    h1 {
        color: #00e5ff !important;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.5) !important;
    }
    
    h2, h3 {
        color: #ffd93d !important;
    }
    
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3) 0%, rgba(0, 229, 255, 0.08) 100%) !important;
        border-left: 5px solid rgba(0, 229, 255, 0.9) !important;
    }
</style>
""", unsafe_allow_html=True)

COLORS = {
    'cyan': '#00e5ff',
    'green': '#00ff00',
    'red': '#ff6b6b',
    'yellow': '#ffd93d',
    'dark_bg': '#0a0e27',
    'amber': '#C8760A'
}

# ============================================================================
# SUPABASE
# ============================================================================

@st.cache_resource
def init_supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    
    if url and key:
        try:
            return create_client(url, key)
        except:
            return None
    return None

supabase: Client = init_supabase()

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_all_assessments():
    """Get all assessment records"""
    if not supabase:
        return []
    
    try:
        response = supabase.table('term_assessments').select('*').execute()
        return response.data if response.data else []
    except:
        return []

def parse_assessment_data(assessments):
    """Convert assessment records to usable dataframe"""
    records = []
    
    for record in assessments:
        try:
            sw = json.loads(record.get('sounds_write_data', '{}'))
            wa = json.loads(record.get('word_aware_data', '{}'))
            smartar = json.loads(record.get('smartar_goals', '{}'))
            
            sw_mastered = sum([d.get('Mastered', 0) for d in sw.values()])
            wa_mastered = sum([d.get('Mastered', 0) for d in wa.values()])
            
            records.append({
                'Staff': record['staff_member'],
                'Program': record['program'],
                'Term': record['term'],
                'Year': record['year'],
                'Date': record.get('date_submitted', ''),
                'SW_Mastered': sw_mastered,
                'WA_Mastered': wa_mastered,
                'SW_Data': sw,
                'WA_Data': wa,
                'SMARTAR_Data': smartar
            })
        except:
            continue
    
    return pd.DataFrame(records) if records else pd.DataFrame()

# ============================================================================
# MAIN
# ============================================================================

def main():
    st.markdown("# 📊 ASSESSMENT ANALYTICS DASHBOARD")
    st.markdown("_Analyze term assessment data across programs and staff_")
    
    if not supabase:
        st.warning("⚠️ Supabase not connected")
        return
    
    assessments = get_all_assessments()
    
    if not assessments:
        st.info("No assessment data found. Staff need to submit term assessments first.")
        return
    
    df = parse_assessment_data(assessments)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_year = st.multiselect("Year", sorted(df['Year'].unique()), default=sorted(df['Year'].unique()))
    with col2:
        selected_term = st.multiselect("Term", sorted(df['Term'].unique()), default=sorted(df['Term'].unique()))
    with col3:
        selected_program = st.multiselect("Program", sorted(df['Program'].unique()), default=sorted(df['Program'].unique()))
    with col4:
        selected_staff = st.multiselect("Staff", sorted(df['Staff'].unique()), default=sorted(df['Staff'].unique()))
    
    filtered_df = df[
        (df['Year'].isin(selected_year)) &
        (df['Term'].isin(selected_term)) &
        (df['Program'].isin(selected_program)) &
        (df['Staff'].isin(selected_staff))
    ]
    
    st.markdown("---")
    st.markdown("## 📈 Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📝 Assessments Submitted", len(filtered_df))
    col2.metric("👥 Staff Members", filtered_df['Staff'].nunique())
    col3.metric("🎓 Programs", filtered_df['Program'].nunique())
    col4.metric("📅 Terms Covered", filtered_df['Term'].nunique())
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎵 Sounds Write",
        "💬 Word Aware",
        "🎯 SMARTAR Goals",
        "👥 Staff Performance",
        "📋 Raw Data"
    ])
    
    with tab1:
        st.markdown("### 🎵 Sounds Write Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            program_sw = []
            for prog in selected_program:
                prog_data = filtered_df[filtered_df['Program'] == prog]
                mastered = prog_data['SW_Mastered'].sum()
                program_sw.append({'Program': prog, 'Mastered': mastered})
            
            if program_sw:
                prog_sw_df = pd.DataFrame(program_sw)
                
                fig = go.Figure(data=[
                    go.Bar(x=prog_sw_df['Program'], y=prog_sw_df['Mastered'],
                           marker_color=COLORS['green'])
                ])
                fig.update_layout(
                    title='Mastered Skills by Program',
                    paper_bgcolor=COLORS['dark_bg'],
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['white']),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            staff_sw = []
            for staff in selected_staff:
                staff_data = filtered_df[filtered_df['Staff'] == staff]
                mastered = staff_data['SW_Mastered'].sum()
                staff_sw.append({'Staff': staff, 'Mastered': mastered})
            
            if staff_sw:
                staff_sw_df = pd.DataFrame(staff_sw).sort_values('Mastered', ascending=True)
                
                fig = go.Figure(data=[
                    go.Bar(y=staff_sw_df['Staff'], x=staff_sw_df['Mastered'],
                           orientation='h', marker_color=COLORS['cyan'])
                ])
                fig.update_layout(
                    title='Sounds Write by Staff',
                    paper_bgcolor=COLORS['dark_bg'],
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['white']),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown("### 💬 Word Aware Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            program_wa = []
            for prog in selected_program:
                prog_data = filtered_df[filtered_df['Program'] == prog]
                mastered = prog_data['WA_Mastered'].sum()
                program_wa.append({'Program': prog, 'Mastered': mastered})
            
            if program_wa:
                prog_wa_df = pd.DataFrame(program_wa)
                
                fig = go.Figure(data=[
                    go.Bar(x=prog_wa_df['Program'], y=prog_wa_df['Mastered'],
                           marker_color=COLORS['yellow'])
                ])
                fig.update_layout(
                    title='Mastered Skills by Program',
                    paper_bgcolor=COLORS['dark_bg'],
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['white']),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            staff_wa = []
            for staff in selected_staff:
                staff_data = filtered_df[filtered_df['Staff'] == staff]
                mastered = staff_data['WA_Mastered'].sum()
                staff_wa.append({'Staff': staff, 'Mastered': mastered})
            
            if staff_wa:
                staff_wa_df = pd.DataFrame(staff_wa).sort_values('Mastered', ascending=True)
                
                fig = go.Figure(data=[
                    go.Bar(y=staff_wa_df['Staff'], x=staff_wa_df['Mastered'],
                           orientation='h', marker_color=COLORS['amber'])
                ])
                fig.update_layout(
                    title='Word Aware by Staff',
                    paper_bgcolor=COLORS['dark_bg'],
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['white']),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### 🎯 SMARTAR Goals Progress")
        
        goal_achievements = {'Achieved': 0, 'In Progress': 0, 'Exceeded': 0, 'Not Started': 0}
        
        for _, row in filtered_df.iterrows():
            try:
                smartar = row['SMARTAR_Data']
                if isinstance(smartar, dict):
                    for goal, data in smartar.items():
                        achievement = data.get('achievement', 'Not Started')
                        if achievement in goal_achievements:
                            goal_achievements[achievement] += 1
            except:
                pass
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(goal_achievements.keys()),
                values=list(goal_achievements.values()),
                marker=dict(colors=[COLORS['green'], COLORS['yellow'], COLORS['cyan'], COLORS['red']])
            )
        ])
        
        fig.update_layout(
            title='SMARTAR Goal Achievement Status',
            paper_bgcolor=COLORS['dark_bg'],
            font=dict(color=COLORS['white']),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("✅ Achieved", goal_achievements['Achieved'])
        col2.metric("⏳ In Progress", goal_achievements['In Progress'])
        col3.metric("🚀 Exceeded", goal_achievements['Exceeded'])
        col4.metric("⭕ Not Started", goal_achievements['Not Started'])
    
    with tab4:
        st.markdown("### 👥 Staff Performance Summary")
        
        staff_summary = []
        for staff in selected_staff:
            staff_data = filtered_df[filtered_df['Staff'] == staff]
            
            staff_summary.append({
                'Staff': staff,
                'Assessments': len(staff_data),
                'Avg_SW_Mastered': staff_data['SW_Mastered'].mean(),
                'Avg_WA_Mastered': staff_data['WA_Mastered'].mean(),
                'Programs': staff_data['Program'].nunique()
            })
        
        staff_summary_df = pd.DataFrame(staff_summary)
        st.dataframe(staff_summary_df, use_container_width=True)
    
    with tab5:
        st.markdown("### 📋 Assessment Records")
        
        display_df = filtered_df[['Staff', 'Program', 'Term', 'Year', 'Date', 'SW_Mastered', 'WA_Mastered']]
        st.dataframe(display_df, use_container_width=True)
        
        csv = display_df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            f"assessments_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

if __name__ == "__main__":
    main()
