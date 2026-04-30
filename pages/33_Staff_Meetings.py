"""
STAFF Meetings Tool - Standalone
Page 33 of CLC-LBU Portal
Weekly staff meetings with DfE format, bulletin integration, and AI transcript processing
"""

import streamlit as st
import datetime
import json
from supabase import create_client

# Get staff name helper
try:
    from utils import get_staff_name
except ImportError:
    def get_staff_name():
        """Fallback if utils.py doesn't exist"""
        return st.session_state.get("staff_name", "Staff Member")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="STAFF Meetings | CLC-LBU",
    page_icon="👥",
    layout="wide"
)

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

supabase = get_supabase()

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════════

if "current_staff_meeting_id" not in st.session_state:
    st.session_state.current_staff_meeting_id = None

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="background:linear-gradient(135deg, #1e6f75 0%, #14b8a6 100%);
            border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
    <h1 style="color:white;margin:0;font-size:2rem;">👥 STAFF MEETINGS</h1>
    <p style="color:#e0f2f1;margin:5px 0 0 0;font-size:1rem;">
        Weekly All-Staff Meetings · DfE Format
    </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MEETING SELECTOR
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### 📅 Select Meeting")

# Load existing meetings
try:
    result = supabase.table('staff_meetings').select('*').order('meeting_date', desc=True).limit(20).execute()
    existing_meetings = result.data if result.data else []
except Exception:
    existing_meetings = []

meeting_options = ["➕ New Meeting"] + [
    f"{m['meeting_date']} - T{m.get('term', '?')} W{m.get('week_number', '?')} - {m.get('minute_taker', 'Unknown')}"
    for m in existing_meetings
]

selected_option = st.selectbox(
    "Choose a meeting",
    options=meeting_options,
    key="staff_meeting_selector"
)

if selected_option == "➕ New Meeting":
    selected_record = None
    st.session_state.current_staff_meeting_id = None
else:
    idx = meeting_options.index(selected_option) - 1
    selected_record = existing_meetings[idx]
    st.session_state.current_staff_meeting_id = selected_record['id']

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING DETAILS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### 📋 Meeting Details")

col1, col2, col3 = st.columns(3)

default_date = datetime.date.fromisoformat(selected_record['meeting_date']) if selected_record else datetime.date.today()
default_term = selected_record.get('term', '') if selected_record else ''
default_week = selected_record.get('week_number', 1) if selected_record else 1

with col1:
    meeting_date = st.date_input("Date", value=default_date, key="staff_date")

with col2:
    term = st.text_input("Term", value=default_term, placeholder="T1", key="staff_term")

with col3:
    week_number = st.number_input("Week #", min_value=1, max_value=11, value=default_week, key="staff_week")

default_minute_taker = selected_record.get('minute_taker', get_staff_name()) if selected_record else get_staff_name()
minute_taker = st.text_input("**Minute Taker**", value=default_minute_taker, key="minute_taker")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# WEEKLY BULLETIN
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### 📰 Weekly Bulletin")
st.caption("The published bulletin for this meeting week (auto-fetched or manual entry)")

default_bulletin = selected_record.get('bulletin_content', '') if selected_record else ''
bulletin_content = st.text_area(
    "Bulletin content (optional)",
    value=default_bulletin,
    height=120,
    placeholder="Week's bulletin will appear here...",
    key="bulletin_content"
)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# DfE MEETING TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### 📝 Meeting Record (DfE Template)")

# Attendees
st.markdown("**Attendees**")
default_attendees = selected_record.get('attendees', '') if selected_record else ''
attendees = st.text_area(
    "Present",
    value=default_attendees,
    height=80,
    placeholder="List staff members present...",
    key="attendees"
)

# Apologies
default_apologies = selected_record.get('apologies', '') if selected_record else ''
apologies = st.text_area(
    "Apologies",
    value=default_apologies,
    height=60,
    placeholder="Staff who sent apologies...",
    key="apologies"
)

st.markdown("---")

# Acknowledgement of Country
st.markdown("**Acknowledgement of Country**")
col_ack1, col_ack2 = st.columns([1, 3])

