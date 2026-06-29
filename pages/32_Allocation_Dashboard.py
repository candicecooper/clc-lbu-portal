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
    h1, h2, h3 { color: #00e5ff !important; }
    p, label, span { color: #ffffff !important; }
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
    except:
        return None

def find_column(df, keywords):
    for col in df.columns:
        if any(kw.lower() in col.lower() for kw in keywords):
            return col
    return None

st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
st.markdown("_Strategic student placement analysis and equity insights_")

main_tabs = st.tabs(["📊 Analysis", "📤 Upload Data"])

# ==== ANALYSIS TAB ====
with main_tabs[0]:
    allocation_df = load_allocation_data()
    
    if allocation_df is None or allocation_df.empty:
        st.warning("⚠️ No data found. Go to **📤 Upload Data** tab to load data.")
    else:
        year_col = find_column(allocation_df, ['year', 'referral_year'])
        term_col = find_column(allocation_df, ['term'])
        prog_col = find_column(allocation_df, ['program', 'allocated'])
        
        if not all([year_col, term_col, prog_col]):
            st.error(f"Missing columns: {list(allocation_df.columns)}")
        else:
            st.markdown("---")
            
            # FILTERS
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                years = sorted(allocation_df[year_col].dropna().unique())
                selected_year = st.selectbox("Year", years)
            with col2:
                terms = sorted(allocation_df[allocation_df[year_col] == selected_year][term_col].dropna().unique())
                selected_term = st.selectbox("Term", terms)
            with col3:
                progs = ['All'] + sorted([p for p in allocation_df[prog_col].dropna().unique() if pd.notna(p)])
                selected_program = st.selectbox("Program", progs)
            with col4:
                st.metric("Total", len(allocation_df), label_visibility="collapsed")
            
            filtered = allocation_df[
                (allocation_df[year_col] == selected_year) &
                (allocation_df[term_col] == selected_term)
            ]
            if selected_program != 'All':
                filtered = filtered[filtered[prog_col] == selected_program]
            
            st.info(f"✅ **{len(filtered)} students** | {selected_year} T{selected_term}")
            st.markdown("---")
            
            tabs = st.tabs(["📍 Placement", "📈 Trends", "🧩 SWD", "⚠️ Complexity", "🔗 Intersect", "🏳️ ATSI", "🌐 EALD", "Assessment", "Raw"])
            
            with tabs[0]:
                st.markdown("## Placement Data")
                prog_counts = allocation_df[prog_col].value_counts().reset_index()
                prog_counts.columns = [prog_col, 'Count']
                fig = px.sunburst(prog_counts, labels=prog_col, values='Count', color='Count', color_continuous_scale='Viridis')
                fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                breakdown = []
                for prog in sorted([p for p in allocation_df[prog_col].unique() if pd.notna(p)]):
                    p_data = allocation_df[allocation_df[prog_col] == prog]
                    breakdown.append({'Program': prog, 'Total': len(p_data), 'ATSI': len(p_data[p_data['Flag_ATSI']=='Yes']), 'EALD': len(p_data[p_data['Flag_EALD']=='Yes']), 'SWD': len(p_data[p_data['Flag_SWD']=='Yes'])})
                st.dataframe(pd.DataFrame(breakdown), use_container_width=True)
            
            with tabs[1]:
                st.markdown("## Trends")
                trend = allocation_df.dropna(subset=[year_col, term_col, prog_col]).copy()
                trend['YT'] = trend[year_col].astype(str) + ' T' + trend[term_col].astype(str)
                tdata = trend.groupby(['YT', prog_col]).size().reset_index(name='Count')
                fig = px.line(tdata, x='YT', y='Count', color=prog_col, markers=True, line_shape='spline')
                fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with tabs[2]:
                st.markdown("## SWD Breakdown")
                swd = allocation_df[allocation_df['Flag_SWD']=='Yes'].copy()
                if len(swd) > 0:
                    swd['Type'] = swd.apply(lambda r: 'ASD+ADHD' if r.get('Flag_ASD')=='Yes' and r.get('Flag_ADHD')=='Yes' else 'ASD' if r.get('Flag_ASD')=='Yes' else 'ADHD' if r.get('Flag_ADHD')=='Yes' else 'Other', axis=1)
                    sdata = swd.groupby([prog_col, 'Type']).size().reset_index(name='Count')
                    fig = px.bar(sdata, x=prog_col, y='Count', color='Type', barmode='stack', text_auto=True)
                    fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=350)
                    st.plotly_chart(fig, use_container_width=True)
            
            with tabs[3]:
                st.markdown("## Complexity")
                allocation_df['needs'] = ((allocation_df['Flag_SWD']=='Yes').astype(int) + (allocation_df['Flag_ATSI']=='Yes').astype(int) + (allocation_df['Flag_EALD']=='Yes').astype(int))
                cdata = allocation_df.groupby(prog_col)['needs'].apply(lambda x: (x>1).sum()).reset_index(name='Multiple')
                cdata['Total'] = allocation_df.groupby(prog_col).size().values
                fig = px.bar(cdata, x=prog_col, y='Multiple', color='Total', text_auto=True, color_continuous_scale='Reds')
                fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with tabs[4]:
                st.markdown("## Intersectionality")
                progs_list = sorted([p for p in allocation_df[prog_col].unique() if pd.notna(p)])
                idata = []
                for p in progs_list:
                    pd_data = allocation_df[allocation_df[prog_col] == p]
                    idata.append({'Program': p, 'ATSI+SWD': len(pd_data[(pd_data['Flag_ATSI']=='Yes') & (pd_data['Flag_SWD']=='Yes')]), 'EALD+SWD': len(pd_data[(pd_data['Flag_EALD']=='Yes') & (pd_data['Flag_SWD']=='Yes')])})
                idf = pd.DataFrame(idata)
                fig = px.imshow(idf.set_index('Program').T, text_auto=True, color_continuous_scale='YlOrRd')
                fig.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with tabs[5]:
                st.markdown("## ATSI")
                atsi = allocation_df.groupby(prog_col).apply(lambda x: (x['Flag_ATSI']=='Yes').sum()).reset_index(name='Count')
                fig = px.pie(atsi, values='Count', names=prog_col, color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#ffd93d'])
                fig.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with tabs[6]:
                st.markdown("## EALD")
                eald = allocation_df.groupby(prog_col).apply(lambda x: (x['Flag_EALD']=='Yes').sum()).reset_index(name='Count')
                fig = px.pie(eald, values='Count', names=prog_col, color_discrete_sequence=['#4ecdc4', '#a8e6cf', '#95e1d3'])
                fig.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with tabs[7]:
                st.markdown("## Assessment Data")
                st.info("View in Assessment Analytics dashboard")
            
            with tabs[8]:
                st.markdown("## Raw Data")
                st.dataframe(filtered, use_container_width=True)
                csv = filtered.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, f"data_{selected_year}_T{selected_term}.csv", "text/csv")

# ==== UPLOAD TAB ====
with main_tabs[1]:
    st.markdown("## 📤 Upload Allocation Data")
    st.markdown("_Replace existing data with new file_")
    st.warning("⚠️ This will DELETE existing data and load your file")
    
    uploaded_file = st.file_uploader("Choose Excel (.xlsx) or CSV", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()
        
        st.success(f"✅ Loaded {len(df)} rows × {len(df.columns)} columns")
        st.dataframe(df.head(10), use_container_width=True)
        
        required = ['Flag_ATSI', 'Flag_EALD', 'Flag_SWD', 'Flag_ASD', 'Flag_ADHD']
        for col in required:
            if col not in df.columns:
                df[col] = 'No'
        
        if 'id' in df.columns:
            df = df.drop('id', axis=1)
        
        df = df.dropna(axis=1, how='all')
        df = df.where(pd.notna(df), '')
        df = df.astype(str)
        df = df[(df != '').any(axis=1)]
        
        st.markdown("### Preview (Cleaned)")
        st.dataframe(df.head(5), use_container_width=True)
        
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
                            
                            records = df.to_dict('records')
                            batch_size = 100
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
                            col2.metric("Columns", len(df.columns))
                            col3.metric("Time", datetime.now().strftime("%H:%M"))
                            st.info("💡 Refresh to see data in Analysis tab")
                            
                        except Exception as e:
                            st.error(f"Upload failed: {e}")
        
        with col2:
            st.info("✓ Review cleaned data above")
