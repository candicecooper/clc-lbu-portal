from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
import json
import os
import time

# For transcript upload
try:
    import docx
    DOCX_AVAILABLE = True
except:
    DOCX_AVAILABLE = False

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

# ── Supabase Connections ──────────────────────────────────────────────────────
# STAFF Meetings uses TWO databases:
# 1. MEETINGS database (cmqyrfekxgjdtuloseri) - for meeting records and agenda items
# 2. OPERATIONAL database (lvzaebjrxrgguypqvdcq) - for bulletin (clc_events)

# Primary connection: MEETINGS database (meeting records, agenda items)
SUPABASE_URL_MEETINGS = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
SUPABASE_KEY_MEETINGS = st.secrets.get("SUPABASE_KEY_MEETINGS", st.secrets["SUPABASE_KEY"])
SUPABASE_SERVICE_KEY_MEETINGS = st.secrets.get("SUPABASE_SERVICE_KEY_MEETINGS", SUPABASE_KEY_MEETINGS)

supabase = create_client(SUPABASE_URL_MEETINGS, SUPABASE_SERVICE_KEY_MEETINGS)

# Secondary connection: OPERATIONAL database (for bulletin)
SUPABASE_URL_OPERATIONAL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY_OPERATIONAL = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY_OPERATIONAL = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY_OPERATIONAL)

supabase_ops = create_client(SUPABASE_URL_OPERATIONAL, SUPABASE_SERVICE_KEY_OPERATIONAL)

GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

# ── BSEM Icebreakers (5-minute activities) ────────────────────────────────────
BSEM_ICEBREAKERS = [
    {
        "week": 1,
        "name": "Two Truths and a Lie",
        "instructions": "Each person shares three statements about themselves - two true, one false. Group guesses which is the lie.",
        "time": "5 mins"
    },
    {
        "week": 2,
        "name": "Gratitude Round",
        "instructions": "Each person shares one thing they're grateful for this week (personal or professional).",
        "time": "5 mins"
    },
    {
        "week": 3,
        "name": "Brain Break: Draw Your Weekend",
        "instructions": "60 seconds to draw something from your weekend. Share with the group.",
        "time": "5 mins"
    },
    {
        "week": 4,
        "name": "Quick Check-In: Rate Your Week",
        "instructions": "Rate your week 1-10 and share one word to describe it.",
        "time": "5 mins"
    },
    {
        "week": 5,
        "name": "Wins & Learnings",
        "instructions": "Share one win and one thing you learned this week.",
        "time": "5 mins"
    },
    {
        "week": 6,
        "name": "Would You Rather?",
        "instructions": "Facilitator poses a 'Would you rather...' question. Quick votes and brief sharing.",
        "time": "5 mins"
    },
    {
        "week": 7,
        "name": "Rose, Thorn, Bud",
        "instructions": "Share: Rose (highlight), Thorn (challenge), Bud (something you're looking forward to).",
        "time": "5 mins"
    },
    {
        "week": 8,
        "name": "Quick Movement Break",
        "instructions": "Stand up stretch or brief movement activity. Can be led by different staff member each week.",
        "time": "5 mins"
    },
    {
        "week": 9,
        "name": "Shout-Outs",
        "instructions": "Acknowledge someone who helped you this week or did something great.",
        "time": "5 mins"
    },
    {
        "week": 10,
        "name": "What's In Your Cup?",
        "instructions": "Share what's filling your emotional cup or draining it this week.",
        "time": "5 mins"
    },
    {
        "week": 11,
        "name": "Reflection Round",
        "instructions": "One word to describe this term. Quick round-robin.",
        "time": "5 mins"
    }
]

