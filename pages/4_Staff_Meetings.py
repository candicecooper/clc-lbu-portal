"""
STAFF Meetings - Direct PostgreSQL Connection (Bypasses PostgREST Cache)
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import datetime
import json

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="STAFF Meetings | CLC-LBU", page_icon="👥", layout="wide")

# ══════════════════════════════════════════════════════════════════════════════
# DIRECT POSTGRESQL CONNECTION
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_db_connection():
    """Direct PostgreSQL connection - bypasses PostgREST cache"""
    url = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
    project_id = url.split("//")[1].split(".")[0]
    
    db_password = st.secrets.get("SUPABASE_DB_PASSWORD", "")
    
    if not db_password:
        st.error("⚠️ SUPABASE_DB_PASSWORD not set!")
        st.stop()
    
    conn_string = f"postgresql://postgres.{project_id}:{db_password}@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres"
    
    return psycopg2.connect(conn_string)

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_meetings():
    """Fetch recent staff meetings"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM staff_meetings 
                ORDER BY meeting_date DESC 
                LIMIT 20
            """)
            return cur.fetchall()
    finally:
        conn.close()

def save_meeting(meeting_data):
    """Save or update meeting"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if meeting_data.get('id'):
                # Update
                cur.execute("""
                    UPDATE staff_meetings 
                    SET meeting_date = %s,
                        term = %s,
                        week_number = %s,
                        minute_taker = %s,
                        attendees = %s,
                        apologies = %s,
                        minutes = %s,
                        actions = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                """, (
                    meeting_data['meeting_date'],
                    meeting_data['term'],
                    meeting_data['week_number'],
                    meeting_data['minute_taker'],
                    meeting_data['attendees'],
                    meeting_data['apologies'],
                    meeting_data['minutes'],
                    Json(meeting_data.get('actions', [])),
                    meeting_data['id']
                ))
                conn.commit()
                return meeting_data['id']
            else:
                # Insert
                cur.execute("""
                    INSERT INTO staff_meetings (
                        meeting_date, term, week_number, minute_taker,
                        attendees, apologies, minutes, actions
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    meeting_data['meeting_date'],
                    meeting_data['term'],
                    meeting_data['week_number'],
                    meeting_data['minute_taker'],
                    meeting_data['attendees'],
                    meeting_data['apologies'],
                    meeting_data['minutes'],
                    Json(meeting_data.get('actions', []))
                ))
                conn.commit()
                result = cur.fetchone()
                return result['id']
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

if 'current_staff_meeting_id' not in st.session_state:
    st.session_state.current_staff_meeting_id = None

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("👥 STAFF MEETINGS")
st.caption("Direct PostgreSQL Connection - Bypasses Cache Issues")

st.markdown("---")

# Meeting selector
st.subheader("📅 Select Meeting")

meetings = fetch_meetings()
meeting_options = ["➕ New Meeting"] + [
    f"{m['meeting_date']} - T{m.get('term', '?')} W{m.get('week_number', '?')} - {m.get('minute_taker', 'Unknown')}"
    for m in meetings
]

selected_option = st.selectbox("Choose meeting", options=meeting_options, key="staff_meeting_selector")

if selected_option == "➕ New Meeting":
    selected_record = None
    st.session_state.current_staff_meeting_id = None
else:
    idx = meeting_options.index(selected_option) - 1
    selected_record = meetings[idx]
    st.session_state.current_staff_meeting_id = selected_record['id']

st.markdown("---")

# Meeting form
st.subheader("📋 Meeting Details")

col1, col2, col3 = st.columns(3)

default_date = selected_record['meeting_date'] if selected_record else datetime.date.today()
default_term = selected_record.get('term', '') if selected_record else ''
default_week = selected_record.get('week_number', 1) if selected_record else 1

with col1:
    meeting_date = st.date_input("Date", value=default_date, key="staff_date")

with col2:
    term = st.text_input("Term", value=default_term, placeholder="T1", key="staff_term")

with col3:
    week_number = st.number_input("Week", min_value=1, max_value=11, value=default_week, key="staff_week")

default_minute_taker = selected_record.get('minute_taker', '') if selected_record else ''
minute_taker = st.text_input("Minute Taker", value=default_minute_taker, key="minute_taker")

st.markdown("---")

st.subheader("👥 Attendees")

default_attendees = selected_record.get('attendees', '') if selected_record else ''
attendees = st.text_area("Present", value=default_attendees, height=80, key="attendees")

default_apologies = selected_record.get('apologies', '') if selected_record else ''
apologies = st.text_area("Apologies", value=default_apologies, height=60, key="apologies")

st.markdown("---")

st.subheader("📄 Meeting Minutes")

default_minutes = selected_record.get('minutes', '') if selected_record else ''
minutes = st.text_area("Minutes", value=default_minutes, height=300, key="minutes")

st.markdown("---")

# Save button
if st.button("💾 Save Meeting", type="primary", use_container_width=True):
    meeting_data = {
        'id': st.session_state.current_staff_meeting_id,
        'meeting_date': str(meeting_date),
        'term': term.strip(),
        'week_number': int(week_number),
        'minute_taker': minute_taker.strip(),
        'attendees': attendees.strip(),
        'apologies': apologies.strip(),
        'minutes': minutes.strip(),
        'actions': []
    }
    
    try:
        meeting_id = save_meeting(meeting_data)
        st.success(f"✅ Meeting saved successfully! (ID: {meeting_id})")
        st.session_state.current_staff_meeting_id = meeting_id
        st.rerun()
    except Exception as e:
        st.error(f"⚠️ Failed to save: {e}")

st.markdown("---")
st.caption("🏫 Direct PostgreSQL Connection · Bypasses PostgREST Cache")
