import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    pass

st.set_page_config(page_title="Allocation Dashboard", page_icon="📊", layout="wide")

# Initialize session state variables
if 'flag_df' not in st.session_state:
    st.session_state.flag_df = None
if 'funding_df' not in st.session_state:
    st.session_state.funding_df = None
if 'raap_df' not in st.session_state:
    st.session_state.raap_df = None
if 'incidents_df' not in st.session_state:
    st.session_state.incidents_df = None

# SMART CALENDAR DETECTION - Determine current term and year
def get_current_term_year():
    """
    Determine current SA school term and year based on date
    SA 2026 Terms with accurate dates:
    - T1: Jan 29 - Mar 20
    - T2: Apr 21 - Jun 26  
    - T3: Jul 27 - Sep 18
    - T4: Sep 19 - Dec 11
    """
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    
    # 2026 specific term boundaries
    if year == 2026:
        if month == 1:
            if day >= 29:
                term = 1
            else:
                term = 4  # Before Jan 29 is still T4 of previous year
        elif month == 2 or month == 3:
            if month == 3 and day > 20:
                term = 2  # After Mar 20 is T2
            else:
                term = 1
        elif month in [4, 5, 6]:
            if month == 4 and day < 21:
                term = 1  # Before Apr 21 is still T1
            elif month == 6 and day > 26:
                term = 3  # After Jun 26 is T3
            else:
                term = 2
        elif month in [7, 8, 9]:
            if month == 7 and day < 27:
                term = 2  # Before Jul 27 is still T2
            elif month == 9 and day > 18:
                term = 4  # After Sep 18 is T4
            else:
                term = 3
        else:  # Oct, Nov, Dec
            term = 4
    else:
        # Generic fallback
        if month in [1, 2, 3]:
            term = 1
        elif month in [4, 5, 6]:
            term = 2
        elif month in [7, 8, 9]:
            term = 3
        else:
            term = 4
    
    return year, term

# Initialize smart filters
if 'auto_year' not in st.session_state:
    current_year, current_term = get_current_term_year()
    st.session_state.auto_year = current_year
    st.session_state.auto_term = current_term
    st.session_state.selected_year = current_year
    st.session_state.selected_term = current_term