default_ack_done = selected_record.get('acknowledgement_done', False) if selected_record else False
default_ack_by = selected_record.get('acknowledgement_by', '') if selected_record else ''

with col_ack1:
    acknowledgement_done = st.checkbox("Completed", value=default_ack_done, key="ack_done")

with col_ack2:
    acknowledgement_by = st.text_input(
        "By (name)",
        value=default_ack_by,
        placeholder="Who delivered the acknowledgement?",
        key="ack_by",
        disabled=not acknowledgement_done
    )

st.markdown("---")

# Ice Breaker Activity
st.markdown("**Ice Breaker / Team Building Activity**")
default_icebreaker = selected_record.get('icebreaker', '') if selected_record else ''
icebreaker = st.text_area(
    "Activity description",
    value=default_icebreaker,
    height=80,
    placeholder="Brief description of ice breaker or team activity...",
    key="icebreaker"
)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TRANSCRIPT UPLOAD & AI PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### 🎙️ Transcript Upload & AI Processing")
st.caption("Upload a transcript file or paste transcript text to auto-generate meeting minutes")

transcript_source = st.radio(
    "Transcript source",
    options=["📄 Upload File", "✏️ Paste Text"],
    horizontal=True,
    key="transcript_source"
)

transcript_text = ""

if transcript_source == "📄 Upload File":
    uploaded_file = st.file_uploader(
        "Upload transcript (.txt or .docx)",
        type=['txt', 'docx'],
        key="transcript_upload"
    )
    
    if uploaded_file:
        if uploaded_file.name.endswith('.txt'):
            transcript_text = uploaded_file.read().decode('utf-8')
        elif uploaded_file.name.endswith('.docx'):
            try:
                import docx
                doc = docx.Document(uploaded_file)
                transcript_text = '\n'.join([para.text for para in doc.paragraphs])
            except ImportError:
                st.error("python-docx library not installed. Please upload a .txt file instead.")
                transcript_text = ""
            except Exception as e:
                st.error(f"Could not read .docx file: {e}")
                transcript_text = ""

else:  # Paste text
    transcript_text = st.text_area(
        "Paste transcript here",
        height=200,
        placeholder="Paste meeting transcript...",
        key="transcript_paste"
    )

# AI Process button
if transcript_text.strip():
    if st.button("🤖 Generate Minutes from Transcript", type="primary", use_container_width=True):
        with st.spinner("Processing transcript with AI..."):
            try:
                from groq import Groq
                
                groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                
                prompt = f"""You are a professional minute-taker for a school staff meeting.

Convert this meeting transcript into structured DfE-format meeting minutes.

TRANSCRIPT:
{transcript_text}

FORMAT YOUR RESPONSE AS:

**Key Discussion Points:**
- [Bullet point summary of main topics discussed]

**Decisions Made:**
- [Bullet point list of decisions]

**Actions Arising:**
- [Action] - [Person] - [Due date if mentioned]

**Next Steps:**
- [Bullet point summary]

Keep it professional, clear, and concise. Focus on decisions and actions, not verbatim conversation."""

                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                generated_minutes = response.choices[0].message.content
                
                st.success("✅ Minutes generated!")
                st.session_state.generated_minutes = generated_minutes
                
            except Exception as e:
                st.error(f"AI processing failed: {e}")
                st.session_state.generated_minutes = None

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING MINUTES (Editable)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### 📄 Meeting Minutes")
st.caption("AI-generated or manually written minutes")

# Pre-fill with AI-generated if available
if "generated_minutes" in st.session_state and st.session_state.generated_minutes:
    default_minutes = st.session_state.generated_minutes
elif selected_record:
    default_minutes = selected_record.get('minutes', '')
else:
    default_minutes = ''

minutes = st.text_area(
    "Minutes (supports markdown)",
    value=default_minutes,
    height=300,
    placeholder="Write or paste meeting minutes here...\n\nSupports markdown formatting.",
    key="minutes"
)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### ✅ Actions")
st.caption("Track action items and assigned owners")