# Standing agenda items
STANDING_AGENDA_ITEMS = [
    "Transition Coordinator Info",
    "Manager Info",
    "PAC (Personnel Advisory Committee)",
    "WHS (Work Health & Safety)",
    "Social Club",
    "Finance"
]

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
    
    # Delete meeting option (only for existing meetings)
    with st.expander("🗑️ Delete This Meeting", expanded=False):
        st.warning("⚠️ **Warning:** This will permanently delete this meeting record!")
        
        delete_confirmation = st.text_input(
            "Type 'DELETE' to confirm deletion",
            key="delete_confirm",
            placeholder="Type DELETE here"
        )
        
        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            if st.button("🗑️ Delete Meeting", type="secondary", disabled=(delete_confirmation != "DELETE")):
                try:
                    supabase.table('staff_meetings').delete().eq('id', st.session_state.current_staff_meeting_id).execute()
                    st.success("✅ Meeting deleted successfully!")
                    st.session_state.current_staff_meeting_id = None
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
    st.subheader("📚 Past STAFF Meetings")
    
    if existing_meetings:
        for meeting in existing_meetings:
            with st.expander(f"📅 {meeting['meeting_date']} - T{meeting.get('term', '?')} W{meeting.get('week_number', '?')} - {meeting.get('minute_taker', 'Unknown')}"):
                st.write(f"**Attendees:** {meeting.get('attendees', 'Not recorded')}")
                st.write(f"**Apologies:** {meeting.get('apologies', 'None')}")
                
                st.markdown("---")
                st.write("**📄 Minutes:**")
                meeting_minutes = meeting.get('minutes', 'No minutes recorded')
                if meeting_minutes and meeting_minutes != 'No minutes recorded':
                    # Show formatted minutes
                    st.markdown(meeting_minutes)
                else:
                    st.info("No minutes recorded for this meeting")
                
                if meeting.get('actions'):
                    st.markdown("---")
                    st.write("**Actions:**")
                    try:
                        actions = json.loads(meeting['actions']) if isinstance(meeting['actions'], str) else meeting['actions']
                        for action in actions:
                            st.write(f"- {action.get('action', '')} - **{action.get('owner', '')}** - Due: {action.get('due_date', '')}")
                    except:
                        pass
                
                # Show meeting attachments if present
                if meeting.get('meeting_attachments'):
                    st.markdown("---")
                    st.write("**📎 Meeting Attachments:**")
                    try:
                        attachments = json.loads(meeting['meeting_attachments']) if isinstance(meeting['meeting_attachments'], str) else meeting['meeting_attachments']
                        if attachments:
                            for att in attachments:
                                st.write(f"📎 {att.get('name', '')} - {att.get('description', '')}")
                    except:
                        pass
                
                # Show PD information if present
                if meeting.get('pd_notes') or meeting.get('pd_attendees'):
                    st.markdown("---")
                    st.write("**🎓 Professional Development:**")
                    if meeting.get('pd_attendees'):
                        st.write(f"**PD Attendees:** {meeting['pd_attendees']}")
                    if meeting.get('pd_absent'):
                        st.write(f"**PD Absent:** {meeting['pd_absent']}")
                    if meeting.get('pd_notes'):
                        st.write("**PD Notes:**")
                        st.markdown(meeting['pd_notes'])
                    if meeting.get('pd_attachments'):
                        try:
                            attachments = json.loads(meeting['pd_attachments']) if isinstance(meeting['pd_attachments'], str) else meeting['pd_attachments']
                            if attachments:
                                st.write("**PD Attachments:**")
                                for att in attachments:
                                    st.write(f"📎 {att.get('name', '')} - {att.get('description', '')}")
                        except:
                            pass
    else:
        st.info("No archived meetings yet.")

