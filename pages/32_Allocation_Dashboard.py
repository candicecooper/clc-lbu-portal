import streamlit as st
import pandas as pd
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
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    h1, h2, h3 { color: #00e5ff !important; text-shadow: 0 0 15px rgba(0,229,255,0.3); }
    p, label, span { color: #ffffff !important; }
    [data-testid="metric-container"] { background: linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(26,122,122,0.1) 100%) !important; }
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
        font=dict(color='#d0d0d0', size=12),
        hovermode='x unified',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig

st.markdown("# Student Allocation Dashboard")
st.markdown("Active student placements and equity analysis")

main_tabs = st.tabs(["Overview", "Analysis", "Data Upload"])

# ==== OVERVIEW TAB ====
with main_tabs[0]:
    if st.button("Refresh Data", key="refresh_btn"):
        st.cache_data.clear()
    
    allocation_df = load_allocation_data()
    
    if allocation_df is None or allocation_df.empty:
        st.warning("No data found. Go to Data Upload tab to load data.")
    else:
        st.markdown("---")
        st.markdown("## Current Active Students")
        
        # FILTERS
        col1, col2, col3, col4 = st.columns(4)
        
        filter_year = None
        filter_term = None
        filter_program = None
        
        with col1:
            if 'year' in allocation_df.columns:
                years = sorted([y for y in allocation_df['year'].dropna().unique() if y != ''])
                filter_year = st.selectbox("Year", years if years else [2026])
        
        with col2:
            if 'term' in allocation_df.columns and filter_year:
                terms = sorted([t for t in allocation_df[allocation_df['year'] == filter_year]['term'].dropna().unique() if t != ''])
                filter_term = st.selectbox("Term", terms if terms else ['1'])
        
        with col3:
            if 'program' in allocation_df.columns:
                progs = ['All'] + sorted([p for p in allocation_df['program'].dropna().unique() if p != ''])
                filter_program = st.selectbox("Program", progs)
        
        with col4:
            st.empty()
        
        # APPLY FILTERS BUTTON
        if st.button("Apply Filters", key="apply_filters"):
            filtered = allocation_df[
                (allocation_df['year'] == filter_year) &
                (allocation_df['term'] == filter_term)
            ]
            
            if filter_program != 'All':
                filtered = filtered[filtered['program'] == filter_program]
        else:
            filtered = allocation_df[
                (allocation_df['year'] == filter_year) &
                (allocation_df['term'] == filter_term)
            ]
            
            if filter_program != 'All':
                filtered = filtered[filtered['program'] == filter_program]
        
        st.markdown(f"**{len(filtered)} active students** | {int(filter_year)} Term {filter_term} | {filter_program}")
        st.markdown("---")
        
        # KEY METRICS
        st.markdown("## Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Active Students", len(filtered))
        
        with col2:
            if 'program' in filtered.columns:
                programs = filtered['program'].nunique()
                st.metric("Programs", programs)
        
        with col3:
            st.metric("Data Points", len(filtered.columns))
        
        with col4:
            st.metric("Last Updated", datetime.now().strftime("%d/%m/%Y"))
        
        st.markdown("---")
        
        # PROGRAM BREAKDOWN
        st.markdown("## Student Distribution by Program")
        
        if 'program' in filtered.columns:
            prog_data = filtered['program'].value_counts().reset_index()
            prog_data.columns = ['program', 'count']
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_prog = px.bar(
                    prog_data,
                    x='program',
                    y='count',
                    title='Students by Program',
                    labels={'program': 'Program', 'count': 'Count'},
                    text_auto=True,
                    color='count',
                    color_continuous_scale='Viridis'
                )
                fig_prog.update_traces(textposition='outside', textfont=dict(color='#d0d0d0'))
                st.plotly_chart(update_chart_layout(fig_prog), use_container_width=True)
            
            with col2:
                st.markdown("### Program Summary")
                for idx, row in prog_data.iterrows():
                    st.write(f"**{row['program']}**: {row['count']} students")
        
        st.markdown("---")
        
        # EQUITY SNAPSHOT
        st.markdown("## Equity Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("**ATSI Students**\n\nColumn pending addition to database")
        
        with col2:
            st.info("**EALD Students**\n\nColumn pending addition to database")
        
        with col3:
            st.info("**SWD Students**\n\nColumn pending addition to database")
        
        st.markdown("---")
        
        # YEAR LEVEL DISTRIBUTION
        st.markdown("## Year Level Distribution")
        
        if 'year_level' in filtered.columns:
            year_level_data = filtered['year_level'].value_counts().reset_index()
            year_level_data.columns = ['year_level', 'count']
            year_level_data = year_level_data.sort_values('year_level')
            
            fig_year = px.bar(
                year_level_data,
                x='year_level',
                y='count',
                title='Students by Year Level',
                labels={'year_level': 'Year Level', 'count': 'Count'},
                text_auto=True,
                color_discrete_sequence=['#4ecdc4']
            )
            fig_year.update_traces(textposition='outside', textfont=dict(color='#d0d0d0'))
            st.plotly_chart(update_chart_layout(fig_year), use_container_width=True)
        
        st.markdown("---")
        
        # PARTNERSHIP PLACEMENTS
        st.markdown("## High Partnership Placements")
        
        if 'partnership_area' in filtered.columns:
            partnership_data = filtered['partnership_area'].value_counts().head(10).reset_index()
            partnership_data.columns = ['partnership_area', 'count']
            
            if len(partnership_data) > 0:
                fig_partner = px.barh(
                    partnership_data,
                    y='partnership_area',
                    x='count',
                    title='Top 10 Partnership Areas',
                    labels={'partnership_area': 'Partnership', 'count': 'Count'},
                    text_auto=True,
                    color='count',
                    color_continuous_scale='Reds'
                )
                fig_partner.update_traces(textposition='outside', textfont=dict(color='#d0d0d0'))
                st.plotly_chart(update_chart_layout(fig_partner), use_container_width=True)
            else:
                st.info("No partnership data available")
        
        st.markdown("---")
        
        # WAITLIST STATUS
        st.markdown("## Waitlist Status")
        
        if 'waitlist_status' in filtered.columns:
            waitlist_data = filtered['waitlist_status'].value_counts().reset_index()
            waitlist_data.columns = ['waitlist_status', 'count']
            
            fig_wait = px.pie(
                waitlist_data,
                values='count',
                names='waitlist_status',
                title='Waitlist Status Distribution',
                color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#ffd93d', '#a8e6cf']
            )
            st.plotly_chart(update_chart_layout(fig_wait), use_container_width=True)

# ==== ANALYSIS TAB ====
with main_tabs[1]:
    st.markdown("## Detailed Analysis")
    st.info("Additional analysis sections coming - Trends, Complexity, Intersectionality, etc.")

# ==== UPLOAD TAB ====
with main_tabs[2]:
    st.markdown("## Upload Student Allocation Data")
    st.warning("This will replace all existing data with your file")
    
    uploaded_file = st.file_uploader("Choose Excel (.xlsx) or CSV", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()
        
        st.success(f"Loaded {len(df)} rows")
        
        column_map = {
            'Student_Name': 'student_name',
            'Meeting_Week': 'meeting_week',
            'Meeting_Date': 'meeting_date',
            'Term': 'term',
            'Referral_Year': 'year',
            'Allocated_Program': 'program',
            'DOB': 'date_of_birth',
            'Gender': 'gender',
            'Year_Level': 'year_level',
            'Referring_School': 'school',
            'Partnership_Area': 'partnership_area',
            'Previous_CLC_Placement': 'previous_clc_placement',
            'Previous_Other_LC': 'previous_other_lc',
            'Other_LC_Name': 'other_lc_name',
            'Total_Previous_Placements': 'total_previous_placements',
            'Placement_History_Notes': 'placement_history_notes',
            'Bespoke_Placement': 'bespoke_placement',
            'Waitlist_Status': 'waitlist_status',
            'Waitlist_Date': 'waitlist_date',
            'Allocated_From_Waitlist': 'allocated_from_waitlist',
            'Previously_Referred': 'previously_referred',
            'Medical_Condition_Details': 'medical_condition_details',
            'Extension_Weeks': 'extension_weeks',
        }
        
        df_mapped = df.copy()
        for excel_col, supabase_col in column_map.items():
            if excel_col in df_mapped.columns:
                df_mapped = df_mapped.rename(columns={excel_col: supabase_col})
        
        df_mapped = df_mapped[[col for col in df_mapped.columns if col in column_map.values()]]
        
        # Handle date columns FIRST
        date_cols = ['meeting_date', 'date_of_birth', 'waitlist_date']
        for col in date_cols:
            if col in df_mapped.columns:
                df_mapped[col] = pd.to_datetime(df_mapped[col], errors='coerce')
                df_mapped[col] = df_mapped[col].dt.strftime('%Y-%m-%d')
                df_mapped[col] = df_mapped[col].replace('NaT', '')
        
        # Handle numeric columns
        numeric_cols = ['year', 'term', 'extension_weeks', 'total_previous_placements']
        for col in numeric_cols:
            if col in df_mapped.columns:
                df_mapped[col] = pd.to_numeric(df_mapped[col], errors='coerce').fillna(0).astype(int)
        
        # Convert to string
        df_mapped = df_mapped.astype(str)
        df_mapped = df_mapped.replace('nan', '')
        df_mapped = df_mapped.fillna('')
        
        for col in df_mapped.columns:
            if df_mapped[col].dtype == 'object':
                df_mapped[col] = df_mapped[col].str.strip()
        
        if 'meeting_date' in df_mapped.columns:
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            df_mapped['meeting_date'] = df_mapped['meeting_date'].replace('', today)
        
        st.markdown("### Data Preview")
        st.dataframe(df_mapped.head(5), use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Upload", key="upload_btn"):
                if not supabase:
                    st.error("Supabase not connected")
                else:
                    with st.spinner("Uploading..."):
                        try:
                            st.write("Clearing existing data...")
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
                            
                            st.success(f"Complete! {total} records uploaded")
                            st.balloons()
                            st.info("Go to Overview tab and click Refresh Data")
                            
                        except Exception as e:
                            st.error(f"Failed: {str(e)[:200]}")
        
        with col2:
            st.info("Review data above before uploading")
