import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
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

# Full column mapping — identical to the Meetings Tool's own FIELD_MAP, so a
# restore here produces exactly the same result as if it had been entered
# through the tool directly. Critically, this includes Allocation_Status -> outcome,
# which a previous version of this script was missing (that's why restored
# students weren't showing up as "Allocated" anywhere).
FIELD_MAP = {
    'Current_Status': 'current_status', 'Previous_Referrals': 'previous_referrals',
    'Student_Name': 'student_name', 'DOB': 'date_of_birth', 'Gender': 'gender', 'Year_Level': 'year_level',
    'Referring_School': 'school', 'Referral_Date': 'referral_date', 'Meeting_Date': 'meeting_date',
    'Meeting_Week': 'meeting_week', 'Previously_Referred': 'previously_referred',
    'Allocation_Status': 'outcome', 'Allocated_Program': 'program', 'Placement_Start': 'start_after',
    'Partnership_Area': 'partnership_area', 'Previous_CLC_Placement': 'previous_clc_placement',
    'Previous_Other_LC': 'previous_other_lc', 'Other_LC_Name': 'other_lc_name',
    'Total_Previous_Placements': 'total_previous_placements',
    'Placement_History_Notes': 'placement_history_notes', 'Flag_EALD': 'flag_eald',
    'Flag_ATSI': 'flag_atsi', 'Flag_Attendance_Fulltime': 'flag_attendance_fulltime',
    'Flag_Attendance_Parttime': 'flag_attendance_parttime',
    'Flag_Intervention_Custody_Order': 'flag_intervention_custody_order',
    'Flag_DCP_involvement': 'flag_dcp_involvement', 'Flag_Child_in_care': 'flag_child_in_care',
    'Flag_IESP_Funding_yes': 'flag_iesp_funding_yes', 'Flag_IESP_Funding_no': 'flag_iesp_funding_no',
    'Flag_Category_1': 'flag_category_1', 'Flag_Category_2': 'flag_category_2',
    'Flag_Category_3': 'flag_category_3', 'Flag_Category_4': 'flag_category_4',
    'Flag_Category_5': 'flag_category_5', 'Flag_Category_6': 'flag_category_6',
    'Flag_Category_7': 'flag_category_7', 'Flag_Category_8': 'flag_category_8',
    'Flag_Category_9': 'flag_category_9', 'Flag_9plusRAAP': 'flag_9plusraap', 'Flag_SWD': 'flag_swd',
    'Flag_Speech_and_Lang': 'flag_speech_and_lang', 'Flag_ASD': 'flag_asd',
    'Flag_Intellectual': 'flag_intellectual', 'Flag_Learning_Difficulty': 'flag_learning_difficulty',
    'Flag_Sensory_Processing': 'flag_sensory_processing', 'Flag_ADHD': 'flag_adhd',
    'Flag_ODD': 'flag_odd', 'Flag_PDA': 'flag_pda', 'Flag_Medication': 'flag_medication',
    'Flag_Medical_condition': 'flag_medical_condition',
    'Medical_Condition_Details': 'medical_condition_details', 'Medication_Details': 'medication_details',
    'Bespoke_Placement': 'bespoke_placement', 'Waitlist_Status': 'waitlist_status',
    'Waitlist_Date': 'waitlist_date', 'Allocated_From_Waitlist': 'allocated_from_waitlist',
    'Extension': 'extension', 'Extension_Date': 'extension_date', 'Exit_Reason': 'exit_reason',
    'Transition_Plan': 'transition_plan', 'Notes': 'notes', 'Placement_End': 'finishing_date',
    'Exclusion_End_Date': 'exclusion_end_date',
    'Proposed_Extension_Finish_Date': 'proposed_extension_finish_date',
    'Extension_Weeks': 'extension_weeks', 'Action_owner': 'actioned_by',
    'Actual_Finish_Date': 'actual_finish_date', 'Extended_Placement': 'extended_placement',
    'Referral_Year': 'year', 'Term': 'term', 'Extension_Status': 'extension_status', 'BSE': 'bse',
}
DATE_FIELDS = {
    'date_of_birth', 'referral_date', 'meeting_date', 'start_after', 'waitlist_date',
    'extension_date', 'exit_reason', 'finishing_date', 'exclusion_end_date',
    'proposed_extension_finish_date', 'actual_finish_date',
}
NUMERIC_FIELDS = {'year', 'term', 'extension_weeks', 'total_previous_placements', 'previous_referrals'}