with tab1:
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
    # ══════════════════════════════════════════════════════════════════════════════
    # 1. STAFF BULLETIN FOR THE WEEK
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📋 Staff Bulletin (This Week)")
    
    # Auto-load bulletin from Staff Bulletin tool based on term and week
    try:
        # Find bulletin edition linked to this meeting's term/week
        bulletin_result = supabase_ops.table('weekly_editions').select('*').eq('meeting_linked', True).eq('meeting_term', term).eq('meeting_week', int(week_number)).execute()
        
        if bulletin_result.data and len(bulletin_result.data) > 0:
            edition = bulletin_result.data[0]
            
            # Get all notices for this edition
            notices_result = supabase_ops.table('notices').select('*').eq('edition_id', edition['id']).order('created_at').execute()
            
            if notices_result.data:
                st.success(f"✅ {len(notices_result.data)} bulletin item(s) loaded from Staff Bulletin")
                
                # Display each notice
                for notice in notices_result.data:
                    category = notice.get('category', 'general')
                    author = notice.get('author', 'Staff')
                    
                    with st.expander(f"📌 {notice['title']} ({category.upper()})"):
                        st.write(f"**From:** {author}")
                        st.write(f"**Category:** {category.title()}")
                        st.markdown("---")
                        st.write(notice.get('content', ''))
            else:
                st.info("Bulletin published but no items added yet")
        else:
            st.info(f"ℹ️ No bulletin published for {term} Week {week_number} yet")
            st.caption("Bulletin items will appear here when published via Staff Bulletin tool")
    
    except Exception as e:
        st.warning(f"Could not load bulletin: {e}")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 2. ATTENDANCE
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("👥 Attendance")
    
    default_attendees = selected_record.get('attendees', '') if selected_record else ''
    attendees = st.text_area("Attendees Present", value=default_attendees, height=80, key="attendees", 
                             placeholder="List staff members present...")
    
    default_apologies = selected_record.get('apologies', '') if selected_record else ''
    apologies = st.text_area("Apologies", value=default_apologies, height=60, key="apologies",
                             placeholder="List staff members with apologies...")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 3. ACKNOWLEDGEMENT OF COUNTRY
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("🪃 Acknowledgement of Country")
    
    # Video playback - Read from environment variable
    VIDEO_URL = os.environ.get("ACKNOWLEDGEMENT_VIDEO_URL", "") or st.secrets.get("ACKNOWLEDGEMENT_VIDEO_URL", "")
    
    if VIDEO_URL:
        with st.expander("📹 Watch Acknowledgement of Country Video", expanded=False):
            st.video(VIDEO_URL)
            st.caption("Play this video at the start of the meeting")
    else:
        st.info("📹 **Video not configured yet** - Add ACKNOWLEDGEMENT_VIDEO_URL to Render environment variables to enable video playback")
    
    # Text version option
    with st.expander("📄 Or Read Acknowledgement of Country (Text Version)", expanded=False):
        st.markdown("""
        *"Before we begin, I acknowledge the Kaurna people as the Traditional Custodians of this land, and pay my respects to their Elders past, present, and emerging.*
        
        *As a Learning and Behaviour Unit, we recognise that many of our students carry trauma — and we acknowledge the particular trauma that colonisation has caused and continues to cause for Aboriginal and Torres Strait Islander peoples.*
        
        *We are committed to trauma-informed, culturally responsive practice that honours the strengths, resilience, and cultures of all our students and their families.*
        
        *I extend my respect to any Aboriginal and Torres Strait Islander people present today."*
        """)
        st.caption("Chair can read this aloud at the start of the meeting")
    
    acknowledgement_done = st.checkbox("✅ Acknowledgement completed", value=selected_record.get('acknowledgement_done', False) if selected_record else False)
    acknowledgement_by = st.text_input("Led by", value=selected_record.get('acknowledgement_by', '') if selected_record else '', placeholder="Who led the Acknowledgement?")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 4. ICEBREAKER / BSEM ACTIVITY (5 mins)
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("🎯 Icebreaker / BSEM Activity (5 mins)")
    
    # Get icebreaker for this week
    week_idx = (int(week_number) - 1) % len(BSEM_ICEBREAKERS)
    icebreaker = BSEM_ICEBREAKERS[week_idx]
    
    with st.expander(f"💡 Suggested Activity: **{icebreaker['name']}**", expanded=True):
        st.write(f"**Time:** {icebreaker['time']}")
        st.write(f"**Instructions:** {icebreaker['instructions']}")
    
    icebreaker_notes = st.text_area("Icebreaker Notes (optional)", 
                                    value=selected_record.get('icebreaker', '') if selected_record else '',
                                    height=80, 
                                    placeholder="Any notes about how the icebreaker went...",
                                    key="icebreaker")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 5. AGENDA ITEMS
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📑 Meeting Agenda")
    
    # Standing agenda items
    st.write("**Standing Items:**")
    
    # Load agenda data
    if selected_record and selected_record.get('agenda_items'):
        try:
            agenda_data = json.loads(selected_record['agenda_items']) if isinstance(selected_record['agenda_items'], str) else selected_record['agenda_items']
        except:
            agenda_data = {}
    else:
        agenda_data = {}
    
    for item in STANDING_AGENDA_ITEMS:
        with st.expander(f"📌 {item}"):
            agenda_data[item] = st.text_area(
                f"Notes for {item}", 
                value=agenda_data.get(item, ''),
                height=100,
                key=f"agenda_{item.replace(' ', '_')}",
                placeholder=f"Add information/updates for {item}..."
            )
    
    # Additional agenda items
    st.write("**Additional Items:**")
    
    # Initialize additional_items FIRST (before Load button)
    if 'additional_agenda' not in agenda_data:
        agenda_data['additional_agenda'] = []
    
    additional_items = agenda_data.get('additional_agenda', [])
    
    # Load pending agenda items from staff
    col_load1, col_load2 = st.columns([1, 3])
    with col_load1:
        if st.button("📥 Load Staff Submissions", key="load_pending_items", type="secondary"):
            try:
                loaded_count = 0
                loaded_ids = []
                
                # Load from OPERATIONAL database (where items actually are)
                try:
                    pending_result = supabase_ops.table('staff_agenda_items').select('*').eq('status', 'pending').execute()
                    
                    if pending_result.data:
                        for item in pending_result.data:
                            item_text = f"{item['item_text']} (submitted by {item['submitted_by']})"
                            if item_text not in additional_items:
                                additional_items.append(item_text)
                                loaded_ids.append(item['id'])
                                loaded_count += 1
                except Exception as e:
                    st.error(f"Error loading items: {e}")
                
                if loaded_count > 0:
                    agenda_data['additional_agenda'] = additional_items
                    
                    # Update status to 'added'
                    for item_id in loaded_ids:
                        try:
                            supabase_ops.table('staff_agenda_items').update({'status': 'added'}).eq('id', item_id).execute()
                        except:
                            pass
                    
                    st.success(f"✅ Loaded {loaded_count} agenda item(s)!")
                    st.rerun()
                else:
                    st.info("No pending agenda items found")
                    
            except Exception as e:
                st.error(f"⚠️ Error: {e}")
    
    with col_load2:
        st.caption("Load agenda items submitted by staff for this week")
    
    # EMERGENCY SIMPLE VERSION - Just type items, one per line
    st.write("**Type agenda items below (one per line):**")
    
    default_items = "\n".join(additional_items) if additional_items else ""
    items_text = st.text_area(
        "Additional Agenda Items",
        value=default_items,
        height=150,
        placeholder="Type each agenda item on a new line...\n\nExample:\nSpeech Buy In Support - Catherine\nSmartar Goal tracking\nWHS update",
        help="Just type your agenda items here - one per line. No buttons needed.",
        key="simple_agenda_items"
    )
    
    # Convert text back to list
    additional_items = [line.strip() for line in items_text.split('\n') if line.strip()]
    agenda_data['additional_agenda'] = additional_items
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 6. MINUTES (Manual OR AI Transcript)
    # ══════════════════════════════════════════════════════════════════════════════
    
    # Initialize minutes variable (will be set in either manual or AI path)
    minutes = selected_record.get('minutes', '') if selected_record else ''
    
    # Check if minutes already exist (for collapsing)
    has_existing_minutes = bool(minutes and minutes.strip())
    
    with st.expander("📄 Meeting Minutes", expanded=not has_existing_minutes):
        
        minutes_method = st.radio("Minutes Entry Method", options=["✍️ Manual Entry", "🤖 AI from Transcript"], horizontal=True)
        
        if minutes_method == "✍️ Manual Entry":
            minutes = st.text_area("Minutes", value=minutes, height=400, key="minutes",
                                   placeholder="Enter meeting minutes here...")
        
        else:  # AI from Transcript
            st.write("**Upload Transcript (.txt or .docx)**")
            
            transcript_file = st.file_uploader("Upload meeting transcript", type=['txt', 'docx'], key="transcript_upload")
            
            if transcript_file:
                # Read transcript
                if transcript_file.name.endswith('.txt'):
                    transcript_text = transcript_file.read().decode('utf-8')
                else:  # .docx
                    if DOCX_AVAILABLE:
                        try:
                            doc = docx.Document(transcript_file)
                            transcript_text = '\n'.join([para.text for para in doc.paragraphs])
                        except Exception as e:
                            st.error(f"Could not read .docx file: {e}")
                            transcript_text = ""
                    else:
                        st.error("python-docx not installed. Please use .txt file.")
                        transcript_text = ""
                
                if transcript_text and GROQ_KEY:
                    if st.button("🤖 Extract Minutes with AI", type="primary"):
                        with st.spinner("Processing transcript with AI..."):
                            try:
                                from groq import Groq
                                client = Groq(api_key=GROQ_KEY)
                                
                                # ENHANCED PROMPT - Extract minutes with sections
                                prompt = f"""You are analyzing a staff meeting transcript. Extract structured meeting minutes with the following format:

**MEETING OVERVIEW**
- Brief summary of key topics discussed (2-3 sentences)

**DISCUSSION BY AGENDA ITEM**

For each topic discussed, create a section with:
- Clear heading (the agenda item/topic)
- Key points discussed (bullet points)
- Decisions made (if any)
- Actions required (if any)

**ACTION ITEMS**
List all action items mentioned in clear format:
- [Person responsible] - [Action to take] - [Deadline if mentioned]

**ADDITIONAL TOPICS**
Any other items discussed not covered above.

Transcript:
{transcript_text}

Format clearly with markdown headings (##) and bullet points."""

                                response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": prompt}],
                                    temperature=0.3,
                                    max_tokens=4000
                                )
                                
                                extracted_minutes = response.choices[0].message.content
                                
                                # Show formatted preview
                                st.success("✅ Minutes extracted successfully!")
                                
                                with st.expander("👁️ Preview Formatted Minutes", expanded=True):
                                    st.markdown(extracted_minutes)
                                
                                # Agenda detection prompt
                                agenda_prompt = f"""From this meeting transcript, list ONLY the specific agenda items or topics that were discussed. 

Return them as a simple list, one per line, with no bullet points or numbering. Just the topic names.

Examples of good output:
Speech pathology support
SMARTAR goal tracking
WHS update
Budget review

Transcript:
{transcript_text}

List the agenda items discussed (one per line):"""

                                agenda_response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": agenda_prompt}],
                                    temperature=0.2,
                                    max_tokens=500
                                )
                                
                                suggested_agenda = agenda_response.choices[0].message.content.strip()
                                
                                # Show suggested agenda items
                                if suggested_agenda:
                                    with st.expander("📋 Agenda Items Detected in Transcript (Click to Auto-Fill)", expanded=False):
                                        st.write("**AI detected these topics were discussed:**")
                                        st.code(suggested_agenda)
                                        
                                        if st.button("➕ Add These to Additional Agenda", type="secondary"):
                                            # Parse suggested items and add to agenda
                                            suggested_items = [item.strip() for item in suggested_agenda.split('\n') if item.strip()]
                                            
                                            # Get current items
                                            current_items_text = st.session_state.get('simple_agenda_items', '')
                                            current_items = [line.strip() for line in current_items_text.split('\n') if line.strip()]
                                            
                                            # Add new items that aren't already there
                                            for item in suggested_items:
                                                if item not in current_items:
                                                    current_items.append(item)
                                            
                                            # Update session state
                                            st.session_state['simple_agenda_items'] = '\n'.join(current_items)
                                            st.success(f"✅ Added {len(suggested_items)} agenda items!")
                                            st.rerun()
                                
                                minutes = st.text_area("Edit AI-Generated Minutes", value=extracted_minutes, height=400, key="ai_minutes")
                                
                            except Exception as e:
                                st.error(f"AI extraction failed: {e}")
                                minutes = st.text_area("Manual entry (AI failed)", height=400, key="fallback_minutes")
                elif not GROQ_KEY:
                    st.warning("⚠️ GROQ_API_KEY not configured. Using manual entry.")
                    minutes = st.text_area("Minutes", height=400, key="manual_minutes_fallback")
                else:
                    minutes = ""
            else:
                st.info("Upload a transcript file to use AI extraction")
                minutes = ""
    
    # Close the expander
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

