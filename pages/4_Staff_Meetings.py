from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
import json

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="STAFF Meetings | CLC-LBU", page_icon="👥", layout="wide")
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
require_auth("STAFF Meetings", "👥")
logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Supabase (same as Team Meetings) ──────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── Session state ──────────────────────────────────────────────────────────────
if 'current_staff_meeting_id' not in st.session_state:
    st.session_state.current_staff_meeting_id = None

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.title("👥 STAFF MEETINGS")
st.caption("Weekly All-Staff Meetings · DfE Format")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING SELECTOR
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📅 Select Meeting")

# Fetch existing meetings
try:
    result = supabase.table('staff_meetings').select('*').order('meeting_date', desc=True).limit(20).execute()
    existing_meetings = result.data if result.data else []
except Exception as e:
    st.warning(f"Could not load meetings: {e}")
    existing_meetings = []

meeting_options = ["➕ New Meeting"] + [
    f"{m['meeting_date']} - T{m.get('term', '?')} W{m.get('week_number', '?')} - {m.get('minute_taker', 'Unknown')}"
    for m in existing_meetings
]

selected_option = st.selectbox("Choose a meeting", options=meeting_options, key="staff_meeting_selector")

if selected_option == "➕ New Meeting":
    selected_record = None
    st.session_state.current_staff_meeting_id = None
else:
    idx = meeting_options.index(selected_option) - 1
    selected_record = existing_meetings[idx]
    st.session_state.current_staff_meeting_id = selected_record['id']

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING FORM
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📋 Meeting Details")

col1, col2, col3 = st.columns(3)

# Defaults
if selected_record:
    default_date = datetime.date.fromisoformat(selected_record['meeting_date'])
    default_term = selected_record.get('term', '')
    default_week = selected_record.get('week_number', 1)
else:
    default_date = datetime.date.today()
    default_term = ''
    default_week = 1

with col1:
    meeting_date = st.date_input("Meeting Date", value=default_date, key="staff_date")

with col2:
    term = st.text_input("Term", value=default_term, placeholder="T1", key="staff_term")

with col3:
    week_number = st.number_input("Week Number", min_value=1, max_value=11, value=default_week, key="staff_week")

default_minute_taker = selected_record.get('minute_taker', get_staff_name()) if selected_record else get_staff_name()
minute_taker = st.text_input("Minute Taker", value=default_minute_taker, key="minute_taker")

st.markdown("---")

st.subheader("👥 Attendance")

default_attendees = selected_record.get('attendees', '') if selected_record else ''
attendees = st.text_area("Attendees Present", value=default_attendees, height=80, key="attendees", 
                         placeholder="List staff members present...")

default_apologies = selected_record.get('apologies', '') if selected_record else ''
apologies = st.text_area("Apologies", value=default_apologies, height=60, key="apologies",
                         placeholder="List staff members with apologies...")

st.markdown("---")

st.subheader("📄 Meeting Minutes")

default_minutes = selected_record.get('minutes', '') if selected_record else ''
minutes = st.text_area("Minutes", value=default_minutes, height=400, key="minutes",
                       placeholder="Enter meeting minutes here...")

st.markdown("---")

st.subheader("✅ Actions")

# Load actions
if selected_record and selected_record.get('actions'):
    try:
        if isinstance(selected_record['actions'], str):
            actions = json.loads(selected_record['actions'])
        else:
            actions = selected_record['actions']
    except:
        actions = []
else:
    actions = []

# Display existing actions
if actions:
    st.write("**Current Actions:**")
    for idx, action in enumerate(actions):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.write(f"{idx+1}. {action.get('action', '')} - **{action.get('owner', 'Unassigned')}** - Due: {action.get('due_date', 'No date')}")
        with col_b:
            if st.button("🗑️", key=f"delete_action_{idx}"):
                actions.pop(idx)
                st.rerun()

st.write("**Add New Action:**")
col_a1, col_a2, col_a3, col_a4 = st.columns([3, 2, 2, 1])

with col_a1:
    new_action = st.text_input("Action Description", key="new_action", placeholder="What needs to be done?")

with col_a2:
    new_owner = st.text_input("Assigned To", key="new_owner", placeholder="Who will do it?")

with col_a3:
    new_due = st.date_input("Due Date", key="new_due", value=None)

with col_a4:
    st.write("")  # Spacing
    st.write("")  # Spacing
    if st.button("➕ Add", key="add_action_btn", use_container_width=True):
        if new_action.strip():
            actions.append({
                "action": new_action.strip(),
                "owner": new_owner.strip(),
                "due_date": str(new_due) if new_due else "",
                "done": False
            })
            st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SAVE BUTTON
# ══════════════════════════════════════════════════════════════════════════════

if st.button("💾 Save Meeting", type="primary", use_container_width=True, key="save_meeting"):
    
    meeting_data = {
        "meeting_date": str(meeting_date),
        "term": term.strip(),
        "week_number": int(week_number),
        "minute_taker": minute_taker.strip(),
        "attendees": attendees.strip(),
        "apologies": apologies.strip(),
        "minutes": minutes.strip(),
        "actions": json.dumps(actions) if actions else '[]'
    }
    
    try:
        if st.session_state.current_staff_meeting_id:
            # Update existing
            result = supabase.table('staff_meetings').update(meeting_data).eq('id', st.session_state.current_staff_meeting_id).execute()
            st.success(f"✅ Meeting updated! (ID: {st.session_state.current_staff_meeting_id})")
        else:
            # Create new
            result = supabase.table('staff_meetings').insert(meeting_data).execute()
            if result.data:
                st.session_state.current_staff_meeting_id = result.data[0]['id']
                st.success(f"✅ Meeting created! (ID: {st.session_state.current_staff_meeting_id})")
                st.rerun()
    
    except Exception as e:
        st.error(f"⚠️ Could not save meeting: {e}")

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre · LBU · STAFF Meetings")
