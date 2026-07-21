import streamlit as st
import pandas as pd
import os
from supabase import create_client

st.set_page_config(page_title="Data Recovery - CLC-LBU", page_icon="🛟", layout="wide")

@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_supabase()

st.title("🛟 Allocation Data Recovery")
st.info(
    "This page exists because the Allocation Dashboard's own upload screen only shows up "
    "once data already exists in the table — so if the table is empty, there's no way back "
    "in through the Dashboard itself. This page does the same upload, always available."
)

upload_password = st.text_input(
    "🔐 Enter password to access data upload", type="password",
    help="Same password as the Dashboard's upload section"
)

if upload_password != "secret2026":
    if upload_password:
        st.error("❌ Incorrect password.")
    st.stop()

st.success("✅ Access granted")

try:
    existing_count = len(supabase.table("allocation_students").select("id").execute().data)
    st.caption(f"Current rows in `allocation_students`: {existing_count}")
except Exception as e:
    st.warning(f"Couldn't check current row count: {e}")

st.markdown("---")
st.subheader("📤 Upload Master Excel File")
uploaded_file = st.file_uploader(
    "Choose your CLC_Allocation_Dashboard Excel or CSV file", type=['xlsx', 'csv']
)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)

        # Same column mapping as the Dashboard's own upload, so the result is identical
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

        st.success(f"Ready: {len(df_mapped)} student records parsed from the file")
        with st.expander("Preview parsed data"):
            st.dataframe(df_mapped, use_container_width=True, hide_index=True)

        clear_first = st.checkbox(
            "Clear existing rows in allocation_students before uploading",
            value=(existing_count == 0 if 'existing_count' in dir() else False),
            help="Leave this on if you're restoring after a wipe. Turn it off if you want to add to what's already there."
        )

        if st.button("🚀 Upload Now", type="primary", use_container_width=True):
            with st.spinner("Uploading..."):
                try:
                    if clear_first:
                        supabase.table('allocation_students').delete().gte(
                            'id', '00000000-0000-0000-0000-000000000000'
                        ).execute()

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
                        supabase.table('allocation_students').insert(records[i:i + 50]).execute()

                    st.success(f"✅ Uploaded {len(records)} records! Open the Allocation Dashboard to confirm.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Failed: {str(e)[:300]}")
    except Exception as e:
        st.error(f"Error reading file: {e}")

st.caption("CLC-LBU — Allocation Data Recovery (temporary tool)")
