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
            return pd.DataFrame(response.data)
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
        prog_col = 'program'
        year_col = 'year'
        term_col = 'term'
        
        st.markdown("---")
        
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
        
        st.info(f"✅ **{len(filtered)} records** | {int(selected_year)} T{int(selected_term)}")
        st.markdown("---")
        
        tabs = st.tabs(["📍 Placement", "📈 Trends", "🧩 SWD", "⚠️ Complexity", "🔗 Intersect", "🏳️ ATSI", "🌐 EALD", "Assessment", "Raw"])
        
        with tabs[0]:
            st.markdown("## Placement Data")
            if prog_col in allocation_df.columns:
                prog_counts = allocation_df[prog_col].value_counts().reset_index()
                prog_counts.columns = [prog_col, 'Count']
                fig = px.sunburst(prog_counts, labels=prog_col, values='Count', color='Count', color_continuous_scale='Viridis')
                fig.update_layout(plot_bgcolor='rgba(10,14,39,0.8)', paper_bgcolor='rgba(10,14,39,0.8)', font=dict(color='#ffffff'), height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with tabs[1]:
            st.markdown("## Trends")
            st.info("Trends by year and term")
        
        with tabs[2]:
            st.markdown("## SWD")
            if 'Flag_SWD' in allocation_df.columns:
                swd_count = len(allocation_df[allocation_df['Flag_SWD'] == 'Yes'])
                st.metric("Students with Disability", swd_count)
        
        with tabs[3]:
            st.markdown("## Complexity")
            st.info("Multiple needs analysis")
        
        with tabs[4]:
            st.markdown("## Intersectionality")
            st.info("Overlapping identities")
        
        with tabs[5]:
            st.markdown("## ATSI")
            if 'Flag_ATSI' in allocation_df.columns:
                atsi_count = len(allocation_df[allocation_df['Flag_ATSI'] == 'Yes'])
                st.metric("ATSI Students", atsi_count)
        
        with tabs[6]:
            st.markdown("## EALD")
            if 'Flag_EALD' in allocation_df.columns:
                eald_count = len(allocation_df[allocation_df['Flag_EALD'] == 'Yes'])
                st.metric("EALD Students", eald_count)
        
        with tabs[7]:
            st.markdown("## Assessment Data")
            st.info("View in Assessment Analytics")
        
        with tabs[8]:
            st.markdown("## Raw Data")
            st.dataframe(filtered, use_container_width=True)
            csv = filtered.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, "data.csv", "text/csv")

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
        
        # COLUMN MAPPING: Excel → Supabase
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
            # Equity flags - keep same names
            'Flag_ATSI': 'Flag_ATSI',
            'Flag_EALD': 'Flag_EALD',
            'Flag_SWD': 'Flag_SWD',
            'Flag_ASD': 'Flag_ASD',
            'Flag_ADHD': 'Flag_ADHD',
        }
        
        # RENAME columns
        df_mapped = df.copy()
        for excel_col, supabase_col in column_map.items():
            if excel_col in df_mapped.columns:
                df_mapped = df_mapped.rename(columns={excel_col: supabase_col})
        
        # Keep only mapped columns (drop extra columns)
        df_mapped = df_mapped[[col for col in df_mapped.columns if col in column_map.values()]]
        
        # CLEAN DATA - nuclear option
        df_mapped = df_mapped.fillna('')
        
        # Replace ALL NaN values everywhere with empty string
        df_mapped = df_mapped.astype(str)
        df_mapped = df_mapped.replace('nan', '').replace('NaT', '').replace('<NA>', '')
        
        # Strip whitespace
        df_mapped = df_mapped.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Convert numeric columns to int
        numeric_cols = ['year', 'term', 'extension_weeks', 'total_previous_placements']
        for col in numeric_cols:
            if col in df_mapped.columns:
                df_mapped[col] = pd.to_numeric(df_mapped[col], errors='coerce').fillna(0).astype(int)
        
        # Final NaN check - if any NaN remain, drop those rows
        df_mapped = df_mapped.dropna(how='any')
        
        # Convert everything to string one final time
        df_mapped = df_mapped.astype(str)
        
        st.markdown("### Preview (Mapped)")
        st.dataframe(df_mapped.head(5), use_container_width=True)
        st.write(f"**Columns to upload:** {list(df_mapped.columns)}")
        
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
                            st.info("💡 Refresh to see data in Analysis tab")
                            
                        except Exception as e:
                            st.error(f"Upload failed: {str(e)[:200]}")
        
        with col2:
            st.info("✓ Review columns above")