# AI Action Extraction option (if minutes exist)
if minutes and minutes.strip() and GROQ_KEY:
    with st.expander("🤖 Extract Actions from Minutes with AI", expanded=False):
        st.caption("AI will scan the minutes and extract action items automatically")
        
        if st.button("🤖 Extract Actions", type="secondary", key="extract_actions_ai"):
            with st.spinner("Extracting actions from minutes..."):
                try:
                    from groq import Groq
                    client = Groq(api_key=GROQ_KEY)
                    
                    action_prompt = f"""From these meeting minutes, extract all action items.

For each action, identify:
1. What needs to be done (the action)
2. Who is responsible (name if mentioned, otherwise "Unassigned")
3. Deadline (if mentioned, otherwise leave blank)

Return ONLY a JSON array in this exact format:
[
  {{"action": "action description", "owner": "person name", "due_date": "YYYY-MM-DD or blank"}},
  {{"action": "action description", "owner": "person name", "due_date": "YYYY-MM-DD or blank"}}
]

If no actions found, return: []

Meeting Minutes:
{minutes}

JSON array of actions:"""

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": action_prompt}],
                        temperature=0.2,
                        max_tokens=2000
                    )
                    
                    extracted_text = response.choices[0].message.content.strip()
                    
                    # Try to parse JSON
                    import re
                    # Extract JSON array from response
                    json_match = re.search(r'\[.*\]', extracted_text, re.DOTALL)
                    if json_match:
                        extracted_actions = json.loads(json_match.group())
                        
                        if extracted_actions:
                            st.success(f"✅ Found {len(extracted_actions)} action items!")
                            
                            # Show preview
                            for action in extracted_actions:
                                st.write(f"• {action.get('action', '')} - **{action.get('owner', 'Unassigned')}** - {action.get('due_date', 'No deadline')}")
                            
                            if st.button("➕ Add All Actions", key="add_extracted_actions"):
                                # Add to actions list
                                for action in extracted_actions:
                                    actions.append({
                                        "action": action.get('action', ''),
                                        "owner": action.get('owner', 'Unassigned'),
                                        "due_date": action.get('due_date', ''),
                                        "done": False
                                    })
                                st.success(f"Added {len(extracted_actions)} actions!")
                                st.rerun()
                        else:
                            st.info("No action items found in minutes")
                    else:
                        st.warning("Could not parse AI response. Add actions manually below.")
                        
                except Exception as e:
                    st.error(f"Action extraction failed: {e}")

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
# MEETING ATTACHMENTS (General)
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📎 Meeting Attachments")

