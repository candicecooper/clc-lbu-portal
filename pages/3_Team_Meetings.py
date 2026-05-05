from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
import json

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Team Meetings | CLC-LBU", page_icon="🎯", layout="wide")
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
require_auth("Team Meetings", "🎯")
logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Program selector in sidebar ────────────────────────────────────────────────
st.sidebar.title("🎯 Team Meetings")
st.sidebar.markdown("---")

PROGRAMS = {
    "JP": "🔵 Junior Primary",
    "PY": "🟢 Primary Years", 
    "SY": "🟣 Senior Years",
    "Specialist": "🎨 Specialist Program"
}

selected_program = st.sidebar.radio(
    "Select Program",
    options=list(PROGRAMS.keys()),
    format_func=lambda x: PROGRAMS[x],
    key="program_selector"
)

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── Session state ──────────────────────────────────────────────────────────────
if 'current_meeting_id' not in st.session_state:
    st.session_state.current_meeting_id = None

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.title(f"{PROGRAMS[selected_program]} Team Meeting")
st.caption(f"Program-based team meeting minutes - {selected_program}")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING SELECTOR
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📅 Select Meeting")

# Fetch existing meetings for this program
try:
    result = supabase.table('tm_program_meetings').select('*').eq('program', selected_program).order('meeting_date', desc=True).limit(20).execute()
    existing_meetings = result.data if result.data else []
except Exception as e:
    st.warning(f"Could not load meetings: {e}")
    existing_meetings = []

meeting_options = ["➕ New Meeting"] + [
    f"{m['meeting_date']} - {m.get('week_type', '?')} - Week {m.get('week_number', '?')} - {m.get('facilitator', 'Unknown')}"
    for m in existing_meetings
]

selected_option = st.selectbox("Choose a meeting to edit or create new", options=meeting_options, key="meeting_selector")

if selected_option == "➕ New Meeting":
    selected_record = None
    st.session_state.current_meeting_id = None
else:
    idx = meeting_options.index(selected_option) - 1
    selected_record = existing_meetings[idx]
    st.session_state.current_meeting_id = selected_record['id']
    
    # Delete meeting option
    with st.expander("🗑️ Delete This Meeting", expanded=False):
        st.warning("⚠️ **Warning:** This will permanently delete this meeting record!")
        
        delete_confirmation = st.text_input(
            "Type 'DELETE' to confirm deletion",
            key="delete_confirm_team",
            placeholder="Type DELETE here"
        )
        
        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            if st.button("🗑️ Delete Meeting", type="secondary", disabled=(delete_confirmation != "DELETE")):
                try:
                    supabase.table('tm_program_meetings').delete().eq('id', st.session_state.current_meeting_id).execute()
                    st.success("✅ Meeting deleted successfully!")
                    st.session_state.current_meeting_id = None
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Could not delete meeting: {e}")
        
        with col_del2:
            if delete_confirmation != "DELETE":
                st.caption("Type DELETE above to enable deletion")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS: CURRENT MEETING / ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2 = st.tabs(["📝 Current Meeting", "📚 Meeting Archive"])

with tab2:
    st.subheader(f"📚 Past {selected_program} Team Meetings")
    
    if existing_meetings:
        for meeting in existing_meetings:
            with st.expander(f"📅 {meeting['meeting_date']} - {meeting.get('week_type', '?')} - Week {meeting.get('week_number', '?')}"):
                
                col_archive1, col_archive2 = st.columns([4, 1])
                
                with col_archive1:
                    st.write(f"**Facilitator:** {meeting.get('facilitator', 'Not recorded')}")
                    st.write(f"**Attendees:** {meeting.get('attendees', 'Not recorded')}")
                
                with col_archive2:
                    if st.button("✏️ Edit", key=f"edit_{meeting['id']}", use_container_width=True):
                        st.session_state.current_meeting_id = meeting['id']
                        st.rerun()
                
                st.markdown("---")
                st.write("**Check-in Notes:**")
                st.write(meeting.get('checkin_notes', 'No check-in notes'))
                
                st.markdown("---")
                st.write("**Meeting Minutes:**")
                st.write(meeting.get('meeting_minutes', 'No minutes recorded'))
                
                if meeting.get('actions'):
                    st.markdown("---")
                    st.write("**Actions:**")
                    try:
                        actions = json.loads(meeting['actions']) if isinstance(meeting['actions'], str) else meeting['actions']
                        for action in actions:
                            st.write(f"- {action.get('action', '')} - **{action.get('owner', '')}** - Due: {action.get('due_date', '')}")
                    except:
                        pass
    else:
        st.info(f"No archived {selected_program} meetings yet.")

