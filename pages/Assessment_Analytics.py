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

supabase = init_supabase()

def get_all_assessments():
    if not supabase:
        return []
    
    try:
        response = supabase.table('term_assessments').select('*').execute()
        return response.data if response.data else []
    except:
        return []

def parse_assessment_data(assessments):
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

st.markdown("# 📊 ASSESSMENT ANALYTICS DASHBOARD")
st.markdown("_Analyze term assessment data across programs and staff_")

if not supabase:
    st.warning("⚠️ Supabase not connected")
else:
    assessments = get_all_assessments()
    
    if not assessments:
        st.info("No assessment data found yet. Staff need to submit term assessments first.")
    else:
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
        st.info("✅ Analytics dashboard ready. Data will appear once assessments are submitted.")