with st.expander("📁 Attach Files to Meeting", expanded=False):
    
    # Load existing meeting attachments
    if selected_record and selected_record.get('meeting_attachments'):
        try:
            meeting_attachments = json.loads(selected_record['meeting_attachments']) if isinstance(selected_record['meeting_attachments'], str) else selected_record['meeting_attachments']
        except:
            meeting_attachments = []
    else:
        meeting_attachments = []
    
    # Display existing attachments
    if meeting_attachments:
        st.write("**Attached Files:**")
        for idx, attachment in enumerate(meeting_attachments):
            col_m1, col_m2 = st.columns([4, 1])
            with col_m1:
                st.write(f"📎 {attachment.get('name', 'Unnamed file')} ({attachment.get('filename', '')}) - {attachment.get('description', 'No description')}")
            with col_m2:
                if st.button("🗑️", key=f"delete_meeting_attachment_{idx}"):
                    meeting_attachments.pop(idx)
                    st.rerun()
    
    # Add multiple attachments at once
    st.write("**Add Files:**")
    meeting_uploaded_files = st.file_uploader("Upload files (select multiple)", 
                                             type=['pdf', 'docx', 'pptx', 'txt', 'jpg', 'png', 'xlsx', 'csv', 'mp4', 'mov'],
                                             accept_multiple_files=True,
                                             key="meeting_file_upload")
    
    if meeting_uploaded_files:
        st.write(f"**{len(meeting_uploaded_files)} file(s) selected**")
        
        # Show selected files
        for f in meeting_uploaded_files:
            st.caption(f"📄 {f.name}")
        
        # Description for all files
        meeting_batch_desc = st.text_input("Description for all files (optional)", 
                                          key="meeting_batch_desc",
                                          placeholder="E.g., Budget documents, Policy drafts")
        
        if st.button("➕ Add All Files", key="add_all_meeting_attachments", type="secondary"):
            for file in meeting_uploaded_files:
                meeting_attachments.append({
                    "name": file.name,
                    "description": meeting_batch_desc if meeting_batch_desc else "",
                    "filename": file.name,
                    "size": file.size,
                    "type": file.type,
                    "uploaded_date": str(datetime.date.today())
                })
            st.success(f"✅ Successfully added {len(meeting_uploaded_files)} file(s) to meeting!")
            st.info("💡 Files recorded. Click 'Save Meeting' at the bottom to save changes.")
            st.info("ℹ️ Note: File metadata saved. For full file storage, integrate with Supabase Storage.")
            st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 7. PROFESSIONAL DEVELOPMENT
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("🎓 Professional Development Component")

