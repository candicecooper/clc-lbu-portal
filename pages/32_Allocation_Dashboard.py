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
            ["Overview", "Trends", "Complexity", "Risk Assessment", "Equity", "Waitlist"],
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
        years = sorted([y for y in allocation_df['year'].dropna().unique() if y != ''])
        selected_year = st.selectbox("Year", years if years else [2026])
    
    with col2:
        terms = sorted([int(t) for t in allocation_df[allocation_df['year'] == selected_year]['term'].dropna().unique() if t != '' and int(t) >= 1])
        selected_term = st.selectbox("Term", terms if terms else [1])
    
    with col3:
        progs = ['All'] + sorted([p for p in allocation_df['program'].dropna().unique() if p != ''])
        selected_program = st.selectbox("Program", progs)
    
    # FILTER DATA
    filtered = allocation_df[
        (allocation_df['year'] == selected_year) &
        (allocation_df['term'] == selected_term)
    ]
    
    if selected_program != 'All':
        filtered = filtered[filtered['program'] == selected_program]
    
    st.info(f"**{len(filtered)} active students** | Year {int(selected_year)} Term {selected_term} | {selected_program}")
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
        st.info("Line chart showing enrollment over time by program")
        
        trend_data = allocation_df.dropna(subset=['year', 'term', 'program'])
        trend_data = trend_data[pd.to_numeric(trend_data['term'], errors='coerce') >= 1]
        trend_data['YT'] = trend_data['year'].astype(str) + ' T' + trend_data['term'].astype(str)
        trend_agg = trend_data.groupby(['YT', 'program']).size().reset_index(name='count')
        trend_agg['count'] = trend_agg['count'].astype(int)
        
        fig = px.line(trend_agg, x='YT', y='count', color='program', markers=True,
                     title='Enrollment Trend', labels={'YT': '', 'count': 'Students'})
        fig.update_traces(line=dict(width=3), marker=dict(size=8))
        st.plotly_chart(update_chart_layout(fig), use_container_width=True)
    
    elif section == "Complexity":
        st.markdown("## Complexity Analysis")
        st.markdown("Matrix showing how students distribute across year levels and programs. Identifies gaps and concentrations in placement.")
        
        if 'year_level' in filtered.columns and 'program' in filtered.columns:
            # Define correct year level order
            year_order = ['R', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
            
            # Create heatmap data
            heatmap = pd.crosstab(filtered['year_level'], filtered['program'])
            
            # Reindex to ensure all year levels and all programs appear
            heatmap = heatmap.reindex(year_order, fill_value=0)
            heatmap = heatmap.reindex(['JP', 'PY', 'SY'], axis=1, fill_value=0)
            
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
        st.markdown("## Risk & Complexity Assessment")
        st.markdown("Identifies high-risk students and predicts placement success - enables early intervention")
        
        # CALCULATE RISK SCORES
        risk_df = filtered.copy()
        risk_df['risk_score'] = 0
        risk_df['risk_factors'] = ''
        
        # Factor 1: Multiple previous placements (higher = more complex)
        if 'total_previous_placements' in risk_df.columns:
            risk_df['prev_placements_num'] = pd.to_numeric(risk_df['total_previous_placements'], errors='coerce').fillna(0)
            risk_df.loc[risk_df['prev_placements_num'] >= 2, 'risk_score'] += 3
            risk_df.loc[risk_df['prev_placements_num'] == 1, 'risk_score'] += 1
        
        # Factor 2: Waitlist status (waiting = higher risk)
        if 'waitlist_status' in risk_df.columns:
            risk_df.loc[risk_df['waitlist_status'] == 'Waiting', 'risk_score'] += 2
        
        # Factor 3: Extended placement (extension weeks = complexity)
        if 'extension_weeks' in risk_df.columns:
            risk_df['ext_weeks_num'] = pd.to_numeric(risk_df['extension_weeks'], errors='coerce').fillna(0)
            risk_df.loc[risk_df['ext_weeks_num'] > 4, 'risk_score'] += 2
            risk_df.loc[(risk_df['ext_weeks_num'] > 0) & (risk_df['ext_weeks_num'] <= 4), 'risk_score'] += 1
        
        # Factor 4: Bespoke placement (specialized needs)
        if 'bespoke_placement' in risk_df.columns:
            risk_df.loc[risk_df['bespoke_placement'] == 'Yes', 'risk_score'] += 2
        
        # Categorize risk level
        risk_df['risk_level'] = 'Low'
        risk_df.loc[risk_df['risk_score'] >= 5, 'risk_level'] = 'Critical'
        risk_df.loc[(risk_df['risk_score'] >= 3) & (risk_df['risk_score'] < 5), 'risk_level'] = 'High'
        risk_df.loc[(risk_df['risk_score'] >= 1) & (risk_df['risk_score'] < 3), 'risk_level'] = 'Medium'
        
        # SUMMARY METRICS
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Critical Risk", int((risk_df['risk_level'] == 'Critical').sum()))
        col2.metric("High Risk", int((risk_df['risk_level'] == 'High').sum()))
        col3.metric("Medium Risk", int((risk_df['risk_level'] == 'Medium').sum()))
        col4.metric("Low Risk", int((risk_df['risk_level'] == 'Low').sum()))
        
        st.markdown("---")
        st.markdown("## Risk Distribution")
        st.markdown("Breakdown of students by risk level - Critical/High need immediate support planning")
        
        col1, col2 = st.columns(2)
        
        with col1:
            risk_summary = risk_df['risk_level'].value_counts().reindex(['Critical', 'High', 'Medium', 'Low'], fill_value=0)
            fig_risk = px.bar(
                x=risk_summary.index,
                y=risk_summary.values,
                text=risk_summary.values,
                color=risk_summary.index,
                color_discrete_map={'Critical': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50'},
                title='Students by Risk Level',
                labels={'x': 'Risk Level', 'y': 'Count'}
            )
            fig_risk.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
            st.plotly_chart(update_chart_layout(fig_risk), use_container_width=True)
        
        with col2:
            risk_by_prog = risk_df.groupby(['program', 'risk_level']).size().unstack(fill_value=0)
            fig_prog_risk = px.bar(
                risk_by_prog,
                x=risk_by_prog.index,
                y=['Critical', 'High', 'Medium', 'Low'],
                title='Risk by Program',
                labels={'value': 'Count', 'index': 'Program'},
                color_discrete_map={'Critical': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50'}
            )
            st.plotly_chart(update_chart_layout(fig_prog_risk), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## Risk Score Analysis")
        st.markdown("Distribution of risk scores (0-9 scale) - higher score = more complex needs")
        
        fig_score = px.histogram(
            risk_df,
            x='risk_score',
            nbins=10,
            color_discrete_sequence=['#00e5ff'],
            title='Risk Score Distribution',
            labels={'risk_score': 'Risk Score (0-9)', 'count': 'Students'}
        )
        fig_score.update_traces(textposition='outside')
        st.plotly_chart(update_chart_layout(fig_score), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## High-Risk Students (Critical)")
        st.markdown("Students requiring immediate attention and intensive support")
        
        critical = risk_df[risk_df['risk_level'] == 'Critical'].copy()
        if len(critical) > 0:
            display_cols = ['student_name', 'program', 'year_level', 'risk_score', 'waitlist_status', 'bespoke_placement']
            display_cols = [col for col in display_cols if col in critical.columns]
            
            critical_display = critical[display_cols].copy()
            critical_display['risk_score'] = critical_display['risk_score'].astype(int)
            critical_display = critical_display.sort_values('risk_score', ascending=False)
            
            st.dataframe(critical_display, use_container_width=True, hide_index=True)
            st.info(f"**{len(critical)} students** require intervention planning")
        else:
            st.success("✅ No critical risk students detected")
        
        st.markdown("---")
        st.markdown("## Placement Success Prediction")
        st.markdown("Estimated likelihood of successful placement completion based on risk profile")
        
        risk_df['success_likelihood'] = 100 - (risk_df['risk_score'] * 10)
        risk_df['success_likelihood'] = risk_df['success_likelihood'].clip(0, 100)
        
        fig_success = px.scatter(
            risk_df,
            x='risk_score',
            y='success_likelihood',
            color='risk_level',
            size='success_likelihood',
            hover_data=['student_name', 'program'],
            title='Risk vs Placement Success Likelihood',
            labels={'risk_score': 'Risk Score', 'success_likelihood': 'Success %'},
            color_discrete_map={'Critical': '#f44336', 'High': '#ff9800', 'Medium': '#ffc107', 'Low': '#4caf50'}
        )
        st.plotly_chart(update_chart_layout(fig_success), use_container_width=True)
    
    elif section == "Equity":
        st.markdown("## Equity Analysis")
        st.warning("Flag_ATSI, Flag_EALD, Flag_SWD columns - ready for addition")
        st.info("Once added: representation %, intersectionality, gap analysis")

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
