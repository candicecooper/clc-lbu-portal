"""
CLC-LBU TERM ASSESSMENT DATA ENTRY (with Supabase)
Staff enter and save Sounds Write, Word Aware, SMARTAR data each term
UPDATED: Save buttons on each tab + overwrite-enabled saving
Page name: Term_Assessment_Data.py
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

st.set_page_config(
    page_title="📝 Term Assessment Data",
    page_icon="📝",
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
    
    .stButton > button {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.5) 0%, rgba(0, 229, 255, 0.25) 100%) !important;
        color: #00e5ff !important;
        border: 2px solid rgba(0, 229, 255, 0.6) !important;
        border-radius: 10px !important;
        font-weight: bold !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 122, 122, 0.25) 0%, rgba(0, 229, 255, 0.1) 100%) !important;
        border-left: 5px solid #00e5ff !important;
        border-radius: 10px !important;
    }
    
    .success-box {
        background: linear-gradient(135deg, rgba(76, 175, 80, 0.2) 0%, rgba(76, 175, 80, 0.05) 100%) !important;
        border-left: 5px solid #4CAF50 !important;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
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
# ASSESSMENT DATA STRUCTURE
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

# SMARTAR goal outcomes are entered as tallies against two capability areas.
# For each capability, staff record how many students:
#   - Reached their expected goal
#   - Reached above expectation
#   - Are exceeding
SMARTAR_CAPABILITIES = ['Personal and Social', 'Learning and Engagement']
SMARTAR_LEVELS = ['Reached Expected', 'Above Expectation', 'Exceeding']

# ============================================================================
# SESSION STATE - Initialize
# ============================================================================

if 'sounds_write' not in st.session_state:
    st.session_state.sounds_write = {}
if 'word_aware' not in st.session_state:
    st.session_state.word_aware = {}
if 'smartar' not in st.session_state:
    st.session_state.smartar = {}
if 'last_saved' not in st.session_state:
    st.session_state.last_saved = None

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def save_assessment_to_supabase(staff, program, term, year, sw, wa, smartar):
    """Save assessment data to Supabase - deletes old record then inserts new (allows overwrite)"""
    if not supabase:
        st.error("⚠️ Supabase not connected. Check credentials.")
        return False
    
    try:
        # Delete any existing record for this staff/program/term/year combo
        supabase.table('term_assessments').delete().eq(
            'staff_member', staff
        ).eq('program', program).eq('term', int(term)).eq('year', int(year)).execute()
        
        # Insert fresh record
        record = {
            'staff_member': staff,
            'program': program,
            'term': int(term),
            'year': int(year),
            'sounds_write_data': json.dumps(sw),
            'word_aware_data': json.dumps(wa),
            'smartar_goals': json.dumps(smartar),
            'date_submitted': datetime.now().isoformat()
        }
        
        supabase.table('term_assessments').insert(record).execute()
        st.session_state.last_saved = datetime.now()
        return True
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return False

def load_assessment_from_supabase(staff, program, term, year):
    """Load existing assessment data"""
    if not supabase:
        return None
    
    try:
        response = supabase.table('term_assessments').select('*').eq(
            'staff_member', staff
        ).eq('program', program).eq('term', int(term)).eq('year', int(year)).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        st.warning(f"Could not load data: {e}")
        return None

def get_all_assessments():
    """Get all assessment records"""
    if not supabase:
        return None
    
    try:
        response = supabase.table('term_assessments').select('*').execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching assessments: {e}")
        return None

# ============================================================================
# SAVE FUNCTION (used in multiple tabs)
# ============================================================================

def save_current_data(staff_member, program, term, year):
    """Save data with confirmation"""
    if supabase:
        if save_assessment_to_supabase(
            staff_member, program, term, year,
            st.session_state.sounds_write,
            st.session_state.word_aware,
            st.session_state.smartar
        ):
            st.success(f"✅ SAVED! {staff_member} - {program} Term {term} {year}")
            return True
        else:
            st.error("❌ Failed to save")
            return False
    else:
        st.error("Database not available")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    st.markdown("# 📝 TERM ASSESSMENT DATA ENTRY")
    st.markdown("_Sounds Write, Word Aware, and SMARTAR Goal Progress_")
    
    if not supabase:
        st.warning("⚠️ Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
    
    # Header
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        staff_list = ['Ben Sutton', 'Ben Selga', 'Jacqui', 'Caitie', 'Brenton', 'Naomi', 'Cheryl', 'Roisin']
        staff_member = st.selectbox("👤 Staff Member (or type below)", staff_list)
    
    # Allow custom staff member if not in list
    col_custom, _ = st.columns([1, 3])
    with col_custom:
        custom_staff = st.text_input("Or enter staff name if not listed", placeholder="e.g., Annette, Tom, Vinnie")
        if custom_staff.strip():
            staff_member = custom_staff.strip()
    with col2:
        program = st.selectbox("🎓 Program", ['JP', 'PY', 'SY'])
    with col3:
        term = st.selectbox("📅 Term", ['1', '2', '3', '4'])
    with col4:
        year = st.selectbox("📆 Year", ['2025', '2026'])
    
    # Load button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("📂 Load Existing Data"):
            existing = load_assessment_from_supabase(staff_member, program, term, year)
            if existing:
                st.success("✅ Existing data loaded!")
                st.session_state.sounds_write = json.loads(existing.get('sounds_write_data', '{}'))
                st.session_state.word_aware = json.loads(existing.get('word_aware_data', '{}'))
                st.session_state.smartar = json.loads(existing.get('smartar_goals', '{}'))
                st.rerun()
            else:
                st.info("No existing data found for this selection.")
    
    with col2:
        if st.session_state.last_saved:
            st.info(f"Last saved: {st.session_state.last_saved.strftime('%H:%M:%S')}")
    
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎵 Sounds Write",
        "💬 Word Aware",
        "🎯 SMARTAR Goals",
        "📊 Summary",
        "📋 All Records"
    ])
    
    # ========================================================================
    # TAB 1: SOUNDS WRITE
    # ========================================================================
    
    with tab1:
        st.markdown("### 🎵 Sounds Write Assessment")
        st.info("For each skill, enter number of students at each performance level")
        
        sounds_write_data = {}
        
        for skill in SOUNDS_WRITE_SKILLS:
            st.markdown(f"**{skill}**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                mastered = st.number_input(
                    "Mastered (85-100%)",
                    min_value=0,
                    value=st.session_state.sounds_write.get(skill, {}).get('Mastered', 0),
                    key=f"sw_m_{skill}"
                )
            with col2:
                developing = st.number_input(
                    "Developing (65-84%)",
                    min_value=0,
                    value=st.session_state.sounds_write.get(skill, {}).get('Developing', 0),
                    key=f"sw_d_{skill}"
                )
            with col3:
                requires = st.number_input(
                    "Requires Dev (<65%)",
                    min_value=0,
                    value=st.session_state.sounds_write.get(skill, {}).get('Requires Development', 0),
                    key=f"sw_r_{skill}"
                )
            
            sounds_write_data[skill] = {
                'Mastered': int(mastered),
                'Developing': int(developing),
                'Requires Development': int(requires)
            }
        
        st.session_state.sounds_write = sounds_write_data
        
        # SAVE BUTTON AT BOTTOM OF TAB
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Sounds Write Data", key="save_sw"):
                save_current_data(staff_member, program, term, year)
    
    # ========================================================================
    # TAB 2: WORD AWARE
    # ========================================================================
    
    with tab2:
        st.markdown("### 💬 Word Aware Assessment")
        st.info("For each skill, enter number of students at each performance level")
        
        word_aware_data = {}
        
        for skill in WORD_AWARE_SKILLS:
            st.markdown(f"**{skill}**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                mastered = st.number_input(
                    "Mastered (85-100%)",
                    min_value=0,
                    value=st.session_state.word_aware.get(skill, {}).get('Mastered', 0),
                    key=f"wa_m_{skill}"
                )
            with col2:
                developing = st.number_input(
                    "Developing (65-84%)",
                    min_value=0,
                    value=st.session_state.word_aware.get(skill, {}).get('Developing', 0),
                    key=f"wa_d_{skill}"
                )
            with col3:
                requires = st.number_input(
                    "Requires Dev (<65%)",
                    min_value=0,
                    value=st.session_state.word_aware.get(skill, {}).get('Requires Development', 0),
                    key=f"wa_r_{skill}"
                )
            
            word_aware_data[skill] = {
                'Mastered': int(mastered),
                'Developing': int(developing),
                'Requires Development': int(requires)
            }
        
        st.session_state.word_aware = word_aware_data
        
        # SAVE BUTTON AT BOTTOM OF TAB
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Word Aware Data", key="save_wa"):
                save_current_data(staff_member, program, term, year)
    
    # ========================================================================
    # TAB 3: SMARTAR GOALS
    # ========================================================================
    
    with tab3:
        st.markdown("### 🎯 SMARTAR Goal Outcomes")
        st.info("For each capability area, enter the number of students at each outcome level (tallies).")

        smartar_data = {}

        for capability in SMARTAR_CAPABILITIES:
            st.markdown(f"**{capability}**")
            col1, col2, col3 = st.columns(3)

            with col1:
                reached = st.number_input(
                    "Reached Expected Goal",
                    min_value=0,
                    value=st.session_state.smartar.get(capability, {}).get('Reached Expected', 0),
                    key=f"smartar_re_{capability}"
                )
            with col2:
                above = st.number_input(
                    "Above Expectation",
                    min_value=0,
                    value=st.session_state.smartar.get(capability, {}).get('Above Expectation', 0),
                    key=f"smartar_ab_{capability}"
                )
            with col3:
                exceeding = st.number_input(
                    "Exceeding",
                    min_value=0,
                    value=st.session_state.smartar.get(capability, {}).get('Exceeding', 0),
                    key=f"smartar_ex_{capability}"
                )

            smartar_data[capability] = {
                'Reached Expected': int(reached),
                'Above Expectation': int(above),
                'Exceeding': int(exceeding)
            }

        st.session_state.smartar = smartar_data

        # SAVE BUTTON AT BOTTOM OF TAB
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save SMARTAR Goals", key="save_smartar"):
                save_current_data(staff_member, program, term, year)
    
    # ========================================================================
    # TAB 4: SUMMARY & SAVE
    # ========================================================================
    
    with tab4:
        st.markdown("### 📊 Data Summary & Save")
        
        col1, col2, col3 = st.columns(3)
        
        if st.session_state.sounds_write:
            sw_total = sum([
                st.session_state.sounds_write[s]['Mastered'] + 
                st.session_state.sounds_write[s]['Developing'] + 
                st.session_state.sounds_write[s]['Requires Development']
                for s in SOUNDS_WRITE_SKILLS
            ]) // len(SOUNDS_WRITE_SKILLS)
            col1.metric("🎵 Sounds Write Students", int(sw_total))
        
        if st.session_state.word_aware:
            wa_total = sum([
                st.session_state.word_aware[s]['Mastered'] + 
                st.session_state.word_aware[s]['Developing'] + 
                st.session_state.word_aware[s]['Requires Development']
                for s in WORD_AWARE_SKILLS
            ]) // len(WORD_AWARE_SKILLS)
            col2.metric("💬 Word Aware Students", int(wa_total))
        
        smartar_total = 0
        for levels in st.session_state.smartar.values():
            if isinstance(levels, dict):
                smartar_total += (
                    levels.get('Reached Expected', 0)
                    + levels.get('Above Expectation', 0)
                    + levels.get('Exceeding', 0)
                )
        col3.metric("🎯 SMARTAR Outcomes Logged", int(smartar_total))
        
        st.markdown("---")
        st.markdown("### 💾 Save All Data")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save ALL Data", key="save_all"):
                if save_current_data(staff_member, program, term, year):
                    st.balloons()
        
        with col2:
            if st.button("🔄 Clear All"):
                st.session_state.sounds_write = {}
                st.session_state.word_aware = {}
                st.session_state.smartar = {}
                st.session_state.last_saved = None
                st.rerun()
    
    # ========================================================================
    # TAB 5: ALL RECORDS
    # ========================================================================
    
    with tab5:
        st.markdown("### 📋 All Assessment Records")
        
        if st.button("🔄 Refresh Records"):
            st.rerun()
        
        all_assessments = get_all_assessments()
        
        if all_assessments:
            records = []
            for record in all_assessments:
                records.append({
                    'Staff': record['staff_member'],
                    'Program': record['program'],
                    'Term': record['term'],
                    'Year': record['year'],
                    'Date Submitted': record.get('date_submitted', ''),
                    'Status': '✅ Saved'
                })
            
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"clc_assessments_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No assessment records found yet.")

if __name__ == "__main__":
    main()
