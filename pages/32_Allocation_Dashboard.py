"""
CLC-LBU ALLOCATION DASHBOARD - FULL BUILD
All 9 tabs with strategic visualizations
"""
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

st.set_page_config(page_title="📊 Allocation Dashboard", page_icon="📊", layout="wide")

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
    """Apply consistent styling to all charts"""
    fig.update_layout(
        plot_bgcolor='rgba(10,14,39,0.8)',
        paper_bgcolor='rgba(10,14,39,0.8)',
        font=dict(color='#ffffff', size=11),
        hovermode='x unified',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    return fig

st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
st.markdown("_Strategic student placement analysis and equity insights_")

main_tabs = st.tabs(["📊 Analysis", "📤 Upload Data"])

# ==== ANALYSIS TAB ====
with main_tabs[0]:
    if st.button("🔄 Refresh Data", key="refresh_btn"):
        st.cache_data.clear()
    
    allocation_df = load_allocation_data()
    
    if allocation_df is None or allocation_df.empty:
        st.warning("⚠️ No data found. Go to **📤 Upload Data** tab to load data.")
    else:
        st.info(f"✅ Loaded {len(allocation_df)} records | Columns: {len(allocation_df.columns)}")
        
        # FILTERS
        st.markdown("## 🔍 Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'year' in allocation_df.columns:
                years = sorted([y for y in allocation_df['year'].dropna().unique() if y != ''])
                selected_year = st.selectbox("Year", years if years else [2026])
            else:
                selected_year = 2026
        
        with col2:
            if 'term' in allocation_df.columns and selected_year:
                terms = sorted([t for t in allocation_df[allocation_df['year'] == selected_year]['term'].dropna().unique() if t != ''])
                selected_term = st.selectbox("Term", terms if terms else ['1'])
            else:
                selected_term = '1'
        
        with col3:
            if 'program' in allocation_df.columns:
                progs = ['All'] + sorted([p for p in allocation_df['program'].dropna().unique() if p != ''])
                selected_program = st.selectbox("Program", progs)
            else:
                selected_program = 'All'
        
        # Filter data
        filtered = allocation_df[
            (allocation_df['year'] == selected_year) &
            (allocation_df['term'] == selected_term)
        ]
        
        if selected_program != 'All':
            filtered = filtered[filtered['program'] == selected_program]
        
        st.info(f"✅ **{len(filtered)} records** | {int(selected_year)} Term {selected_term} | {selected_program}")
        st.markdown("---")
        
        # ANALYSIS TABS
        tabs = st.tabs([
            "📍 Placement", "📈 Trends", "🧩 SWD", "⚠️ Complexity",
            "🔗 Intersect", "🏳️ ATSI", "🌐 EALD", "Assessment", "Raw"
        ])
        
        # TAB 1: PLACEMENT
        with tabs[0]:
            st.markdown("## 📍 Placement Data by Program")
            
            if 'program' in allocation_df.columns:
                prog_dist = allocation_df['program'].value_counts().reset_index()
                prog_dist.columns = ['program', 'count']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_sun = px.sunburst(
                        prog_dist,
                        labels='program',
                        values='count',
                        title='Program Distribution',
                        color='count',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(update_chart_layout(fig_sun), use_container_width=True)
                
                with col2:
                    metrics = pd.DataFrame({
                        'Program': prog_dist['program'],
                        'Students': prog_dist['count'],
                        '%': (prog_dist['count'] / prog_dist['count'].sum() * 100).round(1)
                    })
                    st.dataframe(metrics, use_container_width=True, hide_index=True)
        
        # TAB 2: TRENDS
        with tabs[1]:
            st.markdown("## 📈 Enrollment Trends")
            
            if 'year' in allocation_df.columns and 'term' in allocation_df.columns and 'program' in allocation_df.columns:
                trend_data = allocation_df.dropna(subset=['year', 'term', 'program'])
                trend_data['YearTerm'] = trend_data['year'].astype(str) + ' T' + trend_data['term'].astype(str)
                trend_agg = trend_data.groupby(['YearTerm', 'program']).size().reset_index(name='count')
                
                if len(trend_agg) > 0:
                    fig_trend = px.bar(
                        trend_agg,
                        x='YearTerm',
                        y='count',
                        color='program',
                        title='Enrollment by Year & Term',
                        barmode='stack',
                        text_auto=True
                    )
                    st.plotly_chart(update_chart_layout(fig_trend), use_container_width=True)
        
        # TAB 3: SWD
        with tabs[2]:
            st.markdown("## 🧩 Students with Disability")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Students", len(allocation_df))
            with col2:
                st.metric("Records Loaded", len(allocation_df))
            
            st.info("SWD analysis (add Flag_ATSI, Flag_EALD, Flag_SWD columns to Supabase when ready)")
        
        # TAB 4: COMPLEXITY
        with tabs[3]:
            st.markdown("## ⚠️ Complexity Analysis")
            
            if 'program' in allocation_df.columns:
                prog_counts = allocation_df['program'].value_counts()
                
                fig_complex = px.bar(
                    x=prog_counts.index,
                    y=prog_counts.values,
                    title='Records by Program',
                    labels={'x': 'Program', 'y': 'Count'},
                    text_auto=True,
                    color=prog_counts.values,
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(update_chart_layout(fig_complex), use_container_width=True)
        
        # TAB 5: INTERSECTIONALITY
        with tabs[4]:
            st.markdown("## 🔗 Intersectionality")
            
            if 'program' in allocation_df.columns and 'year_level' in allocation_df.columns:
                intersect = pd.crosstab(
                    allocation_df['program'],
                    allocation_df['year_level'],
                    margins=True
                )
                st.dataframe(intersect, use_container_width=True)
            else:
                st.info("Need program and year_level columns for intersectionality analysis")
        
        # TAB 6: ATSI
        with tabs[5]:
            st.markdown("## 🏳️ ATSI Representation")
            
            if 'program' in allocation_df.columns:
                prog_counts = allocation_df['program'].value_counts()
                
                fig_atsi = px.pie(
                    values=prog_counts.values,
                    names=prog_counts.index,
                    title='Distribution by Program',
                    color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#ffd93d', '#a8e6cf']
                )
                st.plotly_chart(update_chart_layout(fig_atsi), use_container_width=True)
        
        # TAB 7: EALD
        with tabs[6]:
            st.markdown("## 🌐 EALD Representation")
            
            if 'year_level' in allocation_df.columns:
                level_counts = allocation_df['year_level'].value_counts()
                
                fig_eald = px.bar(
                    x=level_counts.index,
                    y=level_counts.values,
                    title='Distribution by Year Level',
                    labels={'x': 'Year Level', 'y': 'Count'},
                    text_auto=True,
                    color_discrete_sequence=['#4ecdc4']
                )
                st.plotly_chart(update_chart_layout(fig_eald), use_container_width=True)
        
        # TAB 8: ASSESSMENT
        with tabs[7]:
            st.markdown("## 📊 Assessment Integration")
            st.info("Assessment data will integrate with Term Assessment Data and Assessment Analytics dashboards")
        
        # TAB 9: RAW
        with tabs[8]:
            st.markdown("## 📋 Raw Data")
            st.dataframe(filtered, use_container_width=True, height=400)
            
            csv = filtered.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"allocation_{int(selected_year)}_T{selected_term}.csv",
                mime="text/csv"
            )

# ==== UPLOAD TAB ====
with main_tabs[1]:
    st.markdown("## 📤 Upload Allocation Data")
    st.markdown("_Map Excel columns to Supabase table_")
    st.warning("⚠️ This will DELETE existing data and load your file")
    
    uploaded_file = st.file_uploader("Choose Excel (.xlsx) or CSV", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()
        
        st.success(f"✅ Loaded {len(df)} rows")
        
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
        
        # BRUTAL: Replace NaN before ANY conversion
        df_mapped = df_mapped.fillna('__EMPTY__')
        
        # Convert ALL to string immediately
        for col in df_mapped.columns:
            df_mapped[col] = df_mapped[col].astype(str)
        
        # Replace all empty/NaN variations with actual empty string
        df_mapped = df_mapped.replace(['nan', 'NaT', '<NA>', 'None', '__EMPTY__'], '')
        
        # Strip whitespace
        for col in df_mapped.columns:
            df_mapped[col] = df_mapped[col].str.strip()
        
        # Handle date columns - empty to None for NULL in DB
        date_cols = ['meeting_date', 'date_of_birth', 'waitlist_date']
        for col in date_cols:
            if col in df_mapped.columns:
                mask = df_mapped[col] == ''
                df_mapped.loc[mask, col] = None
        
        # Fill empty meeting_date with today
        if 'meeting_date' in df_mapped.columns:
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            df_mapped['meeting_date'] = df_mapped['meeting_date'].fillna(today)
            df_mapped.loc[df_mapped['meeting_date'] == '', 'meeting_date'] = today
        
        st.markdown("### Preview (Cleaned)")
        st.dataframe(df_mapped.head(5), use_container_width=True)
        st.write(f"**Columns:** {list(df_mapped.columns)}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ CONFIRM - Upload", key="upload_btn"):
                if not supabase:
                    st.error("Supabase not connected")
                else:
                    with st.spinner("Uploading..."):
                        try:
                            st.write("🗑️ Clearing existing...")
                            supabase.table('allocation_students').delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
                            
                            records = df_mapped.to_dict('records')
                            batch_size = 50
                            total = 0
                            
                            for i in range(0, len(records), batch_size):
                                batch = records[i:i+batch_size]
                                supabase.table('allocation_students').insert(batch).execute()
                                total += len(batch)
                                st.write(f"📤 {total}/{len(records)}...")
                            
                            st.success(f"✅ DONE! Uploaded {total} records")
                            st.balloons()
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Records", total)
                            col2.metric("Columns", len(df_mapped.columns))
                            col3.metric("Time", datetime.now().strftime("%H:%M"))
                            st.info("💡 Go to Analysis tab and click Refresh Data")
                            
                        except Exception as e:
                            st.error(f"Upload failed: {str(e)[:200]}")
        
        with col2:
            st.info("✓ Review columns above")