st.markdown("""
<style>
    /* HIDE ALL STREAMLIT UI ELEMENTS */
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
    .stToolbar { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    
    /* HIDE WHITE BANDS */
    [data-testid="stAppViewContainer"] > div { background: linear-gradient(135deg, rgba(10,14,39,1) 0%, rgba(8,12,32,1) 100%) !important; }
    .block-container { background: linear-gradient(135deg, rgba(10,14,39,0.95) 0%, rgba(8,12,32,0.95) 100%) !important; }
    section { background: linear-gradient(135deg, rgba(10,14,39,0.95) 0%, rgba(8,12,32,0.95) 100%) !important; }
    
    html, body { 
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    * { color: #ffffff !important; }
    
    h1, h2, h3, h4, h5, h6 { color: #00e5ff !important; text-shadow: 0 0 15px rgba(0,229,255,0.3); }
    p, span, div, label, button, a { color: #ffffff !important; }
    
    /* SIDEBAR - MATCH MAIN BACKGROUND WITH LIGHT BLUE ACCENT */
    [data-testid="stSidebar"] { 
        background: linear-gradient(135deg, rgba(10,14,39,0.98) 0%, rgba(8,12,32,0.98) 100%) !important;
        border-right: 2px solid rgba(0,229,255,0.25) !important;
    }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSidebar"] label { 
        font-weight: bold; 
        font-size: 14px;
        color: #ffffff !important;
        margin-top: 15px;
    }
    
    /* DROPDOWN/SELECT BOXES - AGGRESSIVE DARK STYLING */
    [data-testid="stSelectbox"] > div > div > div { 
        background: #1a2a3a !important;
        border: 1px solid #00e5ff !important;
        border-radius: 6px !important;
        color: #ffffff !important;
    }
    
    /* All select/combobox variations */
    [class*="select"] { background: #1a2a3a !important; color: #ffffff !important; }
    [class*="combobox"] { background: #1a2a3a !important; color: #ffffff !important; }
    
    /* Baseui Select Override */
    [data-baseweb="select"] { background: #1a2a3a !important; }
    [data-baseweb="select"] > div { background: #1a2a3a !important; border: 1px solid #00e5ff !important; }
    [data-baseweb="popover"] { background: #1a2a3a !important; }
    [data-baseweb="menu"] { background: #1a2a3a !important; }
    
    /* Dropdown opened state */
    [role="listbox"] { 
        background: #1a2a3a !important; 
        border: 1px solid #00e5ff !important;
        color: #ffffff !important;
    }
    [role="option"] { 
        color: #ffffff !important; 
        background: #1a2a3a !important;
    }
    [role="option"]:hover,
    [role="option"][aria-selected="true"] { 
        background: rgba(0,229,255,0.3) !important;
        color: #ffffff !important;
    }
    
    /* Text in select */
    [data-testid="stSelectbox"] input { 
        background: #1a2a3a !important;
        color: #ffffff !important;
        border: 1px solid #00e5ff !important;
    }
    
    /* Selectbox label */
    [data-testid="stSelectbox"] label { 
        color: #ffffff !important; 
        font-weight: bold; 
    }
    
    /* FILE UPLOADER */
    [data-testid="stFileUploader"] { background: #1a2a3a !important; border: 1px solid #00e5ff !important; border-radius: 6px !important; }
    [data-testid="stFileUploader"] label { color: #ffffff !important; font-weight: bold; }
    
    /* SIDEBAR DIVIDER */
    [data-testid="stSidebar"] hr { border-color: rgba(0,229,255,0.3) !important; }
    
    /* RADIO - STYLED BUTTONS */
    [role="radio"] { 
        padding: 10px 15px !important;
        border-radius: 6px !important;
        margin: 6px 0 !important;
        border: 1px solid rgba(0,229,255,0.2) !important;
        background: transparent !important;
        transition: all 0.2s !important;
    }
    [role="radio"]:hover { 
        background: rgba(0,229,255,0.1) !important;
        border-color: rgba(0,229,255,0.5) !important;
    }
    
    /* BUTTONS */
    .stButton > button { 
        background: rgba(0,229,255,0.15) !important; 
        border: 1px solid #00e5ff !important; 
        color: #ffffff !important; 
        font-weight: bold;
        border-radius: 6px !important;
        padding: 10px 20px !important;
    }
    .stButton > button:hover { 
        background: rgba(0,229,255,0.3) !important; 
    }
    
    /* METRICS */
    [data-testid="stMetricValue"] { color: #00e5ff !important; font-size: 2em; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; }
    [data-testid="metric-container"] { background: rgba(0,229,255,0.08) !important; border-radius: 8px !important; }
    
    /* BOXES */
    .stInfo { background: #1a2a3a !important; border-left: 4px solid #00e5ff !important; }
    .stInfo * { color: #ffffff !important; }
    .stWarning { background: #2a2415 !important; border-left: 4px solid #ffc107 !important; }
    .stWarning * { color: #ffffff !important; }
    .stSuccess { background: #1a2a1a !important; border-left: 4px solid #4caf50 !important; }
    .stSuccess * { color: #ffffff !important; }
    .stError { background: #2a1a1a !important; border-left: 4px solid #f44336 !important; }
    .stError * { color: #ffffff !important; }
    
    /* PLOTLY */
    .plotly text { fill: #ffffff !important; color: #ffffff !important; }
    .plotly .legend text { fill: #ffffff !important; color: #ffffff !important; }
    
    /* DATA FRAMES */
    [data-testid="stDataFrame"] { background: rgba(10,14,39,0.8) !important; }
    [data-testid="stDataFrame"] * { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

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

@st.cache_data
def load_allocation_data():
    if not supabase:
        return None
    try:
        response = supabase.table('allocation_students').select('*').execute()
        if response.data:
            return pd.DataFrame(response.data)
        return None
    except:
        return None

@st.cache_data
def load_flag_data_from_excel():
    """Load flag columns from Excel file - cached for performance"""
    try:
        import os
        excel_path = '/mnt/user-data/uploads/CLC_Allocation_Dashboard_2026_WithNames_1.xlsx'
        
        if os.path.exists(excel_path):
            excel_data = pd.read_excel(excel_path)
            
            if 'Student_Name' in excel_data.columns:
                excel_data['name_match'] = excel_data['Student_Name'].str.strip().str.lower()
                
                flag_cols = ['name_match']
                for col in ['Flag_ATSI', 'Flag_EALD', 'Flag_DCP_involvement']:
                    if col in excel_data.columns:
                        flag_cols.append(col)
                
                if len(flag_cols) > 1:
                    return excel_data[flag_cols].drop_duplicates('name_match')
    except:
        pass
    return None

# Pre-load flags at startup
cached_flag_df = load_flag_data_from_excel()

def update_chart_layout(fig):
    fig.update_layout(
        plot_bgcolor='rgba(10,14,39,0.8)',
        paper_bgcolor='rgba(10,14,39,0.8)',
        font=dict(color='#ffffff', size=12),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=True
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color='#ffffff'))
    fig.update_yaxes(showgrid=True, gridcolor='rgba(100,100,100,0.2)', tickfont=dict(color='#ffffff'))
    return fig

allocation_df = load_allocation_data()

# Load flag columns from Excel 
flag_df = None
flag_load_error = None
flag_load_debug = {}

if allocation_df is not None:
    try:
        import os
        excel_path = '/mnt/user-data/uploads/CLC_Allocation_Dashboard_2026_WithNames_1.xlsx'
        flag_load_debug['step_1_path_check'] = os.path.exists(excel_path)
        
        if os.path.exists(excel_path):
            excel_data = pd.read_excel(excel_path)
            flag_load_debug['step_2_excel_loaded'] = True
            flag_load_debug['step_3_excel_shape'] = excel_data.shape
            flag_load_debug['step_4_has_student_name'] = 'Student_Name' in excel_data.columns
            
            if 'Student_Name' in excel_data.columns:
                excel_data['name_match'] = excel_data['Student_Name'].str.strip().str.lower()
                flag_load_debug['step_5_name_match_created'] = True
                
                flag_cols = ['name_match']
                for col in ['Flag_ATSI', 'Flag_EALD', 'Flag_DCP_involvement']:
                    if col in excel_data.columns:
                        flag_cols.append(col)
                
                flag_load_debug['step_6_flag_cols'] = flag_cols
                flag_load_debug['step_7_len_flag_cols'] = len(flag_cols)
                
                if len(flag_cols) > 1:
                    flag_df = excel_data[flag_cols].drop_duplicates('name_match')
                    flag_load_debug['step_8_flag_df_shape'] = flag_df.shape
                    flag_load_debug['step_8_success'] = True
                else:
                    flag_load_error = f"No flag columns found. Cols: {flag_cols}"
            else:
                flag_load_error = "Student_Name column not found"
        else:
            flag_load_error = f"File not found: {excel_path}"
            
    except Exception as e:
        flag_load_error = f"Exception: {str(e)}"
        flag_load_debug['exception'] = str(e)

if allocation_df is None or allocation_df.empty:
    st.error("No data loaded")
else:
    # SIDEBAR
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 40px; padding: 20px 0; border-bottom: 2px solid rgba(0,229,255,0.5);'>
            <div style='font-size: 32px; margin-bottom: 8px;'>📊</div>
            <h2 style='color: #00e5ff; margin: 0; font-size: 20px; font-weight: bold;'>CLC-LBU</h2>
            <p style='color: #00e5ff; margin: 5px 0 0 0; font-size: 11px; font-weight: bold; letter-spacing: 1px;'>ALLOCATION ANALYTICS</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Navigate**", help="Select an analysis section")
        section = st.radio(
            "Select Section",
            ["Overview", "Trends", "Complexity", "Category of Support", "Cohort Analysis", "Equity", "Critical Incidents", "Assessment", "Waitlist", "Diagnostics"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("**Data Upload**", help="Upload Excel file with student allocation data and optional flag columns")
        
        uploaded_file = st.file_uploader("Choose Excel or CSV file", type=['xlsx', 'csv'], label_visibility="collapsed")
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                
                # Show available columns for debugging
                with st.expander("📋 Available columns in file"):
                    st.write("All columns:", list(df.columns))
                
                # === EXTRACT FLAG DATA (if columns exist) ===
                flag_cols_available = []
                for col in ['Flag_ATSI', 'Flag_EALD', 'Flag_DCP_involvement']:
                    if col in df.columns:
                        flag_cols_available.append(col)
                
                if 'Student_Name' in df.columns and flag_cols_available:
                    # Extract and cache flag data
                    flag_data = df[['Student_Name'] + flag_cols_available].copy()
                    flag_data['name_match'] = flag_data['Student_Name'].str.strip().str.lower()
                    flag_cols_for_merge = ['name_match'] + flag_cols_available
                    st.session_state.flag_df = flag_data[flag_cols_for_merge].drop_duplicates('name_match')
                
                # === EXTRACT FUNDING CATEGORY DATA (if columns exist) ===
                funding_cols_available = []
                for i in range(1, 10):
                    col = f'Flag_Category_{i}'
                    if col in df.columns:
                        funding_cols_available.append(col)
                
                if funding_cols_available:
                    st.info(f"✅ Found funding columns: {', '.join(funding_cols_available)}")
                
                if 'Student_Name' in df.columns and funding_cols_available:
                    # Extract and cache funding data
                    funding_data = df[['Student_Name'] + funding_cols_available].copy()
                    funding_data['name_match'] = funding_data['Student_Name'].str.strip().str.lower()
                    funding_cols_for_merge = ['name_match'] + funding_cols_available
                    st.session_state.funding_df = funding_data[funding_cols_for_merge].drop_duplicates('name_match')
                else:
                    if 'Student_Name' in df.columns:
                        st.warning("No funding category columns found (Flag_Category_1 to 9)")
                
                # === EXTRACT RAAP FLAG (if exists) ===
                if 'Flag_9plusRAAP' in df.columns and 'Student_Name' in df.columns:
                    raap_data = df[['Student_Name', 'Flag_9plusRAAP']].copy()
                    raap_data['name_match'] = raap_data['Student_Name'].str.strip().str.lower()
                    st.session_state.raap_df = raap_data[['name_match', 'Flag_9plusRAAP']].drop_duplicates('name_match')
                # === EXTRACT CRITICAL INCIDENTS (if sheet exists) ===
                try:
                    # Try to read Critical_Incidents sheet
                    if isinstance(uploaded_file.name, str) and uploaded_file.name.endswith('.xlsx'):
                        incidents_df = pd.read_excel(uploaded_file, sheet_name='Critical_Incidents')
                        if len(incidents_df) > 0 and 'Student_Name' in incidents_df.columns:
                            incidents_df['name_match'] = incidents_df['Student_Name'].str.strip().str.lower()
                            st.session_state.incidents_df = incidents_df
                except:
                    pass
                
                # === PROCESS STUDENT DATA ===
                column_map = {
                    'Student_Name': 'student_name', 'Meeting_Week': 'meeting_week', 'Meeting_Date': 'meeting_date',
                    'Term': 'term', 'Referral_Year': 'year', 'Allocated_Program': 'program',
                    'DOB': 'date_of_birth', 'Gender': 'gender', 'Year_Level': 'year_level',
                    'Referring_School': 'school', 'Partnership_Area': 'partnership_area',
                    'Previous_CLC_Placement': 'previous_clc_placement', 'Previous_Other_LC': 'previous_other_lc',
                    'Other_LC_Name': 'other_lc_name', 'Total_Previous_Placements': 'total_previous_placements',
                    'Placement_History_Notes': 'placement_history_notes', 'Bespoke_Placement': 'bespoke_placement',
                    'Waitlist_Status': 'waitlist_status', 'Waitlist_Date': 'waitlist_date',
                    'Allocated_From_Waitlist': 'allocated_from_waitlist', 'Previously_Referred': 'previously_referred',
                    'Medical_Condition_Details': 'medical_condition_details', 'Extension_Weeks': 'extension_weeks',
                }
                
                df_mapped = df.copy()
                for excel_col, supabase_col in column_map.items():
                    if excel_col in df_mapped.columns:
                        df_mapped = df_mapped.rename(columns={excel_col: supabase_col})
                
                df_mapped = df_mapped[[col for col in df_mapped.columns if col in column_map.values()]]
                
                date_cols = ['meeting_date', 'date_of_birth', 'waitlist_date']
                for col in date_cols:
                    if col in df_mapped.columns:
                        df_mapped[col] = pd.to_datetime(df_mapped[col], errors='coerce')
                        df_mapped[col] = df_mapped[col].dt.strftime('%Y-%m-%d')
                        df_mapped[col] = df_mapped[col].replace('NaT', '')
                
                numeric_cols = ['year', 'term', 'extension_weeks', 'total_previous_placements']
                for col in numeric_cols:
                    if col in df_mapped.columns:
                        df_mapped[col] = pd.to_numeric(df_mapped[col], errors='coerce').fillna(0).astype(int)
                
                df_mapped = df_mapped.astype(str)
                df_mapped = df_mapped.replace('nan', '')
                df_mapped = df_mapped.fillna('')
                
                for col in df_mapped.columns:
                    if df_mapped[col].dtype == 'object':
                        df_mapped[col] = df_mapped[col].str.strip()
                
                if 'meeting_date' in df_mapped.columns:
                    today = pd.Timestamp.now().strftime('%Y-%m-%d')
                    df_mapped['meeting_date'] = df_mapped['meeting_date'].replace('', today)
                
                # Show status
                status_msg = f"Ready: {len(df_mapped)} student records"
                if 'flag_df' in st.session_state and st.session_state.flag_df is not None:
                    status_msg += f" + {len(st.session_state.flag_df)} flag records"
                if 'funding_df' in st.session_state and st.session_state.funding_df is not None:
                    status_msg += f" + {len(st.session_state.funding_df)} funding records"
                if 'raap_df' in st.session_state and st.session_state.raap_df is not None:
                    status_msg += f" + RAAP"
                if 'incidents_df' in st.session_state and st.session_state.incidents_df is not None:
                    status_msg += f" + {len(st.session_state.incidents_df)} incidents"
                st.success(status_msg)
                
                if st.button("Upload Now"):
                    if not supabase:
                        st.error("Supabase not connected")
                    else:
                        with st.spinner("Uploading..."):
                            try:
                                supabase.table('allocation_students').delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
                                
                                numeric_cols = ['year', 'term', 'extension_weeks', 'total_previous_placements']
                                date_cols = ['meeting_date', 'date_of_birth', 'waitlist_date']
                                
                                records = []
                                for idx, row in df_mapped.iterrows():
                                    record = {}
                                    for col in df_mapped.columns:
                                        val = row[col]
                                        if pd.isna(val) or val == 'nan' or val == '':
                                            record[col] = 0 if col in numeric_cols else (None if col in date_cols else '')
                                        else:
                                            record[col] = str(val)
                                    records.append(record)
                                
                                for i in range(0, len(records), 50):
                                    supabase.table('allocation_students').insert(records[i:i+50]).execute()
                                
                                st.success(f"Uploaded {len(records)} records!")
                                st.cache_data.clear()
                                
                            except Exception as e:
                                st.error(f"Failed: {str(e)[:150]}")
            
            except Exception as e:
                st.error(f"Error: {e}")
        
        st.markdown("---")
        st.markdown("**Data Status**")
        
        status_items = []
        if 'flag_df' in st.session_state and st.session_state.flag_df is not None:
            status_items.append(f"✅ Flags: {len(st.session_state.flag_df)} records")
        else:
            status_items.append("⚪ Flags: not loaded")
        
        if 'funding_df' in st.session_state and st.session_state.funding_df is not None:
            status_items.append(f"✅ Funding: {len(st.session_state.funding_df)} records")
        else:
            status_items.append("⚪ Funding: not loaded")
        
        if 'raap_df' in st.session_state and st.session_state.raap_df is not None:
            status_items.append(f"✅ RAAP: loaded")
        else:
            status_items.append("⚪ RAAP: not loaded")
        
        for item in status_items:
            st.write(item)
    
    # TOP TITLE
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(0,229,255,0.08) 100%); 
                border: 2px solid #00e5ff; border-radius: 12px; padding: 30px 25px; 
                margin-bottom: 30px; text-align: center;'>
        <h1 style='color: #00e5ff; font-size: 52px; margin: 0; font-weight: bold; 
                   letter-spacing: 0.5px;'>Student Allocation</h1>
        <p style='color: #00e5ff; font-size: 16px; margin: 15px 0 0 0; 
                 font-weight: 500; opacity: 0.9;'>Comprehensive Enrollment Analytics & Equity Insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Get unique years - handle both string and numeric
        allocation_df['year_clean'] = pd.to_numeric(allocation_df['year'], errors='coerce')
        years = sorted([int(y) for y in allocation_df['year_clean'].dropna().unique()])
        if not years:
            years = [2026]
        year_options = ['All'] + years
        
        # Default to current year
        default_year_idx = year_options.index(st.session_state.auto_year) if st.session_state.auto_year in year_options else 1
        selected_year = st.selectbox("Year", year_options, index=default_year_idx)
    
    with col2:
        # Filter terms by selected year (or show all if "All" selected)
        if selected_year == 'All':
            year_data = allocation_df
        else:
            year_data = allocation_df[allocation_df['year_clean'] == selected_year]
        
        year_data['term_clean'] = pd.to_numeric(year_data['term'], errors='coerce')
        terms = sorted([int(t) for t in year_data['term_clean'].dropna().unique() if t >= 1])
        if not terms:
            terms = [1, 2, 3, 4]
        term_options = ['All'] + terms
        
        # Default to current term (if in current year)
        if selected_year == 'All':
            default_term_idx = 1
        elif selected_year == st.session_state.auto_year:
            default_term_idx = term_options.index(st.session_state.auto_term) if st.session_state.auto_term in term_options else 1
        else:
            default_term_idx = 1
        
        selected_term = st.selectbox("Term", term_options, index=default_term_idx)
    
    with col3:
        # Clean program data and build dropdown - handle variations and blanks
        allocation_df['program_clean'] = allocation_df['program'].fillna('').str.strip().str.upper()
        # Only include non-blank, valid programs
        all_progs = sorted([p for p in allocation_df['program_clean'].unique() if p and p not in ['', ':', 'NONE']])
        progs = ['All'] + all_progs
        # Default program to "All"
        selected_program = st.selectbox("Program", progs, index=0)
    
    # FILTER DATA - handle "All" selections
    allocation_df['year_clean'] = pd.to_numeric(allocation_df['year'], errors='coerce')
    allocation_df['term_clean'] = pd.to_numeric(allocation_df['term'], errors='coerce')
    
    # CLEAN PROGRAM DATA - Remove blanks and inconsistencies
    allocation_df['program'] = allocation_df['program'].fillna('').str.strip()
    allocation_df['program'] = allocation_df['program'].replace(['', ':', 'None'], None)
    allocation_df['program_clean'] = allocation_df['program'].fillna('').str.strip().str.upper()
    allocation_df['program_clean'] = allocation_df['program_clean'].replace(['', ':', 'NONE'], '')
    
    # CLEAN YEAR_LEVEL - Remove blanks
    allocation_df['year_level'] = allocation_df['year_level'].fillna('').astype(str).str.strip()
    allocation_df['year_level'] = allocation_df['year_level'].replace(['', 'nan', 'None'], None)
    
    # CLEAN PARTNERSHIP AREA - Remove blanks
    allocation_df['partnership_area'] = allocation_df['partnership_area'].fillna('').astype(str).str.strip()
    allocation_df['partnership_area'] = allocation_df['partnership_area'].replace(['', 'nan', 'None'], None)
    
    filtered = allocation_df.copy()
    
    # Remove records with blank programs from all filtered data
    filtered = filtered[filtered['program_clean'] != '']
    
    # Apply year filter
    if selected_year != 'All':
        filtered = filtered[filtered['year_clean'] == selected_year]
    
    # Apply term filter
    if selected_term != 'All':
        filtered = filtered[filtered['term_clean'] == selected_term]
    
    # Apply program filter
    if selected_program != 'All':
        filtered = filtered[filtered['program_clean'] == selected_program]
    
    st.markdown(f"""
    <div style='background: rgba(0,229,255,0.1); border-left: 4px solid #00e5ff; 
                padding: 16px 20px; border-radius: 6px; margin: 20px 0;'>
        <p style='color: #00e5ff; font-size: 18px; margin: 0; font-weight: 600;'>
            📊 {len(filtered)} Active Students
        </p>
        <p style='color: #00e5ff; font-size: 13px; margin: 8px 0 0 0; opacity: 0.85;'>
            Year: <strong>{selected_year if selected_year != 'All' else 'All'}</strong> 
            | Term: <strong>{selected_term if selected_term != 'All' else 'All'}</strong> 
            | Program: <strong>{selected_program}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    # CONTENT BY SECTION
    if section == "Overview":
        # Display year/term context in title
        year_display = st.session_state.auto_year if selected_year == 'All' else selected_year
        term_display = st.session_state.auto_term if selected_term == 'All' else selected_term
        
        st.markdown(f"## Active Students Overview")
        st.markdown(f"**Year {year_display} | Term {term_display}** - Current enrollment and placement status")
        
        # Debug expander
        with st.expander("🔍 Debug - View filtering details"):
            st.write(f"Selected Year: {selected_year}")
            st.write(f"Selected Term: {selected_term}")
            st.write(f"Selected Program: {selected_program}")
            st.write(f"Total records after filtering: {len(filtered)}")
            st.write(f"Unique programs in filtered data: {filtered['program'].unique().tolist()}")
            st.write(f"Unique years in filtered data: {filtered['year_clean'].unique().tolist()}")
            st.write(f"Unique terms in filtered data: {filtered['term_clean'].unique().tolist()}")
            
            # Show program breakdown
            prog_breakdown = filtered['program'].value_counts().to_dict()
            st.write(f"Program breakdown: {prog_breakdown}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Students", int(len(filtered)))
        col2.metric("Programs", int(filtered['program'].nunique()))
        col3.metric("Year Levels", int(filtered['year_level'].nunique()))
        col4.metric("As at", datetime.now().strftime("%d/%m/%y"))
        
        st.markdown("---")
        st.markdown("## Distribution by Program & Year Level")
        st.markdown("Shows where students are placed across our three programs (JP, PY, SY) and year levels (R-10)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'program' in filtered.columns:
                prog_data = filtered['program'].value_counts().reset_index()
                prog_data.columns = ['program', 'count']
                prog_data['count'] = prog_data['count'].astype(int)
                
                fig = px.bar(prog_data, x='program', y='count', text='count', 
                            color='count', color_continuous_scale='Viridis',
                            title='Students by Program', labels={'program': '', 'count': ''})
                fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                st.markdown("**What this shows:** Enrollment numbers in each program")
        
        with col2:
            if 'year_level' in filtered.columns:
                year_data = filtered['year_level'].value_counts().sort_index().reset_index()
                year_data.columns = ['year_level', 'count']
                year_data['count'] = year_data['count'].astype(int)
                
                fig = px.bar(year_data, x='year_level', y='count', text='count',
                            color_discrete_sequence=['#4ecdc4'],
                            title='Students by Year Level', labels={'year_level': '', 'count': ''})
                fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                st.markdown("**What this shows:** Distribution across year levels R through 10")
        
        st.markdown("---")
        st.markdown("## Partnership Placements")
        st.markdown("Top partnership areas supporting student placements - shows partnership demand")
        
        if 'partnership_area' in filtered.columns:
            partner_data = filtered['partnership_area'].value_counts().head(10).reset_index()
            partner_data.columns = ['partnership_area', 'count']
            partner_data['count'] = partner_data['count'].astype(int)
            
            fig = px.bar(partner_data, y='partnership_area', x='count', orientation='h',
                        text='count', color='count', color_continuous_scale='Reds',
                        title='Top 10 Partnerships', labels={'partnership_area': '', 'count': ''})
            fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
            st.plotly_chart(update_chart_layout(fig), use_container_width=True)
            st.markdown("**What this shows:** Which partnership areas have the most student placements")
    
    elif section == "Trends":
        st.markdown("## Enrollment Trends")
        st.markdown("Line chart showing enrollment over time by program. **Solid lines = actual data | Dashed lines = forecast**")
        
        # Make sure we have clean numeric columns
        trend_data = allocation_df.dropna(subset=['program']).copy()
        trend_data['year_num'] = pd.to_numeric(trend_data['year'], errors='coerce')
        trend_data['term_num'] = pd.to_numeric(trend_data['term'], errors='coerce')
        
        # Filter for valid data
        trend_data = trend_data.dropna(subset=['year_num', 'term_num'])
        trend_data = trend_data[trend_data['term_num'] >= 1]
        
        # Create proper year-term format (2025 T1, 2025 T2, etc)
        trend_data['YearTerm'] = trend_data['year_num'].astype(int).astype(str) + ' T' + trend_data['term_num'].astype(int).astype(str)
        trend_agg = trend_data.groupby(['YearTerm', 'program']).size().reset_index(name='count')
        trend_agg['count'] = trend_agg['count'].astype(int)
        
        # Create sort key for proper ordering
        trend_agg['year_sort'] = trend_agg['YearTerm'].str.extract(r'(\d{4})')[0].astype(int)
        trend_agg['term_sort'] = trend_agg['YearTerm'].str.extract(r'T(\d)')[0].astype(int)
        trend_agg['sort_key'] = trend_agg['year_sort'] * 100 + trend_agg['term_sort']
        trend_agg = trend_agg.sort_values('sort_key').reset_index(drop=True)
        
        # Get unique year-terms in order
        unique_yearterms = trend_agg.sort_values('sort_key')['YearTerm'].unique().tolist()
        
        # ACTUAL DATA
        fig_trend = px.line(
            trend_agg,
            x='YearTerm',
            y='count',
            color='program',
            markers=True,
            title='Actual Enrollment by Program',
            labels={'YearTerm': '', 'count': 'Students'}
        )
        fig_trend.update_xaxes(categoryorder='array', categoryarray=unique_yearterms)
        fig_trend.update_traces(line=dict(width=3), marker=dict(size=8))
        st.plotly_chart(update_chart_layout(fig_trend), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## Enrollment Forecast")
        st.markdown("Predicted enrollment trends based on current patterns - **for planning purposes only**")
        
        # CREATE FORECAST DATA
        forecast_data = []
        
        for prog in trend_agg['program'].unique():
            prog_data = trend_agg[trend_agg['program'] == prog].sort_values('sort_key')
            
            # Add actual data
            for idx, row in prog_data.iterrows():
                forecast_data.append({
                    'YearTerm': row['YearTerm'],
                    'count': row['count'],
                    'program': prog,
                    'type': 'Actual',
                    'sort_key': row['sort_key']
                })
            
            # Generate forecast for next 4 periods
            if len(prog_data) >= 1:
                last_year = prog_data.iloc[-1]['year_sort']
                last_term = prog_data.iloc[-1]['term_sort']
                
                # Calculate trend from last 2 points if available
                if len(prog_data) >= 2:
                    last_counts = prog_data['count'].tail(2).values
                    trend_rate = last_counts[-1] - last_counts[-2]
                else:
                    trend_rate = 0
                
                last_count = prog_data.iloc[-1]['count']
                
                for i in range(1, 5):
                    new_term = last_term + i
                    new_year = last_year
                    
                    if new_term > 4:
                        new_year = last_year + (new_term - 1) // 4
                        new_term = ((new_term - 1) % 4) + 1
                    
                    forecast_count = max(last_count + (trend_rate * i), 0)
                    forecast_data.append({
                        'YearTerm': f'{new_year} T{new_term}',
                        'count': int(forecast_count),
                        'program': prog,
                        'type': 'Forecast',
                        'sort_key': new_year * 100 + new_term
                    })
        
        forecast_df = pd.DataFrame(forecast_data)
        forecast_df = forecast_df.sort_values('sort_key')
        
        # Get all unique year-terms in correct order
        all_yearterms = sorted(forecast_df['YearTerm'].unique(), key=lambda x: (int(x.split()[0]), int(x.split('T')[1])))
        
        # Separate actual and forecast
        actual = forecast_df[forecast_df['type'] == 'Actual']
        predicted = forecast_df[forecast_df['type'] == 'Forecast']
        
        # Create combined figure
        fig_forecast = go.Figure()
        
        # Add actual lines - ensure ALL programs shown
        all_programs = sorted(forecast_df['program'].unique())
        for prog in all_programs:
            prog_actual = actual[actual['program'] == prog].sort_values('sort_key')
            if len(prog_actual) > 0:
                fig_forecast.add_trace(go.Scatter(
                    x=prog_actual['YearTerm'],
                    y=prog_actual['count'],
                    mode='lines+markers',
                    name=f'{prog} (Actual)',
                    line=dict(width=3),
                    marker=dict(size=8)
                ))
        
        # Add forecast lines (dashed)
        for prog in all_programs:
            prog_forecast = predicted[predicted['program'] == prog].sort_values('sort_key')
            
            if len(prog_forecast) > 0:
                fig_forecast.add_trace(go.Scatter(
                    x=prog_forecast['YearTerm'],
                    y=prog_forecast['count'],
                    mode='lines+markers',
                    name=f'{prog} (Forecast)',
                    line=dict(width=2, dash='dash'),
                    marker=dict(size=6, symbol='diamond'),
                    opacity=0.6
                ))
        
        fig_forecast.update_layout(
            title='Enrollment Trends & Forecast',
            xaxis_title='',
            yaxis_title='Students',
            plot_bgcolor='rgba(10,14,39,0.8)',
            paper_bgcolor='rgba(10,14,39,0.8)',
            font=dict(color='#ffffff', size=12),
            hovermode='x unified',
            margin=dict(l=40, r=40, t=40, b=40),
            showlegend=True,
            xaxis=dict(categoryorder='array', categoryarray=all_yearterms)
        )
        fig_forecast.update_xaxes(showgrid=False, tickfont=dict(color='#ffffff'))
        fig_forecast.update_yaxes(showgrid=True, gridcolor='rgba(100,100,100,0.2)', tickfont=dict(color='#ffffff'))
        
        st.plotly_chart(fig_forecast, use_container_width=True)
        
        st.markdown("**Legend:**")
        st.write("- **Solid lines** = Actual enrollment data")
        st.write("- **Dashed lines** = Forecast projections (4 terms ahead)")
        st.write("- Based on recent enrollment trends")
    
    elif section == "Complexity":
        st.markdown("## Complexity Analysis")
        st.markdown("Matrix showing how students distribute across year levels and programs. Identifies gaps and concentrations in placement.")
        
        if 'year_level' in filtered.columns and 'program' in filtered.columns:
            # Define correct year level order
            year_order = ['R', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
            program_order = ['JP', 'PY', 'SY']
            
            # Create heatmap data
            heatmap = pd.crosstab(filtered['year_level'], filtered['program'])
            
            # Reindex to ensure ALL year levels appear (even if empty)
            heatmap = heatmap.reindex([y for y in year_order if y in filtered['year_level'].unique()], fill_value=0)
            
            # Reindex to ensure ALL programs appear (even if empty)
            available_progs = [p for p in program_order if p in filtered['program'].unique()]
            heatmap = heatmap.reindex(available_progs, axis=1, fill_value=0)
            
            fig = px.imshow(heatmap, text_auto=True, color_continuous_scale='Blues',
                           title='Student Distribution: Year Level × Program',
                           labels={'x': 'Program', 'y': 'Year Level', 'color': 'Count'},
                           aspect='auto')
            fig.update_traces(text=heatmap.values, texttemplate='%{text}')
            st.plotly_chart(update_chart_layout(fig), use_container_width=True)
            
            st.markdown("**Key Insights:**")
            st.write("- Numbers show student count in each year level/program combination")
            st.write("- Darker blue = higher concentration")
            st.write("- Empty cells = no students placed")
        else:
            st.warning("Year level or program data missing")
    
    elif section == "Category of Support":
        st.markdown("## Category of Support Analysis")
        st.markdown("Student distribution by support category (Cat 1-9 + RAAP) - identifies support needs and resource allocation")
        
        # Extract funding category for each student
        risk_df = filtered.copy()
        risk_df['funding_category'] = 'None'
        risk_df['is_raap'] = 'No'
        
        # Merge funding data if available (for uploaded data)
        if 'funding_df' in st.session_state and st.session_state.funding_df is not None:
            risk_df['name_match'] = risk_df['student_name'].str.strip().str.lower()
            risk_df = risk_df.merge(st.session_state.funding_df, on='name_match', how='left')
            risk_df = risk_df.drop('name_match', axis=1)
        
        # Merge RAAP data if available
        if 'raap_df' in st.session_state and st.session_state.raap_df is not None:
            risk_df['name_match'] = risk_df['student_name'].str.strip().str.lower()
            risk_df = risk_df.merge(st.session_state.raap_df, on='name_match', how='left')
            risk_df = risk_df.drop('name_match', axis=1)
        
        # Determine funding category from Flag_Category columns (highest category takes precedence)
        for cat in range(9, 0, -1):
            col_name = f'Flag_Category_{cat}'
            if col_name in risk_df.columns:
                # Handle both 'Yes' and True values
                risk_df.loc[(risk_df[col_name] == 'Yes') | (risk_df[col_name] == True), 'funding_category'] = f'Cat {cat}'
        
        # Check for RAAP AFTER setting base category - if Cat 9 + RAAP, change to Cat 9+RAAP
        if 'Flag_9plusRAAP' in risk_df.columns:
            raap_mask = (risk_df['Flag_9plusRAAP'] == 'Yes') | (risk_df['Flag_9plusRAAP'] == True)
            risk_df.loc[raap_mask, 'funding_category'] = 'Cat 9+RAAP'
            risk_df.loc[raap_mask, 'is_raap'] = 'Yes (RAAP)'
        
        # If cat_funding column exists and funding_category is still None, use it
        if 'cat_funding' in risk_df.columns:
            cat_funding_values = risk_df.loc[risk_df['funding_category'] == 'None', 'cat_funding'].fillna('None').astype(str)
            risk_df.loc[risk_df['funding_category'] == 'None', 'funding_category'] = cat_funding_values
        
        # Ensure funding_category is string type
        risk_df['funding_category'] = risk_df['funding_category'].astype(str)
        risk_df['funding_category'] = risk_df['funding_category'].replace('nan', 'None')
        
        # SUMMARY METRICS
        col1, col2, col3, col4 = st.columns(4)
        
        cat_counts = risk_df['funding_category'].value_counts().to_dict()
        col1.metric("Cat 9+RAAP", int(cat_counts.get('Cat 9+RAAP', 0)))
        col2.metric("Cat 9 Only", int(cat_counts.get('Cat 9', 0)))
        col3.metric("Cat 5-8", int(sum(cat_counts.get(f'Cat {i}', 0) for i in range(5, 9))))
        col4.metric("Cat 1-4", int(sum(cat_counts.get(f'Cat {i}', 0) for i in range(1, 5))))
        
        st.markdown("---")
        st.markdown("## Funding Category Distribution")
        st.markdown("How many students are in each funding category")
        
        col1, col2 = st.columns(2)
        
        with col1:
            funding_summary = risk_df['funding_category'].value_counts().reset_index()
            funding_summary.columns = ['category', 'count']
            funding_summary['count'] = funding_summary['count'].astype(int)
            
            # Create custom sort order - Cat 9+RAAP at top (highest), then Cat 9, then 8-1, then None
            category_order = ['Cat 9+RAAP', 'Cat 9', 'Cat 8', 'Cat 7', 'Cat 6', 'Cat 5', 'Cat 4', 'Cat 3', 'Cat 2', 'Cat 1', 'None']
            funding_summary['sort_order'] = funding_summary['category'].apply(
                lambda x: category_order.index(x) if x in category_order else 999
            )
            funding_summary = funding_summary.sort_values('sort_order')
            
            # Color by urgency - Cat 9+RAAP darkest
            color_map = {
                'Cat 9+RAAP': 99,
                'Cat 9': 9,
                'Cat 8': 8,
                'Cat 7': 7,
                'Cat 6': 6,
                'Cat 5': 5,
                'Cat 4': 4,
                'Cat 3': 3,
                'Cat 2': 2,
                'Cat 1': 1,
                'None': 0
            }
            funding_summary['color_key'] = funding_summary['category'].map(color_map)
            
            fig_funding = px.bar(
                funding_summary,
                x='category',
                y='count',
                text='count',
                color='color_key',
                color_continuous_scale='Reds',
                title='Students by Funding Category',
                labels={'category': 'Category', 'count': 'Students', 'color_key': 'Urgency'}
            )
            fig_funding.update_xaxes(categoryorder='array', categoryarray=category_order)
            fig_funding.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
            st.plotly_chart(update_chart_layout(fig_funding), use_container_width=True)
        
        with col2:
            # Funding by program
            if 'program' in risk_df.columns:
                fund_prog = risk_df.groupby(['program', 'funding_category']).size().unstack(fill_value=0)
                
                fig_fund_prog = px.bar(
                    fund_prog,
                    barmode='stack',
                    title='Funding Categories by Program',
                    labels={'value': 'Count', 'index': 'Program'}
                )
                st.plotly_chart(update_chart_layout(fig_fund_prog), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## Funding Category Details")
        st.markdown("Breakdown by category and program")
        
        # Create matrix of programs x funding categories
        if 'program' in risk_df.columns and 'funding_category' in risk_df.columns:
            fund_matrix = pd.crosstab(risk_df['program'], risk_df['funding_category'])
            
            # Reorder columns (Cat 9+RAAP first, then highest to lowest)
            cat_order = ['Cat 9+RAAP'] + [f'Cat {i}' for i in range(9, 0, -1)] + ['None']
            cat_order = [c for c in cat_order if c in fund_matrix.columns]
            fund_matrix = fund_matrix[cat_order]
            
            fig_matrix = px.imshow(
                fund_matrix,
                text_auto=True,
                color_continuous_scale='YlOrRd',
                title='Program × Funding Category',
                labels={'x': 'Funding Category', 'y': 'Program', 'color': 'Students'}
            )
            fig_matrix.update_traces(text=fund_matrix.values, texttemplate='%{text}')
            fig_matrix.update_xaxes(categoryorder='array', categoryarray=cat_order)
            st.plotly_chart(update_chart_layout(fig_matrix), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## Highest-Need Students (Cat 9+RAAP & Cat 9)")
        st.markdown("Students requiring most intensive support and resources")
        
        high_need = risk_df[risk_df['funding_category'].isin(['Cat 9+RAAP', 'Cat 9', 'Cat 8'])].copy()
        
        if len(high_need) > 0:
            display_cols = ['program', 'year_level', 'funding_category', 'partnership_area']
            display_cols = [col for col in display_cols if col in high_need.columns]
            
            high_need_display = high_need[display_cols].copy().sort_values('funding_category', ascending=False)
            
            # Highlight Cat 9+RAAP in the data
            st.dataframe(high_need_display, use_container_width=True, hide_index=True)
            
            cat_9_raap_count = (high_need['funding_category'] == 'Cat 9+RAAP').sum()
            cat_9_only_count = (high_need['funding_category'] == 'Cat 9').sum()
            cat_8_count = (high_need['funding_category'] == 'Cat 8').sum()
            
            st.info(f"**{int(cat_9_raap_count)} students** in Cat 9+RAAP | **{int(cat_9_only_count)} students** in Cat 9 | **{int(cat_8_count)} students** in Cat 8 (highest support needs)")
        else:
            st.success("✅ No highest-need students in current selection")
        
        st.markdown("---")
        st.markdown("## Resource Allocation Summary")
        
        col1, col2, col3 = st.columns(3)
        
        total_students = len(risk_df)
        cat_9_raap_pct = int((risk_df['funding_category'] == 'Cat 9+RAAP').sum() / total_students * 100) if total_students > 0 else 0
        cat_9_only_pct = int((risk_df['funding_category'] == 'Cat 9').sum() / total_students * 100) if total_students > 0 else 0
        
        col1.metric("Cat 9+RAAP %", f"{cat_9_raap_pct}%")
        col2.metric("Cat 9 Only %", f"{cat_9_only_pct}%")
        col3.metric("High Need (8-9+RAAP) %", f"{int(((cat_9_raap_pct + cat_9_only_pct) / 100 * total_students) / total_students * 100 if total_students > 0 else 0)}%")
    
    elif section == "Cohort Analysis":
        st.markdown("## Cohort Deep Dive Analysis")
        st.markdown("Detailed breakdown by program, year level, and partnerships - identify patterns and opportunities")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Program Deep Dive", "Year Level Deep Dive", "Partnership Analysis"])
        
        # === TAB 1: PROGRAM DEEP DIVE ===
        with tab1:
            st.markdown("### Program Deep Dive")
            st.markdown("Comprehensive analysis of each program (JP, PY, SY)")
            
            programs = sorted([p for p in filtered['program_clean'].unique() if p != '' and p != ':2' and pd.notna(p)])
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Program comparison - bar chart
                prog_data = filtered['program_clean'].value_counts().reset_index()
                prog_data.columns = ['program', 'count']
                prog_data['count'] = prog_data['count'].astype(int)
                prog_data = prog_data.sort_values('count', ascending=False)
                
                fig_prog_comp = px.bar(
                    prog_data,
                    x='program',
                    y='count',
                    text='count',
                    color='program',
                    title='Student Count by Program',
                    labels={'program': '', 'count': 'Students'}
                )
                fig_prog_comp.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                st.plotly_chart(update_chart_layout(fig_prog_comp), use_container_width=True)
            
            with col2:
                st.markdown("**Program Summary**")
                for idx, row in prog_data.iterrows():
                    st.write(f"**{row['program']}**: {row['count']} students")
            
            st.markdown("---")
            
            # Deep dive by each program
            for prog in programs:
                prog_filtered = filtered[filtered['program_clean'] == prog]
                
                if len(prog_filtered) > 0:
                    st.markdown(f"#### {prog} Program Details")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric(f"{prog} Total", int(len(prog_filtered)))
                    col2.metric(f"Year Levels", int(prog_filtered['year_level'].nunique()))
                    col3.metric(f"Partnerships", int(prog_filtered['partnership_area'].nunique()))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Year level distribution
                        year_dist = prog_filtered['year_level'].value_counts().sort_index().reset_index()
                        year_dist.columns = ['year_level', 'count']
                        year_dist['count'] = year_dist['count'].astype(int)
                        
                        fig_year = px.bar(
                            year_dist,
                            x='year_level',
                            y='count',
                            text='count',
                            color_discrete_sequence=['#00e5ff'],
                            title=f'{prog} by Year Level',
                            labels={'year_level': '', 'count': 'Count'}
                        )
                        fig_year.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                        st.plotly_chart(update_chart_layout(fig_year), use_container_width=True)
                    
                    with col2:
                        # Top partnerships
                        part_dist = prog_filtered['partnership_area'].value_counts().head(8).reset_index()
                        part_dist.columns = ['partnership_area', 'count']
                        part_dist['count'] = part_dist['count'].astype(int)
                        
                        fig_part = px.bar(
                            part_dist,
                            y='partnership_area',
                            x='count',
                            orientation='h',
                            text='count',
                            color_discrete_sequence=['#ffc107'],
                            title=f'{prog} Top Partnerships',
                            labels={'partnership_area': '', 'count': 'Count'}
                        )
                        fig_part.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                        st.plotly_chart(update_chart_layout(fig_part), use_container_width=True)
                    
                    st.markdown("---")
        
        # === TAB 2: YEAR LEVEL DEEP DIVE ===
        with tab2:
            st.markdown("### Year Level Deep Dive")
            st.markdown("Student distribution and characteristics by year level (R through 10)")
            
            year_order = ['R', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
            year_levels = [y for y in year_order if y in filtered['year_level'].unique()]
            
            # Year level overview
            year_summary = filtered['year_level'].value_counts().reindex(year_levels, fill_value=0).reset_index()
            year_summary.columns = ['year_level', 'count']
            year_summary['count'] = year_summary['count'].astype(int)
            
            fig_year_overview = px.bar(
                year_summary,
                x='year_level',
                y='count',
                text='count',
                color='count',
                color_continuous_scale='Viridis',
                title='Student Distribution by Year Level',
                labels={'year_level': 'Year Level', 'count': 'Students'}
            )
            fig_year_overview.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
            st.plotly_chart(update_chart_layout(fig_year_overview), use_container_width=True)
            
            st.markdown("---")
            
            # Deep dive by year level
            for year in year_levels:
                year_filtered = filtered[filtered['year_level'] == year]
                
                if len(year_filtered) > 0:
                    st.markdown(f"#### Year Level {year}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric(f"Year {year} Students", int(len(year_filtered)))
                    col2.metric("Programs", int(year_filtered['program'].nunique()))
                    col3.metric("Partnerships", int(year_filtered['partnership_area'].nunique()))
                    
                    # Average risk score for this year level
                    risk_score = 0
                    if 'total_previous_placements' in year_filtered.columns:
                        risk_score += (pd.to_numeric(year_filtered['total_previous_placements'], errors='coerce').fillna(0) > 0).sum()
                    if 'bespoke_placement' in year_filtered.columns:
                        risk_score += (year_filtered['bespoke_placement'] == 'Yes').sum()
                    
                    col4.metric("Risk Indicators", int(risk_score))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Programs for this year
                        prog_dist = year_filtered['program'].value_counts().reset_index()
                        prog_dist.columns = ['program', 'count']
                        prog_dist['count'] = prog_dist['count'].astype(int)
                        
                        fig_prog_year = px.pie(
                            prog_dist,
                            values='count',
                            names='program',
                            title=f'Year {year} - Programs',
                            color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#ffd93d']
                        )
                        st.plotly_chart(update_chart_layout(fig_prog_year), use_container_width=True)
                    
                    with col2:
                        # Top partnerships
                        part_year = year_filtered['partnership_area'].value_counts().head(6).reset_index()
                        part_year.columns = ['partnership', 'count']
                        part_year['count'] = part_year['count'].astype(int)
                        
                        fig_part_year = px.bar(
                            part_year,
                            y='partnership',
                            x='count',
                            orientation='h',
                            text='count',
                            color_discrete_sequence=['#a8e6cf'],
                            title=f'Year {year} - Top Partnerships',
                            labels={'partnership': '', 'count': 'Count'}
                        )
                        fig_part_year.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                        st.plotly_chart(update_chart_layout(fig_part_year), use_container_width=True)
                    
                    st.markdown("---")
        
        # === TAB 3: PARTNERSHIP ANALYSIS ===
        with tab3:
            st.markdown("### Partnership Effectiveness")
            st.markdown("Student volume and distribution across partnerships")
            
            # Overall partnership ranking
            part_summary = filtered['partnership_area'].value_counts().head(15).reset_index()
            part_summary.columns = ['partnership', 'count']
            part_summary['count'] = part_summary['count'].astype(int)
            
            fig_part_ranking = px.bar(
                part_summary,
                y='partnership',
                x='count',
                orientation='h',
                text='count',
                color='count',
                color_continuous_scale='Reds',
                title='Top 15 Partnerships by Student Volume',
                labels={'partnership': '', 'count': 'Students'}
            )
            fig_part_ranking.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
            fig_part_ranking.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(update_chart_layout(fig_part_ranking), use_container_width=True)
            
            st.markdown("---")
            st.markdown("### Partnership × Program Matrix")
            st.markdown("How many students in each program are placed with each partnership")
            
            # Create matrix
            if 'partnership_area' in filtered.columns and 'program' in filtered.columns:
                part_prog_matrix = pd.crosstab(
                    filtered['partnership_area'],
                    filtered['program']
                )
                
                # Keep top 12 partnerships
                top_parts = part_prog_matrix.sum(axis=1).nlargest(12).index
                part_prog_matrix = part_prog_matrix.loc[top_parts]
                
                fig_matrix = px.imshow(
                    part_prog_matrix,
                    text_auto=True,
                    color_continuous_scale='YlOrRd',
                    title='Partnership × Program Distribution',
                    labels={'x': 'Program', 'y': 'Partnership', 'color': 'Students'}
                )
                fig_matrix.update_traces(text=part_prog_matrix.values, texttemplate='%{text}')
                st.plotly_chart(update_chart_layout(fig_matrix), use_container_width=True)
            
            st.markdown("---")
            st.markdown("### Partnership Insights")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Partnerships", int(filtered['partnership_area'].nunique()))
            with col2:
                largest_part = filtered['partnership_area'].value_counts().index[0]
                largest_count = filtered['partnership_area'].value_counts().values[0]
                st.metric("Largest Partnership", f"{largest_part} ({largest_count})")
            with col3:
                st.metric("Avg Students/Partnership", int(len(filtered) / filtered['partnership_area'].nunique()))
    




    elif section == "Equity":
        st.markdown("## Equity Deep Dive Analysis")
        st.markdown("Separate analysis of ATSI, EALD, and DCP cohorts with school socioeconomic context")
        
        equity_df = filtered.copy()
        
        # Use flag data from session state, cached data, or show instructions
        flag_df_to_use = None
        
        if 'flag_df' in st.session_state and st.session_state.flag_df is not None:
            flag_df_to_use = st.session_state.flag_df
            st.info("✅ Using flag data from sidebar upload")
        elif cached_flag_df is not None:
            flag_df_to_use = cached_flag_df
            st.info("✅ Using cached flag data")
        else:
            st.warning("📌 **Upload flag data in the sidebar** under 'Flag Data Upload' to see equity analysis")
        
        # Merge flags with filtered data
        if flag_df_to_use is not None and len(flag_df_to_use) > 0:
            equity_df['name_match'] = equity_df['student_name'].str.strip().str.lower()
            equity_df = equity_df.merge(flag_df_to_use, on='name_match', how='left')
            equity_df = equity_df.drop('name_match', axis=1)
        
        # Standardize flag values
        def standardize_flag(val):
            if pd.isna(val):
                return 'No'
            return 'Yes' if str(val).upper() == 'YES' else 'No'
        
        # Standardize flag columns
        if 'Flag_ATSI' in equity_df.columns:
            equity_df['Flag_ATSI'] = equity_df['Flag_ATSI'].apply(standardize_flag)
        if 'Flag_EALD' in equity_df.columns:
            equity_df['Flag_EALD'] = equity_df['Flag_EALD'].apply(standardize_flag)
        if 'Flag_DCP_involvement' in equity_df.columns:
            equity_df['Flag_DCP'] = equity_df['Flag_DCP_involvement'].apply(standardize_flag)
        
        # School SES data
        school_ses_data = {
            'Le Fevre High School': {'SEIFA_IRSAD': 850, 'Disadvantage_Level': 'Very High'},
            'Largs Bay Primary School': {'SEIFA_IRSAD': 860, 'Disadvantage_Level': 'Very High'},
            'Ocean View College': {'SEIFA_IRSAD': 880, 'Disadvantage_Level': 'High'},
            'Woodville High School': {'SEIFA_IRSAD': 890, 'Disadvantage_Level': 'High'},
            'Adelaide High School': {'SEIFA_IRSAD': 900, 'Disadvantage_Level': 'Medium'},
            'Elizabeth High School': {'SEIFA_IRSAD': 820, 'Disadvantage_Level': 'Very High'},
            'Port Adelaide High School': {'SEIFA_IRSAD': 840, 'Disadvantage_Level': 'Very High'},
            'Brighton Primary School': {'SEIFA_IRSAD': 950, 'Disadvantage_Level': 'Low'},
            'Glenelg High School': {'SEIFA_IRSAD': 930, 'Disadvantage_Level': 'Low'},
        }
        
        tab_atsi, tab_eald, tab_dcp = st.tabs(["🇦🇺 ATSI Deep Dive", "🗣️ EALD Deep Dive", "🌏 DCP Deep Dive"])
        
        # === ATSI ===
        with tab_atsi:
            st.markdown("### Aboriginal & Torres Strait Islander Students")
            if 'Flag_ATSI' not in equity_df.columns:
                st.warning("Flag_ATSI column not found in data")
                atsi_df = pd.DataFrame()
            else:
                atsi_df = equity_df[equity_df['Flag_ATSI'] == 'Yes']
            
            if len(atsi_df) > 0:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total ATSI", len(atsi_df))
                multi_need = ((atsi_df['Flag_EALD'] == 'Yes') | (atsi_df['Flag_DCP'] == 'Yes')).sum()
                c2.metric("With 1+ Need", multi_need)
                c3.metric("ATSI + EALD", (atsi_df['Flag_EALD'] == 'Yes').sum())
                c4.metric("ATSI + DCP", (atsi_df['Flag_DCP'] == 'Yes').sum())
                
                st.markdown("---")
                if 'term_clean' in atsi_df.columns and len(atsi_df['term_clean'].dropna()) > 0:
                    by_term = atsi_df[atsi_df['term_clean'] >= 1]['term_clean'].value_counts().sort_index()
                    if len(by_term) > 0:
                        term_df = pd.DataFrame({'Term': by_term.index, 'Count': by_term.values})
                        fig = px.bar(term_df, x='Term', y='Count', title='ATSI Students by Term',
                                     color_discrete_sequence=['#8B4513'])
                        fig.update_traces(textposition='outside', text=term_df['Count'].values, textfont=dict(color='#ffffff'))
                        fig.update_xaxes(type='category', categoryorder='array', categoryarray=[1, 2, 3, 4])
                        st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                if 'school' in atsi_df.columns:
                    school_counts = atsi_df['school'].value_counts().head(10)
                    school_data = pd.DataFrame({'School': school_counts.index, 'Count': school_counts.values})
                    school_data['SES'] = school_data['School'].apply(lambda x: school_ses_data.get(x, {}).get('Disadvantage_Level', 'Unknown'))
                    
                    fig = px.bar(school_data, y='School', x='Count', orientation='h', text='Count', color='SES',
                        color_discrete_map={'Very High': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50', 'Unknown': '#999'},
                        title='Top Schools (ATSI Referrals)')
                    fig.update_yaxes(categoryorder='total ascending')
                    fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                if 'partnership_area' in atsi_df.columns:
                    part_counts = atsi_df['partnership_area'].value_counts().head(8)
                    fig = px.bar(part_counts, title='Top Partnerships (ATSI)',
                        color_discrete_sequence=['#8B4513'], labels={'value': 'Students'})
                    fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                multi_atsi = atsi_df[(atsi_df['Flag_EALD'] == 'Yes') & (atsi_df['Flag_DCP'] == 'Yes')]
                if len(multi_atsi) > 0:
                    cols_show = ['program', 'year_level', 'school', 'partnership_area']
                    cols_show = [c for c in cols_show if c in multi_atsi.columns]
                    st.markdown("#### ATSI with BOTH EALD + DCP")
                    st.write(f"**{len(multi_atsi)} students** with this combination (student names hidden for privacy)")
                    st.dataframe(multi_atsi[cols_show], use_container_width=True, hide_index=True)
                else:
                    st.info("No ATSI students with both EALD + DCP")
            else:
                st.info("No ATSI students in current filters")
        
        # === EALD ===
        with tab_eald:
            st.markdown("### English as Additional Language (EALD) Students")
            if 'Flag_EALD' not in equity_df.columns:
                st.warning("Flag_EALD column not found in data")
                eald_df = pd.DataFrame()
            else:
                eald_df = equity_df[equity_df['Flag_EALD'] == 'Yes']
            
            if len(eald_df) > 0:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total EALD", len(eald_df))
                multi_need = ((eald_df['Flag_ATSI'] == 'Yes') | (eald_df['Flag_DCP'] == 'Yes')).sum()
                c2.metric("With 1+ Need", multi_need)
                c3.metric("EALD + ATSI", (eald_df['Flag_ATSI'] == 'Yes').sum())
                c4.metric("EALD + DCP", (eald_df['Flag_DCP'] == 'Yes').sum())
                
                st.markdown("---")
                if 'term_clean' in eald_df.columns and len(eald_df['term_clean'].dropna()) > 0:
                    by_term = eald_df[eald_df['term_clean'] >= 1]['term_clean'].value_counts().sort_index()
                    if len(by_term) > 0:
                        term_df = pd.DataFrame({'Term': by_term.index, 'Count': by_term.values})
                        fig = px.bar(term_df, x='Term', y='Count', title='EALD Students by Term',
                                     color_discrete_sequence=['#20B2AA'])
                        fig.update_traces(textposition='outside', text=term_df['Count'].values, textfont=dict(color='#ffffff'))
                        fig.update_xaxes(type='category', categoryorder='array', categoryarray=[1, 2, 3, 4])
                        st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                if 'school' in eald_df.columns:
                    school_counts = eald_df['school'].value_counts().head(10)
                    school_data = pd.DataFrame({'School': school_counts.index, 'Count': school_counts.values})
                    school_data['SES'] = school_data['School'].apply(lambda x: school_ses_data.get(x, {}).get('Disadvantage_Level', 'Unknown'))
                    
                    fig = px.bar(school_data, y='School', x='Count', orientation='h', text='Count', color='SES',
                        color_discrete_map={'Very High': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50', 'Unknown': '#999'},
                        title='Top Schools (EALD Referrals)')
                    fig.update_yaxes(categoryorder='total ascending')
                    fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                if 'partnership_area' in eald_df.columns:
                    part_counts = eald_df['partnership_area'].value_counts().head(8)
                    fig = px.bar(part_counts, title='Top Partnerships (EALD)',
                        color_discrete_sequence=['#20B2AA'], labels={'value': 'Students'})
                    fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                multi_eald = eald_df[(eald_df['Flag_ATSI'] == 'Yes') & (eald_df['Flag_DCP'] == 'Yes')]
                if len(multi_eald) > 0:
                    cols_show = ['program', 'year_level', 'school', 'partnership_area']
                    cols_show = [c for c in cols_show if c in multi_eald.columns]
                    st.markdown("#### EALD with BOTH ATSI + DCP")
                    st.write(f"**{len(multi_eald)} students** with this combination (student names hidden for privacy)")
                    st.dataframe(multi_eald[cols_show], use_container_width=True, hide_index=True)
                else:
                    st.info("No EALD students with both ATSI + DCP")
            else:
                st.info("No EALD students in current filters")
        
        # === DCP ===
        with tab_dcp:
            st.markdown("### Diverse Cultural & Linguistic Background (DCP) Students")
            if 'Flag_DCP' not in equity_df.columns:
                st.warning("Flag_DCP column not found in data")
                dcp_df = pd.DataFrame()
            else:
                dcp_df = equity_df[equity_df['Flag_DCP'] == 'Yes']
            
            if len(dcp_df) > 0:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total DCP", len(dcp_df))
                multi_need = ((dcp_df['Flag_ATSI'] == 'Yes') | (dcp_df['Flag_EALD'] == 'Yes')).sum()
                c2.metric("With 1+ Need", multi_need)
                c3.metric("DCP + ATSI", (dcp_df['Flag_ATSI'] == 'Yes').sum())
                c4.metric("DCP + EALD", (dcp_df['Flag_EALD'] == 'Yes').sum())
                
                st.markdown("---")
                if 'term_clean' in dcp_df.columns and len(dcp_df['term_clean'].dropna()) > 0:
                    by_term = dcp_df[dcp_df['term_clean'] >= 1]['term_clean'].value_counts().sort_index()
                    if len(by_term) > 0:
                        term_df = pd.DataFrame({'Term': by_term.index, 'Count': by_term.values})
                        fig = px.bar(term_df, x='Term', y='Count', title='DCP Students by Term',
                                     color_discrete_sequence=['#9370DB'])
                        fig.update_traces(textposition='outside', text=term_df['Count'].values, textfont=dict(color='#ffffff'))
                        fig.update_xaxes(type='category', categoryorder='array', categoryarray=[1, 2, 3, 4])
                        st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                if 'school' in dcp_df.columns:
                    school_counts = dcp_df['school'].value_counts().head(10)
                    school_data = pd.DataFrame({'School': school_counts.index, 'Count': school_counts.values})
                    school_data['SES'] = school_data['School'].apply(lambda x: school_ses_data.get(x, {}).get('Disadvantage_Level', 'Unknown'))
                    
                    fig = px.bar(school_data, y='School', x='Count', orientation='h', text='Count', color='SES',
                        color_discrete_map={'Very High': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50', 'Unknown': '#999'},
                        title='Top Schools (DCP Referrals)')
                    fig.update_yaxes(categoryorder='total ascending')
                    fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                if 'partnership_area' in dcp_df.columns:
                    part_counts = dcp_df['partnership_area'].value_counts().head(8)
                    fig = px.bar(part_counts, title='Top Partnerships (DCP)',
                        color_discrete_sequence=['#9370DB'], labels={'value': 'Students'})
                    fig.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                
                st.markdown("---")
                multi_dcp = dcp_df[(dcp_df['Flag_ATSI'] == 'Yes') & (dcp_df['Flag_EALD'] == 'Yes')]
                if len(multi_dcp) > 0:
                    cols_show = ['program', 'year_level', 'school', 'partnership_area']
                    cols_show = [c for c in cols_show if c in multi_dcp.columns]
                    st.markdown("#### DCP with BOTH ATSI + EALD")
                    st.write(f"**{len(multi_dcp)} students** with this combination (student names hidden for privacy)")
                    st.dataframe(multi_dcp[cols_show], use_container_width=True, hide_index=True)
                else:
                    st.info("No DCP students with both ATSI + EALD")
            else:
                st.info("No DCP students in current filters")

    elif section == "Critical Incidents":
        st.markdown("## Critical Incidents Tracking")
        st.markdown("Track and analyze critical incidents by program, year level, and term - identify support patterns and resource needs")
        
        # Check if incidents data is available
        if 'incidents_df' not in st.session_state or st.session_state.incidents_df is None:
            st.warning("⚠️ No critical incidents data loaded. To add incidents:")
            st.info("""
            1. Add a **"Critical_Incidents"** sheet to your Excel file with columns:
               - Student_Name, Incident_Date, Incident_Type, Severity
               - Term, Year, Program, Year_Level, Partnership_Area
               - Action_Taken, Actioned_By, Notes
            2. Upload the Excel file through the sidebar
            3. Incidents will appear here automatically
            """)
        else:
            incidents = st.session_state.incidents_df.copy()
            
            # Add refresh button
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("🔄 Refresh"):
                    st.rerun()
            
            with col1:
                st.info(f"📌 Total incidents recorded: {len(incidents)}")
            
            # Filter by current year/term
            if 'Year' in incidents.columns:
                incidents['Year'] = pd.to_numeric(incidents['Year'], errors='coerce')
                if selected_year != 'All':
                    incidents = incidents[incidents['Year'] == selected_year]
            
            if 'Term' in incidents.columns:
                incidents['Term'] = pd.to_numeric(incidents['Term'], errors='coerce')
                if selected_term != 'All':
                    incidents = incidents[incidents['Term'] == selected_term]
            
            if len(incidents) == 0:
                st.success("✅ No incidents in current filters")
            else:
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Incidents", len(incidents))
                
                # Severity counts
                if 'Severity' in incidents.columns:
                    critical_count = (incidents['Severity'] == 'Critical').sum()
                    col2.metric("Critical", int(critical_count))
                
                # Incident type count
                if 'Incident_Type' in incidents.columns:
                    col3.metric("Incident Types", incidents['Incident_Type'].nunique())
                
                # Programs affected
                if 'Program' in incidents.columns:
                    col4.metric("Programs Affected", incidents['Program'].nunique())
                
                st.markdown("---")
                
                # Incident Type Breakdown
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'Incident_Type' in incidents.columns:
                        type_counts = incidents['Incident_Type'].value_counts()
                        fig_type = px.bar(
                            x=type_counts.index,
                            y=type_counts.values,
                            title="Incidents by Type",
                            labels={'x': 'Type', 'y': 'Count'}
                        )
                        fig_type.update_traces(marker_color='#ff7675')
                        st.plotly_chart(update_chart_layout(fig_type), use_container_width=True)
                
                with col2:
                    if 'Severity' in incidents.columns:
                        severity_order = ['Critical', 'High', 'Medium', 'Low']
                        severity_counts = incidents['Severity'].value_counts().reindex(severity_order, fill_value=0)
                        colors_severity = ['#d32f2f', '#f57c00', '#ffa726', '#fdd835']
                        
                        fig_sev = px.bar(
                            x=severity_counts.index,
                            y=severity_counts.values,
                            title="Incidents by Severity",
                            labels={'x': 'Severity', 'y': 'Count'}
                        )
                        fig_sev.update_traces(marker_color=colors_severity[:len(severity_counts)])
                        st.plotly_chart(update_chart_layout(fig_sev), use_container_width=True)
                
                st.markdown("---")
                
                # By Program
                if 'Program' in incidents.columns:
                    prog_counts = incidents['Program'].value_counts()
                    fig_prog = px.bar(
                        x=prog_counts.index,
                        y=prog_counts.values,
                        title="Incidents by Program",
                        labels={'x': 'Program', 'y': 'Count'}
                    )
                    st.plotly_chart(update_chart_layout(fig_prog), use_container_width=True)
                
                # By Year Level
                if 'Year_Level' in incidents.columns:
                    yl_counts = incidents['Year_Level'].value_counts().sort_index()
                    fig_yl = px.bar(
                        x=yl_counts.index,
                        y=yl_counts.values,
                        title="Incidents by Year Level",
                        labels={'x': 'Year Level', 'y': 'Count'}
                    )
                    st.plotly_chart(update_chart_layout(fig_yl), use_container_width=True)
                
                st.markdown("---")
                st.markdown("## Incident Details")
                
                # Show incidents table (without student names for privacy by default)
                with st.expander("📋 View all incidents"):
                    display_cols = ['Incident_Date', 'Incident_Type', 'Severity', 'Program', 'Year_Level', 'Partnership_Area']
                    display_cols = [col for col in display_cols if col in incidents.columns]
                    
                    st.dataframe(incidents[display_cols].sort_values('Incident_Date', ascending=False), 
                                use_container_width=True, hide_index=True)
                
                # High-severity incidents summary
                if 'Severity' in incidents.columns:
                    high_sev = incidents[incidents['Severity'].isin(['Critical', 'High'])]
                    if len(high_sev) > 0:
                        st.markdown("---")
                        st.markdown("⚠️ **High/Critical Incidents**")
                        st.warning(f"{len(high_sev)} high-severity incidents requiring attention")
                        
                        summary_cols = ['Incident_Date', 'Incident_Type', 'Severity', 'Program', 'Action_Taken'] if 'Action_Taken' in incidents.columns else ['Incident_Date', 'Incident_Type', 'Severity', 'Program']
                        summary_cols = [col for col in summary_cols if col in high_sev.columns]
                        
                        st.dataframe(high_sev[summary_cols], use_container_width=True, hide_index=True)

    elif section == "Assessment":
        st.markdown("## Assessment Analytics")
        st.markdown("SMARTAR Goals, Sounds Write, and Word Aware assessments")
        
        assessments = []
        try:
            if supabase:
                response = supabase.table('term_assessments').select('*').execute()
                assessments = response.data if response.data else []
        except Exception as e:
            st.error(f"Error loading: {e}")
        
        if not assessments:
            st.warning("📌 No assessment records")
        else:
            assessments_df = pd.DataFrame(assessments)
            assessments_df.columns = assessments_df.columns.str.lower()
            
            # DEBUG
            with st.expander("🔍 Debug - All Assessment Data"):
                st.write(f"**Total raw records:** {len(assessments_df)}")
                st.write(f"**Year column values:**")
                if 'year' in assessments_df.columns:
                    st.write(assessments_df['year'].unique().tolist())
                    st.write(f"**Year data types:** {assessments_df['year'].dtype}")
                
                st.write(f"**All records by year:**")
                if 'year' in assessments_df.columns:
                    year_counts = assessments_df['year'].value_counts().sort_index()
                    st.write(year_counts)
            
            # Parse year - handle both string and numeric
            if 'year' in assessments_df.columns:
                # Try to convert to numeric, handling both string and int
                assessments_df['year_str'] = assessments_df['year'].astype(str).str.strip()
                assessments_df['year_num'] = pd.to_numeric(assessments_df['year_str'], errors='coerce')
            
            # Get available years
            available_years = sorted([int(y) for y in assessments_df['year_num'].dropna().unique()])
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"**Available years: {available_years}**")
            
            with col2:
                if st.button("🔄 Refresh"):
                    st.rerun()
            
            # Filter to 2026 (or first available year if 2026 not available)
            target_year = 2026 if 2026 in available_years else (available_years[0] if available_years else None)
            
            if target_year is None:
                st.error("No valid year data found")
            else:
                filtered_assess = assessments_df[assessments_df['year_num'] == target_year].copy()
                
                st.success(f"✅ {len(filtered_assess)} records in {target_year}")
                
                if len(filtered_assess) == 0:
                    st.info(f"No assessment data for {target_year}")
                    
                    if len(available_years) > 0:
                        st.markdown("---")
                        with st.expander("📅 View assessments from other years"):
                            other_years = [y for y in available_years if y != target_year]
                            if other_years:
                                selected_other_year = st.selectbox("Select year", other_years)
                                other_data = assessments_df[assessments_df['year_num'] == selected_other_year].copy()
                                
                                if len(other_data) > 0:
                                    st.write(f"**{selected_other_year}: {len(other_data)} records**")
                                    with st.expander("View records"):
                                        cols = ['program', 'staff_member', 'term', 'date_submitted']
                                        cols = [c for c in cols if c in other_data.columns]
                                        st.dataframe(other_data[cols], use_container_width=True, hide_index=True)
                else:
                    # Create tabs
                    tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "🎯 SMARTAR Goals", "✍️ Sounds Write", "📖 Word Aware"])
                
                    with tab1:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Records", len(filtered_assess))
                        if 'program' in filtered_assess.columns:
                            c2.metric("Programs", int(filtered_assess['program'].nunique()))
                        if 'staff_member' in filtered_assess.columns:
                            c3.metric("Staff", int(filtered_assess['staff_member'].nunique()))
                        c4.metric("Year", 2026)
                        
                        st.markdown("---")
                        
                        # Summary table
                        with st.expander("📋 View all records"):
                            summary_cols = ['program', 'staff_member', 'term', 'year', 'date_submitted']
                            summary_cols = [c for c in summary_cols if c in filtered_assess.columns]
                            st.dataframe(filtered_assess[summary_cols], use_container_width=True, hide_index=True)
                
                    with tab2:
                        st.markdown("**SMARTAR Achievement Summary**")
                        
                        if 'smartar_goals' in filtered_assess.columns:
                            st.markdown("---")
                            
                            # Parse SMARTAR data - it's aggregated by category
                            total_stats = {'Reached Expected': 0, 'Above Expectation': 0, 'Exceeding': 0}
                            by_program = {}
                            
                            import json
                            records_processed = 0
                            
                            for idx, row in filtered_assess.iterrows():
                                try:
                                    data = row['smartar_goals']
                                    
                                    # Handle None/NaN/empty
                                    if pd.isna(data) or data is None or data == '' or data == '{}':
                                        continue
                                    
                                    # Data is stored as JSON string
                                    if isinstance(data, str):
                                        try:
                                            data = json.loads(data)
                                        except:
                                            continue
                                    
                                    prog = str(row.get('program', 'Unknown')).strip()
                                    if prog not in by_program:
                                        by_program[prog] = {'Reached Expected': 0, 'Above Expectation': 0, 'Exceeding': 0}
                                    
                                    # Data structure: {category: {achievement_level: count, ...}, ...}
                                    if isinstance(data, dict):
                                        for category, achievements in data.items():
                                            if isinstance(achievements, dict):
                                                for level, count in achievements.items():
                                                    count = int(count) if isinstance(count, (int, float)) else 0
                                                    if level in total_stats:
                                                        total_stats[level] += count
                                                        if level in by_program[prog]:
                                                            by_program[prog][level] += count
                                        records_processed += 1
                                except Exception as e:
                                    st.error(f"Error processing record {idx}: {str(e)}")
                            
                            st.write(f"**Records processed: {records_processed}**")
                            
                            # Show totals
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Exceeding", total_stats['Exceeding'])
                            c2.metric("Above Expectation", total_stats['Above Expectation'])
                            c3.metric("Reached Expected", total_stats['Reached Expected'])
                            
                            if sum(total_stats.values()) > 0:
                                st.markdown("---")
                                fig = px.bar(
                                    x=list(total_stats.keys()), 
                                    y=list(total_stats.values()), 
                                    title="SMARTAR Achievement Distribution",
                                    labels={'y': 'Count'}
                                )
                                fig.update_traces(marker_color=['#4CAF50', '#2196F3', '#FF9800'])
                                st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                                
                                if by_program:
                                    st.markdown("---")
                                    df = pd.DataFrame(by_program).T
                                    fig = px.bar(df, barmode='group', title="SMARTAR by Program")
                                    st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                            else:
                                st.info("No SMARTAR data found")
                        else:
                            st.info("smartar_goals column not found")
                
                    with tab3:
                        st.markdown("**Sounds Write Assessment**")
                        
                        # Check sounds_write_data column
                        if 'sounds_write_data' in filtered_assess.columns:
                            st.write("**sounds_write_data column found**")
                            
                            # Show what's in it
                            st.markdown("**Sample values:**")
                            for idx, row in filtered_assess.iterrows():
                                val = row['sounds_write_data']
                                st.write(f"Record {idx}: Type=`{type(val).__name__}`, Value=`{val}`")
                            
                            st.markdown("---")
                            
                            # Try to parse
                            sw_totals = {}
                            import json
                            processed = 0
                            
                            for idx, row in filtered_assess.iterrows():
                                try:
                                    data = row['sounds_write_data']
                                    
                                    if pd.isna(data) or data is None:
                                        continue
                                    
                                    if isinstance(data, str) and data.strip():
                                        try:
                                            data = json.loads(data)
                                        except:
                                            st.write(f"Could not parse JSON in record {idx}")
                                            continue
                                    
                                    if isinstance(data, dict):
                                        processed += 1
                                        for skill, levels in data.items():
                                            if skill not in sw_totals:
                                                sw_totals[skill] = {}
                                            if isinstance(levels, dict):
                                                for level, count in levels.items():
                                                    count = int(count) if isinstance(count, (int, float)) else 0
                                                    sw_totals[skill][level] = sw_totals[skill].get(level, 0) + count
                                except Exception as e:
                                    st.write(f"Error processing record {idx}: {e}")
                            
                            st.write(f"**Records processed: {processed}**")
                            
                            if sw_totals:
                                df = pd.DataFrame(sw_totals).T
                                st.dataframe(df, use_container_width=True)
                                st.markdown("---")
                                fig = px.bar(df, barmode='stack', title="Sounds Write by Skill")
                                st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                            else:
                                st.info("No Sounds Write data found")
                        else:
                            st.info("No sounds_write_data column found")
                    
                    with tab4:
                        st.markdown("**Word Aware Assessment**")
                        
                        # Check word_aware_data column
                        if 'word_aware_data' in filtered_assess.columns:
                            st.write("**word_aware_data column found**")
                            
                            # Show what's in it
                            st.markdown("**Sample values:**")
                            for idx, row in filtered_assess.iterrows():
                                val = row['word_aware_data']
                                st.write(f"Record {idx}: Type=`{type(val).__name__}`, Value=`{val}`")
                            
                            st.markdown("---")
                            
                            # Try to parse
                            wa_totals = {}
                            import json
                            processed = 0
                            
                            for idx, row in filtered_assess.iterrows():
                                try:
                                    data = row['word_aware_data']
                                    
                                    if pd.isna(data) or data is None:
                                        continue
                                    
                                    if isinstance(data, str) and data.strip():
                                        try:
                                            data = json.loads(data)
                                        except:
                                            st.write(f"Could not parse JSON in record {idx}")
                                            continue
                                    
                                    if isinstance(data, dict):
                                        processed += 1
                                        for skill, levels in data.items():
                                            if skill not in wa_totals:
                                                wa_totals[skill] = {}
                                            if isinstance(levels, dict):
                                                for level, count in levels.items():
                                                    count = int(count) if isinstance(count, (int, float)) else 0
                                                    wa_totals[skill][level] = wa_totals[skill].get(level, 0) + count
                                except Exception as e:
                                    st.write(f"Error processing record {idx}: {e}")
                            
                            st.write(f"**Records processed: {processed}**")
                            
                            if wa_totals:
                                df = pd.DataFrame(wa_totals).T
                                st.dataframe(df, use_container_width=True)
                                st.markdown("---")
                                fig = px.bar(df, barmode='stack', title="Word Aware by Skill")
                                st.plotly_chart(update_chart_layout(fig), use_container_width=True)
                            else:
                                st.info("No Word Aware data found")
                        else:
                            st.info("No word_aware_data column found")
