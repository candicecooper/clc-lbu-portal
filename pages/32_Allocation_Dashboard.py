"""
CLC-LBU ALLOCATION DASHBOARD - ENHANCED WITH DATA UPLOAD
Strategic analysis with upload functionality integrated
Page name: 32_Allocation_Dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
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
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(26,122,122,0.1) 100%) !important;
        border: 1px solid rgba(0,229,255,0.4) !important;
    }
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
            df = pd.DataFrame(response.data)
            for col in ['Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Flag_ADHD']:
                if col not in df.columns:
                    df[col] = 'No'
            return df
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def find_column(df, keywords):
    for col in df.columns:
        if any(kw.lower() in col.lower() for kw in keywords):
            return col
    return None

def main():
    st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
    st.markdown("_Strategic student placement analysis and equity insights_")
    
    # TABS: Upload vs Analysis
    main_tabs = st.tabs(["📊 Analysis", "📤 Upload Data"])
    
    # ========================================================================
    # TAB 1: ANALYSIS
    # ========================================================================
    
    with main_tabs[0]:
        allocation_df = load_allocation_data()
        
        if allocation_df is None or allocation_df.empty:
            st.warning("⚠️ No data found. Go to **📤 Upload Data** tab to load allocation data.")
            return
        
        year_col = find_column(allocation_df, ['year', 'referral_year'])
        term_col = find_column(allocation_df, ['term'])
        prog_col = find_column(allocation_df, ['program', 'allocated'])
        
        if not all([year_col, term_col, prog_col]):
            st.error(f"Missing columns. Available: {list(allocation_df.columns)}")
            return
        
        st.markdown("---")
        
        # FILTERS
        st.markdown("## 🔍 Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            years = sorted(allocation_df[year_col].dropna().unique())
            selected_year = st.selectbox("📅 Year", years)
        
        with col2:
            terms = sorted(allocation_df[allocation_df[year_col] == selected_year][term_col].dropna().unique())
            selected_term = st.selectbox("📋 Term", terms)
        
        with col3:
            progs = ['All'] + sorted([p for p in allocation_df[prog_col].dropna().unique() if pd.notna(p)])
            selected_program = st.selectbox("🎓 Program", progs)
        
        with col4:
            st.metric("📊 Total Loaded", len(allocation_df), label_visibility="collapsed")
        
        # FILTER DATA
        filtered = allocation_df[
            (allocation_df[year_col] == selected_year) &
            (allocation_df[term_col] == selected_term)
        ]
        
        if selected_program != 'All':
            filtered = filtered[filtered[prog_col] == selected_program]
        
        st.info(f"✅ **{len(filtered)} students** | {selected_year} T{selected_term} | {selected_program}")
        st.markdown("---")
        
        # ANALYSIS TABS
        tabs = st.tabs([
            "📍 Placement", "📈 Trends", "🧩 SWD", "⚠️ Complexity", 
            "🔗 Intersect", "🏳️ ATSI", "🌐 EALD", "📊 Assessment", "📋 Raw"
        ])
        
        # TAB 1: PLACEMENT
        with tabs[0]:
            st.markdown("## 📍 Placement Data by Program")
            
            prog_counts = allocation_df[prog_col].value_counts().reset_index()
            prog_counts.columns = [prog_col, 'Count']
            
            fig_sun = px.sunburst(
                prog_counts,
                labels=prog_col,
                values='Count',
                title='Program Distribution',
                color='Count',
                color_continuous_scale='Viridis'
            )
            fig_sun.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                                 font=dict(color='#ffffff'), height=450)
            st.plotly_chart(fig_sun, use_container_width=True)
            
            st.markdown("### Demographic Breakdown")
            progs_list = sorted([p for p in allocation_df[prog_col].dropna().unique() if pd.notna(p)])
            
            breakdown_data = []
            for prog in progs_list:
                prog_data = allocation_df[allocation_df[prog_col] == prog]
                total = len(prog_data)
                breakdown_data.append({
                    'Program': prog,
                    'Total': total,
                    'ATSI': len(prog_data[prog_data['Flag_ATSI'] == 'Yes']),
                    'EALD': len(prog_data[prog_data['Flag_EALD'] == 'Yes']),
                    'SWD': len(prog_data[prog_data['Flag_SWD'] == 'Yes'])
                })
            
            breakdown_df = pd.DataFrame(breakdown_data)
            
            fig_breakdown = px.bar(
                breakdown_df,
                x='Program',
                y=['Total', 'ATSI', 'EALD', 'SWD'],
                barmode='group',
                title='Student Distribution by Program & Equity Group',
                color_discrete_map={'Total': '#00e5ff', 'ATSI': '#ff6b6b', 'EALD': '#4ecdc4', 'SWD': '#ffd93d'}
            )
            fig_breakdown.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                                       font=dict(color='#ffffff'), height=400, hovermode='x unified')
            st.plotly_chart(fig_breakdown, use_container_width=True)
            
            st.dataframe(breakdown_df, use_container_width=True)
        
        # TAB 2: TRENDS
        with tabs[1]:
            st.markdown("## 📈 Enrollment Trends")
            
            trend_df = allocation_df.dropna(subset=[year_col, term_col, prog_col]).copy()
            trend_df['YearTerm'] = trend_df[year_col].astype(str) + ' T' + trend_df[term_col].astype(str)
            trend_data = trend_df.groupby(['YearTerm', year_col, term_col, prog_col]).size().reset_index(name='Count')
            trend_data = trend_data.sort_values([year_col, term_col])
            
            fig_line = px.line(
                trend_data,
                x='YearTerm',
                y='Count',
                color=prog_col,
                markers=True,
                title='Enrollment Trend by Program',
                line_shape='spline'
            )
            fig_line.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                                  font=dict(color='#ffffff'), height=450, hovermode='x unified')
            fig_line.update_traces(mode='lines+markers', marker=dict(size=10))
            st.plotly_chart(fig_line, use_container_width=True)
        
        # TAB 3: SWD
        with tabs[2]:
            st.markdown("## 🧩 Students with Disability Breakdown")
            
            swd_data = allocation_df[allocation_df['Flag_SWD'] == 'Yes'].copy()
            if len(swd_data) > 0:
                swd_data['Type'] = swd_data.apply(
                    lambda r: 'ASD + ADHD' if r.get('Flag_ASD')=='Yes' and r.get('Flag_ADHD')=='Yes'
                    else 'ASD Only' if r.get('Flag_ASD')=='Yes'
                    else 'ADHD Only' if r.get('Flag_ADHD')=='Yes'
                    else 'Other', axis=1
                )
                
                swd_by_prog = swd_data.groupby([prog_col, 'Type']).size().reset_index(name='Count')
                
                fig_swd = px.bar(
                    swd_by_prog,
                    x=prog_col,
                    y='Count',
                    color='Type',
                    barmode='stack',
                    title='SWD Students by Disability Type & Program',
                    text_auto=True,
                    color_discrete_map={'ASD Only': '#ff6b6b', 'ADHD Only': '#4ecdc4', 'ASD + ADHD': '#ffd93d', 'Other': '#a8e6cf'}
                )
                fig_swd.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                                     font=dict(color='#ffffff'), height=400)
                st.plotly_chart(fig_swd, use_container_width=True)
                
                col1, col2, col3, col4 = st.columns(4)
                asd_only = len(swd_data[(swd_data['Flag_ASD']=='Yes') & (swd_data['Flag_ADHD']!='Yes')])
                adhd_only = len(swd_data[(swd_data['Flag_ADHD']=='Yes') & (swd_data['Flag_ASD']!='Yes')])
                both = len(swd_data[(swd_data['Flag_ASD']=='Yes') & (swd_data['Flag_ADHD']=='Yes')])
                other = len(swd_data) - asd_only - adhd_only - both
                
                col1.metric("🧠 ASD Only", asd_only)
                col2.metric("⚡ ADHD Only", adhd_only)
                col3.metric("🔗 Both", both)
                col4.metric("📌 Other", other)
            else:
                st.info("No SWD students in selection")
        
        # TAB 4: COMPLEXITY
        with tabs[3]:
            st.markdown("## ⚠️ Complexity - Multiple Needs")
            
            allocation_df['needs'] = (
                (allocation_df['Flag_SWD']=='Yes').astype(int) +
                (allocation_df['Flag_ATSI']=='Yes').astype(int) +
                (allocation_df['Flag_EALD']=='Yes').astype(int)
            )
            
            complexity_prog = allocation_df.groupby(prog_col)['needs'].apply(lambda x: (x>1).sum()).reset_index(name='Multiple')
            complexity_prog['Total'] = allocation_df.groupby(prog_col).size().values
            complexity_prog['Pct'] = (complexity_prog['Multiple'] / complexity_prog['Total'] * 100).round(1)
            
            fig_complex = px.bar(
                complexity_prog,
                x=prog_col,
                y='Multiple',
                color='Pct',
                text_auto=True,
                title='Students with Multiple Needs by Program',
                color_continuous_scale='Reds'
            )
            fig_complex.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                                     font=dict(color='#ffffff'), height=400)
            st.plotly_chart(fig_complex, use_container_width=True)
            
            st.dataframe(complexity_prog, use_container_width=True)
        
        # TAB 5: INTERSECTIONALITY
        with tabs[4]:
            st.markdown("## 🔗 Intersectionality")
            
            progs_list = sorted([p for p in allocation_df[prog_col].dropna().unique() if pd.notna(p)])
            data = []
            for prog in progs_list:
                prog_data = allocation_df[allocation_df[prog_col] == prog]
                data.append({
                    'Program': prog,
                    'ATSI+SWD': len(prog_data[(prog_data['Flag_ATSI']=='Yes') & (prog_data['Flag_SWD']=='Yes')]),
                    'EALD+SWD': len(prog_data[(prog_data['Flag_EALD']=='Yes') & (prog_data['Flag_SWD']=='Yes')]),
                    'ATSI+EALD': len(prog_data[(prog_data['Flag_ATSI']=='Yes') & (prog_data['Flag_EALD']=='Yes')]),
                    'All 3': len(prog_data[(prog_data['Flag_ATSI']=='Yes') & (prog_data['Flag_EALD']=='Yes') & (prog_data['Flag_SWD']=='Yes')])
                })
            
            intersect_df = pd.DataFrame(data)
            
            fig_heat = px.imshow(
                intersect_df.set_index('Program').T,
                text_auto=True,
                color_continuous_scale='YlOrRd',
                title='Students with Overlapping Needs',
            )
            fig_heat.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=400)
            st.plotly_chart(fig_heat, use_container_width=True)
            
            st.dataframe(intersect_df, use_container_width=True)
        
        # TAB 6: ATSI
        with tabs[5]:
            st.markdown("## 🏳️ ATSI Representation")
            
            atsi_by_prog = allocation_df.groupby(prog_col).apply(lambda x: (x['Flag_ATSI']=='Yes').sum()).reset_index(name='Count')
            atsi_by_prog['Total'] = allocation_df.groupby(prog_col).size().values
            
            fig_atsi = px.pie(
                atsi_by_prog,
                values='Count',
                names=prog_col,
                title='ATSI Students by Program',
                color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#ffd93d']
            )
            fig_atsi.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=450)
            st.plotly_chart(fig_atsi, use_container_width=True)
            
            st.dataframe(atsi_by_prog, use_container_width=True)
        
        # TAB 7: EALD
        with tabs[6]:
            st.markdown("## 🌐 EALD Representation")
            
            eald_by_prog = allocation_df.groupby(prog_col).apply(lambda x: (x['Flag_EALD']=='Yes').sum()).reset_index(name='Count')
            eald_by_prog['Total'] = allocation_df.groupby(prog_col).size().values
            
            fig_eald = px.pie(
                eald_by_prog,
                values='Count',
                names=prog_col,
                title='EALD Students by Program',
                color_discrete_sequence=['#4ecdc4', '#a8e6cf', '#95e1d3']
            )
            fig_eald.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=450)
            st.plotly_chart(fig_eald, use_container_width=True)
            
            st.dataframe(eald_by_prog, use_container_width=True)
        
        # TAB 8: ASSESSMENT
        with tabs[7]:
            st.markdown("## 📊 Assessment Data")
            st.info("View assessment data in **Assessment Analytics** dashboard")
        
        # TAB 9: RAW
        with tabs[8]:
            st.markdown("## 📋 Raw Data")
            st.dataframe(filtered, use_container_width=True)
            csv = filtered.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, f"allocation_{selected_year}_T{selected_term}.csv", "text/csv")
    
    # ========================================================================
    # TAB 2: DATA UPLOAD
    # ========================================================================
    
    with main_tabs[1]:
        st.markdown("## 📤 Upload Allocation Data")
        st.markdown("_Upload Excel or CSV file to replace existing data_")
        st.warning("**⚠️ WARNING:** This will DELETE all existing data and load your file")
        
        uploaded_file = st.file_uploader(
            "Choose Excel (.xlsx) or CSV file",
            type=['xlsx', 'csv'],
            help="Your allocation data file"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file)
                else:
                    df = pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.stop()
            
            st.success(f"✅ Loaded {len(df)} rows × {len(df.columns)} columns")
            
            st.markdown("### Data Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Add missing columns
            required_cols = ['Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Flag_ADHD']
            missing = [col for col in required_cols if col not in df.columns]
            
            if missing:
                st.info(f"Adding missing columns: {missing}")
                for col in missing:
                    df[col] = 'No'
            
            # Remove id column first (let Supabase auto-generate)
            if 'id' in df.columns:
                df = df.drop('id', axis=1)
            
            df = df.fillna('')
            df = df.astype(str)
            
            st.markdown("### Upload Confirmation")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ CONFIRM - Replace & Upload", key="upload"):
                    if not supabase:
                        st.error("Supabase not connected")
                    else:
                        with st.spinner("Uploading..."):
                            try:
                                # Delete existing
                                st.write("🗑️ Clearing existing data...")
                                supabase.table('allocation_students').delete().neq('id', '').execute()
                                
                                # Upload (id column already removed above)
                                records = df.to_dict('records')
                                batch_size = 100
                                total = 0
                                
                                for i in range(0, len(records), batch_size):
                                    batch = records[i:i+batch_size]
                                    supabase.table('allocation_students').insert(batch).execute()
                                    total += len(batch)
                                    st.write(f"📤 Uploaded {total}/{len(records)}...")
                                
                                st.success(f"✅ DONE! Uploaded {total} records")
                                st.balloons()
                                
                                col1, col2, col3 = st.columns(3)
                                col1.metric("Records", total)
                                col2.metric("Columns", len(df.columns))
                                col3.metric("Time", datetime.now().strftime("%H:%M:%S"))
                                
                                st.info("📊 Go to **📊 Analysis** tab to view data")
                                
                            except Exception as e:
                                st.error(f"Upload failed: {e}")
            
            with col2:
                st.info("Review data above before uploading")

if __name__ == "__main__":
    main()
