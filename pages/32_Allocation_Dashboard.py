"""
CLC-LBU ALLOCATION DASHBOARD - AUTO-DETECTING
Works with any column names
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os

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
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(26, 122, 122, 0.1) 100%) !important;
        border: 1px solid rgba(0, 229, 255, 0.4) !important;
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
    """Find column by keywords"""
    for col in df.columns:
        if any(kw.lower() in col.lower() for kw in keywords):
            return col
    return None

def main():
    st.markdown("# 📊 CLC-LBU ALLOCATION DASHBOARD")
    st.markdown("_Student placement analysis and equity insights_")
    
    allocation_df = load_allocation_data()
    
    if allocation_df is None or allocation_df.empty:
        st.warning("⚠️ No data found")
        return
    
    # AUTO-DETECT COLUMNS
    year_col = find_column(allocation_df, ['year', 'referral_year'])
    term_col = find_column(allocation_df, ['term'])
    prog_col = find_column(allocation_df, ['program', 'allocated'])
    
    st.write(f"**DEBUG:** Year={year_col}, Term={term_col}, Program={prog_col}")
    
    if not all([year_col, term_col, prog_col]):
        st.error(f"Missing columns. Available: {list(allocation_df.columns)}")
        return
    
    st.markdown("---")
    
    # FILTERS
    st.markdown("## 🔍 Filters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        years = sorted(allocation_df[year_col].dropna().unique())
        selected_year = st.selectbox("Year", years)
    
    with col2:
        terms = sorted(allocation_df[allocation_df[year_col] == selected_year][term_col].dropna().unique())
        selected_term = st.selectbox("Term", terms)
    
    with col3:
        progs = ['All'] + sorted([p for p in allocation_df[prog_col].dropna().unique() if pd.notna(p)])
        selected_program = st.selectbox("Program", progs)
    
    # FILTER DATA
    filtered = allocation_df[
        (allocation_df[year_col] == selected_year) &
        (allocation_df[term_col] == selected_term)
    ]
    
    if selected_program != 'All':
        filtered = filtered[filtered[prog_col] == selected_program]
    
    st.info(f"✅ Showing {len(filtered)} students")
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📍 Placement", "📈 Trends", "🧩 SWD", "⚠️ Complexity", 
        "🔗 Intersect", "🏳️ ATSI", "🌐 EALD", "📊 Assessment", "📋 Raw"
    ])
    
    # TAB 1: PLACEMENT
    with tab1:
        st.markdown("## Placement Data by Program")
        prog_counts = allocation_df[prog_col].value_counts().sort_values(ascending=True)
        fig = px.bar(x=prog_counts.values, y=prog_counts.index, orientation='h', text_auto=True, 
                     title='Total Enrollments by Program')
        fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                         font=dict(color='#ffffff'), height=350)
        st.plotly_chart(fig, use_container_width=True)
        
        # By program breakdown
        st.markdown("### Demographic Breakdown")
        progs_list = sorted([p for p in allocation_df[prog_col].dropna().unique() if pd.notna(p)])
        cols = st.columns(len(progs_list))
        for idx, prog in enumerate(progs_list):
            prog_data = allocation_df[allocation_df[prog_col] == prog]
            with cols[idx]:
                st.markdown(f"#### {prog}")
                st.metric("Total", len(prog_data))
                atsi = len(prog_data[prog_data['Flag_ATSI'] == 'Yes'])
                st.metric("ATSI", f"{atsi} ({atsi*100//len(prog_data)}%)" if len(prog_data) > 0 else "0")
    
    # TAB 2: TRENDS
    with tab2:
        st.markdown("## Enrollment Trends")
        trend_df = allocation_df.dropna(subset=[year_col, term_col, prog_col]).copy()
        trend_df['YearTerm'] = trend_df[year_col].astype(str) + ' T' + trend_df[term_col].astype(str)
        trend_data = trend_df.groupby(['YearTerm', prog_col]).size().reset_index(name='Count')
        fig = px.line(trend_data, x='YearTerm', y='Count', color=prog_col, markers=True, title='Enrollment Over Time')
        fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                         font=dict(color='#ffffff'), height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 3: SWD
    with tab3:
        st.markdown("## SWD Breakdown")
        swd_data = allocation_df[allocation_df['Flag_SWD'] == 'Yes'].copy()
        if len(swd_data) > 0:
            swd_data['Type'] = swd_data.apply(
                lambda r: 'ASD+ADHD' if r.get('Flag_ASD')=='Yes' and r.get('Flag_ADHD')=='Yes'
                else 'ASD' if r.get('Flag_ASD')=='Yes'
                else 'ADHD' if r.get('Flag_ADHD')=='Yes'
                else 'Other', axis=1
            )
            swd_by_prog = swd_data.groupby([prog_col, 'Type']).size().reset_index(name='Count')
            fig = px.bar(swd_by_prog, x=prog_col, y='Count', color='Type', barmode='stack', text_auto=True)
            fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                             font=dict(color='#ffffff'), height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 4: COMPLEXITY
    with tab4:
        st.markdown("## Complexity (Multiple Needs)")
        allocation_df['needs'] = (
            (allocation_df['Flag_SWD']=='Yes').astype(int) +
            (allocation_df['Flag_ATSI']=='Yes').astype(int) +
            (allocation_df['Flag_EALD']=='Yes').astype(int)
        )
        complexity = allocation_df.groupby(prog_col)['needs'].apply(lambda x: (x>1).sum()).reset_index(name='Multiple_Needs')
        complexity['Total'] = allocation_df.groupby(prog_col).size().values
        fig = px.bar(complexity, x=prog_col, y='Multiple_Needs', text_auto=True, title='Students with Multiple Needs')
        fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)',
                         font=dict(color='#ffffff'), height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 5: INTERSECTIONALITY
    with tab5:
        st.markdown("## Intersectionality")
        progs_list = sorted([p for p in allocation_df[prog_col].dropna().unique() if pd.notna(p)])
        data = []
        for prog in progs_list:
            prog_data = allocation_df[allocation_df[prog_col] == prog]
            data.append({
                'Program': prog,
                'ATSI+SWD': len(prog_data[(prog_data['Flag_ATSI']=='Yes') & (prog_data['Flag_SWD']=='Yes')]),
                'EALD+SWD': len(prog_data[(prog_data['Flag_EALD']=='Yes') & (prog_data['Flag_SWD']=='Yes')]),
                'All 3': len(prog_data[(prog_data['Flag_ATSI']=='Yes') & (prog_data['Flag_EALD']=='Yes') & (prog_data['Flag_SWD']=='Yes')])
            })
        intersect_df = pd.DataFrame(data)
        fig = px.imshow(intersect_df.set_index('Program').T, text_auto=True, color_continuous_scale='YlOrRd')
        fig.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'))
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 6: ATSI
    with tab6:
        st.markdown("## ATSI Representation")
        atsi_by_prog = allocation_df.groupby(prog_col).apply(lambda x: (x['Flag_ATSI']=='Yes').sum()).reset_index(name='Count')
        fig = px.pie(atsi_by_prog, values='Count', names=prog_col, title='ATSI by Program')
        fig.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'))
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 7: EALD
    with tab7:
        st.markdown("## EALD Representation")
        eald_by_prog = allocation_df.groupby(prog_col).apply(lambda x: (x['Flag_EALD']=='Yes').sum()).reset_index(name='Count')
        fig = px.pie(eald_by_prog, values='Count', names=prog_col, title='EALD by Program')
        fig.update_layout(paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'))
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 8: ASSESSMENT
    with tab8:
        st.markdown("## Assessment Data")
        st.info("Assessment data integration coming soon")
    
    # TAB 9: RAW
    with tab9:
        st.markdown("## Raw Data")
        st.dataframe(filtered, use_container_width=True)
        csv = filtered.to_csv(index=False)
        st.download_button("📥 Download CSV", csv, "data.csv", "text/csv")

if __name__ == "__main__":
    main()