# Load existing actions
if selected_record and selected_record.get('actions'):
    try:
        actions = json.loads(selected_record['actions'])
    except:
        actions = []
else:
    actions = []

# Display existing actions
if actions:
    st.markdown("**Current Actions:**")
    for idx, action in enumerate(actions):
        col_action, col_owner, col_due, col_done, col_del = st.columns([3, 2, 1.5, 0.8, 0.5])
        
        with col_action:
            st.text(action.get('action', 'No description'))
        with col_owner:
            st.caption(f"👤 {action.get('owner', 'Unassigned')}")
        with col_due:
            st.caption(f"📅 {action.get('due_date', 'No date')}")
        with col_done:
            done_status = "✓ Done" if action.get('done', False) else "○ Open"
            st.caption(done_status)
        with col_del:
            if st.button("🗑️", key=f"del_action_{idx}"):
                actions.pop(idx)
                st.rerun()

# Add new action
st.markdown("**Add New Action:**")
col_new1, col_new2, col_new3 = st.columns([3, 2, 1.5])

with col_new1:
    new_action = st.text_input("Action", key="new_action", placeholder="What needs to be done?")

with col_new2:
    new_owner = st.text_input("Owner", key="new_owner", placeholder="Who's responsible?")

with col_new3:
    new_due = st.date_input("Due Date", key="new_due_date", value=None)

if st.button("➕ Add Action", key="add_action_btn"):
    if new_action.strip():
        actions.append({
            "action": new_action.strip(),
            "owner": new_owner.strip(),
            "due_date": str(new_due) if new_due else "",
            "done": False
        })
        st.rerun()
    else:
        st.warning("Please enter an action")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SAVE MEETING
# ══════════════════════════════════════════════════════════════════════════════

if st.button("💾 Save Meeting", type="primary", use_container_width=True, key="save_meeting"):
    
    meeting_data = {
        "meeting_date": str(meeting_date),
        "term": term.strip(),
        "week_number": int(week_number),
        "minute_taker": minute_taker.strip(),
        "bulletin_content": bulletin_content.strip(),
        "attendees": attendees.strip(),
        "apologies": apologies.strip(),
        "acknowledgement_done": acknowledgement_done,
        "acknowledgement_by": acknowledgement_by.strip() if acknowledgement_done else "",
        "icebreaker": icebreaker.strip(),
        "minutes": minutes.strip(),
        "actions": json.dumps(actions)
    }
    
    try:
        if st.session_state.current_staff_meeting_id:
            # Update existing
            supabase.table('staff_meetings').update(meeting_data).eq('id', st.session_state.current_staff_meeting_id).execute()
            st.success("✅ Meeting updated successfully!")
        else:
            # Create new
            result = supabase.table('staff_meetings').insert(meeting_data).execute()
            if result.data:
                st.session_state.current_staff_meeting_id = result.data[0]['id']
                st.success(f"✅ Meeting created! (ID: {st.session_state.current_staff_meeting_id})")
                st.rerun()
    
    except Exception as e:
        st.error(f"⚠️ Failed to save meeting: {e}")
        st.info("💡 The staff_meetings table may need to be created. See setup SQL below.")
        
        with st.expander("🔧 Database Setup SQL"):
            st.code("""
CREATE TABLE staff_meetings (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  meeting_date DATE NOT NULL,
  term TEXT,
  week_number INTEGER,
  minute_taker TEXT,
  bulletin_content TEXT,
  attendees TEXT,
  apologies TEXT,
  acknowledgement_done BOOLEAN DEFAULT FALSE,
  acknowledgement_by TEXT,
  icebreaker TEXT,
  minutes TEXT,
  actions JSONB DEFAULT '[]'
);

ALTER TABLE staff_meetings DISABLE ROW LEVEL SECURITY;
GRANT ALL ON staff_meetings TO anon, authenticated, service_role;
GRANT ALL ON SEQUENCE staff_meetings_id_seq TO anon, authenticated, service_role;

CREATE INDEX idx_staff_meetings_date ON staff_meetings(meeting_date DESC);
            """, language="sql")

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre · LBU · STAFF Meetings Tool v1.0")