uploaded_file = st.file_uploader("Choose your CLC_Allocation_Dashboard Excel or CSV file", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df.columns = [str(c).strip() for c in df.columns]

        matched_cols = [c for c in df.columns if c in FIELD_MAP]
        st.caption(f"Matched {len(matched_cols)} of {len(df.columns)} columns in your file to known fields.")

        parsed_records = []
        for _, row in df.iterrows():
            record = {}
            for excel_col, db_field in FIELD_MAP.items():
                if excel_col not in df.columns:
                    continue
                val = row[excel_col]
                if pd.isna(val) or val == '':
                    record[db_field] = None
                    continue
                if db_field in DATE_FIELDS:
                    parsed = pd.to_datetime(val, errors='coerce')
                    record[db_field] = parsed.strftime('%Y-%m-%d') if not pd.isna(parsed) else None
                elif db_field in NUMERIC_FIELDS:
                    num = pd.to_numeric(val, errors='coerce')
                    record[db_field] = None if pd.isna(num) else str(int(num))
                else:
                    record[db_field] = str(val).strip()
            if record.get('student_name'):
                if not record.get('term'):
                    record['term'] = "Unknown Term"
                if not record.get('year'):
                    record['year'] = str(datetime.now().year)
                if not record.get('meeting_week'):
                    record['meeting_week'] = f"Unknown Week ({record['term']} {record['year']})"
                if not record.get('meeting_date'):
                    record['meeting_date'] = datetime.now().date().isoformat()
                parsed_records.append(record)

        st.success(f"Ready: {len(parsed_records)} student records parsed from the file")
        with st.expander("Preview parsed data"):
            st.dataframe(pd.DataFrame(parsed_records), use_container_width=True, hide_index=True)

        st.markdown("---")
        mode = st.radio(
            "How should this be applied?",
            [
                "🔄 Update matching students, add new ones (safe — recommended)",
                "🗑️ Wipe everything first, then import fresh",
            ],
            help="The safe option matches by student name: existing students get their info refreshed "
                 "(fixing the missing outcome from before), students not already there get added. "
                 "Nothing already correct in the database (like manually entered students) gets lost."
        )

        if st.button("🚀 Apply", type="primary", use_container_width=True):
            with st.spinner("Working..."):
                errors = []
                if mode.startswith("🗑️"):
                    try:
                        supabase.table('allocation_students').delete().gte(
                            'id', '00000000-0000-0000-0000-000000000000'
                        ).execute()
                    except Exception as e:
                        st.error(f"Couldn't clear existing rows: {str(e)[:300]}")
                        st.stop()

                    inserted = 0
                    for record in parsed_records:
                        try:
                            supabase.table('allocation_students').insert(record).execute()
                            inserted += 1
                        except Exception as e:
                            errors.append((record.get('student_name', '?'), str(e)[:200]))
                    st.success(f"✅ Wiped and re-imported {inserted} of {len(parsed_records)} record(s).")
                else:
                    existing = supabase.table('allocation_students').select('id, student_name').execute().data
                    existing_by_name = {str(r['student_name']).strip().lower(): r['id'] for r in existing if r.get('student_name')}

                    updated, inserted = 0, 0
                    for record in parsed_records:
                        name_key = str(record['student_name']).strip().lower()
                        try:
                            if name_key in existing_by_name:
                                supabase.table('allocation_students').update(record).eq(
                                    'id', existing_by_name[name_key]
                                ).execute()
                                updated += 1
                            else:
                                result = supabase.table('allocation_students').insert(record).execute()
                                inserted += 1
                                if result.data:
                                    existing_by_name[name_key] = result.data[0]['id']
                        except Exception as e:
                            errors.append((record.get('student_name', '?'), str(e)[:200]))

                    st.success(f"✅ Updated {updated} existing student(s), added {inserted} new one(s).")

                if errors:
                    st.error(f"⚠️ {len(errors)} record(s) failed and were skipped — everything else above succeeded:")
                    for name, err in errors:
                        st.write(f"- **{name}**: {err}")
                else:
                    st.balloons()
                st.info("Open the Allocation Dashboard or Meetings Tool to confirm.")
    except Exception as e:
        st.error(f"Error reading file: {e}")

st.caption("CLC-LBU — Allocation Data Recovery (temporary tool)")