with tab1:
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # MEETING FORM
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📋 Meeting Details")
    
    col1, col2, col3 = st.columns(3)
    
    # Defaults from selected record or new
    if selected_record:
        default_date = datetime.date.fromisoformat(selected_record['meeting_date'])
        default_week_type = selected_record.get('week_type', 'Week A')
        default_week_num = selected_record.get('week_number', 1)
        default_facilitator = selected_record.get('facilitator', get_staff_name())
    else:
        default_date = datetime.date.today()
        default_week_type = 'Week A'
        default_week_num = 1
        default_facilitator = get_staff_name()
    
    with col1:
        meeting_date = st.date_input("Meeting Date", value=default_date, key="meeting_date")
    
    with col2:
        week_type = st.selectbox("Week Type", options=["Week A", "Week B"], 
                                index=0 if default_week_type == "Week A" else 1,
                                key="week_type")
    
    with col3:
        week_number = st.number_input("Week Number", min_value=1, max_value=11, 
                                     value=default_week_num, key="week_number")
    
    facilitator = st.text_input("Facilitator", value=default_facilitator, key="facilitator")
    
    default_attendees = selected_record.get('attendees', '') if selected_record else ''
    attendees = st.text_area("Attendees", value=default_attendees, height=80, key="attendees",
                             placeholder="List team members present...")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # CHECK-IN
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("💬 Check-In (5 mins)")
    
    default_checkin = selected_record.get('checkin_notes', '') if selected_record else ''
    checkin_notes = st.text_area("Check-in Notes", value=default_checkin, height=100, key="checkin",
                                 placeholder="Brief notes from check-in round...")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # MEETING MINUTES
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📄 Meeting Minutes")
    
    default_minutes = selected_record.get('meeting_minutes', '') if selected_record else ''
    meeting_minutes = st.text_area("Minutes", value=default_minutes, height=400, key="minutes",
                                   placeholder="Enter meeting minutes here...")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ══════════════════════════════════════════════════════════════════════════════
    
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
        st.write("")
        st.write("")
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
            "program": selected_program,
            "meeting_date": str(meeting_date),
            "week_type": week_type,
            "week_number": int(week_number),
            "facilitator": facilitator.strip(),
            "attendees": attendees.strip(),
            "checkin_notes": checkin_notes.strip(),
            "meeting_minutes": meeting_minutes.strip(),
            "actions": json.dumps(actions) if actions else '[]'
        }
        
        try:
            if st.session_state.current_meeting_id:
                # Update existing meeting
                result = supabase.table('tm_program_meetings').update(meeting_data).eq('id', st.session_state.current_meeting_id).execute()
                st.success(f"✅ Meeting updated successfully! (ID: {st.session_state.current_meeting_id})")
            else:
                # Create new meeting
                result = supabase.table('tm_program_meetings').insert(meeting_data).execute()
                if result.data:
                    st.session_state.current_meeting_id = result.data[0]['id']
                    st.success(f"✅ Meeting created successfully! (ID: {st.session_state.current_meeting_id})")
                    st.rerun()
        
        except Exception as e:
            st.error(f"⚠️ Could not save meeting: {e}")

st.markdown("---")
st.caption(f"🏫 Cowandilla Learning Centre · LBU · {selected_program} Team Meetings")
