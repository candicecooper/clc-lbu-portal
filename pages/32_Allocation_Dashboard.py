import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta

try:
    from supabase import create_client, Client
except ImportError:
    pass

st.set_page_config(page_title="Allocation Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    h1, h2, h3 { color: #00e5ff !important; text-shadow: 0 0 15px rgba(0,229,255,0.3); }
    p, label, span { color: #ffffff !important; }
    [data-testid="metric-container"] { background: linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(26,122,122,0.1) 100%) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { background: rgba(26,122,122,0.2) !important; border-radius: 8px !important; }
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
        font=dict(color='#d0d0d0', size=11),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=True
    )
    fig.update_xaxes(showgrid=False, linecolor='rgba(100,100,100,0.3)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(100,100,100,0.2)', linecolor='rgba(100,100,100,0.3)')
    return fig

# Initialize session state
if 'filter_program' not in st.session_state:
    st.session_state.filter_program = None
if 'filter_year_level' not in st.session_state:
    st.session_state.filter_year_level = None

st.markdown("# Student Allocation Dashboard")
st.markdown("Comprehensive enrollment analysis and equity insights")

# SIDEBAR - GLOBAL FILTERS
with st.sidebar:
    st.markdown("## Global Filters")
    
    allocation_df = load_allocation_data()
    
    if allocation_df is not None and not allocation_df.empty:
        years = sorted([y for y in allocation_df['year'].dropna().unique() if y != ''])
        selected_year = st.selectbox("Year", years if years else [2026], key="sidebar_year")
        
        terms = sorted([t for t in allocation_df[allocation_df['year'] == selected_year]['term'].dropna().unique() if t != ''])
        selected_term = st.selectbox("Term", terms if terms else ['1'], key="sidebar_term")
        
        if st.button("Reset Filters", key="reset_filters"):
            st.session_state.filter_program = None
            st.session_state.filter_year_level = None
        
        st.markdown("---")
        st.markdown("**Active Filters**")
        if st.session_state.filter_program:
            st.write(f"Program: `{st.session_state.filter_program}`")
            if st.button("Clear Program", key="clear_prog"):
                st.session_state.filter_program = None
        
        if st.session_state.filter_year_level:
            st.write(f"Year Level: `{st.session_state.filter_year_level}`")
            if st.button("Clear Year Level", key="clear_level"):
                st.session_state.filter_year_level = None
    else:
        st.warning("No data loaded")

# MAIN CONTENT
if allocation_df is None or allocation_df.empty:
    st.warning("No data found. Go to Data Upload to load data.")
else:
    # BASE FILTER
    filtered = allocation_df[
        (allocation_df['year'] == selected_year) &
        (allocation_df['term'] == selected_term)
    ]
    
    if st.session_state.filter_program:
        filtered = filtered[filtered['program'] == st.session_state.filter_program]
    
    if st.session_state.filter_year_level:
        filtered = filtered[filtered['year_level'] == st.session_state.filter_year_level]
    
    st.info(f"**{len(filtered)} students** | {int(selected_year)} Term {selected_term}" + 
            (f" | Program: {st.session_state.filter_program}" if st.session_state.filter_program else "") +
            (f" | Year Level: {st.session_state.filter_year_level}" if st.session_state.filter_year_level else ""))
    
    # NAVIGATION TABS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Overview", "Trends", "Complexity", "Equity", "Waitlist", "Data Upload"])
    
    # ==== TAB 1: OVERVIEW ====
    with tab1:
        st.markdown("## Dashboard Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Active Students", len(filtered))
        with col2:
            if 'program' in filtered.columns:
                st.metric("Programs", filtered['program'].nunique())
        with col3:
            if 'year_level' in filtered.columns:
                st.metric("Year Levels", filtered['year_level'].nunique())
        with col4:
            st.metric("Updated", datetime.now().strftime("%d/%m/%y"))
        
        st.markdown("---")
        st.markdown("## Program Distribution")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if 'program' in filtered.columns:
                prog_data = filtered['program'].value_counts().reset_index()
                prog_data.columns = ['program', 'count']
                
                fig_prog = px.bar(
                    prog_data,
                    x='program',
                    y='count',
                    text='count',
                    color='count',
                    color_continuous_scale='Viridis',
                    title='Students by Program',
                    labels={'program': '', 'count': 'Students'}
                )
                fig_prog.update_traces(textposition='outside', textfont=dict(color='#d0d0d0'))
                st.plotly_chart(update_chart_layout(fig_prog), use_container_width=True)
                
                # CLICKABLE - filter by program
                st.markdown("**Click to filter:** ")
                for idx, row in prog_data.iterrows():
                    if st.button(f"{row['program']} ({row['count']})", key=f"prog_{idx}"):
                        st.session_state.filter_program = row['program']
                        st.rerun()
        
        with col2:
            st.markdown("### Summary")
            for idx, row in prog_data.iterrows():
                st.write(f"**{row['program']}**: {row['count']}")
        
        st.markdown("---")
        st.markdown("## Year Level Distribution")
        
        if 'year_level' in filtered.columns:
            year_data = filtered['year_level'].value_counts().sort_index().reset_index()
            year_data.columns = ['year_level', 'count']
            
            fig_year = px.bar(
                year_data,
                x='year_level',
                y='count',
                text='count',
                color_discrete_sequence=['#4ecdc4'],
                title='Students by Year Level',
                labels={'year_level': '', 'count': 'Count'}
            )
            fig_year.update_traces(textposition='outside', textfont=dict(color='#d0d0d0'))
            st.plotly_chart(update_chart_layout(fig_year), use_container_width=True)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("**Filter by year level:** ")
                for idx, row in year_data.iterrows():
                    if st.button(f"Year {row['year_level']} ({row['count']})", key=f"year_{idx}"):
                        st.session_state.filter_year_level = row['year_level']
                        st.rerun()
        
        st.markdown("---")
        st.markdown("## Partnership Placements")
        
        if 'partnership_area' in filtered.columns:
            partner_data = filtered['partnership_area'].value_counts().head(12).reset_index()
            partner_data.columns = ['partnership_area', 'count']
            
            fig_partner = px.barh(
                partner_data,
                x='count',
                y='partnership_area',
                text='count',
                color='count',
                color_continuous_scale='Reds',
                title='Top Partnership Areas',
                labels={'partnership_area': '', 'count': 'Count'}
            )
            fig_partner.update_traces(textposition='outside', textfont=dict(color='#d0d0d0'))
            fig_partner.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(update_chart_layout(fig_partner), use_container_width=True)
    
    # ==== TAB 2: TRENDS ====
    with tab2:
        st.markdown("## Enrollment Trends")
        
        if 'year' in filtered.columns and 'term' in filtered.columns and 'program' in filtered.columns:
            # TIME SERIES - by program
            trend_data = allocation_df.dropna(subset=['year', 'term', 'program'])
            trend_data = trend_data.copy()
            trend_data['YearTerm'] = trend_data['year'].astype(str) + ' T' + trend_data['term'].astype(str)
            trend_agg = trend_data.groupby(['YearTerm', 'program']).size().reset_index(name='count')
            
            fig_trend = px.line(
                trend_agg,
                x='YearTerm',
                y='count',
                color='program',
                title='Enrollment Trend by Program',
                markers=True,
                labels={'YearTerm': '', 'count': 'Students'}
            )
            fig_trend.update_traces(line=dict(width=3), marker=dict(size=8))
            st.plotly_chart(update_chart_layout(fig_trend), use_container_width=True)
            
            st.markdown("---")
            
            # AREA CHART - cumulative
            trend_area = trend_agg.copy()
            trend_area = trend_area.sort_values('YearTerm')
            
            fig_area = px.area(
                trend_area,
                x='YearTerm',
                y='count',
                color='program',
                title='Cumulative Enrollment',
                labels={'YearTerm': '', 'count': 'Students'}
            )
            st.plotly_chart(update_chart_layout(fig_area), use_container_width=True)
            
            st.markdown("---")
            
            # GROWTH METRICS
            st.markdown("## Growth Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Enrollment by Program")
                prog_summary = filtered['program'].value_counts().reset_index()
                prog_summary.columns = ['program', 'count']
                
                for idx, row in prog_summary.iterrows():
                    st.write(f"**{row['program']}**: {row['count']} students")
            
            with col2:
                st.markdown("### Year Level Breakdown")
                if 'year_level' in filtered.columns:
                    level_summary = filtered['year_level'].value_counts().sort_index().reset_index()
                    level_summary.columns = ['year_level', 'count']
                    
                    for idx, row in level_summary.iterrows():
                        st.write(f"**Year {row['year_level']}**: {row['count']} students")
    
    # ==== TAB 3: COMPLEXITY ====
    with tab3:
        st.markdown("## Complexity Analysis")
        st.info("Students with multiple placement considerations (year level + previous placements + partnership needs)")
        
        if 'total_previous_placements' in filtered.columns and 'program' in filtered.columns:
            # COMPLEXITY SCORE
            filtered['complexity_score'] = 0
            if 'year_level' in filtered.columns:
                filtered['complexity_score'] += (filtered['year_level'].notna().astype(int))
            filtered['complexity_score'] += (pd.to_numeric(filtered['total_previous_placements'], errors='coerce').fillna(0) > 0).astype(int)
            if 'partnership_area' in filtered.columns:
                filtered['complexity_score'] += (filtered['partnership_area'].notna().astype(int))
            
            complexity_summary = filtered.groupby('program')['complexity_score'].agg(['count', 'mean']).reset_index()
            complexity_summary.columns = ['program', 'students', 'avg_complexity']
            
            fig_complex = px.scatter(
                complexity_summary,
                x='students',
                y='avg_complexity',
                size='students',
                color='avg_complexity',
                color_continuous_scale='Reds',
                text='program',
                title='Complexity by Program',
                labels={'students': 'Student Count', 'avg_complexity': 'Avg Complexity Score'}
            )
            fig_complex.update_traces(textposition='top center', textfont=dict(color='#d0d0d0', size=12))
            st.plotly_chart(update_chart_layout(fig_complex), use_container_width=True)
            
            st.markdown("---")
            
            # HEATMAP - year level x program
            if 'year_level' in filtered.columns and 'program' in filtered.columns:
                heatmap_data = pd.crosstab(filtered['year_level'], filtered['program'])
                
                fig_heat = px.imshow(
                    heatmap_data,
                    text_auto=True,
                    color_continuous_scale='Blues',
                    title='Student Distribution Matrix (Year Level × Program)',
                    labels={'x': 'Program', 'y': 'Year Level', 'color': 'Count'}
                )
                fig_heat.update_traces(text=heatmap_data.values, texttemplate='%{text}')
                st.plotly_chart(update_chart_layout(fig_heat), use_container_width=True)
    
    # ==== TAB 4: EQUITY ====
    with tab4:
        st.markdown("## Equity Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("**Aboriginal & Torres Strait Islander**\n\nFlag_ATSI column - ready for addition")
        with col2:
            st.info("**English as Additional Language**\n\nFlag_EALD column - ready for addition")
        with col3:
            st.info("**Students with Disability**\n\nFlag_SWD column - ready for addition")
        
        st.markdown("---")
        st.markdown("## When Equity Columns Added")
        st.markdown("""
        Once Flag_ATSI, Flag_EALD, and Flag_SWD columns are in Supabase:
        - Representation % by program
        - Co-occurrence analysis (intersectionality)
        - Equity gap identification
        - Trend analysis over time
        - Risk factors by group
        """)
    
    # ==== TAB 5: WAITLIST ====
    with tab5:
        st.markdown("## Waitlist Management")
        
        if 'waitlist_status' in filtered.columns:
            waitlist_summary = filtered['waitlist_status'].value_counts().reset_index()
            waitlist_summary.columns = ['status', 'count']
            
            fig_wait = px.pie(
                waitlist_summary,
                values='count',
                names='status',
                title='Waitlist Status Distribution',
                color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#ffd93d', '#a8e6cf', '#95e1d3']
            )
            st.plotly_chart(update_chart_layout(fig_wait), use_container_width=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Status Breakdown")
                for idx, row in waitlist_summary.iterrows():
                    st.write(f"**{row['status']}**: {row['count']} students")
            
            with col2:
                if 'allocated_from_waitlist' in filtered.columns:
                    allocated = (filtered['allocated_from_waitlist'] == 'Yes').sum()
                    st.metric("From Waitlist", allocated)
        
        st.markdown("---")
        st.markdown("## Extension Analysis")
        
        if 'extension_weeks' in filtered.columns:
            extensions = pd.to_numeric(filtered['extension_weeks'], errors='coerce')
            st.metric("Avg Extension (weeks)", f"{extensions.mean():.1f}")
            
            extension_dist = filtered.copy()
            extension_dist['ext_weeks'] = pd.to_numeric(extension_dist['extension_weeks'], errors='coerce')
            extension_dist = extension_dist[extension_dist['ext_weeks'] > 0]
            
            if len(extension_dist) > 0:
                st.write(f"**{len(extension_dist)} students** with extensions")
    
    # ==== TAB 6: DATA UPLOAD ====
    with tab6:
        st.markdown("## Upload Student Data")
        st.warning("This will replace all existing data")
        
        uploaded_file = st.file_uploader("Choose Excel (.xlsx) or CSV", type=['xlsx', 'csv'])
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()
            
            st.success(f"Loaded {len(df)} rows")
            
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
            
            st.dataframe(df_mapped.head(5), use_container_width=True)
            
            if st.button("Confirm Upload"):
                if not supabase:
                    st.error("Supabase not connected")
                else:
                    with st.spinner("Uploading..."):
                        try:
                            st.write("Clearing data...")
                            supabase.table('allocation_students').delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
                            
                            numeric_cols = ['year', 'term', 'extension_weeks', 'total_previous_placements']
                            date_cols = ['meeting_date', 'date_of_birth', 'waitlist_date']
                            
                            records = []
                            for idx, row in df_mapped.iterrows():
                                record = {}
                                for col in df_mapped.columns:
                                    val = row[col]
                                    
                                    if pd.isna(val) or val == 'nan' or val == '':
                                        if col in numeric_cols:
                                            record[col] = 0
                                        elif col in date_cols:
                                            record[col] = None
                                        else:
                                            record[col] = ''
                                    else:
                                        record[col] = str(val)
                                
                                records.append(record)
                            
                            batch_size = 50
                            total = 0
                            
                            for i in range(0, len(records), batch_size):
                                batch = records[i:i+batch_size]
                                supabase.table('allocation_students').insert(batch).execute()
                                total += len(batch)
                                st.write(f"Uploaded {total}/{len(records)}...")
                            
                            st.success(f"Complete! {total} records")
                            st.balloons()
                            st.info("Go to Overview and click Refresh Data")
                            
                        except Exception as e:
                            st.error(f"Failed: {str(e)[:200]}")
