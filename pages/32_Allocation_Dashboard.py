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

st.markdown("""
<style>
    /* HIDE ALL STREAMLIT UI ELEMENTS */
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
    .stToolbar { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    
    /* HIDE WHITE BANDS */
    [data-testid="stAppViewContainer"] > div { background: #0a0e27 !important; }
    .block-container { background: #0a0e27 !important; }
    section { background: #0a0e27 !important; }
    
    html, body { 
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    * { color: #ffffff !important; }
    
    h1, h2, h3, h4, h5, h6 { color: #00e5ff !important; text-shadow: 0 0 15px rgba(0,229,255,0.3); }
    p, span, div, label, button, a { color: #ffffff !important; }
    
    /* SIDEBAR - MODERN GRADIENT WITH BETTER STYLING */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #050810 0%, #0a1020 100%) !important; 
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
            ["Overview", "Trends", "Complexity", "Risk Assessment", "Cohort Analysis", "Equity", "Waitlist", "Diagnostics"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("**Data Upload**", help="Upload new student allocation data")
        
        uploaded_file = st.file_uploader("Choose Excel or CSV file", type=['xlsx', 'csv'], label_visibility="collapsed")
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                
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
                
                st.success(f"Ready: {len(df_mapped)} rows")
                
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
    
    # TOP TITLE
    st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #00e5ff; font-size: 36px; margin: 0;'>Student Allocation</h1>
        <p style='color: #888; font-size: 14px; margin: 10px 0 0 0;'>Comprehensive enrollment analytics and equity insights</p>
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
        selected_year = st.selectbox("Year", year_options)
    
    with col2:
        # Filter terms by selected year (or show all if "All" selected)
        if selected_year == 'All':
            year_data = allocation_df
        else:
            year_data = allocation_df[allocation_df['year_clean'] == selected_year]
        
        year_data['term_clean'] = pd.to_numeric(year_data['term'], errors='coerce')
        terms = sorted([int(t) for t in year_data['term_clean'].dropna().unique() if t >= 1])
        if not terms:
            terms = [1]
        term_options = ['All'] + terms
        selected_term = st.selectbox("Term", term_options)
    
    with col3:
        progs = ['All'] + sorted([p for p in allocation_df['program'].dropna().unique() if p != '' and p != ':2'])
        selected_program = st.selectbox("Program", progs)
    
    # FILTER DATA - handle "All" selections
    allocation_df['year_clean'] = pd.to_numeric(allocation_df['year'], errors='coerce')
    allocation_df['term_clean'] = pd.to_numeric(allocation_df['term'], errors='coerce')
    
    filtered = allocation_df.copy()
    
    # Apply year filter
    if selected_year != 'All':
        filtered = filtered[filtered['year_clean'] == selected_year]
    
    # Apply term filter
    if selected_term != 'All':
        filtered = filtered[filtered['term_clean'] == selected_term]
    
    # Apply program filter
    if selected_program != 'All':
        filtered = filtered[filtered['program'] == selected_program]
    
    st.info(f"**{len(filtered)} active students** | Year {selected_year if selected_year != 'All' else 'All'} | Term {selected_term if selected_term != 'All' else 'All'} | {selected_program}")
    st.markdown("---")
    
    # CONTENT BY SECTION
    if section == "Overview":
        st.markdown("## Overview")
        st.markdown("High-level snapshot of current enrollment and placement patterns")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Students", int(len(filtered)))
        col2.metric("Programs", int(filtered['program'].nunique()))
        col3.metric("Year Levels", int(filtered['year_level'].nunique()))
        col4.metric("Updated", datetime.now().strftime("%d/%m/%y"))
        
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
    
    elif section == "Risk Assessment":
        st.markdown("## Funding & Support Category Analysis")
        st.markdown("Student distribution by funding category (Cat 1-9 + RAAP) - identifies support needs and resource allocation")
        
        # Extract funding category for each student
        risk_df = filtered.copy()
        risk_df['funding_category'] = 'None'
        risk_df['is_raap'] = 'No'
        
        # Check for RAAP
        if 'Flag_9plus_sRAAP' in risk_df.columns:
            risk_df.loc[risk_df['Flag_9plus_sRAAP'] == 'Yes', 'is_raap'] = 'Yes (RAAP)'
        
        # Determine funding category (highest category takes precedence)
        for cat in range(9, 0, -1):
            col_name = f'Funding_Category_{cat}'
            if col_name in risk_df.columns:
                risk_df.loc[risk_df[col_name] == 'Yes', 'funding_category'] = f'Cat {cat}'
        
        # SUMMARY METRICS
        col1, col2, col3, col4 = st.columns(4)
        
        cat_counts = risk_df['funding_category'].value_counts()
        col1.metric("Cat 9 (Highest)", int(cat_counts.get('Cat 9', 0)))
        col2.metric("Cat 5-8", int(sum(cat_counts.get(f'Cat {i}', 0) for i in range(5, 9))))
        col3.metric("Cat 1-4", int(sum(cat_counts.get(f'Cat {i}', 0) for i in range(1, 5))))
        col4.metric("RAAP", int((risk_df['is_raap'] == 'Yes (RAAP)').sum()))
        
        st.markdown("---")
        st.markdown("## Funding Category Distribution")
        st.markdown("How many students are in each funding category")
        
        col1, col2 = st.columns(2)
        
        with col1:
            funding_summary = risk_df['funding_category'].value_counts().reset_index()
            funding_summary.columns = ['category', 'count']
            funding_summary['count'] = funding_summary['count'].astype(int)
            # Sort by category number
            funding_summary['sort_key'] = funding_summary['category'].str.extract(r'(\d+)').astype(int)
            funding_summary = funding_summary.sort_values('sort_key', ascending=False)
            
            fig_funding = px.bar(
                funding_summary,
                x='category',
                y='count',
                text='count',
                color='sort_key',
                color_continuous_scale='Reds',
                title='Students by Funding Category',
                labels={'category': 'Category', 'count': 'Students'}
            )
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
            
            # Reorder columns (highest funding first)
            cat_order = [f'Cat {i}' for i in range(9, 0, -1)] + ['None']
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
            st.plotly_chart(update_chart_layout(fig_matrix), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## High-Need Students (Cat 8-9)")
        st.markdown("Students requiring intensive support and resources")
        
        high_need = risk_df[risk_df['funding_category'].isin(['Cat 9', 'Cat 8'])].copy()
        
        if len(high_need) > 0:
            display_cols = ['student_name', 'program', 'year_level', 'funding_category', 'partnership_area']
            display_cols = [col for col in display_cols if col in high_need.columns]
            
            high_need_display = high_need[display_cols].copy().sort_values('funding_category')
            
            st.dataframe(high_need_display, use_container_width=True, hide_index=True)
            st.info(f"**{len(high_need)} students** in Cat 8-9 (highest support needs)")
        else:
            st.success("✅ No Cat 8-9 students in current selection")
        
        st.markdown("---")
        st.markdown("## Resource Allocation Summary")
        
        col1, col2, col3 = st.columns(3)
        
        total_students = len(risk_df)
        cat_9_pct = int((risk_df['funding_category'] == 'Cat 9').sum() / total_students * 100) if total_students > 0 else 0
        raap_pct = int((risk_df['is_raap'] == 'Yes (RAAP)').sum() / total_students * 100) if total_students > 0 else 0
        
        col1.metric("Cat 9 %", f"{cat_9_pct}%")
        col2.metric("RAAP %", f"{raap_pct}%")
        col3.metric("High Need (8-9) %", f"{int((len(high_need) / total_students * 100) if total_students > 0 else 0)}%")
    
    elif section == "Cohort Analysis":
        st.markdown("## Cohort Deep Dive Analysis")
        st.markdown("Detailed breakdown by program, year level, and partnerships - identify patterns and opportunities")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Program Deep Dive", "Year Level Deep Dive", "Partnership Analysis"])
        
        # === TAB 1: PROGRAM DEEP DIVE ===
        with tab1:
            st.markdown("### Program Deep Dive")
            st.markdown("Comprehensive analysis of each program (JP, PY, SY)")
            
            programs = sorted([p for p in filtered['program'].unique() if p != '' and p != ':2'])
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Program comparison - bar chart
                prog_data = filtered['program'].value_counts().reset_index()
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
                prog_filtered = filtered[filtered['program'] == prog]
                
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
        
        # Load school SES data (master database)
        school_ses_data = {
            'Le Fevre High School': {'SEIFA_IRSAD': 850, 'Disadvantage_Level': 'Very High', 'Indigenous_Percent': 18, 'EALD_Percent': 22},
            'Largs Bay Primary School': {'SEIFA_IRSAD': 860, 'Disadvantage_Level': 'Very High', 'Indigenous_Percent': 16, 'EALD_Percent': 20},
            'Ocean View College': {'SEIFA_IRSAD': 880, 'Disadvantage_Level': 'High', 'Indigenous_Percent': 12, 'EALD_Percent': 18},
            'Woodville High School': {'SEIFA_IRSAD': 890, 'Disadvantage_Level': 'High', 'Indigenous_Percent': 8, 'EALD_Percent': 15},
            'Adelaide High School': {'SEIFA_IRSAD': 900, 'Disadvantage_Level': 'Medium', 'Indigenous_Percent': 7, 'EALD_Percent': 14},
            'Elizabeth High School': {'SEIFA_IRSAD': 820, 'Disadvantage_Level': 'Very High', 'Indigenous_Percent': 15, 'EALD_Percent': 25},
            'Port Adelaide High School': {'SEIFA_IRSAD': 840, 'Disadvantage_Level': 'Very High', 'Indigenous_Percent': 20, 'EALD_Percent': 28},
            'Brighton Primary School': {'SEIFA_IRSAD': 950, 'Disadvantage_Level': 'Low', 'Indigenous_Percent': 4, 'EALD_Percent': 8},
            'Glenelg High School': {'SEIFA_IRSAD': 930, 'Disadvantage_Level': 'Low', 'Indigenous_Percent': 3, 'EALD_Percent': 7},
        }
        
        # Create tabs for each cohort
        tab_atsi, tab_eald, tab_dcp = st.tabs(["ATSI Deep Dive", "EALD Deep Dive", "DCP Deep Dive"])
        
        # === TAB 1: ATSI ===
        with tab_atsi:
            st.markdown("### Aboriginal & Torres Strait Islander (ATSI) Students")
            
            atsi_students = filtered[filtered['Flag_ATSI'] == 'Yes'].copy() if 'Flag_ATSI' in filtered.columns else pd.DataFrame()
            
            if len(atsi_students) > 0:
                atsi_students['intersecting_needs'] = 0
                
                if 'Flag_EALD' in atsi_students.columns:
                    atsi_students.loc[atsi_students['Flag_EALD'] == 'Yes', 'intersecting_needs'] += 1
                if 'Flag_DCP' in atsi_students.columns:
                    atsi_students.loc[atsi_students['Flag_DCP'] == 'Yes', 'intersecting_needs'] += 1
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("ATSI Total", int(len(atsi_students)))
                col2.metric("With 1+ Additional Need", int((atsi_students['intersecting_needs'] > 0).sum()))
                col3.metric("ATSI + EALD", int(((atsi_students['Flag_EALD'] == 'Yes') if 'Flag_EALD' in atsi_students.columns else False).sum()))
                col4.metric("ATSI + DCP", int(((atsi_students['Flag_DCP'] == 'Yes') if 'Flag_DCP' in atsi_students.columns else False).sum()))
                
                st.markdown("---")
                st.markdown("#### ATSI Students by Term")
                
                if 'term_clean' in atsi_students.columns:
                    atsi_by_term = atsi_students['term_clean'].value_counts().sort_index().reset_index()
                    atsi_by_term.columns = ['term', 'count']
                    atsi_by_term['count'] = atsi_by_term['count'].astype(int)
                    atsi_by_term['Term'] = 'T' + atsi_by_term['term'].astype(int).astype(str)
                    
                    fig_atsi_term = px.bar(
                        atsi_by_term,
                        x='Term',
                        y='count',
                        text='count',
                        color_discrete_sequence=['#8B4513'],
                        title='ATSI Students per Term',
                        labels={'Term': '', 'count': 'Students'}
                    )
                    fig_atsi_term.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig_atsi_term), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### Schools Referring ATSI Students (with SES Context)")
                
                if 'school' in atsi_students.columns:
                    school_alloc = atsi_students['school'].value_counts().head(10).reset_index()
                    school_alloc.columns = ['school', 'atsi_referrals']
                    school_alloc['atsi_referrals'] = school_alloc['atsi_referrals'].astype(int)
                    
                    school_alloc['SES_Context'] = school_alloc['school'].apply(
                        lambda x: school_ses_data.get(x, {}).get('Disadvantage_Level', 'Unknown')
                    )
                    
                    fig_school = px.bar(
                        school_alloc,
                        y='school',
                        x='atsi_referrals',
                        orientation='h',
                        text='atsi_referrals',
                        color='SES_Context',
                        color_discrete_map={'Very High': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50', 'Unknown': '#999'},
                        title='Top Schools Referring ATSI Students',
                        labels={'school': '', 'atsi_referrals': 'ATSI Referrals'}
                    )
                    fig_school.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    fig_school.update_yaxes(categoryorder='total ascending')
                    st.plotly_chart(update_chart_layout(fig_school), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### ATSI Partnerships")
                
                if 'partnership_area' in atsi_students.columns:
                    atsi_partners = atsi_students['partnership_area'].value_counts().head(8).reset_index()
                    atsi_partners.columns = ['partnership', 'count']
                    atsi_partners['count'] = atsi_partners['count'].astype(int)
                    
                    fig_part = px.bar(
                        atsi_partners,
                        y='partnership',
                        x='count',
                        orientation='h',
                        text='count',
                        color_discrete_sequence=['#8B4513'],
                        title='Top Partnerships Serving ATSI Students',
                        labels={'partnership': '', 'count': 'Count'}
                    )
                    fig_part.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig_part), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### ATSI with Multiple Needs (2+)")
                
                multi_need_atsi = atsi_students[atsi_students['intersecting_needs'] >= 2]
                if len(multi_need_atsi) > 0:
                    display_cols = ['student_name', 'program', 'year_level', 'school', 'partnership_area']
                    display_cols = [col for col in display_cols if col in multi_need_atsi.columns]
                    
                    multi_display = multi_need_atsi[display_cols].copy()
                    st.dataframe(multi_display, use_container_width=True, hide_index=True)
                    st.info(f"**{len(multi_need_atsi)} ATSI students** with 2+ additional needs")
                else:
                    st.success("✅ No ATSI students with multiple intersecting needs")
            else:
                st.info("No ATSI students in current selection")
        
        # === TAB 2: EALD ===
        with tab_eald:
            st.markdown("### English as Additional Language or Dialect (EALD) Students")
            
            eald_students = filtered[filtered['Flag_EALD'] == 'Yes'].copy() if 'Flag_EALD' in filtered.columns else pd.DataFrame()
            
            if len(eald_students) > 0:
                eald_students['intersecting_needs'] = 0
                
                if 'Flag_ATSI' in eald_students.columns:
                    eald_students.loc[eald_students['Flag_ATSI'] == 'Yes', 'intersecting_needs'] += 1
                if 'Flag_DCP' in eald_students.columns:
                    eald_students.loc[eald_students['Flag_DCP'] == 'Yes', 'intersecting_needs'] += 1
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("EALD Total", int(len(eald_students)))
                col2.metric("With 1+ Additional Need", int((eald_students['intersecting_needs'] > 0).sum()))
                col3.metric("EALD + ATSI", int(((eald_students['Flag_ATSI'] == 'Yes') if 'Flag_ATSI' in eald_students.columns else False).sum()))
                col4.metric("EALD + DCP", int(((eald_students['Flag_DCP'] == 'Yes') if 'Flag_DCP' in eald_students.columns else False).sum()))
                
                st.markdown("---")
                st.markdown("#### EALD Students by Term")
                
                if 'term_clean' in eald_students.columns:
                    eald_by_term = eald_students['term_clean'].value_counts().sort_index().reset_index()
                    eald_by_term.columns = ['term', 'count']
                    eald_by_term['count'] = eald_by_term['count'].astype(int)
                    eald_by_term['Term'] = 'T' + eald_by_term['term'].astype(int).astype(str)
                    
                    fig_eald_term = px.bar(
                        eald_by_term,
                        x='Term',
                        y='count',
                        text='count',
                        color_discrete_sequence=['#20B2AA'],
                        title='EALD Students per Term',
                        labels={'Term': '', 'count': 'Students'}
                    )
                    fig_eald_term.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig_eald_term), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### Schools Referring EALD Students (with SES Context)")
                
                if 'school' in eald_students.columns:
                    school_eald = eald_students['school'].value_counts().head(10).reset_index()
                    school_eald.columns = ['school', 'eald_referrals']
                    school_eald['eald_referrals'] = school_eald['eald_referrals'].astype(int)
                    
                    school_eald['SES_Context'] = school_eald['school'].apply(
                        lambda x: school_ses_data.get(x, {}).get('Disadvantage_Level', 'Unknown')
                    )
                    
                    fig_school_eald = px.bar(
                        school_eald,
                        y='school',
                        x='eald_referrals',
                        orientation='h',
                        text='eald_referrals',
                        color='SES_Context',
                        color_discrete_map={'Very High': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50', 'Unknown': '#999'},
                        title='Top Schools Referring EALD Students',
                        labels={'school': '', 'eald_referrals': 'EALD Referrals'}
                    )
                    fig_school_eald.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    fig_school_eald.update_yaxes(categoryorder='total ascending')
                    st.plotly_chart(update_chart_layout(fig_school_eald), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### EALD Partnerships")
                
                if 'partnership_area' in eald_students.columns:
                    eald_partners = eald_students['partnership_area'].value_counts().head(8).reset_index()
                    eald_partners.columns = ['partnership', 'count']
                    eald_partners['count'] = eald_partners['count'].astype(int)
                    
                    fig_part_eald = px.bar(
                        eald_partners,
                        y='partnership',
                        x='count',
                        orientation='h',
                        text='count',
                        color_discrete_sequence=['#20B2AA'],
                        title='Top Partnerships Serving EALD Students',
                        labels={'partnership': '', 'count': 'Count'}
                    )
                    fig_part_eald.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig_part_eald), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### EALD with Multiple Needs (2+)")
                
                multi_eald = eald_students[eald_students['intersecting_needs'] >= 2]
                if len(multi_eald) > 0:
                    display_cols = ['student_name', 'program', 'year_level', 'school', 'partnership_area']
                    display_cols = [col for col in display_cols if col in multi_eald.columns]
                    
                    multi_eald_display = multi_eald[display_cols].copy()
                    st.dataframe(multi_eald_display, use_container_width=True, hide_index=True)
                    st.info(f"**{len(multi_eald)} EALD students** with 2+ additional needs")
                else:
                    st.success("✅ No EALD students with multiple intersecting needs")
            else:
                st.info("No EALD students in current selection")
        
        # === TAB 3: DCP ===
        with tab_dcp:
            st.markdown("### Diverse Cultural and Linguistic Background (DCP) Students")
            
            dcp_students = filtered[filtered['Flag_DCP'] == 'Yes'].copy() if 'Flag_DCP' in filtered.columns else pd.DataFrame()
            
            if len(dcp_students) > 0:
                dcp_students['intersecting_needs'] = 0
                
                if 'Flag_ATSI' in dcp_students.columns:
                    dcp_students.loc[dcp_students['Flag_ATSI'] == 'Yes', 'intersecting_needs'] += 1
                if 'Flag_EALD' in dcp_students.columns:
                    dcp_students.loc[dcp_students['Flag_EALD'] == 'Yes', 'intersecting_needs'] += 1
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("DCP Total", int(len(dcp_students)))
                col2.metric("With 1+ Additional Need", int((dcp_students['intersecting_needs'] > 0).sum()))
                col3.metric("DCP + ATSI", int(((dcp_students['Flag_ATSI'] == 'Yes') if 'Flag_ATSI' in dcp_students.columns else False).sum()))
                col4.metric("DCP + EALD", int(((dcp_students['Flag_EALD'] == 'Yes') if 'Flag_EALD' in dcp_students.columns else False).sum()))
                
                st.markdown("---")
                st.markdown("#### DCP Students by Term")
                
                if 'term_clean' in dcp_students.columns:
                    dcp_by_term = dcp_students['term_clean'].value_counts().sort_index().reset_index()
                    dcp_by_term.columns = ['term', 'count']
                    dcp_by_term['count'] = dcp_by_term['count'].astype(int)
                    dcp_by_term['Term'] = 'T' + dcp_by_term['term'].astype(int).astype(str)
                    
                    fig_dcp_term = px.bar(
                        dcp_by_term,
                        x='Term',
                        y='count',
                        text='count',
                        color_discrete_sequence=['#9370DB'],
                        title='DCP Students per Term',
                        labels={'Term': '', 'count': 'Students'}
                    )
                    fig_dcp_term.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig_dcp_term), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### Schools Referring DCP Students (with SES Context)")
                
                if 'school' in dcp_students.columns:
                    school_dcp = dcp_students['school'].value_counts().head(10).reset_index()
                    school_dcp.columns = ['school', 'dcp_referrals']
                    school_dcp['dcp_referrals'] = school_dcp['dcp_referrals'].astype(int)
                    
                    school_dcp['SES_Context'] = school_dcp['school'].apply(
                        lambda x: school_ses_data.get(x, {}).get('Disadvantage_Level', 'Unknown')
                    )
                    
                    fig_school_dcp = px.bar(
                        school_dcp,
                        y='school',
                        x='dcp_referrals',
                        orientation='h',
                        text='dcp_referrals',
                        color='SES_Context',
                        color_discrete_map={'Very High': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50', 'Unknown': '#999'},
                        title='Schools Referring DCP Students',
                        labels={'school': '', 'dcp_referrals': 'DCP Referrals'}
                    )
                    fig_school_dcp.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    fig_school_dcp.update_yaxes(categoryorder='total ascending')
                    st.plotly_chart(update_chart_layout(fig_school_dcp), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### DCP Partnerships")
                
                if 'partnership_area' in dcp_students.columns:
                    dcp_partners = dcp_students['partnership_area'].value_counts().head(8).reset_index()
                    dcp_partners.columns = ['partnership', 'count']
                    dcp_partners['count'] = dcp_partners['count'].astype(int)
                    
                    fig_part_dcp = px.bar(
                        dcp_partners,
                        y='partnership',
                        x='count',
                        orientation='h',
                        text='count',
                        color_discrete_sequence=['#9370DB'],
                        title='Top Partnerships Serving DCP Students',
                        labels={'partnership': '', 'count': 'Count'}
                    )
                    fig_part_dcp.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    st.plotly_chart(update_chart_layout(fig_part_dcp), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### DCP with Multiple Needs (2+)")
                
                multi_dcp = dcp_students[dcp_students['intersecting_needs'] >= 2]
                if len(multi_dcp) > 0:
                    display_cols = ['student_name', 'program', 'year_level', 'school', 'partnership_area']
                    display_cols = [col for col in display_cols if col in multi_dcp.columns]
                    
                    multi_dcp_display = multi_dcp[display_cols].copy()
                    st.dataframe(multi_dcp_display, use_container_width=True, hide_index=True)
                    st.info(f"**{len(multi_dcp)} DCP students** with 2+ additional needs")
                else:
                    st.success("✅ No DCP students with multiple intersecting needs")
            else:
                st.info("No DCP students in current selection")
    

    elif section == "Waitlist":
        st.markdown("## Waitlist Status")
        st.markdown("Overview of current waitlist and placement completion rates - tracks student flow through the system")
        
        if 'waitlist_status' in filtered.columns:
            wait_data = filtered['waitlist_status'].value_counts().reset_index()
            wait_data.columns = ['status', 'count']
            wait_data['count'] = wait_data['count'].astype(int)
            
            fig = px.pie(wait_data, values='count', names='status',
                        title='Waitlist Status Distribution', color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#ffd93d', '#a8e6cf'])
            st.plotly_chart(update_chart_layout(fig), use_container_width=True)
            
            st.markdown("**What this shows:**")
            st.write("- Breakdown of students by waitlist status")
            st.write("- Identifies students waiting vs. placed")
            st.write("- Helps track placement completion")


    elif section == "Diagnostics":
        st.markdown("## Data Diagnostics")
        st.markdown("Debug information to verify data is loaded correctly")
        
        st.markdown("### Raw Data Preview")
        st.write(f"**Total rows loaded:** {len(allocation_df)}")
        st.write(f"**Columns:** {list(allocation_df.columns)}")
        
        st.markdown("### Filtered Data Preview")
        st.write(f"**Rows after filtering:** {len(filtered)}")
        st.dataframe(filtered.head(10), use_container_width=True)
        
        st.markdown("### Column Value Samples")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Programs**")
            if 'program' in allocation_df.columns:
                progs = allocation_df['program'].value_counts()
                for prog, count in progs.items():
                    st.write(f"- {prog}: {count}")
        
        with col2:
            st.markdown("**Year Levels**")
            if 'year_level' in allocation_df.columns:
                levels = allocation_df['year_level'].value_counts().sort_index()
                for level, count in levels.items():
                    st.write(f"- {level}: {count}")
        
        with col3:
            st.markdown("**Partnership Areas**")
            if 'partnership_area' in allocation_df.columns:
                partners = allocation_df['partnership_area'].value_counts().head(5)
                for partner, count in partners.items():
                    st.write(f"- {partner}: {count}")
        
        st.markdown("### Data Quality Check")
        st.write("**Missing values:**")
        missing = allocation_df.isnull().sum()
        missing = missing[missing > 0]
        if len(missing) > 0:
            st.dataframe(missing)
        else:
            st.success("✅ No missing values")
