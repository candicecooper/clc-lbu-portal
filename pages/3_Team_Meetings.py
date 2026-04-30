"""
Team Meetings - Direct PostgreSQL Connection (Bypasses PostgREST Cache)
This version connects directly to PostgreSQL, avoiding the schema cache issue
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import datetime
import json

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Team Meetings | CLC-LBU", page_icon="🗒️", layout="wide")

# ══════════════════════════════════════════════════════════════════════════════
# DIRECT POSTGRESQL CONNECTION (Bypasses PostgREST)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_db_connection():
    """Direct PostgreSQL connection - bypasses PostgREST cache issues"""
    # Get connection string from Supabase URL
    # Format: postgresql://postgres:[password]@[host]:[port]/postgres
    
    # Extract from SUPABASE_URL_MEETINGS
    url = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
    # url is like: https://cmqyrfekxgjdtuloseri.supabase.co
    project_id = url.split("//")[1].split(".")[0]
    
    # Build PostgreSQL connection string
    # You need to add SUPABASE_DB_PASSWORD to your Render environment
    db_password = st.secrets.get("SUPABASE_DB_PASSWORD", "")
    
    if not db_password:
        st.error("⚠️ SUPABASE_DB_PASSWORD not set in environment variables!")
        st.stop()
    
    conn_string = f"postgresql://postgres.{project_id}:{db_password}@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres"
    
    return psycopg2.connect(conn_string)

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_meetings(program):
    """Fetch meetings for a program"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM tm_program_meetings 
                WHERE program = %s 
                ORDER BY meeting_date DESC 
                LIMIT 20
            """, (program,))
            return cur.fetchall()
    finally:
        conn.close()

def save_meeting(meeting_data):
    """Save or update a meeting"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if meeting_data.get('id'):
                # Update existing
                cur.execute("""
                    UPDATE tm_program_meetings 
                    SET program = %s,
                        meeting_date = %s,
                        term = %s,
                        week_number = %s,
                        week_type = %s,
                        facilitator = %s,
                        attendees = %s,
                        meeting_minutes = %s,
                        student_concerns = %s,
                        actions = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                """, (
                    meeting_data['program'],
                    meeting_data['meeting_date'],
                    meeting_data['term'],
                    meeting_data['week_number'],
                    meeting_data['week_type'],
                    meeting_data['facilitator'],
                    meeting_data['attendees'],
                    meeting_data['meeting_minutes'],
                    Json(meeting_data.get('student_concerns', [])),
                    Json(meeting_data.get('actions', [])),
                    meeting_data['id']
                ))
                conn.commit()
                return meeting_data['id']
            else:
                # Insert new
                cur.execute("""
                    INSERT INTO tm_program_meetings (
                        program, meeting_date, term, week_number, week_type,
                        facilitator, attendees, meeting_minutes, student_concerns, actions
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    meeting_data['program'],
                    meeting_data['meeting_date'],
                    meeting_data['term'],
                    meeting_data['week_number'],
                    meeting_data['week_type'],
                    meeting_data['facilitator'],
                    meeting_data['attendees'],
                    meeting_data['meeting_minutes'],
                    Json(meeting_data.get('student_concerns', [])),
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

if 'current_meeting_id' not in st.session_state:
    st.session_state.current_meeting_id = None

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("🗒️ TEAM MEETINGS")
st.caption("Direct PostgreSQL Connection - Bypasses Cache Issues")

# Program selector
program = st.selectbox("Program", options=["JP", "PY", "SY", "SPECIALIST"], key="program_select")

st.markdown("---")

# Meeting selector
st.subheader("📅 Select Meeting")

meetings = fetch_meetings(program)
meeting_options = ["➕ New Meeting"] + [
    f"{m['meeting_date']} - T{m.get('term', '?')} W{m.get('week_number', '?')}"
    for m in meetings
]

selected_option = st.selectbox("Choose meeting", options=meeting_options, key="meeting_selector")

if selected_option == "➕ New Meeting":
    selected_record = None
    st.session_state.current_meeting_id = None
else:
    idx = meeting_options.index(selected_option) - 1
    selected_record = meetings[idx]
    st.session_state.current_meeting_id = selected_record['id']

st.markdown("---")

# Meeting form
st.subheader("📋 Meeting Details")

col1, col2, col3, col4 = st.columns(4)

default_date = selected_record['meeting_date'] if selected_record else datetime.date.today()
default_term = selected_record.get('term', '') if selected_record else ''
default_week = selected_record.get('week_number', 1) if selected_record else 1
default_week_type = selected_record.get('week_type', 'A') if selected_record else 'A'

with col1:
    meeting_date = st.date_input("Date", value=default_date, key="date")

with col2:
    term = st.text_input("Term", value=default_term, placeholder="T1", key="term")

with col3:
    week_number = st.number_input("Week", min_value=1, max_value=11, value=default_week, key="week")

with col4:
    week_type = st.selectbox("Week Type", options=["A", "B"], index=0 if default_week_type == "A" else 1, key="week_type")

default_facilitator = selected_record.get('facilitator', '') if selected_record else ''
facilitator = st.text_input("Facilitator", value=default_facilitator, key="facilitator")

default_attendees = selected_record.get('attendees', '') if selected_record else ''
attendees = st.text_area("Attendees", value=default_attendees, height=80, key="attendees")

st.markdown("---")

st.subheader("📝 Meeting Minutes")

default_minutes = selected_record.get('meeting_minutes', '') if selected_record else ''
meeting_minutes = st.text_area("Minutes", value=default_minutes, height=300, key="minutes")

st.markdown("---")

# Save button
if st.button("💾 Save Meeting", type="primary", use_container_width=True):
    meeting_data = {
        'id': st.session_state.current_meeting_id,
        'program': program,
        'meeting_date': str(meeting_date),
        'term': term.strip(),
        'week_number': int(week_number),
        'week_type': week_type,
        'facilitator': facilitator.strip(),
        'attendees': attendees.strip(),
        'meeting_minutes': meeting_minutes.strip(),
        'student_concerns': [],
        'actions': []
    }
    
    try:
        meeting_id = save_meeting(meeting_data)
        st.success(f"✅ Meeting saved successfully! (ID: {meeting_id})")
        st.session_state.current_meeting_id = meeting_id
        st.rerun()
    except Exception as e:
        st.error(f"⚠️ Failed to save: {e}")

st.markdown("---")
st.caption("🏫 Direct PostgreSQL Connection · Bypasses PostgREST Cache")
