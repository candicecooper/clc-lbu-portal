"""
CLC-LBU ASSESSMENT ANALYTICS (with Program Collation)
View aggregated assessment data by program
Data is collated from all staff entries for each program
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
    
    # SMARTAR collated
    smartar_collated = {
        'Achieved': 0,
        'Exceeded': 0,
        'In Progress': 0,
        'Not Started': 0
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
        
        # Sum SMARTAR
        try:
            smartar_data = json.loads(assessment.get('smartar_goals', '{}'))
            for goal, data in smartar_data.items():
                achievement = data.get('achievement', 'Not Started')
                smartar_collated[achievement] += 1
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
# MAIN
# ============================================================================

def main():
    st.markdown("# 📊 ASSESSMENT ANALYTICS")
    st.markdown("_Program-Level Data (Collated from All Staff)_")
    
    if not supabase:
        st.warning("⚠️ Supabase not configured.")
        return
    
    # Get all assessments
    all_assessments = get_all_assessments()
    
    if not all_assessments:
        st.warning("No assessment data found yet.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        program = st.selectbox("🎓 Program", ['JP', 'PY', 'SY'])
    with col2:
        term = st.selectbox("📅 Term", ['1', '2', '3', '4'])
    with col3:
        year = st.selectbox("📆 Year", ['2025', '2026'])
    
    st.markdown("---")
    
    # Get collated data
    collated = collate_by_program(all_assessments, program, term, year)
    
    if not collated:
        st.warning(f"No data found for {program} Term {term} {year}")
        return
    
    # Show info
    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Staff Entries", collated['staff_count'])
    col2.metric("📊 Total Records", collated['record_count'])
    col3.metric("📅 Selected", f"{program} T{term} {year}")
    
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎵 Sounds Write",
        "💬 Word Aware",
        "🎯 SMARTAR Goals",
        "📋 Raw Data"
    ])
    
    # ========================================================================
    # TAB 1: SOUNDS WRITE ANALYTICS
    # ========================================================================
    
    with tab1:
        st.markdown("### 🎵 Sounds Write - Program Total")
        st.info(f"Combined data from {collated['staff_count']} staff member(s)")
        
        sw_data = collated['sounds_write']
        
        # Create visualization data
        vis_data = []
        for skill, levels in sw_data.items():
            vis_data.append({
                'Skill': skill,
                'Mastered': levels['Mastered'],
                'Developing': levels['Developing'],
                'Requires Dev': levels['Requires Development']
            })
        
        df_sw = pd.DataFrame(vis_data)
        
        # Stacked bar chart
        fig_sw = px.bar(
            df_sw,
            x='Skill',
            y=['Mastered', 'Developing', 'Requires Dev'],
            barmode='stack',
            title='Sounds Write Skills - Program Total',
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
            hovermode='x unified'
        )
        st.plotly_chart(fig_sw, use_container_width=True)
        
        # Data table
        st.markdown("#### Data Table")
        st.dataframe(df_sw, use_container_width=True)
        
        # Totals
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Total Mastered", df_sw['Mastered'].sum())
        col2.metric("🔄 Total Developing", df_sw['Developing'].sum())
        col3.metric("⚠️ Total Requires Dev", df_sw['Requires Dev'].sum())
    
    # ========================================================================
    # TAB 2: WORD AWARE ANALYTICS
    # ========================================================================
    
    with tab2:
        st.markdown("### 💬 Word Aware - Program Total")
        st.info(f"Combined data from {collated['staff_count']} staff member(s)")
        
        wa_data = collated['word_aware']
        
        # Create visualization data
        vis_data = []
        for skill, levels in wa_data.items():
            vis_data.append({
                'Skill': skill,
                'Mastered': levels['Mastered'],
                'Developing': levels['Developing'],
                'Requires Dev': levels['Requires Development']
            })
        
        df_wa = pd.DataFrame(vis_data)
        
        # Stacked bar chart
        fig_wa = px.bar(
            df_wa,
            x='Skill',
            y=['Mastered', 'Developing', 'Requires Dev'],
            barmode='stack',
            title='Word Aware Skills - Program Total',
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
            hovermode='x unified'
        )
        st.plotly_chart(fig_wa, use_container_width=True)
        
        # Data table
        st.markdown("#### Data Table")
        st.dataframe(df_wa, use_container_width=True)
        
        # Totals
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Total Mastered", df_wa['Mastered'].sum())
        col2.metric("🔄 Total Developing", df_wa['Developing'].sum())
        col3.metric("⚠️ Total Requires Dev", df_wa['Requires Dev'].sum())
    
    # ========================================================================
    # TAB 3: SMARTAR GOALS ANALYTICS
    # ========================================================================
    
    with tab3:
        st.markdown("### 🎯 SMARTAR Goals - Program Total")
        st.info(f"Combined data from {collated['staff_count']} staff member(s)")
        
        smartar_data = collated['smartar']
        
        # Create visualization data
        df_smartar = pd.DataFrame([{
            'Status': status,
            'Count': count
        } for status, count in smartar_data.items()])
        
        # Pie chart
        fig_smartar = px.pie(
            df_smartar,
            values='Count',
            names='Status',
            title='SMARTAR Goals Status - Program Total',
            color_discrete_map={
                'Achieved': '#4CAF50',
                'Exceeded': '#00BCD4',
                'In Progress': '#FFC107',
                'Not Started': '#F44336'
            }
        )
        fig_smartar.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#e8e8e8')
        )
        st.plotly_chart(fig_smartar, use_container_width=True)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏆 Exceeded", smartar_data['Exceeded'])
        col2.metric("✅ Achieved", smartar_data['Achieved'])
        col3.metric("🔄 In Progress", smartar_data['In Progress'])
        col4.metric("⏳ Not Started", smartar_data['Not Started'])
    
    # ========================================================================
    # TAB 4: RAW DATA
    # ========================================================================
    
    with tab4:
        st.markdown("### 📋 Raw Data - All Entries")
        
        # Get raw records for this program/term/year
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
            
            # Download button
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