with st.expander("📚 PD Session Details", expanded=True):
    
    # PD Attendance (auto-populated but editable)
    st.write("**PD Attendance** (Auto-filled from meeting attendance - edit if needed)")
    
    col_pd1, col_pd2 = st.columns(2)
    
    with col_pd1:
        # Pre-fill with meeting attendees but allow editing
        default_pd_attendees = selected_record.get('pd_attendees', attendees) if selected_record else attendees
        pd_attendees = st.text_area("PD Attendees", value=default_pd_attendees, height=80, key="pd_attendees",
                                   placeholder="Staff who attended PD session...")
    
    with col_pd2:
        default_pd_absent = selected_record.get('pd_absent', apologies) if selected_record else apologies
        pd_absent = st.text_area("PD Absentees/Left Early", value=default_pd_absent, height=80, key="pd_absent",
                                placeholder="Staff who missed PD or left early...")
    
    st.markdown("---")
    
    # PD Content Entry Method
    st.write("**PD Content Entry:**")
    pd_method = st.radio("Choose entry method", options=["✍️ Manual Entry", "🤖 AI from Transcript"], 
                       horizontal=True, key="pd_method")
    
    if pd_method == "✍️ Manual Entry":
        default_pd_notes = selected_record.get('pd_notes', '') if selected_record else ''
        pd_notes = st.text_area("PD Main Points / Notes", value=default_pd_notes, height=300, key="pd_notes",
                               placeholder="Document key points from the PD session...")
    
    else:  # AI from Transcript
        st.write("**Upload PD Transcript**")
        
        pd_transcript_file = st.file_uploader("Upload PD transcript (.txt or .docx)", 
                                             type=['txt', 'docx'], 
                                             key="pd_transcript_upload")
        
        if pd_transcript_file:
            # Read transcript
            if pd_transcript_file.name.endswith('.txt'):
                pd_transcript_text = pd_transcript_file.read().decode('utf-8')
            else:  # .docx
                if DOCX_AVAILABLE:
                    try:
                        pd_doc = docx.Document(pd_transcript_file)
                        pd_transcript_text = '\n'.join([para.text for para in pd_doc.paragraphs])
                    except Exception as e:
                        st.error(f"Could not read .docx file: {e}")
                        pd_transcript_text = ""
                else:
                    st.error("python-docx not installed. Please use .txt file.")
                    pd_transcript_text = ""
            
            if pd_transcript_text and GROQ_KEY:
                if st.button("🤖 Extract PD Notes with AI", type="secondary", key="extract_pd_ai"):
                    with st.spinner("Processing PD transcript..."):
                        try:
                            from groq import Groq
                            client = Groq(api_key=GROQ_KEY)
                            
                            prompt = f"""Extract the main points and key learnings from this professional development session transcript.

Structure the output with:
- Topic/Title of PD session
- Key points covered (bullet points)
- Main takeaways
- Any action items or next steps

Transcript:
{pd_transcript_text}

Format as clear, structured notes."""

                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.3,
                                max_tokens=3000
                            )
                            
                            extracted_pd = response.choices[0].message.content
                            
                            st.success("✅ PD notes extracted!")
                            pd_notes = st.text_area("Edit AI-Generated PD Notes", value=extracted_pd, 
                                                   height=300, key="ai_pd_notes")
                            
                        except Exception as e:
                            st.error(f"AI extraction failed: {e}")
                            pd_notes = st.text_area("Manual entry (AI failed)", height=300, key="fallback_pd_notes")
            elif not GROQ_KEY:
                st.warning("⚠️ GROQ_API_KEY not configured. Using manual entry.")
                pd_notes = st.text_area("PD Notes", height=300, key="manual_pd_notes_fallback")
            else:
                pd_notes = ""
        else:
            st.info("Upload a transcript to use AI extraction")
            pd_notes = ""
    
    st.markdown("---")
    
    # PD Attachments
    st.write("**PD Attachments / Resources:**")
    
    # Load existing attachments
    if selected_record and selected_record.get('pd_attachments'):
        try:
            pd_attachments = json.loads(selected_record['pd_attachments']) if isinstance(selected_record['pd_attachments'], str) else selected_record['pd_attachments']
        except:
            pd_attachments = []
    else:
        pd_attachments = []
    
    # Display existing attachments
    if pd_attachments:
        st.write("**Uploaded Attachments:**")
        for idx, attachment in enumerate(pd_attachments):
            col_att1, col_att2 = st.columns([4, 1])
            with col_att1:
                st.write(f"📎 {attachment.get('name', 'Unnamed file')} ({attachment.get('filename', '')}) - {attachment.get('description', 'No description')}")
            with col_att2:
                if st.button("🗑️", key=f"delete_pd_attachment_{idx}"):
                    pd_attachments.pop(idx)
                    st.rerun()
    
    # Add multiple attachments at once
    st.write("**Add New Attachments:**")
    uploaded_files = st.file_uploader("Upload files (select multiple)", 
                                     type=['pdf', 'docx', 'pptx', 'txt', 'jpg', 'png', 'xlsx', 'mp4', 'mov'],
                                     accept_multiple_files=True,
                                     key="pd_file_upload")
    
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected**")
        
        # Show selected files
        for f in uploaded_files:
            st.caption(f"📄 {f.name}")
        
        # Description for all files (optional)
        batch_description = st.text_input("Description for all files (optional)", 
                                         key="pd_batch_desc",
                                         placeholder="E.g., Restorative Practices Resources")
        
        if st.button("➕ Add All Files", key="add_all_pd_attachments", type="secondary"):
            for file in uploaded_files:
                pd_attachments.append({
                    "name": file.name,
                    "description": batch_description if batch_description else "",
                    "filename": file.name,
                    "size": file.size,
                    "type": file.type,
                    "uploaded_date": str(datetime.date.today())
                })
            st.success(f"✅ Successfully added {len(uploaded_files)} file(s) to PD!")
            st.info("💡 Files recorded. Click 'Save Meeting' at the bottom to save changes.")
            st.info("ℹ️ Note: File metadata saved. For full file storage, integrate with Supabase Storage.")
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
        "acknowledgement_done": acknowledgement_done,
        "acknowledgement_by": acknowledgement_by.strip(),
        "icebreaker": icebreaker_notes.strip(),
        "agenda_items": json.dumps(agenda_data),
        "minutes": minutes.strip() if minutes else '',
        "actions": json.dumps(actions) if actions else '[]',
        "meeting_attachments": json.dumps(meeting_attachments) if meeting_attachments else '[]',
        "pd_attendees": pd_attendees.strip(),
        "pd_absent": pd_absent.strip(),
        "pd_notes": pd_notes.strip() if pd_notes else '',
        "pd_attachments": json.dumps(pd_attachments) if pd_attachments else '[]'
    }
    
    try:
        if st.session_state.current_staff_meeting_id:
            # Update existing
            result = supabase.table('staff_meetings').update(meeting_data).eq('id', st.session_state.current_staff_meeting_id).execute()
            st.success("✅ **Meeting Saved Successfully!**")
            st.info("📄 Minutes, agenda, and actions have been saved. The Minutes section will collapse on next page load.")
            time.sleep(2)
            st.rerun()
        else:
            # Create new
            result = supabase.table('staff_meetings').insert(meeting_data).execute()
            if result.data:
                st.session_state.current_staff_meeting_id = result.data[0]['id']
                st.success("✅ **New Meeting Created & Saved!**")
                st.info("📄 All meeting details saved successfully.")
                time.sleep(2)
                st.rerun()
    
    except Exception as e:
        st.error(f"⚠️ Could not save meeting: {e}")

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre · LBU · STAFF Meetings")
