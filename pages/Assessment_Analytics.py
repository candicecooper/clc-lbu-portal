"""
CLC-LBU ASSESSMENT ANALYTICS (with Program Collation)
View aggregated assessment data by program
UPDATED: Single Program View + Term Overview
Page name: Assessment_Analytics.py
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
import plotly.express as px
import plotly.graph_objects as go

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
        border-bottom: 2px solid rgba(26, 122, 122, 0.3) !important;
        padding-bottom: 15px !important;
    }
    
    h2, h3 {
        color: #ffd93d !important;
    }
    
    p, span, label {
        color: #e8e8e8 !important;
    }
    
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.3) 0%, rgba(0, 229, 255, 0.08) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.4) !important;
        border-left: 5px solid rgba(0, 229, 255, 0.9) !important;
        border-radius: 12px !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.25) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 5px solid #00e5ff !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SUPABASE CONNECTION
# ============================================================================

@st.cache_resource
def init_supabase():
    """Initialize Supabase connection"""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    
    if url and key:
        try:
            return create_client(url, key)
        except Exception as e:
            st.error(f"Supabase connection error: {e}")
            return None
    return None

supabase: Client = init_supabase()

# ============================================================================
# DATA STRUCTURE
# ============================================================================

SOUNDS_WRITE_SKILLS = [
    'Blending',
    'Segmenting',
    'Phoneme manipulation',
    'Alphabet Code Knowledge test',
    'Non-word Reading test'
]

WORD_AWARE_SKILLS = [
    'Syllable Segmentation',
    'Word Finding',
    'Rhyme Production',
    'Initial Sound Identification',
    'Sound Sequencing'
]

SMARTAR_CAPABILITIES = ['Personal and Social', 'Learning and Engagement']
SMARTAR_LEVELS = ['Reached Expected', 'Above Expectation', 'Exceeding']

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_all_assessments():
    """Get all assessment records from Supabase"""
    if not supabase:
        return None
    
    try:
        response = supabase.table('term_assessments').select('*').execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching assessments: {e}")
        return None

def collate_by_program(assessments, program, term, year):
    """
    Collate assessment data from all staff for a specific program/term/year
    Returns aggregated data (sums across all staff)
    """
    if not assessments:
        return None
    
    # Filter by program, term, year
    filtered = [
        a for a in assessments 
        if a['program'] == program and 
           a['term'] == int(term) and 
           a['year'] == int(year)
    ]
    
    if not filtered:
        return None
    
    # Collate Sounds Write data
    sounds_write_collated = {}
    for skill in SOUNDS_WRITE_SKILLS:
        sounds_write_collated[skill] = {
            'Mastered': 0,
            'Developing': 0,
            'Requires Development': 0
        }
    
    # Collate Word Aware data
    word_aware_collated = {}
    for skill in WORD_AWARE_SKILLS:
        word_aware_collated[skill] = {
            'Mastered': 0,
            'Developing': 0,
            'Requires Development': 0
        }
    
    # SMARTAR collated - tallies per capability area
    smartar_collated = {}
    for cap in SMARTAR_CAPABILITIES:
        smartar_collated[cap] = {
            'Reached Expected': 0,
            'Above Expectation': 0,
            'Exceeding': 0
        }
    
    staff_count = 0
    
    # Sum across all staff
    for assessment in filtered:
        staff_count += 1
        
        # Sum Sounds Write
        try:
            sw_data = json.loads(assessment.get('sounds_write_data', '{}'))
            for skill, levels in sw_data.items():
                if skill in sounds_write_collated:
                    for level, count in levels.items():
                        sounds_write_collated[skill][level] += int(count)
        except:
            pass
        
        # Sum Word Aware
        try:
            wa_data = json.loads(assessment.get('word_aware_data', '{}'))
            for skill, levels in wa_data.items():
                if skill in word_aware_collated:
                    for level, count in levels.items():
                        word_aware_collated[skill][level] += int(count)
        except:
            pass
        
        # Sum SMARTAR tallies (ignores any old-format goal records gracefully)
        try:
            smartar_data = json.loads(assessment.get('smartar_goals', '{}'))
            for cap, levels in smartar_data.items():
                if cap in smartar_collated and isinstance(levels, dict):
                    for level in SMARTAR_LEVELS:
                        smartar_collated[cap][level] += int(levels.get(level, 0))
        except:
            pass
    
    return {
        'sounds_write': sounds_write_collated,
        'word_aware': word_aware_collated,
        'smartar': smartar_collated,
        'staff_count': staff_count,
        'record_count': len(filtered)
    }

# ============================================================================
# RENDER FUNCTIONS
# ============================================================================

def render_sounds_write_chart(collated, program):
    """Render Sounds Write chart"""
    sw_data = collated['sounds_write']
    vis_data = []
    for skill, levels in sw_data.items():
        vis_data.append({
            'Skill': skill,
            'Mastered': levels['Mastered'],
            'Developing': levels['Developing'],
            'Requires Dev': levels['Requires Development']
        })
    
    df_sw = pd.DataFrame(vis_data)
    
    fig_sw = px.bar(
        df_sw,
        x='Skill',
        y=['Mastered', 'Developing', 'Requires Dev'],
        barmode='stack',
        title=f'🎵 Sounds Write - {program} Program',
        color_discrete_map={
            'Mastered': '#4CAF50',
            'Developing': '#FFC107',
            'Requires Dev': '#F44336'
        },
        labels={'value': 'Number of Students', 'variable': 'Performance Level'}
    )
    fig_sw.update_layout(
        plot_bgcolor='rgba(10, 14, 39, 0.8)',
        paper_bgcolor='rgba(10, 14, 39, 0.8)',
        font=dict(color='#e8e8e8'),
        hovermode='x unified',
        height=400
    )
    return fig_sw, df_sw

def render_word_aware_chart(collated, program):
    """Render Word Aware chart"""
    wa_data = collated['word_aware']
    vis_data = []
    for skill, levels in wa_data.items():
        vis_data.append({
            'Skill': skill,
            'Mastered': levels['Mastered'],
            'Developing': levels['Developing'],
            'Requires Dev': levels['Requires Development']
        })
    
    df_wa = pd.DataFrame(vis_data)
    
    fig_wa = px.bar(
        df_wa,
        x='Skill',
        y=['Mastered', 'Developing', 'Requires Dev'],
        barmode='stack',
        title=f'💬 Word Aware - {program} Program',
        color_discrete_map={
            'Mastered': '#4CAF50',
            'Developing': '#FFC107',
            'Requires Dev': '#F44336'
        },
        labels={'value': 'Number of Students', 'variable': 'Performance Level'}
    )
    fig_wa.update_layout(
        plot_bgcolor='rgba(10, 14, 39, 0.8)',
        paper_bgcolor='rgba(10, 14, 39, 0.8)',
        font=dict(color='#e8e8e8'),
        hovermode='x unified',
        height=400
    )
    return fig_wa, df_wa

def render_smartar_chart(collated, program):
    """Render SMARTAR outcomes chart - tallies by capability area"""
    smartar_data = collated['smartar']
    vis_data = []
    for cap, levels in smartar_data.items():
        vis_data.append({
            'Capability': cap,
            'Reached Expected': levels['Reached Expected'],
            'Above Expectation': levels['Above Expectation'],
            'Exceeding': levels['Exceeding']
        })

    df_smartar = pd.DataFrame(vis_data)

    fig_smartar = px.bar(
        df_smartar,
        x='Capability',
        y=['Reached Expected', 'Above Expectation', 'Exceeding'],
        barmode='group',
        title=f'🎯 SMARTAR Goal Outcomes - {program} Program',
        color_discrete_map={
            'Reached Expected': '#4CAF50',
            'Above Expectation': '#00BCD4',
            'Exceeding': '#FFD93D'
        },
        labels={'value': 'Number of Students', 'variable': 'Outcome Level'}
    )
    fig_smartar.update_layout(
        plot_bgcolor='rgba(10, 14, 39, 0.8)',
        paper_bgcolor='rgba(10, 14, 39, 0.8)',
        font=dict(color='#e8e8e8'),
        hovermode='x unified',
        height=400
    )
    return fig_smartar, df_smartar

# ============================================================================
# MAIN
# ============================================================================

def main():
    st.markdown("# 📊 ASSESSMENT ANALYTICS")
    
    if not supabase:
        st.warning("⚠️ Supabase not configured.")
        return
    
    # Get all assessments
    all_assessments = get_all_assessments()
    
    if not all_assessments:
        st.warning("No assessment data found yet.")
        return
    
    # Main view selector
    view_type = st.radio(
        "📋 View Type",
        ["📊 Single Program View", "🎓 Term Overview", "🔍 Detailed Analysis"],
        horizontal=True
    )
    
    st.markdown("---")
    
    # ========================================================================
    # SINGLE PROGRAM VIEW - All sections on one screen
    # ========================================================================
    
    if view_type == "📊 Single Program View":
        col1, col2, col3 = st.columns(3)
        
        with col1:
            program = st.selectbox("🎓 Program", ['JP', 'PY', 'SY'], key="spv_prog")
        with col2:
            term = st.selectbox("📅 Term", ['1', '2', '3', '4'], key="spv_term")
        with col3:
            year = st.selectbox("📆 Year", ['2025', '2026'], key="spv_year")
        
        st.markdown("---")
        
        collated = collate_by_program(all_assessments, program, term, year)
        
        if not collated:
            st.warning(f"No data found for {program} Term {term} {year}")
            return
        
        # Info row
        col1, col2, col3 = st.columns(3)
        col1.metric("📋 Staff Entries", collated['staff_count'])
        col2.metric("📊 Total Records", collated['record_count'])
        col3.metric("📅 Selected", f"{program} T{term} {year}")
        
        st.markdown("---")
        
        # All sections on one screen
        st.markdown(f"## {program} Program - Term {term} {year} - All Data")
        
        # Sounds Write
        fig_sw, df_sw = render_sounds_write_chart(collated, program)
        st.plotly_chart(fig_sw, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Sounds Write Mastered", df_sw['Mastered'].sum())
        col2.metric("🔄 Sounds Write Developing", df_sw['Developing'].sum())
        col3.metric("⚠️ Sounds Write Requires Dev", df_sw['Requires Dev'].sum())
        
        st.markdown("---")
        
        # Word Aware
        fig_wa, df_wa = render_word_aware_chart(collated, program)
        st.plotly_chart(fig_wa, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Word Aware Mastered", df_wa['Mastered'].sum())
        col2.metric("🔄 Word Aware Developing", df_wa['Developing'].sum())
        col3.metric("⚠️ Word Aware Requires Dev", df_wa['Requires Dev'].sum())
        
        st.markdown("---")
        
        # SMARTAR
        fig_smartar, df_smartar = render_smartar_chart(collated, program)
        st.plotly_chart(fig_smartar, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Reached Expected", int(df_smartar['Reached Expected'].sum()))
        col2.metric("⬆️ Above Expectation", int(df_smartar['Above Expectation'].sum()))
        col3.metric("🌟 Exceeding", int(df_smartar['Exceeding'].sum()))
    
    # ========================================================================
    # TERM OVERVIEW - All programs on one screen
    # ========================================================================
    
    elif view_type == "🎓 Term Overview":
        col1, col2 = st.columns(2)
        
        with col1:
            term = st.selectbox("📅 Term", ['1', '2', '3', '4'], key="to_term")
        with col2:
            year = st.selectbox("📆 Year", ['2025', '2026'], key="to_year")
        
        st.markdown("---")
        
        programs = ['JP', 'PY', 'SY']
        
        st.markdown(f"## Term {term} {year} - All Programs Overview")
        
        # ====== SOUNDS WRITE OVERVIEW ======
        st.markdown("### 🎵 Sounds Write - All Programs")
        
        sw_cols = st.columns(3)
        
        for idx, program in enumerate(programs):
            collated = collate_by_program(all_assessments, program, term, year)
            
            with sw_cols[idx]:
                if collated:
                    fig_sw, df_sw = render_sounds_write_chart(collated, program)
                    st.plotly_chart(fig_sw, use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric(f"{program} Mastered", df_sw['Mastered'].sum(), label_visibility="collapsed")
                    col2.metric(f"{program} Dev", df_sw['Developing'].sum(), label_visibility="collapsed")
                    col3.metric(f"{program} Req Dev", df_sw['Requires Dev'].sum(), label_visibility="collapsed")
                else:
                    st.info(f"No data for {program}")
        
        st.markdown("---")
        
        # ====== WORD AWARE OVERVIEW ======
        st.markdown("### 💬 Word Aware - All Programs")
        
        wa_cols = st.columns(3)
        
        for idx, program in enumerate(programs):
            collated = collate_by_program(all_assessments, program, term, year)
            
            with wa_cols[idx]:
                if collated:
                    fig_wa, df_wa = render_word_aware_chart(collated, program)
                    st.plotly_chart(fig_wa, use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric(f"{program} Mastered", df_wa['Mastered'].sum(), label_visibility="collapsed")
                    col2.metric(f"{program} Dev", df_wa['Developing'].sum(), label_visibility="collapsed")
                    col3.metric(f"{program} Req Dev", df_wa['Requires Dev'].sum(), label_visibility="collapsed")
                else:
                    st.info(f"No data for {program}")
        
        st.markdown("---")
        
        # ====== SMARTAR OVERVIEW ======
        st.markdown("### 🎯 SMARTAR Goals - All Programs")
        
        smartar_cols = st.columns(3)
        
        for idx, program in enumerate(programs):
            collated = collate_by_program(all_assessments, program, term, year)
            
            with smartar_cols[idx]:
                if collated:
                    fig_smartar, df_smartar = render_smartar_chart(collated, program)
                    st.plotly_chart(fig_smartar, use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric(f"{program} Reached", int(df_smartar['Reached Expected'].sum()), label_visibility="collapsed")
                    col2.metric(f"{program} Above", int(df_smartar['Above Expectation'].sum()), label_visibility="collapsed")
                    col3.metric(f"{program} Exceed", int(df_smartar['Exceeding'].sum()), label_visibility="collapsed")
                else:
                    st.info(f"No data for {program}")
    
    # ========================================================================
    # DETAILED ANALYSIS - Tabs for deep dive
    # ========================================================================
    
    else:  # "🔍 Detailed Analysis"
        col1, col2, col3 = st.columns(3)
        
        with col1:
            program = st.selectbox("🎓 Program", ['JP', 'PY', 'SY'], key="da_prog")
        with col2:
            term = st.selectbox("📅 Term", ['1', '2', '3', '4'], key="da_term")
        with col3:
            year = st.selectbox("📆 Year", ['2025', '2026'], key="da_year")
        
        st.markdown("---")
        
        collated = collate_by_program(all_assessments, program, term, year)
        
        if not collated:
            st.warning(f"No data found for {program} Term {term} {year}")
            return
        
        # Info
        col1, col2, col3 = st.columns(3)
        col1.metric("📋 Staff Entries", collated['staff_count'])
        col2.metric("📊 Total Records", collated['record_count'])
        col3.metric("📅 Selected", f"{program} T{term} {year}")
        
        st.markdown("---")
        
        # TABS for detailed view
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎵 Sounds Write",
            "💬 Word Aware",
            "🎯 SMARTAR Goals",
            "📋 Raw Data"
        ])
        
        # Tab 1: Sounds Write
        with tab1:
            st.markdown("### 🎵 Sounds Write Assessment")
            fig_sw, df_sw = render_sounds_write_chart(collated, program)
            st.plotly_chart(fig_sw, use_container_width=True)
            st.markdown("#### Data Table")
            st.dataframe(df_sw, use_container_width=True)
        
        # Tab 2: Word Aware
        with tab2:
            st.markdown("### 💬 Word Aware Assessment")
            fig_wa, df_wa = render_word_aware_chart(collated, program)
            st.plotly_chart(fig_wa, use_container_width=True)
            st.markdown("#### Data Table")
            st.dataframe(df_wa, use_container_width=True)
        
        # Tab 3: SMARTAR
        with tab3:
            st.markdown("### 🎯 SMARTAR Goals")
            fig_smartar, df_smartar = render_smartar_chart(collated, program)
            st.plotly_chart(fig_smartar, use_container_width=True)
            st.markdown("#### Metrics")
            col1, col2, col3 = st.columns(3)
            col1.metric("✅ Reached Expected", int(df_smartar['Reached Expected'].sum()))
            col2.metric("⬆️ Above Expectation", int(df_smartar['Above Expectation'].sum()))
            col3.metric("🌟 Exceeding", int(df_smartar['Exceeding'].sum()))
            st.markdown("#### Data Table")
            st.dataframe(df_smartar, use_container_width=True)
        
        # Tab 4: Raw Data
        with tab4:
            st.markdown("### 📋 Raw Data - All Entries")
            raw_records = [
                a for a in all_assessments 
                if a['program'] == program and 
                   a['term'] == int(term) and 
                   a['year'] == int(year)
            ]
            
            if raw_records:
                records_list = []
                for record in raw_records:
                    records_list.append({
                        'Staff': record['staff_member'],
                        'Program': record['program'],
                        'Term': record['term'],
                        'Year': record['year'],
                        'Date': record.get('date_submitted', '')[:10],
                        'Status': '✅'
                    })
                
                df_raw = pd.DataFrame(records_list)
                st.dataframe(df_raw, use_container_width=True)
                
                csv = df_raw.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"assessment_data_{program}_T{term}_{year}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No raw data records found.")

if __name__ == "__main__":
    main()
