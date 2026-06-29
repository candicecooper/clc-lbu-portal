"""
CLC-LBU ALLOCATION DASHBOARD - STRATEGIC REBUILD
Purpose: Strategic allocation analysis with meaningful insights
- Placement Data by Program
- Enrollment Trends (Terms + Years)
- SWD Disability Breakdown
- Complexity Analysis (Multiple Needs)
- ATSI Representation
- EALD Representation  
- Intersectionality (Multiple Overlaps)
- Assessment Data Integration
Page name: 32_Allocation_Dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import os
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

st.set_page_config(page_title="📊 Allocation Dashboard", page_icon="📊", layout="wide")

# ============================================================================
# THEME - HIGH CONTRAST, READABLE
# ============================================================================

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    h1, h2, h3 {
        color: #00e5ff !important;
        text-shadow: 0 0 15px rgba(0, 229, 255, 0.3) !important;
    }
    
    p, label, span {
        color: #ffffff !important;
    }
    
    [data-testid="stSelectbox"] {
        background: rgba(26, 122, 122, 0.3) !important;
    }
    
    [data-testid="stSelectbox"] label {
        color: #ffffff !important;
    }
    
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(26, 122, 122, 0.1) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.4) !important;
        border-radius: 10px !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(26, 122, 122, 0.2) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    
    .stInfo {
        background: rgba(0, 229, 255, 0.1) !important;
        border-left: 4px solid #00e5ff !important;
        color: #ffffff !important;
    }
    
    .stWarning {
        background: rgba(255, 193, 7, 0.1) !important;
        border-left: 4px solid #FFC107 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SUPABASE CONNECTION
# ============================================================================

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

supabase: Client = init_supabase()

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data
def load_allocation_data():
    """Load allocation data from Supabase"""
    if not supabase:
        return None
    try:
        response = supabase.table('allocation_students').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Ensure columns exist
            for col in ['Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Flag_ADHD']:
                if col not in df.columns:
                    df[col] = 'No'
            return df
        return None
    except Exception as e:
        st.error(f"Error loading allocation data: {e}")
        return None

def load_assessment_data():
    """Load assessment data from Supabase"""
    if not supabase:
        return None
    try:
        response = supabase.table('term_assessments').select('*').execute()
        return response.data if response.data else None
    except:
        return None

# ============================================================================
# MAIN
# ============================================================================

def main():
    st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
    st.markdown("_Strategic analysis of student placements, demographics, and learning progress_")
    
    # Load data
    allocation_df = load_allocation_data()
    assessment_data = load_assessment_data()
    
    if allocation_df is None or allocation_df.empty:
        st.warning("⚠️ No allocation data found. Upload data to get started.")
        return
    
    st.markdown("---")
    
    # ========================================================================
    # FILTERS - CLEAR FEEDBACK
    # ========================================================================
    
    st.markdown("## 🔍 Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_year = st.selectbox(
            "📅 Year",
            sorted(allocation_df['Referral_Year'].unique()),
            help="Select year to view"
        )
    
    with col2:
        selected_term = st.selectbox(
            "📋 Term",
            sorted(allocation_df[allocation_df['Referral_Year'] == selected_year]['Term'].unique()),
            help="Select term within year"
        )
    
    with col3:
        selected_program = st.selectbox(
            "🎓 Program",
            ['All'] + sorted([p for p in allocation_df['Program'].unique() if pd.notna(p)]),
            help="Select program or view all"
        )
    
    with col4:
        st.metric("📊 Total Records Loaded", len(allocation_df), label_visibility="collapsed")
    
    # Filter data
    filtered_df = allocation_df[
        (allocation_df['Referral_Year'] == selected_year) &
        (allocation_df['Term'] == selected_term)
    ]
    
    if selected_program != 'All':
        filtered_df = filtered_df[filtered_df['Program'] == selected_program]
    
    st.info(f"✅ Showing {len(filtered_df)} students | Year: {selected_year} | Term: {selected_term} | Program: {selected_program}")
    
    st.markdown("---")
    
    # ========================================================================
    # TABS - STRATEGIC ANALYSIS
    # ========================================================================
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📍 Placement Data",
        "📈 Enrollment Trends",
        "🧩 SWD Breakdown",
        "⚠️ Complexity",
        "🔗 Intersectionality",
        "🏳️ ATSI",
        "🌐 EALD",
        "📊 Assessment Data",
        "📋 Raw Data"
    ])
    
    # ====================================================================
    # TAB 1: PLACEMENT DATA
    # ====================================================================
    
    with tab1:
        st.markdown("## 📍 Placement Data by Program")
        st.markdown("_Student enrollments across programs with demographic breakdown_")
        
        # Overall enrollment by program
        program_counts = allocation_df['Program'].value_counts().sort_values(ascending=True)
        
        fig_programs = px.barh(
            x=program_counts.values,
            y=program_counts.index,
            labels={'x': 'Number of Students', 'y': 'Program'},
            title='Total Enrollments by Program',
            text_auto=True,
            color=program_counts.values,
            color_continuous_scale='Viridis'
        )
        fig_programs.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#ffffff', size=12),
            height=300,
            showlegend=False
        )
        fig_programs.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
        st.plotly_chart(fig_programs, use_container_width=True)
        
        # Demographic breakdown by program
        st.markdown("### Demographic Breakdown by Program")
        
        programs_list = sorted([p for p in allocation_df['Program'].unique() if pd.notna(p)])
        
        cols = st.columns(len(programs_list))
        
        for idx, program in enumerate(programs_list):
            prog_data = allocation_df[allocation_df['Program'] == program]
            
            with cols[idx]:
                st.markdown(f"#### {program} Program")
                
                total = len(prog_data)
                atsi = len(prog_data[prog_data['Flag_ATSI'] == 'Yes'])
                eald = len(prog_data[prog_data['Flag_EALD'] == 'Yes'])
                swd = len(prog_data[prog_data['Flag_SWD'] == 'Yes'])
                
                st.metric("Total", total)
                st.metric("🏳️ ATSI", f"{atsi} ({atsi*100//total}%)" if total > 0 else "0")
                st.metric("🌐 EALD", f"{eald} ({eald*100//total}%)" if total > 0 else "0")
                st.metric("🧩 SWD", f"{swd} ({swd*100//total}%)" if total > 0 else "0")
        
        st.markdown("---")
        
        # Term patterns within year
        st.markdown("### Enrollment Pattern - Terms Within Year")
        
        year_terms = allocation_df[allocation_df['Referral_Year'] == selected_year].groupby(['Term', 'Program']).size().reset_index(name='Count')
        
        fig_terms = px.bar(
            year_terms,
            x='Term',
            y='Count',
            color='Program',
            barmode='group',
            title=f'Enrollments by Term - {selected_year}',
            labels={'Count': 'Number of Students', 'Term': 'Term'},
            text_auto=True
        )
        fig_terms.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#ffffff'),
            height=400
        )
        fig_terms.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
        st.plotly_chart(fig_terms, use_container_width=True)
    
    # ====================================================================
    # TAB 2: ENROLLMENT TRENDS
    # ====================================================================
    
    with tab2:
        st.markdown("## 📈 Enrollment Trends")
        st.markdown("_How enrollments change across terms and years - identifying patterns and decreases_")
        
        # Create proper time series: Year + Term
        trend_df = allocation_df.groupby(['Referral_Year', 'Term', 'Program']).size().reset_index(name='Count')
        trend_df['YearTerm'] = trend_df['Referral_Year'].astype(str) + ' T' + trend_df['Term'].astype(str)
        trend_df = trend_df.sort_values(['Referral_Year', 'Term'])
        
        fig_trends = px.line(
            trend_df,
            x='YearTerm',
            y='Count',
            color='Program',
            markers=True,
            title='Enrollment Trend Over Time (by Year and Term)',
            labels={'Count': 'Number of Students', 'YearTerm': 'Year & Term'},
            text='Count'
        )
        fig_trends.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#ffffff'),
            height=450,
            hovermode='x unified'
        )
        fig_trends.update_traces(textposition='top center', textfont=dict(color='#ffffff'))
        st.plotly_chart(fig_trends, use_container_width=True)
        
        # Year-on-year comparison
        st.markdown("### Year-on-Year Comparison")
        
        yoy_df = allocation_df.groupby(['Referral_Year', 'Program']).size().reset_index(name='Count')
        
        fig_yoy = px.bar(
            yoy_df,
            x='Referral_Year',
            y='Count',
            color='Program',
            barmode='group',
            title='Annual Enrollments by Program',
            text_auto=True,
            labels={'Count': 'Total Students', 'Referral_Year': 'Year'}
        )
        fig_yoy.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#ffffff'),
            height=400
        )
        fig_yoy.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
        st.plotly_chart(fig_yoy, use_container_width=True)
    
    # ====================================================================
    # TAB 3: SWD BREAKDOWN
    # ====================================================================
    
    with tab3:
        st.markdown("## 🧩 Students with Disability - Breakdown by Type")
        st.markdown("_ASD, ADHD, Both, and Other disabilities across programs_")
        
        swd_df = allocation_df[allocation_df['Flag_SWD'] == 'Yes'].copy()
        
        if len(swd_df) == 0:
            st.info("No SWD students in filtered data")
            return
        
        # Categorize disability types
        swd_df['Disability_Type'] = swd_df.apply(
            lambda row: (
                'ASD + ADHD' if row.get('Flag_ASD') == 'Yes' and row.get('Flag_ADHD') == 'Yes'
                else 'ASD Only' if row.get('Flag_ASD') == 'Yes'
                else 'ADHD Only' if row.get('Flag_ADHD') == 'Yes'
                else 'Other'
            ),
            axis=1
        )
        
        # By program
        swd_by_prog = swd_df.groupby(['Program', 'Disability_Type']).size().reset_index(name='Count')
        
        fig_swd = px.bar(
            swd_by_prog,
            x='Program',
            y='Count',
            color='Disability_Type',
            barmode='stack',
            title='SWD Students by Disability Type & Program',
            text_auto=True,
            labels={'Count': 'Number of Students'}
        )
        fig_swd.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#ffffff'),
            height=400
        )
        fig_swd.update_traces(textposition='inside', textfont=dict(color='#ffffff'))
        st.plotly_chart(fig_swd, use_container_width=True)
        
        # Co-occurrence table
        st.markdown("### Co-occurrence Patterns")
        
        cols = st.columns(3)
        
        asd_only = len(swd_df[(swd_df['Flag_ASD'] == 'Yes') & (swd_df['Flag_ADHD'] != 'Yes')])
        adhd_only = len(swd_df[(swd_df['Flag_ADHD'] == 'Yes') & (swd_df['Flag_ASD'] != 'Yes')])
        both = len(swd_df[(swd_df['Flag_ASD'] == 'Yes') & (swd_df['Flag_ADHD'] == 'Yes')])
        
        with cols[0]:
            st.metric("🧠 ASD Only", asd_only)
        with cols[1]:
            st.metric("⚡ ADHD Only", adhd_only)
        with cols[2]:
            st.metric("🔗 Both ASD+ADHD", both)
    
    # ====================================================================
    # TAB 4: COMPLEXITY
    # ====================================================================
    
    with tab4:
        st.markdown("## ⚠️ Complexity Analysis")
        st.markdown("_Students with multiple needs (multiple disabilities and/or marginalized groups)_")
        
        # Add complexity score
        allocation_df['Needs_Count'] = (
            (allocation_df['Flag_SWD'] == 'Yes').astype(int) +
            (allocation_df['Flag_ATSI'] == 'Yes').astype(int) +
            (allocation_df['Flag_EALD'] == 'Yes').astype(int)
        )
        
        complexity_df = allocation_df[allocation_df['Needs_Count'] > 1]
        
        st.markdown(f"### {len(complexity_df)} students with multiple needs out of {len(allocation_df)} total")
        
        # Breakdown
        cols = st.columns(3)
        with cols[0]:
            st.metric("2 Needs", len(allocation_df[allocation_df['Needs_Count'] == 2]))
        with cols[1]:
            st.metric("3+ Needs", len(allocation_df[allocation_df['Needs_Count'] >= 3]))
        with cols[2]:
            st.metric("No Identified Needs", len(allocation_df[allocation_df['Needs_Count'] == 0]))
        
        # By program
        st.markdown("### Multiple Needs by Program")
        
        complexity_prog = allocation_df.groupby('Program')['Needs_Count'].apply(
            lambda x: (x > 1).sum()
        ).reset_index(name='Multiple_Needs')
        complexity_prog['Total'] = allocation_df.groupby('Program').size().values
        complexity_prog['Percentage'] = (complexity_prog['Multiple_Needs'] / complexity_prog['Total'] * 100).round(1)
        
        fig_complexity = px.bar(
            complexity_prog,
            x='Program',
            y='Multiple_Needs',
            color='Percentage',
            text=['Multiple_Needs'],
            title='Students with Multiple Needs by Program',
            labels={'Multiple_Needs': 'Number of Students'},
            color_continuous_scale='Reds'
        )
        fig_complexity.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#ffffff'),
            height=400
        )
        fig_complexity.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
        st.plotly_chart(fig_complexity, use_container_width=True)
        
        st.dataframe(complexity_prog, use_container_width=True)
    
    # ====================================================================
    # TAB 5: INTERSECTIONALITY
    # ====================================================================
    
    with tab5:
        st.markdown("## 🔗 Intersectionality")
        st.markdown("_Students with overlapping identities - ATSI+SWD, EALD+SWD, etc. (whole people counts)_")
        
        # Create intersectionality matrix - WHOLE NUMBERS only
        programs_list = sorted([p for p in allocation_df['Program'].unique() if pd.notna(p)])
        
        intersect_data = []
        
        for program in programs_list:
            prog_data = allocation_df[allocation_df['Program'] == program]
            
            atsi_swd = len(prog_data[(prog_data['Flag_ATSI'] == 'Yes') & (prog_data['Flag_SWD'] == 'Yes')])
            eald_swd = len(prog_data[(prog_data['Flag_EALD'] == 'Yes') & (prog_data['Flag_SWD'] == 'Yes')])
            atsi_eald = len(prog_data[(prog_data['Flag_ATSI'] == 'Yes') & (prog_data['Flag_EALD'] == 'Yes')])
            atsi_eald_swd = len(prog_data[
                (prog_data['Flag_ATSI'] == 'Yes') & 
                (prog_data['Flag_EALD'] == 'Yes') & 
                (prog_data['Flag_SWD'] == 'Yes')
            ])
            
            intersect_data.append({
                'Program': program,
                'ATSI + SWD': atsi_swd,
                'EALD + SWD': eald_swd,
                'ATSI + EALD': atsi_eald,
                'ATSI + EALD + SWD': atsi_eald_swd
            })
        
        intersect_df = pd.DataFrame(intersect_data)
        
        # Heatmap
        fig_heatmap = px.imshow(
            intersect_df.set_index('Program').T,
            text_auto=True,
            color_continuous_scale='YlOrRd',
            title='Students with Overlapping Needs',
            labels={'color': 'Count'}
        )
        fig_heatmap.update_layout(
            plot_bgcolor='rgba(10, 14, 39, 0.8)',
            paper_bgcolor='rgba(10, 14, 39, 0.8)',
            font=dict(color='#ffffff'),
            height=400
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        st.dataframe(intersect_df, use_container_width=True)
    
    # ====================================================================
    # TAB 6: ATSI
    # ====================================================================
    
    with tab6:
        st.markdown("## 🏳️ ATSI Representation")
        st.markdown("_Aboriginal and Torres Strait Islander student representation across programs_")
        
        atsi_data = allocation_df[allocation_df['Flag_ATSI'] == 'Yes']
        
        if len(atsi_data) == 0:
            st.info("No ATSI students in current data")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                # Overall percentage
                total_atsi = len(atsi_data)
                total_all = len(allocation_df)
                pct_atsi = (total_atsi / total_all * 100)
                
                st.metric("ATSI Students", total_atsi)
                st.metric("Overall %", f"{pct_atsi:.1f}%")
            
            with col2:
                # By program
                atsi_by_prog = allocation_df.groupby('Program').apply(
                    lambda x: (x['Flag_ATSI'] == 'Yes').sum()
                ).reset_index(name='ATSI_Count')
                atsi_by_prog['Total'] = allocation_df.groupby('Program').size().values
                atsi_by_prog['Percentage'] = (atsi_by_prog['ATSI_Count'] / atsi_by_prog['Total'] * 100).round(1)
                
                fig_atsi = px.pie(
                    atsi_by_prog,
                    values='ATSI_Count',
                    names='Program',
                    title='ATSI Students by Program',
                    text='ATSI_Count'
                )
                fig_atsi.update_layout(
                    plot_bgcolor='rgba(10, 14, 39, 0.8)',
                    paper_bgcolor='rgba(10, 14, 39, 0.8)',
                    font=dict(color='#ffffff')
                )
                st.plotly_chart(fig_atsi, use_container_width=True)
            
            st.dataframe(atsi_by_prog, use_container_width=True)
    
    # ====================================================================
    # TAB 7: EALD
    # ====================================================================
    
    with tab7:
        st.markdown("## 🌐 EALD Representation")
        st.markdown("_English as Additional Language or Dialect student representation_")
        
        eald_data = allocation_df[allocation_df['Flag_EALD'] == 'Yes']
        
        if len(eald_data) == 0:
            st.info("No EALD students in current data")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                total_eald = len(eald_data)
                total_all = len(allocation_df)
                pct_eald = (total_eald / total_all * 100)
                
                st.metric("EALD Students", total_eald)
                st.metric("Overall %", f"{pct_eald:.1f}%")
            
            with col2:
                eald_by_prog = allocation_df.groupby('Program').apply(
                    lambda x: (x['Flag_EALD'] == 'Yes').sum()
                ).reset_index(name='EALD_Count')
                eald_by_prog['Total'] = allocation_df.groupby('Program').size().values
                eald_by_prog['Percentage'] = (eald_by_prog['EALD_Count'] / eald_by_prog['Total'] * 100).round(1)
                
                fig_eald = px.pie(
                    eald_by_prog,
                    values='EALD_Count',
                    names='Program',
                    title='EALD Students by Program',
                    text='EALD_Count'
                )
                fig_eald.update_layout(
                    plot_bgcolor='rgba(10, 14, 39, 0.8)',
                    paper_bgcolor='rgba(10, 14, 39, 0.8)',
                    font=dict(color='#ffffff')
                )
                st.plotly_chart(fig_eald, use_container_width=True)
            
            st.dataframe(eald_by_prog, use_container_width=True)
    
    # ====================================================================
    # TAB 8: ASSESSMENT DATA
    # ====================================================================
    
    with tab8:
        st.markdown("## 📊 Assessment Data Integration")
        st.markdown("_Student learning progress by program_")
        
        if assessment_data:
            assessment_df = pd.DataFrame(assessment_data)
            
            # Collate by program
            programs_list = sorted([p for p in assessment_df['program'].unique() if pd.notna(p)])
            
            for program in programs_list:
                prog_assess = assessment_df[assessment_df['program'] == program]
                
                st.markdown(f"### {program} Program")
                
                cols = st.columns(3)
                with cols[0]:
                    st.metric("📝 Entries", len(prog_assess))
                with cols[1]:
                    st.metric("👥 Staff", prog_assess['staff_member'].nunique())
                with cols[2]:
                    latest = prog_assess['date_submitted'].max() if 'date_submitted' in prog_assess.columns else 'N/A'
                    st.metric("📅 Latest", latest)
                
                st.divider()
        else:
            st.info("No assessment data available yet")
    
    # ====================================================================
    # TAB 9: RAW DATA
    # ====================================================================
    
    with tab9:
        st.markdown("## 📋 Raw Data")
        
        st.dataframe(filtered_df, use_container_width=True)
        
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"allocation_data_{selected_year}_T{selected_term}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
